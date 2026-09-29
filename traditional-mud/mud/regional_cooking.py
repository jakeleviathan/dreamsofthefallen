"""Regional cooking cultures and high-depth culinary progression for Astralis."""
from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.world as world
from mud.crafting import ConsumableEffect, ItemDefinition, ResourceNodeDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.room_engine import FeatureDefinition, RoomAugmentation
from mud.stats import CharacterStats
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class CookingTradition:
    key: str
    name: str
    identity: str
    chef: str
    hall: str
    gathering_room: str
    ingredient_key: str
    ingredient_name: str
    gathering_skill: str
    gathering_minimum: int
    technique: str
    clue: str
    secret_name: str
    experiment_weather: tuple[str, ...]
    experiment_season: str
    description: str


TRADITIONS: tuple[CookingTradition, ...] = (
    CookingTradition("goblin", "Goblin", "Brassgut Salvage-Kitchen", "Rikka Panhook",
        "goblin_tinker_row", "goblin_patchwork_plaza", "mudpepper_pod", "Mudpepper Pod",
        "harvesting", 0, "char-pan frying", "grease-blackened pan ledger", "Floodfire Scrappot",
        ("rain", "storm", "thunderstorm"), "spring",
        "Improvised heat, sharp swamp flavor and a talent for making unlikely ingredients useful."),
    CookingTradition("dwarf", "Dwarven", "Deepfire Hearth", "Orda Coalspoon",
        "dwarf_workshop_tier", "dwarf_upper_freight_deck", "deepmalt_grain", "Deepmalt Grain",
        "harvesting", 10, "smoking", "soot-marked smoke schedule", "Nine-Shift Smoke Board",
        ("snow", "cloudy", "clear"), "winter",
        "Dense breads, smoked provisions and long-cooked meals built for hard shifts."),
    CookingTradition("forest", "Forest Elf", "Greenway Living Table", "Sela Mossladle",
        "forest_elf_hearthwalk", "forest_elf_greenway", "heartberry", "Heartberry",
        "harvesting", 0, "open-fire roasting", "leaf-pressed recipe strip", "Canopy Ember Supper",
        ("rain", "mist", "clear"), "summer",
        "Seasonal herbs, berries and fire cooking that keeps ingredients recognizable."),
    CookingTradition("moon", "Moon Elf", "Moonstep Table", "Velira Palecup",
        "moon_elf_alpine_light_garden", "moon_elf_wind_terrace", "silverpear", "Silverpear",
        "harvesting", 25, "infusion", "mirror-written tea card", "Long Moon Supper",
        ("snow", "mist", "clear"), "winter",
        "Precise teas, fruit reductions and lightly preserved foods built around timing."),
    CookingTradition("human", "Human", "Veyra Guild Kitchen", "Mara Vell",
        "veyra_public_hearth", "veyra_north_waterworks", "blackglass_onion", "Blackglass Onion",
        "herbalism", 5, "reduction", "guild tasting slate", "Five-Gate Banquet",
        ("rain", "cloudy", "clear"), "autumn",
        "Measured sauces, public-hearth dishes and standardized guild recipes with room for mastery."),
    CookingTradition("troll", "Troll", "Frostroot Fire", "Hrukka Stonepot",
        "troll_ember_hollow", "troll_frostroot_camp", "snowroot_tuber", "Snowroot Tuber",
        "harvesting", 10, "stone-pot braising", "weathered bone spoon", "Longwinter Shelter Stew",
        ("snow", "storm", "windy"), "winter",
        "Heavy braises, preserved roots and warming food meant to survive exposed travel."),
    CookingTradition("undead", "Undead", "Sepulcher Preservation", "Neyra Ashsalt",
        "undead_chisel_market", "undead_desert_gate", "ashdate", "Ashdate",
        "herbalism", 10, "curing and pickling", "paired-name pickle crock", "Quieting Table",
        ("windy", "duststorm", "clear"), "autumn",
        "Curing, pickling and memorial dishes where preservation is part of the culture."),
    CookingTradition("spore", "Sporekin", "Lumen Ferment", "Phellu Softcap",
        "sporekin_lumen_hollow", "sporekin_mycelial_gallery", "honeycap", "Honeycap",
        "herbalism", 0, "fermentation", "breathing clay fermenter", "Sporewake Sharing Bowl",
        ("damp", "mist", "rain"), "spring",
        "Ferments, broths and living cultures whose flavor changes with patient handling."),
    CookingTradition("waymeet", "Crossroads", "Seven Roads Table", "Valline Hearthward",
        "waymeet_fifth_lantern", "waymeet_briarcut_fields", "roadapple", "Roadapple",
        "harvesting", 0, "crossroad blending", "seven-notched serving board", "Seven Roads Feast",
        ("rain", "storm", "mist", "clear"), "autumn",
        "Practical caravan food that deliberately combines techniques learned from every road."),
)
BY_KEY = {t.key: t for t in TRADITIONS}

