from __future__ import annotations

import unittest
from collections import defaultdict

import server  # noqa: F401 - production entrypoint installs all authored content
import mud.quests as quests


class QuestDisplayNameRegressionTests(unittest.TestCase):
    def test_production_quest_display_names_are_unique(self):
        # Audit the union because legacy installers append to QUESTS while some
        # newer registration paths may update QUESTS_BY_KEY directly.
        definitions_by_key = {quest.key: quest for quest in quests.QUESTS}
        definitions_by_key.update(quests.QUESTS_BY_KEY)

        by_name: dict[str, list[str]] = defaultdict(list)
        for quest in definitions_by_key.values():
            by_name[quest.name].append(quest.key)

        duplicates = {
            name: tuple(sorted(keys))
            for name, keys in sorted(by_name.items())
            if len(keys) > 1
        }
        self.assertEqual(duplicates, {}, f"duplicate quest display names: {duplicates}")

    def test_quest_registry_keys_remain_stable_identifiers(self):
        for key, quest in quests.QUESTS_BY_KEY.items():
            self.assertEqual(key, quest.key)


if __name__ == "__main__":
    unittest.main()
