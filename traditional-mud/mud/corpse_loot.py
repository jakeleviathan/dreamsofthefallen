from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from random import randint, random
from time import time

import mud.crafting as crafting
import mud.economy_balance as economy_balance
import mud.economy_loop as economy
import mud.enemy_lifecycle as enemy_lifecycle


CORPSE_TTL_SECONDS = 15 * 60

CORPSE_STORAGE_SQL = """
CREATE TABLE IF NOT EXISTS room_corpses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_key TEXT NOT NULL,
    enemy_key TEXT NOT NULL,
    enemy_name TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_room_corpses_room_created
    ON room_corpses (room_key, created_at DESC);

CREATE TABLE IF NOT EXISTS corpse_items (
    corpse_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reserved_character_id INTEGER NOT NULL,
    PRIMARY KEY (corpse_id, item_key, reserved_character_id),
    FOREIGN KEY (corpse_id) REFERENCES room_corpses(id) ON DELETE CASCADE
);
"""


@dataclass(frozen=True, slots=True)
class LootTableEntry:
    """One independently rolled entry in an NPC loot table.

    chance is expressed from 0.0 through 1.0. Quantity is rolled inclusively
    between min_quantity and max_quantity after the chance succeeds.
    """

    item_key: str
    chance: float = 1.0
    min_quantity: int = 1
    max_quantity: int = 1

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.chance) <= 1.0:
            raise ValueError("Loot chance must be between 0.0 and 1.0.")
        if int(self.min_quantity) <= 0:
            raise ValueError("Loot minimum quantity must be positive.")
        if int(self.max_quantity) < int(self.min_quantity):
            raise ValueError("Loot maximum quantity cannot be below its minimum.")

    @property
    def chance_percent(self) -> float:
        return self.chance * 100.0


@dataclass(frozen=True, slots=True)
class CorpseRecord:
    id: int
    room_key: str
    enemy_key: str
    enemy_name: str
    created_at: float
    expires_at: float


@dataclass(frozen=True, slots=True)
class CorpseItem:
    item_key: str
    quantity: int
    reserved_character_id: int


@dataclass(slots=True)
class _PendingDrop:
    item_key: str
    quantity: int
    reserved_character_id: int
    recipient_session: object | None = None


@dataclass(slots=True)
class _DefeatLootContext:
    session: object
    enemy_object_id: int
    room_key: str
    enemy_key: str
    enemy_name: str
    drops: list[_PendingDrop] = field(default_factory=list)
    loot_rolled: bool = False
    lifecycle_claimed: bool | None = None


# New content may define an explicit table here instead of adding another combat
# special case. Existing economy tables are adapted automatically when a key has
# no explicit override, so older authored content keeps working unchanged.
NPC_LOOT_TABLES: dict[str, tuple[LootTableEntry, ...]] = {}

_DEFEAT_CONTEXT: ContextVar[_DefeatLootContext | None] = ContextVar(
    "dreams_corpse_loot_defeat_context",
    default=None,
)

_LOOT_HOOKS_CAPTURED = False
_ORIGINAL_BASE_AWARD = None
_ORIGINAL_SECONDARY_AWARD = None
_ORIGINAL_MARK_STATIC_DEFEATED = None


def register_loot_table(enemy_key: str, entries: tuple[LootTableEntry, ...]) -> None:
    """Register or replace one NPC's complete independently rolled loot table."""
    clean_key = str(enemy_key).strip()
    if not clean_key:
        raise ValueError("Enemy key is required for a loot table.")
    NPC_LOOT_TABLES[clean_key] = tuple(entries)


def ensure_corpse_storage(database) -> None:
    with database.connect() as db:
        db.executescript(CORPSE_STORAGE_SQL)


def _prune_expired_corpses(database, *, now: float | None = None) -> None:
    ensure_corpse_storage(database)
    current = time() if now is None else float(now)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        expired = db.execute(
            "SELECT id FROM room_corpses WHERE expires_at <= ?",
            (current,),
        ).fetchall()
        corpse_ids = [int(row["id"]) for row in expired]
        for corpse_id in corpse_ids:
            db.execute("DELETE FROM corpse_items WHERE corpse_id = ?", (corpse_id,))
        db.execute("DELETE FROM room_corpses WHERE expires_at <= ?", (current,))


