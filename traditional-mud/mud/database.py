from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from mud.mechanics import PROGRESSION_RULES
from mud.stats import CharacterStats


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mud.db"
MAX_CHARACTERS_PER_ACCOUNT = 8


class CharacterSlotLimitReached(Exception):
    """Raised when an account already uses all available character slots."""


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: int
    name: str
    password_hash: str


@dataclass(frozen=True, slots=True)
class CharacterRecord:
    id: int
    account_id: int
    name: str
    level: int
    experience: int
    race: str | None
    character_class: str | None
    deity_key: str | None
    might: int
    grace: int
    love: int
    mind: int
    hp_stat: int
    current_room: str | None = None
    bind_room: str | None = None

    @property
    def stats(self) -> CharacterStats:
        return CharacterStats(
            might=self.might,
            grace=self.grace,
            love=self.love,
            mind=self.mind,
            hp=self.hp_stat,
        )


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.environ.get("MUD_DB_PATH") or DEFAULT_DB_PATH
        self.path = Path(configured_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
                    experience INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
                    race TEXT,
                    character_class TEXT,
                    deity_key TEXT,
                    might INTEGER NOT NULL DEFAULT 0,
                    grace INTEGER NOT NULL DEFAULT 0,
                    love INTEGER NOT NULL DEFAULT 0,
                    mind INTEGER NOT NULL DEFAULT 0,
                    hp_stat INTEGER NOT NULL DEFAULT 0,
                    current_room TEXT,
                    bind_room TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_played_at TEXT,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_characters_account_id
                ON characters(account_id);

                CREATE TABLE IF NOT EXISTS character_abilities (
                    character_id INTEGER NOT NULL,
                    ability_key TEXT NOT NULL,
                    uses INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
                    skill_xp INTEGER NOT NULL DEFAULT 0 CHECK (skill_xp >= 0),
                    last_used_at TEXT,
                    PRIMARY KEY (character_id, ability_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_trade_skills (
                    character_id INTEGER NOT NULL,
                    trade_skill_key TEXT NOT NULL,
                    uses INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
                    skill_xp INTEGER NOT NULL DEFAULT 0 CHECK (skill_xp >= 0),
                    PRIMARY KEY (character_id, trade_skill_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_flags (
                    character_id INTEGER NOT NULL,
                    flag_key TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (character_id, flag_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_keys (
                    character_id INTEGER NOT NULL,
                    key_key TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (character_id, key_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_items (
                    character_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                    PRIMARY KEY (character_id, item_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_pets (
                    character_id INTEGER PRIMARY KEY,
                    pet_key TEXT NOT NULL,
                    summoned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_quests (
                    character_id INTEGER NOT NULL,
                    quest_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    current_step TEXT,
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    PRIMARY KEY (character_id, quest_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );
                """
            )
            self._ensure_character_columns(db)
            # Development migrations for the fungal race name as it was finalized.
            db.execute("UPDATE characters SET race = 'sporekin' WHERE race IN ('fungal', 'sporkkin', 'sporkin')")
            # Necromancer catalyst terminology was refined from generic Bones
            # to purchasable Bone Chips. Preserve older development inventories.
            db.execute(
                """
                INSERT INTO character_items (character_id, item_key, quantity)
                SELECT character_id, 'bone_chips', quantity
                FROM character_items
                WHERE item_key = 'bones' AND quantity > 0
                ON CONFLICT(character_id, item_key) DO UPDATE SET
                    quantity = quantity + excluded.quantity
                """
            )
            db.execute("DELETE FROM character_items WHERE item_key = 'bones'")
            # Sporekin gained a room-authored opening after the regional shell.
            # Older development characters without a saved room begin in Lumen Hollow.
            db.execute(
                "UPDATE characters SET current_room = 'sporekin_lumen_hollow' WHERE race = 'sporekin' AND current_room IS NULL"
            )
            # Bind points were added after room-based starts. Existing characters
            # default to whatever authored starting/current room they already have.
            db.execute(
                "UPDATE characters SET bind_room = current_room WHERE bind_room IS NULL AND current_room IS NOT NULL"
            )
            # Brute starting AC was later finalized as an equipment-derived 8.
            # Backfill the starter harness for older development Brutes without
            # touching any existing stat allocations or progression.
            db.execute(
                """
                INSERT OR IGNORE INTO character_items (character_id, item_key, quantity)
                SELECT id, 'brute_training_harness', 1
                FROM characters
                WHERE character_class = 'brute'
                """
            )

    @staticmethod
    def _ensure_character_columns(db: sqlite3.Connection) -> None:
        """Upgrade databases made by earlier development builds in-place."""
        columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(characters)").fetchall()
        }
        if "experience" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN experience INTEGER NOT NULL DEFAULT 0")
        if "race" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN race TEXT")
        if "character_class" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN character_class TEXT")
        if "deity_key" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN deity_key TEXT")
        if "might" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN might INTEGER NOT NULL DEFAULT 0")
        if "grace" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN grace INTEGER NOT NULL DEFAULT 0")
        if "love" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN love INTEGER NOT NULL DEFAULT 0")
        if "mind" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN mind INTEGER NOT NULL DEFAULT 0")
        if "hp_stat" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN hp_stat INTEGER NOT NULL DEFAULT 0")
        if "current_room" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN current_room TEXT")
        if "bind_room" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN bind_room TEXT")

    def get_account_by_name(self, name: str) -> AccountRecord | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT id, name, password_hash FROM accounts WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        return AccountRecord(
            id=row["id"],
            name=row["name"],
            password_hash=row["password_hash"],
        )

    def create_account(self, name: str, password_hash: str) -> AccountRecord:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO accounts (name, password_hash) VALUES (?, ?)",
                (name, password_hash),
            )
            account_id = int(cursor.lastrowid)
        return AccountRecord(id=account_id, name=name, password_hash=password_hash)

    def mark_login(self, account_id: int) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE accounts SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
                (account_id,),
            )

    def list_characters(self, account_id: int) -> list[CharacterRecord]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT id, account_id, name, level, experience, race, character_class,
                       deity_key, might, grace, love, mind, hp_stat, current_room, bind_room
                FROM characters
                WHERE account_id = ?
                ORDER BY id
                """,
                (account_id,),
            ).fetchall()
        return [self._character_from_row(row) for row in rows]

    def get_character_by_name(self, name: str) -> CharacterRecord | None:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT id, account_id, name, level, experience, race, character_class,
                       deity_key, might, grace, love, mind, hp_stat, current_room, bind_room
                FROM characters
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
        return None if row is None else self._character_from_row(row)

    def create_character(
        self,
        account_id: int,
        name: str,
        race: str,
        character_class: str,
        stats: CharacterStats | None = None,
        deity_key: str | None = None,
    ) -> CharacterRecord:
        with self.connect() as db:
            # Serialize writers while we count and insert so two simultaneous
            # sessions cannot create slots 8 and 9 at the same time.
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT COUNT(*) AS total FROM characters WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if int(row["total"]) >= MAX_CHARACTERS_PER_ACCOUNT:
                raise CharacterSlotLimitReached(
                    f"Account {account_id} already has {MAX_CHARACTERS_PER_ACCOUNT} characters."
                )

            stats = stats or CharacterStats()
            starting_room = (
                "human_demon_gate" if race == "human"
                else "forest_elf_circle_clearing" if race == "forest_elf"
                else "sporekin_lumen_hollow" if race == "sporekin"
                else None
            )
            cursor = db.execute(
                """
                INSERT INTO characters (
                    account_id, name, race, character_class, deity_key,
                    might, grace, love, mind, hp_stat, current_room, bind_room
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, name, race, character_class, deity_key,
                    stats.might, stats.grace, stats.love, stats.mind, stats.hp,
                    starting_room, starting_room,
                ),
            )
            character_id = int(cursor.lastrowid)
            # Every new character receives a plain starting weapon. The full
            # equipment/inventory experience will grow around this persisted item.
            db.execute(
                "INSERT INTO character_items (character_id, item_key, quantity) VALUES (?, 'starter_weapon', 1)",
                (character_id,),
            )
            if character_class == "brute":
                # Brute's approved starting AC 8 is equipment-derived. Until the
                # full EQUIP command is authored, this persisted training harness
                # represents the starter armor package used by combat state.
                db.execute(
                    "INSERT INTO character_items (character_id, item_key, quantity) VALUES (?, 'brute_training_harness', 1)",
                    (character_id,),
                )
            if race == "human":
                db.execute(
                    "INSERT INTO character_items (character_id, item_key, quantity) VALUES (?, 'sealed_cathedral_note', 1)",
                    (character_id,),
                )
                db.execute(
                    """
                    INSERT INTO character_quests (character_id, quest_key, status, current_step)
                    VALUES (?, 'human_cathedral_summons', 'active', 'read_note')
                    """,
                    (character_id,),
                )
            elif race == "forest_elf":
                db.execute(
                    """
                    INSERT INTO character_quests (character_id, quest_key, status, current_step)
                    VALUES (?, 'forest_elf_first_walk', 'active', 'leave_clearing')
                    """,
                    (character_id,),
                )
            elif race == "sporekin":
                db.execute(
                    """
                    INSERT INTO character_quests (character_id, quest_key, status, current_step)
                    VALUES (?, 'sporekin_first_call', 'active', 'follow_living_threads')
                    """,
                    (character_id,),
                )

        return CharacterRecord(
            id=character_id,
            account_id=account_id,
            name=name,
            level=1,
            experience=0,
            race=race,
            character_class=character_class,
            deity_key=deity_key,
            might=stats.might,
            grace=stats.grace,
            love=stats.love,
            mind=stats.mind,
            hp_stat=stats.hp,
            current_room=starting_room,
            bind_room=starting_room,
        )

    def set_character_deity(self, character_id: int, deity_key: str | None) -> None:
        """Persist the Priest deity/path choice once Astralis's gods are authored."""
        with self.connect() as db:
            db.execute(
                "UPDATE characters SET deity_key = ? WHERE id = ?",
                (deity_key, character_id),
            )

    def add_item(self, character_id: int, item_key: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Item quantity added must be positive.")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO character_items (character_id, item_key, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(character_id, item_key) DO UPDATE SET
                    quantity = quantity + excluded.quantity
                """,
                (character_id, item_key, quantity),
            )

    def item_quantity(self, character_id: int, item_key: str) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                (character_id, item_key),
            ).fetchone()
        return 0 if row is None else int(row["quantity"])

    def list_items(self, character_id: int) -> list[dict[str, int | str]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT item_key, quantity
                FROM character_items
                WHERE character_id = ? AND quantity > 0
                ORDER BY item_key
                """,
                (character_id,),
            ).fetchall()
        return [
            {"item_key": str(row["item_key"]), "quantity": int(row["quantity"])}
            for row in rows
        ]

    def complete_crafting_transaction(
        self,
        character_id: int,
        *,
        trade_skill_key: str,
        materials,
        output_item_key: str,
        output_quantity: int = 1,
        skill_xp_gain: int = 1,
    ) -> bool:
        """Atomically consume recipe materials, create output, and advance the trade skill."""
        if output_quantity <= 0:
            raise ValueError("Crafting output quantity must be positive.")
        if skill_xp_gain < 0:
            raise ValueError("Trade skill XP gain cannot be negative.")

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for requirement in materials:
                row = db.execute(
                    "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, requirement.item_key),
                ).fetchone()
                if row is None or int(row["quantity"]) < requirement.quantity:
                    return False

            for requirement in materials:
                row = db.execute(
                    "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, requirement.item_key),
                ).fetchone()
                remaining = int(row["quantity"]) - requirement.quantity
                if remaining:
                    db.execute(
                        "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                        (remaining, character_id, requirement.item_key),
                    )
                else:
                    db.execute(
                        "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                        (character_id, requirement.item_key),
                    )

            db.execute(
                """
                INSERT INTO character_items (character_id, item_key, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(character_id, item_key) DO UPDATE SET
                    quantity = quantity + excluded.quantity
                """,
                (character_id, output_item_key, output_quantity),
            )
            db.execute(
                """
                INSERT INTO character_trade_skills (character_id, trade_skill_key, uses, skill_xp)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(character_id, trade_skill_key) DO UPDATE SET
                    uses = uses + 1,
                    skill_xp = skill_xp + excluded.skill_xp
                """,
                (character_id, trade_skill_key, skill_xp_gain),
            )
        return True

    def consume_item(self, character_id: int, item_key: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            raise ValueError("Item quantity consumed must be positive.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                (character_id, item_key),
            ).fetchone()
            if row is None or int(row["quantity"]) < quantity:
                return False
            new_quantity = int(row["quantity"]) - quantity
            if new_quantity == 0:
                db.execute(
                    "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, item_key),
                )
            else:
                db.execute(
                    "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                    (new_quantity, character_id, item_key),
                )
        return True

    def summon_pet_with_catalyst(
        self,
        character_id: int,
        *,
        pet_key: str,
        catalyst_item_key: str,
        catalyst_quantity: int = 1,
    ) -> bool:
        """Consume an inventory catalyst and replace the character's active pet."""
        if catalyst_quantity <= 0:
            raise ValueError("Catalyst quantity must be positive.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                (character_id, catalyst_item_key),
            ).fetchone()
            if row is None or int(row["quantity"]) < catalyst_quantity:
                return False
            remaining = int(row["quantity"]) - catalyst_quantity
            if remaining:
                db.execute(
                    "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                    (remaining, character_id, catalyst_item_key),
                )
            else:
                db.execute(
                    "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, catalyst_item_key),
                )
            db.execute(
                """
                INSERT INTO character_pets (character_id, pet_key)
                VALUES (?, ?)
                ON CONFLICT(character_id) DO UPDATE SET
                    pet_key = excluded.pet_key,
                    summoned_at = CURRENT_TIMESTAMP
                """,
                (character_id, pet_key),
            )
        return True

    def get_active_pet(self, character_id: int) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT pet_key FROM character_pets WHERE character_id = ?",
                (character_id,),
            ).fetchone()
        return None if row is None else str(row["pet_key"])

    def set_character_stats(
        self,
        character_id: int,
        *,
        might: int,
        grace: int,
        love: int,
        mind: int,
        hp: int,
    ) -> None:
        values = (might, grace, love, mind, hp)
        if any(value < 0 for value in values):
            raise ValueError("Character stats cannot be negative.")
        with self.connect() as db:
            db.execute(
                """
                UPDATE characters
                SET might = ?, grace = ?, love = ?, mind = ?, hp_stat = ?
                WHERE id = ?
                """,
                (might, grace, love, mind, hp, character_id),
            )

    def record_trade_skill_use(
        self, character_id: int, trade_skill_key: str, skill_xp_gain: int = 1
    ) -> None:
        if skill_xp_gain < 0:
            raise ValueError("Trade skill XP gain cannot be negative.")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO character_trade_skills (character_id, trade_skill_key, uses, skill_xp)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(character_id, trade_skill_key) DO UPDATE SET
                    uses = uses + 1,
                    skill_xp = skill_xp + excluded.skill_xp
                """,
                (character_id, trade_skill_key, skill_xp_gain),
            )

    def get_trade_skill_progress(self, character_id: int, trade_skill_key: str) -> dict[str, int]:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT uses, skill_xp FROM character_trade_skills
                WHERE character_id = ? AND trade_skill_key = ?
                """,
                (character_id, trade_skill_key),
            ).fetchone()
        if row is None:
            return {"uses": 0, "skill_xp": 0}
        return {"uses": int(row["uses"]), "skill_xp": int(row["skill_xp"])}

    def list_trade_skills(self, character_id: int) -> list[dict[str, int | str]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT trade_skill_key, uses, skill_xp
                FROM character_trade_skills
                WHERE character_id = ?
                ORDER BY trade_skill_key
                """,
                (character_id,),
            ).fetchall()
        return [
            {
                "trade_skill_key": str(row["trade_skill_key"]),
                "uses": int(row["uses"]),
                "skill_xp": int(row["skill_xp"]),
            }
            for row in rows
        ]

    def add_experience(self, character_id: int, amount: int) -> int:
        if amount < 0:
            raise ValueError("Experience gain cannot be negative.")
        with self.connect() as db:
            row = db.execute(
                "SELECT experience FROM characters WHERE id = ?",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown character id {character_id}")
            new_experience = int(row["experience"]) + amount
            new_level = PROGRESSION_RULES.level_for_experience(new_experience)
            db.execute(
                "UPDATE characters SET experience = ?, level = ? WHERE id = ?",
                (new_experience, new_level, character_id),
            )
        return new_level


    def grant_flag(self, character_id: int, flag_key: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO character_flags (character_id, flag_key) VALUES (?, ?)",
                (character_id, flag_key),
            )

    def revoke_flag(self, character_id: int, flag_key: str) -> None:
        with self.connect() as db:
            db.execute(
                "DELETE FROM character_flags WHERE character_id = ? AND flag_key = ?",
                (character_id, flag_key),
            )

    def list_flags(self, character_id: int) -> frozenset[str]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT flag_key FROM character_flags WHERE character_id = ? ORDER BY flag_key",
                (character_id,),
            ).fetchall()
        return frozenset(row["flag_key"] for row in rows)

    def grant_key(self, character_id: int, key_key: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO character_keys (character_id, key_key) VALUES (?, ?)",
                (character_id, key_key),
            )

    def revoke_key(self, character_id: int, key_key: str) -> None:
        with self.connect() as db:
            db.execute(
                "DELETE FROM character_keys WHERE character_id = ? AND key_key = ?",
                (character_id, key_key),
            )

    def list_keys(self, character_id: int) -> frozenset[str]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT key_key FROM character_keys WHERE character_id = ? ORDER BY key_key",
                (character_id,),
            ).fetchall()
        return frozenset(row["key_key"] for row in rows)


    def set_character_room(self, character_id: int, room_key: str | None) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE characters SET current_room = ?, last_played_at = CURRENT_TIMESTAMP WHERE id = ?",
                (room_key, character_id),
            )

    def set_bind_room(self, character_id: int, room_key: str) -> None:
        """Persist a character bind point. Spells can call this later."""
        if not room_key:
            raise ValueError("Bind room cannot be empty.")
        with self.connect() as db:
            db.execute(
                "UPDATE characters SET bind_room = ? WHERE id = ?",
                (room_key, character_id),
            )

    def apply_experience_loss(self, character_id: int, amount: int, *, floor_experience: int = 0) -> tuple[int, int, int]:
        """Remove XP atomically without dropping below an authored floor.

        Returns (actual_loss, new_experience, new_level).
        """
        if amount < 0:
            raise ValueError("Experience loss cannot be negative.")
        floor_experience = max(0, floor_experience)
        with self.connect() as db:
            row = db.execute(
                "SELECT experience FROM characters WHERE id = ?",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown character id {character_id}")
            old_experience = int(row["experience"])
            new_experience = max(floor_experience, old_experience - amount)
            actual_loss = old_experience - new_experience
            new_level = PROGRESSION_RULES.level_for_experience(new_experience)
            db.execute(
                "UPDATE characters SET experience = ?, level = ? WHERE id = ?",
                (new_experience, new_level, character_id),
            )
        return actual_loss, new_experience, new_level

    def start_quest(self, character_id: int, quest_key: str, current_step: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO character_quests (character_id, quest_key, status, current_step)
                VALUES (?, ?, 'active', ?)
                ON CONFLICT(character_id, quest_key) DO NOTHING
                """,
                (character_id, quest_key, current_step),
            )

    def get_quest(self, character_id: int, quest_key: str) -> dict[str, str | None] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT quest_key, status, current_step FROM character_quests WHERE character_id = ? AND quest_key = ?",
                (character_id, quest_key),
            ).fetchone()
        if row is None:
            return None
        return {
            "quest_key": str(row["quest_key"]),
            "status": str(row["status"]),
            "current_step": row["current_step"],
        }

    def list_quests(self, character_id: int) -> list[dict[str, str | None]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT quest_key, status, current_step FROM character_quests WHERE character_id = ? ORDER BY started_at, quest_key",
                (character_id,),
            ).fetchall()
        return [
            {"quest_key": str(row["quest_key"]), "status": str(row["status"]), "current_step": row["current_step"]}
            for row in rows
        ]

    def advance_quest(self, character_id: int, quest_key: str, current_step: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE character_quests SET current_step = ? WHERE character_id = ? AND quest_key = ? AND status = 'active'",
                (current_step, character_id, quest_key),
            )

    def complete_quest(self, character_id: int, quest_key: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                UPDATE character_quests
                SET status = 'completed', current_step = 'complete', completed_at = CURRENT_TIMESTAMP
                WHERE character_id = ? AND quest_key = ?
                """,
                (character_id, quest_key),
            )

    def record_ability_use(
        self,
        character_id: int,
        ability_key: str,
        skill_xp_gain: int = 1,
    ) -> None:
        """Persist use-based ability progression without imposing a rank formula yet."""
        if skill_xp_gain < 0:
            raise ValueError("Ability skill XP gain cannot be negative.")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO character_abilities (character_id, ability_key, uses, skill_xp, last_used_at)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(character_id, ability_key) DO UPDATE SET
                    uses = uses + 1,
                    skill_xp = skill_xp + excluded.skill_xp,
                    last_used_at = CURRENT_TIMESTAMP
                """,
                (character_id, ability_key, skill_xp_gain),
            )

    def list_ability_progress(self, character_id: int) -> list[dict[str, int | str]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT ability_key, uses, skill_xp
                FROM character_abilities
                WHERE character_id = ?
                ORDER BY ability_key
                """,
                (character_id,),
            ).fetchall()
        return [
            {
                "ability_key": row["ability_key"],
                "uses": row["uses"],
                "skill_xp": row["skill_xp"],
            }
            for row in rows
        ]

    @staticmethod
    def _character_from_row(row: sqlite3.Row) -> CharacterRecord:
        return CharacterRecord(
            id=row["id"],
            account_id=row["account_id"],
            name=row["name"],
            level=row["level"],
            experience=row["experience"],
            race=row["race"],
            character_class=row["character_class"],
            deity_key=row["deity_key"],
            might=row["might"],
            grace=row["grace"],
            love=row["love"],
            mind=row["mind"],
            hp_stat=row["hp_stat"],
            current_room=row["current_room"] if "current_room" in row.keys() else None,
            bind_room=row["bind_room"] if "bind_room" in row.keys() else None,
        )
