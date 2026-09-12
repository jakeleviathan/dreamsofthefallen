from __future__ import annotations

from dataclasses import dataclass

import mud.class_progression as class_progression
import mud.crafting as crafting
import mud.quests as quests
import mud.session as session_module
from mud.blackreed_holdfast import BLACKREED_ROOM_KEYS
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.gloamworks_dungeon import GLOAMWORKS_ROOM_KEYS
from mud.gravewatch_keep import GRAVEWATCH_KEEP_ROOM_KEYS
from mud.quests import QuestDefinition
from mud.sablewater_reach import DROWNED_ROOM_KEYS
from mud.stats import CharacterStats, EquipmentItem
from mud.veyra_city import VEYRA_FIVE_WAYS_KEY
from mud.veyra_underclock import UNDERCLOCK_ROOM_KEYS
from mud.waymeet_frontier import WAYMEET_SCRIP_KEY


# Class progression should become world behavior rather than a menu of spells.
# These commissions deliberately use dungeons that already matter to the shared
# level-8 world. They do not create isolated class tutorial rooms.
ALL_FIELD_DUNGEON_ROOMS = frozenset(
    (*BLACKREED_ROOM_KEYS, *GLOAMWORKS_ROOM_KEYS, *DROWNED_ROOM_KEYS, *UNDERCLOCK_ROOM_KEYS, *GRAVEWATCH_KEEP_ROOM_KEYS)
)


@dataclass(frozen=True, slots=True)
class ClassCommission:
    class_key: str
    quest: QuestDefinition
    first_step: str
    completion_flag: str
    field_rooms: frozenset[str]
    plate_item_key: str
    field_note: str


BRUTE_COMMISSION = ClassCommission(
    class_key="brute",
    quest=QuestDefinition(
        key="veyra_brute_field_commission",
        name="Stand Where It Matters",
        style="structured",
        minimum_level=8,
        description=(
            "Sable-of-Five-Ways sends the Brute back into a real occupied or undead fort. The test is not raw damage: "
            "interrupt a dangerous enemy, then deliberately hold the line while that enemy is actually focused on you."
        ),
        objective_steps=(
            ("field_control", "In Blackreed Holdfast or Gravewatch Keep, use SHIELD BASH during a real fight."),
            ("field_guard", "In Blackreed or Gravewatch, use HOLD THE LINE while you are currently at the top of that enemy's hate list."),
            ("report", "Return to Sable-of-Five-Ways in Veyra and use CLASS COMMISSION or TALK SABLE."),
            ("complete", "You proved that a Brute's job is control and protection, not simply taking the first swing."),
        ),
    ),
    first_step="field_control",
    completion_flag="veyra_brute_field_commission_complete",
    field_rooms=frozenset((*BLACKREED_ROOM_KEYS, *GRAVEWATCH_KEEP_ROOM_KEYS)),
    plate_item_key="lineholder_commission_plate",
    field_note="Blackreed Holdfast or Gravewatch Keep",
)

WIZARD_COMMISSION = ClassCommission(
    class_key="wizard",
    quest=QuestDefinition(
        key="veyra_wizard_field_commission",
        name="Control Before Power",
        style="structured",
        minimum_level=8,
        description=(
            "The Five Ways instructors want evidence that a Wizard can shape a dangerous fight before trying to end it. "
            "Use control in a hostile works, then deliberately prepare a burst window under pressure."
        ),
        objective_steps=(
            ("field_control", "In the Gloamworks or Underclock, use FROSTBIND during a real fight."),
            ("field_burst", "In the Gloamworks or Underclock, use ARCANE SURGE while actively engaged with an enemy."),
            ("report", "Return to Sable-of-Five-Ways in Veyra and use CLASS COMMISSION or TALK SABLE."),
            ("complete", "You proved that precise control and prepared force belong to the same Wizard toolkit."),
        ),
    ),
    first_step="field_control",
    completion_flag="veyra_wizard_field_commission_complete",
    field_rooms=frozenset((*GLOAMWORKS_ROOM_KEYS, *UNDERCLOCK_ROOM_KEYS)),
    plate_item_key="focus_commission_plate",
    field_note="the Gloamworks or Veyra Underclock",
)

