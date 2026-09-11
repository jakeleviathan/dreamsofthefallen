from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.mechanics as mechanics
import mud.quests as quests
import mud.world as world
from mud.forest_elf_brute_start import (
    ERYN_STONELEAF_KEY,
    FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG,
    FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG,
    FOREST_ELF_BRUTE_BRACE_SET_FLAG,
    FOREST_ELF_BRUTE_COMPLETE_FLAG,
    FOREST_ELF_BRUTE_CROSSING_CHECKED_FLAG,
    FOREST_ELF_BRUTE_FIRST_TAUNT_FLAG,
    FOREST_ELF_BRUTE_LOAD_READ_FLAG,
    FOREST_ELF_BRUTE_QUEST,
    FOREST_ELF_BRUTE_QUEST_KEY,
    FOREST_ELF_STORMFALL_CROSSING_KEY,
    forest_elf_brute_augmentations,
    install_forest_elf_brute_content,
    install_forest_elf_brute_runtime,
)
from mud.forest_elf_home_and_omens import FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.forest_elf_stewardship import (
    FOREST_ELF_RAINPOOL_TERRACE_KEY,
    install_forest_elf_stewardship_content,
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
    name: str = "Theren"
    race: str = "forest_elf"
    character_class: str = "brute"
    deity_key: str | None = None
    current_room: str = FOREST_ELF_RAINPOOL_TERRACE_KEY
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


class ForestElfBruteStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        self.druid_abilities = mechanics.FIXED_CLASS_ABILITIES.get("druid", ())
        install_forest_elf_stewardship_content()
        install_forest_elf_brute_content()

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
        mechanics.FIXED_CLASS_ABILITIES["druid"] = self.druid_abilities

    def test_content_adds_safe_path_worksite_and_brute_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[FOREST_ELF_BRUTE_QUEST_KEY], FOREST_ELF_BRUTE_QUEST)
        room = world.ROOMS_BY_KEY[FOREST_ELF_STORMFALL_CROSSING_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("brute", room.tags)
        self.assertIn("protection", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(ERYN_STONELEAF_KEY, room.npc_keys)
        self.assertEqual(
            world.ROOMS_BY_KEY[FOREST_ELF_RAINPOOL_TERRACE_KEY].exits["west"],
            FOREST_ELF_STORMFALL_CROSSING_KEY,
        )

        augmentation = forest_elf_brute_augmentations()[FOREST_ELF_STORMFALL_CROSSING_KEY]
        self.assertGreaterEqual(len(augmentation.features), 7)
        self.assertGreaterEqual(len(augmentation.description_layers), 3)

    def test_world_service_gets_named_route_from_rainpool(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_forest_elf_brute_content(service)
        context = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="brute", level=1)
        result = service.resolve_exit(FOREST_ELF_RAINPOOL_TERRACE_KEY, "west", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, FOREST_ELF_STORMFALL_CROSSING_KEY)
        self.assertEqual(result.exit.name, "Stormfall Crossing")

    def test_only_forest_elf_brute_gets_extension_after_shared_opening(self):
        class BruteSession(FakeSession):
            pass

        install_forest_elf_brute_runtime(BruteSession)
        brute = BruteSession()
        asyncio.run(brute.enter_character())
        quest = brute.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_eryn")
        self.assertIn("The Weight You Take", "".join(brute.outputs))

        class WizardSession(FakeSession):
            pass

        install_forest_elf_brute_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard"))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY))

        class TrollBruteSession(FakeSession):
            pass

        install_forest_elf_brute_runtime(TrollBruteSession)
        troll = TrollBruteSession(character=FakeCharacter(race="troll"))
        asyncio.run(troll.enter_character())
        self.assertIsNone(troll.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY))

    def test_extension_waits_until_shared_forest_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_forest_elf_brute_runtime(Session)
        session = Session(database=FakeDatabase(opening_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY))

    def test_full_sequence_teaches_controlled_strength_protection_and_nonlethal_taunt(self):
        class Session(FakeSession):
            pass

        install_forest_elf_brute_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_STORMFALL_CROSSING_KEY

        for command, expected_step in (
            ("talk eryn", "inspect_load"),
            ("examine beam", "set_brace"),
            ("set brace", "lift_beam"),
            ("lift beam with crew", "draw_boar"),
            ("taunt boar", "guide_boar"),
            ("back toward brush", "check_crossing"),
            ("examine crossing", "return_eryn"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(FOREST_ELF_BRUTE_LOAD_READ_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_BRUTE_BRACE_SET_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_BRUTE_FIRST_TAUNT_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_BRUTE_CROSSING_CHECKED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "taunt", 1)])

        session.command = "talk eryn"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, FOREST_ELF_BRUTE_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(FOREST_ELF_BRUTE_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("strong enough to lift is not the same thing as ready to lift", output)
        self.assertIn("do not hit it", output)
        self.assertIn("taunt is not clever insult", output)
        self.assertIn("protection is not the same thing as winning", output)
        self.assertIn("make danger choose you", output)

    def test_taunt_training_cannot_be_replayed_for_free_skill_progress(self):
        class Session(FakeSession):
            pass

        install_forest_elf_brute_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_STORMFALL_CROSSING_KEY
        session.database.grant_flag(1, FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG)
        session.database.advance_quest(1, FOREST_ELF_BRUTE_QUEST_KEY, "draw_boar")
        session.command = "taunt boar"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, FOREST_ELF_BRUTE_QUEST_KEY, "draw_boar")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "taunt", 1)])


if __name__ == "__main__":
    unittest.main()
