from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.gravewatch_keep import (
    GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
    GRAVEWATCH_CASTELLAN_DEFEATED_FLAG,
    GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
    GRAVEWATCH_COMPLETE_FLAG,
    GRAVEWATCH_GATE_OPEN_FLAG,
    GRAVEWATCH_HOUND_PULL_FLAG,
    GRAVEWATCH_RIVER_MILE_KEY,
)
from mud.gravewatch_repeatable import GRAVEWATCH_REPEAT_RUN_FLAGS, reset_gravewatch_patrol
from mud.mechanics import PROGRESSION_RULES
from mud.veyra_city import VEYRA_RESIDENT_FLAG


class GravewatchRepeatableTests(unittest.TestCase):
    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "gravewatch_repeat.db")
        account = database.create_account("repeatkeep", "hash")
        character = database.create_character(account.id, "SecondTorch", "dwarf", "brute")
        database.add_experience(character.id, PROGRESSION_RULES.cumulative_xp_for_level(8))
        database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
        database.grant_flag(character.id, GRAVEWATCH_COMPLETE_FLAG)
        database.set_character_room(character.id, GRAVEWATCH_RIVER_MILE_KEY)
        for flag in GRAVEWATCH_REPEAT_RUN_FLAGS:
            database.grant_flag(character.id, flag)
        character = database.get_character_by_name("SecondTorch")
        assert character is not None
        return tempdir, database, SimpleNamespace(database=database, character=character)

    def test_new_patrol_clears_only_repeat_run_state(self):
        tempdir, database, session = self._session()
        try:
            ok, message = reset_gravewatch_patrol(session)
            self.assertTrue(ok)
            flags = set(database.list_flags(session.character.id))
            self.assertIn(GRAVEWATCH_COMPLETE_FLAG, flags)
            for flag in GRAVEWATCH_REPEAT_RUN_FLAGS:
                self.assertNotIn(flag, flags)
            self.assertIn("first-clear rewards and completion remain recorded", message)
        finally:
            tempdir.cleanup()

    def test_repeat_reset_reopens_all_three_major_fights(self):
        tempdir, database, session = self._session()
        try:
            ok, _ = reset_gravewatch_patrol(session)
            self.assertTrue(ok)
            flags = set(database.list_flags(session.character.id))
            for flag in {
                GRAVEWATCH_HOUND_PULL_FLAG,
                GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
                GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
                GRAVEWATCH_GATE_OPEN_FLAG,
                GRAVEWATCH_CASTELLAN_DEFEATED_FLAG,
            }:
                self.assertNotIn(flag, flags)
        finally:
            tempdir.cleanup()

    def test_production_server_installs_repeatable_patrol_layer(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "assert getattr(server.PlayerSession, '_gravewatch_repeatable_runtime_installed', False); "
            "print('GRAVEWATCH_REPEAT_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GRAVEWATCH_REPEAT_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
