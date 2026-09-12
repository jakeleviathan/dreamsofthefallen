from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.crafting as crafting
import mud.mechanics as mechanics
import mud.party_system as party_system
import mud.session as session_module
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem


# This pass deliberately stops at level 9 because the authored shared world is
# currently strongest through roughly level 10. The goal is a complete early-
# midgame class identity, not a speculative fifty-spell endgame tree.
CLASS_ROLE_SUMMARIES: dict[str, str] = {
    "brute": "Front-line protector: hold enemy attention, interrupt danger, and stay standing while allies work.",
    "wizard": "Single-target spell specialist: burst hard, control a dangerous target, and protect yourself with barriers.",
    "druid": "Flexible nature caster: reliable secondary healing, steady recovery, and practical nature damage.",
    "priest": "Primary support: efficient healing, protection, resurrection, and party-wide recovery while retaining your spiritual path's flavor.",
    "necromancer": "Attrition specialist: drain life, maintain an undead servant, curse enemies, and turn time into an advantage.",
}


BRUTE_ABILITIES = (
    mechanics.AbilityDefinition(
        key="heavy_strike",
        name="Heavy Strike",
        unlock_level=2,
        mana_cost=3,
        cooldown_seconds=6.0,
        description="A heavy weapon blow that deals strong physical damage and creates extra threat.",
        category="physical_attack",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="shield_bash",
        name="Shield Bash",
        unlock_level=4,
        mana_cost=4,
        cooldown_seconds=10.0,
        description="A short, reliable interrupt that damages the target and stops its retaliation for three seconds.",
        category="control",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="hold_the_line",
        name="Hold the Line",
        unlock_level=6,
        mana_cost=6,
        cooldown_seconds=16.0,
        description="Brace for incoming punishment, reducing damage taken for a short period while you keep the enemy's attention.",
        category="self_protection",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="rallying_roar",
        name="Rallying Roar",
        unlock_level=8,
        mana_cost=8,
        cooldown_seconds=18.0,
        description="Force yourself to the top of the hate list and recover a small amount of health when the line is starting to break.",
        category="threat_survival",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
)

WIZARD_ABILITIES = (
    mechanics.AbilityDefinition(
        key="minor_barrier",
        name="Minor Barrier",
        unlock_level=2,
        mana_cost=4,
        cooldown_seconds=10.0,
        description="Wrap yourself in a brief arcane barrier that softens incoming blows.",
        category="self_protection",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="arcane_bolt",
        name="Arcane Bolt",
        unlock_level=3,
        mana_cost=6,
        cooldown_seconds=5.0,
        description="A focused single-target arcane strike: slower and heavier than Coldfire Burst.",
        category="spell_damage",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="frostbind",
        name="Frostbind",
        unlock_level=5,
        mana_cost=8,
        cooldown_seconds=11.0,
        description="Damage one enemy and lock its movement long enough to stop retaliation for three seconds.",
        category="spell_control",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="arcane_surge",
        name="Arcane Surge",
        unlock_level=7,
        mana_cost=10,
        cooldown_seconds=20.0,
        description="Charge your next damaging Wizard spell within fifteen seconds to hit fifty percent harder.",
        category="spell_setup",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="rift_lance",
        name="Rift Lance",
        unlock_level=9,
        mana_cost=12,
        cooldown_seconds=8.0,
        description="Drive a narrow lance of arcane force through one target for heavy direct spell damage.",
        category="spell_damage",
        design_status="approved_midgame_live",
    ),
)

DRUID_ABILITIES = (
    mechanics.AbilityDefinition(
        key="hp_buff",
        name="Oakheart",
        unlock_level=2,
        mana_cost=5,
        cooldown_seconds=12.0,
        description="Give yourself or another character six temporary maximum HP for one minute.",
        category="ally_buff",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="thorn_lash",
        name="Thorn Lash",
        unlock_level=3,
        mana_cost=5,
        cooldown_seconds=5.0,
        description="Strike one enemy with fast-growing thorns for direct nature spell damage.",
        category="nature_damage",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="rejuvenation",
        name="Rejuvenation",
        unlock_level=5,
        mana_cost=5,
        cooldown_seconds=8.0,
        description="Place an efficient three-pulse heal over time on yourself or another living character.",
        category="healing_over_time",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="barkskin",
        name="Barkskin",
        unlock_level=7,
        mana_cost=7,
        cooldown_seconds=15.0,
        description="Protect yourself or an ally with a short damage-softening ward.",
        category="ally_protection",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="verdant_pulse",
        name="Verdant Pulse",
        unlock_level=9,
        mana_cost=11,
        cooldown_seconds=14.0,
        description="Restore health to every living party member currently standing with you.",
        category="group_healing",
        design_status="approved_midgame_live",
    ),
)

PRIEST_COMMON_ABILITIES = (
    mechanics.AbilityDefinition(
        key="mend_ally",
        name="Mend Ally",
        unlock_level=3,
        mana_cost=3,
        cooldown_seconds=3.0,
        description="An efficient targeted heal that gives every Priest a dependable party-care tool.",
        category="healing",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="prayer_of_renewal",
        name="Prayer of Renewal",
        unlock_level=7,
        mana_cost=9,
        cooldown_seconds=12.0,
        description="Restore health to every living member of your party in the same room.",
        category="group_healing",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="sanctuary",
        name="Sanctuary",
        unlock_level=9,
        mana_cost=12,
        cooldown_seconds=20.0,
        description="Briefly ward every living party member standing with you against incoming damage.",
        category="group_protection",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
)

NECROMANCER_ABILITIES = (
    mechanics.AbilityDefinition(
        key="bone_ward",
        name="Bone Ward",
        unlock_level=5,
        mana_cost=5,
        cooldown_seconds=13.0,
        description="Harden a shell of pale necromantic force around yourself to soften incoming blows.",
        category="self_protection",
        skill_improves_effectiveness=False,
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="grave_command",
        name="Grave Command",
        unlock_level=7,
        mana_cost=6,
        cooldown_seconds=5.0,
        description="Order your active Skeleton to make a hard coordinated strike against your current target.",
        category="pet_attack",
        design_status="approved_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="wither",
        name="Wither",
        unlock_level=9,
        mana_cost=9,
        cooldown_seconds=12.0,
        description="Damage an enemy and curse its defenses, lowering its armor class for the rest of that encounter.",
        category="curse",
        design_status="approved_midgame_live",
    ),
)


# Five signature pieces are not class-locked. Anyone can wear them and receive
# their raw stats; the named affinity is a bonus only when the matching class
# knows how to exploit that design. This keeps Astralis's universal-equipment
# rule while still creating gear that makes a player think, 'that is for my job.'
SIGNATURE_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        key="lineholder_shield",
        name="Lineholder Shield",
        description="A broad road shield rebuilt from Blackreed fort iron. Its weight, grip, and sightline are designed for somebody who intends to be the person an enemy has to get through.",
        category="equipment",
        equipment=EquipmentItem(
            "Lineholder Shield", "off_hand", armor_class=3,
            stat_bonuses=CharacterStats(might=1, hp=2),
            scripted_effects=("Brute affinity: Heavy Strike creates more threat and Hold the Line lasts longer.",),
        ),
        tier=2,
    ),
    ItemDefinition(
        key="coldglass_circlet",
        name="Coldglass Circlet",
        description="A narrow iron circlet holding a sliver of Gloamworks cold glass away from the skin. The flake gives a spellcaster a brutally clear point on which to focus.",
        category="equipment",
        equipment=EquipmentItem(
            "Coldglass Circlet", "head", armor_class=1,
            stat_bonuses=CharacterStats(mind=2, grace=1),
            scripted_effects=("Wizard affinity: damaging Wizard spells gain +2 damage before Arcane Surge multipliers.",),
        ),
        tier=2,
    ),
    ItemDefinition(
        key="briarheart_mantle",
        name="Briarheart Mantle",
        description="A layered traveling mantle stitched around living-green herb pockets. It smells faintly of wet bark and crushed Greenleaf even after weeks on the road.",
        category="equipment",
        equipment=EquipmentItem(
            "Briarheart Mantle", "chest", armor_class=2,
            stat_bonuses=CharacterStats(love=2, hp=2),
            scripted_effects=("Druid affinity: Druid healing effects restore +2 HP whenever they pulse or land.",),
        ),
        tier=2,
    ),
    ItemDefinition(
        key="resonant_vestments",
        name="Resonant Vestments",
        description="Practical layered vestments with a Gloamworks safety cog sewn inside the sternum panel. The cog answers spoken prayer with a low, steady note rather than spectacle.",
        category="equipment",
        equipment=EquipmentItem(
            "Resonant Vestments", "chest", armor_class=2,
            stat_bonuses=CharacterStats(love=2, mind=1, hp=1),
            scripted_effects=("Priest affinity: Priest healing spells restore +2 additional HP.",),
        ),
        tier=2,
    ),
    ItemDefinition(
        key="regent_bone_wand",
        name="Regent-Bone Wand",
        description="A black horn and bone wand capped by a tiny Regent shard. It does not make necromancy safer; it makes the line between command and curse easier to feel.",
        category="equipment",
        equipment=EquipmentItem(
            "Regent-Bone Wand", "main_hand",
            stat_bonuses=CharacterStats(mind=2, hp=1),
            scripted_effects=("Necromancer affinity: Grave Command and Wither deal +2 damage.",),
        ),
        tier=2,
    ),
)

