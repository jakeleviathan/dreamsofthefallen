from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
import uuid
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import mud.crafting as crafting


LOGGER = logging.getLogger("dreams.production")
_ACTIVE_ACCOUNT_SESSIONS: dict[int, weakref.ReferenceType] = {}
_ACTIVE_CHARACTER_SESSIONS: dict[int, weakref.ReferenceType] = {}


@dataclass(frozen=True, slots=True)
class InventoryAudit:
    foreign_key_violations: int
    nonpositive_item_rows: int
    unknown_item_rows: int
    equipped_missing_rows: int
    provenance_mismatches: int
    details: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return not any((
            self.foreign_key_violations,
            self.nonpositive_item_rows,
            self.unknown_item_rows,
            self.equipped_missing_rows,
            self.provenance_mismatches,
        ))


@dataclass(frozen=True, slots=True)
class CombatSummary:
    hours: int
    fights: int
    victories: int
    deaths: int
    average_seconds: float
    average_level: float


@dataclass(frozen=True, slots=True)
class BackupResult:
    path: Path
    size_bytes: int
    integrity: str


def _truthy(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def configure_runtime_logging() -> logging.Logger:
    """Configure one rotating production log without duplicating handlers."""
    logger = logging.getLogger("dreams")
    logger.setLevel(getattr(logging, os.environ.get("MUD_LOG_LEVEL", "INFO").upper(), logging.INFO))
    if getattr(logger, "_dreams_configured", False):
        return logger

    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    log_dir = Path(os.environ.get("MUD_LOG_DIR", "logs"))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "dreams.log",
            maxBytes=int(os.environ.get("MUD_LOG_MAX_BYTES", str(5 * 1024 * 1024))),
            backupCount=int(os.environ.get("MUD_LOG_FILES", "5")),
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("event=log_file_unavailable path=%s", log_dir)

    logger.propagate = False
    logger._dreams_configured = True
    return logger


def ensure_production_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS production_session_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                account_id INTEGER,
                character_id INTEGER,
                account_name TEXT,
                character_name TEXT,
                outcome TEXT NOT NULL DEFAULT 'open',
                disconnect_reason TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS production_runtime_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                character_id INTEGER,
                details TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS production_combat_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER,
                enemy_key TEXT NOT NULL,
                character_level INTEGER NOT NULL,
                started_at_epoch REAL NOT NULL,
                ended_at_epoch REAL,
                outcome TEXT NOT NULL DEFAULT 'open',
                duration_seconds REAL,
                hp_start INTEGER,
                hp_end INTEGER,
                xp_reward INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS production_backup_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                path TEXT NOT NULL,
                reason TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                integrity TEXT NOT NULL
            );
            """
        )


def database_integrity(database) -> tuple[bool, tuple[str, ...]]:
    with database.connect() as db:
        rows = db.execute("PRAGMA integrity_check").fetchall()
    messages = tuple(str(row[0]) for row in rows)
    return messages == ("ok",), messages


def _table_names(database) -> set[str]:
    with database.connect() as db:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows}


def audit_inventory_integrity(database) -> InventoryAudit:
    """Read-only invariants for the item economy; never auto-deletes player data."""
    ensure_production_schema(database)
    details: list[str] = []
    tables = _table_names(database)

    with database.connect() as db:
        fk_rows = db.execute("PRAGMA foreign_key_check").fetchall()
        nonpositive = db.execute(
            "SELECT character_id, item_key, quantity FROM character_items WHERE quantity <= 0"
        ).fetchall()
        item_rows = db.execute(
            "SELECT character_id, item_key, quantity FROM character_items WHERE quantity > 0"
        ).fetchall()

        unknown = [row for row in item_rows if str(row["item_key"]) not in crafting.ITEMS_BY_KEY]
        for row in unknown[:10]:
            details.append(
                f"unknown item {row['item_key']} on character {row['character_id']} x{row['quantity']}"
            )
        for row in nonpositive[:10]:
            details.append(
                f"nonpositive item {row['item_key']} on character {row['character_id']} qty={row['quantity']}"
            )

        equipped_missing = []
        if "character_equipment" in tables:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(character_equipment)").fetchall()}
            if {"character_id", "item_key"}.issubset(columns):
                equipped_missing = db.execute(
                    """
                    SELECT e.character_id, e.item_key
                    FROM character_equipment e
                    LEFT JOIN character_items i
                      ON i.character_id = e.character_id
                     AND i.item_key = e.item_key
                     AND i.quantity > 0
                    WHERE i.item_key IS NULL
                    """
                ).fetchall()
                for row in equipped_missing[:10]:
                    details.append(
                        f"equipped item missing from inventory: character {row['character_id']} {row['item_key']}"
                    )

        provenance_mismatch_count = 0
        if "style_item_instances" in tables:
            try:
                import mud.style_collectibles as style

                provenance_keys = tuple(
                    meta.item_key for meta in style.STYLE_META if meta.provenance_track
                )
            except Exception:
                provenance_keys = ()
            for item_key in provenance_keys:
                owners = db.execute(
                    """
                    SELECT current_owner_character_id AS character_id, COUNT(*) AS total
                    FROM style_item_instances
                    WHERE item_key = ? AND current_owner_character_id IS NOT NULL
                    GROUP BY current_owner_character_id
                    """,
                    (item_key,),
                ).fetchall()
                instance_counts = {int(row["character_id"]): int(row["total"]) for row in owners}
                inventory = db.execute(
                    "SELECT character_id, quantity FROM character_items WHERE item_key = ? AND quantity > 0",
                    (item_key,),
                ).fetchall()
                inventory_counts = {int(row["character_id"]): int(row["quantity"]) for row in inventory}
                for character_id in set(instance_counts) | set(inventory_counts):
                    if instance_counts.get(character_id, 0) != inventory_counts.get(character_id, 0):
                        provenance_mismatch_count += 1
                        if len(details) < 30:
                            details.append(
                                f"provenance mismatch {item_key} character {character_id}: "
                                f"inventory={inventory_counts.get(character_id, 0)} "
                                f"serialized={instance_counts.get(character_id, 0)}"
                            )

    for row in fk_rows[:10]:
        details.append(f"foreign-key violation: {tuple(row)}")

    return InventoryAudit(
        foreign_key_violations=len(fk_rows),
        nonpositive_item_rows=len(nonpositive),
        unknown_item_rows=len(unknown),
        equipped_missing_rows=len(equipped_missing),
        provenance_mismatches=provenance_mismatch_count,
        details=tuple(details),
    )


def _backup_directory(database) -> Path:
    configured = os.environ.get("MUD_BACKUP_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(database.path).parent / "backups"


def create_database_backup(database, *, reason: str = "manual") -> BackupResult:
    """Use SQLite's online backup API, validate the copy, then atomically publish it."""
    ensure_production_schema(database)
    directory = _backup_directory(database)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    token = uuid.uuid4().hex[:8]
    final_path = directory / f"mud-{stamp}-{reason}-{token}.sqlite3"
    temp_path = final_path.with_suffix(".tmp")

    source = database.connect()
    destination = sqlite3.connect(temp_path)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    check = sqlite3.connect(temp_path)
    try:
        integrity_rows = check.execute("PRAGMA integrity_check").fetchall()
        integrity = "; ".join(str(row[0]) for row in integrity_rows)
    finally:
        check.close()
    if integrity != "ok":
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {integrity}")

    temp_path.replace(final_path)
    size = final_path.stat().st_size
    with database.connect() as db:
        db.execute(
            "INSERT INTO production_backup_log (path, reason, size_bytes, integrity) VALUES (?, ?, ?, ?)",
            (str(final_path), reason, size, integrity),
        )

    retain = max(2, int(os.environ.get("MUD_BACKUP_RETAIN", "48")))
    backups = sorted(directory.glob("mud-*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in backups[retain:]:
        try:
            stale.unlink()
        except OSError:
            LOGGER.warning("event=backup_retention_delete_failed path=%s", stale)

    return BackupResult(path=final_path, size_bytes=size, integrity=integrity)


def last_backup_row(database):
    ensure_production_schema(database)
    with database.connect() as db:
        return db.execute(
            "SELECT created_at, path, reason, size_bytes, integrity FROM production_backup_log ORDER BY id DESC LIMIT 1"
        ).fetchone()


def record_runtime_event(database, severity: str, category: str, details: str, character_id: int | None = None) -> None:
    ensure_production_schema(database)
    clean = " ".join(str(details).replace("\r", " ").replace("\n", " ").split())[:1000]
    with database.connect() as db:
        db.execute(
            "INSERT INTO production_runtime_events (severity, category, character_id, details) VALUES (?, ?, ?, ?)",
            (severity.upper(), category, character_id, clean),
        )
    getattr(LOGGER, severity.lower(), LOGGER.info)("event=%s character_id=%s details=%s", category, character_id, clean)


def combat_summary(database, hours: int = 24) -> CombatSummary:
    ensure_production_schema(database)
    hours = max(1, min(24 * 30, int(hours)))
    cutoff = time.time() - (hours * 3600)
    with database.connect() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS fights,
                   SUM(CASE WHEN outcome = 'victory' THEN 1 ELSE 0 END) AS victories,
                   SUM(CASE WHEN outcome = 'death' THEN 1 ELSE 0 END) AS deaths,
                   AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) AS avg_seconds,
                   AVG(character_level) AS avg_level
            FROM production_combat_log
            WHERE started_at_epoch >= ? AND outcome <> 'open'
            """,
            (cutoff,),
        ).fetchone()
    return CombatSummary(
        hours=hours,
        fights=int(row["fights"] or 0),
        victories=int(row["victories"] or 0),
        deaths=int(row["deaths"] or 0),
        average_seconds=float(row["avg_seconds"] or 0.0),
        average_level=float(row["avg_level"] or 0.0),
    )


def _begin_combat_metric(session) -> None:
    if getattr(session, "_production_combat_log_id", None) is not None:
        return
    character = getattr(session, "character", None)
    enemy = getattr(session, "active_enemy", None)
    combatant = getattr(session, "combatant", None)
    if character is None or enemy is None:
        return
    ensure_production_schema(session.database)
    started = time.time()
    with session.database.connect() as db:
        cursor = db.execute(
            """
            INSERT INTO production_combat_log (
                character_id, enemy_key, character_level, started_at_epoch, hp_start
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                character.id,
                enemy.definition.key,
                character.level,
                started,
                getattr(combatant, "current_hp", None),
            ),
        )
        session._production_combat_log_id = int(cursor.lastrowid)
    session._production_combat_started = started


