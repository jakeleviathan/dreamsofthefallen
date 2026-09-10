from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.dwarf_first_shift import (
    BRUNI_SPARKHEEL_KEY,
    DWARF_BELLOWSWORKS_FLOOR_KEY,
    DWARF_FIRST_SHIFT,
    DWARF_FIRST_SHIFT_COMPLETE_FLAG,
    DWARF_FIRST_SHIFT_COWORKER_CHECKED_FLAG,
    DWARF_FIRST_SHIFT_FAULT_IDENTIFIED_FLAG,
    DWARF_FIRST_SHIFT_REPORTED_FLAG,
    DWARF_FIRST_SHIFT_SHUTOFF_FLAG,
    DWARF_HEARD_CLOCKGLASS_FLAG,
    DWARF_HEARD_DEEPFORGE_FLAG,
    DWARF_TRADE_INTEREST,
    DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG,
    DWARF_TRADE_INTEREST_DEEPFORGE_FLAG,
    KETTA_RIVETBRAID_KEY,
    ORSA_DEEPFORGE_KEY,
    PELLIN_CLOCKGLASS_KEY,
    _file_incident_with_helga,
    _handle_shift_actions,
    _talk_ketta,
    _talk_orsa,
    _talk_pellin,
    dwarf_first_shift_augmentations,
    install_dwarf_first_shift_content,
    reconcile_dwarf_first_shift,
)
from mud.dwarf_start import (
    DWARF_FIRST_WORK_ORDER,
    DWARF_REGISTRY_HALL_KEY,
    DWARF_TRADE_ARCADE_KEY,
    DWARF_WORKSHOP_TIER_KEY,
    install_dwarf_content,
)
from mud.stats import CharacterStats


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


class DwarfFirstShiftTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_dwarf_content()
        install_dwarf_first_shift_content()

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

    def _session(self, name: str = "Rivet"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "dwarf_shift.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(
            account.id,
            name,
            "dwarf",
            "brute",
            stats=CharacterStats(),
        )
        return temp, database, FakeSession(database, character)

    @staticmethod
    def _complete_clearance(database: Database, character_id: int) -> None:
        database.start_quest(character_id, DWARF_FIRST_WORK_ORDER.key, "complete")
        database.complete_quest(character_id, DWARF_FIRST_WORK_ORDER.key)

    def test_content_adds_real_shift_floor_and_two_nonexclusive_house_contacts(self):
        workshop = legacy_world.ROOMS_BY_KEY[DWARF_WORKSHOP_TIER_KEY]
        floor = legacy_world.ROOMS_BY_KEY[DWARF_BELLOWSWORKS_FLOOR_KEY]
        arcade = legacy_world.ROOMS_BY_KEY[DWARF_TRADE_ARCADE_KEY]

        self.assertEqual(workshop.exits["east"], DWARF_BELLOWSWORKS_FLOOR_KEY)
        self.assertEqual(floor.exits["west"], DWARF_WORKSHOP_TIER_KEY)
        self.assertIn(KETTA_RIVETBRAID_KEY, floor.npc_keys)
        self.assertIn(BRUNI_SPARKHEEL_KEY, floor.npc_keys)
        self.assertIn(ORSA_DEEPFORGE_KEY, arcade.npc_keys)
        self.assertIn(PELLIN_CLOCKGLASS_KEY, arcade.npc_keys)
        augmentation = dwarf_first_shift_augmentations()[DWARF_BELLOWSWORKS_FLOOR_KEY]
        self.assertGreaterEqual(len(augmentation.features), 3)
        self.assertTrue(any(layer.condition.required_flags for layer in augmentation.description_layers))

    def test_completed_training_clearance_flows_into_first_real_shift(self):
        temp, database, session = self._session("Clearance")
        self.addCleanup(temp.cleanup)
        self._complete_clearance(database, session.character.id)

        started_shift, started_interest = reconcile_dwarf_first_shift(session)
        self.assertTrue(started_shift)
        self.assertFalse(started_interest)
        first = database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)
        self.assertEqual(first["status"], "active")
        self.assertEqual(first["current_step"], "report_shift")
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key)["status"], "completed")

    def test_routine_check_becomes_crisis_and_correct_response_prioritizes_people_then_fault(self):
        temp, database, session = self._session("Crisis")
        self.addCleanup(temp.cleanup)
        self._complete_clearance(database, session.character.id)
        reconcile_dwarf_first_shift(session)
        move(session, DWARF_BELLOWSWORKS_FLOOR_KEY)

        self.assertTrue(asyncio.run(_talk_ketta(session)))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "check_manifold")
        self.assertTrue(asyncio.run(_handle_shift_actions(session, "check manifold")))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "emergency_shutoff")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "turn intake valve")))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "emergency_shutoff")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "pull emergency shutoff")))
        self.assertIn(DWARF_FIRST_SHIFT_SHUTOFF_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "check_coworker")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "check bruni")))
        self.assertIn(DWARF_FIRST_SHIFT_COWORKER_CHECKED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "identify_fault")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "examine sheared pin")))
        self.assertIn(DWARF_FIRST_SHIFT_FAULT_IDENTIFIED_FLAG, database.list_flags(session.character.id))
        output = "".join(session.outputs).lower()
        self.assertIn("no sabotage", output)
        self.assertIn("failed early", output)

    def test_incident_is_reported_and_filed_instead_of_quietly_repaired(self):
        temp, database, session = self._session("Report")
        self.addCleanup(temp.cleanup)
        self._complete_clearance(database, session.character.id)
        reconcile_dwarf_first_shift(session)
        move(session, DWARF_BELLOWSWORKS_FLOOR_KEY)
        asyncio.run(_talk_ketta(session))
        asyncio.run(_handle_shift_actions(session, "check manifold"))
        asyncio.run(_handle_shift_actions(session, "pull emergency shutoff"))
        asyncio.run(_handle_shift_actions(session, "check bruni"))
        asyncio.run(_handle_shift_actions(session, "examine sheared pin"))

        self.assertTrue(asyncio.run(_talk_ketta(session)))
        self.assertIn(DWARF_FIRST_SHIFT_REPORTED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["current_step"], "file_incident")

        move(session, DWARF_REGISTRY_HALL_KEY)
        self.assertTrue(asyncio.run(_file_incident_with_helga(session)))
        self.assertIn(DWARF_FIRST_SHIFT_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, DWARF_FIRST_SHIFT.key)["status"], "completed")
        interest = database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)
        self.assertEqual(interest["current_step"], "hear_houses")
        output = "".join(session.outputs).lower()
        self.assertIn("we do not quietly replace the pin", output)
        self.assertIn("undocumented failed pin", output)

    def test_player_must_hear_both_houses_before_nonbinding_interest_choice(self):
        temp, database, session = self._session("Choice")
        self.addCleanup(temp.cleanup)
        self._complete_clearance(database, session.character.id)
        database.start_quest(session.character.id, DWARF_FIRST_SHIFT.key, "complete")
        database.complete_quest(session.character.id, DWARF_FIRST_SHIFT.key)
        reconcile_dwarf_first_shift(session)
        move(session, DWARF_TRADE_ARCADE_KEY)

        self.assertTrue(asyncio.run(_talk_orsa(session)))
        self.assertIn(DWARF_HEARD_DEEPFORGE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)["current_step"], "hear_houses")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "interest deepforge")))
        self.assertEqual(database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)["status"], "active")

        self.assertTrue(asyncio.run(_talk_pellin(session)))
        flags = database.list_flags(session.character.id)
        self.assertIn(DWARF_HEARD_CLOCKGLASS_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)["current_step"], "record_interest")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "interest clockglass")))
        flags = database.list_flags(session.character.id)
        self.assertIn(DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG, flags)
        self.assertNotIn(DWARF_TRADE_INTEREST_DEEPFORGE_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)["status"], "completed")
        output = "".join(session.outputs).lower()
        self.assertIn("not contract", output)
        self.assertIn("not joined clockglass", output)
        self.assertIn("chosen a permanent profession", output)

    def test_alternate_house_interest_is_equally_valid_and_does_not_change_class(self):
        temp, database, session = self._session("Deep")
        self.addCleanup(temp.cleanup)
        self._complete_clearance(database, session.character.id)
        database.start_quest(session.character.id, DWARF_FIRST_SHIFT.key, "complete")
        database.complete_quest(session.character.id, DWARF_FIRST_SHIFT.key)
        reconcile_dwarf_first_shift(session)
        database.grant_flag(session.character.id, DWARF_HEARD_DEEPFORGE_FLAG)
        database.grant_flag(session.character.id, DWARF_HEARD_CLOCKGLASS_FLAG)
        database.advance_quest(session.character.id, DWARF_TRADE_INTEREST.key, "record_interest")

        self.assertTrue(asyncio.run(_handle_shift_actions(session, "interest deepforge")))
        flags = database.list_flags(session.character.id)
        self.assertIn(DWARF_TRADE_INTEREST_DEEPFORGE_FLAG, flags)
        refreshed = database.get_character_by_name(session.character.name)
        self.assertEqual(refreshed.character_class, "brute")
        self.assertEqual(database.get_quest(session.character.id, DWARF_TRADE_INTEREST.key)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