DRUID_COMMISSION = ClassCommission(
    class_key="druid",
    quest=QuestDefinition(
        key="veyra_druid_field_commission",
        name="Keep the Road Alive",
        style="structured",
        minimum_level=8,
        description=(
            "The Druid commission treats care as field work. Keep another adventurer recovering while danger is live, "
            "then protect the person who has actually drawn the enemy's attention."
        ),
        objective_steps=(
            ("field_recovery", "In Blackreed or the Drowned Tollhouse, cast REJUVENATION on an injured party member other than yourself."),
            ("field_protection", "In Blackreed or the Drowned Tollhouse, cast BARKSKIN on another party member who currently holds enemy aggro."),
            ("report", "Return to Sable-of-Five-Ways in Veyra and use CLASS COMMISSION or TALK SABLE."),
            ("complete", "You proved that Druid support is about keeping a moving group functional under pressure."),
        ),
    ),
    first_step="field_recovery",
    completion_flag="veyra_druid_field_commission_complete",
    field_rooms=frozenset((*BLACKREED_ROOM_KEYS, *DROWNED_ROOM_KEYS)),
    plate_item_key="steward_commission_plate",
    field_note="Blackreed Holdfast or the Drowned Tollhouse",
)

PRIEST_COMMISSION = ClassCommission(
    class_key="priest",
    quest=QuestDefinition(
        key="veyra_priest_field_commission",
        name="No One Left Untended",
        style="structured",
        minimum_level=8,
        description=(
            "Whatever path a Priest follows, the Five Ways field standard is practical: identify the person in trouble, "
            "stabilize them efficiently, then keep a whole group from sliding toward collapse."
        ),
        objective_steps=(
            ("field_triage", "In any shared dungeon, use MEND ALLY on another party member who is at 65% HP or lower."),
            ("field_group", "In any shared dungeon fight, use PRAYER OF RENEWAL with at least two living party members present and somebody injured."),
            ("report", "Return to Sable-of-Five-Ways in Veyra and use CLASS COMMISSION or TALK SABLE."),
            ("complete", "You proved the shared field discipline beneath the different Priest paths: notice need and answer it."),
        ),
    ),
    first_step="field_triage",
    completion_flag="veyra_priest_field_commission_complete",
    field_rooms=ALL_FIELD_DUNGEON_ROOMS,
    plate_item_key="care_commission_plate",
    field_note="any shared dungeon",
)

NECROMANCER_COMMISSION = ClassCommission(
    class_key="necromancer",
    quest=QuestDefinition(
        key="veyra_necromancer_field_commission",
        name="Make the Dead Useful",
        style="structured",
        minimum_level=8,
        description=(
            "Gravewatch gives the Necromancer an unusually blunt test: command your own dead deliberately in a fortress full of dead soldiers, "
            "then protect yourself long enough to keep that control from becoming panic."
        ),
        objective_steps=(
            ("field_command", "In Gravewatch Keep, use GRAVE COMMAND during combat while your Skeleton is active."),
            ("field_ward", "In Gravewatch Keep, use BONE WARD while actively engaged with an enemy."),
            ("report", "Return to Sable-of-Five-Ways in Veyra and use CLASS COMMISSION or TALK SABLE."),
            ("complete", "You proved that Necromancy is sustained control of danger, not merely producing another corpse."),
        ),
    ),
    first_step="field_command",
    completion_flag="veyra_necromancer_field_commission_complete",
    field_rooms=frozenset(GRAVEWATCH_KEEP_ROOM_KEYS),
    plate_item_key="gravework_commission_plate",
    field_note="Gravewatch Keep",
)

CLASS_COMMISSIONS: tuple[ClassCommission, ...] = (
    BRUTE_COMMISSION,
    WIZARD_COMMISSION,
    DRUID_COMMISSION,
    PRIEST_COMMISSION,
    NECROMANCER_COMMISSION,
)
CLASS_COMMISSIONS_BY_CLASS = {commission.class_key: commission for commission in CLASS_COMMISSIONS}
CLASS_COMMISSIONS_BY_QUEST = {commission.quest.key: commission for commission in CLASS_COMMISSIONS}


