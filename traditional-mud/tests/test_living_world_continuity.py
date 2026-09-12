from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.living_world_depth as depth
import mud.living_world_continuity as continuity
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.mechanics import CombatantState
from mud.veyra_city import VEYRA_PUBLIC_HEARTH_KEY
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_LANTERN_MARKET_KEY


class DummyClock:
    def __init__(self, moment: AstralisMoment) -> None:
        self.moment = moment

    def now(self, real_seconds=None) -> AstralisMoment:
        return self.moment


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []
        self.active_enemy = None
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "human",
            current_hp=20,
            max_hp=30,
            current_mana=10,
            max_mana=20,
            auto_attack_interval=2.5,
            current_movement=100,
            max_movement=100,
            stats=character.stats,
            armor_class=0,
        )

    async def send(self, text: str) -> None:
        self.messages.append(text)

    def refresh(self) -> None:
        refreshed = self.database.get_character_by_name(self.character.name)
        assert refreshed is not None
        self.character = refreshed


class LivingWorldContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        continuity._install_content_extensions()

    def _session(self, root: Path, name: str = "Returner") -> DummySession:
        database = Database(root / "living_continuity.db")
        account = database.create_account(f"account_{name.lower()}", "x")
        character = database.create_character(account.id, name, "human", "brute")
        return DummySession(database, character)

    @staticmethod
    def _moment(day: int, hour: int = 12) -> AstralisMoment:
        return AstralisMoment(
            day_number=day,
            hour=hour,
            minute=0,
            total_minutes=((day - 1) * 24 * 60) + (hour * 60),
        )

    def test_small_texture_extension_stays_focused_on_places_people_use(self):
        self.assertEqual(len(continuity.EXTRA_DAILY_TEXTURES), 6)
        keys = [texture.key for texture in depth.DAILY_TEXTURES]
        for texture in continuity.EXTRA_DAILY_TEXTURES:
            self.assertEqual(keys.count(texture.key), 1)
        rooms = {texture.room_key for texture in continuity.EXTRA_DAILY_TEXTURES}
        self.assertIn(WAYMEET_COMMONHOUSE_KEY, rooms)
        self.assertIn(VEYRA_PUBLIC_HEARTH_KEY, rooms)
        self.assertGreaterEqual(len(depth.DAILY_TEXTURES), 30)

    def test_iven_is_distinct_recurring_face_not_permanent_furniture(self):
        # Day 2 (weekday 1) is a western maintenance route.
        west_market = self._moment(2, 15)
        west_hearth = self._moment(2, 20)
        # Day 3 (weekday 2) is an eastern route.
        east_hearth = self._moment(3, 21)
        absent = self._moment(4, 20)
        self.assertEqual(depth._scheduled_location(continuity.IVEN, west_market), WAYMEET_LANTERN_MARKET_KEY)
        self.assertEqual(depth._scheduled_location(continuity.IVEN, west_hearth), WAYMEET_COMMONHOUSE_KEY)
        self.assertEqual(depth._scheduled_location(continuity.IVEN, east_hearth), VEYRA_PUBLIC_HEARTH_KEY)
        self.assertIsNone(depth._scheduled_location(continuity.IVEN, absent))

    def test_familiar_faces_remember_a_character_across_astralis_days(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Merrin")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()

            first_meeting = self._moment(2, 20)
            with patch.object(continuity, "ASTRALIS_CLOCK", DummyClock(first_meeting)):
                self.assertTrue(asyncio.run(depth._talk_visitor(session, "iven")))

            memory = continuity._memory_row(session, continuity.IVEN.key)
            self.assertIsNotNone(memory)
            self.assertEqual(int(memory["first_met_day"]), 2)
            self.assertEqual(int(memory["last_met_day"]), 2)
            self.assertEqual(int(memory["times_spoken"]), 1)

            # Iven returns to the same western hearth on Day 5. Merely entering
            # the room produces one quiet recognition beat, not a quest popup.
            return_meeting = self._moment(5, 20)
            session.messages.clear()
            asyncio.run(continuity._show_recognition(session, return_meeting))
            first_count = len(session.messages)
            asyncio.run(continuity._show_recognition(session, return_meeting))
            self.assertEqual(len(session.messages), first_count)
            self.assertIn("familiar face", "".join(session.messages).lower())
            self.assertIn("remember", "".join(session.messages).lower())

            with patch.object(continuity, "ASTRALIS_CLOCK", DummyClock(return_meeting)):
                self.assertTrue(asyncio.run(depth._talk_visitor(session, "iven")))
            memory = continuity._memory_row(session, continuity.IVEN.key)
            self.assertEqual(int(memory["last_met_day"]), 5)
            self.assertEqual(int(memory["times_spoken"]), 2)

    def test_returning_visitor_can_acknowledge_a_players_temporary_board_mark(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Boardwalker")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()

            first_meeting = self._moment(2, 20)
            with patch.object(continuity, "ASTRALIS_CLOCK", DummyClock(first_meeting)):
                self.assertTrue(asyncio.run(depth._talk_visitor(session, "iven")))
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(first_meeting)):
                asyncio.run(depth._pin_note(session, "Looking for company for Gravewatch after dusk."))

            session.messages.clear()
            return_meeting = self._moment(5, 20)
            with patch.object(continuity, "ASTRALIS_CLOCK", DummyClock(return_meeting)):
                self.assertTrue(asyncio.run(depth._talk_visitor(session, "iven")))
            message = "".join(session.messages).lower()
            self.assertIn("last time", message)
            self.assertIn("note", message)
            # The visitor acknowledges the mark without quoting or modifying it.
            notes = depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 5)
            self.assertEqual(len(notes), 1)
            self.assertIn("Gravewatch", str(notes[0]["body"]))

    def test_continuity_schema_keeps_memory_separate_from_progression_rewards(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "NoReward")
            continuity.ensure_continuity_schema(session.database)
            with session.database.connect() as db:
                tables = {
                    row["name"]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'living_visitor_%'"
                    ).fetchall()
                }
            self.assertEqual(tables, {"living_visitor_memory", "living_visitor_recognition"})
            self.assertFalse(any("reward" in name for name in tables))

    def test_production_server_installs_continuity_inside_depth_and_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.living_world_depth as depth
from mud.living_world_continuity import LIVING_WORLD_CONTINUITY_VERSION, IVEN
assert LIVING_WORLD_CONTINUITY_VERSION == "1.0.0"
assert len(depth.DAILY_TEXTURES) >= 30
assert any(visitor.key == IVEN.key for visitor in depth.VISITORS)
assert server.PlayerSession._living_world_depth_runtime_installed
assert server.PlayerSession._living_world_continuity_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
print("LIVING_WORLD_CONTINUITY_OK")
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
        self.assertIn("LIVING_WORLD_CONTINUITY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
