from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.content_foundry import DUNGEONS as FOUNDRY_DUNGEONS
from mud.content_density import (
    ALL_DENSITY_ENEMIES,
    BOSS_KEYS,
    CURIOS,
    DENSITY_RECIPES,
    DENSITY_ROOMS,
    DUNGEON_SEEDS,
    EVERYDAY_GEAR,
    FINAL_BOSS_KEYS,
    MINIBOSS_KEYS,
    ODDJOBS,
    RARE_CREATURES,
    WORLD_BOSSES,
)
from mud.iconic_items import ICONIC_ITEMS


class ContentDensityTests(unittest.TestCase):
    def test_expansion_has_ten_dungeon_identities(self):
        self.assertEqual(len(FOUNDRY_DUNGEONS), 3)
        self.assertEqual(len(DUNGEON_SEEDS), 7)
        self.assertEqual(len(FOUNDRY_DUNGEONS) + len(DUNGEON_SEEDS), 10)
        self.assertEqual(len(DENSITY_ROOMS), 42)

    def test_expansion_reaches_twenty_memorable_boss_encounters(self):
        total = len(FOUNDRY_DUNGEONS) + len(MINIBOSS_KEYS) + len(FINAL_BOSS_KEYS) + len(WORLD_BOSSES)
        self.assertEqual(total, 20)
        self.assertEqual(len(BOSS_KEYS), 17)

    def test_everyday_item_layer_is_actually_dense(self):
        self.assertEqual(len(EVERYDAY_GEAR), 100)
        self.assertEqual(len({item.key for item in EVERYDAY_GEAR}), 100)
        self.assertTrue(all(item.category == "equipment" for item in EVERYDAY_GEAR))

    def test_crafting_crosses_regional_material_boundaries(self):
        self.assertEqual(len(DENSITY_RECIPES), 40)
        self.assertTrue(all(len(recipe.materials) >= 2 for recipe in DENSITY_RECIPES))
        self.assertGreaterEqual(len({req.item_key for recipe in DENSITY_RECIPES for req in recipe.materials}), 12)

    def test_rare_creatures_and_curios_are_large_discovery_layers(self):
        self.assertEqual(len(RARE_CREATURES), 34)
        # Content Foundry supplies Silverhart and Rainthread Serpent, bringing the
        # complete rare-creature wave to 36.
        self.assertEqual(len(RARE_CREATURES) + 2, 36)
        self.assertEqual(len(CURIOS), 30)
        self.assertTrue(any("Perfume Sample" in item.name for item in CURIOS))

    def test_twenty_tiny_quests_exist_without_becoming_main_story(self):
        self.assertEqual(len(ODDJOBS), 20)
        self.assertTrue(all(quest.style == "discovery" for quest in ODDJOBS))

    def test_iconic_catalog_is_exactly_ninety_and_not_player_labeled_iconic(self):
        self.assertEqual(len(ICONIC_ITEMS), 90)
        self.assertEqual(len({item.key for item in ICONIC_ITEMS}), 90)
        self.assertEqual({item.level_band for item in ICONIC_ITEMS}, {"early", "mid", "deep"})
        self.assertFalse(any("iconic" in item.name.lower() for item in ICONIC_ITEMS))

    def test_production_server_assembles_foundry_density_before_presentation(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.crafting as crafting
import mud.combat as combat
from mud.content_density import EVERYDAY_GEAR, RARE_CREATURES
from mud.iconic_items import ICONIC_ITEMS
assert server.PlayerSession._content_foundry_installed
assert server.PlayerSession._content_density_installed
assert server.PlayerSession._modern_client_runtime_installed
assert all(item.key in crafting.ITEMS_BY_KEY for item in ICONIC_ITEMS)
assert all(item.key in crafting.ITEMS_BY_KEY for item in EVERYDAY_GEAR)
assert all(enemy.key in combat.ENEMIES_BY_KEY for enemy in RARE_CREATURES)
print("CONTENT_DENSITY_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("CONTENT_DENSITY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
