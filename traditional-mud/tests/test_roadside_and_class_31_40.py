from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import mud.late_class_progression as late
import mud.roadside_discoveries as roadside


class LateClassDesignTests(unittest.TestCase):
    def test_every_class_gets_a_fixed_32_35_38_40_progression(self):
        self.assertEqual([ability.unlock_level for ability in late.BRUTE_LATE_ABILITIES], [32, 35, 38, 40])
        self.assertEqual([ability.unlock_level for ability in late.WIZARD_LATE_ABILITIES], [32, 35, 38, 40])
        self.assertEqual([ability.unlock_level for ability in late.DRUID_LATE_ABILITIES], [32, 35, 38, 40])
        self.assertEqual([ability.unlock_level for ability in late.NECROMANCER_LATE_ABILITIES], [32, 35, 38, 40])
        self.assertEqual(late.PRIEST_COMMON_LATE[0].unlock_level, 32)
        for deity_key in ("zerjz", "tenebrous", "leviathan"):
            self.assertEqual([ability.unlock_level for ability in late.PRIEST_PATH_LATE[deity_key]], [35, 38, 40])

    def test_level_forty_capstones_keep_the_five_class_identities_distinct(self):
        self.assertEqual(late.BRUTE_LATE_ABILITIES[-1].name, "Holdfast")
        self.assertEqual(late.WIZARD_LATE_ABILITIES[-1].name, "Starfall Equation")
        self.assertEqual(late.DRUID_LATE_ABILITIES[-1].name, "Old Growth")
        self.assertEqual(late.NECROMANCER_LATE_ABILITIES[-1].name, "Deathless Hour")
        self.assertEqual(late.PRIEST_PATH_LATE["zerjz"][-1].name, "Abundant Grace")
        self.assertEqual(late.PRIEST_PATH_LATE["tenebrous"][-1].name, "Citadel Prayer")
        self.assertEqual(late.PRIEST_PATH_LATE["leviathan"][-1].name, "Wrath Made Plain")


class RoadsideDiscoveryDesignTests(unittest.TestCase):
    def test_four_optional_pockets_are_small_and_spread_across_the_midgame(self):
        self.assertEqual(len(roadside.FIFTY_ROOM_KEYS), 4)
        self.assertEqual(len(roadside.QUIET_BELL_ROOM_KEYS), 4)
        self.assertEqual(len(roadside.BLUE_SINK_ROOM_KEYS), 5)
        self.assertEqual(len(roadside.NOONWATCH_ROOM_KEYS), 4)
        self.assertEqual(len(roadside.ROADSIDE_ROOM_KEYS), 17)
        self.assertEqual(len(roadside.ROADSIDE_QUESTS), 4)
        self.assertEqual(len(roadside.ROADSIDE_ITEMS), 4)
        self.assertTrue(all(quest.style == "freeform" for quest in roadside.ROADSIDE_QUESTS))
        self.assertTrue(all("optional_discovery" in room.tags for room in roadside.ROADSIDE_ROOMS))

    def test_pockets_are_not_four_more_boss_dungeons(self):
        self.assertTrue(all(not room.enemy_keys for room in roadside.ROADSIDE_ROOMS))
        names = {room.name for room in roadside.ROADSIDE_ROOMS}
        self.assertIn("Hall of Fifty Chairs", names)
        self.assertIn("Quiet Belfry", names)
        self.assertIn("The Dry Table", names)
        self.assertIn("Noonwatch Platform", names)

    def test_keepsakes_are_curios_not_a_new_loot_tier(self):
        self.assertEqual(
            {item.name for item in roadside.ROADSIDE_ITEMS},
            {"Blank-Wall Admission Stub", "Silent Watch Rivet", "Blue Salt Shell", "Noonwatch Lens"},
        )
        self.assertTrue(all(item.category == "curio" for item in roadside.ROADSIDE_ITEMS))
        self.assertTrue(all(item.equipment is None for item in roadside.ROADSIDE_ITEMS))


class ProductionRoadsideAndLateClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import asyncio
import json
from types import SimpleNamespace

import server
from mud.combat import EnemyDefinition, EnemyState
from mud.frontier_convergence import ASHCROSS_SUNKEN_WATCH_KEY
from mud.broken_reach_midgame import FAR_WATCH_KEY
from mud.crownfire_march_31_40 import WINDMILL_SCAR_KEY
from mud.mechanics import CombatantState, class_abilities_for_level
from mud.roadside_discoveries import (
    ROADSIDE_ROOM_KEYS,
    FIFTY_CRAWL_KEY,
    QUIET_STAIR_KEY,
    BLUE_RIM_KEY,
    NOON_PATH_KEY,
)
from mud.room_engine import PlayerRoomContext
from mud.salt_kingdoms_midgame import PILGRIM_SALT_KEY, CURRENT_ENDING_FLAG, SPRINGCUT_GORGE_KEY
from mud.stats import CharacterStats
from mud.world import ROOMS_BY_KEY
import mud.late_class_progression as late

