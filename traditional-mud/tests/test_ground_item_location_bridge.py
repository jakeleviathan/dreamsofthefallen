from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.ground_items import (
    ground_item_quantity,
    transfer_ground_to_inventory,
    transfer_inventory_to_ground,
)
from mud.item_locations import ItemLocation, location_item_quantity
from mud.stats import CharacterStats


class GroundItemLocationBridgeTests(unittest.TestCase):
    def test_drop_and_pickup_share_the_generic_location_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "ground-location.db")
        account = database.create_account("groundlocation", "hash")
        character = database.create_character(
            account.id,
            "GroundLocation",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        room_key = character.current_room
        assert room_key is not None
        database.add_item(character.id, "bone_chips", 2)

        self.assertTrue(
            transfer_inventory_to_ground(database, character.id, room_key, "bone_chips", 2)
        )
        self.assertEqual(ground_item_quantity(database, room_key, "bone_chips"), 2)
        self.assertEqual(
            location_item_quantity(database, ItemLocation.room(room_key), "bone_chips"),
            2,
        )

        self.assertTrue(
            transfer_ground_to_inventory(database, character.id, room_key, "bone_chips", 1)
        )
        self.assertEqual(database.item_quantity(character.id, "bone_chips"), 1)
        self.assertEqual(
            location_item_quantity(database, ItemLocation.room(room_key), "bone_chips"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