def create_corpse(
    database,
    room_key: str,
    enemy_key: str,
    enemy_name: str,
    *,
    created_at: float | None = None,
    ttl_seconds: float = CORPSE_TTL_SECONDS,
) -> int:
    ensure_corpse_storage(database)
    created = time() if created_at is None else float(created_at)
    expires = created + max(1.0, float(ttl_seconds))
    with database.connect() as db:
        cursor = db.execute(
            """
            INSERT INTO room_corpses (room_key, enemy_key, enemy_name, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (room_key, enemy_key, enemy_name, created, expires),
        )
        return int(cursor.lastrowid)


def add_corpse_item(
    database,
    corpse_id: int,
    item_key: str,
    quantity: int,
    reserved_character_id: int,
) -> None:
    if quantity <= 0:
        return
    ensure_corpse_storage(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO corpse_items (corpse_id, item_key, quantity, reserved_character_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(corpse_id, item_key, reserved_character_id) DO UPDATE SET
                quantity = quantity + excluded.quantity
            """,
            (corpse_id, item_key, int(quantity), int(reserved_character_id)),
        )


def list_corpses(database, room_key: str) -> list[CorpseRecord]:
    _prune_expired_corpses(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT id, room_key, enemy_key, enemy_name, created_at, expires_at
            FROM room_corpses
            WHERE room_key = ?
            ORDER BY created_at DESC, id DESC
            """,
            (room_key,),
        ).fetchall()
    return [
        CorpseRecord(
            id=int(row["id"]),
            room_key=str(row["room_key"]),
            enemy_key=str(row["enemy_key"]),
            enemy_name=str(row["enemy_name"]),
            created_at=float(row["created_at"]),
            expires_at=float(row["expires_at"]),
        )
        for row in rows
    ]


def list_corpse_items(database, corpse_id: int) -> list[CorpseItem]:
    ensure_corpse_storage(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT item_key, quantity, reserved_character_id
            FROM corpse_items
            WHERE corpse_id = ? AND quantity > 0
            ORDER BY item_key, reserved_character_id
            """,
            (int(corpse_id),),
        ).fetchall()
    return [
        CorpseItem(
            item_key=str(row["item_key"]),
            quantity=int(row["quantity"]),
            reserved_character_id=int(row["reserved_character_id"]),
        )
        for row in rows
    ]


def _delete_corpse_if_empty(db, corpse_id: int) -> None:
    row = db.execute(
        "SELECT 1 FROM corpse_items WHERE corpse_id = ? AND quantity > 0 LIMIT 1",
        (int(corpse_id),),
    ).fetchone()
    if row is None:
        db.execute("DELETE FROM room_corpses WHERE id = ?", (int(corpse_id),))


def transfer_all_corpse_loot_to_inventory(
    database,
    character_id: int,
    corpse_id: int,
) -> list[CorpseItem]:
    """Atomically move every item reserved for this character into inventory."""
    ensure_corpse_storage(database)
    moved: list[CorpseItem] = []
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        rows = db.execute(
            """
            SELECT item_key, quantity, reserved_character_id
            FROM corpse_items
            WHERE corpse_id = ? AND reserved_character_id = ? AND quantity > 0
            ORDER BY item_key
            """,
            (int(corpse_id), int(character_id)),
        ).fetchall()
        for row in rows:
            item_key = str(row["item_key"])
            quantity = int(row["quantity"])
            db.execute(
                """
                INSERT INTO character_items (character_id, item_key, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(character_id, item_key) DO UPDATE SET
                    quantity = quantity + excluded.quantity
                """,
                (int(character_id), item_key, quantity),
            )
            moved.append(
                CorpseItem(
                    item_key=item_key,
                    quantity=quantity,
                    reserved_character_id=int(character_id),
                )
            )
        if rows:
            db.execute(
                "DELETE FROM corpse_items WHERE corpse_id = ? AND reserved_character_id = ?",
                (int(corpse_id), int(character_id)),
            )
        _delete_corpse_if_empty(db, corpse_id)
    return moved


