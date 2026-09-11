from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.new_player_guidance import _ACTIVE_SESSIONS as GUIDANCE_SESSIONS
from mud.new_player_guidance import install_new_player_guidance_runtime
from mud.social_experience import (
    _ACTIVE_SESSIONS,
    _ensure_schema,
    install_social_experience_runtime,
)


class FakeState:
    DISCONNECTED = "disconnected"


class BaseSession:
    def __init__(self, database, account, character, commands=None):
        self.database = database
        self.account = account
        self.character = character
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def enter_character(self):
        return None

    async def close(self):
        return None

    async def playing_prompt(self):
        command = await self.prompt("> ")
        if command is not None:
            await self.send(f"BASE: {command}\r\n")


def social_session_type(*, with_guidance=False):
    class Session(BaseSession):
        pass

    if with_guidance:
        install_new_player_guidance_runtime(Session)
    install_social_experience_runtime(Session)
    return Session


class SocialExperienceTests(unittest.TestCase):
    def setUp(self):
        _ACTIVE_SESSIONS.clear()
        GUIDANCE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        _ensure_schema(self.db)
        self.alice_account = self.db.create_account("aliceaccount", "hash")
        self.bob_account = self.db.create_account("bobaccount", "hash")
        self.cara_account = self.db.create_account("caraaccount", "hash")
        self.alice_character = self.db.create_character(self.alice_account.id, "Alice", "human", "wizard")
        self.bob_character = self.db.create_character(self.bob_account.id, "Bob", "dwarf", "brute")
        self.cara_character = self.db.create_character(self.cara_account.id, "Cara", "forest_elf", "druid")

    def tearDown(self):
        _ACTIVE_SESSIONS.clear()
        GUIDANCE_SESSIONS.clear()
        self.tempdir.cleanup()

    def _pair(self, alice_commands=None, bob_commands=None, *, guidance=False):
        Session = social_session_type(with_guidance=guidance)
        alice = Session(self.db, self.alice_account, self.alice_character, alice_commands)
        bob = Session(self.db, self.bob_account, self.bob_character, bob_commands)
        asyncio.run(alice.enter_character())
        asyncio.run(bob.enter_character())
        alice.outputs.clear()
        bob.outputs.clear()
        return alice, bob

    def test_channels_are_clear_broadcasts_and_can_be_muted(self):
        alice, bob = self._pair(["chat Hello Astralis"], ["channel chat off"])
        asyncio.run(alice.playing_prompt())
        self.assertIn("[Chat] Alice: Hello Astralis", "".join(alice.outputs))
        self.assertIn("[Chat] Alice: Hello Astralis", "".join(bob.outputs))

        bob.outputs.clear()
        asyncio.run(bob.playing_prompt())
        alice.commands.append("chat Second message")
        asyncio.run(alice.playing_prompt())
        self.assertNotIn("Second message", "".join(bob.outputs))
        self.assertIn("CHAT channel muted", "".join(bob.outputs))

    def test_private_tell_and_reply_track_the_recent_sender(self):
        alice, bob = self._pair(["tell Bob Are you there?"], ["reply Yep."])
        asyncio.run(alice.playing_prompt())
        self.assertIn("[Tell from Alice] Are you there?", "".join(bob.outputs))
        asyncio.run(bob.playing_prompt())
        self.assertIn("[Tell from Bob] Yep.", "".join(alice.outputs))
        self.assertIn("[Tell to Alice] Yep.", "".join(bob.outputs))

    def test_friend_list_persists_and_reports_online_without_exposing_location(self):
        alice, bob = self._pair(["friend Bob", "friends"])
        asyncio.run(alice.playing_prompt())
        asyncio.run(alice.playing_prompt())
        output = "".join(alice.outputs)
        self.assertIn("Bob added to your friends list", output)
        self.assertIn("Bob - online", output)
        self.assertNotIn("human_demon_gate", output)

        asyncio.run(bob.close())
        alice.outputs.clear()
        alice.commands.append("friends")
        asyncio.run(alice.playing_prompt())
        self.assertIn("Bob - offline", "".join(alice.outputs))

    def test_ignore_blocks_private_and_world_messages(self):
        alice, bob = self._pair(["tell Bob Secret", "chat Hello"], ["ignore Alice"])
        asyncio.run(bob.playing_prompt())
        bob.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn("not accepting messages", "".join(alice.outputs))
        self.assertNotIn("Secret", "".join(bob.outputs))
        asyncio.run(alice.playing_prompt())
        self.assertNotIn("[Chat] Alice: Hello", "".join(bob.outputs))

    def test_ignore_also_suppresses_local_say(self):
        alice, bob = self._pair(["say Hello in the room"], ["ignore Alice"], guidance=True)
        asyncio.run(bob.playing_prompt())
        bob.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn('You say, "Hello in the room"', "".join(alice.outputs))
        self.assertNotIn("Hello in the room", "".join(bob.outputs))

    def test_who_lists_connected_characters_without_staff_location_data(self):
        alice, bob = self._pair(["who"])
        asyncio.run(alice.playing_prompt())
        output = "".join(alice.outputs)
        self.assertIn("Who Is In Astralis (2)", output)
        self.assertIn("Alice - Level 1", output)
        self.assertIn("Bob - Level 1", output)
        self.assertNotIn("current_room", output)
        self.assertNotIn("human_demon_gate", output)


if __name__ == "__main__":
    unittest.main()
