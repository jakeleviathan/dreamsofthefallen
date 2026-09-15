from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mud.forest_elf_nurture as forest_nurture
import mud.goblin_deep_mire as deep_mire
import mud.goblin_swamp as goblin_swamp
import mud.troll_start as troll_start
from mud.contextual_command_routing import (
    _dispatch_authored_economy_command,
    install_contextual_command_routing_guard,
)


class AuthoredEconomyRoutingTests(unittest.IsolatedAsyncioTestCase):
    def _session(self, room: str, race: str = "goblin"):
        return SimpleNamespace(character=SimpleNamespace(current_room=room, race=race))

    async def test_troll_deadfall_routes_to_authored_survival_handler(self):
        session = self._session(troll_start.TROLL_HIDEWIND_RING_KEY, "troll")
        with patch.object(troll_start, "_handle_cold_quest", new=AsyncMock(return_value=True)) as handler:
            handled = await _dispatch_authored_economy_command(session, "gather deadfall")
        self.assertTrue(handled)
        handler.assert_awaited_once_with(session, "gather deadfall")

    async def test_forest_elf_silvermoss_routes_to_authored_herbalism_lesson(self):
        session = self._session(forest_nurture.FOREST_ELF_START_ROOM_KEY, "forest_elf")
        with patch.object(
            forest_nurture,
            "_handle_forest_elf_nurture",
            new=AsyncMock(return_value=True),
        ) as handler:
            handled = await _dispatch_authored_economy_command(session, "harvest silvermoss")
        self.assertTrue(handled)
        handler.assert_awaited_once_with(session, "harvest silvermoss")

    async def test_deep_mire_glassroot_routes_to_authored_gathering(self):
        session = self._session(deep_mire.GOBLIN_GREENHOUSE_CONSERVATORY_KEY)
        with patch.object(
            deep_mire,
            "_handle_deep_gathering",
            new=AsyncMock(return_value=True),
        ) as handler:
            handled = await _dispatch_authored_economy_command(session, "harvest glassroot")
        self.assertTrue(handled)
        handler.assert_awaited_once_with(session, "harvest glassroot")

    async def test_goblin_craft_alias_routes_to_authored_field_alchemy(self):
        session = self._session(goblin_swamp.GOBLIN_APOTHECARY_BLIND_KEY)
        with patch.object(goblin_swamp, "_handle_alchemy", new=AsyncMock(return_value=True)) as handler:
            handled = await _dispatch_authored_economy_command(session, "craft minor healing potion")
        self.assertTrue(handled)
        handler.assert_awaited_once_with(session, "craft minor healing potion")

    async def test_unrelated_gathering_is_not_stolen(self):
        session = self._session("human_cathedral_square", "human")
        handled = await _dispatch_authored_economy_command(session, "gather iron")
        self.assertFalse(handled)

    def test_production_guard_installs_authored_router(self):
        class Session:
            async def playing_prompt(self):
                return None

        install_contextual_command_routing_guard(Session)
        self.assertTrue(Session._contextual_command_routing_guard_installed)
        self.assertTrue(Session._authored_economy_router_installed)


if __name__ == "__main__":
    unittest.main()