SIGNATURE_RECIPES: tuple[CraftingRecipe, ...] = (
    CraftingRecipe(
        key="forge_lineholder_shield", trade_skill_key="blacksmithing",
        output_item_key="lineholder_shield", minimum_skill=8, high_skill_quality_threshold=30,
        materials=(MaterialRequirement("iron_ingot", 2), MaterialRequirement("blackreed_iron_fitting", 1)),
        station_key="forge", description="Forge a Blackreed fitting into a broad Lineholder Shield.",
        design_status="live_class_identity_recipe",
    ),
    CraftingRecipe(
        key="forge_coldglass_circlet", trade_skill_key="blacksmithing",
        output_item_key="coldglass_circlet", minimum_skill=10, high_skill_quality_threshold=35,
        materials=(MaterialRequirement("iron_ingot", 1), MaterialRequirement("gloamworks_cold_glass", 1)),
        station_key="forge", description="Set a Cold Glass Flake into a stable iron focusing circlet.",
        design_status="live_class_identity_recipe",
    ),
    CraftingRecipe(
        key="sew_briarheart_mantle", trade_skill_key="tailoring",
        output_item_key="briarheart_mantle", minimum_skill=8, high_skill_quality_threshold=30,
        materials=(MaterialRequirement("cotton_cloth", 1), MaterialRequirement("rough_hide", 1), MaterialRequirement("greenleaf", 2)),
        station_key="loom", description="Sew a field mantle with protected Greenleaf pockets and a hide shoulder layer.",
        design_status="live_class_identity_recipe",
    ),
    CraftingRecipe(
        key="sew_resonant_vestments", trade_skill_key="tailoring",
        output_item_key="resonant_vestments", minimum_skill=10, high_skill_quality_threshold=35,
        materials=(MaterialRequirement("cotton_cloth", 2), MaterialRequirement("gloamworks_resonant_cog", 1)),
        station_key="loom", description="Build practical vestments around a recovered Resonant Cog.",
        design_status="live_class_identity_recipe",
    ),
    CraftingRecipe(
        key="forge_regent_bone_wand", trade_skill_key="blacksmithing",
        output_item_key="regent_bone_wand", minimum_skill=12, high_skill_quality_threshold=38,
        materials=(MaterialRequirement("imp_horn", 1), MaterialRequirement("bone_chips", 2), MaterialRequirement("gloamworks_regent_shard", 1)),
        station_key="forge", description="Bind horn, prepared bone, and a Regent Shard into a necromantic working wand.",
        design_status="live_class_identity_recipe",
    ),
)

