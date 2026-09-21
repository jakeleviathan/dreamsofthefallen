from __future__ import annotations

import mud.command_guide as command_guide
from mud.command_guide import CommandEntry


_EXTRA_COMMANDS: tuple[CommandEntry, ...] = (
    CommandEntry(
        "basics",
        "MAP / MAP HERE / MAP 1..4",
        "Show only rooms this character has personally discovered; choose a local radius from 1 through 4.",
        ("mapper", "discovery", "radius"),
    ),
    CommandEntry(
        "basics",
        "LOOK AT / LOOK / EXAMINE / INSPECT <actor>",
        "Inspect a visible NPC or enemy; the same LOOK AT and INSPECT phrasing also delegates safely to authored world features.",
        ("actor", "npc", "enemy", "inspection"),
    ),
    CommandEntry(
        "combat",
        "CONSIDER / CON <target>",
        "Judge a visible target's relative danger without starting combat or revealing hidden numeric stats.",
        ("consider", "con", "enemy", "danger", "difficulty", "threat"),
    ),
    CommandEntry(
        "character",
        "MOVEMENT / MOVE POINTS / MOVEMENT POINTS / FATIGUE / ENDURANCE",
        "Show current movement points, fatigue band, and recovery guidance.",
        ("move", "stamina", "recovery"),
    ),
    CommandEntry(
        "character",
        "REST / SIT / SIT DOWN",
        "Rest to recover movement and mana faster; authored local SIT actions take priority where a room defines one.",
        ("fatigue", "mana", "recover"),
    ),
    CommandEntry(
        "character",
        "STAND / STAND UP / RISE",
        "Stop resting and return to your feet; authored local aliases take priority where defined.",
        ("rest", "rise"),
    ),
    CommandEntry(
        "world",
        "DRUGS / PERCEPTION / ALTERED / ALTERED STATE",
        "Show the current fantasy altered-perception state, if any, without changing combat statistics.",
        ("moonwake", "choircap", "emberleaf", "hushglass"),
    ),
)


def _extend_catalog() -> None:
    existing = {entry.syntax.casefold() for entry in command_guide.COMMANDS}
    additions = tuple(entry for entry in _EXTRA_COMMANDS if entry.syntax.casefold() not in existing)
    if additions:
        command_guide.COMMANDS = command_guide.COMMANDS + additions
    command_guide.CATEGORIES = tuple(dict.fromkeys(entry.category for entry in command_guide.COMMANDS))


def _catalog_rows(*syntaxes: str) -> tuple[CommandEntry, ...]:
    wanted = {syntax.casefold() for syntax in syntaxes}
    return tuple(entry for entry in command_guide.COMMANDS if entry.syntax.casefold() in wanted)


async def _show_quick_help(session) -> None:
    """Render beginner HELP entirely from entries in the canonical catalog."""

    rows = _catalog_rows(
        "LOOK / L",
        "EXITS",
        "N / E / S / W / U / D",
        "MAP / MAP HERE / MAP 1..4",
        "LOOK AT / LOOK / EXAMINE / INSPECT <actor>",
        "CONSIDER / CON <target>",
        "QUESTS",
        "INVENTORY / INV / I",
        "ITEM / INSPECT ITEM <item>",
        "REST / SIT / SIT DOWN",
        "SAY <message>",
        "HELP HERE / SUGGEST",
    )
    await session.send("\r\n--- Help ---\r\n")
    await session.send("The same command catalog powers HELP and COMMANDS. Start with these:\r\n")
    for entry in rows:
        await session.send(f"{entry.syntax} - {entry.description}\r\n")
    await session.send(
        "COMMANDS shows categories. COMMANDS ALL or HELP ALL prints the full catalog; "
        "HELP <word> or COMMAND SEARCH <word> searches it.\r\n"
    )


async def _show_all(session) -> None:
    for category in command_guide.CATEGORIES:
        await command_guide._show_category(session, category)


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


def install_canonical_command_help(player_session_class) -> None:
    """Make one catalog authoritative for HELP, COMMANDS, aliases, and search."""

    if getattr(player_session_class, "_canonical_command_help_installed", False):
        return
    _extend_catalog()
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

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        if normalized in {"help", "?"}:
            await _show_quick_help(self)
            return
        if normalized in {"commands", "command guide", "help commands"}:
            await command_guide._show_categories(self)
            return
        if normalized in {"commands all", "help all"}:
            await _show_all(self)
            return

        # HELP <category/word> and every COMMANDS search/category form delegate to
        # command_guide, which reads this same extended COMMANDS tuple.
        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._canonical_command_help_installed = True


# Keep direct imports/tests consistent with production even before installer use.
_extend_catalog()
