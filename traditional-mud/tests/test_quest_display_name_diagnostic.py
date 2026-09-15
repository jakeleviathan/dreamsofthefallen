from __future__ import annotations

import unittest
from collections import defaultdict

import server  # noqa: F401 - production entrypoint installs all authored content
import mud.quests as quests


class QuestDisplayNameDiagnosticTests(unittest.TestCase):
    def test_report_duplicate_production_quest_names(self):
        by_name: dict[str, list[str]] = defaultdict(list)
        for quest in quests.QUESTS:
            by_name[quest.name].append(quest.key)
        duplicates = {
            name: keys for name, keys in by_name.items() if len(keys) > 1
        }
        self.assertFalse(duplicates, f"duplicate quest display names: {duplicates}")


if __name__ == "__main__":
    unittest.main()
