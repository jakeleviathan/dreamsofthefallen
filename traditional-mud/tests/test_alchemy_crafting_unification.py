"""Production regression: cultural Alchemy belongs to the shared crafting UI.

The production entry point mutates world registries, so exercise it in an
isolated child process rather than contaminating other unit-test fixtures.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AlchemyCraftingUnificationTests(unittest.TestCase):
    def test_shared_recipe_book_and_generic_learning_commands(self):
        script = r"""
import asyncio
from pathlib import Path
import tempfile

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_alchemy as catalog
import mud.regional_alchemy_runtime as regional
from mud.database import Database

assert len(catalog.RECIPES) == 300
assert all(recipe.key in crafting.RECIPES_BY_KEY for recipe in catalog.RECIPES)
assert economy._recipe_filter("alchemy")[0] == "ready"
assert economy._recipe_filter("blacksmithing")[0] == "craftable"

class LocalSession:
    def __init__(self, db, character):
        self.database = db
        self.character = character
        self.commands = []
        self.outputs = []
        self.active_enemy = None
        self._active_cast = None
        self._active_craft = None
        self.state = None

    async def send(self, message):
        self.outputs.append(message)

    async def prompt(self, prompt):
        return self.commands.pop(0) if self.commands else None

    async def playing_prompt(self):
        cmd = await self.prompt("> ")
        if cmd is not None:
            await self.send("BASE: " + cmd)

    def can_receive_item(self, item_key, quantity):
        return True

economy.install_economy_loop_runtime(LocalSession)
regional.install_regional_alchemy_runtime(LocalSession)

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "alchemy-unified.db")
    account = db.create_account("alchemycraft", "test-hash")
    character = db.create_character(account.id, "Brewster", "goblin", "priest")
    hall = catalog.BY_KEY["goblin"].hall
    db.set_character_room(character.id, hall)
    character = db.get_character_by_name("Brewster")
    session = LocalSession(db, character)

    async def command(text):
        session.outputs.clear()
        session.commands.append(text)
        await session.playing_prompt()
        return "".join(session.outputs)

    beginner = catalog.RECIPES_BY_KEY["regional_goblin_0_0"]
    beginner_name = crafting.ITEMS_BY_KEY[beginner.output_item_key].name
    field = catalog.RECIPES_BY_KEY["regional_goblin_1_0"]
    field_name = crafting.ITEMS_BY_KEY[field.output_item_key].name
    secret = catalog.RECIPES_BY_KEY["regional_secret_goblin_0"]
    secret_name = crafting.ITEMS_BY_KEY[secret.output_item_key].name

    before = asyncio.run(command("recipes alchemy"))
    assert "ALCHEMY RECIPES" in before
    assert "ALCHEMY STUDIES" in before
    assert "TRAIN ALCHEMY" in before
    assert beginner_name not in before
    assert secret_name not in before

    studied = asyncio.run(command("train alchemy"))
    assert "apprentice recipes" in studied
    assert catalog.lesson_flag("goblin", 0) in db.list_flags(character.id)
    after = asyncio.run(command("recipes alchemy"))
    assert beginner_name in after
    assert "Traditions studied: 1/9" in after
    assert economy._resolve_recipe(beginner_name, session)[0].key == beginner.key
    assert "Ingredients" in asyncio.run(command("recipe " + beginner_name))

    browse = asyncio.run(command("browse manuals"))
    assert "Field Goblin Alchemy Manual" in browse
    db.add_sols(character.id, 100)
    bought = asyncio.run(command("buy Field Goblin Alchemy Manual"))
    assert "Purchased" in bought
    book = catalog.book_key("goblin", 1)
    assert db.item_quantity(character.id, book) == 1
    read = asyncio.run(command("read Field Goblin Alchemy Manual"))
    assert "RECIPES ALCHEMY" in read
    assert catalog.lesson_flag("goblin", 1) in db.list_flags(character.id)
    assert db.item_quantity(character.id, book) == 1
    assert field_name in asyncio.run(command("recipes alchemy"))

    hidden = asyncio.run(command("recipes alchemy search " + secret_name))
    assert secret_name not in hidden
    assert "No recipes match" in hidden
    experimented = asyncio.run(command("craft experiment"))
    assert "experiment" in experimented.lower() or "skill" in experimented.lower()
    db.grant_flag(character.id, catalog.secret_flag("goblin", 0))
    assert secret_name in asyncio.run(
        command("recipes alchemy search " + secret_name)
    )
    assert "BLACKSMITHING RECIPES" in asyncio.run(command("recipes blacksmithing"))

print("PASS: all 300 formulas registered; unified browsing, learning, buying, reading, and secret gating")
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=100,
        )
        self.assertEqual(
            completed.returncode, 0,
            completed.stdout + "\n" + completed.stderr,
        )
        self.assertIn("PASS:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
