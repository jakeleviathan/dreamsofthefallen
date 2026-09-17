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
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (container_id, item_key),
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
    kind: str
    key: str

    @classmethod
    def character(cls, character_id: int) -> "ItemLocation":
        return cls("character", str(int(character_id)))

    @classmethod
    def room(cls, room_key: str) -> "ItemLocation":
        return cls("room", str(room_key))

    @classmethod
    def container(cls, container_id: int) -> "ItemLocation":
        return cls("container", str(int(container_id)))


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


def list_location_items(database, location: ItemLocation) -> list[dict[str, int | str]]:
    ensure_item_location_storage(database)
    table, owner_column, owner_value = _storage(location)
    with database.connect() as db:
        rows = db.execute(
            f"SELECT item_key, quantity FROM {table} WHERE {owner_column} = ? AND quantity > 0 ORDER BY item_key",
            (owner_value,),
        ).fetchall()
    return [
        {"item_key": str(row["item_key"]), "quantity": int(row["quantity"])}
        for row in rows
    ]


def location_item_quantity(database, location: ItemLocation, item_key: str) -> int:
    ensure_item_location_storage(database)
    table, owner_column, owner_value = _storage(location)
    with database.connect() as db:
        row = db.execute(
            f"SELECT quantity FROM {table} WHERE {owner_column} = ? AND item_key = ?",
            (owner_value, item_key),
        ).fetchone()
    return 0 if row is None else int(row["quantity"])


def _write_quantity(db, location: ItemLocation, item_key: str, quantity: int) -> None:
    table, owner_column, owner_value = _storage(location)
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
        table, owner_column, owner_value = _storage(location)
        row = db.execute(
            f"SELECT quantity FROM {table} WHERE {owner_column} = ? AND item_key = ?",
            (owner_value, item_key),
        ).fetchone()
        current = 0 if row is None else int(row["quantity"])
        _write_quantity(db, location, item_key, current + quantity)


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
    ensure_item_location_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        source_table, source_owner_column, source_owner_value = _storage(source)
        row = db.execute(
            f"SELECT quantity FROM {source_table} WHERE {source_owner_column} = ? AND item_key = ?",
            (source_owner_value, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            return False

        remaining = int(row["quantity"]) - quantity
        _write_quantity(db, source, item_key, remaining)

        dest_table, dest_owner_column, dest_owner_value = _storage(destination)
        dest = db.execute(
            f"SELECT quantity FROM {dest_table} WHERE {dest_owner_column} = ? AND item_key = ?",
            (dest_owner_value, item_key),
        ).fetchone()
        current = 0 if dest is None else int(dest["quantity"])
        _write_quantity(db, destination, item_key, current + quantity)
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