DISH_PATTERNS = (
    ("bite", "Trail Bite", "snack", 1),
    ("bowl", "Hearth Bowl", "meal", 2),
    ("preserve", "Preserved Provision", "snack", 2),
    ("supper", "Shared Supper", "meal", 3),
)


def lesson_flag(region: str, tier_index: int) -> str:
    return f"cook_lesson_{region}_{tier_index}"


def secret_flag(region: str) -> str:
    return f"cook_secret_{region}"


def ingredient_node_key(region: str) -> str:
    return f"cook_ingredient_node_{region}"


def dish_key(region: str, band: str, slug: str) -> str:
    return f"cook_{region}_{band}_{slug}"


def _bonus(region: str, tier: int, slug: str) -> CharacterStats:
    amount = 1 + (tier >= 6)
    if region in {"goblin", "dwarf", "troll"}:
        return CharacterStats(might=amount, hp=tier // 2 + (1 if slug == "supper" else 0))
    if region in {"forest", "spore"}:
        return CharacterStats(love=amount, grace=1 if tier >= 4 else 0)
    if region in {"moon", "human"}:
        return CharacterStats(mind=amount, grace=1 if tier >= 5 else 0)
    if region == "undead":
        return CharacterStats(mind=amount, hp=max(1, tier // 2))
    return CharacterStats(grace=amount, love=1 if tier >= 4 else 0)


def _catalog():
    items: list[ItemDefinition] = []
    nodes: list[ResourceNodeDefinition] = []
    recipes: list[CraftingRecipe] = []
    for tradition in TRADITIONS:
        items.append(ItemDefinition(
            tradition.ingredient_key, tradition.ingredient_name,
            f"A regional cooking ingredient associated with {tradition.identity}.", "food_material", tier=1))
        nodes.append(ResourceNodeDefinition(
            ingredient_node_key(tradition.key), f"{tradition.ingredient_name} Patch",
            tradition.gathering_skill, tradition.ingredient_key,
            minimum_skill=tradition.gathering_minimum, design_status="regional_cooking_gathering",
            tier=2, region_hint=tradition.gathering_room.replace("_", " ").title()))

        for ti, band in enumerate(expansion.PROFESSION_BANDS):
            for offset, (slug, label, meal_kind, qty) in enumerate(DISH_PATTERNS):
                output = dish_key(tradition.key, band.key, slug)
                name = f"{tradition.identity} {band.name} {label}"
                heal = 5 + band.tier * 4 + offset * 2
                duration = (8 + band.tier * 3) if meal_kind == "snack" else (16 + band.tier * 4)
                tags = ("food", meal_kind, "regional", tradition.key, tradition.technique.replace(" ", "_"))
                items.append(ItemDefinition(
                    output, name,
                    f"{tradition.description} Prepared by {tradition.technique}.",
                    "food",
                    consumable=ConsumableEffect(
                        use_mode="eat", heal_hp=heal,
                        temporary_stat_bonuses=_bonus(tradition.key, band.tier, slug),
                        duration_ticks=duration, effect_tags=tags),
                    tier=band.tier))
                mats = [
                    MaterialRequirement(tradition.ingredient_key, qty),
                    MaterialRequirement(band.reagent_key, 1),
                ]
                if slug in {"bite", "supper"}:
                    mats.append(MaterialRequirement("field_grain", 1 + (slug == "supper")))
                if slug in {"bowl", "supper"}:
                    mats.append(MaterialRequirement("spring_water", 1))
                if slug == "preserve":
                    mats.append(MaterialRequirement("grain_alcohol", 1))
                recipes.append(CraftingRecipe(
                    f"regional_{output}", "cooking", output,
                    band.trivial + 2 + offset * 3, band.trivial + 30 + offset * 3,
                    tuple(mats), station_key="cookfire",
                    description=f"Use {tradition.technique} to prepare {name}.",
                    design_status="regional_cooking_pattern",
                    discovery_flag=lesson_flag(tradition.key, ti)))

        secret_output = f"cook_hidden_{tradition.key}"
        secret_name = f"{tradition.identity} {tradition.secret_name}"
        items.append(ItemDefinition(
            secret_output, secret_name,
            f"A legendary regional meal recovered through conditions, observation and experimentation. {tradition.description}",
            "food",
            consumable=ConsumableEffect(
                use_mode="eat", heal_hp=60,
                temporary_stat_bonuses=CharacterStats(might=2, grace=2, love=2, mind=2, hp=6),
                duration_ticks=64,
                effect_tags=("food", "feast", "regional_secret", tradition.key)),
            tier=8))
        recipes.append(CraftingRecipe(
            f"cook_secret_{tradition.key}", "cooking", secret_output, 185, 225,
            (
                MaterialRequirement(tradition.ingredient_key, 3),
                MaterialRequirement("astral_plum", 1),
                MaterialRequirement("grave_sage", 1),
                MaterialRequirement("rift_truffle", 1),
                MaterialRequirement("field_grain", 2),
                MaterialRequirement("spring_water", 1),
            ),
            output_quantity=2, station_key="cookfire",
            description=f"The hidden {tradition.name.lower()} method for {tradition.secret_name}.",
            design_status="regional_cooking_secret", discovery_flag=secret_flag(tradition.key)))
    return tuple(items), tuple(nodes), tuple(recipes)


ITEMS, NODES, RECIPES = _catalog()
RECIPES_BY_KEY = {r.key: r for r in RECIPES}


def catalog_counts() -> dict[str, int]:
    return {
        "traditions": len(TRADITIONS),
        "regional_dishes": sum(r.design_status == "regional_cooking_pattern" for r in RECIPES),
        "hidden_dishes": sum(r.design_status == "regional_cooking_secret" for r in RECIPES),
        "regional_ingredients": len(NODES),
        "techniques": len({t.technique for t in TRADITIONS}),
    }


def install_regional_cooking_content(world_service=None) -> dict[str, int]:
    if getattr(crafting, "_regional_cooking_installed", False):
        return catalog_counts()
    missing = sorted({r for t in TRADITIONS for r in (t.hall, t.gathering_room) if r not in world.ROOMS_BY_KEY})
    if missing:
        raise RuntimeError(f"Regional Cooking requires real rooms: {missing}")

    expansion._register_items(ITEMS)
    expansion._register_nodes(NODES)
    expansion._register_recipes(RECIPES)

    for tradition in TRADITIONS:
        npc_key = f"regional_cook_{tradition.key}"
        npc = NpcDefinition(
            npc_key, tradition.chef,
            f"a {tradition.name.lower()} cook tending a working hearth",
            tradition.hall, "regional cooking teacher",
            (f"{tradition.chef} says: 'Cooking here is about {tradition.technique}. "
             "TRAIN COOKING teaches the recipes your skill can carry. COOKBOOK tracks what you have learned.'",))
        if npc_key not in world.NPCS_BY_KEY:
            world.NPCS = world.NPCS + (npc,)
        world.NPCS_BY_KEY[npc_key] = npc
        room = world.ROOMS_BY_KEY[tradition.hall]
        if npc_key not in room.npc_keys:
            updated = replace(room, npc_keys=room.npc_keys + (npc_key,))
            world.ROOMS_BY_KEY[room.key] = updated
            world.ROOMS = tuple(updated if x.key == room.key else x for x in world.ROOMS)
            if world_service is not None:
                world_service.legacy_rooms[room.key] = updated

        stations = economy.ROOM_STATIONS.get(tradition.hall, ())
        if "cookfire" not in stations:
            economy.ROOM_STATIONS[tradition.hall] = stations + ("cookfire",)
        nodes = economy.ROOM_RESOURCE_NODE_KEYS.get(tradition.gathering_room, ())
        node = ingredient_node_key(tradition.key)
        if node not in nodes:
            economy.ROOM_RESOURCE_NODE_KEYS[tradition.gathering_room] = nodes + (node,)

        if world_service is not None:
            feature = FeatureDefinition(
                key=f"cook_clue_{tradition.key}", name=tradition.clue.title(),
                summary=f"a {tradition.clue} tucked near the working hearth",
                examine_text=(
                    f"The {tradition.clue} hints at a method that only makes sense in {tradition.experiment_season} "
                    f"and particular weather. COOK EXPERIMENT {tradition.ingredient_name.upper()} here when conditions fit."),
                aliases=(tradition.clue,))
            previous = world_service.augmentations.get(tradition.hall)
            if previous is None:
                world_service.augmentations[tradition.hall] = RoomAugmentation(features=(feature,))
            elif all(x.key != feature.key for x in previous.features):
                world_service.augmentations[tradition.hall] = replace(previous, features=previous.features + (feature,))
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(tradition.hall, None)

    invalid = [(r.key, m.item_key) for r in RECIPES for m in r.materials if m.item_key not in crafting.ITEMS_BY_KEY]
    if invalid:
        raise RuntimeError(f"Missing regional Cooking materials: {invalid[:10]}")
    crafting._regional_cooking_installed = True
    return catalog_counts()
