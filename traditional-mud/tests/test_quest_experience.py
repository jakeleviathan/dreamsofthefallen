from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.quest_experience import (
    _flush_reward_events,
    install_quest_experience_database_hook,
    quest_experience_reward,
)
from mud.quests import HUMAN_CATHEDRAL_SUMMONS
from mud.stats import CharacterStats


ROOT = Path(__file__).resolve().parents[1]


class _Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.client_state_sends = 0

    async def send(self, text: str) -> None:
        self.outputs.append(text)

    async def send_client_state(self) -> None:
        self.client_state_sends += 1


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

    def _make_character(self, database: Database, name: str):
        account = database.create_account(
            f"{name.lower()}account",
            "not-a-real-password-hash",
        )
        return database.create_character(
            account.id,
            name,
            "human",
            "brute",
            CharacterStats(),
        )

    def test_fallback_reward_is_deferred_until_command_finishes(self):
        install_quest_experience_database_hook(Database)
        with tempfile.TemporaryDirectory() as tempdir:
            database = Database(Path(tempdir) / "quest-xp.db")
            character = self._make_character(database, "Questxp")

            database.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)

            # complete_quest itself must not pay immediately because older
            # authored content may award tuned XP immediately afterward.
            after_complete = database.get_character_by_name(character.name)
            self.assertEqual(after_complete.experience, 0)

            session = _Session(database, after_complete)
            asyncio.run(_flush_reward_events(session))

            refreshed = database.get_character_by_name(character.name)
            expected = quest_experience_reward(HUMAN_CATHEDRAL_SUMMONS)
            self.assertEqual(refreshed.experience, expected)
            self.assertIn(
                f"you gain {expected} experience",
                "".join(session.outputs),
            )

            # Re-completing an already completed quest cannot farm fallback XP.
            database.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            asyncio.run(_flush_reward_events(session))
            again = database.get_character_by_name(character.name)
            self.assertEqual(again.experience, expected)

    def test_authored_reward_suppresses_universal_fallback(self):
        install_quest_experience_database_hook(Database)
        with tempfile.TemporaryDirectory() as tempdir:
            database = Database(Path(tempdir) / "authored-xp.db")
            character = self._make_character(database, "Authoredxp")

            database.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            database.add_experience(character.id, 17)

            session = _Session(
                database,
                database.get_character_by_name(character.name),
            )
            asyncio.run(_flush_reward_events(session))

            refreshed = database.get_character_by_name(character.name)
            self.assertEqual(refreshed.experience, 17)
            self.assertNotIn("Quest reward -", "".join(session.outputs))

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
