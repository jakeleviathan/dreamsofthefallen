from __future__ import annotations

import unittest

from mud.combat import EnemyState, SEWER_RAT
from mud.corpse_loot import NPC_LOOT_TABLES, loot_table_for_enemy
from mud.economy_loop import install_economy_content


class CorpseLootDropTableAdapterTests(unittest.TestCase):
    def test_existing_guaranteed_monster_drops_feed_corpse_table(self):
        install_economy_content()
        old = NPC_LOOT_TABLES.pop("sewer_rat", None)
        try:
            table = loot_table_for_enemy(EnemyState(SEWER_RAT))
            by_key = {entry.item_key: entry for entry in table}
            self.assertIn("rough_hide", by_key)
            self.assertEqual(by_key["rough_hide"].chance, 1.0)
        finally:
            if old is not None:
                NPC_LOOT_TABLES["sewer_rat"] = old


if __name__ == "__main__":
    unittest.main()