# The physical plate is intentional. The class player earns it in the field, but
# can hand the plate and other materials to a specialist crafter. That preserves
# the player-economy goal instead of requiring every Brute to also be a smith or
# every Priest to also be a Tailor.
COMMISSION_PLATES: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        "lineholder_commission_plate", "Lineholder Commission Plate",
        "A stamped Five Ways plate issued after a Brute demonstrates real threat control in the field. It is made to be built into a serious shield, not displayed on a wall.",
        "crafting_component", tier=2,
    ),
    ItemDefinition(
        "focus_commission_plate", "Focus Commission Plate",
        "A narrow Five Ways plate etched with two marks: CONTROL first, FORCE second. It is sized for a circlet fitting.",
        "crafting_component", tier=2,
    ),
    ItemDefinition(
        "steward_commission_plate", "Steward Commission Plate",
        "A light pierced plate awarded for practical field care. Its holes are deliberately placed so a Tailor can stitch it into layered working cloth.",
        "crafting_component", tier=2,
    ),
    ItemDefinition(
        "care_commission_plate", "Care Commission Plate",
        "A Five Ways plate stamped after a Priest demonstrates triage and group recovery under real danger. It is a work credential designed to become part of working vestments.",
        "crafting_component", tier=2,
    ),
    ItemDefinition(
        "gravework_commission_plate", "Gravework Commission Plate",
        "A darkened Five Ways plate issued after disciplined field necromancy in Gravewatch. The edge is drilled for binding into a wand or staff ferrule.",
        "crafting_component", tier=2,
    ),
)


ADVANCED_SIGNATURE_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        key="bastion_lineholder_shield",
        name="Bastion Lineholder Shield",
        description=(
            "A rebuilt Lineholder Shield faced with Gravewatch garrison iron and centered on an Underclock governor bearing. "
            "It is heavier, calmer in the hand, and built for somebody who expects pressure to stay on them."
        ),
        category="equipment",
        equipment=EquipmentItem(
            "Bastion Lineholder Shield", "off_hand", armor_class=5,
            stat_bonuses=CharacterStats(might=2, hp=4),
            scripted_effects=("Brute affinity: preserves the Lineholder Heavy Strike threat and extended Hold the Line affinity.",),
        ),
        tier=3,
    ),
    ItemDefinition(
        key="clockglass_circlet",
        name="Clockglass Circlet",
        description=(
            "The original Coldglass focus has been rebuilt around drowned brass and a precision Underclock bearing. "
            "Nothing about it increases spectacle; it simply makes a narrow spell line easier to hold under pressure."
        ),
        category="equipment",
        equipment=EquipmentItem(
            "Clockglass Circlet", "head", armor_class=2,
            stat_bonuses=CharacterStats(mind=4, grace=1),
            scripted_effects=("Wizard affinity: preserves the Coldglass damaging-spell affinity.",),
        ),
        tier=3,
    ),
    ItemDefinition(
        key="floodroot_mantle",
        name="Floodroot Mantle",
        description=(
            "A Briarheart Mantle rebuilt around a stopped Auditor gear and Bitterroot pockets from the floodplain. "
            "The weight is distributed across the shoulders so a field healer can keep moving while carrying useful material."
        ),
        category="equipment",
        equipment=EquipmentItem(
            "Floodroot Mantle", "chest", armor_class=3,
            stat_bonuses=CharacterStats(love=4, hp=3),
            scripted_effects=("Druid affinity: preserves the Briarheart healing affinity.",),
        ),
        tier=3,
    ),
    ItemDefinition(
        key="bellwarden_vestments",
        name="Bellwarden Vestments",
        description=(
            "Resonant Vestments reinforced with old Gravewatch iron and a second carefully mounted safety cog. "
            "The result looks more like durable field clothing than ceremonial robes, which is exactly the point."
        ),
        category="equipment",
        equipment=EquipmentItem(
            "Bellwarden Vestments", "chest", armor_class=3,
            stat_bonuses=CharacterStats(love=4, mind=2, hp=2),
            scripted_effects=("Priest affinity: preserves the Resonant Vestments healing affinity.",),
        ),
        tier=3,
    ),
    ItemDefinition(
        key="grave_regent_wand",
        name="Grave-Regent Wand",
        description=(
            "The Regent-Bone Wand has been given a Gravewatch iron spine and a precision Auditor gear at its balance point. "
            "It feels less like a fetish object and more like a tool designed for repeated, deliberate command."
        ),
        category="equipment",
        equipment=EquipmentItem(
            "Grave-Regent Wand", "main_hand",
            stat_bonuses=CharacterStats(mind=4, hp=2),
            scripted_effects=("Necromancer affinity: preserves the Regent-Bone Grave Command and Wither affinity.",),
        ),
        tier=3,
    ),
)


