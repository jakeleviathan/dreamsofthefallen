from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from mud.welcome_banner import (
    BANNER_WIDTH,
    CELESTIAL_GATE,
    DREAMLIGHT,
    DREAMS_WORDMARK,
    FALLEN_WORDMARK,
    FALLING_SIGIL,
    GOLD,
    SHADOW,
    STARLIGHT,
    TWILIGHT,
    WELCOME_BANNER,
    plain_welcome_banner,
    visible_banner_widths,
)


ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class WelcomeBannerDesignTests(unittest.TestCase):
    def test_celestial_banner_fits_normal_terminal_width(self):
        widths = visible_banner_widths()
        self.assertTrue(widths)
        self.assertLessEqual(max(widths), BANNER_WIDTH)
        self.assertLessEqual(BANNER_WIDTH, 78)

    def test_banner_has_title_gate_falling_sigil_and_world_identity(self):
        plain = plain_welcome_banner()
        self.assertEqual(len(DREAMS_WORDMARK), 5)
        self.assertEqual(len(FALLEN_WORDMARK), 5)
        for line in (*DREAMS_WORDMARK, *FALLEN_WORDMARK):
            self.assertIn(line.strip(), plain)

        self.assertIn("O F   T H E", plain)
        self.assertIn("A S T R A L I S", plain)
        self.assertIn("The road remembers every soul that crossed it.", plain)
        self.assertIn("[ LOGIN / CREATE ACCOUNT ]", plain)
        self.assertIn("Enter your account name below to awaken.", plain)
        self.assertIn(CELESTIAL_GATE[5], plain)
        self.assertIn(FALLING_SIGIL[5], plain)

        # The visible splash remains genuine old-client-safe terminal art.
        plain.encode("ascii")

    def test_falling_sigil_stays_on_one_center_axis(self):
        lines = plain_welcome_banner().replace("\r", "").split("\n")
        center = BANNER_WIDTH // 2
        for row in ("|", "*", ".---+---.", "\\|/", "V"):
            candidates = [line for line in lines if line.strip() == row]
            self.assertTrue(candidates, row)
            # The lower sigil is after the title, so the last matching row is its row.
            line = candidates[-1]
            self.assertEqual(line.index(row[len(row) // 2]), center, row)

    def test_palette_is_restrained_celestial_ansi(self):
        self.assertIn(STARLIGHT, WELCOME_BANNER)
        self.assertIn(DREAMLIGHT, WELCOME_BANNER)
        self.assertIn(TWILIGHT, WELCOME_BANNER)
        self.assertIn(GOLD, WELCOME_BANNER)
        self.assertIn(SHADOW, WELCOME_BANNER)
        self.assertEqual(ANSI.sub("", WELCOME_BANNER), plain_welcome_banner())


class ProductionWelcomeBannerTests(unittest.TestCase):
    def test_production_session_uses_new_banner_and_accessibility_can_strip_ansi(self):
        code = r"""
import re
import server
import mud.session as session_module
from mud.final_runtime_policy import _presentation_text

assert "The road remembers every soul that crossed it." in session_module.WELCOME_BANNER
assert "A S T R A L I S" in session_module.WELCOME_BANNER
assert "[ LOGIN / CREATE ACCOUNT ]" in session_module.WELCOME_BANNER
assert ".---+---." in session_module.WELCOME_BANNER

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
assert "Enter your account name below to awaken." in plain
print("CELESTIAL_BANNER_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CELESTIAL_BANNER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
