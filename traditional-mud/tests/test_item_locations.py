from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.item_locations import (
    ItemLocation,
    add_to_location,
    list_container_item_rows,
    list_location_items,
    location_item_quantity,
    transfer_item,
)
from mud.stats import CharacterStats


class ItemLocationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "locations.db")
        account = self.db.create_account("locationaccount", "hash")
        self.character = self.db.create_character(
            account.id,
            "Locator",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        self.room_key = self.character.current_room
        assert self.room_key is not None

    def tearDown(self):
        self.tempdir.cleanup()

    def _container(self) -> int:
        from mud.corpse_loot import create_corpse

        corpse_id, _ = create_corpse(
            self.db,
            self.room_key,
            "test_enemy",
            "Test Enemy",
            owner_character_id=self.character.id,
            death_key="locations:test",
        )
        return corpse_id

    def test_container_reservations_are_separate_but_aggregate_for_inspection(self):
        container_id = self._container()
        add_to_location(
            self.db,
            ItemLocation.container(container_id, self.character.id),
            "bone_chips",
            2,
        )
        add_to_location(
            self.db,
            ItemLocation.container(container_id, 0),
            "bone_chips",
            1,
        )

        self.assertEqual(
            location_item_quantity(
                self.db,
                ItemLocation.container(container_id),
                "bone_chips",
            ),
            3,
        )
        rows = list_container_item_rows(self.db, container_id)
        self.assertEqual(sum(int(row["quantity"]) for row in rows), 3)
        self.assertEqual({int(row["reserved_character_id"]) for row in rows}, {0, self.character.id})

    def test_transfer_requires_exact_container_bucket(self):
        container_id = self._container()
        add_to_location(
            self.db,
            ItemLocation.container(container_id, self.character.id),
            "bone_chips",
            1,
        )
        with self.assertRaises(ValueError):
            transfer_item(
                self.db,
                ItemLocation.container(container_id),
                ItemLocation.character(self.character.id),
                "bone_chips",
                1,
            )

    def test_character_room_container_round_trip_is_atomic(self):
        container_id = self._container()
        self.db.add_item(self.character.id, "bone_chips", 2)

        self.assertTrue(
            transfer_item(
                self.db,
                ItemLocation.character(self.character.id),
                ItemLocation.room(self.room_key),
                "bone_chips",
                2,
            )
        )
        self.assertEqual(self.db.item_quantity(self.character.id, "bone_chips"), 0)
        self.assertEqual(
            list_location_items(self.db, ItemLocation.room(self.room_key)),
            [{"item_key": "bone_chips", "quantity": 2}],
        )

        self.assertTrue(
            transfer_item(
                self.db,
                ItemLocation.room(self.room_key),
                ItemLocation.container(container_id, self.character.id),
                "bone_chips",
                2,
            )
        )
        self.assertEqual(location_item_quantity(self.db, ItemLocation.room(self.room_key), "bone_chips"), 0)
        self.assertTrue(
            transfer_item(
                self.db,
                ItemLocation.container(container_id, self.character.id),
                ItemLocation.character(self.character.id),
                "bone_chips",
                2,
            )
        )
        self.assertEqual(self.db.item_quantity(self.character.id, "bone_chips"), 2)


if __name__ == "__main__":
    unittest.main()
