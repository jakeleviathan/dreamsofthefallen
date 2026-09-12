from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from mud.database import Database
from mud.greywake_march import LEDGER_FLAG, ROADWARDEN_FLAG
from mud.mechanics import PROGRESSION_RULES
from mud.veyra_city import (
    VEYRA_CARAVAN_COURT_KEY,
    VEYRA_FACTION_RANK_FLAG,
    VEYRA_LEDGER_OFFICE_KEY,
    VEYRA_NOTICE_HALL_KEY,
    VEYRA_RESIDENT_FLAG,
)
from mud.veyra_living_core import (
    RANK_THRESHOLDS,
    _accept_weekly_contract,
    _promote,
    _turn_in_weekly_contract,
    ensure_faction_standing,
    ensure_living_core_tables,
    living_listing_capacity,
    living_vault_capacity,
    market_day,
    weekly_contract,
)
from mud.waymeet_frontier import WAYMEET_SCRIP_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def show_current_room(self) -> None:
        return None

    def move_to(self, room_key: str) -> None:
        self.database.set_character_room(self.character.id, room_key)
        self.refresh()

    def refresh(self) -> None:
        current = self.database.get_character_by_name(self.character.name)
        assert current is not None
        self.character = current


class VeyraLivingCoreTests(unittest.TestCase):
    def _session(self, faction_flag: str = LEDGER_FLAG):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "living.db")
        account = database.create_account("livingtester", "hash")
        character = database.create_character(account.id, "LivingRoad", "human", "wizard")
        database.add_experience(character.id, PROGRESSION_RULES.cumulative_xp_for_level(8))
        database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
        database.grant_flag(character.id, faction_flag)
        database.grant_flag(character.id, VEYRA_FACTION_RANK_FLAG)
        character = database.get_character_by_name("LivingRoad")
        assert character is not None
        session = _Session(database, character)
        ensure_living_core_tables(database)
        ensure_faction_standing(session)
        return tempdir, database, session

    def test_daily_market_rotation_is_calendar_driven_and_material_specific(self):
        monday = market_day(date(2026, 9, 7))
        tuesday = market_day(date(2026, 9, 8))
        self.assertEqual(monday.key, "smiths_day")
        self.assertEqual(tuesday.key, "cloth_day")
        self.assertNotEqual(monday.demands, tuesday.demands)
        self.assertIn("iron_ore", {entry.item_key for entry in monday.demands})
        self.assertIn("raw_cotton", {entry.item_key for entry in tuesday.demands})

    def test_weekly_contract_rotation_is_stable_inside_a_week(self):
        week_a, contract_a = weekly_contract(date(2026, 9, 7))
        week_b, contract_b = weekly_contract(date(2026, 9, 10))
        next_week, next_contract = weekly_contract(date(2026, 9, 14))
        self.assertEqual(week_a, week_b)
        self.assertEqual(contract_a.key, contract_b.key)
        self.assertNotEqual(week_a, next_week)
        self.assertNotEqual(contract_a.key, next_contract.key)

    def test_public_weekly_contract_consumes_real_material_and_builds_faction_service(self):
        tempdir, database, session = self._session(LEDGER_FLAG)
        try:
            session.move_to(VEYRA_NOTICE_HALL_KEY)
            _week_id, contract = weekly_contract()
            database.add_item(session.character.id, contract.item_key, contract.quantity)
            self.assertTrue(asyncio.run(_accept_weekly_contract(session)))
            self.assertTrue(asyncio.run(_turn_in_weekly_contract(session)))
            self.assertEqual(database.item_quantity(session.character.id, contract.item_key), 0)
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), contract.scrip_reward)
            standing = ensure_faction_standing(session)
            assert standing is not None
            self.assertEqual(standing[1], 1)
        finally:
            tempdir.cleanup()

    def test_rank_two_ledger_gets_more_listings_with_less_general_vault_space(self):
        tempdir, database, session = self._session(LEDGER_FLAG)
        try:
            with database.connect() as db:
                db.execute(
                    "UPDATE veyra_faction_standing SET rank = 2, service_points = ? WHERE character_id = ?",
                    (RANK_THRESHOLDS[2], session.character.id),
                )
            self.assertEqual(living_listing_capacity(session), 7)
            self.assertEqual(living_vault_capacity(session), 35)
        finally:
            tempdir.cleanup()

    def test_promotion_is_explicit_at_the_characters_own_office(self):
        tempdir, database, session = self._session(LEDGER_FLAG)
        try:
            with database.connect() as db:
                db.execute(
                    "UPDATE veyra_faction_standing SET service_points = ? WHERE character_id = ?",
                    (RANK_THRESHOLDS[2], session.character.id),
                )
            session.move_to(VEYRA_LEDGER_OFFICE_KEY)
            self.assertTrue(asyncio.run(_promote(session)))
            standing = ensure_faction_standing(session)
            assert standing is not None
            self.assertEqual(standing[2], 2)
            self.assertIn("Rank 2", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_roadwarden_rank_two_unlocks_sablewater_transit_but_keeps_a_storage_tradeoff(self):
        tempdir, database, session = self._session(ROADWARDEN_FLAG)
        try:
            with database.connect() as db:
                db.execute(
                    "UPDATE veyra_faction_standing SET rank = 2, service_points = 3 WHERE character_id = ?",
                    (session.character.id,),
                )
            session.move_to(VEYRA_CARAVAN_COURT_KEY)
            self.assertEqual(living_vault_capacity(session), 35)
        finally:
            tempdir.cleanup()

    def test_production_server_installs_living_core_layer(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "assert getattr(server.PlayerSession, '_veyra_living_core_installed', False); "
            "from mud.veyra_living_core import MARKET_DAYS, WEEKLY_CONTRACTS; "
            "assert len(MARKET_DAYS) == 7; assert len(WEEKLY_CONTRACTS) == 4; "
            "print('VEYRA_LIVING_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("VEYRA_LIVING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
