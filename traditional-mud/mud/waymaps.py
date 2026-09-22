from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import re

from mud.astralis_time import ASTRALIS_CLOCK
from mud.room_engine import PlayerRoomContext


BLANK_WAYMAP_KEY = "blank_waymap"
MARKED_WAYMAP_KEY = "marked_waymap"
WAYMAP_STEP_DELAY_SECONDS = 0.85
MAX_ROUTE_ROOMS = 10000

_WAYMAP_ID = re.compile(r"^#?(\d+)$")


WAYMAP_SCHEMA = """
CREATE TABLE IF NOT EXISTS waymap_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_room_key TEXT NOT NULL,
    destination_name TEXT NOT NULL,
    cartographer_character_id INTEGER,
    cartographer_name TEXT NOT NULL DEFAULT '',
    holder_kind TEXT NOT NULL,
    holder_key TEXT NOT NULL,
    holder_reservation INTEGER,
    created_astral_day INTEGER NOT NULL DEFAULT 0,
    journeys_completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cartographer_character_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_waymap_holder
ON waymap_instances(holder_kind, holder_key, holder_reservation, id);

CREATE INDEX IF NOT EXISTS idx_waymap_destination
ON waymap_instances(destination_room_key);

CREATE TABLE IF NOT EXISTS waymap_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waymap_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_character_id INTEGER,
    from_holder_kind TEXT,
    from_holder_key TEXT,
    to_holder_kind TEXT,
    to_holder_key TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (waymap_id) REFERENCES waymap_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_character_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_waymap_events_waymap
ON waymap_events(waymap_id, id);

CREATE TRIGGER IF NOT EXISTS trg_waymap_retire_deleted_character
AFTER DELETE ON characters
BEGIN
    UPDATE waymap_instances
    SET holder_kind = 'retired',
        holder_key = 'character_deleted',
        holder_reservation = NULL,
        updated_at = CURRENT_TIMESTAMP
    WHERE holder_kind = 'character'
      AND holder_key = CAST(OLD.id AS TEXT);
END;
"""


@dataclass(frozen=True, slots=True)
class WaymapHolder:
    kind: str
    key: str
    reservation: int | None = None

    @classmethod
    def character(cls, character_id: int) -> "WaymapHolder":
        return cls("character", str(int(character_id)))

    @classmethod
    def room(cls, room_key: str) -> "WaymapHolder":
        return cls("room", str(room_key))

    @classmethod
    def retired(cls, reason: str) -> "WaymapHolder":
        return cls("retired", str(reason))


@dataclass(frozen=True, slots=True)
class WaymapRecord:
    id: int
    destination_room_key: str
    destination_name: str
    cartographer_character_id: int | None
    cartographer_name: str
    holder_kind: str
    holder_key: str
    holder_reservation: int | None
    created_astral_day: int
    journeys_completed: int


def ensure_waymap_schema(database) -> None:
    if getattr(database, "_waymap_schema_ready", False):
        return
    with database.connect() as db:
        db.executescript(WAYMAP_SCHEMA)
    database._waymap_schema_ready = True


def _holder(value) -> WaymapHolder:
    return WaymapHolder(
        str(value.kind),
        str(value.key),
        None if getattr(value, "reservation", None) is None else int(value.reservation),
    )


def _holder_where(holder: WaymapHolder) -> tuple[str, tuple[object, ...]]:
    if holder.reservation is None:
        return (
            "holder_kind = ? AND holder_key = ? AND holder_reservation IS NULL",
            (holder.kind, holder.key),
        )
    return (
        "holder_kind = ? AND holder_key = ? AND holder_reservation = ?",
        (holder.kind, holder.key, int(holder.reservation)),
    )


def _record(row) -> WaymapRecord:
    return WaymapRecord(
        id=int(row["id"]),
        destination_room_key=str(row["destination_room_key"]),
        destination_name=str(row["destination_name"]),
        cartographer_character_id=(
            None if row["cartographer_character_id"] is None else int(row["cartographer_character_id"])
        ),
        cartographer_name=str(row["cartographer_name"] or ""),
        holder_kind=str(row["holder_kind"]),
        holder_key=str(row["holder_key"]),
        holder_reservation=(
            None if row["holder_reservation"] is None else int(row["holder_reservation"])
        ),
        created_astral_day=int(row["created_astral_day"] or 0),
        journeys_completed=int(row["journeys_completed"] or 0),
    )


