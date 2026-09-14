from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from mud.alpha_hardening import (
    CHECKPOINTS,
    GROUP_SAMPLES_PER_BAND,
    LEVEL_BANDS,
    MEANINGFUL_COMMANDS,
    OUTSIDE_PLAYTESTER_TARGET,
    SOLO_SAMPLES_PER_CLASS_BAND,
    audit_gear_curve,
    combat_balance_audit,
    ensure_alpha_hardening_schema,
    install_alpha_hardening_runtime,
    playtest_audit,
    recent_observations,
    record_observation,
)
from mud.alpha_ux import ensure_alpha_ux_schema
from mud.database import Database


ROOT = Path(__file__).resolve().parents[1]


def make_database() -> Database:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    return Database(handle.name)


def add_character(database: Database, name: str, race: str, class_key: str, level: int = 10) -> int:
    with database.connect() as db:
        account = db.execute(
            "INSERT INTO accounts (name, password_hash) VALUES (?, 'x')",
            (f"acct_{name}",),
        )
        account_id = int(account.lastrowid)
        character = db.execute(
            """
            INSERT INTO characters (
                account_id, name, level, race, character_class,
                might, grace, love, mind, hp_stat
            ) VALUES (?, ?, ?, ?, ?, 5, 5, 5, 5, 5)
            """,
            (account_id, name, level, race, class_key),
        )
        return int(character.lastrowid)


class AlphaHardeningDesignTests(unittest.TestCase):
    def test_gear_curve_has_four_readable_checkpoints_and_rising_power(self):
        audit = audit_gear_curve()
        self.assertEqual(tuple(point.checkpoint for point in audit.checkpoints), CHECKPOINTS)
        self.assertEqual(tuple(point.tier for point in audit.checkpoints), (1, 2, 3, 4))
        self.assertTrue(all(point.items > 0 for point in audit.checkpoints))
        self.assertTrue(all(len(point.slots) >= 4 for point in audit.checkpoints))
        self.assertTrue(audit.monotonic_power, audit.catalog_problems)
        self.assertTrue(audit.ready, audit.catalog_problems)

    def test_combat_audit_uses_real_class_level_and_party_context(self):
        database = make_database()
        ensure_alpha_hardening_schema(database)
        character_id = add_character(database, "BruteSample", "human", "brute", 10)
        now = time.time()
        with database.connect() as db:
            for i in range(SOLO_SAMPLES_PER_CLASS_BAND):
                cur = db.execute(
                    """
                    INSERT INTO production_combat_log (
                        character_id, enemy_key, character_level, started_at_epoch,
                        ended_at_epoch, outcome, duration_seconds, xp_reward
                    ) VALUES (?, 'test_enemy', 10, ?, ?, 'victory', ?, 10)
                    """,
                    (character_id, now - 10, now, 12.0 + i),
                )
                db.execute(
                    """
                    INSERT INTO alpha_hardening_combat_context (
                        combat_log_id, character_id, race_key, class_key,
                        character_level, party_size, room_key
                    ) VALUES (?, ?, 'human', 'brute', 10, 1, 'test_room')
                    """,
                    (int(cur.lastrowid), character_id),
                )
            for i in range(GROUP_SAMPLES_PER_BAND):
                cur = db.execute(
                    """
                    INSERT INTO production_combat_log (
                        character_id, enemy_key, character_level, started_at_epoch,
                        ended_at_epoch, outcome, duration_seconds, xp_reward
                    ) VALUES (?, 'party_enemy', 10, ?, ?, 'victory', 20.0, 10)
                    """,
                    (character_id, now - 10, now),
                )
                db.execute(
                    """
                    INSERT INTO alpha_hardening_combat_context (
                        combat_log_id, character_id, race_key, class_key,
                        character_level, party_size, room_key
                    ) VALUES (?, ?, 'human', 'brute', 10, 2, 'test_room')
                    """,
                    (int(cur.lastrowid), character_id),
                )

        report = combat_balance_audit(database, 24)
        brute = next(cell for cell in report.cells if cell.level_low == 1 and cell.class_key == "brute")
        self.assertEqual(brute.fights, SOLO_SAMPLES_PER_CLASS_BAND)
        self.assertEqual(brute.victories, SOLO_SAMPLES_PER_CLASS_BAND)
        self.assertEqual(brute.party_fights, GROUP_SAMPLES_PER_BAND)
        self.assertEqual(report.solo_cells_ready, 1)
        self.assertEqual(report.solo_cells_total, len(LEVEL_BANDS) * 5)
        self.assertEqual(report.group_bands_ready, 1)

    def test_outside_playtest_gate_requires_meaningful_uncoached_sessions(self):
        database = make_database()
        ensure_alpha_ux_schema(database)
        ensure_alpha_hardening_schema(database)
        races = ("human", "forest_elf", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin")
        classes = ("brute", "wizard", "druid", "priest", "necromancer")
        with database.connect() as db:
            for i in range(OUTSIDE_PLAYTESTER_TARGET):
                character_id = add_character(database, f"Tester{i}", races[i % len(races)], classes[i % len(classes)], 6)
                for _ in range(MEANINGFUL_COMMANDS):
                    db.execute(
                        "INSERT INTO alpha_ux_events (character_id, event_key, command_verb) VALUES (?, 'command', 'look')",
                        (character_id,),
                    )
                for milestone in ("first_movement", "first_combat", "first_quest_progress"):
                    db.execute(
                        "INSERT INTO alpha_ux_milestones (character_id, milestone_key) VALUES (?, ?)",
                        (character_id, milestone),
                    )

        report = playtest_audit(database, 24 * 30)
        self.assertEqual(report.meaningful_testers, OUTSIDE_PLAYTESTER_TARGET)
        self.assertTrue(report.cohort_ready)
        self.assertGreater(report.race_class_combinations_seen, 1)

    def test_staff_observations_are_short_categorized_and_reviewable(self):
        database = make_database()
        record_observation(database, "navigation", "Player tried WEST three times before noticing EXITS.")
        rows = recent_observations(database, 24)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "navigation")
        self.assertIn("WEST", rows[0]["note"])
        with self.assertRaises(ValueError):
            record_observation(database, "guess", "invalid category")


