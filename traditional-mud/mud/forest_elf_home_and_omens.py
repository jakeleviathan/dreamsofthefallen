from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.forest_elf_nurture import (
    FOREST_ELF_HEARTSEED_QUEST,
    FOREST_ELF_NURTURE_COMPLETE_FLAG,
)
from mud.quests import FOREST_ELF_FIRST_WALK, QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import (
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_START_ROOM_KEY,
    NpcDefinition,
    RoomDefinition,
)


FOREST_ELF_HEARTHWALK_KEY = "forest_elf_hearthwalk"
FOREST_ELF_HUSHED_VERGE_KEY = "forest_elf_hushed_verge"

FOREST_ELF_HOME_ROUNDS_FLAG = "forest_elf_home_rounds_complete"
FOREST_ELF_MARKER_SET_FLAG = "forest_elf_home_marker_reset"
FOREST_ELF_ANOMALY_TRACKS_FLAG = "forest_elf_anomaly_tracks_noted"
FOREST_ELF_ANOMALY_BIRDS_FLAG = "forest_elf_anomaly_birds_noted"
FOREST_ELF_CIRCLE_COMPARED_FLAG = "forest_elf_anomaly_circle_compared"
FOREST_ELF_VERGE_ACCESS_FLAG = "forest_elf_hushed_verge_known"
FOREST_ELF_VERGE_STUDIED_FLAG = "forest_elf_hushed_verge_studied"
FOREST_ELF_OPENING_COMPLETE_FLAG = "forest_elf_expanded_opening_complete"
FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG = "forest_elf_expanded_opening_grandfathered"

FOREST_ELF_LENS_DRUID_FLAG = "forest_elf_verge_lens_druid"
FOREST_ELF_LENS_WIZARD_FLAG = "forest_elf_verge_lens_wizard"
FOREST_ELF_LENS_PRIEST_FLAG = "forest_elf_verge_lens_priest"
FOREST_ELF_LENS_NECROMANCER_FLAG = "forest_elf_verge_lens_necromancer"
FOREST_ELF_LENS_BRUTE_FLAG = "forest_elf_verge_lens_brute"

KEEPER_PARCEL_KEY = "forest_elf_keeper_meal_parcel"


MORNING_ALREADY_UNDERWAY = QuestDefinition(
    key="forest_elf_morning_already_underway",
    name="The Morning Already Underway",
    style="structured",
    description=(
        "Before the Circle asks anything unusual of a new Forest Elf, there is ordinary town work to do: "
        "carry a meal parcel to a water keeper, check a familiar trail marker, and help set the stones for a small Circle meeting."
    ),
    objective_steps=(
        ("talk_neris", "Go west from Circle Clearing to Hearthwalk and TALK NERIS."),
        ("deliver_parcel", "Carry Neris's parcel to Sela Rainbough on the Greenway and TALK SELA."),
        ("check_marker", "CHECK TRAIL MARKER on the Greenway."),
        ("reset_marker", "RESET TRAIL MARKER so the familiar route is clear again."),
        ("set_meeting", "Return to Circle Clearing and SET MEETING CUPS beside the seven stones."),
        ("complete", "You finished a morning round that mattered because it was ordinary and shared."),
    ),
)


QUIET_IS_DIFFERENT = QuestDefinition(
    key="forest_elf_quiet_is_different",
    name="The Quiet Is Different",
    style="structured",
    description=(
        "After learning the local paths, you notice that familiar animals are using them differently. "
        "The Circle asks for observations rather than theories, then compares several small reports before deciding anything is wrong."
    ),
    objective_steps=(
        ("inspect_tracks", "At the Outer Grove, EXAMINE HURRIED TRACKS near the boundary oak."),
        ("listen_birds", "Return south to the Listening Pool and LISTEN BIRDS."),
        ("attend_circle", "Return to Circle Clearing and ATTEND CIRCLE so the keepers can compare observations."),
        ("complete", "The Circle agrees that several ordinary patterns have shifted at the same time."),
    ),
)


ONE_TURN_FARTHER = QuestDefinition(
    key="forest_elf_one_turn_farther",
    name="One Turn Farther",
    style="structured",
    description=(
        "Pathwarden Talen Mossstep takes you beyond the familiar boundary on a narrow side path. "
        "The same disturbance presents a different clue depending on the discipline you already practice."
    ),
    objective_steps=(
        ("meet_talen", "Return to the Outer Grove and TALK TALEN."),
        ("enter_verge", "With Talen's escort, travel EAST into the Hushed Verge."),
        ("study_signs", "At the Hushed Verge, STUDY SIGNS and notice what your class training makes easiest for you to see."),
        ("report_circle", "Return to Circle Clearing and REPORT SIGNS to the Circle."),
        ("complete", "You brought back one useful piece of a larger mystery without pretending it was the whole answer."),
    ),
)


FOREST_ELF_EXPANDED_QUESTS = (
    MORNING_ALREADY_UNDERWAY,
    QUIET_IS_DIFFERENT,
    ONE_TURN_FARTHER,
)


KEEPER_PARCEL = ItemDefinition(
    key=KEEPER_PARCEL_KEY,
    name="Reed-Wrapped Keeper Parcel",
    description=(
        "A small reed-wrapped parcel holding bread, soft cheese, dried berries, and a folded note about the afternoon water checks. "
        "It is lunch and work information, not a sacred object."
    ),
    category="quest_item",
    tier=0,
)


