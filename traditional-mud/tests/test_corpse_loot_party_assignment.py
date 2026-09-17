from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.corpse_loot import add_corpse_item, create_corpse, list_corpse_items
from mud.database import Database
from mud.stats import CharacterStats


class CorpsePartyAssignmentTests(unittest.TestCase):
    def test_different_party_members_can_have_separate_stacks_on_one_corpse(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Database(Path(temp.name) / "party-corpse.db")
        account = database.create_account("partycorpse", "hash")
        one = database.create_character(account.id, "PartyOne", "human", "wizard", CharacterStats(might=5, grace=5, love=5, mind=5, hp=5))
        two = database.create_character(account.id, "PartyTwo", "human", "wizard", CharacterStats(might=5, grace=5, love=5, mind=5, hp=5))
        room_key = one.current_room
        assert room_key is not None
        corpse_id, _ = create_corpse(database, room_key, "sewer_rat", "Sewer Rat", owner_character_id=one.id, protected_character_ids={two.id}, death_key="party:assign")
        add_corpse_item(database, corpse_id, "bone_chips", 1, one.id)
        add_corpse_item(database, corpse_id, "bone_chips", 2, two.id)
        rows = list_corpse_items(database, corpse_id)
        self.assertEqual(sum(row.quantity for row in rows), 3)
        self.assertEqual({row.reserved_character_id for row in rows}, {one.id, two.id})


if __name__ == "__main__":
    unittest.main()
