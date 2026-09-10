from __future__ import annotations

import os
import asyncio
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from mud.character_options import CLASSES, CLASSES_BY_KEY, RACES, RACES_BY_KEY
from mud.access import CharacterAccessState, ContentGate, WORLD_ACCESS_RULES
from mud.combat import ENEMIES_BY_KEY, EnemyHateList, EnemyState, FLEE_RULES
from mud.database import Database
from mud.crafting import (
    ALCHEMY_RECIPES,
    ALCHEMY_RECIPES_BY_KEY,
    BITTERROOT_CLUSTER,
    BLACKSMITHING_RECIPES,
    BLACKSMITHING_RECIPES_BY_KEY,
    ASTRAL_BLOOM,
    COTTON_PATCH,
    GATHERING_SKILLS_BY_KEY,
    GREENLEAF_PATCH,
    IRON_VEIN,
    ITEMS_BY_KEY,
    LAVENDER_PATCH,
    METAL_TIERS,
    RESOURCE_NODES_BY_KEY,
    PROFESSIONS,
    TAILORING_RECIPES,
    TAILORING_RECIPES_BY_KEY,
    TEXTILE_TIERS,
    ResourceNodeState,
    craft_recipe,
    gather_node,
    mine_node,
)
from mud.mechanics import (
    CLASS_ABILITY_RULES,
    COMBAT_RULES,
    ENDGAME_CLASS_RULES,
    FIXED_CLASS_ABILITIES,
    PRIEST_DEITIES,
    PRIEST_DEITIES_BY_KEY,
    PRIEST_DEITY_RULES,
    PROGRESSION_RULES,
    DEATH_RULES,
    STARTER_KIT_RULES,
    TAUNT_RULES,
    CombatantState,
    class_abilities_for_level,
    priest_abilities_for_level,
)
from mud.gear import (
    CRAFTING_PROGRESSION_RULES, GEAR_ACQUISITION_RULES, CraftingRecipe, GearSource,
    NamedEnemyLootEntry, can_equip_item,
)
from mud.stats import (
    BRUTE_STARTER_ARMOR, EQUIPMENT_DESIGN_RULES, STARTER_WEAPON, STARTING_STAT_RULES,
    CharacterStats, EquipmentItem, build_starting_stats, starting_armor_class,
    starting_stat_baseline, total_armor_class, total_equipment_stat_bonuses,
)
from mud.quests import (
    HUMAN_CATHEDRAL_SUMMONS, HUMAN_COMBAT_TRAINING, HUMAN_LOWER_WARDS_INVESTIGATION, FOREST_ELF_FIRST_WALK,
    SPOREKIN_FIRST_CALL, SPOREKIN_FORGOTTEN_PULSE, QUEST_DESIGN_RULES,
)
from mud.social import NpcSocialPolicy
from mud.world_data import REGIONS_BY_KEY, WORLD_NAME, WORLD_STRUCTURE
from mud.npcs import (
    AMBIENT_FOREST_ANIMALS, ASHEN_WAY_CURIO_PEDDLER, BEHAVIOR_HUNTER,
    BEHAVIOR_PATROL, BEHAVIOR_ROUTINE, BLACKWALL_GUARD, BRIARSHADOW_STALKER,
    MOBILE_NPC_DEFINITIONS, SILVERLEAF_HARE, MobileNpcManager,
)
from mud.session import WELCOME_BANNER, PlayerSession, SessionState
from mud.telnet import DO, GMCP, IAC, SB, SE, TelnetConnection
from mud.client_gui import (
    MudletGuiOffer,
    OFFICIAL_MUDLET_HUD_VERSION,
    OFFICIAL_MUDLET_HUD_URL,
    configured_mudlet_gui_offer,
)
from mud.merchants import ASHEN_WAY_CURIO_PEDDLER_MERCHANT, COMMON_MERCHANT_STOCK_BY_KEY
from mud.world import (
    HIGH_ACOLYTE,
    HUMAN_PRACTICE_RING_KEY,
    HUMAN_START_ROOM_KEY,
    HUMAN_TRAINING_YARD_KEY,
    HUMAN_VERMIN_PENS_KEY,
    HUMAN_SOOTSTAIRS_KEY,
    HUMAN_CINDER_LANE_KEY,
    HUMAN_BLACKGLASS_ARCH_KEY,
    HUMAN_LANTERN_COURT_KEY,
    LOWER_WARDS_INFORMANT,
    FOREST_ELF_START_ROOM_KEY,
    FOREST_ELF_OLD_RIVER_PATH_KEY,
    FOREST_ELF_WAYSTONE_BEND_KEY,
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_BRIARSHADOW_THICKET_KEY,
    SPOREKIN_START_ROOM_KEY,
    SPOREKIN_SURFACEWARD_ROOM_KEY,
    SPOREKIN_SURFACE_VERGE_ROOM_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
    SPOREKIN_MEMORY_PATH_ROOM_KEY,
    ROOMS_BY_KEY,
)


