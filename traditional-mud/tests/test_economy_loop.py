from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
from mud.combat import EnemyState, SEWER_RAT
from mud.database import Database
from mud.economy_loop import (
    install_economy_content,
    install_economy_loop_runtime,
    reset_economy_node_state,
)


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


def economy_session_type():
    class Session(BaseSession):
        pass

    install_economy_loop_runtime(Session)
    return Session


class EconomyLoopTests(unittest.TestCase):
    def setUp(self):
        install_economy_content()
        reset_economy_node_state()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        account = self.db.create_account("economyaccount", "hash")
        self.character = self.db.create_character(account.id, "Crafter", "human", "wizard")

    def tearDown(self):
        reset_economy_node_state()
        self.tempdir.cleanup()

    def _session_in(self, room_key: str, commands=None):
        self.db.set_character_room(self.character.id, room_key)
        self.character = self.db.get_character_by_name("Crafter")
        Session = economy_session_type()
        return Session(self.db, self.character, commands)

    def test_mining_node_produces_inventory_and_skill_progress(self):
        session = self._session_in("human_blackglass_arch", ["mine"])

        asyncio.run(session.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ore"), 1)
        self.assertEqual(self.db.get_trade_skill_progress(self.character.id, "mining")["skill_xp"], 1)
        self.assertIn("Iron Ore", "".join(session.outputs))

    def test_real_room_station_allows_existing_crafting_recipe(self):
        session = self._session_in("dwarf_workshop_tier", ["craft smelt iron ingot"])
        self.db.add_item(self.character.id, "iron_ore", 2)

        asyncio.run(session.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ore"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ingot"), 1)
        self.assertEqual(self.db.get_trade_skill_progress(self.character.id, "blacksmithing")["skill_xp"], 1)

    def test_enemy_defeat_awards_hunter_material(self):
        session = self._session_in("human_vermin_pens")
        enemy = EnemyState(SEWER_RAT)
        enemy.current_hp = 0
        session.active_enemy = enemy

        asyncio.run(session._finish_enemy_defeat(enemy))

        self.assertEqual(self.db.item_quantity(self.character.id, "rough_hide"), 1)
        self.assertIn("Loot: 1x Rough Hide", "".join(session.outputs))

    def test_cross_role_recipe_uses_hunter_drop_and_mined_metal(self):
        session = self._session_in("dwarf_workshop_tier", ["craft forge imp horn dagger"])
        self.db.record_trade_skill_use(self.character.id, "blacksmithing", 3)
        self.db.add_item(self.character.id, "iron_ingot", 1)
        self.db.add_item(self.character.id, "imp_horn", 1)

        asyncio.run(session.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ingot"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "imp_horn"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "imp_horn_dagger"), 1)
        self.assertIn("Imp-Horn Dagger", "".join(session.outputs))

    def test_economy_content_registers_social_crafting_chain(self):
        self.assertIn("rough_hide", crafting.ITEMS_BY_KEY)
        self.assertIn("imp_horn", crafting.ITEMS_BY_KEY)
        self.assertIn("sew_trailguard_gloves", crafting.RECIPES_BY_KEY)
        recipe = crafting.RECIPES_BY_KEY["sew_trailguard_gloves"]
        materials = {requirement.item_key for requirement in recipe.materials}
        self.assertEqual(materials, {"rough_hide", "cotton_thread"})


if __name__ == "__main__":
    unittest.main()
