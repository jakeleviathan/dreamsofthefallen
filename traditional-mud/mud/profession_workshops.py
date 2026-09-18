from __future__ import annotations

import asyncio
from dataclasses import dataclass

import mud.crafting as crafting
import mud.economy_loop as economy
from mud.crafting import ConsumableEffect, ItemDefinition, ResourceNodeDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem


# ---------------------------------------------------------------------------
# Missing professions: authored starter content
# ---------------------------------------------------------------------------

ARCANE_RESIDUE = ItemDefinition(
    "arcane_residue",
    "Arcane Residue",
    "A faint violet powder left where minor otherworldly creatures or unstable magic have shed energy. Enchanters use it to wake simple runes.",
    "material",
    tier=1,
)
FIELD_GRAIN = ItemDefinition(
    "field_grain",
    "Field Grain",
    "A hardy Astralian grain harvested in small golden heads and ground for simple trail food.",
    "food_material",
    tier=1,
)
MARSH_ONION = ItemDefinition(
    "marsh_onion",
    "Marsh Onion",
    "A sharp little wetland bulb used to give broth and stew a savory base.",
    "food_material",
    tier=1,
)

RUNED_IRON_DAGGER = ItemDefinition(
    "runed_iron_dagger",
    "Runed Iron Dagger",
    "An ordinary iron dagger awakened with a shallow violet rune. The enchantment favors a wielder who mixes physical and magical force.",
    "equipment",
    EquipmentItem(
        "Runed Iron Dagger",
        "weapon",
        stat_bonuses=CharacterStats(might=1, mind=1),
        scripted_effects=("minor_runic_focus",),
    ),
    tier=1,
)
GREENWARD_HOOD = ItemDefinition(
    "greenward_hood",
    "Greenward Hood",
    "A cotton hood carrying a small living ward fixed with herbal tincture and arcane residue.",
    "equipment",
    EquipmentItem(
        "Greenward Hood",
        "head",
        armor_class=1,
        stat_bonuses=CharacterStats(love=1, hp=1),
        scripted_effects=("minor_greenward",),
    ),
    tier=1,
)
MOONLIT_FOCUS_DAGGER = ItemDefinition(
    "moonlit_focus_dagger",
    "Moonlit Focus Dagger",
    "A Moonsteel dagger re-etched with Moonsilver and layered arcane residue so its edge doubles as a spell focus.",
    "equipment",
    EquipmentItem(
        "Moonlit Focus Dagger",
        "weapon",
        stat_bonuses=CharacterStats(might=4, mind=2),
        scripted_effects=("moonlit_focus",),
    ),
    tier=4,
)

TRAIL_FLATBREAD = ItemDefinition(
    "trail_flatbread",
    "Trail Flatbread",
    "A dense field-grain flatbread cooked for travel and meant to survive a day in a pack.",
    "food",
    consumable=ConsumableEffect(use_mode="eat", heal_hp=8, effect_tags=("food", "trail_food")),
    tier=1,
)
GREENLEAF_BROTH = ItemDefinition(
    "greenleaf_broth",
    "Greenleaf Broth",
    "A savory broth of grain, Marsh Onion, and medicinal Greenleaf. It is food first, medicine second.",
    "food",
    consumable=ConsumableEffect(
        use_mode="eat",
        heal_hp=12,
        temporary_stat_bonuses=CharacterStats(love=1),
        duration_ticks=15,
        effect_tags=("food", "warming_broth"),
    ),
    tier=1,
)
BITTERROOT_STEW = ItemDefinition(
    "bitterroot_stew",
    "Bitterroot Stew",
    "A thick field-grain stew that balances Bitterroot's medicinal bite with roasted Marsh Onion.",
    "food",
    consumable=ConsumableEffect(
        use_mode="eat",
        heal_hp=18,
        temporary_stat_bonuses=CharacterStats(hp=2),
        duration_ticks=20,
        effect_tags=("food", "hearty_stew"),
    ),
    tier=1,
)

