from __future__ import annotations

import re

from mud.alpha_ux import _record_event, _safe_verb


NOTE_TITLE_LIMIT = 80
NOTE_BODY_LIMIT = 6000
NOTE_LINE_LIMIT = 60
NOTE_COUNT_LIMIT = 100
NOTE_LIST_LIMIT = 20

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


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


def ensure_notepad_schema(database) -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_character_notes_owner_updated
            ON character_notes(character_id, updated_at DESC, id DESC)
            """
        )


def _character(session):
    return getattr(session, "character", None)


def _note_count(session) -> int:
    character = _character(session)
    if character is None:
        return 0
    ensure_notepad_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM character_notes WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    return int(row["n"])


def _note_rows(session, *, page: int = 1, limit: int = NOTE_LIST_LIMIT):
    character = _character(session)
    if character is None:
        return []
    ensure_notepad_schema(session.database)
    page_size = max(1, min(NOTE_LIST_LIMIT, int(limit)))
    page_number = max(1, int(page))
    offset = (page_number - 1) * page_size
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT id, title, updated_at
            FROM character_notes
            WHERE character_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (character.id, page_size, offset),
        ).fetchall()


def _get_note(session, note_id: int):
    character = _character(session)
    if character is None:
        return None
    ensure_notepad_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT id, title, body, created_at, updated_at
            FROM character_notes
            WHERE id = ? AND character_id = ?
            """,
            (int(note_id), character.id),
        ).fetchone()


def _create_note(session, title: str, body: str) -> int:
    character = _character(session)
    if character is None:
        raise RuntimeError("Notepad requires an active character.")
    ensure_notepad_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """
            INSERT INTO character_notes (character_id, title, body)
            VALUES (?, ?, ?)
            """,
            (character.id, title, body),
        )
    return int(cursor.lastrowid)


def _update_note(session, note_id: int, title: str, body: str) -> bool:
    character = _character(session)
    if character is None:
        return False
    ensure_notepad_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """
            UPDATE character_notes
            SET title = ?, body = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND character_id = ?
            """,
            (title, body, int(note_id), character.id),
        )
    return bool(cursor.rowcount)


def _delete_note(session, note_id: int) -> bool:
    character = _character(session)
    if character is None:
        return False
    ensure_notepad_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            "DELETE FROM character_notes WHERE id = ? AND character_id = ?",
            (int(note_id), character.id),
        )
    return bool(cursor.rowcount)


def _parse_note_id(text: str) -> int | None:
    value = text.strip()
    return int(value) if value.isdigit() and int(value) > 0 else None


