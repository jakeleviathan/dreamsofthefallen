from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Iterable

import mud.crafting as crafting
from mud.astralis_time import ASTRALIS_CLOCK


HERITAGE_VERSION = "1.0.0"
RECIPE_HERITAGE_VERSION = 1
SPECIAL_ITEM_NAMES = frozenset({"briar eye charm"})
SPECIAL_ITEM_KEYS: set[str] = set()
FIRST_DISCOVERY_CHRONICLE = True


@dataclass(frozen=True, slots=True)
class HeritageHolder:
    kind: str
    key: str
    reservation: int | None = None

    @classmethod
    def character(cls, character_id: int) -> "HeritageHolder":
        return cls("character", str(int(character_id)))

    @classmethod
    def room(cls, room_key: str) -> "HeritageHolder":
        return cls("room", str(room_key))

    @classmethod
    def container(cls, container_id: int, reservation: int | None = None) -> "HeritageHolder":
        return cls("container", str(int(container_id)), reservation)

    @classmethod
    def veyra_vault(cls, character_id: int) -> "HeritageHolder":
        return cls("veyra_vault", str(int(character_id)))

    @classmethod
    def veyra_market(cls, listing_id: int) -> "HeritageHolder":
        return cls("veyra_market", str(int(listing_id)))

    @classmethod
    def living_storage(cls, character_id: int) -> "HeritageHolder":
        return cls("living_storage", str(int(character_id)))

    @classmethod
    def living_display(cls, character_id: int, slot: int) -> "HeritageHolder":
        return cls("living_display", f"{int(character_id)}:{int(slot)}")

    @classmethod
    def retired(cls, reason: str = "retired") -> "HeritageHolder":
        return cls("retired", reason)


HERITAGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS item_heritage_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial TEXT UNIQUE,
    item_key TEXT NOT NULL,
    heritage_kind TEXT NOT NULL,
    current_owner_character_id INTEGER,
    holder_kind TEXT NOT NULL,
    holder_key TEXT NOT NULL,
    holder_reservation INTEGER,
    maker_character_id INTEGER,
    maker_name TEXT,
    maker_sequence INTEGER,
    recipe_key TEXT,
    profession_key TEXT,
    recipe_version INTEGER,
    recipe_revision TEXT,
    high_quality INTEGER NOT NULL DEFAULT 0,
    crafted_room_key TEXT,
    crafted_day INTEGER,
    discovery_ordinal INTEGER,
    discovery_exact INTEGER NOT NULL DEFAULT 1,
    origin_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_owner_character_id) REFERENCES characters(id) ON DELETE SET NULL,
    FOREIGN KEY (maker_character_id) REFERENCES characters(id) ON DELETE SET NULL,
    UNIQUE(maker_character_id, item_key, maker_sequence),
    UNIQUE(item_key, discovery_ordinal)
);

CREATE INDEX IF NOT EXISTS idx_item_heritage_owner_item
ON item_heritage_instances(current_owner_character_id, item_key);

CREATE INDEX IF NOT EXISTS idx_item_heritage_holder
ON item_heritage_instances(holder_kind, holder_key, item_key);

CREATE INDEX IF NOT EXISTS idx_item_heritage_discovery
ON item_heritage_instances(item_key, discovery_ordinal);

