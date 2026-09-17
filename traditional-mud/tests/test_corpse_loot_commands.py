from __future__ import annotations

import unittest

from mud.corpse_loot import _parse_from_command, _parse_quantity_item


class CorpseLootCommandParsingTests(unittest.TestCase):
    def test_from_parser_keeps_item_and_corpse_targets_separate(self):
        self.assertEqual(
            _parse_from_command("2 bone chips from sewer rat"),
            ("2 bone chips", "sewer rat"),
        )
        self.assertEqual(_parse_from_command("all from corpse"), ("all", "corpse"))

    def test_quantity_parser_defaults_to_one(self):
        self.assertEqual(_parse_quantity_item("bone chips"), (1, "bone chips"))
        self.assertEqual(_parse_quantity_item("3 bone chips"), (3, "bone chips"))


if __name__ == "__main__":
    unittest.main()
