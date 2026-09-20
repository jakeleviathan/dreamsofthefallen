from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.combat import ENEMIES_BY_KEY, EnemyState
from mud.database import Database
from mud.discord_presence import (
    DiscordPresenceConfig,
    DiscordPresenceService,
    configured_discord_presence,
)
from mud.mechanics import CombatantState
from mud.session import PlayerSession, SessionState
from mud.telnet import GMCP, IAC, SB, SE, TelnetConnection
from mud.world import SPOREKIN_SURFACEWARD_ROOM_KEY


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return None

    def get_extra_info(self, name: str):
        return ("test", 0) if name == "peername" else None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None


class DiscordPresenceConfigurationTests(unittest.TestCase):
    def test_configuration_validates_application_and_invite_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DREAMS_DISCORD_APPLICATION_ID": "123456789012345678",
                "DREAMS_DISCORD_INVITE_URL": "https://discord.gg/dreams",
            },
            clear=False,
        ):
            config = configured_discord_presence()
        self.assertEqual(config.application_id, "123456789012345678")
        self.assertEqual(config.invite_url, "https://discord.gg/dreams")
        self.assertEqual(
            config.info_payload,
            {
                "applicationid": "123456789012345678",
                "inviteurl": "https://discord.gg/dreams",
            },
        )

        with patch.dict(
            os.environ,
            {
                "DREAMS_DISCORD_APPLICATION_ID": "not-a-snowflake",
                "DREAMS_DISCORD_INVITE_URL": "https://example.com/not-discord",
            },
            clear=False,
        ):
            invalid = configured_discord_presence()
        self.assertEqual(invalid.info_payload, {})


