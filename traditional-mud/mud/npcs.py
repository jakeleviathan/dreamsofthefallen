from __future__ import annotations

import asyncio
import random
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Iterable

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

    @property
    def movement_pattern(self) -> str:
        """Compatibility alias for older code/tests that used movement_pattern."""
        return "random" if self.behavior == BEHAVIOR_WANDER else self.behavior


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
        self.reset()
        self.validate_definitions()

    def reset(self) -> None:
        self.states = {}
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
        state.returning_to_duty = state.active and state.current_room_key != state.definition.spawn_room_key

    def defeat(self, npc_key: str, respawn_ticks: int = 6) -> None:
        """Temporarily remove a defeated mobile NPC, then respawn it at home."""
        state = self.states.get(npc_key)
        if state is None:
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
        return [
            (direction, destination)
            for direction, destination in room.exits.items()
            if destination in allowed
        ]

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

    def tick(
        self,
        rng: random.Random | None = None,
        *,
        player_room_keys: Iterable[str] = (),
        hour: int | None = None,
    ) -> tuple[NpcMovement, ...]:
        rng = rng or random.Random()
        player_rooms = tuple(player_room_keys)
        current_hour = datetime.now().hour if hour is None else hour % 24
        movements: list[NpcMovement] = []

        for state in self.states.values():
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
    ) -> None:
        while True:
            await asyncio.sleep(tick_seconds)
            player_rooms = tuple(player_rooms_provider()) if player_rooms_provider is not None else ()
            hour = hour_provider() if hour_provider is not None else datetime.now().hour
            for movement in self.tick(player_room_keys=player_rooms, hour=hour):
                await on_movement(movement)
