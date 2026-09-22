from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from mud.world_data import REGIONS_BY_KEY


ECOLOGY_SCHEMA_VERSION = 1
MAX_OFFLINE_CATCHUP_HOURS = 24 * 7
ECOLOGY_TICK_SECONDS = 5.0

_WET_WEATHER = {"rain", "storm", "thunderstorm", "snow"}
_DRY_WEATHER = {"clear", "windy", "duststorm"}
_WILD_TAGS = (
    "wilderness", "swamp", "mire", "marsh", "bog", "fen", "forest",
    "wild", "hunt", "frontier", "field", "reach", "desert", "tundra",
    "cave", "cavern", "mountain", "coast", "shore", "plains",
    "grassland", "grove", "river", "trail",
)
_NON_ECOLOGICAL_TAGS = (
    "interior", "indoors", "market", "shop", "workshop", "cathedral",
    "crypt", "tunnel", "city", "urban", "house", "inn", "social",
)

_PREY_TOKENS = (
    "hare", "rabbit", "deer", "stag", "elk", "grazer", "goat", "ram",
    "boar", "rat", "mouse", "moth", "beetle", "tick", "swarm", "crab",
    "lizard", "wren", "bird", "grouse", "fish", "eel", "mirehorn",
)
_PREDATOR_TOKENS = (
    "wolf", "jackal", "stalker", "snapper", "spider", "serpent", "viper",
    "hound", "raptor", "cat", "lion", "croc", "wyrm", "hunter", "predator",
)
_SCAVENGER_TOKENS = (
    "scavenger", "vulture", "crow", "raven", "hyena", "carrion",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _approach(current: float, target: float, rate: float) -> float:
    return _clamp(current + (target - current) * rate)


@dataclass(slots=True)
class RegionEcologyState:
    moisture: float
    temperature: float
    vegetation: float
    insects: float
    prey: float
    predators: float
    carrion: float
    resource_stock: float
    mineral_stock: float
    disturbance: float
    last_total_hour: int

    def to_payload(self) -> dict[str, float | int]:
        return {
            "version": ECOLOGY_SCHEMA_VERSION,
            "moisture": round(_clamp(self.moisture), 6),
            "temperature": round(_clamp(self.temperature), 6),
            "vegetation": round(_clamp(self.vegetation), 6),
            "insects": round(_clamp(self.insects), 6),
            "prey": round(_clamp(self.prey), 6),
            "predators": round(_clamp(self.predators), 6),
            "carrion": round(_clamp(self.carrion), 6),
            "resource_stock": round(_clamp(self.resource_stock), 6),
            "mineral_stock": round(_clamp(self.mineral_stock), 6),
            "disturbance": round(_clamp(self.disturbance), 6),
            "last_total_hour": int(self.last_total_hour),
        }

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, object],
        *,
        fallback: "RegionEcologyState",
    ) -> "RegionEcologyState":
        def number(key: str, default: float) -> float:
            value = payload.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return default
            return _clamp(float(value))

        raw_hour = payload.get("last_total_hour", fallback.last_total_hour)
        last_hour = int(raw_hour) if isinstance(raw_hour, (int, float)) and not isinstance(raw_hour, bool) else fallback.last_total_hour
        return cls(
            moisture=number("moisture", fallback.moisture),
            temperature=number("temperature", fallback.temperature),
            vegetation=number("vegetation", fallback.vegetation),
            insects=number("insects", fallback.insects),
            prey=number("prey", fallback.prey),
            predators=number("predators", fallback.predators),
            carrion=number("carrion", fallback.carrion),
            resource_stock=number("resource_stock", fallback.resource_stock),
            mineral_stock=number("mineral_stock", fallback.mineral_stock),
            disturbance=number("disturbance", fallback.disturbance),
            last_total_hour=max(0, last_hour),
        )


