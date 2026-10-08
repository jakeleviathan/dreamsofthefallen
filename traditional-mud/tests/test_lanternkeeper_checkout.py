"""Offline tests for atomic checkout reservation and idempotency."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_checkout import _reserve_checkout, _ensure_checkout_schema


class LanternkeeperCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "game.db")
        from mud.lanternkeeper_runtime import ensure_schema
        ensure_schema(self.db)
        with self.db.connect() as conn:
            conn.execute("INSERT INTO accounts(name,password_hash) VALUES('tester','hash')")
            self.account_id = conn.execute(
                "SELECT id FROM accounts WHERE name='tester'"
            ).fetchone()[0]

    def test_repeat_checkout_uses_same_reservation(self):
        first, _ = _reserve_checkout(self.db, self.account_id)
        second, _ = _reserve_checkout(self.db, self.account_id)
        self.assertEqual(first, second)

    def test_simultaneous_requests_share_reservation(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(
                lambda _: _reserve_checkout(self.db, self.account_id)[0],
                range(8),
            ))
        self.assertEqual(len(set(results)), 1)

    def test_expired_reservation_is_replaced(self):
        first, _ = _reserve_checkout(self.db, self.account_id)
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE lanternkeeper_checkout_reservations SET expires_at=0 WHERE account_id=?",
                (self.account_id,),
            )
        second, _ = _reserve_checkout(self.db, self.account_id)
        self.assertNotEqual(first, second)

    def test_existing_active_subscription_blocks_checkout(self):
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO lanternkeeper_memberships(account_id,stripe_subscription_id,stripe_status) "
                "VALUES(?,?,?)",
                (self.account_id, "sub_existing", "active"),
            )
        with self.assertRaisesRegex(ValueError, "Existing Lanternkeeper"):
            _reserve_checkout(self.db, self.account_id)


if __name__ == "__main__":
    unittest.main()
