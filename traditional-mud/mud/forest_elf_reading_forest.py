from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import FOREST_ELF_FIRST_WALK, QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import (
    FOREST_ELF_BRIARSHADOW_THICKET_KEY,
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_START_ROOM_KEY,
    NpcDefinition,
    RoomDefinition,
)


WHITEWOOD_LOOKOUT_KEY = "forest_elf_whitewood_lookout"
RIVER_MOSS_BUNDLE_KEY = "forest_elf_river_moss_bundle"

WHAT_DID_YOU_HEAR_KEY = "forest_elf_what_did_you_hear"
WHAT_DID_YOU_HEAR_COMPLETE_FLAG = "forest_elf_what_did_you_hear_complete"
PATH_WARNING_HEARD_FLAG = "forest_elf_path_warning_heard"
PATH_SIGN_READ_FLAG = "forest_elf_path_sign_read"
BARKJAW_AVOIDED_FLAG = "forest_elf_barkjaw_avoided"
BARKJAW_AMBUSHED_FLAG = "forest_elf_barkjaw_ambushed"
BARKJAW_DEFEATED_FLAG = "forest_elf_barkjaw_defeated"
STAG_FOUND_FLAG = "forest_elf_whitewood_stag_found"
STAG_RESCUED_FLAG = "forest_elf_whitewood_stag_rescued"
STAG_LEFT_FLAG = "forest_elf_whitewood_stag_left"
STAG_RETURNED_FLAG = "forest_elf_whitewood_stag_returned"
HOLLOWBACK_ENCOUNTERED_FLAG = "forest_elf_hollowback_encountered"

BARKJAW_KEY = "forest_elf_barkjaw"
HOLLOWBACK_KEY = "forest_elf_hollowback"
LOOKOUT_KEEPER_KEY = "forest_elf_lookout_keeper_serael"


WHAT_DID_YOU_HEAR = QuestDefinition(
    key=WHAT_DID_YOU_HEAR_KEY,
    name="What Did You Hear?",
    style="structured",
    description=(
        "Carry a damp bundle of river moss to Whitewood Lookout while you make the Circle's old river walk. "
        "The delivery is simple. The path is the lesson: notice what the forest stops doing before you decide what is safe."
    ),
    objective_steps=(
        ("read_path", "Carry the River Moss Bundle along the Old River Path. At the Listening Pool, stop and LISTEN before going north."),
        ("decide_stag", "At the Outer Grove, EXAMINE STAG and decide whether to FREE STAG or LEAVE STAG."),
        ("report_lookout", "Take the moss WEST from the Outer Grove to Whitewood Lookout and TALK SERAEL."),
        ("answer_question", "Answer the lookout keeper's question with REPORT BIRDS, REPORT TRACKS, REPORT BARKJAW, or REPORT NOTHING."),
        ("complete", "You delivered the moss and reported what you actually noticed instead of what you expected to find."),
    ),
)


RIVER_MOSS_BUNDLE = ItemDefinition(
    key=RIVER_MOSS_BUNDLE_KEY,
    name="River Moss Bundle",
    description=(
        "A cool, damp bundle of clean river moss wrapped in broad leaves. Whitewood Lookout uses it to pack moisture around "
        "the roots of its living rail and sighting tree. It is an ordinary delivery that happens to require walking through the forest."
    ),
    category="quest_item",
    tier=0,
)


BARKJAW = EnemyDefinition(
    key=BARKJAW_KEY,
    name="Barkjaw",
    aliases=("barkjaw", "bark jaw", "bark-jaw"),
    description=(
        "a low forest predator with mottled brown fur and overlapping bark-hard plates along its jaw and shoulders; "
        "it hunts by staying motionless until something ignores the silence around it"
    ),
    max_hp=24,
    armor_class=4,
    auto_attack_damage=3,
    auto_attack_interval=3.2,
    xp_reward=18,
    retaliates=True,
    tutorial=True,
)


