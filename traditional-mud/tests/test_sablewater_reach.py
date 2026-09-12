from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.sablewater_reach import (
    ALL_SABLEWATER_ROOM_KEYS,
    AUDITOR_AUTHORIZED_FLAG,
    BRASS_AUDITOR,
    DROWNED_BRASS_TRIBUNAL_KEY,
    DROWNED_COIN_VAULT_KEY,
    DROWNED_FLOODED_ARCHIVE_KEY,
    DROWNED_MAGISTRATE_ROOM_KEY,
    DROWNED_ROOM_KEYS,
    DROWNED_ROOMS,
    LOW_WATER_QUEST_KEY,
    PRICE_OF_CROSSING_QUEST_KEY,
    SABLEWATER_BROKEN_LEVEE_KEY,
    SABLEWATER_NORTH_FERRY_KEY,
    SABLEWATER_OLD_CUSTOMS_KEY,
    SABLEWATER_ROOM_KEYS,
    SABLEWATER_ROOMS,
    SABLEWATER_TOLLHOUSE_MOUTH_KEY,
    SABLEWATER_WILLOW_FERRY_KEY,
    SLUICE_WARDEN,
    TOLLHOUSE_UNLOCKED_FLAG,
    TOLL_NOBODY_OWES_QUEST_KEY,
    _inspect_chain,
    _inspect_gate,
    _inspect_levee,
    _inspect_marker,
    _present_seals,
    _search_seal,
    _talk_diver,
    _talk_ferrymaster,
    sablewater_augmentations,
)
from mud.veyra_city import VEYRA_RESIDENT_FLAG, VEYRA_SOUTH_SPRAWL_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def move_to(self, room_key: str) -> None:
        self.database.set_character_room(self.character.id, room_key)
        updated = self.database.get_character_by_name(self.character.name)
        assert updated is not None
        self.character = updated

    def text(self) -> str:
        return "".join(self.sent)


