from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.player_preferences import (
    _ensure_schema,
    install_player_preferences_runtime,
    load_preferences,
    style_text,
)


class FakeState:
    DISCONNECTED = "disconnected"


class FakeTelnet:
    def __init__(self, gmcp_enabled=False):
        self.gmcp_enabled = gmcp_enabled


class BaseSession:
    def __init__(self, database, account, character, commands=None, gmcp=False):
        self.database = database
        self.account = account
        self.character = character
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.state = FakeState()
        self.telnet = FakeTelnet(gmcp)
        self.mudlet_gui_offer_sent = False
        self.offer_calls = 0
        self.state_calls = 0

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def enter_character(self):
        await self.send("ENTERED\r\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        if command is not None:
            await self.send(f"BASE: {command}\r\n")

    async def offer_official_mudlet_hud(self):
        self.offer_calls += 1
        return True

    async def send_client_state(self):
        self.state_calls += 1


def session_type():
    class Session(BaseSession):
        pass

    install_player_preferences_runtime(Session)
    return Session


class PlayerPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        _ensure_schema(self.db)
        self.account = self.db.create_account("reader", "hash")
        self.character = self.db.create_character(self.account.id, "Mira", "human", "wizard")

    def tearDown(self):
        self.tempdir.cleanup()

    def _session(self, commands=None, gmcp=False):
        Session = session_type()
        return Session(self.db, self.account, self.character, commands=commands, gmcp=gmcp)

    def test_recommended_defaults_are_loaded_and_settings_are_plain_language(self):
        session = self._session(["settings"])
        asyncio.run(session.enter_character())
        prefs = load_preferences(session)
        self.assertEqual(prefs.prompt_mode, "compact")
        self.assertEqual(prefs.hint_level, "gentle")
        self.assertTrue(prefs.mudlet_enhancements)
        self.assertFalse(prefs.screen_reader)
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("Settings & Accessibility", output)
        self.assertIn("SET HINTS OFF|GENTLE|FULL", output)
        self.assertIn("SET SCREENREADER ON|OFF", output)

    def test_preferences_persist_across_sessions_for_the_account(self):
        first = self._session([
            "set prompt full",
            "set hints off",
            "set color on",
            "set contrast high",
        ])
        asyncio.run(first.enter_character())
        for _ in range(4):
            asyncio.run(first.playing_prompt())

        second = self._session()
        asyncio.run(second.enter_character())
        prefs = load_preferences(second)
        self.assertEqual(prefs.prompt_mode, "full")
        self.assertEqual(prefs.hint_level, "off")
        self.assertEqual(prefs.color_mode, "on")
        self.assertEqual(prefs.contrast_mode, "high")
        self.assertEqual(second._room_ux_prompt_mode, "full")

    def test_screen_reader_mode_suppresses_ansi_mudlet_state_and_live_status_prompt(self):
        session = self._session(["set screenreader on"], gmcp=True)
        asyncio.run(session.enter_character())
        asyncio.run(session.playing_prompt())
        self.assertTrue(session._screen_reader_enabled)
        self.assertEqual(session._room_ux_prompt_mode, "quiet")
        self.assertEqual(style_text(session, "Room Name", "heading"), "Room Name")
        self.assertFalse(asyncio.run(session.offer_official_mudlet_hud()))
        asyncio.run(session.send_client_state())
        self.assertEqual(session.offer_calls, 0)
        self.assertEqual(session.state_calls, 0)

    def test_mudlet_can_be_disabled_without_enabling_screen_reader_mode(self):
        session = self._session(["set mudlet off"], gmcp=True)
        asyncio.run(session.enter_character())
        asyncio.run(session.playing_prompt())
        self.assertFalse(session._mudlet_enhancements_enabled)
        self.assertFalse(session._screen_reader_enabled)
        self.assertFalse(asyncio.run(session.offer_official_mudlet_hud()))

    def test_high_contrast_color_has_real_ansi_presentation_when_opted_in(self):
        session = self._session(["set color on", "set contrast high"])
        asyncio.run(session.enter_character())
        asyncio.run(session.playing_prompt())
        asyncio.run(session.playing_prompt())
        styled = style_text(session, "Astralis", "heading")
        self.assertIn("\x1b[1;97m", styled)
        self.assertTrue(styled.endswith("\x1b[0m"))


if __name__ == "__main__":
    unittest.main()
