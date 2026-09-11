from __future__ import annotations

from dataclasses import dataclass
from random import random

import mud.crafting as crafting
import mud.economy_loop as economy
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem


# This pass keeps common monster loot dependable while reserving a smaller
# secondary-drop roll for the materials that make repeated hunting exciting.
# The intent is to reward grinding without making a short dry streak feel like
# the player accomplished nothing.
@dataclass(frozen=True, slots=True)
class SecondaryDrop:
    item_key: str
    chance: float
    quantity: int = 1


TOUGH_SINEW = ItemDefinition(
    key="tough_sinew",
    name="Tough Sinew",
    description=(
        "Clean lengths of strong tendon taken from a beast. Tailors use it as natural reinforcement "
        "where ordinary thread would stretch or tear."
    ),
    category="material",
    tier=1,
)

IMP_EMBER_SHARD = ItemDefinition(
    key="imp_ember_shard",
    name="Imp Ember Shard",
    description=(
        "A hard ember-dark sliver sometimes found beneath an imp's horn ridge. It stays faintly warm "
        "and can be fitted into compact weapons without adding much weight."
    ),
    category="material",
    tier=1,
)

REINFORCED_FIELD_VEST = ItemDefinition(
    key="reinforced_field_vest",
    name="Reinforced Field Vest",
    description=(
        "A practical hide vest lined with woven cotton and closed with small iron fittings. No one trade "
        "produces all of its inputs, which makes it a natural early market item."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Reinforced Field Vest",
        "chest",
        armor_class=2,
        stat_bonuses=CharacterStats(hp=2),
    ),
    tier=1,
)

SINEW_TRAIL_BOOTS = ItemDefinition(
    key="sinew_trail_boots",
    name="Sinew-Bound Trail Boots",
    description=(
        "Soft hide trail boots tightened with cleaned sinew and cotton thread. They trade a little bulk "
        "for reliable footing on roots, broken stone, and wet roads."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Sinew-Bound Trail Boots",
        "feet",
        armor_class=1,
        stat_bonuses=CharacterStats(grace=1, hp=1),
    ),
    tier=1,
)

CINDERFANG_DIRK = ItemDefinition(
    key="cinderfang_dirk",
    name="Cinderfang Dirk",
    description=(
        "A compact iron blade with an imp-horn grip and a tiny ember shard locked into the pommel. "
        "It is a better reward for a persistent imp hunter than a second pile of ordinary horns."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Cinderfang Dirk",
        "main_hand",
        stat_bonuses=CharacterStats(might=2, mind=1),
    ),
    tier=1,
)

BALANCE_ITEMS: tuple[ItemDefinition, ...] = (
    TOUGH_SINEW,
    IMP_EMBER_SHARD,
    REINFORCED_FIELD_VEST,
    SINEW_TRAIL_BOOTS,
    CINDERFANG_DIRK,
)

REINFORCED_FIELD_VEST_RECIPE = CraftingRecipe(
    key="sew_reinforced_field_vest",
    trade_skill_key="tailoring",
    output_item_key=REINFORCED_FIELD_VEST.key,
    minimum_skill=6,
    high_skill_quality_threshold=28,
    materials=(
        MaterialRequirement("rough_hide", 2),
        MaterialRequirement("cotton_cloth", 1),
        MaterialRequirement("iron_ingot", 1),
    ),
    output_quantity=1,
    station_key="loom",
    description="Line hunted hide with woven cotton and iron fittings for a durable field vest.",
    design_status="live_social_economy_recipe",
)

SINEW_TRAIL_BOOTS_RECIPE = CraftingRecipe(
    key="sew_sinew_trail_boots",
    trade_skill_key="tailoring",
    output_item_key=SINEW_TRAIL_BOOTS.key,
    minimum_skill=4,
    high_skill_quality_threshold=24,
    materials=(
        MaterialRequirement("rough_hide", 1),
        MaterialRequirement("tough_sinew", 1),
        MaterialRequirement("cotton_thread", 1),
    ),
    output_quantity=1,
    station_key="loom",
    description="Bind light hide with sinew and cotton thread into hard-wearing trail boots.",
    design_status="live_social_economy_recipe",
)

CINDERFANG_DIRK_RECIPE = CraftingRecipe(
    key="forge_cinderfang_dirk",
    trade_skill_key="blacksmithing",
    output_item_key=CINDERFANG_DIRK.key,
    minimum_skill=8,
    high_skill_quality_threshold=30,
    materials=(
        MaterialRequirement("iron_ingot", 1),
        MaterialRequirement("imp_horn", 1),
        MaterialRequirement("imp_ember_shard", 1),
    ),
    output_quantity=1,
    station_key="forge",
    description="Fit a rare ember shard and imp-horn grip to a compact iron dirk.",
    design_status="live_social_economy_recipe",
)

BALANCE_RECIPES: tuple[CraftingRecipe, ...] = (
    REINFORCED_FIELD_VEST_RECIPE,
    SINEW_TRAIL_BOOTS_RECIPE,
    CINDERFANG_DIRK_RECIPE,
)

