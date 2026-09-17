from __future__ import annotations

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mud.combat import EnemyDefinition, EnemyState, SEWER_RAT
from mud.corpse_loot import (
    CORPSE_PROTECTION_SECONDS,
    NAMED_CORPSE_TTL_SECONDS,
    NPC_LOOT_TABLES,
    REGULAR_CORPSE_TTL_SECONDS,
    LootTableEntry,
    add_corpse_item,
    corpse_access_allowed,
    corpse_ttl_seconds_for,
    create_corpse,
    list_corpse_items,
    list_corpses,
    loot_all_command,
    register_loot_table,
    roll_loot_table,
    transfer_all_corpse_loot_to_inventory,
)
from mud.database import Database
from mud.item_locations import (
    ItemLocation,
    currency_balance,
    location_item_quantity,
    transfer_item,
)
from mud.stats import CharacterStats


class FakeSession:
    def __init__(self, database, character, *, can_receive: bool = True):
        self.database = database
        self.character = character
        self.active_enemy = None
        self.outputs: list[str] = []
        self._can_receive = can_receive

    async def send(self, text: str) -> None:
        self.outputs.append(text)

    def can_receive_item(self, _item_key: str, _quantity: int = 1) -> bool:
        return self._can_receive


class CorpseLootTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "corpse.db")
        account = self.db.create_account("corpseaccount", "hash")
        self.killer = self.db.create_character(
            account.id,
            "Killer",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        self.other = self.db.create_character(
            account.id,
            "Other",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        self.room_key = self.killer.current_room
        assert self.room_key is not None
        self.db.set_character_room(self.other.id, self.room_key)
        refreshed = self.db.get_character_by_name("Other")
        assert refreshed is not None
        self.other = refreshed
        self._old_rat_table = NPC_LOOT_TABLES.get("sewer_rat")

    def tearDown(self):
        if self._old_rat_table is None:
            NPC_LOOT_TABLES.pop("sewer_rat", None)
        else:
            NPC_LOOT_TABLES["sewer_rat"] = self._old_rat_table
        self.tempdir.cleanup()

    def test_data_driven_entries_roll_independently_with_quantity_ranges(self):
        register_loot_table(
            "sewer_rat",
            (
                LootTableEntry("bone_chips", chance=0.50, min_quantity=1, max_quantity=1),
                LootTableEntry("starter_weapon", chance=1.0, min_quantity=2, max_quantity=4),
                LootTableEntry("sealed_cathedral_note", chance=0.0),
            ),
        )
        enemy = EnemyState(SEWER_RAT)

        with patch("mud.corpse_loot.random", return_value=0.25), patch(
            "mud.corpse_loot.randint", side_effect=[1, 3]
        ):
            rolled = roll_loot_table(enemy)

        self.assertEqual(rolled, (("bone_chips", 1), ("starter_weapon", 3)))

    def test_regular_and_named_corpses_use_different_decay_windows(self):
        self.assertEqual(corpse_ttl_seconds_for(EnemyState(SEWER_RAT)), REGULAR_CORPSE_TTL_SECONDS)
        named = EnemyDefinition(
            key="test_named_commander",
            name="Test Named Commander",
            aliases=("commander",),
            description="a test commander",
            max_hp=100,
            armor_class=10,
            auto_attack_damage=5,
            auto_attack_interval=2.0,
            xp_reward=100,
        )
        self.assertEqual(
            corpse_ttl_seconds_for(EnemyState(named)),
            NAMED_CORPSE_TTL_SECONDS,
        )

    def test_corpse_persists_until_decay_then_cleans_up(self):
        corpse_id, created = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            created_at=1_000.0,
            ttl_seconds=REGULAR_CORPSE_TTL_SECONDS,
            death_key="test:persist",
        )
        self.assertTrue(created)
        add_corpse_item(self.db, corpse_id, "bone_chips", 2, self.killer.id)

        self.assertEqual(len(list_corpses(self.db, self.room_key, now=1_299.0)), 1)
        self.assertEqual(len(list_corpses(self.db, self.room_key, now=1_301.0)), 0)
        self.assertEqual(list_corpse_items(self.db, corpse_id), [])

    def test_death_key_prevents_duplicate_physical_corpses(self):
        first_id, first_created = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            death_key="static:room:rat:1",
        )
        second_id, second_created = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            death_key="static:room:rat:1",
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_id, second_id)
        self.assertEqual(len(list_corpses(self.db, self.room_key)), 1)

    def test_kill_group_is_protected_then_corpse_becomes_public(self):
        created_at = 2_000.0
        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            protected_character_ids={self.other.id},
            created_at=created_at,
            protection_seconds=CORPSE_PROTECTION_SECONDS,
            death_key="test:protected",
        )
        corpse = list_corpses(self.db, self.room_key, now=created_at)[0]

        self.assertTrue(corpse_access_allowed(self.db, corpse, self.killer.id, now=2_030.0))
        self.assertTrue(corpse_access_allowed(self.db, corpse, self.other.id, now=2_030.0))

        outsider_account = self.db.create_account("outsider", "hash")
        outsider = self.db.create_character(
            outsider_account.id,
            "Outsider",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        self.assertFalse(corpse_access_allowed(self.db, corpse, outsider.id, now=2_030.0))
        self.assertTrue(corpse_access_allowed(self.db, corpse, outsider.id, now=2_061.0))
        self.assertGreater(corpse_id, 0)

    def test_party_assignment_is_private_during_protection_but_public_afterward(self):
        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            protected_character_ids={self.other.id},
            death_key="test:assignments",
        )
        add_corpse_item(self.db, corpse_id, "bone_chips", 2, self.killer.id)

        moved, _blocked = transfer_all_corpse_loot_to_inventory(
            self.db,
            self.other.id,
            corpse_id,
            public=False,
        )
        self.assertEqual(moved, [])
        self.assertEqual(self.db.item_quantity(self.other.id, "bone_chips"), 0)

        moved, _blocked = transfer_all_corpse_loot_to_inventory(
            self.db,
            self.other.id,
            corpse_id,
            public=True,
        )
        self.assertEqual(sum(row.quantity for row in moved), 2)
        self.assertEqual(self.db.item_quantity(self.other.id, "bone_chips"), 2)

    def test_loot_command_leaves_items_on_corpse_when_capacity_hook_blocks_them(self):
        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            death_key="test:capacity",
        )
        add_corpse_item(self.db, corpse_id, "bone_chips", 2, self.killer.id)
        session = FakeSession(self.db, self.killer, can_receive=False)

        asyncio.run(loot_all_command(session, "corpse"))

        self.assertEqual(self.db.item_quantity(self.killer.id, "bone_chips"), 0)
        self.assertEqual(sum(row.quantity for row in list_corpse_items(self.db, corpse_id)), 2)
        self.assertIn("cannot carry", "".join(session.outputs).lower())

    def test_loot_command_moves_items_and_currency_only_when_taken(self):
        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            currency_amount=7,
            death_key="test:loot-command",
        )
        add_corpse_item(self.db, corpse_id, "bone_chips", 2, self.killer.id)
        session = FakeSession(self.db, self.killer)

        self.assertEqual(self.db.item_quantity(self.killer.id, "bone_chips"), 0)
        self.assertEqual(currency_balance(self.db, self.killer.id), 0)
        asyncio.run(loot_all_command(session, "corpse"))

        self.assertEqual(self.db.item_quantity(self.killer.id, "bone_chips"), 2)
        self.assertEqual(currency_balance(self.db, self.killer.id), 7)
        self.assertEqual(list_corpse_items(self.db, corpse_id), [])
        self.assertIn("2x Bone Chips", "".join(session.outputs))

    def test_ground_inventory_and_container_use_one_atomic_transfer_path(self):
        self.db.add_item(self.killer.id, "bone_chips", 3)
        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=self.killer.id,
            death_key="test:locations",
        )

        self.assertTrue(
            transfer_item(
                self.db,
                ItemLocation.character(self.killer.id),
                ItemLocation.room(self.room_key),
                "bone_chips",
                2,
            )
        )
        self.assertTrue(
            transfer_item(
                self.db,
                ItemLocation.room(self.room_key),
                ItemLocation.container(corpse_id, self.killer.id),
                "bone_chips",
                1,
            )
        )

        self.assertEqual(self.db.item_quantity(self.killer.id, "bone_chips"), 1)
        self.assertEqual(location_item_quantity(self.db, ItemLocation.room(self.room_key), "bone_chips"), 1)
        self.assertEqual(
            location_item_quantity(
                self.db,
                ItemLocation.container(corpse_id, self.killer.id),
                "bone_chips",
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
