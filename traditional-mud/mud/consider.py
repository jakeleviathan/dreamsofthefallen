from __future__ import annotations

import math
import re
from dataclasses import dataclass

from mud.actor_inspection import find_visible_actor
from mud.combat import ENEMIES_BY_KEY
from mud.enemy_lifecycle import static_enemy_available
from mud.partial_target_matching import normalize_target


_LEVEL_BAND = re.compile(r"^level_(\d+)(?:_(\d+))?$")
_VALID_RANKS = {"normal", "elite", "boss"}
_RANK_LEVEL_BONUS = {"normal": 0, "elite": 2, "boss": 4}


@dataclass(frozen=True, slots=True)
class ThreatAssessment:
    key: str
    label: str
    comparison: str
    guidance: str


THREAT_BANDS: tuple[tuple[int | None, ThreatAssessment], ...] = (
    (-5, ThreatAssessment("trivial", "Trivial", "It looks vastly weaker than you.", "It should pose very little threat.")),
    (-3, ThreatAssessment("easy", "Easy", "It looks clearly weaker than you.", "You should have a comfortable advantage.")),
    (-1, ThreatAssessment("manageable", "Manageable", "It looks somewhat weaker than you.", "You should have the advantage, but it can still fight back.")),
    (1, ThreatAssessment("even", "Even Match", "It looks about evenly matched with you.", "Expect a fair fight if you engage it alone.")),
    (3, ThreatAssessment("dangerous", "Dangerous", "It looks stronger than you.", "Fighting it alone could be dangerous.")),
    (5, ThreatAssessment("very_dangerous", "Very Dangerous", "It looks far stronger than you.", "Fighting it alone would be very dangerous.")),
    (None, ThreatAssessment("deadly", "Deadly", "It looks overwhelmingly stronger than you.", "Attacking it alone could be deadly.")),
)


def challenge_rank(definition) -> str:
    """Return a hidden encounter rank without exposing it to the player.

    New content can explicitly author ``challenge_rank``. Older content still
    gets useful behavior from the naming conventions already used by generated
    dungeon enemies (``*_miniboss`` and ``*_boss``).
    """

    explicit = str(getattr(definition, "challenge_rank", "normal") or "normal").lower()
    if explicit in {"elite", "boss"}:
        return explicit

    key = str(getattr(definition, "key", "") or "").lower()
    aliases = tuple(str(alias).lower() for alias in getattr(definition, "aliases", ()) or ())
    if "final_boss" in key or key.endswith("_boss") or "boss" in aliases:
        return "boss"
    if "miniboss" in key or key.endswith("_elite") or "elite" in aliases:
        return "elite"
    return "normal"


def _room_level_hint(room_key: str, world_service) -> int | None:
    rooms = getattr(world_service, "legacy_rooms", None)
    room = rooms.get(room_key) if isinstance(rooms, dict) else None
    if room is None:
        return None

    for tag in tuple(getattr(room, "tags", ()) or ()):
        match = _LEVEL_BAND.fullmatch(str(tag).lower())
        if match is None:
            continue
        low = int(match.group(1))
        high = int(match.group(2) or low)
        return max(1, round((low + high) / 2))
    return None


def _fallback_level(definition, rank: str) -> int:
    """Estimate a legacy enemy's level when its room has no authored level tag.

    Most current world content has level-band room tags. This fallback keeps old
    starter/side content useful without requiring a mass data migration. XP is
    normalized for elite/boss reward multipliers before applying the curve.
    """

    if bool(getattr(definition, "tutorial", False)):
        return 1

    xp = max(1, int(getattr(definition, "xp_reward", 0) or 0))
    reward_multiplier = {"normal": 1.0, "elite": 2.2, "boss": 4.5}[rank]
    normalized_xp = max(1.0, xp / reward_multiplier)
    return max(1, round(5.0 * math.pow(normalized_xp / 48.0, 0.63)))


def enemy_base_level(definition, room_key: str, world_service) -> int:
    explicit = getattr(definition, "level", None)
    if explicit is not None:
        return max(1, int(explicit))
    room_level = _room_level_hint(room_key, world_service)
    if room_level is not None:
        return room_level
    return _fallback_level(definition, challenge_rank(definition))


def effective_enemy_level(definition, room_key: str, world_service) -> int:
    rank = challenge_rank(definition)
    return enemy_base_level(definition, room_key, world_service) + _RANK_LEVEL_BONUS[rank]


