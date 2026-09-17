from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import add_corpse_item, create_corpse, list_corpse_items, list_corpses
from mud.database import Database
from mud.stats import CharacterStats


class CorpseLootExpiryTests(unittest.TestCase):
    def test_expired_corpse_removes_its_item_rows(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "expiry.db")
        account = database.create_account("expiryaccount", "hash")
        character = database.create_character(
            account.id,
            "ExpiryTester",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        room_key = character.current_room
        assert room_key is not None
        corpse_id, _ = create_corpse(
            database,
            room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=character.id,
            created_at=100.0,
            ttl_seconds=5.0,
            death_key="expiry:test",
        )
        add_corpse_item(database, corpse_id, "bone_chips", 1, character.id)
        self.assertEqual(len(list_corpse_items(database, corpse_id)), 1)
        self.assertEqual(list_corpses(database, room_key, now=106.0), [])
        self.assertEqual(list_corpse_items(database, corpse_id), [])


if __name__ == "__main__":
    unittest.main()
