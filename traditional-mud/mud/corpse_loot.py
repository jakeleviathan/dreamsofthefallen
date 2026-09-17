from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from random import randint, random
from time import time

import mud.crafting as crafting
import mud.economy_balance as economy_balance
import mud.economy_loop as economy
import mud.enemy_lifecycle as enemy_lifecycle
from mud.item_locations import (
    ItemLocation,
    add_to_location,
    ensure_item_location_storage,
    list_container_item_rows,
    transfer_item,
)


REGULAR_CORPSE_TTL_SECONDS = 5 * 60
NAMED_CORPSE_TTL_SECONDS = 15 * 60
CORPSE_PROTECTION_SECONDS = 60

# Content can override corpse lifetime without adding combat special cases.
CORPSE_TTL_OVERRIDES: dict[str, float] = {}


@dataclass(frozen=True, slots=True)
class LootTableEntry:
    """One independently rolled entry in an NPC loot table."""

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
    owner_character_id: int | None
    created_at: float
    protection_expires_at: float
    expires_at: float
    currency_amount: int = 0


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
    owner_character_id: int
    protected_character_ids: set[int] = field(default_factory=set)
    drops: list[_PendingDrop] = field(default_factory=list)
    loot_rolled: bool = False
    lifecycle_claimed: bool | None = None
    mobile_npc_key: str | None = None


# Explicit entries are authoritative. Enemies without an entry automatically
# inherit their existing guaranteed and secondary economy drops through the same
# percentage/quantity model, so the entire production world uses one loot path.
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
    clean_key = str(enemy_key).strip()
    if not clean_key:
        raise ValueError("Enemy key is required for a loot table.")
    NPC_LOOT_TABLES[clean_key] = tuple(entries)


def register_corpse_ttl(enemy_key: str, seconds: float) -> None:
    clean_key = str(enemy_key).strip()
    if not clean_key:
        raise ValueError("Enemy key is required for a corpse lifetime override.")
    CORPSE_TTL_OVERRIDES[clean_key] = max(1.0, float(seconds))


def ensure_corpse_storage(database) -> None:
    ensure_item_location_storage(database)


def _row_to_corpse(row) -> CorpseRecord:
    owner = row["owner_character_id"]
    return CorpseRecord(
        id=int(row["id"]),
        room_key=str(row["room_key"]),
        enemy_key=str(row["source_key"]),
        enemy_name=str(row["source_name"]),
        owner_character_id=None if owner is None else int(owner),
        created_at=float(row["created_at_epoch"]),
        protection_expires_at=float(row["protection_expires_at_epoch"]),
        expires_at=float(row["decay_at_epoch"]),
        currency_amount=int(row["currency_amount"]),
    )


def _prune_expired_corpses(database, *, now: float | None = None) -> None:
    ensure_corpse_storage(database)
    current = time() if now is None else float(now)
    with database.connect() as db:
        db.execute(
            "DELETE FROM world_containers WHERE kind = 'corpse' AND decay_at_epoch <= ?",
            (current,),
        )


