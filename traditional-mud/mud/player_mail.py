from __future__ import annotations

import re
from dataclasses import dataclass

import mud.living_world as living
import mud.social_experience as social
from mud.astralis_time import ASTRALIS_CLOCK


PLAYER_MAIL_TYPE = "player"
WORLD_MAIL_TYPE = "world"
MAIL_SUBJECT_LIMIT = 80
MAIL_BODY_LIMIT = 2000
MAIL_BODY_LINE_LIMIT = 12
MAIL_BURST_LIMIT = 5
MAIL_BURST_WINDOW_MINUTES = 10
MAIL_DAY_LIMIT = 25
MAIL_LIST_LIMIT = 50

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class MailRecipient:
    id: int
    name: str


def _clean_text(value: str, *, collapse: bool = True, limit: int | None = None) -> str:
    value = _ANSI_RE.sub("", value or "")
    value = _CONTROL_RE.sub("", value)
    if collapse:
        value = " ".join(value.split())
    else:
        value = value.rstrip()
    if limit is not None:
        value = value[:limit]
    return value.strip() if collapse else value


def ensure_player_mail_schema(database) -> None:
    """Upgrade the living-world inbox into a general player/world mailbox.

    The original table used a UNIQUE(character_id, astralis_day, subject)
    constraint because it only stored one generated return letter per day. Player
    correspondence needs to allow two people to use the same subject on the same
    day, so old databases are rebuilt once without that constraint.
    """

    living.ensure_living_world_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'living_mail'"
        ).fetchone()
        table_sql = str(row["sql"] or "") if row is not None else ""
        columns = {
            str(column["name"])
            for column in db.execute("PRAGMA table_info(living_mail)").fetchall()
        }
        compact_sql = "".join(table_sql.upper().split())
        needs_rebuild = "UNIQUE(CHARACTER_ID,ASTRALIS_DAY,SUBJECT)" in compact_sql

        if needs_rebuild:
            db.execute("ALTER TABLE living_mail RENAME TO living_mail_legacy_v2")
            db.execute(
                """
                CREATE TABLE living_mail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    astralis_day INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    mail_type TEXT NOT NULL DEFAULT 'world',
                    sender_character_id INTEGER,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_character_id) REFERENCES characters(id) ON DELETE SET NULL
                )
                """
            )
            mail_type_expr = "mail_type" if "mail_type" in columns else "'world'"
            sender_id_expr = "sender_character_id" if "sender_character_id" in columns else "NULL"
            deleted_expr = "is_deleted" if "is_deleted" in columns else "0"
            deleted_at_expr = "deleted_at" if "deleted_at" in columns else "NULL"
            db.execute(
                f"""
                INSERT INTO living_mail
                    (id, character_id, astralis_day, sender, subject, body, is_read,
                     mail_type, sender_character_id, is_deleted, deleted_at, created_at)
                SELECT id, character_id, astralis_day, sender, subject, body, is_read,
                       {mail_type_expr}, {sender_id_expr}, {deleted_expr},
                       {deleted_at_expr}, created_at
                FROM living_mail_legacy_v2
                """
            )
            db.execute("DROP TABLE living_mail_legacy_v2")
            columns = {
                str(column["name"])
                for column in db.execute("PRAGMA table_info(living_mail)").fetchall()
            }

        additions = (
            ("mail_type", "TEXT NOT NULL DEFAULT 'world'"),
            ("sender_character_id", "INTEGER"),
            ("is_deleted", "INTEGER NOT NULL DEFAULT 0"),
            ("deleted_at", "TEXT"),
        )
        for name, definition in additions:
            if name not in columns:
                db.execute(f"ALTER TABLE living_mail ADD COLUMN {name} {definition}")

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_living_mail_inbox
            ON living_mail(character_id, is_deleted, id DESC)
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_living_mail_sender_created
            ON living_mail(sender_character_id, mail_type, created_at)
            """
        )


def _character(session):
    return getattr(session, "character", None)


def _lookup_recipient(session, name: str) -> MailRecipient | None:
    wanted = _clean_text(name, limit=80)
    if not wanted:
        return None
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT id, name FROM characters WHERE name = ? COLLATE NOCASE",
            (wanted,),
        ).fetchone()
    if row is None:
        return None
    return MailRecipient(id=int(row["id"]), name=str(row["name"]))


def _recipient_ignores_sender(session, recipient_id: int, sender_id: int) -> bool:
    social._ensure_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            """
            SELECT 1
            FROM character_ignores
            WHERE character_id = ? AND ignored_character_id = ?
            """,
            (int(recipient_id), int(sender_id)),
        ).fetchone()
    return row is not None


def _rate_limit_error(session, sender_id: int) -> str | None:
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        burst = db.execute(
            """
            SELECT COUNT(*) AS n
            FROM living_mail
            WHERE sender_character_id = ?
              AND mail_type = ?
              AND created_at >= datetime('now', ?)
            """,
            (int(sender_id), PLAYER_MAIL_TYPE, f"-{MAIL_BURST_WINDOW_MINUTES} minutes"),
        ).fetchone()
        daily = db.execute(
            """
            SELECT COUNT(*) AS n
            FROM living_mail
            WHERE sender_character_id = ?
              AND mail_type = ?
              AND created_at >= datetime('now', '-24 hours')
            """,
            (int(sender_id), PLAYER_MAIL_TYPE),
        ).fetchone()

    if int(burst["n"]) >= MAIL_BURST_LIMIT:
        return (
            f"The post clerk asks you to slow down. You can send at most "
            f"{MAIL_BURST_LIMIT} player letters in {MAIL_BURST_WINDOW_MINUTES} minutes."
        )
    if int(daily["n"]) >= MAIL_DAY_LIMIT:
        return f"You have reached the current player-mail limit of {MAIL_DAY_LIMIT} letters in 24 hours."
    return None


def _unread_count(session) -> int:
    character = _character(session)
    if character is None:
        return 0
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS n
            FROM living_mail
            WHERE character_id = ? AND is_read = 0 AND is_deleted = 0
            """,
            (character.id,),
        ).fetchone()
    return int(row["n"])


