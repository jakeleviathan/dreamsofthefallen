from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import unittest

import mud.veilith as veilith
from mud.salt_kingdoms_midgame import TIDEMARK_SINK_KEY


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Character:
    id: int = 1
    name: str = "Prime"
    level: int = 25
    current_room: str = TIDEMARK_SINK_KEY


class MemoryDatabase:
    def __init__(self):
        self.flags = set()
        self.items = {}
        self.room = TIDEMARK_SINK_KEY
        self.consumptions = 0

    def list_flags(self, _id):
        return frozenset(self.flags)

    def grant_flag(self, _id, flag):
        self.flags.add(flag)

    def set_character_room(self, _id, room):
        self.room = room

    def item_quantity(self, _id, item_key):
        return self.items.get(item_key, 0)

    def add_item(self, _id, item_key, amount=1):
        self.items[item_key] = self.items.get(item_key, 0) + amount

    def consume_item(self, _id, item_key, amount=1):
        if self.item_quantity(_id, item_key) < amount:
            return False
        self.items[item_key] -= amount
        self.consumptions += 1
        return True


class World:
    def __init__(self):
        self.legacy_rooms = {}
        self._scene_cache = {}


class Session:
    def __init__(self):
        self.character = Character()
        self.database = MemoryDatabase()
        self.messages = []
        self.next_command = ""
        self.active_enemy = None
        self.state = "playing"

    async def prompt(self, _prompt):
        return self.next_command

    async def send(self, text):
        self.messages.append(text)

    async def enter_character(self):
        return None

    async def show_current_room(self):
        self.messages.append("BASE ROOM\r\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.messages.append("DELEGATED:" + command)


WORLD = World()
veilith.install_veilith_runtime(Session, WORLD)


def step(session, command):
    session.next_command = command
    asyncio.run(session.playing_prompt())
    return "".join(session.messages)


class VeilithOpeningTests(unittest.TestCase):
    def test_real_registered_rooms_have_no_npcs_or_combat_and_are_not_public_exits(self):
        self.assertEqual(len(veilith.ROOMS), 4)
        self.assertEqual(set(veilith.ROOM_KEYS), {room.key for room in veilith.ROOMS})
        self.assertTrue(all(not room.npc_keys and not room.enemy_keys for room in veilith.ROOMS))
        self.assertTrue(all(not room.exits for room in veilith.ROOMS))
        for room in veilith.ROOMS:
            self.assertIn(room.key, WORLD.legacy_rooms)
        self.assertEqual(veilith.DRAUGHT.category, "recreational")
        self.assertIsNone(veilith.DRAUGHT.consumable)
        self.assertIsNone(veilith.DRAUGHT.equipment)

    def test_discovery_requires_level_25(self):
        session = Session()
        session.character = Character(level=24)
        step(session, "examine crack")
        self.assertNotIn(veilith.DISCOVERED_LAB_FLAG, session.database.flags)
        step(session, "enter crack")
        self.assertEqual(session.character.current_room, TIDEMARK_SINK_KEY)

    def test_brewing_requires_research_and_cannot_stack_unused_doses(self):
        session = Session()
        step(session, "search crack")
        step(session, "enter crack")
        step(session, "prepare draught")
        self.assertEqual(session.database.item_quantity(1, veilith.DRAUGHT_KEY), 0)
        step(session, "read notes")
        step(session, "prepare draught")
        step(session, "prepare draught")
        self.assertEqual(session.database.item_quantity(1, veilith.DRAUGHT_KEY), 1)
        self.assertEqual(session.character.current_room, veilith.LAB_KEY)

    def test_full_playthrough_permanent_attunement_and_safe_puzzle_reset(self):
        session = Session()
        step(session, "search salt")
        self.assertIn(veilith.DISCOVERED_LAB_FLAG, session.database.flags)
        step(session, "enter crack")
        self.assertEqual(session.character.current_room, veilith.LAB_KEY)
        step(session, "enter seam")
        self.assertEqual(session.character.current_room, veilith.LAB_KEY)
        step(session, "read notes")
        step(session, "brew draught")
        step(session, "drink dreamless draught")
        self.assertEqual(session.database.consumptions, 1)
        step(session, "examine wall")
        self.assertIn("lavender light", "".join(session.messages))
        step(session, "enter seam")
        self.assertEqual(session.character.current_room, veilith.FIELD_KEY)
        self.assertIn(veilith.ENTERED_FLAG, session.database.flags)

        step(session, "read marker")
        self.assertIn("WAYMET", "".join(session.messages))
        step(session, "examine flowers")
        self.assertIn("Prime", "".join(session.messages))
        step(session, "listen")
        self.assertIn("heartbeat", "".join(session.messages))
        step(session, "east")
        self.assertEqual(session.character.current_room, veilith.FIELD_KEY)
        step(session, "wait")
        step(session, "east")
        self.assertEqual(session.character.current_room, veilith.CAUSEWAY_KEY)
        step(session, "east")  # Hurrying is harmless and sends you back.
        self.assertEqual(session.character.current_room, veilith.FIELD_KEY)
        self.assertNotIn(veilith.ATTUNED_FLAG, session.database.flags)
        step(session, "wait")
        step(session, "east")
        step(session, "wait")
        step(session, "east")
        self.assertEqual(session.character.current_room, veilith.STILLPOINT_KEY)
        self.assertIn(veilith.ATTUNED_FLAG, session.database.flags)

        step(session, "return")
        self.assertEqual(session.character.current_room, veilith.LAB_KEY)
        session._veilith_perception_until = 0.0
        step(session, "enter seam")
        self.assertEqual(session.character.current_room, veilith.FIELD_KEY)
        self.assertEqual(session.database.consumptions, 1)

    def test_session_timing_is_reset_at_login_but_progress_is_persistent(self):
        session = Session()
        session.database.flags.add(veilith.ATTUNED_FLAG)
        session._veilith_perception_until = float("inf")
        session._veilith_field_ready = True
        asyncio.run(session.enter_character())
        self.assertEqual(session._veilith_perception_until, 0.0)
        self.assertFalse(session._veilith_field_ready)
        self.assertIn(veilith.ATTUNED_FLAG, session.database.flags)

    def test_ordinary_commands_pass_through(self):
        session = Session()
        step(session, "who")
        self.assertIn("DELEGATED:who", session.messages)

    def test_production_server_registers_veilith_before_location_audit(self):
        script = """
import server
import mud.veilith as veilith
from mud.world import ROOMS_BY_KEY
assert server.PlayerSession._veilith_runtime_installed
assert all(key in ROOMS_BY_KEY for key in veilith.ROOM_KEYS)
assert all(key in server.WORLD.legacy_rooms for key in veilith.ROOM_KEYS)
print('VEILITH_OK')
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT, text=True, capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)}, timeout=40,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("VEILITH_OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
