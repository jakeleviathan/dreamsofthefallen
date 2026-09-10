import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.forest_elf_nurture import (
    FOREST_ELF_GREENWAY_KEY,
    FOREST_ELF_HEARTSEED_BLOOMED_FLAG,
    FOREST_ELF_HEARTSEED_QUEST,
    FOREST_ELF_HEARTSEED_TENDED_FLAG,
    FOREST_ELF_NURTURE_COMPLETE_FLAG,
    MAELIS_FERNWARD,
    SILVERMOSS_SPRIG,
    _handle_forest_elf_nurture,
    _initialize_or_reconcile_forest_elf,
    _show_season_wheel,
    _talk_maelis,
    forest_elf_nurture_augmentations,
    install_forest_elf_nurture_content,
)
from mud.quests import FOREST_ELF_FIRST_WALK
from mud.room_engine import PlayerRoomContext, WorldService
from mud.stats import CharacterStats
from mud.world import FOREST_ELF_START_ROOM_KEY


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs = []

    async def send(self, text):
        self.outputs.append(text)


class ForestElfNurtureTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_forest_elf_nurture_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

    def _database_session(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "forest_elf.db")
        account = database.create_account("forest_test", "not-a-real-hash")
        character = database.create_character(
            account.id,
            "LioraTest",
            "forest_elf",
            "druid",
            CharacterStats(might=5, grace=7, love=7, mind=6, hp=10),
        )
        return temp, database, LiveLikeSession(database, character)

    def test_content_adds_keeper_real_herb_and_dynamic_room_features(self):
        self.assertIn(MAELIS_FERNWARD.key, world.NPCS_BY_KEY)
        self.assertIn(MAELIS_FERNWARD.key, world.ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY].npc_keys)
        self.assertIn(SILVERMOSS_SPRIG.key, crafting.ITEMS_BY_KEY)
        self.assertIn(FOREST_ELF_HEARTSEED_QUEST.key, quests.QUESTS_BY_KEY)

        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=forest_elf_nurture_augmentations())
        fresh = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="druid", level=1)
        tended = PlayerRoomContext(
            character_id=1,
            race_key="forest_elf",
            class_key="druid",
            level=1,
            character_flags=frozenset({FOREST_ELF_HEARTSEED_TENDED_FLAG}),
        )
        bloomed = PlayerRoomContext(
            character_id=1,
            race_key="forest_elf",
            class_key="druid",
            level=1,
            character_flags=frozenset({FOREST_ELF_HEARTSEED_TENDED_FLAG, FOREST_ELF_HEARTSEED_BLOOMED_FLAG}),
        )
        fresh_names = {feature.name for feature in service.build_view(FOREST_ELF_START_ROOM_KEY, fresh).features}
        tended_names = {feature.name for feature in service.build_view(FOREST_ELF_START_ROOM_KEY, tended).features}
        bloomed_names = {feature.name for feature in service.build_view(FOREST_ELF_START_ROOM_KEY, bloomed).features}
        self.assertIn("Struggling Heartseed", fresh_names)
        self.assertIn("Tended Heartseed", tended_names)
        self.assertIn("Opened Heartseed", bloomed_names)
        self.assertIn("Boundary Care Marks", {f.name for f in service.build_view(FOREST_ELF_GREENWAY_KEY, fresh).features})

    def test_nurture_prelude_coexists_with_existing_boundary_walk(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_forest_elf(session)
        nurture = database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
        boundary = database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)
        self.assertEqual(nurture["status"], "active")
        self.assertEqual(nurture["current_step"], "speak_keeper")
        self.assertEqual(boundary["status"], "active")
        self.assertEqual(boundary["current_step"], "leave_clearing")

    def test_full_heartseed_lesson_uses_diagnosis_herbalism_tending_and_patience(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_forest_elf(session)
        character_id = session.character.id

        self.assertTrue(asyncio.run(_talk_maelis(session)))
        self.assertEqual(database.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "inspect_heartseed")

        self.assertTrue(asyncio.run(_handle_forest_elf_nurture(session, "examine heartseed")))
        self.assertEqual(database.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "gather_silvermoss")

        self.assertTrue(asyncio.run(_handle_forest_elf_nurture(session, "gather silvermoss")))
        self.assertEqual(database.item_quantity(character_id, SILVERMOSS_SPRIG.key), 1)
        self.assertEqual(database.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "tend_heartseed")

        self.assertTrue(asyncio.run(_handle_forest_elf_nurture(session, "tend heartseed")))
        self.assertEqual(database.item_quantity(character_id, SILVERMOSS_SPRIG.key), 0)
        self.assertIn(FOREST_ELF_HEARTSEED_TENDED_FLAG, database.list_flags(character_id))
        self.assertEqual(database.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "wait_for_growth")

        # Reopen the database before the patience step: the lesson resumes exactly
        # where it stopped and does not recreate the consumed herb.
        reopened = Database(database.path)
        session.database = reopened
        session.character = reopened.get_character_by_name("LioraTest")
        _initialize_or_reconcile_forest_elf(session)
        self.assertEqual(reopened.item_quantity(character_id, SILVERMOSS_SPRIG.key), 0)
        self.assertEqual(reopened.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "wait_for_growth")

        self.assertTrue(asyncio.run(_handle_forest_elf_nurture(session, "wait")))
        self.assertIn(FOREST_ELF_HEARTSEED_BLOOMED_FLAG, reopened.list_flags(character_id))
        self.assertEqual(reopened.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "return_keeper")

        self.assertTrue(asyncio.run(_talk_maelis(session)))
        self.assertEqual(reopened.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["status"], "completed")
        self.assertIn(FOREST_ELF_NURTURE_COMPLETE_FLAG, reopened.list_flags(character_id))

        # Reconciliation and repeat dialogue remain idempotent.
        _initialize_or_reconcile_forest_elf(session)
        self.assertEqual(reopened.item_quantity(character_id, SILVERMOSS_SPRIG.key), 0)
        self.assertTrue(asyncio.run(_talk_maelis(session)))
        self.assertEqual(reopened.get_quest(character_id, FOREST_ELF_HEARTSEED_QUEST.key)["status"], "completed")

    def test_gathering_before_diagnosis_does_not_create_free_tutorial_loot(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_forest_elf(session)
        self.assertTrue(asyncio.run(_handle_forest_elf_nurture(session, "gather silvermoss")))
        self.assertEqual(database.item_quantity(session.character.id, SILVERMOSS_SPRIG.key), 0)
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "speak_keeper")

    def test_season_wheel_reports_current_season_as_practical_care(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        asyncio.run(_show_season_wheel(session))
        output = "".join(session.outputs).lower()
        self.assertIn("season wheel", output)
        self.assertIn("astralis is in", output)
        self.assertTrue(any(word in output for word in ("spring", "summer", "autumn", "winter")))


if __name__ == "__main__":
    unittest.main()
