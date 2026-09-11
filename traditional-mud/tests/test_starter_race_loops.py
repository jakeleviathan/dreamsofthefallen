from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

# Import the fully assembled game server so every authored race module has had a
# chance to register its rooms and first quest before the contract is checked.
import mud.server  # noqa: F401
import mud.quests as quests
import mud.world as world
from mud.character_options import RACES_BY_KEY
from mud.database import Database
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

    def test_live_content_satisfies_the_eight_race_contract(self):
        validate_starter_loop_contract(
            rooms_by_key=world.ROOMS_BY_KEY,
            quests_by_key=quests.QUESTS_BY_KEY,
            race_keys=set(RACES_BY_KEY),
        )

        for loop in STARTER_RACE_LOOPS:
            with self.subTest(race=loop.race_key):
                room = world.ROOMS_BY_KEY[loop.starting_room_key]
                self.assertEqual(room.region_key, loop.region_key)
                self.assertTrue(room.exits)
                self.assertIn(loop.first_quest_key, quests.QUESTS_BY_KEY)

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
                    self.assertIn(character.current_room, world.ROOMS_BY_KEY)

    def test_starting_room_lookup_covers_every_race(self):
        for race_key in RACES_BY_KEY:
            with self.subTest(race=race_key):
                room_key = starting_room_for_race(race_key)
                self.assertIsNotNone(room_key)
                self.assertIn(room_key, world.ROOMS_BY_KEY)
        self.assertIsNone(starting_room_for_race("not_a_race"))


if __name__ == "__main__":
    unittest.main()
