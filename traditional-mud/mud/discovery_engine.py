from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from mud.astralis_time import ASTRALIS_CLOCK


DISCOVERY_SCHEMA = """
CREATE TABLE IF NOT EXISTS character_discoveries (
    character_id INTEGER NOT NULL,
    discovery_key TEXT NOT NULL,
    astralis_day INTEGER NOT NULL,
    room_key TEXT NOT NULL,
    trigger TEXT NOT NULL,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (character_id, discovery_key),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_character_discoveries_character
ON character_discoveries(character_id, discovered_at);

CREATE TABLE IF NOT EXISTS world_discovery_firsts (
    discovery_key TEXT PRIMARY KEY,
    character_id INTEGER,
    character_name TEXT NOT NULL,
    astralis_day INTEGER NOT NULL,
    room_key TEXT NOT NULL,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
);
"""


def _normalize(value: str) -> str:
    return " ".join(
        (value or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


@dataclass(frozen=True, slots=True)
class DiscoveryCondition:
    """Composable requirements for a hidden discovery.

    Conditions deliberately use only stable world concepts. Content can combine
    them without adding one-off command code: place, identity, time, weather,
    calendar, inventory, earlier discoveries, faction memory, ecology, and item
    heritage.
    """

    room_keys: tuple[str, ...] = ()
    region_keys: tuple[str, ...] = ()
    required_tags: tuple[str, ...] = ()
    races: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    min_level: int = 0
    max_level: int = 0
    time_buckets: tuple[str, ...] = ()
    weather: tuple[str, ...] = ()
    seasons: tuple[str, ...] = ()
    moon_phases: tuple[str, ...] = ()
    day_modulus: int = 0
    day_remainder: int = 0
    required_items: tuple[str, ...] = ()
    required_discoveries: tuple[str, ...] = ()
    forbidden_discoveries: tuple[str, ...] = ()
    min_region_standing: int | None = None
    min_region_renown: int | None = None
    ecology_min: tuple[tuple[str, float], ...] = ()
    ecology_max: tuple[tuple[str, float], ...] = ()
    requires_heritage_item: bool = False


@dataclass(frozen=True, slots=True)
class DiscoveryDefinition:
    key: str
    kind: str
    trigger: str
    text: str
    verbs: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    condition: DiscoveryCondition = field(default_factory=DiscoveryCondition)
    internal_name: str = ""
    experience_reward: int = 0
    chronicle_first: bool = False
    consume_command: bool = True

    def matches_command(self, verb: str, target: str) -> bool:
        if self.trigger != "command":
            return False
        normalized_verb = _normalize(verb)
        if self.verbs and normalized_verb not in {_normalize(value) for value in self.verbs}:
            return False
        if not self.targets:
            return not target
        normalized_target = _normalize(target)
        targets = {_normalize(value) for value in self.targets}
        return normalized_target in targets


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    discovered: bool
    handled: bool
    definition: DiscoveryDefinition | None = None
    world_first: bool = False


class DiscoveryRegistry:
    """Small indexed registry for hundreds of definitions."""

    def __init__(self, definitions: Iterable[DiscoveryDefinition]):
        self.definitions = tuple(definitions)
        self.by_room: dict[str, tuple[DiscoveryDefinition, ...]] = {}
        self.global_definitions: tuple[DiscoveryDefinition, ...] = ()
        room_buckets: dict[str, list[DiscoveryDefinition]] = {}
        globals_: list[DiscoveryDefinition] = []
        for definition in self.definitions:
            rooms = definition.condition.room_keys
            if not rooms:
                globals_.append(definition)
                continue
            for room_key in rooms:
                room_buckets.setdefault(room_key, []).append(definition)
        self.by_room = {
            room_key: tuple(values)
            for room_key, values in room_buckets.items()
        }
        self.global_definitions = tuple(globals_)

    def candidates(self, room_key: str) -> tuple[DiscoveryDefinition, ...]:
        return self.by_room.get(room_key, ()) + self.global_definitions


_WORLD_REGISTRIES: dict[int, DiscoveryRegistry] = {}


def ensure_discovery_schema(database) -> None:
    with database.connect() as db:
        db.executescript(DISCOVERY_SCHEMA)


def discovered_keys(database, character_id: int) -> frozenset[str]:
    ensure_discovery_schema(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT discovery_key FROM character_discoveries WHERE character_id = ?",
            (int(character_id),),
        ).fetchall()
    return frozenset(str(row["discovery_key"]) for row in rows)


def has_discovery(database, character_id: int, discovery_key: str) -> bool:
    ensure_discovery_schema(database)
    with database.connect() as db:
        row = db.execute(
            """
            SELECT 1
            FROM character_discoveries
            WHERE character_id = ? AND discovery_key = ?
            """,
            (int(character_id), discovery_key),
        ).fetchone()
    return row is not None


def discovery_record(database, character_id: int, discovery_key: str) -> dict[str, object] | None:
    ensure_discovery_schema(database)
    with database.connect() as db:
        row = db.execute(
            """
            SELECT discovery_key, astralis_day, room_key, trigger, discovered_at
            FROM character_discoveries
            WHERE character_id = ? AND discovery_key = ?
            """,
            (int(character_id), discovery_key),
        ).fetchone()
    if row is None:
        return None
    return {
        "discovery_key": str(row["discovery_key"]),
        "astralis_day": int(row["astralis_day"]),
        "room_key": str(row["room_key"]),
        "trigger": str(row["trigger"]),
        "discovered_at": str(row["discovered_at"]),
    }


def _time_bucket(hour: int) -> str:
    if 5 <= hour < 8:
        return "dawn"
    if 8 <= hour < 18:
        return "day"
    if 18 <= hour < 21:
        return "dusk"
    return "night"


def _has_heritage_item(database, character_id: int) -> bool:
    try:
        with database.connect() as db:
            row = db.execute(
                """
                SELECT 1
                FROM item_heritage_instances
                WHERE current_owner_character_id = ?
                  AND holder_kind = 'character'
                LIMIT 1
                """,
                (int(character_id),),
            ).fetchone()
        return row is not None
    except Exception:
        return False


def _condition_matches(
    session,
    world_service,
    definition: DiscoveryDefinition,
    *,
    known_discoveries: frozenset[str] | None = None,
) -> bool:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return False

    room_key = str(getattr(character, "current_room", "") or "")
    scene = world_service.scene(room_key) if world_service is not None else None
    if scene is None:
        return False
    condition = definition.condition

    if condition.room_keys and room_key not in condition.room_keys:
        return False
    if condition.region_keys and scene.region_key not in condition.region_keys:
        return False
    if condition.required_tags and not set(condition.required_tags).issubset(set(scene.tags)):
        return False

    race = str(getattr(character, "race", "") or "")
    class_key = str(getattr(character, "character_class", "") or "")
    level = int(getattr(character, "level", 1) or 1)
    if condition.races and race not in condition.races:
        return False
    if condition.classes and class_key not in condition.classes:
        return False
    if level < max(0, int(condition.min_level)):
        return False
    if condition.max_level and level > int(condition.max_level):
        return False

    moment = ASTRALIS_CLOCK.now()
    if condition.time_buckets and _time_bucket(moment.hour) not in condition.time_buckets:
        return False
    weather = str(world_service.state.weather_for(scene.region_key) or "clear").casefold()
    if condition.weather and weather not in {value.casefold() for value in condition.weather}:
        return False
    if condition.seasons and moment.season not in condition.seasons:
        return False
    if condition.moon_phases and moment.moon_phase not in condition.moon_phases:
        return False
    if condition.day_modulus:
        modulus = max(1, int(condition.day_modulus))
        if int(moment.day_number) % modulus != int(condition.day_remainder) % modulus:
            return False

    for item_key in condition.required_items:
        try:
            if int(database.item_quantity(character.id, item_key)) <= 0:
                return False
        except Exception:
            return False

    known = known_discoveries
    if known is None and (condition.required_discoveries or condition.forbidden_discoveries):
        known = discovered_keys(database, character.id)
    known = known or frozenset()
    if condition.required_discoveries and not set(condition.required_discoveries).issubset(known):
        return False
    if condition.forbidden_discoveries and set(condition.forbidden_discoveries).intersection(known):
        return False

    if condition.min_region_standing is not None or condition.min_region_renown is not None:
        try:
            from mud.faction_reputation import faction_for_region, get_reputation
            faction_key = faction_for_region(scene.region_key)
            if not faction_key:
                return False
            standing, renown = get_reputation(database, character.id, faction_key)
            if condition.min_region_standing is not None and standing < int(condition.min_region_standing):
                return False
            if condition.min_region_renown is not None and renown < int(condition.min_region_renown):
                return False
        except Exception:
            return False

    if condition.ecology_min or condition.ecology_max:
        try:
            from mud.ecology import ASTRALIS_ECOLOGY
            ecology = ASTRALIS_ECOLOGY.state_for(scene.region_key)
        except Exception:
            ecology = None
        if ecology is None:
            return False
        for field_name, threshold in condition.ecology_min:
            if float(getattr(ecology, field_name, -1.0)) < float(threshold):
                return False
        for field_name, threshold in condition.ecology_max:
            if float(getattr(ecology, field_name, 2.0)) > float(threshold):
                return False

    if condition.requires_heritage_item and not _has_heritage_item(database, character.id):
        return False

    return True


def _record_discovery(
    session,
    definition: DiscoveryDefinition,
    *,
    trigger: str,
) -> tuple[bool, bool]:
    character = session.character
    database = session.database
    moment = ASTRALIS_CLOCK.now()
    room_key = str(character.current_room or "")
    ensure_discovery_schema(database)

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO character_discoveries
            (character_id, discovery_key, astralis_day, room_key, trigger)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                int(character.id),
                definition.key,
                int(moment.day_number),
                room_key,
                trigger,
            ),
        )
        if not cursor.rowcount:
            return False, False

        name = str(getattr(character, "name", "") or "Unknown traveler")
        first = db.execute(
            """
            INSERT OR IGNORE INTO world_discovery_firsts
            (discovery_key, character_id, character_name, astralis_day, room_key)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                definition.key,
                int(character.id),
                name,
                int(moment.day_number),
                room_key,
            ),
        )
        world_first = bool(first.rowcount)

    return True, world_first


async def _apply_discovery(
    session,
    definition: DiscoveryDefinition,
    *,
    trigger: str,
) -> DiscoveryResult:
    created, world_first = _record_discovery(session, definition, trigger=trigger)
    if not created:
        return DiscoveryResult(False, False)

    await session.send("\r\n" + definition.text.rstrip() + "\r\n")

    # The public wiki learns only what a player has actually uncovered. Keep
    # this downstream of the successful discovery write so source definitions
    # never leak undiscovered secrets into the web surface.
    try:
        from mud.collective_wiki import record_hidden_discovery
        record_hidden_discovery(
            session,
            getattr(session, "_discovery_world_service", None),
            definition,
            trigger=trigger,
        )
    except Exception:
        pass

    reward = max(0, int(definition.experience_reward))
    if reward:
        try:
            session.database.add_experience(session.character.id, reward)
        except Exception:
            pass

    if world_first and definition.chronicle_first:
        try:
            from mud.living_world import _chronicle_insert
            moment = ASTRALIS_CLOCK.now()
            scene = None
            try:
                scene = getattr(session, "_discovery_world_service", None).scene(
                    session.character.current_room
                )
            except Exception:
                scene = None
            room_name = getattr(scene, "name", "somewhere in Astralis")
            _chronicle_insert(
                session.database,
                event_key=f"discovery:first:{definition.key}",
                day=int(moment.day_number),
                category="hidden_discovery",
                character_id=int(session.character.id),
                character_name=str(session.character.name),
                text=(
                    f"{session.character.name} was the first known traveler to uncover "
                    f"something long hidden near {room_name}."
                ),
            )
        except Exception:
            pass

    return DiscoveryResult(
        discovered=True,
        handled=bool(definition.consume_command),
        definition=definition,
        world_first=world_first,
    )


def _parse_command(command: str) -> tuple[str, str]:
    normalized = _normalize(command)
    if not normalized:
        return "", ""
    pieces = normalized.split()
    verb = pieces[0]
    target_words = pieces[1:]

    verb_aliases = {
        "l": "look",
        "exa": "examine",
        "inspect": "examine",
        "feel": "touch",
        "hear": "listen",
    }
    verb = verb_aliases.get(verb, verb)

    if verb == "look" and target_words and target_words[0] == "at":
        target_words = target_words[1:]
    elif verb == "listen" and target_words and target_words[0] == "to":
        target_words = target_words[1:]
    elif verb in {"pray", "kneel"} and target_words and target_words[0] in {"at", "to", "before"}:
        target_words = target_words[1:]

    return verb, " ".join(target_words)


def _registry_for_world(world_service) -> DiscoveryRegistry:
    identity = id(world_service)
    registry = _WORLD_REGISTRIES.get(identity)
    if registry is not None:
        return registry
    from mud.discovery_catalog import build_discovery_catalog
    registry = DiscoveryRegistry(build_discovery_catalog(world_service))
    _WORLD_REGISTRIES[identity] = registry
    return registry


def reset_discovery_registry_cache() -> None:
    _WORLD_REGISTRIES.clear()


async def attempt_discovery_command(
    session,
    world_service,
    command: str,
    *,
    registry: DiscoveryRegistry | None = None,
) -> DiscoveryResult:
    character = getattr(session, "character", None)
    if character is None:
        return DiscoveryResult(False, False)

    verb, target = _parse_command(command)
    if not verb:
        return DiscoveryResult(False, False)

    active_registry = registry or _registry_for_world(world_service)
    known = discovered_keys(session.database, character.id)
    for definition in active_registry.candidates(str(character.current_room or "")):
        if definition.key in known:
            continue
        if not definition.matches_command(verb, target):
            continue
        if not _condition_matches(
            session,
            world_service,
            definition,
            known_discoveries=known,
        ):
            continue
        return await _apply_discovery(session, definition, trigger=f"{verb}:{target}")
    return DiscoveryResult(False, False)


async def attempt_entry_discovery(
    session,
    world_service,
    *,
    registry: DiscoveryRegistry | None = None,
) -> DiscoveryResult:
    character = getattr(session, "character", None)
    if character is None or not getattr(character, "current_room", None):
        return DiscoveryResult(False, False)

    active_registry = registry or _registry_for_world(world_service)
    known = discovered_keys(session.database, character.id)
    for definition in active_registry.candidates(str(character.current_room)):
        if definition.key in known or definition.trigger != "enter":
            continue
        if not _condition_matches(
            session,
            world_service,
            definition,
            known_discoveries=known,
        ):
            continue
        return await _apply_discovery(session, definition, trigger="enter")
    return DiscoveryResult(False, False)


_GENERIC_TELL_TARGETS = frozenset({
    "air", "area", "clue", "clues", "crowd", "details", "gossip", "locals",
    "marks", "pattern", "rumor", "rumors", "signs", "silence", "surroundings",
    "traveler", "travelers",
})


def _has_living_condition(condition: DiscoveryCondition) -> bool:
    return bool(
        condition.time_buckets
        or condition.weather
        or condition.seasons
        or condition.moon_phases
        or condition.day_modulus
        or condition.min_region_standing is not None
        or condition.min_region_renown is not None
        or condition.ecology_min
        or condition.ecology_max
        or condition.requires_heritage_item
    )


def discovery_tell(
    session,
    world_service,
    *,
    registry: DiscoveryRegistry | None = None,
) -> str | None:
    """Expose one subtle affordance when living-world conditions unlock a secret.

    The tell names only an inspectable detail. It never reveals the discovery
    result, exact command, reward, internal name, or any completion count.
    """
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if (
        character is None
        or database is None
        or not callable(getattr(database, "connect", None))
        or world_service is None
    ):
        return None

    room_key = str(getattr(character, "current_room", "") or "")
    if not room_key:
        return None

    active_registry = registry or _registry_for_world(world_service)
    known = discovered_keys(database, int(character.id))
    for definition in active_registry.candidates(room_key):
        if (
            definition.key in known
            or definition.trigger != "command"
            or not _has_living_condition(definition.condition)
        ):
            continue
        if not _condition_matches(
            session,
            world_service,
            definition,
            known_discoveries=known,
        ):
            continue

        for raw_target in definition.targets:
            target = _normalize(raw_target)
            if (
                not target
                or target in _GENERIC_TELL_TARGETS
                or len(target) > 48
                or target.startswith("old business")
            ):
                continue
            return f"The {target} catches your attention under the current conditions."
    return None


def discovery_catalog_problems(
    world_service,
    definitions: Iterable[DiscoveryDefinition],
) -> tuple[str, ...]:
    definitions = tuple(definitions)
    problems: list[str] = []
    keys = [definition.key for definition in definitions]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    problems.extend(f"duplicate discovery key: {key}" for key in duplicates)

    key_set = set(keys)
    for definition in definitions:
        if not definition.key or not definition.text.strip():
            problems.append(f"{definition.key or '<missing>'}: missing key or text")
        if definition.trigger not in {"command", "enter"}:
            problems.append(f"{definition.key}: unsupported trigger {definition.trigger!r}")
        if definition.trigger == "command" and not definition.verbs:
            problems.append(f"{definition.key}: command discovery has no verbs")
        for room_key in definition.condition.room_keys:
            if world_service.scene(room_key) is None:
                problems.append(f"{definition.key}: unknown room {room_key}")
        for required in definition.condition.required_discoveries:
            if required not in key_set:
                problems.append(f"{definition.key}: unknown prerequisite {required}")
    return tuple(problems)


def validate_discovery_catalog(
    world_service,
    definitions: Iterable[DiscoveryDefinition],
    *,
    minimum_count: int = 350,
) -> int:
    definitions = tuple(definitions)
    problems = list(discovery_catalog_problems(world_service, definitions))
    if len(definitions) < int(minimum_count):
        problems.append(
            f"catalog has {len(definitions)} discoveries; expected at least {int(minimum_count)}"
        )
    if problems:
        raise RuntimeError(
            "Hidden discovery catalog audit failed:\n- " + "\n- ".join(problems)
        )
    return len(definitions)


async def _delegate_prompt(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    old_prompt = session.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = old_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_discovery_runtime(player_session_class, world_service) -> None:
    """Install the hidden-discovery layer without exposing a completion counter.

    The runtime intentionally provides no player-facing DISCOVERIES command.
    Secrets are learned by interacting with Astralis, not by filling a checklist.
    """

    if getattr(player_session_class, "_discovery_runtime_installed", False):
        return

    from mud.discovery_catalog import build_discovery_catalog

    definitions = tuple(build_discovery_catalog(world_service))
    validate_discovery_catalog(world_service, definitions)
    registry = DiscoveryRegistry(definitions)
    _WORLD_REGISTRIES[id(world_service)] = registry

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if getattr(self, "character", None) is None:
            return
        self._discovery_world_service = world_service
        ensure_discovery_schema(self.database)
        await attempt_entry_discovery(self, world_service, registry=registry)

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        before_room = str(getattr(self.character, "current_room", "") or "")
        result = await attempt_discovery_command(
            self,
            world_service,
            command,
            registry=registry,
        )
        if result.handled:
            return

        await _delegate_prompt(self, previous_prompt, command)

        if getattr(self, "character", None) is None:
            return
        after_room = str(getattr(self.character, "current_room", "") or "")
        if after_room and after_room != before_room:
            await attempt_entry_discovery(self, world_service, registry=registry)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._discovery_runtime_installed = True
    player_session_class._discovery_catalog_size = len(definitions)
