from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.crafting import ItemDefinition
from mud.mechanics import PRIEST_DEITIES_BY_KEY, PROGRESSION_RULES
from mud.stats import CharacterStats, EquipmentItem


EQUIPMENT_SLOTS: tuple[str, ...] = (
    "head",
    "chest",
    "legs",
    "feet",
    "hands",
    "main_hand",
    "off_hand",
)

SLOT_LABELS = {
    "head": "Head",
    "chest": "Chest",
    "legs": "Legs",
    "feet": "Feet",
    "hands": "Hands",
    "main_hand": "Main Hand",
    "off_hand": "Off Hand",
}

_SLOT_ALIASES = {
    "head": "head",
    "helmet": "head",
    "hood": "head",
    "chest": "chest",
    "body": "chest",
    "torso": "chest",
    "armor": "chest",
    "legs": "legs",
    "leg": "legs",
    "pants": "legs",
    "leggings": "legs",
    "feet": "feet",
    "foot": "feet",
    "boots": "feet",
    "shoes": "feet",
    "hands": "hands",
    "hand": "hands",
    "gloves": "hands",
    "gauntlets": "hands",
    "main": "main_hand",
    "main hand": "main_hand",
    "main_hand": "main_hand",
    "weapon": "main_hand",
    "wield": "main_hand",
    "off": "off_hand",
    "off hand": "off_hand",
    "off_hand": "off_hand",
    "shield": "off_hand",
}


@dataclass(frozen=True, slots=True)
class LiveEquipmentRules:
    """The first live equipment pass for Dreams of the Fallen.

    Every race and class can wear every ordinary item. Early and mid-game gear is
    deliberately raw-stat driven. Scripted effects remain a supported data hook,
    but are reserved for rare/endgame equipment rather than baseline progression.
    """

    universal_race_access: bool = True
    universal_class_access: bool = True
    ordinary_gear_is_stat_only: bool = True
    special_effects_reserved_for_rare_endgame_gear: bool = True
    equipment_persists_between_sessions: bool = True
    equipment_changes_blocked_during_combat: bool = True


LIVE_EQUIPMENT_RULES = LiveEquipmentRules()


def normalize_slot(slot: str) -> str:
    normalized = slot.strip().lower().replace("-", " ").replace("_", " ")
    canonical = _SLOT_ALIASES.get(normalized)
    if canonical is None:
        raise ValueError(f"Unknown equipment slot: {slot}")
    return canonical


def _eq(
    name: str,
    slot: str,
    *,
    ac: int = 0,
    might: int = 0,
    grace: int = 0,
    love: int = 0,
    mind: int = 0,
    hp: int = 0,
) -> EquipmentItem:
    return EquipmentItem(
        name=name,
        slot=slot,
        armor_class=ac,
        stat_bonuses=CharacterStats(
            might=might,
            grace=grace,
            love=love,
            mind=mind,
            hp=hp,
        ),
    )


def _item(
    key: str,
    name: str,
    description: str,
    slot: str,
    *,
    ac: int = 0,
    might: int = 0,
    grace: int = 0,
    love: int = 0,
    mind: int = 0,
    hp: int = 0,
) -> ItemDefinition:
    return ItemDefinition(
        key=key,
        name=name,
        description=description,
        category="equipment",
        equipment=_eq(
            name,
            slot,
            ac=ac,
            might=might,
            grace=grace,
            love=love,
            mind=mind,
            hp=hp,
        ),
        tier=0,
    )


