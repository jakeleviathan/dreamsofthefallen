from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mud.character_slot_payments import (
    account_from_purchase_token,
    fulfill_stripe_event,
    purchase_link_for_account,
    sign_purchase_token,
    verify_stripe_event,
)
from mud.database import CharacterSlotLimitReached, Database


def checkout_event(*, account_id=1, checkout_id="cs_test_first", status="paid", price_id="price_test_slot"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": checkout_id,
                "object": "checkout.session",
                "mode": "payment",
                "payment_status": status,
                "currency": "usd",
                "amount_subtotal": 100,
                "metadata": {
                    "dotf_item": "extra_character_slot",
                    "dotf_account_id": str(account_id),
                    "dotf_price_id": price_id,
                },
            }
        },
    }


class CharacterSlotPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name) / "slots.sqlite")
        self.account = self.db.create_account("Buyer", "hashed-password")

    def test_eight_free_slots_and_purchased_ninth_slot_persist_across_reopen(self):
        for i in range(8):
            self.db.create_character(self.account.id, f"Hero{i}", "human", "wizard")
        self.assertEqual(self.db.character_slot_limit(self.account.id), 8)
        with self.assertRaises(CharacterSlotLimitReached):
            self.db.create_character(self.account.id, "HeroEight", "human", "wizard")

        self.assertTrue(self.db.record_character_slot_purchase(self.account.id, "cs_test_one"))
        self.assertFalse(self.db.record_character_slot_purchase(self.account.id, "cs_test_one"))
        self.assertEqual(self.db.character_slot_limit(self.account.id), 9)
        ninth = self.db.create_character(self.account.id, "HeroEight", "human", "wizard")
        self.assertEqual(len(self.db.list_characters(self.account.id)), 9)
        with self.assertRaises(CharacterSlotLimitReached):
            self.db.create_character(self.account.id, "HeroNine", "human", "wizard")

        reopened = Database(self.db.path)
        self.assertEqual(reopened.character_slot_limit(self.account.id), 9)
        self.assertTrue(reopened.delete_character(self.account.id, ninth.id))
        self.assertEqual(reopened.character_slot_limit(self.account.id), 9)

    def test_purchases_are_account_scoped_and_additive(self):
        other = self.db.create_account("Other", "hash")
        self.db.record_character_slot_purchase(self.account.id, "cs_test_a")
        self.db.record_character_slot_purchase(self.account.id, "cs_test_b")
        self.assertEqual(self.db.character_slot_limit(self.account.id), 10)
        self.assertEqual(self.db.character_slot_limit(other.id), 8)
        self.assertFalse(self.db.record_character_slot_purchase(self.account.id, "cs_test_a"))
        self.assertEqual(self.db.character_slot_limit(self.account.id), 10)

    def test_rejects_invalid_grants_and_missing_accounts(self):
        with self.assertRaises(ValueError):
            self.db.record_character_slot_purchase(self.account.id, "", 1)
        with self.assertRaises(ValueError):
            self.db.record_character_slot_purchase(self.account.id, "cs_test_many", 2)
        with self.assertRaises(KeyError):
            self.db.record_character_slot_purchase(999999, "cs_test_missing")

    def test_purchase_link_is_account_bound_and_expires(self):
        token = sign_purchase_token(self.account.id, "development secret", now=1000)
        self.assertEqual(
            account_from_purchase_token(token, "development secret", now=1001),
            self.account.id,
        )
        with self.assertRaises(ValueError):
            account_from_purchase_token(token, "development secret", now=3000)
        with self.assertRaises(ValueError):
            account_from_purchase_token(token[:-1] + "a", "development secret", now=1001)
        with self.assertRaises(ValueError):
            account_from_purchase_token("!!invalid!!", "development secret", now=1001)

    def test_menu_purchase_link_requires_full_secure_configuration(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(purchase_link_for_account(self.account.id))
        config = {
            "DOTF_STRIPE_SECRET_KEY": "sk_test_example",
            "DOTF_SLOT_STRIPE_PRICE_ID": "price_test_slot",
            "DOTF_SLOT_STRIPE_WEBHOOK_SECRET": "whsec_example",
            "DOTF_SLOT_LINK_SECRET": "development-signing-secret",
            "DOTF_SLOT_PUBLIC_BASE_URL": "https://mud.lvthn.io",
        }
        with patch.dict("os.environ", config, clear=True):
            link = purchase_link_for_account(self.account.id)
            self.assertTrue(link.startswith("https://mud.lvthn.io/slots/checkout?token="))

    def test_verified_paid_event_grants_once_and_never_grants_unpaid_or_wrong_product(self):
        event = checkout_event(account_id=self.account.id)
        self.assertTrue(fulfill_stripe_event(self.db, event, expected_price_id="price_test_slot"))
        self.assertFalse(fulfill_stripe_event(self.db, event, expected_price_id="price_test_slot"))
        self.assertEqual(self.db.character_slot_limit(self.account.id), 9)

        unpaid = checkout_event(account_id=self.account.id, checkout_id="cs_test_unpaid", status="unpaid")
        self.assertFalse(fulfill_stripe_event(self.db, unpaid, expected_price_id="price_test_slot"))
        mismatched = checkout_event(account_id=self.account.id, checkout_id="cs_test_wrong", price_id="price_other")
        self.assertFalse(fulfill_stripe_event(self.db, mismatched, expected_price_id="price_test_slot"))
        wrong_amount = checkout_event(account_id=self.account.id, checkout_id="cs_test_amount")
        wrong_amount["data"]["object"]["amount_subtotal"] = 50
        self.assertFalse(fulfill_stripe_event(self.db, wrong_amount, expected_price_id="price_test_slot"))
        self.assertEqual(self.db.character_slot_limit(self.account.id), 9)

    def test_webhook_must_have_valid_stripe_signature_and_fresh_timestamp(self):
        payload = json.dumps(checkout_event(account_id=self.account.id)).encode("utf-8")
        timestamp = 1000
        digest = hmac.new(
            b"whsec_test", str(timestamp).encode() + b"." + payload, hashlib.sha256
        ).hexdigest()
        header = f"t={timestamp},v1={digest}"
        event = verify_stripe_event(payload, header, "whsec_test", now=1000)
        self.assertEqual(event["type"], "checkout.session.completed")
        with self.assertRaises(ValueError):
            verify_stripe_event(payload, header, "whsec_wrong", now=1000)
        with self.assertRaises(ValueError):
            verify_stripe_event(payload, header, "whsec_test", now=1400)
        with self.assertRaises(ValueError):
            verify_stripe_event(payload, "", "whsec_test", now=1000)


if __name__ == "__main__":
    unittest.main()
