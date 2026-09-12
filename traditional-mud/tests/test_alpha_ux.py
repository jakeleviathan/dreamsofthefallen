from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
import mud.alpha_ux as alpha


class DummySession:
    def __init__(self, database, character) -> None:
        self.database = database
        self.character = character
        self.active_enemy = None
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class AlphaUXTests(unittest.TestCase):
    def _session(self, root: Path) -> DummySession:
        db = Database(root / "mud.db")
        account = db.create_account("ux_account", "hash")
        character = db.create_character(account.id, "Uxhero", "human", "wizard")
        return DummySession(db, character)

    def test_schema_tracks_milestones_events_and_reports_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self._session(Path(temp))
            alpha.ensure_alpha_ux_schema(session.database)
            self.assertTrue(alpha._milestone(session, "first_movement"))
            self.assertFalse(alpha._milestone(session, "first_movement"))
            asyncio.run(alpha._save_report(session, "bug", "the gate text repeated twice"))
            with session.database.connect() as db:
                milestones = db.execute("SELECT COUNT(*) FROM alpha_ux_milestones").fetchone()[0]
                reports = db.execute("SELECT report_type, room_key, text FROM alpha_player_reports").fetchall()
            self.assertEqual(milestones, 1)
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["report_type"], "bug")
            self.assertIn("gate text", reports[0]["text"])
            self.assertEqual(reports[0]["room_key"], session.character.current_room)

    def test_command_telemetry_keeps_only_command_family_not_chat_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self._session(Path(temp))
            before = alpha._state_snapshot(session)
            after = alpha._state_snapshot(session)
            alpha._observe_transition(session, "say this secret sentence should never be stored", before, after, 12)
            with session.database.connect() as db:
                row = db.execute(
                    "SELECT command_verb, details FROM alpha_ux_events WHERE event_key='command' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertEqual(row["command_verb"], "say")
            self.assertNotIn("secret sentence", row["details"])

    def test_transition_observation_captures_first_session_funnel_without_checklist(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self._session(Path(temp))
            before = alpha._state_snapshot(session)
            session.character = SimpleNamespace(**{**session.character.__dict__, "current_room": "human_caravan_court"}) if hasattr(session.character, "__dict__") else session.character
            # CharacterRecord is frozen, so use snapshots directly to test the transition detector.
            after = dict(before)
            after["room"] = "human_caravan_court"
            after["inventory"] = before["inventory"].copy()
            after["inventory"]["test_loot"] += 1
            after["quests"] = before["quests"] + (("sample", "active", "step2"),)
            alpha._observe_transition(session, "east", before, after, 7)
            keys = alpha.milestone_keys(session.database, session.character.id)
            self.assertIn("first_movement", keys)
            self.assertIn("first_loot", keys)
            self.assertIn("first_quest_progress", keys)

    def test_guide_teaches_basics_without_revealing_secret_planes(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self._session(Path(temp))
            asyncio.run(alpha._show_guide(session))
            text = "".join(session.messages)
            self.assertIn("HELP HERE", text)
            self.assertIn("LOOK", text)
            self.assertNotIn("Unspoken", text)
            self.assertNotIn("Red Country", text)
            self.assertNotIn("7/7", text)

    def test_summary_surfaces_stalled_characters_and_report_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self._session(Path(temp))
            for _ in range(12):
                alpha._record_event(session, "command", verb="look", latency_ms=10)
            asyncio.run(alpha._save_report(session, "stuck", "I cannot tell where to go"))
            summary = alpha.alpha_ux_summary(session.database, 24)
            self.assertEqual(summary["events_command"], 12)
            self.assertEqual(summary["stalled_without_movement"], 1)
            self.assertEqual(summary["reports_stuck"], 1)
            self.assertEqual(summary["average_command_latency_ms"], 10.0)

    def test_production_server_installs_alpha_ux_between_help_and_modern_presentation(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
assert server.PlayerSession._command_guide_runtime_installed
assert server.PlayerSession._alpha_ux_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
print("ALPHA_UX_OK")
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
        self.assertIn("ALPHA_UX_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
