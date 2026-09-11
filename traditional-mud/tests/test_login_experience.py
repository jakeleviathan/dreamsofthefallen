from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.login_experience import GOTHIC_WELCOME_BANNER, install_login_experience
from mud.session import SessionState
from mud.world import HUMAN_START_ROOM_KEY, ROOMS_BY_KEY


class FakeSession:
    def __init__(self, database: Database, prompts: list[str]):
        self.database = database
        self.prompts = list(prompts)
        self.outputs: list[str] = []
        self.state = SessionState.ACCOUNT_NAME
        self.account = None
        self.character = None
        self.entered = False
        self.creation_called = False

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, text: str):
        self.outputs.append(text)
        if not self.prompts:
            return None
        return self.prompts.pop(0)

    async def enter_character(self):
        self.entered = True
        self.state = SessionState.PLAYING

    async def character_creation_flow(self):
        self.creation_called = True


install_login_experience(FakeSession)


class LoginExperienceTests(unittest.TestCase):
    def _db(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "login.db")
        self.addCleanup(temp.cleanup)
        return database

    def test_gothic_banner_is_ascii_telnet_safe_and_has_two_primary_entries(self):
        self.assertIn("DREAMS OF THE FALLEN", GOTHIC_WELCOME_BANNER)
        self.assertIn("ASTRALIS", GOTHIC_WELCOME_BANNER)
        self.assertIn("LOGIN     CREATE ACCOUNT", GOTHIC_WELCOME_BANNER)
        self.assertIn("Beneath Astralis, something dreams.", GOTHIC_WELCOME_BANNER)
        GOTHIC_WELCOME_BANNER.encode("ascii")

    def test_create_account_requires_matching_confirmation_then_opens_roster(self):
        database = self._db()
        session = FakeSession(
            database,
            ["create account", "BlackRose", "password1", "notthesame", "password1", "password1"],
        )

        asyncio.run(session.account_name_screen())

        account = database.get_account_by_name("BlackRose")
        self.assertIsNotNone(account)
        self.assertIsNotNone(session.account)
        self.assertEqual(session.state, SessionState.CHARACTER_MENU)
        output = "".join(session.outputs)
        self.assertIn("Confirm password", output)
        self.assertIn("passwords did not match", output.lower())
        self.assertIn("character roster is ready", output.lower())

    def test_login_and_create_are_separate_explicit_paths(self):
        database = self._db()
        created = database.create_account("Existing", __import__("mud.security", fromlist=["hash_password"]).hash_password("password1"))
        session = FakeSession(database, ["login", "Existing", "password1"])

        asyncio.run(session.account_name_screen())

        self.assertEqual(session.account.id, created.id)
        self.assertEqual(session.state, SessionState.CHARACTER_MENU)
        self.assertIn("--- Login ---", "".join(session.outputs))

    def test_roster_always_shows_eight_slots_last_played_and_location(self):
        database = self._db()
        account = database.create_account("Roster", "hash")
        first = database.create_character(account.id, "Morrow", "human", "wizard")
        database.create_character(account.id, "Rattle", "undead", "brute")
        database.set_character_room(first.id, HUMAN_START_ROOM_KEY)
        with database.connect() as db:
            db.execute(
                "UPDATE characters SET last_played_at = '2026-09-09 23:45:00' WHERE id = ?",
                (first.id,),
            )

        session = FakeSession(database, ["help"])
        session.account = account
        session.state = SessionState.CHARACTER_MENU
        asyncio.run(session.character_menu())

        output = "".join(session.outputs)
        self.assertIn("CHARACTER ROSTER", output)
        self.assertIn("Morrow", output)
        self.assertIn("Human", output)
        self.assertIn("Wizard", output)
        self.assertIn("2026-09-09 23:45 UTC", output)
        self.assertIn("Location:", output)
        self.assertIn(ROOMS_BY_KEY[HUMAN_START_ROOM_KEY].name, output)
        self.assertEqual(output.count("[ Empty ]"), 6)
        self.assertIn("ENTER <slot or name>", output)
        self.assertIn("PLAY LAST", output)
        self.assertIn("CREATE", output)

    def test_enter_accepts_slot_and_records_last_played(self):
        database = self._db()
        account = database.create_account("Enterer", "hash")
        character = database.create_character(account.id, "Vesper", "human", "wizard")
        session = FakeSession(database, ["enter 1"])
        session.account = account
        session.state = SessionState.CHARACTER_MENU

        asyncio.run(session.character_menu())

        self.assertTrue(session.entered)
        self.assertEqual(session.character.id, character.id)
        with database.connect() as db:
            value = db.execute(
                "SELECT last_played_at FROM characters WHERE id = ?",
                (character.id,),
            ).fetchone()["last_played_at"]
        self.assertIsNotNone(value)

    def test_play_last_enters_most_recent_character(self):
        database = self._db()
        account = database.create_account("QuickReturn", "hash")
        older = database.create_character(account.id, "Older", "human", "wizard")
        newer = database.create_character(account.id, "Newer", "moon_elf", "druid")
        with database.connect() as db:
            db.execute(
                "UPDATE characters SET last_played_at = '2026-09-08 12:00:00' WHERE id = ?",
                (older.id,),
            )
            db.execute(
                "UPDATE characters SET last_played_at = '2026-09-10 12:00:00' WHERE id = ?",
                (newer.id,),
            )

        session = FakeSession(database, ["play last"])
        session.account = account
        session.state = SessionState.CHARACTER_MENU
        asyncio.run(session.character_menu())

        self.assertTrue(session.entered)
        self.assertEqual(session.character.id, newer.id)

    def test_play_last_without_history_is_explained(self):
        database = self._db()
        account = database.create_account("NoHistory", "hash")
        database.create_character(account.id, "Fresh", "human", "wizard")
        session = FakeSession(database, ["play last"])
        session.account = account
        session.state = SessionState.CHARACTER_MENU

        asyncio.run(session.character_menu())

        self.assertFalse(session.entered)
        self.assertIn("no previously played character", "".join(session.outputs).lower())

    def test_create_command_uses_existing_character_creation_flow(self):
        database = self._db()
        account = database.create_account("Maker", "hash")
        session = FakeSession(database, ["create"])
        session.account = account
        session.state = SessionState.CHARACTER_MENU

        asyncio.run(session.character_menu())

        self.assertTrue(session.creation_called)


if __name__ == "__main__":
    unittest.main()
