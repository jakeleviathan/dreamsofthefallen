"""Offline tests for the read-only Stripe sandbox price preflight."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from mud.lanternkeeper_sandbox_check import SANDBOX_PRICE_ID, validate_sandbox_price


class StripeObjectLike:
    """Simulate SDK v16's object that lacks dict.get()."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


def mock_stripe(price):
    stripe = SimpleNamespace(Price=SimpleNamespace(retrieve=Mock(return_value=price)))
    return stripe


def sandbox_price(**changes):
    price = {
        "livemode": False, "active": True, "currency": "usd",
        "unit_amount": 499, "recurring": {"interval": "month", "interval_count": 1},
    }
    price.update(changes)
    return price


class LanternkeeperSandboxPreflightTests(unittest.TestCase):
    def test_accepts_valid_sandbox_price_and_sdk_object(self):
        stripe = mock_stripe(StripeObjectLike(sandbox_price()))
        self.assertTrue(validate_sandbox_price("sk_test_offline", stripe_module=stripe))
        stripe.Price.retrieve.assert_called_once_with(
            SANDBOX_PRICE_ID, api_key="sk_test_offline"
        )

    def test_rejects_live_secret_without_api_call(self):
        stripe = mock_stripe(sandbox_price())
        with self.assertRaisesRegex(ValueError, "sk_test_"):
            validate_sandbox_price("sk_live_never_call", stripe_module=stripe)
        stripe.Price.retrieve.assert_not_called()

    def test_rejects_wrong_price_or_interval(self):
        for fields in (
            {"livemode": True},
            {"active": False},
            {"currency": "eur"},
            {"unit_amount": 500},
            {"recurring": {"interval": "year", "interval_count": 1}},
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    validate_sandbox_price(
                        "sk_test_offline", stripe_module=mock_stripe(sandbox_price(**fields))
                    )


if __name__ == "__main__":
    unittest.main()
