from __future__ import annotations

import json
import time
from collections import Counter


ALPHA_UX_VERSION = "1.0.0"

# Player communication payloads are never stored in command telemetry.
_PRIVATE_VERBS = {"say", "chat", "ooc", "tell", "reply", "tavern", "pin"}


def ensure_alpha_ux_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS alpha_ux_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                character_id INTEGER,
                event_key TEXT NOT NULL,
                room_key TEXT NOT NULL DEFAULT '',
                command_verb TEXT NOT NULL DEFAULT '',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                details TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alpha_ux_events_created
            ON alpha_ux_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_alpha_ux_events_character
            ON alpha_ux_events(character_id, event_key);

            CREATE TABLE IF NOT EXISTS alpha_ux_milestones (
                character_id INTEGER NOT NULL,
                milestone_key TEXT NOT NULL,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                room_key TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (character_id, milestone_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS alpha_player_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                character_id INTEGER,
                report_type TEXT NOT NULL,
                room_key TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );
            """
        )


def _character_id(session) -> int | None:
    character = getattr(session, "character", None)
    return None if character is None else int(character.id)


def _room_key(session) -> str:
    character = getattr(session, "character", None)
    return "" if character is None else str(character.current_room or "")


def _record_event(session, event_key: str, *, verb: str = "", latency_ms: int = 0, details: dict | None = None) -> None:
    character_id = _character_id(session)
    if character_id is None:
        return
    ensure_alpha_ux_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO alpha_ux_events (character_id, event_key, room_key, command_verb, latency_ms, details) VALUES (?, ?, ?, ?, ?, ?)",
            (character_id, event_key, _room_key(session), verb, max(0, int(latency_ms)), json.dumps(details or {}, sort_keys=True)),
        )


def _milestone(session, key: str) -> bool:
    character_id = _character_id(session)
    if character_id is None:
        return False
    ensure_alpha_ux_schema(session.database)
    with session.database.connect() as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO alpha_ux_milestones (character_id, milestone_key, room_key) VALUES (?, ?, ?)",
            (character_id, key, _room_key(session)),
        )
        created = cur.rowcount > 0
    if created:
        _record_event(session, "milestone", details={"milestone": key})
    return created


def milestone_keys(database, character_id: int) -> frozenset[str]:
    ensure_alpha_ux_schema(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT milestone_key FROM alpha_ux_milestones WHERE character_id = ? ORDER BY first_seen_at",
            (character_id,),
        ).fetchall()
    return frozenset(str(row[0]) for row in rows)


def _inventory_snapshot(session) -> Counter:
    character_id = _character_id(session)
    if character_id is None:
        return Counter()
    return Counter({str(row["item_key"]): int(row["quantity"]) for row in session.database.list_items(character_id)})


def _quest_snapshot(session) -> tuple[tuple[str, str, str], ...]:
    character_id = _character_id(session)
    if character_id is None:
        return ()
    rows = session.database.list_quests(character_id)
    return tuple(sorted((str(row["quest_key"]), str(row["status"]), str(row.get("current_step") or "")) for row in rows))


def _safe_verb(command: str) -> str:
    parts = command.strip().lower().split()
    if not parts:
        return ""
    # Store only the command family. This is especially important for SAY/TELL/etc.
    return parts[0]


def _state_snapshot(session) -> dict:
    character = getattr(session, "character", None)
    return {
        "room": _room_key(session),
        "inventory": _inventory_snapshot(session),
        "quests": _quest_snapshot(session),
        "enemy": getattr(session, "active_enemy", None) is not None,
        "level": int(getattr(character, "level", 0) or 0),
    }


def _observe_transition(session, command: str, before: dict, after: dict, latency_ms: int) -> None:
    normalized = " ".join(command.strip().lower().split())
    verb = _safe_verb(command)
    _record_event(session, "command", verb=verb, latency_ms=latency_ms)

    if before["room"] and after["room"] and before["room"] != after["room"]:
        _milestone(session, "first_movement")
        _record_event(session, "room_change", verb=verb, details={"from": before["room"], "to": after["room"]})

    if after["enemy"] and not before["enemy"]:
        _milestone(session, "first_combat")

    gained = []
    for key, quantity in after["inventory"].items():
        delta = quantity - before["inventory"].get(key, 0)
        if delta > 0:
            gained.append((key, delta))
    if gained:
        _milestone(session, "first_loot")
        _record_event(session, "inventory_gain", verb=verb, details={"items": gained[:8]})

    if before["quests"] != after["quests"]:
        _milestone(session, "first_quest_progress")
        _record_event(session, "quest_state_change", verb=verb)

    if after["level"] > before["level"]:
        _milestone(session, "first_level_up")
        _record_event(session, "level_up", details={"from": before["level"], "to": after["level"]})

    if verb in {"equip", "wear", "wield"}:
        _milestone(session, "first_equip_attempt")
    if verb in {"buy", "boutique", "market", "browse"}:
        _milestone(session, "first_merchant_interaction")
    if verb in {"craft", "mine", "gather", "harvest", "herbalism"}:
        _milestone(session, "first_economy_action")
    if verb in {"say", "chat", "tell", "party", "trade", "give", "wave", "nod"}:
        _milestone(session, "first_social_action")
    if normalized in {"help here", "suggest", "suggestions"}:
        _milestone(session, "used_context_help")


def alpha_ux_summary(database, hours: int = 24) -> dict[str, int | float]:
    ensure_alpha_ux_schema(database)
    hours = max(1, min(24 * 30, int(hours)))
    with database.connect() as db:
        events = db.execute(
            "SELECT event_key, COUNT(*) AS total, AVG(latency_ms) AS avg_latency FROM alpha_ux_events WHERE created_at >= datetime('now', ?) GROUP BY event_key",
            (f"-{hours} hours",),
        ).fetchall()
        reports = db.execute(
            "SELECT report_type, COUNT(*) AS total FROM alpha_player_reports WHERE created_at >= datetime('now', ?) GROUP BY report_type",
            (f"-{hours} hours",),
        ).fetchall()
        stalled = db.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT character_id
                FROM alpha_ux_events
                WHERE created_at >= datetime('now', ?) AND event_key='command'
                GROUP BY character_id
                HAVING COUNT(*) >= 12
                   AND character_id NOT IN (
                       SELECT character_id FROM alpha_ux_milestones WHERE milestone_key='first_movement'
                   )
            )
            """,
            (f"-{hours} hours",),
        ).fetchone()
    result: dict[str, int | float] = {"hours": hours, "stalled_without_movement": int(stalled[0] if stalled else 0)}
    for row in events:
        result[f"events_{row['event_key']}"] = int(row["total"])
        if row["event_key"] == "command":
            result["average_command_latency_ms"] = round(float(row["avg_latency"] or 0.0), 1)
    for row in reports:
        result[f"reports_{row['report_type']}"] = int(row["total"])
    return result


