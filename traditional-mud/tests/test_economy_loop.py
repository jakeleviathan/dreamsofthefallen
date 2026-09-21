from __future__ import annotations

import asyncio
import tempfile
import unittest
from unittest.mock import patch
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


class FakeCraftingTelnet:
    def __init__(self):
        self.gmcp_enabled = True
        self.messages: list[tuple[str, dict]] = []

    async def send_gmcp(self, package: str, payload: dict):
        self.messages.append((package, payload))
        return True


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

    def test_generic_gathering_accepts_unique_partial_node_names(self):
        mining = self._session_in("human_blackglass_arch", ["mine iron v"])
        asyncio.run(mining.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ore"), 1)

        herbalism = self._session_in("forest_elf_old_river_path", ["herbalism green"])
        asyncio.run(herbalism.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.character.id, "greenleaf"), 1)

    def test_ambiguous_partial_resource_name_is_not_guessed(self):
        session = self._session_in("forest_elf_greenway", ["gather patch"])
        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("Be more specific", output)
        self.assertIn("Cotton Patch", output)
        self.assertIn("Lavender Patch", output)
        self.assertEqual(self.db.item_quantity(self.character.id, "raw_cotton"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "lavender_blossom"), 0)

    def test_recipe_book_default_is_grouped_and_hides_internal_keys(self):
        session = self._session_in("dwarf_workshop_tier", ["recipes"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("RECIPE BOOK", output)
        self.assertIn("Blacksmithing", output)
        self.assertIn("Tailoring", output)
        self.assertIn("Alchemy", output)
        self.assertIn("Iron Ingot", output)
        self.assertIn("TOO DIFFICULT", output)
        self.assertIn("Trivial", output)
        self.assertNotIn("smelt_iron_ingot:", output)
        self.assertIn("RECIPE <name>", output)

    def test_recipe_list_colors_owned_ingredients_magenta(self):
        # Steel Ingot needs Iron Ingot + Coal. Owning even part/all of one
        # ingredient should make that ingredient magenta while absent materials
        # retain the normal yellow recipe-material color.
        self.db.add_item(self.character.id, "iron_ingot", 1)
        session = self._session_in("dwarf_workshop_tier", ["recipes blacksmithing all"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("\x1b[92m1x Iron Ingot\x1b[0m", output)
        self.assertIn("\x1b[93m1x Coal\x1b[0m", output)

    def test_recipe_detail_shows_owned_requirements_and_station(self):
        self.db.add_item(self.character.id, "iron_ore", 1)
        session = self._session_in("dwarf_workshop_tier", ["recipe iron ingot"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("=== RECIPE ===", output)
        self.assertIn("Iron Ingot", output)
        self.assertIn("Blacksmithing", output)
        self.assertIn("Forge", output)
        self.assertIn("1/2", output)
        self.assertIn("Iron Ore", output)
        self.assertIn("Not ready: materials", output)

    def test_recipes_craftable_only_lists_items_possible_right_now(self):
        self.db.add_item(self.character.id, "iron_ore", 2)
        session = self._session_in("dwarf_workshop_tier", ["recipes craftable"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("Iron Ingot", output)
        self.assertNotIn("Iron Dagger", output)
        self.assertNotIn("CRAFT NOW", output)

    def test_profession_recipe_view_defaults_to_craftable_and_teaches_filters(self):
        self.db.add_item(self.character.id, "raw_cotton", 2)
        session = self._session_in("forest_elf_hearthwalk", ["recipes tailoring"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("TAILORING RECIPES", output)
        self.assertIn("Showing: CRAFTABLE", output)
        self.assertIn("Cotton Thread", output)
        self.assertNotIn("Cotton Gloves", output)
        self.assertIn("Filters: ALL | CRAFTABLE | ARMOR | CLOTHING | MATERIALS | DIFFICULT", output)
        self.assertIn("RECIPES TAILORING SEARCH <text>", output)

    def test_profession_all_lists_attemptable_recipes_not_too_difficult(self):
        session = self._session_in("forest_elf_hearthwalk", ["recipes tailoring all"])

        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("Showing: ALL ATTEMPTABLE", output)
        self.assertIn("Cotton Thread", output)
        self.assertNotIn("Showing: DIFFICULT", output)

    def test_profession_material_and_search_filters_are_semantic(self):
        material_session = self._session_in(
            "forest_elf_hearthwalk", ["recipes tailoring materials"]
        )
        asyncio.run(material_session.playing_prompt())
        material_output = "".join(material_session.outputs)
        self.assertIn("Showing: MATERIALS", material_output)
        self.assertIn("Cotton Thread", material_output)
        self.assertNotIn("Cotton Gloves", material_output)

        search_session = self._session_in(
            "forest_elf_hearthwalk", ["recipes tailoring search gloves"]
        )
        asyncio.run(search_session.playing_prompt())
        search_output = "".join(search_session.outputs)
        self.assertIn("SEARCH: gloves", search_output)
        self.assertIn("Trailguard Gloves", search_output)
        self.assertNotIn("Cotton Thread", search_output)

    def test_difficult_filter_separates_out_of_range_recipes(self):
        session = self._session_in(
            "forest_elf_hearthwalk", ["recipes tailoring difficult"]
        )
        asyncio.run(session.playing_prompt())

        output = "".join(session.outputs)
        self.assertIn("Showing: DIFFICULT", output)
        self.assertIn("too difficult", output)

    def test_real_room_station_allows_existing_crafting_recipe(self):
        session = self._session_in("dwarf_workshop_tier", ["craft smelt iron ingot"])
        self.db.add_item(self.character.id, "iron_ore", 2)

        async def finish_craft():
            await session.playing_prompt()
            task = session._active_craft["task"]
            await task

        with patch.object(crafting, "craft_time_seconds", return_value=0.02):
            asyncio.run(finish_craft())

        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ore"), 0)
        self.assertEqual(self.db.item_quantity(self.character.id, "iron_ingot"), 1)
        # Iron Ingot is trivial at 0: guaranteed success, but no free skill point.
        self.assertEqual(self.db.get_trade_skill_progress(self.character.id, "blacksmithing")["skill_xp"], 0)
        output = "".join(session.outputs)
        self.assertIn("Crafting: [", output)
        self.assertIn("[====================] 100%", output)
        self.assertNotIn("█", output)
        self.assertNotIn("░", output)
        self.assertNotIn("\x1b[2K", output)
        self.assertIn(
            "No Blacksmithing skill increase. Current skill: 0. "
            "This recipe is trivial for you and can no longer raise it.",
            "".join(session.outputs),
        )

    def test_gmcp_clients_get_structured_crafting_progress_without_terminal_redraw_spam(self):
        session = self._session_in("dwarf_workshop_tier", ["craft smelt iron ingot"])
        session.telnet = FakeCraftingTelnet()
        self.db.add_item(self.character.id, "iron_ore", 2)

        async def finish_craft():
            await session.playing_prompt()
            task = session._active_craft["task"]
            await task

        with patch.object(crafting, "craft_time_seconds", return_value=0.03):
            asyncio.run(finish_craft())

        crafting_messages = [
            payload for package, payload in session.telnet.messages
            if package == "Dreams.Crafting"
        ]
        self.assertGreaterEqual(len(crafting_messages), 2)
        self.assertTrue(crafting_messages[0]["active"])
        self.assertEqual(crafting_messages[0]["percent"], 0)
        self.assertFalse(crafting_messages[-1]["active"])
        self.assertEqual(crafting_messages[-1]["status"], "complete")
        self.assertEqual(crafting_messages[-1]["percent"], 100)

        output = "".join(session.outputs)
        self.assertNotIn("Crafting: [", output)
        self.assertNotIn("\x1b[2K", output)
        self.assertIn("You begin crafting Iron Ingot", output)
        self.assertIn("You finish crafting 1x Iron Ingot", output)

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

        async def finish_craft():
            await session.playing_prompt()
            task = session._active_craft["task"]
            await task

        with patch.object(crafting, "craft_time_seconds", return_value=0.02):
            asyncio.run(finish_craft())

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
