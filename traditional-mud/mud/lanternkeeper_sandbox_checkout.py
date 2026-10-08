"""Create a real Stripe *sandbox* subscription Checkout through Lanternkeeper.

This is a manual staging-only harness, NOT the production billing endpoint.
It creates a distinct test MUD account and SQLite DB outside the live checkout,
then exercises the existing authenticated HTTP billing route on loopback.

Usage: python -m mud.lanternkeeper_sandbox_checkout

Both secrets are collected with getpass (never shell arguments or files).
Checkout sessions, subscriptions, and test card payments are Stripe sandbox
objects. This command does not open any public web port or touch the live MUD.
"""
import getpass
import http.client
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from unittest.mock import patch

from mud.database import Database
from mud.security import hash_password, verify_password
from mud.lanternkeeper_http import start_lanternkeeper_http
from mud.lanternkeeper_sandbox_check import SANDBOX_PRICE_ID, validate_sandbox_price


STAGING_ACCOUNT = "lanternkeeper_staging"
STAGING_ORIGIN = "https://mud.lvthn.io"
STAGING_DIRECTORY = Path.home() / "dotf-lanternkeeper-staging"


def prepare_staging_account(directory: Path, password: str):
    """Use only an isolated staging database and account, never MUD_DB_PATH."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Staging directory cannot be a symlink")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    db_path = directory / "sandbox.sqlite3"
    if db_path.is_symlink():
        raise ValueError("Staging database cannot be a symlink")
    with patch.dict(os.environ, {"MUD_DB_PATH": str(db_path)}):
        database = Database(db_path)
        with database.connect() as db:
            row = db.execute(
                "SELECT id,password_hash FROM accounts WHERE name=?",
                (STAGING_ACCOUNT,),
            ).fetchone()
            if row is None:
                if len(password) < 12:
                    raise ValueError("Use at least 12 characters for the staging password")
                db.execute(
                    "INSERT INTO accounts(name,password_hash) VALUES (?,?)",
                    (STAGING_ACCOUNT, hash_password(password)),
                )
            elif not verify_password(password, row["password_hash"]):
                raise ValueError("Incorrect password for existing staging account")
    db_path.chmod(0o600)
    return db_path


def create_staging_checkout(secret_key: str, password: str, directory=STAGING_DIRECTORY):
    """Return a Stripe-hosted sandbox Checkout URL after real HTTP authentication."""
    import stripe

    if not secret_key.startswith("sk_test_"):
        raise ValueError("Only sk_test_ keys are allowed in the checkout harness")
    # Prove the key resolves to our *sandbox* $4.99/month Price before checkout.
    validate_sandbox_price(secret_key, stripe_module=stripe)
    db_path = prepare_staging_account(directory, password)
    staging_env = {
        "MUD_DB_PATH": str(db_path),
        "DOTF_BILLING_ORIGIN": STAGING_ORIGIN,
        "DOTF_LANTERNKEEPER_PRICE_ID": SANDBOX_PRICE_ID,
        "STRIPE_SECRET_KEY": secret_key,
    }
    with patch.dict(os.environ, staging_env):
        # Port zero chooses an unused loopback port; no public Caddy route.
        server = start_lanternkeeper_http(host="127.0.0.1", port=0)
        try:
            body = urlencode({"account": STAGING_ACCOUNT, "password": password})
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_port, timeout=30
            )
            try:
                connection.request(
                    "POST", "/lanternkeeper/checkout", body,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": STAGING_ORIGIN,
                        # Simulates Caddy injection; this is loopback only.
                        "X-Lanternkeeper-Client-IP": "127.0.0.1",
                    },
                )
                response = connection.getresponse()
                result = response.status
                location = response.getheader("Location")
                response.read()
            finally:
                connection.close()
            if result != 303 or not location:
                raise ValueError(
                    "Staging Checkout was not created (HTTP %d); "
                    "no billing URL can be used" % result
                )
            parsed = urlsplit(location)
            if parsed.scheme != "https" or parsed.hostname != "checkout.stripe.com":
                raise ValueError("Stripe returned an unexpected Checkout destination")
            return location
        finally:
            server.shutdown()
            server.server_close()


def main():
    print("Lanternkeeper sandbox checkout; no real money will be charged.")
    print("An isolated test account and DB are kept in ~/dotf-lanternkeeper-staging.")
    print("Use a NEW staging-only password, never your real MUD password.")
    password = getpass.getpass("Staging test account password (hidden): ")
    secret_key = getpass.getpass("Stripe sandbox sk_test_ secret key (hidden): ")
    try:
        url = create_staging_checkout(secret_key, password)
    except ValueError as exc:
        raise SystemExit("CHECK FAILED: " + str(exc)) from None
    except Exception as exc:
        # Stripe errors may include request details; do not print secrets.
        raise SystemExit(
            "CHECK FAILED: Checkout request was unsuccessful; "
            "review the Stripe sandbox logs and application setup."
        ) from None
    finally:
        password = None
        secret_key = None
    print("PASS: Lanternkeeper sandbox Checkout created.")
    print("OPEN THIS STRIPE SANDBOX CHECKOUT IN YOUR BROWSER:")
    print(url)
    print("Use a Stripe test card, not a real card.")
    print("The return page may not be online yet; verify payment in the Stripe sandbox.")
    print("Do not paste the Checkout URL or any secrets into chat.")


if __name__ == "__main__":
    main()