FIELDGRAIN_PATCH = ResourceNodeDefinition(
    "fieldgrain_patch",
    "Field-Grain Patch",
    "harvesting",
    FIELD_GRAIN.key,
    minimum_skill=0,
    design_status="starter_cooking_resource",
    tier=1,
    region_hint="Cultivated paths and settlement edges.",
)
MARSH_ONION_BED = ResourceNodeDefinition(
    "marsh_onion_bed",
    "Marsh Onion Bed",
    "harvesting",
    MARSH_ONION.key,
    minimum_skill=5,
    design_status="starter_cooking_resource",
    tier=1,
    region_hint="Damp river paths and maintained wet gardens.",
)

ENCHANTING_RECIPES = (
    CraftingRecipe(
        "enchant_runed_iron_dagger",
        "enchanting",
        RUNED_IRON_DAGGER.key,
        0,
        25,
        (
            MaterialRequirement("iron_dagger", 1),
            MaterialRequirement(ARCANE_RESIDUE.key, 1),
            MaterialRequirement("lavender_essential_oil", 1),
        ),
        station_key="enchanting_table",
        description="Etch a simple focus rune into an Iron Dagger, wake it with Arcane Residue, and seal the cut with aromatic oil.",
        design_status="starter_enchanting_live",
    ),
    CraftingRecipe(
        "enchant_greenward_hood",
        "enchanting",
        GREENWARD_HOOD.key,
        8,
        35,
        (
            MaterialRequirement("cotton_hood", 1),
            MaterialRequirement(ARCANE_RESIDUE.key, 1),
            MaterialRequirement("greenleaf_tincture", 1),
        ),
        station_key="enchanting_table",
        description="Bind a small restorative ward into a Cotton Hood with Greenleaf Tincture as the sympathetic medium.",
        design_status="starter_enchanting_live",
    ),
    CraftingRecipe(
        "enchant_moonlit_focus_dagger",
        "enchanting",
        MOONLIT_FOCUS_DAGGER.key,
        50,
        85,
        (
            MaterialRequirement("moonsteel_dagger", 1),
            MaterialRequirement(ARCANE_RESIDUE.key, 2),
            MaterialRequirement("moonsilver_ore", 1),
        ),
        station_key="enchanting_table",
        description="Re-etch a Moonsteel Dagger with Moonsilver filings and layered residue to turn the blade into a stronger magical focus.",
        design_status="midgame_enchanting_live",
    ),
)

COOKING_RECIPES = (
    CraftingRecipe(
        "cook_trail_flatbread",
        "cooking",
        TRAIL_FLATBREAD.key,
        0,
        20,
        (
            MaterialRequirement(FIELD_GRAIN.key, 2),
            MaterialRequirement("spring_water", 1),
        ),
        station_key="cookfire",
        description="Grind Field Grain, mix it with clean water, and cook a dense flatbread directly on a hot stone.",
        design_status="starter_cooking_live",
    ),
    CraftingRecipe(
        "cook_greenleaf_broth",
        "cooking",
        GREENLEAF_BROTH.key,
        5,
        30,
        (
            MaterialRequirement(FIELD_GRAIN.key, 1),
            MaterialRequirement(MARSH_ONION.key, 1),
            MaterialRequirement("greenleaf", 1),
            MaterialRequirement("spring_water", 1),
        ),
        station_key="cookfire",
        description="Simmer Field Grain and Marsh Onion in clean water, adding Greenleaf late enough to keep its useful oils.",
        design_status="starter_cooking_live",
    ),
    CraftingRecipe(
        "cook_bitterroot_stew",
        "cooking",
        BITTERROOT_STEW.key,
        10,
        40,
        (
            MaterialRequirement(FIELD_GRAIN.key, 2),
            MaterialRequirement(MARSH_ONION.key, 1),
            MaterialRequirement("bitterroot", 1),
        ),
        station_key="cookfire",
        description="Cook a thick grain-and-onion stew and shave Bitterroot into it carefully so the medicinal bitterness does not overpower the meal.",
        design_status="starter_cooking_live",
    ),
)


def _register_items(items: tuple[ItemDefinition, ...]) -> None:
    additions = tuple(item for item in items if item.key not in crafting.ITEMS_BY_KEY)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})


