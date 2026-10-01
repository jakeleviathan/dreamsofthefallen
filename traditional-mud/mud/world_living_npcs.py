"""World-wide civilian routines, weather reactions, and ambient chatter.

The authored Waymeet, Brassgut, and Forest Elf community casts remain the gold
standard for bespoke local behavior. This module fills the rest of Astralis with
the same *kind* of life without moving quest-critical static NPCs.

At final world assembly it discovers safe connected room clusters by region,
checks how many scheduled residents already exist there, and adds only enough
non-quest residents to reach a small living-world baseline. Every generated
resident has a real route through existing exits, an Astralis-hour schedule,
optional weather shelter, visible movement through MobileNpcManager, ambient
room chatter, and TALK responses.

Nothing here invents invisible teleporting actors. If a resident is speaking,
the MobileNpcManager says that resident is physically in the room.
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import re
from collections import deque
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field

import mud.npcs as mobile_registry
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.npc_conversation import _delegate_prompt, resolve_mobile_talk_target
from mud.npc_name_audit import likely_given_name
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcDefinition, MobileNpcManager, RoutineStop


WORLD_LIVING_PREFIX = "world_living_"
TARGET_ROUTINE_RESIDENTS_PER_REGION = 2
MAX_ROUTE_ROOMS = 12
WET_WEATHER = frozenset(("rain", "storm", "thunderstorm", "snow", "duststorm"))

_BLOCKED_TAG_TOKENS = (
    "boss",
    "elite",
    "dungeon",
    "instance",
    "arena",
    "raid",
    "combat",
    "danger",
    "hostile",
    "tutorial",
    "practice",
    "training",
    "secret",
    "ritual",
    "finale",
    "capstone",
    "grave",
    "crypt",
    "tomb",
)
_SETTLED_TAG_TOKENS = (
    "city",
    "town",
    "village",
    "settlement",
    "market",
    "merchant",
    "shop",
    "street",
    "square",
    "plaza",
    "gate",
    "road",
    "guild",
    "workshop",
    "station",
    "social",
    "home",
    "peaceful",
    "camp",
    "port",
    "harbor",
    "inn",
    "tavern",
    "common",
    "hall",
    "cathedral",
    "temple",
    "shrine",
    "district",
    "court",
)
_SHELTER_TAG_TOKENS = (
    "inn",
    "tavern",
    "hall",
    "home",
    "house",
    "shop",
    "market",
    "workshop",
    "station",
    "cathedral",
    "temple",
    "guild",
    "shelter",
    "interior",
    "indoors",
)
_PLANAR_REGION_TOKENS = ("plane", "planar", "dream_realm")


@dataclass(frozen=True, slots=True)
class ResidentProfile:
    key: str
    role: str
    aliases: tuple[str, ...]
    description: str
    dawn: str
    day: str
    dusk: str
    night: str
    actions: tuple[str, ...]
    weather: str


PROFILES: tuple[ResidentProfile, ...] = (
    ResidentProfile(
        key="courier",
        role="courier",
        aliases=("courier", "runner", "messenger"),
        description="a local courier with a waxed satchel, route slips, and road dust on their boots",
        dawn="First run of the day is the quiet one. You learn more before everybody starts shouting.",
        day="I've crossed this region twice already. The road changes faster than the notices do.",
        dusk="Last deliveries are the ones people suddenly remember were urgent.",
        night="Anything that can wait until morning is finally honest about it.",
        actions=(
            "{name} checks a folded route slip against the signs around {room}.",
            "{name} reties a waxed satchel and counts the next stops under their breath.",
        ),
        weather="Weather like this turns every short route into a long one.",
    ),
    ResidentProfile(
        key="roadhand",
        role="roadhand",
        aliases=("roadhand", "mender", "repairer"),
        description="a local roadhand carrying chalk, cord, and a compact roll of repair tools",
        dawn="Best time to find what broke overnight is before the traffic hides it.",
        day="Most disasters announce themselves as small maintenance jobs first.",
        dusk="I mark what cannot be fixed before dark. Tomorrow starts with those marks.",
        night="The tools are put away. The roads keep making work anyway.",
        actions=(
            "{name} kneels briefly to inspect a worn edge near {room}, then adds a chalk mark.",
            "{name} tests a fitting with one thumb and makes a note on a scrap of board.",
        ),
        weather="Bad weather is useful. It shows you exactly where the world leaks.",
    ),
    ResidentProfile(
        key="quarterhand",
        role="quarterhand",
        aliases=("quarterhand", "factor", "supplier"),
        description="a local quarterhand comparing supply tallies with a bundle of marked tokens",
        dawn="If the numbers are right before breakfast, the rest of the day has a chance.",
        day="People notice shortages. They rarely notice the ten small decisions that prevented one.",
        dusk="I count what came back, not just what went out. Missing things tell stories.",
        night="Tomorrow's tally is already waiting. I'm choosing not to look at it yet.",
        actions=(
            "{name} sorts a handful of marked supply tokens and pockets two after checking {room}.",
            "{name} compares a short tally with the traffic moving through {room}.",
        ),
        weather="Storm days are when every spare blanket and dry crate suddenly becomes important.",
    ),
    ResidentProfile(
        key="watcher",
        role="local watcher",
        aliases=("watcher", "lookout", "watch"),
        description="a local watcher with a weathered cloak and the patient posture of someone paid to notice changes",
        dawn="Dawn is when the night leaves its evidence behind.",
        day="Most of the work is knowing what normally belongs here.",
        dusk="People hurry at dusk. Hurrying makes unusual things easier to spot.",
        night="At night, you listen first and decide what you saw second.",
        actions=(
            "{name} pauses at {room} and studies the approaches before moving on.",
            "{name} watches the passing traffic for a long moment, then relaxes slightly.",
        ),
        weather="Poor visibility does not make the watch shorter. It only makes it slower.",
    ),
    ResidentProfile(
        key="caretaker",
        role="caretaker",
        aliases=("caretaker", "keeper", "tender"),
        description="a local caretaker carrying twine, a cloth bundle, and the small tools of everyday upkeep",
        dawn="Places wake up better when somebody has already fixed the little things.",
        day="You can tell how a place is doing by what everyone steps around without mentioning.",
        dusk="Evening work is mostly putting tomorrow within reach.",
        night="A quiet room is not an empty one. It is a room finally resting.",
        actions=(
            "{name} straightens something small at {room} that most travelers would have walked past.",
            "{name} checks a latch, reties a loose cord, and continues the round.",
        ),
        weather="Wet days make twice the chores and half the time to do them.",
    ),
    ResidentProfile(
        key="surveyor",
        role="surveyor",
        aliases=("surveyor", "pathfinder", "mapper"),
        description="a local surveyor carrying a measuring cord, a stub of chalk, and a much-folded field map",
        dawn="Morning light is good for distances. Shadows have not started lying yet.",
        day="A map is only useful if somebody keeps checking it against the ground.",
        dusk="I stop measuring when I can no longer tell a shallow rut from a deep one.",
        night="I trust a night route I walked in daylight more than one somebody swears is safe.",
        actions=(
            "{name} stretches a short measuring cord beside {room} and marks the result on a folded map.",
            "{name} turns a field map sideways, compares it with the road, and adds a tiny correction.",
        ),
        weather="Rain erases bad maps and improves honest ones.",
    ),
)

_GIVEN_PREFIXES = (
    "Ar", "Bel", "Cael", "Dar", "Eri", "Fen", "Gav", "Hel", "Ira", "Jor",
    "Kel", "Lor", "Mav", "Ner", "Ora", "Pell", "Quin", "Rav", "Sel", "Tor",
    "Una", "Val", "Wen", "Yor", "Zel", "Bran", "Cyr", "Dov", "Esm", "Fara",
)
_GIVEN_SUFFIXES = (
    "a", "an", "en", "in", "or", "is", "eth", "iel", "ren", "rin",
    "ven", "mar", "ric", "len", "wyn", "ira", "esh", "ara", "orn", "une",
    "ek", "oth", "ali", "eva", "ien", "ora", "urn", "ess", "aro", "ynn",
)
_SURNAME_SUFFIXES = ("ward", "mark", "reed", "bell", "stone", "wake", "mere", "row", "vale", "rest")


@dataclass(frozen=True, slots=True)
class ResidentMetadata:
    key: str
    region_key: str
    region_name: str
    profile: ResidentProfile


WORLD_LIVING_METADATA: dict[str, ResidentMetadata] = {}
WORLD_LIVING_NPCS: tuple[MobileNpcDefinition, ...] = ()


def _stable_number(seed: str) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:8], "big")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _region_name(region_key: str) -> str:
    return " ".join(word.capitalize() for word in region_key.replace("-", "_").split("_") if word)


def _tokens(room) -> tuple[str, ...]:
    return tuple(str(tag).casefold() for tag in getattr(room, "tags", ()))


def _blocked(room) -> bool:
    if getattr(room, "enemy_keys", ()):
        return True
    tags = _tokens(room)
    return any(token in tag for tag in tags for token in _BLOCKED_TAG_TOKENS)


def _settled_score(room) -> int:
    tags = _tokens(room)
    score = sum(1 for tag in tags if any(token in tag for token in _SETTLED_TAG_TOKENS))
    if getattr(room, "npc_keys", ()):
        score += 4
    name = str(getattr(room, "name", "")).casefold()
    if any(word in name for word in ("market", "square", "gate", "hall", "inn", "tavern", "street", "court")):
        score += 2
    return score


def _shelter_score(room) -> int:
    tags = _tokens(room)
    score = sum(2 for tag in tags if any(token in tag for token in _SHELTER_TAG_TOKENS))
    name = str(getattr(room, "name", "")).casefold()
    if any(word in name for word in ("inn", "tavern", "hall", "house", "cathedral", "temple", "market", "workshop")):
        score += 3
    if getattr(room, "npc_keys", ()):
        score += 1
    return score


def _neighbors(room_key: str, allowed: set[str]) -> tuple[str, ...]:
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is None:
        return ()
    return tuple(destination for destination in room.exits.values() if destination in allowed)


def _component(start: str, allowed: set[str]) -> tuple[str, ...]:
    seen = {start}
    queue = deque([start])
    ordered: list[str] = []
    while queue:
        room_key = queue.popleft()
        ordered.append(room_key)
        for destination in _neighbors(room_key, allowed):
            if destination in seen:
                continue
            seen.add(destination)
            queue.append(destination)
    return tuple(ordered)


def _bounded_component(start: str, allowed: set[str], limit: int = MAX_ROUTE_ROOMS) -> tuple[str, ...]:
    seen = {start}
    queue = deque([start])
    ordered: list[str] = []
    while queue and len(ordered) < limit:
        room_key = queue.popleft()
        ordered.append(room_key)
        for destination in _neighbors(room_key, allowed):
            if destination in seen:
                continue
            seen.add(destination)
            queue.append(destination)
    return tuple(ordered)


def _best_cluster(region_key: str) -> tuple[str, ...]:
    region_rooms = {
        key
        for key, room in legacy_world.ROOMS_BY_KEY.items()
        if room.region_key == region_key and not _blocked(room)
    }
    if len(region_rooms) < 3:
        return ()

    remaining = set(region_rooms)
    components: list[tuple[str, ...]] = []
    while remaining:
        start = max(
            remaining,
            key=lambda key: (_settled_score(legacy_world.ROOMS_BY_KEY[key]), key),
        )
        found = _component(start, region_rooms)
        components.append(found)
        remaining.difference_update(found)

    eligible = [part for part in components if len(part) >= 3]
    if not eligible:
        return ()

    chosen = max(
        eligible,
        key=lambda part: (
            sum(_settled_score(legacy_world.ROOMS_BY_KEY[key]) for key in part),
            len(part),
        ),
    )
    anchor = max(
        chosen,
        key=lambda key: (_settled_score(legacy_world.ROOMS_BY_KEY[key]), -len(key), key),
    )
    return _bounded_component(anchor, set(chosen))


def _existing_routine_count(region_key: str) -> int:
    count = 0
    for definition in mobile_registry.MOBILE_NPCS_BY_KEY.values():
        if definition.behavior != BEHAVIOR_ROUTINE:
            continue
        room = legacy_world.ROOMS_BY_KEY.get(definition.spawn_room_key)
        if room is not None and room.region_key == region_key:
            count += 1
    return count


def _used_given_names() -> set[str]:
    used: set[str] = set()
    for npc in legacy_world.NPCS_BY_KEY.values():
        given = likely_given_name(npc.name, getattr(npc, "role", ""))
        if given:
            used.add(given)
    for npc in mobile_registry.MOBILE_NPCS_BY_KEY.values():
        given = likely_given_name(npc.name, "")
        if given:
            used.add(given)
    return used


def _unique_given_name(seed: str, used: set[str]) -> str:
    for attempt in range(512):
        number = _stable_number(f"{seed}:{attempt}")
        prefix = _GIVEN_PREFIXES[number % len(_GIVEN_PREFIXES)]
        suffix = _GIVEN_SUFFIXES[(number // len(_GIVEN_PREFIXES)) % len(_GIVEN_SUFFIXES)]
        candidate = prefix + suffix
        if candidate.casefold() not in used:
            used.add(candidate.casefold())
            return candidate
    raise RuntimeError("Unable to generate a unique living-world given name")


def _surname(anchor_room, resident_index: int) -> str:
    words = [
        word.capitalize()
        for word in re.findall(r"[A-Za-z]+", anchor_room.name)
        if word.casefold() not in {"the", "of", "a", "an", "and"}
    ]
    stem = (words[-1] if words else "Road")[:12]
    suffix = _SURNAME_SUFFIXES[resident_index % len(_SURNAME_SUFFIXES)]
    if stem.casefold().endswith(suffix):
        return stem
    return stem + suffix


def _choose_profile(region_key: str, resident_index: int, anchor_room) -> ResidentProfile:
    base = _stable_number(f"{region_key}:{resident_index}:{anchor_room.key}")
    return PROFILES[base % len(PROFILES)]


def _schedule(route: tuple[str, ...], resident_index: int) -> tuple[RoutineStop, ...]:
    anchor = max(
        route,
        key=lambda key: (_settled_score(legacy_world.ROOMS_BY_KEY[key]), key),
    )
    shelter_candidates = sorted(
        route,
        key=lambda key: (_shelter_score(legacy_world.ROOMS_BY_KEY[key]), _settled_score(legacy_world.ROOMS_BY_KEY[key]), key),
        reverse=True,
    )
    home = shelter_candidates[0] if shelter_candidates else anchor

    others = [key for key in route if key != home]
    if not others:
        others = [home]
    morning = others[resident_index % len(others)]
    midday = anchor
    afternoon = others[(resident_index + max(1, len(others) // 2)) % len(others)]
    evening = max(
        route,
        key=lambda key: (
            _shelter_score(legacy_world.ROOMS_BY_KEY[key]) + _settled_score(legacy_world.ROOMS_BY_KEY[key]),
            key,
        ),
    )
    return (
        RoutineStop(0, home),
        RoutineStop(6, morning),
        RoutineStop(9, midday),
        RoutineStop(13, afternoon),
        RoutineStop(18, evening),
        RoutineStop(22, home),
    )


def _definition_for_region(
    region_key: str,
    route: tuple[str, ...],
    resident_index: int,
    used_given: set[str],
) -> tuple[MobileNpcDefinition, ResidentMetadata]:
    anchor_key = max(
        route,
        key=lambda key: (_settled_score(legacy_world.ROOMS_BY_KEY[key]), key),
    )
    anchor = legacy_world.ROOMS_BY_KEY[anchor_key]
    profile = _choose_profile(region_key, resident_index, anchor)
    given = _unique_given_name(f"{region_key}:{profile.key}:{resident_index}", used_given)
    surname = _surname(anchor, resident_index)
    name = f"{given} {surname}"
    schedule = _schedule(route, resident_index)
    spawn_room = schedule[0].room_key
    shelter_room = max(
        route,
        key=lambda key: (_shelter_score(legacy_world.ROOMS_BY_KEY[key]), key),
    )
    if _shelter_score(legacy_world.ROOMS_BY_KEY[shelter_room]) <= 0:
        shelter_room = None

    key = f"{WORLD_LIVING_PREFIX}{_slug(region_key)}_{resident_index + 1}"
    definition = MobileNpcDefinition(
        key=key,
        name=name,
        short_description=profile.description,
        spawn_room_key=spawn_room,
        allowed_room_keys=route,
        behavior=BEHAVIOR_ROUTINE,
        move_chance_per_tick=0.90,
        aliases=(given.casefold(), surname.casefold(), *profile.aliases),
        routine_schedule=schedule,
        weather_shelter_room_key=shelter_room,
        shelter_weathers=("rain", "storm", "thunderstorm", "snow", "duststorm"),
    )
    metadata = ResidentMetadata(
        key=key,
        region_key=region_key,
        region_name=_region_name(region_key),
        profile=profile,
    )
    return definition, metadata


def register_world_living_npcs() -> tuple[MobileNpcDefinition, ...]:
    """Fill every suitable region to a modest baseline of scheduled residents.

    The function is deliberately idempotent. It can run once during final content
    assembly (so name audits see the residents) and again when MudServer starts
    (so direct imports or test harnesses also get a complete manager).
    """

    global WORLD_LIVING_NPCS

    used_given = _used_given_names()
    regions = sorted({room.region_key for room in legacy_world.ROOMS_BY_KEY.values() if room.region_key})

    for region_key in regions:
        if any(token in region_key.casefold() for token in _PLANAR_REGION_TOKENS):
            continue
        route = _best_cluster(region_key)
        if len(route) < 3:
            continue

        needed = max(0, TARGET_ROUTINE_RESIDENTS_PER_REGION - _existing_routine_count(region_key))
        if needed <= 0:
            continue

        existing_generated = sum(
            1
            for definition in mobile_registry.MOBILE_NPCS_BY_KEY.values()
            if definition.key.startswith(f"{WORLD_LIVING_PREFIX}{_slug(region_key)}_")
        )
        for offset in range(needed):
            resident_index = existing_generated + offset
            definition, metadata = _definition_for_region(
                region_key, route, resident_index, used_given,
            )
            existing = mobile_registry.MOBILE_NPCS_BY_KEY.get(definition.key)
            if existing is not None:
                WORLD_LIVING_METADATA.setdefault(definition.key, metadata)
                continue
            mobile_registry.MOBILE_NPCS_BY_KEY[definition.key] = definition
            mobile_registry.MOBILE_NPC_DEFINITIONS += (definition,)
            WORLD_LIVING_METADATA[definition.key] = metadata

    generated = tuple(
        definition
        for definition in mobile_registry.MOBILE_NPC_DEFINITIONS
        if definition.key.startswith(WORLD_LIVING_PREFIX)
    )
    WORLD_LIVING_NPCS = generated
    return generated


def phase_at(hour: int) -> str:
    if 5 <= hour < 8:
        return "dawn"
    if 8 <= hour < 18:
        return "day"
    if 18 <= hour < 21:
        return "dusk"
    return "night"


def _present_generated(manager: MobileNpcManager, room_key: str):
    return tuple(
        state.definition
        for state in manager.npcs_in_room(room_key)
        if state.definition.key in WORLD_LIVING_METADATA
    )


def talk_lines(definition: MobileNpcDefinition, hour: int, weather: str) -> tuple[str, ...]:
    metadata = WORLD_LIVING_METADATA.get(definition.key)
    if metadata is None:
        return ()
    profile = metadata.profile
    phase = phase_at(hour)
    spoken = getattr(profile, phase)
    lines = [f"{definition.name} says, '{spoken}'"]
    if weather.casefold() in WET_WEATHER:
        lines.append(f"{definition.name} adds, '{profile.weather}'")
    return tuple(lines)


def chatter_lines(
    manager: MobileNpcManager,
    room_key: str,
    hour: int,
    weather: str,
    *,
    rng: random.Random | None = None,
) -> tuple[str, ...]:
    present = _present_generated(manager, room_key)
    if not present:
        return ()
    rng = rng or random.Random()
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    room_name = room.name if room is not None else "the road"

    if len(present) > 1 and rng.random() < 0.34:
        first, second = rng.sample(list(present), 2)
        return (
            f"{first.name} pauses beside {second.name} long enough to compare local notes about {room_name}.",
            f"{second.name} answers with a quick correction, and both adjust their rounds before moving on.",
        )

    actor = rng.choice(present)
    metadata = WORLD_LIVING_METADATA[actor.key]
    profile = metadata.profile
    if weather.casefold() in WET_WEATHER and rng.random() < 0.62:
        return (f"{actor.name} remarks, '{profile.weather}'",)
    action = rng.choice(profile.actions).format(name=actor.name, room=room_name)
    return (action,)


@dataclass(slots=True)
class WorldLivingChatterDirector:
    cooldown_seconds: float = 110.0
    last_spoken: dict[str, float] = field(default_factory=dict)

    def due_lines(
        self,
        manager: MobileNpcManager,
        room_key: str,
        hour: int,
        weather: str,
        *,
        now: float,
        rng: random.Random | None = None,
    ) -> tuple[str, ...]:
        if now - self.last_spoken.get(room_key, float("-inf")) < self.cooldown_seconds:
            return ()
        lines = chatter_lines(manager, room_key, hour, weather, rng=rng)
        if lines:
            self.last_spoken[room_key] = now
        return lines


async def run_world_living_chatter(
    manager: MobileNpcManager,
    player_rooms_provider: Callable[[], Iterable[str]],
    broadcast: Callable[[str, str], Awaitable[None]],
    weather_provider: Callable[[str], str],
    *,
    interval_seconds: float = 32.0,
) -> None:
    """Emit low-frequency local activity only in rooms that currently have players."""

    loop = asyncio.get_running_loop()
    rng = random.Random()
    director = WorldLivingChatterDirector()
    while True:
        await asyncio.sleep(interval_seconds)
        hour = ASTRALIS_CLOCK.now().hour
        for room_key in sorted(set(player_rooms_provider())):
            if rng.random() > 0.68:
                continue
            room = legacy_world.ROOMS_BY_KEY.get(room_key)
            if room is None:
                continue
            weather = weather_provider(room.region_key)
            lines = director.due_lines(
                manager,
                room_key,
                hour,
                weather,
                now=loop.time(),
                rng=rng,
            )
            if lines:
                await broadcast(room_key, "\r\n".join(lines))


def install_world_living_talk_runtime(player_session_class, world_service) -> None:
    """Give generated residents ordinary TALK responses without owning quests."""

    if getattr(player_session_class, "_world_living_talk_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        stripped = command.strip()
        pieces = stripped.split(maxsplit=1)
        if not pieces or pieces[0].casefold() != "talk":
            await _delegate_prompt(self, previous_playing_prompt, command)
            return

        target = pieces[1].strip() if len(pieces) > 1 else ""
        if target.casefold().startswith("to "):
            target = target[3:].strip()
        if not target:
            await _delegate_prompt(self, previous_playing_prompt, command)
            return

        definition, ambiguous = resolve_mobile_talk_target(self, target)
        if ambiguous:
            generated_ambiguous = tuple(
                name
                for name in ambiguous
                if any(
                    meta.key == state.definition.key and state.definition.name == name
                    for state in getattr(self.mobile_npcs, "states", {}).values()
                    for meta in WORLD_LIVING_METADATA.values()
                )
            )
            if generated_ambiguous:
                await self.send(
                    "That description matches more than one local here: "
                    + ", ".join(generated_ambiguous)
                    + ". Be more specific.\r\n"
                )
                return
            await _delegate_prompt(self, previous_playing_prompt, command)
            return

        if definition is None or definition.key not in WORLD_LIVING_METADATA:
            await _delegate_prompt(self, previous_playing_prompt, command)
            return

        room_key = self.character.current_room or ""
        room = legacy_world.ROOMS_BY_KEY.get(room_key)
        weather = world_service.state.weather_for(room.region_key) if room is not None else "clear"
        for line in talk_lines(definition, ASTRALIS_CLOCK.now().hour, weather):
            await self.send(line + "\r\n")

    player_session_class.playing_prompt = playing_prompt
    player_session_class._world_living_talk_installed = True
