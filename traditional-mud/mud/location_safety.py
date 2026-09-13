from __future__ import annotations

from collections import deque
from typing import Mapping

import mud.world as legacy_world
from mud.starter_race_loops import STARTER_RACE_LOOPS, starting_room_for_race


DEFAULT_STARTER_WALK_DEPTH = 4


def live_rooms_for_world(world_service) -> dict[str, object]:
    """Return the complete authored room registry used by the live server.

    Dreams of the Fallen still has two compatible registration paths while the
    world is being migrated: older content writes to mud.world.ROOMS_BY_KEY,
    while newer runtime layers also populate the room service's legacy_rooms.
    Neither mapping is guaranteed to be complete on its own, so safety checks and
    stale-location repair must use their union. Runtime-service definitions win
    when both registries intentionally replace the same room key.
    """

    rooms: dict[str, object] = dict(legacy_world.ROOMS_BY_KEY)
    rooms.update(getattr(world_service, "legacy_rooms", {}) or {})
    return rooms


def validate_authored_exit_targets(rooms_by_key: Mapping[str, object]) -> None:
    """Fail fast when an advertised exit points at a room that does not exist.

    This is intentionally global rather than race-specific. The bug that trapped
    a Goblin character was not really a Goblin rule problem; it was a world-graph
    integrity problem. If LOOK/EXITS advertises a direction, the live world must
    contain the destination before the server is allowed to start.
    """

    problems: list[str] = []
    for room_key, room in rooms_by_key.items():
        exits = getattr(room, "exits", None) or {}
        for direction, destination_key in exits.items():
            if destination_key not in rooms_by_key:
                problems.append(
                    f"{room_key} advertises {direction} -> missing room {destination_key}"
                )

    if problems:
        raise RuntimeError(
            "Authored room-exit contract failed:\n- " + "\n- ".join(sorted(problems))
        )


def validate_starter_route_walks(
    rooms_by_key: Mapping[str, object],
    *,
    walk_depth: int = DEFAULT_STARTER_WALK_DEPTH,
) -> None:
    """Walk outward from every racial start and verify the early room graph.

    The traversal is deliberately bounded: starter experiences are allowed to
    branch into the wider world, but the first few physical moves from every one
    of the eight starts must remain authored and traversable. Global exit-target
    validation still protects later rooms everywhere else in Astralis.
    """

    problems: list[str] = []
    required_depth = max(1, walk_depth)

    for loop in STARTER_RACE_LOOPS:
        start_key = loop.starting_room_key
        if start_key not in rooms_by_key:
            problems.append(f"{loop.race_key}: missing start room {start_key}")
            continue

        queue = deque([(start_key, 0)])
        visited = {start_key}
        furthest = 0

        while queue:
            room_key, depth = queue.popleft()
            furthest = max(furthest, depth)
            if depth >= required_depth:
                continue

            room = rooms_by_key[room_key]
            exits = getattr(room, "exits", None) or {}
            for direction, destination_key in exits.items():
                if destination_key not in rooms_by_key:
                    problems.append(
                        f"{loop.race_key}: {room_key} {direction} -> missing room {destination_key}"
                    )
                    continue
                if destination_key not in visited:
                    visited.add(destination_key)
                    queue.append((destination_key, depth + 1))

        # A starter room may branch or loop, so requiring one real move is the
        # correct universal promise. Deeper authored routes are still traversed
        # when they exist, up to the bounded validation depth above.
        if furthest < 1:
            problems.append(f"{loop.race_key}: starter room {start_key} cannot reach another room")

    if problems:
        raise RuntimeError(
            "Starter route-walk contract failed:\n- " + "\n- ".join(sorted(problems))
        )


def repair_invalid_character_location(session, rooms_by_key: Mapping[str, object]) -> bool:
    """Return a character with stale room data to their own racial start.

    Valid travel is never disturbed. We only repair a current room or bind point
    when its saved key is absent from the live authored world. This covers old
    development room names, deleted rooms, region keys accidentally stored as
    room keys, and blank locations for every launch race rather than just Goblins.
    """

    character = getattr(session, "character", None)
    if character is None:
        return False

    fallback = starting_room_for_race(character.race)
    if fallback is None or fallback not in rooms_by_key:
        return False

    changed = False
    if character.current_room not in rooms_by_key:
        session.database.set_character_room(character.id, fallback)
        changed = True
    if character.bind_room not in rooms_by_key:
        session.database.set_bind_room(character.id, fallback)
        changed = True

    if changed:
        refreshed = session.database.get_character_by_name(character.name)
        if refreshed is not None:
            session.character = refreshed
    return changed


def install_universal_location_repair_runtime(player_session_class, world_service) -> None:
    """Install the outermost login guard against stale/deleted room locations."""

    if getattr(player_session_class, "_universal_location_repair_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character

    async def enter_character(self) -> None:
        repaired = repair_invalid_character_location(
            self, live_rooms_for_world(world_service)
        )
        await previous_enter_character(self)
        if repaired and self.character is not None:
            await self.send(
                "\r\nYour saved location no longer exists in the current world. "
                "You have been returned safely to your racial starting area.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class._universal_location_repair_runtime_installed = True
