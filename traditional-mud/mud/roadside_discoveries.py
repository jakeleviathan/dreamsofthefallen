from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.broken_reach_midgame import FAR_WATCH_KEY
from mud.crownfire_march_31_40 import WINDMILL_SCAR_KEY
from mud.crafting import ItemDefinition
from mud.frontier_convergence import ASHCROSS_SUNKEN_WATCH_KEY
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.salt_kingdoms_midgame import PILGRIM_SALT_KEY
from mud.world import RoomDefinition


# These pockets are deliberately not another campaign. They are short places a
# curious player can walk past entirely: local mysteries, mundane remnants, and
# one unanswered detail worth remembering afterward.

FIFTY_REGION_KEY = "roadside_fifty_chairs"
QUIET_BELL_REGION_KEY = "roadside_quiet_bell"
BLUE_SINK_REGION_KEY = "roadside_blue_salt_sink"
NOONWATCH_REGION_KEY = "roadside_noonwatch"

# ---------------------------------------------------------------------------
# 15-ish: The House of Fifty Chairs, beneath the already optional Sunken Watch.
# ---------------------------------------------------------------------------
FIFTY_CRAWL_KEY = "roadside_fifty_chair_crawl"
FIFTY_VESTIBULE_KEY = "roadside_fifty_chair_vestibule"
FIFTY_HALL_KEY = "roadside_hall_of_fifty_chairs"
FIFTY_BEHIND_WALL_KEY = "roadside_behind_blank_wall"

# ---------------------------------------------------------------------------
# 18-ish: an abandoned watchtower above Far Watch. The bell itself is gone.
# ---------------------------------------------------------------------------
QUIET_STAIR_KEY = "roadside_quiet_watch_stair"
QUIET_KEEPER_KEY = "roadside_quiet_keeper_room"
QUIET_BELFRY_KEY = "roadside_quiet_belfry"
QUIET_ROOF_KEY = "roadside_quiet_wind_roof"

# ---------------------------------------------------------------------------
# 25-ish: a blue salt collapse off Pilgrim Salt. It has no Undertide explanation.
# ---------------------------------------------------------------------------
BLUE_RIM_KEY = "roadside_blue_sink_rim"
BLUE_THROAT_KEY = "roadside_blue_salt_throat"
BLUE_CHAMBER_KEY = "roadside_blue_salt_chamber"
BLUE_SHELL_KEY = "roadside_blue_shell_shelf"
BLUE_TABLE_KEY = "roadside_blue_dry_table"

# ---------------------------------------------------------------------------
# 34-ish: Noonwatch, an abandoned civilian signal tower in Crownfire.
# ---------------------------------------------------------------------------
NOON_PATH_KEY = "roadside_noonwatch_path"
NOON_KEEPER_KEY = "roadside_noonwatch_keeper_floor"
NOON_LENS_KEY = "roadside_noonwatch_lens_room"
NOON_PLATFORM_KEY = "roadside_noonwatch_platform"

FIFTY_ROOM_KEYS = (FIFTY_CRAWL_KEY, FIFTY_VESTIBULE_KEY, FIFTY_HALL_KEY, FIFTY_BEHIND_WALL_KEY)
QUIET_BELL_ROOM_KEYS = (QUIET_STAIR_KEY, QUIET_KEEPER_KEY, QUIET_BELFRY_KEY, QUIET_ROOF_KEY)
BLUE_SINK_ROOM_KEYS = (BLUE_RIM_KEY, BLUE_THROAT_KEY, BLUE_CHAMBER_KEY, BLUE_SHELL_KEY, BLUE_TABLE_KEY)
NOONWATCH_ROOM_KEYS = (NOON_PATH_KEY, NOON_KEEPER_KEY, NOON_LENS_KEY, NOON_PLATFORM_KEY)
ROADSIDE_ROOM_KEYS = (*FIFTY_ROOM_KEYS, *QUIET_BELL_ROOM_KEYS, *BLUE_SINK_ROOM_KEYS, *NOONWATCH_ROOM_KEYS)

FIFTY_WALL_OPEN_FLAG = "roadside_fifty_blank_wall_open"
FIFTY_COMPLETE_FLAG = "roadside_fifty_chairs_complete"
QUIET_COMPLETE_FLAG = "roadside_quiet_bell_complete"
BLUE_COMPLETE_FLAG = "roadside_blue_sink_complete"
NOON_COMPLETE_FLAG = "roadside_noonwatch_complete"