NERIS_WILLOWHAND = NpcDefinition(
    key="forest_elf_neris_willowhand",
    name="Neris Willowhand",
    short_description="a neighborhood keeper sorting lunch parcels, mending twine, and answering three people at once",
    room_key=FOREST_ELF_HEARTHWALK_KEY,
    role="Forest Elf community steward and first ordinary-task contact",
    dialogue=(
        "Neris ties off a parcel with her teeth. 'The Circle can wait half a minute. Sela forgets lunch when the water is interesting.'",
        "'A town stays peaceful because people keep doing small things before they become large things.'",
        "'Do not confuse familiar with unimportant. Most of what keeps us alive is familiar.'",
    ),
)


TALEN_MOSSSTEP = NpcDefinition(
    key="forest_elf_pathwarden_talen_mossstep",
    name="Pathwarden Talen Mossstep",
    short_description="a weathered pathwarden with bark-scratched greaves, a short bow, and mud from trails beyond the town",
    room_key=FOREST_ELF_OUTER_GROVE_KEY,
    role="experienced Forest Elf pathwarden and supervised boundary escort",
    dialogue=(
        "Talen studies the boundary oak more often than he studies visitors. 'The useful question is not whether the forest changed. It always changes. The question is whether several changes belong to the same cause.'",
        "'Past the old oak, confidence becomes expensive. Observation is cheaper.'",
    ),
)


FOREST_ELF_EXPANDED_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=FOREST_ELF_HEARTHWALK_KEY,
        name="Hearthwalk",
        region_key="great_elf_forest",
        description=(
            "A looping wooden walk passes between low homes built around living trunks rather than over them. Open shutters face herb boxes, drying racks, and a communal clay oven whose warm stone smells faintly of bread and applewood. "
            "Children carry bundles between households while older Elves mend baskets beneath the eaves. Nothing here is ceremonial. It is simply the part of the forest town where breakfast, errands, gossip, and shared tools keep the day moving."
        ),
        exits={"east": FOREST_ELF_START_ROOM_KEY},
        npc_keys=(NERIS_WILLOWHAND.key,),
        tags=("safe", "forest_town", "homes", "community", "ordinary_life"),
    ),
    RoomDefinition(
        key=FOREST_ELF_HUSHED_VERGE_KEY,
        name="The Hushed Verge",
        region_key="great_elf_forest",
        description=(
            "A narrow side trail slips beyond the boundary oak into ground the town does not tend every day. Windthrow trunks lie where storms left them, and thorn scrub grows high enough to hide a crouched animal. "
            "The place is not cursed and not dead, but the usual scatter of small movement is missing. Fresh hoof cuts, disturbed moss, a dead shrew, and three pale stones sit within a few paces of one another like unrelated details waiting to be compared. "
            "This is the first stretch of the local forest where an inexperienced traveler is expected to have company."
        ),
        exits={"west": FOREST_ELF_OUTER_GROVE_KEY},
        tags=("forest_edge", "supervised_danger", "anomaly", "class_lens", "older_forest"),
    ),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    touch: str = "",
    listen: str = "",
    condition: ViewCondition | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
        condition=condition or ViewCondition(),
    )


def _exit(direction: str, destination: str, name: str, text: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, **kwargs)


