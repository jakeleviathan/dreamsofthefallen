"""Durable, reusable community-event journal for shared Astralis settlements.

World events belong to the world, not to one player's session. Event keys make
daily ceremonies and weather incidents idempotent across concurrent players and
server restarts. Character contributions are recorded separately and never
grant duplicate rewards.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommunityEvent:
    community: str
    kind: str
    key: str
    day: int
    stage: str
    started_minute: int
    stage_minute: int


class CommunityEventJournal:
    def __init__(self, database):
        self.database = database
        with self.database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS community_events (
                    community TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    event_key TEXT NOT NULL,
                    world_day INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    started_minute INTEGER NOT NULL,
                    stage_minute INTEGER NOT NULL,
                    PRIMARY KEY (community, kind, event_key)
                );
                CREATE INDEX IF NOT EXISTS idx_community_recent_events
                    ON community_events (community, kind, started_minute DESC);
                CREATE TABLE IF NOT EXISTS community_event_participants (
                    community TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    event_key TEXT NOT NULL,
                    character_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    joined_minute INTEGER NOT NULL,
                    PRIMARY KEY (community, kind, event_key, character_id, role),
                    FOREIGN KEY (community, kind, event_key)
                        REFERENCES community_events (community, kind, event_key)
                        ON DELETE CASCADE,
                    FOREIGN KEY (character_id)
                        REFERENCES characters (id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS community_stories (
                    community TEXT NOT NULL,
                    story_key TEXT NOT NULL,
                    character_id INTEGER NOT NULL,
                    shared_minute INTEGER NOT NULL,
                    PRIMARY KEY (community, story_key, character_id),
                    FOREIGN KEY (character_id)
                        REFERENCES characters (id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS community_meta (
                    community TEXT NOT NULL,
                    meta_key TEXT NOT NULL,
                    meta_value TEXT NOT NULL,
                    PRIMARY KEY (community, meta_key)
                );
            """)

    @staticmethod
    def _event(row) -> CommunityEvent | None:
        if row is None:
            return None
        return CommunityEvent(
            community=row["community"],
            kind=row["kind"],
            key=row["event_key"],
            day=row["world_day"],
            stage=row["stage"],
            started_minute=row["started_minute"],
            stage_minute=row["stage_minute"],
        )

    def get(self, community: str, kind: str, key: str) -> CommunityEvent | None:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT * FROM community_events WHERE community = ? AND kind = ? AND event_key = ?",
                (community, kind, key),
            ).fetchone()
        return self._event(row)

    def recent(self, community: str, kind: str) -> CommunityEvent | None:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT * FROM community_events WHERE community = ? AND kind = ? "
                "ORDER BY started_minute DESC LIMIT 1", (community, kind),
            ).fetchone()
        return self._event(row)

    def start_once(
        self, community: str, kind: str, key: str, day: int,
        minute: int, stage: str = "active",
    ) -> tuple[CommunityEvent, bool]:
        with self.database.connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO community_events "
                "(community, kind, event_key, world_day, stage, started_minute, stage_minute) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (community, kind, key, day, stage, minute, minute),
            )
            row = db.execute(
                "SELECT * FROM community_events WHERE community = ? AND kind = ? AND event_key = ?",
                (community, kind, key),
            ).fetchone()
        assert row is not None
        return self._event(row), bool(cursor.rowcount)

    def advance(
        self, event: CommunityEvent, expected: str, next_stage: str, minute: int,
    ) -> bool:
        with self.database.connect() as db:
            cursor = db.execute(
                "UPDATE community_events SET stage = ?, stage_minute = ? "
                "WHERE community = ? AND kind = ? AND event_key = ? AND stage = ?",
                (next_stage, minute, event.community, event.kind, event.key, expected),
            )
        return bool(cursor.rowcount)

    def participate(
        self, event: CommunityEvent, character_id: int, role: str, minute: int,
    ) -> bool:
        with self.database.connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO community_event_participants "
                "(community, kind, event_key, character_id, role, joined_minute) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event.community, event.kind, event.key, character_id, role, minute),
            )
        return bool(cursor.rowcount)

    def share_story(
        self, community: str, story: str, character_id: int, minute: int,
    ) -> bool:
        with self.database.connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO community_stories "
                "(community, story_key, character_id, shared_minute) VALUES (?, ?, ?, ?)",
                (community, story, character_id, minute),
            )
        return bool(cursor.rowcount)

    def latest_story(self, community: str, story: str) -> tuple[str, int] | None:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT characters.name AS name, s.shared_minute AS minute "
                "FROM community_stories AS s "
                "JOIN characters ON characters.id = s.character_id "
                "WHERE s.community = ? AND s.story_key = ? "
                "ORDER BY s.shared_minute DESC, characters.id DESC LIMIT 1",
                (community, story),
            ).fetchone()
        return (row["name"], row["minute"]) if row is not None else None

    def latest_participant(self, event: CommunityEvent, role: str) -> str | None:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT characters.name AS name "
                "FROM community_event_participants AS p "
                "JOIN characters ON characters.id = p.character_id "
                "WHERE p.community = ? AND p.kind = ? AND p.event_key = ? AND p.role = ? "
                "ORDER BY p.joined_minute DESC, characters.id DESC LIMIT 1",
                (event.community, event.kind, event.key, role),
            ).fetchone()
        return row["name"] if row is not None else None

    def meta(self, community: str, key: str) -> str | None:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT meta_value FROM community_meta WHERE community = ? AND meta_key = ?",
                (community, key),
            ).fetchone()
        return row["meta_value"] if row is not None else None

    def set_meta(self, community: str, key: str, value: str) -> None:
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO community_meta (community, meta_key, meta_value) "
                "VALUES (?, ?, ?) ON CONFLICT (community, meta_key) "
                "DO UPDATE SET meta_value = excluded.meta_value",
                (community, key, value),
            )
