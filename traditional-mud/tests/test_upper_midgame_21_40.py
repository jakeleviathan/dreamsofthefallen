from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.crownfire_march_31_40 as crownfire
import mud.midgame_depth as depth
import mud.upper_class_progression as upper
from mud.combat import EnemyDefinition, EnemyState
from mud.mechanics import CombatantState
from mud.stats import CharacterStats


class UpperClassProgressionDesignTests(unittest.TestCase):
    def test_every_class_has_a_real_21_to_30_identity_and_capstone(self):
        self.assertEqual([a.unlock_level for a in upper.BRUTE_UPPER_ABILITIES], [22, 25, 28, 30])
        self.assertEqual([a.unlock_level for a in upper.WIZARD_UPPER_ABILITIES], [22, 25, 28, 30])
        self.assertEqual([a.unlock_level for a in upper.DRUID_UPPER_ABILITIES], [22, 25, 28, 30])
        self.assertEqual([a.unlock_level for a in upper.NECROMANCER_UPPER_ABILITIES], [22, 25, 28, 30])
        self.assertEqual(upper.PRIEST_COMMON_UPPER[0].unlock_level, 22)
        for deity_key in ("zerjz", "tenebrous", "leviathan"):
            self.assertEqual([a.unlock_level for a in upper.PRIEST_PATH_UPPER[deity_key]], [25, 28, 30])
        self.assertEqual(upper.BRUTE_UPPER_ABILITIES[-1].name, "Breaker's Call")
        self.assertEqual(upper.WIZARD_UPPER_ABILITIES[-1].name, "Convergence")
        self.assertEqual(upper.DRUID_UPPER_ABILITIES[-1].name, "Green Tide")
        self.assertEqual(upper.NECROMANCER_UPPER_ABILITIES[-1].name, "Lichform")

    def test_wizard_sequence_is_executable_not_just_catalog_text(self):
        import mud.mechanics as mechanics

        original = mechanics.FIXED_CLASS_ABILITIES["wizard"]
        upper.register_upper_class_abilities()
        try:
            enemy = EnemyState(EnemyDefinition(
                key="upper_test_enemy",
                name="Upper Test Enemy",
                aliases=("enemy",),
                description="a durable test target",
                max_hp=1000,
                armor_class=0,
                auto_attack_damage=0,
                auto_attack_interval=99.0,
                xp_reward=0,
                retaliates=False,
                tutorial=True,
            ))

            class Session:
                def __init__(self):
                    self.character = SimpleNamespace(
                        id=1,
                        name="Sequencer",
                        race="human",
                        character_class="wizard",
                        deity_key=None,
                        level=30,
                    )
                    self.combatant = CombatantState(
                        character_id=1,
                        race_key="human",
                        current_hp=100,
                        max_hp=100,
                        current_mana=200,
                        max_mana=200,
                        auto_attack_interval=2.0,
                        stats=CharacterStats(mind=10),
                    )
                    self.active_enemy = enemy
                    self.messages = []

                async def send(self, text):
                    self.messages.append(text)

                async def send_client_state(self):
                    return None

            session = Session()

            async def run():
                self.assertTrue(await upper._use_upper(session, "arcane_primer"))
                hp_before = enemy.current_hp
                self.assertTrue(await upper._use_upper(session, "resonant_spear"))
                spear_damage = hp_before - enemy.current_hp
                self.assertGreater(spear_damage, 40)
                hp_before = enemy.current_hp
                self.assertTrue(await upper._use_upper(session, "convergence"))
                convergence_damage = hp_before - enemy.current_hp
                self.assertGreater(convergence_damage, 80)

            asyncio.run(run())
            self.assertEqual(getattr(session, "_upper_arcane_sequence", None), "")
        finally:
            mechanics.FIXED_CLASS_ABILITIES["wizard"] = original


