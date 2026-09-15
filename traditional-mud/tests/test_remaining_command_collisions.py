from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.command_collision_policy import (
    _sporekin_owns_guide,
    _try_pre_movement_owner,
    _waymeet_owns_frontier,
)
from mud.sporekin_depth import SPOREKIN_MEMORY_PATH_ROOM_KEY
from mud.waymeet_frontier import WAYMEET_CROSSROADS_KEY


ROOT = Path(__file__).resolve().parents[1]


class _Session:
    def __init__(self, *, race: str = "human", room: str = "somewhere") -> None:
        self.character = SimpleNamespace(race=race, current_room=room)
        self.messages: list[str] = []
        self.next_command = ""

    async def prompt(self, _text: str):
        return self.next_command

    async def send(self, text: str) -> None:
        self.messages.append(text)


class ContextOwnerTests(unittest.IsolatedAsyncioTestCase):
    def test_sporekin_bare_guide_is_owned_only_on_memory_path(self):
        memory = _Session(race="sporekin", room=SPOREKIN_MEMORY_PATH_ROOM_KEY)
        elsewhere = _Session(race="sporekin", room=WAYMEET_CROSSROADS_KEY)
        human = _Session(race="human", room=SPOREKIN_MEMORY_PATH_ROOM_KEY)

        self.assertTrue(_sporekin_owns_guide(memory))
        self.assertFalse(_sporekin_owns_guide(elsewhere))
        self.assertFalse(_sporekin_owns_guide(human))

    def test_waymeet_bare_frontier_keeps_local_meaning(self):
        self.assertTrue(_waymeet_owns_frontier(_Session(room=WAYMEET_CROSSROADS_KEY)))
        self.assertFalse(_waymeet_owns_frontier(_Session(room="ashcross_common")))

    async def test_rest_alias_gives_authored_handler_first_refusal(self):
        session = _Session()
        session.next_command = "sit"

        async def authored_prompt(current) -> None:
            command = await current.prompt("\r\n> ")
            if command.strip().lower() == "sit":
                await current.send("You sit on the carved witness bench.\r\n")
                return
            await current.send("Unknown command.\r\n")

        handled = await _try_pre_movement_owner(session, authored_prompt, "sit")
        self.assertTrue(handled)
        self.assertEqual(session.messages, ["You sit on the carved witness bench.\r\n"])

    async def test_rest_alias_discards_unknown_before_movement_fallback(self):
        session = _Session()

        async def unknown_prompt(current) -> None:
            await current.prompt("\r\n> ")
            await current.send("Unknown command. Type HELP for commands.\r\n")

        handled = await _try_pre_movement_owner(session, unknown_prompt, "rise")
        self.assertFalse(handled)
        self.assertEqual(session.messages, [])


class ProductionCollisionPolicyTests(unittest.TestCase):
    def test_production_entrypoint_installs_outer_collision_policy(self):
        code = r'''
import server
assert server.PlayerSession._command_collision_policy_installed
assert server.PlayerSession._runtime_remediation_installed
assert server.PlayerSession._pre_movement_prompt_for_aliases is not None
print("COMMAND_COLLISION_POLICY_OK")
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
        self.assertIn("COMMAND_COLLISION_POLICY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
