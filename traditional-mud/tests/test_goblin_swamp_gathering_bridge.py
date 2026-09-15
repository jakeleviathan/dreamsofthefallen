from __future__ import annotations

import unittest
from types import SimpleNamespace

from mud.goblin_swamp import (
    GOBLIN_REEDFEN_CAUSEWAY_KEY,
    GOBLIN_SWAMP_GATHERING,
)
from mud.room_presentation import install_goblin_swamp_gathering_bridge


class FakeDatabase:
    def __init__(self) -> None:
        self.skill_xp = 0
        self.items: dict[str, int] = {}

    def get_trade_skill_progress(self, character_id: int, trade_skill_key: str):
        return {"trade_skill_key": trade_skill_key, "uses": self.skill_xp, "skill_xp": self.skill_xp}

    def add_item(self, character_id: int, item_key: str, quantity: int) -> None:
        self.items[item_key] = self.items.get(item_key, 0) + quantity

    def record_trade_skill_use(self, character_id: int, trade_skill_key: str, skill_xp: int) -> None:
        self.skill_xp += skill_xp


def session_class():
    class Session:
        async def playing_prompt(self) -> None:
            self.delegated = True

        def __init__(self, command: str, room_key: str) -> None:
            self.command = command
            self.character = SimpleNamespace(id=1, current_room=room_key)
            self.database = FakeDatabase()
            self.messages: list[str] = []
            self.delegated = False

        async def prompt(self, _text: str):
            return self.command

        async def send(self, text: str) -> None:
            self.messages.append(text)

        async def send_client_state(self) -> None:
            return None

    return Session


class GoblinSwampGatheringBridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        GOBLIN_SWAMP_GATHERING.reset()

    async def test_herbalism_reports_visible_reedfen_greenleaf(self) -> None:
        Session = session_class()
        install_goblin_swamp_gathering_bridge(Session)
        session = Session("herbalism", GOBLIN_REEDFEN_CAUSEWAY_KEY)

        await session.playing_prompt()

        text = "".join(session.messages)
        self.assertIn("Herbalism skill: 0", text)
        self.assertIn("Gatherable here: Reedfen Greenleaf", text)
        self.assertFalse(session.delegated)

    async def test_resources_uses_authored_swamp_node_service(self) -> None:
        Session = session_class()
        install_goblin_swamp_gathering_bridge(Session)
        session = Session("resources", GOBLIN_REEDFEN_CAUSEWAY_KEY)

        await session.playing_prompt()

        text = "".join(session.messages)
        self.assertIn("--- Local Economy ---", text)
        self.assertIn("Reedfen Greenleaf [Herbalism 0]", text)
        self.assertNotIn("Resources: none in this room", text)
        self.assertFalse(session.delegated)

    async def test_gather_greenleaf_harvests_the_room_node(self) -> None:
        Session = session_class()
        install_goblin_swamp_gathering_bridge(Session)
        session = Session("gather greenleaf", GOBLIN_REEDFEN_CAUSEWAY_KEY)

        await session.playing_prompt()

        text = "".join(session.messages)
        self.assertIn("You harvest 1x Greenleaf", text)
        self.assertEqual(session.database.items.get("greenleaf"), 1)
        self.assertEqual(session.database.skill_xp, 1)
        self.assertFalse(session.delegated)

    async def test_non_swamp_room_still_delegates_normally(self) -> None:
        Session = session_class()
        install_goblin_swamp_gathering_bridge(Session)
        session = Session("herbalism", "human_cathedral_square")

        await session.playing_prompt()

        self.assertTrue(session.delegated)
        self.assertEqual(session.messages, [])


if __name__ == "__main__":
    unittest.main()
