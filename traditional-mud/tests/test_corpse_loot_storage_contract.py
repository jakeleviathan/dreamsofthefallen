from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import create_corpse
from mud.database import Database
from mud.stats import CharacterStats


class CorpseStorageContractTests(unittest.TestCase):
    def test_corpse_is_stored_as_generic_world_container(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "container-contract.db")
        account = database.create_account("containercontract", "hash")
        character = database.create_character(account.id, "ContainerContract", "human", "wizard", CharacterStats(might=5, grace=5, love=5, mind=5, hp=5))
        room_key = character.current_room
        assert room_key is not None
        corpse_id, _ = create_corpse(database, room_key, "sewer_rat", "Sewer Rat", owner_character_id=character.id, death_key="container:contract")
        with database.connect() as db:
            row = db.execute("SELECT kind, source_key FROM world_containers WHERE id = ?", (corpse_id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["kind"], "corpse")
        self.assertEqual(row["source_key"], "sewer_rat")


if __name__ == "__main__":
    unittest.main()
