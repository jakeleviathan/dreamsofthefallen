from __future__ import annotations

from weakref import WeakSet

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY


_ACTIVE_SESSIONS: WeakSet = WeakSet()


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS character_friends (
                character_id INTEGER NOT NULL,
                friend_character_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, friend_character_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (friend_character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_ignores (
                character_id INTEGER NOT NULL,
                ignored_character_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, ignored_character_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (ignored_character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_channels (
                character_id INTEGER PRIMARY KEY,
                chat_enabled INTEGER NOT NULL DEFAULT 1,
                ooc_enabled INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _clean_message(message: str) -> str:
    return " ".join(message.replace("\r", " ").replace("\n", " ").split())[:500]


def _character(session):
    return getattr(session, "character", None)


def _lookup_character(session, name: str):
    database = getattr(session, "database", None)
    if database is None:
        return None
    return database.get_character_by_name(name.strip())


def _session_for_character_name(name: str):
    needle = name.strip().lower()
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and str(character.name).lower() == needle:
            return session
    return None


def _is_ignored_by_id(session, sender_character_id: int) -> bool:
    character = _character(session)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return False
    _ensure_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT 1 FROM character_ignores WHERE character_id = ? AND ignored_character_id = ?",
            (character.id, sender_character_id),
        ).fetchone()
    return row is not None


def social_allows_message_from(session, sender_name: str) -> bool:
    sender = _lookup_character(session, sender_name)
    if sender is None:
        return True
    return not _is_ignored_by_id(session, sender.id)


def _channel_settings(session) -> tuple[bool, bool]:
    character = _character(session)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return True, True
    _ensure_schema(database)
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO character_channels (character_id) VALUES (?)",
            (character.id,),
        )
        row = db.execute(
            "SELECT chat_enabled, ooc_enabled FROM character_channels WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    return bool(row["chat_enabled"]), bool(row["ooc_enabled"])


def _set_channel(session, channel: str, enabled: bool) -> None:
    character = _character(session)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return
    _ensure_schema(database)
    column = "chat_enabled" if channel == "chat" else "ooc_enabled"
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO character_channels (character_id) VALUES (?)",
            (character.id,),
        )
        db.execute(
            f"UPDATE character_channels SET {column} = ? WHERE character_id = ?",
            (1 if enabled else 0, character.id),
        )


def _friend_rows(session):
    character = _character(session)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return []
    _ensure_schema(database)
    with database.connect() as db:
        return db.execute(
            """
            SELECT c.id, c.name, c.level, c.race, c.character_class
            FROM character_friends f
            JOIN characters c ON c.id = f.friend_character_id
            WHERE f.character_id = ?
            ORDER BY c.name COLLATE NOCASE
            """,
            (character.id,),
        ).fetchall()


def _ignore_rows(session):
    character = _character(session)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return []
    _ensure_schema(database)
    with database.connect() as db:
        return db.execute(
            """
            SELECT c.id, c.name
            FROM character_ignores i
            JOIN characters c ON c.id = i.ignored_character_id
            WHERE i.character_id = ?
            ORDER BY c.name COLLATE NOCASE
            """,
            (character.id,),
        ).fetchall()


def _is_online(character_id: int) -> bool:
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and character.id == character_id:
            return True
    return False


async def _send_channels(session) -> None:
    chat, ooc = _channel_settings(session)
    await session.send(
        "\r\n--- Communication ---\r\n"
        "SAY <message> - people in your current room\r\n"
        f"CHAT <message> - world chat [{('ON' if chat else 'OFF')}]\r\n"
        f"OOC <message> - out-of-character channel [{('ON' if ooc else 'OFF')}]\r\n"
        "TELL <name> <message> - private message\r\n"
        "REPLY <message> - reply to the most recent private sender\r\n"
        "CHANNEL CHAT ON|OFF / CHANNEL OOC ON|OFF - mute or unmute channels\r\n"
        "FRIENDS / FRIEND <name> / UNFRIEND <name> - personal contact list\r\n"
        "IGNORES / IGNORE <name> / UNIGNORE <name> - block player communication\r\n"
        "WHO - see characters currently connected\r\n"
    )


async def _broadcast_channel(session, channel: str, message: str) -> None:
    character = _character(session)
    if character is None:
        return
    cleaned = _clean_message(message)
    if not cleaned:
        await session.send(f"{channel.upper()} what?\r\n")
        return
    chat_enabled, ooc_enabled = _channel_settings(session)
    enabled = chat_enabled if channel == "chat" else ooc_enabled
    if not enabled:
        await session.send(
            f"The {channel.upper()} channel is muted for you. Use CHANNEL {channel.upper()} ON first.\r\n"
        )
        return

    label = "Chat" if channel == "chat" else "OOC"
    sender_id = character.id
    delivered_to_self = False
    for other in tuple(_ACTIVE_SESSIONS):
        other_character = _character(other)
        if other_character is None:
            continue
        other_chat, other_ooc = _channel_settings(other)
        if not (other_chat if channel == "chat" else other_ooc):
            continue
        if other is not session and _is_ignored_by_id(other, sender_id):
            continue
        try:
            await other.send(f"[{label}] {character.name}: {cleaned}\r\n")
            if other is session:
                delivered_to_self = True
        except (ConnectionError, RuntimeError):
            continue
    if not delivered_to_self:
        await session.send(f"[{label}] {character.name}: {cleaned}\r\n")


async def _tell(session, target_name: str, message: str) -> None:
    sender = _character(session)
    if sender is None:
        return
    cleaned = _clean_message(message)
    if not cleaned:
        await session.send("Tell them what?\r\n")
        return
    target_character = _lookup_character(session, target_name)
    if target_character is None:
        await session.send("No character by that name exists.\r\n")
        return
    if target_character.id == sender.id:
        await session.send("You do not need TELL to talk to yourself.\r\n")
        return
    target_session = _session_for_character_name(target_character.name)
    if target_session is None:
        await session.send(f"{target_character.name} is not online.\r\n")
        return
    if _is_ignored_by_id(target_session, sender.id):
        await session.send(f"{target_character.name} is not accepting messages from you.\r\n")
        return

    await target_session.send(f"[Tell from {sender.name}] {cleaned}\r\n")
    await session.send(f"[Tell to {target_character.name}] {cleaned}\r\n")
    target_session._last_tell_from = sender.name
    session._last_tell_to = target_character.name


async def _show_friends(session) -> None:
    rows = _friend_rows(session)
    await session.send("\r\n--- Friends ---\r\n")
    if not rows:
        await session.send("No friends saved yet. Use FRIEND <name>.\r\n")
        return
    for row in rows:
        status = "online" if _is_online(int(row["id"])) else "offline"
        await session.send(f"{row['name']} - {status}\r\n")


async def _show_ignores(session) -> None:
    rows = _ignore_rows(session)
    await session.send("\r\n--- Ignored Characters ---\r\n")
    if not rows:
        await session.send("You are not ignoring anyone.\r\n")
        return
    for row in rows:
        await session.send(f"{row['name']}\r\n")


async def _friend(session, target_name: str, remove: bool = False) -> None:
    character = _character(session)
    target = _lookup_character(session, target_name)
    if character is None:
        return
    if target is None:
        await session.send("No character by that name exists.\r\n")
        return
    if target.id == character.id:
        await session.send("Your own character does not need to be on your friends list.\r\n")
        return
    _ensure_schema(session.database)
    with session.database.connect() as db:
        if remove:
            cursor = db.execute(
                "DELETE FROM character_friends WHERE character_id = ? AND friend_character_id = ?",
                (character.id, target.id),
            )
        else:
            cursor = db.execute(
                "INSERT OR IGNORE INTO character_friends (character_id, friend_character_id) VALUES (?, ?)",
                (character.id, target.id),
            )
    if remove:
        await session.send(
            f"{target.name} removed from your friends list.\r\n"
            if cursor.rowcount
            else f"{target.name} was not on your friends list.\r\n"
        )
    else:
        await session.send(f"{target.name} added to your friends list.\r\n")


async def _ignore(session, target_name: str, remove: bool = False) -> None:
    character = _character(session)
    target = _lookup_character(session, target_name)
    if character is None:
        return
    if target is None:
        await session.send("No character by that name exists.\r\n")
        return
    if target.id == character.id:
        await session.send("You cannot ignore yourself.\r\n")
        return
    _ensure_schema(session.database)
    with session.database.connect() as db:
        if remove:
            cursor = db.execute(
                "DELETE FROM character_ignores WHERE character_id = ? AND ignored_character_id = ?",
                (character.id, target.id),
            )
        else:
            cursor = db.execute(
                "INSERT OR IGNORE INTO character_ignores (character_id, ignored_character_id) VALUES (?, ?)",
                (character.id, target.id),
            )
    if remove:
        await session.send(
            f"{target.name} is no longer ignored.\r\n"
            if cursor.rowcount
            else f"{target.name} was not ignored.\r\n"
        )
    else:
        await session.send(
            f"{target.name} is now ignored for SAY, CHAT, OOC, and private tells.\r\n"
        )


async def _who(session) -> None:
    rows = []
    for other in tuple(_ACTIVE_SESSIONS):
        character = _character(other)
        if character is None:
            continue
        race = RACES_BY_KEY.get(character.race or "")
        klass = CLASSES_BY_KEY.get(character.character_class or "")
        rows.append((
            character.name,
            int(character.level),
            race.name if race else (character.race or "Unknown"),
            klass.name if klass else (character.character_class or "Unknown").title(),
        ))
    rows.sort(key=lambda value: value[0].lower())
    await session.send(f"\r\n--- Who Is In Astralis ({len(rows)}) ---\r\n")
    for name, level, race, klass in rows:
        await session.send(f"{name} - Level {level} {race} {klass}\r\n")
    if not rows:
        await session.send("No characters are currently visible as connected.\r\n")


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
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


def install_social_experience_runtime(player_session_class) -> None:
    """Install clear local/global/private communication plus friend/ignore tools."""
    if getattr(player_session_class, "_social_experience_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if _character(self) is not None:
                _ensure_schema(self.database)
                _channel_settings(self)
                _ACTIVE_SESSIONS.add(self)

        player_session_class.enter_character = enter_character

    previous_close = getattr(player_session_class, "close", None)
    if previous_close is not None:
        async def close(self) -> None:
            _ACTIVE_SESSIONS.discard(self)
            await previous_close(self)

        player_session_class.close = close

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if _character(self) is None:
            await previous_playing_prompt(self)
            return

        _ACTIVE_SESSIONS.add(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"channels", "channel", "social", "communication"}:
            await _send_channels(self)
            return
        if normalized.startswith("channel "):
            parts = normalized.split()
            if len(parts) == 3 and parts[1] in {"chat", "ooc"} and parts[2] in {"on", "off"}:
                enabled = parts[2] == "on"
                _set_channel(self, parts[1], enabled)
                await self.send(f"{parts[1].upper()} channel {'enabled' if enabled else 'muted'}.\r\n")
            else:
                await self.send("Use CHANNEL CHAT ON|OFF or CHANNEL OOC ON|OFF.\r\n")
            return

        if normalized == "chat":
            await self.send("CHAT what?\r\n")
            return
        if normalized.startswith("chat "):
            await _broadcast_channel(self, "chat", stripped[5:])
            return
        if normalized == "ooc":
            await self.send("OOC what?\r\n")
            return
        if normalized.startswith("ooc "):
            await _broadcast_channel(self, "ooc", stripped[4:])
            return

        if normalized == "tell" or normalized.startswith("tell "):
            parts = stripped.split(maxsplit=2)
            if len(parts) < 3:
                await self.send("Use TELL <name> <message>.\r\n")
            else:
                await _tell(self, parts[1], parts[2])
            return
        if normalized == "reply" or normalized.startswith("reply "):
            message = stripped[6:].strip() if len(stripped) > 5 else ""
            target = getattr(self, "_last_tell_from", None)
            if not target:
                await self.send("Nobody has sent you a private tell to reply to yet.\r\n")
                return
            await _tell(self, target, message)
            return

        if normalized in {"friends", "friend list"}:
            await _show_friends(self)
            return
        if normalized.startswith("friend "):
            await _friend(self, stripped.split(maxsplit=1)[1])
            return
        if normalized.startswith("unfriend "):
            await _friend(self, stripped.split(maxsplit=1)[1], remove=True)
            return

        if normalized in {"ignores", "ignore list", "ignored"}:
            await _show_ignores(self)
            return
        if normalized.startswith("ignore "):
            await _ignore(self, stripped.split(maxsplit=1)[1])
            return
        if normalized.startswith("unignore "):
            await _ignore(self, stripped.split(maxsplit=1)[1], remove=True)
            return

        if normalized in {"who", "who is online", "online"}:
            await _who(self)
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.social_allows_message_from = social_allows_message_from
    player_session_class.playing_prompt = playing_prompt
    player_session_class._social_experience_runtime_installed = True
