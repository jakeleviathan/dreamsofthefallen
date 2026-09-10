from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.human_cathedral_faith import (
    DEACON_MERET_VALE_KEY,
    DORNA_IRONSTEP_KEY,
    HUMAN_BELLS_COMPLETE_FLAG,
    HUMAN_BELLS_QUEST,
    HUMAN_CATHEDRAL_GRANDFATHERED_DOOR_FLAG,
    HUMAN_CATHEDRAL_GRANDFATHERED_NAME_FLAG,
    HUMAN_CATHEDRAL_NAME_LITANY_FLAG,
    HUMAN_CATHEDRAL_OUTSIDER_PATIENCE_FLAG,
    HUMAN_CATHEDRAL_ROOM_KEYS,
    HUMAN_CATHEDRAL_VIGIL_BELL_FLAG,
    HUMAN_CROSSING_CHAPEL_KEY,
    HUMAN_HALL_OF_NAMES_KEY,
    HUMAN_KEPT_NAME_COMPLETE_FLAG,
    HUMAN_KEPT_NAME_QUEST,
    HUMAN_MERCY_CLOISTER_KEY,
    HUMAN_OPEN_DOOR_COMPLETE_FLAG,
    HUMAN_OPEN_DOOR_QUEST,
    cathedral_room_augmentations,
    handle_human_cathedral_command,
    install_human_cathedral_content,
    reconcile_human_cathedral_faith,
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


class HumanCathedralFaithTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_human_cathedral_content()

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

    def _session(self, name: str):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "cathedral.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(account.id, name, "human", "wizard")
        return temp, database, FakeSession(database, character)

    def test_cathedral_expands_into_three_religious_service_rooms(self):
        cathedral = legacy_world.ROOMS_BY_KEY["human_grand_cathedral"]
        self.assertEqual(cathedral.exits["east"], HUMAN_HALL_OF_NAMES_KEY)
        self.assertEqual(cathedral.exits["west"], HUMAN_MERCY_CLOISTER_KEY)
        self.assertEqual(cathedral.exits["north"], HUMAN_CROSSING_CHAPEL_KEY)
        self.assertEqual(set(HUMAN_CATHEDRAL_ROOM_KEYS), set(cathedral_room_augmentations()))
        for room_key in HUMAN_CATHEDRAL_ROOM_KEYS:
            augmentation = cathedral_room_augmentations()[room_key]
            self.assertGreaterEqual(len(augmentation.features), 2)
            self.assertGreaterEqual(len(augmentation.description_layers), 1)
        self.assertIn(DEACON_MERET_VALE_KEY, legacy_world.ROOMS_BY_KEY[HUMAN_MERCY_CLOISTER_KEY].npc_keys)
        self.assertIn(DORNA_IRONSTEP_KEY, legacy_world.ROOMS_BY_KEY[HUMAN_MERCY_CLOISTER_KEY].npc_keys)
        self.assertIn("religious", legacy_world.NPCS_BY_KEY["human_high_acolyte"].role)

    def test_name_we_keep_turns_summons_into_religious_identity_lesson(self):
        temp, database, session = self._session("Name")
        self.addCleanup(temp.cleanup)
        database.advance_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key, "find_cathedral")
        move(session, "human_grand_cathedral")

        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))
        kept = database.get_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key)
        self.assertEqual(kept["current_step"], "read_litany")
        self.assertEqual(database.get_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)["status"], "active")

        move(session, HUMAN_HALL_OF_NAMES_KEY)
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "read litany")))
        self.assertIn(HUMAN_CATHEDRAL_NAME_LITANY_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key)["current_step"], "light_crossing_lamp")

        move(session, HUMAN_CROSSING_CHAPEL_KEY)
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "light lamp")))
        move(session, "human_grand_cathedral")
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))

        self.assertIn(HUMAN_KEPT_NAME_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)["status"], "completed")
        training = database.get_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key)
        self.assertEqual(training["current_step"], "read_training_orders")
        output = "".join(session.outputs).lower()
        self.assertIn("not a monster", output)
        self.assertIn("fear may name the stranger", output)

    def test_open_door_teaches_hospitality_without_demanding_outsider_trust(self):
        temp, database, session = self._session("Mercy")
        self.addCleanup(temp.cleanup)
        database.complete_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        database.start_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key, "complete")
        database.complete_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key)
        reconcile_human_cathedral_faith(session)
        move(session, "human_grand_cathedral")

        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key)["current_step"], "meet_deacon")
        move(session, HUMAN_MERCY_CLOISTER_KEY)
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk deacon")))
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "serve bread")))
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "answer patience")))
        self.assertIn(HUMAN_CATHEDRAL_OUTSIDER_PATIENCE_FLAG, database.list_flags(session.character.id))

        move(session, "human_grand_cathedral")
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))
        self.assertIn(HUMAN_OPEN_DOOR_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)["current_step"], "find_lower_wards")
        output = "".join(session.outputs).lower()
        self.assertIn("trust cannot be commanded", output)
        self.assertIn("first demon church", output)

    def test_bells_turn_lower_wards_truth_back_into_religious_duty(self):
        temp, database, session = self._session("Bell")
        self.addCleanup(temp.cleanup)
        database.complete_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        database.start_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key, "complete")
        database.complete_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key)
        database.start_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key, "complete")
        database.complete_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)
        reconcile_human_cathedral_faith(session)
        move(session, "human_grand_cathedral")

        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_BELLS_QUEST.key)["current_step"], "light_vigil")
        move(session, HUMAN_CROSSING_CHAPEL_KEY)
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "light vigil")))
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "ring vigil bell")))
        self.assertIn(HUMAN_CATHEDRAL_VIGIL_BELL_FLAG, database.list_flags(session.character.id))
        move(session, "human_grand_cathedral")
        self.assertTrue(asyncio.run(handle_human_cathedral_command(session, "talk high acolyte")))
        self.assertIn(HUMAN_BELLS_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_BELLS_QUEST.key)["status"], "completed")
        self.assertIn("not to prove the world wrong", "".join(session.outputs).lower())

    def test_old_human_progress_is_grandfathered_without_rewinding_training_or_lower_wards(self):
        temp, database, session = self._session("Legacy")
        self.addCleanup(temp.cleanup)
        database.complete_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        database.start_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key, "defeat_vermin")
        database.start_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key, "inspect_mark")

        reconcile_human_cathedral_faith(session)
        flags = database.list_flags(session.character.id)
        self.assertIn(HUMAN_CATHEDRAL_GRANDFATHERED_NAME_FLAG, flags)
        self.assertIn(HUMAN_CATHEDRAL_GRANDFATHERED_DOOR_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, HUMAN_KEPT_NAME_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, HUMAN_OPEN_DOOR_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, quests.HUMAN_COMBAT_TRAINING.key)["current_step"], "defeat_vermin")
        self.assertEqual(database.get_quest(session.character.id, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)["current_step"], "inspect_mark")


if __name__ == "__main__":
    unittest.main()
