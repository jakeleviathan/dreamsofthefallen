from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.eight_roads_midgame import (
    ALL_WITNESS_FLAGS,
    FIVE_ROAD_ITEMS,
    FIVE_ROAD_ROOMS,
    FIVE_ROUTES,
    FOREST_COMPLETE_FLAG,
    GOBLIN_COMPLETE_FLAG,
    HUMAN_COMPLETE_FLAG,
    SPOREKIN_COMPLETE_FLAG,
    UNDEAD_COMPLETE_FLAG,
    WITNESSES_REQUIRED,
    eight_road_augmentations,
    witness_count,
)
from mud.frontier_convergence import (
    ASHCROSS_CULVERT_KEY,
    ASHCROSS_GATE_KEY,
    ASHCROSS_HUSHWOOD_KEY,
    ASHCROSS_SUNKEN_WATCH_KEY,
)
from mud.midgame_three_roads import (
    DWARF_COMPLETE_FLAG,
    MOON_COMPLETE_FLAG,
    TROLL_COMPLETE_FLAG,
)
from mud.veyra_city import (
    VEYRA_GREENHALL_KEY,
    VEYRA_LOWER_QUAYS_KEY,
    VEYRA_OLD_BRIDGE_KEY,
    VEYRA_PUBLIC_HEARTH_KEY,
    VEYRA_SOUTH_SPRAWL_KEY,
)


class EightRoadsMidgameTests(unittest.TestCase):
    def test_five_missing_cultures_now_have_full_level_twelve_to_fifteen_routes(self):
        self.assertEqual(len(FIVE_ROUTES), 5)
        self.assertEqual(len(FIVE_ROAD_ROOMS), 40)
        self.assertEqual(
            {route.race_key for route in FIVE_ROUTES},
            {"human", "forest_elf", "goblin", "undead", "sporekin"},
        )
        for route in FIVE_ROUTES:
            self.assertEqual(route.quest.minimum_level, 12)
            self.assertEqual(len(route.room_keys), 8)
            self.assertIn(route.mentor_room_key, route.room_keys)
            self.assertIn(route.boss_room_key, route.room_keys)
            self.assertIn(route.clue_room_key, route.room_keys)

    def test_new_routes_have_independent_witness_items_and_completion_flags(self):
        item_keys = {item.key for item in FIVE_ROAD_ITEMS}
        completion_flags = {route.completion_flag for route in FIVE_ROUTES}
        self.assertEqual(len(item_keys), 5)
        self.assertEqual(
            completion_flags,
            {
                HUMAN_COMPLETE_FLAG,
                FOREST_COMPLETE_FLAG,
                GOBLIN_COMPLETE_FLAG,
                UNDEAD_COMPLETE_FLAG,
                SPOREKIN_COMPLETE_FLAG,
            },
        )
        for route in FIVE_ROUTES:
            self.assertIn(route.witness_item_key, item_keys)
            self.assertNotEqual(route.choice_a_flag, route.choice_b_flag)

    def test_all_eight_witness_threads_count_equally_and_any_three_are_enough(self):
        self.assertEqual(WITNESSES_REQUIRED, 3)
        self.assertEqual(len(ALL_WITNESS_FLAGS), 8)
        self.assertEqual(len(set(ALL_WITNESS_FLAGS)), 8)
        self.assertEqual(
            set(ALL_WITNESS_FLAGS),
            {
                TROLL_COMPLETE_FLAG,
                DWARF_COMPLETE_FLAG,
                MOON_COMPLETE_FLAG,
                HUMAN_COMPLETE_FLAG,
                FOREST_COMPLETE_FLAG,
                GOBLIN_COMPLETE_FLAG,
                UNDEAD_COMPLETE_FLAG,
                SPOREKIN_COMPLETE_FLAG,
            },
        )
        self.assertEqual(witness_count(()), 0)
        self.assertEqual(
            witness_count((HUMAN_COMPLETE_FLAG, GOBLIN_COMPLETE_FLAG, SPOREKIN_COMPLETE_FLAG)),
            3,
        )
        self.assertEqual(
            witness_count((TROLL_COMPLETE_FLAG, FOREST_COMPLETE_FLAG, UNDEAD_COMPLETE_FLAG)),
            3,
        )

    def test_five_new_roads_depart_from_distinct_parts_of_veyra_at_level_twelve(self):
        augmentations = eight_road_augmentations()
        expected = (
            (VEYRA_SOUTH_SPRAWL_KEY, "south"),
            (VEYRA_GREENHALL_KEY, "south"),
            (VEYRA_LOWER_QUAYS_KEY, "south"),
            (VEYRA_OLD_BRIDGE_KEY, "east"),
            (VEYRA_PUBLIC_HEARTH_KEY, "down"),
        )
        for room_key, direction in expected:
            exits = [
                exit_def
                for exit_def in augmentations[room_key].extra_exits
                if exit_def.direction == direction
            ]
            self.assertEqual(len(exits), 1, (room_key, direction))
            self.assertEqual(exits[0].condition.min_level, 12)
            self.assertEqual(exits[0].condition.races, ())

    def test_new_roads_physically_join_different_parts_of_ashcross(self):
        augmentations = eight_road_augmentations()
        destinations = {
            exit_def.destination_key
            for room_key in (
                ASHCROSS_GATE_KEY,
                ASHCROSS_HUSHWOOD_KEY,
                ASHCROSS_CULVERT_KEY,
                ASHCROSS_SUNKEN_WATCH_KEY,
            )
            for exit_def in augmentations[room_key].extra_exits
        }
        endpoint_keys = {route.room_keys[-1] for route in FIVE_ROUTES}
        self.assertTrue(endpoint_keys.issubset(destinations))

    def test_new_regional_room_tags_stay_inside_level_twelve_to_fifteen(self):
        tagged_levels = []
        for room in FIVE_ROAD_ROOMS:
            for tag in room.tags:
                if not tag.startswith("level_"):
                    continue
                tagged_levels.extend(
                    int(piece)
                    for piece in tag.split("_")[1:]
                    if piece.isdigit()
                )
        self.assertTrue(tagged_levels)
        self.assertEqual(min(tagged_levels), 12)
        self.assertEqual(max(tagged_levels), 15)

    def test_production_server_assembles_all_eight_roads_and_replaces_old_meridian_gate(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.eight_roads_midgame import (
    FIVE_ROAD_ITEMS,
    FIVE_ROAD_ROOMS,
    FIVE_ROUTES,
    OUTER_COMPLETE_FLAG,
    OUTER_DEEP_GATE_KEY,
    WITNESSES_REQUIRED,
)
from mud.crafting import ITEMS_BY_KEY

assert server.PlayerSession._eight_roads_runtime_installed
assert len(FIVE_ROUTES) == 5
assert WITNESSES_REQUIRED == 3
assert all(room.key in server.WORLD.legacy_rooms for room in FIVE_ROAD_ROOMS)
assert {item.key for item in FIVE_ROAD_ITEMS}.issubset(ITEMS_BY_KEY)

east = [
    exit_def
    for exit_def in server.WORLD.augmentations[OUTER_DEEP_GATE_KEY].extra_exits
    if exit_def.direction == "east"
]
assert len(east) == 1, east
assert east[0].condition.min_level == 19
assert east[0].condition.required_flags == (OUTER_COMPLETE_FLAG,)
print("EIGHT_ROADS_PRODUCTION_OK")
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
        self.assertIn("EIGHT_ROADS_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