def transfer_corpse_item_to_inventory(
    database,
    character_id: int,
    corpse_id: int,
    item_key: str,
    quantity: int = 1,
) -> bool:
    """Atomically move one reserved corpse stack, or part of it, into inventory."""
    if quantity <= 0:
        raise ValueError("Loot quantity must be positive.")
    ensure_corpse_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT quantity
            FROM corpse_items
            WHERE corpse_id = ? AND item_key = ? AND reserved_character_id = ?
            """,
            (int(corpse_id), item_key, int(character_id)),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            return False

        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute(
                """
                UPDATE corpse_items
                SET quantity = ?
                WHERE corpse_id = ? AND item_key = ? AND reserved_character_id = ?
                """,
                (remaining, int(corpse_id), item_key, int(character_id)),
            )
        else:
            db.execute(
                """
                DELETE FROM corpse_items
                WHERE corpse_id = ? AND item_key = ? AND reserved_character_id = ?
                """,
                (int(corpse_id), item_key, int(character_id)),
            )

        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET
                quantity = quantity + excluded.quantity
            """,
            (int(character_id), item_key, int(quantity)),
        )
        _delete_corpse_if_empty(db, corpse_id)
    return True


def _normalize(text: str) -> str:
    return " ".join(str(text).strip().lower().replace("_", " ").split())


def _item_name(item_key: str) -> str:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    return definition.name if definition is not None else item_key.replace("_", " ").title()


def _item_aliases(item_key: str) -> tuple[str, ...]:
    names = {_normalize(item_key)}
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    if definition is not None:
        names.add(_normalize(definition.name))
    return tuple(names)


def _corpse_target_text(target: str) -> str:
    value = _normalize(target)
    if value.startswith("corpse of "):
        value = value[len("corpse of "):]
    elif value.startswith("body of "):
        value = value[len("body of "):]
    elif value.startswith("remains of "):
        value = value[len("remains of "):]
    for suffix in (" corpse", " body", " remains"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].strip()
            break
    return value


def _resolve_corpse(database, room_key: str, target: str) -> CorpseRecord | None:
    corpses = list_corpses(database, room_key)
    if not corpses:
        return None
    wanted = _normalize(target)
    if wanted in {"", "corpse", "body", "remains", "the corpse", "the body", "the remains"}:
        return corpses[0]

    wanted_enemy = _corpse_target_text(wanted)
    exact: list[CorpseRecord] = []
    partial: list[CorpseRecord] = []
    for corpse in corpses:
        aliases = {
            _normalize(corpse.enemy_key),
            _normalize(corpse.enemy_name),
        }
        if wanted_enemy in aliases:
            exact.append(corpse)
        elif any(wanted_enemy and wanted_enemy in alias for alias in aliases):
            partial.append(corpse)
    if exact:
        return exact[0]
    if partial:
        return partial[0]
    return None


def _resolve_corpse_item(items: list[CorpseItem], target: str) -> tuple[str | None, tuple[str, ...]]:
    wanted = _normalize(target)
    if not wanted:
        return None, ()
    candidates: list[str] = []
    for row in items:
        aliases = _item_aliases(row.item_key)
        if wanted in aliases:
            return row.item_key, ()
        if any(wanted in alias for alias in aliases):
            candidates.append(row.item_key)
    unique = tuple(dict.fromkeys(candidates))
    if len(unique) == 1:
        return unique[0], ()
    if len(unique) > 1:
        return None, tuple(_item_name(key) for key in unique)
    return None, ()


def _parse_quantity_item(text: str) -> tuple[int | None, str]:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return None, ""
    if parts[0].isdigit():
        if len(parts) == 1:
            return None, ""
        amount = int(parts[0])
        return (amount if amount > 0 else None), parts[1]
    return 1, text.strip()


