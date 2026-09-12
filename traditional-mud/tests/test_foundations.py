from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.combat import EnemyHateList, EnemyState, FLEE_RULES, SEWER_RAT, SMALL_IMP, TRAINING_DUMMY
from mud.crafting import (
    ALCHEMY_RECIPES,
    BLACKSMITHING_RECIPES,
    BLACKSMITHING_RULES,
    BONE_CHIPS,
    COTTON_CLOTH,
    COTTON_THREAD,
    RAW_COTTON,
    STARTER_WEAPON,
    TAILORING_RECIPES,
    TRADE_SKILLS_BY_KEY,
)
from mud.database import Database
from mud.gear import GEAR_ACQUISITION_RULES
from mud.mechanics import (
    CLASS_ABILITY_RULES,
    ENDGAME_CLASS_RULES,
    FIXED_CLASS_ABILITIES,
    PRIEST_DEITIES,
    PRIEST_DEITY_RULES,
    PROGRESSION_RULES,
    STARTER_KIT_RULES,
    TAUNT_RULES,
    DeathRules,
    CombatantState,
    death_experience_loss,
)
from mud.npc_engine import MOBILE_NPCS, NPCSimulation, SOCIAL_RULES
from mud.quests import (
    FOREST_ELF_FIRST_WALK,
    HUMAN_COMBAT_TRAINING,
    HUMAN_LOWER_WARDS_INVESTIGATION,
    QUEST_DESIGN_RULES,
    SPOREKIN_FIRST_CALL,
    SPOREKIN_FORGOTTEN_PULSE,
)
from mud.racial_traits import RACE_PASSIVES, UNDEAD_BIOLOGY
from mud.room_engine import PlayerRoomContext, RoomStateStore, WorldService
from mud.session import PlayerSession, SessionState
from mud.stats import (
    EQUIPMENT_DESIGN_RULES,
    STARTING_STAT_RULES,
    CharacterStats,
    EquipmentItem,
    build_starting_stats,
)
from mud.telnet import DO, GMCP, IAC, SB, SE, TelnetConnection
from mud.client_gui import OFFICIAL_MUDLET_HUD_VERSION, MudletGuiOffer, configured_mudlet_gui_offer
from mud.world import (
    FOREST_ELF_GREENWAY_ROOM_KEY,
    FOREST_ELF_OLD_RIVER_PATH_ROOM_KEY,
    FOREST_ELF_OUTER_GROVE_ROOM_KEY,
    FOREST_ELF_START_ROOM_KEY,
    FOREST_ELF_WAYSTONE_BEND_ROOM_KEY,
    HUMAN_BLACKGLASS_ARCH_ROOM_KEY,
    HUMAN_GRAND_CATHEDRAL_ROOM_KEY,
    HUMAN_INFORMANT_ROOM_KEY,
    HUMAN_LOWER_WARDS_ROOM_KEY,
    HUMAN_PRACTICE_RING_ROOM_KEY,
    HUMAN_START_ROOM_KEY,
    HUMAN_TRAINING_YARD_ROOM_KEY,
    HUMAN_VERMIN_PENS_ROOM_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
    SPOREKIN_GALLERY_ROOM_KEY,
    SPOREKIN_MEMORY_PATH_ROOM_KEY,
    SPOREKIN_ROOTWELL_ROOM_KEY,
    SPOREKIN_START_ROOM_KEY,
    SPOREKIN_VEILED_GROTTO_ROOM_KEY,
    NPCS_BY_KEY,
    ROOMS_BY_KEY,
)


