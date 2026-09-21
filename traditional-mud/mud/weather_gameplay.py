from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class WeatherGameplayEffects:
    """Mechanical modifiers attached to a readable regional weather state."""

    ranged_attack_penalty: int = 0
    concealment_bonus: float = 0.0
    fire_disruption_chance: float = 0.0
    severe: bool = False
    visibility: str = "normal"


WEATHER_GAMEPLAY_EFFECTS: dict[str, WeatherGameplayEffects] = {
    "clear": WeatherGameplayEffects(),
    "cloudy": WeatherGameplayEffects(),
    "humid": WeatherGameplayEffects(),
    "damp": WeatherGameplayEffects(),
    "mist": WeatherGameplayEffects(
        ranged_attack_penalty=2,
        concealment_bonus=0.12,
        visibility="poor",
    ),
    "rain": WeatherGameplayEffects(
        ranged_attack_penalty=2,
        concealment_bonus=0.08,
        fire_disruption_chance=0.08,
        visibility="reduced",
    ),
    "storm": WeatherGameplayEffects(
        ranged_attack_penalty=4,
        concealment_bonus=0.18,
        fire_disruption_chance=0.20,
        severe=True,
        visibility="poor",
    ),
    "thunderstorm": WeatherGameplayEffects(
        ranged_attack_penalty=4,
        concealment_bonus=0.18,
        fire_disruption_chance=0.20,
        severe=True,
        visibility="poor",
    ),
    "snow": WeatherGameplayEffects(
        ranged_attack_penalty=2,
        concealment_bonus=0.10,
        severe=True,
        visibility="reduced",
    ),
    "windy": WeatherGameplayEffects(
        ranged_attack_penalty=2,
        visibility="normal",
    ),
    "duststorm": WeatherGameplayEffects(
        ranged_attack_penalty=5,
        concealment_bonus=0.22,
        fire_disruption_chance=0.05,
        severe=True,
        visibility="very poor",
    ),
}


@dataclass(frozen=True, slots=True)
class WeatherSurfaceCondition:
    key: str
    text: str
    travel_text: str
    travel_delay_seconds: float


_INDOOR_TAG_TOKENS = (
    "underground",
    "cavern",
    "interior",
    "indoors",
    "cathedral",
    "crypt",
    "tunnel",
    "underways",
)

_SOFT_GROUND_TAG_TOKENS = (
    "forest",
    "swamp",
    "mire",
    "marsh",
    "bog",
    "fen",
    "trail",
    "road",
    "training",
    "field",
    "tundra",
    "wilderness",
    "grove",
    "river",
    "surface",
)

_REGION_WEATHER_AMBIENCE: dict[str, dict[str, str]] = {
    "human_kingdom": {
        "rain": "Rain ticks from horned drainspouts and turns black stone glossy beneath the city lights.",
        "storm": "Wind worries banners and shutters while thunder rolls between the walls and cathedral spires.",
        "mist": "Mist softens the upper spires and leaves the nearest lamps hanging in pale halos.",
        "cloudy": "Low cloud flattens the city's dark stone into a single severe silhouette.",
    },
    "dwarven_mountain_industry": {
        "rain": "Rain hisses where it reaches hot metal and beads on freight rails, lift housings, and soot-dark stone.",
        "storm": "Thunder competes with foundry noise while exposed lifts slow and steam vents flatten in the wind.",
        "snow": "Snow catches on gantries and rooflines while crews keep the heated freight routes scraped clear.",
        "mist": "Mountain mist coils through bridges and lift towers, swallowing the farther industrial tiers.",
    },
    "great_elf_forest": {
        "rain": "Rain arrives first as a whisper high in the canopy, then falls in heavy drops from leaf to leaf.",
        "storm": "The canopy bends and hisses in the wind while deep thunder passes through the trunks like a distant drum.",
        "mist": "Mist lies between the trunks in pale layers, making familiar paths seem longer than they are.",
        "cloudy": "The canopy holds the gray light evenly, muting shadows beneath the leaves.",
    },
    "moon_peaks": {
        "snow": "Fine snow streams from the high ledges and erases the farther peaks a ridge at a time.",
        "storm": "Cloud and wind close around the heights, leaving only brief hard glimpses of stone between gusts.",
        "mist": "Cloud-mist slides directly through the settlement, turning balconies and bridges into islands.",
        "cloudy": "A cold lid of cloud hangs just above the peaks and dulls the polished stone.",
    },
    "junk_city_and_swamps": {
        "rain": "Rain drums on patched metal roofs and turns every low path into a fresh argument about drainage.",
        "storm": "The swamp lashes under hard rain while loose sheet metal bangs and ropes strain across the junk towers.",
        "mist": "Warm mist crawls between salvage stacks and hangs over the water in greasy-looking sheets.",
        "humid": "The air is thick enough to taste, carrying swamp water, hot metal, smoke, and wet wood.",
    },
    "troll_strongholds": {
        "snow": "Snow drives across the old routes and catches in hide lashings, tracks, and the lee of standing stones.",
        "storm": "The weather comes hard and unsheltered here, bending trees and carrying every loose sound into the distance.",
        "mist": "Cold mist gathers low among roots and stones, hiding movement beyond a short bowshot.",
        "rain": "Cold rain darkens bark and hide while runoff cuts new threads through the old tracks.",
    },
    "desert_necropolis": {
        "duststorm": "Dust turns the horizon solid and rasps across exposed stone like dry surf.",
        "windy": "Dry wind combs the open sand and whispers through cracks in ruined masonry.",
        "cloudy": "A rare ceiling of cloud steals the hard desert glare without bringing much relief.",
        "rain": "Sparse rain spots the dust and old stone, releasing a mineral smell from ground that seldom gets wet.",
    },
    "sporekin_underways": {
        "damp": "Moisture beads along roots and stone while the mycelial glow reflects in tiny silver points.",
        "mist": "A low fungal mist gathers in the cooler hollows and carries a faint earthy sweetness.",
        "rain": "Water filters down from the surface in new threads, waking small glints all along the living network.",
        "clear": "The deeper air is unusually still and clean, with only the slow pulse of the living network around it.",
    },
    "central_trade_city": {
        "rain": "Rain stipples the river and sends travelers crowding beneath arcades, bridge roofs, and market awnings.",
        "storm": "Thunder rolls over the crossroads while ferries shorten their runs and awnings snap in the wind.",
        "mist": "River mist blurs bridges, rooflines, and the far bank into layers of gray.",
        "cloudy": "Cloud shadow settles across the river crossroads and cools the crowded streets.",
    },
}

