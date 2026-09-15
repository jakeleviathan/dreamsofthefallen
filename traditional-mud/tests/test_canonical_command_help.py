from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import mud.command_guide as command_guide
from mud.canonical_command_help import _show_quick_help


ROOT = Path(__file__).resolve().parents[1]


class _Session:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class CanonicalCommandCatalogTests(unittest.IsolatedAsyncioTestCase):
    def test_catalog_contains_current_outer_runtime_commands_and_aliases(self):
        syntaxes = {entry.syntax for entry in command_guide.COMMANDS}
        required = {
            "MAP / MAP HERE / MAP 1..4",
            "MOVEMENT / MOVE POINTS / MOVEMENT POINTS / FATIGUE / ENDURANCE",
            "REST / SIT / SIT DOWN",
            "STAND / STAND UP / RISE",
            "LOOK AT / LOOK / EXAMINE / INSPECT <actor>",
            "ITEM / INSPECT ITEM <item>",
            "DRUGS / PERCEPTION / ALTERED / ALTERED STATE",
        }
        self.assertTrue(required.issubset(syntaxes), required - syntaxes)

    async def test_quick_help_is_rendered_from_catalog_entries(self):
        session = _Session()
        await _show_quick_help(session)
        output = "".join(session.messages)
        self.assertIn("The same command catalog powers HELP and COMMANDS", output)
        for syntax in ("MAP / MAP HERE / MAP 1..4", "REST / SIT / SIT DOWN", "ITEM / INSPECT ITEM <item>"):
            self.assertIn(syntax, output)
            self.assertIn(syntax, {entry.syntax for entry in command_guide.COMMANDS})


class ProductionCanonicalCommandHelpTests(unittest.TestCase):
    def test_production_entrypoint_installs_canonical_help_outer_runtime(self):
        code = r'''
import server
import mud.command_guide as guide
assert server.PlayerSession._canonical_command_help_installed
syntaxes = {entry.syntax for entry in guide.COMMANDS}
for expected in (
    "MAP / MAP HERE / MAP 1..4",
    "MOVEMENT / MOVE POINTS / MOVEMENT POINTS / FATIGUE / ENDURANCE",
    "REST / SIT / SIT DOWN",
    "STAND / STAND UP / RISE",
    "LOOK AT / LOOK / EXAMINE / INSPECT <actor>",
    "ITEM / INSPECT ITEM <item>",
    "DRUGS / PERCEPTION / ALTERED / ALTERED STATE",
):
    assert expected in syntaxes, expected
print("CANONICAL_COMMAND_HELP_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("CANONICAL_COMMAND_HELP_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
