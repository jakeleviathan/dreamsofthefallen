from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.forest_elf_home_and_omens import (
    FOREST_ELF_ANOMALY_BIRDS_FLAG,
    FOREST_ELF_ANOMALY_TRACKS_FLAG,
    FOREST_ELF_CIRCLE_COMPARED_FLAG,
    FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG,
    FOREST_ELF_HEARTHWALK_KEY,
    FOREST_ELF_HOME_ROUNDS_FLAG,
    FOREST_ELF_HUSHED_VERGE_KEY,
    FOREST_ELF_LENS_BRUTE_FLAG,
    FOREST_ELF_LENS_DRUID_FLAG,
    FOREST_ELF_LENS_NECROMANCER_FLAG,
    FOREST_ELF_LENS_PRIEST_FLAG,
    FOREST_ELF_LENS_WIZARD_FLAG,
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    FOREST_ELF_VERGE_ACCESS_FLAG,
    FOREST_ELF_VERGE_STUDIED_FLAG,
    KEEPER_PARCEL_KEY,
    MORNING_ALREADY_UNDERWAY,
    NERIS_WILLOWHAND,
    ONE_TURN_FARTHER,
    QUIET_IS_DIFFERENT,
    TALEN_MOSSSTEP,
    _grandfather_if_needed,
    _handle_anomaly_actions,
    _handle_final_actions,
    _handle_home_actions,
    _prepare_fresh_opening,
    _talk_neris,
    _talk_talen,
    forest_elf_home_augmentations,
    install_forest_elf_home_content,
    reconcile_forest_elf_expanded_opening,
)
from mud.forest_elf_nurture import FOREST_ELF_HEARTSEED_QUEST, FOREST_ELF_NURTURE_COMPLETE_FLAG
from mud.quests import FOREST_ELF_FIRST_WALK
from mud.stats import CharacterStats
from mud.world import (
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_START_ROOM_KEY,
)


class FakeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)