@dataclass
class FakeCharacter:
    id: int
    name: str = "Telemetry"
    race: str = "human"
    character_class: str = "wizard"
    level: int = 20
    current_room: str = "test_room"


class FakeState:
    DISCONNECTED = "disconnected"


class BaseCombatSession:
    def __init__(self, database: Database):
        self.database = database
        self.character = FakeCharacter(add_character(database, "Telemetry", "human", "wizard", 20))
        self.commands = ["attack dummy"]
        self.outputs: list[str] = []
        self.state = FakeState()
        self._production_combat_log_id = None

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        return self.commands.pop(0) if self.commands else None

    def current_prompt_text(self):
        return "> "

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is None:
            return
        now = time.time()
        ensure_alpha_hardening_schema(self.database)
        with self.database.connect() as db:
            cur = db.execute(
                """
                INSERT INTO production_combat_log (
                    character_id, enemy_key, character_level, started_at_epoch,
                    outcome, hp_start, xp_reward
                ) VALUES (?, 'dummy', 20, ?, 'open', 100, 0)
                """,
                (self.character.id, now),
            )
            self._production_combat_log_id = int(cur.lastrowid)


class AlphaHardeningRuntimeTests(unittest.TestCase):
    def test_runtime_tags_new_combat_row_with_class_level_and_party_size(self):
        database = make_database()

        class Session(BaseCombatSession):
            pass

        install_alpha_hardening_runtime(Session)
        session = Session(database)
        asyncio.run(session.playing_prompt())
        with database.connect() as db:
            row = db.execute(
                "SELECT race_key, class_key, character_level, party_size, room_key FROM alpha_hardening_combat_context"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["race_key"], "human")
        self.assertEqual(row["class_key"], "wizard")
        self.assertEqual(row["character_level"], 20)
        self.assertEqual(row["party_size"], 1)
        self.assertEqual(row["room_key"], "test_room")


class ProductionAlphaHardeningTests(unittest.TestCase):
    def test_real_production_entrypoint_installs_hardening_and_keeps_all_40_starts_green(self):
        code = r'''
import server
from mud.alpha_hardening import audit_first_ten_matrix, audit_gear_curve

assert server.PlayerSession._alpha_hardening_runtime_installed
matrix = audit_first_ten_matrix(server.WORLD)
assert matrix.ready, matrix.problems
assert matrix.combinations == 40
assert matrix.walkable_starts == 40
assert matrix.level_ten_kits == 40
gear = audit_gear_curve()
assert gear.ready, gear.catalog_problems
print("ALPHA_HARDENING_1_40_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ALPHA_HARDENING_1_40_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