FIFTY_QUEST_KEY = "roadside_fifty_chairs"
QUIET_QUEST_KEY = "roadside_quiet_bell"
BLUE_QUEST_KEY = "roadside_blue_salt_sink"
NOON_QUEST_KEY = "roadside_noonwatch"

FIFTY_STUB_KEY = "roadside_blank_wall_stub"
QUIET_RIVET_KEY = "roadside_silent_watch_rivet"
BLUE_SHELL_ITEM_KEY = "roadside_blue_salt_shell"
NOON_LENS_ITEM_KEY = "roadside_noonwatch_lens"

ROADSIDE_ITEMS = (
    ItemDefinition(
        FIFTY_STUB_KEY,
        "Blank-Wall Admission Stub",
        "A brittle paper stub found behind a wall that fifty chairs still face. The printed event name has been carefully scraped away, but the seat number reads 50.",
        "curio",
        tier=4,
    ),
    ItemDefinition(
        QUIET_RIVET_KEY,
        "Silent Watch Rivet",
        "A cold iron rivet loosened from a bell frame whose bell is long gone. If held beside the ear after sunset, it sometimes seems to hum once and stop.",
        "curio",
        tier=4,
    ),
    ItemDefinition(
        BLUE_SHELL_ITEM_KEY,
        "Blue Salt Shell",
        "A tiny closed shell whitened by age except for a blue mineral seam around its lip. It came from a dry chamber impossibly far from the old shoreline.",
        "curio",
        tier=6,
    ),
    ItemDefinition(
        NOON_LENS_ITEM_KEY,
        "Noonwatch Lens",
        "A thumb-sized spare lens from an abandoned civilian watchtower. Scratches on its rim mark a single sun angle rather than a military bearing.",
        "curio",
        tier=8,
    ),
)

FIFTY_QUEST = QuestDefinition(
    key=FIFTY_QUEST_KEY,
    name="Fifty Seats, No Stage",
    style="freeform",
    minimum_level=15,
    description="Beneath the Sunken Watch is a little house containing fifty mismatched chairs, all facing a blank wall. Nobody left a useful explanation.",
    objective_steps=(
        ("count", "In the Hall of Fifty Chairs, COUNT CHAIRS."),
        ("sit", "SIT LAST CHAIR."),
        ("listen", "While seated, LISTEN WALL."),
        ("take_stub", "Enter the space behind the blank wall and TAKE STUB."),
        ("complete", "You found an admission stub with its event name deliberately removed."),
    ),
)
QUIET_QUEST = QuestDefinition(
    key=QUIET_QUEST_KEY,
    name="The Bell That Left",
    style="freeform",
    minimum_level=18,
    description="The abandoned tower above Far Watch has a belfry, a bell-frame, and old duty logs-but no bell and no record of when it was removed.",
    objective_steps=(
        ("read_log", "READ WATCH LOG in the Keeper Room."),
        ("examine_frame", "EXAMINE BELL FRAME in the belfry."),
        ("ring_frame", "RING FRAME and listen to what answers."),
        ("complete", "The empty frame answered once despite having nothing left to ring."),
    ),
)
BLUE_QUEST = QuestDefinition(
    key=BLUE_QUEST_KEY,
    name="A Table Under Salt",
    style="freeform",
    minimum_level=25,
    description="A blue-veined sink east of Pilgrim Salt contains old shells, fresh mineral growth, and one perfectly dry wooden table with no sensible route by which it arrived.",
    objective_steps=(
        ("touch_salt", "In the Blue Chamber, TOUCH BLUE SALT."),
        ("listen_shell", "At the Shell Shelf, LISTEN SHELL."),
        ("wait_table", "At the Dry Table, WAIT."),
        ("complete", "A tiny shell appeared on the dry table while nothing else moved."),
    ),
)
NOON_QUEST = QuestDefinition(
    key=NOON_QUEST_KEY,
    name="Only at Noon",
    style="freeform",
    minimum_level=34,
    description="A civilian watchtower above Windmill Scar contains a log written only at noon and a lens that someone has adjusted since the tower was abandoned.",
    objective_steps=(
        ("read_log", "READ NOON LOG in the Keeper Floor."),
        ("align_lens", "ALIGN LENS in the Lens Room."),
        ("look_lens", "On the upper platform, LOOK THROUGH LENS."),
        ("complete", "The lens points not at a fort but at an old civilian footpath still used by people avoiding the war road."),
    ),
)
ROADSIDE_QUESTS = (FIFTY_QUEST, QUIET_QUEST, BLUE_QUEST, NOON_QUEST)


