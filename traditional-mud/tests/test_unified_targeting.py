from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mud.enemy_targeting import (
    _player_candidates_here,
    _selected_player,
    install_enemy_targeting_runtime,
)
from mud.social_experience import _ACTIVE_SESSIONS


class _Character:
    def __init__(self, cid: int, name: str, room: str = "shared_room"):
        self.id = cid
        self.name = name
        self.current_room = room
        self.race = "goblin"
        self.character_class = "priest"
        self.level = 5
        self.deity_key = "zerjz"


class _Session:
    def __init__(self, cid: int, name: str, room: str = "shared_room"):
        self.character = _Character(cid, name, room)
        self.combatant = SimpleNamespace(current_hp=28, max_hp=31)
        self.selected_enemy = None
        self.selected_mobile_npc_key = None
        self.selected_enemy_room_key = None
        self.selected_player_character_id = None
        self.selected_player_room_key = None
        self.selected_target_kind = None
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.messages = []
        self.state_pushes = 0

    async def send(self, text):
        self.messages.append(text)

    async def send_client_state(self):
        self.state_pushes += 1


class UnifiedPlayerTargetResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        _ACTIVE_SESSIONS.clear()

    async def asyncTearDown(self):
        _ACTIVE_SESSIONS.clear()

    async def test_target_self_by_character_name_and_self_aliases(self):
        prime = _Session(1, "Prime")
        for text in ("prime", "self", "me", "myself"):
            candidates = _player_candidates_here(prime, text)
            self.assertEqual(candidates, [prime])

    async def test_target_other_player_only_when_in_same_room(self):
        prime = _Session(1, "Prime")
        friend = _Session(2, "Arlathi")
        _ACTIVE_SESSIONS.update({prime, friend})

        self.assertEqual(_player_candidates_here(prime, "arl"), [friend])
        prime.selected_player_character_id = friend.character.id
        prime.selected_target_kind = "player"
        self.assertIs(_selected_player(prime), friend)

        friend.character.current_room = "elsewhere"
        self.assertIsNone(_selected_player(prime))

    async def test_player_selection_can_coexist_with_active_enemy(self):
        prime = _Session(1, "Prime")
        friend = _Session(2, "Arlathi")
        _ACTIVE_SESSIONS.update({prime, friend})
        prime.active_enemy = object()
        prime.selected_player_character_id = friend.character.id
        prime.selected_target_kind = "player"
        self.assertIs(_selected_player(prime), friend)


class UnifiedTargetRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_player_is_implicit_ally_ability_target(self):
        class Session(_Session):
            async def playing_prompt(self):
                return None

            async def use_ability(self, ability_text):
                self.forwarded_ability = ability_text

            async def move_character(self, *_args, **_kwargs):
                return None

            async def _stop_combat(self, *_args, **_kwargs):
                return None

            def _enemy_in_current_room(self, _target):
                return None

            def _mobile_npc_in_current_room(self, _target):
                return None

        install_enemy_targeting_runtime(Session, SimpleNamespace())
        prime = Session(1, "Prime")
        prime.selected_player_character_id = prime.character.id
        prime.selected_target_kind = "player"

        ability = SimpleNamespace(
            key="mend_ally",
            name="Mend Ally",
            category="healing",
        )
        with patch("mud.enemy_targeting.class_abilities_for_level", return_value=(ability,)):
            await prime.use_ability("Mend Ally")
        self.assertEqual(prime.forwarded_ability, "Mend Ally Prime")

    async def test_selected_player_does_not_become_attack_target(self):
        class Session(_Session):
            async def playing_prompt(self):
                return None

            async def use_ability(self, ability_text):
                self.forwarded_ability = ability_text

            async def move_character(self, *_args, **_kwargs):
                return None

            async def _stop_combat(self, *_args, **_kwargs):
                return None

            def _enemy_in_current_room(self, _target):
                return None

            def _mobile_npc_in_current_room(self, _target):
                return None

        install_enemy_targeting_runtime(Session, SimpleNamespace())
        prime = Session(1, "Prime")
        prime.selected_player_character_id = prime.character.id
        prime.selected_target_kind = "player"

        # Hostile spells do not reinterpret a player selection as an enemy.
        ability = SimpleNamespace(
            key="sacred_spark",
            name="Sacred Spark",
            category="divine_damage",
        )
        with patch("mud.enemy_targeting.class_abilities_for_level", return_value=(ability,)):
            await prime.use_ability("Sacred Spark")
        self.assertEqual(prime.forwarded_ability, "Sacred Spark")
        self.assertIsNone(prime.active_enemy)


if __name__ == "__main__":
    unittest.main()