def _event(
    db,
    *,
    waymap_id: int,
    event_type: str,
    actor_character_id: int | None = None,
    from_holder: WaymapHolder | None = None,
    to_holder: WaymapHolder | None = None,
    note: str = "",
) -> None:
    db.execute(
        """
        INSERT INTO waymap_events (
            waymap_id, event_type, actor_character_id,
            from_holder_kind, from_holder_key,
            to_holder_kind, to_holder_key, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(waymap_id),
            str(event_type),
            actor_character_id,
            None if from_holder is None else from_holder.kind,
            None if from_holder is None else from_holder.key,
            None if to_holder is None else to_holder.kind,
            None if to_holder is None else to_holder.key,
            str(note),
        ),
    )


def list_waymaps_at_holder(database, holder: WaymapHolder) -> tuple[WaymapRecord, ...]:
    ensure_waymap_schema(database)
    where, params = _holder_where(holder)
    with database.connect() as db:
        rows = db.execute(
            f"""
            SELECT *
            FROM waymap_instances
            WHERE {where}
            ORDER BY id
            """,
            params,
        ).fetchall()
    return tuple(_record(row) for row in rows)


def list_character_waymaps(database, character_id: int) -> tuple[WaymapRecord, ...]:
    return list_waymaps_at_holder(database, WaymapHolder.character(character_id))


def list_room_waymaps(database, room_key: str) -> tuple[WaymapRecord, ...]:
    return list_waymaps_at_holder(database, WaymapHolder.room(room_key))


def _character_name_in_connection(db, character_id: int) -> str:
    row = db.execute("SELECT name FROM characters WHERE id = ?", (int(character_id),)).fetchone()
    return str(row["name"]) if row is not None else f"Character {int(character_id)}"


def mark_blank_waymap(
    database,
    *,
    character_id: int,
    destination_room_key: str,
    destination_name: str,
) -> WaymapRecord | None:
    """Turn one carried blank waymap into one persistent destination-bearing map."""

    ensure_waymap_schema(database)
    destination_room_key = str(destination_room_key).strip()
    destination_name = str(destination_name).strip()
    if not destination_room_key or not destination_name:
        return None

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        stack = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (int(character_id), BLANK_WAYMAP_KEY),
        ).fetchone()
        if stack is None or int(stack["quantity"]) <= 0:
            return None

        remaining = int(stack["quantity"]) - 1
        if remaining:
            db.execute(
                "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                (remaining, int(character_id), BLANK_WAYMAP_KEY),
            )
        else:
            db.execute(
                "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                (int(character_id), BLANK_WAYMAP_KEY),
            )

        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(character_id, item_key) DO UPDATE SET
                quantity = quantity + 1
            """,
            (int(character_id), MARKED_WAYMAP_KEY),
        )

        cartographer_name = _character_name_in_connection(db, character_id)
        moment = ASTRALIS_CLOCK.now()
        cursor = db.execute(
            """
            INSERT INTO waymap_instances (
                destination_room_key, destination_name,
                cartographer_character_id, cartographer_name,
                holder_kind, holder_key, holder_reservation,
                created_astral_day
            )
            VALUES (?, ?, ?, ?, 'character', ?, NULL, ?)
            """,
            (
                destination_room_key,
                destination_name,
                int(character_id),
                cartographer_name,
                str(int(character_id)),
                int(moment.day_number),
            ),
        )
        waymap_id = int(cursor.lastrowid)
        destination = WaymapHolder.character(character_id)
        _event(
            db,
            waymap_id=waymap_id,
            event_type="marked",
            actor_character_id=int(character_id),
            to_holder=destination,
            note=f"Marked for {destination_name}.",
        )
        row = db.execute("SELECT * FROM waymap_instances WHERE id = ?", (waymap_id,)).fetchone()
    return None if row is None else _record(row)


def _matching_instances_in_connection(
    db,
    holder: WaymapHolder,
    quantity: int,
) -> list:
    where, params = _holder_where(holder)
    return list(
        db.execute(
            f"""
            SELECT *
            FROM waymap_instances
            WHERE {where}
            ORDER BY id
            LIMIT ?
            """,
            (*params, int(quantity)),
        ).fetchall()
    )


