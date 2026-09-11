from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.forest_elf_druid_start import (
    FOREST_ELF_DRUID_COMPLETE_FLAG,
    FOREST_ELF_DRUID_FIRST_HEAL_FLAG,
    FOREST_ELF_DRUID_QUEST,
    FOREST_ELF_DRUID_QUEST_KEY,
    FOREST_ELF_DRUID_ROOST_PREPARED_FLAG,
    FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG,
    FOREST_ELF_DRUID_THRUSH_RESTED_FLAG,
    FOREST_ELF_WARMHOUSE_KEY,
    SENNA_MOSSBELL_KEY,
    forest_elf_druid_augmentations,
    install_forest_elf_druid_content,
    install_forest_elf_druid_runtime,
)
from mud.forest_elf_home_and_omens import (
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    install_forest_elf_home_content,
)
from mud.forest_elf_stewardship import (
    FOREST_ELF_KEEPER_NURSERY_KEY,
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
    name: str = "Lethiel"
    race: str = "forest_elf"
    character_class: str = "druid"
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


class ForestElfDruidStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_forest_elf_stewardship_content()
        install_forest_elf_home_content()
        install_forest_elf_druid_content()

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

    def test_content_adds_safe_cozy_warmhouse_and_druid_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[FOREST_ELF_DRUID_QUEST_KEY], FOREST_ELF_DRUID_QUEST)
        room = world.ROOMS_BY_KEY[FOREST_ELF_WARMHOUSE_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("druid", room.tags)
        self.assertIn("cozy", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(SENNA_MOSSBELL_KEY, room.npc_keys)
        self.assertEqual(
            world.ROOMS_BY_KEY[FOREST_ELF_KEEPER_NURSERY_KEY].exits["east"],
            FOREST_ELF_WARMHOUSE_KEY,
        )

        augmentation = forest_elf_druid_augmentations()[FOREST_ELF_WARMHOUSE_KEY]
        self.assertGreaterEqual(len(augmentation.features), 5)
        self.assertGreaterEqual(len(augmentation.description_layers), 2)

    def test_world_service_gets_named_route_from_nursery(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_forest_elf_druid_content(service)
        context = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="druid", level=1)
        result = service.resolve_exit(FOREST_ELF_KEEPER_NURSERY_KEY, "east", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, FOREST_ELF_WARMHOUSE_KEY)
        self.assertEqual(result.exit.name, "The Warmhouse")

    def test_only_forest_elf_druid_gets_extension_after_shared_opening(self):
        class DruidSession(FakeSession):
            pass

        install_forest_elf_druid_runtime(DruidSession)
        druid = DruidSession()
        asyncio.run(druid.enter_character())
        quest = druid.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_senna")
        self.assertIn("The Light Left On", "".join(druid.outputs))

        class NecromancerSession(FakeSession):
            pass

        install_forest_elf_druid_runtime(NecromancerSession)
        necromancer = NecromancerSession(character=FakeCharacter(character_class="necromancer"))
        asyncio.run(necromancer.enter_character())
        self.assertIsNone(necromancer.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY))

        class GoblinDruidSession(FakeSession):
            pass

        install_forest_elf_druid_runtime(GoblinDruidSession)
        goblin = GoblinDruidSession(character=FakeCharacter(race="goblin"))
        asyncio.run(goblin.enter_character())
        self.assertIsNone(goblin.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY))

    def test_extension_waits_until_shared_forest_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_forest_elf_druid_runtime(Session)
        session = Session(database=FakeDatabase(opening_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY))

    def test_full_sequence_uses_minor_heal_then_ordinary_care_patience_and_release(self):
        class Session(FakeSession):
            pass

        install_forest_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_WARMHOUSE_KEY

        for command, expected_step in (
            ("talk senna", "examine_thrush"),
            ("examine thrush", "heal_thrush"),
            ("minor heal thrush", "prepare_roost"),
            ("prepare roost", "wait_rest"),
            ("wait", "open_shutter"),
            ("open shutter", "return_senna"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(FOREST_ELF_DRUID_FIRST_HEAL_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_DRUID_ROOST_PREPARED_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_DRUID_THRUSH_RESTED_FLAG, session.database.flags)
        self.assertIn(FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "minor_heal", 1)])

        session.command = "talk senna"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, FOREST_ELF_DRUID_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(FOREST_ELF_DRUID_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("minor heal", output)
        self.assertIn("used magic once, cloth twice, and patience the longest", output)
        self.assertIn("does not make you the owner of living things", output)
        self.assertIn("be ordinary when ordinary is enough", output)
        self.assertIn("you do not call it back", output)

    def test_minor_heal_training_cannot_be_replayed_for_free_skill_progress(self):
        class Session(FakeSession):
            pass

        install_forest_elf_druid_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = FOREST_ELF_WARMHOUSE_KEY
        session.database.advance_quest(1, FOREST_ELF_DRUID_QUEST_KEY, "heal_thrush")
        session.command = "minor heal thrush"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, FOREST_ELF_DRUID_QUEST_KEY, "heal_thrush")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "minor_heal", 1)])


if __name__ == "__main__":
    unittest.main()
