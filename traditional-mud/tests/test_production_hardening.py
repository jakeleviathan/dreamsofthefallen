from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.combat import EnemyState, SEWER_RAT, SMALL_IMP
from mud.database import Database
from mud.session import SessionState
import mud.production_hardening as production


class DummyWriter:
    def __init__(self) -> None:
        self.closed = False

    def is_closing(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True


class DummySession:
    def __init__(self, database, account, character=None) -> None:
        self.database = database
        self.account = account
        self.character = character
        self.writer = DummyWriter()
        self.state = SessionState.PLAYING if character is not None else SessionState.CHARACTER_MENU
        self.messages: list[str] = []
        self.combatant = SimpleNamespace(current_hp=31)
        self.active_enemy = None
        self._production_combat_log_id = None
        self._production_combat_started = None

    async def send(self, text: str) -> None:
        self.messages.append(text)

    async def _stop_combat(self) -> None:
        self.active_enemy = None


class ProductionHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        production._ACTIVE_ACCOUNT_SESSIONS.clear()
        production._ACTIVE_CHARACTER_SESSIONS.clear()

    def _database(self, root: Path):
        db = Database(root / "mud.db")
        account = db.create_account("alpha_account", "hash")
        character = db.create_character(account.id, "Alphaone", "human", "wizard")
        return db, account, character

    def test_online_backup_is_valid_and_contains_committed_character_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db, _account, character = self._database(root)
            backup_dir = root / "backups"
            with patch.dict(os.environ, {"MUD_BACKUP_DIR": str(backup_dir), "MUD_BACKUP_RETAIN": "4"}):
                result = production.create_database_backup(db, reason="test")
            self.assertTrue(result.path.exists())
            self.assertEqual(result.integrity, "ok")
            copy = sqlite3.connect(result.path)
            try:
                row = copy.execute("SELECT name FROM characters WHERE id = ?", (character.id,)).fetchone()
            finally:
                copy.close()
            self.assertEqual(row[0], character.name)
            recorded = production.last_backup_row(db)
            self.assertEqual(recorded["reason"], "test")

    def test_inventory_audit_is_read_only_and_surfaces_unknown_item_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            db, _account, character = self._database(Path(temp))
            db.add_item(character.id, "alpha_unknown_item", 2)
            audit = production.audit_inventory_integrity(db)
            self.assertFalse(audit.healthy)
            self.assertEqual(audit.unknown_item_rows, 1)
            self.assertEqual(db.item_quantity(character.id, "alpha_unknown_item"), 2)
            self.assertTrue(any("alpha_unknown_item" in line for line in audit.details))

    def test_database_integrity_check_is_a_real_sqlite_check(self):
        with tempfile.TemporaryDirectory() as temp:
            db, _account, _character = self._database(Path(temp))
            healthy, messages = production.database_integrity(db)
            self.assertTrue(healthy)
            self.assertEqual(messages, ("ok",))

    def test_new_authenticated_connection_safely_supersedes_old_account_session(self):
        with tempfile.TemporaryDirectory() as temp:
            db, account, character = self._database(Path(temp))
            old = DummySession(db, account, character)
            new = DummySession(db, account, character)
            asyncio.run(production._claim_account_session(old))
            asyncio.run(production._claim_account_session(new))
            self.assertEqual(old.state, SessionState.DISCONNECTED)
            self.assertTrue(old.writer.closed)
            self.assertIn("resumed from another connection", "".join(old.messages))
            self.assertIs(production._session_from_ref(production._ACTIVE_ACCOUNT_SESSIONS, account.id), new)

    def test_closed_alpha_allowlist_is_optional_and_owner_is_not_required_to_be_listed(self):
        with patch.dict(os.environ, {"MUD_ALPHA_ALLOWLIST": "One, Two"}, clear=False):
            self.assertTrue(production.alpha_gate_enabled())
            self.assertEqual(production.alpha_allowlist(), frozenset({"one", "two"}))
        with patch.dict(os.environ, {"MUD_ALPHA_ALLOWLIST": ""}, clear=False):
            self.assertFalse(production.alpha_gate_enabled())

    def test_combat_metrics_capture_duration_outcome_and_reward_without_changing_combat(self):
        with tempfile.TemporaryDirectory() as temp:
            db, account, character = self._database(Path(temp))
            session = DummySession(db, account, character)
            session.active_enemy = EnemyState(SEWER_RAT)
            production._begin_combat_metric(session)
            self.assertIsNotNone(session._production_combat_log_id)
            production._finish_combat_metric(session, "victory", SEWER_RAT.xp_reward)
            summary = production.combat_summary(db, 24)
            self.assertEqual(summary.fights, 1)
            self.assertEqual(summary.victories, 1)
            self.assertEqual(summary.deaths, 0)
            with db.connect() as conn:
                row = conn.execute("SELECT outcome, xp_reward FROM production_combat_log").fetchone()
            self.assertEqual(row["outcome"], "victory")
            self.assertEqual(int(row["xp_reward"]), SEWER_RAT.xp_reward)

    def test_first_session_combat_tuning_shortens_fights_without_raising_grind_xp(self):
        self.assertEqual(SEWER_RAT.max_hp, 18)
        self.assertGreaterEqual(SEWER_RAT.auto_attack_interval, 3.4)
        self.assertEqual(SEWER_RAT.xp_reward, 15)
        self.assertEqual(SMALL_IMP.max_hp, 24)
        self.assertGreaterEqual(SMALL_IMP.auto_attack_interval, 3.2)
        self.assertEqual(SMALL_IMP.xp_reward, 20)

    def test_production_entrypoint_installs_hardening_operator_and_server_supervisor(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
assert server.PlayerSession._production_hardening_runtime_installed
assert server.PlayerSession._production_operator_runtime_installed
assert server.MudServer._production_supervisor_installed
print("PRODUCTION_HARDENING_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PRODUCTION_HARDENING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
