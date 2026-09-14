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
import mud.stats as stats

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
    if item.equipment is not None:
        assert item.equipment.name == item.name, (key, item.name, item.equipment.name)

assert not offenders, "Generic/player-facing item names remain: " + repr(offenders)

expected = {
    "starter_weapon": "Wayfarer's Iron",
    "brute_training_harness": "Lineholder's Harness",
    "density_small_saint_minor_material": "Unshriven Bell Clapper",
    "density_small_saint_major_material": "Saintless Emberglass",
    "density_salt_king_minor_material": "Steward's Brinehook",
    "density_salt_king_major_material": "Salt-King's Brineheart",
    "density_red_door_minor_material": "Velvet Lockplate",
    "density_red_door_major_material": "Custodian's Red Key",
    "density_broken_observatory_minor_material": "Blind Astrolabe Cog",
    "density_broken_observatory_major_material": "Fallen-Moon Lensglass",
    "density_rootcourt_minor_material": "Hollow Antler Splint",
    "density_rootcourt_major_material": "Rootcourt Heartwood",
    "density_brass_lung_minor_material": "Bellows Valve-Tongue",
    "density_brass_lung_major_material": "Furnace-Breath Clinker",
    "density_white_room_minor_material": "Guestless Chair Splinter",
    "density_white_room_major_material": "Curator's White Porcelain",
}
for key, name in expected.items():
    assert key in crafting.ITEMS_BY_KEY, key
    assert crafting.ITEMS_BY_KEY[key].name == name, (key, crafting.ITEMS_BY_KEY[key].name)

# The save-facing keys stay exactly the same; old inventories require no migration.
assert crafting.ITEMS_BY_KEY["starter_weapon"].key == "starter_weapon"
assert crafting.ITEMS_BY_KEY["brute_training_harness"].key == "brute_training_harness"
assert stats.STARTER_WEAPON.name == "Wayfarer's Iron"
assert stats.BRUTE_STARTER_ARMOR.name == "Lineholder's Harness"
assert stats.STARTER_ARMOR_BY_CLASS["brute"].name == "Lineholder's Harness"

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
