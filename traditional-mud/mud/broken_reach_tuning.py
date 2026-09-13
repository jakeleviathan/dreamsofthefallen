from __future__ import annotations

from dataclasses import replace

from mud.broken_reach_midgame import FAR_WATCH_KEY, OLD_TOLL_ROAD_KEY
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition
from mud.veyra_city import VEYRA_SOUTH_SPRAWL_KEY
from mud.waymeet_adventure_arc import OLD_TOLL_ROAD as WAYMEET_OLD_TOLL_ROAD
from mud.waymeet_frontier import WAYMEET_BROKEN_MILE_KEY


def _without_destination(augmentation: RoomAugmentation, destination_key: str) -> RoomAugmentation:
    return replace(
        augmentation,
        extra_exits=tuple(
            exit_def
            for exit_def in augmentation.extra_exits
            if exit_def.destination_key != destination_key
        ),
    )


def _add_extra_exit(augmentation: RoomAugmentation | None, exit_def: ExitDefinition) -> RoomAugmentation:
    if augmentation is None:
        return RoomAugmentation(extra_exits=(exit_def,))
    extras = tuple(
        existing
        for existing in augmentation.extra_exits
        if not (
            existing.direction == exit_def.direction
            and existing.destination_key == exit_def.destination_key
        )
    )
    return replace(augmentation, extra_exits=extras + (exit_def,))


def apply_broken_reach_route_tuning(world_service) -> None:
    """Attach Broken Reach without stealing routes owned by earlier content.

    Waymeet already uses SOUTH from the Broken Mile for the level-2 Old Toll
    adventure, and Veyra already uses SOUTH from its timber sprawl for
    Sablewater. Broken Reach therefore continues the *existing* Old Toll Road
    farther south and uses WEST from Veyra for the reverse approach.
    """

    broken_mile = world_service.augmentations.get(WAYMEET_BROKEN_MILE_KEY)
    if broken_mile is not None:
        world_service.augmentations[WAYMEET_BROKEN_MILE_KEY] = _without_destination(
            broken_mile,
            OLD_TOLL_ROAD_KEY,
        )

    world_service.augmentations[WAYMEET_OLD_TOLL_ROAD] = _add_extra_exit(
        world_service.augmentations.get(WAYMEET_OLD_TOLL_ROAD),
        ExitDefinition(
            direction="south",
            destination_key=OLD_TOLL_ROAD_KEY,
            name="Broken Reach Road",
            travel_text=(
                "You continue south beyond the abandoned tollhouse, where the maintained road "
                "thins into the weed-split stones of the Broken Reach."
            ),
            condition=ViewCondition(min_level=10),
            hidden_when_unavailable=True,
        ),
    )

    veyra_sprawl = world_service.augmentations.get(VEYRA_SOUTH_SPRAWL_KEY)
    if veyra_sprawl is not None:
        veyra_sprawl = _without_destination(veyra_sprawl, FAR_WATCH_KEY)
    world_service.augmentations[VEYRA_SOUTH_SPRAWL_KEY] = _add_extra_exit(
        veyra_sprawl,
        ExitDefinition(
            direction="west",
            destination_key=FAR_WATCH_KEY,
            name="Broken Reach Road",
            travel_text=(
                "You leave Veyra's timber streets westward and climb toward Far Watch, "
                "where the Broken Reach road begins to unravel."
            ),
            condition=ViewCondition(min_level=10),
            hidden_when_unavailable=True,
        ),
    )

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (WAYMEET_BROKEN_MILE_KEY, WAYMEET_OLD_TOLL_ROAD, VEYRA_SOUTH_SPRAWL_KEY):
            cache.pop(room_key, None)
