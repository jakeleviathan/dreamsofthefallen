from __future__ import annotations

from mud.character_options import RACES_BY_KEY
from mud.mechanics import class_abilities_for_level
from mud.new_player_guidance import install_new_player_guidance_runtime
from mud.quests import QUESTS_BY_KEY
from mud.world import NPCS_BY_KEY, ROOMS_BY_KEY


# Keep the command index honest: these class abilities currently have executable
# gameplay handlers. Other authored future abilities remain visible through the
# normal ABILITIES/progression systems when appropriate, but HELP ALL does not
# advertise them as working commands before their effects exist.
EXECUTABLE_CLASS_ABILITY_KEYS = frozenset(
    {
        "taunt",
        "coldfire_burst",
        "forage",
        "nurture",
        "minor_heal",
        "restoring_light",
        "guardian_ward",
        "judgment_bolt",
        "minor_life_tap",
        "raise_skeleton",
        "rot",
    }
)

RACIAL_COMMAND_SYNTAX: dict[str, str] = {
    "human": "ADAPT MIGHT|GRACE|LOVE|MIND",
    "forest_elf": "SLIPSTEP",
    "moon_elf": "RECONSIDER",
    "dwarf": "BRACE",
    "goblin": "SCROUNGE",
    "troll": "BLOODSCENT",
    "undead": "STILLNESS",
    "sporekin": "CHORUS BLOOM",
}

RACIAL_ACTIVE_NAMES: dict[str, str] = {
    "human": "Adapt",
    "forest_elf": "Slipstep",
    "moon_elf": "Reconsider",
    "dwarf": "Brace",
    "goblin": "Scrounge",
    "troll": "Bloodscent",
    "undead": "Stillness",
    "sporekin": "Chorus Bloom",
}

# These are stable culture/status commands, not one-off quest verbs. Quest verbs
# are surfaced from the character's live objective below so this file does not
# have to duplicate every authored starter sequence.
RACE_CULTURE_COMMANDS: dict[str, tuple[str, ...]] = {
    "forest_elf": ("HOME", "FOREST OPENING"),
    "moon_elf": (
        "BELIEFS",
        "RELIGION",
        "WITNESS",
        "WITNESS MAGIC",
        "SHRINE",
        "PRAYER",
        "MOON",
        "HORIZON",
        "JOURNALS",
        "ELVES",
        "CITY",
        "GOVERNMENT",
        "COUNTERVIEW",
        "SPIRE",
        "PENTHOUSE",
    ),
    "dwarf": ("OBLIGATIONS",),
    "sporekin": ("CHORUS", "SELFHOOD", "GUIDANCE"),
}


def _normalize_rows(rows) -> list[dict]:
    normalized: list[dict] = []
    for row in rows or ():
        if isinstance(row, dict):
            normalized.append(row)
            continue
        try:
            normalized.append(dict(row))
        except (TypeError, ValueError):
            continue
    return normalized


def _active_quests(session) -> list[tuple[str, str]]:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_quests"):
        return []

    result: list[tuple[str, str]] = []
    for row in _normalize_rows(database.list_quests(character.id)):
        if row.get("status") != "active":
            continue
        quest_key = str(row.get("quest_key") or "")
        definition = QUESTS_BY_KEY.get(quest_key)
        if definition is None:
            continue
        objective = definition.objective_for_step(row.get("current_step"))
        result.append((definition.name, objective or "Continue the current quest."))
    return result