class DiscordPresenceServiceTests(unittest.TestCase):
    def _session(self, *, race: str = "human", character_class: str = "priest"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database(Path(tmp.name) / "mud.db")
        account = db.create_account("presence_test", "not-a-real-hash")
        character = db.create_character(account.id, "Lantern", race, character_class)
        character = replace(character, level=5, current_room="human_ashen_way")
        service = DiscordPresenceService(
            DiscordPresenceConfig(application_id="123456789012345678"),
            started_at=1_700_000_000,
        )
        session = SimpleNamespace(
            database=db,
            character=character,
            active_enemy=None,
            discord_presence=service,
        )
        return session

    def test_presence_uses_character_class_location_and_session_timer(self) -> None:
        session = self._session()
        status = session.discord_presence.build_status(session)
        self.assertIn("Level 5", status["details"])
        self.assertIn("Priest", status["details"])
        self.assertIn("Ashen Way", status["state"])
        self.assertEqual(status["smallimage"][0], "class-priest")
        self.assertEqual(status["starttime"], "1700000000")
        self.assertEqual(status["game"], "Dreams of the Fallen")

    def test_presence_prefers_live_production_world_scene_over_legacy_rooms(self) -> None:
        session = self._session()
        session.character = replace(session.character, current_room="dynamic_live_room")
        dynamic_scene = SimpleNamespace(
            key="dynamic_live_room",
            name="The Clockwork Causeway",
            region_key="veyra",
            tags=("city", "road"),
        )
        fake_world = SimpleNamespace(scene=lambda room_key: dynamic_scene if room_key == "dynamic_live_room" else None)
        with patch("mud.room_runtime.WORLD", fake_world):
            status = session.discord_presence.build_status(session)
        self.assertIn("The Clockwork Causeway", status["state"])

    def test_combat_takes_priority_over_exploration(self) -> None:
        session = self._session()
        session.active_enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
        status = session.discord_presence.build_status(session)
        self.assertIn("Battling Sewer Rat", status["state"])
        self.assertIn("Ashen Way", status["state"])

    def test_secret_room_and_enemy_information_are_not_leaked(self) -> None:
        session = self._session(race="sporekin", character_class="druid")
        session.character = replace(session.character, current_room=SPOREKIN_SURFACEWARD_ROOM_KEY)
        session.active_enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
        status = session.discord_presence.build_status(session)
        self.assertIn("unknown threat", status["state"].lower())
        self.assertIn("forgotten", status["state"].lower())
        self.assertNotIn("Veiled Grotto", status["state"])
        self.assertNotIn("Sewer Rat", status["state"])

    def test_puzzle_rooms_are_spoiler_safe_even_without_hidden_in_the_key(self) -> None:
        session = self._session(race="sporekin", character_class="druid")
        session.character = replace(session.character, current_room="sporekin_forgotten_grove")
        status = session.discord_presence.build_status(session)
        self.assertIn("somewhere forgotten", status["state"].lower())
        self.assertNotIn("Forgotten Grove", status["state"])

    def test_transient_crafting_presence_is_centralized(self) -> None:
        session = self._session()
        session.discord_presence.set_activity("crafting", "Cotton Gloves")
        status = session.discord_presence.build_status(session)
        self.assertEqual(status["state"], "Crafting Cotton Gloves")
        session.discord_presence.clear_activity()
        self.assertIn("Exploring", session.discord_presence.build_status(session)["state"])

    def test_unchanged_full_status_is_deduplicated(self) -> None:
        session = self._session()
        first = session.discord_presence.status_if_changed(session)
        second = session.discord_presence.status_if_changed(session)
        forced = session.discord_presence.status_if_changed(session, force=True)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(forced, first)


class DiscordGmcpProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_telnet_routes_external_discord_messages_case_insensitively(self) -> None:
        reader = asyncio.StreamReader()
        writer = _FakeWriter()
        connection = TelnetConnection(reader, writer)
        seen = []

        async def handler(package: str, payload: object) -> None:
            seen.append((package, payload))

        connection.set_gmcp_message_handler(handler)
        hello = b'External.Discord.Hello {"user":"someone#1234","private":true}'
        reader.feed_data(bytes((IAC, SB, GMCP)) + hello + bytes((IAC, SE)))
        reader.feed_data(b"look\r\n")

        command = await connection.read_line()
        self.assertEqual(command, "look")
        self.assertEqual(seen[0][0], "External.Discord.Hello")
        self.assertEqual(seen[0][1]["private"], True)

    async def test_session_replies_to_hello_without_retaining_discord_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.telnet.gmcp_enabled = True
            session.discord_presence = DiscordPresenceService(
                DiscordPresenceConfig(
                    application_id="123456789012345678",
                    invite_url="https://discord.gg/dreams",
                ),
                started_at=1_700_000_000,
            )

            await session._handle_client_gmcp(
                "External.Discord.Hello",
                {"user": "private-user#9999", "private": True},
            )

            raw = bytes(writer.buffer)
            self.assertIn(b"External.Discord.Info", raw)
            self.assertIn(b"External.Discord.Status", raw)
            self.assertIn(b'"applicationid":"123456789012345678"', raw)
            self.assertIn(b'"inviteurl":"https://discord.gg/dreams"', raw)
            self.assertNotIn(b"private-user", raw)
            self.assertFalse(hasattr(session.discord_presence, "discord_user"))

    async def test_get_returns_a_complete_status_and_state_updates_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("presence_wire", "not-a-real-hash")
            character = db.create_character(account.id, "Presence", "human", "wizard")
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = replace(character, level=3, current_room="human_ashen_way")
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character_id=character.id,
                race_key="human",
                current_hp=30,
                max_hp=30,
                current_mana=40,
                max_mana=40,
                auto_attack_interval=2.5,
                stats=character.stats,
            )
            session.telnet.gmcp_enabled = True
            session.discord_presence = DiscordPresenceService(
                DiscordPresenceConfig(application_id="123456789012345678"),
                started_at=1_700_000_000,
            )

            await session._handle_client_gmcp("External.Discord.Get", None)
            raw = bytes(writer.buffer)
            self.assertIn(b'"game":"Dreams of the Fallen"', raw)
            self.assertIn(b'"state":"Exploring Ashen Way', raw)
            count = raw.count(b"External.Discord.Status")

            await session.send_client_state()
            self.assertEqual(bytes(writer.buffer).count(b"External.Discord.Status"), count)

            session.active_enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
            await session.send_client_state()
            self.assertEqual(bytes(writer.buffer).count(b"External.Discord.Status"), count + 1)
            self.assertIn(b"Battling Sewer Rat", bytes(writer.buffer))


if __name__ == "__main__":
    unittest.main()