class DesignFoundationTests(unittest.TestCase):
    def test_startup_banner_uses_game_title_and_telnet_safe_width(self) -> None:
        self.assertIn("DREAMS OF THE FALLEN", WELCOME_BANNER)
        self.assertIn("ASTRALIS", WELCOME_BANNER)
        self.assertNotIn("TRADITIONAL MUD", WELCOME_BANNER)
        visible_lines = WELCOME_BANNER.replace("\r", "").split("\n")
        self.assertLessEqual(max(len(line) for line in visible_lines), 78)

    def test_race_and_class_rosters(self) -> None:
        self.assertEqual(len(RACES), 8)
        self.assertEqual(
            [race.name for race in RACES],
            [
                "Human",
                "Forest Elf",
                "Moon Elf",
                "Dwarf",
                "Goblin",
                "Troll",
                "Undead",
                "Sporekin",
            ],
        )
        self.assertEqual(
            [character_class.name for character_class in CLASSES],
            ["Brute", "Wizard", "Druid", "Priest", "Necromancer"],
        )

    def test_forest_elf_starting_route_is_authored(self) -> None:
        start = ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY]
        self.assertEqual(start.region_key, "great_elf_forest")
        self.assertIn("druidic_circle", start.tags)
        greenway = ROOMS_BY_KEY[start.exits["north"]]
        river = ROOMS_BY_KEY[greenway.exits["east"]]
        self.assertEqual(river.key, FOREST_ELF_OLD_RIVER_PATH_KEY)
        bend = ROOMS_BY_KEY[river.exits["north"]]
        self.assertEqual(bend.key, FOREST_ELF_WAYSTONE_BEND_KEY)
        pool = ROOMS_BY_KEY[bend.exits["east"]]
        self.assertEqual(pool.key, FOREST_ELF_LISTENING_POOL_KEY)
        outer = ROOMS_BY_KEY[pool.exits["north"]]
        self.assertEqual(outer.key, FOREST_ELF_OUTER_GROVE_KEY)
        self.assertIn("danger_hint", outer.tags)
        thicket = ROOMS_BY_KEY[outer.exits["north"]]
        self.assertEqual(thicket.key, FOREST_ELF_BRIARSHADOW_THICKET_KEY)
        self.assertIn("dangerous", thicket.tags)
        self.assertIn("tracks", thicket.tags)
        self.assertEqual(thicket.exits["south"], FOREST_ELF_OUTER_GROVE_KEY)
        self.assertEqual(thicket.enemy_keys, ())
        self.assertEqual(thicket.npc_keys, ())

    def test_mobile_forest_animals_have_explicit_room_boundaries(self) -> None:
        self.assertEqual(len(AMBIENT_FOREST_ANIMALS), 3)
        for definition in AMBIENT_FOREST_ANIMALS:
            self.assertIn(definition.spawn_room_key, definition.allowed_room_keys)
            self.assertEqual(definition.movement_pattern, "random")
            for room_key in definition.allowed_room_keys:
                self.assertIn(room_key, ROOMS_BY_KEY)

    def test_authored_mobile_npc_behavior_examples_exist(self) -> None:
        self.assertEqual(BLACKWALL_GUARD.behavior, BEHAVIOR_PATROL)
        self.assertTrue(BLACKWALL_GUARD.patrol_route)
        self.assertEqual(BRIARSHADOW_STALKER.behavior, BEHAVIOR_HUNTER)
        self.assertTrue(BRIARSHADOW_STALKER.aggressive)
        self.assertEqual(BRIARSHADOW_STALKER.aggro_radius, 0)
        self.assertEqual(ASHEN_WAY_CURIO_PEDDLER.behavior, BEHAVIOR_ROUTINE)
        self.assertGreaterEqual(len(ASHEN_WAY_CURIO_PEDDLER.routine_schedule), 3)
        for definition in (BLACKWALL_GUARD, BRIARSHADOW_STALKER, ASHEN_WAY_CURIO_PEDDLER):
            self.assertIn(definition.spawn_room_key, definition.allowed_room_keys)
            for room_key in definition.allowed_room_keys:
                self.assertIn(room_key, ROOMS_BY_KEY)

    def test_patrol_npc_follows_authored_route(self) -> None:
        class AlwaysMoveRng:
            def random(self) -> float:
                return 0.0

            def choice(self, values):
                return values[0]

        manager = MobileNpcManager((BLACKWALL_GUARD,))
        expected = [
            "human_outer_drill_road",
            HUMAN_TRAINING_YARD_KEY,
            "human_outer_drill_road",
            HUMAN_START_ROOM_KEY,
        ]
        actual = []
        for _ in range(4):
            movements = manager.tick(AlwaysMoveRng())
            self.assertEqual(len(movements), 1)
            self.assertEqual(movements[0].behavior, BEHAVIOR_PATROL)
            actual.append(movements[0].destination_room_key)
        self.assertEqual(actual, expected)

    def test_hunter_does_not_passively_aggro_across_rooms(self) -> None:
        class AlwaysMoveRng:
            def random(self) -> float:
                return 0.0

            def choice(self, values):
                return values[0]

        manager = MobileNpcManager((BRIARSHADOW_STALKER,))
        movements = manager.tick(
            AlwaysMoveRng(),
            player_room_keys=(FOREST_ELF_OUTER_GROVE_KEY,),
        )
        # The hunter may prowl naturally, but it does not acquire or pursue a
        # player merely because that player is in another room.
        if movements:
            self.assertEqual(movements[0].reason, "prowling")
        self.assertIsNone(manager.states[BRIARSHADOW_STALKER.key].engaged_character_id)

    def test_mobile_hunter_pursuit_obeys_escape_roll_and_habitat_boundary(self) -> None:
        class FollowRng:
            def random(self) -> float:
                return 0.0

        manager = MobileNpcManager((BRIARSHADOW_STALKER,))
        character_id = 77
        self.assertTrue(manager.engage(BRIARSHADOW_STALKER.key, character_id))

        # An already-engaged hunter can follow a fleeing player to the adjacent
        # Outer Grove because it is inside the authored habitat.
        movement = manager.attempt_pursuit_after_flee(
            BRIARSHADOW_STALKER.key,
            character_id,
            FOREST_ELF_OUTER_GROVE_KEY,
            FollowRng(),
        )
        self.assertIsNotNone(movement)
        assert movement is not None
        self.assertEqual(movement.reason, "pursuit")
        self.assertEqual(movement.destination_room_key, FOREST_ELF_OUTER_GROVE_KEY)

        # The Listening Pool is a valid player exit but outside the predator's
        # boundary. Pursuit must fail regardless of the favorable follow roll.
        movement = manager.attempt_pursuit_after_flee(
            BRIARSHADOW_STALKER.key,
            character_id,
            FOREST_ELF_LISTENING_POOL_KEY,
            FollowRng(),
        )
        self.assertIsNone(movement)
        state = manager.states[BRIARSHADOW_STALKER.key]
        self.assertEqual(state.current_room_key, FOREST_ELF_OUTER_GROVE_KEY)
        self.assertIsNone(state.engaged_character_id)
        self.assertTrue(state.returning_to_duty)

    def test_mobile_hunter_returns_home_after_giving_up(self) -> None:
        class AlwaysMoveRng:
            def random(self) -> float:
                return 0.0

            def choice(self, values):
                return values[0]

        manager = MobileNpcManager((BRIARSHADOW_STALKER,))
        state = manager.states[BRIARSHADOW_STALKER.key]
        state.current_room_key = FOREST_ELF_OUTER_GROVE_KEY
        state.engaged_character_id = 88
        manager.disengage(BRIARSHADOW_STALKER.key, 88)
        movement = manager.tick(AlwaysMoveRng())[0]
        self.assertEqual(movement.reason, "returning")
        self.assertEqual(movement.destination_room_key, FOREST_ELF_BRIARSHADOW_THICKET_KEY)

    def test_flee_has_a_real_failure_chance(self) -> None:
        self.assertTrue(FLEE_RULES.succeeds(0.10))
        self.assertTrue(FLEE_RULES.succeeds(FLEE_RULES.base_success_chance))
        self.assertFalse(FLEE_RULES.succeeds(0.99))
        self.assertGreater(FLEE_RULES.base_success_chance, 0.0)
        self.assertLess(FLEE_RULES.base_success_chance, 1.0)

    def test_routine_merchant_moves_toward_scheduled_room(self) -> None:
        class AlwaysMoveRng:
            def random(self) -> float:
                return 0.0

            def choice(self, values):
                return values[0]

        manager = MobileNpcManager((ASHEN_WAY_CURIO_PEDDLER,))
        # At 7 AM the peddler leaves Ashen Way for the Demon Gate.
        movement = manager.tick(AlwaysMoveRng(), hour=7)[0]
        self.assertEqual(movement.destination_room_key, HUMAN_START_ROOM_KEY)
        self.assertEqual(movement.behavior, BEHAVIOR_ROUTINE)

        # At 18:00 the target becomes Cathedral Square. From the gate the NPC
        # takes one legal step at a time through Ashen Way.
        movement = manager.tick(AlwaysMoveRng(), hour=18)[0]
        self.assertEqual(movement.destination_room_key, "human_ashen_way")
        movement = manager.tick(AlwaysMoveRng(), hour=18)[0]
        self.assertEqual(movement.destination_room_key, "human_cathedral_square")

    def test_mobile_npc_cannot_wander_through_exit_outside_boundary(self) -> None:
        class AlwaysMoveRng:
            def random(self) -> float:
                return 0.0

            def choice(self, values):
                return values[0]

        manager = MobileNpcManager((SILVERLEAF_HARE,))
        state = manager.states[SILVERLEAF_HARE.key]
        state.current_room_key = FOREST_ELF_LISTENING_POOL_KEY
        # Listening Pool has a north exit to Outer Grove, but the hare's
        # authored habitat ends at the pool. Only the westward move is legal.
        movements = manager.tick(AlwaysMoveRng())
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].destination_room_key, FOREST_ELF_WAYSTONE_BEND_KEY)
        self.assertNotEqual(movements[0].destination_room_key, FOREST_ELF_OUTER_GROVE_KEY)

    def test_mobile_npcs_remain_inside_boundaries_over_many_ticks(self) -> None:
        import random

        manager = MobileNpcManager()
        rng = random.Random(8675309)
        for _ in range(500):
            manager.tick(rng)
            for state in manager.states.values():
                self.assertIn(state.current_room_key, state.definition.allowed_room_keys)

    def test_briarshadow_thicket_is_first_empty_danger_room(self) -> None:
        outer = ROOMS_BY_KEY[FOREST_ELF_OUTER_GROVE_KEY]
        self.assertEqual(outer.exits["north"], FOREST_ELF_BRIARSHADOW_THICKET_KEY)
        thicket = ROOMS_BY_KEY[FOREST_ELF_BRIARSHADOW_THICKET_KEY]
        self.assertIn("dangerous", thicket.tags)
        self.assertIn("future_encounter", thicket.tags)
        self.assertEqual(thicket.npc_keys, ())
        self.assertEqual(thicket.enemy_keys, ())
        self.assertIn("fresh tracks", thicket.description.lower())

    def test_new_forest_elf_starts_with_druidic_exploration_quest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("elf_walk", "not-a-real-hash")
            character = db.create_character(account.id, "Fern", "forest_elf", "druid")
            self.assertEqual(character.current_room, FOREST_ELF_START_ROOM_KEY)
            quest = db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)
            assert quest is not None
            self.assertEqual(quest["status"], "active")
            self.assertEqual(quest["current_step"], "leave_clearing")
            self.assertEqual(
                [step for step, _ in FOREST_ELF_FIRST_WALK.objective_steps],
                ["leave_clearing", "follow_river", "study_waystone", "listen_pool", "reach_outer_grove", "complete"],
            )

    def test_locked_racial_regeneration(self) -> None:
        troll = CombatantState(1, "troll", 5, 20, 10, 10, 2.0)
        sporekin = CombatantState(2, "sporekin", 5, 20, 10, 10, 2.0)
        human = CombatantState(3, "human", 5, 20, 10, 10, 2.0)

        self.assertEqual(troll.apply_normal_regeneration(2), 3)
        self.assertEqual(sporekin.apply_normal_regeneration(2), 4)
        self.assertEqual(human.apply_normal_regeneration(2), 2)

    def test_sporekin_starting_rooms_are_authored(self) -> None:
        start = ROOMS_BY_KEY[SPOREKIN_START_ROOM_KEY]
        self.assertEqual(start.region_key, "sporekin_underways")
        self.assertIn("bioluminescent", start.tags)
        gallery = ROOMS_BY_KEY[start.exits["north"]]
        self.assertIn("shared_consciousness", gallery.tags)
        ascent = ROOMS_BY_KEY[gallery.exits["east"]]
        self.assertIn("up", ascent.exits)
        self.assertEqual(ascent.exits["up"], SPOREKIN_SURFACEWARD_ROOM_KEY)
        grotto = ROOMS_BY_KEY[SPOREKIN_SURFACEWARD_ROOM_KEY]
        self.assertEqual(grotto.exits["down"], ascent.key)
        self.assertIn("surface_edge", grotto.tags)

    def test_sporekin_forgotten_grove_and_puzzle_quest_are_authored(self) -> None:
        grotto = ROOMS_BY_KEY[SPOREKIN_SURFACEWARD_ROOM_KEY]
        self.assertEqual(grotto.exits["north"], SPOREKIN_SURFACE_VERGE_ROOM_KEY)
        verge = ROOMS_BY_KEY[SPOREKIN_SURFACE_VERGE_ROOM_KEY]
        self.assertEqual(verge.exits["east"], SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY)
        grove = ROOMS_BY_KEY[SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY]
        self.assertIn("puzzle", grove.tags)
        for color in ("blue", "amber", "violet", "ivory"):
            self.assertIn(color, grove.description.lower())
        self.assertNotIn("north", grove.exits)
        memory_path = ROOMS_BY_KEY[SPOREKIN_MEMORY_PATH_ROOM_KEY]
        self.assertEqual(memory_path.exits["south"], SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY)
        self.assertEqual(
            [step for step, _ in SPOREKIN_FORGOTTEN_PULSE.objective_steps],
            [
                "cross_veil", "find_grove", "study_ring", "touch_blue", "touch_amber",
                "touch_violet", "touch_ivory", "complete",
            ],
        )

    def test_new_sporekin_character_starts_in_lumen_hollow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("spore_start", "not-a-real-hash")
            character = db.create_character(account.id, "Glowcap", "sporekin", "druid")
            self.assertEqual(character.current_room, SPOREKIN_START_ROOM_KEY)
            loaded = db.get_character_by_name("Glowcap")
            assert loaded is not None
            self.assertEqual(loaded.current_room, SPOREKIN_START_ROOM_KEY)

    def test_sporekin_first_call_quest_is_authored_in_route_order(self) -> None:
        self.assertEqual(SPOREKIN_FIRST_CALL.style, "structured")
        self.assertEqual(
            [step for step, _ in SPOREKIN_FIRST_CALL.objective_steps],
            ["follow_living_threads", "follow_cool_air", "climb_toward_light", "complete"],
        )
        self.assertIn("mycelial", SPOREKIN_FIRST_CALL.objective_for_step("follow_living_threads").lower())
        self.assertIn("Rootwell", SPOREKIN_FIRST_CALL.objective_for_step("follow_cool_air"))

    def test_new_sporekin_character_receives_first_call_quest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("chorus_start", "not-a-real-hash")
            character = db.create_character(account.id, "Morrowcap", "sporekin", "wizard")
            quest = db.get_quest(character.id, SPOREKIN_FIRST_CALL.key)
            assert quest is not None
            self.assertEqual(quest["status"], "active")
            self.assertEqual(quest["current_step"], "follow_living_threads")
            db.advance_quest(character.id, SPOREKIN_FIRST_CALL.key, "follow_cool_air")
            db.advance_quest(character.id, SPOREKIN_FIRST_CALL.key, "climb_toward_light")
            db.set_character_room(character.id, SPOREKIN_SURFACEWARD_ROOM_KEY)
            db.complete_quest(character.id, SPOREKIN_FIRST_CALL.key)
            db.grant_flag(character.id, "sporekin_first_call_answered")
            loaded = db.get_character_by_name("Morrowcap")
            assert loaded is not None
            self.assertEqual(db.get_quest(loaded.id, SPOREKIN_FIRST_CALL.key)["status"], "completed")
            self.assertIn("sporekin_first_call_answered", db.list_flags(loaded.id))

    def test_human_combat_training_rooms_and_enemies_are_authored(self) -> None:
        gate = ROOMS_BY_KEY[HUMAN_START_ROOM_KEY]
        self.assertIn("south", gate.exits)
        road = ROOMS_BY_KEY[gate.exits["south"]]
        self.assertEqual(road.exits["west"], HUMAN_TRAINING_YARD_KEY)
        yard = ROOMS_BY_KEY[HUMAN_TRAINING_YARD_KEY]
        self.assertEqual(yard.exits["north"], HUMAN_PRACTICE_RING_KEY)
        self.assertEqual(yard.exits["south"], HUMAN_VERMIN_PENS_KEY)
        self.assertIn("training_dummy", ROOMS_BY_KEY[HUMAN_PRACTICE_RING_KEY].enemy_keys)
        self.assertIn("sewer_rat", ROOMS_BY_KEY[HUMAN_VERMIN_PENS_KEY].enemy_keys)
        self.assertIn("small_imp", ROOMS_BY_KEY[HUMAN_VERMIN_PENS_KEY].enemy_keys)
        self.assertFalse(ENEMIES_BY_KEY["training_dummy"].retaliates)
        self.assertTrue(ENEMIES_BY_KEY["sewer_rat"].retaliates)
        self.assertTrue(ENEMIES_BY_KEY["small_imp"].retaliates)

    def test_training_enemy_state_takes_damage_and_dies(self) -> None:
        enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
        self.assertTrue(enemy.alive)
        self.assertEqual(enemy.take_damage(7), 7)
        self.assertEqual(enemy.current_hp, 13)
        enemy.take_damage(99)
        self.assertFalse(enemy.alive)
        self.assertEqual(enemy.current_hp, 0)

    def test_human_combat_training_quest_teaches_combat_in_order(self) -> None:
        self.assertEqual(HUMAN_COMBAT_TRAINING.style, "structured")
        self.assertEqual(
            [step for step, _ in HUMAN_COMBAT_TRAINING.objective_steps],
            ["read_training_orders", "reach_training_yard", "practice_dummy", "defeat_vermin", "complete"],
        )
        self.assertIn("ATTACK DUMMY", HUMAN_COMBAT_TRAINING.objective_for_step("practice_dummy"))

    def test_undead_biology_flags(self) -> None:
        undead = RACES_BY_KEY["undead"]
        self.assertFalse(undead.needs_food)
        self.assertFalse(undead.needs_drink)
        self.assertFalse(undead.needs_sleep)
        self.assertFalse(undead.needs_breath)
        self.assertEqual(undead.poison_resistance, "reduced_effect")
        self.assertEqual(undead.disease_resistance, "reduced_effect")
        self.assertTrue(undead.normal_healing_magic)

    def test_world_anchors(self) -> None:
        self.assertEqual(WORLD_NAME, "Astralis")
        self.assertEqual(WORLD_STRUCTURE["continents"], "multiple")
        self.assertEqual(WORLD_STRUCTURE["separation"], "seas")
        self.assertIn("central_trade_city", REGIONS_BY_KEY)
        self.assertEqual(
            REGIONS_BY_KEY["human_kingdom"].adjacent_regions,
            ("dwarven_mountain_industry",),
        )


    def test_human_start_rooms_and_cathedral_mentor_are_authored(self) -> None:
        gate = ROOMS_BY_KEY[HUMAN_START_ROOM_KEY]
        self.assertEqual(gate.name, "The Demon Gate")
        self.assertIn("north", gate.exits)
        ashen = ROOMS_BY_KEY[gate.exits["north"]]
        square = ROOMS_BY_KEY[ashen.exits["north"]]
        cathedral = ROOMS_BY_KEY[square.exits["north"]]
        self.assertEqual(cathedral.name, "The Grand Cathedral")
        self.assertIn(HIGH_ACOLYTE.key, cathedral.npc_keys)
        self.assertIn("occult_hint", square.tags)
        self.assertEqual(HIGH_ACOLYTE.role, "enigmatic mentor and early quest guide")
        self.assertEqual(HUMAN_CATHEDRAL_SUMMONS.style, "structured")
        self.assertIn("High Acolyte", HUMAN_CATHEDRAL_SUMMONS.objective_for_step("find_cathedral") or "")

    def test_human_lower_wards_investigation_area_is_authored(self) -> None:
        ashen = ROOMS_BY_KEY["human_ashen_way"]
        self.assertEqual(ashen.exits["west"], HUMAN_SOOTSTAIRS_KEY)
        sootstairs = ROOMS_BY_KEY[HUMAN_SOOTSTAIRS_KEY]
        self.assertEqual(sootstairs.exits["down"], HUMAN_CINDER_LANE_KEY)
        lane = ROOMS_BY_KEY[HUMAN_CINDER_LANE_KEY]
        self.assertEqual(lane.exits["east"], HUMAN_BLACKGLASS_ARCH_KEY)
        self.assertEqual(lane.exits["south"], HUMAN_LANTERN_COURT_KEY)
        arch = ROOMS_BY_KEY[HUMAN_BLACKGLASS_ARCH_KEY]
        self.assertIn("strange_mark", arch.tags)
        court = ROOMS_BY_KEY[HUMAN_LANTERN_COURT_KEY]
        self.assertIn(LOWER_WARDS_INFORMANT.key, court.npc_keys)

    def test_marks_in_the_ash_quest_uses_mark_and_informant(self) -> None:
        self.assertEqual(HUMAN_LOWER_WARDS_INVESTIGATION.style, "structured")
        self.assertEqual(
            [step for step, _ in HUMAN_LOWER_WARDS_INVESTIGATION.objective_steps],
            ["find_lower_wards", "inspect_mark", "find_informant", "complete"],
        )
        self.assertIn("EXAMINE MARK", HUMAN_LOWER_WARDS_INVESTIGATION.objective_for_step("inspect_mark") or "")
        self.assertIn("TALK INFORMANT", HUMAN_LOWER_WARDS_INVESTIGATION.objective_for_step("find_informant") or "")

    def test_combat_and_progression_direction(self) -> None:
        self.assertEqual(COMBAT_RULES.mode, "real_time")
        self.assertEqual(COMBAT_RULES.baseline_attack_behavior, "automatic")
        self.assertTrue(COMBAT_RULES.active_abilities_during_auto_attack)
        self.assertTrue(COMBAT_RULES.abilities_use_mana_like_resource)
        self.assertTrue(COMBAT_RULES.abilities_use_cooldowns)
        self.assertEqual(PROGRESSION_RULES.character_level_source, "experience_points")
        self.assertEqual(PROGRESSION_RULES.ability_progression_source, "use_based")


    def test_custom_stat_relationships(self) -> None:
        stats = CharacterStats(might=3, grace=10, love=4, mind=6, hp=12)
        self.assertEqual(stats.auto_attack_damage(7), 10)
        self.assertEqual(stats.healing_amount(8), 12)
        self.assertEqual(stats.spell_damage(9), 15)
        self.assertEqual(stats.maximum_hp(50), 62)
        self.assertEqual(stats.maximum_mana(20), 30)
        self.assertEqual(stats.mana_bonus, 10)

        combatant = CombatantState(99, "human", 50, 50, 20, 20, 2.0, stats=stats)
        self.assertLess(combatant.effective_auto_attack_interval(), 2.0)
        combatant.armor_class = 12
        self.assertFalse(combatant.is_hit_by(11))
        self.assertTrue(combatant.is_hit_by(12))

    def test_armor_class_is_equipment_derived(self) -> None:
        equipment = [
            EquipmentItem("Iron Coat", "body", armor_class=4),
            EquipmentItem("Buckler", "offhand", armor_class=2),
        ]
        self.assertEqual(total_armor_class(equipment), 6)
        self.assertTrue(COMBAT_RULES.hit_resolution_uses_equipment_armor_class)

    def test_social_refusal_is_authored_per_npc(self) -> None:
        policy = NpcSocialPolicy(
            distrusted_races=frozenset({"goblin", "troll"}),
            feared_races=frozenset({"undead"}),
            refused_races=frozenset({"troll"}),
        )
        self.assertEqual(policy.reaction_to("goblin"), "distrust")
        self.assertEqual(policy.reaction_to("undead"), "fear")
        self.assertEqual(policy.reaction_to("troll"), "refuse_service")
        self.assertEqual(policy.reaction_to("dwarf"), "normal")

    def test_hybrid_starting_stats(self) -> None:
        baseline = starting_stat_baseline("goblin", "wizard")
        self.assertLess(baseline.might, baseline.grace)
        allocation = CharacterStats(might=1, grace=1, love=1, mind=1, hp=1)
        final = build_starting_stats("goblin", "wizard", allocation)
        self.assertEqual(sum(allocation.as_dict().values()), STARTING_STAT_RULES.discretionary_points)
        self.assertEqual(final, baseline.plus(allocation))

    def test_class_abilities_are_fixed_not_player_selected(self) -> None:
        self.assertFalse(CLASS_ABILITY_RULES.player_selects_class_abilities)
        self.assertTrue(CLASS_ABILITY_RULES.ability_sets_are_fixed_by_class)
        self.assertEqual(set(FIXED_CLASS_ABILITIES), {c.key for c in CLASSES})

    def test_authored_early_class_kits(self) -> None:
        self.assertEqual(
            [a.key for a in class_abilities_for_level("brute", 1)],
            ["taunt"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("brute", 2)],
            ["taunt", "heavy_strike"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("wizard", 3)],
            ["coldfire_burst", "minor_barrier", "arcane_bolt"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("necromancer", 1)],
            ["minor_life_tap"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("necromancer", 2)],
            ["minor_life_tap", "raise_skeleton"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("necromancer", 3)],
            ["minor_life_tap", "raise_skeleton", "rot"],
        )
        self.assertEqual(
            [a.key for a in class_abilities_for_level("druid", 2)],
            ["forage", "minor_heal", "hp_buff"],
        )

    def test_bone_chips_are_common_merchant_stock_for_necromancers(self) -> None:
        self.assertIn("bone_chips", ITEMS_BY_KEY)
        self.assertIn("bone_chips", COMMON_MERCHANT_STOCK_BY_KEY)
        self.assertTrue(COMMON_MERCHANT_STOCK_BY_KEY["bone_chips"].common_stock)
        self.assertTrue(ASHEN_WAY_CURIO_PEDDLER_MERCHANT.sells("bone_chips"))

    def test_taunt_uses_hate_list_and_improves_with_level(self) -> None:
        hate = EnemyHateList()
        hate.add_threat("wizard", 25)
        hate.add_threat("brute", 3)
        self.assertEqual(TAUNT_RULES.mana_cost, 10)
        self.assertEqual(TAUNT_RULES.cooldown_seconds, 5.0)
        self.assertAlmostEqual(TAUNT_RULES.success_chance(1), 0.30)
        self.assertGreater(TAUNT_RULES.success_chance(10), TAUNT_RULES.success_chance(1))
        self.assertTrue(hate.taunt("brute", character_level=31, roll=0.89))
        self.assertEqual(hate.top_target(), "brute")

    def test_brute_baseline_and_approved_race_adjustments(self) -> None:
        human_brute = starting_stat_baseline("human", "brute")
        self.assertEqual(human_brute, CharacterStats(might=10, grace=6, love=5, mind=5, hp=15))
        moon_elf_brute = starting_stat_baseline("moon_elf", "brute")
        self.assertEqual(moon_elf_brute, CharacterStats(might=8, grace=8, love=5, mind=7, hp=15))
        dwarf_brute = starting_stat_baseline("dwarf", "brute")
        self.assertEqual(dwarf_brute, CharacterStats(might=12, grace=6, love=5, mind=5, hp=18))
        forest_elf_brute = starting_stat_baseline("forest_elf", "brute")
        self.assertEqual(forest_elf_brute, CharacterStats(might=10, grace=8, love=7, mind=5, hp=15))
        goblin_brute = starting_stat_baseline("goblin", "brute")
        self.assertEqual(goblin_brute, CharacterStats(might=9, grace=8, love=5, mind=5, hp=15))
        troll_brute = starting_stat_baseline("troll", "brute")
        self.assertEqual(troll_brute, CharacterStats(might=13, grace=5, love=5, mind=5, hp=18))
        sporekin_brute = starting_stat_baseline("sporekin", "brute")
        self.assertEqual(sporekin_brute, CharacterStats(might=9, grace=6, love=7, mind=7, hp=15))

    def test_brute_starting_ac_is_equipment_derived(self) -> None:
        self.assertEqual(BRUTE_STARTER_ARMOR.armor_class, 8)
        self.assertEqual(starting_armor_class("brute"), 8)
        self.assertEqual(starting_armor_class("wizard"), 0)
        self.assertIn("brute", BRUTE_STARTER_ARMOR.allowed_classes)

    def test_class_endgame_roles_are_locked(self) -> None:
        self.assertTrue(ENDGAME_CLASS_RULES.brute_primary_tank)
        self.assertTrue(ENDGAME_CLASS_RULES.brute_gear_and_weapons_critical)
        self.assertTrue(ENDGAME_CLASS_RULES.wizard_single_target_nuke_specialist)
        self.assertTrue(ENDGAME_CLASS_RULES.wizard_world_teleportation)
        self.assertTrue(ENDGAME_CLASS_RULES.priest_prime_healer)
        self.assertTrue(ENDGAME_CLASS_RULES.priest_resurrects_allies)
        self.assertTrue(ENDGAME_CLASS_RULES.priest_hp_and_ac_buffs)
        self.assertTrue(ENDGAME_CLASS_RULES.priest_heavy_plate)
        self.assertTrue(ENDGAME_CLASS_RULES.necromancer_powerful_undead_pet)
        self.assertTrue(ENDGAME_CLASS_RULES.necromancer_lich_like_form)
        self.assertTrue(ENDGAME_CLASS_RULES.necromancer_dot_specialist)
        self.assertTrue(ENDGAME_CLASS_RULES.druid_reliable_secondary_healer)
        self.assertFalse(ENDGAME_CLASS_RULES.druid_shapeshifting)
        self.assertFalse(CLASSES_BY_KEY["druid"].allows_shapeshifting)

    def test_priest_deities_and_starter_paths_are_authored(self) -> None:
        self.assertTrue(CLASSES_BY_KEY["priest"].requires_deity_path)
        self.assertTrue(PRIEST_DEITY_RULES.deity_choice_defines_spell_path)
        self.assertTrue(PRIEST_DEITY_RULES.deity_roster_authored)
        self.assertTrue(PRIEST_DEITY_RULES.each_path_has_distinct_progression)
        self.assertEqual([d.name for d in PRIEST_DEITIES], ["Zerjz", "Tenebrous", "Leviathan"])
        self.assertEqual(PRIEST_DEITIES_BY_KEY["zerjz"].domain, "healing")
        self.assertEqual(PRIEST_DEITIES_BY_KEY["tenebrous"].domain, "protection")
        self.assertEqual(PRIEST_DEITIES_BY_KEY["leviathan"].domain, "vengeance")
        self.assertEqual([a.key for a in priest_abilities_for_level("zerjz", 1)], ["restoring_light"])
        self.assertEqual([a.key for a in priest_abilities_for_level("tenebrous", 1)], ["guardian_ward"])
        self.assertEqual([a.key for a in priest_abilities_for_level("leviathan", 1)], ["judgment_bolt"])

    def test_every_character_has_a_basic_starting_weapon_rule(self) -> None:
        self.assertTrue(STARTER_KIT_RULES.every_character_receives_basic_weapon)
        self.assertEqual(STARTER_KIT_RULES.basic_weapon_key, "starter_weapon")
        self.assertTrue(STARTER_KIT_RULES.brute_begins_with_solid_weapon_skill)
        self.assertEqual(STARTER_WEAPON.slot, "weapon")

    def test_equipment_is_raw_stat_first_with_rare_effect_hook(self) -> None:
        coat = EquipmentItem(
            "Union-Forged Coat", "body", armor_class=3,
            stat_bonuses=CharacterStats(hp=2),
        )
        relic = EquipmentItem(
            "Impossible Watch", "trinket", stat_bonuses=CharacterStats(mind=1),
            scripted_effects=("earth_relic_pulse",),
        )
        self.assertFalse(coat.is_special)
        self.assertTrue(relic.is_special)
        self.assertEqual(total_equipment_stat_bonuses([coat, relic]), CharacterStats(mind=1, hp=2))
        self.assertTrue(EQUIPMENT_DESIGN_RULES.ordinary_items_focus_on_raw_stats)
        self.assertTrue(EQUIPMENT_DESIGN_RULES.scripted_effects_are_rare_or_special)

    def test_equipment_can_be_universal_race_or_class_restricted(self) -> None:
        universal = EquipmentItem("Plain Ring", "ring", stat_bonuses=CharacterStats(hp=1))
        human_only = EquipmentItem("Human Relic", "trinket", allowed_races=frozenset({"human"}))
        brute_only = EquipmentItem("Brute Harness", "body", allowed_classes=frozenset({"brute"}))
        both = EquipmentItem(
            "Restricted Plate", "body",
            allowed_races=frozenset({"dwarf"}),
            allowed_classes=frozenset({"priest"}),
        )
        self.assertTrue(universal.is_universal)
        self.assertTrue(can_equip_item(universal, "goblin", "wizard"))
        self.assertTrue(can_equip_item(human_only, "human", "wizard"))
        self.assertFalse(can_equip_item(human_only, "elf", "wizard"))
        self.assertTrue(can_equip_item(brute_only, "troll", "brute"))
        self.assertFalse(can_equip_item(brute_only, "troll", "wizard"))
        self.assertTrue(can_equip_item(both, "dwarf", "priest"))
        self.assertFalse(can_equip_item(both, "human", "priest"))

    def test_gear_sources_include_crafting_drops_and_quests(self) -> None:
        self.assertTrue(GEAR_ACQUISITION_RULES.crafting_enabled)
        self.assertTrue(GEAR_ACQUISITION_RULES.enemy_drops_enabled)
        self.assertTrue(GEAR_ACQUISITION_RULES.quest_rewards_enabled)
        self.assertEqual(GearSource("crafting", "smithing").primary_method, "crafting")
        self.assertEqual(GearSource("drop", "named_enemy").primary_method, "drop")
        self.assertEqual(GearSource("quest", "quest_reward").primary_method, "quest")

    def test_named_enemies_and_master_crafting_support_good_gear(self) -> None:
        named_drop = NamedEnemyLootEntry(
            enemy_key="test_named_rat",
            enemy_name="Test Named Rat",
            item_key="test_crown",
            notable_stats=CharacterStats(might=3, hp=4),
            armor_class=2,
        )
        self.assertTrue(named_drop.unique_to_enemy)
        self.assertGreater(sum(named_drop.notable_stats.as_dict().values()), 0)
        recipe = CraftingRecipe("test_plate", "smithing", "test_plate_item", 50, 200)
        self.assertFalse(recipe.can_craft(49))
        self.assertTrue(recipe.can_craft(50))
        self.assertFalse(recipe.produces_high_quality_result(199))
        self.assertTrue(recipe.produces_high_quality_result(200))
        self.assertTrue(CRAFTING_PROGRESSION_RULES.master_crafting_can_compete_with_strong_drops)

    def test_crafting_profession_roster_and_node_based_mining(self) -> None:
        self.assertEqual(
            [profession.name for profession in PROFESSIONS],
            ["Blacksmithing", "Tailoring", "Enchanting", "Alchemy", "Cooking"],
        )
        self.assertTrue(GATHERING_SKILLS_BY_KEY["mining"].node_based)
        self.assertTrue(GATHERING_SKILLS_BY_KEY["harvesting"].node_based)
        self.assertEqual(IRON_VEIN.output_item_key, "iron_ore")
        self.assertEqual(COTTON_PATCH.output_item_key, "raw_cotton")
        self.assertEqual(ITEMS_BY_KEY["iron_ore"].name, "Iron Ore")
        self.assertEqual(ITEMS_BY_KEY["raw_cotton"].name, "Raw Cotton")

    def test_blacksmithing_metal_progression_starts_with_iron_and_scales_to_astralite(self) -> None:
        self.assertEqual(
            [tier.name for tier in METAL_TIERS],
            ["Iron", "Steel", "Cobalt", "Moonsteel", "Emberite", "Stariron", "Astralite"],
        )
        self.assertEqual([tier.tier for tier in METAL_TIERS], list(range(1, 8)))
        self.assertTrue(
            all(
                earlier.blacksmithing_skill < later.blacksmithing_skill
                for earlier, later in zip(METAL_TIERS, METAL_TIERS[1:])
            )
        )

        iron_smelt = BLACKSMITHING_RECIPES_BY_KEY["smelt_iron_ingot"]
        self.assertEqual(iron_smelt.trade_skill_key, "blacksmithing")
        self.assertEqual(iron_smelt.station_key, "forge")
        self.assertEqual([(m.item_key, m.quantity) for m in iron_smelt.materials], [("iron_ore", 2)])

        steel_smelt = BLACKSMITHING_RECIPES_BY_KEY["smelt_steel_ingot"]
        self.assertEqual(
            [(m.item_key, m.quantity) for m in steel_smelt.materials],
            [("iron_ingot", 1), ("coal", 1)],
        )
        moonsteel_smelt = BLACKSMITHING_RECIPES_BY_KEY["smelt_moonsteel_ingot"]
        self.assertEqual(
            [(m.item_key, m.quantity) for m in moonsteel_smelt.materials],
            [("steel_ingot", 1), ("moonsilver_ore", 1)],
        )
        self.assertIn("provisional", moonsteel_smelt.design_status)
        self.assertIn("astralite_breastplate", ITEMS_BY_KEY)
        self.assertEqual(RESOURCE_NODES_BY_KEY["astralite_vein"].minimum_skill, 135)

    def test_every_blacksmithing_recipe_points_to_authored_items(self) -> None:
        for recipe in BLACKSMITHING_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for requirement in recipe.materials:
                self.assertIn(requirement.item_key, ITEMS_BY_KEY)

        self.assertEqual(RESOURCE_NODES_BY_KEY["cobalt_vein"].output_item_key, "cobalt_ore")
        self.assertEqual(RESOURCE_NODES_BY_KEY["moonsilver_vein"].output_item_key, "moonsilver_ore")
        self.assertEqual(RESOURCE_NODES_BY_KEY["emberite_vein"].output_item_key, "emberite_ore")
        self.assertEqual(RESOURCE_NODES_BY_KEY["stariron_deposit"].output_item_key, "stariron_ore")
        self.assertEqual(RESOURCE_NODES_BY_KEY["astralite_vein"].output_item_key, "astralite_ore")

    def test_early_leveling_is_quicker_then_steepens(self) -> None:
        early = [PROGRESSION_RULES.xp_to_next_level(level) for level in range(1, 6)]
        late = [PROGRESSION_RULES.xp_to_next_level(level) for level in range(11, 16)]
        self.assertLess(max(early), min(late))
        self.assertEqual(PROGRESSION_RULES.level_for_experience(0), 1)
        self.assertEqual(
            PROGRESSION_RULES.level_for_experience(PROGRESSION_RULES.cumulative_xp_for_level(10)),
            10,
        )

    def test_open_world_gates_support_flags_keys_and_groups(self) -> None:
        gate = ContentGate(
            required_flags=frozenset({"opened_old_gate"}),
            required_keys=frozenset({"black_iron_key"}),
            minimum_group_size=3,
        )
        solo = CharacterAccessState(
            flags=frozenset({"opened_old_gate"}),
            keys=frozenset({"black_iron_key"}),
            group_size=1,
        )
        group = CharacterAccessState(
            flags=solo.flags, keys=solo.keys, group_size=3,
        )
        self.assertFalse(gate.allows(solo))
        self.assertTrue(gate.allows(group))
        self.assertTrue(WORLD_ACCESS_RULES.mostly_open_world)
        self.assertTrue(WORLD_ACCESS_RULES.every_class_can_solo_to_end_level)

    def test_npc_reactions_can_use_race_or_class(self) -> None:
        policy = NpcSocialPolicy(
            respected_classes=frozenset({"priest"}),
            hostile_classes=frozenset({"necromancer"}),
            distrusted_races=frozenset({"goblin"}),
        )
        self.assertEqual(policy.reaction_to("human", "priest"), "respect")
        self.assertEqual(policy.reaction_to("human", "necromancer"), "hostile")
        self.assertEqual(policy.reaction_to("goblin", "wizard"), "distrust")

    def test_quest_mix_is_structured_and_freeform(self) -> None:
        self.assertTrue(QUEST_DESIGN_RULES.early_game_uses_structured_guidance)
        self.assertTrue(QUEST_DESIGN_RULES.world_also_supports_freeform_discovery)
        self.assertTrue(QUEST_DESIGN_RULES.structured_quests_are_not_the_only_progression_path)


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return None

    def get_extra_info(self, name: str):
        return ("test", 0) if name == "peername" else None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None

    def text(self) -> str:
        return self.buffer.decode("utf-8", errors="replace")


class InteractivePuzzleTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_call_launches_forgotten_pulse_at_the_veil(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("pulse_handoff", "not-a-real-hash")
            character = db.create_character(account.id, "Raincap", "sporekin", "wizard")
            db.advance_quest(character.id, SPOREKIN_FIRST_CALL.key, "climb_toward_light")
            db.set_character_room(character.id, "sporekin_rootwell_ascent")
            character = db.get_character_by_name("Raincap")
            assert character is not None

            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING
            await session.move_character("up")

            first = db.get_quest(character.id, SPOREKIN_FIRST_CALL.key)
            second = db.get_quest(character.id, SPOREKIN_FORGOTTEN_PULSE.key)
            assert first is not None and second is not None
            self.assertEqual(first["status"], "completed")
            self.assertEqual(second["status"], "active")
            self.assertEqual(second["current_step"], "cross_veil")
            self.assertIn("memory near the rain", writer.text().lower())

    async def test_forest_elf_first_walk_uses_examine_and_listen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("elf_listener", "not-a-real-hash")
            character = db.create_character(account.id, "Willow", "forest_elf", "wizard")
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING

            await session.move_character("north")
            await session.move_character("east")
            await session.move_character("north")
            quest = db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)
            assert quest is not None
            self.assertEqual(quest["current_step"], "study_waystone")

            reader.feed_data(b"examine waystone\n")
            await session.playing_prompt()
            self.assertEqual(db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)["current_step"], "listen_pool")

            await session.move_character("east")
            reader.feed_data(b"listen\n")
            await session.playing_prompt()
            self.assertEqual(db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)["current_step"], "reach_outer_grove")

            await session.move_character("north")
            quest = db.get_quest(character.id, FOREST_ELF_FIRST_WALK.key)
            assert quest is not None
            self.assertEqual(quest["status"], "completed")
            self.assertIn("forest_elf_first_walk_completed", db.list_flags(character.id))
            self.assertIn("beauty and danger share the same forest", writer.text().lower())

    async def test_human_lower_wards_investigation_command_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("lower_wards_case", "not-a-real-hash")
            character = db.create_character(account.id, "Vesper", "human", "brute")
            db.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            db.grant_flag(character.id, "met_high_acolyte")
            db.start_quest(character.id, HUMAN_COMBAT_TRAINING.key, "complete")
            db.complete_quest(character.id, HUMAN_COMBAT_TRAINING.key)
            db.grant_flag(character.id, "human_combat_training_complete")
            db.set_character_room(character.id, "human_grand_cathedral")
            character = db.get_character_by_name("Vesper")
            assert character is not None

            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING

            reader.feed_data(b"talk high acolyte\n")
            await session.playing_prompt()
            quest = db.get_quest(character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
            assert quest is not None
            self.assertEqual(quest["current_step"], "find_lower_wards")

            await session.move_character("south")
            await session.move_character("south")
            await session.move_character("west")
            self.assertEqual(
                db.get_quest(character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)["current_step"],
                "inspect_mark",
            )
            await session.move_character("down")
            await session.move_character("east")
            reader.feed_data(b"examine mark\n")
            await session.playing_prompt()
            self.assertEqual(
                db.get_quest(character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)["current_step"],
                "find_informant",
            )
            await session.move_character("west")
            await session.move_character("south")
            reader.feed_data(b"talk informant\n")
            await session.playing_prompt()
            quest = db.get_quest(character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
            assert quest is not None
            self.assertEqual(quest["status"], "completed")
            self.assertIn("human_lower_wards_mark_traced", db.list_flags(character.id))
            self.assertIn("old cistern tunnels", writer.text().lower())

    async def test_minor_life_tap_deals_damage_and_restores_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("life_tap_test", "not-a-real-hash")
            character = db.create_character(account.id, "Siphon", "human", "necromancer")
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character.id, "human", 10, 30, 20, 20, 3.0, stats=character.stats
            )
            enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
            session.active_enemy = enemy
            before_enemy = enemy.current_hp
            before_player = session.combatant.current_hp
            await session.use_ability("minor life tap")
            self.assertLess(enemy.current_hp, before_enemy)
            self.assertGreater(session.combatant.current_hp, before_player)
            self.assertIn("tears", writer.text().lower())

    async def test_rot_pulses_damage_over_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("rot_test", "not-a-real-hash")
            character = db.create_character(account.id, "Blight", "human", "necromancer")
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character.id, "human", 30, 30, 20, 20, 3.0, stats=character.stats
            )
            enemy = EnemyState(ENEMIES_BY_KEY["sewer_rat"])
            session.active_enemy = enemy
            before = enemy.current_hp
            await session._apply_rot(enemy, damage_per_tick=2, ticks=3, interval=0)
            self.assertEqual(enemy.current_hp, before - 6)
            self.assertGreaterEqual(writer.text().lower().count("rot gnaws"), 3)

    async def test_briarshadow_stalker_only_aggros_in_same_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("stalker_target", "not-a-real-hash")
            character = db.create_character(account.id, "Fern", "forest_elf", "brute")
            db.set_character_room(character.id, FOREST_ELF_BRIARSHADOW_THICKET_KEY)
            character = db.get_character_by_name("Fern")
            assert character is not None

            manager = MobileNpcManager((BRIARSHADOW_STALKER,))
            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db, mobile_npcs=manager)
            session.character = character
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character.id,
                "forest_elf",
                40,
                40,
                20,
                20,
                2.5,
                stats=character.stats,
            )

            started = await session.check_mobile_npc_aggression()
            self.assertTrue(started)
            self.assertEqual(session.active_mobile_npc_key, BRIARSHADOW_STALKER.key)
            self.assertEqual(
                manager.states[BRIARSHADOW_STALKER.key].engaged_character_id,
                character.id,
            )
            self.assertIn("lunges to attack", writer.text().lower())
            await session._stop_combat()

    async def test_sporekin_touch_puzzle_resets_then_solves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("pulse_player", "not-a-real-hash")
            character = db.create_character(account.id, "Glowstep", "sporekin", "druid")
            db.complete_quest(character.id, SPOREKIN_FIRST_CALL.key)
            db.grant_flag(character.id, "sporekin_first_call_answered")
            db.start_quest(character.id, SPOREKIN_FORGOTTEN_PULSE.key, "study_ring")
            db.set_character_room(character.id, SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY)
            character = db.get_character_by_name("Glowstep")
            assert character is not None

            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING

            async def issue(command: str) -> None:
                reader.feed_data((command + "\n").encode())
                await session.playing_prompt()

            await issue("examine ring")
            self.assertEqual(db.get_quest(character.id, SPOREKIN_FORGOTTEN_PULSE.key)["current_step"], "touch_blue")
            await issue("touch amber mushroom")
            self.assertEqual(db.get_quest(character.id, SPOREKIN_FORGOTTEN_PULSE.key)["current_step"], "touch_blue")
            for command in (
                "touch blue mushroom",
                "touch amber mushroom",
                "touch violet mushroom",
                "touch ivory mushroom",
            ):
                await issue(command)

            quest = db.get_quest(character.id, SPOREKIN_FORGOTTEN_PULSE.key)
            assert quest is not None
            self.assertEqual(quest["status"], "completed")
            self.assertIn("sporekin_forgotten_pulse_solved", db.list_flags(character.id))
            self.assertIn("new path is open to the north", writer.text().lower())


    async def test_real_death_loses_xp_and_returns_to_bind_point(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("death_flow", "not-a-real-hash")
            character = db.create_character(account.id, "Morrow", "human", "wizard")
            db.add_experience(character.id, 150)  # level 2, 50 XP into the level
            db.set_bind_room(character.id, "human_grand_cathedral")
            db.set_character_room(character.id, HUMAN_VERMIN_PENS_KEY)
            character = db.get_character_by_name("Morrow")
            assert character is not None

            reader = asyncio.StreamReader()
            writer = _FakeWriter()
            session = PlayerSession(reader, writer, db)
            session.character = character
            session.state = SessionState.PLAYING
            session.combatant = CombatantState(
                character_id=character.id, race_key="human",
                current_hp=0, max_hp=40, current_mana=0, max_mana=30,
                auto_attack_interval=2.5, stats=character.stats, armor_class=0,
            )
            await session._handle_character_death("Sewer Horror")

            loaded = db.get_character_by_name("Morrow")
            assert loaded is not None
            self.assertEqual(loaded.current_room, "human_grand_cathedral")
            self.assertEqual(loaded.bind_room, "human_grand_cathedral")
            self.assertEqual(loaded.experience, 145)
            self.assertEqual(loaded.level, 2)
            self.assertEqual(session.combatant.current_hp, session.combatant.max_hp)
            self.assertEqual(session.combatant.current_mana, session.combatant.max_mana)
            self.assertIn("you lose 5 experience", writer.text().lower())
            self.assertIn("grand cathedral", writer.text().lower())




class MudletProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_hud_url_is_enabled_by_default(self) -> None:
        old_url = os.environ.pop("DREAMS_MUDLET_HUD_URL", None)
        old_version = os.environ.pop("DREAMS_MUDLET_HUD_VERSION", None)
        try:
            offer = configured_mudlet_gui_offer()
            self.assertTrue(offer.enabled)
            self.assertEqual(offer.url, OFFICIAL_MUDLET_HUD_URL)
            self.assertEqual(
                offer.url,
                "https://mud.lvthn.io/DreamsOfTheFallenHUD.mpackage",
            )
            self.assertEqual(offer.version, OFFICIAL_MUDLET_HUD_VERSION)
        finally:
            if old_url is not None:
                os.environ["DREAMS_MUDLET_HUD_URL"] = old_url
            if old_version is not None:
                os.environ["DREAMS_MUDLET_HUD_VERSION"] = old_version

    async def test_telnet_reader_consumes_gmcp_negotiation_and_preserves_command(self) -> None:
        reader = asyncio.StreamReader()
        writer = _FakeWriter()
        connection = TelnetConnection(reader, writer)
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
        self.assertIn(b'"version":"1.0.0"', raw)

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
            session.active_enemy = EnemyState(ENEMIES_BY_KEY['sewer_rat'])
            session.active_enemy.current_hp = 9
            session.telnet.gmcp_enabled = True
            await session.send_client_state()

            raw = bytes(writer.buffer)
            self.assertIn(b'Char.Vitals', raw)
            self.assertIn(b'"hp":31', raw)
            self.assertIn(b'"mana":14', raw)
            self.assertIn(b'"movement":88', raw)
            self.assertIn(b'"opponent_health":9', raw)
            self.assertIn(b'Char.Status', raw)
            self.assertIn(b'"opponent_name":"Sewer Rat"', raw)
            self.assertIn(b'Dreams.Target', raw)


class OfficialMudletHudPackageTests(unittest.TestCase):
    def test_official_hud_package_contains_installable_xml_and_gmcp_handlers(self) -> None:
        root = Path(__file__).resolve().parents[1]
        package_path = root / "mudlet" / "DreamsOfTheFallenHUD" / "DreamsOfTheFallenHUD.mpackage"
        self.assertTrue(package_path.exists())
        with zipfile.ZipFile(package_path) as zf:
            names = set(zf.namelist())
            self.assertIn("DreamsOfTheFallenHUD.xml", names)
            self.assertIn("config.lua", names)
            xml_bytes = zf.read("DreamsOfTheFallenHUD.xml")
            config = zf.read("config.lua").decode("utf-8")

        tree = ET.fromstring(xml_bytes)
        self.assertEqual(tree.tag, "MudletPackage")
        scripts = tree.findall(".//Script/script")
        combined = "\n".join(node.text or "" for node in scripts)
        self.assertIn("gmcp.Dreams.Vitals", combined)
        self.assertIn("gmcp.Dreams.Target", combined)
        self.assertIn("Geyser.Gauge", combined)
        self.assertIn("setBorderTop", combined)
        self.assertIn("setBorderRight", combined)
        self.assertIn('mpackage = "DreamsOfTheFallenHUD"', config)
        self.assertIn('version = "1.0.0"', config)



class PersistenceTests(unittest.TestCase):
    def test_xp_and_ability_use_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("tester", "not-a-real-hash")
            character = db.create_character(account.id, "Mara", "human", "wizard")
            db.add_experience(character.id, 25)
            db.set_character_stats(
                character.id, might=2, grace=3, love=4, mind=5, hp=6
            )
            db.record_ability_use(character.id, "spark", 3)
            db.record_ability_use(character.id, "spark", 4)

            loaded = db.get_character_by_name("Mara")
            assert loaded is not None
            self.assertEqual(loaded.experience, 25)
            self.assertEqual(loaded.stats, CharacterStats(2, 3, 4, 5, 6))
            self.assertEqual(
                db.list_ability_progress(character.id),
                [{"ability_key": "spark", "uses": 2, "skill_xp": 7}],
            )

    def test_old_fungal_and_sporkkin_keys_migrate_to_sporekin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mud.db"
            db = Database(path)
            account = db.create_account("tester", "not-a-real-hash")
            fungal = db.create_character(account.id, "Moss", "sporekin", "druid")
            legacy = db.create_character(account.id, "Mold", "sporekin", "brute")
            with db.connect() as conn:
                conn.execute("UPDATE characters SET race = 'fungal', current_room = NULL WHERE id = ?", (fungal.id,))
                conn.execute("UPDATE characters SET race = 'sporkkin', current_room = NULL WHERE id = ?", (legacy.id,))
            # Reinitialization runs development migrations.
            migrated_db = Database(path)
            migrated_fungal = migrated_db.get_character_by_name("Moss")
            migrated_legacy = migrated_db.get_character_by_name("Mold")
            assert migrated_fungal is not None and migrated_legacy is not None
            self.assertEqual(migrated_fungal.race, "sporekin")
            self.assertEqual(migrated_legacy.race, "sporekin")
            self.assertEqual(migrated_fungal.current_room, SPOREKIN_START_ROOM_KEY)
            self.assertEqual(migrated_legacy.current_room, SPOREKIN_START_ROOM_KEY)

    def test_level_updates_and_access_tokens_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("gate_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Vale", "dwarf", "brute")
            target_xp = PROGRESSION_RULES.cumulative_xp_for_level(6)
            level = db.add_experience(character.id, target_xp)
            db.grant_flag(character.id, "met_union_foreman")
            db.grant_key(character.id, "foundry_key")
            self.assertEqual(level, 6)
            loaded = db.get_character_by_name("Vale")
            assert loaded is not None
            self.assertEqual(loaded.level, 6)
            self.assertEqual(db.list_flags(character.id), frozenset({"met_union_foreman"}))
            self.assertEqual(db.list_keys(character.id), frozenset({"foundry_key"}))

    def test_starting_weapon_and_necromancer_bone_chip_catalyst_pet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("bone_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Graves", "human", "necromancer")
            self.assertEqual(db.item_quantity(character.id, "starter_weapon"), 1)
            self.assertFalse(
                db.summon_pet_with_catalyst(
                    character.id,
                    pet_key="skeleton",
                    catalyst_item_key="bone_chips",
                )
            )
            db.add_item(character.id, "bone_chips", 2)
            self.assertTrue(
                db.summon_pet_with_catalyst(
                    character.id,
                    pet_key="skeleton",
                    catalyst_item_key="bone_chips",
                )
            )
            self.assertEqual(db.item_quantity(character.id, "bone_chips"), 1)
            self.assertEqual(db.get_active_pet(character.id), "skeleton")

    def test_bind_point_defaults_to_start_and_is_independent_of_movement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("bind_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Anchor", "human", "wizard")
            self.assertEqual(character.current_room, HUMAN_START_ROOM_KEY)
            self.assertEqual(character.bind_room, HUMAN_START_ROOM_KEY)

            db.set_character_room(character.id, "human_cathedral_square")
            moved = db.get_character_by_name("Anchor")
            assert moved is not None
            self.assertEqual(moved.current_room, "human_cathedral_square")
            self.assertEqual(moved.bind_room, HUMAN_START_ROOM_KEY)

            # Future binding spells use this setter; ordinary movement never does.
            db.set_bind_room(character.id, "human_grand_cathedral")
            rebound = db.get_character_by_name("Anchor")
            assert rebound is not None
            self.assertEqual(rebound.bind_room, "human_grand_cathedral")

    def test_death_rules_lose_current_level_progress_without_deleveling(self) -> None:
        level_two_floor = PROGRESSION_RULES.cumulative_xp_for_level(2)
        loss, floor = DEATH_RULES.experience_loss(2, level_two_floor + 50)
        self.assertEqual(floor, level_two_floor)
        self.assertEqual(loss, 5)
        self.assertFalse(DEATH_RULES.allow_level_loss)

    def test_experience_loss_respects_level_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("death_xp", "not-a-real-hash")
            character = db.create_character(account.id, "Fallen", "human", "brute")
            db.add_experience(character.id, 150)
            actual, xp, level = db.apply_experience_loss(character.id, 999, floor_experience=100)
            self.assertEqual(actual, 50)
            self.assertEqual(xp, 100)
            self.assertEqual(level, 2)

    def test_trade_skill_progress_is_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("crafter_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Forge", "dwarf", "brute")
            db.record_trade_skill_use(character.id, "smithing", 3)
            db.record_trade_skill_use(character.id, "smithing", 5)
            self.assertEqual(
                db.get_trade_skill_progress(character.id, "smithing"),
                {"uses": 2, "skill_xp": 8},
            )
            self.assertEqual(
                db.list_trade_skills(character.id),
                [{"trade_skill_key": "smithing", "uses": 2, "skill_xp": 8}],
            )

    def test_mining_and_blacksmithing_loop_persists_inventory_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("smith_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Hammer", "dwarf", "brute")
            node = ResourceNodeState(IRON_VEIN, remaining_uses=2)

            self.assertEqual(mine_node(db, character.id, node), "iron_ore")
            self.assertEqual(mine_node(db, character.id, node), "iron_ore")
            self.assertTrue(node.depleted)
            self.assertEqual(db.item_quantity(character.id, "iron_ore"), 2)
            self.assertEqual(
                db.get_trade_skill_progress(character.id, "mining"),
                {"uses": 2, "skill_xp": 2},
            )

            no_forge = craft_recipe(db, character.id, "smelt_iron_ingot")
            self.assertFalse(no_forge.success)
            self.assertIn("forge", no_forge.message.lower())

            smelted = craft_recipe(
                db, character.id, "smelt_iron_ingot", station_key="forge"
            )
            self.assertTrue(smelted.success)
            self.assertEqual(db.item_quantity(character.id, "iron_ore"), 0)
            self.assertEqual(db.item_quantity(character.id, "iron_ingot"), 1)
            self.assertEqual(
                db.get_trade_skill_progress(character.id, "blacksmithing"),
                {"uses": 1, "skill_xp": 1},
            )

            dagger = craft_recipe(
                db, character.id, "forge_iron_dagger", station_key="forge"
            )
            self.assertTrue(dagger.success)
            self.assertEqual(db.item_quantity(character.id, "iron_ingot"), 0)
            self.assertEqual(db.item_quantity(character.id, "iron_dagger"), 1)


    def test_cotton_tailoring_loop_persists_inventory_and_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("tailor_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Needle", "forest_elf", "druid")
            patch = ResourceNodeState(COTTON_PATCH, remaining_uses=8)

            for _ in range(8):
                self.assertEqual(gather_node(db, character.id, patch), "raw_cotton")
            self.assertTrue(patch.depleted)
            self.assertEqual(db.item_quantity(character.id, "raw_cotton"), 8)
            self.assertEqual(
                db.get_trade_skill_progress(character.id, "harvesting"),
                {"uses": 8, "skill_xp": 8},
            )

            no_loom = craft_recipe(db, character.id, "spin_cotton_thread")
            self.assertFalse(no_loom.success)
            self.assertIn("loom", no_loom.message.lower())

            for _ in range(2):
                spun = craft_recipe(
                    db, character.id, "spin_cotton_thread", station_key="loom"
                )
                self.assertTrue(spun.success)
            self.assertEqual(db.item_quantity(character.id, "raw_cotton"), 4)
            self.assertEqual(db.item_quantity(character.id, "cotton_thread"), 4)

            for _ in range(2):
                woven = craft_recipe(
                    db, character.id, "weave_cotton_cloth", station_key="loom"
                )
                self.assertTrue(woven.success)
            self.assertEqual(db.item_quantity(character.id, "cotton_thread"), 0)
            self.assertEqual(db.item_quantity(character.id, "cotton_cloth"), 2)

            tunic = craft_recipe(
                db, character.id, "sew_cotton_tunic", station_key="loom"
            )
            self.assertTrue(tunic.success)
            self.assertEqual(db.item_quantity(character.id, "cotton_cloth"), 0)
            self.assertEqual(db.item_quantity(character.id, "cotton_tunic"), 1)
            self.assertEqual(
                db.get_trade_skill_progress(character.id, "tailoring"),
                {"uses": 5, "skill_xp": 5},
            )

    def test_astralweave_endgame_tailoring_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("master_tailor", "not-a-real-hash")
            character = db.create_character(account.id, "Threadseer", "moon_elf", "wizard")
            db.record_trade_skill_use(character.id, "harvesting", 135)
            db.record_trade_skill_use(character.id, "tailoring", 140)
            bloom = ResourceNodeState(ASTRAL_BLOOM, remaining_uses=2)

            self.assertEqual(gather_node(db, character.id, bloom), "astral_bloom_fiber")
            self.assertEqual(gather_node(db, character.id, bloom), "astral_bloom_fiber")
            self.assertTrue(bloom.depleted)

            spun = craft_recipe(
                db, character.id, "spin_astralweave_thread", station_key="loom"
            )
            self.assertTrue(spun.success)
            woven = craft_recipe(
                db, character.id, "weave_astralweave_cloth", station_key="loom"
            )
            self.assertTrue(woven.success)
            hood = craft_recipe(
                db, character.id, "sew_astralweave_hood", station_key="loom"
            )
            self.assertTrue(hood.success)
            self.assertEqual(db.item_quantity(character.id, "astralweave_hood"), 1)

    def test_tailoring_recipes_reference_authored_items(self) -> None:
        self.assertEqual(
            [tier.name for tier in TEXTILE_TIERS],
            [
                "Cotton",
                "Wool",
                "Silk",
                "Moonweave",
                "Spidersilk",
                "Ghostweave",
                "Astralweave",
            ],
        )
        self.assertEqual(len(TAILORING_RECIPES), 28)
        self.assertEqual(TAILORING_RECIPES_BY_KEY["spin_cotton_thread"].station_key, "loom")
        self.assertIn("sew_astralweave_tunic", TAILORING_RECIPES_BY_KEY)
        self.assertEqual(RESOURCE_NODES_BY_KEY["astral_bloom"].minimum_skill, 135)
        for tier in TEXTILE_TIERS:
            self.assertIn(tier.raw_material_key, ITEMS_BY_KEY)
            self.assertIn(tier.thread_item_key, ITEMS_BY_KEY)
            self.assertIn(tier.cloth_item_key, ITEMS_BY_KEY)
            self.assertIn(f"{tier.key}_hood", ITEMS_BY_KEY)
            self.assertIn(f"{tier.key}_tunic", ITEMS_BY_KEY)
        for recipe in TAILORING_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for requirement in recipe.materials:
                self.assertIn(requirement.item_key, ITEMS_BY_KEY)


    def test_alchemy_is_herb_first_and_supports_broad_outputs(self) -> None:
        self.assertTrue(GATHERING_SKILLS_BY_KEY["herbalism"].node_based)
        self.assertEqual(GREENLEAF_PATCH.output_item_key, "greenleaf")
        self.assertEqual(BITTERROOT_CLUSTER.output_item_key, "bitterroot")
        self.assertEqual(LAVENDER_PATCH.output_item_key, "lavender_blossom")
        self.assertEqual(ITEMS_BY_KEY["greenleaf"].category, "herb")
        self.assertIn("perfumes", next(p for p in PROFESSIONS if p.key == "alchemy").primary_outputs)
        self.assertEqual(ALCHEMY_RECIPES_BY_KEY["brew_minor_healing_potion"].station_key, "mortar_and_pestle")
        self.assertEqual(ALCHEMY_RECIPES_BY_KEY["blend_lavender_perfume"].station_key, "alchemy_table")
        perfume = ITEMS_BY_KEY["lavender_perfume"].consumable
        self.assertIsNotNone(perfume)
        assert perfume is not None
        self.assertEqual(perfume.use_mode, "apply")
        self.assertEqual(perfume.temporary_stat_bonuses.grace, 1)
        self.assertGreater(perfume.duration_ticks, 0)

    def test_alchemy_recipes_reference_authored_items(self) -> None:
        self.assertEqual(len(ALCHEMY_RECIPES), 5)
        for recipe in ALCHEMY_RECIPES:
            self.assertIn(recipe.output_item_key, ITEMS_BY_KEY)
            for requirement in recipe.materials:
                self.assertIn(requirement.item_key, ITEMS_BY_KEY)
        healing = ITEMS_BY_KEY["minor_healing_potion"].consumable
        antidote = ITEMS_BY_KEY["lesser_antidote"].consumable
        self.assertIsNotNone(healing)
        self.assertIsNotNone(antidote)
        assert healing is not None and antidote is not None
        self.assertGreater(healing.heal_hp, 0)
        self.assertIn("cleanse_minor_poison", antidote.effect_tags)

    def test_herbalism_to_potion_and_perfume_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("alchemist", "not-a-real-hash")
            character = db.create_character(account.id, "Vial", "goblin", "wizard")

            greenleaf = ResourceNodeState(GREENLEAF_PATCH, remaining_uses=2)
            self.assertEqual(gather_node(db, character.id, greenleaf), "greenleaf")
            self.assertEqual(gather_node(db, character.id, greenleaf), "greenleaf")
            db.add_item(character.id, "spring_water", 1)
            potion = craft_recipe(
                db, character.id, "brew_minor_healing_potion", station_key="mortar_and_pestle"
            )
            self.assertTrue(potion.success)
            self.assertEqual(db.item_quantity(character.id, "minor_healing_potion"), 1)

            # Advance the authored development skills so the same character can
            # exercise the early perfume branch in this focused test.
            db.record_trade_skill_use(character.id, "herbalism", 10)
            db.record_trade_skill_use(character.id, "alchemy", 12)
            lavender = ResourceNodeState(LAVENDER_PATCH, remaining_uses=3)
            for _ in range(3):
                self.assertEqual(gather_node(db, character.id, lavender), "lavender_blossom")
            oil = craft_recipe(
                db, character.id, "distill_lavender_essential_oil", station_key="alchemy_table"
            )
            self.assertTrue(oil.success)
            db.add_item(character.id, "grain_alcohol", 1)
            perfume = craft_recipe(
                db, character.id, "blend_lavender_perfume", station_key="alchemy_table"
            )
            self.assertTrue(perfume.success)
            self.assertEqual(db.item_quantity(character.id, "lavender_perfume"), 1)


    def test_human_starter_note_location_and_intro_quest_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("demon_start", "not-a-real-hash")
            character = db.create_character(account.id, "Ash", "human", "brute")
            self.assertEqual(character.current_room, HUMAN_START_ROOM_KEY)
            self.assertEqual(db.item_quantity(character.id, "sealed_cathedral_note"), 1)
            quest = db.get_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            assert quest is not None
            self.assertEqual(quest["status"], "active")
            self.assertEqual(quest["current_step"], "read_note")

            db.advance_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key, "find_cathedral")
            db.set_character_room(character.id, "human_grand_cathedral")
            db.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            db.grant_flag(character.id, "met_high_acolyte")

            loaded = db.get_character_by_name("Ash")
            assert loaded is not None
            self.assertEqual(loaded.current_room, "human_grand_cathedral")
            self.assertEqual(db.get_quest(loaded.id, HUMAN_CATHEDRAL_SUMMONS.key)["status"], "completed")
            self.assertIn("met_high_acolyte", db.list_flags(loaded.id))

    def test_human_combat_training_progress_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("combat_newbie", "not-a-real-hash")
            character = db.create_character(account.id, "Cinder", "human", "brute")
            db.complete_quest(character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            db.grant_flag(character.id, "met_high_acolyte")
            db.start_quest(character.id, HUMAN_COMBAT_TRAINING.key, "read_training_orders")
            db.advance_quest(character.id, HUMAN_COMBAT_TRAINING.key, "reach_training_yard")
            db.set_character_room(character.id, HUMAN_TRAINING_YARD_KEY)
            db.advance_quest(character.id, HUMAN_COMBAT_TRAINING.key, "practice_dummy")
            db.grant_flag(character.id, "human_training_dummy_defeated")
            db.advance_quest(character.id, HUMAN_COMBAT_TRAINING.key, "defeat_vermin")
            db.grant_flag(character.id, "human_combat_training_complete")
            db.complete_quest(character.id, HUMAN_COMBAT_TRAINING.key)

            loaded = db.get_character_by_name("Cinder")
            assert loaded is not None
            self.assertEqual(loaded.current_room, HUMAN_TRAINING_YARD_KEY)
            training = db.get_quest(loaded.id, HUMAN_COMBAT_TRAINING.key)
            assert training is not None
            self.assertEqual(training["status"], "completed")
            self.assertIn("human_combat_training_complete", db.list_flags(loaded.id))

    def test_priest_deity_choice_can_be_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "mud.db")
            account = db.create_account("priest_tester", "not-a-real-hash")
            character = db.create_character(account.id, "Mercy", "human", "priest")
            self.assertIsNone(character.deity_key)
            db.set_character_deity(character.id, "zerjz")
            loaded = db.get_character_by_name("Mercy")
            assert loaded is not None
            self.assertEqual(loaded.deity_key, "zerjz")


if __name__ == "__main__":
    unittest.main()
