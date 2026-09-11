from __future__ import annotations

from weakref import WeakSet

from mud.player_preferences import hint_level


INTRO_FLAG = "mud_basics_introduced"
STUCK_HINT_FLAG = "mud_basics_stuck_hint_shown"
CONFIDENT_FLAG = "mud_basics_confident"
LOOK_FLAG = "mud_basics_looked"
INTERACT_FLAG = "mud_basics_interacted"
SPEAK_FLAG = "mud_basics_spoke"
MOVE_FLAG = "mud_basics_moved"

_BASIC_PROGRESS_FLAGS = (LOOK_FLAG, INTERACT_FLAG, SPEAK_FLAG, MOVE_FLAG)
_ACTIVE_SESSIONS: WeakSet = WeakSet()


def _normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_flags"):
        return set()
    try:
        return set(database.list_flags(character.id))
    except Exception:
        return set()


def _grant(session, flag: str) -> None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "grant_flag"):
        return
    database.grant_flag(character.id, flag)


def _record_basic_progress(session, flag: str) -> None:
    existing = _flags(session)
    if flag not in existing:
        _grant(session, flag)
        existing.add(flag)
    if CONFIDENT_FLAG not in existing:
        completed = sum(1 for key in _BASIC_PROGRESS_FLAGS if key in existing)
        if completed >= 2:
            _grant(session, CONFIDENT_FLAG)


async def _send_basics(session) -> None:
    await session.send(
        "\r\n--- The Tiny Version ---\r\n"
        "Dreams of the Fallen is a text world: type short commands to act.\r\n"
        "LOOK - see the room again.\r\n"
        "EXITS - see where you can go. Type a direction such as NORTH to move.\r\n"
        "TALK <name> or EXAMINE <thing> - interact with people and the world.\r\n"
        "SAY <message> - speak aloud to other players in the room.\r\n"
        "HELP - a short command overview. COMMANDS - the full list.\r\n"
        "SETTINGS - presentation, accessibility, and automatic hint preferences.\r\n"
        "You do not need to memorize any of this. Your opening will teach things as they become useful.\r\n"
    )


def _clean_speech(message: str) -> str:
    cleaned = " ".join(message.replace("\r", " ").replace("\n", " ").split())
    return cleaned[:280]


async def _say(session, message: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    speech = _clean_speech(message)
    if not speech:
        await session.send("Say what? Try SAY HELLO.\r\n")
        return

    await session.send(f'You say, "{speech}"\r\n')
    current_room = getattr(character, "current_room", None)
    for other in tuple(_ACTIVE_SESSIONS):
        if other is session:
            continue
        other_character = getattr(other, "character", None)
        if other_character is None or getattr(other_character, "current_room", None) != current_room:
            continue
        allows = getattr(other, "social_allows_message_from", None)
        if callable(allows) and not allows(character.name):
            continue
        try:
            await other.send(f'{character.name} says, "{speech}"\r\n')
        except (ConnectionError, RuntimeError):
            continue
    _record_basic_progress(session, SPEAK_FLAG)


async def _delegate_prompt_with_capture(self, previous_playing_prompt, command: str) -> list[str]:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")
    had_instance_send = "send" in self.__dict__
    prior_send = self.__dict__.get("send")
    real_send = self.send
    captured: list[str] = []

    async def replay_prompt(_text: str) -> str:
        return command

    async def capture_send(text: str) -> None:
        captured.append(text)
        await real_send(text)

    self.prompt = replay_prompt
    self.send = capture_send
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)
        if had_instance_send:
            self.send = prior_send
        else:
            self.__dict__.pop("send", None)
    return captured


def _is_beginner_character(session) -> bool:
    character = getattr(session, "character", None)
    return character is not None and int(getattr(character, "level", 1) or 1) <= 1


def _command_progress_flag(normalized: str) -> str | None:
    if normalized in {"look", "l", "exits", "exit"}:
        return LOOK_FLAG
    if normalized.startswith("talk ") or normalized.startswith("examine "):
        return INTERACT_FLAG
    return None


def install_new_player_guidance_runtime(player_session_class) -> None:
    """Teach MUD basics quietly through play instead of a mandatory tutorial.

    The first room gets one concise explanation of typed commands when automatic
    hints are enabled. SAY and BASICS are real commands. GENTLE waits for two
    unknown commands before a single rescue hint; FULL gives that rescue after
    the first miss; OFF never injects automatic help.
    """
    if getattr(player_session_class, "_new_player_guidance_runtime_installed", False):
        return

    if hasattr(player_session_class, "enter_character"):
        previous_enter_character = player_session_class.enter_character

        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if getattr(self, "character", None) is None:
                return
            _ACTIVE_SESSIONS.add(self)
            if not _is_beginner_character(self) or hint_level(self) == "off":
                return
            flags = _flags(self)
            if INTRO_FLAG in flags:
                return
            await self.send(
                "\r\nDreams of the Fallen is a text world: you play by typing short commands.\r\n"
                "Try LOOK to take in the room again. Try SAY HELLO to speak aloud.\r\n"
                "To move, type one of the exits you see, such as NORTH. Type BASICS any time for a tiny refresher.\r\n"
            )
            if hint_level(self) == "full":
                await self.send(
                    "FULL hints are enabled, so the game will be a little quicker to point out useful commands when you appear stuck. SETTINGS can change this any time.\r\n"
                )
            _grant(self, INTRO_FLAG)

        player_session_class.enter_character = enter_character

    previous_playing_prompt = player_session_class.playing_prompt

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

        normalized = _normalize(command)
        if normalized in {
            "basics",
            "basic",
            "new player",
            "new player help",
            "how do i play",
            "how do i move",
            "controls",
        }:
            await _send_basics(self)
            return

        if normalized == "say":
            await _say(self, "")
            return
        if normalized.startswith("say "):
            await _say(self, command.strip()[4:])
            return

        before_room = getattr(self.character, "current_room", None)
        captured = await _delegate_prompt_with_capture(self, previous_playing_prompt, command)
        after_room = getattr(getattr(self, "character", None), "current_room", None)

        if before_room and after_room and before_room != after_room:
            _record_basic_progress(self, MOVE_FLAG)
        progress_flag = _command_progress_flag(normalized)
        if progress_flag is not None and not any("Unknown command." in text for text in captured):
            _record_basic_progress(self, progress_flag)

        if not _is_beginner_character(self):
            return
        level = hint_level(self)
        if level == "off":
            return
        flags = _flags(self)
        if CONFIDENT_FLAG in flags or STUCK_HINT_FLAG in flags:
            return
        if not any("Unknown command." in text for text in captured):
            return

        misses = int(getattr(self, "_new_player_unknown_commands", 0)) + 1
        self._new_player_unknown_commands = misses
        threshold = 1 if level == "full" else 2
        if misses < threshold:
            return

        await self.send(
            "\r\nIf you're not sure what the game expects, try LOOK, EXITS, TALK <name>, or SAY HELLO. "
            "Type BASICS for the tiny version, or HELP for a broader overview.\r\n"
        )
        _grant(self, STUCK_HINT_FLAG)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._new_player_guidance_runtime_installed = True
