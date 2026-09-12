from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.greywake_march import GREYWAKE_CHAIN_COMPLETE_FLAG, GREYWAKE_VEYRA_GATE_KEY, LEDGER_FLAG
from mud.veyra_city import (
    VEYRA_ARRIVAL_QUEST_KEY,
    VEYRA_BRASSMARKET_KEY,
    VEYRA_CIVIC_STEPS_KEY,
    VEYRA_EXCHANGE_KEY,
    VEYRA_FACTION_RANK_FLAG,
    VEYRA_FACTION_SERVICE_QUEST_KEY,
    VEYRA_FIVE_WAYS_KEY,
    VEYRA_GATE_WARD_KEY,
    VEYRA_GRAND_CROSSING_KEY,
    VEYRA_HAMMER_HALL_KEY,
    VEYRA_KEYHOUSE_KEY,
    VEYRA_LOOM_HALL_KEY,
    VEYRA_NOTICE_HALL_KEY,
    VEYRA_RESIDENT_FLAG,
    VEYRA_ROOM_KEYS,
    VEYRA_ROOMS,
    VEYRA_LEDGER_OFFICE_KEY,
    _advance_arrival_by_room,
    _ensure_arrival_quest,
    _listing_capacity,
    _read_board,
    _talk_faction_office,
    _talk_steward,
    _train,
    _do_faction_fieldwork,
    create_market_listing,
    deposit_to_vault,
    fill_market_listing,
    list_market,
    veyra_augmentations,
    withdraw_from_vault,
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
        updated = self.database.get_character_by_name(self.character.name)
        assert updated is not None
        self.character = updated

    def text(self) -> str:
        return "".join(self.sent)


class VeyraCityTests(unittest.TestCase):
    def _db(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "veyra.db")
        return tempdir, database

    def _character(self, database: Database, name: str = "Citywalker"):
        account = database.create_account(name.lower(), "hash")
        character = database.create_character(account.id, name, "human", "wizard")
        database.add_experience(character.id, 3000)
        database.grant_flag(character.id, GREYWAKE_CHAIN_COMPLETE_FLAG)
        database.set_character_room(character.id, VEYRA_GATE_WARD_KEY)
        character = database.get_character_by_name(name)
        assert character is not None
        return character

    def test_city_has_twenty_five_connected_service_rooms_and_real_gate(self):
        self.assertEqual(len(VEYRA_ROOMS), 25)
        self.assertEqual(len(set(VEYRA_ROOM_KEYS)), 25)
        by_key = {room.key: room for room in VEYRA_ROOMS}
        self.assertEqual(set(by_key), set(VEYRA_ROOM_KEYS))
        for room in VEYRA_ROOMS:
            with self.subTest(room=room.key):
                self.assertEqual(room.region_key, "veyra_city")
                self.assertTrue(room.exits)
                self.assertIn("city", room.tags)
        gate_exits = veyra_augmentations()[GREYWAKE_VEYRA_GATE_KEY].extra_exits
        self.assertEqual(len(gate_exits), 1)
        self.assertEqual(gate_exits[0].destination_key, VEYRA_GATE_WARD_KEY)
        self.assertIn(GREYWAKE_CHAIN_COMPLETE_FLAG, gate_exits[0].condition.required_flags)
        self.assertEqual(gate_exits[0].condition.min_level, 8)

    def test_arrival_tour_turns_city_services_into_playable_progression(self):
        tempdir, database = self._db()
        try:
            session = _Session(database, self._character(database))
            self.assertTrue(_ensure_arrival_quest(session))
            self.assertEqual(database.get_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY)["current_step"], "reach_crossing")

            session.move_to(VEYRA_GRAND_CROSSING_KEY)
            self.assertIsNotNone(_advance_arrival_by_room(session))
            session.move_to(VEYRA_BRASSMARKET_KEY)
            self.assertIsNotNone(_advance_arrival_by_room(session))
            session.move_to(VEYRA_KEYHOUSE_KEY)
            self.assertIsNotNone(_advance_arrival_by_room(session))
            session.move_to(VEYRA_FIVE_WAYS_KEY)
            asyncio.run(_train(session))
            self.assertEqual(database.get_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY)["current_step"], "read_board")
            session.move_to(VEYRA_NOTICE_HALL_KEY)
            asyncio.run(_read_board(session))
            self.assertEqual(database.get_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY)["current_step"], "report_steward")
            session.move_to(VEYRA_CIVIC_STEPS_KEY)
            asyncio.run(_talk_steward(session))
            self.assertEqual(database.get_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY)["status"], "completed")
            self.assertIn(VEYRA_RESIDENT_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.get_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY)["status"], "active")
            self.assertIn("belonging", session.text())
        finally:
            tempdir.cleanup()

    def test_keyhouse_moves_real_inventory_into_persistent_vault_and_back(self):
        tempdir, database = self._db()
        try:
            character = self._character(database)
            database.set_character_room(character.id, VEYRA_KEYHOUSE_KEY)
            character = database.get_character_by_name(character.name)
            assert character is not None
            session = _Session(database, character)
            database.add_item(character.id, "iron_ore", 3)

            ok, text = deposit_to_vault(session, "iron ore", 2)
            self.assertTrue(ok, text)
            self.assertEqual(database.item_quantity(character.id, "iron_ore"), 1)
            ok, text = withdraw_from_vault(session, "iron ore", 1)
            self.assertTrue(ok, text)
            self.assertEqual(database.item_quantity(character.id, "iron_ore"), 2)
        finally:
            tempdir.cleanup()

    def test_exchange_is_real_persistent_player_to_player_barter_with_escrow(self):
        tempdir, database = self._db()
        try:
            seller = self._character(database, "Seller")
            buyer = self._character(database, "Buyer")
            database.set_character_room(seller.id, VEYRA_EXCHANGE_KEY)
            database.set_character_room(buyer.id, VEYRA_EXCHANGE_KEY)
            seller = database.get_character_by_name("Seller")
            buyer = database.get_character_by_name("Buyer")
            assert seller is not None and buyer is not None
            seller_session = _Session(database, seller)
            buyer_session = _Session(database, buyer)
            database.add_item(seller.id, "iron_ore", 2)
            database.add_item(buyer.id, "cotton_thread", 1)

            ok, text = create_market_listing(seller_session, "iron ore", 2, "cotton thread", 1)
            self.assertTrue(ok, text)
            self.assertEqual(database.item_quantity(seller.id, "iron_ore"), 0)
            rows = list_market(database)
            self.assertEqual(len(rows), 1)
            listing_id = int(rows[0]["id"])

            ok, text = fill_market_listing(buyer_session, listing_id)
            self.assertTrue(ok, text)
            self.assertEqual(database.item_quantity(buyer.id, "iron_ore"), 2)
            self.assertEqual(database.item_quantity(buyer.id, "cotton_thread"), 0)
            self.assertEqual(database.item_quantity(seller.id, "cotton_thread"), 1)
            self.assertEqual(list_market(database), [])
        finally:
            tempdir.cleanup()

    def test_greywake_faction_choice_becomes_a_concrete_city_perk(self):
        tempdir, database = self._db()
        try:
            character = self._character(database)
            database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
            database.grant_flag(character.id, LEDGER_FLAG)
            database.start_quest(character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "report_office")
            database.set_character_room(character.id, VEYRA_LEDGER_OFFICE_KEY)
            character = database.get_character_by_name(character.name)
            assert character is not None
            session = _Session(database, character)

            asyncio.run(_talk_faction_office(session, "ledger"))
            session.move_to(VEYRA_BRASSMARKET_KEY)
            asyncio.run(_do_faction_fieldwork(session, "cargo"))
            session.move_to(VEYRA_LEDGER_OFFICE_KEY)
            asyncio.run(_talk_faction_office(session, "ledger"))

            self.assertIn(VEYRA_FACTION_RANK_FLAG, database.list_flags(character.id))
            self.assertEqual(_listing_capacity(session), 5)
            self.assertEqual(database.get_quest(character.id, VEYRA_FACTION_SERVICE_QUEST_KEY)["status"], "completed")
        finally:
            tempdir.cleanup()

    def test_production_server_assembles_city_services_and_craft_halls(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.veyra_city import VEYRA_ROOM_KEYS, VEYRA_HAMMER_HALL_KEY, VEYRA_LOOM_HALL_KEY; "
            "from mud.economy_loop import ROOM_STATIONS; "
            "assert all(key in server.WORLD.legacy_rooms for key in VEYRA_ROOM_KEYS); "
            "assert 'forge' in ROOM_STATIONS[VEYRA_HAMMER_HALL_KEY]; "
            "assert 'loom' in ROOM_STATIONS[VEYRA_LOOM_HALL_KEY]; "
            "print('VEYRA_OK')"
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
        self.assertIn("VEYRA_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
