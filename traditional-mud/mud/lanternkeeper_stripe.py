"""Verified Stripe subscription webhook handler for Lanternkeeper.

Mount this handler behind an HTTPS endpoint; do not expose it on the telnet port.
Requires stripe-python and DOTF_STRIPE_WEBHOOK_SECRET. Stripe checkout creation
must include metadata.dotf_account_id on the Subscription itself.
"""
import os
from datetime import datetime, timezone
from mud.lanternkeeper_runtime import ensure_schema
from mud.lanternkeeper_checkout import configured_price_id


def _plain_stripe_data(value):
    """Unwrap Stripe SDK 16 objects and nested lists into plain Python values.

    StripeObject exposes to_dict(), not dict.get() or to_dict_recursive().
    Nested StripeObject instances may remain inside dictionaries and lists,
    so unwrap them explicitly before parsing the subscription payload.
    """
    if isinstance(value, dict):
        return {key: _plain_stripe_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_stripe_data(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _plain_stripe_data(to_dict())
    return value

def process_stripe_webhook(database, raw_body: bytes, signature: str):
    import stripe
    secret = os.environ.get("DOTF_STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("Stripe webhook secret is not configured")
    try:
        event = stripe.Webhook.construct_event(raw_body, signature, secret)
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        # Invalid public webhook traffic is a client error, not an internal
        # outage. Never grant entitlements for an unverified payload.
        raise ValueError("Invalid Stripe webhook signature or JSON") from exc
    if event["type"] not in ("customer.subscription.created", "customer.subscription.updated",
                             "customer.subscription.deleted"):
        return False
    sub = event["data"]["object"]
    # Verified Stripe webhook events may contain nested StripeObject values.
    # Normalize once so entitlement logic consistently handles plain dicts.
    sub = _plain_stripe_data(sub)
    expected_price = configured_price_id()
    items = ((sub.get("items") or {}).get("data") or [])
    if not any((item.get("price") or {}).get("id") == expected_price for item in items):
        # Other products in the same Stripe account are not Lanternkeeper events.
        return False
    account_id = (sub.get("metadata") or {}).get("dotf_account_id")
    if not account_id or not str(account_id).isdigit():
        raise ValueError("Subscription missing trusted DOTF account mapping")
    account_id = int(account_id)
    ensure_schema(database)
    with database.connect() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise ValueError("Unknown DOTF account")
        if db.execute("SELECT 1 FROM lanternkeeper_stripe_events WHERE event_id=?", (event["id"],)).fetchone():
            return False
        # Ignore delayed delivery of older events after a newer update.
        db.execute("CREATE TABLE IF NOT EXISTS lanternkeeper_event_clock (account_id INTEGER PRIMARY KEY, created INTEGER NOT NULL)")
        clock = db.execute("SELECT created FROM lanternkeeper_event_clock WHERE account_id=?", (account_id,)).fetchone()
        if clock and int(event["created"]) < int(clock["created"]):
            db.execute("INSERT INTO lanternkeeper_stripe_events(event_id) VALUES (?)", (event["id"],))
            return False
        # Prevent one Stripe subscription from being assigned to multiple accounts.
        existing = db.execute("SELECT account_id FROM lanternkeeper_memberships WHERE stripe_subscription_id=?",
                              (sub["id"],)).fetchone()
        if existing and existing["account_id"] != account_id:
            raise ValueError("Subscription already belongs to another account")
        # A canceled member can subscribe again. Keep the retired subscription
        # identifiers so delayed webhooks cannot overwrite their new membership.
        db.execute("""CREATE TABLE IF NOT EXISTS lanternkeeper_retired_subscriptions (
            stripe_subscription_id TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL
        )""")
        retired = db.execute(
            "SELECT account_id FROM lanternkeeper_retired_subscriptions "
            "WHERE stripe_subscription_id=?", (sub["id"],)
        ).fetchone()
        if retired:
            if retired["account_id"] != account_id:
                raise ValueError("Retired subscription belongs to another account")
            db.execute("INSERT INTO lanternkeeper_stripe_events(event_id) VALUES (?)", (event["id"],))
            return False

        linked = db.execute(
            "SELECT stripe_subscription_id,stripe_customer_id,stripe_status "
            "FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)
        ).fetchone()
        customer = sub.get("customer")
        if not isinstance(customer, str) or not customer:
            raise ValueError("Invalid Stripe customer")
        if linked and linked["stripe_customer_id"] and linked["stripe_customer_id"] != customer:
            raise ValueError("Different Stripe customer linked to DOTF account")
        if linked and linked["stripe_subscription_id"] and linked["stripe_subscription_id"] != sub["id"]:
            if linked["stripe_status"] not in ("canceled", "incomplete_expired"):
                raise ValueError("Different active subscription already linked to account")
            db.execute(
                "INSERT INTO lanternkeeper_retired_subscriptions(stripe_subscription_id,account_id) "
                "VALUES (?,?)", (linked["stripe_subscription_id"], account_id)
            )
        # Newer Stripe API versions report billing periods on subscription items.
        # Use the latest period end among the items belonging to our price.
        period_ends = [
            item.get("current_period_end")
            for item in items
            if (item.get("price") or {}).get("id") == expected_price
            and isinstance(item.get("current_period_end"), int)
        ]
        legacy_end = sub.get("current_period_end")
        if isinstance(legacy_end, int):
            period_ends.append(legacy_end)
        end_timestamp = max(period_ends) if period_ends else None
        end = datetime.fromtimestamp(end_timestamp, timezone.utc).isoformat() if end_timestamp is not None else None
        status = "canceled" if event["type"] == "customer.subscription.deleted" else sub["status"]
        db.execute("""INSERT INTO lanternkeeper_memberships
          (account_id,stripe_customer_id,stripe_subscription_id,stripe_status,current_period_end)
          VALUES (?,?,?,?,?)
          ON CONFLICT(account_id) DO UPDATE SET
          stripe_customer_id=excluded.stripe_customer_id,
          stripe_subscription_id=excluded.stripe_subscription_id,
          stripe_status=excluded.stripe_status,
          current_period_end=excluded.current_period_end""",
          (account_id, customer, sub["id"], status, end))
        db.execute("INSERT INTO lanternkeeper_stripe_events(event_id) VALUES (?)", (event["id"],))
        db.execute("INSERT INTO lanternkeeper_event_clock(account_id,created) VALUES (?,?) ON CONFLICT(account_id) DO UPDATE SET created=excluded.created", (account_id, int(event["created"])))
    return True
