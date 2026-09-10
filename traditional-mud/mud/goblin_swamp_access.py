from __future__ import annotations

from dataclasses import replace

from mud.goblin_outer_route import GOBLIN_FIRST_PILING_KEY, GOBLIN_OUTER_ROUTE_COMPLETE_FLAG
from mud.goblin_swamp import (
    GOBLIN_BITTERWATER_RUN_KEY,
    GOBLIN_LANTERNMOSS_CUT_KEY,
    GOBLIN_REEDFEN_CAUSEWAY_KEY,
)
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition


def _branch(
    direction: str,
    destination: str,
    name: str,
    travel_text: str,
) -> ExitDefinition:
    return ExitDefinition(
        direction=direction,
        destination_key=destination,
        name=name,
        travel_text=travel_text,
        failure_text=(
            "Finish Ruskle Coil's first route lesson before taking the maintained swamp branches beyond the First Piling."
        ),
        condition=ViewCondition(required_flags=(GOBLIN_OUTER_ROUTE_COMPLETE_FLAG,)),
        hidden_when_unavailable=True,
    )


FIRST_PILING_SWAMP_BRANCHES: tuple[ExitDefinition, ...] = (
    _branch(
        "north",
        GOBLIN_REEDFEN_CAUSEWAY_KEY,
        "Reedfen Causeway",
        "You leave the First Piling north along a bottle-marked beginner causeway through the reeds.",
    ),
    _branch(
        "east",
        GOBLIN_BITTERWATER_RUN_KEY,
        "Bitterwater Run",
        "You take the east stepping route where pale cord marks the medicinal root banks.",
    ),
    _branch(
        "west",
        GOBLIN_LANTERNMOSS_CUT_KEY,
        "Lanternmoss Cut",
        "You follow the west cut between mossy hummocks and copper-tagged herbs.",
    ),
)


def enforce_first_piling_swamp_access(world_service) -> None:
    """Replace the First Piling's physical branch exits with gated room-engine exits.

    The legacy room keeps destination keys so older systems understand topology.
    These overrides are the authoritative player-facing exits and ensure a direct
    NORTH/EAST/WEST command cannot bypass Beyond the Painted Line.
    """
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return

    current = augmentations.get(GOBLIN_FIRST_PILING_KEY, RoomAugmentation())
    gated_directions = {branch.direction for branch in FIRST_PILING_SWAMP_BRANCHES}
    overrides = tuple(
        exit_def
        for exit_def in current.exit_overrides
        if exit_def.direction not in gated_directions
    ) + FIRST_PILING_SWAMP_BRANCHES
    extra_exits = tuple(
        exit_def
        for exit_def in current.extra_exits
        if exit_def.direction not in gated_directions
    )
    augmentations[GOBLIN_FIRST_PILING_KEY] = replace(
        current,
        exit_overrides=overrides,
        extra_exits=extra_exits,
    )

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(GOBLIN_FIRST_PILING_KEY, None)
