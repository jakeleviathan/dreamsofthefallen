from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.human_blackwall_opening import (
    HUMAN_BEYOND_WALL_QUEST_KEY,
    HUMAN_BURROWER_DEFEATED_FLAG,
    HUMAN_CARAVAN_QUEST_KEY,
    HUMAN_CINDER_WARD_KEY,
    HUMAN_EARTH_CACHE_QUEST_KEY,
    HUMAN_OPENING_GRANDFATHERED_FLAG,
    HUMAN_OUTER_CARAVAN_ROAD_KEY,
    HUMAN_READINESS_QUEST_KEY,
    HUMAN_SOOTSTEP_TUNNEL_KEY,
    install_human_blackwall_content,
    prepare_human_blackwall_opening,
)
from mud.human_playable_slice import (
    HUMAN_FIRST_MILE_OVERLOOK_KEY,
    HUMAN_SLICE_BURROWER_LOOT_FLAG,
    HUMAN_SLICE_FIRST_RESCUE_FLAG,
    HUMAN_SOOTSTEP_BRACERS_KEY,
    SLICE_MILESTONES,
    burrower_loot_available,
    claim_burrower_loot,
    human_playable_slice_augmentations,
    install_human_playable_slice_content,
    reconcile_human_slice_progression,
    recover_first_burrower_defeat,
)


class FakeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.active_enemy = None
        self.combatant = SimpleNamespace(current_hp=1, max_hp=31, current_mana=2, max_mana=28)
        self.stop_calls = 0
        self.room_shows = 0
        self.client_state_calls = 0

    async def send(self, text: str):
        self.outputs.append(text)

    async def _stop_combat(self, **_kwargs):
        self.stop_calls += 1
        self.active_enemy = None

    async def show_current_room(self):
        self.room_shows += 1

    async def send_client_state(self):
        self.client_state_calls += 1


