import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.troll_raid_opening as raid
import mud.troll_start as troll_start
import mud.world as world
from mud.database import Database
from mud.mechanics import CombatantState
from mud.room_engine import WorldService
from mud.stats import CharacterStats


class RaidSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.combatant = CombatantState(
            character_id=character.id,
            race_key="troll",
            current_hp=20,
            max_hp=20,
            current_mana=10,
            max_mana=10,
            auto_attack_interval=2.0,
        )

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None


class RuntimeProbeSession(RaidSession):
    async def enter_character(self):
        return None

    async def playing_prompt(self):
        return None

    def _enemy_in_current_room(self, target_text: str):
        return None

    async def _finish_enemy_defeat(self, enemy):
        return None


class TrollRaidOpeningTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        self.reconcile = troll_start._initialize_or_reconcile_troll
        self.reconcile_patched = raid._RECONCILE_PATCHED

        troll_start.install_troll_content()
        raid.install_troll_raid_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)

        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)

        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)

        troll_start._initialize_or_reconcile_troll = self.reconcile
        raid._RECONCILE_PATCHED = self.reconcile_patched

    def _session(self, name: str = "Ashwake"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "troll_raid.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            "troll",
            "brute",
            CharacterStats(might=13, grace=5, love=5, mind=5, hp=18),
        )
        return temp, database, RaidSession(database, character)

    def test_frostroot_opens_in_recent_raid_aftermath(self):
        room = world.ROOMS_BY_KEY[troll_start.TROLL_START_ROOM_KEY]
        text = room.description.lower()
        self.assertIn("cold mud", text)
        self.assertIn("palisade", text)
        self.assertIn("blackened", text)
        self.assertIn("not the same thing as being safe", text)
        self.assertIn("raid_aftermath", room.tags)

        raska = world.NPCS_BY_KEY[troll_start.RASKA_GREYBARK.key]
        self.assertIn("wounded", raska.role.lower())
        self.assertIn("blood-dark", raska.short_description.lower())

    def test_brand_new_troll_gets_raid_before_old_survival_lessons(self):
        temp, database, session = self._session("FirstNight")
        self.addCleanup(temp.cleanup)

        raid.reconcile_troll_raid_opening(session)

        opening = database.get_quest(session.character.id, raid.TROLL_RAID_QUEST.key)
        cold = database.get_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key)
        self.assertEqual(session.character.current_room, troll_start.TROLL_START_ROOM_KEY)
        self.assertEqual(session.character.bind_room, troll_start.TROLL_START_ROOM_KEY)
        self.assertEqual(opening["status"], "active")
        self.assertEqual(opening["current_step"], "talk_raska")
        self.assertIsNone(cold)

    def test_existing_troll_progress_is_grandfathered_not_reset(self):
        temp, database, session = self._session("OldFrostroot")
        self.addCleanup(temp.cleanup)
        database.start_quest(
            session.character.id,
            troll_start.TROLL_COLD_QUEST.key,
            "read_wind",
        )

        raid.reconcile_troll_raid_opening(session)

        opening = database.get_quest(session.character.id, raid.TROLL_RAID_QUEST.key)
        cold = database.get_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key)
        self.assertEqual(opening["status"], "completed")
        self.assertEqual(cold["current_step"], "read_wind")
        self.assertIn(
            raid.TROLL_RAID_COMPLETE_FLAG,
            database.list_flags(session.character.id),
        )

    def test_spear_real_combat_and_visible_plus_one_regeneration_feed_old_arc(self):
        temp, database, session = self._session("Breachborn")
        self.addCleanup(temp.cleanup)
        raid.reconcile_troll_raid_opening(session)

        self.assertTrue(asyncio.run(raid._talk_raska_raid(session)))
        self.assertTrue(asyncio.run(raid._take_raid_weapon(session, "grab spear")))
        self.assertEqual(
            database.item_quantity(session.character.id, raid.TROLL_RAID_WEAPON_KEY),
            1,
        )

        service = WorldService(
            rooms=world.ROOMS_BY_KEY,
            augmentations=troll_start.troll_room_augmentations(),
        )
        raid.install_troll_raid_runtime(RuntimeProbeSession, service)
        probe = RuntimeProbeSession(database, session.character)
        probe.combatant = session.combatant
        enemy = probe._enemy_in_current_room("scavenger")
        self.assertIsNotNone(enemy)
        self.assertTrue(enemy.definition.retaliates)
        self.assertNotEqual(enemy.definition.key, "training_dummy")

        database.advance_quest(
            session.character.id,
            raid.TROLL_RAID_QUEST.key,
            "recover",
        )
        session.combatant.current_hp = 10
        with patch.object(raid.asyncio, "sleep", new=AsyncMock()):
            asyncio.run(raid._raid_regeneration_sequence(session))
        self.assertEqual(session.combatant.current_hp, 13)
        self.assertEqual(
            database.get_quest(session.character.id, raid.TROLL_RAID_QUEST.key)["current_step"],
            "return_raska",
        )
        combined = "".join(session.outputs)
        self.assertIn("restores 1 HP", combined)

        self.assertTrue(asyncio.run(raid._talk_raska_raid(session)))
        self.assertEqual(
            database.get_quest(session.character.id, raid.TROLL_RAID_QUEST.key)["status"],
            "completed",
        )
        cold = database.get_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key)
        self.assertEqual(cold["status"], "active")
        self.assertEqual(cold["current_step"], "speak_raska")


if __name__ == "__main__":
    unittest.main()
