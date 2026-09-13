from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.midgame_three_roads import (
    DWARF_COMPLETE_FLAG,
    DWARF_QUEST,
    DWARF_REGION_KEY,
    DWARF_WITNESS_ITEM_KEY,
    FINAL_REQUIRED_FLAGS,
    LEVEL_20_ABILITIES,
    MERIDIAN_QUEST,
    MERIDIAN_REGION_KEY,
    MIDGAME_ITEMS,
    MIDGAME_ROOMS,
    MOON_COMPLETE_FLAG,
    MOON_QUEST,
    MOON_REGION_KEY,
    MOON_WITNESS_ITEM_KEY,
    TROLL_COMPLETE_FLAG,
    TROLL_QUEST,
    TROLL_REGION_KEY,
    TROLL_WITNESS_ITEM_KEY,
    TWENTIETH_QUEST,
    VEYRA_EAST_RIVER_GATE_KEY,
    VEYRA_NORTH_WATERWORKS_KEY,
    VEYRA_SCHOLARS_RISE_KEY,
    midgame_augmentations,
)


class ThreeRoadsMidgameTests(unittest.TestCase):
    def test_full_midgame_room_wave_has_four_distinct_regions(self):
        self.assertEqual(len(MIDGAME_ROOMS), 51)
        regions = {room.region_key for room in MIDGAME_ROOMS}
        self.assertEqual(
            regions,
            {TROLL_REGION_KEY, DWARF_REGION_KEY, MOON_REGION_KEY, MERIDIAN_REGION_KEY},
        )

    def test_production_server_assembles_the_complete_midgame(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.crafting import ITEMS_BY_KEY
from mud.mechanics import class_abilities_for_level
from mud.midgame_three_roads import (
    DWARF_WITNESS_ITEM_KEY,
    LEVEL_20_ABILITIES,
    MIDGAME_ROOMS,
    MOON_WITNESS_ITEM_KEY,
    TROLL_WITNESS_ITEM_KEY,
    VEYRA_EAST_RIVER_GATE_KEY,
    VEYRA_NORTH_WATERWORKS_KEY,
    VEYRA_SCHOLARS_RISE_KEY,
)

assert server.PlayerSession._midgame_12_20_runtime_installed
assert all(room.key in server.WORLD.legacy_rooms for room in MIDGAME_ROOMS)

for room_key, direction, minimum_level in (
    (VEYRA_NORTH_WATERWORKS_KEY, "north", 12),
    (VEYRA_EAST_RIVER_GATE_KEY, "east", 12),
    (VEYRA_SCHOLARS_RISE_KEY, "up", 13),
):
    exits = [
        exit_def
        for exit_def in server.WORLD.augmentations[room_key].extra_exits
        if exit_def.direction == direction
    ]
    assert exits and exits[-1].condition.min_level == minimum_level

assert {
    TROLL_WITNESS_ITEM_KEY,
    DWARF_WITNESS_ITEM_KEY,
    MOON_WITNESS_ITEM_KEY,
}.issubset(ITEMS_BY_KEY)

for class_key, ability in LEVEL_20_ABILITIES.items():
    if class_key == "priest":
        for deity_key in ("zerjz", "tenebrous", "leviathan"):
            assert ability.key in {
                item.key for item in class_abilities_for_level("priest", 20, deity_key)
            }
    else:
        assert ability.key in {
            item.key for item in class_abilities_for_level(class_key, 20)
        }

print("MIDGAME_PRODUCTION_OK")
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
        self.assertIn("MIDGAME_PRODUCTION_OK", result.stdout)

    def test_three_roads_branch_from_veyra_at_intended_levels(self):
        augmentations = midgame_augmentations()
        cases = (
            (VEYRA_NORTH_WATERWORKS_KEY, "north", 12),
            (VEYRA_EAST_RIVER_GATE_KEY, "east", 12),
            (VEYRA_SCHOLARS_RISE_KEY, "up", 13),
        )
        for room_key, direction, minimum_level in cases:
            augmentation = augmentations[room_key]
            exits = [exit_def for exit_def in augmentation.extra_exits if exit_def.direction == direction]
            self.assertTrue(exits, (room_key, direction))
            self.assertEqual(exits[-1].condition.min_level, minimum_level)

    def test_regional_quests_are_independent_and_converge_at_nineteen(self):
        self.assertEqual(TROLL_QUEST.minimum_level, 12)
        self.assertEqual(DWARF_QUEST.minimum_level, 12)
        self.assertEqual(MOON_QUEST.minimum_level, 13)
        self.assertEqual(MERIDIAN_QUEST.minimum_level, 19)
        self.assertEqual(TWENTIETH_QUEST.minimum_level, 20)

        self.assertEqual(
            set(FINAL_REQUIRED_FLAGS),
            {TROLL_COMPLETE_FLAG, DWARF_COMPLETE_FLAG, MOON_COMPLETE_FLAG},
        )

    def test_each_regional_thread_has_a_physical_witness(self):
        item_keys = {item.key for item in MIDGAME_ITEMS}
        self.assertIn(TROLL_WITNESS_ITEM_KEY, item_keys)
        self.assertIn(DWARF_WITNESS_ITEM_KEY, item_keys)
        self.assertIn(MOON_WITNESS_ITEM_KEY, item_keys)

    def test_level_twenty_gives_every_class_a_major_unlock(self):
        expected = {
            "brute": "unbroken_stance",
            "wizard": "starbreaker",
            "druid": "deep_roots",
            "priest": "last_light",
            "necromancer": "raise_grave_knight",
        }
        self.assertEqual(set(LEVEL_20_ABILITIES), set(expected))

        for class_key, ability in LEVEL_20_ABILITIES.items():
            self.assertEqual(ability.key, expected[class_key])
            self.assertEqual(ability.unlock_level, 20)

    def test_necromancer_milestone_is_a_real_upgraded_undead_servant(self):
        ability = LEVEL_20_ABILITIES["necromancer"]
        self.assertEqual(ability.key, "raise_grave_knight")
        self.assertEqual(ability.catalyst_item_key, "bone_chips")
        self.assertEqual(ability.catalyst_quantity, 4)

    def test_level_tags_reach_exactly_twenty_in_new_content(self):
        tagged = []
        for room in MIDGAME_ROOMS:
            for tag in room.tags:
                if tag.startswith("level_"):
                    tagged.extend(int(part) for part in tag.split("_")[1:] if part.isdigit())
        self.assertTrue(tagged)
        self.assertEqual(min(tagged), 12)
        self.assertEqual(max(tagged), 20)


if __name__ == "__main__":
    unittest.main()