class RegionalEcologyService:
    """Persistent region-scale ecology coupled to weather, wildlife, and gathering.

    The simulation intentionally works at region scale rather than one object per
    animal or plant. Rooms sample the regional state for presentation, regional
    creature pools use it as carrying capacity, and gathering feeds pressure back
    into the same state. This keeps the world responsive without turning a Telnet
    MUD into a costly per-entity ecosystem simulation.
    """

    def __init__(self) -> None:
        self._state_store = None
        self._rooms_by_key: dict[str, object] = {}
        self._region_rooms: dict[str, tuple[str, ...]] = {}
        self._region_biomes: dict[str, str] = {}
        self._adjacency: dict[str, set[str]] = {}

    def configure_world(self, rooms_by_key: Mapping[str, object]) -> None:
        self._rooms_by_key = dict(rooms_by_key)
        grouped: dict[str, list[str]] = {}
        for room_key, room in self._rooms_by_key.items():
            region_key = str(getattr(room, "region_key", "") or "")
            if region_key:
                grouped.setdefault(region_key, []).append(room_key)
        self._region_rooms = {
            region_key: tuple(sorted(room_keys))
            for region_key, room_keys in grouped.items()
        }

        self._region_biomes = {}
        for region_key, room_keys in self._region_rooms.items():
            authored = REGIONS_BY_KEY.get(region_key)
            if authored is not None:
                self._region_biomes[region_key] = authored.biome
                continue
            tags: list[str] = []
            for room_key in room_keys:
                room = self._rooms_by_key[room_key]
                tags.extend(str(tag) for tag in getattr(room, "tags", ()))
            self._region_biomes[region_key] = " ".join(tags) or "temperate"

        adjacency: dict[str, set[str]] = {key: set() for key in self._region_rooms}
        for room in self._rooms_by_key.values():
            source_region = str(getattr(room, "region_key", "") or "")
            if source_region not in adjacency:
                continue
            exits = getattr(room, "exits", {})
            destinations = exits.values() if isinstance(exits, dict) else ()
            for destination_key in destinations:
                destination = self._rooms_by_key.get(destination_key)
                destination_region = str(getattr(destination, "region_key", "") or "") if destination is not None else ""
                if destination_region and destination_region != source_region:
                    adjacency.setdefault(source_region, set()).add(destination_region)
                    adjacency.setdefault(destination_region, set()).add(source_region)

        for region_key, authored in REGIONS_BY_KEY.items():
            if region_key not in adjacency:
                continue
            for neighbor in authored.adjacent_regions:
                if neighbor in adjacency:
                    adjacency[region_key].add(neighbor)
                    adjacency[neighbor].add(region_key)
        self._adjacency = adjacency

    def _baseline(self, region_key: str, total_hour: int) -> RegionEcologyState:
        biome = self._region_biomes.get(region_key, "temperate").lower()
        moisture = 0.52
        temperature = 0.50
        vegetation = 0.58
        insects = 0.48
        prey = 0.52
        predators = 0.32
        resource_stock = 0.72
        mineral_stock = 0.72

        if "desert" in biome:
            moisture, temperature, vegetation, insects = 0.16, 0.78, 0.20, 0.18
            prey, predators, resource_stock = 0.32, 0.24, 0.58
            mineral_stock = 0.80
        elif any(token in biome for token in ("swamp", "marsh", "mire", "fen", "bog")):
            moisture, temperature, vegetation, insects = 0.84, 0.64, 0.82, 0.78
            prey, predators, resource_stock = 0.67, 0.43, 0.82
            mineral_stock = 0.62
        elif "forest" in biome:
            moisture, temperature, vegetation, insects = 0.66, 0.50, 0.86, 0.64
            prey, predators, resource_stock = 0.70, 0.42, 0.84
            mineral_stock = 0.66
        elif "tundra" in biome:
            moisture, temperature, vegetation, insects = 0.38, 0.18, 0.34, 0.18
            prey, predators, resource_stock = 0.48, 0.36, 0.58
            mineral_stock = 0.76
        elif "mountain" in biome:
            moisture, temperature, vegetation, insects = 0.45, 0.28, 0.38, 0.26
            prey, predators, resource_stock = 0.46, 0.33, 0.62
            mineral_stock = 0.88
        elif any(token in biome for token in ("cavern", "underground", "underway")):
            moisture, temperature, vegetation, insects = 0.72, 0.46, 0.48, 0.54
            prey, predators, resource_stock = 0.50, 0.31, 0.72
            mineral_stock = 0.82
        elif any(token in biome for token in ("river", "coast", "shore")):
            moisture, temperature, vegetation, insects = 0.68, 0.52, 0.68, 0.62
            prey, predators, resource_stock = 0.62, 0.37, 0.78
            mineral_stock = 0.64

        return RegionEcologyState(
            moisture=moisture,
            temperature=temperature,
            vegetation=vegetation,
            insects=insects,
            prey=prey,
            predators=predators,
            carrion=0.10,
            resource_stock=resource_stock,
            mineral_stock=mineral_stock,
            disturbance=0.08,
            last_total_hour=max(0, int(total_hour)),
        )

    def initialize(self, moment, state_store, rooms_by_key: Mapping[str, object]) -> None:
        self._state_store = state_store
        self.configure_world(rooms_by_key)
        region_ecology = getattr(state_store, "region_ecology", None)
        if not isinstance(region_ecology, dict):
            state_store.region_ecology = {}
            region_ecology = state_store.region_ecology

        for region_key in self._region_rooms:
            fallback = self._baseline(region_key, moment.total_hours)
            payload = region_ecology.get(region_key)
            if isinstance(payload, dict):
                state = RegionEcologyState.from_payload(payload, fallback=fallback)
            else:
                state = fallback
            region_ecology[region_key] = state.to_payload()

        self.sync(moment, state_store)

    def state_for(self, region_key: str) -> RegionEcologyState | None:
        store = self._state_store
        if store is None:
            return None
        payload = getattr(store, "region_ecology", {}).get(region_key)
        if not isinstance(payload, dict):
            return None
        fallback = self._baseline(region_key, int(payload.get("last_total_hour", 0) or 0))
        return RegionEcologyState.from_payload(payload, fallback=fallback)

    def _write(self, region_key: str, state: RegionEcologyState) -> None:
        if self._state_store is None:
            return
        self._state_store.region_ecology[region_key] = state.to_payload()

    @staticmethod
    def _season_temperature_target(season: str, baseline: float) -> float:
        offset = {
            "spring": 0.00,
            "summer": 0.12,
            "autumn": -0.04,
            "winter": -0.16,
        }.get(str(season).lower(), 0.0)
        return _clamp(baseline + offset)

    def _tick_region(self, region_key: str, state: RegionEcologyState, *, weather: str, season: str) -> None:
        baseline = self._baseline(region_key, state.last_total_hour)
        weather = str(weather).lower()

        if weather in {"storm", "thunderstorm"}:
            state.moisture = _clamp(state.moisture + 0.050)
        elif weather == "rain":
            state.moisture = _clamp(state.moisture + 0.034)
        elif weather == "snow":
            state.moisture = _clamp(state.moisture + 0.014)
            state.temperature = _clamp(state.temperature - 0.025)
        elif weather in {"mist", "humid", "damp"}:
            state.moisture = _clamp(state.moisture + 0.012)
        elif weather == "duststorm":
            state.moisture = _clamp(state.moisture - 0.030)
        elif weather == "windy":
            state.moisture = _clamp(state.moisture - 0.016)
        elif weather == "clear":
            evaporation = 0.012 + max(0.0, state.temperature - 0.55) * 0.025
            state.moisture = _clamp(state.moisture - evaporation)

        state.moisture = _approach(state.moisture, baseline.moisture, 0.015)
        seasonal_temp = self._season_temperature_target(season, baseline.temperature)
        state.temperature = _approach(state.temperature, seasonal_temp, 0.08)

        plant_water_fit = 1.0 - min(1.0, abs(state.moisture - 0.62) * 1.45)
        heat_fit = 1.0 - min(1.0, abs(state.temperature - 0.52) * 1.10)
        vegetation_target = _clamp(
            baseline.vegetation * 0.38
            + plant_water_fit * 0.34
            + heat_fit * 0.18
            + state.resource_stock * 0.16
            - state.disturbance * 0.18
        )
        state.vegetation = _approach(state.vegetation, vegetation_target, 0.055)

        insect_target = _clamp(
            state.vegetation * 0.48
            + state.moisture * 0.34
            + state.temperature * 0.18
            - state.disturbance * 0.10
        )
        state.insects = _approach(state.insects, insect_target, 0.09)

        prey_target = _clamp(
            state.vegetation * 0.50
            + state.insects * 0.30
            + state.resource_stock * 0.18
            - state.predators * 0.16
            - state.disturbance * 0.12
        )
        state.prey = _approach(state.prey, prey_target, 0.045)

        predator_target = _clamp(
            baseline.predators * 0.30
            + state.prey * 0.64
            + state.carrion * 0.10
            - state.disturbance * 0.08
        )
        state.predators = _approach(state.predators, predator_target, 0.035)

        natural_carrion = _clamp(state.predators * state.prey * 0.08)
        decay_rate = 0.11 + state.moisture * 0.05 + state.temperature * 0.05
        state.carrion = _clamp(state.carrion * (1.0 - decay_rate) + natural_carrion)

        renewable_target = _clamp(
            baseline.resource_stock * 0.35
            + state.vegetation * 0.48
            + state.moisture * 0.14
        )
        state.resource_stock = _approach(state.resource_stock, renewable_target, 0.035)
        # Geological deposits recover on a deliberately much slower horizon
        # than plants and fungi. This is extraction pressure, not plant ecology.
        state.mineral_stock = _approach(state.mineral_stock, baseline.mineral_stock, 0.003)
        state.disturbance = _clamp(state.disturbance * 0.955)

    def _migration_score(self, state: RegionEcologyState, *, predator: bool) -> float:
        comfort = 1.0 - abs(state.temperature - 0.50)
        if predator:
            return state.prey * 0.72 + state.carrion * 0.13 + comfort * 0.15 - state.disturbance * 0.20
        return (
            state.vegetation * 0.42
            + state.insects * 0.24
            + state.resource_stock * 0.20
            + comfort * 0.14
            - state.predators * 0.16
            - state.disturbance * 0.18
        )

    def _migrate(self) -> None:
        seen: set[tuple[str, str]] = set()
        for left, neighbors in self._adjacency.items():
            for right in neighbors:
                pair = tuple(sorted((left, right)))
                if pair in seen:
                    continue
                seen.add(pair)
                left_state = self.state_for(left)
                right_state = self.state_for(right)
                if left_state is None or right_state is None:
                    continue

                for field, predator in (("prey", False), ("predators", True)):
                    left_score = self._migration_score(left_state, predator=predator)
                    right_score = self._migration_score(right_state, predator=predator)
                    difference = right_score - left_score
                    if abs(difference) < 0.10:
                        continue
                    source, destination = (left_state, right_state) if difference > 0 else (right_state, left_state)
                    source_amount = getattr(source, field)
                    transfer = min(0.018, abs(difference) * 0.025, source_amount * 0.04)
                    if transfer <= 0:
                        continue
                    setattr(source, field, _clamp(source_amount - transfer))
                    setattr(destination, field, _clamp(getattr(destination, field) + transfer))

                self._write(left, left_state)
                self._write(right, right_state)

    def sync(self, moment, state_store=None) -> bool:
        if state_store is not None:
            self._state_store = state_store
        if self._state_store is None or not self._region_rooms:
            return False

        current_hour = int(moment.total_hours)
        deltas = []
        for region_key in self._region_rooms:
            state = self.state_for(region_key)
            if state is not None:
                deltas.append(max(0, current_hour - state.last_total_hour))
        if not deltas or max(deltas) <= 0:
            return False

        steps = min(MAX_OFFLINE_CATCHUP_HOURS, max(deltas))
        if max(deltas) > MAX_OFFLINE_CATCHUP_HOURS:
            floor = current_hour - MAX_OFFLINE_CATCHUP_HOURS
            for region_key in self._region_rooms:
                state = self.state_for(region_key)
                if state is not None and state.last_total_hour < floor:
                    state.last_total_hour = floor
                    self._write(region_key, state)

        for _ in range(steps):
            advanced = False
            for region_key in self._region_rooms:
                state = self.state_for(region_key)
                if state is None or state.last_total_hour >= current_hour:
                    continue
                weather = self._state_store.weather_for(region_key)
                self._tick_region(region_key, state, weather=weather, season=moment.season)
                state.last_total_hour += 1
                self._write(region_key, state)
                advanced = True
            if not advanced:
                break
            self._migrate()
        return True

    async def run(
        self,
        state_store,
        *,
        clock,
        interval_seconds: float = ECOLOGY_TICK_SECONDS,
        persist: Callable[[], None] | None = None,
    ) -> None:
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                if self.sync(clock.now(), state_store) and persist is not None:
                    persist()
        except asyncio.CancelledError:
            return

    @staticmethod
    def creature_role(definition) -> str:
        text = " ".join(
            (
                str(getattr(definition, "key", "")),
                str(getattr(definition, "name", "")),
                str(getattr(definition, "description", "")),
            )
        ).lower()
        if any(token in text for token in _SCAVENGER_TOKENS):
            return "scavenger"
        if any(token in text for token in _PREDATOR_TOKENS):
            return "predator"
        if any(token in text for token in _PREY_TOKENS):
            return "prey"
        return "other"

    def creature_population_multiplier(self, region_key: str, definition) -> float:
        state = self.state_for(region_key)
        if state is None:
            return 1.0
        role = self.creature_role(definition)
        if role == "prey":
            return max(0.55, min(1.45, 0.55 + state.prey * 1.10))
        if role == "predator":
            return max(0.60, min(1.40, 0.60 + state.predators * 1.05))
        if role == "scavenger":
            return max(0.65, min(1.40, 0.65 + state.carrion * 1.20 + state.prey * 0.25))
        return 1.0

    def record_creature_kill(self, region_key: str, definition) -> None:
        state = self.state_for(region_key)
        if state is None:
            return
        role = self.creature_role(definition)
        if role == "prey":
            state.prey = _clamp(state.prey - 0.035)
        elif role == "predator":
            state.predators = _clamp(state.predators - 0.045)
        elif role == "scavenger":
            state.carrion = _clamp(state.carrion - 0.020)
        state.carrion = _clamp(state.carrion + 0.028)
        state.disturbance = _clamp(state.disturbance + 0.018)
        self._write(region_key, state)

    def record_harvest(self, region_key: str, *, skill_key: str | None, amount: int = 1) -> None:
        state = self.state_for(region_key)
        if state is None:
            return
        units = max(1, int(amount))
        if skill_key == "mining":
            state.mineral_stock = _clamp(state.mineral_stock - 0.012 * units)
            vegetation_loss = 0.001 * units
        elif skill_key is None:
            state.resource_stock = _clamp(state.resource_stock - 0.002 * units)
            vegetation_loss = 0.0
        else:
            state.resource_stock = _clamp(state.resource_stock - 0.022 * units)
            vegetation_loss = 0.006 * units
        state.vegetation = _clamp(state.vegetation - vegetation_loss)
        state.disturbance = _clamp(state.disturbance + 0.006 * units)
        self._write(region_key, state)

    def gathering_allowed(self, region_key: str, *, skill_key: str | None) -> tuple[bool, str]:
        state = self.state_for(region_key)
        if state is None or skill_key is None:
            return True, ""
        if skill_key == "mining":
            if state.mineral_stock < 0.07:
                return False, "The workable material here has been picked thin. The site needs time before it will yield useful ore again."
            return True, ""

        biological_stock = min(state.resource_stock, state.vegetation * 0.85 + state.moisture * 0.15)
        if biological_stock < 0.12:
            return False, "Useful growth has been picked thin here. The land needs time and favorable conditions to recover."
        return True, ""

    def resource_status(self, region_key: str, *, skill_key: str | None) -> str:
        state = self.state_for(region_key)
        if state is None:
            return "normal"
        if skill_key == "mining":
            value = state.mineral_stock
        elif skill_key is None:
            value = max(0.55, state.moisture)
        else:
            value = min(state.resource_stock, state.vegetation * 0.85 + state.moisture * 0.15)
        if value >= 0.78:
            return "abundant"
        if value >= 0.55:
            return "healthy"
        if value >= 0.32:
            return "thinning"
        if value >= 0.12:
            return "sparse"
        return "picked thin"

    @staticmethod
    def room_is_ecological(tags: Iterable[str]) -> bool:
        normalized = tuple(str(tag).lower() for tag in tags)
        if any(token in tag for tag in normalized for token in _NON_ECOLOGICAL_TAGS):
            return False
        return any(token in tag for tag in normalized for token in _WILD_TAGS)

    def ambient_text(self, region_key: str, *, tags: Iterable[str] = ()) -> str:
        if tags and not self.room_is_ecological(tags):
            return ""
        state = self.state_for(region_key)
        if state is None:
            return ""
        if state.resource_stock < 0.16 or state.vegetation < 0.18:
            return "Useful growth is thin and scattered here, with more old cuttings than fresh shoots."
        if state.carrion > 0.30:
            return "Scavenger sign is unusually fresh: disturbed ground, picked remains, and circling tracks mark the area."
        if state.prey < 0.24 and state.predators > 0.42:
            return "Small game is scarce, but predator sign is fresh enough to make the quiet feel deliberate."
        if state.moisture > 0.74 and state.vegetation > 0.68:
            return "Fresh growth crowds the damp ground, and overlapping tracks suggest that the wet spell has drawn life outward."
        if state.moisture < 0.24 and state.vegetation < 0.42:
            return "The ground is dry and forage is thin; old tracks outnumber fresh ones."
        if state.prey > 0.70:
            return "Fresh tracks cross one another repeatedly here, evidence that game is moving through in good numbers."
        if state.predators > 0.58:
            return "Predator tracks appear often enough to suggest that hunters are following the same trails as their prey."
        return "The land shows an ordinary mix of fresh growth, small tracks, and older sign."

    def describe_region(self, region_key: str) -> tuple[str, ...]:
        state = self.state_for(region_key)
        if state is None:
            return ("The local land gives no clear ecological reading.",)

        if state.moisture >= 0.72:
            land = "The ground is wet and holding water well."
        elif state.moisture <= 0.26:
            land = "The ground is dry, and exposed growth is under strain."
        else:
            land = "Moisture and ground cover look broadly settled."

        if state.vegetation >= 0.70:
            growth = "Plant and fungal growth is flourishing."
        elif state.vegetation <= 0.28:
            growth = "Useful growth is sparse and slow to replace itself."
        else:
            growth = "Growth is present without crowding the land."

        if state.prey <= 0.28:
            wildlife = "Small-game sign is scarce."
        elif state.prey >= 0.68:
            wildlife = "Small-game tracks are common and recent."
        else:
            wildlife = "Small-game sign is scattered but steady."

        if state.predators >= 0.56:
            wildlife += " Predator sign is also unusually common."
        elif state.predators <= 0.24:
            wildlife += " Large predator sign is uncommon."

        resources = "Gatherable resources look " + self.resource_status(region_key, skill_key="herbalism") + "."
        return land, growth, wildlife, resources


