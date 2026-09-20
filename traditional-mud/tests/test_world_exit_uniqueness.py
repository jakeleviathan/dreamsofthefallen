from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorldExitUniquenessTests(unittest.TestCase):
    def test_production_world_has_one_route_per_direction(self):
        code = r"""
import server
from mud.room_engine import PlayerRoomContext

world = server.WORLD
audit = world.audit_exit_sources()
conflicts = [row for row in audit if row.startswith("CONFLICT ")]
redundant = [row for row in audit if row.startswith("REDUNDANT ")]
assert not conflicts, conflicts

duplicates = []
for room_key in sorted(world.legacy_rooms):
    scene = world.scene(room_key)
    if scene is None:
        continue
    directions = [exit_def.direction.strip().lower() for exit_def in scene.exits]
    if len(directions) != len(set(directions)):
        duplicates.append((room_key, directions))
assert not duplicates, duplicates

context = PlayerRoomContext(
    character_id=1,
    race_key="forest_elf",
    class_key="druid",
    level=5,
    character_flags=frozenset(),
    hour=10,
)
view = world.build_view("forest_elf_circle_clearing", context)
assert view is not None
circle = [(row.direction, row.destination_key) for row in view.exits]
assert circle.count(("north", "forest_elf_greenway")) == 1, circle
assert circle.count(("east", "forest_elf_keeper_nursery")) == 1, circle
assert circle.count(("west", "forest_elf_hearthwalk")) == 1, circle
assert len([direction for direction, _destination in circle if direction == "east"]) == 1
assert len([direction for direction, _destination in circle if direction == "west"]) == 1

# Production startup calls this same validator after all content installers.
world.validate_exit_integrity()
assert not world.audit_reciprocal_exits(), world.audit_reciprocal_exits()

# Regression for the route that exposed the bug in live play. Waymeet Crossroads
# remains west of Marsh Causeway, and Junk City's Floodgate Walk is east of it.
marsh = world.scene("waymeet_marsh_road")
floodgate = world.scene("goblin_floodgate_walk")
assert marsh is not None and floodgate is not None
marsh_exits = {row.direction: row.destination_key for row in marsh.exits}
floodgate_exits = {row.direction: row.destination_key for row in floodgate.exits}
assert marsh_exits["west"] == "waymeet_crossroads", marsh_exits
assert marsh_exits["east"] == "goblin_floodgate_walk", marsh_exits
assert floodgate_exits["west"] == "waymeet_marsh_road", floodgate_exits

print("RECIPROCAL_EXIT_REPAIRS", server._RECIPROCAL_EXIT_REPAIRS)
print("RAW_REDUNDANT_EXIT_SOURCES", len(redundant))
for row in redundant:
    print(row)
print("WORLD_EXIT_UNIQUENESS_OK", len(world.legacy_rooms))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WORLD_EXIT_UNIQUENESS_OK", result.stdout)
        self.assertIn("RAW_REDUNDANT_EXIT_SOURCES", result.stdout)


if __name__ == "__main__":
    unittest.main()
