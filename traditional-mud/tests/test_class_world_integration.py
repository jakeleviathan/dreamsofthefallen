from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.quests as quests
from mud.class_progression import CLASS_SIGNATURE_GEAR
from mud.class_world_integration import (
    ADVANCED_AFFINITY_EQUIVALENTS,
    ADVANCED_GEAR_BY_CLASS,
    ADVANCED_SIGNATURE_ITEMS,
    ADVANCED_SIGNATURE_RECIPES,
    ALL_FIELD_DUNGEON_ROOMS,
    BRUTE_COMMISSION,
    CLASS_COMMISSIONS,
    CLASS_COMMISSIONS_BY_CLASS,
    COMMISSION_PLATES,
    DRUID_COMMISSION,
    NECROMANCER_COMMISSION,
    PRIEST_COMMISSION,
    WIZARD_COMMISSION,
    AbilityUseContext,
    install_class_world_content,
    next_commission_step,
)


class ClassWorldIntegrationTests(unittest.TestCase):
    def test_every_class_has_one_level_eight_field_commission(self):
        self.assertEqual(
            set(CLASS_COMMISSIONS_BY_CLASS),
            {"brute", "wizard", "druid", "priest", "necromancer"},
        )
        self.assertEqual(len(CLASS_COMMISSIONS), 5)
        self.assertEqual(len({commission.quest.key for commission in CLASS_COMMISSIONS}), 5)
        self.assertEqual(len({commission.plate_item_key for commission in CLASS_COMMISSIONS}), 5)
        for commission in CLASS_COMMISSIONS:
            with self.subTest(class_key=commission.class_key):
                self.assertEqual(commission.quest.minimum_level, 8)
                self.assertTrue(commission.field_rooms)
                self.assertTrue(commission.field_rooms <= ALL_FIELD_DUNGEON_ROOMS)
                steps = dict(commission.quest.objective_steps)
                self.assertIn(commission.first_step, steps)
                self.assertIn("report", steps)
                self.assertIn("complete", steps)

    def test_brute_commission_requires_control_then_real_aggro_guarding(self):
        room = next(iter(BRUTE_COMMISSION.field_rooms))
        context = AbilityUseContext(room_key=room, in_combat=True)
        self.assertEqual(
            next_commission_step(BRUTE_COMMISSION, "field_control", "shield_bash", context),
            "field_guard",
        )
        self.assertIsNone(
            next_commission_step(BRUTE_COMMISSION, "field_guard", "hold_the_line", context)
        )
        tanking = AbilityUseContext(room_key=room, in_combat=True, caster_was_top_threat=True)
        self.assertEqual(
            next_commission_step(BRUTE_COMMISSION, "field_guard", "hold_the_line", tanking),
            "report",
        )

    def test_wizard_commission_teaches_control_then_prepared_burst(self):
        room = next(iter(WIZARD_COMMISSION.field_rooms))
        context = AbilityUseContext(room_key=room, in_combat=True)
        self.assertEqual(
            next_commission_step(WIZARD_COMMISSION, "field_control", "frostbind", context),
            "field_burst",
        )
        self.assertEqual(
            next_commission_step(WIZARD_COMMISSION, "field_burst", "arcane_surge", context),
            "report",
        )

    def test_druid_commission_requires_helping_another_player_and_protecting_aggro(self):
        room = next(iter(DRUID_COMMISSION.field_rooms))
        self_only = AbilityUseContext(room_key=room, in_combat=True, target_hp_fraction=0.5)
        self.assertIsNone(
            next_commission_step(DRUID_COMMISSION, "field_recovery", "rejuvenation", self_only)
        )
        injured_ally = AbilityUseContext(
            room_key=room,
            in_combat=True,
            target_is_other=True,
            target_hp_fraction=0.5,
        )
        self.assertEqual(
            next_commission_step(DRUID_COMMISSION, "field_recovery", "rejuvenation", injured_ally),
            "field_protection",
        )
        ordinary_ally = AbilityUseContext(room_key=room, in_combat=True, target_is_other=True)
        self.assertIsNone(
            next_commission_step(DRUID_COMMISSION, "field_protection", "barkskin", ordinary_ally)
        )
        aggro_ally = AbilityUseContext(
            room_key=room,
            in_combat=True,
            target_is_other=True,
            target_was_top_threat=True,
        )
        self.assertEqual(
            next_commission_step(DRUID_COMMISSION, "field_protection", "barkskin", aggro_ally),
            "report",
        )

    def test_priest_commission_is_real_triage_and_group_recovery(self):
        room = next(iter(PRIEST_COMMISSION.field_rooms))
        healthy_ally = AbilityUseContext(
            room_key=room,
            in_combat=True,
            target_is_other=True,
            target_hp_fraction=0.9,
        )
        self.assertIsNone(
            next_commission_step(PRIEST_COMMISSION, "field_triage", "mend_ally", healthy_ally)
        )
        triage = AbilityUseContext(
            room_key=room,
            in_combat=True,
            target_is_other=True,
            target_hp_fraction=0.60,
        )
        self.assertEqual(
            next_commission_step(PRIEST_COMMISSION, "field_triage", "mend_ally", triage),
            "field_group",
        )
        group_recovery = AbilityUseContext(
            room_key=room,
            in_combat=True,
            living_party_count=3,
            injured_party_count=2,
        )
        self.assertEqual(
            next_commission_step(PRIEST_COMMISSION, "field_group", "prayer_of_renewal", group_recovery),
            "report",
        )

    def test_necromancer_commission_requires_skeleton_command_and_defensive_control(self):
        room = next(iter(NECROMANCER_COMMISSION.field_rooms))
        no_pet = AbilityUseContext(room_key=room, in_combat=True)
        self.assertIsNone(
            next_commission_step(NECROMANCER_COMMISSION, "field_command", "grave_command", no_pet)
        )
        skeleton = AbilityUseContext(room_key=room, in_combat=True, active_pet="skeleton")
        self.assertEqual(
            next_commission_step(NECROMANCER_COMMISSION, "field_command", "grave_command", skeleton),
            "field_ward",
        )
        self.assertEqual(
            next_commission_step(NECROMANCER_COMMISSION, "field_ward", "bone_ward", skeleton),
            "report",
        )

    def test_advanced_gear_preserves_universal_equipment_and_builds_on_old_signature_items(self):
        self.assertEqual(len(COMMISSION_PLATES), 5)
        self.assertEqual(len(ADVANCED_SIGNATURE_ITEMS), 5)
        self.assertEqual(len(ADVANCED_SIGNATURE_RECIPES), 5)
        recipe_by_key = {recipe.key: recipe for recipe in ADVANCED_SIGNATURE_RECIPES}
        dungeon_materials = {
            "gravewatch_old_garrison_iron",
            "underclock_governor_bearing",
            "drowned_brass_scrap",
            "brass_auditor_gear",
            "gloamworks_resonant_cog",
        }
        for class_key, (advanced_item_key, recipe_key) in ADVANCED_GEAR_BY_CLASS.items():
            with self.subTest(class_key=class_key):
                item = next(item for item in ADVANCED_SIGNATURE_ITEMS if item.key == advanced_item_key)
                self.assertIsNotNone(item.equipment)
                self.assertTrue(item.equipment.is_universal)
                recipe = recipe_by_key[recipe_key]
                material_keys = {req.item_key for req in recipe.materials}
                base_item_key, _ = CLASS_SIGNATURE_GEAR[class_key]
                plate_key = CLASS_COMMISSIONS_BY_CLASS[class_key].plate_item_key
                self.assertIn(base_item_key, material_keys)
                self.assertIn(plate_key, material_keys)
                self.assertTrue(material_keys & dungeon_materials)

        self.assertEqual(
            set(ADVANCED_AFFINITY_EQUIVALENTS.values()),
            {item.key for item in ADVANCED_SIGNATURE_ITEMS},
        )

    def test_content_registration_is_idempotent_and_updates_live_catalogs(self):
        install_class_world_content()
        install_class_world_content()
        for commission in CLASS_COMMISSIONS:
            self.assertIn(commission.quest.key, quests.QUESTS_BY_KEY)
        for item in (*COMMISSION_PLATES, *ADVANCED_SIGNATURE_ITEMS):
            self.assertIn(item.key, crafting.ITEMS_BY_KEY)
        for recipe in ADVANCED_SIGNATURE_RECIPES:
            self.assertIn(recipe.key, crafting.RECIPES_BY_KEY)

    def test_production_server_installs_field_runtime_quests_and_upgrade_recipes(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.crafting as crafting
import mud.quests as quests
import mud.session as session_module
from mud.class_world_integration import (
    ADVANCED_GEAR_BY_CLASS,
    ADVANCED_SIGNATURE_RECIPES,
    CLASS_COMMISSIONS,
)

assert server.PlayerSession._class_world_integration_runtime_installed
assert len(CLASS_COMMISSIONS) == 5
for commission in CLASS_COMMISSIONS:
    assert commission.quest.key in quests.QUESTS_BY_KEY
    assert commission.plate_item_key in crafting.ITEMS_BY_KEY
for item_key, recipe_key in ADVANCED_GEAR_BY_CLASS.values():
    assert item_key in crafting.ITEMS_BY_KEY
    assert recipe_key in crafting.RECIPES_BY_KEY
recipe_keys = {recipe.key for recipe in ADVANCED_SIGNATURE_RECIPES}
assert recipe_keys <= {recipe.key for recipe in session_module.ALL_RECIPES}
print("CLASS_WORLD_INTEGRATION_OK")
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
        self.assertIn("CLASS_WORLD_INTEGRATION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
