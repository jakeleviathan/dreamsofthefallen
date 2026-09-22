from __future__ import annotations

import os
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.combat as combat
import mud.npcs as npcs
from mud.combat import EnemyDefinition
from mud.npcs import MobileNpcManager
from mud.world import ROOMS_BY_KEY, RoomDefinition


ROOT = Path(__file__).resolve().parents[1]


def _jackal_enemy() -> EnemyDefinition:
    return EnemyDefinition(
        key="field_jackal",
        name="Field Jackal",
        aliases=("jackal", "field jackal"),
        description="a lean dust-colored jackal watching the road for an easy meal",
        max_hp=24,
        armor_class=4,
        auto_attack_damage=3,
        auto_attack_interval=2.8,
        xp_reward=24,
        retaliates=True,
        tutorial=False,
    )


def _regional_rooms() -> dict[str, RoomDefinition]:
    return {
        "wild_a": RoomDefinition(
            key="wild_a",
            name="Jackal Scrub",
            description="Dry scrub and old tracks.",
            region_key="test_frontier",
            exits={"east": "wild_b"},
            enemy_keys=("field_jackal",),
            tags=("wilderness", "light_danger"),
        ),
        "wild_b": RoomDefinition(
            key="wild_b",
            name="Dust Track",
            description="A narrow track through thorn grass.",
            region_key="test_frontier",
            exits={"west": "wild_a", "east": "wild_c", "north": "safe_inn"},
            tags=("wilderness", "road"),
        ),
        "wild_c": RoomDefinition(
            key="wild_c",
            name="Dry Wash",
            description="A shallow wash cut through hard dirt.",
            region_key="test_frontier",
            exits={"west": "wild_b"},
            tags=("wilderness", "hunting"),
        ),
        "safe_inn": RoomDefinition(
            key="safe_inn",
            name="Roadside Inn",
            description="A warm public house.",
            region_key="test_frontier",
            exits={"south": "wild_b"},
            tags=("safe", "social", "inn"),
        ),
    }