def forest_elf_home_augmentations() -> dict[str, RoomAugmentation]:
    verge_access = ViewCondition(required_flags=(FOREST_ELF_VERGE_ACCESS_FLAG,))
    anomaly_active = ViewCondition(required_flags=("forest_elf_first_walk_completed",), forbidden_flags=(FOREST_ELF_OPENING_COMPLETE_FLAG,))
    return {
        FOREST_ELF_START_ROOM_KEY: RoomAugmentation(
            extra_exits=(
                _exit("west", FOREST_ELF_HEARTHWALK_KEY, "Hearthwalk", "You follow a short plank walk west between the homes and breakfast gardens."),
            ),
            features=(
                _feature(
                    "meeting_cups",
                    "Meeting Cups",
                    "a low shelf of plain wooden cups used whenever the local Circle sits together",
                    "The cups are mismatched, repaired, and scrubbed clean. Preparing a Circle meeting apparently involves more water, tea, and moving benches than mystical ceremony.",
                    aliases=("cups", "meeting cups", "cup shelf", "circle cups"),
                ),
                _feature(
                    "observation_slaters",
                    "Observation Slates",
                    "small waxed slates used to compare practical reports at Circle meetings",
                    "The headings are mundane: water, paths, nesting, blight, weather, injuries, stores. A blank line at the bottom is labeled THINGS THAT DO NOT FIT YET.",
                    aliases=("slates", "observation slates", "reports", "report slates"),
                ),
            ),
        ),
        FOREST_ELF_HEARTHWALK_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", FOREST_ELF_START_ROOM_KEY, "Circle Clearing", "You leave the household walk and return east toward the seven Circle stones."),
            ),
            features=(
                _feature(
                    "communal_oven",
                    "Communal Oven",
                    "a broad clay oven shared by several nearby households",
                    "Someone has chalked baking times beside the door. Loaves, root pies, and covered bean pots rotate through the same heat while neighbors trade gossip and oven space.",
                    aliases=("oven", "clay oven", "bread oven"),
                    listen="The oven itself is quiet; the bench beside it is not.",
                ),
                _feature(
                    "parcel_shelf",
                    "Parcel Shelf",
                    "a roofed shelf for lunches, notes, borrowed tools, and things headed elsewhere in town",
                    "Names are written on reusable wooden tabs. Half the parcels are food; the rest are pruning shears, copied weather notes, herb cuttings, and objects somebody promised to return yesterday.",
                    aliases=("shelf", "parcels", "parcel shelf", "lunch shelf"),
                ),
            ),
        ),
        "forest_elf_greenway": RoomAugmentation(
            features=(
                _feature(
                    "familiar_trail_marker",
                    "Familiar Trail Marker",
                    "a knee-high carved marker showing the footpath toward the town homes and the river",
                    "The marker has been here long enough for moss to soften its lower edge. One side has lifted slightly where a beech root thickened beneath it, turning the arrow a few degrees off the true path. It is a maintenance problem, not a mystery.",
                    aliases=("trail marker", "marker", "path marker", "familiar marker"),
                    touch="The marker rocks a little against the rising root. It can be reseated without cutting the root.",
                ),
            ),
        ),
        FOREST_ELF_LISTENING_POOL_KEY: RoomAugmentation(
            features=(
                _feature(
                    "willow_bird_roost",
                    "Willow Bird Roost",
                    "a familiar tangle where small river birds normally feed and call above the pool",
                    "The branches hold old nests and fresh droppings, but fewer birds are using them than the signs suggest should be here. The ones that remain keep making short contact calls toward the south instead of spreading along the river.",
                    aliases=("birds", "bird roost", "roost", "willow birds", "willows"),
                    listen="A few brief calls answer from farther south. The normal layered chatter over the pool is missing.",
                    condition=anomaly_active,
                ),
            ),
        ),
        FOREST_ELF_OUTER_GROVE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="east",
                    destination_key=FOREST_ELF_HUSHED_VERGE_KEY,
                    name="Hushed Verge",
                    travel_text="You take the narrow side path Talen showed you, beyond the boundary oak and into less-tended forest.",
                    failure_text="The side trail is not part of the beginner boundary walk. Pathwarden Talen Mossstep will take you there when the Circle decides there is a reason.",
                    condition=verge_access,
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "hurried_tracks",
                    "Hurried Tracks",
                    "several overlapping animal trails cutting toward the tended forest instead of away from it",
                    "Deer, hare, and something fox-sized have all crossed the same damp ground within a short span. None of the tracks is remarkable alone. Together, their direction is: they run south and west, toward the familiar paths and town edge.",
                    aliases=("tracks", "hurried tracks", "animal tracks", "prints", "fleeing tracks"),
                    search="Broken fern stems and displaced leaf litter confirm the movement was hurried rather than ordinary browsing.",
                    condition=anomaly_active,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "forest_elf_anomaly_outer_grove",
                    "Now that you know the boundary well enough to compare it with memory, the grove feels subtly busier in one direction and emptier in the other: small animal movement keeps favoring the townward side of the oak.",
                    priority=75,
                    condition=anomaly_active,
                ),
            ),
        ),
        FOREST_ELF_HUSHED_VERGE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", FOREST_ELF_OUTER_GROVE_KEY, "Outer Grove", "You return west to the boundary oak and the better-known path."),
            ),
            features=(
                _feature(
                    "verge_signs",
                    "Disturbance Signs",
                    "hoof cuts, bent fern, a dead shrew, snapped twigs, and pale stones occupying the same small patch",
                    "There is no single dramatic mark to explain the place. The useful evidence is distributed among living growth, physical tracks, a small death, and the strange regularity of what has been disturbed.",
                    aliases=("signs", "disturbance", "disturbance signs", "evidence", "verge signs"),
                ),
                _feature(
                    "dead_shrew",
                    "Dead Shrew",
                    "a small dead animal lying beneath fern cover without visible injury",
                    "The shrew has no obvious wound, swelling, or poison froth. Death itself is ordinary here. Its relationship to the other changes is not yet established.",
                    aliases=("shrew", "dead shrew", "body", "small body"),
                ),
                _feature(
                    "pale_stones",
                    "Three Pale Stones",
                    "three naturally pale stones exposed where the moss has been scuffed away",
                    "The stones are ordinary local rock. What is odd is that the same thin band of moss has been disturbed around each one at nearly equal spacing.",
                    aliases=("stones", "pale stones", "three stones"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "verge_druid_hint",
                    "Your Druid training keeps pulling your attention toward the living plants: several healthy leaves are behaving as though evening or cold arrived hours early.",
                    priority=65,
                    condition=ViewCondition(classes=("druid",)),
                ),
                DescriptionLayer(
                    "verge_wizard_hint",
                    "Your Wizard training makes the spacing bother you. Three otherwise ordinary points in the clearing carry a faint, repeated magical regularity that wild growth rarely produces by accident.",
                    priority=65,
                    condition=ViewCondition(classes=("wizard",)),
                ),
                DescriptionLayer(
                    "verge_priest_hint",
                    "Your Priest training notices a quality harder to name than sound: the small practiced sense of response that usually accompanies your road rites feels strangely absent here.",
                    priority=65,
                    condition=ViewCondition(classes=("priest",)),
                ),
                DescriptionLayer(
                    "verge_necromancer_hint",
                    "Your Necromancer training keeps returning to the dead shrew. Nothing has animated it, but the faint boundary between recent life and settled death seems to be lingering longer than it should.",
                    priority=65,
                    condition=ViewCondition(classes=("necromancer",)),
                ),
                DescriptionLayer(
                    "verge_brute_hint",
                    "Your Brute training reads force before mystery: the snapped twigs, deep hoof cuts, and shoulder-height bark rubs all agree that several animals moved hard in the same townward direction.",
                    priority=65,
                    condition=ViewCondition(classes=("brute",)),
                ),
            ),
        ),
    }


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    override_by_direction = {value.direction: value for value in existing.exit_overrides}
    for value in extra.exit_overrides:
        override_by_direction[value.direction] = value
    extra_by_route = {(value.direction, value.destination_key): value for value in existing.extra_exits}
    for value in extra.extra_exits:
        extra_by_route[(value.direction, value.destination_key)] = value
    features = {value.key: value for value in existing.features}
    for value in extra.features:
        features[value.key] = value
    layers = {value.key: value for value in existing.description_layers}
    for value in extra.description_layers:
        layers[value.key] = value
    return RoomAugmentation(
        exit_overrides=tuple(override_by_direction.values()),
        extra_exits=tuple(extra_by_route.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


def _patch_room(room_key: str, *, exits: dict[str, str] | None = None, npc_keys: tuple[str, ...] = ()) -> None:
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is None:
        return
    merged_exits = dict(room.exits)
    if exits:
        merged_exits.update(exits)
    merged_npcs = room.npc_keys + tuple(key for key in npc_keys if key not in room.npc_keys)
    replacement = replace(room, exits=merged_exits, npc_keys=merged_npcs)
    legacy_world.ROOMS = tuple(replacement if value.key == room_key else value for value in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY[room_key] = replacement


def install_forest_elf_home_content(world_service=None) -> None:
    """Register the expanded Forest Elf home, anomaly, and class-lens opening."""
    for definition in FOREST_ELF_EXPANDED_QUESTS:
        if definition.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (definition,)
        quests.QUESTS_BY_KEY[definition.key] = definition

    if KEEPER_PARCEL.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (KEEPER_PARCEL,)
    crafting.ITEMS_BY_KEY[KEEPER_PARCEL.key] = KEEPER_PARCEL

    for npc in (NERIS_WILLOWHAND, TALEN_MOSSSTEP):
        if npc.key not in legacy_world.NPCS_BY_KEY:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    known_rooms = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in FOREST_ELF_EXPANDED_ROOMS if room.key not in known_rooms)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    legacy_world.ROOMS_BY_KEY.update({room.key: room for room in FOREST_ELF_EXPANDED_ROOMS})

    _patch_room(FOREST_ELF_START_ROOM_KEY, exits={"west": FOREST_ELF_HEARTHWALK_KEY})
    _patch_room(
        FOREST_ELF_OUTER_GROVE_KEY,
        exits={"east": FOREST_ELF_HUSHED_VERGE_KEY},
        npc_keys=(TALEN_MOSSSTEP.key,),
    )

    if world_service is not None:
        for room_key in (FOREST_ELF_START_ROOM_KEY, FOREST_ELF_OUTER_GROVE_KEY):
            room = legacy_world.ROOMS_BY_KEY.get(room_key)
            if room is not None:
                world_service.legacy_rooms[room_key] = room
        world_service.legacy_rooms.update({room.key: room for room in FOREST_ELF_EXPANDED_ROOMS})
        for room_key, augmentation in forest_elf_home_augmentations().items():
            world_service.augmentations[room_key] = _merge_augmentation(
                world_service.augmentations.get(room_key), augmentation
            )
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in (
                FOREST_ELF_START_ROOM_KEY,
                FOREST_ELF_HEARTHWALK_KEY,
                "forest_elf_greenway",
                FOREST_ELF_LISTENING_POOL_KEY,
                FOREST_ELF_OUTER_GROVE_KEY,
                FOREST_ELF_HUSHED_VERGE_KEY,
            ):
                cache.pop(room_key, None)


def _quest(session, definition: QuestDefinition):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, definition.key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _ensure_one(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity == 0:
        session.database.add_item(session.character.id, item_key, 1)
    elif quantity > 1:
        session.database.consume_item(session.character.id, item_key, quantity - 1)


def _consume_all(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _fresh_untouched_forest_elf(session) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    first_walk = session.database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)
    heartseed = session.database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
    home = _quest(session, MORNING_ALREADY_UNDERWAY)
    flags = _flags(session)
    return bool(
        home is None
        and heartseed is None
        and first_walk is not None
        and first_walk.get("status") == "active"
        and first_walk.get("current_step") == "leave_clearing"
        and "forest_elf_first_walk_completed" not in flags
        and FOREST_ELF_NURTURE_COMPLETE_FLAG not in flags
    )


def _prepare_fresh_opening(session) -> bool:
    if not _fresh_untouched_forest_elf(session):
        return False
    assert session.character is not None
    character_id = session.character.id
    session.database.advance_quest(character_id, FOREST_ELF_FIRST_WALK.key, "await_home_rounds")
    session.database.start_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key, "await_home_rounds")
    session.database.start_quest(character_id, MORNING_ALREADY_UNDERWAY.key, "talk_neris")
    _consume_all(session, KEEPER_PARCEL_KEY)
    return True


def _grandfather_if_needed(session) -> None:
    if session.character is None or session.character.race != "forest_elf":
        return
    if _quest(session, MORNING_ALREADY_UNDERWAY) is not None:
        return
    if FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG in _flags(session):
        return
    first_walk = session.database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)
    heartseed = session.database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
    if first_walk is not None or heartseed is not None:
        session.database.grant_flag(session.character.id, FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG)


def _current_objective(session) -> str | None:
    for definition in (MORNING_ALREADY_UNDERWAY, QUIET_IS_DIFFERENT, ONE_TURN_FARTHER):
        state = _quest(session, definition)
        if state and state.get("status") == "active":
            return definition.objective_for_step(state.get("current_step"))
    heartseed = session.database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key) if session.character else None
    if heartseed and heartseed.get("status") == "active" and heartseed.get("current_step") != "await_home_rounds":
        return FOREST_ELF_HEARTSEED_QUEST.objective_for_step(heartseed.get("current_step"))
    first_walk = session.database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key) if session.character else None
    if first_walk and first_walk.get("status") == "active" and first_walk.get("current_step") != "await_home_rounds":
        return FOREST_ELF_FIRST_WALK.objective_for_step(first_walk.get("current_step"))
    return None