def _room(key: str, name: str, region_key: str, description: str, exits: dict[str, str], *, tags: tuple[str, ...]) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        description=description,
        region_key=region_key,
        exits=exits,
        tags=("shared_world", "optional_discovery", "roadside_story", *tags),
    )


ROADSIDE_ROOMS = (
    _room(
        FIFTY_CRAWL_KEY,
        "Crawl Beneath the Watch",
        FIFTY_REGION_KEY,
        "A stair-sized crack descends through the foundation of the Sunken Watch. Old plaster begins where ordinary road stone should continue, as though a small buried building was here before the watchtower was built over it.",
        {"up": ASHCROSS_SUNKEN_WATCH_KEY, "down": FIFTY_VESTIBULE_KEY},
        tags=("level_15_17", "hidden_house"),
    ),
    _room(
        FIFTY_VESTIBULE_KEY,
        "Vestibule Under the Road",
        FIFTY_REGION_KEY,
        "A domestic entryway survives under the roadbed. Fifty wooden coat pegs cover one wall. None has a coat, hat, name, or dust-shadow to prove anything ever hung there.",
        {"up": FIFTY_CRAWL_KEY, "east": FIFTY_HALL_KEY},
        tags=("level_15_17", "hidden_house"),
    ),
    _room(
        FIFTY_HALL_KEY,
        "Hall of Fifty Chairs",
        FIFTY_REGION_KEY,
        "Exactly fifty mismatched chairs stand in ten neat rows. Every seat faces a perfectly blank plaster wall. The chairs range from expensive dining furniture to a three-legged stool repaired with wire. The floor is worn beneath every pair of front legs. There is no stage, shrine, fireplace, window, or inscription to explain what an audience watched here.",
        {"west": FIFTY_VESTIBULE_KEY, "north": FIFTY_BEHIND_WALL_KEY},
        tags=("level_15_17", "oddity", "chairs"),
    ),
    _room(
        FIFTY_BEHIND_WALL_KEY,
        "Behind the Blank Wall",
        FIFTY_REGION_KEY,
        "The space behind the plaster is disappointingly small: bare lath, an old stool, and a nail holding a brittle admission stub. There is no hidden theater machinery and nowhere for a performer to stand. From this side the wall carries fifty tiny pencil marks at seated eye height.",
        {"south": FIFTY_HALL_KEY},
        tags=("level_15_17", "oddity", "hidden"),
    ),

    _room(
        QUIET_STAIR_KEY,
        "Broken Watch Stair",
        QUIET_BELL_REGION_KEY,
        "A narrow exterior stair climbs above Far Watch along a tower that has lost half its facing stones. Wind passes cleanly through arrow slits, but one old iron handrail remains polished by use.",
        {"down": FAR_WATCH_KEY, "up": QUIET_KEEPER_KEY},
        tags=("level_18_20", "watchtower"),
    ),
    _room(
        QUIET_KEEPER_KEY,
        "Abandoned Keeper Room",
        QUIET_BELL_REGION_KEY,
        "The keeper's room contains a narrow bunk, a cold stove, and a weather log written in three hands. Every day records dawn, midday, dusk, and midnight-except for one repeating hour that has been cut cleanly out of every page.",
        {"down": QUIET_STAIR_KEY, "up": QUIET_BELFRY_KEY},
        tags=("level_18_20", "watchtower", "lore"),
    ),
    _room(
        QUIET_BELFRY_KEY,
        "Quiet Belfry",
        QUIET_BELL_REGION_KEY,
        "A heavy oak bell-frame fills the upper chamber. Its rope, axle, and bronze bell are gone. Four empty bolt holes show where the bell was removed carefully rather than torn loose. The frame itself is still under tension, although there is nothing left for it to carry.",
        {"down": QUIET_KEEPER_KEY, "up": QUIET_ROOF_KEY},
        tags=("level_18_20", "watchtower", "oddity"),
    ),
    _room(
        QUIET_ROOF_KEY,
        "Wind Roof",
        QUIET_BELL_REGION_KEY,
        "The roof looks across the Broken Reach, Veyra's outskirts, and the low hill-road to the north. Rust stains mark where a bell could once have been lowered by crane, but no drag trail continues beyond the parapet. Whatever happened to it did not involve rolling it away.",
        {"down": QUIET_BELFRY_KEY},
        tags=("level_18_20", "watchtower", "vista"),
    ),

    _room(
        BLUE_RIM_KEY,
        "Blue Salt Sink",
        BLUE_SINK_REGION_KEY,
        "East of Pilgrim Salt, the white crust gives way to a bowl veined in cobalt-blue mineral. The collapse is old enough for wagon dust to have softened its rim, but no caravan track approaches it.",
        {"west": PILGRIM_SALT_KEY, "down": BLUE_THROAT_KEY},
        tags=("level_25_28", "salt_sink"),
    ),
    _room(
        BLUE_THROAT_KEY,
        "Salt Throat",
        BLUE_SINK_REGION_KEY,
        "A sloping throat of packed salt descends between hard blue ribs. The air is dry and still. Halfway down, a line of tiny marine shells is embedded in the wall as neatly as beads on a string.",
        {"up": BLUE_RIM_KEY, "down": BLUE_CHAMBER_KEY},
        tags=("level_25_28", "salt_sink"),
    ),
    _room(
        BLUE_CHAMBER_KEY,
        "Blue Chamber",
        BLUE_SINK_REGION_KEY,
        "The chamber walls are ordinary gray stone under a skin of luminous blue salt. Nothing drips. Nothing hums. The mineral is cool enough to numb a fingertip even through a glove.",
        {"up": BLUE_THROAT_KEY, "east": BLUE_SHELL_KEY},
        tags=("level_25_28", "salt_sink", "oddity"),
    ),
    _room(
        BLUE_SHELL_KEY,
        "Shell Shelf",
        BLUE_SINK_REGION_KEY,
        "Hundreds of old shells rest on a natural ledge. Most are common basin fossils, but a few sit loose on top of the mineral crust as though placed here after the sea vanished.",
        {"west": BLUE_CHAMBER_KEY, "south": BLUE_TABLE_KEY},
        tags=("level_25_28", "salt_sink", "oddity"),
    ),
    _room(
        BLUE_TABLE_KEY,
        "The Dry Table",
        BLUE_SINK_REGION_KEY,
        "A plain four-legged wooden table occupies the deepest pocket. It is too wide for the Salt Throat and too intact to predate the collapse. Its top is absolutely dry and bears one clean circular stain the size of a drinking cup.",
        {"north": BLUE_SHELL_KEY},
        tags=("level_25_28", "salt_sink", "oddity"),
    ),

    _room(
        NOON_PATH_KEY,
        "Noonwatch Path",
        NOONWATCH_REGION_KEY,
        "A footpath climbs behind the dismantled windmill into thorny high ground. A weathered sign says CIVIL WATCH - NO GARRISON, as though somebody once expected soldiers to misunderstand the distinction.",
        {"down": WINDMILL_SCAR_KEY, "up": NOON_KEEPER_KEY},
        tags=("level_34_36", "watchtower", "civilian"),
    ),
    _room(
        NOON_KEEPER_KEY,
        "Noonwatch Keeper Floor",
        NOONWATCH_REGION_KEY,
        "This tower room was stripped long before the Gilded Host arrived. A ledger survives because somebody used it to level a wobbly shelf. Every surviving entry begins at noon exactly; no dawn or night observations were ever recorded.",
        {"down": NOON_PATH_KEY, "up": NOON_LENS_KEY},
        tags=("level_34_36", "watchtower", "civilian", "lore"),
    ),
    _room(
        NOON_LENS_KEY,
        "Noonwatch Lens Room",
        NOONWATCH_REGION_KEY,
        "A brass sighting frame points through a narrow south-facing slit. Its main lens is dusty, but the adjustment screw carries a fresh bright crescent where someone moved it recently by less than a finger's width.",
        {"down": NOON_KEEPER_KEY, "up": NOON_PLATFORM_KEY},
        tags=("level_34_36", "watchtower", "civilian", "oddity"),
    ),
    _room(
        NOON_PLATFORM_KEY,
        "Noonwatch Platform",
        NOONWATCH_REGION_KEY,
        "The upper platform overlooks red fields, chalk cuts, and a thin footpath that keeps below every military skyline. At noon the tower's lens would throw one small spot of light onto whichever path marker the keeper had aligned it with.",
        {"down": NOON_LENS_KEY},
        tags=("level_34_36", "watchtower", "civilian", "vista"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = (), *, listen: str = "", touch: str = "") -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        listen_text=listen,
        touch_text=touch,
    )


FEATURES_BY_ROOM: dict[str, tuple[FeatureDefinition, ...]] = {
    FIFTY_HALL_KEY: (
        _feature("fifty_chairs", "Fifty Chairs", "fifty mismatched seats facing one blank wall", "The count really is fifty. No two chairs quite match, but the wear under their front legs is remarkably consistent.", ("chairs", "chair", "seats", "fifty chairs")),
        _feature("blank_wall", "Blank Wall", "a bare plaster wall with nothing to watch", "The wall is aggressively ordinary: plaster, old limewash, hairline cracks. No image has been painted over and no shrine was removed.", ("wall", "blank wall"), listen="At first there is only your own breathing. Then, once, something taps from the other side."),
    ),
    FIFTY_BEHIND_WALL_KEY: (
        _feature("admission_stub", "Admission Stub", "a brittle ticket hanging from one nail", "The event name has been scraped away so carefully that the paper is almost transparent there. SEAT 50 remains legible.", ("stub", "ticket", "admission")),
    ),
    QUIET_KEEPER_KEY: (
        _feature("quiet_log", "Watch Log", "a weather log with the same missing hour cut from every page", "Different keepers used different ink and handwriting, but each page has one narrow strip removed at exactly the same place.", ("log", "watch log", "ledger")),
    ),
    QUIET_BELFRY_KEY: (
        _feature("empty_bell_frame", "Empty Bell Frame", "a loaded oak frame carrying no bell", "The bronze bell, axle, and rope were removed cleanly. The timber is still flexed as if several hundred pounds remain hanging from it.", ("frame", "bell frame", "empty frame"), listen="The timber gives one low settling note, far too pure for dry wood."),
    ),
    BLUE_CHAMBER_KEY: (
        _feature("blue_salt", "Blue Salt", "cold cobalt mineral growth on dry stone", "The mineral forms over older salt but does not follow moisture lines. Its blue is strongest where the wall should be driest.", ("salt", "blue salt", "mineral"), touch="Cold travels through the fingertip faster than it should, then stops exactly at the first knuckle."),
    ),
    BLUE_SHELL_KEY: (
        _feature("loose_shells", "Loose Shells", "a few unfossilized shells resting above the old mineral crust", "These shells are not part of the stone. Someone-or something-placed them after the basin dried.", ("shell", "shells", "loose shells"), listen="One shell gives back a tiny wash of surf that ends before a second wave arrives."),
    ),
    BLUE_TABLE_KEY: (
        _feature("dry_table", "Dry Table", "an impossible wooden table with one cup ring", "The table is too broad for the passage you used. Every surface is dry. The lone ring stain is fresh enough to have a sharp edge.", ("table", "wooden table", "ring stain")),
    ),
    NOON_KEEPER_KEY: (
        _feature("noon_log", "Noon Log", "a civic watch log containing only midday observations", "The entries track road visibility, smoke from cookfires, and whether distant path markers could be seen. It was a civilian wayfinding service, not a military watch.", ("log", "noon log", "ledger")),
    ),
    NOON_LENS_KEY: (
        _feature("noon_lens", "Noon Lens", "a dusty civic signal lens with a freshly moved screw", "The sighting frame is old, but somebody adjusted it recently. Its bearing points below the military roads rather than toward Morrowgate or the Redoubt.", ("lens", "sighting lens", "frame")),
    ),
}


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _patch_anchor_exit(anchor_key: str, direction: str, destination_key: str) -> None:
    anchor = legacy_world.ROOMS_BY_KEY[anchor_key]
    current = anchor.exits.get(direction)
    if current is not None and current != destination_key:
        raise ValueError(f"Roadside discovery would overwrite {anchor_key} {direction} -> {current}")
    exits = dict(anchor.exits)
    exits[direction] = destination_key
    _replace_room(replace(anchor, exits=exits))


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    existing = existing or RoomAugmentation()
    overrides = {item.direction: item for item in existing.exit_overrides}
    overrides.update({item.direction: item for item in extra.exit_overrides})
    extras = {(item.direction, item.destination_key): item for item in existing.extra_exits}
    extras.update({(item.direction, item.destination_key): item for item in extra.extra_exits})
    features = {item.key: item for item in existing.features}
    features.update({item.key: item for item in extra.features})
    layers = {item.key: item for item in existing.description_layers}
    layers.update({item.key: item for item in extra.description_layers})
    return RoomAugmentation(
        exit_overrides=tuple(overrides.values()),
        extra_exits=tuple(extras.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


def _route(direction: str, destination_key: str, name: str, text: str, *, min_level: int = 0, required_flags: tuple[str, ...] = ()) -> ExitDefinition:
    return ExitDefinition(
        direction=direction,
        destination_key=destination_key,
        name=name,
        travel_text=text,
        condition=ViewCondition(min_level=min_level, required_flags=required_flags),
        hidden_when_unavailable=True,
    )


def _authored_route_overrides(room: RoomDefinition) -> tuple[ExitDefinition, ...]:
    return tuple(
        _route(direction, destination, legacy_world.ROOMS_BY_KEY.get(destination, room).name, f"You follow the narrow route {direction}.")
        for direction, destination in room.exits.items()
    )


def install_roadside_discoveries_content(world_service=None) -> None:
    for item in ROADSIDE_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for quest in ROADSIDE_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for room in ROADSIDE_ROOMS:
        _replace_room(room)

    # Static legacy routes are required because the base movement function owns
    # the actual room write. The advanced room service then gates those routes so
    # under-level characters never reach the legacy move call.
    _patch_anchor_exit(ASHCROSS_SUNKEN_WATCH_KEY, "down", FIFTY_CRAWL_KEY)
    _patch_anchor_exit(FAR_WATCH_KEY, "up", QUIET_STAIR_KEY)
    _patch_anchor_exit(PILGRIM_SALT_KEY, "east", BLUE_RIM_KEY)
    _patch_anchor_exit(WINDMILL_SCAR_KEY, "up", NOON_PATH_KEY)

    if world_service is None:
        return

    for key, room in legacy_world.ROOMS_BY_KEY.items():
        if key in ROADSIDE_ROOM_KEYS or key in {ASHCROSS_SUNKEN_WATCH_KEY, FAR_WATCH_KEY, PILGRIM_SALT_KEY, WINDMILL_SCAR_KEY}:
            world_service.legacy_rooms[key] = room

    anchor_augments = {
        ASHCROSS_SUNKEN_WATCH_KEY: RoomAugmentation(exit_overrides=(
            _route("down", FIFTY_CRAWL_KEY, "Foundation Crack", "You lower yourself through the old watch foundation into plastered darkness.", min_level=15),
        )),
        FAR_WATCH_KEY: RoomAugmentation(exit_overrides=(
            _route("up", QUIET_STAIR_KEY, "Broken Watch Stair", "You climb the exposed stair above Far Watch toward the abandoned belfry.", min_level=18),
        )),
        PILGRIM_SALT_KEY: RoomAugmentation(exit_overrides=(
            _route("east", BLUE_RIM_KEY, "Blue Salt Sink", "You leave the offering path and cross hard white crust toward a cobalt-veined sink.", min_level=25),
        )),
        WINDMILL_SCAR_KEY: RoomAugmentation(exit_overrides=(
            _route("up", NOON_PATH_KEY, "Noonwatch Path", "You climb behind the dismantled mill toward the old civilian watchtower.", min_level=34),
        )),
    }
    for key, augmentation in anchor_augments.items():
        world_service.augmentations[key] = _merge_augmentation(world_service.augmentations.get(key), augmentation)

    for room in ROADSIDE_ROOMS:
        overrides = list(_authored_route_overrides(room))
        if room.key == FIFTY_HALL_KEY:
            overrides = [item for item in overrides if item.direction != "north"]
            overrides.append(_route(
                "north",
                FIFTY_BEHIND_WALL_KEY,
                "Opened Blank Wall",
                "A narrow plaster panel gives inward and lets you squeeze behind the wall the chairs face.",
                required_flags=(FIFTY_WALL_OPEN_FLAG,),
            ))
        augmentation = RoomAugmentation(
            exit_overrides=tuple(overrides),
            features=FEATURES_BY_ROOM.get(room.key, ()),
        )
        world_service.augmentations[room.key] = _merge_augmentation(world_service.augmentations.get(room.key), augmentation)

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*ROADSIDE_ROOM_KEYS, ASHCROSS_SUNKEN_WATCH_KEY, FAR_WATCH_KEY, PILGRIM_SALT_KEY, WINDMILL_SCAR_KEY):
            cache.pop(key, None)


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _start(session, quest_key: str, step: str) -> None:
    if session.character is not None and _quest(session, quest_key) is None:
        session.database.start_quest(session.character.id, quest_key, step)


def _advance(session, quest_key: str, expected: str, next_step: str) -> bool:
    q = _quest(session, quest_key)
    if not q or q.get("status") != "active" or q.get("current_step") != expected:
        return False
    session.database.advance_quest(session.character.id, quest_key, next_step)
    return True


def _award_completion(session, quest_key: str, flag_key: str, item_key: str, xp: int) -> bool:
    if session.character is None:
        return False
    flags = set(session.database.list_flags(session.character.id))
    if flag_key in flags:
        return False
    session.database.complete_quest(session.character.id, quest_key)
    session.database.grant_flag(session.character.id, flag_key)
    if session.database.item_quantity(session.character.id, item_key) <= 0:
        session.database.add_item(session.character.id, item_key, 1)
    session.database.add_experience(session.character.id, xp)
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed
    return True


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_roadside_discoveries_runtime(player_session_class, world_service) -> None:
    install_roadside_discoveries_content(world_service)
    if getattr(player_session_class, "_roadside_discoveries_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        n = " ".join(command.strip().lower().split())
        room = self.character.current_room or ""

        # Fifty Chairs: no monster, no explanation, just an audience arrangement
        # that behaves exactly once as if something on the other side noticed you.
        if room == FIFTY_HALL_KEY and n == "count chairs":
            _start(self, FIFTY_QUEST_KEY, "count")
            _advance(self, FIFTY_QUEST_KEY, "count", "sit")
            await self.send("You count twice. Fifty. The last chair is the crude three-legged stool in the back-right corner, repaired with black wire. Every front leg has worn the floor in the same direction: toward the blank wall.\r\nQuest discovered: Fifty Seats, No Stage.\r\n")
            return
        if room == FIFTY_HALL_KEY and n in {"sit last chair", "sit in last chair", "sit stool"}:
            if _advance(self, FIFTY_QUEST_KEY, "sit", "listen"):
                await self.send("You sit in seat fifty. From here the wall is exactly at eye level. The room feels less like a theater than a place where fifty people once agreed to wait for the same thing. LISTEN WALL.\r\n")
            else:
                await self.send("You sit for a moment. Nothing about the chair explains the room by itself.\r\n")
            return
        if room == FIFTY_HALL_KEY and n in {"listen wall", "listen blank wall"}:
            if _advance(self, FIFTY_QUEST_KEY, "listen", "take_stub"):
                self.database.grant_flag(self.character.id, FIFTY_WALL_OPEN_FLAG)
                world_service._scene_cache.pop(FIFTY_HALL_KEY, None)
                await self.send("For several breaths: nothing. Then one precise knock answers from the other side. A plaster seam beside the wall releases with a dry click. A narrow way north is now visible.\r\n")
            else:
                await self.send("The wall gives you plaster silence and the distant settling of the buried house.\r\n")
            return
        if room == FIFTY_BEHIND_WALL_KEY and n in {"take stub", "take ticket", "take admission stub"}:
            q = _quest(self, FIFTY_QUEST_KEY)
            if q and q.get("status") == "active" and q.get("current_step") == "take_stub" and _award_completion(self, FIFTY_QUEST_KEY, FIFTY_COMPLETE_FLAG, FIFTY_STUB_KEY, 350):
                await self.send("You take the brittle admission stub. SEAT 50 survived; the event name did not. Quest complete: Fifty Seats, No Stage. Reward: 350 XP and Blank-Wall Admission Stub.\r\n")
            else:
                await self.send("There is no second stub to take.\r\n")
            return

        # Quiet Bell: the object that should make the sound is missing. The tower
        # refuses to explain whether the frame, the place, or memory itself answers.
        if room == QUIET_KEEPER_KEY and n in {"read watch log", "read log"}:
            _start(self, QUIET_QUEST_KEY, "read_log")
            _advance(self, QUIET_QUEST_KEY, "read_log", "examine_frame")
            await self.send("Three keepers recorded weather, road traffic, and lantern checks in different hands. Every page has the same hour physically cut out. The cuts predate the last keeper. Quest discovered: The Bell That Left.\r\n")
            return
        if room == QUIET_BELFRY_KEY and n in {"examine bell frame", "examine frame", "look bell frame"}:
            if _advance(self, QUIET_QUEST_KEY, "examine_frame", "ring_frame"):
                await self.send("The bell was unbolted properly. The frame is still bowed downward as though carrying its old load. One loose rivet sits where the missing axle used to turn. RING FRAME.\r\n")
            else:
                await self.send("The empty frame is under tension for no reason you can prove.\r\n")
            return
        if room == QUIET_BELFRY_KEY and n in {"ring frame", "strike frame", "pull frame"}:
            q = _quest(self, QUIET_QUEST_KEY)
            if q and q.get("status") == "active" and q.get("current_step") == "ring_frame" and _award_completion(self, QUIET_QUEST_KEY, QUIET_COMPLETE_FLAG, QUIET_RIVET_KEY, 475):
                await self.send("You put one hand on the empty frame and pull. Nothing moves. Somewhere above you, one deep bell-note sounds anyway-clean, distant, and finished before an echo can form. The loose rivet drops into your palm. Quest complete: The Bell That Left. Reward: 475 XP and Silent Watch Rivet.\r\n")
            else:
                await self.send("The empty frame answers only with old timber. Whatever happened here does not repeat on demand.\r\n")
            return

        # Blue Salt Sink: intentionally not folded into the Undertide explanation.
        if room == BLUE_CHAMBER_KEY and n in {"touch blue salt", "touch salt"}:
            _start(self, BLUE_QUEST_KEY, "touch_salt")
            _advance(self, BLUE_QUEST_KEY, "touch_salt", "listen_shell")
            await self.send("The blue salt is painfully cold for one knuckle's depth and then ordinary above it, as though the sensation respects an invisible line in your finger. Loose shells lie east. Quest discovered: A Table Under Salt.\r\n")
            return
        if room == BLUE_SHELL_KEY and n in {"listen shell", "listen shells", "listen to shell"}:
            if _advance(self, BLUE_QUEST_KEY, "listen_shell", "wait_table"):
                await self.send("You hold one loose shell to your ear. One tiny wash of surf arrives. There is no second wave. South, the impossible dry table waits in the deepest pocket.\r\n")
            else:
                await self.send("The shells are quiet enough that you can hear your own pulse.\r\n")
            return
        if room == BLUE_TABLE_KEY and n in {"wait", "wait at table", "sit at table"}:
            q = _quest(self, BLUE_QUEST_KEY)
            if q and q.get("status") == "active" and q.get("current_step") == "wait_table" and _award_completion(self, BLUE_QUEST_KEY, BLUE_COMPLETE_FLAG, BLUE_SHELL_ITEM_KEY, 700):
                await self.send("You wait. No machinery starts. No voice speaks. When you finally look down, a tiny closed shell sits exactly inside the old cup ring. You are certain the tabletop was empty when you arrived. Quest complete: A Table Under Salt. Reward: 700 XP and Blue Salt Shell.\r\n")
            else:
                await self.send("You wait. The table remains a table. The first answer, if it was an answer, does not repeat.\r\n")
            return

        # Noonwatch: a human-scale wartime discovery. The lens points to a civilian
        # path, not a secret superweapon or a new layer of Dask's conspiracy.
        if room == NOON_KEEPER_KEY and n in {"read noon log", "read log"}:
            _start(self, NOON_QUEST_KEY, "read_log")
            _advance(self, NOON_QUEST_KEY, "read_log", "align_lens")
            await self.send("Every entry was made at noon because the tower used the sun itself to flash a route marker for travelers. The last page says only: IF THE ROAD CLOSES, KEEP THE LOW PATH VISIBLE. Quest discovered: Only at Noon.\r\n")
            return
        if room == NOON_LENS_KEY and n in {"align lens", "adjust lens", "turn lens"}:
            if _advance(self, NOON_QUEST_KEY, "align_lens", "look_lens"):
                await self.send("You return the sighting screw to the scratched noon mark. The frame now points toward the upper platform and a low fold in the country far below the Host roads.\r\n")
            else:
                await self.send("The lens turns, but without the log's noon mark you have no reason to prefer one bearing over another.\r\n")
            return
        if room == NOON_PLATFORM_KEY and n in {"look through lens", "use lens", "look lens"}:
            q = _quest(self, NOON_QUEST_KEY)
            if q and q.get("status") == "active" and q.get("current_step") == "look_lens" and _award_completion(self, NOON_QUEST_KEY, NOON_COMPLETE_FLAG, NOON_LENS_ITEM_KEY, 950):
                await self.send("Through the aligned lens you find no fort, officer, or hidden weapon. You find a narrow civilian footpath below every military skyline. Two people are using it now, carrying sacks toward Morrowgate. Someone kept the old lens aligned so ordinary travelers could still find the low road. Quest complete: Only at Noon. Reward: 950 XP and Noonwatch Lens.\r\n")
            else:
                await self.send("The lens shows red country and distant roads. Its useful secret has already become ordinary geography to you.\r\n")
            return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._roadside_discoveries_installed = True
