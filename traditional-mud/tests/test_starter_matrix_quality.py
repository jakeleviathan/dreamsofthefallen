from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.starter_class_moments import RACE_OPENING_TRIGGERS, all_starter_class_moments
from mud.starter_matrix_quality import starter_matrix_summary
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


class StarterMatrixQualityTests(unittest.TestCase):
    def test_launch_matrix_is_complete_eight_by_five(self):
        summary = starter_matrix_summary()
        self.assertEqual(summary["races"], 8)
        self.assertEqual(summary["classes"], 5)
        self.assertEqual(summary["combinations"], 40)
        self.assertEqual(summary["race_openings"], 8)
        self.assertEqual(summary["class_moments"], 40)
        self.assertEqual(summary["opening_triggers"], 8)

        expected_pairs = {(race, cls) for race in RACES_BY_KEY for cls in CLASSES_BY_KEY}
        actual_pairs = {(moment.race_key, moment.class_key) for moment in all_starter_class_moments()}
        self.assertEqual(actual_pairs, expected_pairs)
        self.assertEqual(set(STARTER_RACE_LOOPS_BY_RACE), set(RACES_BY_KEY))

    def test_every_integrated_class_trigger_has_complete_authored_metadata(self):
        # Several starter quests are registered by their content modules during
        # production assembly, so the real quest-existence check belongs to the
        # production import below. Here we protect the authored trigger contract.
        self.assertEqual(set(RACE_OPENING_TRIGGERS), set(RACES_BY_KEY))
        for race_key, trigger in RACE_OPENING_TRIGGERS.items():
            with self.subTest(race=race_key):
                self.assertTrue(trigger.quest_key)
                self.assertTrue(trigger.trigger_step)
                self.assertTrue(trigger.lead_in)
                self.assertTrue(trigger.closing)

    def test_production_entrypoint_really_installs_class_specific_opening_runtime(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.starter_matrix_quality import starter_matrix_summary
assert server.PlayerSession._starter_class_moment_runtime_installed
summary = starter_matrix_summary()
assert summary["combinations"] == 40
assert summary["race_openings"] == 8
assert summary["class_moments"] == 40
print("STARTER_MATRIX_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("STARTER_MATRIX_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
