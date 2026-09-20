from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.health_regeneration import (
    HEALTH_REGEN_RULES,
    _health_recovery_loop,
    health_recovery_amount,
    recover_health_once,
    restore_health,
)


ROOT = Path(__file__).resolve().parents[1]


class _World:
    def __init__(self, *, tags=(), feature_names=()):
        self._scene = SimpleNamespace(
            tags=tuple(tags),
            features=tuple(SimpleNamespace(name=name) for name in feature_names),
        )

    def scene(self, _room_key):
        return self._scene


class _Session:
    def __init__(
        self,
        *,
        hp=28,
        max_hp=31,
        race="goblin",
        resting=False,
    ):
        self.character = SimpleNamespace(current_room="test_room", race=race)
        self.combatant = SimpleNamespace(
            current_hp=hp,
            max_hp=max_hp,
            race_key=race,
        )
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.selected_enemy = None
        self._movement_resting = resting
        self.client_state_pushes = 0

    async def send_client_state(self):
        self.client_state_pushes += 1


class HealthRegenerationRuleTests(unittest.TestCase):
    def test_goblin_prime_case_recovers_one_hp_out_of_combat(self):
        session = _Session(hp=28, max_hp=31, race="goblin")
        self.assertEqual(health_recovery_amount(session, _World()), 1)
        self.assertEqual(recover_health_once(session, _World()), 1)
        self.assertEqual(session.combatant.current_hp, 29)

    def test_rest_and_restful_place_accelerate_health_recovery(self):
        standing = _Session(resting=False)
        resting = _Session(resting=True)
        safe_resting = _Session(resting=True)
        self.assertEqual(health_recovery_amount(standing, _World()), 1)
        self.assertEqual(health_recovery_amount(resting, _World()), 2)
        self.assertEqual(
            health_recovery_amount(safe_resting, _World(tags=("safe",))),
            3,
        )

    def test_troll_and_sporekin_regeneration_stack_on_normal_tick(self):
        self.assertEqual(health_recovery_amount(_Session(race="troll"), _World()), 2)
        self.assertEqual(health_recovery_amount(_Session(race="sporekin"), _World()), 3)
        self.assertEqual(
            health_recovery_amount(_Session(race="troll", resting=True), _World(tags=("safe",))),
            4,
        )
        self.assertEqual(
            health_recovery_amount(_Session(race="sporekin", resting=True), _World(tags=("safe",))),
            5,
        )

    def test_health_regeneration_pauses_during_combat_but_not_passive_targeting(self):
        session = _Session(resting=True)
        session.selected_enemy = object()
        self.assertEqual(health_recovery_amount(session, _World(tags=("safe",))), 3)

        session.active_enemy = object()
        self.assertEqual(health_recovery_amount(session, _World(tags=("safe",))), 0)
        session.active_enemy = None
        session.active_mobile_npc_key = "hunter"
        self.assertEqual(health_recovery_amount(session, _World(tags=("safe",))), 0)

    def test_recovery_caps_at_maximum(self):
        session = _Session(hp=30, max_hp=31)
        self.assertEqual(restore_health(session, 50), 1)
        self.assertEqual(session.combatant.current_hp, 31)
        self.assertEqual(recover_health_once(session, _World()), 0)

    def test_interval_is_six_seconds(self):
        self.assertEqual(HEALTH_REGEN_RULES.recovery_interval_seconds, 6.0)


class HealthRegenerationLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_background_tick_heals_and_pushes_hud_state(self):
        session = _Session(hp=28, max_hp=31)
        calls = 0

        async def fake_sleep(_seconds):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError

        with patch("mud.health_regeneration.asyncio.sleep", fake_sleep):
            await _health_recovery_loop(session, _World())

        self.assertEqual(session.combatant.current_hp, 29)
        self.assertEqual(session.client_state_pushes, 1)


class ProductionHealthRegenerationContractTests(unittest.TestCase):
    def test_production_entrypoint_installs_health_regeneration(self):
        code = r"""
import server
from types import SimpleNamespace
from mud.health_regeneration import health_recovery_amount, recover_health_once

assert server.PlayerSession._health_regeneration_runtime_installed

session = SimpleNamespace(
    character=SimpleNamespace(current_room="goblin_clattergate", race="goblin"),
    combatant=SimpleNamespace(current_hp=28, max_hp=31, race_key="goblin"),
    active_enemy=None,
    active_mobile_npc_key=None,
    selected_enemy=None,
    _movement_resting=False,
)
assert health_recovery_amount(session, server.WORLD) == 1
assert recover_health_once(session, server.WORLD) == 1
assert session.combatant.current_hp == 29

print("HEALTH_REGEN_RUNTIME_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("HEALTH_REGEN_RUNTIME_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
