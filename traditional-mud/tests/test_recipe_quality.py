from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductionRecipeQualityTests(unittest.TestCase):
    def test_production_catalog_has_semantic_materials_and_no_missing_inputs(self):
        code = r"""
import server
import mud.crafting as crafting

# Foundry corrections.
ash = crafting.RECIPES_BY_KEY["forge_ashwheel_boots"]
assert ash.trade_skill_key == "tailoring"
assert ash.station_key == "loom"
assert {req.item_key for req in ash.materials} == {"ashwheel_spoke", "rough_hide", "cotton_thread"}

afterimage = crafting.RECIPES_BY_KEY["blend_afterimage_no9"]
assert {req.item_key for req in afterimage.materials} == {
    "ninth_vapor_resin",
    "lavender_essential_oil",
    "grain_alcohol",
    "perfumer_silver_salt",
}
assert "glassfruit_shard" not in {req.item_key for req in afterimage.materials}

# Legacy semantic-audit corrections.
briar = crafting.RECIPES_BY_KEY.get("sew_briarheart_mantle")
if briar is not None:
    keys = {req.item_key for req in briar.materials}
    assert keys == {"cotton_cloth", "rough_hide", "tough_sinew"}
    assert "greenleaf" not in keys

bastion = crafting.RECIPES_BY_KEY.get("forge_bastion_lineholder_shield")
if bastion is not None:
    keys = {req.item_key for req in bastion.materials}
    assert "underclock_governor_bearing" not in keys
    assert "blackreed_iron_fitting" in keys

clockglass = crafting.RECIPES_BY_KEY.get("forge_clockglass_circlet")
if clockglass is not None:
    keys = {req.item_key for req in clockglass.materials}
    assert "underclock_governor_bearing" not in keys
    assert "density_broken_observatory_minor_material" in keys

bellwarden = crafting.RECIPES_BY_KEY.get("sew_bellwarden_vestments")
if bellwarden is not None:
    keys = {req.item_key for req in bellwarden.materials}
    assert "gravewatch_old_garrison_iron" not in keys
    assert "silk_thread" in keys

# Every recipe in the fully assembled production catalog must consume items that
# actually exist and produce an item that actually exists.
missing_materials = sorted({
    req.item_key
    for recipe in crafting.ALL_RECIPES
    for req in recipe.materials
    if req.item_key not in crafting.ITEMS_BY_KEY
})
missing_outputs = sorted({
    recipe.output_item_key
    for recipe in crafting.ALL_RECIPES
    if recipe.output_item_key not in crafting.ITEMS_BY_KEY
})
assert not missing_materials, missing_materials
assert not missing_outputs, missing_outputs
print("RECIPE_QUALITY_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RECIPE_QUALITY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
