from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.combat import EnemyState, SEWER_RAT
from mud.database import Database
from mud.enemy_lifecycle import (
    bind_enemy_lifecycle_database,
    clear_static_enemy_respawn,
    install_enemy_lifecycle_runtime,
    mark_static_enemy_defeated,
    respawn_seconds_for,
    static_enemy_available,
    static_enemy_respawn_remaining,
)
from mud.waymeet_adventure_arc import CELLAR_RAT, TOLL_RAT_RUN
from mud.world import ROOMS_BY_KEY


class EnemyLifecycleStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "enemy-lifecycle.db"
        self.database = Database(self.path)

    def test_defeat_persists_until_respawn_then_expires_lazily(self):
        self.assertTrue(
            mark_static_enemy_defeated(
                self.database,
                "test_room",
                "test_enemy",
                120.0,
                now=1_000.0,
            )
        )
        self.assertFalse(
            static_enemy_available(
                "test_room", "test_enemy", database=self.database, now=1_119.9
            )
        )
        self.assertAlmostEqual(
            static_enemy_respawn_remaining(
                "test_room", "test_enemy", database=self.database, now=1_060.0
            ),
            60.0,
        )

        reopened = Database(self.path)
        self.assertFalse(
            static_enemy_available(
                "test_room", "test_enemy", database=reopened, now=1_119.9
            )
        )
        self.assertTrue(
            static_enemy_available(
                "test_room", "test_enemy", database=reopened, now=1_120.0
            )
        )
        self.assertEqual(
            static_enemy_respawn_remaining(
                "test_room", "test_enemy", database=reopened, now=1_120.0
            ),
            0.0,
        )

    def test_second_concurrent_defeat_cannot_claim_same_spawn_twice(self):
        self.assertTrue(
            mark_static_enemy_defeated(
                self.database, "shared_room", "shared_enemy", 120.0, now=500.0
            )
        )
        self.assertFalse(
            mark_static_enemy_defeated(
                self.database, "shared_room", "shared_enemy", 120.0, now=501.0
            )
        )
        self.assertFalse(
            static_enemy_available(
                "shared_room", "shared_enemy", database=self.database, now=501.0
            )
        )

    def test_clear_restores_spawn_immediately(self):
        mark_static_enemy_defeated(
            self.database, "test_room", "test_enemy", 120.0, now=100.0
        )
        clear_static_enemy_respawn(self.database, "test_room", "test_enemy")
        self.assertTrue(
            static_enemy_available(
                "test_room", "test_enemy", database=self.database, now=101.0
            )
        )

    def test_respawn_policy_is_shorter_for_tutorial_enemies(self):
        self.assertEqual(respawn_seconds_for(SEWER_RAT), 60.0)


class RuntimeSession:
    def __init__(self, database: Database, room_key: str):
        self.database = database
        self.character = SimpleNamespace(id=1, current_room=room_key)
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.outputs: list[str] = []
        self.base_start_calls = 0
        self.base_finish_calls = 0
        self.stop_calls = 0
        self.state_pushes = 0

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        self.state_pushes += 1

    async def _stop_combat(self):
        self.stop_calls += 1
        self.active_enemy = None

    def _enemy_in_current_room(self, target_text: str):
        room = ROOMS_BY_KEY.get(self.character.current_room)
        if room is None:
            return None
        for enemy_key in room.enemy_keys:
            from mud.combat import ENEMIES_BY_KEY
            definition = ENEMIES_BY_KEY.get(enemy_key)
            if definition is not None and definition.matches(target_text):
                return EnemyState(definition)
        return None

    async def start_combat(self, target_text: str):
        self.base_start_calls += 1
        enemy = self._enemy_in_current_room(target_text)
        if enemy is not None:
            self.active_enemy = enemy

    async def _finish_enemy_defeat(self, enemy):
        self.base_finish_calls += 1
        self.active_enemy = None

    async def show_current_room(self):
        await self.send("Vermin Pens\r\n")
        await self.send(f"\r\n{SEWER_RAT.name} is here, {SEWER_RAT.description}.\r\n")


class EnemyLifecycleRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_enemy_lifecycle_runtime(RuntimeSession)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Database(Path(self.temp.name) / "runtime.db")
        self.room_key = next(
            room.key for room in ROOMS_BY_KEY.values() if "sewer_rat" in room.enemy_keys
        )
        bind_enemy_lifecycle_database(self.database)

    def test_defeated_static_enemy_cannot_be_targeted_or_restarted(self):
        session = RuntimeSession(self.database, self.room_key)
        mark_static_enemy_defeated(
            self.database,
            self.room_key,
            SEWER_RAT.key,
            120.0,
        )

        self.assertIsNone(session._enemy_in_current_room("rat"))
        asyncio.run(session.start_combat("rat"))
        self.assertEqual(session.base_start_calls, 0)
        self.assertIn("has not respawned yet", "".join(session.outputs))

    def test_first_kill_claims_spawn_and_second_session_gets_no_second_kill(self):
        first = RuntimeSession(self.database, self.room_key)
        first_enemy = EnemyState(SEWER_RAT)
        first.active_enemy = first_enemy
        asyncio.run(first._finish_enemy_defeat(first_enemy))
        self.assertEqual(first.base_finish_calls, 1)
        self.assertFalse(
            static_enemy_available(
                self.room_key, SEWER_RAT.key, database=self.database
            )
        )

        second = RuntimeSession(self.database, self.room_key)
        second_enemy = EnemyState(SEWER_RAT)
        second.active_enemy = second_enemy
        asyncio.run(second._finish_enemy_defeat(second_enemy))
        self.assertEqual(second.base_finish_calls, 0)
        self.assertEqual(second.stop_calls, 1)
        self.assertIn("no second kill to claim", "".join(second.outputs))

    def test_duplicate_static_enemies_are_independent_spawns(self):
        session = RuntimeSession(self.database, TOLL_RAT_RUN)

        first = session._enemy_in_current_room("rat")
        self.assertIsNotNone(first)
        self.assertEqual(first.definition.key, CELLAR_RAT.key)
        self.assertEqual(first.spawn_key, CELLAR_RAT.key)

        session.active_enemy = first
        asyncio.run(session._finish_enemy_defeat(first))
        self.assertFalse(
            static_enemy_available(
                TOLL_RAT_RUN, CELLAR_RAT.key, database=self.database
            )
        )
        self.assertTrue(
            static_enemy_available(
                TOLL_RAT_RUN, CELLAR_RAT.key + "#2", database=self.database
            )
        )

        second = session._enemy_in_current_room("rat")
        self.assertIsNotNone(second)
        self.assertEqual(second.definition.key, CELLAR_RAT.key)
        self.assertEqual(second.spawn_key, CELLAR_RAT.key + "#2")

        session.active_enemy = second
        asyncio.run(session._finish_enemy_defeat(second))
        self.assertFalse(
            static_enemy_available(
                TOLL_RAT_RUN, CELLAR_RAT.key + "#2", database=self.database
            )
        )
        self.assertIsNone(session._enemy_in_current_room("rat"))

    def test_legacy_room_output_hides_defeated_enemy(self):
        session = RuntimeSession(self.database, self.room_key)
        mark_static_enemy_defeated(
            self.database,
            self.room_key,
            SEWER_RAT.key,
            120.0,
        )
        asyncio.run(session.show_current_room())
        output = "".join(session.outputs)
        self.assertIn("Vermin Pens", output)
        self.assertNotIn("Sewer Rat is here", output)

    def test_polished_room_threat_list_hides_defeated_enemy(self):
        # install_enemy_lifecycle_runtime also patches the production presentation
        # helper so LOOK and Mudlet context actions agree with combat targeting.
        import mud.room_prompt_experience as room_prompt

        session = RuntimeSession(self.database, self.room_key)
        scene = SimpleNamespace(key=self.room_key, enemy_keys=(SEWER_RAT.key,))
        self.assertIn("Sewer Rat", room_prompt._enemy_lines(scene))

        mark_static_enemy_defeated(
            self.database,
            self.room_key,
            SEWER_RAT.key,
            120.0,
        )
        self.assertNotIn("Sewer Rat", room_prompt._enemy_lines(scene))


if __name__ == "__main__":
    unittest.main()
