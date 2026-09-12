from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
from mud.greywake_march import (
    AFTER_GLOAM_QUEST_KEY,
    BELL_BELOW_WIND_QUEST_KEY,
    FACTIONS,
    GREYWAKE_CHAIN_COMPLETE_FLAG,
    GREYWAKE_HEATH_KEY,
    GREYWAKE_RESONANT_ORCHARD_KEY,
    GREYWAKE_RIFTFIELD_KEY,
    GREYWAKE_ROOM_KEYS,
    GREYWAKE_ROOMS,
    GREYWAKE_SIGNAL_HILL_KEY,
    GREYWAKE_SURGE_VETERAN_FLAG,
    GREYWAKE_THREE_BANNER_KEY,
    GREYWAKE_VEYRA_GATE_KEY,
    LEDGER_FLAG,
    LANTERN_FLAG,
    ROADWARDEN_FLAG,
    SURGE_EVENT_ROOMS,
    SURGE_STATE,
    THREE_CLAIMS_QUEST_KEY,
    _ACTIVE_SESSIONS,
    _SURGE_PARTICIPANTS,
    _inspect_site,
    _rally_surge,
    _support_faction,
    greywake_augmentations,
)
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY


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


class GreywakeMarchTests(unittest.TestCase):
    def setUp(self) -> None:
        SURGE_STATE.active = False
        SURGE_STATE.remaining = 0
        SURGE_STATE.generation = 0
        _SURGE_PARTICIPANTS.clear()
        _ACTIVE_SESSIONS.clear()

    def _session(self, *, level_xp: int = 900):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "greywake.db")
        account = database.create_account("marchtester", "hash")
        character = database.create_character(account.id, "Marcher", "goblin", "druid")
        database.add_experience(character.id, level_xp)
        database.grant_flag(character.id, GLOAMWORKS_COMPLETE_FLAG)
        database.set_character_room(character.id, GREYWAKE_THREE_BANNER_KEY)
        character = database.get_character_by_name("Marcher")
        assert character is not None
        session = _Session(database, character)
        _ACTIVE_SESSIONS.add(session)
        return tempdir, database, session

    def test_march_extends_levels_five_to_ten_to_first_city_gate(self):
        self.assertEqual(len(GREYWAKE_ROOMS), 13)
        self.assertEqual(len(set(GREYWAKE_ROOM_KEYS)), 13)
        by_key = {room.key: room for room in GREYWAKE_ROOMS}
        self.assertEqual(set(by_key), set(GREYWAKE_ROOM_KEYS))
        for room in GREYWAKE_ROOMS:
            with self.subTest(room=room.key):
                self.assertEqual(room.region_key, "greywake_march")
                self.assertTrue(room.exits)
        self.assertIn("first_city_gate", by_key[GREYWAKE_VEYRA_GATE_KEY].tags)
        self.assertIn("future_city", by_key[GREYWAKE_VEYRA_GATE_KEY].tags)

    def test_greywake_access_requires_gloamworks_completion_and_level_five(self):
        augmentation = greywake_augmentations()[WAYMEET_GLOAM_MOUTH_KEY]
        east = next(item for item in augmentation.extra_exits if item.direction == "east")
        self.assertEqual(east.condition.min_level, 5)
        self.assertIn(GLOAMWORKS_COMPLETE_FLAG, east.condition.required_flags)
        self.assertEqual(east.destination_key, GREYWAKE_ROOM_KEYS[0])

    def test_three_factions_have_real_tradeoffs_and_distinct_persistent_support(self):
        self.assertEqual(len(FACTIONS), 3)
        self.assertEqual({f.support_flag for f in FACTIONS}, {ROADWARDEN_FLAG, LEDGER_FLAG, LANTERN_FLAG})
        for faction in FACTIONS:
            with self.subTest(faction=faction.name):
                self.assertTrue(faction.belief)
                self.assertTrue(faction.risk)
                self.assertNotIn("evil", faction.belief.lower())

    def test_after_gloam_observations_form_a_longer_regional_chain(self):
        tempdir, database, session = self._session()
        try:
            database.start_quest(session.character.id, AFTER_GLOAM_QUEST_KEY, "inspect_heath")
            session.move_to(GREYWAKE_HEATH_KEY)
            self.assertTrue(asyncio.run(_inspect_site(session, GREYWAKE_HEATH_KEY)))
            self.assertEqual(database.get_quest(session.character.id, AFTER_GLOAM_QUEST_KEY)["current_step"], "inspect_orchard")
            session.move_to(GREYWAKE_RESONANT_ORCHARD_KEY)
            self.assertTrue(asyncio.run(_inspect_site(session, GREYWAKE_RESONANT_ORCHARD_KEY)))
            self.assertEqual(database.get_quest(session.character.id, AFTER_GLOAM_QUEST_KEY)["current_step"], "inspect_riftfield")
            session.move_to(GREYWAKE_RIFTFIELD_KEY)
            self.assertTrue(asyncio.run(_inspect_site(session, GREYWAKE_RIFTFIELD_KEY)))
            self.assertEqual(database.get_quest(session.character.id, AFTER_GLOAM_QUEST_KEY)["current_step"], "return_camp")
        finally:
            tempdir.cleanup()

    def test_faction_support_is_a_choice_not_a_good_evil_lock(self):
        tempdir, database, session = self._session()
        try:
            database.start_quest(session.character.id, THREE_CLAIMS_QUEST_KEY, "pledge")
            session.move_to(GREYWAKE_THREE_BANNER_KEY)
            self.assertTrue(asyncio.run(_support_faction(session, "deep_ledger_consortium")))
            flags = database.list_flags(session.character.id)
            self.assertIn(LEDGER_FLAG, flags)
            self.assertNotIn(ROADWARDEN_FLAG, flags)
            self.assertNotIn(LANTERN_FLAG, flags)
            self.assertEqual(database.get_quest(session.character.id, THREE_CLAIMS_QUEST_KEY)["status"], "completed")
            self.assertEqual(database.get_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY)["current_step"], "rally")
            self.assertIn("other two banners remain standing", session.text())
        finally:
            tempdir.cleanup()

    def test_gloam_surge_is_shared_state_with_multiple_event_sites(self):
        tempdir, database, session = self._session(level_xp=1500)
        try:
            database.start_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY, "rally")
            session.move_to(GREYWAKE_SIGNAL_HILL_KEY)
            self.assertTrue(asyncio.run(_rally_surge(session, strength=3)))
            self.assertTrue(SURGE_STATE.active)
            self.assertEqual(SURGE_STATE.remaining, 3)
            self.assertEqual(len(SURGE_EVENT_ROOMS), 3)
            self.assertIn(GREYWAKE_HEATH_KEY, SURGE_EVENT_ROOMS)
            self.assertIn(GREYWAKE_RIFTFIELD_KEY, SURGE_EVENT_ROOMS)
            self.assertEqual(database.get_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY)["current_step"], "break_surge")
            self.assertFalse(SURGE_STATE.record_kill())
            self.assertFalse(SURGE_STATE.record_kill())
            self.assertTrue(SURGE_STATE.record_kill())
            self.assertFalse(SURGE_STATE.active)
            self.assertEqual(SURGE_STATE.remaining, 0)
        finally:
            tempdir.cleanup()

    def test_production_server_assembles_march_after_dungeon(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.greywake_march import GREYWAKE_ROOM_KEYS, GREYWAKE_SIGNAL_HILL_KEY, FACTIONS; "
            "assert all(key in server.WORLD.legacy_rooms for key in GREYWAKE_ROOM_KEYS); "
            "assert len(FACTIONS) == 3; "
            "assert GREYWAKE_SIGNAL_HILL_KEY in server.WORLD.augmentations; "
            "print('GREYWAKE_OK')"
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
        self.assertIn("GREYWAKE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
