from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.movement_system import (
    MOVEMENT_RULES,
    install_movement_runtime,
    maximum_movement_for_level,
    movement_cost_for_room,
    movement_state_name,
    recover_movement_once,
    spend_movement,
)


ROOT = Path(__file__).resolve().parents[1]


class _Exit:
    def __init__(self, direction: str, destination_key: str):
        self.direction = direction
        self.destination_key = destination_key

    def matches_direction(self, value: str) -> bool:
        return value.strip().lower() == self.direction


class _Scene:
    def __init__(self, key: str, name: str, tags=(), exits=(), features=()):
        self.key = key
        self.name = name
        self.tags = tuple(tags)
        self.exits = tuple(exits)
        self.features = tuple(features)


class _World:
    def __init__(self, scenes):
        self.scenes = {scene.key: scene for scene in scenes}

    def scene(self, key: str):
        return self.scenes.get(key)


class MovementRuleTests(unittest.TestCase):
    def test_fatigue_bands_match_player_facing_thresholds(self):
        self.assertEqual(movement_state_name(100), "Normal")
        self.assertEqual(movement_state_name(25), "Normal")
        self.assertEqual(movement_state_name(24), "Winded")
        self.assertEqual(movement_state_name(10), "Winded")
        self.assertEqual(movement_state_name(9), "Exhausted")
        self.assertEqual(movement_state_name(1), "Exhausted")
        self.assertEqual(movement_state_name(0), "Spent")

    def test_capacity_scales_by_level_not_grace(self):
        self.assertEqual(maximum_movement_for_level(1), 100)
        self.assertEqual(maximum_movement_for_level(10), 109)
        self.assertEqual(maximum_movement_for_level(40), 139)
        self.assertEqual(maximum_movement_for_level(10, bonus=7), 116)

    def test_terrain_costs_are_light_in_safe_places_and_harder_outside(self):
        world = _World(
            (
                _Scene("safe_swamp_view", "Floodgate Walk", tags=("safe", "swamp_view")),
                _Scene("king_road", "King's Road", tags=("road",)),
                _Scene("old_forest", "Old Forest", tags=("forest",)),
                _Scene("black_marsh", "Black Marsh", tags=("marsh",)),
                _Scene("deep_snow_pass", "Deep Snow Pass", tags=("deep_snow",)),
            )
        )
        self.assertEqual(movement_cost_for_room(world, "safe_swamp_view"), 1)
        self.assertEqual(movement_cost_for_room(world, "king_road"), 1)
        self.assertEqual(movement_cost_for_room(world, "old_forest"), 2)
        self.assertEqual(movement_cost_for_room(world, "black_marsh"), 3)
        self.assertEqual(movement_cost_for_room(world, "deep_snow_pass"), 4)

    def test_passive_rest_and_safe_rest_recovery_are_distinct(self):
        world = _World((_Scene("camp", "Way Camp", tags=("safe", "camp")),))
        combatant = SimpleNamespace(current_movement=50, max_movement=100)
        session = SimpleNamespace(
            character=SimpleNamespace(level=1, current_room="camp"),
            combatant=combatant,
            active_enemy=None,
            _movement_resting=False,
        )
        self.assertEqual(recover_movement_once(session, world), MOVEMENT_RULES.passive_recovery)
        session._movement_resting = True
        self.assertEqual(
            recover_movement_once(session, world),
            MOVEMENT_RULES.resting_recovery + MOVEMENT_RULES.restful_place_bonus,
        )
        session.active_enemy = object()
        self.assertEqual(recover_movement_once(session, world), 0)

    def test_spending_clamps_at_zero_instead_of_blocking_future_travel(self):
        session = SimpleNamespace(
            character=SimpleNamespace(level=1),
            combatant=SimpleNamespace(current_movement=2, max_movement=100),
        )
        spent, before, after = spend_movement(session, 4)
        self.assertEqual(spent, 2)
        self.assertEqual(session.combatant.current_movement, 0)
        self.assertEqual(before, "Exhausted")
        self.assertEqual(after, "Spent")


