"""Regional alchemy: 270 cultural formulas, 30 discoveries, real material loops.

This is additive to the original potions, eight profession bands, and perfumery.
Learning flags are persisted on characters; books are ordinary transferable items.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.world as world
from mud.crafting import ConsumableEffect, ItemDefinition, ResourceNodeDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class Tradition:
    key: str
    name: str
    trainer: str
    hall: str
    gathering_room: str
    common: str
    rare: str
    source: str
    patterns: tuple[str, ...]
    clue: tuple[str, str, str]
    description: str


# The source column is the matter that this civilization traditionally alters.
# Pattern count determines exactly how many distinct recipes are in each region.
TRADITIONS: tuple[Tradition, ...] = (
    Tradition("goblin", "Goblin", "Zibrek Rustwise", "goblin_apothecary_blind",
              "goblin_patchwork_plaza", "Mireglass Sap", "Stormcap Spores",
              "iron_ore", ("Scrap Distillate", "Mire-Mend", "Bogskin Tonic",
              "Quickfinger Cordial", "Recast Scrap", "Bottlelight Crystal",
              "Verdigris Bloom"), ("stained mortar", "melted button",
              "crooked alembic"), "Brassgut salvage, fermentation, and clever reuse."),
    Tradition("dwarf", "Dwarven", "Vordun Embercaliper", "dwarf_workshop_tier",
              "dwarf_upper_freight_deck", "Crucible Salt", "Deepforge Flux",
              "iron_ore", ("Crucible Distillate", "Kiln-Heal", "Stoneguard Tonic",
              "Tempermind Cordial", "Recast Metal", "Hammerglass Crystal",
              "Forged Living Filament"), ("slag ledger", "hollow crucible",
              "seven-point anvil"), "Heat, purity, alloying, and permanent metal transmutation."),
    Tradition("forest", "Forest Elf", "Aelvren Dewthread", "forest_elf_hearthwalk",
              "forest_elf_greenway", "Heartseed Dew", "Silvermoss Pollen",
              "raw_cotton", ("Greenheart Distillate", "Sap-Mend", "Barkward Tonic",
              "Clearwater Cordial", "Recast Root", "Dewglass Crystal"),
              ("root diagram", "hollow seed", "grafted branch"),
              "Patient living reactions and renewal without wasting the forest."),
    Tradition("moon", "Moon Elf", "Othrielle Starvane", "moon_elf_alpine_light_garden",
              "moon_elf_wind_terrace", "Mirrorleaf Dew", "Starlit Silica",
              "moonsilver_ore", ("Moonwell Distillate", "Night-Mend", "Mirrorward Tonic",
              "Clearstar Cordial", "Recast Moonstone", "Prismglass Crystal"),
              ("silver chart", "blind mirror", "shattered prism"),
              "Reflective chemistry, celestial crystals, and carefully observed light."),
    Tradition("human", "Human", "Cevrina Glassward", "veyra_greenhall",
              "veyra_north_waterworks", "Greenhall Vitriol", "Cinder Solvent",
              "coal", ("Measured Distillate", "Physicker Draught", "Steelnerve Tonic",
              "Brightmind Cordial", "Recast Vitriol", "Retortglass Crystal",
              "Living Acidglass"), ("burned formula", "double retort",
              "sealed appendix"), "Precise measures, acids, glassware, and ambitious chemistry."),
    Tradition("troll", "Troll", "Ulvrekk Frostjaw", "troll_ember_hollow",
              "troll_frostroot_camp", "Frostbark Sap", "Whitehorn Rime",
              "rough_hide", ("Frostroot Distillate", "Long-Mend", "Hideward Tonic",
              "Stillmind Cordial", "Recast Icehide"),
              ("smoke knot", "old antler", "frozen cairn"),
              "Cold cures, survival extracts, and regenerative materials."),
    Tradition("undead", "Undead", "Nezath Palequill", "undead_chisel_market",
              "undead_desert_gate", "Sepulcher Dust", "Stillgrave Resin",
              "bone_chips", ("Sepulcher Distillate", "Restoration Phial",
              "Graveward Tonic", "Memory Cordial", "Recast Bone",
              "Mourningglass Crystal"), ("chiseled epitaph", "sealed urn",
              "unwritten obituary"), "Preservation, mineral memory, and reversible decay."),
    Tradition("spore", "Sporekin", "Mycela Manygills", "sporekin_lumen_hollow",
              "sporekin_mycelial_gallery", "Lumen Mycelium", "Crownspore Dust",
              "greenleaf", ("Lumen Distillate", "Spore-Mend",
              "Capward Tonic", "Threadmind Cordial", "Recast Mycelium"),
              ("spore calendar", "silent cap", "folded gill"),
              "Fermented growth, symbiosis, and unusual organic transformations."),
    Tradition("waymeet", "Crossroads", "Fenwick Sevenflasks",
              "waymeet_hammer_thread_row", "waymeet_briarcut_fields",
              "Roadside Amber", "Crossroad Salt", "cotton_cloth",
              ("Seven-Road Distillate", "Caravan-Mend", "Traveler Ward",
              "Roadwise Cordial", "Recast Wayglass"),
              ("caravan manifest", "fifth lantern mark", "blank mile map"),
              "Practical mixed traditions learned where the eight roads meet."),
)
BY_KEY = {t.key: t for t in TRADITIONS}

# 5 meaningful skill bands; specializations expand rather than replace the
# preexisting eight-band potion/perfumery ladder.
BANDS = (
    ("Apprentice", 5, 1, "greenleaf"),
    ("Field", 30, 2, "bitterroot"),
    ("Artisan", 60, 3, "lavender_blossom"),
    ("Master", 110, 6, "stariron_ore"),
    ("Astral", 170, 8, "astralite_ore"),
)
BOOK_PRICES = (0, 16, 55, 160, 420)
SECRET_SKILLS = (80, 135, 195)
GOLD_FIXATIVE_PRICE = 240
GOLD_BUYBACK_CEILING = 35  # priced again in sols.item_list_price


def lesson_flag(region: str, band: int) -> str:
    return f"alch_lesson_{region}_{band}"


def secret_flag(region: str, stage: int) -> str:
    return f"alch_secret_{region}_{stage}"


def book_key(region: str, band: int) -> str:
    return f"alch_text_{region}_{band}"


def sample_key(region: str, rare: bool = False) -> str:
    return f"alch_{region}_{'rare' if rare else 'common'}"


def output_key(region: str, band: int, pattern: int) -> str:
    if region == "dwarf" and band == 0 and pattern == 4:
        return "alch_lead_ingot"
    if region == "dwarf" and band == 4 and pattern == 4:
        return "alch_gold_ingot"
    return f"alch_{region}_{band}_{pattern}"


def _materials(*pairs: tuple[str, int]) -> tuple[MaterialRequirement, ...]:
    return tuple(MaterialRequirement(k, n) for k, n in pairs)


def _bonus(pattern: int, tier: int) -> CharacterStats:
    if pattern == 2:
        return CharacterStats(hp=1 + tier // 2, might=1 if tier >= 6 else 0)
    if pattern == 3:
        return CharacterStats(mind=1 + tier // 4, grace=1 if tier >= 6 else 0)
    return CharacterStats()


def _create_catalog() -> tuple[
    tuple[ItemDefinition, ...], tuple[ResourceNodeDefinition, ...],
    tuple[CraftingRecipe, ...],
]:
    items: list[ItemDefinition] = []
    nodes: list[ResourceNodeDefinition] = []
    recipes: list[CraftingRecipe] = []

    items.append(ItemDefinition(
        "alch_auric_fixative", "Licensed Auric Fixative",
        "A costly, single-use stabilizer supplied by a Dwarven assay house. "
        "Consumed whenever lead becomes real gold; not reproducible by ordinary distillation.",
        "reagent", tier=8,
    ))
    for t in TRADITIONS:
        for rare, suffix, name in ((False, "common", t.common), (True, "rare", t.rare)):
            key = sample_key(t.key, rare)
            items.append(ItemDefinition(key, name,
                f"A {'carefully gathered rare' if rare else 'locally gathered'} reagent of {t.name} alchemy.",
                "reagent", tier=3 if rare else 1))
            nodes.append(ResourceNodeDefinition(
                key=f"alch_node_{t.key}_{suffix}", name=f"{name} Deposit",
                gathering_skill_key="herbalism" if t.key not in {"dwarf", "moon", "human", "undead"} else "mining",
                output_item_key=key, minimum_skill=20 if rare else 0,
                tier=3 if rare else 1, design_status="regional_alchemy_gathering",
                region_hint=t.gathering_room,
            ))
        for bi, (rank, trivial, tier, tier_reagent) in enumerate(BANDS):
            items.append(ItemDefinition(
                book_key(t.key, bi), f"{rank} {t.name} Alchemy Manual",
                f"A portable, reusable {t.name.lower()} alchemical manuscript. "
                f"Study it to learn the {rank.lower()} formulas.",
                "book", tier=tier,
            ))
            essence = output_key(t.key, bi, 0)
            forged = output_key(t.key, bi, 4)
            for pi, pattern_name in enumerate(t.patterns):
                key = output_key(t.key, bi, pi)
                name = f"{rank} {t.name} {pattern_name}"
                station = "mortar_and_pestle" if bi == 0 and pi <= 3 else "alchemy_table"
                if pi == 0:
                    ingredients = _materials(
                        (sample_key(t.key), 2), ("spring_water", 1),
                        (tier_reagent, 1),
                    )
                elif pi == 1:
                    ingredients = _materials((essence, 1), ("greenleaf", 1),
                                             ("spring_water", 1))
                elif pi == 2:
                    ingredients = _materials((essence, 1), ("bitterroot", 1),
                                             ("spring_water", 1))
                elif pi == 3:
                    ingredients = _materials((essence, 1), ("grain_alcohol", 1),
                                             (sample_key(t.key, True), 1))
                elif pi == 4:
                    ingredients = _materials((t.source, 1), (essence, 2),
                        (sample_key(t.key, True), 2))
                elif pi == 5:
                    ingredients = _materials((forged, 1), ("arcane_residue", 1),
                                             (essence, 1))
                else:
                    ingredients = _materials((forged, 1), (sample_key(t.key, True), 2),
                                             ("astral_bloom_fiber" if bi == 4 else "greenleaf", 1))
                description = (
                    f"{t.description} Work with {t.common} and {t.rare}, "
                    f"using the {rank.lower()} tradition's controls."
                )
                if t.key == "dwarf" and pi == 4 and bi == 0:
                    name = "True Lead Ingot"
                    description = "Permanently transmute ordinary iron ore into a measured lead ingot."
                if t.key == "dwarf" and pi == 4 and bi == 4:
                    name = "True Gold Ingot"
                    ingredients = _materials(("alch_lead_ingot", 1),
                        (essence, 2), ("alch_auric_fixative", 1),
                        ("stariron_ingot", 1), (sample_key("moon", True), 2))
                    description = (
                        "Permanently transmute lead into real assay-grade gold. "
                        "A licensed fixative, Stariron and Moon Elf silica are consumed; "
                        "the gold can be traded or made into other items."
                    )
                if pi in (1, 2, 3):
                    items.append(ItemDefinition(
                        key, name, description, "potion",
                        consumable=ConsumableEffect(
                            use_mode="drink",
                            heal_hp=(12 + tier * 7) if pi == 1 else 0,
                            temporary_stat_bonuses=_bonus(pi, tier),
                            duration_ticks=15 + tier * 5,
                            effect_tags=("alchemy", t.key, f"band_{bi}", f"pattern_{pi}"),
                        ), tier=tier,
                    ))
                else:
                    items.append(ItemDefinition(
                        key, name, description if pi == 4 else
                        f"{t.description} A permanent {pattern_name.lower()} "
                        f"formed through the {rank.lower()} process.",
                        "reagent" if pi == 0 else "material",
                        tier=tier,
                    ))
                recipes.append(CraftingRecipe(
                    key=f"regional_{t.key}_{bi}_{pi}", trade_skill_key="alchemy",
                    output_item_key=key, minimum_skill=trivial + (pi // 2) * 3,
                    high_skill_quality_threshold=trivial + 30,
                    materials=ingredients, station_key=station,
                    description=description, design_status="regional_alchemy",
                    discovery_flag=lesson_flag(t.key, bi),
                ))

        # Each culture has three genuine secret formulas, each unlocked by
        # examining a different cultural clue at its mentor's workshop.
        for stage, skill in enumerate(SECRET_SKILLS):
            base = output_key(t.key, (2, 3, 4)[stage], 0)
            key = f"alch_secret_item_{t.key}_{stage}"
            name = (
                f"{t.name} Memory Elixir" if stage == 0 else
                f"{t.name} Living Conversion" if stage == 1 else
                f"{t.name} Eternal Reagent"
            )
            materials = (
                _materials((base, 1), (sample_key(t.key, True), 2),
                           ("grain_alcohol", 1))
                if stage == 0 else
                _materials((base, 2), (sample_key(t.key, True), 3),
                           ("stariron_ore" if stage == 1 else "astralite_ore", 1))
            )
            items.append(ItemDefinition(
                key, name,
                f"A hidden {t.name.lower()} formula preserved in an unmarked workshop clue.",
                "potion" if stage == 0 else "material",
                consumable=ConsumableEffect(
                    use_mode="drink", heal_hp=40,
                    temporary_stat_bonuses=CharacterStats(mind=2, love=1),
                    duration_ticks=45, effect_tags=("alchemy", "secret", t.key),
                ) if stage == 0 else None,
                tier=(4, 7, 8)[stage],
            ))
            recipes.append(CraftingRecipe(
                f"regional_secret_{t.key}_{stage}", "alchemy", key,
                skill, skill + 30, materials, station_key="alchemy_table",
                description=f"Recover the {name} formula from {t.name.lower()} workshop evidence.",
                design_status="regional_alchemy_secret",
                discovery_flag=secret_flag(t.key, stage),
            ))

    # A Philosopher's Stone is an optional legendary pursuit, NOT the gate on
    # ordinary high-level permanent gold transmutation.
    global_secrets = (
        ("philosophers_stone", "Philosopher's Stone", "material", 190,
         _materials(*[(sample_key(t.key, True), 2) for t in TRADITIONS],
                    ("alch_gold_ingot", 1), ("astralite_ingot", 1))),
        ("astralis_nectar", "Nectar of Nine Roads", "potion", 195,
         _materials(("alch_secret_item_goblin_0", 1),
                    ("alch_secret_item_forest_0", 1),
                    ("alch_secret_item_spore_0", 1),
                    ("alch_secret_item_waymeet_0", 1))),
        ("living_starbloom", "Living Starbloom", "material", 200,
         _materials(("alch_legend_philosophers_stone", 1),
                    ("astral_bloom_fiber", 2), ("alch_secret_item_moon_2", 1))),
    )
    for i, (slug, name, category, skill, materials) in enumerate(global_secrets):
        key = f"alch_legend_{slug}"
        items.append(ItemDefinition(
            key, name,
            "An extraordinary formula that marries the chemical traditions of Astralis.",
            category,
            consumable=ConsumableEffect(
                use_mode="drink", heal_hp=100,
                temporary_stat_bonuses=CharacterStats(
                    might=2, grace=2, mind=2, love=2, hp=5),
                duration_ticks=55, effect_tags=("alchemy", "legendary"),
            ) if category == "potion" else None,
            tier=8,
        ))
        recipes.append(CraftingRecipe(
            f"regional_legend_{slug}", "alchemy", key, skill, skill + 35,
            materials, station_key="alchemy_table",
            description=f"Combine several independent traditions to create {name}.",
            design_status="regional_alchemy_legendary",
            discovery_flag=secret_flag("legend", i),
        ))

    assert sum(len(t.patterns) for t in TRADITIONS) * len(BANDS) == 270
    assert len(recipes) == 300, len(recipes)
    assert len({r.key for r in recipes}) == len(recipes)
    assert len({i.key for i in items}) == len(items)
    return tuple(items), tuple(nodes), tuple(recipes)


ITEMS, NODES, RECIPES = _create_catalog()
RECIPES_BY_KEY = {r.key: r for r in RECIPES}
SECRET_CLUES = {
    (t.hall, clue): (t.key, stage)
    for t in TRADITIONS for stage, clue in enumerate(t.clue)
}
# The legendary clues are on existing shared journeys.
SECRET_CLUES.update({
    ("waymeet_fifth_lantern", "nine-fold ledger"): ("legend", 0),
    ("waymeet_gloam_mouth", "forgotten condensation"): ("legend", 1),
    ("greywake_riftfield", "impossible root"): ("legend", 2),
})

# The two extra recipes give True Gold an actual player-crafting outlet.
GOLDWORK_ITEMS = (
    ItemDefinition("alch_sunleaf", "Alchemical Gold Leaf",
        "Thin, durable gold leaf for tailors and enchanters.", "material", tier=7),
    ItemDefinition(
        "alch_gilded_travel_coat", "Sun-Gilt Roadkeeper Coat",
        "A practical traveling coat sewn with genuine alchemical gold leaf.",
        "equipment", equipment=EquipmentItem(
            "Sun-Gilt Roadkeeper Coat", "body", armor_class=3,
            stat_bonuses=CharacterStats(grace=2, love=2),
        ), tier=7,
    ),
    ItemDefinition(
        "alch_auric_scrying_focus", "Auric Scrying Focus",
        "A focus pairing real alchemical gold with Moon Elf prismglass.",
        "equipment", equipment=EquipmentItem(
            "Auric Scrying Focus", "off_hand",
            stat_bonuses=CharacterStats(mind=4, love=2),
        ), tier=8,
    ),
)
GOLDWORK_RECIPES = (
    CraftingRecipe("regional_beat_gold_leaf", "alchemy", "alch_sunleaf",
        165, 190, _materials(("alch_gold_ingot", 1), ("moonflax_fiber", 1)),
        station_key="alchemy_table",
        description="Beat genuine alchemical gold into a resilient metallic leaf.",
        design_status="regional_alchemy", discovery_flag=lesson_flag("dwarf", 4)),
    CraftingRecipe(
        "regional_sew_sungilt_roadkeeper", "tailoring",
        "alch_gilded_travel_coat", 130, 160,
        _materials(("alch_sunleaf", 1), ("silk_cloth", 2),
                   ("astral_thread", 1)),
        station_key="loom",
        description="Sew permanent transmuted gold leaf into a durable silk travel coat.",
        design_status="regional_alchemy_collaboration",
    ),
    CraftingRecipe(
        "regional_enchant_auric_focus", "enchanting",
        "alch_auric_scrying_focus", 155, 185,
        _materials(("alch_gold_ingot", 1), ("alch_moon_2_5", 1),
                   ("arcane_residue", 2), ("moonsteel_ingot", 1)),
        station_key="enchanting_table",
        description="Bind true gold and Moon Elf prismglass into a stable magical focus.",
        design_status="regional_alchemy_collaboration",
    ),
)


def install_regional_alchemy_content() -> dict[str, int]:
    """Install after profession expansion and authored room content, once."""
    if getattr(crafting, "_regional_alchemy_installed", False):
        return catalog_counts()

    missing_rooms = [t.hall for t in TRADITIONS if t.hall not in world.ROOMS_BY_KEY]
    if missing_rooms:
        raise RuntimeError(f"Regional alchemy trainers need real rooms: {missing_rooms}")

    expansion._register_items(ITEMS + GOLDWORK_ITEMS)
    expansion._register_nodes(NODES)
    expansion._register_recipes(RECIPES + GOLDWORK_RECIPES)

    for t in TRADITIONS:
        room = world.ROOMS_BY_KEY[t.hall]
        npc_key = f"regional_alchemist_{t.key}"
        if npc_key not in world.NPCS_BY_KEY:
            npc = NpcDefinition(
                npc_key, t.trainer,
                f"a {t.name.lower()} master alchemist arranging carefully labeled reagents",
                t.hall, "regional alchemy trainer",
                (f"{t.trainer} says: '{t.description} "
                 "Use STUDY ALCHEMY here; advanced manuals can be bought and shared.'",),
            )
            world.NPCS += (npc,)
            world.NPCS_BY_KEY[npc_key] = npc
        if npc_key not in room.npc_keys:
            world.ROOMS_BY_KEY[t.hall] = replace(
                room, npc_keys=room.npc_keys + (npc_key,),
            )
        current = economy.ROOM_STATIONS.get(t.hall, ())
        economy.ROOM_STATIONS[t.hall] = current + tuple(
            x for x in ("mortar_and_pestle", "alchemy_table")
            if x not in current
        )
        if t.gathering_room not in world.ROOMS_BY_KEY:
            raise RuntimeError(f"Regional alchemy resource room missing: {t.gathering_room}")
        current = economy.ROOM_RESOURCE_NODE_KEYS.get(t.gathering_room, ())
        additions = tuple(
            f"alch_node_{t.key}_{suffix}"
            for suffix in ("common", "rare")
            if f"alch_node_{t.key}_{suffix}" not in current
        )
        economy.ROOM_RESOURCE_NODE_KEYS[t.gathering_room] = current + additions

    # Resource-sustainable refining requires actual basic water across regions.
    for t in TRADITIONS:
        current = economy.ROOM_RESOURCE_NODE_KEYS.get(t.hall, ())
        if "fresh_water_source" not in current:
            economy.ROOM_RESOURCE_NODE_KEYS[t.hall] = current + ("fresh_water_source",)

    missing = [
        (r.key, m.item_key) for r in (*RECIPES, *GOLDWORK_RECIPES)
        for m in r.materials if m.item_key not in crafting.ITEMS_BY_KEY
    ]
    if missing:
        raise RuntimeError(f"Regional alchemy ingredients missing: {missing[:12]}")
    crafting._regional_alchemy_installed = True
    return catalog_counts()


def catalog_counts() -> dict[str, int]:
    return {
        **{t.key: sum(
            r.key.startswith(f"regional_{t.key}_") or
            r.key.startswith(f"regional_secret_{t.key}_")
            for r in RECIPES
        ) for t in TRADITIONS},
        "secret": sum(r.design_status == "regional_alchemy_secret" for r in RECIPES),
        "legendary": sum(r.design_status == "regional_alchemy_legendary" for r in RECIPES),
        "total": len(RECIPES),
    }