# Small, place-specific rewards spread through the starter content already in
# the game. None has a scripted proc, damage rider, thorn effect, or other
# special behavior. The point of this pass is to make ordinary gear legible.
EARLY_EQUIPMENT_ITEMS: tuple[ItemDefinition, ...] = (
    _item(
        "human_demon_gate_buckler",
        "Demon Gate Buckler",
        "A compact blackwood shield faced with dark iron and issued near the Human capital's outer gate. It is plain, durable, and sized for crowded streets.",
        "off_hand",
        ac=2,
    ),
    _item(
        "human_blackwall_drill_blade",
        "Blackwall Drill Blade",
        "A serviceable training sword from the Blackwall grounds, sharpened enough for real work after the practice edge was removed.",
        "main_hand",
        might=1,
    ),
    _item(
        "human_sootstep_boots",
        "Sootstep Boots",
        "Low black boots with flexible soles made for old brick stairs, wet alleys, and the uneven stone of the Lower Wards.",
        "feet",
        ac=1,
        grace=1,
    ),
    _item(
        "forest_fernward_gloves",
        "Fernward Tending Gloves",
        "Soft hide gloves with open fingertips and reinforced palms, made for handling wet roots without crushing delicate growth.",
        "hands",
        love=1,
    ),
    _item(
        "forest_greenway_hood",
        "Greenway Hood",
        "A quiet green hood stitched with a narrow leaf-patterned edge. It breaks up the outline of the wearer's head among branches without trying to look martial.",
        "head",
        ac=1,
        grace=1,
    ),
    _item(
        "forest_rainpool_legwraps",
        "Rainpool Legwraps",
        "Layered barkcloth and soft hide wraps treated to shed water while moving through wet roots and shallow runoff.",
        "legs",
        ac=1,
        love=1,
    ),
    _item(
        "dwarf_pressure_gauntlets",
        "Pressure Gallery Gauntlets",
        "Heavy work gloves with heat-resistant palms and brass-backed knuckles, stamped as safe for supervised steam-line work.",
        "hands",
        ac=1,
        might=1,
    ),
    _item(
        "dwarf_chainmark_workboots",
        "Chainmark Work Boots",
        "Steel-toed boots with thick nailed soles and a stamped lift-inspection mark on each heel.",
        "feet",
        ac=2,
        hp=1,
    ),
    _item(
        "goblin_patchwork_scrapknife",
        "Patchwork Scrapknife",
        "A narrow working knife rebuilt from three unrelated blades, two handle scales, and one very confident rivet pattern.",
        "main_hand",
        might=1,
        grace=1,
    ),
    _item(
        "goblin_reedfen_patchvest",
        "Reedfen Patchvest",
        "An ugly but effective vest of waxed hide, stitched reed mat, and small scrap plates placed only where they actually help.",
        "chest",
        ac=2,
        hp=1,
    ),
    _item(
        "troll_trail_legwraps",
        "Frostroot Trail Legwraps",
        "Thick hide wraps cut high at the knee so a hunter can cross crusted snow without catching every low branch and drift edge.",
        "legs",
        ac=1,
        grace=1,
    ),
    _item(
        "troll_camp_hide_vest",
        "Frostroot Hide Vest",
        "A patched winter vest made from the same practical hide stock used to repair Frostroot's shelters after the raid.",
        "chest",
        ac=2,
        hp=2,
    ),
    _item(
        "troll_emberhide_gloves",
        "Emberhide Gloves",
        "Smoke-dark gloves with thick palms for moving warm stone, split fuel, and rough shelter material in bitter weather.",
        "hands",
        ac=1,
        might=1,
    ),
    _item(
        "troll_elk_tread_boots",
        "Elk-Tread Boots",
        "Broad-soled winter boots patterned after the stable footing used by Frostroot's working elk on packed snow.",
        "feet",
        ac=1,
        grace=1,
    ),
    _item(
        "troll_windscar_buckler",
        "Windscar Buckler",
        "A small round shield reinforced with a Dwarven freight-brace ring and a Troll hide grip. It is a practical object born from a solved problem, not a trophy.",
        "off_hand",
        ac=2,
        hp=1,
    ),
    _item(
        "sporekin_lumen_mantle",
        "Lumen Mantle",
        "A layered mantle of cured fungal fiber that holds a faint cool sheen like the walls of the Lumen Hollow.",
        "chest",
        ac=1,
        mind=1,
    ),
    _item(
        "sporekin_memory_hood",
        "Memory-Cap Hood",
        "A soft hood woven from pale root fiber and patterned after the four remembered pulses of the forgotten grove.",
        "head",
        ac=1,
        love=1,
        mind=1,
    ),
)


@dataclass(frozen=True, slots=True)
class EquipmentReward:
    key: str
    item_key: str
    reason: str
    race_key: str | None = None
    quest_key: str | None = None
    required_flag: str | None = None

    @property
    def claim_flag(self) -> str:
        return f"equipment_reward_{self.key}"


