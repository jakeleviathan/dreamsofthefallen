from __future__ import annotations

import asyncio
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mud.mechanics import PROGRESSION_RULES


MUDVERSE_LISTING_ID = int(os.environ.get("MUDVERSE_LISTING_ID", "606"))
MUDVERSE_API_BASE = os.environ.get("MUDVERSE_API_BASE", "https://www.mudverse.com/api/v1").rstrip("/")
MUDVERSE_VOTE_URL = os.environ.get(
    "MUDVERSE_VOTE_URL",
    f"https://www.mudverse.com/vote/{MUDVERSE_LISTING_ID}",
)
VOTE_COOLDOWN_SECONDS = 24 * 60 * 60
CLAIM_EXPIRY_SECONDS = 2 * 60 * 60
STREAK_GRACE_SECONDS = 54 * 60 * 60
POLL_SECONDS = 60
VOTE_SPARK_REWARD = 6
VOTE_ECHO_REWARD = 1
VOTE_XP_FRACTION = 0.05
VOTE_XP_CAP = 250


class VoteServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EchoShopItem:
    key: str
    kind: str
    label: str
    cost: int
    description: str
    slot: str | None = None


@dataclass(frozen=True, slots=True)
class MilestoneReward:
    votes: int
    key: str
    kind: str
    label: str
    description: str
    slot: str | None = None


ECHO_SHOP: tuple[EchoShopItem, ...] = (
    EchoShopItem(
        "title_wayfarers_voice",
        "title",
        "Wayfarer's Voice",
        4,
        "Displayed as 'the Wayfarer's Voice'.",
    ),
    EchoShopItem(
        "title_dream_attendant",
        "title",
        "Dream Attendant",
        8,
        "Displayed as 'Dream Attendant'.",
    ),
    EchoShopItem(
        "title_veil_walker",
        "title",
        "Veil-Walker",
        14,
        "Displayed as 'the Veil-Walker'.",
    ),
    EchoShopItem(
        "title_lantern_bearer",
        "title",
        "Lantern-Bearer",
        22,
        "Displayed as 'Lantern-Bearer'.",
    ),
    EchoShopItem(
        "cosmetic_silver_echo_sigil",
        "cosmetic",
        "Silver Echo Sigil",
        6,
        "A fine silver echo-mark seems to hover near the wearer when they are examined.",
        "sigil",
    ),
    EchoShopItem(
        "cosmetic_briar_glass_sigil",
        "cosmetic",
        "Briar-Glass Sigil",
        12,
        "A small thorn-ring of green glass glints beside the wearer when they are examined.",
        "sigil",
    ),
    EchoShopItem(
        "cosmetic_lantern_hush_aura",
        "cosmetic",
        "Lantern Hush",
        9,
        "A low lantern-colored hush hangs around the wearer without shedding useful light.",
        "aura",
    ),
    EchoShopItem(
        "cosmetic_moonlit_vellum_aura",
        "cosmetic",
        "Moonlit Vellum",
        18,
        "A pale vellum-soft shimmer follows the wearer in still air.",
        "aura",
    ),
)

MILESTONE_REWARDS: tuple[MilestoneReward, ...] = (
    MilestoneReward(5, "title_the_heard", "title", "The Heard", "Displayed as 'the Heard'."),
    MilestoneReward(
        10,
        "cosmetic_dawnmark_sigil",
        "cosmetic",
        "Dawnmark Sigil",
        "A warm sun-stroke sigil appears near the wearer when examined.",
        "sigil",
    ),
    MilestoneReward(
        25,
        "title_voice_in_the_dark",
        "title",
        "Voice in the Dark",
        "Displayed as 'Voice in the Dark'.",
    ),
    MilestoneReward(
        50,
        "cosmetic_echo_glow_aura",
        "cosmetic",
        "Echo Glow",
        "A dim pearl glow gathers around the wearer like light remembered through fog.",
        "aura",
    ),
    MilestoneReward(
        100,
        "title_dream_bearer",
        "title",
        "Dream-Bearer",
        "Displayed as 'Dream-Bearer'.",
    ),
    MilestoneReward(
        250,
        "cosmetic_constellation_sigil",
        "cosmetic",
        "Astralis Constellation",
        "A tiny constellation of cold points hangs beside the wearer when examined.",
        "sigil",
    ),
    MilestoneReward(
        365,
        "title_year_and_a_day",
        "title",
        "A Year and a Day",
        "Displayed as 'of a Year and a Day'.",
    ),
    MilestoneReward(
        365,
        "cosmetic_yearlight_aura",
        "cosmetic",
        "Yearlight",
        "A slow ring of pale seasonal light turns around the wearer.",
        "aura",
    ),
    MilestoneReward(
        500,
        "cosmetic_fallen_stars_aura",
        "cosmetic",
        "Fallen Stars",
        "Sparse star-like sparks fade soundlessly around the wearer.",
        "aura",
    ),
    MilestoneReward(
        1000,
        "title_thousand_echoes",
        "title",
        "A Thousand Echoes",
        "Displayed as 'of a Thousand Echoes'.",
    ),
)

SHOP_BY_KEY = {item.key: item for item in ECHO_SHOP}
MILESTONE_BY_KEY = {item.key: item for item in MILESTONE_REWARDS}
ALL_UNLOCKS = {**SHOP_BY_KEY, **MILESTONE_BY_KEY}


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def vote_rewards_enabled() -> bool:
    return _bool_env("DOTF_VOTE_REWARDS_ENABLED", False)


def _api_key() -> str:
    return os.environ.get("MUDVERSE_API_KEY", "").strip()


