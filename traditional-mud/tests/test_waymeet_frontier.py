from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.waymeet_frontier import (
    GLOAM_DELVER,
    HOMELAND_LINKS,
    REEDMAW_BOAR,
    SLATEBACK_CLAW_KEY,
    SLATEBACK_SKULK,
    THORNBACK_FANG_KEY,
    THORNBACK_JACKAL,
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_CULVERT_KEY,
    WAYMEET_GLOAM_MOUTH_KEY,
    WAYMEET_INTRO_COMPLETE_FLAG,
    WAYMEET_INTRO_QUEST_KEY,
    WAYMEET_JACKAL_QUEST_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_QUARRY_KEY,
    WAYMEET_QUARRY_QUEST_KEY,
    WAYMEET_ROOM_KEYS,
    WAYMEET_ROOMS,
    WAYMEET_SCRIP_KEY,
    _buy_market,
    _ensure_intro,
    _inspect_collapse,
    _inspect_gloam,
    _talk_foreman,
    _talk_marshal,
    _talk_warden,
    waymeet_augmentations,
)


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

    def text(self) -> str:
        return "".join(self.sent)


class WaymeetFrontierTests(unittest.TestCase):
    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "waymeet.db")
        account = database.create_account("waymeettester", "hash")
        character = database.create_character(account.id, "Roadwalker", "human", "wizard")
        database.set_character_room(character.id, WAYMEET_CROSSROADS_KEY)
        character = database.get_character_by_name("Roadwalker")
        assert character is not None
        return tempdir, database, _Session(database, character)

    def test_zone_has_a_dozen_plus_connected_rooms_and_four_shared_approaches(self):
        self.assertEqual(len(WAYMEET_ROOMS), 13)
        self.assertEqual(len(set(WAYMEET_ROOM_KEYS)), 13)
        by_key = {room.key: room for room in WAYMEET_ROOMS}
        self.assertEqual(set(by_key), set(WAYMEET_ROOM_KEYS))
        for room in WAYMEET_ROOMS:
            with self.subTest(room=room.key):
                self.assertEqual(room.region_key, "waymeet_frontier")
                self.assertTrue(room.exits)
        self.assertEqual(len(HOMELAND_LINKS), 8)
        self.assertEqual(len({link[0] for link in HOMELAND_LINKS}), 8)

    def test_homeland_links_are_completion_and_level_gated(self):
        augmentations = waymeet_augmentations()
        for room_key, direction, destination, _name, completion_flag in HOMELAND_LINKS:
            with self.subTest(room=room_key):
                exits = [item for item in augmentations[room_key].extra_exits if item.direction == direction]
                self.assertEqual(len(exits), 1)
                self.assertEqual(exits[0].destination_key, destination)
                self.assertIn(completion_flag, exits[0].condition.required_flags)
                self.assertEqual(exits[0].condition.min_level, 2)

    def test_combat_curve_steps_up_toward_gloam_mouth(self):
        self.assertLess(THORNBACK_JACKAL.max_hp, REEDMAW_BOAR.max_hp)
        self.assertLess(REEDMAW_BOAR.max_hp, SLATEBACK_SKULK.max_hp)
        self.assertLess(SLATEBACK_SKULK.max_hp, GLOAM_DELVER.max_hp)
        self.assertLess(THORNBACK_JACKAL.xp_reward, GLOAM_DELVER.xp_reward)
        by_key = {room.key: room for room in WAYMEET_ROOMS}
        self.assertIn(THORNBACK_JACKAL.key, by_key[WAYMEET_BROKEN_MILE_KEY].enemy_keys)
        self.assertIn(SLATEBACK_SKULK.key, by_key[WAYMEET_QUARRY_KEY].enemy_keys)
        self.assertIn(GLOAM_DELVER.key, by_key[WAYMEET_GLOAM_MOUTH_KEY].enemy_keys)

    def test_intro_quest_walks_from_crossroads_to_first_dungeon_hint(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_intro(session))
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)["current_step"], "talk_marshal")

            self.assertTrue(asyncio.run(_talk_marshal(session)))
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)["current_step"], "inspect_broken_mile")

            session.move_to(WAYMEET_BROKEN_MILE_KEY)
            self.assertTrue(asyncio.run(_inspect_collapse(session)))
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)["current_step"], "reach_gloam")

            database.advance_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY, "inspect_gloam")
            session.move_to(WAYMEET_GLOAM_MOUTH_KEY)
            self.assertTrue(asyncio.run(_inspect_gloam(session)))
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)["current_step"], "return_marshal")

            session.move_to(WAYMEET_CROSSROADS_KEY)
            self.assertTrue(asyncio.run(_talk_marshal(session)))
            quest = database.get_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)
            self.assertEqual(quest["status"], "completed")
            self.assertIn(WAYMEET_INTRO_COMPLETE_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 2)
            self.assertIn("Gloamworks", session.text())
        finally:
            tempdir.cleanup()

    def test_repeatable_contracts_consume_proof_and_can_be_started_again(self):
        tempdir, database, session = self._session()
        try:
            session.move_to(WAYMEET_BROKEN_MILE_KEY)
            database.add_item(session.character.id, THORNBACK_FANG_KEY, 3)
            self.assertTrue(asyncio.run(_talk_warden(session)))
            self.assertEqual(database.item_quantity(session.character.id, THORNBACK_FANG_KEY), 0)
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_JACKAL_QUEST_KEY)["status"], "completed")
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 1)
            self.assertTrue(asyncio.run(_talk_warden(session)))
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_JACKAL_QUEST_KEY)["status"], "active")

            session.move_to(WAYMEET_QUARRY_KEY)
            database.add_item(session.character.id, SLATEBACK_CLAW_KEY, 2)
            self.assertTrue(asyncio.run(_talk_foreman(session)))
            self.assertEqual(database.item_quantity(session.character.id, SLATEBACK_CLAW_KEY), 0)
            self.assertEqual(database.get_quest(session.character.id, WAYMEET_QUARRY_QUEST_KEY)["status"], "completed")
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 2)
        finally:
            tempdir.cleanup()

    def test_market_turns_local_contract_scrip_into_useful_economy_inputs(self):
        tempdir, database, session = self._session()
        try:
            session.move_to(WAYMEET_LANTERN_MARKET_KEY)
            database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 3)
            self.assertTrue(asyncio.run(_buy_market(session, "iron")))
            self.assertEqual(database.item_quantity(session.character.id, "iron_ore"), 1)
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 2)
            self.assertTrue(asyncio.run(_buy_market(session, "thread")))
            self.assertEqual(database.item_quantity(session.character.id, "cotton_thread"), 1)
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 0)
        finally:
            tempdir.cleanup()

    def test_production_server_assembles_waymeet_with_economy_and_runtime_layers(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.waymeet_frontier import WAYMEET_ROOM_KEYS, WAYMEET_CRAFT_ROW_KEY, WAYMEET_QUARRY_KEY; "
            "from mud.economy_loop import ROOM_RESOURCE_NODE_KEYS, ROOM_STATIONS; "
            "assert all(key in server.WORLD.legacy_rooms for key in WAYMEET_ROOM_KEYS); "
            "assert 'iron_vein' in ROOM_RESOURCE_NODE_KEYS[WAYMEET_QUARRY_KEY]; "
            "assert 'forge' in ROOM_STATIONS[WAYMEET_CRAFT_ROW_KEY]; "
            "print('WAYMEET_OK')"
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
        self.assertIn("WAYMEET_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
