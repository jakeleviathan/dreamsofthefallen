from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.sols import (
    _merchant_wares_lines,
    format_sols,
    humanoid_sol_drop,
    merchant_buyback_price,
    quest_sol_reward,
    split_sols,
)


class SolEconomyTests(unittest.TestCase):
    def test_denominations_are_decimal_and_sun_themed(self):
        self.assertEqual(split_sols(234).flames, 2)
        self.assertEqual(split_sols(234).embers, 3)
        self.assertEqual(split_sols(234).sparks, 4)
        self.assertEqual(format_sols(234), "2 flames, 3 embers, 4 sparks")
        self.assertEqual(format_sols(100), "1 flame")
        self.assertEqual(format_sols(10), "1 ember")
        self.assertEqual(format_sols(1), "1 spark")

    def test_database_persists_and_atomically_spends_sols(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "sols.sqlite3")
            db.initialize()
            account = db.create_account("soltest", "password123")
            character = db.create_character(account.id, "Sunbuyer", "human", "brute")
            self.assertEqual(db.get_sols(character.id), 0)
            self.assertEqual(db.add_sols(character.id, 35), 35)
            self.assertTrue(db.spend_sols(character.id, 30))
            self.assertFalse(db.spend_sols(character.id, 6))
            self.assertEqual(db.get_sols(character.id), 5)

    def test_merchant_purchase_and_sale_are_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "trade.sqlite3")
            db.initialize()
            account = db.create_account("merchanttest", "password123")
            character = db.create_character(account.id, "Coinhand", "human", "brute")
            db.add_sols(character.id, 20)
            self.assertTrue(
                db.complete_merchant_purchase(
                    character.id,
                    item_key="bone_chips",
                    quantity=2,
                    total_price=6,
                )
            )
            self.assertEqual(db.get_sols(character.id), 14)
            self.assertEqual(db.item_quantity(character.id, "bone_chips"), 2)
            self.assertTrue(
                db.complete_merchant_sale(
                    character.id,
                    item_key="bone_chips",
                    quantity=1,
                    proceeds=1,
                )
            )
            self.assertEqual(db.get_sols(character.id), 15)
            self.assertEqual(db.item_quantity(character.id, "bone_chips"), 1)

    def test_buyback_is_35_percent_with_minimum_one_spark(self):
        self.assertGreaterEqual(merchant_buyback_price("bone_chips"), 1)

    def test_quest_reward_fallback_uses_embers_and_long_story_flame(self):
        short = SimpleNamespace(minimum_level=1, style="structured", objective_steps=(("a", "A"),), sol_reward=None)
        long = SimpleNamespace(minimum_level=10, style="structured", objective_steps=tuple((str(i), str(i)) for i in range(8)), sol_reward=None)
        self.assertGreaterEqual(quest_sol_reward(short), 10)
        self.assertGreaterEqual(quest_sol_reward(long), 100)

    def test_only_humanoid_enemies_drop_sols(self):
        humanoid = SimpleNamespace(key="road_bandit", name="Road Bandit", description="a human bandit", xp_reward=60)
        beast = SimpleNamespace(key="marsh_wolf", name="Marsh Wolf", description="a wild wolf", xp_reward=60)
        self.assertGreater(humanoid_sol_drop(humanoid), 0)
        self.assertEqual(humanoid_sol_drop(beast), 0)

    def test_browse_can_filter_to_one_merchant_with_full_shop_format(self):
        from mud.merchants import WAYMEET_SEVRA_MERCHANT, WAYMEET_VEKK_MERCHANT

        merchants = (
            ("Vekk Coil", WAYMEET_VEKK_MERCHANT),
            ("Sevra Lent", WAYMEET_SEVRA_MERCHANT),
        )
        lines = _merchant_wares_lines(merchants, balance=22, target="vekk")
        text = "\n".join(lines)

        self.assertIn("--- Vekk Coil ---", text)
        self.assertIn("Iron Ore — 4 sparks", text)
        self.assertIn("Raw Cotton — 4 sparks", text)
        self.assertIn("Greenleaf — 4 sparks", text)
        self.assertIn("Coal — 4 sparks", text)
        self.assertNotIn("Iron Ingot", text)
        self.assertIn("Your Sols: 2 embers, 2 sparks", text)
        self.assertIn("BUY [qty] <item> | SELL [qty] <item> | VALUE <item>", text)

    def test_browse_merchant_matching_accepts_first_name_and_full_name(self):
        from mud.merchants import WAYMEET_SEVRA_MERCHANT, WAYMEET_VEKK_MERCHANT

        merchants = (
            ("Vekk Coil", WAYMEET_VEKK_MERCHANT),
            ("Sevra Lent", WAYMEET_SEVRA_MERCHANT),
        )
        short = "\n".join(_merchant_wares_lines(merchants, balance=0, target="vekk"))
        full = "\n".join(_merchant_wares_lines(merchants, balance=0, target="Vekk Coil"))
        sevra = "\n".join(_merchant_wares_lines(merchants, balance=0, target="sevra"))

        self.assertIn("--- Vekk Coil ---", short)
        self.assertIn("--- Vekk Coil ---", full)
        self.assertIn("--- Sevra Lent ---", sevra)

    def test_authored_starter_markets_are_real_merchants(self):
        from mud.merchants import MERCHANTS_BY_NPC_KEY

        brassgut = MERCHANTS_BY_NPC_KEY["goblin_ruskle_coil"]
        self.assertTrue(brassgut.sells("iron_ore"))
        self.assertTrue(brassgut.sells("raw_cotton"))
        chisel = MERCHANTS_BY_NPC_KEY["undead_bonewright_kell"]
        self.assertTrue(chisel.sells("bone_chips"))
        self.assertTrue(chisel.sells("iron_ore"))

    def test_every_starter_culture_has_regional_shopping(self):
        from mud.merchants import MERCHANTS_BY_NPC_KEY
        expected = {
            "goblin_ruskle_coil", "undead_bonewright_kell",
            "forest_elf_greenway_herbalist", "moon_elf_lantern_trader",
            "dwarf_toolwright_bram", "troll_provisioner_yrsa", "sporekin_tender_murr",
        }
        self.assertTrue(expected.issubset(MERCHANTS_BY_NPC_KEY))
        for key in expected:
            self.assertGreaterEqual(len(MERCHANTS_BY_NPC_KEY[key].stock), 3)

    def test_regional_prices_include_longer_term_targets(self):
        from mud.merchants import MERCHANTS_BY_NPC_KEY
        dwarf = MERCHANTS_BY_NPC_KEY["dwarf_toolwright_bram"]
        prices = {row.item_key: row.price_units for row in dwarf.stock}
        self.assertEqual(prices["cobalt_ingot"], 50)
        moon = MERCHANTS_BY_NPC_KEY["moon_elf_lantern_trader"]
        self.assertEqual({row.item_key: row.price_units for row in moon.stock}["moonsilver_ore"], 20)

    def test_character_ui_exposes_sols_and_item_merchant_value(self):
        from mud import equipment_system, inventory_inspection
        import inspect
        equipment_source = inspect.getsource(equipment_system)
        inspection_source = inspect.getsource(inventory_inspection)
        self.assertIn("Sols :", equipment_source)
        self.assertIn("Sols:", equipment_source)
        self.assertIn("Merchant value:", equipment_source)
        self.assertIn("Merchant value:", inspection_source)
        self.assertIn("merchant_buyback_price", inspection_source)


if __name__ == "__main__":
    unittest.main()
