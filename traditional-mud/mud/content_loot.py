from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_balance as economy_balance
import mud.economy_loop as economy
import mud.npcs as mobile_npcs
from mud.corpse_loot import LootTableEntry, NPC_LOOT_TABLES, register_loot_table
from mud.crafting import ItemDefinition


@dataclass(frozen=True, slots=True)
class ContentLootCoverage:
    killable_definitions: int
    generated_tables: int
    authored_tables_preserved: int
    missing_tables: tuple[str, ...]


# These are deliberately broad salvage/material categories. They give every
# combat encounter a thematically legible physical drop without inventing a
# separate bespoke crafting item for every one-off monster in the current world.
# Existing authored drops always survive and remain the most specific rewards.
CONTENT_LOOT_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        key="field_salvage",
        name="Field Salvage",
        description=(
            "Usable straps, fasteners, wrappings, and other practical odds and ends recovered from a defeated foe."
        ),
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="chitin_fragment",
        name="Chitin Fragment",
        description="A hard fragment of shell or carapace suitable for reinforcement, inlay, or alchemical grinding.",
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="grave_dust",
        name="Grave Dust",
        description="Fine gray residue gathered from animated remains and other death-touched creatures.",
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="arcane_residue",
        name="Arcane Residue",
        description="A faintly reactive residue left behind by magical, extraplanar, or spell-saturated creatures.",
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="construct_scrap",
        name="Construct Scrap",
        description="Bent plates, springs, wire, rivets, and other salvageable pieces from a mechanical or constructed foe.",
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="fungal_tissue",
        name="Fungal Tissue",
        description="A cleanly cut piece of unusual fungal matter, still carrying a trace of its original spore structure.",
        category="material",
        tier=1,
    ),
    ItemDefinition(
        key="monster_trophy",
        name="Monster Trophy",
        description="A fang, claw, horn-tip, scale, or other recognizable trophy from a dangerous creature.",
        category="material",
        tier=1,
    ),
)

_GENERATED_KEYS: set[str] = set()


_FAMILY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "undead",
        (
            "undead", "skeleton", "skeletal", "bone", "ghoul", "wight", "revenant",
            "zombie", "mummy", "lich", "grave", "crypt", "corpse", "specter", "spectre",
            "ghost", "shade", "deathless",
        ),
    ),
    (
        "construct",
        (
            "construct", "clockwork", "automaton", "golem", "machine", "mechanical",
            "gearwork", "gear-work", "engine", "sentinel frame",
        ),
    ),
    (
        "fungal",
        ("fungus", "fungal", "mushroom", "mold", "mould", "spore", "mycel", "toadstool"),
    ),
    (
        "insect",
        (
            "spider", "beetle", "tick", "swarm", "wasp", "hornet", "centipede", "moth",
            "roach", "scarab", "insect", "arachnid",
        ),
    ),
    (
        "fiend",
        ("imp", "demon", "devil", "fiend", "hell", "infernal"),
    ),
    (
        "beast",
        (
            "wolf", "rat", "boar", "bear", "hound", "stag", "elk", "hare", "squirrel",
            "predator", "beast", "burrower", "snapper", "serpent", "snake", "lizard",
            "croc", "drake", "wyrm", "cat", "panther", "lion", "bat",
        ),
    ),
    (
        "arcane",
        (
            "elemental", "wisp", "arcane", "astral", "spirit", "apparition", "anomaly",
            "moonfire", "ember", "cinder", "flame", "void", "planar",
        ),
    ),
    (
        "humanoid",
        (
            "bandit", "raider", "soldier", "guard", "cultist", "knight", "warrior",
            "scavenger", "brigand", "smuggler", "pirate", "warden", "marshal", "captain",
            "commander", "goblin", "troll", "dwarf", "elf", "human", "mercenary",
            "thief", "thug", "outlaw", "host", "hunter",
        ),
    ),
)


_PROFILE_ITEMS: dict[str, tuple[tuple[str, float], ...]] = {
    "undead": (("bone_chips", 0.72), ("grave_dust", 0.38)),
    "construct": (("construct_scrap", 0.72), ("coal", 0.18)),
    "fungal": (("fungal_tissue", 0.72), ("bitterroot", 0.18)),
    "insect": (("chitin_fragment", 0.72), ("raw_spidersilk", 0.22)),
    "fiend": (("arcane_residue", 0.58), ("imp_ember_shard", 0.24)),
    "beast": (("rough_hide", 0.68), ("tough_sinew", 0.28)),
    "arcane": (("arcane_residue", 0.66), ("lavender_blossom", 0.14)),
    "humanoid": (("field_salvage", 0.68), ("construct_scrap", 0.12)),
    "creature": (("monster_trophy", 0.58), ("field_salvage", 0.14)),
}


def register_content_loot_items() -> None:
    known = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in CONTENT_LOOT_ITEMS if item.key not in known)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})


def _text_for(definition) -> str:
    return " ".join(
        str(value or "").lower()
        for value in (
            getattr(definition, "key", ""),
            getattr(definition, "name", ""),
            getattr(definition, "description", ""),
            getattr(definition, "short_description", ""),
        )
    )


