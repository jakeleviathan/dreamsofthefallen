from __future__ import annotations

from collections import deque
import zlib

from mud.room_engine import PlayerRoomContext


DEFAULT_MAP_RADIUS = 3
MAX_MAP_RADIUS = 4

_DIRECTION_DELTAS: dict[str, tuple[int, int, int]] = {
    "north": (0, 1, 0),
    "south": (0, -1, 0),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "northeast": (1, 1, 0),
    "northwest": (-1, 1, 0),
    "southeast": (1, -1, 0),
    "southwest": (-1, -1, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
}


def stable_map_room_number(room_key: str) -> int:
    """Use the same stable positive mapper id as the structured client layer."""

    return (zlib.crc32(room_key.encode("utf-8")) & 0x7FFFFFFF) + 1


def _ensure_schema(database) -> None:
    if getattr(database, "_exploration_map_schema_ready", False):
        return
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_discovered_rooms (
                character_id INTEGER NOT NULL,
                room_key TEXT NOT NULL,
                first_visited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, room_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_character_discovered_rooms_character "
            "ON character_discovered_rooms(character_id)"
        )
    database._exploration_map_schema_ready = True


def _discovery_cache(session) -> set[str]:
    cached = getattr(session, "_discovered_room_keys", None)
    if cached is not None:
        return cached

    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        cached = set()
    else:
        _ensure_schema(database)
        with database.connect() as db:
            rows = db.execute(
                "SELECT room_key FROM character_discovered_rooms WHERE character_id = ?",
                (character.id,),
            ).fetchall()
        cached = {str(row["room_key"]) for row in rows}
    session._discovered_room_keys = cached
    return cached


def note_room_visited(session, room_key: str | None = None) -> bool:
    """Persist one room as personally discovered by this character.

    Discovery is intentionally character-specific. A new character does not inherit
    another character's map, and merely having an exit visible does not reveal its
    destination on the discovered map until the character actually enters it.
    """

    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return False
    key = str(room_key or character.current_room or "").strip()
    if not key:
        return False

    cache = _discovery_cache(session)
    if key in cache:
        return False

    _ensure_schema(database)
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO character_discovered_rooms (character_id, room_key) VALUES (?, ?)",
            (character.id, key),
        )
    cache.add(key)
    return True


def discovered_room_keys(session) -> frozenset[str]:
    return frozenset(_discovery_cache(session))


def _context(session, world_service, room_key: str) -> PlayerRoomContext:
    character = session.character
    scene = world_service.scene(room_key)
    weather = "clear"
    if scene is not None:
        weather = world_service.state.weather_for(scene.region_key)
    return PlayerRoomContext(
        character_id=int(character.id),
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=int(character.level),
        character_flags=frozenset(session.database.list_flags(character.id)),
        hour=int(getattr(session, "astralis_hour", 12)),
        weather=weather,
    )


def _visible_exits(session, world_service, room_key: str):
    try:
        view = world_service.build_view(room_key, _context(session, world_service, room_key))
    except Exception:
        return ()
    return tuple(view.exits) if view is not None else ()