CREATE TABLE IF NOT EXISTS item_heritage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    astralis_day INTEGER NOT NULL,
    actor_character_id INTEGER,
    actor_name TEXT,
    from_owner_character_id INTEGER,
    from_owner_name TEXT,
    to_owner_character_id INTEGER,
    to_owner_name TEXT,
    from_holder_kind TEXT,
    from_holder_key TEXT,
    to_holder_kind TEXT,
    to_holder_key TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES item_heritage_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_character_id) REFERENCES characters(id) ON DELETE SET NULL,
    FOREIGN KEY (from_owner_character_id) REFERENCES characters(id) ON DELETE SET NULL,
    FOREIGN KEY (to_owner_character_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_item_heritage_events_instance
ON item_heritage_events(instance_id, id);
"""


def ensure_item_heritage_schema(database) -> None:
    with database.connect() as db:
        db.executescript(HERITAGE_SCHEMA)


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())


def item_name(item_key: str) -> str:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    return definition.name if definition is not None else item_key.replace("_", " ").title()


def is_special_item(item_key: str) -> bool:
    if item_key in SPECIAL_ITEM_KEYS:
        return True
    try:
        from mud.iconic_items import ICONIC_BY_KEY

        if item_key in ICONIC_BY_KEY:
            return True
    except Exception:
        pass
    return _normalize(item_name(item_key)) in SPECIAL_ITEM_NAMES


def recipe_revision(recipe) -> str:
    material_text = ",".join(
        f"{requirement.item_key}:{int(requirement.quantity)}"
        for requirement in getattr(recipe, "materials", ())
    )
    raw = "|".join(
        (
            str(getattr(recipe, "key", "")),
            str(getattr(recipe, "trade_skill_key", "")),
            str(getattr(recipe, "output_item_key", "")),
            str(int(getattr(recipe, "output_quantity", 1))),
            str(int(getattr(recipe, "minimum_skill", 0))),
            str(int(getattr(recipe, "high_skill_quality_threshold", 0))),
            str(getattr(recipe, "station_key", "") or ""),
            str(getattr(recipe, "design_status", "") or ""),
            material_text,
        )
    )
    return sha1(raw.encode("utf-8")).hexdigest()[:12]


def _character_snapshot_in_connection(db, character_id: int) -> tuple[str, str]:
    row = db.execute(
        "SELECT name, current_room FROM characters WHERE id = ?",
        (int(character_id),),
    ).fetchone()
    if row is None:
        return f"Character {int(character_id)}", ""
    return str(row["name"]), str(row["current_room"] or "")


def _character_name_in_connection(db, character_id: int | None) -> str | None:
    if character_id is None:
        return None
    row = db.execute("SELECT name FROM characters WHERE id = ?", (int(character_id),)).fetchone()
    return None if row is None else str(row["name"])


def _next_maker_sequence(db, character_id: int, item_key: str) -> int:
    row = db.execute(
        """
        SELECT MAX(maker_sequence) AS n
        FROM item_heritage_instances
        WHERE maker_character_id = ? AND item_key = ? AND maker_sequence IS NOT NULL
        """,
        (int(character_id), item_key),
    ).fetchone()
    return (0 if row is None or row["n"] is None else int(row["n"])) + 1


def _next_discovery_ordinal(db, item_key: str) -> int:
    row = db.execute(
        """
        SELECT MAX(discovery_ordinal) AS n
        FROM item_heritage_instances
        WHERE item_key = ? AND discovery_ordinal IS NOT NULL
        """,
        (item_key,),
    ).fetchone()
    return (0 if row is None or row["n"] is None else int(row["n"])) + 1


def _serial_prefix(*, crafted: bool, special: bool) -> str:
    if crafted and special:
        return "CH"
    if crafted:
        return "C"
    return "H"


def _event_in_connection(
    db,
    *,
    instance_id: int,
    event_type: str,
    actor_character_id: int | None,
    from_owner_character_id: int | None,
    to_owner_character_id: int | None,
    from_holder: HeritageHolder | None,
    to_holder: HeritageHolder | None,
    note: str,
) -> None:
    moment = ASTRALIS_CLOCK.now()
    db.execute(
        """
        INSERT INTO item_heritage_events (
            instance_id, event_type, astralis_day,
            actor_character_id, actor_name,
            from_owner_character_id, from_owner_name,
            to_owner_character_id, to_owner_name,
            from_holder_kind, from_holder_key,
            to_holder_kind, to_holder_key, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(instance_id),
            event_type,
            int(moment.day_number),
            actor_character_id,
            _character_name_in_connection(db, actor_character_id),
            from_owner_character_id,
            _character_name_in_connection(db, from_owner_character_id),
            to_owner_character_id,
            _character_name_in_connection(db, to_owner_character_id),
            None if from_holder is None else from_holder.kind,
            None if from_holder is None else from_holder.key,
            None if to_holder is None else to_holder.kind,
            None if to_holder is None else to_holder.key,
            note,
        ),
    )


