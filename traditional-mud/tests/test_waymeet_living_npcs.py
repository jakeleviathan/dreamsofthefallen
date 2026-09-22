from __future__ import annotations

import os
import random
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.astralis_time import AstralisClock, AstralisWeatherService, REAL_EPOCH_SECONDS
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcManager
from mud.room_engine import RoomStateStore
from mud.world_data import REGIONS_BY_KEY
from mud.waymeet_frontier import (
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_WEST_ROAD_KEY,
    install_waymeet_content,
)
from mud.waymeet_living_npcs import (
    BELREK,
    EDRIN,
    LESSA,
    SUVVI,
    WAYMEET_LIVING_NPCS,
    WaymeetChatterDirector,
    chatter_lines,
    install_waymeet_living_talk_runtime,
    phase_at,
    register_waymeet_living_npcs,
    resolve_waymeet_talk,
    talk_lines,
)

ROOT = Path(__file__).resolve().parents[1]


class WaymeetLivingNpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_waymeet_content()

    def _manager(self, *definitions):
        return MobileNpcManager(definitions=definitions or WAYMEET_LIVING_NPCS)

    def test_four_unique_residents_have_real_legal_routes_and_daily_schedules(self):
        self.assertEqual(len(WAYMEET_LIVING_NPCS), 4)
        self.assertEqual(len({npc.name for npc in WAYMEET_LIVING_NPCS}), 4)
        manager = self._manager()
        manager.validate_definitions()
        for npc in WAYMEET_LIVING_NPCS:
            self.assertEqual(npc.behavior, BEHAVIOR_ROUTINE)
            self.assertGreaterEqual(len(npc.routine_schedule), 5)
            self.assertIn(npc.key, manager.states)
            self.assertTrue(all(stop.room_key in npc.allowed_room_keys for stop in npc.routine_schedule))
        register_waymeet_living_npcs()  # repeat registration never creates duplicates
        self.assertEqual(len({npc.key for npc in WAYMEET_LIVING_NPCS}), 4)

    def test_waymeet_has_real_regional_weather_for_sheltering(self):
        self.assertIn("waymeet_frontier", REGIONS_BY_KEY)
        state = RoomStateStore()
        weather = AstralisWeatherService(rng=random.Random(7))
        weather.initialize(AstralisClock().now(REAL_EPOCH_SECONDS), state)
        self.assertEqual(state.weather_for("waymeet_frontier"), "clear")

    def test_world_hour_moves_a_dispatcher_along_existing_exits(self):
        manager = self._manager(EDRIN)
        self.assertEqual(manager._routine_destination(EDRIN, 6), WAYMEET_WEST_ROAD_KEY)
        self.assertEqual(manager._routine_destination(EDRIN, 9), WAYMEET_CROSSROADS_KEY)
        self.assertEqual(manager._routine_destination(EDRIN, 12), WAYMEET_LANTERN_MARKET_KEY)
        self.assertEqual(manager._routine_destination(EDRIN, 23), WAYMEET_COMMONHOUSE_KEY)
        movement = manager.tick(
            rng=random.Random(4), hour=6, weather_provider=lambda _: "clear",
        )
        self.assertEqual(manager.states[EDRIN.key].current_room_key, WAYMEET_WEST_ROAD_KEY)
        self.assertTrue(any(move.npc_key == EDRIN.key and move.reason == "schedule" for move in movement))
        manager.tick(rng=random.Random(4), hour=9, weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[EDRIN.key].current_room_key, WAYMEET_CROSSROADS_KEY)

    def test_storm_drives_dispatcher_to_shelter_then_back_to_work(self):
        manager = self._manager(EDRIN)
        manager.states[EDRIN.key].current_room_key = WAYMEET_WEST_ROAD_KEY
        for _ in range(6):
            manager.tick(rng=random.Random(2), hour=9, weather_provider=lambda _: "storm")
        self.assertEqual(manager.states[EDRIN.key].current_room_key, WAYMEET_COMMONHOUSE_KEY)
        for _ in range(6):
            manager.tick(rng=random.Random(2), hour=9, weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[EDRIN.key].current_room_key, WAYMEET_CROSSROADS_KEY)

    def test_overheard_exchange_requires_both_npcs_in_same_room(self):
        manager = self._manager(EDRIN, SUVVI)
        manager.states[SUVVI.key].current_room_key = WAYMEET_CROSSROADS_KEY
        lines = chatter_lines(
            manager, WAYMEET_CROSSROADS_KEY, 10, "clear", rng=random.Random(3),
        )
        self.assertEqual(len(lines), 2)
        self.assertIn("Edrin", " ".join(lines))
        self.assertIn("Suvvi", " ".join(lines))
        manager.states[SUVVI.key].current_room_key = WAYMEET_LANTERN_MARKET_KEY
        lines = chatter_lines(
            manager, WAYMEET_CROSSROADS_KEY, 10, "clear", rng=random.Random(3),
        )
        self.assertNotIn("Suvvi", " ".join(lines))
        self.assertEqual(
            chatter_lines(manager, "some_other_city", 10, "clear"), (),
        )

    def test_cooldown_is_per_room_and_does_not_emit_without_residents(self):
        manager = self._manager(EDRIN, SUVVI)
        director = WaymeetChatterDirector(cooldown_seconds=100)
        first = director.due_lines(
            manager, WAYMEET_CROSSROADS_KEY, 9, "rain", now=200, rng=random.Random(0),
        )
        self.assertTrue(first)
        self.assertEqual(
            director.due_lines(
                manager, WAYMEET_CROSSROADS_KEY, 9, "rain", now=240, rng=random.Random(0),
            ),
            (),
        )
        self.assertTrue(
            director.due_lines(
                manager, WAYMEET_CROSSROADS_KEY, 9, "rain", now=310, rng=random.Random(0),
            )
        )
        self.assertEqual(
            director.due_lines(
                manager, WAYMEET_COMMONHOUSE_KEY, 9, "rain", now=310,
            ),
            (),
        )

    def test_talk_respects_visibility_and_weather_and_world_hour(self):
        manager = self._manager(EDRIN, SUVVI)
        resident, ambiguous = resolve_waymeet_talk(
            manager, WAYMEET_LANTERN_MARKET_KEY, "to suvvi".removeprefix("to "),
        )
        self.assertEqual(resident, SUVVI)
        self.assertFalse(ambiguous)
        missing, _ = resolve_waymeet_talk(manager, WAYMEET_CROSSROADS_KEY, "suvvi")
        self.assertIsNone(missing)
        self.assertEqual(phase_at(6), "dawn")
        self.assertEqual(phase_at(14), "day")
        self.assertEqual(phase_at(19), "dusk")
        self.assertEqual(phase_at(23), "night")
        rainy = talk_lines(EDRIN, 9, "rain")
        dry = talk_lines(EDRIN, 9, "clear")
        self.assertEqual(len(rainy), 2)
        self.assertEqual(len(dry), 1)
        self.assertIn("bridges", rainy[1])


