from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Mapping

import mud.world as legacy_world
from mud.world import (
    HUMAN_START_ROOM_KEY,
    ROOMS_BY_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
    SPOREKIN_MEMORY_PATH_ROOM_KEY,
    RoomDefinition as LegacyRoomDefinition,
)


class PersistenceScope(str, Enum):
    """Where mutable room state belongs.

    TEMPORARY resets with the process, WORLD belongs to the shared world and can
    later be serialized as a world snapshot, and CHARACTER is persisted through
    the character flag system supplied in PlayerRoomContext.
    """

    TEMPORARY = "temporary"
    WORLD = "world"
    CHARACTER = "character"


@dataclass(frozen=True, slots=True)
class ViewCondition:
    races: tuple[str, ...] = ()
    forbidden_races: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    required_flags: tuple[str, ...] = ()
    forbidden_flags: tuple[str, ...] = ()
    time_buckets: tuple[str, ...] = ()
    weather: tuple[str, ...] = ()
    min_level: int = 0
    required_flags_for_races: tuple[str, ...] = ()
    min_level_for_races: tuple[str, ...] = ()

    def matches(self, context: "PlayerRoomContext") -> bool:
        if self.races and context.race_key not in self.races:
            return False
        if self.forbidden_races and context.race_key in self.forbidden_races:
            return False
        if self.classes and context.class_key not in self.classes:
            return False
        flags_apply = (
            not self.required_flags_for_races
            or context.race_key in self.required_flags_for_races
        )
        if (
            self.required_flags
            and flags_apply
            and not set(self.required_flags).issubset(context.character_flags)
        ):
            return False
        if self.forbidden_flags and set(self.forbidden_flags).intersection(context.character_flags):
            return False
        if self.time_buckets and context.time_bucket not in self.time_buckets:
            return False
        if self.weather and context.weather not in self.weather:
            return False
        min_level_applies = (
            not self.min_level_for_races
            or context.race_key in self.min_level_for_races
        )
        if min_level_applies and context.level < self.min_level:
            return False
        return True


@dataclass(frozen=True, slots=True)
class DescriptionLayer:
    key: str
    text: str
    priority: int = 100
    condition: ViewCondition = field(default_factory=ViewCondition)


