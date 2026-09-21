from __future__ import annotations

import asyncio
import random
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Iterable

import mud.combat as combat
from mud.world import (
    FOREST_ELF_BRIARSHADOW_THICKET_KEY,
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OLD_RIVER_PATH_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_START_ROOM_KEY,
    FOREST_ELF_WAYSTONE_BEND_KEY,
    HUMAN_START_ROOM_KEY,
    HUMAN_TRAINING_YARD_KEY,
    ROOMS_BY_KEY,
)


NPC_TICK_SECONDS = 5.0

# Regional populations complement authored one-off room enemies. The manager
# keeps a modest shared population alive across a habitat, increases it gently
# when more players are hunting there, and refills kills out of sight instead of
# popping a replacement into the room where a creature just died.
REGIONAL_BASE_POPULATION = 3
REGIONAL_MAX_POPULATION = 8
REGIONAL_REFILL_TICKS = 6  # 30 real seconds at the default five-second NPC tick.
REGIONAL_HABITAT_DEPTH = 3
REGIONAL_RARE_ROLL_PER_TICK = 0.0025
REGIONAL_RARE_TTL_TICKS = 72  # Six minutes before an unseen rare moves on.
REGIONAL_MAX_DYNAMIC_PER_ROOM = 2

_REGIONAL_BLOCKED_TAG_TOKENS = (
    "tutorial",
    "safe",
    "peaceful",
    "market",
    "merchant",
    "shop",
    "mentor",
    "sanctuary",
    "social",
    "workshop",
    "station",
    "shelter",
    "training",
    "home",
    "start",
    "quest",
    "story",
    "boss",
    "elite",
    "unique",
    "event",
    "capstone",
    "scripted",
    "instance",
    "arena",
    "ritual",
    "finale",
    "setpiece",
)
_REGIONAL_WILD_TAG_TOKENS = (
    "wilderness",
    "swamp",
    "mire",
    "marsh",
    "bog",
    "fen",
    "forest",
    "wild",
    "hunt",
    "frontier",
    "field",
    "reach",
    "desert",
    "tundra",
    "cave",
    "cavern",
    "mountain",
    "coast",
    "shore",
    "plains",
    "grassland",
)

REVERSE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "below",
    "down": "above",
}

BEHAVIOR_WANDER = "wander"
BEHAVIOR_PATROL = "patrol"
BEHAVIOR_HUNTER = "hunter"
BEHAVIOR_ROUTINE = "routine"
VALID_BEHAVIORS = {
    BEHAVIOR_WANDER,
    BEHAVIOR_PATROL,
    BEHAVIOR_HUNTER,
    BEHAVIOR_ROUTINE,
}


@dataclass(frozen=True, slots=True)
class RoutineStop:
    """A room an NPC tries to occupy beginning at a given in-world hour."""

    start_hour: int
    room_key: str


@dataclass(frozen=True, slots=True)
class MobileNpcDefinition:
    key: str
    name: str
    short_description: str
    spawn_room_key: str
    allowed_room_keys: tuple[str, ...]
    behavior: str = BEHAVIOR_WANDER
    move_chance_per_tick: float = 0.35
    patrol_route: tuple[str, ...] = ()
    routine_schedule: tuple[RoutineStop, ...] = ()
    weather_shelter_room_key: str | None = None
    shelter_weathers: tuple[str, ...] = ("storm", "thunderstorm", "snow", "duststorm")
    aliases: tuple[str, ...] = ()
    aggressive: bool = False
    # 0 means same-room aggro. Dreams of the Fallen currently does not permit
    # passive cross-room detection for hostile NPCs.
    aggro_radius: int = 0
    pursuit_chance_after_flee: float = 0.65
    max_hp: int = 1
    armor_class: int = 0
    auto_attack_damage: int = 0
    auto_attack_interval: float = 3.0
    xp_reward: int = 0
    # "Aggressive" controls automatic same-room aggro. "Attackable" lets a
    # peaceful-roaming creature be hunted without making every passing animal
    # initiate combat. Regional creatures use combat_enemy_key so their unique
    # instance key does not break loot/quest tables keyed to the authored enemy.
    attackable: bool = False
    combat_enemy_key: str | None = None
    rare: bool = False

    @property
    def movement_pattern(self) -> str:
        """Compatibility alias for older code/tests that used movement_pattern."""
        return "random" if self.behavior == BEHAVIOR_WANDER else self.behavior


@dataclass(frozen=True, slots=True)
class RegionalSpawnDefinition:
    key: str
    region_key: str
    enemy_key: str
    room_keys: tuple[str, ...]
    source_room_keys: tuple[str, ...]
    base_population: int = REGIONAL_BASE_POPULATION
    max_population: int = REGIONAL_MAX_POPULATION


@dataclass(slots=True)
class MobileNpcState:
    definition: MobileNpcDefinition
    current_room_key: str
    patrol_index: int = 0
    engaged_character_id: int | None = None
    returning_to_duty: bool = False
    inactive_ticks: int = 0

    @property
    def active(self) -> bool:
        return self.inactive_ticks <= 0


@dataclass(frozen=True, slots=True)
class NpcMovement:
    npc_key: str
    npc_name: str
    origin_room_key: str
    destination_room_key: str
    direction: str
    behavior: str = BEHAVIOR_WANDER
    reason: str = "roaming"

    @property
    def arrival_from(self) -> str:
        return REVERSE_DIRECTIONS.get(self.direction, "nearby")

    @property
    def movement_verb(self) -> str:
        if self.reason == "sheltering":
            return "hurries"
        if self.behavior == BEHAVIOR_PATROL:
            return "marches"
        if self.behavior == BEHAVIOR_HUNTER:
            return "stalks" if self.reason == "pursuit" else "prowls"
        if self.behavior == BEHAVIOR_ROUTINE:
            return "walks"
        return "wanders"


