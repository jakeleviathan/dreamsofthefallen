from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_beliefs import MOON_ELF_WITNESS_PATH_KEY
from mud.moon_elf_city import (
    MOON_ELF_MOONMIRROR_WALK_KEY,
    install_moon_elf_city_content,
)
from mud.moon_elf_third_chair import (
    MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG,
    install_third_chair_content,
)
from mud.moon_elf_witness_start import (
    MAERA_VENN_KEY,
    MOON_ELF_WITNESS_COMPLETE_FLAG,
    MOON_ELF_WITNESS_FIRST_MENDING_FLAG,
    MOON_ELF_WITNESS_INFIRMARY_KEY,
    MOON_ELF_WITNESS_QUEST,
    MOON_ELF_WITNESS_QUEST_KEY,
    MOON_ELF_WITNESS_RESULT_CHECKED_FLAG,
    RALEN_ORR_KEY,
    install_moon_elf_witness_start_content,
    install_moon_elf_witness_start_runtime,
    witness_start_augmentations,
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
    name: str = "Ilyen"
    race: str = "moon_elf"
    character_class: str = "priest"
    deity_key: str | None = MOON_ELF_WITNESS_PATH_KEY
    current_room: str = MOON_ELF_MOONMIRROR_WALK_KEY
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


class MoonElfWitnessStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()
        install_moon_elf_witness_start_content()

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

    def test_content_adds_a_real_safe_infirmary_to_high_horizon(self):
        self.assertIs(quests.QUESTS_BY_KEY[MOON_ELF_WITNESS_QUEST_KEY], MOON_ELF_WITNESS_QUEST)
        room = world.ROOMS_BY_KEY[MOON_ELF_WITNESS_INFIRMARY_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("witness", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(MAERA_VENN_KEY, room.npc_keys)
        self.assertIn(RALEN_ORR_KEY, room.npc_keys)
        self.assertEqual(world.ROOMS_BY_KEY[MOON_ELF_MOONMIRROR_WALK_KEY].exits["east"], MOON_ELF_WITNESS_INFIRMARY_KEY)

        augmentation = witness_start_augmentations()[MOON_ELF_WITNESS_INFIRMARY_KEY]
        self.assertGreaterEqual(len(augmentation.features), 3)
        self.assertGreaterEqual(len(augmentation.description_layers), 1)

    def test_world_service_gets_named_public_route_to_infirmary(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_moon_elf_witness_start_content(service)
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="priest", level=1)
        result = service.resolve_exit(MOON_ELF_MOONMIRROR_WALK_KEY, "east", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, MOON_ELF_WITNESS_INFIRMARY_KEY)
        self.assertEqual(result.exit.name, "Open-Sky Infirmary")

    def test_only_witness_priest_gets_extension_after_third_chair(self):
        class WitnessSession(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(WitnessSession)
        witness = WitnessSession()
        asyncio.run(witness.enter_character())
        quest = witness.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_maera")
        self.assertIn("The Wound and the Whole", "".join(witness.outputs))

        class WizardSession(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard", deity_key=None))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY))

        class PatronSession(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(PatronSession)
        patron = PatronSession(character=FakeCharacter(deity_key="zerjz"))
        asyncio.run(patron.enter_character())
        self.assertIsNone(patron.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY))

    def test_extension_waits_until_shared_moon_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(Session)
        session = Session(database=FakeDatabase(third_chair_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY))

    def test_full_witness_care_sequence_uses_clearview_mending_and_checks_result(self):
        class Session(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_WITNESS_INFIRMARY_KEY

        for command, expected_step in (
            ("talk maera", "hear_ralen"),
            ("talk ralen", "inspect_injury"),
            ("examine ankle", "mend_injury"),
            ("mend ralen", "check_result"),
            ("examine gait", "return_maera"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(MOON_ELF_WITNESS_FIRST_MENDING_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_WITNESS_RESULT_CHECKED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "restoring_light", 1)])

        session.command = "talk maera"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_WITNESS_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(MOON_ELF_WITNESS_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("clearview mending", output)
        self.assertIn("nothing speaks from the moon", output)
        self.assertIn("you did not heal a metaphor", output)
        self.assertIn("second view ward", output)

    def test_first_mending_is_idempotent_and_does_not_farm_ability_progress(self):
        class Session(FakeSession):
            pass

        install_moon_elf_witness_start_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_WITNESS_INFIRMARY_KEY
        session.database.advance_quest(1, MOON_ELF_WITNESS_QUEST_KEY, "mend_injury")
        session.command = "mend ralen"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, MOON_ELF_WITNESS_QUEST_KEY, "mend_injury")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "restoring_light", 1)])


if __name__ == "__main__":
    unittest.main()
