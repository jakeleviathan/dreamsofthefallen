from __future__ import annotations

import inspect

import mud.command_guide as command_guide
import mud.sporekin_depth as sporekin_depth
import mud.waymeet_frontier as waymeet_frontier
from mud.movement_system import is_restful_place


_REST_START_ALIASES = frozenset({"sit", "sit down"})
_REST_STOP_ALIASES = frozenset({"stand up", "rise"})


def _normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def _room_key(session) -> str:
    character = getattr(session, "character", None)
    return str(getattr(character, "current_room", "") or "")


def _sporekin_owns_guide(session) -> bool:
    character = getattr(session, "character", None)
    return bool(
        character is not None
        and getattr(character, "race", None) == "sporekin"
        and _room_key(session) == sporekin_depth.SPOREKIN_MEMORY_PATH_ROOM_KEY
    )


def _waymeet_owns_frontier(session) -> bool:
    return bool(waymeet_frontier._in_waymeet(session))


def _closure_values(function) -> dict[str, object]:
    closure = getattr(function, "__closure__", None)
    names = getattr(getattr(function, "__code__", None), "co_freevars", ())
    if not closure:
        return {}
    values: dict[str, object] = {}
    for name, cell in zip(names, closure):
        try:
            values[name] = cell.cell_contents
        except ValueError:
            continue
    return values


def _find_pre_movement_prompt(function, seen: set[int] | None = None):
    """Find the command stack immediately beneath the movement wrapper.

    Movement was intentionally installed near the outside of the production stack.
    Its SIT/STAND convenience aliases therefore shadow older authored commands.
    Rather than knowing every old room in advance, aliases get one pass through the
    pre-movement stack. Canonical REST and STAND remain owned by movement globally.
    """

    if function is None:
        return None
    seen = seen or set()
    marker = id(function)
    if marker in seen:
        return None
    seen.add(marker)

    values = _closure_values(function)
    if (
        getattr(function, "__module__", "") == "mud.movement_system"
        and getattr(function, "__name__", "") == "playing_prompt"
    ):
        candidate = values.get("original_playing_prompt")
        return candidate if callable(candidate) else None

    for value in values.values():
        if not callable(value) or not inspect.iscoroutinefunction(value):
            continue
        if getattr(value, "__name__", "") != "playing_prompt":
            continue
        found = _find_pre_movement_prompt(value, seen)
        if found is not None:
            return found
    return None


async def _try_pre_movement_owner(session, previous_prompt, command: str) -> bool:
    """Run an alias through authored/global handlers below movement first.

    Output is buffered so the base Unknown command response is not shown before
    the movement fallback. Any real handler keeps its side effects and its output.
    """

    if previous_prompt is None:
        return False

    had_prompt = "prompt" in session.__dict__
    prior_prompt = session.__dict__.get("prompt")
    had_send = "send" in session.__dict__
    prior_send = session.__dict__.get("send")
    real_send = session.send
    captured: list[str] = []

    async def replay_prompt(_text: str):
        return command

    async def capture_send(text: str) -> None:
        captured.append(text)

    session.prompt = replay_prompt
    session.send = capture_send
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = prior_prompt
        else:
            session.__dict__.pop("prompt", None)
        if had_send:
            session.send = prior_send
        else:
            session.__dict__.pop("send", None)

    unknown = any("Unknown command." in text for text in captured)
    if unknown:
        return False
    for text in captured:
        await real_send(text)
    return True


async def _movement_rest_fallback(session, *, resting: bool) -> None:
    from mud.room_runtime import WORLD

    if resting:
        if getattr(session, "active_enemy", None) is not None:
            await session.send("You cannot settle down to rest while you are fighting.\r\n")
            return
        session._movement_resting = True
        place_text = (
            " This is a good place to recover."
            if is_restful_place(WORLD, _room_key(session))
            else ""
        )
        await session.send(
            "You settle down and rest. Movement will recover much faster."
            + place_text
            + "\r\n"
        )
    else:
        if bool(getattr(session, "_movement_resting", False)):
            session._movement_resting = False
            await session.send("You get back to your feet.\r\n")
        else:
            await session.send("You are already on your feet.\r\n")

    send_state = getattr(session, "send_client_state", None)
    if callable(send_state):
        await send_state()


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


def install_command_collision_policy(player_session_class) -> None:
    """Give contextual authored commands deterministic ownership at the edge."""

    if getattr(player_session_class, "_command_collision_policy_installed", False):
        return

    previous_prompt = player_session_class.playing_prompt
    pre_movement_prompt = _find_pre_movement_prompt(previous_prompt)

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

        normalized = _normalize(command)

        # GUIDE is a global command-discovery alias except at the one Sporekin
        # mentor location where GUIDE is authored culture content.
        if normalized == "guide":
            if _sporekin_owns_guide(self):
                await sporekin_depth._show_lines(
                    self,
                    "The Discipline of Guidance",
                    sporekin_depth.SPOREKIN_GUIDANCE_LINES,
                )
            else:
                await command_guide._show_categories(self)
            return

        # Waymeet used FRONTIER first. The later 12-20 frontier runtime remains the
        # global fallback, but inside Waymeet the local meaning must win.
        if normalized == "frontier" and _waymeet_owns_frontier(self):
            await self.send(
                "Waymeet is the first shared level 2-5 region. TALK MARSHAL for the local story, "
                "TALK WARDEN or TALK FOREMAN for repeatable contracts, BROWSE in Lantern Market "
                "for merchants, RESOURCES for gathering, and follow the damaged road toward "
                "Gloam Mouth for the first dungeon hint.\r\n"
            )
            return

        # SIT/SIT DOWN and STAND UP/RISE are conveniences, not canonical ownership.
        # Older authored handlers get first refusal. If none recognizes the alias,
        # preserve the movement system's familiar global fallback behavior.
        if normalized in _REST_START_ALIASES | _REST_STOP_ALIASES:
            if await _try_pre_movement_owner(self, pre_movement_prompt, command):
                return
            await _movement_rest_fallback(
                self,
                resting=normalized in _REST_START_ALIASES,
            )
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._command_collision_policy_installed = True
    player_session_class._pre_movement_prompt_for_aliases = pre_movement_prompt
