from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from mud.room_engine import RoomStateStore
from mud.world_data import REGIONS


REAL_SECONDS_PER_ASTRALIS_DAY = 4 * 60 * 60
REAL_SECONDS_PER_ASTRALIS_HOUR = REAL_SECONDS_PER_ASTRALIS_DAY / 24
ASTRALIS_MINUTES_PER_DAY = 24 * 60
# Fixed epoch keeps Astralis time deterministic and continuous across restarts.
# At this real timestamp Astralis Day 1 begins at 06:00.
REAL_EPOCH_SECONDS = 1767225600.0  # 2026-01-01 00:00:00 UTC
ASTRALIS_EPOCH_MINUTES = 6 * 60


@dataclass(frozen=True, slots=True)
class AstralisMoment:
    day_number: int
    hour: int
    minute: int
    total_minutes: int

    @property
    def phase(self) -> str:
        if 5 <= self.hour < 8:
            return "dawn"
        if 8 <= self.hour < 18:
            return "day"
        if 18 <= self.hour < 21:
            return "dusk"
        return "night"

    @property
    def total_hours(self) -> int:
        return self.total_minutes // 60

    @property
    def display(self) -> str:
        return f"Day {self.day_number}, {self.hour:02d}:{self.minute:02d} ({self.phase})"


class AstralisClock:
    """Accelerated persistent world clock.

    One complete Astralis day takes four real hours, making one Astralis hour
    equal to ten real minutes. Because the clock is anchored to a fixed epoch,
    world time continues naturally while the server is offline.
    """

    def now(self, real_seconds: float | None = None) -> AstralisMoment:
        current = time.time() if real_seconds is None else real_seconds
        elapsed_real = current - REAL_EPOCH_SECONDS
        scaled_minutes = int(elapsed_real * ASTRALIS_MINUTES_PER_DAY / REAL_SECONDS_PER_ASTRALIS_DAY)
        total_minutes = max(0, ASTRALIS_EPOCH_MINUTES + scaled_minutes)
        day_index, minute_of_day = divmod(total_minutes, ASTRALIS_MINUTES_PER_DAY)
        hour, minute = divmod(minute_of_day, 60)
        return AstralisMoment(
            day_number=day_index + 1,
            hour=hour,
            minute=minute,
            total_minutes=total_minutes,
        )


ASTRALIS_CLOCK = AstralisClock()


@dataclass(frozen=True, slots=True)
class WeatherEvent:
    region_key: str
    old_weather: str
    new_weather: str
    text: str


@dataclass(frozen=True, slots=True)
class WeatherProfile:
    default: str
    states: tuple[str, ...]
    stay_chance: dict[str, float]


TEMPERATE = WeatherProfile(
    default="clear",
    states=("clear", "cloudy", "mist", "rain", "storm"),
    stay_chance={"clear": 0.90, "cloudy": 0.82, "mist": 0.74, "rain": 0.72, "storm": 0.48},
)
FOREST = WeatherProfile(
    default="clear",
    states=("clear", "cloudy", "mist", "rain", "storm"),
    stay_chance={"clear": 0.88, "cloudy": 0.82, "mist": 0.78, "rain": 0.76, "storm": 0.50},
)
MOUNTAIN = WeatherProfile(
    default="clear",
    states=("clear", "cloudy", "mist", "snow", "storm"),
    stay_chance={"clear": 0.88, "cloudy": 0.80, "mist": 0.72, "snow": 0.80, "storm": 0.52},
)
SWAMP = WeatherProfile(
    default="humid",
    states=("humid", "mist", "cloudy", "rain", "storm"),
    stay_chance={"humid": 0.84, "mist": 0.78, "cloudy": 0.78, "rain": 0.78, "storm": 0.52},
)
DESERT = WeatherProfile(
    default="clear",
    states=("clear", "windy", "duststorm", "cloudy", "rain"),
    stay_chance={"clear": 0.94, "windy": 0.78, "duststorm": 0.55, "cloudy": 0.75, "rain": 0.45},
)
WILDERNESS = WeatherProfile(
    default="clear",
    states=("clear", "cloudy", "mist", "rain", "snow", "storm"),
    stay_chance={"clear": 0.88, "cloudy": 0.80, "mist": 0.75, "rain": 0.74, "snow": 0.80, "storm": 0.50},
)
UNDERWAYS = WeatherProfile(
    default="damp",
    states=("damp", "mist", "clear", "rain"),
    stay_chance={"damp": 0.90, "mist": 0.82, "clear": 0.84, "rain": 0.68},
)


def profile_for_biome(biome: str) -> WeatherProfile:
    value = biome.lower()
    if "desert" in value:
        return DESERT
    if "swamp" in value:
        return SWAMP
    if "mountain" in value:
        return MOUNTAIN
    if "forest" in value:
        return FOREST
    if "cavern" in value or "underground" in value:
        return UNDERWAYS
    if "tundra" in value or "wilderness" in value:
        return WILDERNESS
    return TEMPERATE


