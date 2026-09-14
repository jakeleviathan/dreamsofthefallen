from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ItemNamingQualityTests(unittest.TestCase):
    def test_live_inventory_catalog_has_no_development_placeholder_names(self):
        code = r'''
import server
import mud.crafting as crafting

patterns = (
    "basic starting",
    "starting weapon",
    "training harness",
    "relic material",
    " placeholder",
    "generic ",
    "test item",
    "temporary item",
)

offenders = []
for key, item in sorted(crafting.ITEMS_BY_KEY.items()):
    name = str(item.name).strip()
    lowered = name.lower()
    if any(pattern in lowered for pattern in patterns) or lowered.endswith(" remnant"):
        offenders.append((key, name))

assert not offenders, "Generic/player-facing item names remain: " + repr(offenders)
print("ITEM_NAMES_AUTHORED_OK", len(crafting.ITEMS_BY_KEY))
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
        self.assertIn("ITEM_NAMES_AUTHORED_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