def _insert_instance_in_connection(
    db,
    *,
    item_key: str,
    heritage_kind: str,
    owner_character_id: int | None,
    holder: HeritageHolder,
    maker_character_id: int | None = None,
    maker_name: str | None = None,
    maker_sequence: int | None = None,
    recipe_key: str | None = None,
    profession_key: str | None = None,
    recipe_version: int | None = None,
    recipe_revision_value: str | None = None,
    high_quality: bool = False,
    crafted_room_key: str | None = None,
    crafted_day: int | None = None,
    discovery_ordinal: int | None = None,
    discovery_exact: bool = True,
    origin_text: str = "",
) -> dict[str, object]:
    cursor = db.execute(
        """
        INSERT INTO item_heritage_instances (
            item_key, heritage_kind, current_owner_character_id,
            holder_kind, holder_key, holder_reservation,
            maker_character_id, maker_name, maker_sequence,
            recipe_key, profession_key, recipe_version, recipe_revision,
            high_quality, crafted_room_key, crafted_day,
            discovery_ordinal, discovery_exact, origin_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_key,
            heritage_kind,
            owner_character_id,
            holder.kind,
            holder.key,
            holder.reservation,
            maker_character_id,
            maker_name,
            maker_sequence,
            recipe_key,
            profession_key,
            recipe_version,
            recipe_revision_value,
            1 if high_quality else 0,
            crafted_room_key,
            crafted_day,
            discovery_ordinal,
            1 if discovery_exact else 0,
            origin_text,
        ),
    )
    instance_id = int(cursor.lastrowid)
    serial = f"{_serial_prefix(crafted=maker_character_id is not None, special=discovery_ordinal is not None)}{instance_id:08d}"
    db.execute(
        "UPDATE item_heritage_instances SET serial = ? WHERE id = ?",
        (serial, instance_id),
    )
    return {
        "id": instance_id,
        "serial": serial,
        "item_key": item_key,
        "discovery_ordinal": discovery_ordinal,
        "discovery_exact": bool(discovery_exact),
    }


def record_crafted_gear_in_connection(
    db,
    *,
    character_id: int,
    item_key: str,
    quantity: int,
    recipe_key: str,
    profession_key: str,
    recipe_revision_value: str,
    high_quality: bool,
) -> list[dict[str, object]]:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    if definition is None or definition.equipment is None or quantity <= 0:
        return []

    maker_name, room_key = _character_snapshot_in_connection(db, character_id)
    moment = ASTRALIS_CLOCK.now()
    special = is_special_item(item_key)
    created: list[dict[str, object]] = []
    for _ in range(int(quantity)):
        maker_sequence = _next_maker_sequence(db, character_id, item_key)
        discovery_ordinal = _next_discovery_ordinal(db, item_key) if special else None
        origin = (
            f"Crafted by {maker_name} as their #{maker_sequence} {definition.name}"
            + (f" in {room_key.replace('_', ' ')}" if room_key else "")
            + "."
        )
        entry = _insert_instance_in_connection(
            db,
            item_key=item_key,
            heritage_kind="crafted_special" if special else "crafted",
            owner_character_id=int(character_id),
            holder=HeritageHolder.character(character_id),
            maker_character_id=int(character_id),
            maker_name=maker_name,
            maker_sequence=maker_sequence,
            recipe_key=recipe_key,
            profession_key=profession_key,
            recipe_version=RECIPE_HERITAGE_VERSION,
            recipe_revision_value=recipe_revision_value,
            high_quality=high_quality,
            crafted_room_key=room_key or None,
            crafted_day=int(moment.day_number),
            discovery_ordinal=discovery_ordinal,
            discovery_exact=True,
            origin_text=origin,
        )
        _event_in_connection(
            db,
            instance_id=int(entry["id"]),
            event_type="crafted",
            actor_character_id=int(character_id),
            from_owner_character_id=None,
            to_owner_character_id=int(character_id),
            from_holder=None,
            to_holder=HeritageHolder.character(character_id),
            note=origin,
        )
        created.append(entry)
    return created


def record_special_acquisition_in_connection(
    db,
    *,
    character_id: int,
    item_key: str,
    quantity: int = 1,
    origin_text: str = "",
    discovery_exact: bool = True,
    holder: HeritageHolder | None = None,
) -> list[dict[str, object]]:
    if quantity <= 0 or not is_special_item(item_key):
        return []
    owner_name, _room_key = _character_snapshot_in_connection(db, character_id)
    destination = holder or HeritageHolder.character(character_id)
    created: list[dict[str, object]] = []
    for _ in range(int(quantity)):
        ordinal = _next_discovery_ordinal(db, item_key)
        origin = origin_text or f"First recorded in the possession of {owner_name}."
        entry = _insert_instance_in_connection(
            db,
            item_key=item_key,
            heritage_kind="special",
            owner_character_id=int(character_id),
            holder=destination,
            discovery_ordinal=ordinal,
            discovery_exact=discovery_exact,
            origin_text=origin,
        )
        _event_in_connection(
            db,
            instance_id=int(entry["id"]),
            event_type="found" if discovery_exact else "legacy_registered",
            actor_character_id=int(character_id),
            from_owner_character_id=None,
            to_owner_character_id=int(character_id),
            from_holder=None,
            to_holder=destination,
            note=origin,
        )
        created.append(entry)
    return created


def chronicle_first_discoveries(database, entries: Iterable[dict[str, object]]) -> None:
    if not FIRST_DISCOVERY_CHRONICLE:
        return
    firsts = [entry for entry in entries if entry.get("discovery_ordinal") == 1 and entry.get("discovery_exact")]
    if not firsts:
        return
    try:
        from mud.living_world import _chronicle_insert
    except Exception:
        return
    moment = ASTRALIS_CLOCK.now()
    for entry in firsts:
        instance_id = int(entry["id"])
        with database.connect() as db:
            row = db.execute(
                """
                SELECT h.item_key, h.current_owner_character_id, c.name AS owner_name
                FROM item_heritage_instances h
                LEFT JOIN characters c ON c.id = h.current_owner_character_id
                WHERE h.id = ?
                """,
                (instance_id,),
            ).fetchone()
        if row is None:
            continue
        owner_name = str(row["owner_name"] or "An unknown traveler")
        key = str(row["item_key"])
        _chronicle_insert(
            database,
            event_key=f"heritage:first:{key}",
            day=int(moment.day_number),
            category="item_heritage",
            character_id=row["current_owner_character_id"],
            character_name=owner_name,
            text=f"{owner_name} recorded the first known discovery of {item_name(key)}.",
        )


def special_found_total(database, item_key: str) -> int:
    ensure_item_heritage_schema(database)
    with database.connect() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS n
            FROM item_heritage_instances
            WHERE item_key = ? AND discovery_ordinal IS NOT NULL
            """,
            (item_key,),
        ).fetchone()
    return 0 if row is None else int(row["n"])


