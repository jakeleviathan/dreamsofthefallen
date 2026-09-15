from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.quest_experience import (
    install_quest_experience_database_hook,
    quest_experience_reward,
)
from mud.quests import HUMAN_CATHEDRAL_SUMMONS
from mud.stats import CharacterStats


ROOT = Path(__file__).resolve().parents[1]


class QuestExperienceTests(unittest.TestCase):
    def test_structured_quests_reward_more_than_discovery_at_same_level(self):
        structured = SimpleNamespace(style="structured", minimum_level=20)
        discovery = SimpleNamespace(style="discovery", minimum_level=20)
        self.assertGreater(
            quest_experience_reward(structured),
            quest_experience_reward(discovery),
        )
        self.assertGreater(quest_experience_reward(structured), 0)
        self.assertGreater(quest_experience_reward(discovery), 0)

    def test_reward_uses_authored_level_not_turn_in_level(self):
        quest = SimpleNamespace(style="structured", minimum_level=11)
        self.assertEqual(quest_experience_reward(quest), 269)

    def test_real_quest_completion_awards_xp_once(self):
        install_quest_experience_database_hook(Database)
        with tempfile.TemporaryDirectory() as tempdir:
            database = Database(Path(tempdir) / "quest-xp.db")
            account = database.create_account("QuestXpTester", "not-a-real-password-hash")
            character = database.create_character(
                account.id,
                "Questxp",
                "human",
                "brute",
                CharacterStats(),
            )

            self.assertEqual(character.experience, 0)
            self.assertEqual(
                database.get_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)["status"],
                "active",
            )

            database.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            after_first = database.get_character_by_name(character.name)
            self.assertIsNotNone(after_first)
            expected = quest_experience_reward(HUMAN_CATHEDRAL_SUMMONS)
            self.assertEqual(after_first.experience, expected)

            # Re-completing an already completed quest cannot farm the reward.
            database.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            after_second = database.get_character_by_name(character.name)
            self.assertEqual(after_second.experience, expected)

            events = database._quest_experience_events[character.id]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["experience"], expected)

    def test_production_server_installs_quest_xp_outer_runtime(self):
        code = r'''
import server
from mud.database import Database
assert Database._quest_experience_hook_installed
assert server.PlayerSession._quest_experience_runtime_installed
assert server.PlayerSession._movement_runtime_installed
print("QUEST_XP_RUNTIME_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("QUEST_XP_RUNTIME_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
