from __future__ import annotations

import os
import time
from dataclasses import replace
from weakref import WeakSet

from mud.crafting import ITEMS_BY_KEY
from mud.quests import QUESTS_BY_KEY
from mud.world import ROOMS_BY_KEY


ROLE_ORDER = {
    "player": 0,
    "helper": 1,
    "gm": 2,
    "builder": 3,
    "admin": 4,
    "owner": 5,
}
VALID_STAFF_ROLES = tuple(role for role in ROLE_ORDER if role != "player")
_ACTIVE_SESSIONS: WeakSet = WeakSet()
_CONFIRM_SECONDS = 30.0
_POSSESS_SECONDS = 300.0


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS staff_roles (
                account_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                granted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS staff_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actor_account_id INTEGER,
                actor_account_name TEXT NOT NULL,
                actor_character_name TEXT,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                details TEXT NOT NULL DEFAULT ''
            );
            """
        )


def _owner_bootstrap_name() -> str:
    return os.environ.get("MUD_OWNER_ACCOUNT", "").strip().lower()


def _role_for(session) -> str:
    account = getattr(session, "account", None)
    database = getattr(session, "database", None)
    if account is None or database is None:
        return "player"
    _ensure_schema(database)
    if _owner_bootstrap_name() and account.name.lower() == _owner_bootstrap_name():
        with database.connect() as db:
            db.execute(
                "INSERT INTO staff_roles (account_id, role) VALUES (?, 'owner') "
                "ON CONFLICT(account_id) DO UPDATE SET role = 'owner'",
                (account.id,),
            )
        return "owner"
    with database.connect() as db:
        row = db.execute(
            "SELECT role FROM staff_roles WHERE account_id = ?",
            (account.id,),
        ).fetchone()
    if row is None:
        return "player"
    role = str(row["role"]).lower()
    return role if role in ROLE_ORDER else "player"


def _has_role(session, minimum: str) -> bool:
    return ROLE_ORDER[_role_for(session)] >= ROLE_ORDER[minimum]


def _staff_mode(session) -> bool:
    return bool(getattr(session, "_staff_mode", False))


def _audit(session, action: str, target: str = "", details: str = "") -> None:
    database = getattr(session, "database", None)
    account = getattr(session, "account", None)
    if database is None or account is None:
        return
    _ensure_schema(database)
    character = getattr(session, "character", None)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO staff_audit_log (
                actor_account_id, actor_account_name, actor_character_name,
                actor_role, action, target, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account.id,
                account.name,
                getattr(character, "name", None),
                _role_for(session),
                action,
                target or None,
                details,
            ),
        )


def _clean_text(text: str, limit: int = 400) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())[:limit]


def _online_sessions() -> list:
    result = []
    for session in tuple(_ACTIVE_SESSIONS):
        if getattr(session, "character", None) is None:
            continue
        result.append(session)
    return sorted(result, key=lambda s: s.character.name.lower())


def _find_online_player(name: str):
    needle = name.strip().lower()
    for session in _online_sessions():
        if session.character.name.lower() == needle:
            return session
    return None


def _room_label(room_key: str | None) -> str:
    if not room_key:
        return "nowhere"
    room = ROOMS_BY_KEY.get(room_key)
    return room.name if room is not None else room_key


def _active_quest_rows(session, character_id: int):
    try:
        return [row for row in session.database.list_quests(character_id) if row.get("status") == "active"]
    except Exception:
        return []


def _quest_label(row) -> tuple[str, str]:
    key = str(row.get("quest_key") or "")
    step = str(row.get("current_step") or "")
    definition = QUESTS_BY_KEY.get(key)
    if definition is None:
        return key, step
    objective = definition.objective_for_step(step) or step
    return definition.name, objective


def _find_quest(session, character_id: int, query: str):
    needle = " ".join(query.lower().split())
    for row in session.database.list_quests(character_id):
        key = str(row.get("quest_key") or "")
        definition = QUESTS_BY_KEY.get(key)
        names = {key.lower(), key.replace("_", " ").lower()}
        if definition is not None:
            names.add(definition.name.lower())
        if needle in names or any(needle and needle in candidate for candidate in names):
            return row, definition
    return None, None


def _first_step(definition) -> str | None:
    if definition is None or not definition.objective_steps:
        return None
    return definition.objective_steps[0][0]


def _pending(session):
    pending = getattr(session, "_staff_pending_confirmation", None)
    if not pending:
        return None
    if time.monotonic() > pending["expires"]:
        session._staff_pending_confirmation = None
        return None
    return pending


async def _queue_confirmation(session, action: str, data: dict, description: str) -> None:
    session._staff_pending_confirmation = {
        "action": action,
        "data": data,
        "expires": time.monotonic() + _CONFIRM_SECONDS,
    }
    await session.send(
        f"\r\nConfirmation required: {description}\r\n"
        f"Type CONFIRM within {int(_CONFIRM_SECONDS)} seconds, or CANCEL.\r\n"
    )


async def _stop_combat_safely(session) -> None:
    stop = getattr(session, "_stop_combat", None)
    if stop is not None:
        await stop()


async def _relocate(session, room_key: str) -> None:
    await _stop_combat_safely(session)
    session.database.set_character_room(session.character.id, room_key)
    session.character = replace(session.character, current_room=room_key)
    await session.show_current_room()


async def _dashboard(session) -> None:
    online = _online_sessions()
    await session.send("\r\n--- Staff Console ---\r\n")
    await session.send(f"Role: {_role_for(session).upper()}    Staff mode: {'ON' if _staff_mode(session) else 'OFF'}\r\n")
    await session.send(f"Online characters: {len(online)}\r\n")
    attention = []
    for other in online:
        character = other.character
        flags = set()
        try:
            flags = set(other.database.list_flags(character.id))
        except Exception:
            pass
        marker = ""
        if "mud_basics_stuck_hint_shown" in flags and "mud_basics_confident" not in flags:
            marker = "  [may need help]"
            attention.append(character.name)
        await session.send(
            f"  {character.name:<18} Lv {character.level:<3} {_room_label(character.current_room)}{marker}\r\n"
        )
    if attention:
        await session.send("Attention: " + ", ".join(attention) + "\r\n")
    else:
        await session.send("Attention: nobody is currently flagged as a stuck newcomer.\r\n")

    moments = []
    now = time.monotonic()
    for other in online:
        until = float(getattr(other, "_staff_possess_until", 0.0) or 0.0)
        npc = getattr(other, "_staff_possessed_npc", None)
        if npc and until > now:
            moments.append(f"{other.character.name} as {npc} ({int(until - now)}s left)")
    await session.send(
        "Live GM moments: " + (", ".join(moments) if moments else "none") + "\r\n"
    )
    await session.send("Use STAFF HELP for the control list.\r\n")


async def _inspect_player(session, target_name: str) -> None:
    target = _find_online_player(target_name)
    character = target.character if target is not None else session.database.get_character_by_name(target_name)
    if character is None:
        await session.send("No character by that name was found.\r\n")
        return
    await session.send(f"\r\n--- GM: {character.name} ---\r\n")
    await session.send(
        f"Level {character.level}  Race {character.race or 'unknown'}  Class {character.character_class or 'unknown'}\r\n"
        f"Room: {_room_label(character.current_room)} [{character.current_room or 'none'}]\r\n"
        f"Status: {'ONLINE' if target is not None else 'OFFLINE'}\r\n"
    )
    if target is not None and getattr(target, "active_enemy", None) is not None:
        await session.send(f"Combat: {target.active_enemy.definition.name}\r\n")
    quests = _active_quest_rows(session, character.id)
    if quests:
        await session.send("Active quests:\r\n")
        for row in quests:
            name, objective = _quest_label(row)
            await session.send(f"  {name}: {objective}\r\n")
    else:
        await session.send("Active quests: none\r\n")
    try:
        flags = set(session.database.list_flags(character.id))
    except Exception:
        flags = set()
    if "mud_basics_stuck_hint_shown" in flags and "mud_basics_confident" not in flags:
        await session.send("Support note: beginner guidance has detected repeated unknown commands.\r\n")


async def _inventory(session, target_name: str) -> None:
    character = session.database.get_character_by_name(target_name)
    if character is None:
        await session.send("No character by that name was found.\r\n")
        return
    await session.send(f"\r\n--- {character.name}: Inventory ---\r\n")
    rows = session.database.list_items(character.id)
    if not rows:
        await session.send("Empty.\r\n")
        return
    for row in rows:
        key = str(row["item_key"])
        definition = ITEMS_BY_KEY.get(key)
        name = getattr(definition, "name", key)
        await session.send(f"  {int(row['quantity'])}x {name} [{key}]\r\n")


async def _goto(session, target_name: str, *, observe: bool = False) -> None:
    target = _find_online_player(target_name)
    if target is None or target.character.current_room is None:
        await session.send("That character is not online in a valid room.\r\n")
        return
    if observe:
        session._staff_invisible = True
    await _relocate(session, target.character.current_room)
    _audit(session, "observe" if observe else "goto", target.character.name, target.character.current_room)
    await session.send(
        f"Staff movement: now at {_room_label(target.character.current_room)}"
        + (" in invisible observation mode.\r\n" if observe else ".\r\n")
    )


async def _echo(session, text: str) -> None:
    clean = _clean_text(text)
    if not clean:
        await session.send("Use GM ECHO <text>.\r\n")
        return
    room_key = session.character.current_room
    for other in _online_sessions():
        if other.character.current_room == room_key:
            await other.send(f"\r\n{clean}\r\n")
    _audit(session, "echo", room_key or "", clean)


def _find_mobile_npc(session, query: str):
    manager = getattr(session, "mobile_npcs", None)
    if manager is None:
        return None
    needle = " ".join(query.lower().split())
    for key, state in manager.states.items():
        definition = state.definition
        names = {key.lower(), definition.name.lower(), *[str(a).lower() for a in definition.aliases]}
        if needle in names or any(needle and needle in name for name in names):
            return state
    return None


async def _possess(session, npc_query: str) -> None:
    state = _find_mobile_npc(session, npc_query)
    if state is None:
        await session.send("No mobile NPC by that name was found.\r\n")
        return
    session._staff_possessed_npc = state.definition.name
    session._staff_possessed_npc_key = state.definition.key
    session._staff_possess_until = time.monotonic() + _POSSESS_SECONDS
    _audit(session, "possess", state.definition.name, "five-minute GM performance window")
    await session.send(
        f"You are now puppeteering {state.definition.name} for up to five minutes. "
        "Use GM SPEAK <text>, GM EMOTE <text>, or GM RELEASE.\r\n"
    )


def _possessed_state(session):
    until = float(getattr(session, "_staff_possess_until", 0.0) or 0.0)
    if time.monotonic() > until:
        session._staff_possessed_npc = None
        session._staff_possessed_npc_key = None
        return None
    key = getattr(session, "_staff_possessed_npc_key", None)
    manager = getattr(session, "mobile_npcs", None)
    return manager.states.get(key) if manager is not None and key else None


async def _puppet_speak(session, text: str, *, emote: bool = False) -> None:
    state = _possessed_state(session)
    if state is None:
        await session.send("You are not currently possessing a mobile NPC.\r\n")
        return
    clean = _clean_text(text, 280)
    if not clean:
        await session.send("Give the NPC something to say or do.\r\n")
        return
    if emote:
        line = f"{state.definition.name} {clean}\r\n"
        action = "possess_emote"
    else:
        line = f'{state.definition.name} says, "{clean}"\r\n'
        action = "possess_speak"
    for other in _online_sessions():
        if other.character.current_room == state.current_room_key:
            await other.send("\r\n" + line)
    _audit(session, action, state.definition.name, clean)


async def _confirm(session) -> None:
    pending = _pending(session)
    if pending is None:
        await session.send("There is no staff action waiting for confirmation.\r\n")
        return
    session._staff_pending_confirmation = None
    action = pending["action"]
    data = pending["data"]

    if action == "bring":
        target = _find_online_player(data["target"])
        if target is None or session.character.current_room is None:
            await session.send("The target is no longer online, so nothing changed.\r\n")
            return
        await _relocate(target, session.character.current_room)
        await target.send(f"\r\nA GM has relocated you to {_room_label(session.character.current_room)}.\r\n")
        _audit(session, "bring", target.character.name, session.character.current_room)
        await session.send(f"{target.character.name} has been brought here.\r\n")
        return

    if action == "reset_quest":
        character = session.database.get_character_by_name(data["target"])
        if character is None:
            await session.send("The character no longer exists. Nothing changed.\r\n")
            return
        row, definition = _find_quest(session, character.id, data["quest"])
        if row is None or definition is None:
            await session.send("That quest could not be resolved. Nothing changed.\r\n")
            return
        first_step = _first_step(definition)
        with session.database.connect() as db:
            db.execute(
                """
                UPDATE character_quests
                SET status = 'active', current_step = ?, completed_at = NULL,
                    started_at = CURRENT_TIMESTAMP
                WHERE character_id = ? AND quest_key = ?
                """,
                (first_step, character.id, definition.key),
            )
        _audit(session, "reset_quest", character.name, f"{definition.key} -> {first_step}")
        await session.send(
            f"{character.name}'s quest '{definition.name}' was reset to its first journal step. "
            "World flags, rewards, and inventory were intentionally left untouched.\r\n"
        )
        return

    if action == "restore_npc":
        state = _find_mobile_npc(session, data["npc"])
        if state is None:
            await session.send("That mobile NPC could not be resolved. Nothing changed.\r\n")
            return
        definition = state.definition
        state.current_room_key = definition.spawn_room_key
        state.engaged_character_id = None
        state.returning_to_duty = False
        state.inactive_ticks = 0
        if definition.patrol_route:
            try:
                state.patrol_index = definition.patrol_route.index(definition.spawn_room_key)
            except ValueError:
                state.patrol_index = 0
        _audit(session, "restore_npc", definition.name, definition.spawn_room_key)
        await session.send(f"{definition.name} has been restored to {_room_label(definition.spawn_room_key)}.\r\n")
        return


async def _staff_help(session) -> None:
    role = _role_for(session)
    await session.send(
        "\r\n--- Staff Controls ---\r\n"
        f"Your role: {role.upper()}\r\n"
        "STAFF ON / STAFF OFF - enter or leave staff mode\r\n"
        "GM or GM DASHBOARD - online players, attention flags, live GM moments\r\n"
        "GM <player> - compact player/quest status card\r\n"
        "GM INVENTORY <player> - inspect inventory\r\n"
    )
    if ROLE_ORDER[role] >= ROLE_ORDER["gm"]:
        await session.send(
            "GM GOTO <player> - move to an online player\r\n"
            "GM OBSERVE <player> - move there in invisible observation mode\r\n"
            "GM VISIBLE / GM INVISIBLE - set your staff-presence mode\r\n"
            "GM BRING <player> - relocate a player here after confirmation\r\n"
            "GM RESET QUEST <player> <quest> - safe journal reset after confirmation\r\n"
            "GM RESTORE NPC <npc> - restore a mobile NPC to its authored spawn after confirmation\r\n"
            "GM ECHO <text> - send an atmospheric line to this room\r\n"
            "GM POSSESS <mobile npc> - puppeteer it for five minutes\r\n"
            "GM SPEAK <text> / GM EMOTE <text> / GM RELEASE - perform through that NPC\r\n"
        )
    if ROLE_ORDER[role] >= ROLE_ORDER["admin"]:
        await session.send("STAFF AUDIT [count] - view recent staff actions\r\n")
    if role == "owner":
        await session.send("STAFF ROLE <account> <helper|gm|builder|admin|owner|player> - assign access\r\n")
    await session.send("Disruptive actions use CONFIRM/CANCEL and all staff actions are audited.\r\n")


async def _audit_view(session, count: int = 15) -> None:
    count = max(1, min(50, count))
    _ensure_schema(session.database)
    with session.database.connect() as db:
        rows = db.execute(
            """
            SELECT created_at, actor_account_name, actor_character_name, actor_role,
                   action, target, details
            FROM staff_audit_log ORDER BY id DESC LIMIT ?
            """,
            (count,),
        ).fetchall()
    await session.send("\r\n--- Staff Audit ---\r\n")
    if not rows:
        await session.send("No staff actions have been recorded yet.\r\n")
        return
    for row in rows:
        actor = row["actor_character_name"] or row["actor_account_name"]
        target = f" -> {row['target']}" if row["target"] else ""
        detail = f" ({row['details']})" if row["details"] else ""
        await session.send(
            f"{row['created_at']}  {actor} [{row['actor_role']}]  {row['action']}{target}{detail}\r\n"
        )


async def _assign_role(session, account_name: str, role: str) -> None:
    role = role.lower()
    if role not in ROLE_ORDER:
        await session.send("Unknown role. Use player, helper, gm, builder, admin, or owner.\r\n")
        return
    with session.database.connect() as db:
        row = db.execute("SELECT id, name FROM accounts WHERE name = ?", (account_name,)).fetchone()
        if row is None:
            await session.send("No account by that name exists.\r\n")
            return
        if role == "player":
            db.execute("DELETE FROM staff_roles WHERE account_id = ?", (row["id"],))
        else:
            db.execute(
                "INSERT INTO staff_roles (account_id, role) VALUES (?, ?) "
                "ON CONFLICT(account_id) DO UPDATE SET role = excluded.role, granted_at = CURRENT_TIMESTAMP",
                (row["id"], role),
            )
    _audit(session, "assign_role", str(row["name"]), role)
    await session.send(f"Staff role for {row['name']} set to {role.upper()}.\r\n")


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    previous = self.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = previous
        else:
            self.__dict__.pop("prompt", None)


def install_staff_control_runtime(player_session_class) -> None:
    """Install role-gated, audited GM controls as a calm operator layer."""
    if getattr(player_session_class, "_staff_control_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_close = player_session_class.close
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if getattr(self, "character", None) is not None:
            _ACTIVE_SESSIONS.add(self)
            self._staff_mode = False
            self._staff_invisible = False

    async def close(self) -> None:
        _ACTIVE_SESSIONS.discard(self)
        await previous_close(self)

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return
        _ACTIVE_SESSIONS.add(self)
        prompt = "\r\n" + (self.current_prompt_text() if hasattr(self, "current_prompt_text") else "> ")
        command = await self.prompt(prompt)
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized == "staff" or normalized == "staff help":
            if _role_for(self) == "player":
                await self.send("This account does not have staff access.\r\n")
                return
            await _staff_help(self)
            return
        if normalized == "staff on":
            role = _role_for(self)
            if role == "player":
                await self.send("This account does not have staff access.\r\n")
                return
            self._staff_mode = True
            _audit(self, "staff_mode_on")
            await self.send(f"Staff mode enabled as {role.upper()}. Type GM for the console.\r\n")
            return
        if normalized == "staff off":
            if _role_for(self) == "player":
                await self.send("This account does not have staff access.\r\n")
                return
            self._staff_mode = False
            self._staff_invisible = False
            self._staff_possessed_npc = None
            self._staff_possessed_npc_key = None
            _audit(self, "staff_mode_off")
            await self.send("Staff mode disabled.\r\n")
            return

        if normalized == "confirm" and _pending(self) is not None:
            await _confirm(self)
            return
        if normalized == "cancel" and _pending(self) is not None:
            self._staff_pending_confirmation = None
            await self.send("Staff action cancelled.\r\n")
            return

        if normalized.startswith("staff role "):
            if not _staff_mode(self) or _role_for(self) != "owner":
                await self.send("Only an OWNER in staff mode can assign staff roles.\r\n")
                return
            parts = command.strip().split()
            if len(parts) != 4:
                await self.send("Use STAFF ROLE <account> <role>.\r\n")
                return
            await _assign_role(self, parts[2], parts[3])
            return

        if normalized.startswith("staff audit"):
            if not _staff_mode(self) or not _has_role(self, "admin"):
                await self.send("ADMIN staff mode is required to view the audit log.\r\n")
                return
            parts = normalized.split()
            count = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 15
            await _audit_view(self, count)
            return

        if normalized == "gm" or normalized == "gm dashboard":
            if not _staff_mode(self) or not _has_role(self, "helper"):
                await self.send("Enable staff mode first with STAFF ON.\r\n")
                return
            await _dashboard(self)
            return

        if normalized.startswith("gm "):
            if not _staff_mode(self) or not _has_role(self, "helper"):
                await self.send("Enable staff mode first with STAFF ON.\r\n")
                return
            raw = command.strip()[3:].strip()
            lower = " ".join(raw.lower().split())

            if lower.startswith("inventory "):
                await _inventory(self, raw.split(maxsplit=1)[1])
                return
            if lower.startswith("goto "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _goto(self, raw.split(maxsplit=1)[1])
                return
            if lower.startswith("observe "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _goto(self, raw.split(maxsplit=1)[1], observe=True)
                return
            if lower in {"visible", "invisible"}:
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                self._staff_invisible = lower == "invisible"
                _audit(self, "visibility", details=lower)
                await self.send(f"Staff presence set to {lower.upper()}.\r\n")
                return
            if lower.startswith("bring "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                name = raw.split(maxsplit=1)[1]
                target = _find_online_player(name)
                if target is None:
                    await self.send("That character is not online.\r\n")
                    return
                await _queue_confirmation(self, "bring", {"target": target.character.name}, f"bring {target.character.name} to your room")
                return
            if lower.startswith("reset quest "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                parts = raw.split(maxsplit=3)
                if len(parts) < 4:
                    await self.send("Use GM RESET QUEST <player> <quest>.\r\n")
                    return
                target_name, quest_query = parts[2], parts[3]
                character = self.database.get_character_by_name(target_name)
                if character is None:
                    await self.send("No character by that name was found.\r\n")
                    return
                row, definition = _find_quest(self, character.id, quest_query)
                if row is None or definition is None:
                    await self.send("That character does not have a matching registered quest.\r\n")
                    return
                await _queue_confirmation(
                    self,
                    "reset_quest",
                    {"target": character.name, "quest": definition.key},
                    f"reset {character.name}'s '{definition.name}' journal to its first step; world flags and rewards will not be rewound",
                )
                return
            if lower.startswith("restore npc "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                query = raw[len("restore npc "):].strip()
                state = _find_mobile_npc(self, query)
                if state is None:
                    await self.send("No matching mobile NPC was found.\r\n")
                    return
                await _queue_confirmation(
                    self,
                    "restore_npc",
                    {"npc": state.definition.key},
                    f"restore {state.definition.name} to {_room_label(state.definition.spawn_room_key)}",
                )
                return
            if lower.startswith("echo "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _echo(self, raw.split(maxsplit=1)[1])
                return
            if lower.startswith("possess "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _possess(self, raw.split(maxsplit=1)[1])
                return
            if lower.startswith("speak "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _puppet_speak(self, raw.split(maxsplit=1)[1])
                return
            if lower.startswith("emote "):
                if not _has_role(self, "gm"):
                    await self.send("GM role or higher is required.\r\n")
                    return
                await _puppet_speak(self, raw.split(maxsplit=1)[1], emote=True)
                return
            if lower == "release":
                npc = getattr(self, "_staff_possessed_npc", None)
                self._staff_possessed_npc = None
                self._staff_possessed_npc_key = None
                self._staff_possess_until = 0.0
                _audit(self, "release_possession", npc or "")
                await self.send("NPC possession released.\r\n")
                return

            await _inspect_player(self, raw)
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.close = close
    player_session_class.playing_prompt = playing_prompt
    player_session_class._staff_control_runtime_installed = True
