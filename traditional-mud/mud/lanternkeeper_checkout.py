"""Server-only Stripe Checkout and Billing Portal helpers.

Caller MUST authenticate the MUD account with a server-side session before
passing account_id. Never accept an account id supplied by a browser form.
"""
import os
from mud.lanternkeeper_runtime import ensure_schema

PRICE_ID = "price_1UOAp3LnIVgW4g5mj4rNdD7P"

def create_checkout(database, account_id: int, success_url: str, cancel_url: str):
    import stripe
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise RuntimeError("Stripe secret key missing")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    ensure_schema(database)
    with database.connect() as db:
        account = db.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone()
        if account is None:
            raise ValueError("Unknown account")
        row = db.execute("SELECT stripe_customer_id FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)).fetchone()
    args = dict(mode="subscription", line_items=[{"price": PRICE_ID, "quantity": 1}],
                success_url=success_url, cancel_url=cancel_url,
                client_reference_id=str(account_id),
                subscription_data={"metadata": {"dotf_account_id": str(account_id)}},
                metadata={"dotf_account_id": str(account_id)})
    if row and row["stripe_customer_id"]:
        args["customer"] = row["stripe_customer_id"]
    return stripe.checkout.Session.create(**args).url

def create_billing_portal(database, account_id: int, return_url: str):
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    ensure_schema(database)
    with database.connect() as db:
        row = db.execute("SELECT stripe_customer_id FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)).fetchone()
    if not row or not row["stripe_customer_id"]:
        raise ValueError("No billing customer linked to this account")
    return stripe.billing_portal.Session.create(customer=row["stripe_customer_id"], return_url=return_url).url
