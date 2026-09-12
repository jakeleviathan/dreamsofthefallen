from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.death_recovery import (
    RESURRECTION_MANA_COST,
    _is_dead,
    get_death_record,
    mark_character_dead,
    release_character,
    resurrect_character,
)
from mud.mechanics import CombatantState, DEATH_RULES, PROGRESSION_RULES
from mud.party_system import _ACTIVE_SESSIONS, reset_party_runtime_state
from mud.stats import CharacterStats
from mud.world import HUMAN_START_ROOM_KEY, HUMAN_TRAINING_YARD_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        stats = character.stats if character is not None else CharacterStats()
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "",
            current_hp=stats.maximum_hp(25),
            max_hp=stats.maximum_hp(25),
            current_mana=stats.maximum_mana(20),
            max_mana=stats.maximum_mana(20),
            auto_attack_interval=2.5,
            current_movement=100,
            max_movement=100,
            stats=stats,
        )
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None
        self.dot_tasks = set()
        self.sent: list[str] = []
        self.rooms_shown = 0
        self._death_pending = False

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def send_client_state(self) -> None:
        return None

    async def show_current_room(self) -> None:
        self.rooms_shown += 1

    async def _stop_combat(self, **_kwargs) -> None:
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None

    def refresh(self) -> None:
        updated = self.database.get_character_by_name(self.character.name)
        assert updated is not None
        self.character = updated


class DeathRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_party_runtime_state()
        _ACTIVE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "death.db")
        account = self.database.create_account("deathacct", "hash")

        fighter = self.database.create_character(account.id, "Fallen", "human", "brute")
        level_five_floor = PROGRESSION_RULES.cumulative_xp_for_level(5)
        self.database.add_experience(fighter.id, level_five_floor + 150)
        self.database.set_bind_room(fighter.id, HUMAN_START_ROOM_KEY)
        self.database.set_character_room(fighter.id, HUMAN_TRAINING_YARD_KEY)
        fighter = self.database.get_character_by_name("Fallen")
        assert fighter is not None
        self.fighter = _Session(self.database, fighter)

        priest = self.database.create_character(
            account.id,
            "Mercy",
            "human",
            "priest",
            deity_key="zerjz",
        )
        self.database.add_experience(priest.id, level_five_floor)
        self.database.set_character_room(priest.id, HUMAN_TRAINING_YARD_KEY)
        self.database.set_bind_room(priest.id, HUMAN_START_ROOM_KEY)
        priest = self.database.get_character_by_name("Mercy")
        assert priest is not None
        self.priest = _Session(self.database, priest)

        _ACTIVE_SESSIONS.add(self.fighter)
        _ACTIVE_SESSIONS.add(self.priest)

    def tearDown(self) -> None:
        reset_party_runtime_state()
        _ACTIVE_SESSIONS.clear()
        self.tempdir.cleanup()

    def test_death_stays_in_place_and_does_not_charge_xp_until_release(self):
        before_xp = self.fighter.character.experience
        asyncio.run(mark_character_dead(self.fighter, "Test Ogre"))

        record = get_death_record(self.database, self.fighter.character.id)
        self.assertIsNotNone(record)
        self.assertEqual(record.room_key, HUMAN_TRAINING_YARD_KEY)
        self.assertEqual(record.enemy_name, "Test Ogre")
        self.assertEqual(self.fighter.combatant.current_hp, 0)
        self.assertEqual(self.database.get_character_by_name("Fallen").experience, before_xp)
        self.assertEqual(self.database.get_character_by_name("Fallen").current_room, HUMAN_TRAINING_YARD_KEY)
        self.assertIn("RELEASE", "".join(self.fighter.sent))
        self.assertIn("no death debuff", "".join(self.fighter.sent))

    def test_release_loses_ten_percent_of_current_level_progress_without_deleveling(self):
        before_xp = self.fighter.character.experience
        expected_loss, floor = DEATH_RULES.experience_loss(
            self.fighter.character.level, before_xp
        )
        self.assertEqual(expected_loss, 15)
        self.assertEqual(floor, PROGRESSION_RULES.cumulative_xp_for_level(5))

        asyncio.run(mark_character_dead(self.fighter, "Test Ogre"))
        self.assertTrue(asyncio.run(release_character(self.fighter)))
        self.fighter.refresh()

        self.assertEqual(self.fighter.character.experience, before_xp - expected_loss)
        self.assertEqual(self.fighter.character.level, 5)
        self.assertEqual(self.fighter.character.current_room, HUMAN_START_ROOM_KEY)
        self.assertIsNone(get_death_record(self.database, self.fighter.character.id))
        self.assertEqual(self.fighter.combatant.current_hp, self.fighter.combatant.max_hp)
        self.assertEqual(self.fighter.combatant.current_mana, self.fighter.combatant.max_mana)
        self.assertIn("Death costs 15 experience", "".join(self.fighter.sent))

    def test_level_floor_means_death_never_removes_a_completed_level(self):
        floor = PROGRESSION_RULES.cumulative_xp_for_level(5)
        self.database.apply_experience_loss(self.fighter.character.id, 999999, floor_experience=floor)
        self.fighter.refresh()
        self.assertEqual(self.fighter.character.experience, floor)

        asyncio.run(mark_character_dead(self.fighter, "Test Ogre"))
        self.assertTrue(asyncio.run(release_character(self.fighter)))
        self.fighter.refresh()
        self.assertEqual(self.fighter.character.experience, floor)
        self.assertEqual(self.fighter.character.level, 5)

    def test_priest_resurrection_avoids_xp_loss_and_raises_at_death_site(self):
        before_xp = self.fighter.character.experience
        before_priest_mana = self.priest.combatant.current_mana
        asyncio.run(mark_character_dead(self.fighter, "Test Ogre"))

        self.assertTrue(asyncio.run(resurrect_character(self.priest, "Fallen")))
        self.fighter.refresh()

        self.assertFalse(_is_dead(self.fighter))
        self.assertIsNone(get_death_record(self.database, self.fighter.character.id))
        self.assertEqual(self.fighter.character.experience, before_xp)
        self.assertEqual(self.fighter.character.current_room, HUMAN_TRAINING_YARD_KEY)
        self.assertEqual(
            self.fighter.combatant.current_hp,
            max(1, round(self.fighter.combatant.max_hp * 0.25)),
        )
        self.assertEqual(
            self.priest.combatant.current_mana,
            before_priest_mana - RESURRECTION_MANA_COST,
        )
        self.assertIn("No death XP is lost", "".join(self.fighter.sent))

    def test_non_priest_cannot_resurrect(self):
        asyncio.run(mark_character_dead(self.priest, "Test Ogre"))
        self.assertFalse(asyncio.run(resurrect_character(self.fighter, "Mercy")))
        self.assertIsNotNone(get_death_record(self.database, self.priest.character.id))
        self.assertIn("Priest ability", "".join(self.fighter.sent))

    def test_death_persists_across_a_recreated_session(self):
        asyncio.run(mark_character_dead(self.fighter, "Test Ogre"))
        same_character = self.database.get_character_by_name("Fallen")
        assert same_character is not None
        reconnected = _Session(self.database, same_character)
        self.assertTrue(_is_dead(reconnected))
        self.assertEqual(reconnected.combatant.current_hp, 0)
        self.assertEqual(reconnected._death_enemy_name, "Test Ogre")

    def test_production_server_installs_death_runtime_and_shared_priest_resurrection(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.mechanics import PRIEST_DEITY_ABILITIES; "
            "assert getattr(server.PlayerSession, '_death_recovery_runtime_installed', False); "
            "assert all(any(a.key == 'resurrection' and a.unlock_level == 5 for a in abilities) "
            "for abilities in PRIEST_DEITY_ABILITIES.values()); "
            "print('DEATH_RECOVERY_OK')"
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
        self.assertIn("DEATH_RECOVERY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
