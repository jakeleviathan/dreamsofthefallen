from __future__ import annotations

import unittest

import mud.combat as combat
import mud.economy_balance as economy_balance
import mud.economy_loop as economy
from mud.content_loot import (
    _GENERATED_KEYS,
    build_content_loot_table,
    install_content_loot_tables,
    loot_family_for,
    register_content_loot_items,
)
from mud.corpse_loot import LootTableEntry, NPC_LOOT_TABLES, register_loot_table


class ContentLootTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tables = dict(NPC_LOOT_TABLES)
        self._generated = set(_GENERATED_KEYS)
        economy.install_economy_content()
        economy_balance.install_economy_balance_content()
        register_content_loot_items()

    def tearDown(self) -> None:
        NPC_LOOT_TABLES.clear()
        NPC_LOOT_TABLES.update(self._tables)
        _GENERATED_KEYS.clear()
        _GENERATED_KEYS.update(self._generated)

    def test_existing_guaranteed_and_secondary_drops_are_preserved(self):
        rat = combat.ENEMIES_BY_KEY["sewer_rat"]
        table = build_content_loot_table(rat)
        by_key = {entry.item_key: entry for entry in table}

        self.assertEqual(by_key["rough_hide"].chance, 1.0)
        self.assertGreaterEqual(by_key["tough_sinew"].chance, 0.35)

    def test_family_profiles_are_thematic(self):
        undead = combat.EnemyDefinition(
            key="test_crypt_wight",
            name="Crypt Wight",
            aliases=("wight",),
            description="an undead guardian made of old bone and grave cloth",
            max_hp=50,
            armor_class=5,
            auto_attack_damage=4,
            auto_attack_interval=3.0,
            xp_reward=80,
        )
        construct = combat.EnemyDefinition(
            key="test_clockwork_sentry",
            name="Clockwork Sentry",
            aliases=("sentry",),
            description="a mechanical construct of plates and gears",
            max_hp=50,
            armor_class=5,
            auto_attack_damage=4,
            auto_attack_interval=3.0,
            xp_reward=80,
        )

        self.assertEqual(loot_family_for(undead), "undead")
        self.assertEqual(loot_family_for(construct), "construct")
        self.assertIn("grave_dust", {entry.item_key for entry in build_content_loot_table(undead)})
        self.assertIn("construct_scrap", {entry.item_key for entry in build_content_loot_table(construct)})

    def test_named_enemy_scales_primary_quantity_without_guaranteeing_it(self):
        boss = combat.EnemyDefinition(
            key="test_marsh_warden",
            name="Marsh Warden",
            aliases=("warden",),
            description="a brutal swamp hunter",
            max_hp=300,
            armor_class=12,
            auto_attack_damage=12,
            auto_attack_interval=2.5,
            xp_reward=350,
        )
        table = build_content_loot_table(boss)
        primary = table[0]
        self.assertEqual(primary.max_quantity, 3)
        self.assertLessEqual(primary.chance, 0.95)

    def test_authored_explicit_table_wins_over_generated_coverage(self):
        custom = (LootTableEntry("greenleaf", 0.07, 1, 1),)
        register_loot_table("sewer_rat", custom)
        _GENERATED_KEYS.discard("sewer_rat")

        coverage = install_content_loot_tables()

        self.assertEqual(NPC_LOOT_TABLES["sewer_rat"], custom)
        self.assertGreaterEqual(coverage.authored_tables_preserved, 1)
        self.assertEqual(coverage.missing_tables, ())

    def test_training_dummy_does_not_gain_physical_loot(self):
        self.assertEqual(build_content_loot_table(combat.ENEMIES_BY_KEY["training_dummy"]), ())


if __name__ == "__main__":
    unittest.main()