def _register_nodes(nodes: tuple[ResourceNodeDefinition, ...]) -> None:
    additions = tuple(node for node in nodes if node.key not in crafting.RESOURCE_NODES_BY_KEY)
    if additions:
        crafting.RESOURCE_NODES = crafting.RESOURCE_NODES + additions
        crafting.RESOURCE_NODES_BY_KEY.update({node.key: node for node in additions})


def _register_recipes(recipes: tuple[CraftingRecipe, ...], attr_name: str) -> None:
    existing = getattr(crafting, attr_name, ())
    existing_keys = {recipe.key for recipe in existing}
    additions = tuple(recipe for recipe in recipes if recipe.key not in existing_keys)
    if additions:
        setattr(crafting, attr_name, existing + additions)

    all_keys = set(crafting.RECIPES_BY_KEY)
    all_additions = tuple(recipe for recipe in recipes if recipe.key not in all_keys)
    if all_additions:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + all_additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in all_additions})


def install_missing_profession_content() -> None:
    _register_items((
        ARCANE_RESIDUE,
        FIELD_GRAIN,
        MARSH_ONION,
        RUNED_IRON_DAGGER,
        GREENWARD_HOOD,
        MOONLIT_FOCUS_DAGGER,
        TRAIL_FLATBREAD,
        GREENLEAF_BROTH,
        BITTERROOT_STEW,
    ))
    _register_nodes((FIELDGRAIN_PATCH, MARSH_ONION_BED))
    _register_recipes(ENCHANTING_RECIPES, "ENCHANTING_RECIPES")
    _register_recipes(COOKING_RECIPES, "COOKING_RECIPES")

    # Starter access to the new gathering/crafting loops uses rooms already
    # proven by the production economy slice.
    for room_key, node_key in (
        ("forest_elf_greenway", FIELDGRAIN_PATCH.key),
        ("forest_elf_old_river_path", MARSH_ONION_BED.key),
    ):
        current = economy.ROOM_RESOURCE_NODE_KEYS.get(room_key, ())
        if node_key not in current:
            economy.ROOM_RESOURCE_NODE_KEYS[room_key] = current + (node_key,)

    station_additions = {
        "dwarf_workshop_tier": ("enchanting_table",),
        "human_cinder_lane": ("enchanting_table",),
        "forest_elf_hearthwalk": ("cookfire",),
        "goblin_tinker_row": ("cookfire",),
    }
    for room_key, additions in station_additions.items():
        current = economy.ROOM_STATIONS.get(room_key, ())
        economy.ROOM_STATIONS[room_key] = current + tuple(key for key in additions if key not in current)

    economy.STATION_LABELS.update({
        "enchanting_table": "Runic Workbench",
        "cookfire": "Cookfire",
    })

    # Small imps now feed the starter Enchanting loop as well as smithing.
    imp_drops = economy.LOOT_TABLES.get("small_imp", (economy.LootDrop(economy.IMP_HORN.key),))
    if not any(drop.item_key == ARCANE_RESIDUE.key for drop in imp_drops):
        economy.LOOT_TABLES["small_imp"] = imp_drops + (economy.LootDrop(ARCANE_RESIDUE.key),)


# ---------------------------------------------------------------------------
# Crafted food is real consumable gameplay, not just inventory output.
# ---------------------------------------------------------------------------

FOOD_TICK_SECONDS = 5.0


def _food_names(item: ItemDefinition) -> set[str]:
    return {
        item.key.replace("_", " ").lower(),
        item.name.lower(),
    }


def _resolve_food(session, target: str) -> tuple[ItemDefinition | None, str | None]:
    wanted = " ".join(target.strip().lower().replace("_", " ").split())
    candidates = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if item is None or item.consumable is None or item.consumable.use_mode != "eat":
            continue
        names = _food_names(item)
        quality = 2 if wanted in names else 1 if wanted and any(wanted in name for name in names) else 0
        if quality:
            candidates.append((quality, item))
    if not candidates:
        return None, "You are not carrying edible food by that name."
    best = max(quality for quality, _item in candidates)
    matches = [item for quality, item in candidates if quality == best]
    unique = {item.key: item for item in matches}
    if len(unique) != 1:
        names = ", ".join(item.name for item in unique.values())
        return None, f"Be more specific: {names}."
    return next(iter(unique.values())), None


