from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mud.combat import EnemyState, SEWER_RAT, SMALL_IMP
from mud.database import Database
from mud.economy_balance import (
    install_economy_balance_content,
    install_economy_balance_runtime,
)
from mud.economy_loop import install_economy_loop_runtime, reset_economy_node_state
from mud.human_blackwall_opening import SOOTSTEP_BURROWER


class FakeState:
    DISCONNECTED = "disconnected"


class BaseSession:
    def __init__(self, database, character, commands=None):
        self.database = database
        self.character = character
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.state = FakeState()
        self.active_enemy = None

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def playing_prompt(self):
        command = await self.prompt("> ")
        if command is not None:
            await self.send(f"BASE: {command}\r\n")

    async def show_current_room(self):
        await self.send("BASE ROOM\r\n")

    async def _finish_enemy_defeat(self, enemy):
        self.active_enemy = None
        await self.send(f"BASE DEFEAT: {enemy.definition.name}\r\n")


def balanced_session_type():
    class Session(BaseSession):
        pass

    install_economy_loop_runtime(Session)
    install_economy_balance_runtime(Session)
    return Session


class EconomyBalanceTests(unittest.TestCase):
    def setUp(self):
        install_economy_balance_content()
        reset_economy_node_state()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        account = self.db.create_account("balanceaccount", "hash")
        self.character = self.db.create_character(account.id, "Runner", "human", "wizard")

    def tearDown(self):
        reset_economy_node_state()
        self.tempdir.cleanup()

    def _session_in(self, room_key: str, commands=None):
        self.db.set_character_room(self.character.id, room_key)
        self.character = self.db.get_character_by_name("Runner")
        Session = balanced_session_type()
        return Session(self.db, self.character, commands)

    def test_repeatable_training_mobs_have_reduced_xp_but_blackwall_anchor_does_not(self):
        self.assertEqual(SEWER_RAT.xp_reward, 15)
        self.assertEqual(SMALL_IMP.xp_reward, 20)
        self.assertEqual(SOOTSTEP_BURROWER.xp_reward, 30)

    def test_blackwall_burrower_guarantees_hide_and_can_roll_secondary_sinew(self):
        session = self._session_in("human_sootstep_service_tunnel")
        enemy = EnemyState(SOOTSTEP_BURROWER)
        enemy.current_hp = 0
        session.active_enemy = enemy

        with patch("mud.economy_balance.random", return_value=0.0):
            asyncio.run(session._finish_enemy_defeat(enemy))

        self.assertEqual(self.db.item_quantity(self.character.id, "rough_hide"), 2)
        self.assertEqual(self.db.item_quantity(self.character.id, "tough_sinew"), 1)
        output = "".join(session.outputs)
        self.assertIn("Loot: 2x Rough Hide", output)
        self.assertIn("Bonus loot: 1x Tough Sinew", output)

    def test_imp_grind_has_guaranteed_horn_and_uncommon_upgrade_material(self):
        session = self._session_in("human_vermin_pens")
        enemy = EnemyState(SMALL_IMP)
        enemy.current_hp = 0
        session.active_enemy = enemy

        with patch("mud.economy_balance.random", return_value=0.0):
            asyncio.run(session._finish_enemy_defeat(enemy))

        self.assertEqual(self.db.item_quantity(self.character.id, "imp_horn"), 1)
        self.assertEqual(self.db.item_quantity(self.character.id, "imp_ember_shard"), 1)

    def test_caravan_court_sewing_station_closes_the_human_hunt_to_craft_loop(self):
        session = self._session_in(
            "human_blackwall_caravan_court",
            ["craft sew reinforced field vest"],
        )
        self.db.record_trade_skill_use(self.character.id, "tailoring", 6)
        self.db.add_item(self.character.id, "rough_hide", 2)
        self.db.add_item(self.character.id, "cotton_cloth", 1)
        self.db.add_item(self.character.id, "iron_ingot", 1)

        asyncio.run(session.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.character.id, "reinforced_field_vest"), 1)
        self.assertIn("Reinforced Field Vest", "".join(session.outputs))

    def test_needs_makes_cross_region_trade_inputs_explicit(self):
        session = self._session_in("human_blackwall_caravan_court", ["needs"])
        self.db.add_item(self.character.id, "rough_hide", 2)

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("What Should I Trade For?", output)
        self.assertIn("Reinforced Field Vest", output)
        self.assertIn("Cotton Cloth", output)
        self.assertIn("Iron Ingot", output)
        self.assertIn("trade", output.lower())

    def test_human_starter_route_is_exposed_as_an_end_to_end_loop(self):
        session = self._session_in("human_cinder_ward", ["economy route"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("Human Starter Economy Route", output)
        self.assertIn("Sootstep Burrower", output)
        self.assertIn("NEEDS", output)
        self.assertIn("hunt -> resources -> craft -> trade -> upgrade -> hunt", output)

    def test_outer_caravan_road_introduces_world_gathering_after_the_slice(self):
        session = self._session_in("human_outer_caravan_road", ["herbalism"])

        asyncio.run(session.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.character.id, "greenleaf"), 1)
        self.assertEqual(self.db.get_trade_skill_progress(self.character.id, "herbalism")["skill_xp"], 1)


if __name__ == "__main__":
    unittest.main()
