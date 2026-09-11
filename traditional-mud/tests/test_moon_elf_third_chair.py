from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_city import MOON_ELF_SKYCOURT_KEY, install_moon_elf_city_content
from mud.moon_elf_third_chair import (
    ILYRA_SEN_KEY,
    MOON_ELF_CHOICE_KEEP_FLAG,
    MOON_ELF_CHOICE_NEIGHBORS_FLAG,
    MOON_ELF_CHOICE_REDRAW_FLAG,
    MOON_ELF_CHOICE_WIND_FLAG,
    MOON_ELF_FIRST_OVERLOOK_KEY,
    MOON_ELF_HEARD_SERA_FLAG,
    MOON_ELF_HEARD_TALIN_FLAG,
    MOON_ELF_ORCHARD_OVERLOOK_KEY,
    MOON_ELF_THIRD_CHAIR,
    MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG,
    MOON_ELF_THIRD_CHAIR_QUEST_KEY,
    MOON_ELF_THIRD_CHAIR_ROOM_KEY,
    MOON_ELF_THIRD_CHAIR_ROOM_KEYS,
    SERA_VALEGLASS_KEY,
    TALIN_ORROW_KEY,
    _choice_flag,
    install_third_chair_content,
    install_third_chair_runtime,
    third_chair_augmentations,
)
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self):
        self.flags: set[str] = set()
        self.quest = None

    def list_flags(self, _character_id):
        return frozenset(self.flags)

    def grant_flag(self, _character_id, flag_key):
        self.flags.add(flag_key)

    def get_quest(self, _character_id, quest_key):
        if quest_key != MOON_ELF_THIRD_CHAIR_QUEST_KEY:
            return None
        return self.quest

    def start_quest(self, _character_id, quest_key, step):
        if quest_key == MOON_ELF_THIRD_CHAIR_QUEST_KEY and self.quest is None:
            self.quest = {"quest_key": quest_key, "status": "active", "current_step": step}

    def advance_quest(self, _character_id, quest_key, step):
        if quest_key == MOON_ELF_THIRD_CHAIR_QUEST_KEY and self.quest is not None:
            self.quest["current_step"] = step

    def complete_quest(self, _character_id, quest_key):
        if quest_key == MOON_ELF_THIRD_CHAIR_QUEST_KEY and self.quest is not None:
            self.quest["status"] = "completed"
            self.quest["current_step"] = "complete"


@dataclass
class FakeCharacter:
    id: int = 1
    race: str = "moon_elf"
    current_room: str = MOON_ELF_THIRD_CHAIR_ROOM_KEY


class FakeSession:
    def __init__(self, command=""):
        self.character = FakeCharacter()
        self.database = FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = None

    async def send(self, text):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text):
        return self.command

    async def enter_character(self):
        self.outputs.append("BASE ENTER\n")

    async def playing_prompt(self):
        self.outputs.append(f"BASE COMMAND: {await self.prompt('> ')}\n")


class MoonElfThirdChairTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quest_map)

    def test_content_adds_three_safe_views_and_three_people_to_high_horizon(self):
        self.assertEqual(len(MOON_ELF_THIRD_CHAIR_ROOM_KEYS), 3)
        self.assertEqual(world.ROOMS_BY_KEY[MOON_ELF_SKYCOURT_KEY].exits["up"], MOON_ELF_THIRD_CHAIR_ROOM_KEY)
        for room_key in MOON_ELF_THIRD_CHAIR_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertIn("safe", room.tags)
            self.assertEqual(room.enemy_keys, ())
        chamber = world.ROOMS_BY_KEY[MOON_ELF_THIRD_CHAIR_ROOM_KEY]
        self.assertEqual(chamber.npc_keys, (ILYRA_SEN_KEY, SERA_VALEGLASS_KEY, TALIN_ORROW_KEY))
        self.assertIn(MOON_ELF_THIRD_CHAIR_QUEST_KEY, quests.QUESTS_BY_KEY)

    def test_new_rooms_have_rich_features_and_named_routes(self):
        augmentations = third_chair_augmentations()
        service = WorldService(
            rooms={key: world.ROOMS_BY_KEY[key] for key in MOON_ELF_THIRD_CHAIR_ROOM_KEYS},
            augmentations=augmentations,
        )
        # The chamber's down route points into the wider city and need not be in
        # this deliberately small service fixture.
        service.legacy_rooms[MOON_ELF_SKYCOURT_KEY] = world.ROOMS_BY_KEY[MOON_ELF_SKYCOURT_KEY]
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="wizard", level=1)
        for room_key in MOON_ELF_THIRD_CHAIR_ROOM_KEYS:
            augmentation = augmentations[room_key]
            self.assertGreaterEqual(len(augmentation.features), 2)
            self.assertGreaterEqual(len(augmentation.description_layers), 1)
            overrides = {item.direction: item for item in augmentation.exit_overrides}
            self.assertEqual(set(overrides), set(world.ROOMS_BY_KEY[room_key].exits))
            view = service.build_view(room_key, context)
            self.assertIsNotNone(view)
            self.assertGreaterEqual(len(view.features), 2)
            self.assertTrue(all(route.name for route in view.exits))

    def test_quest_teaches_counterview_before_physical_perspective(self):
        objectives = dict(MOON_ELF_THIRD_CHAIR.objective_steps)
        self.assertIn("sit third chair", objectives["sit_third_chair"].lower())
        self.assertIn("talk sera", objectives["hear_counterviews"].lower())
        self.assertIn("talk talin", objectives["hear_counterviews"].lower())
        self.assertIn("examine path", objectives["inspect_first_view"].lower())
        self.assertIn("examine orchard", objectives["inspect_second_view"].lower())
        self.assertIn("study the wind", objectives["choose_next_step"].lower())
        self.assertIn("ask the neighbors", objectives["choose_next_step"].lower())

    def test_runtime_requires_both_people_then_two_views(self):
        class Session(FakeSession):
            pass

        service = WorldService(
            rooms={key: world.ROOMS_BY_KEY[key] for key in (*MOON_ELF_THIRD_CHAIR_ROOM_KEYS, MOON_ELF_SKYCOURT_KEY)},
            augmentations=third_chair_augmentations(),
        )
        install_third_chair_runtime(Session, service)
        session = Session("talk ilyra")
        asyncio.run(session.enter_character())
        self.assertEqual(session.database.quest["current_step"], "meet_ilyra")

        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.quest["current_step"], "sit_third_chair")
        session.command = "sit third chair"
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.quest["current_step"], "hear_counterviews")

        session.command = "talk talin"
        asyncio.run(session.playing_prompt())
        self.assertIn(MOON_ELF_HEARD_TALIN_FLAG, session.database.flags)
        self.assertEqual(session.database.quest["current_step"], "hear_counterviews")

        session.command = "talk sera"
        asyncio.run(session.playing_prompt())
        self.assertIn(MOON_ELF_HEARD_SERA_FLAG, session.database.flags)
        self.assertEqual(session.database.quest["current_step"], "inspect_first_view")

        session.character.current_room = MOON_ELF_FIRST_OVERLOOK_KEY
        session.command = "examine path"
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.quest["current_step"], "inspect_second_view")

        session.character.current_room = MOON_ELF_ORCHARD_OVERLOOK_KEY
        session.command = "examine orchard"
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.quest["current_step"], "choose_next_step")
        output = "".join(session.outputs).lower()
        self.assertIn("both sera and talin were right about something", output)

    def test_all_four_final_answers_are_real_non_joke_completions(self):
        choices = {
            "redraw the path": MOON_ELF_CHOICE_REDRAW_FLAG,
            "keep the old path": MOON_ELF_CHOICE_KEEP_FLAG,
            "study the wind": MOON_ELF_CHOICE_WIND_FLAG,
            "ask the neighbors": MOON_ELF_CHOICE_NEIGHBORS_FLAG,
        }
        self.assertEqual({choice: _choice_flag(choice) for choice in choices}, choices)

        for command, expected_flag in choices.items():
            class Session(FakeSession):
                pass

            service = WorldService(
                rooms={key: world.ROOMS_BY_KEY[key] for key in (*MOON_ELF_THIRD_CHAIR_ROOM_KEYS, MOON_ELF_SKYCOURT_KEY)},
                augmentations=third_chair_augmentations(),
            )
            install_third_chair_runtime(Session, service)
            session = Session(command)
            session.character.current_room = MOON_ELF_ORCHARD_OVERLOOK_KEY
            session.database.start_quest(1, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "choose_next_step")
            asyncio.run(session.playing_prompt())
            self.assertEqual(session.database.quest["status"], "completed")
            self.assertIn(expected_flag, session.database.flags)
            self.assertIn(MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG, session.database.flags)
            output = "".join(session.outputs).lower()
            self.assertIn("quest complete: the third chair", output)
            self.assertIn("most miracles are considerably less impressive than advertised", output)

    def test_cautious_answers_receive_clarity_without_speed_line(self):
        for command in ("study the wind", "ask the neighbors"):
            class Session(FakeSession):
                pass

            service = WorldService(
                rooms={key: world.ROOMS_BY_KEY[key] for key in (*MOON_ELF_THIRD_CHAIR_ROOM_KEYS, MOON_ELF_SKYCOURT_KEY)},
                augmentations=third_chair_augmentations(),
            )
            install_third_chair_runtime(Session, service)
            session = Session(command)
            session.character.current_room = MOON_ELF_ORCHARD_OVERLOOK_KEY
            session.database.start_quest(1, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "choose_next_step")
            asyncio.run(session.playing_prompt())
            self.assertIn("clarity is not the same thing as reaching a conclusion quickly", "".join(session.outputs).lower())


if __name__ == "__main__":
    unittest.main()
