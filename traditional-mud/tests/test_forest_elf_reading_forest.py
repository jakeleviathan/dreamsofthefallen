from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.forest_elf_reading_forest import (
    BARKJAW,
    BARKJAW_AVOIDED_FLAG,
    HOLLOWBACK,
    PATH_SIGN_READ_FLAG,
    PATH_WARNING_HEARD_FLAG,
    RIVER_MOSS_BUNDLE_KEY,
    STAG_RESCUED_FLAG,
    WHAT_DID_YOU_HEAR,
    WHAT_DID_YOU_HEAR_COMPLETE_FLAG,
    WHITEWOOD_LOOKOUT,
    WHITEWOOD_LOOKOUT_KEY,
    _advance_to_stag,
    _handle_listening_pool,
    _handle_lookout,
    _handle_stag,
    reading_forest_augmentations,
    start_reading_forest_if_ready,
)
from mud.quests import FOREST_ELF_FIRST_WALK
from mud.world import FOREST_ELF_LISTENING_POOL_KEY, FOREST_ELF_OUTER_GROVE_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.active_enemy = None
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def refresh(self) -> None:
        current = self.database.get_character_by_name(self.character.name)
        assert current is not None
        self.character = current

    def text(self) -> str:
        return "".join(self.sent)


class ForestElfReadingForestTests(unittest.TestCase):
    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "mud.db")
        account = database.create_account("forestreader", "hash")
        character = database.create_character(account.id, "Willowread", "forest_elf", "wizard")
        return tempdir, database, _Session(database, character)

    def test_content_is_action_first_and_adds_memorable_forest_elements(self):
        self.assertEqual(WHAT_DID_YOU_HEAR.name, "What Did You Hear?")
        self.assertIn("LISTEN", WHAT_DID_YOU_HEAR.objective_for_step("read_path"))
        self.assertIn("FREE STAG", WHAT_DID_YOU_HEAR.objective_for_step("decide_stag"))
        self.assertEqual(WHITEWOOD_LOOKOUT.key, WHITEWOOD_LOOKOUT_KEY)
        self.assertTrue(WHITEWOOD_LOOKOUT.exits)

        augmentations = reading_forest_augmentations()
        pool_features = {feature.key for feature in augmentations[FOREST_ELF_LISTENING_POOL_KEY].features}
        grove_features = {feature.key for feature in augmentations[FOREST_ELF_OUTER_GROVE_KEY].features}
        self.assertIn("underbird_warning", pool_features)
        self.assertIn("veering_deer_sign", pool_features)
        self.assertIn("snared_whitewood_stag", grove_features)

        self.assertLess(BARKJAW.max_hp, HOLLOWBACK.max_hp)
        self.assertTrue(BARKJAW.tutorial)
        self.assertFalse(HOLLOWBACK.tutorial)
        self.assertIn("pale", HOLLOWBACK.description.lower())
        self.assertIn("fung", HOLLOWBACK.description.lower())

    def test_listening_turns_silence_and_tracks_into_real_safety_information(self):
        tempdir, database, session = self._session()
        try:
            database.advance_quest(session.character.id, FOREST_ELF_FIRST_WALK.key, "listen_pool")
            database.set_character_room(session.character.id, FOREST_ELF_LISTENING_POOL_KEY)
            session.refresh()

            self.assertTrue(start_reading_forest_if_ready(session))
            self.assertEqual(database.item_quantity(session.character.id, RIVER_MOSS_BUNDLE_KEY), 1)

            handled = asyncio.run(_handle_listening_pool(session, "listen"))
            self.assertTrue(handled)
            flags = database.list_flags(session.character.id)
            self.assertIn(PATH_WARNING_HEARD_FLAG, flags)
            self.assertIn(PATH_SIGN_READ_FLAG, flags)
            self.assertEqual(
                database.get_quest(session.character.id, FOREST_ELF_FIRST_WALK.key)["current_step"],
                "reach_outer_grove",
            )
            self.assertIn("birds north of you go quiet together", session.text().lower())
            self.assertIn("deer tracks", session.text().lower())
        finally:
            tempdir.cleanup()

    def test_stag_choice_persists_and_lookout_asks_what_player_actually_heard(self):
        tempdir, database, session = self._session()
        try:
            database.advance_quest(session.character.id, FOREST_ELF_FIRST_WALK.key, "listen_pool")
            database.set_character_room(session.character.id, FOREST_ELF_LISTENING_POOL_KEY)
            session.refresh()
            start_reading_forest_if_ready(session)
            asyncio.run(_handle_listening_pool(session, "listen"))

            database.set_character_room(session.character.id, FOREST_ELF_OUTER_GROVE_KEY)
            session.refresh()
            database.grant_flag(session.character.id, BARKJAW_AVOIDED_FLAG)
            _advance_to_stag(session)

            self.assertTrue(asyncio.run(_handle_stag(session, "examine stag")))
            self.assertTrue(asyncio.run(_handle_stag(session, "free stag")))
            self.assertIn(STAG_RESCUED_FLAG, database.list_flags(session.character.id))
            self.assertEqual(
                database.get_quest(session.character.id, WHAT_DID_YOU_HEAR.key)["current_step"],
                "report_lookout",
            )

            database.set_character_room(session.character.id, WHITEWOOD_LOOKOUT_KEY)
            session.refresh()
            self.assertTrue(asyncio.run(_handle_lookout(session, "talk serael")))
            self.assertIn("what did you hear", session.text().lower())
            self.assertEqual(database.item_quantity(session.character.id, RIVER_MOSS_BUNDLE_KEY), 0)

            self.assertTrue(asyncio.run(_handle_lookout(session, "report birds")))
            quest = database.get_quest(session.character.id, WHAT_DID_YOU_HEAR.key)
            assert quest is not None
            self.assertEqual(quest["status"], "completed")
            self.assertIn(WHAT_DID_YOU_HEAR_COMPLETE_FLAG, database.list_flags(session.character.id))
            self.assertIn("silence is sometimes an action", session.text().lower())
        finally:
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
