from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.first_ten_story_depth as story_depth
import mud.waymeet_adventure_arc as waymeet
from mud.contextual_command_routing import (
    OWNED_ROOMS_BY_HELPER,
    install_contextual_command_routing_guard,
)
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


ROOT = Path(__file__).resolve().parents[1]


class _Database:
    def list_flags(self, _character_id):
        return []


class _Session:
    def __init__(self, room_key: str, race: str = "goblin") -> None:
        self.character = SimpleNamespace(id=1, race=race, current_room=room_key)
        self.database = _Database()
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class _PlayerSession:
    pass


class ContextualCommandRoutingTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_contextual_command_routing_guard(_PlayerSession)

    async def test_waymeet_catch_all_verbs_decline_rooms_they_do_not_own(self):
        goblin_start = STARTER_RACE_LOOPS_BY_RACE["goblin"].starting_room_key
        session = _Session(goblin_start)

        calls = (
            (waymeet._search, (session, "conversation")),
            (waymeet._listen, (session, "conversation")),
            (waymeet._climb, (session, "conversation")),
            (waymeet._pull, (session, "conversation")),
            (waymeet._touch, (session, "conversation")),
        )
        for helper, args in calls:
            with self.subTest(helper=helper.__name__):
                session.messages.clear()
                self.assertFalse(await helper(*args))
                self.assertEqual(session.messages, [])

    async def test_listen_conversation_reaches_goblin_relationship_scene(self):
        goblin_start = STARTER_RACE_LOOPS_BY_RACE["goblin"].starting_room_key
        session = _Session(goblin_start)

        # The outer Waymeet layer must decline this command instead of printing
        # its generic no-special-LISTEN fallback.
        self.assertFalse(await waymeet._listen(session, "conversation"))
        self.assertEqual(session.messages, [])

        handled = await story_depth._relationship_talk(
            session,
            "goblin",
            "listen conversation",
        )
        self.assertTrue(handled)
        output = "".join(session.messages)
        self.assertIn("Pella", output)
        self.assertIn("Nix", output)
        self.assertNotIn("no special LISTEN interaction", output)

    def test_all_racial_start_rooms_are_outside_waymeet_generic_verb_ownership(self):
        owned = set().union(*OWNED_ROOMS_BY_HELPER.values())
        for race_key, loop in STARTER_RACE_LOOPS_BY_RACE.items():
            with self.subTest(race=race_key):
                self.assertNotIn(loop.starting_room_key, owned)

    def test_guard_covers_every_waymeet_generic_fallback_verb(self):
        self.assertEqual(
            set(OWNED_ROOMS_BY_HELPER),
            {"_search", "_listen", "_climb", "_pull", "_touch"},
        )


class ProductionContextualCommandRoutingTests(unittest.TestCase):
    def test_production_entrypoint_installs_routing_guard(self):
        code = r'''
import server
import mud.waymeet_adventure_arc as waymeet
assert server.PlayerSession._contextual_command_routing_guard_installed
for name in ("_search", "_listen", "_climb", "_pull", "_touch"):
    assert getattr(getattr(waymeet, name), "_dotf_context_scoped", False), name
print("CONTEXTUAL_COMMAND_ROUTING_OK")
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
        self.assertIn("CONTEXTUAL_COMMAND_ROUTING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
