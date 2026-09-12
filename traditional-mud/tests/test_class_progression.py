from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.class_progression import (
    BRUTE_ABILITIES,
    CLASS_ROLE_SUMMARIES,
    CLASS_SIGNATURE_GEAR,
    DRUID_ABILITIES,
    NECROMANCER_ABILITIES,
    PRIEST_COMMON_ABILITIES,
    SIGNATURE_ITEMS,
    SIGNATURE_RECIPES,
    WIZARD_ABILITIES,
    _last_announced_level,
    _set_last_announced_level,
)
from mud.database import Database


class ClassProgressionTests(unittest.TestCase):
    def test_all_five_classes_have_a_readable_role_and_midgame_growth(self):
        self.assertEqual(
            set(CLASS_ROLE_SUMMARIES),
            {"brute", "wizard", "druid", "priest", "necromancer"},
        )
        ladders = {
            "brute": BRUTE_ABILITIES,
            "wizard": WIZARD_ABILITIES,
            "druid": DRUID_ABILITIES,
            "priest": PRIEST_COMMON_ABILITIES,
            "necromancer": NECROMANCER_ABILITIES,
        }
        for class_key, abilities in ladders.items():
            with self.subTest(class_key=class_key):
                self.assertTrue(abilities)
                self.assertTrue(all(ability.unlock_level is not None for ability in abilities))
                self.assertTrue(all(ability.unlock_level <= 9 for ability in abilities))
                self.assertTrue(all(ability.description for ability in abilities))

        self.assertEqual(
            {ability.key for ability in BRUTE_ABILITIES},
            {"heavy_strike", "shield_bash", "hold_the_line", "rallying_roar"},
        )
        self.assertTrue({"frostbind", "arcane_surge", "rift_lance"} <= {a.key for a in WIZARD_ABILITIES})
        self.assertTrue({"thorn_lash", "rejuvenation", "barkskin", "verdant_pulse"} <= {a.key for a in DRUID_ABILITIES})
        self.assertTrue({"mend_ally", "prayer_of_renewal", "sanctuary"} <= {a.key for a in PRIEST_COMMON_ABILITIES})
        self.assertTrue({"bone_ward", "grave_command", "wither"} <= {a.key for a in NECROMANCER_ABILITIES})

    def test_signature_gear_is_universal_but_has_one_class_affinity_each(self):
        self.assertEqual(len(SIGNATURE_ITEMS), 5)
        self.assertEqual(len(CLASS_SIGNATURE_GEAR), 5)
        keys = {item.key for item in SIGNATURE_ITEMS}
        self.assertEqual(
            keys,
            {"lineholder_shield", "coldglass_circlet", "briarheart_mantle", "resonant_vestments", "regent_bone_wand"},
        )
        for item in SIGNATURE_ITEMS:
            with self.subTest(item=item.key):
                self.assertIsNotNone(item.equipment)
                self.assertTrue(item.equipment.is_universal)
                self.assertTrue(item.equipment.scripted_effects)

        recipe_outputs = {recipe.output_item_key for recipe in SIGNATURE_RECIPES}
        self.assertEqual(recipe_outputs, keys)
        for class_key, (item_key, recipe_key) in CLASS_SIGNATURE_GEAR.items():
            self.assertIn(item_key, keys)
            self.assertIn(recipe_key, {recipe.key for recipe in SIGNATURE_RECIPES})

    def test_level_notice_state_is_persistent_and_monotonic_by_caller(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "progress.db")
            with database.connect() as db:
                account_id = db.execute(
                    "INSERT INTO accounts (name, password_hash) VALUES ('progress_test', 'x')"
                ).lastrowid
                character_id = db.execute(
                    """
                    INSERT INTO characters (account_id, name, level, experience, race, character_class)
                    VALUES (?, 'Progressor', 1, 0, 'human', 'brute')
                    """,
                    (account_id,),
                ).lastrowid
            self.assertIsNone(_last_announced_level(database, int(character_id)))
            _set_last_announced_level(database, int(character_id), 4)
            self.assertEqual(_last_announced_level(database, int(character_id)), 4)
            reopened = Database(Path(temp_dir) / "progress.db")
            self.assertEqual(_last_announced_level(reopened, int(character_id)), 4)

    def test_production_server_installs_complete_level_one_to_nine_kits_and_recipes(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.crafting as crafting
import mud.mechanics as mechanics
import mud.session as session_module

assert server.PlayerSession._class_progression_runtime_installed
expected = {
    "brute": {"taunt", "heavy_strike", "shield_bash", "hold_the_line", "rallying_roar"},
    "wizard": {"coldfire_burst", "minor_barrier", "arcane_bolt", "frostbind", "arcane_surge", "rift_lance"},
    "druid": {"forage", "minor_heal", "hp_buff", "thorn_lash", "rejuvenation", "barkskin", "verdant_pulse"},
    "necromancer": {"minor_life_tap", "raise_skeleton", "rot", "bone_ward", "grave_command", "wither"},
}
for class_key, keys in expected.items():
    actual = {ability.key for ability in mechanics.FIXED_CLASS_ABILITIES[class_key]}
    assert keys <= actual, (class_key, actual)

for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items():
    keys = {ability.key for ability in abilities}
    assert {"mend_ally", "resurrection", "prayer_of_renewal", "sanctuary"} <= keys, (path_key, keys)
    levels = [ability.unlock_level for ability in abilities if ability.unlock_level is not None]
    assert levels == sorted(levels), (path_key, levels)

# Old starter spells now expose the same costs/cooldowns the executable shell used.
wizard = {ability.key: ability for ability in mechanics.FIXED_CLASS_ABILITIES["wizard"]}
druid = {ability.key: ability for ability in mechanics.FIXED_CLASS_ABILITIES["druid"]}
assert wizard["coldfire_burst"].mana_cost == 5 and wizard["coldfire_burst"].cooldown_seconds == 4.0
assert druid["minor_heal"].mana_cost == 4 and druid["minor_heal"].cooldown_seconds == 5.0

item_keys = {"lineholder_shield", "coldglass_circlet", "briarheart_mantle", "resonant_vestments", "regent_bone_wand"}
recipe_keys = {"forge_lineholder_shield", "forge_coldglass_circlet", "sew_briarheart_mantle", "sew_resonant_vestments", "forge_regent_bone_wand"}
assert item_keys <= set(crafting.ITEMS_BY_KEY)
assert recipe_keys <= set(crafting.RECIPES_BY_KEY)
assert recipe_keys <= {recipe.key for recipe in session_module.ALL_RECIPES}
print("CLASS_PROGRESSION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("CLASS_PROGRESSION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