def loot_family_for(definition) -> str:
    text = _text_for(definition)
    for family, tokens in _FAMILY_TOKENS:
        if any(token in text for token in tokens):
            return family
    return "creature"


def _quantity_ceiling(definition) -> int:
    xp = max(0, int(getattr(definition, "xp_reward", 0) or 0))
    if xp >= 300:
        return 3
    if xp >= 100:
        return 2
    return 1


def _is_named_or_boss(definition) -> bool:
    xp = max(0, int(getattr(definition, "xp_reward", 0) or 0))
    text = _text_for(definition)
    return xp >= 100 or any(
        token in text
        for token in (
            "boss", "captain", "commander", "marshal", "warden", "king", "queen",
            "saint", "governor", "champion", "master", "matriarch", "patriarch",
        )
    )


def _existing_entries(definition) -> tuple[LootTableEntry, ...]:
    proxy = SimpleNamespace(definition=definition)
    entries: list[LootTableEntry] = []
    for drop in economy._loot_for(proxy):
        quantity = max(1, int(drop.quantity))
        entries.append(LootTableEntry(drop.item_key, 1.0, quantity, quantity))
    for drop in economy_balance._secondary_for_enemy(proxy):
        quantity = max(1, int(drop.quantity))
        entries.append(
            LootTableEntry(
                drop.item_key,
                max(0.0, min(1.0, float(drop.chance))),
                quantity,
                quantity,
            )
        )
    return tuple(entries)


def _profile_entries(definition) -> tuple[LootTableEntry, ...]:
    family = loot_family_for(definition)
    ceiling = _quantity_ceiling(definition)
    boss_bonus = 0.12 if _is_named_or_boss(definition) else 0.0
    result: list[LootTableEntry] = []
    for index, (item_key, chance) in enumerate(_PROFILE_ITEMS[family]):
        if item_key not in crafting.ITEMS_BY_KEY:
            continue
        adjusted = min(0.95, chance + boss_bonus)
        result.append(
            LootTableEntry(
                item_key=item_key,
                chance=adjusted,
                min_quantity=1,
                max_quantity=ceiling if index == 0 else 1,
            )
        )
    return tuple(result)


def _merge_entries(entries: tuple[LootTableEntry, ...]) -> tuple[LootTableEntry, ...]:
    merged: dict[str, LootTableEntry] = {}
    order: list[str] = []
    for entry in entries:
        previous = merged.get(entry.item_key)
        if previous is None:
            merged[entry.item_key] = entry
            order.append(entry.item_key)
            continue
        merged[entry.item_key] = LootTableEntry(
            item_key=entry.item_key,
            chance=max(previous.chance, entry.chance),
            min_quantity=max(previous.min_quantity, entry.min_quantity),
            max_quantity=max(previous.max_quantity, entry.max_quantity),
        )
    return tuple(merged[item_key] for item_key in order)


def build_content_loot_table(definition) -> tuple[LootTableEntry, ...]:
    """Build one physical-corpse loot table while preserving authored drops."""
    key = str(getattr(definition, "key", ""))
    if key == "training_dummy" or (
        bool(getattr(definition, "tutorial", False))
        and int(getattr(definition, "xp_reward", 0) or 0) <= 0
    ):
        return ()

    table = _merge_entries(_existing_entries(definition) + _profile_entries(definition))
    if table:
        return table

    # CONTENT_LOOT_ITEMS are registered before production coverage is compiled,
    # so this is a final guard rather than the normal path.
    return (LootTableEntry("monster_trophy", 0.58, 1, _quantity_ceiling(definition)),)


def _killable_definitions() -> dict[str, object]:
    result: dict[str, object] = {}
    for key, definition in combat.ENEMIES_BY_KEY.items():
        if key == "training_dummy":
            continue
        result[str(key)] = definition

    for definition in getattr(mobile_npcs, "MOBILE_NPC_DEFINITIONS", ()):
        if not bool(getattr(definition, "aggressive", False)) and int(getattr(definition, "xp_reward", 0) or 0) <= 0:
            continue
        key = str(getattr(definition, "key", ""))
        if key:
            result.setdefault(key, definition)
    return result


def install_content_loot_tables() -> ContentLootCoverage:
    """Compile physical loot tables for every combat enemy currently registered.

    This runs after all production content installers. Hand-authored explicit
    corpse tables win; generated tables fill every remaining combat definition.
    Existing economy drops are carried forward, then a family profile adds a
    modest thematic chance so one-off enemies do not produce permanently empty
    corpses simply because their content module predates the corpse system.
    """
    register_content_loot_items()
    definitions = _killable_definitions()
    generated = 0
    preserved = 0

    for key, definition in definitions.items():
        if key in NPC_LOOT_TABLES and key not in _GENERATED_KEYS:
            preserved += 1
            continue
        register_loot_table(key, build_content_loot_table(definition))
        _GENERATED_KEYS.add(key)
        generated += 1

    missing = tuple(sorted(key for key in definitions if not NPC_LOOT_TABLES.get(key)))
    return ContentLootCoverage(
        killable_definitions=len(definitions),
        generated_tables=generated,
        authored_tables_preserved=preserved,
        missing_tables=missing,
    )


def generated_content_loot_keys() -> frozenset[str]:
    return frozenset(_GENERATED_KEYS)
