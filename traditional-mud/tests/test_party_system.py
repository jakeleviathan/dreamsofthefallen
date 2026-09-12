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
from mud.party_system import (
    PARTY_MAX_MEMBERS,
    _PARTY_BY_MEMBER,
    _ACTIVE_SESSIONS,
    _accept,
    _encounter_for,
    _ensure_encounter,
    _invite,
    _loot_recipient,
    _party_for_session,
    _party_xp_share,
    _shared_enemy_finish,
    install_party_runtime,
    reset_party_runtime_state,
)


TEST_ENEMY = EnemyDefinition(
    key="party_test_skeleton",
    name="Party Test Skeleton",
    aliases=("skeleton",),
    description="a test skeleton",
    max_hp=100,
    armor_class=5,
    auto_attack_damage=5,
    auto_attack_interval=3.0,
    xp_reward=100,
)


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None
        self.combatant = SimpleNamespace(current_hp=100, max_hp=100, current_mana=100, max_mana=100, current_movement=100, max_movement=100)
        self.ward_until = 0.0
        self.state = SimpleNamespace()
        self.moves: list[str] = []
        self.closed = False

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def send_client_state(self) -> None:
        return None

    async def _stop_combat(self, **_kwargs) -> None:
        self.active_enemy = None
        self.combat_task = None

    async def move_character(self, direction: str) -> None:
        self.moves.append(direction)
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
        self.closed = True

    async def playing_prompt(self) -> None:
        return None

    async def prompt(self, _text: str):
        return None


class PartySystemTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_party_runtime_state()
        _ACTIVE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "party.db")
        account = self.database.create_account("partyacct", "hash")
        self.characters = []
        self.sessions = []
        for index, name in enumerate(("Aster", "Bram", "Cora", "Dain", "Eris"), start=1):
            character = self.database.create_character(account.id, name, "human", "brute")
            self.database.set_character_room(character.id, "room_a")
            character = self.database.get_character_by_name(name)
            self.characters.append(character)
            session = _Session(self.database, character)
            self.sessions.append(session)
            _ACTIVE_SESSIONS.add(session)

    def tearDown(self) -> None:
        reset_party_runtime_state()
        _ACTIVE_SESSIONS.clear()
        self.tempdir.cleanup()

    def test_invite_accept_creates_five_slot_party_with_follow_and_roundrobin_defaults(self):
        leader, member = self.sessions[:2]
        asyncio.run(_invite(leader, member.character.name))
        asyncio.run(_accept(member, leader.character.name))
        party = _party_for_session(leader)
        self.assertIsNotNone(party)
        self.assertIs(party, _party_for_session(member))
        self.assertEqual(PARTY_MAX_MEMBERS, 5)
        self.assertEqual(party.leader_id, leader.character.id)
        self.assertIn(member.character.id, party.follow_ids)
        self.assertEqual(party.loot_mode, "roundrobin")
        self.assertIn("joins the party", "".join(leader.sent))

    def test_shared_xp_uses_one_pool_with_a_modest_group_bonus_not_full_xp_per_player(self):
        self.assertEqual(_party_xp_share(100, 1), 100)
        self.assertEqual(_party_xp_share(100, 2), 60)
        self.assertEqual(_party_xp_share(100, 4), 40)

    def test_roundrobin_loot_rotates_across_actual_encounter_participants(self):
        leader, member, spectator = self.sessions[:3]
        asyncio.run(_invite(leader, member.character.name))
        asyncio.run(_accept(member))
        asyncio.run(_invite(leader, spectator.character.name))
        asyncio.run(_accept(spectator))
        party = _party_for_session(leader)
        enemy = EnemyState(TEST_ENEMY)

        async def prepare():
            encounter = _ensure_encounter(leader, enemy)
            encounter.participant_ids.add(member.character.id)
            return encounter

        encounter = asyncio.run(prepare())
        self.assertIs(encounter, _encounter_for(enemy))
        first = _loot_recipient(leader, enemy, "bone_chips")
        second = _loot_recipient(leader, enemy, "bone_chips")
        third = _loot_recipient(leader, enemy, "bone_chips")
        self.assertEqual(first.character.id, leader.character.id)
        self.assertEqual(second.character.id, member.character.id)
        self.assertEqual(third.character.id, leader.character.id)
        self.assertNotEqual(first.character.id, spectator.character.id)
        self.assertEqual(party.loot_cursor, 1)

    def test_shared_enemy_finish_awards_party_xp_once_and_clears_every_participant(self):
        leader, member = self.sessions[:2]
        asyncio.run(_invite(leader, member.character.name))
        asyncio.run(_accept(member))
        enemy = EnemyState(TEST_ENEMY)
        leader.active_enemy = enemy
        member.active_enemy = enemy

        async def run_finish():
            encounter = _ensure_encounter(leader, enemy)
            encounter.participant_ids.add(member.character.id)

            async def previous_finish(session, defeated):
                self.assertIs(defeated, enemy)
                self.assertEqual(defeated.definition.xp_reward, 0)
                session.active_enemy = None

            await _shared_enemy_finish(leader, enemy, previous_finish)

        asyncio.run(run_finish())
        leader.character = self.database.get_character_by_name(leader.character.name)
        member.character = self.database.get_character_by_name(member.character.name)
        self.assertEqual(leader.character.experience, 60)
        self.assertEqual(member.character.experience, 60)
        self.assertIsNone(leader.active_enemy)
        self.assertIsNone(member.active_enemy)
        self.assertIsNone(_encounter_for(enemy))

    def test_leader_movement_auto_moves_followers_but_not_manual_members(self):
        leader, follower, manual = self.sessions[:3]
        asyncio.run(_invite(leader, follower.character.name))
        asyncio.run(_accept(follower))
        asyncio.run(_invite(leader, manual.character.name))
        asyncio.run(_accept(manual))
        party = _party_for_session(leader)
        party.follow_ids.discard(manual.character.id)

        install_party_runtime(_Session)
        asyncio.run(leader.move_character("east"))

        self.assertEqual(leader.character.current_room, "room_b")
        self.assertEqual(follower.character.current_room, "room_b")
        self.assertEqual(manual.character.current_room, "room_a")
        self.assertIn("east", follower.moves)
        self.assertNotIn("east", manual.moves)

    def test_production_server_installs_party_gravewatch_bridge_and_loot_hooks(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "import mud.party_loot as party_loot; "
            "assert getattr(server.PlayerSession, '_party_runtime_installed', False); "
            "assert getattr(server.PlayerSession, '_gravewatch_party_runtime_installed', False); "
            "assert party_loot._INSTALLED; "
            "assert callable(getattr(server.PlayerSession, 'party_sessions_here', None)); "
            "print('PARTY_OK')"
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
        self.assertIn("PARTY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