def reconcile_forest_elf_expanded_opening(session) -> str | None:
    """Keep the expanded opening sequenced around the two older Forest Elf lessons."""
    if session.character is None or session.character.race != "forest_elf":
        return None
    flags = _flags(session)
    if FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG in flags:
        return None
    home = _quest(session, MORNING_ALREADY_UNDERWAY)
    if home is None:
        return None

    character_id = session.character.id
    if home.get("status") == "active":
        if home.get("current_step") == "deliver_parcel":
            _ensure_one(session, KEEPER_PARCEL_KEY)
        return None

    session.database.grant_flag(character_id, FOREST_ELF_HOME_ROUNDS_FLAG)
    _consume_all(session, KEEPER_PARCEL_KEY)
    heartseed = session.database.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)
    if heartseed is not None and heartseed.get("status") == "active" and heartseed.get("current_step") == "await_home_rounds":
        session.database.advance_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key, "speak_keeper")
        return "heartseed_started"
    if heartseed is None or heartseed.get("status") != "completed":
        return None

    first_walk = session.database.get_quest(character_id, FOREST_ELF_FIRST_WALK.key)
    if first_walk is not None and first_walk.get("status") == "active" and first_walk.get("current_step") == "await_home_rounds":
        session.database.advance_quest(character_id, FOREST_ELF_FIRST_WALK.key, "leave_clearing")
        return "first_walk_started"
    if first_walk is None or first_walk.get("status") != "completed":
        return None

    anomaly = _quest(session, QUIET_IS_DIFFERENT)
    if anomaly is None:
        session.database.start_quest(character_id, QUIET_IS_DIFFERENT.key, "inspect_tracks")
        return "anomaly_started"
    if anomaly.get("status") != "completed":
        return None

    final = _quest(session, ONE_TURN_FARTHER)
    if final is None:
        session.database.start_quest(character_id, ONE_TURN_FARTHER.key, "meet_talen")
        return "final_started"
    if final.get("status") == "completed":
        session.database.grant_flag(character_id, FOREST_ELF_OPENING_COMPLETE_FLAG)
        return "complete"
    return None


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches(target: str, *names: str) -> bool:
    return target in {name.lower() for name in names}