@dataclass(frozen=True, slots=True)
class ExitDefinition:
    direction: str
    destination_key: str
    name: str = ""
    aliases: tuple[str, ...] = ()
    travel_text: str = ""
    failure_text: str = "You cannot go that way."
    condition: ViewCondition = field(default_factory=ViewCondition)
    hidden_when_unavailable: bool = True
    door_key: str | None = None
    one_way: bool = False

    def matches_direction(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized == self.direction or normalized in self.aliases


_FEATURE_STOPWORDS = {"a", "an", "and", "at", "in", "of", "on", "the", "to"}
_FEATURE_PREPOSITIONS = ("at ", "to ", "on ", "in ")


def _normalize_feature_target(value: str) -> str:
    normalized = " ".join((value or "").strip().lower().replace("_", " ").split())
    for prefix in _FEATURE_PREPOSITIONS:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    return normalized


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    key: str
    name: str
    aliases: tuple[str, ...] = ()
    summary: str = ""
    examine_text: str = ""
    search_text: str = ""
    touch_text: str = ""
    listen_text: str = ""
    condition: ViewCondition = field(default_factory=ViewCondition)

    def _match_phrases(self) -> tuple[str, ...]:
        values = (
            self.key.replace("_", " "),
            self.name,
            *self.aliases,
        )
        return tuple(
            normalized
            for value in values
            if (normalized := _normalize_feature_target(value))
        )

    def matches(self, value: str) -> bool:
        normalized = _normalize_feature_target(value)
        return bool(normalized and normalized in set(self._match_phrases()))

    def matches_shorthand(self, value: str) -> bool:
        """Match natural shorthand; caller must still enforce uniqueness.

        Exact aliases remain authoritative. Shorthand deliberately accepts a
        substantial whole word such as CHAPEL from "Chapel of the Small Saint"
        and phrase prefixes such as CROOKED BELL. Generic stopwords and tiny
        fragments never qualify on their own.
        """
        normalized = _normalize_feature_target(value)
        if not normalized:
            return False
        if self.matches(normalized):
            return True

        query_words = tuple(normalized.split())
        if not query_words:
            return False
        if len(query_words) == 1:
            token = query_words[0]
            if token in _FEATURE_STOPWORDS or len(token) < 3:
                return False
            return any(token in phrase.split() for phrase in self._match_phrases())

        for phrase in self._match_phrases():
            if phrase.startswith(normalized):
                return True
            phrase_words = phrase.split()
            width = len(query_words)
            if any(
                tuple(phrase_words[index:index + width]) == query_words
                for index in range(max(0, len(phrase_words) - width + 1))
            ):
                return True
        return False


@dataclass(frozen=True, slots=True)
class RoomSceneDefinition:
    key: str
    name: str
    region_key: str
    base_description: str
    exits: tuple[ExitDefinition, ...]
    features: tuple[FeatureDefinition, ...] = ()
    description_layers: tuple[DescriptionLayer, ...] = ()
    npc_keys: tuple[str, ...] = ()
    enemy_keys: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class DoorState:
    open: bool = True
    locked: bool = False


@dataclass(slots=True)
class RoomStateStore:
    """Mutable shared/temporary world state, separated from authored content."""

    world_flags: dict[str, set[str]] = field(default_factory=dict)
    temporary_flags: dict[str, set[str]] = field(default_factory=dict)
    doors: dict[str, DoorState] = field(default_factory=dict)
    region_weather: dict[str, str] = field(default_factory=dict)
    # JSON-safe persistent regional ecology payloads. Ecology owns the schema;
    # RoomStateStore only carries the shared world state across restarts.
    region_ecology: dict[str, dict[str, float | int]] = field(default_factory=dict)

    def flags_for(self, room_key: str, scope: PersistenceScope) -> frozenset[str]:
        source = self.world_flags if scope is PersistenceScope.WORLD else self.temporary_flags
        return frozenset(source.get(room_key, set()))

    def set_flag(self, room_key: str, flag_key: str, enabled: bool, scope: PersistenceScope) -> None:
        if scope is PersistenceScope.CHARACTER:
            raise ValueError("Character-scoped state is persisted through character flags, not RoomStateStore")
        source = self.world_flags if scope is PersistenceScope.WORLD else self.temporary_flags
        bucket = source.setdefault(room_key, set())
        if enabled:
            bucket.add(flag_key)
        else:
            bucket.discard(flag_key)

    def door_state(self, door_key: str) -> DoorState:
        return self.doors.setdefault(door_key, DoorState())

    def set_door(self, door_key: str, *, open: bool | None = None, locked: bool | None = None) -> DoorState:
        state = self.door_state(door_key)
        if open is not None:
            state.open = open
        if locked is not None:
            state.locked = locked
        return state

    def weather_for(self, region_key: str) -> str:
        return self.region_weather.get(region_key, "clear")

    def set_weather(self, region_key: str, weather: str) -> None:
        self.region_weather[region_key] = weather.strip().lower() or "clear"

    def snapshot_world_state(self) -> dict[str, object]:
        """Return only state intended to survive a future world-state save."""
        return {
            "world_flags": {key: sorted(values) for key, values in self.world_flags.items()},
            "doors": {
                key: {"open": state.open, "locked": state.locked}
                for key, state in self.doors.items()
            },
            "region_weather": dict(self.region_weather),
            "region_ecology": {
                region_key: dict(values)
                for region_key, values in self.region_ecology.items()
            },
        }


@dataclass(frozen=True, slots=True)
class PlayerRoomContext:
    character_id: int
    race_key: str
    class_key: str
    level: int
    character_flags: frozenset[str] = frozenset()
    hour: int = 12
    weather: str = "clear"

    @property
    def time_bucket(self) -> str:
        if 5 <= self.hour < 8:
            return "dawn"
        if 8 <= self.hour < 18:
            return "day"
        if 18 <= self.hour < 21:
            return "dusk"
        return "night"


@dataclass(frozen=True, slots=True)
class VisibleExit:
    direction: str
    name: str
    destination_key: str


@dataclass(frozen=True, slots=True)
class RoomView:
    key: str
    name: str
    description: str
    exits: tuple[VisibleExit, ...]
    features: tuple[FeatureDefinition, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExitResolution:
    allowed: bool
    exit: ExitDefinition | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class InteractionResult:
    handled: bool
    text: str = ""
    feature_key: str | None = None


@dataclass(frozen=True, slots=True)
class RoomAugmentation:
    """Extra authored behavior layered over an existing legacy room."""

    exit_overrides: tuple[ExitDefinition, ...] = ()
    extra_exits: tuple[ExitDefinition, ...] = ()
    features: tuple[FeatureDefinition, ...] = ()
    description_layers: tuple[DescriptionLayer, ...] = ()


def _demon_gate_augmentation() -> RoomAugmentation:
    return RoomAugmentation(
        exit_overrides=(
            ExitDefinition(
                direction="north",
                destination_key="human_ashen_way",
                name="Ashen Way",
                travel_text="You pass beneath the horned arch and climb into Ashen Way.",
            ),
            ExitDefinition(
                direction="south",
                destination_key="human_outer_drill_road",
                name="Outer Drill Road",
                travel_text="You leave the gate's shadow and follow the black wall toward the drill road.",
                door_key="demon_gate_outer_portal",
                failure_text="The great outer portal is closed; the road beyond is unreachable.",
            ),
        ),
        features=(
            FeatureDefinition(
                key="wrought_iron_gates",
                name="Wrought-Iron Gates",
                aliases=("gate", "gates", "iron gate", "demon gate"),
                summary="the enormous horn-worked wrought-iron gates",
                examine_text=(
                    "The gates are less defensive ornament than civic declaration: black iron ribs climb overhead into hooked points, "
                    "while old hammer marks remain visible beneath generations of oil and soot. The imagery is deliberately demonic, not accidental."
                ),
                search_text=(
                    "You find maintenance stamps, old repair welds, and a tiny maker's seal hidden near the lowest hinge. Nothing suggests a secret mechanism."
                ),
                touch_text="The iron is cool, slick with protective oil, and faintly rough where age has pitted the surface.",
            ),
            FeatureDefinition(
                key="demonic_reliefs",
                name="Demonic Reliefs",
                aliases=("reliefs", "faces", "carvings", "demonic faces", "horned faces"),
                summary="the horned stone reliefs worked into the arch",
                examine_text=(
                    "The faces are not depictions of one creature or god. Each is different: stern, beautiful, grotesque, serene. "
                    "Human masons have spent centuries turning an old insult into heraldry, until 'Demon' became an aesthetic language of its own."
                ),
                touch_text="Your fingers trace a polished horn where thousands of other hands have done the same.",
            ),
            FeatureDefinition(
                key="cathedral_skyline",
                name="Cathedral Skyline",
                aliases=("cathedral", "spires", "skyline", "great cathedral"),
                summary="the distant cathedral spires above the city",
                examine_text=(
                    "Beyond the roofs, the Grand Cathedral dominates the city by design. Flying buttresses and needlelike towers make it look almost skeletal against the sky."
                ),
                listen_text="A slow cathedral bell rolls over the rooftops, followed by the thinner answer of smaller bells deeper in the city.",
            ),
            FeatureDefinition(
                key="gate_watch",
                name="Gate Watch",
                aliases=("guards", "watch", "guardhouse", "watchtower", "watchtowers"),
                summary="the black-uniformed gate watch and iron watchtowers",
                examine_text=(
                    "The gate watch wears dark practical uniforms beneath ceremonial horn-shaped badges. Their attention is on arrivals, wagons, and the road-not on posing for visitors."
                ),
            ),
        ),
        description_layers=(
            DescriptionLayer(
                key="human_familiarity",
                priority=30,
                condition=ViewCondition(races=("human",)),
                text=(
                    "To you, the horns and severe faces do not read as monstrous. They are as ordinary and civic as another kingdom's lions or eagles."
                ),
            ),
            DescriptionLayer(
                key="outsider_reading",
                priority=30,
                condition=ViewCondition(forbidden_races=("human",)),
                text=(
                    "Seen from outside Human culture, the sheer enthusiasm of the demonic imagery is difficult to mistake: this city chose the name others gave its people and made it monumental."
                ),
            ),
            DescriptionLayer(
                key="night_gate",
                priority=50,
                condition=ViewCondition(time_buckets=("night",)),
                text=(
                    "Night turns the gate theatrical. Braziers burn beneath the arch, throwing long horn-shaped shadows across the road while the upper watchtowers vanish into darkness."
                ),
            ),
            DescriptionLayer(
                key="dusk_gate",
                priority=50,
                condition=ViewCondition(time_buckets=("dusk",)),
                text=(
                    "The last daylight catches the cathedral spires while the first gate braziers are being lit, leaving the city briefly divided between violet sky and orange fire."
                ),
            ),
            DescriptionLayer(
                key="rain_gate",
                priority=60,
                condition=ViewCondition(weather=("rain",)),
                text=(
                    "Rain beads on black iron and turns the cobbles mirror-dark, doubling every torch flame beneath the gate."
                ),
            ),
        ),
    )


def default_room_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HUMAN_START_ROOM_KEY: _demon_gate_augmentation(),
        SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="north",
                    destination_key=SPOREKIN_MEMORY_PATH_ROOM_KEY,
                    name="Memory Path",
                    travel_text="You follow the spore-sigil north onto the newly remembered path.",
                    condition=ViewCondition(required_flags=("sporekin_forgotten_pulse_solved",)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="remembered_path",
                    priority=70,
                    condition=ViewCondition(required_flags=("sporekin_forgotten_pulse_solved",)),
                    text="A faint spore-shaped sigil hangs above the roots, pointing north toward a path that was invisible before the old pulse was restored.",
                ),
            ),
        ),
    }


