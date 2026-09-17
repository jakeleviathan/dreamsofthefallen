from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import add_corpse_item, create_corpse, transfer_corpse_item_to_inventory
from mud.database import Database
from mud.stats import CharacterStats


class CorpseSpecificItemTests(unittest.TestCase):
    def test_specific_quantity_moves_without_emptying_other_drops(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "specific-corpse.db")
        account = database.create_account("specificcorpse", "hash")
        character = database.create_character(
            account.id,
            "SpecificCorpse",
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
            death_key="specific:test",
        )
        add_corpse_item(database, corpse_id, "bone_chips", 3, character.id)
        self.assertTrue(
            transfer_corpse_item_to_inventory(
                database,
                character.id,
                corpse_id,
                "bone_chips",
                2,
            )
        )
        self.assertEqual(database.item_quantity(character.id, "bone_chips"), 2)


if __name__ == "__main__":
    unittest.main()
