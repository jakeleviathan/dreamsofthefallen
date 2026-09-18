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
    GOLD,
    GRADIENT_256,
    MID_ORNAMENT,
    SHADOW,
    TOP_ORNAMENT,
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
        self.assertLessEqual(BANNER_WIDTH, 78)

    def test_banner_has_two_large_wordmarks_and_world_identity(self):
        plain = plain_welcome_banner()
        # Two five-row slanted wordmarks make the title itself the artwork rather
        # than putting ordinary text inside another decorative rectangle.
        self.assertEqual(len(DREAMS_WORDMARK), 5)
        self.assertEqual(len(FALLEN_WORDMARK), 5)
        for line in (*DREAMS_WORDMARK, *FALLEN_WORDMARK):
            self.assertIn(line.strip(), plain)
        self.assertIn("O F   T H E", plain)
        self.assertIn("A S T R A L I S", plain)
        self.assertIn("Beneath Astralis, something dreams.", plain)
        self.assertIn("LOGIN     CREATE ACCOUNT", plain)
        self.assertIn("\\|/", plain)
        # The visible splash remains genuine old-client-safe text art.
        plain.encode("ascii")

    def test_dream_sigil_uses_one_fixed_center_axis(self):
        lines = plain_welcome_banner().replace("\r", "").split("\n")
        center = (BANNER_WIDTH - 1) // 2
        sigil_rows = (
            r"\        |        /",
            r"\       |       /",
            r"\      |      /",
            r"------\     |     /------",
            r"\    |    /",
            r"\   |   /",
            r"\  |  /",
            r"\ | /",
            r"\|/",
        )
        for row in sigil_rows:
            line = next(candidate for candidate in lines if candidate.strip() == row)
            axis = line.index("|")
            self.assertEqual(axis, center, row)
            self.assertEqual(center - line.index("\\"), line.index("/") - center, row)

        point = next(candidate for candidate in lines if candidate.strip() == "V")
        self.assertEqual(point.index("V"), center)

    def test_top_and_mid_ornaments_are_true_generated_mirrors(self):
        def mirror(text: str) -> str:
            out = []
            for char in reversed(text):
                if char == "/":
                    out.append("\\")
                elif char == "\\":
                    out.append("/")
                elif char == "<":
                    out.append(">")
                elif char == ">":
                    out.append("<")
                elif char == "(":
                    out.append(")")
                elif char == ")":
                    out.append("(")
                else:
                    out.append(char)
            return "".join(out)

        for row in (*TOP_ORNAMENT, *MID_ORNAMENT):
            self.assertEqual(len(row), 77)
            self.assertEqual(row[39:], mirror(row[:38]), row)

    def test_banner_runs_blue_to_purple_to_pink(self):
        self.assertEqual(GRADIENT_256[0], 33)
        self.assertEqual(GRADIENT_256[-1], 213)
        self.assertIn("\x1b[1;38;5;33m", WELCOME_BANNER)
        self.assertIn("\x1b[1;38;5;99m", WELCOME_BANNER)
        self.assertIn("\x1b[1;38;5;213m", WELCOME_BANNER)
        self.assertIn(SHADOW, WELCOME_BANNER)
        self.assertIn(GOLD, WELCOME_BANNER)
        self.assertEqual(ANSI.sub("", WELCOME_BANNER), plain_welcome_banner())


class ProductionWelcomeBannerTests(unittest.TestCase):
    def test_production_session_uses_new_banner_and_accessibility_can_strip_ansi(self):
        code = r"""
import re
import server
import mud.session as session_module
from mud.final_runtime_policy import _presentation_text

ANSI = re.compile(r"\x1b\[[0-9;]*m")
assert "DREAMS OF THE FALLEN // ASTRALIS" in session_module.WELCOME_BANNER
assert "____  ____  _________" in session_module.WELCOME_BANNER
assert "LOGIN     CREATE ACCOUNT" in session_module.WELCOME_BANNER

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