def move(session: FakeSession, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    refreshed = session.database.get_character_by_name(session.character.name)
    assert refreshed is not None
    session.character = refreshed


class ForestElfHomeAndOmensTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        self.item_tuple = crafting.ITEMS
        self.item_map = dict(crafting.ITEMS_BY_KEY)
        install_forest_elf_home_content()

    def tearDown(self):
        legacy_world.ROOMS = self.rooms
        legacy_world.ROOMS_BY_KEY.clear()
        legacy_world.ROOMS_BY_KEY.update(self.rooms_by_key)
        legacy_world.NPCS = self.npcs
        legacy_world.NPCS_BY_KEY.clear()
        legacy_world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quest_map)
        crafting.ITEMS = self.item_tuple
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.item_map)

    def _session(self, name: str = "Willow", character_class: str = "wizard"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "forest_home.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(
            account.id,
            name,
            "forest_elf",
            character_class,
            stats=CharacterStats(),
        )
        return temp, database, FakeSession(database, character)

    def _finish_home_round(self, session: FakeSession) -> None:
        move(session, FOREST_ELF_HEARTHWALK_KEY)
        self.assertTrue(asyncio.run(_talk_neris(session)))
        move(session, "forest_elf_greenway")
        # The live runtime intercepts TALK SELA. Directly exercise the same
        # state transition through the home action path around it.
        quest = session.database.get_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key)
        self.assertEqual(quest["current_step"], "deliver_parcel")
        session.database.consume_item(session.character.id, KEEPER_PARCEL_KEY, 1)
        session.database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "check_marker")
        self.assertTrue(asyncio.run(_handle_home_actions(session, "check trail marker")))
        self.assertTrue(asyncio.run(_handle_home_actions(session, "reset trail marker")))
        move(session, FOREST_ELF_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_handle_home_actions(session, "set meeting cups")))

    def test_fresh_elf_defers_old_lessons_until_home_rounds(self):
        temp, database, session = self._session("Fresh")
        self.addCleanup(temp.cleanup)

        self.assertTrue(_prepare_fresh_opening(session))
        home = database.get_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key)
        heartseed = database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
        first_walk = database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)

        self.assertEqual(home["current_step"], "talk_neris")
        self.assertEqual(heartseed["current_step"], "await_home_rounds")
        self.assertEqual(first_walk["current_step"], "await_home_rounds")
        self.assertEqual(database.item_quantity(session.character.id, KEEPER_PARCEL_KEY), 0)

    def test_home_round_is_food_marker_and_meeting_setup_then_releases_heartseed(self):
        temp, database, session = self._session("Home")
        self.addCleanup(temp.cleanup)
        self.assertTrue(_prepare_fresh_opening(session))

        move(session, FOREST_ELF_HEARTHWALK_KEY)
        self.assertTrue(asyncio.run(_talk_neris(session)))
        self.assertEqual(database.item_quantity(session.character.id, KEEPER_PARCEL_KEY), 1)
        move(session, "forest_elf_greenway")
        database.consume_item(session.character.id, KEEPER_PARCEL_KEY, 1)
        database.advance_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key, "check_marker")
        self.assertTrue(asyncio.run(_handle_home_actions(session, "check trail marker")))
        self.assertTrue(asyncio.run(_handle_home_actions(session, "reset trail marker")))
        move(session, FOREST_ELF_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_handle_home_actions(session, "set meeting cups")))

        self.assertIn(FOREST_ELF_HOME_ROUNDS_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "speak_keeper")
        output = "".join(session.outputs).lower()
        self.assertIn("bread", output)
        self.assertIn("maintenance", output)
        self.assertIn("meeting", output)

    def test_existing_heartseed_and_river_walk_become_middle_of_larger_arc(self):
        temp, database, session = self._session("Sequence")
        self.addCleanup(temp.cleanup)
        self.assertTrue(_prepare_fresh_opening(session))
        self._finish_home_round(session)

        database.complete_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
        database.grant_flag(session.character.id, FOREST_ELF_NURTURE_COMPLETE_FLAG)
        self.assertEqual(reconcile_forest_elf_expanded_opening(session), "first_walk_started")
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)["current_step"], "leave_clearing")

        database.complete_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)
        database.grant_flag(session.character.id, "forest_elf_first_walk_completed")
        self.assertEqual(reconcile_forest_elf_expanded_opening(session), "anomaly_started")
        self.assertEqual(database.get_quest(session.character.id, QUIET_IS_DIFFERENT.key)["current_step"], "inspect_tracks")

        move(session, FOREST_ELF_OUTER_GROVE_KEY)
        self.assertTrue(asyncio.run(_handle_anomaly_actions(session, "examine hurried tracks")))
        move(session, FOREST_ELF_LISTENING_POOL_KEY)
        self.assertTrue(asyncio.run(_handle_anomaly_actions(session, "listen birds")))
        move(session, FOREST_ELF_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_handle_anomaly_actions(session, "attend circle")))

        flags = database.list_flags(session.character.id)
        self.assertIn(FOREST_ELF_ANOMALY_TRACKS_FLAG, flags)
        self.assertIn(FOREST_ELF_ANOMALY_BIRDS_FLAG, flags)
        self.assertIn(FOREST_ELF_CIRCLE_COMPARED_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, ONE_TURN_FARTHER.key)["current_step"], "meet_talen")
        output = "".join(session.outputs).lower()
        self.assertIn("beekeeper", output)
        self.assertIn("frogs", output)
        self.assertIn("does not declare a curse", output)

    def test_all_five_classes_read_same_verge_through_different_training(self):
        expected = {
            "druid": (FOREST_ELF_LENS_DRUID_FLAG, "timing is wrong"),
            "wizard": (FOREST_ELF_LENS_WIZARD_FLAG, "residue repeats"),
            "priest": (FOREST_ELF_LENS_PRIEST_FLAG, "usual echo"),
            "necromancer": (FOREST_ELF_LENS_NECROMANCER_FLAG, "delaying a transition"),
            "brute": (FOREST_ELF_LENS_BRUTE_FLAG, "fear had a direction"),
        }
        for index, (character_class, (flag, phrase)) in enumerate(expected.items()):
            with self.subTest(character_class=character_class):
                temp, database, session = self._session(f"Lens{index}", character_class)
                self.addCleanup(temp.cleanup)
                database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "meet_talen")
                move(session, FOREST_ELF_OUTER_GROVE_KEY)
                self.assertTrue(asyncio.run(_talk_talen(session)))
                self.assertIn(FOREST_ELF_VERGE_ACCESS_FLAG, database.list_flags(session.character.id))
                move(session, FOREST_ELF_HUSHED_VERGE_KEY)
                # Entering the verge advances to the class observation.
                asyncio.run(_handle_final_actions(session, ""))
                self.assertTrue(asyncio.run(_handle_final_actions(session, "study signs")))
                flags = database.list_flags(session.character.id)
                self.assertIn(flag, flags)
                self.assertIn(FOREST_ELF_VERGE_STUDIED_FLAG, flags)
                self.assertIn(phrase, "".join(session.outputs).lower())

    def test_reporting_class_lens_finishes_opening_without_solving_mystery(self):
        temp, database, session = self._session("Finish", "necromancer")
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "meet_talen")
        move(session, FOREST_ELF_OUTER_GROVE_KEY)
        asyncio.run(_talk_talen(session))
        move(session, FOREST_ELF_HUSHED_VERGE_KEY)
        asyncio.run(_handle_final_actions(session, "study signs"))
        move(session, FOREST_ELF_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_handle_final_actions(session, "report signs")))

        self.assertEqual(database.get_quest(session.character.id, ONE_TURN_FARTHER.key)["status"], "completed")
        self.assertIn(FOREST_ELF_OPENING_COMPLETE_FLAG, database.list_flags(session.character.id))
        output = "".join(session.outputs).lower()
        self.assertIn("larger mystery", output)
        self.assertIn("owes us neither comfort nor explanation", output)

    def test_legacy_forest_elf_progress_is_grandfathered_without_rewind(self):
        temp, database, session = self._session("Legacy")
        self.addCleanup(temp.cleanup)
        database.advance_quest(session.character.id, FOREST_ELF_FIRST_WALK.key, "study_waystone")

        self.assertFalse(_prepare_fresh_opening(session))
        _grandfather_if_needed(session)
        self.assertIn(FOREST_ELF_EXPANDED_GRANDFATHERED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)["current_step"], "study_waystone")
        self.assertIsNone(database.get_quest(session.character.id, MORNING_ALREADY_UNDERWAY.key))

    def test_content_adds_real_home_space_and_supervised_verge(self):
        self.assertIn(FOREST_ELF_HEARTHWALK_KEY, legacy_world.ROOMS_BY_KEY)
        self.assertIn(FOREST_ELF_HUSHED_VERGE_KEY, legacy_world.ROOMS_BY_KEY)
        self.assertEqual(legacy_world.ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY].exits["west"], FOREST_ELF_HEARTHWALK_KEY)
        self.assertEqual(legacy_world.ROOMS_BY_KEY[FOREST_ELF_OUTER_GROVE_KEY].exits["east"], FOREST_ELF_HUSHED_VERGE_KEY)
        self.assertIn(NERIS_WILLOWHAND.key, legacy_world.NPCS_BY_KEY)
        self.assertIn(TALEN_MOSSSTEP.key, legacy_world.NPCS_BY_KEY)

        augmentations = forest_elf_home_augmentations()
        verge = augmentations[FOREST_ELF_OUTER_GROVE_KEY]
        east = next(value for value in verge.exit_overrides if value.direction == "east")
        self.assertIn(FOREST_ELF_VERGE_ACCESS_FLAG, east.condition.required_flags)
        final_room = augmentations[FOREST_ELF_HUSHED_VERGE_KEY]
        self.assertGreaterEqual(len(final_room.features), 3)
        class_layers = {layer.condition.classes for layer in final_room.description_layers}
        self.assertIn(("druid",), class_layers)
        self.assertIn(("wizard",), class_layers)
        self.assertIn(("priest",), class_layers)
        self.assertIn(("necromancer",), class_layers)
        self.assertIn(("brute",), class_layers)


if __name__ == "__main__":
    unittest.main()
