from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.faction_reputation import (
    adjust_reputation,
    get_reputation,
    merchant_price_multiplier,
    npc_reaction,
    render_reputation,
)


class FactionReputationTests(unittest.TestCase):
    def _database(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "factions.db")
        account = database.create_account("faction_test", "hash")
        character = database.create_character(account.id, "Prime", "goblin", "priest")
        return temp, database, character

    def test_standing_and_renown_are_distinct_and_persistent(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        adjust_reputation(database, character.id, "green_circle", standing=400, renown=90, reason="Helped the grove.")
        self.assertEqual(get_reputation(database, character.id, "green_circle"), (400, 90))
        text = render_reputation(database, character.id)
        self.assertIn("trusted", text)
        self.assertIn("recognized", text)

    def test_allied_word_of_mouth_is_smaller_than_direct_change(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        adjust_reputation(database, character.id, "green_circle", standing=100, renown=100)
        direct = get_reputation(database, character.id, "green_circle")
        ally = get_reputation(database, character.id, "rainroot_chorus")
        self.assertEqual(direct, (100, 100))
        self.assertEqual(ally, (20, 10))

    def test_fame_does_not_mean_liked(self):
        self.assertIn("hatred", npc_reaction(-800, 800))
        self.assertIn("recognizes", npc_reaction(-800, 800))

    def test_merchant_treatment_is_bounded(self):
        self.assertEqual(merchant_price_multiplier(0), 1.0)
        self.assertGreater(merchant_price_multiplier(-800), 1.0)
        self.assertLess(merchant_price_multiplier(800), 1.0)


if __name__ == "__main__":
    unittest.main()
