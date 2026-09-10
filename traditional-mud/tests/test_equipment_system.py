from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.troll_raid_opening as troll_raid
from mud.database import Database
from mud.equipment_system import (
    EARLY_EQUIPMENT_ITEMS,
    EQUIPMENT_REWARDS,
    EQUIPMENT_SLOTS,
    LIVE_EQUIPMENT_RULES,
    _bootstrap_equipment,
    _equip,
    _unequip,
    apply_equipment_to_combatant,
    claim_new_equipment_rewards,
    clear_equipped_slot,
    equipped_item_keys,
    equipment_totals,
    install_equipment_content,
    normalize_slot,
    set_equipped_item,
)
from mud.mechanics import CombatantState
from mud.stats import CharacterStats


class DummyTelnet:
    gmcp_enabled = False

    async def send_gmcp(self, *_args, **_kwargs):
        return False


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.active_enemy = None
        self.outputs: list[str] = []
        self.telnet = DummyTelnet()
        base = character.stats
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "",
            current_hp=base.maximum_hp(25),
            max_hp=base.maximum_hp(25),
            current_mana=base.maximum_mana(20),
            max_mana=base.maximum_mana(20),
            auto_attack_interval=2.5,
            stats=base,
            armor_class=0,
        )

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None


class EquipmentSystemTests(unittest.TestCase):
    def setUp(self):
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        install_equipment_content()

    def tearDown(self):
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)

    def _session(
        self,
        name: str,
        race: str = "human",
        character_class: str = "wizard",
        stats: CharacterStats | None = None,
    ):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "equipment.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            race,
            character_class,
            stats or CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        return temp, database, LiveLikeSession(database, character)

    def test_live_rules_are_universal_stat_first_and_persistent(self):
        self.assertTrue(LIVE_EQUIPMENT_RULES.universal_race_access)
        self.assertTrue(LIVE_EQUIPMENT_RULES.universal_class_access)
        self.assertTrue(LIVE_EQUIPMENT_RULES.ordinary_gear_is_stat_only)
        self.assertTrue(LIVE_EQUIPMENT_RULES.special_effects_reserved_for_rare_endgame_gear)
        self.assertTrue(LIVE_EQUIPMENT_RULES.equipment_persists_between_sessions)

    def test_fixed_slot_roster_is_exactly_the_first_pass_we_defined(self):
        self.assertEqual(
            EQUIPMENT_SLOTS,
            ("head", "chest", "legs", "feet", "hands", "main_hand", "off_hand"),
        )
        self.assertEqual(normalize_slot("body"), "chest")
        self.assertEqual(normalize_slot("weapon"), "main_hand")
        self.assertEqual(normalize_slot("main hand"), "main_hand")
        self.assertEqual(normalize_slot("shield"), "off_hand")

    def test_new_authored_gear_covers_every_slot_and_has_no_scripted_effects(self):
        slots = {normalize_slot(item.equipment.slot) for item in EARLY_EQUIPMENT_ITEMS if item.equipment}
        self.assertEqual(slots, set(EQUIPMENT_SLOTS))
        for item in EARLY_EQUIPMENT_ITEMS:
            self.assertIsNotNone(item.equipment)
            assert item.equipment is not None
            self.assertFalse(item.equipment.scripted_effects)

    def test_live_catalog_strips_race_and_class_restrictions(self):
        harness = crafting.ITEMS_BY_KEY["brute_training_harness"]
        self.assertIsNotNone(harness.equipment)
        assert harness.equipment is not None
        self.assertEqual(harness.equipment.allowed_races, frozenset())
        self.assertEqual(harness.equipment.allowed_classes, frozenset())

    def test_equipped_items_persist_in_sqlite(self):
        temp, database, session = self._session("Persist")
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, "forest_greenway_hood", 1)
        set_equipped_item(database, session.character.id, "head", "forest_greenway_hood")

        first = equipped_item_keys(database, session.character.id)
        self.assertEqual(first["head"], "forest_greenway_hood")

        # New Database object, same SQLite file: equipment is not session-only state.
        reopened = Database(database.path)
        second = equipped_item_keys(reopened, session.character.id)
        self.assertEqual(second["head"], "forest_greenway_hood")

    def test_equipment_stats_feed_live_combatant_and_unequip_reverses_them(self):
        temp, database, session = self._session("Numbers")
        self.addCleanup(temp.cleanup)
        base_hp = session.combatant.max_hp
        database.add_item(session.character.id, "troll_camp_hide_vest", 1)
        database.add_item(session.character.id, "human_sootstep_boots", 1)
        set_equipped_item(database, session.character.id, "chest", "troll_camp_hide_vest")
        set_equipped_item(database, session.character.id, "feet", "human_sootstep_boots")

        apply_equipment_to_combatant(session)
        self.assertEqual(session.combatant.armor_class, 3)
        self.assertEqual(session.combatant.stats.hp, session.character.hp_stat + 2)
        self.assertEqual(session.combatant.stats.grace, session.character.grace + 1)
        self.assertEqual(session.combatant.max_hp, base_hp + 2)

        clear_equipped_slot(database, session.character.id, "chest")
        clear_equipped_slot(database, session.character.id, "feet")
        apply_equipment_to_combatant(session)
        self.assertEqual(session.combatant.armor_class, 0)
        self.assertEqual(session.combatant.stats, session.character.stats)
        self.assertEqual(session.combatant.max_hp, base_hp)

    def test_brute_starter_harness_and_weapon_auto_equip_but_are_not_restrictions(self):
        temp, database, session = self._session("BruteStart", race="goblin", character_class="brute")
        self.addCleanup(temp.cleanup)
        _bootstrap_equipment(session)
        equipped = equipped_item_keys(database, session.character.id)
        self.assertEqual(equipped["main_hand"], "starter_weapon")
        self.assertEqual(equipped["chest"], "brute_training_harness")

        apply_equipment_to_combatant(session)
        self.assertEqual(session.combatant.armor_class, 8)

        # A non-Brute can still wear that exact harness if they acquire one.
        temp2, database2, wizard = self._session("WizardHarness", race="forest_elf", character_class="wizard")
        self.addCleanup(temp2.cleanup)
        database2.add_item(wizard.character.id, "brute_training_harness", 1)
        asyncio.run(_equip(wizard, "brute training harness"))
        self.assertEqual(equipped_item_keys(database2, wizard.character.id)["chest"], "brute_training_harness")
        self.assertEqual(wizard.combatant.armor_class, 8)

    def test_equipping_cross_culture_gear_is_allowed_and_updates_stats(self):
        temp, database, session = self._session("CrossWear", race="human", character_class="priest")
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, "goblin_reedfen_patchvest", 1)
        asyncio.run(_equip(session, "reedfen patchvest"))
        equipped = equipped_item_keys(database, session.character.id)
        self.assertEqual(equipped["chest"], "goblin_reedfen_patchvest")
        self.assertEqual(session.combatant.armor_class, 2)
        self.assertIn("equip", "".join(session.outputs).lower())

        asyncio.run(_unequip(session, "chest"))
        self.assertNotIn("chest", equipped_item_keys(database, session.character.id))
        self.assertEqual(session.combatant.armor_class, 0)

    def test_quest_rewards_are_catchup_safe_and_never_duplicate(self):
        temp, database, session = self._session("HumanReward")
        self.addCleanup(temp.cleanup)
        database.start_quest(session.character.id, "human_combat_training", "complete")
        database.complete_quest(session.character.id, "human_combat_training")

        claimed = claim_new_equipment_rewards(session)
        self.assertEqual([reward.item_key for reward in claimed], ["human_blackwall_drill_blade"])
        self.assertEqual(database.item_quantity(session.character.id, "human_blackwall_drill_blade"), 1)

        claimed_again = claim_new_equipment_rewards(session)
        self.assertEqual(claimed_again, ())
        self.assertEqual(database.item_quantity(session.character.id, "human_blackwall_drill_blade"), 1)

    def test_troll_first_duty_choice_produces_different_equipment_echo(self):
        temp, database, tracker = self._session("Tracker", race="troll", character_class="druid")
        self.addCleanup(temp.cleanup)
        database.grant_flag(tracker.character.id, "troll_first_duty_track_complete")
        track_claims = claim_new_equipment_rewards(tracker)
        self.assertIn("troll_trail_legwraps", {reward.item_key for reward in track_claims})
        self.assertEqual(database.item_quantity(tracker.character.id, "troll_camp_hide_vest"), 0)

        temp2, database2, camp = self._session("Camper", race="troll", character_class="wizard")
        self.addCleanup(temp2.cleanup)
        database2.grant_flag(camp.character.id, "troll_first_duty_camp_complete")
        camp_claims = claim_new_equipment_rewards(camp)
        self.assertIn("troll_camp_hide_vest", {reward.item_key for reward in camp_claims})
        self.assertEqual(database2.item_quantity(camp.character.id, "troll_trail_legwraps"), 0)

    def test_troll_raid_spear_becomes_universal_stat_weapon_and_auto_wields_during_tutorial(self):
        troll_raid.install_troll_raid_content()
        install_equipment_content()
        spear = crafting.ITEMS_BY_KEY["frostroot_notched_spear"]
        self.assertIsNotNone(spear.equipment)
        assert spear.equipment is not None
        self.assertEqual(spear.equipment.allowed_races, frozenset())
        self.assertEqual(spear.equipment.allowed_classes, frozenset())
        self.assertEqual(spear.equipment.stat_bonuses.might, 1)

        temp, database, session = self._session("RaidSpear", race="troll", character_class="necromancer")
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, "frostroot_notched_spear", 1)
        database.grant_flag(session.character.id, "troll_raid_weapon_taken")
        _bootstrap_equipment(session)
        self.assertEqual(equipped_item_keys(database, session.character.id)["main_hand"], "frostroot_notched_spear")
        apply_equipment_to_combatant(session)
        self.assertEqual(session.combatant.stats.might, session.character.might + 1)

    def test_reward_table_spreads_gear_across_authored_races(self):
        races = {reward.race_key for reward in EQUIPMENT_REWARDS}
        self.assertTrue({"human", "forest_elf", "dwarf", "goblin", "troll", "sporekin"}.issubset(races))

    def test_equipment_totals_only_count_worn_items_not_everything_in_bag(self):
        temp, database, session = self._session("BagVsWorn")
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, "dwarf_pressure_gauntlets", 1)
        database.add_item(session.character.id, "dwarf_chainmark_workboots", 1)
        set_equipped_item(database, session.character.id, "hands", "dwarf_pressure_gauntlets")
        bonus, ac = equipment_totals(database, session.character.id)
        self.assertEqual(ac, 1)
        self.assertEqual(bonus.might, 1)
        self.assertEqual(bonus.hp, 0)


if __name__ == "__main__":
    unittest.main()