def _people_here(session) -> tuple[str, ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    room = ROOMS_BY_KEY.get(character.current_room or "")
    if room is None:
        return ()
    names: list[str] = []
    for npc_key in room.npc_keys:
        npc = NPCS_BY_KEY.get(npc_key)
        if npc is not None and npc.name not in names:
            names.append(npc.name)
    return tuple(names)


def _class_commands(session) -> tuple[str, ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    abilities = class_abilities_for_level(
        character.character_class or "",
        character.level,
        character.deity_key,
    )
    commands: list[str] = []
    for ability in abilities:
        if ability.key not in EXECUTABLE_CLASS_ABILITY_KEYS:
            continue
        if ability.key == "nurture":
            command = "NURTURE <target>"
        elif ability.key == "forage":
            command = "USE FORAGE"
        else:
            command = f"USE {ability.name.upper()}"
        commands.append(f"{command} - {ability.name}")
    return tuple(commands)


def _racial_lines(session) -> tuple[str, ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    race_key = character.race or ""
    race = RACES_BY_KEY.get(race_key)
    if race is None:
        return ()
    lines: list[str] = ["RACIAL - show your racial passive, at-will, and cooldown"]
    if race.passive_name:
        lines.append(f"Passive: {race.passive_name}")
    command = RACIAL_COMMAND_SYNTAX.get(race_key)
    if command:
        # The live server installs the full racial definitions before play. The
        # fallback name keeps this help layer independently testable and prevents
        # a missing display field from hiding a known executable racial command.
        ability_name = race.ability_name or RACIAL_ACTIVE_NAMES.get(race_key, "Racial ability")
        lines.append(f"{command} - {ability_name}")
    return tuple(lines)


def _culture_commands(session) -> tuple[str, ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    return RACE_CULTURE_COMMANDS.get(character.race or "", ())


def _quick_help_text(session) -> str:
    lines = [
        "\r\n--- Help ---",
        "LOOK and EXITS show where you are. Move with NORTH/SOUTH/EAST/WEST/UP/DOWN (or N/S/E/W/U/D).",
        "EXAMINE <thing>, SEARCH <thing>, TOUCH <thing>, LISTEN, READ <thing>, and TALK <person> interact with the world.",
        "SAY <message> speaks aloud to players in your room. BASICS gives the tiny new-player version at any time.",
        "QUESTS shows your quest journal. ABILITIES shows your class abilities. RACIAL shows your racial kit.",
        "ATTACK <target>, USE <ability>, and FLEE cover the basic combat loop.",
        "INVENTORY and EQUIPMENT show what you carry and wear. Your opening teaches class basics naturally as you progress.",
    ]
    active = _active_quests(session)
    if active:
        name, objective = active[0]
        lines.append(f"Current objective - {name}: {objective}")
    people = _people_here(session)
    if people:
        lines.append("Someone here can be spoken to: " + ", ".join(people) + ".")
    lines.append("Type COMMANDS or HELP ALL for the full categorized command list tailored to this character.")
    return "\r\n".join(lines) + "\r\n"


def _full_help_text(session) -> str:
    character = getattr(session, "character", None)
    class_commands = _class_commands(session)
    racial_lines = _racial_lines(session)
    culture_commands = _culture_commands(session)
    active = _active_quests(session)
    people = _people_here(session)

    lines = [
        "\r\n--- Commands: Your Character ---",
        "This list favors commands that are implemented and usable by this character right now.",
        "",
        "[Movement & Exploration]",
        "LOOK (L) - show the current room",
        "EXITS - show available routes",
        "NORTH/SOUTH/EAST/WEST/UP/DOWN (N/S/E/W/U/D) - travel",
        "EXAMINE <thing> - inspect a room feature, object, or clue",
        "SEARCH <thing> - search an authored feature when supported",
        "TOUCH <thing> - physically interact with an authored feature",
        "LISTEN [thing] - listen to the room or a supported feature",
        "READ <thing> - read an item, note, sign, or authored text",
        "TALK <person> - speak to someone in the room",
        "SAY <message> - speak aloud to other players in the room",
        "BASICS - show the tiny new-player command refresher",
        "FEATURES / DETAILS / LANDMARKS - review visible room features",
        "",
        "[Character & Progression]",
        "SCORE / STATUS / SHEET - character overview",
        "STATS - attribute details",
        "HEALTH / HP - health details",
        "MANA - mana details",
        "LORE - race and world identity information",
        "PROGRESS / SKILLS - progression details",
        "ABILITIES - unlocked class abilities",
        "QUESTS / JOURNAL - quest journal and current objectives",
        "ACCESS - persistent access and progression gates",
        "BIND / BIND POINT - bind-point information",
        "INVENTORY - carried items",
        "EQUIPMENT - worn and wielded gear",
        "EQUIP <item> / UNEQUIP <slot or item> / COMPARE <item> - manage gear",
        "MENU / CHARACTERS - return toward character selection when supported",
        "QUIT - leave the game",
        "",
        "[Combat]",
        "ATTACK <target> / KILL <target> - begin combat",
        "FLEE / DISENGAGE - attempt to break away",
        "USE <ability> / CAST <ability> - use an unlocked executable class ability",
    ]

    if class_commands:
        lines.append("Your executable class abilities:")
        lines.extend(f"  {entry}" for entry in class_commands)
    else:
        lines.append("No additional executable class ability command is unlocked yet.")

    lines.extend(["", "[Racial]"])
    if racial_lines:
        lines.extend(racial_lines)
    else:
        lines.append("No racial command data is available for this character.")

    lines.extend(["", "[Culture]"])
    if culture_commands:
        lines.append("Commands specific to your people's authored culture:")
        lines.append("  " + ", ".join(culture_commands))
    else:
        lines.append("Your race currently uses LORE and its quest scenes rather than separate culture-menu commands.")

    lines.extend(
        [
            "",
            "[Crafts, Gathering & Shops]",
            "TRADES / PROFESSIONS - trade-skill information",
            "RECIPES - known crafting recipes",
            "CRAFT <recipe> - craft when the required station and materials are available",
            "MINE / HARVEST / HERBALISM - use supported gathering content",
            "SHOP / LIST / WARES - inspect a merchant when one is available",
            "",
            "[Time & World]",
            "TIME / CLOCK - current Astralis time",
            "WEATHER / CONDITIONS - current regional conditions",
            "DATE / TODAY / CALENDAR - Astralis calendar information",
            "SEASON / SEASONS - seasonal information",
            "",
            "[Right Now]",
        ]
    )

    if active:
        for name, objective in active:
            lines.append(f"Quest - {name}: {objective}")
    else:
        lines.append("No active quest objective is currently recorded.")

    if people:
        lines.append("People here: " + ", ".join(people) + ". Use TALK <person>.")
    else:
        lines.append("No authored NPC is standing in this room right now.")

    if character is not None:
        race = RACES_BY_KEY.get(character.race or "")
        race_name = race.name if race else (character.race or "Unknown")
        lines.append(
            f"Tailored for: {character.name} - Level {character.level} {race_name} "
            f"{(character.character_class or 'Unknown').title()}."
        )

    lines.extend(
        [
            "",
            "HELP or ? returns to the short beginner overview.",
            "Quest-specific verbs are not duplicated here: the live objective above gives the exact command when a quest needs one.",
        ]
    )
    return "\r\n".join(lines) + "\r\n"


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
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


def install_command_help_runtime(player_session_class) -> None:
    """Install one quiet HELP screen plus a contextual, categorized full index.

    This runtime is deliberately installed last. It owns HELP before older
    feature layers can append several separate help paragraphs, while delegating
    every non-help command through the complete existing runtime stack.
    """
    if getattr(player_session_class, "_command_help_runtime_installed", False):
        return

    # The newcomer layer sits immediately beneath HELP: it teaches typed-command
    # basics, provides real SAY/BASICS commands, and stays quiet once the player
    # demonstrates that they understand the interaction model.
    install_new_player_guidance_runtime(player_session_class)
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized in {"help", "?"}:
            await self.send(_quick_help_text(self))
            return
        if normalized in {"commands", "commands all", "help all", "help commands"}:
            await self.send(_full_help_text(self))
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._command_help_runtime_installed = True
