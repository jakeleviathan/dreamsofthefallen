from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.combat import EnemyDefinition
from mud.consider import assess_threat, challenge_rank, handle_consider
from mud.partial_target_matching import resolve_target_command
from mud.world import NpcDefinition


ROOT = Path(__file__).resolve().parents[1]


class _World:
    def __init__(self, *, npc_keys=(), enemy_keys=(), tags=()):
        self._scene = SimpleNamespace(npc_keys=tuple(npc_keys), enemy_keys=tuple(enemy_keys))
        self.legacy_rooms = {
            "test_room": SimpleNamespace(tags=tuple(tags)),
        }

    def scene(self, _room_key):
        return self._scene


class _Session:
    def __init__(self, *, level=1, mobile_npcs=None):
        self.character = SimpleNamespace(current_room="test_room", level=level)
        self.mobile_npcs = mobile_npcs
        self.database = None
        self.active_enemy = None
        self.sent: list[str] = []

    async def send(self, text: str):
        self.sent.append(text)


class ConsiderBandTests(unittest.TestCase):
    def test_level_difference_maps_to_seven_qualitative_bands(self):
        expectations = {
            -5: "trivial",
            -4: "easy",
            -2: "manageable",
            0: "even",
            2: "dangerous",
            4: "very_dangerous",
            6: "deadly",
        }
        for delta, expected in expectations.items():
            with self.subTest(delta=delta):
                self.assertEqual(assess_threat(10, 10 + delta).key, expected)

    def test_generated_elite_and_boss_keys_receive_hidden_rank(self):
        elite = SimpleNamespace(key="crypt_miniboss", aliases=(), challenge_rank="normal")
        boss = SimpleNamespace(key="crypt_final_boss", aliases=(), challenge_rank="normal")
        self.assertEqual(challenge_rank(elite), "elite")
        self.assertEqual(challenge_rank(boss), "boss")


class ConsiderTargetMatchingTests(unittest.TestCase):
    def test_con_unique_prefix_expands_to_full_visible_target(self):
        enemy = EnemyDefinition(
            key="swamp_troll",
            name="Swamp Troll",
            aliases=("troll",),
            description="a broad-backed troll streaked with mire",
            max_hp=180,
            armor_class=12,
            auto_attack_damage=11,
            auto_attack_interval=3.0,
            xp_reward=100,
        )
        world = _World(enemy_keys=(enemy.key,))
        session = _Session()
        with patch.dict("mud.partial_target_matching.ENEMIES_BY_KEY", {enemy.key: enemy}, clear=True):
            resolution = resolve_target_command(session, "con swamp", world)
        self.assertEqual(resolution.command, "con Swamp Troll")
        self.assertEqual(resolution.matched_name, "Swamp Troll")
        self.assertFalse(resolution.ambiguous)


class ConsiderCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_consider_and_con_report_danger_without_starting_combat_or_stats(self):
        enemy = EnemyDefinition(
            key="bog_snapper",
            name="Bog Snapper",
            aliases=("snapper", "bog snapper"),
            description="a squat amphibious scavenger",
            max_hp=220,
            armor_class=14,
            auto_attack_damage=12,
            auto_attack_interval=3.0,
            xp_reward=120,
        )
        world = _World(enemy_keys=(enemy.key,), tags=("level_12_12",))
        session = _Session(level=10)

        with patch.dict("mud.actor_inspection.ENEMIES_BY_KEY", {enemy.key: enemy}, clear=True):
            for command in ("consider Bog Snapper", "con snapper"):
                session.sent.clear()
                with self.subTest(command=command):
                    handled = await handle_consider(session, command, world)
                    self.assertTrue(handled)
                    output = "".join(session.sent)
                    self.assertIn("Threat: Dangerous", output)
                    self.assertIn("looks stronger than you", output)
                    self.assertNotIn("220", output)
                    self.assertNotIn("14", output)
                    self.assertNotIn("12.0", output)
                    self.assertIsNone(session.active_enemy)

    async def test_boss_modifier_is_hidden_but_changes_the_read(self):
        boss = EnemyDefinition(
            key="glass_catacomb_boss",
            name="Glass Warden",
            aliases=("warden",),
            description="a towering warden of smoked glass",
            max_hp=500,
            armor_class=18,
            auto_attack_damage=18,
            auto_attack_interval=3.0,
            xp_reward=400,
        )
        world = _World(enemy_keys=(boss.key,), tags=("level_10_10",))
        session = _Session(level=10)
        with patch.dict("mud.actor_inspection.ENEMIES_BY_KEY", {boss.key: boss}, clear=True):
            await handle_consider(session, "consider warden", world)
        output = "".join(session.sent)
        self.assertIn("Threat: Very Dangerous", output)
        self.assertNotIn("boss", output.lower())
        self.assertNotIn("+4", output)

    async def test_friendly_npc_reports_no_interest_in_fighting(self):
        npc = NpcDefinition(
            key="pella",
            name="Pella Mireglass",
            short_description="a field apothecary",
            room_key="test_room",
            role="apothecary",
        )
        world = _World(npc_keys=(npc.key,))
        session = _Session(level=1)
        with patch.dict("mud.actor_inspection.NPCS_BY_KEY", {npc.key: npc}, clear=True):
            handled = await handle_consider(session, "con Pella Mireglass", world)
        self.assertTrue(handled)
        self.assertIn("do not seem interested in fighting you", "".join(session.sent))

    async def test_defeated_static_enemy_reports_already_dead(self):
        enemy = EnemyDefinition(
            key="dead_rat",
            name="Sewer Rat",
            aliases=("rat",),
            description="a large rat",
            max_hp=20,
            armor_class=3,
            auto_attack_damage=2,
            auto_attack_interval=3.4,
            xp_reward=15,
        )
        world = _World(enemy_keys=(enemy.key,), tags=("level_1_1",))
        session = _Session(level=1)
        with patch.dict("mud.consider.ENEMIES_BY_KEY", {enemy.key: enemy}, clear=True), patch(
            "mud.consider.static_enemy_available", return_value=False
        ):
            handled = await handle_consider(session, "consider rat", world)
        self.assertTrue(handled)
        self.assertIn("Sewer Rat is already dead", "".join(session.sent))

    async def test_bare_consider_gives_usage(self):
        session = _Session()
        handled = await handle_consider(session, "consider", _World())
        self.assertTrue(handled)
        self.assertIn("CONSIDER <target>", "".join(session.sent))


class ProductionConsiderTests(unittest.TestCase):
    def test_production_entrypoint_installs_consider_and_help_catalogs_it(self):
        code = r'''
import server
import mud.command_guide as command_guide
assert server.PlayerSession._consider_runtime_installed
assert any(entry.syntax == "CONSIDER / CON <target>" for entry in command_guide.COMMANDS)
print("CONSIDER_OK")
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
        self.assertIn("CONSIDER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