def loot_table_for_enemy(enemy) -> tuple[LootTableEntry, ...]:
    """Return the live data-driven table for an enemy.

    Explicit NPC_LOOT_TABLES entries are authoritative. Otherwise the legacy
    common-drop and secondary-drop registries are adapted into one table so the
    whole production game receives corpse rolls without rewriting old content.
    """
    definition = getattr(enemy, "definition", None)
    enemy_key = str(getattr(definition, "key", ""))
    if enemy_key in NPC_LOOT_TABLES:
        return NPC_LOOT_TABLES[enemy_key]

    authored = getattr(definition, "loot_table", None)
    if authored:
        result: list[LootTableEntry] = []
        for entry in authored:
            if isinstance(entry, LootTableEntry):
                result.append(entry)
                continue
            if isinstance(entry, dict):
                result.append(LootTableEntry(**entry))
        if result:
            return tuple(result)

    combined: list[LootTableEntry] = []
    for drop in economy._loot_for(enemy):
        combined.append(
            LootTableEntry(
                item_key=drop.item_key,
                chance=1.0,
                min_quantity=max(1, int(drop.quantity)),
                max_quantity=max(1, int(drop.quantity)),
            )
        )
    for drop in economy_balance._secondary_for_enemy(enemy):
        combined.append(
            LootTableEntry(
                item_key=drop.item_key,
                chance=max(0.0, min(1.0, float(drop.chance))),
                min_quantity=max(1, int(drop.quantity)),
                max_quantity=max(1, int(drop.quantity)),
            )
        )
    return tuple(combined)


def roll_loot_table(enemy) -> tuple[tuple[str, int], ...]:
    """Roll every table entry independently and return the successful drops."""
    rolled: list[tuple[str, int]] = []
    for entry in loot_table_for_enemy(enemy):
        if entry.chance <= 0.0:
            continue
        if entry.chance < 1.0 and random() > entry.chance:
            continue
        quantity = randint(entry.min_quantity, entry.max_quantity)
        if quantity > 0:
            rolled.append((entry.item_key, quantity))
    return tuple(rolled)


def _corpse_runtime_enabled(session) -> bool:
    return bool(getattr(type(session), "_corpse_loot_runtime_installed", False))


def _recipient_for_drop(session, enemy, item_key: str):
    try:
        from mud.party_system import _encounter_for, _loot_recipient

        if _encounter_for(enemy) is not None:
            return _loot_recipient(session, enemy, item_key)
    except Exception:
        pass
    return session


async def _award_corpse_loot(session, enemy) -> None:
    global _ORIGINAL_BASE_AWARD
    if not _corpse_runtime_enabled(session):
        if _ORIGINAL_BASE_AWARD is not None:
            await _ORIGINAL_BASE_AWARD(session, enemy)
        return

    context = _DEFEAT_CONTEXT.get()
    if context is None or context.session is not session or context.enemy_object_id != id(enemy):
        return
    if context.loot_rolled:
        return
    context.loot_rolled = True

    for item_key, quantity in roll_loot_table(enemy):
        recipient = _recipient_for_drop(session, enemy, item_key)
        recipient_character = getattr(recipient, "character", None)
        if recipient_character is None:
            recipient = session
            recipient_character = getattr(session, "character", None)
        if recipient_character is None:
            continue
        context.drops.append(
            _PendingDrop(
                item_key=item_key,
                quantity=quantity,
                reserved_character_id=int(recipient_character.id),
                recipient_session=recipient,
            )
        )


async def _suppress_legacy_secondary_award(session, enemy) -> None:
    global _ORIGINAL_SECONDARY_AWARD
    if not _corpse_runtime_enabled(session):
        if _ORIGINAL_SECONDARY_AWARD is not None:
            await _ORIGINAL_SECONDARY_AWARD(session, enemy)
        return
    # Secondary entries were folded into roll_loot_table and rolled exactly once
    # by _award_corpse_loot. This hook intentionally prevents a second roll.
    return


def _mark_static_enemy_defeated_proxy(database, room_key, enemy_key, respawn_seconds, *, now=None):
    assert _ORIGINAL_MARK_STATIC_DEFEATED is not None
    claimed = _ORIGINAL_MARK_STATIC_DEFEATED(
        database,
        room_key,
        enemy_key,
        respawn_seconds,
        now=now,
    )
    context = _DEFEAT_CONTEXT.get()
    if (
        context is not None
        and context.room_key == str(room_key)
        and context.enemy_key == str(enemy_key)
    ):
        context.lifecycle_claimed = bool(claimed)
    return claimed


