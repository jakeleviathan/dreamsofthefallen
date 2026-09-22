from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from mud.combat_grind import (
    HUNT_CHAIN_WINDOW_SECONDS,
    HuntChainState,
    chain_bonus_percent,
    install_combat_grind_runtime,
)
from mud.npcs import MobileNpcManager, RegionalSpawnDefinition
from mud.world import ROOMS_BY_KEY


class HuntChainTests(unittest.TestCase):
    def test_bonus_tiers_are_small_and_capped(self):
        self.assertEqual(chain_bonus_percent(1), 0)
        self.assertEqual(chain_bonus_percent(2), 0)
        self.assertEqual(chain_bonus_percent(3), 5)
        self.assertEqual(chain_bonus_percent(6), 10)
        self.assertEqual(chain_bonus_percent(10), 15)
        self.assertEqual(chain_bonus_percent(100), 15)

    def test_chain_resets_on_region_change_or_timeout(self):
        state = HuntChainState()
        self.assertEqual(state.record(7, "fen", 100.0), 1)
        self.assertEqual(state.record(7, "fen", 120.0), 2)
        self.assertEqual(state.record(7, "ridge", 130.0), 1)
        self.assertEqual(
            state.record(7, "ridge", 130.0 + HUNT_CHAIN_WINDOW_SECONDS + 1.0),
            1,
        )
        self.assertEqual(state.record(8, "ridge", 132.0 + HUNT_CHAIN_WINDOW_SECONDS), 1)


class HuntingDensityTests(unittest.TestCase):
    def test_room_capacity_grows_from_two_to_six_with_depth(self):
        manager = object.__new__(MobileNpcManager)
        pool = RegionalSpawnDefinition(
            key="test:rat",
            region_key="test",
            enemy_key="rat",
            room_keys=("edge", "one", "two", "three", "deep"),
            source_room_keys=("edge",),
        )
        manager.regional_pools = {pool.key: pool}
        manager._regional_room_depths = {
            pool.key: {
                "edge": 0,
                "one": 1,
                "two": 2,
                "three": 3,
                "deep": 4,
            }
        }

        self.assertEqual(manager.hunting_room_capacity("edge"), 2)
        self.assertEqual(manager.hunting_room_capacity("one"), 3)
        self.assertEqual(manager.hunting_room_capacity("two"), 4)
        self.assertEqual(manager.hunting_room_capacity("three"), 5)
        self.assertEqual(manager.hunting_room_capacity("deep"), 6)

    def test_spawn_choice_prefers_deeper_hunting_ground_and_avoids_players(self):
        manager = object.__new__(MobileNpcManager)
        pool = RegionalSpawnDefinition(
            key="test:rat",
            region_key="test",
            enemy_key="rat",
            room_keys=("edge", "deep"),
            source_room_keys=("edge",),
        )
        manager.states = {}
        manager._regional_instance_to_pool = {}
        manager._regional_room_depths = {pool.key: {"edge": 0, "deep": 4}}

        class HighestWeightRandom:
            @staticmethod
            def choices(population, *, weights, k):
                return [population[weights.index(max(weights))]]

        selected = manager._choose_regional_spawn_room(
            pool,
            player_room_keys=(),
            rng=HighestWeightRandom(),
        )
        self.assertEqual(selected, "deep")

        hidden_selected = manager._choose_regional_spawn_room(
            pool,
            player_room_keys=("deep",),
            rng=HighestWeightRandom(),
        )
        self.assertEqual(hidden_selected, "edge")