def _transition_candidates(profile: WeatherProfile, current: str) -> tuple[str, ...]:
    states = list(profile.states)
    if current not in states:
        return tuple(states)
    index = states.index(current)
    adjacent = {current}
    if index > 0:
        adjacent.add(states[index - 1])
    if index + 1 < len(states):
        adjacent.add(states[index + 1])
    # Allow a rare jump from settled weather into a severe state, but avoid
    # constantly snapping between unrelated extremes.
    severe = {"storm", "duststorm", "snow", "rain"}
    adjacent.update(state for state in states if state in severe)
    return tuple(state for state in states if state in adjacent)


def weather_change_text(region_name: str, old: str, new: str) -> str:
    if new == "rain":
        return f"Rain begins to move across {region_name}, first in scattered drops and then in a steadier fall."
    if new == "storm":
        return f"A storm gathers over {region_name}; wind rises and distant thunder begins to roll."
    if new == "snow":
        return f"Snow begins to fall across {region_name}, softening distant edges beneath a pale veil."
    if new == "mist":
        return f"Mist thickens through {region_name}, swallowing distance and muting the world beyond nearby shapes."
    if new == "cloudy":
        return f"A broad ceiling of cloud settles over {region_name}, flattening the light."
    if new == "windy":
        return f"The wind strengthens across {region_name}, carrying grit and dry leaves along exposed ground."
    if new == "duststorm":
        return f"A wall of dust builds across {region_name}, turning the horizon into a moving brown haze."
    if new == "humid":
        return f"The air across {region_name} grows close and humid, heavy with moisture."
    if new == "damp":
        return f"Moisture settles through {region_name}; stone, root, and soil all darken with damp."
    if new == "clear":
        if old in {"rain", "storm", "snow", "duststorm"}:
            return f"The weather over {region_name} breaks at last, leaving clearer air behind it."
        return f"The sky over {region_name} clears."
    return f"The weather across {region_name} shifts from {old} to {new}."


class AstralisWeatherService:
    """Low-volatility regional weather checked once per Astralis hour."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.last_total_hour: int | None = None

    def initialize(self, moment: AstralisMoment, state: RoomStateStore) -> None:
        self.last_total_hour = moment.total_hours
        for region in REGIONS:
            if region.key not in state.region_weather:
                state.set_weather(region.key, profile_for_biome(region.biome).default)

    def _roll_region(self, region_key: str, region_name: str, biome: str, state: RoomStateStore) -> WeatherEvent | None:
        profile = profile_for_biome(biome)
        current = state.weather_for(region_key)
        if current not in profile.states:
            current = profile.default
            state.set_weather(region_key, current)
        if self.rng.random() < profile.stay_chance.get(current, 0.85):
            return None

        candidates = [value for value in _transition_candidates(profile, current) if value != current]
        if not candidates:
            return None
        new_weather = self.rng.choice(candidates)
        state.set_weather(region_key, new_weather)
        return WeatherEvent(
            region_key=region_key,
            old_weather=current,
            new_weather=new_weather,
            text=weather_change_text(region_name, current, new_weather),
        )

    def sync(self, moment: AstralisMoment, state: RoomStateStore) -> tuple[WeatherEvent, ...]:
        if self.last_total_hour is None:
            self.initialize(moment, state)
            return ()
        if moment.total_hours == self.last_total_hour:
            return ()

        crossed = max(1, min(24, moment.total_hours - self.last_total_hour))
        events: list[WeatherEvent] = []
        for _ in range(crossed):
            for region in REGIONS:
                event = self._roll_region(region.key, region.name, region.biome, state)
                if event is not None:
                    events.append(event)
        self.last_total_hour = moment.total_hours
        return tuple(events)

    async def run(
        self,
        state: RoomStateStore,
        broadcast: Callable[[WeatherEvent], Awaitable[None]],
        *,
        clock: AstralisClock = ASTRALIS_CLOCK,
        interval_seconds: float = 5.0,
    ) -> None:
        if self.last_total_hour is None:
            self.initialize(clock.now(), state)
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                for event in self.sync(clock.now(), state):
                    await broadcast(event)
        except asyncio.CancelledError:
            return


ASTRALIS_WEATHER = AstralisWeatherService()


RAINY_WEATHER = frozenset({"rain", "storm", "thunderstorm"})

# Current authored outdoor/surface rooms where standing rainwater can reasonably
# collect. Future room content can migrate this into an explicit outdoor tag.
PUDDLE_ELIGIBLE_ROOMS = frozenset({
    "human_demon_gate", "human_ashen_way", "human_cathedral_square",
    "human_outer_drill_road", "human_training_yard", "human_practice_ring",
    "human_vermin_pens", "human_sootstairs", "human_cinder_lane",
    "human_blackglass_arch", "human_lantern_court",
    "forest_elf_circle_clearing", "forest_elf_greenway", "forest_elf_old_river_path",
    "forest_elf_waystone_bend", "forest_elf_listening_pool", "forest_elf_outer_grove",
    "forest_elf_briarshadow_thicket", "sporekin_rainroot_verge",
    "sporekin_forgotten_grove", "sporekin_memory_path",
})


def puddle_available(room_key: str, region_key: str, state: RoomStateStore) -> bool:
    return room_key in PUDDLE_ELIGIBLE_ROOMS and state.weather_for(region_key) in RAINY_WEATHER
