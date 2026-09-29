"""Regional brewing traditions for Astralis.

Cooking owns meals; Brewing owns drinks, fermentation, cellaring and the social
ritual around a shared pour. The two professions intentionally share regional
produce so gathering a local ingredient can support either kitchen.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import mud.brewing as brewing
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.regional_cooking as cooking
import mud.world as world
from mud.crafting import ConsumableEffect, ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.room_engine import FeatureDefinition, RoomAugmentation
from mud.stats import CharacterStats
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class BrewingTradition:
    key: str
    name: str
    identity: str
    brewer: str
    hall: str
    ingredient_key: str
    ingredient_name: str
    primary_label: str
    primary_family: str
    secondary_label: str
    secondary_family: str
    clue: str
    secret_name: str
    experiment_weather: tuple[str, ...]
    experiment_season: str
    description: str


TRADITIONS: tuple[BrewingTradition, ...] = (
    BrewingTradition(
        "goblin", "Goblin", "Brassgut Bottleworks", "Nikka Corksnap",
        "goblin_tinker_row", "mudpepper_pod", "Mudpepper Pod",
        "Scrap Cider", "cider", "Mirekick Tonic", "tonic",
        "copper-capped sour jar", "Floodbarrel No. 3",
        ("rain", "storm", "thunderstorm"), "spring",
        "Sharp swamp fruit, salvaged vessels and lively ferments that refuse to taste polite.",
    ),
    BrewingTradition(
        "dwarf", "Dwarven", "Deepfire Kegroom", "Bramma Kegwright",
        "dwarf_workshop_tier", "deepmalt_grain", "Deepmalt Grain",
        "Shift Ale", "ale", "Coalbreak Coffee", "coffee",
        "seven-notch mash paddle", "Nine-Shift Reserve",
        ("snow", "cloudy", "clear"), "winter",
        "Dense malt, measured temperatures and cellar schedules built around working shifts.",
    ),
    BrewingTradition(
        "forest", "Forest Elf", "Greenway Mead Table", "Sael Mosscup",
        "forest_elf_hearthwalk", "heartberry", "Heartberry",
        "Heartberry Mead", "mead", "Canopy Tea", "tea",
        "wax-sealed blossom cup", "First-Bloom Mead",
        ("rain", "mist", "clear"), "summer",
        "Wild honey, living fruit and gentle infusions that keep the season recognizable.",
    ),
    BrewingTradition(
        "moon", "Moon Elf", "Moonstep Infusion House", "Ilyra Stillmoon",
        "moon_elf_alpine_light_garden", "silverpear", "Silverpear",
        "Silverpear Cider", "cider", "Paleleaf Tea", "tea",
        "mirror-marked steeping glass", "Long-Moon Reserve",
        ("snow", "mist", "clear"), "winter",
        "Precise fruit ferments and timed infusions where water and temperature matter as much as ingredients.",
    ),
    BrewingTradition(
        "human", "Human", "Veyra Brewers' Measure", "Dessa Vintner",
        "veyra_public_hearth", "blackglass_onion", "Blackglass Onion",
        "Guild Bitter", "ale", "Blackglass Coffee", "coffee",
        "guild gravity slate", "Five-Gate Cordial",
        ("rain", "cloudy", "clear"), "autumn",
        "Repeatable guild methods, bitter roasting and careful blending built to travel between districts.",
    ),
    BrewingTradition(
        "troll", "Troll", "Frostroot Warmbarrel", "Vorga Warmbarrel",
        "troll_ember_hollow", "snowroot_tuber", "Snowroot Tuber",
        "Snowroot Ale", "ale", "Hearth Tonic", "tonic",
        "stone-lidded warming crock", "Longwinter Barrel",
        ("snow", "storm", "windy"), "winter",
        "Heavy warm ferments and root tonics intended to make exposed roads feel survivable.",
    ),
    BrewingTradition(
        "undead", "Undead", "Sepulcher Cordial Room", "Teren Ashcup",
        "undead_chisel_market", "ashdate", "Ashdate",
        "Ashdate Cordial", "cordial", "Quiet Tea", "tea",
        "paired-name bottle ledger", "Memorial Vintage",
        ("windy", "duststorm", "clear"), "autumn",
        "Preserved fruit, dry cordials and restrained infusions where the bottle records who it was meant to remember.",
    ),
    BrewingTradition(
        "spore", "Sporekin", "Lumen Culture Cellar", "Mellu Bubblecap",
        "sporekin_lumen_hollow", "honeycap", "Honeycap",
        "Living Ferment", "kvass", "Lumen Tisane", "tea",
        "breathing clay culture bell", "Sporewake Mother",
        ("damp", "mist", "rain"), "spring",
        "Living cultures and fungal infusions whose character comes from patient handling rather than brute strength.",
    ),
    BrewingTradition(
        "waymeet", "Crossroads", "Fifth Lantern Cellar", "Jori Sevenmug",
        "waymeet_fifth_lantern", "roadapple", "Roadapple",
        "Roadapple Cider", "cider", "Seven-Roads Blend", "blend",
        "seven-ring tasting board", "Crossroads House Reserve",
        ("rain", "storm", "mist", "clear"), "autumn",
        "Caravan fruit, borrowed techniques and practical blends that make the crossroads taste like everybody passed through.",
    ),
)
BY_KEY = {t.key: t for t in TRADITIONS}


def lesson_flag(region: str, tier_index: int) -> str:
    return f"brew_lesson_{region}_{tier_index}"


def secret_flag(region: str) -> str:
    return f"brew_secret_{region}"


def drink_key(region: str, band: str, slug: str) -> str:
    return f"brew_{region}_{band}_{slug}"


def _bonus(region: str, tier: int, family: str) -> CharacterStats:
    amount = 1 + int(tier >= 7)
    if family in {"ale", "kvass"}:
        return CharacterStats(might=amount, hp=max(0, tier // 4))
    if family == "cider":
        return CharacterStats(grace=amount)
    if family == "mead":
        return CharacterStats(love=amount)
    if family in {"tea", "coffee"}:
        return CharacterStats(mind=amount, grace=1 if family == "coffee" else 0)
    if family == "tonic":
        return CharacterStats(hp=2 + tier // 2)
    if family == "cordial":
        return CharacterStats(love=amount, mind=1)
    return CharacterStats(grace=1, love=1, mind=1)


def _materials(
    tradition: BrewingTradition,
    family: str,
    *,
    primary: bool,
    band_key: str,
) -> tuple[MaterialRequirement, ...]:
    ingredient = tradition.ingredient_key
    water = "filtered_brewing_water" if family in {"coffee", "tonic", "tea"} else "spring_water"
    if family == "ale":
        return (
            MaterialRequirement("field_grain", 2),
            MaterialRequirement(ingredient, 1),
            MaterialRequirement("brewers_yeast", 1),
            MaterialRequirement(water, 1),
        )
    if family == "cider":
        return (
            MaterialRequirement(ingredient, 2),
            MaterialRequirement("wild_yeast_culture", 1),
            MaterialRequirement(water, 1),
        )
    if family == "mead":
        return (
            MaterialRequirement("wild_honey", 2),
            MaterialRequirement(ingredient, 1),
            MaterialRequirement("brewers_yeast", 1),
            MaterialRequirement(water, 1),
        )
    if family == "kvass":
        return (
            MaterialRequirement("field_grain", 2),
            MaterialRequirement(ingredient, 1),
            MaterialRequirement("wild_yeast_culture", 1),
            MaterialRequirement(water, 1),
        )
    if family == "cordial":
        return (
            MaterialRequirement(ingredient, 2),
            MaterialRequirement("grain_alcohol", 1),
        )
    if family == "coffee":
        return (
            MaterialRequirement("cinderbean", 2),
            MaterialRequirement(ingredient, 1),
            MaterialRequirement(water, 1),
        )
    if family == "tonic":
        return (
            MaterialRequirement("bitterroot", 1),
            MaterialRequirement(ingredient, 1),
            MaterialRequirement(water, 1),
        )
    if family == "blend":
        # Crossroads blending stays grounded in finished beverages rather than
        # pretending two raw ingredients are a "blend".
        return (
            MaterialRequirement(f"brewed_{band_key}_fruit_cider", 1),
            MaterialRequirement(f"brewed_{band_key}_root_tonic", 1),
        )
    return (
        MaterialRequirement(ingredient, 1),
        MaterialRequirement("greenleaf", 1),
        MaterialRequirement(water, 1),
    )


def _process_profile(family: str, tier: int) -> tuple[int, int, str | None, str | None]:
    if family == "ale":
        return 34 + tier * 3, 45 + tier * 4, "brewers_yeast", "spring_water"
    if family == "cider":
        return 30 + tier * 3, 38 + tier * 4, "wild_yeast_culture", "spring_water"
    if family == "mead":
        return 42 + tier * 4, 60 + tier * 5, "brewers_yeast", "spring_water"
    if family == "kvass":
        return 20 + tier * 2, 22 + tier * 2, "wild_yeast_culture", "spring_water"
    if family == "cordial":
        return 10 + tier, 32 + tier * 3, None, None
    if family == "blend":
        return 12 + tier, 28 + tier * 2, None, None
    if family == "coffee":
        return 5 + tier, 0, None, "filtered_brewing_water"
    if family == "tonic":
        return 8 + tier, 0, None, "filtered_brewing_water"
    return 6 + tier, 0, None, "filtered_brewing_water"


def _catalog():
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []

    for tradition in TRADITIONS:
        for ti, band in enumerate(expansion.PROFESSION_BANDS):
            for slug, label, family, primary in (
                ("house", tradition.primary_label, tradition.primary_family, True),
                ("second", tradition.secondary_label, tradition.secondary_family, False),
            ):
                output = drink_key(tradition.key, band.key, slug)
                name = f"{band.name} {tradition.identity} {label}"
                ferment, age, yeast, water = _process_profile(family, band.tier)
                alcoholic = family in {"ale", "cider", "mead", "kvass", "cordial", "blend"}
                tags = ["brew", "regional", tradition.key, family]
                tags.append("alcoholic" if alcoholic else "nonalcoholic")
                if family == "coffee":
                    tags.append("caffeinated")
                if tradition.key == "goblin" and primary:
                    tags.append("belch")

                effect = ConsumableEffect(
                    use_mode="drink",
                    heal_hp=3 + band.tier,
                    temporary_stat_bonuses=_bonus(tradition.key, band.tier, family),
                    duration_ticks=12 + band.tier * 3 + int(primary) * 2,
                    effect_tags=tuple(tags),
                )
                items.append(ItemDefinition(
                    output,
                    name,
                    f"{tradition.description} A {family} made in the {tradition.identity} tradition.",
                    "beverage",
                    consumable=effect,
                    tier=band.tier,
                ))

                aged_key = None
                if age:
                    aged_key = f"{output}_cellared"
                    items.append(ItemDefinition(
                        aged_key,
                        f"Cellared {name}",
                        f"A patiently cellared bottle of {name}. Time changes its character more than its raw power.",
                        "beverage",
                        consumable=ConsumableEffect(
                            use_mode="drink",
                            heal_hp=effect.heal_hp,
                            temporary_stat_bonuses=effect.temporary_stat_bonuses,
                            duration_ticks=effect.duration_ticks + 8 + band.tier,
                            effect_tags=effect.effect_tags + ("cellared",),
                        ),
                        tier=band.tier,
                    ))

                recipe = CraftingRecipe(
                    f"regional_{output}",
                    "brewing",
                    output,
                    band.trivial + (2 if primary else 7),
                    band.trivial + (30 if primary else 35),
                    _materials(tradition, family, primary=primary, band_key=band.key),
                    output_quantity=2,
                    station_key="brewhouse",
                    description=f"Use the {tradition.identity} method to make {name}, then let the batch finish before bottling.",
                    design_status="regional_brewing_pattern",
                    discovery_flag=lesson_flag(tradition.key, ti),
                )
                recipes.append(recipe)
                brewing.register_process(brewing.BrewProcess(
                    recipe_key=recipe.key,
                    family=family,
                    ferment_seconds=ferment,
                    age_seconds=age,
                    aged_output_item_key=aged_key,
                    default_yeast_key=yeast,
                    default_water_key=water,
                    can_swap_yeast=yeast is not None,
                    can_swap_water=water is not None,
                    social_cups=3 if family in {"tea", "coffee", "tonic"} else 4,
                ))

        secret_output = f"brew_hidden_{tradition.key}"
        secret_aged = f"{secret_output}_cellared"
        secret_name = f"{tradition.identity} {tradition.secret_name}"
        secret_effect = ConsumableEffect(
            use_mode="drink",
            heal_hp=18,
            temporary_stat_bonuses=CharacterStats(might=1, grace=1, love=1, mind=1, hp=3),
            duration_ticks=58,
            effect_tags=("brew", "regional_secret", tradition.key, "alcoholic"),
        )
        items.extend((
            ItemDefinition(
                secret_output, secret_name,
                f"A hidden house brew recovered through weather, season and observation. {tradition.description}",
                "beverage", consumable=secret_effect, tier=8,
            ),
            ItemDefinition(
                secret_aged, f"Cellared {secret_name}",
                f"The cellar expression of {secret_name}, smoother and longer-lived rather than simply stronger.",
                "beverage",
                consumable=ConsumableEffect(
                    use_mode="drink",
                    heal_hp=secret_effect.heal_hp,
                    temporary_stat_bonuses=secret_effect.temporary_stat_bonuses,
                    duration_ticks=72,
                    effect_tags=secret_effect.effect_tags + ("cellared",),
                ),
                tier=8,
            ),
        ))
        secret_recipe = CraftingRecipe(
            f"brew_secret_{tradition.key}",
            "brewing",
            secret_output,
            190,
            225,
            (
                MaterialRequirement(tradition.ingredient_key, 3),
                MaterialRequirement("wild_honey", 1),
                MaterialRequirement("field_grain", 2),
                MaterialRequirement("wild_yeast_culture", 1),
                MaterialRequirement("filtered_brewing_water", 1),
            ),
            output_quantity=2,
            station_key="brewhouse",
            description=f"The hidden {tradition.name.lower()} process for {tradition.secret_name}.",
            design_status="regional_brewing_secret",
            discovery_flag=secret_flag(tradition.key),
        )
        recipes.append(secret_recipe)
        brewing.register_process(brewing.BrewProcess(
            recipe_key=secret_recipe.key,
            family="reserve",
            ferment_seconds=80,
            age_seconds=120,
            aged_output_item_key=secret_aged,
            default_yeast_key="wild_yeast_culture",
            default_water_key="filtered_brewing_water",
            can_swap_yeast=True,
            can_swap_water=True,
            social_cups=6,
        ))

    return tuple(items), tuple(recipes)


ITEMS, RECIPES = _catalog()
RECIPES_BY_KEY = {r.key: r for r in RECIPES}


def catalog_counts() -> dict[str, int]:
    return {
        "traditions": len(TRADITIONS),
        "regional_drinks": sum(r.design_status == "regional_brewing_pattern" for r in RECIPES),
        "hidden_drinks": sum(r.design_status == "regional_brewing_secret" for r in RECIPES),
        "regional_ingredients_reused": len({t.ingredient_key for t in TRADITIONS}),
        "house_styles": len(TRADITIONS) * 2,
    }


def install_regional_brewing_content(world_service=None) -> dict[str, int]:
    if getattr(crafting, "_regional_brewing_installed", False):
        return catalog_counts()

    # Brewing deliberately shares the local produce established by Cooking.
    # Calling this installer is safe and makes isolated tests deterministic.
    cooking.install_regional_cooking_content(world_service)

    missing_rooms = sorted({t.hall for t in TRADITIONS if t.hall not in world.ROOMS_BY_KEY})
    if missing_rooms:
        raise RuntimeError(f"Regional Brewing requires real rooms: {missing_rooms}")

    missing_inputs = sorted({t.ingredient_key for t in TRADITIONS if t.ingredient_key not in crafting.ITEMS_BY_KEY})
    if missing_inputs:
        raise RuntimeError(f"Regional Brewing requires regional produce: {missing_inputs}")

    expansion._register_items(ITEMS)
    expansion._register_recipes(RECIPES)

    for tradition in TRADITIONS:
        npc_key = f"regional_brewer_{tradition.key}"
        npc = NpcDefinition(
            npc_key,
            tradition.brewer,
            f"a {tradition.name.lower()} brewer checking cups, crocks and cellar marks",
            tradition.hall,
            "regional brewing teacher",
            (
                f"{tradition.brewer} says: 'The bottle starts with ingredients, but it becomes ours through time. "
                "TRAIN BREWING teaches the bands your skill can carry. BATCHES tells you what the cellar is doing.'",
            ),
        )
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
        if "brewhouse" not in stations:
            economy.ROOM_STATIONS[tradition.hall] = stations + ("brewhouse",)

        nodes = economy.ROOM_RESOURCE_NODE_KEYS.get(tradition.hall, ())
        for node_key in ("brewers_yeast_crock", "wild_yeast_jar"):
            if node_key not in nodes:
                nodes = nodes + (node_key,)
        economy.ROOM_RESOURCE_NODE_KEYS[tradition.hall] = nodes

        if world_service is not None:
            feature = FeatureDefinition(
                key=f"brew_clue_{tradition.key}",
                name=tradition.clue.title(),
                summary=f"a {tradition.clue} left among the brewing tools",
                examine_text=(
                    f"The {tradition.clue} points to {tradition.experiment_season} and particular weather. "
                    f"BREW EXPERIMENT {tradition.ingredient_name.upper()} here when those conditions meet."
                ),
                aliases=(tradition.clue,),
            )
            previous = world_service.augmentations.get(tradition.hall)
            if previous is None:
                world_service.augmentations[tradition.hall] = RoomAugmentation(features=(feature,))
            elif all(x.key != feature.key for x in previous.features):
                world_service.augmentations[tradition.hall] = replace(
                    previous, features=previous.features + (feature,)
                )
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(tradition.hall, None)

    invalid = [
        (recipe.key, req.item_key)
        for recipe in RECIPES
        for req in recipe.materials
        if req.item_key not in crafting.ITEMS_BY_KEY
    ]
    if invalid:
        raise RuntimeError(f"Missing regional Brewing materials: {invalid[:10]}")

    crafting._regional_brewing_installed = True
    return catalog_counts()