class RegionalPopulationTests(unittest.TestCase):
    def _manager(self) -> MobileNpcManager:
        self.room_patch = patch.dict(ROOMS_BY_KEY, _regional_rooms(), clear=True)
        self.enemy_patch = patch.dict(
            combat.ENEMIES_BY_KEY,
            {"field_jackal": _jackal_enemy()},
            clear=True,
        )
        self.room_patch.start()
        self.enemy_patch.start()
        self.addCleanup(self.room_patch.stop)
        self.addCleanup(self.enemy_patch.stop)
        return MobileNpcManager(definitions=())

    def test_region_seeds_multiple_shared_roamers_without_entering_safe_rooms(self):
        manager = self._manager()
        self.assertEqual(len(manager.regional_pools), 1)
        pool = next(iter(manager.regional_pools.values()))
        self.assertEqual(pool.enemy_key, "field_jackal")
        self.assertEqual(set(pool.room_keys), {"wild_a", "wild_b", "wild_c"})
        states = manager._regional_states(pool.key, include_rare=False)
        self.assertEqual(len(states), npcs.REGIONAL_BASE_POPULATION)
        self.assertTrue(all(state.definition.attackable for state in states))
        self.assertTrue(all(state.definition.combat_enemy_key == "field_jackal" for state in states))
        self.assertNotIn("safe_inn", {state.current_room_key for state in states})

    def test_population_scales_gently_with_multiple_players_and_respects_cap(self):
        manager = self._manager()
        pool = next(iter(manager.regional_pools.values()))
        self.assertEqual(
            manager.target_population(pool, ("wild_a", "wild_b")),
            min(pool.max_population, npcs.REGIONAL_BASE_POPULATION + 2),
        )

        with patch.object(npcs, "REGIONAL_RARE_ROLL_PER_TICK", 0.0):
            for tick in range(1, 8):
                manager.tick(
                    random.Random(tick),
                    player_room_keys=("wild_a", "wild_b"),
                    hour=12,
                )

        common = manager._regional_states(pool.key, include_rare=False)
        self.assertEqual(
            len(common),
            min(pool.max_population, npcs.REGIONAL_BASE_POPULATION + 2),
        )
        self.assertLessEqual(
            len(manager._regional_states(pool.key)),
            manager._region_dynamic_cap(pool.region_key),
        )

    def test_ecology_owns_carrying_capacity_and_records_hunting_pressure(self):
        class FakeEcology:
            def __init__(self):
                self.kills = []

            def creature_population_multiplier(self, region_key, definition):
                self.last_region = region_key
                self.last_definition = definition.key
                return 0.55

            def record_creature_kill(self, region_key, definition):
                self.kills.append((region_key, definition.combat_enemy_key))

        manager = self._manager()
        ecology = FakeEcology()
        manager.ecology = ecology
        pool = next(iter(manager.regional_pools.values()))

        # Active players no longer manufacture wildlife when ecology is enabled.
        self.assertEqual(
            manager.target_population(pool, ("wild_a", "wild_b", "wild_c")),
            1,
        )
        self.assertEqual(ecology.last_region, "test_frontier")
        self.assertEqual(ecology.last_definition, "field_jackal")

        victim = manager._regional_states(pool.key, include_rare=False)[0]
        manager.defeat(victim.definition.key)
        self.assertEqual(ecology.kills, [("test_frontier", "field_jackal")])

    def test_kill_reduces_shared_count_then_refills_out_of_sight_after_cooldown(self):
        manager = self._manager()
        pool = next(iter(manager.regional_pools.values()))
        victim = manager._regional_states(pool.key, include_rare=False)[0]
        old_keys = set(manager.states)

        manager.defeat(victim.definition.key)
        self.assertEqual(
            len(manager._regional_states(pool.key, include_rare=False)),
            npcs.REGIONAL_BASE_POPULATION - 1,
        )

        with patch.object(npcs, "REGIONAL_RARE_ROLL_PER_TICK", 0.0):
            for tick in range(1, npcs.REGIONAL_REFILL_TICKS):
                manager.tick(
                    random.Random(100 + tick),
                    player_room_keys=("wild_a",),
                    hour=12,
                )
        self.assertEqual(
            len(manager._regional_states(pool.key, include_rare=False)),
            npcs.REGIONAL_BASE_POPULATION - 1,
        )

        manager.tick(
            random.Random(999),
            player_room_keys=("wild_a",),
            hour=12,
        )
        new_keys = set(manager.states).difference(old_keys)
        self.assertTrue(new_keys)
        replacement = manager.states[next(iter(new_keys))]
        self.assertNotEqual(replacement.current_room_key, "wild_a")

    def test_rare_roll_creates_one_tough_aggressive_passing_threat(self):
        manager = self._manager()
        base = combat.ENEMIES_BY_KEY["field_jackal"]

        with patch.object(npcs, "REGIONAL_RARE_ROLL_PER_TICK", 1.0):
            manager.tick(
                random.Random(5),
                player_room_keys=("wild_a",),
                hour=12,
            )

        rares = [
            state for state in manager.states.values()
            if bool(getattr(state.definition, "rare", False))
        ]
        self.assertEqual(len(rares), 1)
        rare = rares[0]
        self.assertTrue(rare.definition.aggressive)
        self.assertTrue(rare.definition.attackable)
        self.assertEqual(rare.definition.combat_enemy_key, base.key)
        self.assertGreater(rare.definition.max_hp, base.max_hp)
        self.assertGreater(rare.definition.xp_reward, base.xp_reward)
        self.assertNotEqual(rare.current_room_key, "wild_a")


class ProductionRegionalPopulationContractTests(unittest.TestCase):
    def test_production_assembly_builds_regional_goblin_hunting_pools(self):
        code = r"""
import server
from mud.npcs import MobileNpcManager

manager = MobileNpcManager()
pools = tuple(manager.regional_pools.values())
assert any(pool.enemy_key == "mire_tick_swarm" for pool in pools)
assert any(pool.enemy_key == "bog_snapper" for pool in pools)
assert any(
    state.definition.attackable and state.definition.combat_enemy_key == "mire_tick_swarm"
    for state in manager.states.values()
)
print("REGIONAL_SPAWNS_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("REGIONAL_SPAWNS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