def _month_key(epoch: int | None = None) -> str:
    dt = datetime.fromtimestamp(epoch or int(time.time()), tz=timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def ensure_vote_schema(database) -> None:
    with database.connect() as db:
        account_columns = {
            str(row["name"])
            for row in db.execute("PRAGMA table_info(accounts)").fetchall()
        }
        additions = (
            ("echoes_of_favour", "INTEGER NOT NULL DEFAULT 0"),
            ("vote_lifetime", "INTEGER NOT NULL DEFAULT 0"),
            ("vote_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("vote_best_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("vote_last_rewarded_at_epoch", "INTEGER"),
        )
        for name, definition in additions:
            if name not in account_columns:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {name} {definition}")

        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS mudverse_vote_sync_state (
                month_key TEXT PRIMARY KEY,
                high_watermark INTEGER NOT NULL DEFAULT 0,
                last_seen_count INTEGER NOT NULL DEFAULT 0,
                last_synced_at_epoch INTEGER,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS mudverse_vote_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_key TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                observed_at_epoch INTEGER NOT NULL,
                allocated_claim_id INTEGER,
                UNIQUE(month_key, ordinal)
            );

            CREATE TABLE IF NOT EXISTS mudverse_vote_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                month_key TEXT NOT NULL,
                baseline_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at_epoch INTEGER NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                allocated_event_id INTEGER,
                rewarded_at_epoch INTEGER,
                source TEXT NOT NULL DEFAULT 'mudverse',
                note TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (allocated_event_id) REFERENCES mudverse_vote_events(id) ON DELETE SET NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_vote_one_pending_per_account
            ON mudverse_vote_claims(account_id)
            WHERE status = 'pending';

            CREATE UNIQUE INDEX IF NOT EXISTS idx_vote_event_one_claim
            ON mudverse_vote_events(allocated_claim_id)
            WHERE allocated_claim_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS idx_vote_claim_status_time
            ON mudverse_vote_claims(status, started_at_epoch);

            CREATE TABLE IF NOT EXISTS echo_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                reason TEXT NOT NULL,
                reference_type TEXT,
                reference_id TEXT,
                created_at_epoch INTEGER NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_echo_ledger_account
            ON echo_ledger(account_id, id DESC);

            CREATE TABLE IF NOT EXISTS account_echo_unlocks (
                account_id INTEGER NOT NULL,
                unlock_key TEXT NOT NULL,
                unlock_type TEXT NOT NULL,
                source TEXT NOT NULL,
                unlocked_at_epoch INTEGER NOT NULL,
                PRIMARY KEY (account_id, unlock_key),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS account_vote_milestones (
                account_id INTEGER NOT NULL,
                milestone_votes INTEGER NOT NULL,
                granted_at_epoch INTEGER NOT NULL,
                PRIMARY KEY (account_id, milestone_votes),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_echo_profile (
                character_id INTEGER PRIMARY KEY,
                title_key TEXT,
                aura_key TEXT,
                sigil_key TEXT,
                updated_at_epoch INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS vote_admin_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_account_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_account_id INTEGER,
                details TEXT NOT NULL,
                created_at_epoch INTEGER NOT NULL,
                FOREIGN KEY (actor_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (target_account_id) REFERENCES accounts(id) ON DELETE SET NULL
            );
            """
        )


class MudVerseClient:
    def __init__(self, api_key: str | None = None, listing_id: int = MUDVERSE_LISTING_ID) -> None:
        self.api_key = (api_key if api_key is not None else _api_key()).strip()
        self.listing_id = int(listing_id)

    def _fetch_sync(self) -> tuple[int, int | None]:
        if not self.api_key:
            raise VoteServiceError("MUDVerse API key is not configured.")
        request = Request(
            f"{MUDVERSE_API_BASE}/games/{self.listing_id}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "DreamsOfTheFallen/1.0 vote-rewards",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise VoteServiceError(f"MUDVerse returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise VoteServiceError(f"MUDVerse could not be reached: {exc.reason}.") from exc
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise VoteServiceError("MUDVerse returned an unreadable API response.") from exc

        try:
            data = payload["data"]
            if int(data["id"]) != self.listing_id:
                raise VoteServiceError("MUDVerse returned the wrong listing.")
            votes = int(data["ranking"]["monthly_votes"])
            rank_raw = data["ranking"].get("rank")
            rank = None if rank_raw is None else int(rank_raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise VoteServiceError("MUDVerse response did not include monthly vote data.") from exc
        return max(0, votes), rank

    async def fetch(self) -> tuple[int, int | None]:
        return await asyncio.to_thread(self._fetch_sync)


def _expire_claims_tx(db, now: int) -> None:
    db.execute(
        """
        UPDATE mudverse_vote_claims
        SET status = 'expired'
        WHERE status = 'pending' AND expires_at_epoch <= ?
        """,
        (now,),
    )


def _ingest_observation(database, month_key: str, count: int, now: int) -> int:
    ensure_vote_schema(database)
    count = max(0, int(count))
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT high_watermark FROM mudverse_vote_sync_state WHERE month_key = ?",
            (month_key,),
        ).fetchone()
        created = 0
        if row is None:
            # Ordinarily the first observation of a calendar month is a baseline:
            # old votes must never become free reward events. The one exception is
            # a still-live claim armed before the UTC month rollover. In that narrow
            # case, seed at most one fresh-month event per waiting claim so a real
            # vote cast across midnight can still be matched instead of disappearing.
            waiting = db.execute(
                """
                SELECT COUNT(*) AS n
                FROM mudverse_vote_claims
                WHERE status = 'pending'
                  AND started_at_epoch <= ?
                  AND expires_at_epoch > ?
                  AND month_key != ?
                """,
                (now, now, month_key),
            ).fetchone()
            seed = min(count, int(waiting["n"])) if waiting is not None else 0
            for ordinal in range(1, seed + 1):
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO mudverse_vote_events
                        (month_key, ordinal, observed_at_epoch)
                    VALUES (?, ?, ?)
                    """,
                    (month_key, ordinal, now),
                )
                created += int(cursor.rowcount or 0)
            db.execute(
                """
                INSERT INTO mudverse_vote_sync_state
                    (month_key, high_watermark, last_seen_count, last_synced_at_epoch, last_error)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (month_key, count, count, now),
            )
            return created

        high = int(row["high_watermark"])
        if count > high:
            for ordinal in range(high + 1, count + 1):
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO mudverse_vote_events
                        (month_key, ordinal, observed_at_epoch)
                    VALUES (?, ?, ?)
                    """,
                    (month_key, ordinal, now),
                )
                created += int(cursor.rowcount or 0)
            high = count

        db.execute(
            """
            UPDATE mudverse_vote_sync_state
            SET high_watermark = ?, last_seen_count = ?, last_synced_at_epoch = ?, last_error = NULL
            WHERE month_key = ?
            """,
            (high, count, now, month_key),
        )
    return created


def _record_sync_error(database, month_key: str, message: str, now: int) -> None:
    ensure_vote_schema(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO mudverse_vote_sync_state
                (month_key, high_watermark, last_seen_count, last_synced_at_epoch, last_error)
            VALUES (?, 0, 0, ?, ?)
            ON CONFLICT(month_key) DO UPDATE SET
                last_synced_at_epoch = excluded.last_synced_at_epoch,
                last_error = excluded.last_error
            """,
            (month_key, now, message[:300]),
        )


async def sync_mudverse(database, client: MudVerseClient | None = None) -> tuple[int, int | None, int]:
    client = client or MudVerseClient()
    now = int(time.time())
    month = _month_key(now)
    try:
        count, rank = await client.fetch()
    except VoteServiceError as exc:
        _record_sync_error(database, month, str(exc), now)
        raise
    created = _ingest_observation(database, month, count, now)
    return count, rank, created


def _account_status(database, account_id: int) -> dict:
    ensure_vote_schema(database)
    with database.connect() as db:
        _expire_claims_tx(db, int(time.time()))
        row = db.execute(
            """
            SELECT echoes_of_favour, vote_lifetime, vote_streak, vote_best_streak,
                   vote_last_rewarded_at_epoch
            FROM accounts WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown account id {account_id}")
        pending = db.execute(
            """
            SELECT id, character_id, started_at_epoch, expires_at_epoch, baseline_count, month_key
            FROM mudverse_vote_claims
            WHERE account_id = ? AND status = 'pending'
            ORDER BY started_at_epoch ASC LIMIT 1
            """,
            (account_id,),
        ).fetchone()
    return {
        "echoes": int(row["echoes_of_favour"]),
        "lifetime": int(row["vote_lifetime"]),
        "streak": int(row["vote_streak"]),
        "best_streak": int(row["vote_best_streak"]),
        "last_rewarded": None if row["vote_last_rewarded_at_epoch"] is None else int(row["vote_last_rewarded_at_epoch"]),
        "pending": None if pending is None else dict(pending),
    }


def _next_milestone(lifetime: int) -> tuple[int, list[MilestoneReward]] | None:
    votes = sorted({item.votes for item in MILESTONE_REWARDS})
    for threshold in votes:
        if threshold > lifetime:
            return threshold, [item for item in MILESTONE_REWARDS if item.votes == threshold]
    return None


def _create_pending_claim(
    database,
    account_id: int,
    character_id: int,
    baseline_count: int,
    now: int | None = None,
) -> tuple[str, dict | None]:
    ensure_vote_schema(database)
    now = int(time.time()) if now is None else int(now)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _expire_claims_tx(db, now)
        account = db.execute(
            "SELECT vote_last_rewarded_at_epoch FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if account is None:
            return "missing_account", None
        last = account["vote_last_rewarded_at_epoch"]
        if last is not None and now - int(last) < VOTE_COOLDOWN_SECONDS:
            return "cooldown", {"remaining": VOTE_COOLDOWN_SECONDS - (now - int(last))}

        existing = db.execute(
            """
            SELECT id, character_id, started_at_epoch, expires_at_epoch, baseline_count, month_key
            FROM mudverse_vote_claims
            WHERE account_id = ? AND status = 'pending'
            ORDER BY started_at_epoch ASC LIMIT 1
            """,
            (account_id,),
        ).fetchone()
        if existing is not None:
            return "pending", dict(existing)

        cursor = db.execute(
            """
            INSERT INTO mudverse_vote_claims (
                account_id, character_id, month_key, baseline_count,
                status, started_at_epoch, expires_at_epoch
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                account_id,
                character_id,
                _month_key(now),
                max(0, int(baseline_count)),
                now,
                now + CLAIM_EXPIRY_SECONDS,
            ),
        )
        claim_id = int(cursor.lastrowid)
        row = db.execute(
            "SELECT * FROM mudverse_vote_claims WHERE id = ?",
            (claim_id,),
        ).fetchone()
    return "created", dict(row)


def _milestone_unlocks_tx(db, account_id: int, old_lifetime: int, new_lifetime: int, now: int) -> list[str]:
    granted: list[str] = []
    thresholds = sorted({item.votes for item in MILESTONE_REWARDS if old_lifetime < item.votes <= new_lifetime})
    for threshold in thresholds:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO account_vote_milestones
                (account_id, milestone_votes, granted_at_epoch)
            VALUES (?, ?, ?)
            """,
            (account_id, threshold, now),
        )
        if not cursor.rowcount:
            continue
        for reward in (item for item in MILESTONE_REWARDS if item.votes == threshold):
            db.execute(
                """
                INSERT OR IGNORE INTO account_echo_unlocks
                    (account_id, unlock_key, unlock_type, source, unlocked_at_epoch)
                VALUES (?, ?, ?, ?, ?)
                """,
                (account_id, reward.key, reward.kind, f"vote_milestone_{threshold}", now),
            )
            granted.append(reward.label)
    return granted


def _grant_vote_reward_tx(db, claim, now: int) -> dict:
    account_id = int(claim["account_id"])
    character_id = int(claim["character_id"])
    account = db.execute(
        """
        SELECT echoes_of_favour, vote_lifetime, vote_streak, vote_best_streak,
               vote_last_rewarded_at_epoch
        FROM accounts WHERE id = ?
        """,
        (account_id,),
    ).fetchone()
    character = db.execute(
        "SELECT level, experience FROM characters WHERE id = ? AND account_id = ?",
        (character_id, account_id),
    ).fetchone()
    if account is None or character is None:
        raise VoteServiceError("Vote reward target no longer exists.")

    level = max(1, int(character["level"]))
    xp_reward = min(
        VOTE_XP_CAP,
        max(1, int(math.ceil(PROGRESSION_RULES.xp_to_next_level(level) * VOTE_XP_FRACTION))),
    )
    new_experience = int(character["experience"]) + xp_reward
    new_level = PROGRESSION_RULES.level_for_experience(new_experience)

    old_lifetime = int(account["vote_lifetime"])
    new_lifetime = old_lifetime + 1
    previous_reward = account["vote_last_rewarded_at_epoch"]
    if previous_reward is not None and now - int(previous_reward) <= STREAK_GRACE_SECONDS:
        streak = int(account["vote_streak"]) + 1
    else:
        streak = 1
    best = max(int(account["vote_best_streak"]), streak)
    new_echo_balance = int(account["echoes_of_favour"]) + VOTE_ECHO_REWARD

    db.execute(
        """
        UPDATE accounts
        SET echoes_of_favour = ?, vote_lifetime = ?, vote_streak = ?,
            vote_best_streak = ?, vote_last_rewarded_at_epoch = ?
        WHERE id = ?
        """,
        (new_echo_balance, new_lifetime, streak, best, now, account_id),
    )
    db.execute(
        """
        UPDATE characters
        SET sols = sols + ?, experience = ?, level = ?
        WHERE id = ?
        """,
        (VOTE_SPARK_REWARD, new_experience, new_level, character_id),
    )
    db.execute(
        """
        INSERT INTO echo_ledger (
            account_id, delta, balance_after, reason,
            reference_type, reference_id, created_at_epoch
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            VOTE_ECHO_REWARD,
            new_echo_balance,
            "Daily MUDVerse vote reward",
            "vote_claim",
            str(claim["id"]),
            now,
        ),
    )
    milestones = _milestone_unlocks_tx(db, account_id, old_lifetime, new_lifetime, now)
    return {
        "echoes": VOTE_ECHO_REWARD,
        "sparks": VOTE_SPARK_REWARD,
        "xp": xp_reward,
        "level": new_level,
        "lifetime": new_lifetime,
        "streak": streak,
        "best_streak": best,
        "milestones": milestones,
    }


def allocate_pending_claims(database, now: int | None = None) -> list[dict]:
    ensure_vote_schema(database)
    now = int(time.time()) if now is None else int(now)
    awarded: list[dict] = []
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _expire_claims_tx(db, now)
        claims = db.execute(
            """
            SELECT * FROM mudverse_vote_claims
            WHERE status = 'pending'
            ORDER BY started_at_epoch ASC, id ASC
            """
        ).fetchall()

        for claim in claims:
            event = db.execute(
                """
                SELECT id, month_key, ordinal, observed_at_epoch
                FROM mudverse_vote_events
                WHERE allocated_claim_id IS NULL
                  AND observed_at_epoch >= ?
                  AND (
                        month_key != ?
                        OR ordinal > ?
                  )
                ORDER BY observed_at_epoch ASC, id ASC
                LIMIT 1
                """,
                (
                    int(claim["started_at_epoch"]),
                    str(claim["month_key"]),
                    int(claim["baseline_count"]),
                ),
            ).fetchone()
            if event is None:
                continue

            cursor = db.execute(
                """
                UPDATE mudverse_vote_events
                SET allocated_claim_id = ?
                WHERE id = ? AND allocated_claim_id IS NULL
                """,
                (int(claim["id"]), int(event["id"])),
            )
            if cursor.rowcount != 1:
                continue

            reward = _grant_vote_reward_tx(db, claim, now)
            db.execute(
                """
                UPDATE mudverse_vote_claims
                SET status = 'allocated', allocated_event_id = ?, rewarded_at_epoch = ?
                WHERE id = ? AND status = 'pending'
                """,
                (int(event["id"]), now, int(claim["id"])),
            )
            reward.update(
                {
                    "claim_id": int(claim["id"]),
                    "account_id": int(claim["account_id"]),
                    "character_id": int(claim["character_id"]),
                    "event_id": int(event["id"]),
                }
            )
            awarded.append(reward)
    return awarded


def _grant_manual_vote(database, account_id: int, character_id: int, actor_id: int, reason: str, now: int | None = None) -> dict:
    ensure_vote_schema(database)
    now = int(time.time()) if now is None else int(now)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            """
            INSERT INTO mudverse_vote_claims (
                account_id, character_id, month_key, baseline_count, status,
                started_at_epoch, expires_at_epoch, source, note
            ) VALUES (?, ?, ?, 0, 'manual', ?, ?, 'manual', ?)
            """,
            (account_id, character_id, _month_key(now), now, now, reason[:300]),
        )
        claim_id = int(cursor.lastrowid)
        claim = db.execute("SELECT * FROM mudverse_vote_claims WHERE id = ?", (claim_id,)).fetchone()
        reward = _grant_vote_reward_tx(db, claim, now)
        db.execute(
            "UPDATE mudverse_vote_claims SET status = 'allocated', rewarded_at_epoch = ? WHERE id = ?",
            (now, claim_id),
        )
        db.execute(
            """
            INSERT INTO vote_admin_audit
                (actor_account_id, action, target_account_id, details, created_at_epoch)
            VALUES (?, 'manual_vote_grant', ?, ?, ?)
            """,
            (actor_id, account_id, reason[:500], now),
        )
    reward["claim_id"] = claim_id
    return reward


def _grant_manual_echoes(database, account_id: int, actor_id: int, amount: int, reason: str, now: int | None = None) -> int:
    ensure_vote_schema(database)
    now = int(time.time()) if now is None else int(now)
    amount = int(amount)
    if amount == 0:
        raise ValueError("Echo grant cannot be zero.")
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT echoes_of_favour FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise KeyError(account_id)
        balance = max(0, int(row["echoes_of_favour"]) + amount)
        actual_delta = balance - int(row["echoes_of_favour"])
        db.execute("UPDATE accounts SET echoes_of_favour = ? WHERE id = ?", (balance, account_id))
        db.execute(
            """
            INSERT INTO echo_ledger (
                account_id, delta, balance_after, reason,
                reference_type, reference_id, created_at_epoch
            ) VALUES (?, ?, ?, ?, 'admin', ?, ?)
            """,
            (account_id, actual_delta, balance, reason[:300], str(actor_id), now),
        )
        db.execute(
            """
            INSERT INTO vote_admin_audit
                (actor_account_id, action, target_account_id, details, created_at_epoch)
            VALUES (?, 'manual_echo_grant', ?, ?, ?)
            """,
            (actor_id, account_id, f"{actual_delta:+d} echoes: {reason[:420]}", now),
        )
    return balance


def _unlocks(database, account_id: int, kind: str | None = None) -> list[dict]:
    ensure_vote_schema(database)
    sql = "SELECT unlock_key, unlock_type, source, unlocked_at_epoch FROM account_echo_unlocks WHERE account_id = ?"
    args: list[object] = [account_id]
    if kind:
        sql += " AND unlock_type = ?"
        args.append(kind)
    sql += " ORDER BY unlocked_at_epoch, unlock_key"
    with database.connect() as db:
        rows = db.execute(sql, tuple(args)).fetchall()
    return [dict(row) for row in rows]


def _profile(database, character_id: int) -> dict:
    ensure_vote_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT title_key, aura_key, sigil_key FROM character_echo_profile WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    if row is None:
        return {"title_key": None, "aura_key": None, "sigil_key": None}
    return dict(row)


def _resolve_unlock(database, account_id: int, target: str, kind: str) -> tuple[str | None, str | None]:
    wanted = _normalize(target)
    owned = _unlocks(database, account_id, kind)
    exact: list[str] = []
    partial: list[str] = []
    for row in owned:
        key = str(row["unlock_key"])
        item = ALL_UNLOCKS.get(key)
        if item is None:
            continue
        names = {_normalize(key), _normalize(item.label)}
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)
    matches = list(dict.fromkeys(exact or partial))
    if not matches:
        return None, f"You have not unlocked a {kind} by that name."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(ALL_UNLOCKS[key].label for key in matches) + "."
    return matches[0], None


def _set_profile_field(database, character_id: int, field: str, key: str | None, now: int | None = None) -> None:
    ensure_vote_schema(database)
    if field not in {"title_key", "aura_key", "sigil_key"}:
        raise ValueError(field)
    now = int(time.time()) if now is None else int(now)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_echo_profile
                (character_id, title_key, aura_key, sigil_key, updated_at_epoch)
            VALUES (?, NULL, NULL, NULL, ?)
            ON CONFLICT(character_id) DO NOTHING
            """,
            (character_id, now),
        )
        db.execute(
            f"UPDATE character_echo_profile SET {field} = ?, updated_at_epoch = ? WHERE character_id = ?",
            (key, now, character_id),
        )


def buy_echo_item(database, account_id: int, item_key: str, now: int | None = None) -> tuple[str, int]:
    ensure_vote_schema(database)
    item = SHOP_BY_KEY.get(item_key)
    if item is None:
        return "unknown", _account_status(database, account_id)["echoes"]
    now = int(time.time()) if now is None else int(now)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        owned = db.execute(
            "SELECT 1 FROM account_echo_unlocks WHERE account_id = ? AND unlock_key = ?",
            (account_id, item.key),
        ).fetchone()
        row = db.execute("SELECT echoes_of_favour FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise KeyError(account_id)
        balance = int(row["echoes_of_favour"])
        if owned is not None:
            return "owned", balance
        if balance < item.cost:
            return "insufficient", balance
        balance -= item.cost
        db.execute("UPDATE accounts SET echoes_of_favour = ? WHERE id = ?", (balance, account_id))
        db.execute(
            """
            INSERT INTO account_echo_unlocks
                (account_id, unlock_key, unlock_type, source, unlocked_at_epoch)
            VALUES (?, ?, ?, 'echo_shop', ?)
            """,
            (account_id, item.key, item.kind, now),
        )
        db.execute(
            """
            INSERT INTO echo_ledger (
                account_id, delta, balance_after, reason,
                reference_type, reference_id, created_at_epoch
            ) VALUES (?, ?, ?, ?, 'echo_shop', ?, ?)
            """,
            (account_id, -item.cost, balance, f"Purchased {item.label}", item.key, now),
        )
    return "purchased", balance


def _title_text(item) -> str:
    key = item.key
    if key == "title_the_heard":
        return "the Heard"
    if key == "title_voice_in_the_dark":
        return "Voice in the Dark"
    if key == "title_dream_bearer":
        return "Dream-Bearer"
    if key == "title_year_and_a_day":
        return "of a Year and a Day"
    if key == "title_thousand_echoes":
        return "of a Thousand Echoes"
    if key == "title_wayfarers_voice":
        return "the Wayfarer's Voice"
    if key == "title_dream_attendant":
        return "Dream Attendant"
    if key == "title_veil_walker":
        return "the Veil-Walker"
    if key == "title_lantern_bearer":
        return "Lantern-Bearer"
    return item.label


def decorated_character_name(database, character) -> str:
    profile = _profile(database, int(character.id))
    title_key = profile.get("title_key")
    item = ALL_UNLOCKS.get(str(title_key)) if title_key else None
    if item is None:
        return str(character.name)
    return f"{character.name}, {_title_text(item)}"


def _resolve_shop_target(target: str) -> tuple[str | None, str | None]:
    wanted = _normalize(target)
    exact: list[str] = []
    partial: list[str] = []
    for item in ECHO_SHOP:
        names = {_normalize(item.key), _normalize(item.label)}
        if wanted in names:
            exact.append(item.key)
        elif any(wanted in name for name in names):
            partial.append(item.key)
    matches = list(dict.fromkeys(exact or partial))
    if not matches:
        return None, "No Echo Shop offering matches that name."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(SHOP_BY_KEY[key].label for key in matches) + "."
    return matches[0], None


async def _show_vote(session, arm: bool = True) -> None:
    account = session.account
    character = session.character
    if account is None or character is None:
        return
    ensure_vote_schema(session.database)
    now = int(time.time())
    status = _account_status(session.database, account.id)

    await session.send(
        "\r\n--- Support Dreams of the Fallen ---\r\n"
        f"MUDVerse vote page: {MUDVERSE_VOTE_URL}\r\n"
        "MUDVerse permits one vote across the site during each rolling 24-hour period.\r\n"
        "Rewards are account-wide for tracking and Echoes; Sparks and XP go to the character that arms the claim.\r\n"
    )
    await session.send(
        f"Lifetime rewarded votes: {status['lifetime']} | Current streak: {status['streak']} "
        f"| Best streak: {status['best_streak']} | Echoes of Favour: {status['echoes']}\r\n"
    )
    milestone = _next_milestone(status["lifetime"])
    if milestone is not None:
        threshold, rewards = milestone
        await session.send(
            f"Next milestone: {threshold} votes - " + ", ".join(item.label for item in rewards) + ".\r\n"
        )

    if not vote_rewards_enabled():
        await session.send(
            "Vote rewards are currently disabled by the server operator. You may still use the voting link normally.\r\n"
        )
        return
    if not _api_key():
        await session.send(
            "Vote rewards are enabled, but the MUDVerse API key is not configured. Staff must finish server setup before claims can be armed.\r\n"
        )
        return

    last = status["last_rewarded"]
    if last is not None and now - last < VOTE_COOLDOWN_SECONDS:
        remaining = VOTE_COOLDOWN_SECONDS - (now - last)
        await session.send(f"Your account's next reward is available in {_format_duration(remaining)}.\r\n")
        return

    pending = status["pending"]
    if pending is not None:
        await session.send(
            f"A vote claim is already armed for this account for another {_format_duration(int(pending['expires_at_epoch']) - now)}. "
            "Vote on MUDVerse, then type VOTE CLAIM. The background checker also watches pending claims.\r\n"
        )
        return

    if not arm:
        await session.send("Type VOTE to arm today's claim before voting.\r\n")
        return

    try:
        count, rank, _ = await sync_mudverse(session.database)
        allocate_pending_claims(session.database)
    except VoteServiceError as exc:
        await session.send(
            f"The MUDVerse count could not be checked right now: {exc} "
            "No claim was armed, so try VOTE again before voting.\r\n"
        )
        return

    state, claim = _create_pending_claim(
        session.database,
        account.id,
        character.id,
        count,
        now=int(time.time()),
    )
    if state == "created":
        rank_text = f" and rank #{rank}" if rank is not None else ""
        await session.send(
            f"Claim armed at {count} votes this month{rank_text}. "
            "Cast your vote at the link above, then type VOTE CLAIM. This claim expires in 2 hours.\r\n"
        )
    elif state == "cooldown" and claim:
        await session.send(f"Your next reward is available in {_format_duration(int(claim['remaining']))}.\r\n")
    elif state == "pending":
        await session.send("A claim is already armed. Vote, then type VOTE CLAIM.\r\n")


async def _claim_vote(session) -> None:
    account = session.account
    if account is None or session.character is None:
        return
    if not vote_rewards_enabled():
        await session.send("Vote rewards are currently disabled.\r\n")
        return
    if not _api_key():
        await session.send("MUDVerse API access is not configured on the server yet.\r\n")
        return

    before = _account_status(session.database, account.id)
    if before["pending"] is None:
        last = before["last_rewarded"]
        if last is not None and int(time.time()) - last < VOTE_COOLDOWN_SECONDS:
            await session.send(
                f"Your most recent vote reward is already credited. Next reward in "
                f"{_format_duration(VOTE_COOLDOWN_SECONDS - (int(time.time()) - last))}.\r\n"
            )
        else:
            await session.send("No vote claim is armed. Type VOTE before you cast today's vote.\r\n")
        return

    try:
        count, rank, created = await sync_mudverse(session.database)
    except VoteServiceError as exc:
        await session.send(f"MUDVerse could not be checked right now: {exc}\r\n")
        return

    awards = allocate_pending_claims(session.database)
    after = _account_status(session.database, account.id)
    mine = next((award for award in awards if award["account_id"] == account.id), None)
    if mine is not None:
        await session.send(
            "\r\nVote confirmed. Thank you for supporting Dreams of the Fallen.\r\n"
            f"Reward: +{mine['echoes']} Echo of Favour, +{mine['sparks']} Sparks, +{mine['xp']} XP.\r\n"
            f"Lifetime rewarded votes: {mine['lifetime']} | Streak: {mine['streak']}.\r\n"
        )
        if mine["milestones"]:
            await session.send("Milestone unlocked: " + ", ".join(mine["milestones"]) + ".\r\n")
        return

    if after["pending"] is None and after["last_rewarded"] != before["last_rewarded"]:
        await session.send("Your vote reward was already matched and credited by the background checker.\r\n")
        return

    rank_text = f", rank #{rank}" if rank is not None else ""
    await session.send(
        f"MUDVerse currently shows {count} votes this month{rank_text}. "
        f"No unallocated vote increase has been matched to your claim yet"
        + ("." if created == 0 else "; another pending claim was ahead of yours.")
        + "\r\nTry VOTE CLAIM again shortly. Claims are matched FIFO because MUDVerse exposes an aggregate count, not voter identities.\r\n"
    )


async def _show_echoes(session) -> None:
    if session.account is None or session.character is None:
        return
    status = _account_status(session.database, session.account.id)
    profile = _profile(session.database, session.character.id)
    title = ALL_UNLOCKS.get(profile.get("title_key")) if profile.get("title_key") else None
    aura = ALL_UNLOCKS.get(profile.get("aura_key")) if profile.get("aura_key") else None
    sigil = ALL_UNLOCKS.get(profile.get("sigil_key")) if profile.get("sigil_key") else None
    await session.send(
        "\r\n--- Echoes of Favour ---\r\n"
        f"Balance: {status['echoes']}\r\n"
        "Echoes are account-wide and buy presentation only. They never change combat stats, equipment, loot odds, or crafting power.\r\n"
        f"Active title: {title.label if title else 'none'}\r\n"
        f"Active aura: {aura.label if aura else 'none'}\r\n"
        f"Active sigil: {sigil.label if sigil else 'none'}\r\n"
        "Commands: ECHOES SHOP | ECHOES BUY <name> | TITLES | TITLE SET <name> | TITLE CLEAR | "
        "COSMETICS | COSMETIC SET <name> | COSMETIC CLEAR AURA|SIGIL\r\n"
    )


async def _show_echo_shop(session) -> None:
    if session.account is None:
        return
    status = _account_status(session.database, session.account.id)
    owned = {row["unlock_key"] for row in _unlocks(session.database, session.account.id)}
    await session.send(f"\r\n--- Echo Shop - Balance {status['echoes']} ---\r\n")
    for item in ECHO_SHOP:
        marker = " [OWNED]" if item.key in owned else ""
        kind = item.kind.upper() if item.slot is None else f"{item.slot.upper()} COSMETIC"
        await session.send(f"{item.label} - {item.cost} Echoes [{kind}]{marker}\r\n  {item.description}\r\n")
    await session.send("Use ECHOES BUY <name>. Purchases unlock account-wide.\r\n")


async def _buy_echo(session, target: str) -> None:
    if session.account is None:
        return
    key, error = _resolve_shop_target(target)
    if key is None:
        await session.send((error or "Unknown offering.") + "\r\n")
        return
    item = SHOP_BY_KEY[key]
    state, balance = buy_echo_item(session.database, session.account.id, key)
    if state == "purchased":
        await session.send(f"Unlocked {item.label} account-wide for {item.cost} Echoes. Balance: {balance}.\r\n")
    elif state == "owned":
        await session.send(f"{item.label} is already unlocked on this account.\r\n")
    elif state == "insufficient":
        await session.send(f"{item.label} costs {item.cost} Echoes. Your balance is {balance}.\r\n")


async def _show_titles(session) -> None:
    if session.account is None or session.character is None:
        return
    owned = _unlocks(session.database, session.account.id, "title")
    profile = _profile(session.database, session.character.id)
    await session.send("\r\n--- Titles ---\r\n")
    if not owned:
        await session.send("No titles unlocked yet. Vote milestones and the Echo Shop can unlock them.\r\n")
        return
    for row in owned:
        item = ALL_UNLOCKS.get(str(row["unlock_key"]))
        if item is None:
            continue
        marker = " [ACTIVE]" if profile.get("title_key") == item.key else ""
        await session.send(f"{item.label}{marker} - {item.description}\r\n")
    await session.send("Use TITLE SET <name> or TITLE CLEAR.\r\n")


async def _set_title(session, target: str | None) -> None:
    if session.account is None or session.character is None:
        return
    if target is None:
        _set_profile_field(session.database, session.character.id, "title_key", None)
        await session.send("Your displayed title has been cleared.\r\n")
        return
    key, error = _resolve_unlock(session.database, session.account.id, target, "title")
    if key is None:
        await session.send((error or "Unknown title.") + "\r\n")
        return
    _set_profile_field(session.database, session.character.id, "title_key", key)
    await session.send(f"Title set: {ALL_UNLOCKS[key].label}.\r\n")


async def _show_cosmetics(session) -> None:
    if session.account is None or session.character is None:
        return
    owned = _unlocks(session.database, session.account.id, "cosmetic")
    profile = _profile(session.database, session.character.id)
    await session.send("\r\n--- Echo Cosmetics ---\r\n")
    if not owned:
        await session.send("No Echo cosmetics unlocked yet. Vote milestones and the Echo Shop can unlock them.\r\n")
        return
    for row in owned:
        item = ALL_UNLOCKS.get(str(row["unlock_key"]))
        if item is None:
            continue
        marker = " [ACTIVE]" if profile.get(f"{item.slot}_key") == item.key else ""
        await session.send(f"{item.label} [{str(item.slot).upper()}]{marker}\r\n  {item.description}\r\n")
    await session.send("Use COSMETIC SET <name> or COSMETIC CLEAR AURA|SIGIL.\r\n")


async def _set_cosmetic(session, target: str) -> None:
    if session.account is None or session.character is None:
        return
    key, error = _resolve_unlock(session.database, session.account.id, target, "cosmetic")
    if key is None:
        await session.send((error or "Unknown cosmetic.") + "\r\n")
        return
    item = ALL_UNLOCKS[key]
    if item.slot not in {"aura", "sigil"}:
        await session.send("That cosmetic does not have a valid presentation slot.\r\n")
        return
    _set_profile_field(session.database, session.character.id, f"{item.slot}_key", key)
    await session.send(f"{item.slot.title()} cosmetic set: {item.label}.\r\n")


async def _clear_cosmetic(session, slot: str) -> None:
    if session.character is None:
        return
    slot = _normalize(slot)
    if slot not in {"aura", "sigil"}:
        await session.send("Use COSMETIC CLEAR AURA or COSMETIC CLEAR SIGIL.\r\n")
        return
    _set_profile_field(session.database, session.character.id, f"{slot}_key", None)
    await session.send(f"Your {slot} cosmetic has been cleared.\r\n")


def _account_by_name(database, name: str):
    return database.get_account_by_name(name)


def _character_by_name(database, name: str):
    return database.get_character_by_name(name)


def _staff_role(session) -> str:
    try:
        from mud.staff_control import _role_for
        return _role_for(session)
    except Exception:
        return "player"


def _staff_at_least(session, minimum: str) -> bool:
    order = {"player": 0, "helper": 1, "gm": 2, "builder": 3, "admin": 4, "owner": 5}
    return order.get(_staff_role(session), 0) >= order[minimum]


def _audit_admin(database, actor_id: int, action: str, target_account_id: int | None, details: str) -> None:
    ensure_vote_schema(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO vote_admin_audit
                (actor_account_id, action, target_account_id, details, created_at_epoch)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor_id, action, target_account_id, details[:500], int(time.time())),
        )


async def _vote_admin(session, stripped: str) -> None:
    if session.account is None:
        return
    if not _staff_at_least(session, "gm"):
        await session.send("That command is restricted to staff.\r\n")
        return
    if not bool(getattr(session, "_staff_mode", False)):
        await session.send("Use STAFF ON before using vote administration commands.\r\n")
        return
    ensure_vote_schema(session.database)
    parts = stripped.split()
    sub = parts[2].lower() if len(parts) >= 3 else "status"

    if sub == "status":
        month = _month_key()
        with session.database.connect() as db:
            sync = db.execute("SELECT * FROM mudverse_vote_sync_state WHERE month_key = ?", (month,)).fetchone()
            pending = db.execute("SELECT COUNT(*) AS n FROM mudverse_vote_claims WHERE status = 'pending'").fetchone()
            events = db.execute("SELECT COUNT(*) AS n FROM mudverse_vote_events WHERE month_key = ?", (month,)).fetchone()
            free = db.execute(
                "SELECT COUNT(*) AS n FROM mudverse_vote_events WHERE month_key = ? AND allocated_claim_id IS NULL",
                (month,),
            ).fetchone()
        await session.send(
            "\r\n--- Vote Reward Status ---\r\n"
            f"Feature flag: {'ON' if vote_rewards_enabled() else 'OFF'} | API key: {'configured' if _api_key() else 'missing'}\r\n"
            f"Listing: {MUDVERSE_LISTING_ID} | Pending claims: {int(pending['n'])}\r\n"
            f"Current-month observed events: {int(events['n'])} | Unallocated: {int(free['n'])}\r\n"
        )
        if sync:
            await session.send(
                f"MUDVerse last seen: {int(sync['last_seen_count'])} | High watermark: {int(sync['high_watermark'])} "
                f"| Last error: {sync['last_error'] or 'none'}\r\n"
            )
        return

    if sub == "pending":
        with session.database.connect() as db:
            rows = db.execute(
                """
                SELECT c.id, a.name AS account_name, ch.name AS character_name,
                       c.started_at_epoch, c.expires_at_epoch, c.baseline_count
                FROM mudverse_vote_claims c
                JOIN accounts a ON a.id = c.account_id
                JOIN characters ch ON ch.id = c.character_id
                WHERE c.status = 'pending'
                ORDER BY c.started_at_epoch ASC
                LIMIT 50
                """
            ).fetchall()
        await session.send("\r\n--- Pending Vote Claims ---\r\n")
        if not rows:
            await session.send("None.\r\n")
        for row in rows:
            await session.send(
                f"#{row['id']} {row['account_name']} -> {row['character_name']} "
                f"baseline {row['baseline_count']} expires in {_format_duration(int(row['expires_at_epoch']) - int(time.time()))}\r\n"
            )
        return

    if sub == "history":
        limit = 20
        if len(parts) >= 4 and parts[3].isdigit():
            limit = min(100, max(1, int(parts[3])))
        with session.database.connect() as db:
            rows = db.execute(
                """
                SELECT c.id, c.status, c.source, c.rewarded_at_epoch, c.note,
                       a.name AS account_name, ch.name AS character_name
                FROM mudverse_vote_claims c
                JOIN accounts a ON a.id = c.account_id
                JOIN characters ch ON ch.id = c.character_id
                ORDER BY c.id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        await session.send("\r\n--- Vote Reward History ---\r\n")
        for row in rows:
            await session.send(
                f"#{row['id']} {row['account_name']} / {row['character_name']} "
                f"[{str(row['status']).upper()}] source={row['source']}"
                + (f" note={row['note']}" if row["note"] else "")
                + "\r\n"
            )
        return

    if sub == "account":
        if len(parts) < 4:
            await session.send("Use VOTE ADMIN ACCOUNT <account>.\r\n")
            return
        target = _account_by_name(session.database, parts[3])
        if target is None:
            await session.send("No account by that name exists.\r\n")
            return
        status = _account_status(session.database, target.id)
        await session.send(
            f"\r\n--- Vote Account: {target.name} ---\r\n"
            f"Echoes {status['echoes']} | Lifetime {status['lifetime']} | Streak {status['streak']} | Best {status['best_streak']}\r\n"
            f"Pending: {'yes' if status['pending'] else 'no'}\r\n"
        )
        return

    if sub == "sync":
        if not _api_key():
            await session.send("MUDVERSE_API_KEY is not configured.\r\n")
            return
        try:
            count, rank, created = await sync_mudverse(session.database)
            awards = allocate_pending_claims(session.database)
        except VoteServiceError as exc:
            await session.send(f"Sync failed: {exc}\r\n")
            return
        _audit_admin(session.database, session.account.id, "manual_sync", None, f"count={count} created={created} awards={len(awards)}")
        await session.send(
            f"Sync complete: {count} monthly votes, rank {rank if rank is not None else 'unranked'}, "
            f"{created} new event(s), {len(awards)} reward(s) allocated.\r\n"
        )
        return

    if sub == "grant":
        if not _staff_at_least(session, "admin"):
            await session.send("Manual reward grants require ADMIN or OWNER.\r\n")
            return
        if len(parts) < 6:
            await session.send(
                "Use VOTE ADMIN GRANT <account> <character> <reason...> or "
                "VOTE ADMIN GRANT ECHOES <account> <amount> <reason...>.\r\n"
            )
            return
        if parts[3].lower() == "echoes":
            if len(parts) < 7:
                await session.send("Use VOTE ADMIN GRANT ECHOES <account> <amount> <reason...>.\r\n")
                return
            target = _account_by_name(session.database, parts[4])
            if target is None:
                await session.send("No account by that name exists.\r\n")
                return
            try:
                amount = int(parts[5])
            except ValueError:
                await session.send("Echo amount must be an integer.\r\n")
                return
            reason = " ".join(parts[6:]).strip()
            if not reason:
                await session.send("A reason is required for every manual grant.\r\n")
                return
            balance = _grant_manual_echoes(session.database, target.id, session.account.id, amount, reason)
            await session.send(f"{target.name} now has {balance} Echoes of Favour. Audit reason recorded.\r\n")
            return

        target = _account_by_name(session.database, parts[3])
        character = _character_by_name(session.database, parts[4])
        reason = " ".join(parts[5:]).strip()
        if target is None or character is None or int(character.account_id) != int(target.id):
            await session.send("That account/character pair could not be resolved.\r\n")
            return
        if not reason:
            await session.send("A reason is required for every manual grant.\r\n")
            return
        reward = _grant_manual_vote(
            session.database,
            target.id,
            character.id,
            session.account.id,
            reason,
        )
        await session.send(
            f"Manual vote reward granted to {target.name}/{character.name}: "
            f"+{reward['echoes']} Echo, +{reward['sparks']} Sparks, +{reward['xp']} XP. Audit reason recorded.\r\n"
        )
        return

    await session.send(
        "VOTE ADMIN STATUS | PENDING | HISTORY [n] | ACCOUNT <account> | SYNC | "
        "GRANT <account> <character> <reason...> | GRANT ECHOES <account> <amount> <reason...>\r\n"
    )


def _patch_player_appearance() -> None:
    try:
        import mud.room_prompt_experience as room_prompt
    except Exception:
        return
    if getattr(room_prompt, "_echo_presentation_patched", False):
        return
    previous = room_prompt._show_player_appearance

    async def show_player_appearance(session, player) -> None:
        await previous(session, player)
        profile = _profile(session.database, int(player.id))
        title_key = profile.get("title_key")
        aura_key = profile.get("aura_key")
        sigil_key = profile.get("sigil_key")
        title = ALL_UNLOCKS.get(str(title_key)) if title_key else None
        aura = ALL_UNLOCKS.get(str(aura_key)) if aura_key else None
        sigil = ALL_UNLOCKS.get(str(sigil_key)) if sigil_key else None
        if title:
            await session.send(f"Known as: {decorated_character_name(session.database, player)}\r\n")
        if aura:
            await session.send(f"Aura: {aura.description}\r\n")
        if sigil:
            await session.send(f"Sigil: {sigil.description}\r\n")

    room_prompt._show_player_appearance = show_player_appearance
    room_prompt._echo_presentation_patched = True


def _patch_who() -> None:
    try:
        import mud.social_experience as social
    except Exception:
        return
    if getattr(social, "_echo_titles_patched", False):
        return

    async def who(session) -> None:
        rows = []
        for other in tuple(social._ACTIVE_SESSIONS):
            character = social._character(other)
            if character is None:
                continue
            race = social.RACES_BY_KEY.get(character.race or "")
            klass = social.CLASSES_BY_KEY.get(character.character_class or "")
            rows.append(
                (
                    decorated_character_name(session.database, character),
                    int(character.level),
                    race.name if race else (character.race or "Unknown"),
                    klass.name if klass else (character.character_class or "Unknown").title(),
                    social._visible_staff_role(other),
                )
            )
        rows.sort(key=lambda value: value[0].lower())
        await session.send(f"\r\n--- Who Is In Astralis ({len(rows)}) ---\r\n")
        for name, level, race, klass, staff_role in rows:
            tag = f"[{staff_role.upper()}] " if staff_role else ""
            await session.send(f"{tag}{name} - Level {level} {race} {klass}\r\n")
        if not rows:
            await session.send("No characters are currently visible as connected.\r\n")

    social._who = who
    social._echo_titles_patched = True


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


async def _poll_loop(database) -> None:
    ensure_vote_schema(database)
    client = MudVerseClient()
    while True:
        try:
            if vote_rewards_enabled() and client.api_key:
                with database.connect() as db:
                    _expire_claims_tx(db, int(time.time()))
                    row = db.execute(
                        "SELECT 1 FROM mudverse_vote_claims WHERE status = 'pending' LIMIT 1"
                    ).fetchone()
                if row is not None:
                    try:
                        await sync_mudverse(database, client)
                        allocate_pending_claims(database)
                    except VoteServiceError:
                        pass
            await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(POLL_SECONDS)


def install_vote_rewards_runtime(player_session_class, mud_server_class, database_class) -> None:
    if getattr(player_session_class, "_vote_rewards_runtime_installed", False):
        return

    previous_initialize = database_class.initialize

    def initialize(self) -> None:
        previous_initialize(self)
        ensure_vote_schema(self)

    database_class.initialize = initialize

    _patch_player_appearance()
    _patch_who()

    previous_enter = player_session_class.enter_character

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.account is not None:
            ensure_vote_schema(self.database)

    player_session_class.enter_character = enter_character

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None or getattr(self, "account", None) is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"vote", "votes", "vote status"}:
            await _show_vote(self, arm=True)
            return
        if normalized in {"vote claim", "claim vote"}:
            await _claim_vote(self)
            return
        if normalized.startswith("vote admin"):
            await _vote_admin(self, stripped)
            return
        if normalized in {"echo", "echoes", "echoes of favour", "echoes of favor"}:
            await _show_echoes(self)
            return
        if normalized in {"echo shop", "echoes shop", "favour shop", "favor shop"}:
            await _show_echo_shop(self)
            return
        if normalized.startswith("echoes buy "):
            await _buy_echo(self, stripped[len("echoes buy "):])
            return
        if normalized.startswith("echo buy "):
            await _buy_echo(self, stripped[len("echo buy "):])
            return
        if normalized in {"title", "titles"}:
            await _show_titles(self)
            return
        if normalized == "title clear":
            await _set_title(self, None)
            return
        if normalized.startswith("title set "):
            await _set_title(self, stripped[len("title set "):])
            return
        if normalized in {"cosmetic", "cosmetics", "echo cosmetics"}:
            await _show_cosmetics(self)
            return
        if normalized.startswith("cosmetic set "):
            await _set_cosmetic(self, stripped[len("cosmetic set "):])
            return
        if normalized.startswith("cosmetic clear "):
            await _clear_cosmetic(self, stripped[len("cosmetic clear "):])
            return

        await _delegate_command(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._vote_rewards_runtime_installed = True

    previous_run = mud_server_class.run

    async def run(self) -> None:
        ensure_vote_schema(self.database)
        task = asyncio.create_task(_poll_loop(self.database))
        try:
            await previous_run(self)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    mud_server_class.run = run
