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

    def test_every_named_quest_talk_command_survives_partial_target_matching(self):
        code = r"""
from types import SimpleNamespace

import server
import mud.quests as quests
import mud.world as world
from mud.partial_target_matching import normalize_target, resolve_target_command
from mud.quest_npc_audit import GENERIC_TALK_TARGETS, npc_talk_names, quest_talk_references


class FakeWorld:
    def __init__(self, npc_key):
        self._scene = SimpleNamespace(npc_keys=(npc_key,), enemy_keys=())
    def scene(self, _room_key):
        return self._scene


class FakeSession:
    def __init__(self):
        self.character = SimpleNamespace(current_room="audit_room")
        self.mobile_npcs = None


checked = 0
for ref in quest_talk_references(quests.QUESTS_BY_KEY):
    target = normalize_target(ref.target)
    if target in GENERIC_TALK_TARGETS:
        continue
    matching = [
        npc
        for npc in world.NPCS_BY_KEY.values()
        if target in npc_talk_names({npc.key: npc})
    ]
    assert matching, (ref.quest_key, ref.step_key, ref.target)
    # The global NPC-name invariant makes proper-name targets unique; if a
    # multiword role target happens to match more than one actor, each must
    # still preserve the command text when considered locally.
    for npc in matching:
        result = resolve_target_command(
            FakeSession(),
            f"TALK {ref.target}",
            FakeWorld(npc.key),
        )
        assert normalize_target(result.command) == f"talk {target}", (
            ref.quest_key,
            ref.step_key,
            ref.target,
            npc.name,
            result.command,
        )
        checked += 1

assert checked > 0
print(f"QUEST_TALK_ROUTING_OK:{checked}")
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
        self.assertIn("QUEST_TALK_ROUTING_OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
