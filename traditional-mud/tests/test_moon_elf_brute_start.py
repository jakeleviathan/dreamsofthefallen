from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_brute_start import (
    KALEN_SORR_KEY,
    MOON_ELF_BRUTE_BRACE_SET_FLAG,
    MOON_ELF_BRUTE_COMPLETE_FLAG,
    MOON_ELF_BRUTE_FRAME_STABLE_FLAG,
    MOON_ELF_BRUTE_INNER_VIEW_FLAG,
    MOON_ELF_BRUTE_MECHANISM_RESET_FLAG,
    MOON_ELF_BRUTE_OUTER_VIEW_FLAG,
    MOON_ELF_BRUTE_QUEST,
    MOON_ELF_BRUTE_QUEST_KEY,
    MOON_ELF_BRUTE_STRAIN_FOUND_FLAG,
    MOON_ELF_BRUTE_WEIGHT_TAKEN_FLAG,
    MOON_ELF_HIGH_SPAN_WALK_KEY,
    install_moon_elf_brute_content,
    install_moon_elf_brute_runtime,
    moon_elf_brute_augmentations,
)
from mud.moon_elf_city import MOON_ELF_HORIZON_DECK_KEY, install_moon_elf_city_content
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG, install_third_chair_content
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self, *, third_chair_complete: bool = True) -> None:
        self.flags: set[str] = set()
        if third_chair_complete:
            self.flags.add(MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG)
        self.quests: dict[str, dict[str, str | None]] = {}

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


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Taren"
    race: str = "moon_elf"
    character_class: str = "brute"
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


class MoonElfBruteStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()
        install_moon_elf_brute_content()

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

    def test_content_adds_safe_high_span_worksite_and_brute_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[MOON_ELF_BRUTE_QUEST_KEY], MOON_ELF_BRUTE_QUEST)
        room = world.ROOMS_BY_KEY[MOON_ELF_HIGH_SPAN_WALK_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("brute", room.tags)
        self.assertIn("perspective", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(KALEN_SORR_KEY, room.npc_keys)
        self.assertEqual(world.ROOMS_BY_KEY[MOON_ELF_HORIZON_DECK_KEY].exits["south"], MOON_ELF_HIGH_SPAN_WALK_KEY)

        augmentation = moon_elf_brute_augmentations()[MOON_ELF_HIGH_SPAN_WALK_KEY]
        self.assertGreaterEqual(len(augmentation.features), 7)
        self.assertGreaterEqual(len(augmentation.description_layers), 4)

    def test_world_service_gets_named_route_from_horizon_deck(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_moon_elf_brute_content(service)
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="brute", level=1)
        result = service.resolve_exit(MOON_ELF_HORIZON_DECK_KEY, "south", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, MOON_ELF_HIGH_SPAN_WALK_KEY)
        self.assertEqual(result.exit.name, "High Span Service Walk")

    def test_only_moon_elf_brute_gets_extension_after_third_chair(self):
        class BruteSession(FakeSession):
            pass

        install_moon_elf_brute_runtime(BruteSession)
        brute = BruteSession()
        asyncio.run(brute.enter_character())
        quest = brute.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_kalen")
        self.assertIn("Before You Lift", "".join(brute.outputs))

        class WizardSession(FakeSession):
            pass

        install_moon_elf_brute_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard"))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY))

        class ForestBruteSession(FakeSession):
            pass

        install_moon_elf_brute_runtime(ForestBruteSession)
        forest_brute = ForestBruteSession(character=FakeCharacter(race="forest_elf"))
        asyncio.run(forest_brute.enter_character())
        self.assertIsNone(forest_brute.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY))

    def test_extension_waits_until_shared_moon_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_moon_elf_brute_runtime(Session)
        session = Session(database=FakeDatabase(third_chair_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY))

    def test_two_views_are_required_and_can_be_read_in_either_order(self):
        class Session(FakeSession):
            pass

        install_moon_elf_brute_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_HIGH_SPAN_WALK_KEY

        for command in ("talk kalen", "examine supply frame", "view from outer rail"):
            session.command = command
            asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["current_step"], "compare_views")
        self.assertIn(MOON_ELF_BRUTE_OUTER_VIEW_FLAG, session.database.flags)
        self.assertNotIn(MOON_ELF_BRUTE_INNER_VIEW_FLAG, session.database.flags)

        session.command = "view from inner rail"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["current_step"], "check_strain")

    def test_full_sequence_uses_careful_strength_without_combat_or_class_spell(self):
        class Session(FakeSession):
            pass

        install_moon_elf_brute_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_HIGH_SPAN_WALK_KEY

        sequence = (
            ("talk kalen", "inspect_frame"),
            ("examine supply frame", "compare_views"),
            ("view from inner rail", "compare_views"),
            ("view from outer rail", "check_strain"),
            ("check strain", "set_brace"),
            ("set safety brace", "take_weight"),
            ("take weight", "hold_steady"),
            ("hold steady", "verify_frame"),
            ("check frame", "return_kalen"),
        )
        for command, expected_step in sequence:
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(MOON_ELF_BRUTE_STRAIN_FOUND_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_BRUTE_BRACE_SET_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_BRUTE_WEIGHT_TAKEN_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_BRUTE_MECHANISM_RESET_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_BRUTE_FRAME_STABLE_FLAG, session.database.flags)

        session.command = "talk kalen"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(MOON_ELF_BRUTE_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("know what you are carrying", output)
        self.assertIn("strength", output)
        self.assertIn("first judgment", output)
        self.assertIn("hold steady", output)

    def test_force_first_is_stopped_and_does_not_advance_quest(self):
        class Session(FakeSession):
            pass

        install_moon_elf_brute_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_HIGH_SPAN_WALK_KEY
        session.command = "talk kalen"
        asyncio.run(session.playing_prompt())
        session.command = "lift frame"
        asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["current_step"], "inspect_frame")
        self.assertIn("read the load first", "".join(session.outputs).lower())


if __name__ == "__main__":
    unittest.main()