class RuntimeRewardTests(unittest.TestCase):
    def setUp(self):
        self.room_key = "test_combat_grind_room"
        self.original_room = ROOMS_BY_KEY.get(self.room_key)
        ROOMS_BY_KEY[self.room_key] = SimpleNamespace(
            key=self.room_key,
            region_key="test_hunt_region",
            exits={},
            tags=("wilderness", "hunt"),
        )

    def tearDown(self):
        if self.original_room is None:
            ROOMS_BY_KEY.pop(self.room_key, None)
        else:
            ROOMS_BY_KEY[self.room_key] = self.original_room

    def test_third_timely_hunting_kill_gets_bonus_xp(self):
        character = SimpleNamespace(
            id=1,
            name="Hunter",
            level=1,
            experience=0,
            current_room=self.room_key,
        )

        class FakeDatabase:
            def __init__(self, record):
                self.record = record

            def add_experience(self, character_id, amount):
                assert character_id == self.record.id
                self.record.experience += int(amount)
                return self.record.level

            def get_character_by_name(self, name):
                assert name == self.record.name
                return self.record

        class FakeManager:
            def __init__(self):
                self.states = {}
                self._regional_instance_to_pool = {}
                self.pressure = 0

            def is_hunting_room(self, room_key):
                return room_key == self_room_key

            def note_hunt_kill(self, region_key):
                assert region_key == "test_hunt_region"
                self.pressure += 1

        self_room_key = self.room_key

        class Session:
            async def _finish_enemy_defeat(self, enemy):
                if self.active_enemy is not enemy:
                    return
                self.database.add_experience(self.character.id, enemy.definition.xp_reward)
                self.character = self.database.get_character_by_name(self.character.name)
                self.active_enemy = None

        install_combat_grind_runtime(Session)

        session = Session()
        session.character = character
        session.database = FakeDatabase(character)
        session.mobile_npcs = FakeManager()
        session.active_mobile_npc_key = None
        session.outputs = []

        async def send(text):
            session.outputs.append(text)

        session.send = send

        definition = SimpleNamespace(
            key="test_rat",
            name="Test Rat",
            xp_reward=20,
            tutorial=False,
        )

        for _ in range(3):
            enemy = SimpleNamespace(definition=definition)
            session.active_enemy = enemy
            asyncio.run(session._finish_enemy_defeat(enemy))

        self.assertEqual(character.experience, 61)
        self.assertEqual(session.mobile_npcs.pressure, 3)
        self.assertIn("Hunting chain 3: +1 bonus experience", "".join(session.outputs))

    def test_party_members_build_momentum_from_their_actual_xp_share(self):
        records = {
            1: SimpleNamespace(
                id=1,
                name="Hunter",
                level=1,
                experience=0,
                current_room=self.room_key,
            ),
            2: SimpleNamespace(
                id=2,
                name="Companion",
                level=1,
                experience=0,
                current_room=self.room_key,
            ),
        }

        class SharedDatabase:
            def add_experience(self, character_id, amount):
                record = records[int(character_id)]
                record.experience += int(amount)
                return record.level

            def get_character_by_name(self, name):
                return next(record for record in records.values() if record.name == name)

        class FakeManager:
            def __init__(self):
                self.states = {}
                self._regional_instance_to_pool = {}
                self.pressure = 0

            def is_hunting_room(self, room_key):
                return room_key == self_room_key

            def note_hunt_kill(self, region_key):
                self.pressure += 1

        self_room_key = self.room_key
        shared_database = SharedDatabase()
        shared_manager = FakeManager()

        class PartySession:
            def party_victory_sessions(self, enemy):
                return tuple(self.participants)

            async def _finish_enemy_defeat(self, enemy):
                # Model the already-installed party runtime: both participants
                # receive their real share before the outer hunting wrapper runs.
                for member in self.participants:
                    member.database.add_experience(member.character.id, 20)
                    member.character = member.database.get_character_by_name(
                        member.character.name
                    )
                    member.active_enemy = None

        install_combat_grind_runtime(PartySession)

        hunter = PartySession()
        companion = PartySession()
        hunter.character = records[1]
        companion.character = records[2]
        for member in (hunter, companion):
            member.database = shared_database
            member.mobile_npcs = shared_manager
            member.active_mobile_npc_key = None
            member.outputs = []

            async def send(text, *, target=member):
                target.outputs.append(text)

            member.send = send
        hunter.participants = [hunter, companion]
        companion.participants = hunter.participants

        definition = SimpleNamespace(
            key="test_rat",
            name="Test Rat",
            xp_reward=40,
            tutorial=False,
        )
        for _ in range(3):
            enemy = SimpleNamespace(definition=definition)
            hunter.active_enemy = enemy
            companion.active_enemy = enemy
            asyncio.run(hunter._finish_enemy_defeat(enemy))

        self.assertEqual(records[1].experience, 61)
        self.assertEqual(records[2].experience, 61)
        self.assertEqual(shared_manager.pressure, 3)
        self.assertIn("Hunting chain 3: +1 bonus experience", "".join(hunter.outputs))
        self.assertIn("Hunting chain 3: +1 bonus experience", "".join(companion.outputs))


if __name__ == "__main__":
    unittest.main()
