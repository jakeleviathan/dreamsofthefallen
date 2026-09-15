from __future__ import annotations

import time

from mud.alpha_ux import _observe_transition, _state_snapshot, ensure_alpha_ux_schema


def _latest_command_event_id(session) -> int:
    """Return the newest command event for this character, or zero.

    The original alpha telemetry wrapper lives inside several later production
    command layers. A final wrapper can therefore tell whether an inner handler
    already counted a command without changing those handlers or double-counting
    commands that still reach the alpha layer.
    """

    character = getattr(session, "character", None)
    character_id = getattr(character, "id", None)
    if character_id is None:
        return 0
    ensure_alpha_ux_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            """
            SELECT COALESCE(MAX(id), 0)
            FROM alpha_ux_events
            WHERE character_id = ? AND event_key = 'command'
            """,
            (int(character_id),),
        ).fetchone()
    return int(row[0] if row else 0)


async def _delegate(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    prior_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    session.prompt = replay_prompt
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = prior_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_final_command_telemetry(player_session_class) -> None:
    """Count commands after the complete production stack has been assembled.

    Alpha UX telemetry was originally installed before MAP, movement/rest,
    inventory/actor inspection, altered perception, and the Goblin gathering
    bridge. Those outer handlers could return before the alpha wrapper ever saw
    the command. This final edge wrapper observes the full stack and backfills
    telemetry only when the inner alpha layer did not already record the command.
    """

    if getattr(player_session_class, "_final_command_telemetry_installed", False):
        return

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        before_event_id = _latest_command_event_id(self)
        before = _state_snapshot(self)
        started = time.monotonic()
        await _delegate(self, previous_prompt, command)
        latency_ms = int((time.monotonic() - started) * 1000)

        # If the command reached alpha_ux, it has already been recorded with its
        # transition milestones. Only outer short-circuit handlers need backfill.
        if _latest_command_event_id(self) != before_event_id:
            return

        after = _state_snapshot(self)
        _observe_transition(self, command, before, after, latency_ms)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._final_command_telemetry_installed = True