async def _show_guide(session) -> None:
    character = session.character
    known = milestone_keys(session.database, character.id)
    await session.send("\r\n--- New Player Guide ---\r\n")
    await session.send("You do not need to learn every command. Read the room, try obvious verbs, and use HELP HERE whenever you are unsure.\r\n")

    if "first_movement" not in known:
        await session.send("Right now: LOOK, EXITS, then move with a direction such as N, E, S, or W.\r\n")
    elif "first_quest_progress" not in known:
        await session.send("Next: QUESTS shows your current objective. EXAMINE named things and TALK to named people when the room points at them.\r\n")
    elif "first_combat" not in known:
        await session.send("Soon: when danger appears, CLASS shows your abilities. ATTACK <enemy> begins combat and FLEE can break it.\r\n")
    elif "first_loot" not in known:
        await session.send("After a fight: INVENTORY shows what changed; ITEM <name> explains an unfamiliar object.\r\n")
    elif "first_equip_attempt" not in known:
        await session.send("Gear: EQUIPMENT shows slots; COMPARE <item> and EQUIP <item> help you make a simple choice.\r\n")
    elif "first_merchant_interaction" not in known:
        await session.send("Trade: use HELP HERE in a market or shop. BUY, BOUTIQUE, MARKET, and NEEDS are surfaced only where relevant.\r\n")
    else:
        await session.send("You have the basics. From here, HELP HERE is usually better than a tutorial checklist; Astralis is meant to be explored rather than completed from a menu.\r\n")
    await session.send("If something feels broken or confusing: BUG <text>, FEEDBACK <text>, or STUCK <text>.\r\n")


async def _save_report(session, report_type: str, text: str) -> None:
    text = " ".join(text.strip().split())
    if not text:
        await session.send(f"Usage: {report_type.upper()} <what happened>\r\n")
        return
    text = text[:1000]
    ensure_alpha_ux_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO alpha_player_reports (character_id, report_type, room_key, text) VALUES (?, ?, ?, ?)",
            (_character_id(session), report_type, _room_key(session), text),
        )
    _record_event(session, "player_report", details={"type": report_type})
    await session.send("Saved. Thank you — the report includes your current room automatically.\r\n")
    if report_type == "stuck":
        await session.send("Try HELP HERE for contextual actions, QUESTS for your current objective, or JOURNEY for the spoiler-light route forward.\r\n")


async def _delegate(session, previous_prompt, command: str) -> None:
    had = "prompt" in session.__dict__
    old = session.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had:
            session.prompt = old
        else:
            session.__dict__.pop("prompt", None)


def install_alpha_ux_runtime(player_session_class) -> None:
    """Playable-alpha guidance plus privacy-conscious behavioral telemetry."""
    if getattr(player_session_class, "_alpha_ux_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is None:
            return
        ensure_alpha_ux_schema(self.database)
        _record_event(self, "character_enter")
        known = milestone_keys(self.database, self.character.id)
        if "ux_guide_seen" not in known:
            _milestone(self, "ux_guide_seen")
            await self.send("New here? GUIDE gives a short next-step hint. HELP HERE tells you what makes sense in the room you are standing in.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return

        prompt_text = "\r\n" + (self.current_prompt_text() if hasattr(self, "current_prompt_text") else "> ")
        command = await self.prompt(prompt_text)
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        if normalized in {"guide", "new player", "new player guide", "next", "what next"}:
            _milestone(self, "used_guide")
            await _show_guide(self)
            return
        for report_type in ("bug", "feedback", "stuck"):
            prefix = report_type + " "
            if normalized == report_type:
                await _save_report(self, report_type, "")
                return
            if normalized.startswith(prefix):
                await _save_report(self, report_type, stripped[len(prefix):])
                return

        before = _state_snapshot(self)
        started = time.monotonic()
        await _delegate(self, previous_prompt, command)
        latency_ms = int((time.monotonic() - started) * 1000)
        after = _state_snapshot(self)
        _observe_transition(self, command, before, after, latency_ms)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._alpha_ux_runtime_installed = True
