from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


HUMAN_HALL_OF_NAMES_KEY = "human_cathedral_hall_of_names"
HUMAN_MERCY_CLOISTER_KEY = "human_cathedral_mercy_cloister"
HUMAN_CROSSING_CHAPEL_KEY = "human_cathedral_crossing_chapel"

HUMAN_CATHEDRAL_ROOM_KEYS = (
    HUMAN_HALL_OF_NAMES_KEY,
    HUMAN_MERCY_CLOISTER_KEY,
    HUMAN_CROSSING_CHAPEL_KEY,
)

HUMAN_KEPT_NAME_QUEST_KEY = "human_cathedral_kept_name"
HUMAN_OPEN_DOOR_QUEST_KEY = "human_cathedral_open_door"
HUMAN_BELLS_QUEST_KEY = "human_cathedral_bells_for_living"

HUMAN_KEPT_NAME_COMPLETE_FLAG = "human_cathedral_kept_name_complete"
HUMAN_OPEN_DOOR_COMPLETE_FLAG = "human_cathedral_open_door_complete"
HUMAN_BELLS_COMPLETE_FLAG = "human_cathedral_bells_for_living_complete"
HUMAN_CATHEDRAL_NAME_LITANY_FLAG = "human_cathedral_name_litany_read"
HUMAN_CATHEDRAL_CROSSING_LAMP_FLAG = "human_cathedral_crossing_lamp_lit"
HUMAN_CATHEDRAL_DEACON_HEARD_FLAG = "human_cathedral_deacon_heard"
HUMAN_CATHEDRAL_BREAD_SERVED_FLAG = "human_cathedral_bread_served"
HUMAN_CATHEDRAL_OUTSIDER_ANSWER_FLAG = "human_cathedral_outsider_answered"
HUMAN_CATHEDRAL_OUTSIDER_PATIENCE_FLAG = "human_cathedral_answer_patience"
HUMAN_CATHEDRAL_OUTSIDER_PRIDE_FLAG = "human_cathedral_answer_pride"
HUMAN_CATHEDRAL_OUTSIDER_SILENCE_FLAG = "human_cathedral_answer_silence"
HUMAN_CATHEDRAL_VIGIL_LIT_FLAG = "human_cathedral_vigil_lit"
HUMAN_CATHEDRAL_VIGIL_BELL_FLAG = "human_cathedral_vigil_bell_rung"
HUMAN_CATHEDRAL_GRANDFATHERED_NAME_FLAG = "human_cathedral_kept_name_grandfathered"
HUMAN_CATHEDRAL_GRANDFATHERED_DOOR_FLAG = "human_cathedral_open_door_grandfathered"

DEACON_MERET_VALE_KEY = "human_deacon_meret_vale"
DORNA_IRONSTEP_KEY = "human_dwarf_dorna_ironstep"


HUMAN_KEPT_NAME_QUEST = QuestDefinition(
    key=HUMAN_KEPT_NAME_QUEST_KEY,
    name="The Name We Keep",
    style="structured",
    description=(
        "The High Acolyte does not answer the world's name for Humans with denial or anger. "
        "Instead, the cathedral asks a new Human to learn a central teaching: fear may give a people a name, "
        "but it cannot decide the worth of a soul."
    ),
    objective_steps=(
        ("read_litany", "Go EAST from the Grand Cathedral into the Hall of Names and READ LITANY."),
        ("light_crossing_lamp", "Return to the nave, go NORTH into the Crossing Chapel, and LIGHT LAMP."),
        ("return_acolyte", "Return SOUTH to the Grand Cathedral and TALK HIGH ACOLYTE."),
        ("complete", "You learned the cathedral's first answer to the name Demon."),
    ),
)

HUMAN_OPEN_DOOR_QUEST = QuestDefinition(
    key=HUMAN_OPEN_DOOR_QUEST_KEY,
    name="An Open Door",
    style="structured",
    description=(
        "After the combat lesson, the High Acolyte sends you to the Mercy Cloister. The lesson is deliberately ordinary: "
        "a faith that reassures Humans about their own dignity must also practice hospitality toward people who are still afraid of them."
    ),
    objective_steps=(
        ("meet_deacon", "Go WEST from the Grand Cathedral into the Mercy Cloister and TALK DEACON."),
        ("serve_bread", "SERVE BREAD at the cloister table."),
        ("answer_pilgrim", "Answer the wary outsider: ANSWER PATIENCE, ANSWER PRIDE, or ANSWER SILENCE."),
        ("return_acolyte", "Return EAST to the Grand Cathedral and TALK HIGH ACOLYTE."),
        ("complete", "You served someone who did not yet fully trust the people serving them."),
    ),
)