HOLLOWBACK = EnemyDefinition(
    key=HOLLOWBACK_KEY,
    name="Hollowback",
    aliases=("hollowback", "hollow back", "fungal hollowback"),
    description=(
        "a deer-sized forest browser whose ridged back has grown barklike and strangely concave, with pale shelf-fungi "
        "flowering along the hollow. It moves with the frightened aggression of an animal whose ordinary instincts have been pushed out of shape."
    ),
    max_hp=34,
    armor_class=6,
    auto_attack_damage=4,
    auto_attack_interval=3.1,
    xp_reward=28,
    retaliates=True,
    tutorial=False,
)


LOOKOUT_KEEPER = NpcDefinition(
    key=LOOKOUT_KEEPER_KEY,
    name="Serael Reedwatch",
    short_description="a lean lookout keeper replacing damp moss around the roots of a living whitewood rail",
    room_key=WHITEWOOD_LOOKOUT_KEY,
    role="Forest Elf boundary lookout and observation mentor",
    dialogue=(
        "Serael presses two fingers against the whitewood bark, then looks past you toward the path. 'Moss can be replaced. Attention is harder.'",
        "'A quiet forest is not an empty forest. Something made it quiet.'",
        "'When you come up from the river, I do not want a theory first. Tell me what you actually heard.'",
    ),
)