def _install_loot_hooks() -> None:
    """Redirect the established economy hooks into one corpse roll."""
    global _LOOT_HOOKS_CAPTURED
    global _ORIGINAL_BASE_AWARD, _ORIGINAL_SECONDARY_AWARD, _ORIGINAL_MARK_STATIC_DEFEATED

    if not _LOOT_HOOKS_CAPTURED:
        _ORIGINAL_BASE_AWARD = economy._award_loot
        _ORIGINAL_SECONDARY_AWARD = economy_balance._award_secondary_loot
        _ORIGINAL_MARK_STATIC_DEFEATED = enemy_lifecycle.mark_static_enemy_defeated
        _LOOT_HOOKS_CAPTURED = True

    # Reassert these assignments on every runtime install. Focused tests may
    # install party hooks in a different order; production installs this system
    # at the final policy edge so corpse behavior remains authoritative.
    economy._award_loot = _award_corpse_loot
    economy_balance._award_secondary_loot = _suppress_legacy_secondary_award
    enemy_lifecycle.mark_static_enemy_defeated = _mark_static_enemy_defeated_proxy


def _install_help_catalog() -> None:
    try:
        import mud.command_guide as command_guide
        from mud.command_guide import CommandEntry

        additions = (
            CommandEntry(
                "character",
                "DROP <item> / DROP <quantity> <item>",
                "Leave carried items on the ground in your current room.",
                ("ground", "discard", "leave"),
            ),
            CommandEntry(
                "character",
                "GET / TAKE <ground item>",
                "Pick up an ordinary item lying on the room floor.",
                ("pickup", "ground"),
            ),
            CommandEntry(
                "combat",
                "LOOT CORPSE / LOOT <enemy>",
                "Take every drop assigned to you from the newest matching defeated enemy corpse.",
                ("corpse", "drops", "remains"),
            ),
            CommandEntry(
                "combat",
                "GET / TAKE ALL FROM <corpse or enemy>",
                "Loot all drops assigned to you from a defeated enemy.",
                ("corpse", "loot", "drops"),
            ),
            CommandEntry(
                "combat",
                "GET / TAKE <item> FROM <corpse or enemy>",
                "Take one particular drop, optionally with a quantity, from a corpse.",
                ("corpse", "loot", "item"),
            ),
            CommandEntry(
                "combat",
                "LOOK / EXAMINE CORPSE",
                "Inspect a corpse and see which drops are assigned to you.",
                ("corpse", "body", "remains"),
            ),
        )
        existing = {entry.syntax.casefold() for entry in command_guide.COMMANDS}
        new_entries = tuple(entry for entry in additions if entry.syntax.casefold() not in existing)
        if new_entries:
            command_guide.COMMANDS = command_guide.COMMANDS + new_entries
        command_guide.CATEGORIES = tuple(dict.fromkeys(entry.category for entry in command_guide.COMMANDS))
    except Exception:
        # Help catalog integration should never prevent the game from booting.
        return


def _pending_for_character(context: _DefeatLootContext, character_id: int) -> list[_PendingDrop]:
    return [drop for drop in context.drops if drop.reserved_character_id == int(character_id)]


async def _commit_defeat_corpse(session, context: _DefeatLootContext) -> int | None:
    character = getattr(session, "character", None)
    if character is None:
        return None
    if context.lifecycle_claimed is False:
        # Another session won the shared static-spawn claim. Its kill owns the one
        # corpse and one set of drops; discard this staged roll completely.
        return None

    corpse_id = create_corpse(
        session.database,
        context.room_key,
        context.enemy_key,
        context.enemy_name,
    )
    for drop in context.drops:
        add_corpse_item(
            session.database,
            corpse_id,
            drop.item_key,
            drop.quantity,
            drop.reserved_character_id,
        )

    session._last_defeat_corpse_id = corpse_id
    session._last_defeat_corpse_enemy_key = context.enemy_key
    await session.send(
        f"The corpse of {context.enemy_name} lies here. Type LOOT CORPSE to search it.\r\n"
    )

    notified: set[int] = set()
    for drop in context.drops:
        recipient = drop.recipient_session
        if recipient is None or recipient is session:
            continue
        recipient_character = getattr(recipient, "character", None)
        if recipient_character is None:
            continue
        recipient_id = int(recipient_character.id)
        if recipient_id in notified:
            continue
        notified.add(recipient_id)
        try:
            await recipient.send(
                f"[Party Loot] {context.enemy_name} left loot assigned to you in its corpse. "
                "Type LOOT CORPSE while you are here.\r\n"
            )
        except (ConnectionError, RuntimeError):
            pass
    return corpse_id