HUMAN_BELLS_QUEST = QuestDefinition(
    key=HUMAN_BELLS_QUEST_KEY,
    name="What the Bells Are For",
    style="structured",
    description=(
        "After the Lower Wards investigation, the High Acolyte turns discovery back into religious duty. "
        "The cathedral does not exist merely to tell Humans that they are good; it exists to remember the harmed, "
        "call attention to danger, and keep compassion attached to truth."
    ),
    objective_steps=(
        ("light_vigil", "Go NORTH from the Grand Cathedral into the Crossing Chapel and LIGHT VIGIL."),
        ("ring_bell", "RING VIGIL BELL for the living people affected by what was hidden below the city."),
        ("return_acolyte", "Return SOUTH and TALK HIGH ACOLYTE."),
        ("complete", "You learned what the cathedral believes its bells are for."),
    ),
)

HUMAN_CATHEDRAL_QUESTS = (
    HUMAN_KEPT_NAME_QUEST,
    HUMAN_OPEN_DOOR_QUEST,
    HUMAN_BELLS_QUEST,
)


HIGH_ACOLYTE_RELIGIOUS = NpcDefinition(
    key="human_high_acolyte",
    name="High Acolyte",
    short_description="a senior cleric in dark vestments whose calm attention makes the immense nave feel briefly smaller",
    room_key="human_grand_cathedral",
    role="religious mentor, keeper of Human dignity, and cathedral quest guide",
    dialogue=(
        "The High Acolyte folds their hands. 'The world has called us Demons longer than anyone living remembers. The cathedral does not answer by pretending the word was never spoken.'",
        "'A name given in fear can become history. It cannot become a verdict on a soul.'",
        "'You are not a monster because a stranger needs time to stop seeing one. Nor are you virtuous merely because you are Human. What you do still matters.'",
    ),
)

DEACON_MERET_VALE = NpcDefinition(
    key=DEACON_MERET_VALE_KEY,
    name="Deacon Meret Vale",
    short_description="a broad-shouldered Human deacon portioning bread and stew with the concentration of a bookkeeper",
    room_key=HUMAN_MERCY_CLOISTER_KEY,
    role="cathedral almoner and hospitality teacher",
    dialogue=(
        "Meret sets another bowl on the long table. 'Sanctuary offered only to people who already trust us would be vanity with a roof.'",
        "'Feed the person in front of you. Let trust arrive on its own legs.'",
    ),
)

DORNA_IRONSTEP = NpcDefinition(
    key=DORNA_IRONSTEP_KEY,
    name="Dorna Ironstep",
    short_description="a travel-worn Dwarven drover keeping her pack close even while accepting the cloister's warmth",
    room_key=HUMAN_MERCY_CLOISTER_KEY,
    role="wary outsider pilgrim and small test of cathedral hospitality",
    dialogue=(
        "Dorna glances up at the horned arches. 'First Demon cathedral I've ever sat inside. I expected more fire.'",
        "She gives the room another careful look. 'Bread is bread, though. I can start there.'",
    ),
)

HUMAN_CATHEDRAL_NPCS = (HIGH_ACOLYTE_RELIGIOUS, DEACON_MERET_VALE, DORNA_IRONSTEP)


