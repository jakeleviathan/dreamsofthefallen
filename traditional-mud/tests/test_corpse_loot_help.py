from __future__ import annotations

import unittest

import mud.command_guide as command_guide
from mud.corpse_loot import _install_help_catalog


class CorpseLootHelpTests(unittest.TestCase):
    def test_corpse_commands_are_discoverable_in_command_catalog(self):
        _install_help_catalog()
        syntaxes = {entry.syntax for entry in command_guide.COMMANDS}
        self.assertIn("LOOT CORPSE / LOOT <enemy>", syntaxes)
        self.assertIn("GET / TAKE ALL FROM <corpse or enemy>", syntaxes)
        self.assertIn("GET / TAKE <item> FROM <corpse or enemy>", syntaxes)
        self.assertIn("LOOK / EXAMINE CORPSE", syntaxes)
        self.assertIn("CORPSES", syntaxes)


if __name__ == "__main__":
    unittest.main()