def assess_threat(player_level: int, enemy_level: int) -> ThreatAssessment:
    delta = int(enemy_level) - max(1, int(player_level))
    for upper_bound, assessment in THREAT_BANDS:
        if upper_bound is None or delta <= upper_bound:
            return assessment
    return THREAT_BANDS[-1][1]


def _definition_matches(definition, target: str) -> bool:
    query = normalize_target(target)
    if not query:
        return False
    terms = (getattr(definition, "name", ""), *tuple(getattr(definition, "aliases", ()) or ()))
    return any(normalize_target(term) == query for term in terms if term)


def _mobile_definition(session, actor_key: str):
    manager = getattr(session, "mobile_npcs", None)
    if manager is None:
        return None
    for state in manager.npcs_in_room(getattr(session.character, "current_room", "") or ""):
        if getattr(state.definition, "key", "") == actor_key:
            return state.definition
    return None


def _dead_target_name(session, target: str, world_service) -> str | None:
    character = getattr(session, "character", None)
    if character is None:
        return None
    room_key = character.current_room or ""

    scene = world_service.scene(room_key)
    if scene is not None:
        for enemy_key in tuple(getattr(scene, "enemy_keys", ()) or ()):
            definition = ENEMIES_BY_KEY.get(enemy_key)
            if definition is None or not _definition_matches(definition, target):
                continue
            if not static_enemy_available(
                room_key,
                enemy_key,
                database=getattr(session, "database", None),
            ):
                return definition.name

    active_enemy = getattr(session, "active_enemy", None)
    if active_enemy is not None and not bool(getattr(active_enemy, "alive", True)):
        definition = getattr(active_enemy, "definition", None)
        if definition is not None and _definition_matches(definition, target):
            return definition.name

    manager = getattr(session, "mobile_npcs", None)
    states = getattr(manager, "states", None)
    iterable = states.values() if isinstance(states, dict) else ()
    for state in iterable:
        definition = getattr(state, "definition", None)
        if definition is None or getattr(state, "current_room_key", "") != room_key:
            continue
        if bool(getattr(state, "active", True)):
            continue
        if _definition_matches(definition, target):
            return definition.name
    return None


def _consider_target(command: str) -> str | None:
    stripped = command.strip()
    normalized = " ".join(stripped.lower().split())
    for prefix in ("consider ", "con "):
        if normalized.startswith(prefix):
            return stripped[len(prefix):].strip()
    if normalized in {"consider", "con"}:
        return ""
    return None


async def handle_consider(session, command: str, world_service) -> bool:
    """Give a non-aggro qualitative danger read on a visible actor."""

    target = _consider_target(command)
    if target is None:
        return False
    if not target:
        await session.send("\r\nConsider whom? Usage: CONSIDER <target>.\r\n")
        return True

    dead_name = _dead_target_name(session, target, world_service)
    if dead_name is not None:
        await session.send(f"\r\n{dead_name} is already dead.\r\n")
        return True

    actor = find_visible_actor(session, world_service, target)
    if actor is None:
        await session.send(f"\r\nYou do not see {target} here.\r\n")
        return True

    if actor.kind != "enemy":
        await session.send(
            f"\r\nYou study {actor.name} for a moment. They do not seem interested in fighting you.\r\n"
        )
        return True

    definition = ENEMIES_BY_KEY.get(actor.key) or _mobile_definition(session, actor.key)
    if definition is None:
        await session.send(
            f"\r\nYou study {actor.name} carefully, but cannot get a reliable read on its strength.\r\n"
        )
        return True

    character = session.character
    room_key = character.current_room or ""
    assessment = assess_threat(
        getattr(character, "level", 1),
        effective_enemy_level(definition, room_key, world_service),
    )
    await session.send(
        "\r\n"
        f"You study {actor.name} carefully.\r\n"
        f"Threat: {assessment.label}\r\n"
        f"{assessment.comparison} {assessment.guidance}\r\n"
    )
    return True


def install_consider_runtime(player_session_class, world_service) -> None:
    """Install CONSIDER/CON at level 1 without touching combat or aggro state."""

    if getattr(player_session_class, "_consider_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            disconnected = getattr(type(state), "DISCONNECTED", None) if state is not None else None
            if disconnected is not None:
                self.state = disconnected
            return

        if await handle_consider(self, command, world_service):
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay(_text: str):
            return command

        self.prompt = replay
        try:
            await previous_playing_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._consider_runtime_installed = True