ADVANCED_SIGNATURE_RECIPES: tuple[CraftingRecipe, ...] = (
    CraftingRecipe(
        key="forge_bastion_lineholder_shield",
        trade_skill_key="blacksmithing",
        output_item_key="bastion_lineholder_shield",
        minimum_skill=18,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement("lineholder_shield", 1),
            MaterialRequirement("lineholder_commission_plate", 1),
            MaterialRequirement("gravewatch_old_garrison_iron", 2),
            MaterialRequirement("underclock_governor_bearing", 1),
        ),
        station_key="forge",
        description="Rebuild a proven Lineholder Shield with Gravewatch iron and an Underclock bearing.",
        design_status="live_class_world_upgrade",
    ),
    CraftingRecipe(
        key="forge_clockglass_circlet",
        trade_skill_key="blacksmithing",
        output_item_key="clockglass_circlet",
        minimum_skill=18,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement("coldglass_circlet", 1),
            MaterialRequirement("focus_commission_plate", 1),
            MaterialRequirement("underclock_governor_bearing", 1),
            MaterialRequirement("drowned_brass_scrap", 2),
        ),
        station_key="forge",
        description="Rebuild a Coldglass Circlet around precision civic-machine metal.",
        design_status="live_class_world_upgrade",
    ),
    CraftingRecipe(
        key="sew_floodroot_mantle",
        trade_skill_key="tailoring",
        output_item_key="floodroot_mantle",
        minimum_skill=18,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement("briarheart_mantle", 1),
            MaterialRequirement("steward_commission_plate", 1),
            MaterialRequirement("brass_auditor_gear", 1),
            MaterialRequirement("bitterroot", 2),
        ),
        station_key="loom",
        description="Rebuild a Briarheart Mantle around floodplain medicine and a stable brass weight.",
        design_status="live_class_world_upgrade",
    ),
    CraftingRecipe(
        key="sew_bellwarden_vestments",
        trade_skill_key="tailoring",
        output_item_key="bellwarden_vestments",
        minimum_skill=18,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement("resonant_vestments", 1),
            MaterialRequirement("care_commission_plate", 1),
            MaterialRequirement("gloamworks_resonant_cog", 1),
            MaterialRequirement("gravewatch_old_garrison_iron", 1),
        ),
        station_key="loom",
        description="Reinforce Resonant Vestments with field-proven metal and a second safety resonance.",
        design_status="live_class_world_upgrade",
    ),
    CraftingRecipe(
        key="forge_grave_regent_wand",
        trade_skill_key="blacksmithing",
        output_item_key="grave_regent_wand",
        minimum_skill=20,
        high_skill_quality_threshold=48,
        materials=(
            MaterialRequirement("regent_bone_wand", 1),
            MaterialRequirement("gravework_commission_plate", 1),
            MaterialRequirement("gravewatch_old_garrison_iron", 1),
            MaterialRequirement("brass_auditor_gear", 1),
            MaterialRequirement("bone_chips", 2),
        ),
        station_key="forge",
        description="Give the Regent-Bone Wand a durable Gravewatch spine and a precise civic-machine balance.",
        design_status="live_class_world_upgrade",
    ),
)

ADVANCED_GEAR_BY_CLASS = {
    "brute": ("bastion_lineholder_shield", "forge_bastion_lineholder_shield"),
    "wizard": ("clockglass_circlet", "forge_clockglass_circlet"),
    "druid": ("floodroot_mantle", "sew_floodroot_mantle"),
    "priest": ("bellwarden_vestments", "sew_bellwarden_vestments"),
    "necromancer": ("grave_regent_wand", "forge_grave_regent_wand"),
}

