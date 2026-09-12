from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.blackreed_holdfast import (
    BLACKREED_CAPTAIN_HALL_KEY,
    BLACKREED_CHIEF_DEFEATED_FLAG,
    BLACKREED_COMPLETE_FLAG,
    BLACKREED_FITTING_KEY,
    BLACKREED_PARAPET_KEY,
    BLACKREED_QUEST_KEY,
    BLACKREED_ROUTE_TOKEN_KEY,
    BLACKREED_ROOM_KEYS,
    BLACKREED_ROOMS,
    BLACKREED_RUNNER_DEFEATED_FLAG,
    BLACKREED_SIGNAL_YARD_KEY,
    BLACKREED_TRAILHEAD_KEY,
    BLACKREED_YARDMASTER_DEFEATED_FLAG,
    BOWHAND_KEY,
    BRUISER_KEY,
    CAPTAIN_SKELL_EXPOSED,
    CAPTAIN_SKELL_SHIELDED,
    CHIEF_EXPOSED_KEY,
    CHIEF_SHIELDED_KEY,
    HOUND_KEY,
    KNIFEHAND_KEY,
    REINFORCED_YARDMASTER,
    REINFORCED_YARDMASTER_KEY,
    SHIELDMAN_KEY,
    SIGNAL_RUNNER_KEY,
    YARDMASTER,
    YARDMASTER_KEY,
    _ensure_quest,
    _flank_captain,
    _raise_road_lantern,
    _take_repeat_patrol,
    _talk_scout,
    blackreed_augmentations,
    signal_yard_clear,
    yardmaster_definition_for_flags,
)
from mud.database import Database
from mud.greywake_march import GREYWAKE_WEST_MILE_KEY
from mud.mechanics import PROGRESSION_RULES
from mud.waymeet_frontier import WAYMEET_SCRIP_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None
        self.combatant = SimpleNamespace(current_movement=100, next_auto_attack_at=0.0)

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def refresh(self) -> None:
        current = self.database.get_character_by_name(self.character.name)
        assert current is not None
        self.character = current

    def move_to(self, room_key: str) -> None:
        self.database.set_character_room(self.character.id, room_key)
        self.refresh()


