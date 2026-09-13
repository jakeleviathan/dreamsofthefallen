from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.frontier_convergence import (
    ALL_FRONTIER_ROOMS,
    ASHCROSS_COMMON_KEY,
    ASHCROSS_DELVERS_KEY,
    ASHCROSS_IRON_CAUSEWAY_KEY,
    ASHCROSS_ROOTROAD_KEY,
    ASHCROSS_SKYROAD_KEY,
    DWARF_HUB_KEY,
    FRONTIER_ROOMS,
    INTRO_QUEST,
    MERIDIAN_CAMP_KEY,
    MOON_HUB_KEY,
    OUTERWORKS_ROOMS,
    OUTER_COMPLETE_FLAG,
    OUTER_CISTERN_KEY,
    OUTER_DEEP_GATE_KEY,
    OUTER_FLOOD_RING_KEY,
    OUTER_FOSSIL_BEND_KEY,
    OUTER_PUMP_KEY,
    OUTER_QUEST,
    OUTER_ROOT_GALLERY_KEY,
    OUTER_SEAM_BALCONY_KEY,
    OUTER_SURVEY_KEY,
    TROLL_CLUE_KEY,
    frontier_augmentations,
)
from mud.midgame_three_roads import FINAL_REQUIRED_FLAGS


class FrontierConvergenceTests(unittest.TestCase):
    def test_frontier_adds_shared_town_roads_secrets_and_outer_dungeon(self):
        self.assertEqual(len(FRONTIER_ROOMS), 12)
        self.assertEqual(len(OUTERWORKS_ROOMS), 11)
        self.assertEqual(len(ALL_FRONTIER_ROOMS), 23)

        tags = {tag for room in FRONTIER_ROOMS for tag in room.tags}
        self.assertIn("deep_forest", tags)
        self.assertIn("abandoned_causeway", tags)
        self.assertIn("optional_pocket", tags)
        self.assertIn("multiracial_hub", tags)

    def test_three_existing_roads_really_converge_on_ashcross(self):
        augmentations = frontier_augmentations()
        cases = (
            (TROLL_CLUE_KEY, "east", ASHCROSS_ROOTROAD_KEY, 15),
            (DWARF_HUB_KEY, "south", ASHCROSS_IRON_CAUSEWAY_KEY, 15),
            (MOON_HUB_KEY, "south", ASHCROSS_SKYROAD_KEY, 16),
        )
        for room_key, direction, destination, minimum_level in cases:
            exits = [
                exit_def
                for exit_def in augmentations[room_key].extra_exits
                if exit_def.direction == direction
            ]
            self.assertTrue(exits, (room_key, direction))
            self.assertEqual(exits[-1].destination_key, destination)
            self.assertEqual(exits[-1].condition.min_level, minimum_level)

    def test_ashcross_common_has_a_distinct_layer_for_all_eight_races(self):
        layers = frontier_augmentations()[ASHCROSS_COMMON_KEY].description_layers
        races = {
            layer.condition.races[0]
            for layer in layers
            if len(layer.condition.races) == 1
        }
        self.assertEqual(
            races,
            {"human", "forest_elf", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin"},
        )

    def test_outerworks_has_two_real_loops_back_to_the_survey_gallery(self):
        rooms = {room.key: room for room in OUTERWORKS_ROOMS}

        flood_path = (
            (OUTER_SURVEY_KEY, "north", OUTER_FLOOD_RING_KEY),
            (OUTER_FLOOD_RING_KEY, "east", OUTER_CISTERN_KEY),
            (OUTER_CISTERN_KEY, "south", OUTER_PUMP_KEY),
            (OUTER_PUMP_KEY, "west", OUTER_SURVEY_KEY),
        )
        root_path = (
            (OUTER_SURVEY_KEY, "south", OUTER_ROOT_GALLERY_KEY),
            (OUTER_ROOT_GALLERY_KEY, "east", OUTER_FOSSIL_BEND_KEY),
            (OUTER_FOSSIL_BEND_KEY, "north", OUTER_SEAM_BALCONY_KEY),
            (OUTER_SEAM_BALCONY_KEY, "west", OUTER_SURVEY_KEY),
        )
        for origin, direction, destination in flood_path + root_path:
            self.assertEqual(rooms[origin].exits[direction], destination)

    def test_level_gates_form_the_intended_15_to_20_spine(self):
        self.assertEqual(INTRO_QUEST.minimum_level, 15)
        self.assertEqual(OUTER_QUEST.minimum_level, 17)

        augmentations = frontier_augmentations()
        dungeon_exit = [
            exit_def
            for exit_def in augmentations[ASHCROSS_DELVERS_KEY].extra_exits
            if exit_def.direction == "down"
        ][0]
        self.assertEqual(dungeon_exit.condition.min_level, 17)

        meridian_exit = [
            exit_def
            for exit_def in augmentations[OUTER_DEEP_GATE_KEY].extra_exits
            if exit_def.direction == "east"
        ][0]
        self.assertEqual(meridian_exit.destination_key, MERIDIAN_CAMP_KEY)
        self.assertEqual(meridian_exit.condition.min_level, 19)
        self.assertEqual(
            set(meridian_exit.condition.required_flags),
            {OUTER_COMPLETE_FLAG, *FINAL_REQUIRED_FLAGS},
        )

    def test_production_server_assembles_frontier_convergence(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.crafting import ITEMS_BY_KEY
from mud.frontier_convergence import (
    ALL_FRONTIER_ROOMS,
    ASHCROSS_COMMON_KEY,
    DELVERS_TOKEN_KEY,
    DISPATCH_SATCHEL_KEY,
    LOCKWARDEN_PLATE_KEY,
    OUTER_DEEP_GATE_KEY,
)

assert server.PlayerSession._frontier_convergence_runtime_installed
assert all(room.key in server.WORLD.legacy_rooms for room in ALL_FRONTIER_ROOMS)
assert {DELVERS_TOKEN_KEY, DISPATCH_SATCHEL_KEY, LOCKWARDEN_PLATE_KEY}.issubset(ITEMS_BY_KEY)
assert len(server.WORLD.augmentations[ASHCROSS_COMMON_KEY].description_layers) >= 8
assert any(
    exit_def.direction == "east"
    for exit_def in server.WORLD.augmentations[OUTER_DEEP_GATE_KEY].extra_exits
)
print("FRONTIER_CONVERGENCE_PRODUCTION_OK")
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
        self.assertIn("FRONTIER_CONVERGENCE_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
