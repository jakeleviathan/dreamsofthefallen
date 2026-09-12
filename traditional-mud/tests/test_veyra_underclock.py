from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.mechanics import PROGRESSION_RULES
from mud.veyra_city import VEYRA_NORTH_WATERWORKS_KEY, VEYRA_RESIDENT_FLAG
from mud.veyra_underclock import (
    CINDER_GOVERNOR,
    GOVERNOR_BLED_FLAG,
    GOVERNOR_DEFEATED_FLAG,
    GOVERNOR_KEY,
    INTAKE_SET_FLAG,
    FLYWHEEL_LOCKED_FLAG,
    UNDERCLOCK_COMPLETE_FLAG,
    UNDERCLOCK_FLYWHEEL_KEY,
    UNDERCLOCK_GAUGE_KEY,
    UNDERCLOCK_GOVERNOR_KEY,
    UNDERCLOCK_INTAKE_KEY,
    UNDERCLOCK_MINUTE_KEY,
    UNDERCLOCK_PISTON_KEY,
    UNDERCLOCK_QUEST_KEY,
    UNDERCLOCK_ROOM_KEYS,
    UNDERCLOCK_ROOMS,
    UNDERCLOCK_STEAM_KEY,
    UNDERCLOCK_TEETH_KEY,
    _ensure_quest,
    _read_gauge,
    _set_control,
    _start_lift,
    _timed_cross,
    clock_state,
    set_underclock_phase_for_tests,
    underclock_augmentations,
)


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []
        self.combatant = SimpleNamespace(current_movement=100)
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None

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


class UnderclockTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_underclock_phase_for_tests(None)

    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "underclock.db")
        account = database.create_account("clocktester", "hash")
        character = database.create_character(account.id, "Clockhand", "dwarf", "brute")
        database.add_experience(character.id, PROGRESSION_RULES.cumulative_xp_for_level(8))
        database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
        database.set_character_room(character.id, UNDERCLOCK_INTAKE_KEY)
        character = database.get_character_by_name("Clockhand")
        assert character is not None
        return tempdir, database, _Session(database, character)

    def test_dungeon_has_twelve_rooms_and_waterworks_entry_is_level_and_residency_gated(self):
        self.assertEqual(len(UNDERCLOCK_ROOMS), 12)
        self.assertEqual(len(set(UNDERCLOCK_ROOM_KEYS)), 12)
        by_key = {room.key: room for room in UNDERCLOCK_ROOMS}
        self.assertEqual(set(by_key), set(UNDERCLOCK_ROOM_KEYS))
        for room in UNDERCLOCK_ROOMS:
            self.assertEqual(room.region_key, "veyra_underclock")
        entry = underclock_augmentations()[VEYRA_NORTH_WATERWORKS_KEY].extra_exits[0]
        self.assertEqual(entry.destination_key, UNDERCLOCK_INTAKE_KEY)
        self.assertEqual(entry.condition.min_level, 8)
        self.assertIn(VEYRA_RESIDENT_FLAG, entry.condition.required_flags)

    def test_clock_is_a_real_four_phase_repeating_cycle(self):
        self.assertEqual(clock_state(0).phase, "intake")
        self.assertEqual(clock_state(8).phase, "pressure")
        self.assertEqual(clock_state(16).phase, "vent")
        self.assertEqual(clock_state(24).phase, "reset")
        self.assertEqual(clock_state(32).phase, "intake")

    def test_wrong_timing_blocks_crossing_and_costs_movement(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            session.move_to(UNDERCLOCK_GAUGE_KEY)
            self.assertTrue(asyncio.run(_read_gauge(session)))
            session.move_to(UNDERCLOCK_PISTON_KEY)
            set_underclock_phase_for_tests("pressure")
            self.assertTrue(asyncio.run(_timed_cross(
                session, room_key=UNDERCLOCK_PISTON_KEY, safe_phase="reset", destination=UNDERCLOCK_FLYWHEEL_KEY,
                flag="underclock_pistons_crossed", expected_step="cross_pistons", next_step="cross_steam", label="the Piston Gallery",
            )))
            self.assertEqual(session.character.current_room, UNDERCLOCK_PISTON_KEY)
            self.assertEqual(session.combatant.current_movement, 94)
            self.assertIn("Safe beat: RESET", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_correct_timing_turns_the_machine_into_traversable_space(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            session.move_to(UNDERCLOCK_GAUGE_KEY)
            asyncio.run(_read_gauge(session))
            session.move_to(UNDERCLOCK_PISTON_KEY)
            set_underclock_phase_for_tests("reset")
            self.assertTrue(asyncio.run(_timed_cross(
                session, room_key=UNDERCLOCK_PISTON_KEY, safe_phase="reset", destination=UNDERCLOCK_FLYWHEEL_KEY,
                flag="underclock_pistons_crossed", expected_step="cross_pistons", next_step="cross_steam", label="the Piston Gallery",
            )))
            self.assertEqual(session.character.current_room, UNDERCLOCK_FLYWHEEL_KEY)
            quest = database.get_quest(session.character.id, UNDERCLOCK_QUEST_KEY)
            self.assertEqual(quest["current_step"], "cross_steam")
        finally:
            tempdir.cleanup()

    def test_walking_teeth_signature_crossing_only_opens_during_vent(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "cross_teeth")
            session.move_to(UNDERCLOCK_TEETH_KEY)
            set_underclock_phase_for_tests("vent")
            self.assertTrue(asyncio.run(_timed_cross(
                session, room_key=UNDERCLOCK_TEETH_KEY, safe_phase="vent", destination=UNDERCLOCK_GOVERNOR_KEY,
                flag="underclock_teeth_crossed", expected_step="cross_teeth", next_step="calibrate_governor", label="the Walking Teeth",
            )))
            self.assertEqual(session.character.current_room, UNDERCLOCK_GOVERNOR_KEY)
            self.assertIn("pretending to be architecture", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_governor_controls_require_three_different_clock_beats(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "calibrate_governor")
            session.move_to(UNDERCLOCK_GOVERNOR_KEY)

            set_underclock_phase_for_tests("intake")
            self.assertTrue(asyncio.run(_set_control(session, "intake")))
            set_underclock_phase_for_tests("reset")
            self.assertTrue(asyncio.run(_set_control(session, "flywheel")))
            set_underclock_phase_for_tests("vent")
            self.assertTrue(asyncio.run(_set_control(session, "bleed")))

            flags = set(database.list_flags(session.character.id))
            self.assertTrue({INTAKE_SET_FLAG, FLYWHEEL_LOCKED_FLAG, GOVERNOR_BLED_FLAG}.issubset(flags))
            quest = database.get_quest(session.character.id, UNDERCLOCK_QUEST_KEY)
            self.assertEqual(quest["current_step"], "engage_governor")
            self.assertEqual(CINDER_GOVERNOR.key, GOVERNOR_KEY)
        finally:
            tempdir.cleanup()

    def test_restart_lift_finishes_grounded_city_service_story(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "restart_lift")
            database.grant_flag(session.character.id, GOVERNOR_DEFEATED_FLAG)
            session.move_to(UNDERCLOCK_MINUTE_KEY)
            self.assertTrue(asyncio.run(_start_lift(session)))
            quest = database.get_quest(session.character.id, UNDERCLOCK_QUEST_KEY)
            self.assertEqual(quest["status"], "completed")
            self.assertIn(UNDERCLOCK_COMPLETE_FLAG, database.list_flags(session.character.id))
            self.assertIn("tap that would have run dry tomorrow simply keeps working", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_production_server_assembles_underclock(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.veyra_underclock import UNDERCLOCK_ROOM_KEYS, UNDERCLOCK_QUEST_KEY; "
            "from mud.quests import QUESTS_BY_KEY; "
            "assert all(key in server.WORLD.legacy_rooms for key in UNDERCLOCK_ROOM_KEYS); "
            "assert UNDERCLOCK_QUEST_KEY in QUESTS_BY_KEY; "
            "assert getattr(server.PlayerSession, '_underclock_runtime_installed', False); "
            "print('UNDERCLOCK_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("UNDERCLOCK_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
