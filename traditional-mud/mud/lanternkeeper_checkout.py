"""Server-side Stripe Checkout and Billing Portal helpers.

An account has one persistent Checkout attempt at a time. Session IDs survive
restarts and Stripe's status is checked before an attempt can be replaced.
When recovery cannot be proven safe, fail closed instead of risking a charge.
"""
import os
import time
import uuid

from mud.lanternkeeper_runtime import ensure_schema

PRICE_ID = "price_1UOAp3LnIVgW4g5mj4rNdD7P"
RESERVATION_SECONDS = 1800
BLOCKING_STATUSES = ("active", "trialing", "past_due", "unpaid", "incomplete", "paused")


def _ensure_checkout_schema(database):
    with database.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS lanternkeeper_checkout_reservations (
            account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            stripe_session_id TEXT UNIQUE
        )""")
        # Upgrade the existing development database without dropping reservations.
        columns = {row["name"] for row in db.execute(
            "PRAGMA table_info(lanternkeeper_checkout_reservations)"
        )}
        if "stripe_session_id" not in columns:
            db.execute(
                "ALTER TABLE lanternkeeper_checkout_reservations ADD COLUMN stripe_session_id TEXT"
            )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "lanternkeeper_checkout_stripe_session_idx "
                "ON lanternkeeper_checkout_reservations(stripe_session_id)"
            )


def _membership_row(db, account_id):
    account = db.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone()
    if account is None:
        raise ValueError("Unknown account")
    membership = db.execute(
        "SELECT stripe_customer_id,stripe_subscription_id,stripe_status "
        "FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)
    ).fetchone()
    if membership and membership["stripe_subscription_id"] and membership["stripe_status"] in BLOCKING_STATUSES:
        raise ValueError("Existing Lanternkeeper subscription: use the billing portal")
    return membership


def _reserve_checkout(database, account_id):
    """Create or reuse the account's atomic Checkout reservation."""
    _ensure_checkout_schema(database)
    now = int(time.time())
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        membership = _membership_row(db, account_id)
        existing = db.execute(
            "SELECT request_id,expires_at FROM lanternkeeper_checkout_reservations "
            "WHERE account_id=?", (account_id,),
        ).fetchone()
        if existing:
            if existing["expires_at"] <= now:
                raise ValueError("Previous checkout requires reconciliation before retrying")
            return existing["request_id"], membership["stripe_customer_id"] if membership else None
        request_id = uuid.uuid4().hex
        db.execute(
            "INSERT INTO lanternkeeper_checkout_reservations(account_id,request_id,expires_at) "
            "VALUES(?,?,?)", (account_id, request_id, now + RESERVATION_SECONDS)
        )
        return request_id, membership["stripe_customer_id"] if membership else None


def _saved_session(database, account_id):
    _ensure_checkout_schema(database)
    with database.connect() as db:
        _membership_row(db, account_id)
        row = db.execute(
            "SELECT request_id,stripe_session_id FROM lanternkeeper_checkout_reservations "
            "WHERE account_id=?", (account_id,)
        ).fetchone()
        return (row["request_id"], row["stripe_session_id"]) if row else (None, None)


def _replace_verified_expired(database, account_id, request_id, session_id):
    """Rotate one reservation only after Stripe reports its Session expired."""
    now = int(time.time())
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _membership_row(db, account_id)
        row = db.execute(
            "SELECT request_id,stripe_session_id FROM lanternkeeper_checkout_reservations "
            "WHERE account_id=?", (account_id,)
        ).fetchone()
        if not row:
            raise ValueError("Missing previous checkout reservation")
        if row["request_id"] != request_id:
            # A different request already reconciled this checkout.
            return
        if row["stripe_session_id"] != session_id:
            raise ValueError("Checkout reservation changed during reconciliation")
        db.execute(
            "UPDATE lanternkeeper_checkout_reservations SET request_id=?,expires_at=?,"
            "stripe_session_id=NULL WHERE account_id=?",
            (uuid.uuid4().hex, now + RESERVATION_SECONDS, account_id),
        )


def _record_session(database, account_id, request_id, session_id):
    if not isinstance(session_id, str) or not session_id.startswith("cs_"):
        raise ValueError("Stripe returned an invalid Checkout session")
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT request_id,stripe_session_id FROM lanternkeeper_checkout_reservations "
            "WHERE account_id=?", (account_id,)
        ).fetchone()
        if not row or row["request_id"] != request_id:
            raise ValueError("Checkout reservation changed during creation")
        if row["stripe_session_id"] not in (None, session_id):
            raise ValueError("Conflicting Checkout session for this account")
        db.execute(
            "UPDATE lanternkeeper_checkout_reservations SET stripe_session_id=? "
            "WHERE account_id=?", (session_id, account_id)
        )


def create_checkout(database, account_id: int, success_url: str, cancel_url: str):
    import stripe
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise RuntimeError("Stripe secret key missing")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    ensure_schema(database)
    _ensure_checkout_schema(database)

    request_id, saved_id = _saved_session(database, account_id)
    if saved_id:
        session = stripe.checkout.Session.retrieve(saved_id)
        if session.id != saved_id:
            raise ValueError("Unexpected Checkout session")
        if session.status == "open":
            if not session.url:
                raise ValueError("Open Checkout session has no payment link")
            return session.url
        if session.status == "complete":
            raise ValueError("Previous checkout completed; wait for subscription confirmation")
        if session.status != "expired":
            raise ValueError("Cannot verify previous Checkout session status")
        _replace_verified_expired(database, account_id, request_id, saved_id)

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
    session = stripe.checkout.Session.create(
        **args, idempotency_key="dotf-lanternkeeper-" + request_id
    )
    _record_session(database, account_id, request_id, session.id)
    if not session.url:
        raise ValueError("Stripe returned a Checkout session without a payment link")
    return session.url


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
