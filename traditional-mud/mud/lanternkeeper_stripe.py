"""Verified Stripe subscription webhook handler for Lanternkeeper.

Mount this handler behind an HTTPS endpoint; do not expose it on the telnet port.
Requires stripe-python and DOTF_STRIPE_WEBHOOK_SECRET. Stripe checkout creation
must include metadata.dotf_account_id on the Subscription itself.
"""
import os
from datetime import datetime, timezone
from mud.lanternkeeper_runtime import ensure_schema

def process_stripe_webhook(database, raw_body: bytes, signature: str):
    import stripe
    secret = os.environ.get("DOTF_STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("Stripe webhook secret is not configured")
    event = stripe.Webhook.construct_event(raw_body, signature, secret)
    if event["type"] not in ("customer.subscription.created", "customer.subscription.updated",
                             "customer.subscription.deleted"):
        return False
    sub = event["data"]["object"]
    expected_price = "price_1UOAp3LnIVgW4g5mj4rNdD7P"
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
        linked = db.execute("SELECT stripe_subscription_id FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)).fetchone()
        if linked and linked["stripe_subscription_id"] and linked["stripe_subscription_id"] != sub["id"]:
            raise ValueError("Different subscription already linked to account")
        customer = sub.get("customer")
        if not isinstance(customer, str):
            raise ValueError("Invalid Stripe customer")
        end_timestamp = sub.get("current_period_end")
        end = datetime.fromtimestamp(end_timestamp, timezone.utc).isoformat() if isinstance(end_timestamp, int) else None
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
