from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_city import MOON_ELF_WIND_TERRACE_KEY, install_moon_elf_city_content
from mud.moon_elf_druid_start import (
    MOON_ELF_ALPINE_GARDEN_KEY,
    MOON_ELF_DRUID_BED_STABLE_FLAG,
    MOON_ELF_DRUID_COMPLETE_FLAG,
    MOON_ELF_DRUID_FIRST_NURTURE_FLAG,
    MOON_ELF_DRUID_PATH_VIEW_FLAG,
    MOON_ELF_DRUID_QUEST,
    MOON_ELF_DRUID_QUEST_KEY,
    MOON_ELF_DRUID_REFLECTOR_RESET_FLAG,
    MOON_ELF_DRUID_SHADE_VIEW_FLAG,
    NERA_VOSS_KEY,
    install_moon_elf_druid_content,
    install_moon_elf_druid_runtime,
    moon_elf_druid_augmentations,
)
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG, install_third_chair_content
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
    name: str = "Serai"
    race: str = "moon_elf"
    character_class: str = "druid"
    deity_key: str | None = None
    current_room: str = MOON_ELF_WIND_TERRACE_KEY
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


class MoonElfDruidStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()
        install_moon_elf_druid_content()

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

    def test_content_adds_safe_alpine_garden_and_druid_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[MOON_ELF_DRUID_QUEST_KEY], MOON_ELF_DRUID_QUEST)
        room = world.ROOMS_BY_KEY[MOON_ELF_ALPINE_GARDEN_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("druid", room.tags)
        self.assertIn("perspective", room.tags)
        self.assertIn("ordinary_care", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(NERA_VOSS_KEY, room.npc_keys)
        self.assertEqual(world.ROOMS_BY_KEY[MOON_ELF_WIND_TERRACE_KEY].exits["south"], MOON_ELF_ALPINE_GARDEN_KEY)

        augmentation = moon_elf_druid_augmentations()[MOON_ELF_ALPINE_GARDEN_KEY]
        self.assertGreaterEqual(len(augmentation.features), 7)
        self.assertGreaterEqual(len(augmentation.description_layers), 4)

    def test_world_service_gets_named_route_from_wind_terrace(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_moon_elf_druid_content(service)
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="druid", level=1)
        result = service.resolve_exit(MOON_ELF_WIND_TERRACE_KEY, "south", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, MOON_ELF_ALPINE_GARDEN_KEY)
        self.assertEqual(result.exit.name, "Alpine Light Garden")

    def test_only_moon_elf_druid_gets_extension_after_third_chair(self):
        class DruidSession(FakeSession):
            pass

        install_moon_elf_druid_runtime(DruidSession)
        druid = DruidSession()
        asyncio.run(druid.enter_character())
        quest = druid.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_nera")
        self.assertIn("Where the Light Falls", "".join(druid.outputs))

        class WizardSession(FakeSession):
            pass

        install_moon_elf_druid_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard"))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY))

        class ForestDruidSession(FakeSession):
            pass

        install_moon_elf_druid_runtime(ForestDruidSession)
        forest_druid = ForestDruidSession(character=FakeCharacter(race="forest_elf"))
        asyncio.run(forest_druid.enter_character())
        self.assertIsNone(forest_druid.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY))

    def test_extension_waits_until_shared_moon_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_moon_elf_druid_runtime(Session)
        session = Session(database=FakeDatabase(third_chair_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY))

    def test_two_views_are_required_and_can_be_read_in_either_order(self):
        class Session(FakeSession):
            pass

        install_moon_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_ALPINE_GARDEN_KEY

        for command in ("talk nera", "examine starbell bed", "view from water step"):
            session.command = command
            asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["current_step"], "compare_views")
        self.assertIn(MOON_ELF_DRUID_PATH_VIEW_FLAG, session.database.flags)
        self.assertNotIn(MOON_ELF_DRUID_SHADE_VIEW_FLAG, session.database.flags)

        session.command = "view from shade bench"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["current_step"], "check_light")

    def test_nurture_before_diagnosis_is_stopped(self):
        class Session(FakeSession):
            pass

        install_moon_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_ALPINE_GARDEN_KEY
        session.command = "talk nera"
        asyncio.run(session.playing_prompt())
        session.command = "nurture roots"
        asyncio.run(session.playing_prompt())

        quest = session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["current_step"], "inspect_bed")
        self.assertEqual(session.database.ability_uses, [])
        self.assertIn("care is not more accurate", "".join(session.outputs).lower())

    def test_full_sequence_corrects_cause_then_nurtures_and_waits(self):
        class Session(FakeSession):
            pass

        install_moon_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_ALPINE_GARDEN_KEY

        sequence = (
            ("talk nera", "inspect_bed"),
            ("examine starbell bed", "compare_views"),
            ("view from shade bench", "compare_views"),
            ("view from water step", "check_light"),
            ("check light", "reset_reflector"),
            ("reset daymirror", "nurture_roots"),
            ("nurture roots", "wait_watch"),
            ("wait and watch", "return_nera"),
        )
        for command, expected_step in sequence:
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(MOON_ELF_DRUID_REFLECTOR_RESET_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_DRUID_FIRST_NURTURE_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_DRUID_BED_STABLE_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "nurture", 1)])

        session.command = "talk nera"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(MOON_ELF_DRUID_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("care without clarity can still cause harm", output)
        self.assertIn("corrected the light before you strengthened the roots", output)
        self.assertIn("not suddenly perfect", output)

    def test_nurture_progress_cannot_be_farmed_by_replaying_step(self):
        class Session(FakeSession):
            pass

        install_moon_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_ALPINE_GARDEN_KEY
        session.database.advance_quest(1, MOON_ELF_DRUID_QUEST_KEY, "nurture_roots")
        session.database.grant_flag(1, MOON_ELF_DRUID_REFLECTOR_RESET_FLAG)
        session.command = "nurture roots"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, MOON_ELF_DRUID_QUEST_KEY, "nurture_roots")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "nurture", 1)])


if __name__ == "__main__":
    unittest.main()
