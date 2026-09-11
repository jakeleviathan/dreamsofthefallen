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
}


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


def _node_matches(node: ResourceNodeDefinition, target: str) -> bool:
    wanted = _normalize(target)
    return wanted in {
        _normalize(node.key),
        _normalize(node.name),
        _normalize(node.output_item_key),
        _normalize(crafting.ITEMS_BY_KEY.get(node.output_item_key).name)
        if node.output_item_key in crafting.ITEMS_BY_KEY
        else "",
    }


def _resolve_node(session, target: str, skill_key: str | None = None) -> tuple[LiveNode | None, str | None]:
    nodes = [
        live
        for live in _nodes_here(session)
        if skill_key is None or live.state.definition.gathering_skill_key == skill_key
    ]
    if target.strip():
        exact = [live for live in nodes if _node_matches(live.state.definition, target)]
        if not exact:
            wanted = _normalize(target)
            exact = [
                live
                for live in nodes
                if wanted in _normalize(live.state.definition.name)
                or wanted in _normalize(live.state.definition.key)
            ]
        if len(exact) == 1:
            return exact[0], None
        if len(exact) > 1:
            return None, "Be more specific about which resource node you want."
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
        "Commands: RESOURCES, RECIPES, CRAFT <recipe>, GIVE <player> [qty] <item>, TRADE <player>.\r\n"
    )


def _recipe_names(recipe: CraftingRecipe) -> set[str]:
    names = {_normalize(recipe.key)}
    output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
    if output is not None:
        names.add(_normalize(output.name))
    return names


def _resolve_recipe(target: str) -> tuple[CraftingRecipe | None, str | None]:
    wanted = _normalize(target)
    if not wanted:
        return None, "Name a recipe. Use RECIPES to browse them."
    exact = [recipe for recipe in crafting.ALL_RECIPES if wanted in _recipe_names(recipe)]
    if not exact:
        exact = [recipe for recipe in crafting.ALL_RECIPES if any(wanted in name for name in _recipe_names(recipe))]
    unique = tuple(dict.fromkeys(recipe.key for recipe in exact))
    if not unique:
        return None, "Unknown recipe. Use RECIPES to browse the current catalog."
    if len(unique) > 1:
        return None, "That matches several recipes. Use the recipe key shown by RECIPES."
    return crafting.RECIPES_BY_KEY[unique[0]], None


async def _show_recipes(session, profession_filter: str = "") -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    wanted = _normalize(profession_filter)
    recipes = [
        recipe
        for recipe in crafting.ALL_RECIPES
        if not wanted or wanted in {_normalize(recipe.trade_skill_key), _normalize(recipe.trade_skill_key + "ing")}
    ]
    if not recipes:
        await session.send("No recipes match that profession.\r\n")
        return
    await session.send("\r\n--- Recipes ---\r\n")
    for recipe in recipes:
        materials = ", ".join(
            f"{requirement.quantity}x "
            f"{crafting.ITEMS_BY_KEY.get(requirement.item_key).name if requirement.item_key in crafting.ITEMS_BY_KEY else requirement.item_key}"
            for requirement in recipe.materials
        )
        output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
        output_name = output.name if output is not None else recipe.output_item_key
        current = crafting.trade_skill_value(session.database, character.id, recipe.trade_skill_key)
        ready = "READY" if current >= recipe.minimum_skill else f"skill {current}/{recipe.minimum_skill}"
        station = STATION_LABELS.get(recipe.station_key, recipe.station_key or "none")
        await session.send(
            f"{recipe.key}: {output_name} | {ready} | {materials} | station: {station}\r\n"
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
        if normalized == "craft":
            await self.send("Use CRAFT <recipe>. Type RECIPES to browse the catalog.\r\n")
            return
        if normalized.startswith("craft "):
            await _craft(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._economy_loop_runtime_installed = True