def _holder_where(holder: HeritageHolder) -> tuple[str, tuple[object, ...]]:
    if holder.reservation is None:
        return "holder_kind = ? AND holder_key = ?", (holder.kind, holder.key)
    return (
        "holder_kind = ? AND holder_key = ? AND holder_reservation = ?",
        (holder.kind, holder.key, int(holder.reservation)),
    )


def _instances_at_holder_in_connection(
    db,
    *,
    holder: HeritageHolder,
    item_key: str,
    owner_character_id: int | None = None,
) -> list:
    where, params = _holder_where(holder)
    owner_sql = ""
    owner_params: tuple[object, ...] = ()
    if owner_character_id is not None:
        owner_sql = " AND current_owner_character_id = ?"
        owner_params = (int(owner_character_id),)
    return db.execute(
        f"""
        SELECT *
        FROM item_heritage_instances
        WHERE {where} AND item_key = ?{owner_sql}
        ORDER BY id
        """,
        (*params, item_key, *owner_params),
    ).fetchall()


def ensure_special_inventory_item(database, character_id: int, item_key: str) -> list[dict[str, object]]:
    if not is_special_item(item_key):
        return []
    ensure_item_heritage_schema(database)
    inventory_quantity = database.item_quantity(character_id, item_key)
    if inventory_quantity <= 0:
        return []
    holder = HeritageHolder.character(character_id)
    with database.connect() as db:
        existing = _instances_at_holder_in_connection(
            db,
            holder=holder,
            item_key=item_key,
            owner_character_id=character_id,
        )
    missing = max(0, inventory_quantity - len(existing))
    if missing <= 0:
        return []
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        created = record_special_acquisition_in_connection(
            db,
            character_id=character_id,
            item_key=item_key,
            quantity=missing,
            origin_text=(
                "Registered from an existing inventory when item heritage tracking began. "
                "The exact original discovery order predates the registry."
            ),
            discovery_exact=False,
        )
    return created


def synchronize_character_heritage(database, character_id: int) -> None:
    ensure_item_heritage_schema(database)
    for row in database.list_items(character_id):
        key = str(row["item_key"])
        if is_special_item(key):
            ensure_special_inventory_item(database, character_id, key)


def _source_origin_in_connection(db, holder: HeritageHolder, item_key: str) -> str:
    if holder.kind == "container":
        row = db.execute(
            "SELECT source_key, source_name, name FROM world_containers WHERE id = ?",
            (int(holder.key),),
        ).fetchone()
        if row is not None:
            source_name = str(row["source_name"] or row["name"] or "a world container")
            return f"Recovered from {source_name}."
    if holder.kind == "room":
        return f"Picked up in {holder.key.replace('_', ' ')}."
    return f"Acquired {item_name(item_key)}."


def move_location_instances_in_connection(
    db,
    *,
    source: HeritageHolder,
    destination: HeritageHolder,
    item_key: str,
    quantity: int,
) -> list[dict[str, object]]:
    if quantity <= 0:
        return []
    from_owner = int(source.key) if source.kind == "character" and source.key.isdigit() else None
    to_owner = int(destination.key) if destination.kind == "character" and destination.key.isdigit() else None
    rows = _instances_at_holder_in_connection(
        db,
        holder=source,
        item_key=item_key,
        owner_character_id=from_owner,
    )
    moved_rows = rows[: int(quantity)]
    results: list[dict[str, object]] = []
    for row in moved_rows:
        previous_owner = row["current_owner_character_id"]
        db.execute(
            """
            UPDATE item_heritage_instances
            SET current_owner_character_id = ?,
                holder_kind = ?, holder_key = ?, holder_reservation = ?
            WHERE id = ?
            """,
            (
                to_owner,
                destination.kind,
                destination.key,
                destination.reservation,
                int(row["id"]),
            ),
        )
        event_type = "transferred"
        if source.kind == "character" and destination.kind == "room":
            event_type = "dropped"
        elif source.kind == "room" and destination.kind == "character":
            event_type = "picked_up"
        elif source.kind == "container" and destination.kind == "character":
            event_type = "looted"
        _event_in_connection(
            db,
            instance_id=int(row["id"]),
            event_type=event_type,
            actor_character_id=to_owner if to_owner is not None else from_owner,
            from_owner_character_id=None if previous_owner is None else int(previous_owner),
            to_owner_character_id=to_owner,
            from_holder=source,
            to_holder=destination,
            note=(
                f"{item_name(item_key)} moved from {source.kind} to {destination.kind}."
            ),
        )
        results.append(
            {
                "id": int(row["id"]),
                "serial": str(row["serial"]),
                "item_key": item_key,
                "discovery_ordinal": row["discovery_ordinal"],
                "discovery_exact": bool(row["discovery_exact"]),
            }
        )

    missing = int(quantity) - len(moved_rows)
    if missing > 0 and to_owner is not None and is_special_item(item_key):
        results.extend(
            record_special_acquisition_in_connection(
                db,
                character_id=to_owner,
                item_key=item_key,
                quantity=missing,
                origin_text=_source_origin_in_connection(db, source, item_key),
                discovery_exact=True,
                holder=destination,
            )
        )
    return results


