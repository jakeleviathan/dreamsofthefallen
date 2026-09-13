from __future__ import annotations

from dataclasses import replace

import mud.crownfire_march_31_40 as crownfire
import mud.world as legacy_world
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition


_REGION_KEYS = {
    crownfire.CROWNFIRE_REGION_KEY,
    crownfire.MORROWGATE_REGION_KEY,
    crownfire.REDOUBT_REGION_KEY,
    crownfire.PALACE_REGION_KEY,
}


def _without_extra(augmentation: RoomAugmentation, direction: str, destination_key: str) -> RoomAugmentation:
    return replace(
        augmentation,
        extra_exits=tuple(
            item
            for item in augmentation.extra_exits
            if not (item.direction == direction and item.destination_key == destination_key)
        ),
    )


def _add_extra(augmentation: RoomAugmentation, exit_def: ExitDefinition) -> RoomAugmentation:
    cleaned = tuple(
        item
        for item in augmentation.extra_exits
        if not (item.direction == exit_def.direction and item.destination_key == exit_def.destination_key)
    )
    return replace(augmentation, extra_exits=cleaned + (exit_def,))


def _add_override(augmentation: RoomAugmentation, exit_def: ExitDefinition) -> RoomAugmentation:
    cleaned = tuple(item for item in augmentation.exit_overrides if item.direction != exit_def.direction)
    return replace(augmentation, exit_overrides=cleaned + (exit_def,))


def apply_crownfire_room_field_tuning(world_service) -> None:
    """Normalize Crownfire room fields and make progression gates real exits.

    Crownfire's compact authored room helper used the legacy RoomDefinition field
    order incorrectly for description/region. The authored topology also includes
    static links that are meant to become available only after story milestones.
    Normalize both here before the production world-safety audit.
    """

    reverse_exits = {
        crownfire.TRIBUNAL_YARD_KEY: {"east": crownfire.MORROWGATE_COUNCIL_KEY},
        crownfire.DESERTER_ROAD_KEY: {"east": crownfire.REFUGEE_FORD_KEY},
        crownfire.DISARMED_ROAD_KEY: {"south": crownfire.REDOUBT_GATE_KEY},
    }

    corrected = []
    for room in crownfire.CROWNFIRE_ROOMS:
        if room.description in _REGION_KEYS and room.region_key not in _REGION_KEYS:
            room = replace(room, description=room.region_key, region_key=room.description)
        if room.key in reverse_exits:
            room = replace(room, exits=reverse_exits[room.key])
        corrected.append(room)

    crownfire.CROWNFIRE_ROOMS = tuple(corrected)

    for room in crownfire.CROWNFIRE_ROOMS:
        if room.key in legacy_world.ROOMS_BY_KEY:
            legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
        else:
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        legacy_world.ROOMS_BY_KEY[room.key] = room
        world_service.legacy_rooms[room.key] = room

    # Static dungeon links remain in the legacy topology for return-path auditing.
    # The advanced room service owns the player-facing story gates through explicit
    # exit overrides.
    gallows = world_service.augmentations.get(crownfire.GALLOWS_MILE_KEY, RoomAugmentation())
    gallows = _without_extra(gallows, "east", crownfire.REDOUBT_GATE_KEY)
    gallows = _add_override(
        gallows,
        ExitDefinition(
            direction="east",
            destination_key=crownfire.REDOUBT_GATE_KEY,
            name="Brass Redoubt Track",
            travel_text="You follow the Host supply track toward the forward redoubt.",
            condition=ViewCondition(required_flags=(crownfire.BLOCKADE_COMPLETE_FLAG,), min_level=34),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.GALLOWS_MILE_KEY] = gallows

    rampart = world_service.augmentations.get(crownfire.MORROWGATE_RAMPART_KEY, RoomAugmentation())
    rampart = _without_extra(rampart, "east", crownfire.PALACE_APPROACH_KEY)
    rampart = _add_override(
        rampart,
        ExitDefinition(
            direction="east",
            destination_key=crownfire.PALACE_APPROACH_KEY,
            name="Banner Palace Road",
            travel_text="You descend from the rampart onto the captured road toward Dask's field headquarters.",
            condition=ViewCondition(
                required_flags=(crownfire.REDOUBT_COMPLETE_FLAG, crownfire.DESERTER_COMPLETE_FLAG),
                min_level=37,
            ),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.MORROWGATE_RAMPART_KEY] = rampart

    command = world_service.augmentations.get(crownfire.PALACE_COMMAND_KEY, RoomAugmentation())
    command = _add_override(
        command,
        ExitDefinition(
            direction="north",
            destination_key=crownfire.PALACE_TREATY_KEY,
            name="Treaty Chamber",
            travel_text="With Dask's campaign ledger secured, you enter the treaty chamber where the marshal has made his final stand.",
            condition=ViewCondition(required_flags=(crownfire.PALACE_COMPLETE_FLAG,), min_level=40),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.PALACE_COMMAND_KEY] = command

    # Post-capstone routes deliberately use directions not already owned by the
    # base city/fort map, so the ending never steals a normal travel command.
    council = world_service.augmentations.get(crownfire.MORROWGATE_COUNCIL_KEY, RoomAugmentation())
    council = _without_extra(council, "east", crownfire.TRIBUNAL_YARD_KEY)
    council = _add_extra(
        council,
        ExitDefinition(
            direction="west",
            destination_key=crownfire.TRIBUNAL_YARD_KEY,
            name="Public Tribunal Yard",
            condition=ViewCondition(required_flags=(crownfire.TRIAL_ENDING_FLAG,)),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.MORROWGATE_COUNCIL_KEY] = council

    ford = world_service.augmentations.get(crownfire.REFUGEE_FORD_KEY, RoomAugmentation())
    ford = _without_extra(ford, "north", crownfire.DESERTER_ROAD_KEY)
    ford = _add_extra(
        ford,
        ExitDefinition(
            direction="west",
            destination_key=crownfire.DESERTER_ROAD_KEY,
            name="Open Deserter Road",
            condition=ViewCondition(required_flags=(crownfire.EXILE_ENDING_FLAG,)),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.REFUGEE_FORD_KEY] = ford

    redoubt = world_service.augmentations.get(crownfire.REDOUBT_GATE_KEY, RoomAugmentation())
    redoubt = _without_extra(redoubt, "east", crownfire.DISARMED_ROAD_KEY)
    redoubt = _add_extra(
        redoubt,
        ExitDefinition(
            direction="north",
            destination_key=crownfire.DISARMED_ROAD_KEY,
            name="Disarmed Host Road",
            condition=ViewCondition(required_flags=(crownfire.JUDGMENT_ENDING_FLAG,)),
            hidden_when_unavailable=True,
        ),
    )
    world_service.augmentations[crownfire.REDOUBT_GATE_KEY] = redoubt

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room in crownfire.CROWNFIRE_ROOMS:
            cache.pop(room.key, None)
        for key in (
            crownfire.GALLOWS_MILE_KEY,
            crownfire.MORROWGATE_RAMPART_KEY,
            crownfire.PALACE_COMMAND_KEY,
            crownfire.MORROWGATE_COUNCIL_KEY,
            crownfire.REFUGEE_FORD_KEY,
            crownfire.REDOUBT_GATE_KEY,
        ):
            cache.pop(key, None)
