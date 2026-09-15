from __future__ import annotations

import unittest
from collections import defaultdict


class QuestDisplayNameAuditTests(unittest.TestCase):
    def test_production_quest_display_names_are_unique(self) -> None:
        # Import the real production entrypoint so every dynamically installed
        # authored quest is present in the canonical quest registry.
        import server  # noqa: F401
        import mud.quests as quests

        by_name: dict[str, list[str]] = defaultdict(list)
        for quest in quests.QUESTS:
            by_name[quest.name].append(quest.key)

        duplicates = {
            name: tuple(keys)
            for name, keys in sorted(by_name.items())
            if len(keys) > 1
        }
        self.assertEqual(duplicates, {}, f"Duplicate quest display names: {duplicates}")


if __name__ == "__main__":
    unittest.main()
