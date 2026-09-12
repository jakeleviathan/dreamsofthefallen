from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.gravewatch_keep import (
    ARCHER_KEY,
    CAPTAIN_KEY,
    CASTELLAN_KEY,
    CASTELLAN_SIGNET_KEY,
    CHAMPION_KEY,
    CHAPLAIN_KEY,
    GRAVEWATCH_ARCHER_PULL_FLAG,
    GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
    GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
    GRAVEWATCH_COMPLETE_FLAG,
    GRAVEWATCH_GATE_OPEN_FLAG,
    GRAVEWATCH_HOUND_PULL_FLAG,
    GRAVEWATCH_KEEP_ROOM_KEYS,
    GRAVEWATCH_MAP_ROOM_KEY,
    GRAVEWATCH_PIKE_PULL_FLAG,
    GRAVEWATCH_PORTCULLIS_KEY,
    GRAVEWATCH_QUEST_KEY,
    GRAVEWATCH_RIVER_MILE_KEY,
    GRAVEWATCH_ROOM_KEYS,
    GRAVEWATCH_ROOMS,
    HOUND_KEY,
    OLD_GARRISON_IRON_KEY,
    PIKE_KEY,
    REINFORCED_CAPTAIN_KEY,
    RELIEF_SURCOAT_KEY,
    SENTRY_KEY,
    WIGHT_CAPTAIN,
    REINFORCED_WIGHT_CAPTAIN,
    _ensure_quest,
    _light_beacon,
    _open_portcullis,
    _talk_sergeant,
    captain_definition_for_flags,
    courtyard_pull_complete,
    gravewatch_augmentations,
)
from mud.mechanics import PROGRESSION_RULES
from mud.veyra_city import VEYRA_EAST_RIVER_GATE_KEY, VEYRA_RESIDENT_FLAG


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.sent: list[str] = []
        self.combatant = SimpleNamespace(current_movement=100, next_auto_attack_at=0.0)
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def show_current_room(self) -> None:
        return None

    def move_to(self, room_key: str) -> None:
        self.database.set_character_room(self.character.id, room_key)
        self.refresh()

    def refresh(self) -> None:
        current = self.database.get_character_by_name(self.character.name)
        assert current is not None
        self.character = current


