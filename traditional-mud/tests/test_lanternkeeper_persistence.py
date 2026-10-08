import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from mud.database import Database
from mud.lanternkeeper_runtime import ensure_schema, load_wisp, save_wisp, membership, room_wisp_lines
from mud.lanternkeeper_wisp import LanternWisp


class LanternkeeperPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "game.db")
        ensure_schema(self.db)
        with self.db.connect() as conn:
            conn.execute("INSERT INTO accounts(name,password_hash) VALUES('tester','hash')")
            self.account_id = conn.execute("SELECT id FROM accounts WHERE name='tester'").fetchone()[0]
            conn.execute("INSERT INTO characters(account_id,name) VALUES(?,?)", (self.account_id, 'WispTester'))
            self.character_id = conn.execute("SELECT id FROM characters WHERE name='WispTester'").fetchone()[0]

    def test_character_cosmetics_persist(self):
        wisp = LanternWisp()
        wisp.set_name("Starlight")
        wisp.set_color("gold")
        wisp.summoned = True
        save_wisp(self.db, self.character_id, wisp)
        loaded = load_wisp(self.db, self.character_id)
        self.assertEqual(loaded.name, "Starlight")
        self.assertEqual(loaded.color, "gold")
        self.assertTrue(loaded.summoned)

    def test_active_membership_and_room_visibility(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        with self.db.connect() as conn:
            conn.execute("INSERT INTO lanternkeeper_memberships(account_id,stripe_status,current_period_end) VALUES(?,?,?)",
                         (self.account_id, "active", expiry))
            conn.execute("UPDATE characters SET current_room='waymeet' WHERE id=?", (self.character_id,))
        wisp = LanternWisp(summoned=True)
        save_wisp(self.db, self.character_id, wisp)
        self.assertTrue(membership(self.db, self.account_id).active())
        self.assertEqual(len(room_wisp_lines(self.db, 'waymeet', {self.character_id})), 1)
        self.assertEqual(room_wisp_lines(self.db, 'waymeet', set()), [])
        with self.db.connect() as conn:
            conn.execute("UPDATE lanternkeeper_memberships SET stripe_status='canceled' WHERE account_id=?", (self.account_id,))
        self.assertEqual(room_wisp_lines(self.db, 'waymeet', {self.character_id}), [])
        self.assertTrue(load_wisp(self.db, self.character_id).summoned)


if __name__ == "__main__":
    unittest.main()
