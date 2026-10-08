"""Safely validate a Lanternkeeper sandbox Price without creating payments.

Usage:
    python -m mud.lanternkeeper_sandbox_check

Enter a sandbox sk_test_ key at the non-echoing prompt. The key is never
persisted, printed, or passed as a command-line argument.
"""
import getpass

SANDBOX_PRICE_ID = "price_1UOBtYLsIp78ZNViq1uuSgZf"


def validate_sandbox_price(key, *, stripe_module):
    """Read-only Stripe API check. Never accepts a live secret key."""
    if not key.startswith("sk_test_"):
        raise ValueError("A Stripe sandbox secret key beginning with sk_test_ is required")
    price = stripe_module.Price.retrieve(SANDBOX_PRICE_ID, api_key=key)
    if hasattr(price, "to_dict"):
        price = price.to_dict()
    recurring = price.get("recurring")
    if hasattr(recurring, "to_dict"):
        recurring = recurring.to_dict()
    recurring = recurring or {}
    if not isinstance(recurring, dict):
        raise ValueError("Sandbox price has invalid recurring details")
    if price.get("livemode") is not False:
        raise ValueError("Price was not returned from a Stripe sandbox")
    if price.get("active") is not True:
        raise ValueError("Sandbox price must be active")
    if price.get("currency") != "usd" or price.get("unit_amount") != 499:
        raise ValueError("Sandbox price must be exactly $4.99 USD")
    if recurring.get("interval") != "month" or recurring.get("interval_count") != 1:
        raise ValueError("Sandbox price must recur monthly")
    return True


def main():
    import stripe

    print("Checking the Lanternkeeper sandbox price (read-only; no payments).")
    key = getpass.getpass("Stripe sandbox secret key (input hidden): ")
    try:
        validate_sandbox_price(key, stripe_module=stripe)
    except ValueError as exc:
        raise SystemExit("CHECK FAILED: " + str(exc)) from None
    except stripe.error.StripeError:
        raise SystemExit(
            "CHECK FAILED: Stripe could not retrieve the sandbox price. "
            "Check the sandbox selection and API key."
        ) from None
    finally:
        key = None
    print("PASS: Sandbox Lanternkeeper price is active, USD $4.99 per month.")


if __name__ == "__main__":
    main()