_GENERIC_WEATHER_AMBIENCE = {
    "clear": "The air is settled and the sky is clear.",
    "cloudy": "Cloud covers the sky and softens the light.",
    "mist": "Mist shortens the view and muffles distant movement.",
    "rain": "Rain falls steadily across the exposed ground.",
    "storm": "Wind and hard rain sweep the area beneath rolling thunder.",
    "thunderstorm": "Wind and hard rain sweep the area beneath rolling thunder.",
    "snow": "Snow moves through the air and gathers wherever the wind allows.",
    "windy": "A persistent wind moves across the exposed ground.",
    "duststorm": "Driven dust reduces the world to nearby shapes and moving grit.",
    "humid": "The air hangs close and heavy with moisture.",
    "damp": "Moisture clings to the surrounding surfaces.",
}


def effects_for_weather(weather: str, *, exposed: bool = True) -> WeatherGameplayEffects:
    if not exposed:
        return WeatherGameplayEffects()
    return WEATHER_GAMEPLAY_EFFECTS.get(weather.lower(), WeatherGameplayEffects())


def room_is_weather_exposed(tags: Iterable[str], room_key: str = "") -> bool:
    normalized = tuple(str(tag).strip().lower() for tag in tags)
    if any(token in tag for tag in normalized for token in _INDOOR_TAG_TOKENS):
        return False
    if room_key == "human_grand_cathedral":
        return False
    return True


def underground_weather_is_local(region_key: str) -> bool:
    return region_key == "sporekin_underways"


def weather_ambient_text(region_key: str, weather: str) -> str:
    normalized = weather.lower()
    regional = _REGION_WEATHER_AMBIENCE.get(region_key, {})
    return regional.get(normalized, _GENERIC_WEATHER_AMBIENCE.get(normalized, ""))


def weather_listen_text(region_key: str, weather: str, *, exposed: bool = True) -> str:
    if not exposed and not underground_weather_is_local(region_key):
        return "The structure around you blocks most of the weather; only faint outside sounds reach this place."
    normalized = weather.lower()
    if normalized in {"storm", "thunderstorm"}:
        return "Wind rises and falls around you, punctuated by hard rain and the long roll of thunder."
    if normalized == "rain":
        return "Rain makes a layered sound here: close drops, runoff, and a softer wash farther away."
    if normalized == "snow":
        return "The snowfall itself is nearly silent; wind and the small collapse of settling drifts make most of the sound."
    if normalized == "mist":
        return "The mist seems to swallow distance. Nearby sounds remain clear while farther ones lose their edges."
    if normalized == "duststorm":
        return "Wind drives grit against every exposed surface with a dry, relentless hiss."
    if normalized == "windy":
        return "Wind combs across the area in long gusts, tugging at anything loose."
    if normalized in {"damp", "humid"}:
        return "Water and small movements carry unusually well through the close, moisture-heavy air."
    return "The weather is quiet enough that ordinary local sounds dominate."