async def _talk_neris(session) -> bool:
    quest = _quest(session, MORNING_ALREADY_UNDERWAY)
    if not quest or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != FOREST_ELF_HEARTHWALK_KEY:
        await session.send("Neris Willowhand is on Hearthwalk, west of Circle Clearing.\r\n")
        return True
    if quest.get("current_step") != "talk_neris":
        objective = MORNING_ALREADY_UNDERWAY.objective_for_step(quest.get("current_step"))
        await session.send("\r\nNeris keeps sorting the morning parcels.\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True
    _ensure_one(session, KEEPER_PARCEL_KEY)
    session.database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "deliver_parcel")
    await session.send(
        "\r\nNeris presses a reed-wrapped parcel into your hands. It smells like bread, berries, and ordinary responsibility.\r\n"
        "'Sela Rainbough is on the Greenway staring at water again. Take her lunch before she decides noon is a theory.'\r\n"
        "You receive a Reed-Wrapped Keeper Parcel. Take it to the Greenway and TALK SELA.\r\n"
    )
    return True


async def _deliver_sela(session) -> bool:
    quest = _quest(session, MORNING_ALREADY_UNDERWAY)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "deliver_parcel":
        return False
    assert session.character is not None
    if session.character.current_room != "forest_elf_greenway":
        return False
    _consume_all(session, KEEPER_PARCEL_KEY)
    session.database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "check_marker")
    await session.send(
        "\r\nSela accepts the parcel with the guilty expression of someone who had, in fact, forgotten lunch.\r\n"
        "'Tell Neris I was going to remember.' She looks at the bread, then decides not to insult either of you with the lie.\r\n"
        "Before sitting down, she points at a familiar knee-high trail marker near the beech roots. 'That one shifted after the last root swell. CHECK TRAIL MARKER while you're here. It should still point cleanly toward the river.'\r\n"
    )
    return True