def _finish_combat_metric(session, outcome: str, xp_reward: int = 0) -> None:
    row_id = getattr(session, "_production_combat_log_id", None)
    if row_id is None:
        return
    ended = time.time()
    started = float(getattr(session, "_production_combat_started", ended))
    combatant = getattr(session, "combatant", None)
    with session.database.connect() as db:
        db.execute(
            """
            UPDATE production_combat_log
            SET ended_at_epoch = ?, outcome = ?, duration_seconds = ?, hp_end = ?, xp_reward = ?
            WHERE id = ? AND outcome = 'open'
            """,
            (
                ended,
                outcome,
                max(0.0, ended - started),
                getattr(combatant, "current_hp", None),
                max(0, int(xp_reward)),
                row_id,
            ),
        )
    session._production_combat_log_id = None
    session._production_combat_started = None


def _start_session_log(session) -> None:
    account = getattr(session, "account", None)
    character = getattr(session, "character", None)
    if account is None or character is None:
        return
    _finish_session_log(session, "character_switch")
    ensure_production_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """
            INSERT INTO production_session_log (
                account_id, character_id, account_name, character_name
            ) VALUES (?, ?, ?, ?)
            """,
            (account.id, character.id, account.name, character.name),
        )
        session._production_session_log_id = int(cursor.lastrowid)


