from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic

import mud.crafting as crafting
import mud.world as legacy_world
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

# Fresh water is a common-world input rather than a race-specific convenience.
# These placements are intentionally limited to rooms whose authored text
# describes a protected, clear, tested, or otherwise credible freshwater source.
# Polluted swamp water, floodwater, brine, dry wells, and merely decorative
# water are deliberately excluded. Goblin Cleanwater Seep keeps its existing
# authored one-Astralis-hour gathering service and is therefore not duplicated
# in this generic table.
FRESH_WATER_ROOM_KEYS: tuple[str, ...] = (
    "human_cinder_ward",                 # public cisterns
    "forest_elf_old_river_path",         # clear shallow river
    "forest_elf_waystone_bend",           # same clear river at the waystone bend
    "forest_elf_listening_pool",         # clear river pool
    "forest_elf_rainpool_terrace",       # maintained rain catchments
    "forest_elf_seepstone_run",          # clean hillside runoff
    "moon_elf_alpine_light_garden",      # garden cistern and drip channels
    "sporekin_lumen_hollow",             # clean cavern seepage
    "goblin_patchwork_plaza",            # maintained public water trough
    "waymeet_commonhouse_yard",          # public rain barrels
    "greywake_three_banner_camp",        # shared camp well
    "greywake_lantern_hospice",          # explicitly maintained clean water
    "greywake_old_aqueduct",             # clean mountain aqueduct
    "veyra_five_ways_yard",              # central public water trough
    "veyra_north_waterworks",            # tested mountain water
    "sablewater_saltgrass_bend",         # mineral springs
    "ashcross_common",                    # public water pump
    "broken_reach_ragged_caravanserai",  # shared roadside cistern
    "nine_vapors_distillation_hall",     # clean condenser drip
    "underclock_condenser_court",        # condensed water in stone gutters
    "keelspire_three_wells_court",       # public sweet-water well
    "salt_kingdoms_springcut_gorge",     # restored natural stream
    "salt_kingdoms_cistern_road",        # refilled roadside cisterns
)


def install_fresh_water_sources(rooms_by_key: dict[str, object] | None = None) -> None:
    """Attach renewable Spring Water to credible freshwater rooms world-wide.

    This runs after regional installers so it appends to, rather than being
    overwritten by, region-specific mining/harvesting/herbalism placements.
    """

    if rooms_by_key is not None:
        missing = tuple(key for key in FRESH_WATER_ROOM_KEYS if key not in rooms_by_key)
        if missing:
            raise RuntimeError("Unknown fresh-water room keys: " + ", ".join(missing))

    for room_key in FRESH_WATER_ROOM_KEYS:
        current = ROOM_RESOURCE_NODE_KEYS.get(room_key, ())
        if "fresh_water_source" not in current:
            ROOM_RESOURCE_NODE_KEYS[room_key] = current + ("fresh_water_source",)

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
_RECIPE_OWNED_MATERIAL = "\x1b[92m"
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
    room_key = character.current_room or ""
    stations = list(ROOM_STATIONS.get(room_key, ()))

    # Newer authored rooms often advertise infrastructure through semantic room
    # tags instead of the old starter ROOM_STATIONS table. Treat those tags as
    # first-class stations so every region can share the same workshop UI.
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is not None:
        known = set(STATION_LABELS)
        for tag in getattr(room, "tags", ()):
            if tag in known and tag not in stations:
                stations.append(tag)
    return tuple(stations)


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


