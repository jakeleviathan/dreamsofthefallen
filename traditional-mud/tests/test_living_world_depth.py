from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.living_world as living
import mud.living_world_depth as depth
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.mechanics import CombatantState
from mud.veyra_city import VEYRA_BRASSMARKET_KEY
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_LANTERN_MARKET_KEY, WAYMEET_SCRIP_KEY


class DummyClock:
    def __init__(self, moment: AstralisMoment) -> None:
        self.moment = moment

    def now(self, real_seconds=None) -> AstralisMoment:
        return self.moment


class DummyTelnet:
    def __init__(self) -> None:
        self.gmcp_enabled = True
        self.packets: list[tuple[str, dict]] = []

    async def send_gmcp(self, package: str, payload: dict) -> bool:
        self.packets.append((package, payload))
        return True


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []
        self.telnet = DummyTelnet()
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


class LivingWorldDepthTests(unittest.TestCase):
    def _session(self, root: Path, name: str = "Roadwatcher") -> DummySession:
        database = Database(root / "living_depth.db")
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

    def test_daily_texture_library_is_dense_deterministic_and_multicultural(self):
        self.assertGreaterEqual(len(depth.DAILY_TEXTURES), 20)
        first = depth.texture_for_day(123)
        second = depth.texture_for_day(123)
        self.assertEqual(first, second)
        seen = {depth.texture_for_day(day).category for day in range(1, 400)}
        self.assertGreaterEqual(len(seen), 6)
        rooms = {texture.room_key for texture in depth.DAILY_TEXTURES}
        self.assertIn(WAYMEET_COMMONHOUSE_KEY, rooms)
        self.assertIn(VEYRA_BRASSMARKET_KEY, rooms)

    def test_recurring_people_keep_real_schedules_and_hesta_is_weekly(self):
        # Day 4 is Hesta's one weekly circuit day because weekday index == 3.
        hesta_morning = self._moment(4, 9)
        hesta_afternoon = self._moment(4, 14)
        next_day = self._moment(5, 9)
        self.assertEqual(depth._scheduled_location(depth.HESTA, hesta_morning), WAYMEET_LANTERN_MARKET_KEY)
        self.assertEqual(depth._scheduled_location(depth.HESTA, hesta_afternoon), VEYRA_BRASSMARKET_KEY)
        self.assertIsNone(depth._scheduled_location(depth.HESTA, next_day))

        pell_day = self._moment(1, 10)
        pell_night = self._moment(1, 19)
        self.assertEqual(depth._scheduled_location(depth.PELL, pell_day), WAYMEET_LANTERN_MARKET_KEY)
        self.assertEqual(depth._scheduled_location(depth.PELL, pell_night), WAYMEET_COMMONHOUSE_KEY)

    def test_weekly_factor_sells_only_ordinary_existing_materials_for_scrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Buyer")
            moment = self._moment(4, 9)
            session.database.set_character_room(session.character.id, WAYMEET_LANTERN_MARKET_KEY)
            session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 4)
            session.refresh()
            wares = depth._weekly_wares(moment.day_number)
            item_key, cost = wares[0]
            self.assertIn(item_key, __import__("mud.crafting", fromlist=["ITEMS_BY_KEY"]).ITEMS_BY_KEY)
            before_scrip = session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(moment)):
                self.assertTrue(asyncio.run(depth._browse_hesta(session)))
                self.assertTrue(asyncio.run(depth._buy_hesta(session, living._item_label(item_key))))
            self.assertEqual(session.database.item_quantity(session.character.id, item_key), 1)
            self.assertEqual(
                session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY),
                before_scrip - cost,
            )

    def test_multi_day_arc_has_authored_progression_and_becomes_chronicle_history(self):
        state1 = depth.arc_state(1)
        state2 = depth.arc_state(2)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)
        arc1, stage1, index1, cycle1 = state1
        arc2, stage2, index2, cycle2 = state2
        self.assertEqual(arc1.key, arc2.key)
        self.assertEqual(cycle1, cycle2)
        self.assertEqual(index1, 0)
        self.assertEqual(index2, 1)
        self.assertNotEqual(stage1.dispatch, stage2.dispatch)
        self.assertGreaterEqual(len(arc1.stages), 6)

        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Historian")
            final_day = len(arc1.stages)
            depth._record_arc_history(session.database, self._moment(final_day))
            entries = living.latest_chronicle(session.database, 20)
            texts = [str(row["entry_text"]) for row in entries]
            self.assertIn(arc1.start_record, texts)
            self.assertIn(arc1.resolution_record, texts)

    def test_player_board_notes_are_short_local_expiring_and_rate_limited(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Noteleaver")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()
            day10 = self._moment(10, 18)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(day10)):
                asyncio.run(depth._pin_note(session, "Looking for a smith for a road shield."))
                asyncio.run(depth._pin_note(session, "This second note should be rate limited."))
            rows = depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["character_name"], "Noteleaver")
            self.assertEqual(int(rows[0]["expires_day"]), 16)
            self.assertIn("breathing room", "".join(session.messages).lower())

            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(self._moment(13, 18))):
                asyncio.run(depth._pin_note(session, "Three days later, this one is allowed."))
            rows = depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 13)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 17)), 1)

    def test_board_notes_reject_external_links_and_control_sequences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "SafeNote")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()
            moment = self._moment(20, 18)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(depth._pin_note(session, "visit https://example.com for loot"))
            self.assertEqual(depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 20), [])
            self.assertIn("external links", "".join(session.messages).lower())
            self.assertNotIn("\x1b", depth._clean_note("hello\x1b[31m world"))

    def test_keeper_can_repeat_player_marks_or_public_chronicle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Rumormaker")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()
            moment = self._moment(30, 18)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(depth._pin_note(session, "Need two travelers for the old road after dusk."))
                asyncio.run(depth._keeper_rumor(session))
            message = "".join(session.messages)
            self.assertIn("Need two travelers", message)
            self.assertIn("Rumormaker", message)

    def test_ambient_scene_is_seen_only_once_per_character_per_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Observer")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()
            moment = self._moment(50, 22)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(depth._show_ambient_once(session, moment))
                count_after_first = len(session.messages)
                asyncio.run(depth._show_ambient_once(session, moment))
            # There can be more than one eligible scene in a room, but each exact
            # scene is one-shot. Repeated LOOKs never replay the same scene key.
            self.assertGreaterEqual(count_after_first, 1)
            with session.database.connect() as db:
                rows = db.execute(
                    "SELECT scene_key, COUNT(*) AS n FROM living_depth_seen WHERE character_id = ? AND astralis_day = ? GROUP BY scene_key",
                    (session.character.id, moment.day_number),
                ).fetchall()
            self.assertTrue(rows)
            self.assertTrue(all(int(row["n"]) == 1 for row in rows))

    def test_world_texture_gmcp_exposes_nudge_arc_visitors_and_board_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "MudletUser")
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()
            moment = self._moment(1, 19)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(depth._push_depth_gmcp(session))
            packet = next(payload for package, payload in session.telnet.packets if package == "Dreams.WorldTexture")
            self.assertTrue(packet["nudge"])
            self.assertIsNotNone(packet["arc"])
            self.assertIn("Pell Roadsong", packet["visitors_here"])
            self.assertEqual(packet["board_notes_here"], 0)

    def test_production_server_installs_depth_between_living_world_and_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.living_world_depth import LIVING_WORLD_DEPTH_VERSION, DAILY_TEXTURES, WORLD_ARCS
assert LIVING_WORLD_DEPTH_VERSION == "1.0.0"
assert len(DAILY_TEXTURES) >= 20
assert len(WORLD_ARCS) >= 4
assert server.PlayerSession._living_world_runtime_installed
assert server.PlayerSession._living_world_depth_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
print("LIVING_WORLD_DEPTH_OK")
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
        self.assertIn("LIVING_WORLD_DEPTH_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
