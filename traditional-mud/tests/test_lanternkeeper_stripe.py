"""Offline Stripe webhook lifecycle tests. No network calls or charges."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_runtime import membership
from mud.lanternkeeper_stripe import process_stripe_webhook

PRICE = "price_1UOAp3LnIVgW4g5mj4rNdD7P"


class LanternkeeperStripeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "game.db")
        with self.db.connect() as conn:
            conn.execute("INSERT INTO accounts(name,password_hash) VALUES('tester','hash')")
            self.account_id = conn.execute("SELECT id FROM accounts WHERE name='tester'").fetchone()[0]
        self.counter = 0

    def event(self, status="active", price=PRICE, event_type="customer.subscription.updated",
              created=100, end=4102444800, event_id=None):
        self.counter += 1
        return {
            "id": event_id or f"evt_{self.counter}",
            "created": created,
            "type": event_type,
            "data": {"object": {
                "id": "sub_lanternkeeper_test",
                "customer": "cus_lanternkeeper_test",
                "status": status,
                "current_period_end": end,
                "metadata": {"dotf_account_id": str(self.account_id)},
                "items": {"data": [{"price": {"id": price}}]},
            }},
        }

    def deliver(self, event):
        # Mock ONLY Stripe signature verification; exercise the real persistence handler.
        with patch.dict(os.environ, {"DOTF_STRIPE_WEBHOOK_SECRET": "whsec_offline_test"}):
            with patch("stripe.Webhook.construct_event", return_value=event):
                return process_stripe_webhook(self.db, json.dumps(event).encode(), "mocked-signature")

    def test_active_then_deleted(self):
        self.assertTrue(self.deliver(self.event()))
        self.assertTrue(membership(self.db, self.account_id).active())
        self.assertTrue(self.deliver(self.event(status="canceled", event_type="customer.subscription.deleted", created=101)))
        self.assertFalse(membership(self.db, self.account_id).active())

    def test_canceled_member_can_rejoin_with_new_subscription(self):
        self.deliver(self.event(status="canceled", event_type="customer.subscription.deleted", created=101))
        new_event = self.event(status="active", created=102)
        new_event["data"]["object"]["id"] = "sub_lanternkeeper_rejoined"
        self.assertTrue(self.deliver(new_event))
        current = membership(self.db, self.account_id)
        self.assertTrue(current.active())
        self.assertEqual(current.subscription_id, "sub_lanternkeeper_rejoined")

    def test_late_retired_subscription_event_cannot_disable_rejoined_member(self):
        self.deliver(self.event(status="canceled", event_type="customer.subscription.deleted", created=101))
        new_event = self.event(status="active", created=102)
        new_event["data"]["object"]["id"] = "sub_lanternkeeper_rejoined"
        self.assertTrue(self.deliver(new_event))
        old_event = self.event(status="canceled", event_type="customer.subscription.deleted", created=103)
        self.assertFalse(self.deliver(old_event))
        current = membership(self.db, self.account_id)
        self.assertTrue(current.active())
        self.assertEqual(current.subscription_id, "sub_lanternkeeper_rejoined")

    def test_active_member_cannot_be_replaced_by_different_subscription(self):
        self.deliver(self.event(status="active", created=101))
        new_event = self.event(status="active", created=102)
        new_event["data"]["object"]["id"] = "sub_unexpected_second"
        with self.assertRaisesRegex(ValueError, "Different active subscription"):
            self.deliver(new_event)

    def test_rejoining_must_keep_existing_stripe_customer(self):
        self.deliver(self.event(status="canceled", event_type="customer.subscription.deleted", created=101))
        new_event = self.event(status="active", created=102)
        new_event["data"]["object"]["id"] = "sub_different_customer"
        new_event["data"]["object"]["customer"] = "cus_other"
        with self.assertRaisesRegex(ValueError, "Different Stripe customer"):
            self.deliver(new_event)

    def test_duplicate_delivery_is_idempotent(self):
        event = self.event(event_id="evt_repeat")
        self.assertTrue(self.deliver(event))
        self.assertFalse(self.deliver(event))

    def test_older_event_cannot_restore_canceled_membership(self):
        self.deliver(self.event(status="canceled", event_type="customer.subscription.deleted", created=200))
        self.assertFalse(self.deliver(self.event(status="active", created=199)))
        self.assertFalse(membership(self.db, self.account_id).active())

    def test_other_price_is_ignored(self):
        self.assertFalse(self.deliver(self.event(price="price_unrelated")))
        self.assertFalse(membership(self.db, self.account_id).active())

    def test_item_level_period_end_activates_membership(self):
        event = self.event(end=None)
        item = event["data"]["object"]["items"]["data"][0]
        item["current_period_end"] = 4102444800
        self.assertTrue(self.deliver(event))
        self.assertTrue(membership(self.db, self.account_id).active())

    def test_item_level_period_end_for_other_price_is_ignored(self):
        event = self.event(end=None)
        event["data"]["object"]["items"]["data"].append(
            {"price": {"id": "price_other"}, "current_period_end": 4102444800}
        )
        self.assertTrue(self.deliver(event))
        self.assertFalse(membership(self.db, self.account_id).active())

    def test_missing_period_end_is_not_active(self):
        self.deliver(self.event(end=None))
        self.assertFalse(membership(self.db, self.account_id).active())


if __name__ == "__main__":
    unittest.main()