assert server.PlayerSession._late_class_progression_installed
assert server.PlayerSession._roadside_discoveries_installed

for key in ROADSIDE_ROOM_KEYS:
    assert key in ROOMS_BY_KEY, key
    assert key in server.WORLD.legacy_rooms, key

# Static routes exist for the legacy movement writer, while the advanced WORLD
# owns player-facing level gates.
assert ROOMS_BY_KEY[ASHCROSS_SUNKEN_WATCH_KEY].exits["down"] == FIFTY_CRAWL_KEY
assert ROOMS_BY_KEY[FAR_WATCH_KEY].exits["up"] == QUIET_STAIR_KEY
assert ROOMS_BY_KEY[PILGRIM_SALT_KEY].exits["east"] == BLUE_RIM_KEY
assert ROOMS_BY_KEY[WINDMILL_SCAR_KEY].exits["up"] == NOON_PATH_KEY

low = PlayerRoomContext(1, "human", "wizard", 14, frozenset())
assert not server.WORLD.resolve_exit(ASHCROSS_SUNKEN_WATCH_KEY, "down", low).allowed
ready = PlayerRoomContext(1, "human", "wizard", 15, frozenset())
entry = server.WORLD.resolve_exit(ASHCROSS_SUNKEN_WATCH_KEY, "down", ready)
assert entry.allowed and entry.exit.destination_key == FIFTY_CRAWL_KEY

blue_low = PlayerRoomContext(1, "human", "wizard", 24, frozenset())
assert not server.WORLD.resolve_exit(PILGRIM_SALT_KEY, "east", blue_low).allowed
blue_ready = PlayerRoomContext(1, "human", "wizard", 25, frozenset())
blue_entry = server.WORLD.resolve_exit(PILGRIM_SALT_KEY, "east", blue_ready)
assert blue_entry.allowed and blue_entry.exit.destination_key == BLUE_RIM_KEY

# The new Blue Salt route must not steal Whitewake's existing post-capstone gorge.
current = PlayerRoomContext(1, "human", "wizard", 30, frozenset({CURRENT_ENDING_FLAG}))
gorge = server.WORLD.resolve_exit(PILGRIM_SALT_KEY, "down", current)
assert gorge.allowed and gorge.exit.destination_key == SPRINGCUT_GORGE_KEY

max_unlock = 0
for class_key in ("brute", "wizard", "druid", "necromancer"):
    max_unlock = max(max_unlock, max(a.unlock_level or 1 for a in class_abilities_for_level(class_key, 60)))
for deity_key in ("zerjz", "tenebrous", "leviathan"):
    max_unlock = max(max_unlock, max(a.unlock_level or 1 for a in class_abilities_for_level("priest", 60, deity_key)))
assert max_unlock == 40

# Prove the Wizard's late sequence is executable and materially rewards setup.
def wizard_session():
    enemy = EnemyState(EnemyDefinition(
        key="late_test_target",
        name="Late Test Target",
        aliases=("target",),
        description="a durable target",
        max_hp=5000,
        armor_class=0,
        auto_attack_damage=0,
        auto_attack_interval=99.0,
        xp_reward=0,
        retaliates=False,
        tutorial=True,
    ))
    class Session:
        def __init__(self):
            self.character = SimpleNamespace(id=1, name="Sequence", race="human", character_class="wizard", deity_key=None, level=40)
            self.combatant = CombatantState(
                character_id=1,
                race_key="human",
                current_hp=200,
                max_hp=200,
                current_mana=500,
                max_mana=500,
                auto_attack_interval=2.0,
                stats=CharacterStats(mind=12),
            )
            self.active_enemy = enemy
            self.ward_until = 0.0
            self.messages = []
        async def send(self, text):
            self.messages.append(text)
        async def send_client_state(self):
            return None
        async def _finish_enemy_defeat(self, enemy):
            raise AssertionError("test target should survive")
    return Session(), enemy

async def prepared_damage():
    session, enemy = wizard_session()
    await late._use_late(session, "returning_glyph")
    await late._use_late(session, "prismatic_lance")
    before = enemy.current_hp
    await late._use_late(session, "starfall_equation")
    return before - enemy.current_hp

async def unprepared_damage():
    session, enemy = wizard_session()
    before = enemy.current_hp
    await late._use_late(session, "starfall_equation")
    return before - enemy.current_hp

prepared = asyncio.run(prepared_damage())
unprepared = asyncio.run(unprepared_damage())
assert prepared > unprepared

print(json.dumps({
    "rooms": len(ROADSIDE_ROOM_KEYS),
    "max_unlock": max_unlock,
    "prepared": prepared,
    "unprepared": unprepared,
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

    def test_actual_production_entrypoint_installs_both_passes(self):
        self.assertEqual(self.production["rooms"], 17)
        self.assertEqual(self.production["max_unlock"], 40)
        self.assertGreater(self.production["prepared"], self.production["unprepared"])
        self.assertEqual(self.production["production"], "ok")


if __name__ == "__main__":
    unittest.main()