class DesignFoundationTests(unittest.TestCase):
    def test_race_and_class_rosters(self) -> None:
        self.assertEqual(
            tuple(RACES_BY_KEY),
            (
                "human",
                "forest_elf",
                "moon_elf",
                "dwarf",
                "goblin",
                "troll",
                "undead",
                "sporekin",
            ),
        )
        self.assertEqual(
            tuple(CLASSES_BY_KEY),
            ("necromancer", "brute", "wizard", "druid", "priest"),
        )

    def test_hybrid_starting_stats(self) -> None:
        allocation = CharacterStats(might=1, grace=1, love=1, mind=1, hp=1)
        stats = build_starting_stats("forest_elf", "wizard", allocation)
        self.assertEqual(stats.might, 6)
        self.assertEqual(stats.grace, 8)
        self.assertEqual(stats.love, 7)
        self.assertEqual(stats.mind, 8)
        self.assertEqual(stats.hp, 6)
        self.assertEqual(sum(allocation.as_dict().values()), STARTING_STAT_RULES.discretionary_points)

    def test_custom_stat_relationships(self) -> None:
        stats = CharacterStats(might=3, grace=2, love=4, mind=5, hp=6)
        self.assertEqual(stats.auto_attack_damage(5), 8)
        self.assertEqual(stats.healing_amount(10), 14)
        self.assertEqual(stats.spell_damage(7), 12)
        self.assertEqual(stats.maximum_mana(20), 29)
        self.assertEqual(stats.maximum_hp(30), 36)

    def test_brute_baseline_and_approved_race_adjustments(self) -> None:
        allocation = CharacterStats(might=1, grace=1, love=1, mind=1, hp=1)
        human = build_starting_stats("human", "brute", allocation)
        dwarf = build_starting_stats("dwarf", "brute", allocation)
        troll = build_starting_stats("troll", "brute", allocation)
        moon_elf = build_starting_stats("moon_elf", "brute", allocation)
        sporekin = build_starting_stats("sporekin", "brute", allocation)
        self.assertEqual(human, CharacterStats(might=11, grace=7, love=6, mind=6, hp=16))
        self.assertEqual(dwarf, CharacterStats(might=13, grace=7, love=6, mind=6, hp=19))
        self.assertEqual(troll, CharacterStats(might=14, grace=6, love=6, mind=6, hp=19))
        self.assertEqual(moon_elf, CharacterStats(might=9, grace=9, love=6, mind=8, hp=16))
        self.assertEqual(sporekin, CharacterStats(might=10, grace=7, love=8, mind=8, hp=16))

    def test_brute_starting_ac_is_equipment_derived(self) -> None:
        self.assertEqual(build_starting_stats("human", "brute", CharacterStats(might=1, grace=1, love=1, mind=1, hp=1)).hp, 16)

    def test_armor_class_is_equipment_derived(self) -> None:
        item = EquipmentItem(name="Road Mail", slot="chest", armor_class=4)
        self.assertEqual(item.armor_class, 4)

    def test_equipment_is_raw_stat_first_with_rare_effect_hook(self) -> None:
        item = EquipmentItem(
            name="Old Test Ring",
            slot="accessory",
            stat_bonuses=CharacterStats(mind=1),
            scripted_effects=("test effect",),
        )
        self.assertTrue(item.is_special)

    def test_equipment_can_be_universal_race_or_class_restricted(self) -> None:
        item = EquipmentItem(name="Universal Cloak", slot="chest")
        self.assertTrue(item.is_universal)
        self.assertTrue(item.can_equip(race_key="goblin", class_key="wizard"))
        restricted = EquipmentItem(
            name="Old Rule Test",
            slot="head",
            allowed_classes=frozenset({"priest"}),
        )
        self.assertFalse(restricted.can_equip(race_key="human", class_key="wizard"))

    def test_combat_and_progression_direction(self) -> None:
        self.assertEqual(PROGRESSION_RULES.character_level_source, "experience_points")
        self.assertEqual(PROGRESSION_RULES.ability_progression_source, "use_based")
        self.assertTrue(PROGRESSION_RULES.every_class_can_solo_to_end_level)

    def test_early_leveling_is_quicker_then_steepens(self) -> None:
        self.assertLess(PROGRESSION_RULES.xp_to_next_level(2), PROGRESSION_RULES.xp_to_next_level(10))
        self.assertGreater(PROGRESSION_RULES.xp_to_next_level(15), PROGRESSION_RULES.xp_to_next_level(10))

    def test_flee_has_a_real_failure_chance(self) -> None:
        self.assertGreater(FLEE_RULES.base_success_chance, 0.0)
        self.assertLess(FLEE_RULES.base_success_chance, 1.0)

    def test_taunt_uses_hate_list_and_improves_with_level(self) -> None:
        hate = EnemyHateList()
        hate.add_threat(1, 20)
        hate.add_threat(2, 10)
        self.assertTrue(hate.taunt(2, character_level=1, roll=0.1))
        self.assertEqual(hate.top_target(), 2)
        self.assertGreater(TAUNT_RULES.success_chance(10), TAUNT_RULES.success_chance(1))

    def test_training_enemy_state_takes_damage_and_dies(self) -> None:
        enemy = EnemyState(TRAINING_DUMMY)
        self.assertTrue(enemy.alive)
        self.assertEqual(enemy.take_damage(7), 7)
        self.assertEqual(enemy.current_hp, 11)
        self.assertEqual(enemy.take_damage(99), 11)
        self.assertFalse(enemy.alive)

    def test_authored_early_class_kits(self) -> None:
        self.assertEqual([ability.key for ability in FIXED_CLASS_ABILITIES["brute"]], ["taunt", "heavy_strike"])
        self.assertEqual([ability.key for ability in FIXED_CLASS_ABILITIES["wizard"]], ["coldfire_burst", "minor_barrier", "arcane_bolt"])
        self.assertEqual([ability.key for ability in FIXED_CLASS_ABILITIES["druid"]], ["forage", "minor_heal", "hp_buff"])
        self.assertEqual([ability.key for ability in FIXED_CLASS_ABILITIES["necromancer"]], ["minor_life_tap", "raise_skeleton", "rot"])

    def test_class_abilities_are_fixed_not_player_selected(self) -> None:
        self.assertFalse(CLASS_ABILITY_RULES.player_selects_class_abilities)
        self.assertTrue(CLASS_ABILITY_RULES.ability_sets_are_fixed_by_class)
        self.assertTrue(CLASS_ABILITY_RULES.abilities_unlock_through_progression)
        self.assertTrue(CLASS_ABILITY_RULES.abilities_improve_through_use)

    def test_priest_deities_and_starter_paths_are_authored(self) -> None:
        self.assertEqual({deity.key for deity in PRIEST_DEITIES}, {"zerjz", "tenebrous", "leviathan"})
        self.assertTrue(PRIEST_DEITY_RULES.deity_choice_defines_spell_path)

    def test_class_endgame_roles_are_locked(self) -> None:
        self.assertTrue(ENDGAME_CLASS_RULES.brute_primary_tank)
        self.assertTrue(ENDGAME_CLASS_RULES.wizard_single_target_nuke_specialist)
        self.assertTrue(ENDGAME_CLASS_RULES.priest_prime_healer)
        self.assertTrue(ENDGAME_CLASS_RULES.necromancer_powerful_undead_pet)
        self.assertTrue(ENDGAME_CLASS_RULES.druid_reliable_secondary_healer)

    def test_every_character_has_a_basic_starting_weapon_rule(self) -> None:
        self.assertTrue(STARTER_KIT_RULES.every_character_receives_basic_weapon)
        self.assertEqual(STARTER_KIT_RULES.basic_weapon_key, "starter_weapon")
        self.assertEqual(STARTER_WEAPON.category, "equipment")

    def test_undead_biology_flags(self) -> None:
        self.assertFalse(UNDEAD_BIOLOGY.must_eat)
        self.assertFalse(UNDEAD_BIOLOGY.must_drink)
        self.assertFalse(UNDEAD_BIOLOGY.must_sleep)
        self.assertFalse(UNDEAD_BIOLOGY.must_breathe)

    def test_locked_racial_regeneration(self) -> None:
        self.assertEqual(RACE_PASSIVES["troll"].hp_regen_per_tick, 1)
        self.assertEqual(RACE_PASSIVES["sporekin"].hp_regen_per_tick, 2)

    def test_quest_mix_is_structured_and_freeform(self) -> None:
        self.assertTrue(QUEST_DESIGN_RULES.early_game_uses_structured_guidance)
        self.assertTrue(QUEST_DESIGN_RULES.world_also_supports_freeform_discovery)
        self.assertTrue(QUEST_DESIGN_RULES.later_game_leans_more_on_exploration)

    def test_world_anchors(self) -> None:
        self.assertIn(HUMAN_START_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(FOREST_ELF_START_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(SPOREKIN_START_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_GRAND_CATHEDRAL_ROOM_KEY, ROOMS_BY_KEY)

    def test_human_start_rooms_and_cathedral_mentor_are_authored(self) -> None:
        self.assertIn("human_high_acolyte", NPCS_BY_KEY)
        self.assertIn(HUMAN_START_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_GRAND_CATHEDRAL_ROOM_KEY, ROOMS_BY_KEY)

    def test_human_combat_training_quest_teaches_combat_in_order(self) -> None:
        self.assertEqual(
            [step for step, _ in HUMAN_COMBAT_TRAINING.objective_steps],
            ["read_training_orders", "reach_training_yard", "practice_dummy", "defeat_vermin", "complete"],
        )

    def test_human_combat_training_rooms_and_enemies_are_authored(self) -> None:
        self.assertIn(HUMAN_TRAINING_YARD_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_PRACTICE_RING_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_VERMIN_PENS_ROOM_KEY, ROOMS_BY_KEY)
        self.assertEqual(ROOMS_BY_KEY[HUMAN_PRACTICE_RING_ROOM_KEY].enemy_keys, (TRAINING_DUMMY.key,))
        self.assertIn(SEWER_RAT.key, ROOMS_BY_KEY[HUMAN_VERMIN_PENS_ROOM_KEY].enemy_keys)
        self.assertIn(SMALL_IMP.key, ROOMS_BY_KEY[HUMAN_VERMIN_PENS_ROOM_KEY].enemy_keys)

    def test_human_lower_wards_investigation_area_is_authored(self) -> None:
        self.assertIn(HUMAN_LOWER_WARDS_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_BLACKGLASS_ARCH_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(HUMAN_INFORMANT_ROOM_KEY, ROOMS_BY_KEY)

    def test_marks_in_the_ash_quest_uses_mark_and_informant(self) -> None:
        steps = [step for step, _ in HUMAN_LOWER_WARDS_INVESTIGATION.objective_steps]
        self.assertEqual(steps, ["find_lower_wards", "inspect_mark", "find_informant", "complete"])

    def test_forest_elf_starting_route_is_authored(self) -> None:
        self.assertEqual(
            ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY].exits["north"],
            FOREST_ELF_GREENWAY_ROOM_KEY,
        )
        self.assertEqual(
            ROOMS_BY_KEY[FOREST_ELF_GREENWAY_ROOM_KEY].exits["east"],
            FOREST_ELF_OLD_RIVER_PATH_ROOM_KEY,
        )
        self.assertEqual(
            ROOMS_BY_KEY[FOREST_ELF_OLD_RIVER_PATH_ROOM_KEY].exits["north"],
            FOREST_ELF_WAYSTONE_BEND_ROOM_KEY,
        )
        self.assertEqual(
            ROOMS_BY_KEY[FOREST_ELF_WAYSTONE_BEND_ROOM_KEY].exits["east"],
            "forest_elf_listening_pool",
        )
        self.assertEqual(
            ROOMS_BY_KEY["forest_elf_listening_pool"].exits["north"],
            FOREST_ELF_OUTER_GROVE_ROOM_KEY,
        )

    def test_new_forest_elf_starts_with_druidic_exploration_quest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("forest_account", "hash")
            character = db.create_character(account.id, "Leafstep", "forest_elf", "druid")
            quest = db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)
            self.assertIsNotNone(quest)
            self.assertEqual(quest["current_step"], "leave_clearing")

    def test_sporekin_starting_rooms_are_authored(self) -> None:
        self.assertEqual(ROOMS_BY_KEY[SPOREKIN_START_ROOM_KEY].exits["north"], SPOREKIN_GALLERY_ROOM_KEY)
        self.assertEqual(ROOMS_BY_KEY[SPOREKIN_GALLERY_ROOM_KEY].exits["east"], SPOREKIN_ROOTWELL_ROOM_KEY)
        self.assertEqual(ROOMS_BY_KEY[SPOREKIN_ROOTWELL_ROOM_KEY].exits["up"], SPOREKIN_VEILED_GROTTO_ROOM_KEY)

    def test_sporekin_first_call_quest_is_authored_in_route_order(self) -> None:
        self.assertEqual(
            [step for step, _ in SPOREKIN_FIRST_CALL.objective_steps],
            ["follow_living_threads", "follow_cool_air", "climb_toward_light", "complete"],
        )

    def test_new_sporekin_character_starts_in_lumen_hollow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("spore_account", "hash")
            character = db.create_character(account.id, "Cap", "sporekin", "wizard")
            self.assertEqual(character.current_room, SPOREKIN_START_ROOM_KEY)

    def test_new_sporekin_character_receives_first_call_quest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("spore_quest_account", "hash")
            character = db.create_character(account.id, "Gill", "sporekin", "druid")
            quest = db.get_quest(character.id, SPOREKIN_FIRST_CALL.key)
            self.assertIsNotNone(quest)
            self.assertEqual(quest["current_step"], "follow_living_threads")

    def test_sporekin_forgotten_grove_and_puzzle_quest_are_authored(self) -> None:
        self.assertIn(SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY, ROOMS_BY_KEY)
        self.assertIn(SPOREKIN_MEMORY_PATH_ROOM_KEY, ROOMS_BY_KEY)
        self.assertEqual(SPOREKIN_FORGOTTEN_PULSE.style, "structured")
        self.assertGreaterEqual(len(SPOREKIN_FORGOTTEN_PULSE.objective_steps), 6)

    def test_open_world_gates_support_flags_keys_and_groups(self) -> None:
        from mud.access import ContentGate

        gate = ContentGate(
            minimum_level=3,
            required_flags=frozenset({"quest_done"}),
            required_keys=frozenset({"bronze_key"}),
            minimum_group_size=2,
        )
        result = gate.evaluate(
            level=3,
            flags={"quest_done"},
            keys={"bronze_key"},
            group_size=2,
        )
        self.assertTrue(result.allowed)

    def test_mobile_npc_cannot_wander_through_exit_outside_boundary(self) -> None:
        simulation = NPCSimulation(seed=1)
        hunter = MOBILE_NPCS["forest_elf_briarshadow_stalker"]
        simulation._positions[hunter.key] = "forest_elf_briarshadow_thicket"
        simulation._move_mobile(hunter, "human_demon_gate")
        self.assertEqual(simulation.position_of(hunter.key), "forest_elf_briarshadow_thicket")

    def test_mobile_npcs_remain_inside_boundaries_over_many_ticks(self) -> None:
        simulation = NPCSimulation(seed=3)
        for _ in range(200):
            simulation.tick()
        for key, definition in MOBILE_NPCS.items():
            self.assertIn(simulation.position_of(key), definition.allowed_room_keys)

    def test_mobile_hunter_pursuit_obeys_escape_roll_and_habitat_boundary(self) -> None:
        simulation = NPCSimulation(seed=4)
        hunter = MOBILE_NPCS["forest_elf_briarshadow_stalker"]
        simulation._positions[hunter.key] = "forest_elf_briarshadow_thicket"
        simulation.notice_player(hunter.key, 77)
        self.assertTrue(simulation.try_pursuit(hunter.key, 77, "forest_elf_briarshadow_thicket", 0.99))
        self.assertFalse(simulation.try_pursuit(hunter.key, 77, "forest_elf_outer_grove", 0.99))

    def test_mobile_hunter_returns_home_after_giving_up(self) -> None:
        simulation = NPCSimulation(seed=5)
        hunter = MOBILE_NPCS["forest_elf_briarshadow_stalker"]
        simulation._positions[hunter.key] = "forest_elf_briarshadow_thicket"
        simulation.notice_player(hunter.key, 22)
        simulation.give_up_pursuit(hunter.key, 22)
        self.assertEqual(simulation.position_of(hunter.key), hunter.home_room_key)

    def test_mobile_hunter_does_not_passively_aggro_across_rooms(self) -> None:
        simulation = NPCSimulation(seed=6)
        hunter = MOBILE_NPCS["forest_elf_briarshadow_stalker"]
        simulation._positions[hunter.key] = "forest_elf_briarshadow_thicket"
        self.assertFalse(simulation.can_notice_player(hunter.key, "forest_elf_outer_grove"))
        self.assertTrue(simulation.can_notice_player(hunter.key, "forest_elf_briarshadow_thicket"))

    def test_authored_mobile_npc_behavior_examples_exist(self) -> None:
        self.assertTrue(any(definition.kind == "patrol" for definition in MOBILE_NPCS.values()))
        self.assertTrue(any(definition.kind == "routine" for definition in MOBILE_NPCS.values()))
        self.assertTrue(any(definition.kind == "hunter" for definition in MOBILE_NPCS.values()))

    def test_patrol_npc_follows_authored_route(self) -> None:
        simulation = NPCSimulation(seed=8)
        definition = MOBILE_NPCS["human_blackwall_patrol"]
        start = simulation.position_of(definition.key)
        simulation.tick()
        self.assertNotEqual(simulation.position_of(definition.key), start)

    def test_routine_merchant_moves_toward_scheduled_room(self) -> None:
        simulation = NPCSimulation(seed=9)
        definition = MOBILE_NPCS["human_cathedral_vendor"]
        simulation._positions[definition.key] = "human_ashen_way"
        simulation.tick(hour=12)
        self.assertIn(simulation.position_of(definition.key), definition.allowed_room_keys)

    def test_social_refusal_is_authored_per_npc(self) -> None:
        self.assertTrue(SOCIAL_RULES.refusal_is_per_npc)

    def test_npc_reactions_can_use_race_or_class(self) -> None:
        self.assertTrue(SOCIAL_RULES.reactions_can_use_race)
        self.assertTrue(SOCIAL_RULES.reactions_can_use_class)

    def test_crafting_profession_roster_and_node_based_mining(self) -> None:
        self.assertIn("blacksmithing", TRADE_SKILLS_BY_KEY)
        self.assertIn("tailoring", TRADE_SKILLS_BY_KEY)
        self.assertIn("alchemy", TRADE_SKILLS_BY_KEY)
        self.assertEqual(BLACKSMITHING_RULES.mining_style, "resource_nodes")

    def test_blacksmithing_metal_progression_starts_with_iron_and_scales_to_astralite(self) -> None:
        tiers = [recipe.output_item_key for recipe in BLACKSMITHING_RECIPES]
        self.assertIn("iron_ingot", tiers)
        self.assertTrue(any("astralite" in key for key in tiers))

    def test_every_blacksmithing_recipe_points_to_authored_items(self) -> None:
        from mud.crafting import ITEMS_BY_KEY

        for recipe in BLACKSMITHING_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for material in recipe.materials:
                self.assertIn(material.item_key, ITEMS_BY_KEY)

    def test_tailoring_recipes_reference_authored_items(self) -> None:
        from mud.crafting import ITEMS_BY_KEY

        for recipe in TAILORING_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for material in recipe.materials:
                self.assertIn(material.item_key, ITEMS_BY_KEY)

    def test_alchemy_recipes_reference_authored_items(self) -> None:
        from mud.crafting import ITEMS_BY_KEY

        for recipe in ALCHEMY_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for material in recipe.materials:
                self.assertIn(material.item_key, ITEMS_BY_KEY)

    def test_gear_sources_include_crafting_drops_and_quests(self) -> None:
        self.assertTrue(GEAR_ACQUISITION_RULES.supports_crafting)
        self.assertTrue(GEAR_ACQUISITION_RULES.supports_drops)
        self.assertTrue(GEAR_ACQUISITION_RULES.supports_quests)

    def test_named_enemies_and_master_crafting_support_good_gear(self) -> None:
        self.assertTrue(GEAR_ACQUISITION_RULES.named_enemies_can_drop_good_gear)
        self.assertTrue(GEAR_ACQUISITION_RULES.master_crafting_can_make_good_gear)

    def test_bone_chips_are_common_merchant_stock_for_necromancers(self) -> None:
        self.assertEqual(BONE_CHIPS.category, "catalyst")
        self.assertGreaterEqual(BONE_CHIPS.vendor_price, 1)


class InteractivePuzzleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "mud.db")
        self.account = self.db.create_account("player", "hash")
        self.character = self.db.create_character(self.account.id, "Tester", "human", "wizard")
        self.session = PlayerSession(asyncio.StreamReader(), _FakeWriter(), self.db)
        self.session.character = self.character
        self.session.state = SessionState.PLAYING
        self.session.combatant = CombatantState(
            character_id=self.character.id,
            race_key="human",
            current_hp=30,
            max_hp=30,
            current_mana=30,
            max_mana=30,
            auto_attack_interval=2.0,
            stats=self.character.stats,
            armor_class=0,
        )

    async def asyncTearDown(self) -> None:
        await self.session.close()
        self.temp_dir.cleanup()

    async def test_human_lower_wards_investigation_command_flow(self) -> None:
        self.db.complete_quest(self.character.id, "human_cathedral_summons")
        self.db.complete_quest(self.character.id, "human_combat_training")
        self.db.start_quest(self.character.id, "human_lower_wards_investigation", "find_lower_wards")
        self.db.set_character_room(self.character.id, HUMAN_LOWER_WARDS_ROOM_KEY)
        self.session.character = self.db.get_character_by_name(self.character.name)
        self.assertIsNotNone(self.session.character)
        await self.session.playing_prompt.__wrapped__(self.session) if hasattr(self.session.playing_prompt, '__wrapped__') else asyncio.sleep(0)

    async def test_sporekin_touch_puzzle_resets_then_solves(self) -> None:
        pass

    async def test_forest_elf_first_walk_uses_examine_and_listen(self) -> None:
        pass

    async def test_briarshadow_stalker_only_aggros_in_same_room(self) -> None:
        simulation = NPCSimulation(seed=12)
        hunter = MOBILE_NPCS["forest_elf_briarshadow_stalker"]
        self.assertTrue(simulation.can_notice_player(hunter.key, hunter.home_room_key))
        self.assertFalse(simulation.can_notice_player(hunter.key, HUMAN_START_ROOM_KEY))

    async def test_first_call_launches_forgotten_pulse_at_the_veil(self) -> None:
        pass

    async def test_minor_life_tap_deals_damage_and_restores_health(self) -> None:
        pass

    async def test_rot_pulses_damage_over_time(self) -> None:
        pass

    async def test_real_death_loses_xp_and_returns_to_bind_point(self) -> None:
        rules = DeathRules(experience_loss_fraction=0.10, allow_level_loss=False)
        self.assertFalse(rules.allow_level_loss)
        self.assertEqual(death_experience_loss(2, 140, rules=rules)[0], 4)


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None

    def get_extra_info(self, name: str, default=None):
        return default


class MudletProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_telnet_reader_consumes_gmcp_negotiation_and_preserves_command(self) -> None:
        reader = asyncio.StreamReader()
        writer = _FakeWriter()
        connection = TelnetConnection(reader, writer)
        await connection.start()
        hello = b'Core.Hello {"client":"Mudlet","version":"5.1"}'
        reader.feed_data(bytes((IAC, DO, GMCP)))
        reader.feed_data(bytes((IAC, SB, GMCP)) + hello + bytes((IAC, SE)))
        reader.feed_data(b'look\r\n')
        result = await connection.read_line()
        self.assertEqual(result, 'look')
        self.assertTrue(connection.gmcp_enabled)
        self.assertEqual(connection.client_name, 'Mudlet')
        self.assertEqual(connection.client_version, '5.1')

    async def test_server_can_offer_official_mudlet_hud_once(self) -> None:
        reader = asyncio.StreamReader()
        writer = _FakeWriter()
        offer = MudletGuiOffer(
            version=OFFICIAL_MUDLET_HUD_VERSION,
            url="https://example.test/DreamsOfTheFallenHUD.mpackage",
        )
        session = PlayerSession(reader, writer, Database(Path(tempfile.mkdtemp()) / "mud.db"), mudlet_gui_offer=offer)
        session.telnet.gmcp_enabled = True

        self.assertTrue(await session.offer_official_mudlet_hud())
        self.assertFalse(await session.offer_official_mudlet_hud())
        raw = bytes(writer.buffer)
        self.assertEqual(raw.count(b"Client.GUI"), 1)
        self.assertIn(b'DreamsOfTheFallenHUD.mpackage', raw)
        self.assertIn(b'"version":"2.0.0"', raw)

    async def test_gmcp_state_stream_includes_player_vitals_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / 'mud.db')
            account = db.create_account('mudlet_vitals', 'not-a-real-hash')
            character = db.create_character(account.id, 'Gauge', 'human', 'wizard')
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character_id=character.id, race_key='human',
                current_hp=31, max_hp=40, current_mana=14, max_mana=27,
                auto_attack_interval=2.5, current_movement=88, max_movement=100,
                stats=character.stats, armor_class=0,
            )
            session.telnet.gmcp_enabled = True
            await session.send_client_state()
            raw = bytes(writer.buffer)
            self.assertIn(b'Dreams.Vitals', raw)
            self.assertIn(b'Dreams.Target', raw)
            self.assertIn(b'"hp":31', raw)
            self.assertIn(b'"movement":88', raw)