EQUIPMENT_REWARDS: tuple[EquipmentReward, ...] = (
    EquipmentReward(
        "human_gate_buckler",
        "human_demon_gate_buckler",
        "Answering the cathedral summons earns a piece of ordinary gate equipment instead of ceremonial finery.",
        race_key="human",
        quest_key="human_cathedral_summons",
    ),
    EquipmentReward(
        "human_drill_blade",
        "human_blackwall_drill_blade",
        "Finishing the Blackwall exercises leaves you with a real blade built on the same simple training pattern.",
        race_key="human",
        quest_key="human_combat_training",
    ),
    EquipmentReward(
        "human_sootstep_boots",
        "human_sootstep_boots",
        "Tracing the Lower Wards mark earns footwear better suited to the city beneath the polished avenues.",
        race_key="human",
        quest_key="human_lower_wards_investigation",
    ),
    EquipmentReward(
        "forest_tending_gloves",
        "forest_fernward_gloves",
        "The Heartseed lesson leaves you with the same kind of gloves the Circle uses for careful tending.",
        race_key="forest_elf",
        quest_key="forest_elf_heartseed_patience",
    ),
    EquipmentReward(
        "forest_greenway_hood",
        "forest_greenway_hood",
        "Completing the old river walk earns a quiet travel hood from the Circle's common stores.",
        race_key="forest_elf",
        quest_key="forest_elf_first_walk",
    ),
    EquipmentReward(
        "forest_rainpool_wraps",
        "forest_rainpool_legwraps",
        "Restoring the rain-pool flow earns practical wet-weather legwraps used by local keepers.",
        race_key="forest_elf",
        quest_key="forest_elf_rainpool_balance",
    ),
    EquipmentReward(
        "dwarf_pressure_gauntlets",
        "dwarf_pressure_gauntlets",
        "Closing a first civic work order includes basic protective hand gear from the public workshop stores.",
        race_key="dwarf",
        quest_key="dwarf_first_work_order",
    ),
    EquipmentReward(
        "dwarf_chainmark_boots",
        "dwarf_chainmark_workboots",
        "The completed lift inspection qualifies you for ordinary freight-deck work boots.",
        race_key="dwarf",
        quest_key="dwarf_first_work_order",
    ),
    EquipmentReward(
        "goblin_scrapknife",
        "goblin_patchwork_scrapknife",
        "Your first completed salvage transaction comes with a repaired working knife that embodies Junk City's whole philosophy.",
        race_key="goblin",
        quest_key="goblin_from_scrap_to_claim",
    ),
    EquipmentReward(
        "goblin_patchvest",
        "goblin_reedfen_patchvest",
        "Returning alive from the First Piling earns a vest built for the wet routes beyond the painted line.",
        race_key="goblin",
        quest_key="goblin_beyond_painted_line",
    ),
    EquipmentReward(
        "troll_trail_wraps",
        "troll_trail_legwraps",
        "Frostroot's scouts recognize that you chose to follow the retreat and came back with facts.",
        race_key="troll",
        required_flag="troll_first_duty_track_complete",
    ),
    EquipmentReward(
        "troll_camp_vest",
        "troll_camp_hide_vest",
        "Frostroot's shelter crews remember that you chose food, roof, and heat while the camp was still bleeding.",
        race_key="troll",
        required_flag="troll_first_duty_camp_complete",
    ),
    EquipmentReward(
        "troll_emberhide_gloves",
        "troll_emberhide_gloves",
        "A Fire Before Pride ends with practical gloves for the cold work the lesson was actually about.",
        race_key="troll",
        quest_key="troll_fire_before_pride",
    ),
    EquipmentReward(
        "troll_elk_tread_boots",
        "troll_elk_tread_boots",
        "Tracks Have Reasons leaves you with broad winter boots built for patient movement around animals and sign.",
        race_key="troll",
        quest_key="troll_tracks_have_reasons",
    ),
    EquipmentReward(
        "troll_windscar_buckler",
        "troll_windscar_buckler",
        "Solving Brannik's freight problem produces a useful buckler from spare brace iron and hide rather than a decorative trophy.",
        race_key="troll",
        quest_key="troll_what_they_expected",
    ),
    EquipmentReward(
        "sporekin_lumen_mantle",
        "sporekin_lumen_mantle",
        "Reaching the breathing world leaves you with a simple mantle woven from the underground colony's common fiber.",
        race_key="sporekin",
        quest_key="sporekin_first_call",
    ),
    EquipmentReward(
        "sporekin_memory_hood",
        "sporekin_memory_hood",
        "Restoring the forgotten pulse earns a hood patterned after the old sequence you recovered.",
        race_key="sporekin",
        quest_key="sporekin_forgotten_pulse",
    ),
)


