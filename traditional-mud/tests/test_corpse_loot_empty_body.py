from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import create_corpse, list_corpses
from mud.database import Database
from mud.stats import CharacterStats


class CorpseEmptyBodyTests(unittest.TestCase):
    def test_empty_corpse_still_exists_until_its_decay_timer(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "empty-corpse.db")
        account = database.create_account("emptycorpse", "hash")
        character = database.create_character(
            account.id,
            "EmptyCorpse",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        room_key = character.current_room
        assert room_key is not None
        create_corpse(
            database,
            room_key,
            "empty_enemy",
            "Empty Enemy",
            owner_character_id=character.id,
            created_at=100.0,
            ttl_seconds=10.0,
            death_key="empty:test",
        )
        self.assertEqual(len(list_corpses(database, room_key, now=105.0)), 1)
        self.assertEqual(len(list_corpses(database, room_key, now=111.0)), 0)


if __name__ == "__main__":
    unittest.main()