def _mail_rows(session, *, limit: int = MAIL_LIST_LIMIT):
    character = _character(session)
    if character is None:
        return []
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT id, astralis_day, sender, subject, is_read, mail_type
            FROM living_mail
            WHERE character_id = ? AND is_deleted = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (character.id, max(1, min(MAIL_LIST_LIMIT, int(limit)))),
        ).fetchall()


async def _show_mail(session) -> None:
    rows = _mail_rows(session)
    await session.send("\r\n--- Post ---\r\n")
    if not rows:
        await session.send("Your inbox is empty. MAIL HELP shows the post commands.\r\n")
        return
    for row in rows:
        marker = "*" if not int(row["is_read"]) else " "
        kind = str(row["mail_type"] or WORLD_MAIL_TYPE).upper()
        if kind not in {"PLAYER", "WORLD", "SYSTEM"}:
            kind = "SYSTEM"
        await session.send(
            f"{marker} [{kind}] {row['id']}) {row['subject']} - {row['sender']} "
            f"[Day {row['astralis_day']}]\r\n"
        )
    await session.send(
        "* means unread. MAIL READ <number> opens a letter. "
        "MAIL SEND <player>, MAIL DELETE <number>, or MAIL CLEAR READ|ALL manage the inbox.\r\n"
    )


async def _read_mail(session, mail_id: int) -> None:
    character = _character(session)
    if character is None:
        return
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            """
            SELECT id, astralis_day, sender, subject, body, mail_type
            FROM living_mail
            WHERE id = ? AND character_id = ? AND is_deleted = 0
            """,
            (int(mail_id), character.id),
        ).fetchone()
        if row is not None:
            db.execute(
                "UPDATE living_mail SET is_read = 1 WHERE id = ? AND character_id = ?",
                (int(mail_id), character.id),
            )
    if row is None:
        await session.send("You do not have a visible letter with that number.\r\n")
        return
    kind = str(row["mail_type"] or WORLD_MAIL_TYPE).upper()
    await session.send(
        f"\r\n--- {row['subject']} ---\r\n"
        f"From: {row['sender']} [{kind}]\r\n"
        f"{row['body']}\r\n"
    )


