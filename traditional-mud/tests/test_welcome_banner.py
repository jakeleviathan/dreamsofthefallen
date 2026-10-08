from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from mud.welcome_banner import (
    BANNER_WIDTH,
    DREAMS_WORDMARK,
    FALLEN_WORDMARK,
    WELCOME_BANNER,
    plain_welcome_banner,
    visible_banner_widths,
)

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class WelcomeBannerDesignTests(unittest.TestCase):
    def test_every_line_fits_traditional_telnet(self):
        self.assertEqual(BANNER_WIDTH, 78)
        self.assertLessEqual(max(visible_banner_widths()), 78)
        self.assertTrue(plain_welcome_banner().isascii())
        self.assertIn("\r\n", WELCOME_BANNER)

    def test_title_and_all_player_actions_survive(self):
        plain = plain_welcome_banner()
        for rows in (DREAMS_WORDMARK, FALLEN_WORDMARK):
            for row in rows:
                self.assertIn(row.strip(), plain)
        for phrase in (
            "O F   T H E", "A S T R A L I S",
            "[ LOGIN / CREATE ACCOUNT ]",
            "Root: https://rootapp.gg/ADG6eZjrgQqXVAqT0c7ceA",
            "Enter your account name below to awaken.",
            "The road remembers every soul that crossed it.",
            "RUINS  +  MYSTERY  +  MAGIC",
        ):
            self.assertIn(phrase, plain)

    def test_rich_colored_ansi_and_illustration(self):
        self.assertEqual(ANSI.sub("", WELCOME_BANNER), plain_welcome_banner())
        self.assertGreater(len(set(ANSI.findall(WELCOME_BANNER))), 8)
        self.assertIn("[]", plain_welcome_banner())
        self.assertIn("~~~~", plain_welcome_banner())
        self.assertGreater(len(WELCOME_BANNER.splitlines()), 35)


class ProductionWelcomeBannerTests(unittest.TestCase):
    def test_server_session_uses_art_and_accessibility_can_strip_ansi(self):
        code = r"""
import server
import mud.session as session_module
from mud.final_runtime_policy import _presentation_text
assert "RUINS  +  MYSTERY  +  MAGIC" in session_module.WELCOME_BANNER
assert "[ LOGIN / CREATE ACCOUNT ]" in session_module.WELCOME_BANNER

class Telnet:
    gmcp_enabled = False

class Session:
    account = None
    telnet = Telnet()
    _player_color_mode = "auto"
    _screen_reader_enabled = False
    _player_contrast_mode = "standard"

plain = _presentation_text(Session(), session_module.WELCOME_BANNER)
assert "\x1b[" not in plain
assert "A S T R A L I S" in plain
assert "Root: https://rootapp.gg/ADG6eZjrgQqXVAqT0c7ceA" in plain
print("ANSI_BANNER_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True, text=True, timeout=45, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ANSI_BANNER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
