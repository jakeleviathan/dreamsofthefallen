from __future__ import annotations

import asyncio
import unittest

from mud.client_gui import OFFICIAL_MUDLET_HUD_URL, OFFICIAL_MUDLET_HUD_VERSION
from mud.telnet import DO, GMCP, IAC, SB, SE, TelnetConnection


class MemoryWriter:
    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        return None


class TelnetGuiNegotiationTests(unittest.IsolatedAsyncioTestCase):
    async def test_do_gmcp_immediately_offers_official_hud_once(self) -> None:
        reader = asyncio.StreamReader()
        writer = MemoryWriter()
        connection = TelnetConnection(reader, writer)  # type: ignore[arg-type]

        # Mudlet accepts GMCP. Send the acknowledgement twice to verify that a
        # reconnect/duplicate negotiation cannot trigger duplicate GUI offers.
        reader.feed_data(
            bytes((IAC, DO, GMCP, IAC, DO, GMCP))
            + b"Jake\r\n"
        )
        reader.feed_eof()

        line = await connection.read_line()

        self.assertEqual(line, "Jake")
        self.assertTrue(connection.gmcp_enabled)
        self.assertTrue(connection.client_gui_offer_sent)

        expected_body = (
            'Client.GUI '
            f'{{"version":"{OFFICIAL_MUDLET_HUD_VERSION}",'
            f'"url":"{OFFICIAL_MUDLET_HUD_URL}"}}'
        ).encode("utf-8")
        expected_frame = bytes((IAC, SB, GMCP)) + expected_body + bytes((IAC, SE))

        output = bytes(writer.data)
        self.assertIn(expected_frame, output)
        self.assertEqual(output.count(b"Client.GUI "), 1)


if __name__ == "__main__":
    unittest.main()
