from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.living_world_depth as depth
import mud.living_world_depth_tuning as tuning
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY


class DummyClock:
    def __init__(self, moment: AstralisMoment) -> None:
        self.moment = moment

    def now(self, real_seconds=None) -> AstralisMoment:
        return self.moment


class DummySession:
    def __init__(self, database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)

    def refresh(self) -> None:
        value = self.database.get_character_by_name(self.character.name)
        assert value is not None
        self.character = value


class LivingWorldDepthTuningTests(unittest.TestCase):
    @staticmethod
    def _moment(day: int, hour: int = 18) -> AstralisMoment:
        return AstralisMoment(
            day_number=day,
            hour=hour,
            minute=0,
            total_minutes=((day - 1) * 24 * 60) + hour * 60,
        )

    def _session(self, root: Path):
        database = Database(root / "depth_tuning.db")
        account = database.create_account("depth_tuning", "x")
        character = database.create_character(account.id, "NoteGuard", "human", "brute")
        database.set_character_room(character.id, WAYMEET_COMMONHOUSE_KEY)
        character = database.get_character_by_name("NoteGuard")
        return DummySession(database, character)

    def test_phase_aliases_normalize_to_real_astralis_clock_phases(self):
        tuning._DEPTH_TUNING_APPLIED = False
        # Restore a representative human-language phase if another production
        # import normalized the module earlier in this test process.
        original = depth.AMBIENT_SCENES
        try:
            depth.AMBIENT_SCENES = tuple(
                type(scene)(scene.key, scene.room_key, tuple("morning" if p == "dawn" else "evening" if p == "dusk" else p for p in scene.phases), scene.text)
                for scene in original
            )
            tuning.apply_living_world_depth_tuning()
            phases = {phase for scene in depth.AMBIENT_SCENES for phase in scene.phases}
            self.assertNotIn("morning", phases)
            self.assertNotIn("evening", phases)
            self.assertTrue(phases.issubset({"dawn", "day", "dusk", "night"}))
        finally:
            depth.AMBIENT_SCENES = original
            tuning._DEPTH_TUNING_APPLIED = False
            tuning.apply_living_world_depth_tuning()

    def test_removing_note_does_not_bypass_three_day_posting_cooldown(self):
        tuning._DEPTH_TUNING_APPLIED = False
        tuning.apply_living_world_depth_tuning()
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            day = self._moment(40)
            with patch.object(depth, "ASTRALIS_CLOCK", DummyClock(day)):
                asyncio.run(depth._pin_note(session, "First note."))
                rows = depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 40)
                self.assertEqual(len(rows), 1)
                asyncio.run(depth._remove_note(session, int(rows[0]["id"])))
                asyncio.run(depth._pin_note(session, "Trying to repost immediately."))
            self.assertEqual(depth._active_notes(session, WAYMEET_COMMONHOUSE_KEY, 40), [])
            self.assertIn("breathing room", "".join(session.messages).lower())
            self.assertEqual(depth._days_until_note_allowed(session, 40), 3)
            self.assertEqual(depth._days_until_note_allowed(session, 43), 0)


if __name__ == "__main__":
    unittest.main()
