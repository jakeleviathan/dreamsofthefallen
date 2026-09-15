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
from mud.exploration_map import (
    build_discovered_map_snapshot,
    discovered_room_keys,
    note_room_visited,
    render_ascii_map,
    stable_map_room_number,
)
from mud.exploration_map_gmcp import push_discovered_map_state
from mud.room_engine import WorldService
from mud.stats import CharacterStats


class _Telnet:
    def __init__(self) -> None:
        self.gmcp_enabled = True
        self.messages: list[tuple[str, object]] = []

    async def send_gmcp(self, package: str, payload=None) -> bool:
        self.messages.append((package, payload))
        return True


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.combatant = SimpleNamespace(current_hp=20, max_hp=20)
        self.telnet = _Telnet()


class ExplorationMapTests(unittest.TestCase):
    def _make(self, root: Path):
        database = Database(root / "map.db")
        account = database.create_account("map_test", "x")
        character = database.create_character(
            account.id,
            "Cartographer",
            "human",
            "priest",
            CharacterStats(might=5, grace=5, love=10, mind=8, hp=10),
        )
        return database, character, _Session(database, character), WorldService()

    def test_current_room_is_discovered_without_revealing_visible_neighbors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _database, character, session, world = self._make(Path(temp_dir))
            snapshot = build_discovered_map_snapshot(session, world)
            self.assertEqual(snapshot["current"], stable_map_room_number(character.current_room))
            self.assertEqual(len(snapshot["rooms"]), 1)
            self.assertEqual(snapshot["rooms"][0]["key"], character.current_room)
            # The Demon Gate has visible exits, but an exit is not a discovery.
            self.assertEqual(snapshot["rooms"][0]["exits"], {})

    def test_entered_neighbor_appears_and_persists_for_the_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database, character, session, world = self._make(Path(temp_dir))
            self.assertTrue(note_room_visited(session))
            self.assertTrue(note_room_visited(session, "human_ashen_way"))

            snapshot = build_discovered_map_snapshot(session, world)
            keys = {room["key"] for room in snapshot["rooms"]}
            self.assertIn(character.current_room, keys)
            self.assertIn("human_ashen_way", keys)
            self.assertNotIn("human_outer_drill_road", keys)

            # Rebuild the session to prove discovery lives in SQLite, not just RAM.
            session2 = _Session(database, database.get_character_by_name(character.name))
            self.assertIn("human_ashen_way", discovered_room_keys(session2))

    def test_ascii_map_marks_current_room_and_uses_full_name_legend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _database, character, session, world = self._make(Path(temp_dir))
            note_room_visited(session)
            note_room_visited(session, "human_ashen_way")
            text = render_ascii_map(session, world, radius=3)
            current_name = world.scene(character.current_room).name
            neighbor_name = world.scene("human_ashen_way").name
            self.assertIn("--- Local Map:", text)
            self.assertIn("@  " + current_name, text)
            self.assertIn(neighbor_name, text)
            self.assertIn("Mapped: 2 rooms total", text)
            self.assertIn("Only rooms you have personally entered", text)

    def test_discovery_is_per_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database, character, session, _world = self._make(Path(temp_dir))
            note_room_visited(session)
            note_room_visited(session, "human_ashen_way")

            second = database.create_character(
                character.account_id,
                "FreshMap",
                "human",
                "priest",
                CharacterStats(might=5, grace=5, love=10, mind=8, hp=10),
            )
            other_session = _Session(database, second)
            note_room_visited(other_session)
            self.assertNotIn("human_ashen_way", discovered_room_keys(other_session))


class ExplorationMapGmcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_gmcp_packet_contains_only_discovered_rooms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "map.db")
            account = database.create_account("map_gmcp", "x")
            character = database.create_character(
                account.id,
                "MapPacket",
                "human",
                "priest",
                CharacterStats(might=5, grace=5, love=10, mind=8, hp=10),
            )
            session = _Session(database, character)
            world = WorldService()
            note_room_visited(session, "human_ashen_way")

            sent = await push_discovered_map_state(session, world)
            self.assertTrue(sent)
            package, payload = session.telnet.messages[-1]
            self.assertEqual(package, "Dreams.Map")
            keys = {room["key"] for room in payload["rooms"]}
            self.assertIn(character.current_room, keys)
            self.assertIn("human_ashen_way", keys)
            self.assertNotIn("human_outer_drill_road", keys)

            # Unchanged snapshots are de-duplicated just like the other modern GMCP surfaces.
            self.assertFalse(await push_discovered_map_state(session, world))
            self.assertEqual(len(session.telnet.messages), 1)


class ProductionExplorationMapTests(unittest.TestCase):
    def test_production_entrypoint_installs_ascii_and_gmcp_map_layers(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
assert server.PlayerSession._exploration_map_runtime_installed
assert server.PlayerSession._exploration_map_gmcp_runtime_installed
print("EXPLORATION_MAP_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("EXPLORATION_MAP_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
