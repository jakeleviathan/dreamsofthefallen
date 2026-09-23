"""Production integration checks for the 300-recipe regional alchemy layer."""
from __future__ import annotations

import asyncio
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_alchemy as regional
import mud.regional_alchemy_runtime as runtime
from mud.database import Database
from mud.sols import item_list_price, merchant_buyback_price
from mud.world import NPCS_BY_KEY, ROOMS_BY_KEY


class RegionalAlchemyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "alch.db")
        account = self.db.create_account("alchemist", "test-hash")
        self.character = self.db.create_character(
            account.id, "AlchTester", "goblin", "priest"
        )
        self.text: list[str] = []
        async def send(value):
            self.text.append(value)
        self.session = SimpleNamespace(
            database=self.db, character=self.character, send=send,
            can_receive_item=lambda _key, _qty: True,
        )

    def move(self, room):
        self.db.set_character_room(self.character.id, room)
        self.session.character = replace(self.character, current_room=room)

    def test_catalog_counts_unique_and_integrated(self):
        counts = regional.catalog_counts()
        self.assertEqual(counts["total"], 300)
        self.assertEqual(counts["secret"], 27)
        self.assertEqual(counts["legendary"], 3)
        self.assertEqual(
            {t.key: 5 * len(t.patterns) + 3 for t in regional.TRADITIONS},
            {t.key: counts[t.key] for t in regional.TRADITIONS},
        )
        self.assertEqual(len(regional.SECRET_CLUES), 30)
        self.assertEqual(len(set(r.key for r in regional.RECIPES)), 300)
        self.assertTrue(all(r.key in crafting.RECIPES_BY_KEY for r in regional.RECIPES))
        self.assertTrue(all(
            item.key in crafting.ITEMS_BY_KEY for item in regional.ITEMS
        ))
        self.assertTrue(all(
            all(req.item_key in crafting.ITEMS_BY_KEY for req in recipe.materials)
            for recipe in regional.RECIPES
        ))

    def test_trainers_are_real_and_regions_produce_local_inputs(self):
        for t in regional.TRADITIONS:
            self.assertIn(t.hall, ROOMS_BY_KEY)
            self.assertIn(t.gathering_room, ROOMS_BY_KEY)
            self.assertIn(f"regional_alchemist_{t.key}", NPCS_BY_KEY)
            self.assertIn(
                f"regional_alchemist_{t.key}", ROOMS_BY_KEY[t.hall].npc_keys
            )
            self.assertIn("alchemy_table", economy.ROOM_STATIONS[t.hall])
            for suffix in ("common", "rare"):
                node = f"alch_node_{t.key}_{suffix}"
                self.assertIn(node, economy.ROOM_RESOURCE_NODE_KEYS[t.gathering_room])
                self.assertIn(node, crafting.RESOURCE_NODES_BY_KEY)

    def test_learning_books_are_durable_and_traded_like_items(self):
        t = regional.BY_KEY["goblin"]
        self.move(t.hall)
        locked = regional.RECIPES_BY_KEY["regional_goblin_0_0"]
        self.assertFalse(economy._recipe_visible(self.session, locked))
        asyncio.run(runtime._study(self.session))
        self.assertTrue(economy._recipe_visible(self.session, locked))
        self.assertIn(regional.lesson_flag(t.key, 0), self.db.list_flags(self.character.id))
        higher = regional.RECIPES_BY_KEY["regional_goblin_1_0"]
        self.assertFalse(economy._recipe_visible(self.session, higher))
        self.db.add_sols(self.character.id, 50)
        asyncio.run(runtime._buy_book(self.session, "Field"))
        book = regional.book_key(t.key, 1)
        self.assertEqual(self.db.item_quantity(self.character.id, book), 1)
        asyncio.run(runtime._read_book(self.session, "Field Goblin"))
        self.assertTrue(economy._recipe_visible(self.session, higher))
        self.assertEqual(self.db.item_quantity(self.character.id, book), 1)

    def test_secret_not_listed_until_actual_discovery(self):
        t = regional.BY_KEY["forest"]
        self.move(t.hall)
        recipe = regional.RECIPES_BY_KEY["regional_secret_forest_0"]
        self.assertFalse(economy._recipe_visible(self.session, recipe))
        asyncio.run(runtime._secret(self.session, t.clue[0]))
        self.assertTrue(economy._recipe_visible(self.session, recipe))
        self.assertIn("Secret formula discovered", "".join(self.text))

    def test_server_cannot_bypass_learned_flags_via_direct_craft(self):
        key = "regional_goblin_0_0"
        denied = crafting.craft_recipe(
            self.db, self.character.id, key, station_key="mortar_and_pestle"
        )
        self.assertFalse(denied.success)
        self.assertIn("not learned", denied.message.lower())
        self.db.grant_flag(self.character.id, regional.lesson_flag("goblin", 0))
        self.db.add_item(self.character.id, regional.sample_key("goblin"), 2)
        self.db.add_item(self.character.id, "spring_water", 1)
        self.db.add_item(self.character.id, "greenleaf", 1)
        completed = crafting.craft_recipe(
            self.db, self.character.id, key,
            station_key="mortar_and_pestle", success_roll=0, skillup_roll=1
        )
        self.assertTrue(completed.success, completed.message)
        self.assertEqual(
            self.db.item_quantity(self.character.id,
                                  regional.output_key("goblin", 0, 0)), 1
        )

    def test_permanent_gold_requires_purchased_fixative_and_cannot_print_sols(self):
        recipe = regional.RECIPES_BY_KEY["regional_dwarf_4_4"]
        self.assertEqual(recipe.output_item_key, "alch_gold_ingot")
        required = {req.item_key: req.quantity for req in recipe.materials}
        self.assertEqual(required["alch_lead_ingot"], 1)
        self.assertEqual(required["alch_auric_fixative"], 1)
        self.assertEqual(required["stariron_ingot"], 1)
        self.assertGreater(
            regional.GOLD_FIXATIVE_PRICE,
            merchant_buyback_price("alch_gold_ingot")
        )
        self.assertEqual(item_list_price("alch_gold_ingot"), 100)
        self.assertEqual(merchant_buyback_price("alch_gold_ingot"), 35)
        self.assertEqual(merchant_buyback_price("alch_auric_fixative"), 0)

        self.move(regional.BY_KEY["dwarf"].hall)
        self.db.add_sols(self.character.id, 300)
        self.db.get_trade_skill_progress = lambda _cid, _skill: {
            "skill_xp": 200, "use_count": 200,
        }
        asyncio.run(runtime._buy_fixative(self.session))
        self.assertEqual(
            self.db.item_quantity(self.character.id, "alch_auric_fixative"), 1
        )
        self.db.grant_flag(self.character.id, regional.lesson_flag("dwarf", 4))
        for material, amount in required.items():
            missing = amount - self.db.item_quantity(self.character.id, material)
            if missing > 0:
                self.db.add_item(self.character.id, material, missing)
        made = crafting.craft_recipe(
            self.db, self.character.id, recipe.key,
            station_key="alchemy_table", success_roll=0, skillup_roll=1
        )
        self.assertTrue(made.success, made.message)
        self.assertEqual(
            self.db.item_quantity(self.character.id, "alch_gold_ingot"), 1
        )
        self.assertEqual(
            self.db.item_quantity(self.character.id, "alch_auric_fixative"), 0
        )

    def test_hidden_experiment_consumes_material_and_unlocks_only_on_success(self):
        t = regional.BY_KEY["waymeet"]
        self.move(t.hall)
        self.db.get_trade_skill_progress = lambda _cid, _skill: {
            "skill_xp": 90, "use_count": 90,
        }
        for key in (
            regional.sample_key(t.key),
            regional.sample_key(t.key, True), "spring_water"
        ):
            self.db.add_item(self.character.id, key, 2)
        flag = regional.secret_flag(t.key, 0)
        asyncio.run(runtime._experiment(self.session, roll=0.95))
        self.assertNotIn(flag, self.db.list_flags(self.character.id))
        asyncio.run(runtime._experiment(self.session, roll=0.05))
        self.assertIn(flag, self.db.list_flags(self.character.id))
        self.assertEqual(
            self.db.item_quantity(self.character.id,
                                  regional.sample_key(t.key)), 0
        )


if __name__ == "__main__":
    unittest.main()