CLASS_SIGNATURE_GEAR = {
    "brute": ("lineholder_shield", "forge_lineholder_shield"),
    "wizard": ("coldglass_circlet", "forge_coldglass_circlet"),
    "druid": ("briarheart_mantle", "sew_briarheart_mantle"),
    "priest": ("resonant_vestments", "sew_resonant_vestments"),
    "necromancer": ("regent_bone_wand", "forge_regent_bone_wand"),
}


_WITHERED_ENEMIES: dict[int, object] = {}
_STUNNED_ENEMIES: dict[int, object] = {}


def _sort_abilities(abilities):
    return tuple(sorted(abilities, key=lambda a: (10_000 if a.unlock_level is None else a.unlock_level, a.name)))


def _upsert_fixed(class_key: str, definitions) -> None:
    by_key = {ability.key: ability for ability in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())}
    for definition in definitions:
        by_key[definition.key] = definition
    mechanics.FIXED_CLASS_ABILITIES[class_key] = _sort_abilities(by_key.values())


def install_class_progression_content() -> None:
    """Register the level 1-9 class ladders, signature gear, and real recipes idempotently."""
    _upsert_fixed("brute", BRUTE_ABILITIES)
    _upsert_fixed("wizard", WIZARD_ABILITIES)
    _upsert_fixed("druid", DRUID_ABILITIES)
    _upsert_fixed("necromancer", NECROMANCER_ABILITIES)

    # Priest paths keep their deity/Witness starter identity, then share a small
    # party-care backbone. Resurrection is registered by the death system and is
    # preserved here if it is already present.
    for path_key, current in tuple(mechanics.PRIEST_DEITY_ABILITIES.items()):
        by_key = {ability.key: ability for ability in current}
        for definition in PRIEST_COMMON_ABILITIES:
            by_key[definition.key] = definition
        mechanics.PRIEST_DEITY_ABILITIES[path_key] = _sort_abilities(by_key.values())

    known_items = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in SIGNATURE_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    blacksmith_additions = tuple(
        recipe for recipe in SIGNATURE_RECIPES
        if recipe.trade_skill_key == "blacksmithing" and recipe.key not in crafting.BLACKSMITHING_RECIPES_BY_KEY
    )
    if blacksmith_additions:
        crafting.BLACKSMITHING_RECIPES = crafting.BLACKSMITHING_RECIPES + blacksmith_additions
        crafting.BLACKSMITHING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in blacksmith_additions})

    tailoring_additions = tuple(
        recipe for recipe in SIGNATURE_RECIPES
        if recipe.trade_skill_key == "tailoring" and recipe.key not in crafting.TAILORING_RECIPES_BY_KEY
    )
    if tailoring_additions:
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + tailoring_additions
        crafting.TAILORING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in tailoring_additions})

    recipe_additions = tuple(recipe for recipe in SIGNATURE_RECIPES if recipe.key not in crafting.RECIPES_BY_KEY)
    if recipe_additions:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + recipe_additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in recipe_additions})

    # mud.session imported ALL_RECIPES as a value long before this product-level
    # pass. Refresh that one alias so RECIPES shows the same live catalog that
    # craft_recipe() actually uses.
    session_module.ALL_RECIPES = crafting.ALL_RECIPES


