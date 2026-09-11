from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.forest_elf_home_and_omens import (
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    install_forest_elf_home_content,
)
from mud.forest_elf_stewardship import (
    FOREST_ELF_KEEPER_NURSERY_KEY,
    install_forest_elf_stewardship_content,
)
from mud.forest_elf_wizard_start import (
    FOREST_ELF_KILN_TERRACE_KEY,
    FOREST_ELF_WIZARD_COMPLETE_FLAG,
    FOREST_ELF_WIZARD_FIRST_COLDFIRE_FLAG,
    FOREST_ELF_WIZARD_KILN_READ_FLAG,
    FOREST_ELF_WIZARD_QUEST,
    FOREST_ELF_WIZARD_QUEST_KEY,
    FOREST_ELF_WIZARD_TILE_FIRED_FLAG,
    FOREST_ELF_WIZARD_TILE_RACKED_FLAG,
    FOREST_ELF_WIZARD_VENTS_SET_FLAG,
    LETHRA_CLAYBOUGH_KEY,
    forest_elf_wizard_augmentations,
    install_forest_elf_wizard_content,
    install_forest_elf_wizard_runtime,
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
    name: str = "Caelir"
    race: str = "forest_elf"
    character_class: str = "wizard"
    deity_key: str | None = None
    current_room: str = FOREST_ELF_KEEPER_NURSERY_KEY
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


class ForestElfWizardStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_forest_elf_stewardship_content()
        install_forest_elf_home_content()
        install_forest_elf_wizard_content()

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

    def test_content_adds_safe_practical_kiln_and_wizard_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[FOREST_ELF_WIZARD_QUEST_KEY], FOREST_ELF_WIZARD_QUEST)
        room = world.ROOMS_BY_KEY[FOREST_ELF_KILN_TERRACE_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("wizard", room.tags)
        self.assertIn("community_work", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(LETHRA_CLAYBOUGH_KEY, room.npc_keys)
        self.assertEqual(
            world.ROOMS_BY_KEY[FOREST_ELF_KEEPER_NURSERY_KEY].exits["south"],
            FOREST_ELF_KILN_TERRACE_KEY,
        )

        augmentation = forest_elf_wizard_augmentations()[FOREST_ELF_KILN_TERRACE_KEY]
        self.assertGreaterEqual(len(augmentation.features), 6)
        self.assertGreaterEqual(len(augmentation.description_layers), 3)

    def test_world_service_gets_named_route_from_nursery(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_forest_elf_wizard_content(service)
        context = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="wizard", level=1)
        result = service.resolve_exit(FOREST_ELF_KEEPER_NURSERY_KEY, "south", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, FOREST_ELF_KILN_TERRACE_KEY)
        self.assertEqual(result.exit.name, "Tile Kiln Terrace")

    def test_only_forest_elf_wizard_gets_extension_after_shared_opening(self):
        class WizardSession(FakeSession):
            pass

        install_forest_elf_wizard_runtime(WizardSession)
        wizard = WizardSession()
        asyncio.run(wizard.enter_character())
        quest = wizard.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_lethra")
        self.assertIn("The Useful Heat", "".join(wizard.outputs))

        class DruidSession(FakeSession):
            pass

        install_forest_elf_wizard_runtime(DruidSession)
        druid = DruidSession(character=FakeCharacter(character_class="druid"))
        asyncio.run(druid.enter_character())
        self.assertIsNone(druid.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY))

        class MoonWizardSession(FakeSession):
            pass

        install_forest_elf_wizard_runtime(MoonWizardSession)
        moon_wizard = MoonWizardSession(character=FakeCharacter(race="moon_elf"))
        asyncio.run(moon_wizard.enter_character())
        self.assertIsNone(moon_wizard.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY))

    def test_extension_waits_until_shared_forest_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_forest_elf_wizard_runtime(Session)
        session = Session(database=FakeDatabase(opening_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY))

    def test_full_sequence_uses_coldfire_as_controlled_craft_not_performance(self):
        class Session(FakeSession):
            pass

        install_forest_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_KILN_TERRACE_KEY

        for command, expected_step in (
            ("talk lethra", "inspect_tile"),
            ("examine green tile", "inspect_kiln"),
            ("examine kiln", "set_vents"),
            ("set vents", "fire_tile"),
            ("coldfire burst kiln", "inspect_fired_tile"),
            ("examine fired tile", "rack_tile"),
            ("move tile to rack", "return_lethra"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(FOREST_ELF_WIZARD_KILN_READ_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_WIZARD_VENTS_SET_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_WIZARD_FIRST_COLDFIRE_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_WIZARD_TILE_FIRED_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_WIZARD_TILE_RACKED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "coldfire_burst", 1)])

        session.command = "talk lethra"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, FOREST_ELF_WIZARD_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(FOREST_ELF_WIZARD_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("coldfire burst", output)
        self.assertIn("a good wizard is allowed to use a lever", output)
        self.assertIn("magic happened", output)
        self.assertIn("magic is a tool, not a performance", output)
        self.assertIn("probably never know which wizard fired it", output)

    def test_coldfire_training_cannot_be_replayed_for_free_skill_progress(self):
        class Session(FakeSession):
            pass

        install_forest_elf_wizard_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_KILN_TERRACE_KEY
        session.database.grant_flag(1, FOREST_ELF_WIZARD_VENTS_SET_FLAG)
        session.database.advance_quest(1, FOREST_ELF_WIZARD_QUEST_KEY, "fire_tile")
        session.command = "coldfire burst kiln"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, FOREST_ELF_WIZARD_QUEST_KEY, "fire_tile")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "coldfire_burst", 1)])


if __name__ == "__main__":
    unittest.main()