class SablewaterReachTests(unittest.TestCase):
    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "sablewater.db")
        account = database.create_account("riverwalker", "hash")
        character = database.create_character(account.id, "Riverwalker", "forest_elf", "brute")
        database.add_experience(character.id, 3000)
        database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
        database.set_character_room(character.id, SABLEWATER_NORTH_FERRY_KEY)
        character = database.get_character_by_name("Riverwalker")
        assert character is not None
        return tempdir, database, _Session(database, character)

    def test_midgame_direction_adds_thirteen_overworld_and_twelve_dungeon_rooms(self):
        self.assertEqual(len(SABLEWATER_ROOMS), 13)
        self.assertEqual(len(DROWNED_ROOMS), 12)
        self.assertEqual(len(ALL_SABLEWATER_ROOM_KEYS), 25)
        self.assertEqual(len(set(ALL_SABLEWATER_ROOM_KEYS)), 25)
        self.assertEqual(set(SABLEWATER_ROOM_KEYS).intersection(DROWNED_ROOM_KEYS), set())
        for room in SABLEWATER_ROOMS:
            self.assertEqual(room.region_key, "sablewater_reach")
            self.assertTrue(room.exits)
        for room in DROWNED_ROOMS:
            self.assertEqual(room.region_key, "drowned_tollhouse")
            self.assertTrue(room.exits)

    def test_veyra_south_road_is_residency_and_level_gated(self):
        exit_def = sablewater_augmentations()[VEYRA_SOUTH_SPRAWL_KEY].extra_exits[0]
        self.assertEqual(exit_def.destination_key, SABLEWATER_NORTH_FERRY_KEY)
        self.assertIn(VEYRA_RESIDENT_FLAG, exit_def.condition.required_flags)
        self.assertEqual(exit_def.condition.min_level, 6)

    def test_sablewater_story_is_hydrology_and_obsolete_infrastructure_not_gloam(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(asyncio.run(_talk_ferrymaster(session)))
            self.assertEqual(database.get_quest(session.character.id, LOW_WATER_QUEST_KEY)["current_step"], "inspect_levee")

            session.move_to(SABLEWATER_BROKEN_LEVEE_KEY)
            self.assertTrue(asyncio.run(_inspect_levee(session)))
            session.move_to(SABLEWATER_WILLOW_FERRY_KEY)
            self.assertTrue(asyncio.run(_inspect_chain(session)))
            session.move_to(SABLEWATER_NORTH_FERRY_KEY)
            self.assertTrue(asyncio.run(_talk_ferrymaster(session)))
            self.assertEqual(database.get_quest(session.character.id, LOW_WATER_QUEST_KEY)["status"], "completed")
            self.assertEqual(database.get_quest(session.character.id, TOLL_NOBODY_OWES_QUEST_KEY)["current_step"], "inspect_marker")

            session.move_to(SABLEWATER_OLD_CUSTOMS_KEY)
            self.assertTrue(asyncio.run(_inspect_marker(session)))
            session.move_to(SABLEWATER_TOLLHOUSE_MOUTH_KEY)
            self.assertTrue(asyncio.run(_inspect_gate(session)))
            self.assertTrue(asyncio.run(_talk_diver(session)))
            self.assertIn(TOLLHOUSE_UNLOCKED_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.get_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY)["current_step"], "defeat_warden")
            self.assertNotIn("Gloam", session.text())
        finally:
            tempdir.cleanup()

    def test_dungeon_requires_three_obsolete_seals_before_auditor_becomes_legal_target(self):
        tempdir, database, session = self._session()
        try:
            database.start_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY, "collect_seals")

            session.move_to(DROWNED_FLOODED_ARCHIVE_KEY)
            self.assertTrue(asyncio.run(_search_seal(session, "archive")))
            session.move_to(DROWNED_COIN_VAULT_KEY)
            self.assertTrue(asyncio.run(_search_seal(session, "vault")))
            session.move_to(DROWNED_MAGISTRATE_ROOM_KEY)
            self.assertTrue(asyncio.run(_search_seal(session, "magistrate")))
            self.assertEqual(database.get_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY)["current_step"], "present_seals")

            session.move_to(DROWNED_BRASS_TRIBUNAL_KEY)
            self.assertTrue(asyncio.run(_present_seals(session)))
            self.assertIn(AUDITOR_AUTHORIZED_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.get_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY)["current_step"], "defeat_auditor")

            tribunal = next(room for room in DROWNED_ROOMS if room.key == DROWNED_BRASS_TRIBUNAL_KEY)
            self.assertNotIn(BRASS_AUDITOR.key, tribunal.enemy_keys)
            self.assertGreater(BRASS_AUDITOR.max_hp, SLUICE_WARDEN.max_hp)
        finally:
            tempdir.cleanup()

    def test_auditor_exit_only_appears_after_boss_defeat_flag(self):
        augmentation = sablewater_augmentations()[DROWNED_BRASS_TRIBUNAL_KEY]
        east = next(exit_def for exit_def in augmentation.extra_exits if exit_def.direction == "east")
        self.assertIn("drowned_auditor_defeated", east.condition.required_flags)

    def test_production_server_assembles_sablewater_dungeon_and_economy_hooks(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.sablewater_reach import ALL_SABLEWATER_ROOM_KEYS, SABLEWATER_REED_FARMS_KEY, TARIFF_CRAB_KEY; "
            "from mud.economy_loop import ROOM_RESOURCE_NODE_KEYS, LOOT_TABLES; "
            "assert all(key in server.WORLD.legacy_rooms for key in ALL_SABLEWATER_ROOM_KEYS); "
            "assert 'cotton_patch' in ROOM_RESOURCE_NODE_KEYS[SABLEWATER_REED_FARMS_KEY]; "
            "assert TARIFF_CRAB_KEY in LOOT_TABLES; "
            "print('SABLEWATER_OK')"
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
        self.assertIn("SABLEWATER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