async def _expire_food_bonus(session, item_name: str, bonus: CharacterStats, seconds: float) -> None:
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        return
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return
    inverse = CharacterStats(
        might=-bonus.might,
        grace=-bonus.grace,
        love=-bonus.love,
        mind=-bonus.mind,
        hp=-bonus.hp,
    )
    combatant.stats = combatant.stats.plus(inverse)
    combatant.max_hp = max(1, combatant.max_hp - max(0, bonus.hp))
    combatant.current_hp = min(combatant.current_hp, combatant.max_hp)
    mana_bonus = max(0, bonus.mana_bonus)
    combatant.max_mana = max(0, combatant.max_mana - mana_bonus)
    combatant.current_mana = min(combatant.current_mana, combatant.max_mana)
    await session.send(f"\r\nThe temporary benefit from {item_name} fades.\r\n")
    sender = getattr(session, "send_client_state", None)
    if callable(sender):
        await sender()


async def _eat(session, target: str) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to eat while fighting.\r\n")
        return
    item, error = _resolve_food(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert item is not None and item.consumable is not None
    if not session.database.consume_item(session.character.id, item.key, 1):
        await session.send("That food is no longer in your inventory.\r\n")
        return

    effect = item.consumable
    combatant = getattr(session, "combatant", None)
    healed = 0
    duration = 0.0
    if combatant is not None:
        before = combatant.current_hp
        combatant.current_hp = min(combatant.max_hp, combatant.current_hp + max(0, effect.heal_hp))
        healed = combatant.current_hp - before

        bonus = effect.temporary_stat_bonuses
        if effect.duration_ticks > 0 and bonus != CharacterStats():
            combatant.stats = combatant.stats.plus(bonus)
            combatant.max_hp += max(0, bonus.hp)
            combatant.max_mana += max(0, bonus.mana_bonus)
            duration = effect.duration_ticks * FOOD_TICK_SECONDS
            task = asyncio.create_task(_expire_food_bonus(session, item.name, bonus, duration))
            tasks = getattr(session, "_food_effect_tasks", None)
            if tasks is None:
                tasks = set()
                session._food_effect_tasks = tasks
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    text = f"You eat {item.name}."
    if healed:
        text += f" You recover {healed} HP."
    if duration:
        text += f" Its temporary nourishment lasts about {int(duration)} seconds."
    await session.send(text + "\r\n")
    sender = getattr(session, "send_client_state", None)
    if callable(sender):
        await sender()


async def _show_food(session) -> None:
    foods = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if item is None or item.consumable is None or item.consumable.use_mode != "eat":
            continue
        foods.append((item, int(row["quantity"])))
    await session.send(f"\r\n{_paint(_HEADER, '=== FOOD ===')}\r\n")
    if not foods:
        await session.send("You are not carrying prepared food. Cook at a Cookfire to make some.\r\n")
        return
    for item, quantity in foods:
        await session.send(f"  {quantity}x {_paint(_NAME, item.name)} — {item.description}\r\n")
    await session.send("\r\nUse EAT <food>.\r\n")


# ---------------------------------------------------------------------------
# Profession / gathering character sheet
# ---------------------------------------------------------------------------

_RESET = "\x1b[0m"
_HEADER = "\x1b[1;97m"
_NAME = "\x1b[96m"
_ACCENT = "\x1b[1;36m"
_PROGRESS = "\x1b[92m"
_DIM = "\x1b[90m"
_GOLD = "\x1b[93m"
_BAD = "\x1b[91m"


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{_RESET}"


def _skill_progress(session, key: str) -> tuple[int, int]:
    row = session.database.get_trade_skill_progress(session.character.id, key)
    return int(row["uses"]), int(row["skill_xp"])


def _bar(current: int, low: int, high: int | None, width: int = 20) -> tuple[str, str]:
    if high is None or high <= low:
        return "[" + ("█" * width) + "]", "top authored milestone"
    earned = max(0, min(high - low, current - low))
    needed = high - low
    filled = int(round(width * earned / max(1, needed)))
    return "[" + ("█" * filled) + ("░" * (width - filled)) + "]", f"{earned}/{needed}"


def _recipe_milestones(skill_key: str) -> tuple[tuple[int, str], ...]:
    rows: dict[int, str] = {}
    for recipe in crafting.ALL_RECIPES:
        if recipe.trade_skill_key != skill_key:
            continue
        rows.setdefault(recipe.minimum_skill, economy._recipe_output_name(recipe))
    return tuple(sorted(rows.items()))


def _milestones(skill_key: str) -> tuple[tuple[int, str], ...]:
    if skill_key == "blacksmithing":
        return tuple((tier.blacksmithing_skill, tier.name) for tier in crafting.METAL_TIERS)
    if skill_key == "tailoring":
        return tuple((tier.tailoring_skill, tier.name) for tier in crafting.TEXTILE_TIERS)
    if skill_key == "mining":
        return tuple(
            (tier.mining_skill, tier.name)
            for tier in crafting.METAL_TIERS
            if tier.mining_skill is not None
        )
    if skill_key == "harvesting":
        return tuple((tier.harvesting_skill, tier.name) for tier in crafting.TEXTILE_TIERS)
    if skill_key == "herbalism":
        nodes = sorted(
            (
                node.minimum_skill,
                node.name,
            )
            for node in crafting.RESOURCE_NODES
            if node.gathering_skill_key == "herbalism"
        )
        dedup: dict[int, str] = {}
        for threshold, name in nodes:
            dedup.setdefault(threshold, name)
        return tuple(dedup.items())
    return _recipe_milestones(skill_key)


def _milestone_state(skill_key: str, skill: int) -> tuple[str, int, str | None, int | None]:
    rows = _milestones(skill_key)
    if not rows:
        return "Practiced", 0, None, None
    current_name = rows[0][1]
    current_floor = rows[0][0]
    next_name = None
    next_threshold = None
    for threshold, name in rows:
        if threshold <= skill:
            current_name = name
            current_floor = threshold
            continue
        next_name = name
        next_threshold = threshold
        break
    return current_name, current_floor, next_name, next_threshold


def _unlocked_recipe_count(skill_key: str, skill: int) -> tuple[int, int]:
    recipes = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == skill_key]
    return (
        sum(1 for recipe in recipes if recipe.minimum_skill <= skill),
        len(recipes),
    )