SECONDARY_LOOT: dict[str, tuple[SecondaryDrop, ...]] = {
    "sewer_rat": (SecondaryDrop(TOUGH_SINEW.key, 0.35),),
    "human_sootstep_burrower": (SecondaryDrop(TOUGH_SINEW.key, 0.55),),
    "troll_breach_scavenger": (SecondaryDrop(TOUGH_SINEW.key, 0.50),),
    "small_imp": (SecondaryDrop(IMP_EMBER_SHARD.key, 0.30),),
}

# Source copy intentionally names other player roles before long self-sufficient
# material chains. The game never hard-locks a profession, but this makes the
# convenient path socially obvious.
SOURCE_HINTS: dict[str, str] = {
    "rough_hide": "hunt beasts such as rats, wolves, and the Blackwall burrower; hunters usually have extras",
    "tough_sinew": "secondary beast drop; trade with players who spend time hunting",
    "imp_horn": "hunt imps; repeated imp runs create a steady supply",
    "imp_ember_shard": "uncommon imp drop; dedicated imp hunters are the fastest source",
    "raw_cotton": "harvest Cotton Patches on the Forest Elf Greenway",
    "cotton_thread": "spin Raw Cotton at a loom; a practiced Tailor can supply it quickly",
    "cotton_cloth": "weave Cotton Thread at a loom; Forest Elf gatherers and Tailors are a natural source",
    "iron_ore": "mine Iron Veins at the Blackglass Arch or Dwarven freight workings",
    "iron_ingot": "smelt Iron Ore at a forge; Dwarven miners and smiths are a natural source",
    "greenleaf": "gather Greenleaf from low-level herb patches",
}

HUMAN_BLACKWALL_ROOMS = frozenset(
    {
        "human_cinder_ward",
        "human_blackwall_readiness_yard",
        "human_blackwall_caravan_court",
        "human_sootstep_tunnel_mouth",
        "human_sootstep_service_tunnel",
        "human_smuggler_cistern",
        "human_blackwall_archive_annex",
        "human_outer_caravan_road",
        "human_first_mile_overlook",
    }
)


def _register_recipe(recipe: CraftingRecipe) -> None:
    if recipe.trade_skill_key == "blacksmithing" and recipe.key not in crafting.BLACKSMITHING_RECIPES_BY_KEY:
        crafting.BLACKSMITHING_RECIPES = crafting.BLACKSMITHING_RECIPES + (recipe,)
        crafting.BLACKSMITHING_RECIPES_BY_KEY[recipe.key] = recipe
    elif recipe.trade_skill_key == "tailoring" and recipe.key not in crafting.TAILORING_RECIPES_BY_KEY:
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + (recipe,)
        crafting.TAILORING_RECIPES_BY_KEY[recipe.key] = recipe

    if recipe.key not in crafting.RECIPES_BY_KEY:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + (recipe,)
        crafting.RECIPES_BY_KEY[recipe.key] = recipe