def _store_player_mail(session, recipient: MailRecipient, subject: str, body: str) -> int:
    sender = _character(session)
    if sender is None:
        raise RuntimeError("Player mail requires an active character.")
    ensure_player_mail_schema(session.database)
    moment = ASTRALIS_CLOCK.now()
    with session.database.connect() as db:
        cursor = db.execute(
            """
            INSERT INTO living_mail
                (character_id, astralis_day, sender, subject, body, is_read,
                 mail_type, sender_character_id, is_deleted)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, 0)
            """,
            (
                recipient.id,
                int(moment.day_number),
                sender.name,
                subject,
                body,
                PLAYER_MAIL_TYPE,
                sender.id,
            ),
        )
    return int(cursor.lastrowid)


async def _notify_online_recipient(recipient: MailRecipient, sender_name: str) -> None:
    target_session = social._session_for_character_name(recipient.name)
    if target_session is None:
        return
    try:
        await target_session.send(
            f"\r\n[Post] A letter from {sender_name} has arrived. Type MAIL when you want to read it.\r\n"
        )
    except (ConnectionError, RuntimeError):
        return


async def _compose_mail(session, target_text: str) -> None:
    """Begin a mail composition without nesting another prompt call.

    Production has many command wrappers that replay a command into inner layers.
    Asking session.prompt() again from inside one of those layers can receive the
    replayed command instead of waiting for fresh player input. Mail composition
    therefore spans normal command cycles as explicit session state.
    """

    sender = _character(session)
    if sender is None:
        return
    recipient = _lookup_recipient(session, target_text)
    if recipient is None:
        await session.send("No character by that name exists.\r\n")
        return
    if recipient.id == sender.id:
        await session.send("You do not need the post to write to yourself.\r\n")
        return
    if _recipient_ignores_sender(session, recipient.id, sender.id):
        await session.send(f"{recipient.name} is not accepting messages from you.\r\n")
        return
    limit_error = _rate_limit_error(session, sender.id)
    if limit_error:
        await session.send(limit_error + "\r\n")
        return

    session._player_mail_interaction = {
        "kind": "compose",
        "recipient": recipient,
        "stage": "subject",
        "subject": "",
        "lines": [],
        "total": 0,
    }
    await session.send(
        f"Subject for {recipient.name} (max {MAIL_SUBJECT_LIMIT} characters; /cancel to stop):\r\n"
    )


async def _handle_compose_input(session, state: dict[str, object], raw: str) -> None:
    sender = _character(session)
    if sender is None:
        session._player_mail_interaction = None
        return

    recipient = state.get("recipient")
    if not isinstance(recipient, MailRecipient):
        session._player_mail_interaction = None
        await session.send("That draft could not be continued. Start again with MAIL SEND <player>.\r\n")
        return

    stripped = raw.strip()
    if stripped.lower() == "/cancel":
        session._player_mail_interaction = None
        await session.send("Letter canceled.\r\n")
        return

    stage = str(state.get("stage") or "subject")
    if stage == "subject":
        subject = _clean_text(raw, limit=MAIL_SUBJECT_LIMIT)
        if not subject:
            await session.send("A letter needs a subject. Type a subject, or /cancel to stop.\r\n")
            return
        state["subject"] = subject
        state["stage"] = "body"
        await session.send(
            f"Write up to {MAIL_BODY_LINE_LIMIT} lines ({MAIL_BODY_LIMIT} characters total). "
            "Enter a single . on its own line to send, or /cancel to discard.\r\n"
        )
        return

    lines = state.get("lines")
    if not isinstance(lines, list):
        lines = []
        state["lines"] = lines
    total = int(state.get("total") or 0)

    if stripped == ".":
        body = "\n".join(str(value) for value in lines).strip()
        if not body:
            await session.send("The letter body is still empty. Write a line, or /cancel to stop.\r\n")
            return

        # Re-check mutable delivery rules after composition.
        if _recipient_ignores_sender(session, recipient.id, sender.id):
            session._player_mail_interaction = None
            await session.send(f"{recipient.name} is no longer accepting messages from you.\r\n")
            return
        limit_error = _rate_limit_error(session, sender.id)
        if limit_error:
            session._player_mail_interaction = None
            await session.send(limit_error + "\r\n")
            return

        subject = str(state.get("subject") or "").strip()
        session._player_mail_interaction = None
        _store_player_mail(session, recipient, subject, body)
        await session.send(f"Letter sent to {recipient.name}.\r\n")
        await _notify_online_recipient(recipient, sender.name)
        return

    clean = _clean_text(raw, collapse=False)
    prospective = total + len(clean) + (1 if lines else 0)
    if len(lines) >= MAIL_BODY_LINE_LIMIT:
        await session.send(
            f"The letter already has {MAIL_BODY_LINE_LIMIT} lines. Enter . to send it, or /cancel to discard it.\r\n"
        )
        return
    if prospective > MAIL_BODY_LIMIT:
        await session.send(
            f"That line would exceed the {MAIL_BODY_LIMIT}-character letter limit. "
            "Enter . to send what you have, or /cancel to discard it.\r\n"
        )
        return

    lines.append(clean)
    state["total"] = prospective