def move_location_instances_in_connection(
    db,
    *,
    source,
    destination,
    quantity: int,
    actor_character_id: int | None = None,
    event_type: str = "transfer",
    note: str = "",
) -> bool:
    """Move waymap identity alongside a generic marked-waymap inventory stack."""

    if quantity <= 0:
        raise ValueError("Waymap transfer quantity must be positive.")
    source_holder = _holder(source)
    destination_holder = _holder(destination)
    rows = _matching_instances_in_connection(db, source_holder, quantity)
    if len(rows) != int(quantity):
        return False

    for row in rows:
        waymap_id = int(row["id"])
        db.execute(
            """
            UPDATE waymap_instances
            SET holder_kind = ?, holder_key = ?, holder_reservation = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                destination_holder.kind,
                destination_holder.key,
                destination_holder.reservation,
                waymap_id,
            ),
        )
        _event(
            db,
            waymap_id=waymap_id,
            event_type=event_type,
            actor_character_id=actor_character_id,
            from_holder=source_holder,
            to_holder=destination_holder,
            note=note,
        )
    return True


def transfer_owned_waymaps_in_connection(
    db,
    *,
    from_character_id: int,
    to_character_id: int,
    quantity: int,
    event_type: str = "trade",
    note: str = "",
) -> bool:
    return move_location_instances_in_connection(
        db,
        source=WaymapHolder.character(from_character_id),
        destination=WaymapHolder.character(to_character_id),
        quantity=quantity,
        actor_character_id=from_character_id,
        event_type=event_type,
        note=note,
    )


def retire_owned_waymaps_in_connection(
    db,
    *,
    character_id: int,
    quantity: int,
    event_type: str,
    note: str,
) -> bool:
    return move_location_instances_in_connection(
        db,
        source=WaymapHolder.character(character_id),
        destination=WaymapHolder.retired(event_type),
        quantity=quantity,
        actor_character_id=character_id,
        event_type=event_type,
        note=note,
    )


def transfer_specific_waymap_between_characters(
    database,
    *,
    waymap_id: int,
    from_character_id: int,
    to_character_id: int,
) -> WaymapRecord | None:
    """Give one exact waymap instance while keeping the generic item stack consistent."""

    if int(from_character_id) == int(to_character_id):
        return None
    ensure_waymap_schema(database)
    source = WaymapHolder.character(from_character_id)
    destination = WaymapHolder.character(to_character_id)
    where, params = _holder_where(source)

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            f"SELECT * FROM waymap_instances WHERE id = ? AND {where}",
            (int(waymap_id), *params),
        ).fetchone()
        if row is None:
            return None
        stack = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (int(from_character_id), MARKED_WAYMAP_KEY),
        ).fetchone()
        if stack is None or int(stack["quantity"]) <= 0:
            return None

        remaining = int(stack["quantity"]) - 1
        if remaining:
            db.execute(
                "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                (remaining, int(from_character_id), MARKED_WAYMAP_KEY),
            )
        else:
            db.execute(
                "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                (int(from_character_id), MARKED_WAYMAP_KEY),
            )
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + 1
            """,
            (int(to_character_id), MARKED_WAYMAP_KEY),
        )
        db.execute(
            """
            UPDATE waymap_instances
            SET holder_kind = 'character', holder_key = ?, holder_reservation = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(int(to_character_id)), int(waymap_id)),
        )
        _event(
            db,
            waymap_id=int(waymap_id),
            event_type="given",
            actor_character_id=int(from_character_id),
            from_holder=source,
            to_holder=destination,
            note="Given directly to another traveler.",
        )
        updated = db.execute("SELECT * FROM waymap_instances WHERE id = ?", (int(waymap_id),)).fetchone()
    return None if updated is None else _record(updated)


def record_completed_journey(database, *, waymap_id: int, character_id: int) -> None:
    ensure_waymap_schema(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT destination_name FROM waymap_instances WHERE id = ?",
            (int(waymap_id),),
        ).fetchone()
        if row is None:
            return
        db.execute(
            """
            UPDATE waymap_instances
            SET journeys_completed = journeys_completed + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(waymap_id),),
        )
        holder = WaymapHolder.character(character_id)
        _event(
            db,
            waymap_id=int(waymap_id),
            event_type="journey_completed",
            actor_character_id=int(character_id),
            from_holder=holder,
            to_holder=holder,
            note=f"Guided a traveler to {row['destination_name']}.",
        )


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _selector_text(value: str) -> str:
    normalized = _normalize(value)
    for prefix in ("marked waymap ", "marked map ", "waymap ", "map "):
        if normalized.startswith(prefix):
            return normalized[len(prefix):].strip()
    if normalized in {"marked waymap", "marked map", "waymap", "map"}:
        return ""
    return normalized