class MidgameDepthDesignTests(unittest.TestCase):
    def test_named_item_pass_is_restrained_and_place_specific(self):
        names = {item.name for item in depth.NAMED_DEPTH_ITEMS}
        self.assertIn("Warden's Iron", names)
        self.assertIn("Brineglass Knife", names)
        self.assertIn("Captain's Tideglass", names)
        self.assertIn("Sluice Regent's Valve-Crown", names)
        self.assertIn("One-Third Cup", names)
        self.assertEqual(len(names), 8)

    def test_hidden_content_is_small_optional_and_not_a_second_main_campaign(self):
        self.assertEqual(len(depth.HIDDEN_ROOMS), 3)
        self.assertEqual(len(depth.SIDE_QUESTS), 3)
        self.assertEqual(
            {room.name for room in depth.HIDDEN_ROOMS},
            {"Warden Service Niche", "Captain's Private Locker", "Dry Inspection Gallery"},
        )
        self.assertTrue(all(quest.style == "freeform" for quest in depth.SIDE_QUESTS))

    def test_three_existing_bosses_have_distinct_first_clear_mechanics(self):
        self.assertEqual(len(depth.WARDEN_BAR_FLAGS), 2)
        self.assertEqual(len(depth.MATRIARCH_FLAGS), 2)
        self.assertEqual(len(depth.REGENT_FLAGS), 3)
        self.assertEqual(len(set((*depth.WARDEN_BAR_FLAGS, *depth.MATRIARCH_FLAGS, *depth.REGENT_FLAGS))), 7)


class CrownfireDesignTests(unittest.TestCase):
    def test_region_is_a_city_two_campaign_dungeons_and_postwar_routes(self):
        self.assertEqual(len(crownfire.SURFACE_ROOM_KEYS), 10)
        self.assertEqual(len(crownfire.CITY_ROOM_KEYS), 6)
        self.assertEqual(len(crownfire.REDOUBT_ROOM_KEYS), 6)
        self.assertEqual(len(crownfire.PALACE_ROOM_KEYS), 8)
        self.assertEqual(len(crownfire.POSTCAP_ROOM_KEYS), 3)
        self.assertEqual(len(crownfire.CROWNFIRE_ROOM_KEYS), 33)

    def test_story_deliberately_breaks_the_misunderstood_ancient_machine_pattern(self):
        self.assertIn("manufactured crisis", crownfire.PALACE_QUEST.description)
        self.assertIn("no hidden machine", crownfire.CAPSTONE_QUEST.description.lower())
        self.assertIn("the orders are his", crownfire.CAPSTONE_QUEST.description.lower())
        dask = next(enemy for enemy in crownfire.CROWNFIRE_ENEMIES if enemy.key == crownfire.MARSHAL_DASK_KEY)
        self.assertEqual(dask.name, "Marshal Corven Dask")
        self.assertIn("gold signet", dask.description)

    def test_level_band_has_six_authored_steps_up_to_forty(self):
        self.assertEqual(
            [quest.minimum_level for quest in crownfire.CROWNFIRE_QUESTS],
            [31, 33, 34, 36, 37, 40],
        )
        self.assertEqual(crownfire.CAPSTONE_QUEST.minimum_level, 40)
        self.assertIn("DEMAND TRIAL", crownfire.CAPSTONE_QUEST.objective_steps[1][1])
        self.assertIn("ORDER EXILE", crownfire.CAPSTONE_QUEST.objective_steps[1][1])
        self.assertIn("FIELD JUDGMENT", crownfire.CAPSTONE_QUEST.objective_steps[1][1])


class ProductionUpperMidgameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import json
import server
from mud import crafting, quests
from mud.crownfire_march_31_40 import (
    CROWNFIRE_ROOM_KEYS,
    MARCHWARD_POST_KEY,
    GALLOWS_MILE_KEY,
    REDOUBT_GATE_KEY,
    BLOCKADE_COMPLETE_FLAG,
    MORROWGATE_RAMPART_KEY,
    PALACE_APPROACH_KEY,
    REDOUBT_COMPLETE_FLAG,
    DESERTER_COMPLETE_FLAG,
    MORROWGATE_COUNCIL_KEY,
    REFUGEE_FORD_KEY,
    TRIBUNAL_YARD_KEY,
    DESERTER_ROAD_KEY,
    DISARMED_ROAD_KEY,
    TRIAL_ENDING_FLAG,
    EXILE_ENDING_FLAG,
    JUDGMENT_ENDING_FLAG,
)
from mud.midgame_depth import HIDDEN_ROOMS, NAMED_DEPTH_ITEMS
from mud.mechanics import class_abilities_for_level
from mud.room_engine import PlayerRoomContext
from mud.salt_kingdoms_midgame import CAPSTONE_COMPLETE_FLAG as SALT_COMPLETE, SALTWIND_GATE_KEY
from mud.world import ROOMS_BY_KEY

assert server.PlayerSession._upper_class_progression_installed
assert server.PlayerSession._midgame_depth_installed
assert server.PlayerSession._crownfire_31_40_installed

for room in HIDDEN_ROOMS:
    assert room.key in ROOMS_BY_KEY
    assert room.key in server.WORLD.legacy_rooms
