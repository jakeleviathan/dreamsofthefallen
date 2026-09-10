from __future__ import annotations

import json
from pathlib import Path

from mud.room_engine import DoorState, RoomStateStore


DEFAULT_WORLD_ROOM_STATE_PATH = Path("data/world_room_state.json")


def load_world_room_state(
    state: RoomStateStore,
    path: str | Path = DEFAULT_WORLD_ROOM_STATE_PATH,
) -> bool:
    """Load only shared WORLD state.

    Temporary state is deliberately never restored. Character-scoped state is
    already owned by the character database/flag system and therefore is not
    duplicated in this file.
    """
    state_path = Path(path)
    if not state_path.exists():
        return False

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False

    world_flags = payload.get("world_flags", {})
    if isinstance(world_flags, dict):
        state.world_flags = {
            str(room_key): {str(flag) for flag in flags if isinstance(flag, str)}
            for room_key, flags in world_flags.items()
            if isinstance(flags, list)
        }

    doors = payload.get("doors", {})
    if isinstance(doors, dict):
        restored_doors: dict[str, DoorState] = {}
        for door_key, values in doors.items():
            if not isinstance(values, dict):
                continue
            restored_doors[str(door_key)] = DoorState(
                open=bool(values.get("open", True)),
                locked=bool(values.get("locked", False)),
            )
        state.doors = restored_doors

    weather = payload.get("region_weather", {})
    if isinstance(weather, dict):
        state.region_weather = {
            str(region_key): str(value).lower()
            for region_key, value in weather.items()
            if isinstance(value, str)
        }
    return True


def save_world_room_state(
    state: RoomStateStore,
    path: str | Path = DEFAULT_WORLD_ROOM_STATE_PATH,
) -> None:
    """Atomically save WORLD state while excluding temporary/player state."""
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_suffix(state_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(state.snapshot_world_state(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(state_path)
