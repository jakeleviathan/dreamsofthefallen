from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import server
from mud.database import Database


class _Writer:
    def __init__(self) -> None:
        self.data = bytearray()

    def get_extra_info(self, name: str):
        if name == "peername":
            return ("127.0.0.1", 40000)
        return None

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        return None


class LiveTelnetSessionConstructionTests(unittest.TestCase):
    def test_production_player_session_constructs_with_slotted_telnet_connection(self) -> None:
        """Regression for the live-only crash seen when Mudlet connected.

        The final accessibility policy used to replace ``telnet.send_gmcp`` on
        an individual TelnetConnection. TelnetConnection is a slotted dataclass,
        so real PlayerSession construction raised AttributeError before the
        welcome banner could be sent.
        """

        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "mud.db")
            reader = asyncio.StreamReader()
            writer = _Writer()

            session = server.PlayerSession(reader, writer, database)

            self.assertIsNotNone(session.telnet.gmcp_send_allowed)
            self.assertTrue(session._dotf_preference_gmcp_policy)

            async def exercise_policy() -> None:
                session.telnet.gmcp_enabled = True

                sent = await session.telnet.send_gmcp("Char.Status", {"name": "Probe"})
                self.assertTrue(sent)
                self.assertGreater(len(writer.data), 0)

                session._mudlet_enhancements_enabled = False
                before = len(writer.data)
                sent = await session.telnet.send_gmcp("Char.Status", {"name": "Blocked"})
                self.assertFalse(sent)
                self.assertEqual(len(writer.data), before)

            asyncio.run(exercise_policy())


if __name__ == "__main__":
    unittest.main()
