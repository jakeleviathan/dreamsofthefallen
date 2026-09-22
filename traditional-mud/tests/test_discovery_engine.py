from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.discovery_catalog import TARGET_CATALOG_SIZE, build_discovery_catalog, catalog_kind_counts
from mud.discovery_engine import (
    DiscoveryCondition,
    DiscoveryDefinition,
    DiscoveryRegistry,
    attempt_discovery_command,
    attempt_entry_discovery,
    discovery_record,
    validate_discovery_catalog,
)
from mud.room_engine import WorldService
from mud.world import RoomDefinition


class _Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str) -> None:
        self.outputs.append(text)


def _test_world() -> WorldService:
    rooms = {
        "test_court": RoomDefinition(
            key="test_court",
            name="Test Court",
            description="An old paved court with a shallow mark near the wall.",
            region_key="human_kingdom",
            exits={"east": "test_path"},
            tags=("city", "old_stone"),
        ),
        "test_path": RoomDefinition(
            key="test_path",
            name="Test Path",
            description="A narrow old path under trees.",
            region_key="great_elf_forest",
            exits={"west": "test_court"},
            tags=("forest", "path"),
        ),
    }
    return WorldService(rooms, augmentations={})


class DiscoveryEngineTests(unittest.TestCase):
    def _database(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "discoveries.db")
        account = database.create_account("seeker", "hash")
        character = database.create_character(account.id, "Seeker", "human", "wizard")
        database.set_character_room(character.id, "test_court")
        character = database.get_character_by_name("Seeker")
        return temp, database, character

    def test_hidden_command_records_once_without_becoming_a_checklist(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        world = _test_world()
        definition = DiscoveryDefinition(
            key="test:hidden_mark",
            kind="environmental",
            trigger="command",
            verbs=("search",),
            targets=("ground",),
            text="A nearly invisible line joins three old paving stones.",
            condition=DiscoveryCondition(room_keys=("test_court",)),
        )
        registry = DiscoveryRegistry((definition,))
        session = _Session(database, character)

        first = asyncio.run(
            attempt_discovery_command(
                session,
                world,
                "search ground",
                registry=registry,
            )
        )
        second = asyncio.run(
            attempt_discovery_command(
                session,
                world,
                "search ground",
                registry=registry,
            )
        )
        checklist = asyncio.run(
            attempt_discovery_command(
                session,
                world,
                "discoveries",
                registry=registry,
            )
        )

        self.assertTrue(first.discovered)
        self.assertTrue(first.handled)
        self.assertFalse(second.discovered)
        self.assertFalse(checklist.handled)
        self.assertIsNotNone(discovery_record(database, character.id, definition.key))
        self.assertEqual("".join(session.outputs).count("nearly invisible line"), 1)

    def test_prerequisite_chain_is_invisible_until_prior_clue_is_found(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        world = _test_world()
        first = DiscoveryDefinition(
            key="chain:first",
            kind="hidden_quest",
            trigger="command",
            verbs=("search",),
            targets=("mark",),
            text="The first mark is deliberate.",
            condition=DiscoveryCondition(room_keys=("test_court",)),
        )
        second = DiscoveryDefinition(
            key="chain:second",
            kind="hidden_quest",
            trigger="command",
            verbs=("touch",),
            targets=("seam",),
            text="The seam answers the earlier mark.",
            condition=DiscoveryCondition(
                room_keys=("test_court",),
                required_discoveries=("chain:first",),
            ),
        )
        registry = DiscoveryRegistry((first, second))
        session = _Session(database, character)

        blocked = asyncio.run(
            attempt_discovery_command(session, world, "touch seam", registry=registry)
        )
        self.assertFalse(blocked.discovered)

        self.assertTrue(
            asyncio.run(
                attempt_discovery_command(session, world, "search mark", registry=registry)
            ).discovered
        )
        self.assertTrue(
            asyncio.run(
                attempt_discovery_command(session, world, "touch seam", registry=registry)
            ).discovered
        )

    def test_inventory_condition_is_real_not_flavor_text(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        world = _test_world()
        definition = DiscoveryDefinition(
            key="test:item_gate",
            kind="interaction",
            trigger="command",
            verbs=("read",),
            targets=("scratches",),
            text="The scratches make sense only beside the note you carry.",
            condition=DiscoveryCondition(
                room_keys=("test_court",),
                required_items=("sealed_cathedral_note",),
            ),
        )
        registry = DiscoveryRegistry((definition,))
        session = _Session(database, character)

        # Human characters receive this note by default. Remove it to prove the
        # condition is actually enforced, then restore it.
        held = database.item_quantity(character.id, "sealed_cathedral_note")
        if held:
            database.consume_item(character.id, "sealed_cathedral_note", held)

        self.assertFalse(
            asyncio.run(
                attempt_discovery_command(session, world, "read scratches", registry=registry)
            ).discovered
        )
        database.add_item(character.id, "sealed_cathedral_note", 1)
        self.assertTrue(
            asyncio.run(
                attempt_discovery_command(session, world, "read scratches", registry=registry)
            ).discovered
        )

    def test_passive_event_can_be_discovered_on_room_entry(self):
        temp, database, character = self._database()
        self.addCleanup(temp.cleanup)
        world = _test_world()
        definition = DiscoveryDefinition(
            key="test:entry_event",
            kind="world_event",
            trigger="enter",
            text="Every bird in the court takes flight at the same instant.",
            condition=DiscoveryCondition(room_keys=("test_court",)),
            consume_command=False,
        )
        registry = DiscoveryRegistry((definition,))
        session = _Session(database, character)

        result = asyncio.run(attempt_entry_discovery(session, world, registry=registry))
        self.assertTrue(result.discovered)
        self.assertIn("same instant", "".join(session.outputs))

    def test_world_first_is_recorded_once_across_characters(self):
        temp, database, first = self._database()
        self.addCleanup(temp.cleanup)
        second_account = database.create_account("second_seeker", "hash")
        second = database.create_character(second_account.id, "Second", "human", "wizard")
        database.set_character_room(second.id, "test_court")
        second = database.get_character_by_name("Second")
        world = _test_world()
        definition = DiscoveryDefinition(
            key="test:world_first",
            kind="mystery",
            trigger="command",
            verbs=("examine",),
            targets=("shadow",),
            text="The shadow has a geometry the room does not.",
            condition=DiscoveryCondition(room_keys=("test_court",)),
        )
        registry = DiscoveryRegistry((definition,))

        first_result = asyncio.run(
            attempt_discovery_command(_Session(database, first), world, "examine shadow", registry=registry)
        )
        second_result = asyncio.run(
            attempt_discovery_command(_Session(database, second), world, "examine shadow", registry=registry)
        )

        self.assertTrue(first_result.world_first)
        self.assertFalse(second_result.world_first)
        with database.connect() as db:
            count = db.execute(
                "SELECT COUNT(*) AS n FROM world_discovery_firsts WHERE discovery_key = ?",
                (definition.key,),
            ).fetchone()
        self.assertEqual(int(count["n"]), 1)

    def test_full_catalog_has_hundreds_of_mixed_discoveries(self):
        from mud.server import WORLD

        definitions = build_discovery_catalog(WORLD)
        self.assertEqual(len(definitions), TARGET_CATALOG_SIZE)
        self.assertEqual(validate_discovery_catalog(WORLD, definitions), TARGET_CATALOG_SIZE)

        counts = catalog_kind_counts(definitions)
        self.assertEqual(counts["environmental"], 82)
        self.assertEqual(counts["racial"], 8)
        self.assertEqual(counts["class"], 5)
        self.assertEqual(counts["reputation"], 10)
        self.assertEqual(counts["inventory"], 5)
        self.assertEqual(counts["interaction"], 60)
        self.assertEqual(counts["rumor"], 10)
        self.assertEqual(counts["hidden_quest"], 50)
        self.assertEqual(counts["calendar"], 35)
        self.assertEqual(counts["provenance"], 25)
        self.assertEqual(counts["ecology"], 25)
        self.assertEqual(counts["world_event"], 20)
        self.assertEqual(counts["mystery"], 20)
        self.assertEqual(counts["ultra_secret"], 5)

        room_regions = {
            room_key: WORLD.scene(room_key).region_key
            for room_key in WORLD.legacy_rooms
            if WORLD.scene(room_key) is not None
        }
        covered_regions = {
            room_regions[room_key]
            for definition in definitions
            for room_key in definition.condition.room_keys
            if room_key in room_regions
        }
        self.assertEqual(covered_regions, set(room_regions.values()))

    def test_production_server_installs_private_discovery_runtime(self):
        root = Path(__file__).resolve().parents[1]
        code = r"""
import server
assert server.PlayerSession._discovery_runtime_installed
assert server.PlayerSession._discovery_catalog_size == 360
assert not hasattr(server.PlayerSession, "show_discoveries")
print("DISCOVERY_ENGINE_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=45,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("DISCOVERY_ENGINE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