# The upgraded piece counts as the earlier affinity piece. The stronger raw stats
# come from the item itself; this avoids quietly inventing a second spell-rank
# system inside equipment while still making the upgrade preserve class identity.
ADVANCED_AFFINITY_EQUIVALENTS = {
    "lineholder_shield": "bastion_lineholder_shield",
    "coldglass_circlet": "clockglass_circlet",
    "briarheart_mantle": "floodroot_mantle",
    "resonant_vestments": "bellwarden_vestments",
    "regent_bone_wand": "grave_regent_wand",
}

MATERIAL_SOURCE_HINTS = {
    "lineholder_shield": "the first Brute signature recipe (CLASS GEAR)",
    "coldglass_circlet": "the first Wizard signature recipe (CLASS GEAR)",
    "briarheart_mantle": "the first Druid signature recipe (CLASS GEAR)",
    "resonant_vestments": "the first Priest signature recipe (CLASS GEAR)",
    "regent_bone_wand": "the first Necromancer signature recipe (CLASS GEAR)",
    "lineholder_commission_plate": "the Brute Five Ways field commission",
    "focus_commission_plate": "the Wizard Five Ways field commission",
    "steward_commission_plate": "the Druid Five Ways field commission",
    "care_commission_plate": "the Priest Five Ways field commission",
    "gravework_commission_plate": "the Necromancer Five Ways field commission",
    "gravewatch_old_garrison_iron": "Gravewatch Keep enemies and officers",
    "underclock_governor_bearing": "the Cinder Governor in the Veyra Underclock",
    "drowned_brass_scrap": "Drowned Tollhouse enemies",
    "brass_auditor_gear": "the Brass Auditor in the Drowned Tollhouse",
    "gloamworks_resonant_cog": "the Gloamworks",
    "bitterroot": "Herbalism nodes in Forest Elf lands or Sablewater",
    "bone_chips": "common Necromancer catalyst stock and bone sources",
}


@dataclass(frozen=True, slots=True)
class AbilityUseContext:
    room_key: str
    in_combat: bool
    target_is_other: bool = False
    target_hp_fraction: float = 1.0
    target_was_top_threat: bool = False
    caster_was_top_threat: bool = False
    living_party_count: int = 1
    injured_party_count: int = 0
    active_pet: str | None = None


def next_commission_step(
    commission: ClassCommission,
    current_step: str,
    ability_key: str,
    context: AbilityUseContext,
) -> str | None:
    """Return the next quest step only when a successful ability use proves the role."""
    if context.room_key not in commission.field_rooms or not context.in_combat:
        return None

    if commission.class_key == "brute":
        if current_step == "field_control" and ability_key == "shield_bash":
            return "field_guard"
        if current_step == "field_guard" and ability_key == "hold_the_line" and context.caster_was_top_threat:
            return "report"

    elif commission.class_key == "wizard":
        if current_step == "field_control" and ability_key == "frostbind":
            return "field_burst"
        if current_step == "field_burst" and ability_key == "arcane_surge":
            return "report"

    elif commission.class_key == "druid":
        if (
            current_step == "field_recovery"
            and ability_key == "rejuvenation"
            and context.target_is_other
            and context.target_hp_fraction < 1.0
        ):
            return "field_protection"
        if (
            current_step == "field_protection"
            and ability_key == "barkskin"
            and context.target_is_other
            and context.target_was_top_threat
        ):
            return "report"

    elif commission.class_key == "priest":
        if (
            current_step == "field_triage"
            and ability_key == "mend_ally"
            and context.target_is_other
            and context.target_hp_fraction <= 0.65
        ):
            return "field_group"
        if (
            current_step == "field_group"
            and ability_key == "prayer_of_renewal"
            and context.living_party_count >= 2
            and context.injured_party_count >= 1
        ):
            return "report"

    elif commission.class_key == "necromancer":
        if current_step == "field_command" and ability_key == "grave_command" and context.active_pet == "skeleton":
            return "field_ward"
        if current_step == "field_ward" and ability_key == "bone_ward":
            return "report"

    return None


