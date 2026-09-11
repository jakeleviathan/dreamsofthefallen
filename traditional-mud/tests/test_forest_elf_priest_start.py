from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.forest_elf_home_and_omens import (
    FOREST_ELF_HEARTHWALK_KEY,
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    install_forest_elf_home_content,
)
from mud.forest_elf_priest_start import (
    FOREST_ELF_PRIEST_COMPLETE_FLAG,
    FOREST_ELF_PRIEST_CUP_SET_FLAG,
    FOREST_ELF_PRIEST_NAME_SPOKEN_FLAG,
    FOREST_ELF_PRIEST_QUEST,
    FOREST_ELF_PRIEST_QUEST_KEY,
    FOREST_ELF_PRIEST_SILENCE_HELD_FLAG,
    FOREST_ELF_PRIEST_STORY_HEARD_FLAG,
    FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
    MIRA_ASHFERN_KEY,
    PRIEST_ALEN_WILLOWGREY_KEY,
    forest_elf_priest_augmentations,
    install_forest_elf_priest_content,
    install_forest_elf_priest_runtime,
)
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self, *, opening_complete: bool = True) -> None:
        self.flags: set[str] = set()
        if opening_complete:
            self.flags.add(FOREST_ELF_OPENING_COMPLETE_FLAG)
        self.quests: dict[str, dict[str, str | None]] = {}
        self.ability_uses: list[tuple[int, str, int]] = []

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def get_quest(self, _character_id: int, quest_key: str):
        row = self.quests.get(quest_key)
        return None if row is None else dict(row)

    def start_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests.setdefault(
            quest_key,
            {"quest_key": quest_key, "status": "active", "current_step": current_step},
        )

    def advance_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests[quest_key]["current_step"] = current_step

    def complete_quest(self, _character_id: int, quest_key: str):
        self.quests[quest_key]["status"] = "completed"
        self.quests[quest_key]["current_step"] = "complete"

    def record_ability_use(self, character_id: int, ability_key: str, skill_xp_gain: int = 1):
        self.ability_uses.append((character_id, ability_key, skill_xp_gain))


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Lethiel"
    race: str = "forest_elf"
    character_class: str = "priest"
    deity_key: str | None = "zerjz"
    current_room: str = FOREST_ELF_HEARTHWALK_KEY
    level: int = 1


class FakeState:
    DISCONNECTED = "disconnected"


class FakeSession:
    def __init__(self, command: str = "", *, character=None, database=None) -> None:
        self.character = character or FakeCharacter()
        self.database = database or FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text: str):
        return self.command

    async def enter_character(self):
        self.outputs.append("BASE ENTER\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.outputs.append(f"BASE COMMAND: {command}\n")


class ForestElfPriestStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_forest_elf_home_content()
        install_forest_elf_priest_content()

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

    def test_content_adds_safe_remembrance_arbor_and_two_people(self):
        self.assertIs(quests.QUESTS_BY_KEY[FOREST_ELF_PRIEST_QUEST_KEY], FOREST_ELF_PRIEST_QUEST)
        room = world.ROOMS_BY_KEY[FOREST_ELF_REMEMBRANCE_ARBOR_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("priest", room.tags)
        self.assertIn("remembrance", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(PRIEST_ALEN_WILLOWGREY_KEY, room.npc_keys)
        self.assertIn(MIRA_ASHFERN_KEY, room.npc_keys)
        self.assertEqual(
            world.ROOMS_BY_KEY[FOREST_ELF_HEARTHWALK_KEY].exits["south"],
            FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
        )
        augmentation = forest_elf_priest_augmentations()[FOREST_ELF_REMEMBRANCE_ARBOR_KEY]
        self.assertGreaterEqual(len(augmentation.features), 5)
        self.assertGreaterEqual(len(augmentation.description_layers), 3)

    def test_world_service_gets_named_route_from_hearthwalk(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_forest_elf_priest_content(service)
        context = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="priest", level=1)
        result = service.resolve_exit(FOREST_ELF_HEARTHWALK_KEY, "south", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, FOREST_ELF_REMEMBRANCE_ARBOR_KEY)
        self.assertEqual(result.exit.name, "Remembrance Arbor")

    def test_only_forest_elf_priest_gets_extension_after_shared_opening(self):
        class PriestSession(FakeSession):
            pass

        install_forest_elf_priest_runtime(PriestSession)
        priest = PriestSession()
        asyncio.run(priest.enter_character())
        quest = priest.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_alen")
        self.assertIn("One Cup Unfilled", "".join(priest.outputs))

        class DruidSession(FakeSession):
            pass

        install_forest_elf_priest_runtime(DruidSession)
        druid = DruidSession(character=FakeCharacter(character_class="druid", deity_key=None))
        asyncio.run(druid.enter_character())
        self.assertIsNone(druid.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY))

        class MoonElfPriestSession(FakeSession):
            pass

        install_forest_elf_priest_runtime(MoonElfPriestSession)
        moon = MoonElfPriestSession(character=FakeCharacter(race="moon_elf"))
        asyncio.run(moon.enter_character())
        self.assertIsNone(moon.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY))

    def test_extension_waits_until_shared_forest_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_forest_elf_priest_runtime(Session)
        session = Session(database=FakeDatabase(opening_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY))

    def test_all_three_deity_paths_are_acknowledged_without_turning_grief_into_spell_problem(self):
        expected = {
            "zerjz": "grief is not a wound",
            "tenebrous": "loving someone can be made safe from loss",
            "leviathan": "there is no culprit here for grief to prosecute",
        }
        for deity_key, phrase in expected.items():
            class Session(FakeSession):
                pass

            install_forest_elf_priest_runtime(Session)
            session = Session(character=FakeCharacter(deity_key=deity_key))
            asyncio.run(session.enter_character())
            session.character.current_room = FOREST_ELF_REMEMBRANCE_ARBOR_KEY
            session.command = "talk alen"
            asyncio.run(session.playing_prompt())
            output = "".join(session.outputs).lower()
            self.assertIn(phrase, output)
            self.assertEqual(session.database.ability_uses, [])

    def test_full_sequence_is_listening_ritual_silence_and_name_without_magic(self):
        class Session(FakeSession):
            pass

        install_forest_elf_priest_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_REMEMBRANCE_ARBOR_KEY

        for command, expected_step in (
            ("talk alen", "listen_mira"),
            ("talk mira", "inspect_table"),
            ("examine memory table", "set_cup"),
            ("set empty cup", "hold_silence"),
            ("hold silence", "speak_name"),
            ("speak sera's name", "return_alen"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(FOREST_ELF_PRIEST_STORY_HEARD_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_PRIEST_CUP_SET_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_PRIEST_SILENCE_HELD_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_PRIEST_NAME_SPOKEN_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [])

        session.command = "talk alen"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, FOREST_ELF_PRIEST_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(FOREST_ELF_PRIEST_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("ritual is not evidence", output)
        self.assertIn("you do not attach a sermon to the name", output)
        self.assertIn("you did not turn grief into a test of faith", output)
        self.assertIn("hold a moment without stealing it", output)


if __name__ == "__main__":
    unittest.main()
