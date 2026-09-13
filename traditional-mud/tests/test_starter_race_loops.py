from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.character_options import RACES_BY_KEY
from mud.database import Database
from mud.location_safety import (
    live_rooms_for_world,
    repair_invalid_character_location,
    validate_authored_exit_targets,
    validate_starter_route_walks,
)
from mud.starter_race_loops import (
    STARTER_RACE_LOOPS,
    STARTER_RACE_LOOPS_BY_RACE,
    install_starter_room_database_hook,
    starting_room_for_race,
    validate_starter_loop_contract,
)


class HookedDatabase(Database):
    """Isolate the creation hook so unrelated Database tests are not mutated."""


install_starter_room_database_hook(HookedDatabase)


class StarterRaceLoopTests(unittest.TestCase):
    def test_every_launch_race_has_one_distinct_playable_hook(self):
        self.assertEqual(set(STARTER_RACE_LOOPS_BY_RACE), set(RACES_BY_KEY))
        self.assertEqual(len(STARTER_RACE_LOOPS), 8)
        self.assertEqual(len({loop.hook_name for loop in STARTER_RACE_LOOPS}), 8)

        for loop in STARTER_RACE_LOOPS:
            with self.subTest(race=loop.race_key):
                self.assertTrue(loop.hook_summary.strip())
                self.assertGreaterEqual(len(loop.player_actions), 4)
                self.assertTrue(all(action.strip() for action in loop.player_actions))
                self.assertTrue(loop.completion_flag.strip())

    def test_contract_validator_requires_rooms_regions_exits_and_first_quests(self):
        rooms = {
            loop.starting_room_key: SimpleNamespace(
                region_key=loop.region_key,
                exits={"out": "somewhere"},
            )
            for loop in STARTER_RACE_LOOPS
        }
        quests = {loop.first_quest_key: object() for loop in STARTER_RACE_LOOPS}

        validate_starter_loop_contract(
            rooms_by_key=rooms,
            quests_by_key=quests,
            race_keys=set(RACES_BY_KEY),
        )

        broken_quests = dict(quests)
        broken_quests.pop(STARTER_RACE_LOOPS[0].first_quest_key)
        with self.assertRaises(RuntimeError):
            validate_starter_loop_contract(
                rooms_by_key=rooms,
                quests_by_key=broken_quests,
                race_keys=set(RACES_BY_KEY),
            )

    def test_new_characters_of_all_eight_races_have_real_room_and_bind_immediately(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database = HookedDatabase(Path(tempdir) / "starter-races.db")
            account = database.create_account("starterloops", "hash")

            for index, loop in enumerate(STARTER_RACE_LOOPS, start=1):
                with self.subTest(race=loop.race_key):
                    character = database.create_character(
                        account.id,
                        f"Loop{index}",
                        loop.race_key,
                        "wizard",
                    )
                    self.assertEqual(character.current_room, loop.starting_room_key)
                    self.assertEqual(character.bind_room, loop.starting_room_key)

    def test_starting_room_lookup_covers_every_race(self):
        for race_key in RACES_BY_KEY:
            with self.subTest(race=race_key):
                self.assertIsNotNone(starting_room_for_race(race_key))
        self.assertIsNone(starting_room_for_race("not_a_race"))

    def test_global_exit_contract_rejects_any_advertised_missing_destination(self):
        rooms = {
            "a": SimpleNamespace(exits={"north": "b"}),
            "b": SimpleNamespace(exits={"south": "a"}),
        }
        validate_authored_exit_targets(rooms)

        broken = dict(rooms)
        broken["a"] = SimpleNamespace(exits={"north": "deleted_room"})
        with self.assertRaises(RuntimeError):
            validate_authored_exit_targets(broken)

    def test_every_racial_start_can_be_walked_into_a_real_second_room(self):
        rooms = {}
        for index, loop in enumerate(STARTER_RACE_LOOPS, start=1):
            next_key = f"starter_test_next_{index}"
            rooms[loop.starting_room_key] = SimpleNamespace(exits={"out": next_key})
            rooms[next_key] = SimpleNamespace(exits={"back": loop.starting_room_key})

        validate_authored_exit_targets(rooms)
        validate_starter_route_walks(rooms)

    def test_stale_saved_locations_are_repaired_for_all_eight_races(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database = HookedDatabase(Path(tempdir) / "repair-all-races.db")
            account = database.create_account("repairloops", "hash")
            live_rooms = {
                loop.starting_room_key: SimpleNamespace(exits={})
                for loop in STARTER_RACE_LOOPS
            }

            for index, loop in enumerate(STARTER_RACE_LOOPS, start=1):
                with self.subTest(race=loop.race_key):
                    character = database.create_character(
                        account.id,
                        f"Repair{index}",
                        loop.race_key,
                        "wizard",
                    )
                    database.set_character_room(character.id, "deleted_development_room")
                    database.set_bind_room(character.id, "deleted_bind_room")
                    stale = database.get_character_by_name(character.name)
                    session = SimpleNamespace(character=stale, database=database)

                    self.assertTrue(repair_invalid_character_location(session, live_rooms))
                    self.assertEqual(session.character.current_room, loop.starting_room_key)
                    self.assertEqual(session.character.bind_room, loop.starting_room_key)

    def test_valid_travel_is_never_teleported_back_to_a_racial_start(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database = HookedDatabase(Path(tempdir) / "repair-valid-travel.db")
            account = database.create_account("validtravel", "hash")
            character = database.create_character(
                account.id,
                "Traveler",
                "human",
                "wizard",
            )
            database.set_character_room(character.id, "shared_valid_destination")
            database.set_bind_room(character.id, "shared_valid_destination")
            traveled = database.get_character_by_name(character.name)
            live_rooms = {
                loop.starting_room_key: SimpleNamespace(exits={})
                for loop in STARTER_RACE_LOOPS
            }
            live_rooms["shared_valid_destination"] = SimpleNamespace(exits={})
            session = SimpleNamespace(character=traveled, database=database)

            self.assertFalse(repair_invalid_character_location(session, live_rooms))
            self.assertEqual(session.character.current_room, "shared_valid_destination")
            self.assertEqual(session.character.bind_room, "shared_valid_destination")

    def test_production_entrypoint_assembles_and_validates_all_eight_starts(self):
        # Importing the production entrypoint installs every authored content
        # layer, validates every advertised room destination, walks outward from
        # all eight racial starts, and installs the universal stale-location guard.
        # Do it in a child process so production registry mutations cannot leak.
        project_root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.location_safety import live_rooms_for_world, validate_authored_exit_targets, validate_starter_route_walks

assert server.PlayerSession._universal_location_repair_runtime_installed
rooms = live_rooms_for_world(server.WORLD)
validate_authored_exit_targets(rooms)
validate_starter_route_walks(rooms)
print('STARTER_LOCATION_SAFETY_OK')
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("STARTER_LOCATION_SAFETY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