def _universal_live_item(item: ItemDefinition) -> ItemDefinition:
    equipment = item.equipment
    if equipment is None:
        return item

    # Preserve old slot strings in legacy item constants so old data/tests remain
    # readable; the live system canonicalizes them when equipping. Restrictions,
    # however, are removed from the live item catalog: everyone can wear everything.
    equipment = replace(
        equipment,
        allowed_races=frozenset(),
        allowed_classes=frozenset(),
    )

    # The Troll tutorial spear predates the live stat system. Give it the small
    # physical bonus expected from the first real weapon without adding a proc.
    if item.key == "frostroot_notched_spear":
        equipment = replace(
            equipment,
            stat_bonuses=equipment.stat_bonuses.plus(CharacterStats(might=1)),
        )
    return replace(item, equipment=equipment)


def install_equipment_content() -> None:
    """Register starter-region gear and make the live catalog universally wearable."""
    known = {item.key for item in crafting.ITEMS}
    additions = tuple(item for item in EARLY_EQUIPMENT_ITEMS if item.key not in known)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions

    # Rebuild the tuple and mutate the shared dictionary in-place. Session modules
    # that imported ITEMS_BY_KEY keep seeing the same dictionary object.
    normalized = tuple(_universal_live_item(item) for item in crafting.ITEMS)
    crafting.ITEMS = normalized
    crafting.ITEMS_BY_KEY.clear()
    crafting.ITEMS_BY_KEY.update({item.key: item for item in normalized})


def ensure_equipment_storage(database) -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_equipment (
                character_id INTEGER NOT NULL,
                slot_key TEXT NOT NULL,
                item_key TEXT NOT NULL,
                equipped_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, slot_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )


def equipped_item_keys(database, character_id: int) -> dict[str, str]:
    ensure_equipment_storage(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT slot_key, item_key FROM character_equipment WHERE character_id = ? ORDER BY slot_key",
            (character_id,),
        ).fetchall()
    return {str(row["slot_key"]): str(row["item_key"]) for row in rows}


