"""Regression coverage for the world-wide living NPC layer."""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcManager
from mud.world import ROOMS_BY_KEY
from mud.world_living_npcs import (
    WORLD_LIVING_METADATA,
    WORLD_LIVING_PREFIX,
    WorldLivingChatterDirector,
    chatter_lines,
    install_world_living_talk_runtime,
    register_world_living_npcs,
)


ROOT = Path(__file__).resolve().parents[1]


class WorldLivingNpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = register_world_living_npcs()

    def test_world_registration_creates_safe_scheduled_residents(self):
        self.assertTrue(self.generated)
        self.assertEqual(len({npc.key for npc in self.generated}), len(self.generated))
        self.assertEqual(len({npc.name for npc in self.generated}), len(self.generated))

        manager = MobileNpcManager(definitions=self.generated)
        manager.validate_definitions()

        for npc in self.generated:
            self.assertTrue(npc.key.startswith(WORLD_LIVING_PREFIX))
            self.assertEqual(npc.behavior, BEHAVIOR_ROUTINE)
            self.assertIn(npc.key, WORLD_LIVING_METADATA)
            self.assertGreaterEqual(len(npc.routine_schedule), 5)
            self.assertTrue(all(stop.room_key in npc.allowed_room_keys for stop in npc.routine_schedule))
            self.assertTrue(all(room_key in ROOMS_BY_KEY for room_key in npc.allowed_room_keys))
            self.assertFalse(any(ROOMS_BY_KEY[key].enemy_keys for key in npc.allowed_room_keys))

    def test_registration_is_idempotent(self):
        first = tuple(npc.key for npc in register_world_living_npcs())
        second = tuple(npc.key for npc in register_world_living_npcs())
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))

    def test_schedule_moves_on_existing_exits(self):
        actor = self.generated[0]
        manager = MobileNpcManager(definitions=(actor,))
        for hour in (6, 9, 13, 18, 22):
            for _ in range(20):
                manager.tick(
                    rng=random.Random(4),
                    hour=hour,
                    weather_provider=lambda _region: "clear",
                )
            expected = manager._routine_destination(actor, hour)
            self.assertEqual(manager.states[actor.key].current_room_key, expected)

    def test_chatter_requires_physical_presence_and_is_throttled(self):
        actor = self.generated[0]
        manager = MobileNpcManager(definitions=(actor,))
        room_key = actor.spawn_room_key
        lines = chatter_lines(manager, room_key, 10, "clear", rng=random.Random(2))
        self.assertTrue(lines)
        self.assertIn(actor.name, " ".join(lines))

        other_room = next(
            key for key in ROOMS_BY_KEY
            if key not in actor.allowed_room_keys
        )
        self.assertEqual(chatter_lines(manager, other_room, 10, "clear"), ())

        director = WorldLivingChatterDirector(cooldown_seconds=100)
        self.assertTrue(director.due_lines(
            manager, room_key, 10, "clear", now=100, rng=random.Random(2),
        ))
        self.assertEqual(
            director.due_lines(
                manager, room_key, 10, "clear", now=150, rng=random.Random(2),
            ),
            (),
        )


class _DummyWorldState:
    def weather_for(self, _region):
        return "rain"


class _DummyWorld:
    state = _DummyWorldState()


class _DummySession:
    def __init__(self, manager, room_key):
        self.character = SimpleNamespace(current_room=room_key)
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


class WorldLivingTalkTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_local_can_be_talked_to(self):
        actor = register_world_living_npcs()[0]
        manager = MobileNpcManager(definitions=(actor,))
        Session = type("WorldLivingSession", (_DummySession,), {})
        install_world_living_talk_runtime(Session, _DummyWorld())

        session = Session(manager, actor.spawn_room_key)
        session.input_line = "talk " + actor.aliases[0]
        await session.playing_prompt()

        text = "".join(session.sent)
        self.assertIn(actor.name + " says", text)
        self.assertIn(actor.name + " adds", text)
        self.assertFalse(session.delegated)

    async def test_unrelated_talk_delegates(self):
        actor = register_world_living_npcs()[0]
        manager = MobileNpcManager(definitions=(actor,))
        Session = type("WorldLivingDelegateSession", (_DummySession,), {})
        install_world_living_talk_runtime(Session, _DummyWorld())

        session = Session(manager, actor.spawn_room_key)
        session.input_line = "talk somebody-else"
        await session.playing_prompt()
        self.assertTrue(session.delegated)


class ProductionWorldLivingTests(unittest.TestCase):
    def test_production_server_registers_and_runs_world_living_layer(self):
        script = """
import server
from mud.world_living_npcs import WORLD_LIVING_METADATA
assert server.PlayerSession._world_living_talk_installed
assert server._WORLD_LIVING_NPCS
assert WORLD_LIVING_METADATA
game = server.MudServer(host="127.0.0.1", port=0)
assert all(actor.key in game.mobile_npcs.states for actor in server._WORLD_LIVING_NPCS)
print("WORLD_LIVING_OK", len(server._WORLD_LIVING_NPCS))
"""
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env={**os.environ, "MUD_DB_PATH": str(Path(td) / "probe.db")},
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WORLD_LIVING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
