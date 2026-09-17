from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import add_corpse_item, create_corpse
from mud.database import Database
from mud.stats import CharacterStats


class CorpseNoAutoInventoryTests(unittest.TestCase):
    def test_creating_and_filling_corpse_does_not_credit_inventory(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "no-auto.db")
        account = database.create_account("noautoloot", "hash")
        character = database.create_character(
            account.id,
            "NoAutoLoot",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        room_key = character.current_room
        assert room_key is not None
        before = database.item_quantity(character.id, "bone_chips")
        corpse_id, _ = create_corpse(
            database,
            room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=character.id,
            death_key="no-auto:test",
        )
        add_corpse_item(database, corpse_id, "bone_chips", 2, character.id)
        self.assertEqual(database.item_quantity(character.id, "bone_chips"), before)


if __name__ == "__main__":
    unittest.main()