async def _handle_home_actions(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session, MORNING_ALREADY_UNDERWAY)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == "forest_elf_greenway" and normalized in {
        "check trail marker", "examine trail marker", "look trail marker", "check marker", "examine marker", "inspect marker"
    }:
        if step == "check_marker":
            session.database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "reset_marker")
        await session.send(
            "\r\nThe marker has not been vandalized and the trail has not moved. A growing beech root simply lifted one edge of the stone and turned the arrow a little. The root is healthy. You can correct the marker without cutting it. RESET TRAIL MARKER.\r\n"
        )
        return True

    if room == "forest_elf_greenway" and normalized in {
        "reset trail marker", "reset marker", "set trail marker", "straighten marker", "reseat marker"
    }:
        if step != "reset_marker":
            await session.send("\r\nCheck the marker before changing it. Familiar things deserve observation too.\r\n")
            return True
        session.database.grant_flag(session.character.id, FOREST_ELF_MARKER_SET_FLAG)
        session.database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "set_meeting")
        await session.send(
            "\r\nYou lift the marker just enough to pack leaf mold beneath the low side, leaving the living beech root untouched. The arrow settles back toward the river path.\r\n"
            "One tiny maintenance job is finished. Return to Circle Clearing and SET MEETING CUPS beside the seven stones.\r\n"
        )
        return True

    if room == FOREST_ELF_START_ROOM_KEY and normalized in {
        "set meeting cups", "set cups", "prepare meeting", "prepare circle", "arrange cups", "set circle cups"
    }:
        if step != "set_meeting":
            await session.send("\r\nThe Circle meeting is later. Finish the small errand already in your hands first.\r\n")
            return True
        session.database.complete_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key)
        session.database.grant_flag(session.character.id, FOREST_ELF_HOME_ROUNDS_FLAG)
        await session.send(
            "\r\nYou set water and plain wooden cups beside the seven weathered stones, move one low bench out of the damp, and leave the rest alone. No chant announces that the room is ready. It simply is.\r\n"
            "Quest complete: The Morning Already Underway.\r\n"
            "Maelis Fernward is nearby with a stressed Heartseed cutting. TALK MAELIS when you are ready for the next ordinary piece of Circle work.\r\n"
        )
        reconcile_forest_elf_expanded_opening(session)
        return True

    return False


async def _handle_anomaly_actions(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session, QUIET_IS_DIFFERENT)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == FOREST_ELF_OUTER_GROVE_KEY and normalized in {
        "examine hurried tracks", "look hurried tracks", "examine tracks", "look tracks", "inspect tracks", "examine animal tracks"
    }:
        if step == "inspect_tracks":
            session.database.grant_flag(session.character.id, FOREST_ELF_ANOMALY_TRACKS_FLAG)
            session.database.advance_quest(session.character.id, QUIET_IS_DIFFERENT.key, "listen_birds")
        await session.send(
            "\r\nYou compare the impressions instead of treating them as one trail. Deer, hare, and a fox-sized animal all moved through recently, and all of them favored the same direction: back toward the tended forest. Nothing here proves why. It is only the first fact.\r\n"
            "Return south to the Listening Pool and LISTEN BIRDS.\r\n"
        )
        return True

    if room == FOREST_ELF_LISTENING_POOL_KEY and normalized in {
        "listen birds", "listen to birds", "listen roost", "listen bird roost", "listen willow birds"
    }:
        if step != "listen_birds":
            return False
        session.database.grant_flag(session.character.id, FOREST_ELF_ANOMALY_BIRDS_FLAG)
        session.database.advance_quest(session.character.id, QUIET_IS_DIFFERENT.key, "attend_circle")
        await session.send(
            "\r\nYou stop trying to hear one special sound and notice the missing layers instead. The pool still has birds, but fewer than the nests suggest, and the ones that remain keep answering southward. Like the tracks, the pattern leans toward town.\r\n"
            "Two small observations are enough to report, not enough to explain. Return to Circle Clearing and ATTEND CIRCLE.\r\n"
        )
        return True

    if room == FOREST_ELF_START_ROOM_KEY and normalized in {
        "attend circle", "attend meeting", "join circle", "sit circle", "share observations", "report observations"
    }:
        if step != "attend_circle":
            await session.send("\r\nThe Circle would rather hear observations after you have actually made them.\r\n")
            return True
        session.database.grant_flag(session.character.id, FOREST_ELF_CIRCLE_COMPARED_FLAG)
        session.database.complete_quest(session.character.id, QUIET_IS_DIFFERENT.key)
        session.database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "meet_talen")
        await session.send(
            "\r\nThe meeting is small: Maelis, Sela, two household keepers, a beekeeper, and Pathwarden Talen Mossstep around seven old stones with the cups you set earlier.\r\n"
            "Nobody asks for a theory first. The reports go around in order. You give the townward animal tracks and the thinned bird calls. The beekeeper reports that two hives changed their flight line. Sela reports frogs leaving one upper pool despite normal water. Talen reports no storm damage and no known predator moving through the usual corridor.\r\n"
            "The Circle does not declare a curse, invasion, or prophecy. Maelis writes all five observations under THINGS THAT DO NOT FIT YET.\r\n"
            "Talen says, 'There is a side turn past the boundary oak. New walkers do not take it alone. I do. Come with me and we will see whether the pattern continues.'\r\n"
            "Quest complete: The Quiet Is Different.\r\n"
            "New quest: One Turn Farther. Return to the Outer Grove and TALK TALEN.\r\n"
        )
        return True

    return False


