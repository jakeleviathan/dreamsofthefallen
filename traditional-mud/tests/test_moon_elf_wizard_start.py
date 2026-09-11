from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_city import MOON_ELF_HORIZON_DECK_KEY, install_moon_elf_city_content
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG, install_third_chair_content
from mud.moon_elf_wizard_start import (
    CORIN_VAEL_KEY,
    MOON_ELF_CROWN_MIRROR_ARRAY_KEY,
    MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG,
    MOON_ELF_WIZARD_COMPLETE_FLAG,
    MOON_ELF_WIZARD_FIRST_COLDFIRE_FLAG,
    MOON_ELF_WIZARD_NORTH_VIEW_FLAG,
    MOON_ELF_WIZARD_QUEST,
    MOON_ELF_WIZARD_QUEST_KEY,
    MOON_ELF_WIZARD_SOUTH_VIEW_FLAG,
    install_moon_elf_wizard_content,
    install_moon_elf_wizard_runtime,
    moon_elf_wizard_augmentations,
)
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self, *, third_chair_complete: bool = True) -> None:
        self.flags: set[str] = set()
        if third_chair_complete:
            self.flags.add(MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG)
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
    name: str = "Averin"
    race: str = "moon_elf"
    character_class: str = "wizard"
    deity_key: str | None = None
    current_room: str = MOON_ELF_HORIZON_DECK_KEY
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


class MoonElfWizardStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()
        install_moon_elf_wizard_content()

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

    def test_content_adds_safe_civic_mirror_array_and_wizard_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[MOON_ELF_WIZARD_QUEST_KEY], MOON_ELF_WIZARD_QUEST)
        room = world.ROOMS_BY_KEY[MOON_ELF_CROWN_MIRROR_ARRAY_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("wizard", room.tags)
        self.assertIn("perspective", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(CORIN_VAEL_KEY, room.npc_keys)
        self.assertEqual(world.ROOMS_BY_KEY[MOON_ELF_HORIZON_DECK_KEY].exits["east"], MOON_ELF_CROWN_MIRROR_ARRAY_KEY)

        augmentation = moon_elf_wizard_augmentations()[MOON_ELF_CROWN_MIRROR_ARRAY_KEY]
        self.assertGreaterEqual(len(augmentation.features), 6)
        self.assertGreaterEqual(len(augmentation.description_layers), 3)

    def test_world_service_gets_named_route_from_horizon_deck(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_moon_elf_wizard_content(service)
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="wizard", level=1)
        result = service.resolve_exit(MOON_ELF_HORIZON_DECK_KEY, "east", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, MOON_ELF_CROWN_MIRROR_ARRAY_KEY)
        self.assertEqual(result.exit.name, "Crown Mirror Array")

    def test_only_moon_elf_wizard_gets_extension_after_third_chair(self):
        class WizardSession(FakeSession):
            pass

        install_moon_elf_wizard_runtime(WizardSession)
        wizard = WizardSession()
        asyncio.run(wizard.enter_character())
        quest = wizard.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_corin")
        self.assertIn("The First Explanation", "".join(wizard.outputs))

        class BruteSession(FakeSession):
            pass

        install_moon_elf_wizard_runtime(BruteSession)
        brute = BruteSession(character=FakeCharacter(character_class="brute"))
        asyncio.run(brute.enter_character())
        self.assertIsNone(brute.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY))

        class ForestWizardSession(FakeSession):
            pass

        install_moon_elf_wizard_runtime(ForestWizardSession)
        forest_wizard = ForestWizardSession(character=FakeCharacter(race="forest_elf"))
        asyncio.run(forest_wizard.enter_character())
        self.assertIsNone(forest_wizard.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY))

    def test_extension_waits_until_shared_moon_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_moon_elf_wizard_runtime(Session)
        session = Session(database=FakeDatabase(third_chair_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY))

    def test_two_sight_lines_are_required_and_can_be_read_in_either_order(self):
        class Session(FakeSession):
            pass

        install_moon_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_CROWN_MIRROR_ARRAY_KEY

        for command in ("talk corin", "examine mirror array", "sight south rail"):
            session.command = command
            asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["current_step"], "compare_views")
        self.assertIn(MOON_ELF_WIZARD_SOUTH_VIEW_FLAG, session.database.flags)
        self.assertNotIn(MOON_ELF_WIZARD_NORTH_VIEW_FLAG, session.database.flags)

        session.command = "sight north rail"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["current_step"], "check_bracket")

    def test_full_sequence_uses_coldfire_only_after_understanding_the_fault(self):
        class Session(FakeSession):
            pass

        install_moon_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_CROWN_MIRROR_ARRAY_KEY

        sequence = (
            ("talk corin", "inspect_array"),
            ("examine mirror array", "compare_views"),
            ("sight north rail", "compare_views"),
            ("sight south rail", "check_bracket"),
            ("check bracket", "set_collar"),
            ("set alignment collar", "heat_pin"),
            ("coldfire burst pin", "verify_beacon"),
            ("check beacon", "return_corin"),
        )
        for command, expected_step in sequence:
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(MOON_ELF_WIZARD_FIRST_COLDFIRE_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "coldfire_burst", 1)])

        session.command = "talk corin"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(MOON_ELF_WIZARD_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("first explanation", output)
        self.assertIn("power tells you what you can change", output)
        self.assertIn("understanding tells you what to change", output)
        self.assertIn("mirror", output)
        self.assertIn("bracket", output)

    def test_casting_at_the_obvious_answer_too_early_is_stopped(self):
        class Session(FakeSession):
            pass

        install_moon_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_CROWN_MIRROR_ARRAY_KEY
        session.command = "talk corin"
        asyncio.run(session.playing_prompt())
        session.command = "coldfire burst mirror"
        asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["current_step"], "inspect_array")
        self.assertEqual(session.database.ability_uses, [])
        self.assertIn("not yet", "".join(session.outputs).lower())

    def test_coldfire_progress_cannot_be_farmed_by_replaying_heat_step(self):
        class Session(FakeSession):
            pass

        install_moon_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_CROWN_MIRROR_ARRAY_KEY
        session.database.advance_quest(1, MOON_ELF_WIZARD_QUEST_KEY, "heat_pin")
        session.database.grant_flag(1, "moon_elf_wizard_collar_set")
        session.command = "coldfire burst pin"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, MOON_ELF_WIZARD_QUEST_KEY, "heat_pin")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "coldfire_burst", 1)])


if __name__ == "__main__":
    unittest.main()
