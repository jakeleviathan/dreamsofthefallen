"""Server-side Stripe Checkout and Billing Portal helpers.

Checkout attempts are reserved atomically in SQLite. The Stripe idempotency
key is stable for the reservation lifetime, including across process restarts.
"""
import os
import sqlite3
import time
import uuid

from mud.lanternkeeper_runtime import ensure_schema

PRICE_ID = "price_1UOAp3LnIVgW4g5mj4rNdD7P"
RESERVATION_SECONDS = 1800


def _ensure_checkout_schema(database):
    with database.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS lanternkeeper_checkout_reservations (
            account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )""")


def _reserve_checkout(database, account_id):
    """Return an existing request id or reserve a fresh one atomically."""
    _ensure_checkout_schema(database)
    now = int(time.time())
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        account = db.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone()
        if account is None:
            raise ValueError("Unknown account")
        membership = db.execute(
            "SELECT stripe_customer_id,stripe_subscription_id,stripe_status "
            "FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)
        ).fetchone()
        if membership and membership["stripe_subscription_id"] and membership["stripe_status"] in (
            "active", "trialing", "past_due", "unpaid", "incomplete", "paused"
        ):
            raise ValueError("Existing Lanternkeeper subscription: use the billing portal")
        existing = db.execute(
            "SELECT request_id,expires_at FROM lanternkeeper_checkout_reservations WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if existing and existing["expires_at"] > now:
            return existing["request_id"], membership["stripe_customer_id"] if membership else None
        request_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO lanternkeeper_checkout_reservations(account_id,request_id,expires_at)
               VALUES(?,?,?)
               ON CONFLICT(account_id) DO UPDATE SET
               request_id=excluded.request_id,expires_at=excluded.expires_at""",
            (account_id, request_id, now + RESERVATION_SECONDS),
        )
        return request_id, membership["stripe_customer_id"] if membership else None


def create_checkout(database, account_id: int, success_url: str, cancel_url: str):
    import stripe
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise RuntimeError("Stripe secret key missing")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    ensure_schema(database)
    request_id, customer_id = _reserve_checkout(database, account_id)
    args = dict(
        mode="subscription",
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(account_id),
        subscription_data={"metadata": {"dotf_account_id": str(account_id)}},
        metadata={"dotf_account_id": str(account_id)},
    )
    if customer_id:
        args["customer"] = customer_id
    return stripe.checkout.Session.create(
        **args, idempotency_key="dotf-lanternkeeper-" + request_id
    ).url


def create_billing_portal(database, account_id: int, return_url: str):
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    ensure_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT stripe_customer_id FROM lanternkeeper_memberships WHERE account_id=?",
            (account_id,),
        ).fetchone()
    if not row or not row["stripe_customer_id"]:
        raise ValueError("No billing customer linked to this account")
    return stripe.billing_portal.Session.create(
        customer=row["stripe_customer_id"], return_url=return_url
    ).url