async def _show_corpses(session) -> None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return
    corpses = list_corpses(session.database, character.current_room)
    if not corpses:
        return
    await session.send("\r\nRemains:\r\n")
    counts: dict[str, int] = {}
    for corpse in corpses:
        counts[corpse.enemy_name] = counts.get(corpse.enemy_name, 0) + 1
    seen: dict[str, int] = {}
    for corpse in corpses:
        seen[corpse.enemy_name] = seen.get(corpse.enemy_name, 0) + 1
        suffix = f" #{seen[corpse.enemy_name]}" if counts[corpse.enemy_name] > 1 else ""
        await session.send(f"  Corpse of {corpse.enemy_name}{suffix}\r\n")


async def inspect_corpse_command(session, target: str = "corpse") -> None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return
    corpse = _resolve_corpse(session.database, character.current_room, target)
    if corpse is None:
        await session.send("There is no matching corpse here.\r\n")
        return

    items = list_corpse_items(session.database, corpse.id)
    mine = [item for item in items if item.reserved_character_id == int(character.id)]
    others = [item for item in items if item.reserved_character_id != int(character.id)]
    await session.send(f"\r\n--- Corpse of {corpse.enemy_name} ---\r\n")
    if not items:
        await session.send("It holds nothing useful.\r\n")
        return
    if mine:
        await session.send("Your loot:\r\n")
        for item in mine:
            await session.send(f"  {item.quantity}x {_item_name(item.item_key)}\r\n")
    else:
        await session.send("No drops on this corpse are assigned to you.\r\n")
    if others:
        await session.send(
            f"Other party loot: {sum(item.quantity for item in others)} item"
            f"{'s' if sum(item.quantity for item in others) != 1 else ''} reserved for other members.\r\n"
        )


async def loot_all_command(session, target: str = "corpse") -> None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to loot a corpse while fighting.\r\n")
        return

    corpse = _resolve_corpse(session.database, character.current_room, target)
    if corpse is None:
        await session.send("There is no matching corpse here.\r\n")
        return

    before = list_corpse_items(session.database, corpse.id)
    moved = transfer_all_corpse_loot_to_inventory(
        session.database,
        int(character.id),
        corpse.id,
    )
    if moved:
        names = ", ".join(f"{item.quantity}x {_item_name(item.item_key)}" for item in moved)
        await session.send(f"You loot {names} from the corpse of {corpse.enemy_name}.\r\n")
        return

    if not before:
        # Searching an empty corpse consumes it so empty remains do not clutter a
        # busy hunting room for the full expiration window.
        with session.database.connect() as db:
            db.execute("DELETE FROM room_corpses WHERE id = ?", (corpse.id,))
        await session.send(f"You search the corpse of {corpse.enemy_name}, but find nothing useful.\r\n")
        return

    await session.send("Nothing on that corpse is assigned to you.\r\n")


async def loot_item_command(
    session,
    item_text: str,
    corpse_target: str = "corpse",
) -> None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to loot a corpse while fighting.\r\n")
        return

    corpse = _resolve_corpse(session.database, character.current_room, corpse_target)
    if corpse is None:
        await session.send("There is no matching corpse here.\r\n")
        return

    quantity, target = _parse_quantity_item(item_text)
    if quantity is None or not target:
        await session.send("Loot what? Use LOOT <item> FROM <corpse or enemy>.\r\n")
        return

    all_items = list_corpse_items(session.database, corpse.id)
    mine = [item for item in all_items if item.reserved_character_id == int(character.id)]
    item_key, ambiguous = _resolve_corpse_item(mine, target)
    if ambiguous:
        await session.send("Be more specific: " + ", ".join(ambiguous) + ".\r\n")
        return
    if item_key is None:
        other_key, _other_ambiguous = _resolve_corpse_item(all_items, target)
        if other_key is not None:
            await session.send("That drop is reserved for another party member.\r\n")
        else:
            await session.send("That item is not on the corpse.\r\n")
        return

    available = sum(item.quantity for item in mine if item.item_key == item_key)
    if available < quantity:
        await session.send(f"Only {available}x {_item_name(item_key)} is assigned to you here.\r\n")
        return

    if not transfer_corpse_item_to_inventory(
        session.database,
        int(character.id),
        corpse.id,
        item_key,
        quantity,
    ):
        await session.send("You cannot take that drop right now.\r\n")
        return

    if quantity == 1:
        await session.send(f"You loot {_item_name(item_key)} from the corpse of {corpse.enemy_name}.\r\n")
    else:
        await session.send(
            f"You loot {quantity}x {_item_name(item_key)} from the corpse of {corpse.enemy_name}.\r\n"
        )


