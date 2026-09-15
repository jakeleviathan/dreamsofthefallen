from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.actor_inspection import (
    find_visible_actor,
    handle_actor_inspection,
    normalize_inspection_synonym,
    render_actor_detail,
)
from mud.combat import EnemyDefinition
from mud.npcs import MobileNpcDefinition, MobileNpcState
from mud.partial_target_matching import resolve_target_command
from mud.world import NpcDefinition


ROOT = Path(__file__).resolve().parents[1]


class _World:
    def __init__(self, *, npc_keys=(), enemy_keys=()):
        self._scene = SimpleNamespace(npc_keys=tuple(npc_keys), enemy_keys=tuple(enemy_keys))

    def scene(self, _room_key):
        return self._scene


class _MobileManager:
    def __init__(self, states=()):
        self.states = tuple(states)

    def npcs_in_room(self, room_key):
        return tuple(state for state in self.states if state.current_room_key == room_key)


class _Session:
    def __init__(self, *, mobile_npcs=None):
        self.character = SimpleNamespace(current_room="test_room")
        self.mobile_npcs = mobile_npcs
        self.sent: list[str] = []

    async def send(self, text: str):
        self.sent.append(text)


class ActorInspectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_look_examine_and_inspect_work_on_static_npc(self):
        pella = NpcDefinition(
            key="goblin_pella_mireglass",
            name="Pella Mireglass",
            short_description="a field apothecary labeling damp herb bundles with a grease pencil",
            room_key="test_room",
            role="apothecary",
        )
        session = _Session()
        world = _World(npc_keys=(pella.key,))
        with patch.dict("mud.actor_inspection.NPCS_BY_KEY", {pella.key: pella}, clear=True):
            for command in (
                "look Pella Mireglass",
                "look at Pella Mireglass",
                "examine Pella Mireglass",
                "inspect Pella Mireglass",
            ):
                session.sent.clear()
                with self.subTest(command=command):
                    handled = await handle_actor_inspection(session, command, world)
                    self.assertTrue(handled)
                    output = "".join(session.sent)
                    self.assertIn("Pella Mireglass", output)
                    self.assertIn("field apothecary", output)
                    self.assertIn("TALK Pella Mireglass", output)

    async def test_enemy_can_be_looked_at_without_revealing_hidden_stats(self):
        enemy = EnemyDefinition(
            key="bog_snapper",
            name="Bog Snapper",
            aliases=("snapper", "bog snapper"),
            description="a squat amphibious scavenger with a shovel-shaped head",
            max_hp=22,
            armor_class=4,
            auto_attack_damage=2,
            auto_attack_interval=3.8,
            xp_reward=30,
        )
        session = _Session()
        world = _World(enemy_keys=(enemy.key,))
        with patch.dict("mud.actor_inspection.ENEMIES_BY_KEY", {enemy.key: enemy}, clear=True):
            handled = await handle_actor_inspection(session, "look Bog Snapper", world)
        self.assertTrue(handled)
        output = "".join(session.sent)
        self.assertIn("Bog Snapper", output)
        self.assertIn("shovel-shaped head", output)
        self.assertIn("ATTACK Bog Snapper", output)
        self.assertNotIn("22", output)
        self.assertNotIn("Armor Class", output)
        self.assertNotIn("AC: 4", output)

    async def test_mobile_npc_inspection_uses_live_room_presence(self):
        definition = MobileNpcDefinition(
            key="road_mender",
            name="Road Mender",
            short_description="a tired worker checking the edge stones",
            spawn_room_key="test_room",
            allowed_room_keys=("test_room",),
        )
        state = MobileNpcState(definition=definition, current_room_key="test_room")
        session = _Session(mobile_npcs=_MobileManager((state,)))
        actor = find_visible_actor(session, _World(), "Road Mender")
        self.assertIsNotNone(actor)
        self.assertEqual(actor.name, "Road Mender")
        self.assertIn("tired worker", render_actor_detail(actor))

    async def test_non_actor_target_is_not_stolen_from_existing_feature_handlers(self):
        session = _Session()
        handled = await handle_actor_inspection(session, "look old lever", _World())
        self.assertFalse(handled)
        self.assertEqual(session.sent, [])

    def test_common_inspection_synonyms_normalize_for_every_other_world_target(self):
        self.assertEqual(normalize_inspection_synonym("look at old lever"), "look old lever")
        self.assertEqual(normalize_inspection_synonym("inspect old lever"), "examine old lever")
        self.assertEqual(
            normalize_inspection_synonym("inspect item Stamped Earth Token"),
            "inspect item Stamped Earth Token",
        )

    def test_partial_matching_extends_to_actor_inspection_verbs(self):
        pella = NpcDefinition(
            key="goblin_pella_mireglass",
            name="Pella Mireglass",
            short_description="a field apothecary",
            room_key="test_room",
            role="apothecary",
        )
        session = _Session()
        world = _World(npc_keys=(pella.key,))
        with patch.dict("mud.partial_target_matching.NPCS_BY_KEY", {pella.key: pella}, clear=True):
            expectations = {
                "look pel": "look Pella Mireglass",
                "look at pel": "look Pella Mireglass",
                "examine pel": "examine Pella Mireglass",
                "inspect pel": "inspect Pella Mireglass",
            }
            for command, expected in expectations.items():
                with self.subTest(command=command):
                    self.assertEqual(resolve_target_command(session, command, world).command, expected)


class ProductionActorInspectionTests(unittest.TestCase):
    def test_production_entrypoint_installs_actor_inspection(self):
        code = r'''
import server
assert server.PlayerSession._actor_inspection_runtime_installed
assert server.PlayerSession._partial_target_matching_runtime_installed
print("ACTOR_INSPECTION_OK")
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
        self.assertIn("ACTOR_INSPECTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