# ---------------------------------------------------------------------------
# Ambient Forest Elf wildlife: random wanderers.
# ---------------------------------------------------------------------------
SILVERLEAF_HARE = MobileNpcDefinition(
    key="silverleaf_hare",
    name="Silverleaf Hare",
    short_description="a small gray hare nosing cautiously through the ferns",
    spawn_room_key="forest_elf_greenway",
    allowed_room_keys=(
        "forest_elf_greenway",
        FOREST_ELF_OLD_RIVER_PATH_KEY,
        FOREST_ELF_WAYSTONE_BEND_KEY,
        FOREST_ELF_LISTENING_POOL_KEY,
    ),
    behavior=BEHAVIOR_WANDER,
    move_chance_per_tick=0.42,
)

REDTAIL_SQUIRREL = MobileNpcDefinition(
    key="redtail_squirrel",
    name="Redtail Squirrel",
    short_description="a russet squirrel with an oversized tail and bright black eyes",
    spawn_room_key=FOREST_ELF_START_ROOM_KEY,
    allowed_room_keys=(
        FOREST_ELF_START_ROOM_KEY,
        "forest_elf_greenway",
        FOREST_ELF_OLD_RIVER_PATH_KEY,
    ),
    behavior=BEHAVIOR_WANDER,
    move_chance_per_tick=0.32,
)

WILLOW_WREN = MobileNpcDefinition(
    key="willow_wren",
    name="Willow Wren",
    short_description="a tiny green-brown songbird flitting between the lower branches",
    spawn_room_key=FOREST_ELF_LISTENING_POOL_KEY,
    allowed_room_keys=(
        FOREST_ELF_OLD_RIVER_PATH_KEY,
        FOREST_ELF_WAYSTONE_BEND_KEY,
        FOREST_ELF_LISTENING_POOL_KEY,
        FOREST_ELF_OUTER_GROVE_KEY,
    ),
    behavior=BEHAVIOR_WANDER,
    move_chance_per_tick=0.48,
)

# ---------------------------------------------------------------------------
# Authored behavior examples in the existing world.
# ---------------------------------------------------------------------------
BLACKWALL_GUARD = MobileNpcDefinition(
    key="blackwall_guard",
    name="Blackwall Guard",
    short_description="a dark-uniformed city guard making a measured circuit of the outer wall",
    spawn_room_key=HUMAN_START_ROOM_KEY,
    allowed_room_keys=(
        HUMAN_START_ROOM_KEY,
        "human_outer_drill_road",
        HUMAN_TRAINING_YARD_KEY,
    ),
    behavior=BEHAVIOR_PATROL,
    move_chance_per_tick=0.75,
    # The repeated drill-road stop creates a legal out-and-back patrol.
    patrol_route=(
        HUMAN_START_ROOM_KEY,
        "human_outer_drill_road",
        HUMAN_TRAINING_YARD_KEY,
        "human_outer_drill_road",
    ),
    weather_shelter_room_key=HUMAN_START_ROOM_KEY,
)

BRIARSHADOW_STALKER = MobileNpcDefinition(
    key="briarshadow_stalker",
    name="Briarshadow Stalker",
    short_description="a lean dark-furred forest predator watching from beneath the thorn canopy",
    spawn_room_key=FOREST_ELF_BRIARSHADOW_THICKET_KEY,
    allowed_room_keys=(
        FOREST_ELF_BRIARSHADOW_THICKET_KEY,
        FOREST_ELF_OUTER_GROVE_KEY,
    ),
    behavior=BEHAVIOR_HUNTER,
    move_chance_per_tick=0.70,
    aliases=("stalker", "briarshadow stalker", "predator"),
    aggressive=True,
    aggro_radius=0,
    pursuit_chance_after_flee=0.70,
    max_hp=34,
    armor_class=6,
    auto_attack_damage=4,
    auto_attack_interval=2.8,
    xp_reward=55,
)

ASHEN_WAY_CURIO_PEDDLER = MobileNpcDefinition(
    key="ashen_way_curio_peddler",
    name="Ashen Way Curio Peddler",
    short_description="a black-coated peddler carrying a lacquered case of charms, relics, and dubious curios",
    spawn_room_key="human_ashen_way",
    allowed_room_keys=(
        HUMAN_START_ROOM_KEY,
        "human_ashen_way",
        "human_cathedral_square",
    ),
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    routine_schedule=(
        RoutineStop(0, "human_ashen_way"),      # shutters/stockroom overnight
        RoutineStop(7, HUMAN_START_ROOM_KEY),   # catches early gate traffic
        RoutineStop(9, "human_ashen_way"),      # main daytime market
        RoutineStop(18, "human_cathedral_square"),  # evening clerical crowds
        RoutineStop(22, "human_ashen_way"),     # returns to the shopfront
    ),
    weather_shelter_room_key="human_ashen_way",
    shelter_weathers=("rain", "storm", "thunderstorm", "snow", "duststorm"),
)

AMBIENT_FOREST_ANIMALS: tuple[MobileNpcDefinition, ...] = (
    SILVERLEAF_HARE,
    REDTAIL_SQUIRREL,
    WILLOW_WREN,
)