def build_discovered_map_snapshot(session, world_service, radius: int = DEFAULT_MAP_RADIUS) -> dict:
    """Return a local graph containing only rooms this character has entered."""

    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return {"radius": int(radius), "current": 0, "rooms": []}

    note_room_visited(session, character.current_room)
    visited = discovered_room_keys(session)
    current_key = str(character.current_room)
    radius = max(1, min(MAX_MAP_RADIUS, int(radius)))

    distances: dict[str, int] = {current_key: 0}
    queue: deque[str] = deque((current_key,))
    while queue:
        room_key = queue.popleft()
        depth = distances[room_key]
        if depth >= radius:
            continue
        for visible in _visible_exits(session, world_service, room_key):
            destination = str(visible.destination_key)
            if destination not in visited or destination in distances:
                continue
            distances[destination] = depth + 1
            queue.append(destination)

    rooms: list[dict] = []
    included = set(distances)
    for room_key, distance in sorted(distances.items(), key=lambda item: (item[1], item[0])):
        scene = world_service.scene(room_key)
        try:
            view = world_service.build_view(room_key, _context(session, world_service, room_key))
        except Exception:
            view = None
        if scene is None or view is None:
            continue
        exits = {
            str(visible.direction).lower(): stable_map_room_number(str(visible.destination_key))
            for visible in view.exits
            if str(visible.destination_key) in included
        }
        exit_keys = {
            str(visible.direction).lower(): str(visible.destination_key)
            for visible in view.exits
            if str(visible.destination_key) in included
        }
        rooms.append(
            {
                "key": room_key,
                "num": stable_map_room_number(room_key),
                "name": view.name,
                "zone": scene.region_key,
                "distance": distance,
                "current": room_key == current_key,
                "exits": exits,
                "exit_keys": exit_keys,
            }
        )

    return {
        "radius": radius,
        "current": stable_map_room_number(current_key),
        "current_key": current_key,
        "discovered_count": len(visited),
        "rooms": rooms,
    }


def _coordinate_rooms(snapshot: dict) -> tuple[dict[int, tuple[int, int, int]], dict[int, dict]]:
    rooms = {int(room["num"]): room for room in snapshot.get("rooms", ())}
    current = int(snapshot.get("current") or 0)
    if not current or current not in rooms:
        return {}, rooms

    coords: dict[int, tuple[int, int, int]] = {current: (0, 0, 0)}
    occupied: dict[tuple[int, int, int], int] = {(0, 0, 0): current}
    queue: deque[int] = deque((current,))
    while queue:
        room_num = queue.popleft()
        x, y, z = coords[room_num]
        room = rooms[room_num]
        for direction, target_value in room.get("exits", {}).items():
            target = int(target_value)
            if target not in rooms or target in coords:
                continue
            delta = _DIRECTION_DELTAS.get(str(direction).lower())
            if delta is None:
                continue
            candidate = (x + delta[0], y + delta[1], z + delta[2])
            if candidate in occupied and occupied[candidate] != target:
                # Authored MUD topology is not guaranteed to be Euclidean. Keep a
                # readable local diagram instead of stacking two labels together.
                alternatives = (
                    (candidate[0] + 1, candidate[1], candidate[2]),
                    (candidate[0] - 1, candidate[1], candidate[2]),
                    (candidate[0], candidate[1] + 1, candidate[2]),
                    (candidate[0], candidate[1] - 1, candidate[2]),
                )
                candidate = next((value for value in alternatives if value not in occupied), candidate)
            coords[target] = candidate
            occupied[candidate] = target
            queue.append(target)
    return coords, rooms


