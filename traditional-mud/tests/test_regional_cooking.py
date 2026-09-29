"""Isolated production integration tests for the regional Cooking system.

The production server assembles mutable global registries, so the full Cooking
contract runs in a child process rather than contaminating neighboring tests.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_TESTS = r'''
from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_cooking as cooking
import mud.regional_cooking_runtime as runtime
from mud.database import Database
from mud.stats import CharacterStats
from mud.world import NPCS_BY_KEY, ROOMS_BY_KEY


class RegionalCookingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Database(Path(tmp.name) / "cooking.db")
        account = self.db.create_account("cooktest", "x")
        self.character = self.db.create_character(
            account.id, "PanTester", "human", "druid"
        )
        self.messages = []

        async def send(text):
            self.messages.append(text)

        self.session = SimpleNamespace(
            database=self.db,
            character=self.character,
            send=send,
            active_enemy=None,
            current_weather=lambda: "clear",
            can_receive_item=lambda key, qty: True,
        )

    def move(self, room):
        self.db.set_character_room(self.character.id, room)
        self.character = self.db.get_character_by_name(self.character.name)
        self.session.character = self.character

    def test_catalog_has_blacksmithing_scale_depth(self):
        self.assertEqual(cooking.catalog_counts(), {
            "traditions": 9,
            "regional_dishes": 288,
            "hidden_dishes": 9,
            "regional_ingredients": 9,
            "techniques": 9,
        })
        self.assertEqual(
            len({item.key for item in cooking.ITEMS}), len(cooking.ITEMS)
        )
        self.assertEqual(
            len({recipe.key for recipe in cooking.RECIPES}), len(cooking.RECIPES)
        )
        for recipe in cooking.RECIPES:
            self.assertIn(recipe.key, crafting.RECIPES_BY_KEY)
            self.assertTrue(
                all(req.item_key in crafting.ITEMS_BY_KEY for req in recipe.materials),
                recipe.key,
            )

        metal_inputs = {
            key
            for tier in crafting.METAL_TIERS
            for key in (tier.raw_material_key, tier.ingot_key)
            if key is not None
        }
        for recipe in cooking.RECIPES:
            if recipe.design_status == "regional_cooking_pattern":
                self.assertFalse(
                    any(req.item_key in metal_inputs for req in recipe.materials),
                    recipe.key,
                )

    def test_every_cuisine_is_physically_present(self):
        for tradition in cooking.TRADITIONS:
            self.assertIn(tradition.hall, ROOMS_BY_KEY)
            self.assertIn(tradition.gathering_room, ROOMS_BY_KEY)
            self.assertIn(f"regional_cook_{tradition.key}", NPCS_BY_KEY)
            self.assertIn("cookfire", economy.ROOM_STATIONS[tradition.hall])
            self.assertIn(
                cooking.ingredient_node_key(tradition.key),
                economy.ROOM_RESOURCE_NODE_KEYS[tradition.gathering_room],
            )

    def test_master_training_reveals_regional_recipes(self):
        tradition = cooking.BY_KEY["waymeet"]
        self.move(tradition.hall)
        self.db.get_trade_skill_progress = lambda *_: {
            "skill_xp": 55,
            "uses": 55,
        }
        recipe = cooking.RECIPES_BY_KEY[
            "regional_cook_waymeet_greenward_bite"
        ]
        self.assertFalse(economy._recipe_visible(self.session, recipe))
        asyncio.run(runtime._train(self.session))
        self.assertTrue(economy._recipe_visible(self.session, recipe))
        self.assertIn(
            cooking.lesson_flag("waymeet", 3),
            self.db.list_flags(self.character.id),
        )

    def test_world_condition_experiment_unlocks_secret(self):
        tradition = cooking.BY_KEY["forest"]
        self.move(tradition.hall)
        self.db.add_item(self.character.id, tradition.ingredient_key, 1)
        self.session.current_weather = lambda: tradition.experiment_weather[0]
        old_clock = runtime.ASTRALIS_CLOCK
        runtime.ASTRALIS_CLOCK = SimpleNamespace(
            now=lambda: SimpleNamespace(season=tradition.experiment_season)
        )
        try:
            asyncio.run(
                runtime._experiment(self.session, tradition.ingredient_name)
            )
        finally:
            runtime.ASTRALIS_CLOCK = old_clock
        self.assertIn(
            cooking.secret_flag("forest"),
            self.db.list_flags(self.character.id),
        )
        self.assertEqual(
            self.db.item_quantity(
                self.character.id, tradition.ingredient_key
            ),
            0,
        )

    def test_food_nourishment_replaces_instead_of_stacking(self):
        tradition = cooking.BY_KEY["forest"]
        self.move(tradition.hall)
        first_key = cooking.dish_key("forest", "greenward", "bowl")
        second_key = cooking.dish_key("forest", "bitterroad", "bowl")
        self.db.add_item(self.character.id, first_key, 1)
        self.db.add_item(self.character.id, second_key, 1)

        class Combatant:
            current_hp = 20
            max_hp = 30
            current_mana = 10
            max_mana = 20
            stats = CharacterStats()

        self.session.combatant = Combatant()
        self.session.send_client_state = lambda: asyncio.sleep(0)

        asyncio.run(
            __import__("mud.profession_workshops", fromlist=["_eat"])._eat(
                self.session, crafting.item_display_name(first_key)
            )
        )
        asyncio.run(
            __import__("mud.profession_workshops", fromlist=["_eat"])._eat(
                self.session, crafting.item_display_name(second_key)
            )
        )
        expected = crafting.ITEMS_BY_KEY[
            second_key
        ].consumable.temporary_stat_bonuses
        self.assertEqual(self.session.combatant.stats, expected)

    def test_communal_table_serves_multiple_portions(self):
        tradition = cooking.BY_KEY["goblin"]
        self.move(tradition.hall)
        item_key = cooking.dish_key(
            "goblin", "greenward", "supper"
        )
        self.db.add_item(self.character.id, item_key, 1)
        asyncio.run(
            runtime._serve(
                self.session, crafting.item_display_name(item_key)
            )
        )
        rows = runtime._table_rows(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["portions"]), 4)

        class Combatant:
            current_hp = 5
            max_hp = 30
            current_mana = 10
            max_mana = 20
            stats = CharacterStats()

        self.session.combatant = Combatant()
        self.session.send_client_state = lambda: asyncio.sleep(0)
        asyncio.run(
            runtime._eat_table(
                self.session, crafting.item_display_name(item_key)
            )
        )
        rows = runtime._table_rows(self.session)
        self.assertEqual(int(rows[0]["portions"]), 3)
        self.assertGreater(self.session.combatant.current_hp, 5)


if __name__ == "__main__":
    unittest.main()
'''


class RegionalCookingIsolatedTests(unittest.TestCase):
    def test_production_regional_cooking_contract(self):
        result = subprocess.run(
            [sys.executable, "-c", PRODUCTION_TESTS],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout + "\n" + result.stderr,
        )
        self.assertIn("Ran 6 tests", result.stderr)


if __name__ == "__main__":
    unittest.main()
