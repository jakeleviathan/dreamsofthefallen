import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.forest_elf_home_and_omens import (
    FOREST_ELF_HUSHED_VERGE_KEY,
    FOREST_ELF_LENS_WIZARD_FLAG,
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    FOREST_ELF_VERGE_STUDIED_FLAG,
    ONE_TURN_FARTHER,
)
from mud.forest_elf_homecoming import (
    FOREST_ELF_CLOSING_SEEN_FLAG,
    FOREST_ELF_HOMECOMING_FLAG,
    FOREST_ELF_HOMECOMING_STEP,
    append_opening_closing_if_needed,
    return_home_by_wayroot,
    study_signs_with_homecoming,
)
from mud.world import FOREST_ELF_START_ROOM_KEY


class FakeSession:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.outputs = []
        self.room_views = 0

    async def send(self, text):
        self.outputs.append(text)

    async def show_current_room(self):
        self.room_views += 1

    def text(self):
        return "".join(self.outputs).lower()


class ForestElfHomecomingTests(unittest.TestCase):
    def _session(self, name="Waywalker", character_class="wizard"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "mud.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(account.id, name, "forest_elf", character_class)
        session = FakeSession(database, character)
        return temp, database, session

    def _move(self, session, room_key):
        session.database.set_character_room(session.character.id, room_key)
        refreshed = session.database.get_character_by_name(session.character.name)
        self.assertIsNotNone(refreshed)
        session.character = refreshed

    def test_study_signs_leads_to_prepared_wayroot_instead_of_walk_home(self):
        temp, database, session = self._session()
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "study_signs")
        self._move(session, FOREST_ELF_HUSHED_VERGE_KEY)

        self.assertTrue(asyncio.run(study_signs_with_homecoming(session)))
        quest = database.get_quest(session.character.id, ONE_TURN_FARTHER.key)
        self.assertEqual(quest["current_step"], FOREST_ELF_HOMECOMING_STEP)
        flags = database.list_flags(session.character.id)
        self.assertIn(FOREST_ELF_LENS_WIZARD_FLAG, flags)
        self.assertIn(FOREST_ELF_VERGE_STUDIED_FLAG, flags)
        self.assertIn("return home", session.text())
        self.assertIn("prepared road", session.text())

    def test_return_home_wayroot_moves_player_to_circle_and_keeps_report_pending(self):
        temp, database, session = self._session("Rootstep")
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, ONE_TURN_FARTHER.key, FOREST_ELF_HOMECOMING_STEP)
        self._move(session, FOREST_ELF_HUSHED_VERGE_KEY)

        self.assertTrue(asyncio.run(return_home_by_wayroot(session)))
        self.assertEqual(session.character.current_room, FOREST_ELF_START_ROOM_KEY)
        self.assertEqual(
            database.get_quest(session.character.id, ONE_TURN_FARTHER.key)["current_step"],
            "report_circle",
        )
        self.assertIn(FOREST_ELF_HOMECOMING_FLAG, database.list_flags(session.character.id))
        self.assertIn("home did not stop while you were gone", session.text())
        self.assertIn("report signs", session.text())
        self.assertEqual(session.room_views, 1)

    def test_existing_report_step_stranded_at_verge_can_also_take_wayroot(self):
        temp, database, session = self._session("LegacyReturn")
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "report_circle")
        self._move(session, FOREST_ELF_HUSHED_VERGE_KEY)

        self.assertTrue(asyncio.run(return_home_by_wayroot(session)))
        self.assertEqual(session.character.current_room, FOREST_ELF_START_ROOM_KEY)
        self.assertEqual(
            database.get_quest(session.character.id, ONE_TURN_FARTHER.key)["current_step"],
            "report_circle",
        )

    def test_quiet_completion_beat_is_persistent_and_only_sent_once(self):
        temp, database, session = self._session("LastLeaf")
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, ONE_TURN_FARTHER.key, "report_circle")
        database.complete_quest(session.character.id, ONE_TURN_FARTHER.key)

        self.assertTrue(asyncio.run(append_opening_closing_if_needed(session, was_active=True)))
        flags = database.list_flags(session.character.id)
        self.assertIn(FOREST_ELF_CLOSING_SEEN_FLAG, flags)
        self.assertIn(FOREST_ELF_OPENING_COMPLETE_FLAG, flags)
        self.assertIn("the rest of astralis is yours to walk", session.text())
        self.assertIn("forest elf opening complete", session.text())

        before = len(session.outputs)
        self.assertFalse(asyncio.run(append_opening_closing_if_needed(session, was_active=True)))
        self.assertEqual(len(session.outputs), before)


if __name__ == "__main__":
    unittest.main()