def install_economy_balance_content() -> None:
    """Register the second economy pass and tune the first Human trade loop."""
    economy.install_economy_content()

    known_items = {item.key for item in crafting.ITEMS}
    additions = tuple(item for item in BALANCE_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    for recipe in BALANCE_RECIPES:
        _register_recipe(recipe)

    # Human first-session economy walk-through:
    # - the Burrower guarantees enough useful hide to matter,
    # - Caravan Court exposes a sewing station immediately after that fight,
    # - the road beyond Blackwall introduces gathering,
    # - the best early vest still needs cotton cloth and an iron ingot from other
    #   routes/players, so the social shortcut is visible instead of theoretical.
    economy.LOOT_TABLES["human_sootstep_burrower"] = (
        economy.LootDrop("rough_hide", 2),
    )
    economy.ROOM_STATIONS["human_blackwall_caravan_court"] = ("loom",)
    economy.ROOM_RESOURCE_NODE_KEYS["human_outer_caravan_road"] = ("greenleaf_patch",)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _secondary_for_enemy(enemy) -> tuple[SecondaryDrop, ...]:
    key = str(getattr(getattr(enemy, "definition", None), "key", ""))
    if key in SECONDARY_LOOT:
        return SECONDARY_LOOT[key]
    normalized = key.lower()
    if "imp" in normalized:
        return (SecondaryDrop(IMP_EMBER_SHARD.key, 0.20),)
    if any(word in normalized for word in ("wolf", "rat", "boar", "beast", "burrower")):
        return (SecondaryDrop(TOUGH_SINEW.key, 0.25),)
    return ()


async def _award_secondary_loot(session, enemy) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    awarded: list[str] = []
    for drop in _secondary_for_enemy(enemy):
        if random() > drop.chance:
            continue
        session.database.add_item(character.id, drop.item_key, drop.quantity)
        definition = crafting.ITEMS_BY_KEY.get(drop.item_key)
        name = definition.name if definition is not None else drop.item_key
        awarded.append(f"{drop.quantity}x {name}")
    if awarded:
        await session.send("Bonus loot: " + ", ".join(awarded) + ".\r\n")


def _missing_materials(session, recipe: CraftingRecipe) -> list[tuple[MaterialRequirement, int]]:
    character = getattr(session, "character", None)
    if character is None:
        return []
    result: list[tuple[MaterialRequirement, int]] = []
    for requirement in recipe.materials:
        owned = session.database.item_quantity(character.id, requirement.item_key)
        missing = max(0, requirement.quantity - owned)
        if missing:
            result.append((requirement, missing))
    return result


def _trade_recipe_pool() -> tuple[CraftingRecipe, ...]:
    # Keep NEEDS focused on the hand-authored social recipes rather than dumping
    # the entire baseline metal/textile ladders at a new player.
    combined = economy.ECONOMY_RECIPES + BALANCE_RECIPES
    seen: set[str] = set()
    result: list[CraftingRecipe] = []
    for recipe in combined:
        if recipe.key in seen:
            continue
        seen.add(recipe.key)
        result.append(recipe)
    return tuple(result)


async def _show_needs(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return

    scored = []
    for recipe in _trade_recipe_pool():
        missing = _missing_materials(session, recipe)
        missing_units = sum(amount for _requirement, amount in missing)
        skill = crafting.trade_skill_value(session.database, character.id, recipe.trade_skill_key)
        skill_gap = max(0, recipe.minimum_skill - skill)
        scored.append((missing_units, skill_gap, recipe.key, recipe, missing, skill))
    scored.sort(key=lambda row: (row[0], row[1], row[2]))

    await session.send("\r\n--- What Should I Trade For? ---\r\n")
    await session.send(
        "These are the closest early upgrades built around materials from different play styles. "
        "Trading for a missing input or the finished item is intentionally faster than mastering every profession yourself.\r\n"
    )

    for _missing_units, _skill_gap, _key, recipe, missing, skill in scored[:5]:
        output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
        output_name = output.name if output is not None else recipe.output_item_key
        await session.send(
            f"\r\n{output_name} - {recipe.trade_skill_key.title()} {skill}/{recipe.minimum_skill}\r\n"
        )
        if not missing:
            await session.send("  Materials: READY. Find the required station or trade the inputs to a specialist.\r\n")
        else:
            await session.send("  Missing:\r\n")
            for requirement, amount in missing:
                definition = crafting.ITEMS_BY_KEY.get(requirement.item_key)
                name = definition.name if definition is not None else requirement.item_key
                hint = SOURCE_HINTS.get(requirement.item_key, "ask another player who works this material")
                await session.send(f"  - {amount}x {name}: {hint}.\r\n")
        if skill < recipe.minimum_skill:
            await session.send(
                f"  Fast path: your {recipe.trade_skill_key.title()} is below this recipe, so a practiced crafter can make or sell it sooner.\r\n"
            )


async def _show_economy_route(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if character.race == "human" or (character.current_room or "") in HUMAN_BLACKWALL_ROOMS:
        await session.send(
            "\r\n--- Human Starter Economy Route ---\r\n"
            "1) Follow the Blackwall opening to the Sootstep Burrower. The kill now guarantees 2x Rough Hide and can also yield Tough Sinew.\r\n"
            "2) Return to Caravan Court. Its wagon-repair bench counts as a Loom / Sewing Bench for early Tailoring.\r\n"
            "3) Type NEEDS. Reinforced Field Vest is the clearest first social upgrade: your hunted hide combines with Cotton Cloth and an Iron Ingot.\r\n"
            "4) Cotton production is strongest on the Forest Elf route; iron production is strongest around Human/Dwarven mining and forges. Ask, GIVE, or TRADE instead of running every chain yourself.\r\n"
            "5) Beyond Blackwall, the Outer Caravan Road has a Greenleaf Patch so the first trip outside also teaches that useful resources live in the world, not in menus.\r\n"
            "6) Equip the crafted/traded upgrade and go back to harder hunting. That closes the intended hunt -> resources -> craft -> trade -> upgrade -> hunt loop.\r\n"
        )
        return
    await session.send(
        "Hunt for monster materials, use RESOURCES to find local gathering/stations, then type NEEDS to see which missing inputs are fastest to trade for.\r\n"
    )


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_economy_balance_runtime(player_session_class) -> None:
    """Install trade incentives, secondary loot rolls, and starter-loop tuning."""
    if getattr(player_session_class, "_economy_balance_runtime_installed", False):
        return
    install_economy_balance_content()

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if previous_finish_enemy is not None:
        async def _finish_enemy_defeat(self, enemy) -> None:
            eligible = getattr(self, "active_enemy", None) is enemy
            await previous_finish_enemy(self, enemy)
            if eligible:
                await _award_secondary_loot(self, enemy)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        prompt_text = "\r\n> "
        current = getattr(self, "current_prompt_text", None)
        if callable(current):
            try:
                prompt_text = "\r\n" + str(current())
            except Exception:
                pass
        command = await self.prompt(prompt_text)
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        normalized = _normalize(command)
        if normalized in {"needs", "craft needs", "market needs", "what do i need"}:
            await _show_needs(self)
            return
        if normalized in {"economy route", "starter economy", "starter economy route"}:
            await _show_economy_route(self)
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._economy_balance_runtime_installed = True