def _finish_session_log(session, reason: str = "disconnect") -> None:
    row_id = getattr(session, "_production_session_log_id", None)
    if row_id is None:
        return
    with session.database.connect() as db:
        db.execute(
            """
            UPDATE production_session_log
            SET ended_at = CURRENT_TIMESTAMP, outcome = 'closed', disconnect_reason = ?
            WHERE id = ? AND outcome = 'open'
            """,
            (reason[:80], row_id),
        )
    session._production_session_log_id = None


def _session_from_ref(mapping: dict[int, weakref.ReferenceType], key: int):
    ref = mapping.get(key)
    if ref is None:
        return None
    session = ref()
    if session is None:
        mapping.pop(key, None)
    return session


async def _supersede_session(old_session, new_session, reason: str) -> None:
    if old_session is None or old_session is new_session:
        return
    try:
        await old_session.send(
            "\r\nThis account resumed from another connection. This older connection is closing safely.\r\n"
        )
    except Exception:
        pass
    old_session._production_disconnect_reason = reason
    stop = getattr(old_session, "_stop_combat", None)
    if stop is not None:
        try:
            await stop()
        except Exception:
            pass
    state = getattr(old_session, "state", None)
    if state is not None and hasattr(type(state), "DISCONNECTED"):
        old_session.state = type(state).DISCONNECTED
    writer = getattr(old_session, "writer", None)
    if writer is not None and not writer.is_closing():
        writer.close()