def resolve_character_waymap(
    database,
    character_id: int,
    selector: str = "",
) -> tuple[WaymapRecord | None, str | None]:
    maps = list_character_waymaps(database, character_id)
    if not maps:
        return None, "You are not carrying a marked waymap."

    wanted = _selector_text(selector)
    if not wanted:
        if len(maps) == 1:
            return maps[0], None
        return None, "You carry more than one marked waymap. Use WAYMAPS, then USE WAYMAP #<number>."

    id_match = _WAYMAP_ID.fullmatch(wanted)
    if id_match:
        waymap_id = int(id_match.group(1))
        match = next((row for row in maps if row.id == waymap_id), None)
        if match is None:
            return None, f"You are not carrying Waymap #{waymap_id}."
        return match, None

    exact = [row for row in maps if _normalize(row.destination_name) == wanted]
    partial = [row for row in maps if wanted in _normalize(row.destination_name)]
    matches = exact or partial
    unique = tuple(dict.fromkeys(matches))
    if not unique:
        return None, "None of your marked waymaps points to that destination."
    if len(unique) > 1:
        choices = ", ".join(f"#{row.id} {row.destination_name}" for row in unique)
        return None, "Be more specific: " + choices + "."
    return unique[0], None


def _route_context(session) -> PlayerRoomContext:
    character = session.character
    moment = ASTRALIS_CLOCK.now()
    return PlayerRoomContext(
        character_id=int(character.id),
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=int(character.level),
        character_flags=frozenset(session.database.list_flags(character.id)),
        hour=int(moment.hour),
    )


def shortest_route(world_service, session, start_room_key: str, destination_room_key: str) -> tuple[str, ...] | None:
    """Breadth-first route over exits the character can actually traverse right now."""

    start = str(start_room_key)
    goal = str(destination_room_key)
    if not start or not goal:
        return None
    if start == goal:
        return ()
    if world_service.scene(start) is None or world_service.scene(goal) is None:
        return None

    context = _route_context(session)
    queue: deque[str] = deque((start,))
    previous: dict[str, tuple[str, str] | None] = {start: None}

    while queue and len(previous) <= MAX_ROUTE_ROOMS:
        room_key = queue.popleft()
        scene = world_service.scene(room_key)
        if scene is None:
            continue
        for exit_definition in scene.exits:
            resolution = world_service.resolve_exit(room_key, exit_definition.direction, context)
            if not resolution.allowed or resolution.exit is None:
                continue
            destination = str(resolution.exit.destination_key)
            if destination in previous or world_service.scene(destination) is None:
                continue
            previous[destination] = (room_key, str(resolution.exit.direction))
            if destination == goal:
                queue.clear()
                break
            queue.append(destination)

    if goal not in previous:
        return None

    reversed_directions: list[str] = []
    cursor = goal
    while cursor != start:
        step = previous.get(cursor)
        if step is None:
            return None
        prior_room, direction = step
        reversed_directions.append(direction)
        cursor = prior_room
    reversed_directions.reverse()
    return tuple(reversed_directions)


