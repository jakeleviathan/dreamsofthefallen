from __future__ import annotations

from dataclasses import replace

import mud.crownfire_march_31_40 as crownfire
import mud.world as legacy_world


_REGION_KEYS = {
    crownfire.CROWNFIRE_REGION_KEY,
    crownfire.MORROWGATE_REGION_KEY,
    crownfire.REDOUBT_REGION_KEY,
    crownfire.PALACE_REGION_KEY,
}


def apply_crownfire_room_field_tuning(world_service) -> None:
    """Normalize Crownfire RoomDefinition fields before production validation.

    Crownfire was authored with a compact room helper while the legacy room
    dataclass stores description before region_key. Normalize the assembled
    definitions here so the live room registry always receives the intended
    description and region identity.
    """

    corrected = []
    for room in crownfire.CROWNFIRE_ROOMS:
        if room.description in _REGION_KEYS and room.region_key not in _REGION_KEYS:
            room = replace(room, description=room.region_key, region_key=room.description)
        corrected.append(room)

    crownfire.CROWNFIRE_ROOMS = tuple(corrected)

    for room in crownfire.CROWNFIRE_ROOMS:
        if room.key in legacy_world.ROOMS_BY_KEY:
            legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
        else:
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        legacy_world.ROOMS_BY_KEY[room.key] = room
        world_service.legacy_rooms[room.key] = room

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room in crownfire.CROWNFIRE_ROOMS:
            cache.pop(room.key, None)
