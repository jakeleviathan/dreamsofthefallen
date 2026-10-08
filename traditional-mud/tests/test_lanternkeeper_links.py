"""Offline account-bound, one-use Lanternkeeper web handoff tests."""
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_links import (
    LINK_TTL_SECONDS, consume_action_link, issue_action_link, lookup_action_link,
)
from mud.lanternkeeper_runtime import ensure_schema


class LanternkeeperLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Database(Path(self.tmp.name) / "game.sqlite3")
        ensure_schema(self.database)
        with self.database.connect() as db:
            db.execute("INSERT INTO accounts(name,password_hash) VALUES ('tester','hash')")
            db.execute("INSERT INTO accounts(name,password_hash) VALUES ('other','hash')")
        self.env = patch.dict(os.environ, {
            "DOTF_LANTERNKEEPER_LINKS_ENABLED": "1",
            "DOTF_BILLING_ORIGIN": "https://mud.lvthn.io",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def token(self, url):
        self.assertEqual(urlsplit(url).scheme, "https")
        self.assertEqual(urlsplit(url).path, "/lanternkeeper/confirm")
        return parse_qs(urlsplit(url).query)["ticket"][0]

    def test_link_is_scoped_to_authenticated_account_and_hashed_in_storage(self):
        token = self.token(issue_action_link(self.database, 1, "subscribe"))
        self.assertEqual(lookup_action_link(self.database, token)["account_id"], 1)
        self.assertEqual(lookup_action_link(self.database, token)["name"], "tester")
        with self.database.connect() as db:
            row = db.execute(
                "SELECT token_hash,purpose FROM lanternkeeper_action_links"
            ).fetchone()
        self.assertEqual(row["purpose"], "subscribe")
        self.assertNotIn(token, row["token_hash"])

    def test_link_cannot_be_redeemed_twice(self):
        token = self.token(issue_action_link(self.database, 1, "subscribe"))
        first = consume_action_link(self.database, token)
        self.assertEqual(first["purpose"], "subscribe")
        self.assertIsNone(consume_action_link(self.database, token))
        self.assertIsNone(lookup_action_link(self.database, token))

    def test_expired_link_does_not_redeem(self):
        issued = 1000000
        token = self.token(issue_action_link(self.database, 1, "subscribe", now=issued))
        self.assertIsNotNone(lookup_action_link(self.database, token, now=issued))
        self.assertIsNone(lookup_action_link(
            self.database, token, now=issued + LINK_TTL_SECONDS
        ))
        self.assertIsNone(consume_action_link(
            self.database, token, now=issued + LINK_TTL_SECONDS
        ))

    def test_new_subscribe_link_revokes_old_subscribe_link(self):
        old = self.token(issue_action_link(self.database, 1, "subscribe"))
        new = self.token(issue_action_link(self.database, 1, "subscribe"))
        self.assertNotEqual(old, new)
        self.assertIsNone(lookup_action_link(self.database, old))
        self.assertIsNotNone(lookup_action_link(self.database, new))

    def test_manage_requires_existing_stripe_customer(self):
        with self.assertRaisesRegex(ValueError, "No billing account"):
            issue_action_link(self.database, 1, "manage")
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO lanternkeeper_memberships "
                "(account_id,stripe_customer_id,stripe_subscription_id,stripe_status) "
                "VALUES (1,'cus_test_123','sub_test_123','active')"
            )
        token = self.token(issue_action_link(self.database, 1, "manage"))
        record = lookup_action_link(self.database, token)
        self.assertEqual(record["purpose"], "manage")
        self.assertEqual(record["account_id"], 1)

    def test_links_turned_off_even_if_billing_origin_exists(self):
        with patch.dict(os.environ, {"DOTF_LANTERNKEEPER_LINKS_ENABLED": "0"}):
            with self.assertRaisesRegex(ValueError, "not available"):
                issue_action_link(self.database, 1, "subscribe")

    def test_invalid_token_and_invalid_account_rejected(self):
        self.assertIsNone(consume_action_link(self.database, "fake"))
        self.assertIsNone(lookup_action_link(self.database, "fake"))
        with self.assertRaisesRegex(ValueError, "Unknown game account"):
            issue_action_link(self.database, 500000, "subscribe")
        with self.assertRaisesRegex(ValueError, "Unknown billing action"):
            issue_action_link(self.database, 1, "transfer")

    def test_rejects_insecure_billing_origin(self):
        with patch.dict(os.environ, {"DOTF_BILLING_ORIGIN": "http://mud.lvthn.io"}):
            with self.assertRaisesRegex(RuntimeError, "HTTPS"):
                issue_action_link(self.database, 1, "subscribe")


if __name__ == "__main__":
    unittest.main()
