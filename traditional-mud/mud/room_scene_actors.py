from __future__ import annotations

from dataclasses import dataclass
from random import random
from time import time

import mud.crafting as crafting
from mud.astralis_time import ASTRALIS_CLOCK
from mud.ecology import ASTRALIS_ECOLOGY
from mud.item_locations import ItemLocation, list_location_items


SCENE_SCHEMA = """
CREATE TABLE IF NOT EXISTS room_scene_actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    actor_key TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_key TEXT NOT NULL DEFAULT '',
    created_at_epoch REAL NOT NULL,
    expires_at_epoch REAL NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '',
    UNIQUE(room_key, kind, actor_key)
);
CREATE INDEX IF NOT EXISTS idx_room_scene_actors_room
ON room_scene_actors(room_key, expires_at_epoch);
"""


@dataclass(frozen=True, slots=True)
class SceneActor:
    id: int
    room_key: str
    kind: str
    actor_key: str
    name: str
    description: str
    source_key: str
    created_at: float
    expires_at: float


def ensure_scene_storage(database) -> None:
    with database.connect() as db:
        db.executescript(SCENE_SCHEMA)


def _row(row) -> SceneActor:
    return SceneActor(
        id=int(row["id"]), room_key=str(row["room_key"]), kind=str(row["kind"]),
        actor_key=str(row["actor_key"]), name=str(row["name"]),
        description=str(row["description"]), source_key=str(row["source_key"]),
        created_at=float(row["created_at_epoch"]), expires_at=float(row["expires_at_epoch"]),
    )


def add_scene_actor(database, room_key: str, kind: str, actor_key: str, name: str,
                    description: str, *, source_key: str = "", ttl_seconds: float = 0,
                    now: float | None = None) -> None:
    ensure_scene_storage(database)
    created = time() if now is None else float(now)
    expires = created + max(1.0, ttl_seconds) if ttl_seconds else 0.0
    with database.connect() as db:
        db.execute(
            """INSERT INTO room_scene_actors
               (room_key, kind, actor_key, name, description, source_key, created_at_epoch, expires_at_epoch)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(room_key, kind, actor_key) DO UPDATE SET
                 name=excluded.name, description=excluded.description,
                 source_key=excluded.source_key, created_at_epoch=excluded.created_at_epoch,
                 expires_at_epoch=excluded.expires_at_epoch""",
            (room_key, kind, actor_key, name, description, source_key, created, expires),
        )


def _weather_decay_factor(weather: str) -> float:
    value = weather.lower()
    if any(word in value for word in ("rain", "storm", "downpour")):
        return 0.35
    if any(word in value for word in ("hot", "heat", "sun")):
        return 0.65
    return 1.0


def list_scene_actors(database, room_key: str, *, weather: str = "", now: float | None = None) -> list[SceneActor]:
    ensure_scene_storage(database)
    current = time() if now is None else float(now)
    factor = _weather_decay_factor(weather)
    with database.connect() as db:
        # Weather does not merely change prose: rain and heat accelerate the
        # disappearance of exposed organic traces.
        rows = db.execute(
            "SELECT * FROM room_scene_actors WHERE room_key = ? ORDER BY created_at_epoch, id",
            (room_key,),
        ).fetchall()
        expired = []
        result = []
        for row in rows:
            actor = _row(row)
            effective_expiry = actor.expires_at
            if actor.kind in {"blood", "tracks", "remains"} and effective_expiry > 0 and factor < 1:
                effective_expiry = actor.created_at + (actor.expires_at - actor.created_at) * factor
            if effective_expiry > 0 and effective_expiry <= current:
                expired.append(actor.id)
            else:
                result.append(actor)
        if expired:
            db.executemany("DELETE FROM room_scene_actors WHERE id = ?", ((value,) for value in expired))
    return result


def record_combat_trace(database, room_key: str, enemy_key: str, enemy_name: str, *, roll: float | None = None) -> bool:
    """Rarely leave a physical trace. Nonliving foes never bleed."""
    lowered = (enemy_key + " " + enemy_name).lower()
    if any(word in lowered for word in ("skeleton", "construct", "golem", "dummy", "ghost", "wraith")):
        return False
    chance = 0.16
    if (random() if roll is None else roll) >= chance:
        return False
    add_scene_actor(
        database, room_key, "blood", f"blood:{enemy_key}",
        "Pool of Blood",
        f"A dark pool of blood from {enemy_name} stains the ground.",
        source_key=enemy_key, ttl_seconds=12 * 60,
    )
    return True


