from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.npc_conversation import (
    install_generic_npc_conversation_runtime,
    resolve_static_talk_target,
)


ROOT = Path(__file__).resolve().parents[1]


class _Npc:
    def __init__(self, key, name, room_key, role, dialogue):
        self.key = key
        self.name = name
        self.room_key = room_key
        self.role = role
        self.dialogue = tuple(dialogue)


class _World:
    def __init__(self, npc_keys):
        self._scene = SimpleNamespace(npc_keys=tuple(npc_keys))

    def scene(self, _room_key):
        return self._scene


class _DummySession:
    def __init__(self):
        self.character = SimpleNamespace(current_room="market")
        self.next_command = ""
        self.messages = []
        self.delegated = False
        self.state = SimpleNamespace(DISCONNECTED="disconnected")
        self.mobile_npcs = None

    async def prompt(self, _text):
        return self.next_command

    async def send(self, text):
        self.messages.append(text)

    async def playing_prompt(self):
        self.delegated = True
        await self.send("There is no one by that name here to speak with.\r\n")


class GenericNpcConversationTests(unittest.IsolatedAsyncioTestCase):
    async def test_visible_npc_given_and_full_name_never_fall_through(self):
        hadrik = _Npc(
            "dwarf_hadrik_coilpress",
            "Hadrik Coilpress",
            "market",
            "Dwarven trade factor",
            (
                "Hadrik folds his brass rule shut. 'Accurate information costs less than a broken axle.'",
            ),
        )
        npcs = {hadrik.key: hadrik}
        world = _World((hadrik.key,))
        Session = type("ConversationSession", (_DummySession,), {})
        install_generic_npc_conversation_runtime(Session, world, npcs)

        for command in ("talk hadrik", "talk hadrik coilpress", "talk coilpress"):
            with self.subTest(command=command):
                session = Session()
                session.next_command = command
                await session.playing_prompt()
                output = "".join(session.messages)
                self.assertIn("Hadrik folds his brass rule shut", output)
                self.assertNotIn("There is no one by that name", output)
                self.assertFalse(session.delegated)

    async def test_unknown_person_still_delegates_to_existing_command_stack(self):
        hadrik = _Npc(
            "dwarf_hadrik_coilpress",
            "Hadrik Coilpress",
            "market",
            "Dwarven trade factor",
            ("Hello.",),
        )
        Session = type("ConversationSession", (_DummySession,), {})
        install_generic_npc_conversation_runtime(
            Session,
            _World((hadrik.key,)),
            {hadrik.key: hadrik},
        )
        session = Session()
        session.next_command = "talk nobody"
        await session.playing_prompt()
        self.assertTrue(session.delegated)

    def test_resolver_rejects_ambiguous_local_aliases(self):
        npcs = {
            "a": _Npc("a", "Factor One", "market", "factor", ("A",)),
            "b": _Npc("b", "Factor Two", "market", "factor", ("B",)),
        }
        world = _World(("a", "b"))
        npc, ambiguous = resolve_static_talk_target(world, npcs, "market", "factor")
        self.assertIsNone(npc)
        self.assertEqual(set(ambiguous), {"Factor One", "Factor Two"})


class ProductionNpcTalkabilityTests(unittest.TestCase):
    def test_every_visible_static_npc_is_talkable_and_hadrik_resolves(self):
        code = r"""
import server
import mud.world as world
from mud.npc_conversation import (
    resolve_static_talk_target,
    static_npc_talkability_problems,
    validate_static_npc_talkability,
)
from mud.goblin_start import GOBLIN_BRASSGUT_MARKET_KEY

problems = static_npc_talkability_problems(server.WORLD, world.NPCS_BY_KEY)
assert not problems, "\n".join(problems)
count = validate_static_npc_talkability(server.WORLD, world.NPCS_BY_KEY)
assert count == len(world.NPCS_BY_KEY)

hadrik = world.NPCS_BY_KEY["dwarf_hadrik_coilpress"]
for target in ("Hadrik", "Hadrik Coilpress", "Coilpress"):
    resolved, ambiguous = resolve_static_talk_target(
        server.WORLD,
        world.NPCS_BY_KEY,
        GOBLIN_BRASSGUT_MARKET_KEY,
        target,
    )
    assert not ambiguous, (target, ambiguous)
    assert resolved is not None, target
    assert resolved.key == hadrik.key, (target, resolved.key)

assert server.PlayerSession._generic_npc_conversation_runtime_installed
print(f"NPC_TALKABILITY_OK:{count}")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NPC_TALKABILITY_OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
