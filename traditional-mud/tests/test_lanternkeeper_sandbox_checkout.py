"""Offline integration checks for sandbox Checkout; no Stripe network calls."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_sandbox_checkout import (
    STAGING_ACCOUNT, create_staging_checkout, prepare_staging_account,
)


class LanternkeeperSandboxCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "staging"
        self.password = "staging-only-password-123"

    def test_checkout_runs_through_authenticated_http_and_persists_reservation(self):
        session = SimpleNamespace(
            id="cs_test_staging", url="https://checkout.stripe.com/c/pay/staging"
        )
        with patch("mud.lanternkeeper_sandbox_checkout.validate_sandbox_price") as check:
            with patch("stripe.checkout.Session.create", return_value=session) as create:
                url = create_staging_checkout(
                    "sk_test_offline", self.password, self.directory
                )
        self.assertEqual(url, session.url)
        check.assert_called_once()
        create.assert_called_once()
        self.assertEqual(
            create.call_args.kwargs["line_items"][0]["price"],
            "price_1UOBtYLsIp78ZNViq1uuSgZf",
        )
        self.assertEqual(
            create.call_args.kwargs["subscription_data"]["metadata"]["dotf_account_id"],
            "1",
        )
        db = Database(self.directory / "sandbox.sqlite3")
        with db.connect() as conn:
            account = conn.execute(
                "SELECT id FROM accounts WHERE name=?", (STAGING_ACCOUNT,)
            ).fetchone()
            session_id = conn.execute(
                "SELECT stripe_session_id FROM lanternkeeper_checkout_reservations "
                "WHERE account_id=?", (account["id"],)
            ).fetchone()[0]
        self.assertEqual(session_id, "cs_test_staging")

    def test_repeated_checkout_resumes_same_stripe_session(self):
        session = SimpleNamespace(
            id="cs_test_staging", url="https://checkout.stripe.com/c/pay/staging"
        )
        with patch("mud.lanternkeeper_sandbox_checkout.validate_sandbox_price"):
            with patch("stripe.checkout.Session.create", return_value=session) as create:
                with patch("stripe.checkout.Session.retrieve", return_value=SimpleNamespace(
                    id=session.id, status="open", url=session.url,
                )) as retrieve:
                    first = create_staging_checkout(
                        "sk_test_offline", self.password, self.directory
                    )
                    second = create_staging_checkout(
                        "sk_test_offline", self.password, self.directory
                    )
        self.assertEqual(first, second)
        create.assert_called_once()
        retrieve.assert_called_once_with("cs_test_staging")

    def test_rejects_live_key_without_network_or_database(self):
        with patch("mud.lanternkeeper_sandbox_checkout.validate_sandbox_price") as check:
            with self.assertRaisesRegex(ValueError, "sk_test_"):
                create_staging_checkout(
                    "sk_live_not_allowed", self.password, self.directory
                )
            check.assert_not_called()
        self.assertFalse(self.directory.exists())

    def test_rejects_different_staging_password(self):
        prepare_staging_account(self.directory, self.password)
        with self.assertRaisesRegex(ValueError, "Incorrect password"):
            prepare_staging_account(self.directory, "different-staging-password")

    def test_never_uses_inherited_production_database_path(self):
        decoy_path = Path(self.tmp.name) / "production-would-be-wrong.sqlite3"
        with patch.dict(os.environ, {"MUD_DB_PATH": str(decoy_path)}):
            prepare_staging_account(self.directory, self.password)
        self.assertFalse(decoy_path.exists())
        self.assertTrue((self.directory / "sandbox.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