class WorldService:
    """Single interface between sessions and authored/mutable room data."""

    def __init__(
        self,
        rooms: Mapping[str, LegacyRoomDefinition] | None = None,
        *,
        state: RoomStateStore | None = None,
        augmentations: Mapping[str, RoomAugmentation] | None = None,
    ) -> None:
        self.legacy_rooms = dict(rooms or ROOMS_BY_KEY)
        self.state = state or RoomStateStore()
        self.augmentations = dict(augmentations or default_room_augmentations())
        self._scene_cache: dict[str, RoomSceneDefinition] = {}
        # Final production assembly can normalize physical directions without
        # throwing away richer authored exit metadata (gates, conditions, text).
        self._topology_exits: dict[str, tuple[ExitDefinition, ...]] = {}

    def scene(self, room_key: str) -> RoomSceneDefinition | None:
        cached = self._scene_cache.get(room_key)
        if cached is not None:
            return cached
        legacy = self.legacy_rooms.get(room_key)
        if legacy is None:
            return None

        augmentation = self.augmentations.get(room_key, RoomAugmentation())
        override_by_direction = {exit_def.direction: exit_def for exit_def in augmentation.exit_overrides}

        # A room can be expanded in two layers: its legacy RoomDefinition and a
        # richer RoomAugmentation. Several later content installers correctly
        # patch a newly-authored route into the legacy room so movement works
        # everywhere, while also supplying the same route as an extra exit so it
        # has authored travel text/conditions. Treat those as one logical exit.
        #
        # Direction is the player's command surface, so there may never be two
        # simultaneously-defined routes for the same direction. Identical
        # legacy+augmentation routes collapse to the richer augmentation entry;
        # different destinations are an authoring conflict and fail loudly.
        exits: list[ExitDefinition] = []
        exit_index_by_direction: dict[str, int] = {}

        def add_exit(exit_def: ExitDefinition, *, source: str, prefer_new: bool = True) -> None:
            direction = exit_def.direction.strip().lower()
            existing_index = exit_index_by_direction.get(direction)
            if existing_index is None:
                exit_index_by_direction[direction] = len(exits)
                exits.append(exit_def)
                return

            existing = exits[existing_index]
            if existing.destination_key != exit_def.destination_key:
                raise RuntimeError(
                    "Ambiguous room exit definition: "
                    f"{room_key} has {direction!r} pointing to both "
                    f"{existing.destination_key!r} and {exit_def.destination_key!r} "
                    f"(latest source: {source})."
                )
            if prefer_new:
                exits[existing_index] = exit_def

        for direction, destination_key in legacy.exits.items():
            override = override_by_direction.get(direction)
            if override is not None:
                add_exit(override, source="exit override")
                continue
            destination = self.legacy_rooms.get(destination_key)
            add_exit(
                ExitDefinition(
                    direction=direction,
                    destination_key=destination_key,
                    name=destination.name if destination else destination_key,
                ),
                source="legacy room",
            )

        # An explicit override is authoritative if a later extra exit repeats
        # the same direction/destination; otherwise the extra exit is preferred
        # over a plain legacy definition because it usually carries travel text,
        # visibility conditions, door state, or aliases.
        for exit_def in augmentation.extra_exits:
            add_exit(
                exit_def,
                source="extra exit",
                prefer_new=exit_def.direction not in override_by_direction,
            )

        topology_exits = self._topology_exits.get(room_key)
        if topology_exits is not None:
            exits = list(topology_exits)

        scene = RoomSceneDefinition(
            key=legacy.key,
            name=legacy.name,
            region_key=legacy.region_key,
            base_description=legacy.description,
            exits=tuple(exits),
            features=augmentation.features,
            description_layers=augmentation.description_layers,
            npc_keys=legacy.npc_keys,
            enemy_keys=legacy.enemy_keys,
            tags=legacy.tags,
        )
        self._scene_cache[room_key] = scene
        return scene

    def audit_exit_sources(self) -> tuple[str, ...]:
        """Report redundant or conflicting raw exit definitions across the world.

        This inspects the authored sources before scene canonicalization. It is
        useful for production audits because a clean rendered scene should not
        depend on players happening to avoid duplicated content layers.
        """

        problems: list[str] = []
        for room_key, legacy in sorted(self.legacy_rooms.items()):
            augmentation = self.augmentations.get(room_key, RoomAugmentation())
            by_direction: dict[str, tuple[str, str]] = {}

            for direction, destination_key in legacy.exits.items():
                normalized = direction.strip().lower()
                by_direction[normalized] = (destination_key, "legacy")

            for exit_def in augmentation.exit_overrides:
                normalized = exit_def.direction.strip().lower()
                previous = by_direction.get(normalized)
                if previous is not None and previous[0] != exit_def.destination_key:
                    problems.append(
                        f"CONFLICT {room_key} {normalized}: {previous[0]} ({previous[1]}) vs "
                        f"{exit_def.destination_key} (override)"
                    )
                by_direction[normalized] = (exit_def.destination_key, "override")

            for exit_def in augmentation.extra_exits:
                normalized = exit_def.direction.strip().lower()
                previous = by_direction.get(normalized)
                if previous is None:
                    by_direction[normalized] = (exit_def.destination_key, "extra")
                    continue
                kind = "REDUNDANT" if previous[0] == exit_def.destination_key else "CONFLICT"
                problems.append(
                    f"{kind} {room_key} {normalized}: {previous[0]} ({previous[1]}) vs "
                    f"{exit_def.destination_key} (extra)"
                )
        return tuple(problems)

    def normalize_reciprocal_topology(self) -> int:
        """Make every ordinary physical connection use a true opposite return.

        Older content was authored in many independent passes, so several rooms
        accumulated locally sensible direction labels that did not agree with
        the room on the far side.  Rather than special-casing one region, build
        one final physical graph after all content installers run.

        Already-correct reciprocal links are kept exactly as authored.  Only
        inconsistent links are reoriented, preferring an existing direction
        whenever its opposite slot is actually free.  If a busy junction has no
        cardinal slot left, diagonals are preferred before vertical or IN/OUT.
        Explicit one-way exits and non-spatial command exits are never touched.
        """

        opposites = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "northeast": "southwest",
            "southwest": "northeast",
            "northwest": "southeast",
            "southeast": "northwest",
            "up": "down",
            "down": "up",
            "in": "out",
            "out": "in",
        }
        preference = (
            "north", "south", "east", "west",
            "northeast", "northwest", "southeast", "southwest",
            "up", "down", "in", "out",
        )

        # Always audit the authored/augmented graph, never a previous normalized
        # snapshot. This keeps repeated production imports deterministic.
        self._topology_exits.clear()
        self._scene_cache.clear()
        raw_scenes = {
            room_key: scene
            for room_key in sorted(self.legacy_rooms)
            if (scene := self.scene(room_key)) is not None
        }

        # Pair physical exits into undirected edges. A side may be absent, which
        # is exactly the missing-return case this pass repairs.
        edges: dict[tuple[str, str], dict[str, ExitDefinition]] = {}
        fixed_by_room: dict[str, list[ExitDefinition]] = {
            room_key: [] for room_key in raw_scenes
        }
        used: dict[str, set[str]] = {room_key: set() for room_key in raw_scenes}

        for room_key, scene in raw_scenes.items():
            for exit_def in scene.exits:
                direction = exit_def.direction.strip().lower()
                if (
                    direction not in opposites
                    or exit_def.one_way
                    or exit_def.destination_key not in raw_scenes
                ):
                    fixed_by_room[room_key].append(exit_def)
                    used[room_key].add(direction)
                    continue
                pair = tuple(sorted((room_key, exit_def.destination_key)))
                edges.setdefault(pair, {})[room_key] = exit_def

        assignments: dict[tuple[str, str], tuple[str, str]] = {}
        pending: list[tuple[str, str]] = []

        # Keep links that are already genuinely reciprocal. They form the stable
        # backbone of the authored geography; inconsistent additions route around
        # them instead of silently moving established roads.
        for pair, sides in sorted(edges.items()):
            a, b = pair
            a_exit = sides.get(a)
            b_exit = sides.get(b)
            if a_exit is not None and b_exit is not None:
                a_dir = a_exit.direction.strip().lower()
                b_dir = b_exit.direction.strip().lower()
                if opposites.get(a_dir) == b_dir:
                    assignments[pair] = (a_dir, b_dir)
                    used[a].add(a_dir)
                    used[b].add(b_dir)
                    continue
            pending.append(pair)

        def candidates(pair: tuple[str, str]) -> list[tuple[int, str, str]]:
            a, b = pair
            sides = edges[pair]
            a_existing = sides.get(a)
            b_existing = sides.get(b)
            a_old = a_existing.direction.strip().lower() if a_existing else None
            b_old = b_existing.direction.strip().lower() if b_existing else None
            rows: list[tuple[int, str, str]] = []
            for rank, a_dir in enumerate(preference):
                b_dir = opposites[a_dir]
                if a_dir in used[a] or b_dir in used[b]:
                    continue
                changes = int(a_old is not None and a_old != a_dir)
                changes += int(b_old is not None and b_old != b_dir)
                # Preserve authored directions first. Within equal-change
                # options, prefer cardinal, then diagonal, then vertical/IN-OUT.
                score = changes * 100 + rank
                rows.append((score, a_dir, b_dir))
            rows.sort()
            return rows

        # Constraint search with minimum-remaining-values selection. In practice
        # Astralis rooms have low degree, but backtracking prevents an early busy
        # junction from consuming the only sensible slot of a later edge.
        def solve(remaining: list[tuple[str, str]]) -> bool:
            if not remaining:
                return True
            choices = [(len(candidates(pair)), pair) for pair in remaining]
            count, pair = min(choices, key=lambda row: (row[0], row[1]))
            if count == 0:
                return False
            next_remaining = [value for value in remaining if value != pair]
            a, b = pair
            for _score, a_dir, b_dir in candidates(pair):
                assignments[pair] = (a_dir, b_dir)
                used[a].add(a_dir)
                used[b].add(b_dir)
                if solve(next_remaining):
                    return True
                used[a].discard(a_dir)
                used[b].discard(b_dir)
                assignments.pop(pair, None)
            return False

        if not solve(pending):
            unresolved = ", ".join(f"{a}<->{b}" for a, b in pending)
            raise RuntimeError(
                "Unable to assign reciprocal directions to the assembled world: "
                + unresolved
            )

        rebuilt: dict[str, list[ExitDefinition]] = {
            room_key: list(fixed_by_room[room_key]) for room_key in raw_scenes
        }
        original_pairs_by_room: dict[str, set[tuple[str, str]]] = {
            room_key: set() for room_key in raw_scenes
        }

        # Reuse each side's authored ExitDefinition so conditions, door keys,
        # aliases, failure text, and travel prose survive a direction repair.
        for pair, (a_dir, b_dir) in sorted(assignments.items()):
            a, b = pair
            sides = edges[pair]
            a_proto = sides.get(a)
            b_proto = sides.get(b)
            if a_proto is None:
                source = b_proto
                a_proto = ExitDefinition(
                    direction=a_dir,
                    destination_key=b,
                    name=raw_scenes[b].name,
                    failure_text=source.failure_text if source else "You cannot go that way.",
                    condition=source.condition if source else ViewCondition(),
                    hidden_when_unavailable=source.hidden_when_unavailable if source else True,
                    door_key=source.door_key if source else None,
                )
            else:
                original_pairs_by_room[a].add(pair)
            if b_proto is None:
                source = a_proto
                b_proto = ExitDefinition(
                    direction=b_dir,
                    destination_key=a,
                    name=raw_scenes[a].name,
                    failure_text=source.failure_text if source else "You cannot go that way.",
                    condition=source.condition if source else ViewCondition(),
                    hidden_when_unavailable=source.hidden_when_unavailable if source else True,
                    door_key=source.door_key if source else None,
                )
            else:
                original_pairs_by_room[b].add(pair)

            rebuilt[a].append(replace(a_proto, direction=a_dir, destination_key=b))
            rebuilt[b].append(replace(b_proto, direction=b_dir, destination_key=a))

        self._topology_exits = {
            room_key: tuple(
                sorted(
                    exits,
                    key=lambda value: (
                        preference.index(value.direction.strip().lower())
                        if value.direction.strip().lower() in preference
                        else len(preference),
                        value.direction,
                        value.destination_key,
                    ),
                )
            )
            for room_key, exits in rebuilt.items()
        }

        # The advanced WorldService is the presentation/condition authority, but
        # the oldest movement layer still performs the final transition through
        # mud.world.ROOMS_BY_KEY. Keep that legacy graph synchronized with the
        # normalized directions so LOOK/EXITS and the actual movement command can
        # never disagree.
        normalized_rooms: dict[str, LegacyRoomDefinition] = {}
        for room_key, exits in self._topology_exits.items():
            legacy = self.legacy_rooms[room_key]
            normalized = replace(
                legacy,
                exits={
                    exit_def.direction.strip().lower(): exit_def.destination_key
                    for exit_def in exits
                },
            )
            normalized_rooms[room_key] = normalized
            self.legacy_rooms[room_key] = normalized
            if room_key in legacy_world.ROOMS_BY_KEY:
                legacy_world.ROOMS_BY_KEY[room_key] = normalized

        if normalized_rooms:
            legacy_world.ROOMS = tuple(
                normalized_rooms.get(room.key, room) for room in legacy_world.ROOMS
            )

        # Raw augmentation audits should describe the same topology too. Preserve
        # all gating/travel metadata and change only the spatial command label.
        for room_key, augmentation in tuple(self.augmentations.items()):
            def normalized_augmented(exit_def: ExitDefinition) -> ExitDefinition:
                direction = exit_def.direction.strip().lower()
                if (
                    direction not in opposites
                    or exit_def.one_way
                    or exit_def.destination_key not in raw_scenes
                ):
                    return exit_def
                pair = tuple(sorted((room_key, exit_def.destination_key)))
                assigned = assignments.get(pair)
                if assigned is None:
                    return exit_def
                new_direction = assigned[0] if room_key == pair[0] else assigned[1]
                return replace(exit_def, direction=new_direction)

            self.augmentations[room_key] = replace(
                augmentation,
                exit_overrides=tuple(
                    normalized_augmented(exit_def)
                    for exit_def in augmentation.exit_overrides
                ),
                extra_exits=tuple(
                    normalized_augmented(exit_def)
                    for exit_def in augmentation.extra_exits
                ),
            )

        self._scene_cache.clear()

        changed = 0
        for pair, sides in edges.items():
            a, b = pair
            assigned_a, assigned_b = assignments[pair]
            old_a = sides.get(a)
            old_b = sides.get(b)
            if old_a is None or old_a.direction.strip().lower() != assigned_a:
                changed += 1
            if old_b is None or old_b.direction.strip().lower() != assigned_b:
                changed += 1
        return changed

    def audit_reciprocal_exits(self) -> tuple[str, ...]:
        """Report physical exits whose reverse direction does not lead back.

        Cardinal/diagonal/vertical room movement is spatial grammar: if EAST
        takes a player from A to B, WEST from B must return to A unless the
        authored exit is explicitly marked one_way.  This audit runs against
        fully canonicalized room scenes, so late runtime augmentations and
        overrides are checked too.
        """

        opposites = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "northeast": "southwest",
            "southwest": "northeast",
            "northwest": "southeast",
            "southeast": "northwest",
            "up": "down",
            "down": "up",
            "in": "out",
            "out": "in",
        }
        problems: list[str] = []

        for room_key in sorted(self.legacy_rooms):
            scene = self.scene(room_key)
            if scene is None:
                continue
            for exit_def in scene.exits:
                direction = exit_def.direction.strip().lower()
                reverse_direction = opposites.get(direction)
                if reverse_direction is None or exit_def.one_way:
                    continue

                destination = self.scene(exit_def.destination_key)
                if destination is None:
                    continue

                reverse = next(
                    (
                        candidate
                        for candidate in destination.exits
                        if candidate.direction.strip().lower() == reverse_direction
                    ),
                    None,
                )
                if reverse is None:
                    problems.append(
                        f"{room_key} {direction} -> {exit_def.destination_key}: "
                        f"missing {reverse_direction} return exit"
                    )
                    continue
                if reverse.destination_key != room_key:
                    problems.append(
                        f"{room_key} {direction} -> {exit_def.destination_key}: "
                        f"{reverse_direction} returns to {reverse.destination_key}, not {room_key}"
                    )

        return tuple(problems)

    def validate_exit_integrity(self) -> None:
        """Fail fast on ambiguous, duplicate, or spatially inconsistent exits."""

        conflicts = [row for row in self.audit_exit_sources() if row.startswith("CONFLICT ")]
        if conflicts:
            raise RuntimeError("World exit integrity failed:\n- " + "\n- ".join(conflicts))

        duplicates: list[str] = []
        for room_key in sorted(self.legacy_rooms):
            scene = self.scene(room_key)
            if scene is None:
                continue
            seen: set[str] = set()
            for exit_def in scene.exits:
                direction = exit_def.direction.strip().lower()
                if direction in seen:
                    duplicates.append(f"{room_key}: duplicate {direction}")
                seen.add(direction)
        if duplicates:
            raise RuntimeError("World scene exit uniqueness failed:\n- " + "\n- ".join(duplicates))

        reciprocal = self.audit_reciprocal_exits()
        if reciprocal:
            raise RuntimeError(
                "World reciprocal exit integrity failed:\n- " + "\n- ".join(reciprocal)
            )


    def context_with_world(self, context: PlayerRoomContext, room_key: str) -> PlayerRoomContext:
        scene = self.scene(room_key)
        if scene is None:
            return context
        return PlayerRoomContext(
            character_id=context.character_id,
            race_key=context.race_key,
            class_key=context.class_key,
            level=context.level,
            character_flags=context.character_flags,
            hour=context.hour,
            weather=self.state.weather_for(scene.region_key),
        )

    def build_view(self, room_key: str, context: PlayerRoomContext) -> RoomView | None:
        scene = self.scene(room_key)
        if scene is None:
            return None
        context = self.context_with_world(context, room_key)
        paragraphs = [scene.base_description]
        for layer in sorted(scene.description_layers, key=lambda value: value.priority):
            if layer.condition.matches(context):
                paragraphs.append(layer.text)

        visible_exits: list[VisibleExit] = []
        for exit_def in scene.exits:
            if not exit_def.condition.matches(context):
                if exit_def.hidden_when_unavailable:
                    continue
                visible_exits.append(
                    VisibleExit(exit_def.direction, exit_def.name or exit_def.destination_key, exit_def.destination_key)
                )
                continue
            if exit_def.door_key:
                door = self.state.door_state(exit_def.door_key)
                if door.locked or not door.open:
                    # A known doorway remains visible even when traversal is blocked.
                    visible_exits.append(
                        VisibleExit(exit_def.direction, exit_def.name or exit_def.destination_key, exit_def.destination_key)
                    )
                    continue
            visible_exits.append(
                VisibleExit(exit_def.direction, exit_def.name or exit_def.destination_key, exit_def.destination_key)
            )

        features = tuple(feature for feature in scene.features if feature.condition.matches(context))
        return RoomView(
            key=scene.key,
            name=scene.name,
            description="\n\n".join(paragraphs),
            exits=tuple(visible_exits),
            features=features,
            tags=scene.tags,
        )

    def resolve_exit(self, room_key: str, direction: str, context: PlayerRoomContext) -> ExitResolution:
        scene = self.scene(room_key)
        if scene is None:
            return ExitResolution(False, message="There are no authored exits from this area yet.")
        context = self.context_with_world(context, room_key)
        matched = next((exit_def for exit_def in scene.exits if exit_def.matches_direction(direction)), None)
        if matched is None:
            return ExitResolution(False, message="You cannot go that way.")
        if not matched.condition.matches(context):
            return ExitResolution(False, message=matched.failure_text)
        if matched.door_key:
            door = self.state.door_state(matched.door_key)
            if door.locked:
                return ExitResolution(False, matched, "That way is locked.")
            if not door.open:
                return ExitResolution(False, matched, matched.failure_text or "That way is closed.")
        return ExitResolution(True, matched)

    def interact(self, room_key: str, verb: str, target: str, context: PlayerRoomContext) -> InteractionResult:
        scene = self.scene(room_key)
        if scene is None:
            return InteractionResult(False)
        context = self.context_with_world(context, room_key)
        visible_features = tuple(
            value for value in scene.features
            if value.condition.matches(context)
        )

        exact = tuple(value for value in visible_features if value.matches(target))
        if len(exact) == 1:
            feature = exact[0]
        elif len(exact) > 1:
            names = ", ".join(value.name for value in exact)
            return InteractionResult(True, text=f"Be more specific: {names}.")
        else:
            shorthand = tuple(
                value for value in visible_features
                if value.matches_shorthand(target)
            )
            if len(shorthand) == 1:
                feature = shorthand[0]
            elif len(shorthand) > 1:
                names = ", ".join(value.name for value in shorthand)
                return InteractionResult(
                    True,
                    text=f"That shorthand could mean more than one notable feature: {names}. Be more specific.",
                )
            else:
                return InteractionResult(False)

        verb = verb.strip().lower()
        text = ""
        if verb in {"look", "examine"}:
            text = feature.examine_text or feature.summary
        elif verb == "search":
            text = feature.search_text or feature.examine_text or feature.summary
        elif verb == "touch":
            text = feature.touch_text
        elif verb == "listen":
            text = feature.listen_text

        if not text:
            text = f"You find nothing noteworthy by trying to {verb} {feature.name.lower()}."
        return InteractionResult(True, text=text, feature_key=feature.key)

    def visible_feature_summaries(self, room_key: str, context: PlayerRoomContext) -> tuple[str, ...]:
        view = self.build_view(room_key, context)
        if view is None:
            return ()
        return tuple(feature.name for feature in view.features)