ASTRALIS_ECOLOGY = RegionalEcologyService()


async def _delegate_command(session, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in session.__dict__
    prior_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    session.prompt = replay_prompt
    try:
        await previous_playing_prompt(session)
    finally:
        if had_instance_prompt:
            session.prompt = prior_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_ecology_runtime(player_session_class, world_service) -> None:
    """Expose ecology through natural room sign without showing simulation numbers."""

    if getattr(player_session_class, "_ecology_runtime_installed", False):
        return

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            character = getattr(self, "character", None)
            if character is None:
                return
            scene = world_service.scene(character.current_room or "")
            if scene is None:
                return
            text = ASTRALIS_ECOLOGY.ambient_text(scene.region_key, tags=scene.tags)
            if text:
                await self.send(text + "\r\n")

        player_session_class.show_current_room = show_current_room

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized in {"tracks", "wildlife", "read land", "read the land", "conditions", "ecology"}:
            scene = world_service.scene(self.character.current_room or "")
            if scene is None or not ASTRALIS_ECOLOGY.room_is_ecological(scene.tags):
                await self.send("This place is too built-up or enclosed for the surrounding ecology to leave a clear local reading.\r\n")
                return
            await self.send("\r\n--- Signs of the Land ---\r\n")
            for line in ASTRALIS_ECOLOGY.describe_region(scene.region_key):
                await self.send(line + "\r\n")
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._ecology_runtime_installed = True