class BlackreedHoldfastTests(unittest.TestCase):
    def _session(self, name: str = "Roadhand"):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "blackreed.db")
        account = database.create_account("blackreedtester", "hash")
        character = database.create_character(account.id, name, "human", "brute")
        database.add_experience(character.id, PROGRESSION_RULES.cumulative_xp_for_level(5))
        database.set_character_room(character.id, BLACKREED_TRAILHEAD_KEY)
        character = database.get_character_by_name(name)
        assert character is not None
        return tempdir, database, _Session(database, character)

    def test_holdfast_is_a_compact_twelve_room_level_five_to_seven_dungeon(self):
        self.assertEqual(len(BLACKREED_ROOM_KEYS), 12)
        self.assertEqual(len(BLACKREED_ROOMS), 12)
        self.assertEqual(len(set(BLACKREED_ROOM_KEYS)), 12)
        by_key = {room.key: room for room in BLACKREED_ROOMS}
        self.assertEqual(set(by_key), set(BLACKREED_ROOM_KEYS))
        self.assertTrue(all(room.region_key == "blackreed_holdfast" for room in BLACKREED_ROOMS))

    def test_greywake_west_mile_opens_the_dungeon_at_level_five(self):
        entry = blackreed_augmentations()[GREYWAKE_WEST_MILE_KEY].extra_exits[0]
        self.assertEqual(entry.destination_key, BLACKREED_TRAILHEAD_KEY)
        self.assertEqual(entry.condition.min_level, 5)
        self.assertEqual(entry.direction, "south")

    def test_enemy_roster_is_readable_traditional_bandits_and_hounds(self):
        from mud.blackreed_holdfast import BLACKREED_ENEMIES

        keys = {enemy.key for enemy in BLACKREED_ENEMIES}
        for key in {
            KNIFEHAND_KEY,
            BOWHAND_KEY,
            SHIELDMAN_KEY,
            BRUISER_KEY,
            HOUND_KEY,
            SIGNAL_RUNNER_KEY,
            YARDMASTER_KEY,
            REINFORCED_YARDMASTER_KEY,
            CHIEF_SHIELDED_KEY,
            CHIEF_EXPOSED_KEY,
        }:
            self.assertIn(key, keys)

    def test_focus_fire_runner_first_materially_weakens_yardmaster(self):
        self.assertFalse(signal_yard_clear(set()))
        dirty = yardmaster_definition_for_flags(set())
        self.assertEqual(dirty.key, REINFORCED_YARDMASTER_KEY)
        self.assertGreater(REINFORCED_YARDMASTER.max_hp, YARDMASTER.max_hp)
        self.assertGreater(REINFORCED_YARDMASTER.auto_attack_damage, YARDMASTER.auto_attack_damage)

        flags = {BLACKREED_RUNNER_DEFEATED_FLAG, BLACKREED_YARDMASTER_DEFEATED_FLAG}
        self.assertTrue(signal_yard_clear(flags))
        clean = yardmaster_definition_for_flags(flags)
        self.assertEqual(clean.key, YARDMASTER_KEY)

    def test_first_clear_starts_at_scout_and_ends_with_personal_lantern_reward(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            quest = database.get_quest(session.character.id, BLACKREED_QUEST_KEY)
            self.assertEqual(quest["current_step"], "talk_scout")

            self.assertTrue(asyncio.run(_talk_scout(session)))
            quest = database.get_quest(session.character.id, BLACKREED_QUEST_KEY)
            self.assertEqual(quest["current_step"], "enter_hold")

            database.advance_quest(session.character.id, BLACKREED_QUEST_KEY, "raise_lantern")
            database.grant_flag(session.character.id, BLACKREED_CHIEF_DEFEATED_FLAG)
            session.move_to(BLACKREED_PARAPET_KEY)
            self.assertTrue(asyncio.run(_raise_road_lantern(session)))

            quest = database.get_quest(session.character.id, BLACKREED_QUEST_KEY)
            self.assertEqual(quest["status"], "completed")
            self.assertIn(BLACKREED_COMPLETE_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.item_quantity(session.character.id, BLACKREED_ROUTE_TOKEN_KEY), 1)
            self.assertEqual(database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 2)
            self.assertIn("public road is open again", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_repeat_patrol_clears_only_run_state(self):
        tempdir, database, session = self._session()
        try:
            database.grant_flag(session.character.id, BLACKREED_COMPLETE_FLAG)
            database.grant_flag(session.character.id, BLACKREED_RUNNER_DEFEATED_FLAG)
            database.grant_flag(session.character.id, BLACKREED_YARDMASTER_DEFEATED_FLAG)
            database.grant_flag(session.character.id, BLACKREED_CHIEF_DEFEATED_FLAG)
            self.assertTrue(asyncio.run(_take_repeat_patrol(session)))
            flags = set(database.list_flags(session.character.id))
            self.assertIn(BLACKREED_COMPLETE_FLAG, flags)
            self.assertNotIn(BLACKREED_RUNNER_DEFEATED_FLAG, flags)
            self.assertNotIn(BLACKREED_YARDMASTER_DEFEATED_FLAG, flags)
            self.assertNotIn(BLACKREED_CHIEF_DEFEATED_FLAG, flags)
        finally:
            tempdir.cleanup()

    def test_final_boss_flank_rewards_two_player_threat_control(self):
        tempdir, database, session = self._session()
        try:
            account = database.get_account_by_name("blackreedtester")
            assert account is not None
            partner = database.create_character(account.id, "Shieldmate", "dwarf", "brute")
            database.add_experience(partner.id, PROGRESSION_RULES.cumulative_xp_for_level(5))
            database.set_character_room(partner.id, BLACKREED_CAPTAIN_HALL_KEY)
            partner = database.get_character_by_name("Shieldmate")
            assert partner is not None
            partner_session = _Session(database, partner)

            session.move_to(BLACKREED_CAPTAIN_HALL_KEY)
            enemy = __import__("mud.combat", fromlist=["EnemyState"]).EnemyState(CAPTAIN_SKELL_SHIELDED)
            session.active_enemy = enemy
            partner_session.active_enemy = enemy
            enemy.hate.add_threat(partner.id, 20.0)
            enemy.hate.add_threat(session.character.id, 1.0)
            session.party_victory_sessions = lambda _enemy: [session, partner_session]

            self.assertTrue(asyncio.run(_flank_captain(session)))
            self.assertEqual(enemy.definition.key, CHIEF_EXPOSED_KEY)
            self.assertLess(CAPTAIN_SKELL_EXPOSED.armor_class, CAPTAIN_SKELL_SHIELDED.armor_class)
            self.assertIn("defensive line is broken", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_production_server_assembles_blackreed_with_loot_and_party_runtime(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "import mud.economy_loop as economy; "
            "from mud.blackreed_holdfast import BLACKREED_ROOM_KEYS, BLACKREED_QUEST_KEY, YARDMASTER_KEY, CHIEF_EXPOSED_KEY, BLACKREED_FITTING_KEY; "
            "from mud.quests import QUESTS_BY_KEY; "
            "assert all(key in server.WORLD.legacy_rooms for key in BLACKREED_ROOM_KEYS); "
            "assert BLACKREED_QUEST_KEY in QUESTS_BY_KEY; "
            "assert economy.LOOT_TABLES[YARDMASTER_KEY][0].item_key == BLACKREED_FITTING_KEY; "
            "assert economy.LOOT_TABLES[CHIEF_EXPOSED_KEY][0].quantity == 2; "
            "assert getattr(server.PlayerSession, '_blackreed_runtime_installed', False); "
            "assert getattr(server.PlayerSession, '_party_runtime_installed', False); "
            "print('BLACKREED_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("BLACKREED_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