def audit_waymaps(database) -> tuple[str, ...]:
    """Find stack/instance mismatches anywhere physical waymaps can exist."""

    from mud.item_locations import ensure_item_location_storage

    ensure_waymap_schema(database)
    ensure_item_location_storage(database)
    problems: list[str] = []
    with database.connect() as db:
        character_rows = db.execute(
            """
            SELECT c.id,
                   COALESCE(i.quantity, 0) AS stack_quantity,
                   COUNT(w.id) AS instance_quantity
            FROM characters c
            LEFT JOIN character_items i
              ON i.character_id = c.id AND i.item_key = ?
            LEFT JOIN waymap_instances w
              ON w.holder_kind = 'character'
             AND w.holder_key = CAST(c.id AS TEXT)
             AND w.holder_reservation IS NULL
            GROUP BY c.id, i.quantity
            HAVING COALESCE(i.quantity, 0) != COUNT(w.id)
            """,
            (MARKED_WAYMAP_KEY,),
        ).fetchall()
        for row in character_rows:
            problems.append(
                f"character {int(row['id'])}: stack {int(row['stack_quantity'])}, "
                f"instances {int(row['instance_quantity'])}"
            )

        room_rows = db.execute(
            """
            WITH room_keys AS (
                SELECT room_key AS key
                FROM room_ground_items
                WHERE item_key = ?
                UNION
                SELECT holder_key AS key
                FROM waymap_instances
                WHERE holder_kind = 'room'
            )
            SELECT r.key AS room_key,
                   COALESCE(g.quantity, 0) AS stack_quantity,
                   COUNT(w.id) AS instance_quantity
            FROM room_keys r
            LEFT JOIN room_ground_items g
              ON g.room_key = r.key AND g.item_key = ?
            LEFT JOIN waymap_instances w
              ON w.holder_kind = 'room'
             AND w.holder_key = r.key
             AND w.holder_reservation IS NULL
            GROUP BY r.key, g.quantity
            HAVING COALESCE(g.quantity, 0) != COUNT(w.id)
            """,
            (MARKED_WAYMAP_KEY, MARKED_WAYMAP_KEY),
        ).fetchall()
        for row in room_rows:
            problems.append(
                f"room {row['room_key']}: stack {int(row['stack_quantity'])}, "
                f"instances {int(row['instance_quantity'])}"
            )

        container_rows = db.execute(
            """
            WITH stack AS (
                SELECT CAST(container_id AS TEXT) AS holder_key,
                       reserved_character_id AS reservation,
                       SUM(quantity) AS quantity
                FROM world_container_items
                WHERE item_key = ?
                GROUP BY container_id, reserved_character_id
            ),
            instances AS (
                SELECT holder_key,
                       COALESCE(holder_reservation, 0) AS reservation,
                       COUNT(*) AS quantity
                FROM waymap_instances
                WHERE holder_kind = 'container'
                GROUP BY holder_key, COALESCE(holder_reservation, 0)
            ),
            buckets AS (
                SELECT holder_key, reservation FROM stack
                UNION
                SELECT holder_key, reservation FROM instances
            )
            SELECT b.holder_key,
                   b.reservation,
                   COALESCE(s.quantity, 0) AS stack_quantity,
                   COALESCE(i.quantity, 0) AS instance_quantity
            FROM buckets b
            LEFT JOIN stack s
              ON s.holder_key = b.holder_key
             AND s.reservation = b.reservation
            LEFT JOIN instances i
              ON i.holder_key = b.holder_key
             AND i.reservation = b.reservation
            WHERE COALESCE(s.quantity, 0) != COALESCE(i.quantity, 0)
            """,
            (MARKED_WAYMAP_KEY,),
        ).fetchall()
        for row in container_rows:
            problems.append(
                f"container {row['holder_key']} reservation {int(row['reservation'])}: "
                f"stack {int(row['stack_quantity'])}, instances {int(row['instance_quantity'])}"
            )

        orphan_rows = db.execute(
            """
            SELECT w.id, w.holder_key
            FROM waymap_instances w
            LEFT JOIN characters c
              ON w.holder_kind = 'character'
             AND w.holder_key = CAST(c.id AS TEXT)
            WHERE w.holder_kind = 'character' AND c.id IS NULL
            ORDER BY w.id
            """
        ).fetchall()
        for row in orphan_rows:
            problems.append(
                f"waymap #{int(row['id'])}: orphan character holder {row['holder_key']}"
            )

    return tuple(problems)


def _waymap_line(row: WaymapRecord) -> str:
    maker = row.cartographer_name or "unknown cartographer"
    journeys = f"{row.journeys_completed} journey" if row.journeys_completed == 1 else f"{row.journeys_completed} journeys"
    return f"#{row.id}  {row.destination_name} | charted by {maker} | {journeys}"


