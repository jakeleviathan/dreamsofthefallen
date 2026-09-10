from __future__ import annotations

from dataclasses import replace

import mud.world as legacy_world
from mud.goblin_deep_mire import GOBLIN_OLD_PUMP_TRACK_KEY, install_goblin_deep_mire_content
from mud.goblin_start import GOBLIN_REGION_KEY
from mud.goblin_swamp import GOBLIN_APOTHECARY_BLIND_KEY
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import RoomDefinition


GOBLIN_HIGHWATER_CATWALK_KEY = "goblin_highwater_catwalk"
GOBLIN_BOTTLEWIRE_RETURN_KEY = "goblin_bottlewire_return"
GOBLIN_RETURN_LOOP_ROOM_KEYS = (
    GOBLIN_HIGHWATER_CATWALK_KEY,
    GOBLIN_BOTTLEWIRE_RETURN_KEY,
)
GOBLIN_RETURN_LOOP_DISCOVERED_FLAG = "goblin_highwater_return_discovered"


GOBLIN_RETURN_LOOP_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=GOBLIN_HIGHWATER_CATWALK_KEY,
        name="Highwater Catwalk",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A narrow catwalk rides the tops of old Human pump pylons above the worst of the mire. "
            "Goblin route crews have replaced missing spans with grating, boiler plate, and two improbably straight lengths of Dwarven rail. "
            "Bottle-glass reflectors mark every turn. The Old Pump Track is west; a descending switchback runs south toward the maintained herb routes."
        ),
        exits={"west": GOBLIN_OLD_PUMP_TRACK_KEY, "south": GOBLIN_BOTTLEWIRE_RETURN_KEY},
        tags=("goblin_deep_mire", "safe_return_route", "no_hostiles", "route_connector"),
    ),
    RoomDefinition(
        key=GOBLIN_BOTTLEWIRE_RETURN_KEY,
        name="Bottlewire Return",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "The catwalk folds into a broad switchback of plank, wire, and colored bottles hung at shoulder height. "
            "The bottles are not decoration: green means stable footing, amber marks a repair seam, and blue points toward clean water and the field apothecary. "
            "A roofed rest shelf sits above the mud. Highwater Catwalk is north; the Apothecary Blind lies south."
        ),
        exits={"north": GOBLIN_HIGHWATER_CATWALK_KEY, "south": GOBLIN_APOTHECARY_BLIND_KEY},
        tags=("goblin_deep_mire", "safe_return_route", "no_hostiles", "rest_point"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
    )