def _ecology_flora(room_key: str, region_key: str) -> tuple[tuple[str, str, str], ...]:
    state = ASTRALIS_ECOLOGY.state_for(region_key)
    if state is None or state.vegetation < 0.48 or state.resource_stock < 0.38:
        return ()
    biome = str(getattr(ASTRALIS_ECOLOGY, "_region_biomes", {}).get(region_key, "")).lower()
    if any(word in biome for word in ("desert", "tundra")):
        return ()
    if any(word in biome for word in ("swamp", "marsh", "fen", "bog")):
        return (("marsh_bloom", "Marsh Blooms", "Small pale flowers push up between the wet reeds."),)
    if any(word in biome for word in ("cavern", "underground", "underway")):
        return (("glowcap", "Glowcaps", "A small cluster of dim fungal caps grows along the damp stone."),)
    return (("wildflowers", "Wildflowers", "A few hardy wildflowers grow here among the grass."),)


def scene_lines(session, world_service, room_key: str, region_key: str) -> tuple[str, ...]:
    database = session.database
    weather = world_service.state.weather_for(region_key)
    lines: list[str] = []
    usable_database = database is not None and callable(getattr(database, "connect", None))

    # Dropped objects are first-class room contents. The underlying transfer
    # system preserves heritage serials, maker marks, and discovery identity.
    if usable_database:
        for item in list_location_items(database, ItemLocation.room(room_key)):
            key, qty = str(item["item_key"]), int(item["quantity"])
            definition = crafting.ITEMS_BY_KEY.get(key)
            name = definition.name if definition is not None else key.replace("_", " ").title()
            lines.append(f"{qty}x {name}" if qty > 1 else name)

        for actor in list_scene_actors(database, room_key, weather=weather):
            lines.append(f"{actor.name} - {actor.description}")

    for _key, name, description in _ecology_flora(room_key, region_key):
        lines.append(f"{name} - {description}")
    return tuple(lines)


def _flora_target(session, world_service, target: str):
    character = getattr(session, "character", None)
    if character is None:
        return None
    scene = world_service.scene(character.current_room or "")
    if scene is None:
        return None
    wanted = " ".join(target.lower().split())
    for key, name, description in _ecology_flora(scene.key, scene.region_key):
        aliases = {key.replace("_", " "), name.lower(), name.lower().rstrip("s")}
        if wanted in aliases or any(wanted and wanted in alias for alias in aliases):
            return key, name, description, scene
    return None


async def _handle_flora(session, world_service, verb: str, target: str) -> bool:
    match = _flora_target(session, world_service, target)
    if match is None:
        return False
    key, name, _description, scene = match
    if verb in {"smell", "sniff"}:
        scent = "earthy and faintly sweet" if key != "glowcap" else "cool, damp, and mushroom-rich"
        await session.send(f"You smell the {name.lower()}. They smell {scent}.\r\n")
        return True
    if verb in {"pick", "pluck"}:
        state = ASTRALIS_ECOLOGY.state_for(scene.region_key)
        if state is not None and state.resource_stock < 0.30:
            await session.send(f"The {name.lower()} here are too sparse to pick without stripping the patch.\r\n")
            return True
        # Picking is intentionally an ecological interaction, not free inventory
        # duplication. Existing gathering remains authoritative for valuable goods.
        if state is not None:
            state.resource_stock = max(0.0, state.resource_stock - 0.012)
            state.vegetation = max(0.0, state.vegetation - 0.006)
            ASTRALIS_ECOLOGY._write(scene.region_key, state)
        await session.send(f"You pick one of the {name.lower()}, leaving the rest of the patch intact.\r\n")
        return True
    return False


async def _delegate(self, previous, command: str) -> None:
    old = self.__dict__.get("prompt")
    had = "prompt" in self.__dict__
    async def replay(_text: str):
        return command
    self.prompt = replay
    try:
        await previous(self)
    finally:
        if had:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_room_scene_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_room_scene_runtime_installed", False):
        return
    previous = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        parts = normalized.split(maxsplit=1)
        if len(parts) == 2 and parts[0] in {"smell", "sniff", "pick", "pluck"}:
            if await _handle_flora(self, world_service, parts[0], parts[1]):
                return
        await _delegate(self, previous, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._room_scene_runtime_installed = True