def weather_smell_text(region_key: str, weather: str, *, exposed: bool = True) -> str:
    if not exposed and not underground_weather_is_local(region_key):
        return "The outside weather contributes little here; the room's own scents dominate."
    normalized = weather.lower()
    if normalized in {"rain", "storm", "thunderstorm"}:
        if region_key == "human_kingdom":
            return "Wet stone, iron, soot, and gutter water sharpen in the rain."
        if region_key == "great_elf_forest":
            return "Wet bark, crushed leaves, dark soil, and clean rain fill the air."
        if region_key == "junk_city_and_swamps":
            return "Rain pulls up the smell of swamp water, rust, smoke, wet rope, and old timber."
        return "Rain brings out the smell of wet ground, stone, vegetation, and whatever the region has built upon them."
    if normalized == "snow":
        return "The cold air is spare and clean, muting most scents except smoke, resin, and nearby bodies."
    if normalized == "duststorm":
        return "Dry mineral dust overwhelms almost every other scent."
    if normalized in {"damp", "humid", "mist"}:
        return "Moisture thickens the local scents and makes earth, wood, stone, and living growth more noticeable."
    return "The settled weather adds little scent of its own."


def surface_condition(tags: Iterable[str], weather: str, *, exposed: bool = True) -> WeatherSurfaceCondition | None:
    if not exposed:
        return None
    normalized_tags = tuple(str(tag).strip().lower() for tag in tags)
    soft_ground = any(
        token in tag
        for tag in normalized_tags
        for token in _SOFT_GROUND_TAG_TOKENS
    )
    weather = weather.lower()

    if weather in {"rain", "storm", "thunderstorm"}:
        if soft_ground:
            return WeatherSurfaceCondition(
                "mud",
                "The exposed ground has churned into slick mud.",
                "Mud drags at your footing and slows the crossing.",
                0.35 if weather == "rain" else 0.55,
            )
        return WeatherSurfaceCondition(
            "slick",
            "Rain has left the exposed stone and hard surfaces slick underfoot.",
            "You shorten your stride on the rain-slick footing.",
            0.18 if weather == "rain" else 0.30,
        )

    if weather == "snow":
        return WeatherSurfaceCondition(
            "snow",
            "Fresh snow softens the route and hides the most reliable footing.",
            "You push through the snow more carefully than the bare route would require.",
            0.45,
        )

    if weather == "duststorm":
        return WeatherSurfaceCondition(
            "grit",
            "Windblown grit skates across the ground and gathers against every obstacle.",
            "You move with your face turned from the blowing grit.",
            0.30,
        )

    return None


def seasonal_sky_text(
    season: str,
    season_day: int,
    phase: str,
    moon_phase: str,
) -> str:
    """Return rare sky dressing tied to calendar turns without inventing prophecy."""

    if phase not in {"dusk", "night", "dawn"}:
        return ""
    if season_day == 1 and season == "summer":
        return "The first summer night holds a long afterglow at the horizon, a sky people across Astralis recognize as the turning into the bright season."
    if season_day == 1 and season == "winter":
        return "The first winter night comes hard and clear above breaks in the weather, marking the dark-season turning across Astralis."
    if moon_phase == "full" and phase == "night":
        return "Where the clouds permit it, the full moon lays a pale second light across exposed surfaces."
    return ""


def is_ranged_attack_style(attack_style: str | None) -> bool:
    return str(attack_style or "melee").strip().lower() == "ranged"


def adjusted_attack_roll(
    raw_roll: int,
    weather: str,
    *,
    ranged: bool,
    exposed: bool = True,
) -> int:
    penalty = effects_for_weather(weather, exposed=exposed).ranged_attack_penalty if ranged else 0
    return max(1, int(raw_roll) - penalty)


def fire_spell_disrupted(
    weather: str,
    roll: float,
    *,
    element: str | None,
    exposed: bool = True,
) -> bool:
    if str(element or "").lower() != "fire":
        return False
    chance = effects_for_weather(weather, exposed=exposed).fire_disruption_chance
    return chance > 0.0 and float(roll) < chance


def flee_success_chance(base_chance: float, weather: str, *, exposed: bool = True) -> float:
    effects = effects_for_weather(weather, exposed=exposed)
    return min(0.95, max(0.05, float(base_chance) + effects.concealment_bonus))