def _day(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_return_day", text, priority=40, condition=ViewCondition(time_buckets=("day",)))


def _night(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_return_night", text, priority=50, condition=ViewCondition(time_buckets=("night",)))


def _rain(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_return_rain", text, priority=60, condition=ViewCondition(weather=("rain", "storm")))


def goblin_return_loop_augmentations() -> dict[str, RoomAugmentation]:
    return {
        GOBLIN_HIGHWATER_CATWALK_KEY: RoomAugmentation(
            features=(
                _feature(
                    "highwater_rails",
                    "Highwater Rails",
                    "salvaged rails and grating holding the return route above deep mud",
                    "The route crews have overbuilt the dangerous parts on purpose. Repair dates and initials cover the plates, making maintenance history visible to anyone who bothers to read it.",
                    ("rails", "catwalk", "grating", "repair plates"),
                ),
            ),
            description_layers=(
                _day("In daylight the high route gives a rare long view over the reeds toward Junk City's smoke."),
                _night("At night hooded lamps and bottle reflectors make the catwalk read like a dotted line through black water."),
                _rain("Rain drums on the metal plates, but the elevated route remains above the rising surface water."),
            ),
        ),
        GOBLIN_BOTTLEWIRE_RETURN_KEY: RoomAugmentation(
            features=(
                _feature(
                    "return_markers",
                    "Return Markers",
                    "colored bottle markers encoding the safe way back toward the city",
                    "Green glass marks sound footing, amber marks a section due for inspection, and blue points toward the Apothecary Blind and clean water. A small Mirehook hook-mark identifies the route crew that first formalized the shortcut.",
                    ("markers", "bottles", "bottle markers", "route markers", "return markers"),
                ),
                _feature(
                    "rest_shelf",
                    "Roofed Rest Shelf",
                    "a dry bench built above the mud for loaded gatherers",
                    "The shelf is intentionally plain: a roof, a bench, drainage holes, and hooks for wet herb baskets. It exists because a useful route includes somewhere to stop without standing ankle-deep in swamp water.",
                    ("shelf", "bench", "rest bench", "rest shelf"),
                ),
            ),
            description_layers=(
                _day("Colored bottle glass throws small green, amber, and blue patches across the planks."),
                _night("Tiny shielded lamps shine through the bottle markers, making the switchback unusually easy to follow after dark."),
                _rain("The roofed shelf stays mostly dry while runoff spills harmlessly through gaps beside the route."),
            ),
        ),
    }


def _patch_exit(room: RoomDefinition, direction: str, destination: str) -> RoomDefinition:
    exits = dict(room.exits)
    exits[direction] = destination
    return replace(room, exits=exits)


def _merge_augmentations(world_service) -> None:
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return

    old_pump = augmentations.get(GOBLIN_OLD_PUMP_TRACK_KEY, RoomAugmentation())
    east_exit = ExitDefinition(
        direction="east",
        destination_key=GOBLIN_HIGHWATER_CATWALK_KEY,
        name="Highwater Return",
        travel_text="You step east onto the elevated emergency catwalk, leaving the pump ruins for the high return route.",
    )
    old_overrides = tuple(value for value in old_pump.exit_overrides if value.direction != "east") + (east_exit,)
    augmentations[GOBLIN_OLD_PUMP_TRACK_KEY] = replace(old_pump, exit_overrides=old_overrides)

    apothecary = augmentations.get(GOBLIN_APOTHECARY_BLIND_KEY, RoomAugmentation())
    north_exit = ExitDefinition(
        direction="north",
        destination_key=GOBLIN_BOTTLEWIRE_RETURN_KEY,
        name="Bottlewire Return",
        travel_text="Knowing the marker code, you take the north switchback onto the discovered highwater shortcut.",
        failure_text="The north marker route is not obvious from this side. Discover the highwater return from the deeper mire first.",
        condition=ViewCondition(required_flags=(GOBLIN_RETURN_LOOP_DISCOVERED_FLAG,)),
        hidden_when_unavailable=True,
    )
    apoth_overrides = tuple(value for value in apothecary.exit_overrides if value.direction != "north") + (north_exit,)
    augmentations[GOBLIN_APOTHECARY_BLIND_KEY] = replace(apothecary, exit_overrides=apoth_overrides)

    augmentations.update(goblin_return_loop_augmentations())

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(GOBLIN_OLD_PUMP_TRACK_KEY, None)
        cache.pop(GOBLIN_APOTHECARY_BLIND_KEY, None)
        for room_key in GOBLIN_RETURN_LOOP_ROOM_KEYS:
            cache.pop(room_key, None)


def install_goblin_return_loop_content(world_service=None) -> None:
    install_goblin_deep_mire_content()

    replacements: dict[str, RoomDefinition] = {}
    old_pump = legacy_world.ROOMS_BY_KEY.get(GOBLIN_OLD_PUMP_TRACK_KEY)
    if old_pump is not None:
        replacements[GOBLIN_OLD_PUMP_TRACK_KEY] = _patch_exit(old_pump, "east", GOBLIN_HIGHWATER_CATWALK_KEY)
    apothecary = legacy_world.ROOMS_BY_KEY.get(GOBLIN_APOTHECARY_BLIND_KEY)
    if apothecary is not None:
        replacements[GOBLIN_APOTHECARY_BLIND_KEY] = _patch_exit(apothecary, "north", GOBLIN_BOTTLEWIRE_RETURN_KEY)

    known = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in GOBLIN_RETURN_LOOP_ROOMS if room.key not in known)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    replacements.update({room.key: room for room in GOBLIN_RETURN_LOOP_ROOMS})
    legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY.update(replacements)

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        _merge_augmentations(world_service)


def install_goblin_return_loop_runtime(player_session_class, world_service) -> None:
    install_goblin_return_loop_content(world_service)
    if getattr(player_session_class, "_goblin_return_loop_runtime_installed", False):
        return

    previous_move_character = player_session_class.move_character

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        if self.character is None or self.character.race != "goblin":
            return
        after = self.character.current_room
        if before == after or after not in GOBLIN_RETURN_LOOP_ROOM_KEYS:
            return
        flags = self.database.list_flags(self.character.id)
        if GOBLIN_RETURN_LOOP_DISCOVERED_FLAG not in flags:
            self.database.grant_flag(self.character.id, GOBLIN_RETURN_LOOP_DISCOVERED_FLAG)
            await self.send(
                "\r\nYou learn the bottlewire marker code as the route folds back toward the city. From now on, the shortcut can also be found north from the Apothecary Blind.\r\n"
            )

    player_session_class.move_character = move_character
    player_session_class._goblin_return_loop_runtime_installed = True