def create_corpse(
    database,
    room_key: str,
    enemy_key: str,
    enemy_name: str,
    *,
    owner_character_id: int,
    protected_character_ids: set[int] | frozenset[int] | tuple[int, ...] = (),
    created_at: float | None = None,
    ttl_seconds: float = REGULAR_CORPSE_TTL_SECONDS,
    protection_seconds: float = CORPSE_PROTECTION_SECONDS,
    currency_amount: int = 0,
    death_key: str | None = None,
) -> tuple[int, bool]:
    """Create one persistent corpse and its temporary loot-rights group.

    death_key is an idempotency guard for shared/static kills. The caller can
    safely retry corpse creation without duplicating the physical remains.
    """
    ensure_corpse_storage(database)
    created = time() if created_at is None else float(created_at)
    protected_until = created + max(0.0, float(protection_seconds))
    expires = created + max(1.0, float(ttl_seconds))
    protected = {int(owner_character_id), *(int(value) for value in protected_character_ids)}

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO world_containers (
                room_key, kind, name, source_key, source_name, owner_character_id,
                created_at_epoch, protection_expires_at_epoch, decay_at_epoch,
                currency_amount, death_key
            ) VALUES (?, 'corpse', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room_key,
                f"corpse of {enemy_name}",
                enemy_key,
                enemy_name,
                int(owner_character_id),
                created,
                protected_until,
                expires,
                max(0, int(currency_amount)),
                death_key,
            ),
        )
        was_created = bool(cursor.rowcount)
        if was_created:
            corpse_id = int(cursor.lastrowid)
            for character_id in protected:
                db.execute(
                    """
                    INSERT OR IGNORE INTO world_container_access (container_id, character_id)
                    VALUES (?, ?)
                    """,
                    (corpse_id, character_id),
                )
        else:
            if not death_key:
                raise RuntimeError("Corpse creation failed without an idempotency key.")
            row = db.execute(
                "SELECT id FROM world_containers WHERE death_key = ?",
                (death_key,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Corpse creation failed and no existing corpse could be recovered.")
            corpse_id = int(row["id"])
    return corpse_id, was_created


def add_corpse_item(
    database,
    corpse_id: int,
    item_key: str,
    quantity: int,
    reserved_character_id: int,
) -> None:
    if quantity <= 0:
        return
    add_to_location(
        database,
        ItemLocation.container(corpse_id, int(reserved_character_id)),
        item_key,
        int(quantity),
    )


def list_corpses(
    database,
    room_key: str,
    *,
    now: float | None = None,
) -> list[CorpseRecord]:
    current = time() if now is None else float(now)
    _prune_expired_corpses(database, now=current)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT id, room_key, source_key, source_name, owner_character_id,
                   created_at_epoch, protection_expires_at_epoch, decay_at_epoch,
                   currency_amount
            FROM world_containers
            WHERE room_key = ? AND kind = 'corpse' AND decay_at_epoch > ?
            ORDER BY created_at_epoch DESC, id DESC
            """,
            (room_key, current),
        ).fetchall()
    return [_row_to_corpse(row) for row in rows]


def list_corpse_items(database, corpse_id: int) -> list[CorpseItem]:
    return [
        CorpseItem(
            item_key=str(row["item_key"]),
            quantity=int(row["quantity"]),
            reserved_character_id=int(row["reserved_character_id"]),
        )
        for row in list_container_item_rows(database, int(corpse_id))
    ]


def _protected_access(database, corpse_id: int, character_id: int) -> bool:
    ensure_corpse_storage(database)
    with database.connect() as db:
        row = db.execute(
            """
            SELECT 1 FROM world_container_access
            WHERE container_id = ? AND character_id = ?
            """,
            (int(corpse_id), int(character_id)),
        ).fetchone()
    return row is not None


def corpse_access_allowed(
    database,
    corpse: CorpseRecord,
    character_id: int,
    *,
    now: float | None = None,
) -> bool:
    current = time() if now is None else float(now)
    if current >= corpse.protection_expires_at:
        return True
    return _protected_access(database, corpse.id, character_id)


def _eligible_item_rows(
    database,
    corpse: CorpseRecord,
    character_id: int,
    *,
    now: float | None = None,
) -> list[CorpseItem]:
    current = time() if now is None else float(now)
    rows = list_corpse_items(database, corpse.id)
    if current >= corpse.protection_expires_at:
        return rows
    return [
        row
        for row in rows
        if row.reserved_character_id in {0, int(character_id)}
    ]


def _can_receive(session, item_key: str, quantity: int) -> bool:
    checker = getattr(session, "can_receive_item", None)
    if not callable(checker):
        return True
    try:
        return bool(checker(item_key, quantity))
    except TypeError:
        return bool(checker(item_key))


def transfer_all_corpse_loot_to_inventory(
    database,
    character_id: int,
    corpse_id: int,
    *,
    public: bool = False,
    can_receive=None,
) -> tuple[list[CorpseItem], list[CorpseItem]]:
    """Move all eligible corpse stacks, leaving capacity-blocked stacks behind."""
    rows = list_corpse_items(database, corpse_id)
    eligible = rows if public else [
        row for row in rows if row.reserved_character_id in {0, int(character_id)}
    ]
    moved: list[CorpseItem] = []
    blocked: list[CorpseItem] = []
    for row in eligible:
        if can_receive is not None and not bool(can_receive(row.item_key, row.quantity)):
            blocked.append(row)
            continue
        if transfer_item(
            database,
            ItemLocation.container(corpse_id, row.reserved_character_id),
            ItemLocation.character(character_id),
            row.item_key,
            row.quantity,
        ):
            moved.append(row)
    return moved, blocked


def transfer_corpse_item_to_inventory(
    database,
    character_id: int,
    corpse_id: int,
    item_key: str,
    quantity: int = 1,
    *,
    public: bool = False,
) -> bool:
    """Move a requested quantity across one or more eligible reservation buckets."""
    if quantity <= 0:
        raise ValueError("Loot quantity must be positive.")
    rows = [
        row
        for row in list_corpse_items(database, corpse_id)
        if row.item_key == item_key
        and (public or row.reserved_character_id in {0, int(character_id)})
    ]
    if sum(row.quantity for row in rows) < quantity:
        return False

    remaining = quantity
    for row in rows:
        take = min(remaining, row.quantity)
        if take <= 0:
            break
        if not transfer_item(
            database,
            ItemLocation.container(corpse_id, row.reserved_character_id),
            ItemLocation.character(character_id),
            item_key,
            take,
        ):
            return False
        remaining -= take
    return remaining == 0


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
    if value.startswith("the "):
        value = value[4:]
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
    if wanted.startswith("the "):
        wanted = wanted[4:]
    if wanted in {"", "corpse", "body", "remains"}:
        return corpses[0]

    parts = wanted.split()
    if len(parts) == 2 and parts[0] in {"corpse", "body", "remains"} and parts[1].isdigit():
        index = int(parts[1]) - 1
        return corpses[index] if 0 <= index < len(corpses) else None

    wanted_enemy = _corpse_target_text(wanted)
    exact: list[CorpseRecord] = []
    partial: list[CorpseRecord] = []
    for corpse in corpses:
        aliases = {_normalize(corpse.enemy_key), _normalize(corpse.enemy_name)}
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
    definition = getattr(enemy, "definition", None)
    enemy_key = str(getattr(definition, "key", ""))
    if enemy_key in NPC_LOOT_TABLES:
        return NPC_LOOT_TABLES[enemy_key]

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
    """Roll each configured item independently at kill time."""
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


def corpse_ttl_seconds_for(enemy) -> float:
    definition = getattr(enemy, "definition", None)
    key = str(getattr(definition, "key", ""))
    if key in CORPSE_TTL_OVERRIDES:
        return CORPSE_TTL_OVERRIDES[key]

    xp = int(getattr(definition, "xp_reward", 0) or 0)
    named_tokens = (
        "boss",
        "captain",
        "commander",
        "marshal",
        "warden",
        "king",
        "queen",
        "saint",
        "governor",
    )
    if xp >= 100 or any(token in key.lower() for token in named_tokens):
        return NAMED_CORPSE_TTL_SECONDS
    return REGULAR_CORPSE_TTL_SECONDS


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


def _protected_character_ids(session, enemy) -> set[int]:
    character = getattr(session, "character", None)
    result = {int(character.id)} if character is not None else set()
    try:
        from mud.party_system import _encounter_for, _encounter_sessions

        if _encounter_for(enemy) is not None:
            for member in _encounter_sessions(session, enemy):
                member_character = getattr(member, "character", None)
                if member_character is not None:
                    result.add(int(member_character.id))
    except Exception:
        pass
    return result


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
        recipient_id = int(recipient_character.id)
        context.protected_character_ids.add(recipient_id)
        context.drops.append(
            _PendingDrop(
                item_key=item_key,
                quantity=quantity,
                reserved_character_id=recipient_id,
                recipient_session=recipient,
            )
        )


async def _suppress_legacy_secondary_award(session, enemy) -> None:
    global _ORIGINAL_SECONDARY_AWARD
    if not _corpse_runtime_enabled(session):
        if _ORIGINAL_SECONDARY_AWARD is not None:
            await _ORIGINAL_SECONDARY_AWARD(session, enemy)
        return
    # Secondary entries are already folded into roll_loot_table and must not roll twice.
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
    """Redirect the existing economy award points into one corpse roll."""
    global _LOOT_HOOKS_CAPTURED
    global _ORIGINAL_BASE_AWARD, _ORIGINAL_SECONDARY_AWARD, _ORIGINAL_MARK_STATIC_DEFEATED

    if not _LOOT_HOOKS_CAPTURED:
        _ORIGINAL_BASE_AWARD = economy._award_loot
        _ORIGINAL_SECONDARY_AWARD = economy_balance._award_secondary_loot
        _ORIGINAL_MARK_STATIC_DEFEATED = enemy_lifecycle.mark_static_enemy_defeated
        _LOOT_HOOKS_CAPTURED = True

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
                "Take every corpse drop currently assigned or available to you.",
                ("corpse", "drops", "remains"),
            ),
            CommandEntry(
                "combat",
                "GET / TAKE ALL FROM <corpse or enemy>",
                "Take all available loot from a defeated enemy corpse.",
                ("corpse", "loot", "drops"),
            ),
            CommandEntry(
                "combat",
                "GET / TAKE <item> FROM <corpse or enemy>",
                "Take a particular corpse drop, optionally with a quantity.",
                ("corpse", "loot", "item"),
            ),
            CommandEntry(
                "combat",
                "LOOK / EXAMINE CORPSE",
                "Inspect a corpse, its drops, protection state, and remaining loot.",
                ("corpse", "body", "remains"),
            ),
            CommandEntry(
                "combat",
                "CORPSES",
                "List persistent defeated-enemy remains in the current room.",
                ("bodies", "remains"),
            ),
        )
        existing = {entry.syntax.casefold() for entry in command_guide.COMMANDS}
        new_entries = tuple(entry for entry in additions if entry.syntax.casefold() not in existing)
        if new_entries:
            command_guide.COMMANDS = command_guide.COMMANDS + new_entries
        command_guide.CATEGORIES = tuple(dict.fromkeys(entry.category for entry in command_guide.COMMANDS))
    except Exception:
        return


def _static_death_key(database, room_key: str, enemy_key: str) -> str | None:
    try:
        with database.connect() as db:
            row = db.execute(
                """
                SELECT defeated_at FROM room_enemy_respawns
                WHERE room_key = ? AND enemy_key = ?
                """,
                (room_key, enemy_key),
            ).fetchone()
        if row is None:
            return None
        return f"static:{room_key}:{enemy_key}:{float(row['defeated_at']):.6f}"
    except Exception:
        return None


async def _commit_defeat_corpse(session, enemy, context: _DefeatLootContext) -> int | None:
    if context.lifecycle_claimed is False:
        # Another session already claimed this shared static spawn. That kill owns
        # the one corpse and one set of rewards.
        return None

    death_key = _static_death_key(session.database, context.room_key, context.enemy_key)
    if death_key is None and context.mobile_npc_key:
        death_key = f"mobile:{context.room_key}:{context.mobile_npc_key}:{context.enemy_object_id}"
    if death_key is None:
        death_key = f"encounter:{context.room_key}:{context.enemy_key}:{context.enemy_object_id}"

    corpse_id, created = create_corpse(
        session.database,
        context.room_key,
        context.enemy_key,
        context.enemy_name,
        owner_character_id=context.owner_character_id,
        protected_character_ids=context.protected_character_ids,
        ttl_seconds=corpse_ttl_seconds_for(enemy),
        protection_seconds=CORPSE_PROTECTION_SECONDS,
        death_key=death_key,
    )
    if not created:
        return corpse_id

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
    current = time()
    public = current >= corpse.protection_expires_at
    allowed = corpse_access_allowed(session.database, corpse, int(character.id), now=current)
    mine = [item for item in items if item.reserved_character_id in {0, int(character.id)}]
    others = [item for item in items if item.reserved_character_id not in {0, int(character.id)}]

    await session.send(f"\r\n--- Corpse of {corpse.enemy_name} ---\r\n")
    if not items and corpse.currency_amount <= 0:
        await session.send("It holds nothing useful.\r\n")
    else:
        await session.send("Contents:\r\n")
        grouped: dict[str, int] = {}
        for item in items:
            grouped[item.item_key] = grouped.get(item.item_key, 0) + item.quantity
        for item_key, quantity in grouped.items():
            await session.send(f"  {quantity}x {_item_name(item_key)}\r\n")
        if corpse.currency_amount:
            await session.send(
                f"  {corpse.currency_amount} coin{'s' if corpse.currency_amount != 1 else ''}\r\n"
            )

    if public:
        await session.send("Loot rights: public. Anything remaining can be taken.\r\n")
    elif not allowed:
        seconds = max(1, int(corpse.protection_expires_at - current))
        await session.send(
            f"Loot rights: protected for the killer/party for about {seconds} more seconds.\r\n"
        )
    else:
        seconds = max(1, int(corpse.protection_expires_at - current))
        own_count = sum(item.quantity for item in mine)
        other_count = sum(item.quantity for item in others)
        await session.send(
            f"Loot rights: protected for your kill group for about {seconds} more seconds. "
            f"Your assigned drops: {own_count}."
            + (f" Other party drops: {other_count}." if other_count else "")
            + "\r\n"
        )


def _loot_currency(session, corpse: CorpseRecord, *, public: bool) -> int:
    character = getattr(session, "character", None)
    if character is None or corpse.currency_amount <= 0:
        return 0
    if not public and corpse.owner_character_id != int(character.id):
        return 0

    ensure_corpse_storage(session.database)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT currency_amount FROM world_containers WHERE id = ?",
            (corpse.id,),
        ).fetchone()
        amount = 0 if row is None else int(row["currency_amount"])
        if amount <= 0:
            return 0
        db.execute(
            "UPDATE world_containers SET currency_amount = 0 WHERE id = ?",
            (corpse.id,),
        )
        db.execute(
            """
            INSERT INTO character_currency (character_id, currency_key, amount)
            VALUES (?, 'coin', ?)
            ON CONFLICT(character_id, currency_key) DO UPDATE SET amount = amount + excluded.amount
            """,
            (int(character.id), amount),
        )
    return amount


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

    current = time()
    public = current >= corpse.protection_expires_at
    if not corpse_access_allowed(session.database, corpse, int(character.id), now=current):
        seconds = max(1, int(corpse.protection_expires_at - current))
        await session.send(
            f"That corpse is protected for the killer/party for about {seconds} more seconds.\r\n"
        )
        return

    moved, blocked = transfer_all_corpse_loot_to_inventory(
        session.database,
        int(character.id),
        corpse.id,
        public=public,
        can_receive=lambda item_key, quantity: _can_receive(session, item_key, quantity),
    )
    coins = _loot_currency(session, corpse, public=public)

    names = [f"{item.quantity}x {_item_name(item.item_key)}" for item in moved]
    if coins:
        names.append(f"{coins} coin{'s' if coins != 1 else ''}")
    if names:
        await session.send(
            f"You loot {', '.join(names)} from the corpse of {corpse.enemy_name}.\r\n"
        )
    elif blocked:
        await session.send("You cannot carry any more of the available corpse loot right now.\r\n")
    else:
        all_items = list_corpse_items(session.database, corpse.id)
        if all_items and not public:
            await session.send("Nothing currently assigned to you remains on that corpse.\r\n")
        else:
            await session.send(f"You search the corpse of {corpse.enemy_name}, but find nothing useful.\r\n")

    if blocked:
        await session.send(
            "Left on the corpse: "
            + ", ".join(f"{item.quantity}x {_item_name(item.item_key)}" for item in blocked)
            + ".\r\n"
        )


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

    current = time()
    public = current >= corpse.protection_expires_at
    if not corpse_access_allowed(session.database, corpse, int(character.id), now=current):
        seconds = max(1, int(corpse.protection_expires_at - current))
        await session.send(
            f"That corpse is protected for the killer/party for about {seconds} more seconds.\r\n"
        )
        return

    quantity, target = _parse_quantity_item(item_text)
    if quantity is None or not target:
        await session.send("Loot what? Use LOOT <item> FROM <corpse or enemy>.\r\n")
        return

    eligible = _eligible_item_rows(
        session.database,
        corpse,
        int(character.id),
        now=current,
    )
    item_key, ambiguous = _resolve_corpse_item(eligible, target)
    if ambiguous:
        await session.send("Be more specific: " + ", ".join(ambiguous) + ".\r\n")
        return
    if item_key is None:
        all_items = list_corpse_items(session.database, corpse.id)
        other_key, _ = _resolve_corpse_item(all_items, target)
        if other_key is not None and not public:
            await session.send("That drop is still assigned to another party member.\r\n")
        else:
            await session.send("That item is not on the corpse.\r\n")
        return

    available = sum(item.quantity for item in eligible if item.item_key == item_key)
    if available < quantity:
        await session.send(f"Only {available}x {_item_name(item_key)} is available to you here.\r\n")
        return
    if not _can_receive(session, item_key, quantity):
        await session.send("You cannot carry that item right now; it remains on the corpse.\r\n")
        return

    if not transfer_corpse_item_to_inventory(
        session.database,
        int(character.id),
        corpse.id,
        item_key,
        quantity,
        public=public,
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

    if normalized in {"corpses", "bodies", "remains"}:
        character = getattr(session, "character", None)
        if character is None or not character.current_room:
            return True
        corpses = list_corpses(session.database, character.current_room)
        if not corpses:
            await session.send("There are no corpses here.\r\n")
        else:
            await session.send("\r\n--- Corpses ---\r\n")
            for index, corpse in enumerate(corpses, start=1):
                await session.send(f"  {index}) Corpse of {corpse.enemy_name}\r\n")
        return True

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
    """Install persistent corpses, percentage drops, loot rights, and loot verbs."""
    _install_loot_hooks()
    _install_help_catalog()

    if getattr(player_session_class, "_corpse_loot_runtime_installed", False):
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
            # organic body on the floor.
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
                    owner_character_id=int(character.id),
                    protected_character_ids=_protected_character_ids(self, enemy),
                    mobile_npc_key=getattr(self, "active_mobile_npc_key", None),
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
                await _commit_defeat_corpse(self, enemy, context)

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
