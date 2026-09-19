from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EnemyTargetingProductionTests(unittest.TestCase):
    def test_target_then_hotbar_spell_engages_and_hits_selected_enemy(self):
        code = r"""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

import server
from mud.database import Database
from mud.mechanics import CombatantState
from mud.session import SessionState
from mud.stats import CharacterStats
from mud.world import HUMAN_VERMIN_PENS_KEY

async def run():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "targeting.db")
        account = db.create_account("targettest", "x")
        character = db.create_character(
            account.id,
            "TargetPriest",
            "human",
            "priest",
            CharacterStats(might=5, grace=5, love=8, mind=8, hp=12),
            deity_key="zerjz",
        )
        db.set_character_room(character.id, HUMAN_VERMIN_PENS_KEY)
        character = db.get_character_by_name(character.name)

        session = object.__new__(server.PlayerSession)
        session.database = db
        session.character = character
        session.state = SessionState.PLAYING
        session.combatant = CombatantState(
            character_id=character.id,
            race_key="human",
            current_hp=40,
            max_hp=40,
            current_mana=40,
            max_mana=40,
            auto_attack_interval=99.0,
            stats=CharacterStats(might=5, grace=5, love=8, mind=8, hp=12),
            armor_class=0,
        )
        session.active_enemy = None
        session.active_mobile_npc_key = None
        session.selected_enemy = None
        session.selected_mobile_npc_key = None
        session.selected_enemy_room_key = None
        session.combat_task = None
        session.dot_tasks = set()
        session.ward_until = 0.0
        session.mobile_npcs = None
        session.current_opponent = None
        session.telnet = SimpleNamespace(gmcp_enabled=False)
        output = []

        async def send(text):
            output.append(text)
        session.send = send

        # Selecting is passive: the target exists in the HUD state, but no
        # auto-attack task or active encounter starts.
        handled = await session.select_enemy_target("rat")
        assert handled
        assert session.selected_enemy is not None
        assert session.selected_enemy.definition.name == "Sewer Rat"
        assert session.active_enemy is None
        assert session.combat_task is None
        selected_hp = session.selected_enemy.current_hp

        # This models pressing CAST SACRED SPARK from the hotbar. The targeting
        # layer promotes the passive selection to the combat opponent just in
        # time for the enemy-targeted ability.
        await session.use_ability("sacred spark")
        assert session.active_enemy is not None
        assert session.active_enemy.definition.name == "Sewer Rat"
        assert session.active_enemy.current_hp < selected_hp
        assert session.combat_task is not None
        assert any("Sacred Spark hits Sewer Rat" in line for line in output), output

        await session._stop_combat()
        assert session.active_enemy is None
        assert session.selected_enemy is None

asyncio.run(run())
print("TARGET_HOTBAR_SPELL_OK")
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
        self.assertIn("TARGET_HOTBAR_SPELL_OK", result.stdout)

    def test_targeting_runtime_is_installed_in_production(self):
        code = r"""
import server
assert server.PlayerSession._enemy_targeting_runtime_installed
assert hasattr(server.PlayerSession, "select_enemy_target")
assert hasattr(server.PlayerSession, "clear_enemy_target")
assert hasattr(server.PlayerSession, "engage_selected_enemy")
print("TARGET_RUNTIME_OK")
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
        self.assertIn("TARGET_RUNTIME_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
