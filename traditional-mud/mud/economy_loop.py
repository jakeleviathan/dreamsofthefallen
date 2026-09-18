from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import mud.crafting as crafting
from mud.crafting import ItemDefinition, ResourceNodeDefinition, ResourceNodeState
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem


NODE_USES = 5
NODE_RESPAWN_SECONDS = 120.0


@dataclass(slots=True)
class LiveNode:
    state: ResourceNodeState
    depleted_at: float | None = None

    def refresh(self, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        if (
            self.state.depleted
            and self.depleted_at is not None
            and current - self.depleted_at >= NODE_RESPAWN_SECONDS
        ):
            self.state.remaining_uses = NODE_USES
            self.depleted_at = None

    def mark_if_depleted(self, now: float | None = None) -> None:
        if self.state.depleted and self.depleted_at is None:
            self.depleted_at = monotonic() if now is None else now


# Starter-economy placements deliberately spread useful inputs across different
# routes. A player can learn everything eventually, but specialization and trade
# are faster and more convenient than personally running every material chain.
ROOM_RESOURCE_NODE_KEYS: dict[str, tuple[str, ...]] = {
    "human_blackglass_arch": ("iron_vein",),
    "human_sootstairs": ("coal_seam",),
    "human_outer_drill_road": ("greenleaf_patch",),
    "forest_elf_greenway": ("cotton_patch", "lavender_patch"),
    "forest_elf_old_river_path": ("greenleaf_patch",),
    "forest_elf_outer_grove": ("bitterroot_cluster",),
    "dwarf_upper_freight_deck": ("iron_vein", "coal_seam"),
}

ROOM_STATIONS: dict[str, tuple[str, ...]] = {
    "human_cinder_lane": ("forge",),
    "forest_elf_hearthwalk": ("loom", "mortar_and_pestle", "alchemy_table"),
    "dwarf_workshop_tier": ("forge",),
    "goblin_tinker_row": ("forge", "loom"),
}

STATION_LABELS = {
    "forge": "Forge",
    "loom": "Loom / Sewing Bench",
    "mortar_and_pestle": "Mortar and Pestle",
    "alchemy_table": "Alchemy Table",
    "enchanting_table": "Runic Workbench",
    "cookfire": "Cookfire",
}


_RECIPE_RESET = "\x1b[0m"
_RECIPE_HEADER = "\x1b[1;97m"
_RECIPE_NAME = "\x1b[96m"
_RECIPE_PROFESSION = "\x1b[1;36m"
_RECIPE_READY = "\x1b[1;92m"
_RECIPE_AVAILABLE = "\x1b[92m"
_RECIPE_LOCKED = "\x1b[90m"
_RECIPE_MATERIAL = "\x1b[93m"
_RECIPE_WARNING = "\x1b[91m"


def _recipe_paint(style: str, text: str) -> str:
    return f"{style}{text}{_RECIPE_RESET}"


ROUGH_HIDE = ItemDefinition(
    key="rough_hide",
    name="Rough Hide",
    description="A usable hide cut from a dangerous animal. Tailors can clean, trim, and reinforce it for practical gear.",
    category="material",
    tier=1,
)
IMP_HORN = ItemDefinition(
    key="imp_horn",
    name="Imp Horn",
    description="A hard black horn taken from a defeated imp. Smiths prize the dense material for grips, points, and reinforced fittings.",
    category="material",
    tier=1,
)
TRAILGUARD_GLOVES = ItemDefinition(
    key="trailguard_gloves",
    name="Trailguard Gloves",
    description="Flexible gloves made from rough hide reinforced with tightly spun cotton thread; light enough for careful movement but tougher than plain cloth.",
    category="equipment",
    equipment=EquipmentItem(
        "Trailguard Gloves",
        "hands",
        armor_class=1,
        stat_bonuses=CharacterStats(grace=1),
    ),
    tier=1,
)
IMP_HORN_DAGGER = ItemDefinition(
    key="imp_horn_dagger",
    name="Imp-Horn Dagger",
    description="An iron dagger reinforced with a black imp-horn grip and pommel. It is a practical collaboration between a hunter and a smith.",
    category="equipment",
    equipment=EquipmentItem(
        "Imp-Horn Dagger",
        "main_hand",
        stat_bonuses=CharacterStats(might=2),
    ),
    tier=1,
)

ECONOMY_ITEMS: tuple[ItemDefinition, ...] = (
    ROUGH_HIDE,
    IMP_HORN,
    TRAILGUARD_GLOVES,
    IMP_HORN_DAGGER,
)

TRAILGUARD_GLOVES_RECIPE = CraftingRecipe(
    key="sew_trailguard_gloves",
    trade_skill_key="tailoring",
    output_item_key=TRAILGUARD_GLOVES.key,
    minimum_skill=3,
    high_skill_quality_threshold=25,
    materials=(
        MaterialRequirement(ROUGH_HIDE.key, 2),
        MaterialRequirement("cotton_thread", 1),
    ),
    output_quantity=1,
    station_key="loom",
    description="Combine hunted hide with gathered-and-spun cotton to make durable light gloves.",
    design_status="live_social_economy_recipe",
)
IMP_HORN_DAGGER_RECIPE = CraftingRecipe(
    key="forge_imp_horn_dagger",
    trade_skill_key="blacksmithing",
    output_item_key=IMP_HORN_DAGGER.key,
    minimum_skill=3,
    high_skill_quality_threshold=25,
    materials=(
        MaterialRequirement("iron_ingot", 1),
        MaterialRequirement(IMP_HORN.key, 1),
    ),
    output_quantity=1,
    station_key="forge",
    description="Forge an iron dagger around a hard imp-horn grip and fitting.",
    design_status="live_social_economy_recipe",
)
ECONOMY_RECIPES: tuple[CraftingRecipe, ...] = (
    TRAILGUARD_GLOVES_RECIPE,
    IMP_HORN_DAGGER_RECIPE,
)


@dataclass(frozen=True, slots=True)
class LootDrop:
    item_key: str
    quantity: int = 1


LOOT_TABLES: dict[str, tuple[LootDrop, ...]] = {
    "sewer_rat": (LootDrop(ROUGH_HIDE.key),),
    "small_imp": (LootDrop(IMP_HORN.key),),
    "troll_breach_scavenger": (LootDrop(ROUGH_HIDE.key),),
}

_LIVE_NODES: dict[tuple[str, str], LiveNode] = {}


def reset_economy_node_state() -> None:
    _LIVE_NODES.clear()


def install_economy_content() -> None:
    """Register the first hunter-to-gatherer-to-artisan item chains idempotently."""
    known_items = {item.key for item in crafting.ITEMS}
    additions = tuple(item for item in ECONOMY_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    blacksmith_additions = tuple(
        recipe
        for recipe in ECONOMY_RECIPES
        if recipe.trade_skill_key == "blacksmithing" and recipe.key not in crafting.BLACKSMITHING_RECIPES_BY_KEY
    )
    if blacksmith_additions:
        crafting.BLACKSMITHING_RECIPES = crafting.BLACKSMITHING_RECIPES + blacksmith_additions
        crafting.BLACKSMITHING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in blacksmith_additions})

    tailoring_additions = tuple(
        recipe
        for recipe in ECONOMY_RECIPES
        if recipe.trade_skill_key == "tailoring" and recipe.key not in crafting.TAILORING_RECIPES_BY_KEY
    )
    if tailoring_additions:
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + tailoring_additions
        crafting.TAILORING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in tailoring_additions})

    known_recipes = set(crafting.RECIPES_BY_KEY)
    recipe_additions = tuple(recipe for recipe in ECONOMY_RECIPES if recipe.key not in known_recipes)
    if recipe_additions:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + recipe_additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in recipe_additions})


