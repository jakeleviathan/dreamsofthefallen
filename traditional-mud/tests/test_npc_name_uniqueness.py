from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.npc_name_audit import (
    NpcNameRecord,
    duplicate_full_names,
    duplicate_given_names,
    likely_given_name,
)


ROOT = Path(__file__).resolve().parents[1]


class NpcNameHeuristicTests(unittest.TestCase):
    def test_title_is_not_mistaken_for_given_name(self):
        self.assertEqual(likely_given_name("Claimwright Pella Six-Wires"), "pella")
        self.assertEqual(likely_given_name("Road-Captain Elian Voss"), "elian")
        self.assertIsNone(likely_given_name("High Acolyte"))
        self.assertIsNone(likely_given_name("Blackwall Guard"))

    def test_duplicate_given_names_catch_titled_and_untitled_people(self):
        records = (
            NpcNameRecord("a", "Claimwright Pella Six-Wires", "static"),
            NpcNameRecord("b", "Pella Mireglass", "static"),
        )
        self.assertIn("pella", duplicate_given_names(records))


class ProductionNpcNameUniquenessTests(unittest.TestCase):
    def test_production_has_unique_authored_npc_names(self):
        code = r"""
import server
import mud.npcs as mobile
import mud.world as world
from mud.npc_name_audit import (
    duplicate_full_names,
    duplicate_given_names,
    format_duplicate_report,
    production_npc_name_records,
)

records = production_npc_name_records(world, mobile)
full = duplicate_full_names(records)
# Given-name reuse is a problem for authored people because TALK commonly accepts
# first names. Mobile wildlife/role labels are covered by full-name uniqueness.
static_records = tuple(row for row in records if row.source == "static")
given = duplicate_given_names(static_records)
report = format_duplicate_report(full, given)
assert not full and not given, report

names = {row.name for row in static_records}
assert "Claimwright Pella Six-Wires" in names
assert "Rixa Mireglass" in names
assert "Pella Mireglass" not in names

print(f"NPC_NAME_AUDIT_OK:{len(records)}")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NPC_NAME_AUDIT_OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
