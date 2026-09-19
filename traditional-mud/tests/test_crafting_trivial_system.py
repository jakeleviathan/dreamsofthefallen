from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import mud.crafting as crafting
import mud.economy_loop as economy
from mud.database import Database


class CraftingTrivialSystemTests(unittest.TestCase):
    def setUp(self):
        economy.install_economy_content()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "crafting.db")
        account = self.db.create_account("crafting_rules", "hash")
        self.character = self.db.create_character(account.id, "Artisan", "human", "wizard")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_success_curve_and_attempt_cap(self):
        skill = 100
        expected = {
            0: 1.00,
            1: 0.95,
            5: 0.95,
            6: 0.85,
            10: 0.85,
            11: 0.70,
            20: 0.70,
            21: 0.50,
            30: 0.50,
            31: 0.30,
            40: 0.30,
            41: 0.15,
            50: 0.15,
            51: 0.00,
        }
        for gap, chance in expected.items():
            with self.subTest(gap=gap):
                self.assertEqual(crafting.craft_success_chance(skill, skill + gap), chance)

    def test_skillup_curve_stops_at_trivial(self):
        skill = 100
        expected = {
            0: 0.00,
            1: 0.06,
            5: 0.06,
            6: 0.12,
            10: 0.12,
            11: 0.20,
            20: 0.20,
            21: 0.25,
            30: 0.25,
            31: 0.30,
            50: 0.30,
            51: 0.00,
        }
        for gap, chance in expected.items():
            with self.subTest(gap=gap):
                self.assertEqual(crafting.craft_skillup_chance(skill, skill + gap), chance)

    def test_trivial_recipe_is_guaranteed_and_cannot_raise_skill(self):
        self.db.add_item(self.character.id, "iron_ore", 2)

        result = crafting.craft_recipe(
            self.db,
            self.character.id,
            "smelt_iron_ingot",
            station_key="forge",
            success_roll=0.999999,
            skillup_roll=0.0,
        )

        self.assertTrue(result.completed)
        self.assertTrue(result.success)
        self.assertFalse(result.skill_increased)
        self.assertEqual(result.success_chance, 1.0)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ore"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ingot"), 1)
        progress = self.db.get_trade_skill_progress(self.character.id, "blacksmithing")
        self.assertEqual(progress["uses"], 1)
        self.assertEqual(progress["skill_xp"], 0)

    def test_failed_completed_craft_consumes_materials_and_can_teach(self):
        self.db.add_item(self.character.id, "iron_ingot", 2)

        result = crafting.craft_recipe(
            self.db,
            self.character.id,
            "forge_iron_sword",
            station_key="forge",
            success_roll=0.99,
            skillup_roll=0.0,
        )

        self.assertTrue(result.completed)
        self.assertFalse(result.success)
        self.assertTrue(result.skill_increased)
        self.assertEqual(result.new_skill_value, 1)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ingot"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_sword"), 0)
        progress = self.db.get_trade_skill_progress(self.character.id, "blacksmithing")
        self.assertEqual(progress["uses"], 1)
        self.assertEqual(progress["skill_xp"], 1)

    def test_recipe_more_than_fifty_above_skill_cannot_be_attempted(self):
        self.db.add_item(self.character.id, "emberite_ore", 2)

        result = crafting.craft_recipe(
            self.db,
            self.character.id,
            "smelt_emberite_ingot",
            station_key="forge",
            success_roll=0.0,
            skillup_roll=0.0,
        )

        self.assertFalse(result.completed)
        self.assertFalse(result.success)
        self.assertIn("too difficult", result.message.lower())
        self.assertEqual(self.db.item_quantity(self.character.id, "emberite_ore"), 2)
        self.assertEqual(
            self.db.get_trade_skill_progress(self.character.id, "blacksmithing"),
            {"uses": 0, "skill_xp": 0},
        )

    def test_craft_time_stays_in_three_to_six_second_band(self):
        for recipe in crafting.ALL_RECIPES:
            duration = crafting.craft_time_seconds(recipe)
            self.assertGreaterEqual(duration, 3.0)
            self.assertLessEqual(duration, 6.0)

    def test_movement_interrupts_channel_without_material_loss(self):
        self.db.set_character_room(self.character.id, "dwarf_workshop_tier")
        character = self.db.get_character_by_name(self.character.name)
        self.db.add_item(character.id, "iron_ore", 2)

        class BaseSession:
            def __init__(self):
                self.database = self_outer.db
                self.character = character
                self.active_enemy = None
                self.combatant = None
                self.outputs = []
                self.moves = 0

            async def send(self, text):
                self.outputs.append(text)

            async def prompt(self, _text):
                return None

            async def playing_prompt(self):
                return None

            async def move_character(self, _direction):
                self.moves += 1

            async def close(self):
                return None

        self_outer = self

        class Session(BaseSession):
            pass

        economy.install_economy_loop_runtime(Session)
        session = Session()

        async def scenario():
            await economy._craft(session, "iron ingot")
            self.assertIsInstance(getattr(session, "_active_craft", None), dict)
            await session.move_character("north")
            await asyncio.sleep(0)

        asyncio.run(scenario())

        self.assertEqual(session.moves, 1)
        self.assertIsNone(getattr(session, "_active_craft", None))
        self.assertEqual(self.db.item_quantity(character.id, "iron_ore"), 2)
        self.assertEqual(self.db.item_quantity(character.id, "iron_ingot"), 0)
        self.assertIn("No materials are consumed", "".join(session.outputs))

    def test_damage_interrupts_channel_without_material_loss(self):
        self.db.set_character_room(self.character.id, "dwarf_workshop_tier")
        character = self.db.get_character_by_name(self.character.name)
        self.db.add_item(character.id, "iron_ore", 2)

        class Session:
            def __init__(self):
                self.database = self_outer.db
                self.character = character
                self.active_enemy = None
                self.combatant = SimpleNamespace(current_hp=20)
                self.outputs = []

            async def send(self, text):
                self.outputs.append(text)

        self_outer = self
        session = Session()

        async def scenario():
            with patch.object(crafting, "craft_time_seconds", return_value=0.5):
                await economy._craft(session, "iron ingot")
                await asyncio.sleep(0.05)
                session.combatant.current_hp = 19
                await asyncio.sleep(0.30)

        asyncio.run(scenario())

        self.assertIsNone(getattr(session, "_active_craft", None))
        self.assertEqual(self.db.item_quantity(character.id, "iron_ore"), 2)
        self.assertEqual(self.db.item_quantity(character.id, "iron_ingot"), 0)
        self.assertIn("interrupted by damage", "".join(session.outputs))


if __name__ == "__main__":
    unittest.main()
