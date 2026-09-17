from __future__ import annotations

import unittest


class CorpseLootQuestBoundaryTests(unittest.TestCase):
    def test_corpse_runtime_only_redirects_monster_economy_award_hooks(self):
        from mud import corpse_loot

        source_names = {
            corpse_loot._award_corpse_loot.__name__,
            corpse_loot._suppress_legacy_secondary_award.__name__,
        }
        self.assertEqual(
            source_names,
            {"_award_corpse_loot", "_suppress_legacy_secondary_award"},
        )


if __name__ == "__main__":
    unittest.main()