class GravewatchKeepTests(unittest.TestCase):
    def _session(self):
        tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(tempdir.name) / "gravewatch.db")
        account = database.create_account("keeptester", "hash")
        character = database.create_character(account.id, "Torchbearer", "human", "brute")
        database.add_experience(character.id, PROGRESSION_RULES.cumulative_xp_for_level(8))
        database.grant_flag(character.id, VEYRA_RESIDENT_FLAG)
        database.set_character_room(character.id, GRAVEWATCH_RIVER_MILE_KEY)
        character = database.get_character_by_name("Torchbearer")
        assert character is not None
        return tempdir, database, _Session(database, character)

    def test_keep_is_a_classic_sixteen_room_fortress_with_two_room_approach(self):
        self.assertEqual(len(GRAVEWATCH_KEEP_ROOM_KEYS), 16)
        self.assertEqual(len(GRAVEWATCH_ROOM_KEYS), 18)
        self.assertEqual(len(GRAVEWATCH_ROOMS), 18)
        self.assertEqual(len(set(GRAVEWATCH_ROOM_KEYS)), 18)
        by_key = {room.key: room for room in GRAVEWATCH_ROOMS}
        self.assertEqual(set(by_key), set(GRAVEWATCH_ROOM_KEYS))
        self.assertTrue(all(room.region_key == "gravewatch_keep" for room in GRAVEWATCH_ROOMS))

    def test_veyra_river_gate_opens_gravewatch_at_level_eight_for_residents(self):
        entry = gravewatch_augmentations()[VEYRA_EAST_RIVER_GATE_KEY].extra_exits[0]
        self.assertEqual(entry.destination_key, GRAVEWATCH_RIVER_MILE_KEY)
        self.assertEqual(entry.condition.min_level, 8)
        self.assertIn(VEYRA_RESIDENT_FLAG, entry.condition.required_flags)

    def test_enemy_roster_is_readable_traditional_undead(self):
        from mud.gravewatch_keep import GRAVEWATCH_ENEMIES

        keys = {enemy.key for enemy in GRAVEWATCH_ENEMIES}
        for key in {
            SENTRY_KEY,
            HOUND_KEY,
            ARCHER_KEY,
            PIKE_KEY,
            CHAMPION_KEY,
            CAPTAIN_KEY,
            CHAPLAIN_KEY,
            CASTELLAN_KEY,
        }:
            self.assertIn(key, keys)

    def test_clean_courtyard_pulls_make_captain_materially_easier(self):
        self.assertFalse(courtyard_pull_complete(set()))
        dirty = captain_definition_for_flags(set())
        self.assertEqual(dirty.key, REINFORCED_CAPTAIN_KEY)
        flags = {GRAVEWATCH_HOUND_PULL_FLAG, GRAVEWATCH_ARCHER_PULL_FLAG, GRAVEWATCH_PIKE_PULL_FLAG}
        self.assertTrue(courtyard_pull_complete(flags))
        clean = captain_definition_for_flags(flags)
        self.assertEqual(clean.key, CAPTAIN_KEY)
        self.assertLess(WIGHT_CAPTAIN.max_hp, REINFORCED_WIGHT_CAPTAIN.max_hp)
        self.assertLess(WIGHT_CAPTAIN.auto_attack_damage, REINFORCED_WIGHT_CAPTAIN.auto_attack_damage)

    def test_first_clear_quest_starts_with_sergeant_and_gate_requires_both_officers(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            quest = database.get_quest(session.character.id, GRAVEWATCH_QUEST_KEY)
            self.assertEqual(quest["current_step"], "report_sergeant")
            self.assertTrue(asyncio.run(_talk_sergeant(session)))
            quest = database.get_quest(session.character.id, GRAVEWATCH_QUEST_KEY)
            self.assertEqual(quest["current_step"], "enter_keep")

            database.advance_quest(session.character.id, GRAVEWATCH_QUEST_KEY, "open_inner_gate")
            session.move_to(GRAVEWATCH_PORTCULLIS_KEY)
            self.assertTrue(asyncio.run(_open_portcullis(session)))
            self.assertNotIn(GRAVEWATCH_GATE_OPEN_FLAG, database.list_flags(session.character.id))

            database.grant_flag(session.character.id, GRAVEWATCH_CAPTAIN_DEFEATED_FLAG)
            database.grant_flag(session.character.id, GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG)
            self.assertTrue(asyncio.run(_open_portcullis(session)))
            self.assertIn(GRAVEWATCH_GATE_OPEN_FLAG, database.list_flags(session.character.id))
            quest = database.get_quest(session.character.id, GRAVEWATCH_QUEST_KEY)
            self.assertEqual(quest["current_step"], "defeat_castellan")
        finally:
            tempdir.cleanup()

    def test_beacon_finishes_first_clear_with_real_dungeon_rewards(self):
        tempdir, database, session = self._session()
        try:
            self.assertTrue(_ensure_quest(session))
            database.advance_quest(session.character.id, GRAVEWATCH_QUEST_KEY, "light_beacon")
            database.grant_flag(session.character.id, "gravewatch_castellan_defeated")
            session.move_to(GRAVEWATCH_MAP_ROOM_KEY)
            self.assertTrue(asyncio.run(_light_beacon(session)))
            quest = database.get_quest(session.character.id, GRAVEWATCH_QUEST_KEY)
            self.assertEqual(quest["status"], "completed")
            self.assertIn(GRAVEWATCH_COMPLETE_FLAG, database.list_flags(session.character.id))
            self.assertEqual(database.item_quantity(session.character.id, CASTELLAN_SIGNET_KEY), 1)
            self.assertEqual(database.item_quantity(session.character.id, RELIEF_SURCOAT_KEY), 1)
            self.assertIn("sanctioned repeatable delve", "".join(session.sent))
        finally:
            tempdir.cleanup()

    def test_skeletons_feed_necromancer_catalysts_and_wights_feed_smithing_material(self):
        # Run this through the canonical production assembler in a subprocess so
        # the test verifies the real install without mutating mud.world globals in
        # this unittest process. The legacy room-content tests intentionally own
        # their original 26-room registry and should not depend on test order.
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "import mud.economy_loop as economy; "
            "from mud.gravewatch_keep import SENTRY_KEY, CHAMPION_KEY, CAPTAIN_KEY, CHAPLAIN_KEY, OLD_GARRISON_IRON_KEY; "
            "assert economy.LOOT_TABLES[SENTRY_KEY][0].item_key == 'bone_chips'; "
            "assert economy.LOOT_TABLES[CHAMPION_KEY][0].quantity == 2; "
            "assert economy.LOOT_TABLES[CAPTAIN_KEY][0].item_key == OLD_GARRISON_IRON_KEY; "
            "assert economy.LOOT_TABLES[CHAPLAIN_KEY][0].item_key == OLD_GARRISON_IRON_KEY; "
            "print('GRAVEWATCH_LOOT_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GRAVEWATCH_LOOT_OK", result.stdout)

    def test_production_server_assembles_gravewatch(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import server; "
            "from mud.gravewatch_keep import GRAVEWATCH_ROOM_KEYS, GRAVEWATCH_QUEST_KEY; "
            "from mud.quests import QUESTS_BY_KEY; "
            "assert all(key in server.WORLD.legacy_rooms for key in GRAVEWATCH_ROOM_KEYS); "
            "assert GRAVEWATCH_QUEST_KEY in QUESTS_BY_KEY; "
            "assert getattr(server.PlayerSession, '_gravewatch_runtime_installed', False); "
            "print('GRAVEWATCH_OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=project_root, capture_output=True, text=True,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GRAVEWATCH_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
