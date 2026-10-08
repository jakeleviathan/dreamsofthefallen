"""Offline tests for atomic checkout reservation and idempotency."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import os

from mud.lanternkeeper_checkout import create_checkout

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

    def test_checkout_passes_price_metadata_and_idempotency_key(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create", return_value=SimpleNamespace(id="cs_test_first", url="https://checkout.stripe.com/test")) as create:
                url = create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                self.assertEqual(url, "https://checkout.stripe.com/test")
                kwargs = create.call_args.kwargs
                self.assertEqual(kwargs["line_items"][0]["price"], "price_1UOAp3LnIVgW4g5mj4rNdD7P")
                self.assertEqual(kwargs["subscription_data"]["metadata"]["dotf_account_id"], str(self.account_id))
                self.assertTrue(kwargs["idempotency_key"].startswith("dotf-lanternkeeper-"))

    def test_repeated_checkout_resumes_saved_open_session(self):
        original = SimpleNamespace(id="cs_test_first", url="https://checkout.stripe.com/first")
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create", return_value=original) as create:
                with patch("stripe.checkout.Session.retrieve", return_value=SimpleNamespace(
                    id=original.id, status="open", url=original.url
                )) as retrieve:
                    first = create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                    second = create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                    self.assertEqual(first, second)
                    create.assert_called_once()
                    retrieve.assert_called_once_with("cs_test_first")
        with self.db.connect() as conn:
            saved = conn.execute(
                "SELECT stripe_session_id FROM lanternkeeper_checkout_reservations WHERE account_id=?",
                (self.account_id,),
            ).fetchone()[0]
        self.assertEqual(saved, "cs_test_first")

    def test_completed_checkout_blocks_duplicate(self):
        original = SimpleNamespace(id="cs_test_first", url="https://checkout.stripe.com/first")
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create", return_value=original) as create:
                create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                with patch("stripe.checkout.Session.retrieve", return_value=SimpleNamespace(
                    id=original.id, status="complete", url=None
                )):
                    with self.assertRaisesRegex(ValueError, "completed"):
                        create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                create.assert_called_once()

    def test_expired_stripe_checkout_gets_new_reservation(self):
        original = SimpleNamespace(id="cs_test_first", url="https://checkout.stripe.com/first")
        fresh = SimpleNamespace(id="cs_test_second", url="https://checkout.stripe.com/second")
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create", side_effect=[original, fresh]) as create:
                create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                with patch("stripe.checkout.Session.retrieve", return_value=SimpleNamespace(
                    id=original.id, status="expired", url=None
                )):
                    url = create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                self.assertEqual(url, fresh.url)
                self.assertNotEqual(
                    create.call_args_list[0].kwargs["idempotency_key"],
                    create.call_args_list[1].kwargs["idempotency_key"],
                )
        with self.db.connect() as conn:
            saved = conn.execute(
                "SELECT stripe_session_id FROM lanternkeeper_checkout_reservations WHERE account_id=?",
                (self.account_id,),
            ).fetchone()[0]
        self.assertEqual(saved, "cs_test_second")

    def test_unknown_stripe_checkout_state_blocks_retry(self):
        original = SimpleNamespace(id="cs_test_first", url="https://checkout.stripe.com/first")
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create", return_value=original) as create:
                create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                with patch("stripe.checkout.Session.retrieve", return_value=SimpleNamespace(
                    id=original.id, status="unknown", url=None
                )):
                    with self.assertRaisesRegex(ValueError, "Cannot verify"):
                        create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                create.assert_called_once()

    def test_legacy_reservation_table_gains_session_id_column(self):
        with self.db.connect() as conn:
            conn.execute("DROP TABLE IF EXISTS lanternkeeper_checkout_reservations")
            conn.execute("""CREATE TABLE lanternkeeper_checkout_reservations (
                account_id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL)""")
        _ensure_checkout_schema(self.db)
        with self.db.connect() as conn:
            columns = {row["name"] for row in conn.execute(
                "PRAGMA table_info(lanternkeeper_checkout_reservations)"
            )}
        self.assertIn("stripe_session_id", columns)

    def test_checkout_rejects_existing_subscription_without_calling_stripe(self):
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO lanternkeeper_memberships(account_id,stripe_subscription_id,stripe_status) VALUES(?,?,?)",
                (self.account_id, "sub_existing", "active"),
            )
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_offline"}):
            with patch("stripe.checkout.Session.create") as create:
                with self.assertRaisesRegex(ValueError, "Existing Lanternkeeper"):
                    create_checkout(self.db, self.account_id, "https://example.test/success", "https://example.test/cancel")
                create.assert_not_called()

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

    def test_expired_reservation_requires_reconciliation(self):
        first, _ = _reserve_checkout(self.db, self.account_id)
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE lanternkeeper_checkout_reservations SET expires_at=0 WHERE account_id=?",
                (self.account_id,),
            )
        with self.assertRaisesRegex(ValueError, "requires reconciliation"):
            _reserve_checkout(self.db, self.account_id)
        with self.db.connect() as conn:
            still_reserved = conn.execute(
                "SELECT request_id FROM lanternkeeper_checkout_reservations WHERE account_id=?",
                (self.account_id,),
            ).fetchone()[0]
        self.assertEqual(first, still_reserved)

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
