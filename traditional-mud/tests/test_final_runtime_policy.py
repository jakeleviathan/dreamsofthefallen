from __future__ import annotations

import unittest
from types import SimpleNamespace

from mud.final_runtime_policy import _presentation_text, install_accessibility_policy_runtime


class _Telnet:
    def __init__(self) -> None:
        self.gmcp_enabled = True
        self.sent: list[tuple[str, object]] = []

    async def send_gmcp(self, package: str, payload=None) -> bool:
        self.sent.append((package, payload))
        return True


class _Session:
    def __init__(self, *args, **kwargs) -> None:
        self.telnet = _Telnet()
        self.account = None
        self.character = None
        self.sent: list[str] = []
        self._player_color_mode = "on"
        self._player_contrast_mode = "standard"
        self._mudlet_enhancements_enabled = True
        self._screen_reader_enabled = False

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def enter_character(self) -> None:
        return None


class FinalRuntimePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_color_off_strips_ansi_from_any_outer_runtime(self):
        install_accessibility_policy_runtime(_Session)
        session = _Session()
        session._player_color_mode = "off"
        await session.send("\x1b[1;93mGold title\x1b[0m\r\n")
        self.assertEqual(session.sent, ["Gold title\r\n"])

    async def test_screen_reader_suppresses_direct_gmcp_and_ansi(self):
        install_accessibility_policy_runtime(_Session)
        session = _Session()
        session._screen_reader_enabled = True
        await session.send("\x1b[96mAltered perception\x1b[0m")
        sent = await session.telnet.send_gmcp("Dreams.Map", {"rooms": []})
        self.assertFalse(sent)
        self.assertEqual(session.sent, ["Altered perception"])
        self.assertEqual(session.telnet.sent, [])

    async def test_mudlet_off_blocks_direct_outer_runtime_packets(self):
        install_accessibility_policy_runtime(_Session)
        session = _Session()
        session._mudlet_enhancements_enabled = False
        sent = await session.telnet.send_gmcp("Dreams.Movement", {"movement": 20})
        self.assertFalse(sent)
        self.assertEqual(session.telnet.sent, [])

    async def test_reenable_mudlet_takes_effect_without_rewrapping(self):
        install_accessibility_policy_runtime(_Session)
        session = _Session()
        session._mudlet_enhancements_enabled = False
        self.assertFalse(await session.telnet.send_gmcp("Dreams.Map", {}))
        session._mudlet_enhancements_enabled = True
        self.assertTrue(await session.telnet.send_gmcp("Dreams.Map", {}))
        self.assertEqual(session.telnet.sent, [("Dreams.Map", {})])

    def test_high_contrast_remaps_raw_semantic_ansi(self):
        session = SimpleNamespace(
            _player_color_mode="on",
            _player_contrast_mode="high",
            _screen_reader_enabled=False,
            telnet=SimpleNamespace(gmcp_enabled=True),
        )
        output = _presentation_text(session, "\x1b[90mRegion\x1b[0m")
        self.assertIn("\x1b[1;97mRegion", output)


if __name__ == "__main__":
    unittest.main()