async def _claim_account_session(session) -> None:
    account = getattr(session, "account", None)
    if account is None:
        return
    old = _session_from_ref(_ACTIVE_ACCOUNT_SESSIONS, int(account.id))
    if old is not None and old is not session:
        await _supersede_session(old, session, "superseded_account_reconnect")
    _ACTIVE_ACCOUNT_SESSIONS[int(account.id)] = weakref.ref(session)


async def _claim_character_session(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    old = _session_from_ref(_ACTIVE_CHARACTER_SESSIONS, int(character.id))
    if old is not None and old is not session:
        await _supersede_session(old, session, "superseded_character_reconnect")
    _ACTIVE_CHARACTER_SESSIONS[int(character.id)] = weakref.ref(session)


def _release_session_claims(session) -> None:
    account = getattr(session, "account", None)
    if account is not None:
        current = _session_from_ref(_ACTIVE_ACCOUNT_SESSIONS, int(account.id))
        if current is session:
            _ACTIVE_ACCOUNT_SESSIONS.pop(int(account.id), None)
    character = getattr(session, "character", None)
    if character is not None:
        current = _session_from_ref(_ACTIVE_CHARACTER_SESSIONS, int(character.id))
        if current is session:
            _ACTIVE_CHARACTER_SESSIONS.pop(int(character.id), None)


def active_session_snapshot() -> tuple[tuple[str, str, str], ...]:
    rows: list[tuple[str, str, str]] = []
    seen: set[int] = set()
    for ref in tuple(_ACTIVE_ACCOUNT_SESSIONS.values()):
        session = ref()
        if session is None or id(session) in seen:
            continue
        seen.add(id(session))
        account = getattr(session, "account", None)
        character = getattr(session, "character", None)
        rows.append((
            getattr(account, "name", "?"),
            getattr(character, "name", "roster"),
            str(getattr(character, "current_room", "") or "roster"),
        ))
    return tuple(sorted(rows))


def alpha_allowlist() -> frozenset[str]:
    raw = os.environ.get("MUD_ALPHA_ALLOWLIST", "")
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def alpha_gate_enabled() -> bool:
    return bool(alpha_allowlist())


def _alpha_account_allowed(session) -> bool:
    allow = alpha_allowlist()
    if not allow:
        return True
    account = getattr(session, "account", None)
    if account is None:
        return False
    if account.name.lower() in allow:
        return True
    owner = os.environ.get("MUD_OWNER_ACCOUNT", "").strip().lower()
    return bool(owner and account.name.lower() == owner)


async def _enforce_alpha_gate(session) -> bool:
    if _alpha_account_allowed(session):
        return True
    account = getattr(session, "account", None)
    name = getattr(account, "name", "unknown")
    record_runtime_event(session.database, "info", "alpha_gate_denied", f"account={name}")
    await session.send(
        "\r\nDreams of the Fallen is currently in closed alpha. This account is not on the current invitation list.\r\n"
    )
    session.account = None
    state = getattr(session, "state", None)
    if state is not None and hasattr(type(state), "ACCOUNT_NAME"):
        session.state = type(state).ACCOUNT_NAME
    return False


def install_production_hardening_runtime(player_session_class) -> None:
    """Install reconnect exclusivity, alpha gating, and production telemetry."""
    if getattr(player_session_class, "_production_hardening_runtime_installed", False):
        return

    previous_login = player_session_class.login_flow
    previous_create = player_session_class.create_account_flow
    previous_enter = player_session_class.enter_character
    previous_close = player_session_class.close
    previous_start_combat = player_session_class.start_combat
    previous_start_mobile = player_session_class.start_mobile_npc_combat
    previous_finish_enemy = player_session_class._finish_enemy_defeat
    previous_death = player_session_class._handle_character_death

    async def login_flow(self, *args, **kwargs):
        await previous_login(self, *args, **kwargs)
        if getattr(self, "account", None) is None:
            return
        if not await _enforce_alpha_gate(self):
            return
        await _claim_account_session(self)

    async def create_account_flow(self, *args, **kwargs):
        await previous_create(self, *args, **kwargs)
        if getattr(self, "account", None) is None:
            return
        if not await _enforce_alpha_gate(self):
            return
        await _claim_account_session(self)

    async def enter_character(self):
        await _claim_account_session(self)
        await _claim_character_session(self)
        await previous_enter(self)
        if getattr(self, "character", None) is not None:
            ensure_production_schema(self.database)
            _start_session_log(self)
            record_runtime_event(
                self.database,
                "info",
                "character_enter",
                f"character={self.character.name} room={self.character.current_room or 'none'}",
                self.character.id,
            )

    async def close(self):
        reason = getattr(self, "_production_disconnect_reason", "disconnect")
        if getattr(self, "_production_combat_log_id", None) is not None:
            _finish_combat_metric(self, "disconnect", 0)
        _finish_session_log(self, reason)
        _release_session_claims(self)
        await previous_close(self)

    async def start_combat(self, target_text: str):
        await previous_start_combat(self, target_text)
        _begin_combat_metric(self)

    async def start_mobile_npc_combat(self, npc_key: str, *, initiated_by_npc: bool = False):
        result = await previous_start_mobile(self, npc_key, initiated_by_npc=initiated_by_npc)
        if result:
            _begin_combat_metric(self)
        return result

    async def finish_enemy_defeat(self, enemy):
        xp = int(getattr(enemy.definition, "xp_reward", 0) or 0)
        await previous_finish_enemy(self, enemy)
        _finish_combat_metric(self, "victory", xp)

    async def handle_character_death(self, enemy_name: str):
        await previous_death(self, enemy_name)
        _finish_combat_metric(self, "death", 0)

    player_session_class.login_flow = login_flow
    player_session_class.create_account_flow = create_account_flow
    player_session_class.enter_character = enter_character
    player_session_class.close = close
    player_session_class.start_combat = start_combat
    player_session_class.start_mobile_npc_combat = start_mobile_npc_combat
    player_session_class._finish_enemy_defeat = finish_enemy_defeat
    player_session_class._handle_character_death = handle_character_death
    player_session_class._production_hardening_runtime_installed = True


class ProductionSupervisor:
    """Startup validation and recurring online backups around the live server."""

    def __init__(self, database) -> None:
        self.database = database
        self.logger = configure_runtime_logging()
        self.interval_seconds = max(
            60,
            int(float(os.environ.get("MUD_BACKUP_INTERVAL_MINUTES", "30")) * 60),
        )

    async def startup(self) -> None:
        ensure_production_schema(self.database)
        healthy, messages = database_integrity(self.database)
        if not healthy:
            self.logger.critical("event=database_integrity_failed details=%s", messages)
            if not _truthy("MUD_ALLOW_CORRUPT_DB", False):
                raise RuntimeError("Database integrity check failed; refusing to start without MUD_ALLOW_CORRUPT_DB=1")
        audit = audit_inventory_integrity(self.database)
        if audit.healthy:
            self.logger.info("event=inventory_audit status=ok")
        else:
            self.logger.warning("event=inventory_audit status=warning details=%s", audit.details)
        if _truthy("MUD_BACKUP_ON_START", True):
            result = await asyncio.to_thread(create_database_backup, self.database, reason="startup")
            self.logger.info("event=backup reason=startup path=%s bytes=%s", result.path, result.size_bytes)
        self.logger.info(
            "event=production_start alpha_gate=%s backup_interval_seconds=%s",
            alpha_gate_enabled(),
            self.interval_seconds,
        )

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            try:
                result = await asyncio.to_thread(create_database_backup, self.database, reason="periodic")
                self.logger.info("event=backup reason=periodic path=%s bytes=%s", result.path, result.size_bytes)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("event=periodic_backup_failed")

    async def shutdown(self) -> None:
        if not _truthy("MUD_BACKUP_ON_SHUTDOWN", True):
            return
        try:
            result = await asyncio.to_thread(create_database_backup, self.database, reason="shutdown")
            self.logger.info("event=backup reason=shutdown path=%s bytes=%s", result.path, result.size_bytes)
        except Exception:
            self.logger.exception("event=shutdown_backup_failed")


def install_production_server_runtime(mud_server_class) -> None:
    """Wrap the assembled server with startup checks, periodic backups, and shutdown backup."""
    if getattr(mud_server_class, "_production_supervisor_installed", False):
        return
    previous_run = mud_server_class.run

    async def run(self) -> None:
        supervisor = ProductionSupervisor(self.database)
        await supervisor.startup()
        backup_task = asyncio.create_task(supervisor.run(), name="production-backups")
        try:
            await previous_run(self)
        except asyncio.CancelledError:
            raise
        except Exception:
            supervisor.logger.exception("event=server_crash")
            raise
        finally:
            backup_task.cancel()
            await asyncio.gather(backup_task, return_exceptions=True)
            await supervisor.shutdown()

    mud_server_class.run = run
    mud_server_class._production_supervisor_installed = True
