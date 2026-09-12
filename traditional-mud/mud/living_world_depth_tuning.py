from __future__ import annotations

from dataclasses import replace

import mud.living_world_depth as depth


_DEPTH_TUNING_APPLIED = False


def _ensure_note_history(database) -> None:
    depth.ensure_depth_schema(database)
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS living_board_note_posts (
                note_id INTEGER PRIMARY KEY,
                character_id INTEGER NOT NULL,
                posted_day INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_living_board_note_posts_character_day
            ON living_board_note_posts(character_id, posted_day);

            CREATE TRIGGER IF NOT EXISTS living_board_note_posts_after_insert
            AFTER INSERT ON living_board_notes
            BEGIN
                INSERT OR IGNORE INTO living_board_note_posts(note_id, character_id, posted_day)
                VALUES (NEW.id, NEW.character_id, NEW.posted_day);
            END;
            """
        )
        # Backfill any notes created before this tuning layer was installed.
        db.execute(
            """
            INSERT OR IGNORE INTO living_board_note_posts(note_id, character_id, posted_day)
            SELECT id, character_id, posted_day FROM living_board_notes
            """
        )


def _hardened_days_until_note_allowed(session, day: int) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return depth.BOARD_NOTE_COOLDOWN_DAYS
    _ensure_note_history(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT MAX(posted_day) AS last_day FROM living_board_note_posts WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    if row is None or row["last_day"] is None:
        return 0
    elapsed = int(day) - int(row["last_day"])
    return max(0, depth.BOARD_NOTE_COOLDOWN_DAYS - elapsed)


def _normalize_ambient_phases() -> None:
    # AstralisClock exposes dawn/day/dusk/night. A few authored scenes were
    # intentionally written in human-language morning/evening terms; normalize
    # those labels once so every scene can actually fire in the live clock.
    aliases = {"morning": "dawn", "evening": "dusk"}
    depth.AMBIENT_SCENES = tuple(
        replace(scene, phases=tuple(aliases.get(phase, phase) for phase in scene.phases))
        for scene in depth.AMBIENT_SCENES
    )


def apply_living_world_depth_tuning() -> None:
    global _DEPTH_TUNING_APPLIED
    if _DEPTH_TUNING_APPLIED:
        return
    _normalize_ambient_phases()
    depth._days_until_note_allowed = _hardened_days_until_note_allowed
    _DEPTH_TUNING_APPLIED = True
