from __future__ import annotations

from mud.mechanics import class_abilities_for_level
from mud.quests import QUESTS_BY_KEY
from mud.room_engine import PlayerRoomContext
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


EARLY_GAME_MAX_LEVEL = 10
GOAL_ALIASES = frozenset({"goal", "goals", "objective", "objectives", "what now", "what next"})
DIRECTION_COMMANDS = frozenset({"north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"})

LOOK_FLAG = "early_polish_looked"
MOVE_FLAG = "early_polish_moved"
FIGHT_FLAG = "early_polish_fought"
ABILITY_FLAG = "early_polish_used_ability"
EXIT_RESCUE_FLAG = "early_polish_exit_rescue_seen"

RACE_VERB_FLAVOR: dict[str, str] = {
    "human": "LOOK at the street, question people, and follow the gate roads; civic life is part of the tutorial.",
    "forest_elf": "Read the forest itself: LOOK, LISTEN, EXAMINE, and then follow the path the signs justify.",
    "moon_elf": "Compare viewpoints before acting: LOOK, EXAMINE, TALK, and move only when the route makes sense.",
    "dwarf": "Treat the city like a worksite: LOOK, EXAMINE gauges or machinery, TALK to the responsible worker, then follow posted routes.",
    "goblin": "Treat everything as potentially useful: LOOK, EXAMINE, TALK, and follow the marked salvage lanes instead of guessing.",
    "troll": "Read the land before forcing it: LOOK, EXAMINE, LISTEN, then move by the safe trail you have actually found.",
    "undead": "Start with evidence: LOOK, LISTEN, EXAMINE, TALK, and decide what deserves obedience before you move on.",
    "sporekin": "Notice the shared signs without surrendering judgment: LOOK, LISTEN, EXAMINE, then choose the path yourself.",
}


def _normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def _rows(value) -> list[dict]:
    rows: list[dict] = []
    for row in value or ():
        if isinstance(row, dict):
            rows.append(row)
            continue
        try:
            rows.append(dict(row))
        except (TypeError, ValueError):
            continue
    return rows


def _character_flags(session) -> set[str]:
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


def _active_objective(session) -> tuple[str, str] | None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_quests"):
        return None
    for row in _rows(database.list_quests(character.id)):
        if row.get("status") != "active":
            continue
        definition = QUESTS_BY_KEY.get(str(row.get("quest_key") or ""))
        if definition is None:
            continue
        objective = definition.objective_for_step(row.get("current_step")) or "Continue the current quest."
        return definition.name, objective
    return None


def _goal_text(session) -> str:
    active = _active_objective(session)
    if active is not None:
        name, objective = active
        return f"\r\nCurrent goal - {name}: {objective}\r\n"

    character = getattr(session, "character", None)
    if character is None:
        return "\r\nNo character is active.\r\n"
    if int(getattr(character, "level", 1) or 1) <= EARLY_GAME_MAX_LEVEL:
        loop = STARTER_RACE_LOOPS_BY_RACE.get(getattr(character, "race", None))
        if loop is not None:
            return f"\r\nCurrent goal - {loop.hook_name}: keep exploring your opening and follow the people, signs, and routes it introduces.\r\n"
    return "\r\nYou have no active quest objective right now. LOOK and EXITS will re-orient you; TALK to local people when you want another lead.\r\n"


def _early_context(session) -> PlayerRoomContext | None:
    character = getattr(session, "character", None)
    if character is None or int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
        return None
    return PlayerRoomContext(
        character_id=character.id,
        race_key=getattr(character, "race", "") or "",
        class_key=getattr(character, "character_class", "") or "",
        level=int(getattr(character, "level", 1) or 1),
        character_flags=frozenset(_character_flags(session)),
    )


def _visible_exit_hint(session, world) -> str | None:
    character = getattr(session, "character", None)
    context = _early_context(session)
    if character is None or context is None:
        return None
    view = world.build_view(getattr(character, "current_room", "") or "", context)
    if view is None or not view.exits:
        return None
    exits = ", ".join(exit_def.direction.upper() for exit_def in view.exits)
    return f"Available exits here: {exits}. Type EXITS any time to see them again."


