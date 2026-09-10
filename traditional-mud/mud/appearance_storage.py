from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.database import Database


def ensure_appearance_table(database: "Database") -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_appearance (
                character_id INTEGER NOT NULL,
                trait_key TEXT NOT NULL,
                trait_value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, trait_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )


def get_appearance(database: "Database", character_id: int) -> dict[str, str]:
    ensure_appearance_table(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT trait_key, trait_value FROM character_appearance WHERE character_id = ? ORDER BY trait_key",
            (character_id,),
        ).fetchall()
    return {str(row["trait_key"]): str(row["trait_value"]) for row in rows}


def set_appearance(database: "Database", character_id: int, trait_key: str, trait_value: str) -> None:
    ensure_appearance_table(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_appearance (character_id, trait_key, trait_value)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, trait_key) DO UPDATE SET
                trait_value = excluded.trait_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (character_id, trait_key, trait_value),
        )