def move(session: FakeSession, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    refreshed = session.database.get_character_by_name(session.character.name)
    assert refreshed is not None
    session.character = refreshed


class HumanPlayableSliceTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        install_human_blackwall_content()
        install_human_playable_slice_content()

    def tearDown(self):
        legacy_world.ROOMS = self.rooms
        legacy_world.ROOMS_BY_KEY.clear()
        legacy_world.ROOMS_BY_KEY.update(self.rooms_by_key)
        legacy_world.NPCS = self.npcs
        legacy_world.NPCS_BY_KEY.clear()
        legacy_world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)

    def _session(self, name: str = "Slice"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "slice.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(account.id, name, "human", "wizard")
        session = FakeSession(database, character)
        prepare_human_blackwall_opening(session)
        return temp, database, session

    def test_slice_adds_real_loot_and_a_safe_world_handoff_overlook(self):
        outer = legacy_world.ROOMS_BY_KEY[HUMAN_OUTER_CARAVAN_ROAD_KEY]
        self.assertEqual(outer.exits["east"], HUMAN_FIRST_MILE_OVERLOOK_KEY)

        overlook = legacy_world.ROOMS_BY_KEY[HUMAN_FIRST_MILE_OVERLOOK_KEY]
        self.assertIn("safe", overlook.tags)
        self.assertEqual(overlook.exits["west"], HUMAN_OUTER_CARAVAN_ROAD_KEY)

        augmentation = human_playable_slice_augmentations()[HUMAN_FIRST_MILE_OVERLOOK_KEY]
        self.assertGreaterEqual(len(augmentation.features), 2)
        self.assertIn("Nothing is asking to be saved", augmentation.description_layers[0].text)

        bracers = crafting.ITEMS_BY_KEY[HUMAN_SOOTSTEP_BRACERS_KEY]
        self.assertEqual(bracers.equipment.slot, "hands")
        self.assertEqual(bracers.equipment.armor_class, 1)
        self.assertEqual(bracers.equipment.stat_bonuses.hp, 1)

    def test_authored_slice_rewards_plus_burrower_xp_land_fresh_human_at_level_two(self):
        temp, database, session = self._session("Leveler")
        self.addCleanup(temp.cleanup)

        # The real burrower already grants 30 XP through normal combat.
        database.add_experience(session.character.id, 30)
        session.character = database.get_character_by_name(session.character.name)

        expected = 30
        for milestone in SLICE_MILESTONES:
            row = database.get_quest(session.character.id, milestone.quest_key)
            if row is None:
                database.start_quest(session.character.id, milestone.quest_key, "test_step")
            database.complete_quest(session.character.id, milestone.quest_key)
            awards = reconcile_human_slice_progression(session)
            self.assertEqual(len(awards), 1)
            self.assertEqual(awards[0].xp, milestone.xp)
            expected += milestone.xp
            self.assertEqual(session.character.experience, expected)

        self.assertEqual(expected, 100)
        self.assertEqual(session.character.level, 2)
        self.assertEqual(reconcile_human_slice_progression(session), ())

    def test_grandfathered_human_does_not_receive_retroactive_slice_xp(self):
        temp, database, session = self._session("Legacy")
        self.addCleanup(temp.cleanup)
        database.grant_flag(session.character.id, HUMAN_OPENING_GRANDFATHERED_FLAG)
        database.complete_quest(session.character.id, HUMAN_READINESS_QUEST_KEY)

        self.assertEqual(reconcile_human_slice_progression(session), ())
        refreshed = database.get_character_by_name(session.character.name)
        self.assertEqual(refreshed.experience, 0)

    def test_burrower_loot_is_explicit_useful_and_cannot_be_farmed(self):
        temp, database, session = self._session("Looter")
        self.addCleanup(temp.cleanup)
        move(session, HUMAN_SOOTSTEP_TUNNEL_KEY)
        database.grant_flag(session.character.id, HUMAN_BURROWER_DEFEATED_FLAG)

        self.assertTrue(burrower_loot_available(session))
        self.assertTrue(asyncio.run(claim_burrower_loot(session)))
        self.assertEqual(database.item_quantity(session.character.id, HUMAN_SOOTSTEP_BRACERS_KEY), 1)
        self.assertIn(HUMAN_SLICE_BURROWER_LOOT_FLAG, database.list_flags(session.character.id))
        self.assertFalse(asyncio.run(claim_burrower_loot(session)))
        self.assertEqual(database.item_quantity(session.character.id, HUMAN_SOOTSTEP_BRACERS_KEY), 1)
        output = "".join(session.outputs)
        self.assertIn("COMPARE SOOTSTEP HIDE BRACERS", output)
        self.assertIn("EQUIP SOOTSTEP HIDE BRACERS", output)

    def test_first_burrower_defeat_is_a_single_forgiving_recovery_lesson(self):
        temp, database, session = self._session("Rescued")
        self.addCleanup(temp.cleanup)
        move(session, HUMAN_SOOTSTEP_TUNNEL_KEY)
        quest = database.get_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY)
        if quest is None:
            database.start_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "fight_burrower")
        else:
            database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "fight_burrower")
        database.add_experience(session.character.id, 17)
        session.character = database.get_character_by_name(session.character.name)

        self.assertTrue(asyncio.run(recover_first_burrower_defeat(session, "Sootstep Burrower")))
        self.assertEqual(session.character.current_room, HUMAN_CINDER_WARD_KEY)
        self.assertEqual(session.character.experience, 17)
        self.assertEqual(session.combatant.current_hp, session.combatant.max_hp)
        self.assertEqual(session.combatant.current_mana, session.combatant.max_mana)
        self.assertEqual(session.stop_calls, 1)
        self.assertEqual(session.room_shows, 1)
        self.assertIn(HUMAN_SLICE_FIRST_RESCUE_FLAG, database.list_flags(session.character.id))
        self.assertIn("costs no experience", "".join(session.outputs).lower())

        # The protection is instructional, not an infinite immunity to death rules.
        move(session, HUMAN_SOOTSTEP_TUNNEL_KEY)
        self.assertFalse(asyncio.run(recover_first_burrower_defeat(session, "Sootstep Burrower")))


if __name__ == "__main__":
    unittest.main()