def transfer_owned_instances_in_connection(
    db,
    *,
    from_character_id: int,
    to_character_id: int,
    item_key: str,
    quantity: int,
    event_type: str = "trade",
    note: str = "",
) -> list[int]:
    if quantity <= 0:
        return []
    source = HeritageHolder.character(from_character_id)
    destination = HeritageHolder.character(to_character_id)
    rows = _instances_at_holder_in_connection(
        db,
        holder=source,
        item_key=item_key,
        owner_character_id=from_character_id,
    )[: int(quantity)]
    moved: list[int] = []
    for row in rows:
        db.execute(
            """
            UPDATE item_heritage_instances
            SET current_owner_character_id = ?, holder_kind = ?, holder_key = ?, holder_reservation = NULL
            WHERE id = ?
            """,
            (int(to_character_id), destination.kind, destination.key, int(row["id"])),
        )
        _event_in_connection(
            db,
            instance_id=int(row["id"]),
            event_type=event_type,
            actor_character_id=from_character_id,
            from_owner_character_id=from_character_id,
            to_owner_character_id=to_character_id,
            from_holder=source,
            to_holder=destination,
            note=note or f"Transferred from one player to another by {event_type}.",
        )
        moved.append(int(row["id"]))
    return moved


def move_owned_to_holder_in_connection(
    db,
    *,
    character_id: int,
    item_key: str,
    quantity: int,
    destination: HeritageHolder,
    event_type: str,
    note: str,
    keep_owner: bool = True,
) -> list[int]:
    source = HeritageHolder.character(character_id)
    rows = _instances_at_holder_in_connection(
        db,
        holder=source,
        item_key=item_key,
        owner_character_id=character_id,
    )[: int(quantity)]
    moved: list[int] = []
    for row in rows:
        to_owner = int(character_id) if keep_owner else None
        db.execute(
            """
            UPDATE item_heritage_instances
            SET current_owner_character_id = ?, holder_kind = ?, holder_key = ?, holder_reservation = ?
            WHERE id = ?
            """,
            (to_owner, destination.kind, destination.key, destination.reservation, int(row["id"])),
        )
        _event_in_connection(
            db,
            instance_id=int(row["id"]),
            event_type=event_type,
            actor_character_id=character_id,
            from_owner_character_id=character_id,
            to_owner_character_id=to_owner,
            from_holder=source,
            to_holder=destination,
            note=note,
        )
        moved.append(int(row["id"]))
    return moved


def move_holder_to_owner_in_connection(
    db,
    *,
    source: HeritageHolder,
    character_id: int,
    item_key: str,
    quantity: int,
    event_type: str,
    note: str,
) -> list[int]:
    rows = _instances_at_holder_in_connection(db, holder=source, item_key=item_key)[: int(quantity)]
    destination = HeritageHolder.character(character_id)
    moved: list[int] = []
    for row in rows:
        previous_owner = row["current_owner_character_id"]
        db.execute(
            """
            UPDATE item_heritage_instances
            SET current_owner_character_id = ?, holder_kind = ?, holder_key = ?, holder_reservation = NULL
            WHERE id = ?
            """,
            (int(character_id), destination.kind, destination.key, int(row["id"])),
        )
        _event_in_connection(
            db,
            instance_id=int(row["id"]),
            event_type=event_type,
            actor_character_id=character_id,
            from_owner_character_id=None if previous_owner is None else int(previous_owner),
            to_owner_character_id=character_id,
            from_holder=source,
            to_holder=destination,
            note=note,
        )
        moved.append(int(row["id"]))
    return moved


def retire_owned_instances_in_connection(
    db,
    *,
    character_id: int,
    item_key: str,
    quantity: int,
    event_type: str,
    note: str,
) -> list[int]:
    source = HeritageHolder.character(character_id)
    rows = _instances_at_holder_in_connection(
        db,
        holder=source,
        item_key=item_key,
        owner_character_id=character_id,
    )[: int(quantity)]
    retired: list[int] = []
    destination = HeritageHolder.retired(event_type)
    for row in rows:
        db.execute(
            """
            UPDATE item_heritage_instances
            SET current_owner_character_id = NULL,
                holder_kind = ?, holder_key = ?, holder_reservation = NULL
            WHERE id = ?
            """,
            (destination.kind, destination.key, int(row["id"])),
        )
        _event_in_connection(
            db,
            instance_id=int(row["id"]),
            event_type=event_type,
            actor_character_id=character_id,
            from_owner_character_id=character_id,
            to_owner_character_id=None,
            from_holder=source,
            to_holder=destination,
            note=note,
        )
        retired.append(int(row["id"]))
    return retired