class _DummySession:
    def __init__(self, manager):
        self.character = SimpleNamespace(current_room=WAYMEET_LANTERN_MARKET_KEY)
        self.mobile_npcs = manager
        self.input_line = ""
        self.sent = []
        self.delegated = False
        self.state = SimpleNamespace(DISCONNECTED="disconnected")

    async def prompt(self, _text):
        return self.input_line

    async def send(self, text):
        self.sent.append(text)

    async def playing_prompt(self):
        self.delegated = True
        await self.send("Passed to existing quest and conversation handlers.\r\n")


class WaymeetTalkRuntimeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_waymeet_content()

    async def test_talk_to_visible_resident_and_preserve_existing_quest_handlers(self):
        manager = MobileNpcManager(definitions=(EDRIN, SUVVI))
        Session = type("WaymeetTalkSession", (_DummySession,), {})
        install_waymeet_living_talk_runtime(Session)

        session = Session(manager)
        session.input_line = "talk to suvvi"
        await session.playing_prompt()
        self.assertIn("Suvvi Rainpenny says", "".join(session.sent))
        self.assertFalse(session.delegated)

        other = Session(manager)
        other.input_line = "talk marshal"
        await other.playing_prompt()
        self.assertTrue(other.delegated)

        absent = Session(manager)
        absent.character.current_room = WAYMEET_CROSSROADS_KEY
        absent.input_line = "talk suvvi"
        await absent.playing_prompt()
        self.assertTrue(absent.delegated)


class ProductionWaymeetRegistrationTests(unittest.TestCase):
    def test_main_server_registers_waymeet_cast_and_installs_talk_runtime(self):
        script = """
import server
from mud.waymeet_living_npcs import WAYMEET_LIVING_NPCS
from mud.npcs import MOBILE_NPCS_BY_KEY
from mud.world import ROOMS_BY_KEY
assert server.PlayerSession._waymeet_living_talk_installed
assert all(actor.key in MOBILE_NPCS_BY_KEY for actor in WAYMEET_LIVING_NPCS)
assert all(set(actor.allowed_room_keys).issubset(ROOMS_BY_KEY) for actor in WAYMEET_LIVING_NPCS)
game = server.MudServer(host="127.0.0.1", port=0)
assert all(actor.key in game.mobile_npcs.states for actor in WAYMEET_LIVING_NPCS)
print("WAYMEET_LIVING_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WAYMEET_LIVING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
