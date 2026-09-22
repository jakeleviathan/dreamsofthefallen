from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.command_guide as command_guide
from mud.deep_help import (
    CATEGORY_INFO,
    TOPICS,
    TOPICS_BY_KEY,
    _find_exact_commands,
    _search_commands,
    _search_topics,
    install_deep_help_runtime,
    validate_help_library,
)


ROOT = Path(__file__).resolve().parents[1]


class _State:
    DISCONNECTED = "disconnected"


class _Session:
    def __init__(self, command: str) -> None:
        self.command = command
        self.character = SimpleNamespace(id=1, name="Prime", current_room="waymeet_crossroads")
        self.state = _State()
        self.messages: list[str] = []

    async def prompt(self, _text: str):
        return self.command

    async def send(self, text: str) -> None:
        self.messages.append(text)

    async def playing_prompt(self) -> None:
        command = await self.prompt("\r\n> ")
        self.messages.append(f"BASE:{command}\n")


class DeepHelpLibraryTests(unittest.TestCase):
    def _run(self, command: str) -> str:
        class Session(_Session):
            pass

        install_deep_help_runtime(Session)
        session = Session(command)
        asyncio.run(session.playing_prompt())
        return "".join(session.messages)

    def test_library_validates_and_has_real_depth(self):
        self.assertEqual(validate_help_library(), ())
        self.assertGreaterEqual(len(TOPICS), 30)
        self.assertGreaterEqual(len(CATEGORY_INFO), 12)
        for key in ("getting-started", "combat-basics", "crafting", "custom-channels", "ecology", "factions", "help-system"):
            self.assertIn(key, TOPICS_BY_KEY)

    def test_missing_live_systems_are_added_to_canonical_catalog(self):
        syntaxes = {entry.syntax for entry in command_guide.COMMANDS}
        required = {
            "TRACKS / WILDLIFE / READ LAND / CONDITIONS / ECOLOGY",
            "REPUTATION / REP / STANDING / FACTIONS",
            "CHANNELS / CHANNEL LIST / CHANNEL HELP",
            "CHANNEL CREATE <name> / CHANNEL JOIN <name> / CHANNEL LEAVE <name>",
            "HISTORY <serial>",
            "VOTE / VOTE CLAIM",
            "ECHOES / ECHOES SHOP / ECHOES BUY <name>",
            "TITLES / TITLE SET <name> / TITLE CLEAR",
            "COSMETICS / COSMETIC SET <name> / COSMETIC CLEAR AURA|SIGIL",
            "HUNT / HUNT STATUS",
            "RACIAL",
            "SETTINGS / PREFERENCES / ACCESSIBILITY",
            "BUG [note] / FEEDBACK [note] / STUCK [note]",
            "HELP <topic> / HELP CATEGORIES / HELP INDEX",
        }
        self.assertTrue(required.issubset(syntaxes), required - syntaxes)

    def test_every_catalog_entry_has_automatic_command_help(self):
        for entry in command_guide.COMMANDS:
            aliases = _find_exact_commands(entry.syntax.split("/")[0].split("<")[0].split("[")[0].strip())
            self.assertTrue(entry.description.strip())
            self.assertTrue(entry.syntax.strip())
            self.assertTrue(
                aliases or _search_commands(entry.syntax.split()[0]),
                entry.syntax,
            )

    def test_topic_and_command_search_span_the_same_library(self):
        self.assertEqual(_search_topics("regeneration")[0].key, "health")
        self.assertTrue(any("HUNT" in entry.syntax for entry in _search_commands("grind")))
        self.assertTrue(any("CHANNEL" in entry.syntax for entry in _search_commands("custom channel")))

    def test_help_home_is_a_category_map_not_a_tiny_cheat_sheet(self):
        output = self._run("help")
        self.assertIn("Dreams of the Fallen Help Library", output)
        self.assertIn("Movement & Exploration", output)
        self.assertIn("Combat & Survival", output)
        self.assertIn("Settings & Accessibility", output)
        self.assertIn("HELP SEARCH", output)
        self.assertIn("HELP INDEX", output)
        self.assertIn("HELP CATALOG", output)

    def test_category_topic_and_command_rabbit_holes(self):
        combat = self._run("help combat")
        self.assertIn("Combat & Survival", combat)
        self.assertIn("HELP COMBAT-BASICS", combat)

        hunting = self._run("help hunting")
        self.assertIn("Hunting & Combat Grinding", hunting)
        self.assertIn("HUNT or HUNT STATUS", hunting)
        self.assertIn("See also:", hunting)

        attack = self._run("help command attack")
        self.assertIn("Command Help:", attack)
        self.assertIn("ATTACK", attack)
        self.assertIn("Purpose", attack)

    def test_help_search_finds_concepts_and_commands(self):
        output = self._run("help search corpse")
        self.assertIn("Help Search: corpse", output)
        self.assertIn("Corpses & Physical Loot", output)
        self.assertIn("LOOT CORPSE", output)

    def test_help_index_and_catalog_are_exhaustive_browsing_paths(self):
        index = self._run("help index")
        self.assertIn("Help Index", index)
        self.assertIn(f"{len(TOPICS)} conceptual topics", index)

        catalog = self._run("help catalog")
        self.assertIn("Complete Command Catalog", catalog)
        self.assertIn("Catalog total:", catalog)
        self.assertIn("CHANNEL CREATE", catalog)
        self.assertIn("REPUTATION / REP / STANDING / FACTIONS", catalog)

    def test_non_help_commands_delegate_unchanged(self):
        output = self._run("look")
        self.assertEqual(output, "BASE:look\n")


class ProductionDeepHelpTests(unittest.TestCase):
    def test_production_runtime_installs_deep_help_outside_canonical_help(self):
        code = r"""
import server
import mud.command_guide as guide
from mud.deep_help import validate_help_library

assert server.PlayerSession._runtime_remediation_installed
assert server.PlayerSession._canonical_command_help_installed
assert server.PlayerSession._deep_help_runtime_installed
assert server.PlayerSession._final_command_telemetry_installed
assert validate_help_library() == ()
syntaxes = {entry.syntax for entry in guide.COMMANDS}
assert "REPUTATION / REP / STANDING / FACTIONS" in syntaxes
assert "VOTE / VOTE CLAIM" in syntaxes
assert "CHANNELS / CHANNEL LIST / CHANNEL HELP" in syntaxes
print("DEEP_HELP_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("DEEP_HELP_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