def install_class_world_content() -> None:
    """Register field commissions and the next craftable signature-gear tier."""
    class_progression.install_class_progression_content()

    known_quests = set(quests.QUESTS_BY_KEY)
    quest_additions = tuple(c.quest for c in CLASS_COMMISSIONS if c.quest.key not in known_quests)
    if quest_additions:
        quests.QUESTS = quests.QUESTS + quest_additions
        quests.QUESTS_BY_KEY.update({quest.key: quest for quest in quest_additions})

    additions = tuple(
        item for item in (*COMMISSION_PLATES, *ADVANCED_SIGNATURE_ITEMS)
        if item.key not in crafting.ITEMS_BY_KEY
    )
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    blacksmith_additions = tuple(
        recipe for recipe in ADVANCED_SIGNATURE_RECIPES
        if recipe.trade_skill_key == "blacksmithing" and recipe.key not in crafting.BLACKSMITHING_RECIPES_BY_KEY
    )
    if blacksmith_additions:
        crafting.BLACKSMITHING_RECIPES = crafting.BLACKSMITHING_RECIPES + blacksmith_additions
        crafting.BLACKSMITHING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in blacksmith_additions})

    tailoring_additions = tuple(
        recipe for recipe in ADVANCED_SIGNATURE_RECIPES
        if recipe.trade_skill_key == "tailoring" and recipe.key not in crafting.TAILORING_RECIPES_BY_KEY
    )
    if tailoring_additions:
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + tailoring_additions
        crafting.TAILORING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in tailoring_additions})

    recipe_additions = tuple(
        recipe for recipe in ADVANCED_SIGNATURE_RECIPES if recipe.key not in crafting.RECIPES_BY_KEY
    )
    if recipe_additions:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + recipe_additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in recipe_additions})

    session_module.ALL_RECIPES = crafting.ALL_RECIPES


def _install_advanced_affinity_equivalents() -> None:
    if getattr(class_progression, "_class_world_affinity_equivalents_installed", False):
        return
    previous = class_progression._has_affinity_item

    def has_affinity(session, item_key: str, class_key: str) -> bool:
        if previous(session, item_key, class_key):
            return True
        advanced = ADVANCED_AFFINITY_EQUIVALENTS.get(item_key)
        character = getattr(session, "character", None)
        return bool(
            advanced
            and character is not None
            and character.character_class == class_key
            and advanced in class_progression._equipped_item_keys(session)
        )

    class_progression._has_affinity_item = has_affinity
    class_progression._class_world_affinity_equivalents_installed = True


def _commission_for_session(session) -> ClassCommission | None:
    character = getattr(session, "character", None)
    if character is None:
        return None
    return CLASS_COMMISSIONS_BY_CLASS.get(character.character_class or "")


def _current_commission_quest(session, commission: ClassCommission):
    return session.database.get_quest(session.character.id, commission.quest.key)


def _capture_context(session, target_text: str) -> AbilityUseContext:
    character = session.character
    enemy = getattr(session, "active_enemy", None)
    top_target = enemy.hate.top_target() if enemy is not None else None
    target = class_progression._ally_here(session, target_text) if target_text else None
    target_fraction = 1.0
    target_is_other = False
    target_was_top = False
    if target is not None and getattr(target, "combatant", None) is not None:
        target_is_other = target is not session
        if target.combatant.max_hp > 0:
            target_fraction = target.combatant.current_hp / target.combatant.max_hp
        if target_is_other and getattr(target, "character", None) is not None:
            target_was_top = top_target == target.character.id

    living = class_progression._support_targets(session)
    injured = sum(1 for member in living if member.combatant.current_hp < member.combatant.max_hp)
    active_pet = session.database.get_active_pet(character.id)
    return AbilityUseContext(
        room_key=character.current_room or "",
        in_combat=enemy is not None,
        target_is_other=target_is_other,
        target_hp_fraction=target_fraction,
        target_was_top_threat=target_was_top,
        caster_was_top_threat=bool(enemy is not None and top_target == character.id),
        living_party_count=len(living),
        injured_party_count=injured,
        active_pet=active_pet,
    )


