from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.gloamworks_dungeon import (
    BRAKE_SAINT,
    BURIED_REGENT,
    BURIED_REGENT_KEY,
    CLASS_RESONANCE_TEXT,
    GLOAMWORKS_BOSS_KEY,
    GLOAMWORKS_COMPLETE_FLAG,
    GLOAMWORKS_MINIBOSS_KEYS,
    GLOAMWORKS_QUEST_KEY,
    GLOAMWORKS_ROOM_KEYS,
    GLOAMWORKS_ROOMS,
    GLOAMWORKS_TWIN_SEAL_FLAG,
    GLOAM_BRAKE_CHAPEL_KEY,
    GLOAM_BURIED_COURT_KEY,
    GLOAM_GLASS_FAULT_KEY,
    GLOAM_HOLLOW_DYNAMO_KEY,
    GLOAM_RESONANCE_SHAFT_KEY,
    GLOAM_TWIN_SEAL_KEY,
    MOTHER_SPARKS,
    RACE_FAULT_TEXT,
    _SEAL_HOLDS,
    _attempt_seal_hold,
    _group_ready_for_regent,
    gloamworks_augmentations,
)
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY, WAYMEET_INTRO_COMPLETE_FLAG


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def move_to(self, room_key: str) -> None:
        self.database.set_character_room(self.character.id, room_key)
        refreshed = self.database.get_character_by_name(self.character.name)
        assert refreshed is not None
        self.character = refreshed


