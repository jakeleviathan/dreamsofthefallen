from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from mud.welcome_banner import (
    BANNER_WIDTH,
    DREAMLIGHT,
    GOLD,
    IRON,
    SHADOW,
    WELCOME_BANNER,
    plain_welcome_banner,
    visible_banner_widths,
)


ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class WelcomeBannerDesignTests(unittest.TestCase):
    def test_heavy_metal_banner_fits_normal_terminal_width(self):
        widths = visible_banner_widths()
        self.assertTrue(widths)
        self.assertLessEqual(max(widths), BANNER_WIDTH)
        self.assertLessEqual(BANNER_WIDTH, 90)

    def test_banner_has_two_large_wordmarks_and_world_identity(self):
        plain = plain_welcome_banner()
        # Six rows for DREAMS + six rows for FALLEN should produce a genuinely
        # oversized title treatment rather than another framed text plaque.
        self.assertGreaterEqual(plain.count("██"), 12)
        self.assertIn("O F   T H E", plain)
        self.assertIn("A S T R A L I S", plain)
        self.assertIn("Beneath Astralis, something dreams.", plain)
        self.assertIn("▼", plain)

    def test_banner_uses_restrained_semantic_palette(self):
        self.assertIn(IRON, WELCOME_BANNER)
        self.assertIn(SHADOW, WELCOME_BANNER)
        self.assertIn(GOLD, WELCOME_BANNER)
        self.assertIn(DREAMLIGHT, WELCOME_BANNER)
        self.assertEqual(ANSI.sub("", WELCOME_BANNER), plain_welcome_banner())


class ProductionWelcomeBannerTests(unittest.TestCase):
    def test_production_session_uses_new_banner_and_accessibility_can_strip_ansi(self):
        code = r"""
import re
import server
import mud.session as session_module
from mud.final_runtime_policy import _presentation_text
from mud.welcome_banner import WELCOME_BANNER

ANSI = re.compile(r"\x1b\[[0-9;]*m")
assert session_module.WELCOME_BANNER is WELCOME_BANNER
assert server.PlayerSession._final_runtime_policy_installed

class Telnet:
    gmcp_enabled = False

class Session:
    account = None
    telnet = Telnet()
    _player_color_mode = "auto"
    _screen_reader_enabled = False
    _player_contrast_mode = "standard"

plain = _presentation_text(Session(), WELCOME_BANNER)
assert "\x1b[" not in plain
assert "A S T R A L I S" in plain
assert "Beneath Astralis, something dreams." in plain
print("HEAVY_METAL_BANNER_OK")
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
        self.assertIn("HEAVY_METAL_BANNER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
