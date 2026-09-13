from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.world as world
from mud.goblin_runtime import (
    GOBLIN_STARTER_ROUTE,
    repair_goblin_location,
    validate_goblin_starter_routes,
)
from mud.goblin_start import GOBLIN_ROOMS, GOBLIN_START_ROOM_KEY, install_goblin_world


class _RepairDatabase:
    def __init__(self, character):
        self.character = character

    def set_character_room(self, _character_id: int, room_key: str) -> None:
        self.character.current_room = room_key

    def set_bind_room(self, _character_id: int, room_key: str) -> None:
        self.character.bind_room = room_key

    def get_character_by_name(self, _name: str):
        return self.character


class GoblinPriestPlayabilityTests(unittest.TestCase):
    def test_every_goblin_exit_is_walkable_and_has_a_return_path(self):
        validate_goblin_starter_routes()
        rooms = {room.key: room for room in GOBLIN_ROOMS}
        opposite = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "up": "down",
            "down": "up",
        }
        for room in GOBLIN_ROOMS:
            for direction, destination_key in room.exits.items():
                with self.subTest(room=room.key, direction=direction):
                    self.assertIn(destination_key, rooms)
                    self.assertEqual(
                        rooms[destination_key].exits.get(opposite[direction]),
                        room.key,
                    )

    def test_three_bells_route_begins_with_a_real_north_move_and_reaches_swamp_gate(self):
        rooms = {room.key: room for room in GOBLIN_ROOMS}
        self.assertEqual(
            rooms[GOBLIN_START_ROOM_KEY].exits.get("north"),
            "goblin_sorting_spine",
        )
        self.assertEqual(
            GOBLIN_STARTER_ROUTE,
            (
                "goblin_clattergate",
                "goblin_sorting_spine",
                "goblin_patchwork_plaza",
                "goblin_floodgate_walk",
            ),
        )
        for current, destination in zip(GOBLIN_STARTER_ROUTE, GOBLIN_STARTER_ROUTE[1:]):
            self.assertIn(destination, rooms[current].exits.values())

    def test_legacy_goblin_with_stale_room_is_repaired_to_clattergate(self):
        original_rooms = world.ROOMS
        original_rooms_by_key = dict(world.ROOMS_BY_KEY)
        original_npcs = world.NPCS
        original_npcs_by_key = dict(world.NPCS_BY_KEY)
        try:
            install_goblin_world()
            character = SimpleNamespace(
                id=17,
                name="Scrapprayer",
                race="goblin",
                current_room="junk_city_and_swamps",
                bind_room="deleted_goblin_dev_room",
            )
            session = SimpleNamespace(
                character=character,
                database=_RepairDatabase(character),
            )
            self.assertTrue(repair_goblin_location(session))
            self.assertEqual(character.current_room, GOBLIN_START_ROOM_KEY)
            self.assertEqual(character.bind_room, GOBLIN_START_ROOM_KEY)
        finally:
            world.ROOMS = original_rooms
            world.ROOMS_BY_KEY.clear()
            world.ROOMS_BY_KEY.update(original_rooms_by_key)
            world.NPCS = original_npcs
            world.NPCS_BY_KEY.clear()
            world.NPCS_BY_KEY.update(original_npcs_by_key)

    def test_priest_foundation_is_playable_from_level_one_through_ten(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import mud.mechanics as mechanics
from mud.priest_early_progression import install_priest_early_progression_content
from mud.stats import CharacterStats

install_priest_early_progression_content()
required = {
    "mend_ally": 1,
    "sacred_spark": 1,
    "blessing_of_resolve": 2,
    "greater_mend": 4,
    "resurrection": 5,
    "purifying_light": 6,
    "prayer_of_renewal": 7,
    "aegis_of_faith": 8,
    "sanctuary": 9,
    "divine_concord": 10,
}
for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items():
    by_key = {ability.key: ability for ability in abilities}
    for key, level in required.items():
        assert key in by_key, (path_key, key, sorted(by_key))
        assert by_key[key].unlock_level == level, (path_key, key, by_key[key].unlock_level)
        assert by_key[key].mana_cost is not None, (path_key, key)
        assert by_key[key].cooldown_seconds is not None, (path_key, key)
    level_one = {a.key for a in mechanics.priest_abilities_for_level(path_key, 1)}
    assert {"mend_ally", "sacred_spark"} <= level_one, (path_key, level_one)
    assert mechanics.priest_abilities_for_level(path_key, 10)

# Shared stat rules are the Priest resource/effect rules: both caster stats feed
# mana, Love feeds healing, and Mind feeds spell damage.
stats = CharacterStats(love=8, mind=6)
assert stats.maximum_mana(20) == 34
assert stats.healing_amount(5) == 13
assert stats.spell_damage(5) == 11
print("PRIEST_1_10_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PRIEST_1_10_OK", result.stdout)

    def test_production_entrypoint_installs_repair_and_priest_runtime(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.mechanics as mechanics
from mud.goblin_runtime import validate_goblin_starter_routes

validate_goblin_starter_routes()
assert server.PlayerSession._goblin_start_runtime_installed
assert server.PlayerSession._rattlefen_opening_runtime_installed
assert server.PlayerSession._priest_early_progression_runtime_installed
for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items():
    keys = {ability.key for ability in abilities}
    assert {"mend_ally", "sacred_spark", "blessing_of_resolve", "resurrection", "divine_concord"} <= keys, (path_key, keys)
print("GOBLIN_PRIEST_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GOBLIN_PRIEST_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