class _DummyTelnet:
    def __init__(self):
        self.gmcp_enabled = True
        self.packets = []

    async def send_gmcp(self, package, payload):
        self.packets.append((package, payload))
        return True


class _DummySession:
    def __init__(self):
        self.character = SimpleNamespace(id=1, level=1, current_room="town")
        self.combatant = SimpleNamespace(current_movement=100, max_movement=100)
        self.active_enemy = None
        self._movement_resting = False
        self.messages = []
        self.state = SimpleNamespace(DISCONNECTED="disconnected")
        self.telnet = _DummyTelnet()
        self.next_command = ""
        self.closed = False

    async def send(self, text):
        self.messages.append(text)

    async def prompt(self, _text):
        return self.next_command

    async def enter_character(self):
        return None

    async def move_character(self, direction):
        if self.character.current_room == "town" and direction == "north":
            self.character.current_room = "forest"
        elif self.character.current_room == "forest" and direction == "south":
            self.character.current_room = "town"

    async def attempt_flee(self):
        return None

    def _available_flee_exits(self):
        return [("south", "town")]

    async def start_combat(self, _target_text):
        self.active_enemy = object()

    async def start_mobile_npc_combat(self, _npc_key, *, initiated_by_npc=False):
        self.active_enemy = object()
        return True

    async def playing_prompt(self):
        self.messages.append("delegated")

    async def send_client_state(self):
        return None

    async def close(self):
        self.closed = True


class MovementRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # The installer mutates a class, so give every test a fresh subclass.
        self.Session = type("MovementSession", (_DummySession,), {})
        self.world = _World(
            (
                _Scene("town", "Town Street", tags=("safe", "street"), exits=(_Exit("north", "forest"),)),
                _Scene("forest", "Old Forest", tags=("forest",), exits=(_Exit("south", "town"),)),
            )
        )
        install_movement_runtime(self.Session, self.world)

    async def test_successful_room_change_spends_destination_terrain_cost(self):
        session = self.Session()
        await session.move_character("north")
        self.assertEqual(session.character.current_room, "forest")
        self.assertEqual(session.combatant.current_movement, 98)

        before = session.combatant.current_movement
        await session.move_character("west")
        self.assertEqual(session.character.current_room, "forest")
        self.assertEqual(session.combatant.current_movement, before)

    async def test_flee_attempt_costs_movement_even_when_it_does_not_move(self):
        session = self.Session()
        session.active_enemy = object()
        await session.attempt_flee()
        self.assertEqual(session.combatant.current_movement, 94)

    async def test_rest_command_is_real_and_safe_room_rest_is_faster(self):
        session = self.Session()
        session.next_command = "rest"
        await session.playing_prompt()
        self.assertTrue(session._movement_resting)
        self.assertTrue(any("Movement will recover much faster" in line for line in session.messages))
        gained = recover_movement_once(session, self.world)
        self.assertEqual(gained, 0)  # already full
        session.combatant.current_movement = 50
        self.assertEqual(
            recover_movement_once(session, self.world),
            MOVEMENT_RULES.resting_recovery + MOVEMENT_RULES.restful_place_bonus,
        )
        await session.close()

    async def test_gmcp_gets_structured_movement_state(self):
        session = self.Session()
        session.combatant.current_movement = 8
        await session.send_client_state()
        packets = [payload for package, payload in session.telnet.packets if package == "Dreams.Movement"]
        self.assertTrue(packets)
        self.assertEqual(packets[-1]["state"], "Exhausted")
        self.assertEqual(packets[-1]["current"], 8)


class ProductionMovementContractTests(unittest.TestCase):
    def test_production_entrypoint_installs_real_movement_runtime(self):
        code = r'''
import server
from mud.movement_system import movement_cost_for_room

assert server.PlayerSession._movement_runtime_installed
assert movement_cost_for_room(server.WORLD, "goblin_clattergate") == 1
print("MOVEMENT_RUNTIME_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("MOVEMENT_RUNTIME_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