WHITEWOOD_LOOKOUT = RoomDefinition(
    key=WHITEWOOD_LOOKOUT_KEY,
    name="Whitewood Lookout",
    region_key="great_elf_forest",
    description=(
        "A broad whitewood grows out over the slope west of the boundary oak, its lower limbs shaped over decades into a modest lookout platform. "
        "Nothing here resembles a military tower. A living rail, two weather slates, a rain cup, and a narrow bench are enough to watch the river path and the darker woods beyond it. "
        "The view back toward town is green and comfortable. The view north is broken by thorn, old trunks, and places where the canopy hides what is moving beneath it."
    ),
    exits={"east": FOREST_ELF_OUTER_GROVE_KEY},
    npc_keys=(LOOKOUT_KEEPER_KEY,),
    tags=("forest_elf_start", "safe", "lookout", "boundary", "observation"),
)


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    overrides = {value.direction: value for value in existing.exit_overrides}
    overrides.update({value.direction: value for value in extra.exit_overrides})
    extras = {(value.direction, value.destination_key): value for value in existing.extra_exits}
    extras.update({(value.direction, value.destination_key): value for value in extra.extra_exits})
    features = {value.key: value for value in existing.features}
    features.update({value.key: value for value in extra.features})
    layers = {value.key: value for value in existing.description_layers}
    layers.update({value.key: value for value in extra.description_layers})
    return RoomAugmentation(
        exit_overrides=tuple(overrides.values()),
        extra_exits=tuple(extras.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


def _patch_room(room_key: str, *, exits: dict[str, str] | None = None, enemy_keys: tuple[str, ...] = ()) -> RoomDefinition | None:
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is None:
        return None
    merged_exits = dict(room.exits)
    if exits:
        merged_exits.update(exits)
    merged_enemies = tuple(dict.fromkeys(room.enemy_keys + enemy_keys))
    replacement = replace(room, exits=merged_exits, enemy_keys=merged_enemies)
    legacy_world.ROOMS = tuple(replacement if value.key == room_key else value for value in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY[room_key] = replacement
    return replacement


def reading_forest_augmentations() -> dict[str, RoomAugmentation]:
    return {
        FOREST_ELF_LISTENING_POOL_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="underbird_warning",
                    name="Underbird Canopy",
                    aliases=("canopy", "birds", "underbirds", "birdsong", "quiet"),
                    summary="willow branches where the small river birds should be noisier than they are",
                    examine_text=(
                        "Fresh droppings, seed husks, and old nests say this stretch should be busy. It is not. A few birds remain, but each time the path north rustles, their calls stop together."
                    ),
                    listen_text=(
                        "The important sound is the one that disappears. Birdsong cuts off northward in a clean wave, then resumes behind you. Beneath it, deer tracks veer sharply away from the same patch of brush and several leaves lie freshly turned pale-side up."
                    ),
                ),
                FeatureDefinition(
                    key="veering_deer_sign",
                    name="Veering Deer Sign",
                    aliases=("deer tracks", "tracks", "sign", "turned leaves", "leaves"),
                    summary="fresh deer tracks that abruptly abandon the easiest line north",
                    examine_text=(
                        "The deer were not running. They simply chose not to pass one particular patch of brush. Scuffed moss and pale-up leaves show where several animals made the same quiet decision."
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="reading_forest_pool_quiet",
                    text=(
                        "Small river birds still move through the willows, but their noise is uneven. Northward, whole layers of birdsong keep dropping out for a few breaths at a time."
                    ),
                    priority=72,
                    condition=ViewCondition(races=("forest_elf",)),
                ),
            ),
        ),
        FOREST_ELF_OUTER_GROVE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="west",
                    destination_key=WHITEWOOD_LOOKOUT_KEY,
                    name="Whitewood Lookout",
                    travel_text="You follow a short root stair west onto the low living platform of Whitewood Lookout.",
                ),
            ),
            features=(
                FeatureDefinition(
                    key="snared_whitewood_stag",
                    name="Snared Whitewood Stag",
                    aliases=("stag", "whitewood stag", "snare", "iron snare", "wounded stag"),
                    summary="a pale-antlered stag caught low around one foreleg in an old iron snare",
                    examine_text=(
                        "The stag is exhausted rather than dying. An old iron cable has tightened above the hoof, probably left from a trapping line that predates the current Circle markers. The animal watches your hands. The wire can be opened carefully without forcing the leg."
                    ),
                ),
            ),
        ),
        WHITEWOOD_LOOKOUT_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="east",
                    destination_key=FOREST_ELF_OUTER_GROVE_KEY,
                    name="Outer Grove",
                    travel_text="You step east off the living platform and return to the boundary oak.",
                ),
            ),
            features=(
                FeatureDefinition(
                    key="living_sighting_rail",
                    name="Living Sighting Rail",
                    aliases=("rail", "whitewood rail", "sighting rail", "whitewood"),
                    summary="a shaped whitewood limb kept alive as the lookout's waist-high rail",
                    examine_text=(
                        "The rail was trained into place rather than cut and nailed. Old moss packing keeps the exposed root seam cool where the platform meets the trunk; today's bundle is meant to replace the dry brown layer."
                    ),
                ),
                FeatureDefinition(
                    key="weather_slates",
                    name="Weather Slates",
                    aliases=("slates", "weather slates", "observation slates"),
                    summary="two waxed slates recording ordinary changes along the boundary",
                    examine_text=(
                        "Entries are terse: wind, rain, deer crossings, bird counts, broken markers, smoke, strangers, silence. There is no column for omens."
                    ),
                ),
            ),
        ),
        FOREST_ELF_BRIARSHADOW_THICKET_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="hollowback_browse",
                    name="Hollowback Browse",
                    aliases=("browse", "fungus", "fungi", "bark", "scrapes", "hollowback sign"),
                    summary="ragged browsing cuts and strips of bark dusted with pale fungal powder",
                    examine_text=(
                        "The feeding marks are too high and too ragged for deer. Pale fungal dust clings to the bark where something broad-backed pushed through. The trail trends upstream rather than toward town."
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="hollowback_presence",
                    text=(
                        "Something deer-sized moves behind the briars with a dry wooden scrape. For an instant you see a ridged, hollow-looking back plated in barklike growth and pale shelf-fungi before it disappears behind the trunks."
                    ),
                    priority=78,
                ),
            ),
        ),
    }