async def _show_professions(session) -> None:
    await session.send(f"\r\n{_paint(_HEADER, '=== PROFESSIONS & GATHERING ===')}\r\n")
    await session.send(
        "Use-based trade skills are the number shown here: successful gathering or crafting raises the relevant skill.\r\n"
    )

    await session.send(f"\r\n{_paint(_ACCENT, 'CRAFTING')}\r\n")
    for profession in crafting.PROFESSIONS:
        uses, skill = _skill_progress(session, profession.key)
        current, floor, next_name, next_threshold = _milestone_state(profession.key, skill)
        bar, fraction = _bar(skill, floor, next_threshold)
        unlocked, total = _unlocked_recipe_count(profession.key, skill)
        await session.send(
            f"\r\n  {_paint(_NAME, profession.name)}\r\n"
            f"  Skill     {skill}   {_paint(_PROGRESS, bar)}  {fraction}\r\n"
            f"  Current   {current}\r\n"
            + (
                f"  Next      {next_name} at {next_threshold}\r\n"
                if next_name is not None
                else "  Next      No higher authored milestone yet\r\n"
            )
            + f"  Recipes   {unlocked}/{total} unlocked"
            + (f"   |   Uses {uses}" if uses else "")
            + "\r\n"
        )

    await session.send(f"\r\n{_paint(_ACCENT, 'GATHERING')}\r\n")
    for definition in crafting.GATHERING_SKILLS:
        uses, skill = _skill_progress(session, definition.key)
        current, floor, next_name, next_threshold = _milestone_state(definition.key, skill)
        bar, fraction = _bar(skill, floor, next_threshold)
        await session.send(
            f"\r\n  {_paint(_NAME, definition.name)}\r\n"
            f"  Skill     {skill}   {_paint(_PROGRESS, bar)}  {fraction}\r\n"
            f"  Current   {current}\r\n"
            + (
                f"  Next      {next_name} at {next_threshold}\r\n"
                if next_name is not None
                else "  Next      No higher authored milestone yet\r\n"
            )
            + (f"  Uses      {uses}\r\n" if uses else "")
        )

    await session.send(
        "\r\nCommands: FORGE, TAILOR, ENCHANT, COOK, MINING, HARVESTING, HERBALISM, RECIPES.\r\n"
    )