async def _record_successful_role_use(session, ability, context: AbilityUseContext) -> None:
    commission = _commission_for_session(session)
    if commission is None:
        return
    quest = _current_commission_quest(session, commission)
    if not quest or quest.get("status") != "active":
        return
    current_step = str(quest.get("current_step") or "")
    next_step = next_commission_step(commission, current_step, ability.key, context)
    if next_step is None:
        return
    session.database.advance_quest(session.character.id, commission.quest.key, next_step)
    objective = commission.quest.objective_for_step(next_step)
    await session.send(f"\r\n*** CLASS COMMISSION UPDATED: {commission.quest.name} ***\r\n")
    if next_step == "report":
        await session.send("Field proof accepted. Return to Sable-of-Five-Ways in Veyra.\r\n")
    elif objective:
        await session.send(objective + "\r\n")


async def _complete_commission(session, commission: ClassCommission) -> None:
    quest = _current_commission_quest(session, commission)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "report":
        return
    old_level = session.character.level
    session.database.complete_quest(session.character.id, commission.quest.key)
    session.database.grant_flag(session.character.id, commission.completion_flag)
    session.database.add_item(session.character.id, commission.plate_item_key, 1)
    session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 2)
    new_level = session.database.add_experience(session.character.id, 250)
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed
    plate = crafting.ITEMS_BY_KEY[commission.plate_item_key]
    advanced_key, recipe_key = ADVANCED_GEAR_BY_CLASS[commission.class_key]
    advanced = crafting.ITEMS_BY_KEY[advanced_key]
    await session.send(
        f"\r\n*** CLASS COMMISSION COMPLETE: {commission.quest.name} ***\r\n"
        "Sable signs the field report instead of giving you a speech. Your actions already supplied the argument.\r\n"
        f"Reward: 250 XP, 2 Waymeet Trade Scrip, and 1x {plate.name}.\r\n"
        f"That plate is a crafting component for {advanced.name}. You can craft it yourself or trade the plate and materials to an artisan.\r\n"
        f"Recipe: {recipe_key}. Type CLASS GEAR PATH for the full material route.\r\n"
    )
    if new_level > old_level:
        await session.send(f"The commission advances you to level {new_level}.\r\n")


async def _show_commission(session) -> None:
    commission = _commission_for_session(session)
    if commission is None:
        await session.send("Your class does not have a Five Ways field commission.\r\n")
        return
    quest = _current_commission_quest(session, commission)
    here = session.character.current_room == VEYRA_FIVE_WAYS_KEY

    if quest is None:
        if session.character.level < commission.quest.minimum_level:
            await session.send(
                f"Five Ways field commissions begin at level {commission.quest.minimum_level}. Your current level is {session.character.level}.\r\n"
            )
            return
        if not here:
            await session.send(
                f"Your {session.character.character_class.title()} field commission is issued by Sable-of-Five-Ways in Veyra's Five Ways Yard.\r\n"
            )
            return
        session.database.start_quest(session.character.id, commission.quest.key, commission.first_step)
        objective = commission.quest.objective_for_step(commission.first_step)
        await session.send(
            f"\r\nNew class commission: {commission.quest.name}\r\n{commission.quest.description}\r\n"
            f"Field site: {commission.field_note}.\r\n{objective or ''}\r\n"
            "This is real field work. The commission advances only when the required ability succeeds during combat.\r\n"
        )
        return

    if quest.get("status") == "completed":
        await session.send(
            f"{commission.quest.name}: COMPLETE. Your field qualification is permanent. Type CLASS GEAR PATH for the equipment route it opened.\r\n"
        )
        return

    step = str(quest.get("current_step") or commission.first_step)
    if step == "report" and here:
        await _complete_commission(session, commission)
        return
    objective = commission.quest.objective_for_step(step)
    await session.send(f"\r\n--- Class Commission: {commission.quest.name} ---\r\n")
    await session.send((objective or "Continue the field commission.") + "\r\n")
    if step == "report":
        await session.send("Return to Sable-of-Five-Ways in Veyra to close the commission.\r\n")
    else:
        await session.send(f"Field site: {commission.field_note}.\r\n")