def set_equipped_item(database, character_id: int, slot_key: str, item_key: str) -> None:
    canonical = normalize_slot(slot_key)
    ensure_equipment_storage(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_equipment (character_id, slot_key, item_key)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, slot_key) DO UPDATE SET
                item_key = excluded.item_key,
                equipped_at = CURRENT_TIMESTAMP
            """,
            (character_id, canonical, item_key),
        )


def clear_equipped_slot(database, character_id: int, slot_key: str) -> bool:
    canonical = normalize_slot(slot_key)
    ensure_equipment_storage(database)
    with database.connect() as db:
        cursor = db.execute(
            "DELETE FROM character_equipment WHERE character_id = ? AND slot_key = ?",
            (character_id, canonical),
        )
    return bool(cursor.rowcount)


def sanitize_equipment(database, character_id: int) -> dict[str, str]:
    """Drop stale rows if an equipped item no longer exists in inventory/catalog."""
    equipped = equipped_item_keys(database, character_id)
    for slot, item_key in tuple(equipped.items()):
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        if (
            definition is None
            or definition.equipment is None
            or database.item_quantity(character_id, item_key) <= 0
        ):
            clear_equipped_slot(database, character_id, slot)
            equipped.pop(slot, None)
            continue
        try:
            expected_slot = normalize_slot(definition.equipment.slot)
        except ValueError:
            clear_equipped_slot(database, character_id, slot)
            equipped.pop(slot, None)
            continue
        if expected_slot != slot:
            clear_equipped_slot(database, character_id, slot)
            set_equipped_item(database, character_id, expected_slot, item_key)
            equipped.pop(slot, None)
            equipped[expected_slot] = item_key
    return equipped


def equipped_definitions(database, character_id: int) -> dict[str, ItemDefinition]:
    result: dict[str, ItemDefinition] = {}
    for slot, item_key in sanitize_equipment(database, character_id).items():
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        if definition is not None and definition.equipment is not None:
            result[slot] = definition
    return result


def equipment_totals(database, character_id: int) -> tuple[CharacterStats, int]:
    stats = CharacterStats()
    armor_class = 0
    for definition in equipped_definitions(database, character_id).values():
        assert definition.equipment is not None
        stats = stats.plus(definition.equipment.stat_bonuses)
        armor_class += max(0, definition.equipment.armor_class)
    return stats, armor_class


def _reward_is_eligible(session, reward: EquipmentReward) -> bool:
    if session.character is None:
        return False
    if reward.race_key and session.character.race != reward.race_key:
        return False
    flags = session.database.list_flags(session.character.id)
    if reward.claim_flag in flags:
        return False
    if reward.required_flag and reward.required_flag not in flags:
        return False
    if reward.quest_key:
        quest = session.database.get_quest(session.character.id, reward.quest_key)
        if not quest or quest.get("status") != "completed":
            return False
    return True


def claim_new_equipment_rewards(session) -> tuple[EquipmentReward, ...]:
    if session.character is None:
        return ()
    claimed: list[EquipmentReward] = []
    for reward in EQUIPMENT_REWARDS:
        if not _reward_is_eligible(session, reward):
            continue
        if session.database.item_quantity(session.character.id, reward.item_key) <= 0:
            session.database.add_item(session.character.id, reward.item_key, 1)
        session.database.grant_flag(session.character.id, reward.claim_flag)
        claimed.append(reward)
    return tuple(claimed)


def _bootstrap_equipment(session) -> None:
    if session.character is None:
        return
    character_id = session.character.id
    equipped = sanitize_equipment(session.database, character_id)

    if "main_hand" not in equipped and session.database.item_quantity(character_id, "starter_weapon") > 0:
        set_equipped_item(session.database, character_id, "main_hand", "starter_weapon")
        equipped["main_hand"] = "starter_weapon"

    if (
        "chest" not in equipped
        and session.database.item_quantity(character_id, "brute_training_harness") > 0
    ):
        # The harness is issued to Brutes, but once an item exists in inventory it
        # has no class restriction. This auto-equip is only starter convenience.
        set_equipped_item(session.database, character_id, "chest", "brute_training_harness")
        equipped["chest"] = "brute_training_harness"

    # The desperate Troll opening tells the player to grab a spear under pressure.
    # If the Basic Starting Weapon is still in hand, automatically put the spear
    # where the tutorial fiction says it is rather than adding another command.
    if (
        session.database.item_quantity(character_id, "frostroot_notched_spear") > 0
        and equipped.get("main_hand") in {None, "starter_weapon"}
        and "troll_raid_weapon_taken" in session.database.list_flags(character_id)
    ):
        set_equipped_item(session.database, character_id, "main_hand", "frostroot_notched_spear")


def apply_equipment_to_combatant(session) -> None:
    if session.character is None or session.combatant is None:
        return
    bonus, armor_class = equipment_totals(session.database, session.character.id)
    total = session.character.stats.plus(bonus)

    old_max_hp = session.combatant.max_hp
    old_max_mana = session.combatant.max_mana
    new_max_hp = total.maximum_hp(25)
    new_max_mana = total.maximum_mana(20)

    if new_max_hp > old_max_hp:
        session.combatant.current_hp += new_max_hp - old_max_hp
    session.combatant.current_hp = min(session.combatant.current_hp, new_max_hp)

    if new_max_mana > old_max_mana:
        session.combatant.current_mana += new_max_mana - old_max_mana
    session.combatant.current_mana = min(session.combatant.current_mana, new_max_mana)

    session.combatant.stats = total
    session.combatant.armor_class = armor_class
    session.combatant.max_hp = new_max_hp
    session.combatant.max_mana = new_max_mana


def _stat_parts(equipment: EquipmentItem) -> list[str]:
    parts: list[str] = []
    if equipment.armor_class:
        parts.append(f"AC +{equipment.armor_class}")
    for key, label in (
        ("might", "Might"),
        ("grace", "Grace"),
        ("love", "Love"),
        ("mind", "Mind"),
        ("hp", "HP"),
    ):
        value = getattr(equipment.stat_bonuses, key)
        if value:
            sign = "+" if value > 0 else ""
            parts.append(f"{label} {sign}{value}")
    return parts or ["no stat modifiers"]


def _owned_equipment_matches(session, target: str) -> list[ItemDefinition]:
    assert session.character is not None
    wanted = target.strip().lower().replace("_", " ")
    matches: list[ItemDefinition] = []
    for row in session.database.list_items(session.character.id):
        if int(row["quantity"]) <= 0:
            continue
        key = str(row["item_key"])
        definition = crafting.ITEMS_BY_KEY.get(key)
        if definition is None or definition.equipment is None:
            continue
        names = {definition.key.lower().replace("_", " "), definition.name.lower()}
        if wanted in names:
            return [definition]
        if any(wanted in name for name in names):
            matches.append(definition)
    return matches


def _equipped_target_slot(session, target: str) -> str | None:
    assert session.character is not None
    try:
        return normalize_slot(target)
    except ValueError:
        pass
    wanted = target.strip().lower().replace("_", " ")
    for slot, item_key in equipped_item_keys(session.database, session.character.id).items():
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        if definition is None:
            continue
        if wanted in {definition.name.lower(), definition.key.lower().replace("_", " ")}:
            return slot
    return None


async def _show_equipment(session) -> None:
    assert session.character is not None
    equipped = equipped_definitions(session.database, session.character.id)
    bonus, armor_class = equipment_totals(session.database, session.character.id)
    await session.send("\r\n--- Equipment ---\r\n")
    for slot in EQUIPMENT_SLOTS:
        definition = equipped.get(slot)
        if definition is None:
            await session.send(f"{SLOT_LABELS[slot]:<10}: [empty]\r\n")
            continue
        assert definition.equipment is not None
        await session.send(
            f"{SLOT_LABELS[slot]:<10}: {definition.name} ({', '.join(_stat_parts(definition.equipment))})\r\n"
        )
    await session.send(
        "Totals     : "
        f"AC {armor_class}; Might {bonus.might:+d}; Grace {bonus.grace:+d}; "
        f"Love {bonus.love:+d}; Mind {bonus.mind:+d}; HP {bonus.hp:+d}\r\n"
    )
    await session.send("Commands: EQUIP <item>, UNEQUIP <slot or item>, COMPARE <item>.\r\n")


async def _show_inventory(session) -> None:
    assert session.character is not None
    equipped = equipped_item_keys(session.database, session.character.id)
    reverse: dict[str, list[str]] = {}
    for slot, item_key in equipped.items():
        reverse.setdefault(item_key, []).append(SLOT_LABELS[slot])

    items = session.database.list_items(session.character.id)
    await session.send("\r\n--- Inventory ---\r\n")
    if not items:
        await session.send("Empty.\r\n")
        return
    for row in items:
        item_key = str(row["item_key"])
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        name = definition.name if definition else item_key
        suffix = ""
        if item_key in reverse:
            suffix = " [EQUIPPED: " + ", ".join(reverse[item_key]) + "]"
        elif definition and definition.equipment:
            suffix = f" [gear: {SLOT_LABELS[normalize_slot(definition.equipment.slot)]}]"
        await session.send(f"{int(row['quantity'])}x {name}{suffix}\r\n")


async def _show_item_detail(session, target: str) -> None:
    matches = _owned_equipment_matches(session, target)
    if not matches:
        await session.send("You are not carrying equipment by that name.\r\n")
        return
    if len(matches) > 1:
        await session.send("That matches more than one item: " + ", ".join(item.name for item in matches) + ".\r\n")
        return
    definition = matches[0]
    assert definition.equipment is not None
    await session.send(
        f"\r\n{definition.name}\r\n{definition.description}\r\n"
        f"Slot: {SLOT_LABELS[normalize_slot(definition.equipment.slot)]}\r\n"
        f"Stats: {', '.join(_stat_parts(definition.equipment))}\r\n"
        "Wearability: universal - every race and class can use this item.\r\n"
    )
    if definition.equipment.scripted_effects:
        await session.send("Special effects: " + ", ".join(definition.equipment.scripted_effects) + "\r\n")


async def _compare_item(session, target: str) -> None:
    assert session.character is not None
    matches = _owned_equipment_matches(session, target)
    if not matches:
        await session.send("You are not carrying equipment by that name.\r\n")
        return
    if len(matches) > 1:
        await session.send("That matches more than one item: " + ", ".join(item.name for item in matches) + ".\r\n")
        return
    candidate = matches[0]
    assert candidate.equipment is not None
    slot = normalize_slot(candidate.equipment.slot)
    current_key = equipped_item_keys(session.database, session.character.id).get(slot)
    current = crafting.ITEMS_BY_KEY.get(current_key or "")
    if current is None or current.equipment is None:
        await session.send(
            f"{candidate.name} would fill your empty {SLOT_LABELS[slot]} slot: {', '.join(_stat_parts(candidate.equipment))}.\r\n"
        )
        return
    c = candidate.equipment
    e = current.equipment
    diff = c.stat_bonuses.plus(
        CharacterStats(
            might=-e.stat_bonuses.might,
            grace=-e.stat_bonuses.grace,
            love=-e.stat_bonuses.love,
            mind=-e.stat_bonuses.mind,
            hp=-e.stat_bonuses.hp,
        )
    )
    ac_diff = c.armor_class - e.armor_class
    parts = [f"AC {ac_diff:+d}"]
    for key, label in (("might", "Might"), ("grace", "Grace"), ("love", "Love"), ("mind", "Mind"), ("hp", "HP")):
        value = getattr(diff, key)
        if value:
            parts.append(f"{label} {value:+d}")
    await session.send(
        f"{candidate.name} vs {current.name} ({SLOT_LABELS[slot]}): " + ", ".join(parts) + ".\r\n"
    )


async def _equip(session, target: str) -> None:
    assert session.character is not None
    if session.active_enemy is not None:
        await session.send("You cannot change equipment while fighting. FLEE or finish the fight first.\r\n")
        return
    matches = _owned_equipment_matches(session, target)
    if not matches:
        await session.send("You are not carrying equippable gear by that name.\r\n")
        return
    if len(matches) > 1:
        await session.send("Be more specific: " + ", ".join(item.name for item in matches) + ".\r\n")
        return
    definition = matches[0]
    assert definition.equipment is not None
    slot = normalize_slot(definition.equipment.slot)
    old_key = equipped_item_keys(session.database, session.character.id).get(slot)
    if old_key == definition.key:
        await session.send(f"{definition.name} is already equipped in {SLOT_LABELS[slot]}.\r\n")
        return
    set_equipped_item(session.database, session.character.id, slot, definition.key)
    apply_equipment_to_combatant(session)
    replaced_name = crafting.ITEMS_BY_KEY.get(old_key).name if old_key in crafting.ITEMS_BY_KEY else None
    if replaced_name:
        await session.send(f"You equip {definition.name} in {SLOT_LABELS[slot]}, replacing {replaced_name}.\r\n")
    else:
        await session.send(f"You equip {definition.name} in {SLOT_LABELS[slot]}.\r\n")
    await session.send(f"Stats: {', '.join(_stat_parts(definition.equipment))}.\r\n")
    await session.send_client_state()
    await _send_equipment_gmcp(session)


async def _unequip(session, target: str) -> None:
    assert session.character is not None
    if session.active_enemy is not None:
        await session.send("You cannot change equipment while fighting. FLEE or finish the fight first.\r\n")
        return
    slot = _equipped_target_slot(session, target)
    if slot is None:
        await session.send("Nothing equipped matches that slot or item name.\r\n")
        return
    equipped = equipped_item_keys(session.database, session.character.id)
    item_key = equipped.get(slot)
    definition = crafting.ITEMS_BY_KEY.get(item_key or "")
    if not item_key:
        await session.send(f"Your {SLOT_LABELS[slot]} slot is already empty.\r\n")
        return
    clear_equipped_slot(session.database, session.character.id, slot)
    apply_equipment_to_combatant(session)
    await session.send(f"You unequip {definition.name if definition else item_key} from {SLOT_LABELS[slot]}.\r\n")
    await session.send_client_state()
    await _send_equipment_gmcp(session)


async def _show_live_stats(session) -> None:
    assert session.character is not None
    bonus, armor_class = equipment_totals(session.database, session.character.id)
    total = session.character.stats.plus(bonus)
    race = RACES_BY_KEY.get(session.character.race or "")
    character_class = CLASSES_BY_KEY.get(session.character.character_class or "")
    await session.send(
        f"\r\nName : {session.character.name}\r\n"
        f"Race : {race.name if race else session.character.race}\r\n"
        f"Class: {character_class.name if character_class else session.character.character_class}\r\n"
        + (
            f"Deity: {PRIEST_DEITIES_BY_KEY.get(session.character.deity_key).name if session.character.deity_key in PRIEST_DEITIES_BY_KEY else (session.character.deity_key or 'not yet chosen')}\r\n"
            if session.character.character_class == "priest"
            else ""
        )
        + f"Level: {session.character.level}\r\n"
        f"XP   : {session.character.experience}\r\n"
        f"Next : {PROGRESSION_RULES.cumulative_xp_for_level(session.character.level + 1)} total XP\r\n"
        "\r\n--- Stats (base + equipment = total) ---\r\n"
        f"Might: {session.character.might} {bonus.might:+d} = {total.might}\r\n"
        f"Grace: {session.character.grace} {bonus.grace:+d} = {total.grace}\r\n"
        f"Love : {session.character.love} {bonus.love:+d} = {total.love}\r\n"
        f"Mind : {session.character.mind} {bonus.mind:+d} = {total.mind}\r\n"
        f"HP   : {session.character.hp_stat} {bonus.hp:+d} = {total.hp}\r\n"
        f"AC   : {armor_class} (entirely equipment-derived)\r\n"
        f"Mana bonus: {total.love + total.mind}\r\n"
    )
    if race and race.passive_name:
        await session.send(f"Passive: {race.passive_name} - {race.passive_description}\r\n")


async def _send_equipment_gmcp(session) -> None:
    if session.character is None or not getattr(session.telnet, "gmcp_enabled", False):
        return
    equipped = equipped_definitions(session.database, session.character.id)
    bonus, armor_class = equipment_totals(session.database, session.character.id)
    payload = {
        "slots": {
            slot: {
                "item_key": equipped[slot].key if slot in equipped else "",
                "name": equipped[slot].name if slot in equipped else "",
            }
            for slot in EQUIPMENT_SLOTS
        },
        "armor_class": armor_class,
        "bonus_might": bonus.might,
        "bonus_grace": bonus.grace,
        "bonus_love": bonus.love,
        "bonus_mind": bonus.mind,
        "bonus_hp": bonus.hp,
    }
    await session.telnet.send_gmcp("Dreams.Equipment", payload)


async def _announce_rewards(session, rewards: tuple[EquipmentReward, ...]) -> None:
    for reward in rewards:
        definition = crafting.ITEMS_BY_KEY[reward.item_key]
        assert definition.equipment is not None
        await session.send(
            f"\r\nEquipment earned: {definition.name} ({SLOT_LABELS[normalize_slot(definition.equipment.slot)]}; "
            f"{', '.join(_stat_parts(definition.equipment))}).\r\n"
            f"{reward.reason}\r\n"
            f"It is now in your inventory. EQUIP {definition.name.upper()} when you want to wear it.\r\n"
        )


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_equipment_runtime(player_session_class) -> None:
    """Install persistent slot equipment outside every existing race runtime."""
    install_equipment_content()
    if getattr(player_session_class, "_live_equipment_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None:
            return
        ensure_equipment_storage(self.database)
        rewards = claim_new_equipment_rewards(self)
        _bootstrap_equipment(self)
        apply_equipment_to_combatant(self)
        if rewards:
            await _announce_rewards(self, rewards)
        await self.send(
            "\r\nEquipment is active: HEAD, CHEST, LEGS, FEET, HANDS, MAIN HAND, and OFF HAND. "
            "Type EQUIPMENT to inspect your worn gear.\r\n"
        )
        await self.send_client_state()
        await _send_equipment_gmcp(self)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"equipment", "equip", "eq", "gear", "worn"}:
            await _show_equipment(self)
            return
        if normalized in {"inventory", "inv", "i"}:
            await _show_inventory(self)
            return
        if normalized in {"score", "status", "sheet", "stats"}:
            await _show_live_stats(self)
            return
        if normalized.startswith("equip "):
            await _equip(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("wear "):
            await _equip(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("wield "):
            await _equip(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("unequip "):
            await _unequip(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("remove "):
            await _unequip(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("compare "):
            await _compare_item(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized.startswith("item ") or normalized.startswith("inspect item "):
            target = command.strip().split(maxsplit=1)[1]
            if normalized.startswith("inspect item "):
                target = command.strip()[len("inspect item "):]
            await _show_item_detail(self, target)
            return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is None:
            return

        # Existing quest/race runtimes may have just granted an item or completed
        # a milestone. Reconcile after every normal command so equipment rewards
        # arrive immediately without editing every quest module individually.
        rewards = claim_new_equipment_rewards(self)
        before = equipped_item_keys(self.database, self.character.id)
        _bootstrap_equipment(self)
        after = equipped_item_keys(self.database, self.character.id)
        apply_equipment_to_combatant(self)
        if rewards:
            await _announce_rewards(self, rewards)
        if before != after and after.get("main_hand") == "frostroot_notched_spear":
            await self.send("The Notched Hunting Spear replaces your basic weapon in your Main Hand.\r\n")
        if normalized in {"help", "?"}:
            await self.send(
                "Equipment commands: EQUIPMENT/GEAR, INVENTORY, EQUIP/WEAR/WIELD <item>, "
                "UNEQUIP/REMOVE <slot or item>, COMPARE <item>, ITEM <item>. "
                "All races and classes can wear all ordinary equipment; early gear is stat-only.\r\n"
            )
        await self.send_client_state()
        await _send_equipment_gmcp(self)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._live_equipment_runtime_installed = True
