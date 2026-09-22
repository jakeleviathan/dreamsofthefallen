from __future__ import annotations

from dataclasses import dataclass


ITEM_LOCATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS room_ground_items (
    room_key TEXT NOT NULL,
    item_key TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_key, item_key)
);

CREATE TABLE IF NOT EXISTS world_containers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    source_key TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',
    owner_character_id INTEGER,
    created_at_epoch REAL NOT NULL,
    protection_expires_at_epoch REAL NOT NULL DEFAULT 0,
    decay_at_epoch REAL NOT NULL,
    currency_amount INTEGER NOT NULL DEFAULT 0 CHECK (currency_amount >= 0),
    death_key TEXT UNIQUE,
    FOREIGN KEY (owner_character_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_world_containers_room
ON world_containers(room_key, kind, decay_at_epoch);

CREATE TABLE IF NOT EXISTS world_container_access (
    container_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    PRIMARY KEY (container_id, character_id),
    FOREIGN KEY (container_id) REFERENCES world_containers(id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS world_container_items (
    container_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    reserved_character_id INTEGER NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (container_id, item_key, reserved_character_id),
    FOREIGN KEY (container_id) REFERENCES world_containers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS character_currency (
    character_id INTEGER NOT NULL,
    currency_key TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
    PRIMARY KEY (character_id, currency_key),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
"""


@dataclass(frozen=True, slots=True)
class ItemLocation:
    """A physical item location.

    Container locations may include a reservation bucket. Reservation 0 means
    unassigned/public. A reservation of None is useful for aggregate reads but
    transfers out of a container must name the exact bucket being moved.
    """

    kind: str
    key: str
    reservation: int | None = None

    @classmethod
    def character(cls, character_id: int) -> "ItemLocation":
        return cls("character", str(int(character_id)))

    @classmethod
    def room(cls, room_key: str) -> "ItemLocation":
        return cls("room", str(room_key))

    @classmethod
    def container(
        cls,
        container_id: int,
        reserved_character_id: int | None = None,
    ) -> "ItemLocation":
        return cls(
            "container",
            str(int(container_id)),
            None if reserved_character_id is None else int(reserved_character_id),
        )


def ensure_item_location_storage(database) -> None:
    with database.connect() as db:
        db.executescript(ITEM_LOCATION_SCHEMA)


def _storage(location: ItemLocation) -> tuple[str, str, object]:
    if location.kind == "character":
        return "character_items", "character_id", int(location.key)
    if location.kind == "room":
        return "room_ground_items", "room_key", location.key
    if location.kind == "container":
        return "world_container_items", "container_id", int(location.key)
    raise ValueError(f"Unsupported item location kind: {location.kind}")


def _where(location: ItemLocation) -> tuple[str, tuple[object, ...]]:
    table, owner_column, owner_value = _storage(location)
    if location.kind == "container" and location.reservation is not None:
        return (
            f"{owner_column} = ? AND reserved_character_id = ?",
            (owner_value, int(location.reservation)),
        )
    return f"{owner_column} = ?", (owner_value,)


def list_location_items(database, location: ItemLocation) -> list[dict[str, int | str]]:
    """List item totals at a location; wildcard containers aggregate reservations."""
    ensure_item_location_storage(database)
    table, _owner_column, _owner_value = _storage(location)
    where, params = _where(location)
    with database.connect() as db:
        rows = db.execute(
            f"""
            SELECT item_key, SUM(quantity) AS quantity
            FROM {table}
            WHERE {where} AND quantity > 0
            GROUP BY item_key
            ORDER BY item_key
            """,
            params,
        ).fetchall()
    return [
        {"item_key": str(row["item_key"]), "quantity": int(row["quantity"])}
        for row in rows
    ]


def list_container_item_rows(database, container_id: int) -> list[dict[str, int | str]]:
    """List exact container stacks, preserving temporary loot reservations."""
    ensure_item_location_storage(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT item_key, quantity, reserved_character_id
            FROM world_container_items
            WHERE container_id = ? AND quantity > 0
            ORDER BY item_key, reserved_character_id
            """,
            (int(container_id),),
        ).fetchall()
    return [
        {
            "item_key": str(row["item_key"]),
            "quantity": int(row["quantity"]),
            "reserved_character_id": int(row["reserved_character_id"]),
        }
        for row in rows
    ]


def location_item_quantity(database, location: ItemLocation, item_key: str) -> int:
    ensure_item_location_storage(database)
    table, _owner_column, _owner_value = _storage(location)
    where, params = _where(location)
    with database.connect() as db:
        row = db.execute(
            f"SELECT SUM(quantity) AS quantity FROM {table} WHERE {where} AND item_key = ?",
            (*params, item_key),
        ).fetchone()
    return 0 if row is None or row["quantity"] is None else int(row["quantity"])


def _write_quantity(db, location: ItemLocation, item_key: str, quantity: int) -> None:
    table, owner_column, owner_value = _storage(location)

    if location.kind == "container":
        reservation = 0 if location.reservation is None else int(location.reservation)
        if quantity <= 0:
            db.execute(
                """
                DELETE FROM world_container_items
                WHERE container_id = ? AND item_key = ? AND reserved_character_id = ?
                """,
                (owner_value, item_key, reservation),
            )
            return
        db.execute(
            """
            INSERT INTO world_container_items (
                container_id, item_key, reserved_character_id, quantity
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(container_id, item_key, reserved_character_id) DO UPDATE SET
                quantity = excluded.quantity
            """,
            (owner_value, item_key, reservation, quantity),
        )
        return

    if quantity <= 0:
        db.execute(
            f"DELETE FROM {table} WHERE {owner_column} = ? AND item_key = ?",
            (owner_value, item_key),
        )
        return

    if location.kind == "room":
        db.execute(
            """
            INSERT INTO room_ground_items (room_key, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(room_key, item_key) DO UPDATE SET
                quantity = excluded.quantity,
                updated_at = CURRENT_TIMESTAMP
            """,
            (owner_value, item_key, quantity),
        )
        return

    db.execute(
        f"""
        INSERT INTO {table} ({owner_column}, item_key, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT({owner_column}, item_key) DO UPDATE SET quantity = excluded.quantity
        """,
        (owner_value, item_key, quantity),
    )


def add_to_location(database, location: ItemLocation, item_key: str, quantity: int = 1) -> None:
    if quantity <= 0:
        raise ValueError("Item quantity added must be positive.")
    ensure_item_location_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = location_item_quantity_in_connection(db, location, item_key)
        _write_quantity(db, location, item_key, current + quantity)


def location_item_quantity_in_connection(db, location: ItemLocation, item_key: str) -> int:
    table, _owner_column, _owner_value = _storage(location)
    where, params = _where(location)
    row = db.execute(
        f"SELECT SUM(quantity) AS quantity FROM {table} WHERE {where} AND item_key = ?",
        (*params, item_key),
    ).fetchone()
    return 0 if row is None or row["quantity"] is None else int(row["quantity"])


def transfer_item(
    database,
    source: ItemLocation,
    destination: ItemLocation,
    item_key: str,
    quantity: int = 1,
) -> bool:
    """Atomically move items between inventory, rooms, and persistent containers."""
    if quantity <= 0:
        raise ValueError("Transfer quantity must be positive.")
    if source.kind == "container" and source.reservation is None:
        raise ValueError("Container transfers require an exact reservation bucket.")

    from mud.item_heritage import (
        HeritageHolder,
        chronicle_first_discoveries,
        ensure_item_heritage_schema,
        ensure_special_inventory_item,
        is_special_item,
        move_location_instances_in_connection,
    )

    ensure_item_location_storage(database)
    ensure_item_heritage_schema(database)

    move_waymaps = None
    if item_key == "marked_waymap":
        from mud.waymaps import ensure_waymap_schema, move_location_instances_in_connection

        ensure_waymap_schema(database)
        move_waymaps = move_location_instances_in_connection

    if source.kind == "character" and is_special_item(item_key):
        ensure_special_inventory_item(database, int(source.key), item_key)

    def heritage_holder(location: ItemLocation) -> HeritageHolder:
        if location.kind == "character":
            return HeritageHolder.character(int(location.key))
        if location.kind == "room":
            return HeritageHolder.room(location.key)
        if location.kind == "container":
            return HeritageHolder.container(int(location.key), location.reservation)
        return HeritageHolder(location.kind, location.key, location.reservation)

    changed_heritage = []
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        available = location_item_quantity_in_connection(db, source, item_key)
        if available < quantity:
            return False

        if move_waymaps is not None:
            actor_character_id = None
            if source.kind == "character":
                actor_character_id = int(source.key)
            elif destination.kind == "character":
                actor_character_id = int(destination.key)
            if source.kind == "character" and destination.kind == "room":
                waymap_event = "dropped"
            elif source.kind == "room" and destination.kind == "character":
                waymap_event = "picked_up"
            else:
                waymap_event = "location_transfer"
            if not move_waymaps(
                db,
                source=source,
                destination=destination,
                quantity=quantity,
                actor_character_id=actor_character_id,
                event_type=waymap_event,
                note="Moved with the physical marked waymap.",
            ):
                return False

        _write_quantity(db, source, item_key, available - quantity)
        current = location_item_quantity_in_connection(db, destination, item_key)
        _write_quantity(db, destination, item_key, current + quantity)
        changed_heritage = move_location_instances_in_connection(
            db,
            source=heritage_holder(source),
            destination=heritage_holder(destination),
            item_key=item_key,
            quantity=quantity,
        )
    if changed_heritage:
        chronicle_first_discoveries(database, changed_heritage)
    return True


def currency_balance(database, character_id: int, currency_key: str = "coin") -> int:
    ensure_item_location_storage(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT amount FROM character_currency WHERE character_id = ? AND currency_key = ?",
            (character_id, currency_key),
        ).fetchone()
    return 0 if row is None else int(row["amount"])


def credit_currency(database, character_id: int, amount: int, currency_key: str = "coin") -> None:
    if amount < 0:
        raise ValueError("Currency credit cannot be negative.")
    if amount == 0:
        return
    ensure_item_location_storage(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_currency (character_id, currency_key, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, currency_key) DO UPDATE SET amount = amount + excluded.amount
            """,
            (character_id, currency_key, amount),
        )
