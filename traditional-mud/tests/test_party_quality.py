from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.combat import EnemyDefinition, EnemyState
from mud.database import Database
import mud.party_system as party_system
from mud.party_quality import (
    _enhanced_loot_announcement,
    _monitor_party_combat,
    _set_focus,
    _set_ready,
    _show_party_hud,
    _show_nearby,
    _start_ready_check,
    install_party_quality_runtime,
    reset_party_quality_state,
)


TEST_ENEMY = EnemyDefinition(
    key="quality_test_bandit",
    name="Quality Test Bandit",
    aliases=("bandit",),
    description="a test bandit",
    max_hp=100,
    armor_class=5,
    auto_attack_damage=5,
    auto_attack_interval=3.0,
    xp_reward=100,
)


class _QualitySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None
        self.combatant = SimpleNamespace(
            current_hp=100,
            max_hp=100,
            current_mana=100,
            max_mana=100,
            current_movement=100,
            max_movement=100,
        )
        self.ward_until = 0.0
        self.state = SimpleNamespace()
        self.block_movement = False

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def send_client_state(self) -> None:
        return None

    async def _stop_combat(self, **_kwargs) -> None:
        self.active_enemy = None
        self.combat_task = None

    async def move_character(self, direction: str) -> None:
        if self.block_movement:
            return
        if direction.lower() in {"east", "e"}:
            self.database.set_character_room(self.character.id, "room_b")
            self.character = self.database.get_character_by_name(self.character.name)

    async def start_combat(self, _target: str) -> None:
        return None

    async def _combat_loop(self, _enemy) -> None:
        return None

    async def _finish_enemy_defeat(self, _enemy) -> None:
        self.active_enemy = None

    async def close(self) -> None:
        return None

    async def playing_prompt(self) -> None:
        return None

    async def prompt(self, _text: str):
        return None


class PartyQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        party_system.reset_party_runtime_state()
        reset_party_quality_state()
        party_system._ACTIVE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "quality.db")
        account = self.database.create_account("qualityacct", "hash")
        self.sessions = []
        for name in ("Aster", "Bram", "Cora", "Dain"):
            character = self.database.create_character(account.id, name, "human", "brute")
            self.database.set_character_room(character.id, "room_a")
            character = self.database.get_character_by_name(name)
            session = _QualitySession(self.database, character)
            self.sessions.append(session)
            party_system._ACTIVE_SESSIONS.add(session)

    def tearDown(self) -> None:
        party_system.reset_party_runtime_state()
        reset_party_quality_state()
        party_system._ACTIVE_SESSIONS.clear()
        self.tempdir.cleanup()

    def _form_pair(self):
        leader, member = self.sessions[:2]
        asyncio.run(party_system._invite(leader, member.character.name))
        asyncio.run(party_system._accept(member))
        return leader, member, party_system._party_for_session(leader)

    def test_nearby_discovery_surfaces_ungrouped_players_in_the_same_room(self):
        leader = self.sessions[0]
        asyncio.run(_show_nearby(leader))
        text = "".join(leader.sent)
        self.assertIn("Bram", text)
        self.assertIn("Cora", text)
        self.assertIn("PARTY INVITE ALL", text)

    def test_ready_check_makes_group_readiness_explicit(self):
        leader, member, _party = self._form_pair()
        asyncio.run(_start_ready_check(leader))
        asyncio.run(_set_ready(member, True))
        combined = "".join(leader.sent + member.sent)
        self.assertIn("Ready Check", combined)
        self.assertIn("ALL READY (2/2)", combined)

    def test_party_hud_shows_focus_health_and_separation_at_a_glance(self):
        leader, member, _party = self._form_pair()
        asyncio.run(_set_focus(leader, "Signal Runner"))
        member.combatant.current_hp = 20
        self.database.set_character_room(member.character.id, "room_b")
        member.character = self.database.get_character_by_name(member.character.name)
        asyncio.run(_show_party_hud(leader))
        text = "".join(leader.sent)
        self.assertIn("Focus: Signal Runner", text)
        self.assertIn("Bram: 20% HP", text)
        self.assertIn("SEPARATED", text)
        self.assertIn("CRITICAL", text)

    def test_combat_monitor_announces_aggro_and_critical_health(self):
        leader, member, party = self._form_pair()
        enemy = EnemyState(TEST_ENEMY)
        leader.active_enemy = enemy
        member.active_enemy = enemy
        member.combatant.current_hp = 20

        async def exercise():
            encounter = party_system._ensure_encounter(leader, enemy)
            encounter.participant_ids.add(member.character.id)
            enemy.hate.add_threat(leader.character.id, 2)
            enemy.hate.add_threat(member.character.id, 10)
            task = asyncio.create_task(_monitor_party_combat(leader, enemy))
            await asyncio.sleep(0.03)
            encounter.resolved = True
            await task

        asyncio.run(exercise())
        combined = "".join(leader.sent + member.sent)
        self.assertIn("AGGRO -> Bram", combined)
        self.assertIn("Bram is CRITICAL", combined)
        self.assertIs(party, party_system._party_for_session(member))

    def test_follow_failure_is_called_out_as_separation_instead_of_silent_desync(self):
        leader, member, _party = self._form_pair()
        member.block_movement = True
        party_system.install_party_runtime(_QualitySession)
        install_party_quality_runtime(_QualitySession)
        asyncio.run(leader.move_character("east"))
        self.assertEqual(leader.character.current_room, "room_b")
        self.assertEqual(member.character.current_room, "room_a")
        combined = "".join(leader.sent + member.sent)
        self.assertIn("Party Sync", combined)
        self.assertIn("SEPARATED", combined)

    def test_party_loot_announcement_is_visible_to_the_whole_group(self):
        leader, member, _party = self._form_pair()
        asyncio.run(_enhanced_loot_announcement(leader, member, "Loot", ["1x Iron Fitting"]))
        self.assertIn("Iron Fitting -> Bram", "".join(leader.sent))
        self.assertIn("Iron Fitting -> Bram", "".join(member.sent))
        self.assertIn("ROUNDROBIN", "".join(member.sent))

    def test_production_server_installs_multiplayer_clarity_outermost(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "import mud.party_loot as party_loot; "
            "assert getattr(server.PlayerSession, '_party_runtime_installed', False); "
            "assert getattr(server.PlayerSession, '_party_quality_runtime_installed', False); "
            "assert party_loot._announce_distribution.__module__ == 'mud.party_quality'; "
            "print('PARTY_QUALITY_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PARTY_QUALITY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
