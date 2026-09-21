from __future__ import annotations

import re
from weakref import WeakSet

from mud.social_experience import _channel_settings, social_allows_message_from


_ACTIVE_SESSIONS: WeakSet = WeakSet()
MAX_OWNED_CHANNELS = 3
MAX_CHANNEL_NAME_LENGTH = 20
_CHANNEL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,19}$")
_RESERVED_NAMES = {
    "chat", "ooc", "create", "join", "leave", "invite", "kick", "mute",
    "unmute", "private", "public", "rename", "close", "info", "list", "help",
}


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS player_chat_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                owner_character_id INTEGER NOT NULL,
                invite_only INTEGER NOT NULL DEFAULT 0 CHECK (invite_only IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS player_chat_channel_members (
                channel_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                owner_muted INTEGER NOT NULL DEFAULT 0 CHECK (owner_muted IN (0, 1)),
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, character_id),
                FOREIGN KEY (channel_id) REFERENCES player_chat_channels(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS player_chat_channel_invites (
                channel_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                invited_by_character_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, character_id),
                FOREIGN KEY (channel_id) REFERENCES player_chat_channels(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by_character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS player_chat_channel_kicks (
                channel_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                kicked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, character_id),
                FOREIGN KEY (channel_id) REFERENCES player_chat_channels(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_player_chat_members_character
                ON player_chat_channel_members(character_id);
            CREATE INDEX IF NOT EXISTS idx_player_chat_invites_character
                ON player_chat_channel_invites(character_id);
            """
        )


def _character(session):
    return getattr(session, "character", None)


def _clean_message(message: str) -> str:
    return " ".join(message.replace("\r", " ").replace("\n", " ").split())[:500]


def _validate_channel_name(name: str) -> str | None:
    candidate = name.strip()
    if not _CHANNEL_NAME_RE.fullmatch(candidate):
        return None
    if candidate.casefold() in _RESERVED_NAMES:
        return None
    return candidate


def _lookup_character(session, name: str):
    database = getattr(session, "database", None)
    if database is None:
        return None
    return database.get_character_by_name(name.strip())


def _session_for_character_id(character_id: int):
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and int(character.id) == int(character_id):
            return session
    return None


def _channel_row(session, name: str):
    _ensure_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT pc.*, c.name AS owner_name
            FROM player_chat_channels pc
            JOIN characters c ON c.id = pc.owner_character_id
            WHERE pc.name = ? COLLATE NOCASE
            """,
            (name.strip(),),
        ).fetchone()


def _member_row(session, channel_id: int, character_id: int):
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT owner_muted
            FROM player_chat_channel_members
            WHERE channel_id = ? AND character_id = ?
            """,
            (channel_id, character_id),
        ).fetchone()


def _is_invited(session, channel_id: int, character_id: int) -> bool:
    with session.database.connect() as db:
        row = db.execute(
            "SELECT 1 FROM player_chat_channel_invites WHERE channel_id = ? AND character_id = ?",
            (channel_id, character_id),
        ).fetchone()
    return row is not None


def _is_kicked(session, channel_id: int, character_id: int) -> bool:
    with session.database.connect() as db:
        row = db.execute(
            "SELECT 1 FROM player_chat_channel_kicks WHERE channel_id = ? AND character_id = ?",
            (channel_id, character_id),
        ).fetchone()
    return row is not None


def _owned_channel_count(session) -> int:
    character = _character(session)
    if character is None:
        return 0
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS count FROM player_chat_channels WHERE owner_character_id = ?",
            (character.id,),
        ).fetchone()
    return int(row["count"])


def _member_counts(session, channel_id: int) -> tuple[int, int]:
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS count FROM player_chat_channel_members WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
        member_ids = {
            int(member["character_id"])
            for member in db.execute(
                "SELECT character_id FROM player_chat_channel_members WHERE channel_id = ?",
                (channel_id,),
            ).fetchall()
        }
    online = 0
    for active in tuple(_ACTIVE_SESSIONS):
        character = _character(active)
        if character is not None and int(character.id) in member_ids:
            online += 1
    return online, int(row["count"])


async def _show_channels(session) -> None:
    character = _character(session)
    if character is None:
        return
    _ensure_schema(session.database)
    chat_enabled, ooc_enabled = _channel_settings(session)
    with session.database.connect() as db:
        rows = db.execute(
            """
            SELECT pc.*, owner.name AS owner_name,
                   CASE WHEN m.character_id IS NULL THEN 0 ELSE 1 END AS joined,
                   CASE WHEN i.character_id IS NULL THEN 0 ELSE 1 END AS invited
            FROM player_chat_channels pc
            JOIN characters owner ON owner.id = pc.owner_character_id
            LEFT JOIN player_chat_channel_members m
              ON m.channel_id = pc.id AND m.character_id = ?
            LEFT JOIN player_chat_channel_invites i
              ON i.channel_id = pc.id AND i.character_id = ?
            ORDER BY pc.name COLLATE NOCASE
            """,
            (character.id, character.id),
        ).fetchall()

    await session.send("\r\n--- Channels ---\r\n")
    await session.send(
        f"Built-in: CHAT [{'ON' if chat_enabled else 'OFF'}]  OOC [{'ON' if ooc_enabled else 'OFF'}]\r\n\r\n"
    )
    if not rows:
        await session.send("No player-created channels yet.  CHANNEL CREATE <name>\r\n")
    else:
        await session.send(f"{'Name':<22} {'Members':<11} {'Access':<12} Status\r\n")
        await session.send(f"{'-' * 20:<22} {'-' * 9:<11} {'-' * 10:<12} {'-' * 8}\r\n")
        for row in rows:
            joined = bool(row["joined"])
            invited = bool(row["invited"])
            status = "joined" if joined else ("invited" if invited else "")
            if bool(row["invite_only"]) and not (
                joined
                or invited
                or int(row["owner_character_id"]) == int(character.id)
            ):
                await session.send(
                    f"{str(row['name']):<22} {'--':<11} {'invite-only':<12} {status}\r\n"
                )
                continue
            online, total = _member_counts(session, int(row["id"]))
            access = "invite-only" if bool(row["invite_only"]) else "public"
            members = f"{online}/{total}"
            await session.send(
                f"{str(row['name']):<22} {members:<11} {access:<12} {status}\r\n"
            )
    await session.send(
        "\r\nCHANNEL JOIN <name>  |  CHANNEL LEAVE <name>  |  CHANNEL INFO <name>\r\n"
        "Talk: CHANNEL <name> <message> or #<name> <message>\r\n"
        "Create: CHANNEL CREATE <name> (free; up to "
        f"{MAX_OWNED_CHANNELS} owned channels)\r\n"
    )


async def _create_channel(session, name: str) -> None:
    character = _character(session)
    if character is None:
        return
    valid_name = _validate_channel_name(name)
    if valid_name is None:
        await session.send(
            f"Channel names must be 2-{MAX_CHANNEL_NAME_LENGTH} characters, start with a letter, "
            "and use only letters, numbers, _ or -.\r\n"
        )
        return
    _ensure_schema(session.database)
    if _owned_channel_count(session) >= MAX_OWNED_CHANNELS:
        await session.send(
            f"You already own {MAX_OWNED_CHANNELS} player-created channels. "
            "Close one before creating another.\r\n"
        )
        return
    try:
        with session.database.connect() as db:
            cursor = db.execute(
                "INSERT INTO player_chat_channels (name, owner_character_id) VALUES (?, ?)",
                (valid_name, character.id),
            )
            channel_id = int(cursor.lastrowid)
            db.execute(
                "INSERT INTO player_chat_channel_members (channel_id, character_id) VALUES (?, ?)",
                (channel_id, character.id),
            )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            await session.send("A player-created channel with that name already exists.\r\n")
            return
        raise
    await session.send(
        f"Channel {valid_name} created as a public channel. "
        f"Use CHANNEL {valid_name} <message> to talk there.\r\n"
    )


async def _join_channel(session, name: str) -> None:
    character = _character(session)
    if character is None:
        return
    row = _channel_row(session, name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    channel_id = int(row["id"])
    if _member_row(session, channel_id, character.id) is not None:
        await session.send(f"You are already connected to {row['name']}.\r\n")
        return
    invited = _is_invited(session, channel_id, character.id)
    if _is_kicked(session, channel_id, character.id) and not invited:
        await session.send(
            f"You were removed from {row['name']}. The owner must invite you back.\r\n"
        )
        return
    if bool(row["invite_only"]) and not invited:
        await session.send("That channel is invite-only. An owner invitation is required.\r\n")
        return
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO player_chat_channel_members (channel_id, character_id) VALUES (?, ?)",
            (channel_id, character.id),
        )
        db.execute(
            "DELETE FROM player_chat_channel_invites WHERE channel_id = ? AND character_id = ?",
            (channel_id, character.id),
        )
        db.execute(
            "DELETE FROM player_chat_channel_kicks WHERE channel_id = ? AND character_id = ?",
            (channel_id, character.id),
        )
    await session.send(f"Connected to {row['name']}.\r\n")


async def _leave_channel(session, name: str) -> None:
    character = _character(session)
    if character is None:
        return
    row = _channel_row(session, name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if int(row["owner_character_id"]) == int(character.id):
        await session.send(
            f"You own {row['name']}. Use CHANNEL CLOSE {row['name']} to shut it down.\r\n"
        )
        return
    with session.database.connect() as db:
        cursor = db.execute(
            "DELETE FROM player_chat_channel_members WHERE channel_id = ? AND character_id = ?",
            (row["id"], character.id),
        )
    if cursor.rowcount:
        await session.send(f"Disconnected from {row['name']}.\r\n")
    else:
        await session.send(f"You are not connected to {row['name']}.\r\n")


async def _show_channel_info(session, name: str) -> None:
    character = _character(session)
    if character is None:
        return
    row = _channel_row(session, name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    member = _member_row(session, int(row["id"]), character.id)
    invited = _is_invited(session, int(row["id"]), character.id)
    if (
        bool(row["invite_only"])
        and member is None
        and not invited
        and int(row["owner_character_id"]) != int(character.id)
    ):
        await session.send(
            f"{row['name']} is an invite-only player channel. Its details are private.\r\n"
        )
        return
    online, total = _member_counts(session, int(row["id"]))
    access = "invite-only" if bool(row["invite_only"]) else "public"
    await session.send(f"\r\n--- Channel: {row['name']} ---\r\n")
    await session.send(
        f"Owner: {row['owner_name']}\r\nAccess: {access}\r\n"
        f"Members: {online} online / {total} total\r\n"
    )
    if member is not None:
        state = "owner-muted" if bool(member["owner_muted"]) else "connected"
        await session.send(f"Your status: {state}\r\n")
    elif invited:
        await session.send("Your status: invited; use CHANNEL JOIN to connect.\r\n")
    else:
        await session.send("Your status: not connected.\r\n")

    if _require_owner(session, row):
        await session.send(
            "\r\nOwner controls:\r\n"
            f"  CHANNEL INVITE {row['name']} <player>\r\n"
            f"  CHANNEL KICK {row['name']} <player>\r\n"
            f"  CHANNEL MUTE {row['name']} <player>\r\n"
            f"  CHANNEL UNMUTE {row['name']} <player>\r\n"
            f"  CHANNEL PRIVATE {row['name']} ON|OFF\r\n"
            f"  CHANNEL RENAME {row['name']} <new-name>\r\n"
            f"  CHANNEL CLOSE {row['name']}\r\n"
        )


def _require_owner(session, row) -> bool:
    character = _character(session)
    return (
        character is not None
        and int(row["owner_character_id"]) == int(character.id)
    )


async def _invite(session, channel_name: str, target_name: str) -> None:
    owner = _character(session)
    row = _channel_row(session, channel_name)
    if owner is None:
        return
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can invite people.\r\n")
        return
    target = _lookup_character(session, target_name)
    if target is None:
        await session.send("No character by that name exists.\r\n")
        return
    if int(target.id) == int(owner.id):
        await session.send("You are already the owner of that channel.\r\n")
        return
    if _member_row(session, int(row["id"]), target.id) is not None:
        await session.send(f"{target.name} is already connected to {row['name']}.\r\n")
        return
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM player_chat_channel_kicks WHERE channel_id = ? AND character_id = ?",
            (row["id"], target.id),
        )
        db.execute(
            """
            INSERT INTO player_chat_channel_invites
                (channel_id, character_id, invited_by_character_id)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_id, character_id) DO UPDATE SET
                invited_by_character_id = excluded.invited_by_character_id,
                created_at = CURRENT_TIMESTAMP
            """,
            (row["id"], target.id, owner.id),
        )
    await session.send(f"{target.name} invited to {row['name']}.\r\n")
    target_session = _session_for_character_id(target.id)
    if target_session is not None:
        await target_session.send(
            f"[Channel invite] {owner.name} invited you to {row['name']}. "
            f"Use CHANNEL JOIN {row['name']}.\r\n"
        )


async def _kick(session, channel_name: str, target_name: str) -> None:
    owner = _character(session)
    row = _channel_row(session, channel_name)
    if owner is None:
        return
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can remove members.\r\n")
        return
    target = _lookup_character(session, target_name)
    if target is None:
        await session.send("No character by that name exists.\r\n")
        return
    if int(target.id) == int(owner.id):
        await session.send(
            "You cannot remove yourself from a channel you own. Close it instead.\r\n"
        )
        return
    if _member_row(session, int(row["id"]), target.id) is None:
        await session.send(f"{target.name} is not connected to {row['name']}.\r\n")
        return
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM player_chat_channel_members WHERE channel_id = ? AND character_id = ?",
            (row["id"], target.id),
        )
        db.execute(
            "DELETE FROM player_chat_channel_invites WHERE channel_id = ? AND character_id = ?",
            (row["id"], target.id),
        )
        db.execute(
            """
            INSERT OR REPLACE INTO player_chat_channel_kicks
                (channel_id, character_id, kicked_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (row["id"], target.id),
        )
    await session.send(
        f"{target.name} removed from {row['name']}. "
        "They must be invited before they can return.\r\n"
    )
    target_session = _session_for_character_id(target.id)
    if target_session is not None:
        await target_session.send(
            f"[Channel] You were removed from {row['name']} by its owner.\r\n"
        )


async def _set_member_mute(
    session, channel_name: str, target_name: str, muted: bool
) -> None:
    owner = _character(session)
    row = _channel_row(session, channel_name)
    if owner is None:
        return
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can moderate member speech.\r\n")
        return
    target = _lookup_character(session, target_name)
    if target is None:
        await session.send("No character by that name exists.\r\n")
        return
    if int(target.id) == int(owner.id):
        await session.send("The channel owner cannot owner-mute themselves.\r\n")
        return
    if _member_row(session, int(row["id"]), target.id) is None:
        await session.send(f"{target.name} is not connected to {row['name']}.\r\n")
        return
    with session.database.connect() as db:
        db.execute(
            """
            UPDATE player_chat_channel_members
            SET owner_muted = ?
            WHERE channel_id = ? AND character_id = ?
            """,
            (1 if muted else 0, row["id"], target.id),
        )
    await session.send(
        f"{target.name} is now {'muted' if muted else 'unmuted'} in {row['name']}.\r\n"
    )
    target_session = _session_for_character_id(target.id)
    if target_session is not None:
        await target_session.send(
            f"[Channel] The owner of {row['name']} "
            f"{'muted' if muted else 'unmuted'} your channel speech.\r\n"
        )


async def _set_private(session, channel_name: str, invite_only: bool) -> None:
    row = _channel_row(session, channel_name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can change channel access.\r\n")
        return
    with session.database.connect() as db:
        db.execute(
            "UPDATE player_chat_channels SET invite_only = ? WHERE id = ?",
            (1 if invite_only else 0, row["id"]),
        )
    await session.send(
        f"{row['name']} is now {'invite-only' if invite_only else 'public'}.\r\n"
    )


async def _rename_channel(session, old_name: str, new_name: str) -> None:
    row = _channel_row(session, old_name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can rename it.\r\n")
        return
    valid_name = _validate_channel_name(new_name)
    if valid_name is None:
        await session.send(
            f"Channel names must be 2-{MAX_CHANNEL_NAME_LENGTH} characters, start with a letter, "
            "and use only letters, numbers, _ or -.\r\n"
        )
        return
    try:
        with session.database.connect() as db:
            db.execute(
                "UPDATE player_chat_channels SET name = ? WHERE id = ?",
                (valid_name, row["id"]),
            )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            await session.send("A player-created channel with that name already exists.\r\n")
            return
        raise
    old_display = str(row["name"])
    await session.send(f"Channel {old_display} renamed to {valid_name}.\r\n")
    with session.database.connect() as db:
        member_ids = [
            int(item["character_id"])
            for item in db.execute(
                "SELECT character_id FROM player_chat_channel_members WHERE channel_id = ?",
                (row["id"],),
            ).fetchall()
        ]
    for character_id in member_ids:
        target_session = _session_for_character_id(character_id)
        if target_session is None or target_session is session:
            continue
        await target_session.send(
            f"[Channel] {old_display} has been renamed to {valid_name}.\r\n"
        )


async def _close_channel(session, name: str) -> None:
    row = _channel_row(session, name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    if not _require_owner(session, row):
        await session.send("Only the channel owner can close it.\r\n")
        return
    with session.database.connect() as db:
        member_ids = [
            int(item["character_id"])
            for item in db.execute(
                "SELECT character_id FROM player_chat_channel_members WHERE channel_id = ?",
                (row["id"],),
            ).fetchall()
        ]
        db.execute("DELETE FROM player_chat_channels WHERE id = ?", (row["id"],))
    await session.send(f"Channel {row['name']} closed.\r\n")
    for character_id in member_ids:
        target_session = _session_for_character_id(character_id)
        if target_session is None or target_session is session:
            continue
        await target_session.send(
            f"[Channel] {row['name']} has been closed by its owner.\r\n"
        )


async def _broadcast(session, channel_name: str, message: str) -> None:
    sender = _character(session)
    if sender is None:
        return
    row = _channel_row(session, channel_name)
    if row is None:
        await session.send("No player-created channel by that name exists.\r\n")
        return
    member = _member_row(session, int(row["id"]), sender.id)
    if member is None:
        await session.send(
            f"You are not connected to {row['name']}. "
            f"Use CHANNEL JOIN {row['name']} first.\r\n"
        )
        return
    if (
        bool(member["owner_muted"])
        and int(row["owner_character_id"]) != int(sender.id)
    ):
        await session.send(
            f"The owner has muted your speech in {row['name']}.\r\n"
        )
        return
    cleaned = _clean_message(message)
    if not cleaned:
        await session.send(f"Say what on {row['name']}?\r\n")
        return
    with session.database.connect() as db:
        member_ids = {
            int(item["character_id"])
            for item in db.execute(
                "SELECT character_id FROM player_chat_channel_members WHERE channel_id = ?",
                (row["id"],),
            ).fetchall()
        }
    delivered_to_self = False
    for other in tuple(_ACTIVE_SESSIONS):
        other_character = _character(other)
        if other_character is None or int(other_character.id) not in member_ids:
            continue
        if (
            other is not session
            and not social_allows_message_from(other, sender.name)
        ):
            continue
        try:
            await other.send(f"{row['name']} | {sender.name}: {cleaned}\r\n")
            if other is session:
                delivered_to_self = True
        except (ConnectionError, RuntimeError):
            continue
    if not delivered_to_self:
        await session.send(f"{row['name']} | {sender.name}: {cleaned}\r\n")


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_player_channels_runtime(player_session_class) -> None:
    """Install free, discoverable player-created chat channels and owner moderation."""
    if getattr(player_session_class, "_player_channels_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if _character(self) is not None:
                _ensure_schema(self.database)
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

        _ensure_schema(self.database)
        _ACTIVE_SESSIONS.add(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        if normalized in {"channels", "channel", "channel list", "channel help"}:
            await _show_channels(self)
            return

        if stripped.startswith("#") and len(stripped) > 1:
            shortcut = stripped[1:].split(maxsplit=1)
            if len(shortcut) < 2:
                await self.send("Use #<channel> <message>.\r\n")
            else:
                await _broadcast(self, shortcut[0], shortcut[1])
            return

        parts = stripped.split()
        lower_parts = [part.lower() for part in parts]
        if (
            len(lower_parts) == 3
            and lower_parts[0] == "channel"
            and lower_parts[1] in {"chat", "ooc"}
            and lower_parts[2] in {"on", "off"}
        ):
            await _delegate_command(self, previous_playing_prompt, command)
            return

        if len(parts) >= 2 and lower_parts[0] == "channel":
            action = lower_parts[1]
            if action == "create":
                if len(parts) != 3:
                    await self.send("Use CHANNEL CREATE <name>.\r\n")
                else:
                    await _create_channel(self, parts[2])
                return
            if action == "join":
                if len(parts) != 3:
                    await self.send("Use CHANNEL JOIN <name>.\r\n")
                else:
                    await _join_channel(self, parts[2])
                return
            if action == "leave":
                if len(parts) != 3:
                    await self.send("Use CHANNEL LEAVE <name>.\r\n")
                else:
                    await _leave_channel(self, parts[2])
                return
            if action == "info":
                if len(parts) != 3:
                    await self.send("Use CHANNEL INFO <name>.\r\n")
                else:
                    await _show_channel_info(self, parts[2])
                return
            if action == "invite":
                if len(parts) != 4:
                    await self.send("Use CHANNEL INVITE <name> <player>.\r\n")
                else:
                    await _invite(self, parts[2], parts[3])
                return
            if action == "kick":
                if len(parts) != 4:
                    await self.send("Use CHANNEL KICK <name> <player>.\r\n")
                else:
                    await _kick(self, parts[2], parts[3])
                return
            if action in {"mute", "unmute"}:
                if len(parts) != 4:
                    await self.send(
                        f"Use CHANNEL {action.upper()} <name> <player>.\r\n"
                    )
                else:
                    await _set_member_mute(
                        self, parts[2], parts[3], action == "mute"
                    )
                return
            if action == "private":
                if len(parts) != 4 or lower_parts[3] not in {"on", "off"}:
                    await self.send("Use CHANNEL PRIVATE <name> ON|OFF.\r\n")
                else:
                    await _set_private(
                        self, parts[2], lower_parts[3] == "on"
                    )
                return
            if action == "public":
                if len(parts) != 3:
                    await self.send("Use CHANNEL PUBLIC <name>.\r\n")
                else:
                    await _set_private(self, parts[2], False)
                return
            if action == "rename":
                if len(parts) != 4:
                    await self.send("Use CHANNEL RENAME <old> <new>.\r\n")
                else:
                    await _rename_channel(self, parts[2], parts[3])
                return
            if action == "close":
                if len(parts) != 3:
                    await self.send("Use CHANNEL CLOSE <name>.\r\n")
                else:
                    await _close_channel(self, parts[2])
                return

            if len(parts) >= 3:
                await _broadcast(
                    self, parts[1], stripped.split(maxsplit=2)[2]
                )
                return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._player_channels_runtime_installed = True
