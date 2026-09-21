from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.player_channels import (
    MAX_OWNED_CHANNELS,
    _ACTIVE_SESSIONS,
    _ensure_schema,
    install_player_channels_runtime,
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


def channel_session_type():
    class Session(BaseSession):
        pass

    install_player_channels_runtime(Session)
    return Session


class PlayerChannelTests(unittest.TestCase):
    def setUp(self):
        _ACTIVE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        _ensure_schema(self.db)
        self.alice_account = self.db.create_account("aliceaccount", "hash")
        self.bob_account = self.db.create_account("bobaccount", "hash")
        self.cara_account = self.db.create_account("caraaccount", "hash")
        self.alice_character = self.db.create_character(
            self.alice_account.id, "Alice", "human", "wizard"
        )
        self.bob_character = self.db.create_character(
            self.bob_account.id, "Bob", "dwarf", "brute"
        )
        self.cara_character = self.db.create_character(
            self.cara_account.id, "Cara", "forest_elf", "druid"
        )

    def tearDown(self):
        _ACTIVE_SESSIONS.clear()
        self.tempdir.cleanup()

    def _sessions(
        self, alice_commands=None, bob_commands=None, cara_commands=None
    ):
        Session = channel_session_type()
        alice = Session(
            self.db, self.alice_account, self.alice_character, alice_commands
        )
        bob = Session(
            self.db, self.bob_account, self.bob_character, bob_commands
        )
        cara = Session(
            self.db, self.cara_account, self.cara_character, cara_commands
        )
        asyncio.run(alice.enter_character())
        asyncio.run(bob.enter_character())
        asyncio.run(cara.enter_character())
        for session in (alice, bob, cara):
            session.outputs.clear()
        return alice, bob, cara

    def test_public_channel_can_be_created_discovered_joined_and_used(self):
        alice, bob, _ = self._sessions(
            [
                "channel create Raiders",
                "channel Raiders Meet at Waymeet.",
            ],
            ["channels", "channel join Raiders"],
        )
        asyncio.run(alice.playing_prompt())
        self.assertIn(
            "Channel Raiders created as a public channel",
            "".join(alice.outputs),
        )

        asyncio.run(bob.playing_prompt())
        listing = "".join(bob.outputs)
        self.assertIn("Raiders - public", listing)
        self.assertIn("owner Alice", listing)

        bob.outputs.clear()
        asyncio.run(bob.playing_prompt())
        self.assertIn("Connected to Raiders", "".join(bob.outputs))

        bob.outputs.clear()
        alice.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn(
            "Raiders | Alice: Meet at Waymeet.", "".join(alice.outputs)
        )
        self.assertIn(
            "Raiders | Alice: Meet at Waymeet.", "".join(bob.outputs)
        )

    def test_invite_only_channels_remain_discoverable_without_private_details(self):
        alice, _, cara = self._sessions(
            [
                "channel create Circle",
                "channel private Circle on",
                "channel invite Circle Cara",
            ],
            [],
            [
                "channels",
                "channel join Circle",
                "channel join Circle",
            ],
        )
        asyncio.run(alice.playing_prompt())
        asyncio.run(alice.playing_prompt())

        asyncio.run(cara.playing_prompt())
        listing = "".join(cara.outputs)
        self.assertIn("Circle - invite-only", listing)
        self.assertNotIn("owner Alice", listing)

        cara.outputs.clear()
        asyncio.run(cara.playing_prompt())
        self.assertIn(
            "owner invitation is required", "".join(cara.outputs)
        )

        cara.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn("invited you to Circle", "".join(cara.outputs))
        asyncio.run(cara.playing_prompt())
        self.assertIn("Connected to Circle", "".join(cara.outputs))

    def test_owner_can_mute_unmute_kick_and_reinvite(self):
        alice, bob, _ = self._sessions(
            [
                "channel create Raiders",
                "channel mute Raiders Bob",
                "channel unmute Raiders Bob",
                "channel kick Raiders Bob",
                "channel invite Raiders Bob",
            ],
            [
                "channel join Raiders",
                "channel Raiders Can anyone hear me?",
                "channel Raiders I am back.",
                "channel join Raiders",
                "channel join Raiders",
            ],
        )
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())

        asyncio.run(alice.playing_prompt())
        bob.outputs.clear()
        asyncio.run(bob.playing_prompt())
        self.assertIn(
            "owner has muted your speech", "".join(bob.outputs)
        )

        asyncio.run(alice.playing_prompt())
        bob.outputs.clear()
        alice.outputs.clear()
        asyncio.run(bob.playing_prompt())
        self.assertIn(
            "Raiders | Bob: I am back.", "".join(alice.outputs)
        )

        asyncio.run(alice.playing_prompt())
        self.assertIn("removed from Raiders", "".join(bob.outputs))
        bob.outputs.clear()
        asyncio.run(bob.playing_prompt())
        self.assertIn("must invite you back", "".join(bob.outputs))

        asyncio.run(alice.playing_prompt())
        bob.outputs.clear()
        asyncio.run(bob.playing_prompt())
        self.assertIn("Connected to Raiders", "".join(bob.outputs))

    def test_owner_can_rename_and_close_channel(self):
        alice, bob, _ = self._sessions(
            [
                "channel create Raiders",
                "channel rename Raiders Roadcrew",
                "channel close Roadcrew",
            ],
            ["channel join Raiders"],
        )
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        bob.outputs.clear()

        asyncio.run(alice.playing_prompt())
        self.assertIn("renamed to Roadcrew", "".join(alice.outputs))
        self.assertIn("renamed to Roadcrew", "".join(bob.outputs))

        bob.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn(
            "Channel Roadcrew closed", "".join(alice.outputs)
        )
        self.assertIn(
            "Roadcrew has been closed", "".join(bob.outputs)
        )
        with self.db.connect() as db:
            row = db.execute(
                "SELECT 1 FROM player_chat_channels WHERE name = 'Roadcrew'"
            ).fetchone()
        self.assertIsNone(row)

    def test_channel_creation_is_free_but_owner_count_is_capped(self):
        commands = [
            f"channel create Chan{index}"
            for index in range(1, MAX_OWNED_CHANNELS + 2)
        ]
        alice, _, _ = self._sessions(commands)
        for _ in commands:
            asyncio.run(alice.playing_prompt())
        output = "".join(alice.outputs)
        self.assertEqual(
            output.count("created as a public channel"),
            MAX_OWNED_CHANNELS,
        )
        self.assertIn(
            f"already own {MAX_OWNED_CHANNELS}", output
        )


    def test_channels_list_is_compact_and_owner_controls_live_in_info(self):
        alice, bob, _ = self._sessions(
            ["channel create Raiders", "channel info Raiders"],
            ["channels"],
        )
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        listing = "".join(bob.outputs)
        self.assertIn("Name", listing)
        self.assertIn("Members", listing)
        self.assertIn("Access", listing)
        self.assertIn("Raiders", listing)
        self.assertNotIn("CHANNEL INVITE/KICK/MUTE", listing)

        alice.outputs.clear()
        asyncio.run(alice.playing_prompt())
        info = "".join(alice.outputs)
        self.assertIn("Owner controls:", info)
        self.assertIn("CHANNEL INVITE Raiders <player>", info)
        self.assertIn("CHANNEL RENAME Raiders <new-name>", info)

    def test_hash_shortcut_sends_to_player_channel(self):
        alice, bob, _ = self._sessions(
            ["channel create Raiders", "#Raiders Meet at Waymeet."],
            ["channel join Raiders"],
        )
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        alice.outputs.clear()
        bob.outputs.clear()
        asyncio.run(alice.playing_prompt())
        self.assertIn("Raiders | Alice: Meet at Waymeet.", "".join(alice.outputs))
        self.assertIn("Raiders | Alice: Meet at Waymeet.", "".join(bob.outputs))

    def test_builtin_channel_settings_are_delegated_to_existing_social_owner(self):
        alice, _, _ = self._sessions(["channel chat off"])
        asyncio.run(alice.playing_prompt())
        self.assertIn(
            "BASE: channel chat off", "".join(alice.outputs)
        )


if __name__ == "__main__":
    unittest.main()