def _parse_from_command(body: str) -> tuple[str, str] | None:
    normalized = _normalize(body)
    marker = " from "
    if marker not in normalized:
        return None
    item_text, corpse_target = normalized.rsplit(marker, 1)
    if not item_text or not corpse_target:
        return None
    return item_text, corpse_target


async def _handle_corpse_command(session, command: str) -> bool:
    normalized = _normalize(command)
    if not normalized:
        return False

    for verb in ("look ", "examine ", "inspect "):
        if normalized.startswith(verb):
            target = normalized[len(verb):]
            if any(word in target for word in ("corpse", "body", "remains")):
                await inspect_corpse_command(session, target)
                return True

    if normalized == "loot":
        await session.send(
            "Loot what? Use LOOT CORPSE, LOOT <enemy>, or GET ALL FROM <enemy>.\r\n"
        )
        return True

    if normalized.startswith("loot "):
        body = normalized[len("loot "):]
        parsed = _parse_from_command(body)
        if parsed is None:
            await loot_all_command(session, body)
            return True
        item_text, corpse_target = parsed
        if item_text in {"all", "everything"}:
            await loot_all_command(session, corpse_target)
        else:
            await loot_item_command(session, item_text, corpse_target)
        return True

    for verb in ("get ", "take "):
        if not normalized.startswith(verb):
            continue
        body = normalized[len(verb):]
        parsed = _parse_from_command(body)
        if parsed is None:
            return False
        item_text, corpse_target = parsed
        if item_text in {"all", "everything"}:
            await loot_all_command(session, corpse_target)
        else:
            await loot_item_command(session, item_text, corpse_target)
        return True

    return False


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_corpse_loot_runtime(player_session_class) -> None:
    """Install persistent classic-MUD corpses, percentage drops, and loot verbs."""
    _install_loot_hooks()
    _install_help_catalog()

    if getattr(player_session_class, "_corpse_loot_runtime_installed", False):
        # Hooks are global function references and may have been replaced by a
        # focused test installer since this class was first configured.
        return

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if callable(previous_finish_enemy):
        async def _finish_enemy_defeat(self, enemy) -> None:
            character = getattr(self, "character", None)
            eligible = getattr(self, "active_enemy", None) is enemy
            room_key = str(getattr(character, "current_room", "") or "") if character is not None else ""
            enemy_key = str(getattr(getattr(enemy, "definition", None), "key", ""))
            enemy_name = str(getattr(getattr(enemy, "definition", None), "name", enemy_key or "Enemy"))

            # Practice furniture is defeated mechanically but should not leave an
            # organic corpse in the room.
            make_corpse = bool(
                eligible
                and character is not None
                and room_key
                and enemy_key
                and enemy_key != "training_dummy"
            )
            context = (
                _DefeatLootContext(
                    session=self,
                    enemy_object_id=id(enemy),
                    room_key=room_key,
                    enemy_key=enemy_key,
                    enemy_name=enemy_name,
                )
                if make_corpse
                else None
            )
            token = _DEFEAT_CONTEXT.set(context)
            try:
                await previous_finish_enemy(self, enemy)
            finally:
                _DEFEAT_CONTEXT.reset(token)

            if context is not None:
                await _commit_defeat_corpse(self, context)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if callable(previous_show_current_room):
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            await _show_corpses(self)

        player_session_class.show_current_room = show_current_room

    previous_playing_prompt = getattr(player_session_class, "playing_prompt", None)
    if callable(previous_playing_prompt):
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

            if await _handle_corpse_command(self, command):
                return
            await _delegate_prompt(self, previous_playing_prompt, command)

        player_session_class.playing_prompt = playing_prompt

    player_session_class._corpse_loot_runtime_installed = True
