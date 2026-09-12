from __future__ import annotations

import unittest

import mud.crafting as crafting
from mud.iconic_items import ICONIC_ITEMS, install_iconic_items


class IconicItemTests(unittest.TestCase):
    def test_catalog_has_exactly_ninety_unique_world_anchors(self):
        self.assertEqual(len(ICONIC_ITEMS), 90)
        self.assertEqual(len({item.key for item in ICONIC_ITEMS}), 90)
        self.assertEqual(sum(item.level_band == "early" for item in ICONIC_ITEMS), 30)
        self.assertEqual(sum(item.level_band == "mid" for item in ICONIC_ITEMS), 30)
        self.assertEqual(sum(item.level_band == "deep" for item in ICONIC_ITEMS), 30)

    def test_catalog_is_not_just_ninety_stat_sticks(self):
        self.assertGreaterEqual(sum(item.slot is None for item in ICONIC_ITEMS), 20)
        self.assertGreaterEqual(len({item.source for item in ICONIC_ITEMS}), 60)
        self.assertTrue(any(item.name == "The Empty Scabbard" for item in ICONIC_ITEMS))
        self.assertTrue(any(item.name == "A Word That Wasn't Spoken" for item in ICONIC_ITEMS))

    def test_registration_is_idempotent(self):
        install_iconic_items()
        install_iconic_items()
        self.assertTrue(all(item.key in crafting.ITEMS_BY_KEY for item in ICONIC_ITEMS))
        keys = [item.key for item in crafting.ITEMS]
        for item in ICONIC_ITEMS:
            self.assertEqual(keys.count(item.key), 1)


if __name__ == "__main__":
    unittest.main()
