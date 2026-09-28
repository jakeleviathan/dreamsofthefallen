from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.item_heritage as heritage
import mud.regional_blacksmithing as smith
from mud.database import Database
from mud.crafting import ItemDefinition
from mud.stats import CharacterStats, EquipmentItem


class RegionalBlacksmithingTests(unittest.TestCase):
    def test_regional_blacksmithing_catalog_has_requested_depth(self) -> None:
        counts = smith.catalog_counts()

        self.assertEqual(len(smith.TRADITIONS), 9)
        self.assertEqual(counts["regional_patterns"], 378)
        self.assertEqual(counts["components"], 21)
        self.assertEqual(counts["quench_media"], 9)
        self.assertEqual(counts["alloy_billets"], 3)
        self.assertEqual(counts["hidden_techniques"], 9)
        self.assertEqual(
            len({recipe.key for recipe in smith.RECIPES}),
            len(smith.RECIPES),
        )
        self.assertEqual(
            len({item.key for item in smith.ITEMS}),
            len(smith.ITEMS),
        )

    def test_every_regional_pattern_uses_components_quench_and_lesson(self) -> None:
        for tradition in smith.TRADITIONS:
            for metal in crafting.METAL_TIERS:
                rows = [
                    recipe
                    for recipe in smith.RECIPES
                    if recipe.design_status == "regional_blacksmith_pattern"
                    and recipe.key.startswith(
                        f"smith_pattern_{tradition.key}_{metal.key}_"
                    )
                ]
                self.assertEqual(len(rows), 6)
                self.assertTrue(
                    all(
                        recipe.discovery_flag
                        == smith.lesson_flag(tradition.key, metal.key)
                        for recipe in rows
                    )
                )
                self.assertTrue(
                    all(
                        any(
                            requirement.item_key
                            == smith.quench_key(tradition.key)
                            for requirement in recipe.materials
                        )
                        for recipe in rows
                    )
                )
                self.assertTrue(
                    all(
                        any(
                            requirement.item_key.startswith(
                                f"smith_{metal.key}_"
                            )
                            for requirement in recipe.materials
                        )
                        for recipe in rows
                    )
                )

    def test_regional_blacksmithing_static_materials_are_real_items(self) -> None:
        known = (
            set(crafting.ITEMS_BY_KEY)
            | {item.key for item in economy.ECONOMY_ITEMS}
            | {item.key for item in smith.ITEMS}
        )
        missing = {
            requirement.item_key
            for recipe in smith.RECIPES
            for requirement in recipe.materials
            if requirement.item_key not in known
        }
        self.assertEqual(missing, set())

    def test_reforging_never_reduces_base_weapon_stats(self) -> None:
        base = ItemDefinition(
            "test_old_sword",
            "Test Old Sword",
            "An old test blade.",
            "equipment",
            EquipmentItem(
                "Test Old Sword",
                "main_hand",
                stat_bonuses=CharacterStats(might=3, grace=2),
            ),
            tier=1,
        )

        reforged = smith._reforge_stats(
            base,
            crafting.METAL_TIERS_BY_KEY["cobalt"],
        )

        self.assertGreaterEqual(reforged.stat_bonuses.might, 4)
        self.assertEqual(reforged.stat_bonuses.grace, 2)
        self.assertEqual(reforged.armor_class, 0)

    def test_metals_have_distinct_mechanical_character(self) -> None:
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["iron"]).hp, 1)
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["steel"]).might, 1)
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["cobalt"]).grace, 1)
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["moonsteel"]).mind, 1)
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["emberite"]).might, 2)
        self.assertEqual(smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["stariron"]).hp, 2)
        astralite = smith._metal_bonus(crafting.METAL_TIERS_BY_KEY["astralite"])
        self.assertEqual((astralite.grace, astralite.mind, astralite.hp), (1, 1, 2))

    def test_reforge_transaction_preserves_one_heritage_serial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "smithing.db")
            account = database.create_account("smith", "test-hash")
            character = database.create_character(
                account.id,
                "Hammerhand",
                "dwarf",
                "brute",
            )
            database.add_item(character.id, "iron_sword", 1)
            database.add_item(character.id, "cobalt_ingot", 2)

            ok, serial, error = smith._reforge_transaction(
                database,
                character_id=character.id,
                source_key="iron_sword",
                output_key="cobalt_sword",
                ingot_key="cobalt_ingot",
                ingot_quantity=2,
                serial=None,
            )

            self.assertTrue(ok, error)
            self.assertIsNotNone(serial)
            self.assertEqual(database.item_quantity(character.id, "iron_sword"), 0)
            self.assertEqual(database.item_quantity(character.id, "cobalt_sword"), 1)
            self.assertEqual(database.item_quantity(character.id, "cobalt_ingot"), 0)

            record = heritage.provenance_by_serial(database, str(serial))
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record["item_key"], "cobalt_sword")
            self.assertEqual(record["serial"], serial)
            self.assertEqual(record["events"][-1]["event_type"], "reforged")

    def test_reforge_cost_scales_with_piece_size(self) -> None:
        weapon = ItemDefinition(
            "test_sword",
            "Test Sword",
            "",
            "equipment",
            EquipmentItem("Test Sword", "main_hand"),
            tier=1,
        )
        shield = ItemDefinition(
            "test_shield",
            "Test Shield",
            "",
            "equipment",
            EquipmentItem("Test Shield", "off_hand"),
            tier=1,
        )
        armor = ItemDefinition(
            "test_breastplate",
            "Test Breastplate",
            "",
            "equipment",
            EquipmentItem("Test Breastplate", "chest"),
            tier=1,
        )

        self.assertEqual(smith._reforge_cost(weapon), 2)
        self.assertEqual(smith._reforge_cost(shield), 3)
        self.assertEqual(smith._reforge_cost(armor), 4)


if __name__ == "__main__":
    unittest.main()