async def _show_gear_path(session) -> None:
    commission = _commission_for_session(session)
    if commission is None:
        await session.send("No class gear path is registered for this class.\r\n")
        return
    base_key, base_recipe_key = class_progression.CLASS_SIGNATURE_GEAR[commission.class_key]
    advanced_key, advanced_recipe_key = ADVANCED_GEAR_BY_CLASS[commission.class_key]
    base = crafting.ITEMS_BY_KEY[base_key]
    advanced = crafting.ITEMS_BY_KEY[advanced_key]
    recipe = crafting.RECIPES_BY_KEY[advanced_recipe_key]
    quest = _current_commission_quest(session, commission)
    qualified = bool(quest and quest.get("status") == "completed")
    owned_advanced = session.database.item_quantity(session.character.id, advanced_key) > 0

    await session.send(f"\r\n--- {session.character.character_class.title()} Gear Path ---\r\n")
    await session.send(f"Stage 1: {base.name} via {base_recipe_key}.\r\n")
    await session.send(f"Field proof: {commission.quest.name} - {'COMPLETE' if qualified else 'not complete'}.\r\n")
    await session.send(f"Stage 2: {advanced.name} via {advanced_recipe_key} ({recipe.trade_skill_key} {recipe.minimum_skill}).\r\n")
    await session.send("Required materials:\r\n")
    for requirement in recipe.materials:
        definition = crafting.ITEMS_BY_KEY.get(requirement.item_key)
        name = definition.name if definition else requirement.item_key
        hint = MATERIAL_SOURCE_HINTS.get(requirement.item_key, "the wider player economy")
        have = session.database.item_quantity(session.character.id, requirement.item_key)
        await session.send(f"- {requirement.quantity}x {name} (you have {have}) - source: {hint}.\r\n")
    await session.send(
        "The commission plate is deliberately tradable crafting work: earn it with your class, then use your own profession or hand the component and materials to another player.\r\n"
    )
    if owned_advanced:
        await session.send(f"Status: you already own {advanced.name}.\r\n")


async def _delegate_prompt(self, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    self.prompt = replay_prompt
    try:
        await previous_prompt(self)
    finally:
        if had_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_class_world_integration_runtime(player_session_class) -> None:
    """Connect class kits to field quests, existing dungeons, and artisan upgrades."""
    install_class_world_content()
    _install_advanced_affinity_equivalents()
    if getattr(player_session_class, "_class_world_integration_runtime_installed", False):
        return

    previous_prompt = player_session_class.playing_prompt
    previous_progression_use = class_progression._use_progression_ability
    previous_complete_use = class_progression._complete_use

    async def observed_progression_use(session, ability, target_text: str):
        previous_context = getattr(session, "_class_commission_use_context", None)
        session._class_commission_use_context = _capture_context(session, target_text)
        try:
            return await previous_progression_use(session, ability, target_text)
        finally:
            if previous_context is None:
                session.__dict__.pop("_class_commission_use_context", None)
            else:
                session._class_commission_use_context = previous_context

    async def observed_complete_use(session, ability) -> None:
        await previous_complete_use(session, ability)
        context = getattr(session, "_class_commission_use_context", None)
        if context is not None:
            await _record_successful_role_use(session, ability, context)

    class_progression._use_progression_ability = observed_progression_use
    class_progression._complete_use = observed_complete_use

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"class commission", "field commission", "commission", "take class commission"}:
            await _show_commission(self)
            return
        if normalized in {"class gear path", "gear path", "class advancement gear"}:
            await _show_gear_path(self)
            return
        if normalized in {"talk sable", "talk sable-of-five-ways", "talk sable of five ways"} and self.character.current_room == VEYRA_FIVE_WAYS_KEY:
            await _show_commission(self)
            return

        await _delegate_prompt(self, previous_prompt, command)
        if normalized in {"help", "?", "help all", "help full"}:
            await self.send(
                "Class field progression: at level 8 visit Sable-of-Five-Ways in Veyra and use CLASS COMMISSION. "
                "Complete role-specific actions in real dungeons, then use CLASS GEAR PATH to connect the reward plate, dungeon materials, and artisan upgrade recipe.\r\n"
            )

    player_session_class.playing_prompt = playing_prompt
    player_session_class._class_world_integration_runtime_installed = True
