from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

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

    def matches(self, context: "PlayerRoomContext") -> bool:
        if self.races and context.race_key not in self.races:
            return False
        if self.forbidden_races and context.race_key in self.forbidden_races:
            return False
        if self.classes and context.class_key not in self.classes:
            return False
        if self.required_flags and not set(self.required_flags).issubset(context.character_flags):
            return False
        if self.forbidden_flags and set(self.forbidden_flags).intersection(context.character_flags):
            return False
        if self.time_buckets and context.time_bucket not in self.time_buckets:
            return False
        if self.weather and context.weather not in self.weather:
            return False
        if context.level < self.min_level:
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

    def matches(self, value: str) -> bool:
        normalized = value.strip().lower()
        names = {self.key.replace("_", " "), self.name.lower(), *(alias.lower() for alias in self.aliases)}
        return normalized in names


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
                    "The gate watch wears dark practical uniforms beneath ceremonial horn-shaped badges. Their attention is on arrivals, wagons, and the road—not on posing for visitors."
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

    def scene(self, room_key: str) -> RoomSceneDefinition | None:
        cached = self._scene_cache.get(room_key)
        if cached is not None:
            return cached
        legacy = self.legacy_rooms.get(room_key)
        if legacy is None:
            return None

        augmentation = self.augmentations.get(room_key, RoomAugmentation())
        override_by_direction = {exit_def.direction: exit_def for exit_def in augmentation.exit_overrides}
        exits: list[ExitDefinition] = []
        for direction, destination_key in legacy.exits.items():
            override = override_by_direction.get(direction)
            if override is not None:
                exits.append(override)
                continue
            destination = self.legacy_rooms.get(destination_key)
            exits.append(
                ExitDefinition(
                    direction=direction,
                    destination_key=destination_key,
                    name=destination.name if destination else destination_key,
                )
            )
        exits.extend(augmentation.extra_exits)

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
        feature = next(
            (
                value for value in scene.features
                if value.condition.matches(context) and value.matches(target)
            ),
            None,
        )
        if feature is None:
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
