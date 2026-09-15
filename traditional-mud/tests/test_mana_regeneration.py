from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mud.mana_regeneration import (
    _mana_recovery_loop,
    mana_recovery_amount,
    recover_mana_once,
    restore_mana,
)


class _World:
    def __init__(self, *, tags=(), feature_names=()):
        self._scene = SimpleNamespace(
            tags=tuple(tags),
            features=tuple(SimpleNamespace(name=name) for name in feature_names),
        )

    def scene(self, _room_key):
        return self._scene


class _Session:
    def __init__(self, *, mana=10, max_mana=20, resting=False):
        self.character = SimpleNamespace(current_room="test_room")
        self.combatant = SimpleNamespace(current_mana=mana, max_mana=max_mana)
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self._movement_resting = resting
        self.client_state_pushes = 0

    async def send_client_state(self):
        self.client_state_pushes += 1


class ManaRegenerationRuleTests(unittest.TestCase):
    def test_passive_resting_and_restful_recovery_are_distinct(self):
        self.assertEqual(mana_recovery_amount(_Session(resting=False), _World()), 1)
        self.assertEqual(mana_recovery_amount(_Session(resting=True), _World()), 3)
        self.assertEqual(
            mana_recovery_amount(_Session(resting=True), _World(tags=("safe",))),
            4,
        )

    def test_mana_recovery_pauses_during_static_or_mobile_combat(self):
        session = _Session(resting=True)
        session.active_enemy = object()
        self.assertEqual(mana_recovery_amount(session, _World(tags=("safe",))), 0)
        session.active_enemy = None
        session.active_mobile_npc_key = "hunter"
        self.assertEqual(mana_recovery_amount(session, _World(tags=("safe",))), 0)

    def test_recovery_caps_at_maximum(self):
        session = _Session(mana=19, max_mana=20)
        self.assertEqual(restore_mana(session, 50), 1)
        self.assertEqual(session.combatant.current_mana, 20)
        self.assertEqual(recover_mana_once(session, _World()), 0)

    def test_recover_once_uses_current_rest_state(self):
        session = _Session(mana=10, max_mana=20, resting=True)
        self.assertEqual(recover_mana_once(session, _World(tags=("safe",))), 4)
        self.assertEqual(session.combatant.current_mana, 14)


class ManaRegenerationLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_background_tick_pushes_updated_hud_state(self):
        session = _Session(mana=10, max_mana=20)
        calls = 0

        async def fake_sleep(_seconds):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError

        with patch("mud.mana_regeneration.asyncio.sleep", fake_sleep):
            await _mana_recovery_loop(session, _World())

        self.assertEqual(session.combatant.current_mana, 11)
        self.assertEqual(session.client_state_pushes, 1)


if __name__ == "__main__":
    unittest.main()
