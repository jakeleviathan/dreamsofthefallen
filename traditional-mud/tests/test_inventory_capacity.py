from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.crafting as crafting
import mud.equipment_system as equipment
from mud.database import Database
from mud.inventory_capacity import (
    BASE_INVENTORY_SLOTS,
    BAG_RECIPES,
    BAGS_BY_KEY,
    can_receive_item,
    crafting_output_fits,
    install_bag_content,
    install_bag_slot,
    inventory_capacity_status,
    inventory_slot_capacity,
)
from mud.merchants import (
    ASHEN_WAY_CURIO_PEDDLER_MERCHANT,
    GOBLIN_BRASSGUT_MERCHANT,
    REGIONAL_STARTER_MERCHANTS,
    UNDEAD_CHISEL_MERCHANT,
    WAYMEET_SEVRA_MERCHANT,
)
from mud.stats import CharacterStats


class InventoryCapacityTests(unittest.TestCase):
    def setUp(self) -> None:
        install_bag_slot()
        install_bag_content()
        self.tmp = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tmp.name) / "inventory-capacity.db")
        account = self.database.create_account("bags", "x")
        self.character = self.database.create_character(
            account.id,
            "Packrat",
            "goblin",
            "priest",
            CharacterStats(might=4, grace=7, love=12, mind=6, hp=5),
            deity_key="zerjz",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bag_slot_and_capacity_expand_without_nested_inventories(self):
        self.assertIn("bag", equipment.EQUIPMENT_SLOTS)
        self.assertEqual(equipment.normalize_slot("backpack"), "bag")
        self.assertEqual(inventory_slot_capacity(self.database, self.character.id), BASE_INVENTORY_SLOTS)

        self.database.add_item(self.character.id, "bag_brassgut_salvage_sack", 1)
        equipment.set_equipped_item(
            self.database,
            self.character.id,
            "bag",
            "bag_brassgut_salvage_sack",
        )

        used, capacity = inventory_capacity_status(self.database, self.character.id)
        self.assertEqual(capacity, BASE_INVENTORY_SLOTS + 6)
        self.assertGreaterEqual(used, 2)
        bag = crafting.ITEMS_BY_KEY["bag_brassgut_salvage_sack"]
        self.assertEqual(bag.equipment.inventory_slots, 6)

    def test_inventory_slots_count_item_stacks_not_stack_quantity(self):
        self.database.add_item(self.character.id, "greenleaf", 50)
        used_after_first_stack, _ = inventory_capacity_status(self.database, self.character.id)
        self.database.add_item(self.character.id, "greenleaf", 50)
        used_after_second_stack, _ = inventory_capacity_status(self.database, self.character.id)
        self.assertEqual(used_after_first_stack, used_after_second_stack)

    def test_full_inventory_allows_existing_stacks_but_blocks_new_item_types(self):
        existing = {str(row["item_key"]) for row in self.database.list_items(self.character.id)}
        index = 0
        while len(existing) < BASE_INVENTORY_SLOTS:
            key = f"capacity_fixture_{index}"
            self.database.add_item(self.character.id, key, 1)
            existing.add(key)
            index += 1

        self.assertFalse(can_receive_item(self.database, self.character.id, "brand_new_stack", 1))
        first_existing = next(iter(existing))
        self.assertTrue(can_receive_item(self.database, self.character.id, first_existing, 99))

    def test_unequipping_a_bag_never_discards_existing_items(self):
        self.database.add_item(self.character.id, "bag_brassgut_salvage_sack", 1)
        equipment.set_equipped_item(self.database, self.character.id, "bag", "bag_brassgut_salvage_sack")
        while inventory_capacity_status(self.database, self.character.id)[0] < BASE_INVENTORY_SLOTS + 3:
            used, _ = inventory_capacity_status(self.database, self.character.id)
            self.database.add_item(self.character.id, f"overflow_fixture_{used}", 1)

        before = list(self.database.list_items(self.character.id))
        equipment.clear_equipped_slot(self.database, self.character.id, "bag")
        after = list(self.database.list_items(self.character.id))
        used, capacity = inventory_capacity_status(self.database, self.character.id)

        self.assertEqual(before, after)
        self.assertGreater(used, capacity)
        self.assertFalse(can_receive_item(self.database, self.character.id, "another_new_stack", 1))

    def test_bag_tailoring_progression_reaches_master_capacity(self):
        slots = [
            crafting.ITEMS_BY_KEY[recipe.output_item_key].equipment.inventory_slots
            for recipe in BAG_RECIPES
        ]
        self.assertEqual(slots, sorted(slots))
        self.assertEqual(slots[0], 14)
        self.assertEqual(slots[-1], 36)
        self.assertEqual(BAGS_BY_KEY["bag_astralweave_wayfarer_pack"].extra_slots, 36)

    def test_crafting_can_replace_a_consumed_stack_at_capacity(self):
        recipe = next(recipe for recipe in BAG_RECIPES if recipe.output_item_key == "bag_wool_trail_pack")
        self.database.add_item(self.character.id, "wool_cloth", 3)
        existing = {str(row["item_key"]) for row in self.database.list_items(self.character.id)}
        index = 0
        while len(existing) < BASE_INVENTORY_SLOTS:
            key = f"craft_capacity_fixture_{index}"
            self.database.add_item(self.character.id, key, 1)
            existing.add(key)
            index += 1

        self.assertTrue(crafting_output_fits(self.database, self.character.id, recipe))

    def test_regional_merchants_stock_bags(self):
        self.assertTrue(ASHEN_WAY_CURIO_PEDDLER_MERCHANT.sells("bag_blackwall_road_satchel"))
        self.assertTrue(GOBLIN_BRASSGUT_MERCHANT.sells("bag_brassgut_salvage_sack"))
        self.assertTrue(UNDEAD_CHISEL_MERCHANT.sells("bag_gravecloth_courier_bag"))
        self.assertTrue(WAYMEET_SEVRA_MERCHANT.sells("bag_waymeet_caravan_pack"))
        regional_keys = {
            entry.item_key
            for merchant in REGIONAL_STARTER_MERCHANTS
            for entry in merchant.stock
        }
        for key in (
            "bag_greenway_forager_pack",
            "bag_moonstep_travelers_bag",
            "bag_chainmark_tool_pack",
            "bag_frostroot_hide_pack",
            "bag_lumen_sporewoven_pack",
        ):
            self.assertIn(key, regional_keys)

    def test_inventory_view_reports_used_and_max_slots(self):
        class FakeSession:
            def __init__(self, database, character):
                self.database = database
                self.character = character
                self.outputs: list[str] = []

            async def send(self, text: str) -> None:
                self.outputs.append(text)

        session = FakeSession(self.database, self.character)
        asyncio.run(equipment._show_inventory(session))
        output = "".join(session.outputs)
        self.assertIn("Inventory:", output)
        self.assertIn(f"/{BASE_INVENTORY_SLOTS}slots", output.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