def ensure_progression_storage(database) -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_class_progression_notice (
                character_id INTEGER PRIMARY KEY,
                last_announced_level INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )


def _last_announced_level(database, character_id: int) -> int | None:
    ensure_progression_storage(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT last_announced_level FROM character_class_progression_notice WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    return None if row is None else int(row["last_announced_level"])


def _set_last_announced_level(database, character_id: int, level: int) -> None:
    ensure_progression_storage(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_class_progression_notice (character_id, last_announced_level)
            VALUES (?, ?)
            ON CONFLICT(character_id) DO UPDATE SET
                last_announced_level = excluded.last_announced_level,
                updated_at = CURRENT_TIMESTAMP
            """,
            (character_id, level),
        )


def _all_class_abilities(session):
    character = getattr(session, "character", None)
    if character is None:
        return ()
    class_key = character.character_class or ""
    if class_key == "priest":
        return mechanics.PRIEST_DEITY_ABILITIES.get(character.deity_key or "", ())
    return mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())


def _unlocked_class_abilities(session):
    character = getattr(session, "character", None)
    if character is None:
        return ()
    return mechanics.class_abilities_for_level(
        character.character_class or "", character.level, character.deity_key
    )


def _next_ability(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    future = [
        ability for ability in _all_class_abilities(session)
        if ability.unlock_level is not None and ability.unlock_level > character.level
    ]
    return min(future, key=lambda a: (a.unlock_level, a.name), default=None)


def _command_for(ability) -> str:
    if ability.key == "resurrection":
        return "RESURRECT <name>"
    if ability.category in {"healing", "ally_buff", "healing_over_time", "ally_protection"}:
        return f"CAST {ability.name.upper()} <name>"
    return f"CAST {ability.name.upper()}"


def _equipped_item_keys(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    from mud.equipment_system import equipped_item_keys
    return set(equipped_item_keys(session.database, character.id).values())


def _has_affinity_item(session, item_key: str, class_key: str) -> bool:
    character = getattr(session, "character", None)
    return bool(
        character is not None
        and character.character_class == class_key
        and item_key in _equipped_item_keys(session)
    )


async def _show_class(session) -> None:
    character = session.character
    class_key = character.character_class or ""
    await session.send(f"\r\n--- {class_key.replace('_', ' ').title()} Role ---\r\n")
    await session.send(CLASS_ROLE_SUMMARIES.get(class_key, "Your class role is still being authored.") + "\r\n")
    await session.send(f"Level {character.level}. Your class kit is fixed and grows automatically as you level.\r\n")
    unlocked = _unlocked_class_abilities(session)
    if unlocked:
        await session.send("\r\nUnlocked tools:\r\n")
        for ability in unlocked:
            await session.send(
                f"- {ability.name} [{ability.category}] - {_command_for(ability)}\r\n"
                f"  {ability.description}\r\n"
            )
    next_ability = _next_ability(session)
    if next_ability is not None:
        await session.send(
            f"\r\nNext unlock: level {next_ability.unlock_level} - {next_ability.name}: {next_ability.description}\r\n"
        )
    await session.send("Type CLASS GEAR for the signature midgame item that reinforces this role.\r\n")


async def _show_class_gear(session) -> None:
    character = session.character
    class_key = character.character_class or ""
    item_key, recipe_key = CLASS_SIGNATURE_GEAR.get(class_key, (None, None))
    if item_key is None:
        await session.send("This class does not have a signature gear recommendation yet.\r\n")
        return
    item = crafting.ITEMS_BY_KEY[item_key]
    recipe = crafting.RECIPES_BY_KEY[recipe_key]
    equipment = item.equipment
    assert equipment is not None
    owned = session.database.item_quantity(character.id, item_key) > 0
    equipped = item_key in _equipped_item_keys(session)
    materials = ", ".join(
        f"{req.quantity}x {crafting.ITEMS_BY_KEY.get(req.item_key).name if req.item_key in crafting.ITEMS_BY_KEY else req.item_key}"
        for req in recipe.materials
    )
    stats = []
    if equipment.armor_class:
        stats.append(f"AC +{equipment.armor_class}")
    for key, label in (("might", "Might"), ("grace", "Grace"), ("love", "Love"), ("mind", "Mind"), ("hp", "HP")):
        value = getattr(equipment.stat_bonuses, key)
        if value:
            stats.append(f"{label} +{value}")
    await session.send(f"\r\n--- Signature Gear: {item.name} ---\r\n{item.description}\r\n")
    await session.send("Stats: " + ", ".join(stats or ["none"]) + "\r\n")
    for effect in equipment.scripted_effects:
        await session.send("Affinity: " + effect + "\r\n")
    await session.send(
        f"Recipe: {recipe.key} ({recipe.trade_skill_key} {recipe.minimum_skill}) - {materials}. Station: {recipe.station_key}.\r\n"
    )
    await session.send(
        "Status: " + ("EQUIPPED" if equipped else "OWNED" if owned else "not yet owned") + ". "
        "The item remains universally wearable; its raw stats work for every class.\r\n"
    )


async def _show_ability_detail(session, target_text: str) -> None:
    wanted = " ".join(target_text.strip().lower().replace("_", " ").split())
    for ability in _all_class_abilities(session):
        aliases = {ability.key.replace("_", " ").lower(), ability.name.lower()}
        if wanted not in aliases:
            continue
        status = "UNLOCKED" if ability in _unlocked_class_abilities(session) else f"LOCKED until level {ability.unlock_level}"
        await session.send(
            f"\r\n{ability.name} - {status}\r\n{ability.description}\r\n"
            f"Category: {ability.category} | Mana: {ability.mana_cost or 0} | Cooldown: {ability.cooldown_seconds or 0:g}s\r\n"
            f"Command: {_command_for(ability)}\r\n"
        )
        return
    await session.send("That is not an ability in your class progression. Type CLASS to review your kit.\r\n")


async def _announce_pending_level(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    refreshed = session.database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed
        character = refreshed
    last = _last_announced_level(session.database, character.id)
    if last is None:
        _set_last_announced_level(session.database, character.id, character.level)
        return
    if character.level <= last:
        return
    unlocks = [
        ability for ability in _all_class_abilities(session)
        if ability.unlock_level is not None and last < ability.unlock_level <= character.level
    ]
    await session.send(f"\r\n*** CLASS MILESTONE: LEVEL {character.level} ***\r\n")
    await session.send(CLASS_ROLE_SUMMARIES.get(character.character_class or "", "Your role continues to grow.") + "\r\n")
    if unlocks:
        for ability in unlocks:
            await session.send(
                f"NEW: {ability.name} - {ability.description}\r\n"
                f"Try it with: {_command_for(ability)}\r\n"
            )
    else:
        await session.send("No new active ability at this level; your existing kit and use-based skills continue to improve.\r\n")
    if last < 5 <= character.level:
        await session.send("Your midgame role gear is now worth pursuing. Type CLASS GEAR to see the signature piece and its recipe.\r\n")
    next_ability = _next_ability(session)
    if next_ability is not None:
        await session.send(f"Next class tool: {next_ability.name} at level {next_ability.unlock_level}.\r\n")
    _set_last_announced_level(session.database, character.id, character.level)


def _resolve_ability(session, ability_text: str):
    normalized = " ".join(ability_text.strip().lower().replace("_", " ").split())
    matches = []
    for ability in _unlocked_class_abilities(session):
        for alias in {ability.key.replace("_", " ").lower(), ability.name.lower()}:
            if normalized == alias:
                matches.append((len(alias), ability, ""))
            elif normalized.startswith(alias + " "):
                matches.append((len(alias), ability, normalized[len(alias):].strip()))
    if not matches:
        return None, ""
    _, ability, target = max(matches, key=lambda row: row[0])
    return ability, target


def _ally_here(session, target_text: str):
    wanted = target_text.strip()
    if not wanted or wanted.lower() in {"self", "me", "myself"}:
        return session
    target = party_system._session_for_name(wanted)
    if target is None or getattr(target, "character", None) is None:
        return None
    if target.character.current_room != session.character.current_room:
        return None
    return target


def _living(target) -> bool:
    combatant = getattr(target, "combatant", None)
    return combatant is not None and combatant.current_hp > 0 and not getattr(target, "_death_pending", False)


def _support_targets(session) -> list:
    targets = party_system._party_sessions_here(session)
    return [target for target in targets if _living(target)]


def _track_task(session, coroutine) -> None:
    tasks = getattr(session, "_class_progression_tasks", None)
    if tasks is None:
        tasks = set()
        session._class_progression_tasks = tasks
    task = asyncio.create_task(coroutine)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def _affinity_healing_bonus(session) -> int:
    character = session.character
    if character.character_class == "druid" and _has_affinity_item(session, "briarheart_mantle", "druid"):
        return 2
    if character.character_class == "priest" and _has_affinity_item(session, "resonant_vestments", "priest"):
        return 2
    return 0


def _wizard_damage(session, base: int) -> tuple[int, bool]:
    damage = session.combatant.spell_damage(base)
    if _has_affinity_item(session, "coldglass_circlet", "wizard"):
        damage += 2
    now = asyncio.get_running_loop().time()
    surged = now < getattr(session, "_arcane_surge_until", 0.0)
    if surged:
        damage = max(1, round(damage * 1.5))
        session._arcane_surge_until = 0.0
    return damage, surged


async def _activate(session, ability) -> bool:
    combatant = session.combatant
    mana_cost = ability.mana_cost or 0
    if not combatant.ability_ready(ability.key):
        await session.send(f"{ability.name} is still on cooldown.\r\n")
        return False
    if not combatant.spend_mana(mana_cost):
        await session.send(f"You need {mana_cost} mana for {ability.name}.\r\n")
        return False
    return True


async def _complete_use(session, ability) -> None:
    session.database.record_ability_use(session.character.id, ability.key)
    session.combatant.start_cooldown(ability.key, ability.cooldown_seconds or 0.0)
    await session.send_client_state()


async def _party_combat_echo(session, text: str) -> None:
    enemy = getattr(session, "active_enemy", None)
    encounter = party_system._encounter_for(enemy) if enemy is not None else None
    if encounter is not None:
        await party_system._send_party(encounter.party, f"[Party Combat] {text}\r\n", exclude=session)


async def _deal_damage(session, ability, damage: int, *, threat_multiplier: float = 1.0) -> bool:
    enemy = session.active_enemy
    if enemy is None:
        return False
    dealt = enemy.take_damage(max(0, damage))
    enemy.hate.add_threat(session.character.id, max(1.0, dealt * threat_multiplier))
    await session.send(
        f"{ability.name} hits {enemy.definition.name} for {dealt} damage ({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
    )
    await _party_combat_echo(session, f"{session.character.name} uses {ability.name} on {enemy.definition.name} for {dealt}.")
    if not enemy.alive:
        _WITHERED_ENEMIES.pop(id(enemy), None)
        _STUNNED_ENEMIES.pop(id(enemy), None)
        await session._finish_enemy_defeat(enemy)
        return True
    return False


async def _stun_enemy(session, enemy, seconds: float) -> None:
    if not enemy.definition.retaliates or id(enemy) in _STUNNED_ENEMIES:
        return
    _STUNNED_ENEMIES[id(enemy)] = enemy
    enemy.definition = replace(enemy.definition, retaliates=False)

    async def restore():
        try:
            await asyncio.sleep(seconds)
            if _STUNNED_ENEMIES.get(id(enemy)) is enemy and enemy.alive:
                enemy.definition = replace(enemy.definition, retaliates=True)
        finally:
            _STUNNED_ENEMIES.pop(id(enemy), None)

    _track_task(session, restore())


async def _heal(caster, target, base: int, label: str) -> int:
    amount = caster.combatant.healing_amount(base) + _affinity_healing_bonus(caster)
    before = target.combatant.current_hp
    target.combatant.current_hp = min(target.combatant.max_hp, before + amount)
    restored = target.combatant.current_hp - before
    if target is caster:
        await caster.send(f"{label} restores {restored} HP.\r\n")
    else:
        await caster.send(f"{label} restores {restored} HP to {target.character.name}.\r\n")
        await target.send(f"{caster.character.name}'s {label} restores {restored} HP to you.\r\n")
    await target.send_client_state()
    return restored


async def _rejuvenation(caster, target) -> None:
    try:
        for pulse in range(1, 4):
            await asyncio.sleep(2.0)
            if not _living(target):
                return
            amount = caster.combatant.healing_amount(3) + _affinity_healing_bonus(caster)
            before = target.combatant.current_hp
            target.combatant.current_hp = min(target.combatant.max_hp, before + amount)
            restored = target.combatant.current_hp - before
            await target.send(f"Rejuvenation pulses for {restored} HP ({pulse}/3).\r\n")
            if target is not caster:
                await caster.send(f"Rejuvenation restores {restored} HP to {target.character.name} ({pulse}/3).\r\n")
            await target.send_client_state()
    except asyncio.CancelledError:
        return


async def _expire_oakheart(target, amount: int) -> None:
    try:
        await asyncio.sleep(60.0)
        if getattr(target, "combatant", None) is None:
            return
        target.combatant.max_hp = max(1, target.combatant.max_hp - amount)
        target.combatant.current_hp = min(target.combatant.current_hp, target.combatant.max_hp)
        target._oakheart_active = False
        await target.send("Oakheart fades; your maximum HP returns to normal.\r\n")
        await target.send_client_state()
    except asyncio.CancelledError:
        return


HANDLED_ABILITIES = {
    "heavy_strike", "shield_bash", "hold_the_line", "rallying_roar",
    "coldfire_burst", "minor_barrier", "arcane_bolt", "frostbind", "arcane_surge", "rift_lance",
    "minor_heal", "hp_buff", "thorn_lash", "rejuvenation", "barkskin", "verdant_pulse",
    "restoring_light", "guardian_ward", "judgment_bolt", "mend_ally", "resurrection", "prayer_of_renewal", "sanctuary",
    "bone_ward", "grave_command", "wither",
}


async def _use_progression_ability(session, ability, target_text: str) -> bool:
    key = ability.key
    if key not in HANDLED_ABILITIES:
        return False

    enemy_keys = {
        "heavy_strike", "shield_bash", "rallying_roar", "coldfire_burst", "arcane_bolt",
        "frostbind", "rift_lance", "thorn_lash", "judgment_bolt", "grave_command", "wither",
    }
    if key in enemy_keys and session.active_enemy is None:
        await session.send(f"You need an active enemy target for {ability.name}.\r\n")
        return True

    if key in {"minor_heal", "hp_buff", "rejuvenation", "barkskin", "restoring_light", "guardian_ward", "mend_ally"}:
        target = _ally_here(session, target_text)
        if target is None or not _living(target):
            await session.send("That living character is not here.\r\n")
            return True
    else:
        target = None

    if key == "resurrection":
        if not target_text:
            await session.send("Resurrect whom? Use RESURRECT <name> or CAST RESURRECTION <name>.\r\n")
            return True
        from mud.death_recovery import resurrect_character
        await resurrect_character(session, target_text)
        return True

    if key == "grave_command" and session.database.get_active_pet(session.character.id) != "skeleton":
        await session.send("Grave Command requires an active Skeleton. Raise one first.\r\n")
        return True

    if key == "hp_buff" and getattr(target, "_oakheart_active", False):
        await session.send(f"{target.character.name} is already strengthened by Oakheart.\r\n")
        return True

    if not await _activate(session, ability):
        return True

    if key == "heavy_strike":
        affinity = _has_affinity_item(session, "lineholder_shield", "brute")
        damage = session.combatant.auto_attack_damage(5)
        await _deal_damage(session, ability, damage, threat_multiplier=3.0 if affinity else 2.0)
    elif key == "shield_bash":
        enemy = session.active_enemy
        damage = session.combatant.auto_attack_damage(2)
        died = await _deal_damage(session, ability, damage, threat_multiplier=2.0)
        if not died and enemy is not None:
            await _stun_enemy(session, enemy, 3.0)
            await session.send(f"{enemy.definition.name} is STUNNED for three seconds.\r\n")
    elif key == "hold_the_line":
        duration = 14.0 if _has_affinity_item(session, "lineholder_shield", "brute") else 10.0
        session.ward_until = asyncio.get_running_loop().time() + duration
        await session.send(f"You plant yourself and Hold the Line for {int(duration)} seconds; incoming blows are softened.\r\n")
    elif key == "rallying_roar":
        enemy = session.active_enemy
        top = max(enemy.hate.threat.values(), default=0.0)
        enemy.hate.threat[session.character.id] = top + 10.0
        restored = max(1, session.combatant.max_hp // 8)
        before = session.combatant.current_hp
        session.combatant.current_hp = min(session.combatant.max_hp, before + restored)
        await session.send(f"Your roar seizes the fight. You recover {session.combatant.current_hp - before} HP and take the top of the hate list.\r\n")
    elif key in {"coldfire_burst", "arcane_bolt", "frostbind", "rift_lance"}:
        base = {"coldfire_burst": 7, "arcane_bolt": 10, "frostbind": 6, "rift_lance": 15}[key]
        damage, surged = _wizard_damage(session, base)
        enemy = session.active_enemy
        died = await _deal_damage(session, ability, damage)
        if surged:
            await session.send("Arcane Surge discharges through the spell, increasing its damage by fifty percent.\r\n")
        if key == "frostbind" and not died and enemy is not None:
            await _stun_enemy(session, enemy, 3.0)
            await session.send(f"Ice-blue force locks {enemy.definition.name} in place for three seconds.\r\n")
    elif key == "minor_barrier":
        session.ward_until = asyncio.get_running_loop().time() + 8.0
        await session.send("A Minor Barrier tightens around you for eight seconds.\r\n")
    elif key == "arcane_surge":
        session._arcane_surge_until = asyncio.get_running_loop().time() + 15.0
        await session.send("Arcane power gathers behind your next damaging Wizard spell for fifteen seconds.\r\n")
    elif key in {"minor_heal", "restoring_light", "mend_ally"}:
        base = {"minor_heal": 6, "restoring_light": 8, "mend_ally": 10}[key]
        await _heal(session, target, base, ability.name)
    elif key == "hp_buff":
        target._oakheart_active = True
        target.combatant.max_hp += 6
        target.combatant.current_hp += 6
        await session.send(f"Oakheart strengthens {target.character.name}, granting 6 maximum HP for one minute.\r\n")
        if target is not session:
            await target.send(f"{session.character.name}'s Oakheart grants you 6 maximum HP for one minute.\r\n")
        _track_task(target, _expire_oakheart(target, 6))
    elif key == "thorn_lash":
        await _deal_damage(session, ability, session.combatant.spell_damage(7))
    elif key == "rejuvenation":
        await session.send(f"Rejuvenation takes root on {target.character.name}; three healing pulses will follow.\r\n")
        _track_task(session, _rejuvenation(session, target))
    elif key in {"barkskin", "guardian_ward"}:
        duration = 10.0
        target.ward_until = asyncio.get_running_loop().time() + duration
        await session.send(f"{ability.name} protects {target.character.name} for ten seconds.\r\n")
        if target is not session:
            await target.send(f"{session.character.name}'s {ability.name} settles around you.\r\n")
    elif key == "verdant_pulse":
        targets = _support_targets(session)
        await session.send(f"Verdant Pulse spreads through {len(targets)} living party member{'s' if len(targets) != 1 else ''}.\r\n")
        for member in targets:
            await _heal(session, member, 6, "Verdant Pulse")
    elif key == "judgment_bolt":
        await _deal_damage(session, ability, session.combatant.spell_damage(6))
    elif key == "prayer_of_renewal":
        targets = _support_targets(session)
        await session.send(f"Prayer of Renewal reaches {len(targets)} living party member{'s' if len(targets) != 1 else ''}.\r\n")
        for member in targets:
            await _heal(session, member, 6, "Prayer of Renewal")
    elif key == "sanctuary":
        targets = _support_targets(session)
        until = asyncio.get_running_loop().time() + 8.0
        for member in targets:
            member.ward_until = max(getattr(member, "ward_until", 0.0), until)
            if member is not session:
                await member.send(f"{session.character.name}'s Sanctuary protects you for eight seconds.\r\n")
        await session.send(f"Sanctuary protects {len(targets)} living party member{'s' if len(targets) != 1 else ''} for eight seconds.\r\n")
    elif key == "bone_ward":
        session.ward_until = asyncio.get_running_loop().time() + 10.0
        await session.send("A pale Bone Ward locks around you for ten seconds.\r\n")
    elif key == "grave_command":
        bonus = 2 if _has_affinity_item(session, "regent_bone_wand", "necromancer") else 0
        damage = session.combatant.spell_damage(7) + bonus
        await _deal_damage(session, ability, damage, threat_multiplier=0.75)
        await session.send("Your Skeleton answers the command with a sudden coordinated strike.\r\n")
    elif key == "wither":
        enemy = session.active_enemy
        bonus = 2 if _has_affinity_item(session, "regent_bone_wand", "necromancer") else 0
        died = await _deal_damage(session, ability, session.combatant.spell_damage(3) + bonus)
        if not died and enemy is not None and _WITHERED_ENEMIES.get(id(enemy)) is not enemy:
            _WITHERED_ENEMIES[id(enemy)] = enemy
            enemy.definition = replace(enemy.definition, armor_class=max(0, enemy.definition.armor_class - 3))
            await session.send(f"{enemy.definition.name} WITHERS; its armor class is reduced by 3 for this encounter.\r\n")

    await _complete_use(session, ability)
    return True


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


def install_class_progression_runtime(player_session_class) -> None:
    """Make levels 1-9 feel like a growing class rather than only larger numbers."""
    install_class_progression_content()
    if getattr(player_session_class, "_class_progression_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt
    previous_use = player_session_class.use_ability
    previous_close = player_session_class.close

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is None:
            return
        last = _last_announced_level(self.database, self.character.id)
        if last is None:
            _set_last_announced_level(self.database, self.character.id, self.character.level)
            await self.send(
                "\r\nYour class now has a complete early-midgame progression. Type CLASS for your role, unlocked tools, and next ability.\r\n"
            )
        else:
            await _announce_pending_level(self)

    async def use_ability(self, ability_text: str) -> None:
        ability, target_text = _resolve_ability(self, ability_text)
        if ability is not None and ability.key in HANDLED_ABILITIES:
            handled = await _use_progression_ability(self, ability, target_text)
            if handled:
                return
        await previous_use(self, ability_text)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        await _announce_pending_level(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"class", "role", "class kit", "class progression"}:
            await _show_class(self)
            return
        if normalized in {"class gear", "role gear", "signature gear"}:
            await _show_class_gear(self)
            return
        if normalized in {"next ability", "next spell", "next class ability"}:
            next_ability = _next_ability(self)
            if next_ability is None:
                await self.send("You have unlocked every ability in the current level 1-9 class pass.\r\n")
            else:
                await self.send(
                    f"Next: level {next_ability.unlock_level} - {next_ability.name}. {next_ability.description}\r\n"
                    f"When unlocked: {_command_for(next_ability)}\r\n"
                )
            return
        if normalized.startswith("ability "):
            await _show_ability_detail(self, stripped.split(maxsplit=1)[1])
            return

        # Exact direct ability names remain convenient in a Telnet client. Targeted
        # abilities still use CAST <ability> <name> so the parser stays unambiguous.
        ability, target_text = _resolve_ability(self, stripped)
        if ability is not None and not target_text and normalized in {
            ability.name.lower(), ability.key.replace("_", " ").lower()
        }:
            if ability.category not in {"healing", "ally_buff", "healing_over_time", "ally_protection"}:
                if await _use_progression_ability(self, ability, ""):
                    await _announce_pending_level(self)
                    return

        await _delegate_prompt(self, previous_prompt, command)
        await _announce_pending_level(self)
        if normalized in {"help", "?", "help all", "help full"}:
            await self.send(
                "Class progression: CLASS/ROLE shows your combat identity and unlocks; NEXT ABILITY previews the next level tool; "
                "ABILITY <name> explains one tool; CLASS GEAR shows your signature midgame item and recipe.\r\n"
            )

    async def close(self) -> None:
        for task in tuple(getattr(self, "_class_progression_tasks", set())):
            if not task.done():
                task.cancel()
        await previous_close(self)

    player_session_class.enter_character = enter_character
    player_session_class.use_ability = use_ability
    player_session_class.playing_prompt = playing_prompt
    player_session_class.close = close
    player_session_class._class_progression_runtime_installed = True