def _skill_label(skill_key: str | None) -> str:
    if skill_key is None:
        return "Collect"
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
    skill_key = definition.gathering_skill_key
    if skill_key is not None:
        skill_value = crafting.trade_skill_value(session.database, character.id, skill_key)
        if skill_value < definition.minimum_skill:
            await session.send(
                f"{definition.name} requires {_skill_label(skill_key)} {definition.minimum_skill}; your skill is {skill_value}.\r\n"
            )
            return
    if live.state.depleted:
        live.mark_if_depleted()
        remaining = max(1, int(NODE_RESPAWN_SECONDS - (monotonic() - (live.depleted_at or monotonic()))))
        await session.send(f"{definition.name} is depleted. It should recover in about {remaining} seconds.\r\n")
        return

    checker = getattr(session, "can_receive_item", None)
    if callable(checker) and not checker(definition.output_item_key, 1):
        await session.send(
            "Your inventory has no free slot for that item type. "
            "Free a slot or equip a larger bag before gathering it.\r\n"
        )
        return

    output_key = crafting.gather_node(session.database, character.id, live.state)
    live.mark_if_depleted()
    if output_key is None:
        await session.send("You fail to gather anything useful.\r\n")
        return
    output = crafting.ITEMS_BY_KEY.get(output_key)
    output_name = output.name if output is not None else output_key
    if skill_key is None:
        await session.send(f"You collect 1x {output_name} from {definition.name}.\r\n")
    else:
        new_skill = crafting.trade_skill_value(session.database, character.id, skill_key)
        await session.send(
            f"You gather 1x {output_name} from {definition.name}. "
            f"{_skill_label(skill_key)} is now {new_skill}.\r\n"
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
            requirement = (
                _skill_label(definition.gathering_skill_key)
                if definition.gathering_skill_key is None
                else f"{_skill_label(definition.gathering_skill_key)} {definition.minimum_skill}"
            )
            await session.send(f"- {definition.name} [{requirement}] - {status}\r\n")
    if stations:
        await session.send("Stations: " + ", ".join(STATION_LABELS.get(key, key) for key in stations) + ".\r\n")
    else:
        await session.send("Stations: none in this room.\r\n")
    await session.send("Use GATHER <resource>, COLLECT WATER, MINE, HARVEST, or HERBALISM as appropriate.\r\n")


async def _show_economy_help(session) -> None:
    await session.send(
        "\r\n--- Hunt, Gather, Craft, Trade ---\r\n"
        "Hunters defeat creatures for materials such as Rough Hide and Imp Horn.\r\n"
        "Gatherers work room resources with Mining, Harvesting, and Herbalism; those skills improve through use. Clean freshwater sources can be collected without a gathering skill.\r\n"
        "Artisans turn gathered and hunted inputs into equipment and consumables at real crafting stations.\r\n"
        "The useful chains overlap on purpose: Trailguard Gloves need hunted hide plus gathered-and-spun cotton; an Imp-Horn Dagger needs an imp drop plus mined-and-smelted iron.\r\n"
        "No role is a hard class lock, but use-based skill growth and geographically separated materials reward specialization and player exchange.\r\n"
        "Commands: RESOURCES, GATHER <resource>, COLLECT WATER, RECIPES, RECIPES <profession>, RECIPES READY, RECIPES CRAFTABLE, RECIPE <name>, CRAFT <recipe>, GIVE <player> [qty] <item>, TRADE <player>.\r\n"
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


def _recipe_visible(session, recipe: CraftingRecipe) -> bool:
    """Secret recipes stay out of player-facing catalogs until discovered."""

    flag = getattr(recipe, "discovery_flag", None)
    if not flag:
        return True
    character = getattr(session, "character", None)
    if character is None:
        return False
    return flag in set(session.database.list_flags(character.id))


def _visible_recipes(session) -> tuple[CraftingRecipe, ...]:
    return tuple(recipe for recipe in crafting.ALL_RECIPES if _recipe_visible(session, recipe))


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
    skill_ready = recipe.can_attempt(current, max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP)
    mastered = current >= recipe.trivial_skill
    success_chance = crafting.craft_success_chance(current, recipe.trivial_skill)
    skillup_chance = crafting.craft_skillup_chance(current, recipe.trivial_skill)
    return {
        "skill": current,
        "skill_ready": skill_ready,
        "mastered": mastered,
        "success_chance": success_chance,
        "skillup_chance": skillup_chance,
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
    return _recipe_paint(_RECIPE_LOCKED, "TOO HARD")

def _recipe_sort_key(recipe: CraftingRecipe) -> tuple[int, str]:
    return (recipe.minimum_skill, _recipe_output_name(recipe).lower())


def _resolve_recipe(
    target: str,
    session=None,
) -> tuple[CraftingRecipe | None, str | None]:
    wanted = _normalize(target)
    if not wanted:
        return None, "Name a recipe. Use RECIPES to browse them."
    source = _visible_recipes(session) if session is not None else crafting.ALL_RECIPES
    exact = [recipe for recipe in source if wanted in _recipe_names(recipe)]
    if not exact:
        exact = [
            recipe
            for recipe in source
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

def _recipe_filter(value: str) -> tuple[str, str | None, str | None]:
    """Parse recipe-book views without making players memorize rigid syntax."""

    wanted = _normalize(value)
    aliases = {
        "smith": "blacksmithing", "smithing": "blacksmithing",
        "blacksmith": "blacksmithing", "blacksmithing": "blacksmithing",
        "tailor": "tailoring", "tailoring": "tailoring", "sewing": "tailoring",
        "alchemy": "alchemy", "alchemist": "alchemy",
        "enchant": "enchanting", "enchanter": "enchanting", "enchanting": "enchanting",
        "cook": "cooking", "cooking": "cooking", "chef": "cooking",
    }
    if not wanted:
        return "overview", None, None
    if wanted in {"help", "?"}:
        return "help", None, None

    parts = wanted.split()
    profession = aliases.get(parts[0])
    if profession:
        if len(parts) == 1:
            # A profession view answers the most useful question first: what can
            # I actually make right now?
            return "craftable", profession, None
        view = parts[1]
        if view in {"craftable", "now"} and len(parts) == 2:
            return "craftable", profession, None
        if view in {"all", "ready", "unlocked", "known"} and len(parts) == 2:
            return "ready", profession, None
        if view in {"difficult", "hard", "locked"} and len(parts) == 2:
            return "difficult", profession, None
        if view in {"armor", "clothing", "materials"} and len(parts) == 2:
            return view, profession, None
        if view == "search" and len(parts) >= 3:
            return "search", profession, " ".join(parts[2:])
        return "unknown", profession, None

    if parts[0] == "search" and len(parts) >= 2:
        return "search", None, " ".join(parts[1:])
    if wanted in {"all", "catalog", "full"}:
        return "all", None, None
    if wanted in {"ready", "unlocked", "known"}:
        return "ready", None, None
    if wanted in {"craftable", "now", "craftable now"}:
        return "craftable", None, None
    if wanted in {"difficult", "hard", "locked"}:
        return "difficult", None, None
    if wanted in {"armor", "clothing", "materials"}:
        return wanted, None, None
    return "unknown", None, None


def _recipe_category_matches(recipe: CraftingRecipe, category: str) -> bool:
    """Semantic recipe categories derived from the output item, not its name."""

    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    if output is None:
        return False
    if category == "materials":
        return output.equipment is None and output.consumable is None
    if category == "armor":
        return output.equipment is not None and output.equipment.armor_class > 0
    if category == "clothing":
        return output.equipment is not None
    return False


def _recipe_search_matches(recipe: CraftingRecipe, query: str) -> bool:
    needle = _normalize(query)
    if not needle:
        return False
    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    haystack = " ".join(
        (
            _recipe_output_name(recipe),
            recipe.key.replace("_", " "),
            recipe.description,
            output.description if output is not None else "",
        )
    )
    return needle in _normalize(haystack)

def _recipe_line(session, recipe: CraftingRecipe, *, include_materials: bool = True) -> str:
    station = STATION_LABELS.get(recipe.station_key, recipe.station_key or "No station")
    state = _recipe_state(session, recipe)
    name = _recipe_paint(_RECIPE_NAME, _recipe_output_name(recipe))
    success_pct = int(round(float(state["success_chance"]) * 100))

    # Telnet-first hierarchy: the crafted item is the visual anchor. Repeated
    # READY / CRAFT NOW labels added noise without adding useful information;
    # material colors and the surrounding recipe section already communicate
    # availability.
    station_style = _RECIPE_READY if state["station_ready"] else _RECIPE_LOCKED
    line = (
        f"  {name}\r\n"
        f"       {_recipe_paint(station_style, station)}"
        f"  |  Trivial {recipe.trivial_skill}  |  {success_pct}% success\r\n"
    )
    if include_materials:
        materials = ", ".join(
            _recipe_paint(
                _RECIPE_OWNED_MATERIAL if owned > 0 else _RECIPE_MATERIAL,
                f"{needed}x {material_name}",
            )
            for owned, needed, material_name in state["materials"]
        )
        line += f"       Requires: {materials}\r\n"
    return line

async def _show_recipe_help(session) -> None:
    await session.send(
        "\r\n--- Recipe Book Commands ---\r\n"
        "RECIPES                         concise all-profession overview\r\n"
        "RECIPES <profession>            recipes you can craft right now\r\n"
        "RECIPES <profession> ALL        every attemptable recipe\r\n"
        "RECIPES <profession> CRAFTABLE  materials, station, and skill ready now\r\n"
        "RECIPES <profession> ARMOR      protective equipment\r\n"
        "RECIPES <profession> CLOTHING   wearable equipment\r\n"
        "RECIPES <profession> MATERIALS  thread, cloth, ingots, and other components\r\n"
        "RECIPES <profession> DIFFICULT  visible recipes beyond your current skill range\r\n"
        "RECIPES <profession> SEARCH <text>  search names and descriptions\r\n"
        "RECIPES CRAFTABLE               craftable recipes across every profession\r\n"
        "RECIPES SEARCH <text>           search the whole visible recipe book\r\n"
        "RECIPE <name>                   full recipe details\r\n"
        "CRAFT <name>                    begin an interruptible crafting action\r\n\r\n"
        "At a recipe trivial value, success is guaranteed and that recipe can no longer raise your skill.\r\n"
        "Completed failures consume ingredients. Movement or damage interrupts crafting without consuming them.\r\n"
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
    attemptable = [
        recipe for recipe in recipes
        if recipe.can_attempt(skill, max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP)
    ]
    too_hard = [recipe for recipe in recipes if recipe not in attemptable]
    craftable = [recipe for recipe in attemptable if _recipe_state(session, recipe)["craftable"]]

    title = (
        f"{_profession_name(profession_key)} — skill {skill} — "
        f"{len(attemptable)} attemptable, {len(craftable)} craftable now, {len(too_hard)} too difficult"
    )
    await session.send(f"\r\n{_recipe_paint(_RECIPE_PROFESSION, title)}\r\n")

    if overview:
        shown = sorted(
            sorted(
                attemptable,
                key=lambda recipe: (abs(recipe.trivial_skill - skill), recipe.trivial_skill, _recipe_output_name(recipe).lower()),
            )[:6],
            key=_recipe_sort_key,
        )
        if shown:
            await session.send(_recipe_paint(_RECIPE_HEADER, "  ATTEMPTABLE") + "\r\n")
            for recipe in shown:
                await session.send(_recipe_line(session, recipe))
        else:
            await session.send("  No recipes are close enough to attempt yet.\r\n")

        next_hard = sorted(too_hard, key=_recipe_sort_key)[:3]
        if next_hard:
            await session.send(_recipe_paint(_RECIPE_HEADER, "  TOO DIFFICULT") + "\r\n")
            for recipe in next_hard:
                await session.send(
                    f"  {_recipe_paint(_RECIPE_LOCKED, f'Trivial {recipe.trivial_skill:>3}')}  "
                    f"{_recipe_paint(_RECIPE_NAME, _recipe_output_name(recipe))}\r\n"
                )
        return

    for recipe in sorted(recipes, key=_recipe_sort_key):
        await session.send(_recipe_line(session, recipe))

async def _show_recipes(session, recipe_filter: str = "") -> None:
    character = getattr(session, "character", None)
    if character is None:
        return

    mode, profession, query = _recipe_filter(recipe_filter)
    if mode == "help":
        await _show_recipe_help(session)
        return
    if mode == "unknown":
        await session.send(
            "Unknown recipe filter. Use RECIPES HELP for the available views.\r\n"
        )
        return

    visible = list(_visible_recipes(session))
    scoped = [r for r in visible if profession is None or r.trade_skill_key == profession]

    # Filter before rendering so a profession command never falls back to the
    # old wall-of-recipes behavior.
    if mode == "craftable":
        selected = [r for r in scoped if _recipe_state(session, r)["craftable"]]
    elif mode == "ready":
        selected = [
            r for r in scoped
            if r.can_attempt(
                crafting.trade_skill_value(session.database, character.id, r.trade_skill_key),
                max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP,
            )
        ]
    elif mode == "difficult":
        selected = [
            r for r in scoped
            if not r.can_attempt(
                crafting.trade_skill_value(session.database, character.id, r.trade_skill_key),
                max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP,
            )
        ]
    elif mode in {"armor", "clothing", "materials"}:
        selected = [r for r in scoped if _recipe_category_matches(r, mode)]
    elif mode == "search":
        selected = [r for r in scoped if _recipe_search_matches(r, query or "")]
    else:
        selected = scoped

    stations = _stations_here(session)
    station_text = (
        ", ".join(STATION_LABELS.get(key, key) for key in stations)
        if stations else "none in this room"
    )

    if profession is not None:
        skill = crafting.trade_skill_value(session.database, character.id, profession)
        attemptable = [
            r for r in scoped
            if r.can_attempt(skill, max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP)
        ]
        craftable = [r for r in attemptable if _recipe_state(session, r)["craftable"]]
        difficult = [r for r in scoped if r not in attemptable]
        view_label = {
            "craftable": "CRAFTABLE",
            "ready": "ALL ATTEMPTABLE",
            "difficult": "DIFFICULT",
            "armor": "ARMOR",
            "clothing": "CLOTHING",
            "materials": "MATERIALS",
            "search": f'SEARCH: {query}',
        }.get(mode, "ALL")
        await session.send(
            f"\r\n{_recipe_paint(_RECIPE_HEADER, f'=== {_profession_name(profession).upper()} RECIPES ===')}\r\n"
            f"Skill: {skill}\r\n"
            f"{len(scoped)} known recipes | {len(craftable)} craftable now | {len(difficult)} too difficult\r\n"
            f"Stations here: {station_text}\r\n"
            f"Showing: {view_label} ({len(selected)})\r\n"
        )
    else:
        await session.send(
            f"\r\n{_recipe_paint(_RECIPE_HEADER, '=== RECIPE BOOK ===')}\r\n"
            f"Stations here: {station_text}\r\n"
            "Use RECIPE <name> for full details.\r\n"
        )

    if mode == "overview":
        await session.send(
            "Showing a concise view. Use RECIPES <profession> for what you can craft now, "
            "or RECIPES HELP for filters.\r\n"
        )
        profession_order = ("blacksmithing", "tailoring", "alchemy", "enchanting", "cooking")
        for key in profession_order:
            recipes = [r for r in visible if r.trade_skill_key == key]
            if recipes:
                await _show_recipe_group(session, key, recipes, overview=True)
        return

    if not selected:
        await session.send("No recipes match that view right now.\r\n")
    else:
        profession_order = ("blacksmithing", "tailoring", "alchemy", "enchanting", "cooking")
        remaining = sorted({r.trade_skill_key for r in selected} - set(profession_order))
        for key in (*profession_order, *remaining):
            group = [r for r in selected if r.trade_skill_key == key]
            if group:
                # Profession-scoped screens already have their own header/counts.
                if profession is not None:
                    for recipe in sorted(group, key=_recipe_sort_key):
                        await session.send(_recipe_line(session, recipe))
                else:
                    await _show_recipe_group(session, key, group)

    if profession is not None:
        label = _profession_name(profession).upper()
        await session.send(
            f"\r\nFilters: ALL | CRAFTABLE | ARMOR | CLOTHING | MATERIALS | DIFFICULT\r\n"
            f"Search: RECIPES {label} SEARCH <text>\r\n"
            "Details: RECIPE <name>\r\n"
        )


async def _show_recipe_detail(session, target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    recipe, error = _resolve_recipe(target, session)
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
    station_style = _RECIPE_READY if state["station_ready"] else _RECIPE_LOCKED
    station_display = _recipe_paint(station_style, f"{station}  ({station_state})")
    success_pct = int(round(float(state["success_chance"]) * 100))
    skillup_pct = int(round(float(state["skillup_chance"]) * 100))
    if state["mastered"]:
        skill_state = "MASTERED — 100% success; this recipe no longer raises skill"
    elif state["skill_ready"]:
        skill_state = f"ATTEMPTABLE — {success_pct}% success; {skillup_pct}% skill-up chance"
    else:
        skill_state = (
            f"TOO DIFFICULT — recipes more than {crafting.MAX_CRAFT_DIFFICULTY_GAP} "
            "skill above you cannot be attempted"
        )

    await session.send(
        f"\r\n{_recipe_paint(_RECIPE_HEADER, '=== RECIPE ===')}\r\n"
        f"{_recipe_paint(_RECIPE_NAME, output_name)}\r\n"
        f"{recipe.description}\r\n\r\n"
        f"Profession : {profession}\r\n"
        f"Skill      : {state['skill']}\r\n"
        f"Trivial    : {recipe.trivial_skill}\r\n"
        f"Success    : {success_pct}%\r\n"
        f"Training   : {skill_state}\r\n"
        f"Craft time : {crafting.craft_time_seconds(recipe):g}s\r\n"
        f"Station    : {station_display}\r\n"
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

    await session.send(
        "\r\nCompleted failures consume the listed ingredients. Movement or damage interrupts the craft with no material loss.\r\n"
    )
    if state["craftable"]:
        await session.send(
            f"{_recipe_paint(_RECIPE_READY, 'You can attempt this now.')} "
            f"Use CRAFT {output_name}.\r\n"
        )
    else:
        reasons = []
        if not state["skill_ready"]:
            reasons.append("recipe is too difficult")
        if not state["materials_ready"]:
            reasons.append("materials")
        if not state["station_ready"]:
            reasons.append("station")
        await session.send(
            f"Not ready: {', '.join(reasons)}. When ready, use CRAFT {output_name}.\r\n"
        )

_CRAFT_BAR_WIDTH = 20


def _craft_bar(fraction: float) -> str:
    """Terminal-safe fallback bar.

    Do not use block/shade Unicode here. Mudlet profiles and raw Telnet clients
    can render those glyphs inconsistently, while '='/'-' is predictable in
    every monospaced terminal.
    """
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(_CRAFT_BAR_WIDTH * fraction))
    return "[" + ("=" * filled) + ("-" * (_CRAFT_BAR_WIDTH - filled)) + "]"


def _crafting_gmcp_available(session) -> bool:
    telnet = getattr(session, "telnet", None)
    return bool(telnet is not None and getattr(telnet, "gmcp_enabled", False))


async def _send_crafting_state(
    session,
    *,
    active: bool,
    output_name: str,
    fraction: float,
    duration: float,
    remaining: float,
    status: str,
    reason: str = "",
) -> None:
    telnet = getattr(session, "telnet", None)
    if telnet is None or not getattr(telnet, "gmcp_enabled", False):
        return
    fraction = max(0.0, min(1.0, float(fraction)))
    await telnet.send_gmcp(
        "Dreams.Crafting",
        {
            "active": bool(active),
            "item": str(output_name),
            "progress": round(fraction, 3),
            "percent": int(round(fraction * 100)),
            "duration": round(max(0.0, float(duration)), 2),
            "remaining": round(max(0.0, float(remaining)), 2),
            "status": str(status),
            "reason": str(reason),
            "interruptible": True,
        },
    )


async def _interrupt_craft(session, reason: str = "interrupted") -> bool:
    state = getattr(session, "_active_craft", None)
    if not isinstance(state, dict):
        return False

    session._active_craft = None
    task = state.get("task")
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()

    output_name = str(state.get("output_name") or "the item")
    duration = float(state.get("duration") or 0.0)
    fraction = float(state.get("progress") or 0.0)
    await _send_crafting_state(
        session,
        active=False,
        output_name=output_name,
        fraction=fraction,
        duration=duration,
        remaining=0.0,
        status="interrupted",
        reason=reason,
    )

    if reason == "movement":
        message = f"You stop crafting {output_name} as you move."
    elif reason == "damage":
        message = f"Your work on {output_name} is interrupted by damage."
    else:
        message = f"Your work on {output_name} is interrupted."
    await session.send(message + " No materials are consumed.\r\n")
    return True


async def _craft(session, target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot craft while fighting.\r\n")
        return
    if isinstance(getattr(session, "_active_cast", None), dict):
        await session.send("Finish or interrupt your spell before crafting.\r\n")
        return
    active = getattr(session, "_active_craft", None)
    if isinstance(active, dict):
        await session.send(f"You are already crafting {active.get('output_name', 'something')}.\r\n")
        return

    recipe, error = _resolve_recipe(target, session)
    if error:
        await session.send(error + "\r\n")
        return
    assert recipe is not None

    state = _recipe_state(session, recipe)
    if not state["skill_ready"]:
        await session.send(
            f"{_recipe_output_name(recipe)} is too difficult to attempt. "
            f"Your {recipe.trade_skill_key.title()} is {state['skill']}; "
            f"the recipe trivial is {recipe.trivial_skill}.\r\n"
        )
        return
    if not state["station_ready"]:
        label = STATION_LABELS.get(recipe.station_key, recipe.station_key)
        await session.send(f"This recipe requires a {label}. Use RESOURCES to see local stations.\r\n")
        return
    if not state["materials_ready"]:
        missing = [
            f"{needed - owned}x {name}"
            for owned, needed, name in state["materials"]
            if owned < needed
        ]
        await session.send("Missing materials: " + ", ".join(missing) + ".\r\n")
        return

    output_name = _recipe_output_name(recipe)
    duration = crafting.craft_time_seconds(recipe)
    success_pct = int(round(float(state["success_chance"]) * 100))
    craft_state = {
        "recipe": recipe,
        "output_name": output_name,
        "character_id": character.id,
        "room_key": character.current_room,
        "duration": duration,
        "progress": 0.0,
        "last_text_bucket": 0,
        "task": None,
    }
    session._active_craft = craft_state
    await session.send(
        f"You begin crafting {output_name} ({duration:g}s, {success_pct}% success, "
        f"trivial {recipe.trivial_skill}). Movement or damage will interrupt you.\r\n"
    )
    await _send_crafting_state(
        session,
        active=True,
        output_name=output_name,
        fraction=0.0,
        duration=duration,
        remaining=duration,
        status="crafting",
    )
    if not _crafting_gmcp_available(session):
        await session.send(f"Crafting: {_craft_bar(0.0)}   0%\r\n")

    async def finish_craft() -> None:
        started = monotonic()
        combatant = getattr(session, "combatant", None)
        last_hp = getattr(combatant, "current_hp", None) if combatant is not None else None
        try:
            while True:
                elapsed = monotonic() - started
                remaining = duration - elapsed
                if remaining <= 0:
                    break
                await asyncio.sleep(min(0.25, remaining))
                if getattr(session, "_active_craft", None) is not craft_state:
                    return

                current_character = getattr(session, "character", None)
                if current_character is None or current_character.id != craft_state["character_id"]:
                    await _interrupt_craft(session)
                    return
                if current_character.current_room != craft_state["room_key"]:
                    await _interrupt_craft(session, "movement")
                    return

                current_combatant = getattr(session, "combatant", None)
                current_hp = getattr(current_combatant, "current_hp", None) if current_combatant is not None else None
                if last_hp is not None and current_hp is not None and current_hp < last_hp:
                    await _interrupt_craft(session, "damage")
                    return
                last_hp = current_hp

                elapsed_now = monotonic() - started
                fraction = min(1.0, elapsed_now / duration)
                craft_state["progress"] = fraction
                await _send_crafting_state(
                    session,
                    active=True,
                    output_name=output_name,
                    fraction=fraction,
                    duration=duration,
                    remaining=max(0.0, duration - elapsed_now),
                    status="crafting",
                )

                # Raw Telnet fallback: use four readable milestones instead of
                # trying to redraw a live line with carriage returns/ANSI erase.
                # Mudlet gets the smooth bar through Dreams.Crafting GMCP.
                if not _crafting_gmcp_available(session):
                    bucket = min(3, int(fraction * 4))
                    if bucket > int(craft_state.get("last_text_bucket") or 0):
                        craft_state["last_text_bucket"] = bucket
                        pct = bucket * 25
                        await session.send(
                            f"Crafting: {_craft_bar(pct / 100.0)} {pct:>3}%\r\n"
                        )

            if getattr(session, "_active_craft", None) is not craft_state:
                return
            current_character = getattr(session, "character", None)
            if current_character is None or current_character.current_room != craft_state["room_key"]:
                await _interrupt_craft(session, "movement")
                return

            stations = set(_stations_here(session))
            station_key = recipe.station_key if recipe.station_key in stations else None
            result = crafting.craft_recipe(
                session.database,
                current_character.id,
                recipe.key,
                station_key=station_key,
            )
            if getattr(session, "_active_craft", None) is not craft_state:
                return
            session._active_craft = None
            craft_state["progress"] = 1.0
            await _send_crafting_state(
                session,
                active=False,
                output_name=output_name,
                fraction=1.0,
                duration=duration,
                remaining=0.0,
                status="complete" if result.completed and result.success else "failed",
            )
            if not _crafting_gmcp_available(session):
                await session.send(f"Crafting: {_craft_bar(1.0)} 100%\r\n")

            if not result.completed:
                await session.send(result.message + "\r\n")
                return

            if result.success:
                quality = " The work comes out especially clean." if result.high_quality else ""
                await session.send(
                    f"You finish crafting {recipe.output_quantity}x {output_name}.{quality}\r\n"
                )
            else:
                await session.send(
                    f"Your attempt to craft {output_name} fails. The materials are consumed.\r\n"
                )

            if result.skill_increased:
                await session.send(
                    f"{recipe.trade_skill_key.title()} improves to {result.new_skill_value}!\r\n"
                )
            else:
                current_skill = (
                    int(result.new_skill_value)
                    if result.new_skill_value is not None
                    else crafting.trade_skill_value(
                        session.database,
                        current_character.id,
                        recipe.trade_skill_key,
                    )
                )
                if current_skill >= recipe.trivial_skill:
                    await session.send(
                        f"No {recipe.trade_skill_key.title()} skill increase. "
                        f"Current skill: {current_skill}. This recipe is trivial for you and can no longer raise it.\r\n"
                    )
                else:
                    chance = int(
                        round(
                            crafting.craft_skillup_chance(
                                current_skill,
                                recipe.trivial_skill,
                            )
                            * 100
                        )
                    )
                    await session.send(
                        f"No {recipe.trade_skill_key.title()} skill increase this attempt. "
                        f"Current skill: {current_skill}. This recipe can still train you "
                        f"({chance}% chance per completed craft at this skill).\r\n"
                    )
        except asyncio.CancelledError:
            return
        finally:
            if getattr(session, "_active_craft", None) is craft_state:
                session._active_craft = None

    task = asyncio.create_task(finish_craft())
    craft_state["task"] = task

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
    previous_move_character = getattr(player_session_class, "move_character", None)
    previous_close = getattr(player_session_class, "close", None)


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
        if normalized in {"collect water", "collect spring water", "fill water", "fill spring water"}:
            # Only claim these aliases when the generic world actually exposes a
            # freshwater node here. This preserves specialized room handlers such
            # as Goblin Cleanwater Seep, which owns its own depletion clock.
            water, _ = _resolve_node(self, "water")
            if water is not None and water.state.definition.gathering_skill_key is None:
                await _gather(self, "water")
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

    if previous_move_character is not None:
        async def move_character(self, *args, **kwargs):
            if isinstance(getattr(self, "_active_craft", None), dict):
                await _interrupt_craft(self, "movement")
            return await previous_move_character(self, *args, **kwargs)

        player_session_class.move_character = move_character

    if previous_close is not None:
        async def close(self, *args, **kwargs):
            state = getattr(self, "_active_craft", None)
            if isinstance(state, dict):
                task = state.get("task")
                if task is not None and not task.done():
                    task.cancel()
                self._active_craft = None
            return await previous_close(self, *args, **kwargs)

        player_session_class.close = close

    player_session_class._economy_loop_runtime_installed = True