def _class_lens(character_class: str) -> tuple[str, str]:
    mapping = {
        "druid": (
            FOREST_ELF_LENS_DRUID_FLAG,
            "Your Druid training keeps you with the living growth. Several healthy plants have drawn moisture inward and partly closed their leaves as though dusk, frost, or hard weather were already arriving. They are not diseased. Their timing is wrong. Whatever disturbed the animals may also be touching the forest's ordinary rhythms.",
        ),
        "wizard": (
            FOREST_ELF_LENS_WIZARD_FLAG,
            "Your Wizard training makes the three pale stones impossible to dismiss as coincidence. The magic around them is faint, but it rises and falls at nearly equal intervals from point to point. Wild forest magic overlaps, wanders, and frays. This residue repeats. You cannot yet tell whether it is a spell, a device, or an aftereffect.",
        ),
        "priest": (
            FOREST_ELF_LENS_PRIEST_FLAG,
            "Your Priest training gives you a different absence to report. You speak the small road rite you have used in ordinary travel before. The words are yours and nothing prevents them, but the familiar sense of response does not settle over this patch of ground. It feels less like refusal than a space where the usual echo has been muffled.",
        ),
        "necromancer": (
            FOREST_ELF_LENS_NECROMANCER_FLAG,
            "Your Necromancer training turns the dead shrew from scenery into evidence. It has not risen, twitched, or been worked by a visible binding. The oddity is subtler: the residue of recent life is lingering at the edge of death longer than your training says it should. Something here may be delaying a transition rather than reversing it.",
        ),
        "brute": (
            FOREST_ELF_LENS_BRUTE_FLAG,
            "Your Brute training reads the physical story first. Deep hoof cuts, snapped stems, bark rubbed at shoulder height, and compressed mud all show acceleration in the same direction. Different animals did not wander toward town independently; they fled hard from somewhere deeper east and north. Whatever else is happening, the fear had a direction.",
        ),
    }
    return mapping.get(
        character_class,
        (
            FOREST_ELF_VERGE_STUDIED_FLAG,
            "You compare the signs carefully and refuse to force them into one explanation. The useful fact is that several different systems here changed at once.",
        ),
    )