def install_reading_forest_content(world_service=None) -> None:
    if WHAT_DID_YOU_HEAR.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (WHAT_DID_YOU_HEAR,)
    quests.QUESTS_BY_KEY[WHAT_DID_YOU_HEAR.key] = WHAT_DID_YOU_HEAR

    if RIVER_MOSS_BUNDLE.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (RIVER_MOSS_BUNDLE,)
    crafting.ITEMS_BY_KEY[RIVER_MOSS_BUNDLE.key] = RIVER_MOSS_BUNDLE

    for enemy in (BARKJAW, HOLLOWBACK):
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    if LOOKOUT_KEEPER.key not in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = legacy_world.NPCS + (LOOKOUT_KEEPER,)
    legacy_world.NPCS_BY_KEY[LOOKOUT_KEEPER.key] = LOOKOUT_KEEPER

    if WHITEWOOD_LOOKOUT.key not in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = legacy_world.ROOMS + (WHITEWOOD_LOOKOUT,)
    legacy_world.ROOMS_BY_KEY[WHITEWOOD_LOOKOUT.key] = WHITEWOOD_LOOKOUT

    outer = _patch_room(FOREST_ELF_OUTER_GROVE_KEY, exits={"west": WHITEWOOD_LOOKOUT_KEY})
    briar = _patch_room(FOREST_ELF_BRIARSHADOW_THICKET_KEY, enemy_keys=(HOLLOWBACK_KEY,))

    if world_service is None:
        return

    world_service.legacy_rooms[WHITEWOOD_LOOKOUT_KEY] = WHITEWOOD_LOOKOUT
    if outer is not None:
        world_service.legacy_rooms[FOREST_ELF_OUTER_GROVE_KEY] = outer
    if briar is not None:
        world_service.legacy_rooms[FOREST_ELF_BRIARSHADOW_THICKET_KEY] = briar
    for room_key, augmentation in reading_forest_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (
            FOREST_ELF_LISTENING_POOL_KEY,
            FOREST_ELF_OUTER_GROVE_KEY,
            WHITEWOOD_LOOKOUT_KEY,
            FOREST_ELF_BRIARSHADOW_THICKET_KEY,
        ):
            cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _microquest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, WHAT_DID_YOU_HEAR.key)


def _first_walk(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)


