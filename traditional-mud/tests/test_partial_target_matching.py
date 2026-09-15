from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.combat import EnemyDefinition
from mud.partial_target_matching import (
    TargetCandidate,
    _match_score,
    normalize_target,
    resolve_target_command,
)
from mud.world import NpcDefinition


ROOT = Path(__file__).resolve().parents[1]


class _World:
    def __init__(self, *, npc_keys=(), enemy_keys=()):
        self._scene = SimpleNamespace(npc_keys=tuple(npc_keys), enemy_keys=tuple(enemy_keys))

    def scene(self, _room_key):
        return self._scene


class _Session:
    def __init__(self):
        self.character = SimpleNamespace(current_room="test_room")
        self.mobile_npcs = None


class PartialTargetMatchingTests(unittest.TestCase):
    def test_name_normalization_handles_case_hyphens_and_spacing(self):
        self.assertEqual(normalize_target("  Grey-Cloaked   Informant "), "grey cloaked informant")

    def test_distinctive_title_first_or_last_name_can_target_npc(self):
        npc = NpcDefinition(
            key="goblin_riveter_nix_hookspit",
            name="Riveter Nix Hookspit",
            short_description="a wiry riveter",
            room_key="test_room",
            role="riveter",
        )
        with patch.dict("mud.partial_target_matching.NPCS_BY_KEY", {npc.key: npc}, clear=True):
            world = _World(npc_keys=(npc.key,))
            session = _Session()
            for command in ("talk riveter", "talk nix", "talk hooks", "talk nix hook"):
                with self.subTest(command=command):
                    resolved = resolve_target_command(session, command, world)
                    self.assertEqual(resolved.command, "talk Riveter Nix Hookspit")
                    self.assertEqual(resolved.matched_name, "Riveter Nix Hookspit")

    def test_speak_is_a_convenience_synonym_for_talk(self):
        npc = NpcDefinition(
            key="human_high_acolyte",
            name="High Acolyte",
            short_description="a senior cleric",
            room_key="test_room",
            role="mentor",
        )
        with patch.dict("mud.partial_target_matching.NPCS_BY_KEY", {npc.key: npc}, clear=True):
            resolved = resolve_target_command(_Session(), "speak acol", _World(npc_keys=(npc.key,)))
        self.assertEqual(resolved.command, "talk High Acolyte")

    def test_enemy_alias_and_prefix_expand_for_attack_or_kill(self):
        enemy = EnemyDefinition(
            key="sewer_rat",
            name="Sewer Rat",
            aliases=("rat", "vermin"),
            description="an oversized rat",
            max_hp=20,
            armor_class=3,
            auto_attack_damage=2,
            auto_attack_interval=3.0,
            xp_reward=15,
        )
        with patch.dict("mud.partial_target_matching.ENEMIES_BY_KEY", {enemy.key: enemy}, clear=True):
            world = _World(enemy_keys=(enemy.key,))
            session = _Session()
            self.assertEqual(resolve_target_command(session, "kill rat", world).command, "kill Sewer Rat")
            self.assertEqual(resolve_target_command(session, "attack sew", world).command, "attack Sewer Rat")

    def test_ambiguous_abbreviation_is_never_guessed(self):
        first = NpcDefinition(
            key="gate_guard",
            name="Gate Guard",
            short_description="a guard",
            room_key="test_room",
            role="guard",
        )
        second = NpcDefinition(
            key="guard_captain",
            name="Guard Captain",
            short_description="a captain",
            room_key="test_room",
            role="captain",
        )
        with patch.dict(
            "mud.partial_target_matching.NPCS_BY_KEY",
            {first.key: first, second.key: second},
            clear=True,
        ):
            resolved = resolve_target_command(
                _Session(),
                "talk guard",
                _World(npc_keys=(first.key, second.key)),
            )
        self.assertTrue(resolved.ambiguous)
        self.assertEqual(resolved.command, "talk guard")
        self.assertEqual(resolved.ambiguous_names, ("Gate Guard", "Guard Captain"))

    def test_exact_name_or_alias_beats_a_looser_prefix(self):
        exact = TargetCandidate("rat", "Rat", "enemy", aliases=("rat",))
        longer = TargetCandidate("rat_king", "Rat King", "enemy")
        self.assertGreater(_match_score("rat", exact), _match_score("rat", longer))

    def test_one_letter_prefix_is_not_expanded(self):
        candidate = TargetCandidate("riveter", "Riveter Nix Hookspit", "npc")
        self.assertEqual(_match_score("r", candidate), 0)
        self.assertGreater(_match_score("ri", candidate), 0)


class ProductionPartialTargetMatchingTests(unittest.TestCase):
    def test_production_entrypoint_installs_partial_target_matching_outer_layer(self):
        code = r'''
import server
assert server.PlayerSession._partial_target_matching_runtime_installed
print("PARTIAL_TARGET_MATCHING_OK")
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
        self.assertIn("PARTIAL_TARGET_MATCHING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
