from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import create_corpse, list_corpses
from mud.database import Database
from mud.stats import CharacterStats


class CorpseLootVisibilityTests(unittest.TestCase):
    def test_corpses_are_scoped_to_the_room_where_the_enemy_died(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "corpse-visibility.db")
        account = database.create_account("corpsevisibility", "hash")
        character = database.create_character(
            account.id,
            "CorpseVisibility",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        room_key = character.current_room
        assert room_key is not None
        create_corpse(
            database,
            room_key,
            "sewer_rat",
            "Sewer Rat",
            owner_character_id=character.id,
            death_key="visibility:test",
        )
        self.assertEqual(len(list_corpses(database, room_key)), 1)
        self.assertEqual(list_corpses(database, "some_other_room"), [])


if __name__ == "__main__":
    unittest.main()