# ---------------------------------------------------------------------------
# Workshop interfaces
# ---------------------------------------------------------------------------

WORKSHOP_META = {
    "blacksmithing": ("FORGE", "forge", "Forge"),
    "tailoring": ("TAILORING WORKBENCH", "loom", "Loom / Sewing Bench"),
    "enchanting": ("ENCHANTING WORKBENCH", "enchanting_table", "Runic Workbench"),
    "cooking": ("COOKFIRE", "cookfire", "Cookfire"),
}


def _recipe_category(recipe: CraftingRecipe) -> str:
    if recipe.trade_skill_key == "blacksmithing":
        if recipe.key.startswith("smelt_"):
            return "SMELTING & ALLOYING"
        item = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
        if item is not None and item.equipment is not None and item.equipment.slot == "weapon":
            return "WEAPONS"
        return "ARMOR & HARDWARE"
    if recipe.trade_skill_key == "tailoring":
        if recipe.key.startswith(("spin_", "reel_")):
            return "FIBER PREPARATION"
        if recipe.key.startswith("weave_"):
            return "WEAVING"
        return "FINISHED GOODS"
    if recipe.trade_skill_key == "enchanting":
        return "RUNES & ENCHANTED GEAR"
    if recipe.trade_skill_key == "cooking":
        return "MEALS & PROVISIONS"
    return "RECIPES"


async def _show_workshop(session, profession_key: str) -> None:
    title, station_key, station_name = WORKSHOP_META[profession_key]
    uses, skill = _skill_progress(session, profession_key)
    current, floor, next_name, next_threshold = _milestone_state(profession_key, skill)
    bar, fraction = _bar(skill, floor, next_threshold)
    station_here = station_key in economy._stations_here(session)
    recipes = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == profession_key]

    await session.send(
        f"\r\n{_paint(_HEADER, f'=== {title} ===')}\r\n"
        f"Skill: {skill}   {_paint(_PROGRESS, bar)}  {fraction}\r\n"
        f"Current tier: {current}\r\n"
        + (f"Next milestone: {next_name} at {next_threshold}\r\n" if next_name else "")
        + f"Station: {station_name} — "
        + (_paint(_PROGRESS, "HERE") if station_here else _paint(_BAD, "NOT HERE"))
        + "\r\n"
    )

    categories = []
    for recipe in recipes:
        category = _recipe_category(recipe)
        if category not in categories:
            categories.append(category)

    for category in categories:
        await session.send(f"\r\n{_paint(_ACCENT, category)}\r\n")
        group = sorted(
            (recipe for recipe in recipes if _recipe_category(recipe) == category),
            key=lambda recipe: (recipe.minimum_skill, economy._recipe_output_name(recipe).lower()),
        )
        for recipe in group:
            if recipe.minimum_skill > skill and recipe.minimum_skill > skill + 15:
                continue
            state = economy._recipe_state(session, recipe)
            if state["craftable"]:
                label = _paint(_PROGRESS, "CRAFT NOW")
            elif state["skill_ready"]:
                label = _paint(_GOLD, "READY")
            else:
                label = _paint(_DIM, f"SKILL {recipe.minimum_skill}")
            await session.send(
                f"  [{label}] {_paint(_NAME, economy._recipe_output_name(recipe))}\r\n"
            )

    verb = {
        "blacksmithing": "FORGE",
        "tailoring": "TAILOR",
        "enchanting": "ENCHANT",
        "cooking": "COOK",
    }[profession_key]
    await session.send(
        f"\r\nUse {verb} <item> to make something here, or RECIPE <item> for ingredient details.\r\n"
    )