async def _delete_mail(session, mail_id: int) -> None:
    character = _character(session)
    if character is None:
        return
    ensure_player_mail_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """
            UPDATE living_mail
            SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP
            WHERE id = ? AND character_id = ? AND is_deleted = 0
            """,
            (int(mail_id), character.id),
        )
    if cursor.rowcount:
        await session.send(f"Letter {mail_id} removed from your inbox.\r\n")
    else:
        await session.send("You do not have a visible letter with that number.\r\n")


async def _clear_mail(session, *, read_only: bool) -> None:
    """Begin a confirmed bulk-clear operation across normal command cycles."""

    character = _character(session)
    if character is None:
        return
    ensure_player_mail_schema(session.database)
    predicate = "AND is_read = 1" if read_only else ""
    with session.database.connect() as db:
        row = db.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM living_mail
            WHERE character_id = ? AND is_deleted = 0 {predicate}
            """,
            (character.id,),
        ).fetchone()
    count = int(row["n"])
    if count <= 0:
        await session.send("There are no matching letters to clear.\r\n")
        return

    label = "read letters" if read_only else "letters"
    session._player_mail_interaction = {
        "kind": "clear",
        "read_only": bool(read_only),
    }
    await session.send(
        f"Clear {count} {label} from your inbox? Type YES to confirm, or NO to cancel.\r\n"
    )


async def _perform_clear_mail(session, *, read_only: bool) -> int:
    character = _character(session)
    if character is None:
        return 0
    ensure_player_mail_schema(session.database)
    predicate = "AND is_read = 1" if read_only else ""
    with session.database.connect() as db:
        cursor = db.execute(
            f"""
            UPDATE living_mail
            SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP
            WHERE character_id = ? AND is_deleted = 0 {predicate}
            """,
            (character.id,),
        )
    return int(cursor.rowcount)


async def _handle_clear_input(session, state: dict[str, object], raw: str) -> None:
    answer = raw.strip().lower()
    if answer not in {"yes", "y", "no", "n", "cancel", "/cancel"}:
        await session.send("Please type YES to clear the mail, or NO to cancel.\r\n")
        return

    session._player_mail_interaction = None
    if answer not in {"yes", "y"}:
        await session.send("Inbox clear canceled.\r\n")
        return

    read_only = bool(state.get("read_only"))
    count = await _perform_clear_mail(session, read_only=read_only)
    label = "read letters" if read_only else "letters"
    await session.send(f"Cleared {count} {label} from your inbox.\r\n")


async def _handle_mail_interaction(session, raw: str) -> bool:
    state = getattr(session, "_player_mail_interaction", None)
    if not isinstance(state, dict):
        return False

    kind = str(state.get("kind") or "")
    if kind == "compose":
        await _handle_compose_input(session, state, raw)
        return True
    if kind == "clear":
        await _handle_clear_input(session, state, raw)
        return True

    session._player_mail_interaction = None
    return False


async def _show_mail_help(session) -> None:
    await session.send(
        "\r\n--- Post Commands ---\r\n"
        "MAIL / POST / INBOX - list up to 50 visible letters; * marks unread.\r\n"
        "MAIL READ <number> / READ MAIL <number> - open a letter.\r\n"
        "MAIL SEND <player> - compose persistent mail for an online or offline character.\r\n"
        "MAIL SEND TO <player> - same command, alternate phrasing.\r\n"
        "MAIL DELETE <number> - remove one letter from your inbox.\r\n"
        "MAIL CLEAR READ - clear all read letters after confirmation.\r\n"
        "MAIL CLEAR ALL - clear the whole inbox after confirmation.\r\n"
        "IGNORE <player> blocks that character's tells, public communication, and player mail.\r\n"
    )


def _parse_mail_id(text: str) -> int | None:
    value = text.strip()
    return int(value) if value.isdigit() and int(value) > 0 else None


async def _delegate(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    prior_prompt = session.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = prior_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_player_mail_runtime(player_session_class) -> None:
    """Install persistent player mail and safe mailbox-management commands."""

    if getattr(player_session_class, "_player_mail_runtime_installed", False):
        return

    # Living-world login/GMCP code resolves this function through its module
    # global, so replacing it keeps unread counts correct after soft deletes.
    living._unread_mail_count = _unread_count
    living._show_mail = _show_mail
    living._read_mail = _read_mail

    previous_enter = getattr(player_session_class, "enter_character", None)
    if previous_enter is not None:
        async def enter_character(self) -> None:
            # A draft or confirmation belongs only to the current character/session.
            self._player_mail_interaction = None
            # Migrate before the living-world login layer creates or counts mail.
            ensure_player_mail_schema(self.database)
            await previous_enter(self)

        player_session_class.enter_character = enter_character

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if _character(self) is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        # Interactive mail state consumes the next real command line before any
        # normal command parser sees it. This is why YES now works reliably even
        # through the production stack's command-replay wrappers.
        if await _handle_mail_interaction(self, command):
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"mail", "post", "inbox"}:
            await _show_mail(self)
            return
        if normalized in {"mail help", "post help", "help mail"}:
            await _show_mail_help(self)
            return

        read_arg = None
        if normalized.startswith("mail read "):
            read_arg = stripped.split(maxsplit=2)[2]
        elif normalized.startswith("read mail "):
            read_arg = stripped.split(maxsplit=2)[2]
        if read_arg is not None:
            mail_id = _parse_mail_id(read_arg)
            if mail_id is None:
                await self.send("Use MAIL READ <number>.\r\n")
            else:
                await _read_mail(self, mail_id)
            return

        if normalized == "mail send" or normalized == "mail send to":
            await self.send("Use MAIL SEND <player>.\r\n")
            return
        if normalized.startswith("mail send to "):
            await _compose_mail(self, stripped[len("mail send to "):])
            return
        if normalized.startswith("mail send "):
            await _compose_mail(self, stripped[len("mail send "):])
            return

        delete_arg = None
        if normalized.startswith("mail delete "):
            delete_arg = stripped[len("mail delete "):]
        elif normalized.startswith("delete mail "):
            delete_arg = stripped[len("delete mail "):]
        if delete_arg is not None:
            mail_id = _parse_mail_id(delete_arg)
            if mail_id is None:
                await self.send("Use MAIL DELETE <number>.\r\n")
            else:
                await _delete_mail(self, mail_id)
            return

        if normalized in {"mail clear", "clear mail"}:
            await self.send("Use MAIL CLEAR READ or MAIL CLEAR ALL. Both require confirmation.\r\n")
            return
        if normalized in {"mail clear read", "clear read mail"}:
            await _clear_mail(self, read_only=True)
            return
        if normalized in {"mail clear all", "clear all mail", "mail clear inbox"}:
            await _clear_mail(self, read_only=False)
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._player_mail_runtime_installed = True