HUMAN_CATHEDRAL_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=HUMAN_HALL_OF_NAMES_KEY,
        name="Hall of Names",
        region_key="human_kingdom",
        description=(
            "A long side hall runs beneath ribbed black stone and narrow violet windows. Thousands of names are cut into pale tablets: births, marriages, "
            "adoptions, vows, deaths, and names restored after war or disaster. At the center stands a waist-high lectern bearing the Litany of the Kept Name. "
            "Nothing here asks whether the outside world considered the people on the walls beautiful, frightening, holy, or strange. It records that they lived and were known."
        ),
        exits={"west": "human_grand_cathedral"},
        tags=("cathedral", "religion", "human_identity", "litany", "safe"),
    ),
    RoomDefinition(
        key=HUMAN_MERCY_CLOISTER_KEY,
        name="Mercy Cloister",
        region_key="human_kingdom",
        description=(
            "An open-sided cloister wraps a warm kitchen court. Black-robed clerics work beside lay volunteers at long tables of bread, stew, bandages, blankets, "
            "and road water. Humans are not the only people here. A Dwarven drover eats near the wall while two other travelers linger close to the exit, accepting help without quite relaxing. "
            "No sermon is required before a bowl is filled."
        ),
        exits={"east": "human_grand_cathedral"},
        npc_keys=(DEACON_MERET_VALE_KEY, DORNA_IRONSTEP_KEY),
        tags=("cathedral", "religion", "hospitality", "outsiders", "safe"),
    ),
    RoomDefinition(
        key=HUMAN_CROSSING_CHAPEL_KEY,
        name="Crossing Chapel",
        region_key="human_kingdom",
        description=(
            "A smaller chapel rises behind the cathedral crossing. Its altar is plain black stone surrounded by tiers of low lamps. Some memorial tablets are centuries old and marked only with family names; "
            "others bear careful notes that a person or object came from Earth. Above them hangs no map home, only a carved arch opening onto a field of stars. A thick vigil-bell rope descends beside the lamps."
        ),
        exits={"south": "human_grand_cathedral"},
        tags=("cathedral", "religion", "earth_memory", "vigil", "safe"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(key=key, name=name, aliases=aliases, summary=summary, examine_text=examine)


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _layer(key: str, text: str, *, priority: int = 50) -> DescriptionLayer:
    return DescriptionLayer(key=key, text=text, priority=priority, condition=ViewCondition())


def cathedral_room_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HUMAN_HALL_OF_NAMES_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", "human_grand_cathedral", "Grand Cathedral", "You leave the tablets and return to the central nave."),),
            features=(
                _feature(
                    "kept_name_litany",
                    "Litany of the Kept Name",
                    "a public liturgical text resting open on a blackwood lectern",
                    "The recurring line is written larger than the rest: 'Fear may name the stranger. It may not name the soul.' The verses around it insist that deeds, vows, mercy, courage, repentance, and truth belong to the person who chooses them.",
                    ("litany", "lectern", "kept name", "litany of the kept name"),
                ),
                _feature(
                    "name_tablets",
                    "Name Tablets",
                    "thousands of pale tablets recording ordinary Human lives",
                    "The tablets contain no heroic filter. Midwives, criminals, bakers, converts, soldiers, widows, children, and unnamed dead all appear. The religious point is almost stubbornly simple: every life is more specific than a category imposed on it.",
                    ("tablets", "names", "wall of names"),
                ),
            ),
            description_layers=(_layer("hall_daily", "Visitors touch familiar names, copy dates for family records, and sometimes stand silently before people they never met."),),
        ),
        HUMAN_MERCY_CLOISTER_KEY: RoomAugmentation(
            exit_overrides=(_exit("east", "human_grand_cathedral", "Grand Cathedral", "You pass from the kitchen court back into the cathedral nave."),),
            features=(
                _feature(
                    "mercy_table",
                    "Mercy Table",
                    "a long scrubbed table where bread, stew, water, and bandages are handed out",
                    "There is no donation box at the serving end. A small inscription under the table edge reads: 'Need is enough reason.'",
                    ("table", "bread table", "serving table", "food"),
                ),
                _feature(
                    "open_cloister_gate",
                    "Open Cloister Gate",
                    "an unbarred street gate left visibly open while the kitchens operate",
                    "The gate faces the public square and is broad enough for a cart or stretcher. Its hinges are maintained better than some ceremonial doors in the cathedral. Hospitality here is infrastructure, not metaphor.",
                    ("gate", "open gate", "cloister gate"),
                ),
            ),
            description_layers=(_layer("mercy_daily", "Some outsiders eat with easy familiarity. Others keep one hand on their packs and sit where they can see the exit. Nobody is asked to perform trust before receiving help."),),
        ),
        HUMAN_CROSSING_CHAPEL_KEY: RoomAugmentation(
            exit_overrides=(_exit("south", "human_grand_cathedral", "Grand Cathedral", "You descend from the small memorial chapel into the nave."),),
            features=(
                _feature(
                    "crossing_lamps",
                    "Crossing Lamps",
                    "rows of low memorial lamps kept for ancestors, travelers, and the dead",
                    "Several old plaques remember the first generations born on Astralis after the crossing from Earth. Newer lamps have nothing to do with Earth at all. The chapel treats exile as part of Human history, not the whole of Human identity.",
                    ("lamps", "lamp", "memorial lamps", "crossing lamp"),
                ),
                _feature(
                    "vigil_bell",
                    "Vigil Bell",
                    "a dark bronze bell hung above the chapel with a rope descending beside the lamps",
                    "A small plaque says the bell is rung for danger discovered, people missing, the dead newly named, and the living who must decide what to do next. It is not an alarm bell. It is a promise not to look away.",
                    ("bell", "vigil bell", "bell rope", "rope"),
                ),
            ),
            description_layers=(_layer("chapel_hush", "The organ is only a distant vibration here. Most people speak in whispers, but nobody is required to."),),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _patch_grand_cathedral() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY["human_grand_cathedral"]
    exits = dict(original.exits)
    exits.update(
        {
            "east": HUMAN_HALL_OF_NAMES_KEY,
            "west": HUMAN_MERCY_CLOISTER_KEY,
            "north": HUMAN_CROSSING_CHAPEL_KEY,
        }
    )
    description = (
        "The cathedral nave rises into darkness above rows of black wooden pews. Hundreds of candles burn before severe stone saints, "
        "their light reflected in crimson glass and polished iron. This is not only a ceremonial monument: families wait for blessings, mourners sit beneath side arches, "
        "clerics carry food toward the mercy kitchens, and travelers cross the nave to smaller chapels. The High Acolyte stands near the crossing. "
        "East lies the Hall of Names, west the Mercy Cloister, and north the smaller Crossing Chapel."
    )
    return replace(original, description=description, exits=exits, npc_keys=tuple(dict.fromkeys(original.npc_keys + ("human_high_acolyte",))))


def _patch_grand_cathedral_augmentation(world_service) -> None:
    base = world_service.augmentations.get("human_grand_cathedral", RoomAugmentation())
    additions = {
        "east": _exit("east", HUMAN_HALL_OF_NAMES_KEY, "Hall of Names", "You pass beneath a low arch into the tablet-lined Hall of Names."),
        "west": _exit("west", HUMAN_MERCY_CLOISTER_KEY, "Mercy Cloister", "Warm kitchen air reaches you as you enter the Mercy Cloister."),
        "north": _exit("north", HUMAN_CROSSING_CHAPEL_KEY, "Crossing Chapel", "You climb a short flight of steps into the quieter Crossing Chapel."),
    }
    exits = tuple(exit_def for exit_def in base.exit_overrides if exit_def.direction not in additions) + tuple(additions.values())
    sanctuary = _feature(
        "cathedral_daily_sanctuary",
        "Open Sanctuary",
        "the ordinary flow of worship, mourning, counsel, and service beneath the immense nave",
        "The cathedral is central to Human life without functioning as the city government. People come here to marry, mourn, confess, seek counsel, receive food, keep vigils, and hear the old liturgies that insist a fearful outsider does not get final authority over a Human soul.",
        ("sanctuary", "nave", "worshippers", "worship"),
    )
    features = base.features if any(f.key == sanctuary.key for f in base.features) else base.features + (sanctuary,)
    layer = _layer(
        "cathedral_anchor",
        "For Humans, the cathedral is less a throne than an anchor: a place that repeats, in ritual and ordinary service, that being feared is not the same thing as being monstrous.",
        priority=35,
    )
    layers = base.description_layers if any(item.key == layer.key for item in base.description_layers) else base.description_layers + (layer,)
    world_service.augmentations["human_grand_cathedral"] = replace(base, exit_overrides=exits, features=features, description_layers=layers)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop("human_grand_cathedral", None)


def install_human_cathedral_content(world_service=None) -> None:
    """Register the religious Human cathedral arc and its three side rooms."""
    for quest in HUMAN_CATHEDRAL_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for npc in HUMAN_CATHEDRAL_NPCS:
        _replace_npc(npc)
    for room in HUMAN_CATHEDRAL_ROOMS:
        _replace_room(room)
    grand = _patch_grand_cathedral()
    _replace_room(grand)

    if world_service is not None:
        world_service.legacy_rooms[grand.key] = grand
        for room in HUMAN_CATHEDRAL_ROOMS:
            world_service.legacy_rooms[room.key] = room
        world_service.augmentations.update(cathedral_room_augmentations())
        _patch_grand_cathedral_augmentation(world_service)
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in HUMAN_CATHEDRAL_ROOM_KEYS:
                cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _active_step(session, key: str) -> str | None:
    row = _quest(session, key)
    if row and row.get("status") == "active":
        return row.get("current_step")
    return None


def _finish_quest(session, key: str, complete_flag: str) -> None:
    assert session.character is not None
    row = _quest(session, key)
    if row is None:
        session.database.start_quest(session.character.id, key, "complete")
    session.database.complete_quest(session.character.id, key)
    session.database.grant_flag(session.character.id, complete_flag)


def _grandfather_quest(session, quest: QuestDefinition, complete_flag: str, grandfather_flag: str) -> None:
    assert session.character is not None
    if _quest(session, quest.key) is None:
        session.database.start_quest(session.character.id, quest.key, "complete")
        session.database.complete_quest(session.character.id, quest.key)
    session.database.grant_flag(session.character.id, complete_flag)
    session.database.grant_flag(session.character.id, grandfather_flag)


def reconcile_human_cathedral_faith(session) -> None:
    """Do not rewind Humans who progressed through the older cathedral chain."""
    if session.character is None or session.character.race != "human":
        return
    training = _quest(session, quests.HUMAN_COMBAT_TRAINING.key)
    lower = _quest(session, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)

    if training is not None and _quest(session, HUMAN_KEPT_NAME_QUEST.key) is None:
        _grandfather_quest(
            session,
            HUMAN_KEPT_NAME_QUEST,
            HUMAN_KEPT_NAME_COMPLETE_FLAG,
            HUMAN_CATHEDRAL_GRANDFATHERED_NAME_FLAG,
        )
    if lower is not None and _quest(session, HUMAN_OPEN_DOOR_QUEST.key) is None:
        _grandfather_quest(
            session,
            HUMAN_OPEN_DOOR_QUEST,
            HUMAN_OPEN_DOOR_COMPLETE_FLAG,
            HUMAN_CATHEDRAL_GRANDFATHERED_DOOR_FLAG,
        )


def _cathedral_status(session) -> tuple[str, str | None]:
    for quest in HUMAN_CATHEDRAL_QUESTS:
        row = _quest(session, quest.key)
        if row and row.get("status") == "active":
            return quest.name, quest.objective_for_step(row.get("current_step"))
    summons = _quest(session, quests.HUMAN_CATHEDRAL_SUMMONS.key)
    if summons and summons.get("status") == "active":
        return quests.HUMAN_CATHEDRAL_SUMMONS.name, quests.HUMAN_CATHEDRAL_SUMMONS.objective_for_step(summons.get("current_step"))
    training = _quest(session, quests.HUMAN_COMBAT_TRAINING.key)
    if training and training.get("status") == "active":
        return quests.HUMAN_COMBAT_TRAINING.name, quests.HUMAN_COMBAT_TRAINING.objective_for_step(training.get("current_step"))
    lower = _quest(session, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)
    if lower and lower.get("status") == "active":
        return quests.HUMAN_LOWER_WARDS_INVESTIGATION.name, quests.HUMAN_LOWER_WARDS_INVESTIGATION.objective_for_step(lower.get("current_step"))
    return "No active cathedral duty", None


async def _show_cathedral_status(session) -> None:
    name, objective = _cathedral_status(session)
    await session.send("\r\n--- Grand Cathedral ---\r\n")
    await session.send(f"Current thread: {name}.\r\n")
    if objective:
        await session.send(f"Objective: {objective}\r\n")
    await session.send(
        "The cathedral's current teaching is simple: fear can shape a reputation, but it does not get final authority over a soul.\r\n"
    )


async def _talk_high_acolyte(session) -> bool:
    if session.character is None or session.character.race != "human" or session.character.current_room != "human_grand_cathedral":
        return False
    reconcile_human_cathedral_faith(session)
    summons = _quest(session, quests.HUMAN_CATHEDRAL_SUMMONS.key)
    kept = _quest(session, HUMAN_KEPT_NAME_QUEST.key)
    training = _quest(session, quests.HUMAN_COMBAT_TRAINING.key)
    door = _quest(session, HUMAN_OPEN_DOOR_QUEST.key)
    lower = _quest(session, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)
    bells = _quest(session, HUMAN_BELLS_QUEST.key)

    if summons and summons.get("status") == "active" and training is None:
        if kept is None:
            session.database.start_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key, "read_litany")
            await session.send(
                "\r\nThe High Acolyte accepts the sealed note but does not turn it over to write orders yet. Instead, they gesture toward the side aisles where families, mourners, workers, and strangers move through the cathedral.\r\n"
                "'You already know what people beyond Blackwall call us. The cathedral will not teach you to pretend the word Demon has no weight.'\r\n"
                "'It will teach you something more useful: a fearful stranger does not receive final authority over your soul.'\r\n"
                "They point east. 'Begin in the Hall of Names. READ LITANY. Then go north to the Crossing Chapel and LIGHT LAMP. Come back when those words have had time to become more than words.'\r\n"
                "\r\nNew quest: The Name We Keep.\r\n"
            )
            return True
        step = _active_step(session, HUMAN_KEPT_NAME_QUEST.key)
        if step == "return_acolyte":
            _finish_quest(session, HUMAN_KEPT_NAME_QUEST.key, HUMAN_KEPT_NAME_COMPLETE_FLAG)
            session.database.complete_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
            session.database.grant_flag(session.character.id, "met_high_acolyte")
            if session.database.item_quantity(session.character.id, "sealed_cathedral_note") <= 0:
                session.database.add_item(session.character.id, "sealed_cathedral_note", 1)
            session.database.start_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key, "read_training_orders")
            await session.send(
                "\r\nThe High Acolyte listens without asking what you felt at the lamps.\r\n"
                "'Good. Keep this much: you are not a monster because somebody needs time to stop seeing one. And you are not righteous merely because you are Human. Your choices remain yours.'\r\n"
                "Only then do they turn your note over and write across the reverse. 'Now learn what happens when something hits back.'\r\n"
                "\r\nQuest complete: The Name We Keep.\r\nQuest complete: A Summons to the Cathedral.\r\n"
                "New quest: Lessons Beyond the Gate. Type READ NOTE.\r\n"
            )
            return True
        objective = HUMAN_KEPT_NAME_QUEST.objective_for_step(step)
        await session.send("\r\n'The lesson is not finished because you returned to the building,' the High Acolyte says.\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    if training and training.get("status") == "active":
        objective = quests.HUMAN_COMBAT_TRAINING.objective_for_step(training.get("current_step"))
        await session.send("\r\nThe High Acolyte nods toward the note. 'Learn the controlled lesson first. Faith does not make an untested body harder to kill.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    if training and training.get("status") == "completed" and lower is None:
        if door is None:
            session.database.start_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key, "meet_deacon")
            await session.send(
                "\r\nThe High Acolyte hears your account of the training yard, then looks toward the western cloister.\r\n"
                "'Knowing you are not a monster can become another kind of vanity if all it teaches you to do is defend yourself.'\r\n"
                "'The Mercy Cloister feeds travelers who distrust us, people who dislike our saints, and people who will take the bread and leave still calling us Demons. We feed them anyway.'\r\n"
                "'Go west. TALK DEACON. Learn why an open door cannot demand trust as its entrance fee.'\r\n"
                "\r\nNew quest: An Open Door.\r\n"
            )
            return True
        step = _active_step(session, HUMAN_OPEN_DOOR_QUEST.key)
        if step == "return_acolyte":
            _finish_quest(session, HUMAN_OPEN_DOOR_QUEST.key, HUMAN_OPEN_DOOR_COMPLETE_FLAG)
            session.database.start_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key, "find_lower_wards")
            await session.send(
                "\r\nThe High Acolyte listens to how the outsider answered—or did not answer.\r\n"
                "'Sanctuary can be offered. Trust cannot be commanded. Remember the difference.'\r\n"
                "Their attention shifts toward the nave doors. 'Now there is work in the Lower Wards. Sealed passages are being marked and scrubbed clean. Care for a city includes noticing what it is trying not to show you.'\r\n"
                "\r\nQuest complete: An Open Door.\r\nNew quest: Marks in the Ash.\r\n"
            )
            return True
        objective = HUMAN_OPEN_DOOR_QUEST.objective_for_step(step)
        await session.send("\r\n'The cloister lesson is deliberately ordinary,' the High Acolyte says. 'That is why it matters.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    if lower and lower.get("status") == "active":
        objective = quests.HUMAN_LOWER_WARDS_INVESTIGATION.objective_for_step(lower.get("current_step"))
        await session.send(
            "\r\nThe High Acolyte regards you with measured patience. 'The Lower Wards do not reward loud questions. Follow what you can prove. People deserve truth more than the cathedral deserves to look wise.'\r\n"
        )
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    if lower and lower.get("status") == "completed":
        if bells is None:
            session.database.start_quest(session.character.id, HUMAN_BELLS_QUEST.key, "light_vigil")
            await session.send(
                "\r\nThe High Acolyte's expression tightens at your report from the Lower Wards.\r\n"
                "'A cathedral that only tells people they are good while refusing to look at who is endangered would be decoration, not faith.'\r\n"
                "They gesture north. 'Go to the Crossing Chapel. LIGHT VIGIL for the people living above those hidden ways. Then RING VIGIL BELL. The bell is not for us to feel solemn. It is a promise that what was discovered will not be ignored.'\r\n"
                "\r\nNew quest: What the Bells Are For.\r\n"
            )
            return True
        step = _active_step(session, HUMAN_BELLS_QUEST.key)
        if step == "return_acolyte":
            _finish_quest(session, HUMAN_BELLS_QUEST.key, HUMAN_BELLS_COMPLETE_FLAG)
            await session.send(
                "\r\nThe High Acolyte hears the last vibration of the vigil bell through the stone before you speak.\r\n"
                "'That is what these walls are for. Not to prove the world wrong about us. To make sure fear—ours or theirs—does not decide what we become.'\r\n"
                "They incline their head. 'There will be more work. For now, remember the order: name the person, open the door, tell the truth, ring the bell when truth asks something of the living.'\r\n"
                "\r\nQuest complete: What the Bells Are For.\r\n"
            )
            return True
        if bells.get("status") == "active":
            objective = HUMAN_BELLS_QUEST.objective_for_step(step)
            await session.send("\r\n'The bell is waiting for an action, not a speech,' the High Acolyte says.\r\n")
            if objective:
                await session.send(f"Current objective: {objective}\r\n")
            return True

    await session.send("\r\n")
    for line in HIGH_ACOLYTE_RELIGIOUS.dialogue:
        await session.send(line + "\r\n")
    await session.send(
        "The High Acolyte glances across the working cathedral. 'These walls do not govern Blackwall. They witness marriages, receive the dead, feed strangers, keep vigils, and remind frightened people that fear is a poor theologian.'\r\n"
    )
    return True


async def handle_human_cathedral_command(session, command: str) -> bool:
    if session.character is None or session.character.race != "human":
        return False
    reconcile_human_cathedral_faith(session)
    normalized = command.strip().lower()
    room = session.character.current_room

    if normalized in {"cathedral", "faith", "church", "cathedral duty", "faith duty"}:
        await _show_cathedral_status(session)
        return True

    if normalized in {"talk high acolyte", "talk to high acolyte", "talk acolyte", "talk to acolyte"}:
        return await _talk_high_acolyte(session)

    if room == HUMAN_HALL_OF_NAMES_KEY and normalized in {
        "read litany", "read the litany", "read kept name", "read litany of the kept name", "examine litany"
    }:
        step = _active_step(session, HUMAN_KEPT_NAME_QUEST.key)
        if step == "read_litany":
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_NAME_LITANY_FLAG)
            session.database.advance_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key, "light_crossing_lamp")
            await session.send(
                "\r\nThe litany begins with names other peoples once used for Humans in fear, contempt, curiosity, and ignorance. None is treated as magic. None is denied its history.\r\n"
                "The response follows every verse: 'Fear may name the stranger. It may not name the soul.'\r\n"
                "The final lines are harder: dignity does not excuse cruelty, and prejudice does not erase responsibility. The person you become still belongs to your choices.\r\n"
                "Go NORTH from the Grand Cathedral into the Crossing Chapel and LIGHT LAMP.\r\n"
            )
            return True
        await session.send("\r\nYou read the familiar response again: 'Fear may name the stranger. It may not name the soul.'\r\n")
        return True

    if room == HUMAN_CROSSING_CHAPEL_KEY and normalized in {
        "light lamp", "light crossing lamp", "light memorial lamp", "light a lamp"
    }:
        step = _active_step(session, HUMAN_KEPT_NAME_QUEST.key)
        if step == "light_crossing_lamp":
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_CROSSING_LAMP_FLAG)
            session.database.advance_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key, "return_acolyte")
            await session.send(
                "\r\nYou light one low lamp among hundreds. No mechanism answers. No vision arrives. It is only flame, smoke, old names, and the knowledge that the first Humans crossed here intentionally and never found a road home.\r\n"
                "A plaque beneath the lamps reads: 'We inherited exile, not guilt.'\r\n"
                "Return SOUTH and TALK HIGH ACOLYTE.\r\n"
            )
            return True
        await session.send("\r\nYou tend one of the low memorial flames. The chapel does not require every lamp to begin a quest.\r\n")
        return True

    if room == HUMAN_MERCY_CLOISTER_KEY and normalized in {
        "talk deacon", "talk to deacon", "talk meret", "talk to meret", "talk deacon meret", "talk to deacon meret"
    }:
        step = _active_step(session, HUMAN_OPEN_DOOR_QUEST.key)
        if step == "meet_deacon":
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_DEACON_HEARD_FLAG)
            session.database.advance_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key, "serve_bread")
            await session.send(
                "\r\nMeret hands you a stack of bowls. 'Sanctuary offered only to people who already trust us would be vanity with a roof.'\r\n"
                "The deacon nods toward the serving table. 'SERVE BREAD. Do not make anyone earn it with gratitude.'\r\n"
            )
            return True
        await session.send("\r\nMeret keeps working. 'Need is enough reason for the first bowl.'\r\n")
        return True

    if room == HUMAN_MERCY_CLOISTER_KEY and normalized in {
        "serve bread", "serve meal", "serve food", "serve stew", "help serve"
    }:
        step = _active_step(session, HUMAN_OPEN_DOOR_QUEST.key)
        if step != "serve_bread":
            await session.send("\r\nYou can help with the table, but your current cathedral duty does not require another serving round.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_BREAD_SERVED_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key, "answer_pilgrim")
        await session.send(
            "\r\nYou pass bowls down the table. Dorna Ironstep accepts hers, then looks up at the horned stonework above you.\r\n"
            "'First Demon church I've ever eaten in,' she says. 'I know your caravans. I know your contracts. Church is different.'\r\n"
            "At the open gate, another traveler accepts bread but remains outside the threshold. Nobody drags them in. Nobody laughs.\r\n"
            "Dorna studies you. 'Doesn't bother you, people looking at you and seeing the story before the person?'\r\n"
            "You may ANSWER PATIENCE, ANSWER PRIDE, or ANSWER SILENCE.\r\n"
        )
        return True

    if room == HUMAN_MERCY_CLOISTER_KEY and normalized in {
        "answer patience", "answer with patience", "answer pride", "answer with pride", "answer silence", "answer with silence"
    }:
        step = _active_step(session, HUMAN_OPEN_DOOR_QUEST.key)
        if step != "answer_pilgrim":
            await session.send("\r\nThere is no unanswered pilgrim question in your current duty.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_OUTSIDER_ANSWER_FLAG)
        if "patience" in normalized:
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_OUTSIDER_PATIENCE_FLAG)
            response = (
                "You tell Dorna she does not have to trust you before she eats. Trust can come later, if it comes at all.\r\n"
                "Dorna considers that, then nods once. 'Fairer answer than most border sermons.'"
            )
        elif "pride" in normalized:
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_OUTSIDER_PRIDE_FLAG)
            response = (
                "You tell Dorna that Humans made Demon part of their own language long ago, but owning the word does not require anyone else to stop being wary overnight.\r\n"
                "Dorna snorts softly. 'You lot do commit to an aesthetic.' Then, more seriously: 'I can respect owning it.'"
            )
        else:
            session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_OUTSIDER_SILENCE_FLAG)
            response = (
                "You do not turn the meal into a defense of your people. You refill Dorna's water and move to the next bowl.\r\n"
                "After a moment she says, 'All right. That was an answer too.'"
            )
        session.database.advance_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key, "return_acolyte")
        await session.send("\r\n" + response + "\r\nReturn EAST and TALK HIGH ACOLYTE.\r\n")
        return True

    if room == HUMAN_CROSSING_CHAPEL_KEY and normalized in {
        "light vigil", "light vigil lamp", "light the vigil", "light a vigil"
    }:
        step = _active_step(session, HUMAN_BELLS_QUEST.key)
        if step != "light_vigil":
            await session.send("\r\nThe vigil lamps are available, but there is no new cathedral vigil assigned to you now.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_VIGIL_LIT_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_BELLS_QUEST.key, "ring_bell")
        await session.send(
            "\r\nYou light a fresh vigil from an older flame. You do not know every name of the people living over forgotten cisterns, sealed passages, or hidden routes. The lamp does not pretend that ignorance is the same as innocence.\r\n"
            "The bell rope hangs beside you. RING VIGIL BELL.\r\n"
        )
        return True

    if room == HUMAN_CROSSING_CHAPEL_KEY and normalized in {
        "ring bell", "ring vigil bell", "ring the bell", "pull bell rope", "ring vigil"
    }:
        step = _active_step(session, HUMAN_BELLS_QUEST.key)
        if step != "ring_bell":
            await session.send("\r\nThe vigil bell remains still. It is not rung casually.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_CATHEDRAL_VIGIL_BELL_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_BELLS_QUEST.key, "return_acolyte")
        await session.send(
            "\r\nYou pull the rope. The bronze bell answers once, deep enough to vibrate through the floor and out into Cathedral Square.\r\n"
            "Nobody cheers. In the nave below, heads lift. Clerics pause. Somewhere outside, a watch clerk will note the vigil and ask what was discovered.\r\n"
            "The sound is not proof that Humans are good. It is a public refusal to look away. Return SOUTH and TALK HIGH ACOLYTE.\r\n"
        )
        return True

    return False


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_human_cathedral_runtime(player_session_class, world_service) -> None:
    install_human_cathedral_content(world_service)
    if getattr(player_session_class, "_human_cathedral_faith_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "human":
            return
        reconcile_human_cathedral_faith(self)
        for quest in HUMAN_CATHEDRAL_QUESTS:
            row = _quest(self, quest.key)
            if row and row.get("status") == "active":
                objective = quest.objective_for_step(row.get("current_step"))
                await self.send(f"\r\nCathedral duty still active: {quest.name}.\r\n")
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")
                break

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "human":
            await previous_playing_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        if await handle_human_cathedral_command(self, command):
            return
        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is None or self.character.race != "human":
            return
        reconcile_human_cathedral_faith(self)
        if command.strip().lower() in {"help", "?"}:
            await self.send(
                "Human cathedral: use CATHEDRAL or FAITH for the current religious thread. Cathedral duties may use READ LITANY, LIGHT LAMP, TALK DEACON, SERVE BREAD, ANSWER <PATIENCE/PRIDE/SILENCE>, LIGHT VIGIL, and RING VIGIL BELL.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._human_cathedral_faith_runtime_installed = True