async def _craft_profession(session, profession_key: str, target: str) -> None:
    recipe, error = economy._resolve_recipe(target)
    if error:
        await session.send(error + "\r\n")
        return
    assert recipe is not None
    if recipe.trade_skill_key != profession_key:
        await session.send(
            f"{economy._recipe_output_name(recipe)} is a {economy._profession_name(recipe.trade_skill_key)} recipe, "
            f"not {economy._profession_name(profession_key)}.\r\n"
        )
        return
    await economy._craft(session, target)


# ---------------------------------------------------------------------------
# Shared gathering presentation, including the custom Goblin resource services
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LocalGatherable:
    name: str
    skill_key: str
    minimum_skill: int
    output_name: str
    status: str


def _generic_local_gatherables(session, skill_key: str) -> list[LocalGatherable]:
    result: list[LocalGatherable] = []
    for live in economy._nodes_here(session):
        definition = live.state.definition
        if definition.gathering_skill_key != skill_key:
            continue
        live.refresh()
        output = crafting.ITEMS_BY_KEY.get(definition.output_item_key)
        status = "DEPLETED" if live.state.depleted else f"{live.state.remaining_uses} uses"
        result.append(LocalGatherable(
            definition.name,
            skill_key,
            definition.minimum_skill,
            output.name if output is not None else definition.output_item_key.replace("_", " ").title(),
            status,
        ))
    return result


def _goblin_local_gatherables(session, skill_key: str) -> list[LocalGatherable]:
    if skill_key != "herbalism":
        return []
    result: list[LocalGatherable] = []
    room_key = session.character.current_room or ""
    try:
        from mud.goblin_swamp import GOBLIN_SWAMP_GATHERING
        for state in GOBLIN_SWAMP_GATHERING.nodes_in_room(room_key):
            resource = state.definition.resource
            if resource is None or resource.gathering_skill_key != skill_key:
                continue
            output = crafting.ITEMS_BY_KEY.get(state.definition.output_item_key)
            status = "DEPLETED" if state.remaining_uses <= 0 else f"{state.remaining_uses} uses"
            result.append(LocalGatherable(
                state.definition.name,
                skill_key,
                resource.minimum_skill,
                output.name if output else state.definition.output_item_key.replace("_", " ").title(),
                status,
            ))
    except Exception:
        pass

    try:
        from mud.goblin_deep_mire import GOBLIN_DEEP_MIRE_GATHERING
        flags = session.database.list_flags(session.character.id)
        for state in GOBLIN_DEEP_MIRE_GATHERING.nodes_in_room(room_key, flags):
            output_key = GOBLIN_DEEP_MIRE_GATHERING.output_for(state)
            output = crafting.ITEMS_BY_KEY.get(output_key)
            status = "DEPLETED" if state.remaining_uses <= 0 else f"{state.remaining_uses} uses"
            result.append(LocalGatherable(
                state.definition.name,
                skill_key,
                state.definition.minimum_herbalism,
                output.name if output else output_key.replace("_", " ").title(),
                status,
            ))
    except Exception:
        pass
    return result