async def _show_waymaps(session, *, here: bool = False) -> None:
    character = session.character
    if here:
        rows = list_room_waymaps(session.database, character.current_room or "")
        await session.send("\r\n--- Waymaps Here ---\r\n")
        if not rows:
            await session.send("No marked waymaps are lying here.\r\n")
            return
        for row in rows:
            await session.send(_waymap_line(row) + "\r\n")
        return

    blank_count = session.database.item_quantity(character.id, BLANK_WAYMAP_KEY)
    rows = list_character_waymaps(session.database, character.id)
    await session.send("\r\n--- Waymaps ---\r\n")
    await session.send(f"Blank Waymaps: {blank_count}\r\n")
    if not rows:
        await session.send("Marked Waymaps: none\r\n")
    else:
        await session.send("Marked Waymaps:\r\n")
        for row in rows:
            await session.send("  " + _waymap_line(row) + "\r\n")
    await session.send(
        "MARK WAYMAP marks your current room. USE WAYMAP #<number> follows one. "
        "STOP TRAVEL cancels an active route.\r\n"
    )


async def _show_waymap_detail(session, selector: str) -> None:
    row, error = resolve_character_waymap(session.database, session.character.id, selector)
    if row is None:
        await session.send((error or "No such waymap.") + "\r\n")
        return
    await session.send(
        f"\r\nWaymap #{row.id}\r\n"
        f"Destination: {row.destination_name}\r\n"
        f"Charted by: {row.cartographer_name or 'unknown cartographer'}\r\n"
        f"Journeys completed: {row.journeys_completed}\r\n"
        "Use: USE WAYMAP #" + str(row.id) + "\r\n"
    )


def _active_travel(session):
    task = getattr(session, "_waymap_travel_task", None)
    return task if task is not None and not task.done() else None


async def _cancel_travel(session, message: str | None = None) -> bool:
    task = _active_travel(session)
    if task is None:
        return False
    if task is asyncio.current_task():
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    if message:
        await session.send(message.rstrip() + "\r\n")
    return True


async def _walk_waymap(session, world_service, row: WaymapRecord) -> None:
    try:
        while True:
            character = getattr(session, "character", None)
            if character is None:
                return
            if getattr(session, "active_enemy", None) is not None:
                await session.send(
                    f"\r\nWaymap #{row.id} travel stops because combat has begun.\r\n"
                )
                return
            current_room = str(character.current_room or "")
            if current_room == row.destination_room_key:
                record_completed_journey(
                    session.database,
                    waymap_id=row.id,
                    character_id=character.id,
                )
                await session.send(
                    f"\r\nWaymap #{row.id}: you have arrived at {row.destination_name}.\r\n"
                )
                return

            route = shortest_route(world_service, session, current_room, row.destination_room_key)
            if route is None or not route:
                await session.send(
                    f"\r\nWaymap #{row.id} can no longer trace a passable route to "
                    f"{row.destination_name}. A locked door, closed passage, or changed route may be blocking the way.\r\n"
                )
                return

            direction = route[0]
            before_room = current_room
            await session.send(f"\r\nWaymap #{row.id} guides you {direction}.\r\n")
            session._waymap_internal_move = True
            try:
                await session.move_character(direction)
            finally:
                session._waymap_internal_move = False

            character = getattr(session, "character", None)
            if character is None:
                return
            if str(character.current_room or "") == before_room:
                await session.send(
                    f"Waymap #{row.id} travel stops because the next step is no longer passable.\r\n"
                )
                return
            if getattr(session, "active_enemy", None) is not None:
                await session.send(
                    f"Waymap #{row.id} travel stops because something has engaged you.\r\n"
                )
                return
            await asyncio.sleep(WAYMAP_STEP_DELAY_SECONDS)
    except asyncio.CancelledError:
        raise
    finally:
        if getattr(session, "_waymap_travel_task", None) is asyncio.current_task():
            session._waymap_travel_task = None
            session._waymap_travel_id = None


async def _start_travel(session, world_service, selector: str) -> None:
    character = session.character
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot begin waymap travel while fighting.\r\n")
        return

    row, error = resolve_character_waymap(session.database, character.id, selector)
    if row is None:
        await session.send((error or "No such waymap.") + "\r\n")
        return

    current_room = str(character.current_room or "")
    if current_room == row.destination_room_key:
        await session.send(f"You are already at {row.destination_name}.\r\n")
        return

    route = shortest_route(world_service, session, current_room, row.destination_room_key)
    if route is None:
        await session.send(
            f"Waymap #{row.id} cannot trace a passable route from here to {row.destination_name}.\r\n"
        )
        return

    await _cancel_travel(session)
    await session.send(
        f"You consult Waymap #{row.id}. Route: {len(route)} room"
        + ("" if len(route) == 1 else "s")
        + f" to {row.destination_name}. Type STOP TRAVEL at any time.\r\n"
    )
    task = asyncio.create_task(_walk_waymap(session, world_service, row))
    session._waymap_travel_task = task
    session._waymap_travel_id = row.id


