from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.session import _quest_journal_group


class QuestJournalDashboardTests(unittest.TestCase):
    def test_completed_quest_groups_match_major_story_areas(self):
        self.assertEqual(_quest_journal_group("goblin_from_scrap_to_claim"), "Goblin Homeland")
        self.assertEqual(_quest_journal_group("waymeet_roads_meet_here"), "Waymeet & Outer Roads")
        self.assertEqual(_quest_journal_group("adventure_under_old_toll"), "Waymeet & Outer Roads")
        self.assertEqual(_quest_journal_group("broken_reach_no_smiling_matter"), "Broken Reach")
        self.assertEqual(_quest_journal_group("unknown_side_story"), "Other Adventures")

    def test_list_quests_exposes_started_and_completed_timestamps(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Database(Path(temporary) / "journal.db")
            with database.connect() as db:
                account_cursor = db.execute(
                    "INSERT INTO accounts (name, password_hash) VALUES (?, ?)",
                    ("journal_test", "hash"),
                )
                account_id = int(account_cursor.lastrowid)
                character_cursor = db.execute(
                    "INSERT INTO characters (account_id, name) VALUES (?, ?)",
                    (account_id, "JournalTester"),
                )
                character_id = int(character_cursor.lastrowid)
                db.execute(
                    """
                    INSERT INTO character_quests
                        (character_id, quest_key, status, current_step, started_at)
                    VALUES (?, ?, 'active', 'first_step', '2026-10-01 12:00:00')
                    """,
                    (character_id, "journal_test_quest"),
                )

            database.complete_quest(character_id, "journal_test_quest")
            rows = database.list_quests(character_id)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["started_at"], "2026-10-01 12:00:00")
            self.assertIsNotNone(rows[0]["completed_at"])
            self.assertEqual(rows[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
