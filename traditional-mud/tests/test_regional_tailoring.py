"""Isolated production integration tests for all nine regional tailoring cultures.

Server assembly mutates global registries; run it in a child process to avoid
contaminating the smaller standalone crafting and room tests.
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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_workshops as workshops
import mud.regional_tailoring as tailor
import mud.regional_tailoring_runtime as runtime
from mud.database import Database
from mud.world import ROOMS_BY_KEY, NPCS_BY_KEY


class RegionalTailoringTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Database(Path(tmp.name) / "tailoring.db")
        account = self.db.create_account("tailor", "x")
        self.character = self.db.create_character(account.id, "TailorTester", "goblin", "priest")
        self.messages = []
        async def send(message):
            self.messages.append(message)
        self.session = SimpleNamespace(
            character=self.character, database=self.db, send=send,
            can_receive_item=lambda key, qty: True,
        )

    def move(self, room):
        self.db.set_character_room(self.character.id, room)
        self.session.character = replace(self.session.character, current_room=room)

    def test_catalog_and_region_world_are_real(self):
        counts = tailor.catalog_counts()
        self.assertEqual(counts, {
            "traditions": 9, "regional_patterns": 378,
            "regional_dyes_and_linings": 18, "hidden_patterns": 9,
            "pattern_folios": 54,
        })
        self.assertEqual(len(set(item.key for item in tailor.ITEMS)), len(tailor.ITEMS))
        self.assertEqual(len(set(recipe.key for recipe in tailor.RECIPES)), len(tailor.RECIPES))
        for item in tailor.ITEMS:
            self.assertIn(item.key, crafting.ITEMS_BY_KEY)
        for recipe in tailor.RECIPES:
            self.assertIn(recipe.key, crafting.RECIPES_BY_KEY)
            self.assertTrue(all(req.item_key in crafting.ITEMS_BY_KEY
                                for req in recipe.materials), recipe.key)
        for tradition in tailor.TRADITIONS:
            self.assertIn(tradition.hall, ROOMS_BY_KEY)
            self.assertIn(tradition.gathering_room, ROOMS_BY_KEY)
            self.assertIn(f"regional_tailor_{tradition.key}", NPCS_BY_KEY)
            self.assertIn(f"regional_tailor_{tradition.key}",
                          ROOMS_BY_KEY[tradition.hall].npc_keys)
            self.assertIn("loom", economy.ROOM_STATIONS[tradition.hall])
            node = f"tailor_pigment_node_{tradition.key}"
            self.assertIn(node, economy.ROOM_RESOURCE_NODE_KEYS[tradition.gathering_room])
            features = server.WORLD.augmentations[tradition.hall].features
            self.assertTrue(any(f.key == f"tailor_clue_{tradition.key}" for f in features))
        for room, node in (
            ("troll_frostroot_camp", "wool_flock"),
            ("forest_elf_outer_grove", "silk_cocoon_cluster"),
            ("moon_elf_wind_terrace", "moonflax_bed"),
            ("greywake_riftfield", "giant_spider_nest"),
            ("gravewatch_chapel_nave", "ghostmoss_patch"),
            ("salt_kingdoms_springcut_gorge", "astral_bloom"),
        ):
            self.assertIn(node, economy.ROOM_RESOURCE_NODE_KEYS[room])
        self.assertEqual(tailor.install_regional_tailoring_content(server.WORLD), counts)

    def test_common_dye_lining_and_region_patterns_share_crafting(self):
        tradition = tailor.BY_KEY["goblin"]
        self.move(tradition.hall)
        dye = tailor.RECIPES_BY_KEY["tailor_mix_dye_goblin"]
        lining = tailor.RECIPES_BY_KEY["tailor_cut_lining_goblin"]
        self.assertEqual(dye.station_key, lining.station_key)
        self.assertEqual(dye.station_key, "loom")
        recipe = tailor.RECIPES_BY_KEY["tailor_pattern_goblin_cotton_gloves"]
        self.assertFalse(economy._recipe_visible(self.session, recipe))
        forbidden = crafting.craft_recipe(
            self.db, self.character.id, recipe.key, station_key="loom",
            success_roll=0, skillup_roll=1)
        self.assertFalse(forbidden.success)
        self.assertIn("not learned", forbidden.message.lower())

        asyncio.run(runtime._train(self.session))
        self.assertTrue(economy._recipe_visible(self.session, recipe))
        self.assertIn(tailor.lesson_flag("goblin", 0),
                      self.db.list_flags(self.character.id))
        for requirement in recipe.materials:
            self.db.add_item(self.character.id, requirement.item_key, requirement.quantity)
        made = crafting.craft_recipe(
            self.db, self.character.id, recipe.key,
            station_key="loom", success_roll=0, skillup_roll=1)
        self.assertTrue(made.success, made.message)
        self.assertEqual(self.db.item_quantity(self.character.id, recipe.output_item_key), 1)
        self.assertIsNotNone(crafting.ITEMS_BY_KEY[recipe.output_item_key].equipment)

    def test_normal_recipe_book_and_workshop_show_learning_and_commissions(self):
        self.move(tailor.BY_KEY["waymeet"].hall)
        asyncio.run(runtime._train(self.session))
        self.messages.clear()
        asyncio.run(economy._show_recipes(self.session, "tailoring"))
        output = "".join(self.messages)
        self.assertIn("TAILORING RECIPES", output)
        self.assertIn("ALL ATTEMPTABLE", output)
        self.assertIn("Seven Roads Cotton", output)
        self.assertIn("REGIONAL TAILORING", output)
        self.assertIn("DAILY COMMISSION", output)
        self.messages.clear()
        asyncio.run(workshops._show_workshop(self.session, "tailoring"))
        output = "".join(self.messages)
        self.assertIn("Seven Roads Cotton", output)
        self.assertIn("REGIONAL TAILORING", output)

    def test_folios_are_tradeable_and_not_auto_learned(self):
        self.move(tailor.BY_KEY["forest"].hall)
        self.db.add_sols(self.character.id, 80)
        self.assertTrue(asyncio.run(runtime._buy_folio(self.session, "Wool Pattern Folio")))
        key = tailor.folio_key("forest", 1)
        self.assertEqual(self.db.item_quantity(self.character.id, key), 1)
        learned_flag = tailor.lesson_flag("forest", 1)
        self.assertNotIn(learned_flag, self.db.list_flags(self.character.id))
        self.assertTrue(asyncio.run(runtime._read_folio(self.session, "Wool Pattern Folio")))
        self.assertNotIn(learned_flag, self.db.list_flags(self.character.id),
                         "reading under the required skill must not bypass the gate")
        self.db.get_trade_skill_progress = lambda *_: {"skill_xp": 200, "use_count": 200}
        self.assertTrue(asyncio.run(runtime._read_folio(self.session, "Wool Pattern Folio")))
        self.assertIn(learned_flag, self.db.list_flags(self.character.id))
        self.assertEqual(self.db.item_quantity(self.character.id, key), 1,
                         "folios remain transferable after study")
        recipe = tailor.RECIPES_BY_KEY["tailor_pattern_forest_wool_vest"]
        self.assertTrue(economy._recipe_visible(self.session, recipe))

    def test_hidden_pattern_requires_actual_discovery_and_enters_wiki(self):
        tradition = tailor.BY_KEY["spore"]
        self.move(tradition.hall)
        secret = tailor.RECIPES_BY_KEY["tailor_hidden_spore"]
        self.assertFalse(economy._recipe_visible(self.session, secret))
        self.assertFalse(asyncio.run(runtime._study_secret(self.session, "random thread")))
        self.assertTrue(asyncio.run(runtime._study_secret(self.session, tradition.clue)))
        self.assertTrue(economy._recipe_visible(self.session, secret))
        self.assertIn("Secret pattern discovered", "".join(self.messages))
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT entry_key FROM collective_wiki_entries "
                "WHERE category = 'recipe' AND entry_key = ?",
                (secret.key,)).fetchone()
        self.assertIsNotNone(row)

    def test_daily_commission_is_persistent_atomic_and_capped(self):
        tradition = tailor.BY_KEY["goblin"]
        self.move(tradition.hall)
        asyncio.run(runtime._train(self.session))
        offer = runtime._commission_offer(self.session, tradition)
        self.assertIsNotNone(offer)
        self.assertEqual(offer, runtime._commission_offer(self.session, tradition))
        output = offer["output_item_key"]
        recipe = next(r for r in tailor.RECIPES if r.output_item_key == output)
        for req in recipe.materials:
            self.db.add_item(self.character.id, req.item_key, req.quantity)
        result = crafting.craft_recipe(
            self.db, self.character.id, recipe.key,
            station_key="loom", success_roll=0, skillup_roll=1)
        self.assertTrue(result.success, result.message)
        before = self.db.get_character_by_name(self.character.name)
        before_sols = self.db.get_sols(self.character.id)
        asyncio.run(runtime._turn_in(self.session))
        after = self.db.get_character_by_name(self.character.name)
        after_sols = self.db.get_sols(self.character.id)
        self.assertEqual(after_sols, before_sols + offer["reward_sparks"])
        self.assertEqual(after.experience, before.experience + offer["reward_xp"])
        self.assertEqual(self.db.item_quantity(self.character.id, output), 0)
        self.assertIsNotNone(runtime._commission_offer(self.session, tradition)["completed_at"])
        self.db.add_item(self.character.id, output)
        asyncio.run(runtime._turn_in(self.session))
        repeated = self.db.get_character_by_name(self.character.name)
        self.assertEqual(self.db.get_sols(self.character.id), after_sols)
        self.assertEqual(repeated.experience, after.experience)
        self.assertEqual(self.db.item_quantity(self.character.id, output), 1,
                         "second delivery must not consume gear or print Sols")


if __name__ == "__main__":
    unittest.main()
'''


class RegionalTailoringIsolatedTests(unittest.TestCase):
    def test_production_tailoring_contract(self):
        result = subprocess.run(
            [sys.executable, "-c", PRODUCTION_TESTS],
            cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        self.assertIn("Ran 6 tests", result.stderr)


if __name__ == "__main__":
    unittest.main()
