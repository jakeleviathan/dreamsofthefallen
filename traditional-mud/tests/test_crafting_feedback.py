from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CraftingFeedbackTests(unittest.TestCase):
    def test_missing_materials_use_authored_item_names(self):
        code = r"""
import tempfile
from pathlib import Path

import server
import mud.crafting as crafting
from mud.database import Database
from mud.stats import CharacterStats

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "craft-material-names.db")
    account = db.create_account("materialnames", "x")
    character = db.create_character(
        account.id,
        "MaterialNames",
        "goblin",
        "priest",
        CharacterStats(might=4, grace=7, love=12, mind=6, hp=5),
        deity_key="zerjz",
    )

    recipe = crafting.RECIPES_BY_KEY["refine_greenward_catalyst"]
    db.add_item(character.id, "greenleaf", 2)

    result = crafting.craft_recipe(
        db,
        character.id,
        recipe.key,
        station_key=recipe.station_key,
    )

    assert not result.success
    assert result.message == "Missing materials: 1x Spring Water.", result.message
    assert "spring_water" not in result.message

print("CRAFTING_MATERIAL_NAMES_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CRAFTING_MATERIAL_NAMES_OK", result.stdout)

    def test_greenward_catalyst_distinguishes_practice_from_actual_skillup(self):
        code = r"""
import tempfile
from pathlib import Path

import server
import mud.crafting as crafting
from mud.database import Database
from mud.stats import CharacterStats

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "craft-feedback.db")
    account = db.create_account("craftfeedback", "x")
    character = db.create_character(
        account.id,
        "Feedback",
        "goblin",
        "priest",
        CharacterStats(might=4, grace=7, love=12, mind=6, hp=5),
        deity_key="zerjz",
    )

    recipe = crafting.RECIPES_BY_KEY["refine_greenward_catalyst"]
    # Greenward Catalyst is the deliberately trivial skill-0 starter component:
    # it teaches the crafting flow and feeds later recipes, but it is already
    # mastered at Alchemy 0 and therefore cannot itself grant a skill point.
    assert recipe.trivial_skill == 0
    db.add_item(character.id, "greenleaf", 2)
    db.add_item(character.id, "spring_water", 1)

    result = crafting.craft_recipe(
        db,
        character.id,
        recipe.key,
        station_key=recipe.station_key,
        success_roll=0.0,
        skillup_roll=0.0,
    )

    assert result.success
    assert result.completed
    assert not result.skill_increased
    assert result.new_skill_value == 0
    assert "No Alchemy skill increase" in result.message, result.message
    assert "current skill is 0" in result.message, result.message
    assert "trivial for you" in result.message, result.message
    assert "can no longer raise the skill" in result.message, result.message
    assert "improves through use" not in result.message.lower(), result.message

print("CRAFTING_FEEDBACK_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CRAFTING_FEEDBACK_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
