from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContentLootProductionCoverageTests(unittest.TestCase):
    def test_real_production_world_gives_every_killable_enemy_a_table(self):
        code = r'''
import server
import mud.combat as combat
import mud.crafting as crafting
import mud.npcs as mobile_npcs
from mud.corpse_loot import NPC_LOOT_TABLES

killable = {
    key
    for key in combat.ENEMIES_BY_KEY
    if key != "training_dummy"
}
for definition in mobile_npcs.MOBILE_NPC_DEFINITIONS:
    if definition.aggressive or definition.xp_reward > 0:
        killable.add(definition.key)

missing = sorted(key for key in killable if not NPC_LOOT_TABLES.get(key))
assert not missing, missing

unknown_items = []
invalid_entries = []
for enemy_key in sorted(killable):
    for entry in NPC_LOOT_TABLES[enemy_key]:
        if entry.item_key not in crafting.ITEMS_BY_KEY:
            unknown_items.append((enemy_key, entry.item_key))
        if not 0.0 <= entry.chance <= 1.0 or entry.min_quantity <= 0 or entry.max_quantity < entry.min_quantity:
            invalid_entries.append((enemy_key, entry))

assert not unknown_items, unknown_items
assert not invalid_entries, invalid_entries
assert server._CONTENT_LOOT_COVERAGE.killable_definitions == len(killable), (
    server._CONTENT_LOOT_COVERAGE,
    len(killable),
)
assert not server._CONTENT_LOOT_COVERAGE.missing_tables
print(f"CONTENT_LOOT_COVERAGE_OK:{len(killable)}")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("CONTENT_LOOT_COVERAGE_OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