class GloamworksDungeonTests(unittest.TestCase):
    def setUp(self) -> None:
        _SEAL_HOLDS.clear()

    def _pair(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "gloamworks.db")
        account = database.create_account("gloamtest", "hash")
        first = database.create_character(account.id, "LeftHand", "human", "brute")
        second = database.create_character(account.id, "RightHand", "moon_elf", "wizard")
        # Level 4 begins at 450 cumulative XP under the current progression curve.
        database.add_experience(first.id, 450)
        database.add_experience(second.id, 450)
        for character in (first, second):
            database.grant_flag(character.id, WAYMEET_INTRO_COMPLETE_FLAG)
            database.start_quest(character.id, GLOAMWORKS_QUEST_KEY, "sync_seals")
            database.set_character_room(character.id, GLOAM_TWIN_SEAL_KEY)
        first = database.get_character_by_name("LeftHand")
        second = database.get_character_by_name("RightHand")
        assert first is not None and second is not None
        return tempdir, database, _Session(database, first), _Session(database, second)

    def test_dungeon_is_eighteen_connected_rooms_with_real_boss_structure(self):
        self.assertEqual(len(GLOAMWORKS_ROOMS), 18)
        self.assertEqual(len(set(GLOAMWORKS_ROOM_KEYS)), 18)
        by_key = {room.key: room for room in GLOAMWORKS_ROOMS}
        self.assertEqual(set(by_key), set(GLOAMWORKS_ROOM_KEYS))
        for room in GLOAMWORKS_ROOMS:
            with self.subTest(room=room.key):
                self.assertEqual(room.region_key, "gloamworks")
                self.assertTrue(room.exits)
        self.assertIn(BRAKE_SAINT.key, by_key[GLOAM_BRAKE_CHAPEL_KEY].enemy_keys)
        self.assertIn(MOTHER_SPARKS.key, by_key[GLOAM_HOLLOW_DYNAMO_KEY].enemy_keys)
        self.assertIn(BURIED_REGENT.key, by_key[GLOAM_BURIED_COURT_KEY].enemy_keys)
        self.assertEqual(GLOAMWORKS_MINIBOSS_KEYS, (BRAKE_SAINT.key, MOTHER_SPARKS.key))
        self.assertEqual(GLOAMWORKS_BOSS_KEY, BURIED_REGENT_KEY)
        self.assertLess(BRAKE_SAINT.max_hp, MOTHER_SPARKS.max_hp)
        self.assertLess(MOTHER_SPARKS.max_hp, BURIED_REGENT.max_hp)

    def test_waymeet_dungeon_entrance_requires_level_four_and_shared_zone_completion(self):
        augmentation = gloamworks_augmentations()[WAYMEET_GLOAM_MOUTH_KEY]
        exits = [item for item in augmentation.extra_exits if item.destination_key == GLOAMWORKS_ROOM_KEYS[0]]
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].condition.min_level, 4)
        self.assertIn(WAYMEET_INTRO_COMPLETE_FLAG, exits[0].condition.required_flags)

    def test_deep_rooms_deliberately_show_different_truths_by_race_and_class(self):
        augmentations = gloamworks_augmentations()
        fault_layers = augmentations[GLOAM_GLASS_FAULT_KEY].description_layers
        resonance_layers = augmentations[GLOAM_RESONANCE_SHAFT_KEY].description_layers
        self.assertEqual(len(RACE_FAULT_TEXT), 8)
        self.assertEqual(len(fault_layers), 8)
        self.assertEqual({layer.condition.races[0] for layer in fault_layers}, set(RACE_FAULT_TEXT))
        self.assertEqual(len(CLASS_RESONANCE_TEXT), 5)
        self.assertEqual(len(resonance_layers), 5)
        self.assertEqual({layer.condition.classes[0] for layer in resonance_layers}, set(CLASS_RESONANCE_TEXT))
        self.assertNotEqual(RACE_FAULT_TEXT["dwarf"], RACE_FAULT_TEXT["sporekin"])
        self.assertNotEqual(CLASS_RESONANCE_TEXT["wizard"], CLASS_RESONANCE_TEXT["druid"])

    def test_twin_seal_requires_two_distinct_players_and_unlocks_both(self):
        tempdir, database, left, right = self._pair()
        try:
            peers = [left, right]
            self.assertTrue(asyncio.run(_attempt_seal_hold(left, "left", peers)))
            self.assertNotIn(GLOAMWORKS_TWIN_SEAL_FLAG, database.list_flags(left.character.id))
            self.assertTrue(asyncio.run(_attempt_seal_hold(right, "right", peers)))
            self.assertIn(GLOAMWORKS_TWIN_SEAL_FLAG, database.list_flags(left.character.id))
            self.assertIn(GLOAMWORKS_TWIN_SEAL_FLAG, database.list_flags(right.character.id))
            self.assertEqual(database.get_quest(left.character.id, GLOAMWORKS_QUEST_KEY)["current_step"], "defeat_regent")
            self.assertEqual(database.get_quest(right.character.id, GLOAMWORKS_QUEST_KEY)["current_step"], "defeat_regent")
            left.move_to(GLOAM_BURIED_COURT_KEY)
            right.move_to(GLOAM_BURIED_COURT_KEY)
            self.assertTrue(_group_ready_for_regent(left, peers))
        finally:
            tempdir.cleanup()

    def test_boss_door_is_character_gated_by_successful_cooperative_seal(self):
        augmentation = gloamworks_augmentations()[GLOAM_TWIN_SEAL_KEY]
        east = next(item for item in augmentation.exit_overrides if item.direction == "east")
        self.assertIn(GLOAMWORKS_TWIN_SEAL_FLAG, east.condition.required_flags)
        self.assertIn("Two explorers", east.failure_text)

    def test_production_server_assembles_gloamworks_after_waymeet(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.gloamworks_dungeon import GLOAMWORKS_ROOM_KEYS, GLOAMWORKS_BOSS_KEY, GLOAM_GLASS_FAULT_KEY; "
            "from mud.combat import ENEMIES_BY_KEY; "
            "assert all(key in server.WORLD.legacy_rooms for key in GLOAMWORKS_ROOM_KEYS); "
            "assert GLOAMWORKS_BOSS_KEY in ENEMIES_BY_KEY; "
            "assert server.WORLD.augmentations[GLOAM_GLASS_FAULT_KEY].description_layers; "
            "print('GLOAMWORKS_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GLOAMWORKS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
