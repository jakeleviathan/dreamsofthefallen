"""Persistent, transferable Lantern Favors. No player-facing mint operation.

Payment fulfillment must authenticate and validate the Stripe event before calling
mint_paid_favor. Each favor remains in the ledger after redemption.
"""
import sqlite3
import uuid

REWARDS = {
    "character_slot": 1, "rename": 1, "cosmetic_title": 2,
    "room_description": 2, "wisp_customization": 1,
    "memorial_lantern": 1, "community_project": 1,
    "cosmetic_gift": 1, "appearance": 2, "housing_decoration": 2,
}

def ensure_schema(database):
    with database.connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS lantern_favors (
            id TEXT PRIMARY KEY,
            owner_account_id INTEGER NOT NULL REFERENCES accounts(id),
            payment_reference TEXT UNIQUE,
            redeemed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_favors_owner ON lantern_favors(owner_account_id);
        CREATE TABLE IF NOT EXISTS lantern_favor_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            favor_id TEXT NOT NULL REFERENCES lantern_favors(id),
            event_type TEXT NOT NULL CHECK(event_type IN ('mint','transfer','redeem')),
            from_account_id INTEGER REFERENCES accounts(id),
            to_account_id INTEGER REFERENCES accounts(id),
            message TEXT NOT NULL DEFAULT '',
            reward_key TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lantern_favor_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            reward_key TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lantern_favor_redemption_items (
            redemption_id INTEGER NOT NULL REFERENCES lantern_favor_redemptions(id),
            favor_id TEXT NOT NULL UNIQUE REFERENCES lantern_favors(id),
            PRIMARY KEY (redemption_id, favor_id)
        );
        """)

def mint_paid_favor(database, account_id, payment_reference):
    """Call only after verified payment; idempotent on payment reference."""
    if not payment_reference or not payment_reference.startswith("cs_"):
        raise ValueError("Verified Stripe Checkout Session ID required")
    ensure_schema(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise ValueError("Unknown account")
        existing = db.execute("SELECT id,owner_account_id FROM lantern_favors WHERE payment_reference=?", (payment_reference,)).fetchone()
        if existing:
            if existing["owner_account_id"] != account_id:
                raise ValueError("Payment already assigned to another account")
            return existing["id"], False
        favor_id = "LF-" + uuid.uuid4().hex[:16].upper()
        db.execute("INSERT INTO lantern_favors(id,owner_account_id,payment_reference) VALUES (?,?,?)", (favor_id, account_id, payment_reference))
        db.execute("INSERT INTO lantern_favor_events(favor_id,event_type,to_account_id) VALUES (?,'mint',?)", (favor_id, account_id))
        return favor_id, True

def transfer(database, favor_id, sender_account_id, recipient_account_id, message=""):
    if sender_account_id == recipient_account_id:
        raise ValueError("Cannot transfer to yourself")
    if len(message) > 240:
        raise ValueError("Message exceeds 240 characters")
    ensure_schema(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (recipient_account_id,)).fetchone():
            raise ValueError("Recipient not found")
        changed = db.execute("UPDATE lantern_favors SET owner_account_id=? WHERE id=? AND owner_account_id=? AND redeemed_at IS NULL",
                             (recipient_account_id, favor_id, sender_account_id))
        if changed.rowcount != 1:
            raise ValueError("Favor unavailable or not yours")
        db.execute("INSERT INTO lantern_favor_events(favor_id,event_type,from_account_id,to_account_id,message) VALUES (?,'transfer',?,?,?)",
                   (favor_id, sender_account_id, recipient_account_id, message))

def redeem(database, favor_ids, account_id, reward_key, details=""):
    if reward_key not in REWARDS:
        raise ValueError("Unknown reward")
    if len(details) > 500:
        raise ValueError("Details exceed 500 characters")
    if len(favor_ids) != REWARDS[reward_key] or len(set(favor_ids)) != len(favor_ids):
        raise ValueError("Incorrect Favor count")
    ensure_schema(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for favor_id in favor_ids:
            row = db.execute("SELECT owner_account_id,redeemed_at FROM lantern_favors WHERE id=?", (favor_id,)).fetchone()
            if not row or row["owner_account_id"] != account_id or row["redeemed_at"]:
                raise ValueError("Favor unavailable or not yours")
        cur = db.execute("INSERT INTO lantern_favor_redemptions(account_id,reward_key,details) VALUES (?,?,?)",
                         (account_id, reward_key, details))
        for favor_id in favor_ids:
            db.execute("UPDATE lantern_favors SET redeemed_at=CURRENT_TIMESTAMP WHERE id=?", (favor_id,))
            db.execute("INSERT INTO lantern_favor_redemption_items(redemption_id,favor_id) VALUES (?,?)", (cur.lastrowid, favor_id))
            db.execute("INSERT INTO lantern_favor_events(favor_id,event_type,from_account_id,reward_key) VALUES (?,'redeem',?,?)",
                       (favor_id, account_id, reward_key))
        return cur.lastrowid

def history(database, favor_id):
    ensure_schema(database)
    with database.connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT event_type,from_account_id,to_account_id,message,reward_key,created_at FROM lantern_favor_events WHERE favor_id=? ORDER BY id", (favor_id,))]