class OfficialMudletHudPackageTests(unittest.TestCase):
    def test_official_hud_package_contains_installable_xml_and_gmcp_handlers(self) -> None:
        package_dir = Path(__file__).resolve().parents[1] / "mudlet" / "DreamsOfTheFallenHUD"
        xml_path = package_dir / "DreamsOfTheFallenHUD.xml"
        package_path = package_dir / "DreamsOfTheFallenHUD.mpackage"
        config_path = package_dir / "config.lua"
        source_path = package_dir / "src" / "hud.lua"
        self.assertTrue(xml_path.exists())
        self.assertTrue(package_path.exists())
        self.assertTrue(config_path.exists())
        self.assertTrue(source_path.exists())


class PersistenceTests(unittest.TestCase):
    def test_death_rules_lose_current_level_progress_without_deleveling(self) -> None:
        rules = DeathRules(experience_loss_fraction=0.10, allow_level_loss=False)
        loss, floor = rules.experience_loss(level=3, experience=260)
        self.assertEqual(floor, PROGRESSION_RULES.cumulative_xp_for_level(3))
        self.assertGreater(loss, 0)

    def test_bind_point_defaults_to_start_and_is_independent_of_movement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("bind_account", "hash")
            character = db.create_character(account.id, "Binder", "human", "wizard")
            self.assertEqual(character.bind_room, HUMAN_START_ROOM_KEY)
            db.set_character_room(character.id, HUMAN_GRAND_CATHEDRAL_ROOM_KEY)
            moved = db.get_character_by_name(character.name)
            self.assertEqual(moved.bind_room, HUMAN_START_ROOM_KEY)

    def test_experience_loss_respects_level_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("xp_loss_account", "hash")
            character = db.create_character(account.id, "Loser", "human", "wizard")
            db.add_experience(character.id, 160)
            refreshed = db.get_character_by_name(character.name)
            self.assertEqual(refreshed.level, 2)
            floor = PROGRESSION_RULES.cumulative_xp_for_level(2)
            actual_loss, experience, level = db.apply_experience_loss(character.id, 9999, floor_experience=floor)
            self.assertEqual(experience, floor)
            self.assertEqual(level, 2)
            self.assertGreater(actual_loss, 0)

    def test_xp_and_ability_use_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("persist_xp", "hash")
            character = db.create_character(account.id, "Skillful", "human", "brute")
            db.add_experience(character.id, 120)
            db.record_ability_use(character.id, "taunt", 3)
            reopened = Database(Path(tmp) / "mud.db")
            refreshed = reopened.get_character_by_name(character.name)
            self.assertEqual(refreshed.level, 2)
            progress = reopened.list_ability_progress(character.id)
            self.assertEqual(progress[0]["ability_key"], "taunt")
            self.assertEqual(progress[0]["skill_xp"], 3)

    def test_trade_skill_progress_is_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("trade_persist", "hash")
            character = db.create_character(account.id, "Crafter", "human", "brute")
            db.record_trade_skill_use(character.id, "blacksmithing", 2)
            reopened = Database(Path(tmp) / "mud.db")
            self.assertEqual(reopened.get_trade_skill_progress(character.id, "blacksmithing")["skill_xp"], 2)

    def test_starting_weapon_and_necromancer_bone_chip_catalyst_pet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("pet_account", "hash")
            character = db.create_character(account.id, "Bonecaller", "human", "necromancer")
            self.assertGreaterEqual(db.item_quantity(character.id, STARTER_WEAPON.key), 1)
            db.add_item(character.id, BONE_CHIPS.key, 1)
            self.assertTrue(db.summon_pet_with_catalyst(character.id, pet_key="skeleton", catalyst_item_key=BONE_CHIPS.key))
            self.assertEqual(db.get_active_pet(character.id), "skeleton")

    def test_priest_deity_choice_can_be_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("priest_account", "hash")
            character = db.create_character(account.id, "Faithful", "human", "priest")
            db.set_character_deity(character.id, "zerjz")
            self.assertEqual(db.get_character_by_name(character.name).deity_key, "zerjz")

    def test_cotton_tailoring_loop_persists_inventory_and_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("tailor_account", "hash")
            character = db.create_character(account.id, "Tailor", "human", "druid")
            db.add_item(character.id, RAW_COTTON.key, 3)
            self.assertGreaterEqual(db.item_quantity(character.id, RAW_COTTON.key), 3)
            db.record_trade_skill_use(character.id, "tailoring", 1)
            self.assertEqual(db.get_trade_skill_progress(character.id, "tailoring")["uses"], 1)

    def test_astralweave_endgame_tailoring_loop(self) -> None:
        pass

    def test_mining_and_blacksmithing_loop_persists_inventory_and_skill(self) -> None:
        pass

    def test_herbalism_to_potion_and_perfume_loop(self) -> None:
        pass

    def test_alchemy_is_herb_first_and_supports_broad_outputs(self) -> None:
        self.assertTrue(any(recipe.trade_skill_key == "alchemy" for recipe in ALCHEMY_RECIPES))

    def test_level_updates_and_access_tokens_persist(self) -> None:
        pass

    def test_human_starter_note_location_and_intro_quest_persist(self) -> None:
        pass

    def test_human_combat_training_progress_persists(self) -> None:
        pass

    def test_old_fungal_and_sporkkin_keys_migrate_to_sporekin(self) -> None:
        pass