async def _mark_current_room(session, world_service) -> None:
    character = session.character
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to chart a waymap while fighting.\r\n")
        return
    if session.database.item_quantity(character.id, BLANK_WAYMAP_KEY) <= 0:
        await session.send(
            "You need a Blank Waymap. They can be crafted through Cartography or purchased from ordinary merchants.\r\n"
        )
        return

    scene = world_service.scene(character.current_room or "")
    if scene is None:
        await session.send("This place is not stable enough to mark on a waymap.\r\n")
        return

    blank_count = session.database.item_quantity(character.id, BLANK_WAYMAP_KEY)
    marked_count = session.database.item_quantity(character.id, MARKED_WAYMAP_KEY)
    if blank_count > 1 and marked_count == 0:
        try:
            from mud.inventory_capacity import can_receive_item

            if not can_receive_item(session.database, character.id, MARKED_WAYMAP_KEY, 1):
                await session.send(
                    "Your inventory is too full to separate a newly marked waymap from the remaining blanks. "
                    "Free a slot or mark your last blank instead.\r\n"
                )
                return
        except Exception:
            pass

    row = mark_blank_waymap(
        session.database,
        character_id=character.id,
        destination_room_key=scene.key,
        destination_name=scene.name,
    )
    if row is None:
        await session.send("The waymap could not be marked safely. Nothing was changed.\r\n")
        return
    await session.send(
        f"You mark {scene.name} as the destination of Waymap #{row.id}. "
        "The marked map can now be used, dropped, given, or traded.\r\n"
    )


async def _delegate_prompt(session, previous_playing_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    prior_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    session.prompt = replay_prompt
    try:
        await previous_playing_prompt(session)
    finally:
        if had_prompt:
            session.prompt = prior_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_waymap_runtime(player_session_class, world_service) -> None:
    """Install physical destination maps and safe step-by-step automatic travel."""

    if getattr(player_session_class, "_waymap_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = getattr(player_session_class, "move_character", None)
    previous_close = getattr(player_session_class, "close", None)

    if previous_move_character is not None:
        async def move_character(self, *args, **kwargs):
            if not getattr(self, "_waymap_internal_move", False):
                await _cancel_travel(
                    self,
                    "You leave the plotted route and stop following the waymap.",
                )
            return await previous_move_character(self, *args, **kwargs)

        player_session_class.move_character = move_character

    if previous_close is not None:
        async def close(self, *args, **kwargs):
            await _cancel_travel(self)
            return await previous_close(self, *args, **kwargs)

        player_session_class.close = close

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            await _cancel_travel(self)
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"waymaps", "waymap list", "maps carried"}:
            await _show_waymaps(self)
            return
        if normalized in {"waymaps here", "waymap here"}:
            await _show_waymaps(self, here=True)
            return

        if normalized in {
            "mark waymap",
            "mark map",
            "use blank waymap",
            "use blank map",
            "chart waymap",
            "chart map",
        }:
            await _mark_current_room(self, world_service)
            return

        if normalized in {"stop travel", "cancel travel", "stop waymap", "cancel waymap"}:
            if not await _cancel_travel(self, "You stop following the waymap."):
                await self.send("You are not currently following a waymap.\r\n")
            return
        if normalized == "stop" and _active_travel(self) is not None:
            await _cancel_travel(self, "You stop following the waymap.")
            return

        for prefix in ("use waymap", "use marked waymap", "use map", "follow waymap"):
            if normalized == prefix or normalized.startswith(prefix + " "):
                selector = stripped[len(prefix):].strip()
                await _start_travel(self, world_service, selector)
                return

        for prefix in ("examine waymap", "inspect waymap", "study waymap"):
            if normalized == prefix or normalized.startswith(prefix + " "):
                selector = stripped[len(prefix):].strip()
                await _show_waymap_detail(self, selector)
                return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._waymap_runtime_installed = True