def _ensure_one(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity <= 0:
        session.database.add_item(session.character.id, item_key, 1)
    elif quantity > 1:
        session.database.consume_item(session.character.id, item_key, quantity - 1)


def _consume_all(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def start_reading_forest_if_ready(session) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    if WHAT_DID_YOU_HEAR_COMPLETE_FLAG in _flags(session):
        return False
    existing = _microquest(session)
    if existing is not None:
        if existing.get("status") == "active":
            _ensure_one(session, RIVER_MOSS_BUNDLE_KEY)
        return False
    first_walk = _first_walk(session)
    if not first_walk or first_walk.get("status") != "active":
        return False
    if first_walk.get("current_step") in {None, "await_home_rounds"}:
        return False
    session.database.start_quest(session.character.id, WHAT_DID_YOU_HEAR.key, "read_path")
    _ensure_one(session, RIVER_MOSS_BUNDLE_KEY)
    return True


def _advance_to_stag(session) -> None:
    quest = _microquest(session)
    if not quest or quest.get("status") != "active":
        return
    if quest.get("current_step") == "read_path":
        session.database.advance_quest(session.character.id, WHAT_DID_YOU_HEAR.key, "decide_stag")


def _begin_forced_combat(session, enemy_definition: EnemyDefinition) -> bool:
    if session.character is None or session.combatant is None or session.active_enemy is not None:
        return False
    enemy = EnemyState(enemy_definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


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


async def _handle_listening_pool(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    if session.character.current_room != FOREST_ELF_LISTENING_POOL_KEY:
        return False
    quest = _microquest(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "read_path":
        return False

    if normalized in {"examine tracks", "look tracks", "examine deer tracks", "look deer tracks", "examine sign", "read sign", "examine leaves"}:
        session.database.grant_flag(session.character.id, PATH_SIGN_READ_FLAG)
        await session.send(
            "\r\nThe deer tracks do not show panic. They show refusal. Several animals approached the easy north line, turned before the same brush, and chose worse footing instead. Fresh leaves lie pale-side up where hooves changed direction.\r\n"
            "That is useful, but the path is giving you another kind of information too. LISTEN.\r\n"
        )
        return True

    if normalized in {"listen", "listen pool", "listen birds", "listen to birds", "listen forest", "listen to forest", "listen canopy"}:
        session.database.grant_flag(session.character.id, PATH_WARNING_HEARD_FLAG)
        session.database.grant_flag(session.character.id, PATH_SIGN_READ_FLAG)
        first_walk = _first_walk(session)
        if first_walk and first_walk.get("status") == "active" and first_walk.get("current_step") == "listen_pool":
            session.database.advance_quest(session.character.id, FOREST_ELF_FIRST_WALK.key, "reach_outer_grove")
        await session.send(
            "\r\nYou stop moving long enough for the forest to become specific. The river keeps sliding over stone. Insects continue under the leaves. Then the birds north of you go quiet together.\r\n"
            "A few breaths later they resume behind you, not ahead. Deer tracks bend away from the same brush. Fresh leaves have been flipped pale-side up without any wind strong enough to do it.\r\n"
            "Nothing announces a monster. The path simply stops behaving like a safe path. You can still go NORTH, but now you know where not to put your feet.\r\n"
            "Quest updated: The Old River Path.\r\n"
        )
        return True

    return False


async def _handle_stag(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    if session.character.current_room != FOREST_ELF_OUTER_GROVE_KEY:
        return False
    quest = _microquest(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "decide_stag":
        return False
    if session.active_enemy is not None:
        return False

    if normalized in {"examine stag", "look stag", "examine whitewood stag", "look whitewood stag", "examine snare", "look snare"}:
        session.database.grant_flag(session.character.id, STAG_FOUND_FLAG)
        await session.send(
            "\r\nA whitewood stag is down in the fern shadow beside the boundary oak, one foreleg caught in a rust-dark iron cable. It has already spent its panic. Now it watches you with its breath coming hard and shallow.\r\n"
            "The snare is old, not Circle work, and the catch can be opened if you keep the leg still instead of yanking against it. You can FREE STAG carefully or LEAVE STAG and report it to the lookout.\r\n"
        )
        return True

    if normalized in {"free stag", "free the stag", "open snare", "release stag", "release the stag", "cut snare"}:
        session.database.grant_flag(session.character.id, STAG_FOUND_FLAG)
        session.database.grant_flag(session.character.id, STAG_RESCUED_FLAG)
        session.database.advance_quest(session.character.id, WHAT_DID_YOU_HEAR.key, "report_lookout")
        await session.send(
            "\r\nYou pin the cable against the earth instead of pulling the leg. When the rusted catch finally opens, you let the stag choose the moment to stand.\r\n"
            "It favors the leg once, twice, then disappears south through cover without looking back. No blessing settles over you. No reward appears. There is only an empty snare and one animal no longer inside it.\r\n"
            "Whitewood Lookout is WEST. Take the river moss to Serael Reedwatch.\r\n"
        )
        return True

    if normalized in {"leave stag", "leave the stag", "do not free stag", "report stag", "leave snare"}:
        session.database.grant_flag(session.character.id, STAG_FOUND_FLAG)
        session.database.grant_flag(session.character.id, STAG_LEFT_FLAG)
        session.database.advance_quest(session.character.id, WHAT_DID_YOU_HEAR.key, "report_lookout")
        await session.send(
            "\r\nYou leave the cable alone rather than risk worsening the injury. The stag remains alert, and the lookout is only a short climb away.\r\n"
            "Whitewood Lookout is WEST. Take the river moss to Serael and report the animal with the rest of what you noticed.\r\n"
        )
        return True

    return False


async def _handle_lookout(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    if session.character.current_room != WHITEWOOD_LOOKOUT_KEY:
        return False
    quest = _microquest(session)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")

    if normalized in {"talk serael", "talk to serael", "talk lookout", "talk to lookout", "talk keeper", "talk reedwatch"}:
        if step == "report_lookout":
            if session.database.item_quantity(session.character.id, RIVER_MOSS_BUNDLE_KEY) <= 0:
                _ensure_one(session, RIVER_MOSS_BUNDLE_KEY)
            _consume_all(session, RIVER_MOSS_BUNDLE_KEY)
            session.database.advance_quest(session.character.id, WHAT_DID_YOU_HEAR.key, "answer_question")
            await session.send(
                "\r\nSerael takes the moss, kneels, and presses it into the dry seam around the living whitewood rail. Only after the ordinary job is finished does she look up.\r\n"
                "'Good. Now the part I actually care about.' She nods toward the river path. 'What did you hear?'\r\n"
                "You can REPORT BIRDS, REPORT TRACKS, REPORT BARKJAW, or REPORT NOTHING. Tell her what you actually noticed.\r\n"
            )
            return True
        if step == "answer_question":
            await session.send("\r\nSerael waits without helping. 'What did you hear?' REPORT BIRDS, REPORT TRACKS, REPORT BARKJAW, or REPORT NOTHING.\r\n")
            return True

    reports = {
        "report birds": "The birds went quiet northward before anything showed itself.",
        "report quiet": "The birds went quiet northward before anything showed itself.",
        "report tracks": "The deer tracks turned away before the dangerous brush, and the leaves showed where they changed course.",
        "report barkjaw": "A Barkjaw was using the quiet patch as an ambush. I learned that after it was already close.",
        "report nothing": "I did not notice enough before I moved.",
    }
    if normalized not in reports or step != "answer_question":
        return False

    flags = _flags(session)
    if normalized in {"report birds", "report quiet"} and PATH_WARNING_HEARD_FLAG in flags:
        response = "Serael nods once. 'Good. Silence is sometimes an action.'"
    elif normalized == "report tracks" and PATH_SIGN_READ_FLAG in flags:
        response = "Serael nods toward the path. 'Good. Animals spend their lives voting with their feet.'"
    elif normalized == "report barkjaw" and BARKJAW_AMBUSHED_FLAG in flags:
        response = "Serael does not mock you. 'Also true. Pain is expensive information, but it is still information if you keep it.'"
    elif normalized == "report nothing":
        response = "Serael shrugs. 'Then next time stop earlier. Nobody is born observant.'"
    else:
        response = "Serael tilts her head. 'That may be a good answer another day. Today, keep your report tied to what you actually noticed.'"

    await session.send(f"\r\nYou tell her: '{reports[normalized]}'\r\n{response}\r\n")
    session.database.complete_quest(session.character.id, WHAT_DID_YOU_HEAR.key)
    session.database.grant_flag(session.character.id, WHAT_DID_YOU_HEAR_COMPLETE_FLAG)
    await session.send(
        "Quest complete: What Did You Hear?\r\n"
        "Serael turns back to the whitewood rail. 'The Circle can teach names later. First learn when the forest has stopped acting like itself.'\r\n"
    )
    return True


def install_reading_forest_runtime(player_session_class, world_service) -> None:
    install_reading_forest_content(world_service)
    if getattr(player_session_class, "_forest_elf_reading_forest_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_move_character = player_session_class.move_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if start_reading_forest_if_ready(self):
            await self.send(
                "\r\nNeris catches you before the river walk gets properly underway and hands you a cool leaf-wrapped bundle.\r\n"
                "'River moss for Serael at Whitewood Lookout. It is on your way if you are paying attention.'\r\n"
                "You receive a River Moss Bundle. The delivery is simple; carry it while you make the Old River Path walk.\r\n"
            )

    async def move_character(self, direction: str) -> None:
        if self.character is None or self.character.race != "forest_elf":
            await previous_move_character(self, direction)
            return

        just_started = start_reading_forest_if_ready(self)
        if just_started:
            await self.send(
                "\r\nAt the path mouth, Neris presses a cool leaf-wrapped bundle into your hands. 'River moss for Serael at Whitewood Lookout. Do not hurry just because the errand is ordinary.'\r\n"
                "You receive a River Moss Bundle.\r\n"
            )

        origin = self.character.current_room
        normalized = direction.lower()
        quest = _microquest(self)

        if (
            origin == FOREST_ELF_OUTER_GROVE_KEY
            and normalized == "west"
            and quest
            and quest.get("status") == "active"
            and quest.get("current_step") == "decide_stag"
        ):
            await self.send("The lookout is close, but the snared animal is still at your feet. EXAMINE STAG before leaving the grove.\r\n")
            return

        await previous_move_character(self, direction)
        if self.character is None:
            return

        if origin == FOREST_ELF_LISTENING_POOL_KEY and normalized == "north" and self.character.current_room == FOREST_ELF_OUTER_GROVE_KEY:
            quest = _microquest(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "read_path":
                flags = _flags(self)
                if PATH_WARNING_HEARD_FLAG in flags:
                    self.database.grant_flag(self.character.id, BARKJAW_AVOIDED_FLAG)
                    _advance_to_stag(self)
                    await self.send(
                        "\r\nBecause you noticed where the birds stopped, you leave the easy center of the trail before the brush closes around it. A Barkjaw explodes from cover a few paces away, jaws snapping on empty air where your leg would have been.\r\n"
                        "It does not chase once surprise is gone. The animal vanishes downslope. You avoided a fight by reading the forest before the fight existed.\r\n"
                        "Near the boundary oak, something pale moves low in the ferns. EXAMINE STAG.\r\n"
                    )
                else:
                    self.database.grant_flag(self.character.id, BARKJAW_AMBUSHED_FLAG)
                    if _begin_forced_combat(self, BARKJAW):
                        await self.send(
                            "\r\nThe birds vanish from your awareness a heartbeat too late. A Barkjaw launches from the brush at knee height, bark-plated jaws already open. It was not hidden by magic; you simply walked into the silence it created.\r\n"
                            "The Barkjaw attacks! Your normal attacks begin automatically.\r\n"
                        )

        if self.character.current_room == FOREST_ELF_BRIARSHADOW_THICKET_KEY and origin != FOREST_ELF_BRIARSHADOW_THICKET_KEY:
            flags = _flags(self)
            if STAG_RESCUED_FLAG in flags and STAG_RETURNED_FLAG not in flags:
                self.database.grant_flag(self.character.id, STAG_RETURNED_FLAG)
                await self.send(
                    "\r\nA pale antler flashes between the blackthorns. The whitewood stag you freed stands on a narrow rise, weight still slightly off one foreleg. It stamps once, then slips along a line of stone you would not have chosen.\r\n"
                    "You follow just far enough to see why. Two Hollowbacks are feeding in the lower hollow, bark-ridged backs dusted with pale fungus, agitated by something farther upstream. The stag's route carries you around them without a fight.\r\n"
                    "By the time you look back, it is gone. The forest has not repaid a debt. An animal simply remembered where it could move safely—and you were paying attention this time.\r\n"
                )
            elif HOLLOWBACK_ENCOUNTERED_FLAG not in flags:
                self.database.grant_flag(self.character.id, HOLLOWBACK_ENCOUNTERED_FLAG)
                if _begin_forced_combat(self, HOLLOWBACK):
                    await self.send(
                        "\r\nA deer-sized shape tears out of the briars instead of fleeing. Barklike ridges cup its back around a line of pale fungi, and its eyes are too wide with panic. This does not move like a healthy browsing animal defending normal ground.\r\n"
                        "A Hollowback charges!\r\n"
                    )

    def _enemy_in_current_room(self, target_text: str):
        if self.character is not None and self.character.race == "forest_elf":
            flags = _flags(self)
            if (
                self.character.current_room == FOREST_ELF_OUTER_GROVE_KEY
                and BARKJAW_AMBUSHED_FLAG in flags
                and BARKJAW_DEFEATED_FLAG not in flags
                and BARKJAW.matches(target_text)
            ):
                return EnemyState(BARKJAW)
        return previous_enemy_lookup(self, target_text)

    async def _finish_enemy_defeat(self, enemy) -> None:
        enemy_key = enemy.definition.key
        await previous_finish_enemy(self, enemy)
        if self.character is None or self.character.race != "forest_elf":
            return
        if enemy_key == BARKJAW_KEY:
            self.database.grant_flag(self.character.id, BARKJAW_DEFEATED_FLAG)
            _advance_to_stag(self)
            await self.send(
                "\r\nThe Barkjaw stops moving. The lesson is not that you were strong enough to kill it; the fight existed because you arrived after the useful warning.\r\n"
                "Near the boundary oak, a pale-antlered animal is caught low in the ferns. EXAMINE STAG.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "forest_elf":
            await previous_playing_prompt(self)
            return

        if start_reading_forest_if_ready(self):
            await self.send(
                "\r\nNeris sends a River Moss Bundle with you for Whitewood Lookout. The delivery is ordinary. The path is not obligated to stay ordinary.\r\n"
            )

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if await _handle_listening_pool(self, normalized):
            return
        if await _handle_stag(self, normalized):
            return
        if await _handle_lookout(self, normalized):
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {"help", "?"} and _microquest(self) and _microquest(self).get("status") == "active":
            await self.send(
                "Forest Elf path lesson: use EXAMINE and LISTEN when the forest changes. At the boundary, EXAMINE STAG; later take the moss WEST to Whitewood Lookout and TALK SERAEL.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = _enemy_in_current_room
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._forest_elf_reading_forest_installed = True
