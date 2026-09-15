from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class QuestDisplayNameRegressionTests(unittest.TestCase):
    def test_production_quest_display_names_are_unique_and_keys_stable(self):
        code = r'''
from collections import defaultdict

import server  # noqa: F401 - assembles the real production registry
import mud.quests as quests

definitions_by_key = {quest.key: quest for quest in quests.QUESTS}
definitions_by_key.update(quests.QUESTS_BY_KEY)

by_name = defaultdict(list)
for quest in definitions_by_key.values():
    by_name[quest.name].append(quest.key)

duplicates = {
    name: tuple(sorted(keys))
    for name, keys in sorted(by_name.items())
    if len(keys) > 1
}
assert duplicates == {}, f"duplicate quest display names: {duplicates}"
for key, quest in quests.QUESTS_BY_KEY.items():
    assert key == quest.key, (key, quest.key)

print("QUEST_DISPLAY_NAMES_UNIQUE", len(definitions_by_key))
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
        self.assertIn("QUEST_DISPLAY_NAMES_UNIQUE", result.stdout)


if __name__ == "__main__":
    unittest.main()