def owned_heritage_rows(database, character_id: int, item_key: str, *, carried_only: bool = False) -> list:
    ensure_item_heritage_schema(database)
    with database.connect() as db:
        if carried_only:
            return db.execute(
                """
                SELECT * FROM item_heritage_instances
                WHERE current_owner_character_id = ? AND item_key = ?
                  AND holder_kind = 'character' AND holder_key = ?
                ORDER BY id
                """,
                (int(character_id), item_key, str(int(character_id))),
            ).fetchall()
        return db.execute(
            """
            SELECT * FROM item_heritage_instances
            WHERE current_owner_character_id = ? AND item_key = ?
            ORDER BY id
            """,
            (int(character_id), item_key),
        ).fetchall()


def _maker_mark(row) -> str:
    if row["maker_name"] is None or row["maker_sequence"] is None:
        return ""
    return f"{row['maker_name']}'s #{int(row['maker_sequence'])} {item_name(str(row['item_key']))}"


def heritage_summary_data(database, character_id: int, item_key: str) -> dict[str, object]:
    rows = owned_heritage_rows(database, character_id, item_key, carried_only=True)
    total = special_found_total(database, item_key) if is_special_item(item_key) else 0
    return {
        "tracked": len(rows),
        "serials": [str(row["serial"]) for row in rows],
        "maker_marks": [_maker_mark(row) for row in rows if row["maker_sequence"] is not None],
        "discoveries": [
            {
                "ordinal": int(row["discovery_ordinal"]),
                "exact": bool(row["discovery_exact"]),
                "total": total,
            }
            for row in rows
            if row["discovery_ordinal"] is not None
        ],
        "special_total": total,
    }