BEHAVIOR_EXAMPLE_NPCS: tuple[MobileNpcDefinition, ...] = (
    BLACKWALL_GUARD,
    BRIARSHADOW_STALKER,
    ASHEN_WAY_CURIO_PEDDLER,
)

MOBILE_NPC_DEFINITIONS: tuple[MobileNpcDefinition, ...] = (
    *AMBIENT_FOREST_ANIMALS,
    *BEHAVIOR_EXAMPLE_NPCS,
)
MOBILE_NPCS_BY_KEY = {npc.key: npc for npc in MOBILE_NPC_DEFINITIONS}


MovementCallback = Callable[[NpcMovement], Awaitable[None]]
PlayerRoomsProvider = Callable[[], Iterable[str]]
HourProvider = Callable[[], int]
WeatherProvider = Callable[[str], str]


class MobileNpcManager:
    """Owns mobile NPC position, boundaries, and lightweight behavior AI.

    Boundaries are authoritative. A behavior may choose *how* an NPC moves, but
    never where it is permitted to exist. Hunters therefore stop at habitat
    edges, patrols cannot leave their post, and scheduled NPCs may only route
    through rooms authored in their allowed-room set.
    """

    def __init__(self, definitions: tuple[MobileNpcDefinition, ...] = MOBILE_NPC_DEFINITIONS) -> None:
        self.definitions = definitions
        self.states: dict[str, MobileNpcState] = {}
        self.regional_pools: dict[str, RegionalSpawnDefinition] = {}
        self._regional_instance_to_pool: dict[str, str] = {}
        self._regional_next_spawn_tick: dict[str, int] = {}
        self._rare_expiry_tick: dict[str, int] = {}
        self._regional_serial = 0
        self._tick_index = 0
        self.reset()
        self.validate_definitions()
        self.regional_pools = self._build_regional_spawn_definitions()
        self._regional_next_spawn_tick = {key: 0 for key in self.regional_pools}
        self._seed_regional_population()

    def reset(self) -> None:
        self.states = {}
        self._regional_instance_to_pool.clear()
        self._rare_expiry_tick.clear()
        self._tick_index = 0
        for definition in self.definitions:
            patrol_index = 0
            if definition.patrol_route:
                try:
                    patrol_index = definition.patrol_route.index(definition.spawn_room_key)
                except ValueError:
                    patrol_index = 0
            self.states[definition.key] = MobileNpcState(
                definition=definition,
                current_room_key=definition.spawn_room_key,
                patrol_index=patrol_index,
            )
        if self.regional_pools:
            self._regional_next_spawn_tick = {key: 0 for key in self.regional_pools}
            self._seed_regional_population()

    def validate_definitions(self) -> None:
        for definition in self.definitions:
            if definition.spawn_room_key not in ROOMS_BY_KEY:
                raise ValueError(f"Unknown spawn room for {definition.key}: {definition.spawn_room_key}")
            allowed = set(definition.allowed_room_keys)
            if definition.spawn_room_key not in allowed:
                raise ValueError(f"Spawn room must be inside the boundary for {definition.key}")
            unknown = allowed.difference(ROOMS_BY_KEY)
            if unknown:
                raise ValueError(f"Unknown boundary rooms for {definition.key}: {sorted(unknown)}")
            if not 0.0 <= definition.move_chance_per_tick <= 1.0:
                raise ValueError(f"Invalid move chance for {definition.key}")
            if definition.behavior not in VALID_BEHAVIORS:
                raise ValueError(f"Unknown behavior for {definition.key}: {definition.behavior}")

            if definition.behavior == BEHAVIOR_PATROL:
                route = definition.patrol_route
                if not route:
                    raise ValueError(f"Patrol NPC {definition.key} requires a patrol route")
                if set(route).difference(allowed):
                    raise ValueError(f"Patrol route leaves boundary for {definition.key}")
                for origin, destination in zip(route, route[1:] + route[:1]):
                    if destination not in ROOMS_BY_KEY[origin].exits.values():
                        raise ValueError(
                            f"Patrol route for {definition.key} contains non-adjacent rooms: {origin} -> {destination}"
                        )

            if definition.aggro_radius != 0:
                raise ValueError(
                    f"{definition.key} uses unsupported passive cross-room aggro radius {definition.aggro_radius}; "
                    "hostile NPCs currently acquire targets only in the same room"
                )
            if not 0.0 <= definition.pursuit_chance_after_flee <= 1.0:
                raise ValueError(f"Invalid pursuit chance for {definition.key}")
            if definition.aggressive and (definition.max_hp <= 0 or definition.auto_attack_damage < 0):
                raise ValueError(f"Aggressive NPC {definition.key} requires valid combat stats")

            if definition.weather_shelter_room_key is not None:
                if definition.weather_shelter_room_key not in allowed:
                    raise ValueError(
                        f"Weather shelter leaves boundary for {definition.key}: "
                        f"{definition.weather_shelter_room_key}"
                    )
                if self._shortest_path(
                    definition.spawn_room_key,
                    definition.weather_shelter_room_key,
                    allowed,
                ) is None:
                    raise ValueError(
                        f"Weather shelter is unreachable for {definition.key}: "
                        f"{definition.weather_shelter_room_key}"
                    )

            if definition.behavior == BEHAVIOR_ROUTINE:
                if not definition.routine_schedule:
                    raise ValueError(f"Routine NPC {definition.key} requires a schedule")
                for stop in definition.routine_schedule:
                    if not 0 <= stop.start_hour <= 23:
                        raise ValueError(f"Invalid routine hour for {definition.key}: {stop.start_hour}")
                    if stop.room_key not in allowed:
                        raise ValueError(f"Routine stop leaves boundary for {definition.key}: {stop.room_key}")
                if len({stop.start_hour for stop in definition.routine_schedule}) != len(definition.routine_schedule):
                    raise ValueError(f"Routine NPC {definition.key} has duplicate schedule hours")
                # Every scheduled destination must be reachable through allowed rooms.
                for stop in definition.routine_schedule:
                    if self._shortest_path(definition.spawn_room_key, stop.room_key, allowed) is None:
                        raise ValueError(f"Routine stop is unreachable for {definition.key}: {stop.room_key}")

    @staticmethod
    def _room_allows_regional_spawns(room) -> bool:
        tags = tuple(str(tag).lower() for tag in getattr(room, "tags", ()))
        if any(
            blocked in tag
            for tag in tags
            for blocked in _REGIONAL_BLOCKED_TAG_TOKENS
        ):
            return False
        return True

    @staticmethod
    def _room_looks_like_hunting_ground(room) -> bool:
        tags = tuple(str(tag).lower() for tag in getattr(room, "tags", ()))
        return any(
            token in tag
            for tag in tags
            for token in _REGIONAL_WILD_TAG_TOKENS
        )

    def _regional_source_is_eligible(self, room, enemy) -> bool:
        if bool(getattr(enemy, "tutorial", False)):
            return False
        if not bool(getattr(enemy, "retaliates", True)):
            return False
        xp = int(getattr(enemy, "xp_reward", 0) or 0)
        # Elite/boss encounters stay authored and predictable. The regional
        # layer is for ordinary huntable wildlife and field threats.
        if xp <= 0 or xp >= 100:
            return False
        if not self._room_allows_regional_spawns(room):
            return False
        return self._room_looks_like_hunting_ground(room)

    def _regional_habitat(
        self,
        region_key: str,
        source_room_keys: tuple[str, ...],
    ) -> tuple[str, ...]:
        queue: deque[tuple[str, int]] = deque()
        visited: set[str] = set()
        for source_key in source_room_keys:
            room = ROOMS_BY_KEY.get(source_key)
            if (
                room is None
                or room.region_key != region_key
                or not self._room_allows_regional_spawns(room)
            ):
                continue
            visited.add(source_key)
            queue.append((source_key, 0))

        while queue:
            room_key, depth = queue.popleft()
            if depth >= REGIONAL_HABITAT_DEPTH:
                continue
            room = ROOMS_BY_KEY.get(room_key)
            if room is None:
                continue
            for destination in room.exits.values():
                if destination in visited:
                    continue
                next_room = ROOMS_BY_KEY.get(destination)
                if (
                    next_room is None
                    or next_room.region_key != region_key
                    or not self._room_allows_regional_spawns(next_room)
                ):
                    continue
                visited.add(destination)
                queue.append((destination, depth + 1))
        return tuple(sorted(visited))

    def _build_regional_spawn_definitions(self) -> dict[str, RegionalSpawnDefinition]:
        sources: dict[tuple[str, str], set[str]] = {}
        for room in ROOMS_BY_KEY.values():
            for enemy_key in getattr(room, "enemy_keys", ()):
                enemy = combat.ENEMIES_BY_KEY.get(enemy_key)
                if enemy is None or not self._regional_source_is_eligible(room, enemy):
                    continue
                sources.setdefault((room.region_key, enemy_key), set()).add(room.key)

        pools: dict[str, RegionalSpawnDefinition] = {}
        for (region_key, enemy_key), source_keys in sorted(sources.items()):
            source_tuple = tuple(sorted(source_keys))
            habitat = self._regional_habitat(region_key, source_tuple)
            # A one-room encounter stays static. Regional populations only exist
            # when the creature has somewhere real to roam.
            if len(habitat) < 2:
                continue
            pool_key = f"{region_key}:{enemy_key}"
            pools[pool_key] = RegionalSpawnDefinition(
                key=pool_key,
                region_key=region_key,
                enemy_key=enemy_key,
                room_keys=habitat,
                source_room_keys=source_tuple,
            )
        return pools

    def _regional_states(
        self,
        pool_key: str,
        *,
        include_rare: bool = True,
    ) -> list[MobileNpcState]:
        result: list[MobileNpcState] = []
        for instance_key, mapped_pool in tuple(self._regional_instance_to_pool.items()):
            if mapped_pool != pool_key:
                continue
            state = self.states.get(instance_key)
            if state is None or not state.active:
                continue
            if not include_rare and bool(getattr(state.definition, "rare", False)):
                continue
            result.append(state)
        return result

    def _region_dynamic_cap(self, region_key: str) -> int:
        habitat_rooms = {
            room_key
            for pool in self.regional_pools.values()
            if pool.region_key == region_key
            for room_key in pool.room_keys
        }
        # Roughly two mobile threats per useful habitat room, with hard global
        # bounds so dense authored regions never turn into a CPU or combat flood.
        return max(6, min(24, len(habitat_rooms) * 2))

    def target_population(
        self,
        pool: RegionalSpawnDefinition,
        player_room_keys: Iterable[str] = (),
    ) -> int:
        player_count = 0
        for room_key in player_room_keys:
            room = ROOMS_BY_KEY.get(room_key)
            if room is not None and room.region_key == pool.region_key:
                player_count += 1
        return min(pool.max_population, pool.base_population + player_count)

    def _regional_definition(
        self,
        pool: RegionalSpawnDefinition,
        instance_key: str,
        spawn_room_key: str,
        *,
        rare: bool,
        rng: random.Random,
    ) -> MobileNpcDefinition | None:
        base = combat.ENEMIES_BY_KEY.get(pool.enemy_key)
        if base is None:
            return None

        if rare:
            name = f"Ravenous {base.name}"
            aliases = tuple(
                dict.fromkeys(
                    (
                        f"ravenous {base.name.lower()}",
                        *(f"ravenous {alias}" for alias in base.aliases),
                    )
                )
            )
            return MobileNpcDefinition(
                key=instance_key,
                name=name,
                short_description=(
                    f"{base.description}, visibly larger and more dangerous than the ordinary kind"
                ),
                spawn_room_key=spawn_room_key,
                allowed_room_keys=pool.room_keys,
                behavior=BEHAVIOR_HUNTER,
                move_chance_per_tick=0.18,
                aliases=aliases,
                aggressive=True,
                pursuit_chance_after_flee=0.75,
                max_hp=max(base.max_hp + 1, int(base.max_hp * 1.75)),
                armor_class=base.armor_class + 2,
                auto_attack_damage=base.auto_attack_damage + max(1, base.auto_attack_damage // 2),
                auto_attack_interval=max(1.0, base.auto_attack_interval * 0.9),
                xp_reward=max(base.xp_reward + 1, base.xp_reward * 2),
                attackable=True,
                combat_enemy_key=base.key,
                rare=True,
            )

        return MobileNpcDefinition(
            key=instance_key,
            name=base.name,
            short_description=base.description,
            spawn_room_key=spawn_room_key,
            allowed_room_keys=pool.room_keys,
            behavior=BEHAVIOR_WANDER,
            # Five-second ticks put ordinary movement in roughly the requested
            # 30-90 second cadence without every creature moving in lockstep.
            move_chance_per_tick=rng.uniform(0.06, 0.16),
            aliases=tuple(base.aliases),
            aggressive=False,
            pursuit_chance_after_flee=0.30,
            max_hp=base.max_hp,
            armor_class=base.armor_class,
            auto_attack_damage=base.auto_attack_damage,
            auto_attack_interval=base.auto_attack_interval,
            xp_reward=base.xp_reward,
            attackable=True,
            combat_enemy_key=base.key,
            rare=False,
        )

    def awaken_weather_rare(
        self,
        region_key: str,
        *,
        player_room_keys: Iterable[str] = (),
        rng: random.Random | None = None,
    ) -> MobileNpcState | None:
        """Spawn at most one hidden regional rare in response to a weather event."""

        rng = rng or random.Random()
        active_rare = any(
            state.active
            and state.definition.rare
            and ROOMS_BY_KEY.get(state.current_room_key) is not None
            and ROOMS_BY_KEY[state.current_room_key].region_key == region_key
            for state in self.states.values()
        )
        if active_rare:
            return None

        regional_states = [
            state
            for state in self.states.values()
            if state.active
            and ROOMS_BY_KEY.get(state.current_room_key) is not None
            and ROOMS_BY_KEY[state.current_room_key].region_key == region_key
        ]
        if len(regional_states) >= self._region_dynamic_cap(region_key):
            return None

        pools = [pool for pool in self.regional_pools.values() if pool.region_key == region_key]
        rng.shuffle(pools)
        for pool in pools:
            state = self._spawn_regional_instance(
                pool,
                player_room_keys=player_room_keys,
                rng=rng,
                rare=True,
            )
            if state is not None:
                return state
        return None

    def _choose_regional_spawn_room(
        self,
        pool: RegionalSpawnDefinition,
        player_room_keys: Iterable[str],
        rng: random.Random,
    ) -> str | None:
        player_rooms = set(player_room_keys)
        hidden = [room_key for room_key in pool.room_keys if room_key not in player_rooms]
        if not hidden:
            return None

        counts: dict[str, int] = {room_key: 0 for room_key in hidden}
        for state in self._regional_states(pool.key):
            if state.current_room_key in counts:
                counts[state.current_room_key] += 1

        below_soft_cap = [
            room_key
            for room_key in hidden
            if counts[room_key] < REGIONAL_MAX_DYNAMIC_PER_ROOM
        ]
        candidates = below_soft_cap or hidden
        lowest = min(counts[room_key] for room_key in candidates)
        least_crowded = [room_key for room_key in candidates if counts[room_key] == lowest]
        return rng.choice(least_crowded)

    def _spawn_regional_instance(
        self,
        pool: RegionalSpawnDefinition,
        *,
        player_room_keys: Iterable[str],
        rng: random.Random,
        rare: bool = False,
    ) -> MobileNpcState | None:
        spawn_room = self._choose_regional_spawn_room(pool, player_room_keys, rng)
        if spawn_room is None:
            return None
        self._regional_serial += 1
        suffix = "rare" if rare else "common"
        instance_key = f"regional::{pool.region_key}::{pool.enemy_key}::{suffix}::{self._regional_serial}"
        definition = self._regional_definition(
            pool,
            instance_key,
            spawn_room,
            rare=rare,
            rng=rng,
        )
        if definition is None:
            return None
        state = MobileNpcState(definition=definition, current_room_key=spawn_room)
        self.states[instance_key] = state
        self._regional_instance_to_pool[instance_key] = pool.key
        if rare:
            self._rare_expiry_tick[instance_key] = self._tick_index + REGIONAL_RARE_TTL_TICKS
        return state

    def _seed_regional_population(self) -> None:
        if not self.regional_pools:
            return
        rng = random.Random(0xA57A115)
        by_region: dict[str, list[RegionalSpawnDefinition]] = {}
        for pool in self.regional_pools.values():
            by_region.setdefault(pool.region_key, []).append(pool)

        for region_key, pools in sorted(by_region.items()):
            cap = self._region_dynamic_cap(region_key)
            created = 0
            # Round-robin seeding prevents the first species alphabetically from
            # consuming an entire small-region cap.
            for _round in range(REGIONAL_BASE_POPULATION):
                for pool in sorted(pools, key=lambda value: value.key):
                    if created >= cap:
                        break
                    if self._spawn_regional_instance(
                        pool,
                        player_room_keys=(),
                        rng=rng,
                    ) is not None:
                        created += 1
                if created >= cap:
                    break

    def _despawn_regional_instance(self, instance_key: str) -> None:
        self.states.pop(instance_key, None)
        self._regional_instance_to_pool.pop(instance_key, None)
        self._rare_expiry_tick.pop(instance_key, None)

    def _reconcile_regional_populations(
        self,
        player_room_keys: Iterable[str],
        rng: random.Random,
    ) -> None:
        player_rooms = tuple(player_room_keys)
        occupied = set(player_rooms)

        # Rares leave after a while, but never vanish while someone is fighting
        # or visibly standing beside them.
        for instance_key, expiry_tick in tuple(self._rare_expiry_tick.items()):
            if self._tick_index < expiry_tick:
                continue
            state = self.states.get(instance_key)
            if state is None:
                self._despawn_regional_instance(instance_key)
                continue
            if state.engaged_character_id is not None or state.current_room_key in occupied:
                self._rare_expiry_tick[instance_key] = self._tick_index + 12
                continue
            self._despawn_regional_instance(instance_key)

        player_counts: dict[str, int] = {}
        for room_key in player_rooms:
            room = ROOMS_BY_KEY.get(room_key)
            if room is not None:
                player_counts[room.region_key] = player_counts.get(room.region_key, 0) + 1

        for pool in sorted(self.regional_pools.values(), key=lambda value: value.key):
            common_states = self._regional_states(pool.key, include_rare=False)
            target = min(
                pool.max_population,
                pool.base_population + player_counts.get(pool.region_key, 0),
            )

            if len(common_states) > target:
                removable = [
                    state
                    for state in common_states
                    if state.engaged_character_id is None
                    and state.current_room_key not in occupied
                ]
                if removable:
                    self._despawn_regional_instance(removable[-1].definition.key)
                continue

            if len(common_states) >= target:
                continue
            if self._tick_index < self._regional_next_spawn_tick.get(pool.key, 0):
                continue

            region_states = [
                self.states[instance_key]
                for instance_key, mapped_pool in self._regional_instance_to_pool.items()
                if instance_key in self.states
                and self.regional_pools.get(mapped_pool) is not None
                and self.regional_pools[mapped_pool].region_key == pool.region_key
                and self.states[instance_key].active
            ]
            if len(region_states) >= self._region_dynamic_cap(pool.region_key):
                continue

            if self._spawn_regional_instance(
                pool,
                player_room_keys=player_rooms,
                rng=rng,
            ) is not None:
                self._regional_next_spawn_tick[pool.key] = self._tick_index + REGIONAL_REFILL_TICKS

        # Occasional tougher visitors are generated only in regions that contain
        # active players, capped at one rare at a time per region.
        for region_key, player_count in sorted(player_counts.items()):
            if player_count <= 0:
                continue
            if any(
                state.definition.rare
                and self.regional_pools.get(self._regional_instance_to_pool.get(state.definition.key, ""))
                and self.regional_pools[self._regional_instance_to_pool[state.definition.key]].region_key == region_key
                for state in self.states.values()
                if state.active
            ):
                continue
            if rng.random() > REGIONAL_RARE_ROLL_PER_TICK:
                continue
            region_pools = [
                pool for pool in self.regional_pools.values()
                if pool.region_key == region_key
            ]
            if not region_pools:
                continue
            current_region_population = sum(
                1
                for state in self.states.values()
                if state.active
                and (
                    pool_key := self._regional_instance_to_pool.get(state.definition.key)
                ) is not None
                and self.regional_pools.get(pool_key) is not None
                and self.regional_pools[pool_key].region_key == region_key
            )
            if current_region_population >= self._region_dynamic_cap(region_key):
                continue
            self._spawn_regional_instance(
                rng.choice(region_pools),
                player_room_keys=player_rooms,
                rng=rng,
                rare=True,
            )

    def npcs_in_room(self, room_key: str) -> tuple[MobileNpcState, ...]:
        return tuple(
            state for state in self.states.values()
            if state.active and state.current_room_key == room_key
        )

    def aggressive_npcs_in_room(self, room_key: str) -> tuple[MobileNpcState, ...]:
        """Return unengaged hostile NPCs physically sharing the room.

        Aggro acquisition is intentionally same-room only. No mobile NPC scans
        neighboring rooms for unsuspecting players.
        """
        return tuple(
            state for state in self.npcs_in_room(room_key)
            if state.definition.aggressive and state.engaged_character_id is None
        )

    def engage(self, npc_key: str, character_id: int) -> bool:
        state = self.states.get(npc_key)
        if state is None or not state.active:
            return False
        if state.engaged_character_id not in {None, character_id}:
            return False
        state.engaged_character_id = character_id
        state.returning_to_duty = False
        return True

    def disengage(self, npc_key: str, character_id: int | None = None) -> None:
        state = self.states.get(npc_key)
        if state is None:
            return
        if character_id is not None and state.engaged_character_id not in {None, character_id}:
            return
        state.engaged_character_id = None
        if npc_key in self._regional_instance_to_pool:
            # Regional wildlife resumes wandering from wherever the encounter
            # ended instead of pathing back to an arbitrary "home" room.
            state.returning_to_duty = False
        else:
            state.returning_to_duty = state.active and state.current_room_key != state.definition.spawn_room_key

    def defeat(self, npc_key: str, respawn_ticks: int = 6) -> None:
        """Remove a regional kill from its shared pool or respawn authored mobiles."""
        state = self.states.get(npc_key)
        if state is None:
            return

        pool_key = self._regional_instance_to_pool.get(npc_key)
        if pool_key is not None:
            # The population manager, not this instance, owns replacement. This
            # makes a kill reduce the real regional count and guarantees refill
            # observes its cooldown and out-of-sight placement rules.
            self._despawn_regional_instance(npc_key)
            self._regional_next_spawn_tick[pool_key] = max(
                self._regional_next_spawn_tick.get(pool_key, 0),
                self._tick_index + REGIONAL_REFILL_TICKS,
            )
            return

        state.engaged_character_id = None
        state.returning_to_duty = False
        state.inactive_ticks = max(1, respawn_ticks)

    def attempt_pursuit_after_flee(
        self,
        npc_key: str,
        character_id: int,
        destination_room_key: str,
        rng: random.Random | None = None,
    ) -> NpcMovement | None:
        """Let an already-engaged NPC try to follow a fleeing target.

        The destination must be adjacent and inside the NPC's explicit habitat.
        Boundaries always override pursuit chance.
        """
        rng = rng or random.Random()
        state = self.states.get(npc_key)
        if state is None or not state.active or state.engaged_character_id != character_id:
            return None

        definition = state.definition
        if destination_room_key not in definition.allowed_room_keys:
            self.disengage(npc_key, character_id)
            return None

        direction = self._direction_to(state.current_room_key, destination_room_key)
        if direction is None:
            self.disengage(npc_key, character_id)
            return None

        if rng.random() > definition.pursuit_chance_after_flee:
            self.disengage(npc_key, character_id)
            return None

        origin = state.current_room_key
        state.current_room_key = destination_room_key
        return NpcMovement(
            npc_key=definition.key,
            npc_name=definition.name,
            origin_room_key=origin,
            destination_room_key=destination_room_key,
            direction=direction,
            behavior=definition.behavior,
            reason="pursuit",
        )

    def _legal_moves(self, state: MobileNpcState) -> list[tuple[str, str]]:
        room = ROOMS_BY_KEY[state.current_room_key]
        allowed = set(state.definition.allowed_room_keys)
        legal = [
            (direction, destination)
            for direction, destination in room.exits.items()
            if destination in allowed
        ]
        if state.definition.key not in self._regional_instance_to_pool:
            return legal

        canonical_key = state.definition.combat_enemy_key
        if canonical_key is None:
            return legal
        occupied_by_same_species = {
            other.current_room_key
            for other in self.states.values()
            if other is not state
            and other.active
            and other.definition.combat_enemy_key == canonical_key
        }
        uncrowded = [
            move for move in legal
            if move[1] not in occupied_by_same_species
        ]
        return uncrowded or legal

    @staticmethod
    def _shortest_path(origin: str, destination: str, allowed: set[str]) -> list[str] | None:
        if origin == destination:
            return [origin]
        if origin not in allowed or destination not in allowed:
            return None
        queue: deque[tuple[str, list[str]]] = deque([(origin, [origin])])
        visited = {origin}
        while queue:
            room_key, path = queue.popleft()
            for next_room in ROOMS_BY_KEY[room_key].exits.values():
                if next_room not in allowed or next_room in visited:
                    continue
                next_path = path + [next_room]
                if next_room == destination:
                    return next_path
                visited.add(next_room)
                queue.append((next_room, next_path))
        return None

    def _direction_to(self, origin: str, destination: str) -> str | None:
        for direction, room_key in ROOMS_BY_KEY[origin].exits.items():
            if room_key == destination:
                return direction
        return None

    def _choose_patrol_move(self, state: MobileNpcState) -> tuple[str, str, str] | None:
        route = state.definition.patrol_route
        if not route:
            return None

        # If state was moved externally in a test/admin tool, resynchronize to a
        # matching route occurrence whose next leg is legal.
        if route[state.patrol_index % len(route)] != state.current_room_key:
            matching = [i for i, room_key in enumerate(route) if room_key == state.current_room_key]
            if not matching:
                return None
            state.patrol_index = matching[0]

        next_index = (state.patrol_index + 1) % len(route)
        destination = route[next_index]
        direction = self._direction_to(state.current_room_key, destination)
        if direction is None:
            return None
        state.patrol_index = next_index
        return direction, destination, "patrol"

    def _choose_hunter_move(
        self,
        state: MobileNpcState,
        rng: random.Random,
    ) -> tuple[str, str, str] | None:
        # Unengaged hunters do not passively detect players in other rooms.
        # They simply prowl their authored habitat until same-room aggro occurs.
        legal = self._legal_moves(state)
        if not legal:
            return None
        direction, destination = rng.choice(legal)
        return direction, destination, "prowling"

    def _choose_return_move(self, state: MobileNpcState, hour: int) -> tuple[str, str, str] | None:
        definition = state.definition
        allowed = set(definition.allowed_room_keys)
        if definition.behavior == BEHAVIOR_ROUTINE and definition.routine_schedule:
            destination_room = self._routine_destination(definition, hour)
        else:
            destination_room = definition.spawn_room_key

        path = self._shortest_path(state.current_room_key, destination_room, allowed)
        if path is None or len(path) < 2:
            state.returning_to_duty = False
            return None
        destination = path[1]
        direction = self._direction_to(state.current_room_key, destination)
        if direction is None:
            state.returning_to_duty = False
            return None
        return direction, destination, "returning"

    def _routine_destination(self, definition: MobileNpcDefinition, hour: int) -> str:
        schedule = sorted(definition.routine_schedule, key=lambda stop: stop.start_hour)
        eligible = [stop for stop in schedule if stop.start_hour <= hour]
        if eligible:
            return eligible[-1].room_key
        return schedule[-1].room_key

    def _choose_routine_move(self, state: MobileNpcState, hour: int) -> tuple[str, str, str] | None:
        allowed = set(state.definition.allowed_room_keys)
        desired_room = self._routine_destination(state.definition, hour)
        path = self._shortest_path(state.current_room_key, desired_room, allowed)
        if path is None or len(path) < 2:
            return None
        destination = path[1]
        direction = self._direction_to(state.current_room_key, destination)
        if direction is None:
            return None
        return direction, destination, "schedule"

    def _choose_weather_shelter_move(self, state: MobileNpcState) -> tuple[str, str, str] | None:
        shelter = state.definition.weather_shelter_room_key
        if shelter is None or shelter == state.current_room_key:
            return None
        path = self._shortest_path(
            state.current_room_key,
            shelter,
            set(state.definition.allowed_room_keys),
        )
        if path is None or len(path) < 2:
            return None
        destination = path[1]
        direction = self._direction_to(state.current_room_key, destination)
        if direction is None:
            return None
        return direction, destination, "sheltering"

    def tick(
        self,
        rng: random.Random | None = None,
        *,
        player_room_keys: Iterable[str] = (),
        hour: int | None = None,
        weather_provider: WeatherProvider | None = None,
    ) -> tuple[NpcMovement, ...]:
        rng = rng or random.Random()
        player_rooms = tuple(player_room_keys)
        current_hour = datetime.now().hour if hour is None else hour % 24
        movements: list[NpcMovement] = []
        self._tick_index += 1
        self._reconcile_regional_populations(player_rooms, rng)

        for state in tuple(self.states.values()):
            definition = state.definition

            if state.inactive_ticks > 0:
                state.inactive_ticks -= 1
                if state.inactive_ticks == 0:
                    state.current_room_key = definition.spawn_room_key
                    state.patrol_index = 0
                    state.returning_to_duty = False
                continue

            # NPCs engaged in combat are controlled by combat/flee logic and do
            # not wander away mid-fight.
            if state.engaged_character_id is not None:
                continue

            current_room = ROOMS_BY_KEY.get(state.current_room_key)
            region_key = current_room.region_key if current_room is not None else ""
            current_weather = (
                weather_provider(region_key)
                if weather_provider is not None and region_key
                else "clear"
            )
            seeking_shelter = (
                definition.weather_shelter_room_key is not None
                and current_weather in definition.shelter_weathers
            )

            # Severe weather overrides an ordinary patrol or routine. NPCs with
            # authored shelter hurry toward it and remain there until conditions
            # ease, then resume their normal schedule automatically.
            if seeking_shelter:
                if state.current_room_key == definition.weather_shelter_room_key:
                    continue
                if rng.random() > max(0.75, definition.move_chance_per_tick):
                    continue
                selected = self._choose_weather_shelter_move(state)
            else:
                # Routine NPCs should promptly travel toward their scheduled room;
                # their move chance still allows designers to slow that travel down.
                if rng.random() > definition.move_chance_per_tick:
                    continue
                selected: tuple[str, str, str] | None
                if state.returning_to_duty:
                    selected = self._choose_return_move(state, current_hour)
                elif definition.behavior == BEHAVIOR_PATROL:
                    selected = self._choose_patrol_move(state)
                elif definition.behavior == BEHAVIOR_HUNTER:
                    selected = self._choose_hunter_move(state, rng)
                elif definition.behavior == BEHAVIOR_ROUTINE:
                    selected = self._choose_routine_move(state, current_hour)
                else:
                    legal = self._legal_moves(state)
                    if legal:
                        direction, destination = rng.choice(legal)
                        selected = direction, destination, "roaming"
                    else:
                        selected = None

            if selected is None:
                continue

            direction, destination, reason = selected
            # Final safety gate: behavior code can never bypass the boundary.
            if destination not in definition.allowed_room_keys:
                continue

            origin = state.current_room_key
            state.current_room_key = destination
            movements.append(
                NpcMovement(
                    npc_key=definition.key,
                    npc_name=definition.name,
                    origin_room_key=origin,
                    destination_room_key=destination,
                    direction=direction,
                    behavior=definition.behavior,
                    reason=reason,
                )
            )

        return tuple(movements)

    async def run(
        self,
        on_movement: MovementCallback,
        tick_seconds: float = NPC_TICK_SECONDS,
        player_rooms_provider: PlayerRoomsProvider | None = None,
        hour_provider: HourProvider | None = None,
        weather_provider: WeatherProvider | None = None,
    ) -> None:
        while True:
            await asyncio.sleep(tick_seconds)
            player_rooms = tuple(player_rooms_provider()) if player_rooms_provider is not None else ()
            hour = hour_provider() if hour_provider is not None else datetime.now().hour
            for movement in self.tick(
                player_room_keys=player_rooms,
                hour=hour,
                weather_provider=weather_provider,
            ):
                await on_movement(movement)