def _successful(captured: list[str]) -> bool:
    text = "".join(captured).lower()
    return not any(
        marker in text
        for marker in (
            "unknown command",
            "you cannot go that way",
            "there are no authored exits",
            "that way is locked",
            "that way is closed",
        )
    )


def install_early_game_polish_runtime(player_session_class, world) -> None:
    """Keep levels 1-10 easy to read without flattening the game's depth."""
    if getattr(player_session_class, "_early_game_polish_runtime_installed", False):
        return

    if hasattr(player_session_class, "enter_character"):
        previous_enter = player_session_class.enter_character

        async def enter_character(self) -> None:
            await previous_enter(self)
            character = getattr(self, "character", None)
            if character is None or int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
                return
            if getattr(self, "_early_polish_flavor_shown", False):
                return
            race_key = getattr(character, "race", "") or ""
            flavor = RACE_VERB_FLAVOR.get(race_key)
            if flavor:
                await self.send(
                    f"\r\n{flavor}\r\n"
                    "Type GOALS whenever you forget what you were doing; it gives one current objective without spoiling the road ahead.\r\n"
                )
            self._early_polish_flavor_shown = True

        player_session_class.enter_character = enter_character

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            return
        normalized = _normalize(command)
        if normalized in GOAL_ALIASES:
            await self.send(_goal_text(self))
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")
        had_send = "send" in self.__dict__
        old_send = self.__dict__.get("send")
        real_send = self.send
        captured: list[str] = []

        async def replay_prompt(_text: str) -> str:
            return command

        async def capture_send(text: str) -> None:
            captured.append(text)
            await real_send(text)

        before_room = getattr(character, "current_room", None)
        self.prompt = replay_prompt
        self.send = capture_send
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)
            if had_send:
                self.send = old_send
            else:
                self.__dict__.pop("send", None)

        if int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
            return

        after_room = getattr(character, "current_room", None)
        ok = _successful(captured)
        if ok and normalized in {"look", "l"}:
            _grant(self, LOOK_FLAG)
        if before_room and after_room and before_room != after_room:
            _grant(self, MOVE_FLAG)
        if ok and (normalized.startswith("attack ") or normalized.startswith("kill ")):
            _grant(self, FIGHT_FLAG)
        if ok and (normalized.startswith("use ") or normalized.startswith("cast ") or normalized.startswith("nurture")):
            _grant(self, ABILITY_FLAG)

        if normalized in DIRECTION_COMMANDS and not ok:
            flags = _character_flags(self)
            if EXIT_RESCUE_FLAG not in flags:
                hint = _visible_exit_hint(self, world)
                if hint:
                    await real_send(f"\r\n{hint}\r\n")
                    _grant(self, EXIT_RESCUE_FLAG)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._early_game_polish_runtime_installed = True


def validate_level_ten_playability_contract(world, race_keys: tuple[str, ...], class_keys: tuple[str, ...]) -> None:
    """Fail fast if any launch race/class combination loses its basic 1-10 path."""
    problems: list[str] = []
    for race_key in race_keys:
        loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
        if loop is None:
            problems.append(f"{race_key}: no starter loop")
            continue
        scene = world.scene(loop.starting_room_key)
        if scene is None:
            problems.append(f"{race_key}: missing live start room {loop.starting_room_key}")
            continue
        for class_key in class_keys:
            context = PlayerRoomContext(1, race_key, class_key, 1, frozenset())
            view = world.build_view(loop.starting_room_key, context)
            if view is None or not view.exits:
                problems.append(f"{race_key}/{class_key}: start has no visible route")
                continue
            if not any(world.resolve_exit(loop.starting_room_key, exit_def.direction, context).allowed for exit_def in view.exits):
                problems.append(f"{race_key}/{class_key}: no walkable start exit")
            deity_key = "zerjz" if class_key == "priest" else None
            if not class_abilities_for_level(class_key, 10, deity_key):
                problems.append(f"{race_key}/{class_key}: no class kit at level 10")
    if problems:
        raise RuntimeError("Early-game playability contract failed: " + "; ".join(problems))