async def _show_notepad(session, *, page: int = 1) -> None:
    total = _note_count(session)
    page_count = max(1, (total + NOTE_LIST_LIMIT - 1) // NOTE_LIST_LIMIT)
    page_number = max(1, min(int(page), page_count))
    rows = _note_rows(session, page=page_number)

    await session.send(
        f"\r\n--- Notepad · {total} note{'s' if total != 1 else ''} · page {page_number}/{page_count} ---\r\n"
    )
    if not rows:
        await session.send(
            "No notes yet. NOTEPAD NEW <title> starts one.\r\n"
        )
        return

    for row in rows:
        await session.send(f"{row['id']:>3}) {row['title']}\r\n")

    await session.send(
        "\r\nNOTEPAD READ <number> · NEW <title> · EDIT <number> · DELETE <number>\r\n"
    )
    if page_count > 1:
        await session.send(
            f"NOTEPAD PAGE <number> browses pages 1-{page_count}.\r\n"
        )


async def _read_note(session, note_id: int) -> None:
    row = _get_note(session, note_id)
    if row is None:
        await session.send("You do not have a note with that number.\r\n")
        return

    body = str(row["body"] or "")
    await session.send(
        f"\r\n--- Note {row['id']}: {row['title']} ---\r\n"
        f"{body if body else '(empty note)'}\r\n"
        f"\r\nNOTEPAD EDIT {row['id']} · NOTEPAD DELETE {row['id']}\r\n"
    )


def _editor_lines(state: dict[str, object]) -> list[str]:
    lines = state.get("lines")
    if not isinstance(lines, list):
        lines = []
        state["lines"] = lines
    return lines


def _editor_total(lines: list[str]) -> int:
    return sum(len(line) for line in lines) + max(0, len(lines) - 1)


async def _show_editor(session, state: dict[str, object]) -> None:
    kind = str(state.get("kind") or "")
    title = str(state.get("title") or "Untitled")
    note_id = state.get("note_id")
    heading = f"Edit Note {note_id}: {title}" if kind == "edit" else f"New Note: {title}"
    lines = _editor_lines(state)

    await session.send(f"\r\n--- {heading} ---\r\n")
    if lines:
        for index, line in enumerate(lines, start=1):
            await session.send(f"{index:>3} | {line}\r\n")
    else:
        await session.send("(empty)\r\n")

    if kind == "edit":
        await session.send(
            "\r\nPlain text appends a line. /set N text replaces a line; "
            "/insert N text inserts; /delete N removes; /title text renames; "
            "/clear empties the body; /show redraws.\r\n"
            "Enter . on its own line to save, or /cancel to discard changes.\r\n"
        )
    else:
        await session.send(
            f"\r\nWrite up to {NOTE_LINE_LIMIT} lines ({NOTE_BODY_LIMIT} characters total). "
            "/title text renames; /show redraws.\r\n"
            "Enter . on its own line to save, or /cancel to discard.\r\n"
        )


async def _begin_new_note(session, title_text: str) -> None:
    if _note_count(session) >= NOTE_COUNT_LIMIT:
        await session.send(
            f"Your notepad already contains {NOTE_COUNT_LIMIT} notes. Delete one before creating another.\r\n"
        )
        return

    title = _clean_text(title_text, limit=NOTE_TITLE_LIMIT)
    if title:
        session._notepad_interaction = {
            "kind": "new",
            "stage": "body",
            "title": title,
            "lines": [],
        }
        await _show_editor(session, session._notepad_interaction)
        return

    session._notepad_interaction = {
        "kind": "new",
        "stage": "title",
        "title": "",
        "lines": [],
    }
    await session.send(
        f"Title for the new note (max {NOTE_TITLE_LIMIT} characters; /cancel to stop):\r\n"
    )


async def _begin_edit_note(session, note_id: int) -> None:
    row = _get_note(session, note_id)
    if row is None:
        await session.send("You do not have a note with that number.\r\n")
        return

    body = str(row["body"] or "")
    session._notepad_interaction = {
        "kind": "edit",
        "stage": "body",
        "note_id": int(row["id"]),
        "title": str(row["title"]),
        "lines": body.split("\n") if body else [],
    }
    await _show_editor(session, session._notepad_interaction)


async def _begin_delete_note(session, note_id: int) -> None:
    row = _get_note(session, note_id)
    if row is None:
        await session.send("You do not have a note with that number.\r\n")
        return
    session._notepad_interaction = {
        "kind": "delete",
        "note_id": int(row["id"]),
        "title": str(row["title"]),
    }
    await session.send(
        f"Delete note {row['id']} ({row['title']}) permanently? Type YES to confirm, or NO to cancel.\r\n"
    )


async def _handle_delete_confirmation(session, state: dict[str, object], raw: str) -> None:
    answer = raw.strip().lower()
    if answer not in {"yes", "y", "no", "n", "cancel", "/cancel"}:
        await session.send("Please type YES to delete the note, or NO to cancel.\r\n")
        return

    session._notepad_interaction = None
    if answer not in {"yes", "y"}:
        await session.send("Note deletion canceled.\r\n")
        return

    note_id = int(state.get("note_id") or 0)
    if _delete_note(session, note_id):
        await session.send(f"Note {note_id} deleted.\r\n")
    else:
        await session.send("That note no longer exists.\r\n")


def _line_command(raw: str, command: str) -> tuple[int | None, str]:
    remainder = raw[len(command):].strip()
    if not remainder:
        return None, ""
    number_text, _, text = remainder.partition(" ")
    if not number_text.isdigit():
        return None, ""
    return int(number_text), text


async def _handle_editor_input(session, state: dict[str, object], raw: str) -> None:
    stripped = raw.strip()
    lower = stripped.lower()
    kind = str(state.get("kind") or "new")

    if lower == "/cancel":
        session._notepad_interaction = None
        await session.send("Note changes discarded.\r\n")
        return

    if str(state.get("stage") or "body") == "title":
        title = _clean_text(raw, limit=NOTE_TITLE_LIMIT)
        if not title:
            await session.send("A note needs a title. Type one, or /cancel to stop.\r\n")
            return
        state["title"] = title
        state["stage"] = "body"
        await _show_editor(session, state)
        return

    lines = _editor_lines(state)

    if stripped == ".":
        title = _clean_text(str(state.get("title") or ""), limit=NOTE_TITLE_LIMIT)
        if not title:
            await session.send("Use /title <text> to give the note a title before saving.\r\n")
            return
        body = "\n".join(lines).strip()
        if kind == "edit":
            note_id = int(state.get("note_id") or 0)
            saved = _update_note(session, note_id, title, body)
            session._notepad_interaction = None
            if saved:
                await session.send(f"Note {note_id} saved.\r\n")
            else:
                await session.send("That note no longer exists; your changes were not saved.\r\n")
            return

        note_id = _create_note(session, title, body)
        session._notepad_interaction = None
        await session.send(f"Note {note_id} saved.\r\n")
        return

    if lower == "/show":
        await _show_editor(session, state)
        return

    if lower.startswith("/title "):
        title = _clean_text(stripped[len("/title "):], limit=NOTE_TITLE_LIMIT)
        if not title:
            await session.send("Use /title followed by the new title.\r\n")
            return
        state["title"] = title
        await session.send(f"Title changed to: {title}\r\n")
        return

    if lower == "/clear":
        if kind != "edit":
            await session.send("/clear is available while editing an existing note.\r\n")
            return
        lines.clear()
        await session.send("Note body cleared in the editor. Enter . to save or /cancel to discard.\r\n")
        return

    if lower.startswith("/set "):
        if kind != "edit":
            await session.send("/set is available while editing an existing note.\r\n")
            return
        number, text = _line_command(stripped, "/set ")
        clean = _clean_text(text, collapse=False)
        if number is None or number < 1 or number > len(lines) or not clean:
            await session.send("Use /set <line number> <replacement text>.\r\n")
            return
        candidate = list(lines)
        candidate[number - 1] = clean
        if _editor_total(candidate) > NOTE_BODY_LIMIT:
            await session.send(f"That change would exceed the {NOTE_BODY_LIMIT}-character note limit.\r\n")
            return
        lines[number - 1] = clean
        await session.send(f"Line {number} replaced.\r\n")
        return

    if lower.startswith("/insert "):
        if kind != "edit":
            await session.send("/insert is available while editing an existing note.\r\n")
            return
        number, text = _line_command(stripped, "/insert ")
        clean = _clean_text(text, collapse=False)
        if number is None or number < 1 or number > len(lines) + 1 or not clean:
            await session.send("Use /insert <line number> <text>.\r\n")
            return
        if len(lines) >= NOTE_LINE_LIMIT:
            await session.send(f"The note already has {NOTE_LINE_LIMIT} lines.\r\n")
            return
        candidate = list(lines)
        candidate.insert(number - 1, clean)
        if _editor_total(candidate) > NOTE_BODY_LIMIT:
            await session.send(f"That change would exceed the {NOTE_BODY_LIMIT}-character note limit.\r\n")
            return
        lines.insert(number - 1, clean)
        await session.send(f"Line inserted at {number}.\r\n")
        return

    if lower.startswith("/delete "):
        if kind != "edit":
            await session.send("/delete is available while editing an existing note.\r\n")
            return
        number_text = stripped[len("/delete "):].strip()
        if not number_text.isdigit():
            await session.send("Use /delete <line number>.\r\n")
            return
        number = int(number_text)
        if number < 1 or number > len(lines):
            await session.send("That line number is not in the note.\r\n")
            return
        lines.pop(number - 1)
        await session.send(f"Line {number} removed.\r\n")
        return

    # Plain text is the fast path both for new notes and for appending while editing.
    clean = _clean_text(raw, collapse=False)
    if len(lines) >= NOTE_LINE_LIMIT:
        await session.send(
            f"The note already has {NOTE_LINE_LIMIT} lines. Enter . to save, or edit/remove an existing line.\r\n"
        )
        return
    candidate = list(lines)
    candidate.append(clean)
    if _editor_total(candidate) > NOTE_BODY_LIMIT:
        await session.send(
            f"That line would exceed the {NOTE_BODY_LIMIT}-character note limit. Enter . to save what you have.\r\n"
        )
        return
    lines.append(clean)


async def _handle_notepad_interaction(session, raw: str) -> bool:
    state = getattr(session, "_notepad_interaction", None)
    if not isinstance(state, dict):
        return False

    if str(state.get("kind") or "") == "delete":
        await _handle_delete_confirmation(session, state, raw)
        return True

    await _handle_editor_input(session, state, raw)
    return True


async def _show_notepad_help(session) -> None:
    await session.send(
        "\r\n--- Notepad Commands ---\r\n"
        "NOTEPAD / NOTES - list your private character notes. NOTEPAD PAGE <number> browses longer lists.\r\n"
        "NOTEPAD NEW <title> / NOTEPAD WRITE <title> - start a multiline note. The title may be entered on the next line if omitted.\r\n"
        "NOTEPAD READ <number> - open a note. NOTEPAD <number> is a shorthand.\r\n"
        "NOTEPAD EDIT <number> - edit title or individual lines, or append new lines.\r\n"
        "NOTEPAD DELETE <number> - permanently delete a note after confirmation.\r\n"
        "While writing: . saves, /cancel discards, /show redraws, and /title <text> renames.\r\n"
        "While editing: /set N text, /insert N text, /delete N, and /clear change the body.\r\n"
        "Notes are private to the character that wrote them.\r\n"
    )


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


def install_notepad_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_notepad_runtime_installed", False):
        return

    previous_enter = getattr(player_session_class, "enter_character", None)
    if previous_enter is not None:
        async def enter_character(self) -> None:
            self._notepad_interaction = None
            ensure_notepad_schema(self.database)
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

        if await _handle_notepad_interaction(self, command):
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"notepad", "notes"}:
            # This modal wrapper sits outside final command telemetry so note
            # editor text is never mistaken for a command. Count only the safe
            # top-level invocation; note titles and body lines remain private.
            _record_event(self, "command", verb=_safe_verb(command))
            await _show_notepad(self)
            return
        if normalized.startswith("notepad page ") or normalized.startswith("notes page "):
            page_text = stripped.rsplit(" ", 1)[-1].strip()
            if not page_text.isdigit() or int(page_text) < 1:
                await self.send("Use NOTEPAD PAGE <number>.\r\n")
            else:
                await _show_notepad(self, page=int(page_text))
            return
        if normalized in {"notepad help", "notes help", "help notepad", "help notes"}:
            await _show_notepad_help(self)
            return

        if normalized in {"notepad new", "notes new", "notepad write", "notes write"}:
            await _begin_new_note(self, "")
            return
        if normalized.startswith("notepad new "):
            await _begin_new_note(self, stripped[len("notepad new "):])
            return
        if normalized.startswith("notes new "):
            await _begin_new_note(self, stripped[len("notes new "):])
            return
        if normalized.startswith("notepad write "):
            await _begin_new_note(self, stripped[len("notepad write "):])
            return
        if normalized.startswith("notes write "):
            await _begin_new_note(self, stripped[len("notes write "):])
            return

        read_arg = None
        if normalized.startswith("notepad read "):
            read_arg = stripped[len("notepad read "):]
        elif normalized.startswith("notes read "):
            read_arg = stripped[len("notes read "):]
        elif normalized.startswith("notepad ") and stripped[len("notepad "):].strip().isdigit():
            read_arg = stripped[len("notepad "):]
        if read_arg is not None:
            note_id = _parse_note_id(read_arg)
            if note_id is None:
                await self.send("Use NOTEPAD READ <number>.\r\n")
            else:
                await _read_note(self, note_id)
            return

        edit_arg = None
        if normalized.startswith("notepad edit "):
            edit_arg = stripped[len("notepad edit "):]
        elif normalized.startswith("notes edit "):
            edit_arg = stripped[len("notes edit "):]
        if edit_arg is not None:
            note_id = _parse_note_id(edit_arg)
            if note_id is None:
                await self.send("Use NOTEPAD EDIT <number>.\r\n")
            else:
                await _begin_edit_note(self, note_id)
            return

        delete_arg = None
        if normalized.startswith("notepad delete "):
            delete_arg = stripped[len("notepad delete "):]
        elif normalized.startswith("notes delete "):
            delete_arg = stripped[len("notes delete "):]
        elif normalized.startswith("notepad remove "):
            delete_arg = stripped[len("notepad remove "):]
        if delete_arg is not None:
            note_id = _parse_note_id(delete_arg)
            if note_id is None:
                await self.send("Use NOTEPAD DELETE <number>.\r\n")
            else:
                await _begin_delete_note(self, note_id)
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._notepad_runtime_installed = True
