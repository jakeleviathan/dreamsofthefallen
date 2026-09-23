"""Brassgut's living cast follows the shared NPC engine without breaking quests."""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.brassgut_living_npcs import (
    BRASSGUT_LIVING_NPCS,
    BRASSGUT_KEYS,
    CHATTER_ROOMS,
    HADRIK,
    JEX,
    RUSKLE,
    TRESSA,
    BrassgutChatterDirector,
    BrassgutMemoryStore,
    chatter_lines,
    install_brassgut_living_talk_runtime,
    register_brassgut_living_npcs,
    resolve_brassgut_talk,
    residents_here,
    static_contact_visible,
    talk_lines,
)
from mud.database import Database
from mud.goblin_clans import install_goblin_clan_content
from mud.goblin_rattlefen_opening import install_rattlefen_opening_content
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY as MARKET,
    GOBLIN_FLOODGATE_WALK_KEY as FLOODGATE,
    GOBLIN_LEDGER_HALL_KEY as LEDGER,
    GOBLIN_PATCHWORK_PLAZA_KEY as PLAZA,
    GOBLIN_SORTING_SPINE_KEY as SORTING,
    GOBLIN_TINKER_ROW_KEY as TINKER,
    install_goblin_world,
)
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcManager
from mud.room_prompt_experience import _npc_lines
from mud.world import ROOMS_BY_KEY


ROOT = Path(__file__).resolve().parents[1]


class BrassgutLivingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_goblin_world()
        install_goblin_clan_content()
        install_rattlefen_opening_content()

    def _manager(self, *cast):
        return MobileNpcManager(definitions=cast or BRASSGUT_LIVING_NPCS)

    def test_existing_four_people_share_canonical_quest_keys_and_safe_routes(self):
        self.assertEqual(len(BRASSGUT_LIVING_NPCS), 4)
        self.assertEqual(len(BRASSGUT_KEYS), 4)
        self.assertEqual({npc.name for npc in BRASSGUT_LIVING_NPCS},
                         {"Ruskle Coil", "Jex Mirehook", "Hadrik Coilpress", "Tressa Vale"})
        manager = self._manager()
        manager.validate_definitions()
        for npc in BRASSGUT_LIVING_NPCS:
            self.assertEqual(npc.behavior, BEHAVIOR_ROUTINE)
            self.assertIn(npc.key, manager.states)
            self.assertTrue(all(stop.room_key in ROOMS_BY_KEY for stop in npc.routine_schedule))
        register_brassgut_living_npcs()
        register_brassgut_living_npcs()  # idempotent
        self.assertEqual(len(BRASSGUT_KEYS), 4)

    def test_jex_checks_floodgate_then_returns_to_market(self):
        manager = self._manager(JEX)
        for _ in range(6):
            manager.tick(hour=5, rng=random.Random(0), weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[JEX.key].current_room_key, FLOODGATE)
        self.assertFalse(static_contact_visible(manager, JEX.key, MARKET))
        for _ in range(6):
            manager.tick(hour=9, rng=random.Random(0), weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[JEX.key].current_room_key, MARKET)
        self.assertTrue(static_contact_visible(manager, JEX.key, MARKET))

    def test_weather_shelter_and_resumed_daily_work(self):
        manager = self._manager(HADRIK)
        for _ in range(6):
            manager.tick(hour=11, rng=random.Random(0), weather_provider=lambda _: "storm")
        self.assertEqual(manager.states[HADRIK.key].current_room_key, LEDGER)
        for _ in range(6):
            manager.tick(hour=11, rng=random.Random(0), weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[HADRIK.key].current_room_key, TINKER)

    def test_only_physically_colocated_npcs_have_conversations(self):
        manager = self._manager(RUSKLE, JEX)
        dialogue = chatter_lines(manager, MARKET, 100, 10, "clear", rng=random.Random(1))
        self.assertEqual(len(dialogue), 2)
        self.assertIn("Ruskle", " ".join(dialogue))
        self.assertIn("Jex", " ".join(dialogue))
        manager.states[JEX.key].current_room_key = FLOODGATE
        dialogue = chatter_lines(manager, MARKET, 100, 10, "clear", rng=random.Random(1))
        self.assertNotIn("Jex", " ".join(dialogue))
        self.assertEqual(chatter_lines(manager, "veyra", 100, 10, "clear"), ())
        self.assertFalse(residents_here(manager, "veyra"))

    def test_chatter_is_throttled_per_room(self):
        manager = self._manager(RUSKLE, JEX)
        director = BrassgutChatterDirector(cooldown_seconds=90)
        self.assertTrue(director.due_lines(
            manager, MARKET, 100, 10, "clear", now=100, rng=random.Random(1),
        ))
        self.assertEqual(director.due_lines(
            manager, MARKET, 100, 10, "clear", now=110, rng=random.Random(1),
        ), ())
        self.assertTrue(director.due_lines(
            manager, MARKET, 100, 10, "clear", now=191, rng=random.Random(1),
        ))

    def test_relationship_memory_survives_restart_and_changes_next_day(self):
        with tempfile.TemporaryDirectory() as td:
            db = Database(Path(td) / "mud.db")
            manager = self._manager(RUSKLE, JEX)
            first = chatter_lines(
                manager, MARKET, 100, 10, "clear",
                memory=BrassgutMemoryStore(db), rng=random.Random(1),
            )
            later_today = chatter_lines(
                manager, MARKET, 100, 10, "clear",
                memory=BrassgutMemoryStore(db), rng=random.Random(1),
            )
            tomorrow = chatter_lines(
                manager, MARKET, 101, 10, "clear",
                memory=BrassgutMemoryStore(db), rng=random.Random(1),
            )
            self.assertIn("same useful hinge", " ".join(first))
            self.assertIn("No double claims today", " ".join(later_today))
            self.assertIn("yesterday", " ".join(tomorrow))
            with db.connect() as conn:
                memory = conn.execute("SELECT encounters, rapport FROM brassgut_relationships").fetchone()
            self.assertEqual(memory["encounters"], 2)
            self.assertEqual(memory["rapport"], 0)

    def test_mobile_talk_respects_visibility_and_weather(self):
        manager = self._manager(JEX, TRESSA)
        jex, ambiguous = resolve_brassgut_talk(manager, MARKET, "jex")
        self.assertEqual(jex, JEX)
        self.assertFalse(ambiguous)
        self.assertIsNone(resolve_brassgut_talk(manager, PLAZA, "jex")[0])
        self.assertEqual(len(talk_lines(TRESSA, 9, "rain")), 2)
        self.assertEqual(len(talk_lines(TRESSA, 9, "clear")), 1)
        self.assertTrue(CHATTER_ROOMS)

    def test_market_static_placeholder_disappears_while_npc_is_out(self):
        manager = self._manager(JEX)
        session = SimpleNamespace(mobile_npcs=manager,
                                  character=SimpleNamespace(current_room=MARKET))
        scene = SimpleNamespace(key=MARKET, npc_keys=(JEX.key,))
        self.assertIn("Jex", " ".join(_npc_lines(session, scene)))
        manager.states[JEX.key].current_room_key = FLOODGATE
        self.assertNotIn("Jex", " ".join(_npc_lines(session, scene)))
        self.assertIn("Jex", " ".join(_npc_lines(
            SimpleNamespace(mobile_npcs=manager,
                            character=SimpleNamespace(current_room=FLOODGATE)),
            SimpleNamespace(key=FLOODGATE, npc_keys=()),
        )))


class _DummySession:
    def __init__(self, manager, database, room=MARKET):
        self.character = SimpleNamespace(current_room=room, id=1, name="Tester")
        self.mobile_npcs = manager
        self.database = database
        self.input_line = ""
        self.sent = []
        self.delegated = False
        self.state = SimpleNamespace(DISCONNECTED="disconnected")

    async def prompt(self, _prompt):
        return self.input_line

    async def send(self, msg):
        self.sent.append(msg)

    async def playing_prompt(self):
        self.delegated = True


class BrassgutTalkTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_goblin_world()
        install_goblin_clan_content()
        install_rattlefen_opening_content()

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "mud.db")
        with self.db.connect() as db:
            db.execute("INSERT INTO accounts (name, password_hash) VALUES ('local', 'hash')")
            db.execute("INSERT INTO characters (account_id, name) VALUES (1, 'Tester')")
        self.manager = MobileNpcManager(definitions=(RUSKLE, JEX, HADRIK, TRESSA))
        self.Session = type("BrassgutTalkSession", (_DummySession,), {})
        install_brassgut_living_talk_runtime(self.Session)

    async def test_market_talk_preserves_existing_quest_handler(self):
        player = self.Session(self.manager, self.db)
        player.input_line = "talk ruskle"
        with patch("mud.brassgut_living_npcs.ASTRALIS_CLOCK") as clock:
            clock.now.return_value = SimpleNamespace(day_number=100, hour=9)
            await player.playing_prompt()
        self.assertTrue(player.delegated)
        self.assertEqual(len(player.sent), 0)

    async def test_absent_market_actor_is_not_a_ghost_quest_giver(self):
        self.manager.states[JEX.key].current_room_key = FLOODGATE
        player = self.Session(self.manager, self.db)
        player.input_line = "talk jex"
        await player.playing_prompt()
        self.assertFalse(player.delegated)
        self.assertIn("out on their rounds", " ".join(player.sent))

    async def test_talking_on_route_does_not_consume_market_quest(self):
        self.manager.states[JEX.key].current_room_key = FLOODGATE
        player = self.Session(self.manager, self.db, FLOODGATE)
        player.input_line = "talk jex"
        with patch("mud.brassgut_living_npcs.ASTRALIS_CLOCK") as clock:
            clock.now.return_value = SimpleNamespace(day_number=100, hour=5)
            await player.playing_prompt()
        self.assertFalse(player.delegated)
        self.assertIn("Jex Mirehook says", " ".join(player.sent))

    async def test_remembers_previous_visit_across_world_days(self):
        player = self.Session(self.manager, self.db)
        player.input_line = "talk ruskle"
        with patch("mud.brassgut_living_npcs.ASTRALIS_CLOCK") as clock:
            clock.now.return_value = SimpleNamespace(day_number=100, hour=9)
            await player.playing_prompt()
            clock.now.return_value = SimpleNamespace(day_number=101, hour=9)
            await player.playing_prompt()
        self.assertIn("Back again, Tester", " ".join(player.sent))


class ProductionBrassgutTests(unittest.TestCase):
    def test_assembled_server_has_shared_memory_and_four_living_residents(self):
        script = """
import server
from mud.brassgut_living_npcs import BRASSGUT_LIVING_NPCS, BrassgutMemoryStore
from mud.npcs import MOBILE_NPCS_BY_KEY
from mud.world import ROOMS_BY_KEY
assert server.PlayerSession._brassgut_living_talk_installed
assert all(actor.key in MOBILE_NPCS_BY_KEY for actor in BRASSGUT_LIVING_NPCS)
assert all(set(actor.allowed_room_keys).issubset(ROOMS_BY_KEY) for actor in BRASSGUT_LIVING_NPCS)
game = server.MudServer(host="127.0.0.1", port=0)
assert all(actor.key in game.mobile_npcs.states for actor in BRASSGUT_LIVING_NPCS)
BrassgutMemoryStore(game.database)
print("BRASSGUT_LIVING_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=ROOT,
            env={**os.environ, "MUD_DB_PATH": ":memory:"},
            capture_output=True, text=True, timeout=100,
            check=False,
        )
        # The main server uses an on-disk DB because room state spans several
        # connections. This probe verifies import and assembly independently.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("BRASSGUT_LIVING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
