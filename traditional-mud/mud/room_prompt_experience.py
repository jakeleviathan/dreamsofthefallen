from __future__ import annotations

import re
from typing import Any

from mud.astralis_human_district import HUMAN_DISTRICT
from mud.combat import ENEMIES_BY_KEY
from mud.player_preferences import (
    hint_level,
    install_player_preferences_runtime,
    persist_prompt_mode,
    style_text,
)
from mud.quests import QUESTS_BY_KEY
from mud.room_runtime import (
    WORLD as LIVE_WORLD,
    _context_for,
    _puddle_here,
    _render_business_status,
)
from mud.social_experience import install_social_experience_runtime
from mud.world import NPCS_BY_KEY


PROMPT_MODES = frozenset({"quiet", "compact", "full"})
DEFAULT_PROMPT_MODE = "compact"
_TALK_OBJECTIVE = re.compile(r"\bTALK\s+(?:TO\s+)?([A-Z][A-Z'\-]*)\b", re.IGNORECASE)


def _row_value(row: Any, key: str, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        value = row[key]
    except (KeyError, TypeError, IndexError):
        return default
    return default if value is None else value


def _prompt_mode(session) -> str:
    if bool(getattr(session, "_screen_reader_enabled", False)):
        return "quiet"
    mode = str(getattr(session, "_room_ux_prompt_mode", DEFAULT_PROMPT_MODE)).lower()
    return mode if mode in PROMPT_MODES else DEFAULT_PROMPT_MODE


def _target_prompt_text(session) -> str:
    enemy = getattr(session, "active_enemy", None)
    if enemy is None:
        return ""
    definition = getattr(enemy, "definition", None)
    if definition is None:
        return ""
    current_hp = int(getattr(enemy, "current_hp", 0) or 0)
    max_hp = int(getattr(definition, "max_hp", 0) or 0)
    name = str(getattr(definition, "name", "Target") or "Target")
    return f" | {name} {current_hp}/{max_hp}"


def prompt_text(session, *, leading_newline: bool = True) -> str:
    prefix = "\r\n" if leading_newline else ""
    mode = _prompt_mode(session)
    combatant = getattr(session, "combatant", None)
    if mode == "quiet" or combatant is None:
        return prefix + "> "

    hp = int(getattr(combatant, "current_hp", 0) or 0)
    max_hp = int(getattr(combatant, "max_hp", 0) or 0)
    mana = int(getattr(combatant, "current_mana", 0) or 0)
    max_mana = int(getattr(combatant, "max_mana", 0) or 0)
    target = _target_prompt_text(session)

    if mode == "compact":
        text = f"[HP {hp}/{max_hp}  MP {mana}/{max_mana}{target}]"
        return prefix + style_text(session, text, "accent") + " > "

    movement = int(getattr(combatant, "current_movement", 0) or 0)
    max_movement = int(getattr(combatant, "max_movement", 0) or 0)
    character = getattr(session, "character", None)
    level = int(getattr(character, "level", 1) or 1)
    text = f"[Lv {level} | HP {hp}/{max_hp} | MP {mana}/{max_mana} | MV {movement}/{max_movement}{target}]"
    return prefix + style_text(session, text, "accent") + " > "


def _npc_lines(session, scene) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    if scene is not None:
        for npc_key in getattr(scene, "npc_keys", ()):
            npc = NPCS_BY_KEY.get(npc_key)
            if npc is None or npc.name in seen:
                continue
            seen.add(npc.name)
            lines.append(f"{npc.name} - {npc.short_description}")

    mobile_npcs = getattr(session, "mobile_npcs", None)
    character = getattr(session, "character", None)
    if mobile_npcs is not None and character is not None:
        for state in mobile_npcs.npcs_in_room(character.current_room or ""):
            name = state.definition.name
            if name in seen:
                continue
            seen.add(name)
            lines.append(f"{name} - {state.definition.short_description}")
    return lines


def _enemy_lines(scene) -> list[str]:
    lines: list[str] = []
    if scene is None:
        return lines
    for enemy_key in getattr(scene, "enemy_keys", ()):
        enemy = ENEMIES_BY_KEY.get(enemy_key)
        if enemy is not None:
            lines.append(enemy.name)
    return lines


def _active_objectives(session) -> list[tuple[str, str, str, str]]:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return []
    try:
        rows = database.list_quests(character.id)
    except Exception:
        return []
    result: list[tuple[str, str, str, str]] = []
    for row in rows or ():
        if _row_value(row, "status") != "active":
            continue
        quest_key = str(_row_value(row, "quest_key", ""))
        step = str(_row_value(row, "current_step", ""))
        definition = QUESTS_BY_KEY.get(quest_key)
        if definition is None:
            continue
        objective = definition.objective_for_step(step)
        if objective:
            result.append((quest_key, step, definition.name, objective))
    return result


def _objective_talk_hint(session, scene) -> tuple[str, str, str] | None:
    character = getattr(session, "character", None)
    if character is None or scene is None:
        return None
    if int(getattr(character, "level", 1) or 1) > 3:
        return None

    available: list[tuple[str, object]] = []
    for npc_key in getattr(scene, "npc_keys", ()):
        npc = NPCS_BY_KEY.get(npc_key)
        if npc is not None:
            available.append((npc_key, npc))
    if not available:
        return None

    for quest_key, step, _name, objective in _active_objectives(session):
        match = _TALK_OBJECTIVE.search(objective)
        if match is None:
            continue
        talk_name = match.group(1)
        needle = talk_name.lower()
        for npc_key, npc in available:
            aliases = tuple(str(alias).lower() for alias in getattr(npc, "aliases", ()) or ())
            name_words = {word.strip(".,'\"").lower() for word in str(npc.name).split()}
            if needle in name_words or any(needle == alias or needle in alias.split() for alias in aliases):
                hint_key = f"{character.id}:{quest_key}:{step}:{npc_key}"
                return hint_key, npc.name, talk_name.upper()
    return None


async def _maybe_send_context_hint(session, scene) -> None:
    level = hint_level(session)
    if level == "off":
        return

    shown = getattr(session, "_room_ux_shown_hints", None)
    if shown is None:
        shown = set()
        session._room_ux_shown_hints = shown

    hint = _objective_talk_hint(session, scene)
    if hint is not None:
        hint_key, npc_name, command_name = hint
        if hint_key not in shown:
            shown.add(hint_key)
            await session.send(f"\r\nYou could TALK {command_name}. ({npc_name} is here.)\r\n")
        return

    if level != "full":
        return
    character = getattr(session, "character", None)
    if character is None:
        return
    objectives = _active_objectives(session)
    if not objectives:
        return
    quest_key, step, quest_name, objective = objectives[0]
    hint_key = f"objective:{character.id}:{quest_key}:{step}"
    if hint_key in shown:
        return
    shown.add(hint_key)
    await session.send(f"\r\nCurrent objective - {quest_name}: {objective}\r\n")


async def _render_room(session, world, previous_show_current_room) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    try:
        view = world.build_view(character.current_room or "", _context_for(session))
    except Exception:
        await previous_show_current_room(session)
        return
    if view is None:
        await previous_show_current_room(session)
        return

    scene = world.scene(view.key)
    await session.send(style_text(session, view.name, "heading") + "\r\n")
    await session.send(view.description.replace("\n", "\r\n") + "\r\n")

    notable = [feature.name for feature in getattr(view, "features", ())]
    if world is LIVE_WORLD and _puddle_here(session):
        notable.append("Puddle")
    business = HUMAN_DISTRICT.business_in_room(view.key) if world is LIVE_WORLD else None
    if business is not None and business.name not in notable:
        notable.append(business.name)
    if notable:
        await session.send("\r\n" + style_text(session, "Notable:", "accent") + " " + ", ".join(notable) + ".\r\n")

    people = _npc_lines(session, scene)
    if people:
        await session.send(style_text(session, "People:", "accent") + "\r\n")
        for line in people:
            await session.send(f"  {line}\r\n")

    threats = _enemy_lines(scene)
    if threats:
        await session.send(style_text(session, "Threats:", "accent") + " " + ", ".join(threats) + ".\r\n")

    exits = []
    for exit_view in getattr(view, "exits", ()):
        label = exit_view.direction.upper()
        if exit_view.name:
            label += f" - {exit_view.name}"
        exits.append(label)
    if exits:
        await session.send(style_text(session, "Exits:", "accent") + " " + " | ".join(exits) + "\r\n")

    if business is not None:
        await _render_business_status(session)

    await _maybe_send_context_hint(session, scene)


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


async def _show_prompt_setting(session) -> None:
    mode = _prompt_mode(session)
    await session.send(
        f"Prompt mode: {mode.upper()}.\r\n"
        "PROMPT QUIET - just >\r\n"
        "PROMPT COMPACT - HP and mana\r\n"
        "PROMPT FULL - level, HP, mana, movement, and current target\r\n"
        "Prompt choices are saved to your account. SETTINGS shows the rest of your presentation options.\r\n"
    )


def install_room_prompt_experience_runtime(player_session_class, world_service=None) -> None:
    """Make moment-to-moment text play readable without turning it into a HUD dump."""
    if getattr(player_session_class, "_room_prompt_experience_runtime_installed", False):
        return

    # Presentation preferences and social communication are part of the same
    # player-facing shell. Install them immediately beneath this final room/prompt
    # layer so normal game commands still flow through the complete older stack.
    install_player_preferences_runtime(player_session_class)
    install_social_experience_runtime(player_session_class)

    world = world_service or LIVE_WORLD
    previous_show_current_room = player_session_class.show_current_room
    previous_playing_prompt = player_session_class.playing_prompt

    async def show_current_room(self) -> None:
        await _render_room(self, world, previous_show_current_room)

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt(prompt_text(self))
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized in {"prompt", "prompt status", "prompt help"}:
            await _show_prompt_setting(self)
            return
        if normalized.startswith("prompt "):
            requested = normalized.split(maxsplit=1)[1]
            aliases = {
                "off": "quiet",
                "minimal": "quiet",
                "quiet": "quiet",
                "compact": "compact",
                "default": "compact",
                "full": "full",
            }
            mode = aliases.get(requested)
            if mode is None:
                await self.send("Choose PROMPT QUIET, PROMPT COMPACT, or PROMPT FULL.\r\n")
                return
            persist_prompt_mode(self, mode)
            if bool(getattr(self, "_screen_reader_enabled", False)):
                await self.send(
                    f"Prompt preference saved as {mode.upper()}. Screen reader mode keeps the live prompt quiet until that mode is disabled.\r\n"
                )
            else:
                await self.send(f"Prompt mode set to {mode.upper()} and saved.\r\n")
            return

        await _delegate_command(self, previous_playing_prompt, command)

    def current_prompt_text(self) -> str:
        return prompt_text(self, leading_newline=False)

    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class.current_prompt_text = current_prompt_text
    player_session_class._room_prompt_experience_runtime_installed = True
