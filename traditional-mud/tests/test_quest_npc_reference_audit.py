from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.quest_npc_audit import stale_quest_talk_references


ROOT = Path(__file__).resolve().parents[1]


class QuestNpcReferenceAuditTests(unittest.TestCase):
    def test_production_quest_talk_targets_match_current_npcs(self):
        code = r"""
import server
import mud.quests as quests
import mud.world as world
from mud.quest_npc_audit import (
    quest_talk_references,
    stale_quest_talk_references,
    validate_quest_talk_references,
)

stale = stale_quest_talk_references(quests.QUESTS_BY_KEY, world.NPCS_BY_KEY)
assert not stale, "\n".join(
    f"{row.quest_key}:{row.step_key}: TALK {row.target} :: {row.objective}"
    for row in stale
)
count = validate_quest_talk_references(quests.QUESTS_BY_KEY, world.NPCS_BY_KEY)
assert count == len(quest_talk_references(quests.QUESTS_BY_KEY))
print(f"QUEST_NPC_REFERENCE_AUDIT_OK:{count}")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("QUEST_NPC_REFERENCE_AUDIT_OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