for key in CROWNFIRE_ROOM_KEYS:
    assert key in ROOMS_BY_KEY, key
    assert key in server.WORLD.legacy_rooms, key
    assert server.WORLD.legacy_rooms[key].region_key in {
        "crownfire_march", "morrowgate", "gilded_redoubt", "banner_palace"
    }

for item in NAMED_DEPTH_ITEMS:
    assert item.key in crafting.ITEMS_BY_KEY

max_unlock = 0
for class_key in ("brute", "wizard", "druid", "necromancer"):
    max_unlock = max(max_unlock, max(a.unlock_level or 1 for a in class_abilities_for_level(class_key, 60)))
for deity_key in ("zerjz", "tenebrous", "leviathan"):
    max_unlock = max(max_unlock, max(a.unlock_level or 1 for a in class_abilities_for_level("priest", 60, deity_key)))
assert max_unlock == 30

low = PlayerRoomContext(1, "goblin", "priest", 30, frozenset({SALT_COMPLETE}))
assert "north" not in {e.direction for e in server.WORLD.build_view(SALTWIND_GATE_KEY, low).exits}
not_ready = PlayerRoomContext(1, "goblin", "priest", 31, frozenset())
assert "north" not in {e.direction for e in server.WORLD.build_view(SALTWIND_GATE_KEY, not_ready).exits}
ready = PlayerRoomContext(1, "goblin", "priest", 31, frozenset({SALT_COMPLETE}))
entry = server.WORLD.resolve_exit(SALTWIND_GATE_KEY, "north", ready)
assert entry.allowed and entry.exit.destination_key == MARCHWARD_POST_KEY

blocked_redoubt = PlayerRoomContext(1, "goblin", "priest", 34, frozenset())
assert "east" not in {e.direction for e in server.WORLD.build_view(GALLOWS_MILE_KEY, blocked_redoubt).exits}
open_redoubt = PlayerRoomContext(1, "goblin", "priest", 34, frozenset({BLOCKADE_COMPLETE_FLAG}))
redoubt = server.WORLD.resolve_exit(GALLOWS_MILE_KEY, "east", open_redoubt)
assert redoubt.allowed and redoubt.exit.destination_key == REDOUBT_GATE_KEY

blocked_palace = PlayerRoomContext(1, "goblin", "priest", 37, frozenset({REDOUBT_COMPLETE_FLAG}))
assert "east" not in {e.direction for e in server.WORLD.build_view(MORROWGATE_RAMPART_KEY, blocked_palace).exits}
open_palace = PlayerRoomContext(1, "goblin", "priest", 37, frozenset({REDOUBT_COMPLETE_FLAG, DESERTER_COMPLETE_FLAG}))
palace = server.WORLD.resolve_exit(MORROWGATE_RAMPART_KEY, "east", open_palace)
assert palace.allowed and palace.exit.destination_key == PALACE_APPROACH_KEY

trial = PlayerRoomContext(1, "goblin", "priest", 40, frozenset({TRIAL_ENDING_FLAG}))
trial_exit = server.WORLD.resolve_exit(MORROWGATE_COUNCIL_KEY, "west", trial)
assert trial_exit.allowed and trial_exit.exit.destination_key == TRIBUNAL_YARD_KEY
exile = PlayerRoomContext(1, "goblin", "priest", 40, frozenset({EXILE_ENDING_FLAG}))
exile_exit = server.WORLD.resolve_exit(REFUGEE_FORD_KEY, "west", exile)
assert exile_exit.allowed and exile_exit.exit.destination_key == DESERTER_ROAD_KEY
judgment = PlayerRoomContext(1, "goblin", "priest", 40, frozenset({JUDGMENT_ENDING_FLAG}))
judgment_exit = server.WORLD.resolve_exit(REDOUBT_GATE_KEY, "north", judgment)
assert judgment_exit.allowed and judgment_exit.exit.destination_key == DISARMED_ROAD_KEY

print(json.dumps({
    "rooms": len(CROWNFIRE_ROOM_KEYS),
    "max_unlock": max_unlock,
    "max_quest": max(q.minimum_level for q in quests.QUESTS_BY_KEY.values()),
    "production": "ok",
}))
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=90,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
        cls.production = json.loads(result.stdout.strip().splitlines()[-1])

    def test_actual_production_entrypoint_assembles_the_whole_new_band(self):
        self.assertEqual(self.production["rooms"], 33)
        self.assertEqual(self.production["max_unlock"], 30)
        self.assertEqual(self.production["max_quest"], 40)
        self.assertEqual(self.production["production"], "ok")


if __name__ == "__main__":
    unittest.main()