def _render_floor(
    z: int,
    coords: dict[int, tuple[int, int, int]],
    rooms: dict[int, dict],
    labels: dict[int, str],
) -> list[str]:
    floor = {room_num: coord for room_num, coord in coords.items() if coord[2] == z}
    if not floor:
        return []

    xs = [coord[0] for coord in floor.values()]
    ys = [coord[1] for coord in floor.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_scale = 7
    y_scale = 3
    width = (max_x - min_x) * x_scale + 5
    height = (max_y - min_y) * y_scale + 1
    canvas = [[" " for _ in range(width)] for _ in range(height)]

    def point(coord: tuple[int, int, int]) -> tuple[int, int]:
        x, y, _ = coord
        return (max_y - y) * y_scale, (x - min_x) * x_scale + 1

    # Draw cardinal connections first so room labels remain on top.
    drawn: set[tuple[int, int]] = set()
    for room_num, coord in floor.items():
        row, col = point(coord)
        for direction, target_value in rooms[room_num].get("exits", {}).items():
            target = int(target_value)
            if target not in floor:
                continue
            pair = tuple(sorted((room_num, target)))
            if pair in drawn:
                continue
            drawn.add(pair)
            target_row, target_col = point(floor[target])
            direction = str(direction).lower()
            if row == target_row:
                for cursor in range(min(col, target_col) + 2, max(col, target_col)):
                    canvas[row][cursor] = "-"
            elif col == target_col:
                for cursor in range(min(row, target_row) + 1, max(row, target_row)):
                    canvas[cursor][col] = "|"
            elif direction in {"northeast", "southwest", "northwest", "southeast"}:
                mid_row = (row + target_row) // 2
                mid_col = (col + target_col) // 2
                if 0 <= mid_row < height and 0 <= mid_col < width:
                    canvas[mid_row][mid_col] = "/" if (target_row - row) * (target_col - col) < 0 else "\\"

    for room_num, coord in floor.items():
        row, col = point(coord)
        token = labels[room_num]
        for offset, char in enumerate(token):
            if 0 <= col + offset < width:
                canvas[row][col + offset] = char

    return ["".join(line).rstrip() for line in canvas]


def render_ascii_map(session, world_service, radius: int = DEFAULT_MAP_RADIUS) -> str:
    snapshot = build_discovered_map_snapshot(session, world_service, radius)
    rooms_list = snapshot.get("rooms", [])
    if not rooms_list:
        return "No discovered map is available here yet.\r\n"

    coords, rooms = _coordinate_rooms(snapshot)
    current = int(snapshot["current"])
    ordered = sorted(
        rooms,
        key=lambda room_num: (
            0 if room_num == current else 1,
            int(rooms[room_num].get("distance", 0)),
            str(rooms[room_num].get("name", "")),
        ),
    )
    labels: dict[int, str] = {}
    next_number = 1
    for room_num in ordered:
        if room_num == current:
            labels[room_num] = "@"
        else:
            labels[room_num] = str(next_number)
            next_number += 1

    lines = [
        "",
        f"--- Local Map: discovered rooms (radius {snapshot['radius']}) ---",
    ]
    floors = sorted({coord[2] for coord in coords.values()}, reverse=True)
    for z in floors:
        if len(floors) > 1:
            if z > 0:
                lines.append(f"[Upper level +{z}]")
            elif z < 0:
                lines.append(f"[Lower level {z}]")
            else:
                lines.append("[Current level]")
        lines.extend(_render_floor(z, coords, rooms, labels))
        lines.append("")

    lines.append("@  " + str(rooms[current]["name"]))
    for room_num in ordered:
        if room_num == current:
            continue
        room = rooms[room_num]
        lines.append(f"{labels[room_num]:>2}  {room['name']}")
    lines.extend(
        [
            "",
            f"Mapped: {snapshot['discovered_count']} rooms total for this character.",
            "Only rooms you have personally entered appear here. LOOK or EXITS may show roads beyond the mapped frontier.",
            "Use MAP 1 through MAP 4 to change the local radius.",
            "",
        ]
    )
    return "\r\n".join(lines)


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_exploration_map_runtime(player_session_class, world_service) -> None:
    """Install persistent discovery plus the plain-Telnet MAP command."""

    if getattr(player_session_class, "_exploration_map_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_show_current_room = player_session_class.show_current_room
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if getattr(self, "character", None) is not None:
            note_room_visited(self)

    async def show_current_room(self) -> None:
        if getattr(self, "character", None) is not None:
            note_room_visited(self)
        await previous_show_current_room(self)

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        if normalized == "map" or normalized == "map here":
            await self.send(render_ascii_map(self, world_service, DEFAULT_MAP_RADIUS))
            return
        if normalized.startswith("map "):
            value = normalized.removeprefix("map ").strip()
            if value.isdigit() and 1 <= int(value) <= MAX_MAP_RADIUS:
                await self.send(render_ascii_map(self, world_service, int(value)))
                return
            if value in {"help", "?"}:
                await self.send(
                    "MAP shows only rooms this character has personally visited. "
                    "Use MAP 1 through MAP 4 to choose the local radius.\r\n"
                )
                return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class._exploration_map_runtime_installed = True