async def _show_gathering_skill(session, skill_key: str) -> None:
    definition = crafting.GATHERING_SKILLS_BY_KEY[skill_key]
    uses, skill = _skill_progress(session, skill_key)
    current, floor, next_name, next_threshold = _milestone_state(skill_key, skill)
    bar, fraction = _bar(skill, floor, next_threshold)
    local = _generic_local_gatherables(session, skill_key) + _goblin_local_gatherables(session, skill_key)

    await session.send(
        f"\r\n{_paint(_HEADER, f'=== {definition.name.upper()} ===')}\r\n"
        f"Skill: {skill}   {_paint(_PROGRESS, bar)}  {fraction}\r\n"
        f"Current tier: {current}\r\n"
        + (f"Next milestone: {next_name} at {next_threshold}\r\n" if next_name else "No higher authored milestone yet.\r\n")
        + (f"Uses: {uses}\r\n" if uses else "")
    )

    await session.send(f"\r\n{_paint(_ACCENT, 'GATHERABLE HERE')}\r\n")
    if not local:
        await session.send("  Nothing for this skill in the current room.\r\n")
    else:
        seen = set()
        for node in local:
            identity = (node.name, node.output_name)
            if identity in seen:
                continue
            seen.add(identity)
            readiness = (
                _paint(_PROGRESS, "READY")
                if skill >= node.minimum_skill and node.status != "DEPLETED"
                else _paint(_DIM, f"SKILL {node.minimum_skill}")
                if skill < node.minimum_skill
                else _paint(_BAD, "DEPLETED")
            )
            await session.send(
                f"  [{readiness}] {_paint(_NAME, node.name)} → {node.output_name}  {_paint(_DIM, node.status)}\r\n"
            )

    action = {"mining": "MINE", "harvesting": "HARVEST", "herbalism": "HERBALISM"}[skill_key]
    await session.send(
        f"\r\nUse {action} <resource> to gather. Partial names work when the match is unique.\r\n"
    )


async def _show_all_gathering(session) -> None:
    await session.send(f"\r\n{_paint(_HEADER, '=== GATHERING SKILLS ===')}\r\n")
    for definition in crafting.GATHERING_SKILLS:
        _uses, skill = _skill_progress(session, definition.key)
        current, _floor, next_name, next_threshold = _milestone_state(definition.key, skill)
        next_text = f"next {next_name} at {next_threshold}" if next_name else "top authored milestone"
        await session.send(
            f"  {_paint(_NAME, definition.name):<24} Skill {skill:<4} {current} — {next_text}\r\n"
        )
    await session.send("\r\nType MINING, HARVESTING, or HERBALISM for the detailed local view.\r\n")


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    prior = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = prior
        else:
            self.__dict__.pop("prompt", None)


def _live_prompt(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_profession_workshops_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_profession_workshops_runtime_installed", False):
        return

    install_missing_profession_content()
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt(_live_prompt(self))
        if command is None:
            await previous_playing_prompt(self)
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"professions", "tradeskills", "craftskills", "profession skills"}:
            await _show_professions(self)
            return
        if normalized in {"gathering skills", "gather skills"}:
            await _show_all_gathering(self)
            return

        if normalized in {"forge", "smithing", "blacksmithing"}:
            await _show_workshop(self, "blacksmithing")
            return
        if normalized.startswith("forge "):
            await _craft_profession(self, "blacksmithing", stripped.split(maxsplit=1)[1])
            return

        if normalized in {"tailor", "tailoring", "loom", "sewing"}:
            await _show_workshop(self, "tailoring")
            return
        if normalized.startswith(("tailor ", "sew ")):
            await _craft_profession(self, "tailoring", stripped.split(maxsplit=1)[1])
            return

        if normalized in {"enchant", "enchanting"}:
            await _show_workshop(self, "enchanting")
            return
        if normalized.startswith("enchant "):
            await _craft_profession(self, "enchanting", stripped.split(maxsplit=1)[1])
            return

        if normalized in {"cook", "cooking", "cookfire"}:
            await _show_workshop(self, "cooking")
            return
        if normalized.startswith("cook "):
            await _craft_profession(self, "cooking", stripped.split(maxsplit=1)[1])
            return
        if normalized in {"food", "foods"}:
            await _show_food(self)
            return
        if normalized == "eat":
            await self.send("Use EAT <food>. Type FOOD to see what you are carrying.\r\n")
            return
        if normalized.startswith("eat "):
            await _eat(self, stripped.split(maxsplit=1)[1])
            return

        if normalized == "mining":
            await _show_gathering_skill(self, "mining")
            return
        if normalized == "harvesting":
            await _show_gathering_skill(self, "harvesting")
            return
        if normalized in {"herbalism", "herbalism info"}:
            await _show_gathering_skill(self, "herbalism")
            return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._profession_workshops_runtime_installed = True
