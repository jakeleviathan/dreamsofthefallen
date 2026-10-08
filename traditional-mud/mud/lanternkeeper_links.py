"""Short-lived, account-scoped browser handoff for in-game Lanternkeeper billing.

Authenticated game sessions mint a random, single-use link; browsers never
receive the MUD password and the game never receives card information.
The token is stored only as a SHA-256 hash in the shared SQLite database.
"""
import hashlib
import os
import re
import secrets
import time
from urllib.parse import urlsplit

LINK_TTL_SECONDS = 600
PURPOSES = ("subscribe", "manage")
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,64}$")


def billing_origin():
    origin = os.environ.get("DOTF_BILLING_ORIGIN", "").rstrip("/")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise RuntimeError("Billing origin must be an HTTPS host without a path or query")
    return origin


def links_enabled():
    # MUD-side opt-in is independent of the billing web worker's startup.
    return os.environ.get("DOTF_LANTERNKEEPER_LINKS_ENABLED") == "1"


def ensure_link_schema(database):
    with database.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS lanternkeeper_action_links (
            token_hash TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            purpose TEXT NOT NULL CHECK(purpose IN ('subscribe','manage')),
            expires_at INTEGER NOT NULL,
            consumed_at INTEGER
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS idx_lanternkeeper_action_links_account
                      ON lanternkeeper_action_links(account_id)""")


def _hash(token):
    if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
        return None
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_action_link(database, account_id, purpose, now=None):
    """Issue a bearer link only on an authenticated game session."""
    if not links_enabled():
        raise ValueError("Lanternkeeper subscriptions are not available yet")
    if purpose not in PURPOSES:
        raise ValueError("Unknown billing action")
    origin = billing_origin()
    now = int(time.time() if now is None else now)
    ensure_link_schema(database)
    if purpose == "manage":
        from mud.lanternkeeper_runtime import ensure_schema
        ensure_schema(database)
    token = secrets.token_urlsafe(32)
    digest = _hash(token)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise ValueError("Unknown game account")
        if purpose == "manage":
            # Schema is initialized before the transaction so this check
            # cannot implicitly commit the token-issuance transaction.
            row = db.execute(
                "SELECT stripe_customer_id FROM lanternkeeper_memberships WHERE account_id=?",
                (account_id,),
            ).fetchone()
            if row is None or not row["stripe_customer_id"]:
                raise ValueError("No billing account yet. Try LANTERNKEEPER SUBSCRIBE")
        # Creating another link revokes earlier unused links for the same action.
        db.execute(
            "DELETE FROM lanternkeeper_action_links WHERE account_id=? AND purpose=?",
            (account_id, purpose),
        )
        db.execute(
            "INSERT INTO lanternkeeper_action_links(token_hash,account_id,purpose,expires_at) "
            "VALUES (?,?,?,?)",
            (digest, account_id, purpose, now + LINK_TTL_SECONDS),
        )
    return origin + "/lanternkeeper/confirm?ticket=" + token


def lookup_action_link(database, token, now=None):
    """Return account and purpose only for an existing, unexpired, unused token."""
    digest = _hash(token)
    if digest is None:
        return None
    now = int(time.time() if now is None else now)
    ensure_link_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT l.account_id,l.purpose,a.name FROM lanternkeeper_action_links l "
            "JOIN accounts a ON a.id=l.account_id "
            "WHERE l.token_hash=? AND l.consumed_at IS NULL AND l.expires_at>?",
            (digest, now),
        ).fetchone()
    return dict(row) if row else None


def consume_action_link(database, token, now=None):
    """Atomically redeem a token once, including across concurrent web workers."""
    digest = _hash(token)
    if digest is None:
        return None
    now = int(time.time() if now is None else now)
    ensure_link_schema(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT l.account_id,l.purpose,a.name FROM lanternkeeper_action_links l "
            "JOIN accounts a ON a.id=l.account_id "
            "WHERE l.token_hash=? AND l.consumed_at IS NULL AND l.expires_at>?",
            (digest, now),
        ).fetchone()
        if row is None:
            return None
        updated = db.execute(
            "UPDATE lanternkeeper_action_links SET consumed_at=? "
            "WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?",
            (now, digest, now),
        )
        if updated.rowcount != 1:
            return None
        return dict(row)
