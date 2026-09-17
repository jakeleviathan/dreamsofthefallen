from __future__ import annotations

import asyncio
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.combat_variance import (
    BASIC_WEAPON_DAMAGE,
    DAGGER_DAMAGE,
    HEAVY_AXE_DAMAGE,
    SPEAR_DAMAGE,
    SWORD_DAMAGE,
    TWO_HANDED_DAMAGE,
    DamageDice,
    install_combat_variance_runtime,
    roll_enemy_attack_damage,
    roll_player_weapon_damage,
    roll_spell_base_damage,
    weapon_damage_for_item,
)
from mud.mechanics import CombatantState
from mud.stats import CharacterStats


class EndpointRng:
    def __init__(self, high: bool):
        self.high = high

    def randint(self, low: int, high: int) -> int:
        return high if self.high else low


class DamageDiceTests(unittest.TestCase):
    def test_basic_weapon_preserves_old_average_with_real_range(self):
        self.assertEqual(BASIC_WEAPON_DAMAGE.notation, "1d3")
        self.assertEqual(BASIC_WEAPON_DAMAGE.minimum, 1)
        self.assertEqual(BASIC_WEAPON_DAMAGE.maximum, 3)
        self.assertEqual(BASIC_WEAPON_DAMAGE.average, 2.0)
        self.assertEqual(BASIC_WEAPON_DAMAGE.roll(EndpointRng(False)), 1)
        self.assertEqual(BASIC_WEAPON_DAMAGE.roll(EndpointRng(True)), 3)

    def test_weapon_families_have_distinct_damage_profiles(self):
        self.assertEqual(DAGGER_DAMAGE.notation, "1d4")
        self.assertEqual(SWORD_DAMAGE.notation, "1d6")
        self.assertEqual(SPEAR_DAMAGE.notation, "1d6")
        self.assertEqual(HEAVY_AXE_DAMAGE.notation, "1d8")
        self.assertEqual(TWO_HANDED_DAMAGE.notation, "1d10")

    def test_existing_authored_weapons_resolve_to_expected_families(self):
        self.assertEqual(weapon_damage_for_item("starter_weapon"), BASIC_WEAPON_DAMAGE)
        self.assertEqual(weapon_damage_for_item("human_blackwall_drill_blade"), SWORD_DAMAGE)
        self.assertEqual(weapon_damage_for_item("goblin_patchwork_scrapknife"), DAGGER_DAMAGE)
        self.assertEqual(weapon_damage_for_item("frostroot_notched_spear"), SPEAR_DAMAGE)

    def test_unlisted_weapon_names_receive_family_inference(self):
        axe = SimpleNamespace(name="Old Iron Battle Axe")
        greatsword = SimpleNamespace(name="Ashen Greatsword")
        knife = SimpleNamespace(name="Dockside Knife")
        unknown = SimpleNamespace(name="Strange Fighting Tool")
        self.assertEqual(weapon_damage_for_item("test_axe", axe), HEAVY_AXE_DAMAGE)
        self.assertEqual(weapon_damage_for_item("test_greatsword", greatsword), TWO_HANDED_DAMAGE)
        self.assertEqual(weapon_damage_for_item("test_knife", knife), DAGGER_DAMAGE)
        self.assertEqual(weapon_damage_for_item("test_unknown", unknown), BASIC_WEAPON_DAMAGE)

    def test_might_is_added_after_weapon_roll(self):
        self.assertEqual(roll_player_weapon_damage(6, BASIC_WEAPON_DAMAGE, EndpointRng(False)), 7)
        self.assertEqual(roll_player_weapon_damage(6, BASIC_WEAPON_DAMAGE, EndpointRng(True)), 9)

    def test_enemy_damage_varies_around_authored_center(self):
        self.assertEqual(roll_enemy_attack_damage(4, EndpointRng(False)), 3)
        self.assertEqual(roll_enemy_attack_damage(4, EndpointRng(True)), 5)
        self.assertEqual(roll_enemy_attack_damage(1, EndpointRng(False)), 0)
        self.assertEqual(roll_enemy_attack_damage(1, EndpointRng(True)), 2)
        self.assertEqual(roll_enemy_attack_damage(0, EndpointRng(True)), 0)

    def test_spell_base_damage_has_tight_plus_or_minus_one_range(self):
        self.assertEqual(roll_spell_base_damage(7, EndpointRng(False)), 6)
        self.assertEqual(roll_spell_base_damage(7, EndpointRng(True)), 8)
        self.assertEqual(roll_spell_base_damage(0, EndpointRng(True)), 0)

    def test_damage_dice_validate_inputs(self):
        with self.assertRaises(ValueError):
            DamageDice(0, 6)
        with self.assertRaises(ValueError):
            DamageDice(1, 0)


class RuntimeVarianceTests(unittest.TestCase):
    def test_live_combatant_gets_variable_weapon_and_spell_damage(self):
        class RuntimeSession:
            def __init__(self):
                self.character = SimpleNamespace(id=42)
                self.database = object()
                self.combatant = None

            async def enter_character(self):
                self.combatant = CombatantState(
                    character_id=42,
                    race_key="human",
                    current_hp=30,
                    max_hp=30,
                    current_mana=20,
                    max_mana=20,
                    auto_attack_interval=2.5,
                    stats=CharacterStats(might=6, mind=5),
                )

            async def _combat_loop(self, enemy):
                return None

        install_combat_variance_runtime(RuntimeSession)
        session = RuntimeSession()
        asyncio.run(session.enter_character())
        assert session.combatant is not None

        # The fake database cannot resolve equipment, so the balance-preserving
        # Basic Starting Weapon profile (1d3) is the intended fallback.
        with patch("mud.combat_variance.random.randint", return_value=1):
            self.assertEqual(session.combatant.auto_attack_damage(2), 7)
        with patch("mud.combat_variance.random.randint", return_value=3):
            self.assertEqual(session.combatant.auto_attack_damage(2), 9)

        with patch("mud.combat_variance.random.randint", return_value=6):
            self.assertEqual(session.combatant.spell_damage(7), 11)
        with patch("mud.combat_variance.random.randint", return_value=8):
            self.assertEqual(session.combatant.spell_damage(7), 13)

    def test_unmarked_combatant_keeps_deterministic_foundation_math(self):
        combatant = CombatantState(
            character_id=999,
            race_key="human",
            current_hp=30,
            max_hp=30,
            current_mana=20,
            max_mana=20,
            auto_attack_interval=2.5,
            stats=CharacterStats(might=6, mind=5),
        )
        self.assertEqual(combatant.auto_attack_damage(2), 8)
        self.assertEqual(combatant.spell_damage(7), 12)

    def test_production_entrypoint_installs_damage_variance(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.equipment_system as equipment
from mud.mechanics import CombatantState

assert server.PlayerSession._combat_damage_variance_runtime_installed
assert CombatantState._combat_damage_variance_installed
assert equipment._combat_damage_variance_sync_installed
print("COMBAT_VARIANCE_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("COMBAT_VARIANCE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