def heritage_inventory_summaries(database, character_id: int) -> dict[str, dict[str, object]]:
    """Return all carried heritage in two SQL reads for frequent client snapshots."""
    ensure_item_heritage_schema(database)
    holder_key = str(int(character_id))
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT *
            FROM item_heritage_instances
            WHERE current_owner_character_id = ?
              AND holder_kind = 'character'
              AND holder_key = ?
            ORDER BY item_key, id
            """,
            (int(character_id), holder_key),
        ).fetchall()
        totals = db.execute(
            """
            SELECT item_key, COUNT(*) AS n
            FROM item_heritage_instances
            WHERE discovery_ordinal IS NOT NULL
            GROUP BY item_key
            """
        ).fetchall()

    total_by_key = {str(row["item_key"]): int(row["n"]) for row in totals}
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(str(row["item_key"]), []).append(row)

    result: dict[str, dict[str, object]] = {}
    for item_key, item_rows in grouped.items():
        total = total_by_key.get(item_key, 0)
        result[item_key] = {
            "tracked": len(item_rows),
            "serials": [str(row["serial"]) for row in item_rows],
            "maker_marks": [
                _maker_mark(row)
                for row in item_rows
                if row["maker_sequence"] is not None
            ],
            "discoveries": [
                {
                    "ordinal": int(row["discovery_ordinal"]),
                    "exact": bool(row["discovery_exact"]),
                    "total": total,
                }
                for row in item_rows
                if row["discovery_ordinal"] is not None
            ],
            "special_total": total,
        }
    return result


def compact_heritage_lines(database, character_id: int, item_key: str) -> tuple[str, ...]:
    if is_special_item(item_key):
        ensure_special_inventory_item(database, character_id, item_key)
    rows = owned_heritage_rows(database, character_id, item_key, carried_only=True)
    if not rows:
        return ()
    lines: list[str] = []
    crafted = [row for row in rows if row["maker_sequence"] is not None]
    if len(crafted) == 1:
        row = crafted[0]
        lines.append(f"Maker's mark: {_maker_mark(row)} [{row['serial']}]")
    elif crafted:
        sequences = ", ".join(
            f"{row['maker_name']} #{int(row['maker_sequence'])}"
            for row in crafted[:4]
        )
        suffix = "" if len(crafted) <= 4 else f", +{len(crafted) - 4} more"
        lines.append(f"Maker's marks: {sequences}{suffix}.")
    discoveries = [row for row in rows if row["discovery_ordinal"] is not None]
    if discoveries:
        total = special_found_total(database, item_key)
        if len(discoveries) == 1:
            row = discoveries[0]
            if bool(row["discovery_exact"]):
                lines.append(
                    f"Discovery: #{int(row['discovery_ordinal'])} of {total} ever found."
                )
            else:
                lines.append(
                    f"Heritage registry: #{int(row['discovery_ordinal'])} of {total} known; "
                    "this copy predates exact discovery-order tracking."
                )
        else:
            labels = ", ".join(f"#{int(row['discovery_ordinal'])}" for row in discoveries[:6])
            suffix = "" if len(discoveries) <= 6 else f", +{len(discoveries) - 6} more"
            lines.append(f"Special-item discoveries carried: {labels}{suffix}; {total} ever found.")
    lines.append("Use PROVENANCE <item> for the full heritage record.")
    return tuple(lines)


def _events_for_instance(database, instance_id: int) -> list:
    ensure_item_heritage_schema(database)
    with database.connect() as db:
        return db.execute(
            """
            SELECT *
            FROM item_heritage_events
            WHERE instance_id = ?
            ORDER BY id
            """,
            (int(instance_id),),
        ).fetchall()


def _display_room_key(room_key: str | None) -> str:
    if not room_key:
        return "an unrecorded location"
    return str(room_key).replace("_", " ").title()


def render_provenance(database, character_id: int, item_key: str, *, serial: str | None = None) -> str:
    if is_special_item(item_key):
        ensure_special_inventory_item(database, character_id, item_key)
    rows = owned_heritage_rows(database, character_id, item_key)
    if serial is not None:
        rows = [row for row in rows if str(row["serial"]).casefold() == serial.casefold()]
    if not rows:
        return (
            f"{item_name(item_key)} has no individual heritage record. Ordinary found and purchased items "
            "remain anonymous unless they are player-crafted gear or an explicitly tracked special item."
        )

    total = special_found_total(database, item_key) if is_special_item(item_key) else 0
    lines = [f"--- Provenance: {item_name(item_key)} ---"]
    for index, row in enumerate(rows, start=1):
        if len(rows) > 1:
            lines.append(f"Copy {index} of {len(rows)}")
        lines.append(f"Serial: {row['serial']}")
        if row["maker_sequence"] is not None:
            lines.append(f"Maker's mark: {_maker_mark(row)}")
            lines.append(
                f"Crafted: Astralis Day {int(row['crafted_day']) if row['crafted_day'] is not None else '?'} "
                f"at {_display_room_key(row['crafted_room_key'])}"
            )
            lines.append(
                f"Recipe: {row['recipe_key'] or 'unknown'} | Profession: {row['profession_key'] or 'unknown'} | "
                f"recipe version {row['recipe_version'] or '?'} / revision {row['recipe_revision'] or 'unknown'}"
            )
            lines.append("Quality: high-quality result" if bool(row["high_quality"]) else "Quality: standard result")
        if row["discovery_ordinal"] is not None:
            ordinal = int(row["discovery_ordinal"])
            if bool(row["discovery_exact"]):
                lines.append(f"Discovery: #{ordinal} of {total} ever found.")
                lines.append(
                    f"#{ordinal} is permanent for this copy. The live total {total} only rises when another copy is found."
                )
            else:
                lines.append(
                    f"Heritage registry: #{ordinal} of {total} known. This copy existed before exact "
                    "discovery-order tracking, so its historical find position cannot be guaranteed."
                )
        if row["origin_text"]:
            lines.append(f"Origin: {row['origin_text']}")
        events = _events_for_instance(database, int(row["id"]))
        if events:
            lines.append("History:")
            for event in events:
                from_name = event["from_owner_name"] or "unowned"
                to_name = event["to_owner_name"] or "unowned"
                ownership = ""
                if from_name != to_name:
                    ownership = f" {from_name} -> {to_name}."
                note = str(event["note"] or "").strip()
                lines.append(
                    f"  Day {int(event['astralis_day'])}: {str(event['event_type']).replace('_', ' ')}."
                    f"{ownership}" + (f" {note}" if note else "")
                )
        if index != len(rows):
            lines.append("")
    return "\r\n".join(lines)


def resolve_inventory_item(session, target: str) -> tuple[str | None, str | None]:
    character = getattr(session, "character", None)
    if character is None:
        return None, "No active character."
    wanted = _normalize(target)
    if not wanted:
        return None, "Name an item."
    exact: list[str] = []
    partial: list[str] = []
    for row in session.database.list_items(character.id):
        key = str(row["item_key"])
        if int(row["quantity"]) <= 0:
            continue
        aliases = {_normalize(key), _normalize(item_name(key))}
        if wanted in aliases:
            exact.append(key)
        elif any(wanted in alias for alias in aliases):
            partial.append(key)
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, None
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(item_name(key) for key in matches) + "."
    return matches[0], None


def resolve_owned_serial(database, character_id: int, target: str) -> tuple[str, str] | None:
    ensure_item_heritage_schema(database)
    wanted = target.strip().upper()
    if not wanted:
        return None
    with database.connect() as db:
        row = db.execute(
            """
            SELECT item_key, serial
            FROM item_heritage_instances
            WHERE current_owner_character_id = ? AND UPPER(serial) = ?
            """,
            (int(character_id), wanted),
        ).fetchone()
    if row is None:
        return None
    return str(row["item_key"]), str(row["serial"])


def audit_item_heritage(database) -> tuple[str, ...]:
    ensure_item_heritage_schema(database)
    issues: list[str] = []
    with database.connect() as db:
        duplicates = db.execute(
            """
            SELECT serial, COUNT(*) AS n
            FROM item_heritage_instances
            WHERE serial IS NOT NULL
            GROUP BY serial HAVING COUNT(*) > 1
            """
        ).fetchall()
        for row in duplicates:
            issues.append(f"Duplicate heritage serial {row['serial']} ({int(row['n'])} rows).")

        discovery_dupes = db.execute(
            """
            SELECT item_key, discovery_ordinal, COUNT(*) AS n
            FROM item_heritage_instances
            WHERE discovery_ordinal IS NOT NULL
            GROUP BY item_key, discovery_ordinal HAVING COUNT(*) > 1
            """
        ).fetchall()
        for row in discovery_dupes:
            issues.append(
                f"Duplicate discovery #{int(row['discovery_ordinal'])} for {row['item_key']}."
            )

        discovery_groups = db.execute(
            """
            SELECT item_key, COUNT(*) AS n, MAX(discovery_ordinal) AS maximum
            FROM item_heritage_instances
            WHERE discovery_ordinal IS NOT NULL
            GROUP BY item_key
            """
        ).fetchall()
        for row in discovery_groups:
            if int(row["n"]) != int(row["maximum"]):
                issues.append(
                    f"Discovery sequence for {row['item_key']} has a gap: "
                    f"{int(row['n'])} records through #{int(row['maximum'])}."
                )

        held = db.execute(
            """
            SELECT current_owner_character_id AS character_id, item_key, COUNT(*) AS n
            FROM item_heritage_instances
            WHERE holder_kind = 'character' AND current_owner_character_id IS NOT NULL
            GROUP BY current_owner_character_id, item_key
            """
        ).fetchall()
        for row in held:
            inventory = db.execute(
                "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                (int(row["character_id"]), str(row["item_key"])),
            ).fetchone()
            quantity = 0 if inventory is None else int(inventory["quantity"])
            if int(row["n"]) > quantity:
                issues.append(
                    f"Heritage ownership mismatch: character {int(row['character_id'])} has "
                    f"{int(row['n'])} tracked {row['item_key']} instances but only {quantity} in inventory."
                )

        instances = db.execute(
            "SELECT id, serial, current_owner_character_id FROM item_heritage_instances ORDER BY id"
        ).fetchall()
        for instance in instances:
            events = db.execute(
                """
                SELECT from_owner_character_id, to_owner_character_id
                FROM item_heritage_events
                WHERE instance_id = ? ORDER BY id
                """,
                (int(instance["id"]),),
            ).fetchall()
            expected = None
            for event_index, event in enumerate(events):
                from_owner = event["from_owner_character_id"]
                if event_index > 0 and from_owner != expected:
                    issues.append(
                        f"Broken ownership chain for {instance['serial']} before event {event_index + 1}."
                    )
                    break
                expected = event["to_owner_character_id"]
            if events and expected != instance["current_owner_character_id"]:
                issues.append(
                    f"Current owner mismatch for {instance['serial']}: history and registry disagree."
                )

    return tuple(issues)


def _session_is_staff(session) -> bool:
    if not bool(getattr(session, "_staff_mode", False)):
        return False
    account = getattr(session, "account", None)
    database = getattr(session, "database", None)
    if account is None or database is None:
        return False
    try:
        with database.connect() as db:
            row = db.execute(
                "SELECT role FROM staff_roles WHERE account_id = ?",
                (int(account.id),),
            ).fetchone()
    except Exception:
        return False
    if row is None:
        return False
    return str(row["role"]).strip().lower() in {"helper", "gm", "builder", "admin", "owner"}


async def _delegate(self, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    self.prompt = replay
    try:
        await previous_prompt(self)
    finally:
        if had_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_item_heritage_runtime(player_session_class, world_service=None) -> None:
    if getattr(player_session_class, "_item_heritage_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is None:
            return
        ensure_item_heritage_schema(self.database)
        synchronize_character_heritage(self.database, self.character.id)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"provenance audit", "heritage audit"} and _session_is_staff(self):
            issues = audit_item_heritage(self.database)
            await self.send("\r\n--- Item Heritage Audit ---\r\n")
            if not issues:
                await self.send("No duplicate serials, discovery gaps, inventory mismatches, or broken ownership chains detected.\r\n")
            else:
                for issue in issues[:100]:
                    await self.send(" - " + issue + "\r\n")
            return

        prefix = None
        if normalized.startswith("provenance "):
            prefix = "provenance "
        elif normalized.startswith("heritage "):
            prefix = "heritage "
        if prefix is not None:
            target = stripped[len(prefix):].strip()
            serial_match = resolve_owned_serial(self.database, self.character.id, target)
            if serial_match is not None:
                key, serial = serial_match
                await self.send("\r\n" + render_provenance(self.database, self.character.id, key, serial=serial) + "\r\n")
                return

            key, error = resolve_inventory_item(self, target)
            if error:
                await self.send(error + "\r\n")
                return
            if key is not None:
                try:
                    from mud.style_collectibles import STYLE_META_BY_KEY

                    if key in STYLE_META_BY_KEY and not owned_heritage_rows(self.database, self.character.id, key):
                        delegated = command
                        if prefix == "heritage ":
                            delegated = "PROVENANCE " + target
                        await _delegate(self, previous_prompt, delegated)
                        return
                except Exception:
                    pass
                await self.send("\r\n" + render_provenance(self.database, self.character.id, key) + "\r\n")
                return

        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._item_heritage_runtime_installed = True