def _node_for(room_key: str, node_key: str) -> LiveNode | None:
    definition = crafting.RESOURCE_NODES_BY_KEY.get(node_key)
    if definition is None:
        return None
    identity = (room_key, node_key)
    live = _LIVE_NODES.get(identity)
    if live is None:
        live = LiveNode(ResourceNodeState(definition=definition, remaining_uses=NODE_USES))
        _LIVE_NODES[identity] = live
    live.refresh()
    return live


def _nodes_here(session) -> list[LiveNode]:
    character = getattr(session, "character", None)
    if character is None:
        return []
    result: list[LiveNode] = []
    for node_key in ROOM_RESOURCE_NODE_KEYS.get(character.current_room or "", ()):
        node = _node_for(character.current_room or "", node_key)
        if node is not None:
            result.append(node)
    return result


def _stations_here(session) -> tuple[str, ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    return ROOM_STATIONS.get(character.current_room or "", ())


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _node_search_names(node: ResourceNodeDefinition) -> frozenset[str]:
    names = {
        _normalize(node.key),
        _normalize(node.name),
        _normalize(node.output_item_key),
    }
    output = crafting.ITEMS_BY_KEY.get(node.output_item_key)
    if output is not None:
        names.add(_normalize(output.name))
    return frozenset(name for name in names if name)


def _node_match_quality(node: ResourceNodeDefinition, target: str) -> int:
    wanted = _normalize(target)
    if not wanted:
        return 0
    names = _node_search_names(node)
    if wanted in names:
        return 2
    if len(wanted) >= 2 and any(wanted in name for name in names):
        return 1
    return 0


def _node_matches(node: ResourceNodeDefinition, target: str) -> bool:
    return _node_match_quality(node, target) > 0


def _resolve_node(session, target: str, skill_key: str | None = None) -> tuple[LiveNode | None, str | None]:
    nodes = [
        live
        for live in _nodes_here(session)
        if skill_key is None or live.state.definition.gathering_skill_key == skill_key
    ]
    if target.strip():
        exact = [live for live in nodes if _node_match_quality(live.state.definition, target) == 2]
        matches = exact or [
            live for live in nodes if _node_match_quality(live.state.definition, target) == 1
        ]
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            names = ", ".join(live.state.definition.name for live in matches)
            return None, f"Be more specific: {names}."
        return None, "There is no matching resource node here."

    if not nodes:
        return None, "There is no matching resource node here."
    if len(nodes) > 1:
        names = ", ".join(live.state.definition.name for live in nodes)
        return None, f"Choose a resource: {names}."
    return nodes[0], None


def _skill_label(skill_key: str) -> str:
    skill = crafting.GATHERING_SKILLS_BY_KEY.get(skill_key)
    return skill.name if skill is not None else skill_key.replace("_", " ").title()


async def _gather(session, target: str, skill_key: str | None = None) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot gather while fighting.\r\n")
        return

    live, error = _resolve_node(session, target, skill_key)
    if error:
        await session.send(error + " Use RESOURCES to see what can be gathered here.\r\n")
        return
    assert live is not None
    live.refresh()
    definition = live.state.definition
    skill_value = crafting.trade_skill_value(session.database, character.id, definition.gathering_skill_key)
    if skill_value < definition.minimum_skill:
        await session.send(
            f"{definition.name} requires {_skill_label(definition.gathering_skill_key)} {definition.minimum_skill}; your skill is {skill_value}.\r\n"
        )
        return
    if live.state.depleted:
        live.mark_if_depleted()
        remaining = max(1, int(NODE_RESPAWN_SECONDS - (monotonic() - (live.depleted_at or monotonic()))))
        await session.send(f"{definition.name} is depleted. It should recover in about {remaining} seconds.\r\n")
        return

    output_key = crafting.gather_node(session.database, character.id, live.state)
    live.mark_if_depleted()
    if output_key is None:
        await session.send("You fail to gather anything useful.\r\n")
        return
    output = crafting.ITEMS_BY_KEY.get(output_key)
    output_name = output.name if output is not None else output_key
    new_skill = crafting.trade_skill_value(session.database, character.id, definition.gathering_skill_key)
    await session.send(
        f"You gather 1x {output_name} from {definition.name}. "
        f"{_skill_label(definition.gathering_skill_key)} is now {new_skill}.\r\n"
    )


async def _show_resources(session) -> None:
    nodes = _nodes_here(session)
    stations = _stations_here(session)
    await session.send("\r\n--- Local Economy ---\r\n")
    if not nodes:
        await session.send("Resources: none in this room.\r\n")
    else:
        await session.send("Resources:\r\n")
        for live in nodes:
            live.refresh()
            definition = live.state.definition
            status = "depleted" if live.state.depleted else f"{live.state.remaining_uses} uses available"
            await session.send(
                f"- {definition.name} [{_skill_label(definition.gathering_skill_key)} {definition.minimum_skill}] - {status}\r\n"
            )
    if stations:
        await session.send("Stations: " + ", ".join(STATION_LABELS.get(key, key) for key in stations) + ".\r\n")
    else:
        await session.send("Stations: none in this room.\r\n")
    await session.send("Use GATHER <resource>, MINE, HARVEST, or HERBALISM as appropriate.\r\n")


async def _show_economy_help(session) -> None:
    await session.send(
        "\r\n--- Hunt, Gather, Craft, Trade ---\r\n"
        "Hunters defeat creatures for materials such as Rough Hide and Imp Horn.\r\n"
        "Gatherers work room resources with Mining, Harvesting, and Herbalism; those skills improve through use.\r\n"
        "Artisans turn gathered and hunted inputs into equipment and consumables at real crafting stations.\r\n"
        "The useful chains overlap on purpose: Trailguard Gloves need hunted hide plus gathered-and-spun cotton; an Imp-Horn Dagger needs an imp drop plus mined-and-smelted iron.\r\n"
        "No role is a hard class lock, but use-based skill growth and geographically separated materials reward specialization and player exchange.\r\n"
        "Commands: RESOURCES, RECIPES, RECIPES <profession>, RECIPES READY, RECIPES CRAFTABLE, RECIPE <name>, CRAFT <recipe>, GIVE <player> [qty] <item>, TRADE <player>.\r\n"
    )


def _recipe_names(recipe: CraftingRecipe) -> set[str]:
    names = {_normalize(recipe.key)}
    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    if output is not None:
        names.add(_normalize(output.name))
    return names


def _recipe_output_name(recipe: CraftingRecipe) -> str:
    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    return output.name if output is not None else recipe.output_item_key.replace("_", " ").title()


def _profession_name(key: str) -> str:
    profession = crafting.PROFESSIONS_BY_KEY.get(key)
    return profession.name if profession is not None else key.replace("_", " ").title()


def _material_name(item_key: str) -> str:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    return item.name if item is not None else item_key.replace("_", " ").title()


def _material_state(session, recipe: CraftingRecipe) -> tuple[tuple[int, int, str], ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    return tuple(
        (
            session.database.item_quantity(character.id, requirement.item_key),
            requirement.quantity,
            _material_name(requirement.item_key),
        )
        for requirement in recipe.materials
    )


def _recipe_state(session, recipe: CraftingRecipe) -> dict[str, object]:
    character = session.character
    current = crafting.trade_skill_value(session.database, character.id, recipe.trade_skill_key)
    materials = _material_state(session, recipe)
    materials_ready = all(owned >= needed for owned, needed, _name in materials)
    station_ready = recipe.station_key is None or recipe.station_key in set(_stations_here(session))
    skill_ready = current >= recipe.minimum_skill
    return {
        "skill": current,
        "skill_ready": skill_ready,
        "materials": materials,
        "materials_ready": materials_ready,
        "station_ready": station_ready,
        "craftable": skill_ready and materials_ready and station_ready,
    }


def _recipe_status_label(session, recipe: CraftingRecipe) -> str:
    state = _recipe_state(session, recipe)
    if state["craftable"]:
        return _recipe_paint(_RECIPE_READY, "CRAFT NOW")
    if state["skill_ready"]:
        return _recipe_paint(_RECIPE_AVAILABLE, "READY")
    return _recipe_paint(_RECIPE_LOCKED, f"LOCKED {state['skill']}/{recipe.minimum_skill}")


def _recipe_sort_key(recipe: CraftingRecipe) -> tuple[int, str]:
    return (recipe.minimum_skill, _recipe_output_name(recipe).lower())


def _resolve_recipe(target: str) -> tuple[CraftingRecipe | None, str | None]:
    wanted = _normalize(target)
    if not wanted:
        return None, "Name a recipe. Use RECIPES to browse them."
    exact = [recipe for recipe in crafting.ALL_RECIPES if wanted in _recipe_names(recipe)]
    if not exact:
        exact = [
            recipe
            for recipe in crafting.ALL_RECIPES
            if any(wanted in name for name in _recipe_names(recipe))
        ]
    unique_keys = tuple(dict.fromkeys(recipe.key for recipe in exact))
    if not unique_keys:
        return None, "Unknown recipe. Use RECIPES to browse the current catalog."
    if len(unique_keys) > 1:
        names = ", ".join(
            _recipe_output_name(crafting.RECIPES_BY_KEY[key]) for key in unique_keys[:6]
        )
        suffix = "..." if len(unique_keys) > 6 else ""
        return None, f"That matches several recipes: {names}{suffix}. Be more specific."
    return crafting.RECIPES_BY_KEY[unique_keys[0]], None


def _recipe_filter(value: str) -> tuple[str, str | None]:
    wanted = _normalize(value)
    aliases = {
        "smith": "blacksmithing",
        "smithing": "blacksmithing",
        "blacksmith": "blacksmithing",
        "blacksmithing": "blacksmithing",
        "tailor": "tailoring",
        "tailoring": "tailoring",
        "sewing": "tailoring",
        "alchemy": "alchemy",
        "alchemist": "alchemy",
        "enchant": "enchanting",
        "enchanter": "enchanting",
        "enchanting": "enchanting",
        "cook": "cooking",
        "cooking": "cooking",
        "chef": "cooking",
    }
    if not wanted:
        return "overview", None
    if wanted in {"all", "catalog", "full"}:
        return "all", None
    if wanted in {"ready", "unlocked", "known"}:
        return "ready", None
    if wanted in {"craftable", "now", "craftable now"}:
        return "craftable", None
    if wanted in {"help", "?"}:
        return "help", None
    profession = aliases.get(wanted)
    if profession:
        return "profession", profession
    return "unknown", wanted


def _recipe_line(session, recipe: CraftingRecipe, *, include_materials: bool = True) -> str:
    station = STATION_LABELS.get(recipe.station_key, recipe.station_key or "No station")
    status = _recipe_status_label(session, recipe)
    name = _recipe_paint(_RECIPE_NAME, _recipe_output_name(recipe))
    line = f"  {status:<28} {name}  {_recipe_paint(_RECIPE_LOCKED, station)}\r\n"
    if include_materials:
        materials = ", ".join(
            f"{need}x {_material_name(requirement.item_key)}"
            for requirement, need in ((req, req.quantity) for req in recipe.materials)
        )
        line += f"       {_recipe_paint(_RECIPE_MATERIAL, materials)}\r\n"
    return line


async def _show_recipe_help(session) -> None:
    await session.send(
        "\r\n--- Recipe Book Commands ---\r\n"
        "RECIPES                  concise overview: usable recipes plus your next unlocks\r\n"
        "RECIPES BLACKSMITHING    full Blacksmithing catalog\r\n"
        "RECIPES TAILORING        full Tailoring catalog\r\n"
        "RECIPES ALCHEMY          full Alchemy catalog\r\n"
        "RECIPES ENCHANTING       full Enchanting catalog\r\n"
        "RECIPES COOKING          full Cooking catalog\r\n"
        "RECIPES READY            every recipe your current skill has unlocked\r\n"
        "RECIPES CRAFTABLE        recipes you can craft right now with your inventory and local station\r\n"
        "RECIPES ALL              complete catalog\r\n"
        "RECIPE <name>            detailed ingredients, inventory counts, station, description, and craft command\r\n"
        "CRAFT <name>             craft by output name; internal recipe keys are not required\r\n"
    )


async def _show_recipe_group(
    session,
    profession_key: str,
    recipes: list[CraftingRecipe],
    *,
    overview: bool = False,
) -> None:
    character = session.character
    skill = crafting.trade_skill_value(session.database, character.id, profession_key)
    ready = [recipe for recipe in recipes if skill >= recipe.minimum_skill]
    locked = [recipe for recipe in recipes if skill < recipe.minimum_skill]
    craftable = [recipe for recipe in ready if _recipe_state(session, recipe)["craftable"]]

    title = (
        f"{_profession_name(profession_key)} — skill {skill} — "
        f"{len(ready)} unlocked, {len(craftable)} craftable now, {len(locked)} locked"
    )
    await session.send(f"\r\n{_recipe_paint(_RECIPE_PROFESSION, title)}\r\n")

    if overview:
        # Keep the default screen useful even for a master artisan with dozens of
        # recipes: show at most six most-recently-unlocked recipes and three next.
        shown_ready = sorted(ready, key=_recipe_sort_key)[-6:]
        if shown_ready:
            await session.send(_recipe_paint(_RECIPE_HEADER, "  USABLE") + "\r\n")
            for recipe in shown_ready:
                await session.send(_recipe_line(session, recipe))
        else:
            await session.send("  No recipes unlocked yet.\r\n")

        next_locked = sorted(locked, key=_recipe_sort_key)[:3]
        if next_locked:
            await session.send(_recipe_paint(_RECIPE_HEADER, "  NEXT UNLOCKS") + "\r\n")
            for recipe in next_locked:
                await session.send(
                    f"  {_recipe_paint(_RECIPE_LOCKED, f'Skill {recipe.minimum_skill:>3}')}  "
                    f"{_recipe_paint(_RECIPE_NAME, _recipe_output_name(recipe))}\r\n"
                )
        return

    for recipe in sorted(recipes, key=_recipe_sort_key):
        await session.send(_recipe_line(session, recipe))


async def _show_recipes(session, recipe_filter: str = "") -> None:
    character = getattr(session, "character", None)
    if character is None:
        return

    mode, profession = _recipe_filter(recipe_filter)
    if mode == "help":
        await _show_recipe_help(session)
        return
    if mode == "unknown":
        await session.send(
            "Unknown recipe filter. Use RECIPES HELP for the available views.\r\n"
        )
        return

    stations = _stations_here(session)
    station_text = (
        ", ".join(STATION_LABELS.get(key, key) for key in stations)
        if stations
        else "none in this room"
    )
    await session.send(
        f"\r\n{_recipe_paint(_RECIPE_HEADER, '=== RECIPE BOOK ===')}\r\n"
        f"Stations here: {station_text}\r\n"
        "Use RECIPE <name> for full details. Internal recipe keys are hidden because you do not need them.\r\n"
    )

    if mode == "overview":
        await session.send(
            "Showing a concise view. Use RECIPES <profession>, RECIPES READY, "
            "RECIPES CRAFTABLE, or RECIPES ALL for more.\r\n"
        )
        profession_order = ("blacksmithing", "tailoring", "alchemy", "enchanting", "cooking")
        for key in profession_order:
            recipes = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == key]
            if recipes:
                await _show_recipe_group(session, key, recipes, overview=True)
        return

    selected = list(crafting.ALL_RECIPES)
    if mode == "profession" and profession is not None:
        selected = [r for r in selected if r.trade_skill_key == profession]
    elif mode == "ready":
        selected = [
            r for r in selected
            if crafting.trade_skill_value(session.database, character.id, r.trade_skill_key)
            >= r.minimum_skill
        ]
    elif mode == "craftable":
        selected = [r for r in selected if _recipe_state(session, r)["craftable"]]

    if not selected:
        await session.send("No recipes match that view right now.\r\n")
        return

    profession_order = ("blacksmithing", "tailoring", "alchemy", "enchanting", "cooking")
    remaining = sorted({r.trade_skill_key for r in selected} - set(profession_order))
    for key in (*profession_order, *remaining):
        group = [r for r in selected if r.trade_skill_key == key]
        if group:
            await _show_recipe_group(session, key, group)


async def _show_recipe_detail(session, target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    recipe, error = _resolve_recipe(target)
    if error:
        await session.send(error + "\r\n")
        return
    assert recipe is not None

    state = _recipe_state(session, recipe)
    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    output_name = _recipe_output_name(recipe)
    profession = _profession_name(recipe.trade_skill_key)
    station = STATION_LABELS.get(recipe.station_key, recipe.station_key or "No station")
    station_state = "HERE" if state["station_ready"] else "NOT HERE"
    skill_state = (
        "READY"
        if state["skill_ready"]
        else f"LOCKED — need {recipe.minimum_skill - int(state['skill'])} more skill"
    )

    await session.send(
        f"\r\n{_recipe_paint(_RECIPE_HEADER, '=== RECIPE ===')}\r\n"
        f"{_recipe_paint(_RECIPE_NAME, output_name)}\r\n"
        f"{recipe.description}\r\n\r\n"
        f"Profession : {profession}\r\n"
        f"Skill      : {state['skill']} / {recipe.minimum_skill}  ({skill_state})\r\n"
        f"Station    : {station}  ({station_state})\r\n"
        f"Output     : {recipe.output_quantity}x {output_name}\r\n"
        f"Ingredients:\r\n"
    )
    for owned, needed, name in state["materials"]:
        enough = owned >= needed
        marker = _recipe_paint(_RECIPE_READY if enough else _RECIPE_WARNING, "OK" if enough else "NEED")
        await session.send(
            f"  {marker:<18} {owned}/{needed}  {_recipe_paint(_RECIPE_MATERIAL, name)}\r\n"
        )

    if output is not None and output.description:
        await session.send(f"\r\nItem: {output.description}\r\n")

    if state["craftable"]:
        await session.send(
            f"\r\n{_recipe_paint(_RECIPE_READY, 'You can craft this now.')} "
            f"Use CRAFT {output_name}.\r\n"
        )
    else:
        reasons = []
        if not state["skill_ready"]:
            reasons.append("skill")
        if not state["materials_ready"]:
            reasons.append("materials")
        if not state["station_ready"]:
            reasons.append("station")
        await session.send(
            f"\r\nNot craftable yet: {', '.join(reasons)}. "
            f"When ready, use CRAFT {output_name}.\r\n"
        )


async def _craft(session, target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot craft while fighting.\r\n")
        return
    recipe, error = _resolve_recipe(target)
    if error:
        await session.send(error + "\r\n")
        return
    assert recipe is not None

    stations = set(_stations_here(session))
    if recipe.station_key is not None and recipe.station_key not in stations:
        label = STATION_LABELS.get(recipe.station_key, recipe.station_key)
        await session.send(f"This recipe requires a {label}. Use RESOURCES to see local stations.\r\n")
        return

    result = crafting.craft_recipe(
        session.database,
        character.id,
        recipe.key,
        station_key=recipe.station_key if recipe.station_key in stations else None,
    )
    if not result.success:
        await session.send(result.message + "\r\n")
        return
    output = crafting.ITEMS_BY_KEY.get(result.output_item_key or "")
    output_name = output.name if output is not None else (result.output_item_key or "item")
    skill = crafting.trade_skill_value(session.database, character.id, recipe.trade_skill_key)
    quality = " The work comes out especially clean." if result.high_quality else ""
    await session.send(
        f"Crafted {result.output_quantity}x {output_name}. {recipe.trade_skill_key.title()} is now {skill}.{quality}\r\n"
    )


def _loot_for(enemy) -> tuple[LootDrop, ...]:
    key = str(getattr(getattr(enemy, "definition", None), "key", ""))
    if key in LOOT_TABLES:
        return LOOT_TABLES[key]
    normalized = key.lower()
    if any(word in normalized for word in ("wolf", "rat", "boar", "beast")):
        return (LootDrop(ROUGH_HIDE.key),)
    if "imp" in normalized:
        return (LootDrop(IMP_HORN.key),)
    return ()


async def _award_loot(session, enemy) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    drops = _loot_for(enemy)
    if not drops:
        return
    names: list[str] = []
    for drop in drops:
        session.database.add_item(character.id, drop.item_key, drop.quantity)
        definition = crafting.ITEMS_BY_KEY.get(drop.item_key)
        name = definition.name if definition is not None else drop.item_key
        names.append(f"{drop.quantity}x {name}")
    await session.send("Loot: " + ", ".join(names) + ".\r\n")


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


def _live_prompt(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_economy_loop_runtime(player_session_class, world_service=None) -> None:
    """Make hunting loot, gathering nodes, stations, crafting, and specialization live."""
    if getattr(player_session_class, "_economy_loop_runtime_installed", False):
        return
    install_economy_content()

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            nodes = _nodes_here(self)
            stations = _stations_here(self)
            if nodes:
                await self.send(
                    "Resources: "
                    + " | ".join(
                        f"{live.state.definition.name} ({_skill_label(live.state.definition.gathering_skill_key)})"
                        for live in nodes
                    )
                    + "\r\n"
                )
            if stations:
                await self.send(
                    "Crafting: " + ", ".join(STATION_LABELS.get(key, key) for key in stations) + ".\r\n"
                )

        player_session_class.show_current_room = show_current_room

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if previous_finish_enemy is not None:
        async def _finish_enemy_defeat(self, enemy) -> None:
            eligible = getattr(self, "active_enemy", None) is enemy
            await previous_finish_enemy(self, enemy)
            if eligible:
                await _award_loot(self, enemy)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt(_live_prompt(self))
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"economy", "economy help", "help economy", "craft economy"}:
            await _show_economy_help(self)
            return
        if normalized in {"resources", "resource", "stations", "gathering"}:
            await _show_resources(self)
            return

        if normalized == "gather":
            await _gather(self, "")
            return
        if normalized.startswith("gather "):
            await _gather(self, stripped.split(maxsplit=1)[1])
            return
        if normalized in {"mine", "mining"}:
            await _gather(self, "", "mining")
            return
        if normalized.startswith("mine "):
            await _gather(self, stripped.split(maxsplit=1)[1], "mining")
            return
        if normalized in {"harvest", "harvesting"}:
            await _gather(self, "", "harvesting")
            return
        if normalized.startswith("harvest "):
            await _gather(self, stripped.split(maxsplit=1)[1], "harvesting")
            return
        if normalized in {"herbalism", "herbs"}:
            await _gather(self, "", "herbalism")
            return
        if normalized.startswith("herbalism "):
            await _gather(self, stripped.split(maxsplit=1)[1], "herbalism")
            return
        if normalized.startswith("herbs "):
            await _gather(self, stripped.split(maxsplit=1)[1], "herbalism")
            return

        if normalized == "recipes":
            await _show_recipes(self)
            return
        if normalized.startswith("recipes "):
            await _show_recipes(self, stripped.split(maxsplit=1)[1])
            return
        if normalized == "recipe":
            await self.send("Use RECIPE <name>. Type RECIPES to browse the catalog.\r\n")
            return
        if normalized.startswith("recipe "):
            await _show_recipe_detail(self, stripped.split(maxsplit=1)[1])
            return
        if normalized == "craft":
            await self.send("Use CRAFT <recipe>. Type RECIPES to browse the catalog.\r\n")
            return
        if normalized.startswith("craft "):
            await _craft(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._economy_loop_runtime_installed = True