async def _talk_talen(session) -> bool:
    quest = _quest(session, ONE_TURN_FARTHER)
    if not quest or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != FOREST_ELF_OUTER_GROVE_KEY:
        await session.send("Pathwarden Talen Mossstep is waiting at the boundary oak in the Outer Grove.\r\n")
        return True
    if quest.get("current_step") != "meet_talen":
        objective = ONE_TURN_FARTHER.objective_for_step(quest.get("current_step"))
        await session.send("\r\nTalen checks the side trail and waits for you to finish looking rather than filling the silence.\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True
    session.database.grant_flag(session.character.id, FOREST_ELF_VERGE_ACCESS_FLAG)
    session.database.advance_quest(session.character.id, ONE_TURN_FARTHER.key, "enter_verge")
    await session.send(
        "\r\nTalen checks your pack, the sky, and the wind with equal seriousness. 'This is not a bravery test. If something large moves, we leave. If something strange appears, we look before naming it.'\r\n"
        "He steps onto the narrow side trail. 'East. Stay close enough that I do not have to wonder whether the silence behind me is you thinking.'\r\n"
        "The Hushed Verge is now accessible EAST from the Outer Grove.\r\n"
    )
    return True


async def _handle_final_actions(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session, ONE_TURN_FARTHER)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == FOREST_ELF_HUSHED_VERGE_KEY and step == "enter_verge":
        session.database.advance_quest(session.character.id, ONE_TURN_FARTHER.key, "study_signs")
        step = "study_signs"
        await session.send(
            "\r\nTalen stops where the side trail widens by three pale stones. 'This is far enough for a first look. Nothing here gets better because we walk another hundred paces without understanding these hundred.'\r\n"
            "STUDY SIGNS. Your class training may make one part of the disturbance easier to notice than the others.\r\n"
        )

    if room == FOREST_ELF_HUSHED_VERGE_KEY and normalized in {
        "study signs", "study disturbance", "read signs", "examine signs", "inspect signs", "study evidence"
    }:
        if step != "study_signs":
            return False
        flag, text = _class_lens(session.character.character_class or "")
        session.database.grant_flag(session.character.id, flag)
        session.database.grant_flag(session.character.id, FOREST_ELF_VERGE_STUDIED_FLAG)
        session.database.advance_quest(session.character.id, ONE_TURN_FARTHER.key, "report_circle")
        await session.send(
            "\r\n" + text + "\r\n\r\n"
            "Talen listens without trying to translate your discipline into his own. 'Good. One useful fact. Do not turn it into five facts because you want the answer early.'\r\n"
            "Return to Circle Clearing and REPORT SIGNS.\r\n"
        )
        return True

    if room == FOREST_ELF_START_ROOM_KEY and normalized in {
        "report signs", "report verge", "report to circle", "share signs", "report disturbance"
    }:
        if step != "report_circle":
            await session.send("\r\nThe Circle is waiting for what you actually observed beyond the boundary, not a guess made from home.\r\n")
            return True
        session.database.complete_quest(session.character.id, ONE_TURN_FARTHER.key)
        session.database.grant_flag(session.character.id, FOREST_ELF_OPENING_COMPLETE_FLAG)
        await session.send(
            "\r\nYou give the Circle exactly what you found and exactly what your training made easiest to notice. Nobody asks you to make the observations agree yet. Maelis adds yours to the bottom of the slate and leaves space beneath it.\r\n"
            "'A place can be home and still surprise us,' she says. 'Belonging does not mean assuming you already know it.'\r\n"
            "Talen adds, 'And now you know the difference between the path we tend, the boundary we watch, and the forest that owes us neither comfort nor explanation.'\r\n"
            "Quest complete: One Turn Farther.\r\n"
            "The first Forest Elf opening is complete. The disturbance remains an open thread for later stories rather than a solved beginner mystery.\r\n"
        )
        return True

    return False


async def _show_home_record(session) -> None:
    if session.character is None:
        return
    await session.send("\r\n--- Forest Elf Opening ---\r\n")
    if FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG in _flags(session):
        await session.send("This character predates the expanded home-and-omens opening; existing progress was preserved.\r\n")
        return
    for definition in (MORNING_ALREADY_UNDERWAY, FOREST_ELF_HEARTSEED_QUEST, FOREST_ELF_FIRST_WALK, QUIET_IS_DIFFERENT, ONE_TURN_FARTHER):
        state = session.database.get_quest(session.character.id, definition.key)
        if state is None:
            continue
        status = str(state.get("status") or "").upper()
        await session.send(f"{definition.name}: {status}.\r\n")
        if state.get("status") == "active":
            objective = definition.objective_for_step(state.get("current_step"))
            if objective:
                await session.send(f"  {objective}\r\n")
    if FOREST_ELF_OPENING_COMPLETE_FLAG in _flags(session):
        await session.send("Expanded opening: COMPLETE. The Hushed Verge remains known to you.\r\n")


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


async def _announce_transition(session, transition: str | None) -> None:
    if transition == "heartseed_started":
        await session.send(
            "\r\nThe morning errands are done. Maelis Fernward now has a small tending lesson ready in Circle Clearing. TALK MAELIS.\r\n"
        )
    elif transition == "first_walk_started":
        await session.send(
            "\r\nWith the Heartseed restored, Maelis points north. The old boundary walk is ready now: leave Circle Clearing NORTH and follow the Greenway toward the Old River Path.\r\n"
        )
    elif transition == "anomaly_started":
        await session.send(
            "\r\nAt the boundary oak, something feels different only because you have finally learned what ordinary looks like here. Several fresh animal trails run toward the tended forest.\r\n"
            "New quest: The Quiet Is Different. EXAMINE HURRIED TRACKS.\r\n"
        )
    elif transition == "final_started":
        await session.send(
            "\r\nThe Circle has compared the reports. Pathwarden Talen Mossstep is waiting at the Outer Grove for the supervised side route.\r\n"
        )


def install_forest_elf_home_runtime(player_session_class, world_service) -> None:
    install_forest_elf_home_content(world_service)
    if getattr(player_session_class, "_forest_elf_home_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        started_fresh = False
        if self.character is not None and self.character.race == "forest_elf":
            started_fresh = _prepare_fresh_opening(self)
            if not started_fresh:
                _grandfather_if_needed(self)
        await previous_enter_character(self)
        if self.character is None or self.character.race != "forest_elf":
            return
        transition = reconcile_forest_elf_expanded_opening(self)
        if started_fresh:
            await self.send(
                "\r\nThe forest town is already awake around you. Bread is coming out of the communal oven, somebody is arguing about a borrowed pruning knife, and the local Circle has not begun its meeting because there is no reason to hurry it.\r\n"
                "Neris Willowhand has the first ordinary errand of your morning.\r\n"
                "New quest: The Morning Already Underway. Go WEST to Hearthwalk and TALK NERIS.\r\n"
            )
        else:
            await _announce_transition(self, transition)
            objective = _current_objective(self)
            if objective and FOREST_ELF_OPENING_COMPLETE_FLAG not in _flags(self):
                await self.send(f"\r\nForest Elf opening objective: {objective}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "forest_elf":
            await previous_playing_prompt(self)
            return

        transition = reconcile_forest_elf_expanded_opening(self)
        await _announce_transition(self, transition)

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"home", "forest opening", "elf opening", "circle record", "opening"}:
            await _show_home_record(self)
            return

        if await _handle_home_actions(self, normalized):
            return
        if await _handle_anomaly_actions(self, normalized):
            return
        if await _handle_final_actions(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            home = _quest(self, MORNING_ALREADY_UNDERWAY)
            if home and home.get("status") == "active":
                if _matches(target, "neris", "neris willowhand", "willowhand", "community keeper"):
                    if await _talk_neris(self):
                        return
                if _matches(target, "sela", "sela rainbough", "keeper sela", "water keeper", "water-keeper"):
                    if await _deliver_sela(self):
                        return
                if _matches(target, "maelis", "maelis fernward", "keeper maelis"):
                    await self.send("\r\nMaelis gestures toward the household work already underway. 'The Heartseed can wait until you finish the morning round in front of you.'\r\n")
                    return
            final = _quest(self, ONE_TURN_FARTHER)
            if final and final.get("status") == "active" and _matches(
                target, "talen", "talen mossstep", "pathwarden", "pathwarden talen"
            ):
                if await _talk_talen(self):
                    return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if self.character is None or self.character.race != "forest_elf":
            return
        transition = reconcile_forest_elf_expanded_opening(self)
        await _announce_transition(self, transition)

        # Movement into the new verge advances the final quest after the room
        # runtime has actually allowed and completed the travel.
        final = _quest(self, ONE_TURN_FARTHER)
        if (
            final
            and final.get("status") == "active"
            and final.get("current_step") == "enter_verge"
            and self.character.current_room == FOREST_ELF_HUSHED_VERGE_KEY
        ):
            session_transition = await _handle_final_actions(self, "")
            if session_transition:
                return

        if normalized in {"help", "?"} and FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG not in _flags(self):
            await self.send(
                "Forest Elf opening: HOME reviews the current sequence. The new home round uses TALK NERIS, TALK SELA, CHECK TRAIL MARKER, RESET TRAIL MARKER, and SET MEETING CUPS. After the existing Heartseed and Old River Path lessons, the omen thread uses EXAMINE HURRIED TRACKS, LISTEN BIRDS, ATTEND CIRCLE, TALK TALEN, STUDY SIGNS, and REPORT SIGNS.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_home_runtime_installed = True
