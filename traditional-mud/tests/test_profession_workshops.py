from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductionProfessionOverhaulTests(unittest.TestCase):
    def test_full_profession_stack_is_live_and_player_facing(self):
        code = r"""
import asyncio
import re
import tempfile
from pathlib import Path

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_workshops as workshops
from mud.database import Database
from mud.stats import CharacterStats

ANSI = re.compile(r"\x1b\[[0-9;]*m")

assert server.PlayerSession._profession_workshops_runtime_installed

# Enchanting and Cooking are real recipe professions now.
for key in ("enchanting", "cooking"):
    recipes = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == key]
    assert recipes, key

assert "arcane_residue" in crafting.ITEMS_BY_KEY
assert "field_grain" in crafting.ITEMS_BY_KEY
assert "marsh_onion" in crafting.ITEMS_BY_KEY
assert "fieldgrain_patch" in crafting.RESOURCE_NODES_BY_KEY
assert "marsh_onion_bed" in crafting.RESOURCE_NODES_BY_KEY
assert "enchanting_table" in economy.ROOM_STATIONS["dwarf_workshop_tier"]
assert "cookfire" in economy.ROOM_STATIONS["forest_elf_hearthwalk"]
assert any(drop.item_key == "arcane_residue" for drop in economy.LOOT_TABLES["small_imp"])

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "professions.db")
    account = db.create_account("profession_test", "x")
    character = db.create_character(account.id, "ProfessionTester", "human", "druid")
    db.set_character_room(character.id, "dwarf_workshop_tier")
    character = db.get_character_by_name(character.name)

    class Session:
        def __init__(self):
            self.database = db
            self.character = character
            self.outputs = []
            self.active_enemy = None
        async def send(self, text):
            self.outputs.append(text)

    session = Session()

    asyncio.run(workshops._show_professions(session))
    sheet = ANSI.sub("", "".join(session.outputs))
    for label in (
        "Blacksmithing", "Tailoring", "Enchanting", "Alchemy", "Cooking",
        "Mining", "Harvesting", "Herbalism",
    ):
        assert label in sheet, label
    assert "PROFESSIONS & GATHERING" in sheet
    assert "Recipes" in sheet
    assert "Next" in sheet

    session.outputs.clear()
    asyncio.run(workshops._show_workshop(session, "blacksmithing"))
    forge = ANSI.sub("", "".join(session.outputs))
    assert "FORGE" in forge
    assert "SMELTING & ALLOYING" in forge
    assert "WEAPONS" in forge
    assert "Iron Ingot" in forge
    assert "HERE" in forge

    db.set_character_room(character.id, "forest_elf_hearthwalk")
    session.character = db.get_character_by_name(character.name)
    session.outputs.clear()
    asyncio.run(workshops._show_workshop(session, "tailoring"))
    tailoring = ANSI.sub("", "".join(session.outputs))
    assert "TAILORING WORKBENCH" in tailoring
    assert "FIBER PREPARATION" in tailoring
    assert "WEAVING" in tailoring
    assert "FINISHED GOODS" in tailoring
    assert "HERE" in tailoring

    session.outputs.clear()
    asyncio.run(workshops._show_workshop(session, "cooking"))
    cooking = ANSI.sub("", "".join(session.outputs))
    assert "COOKFIRE" in cooking
    assert "Trail Flatbread" in cooking
    assert "MEALS & PROVISIONS" in cooking

    # Starter Cooking is already trivial at skill 0: it crafts reliably without a free skill point.
    db.add_item(character.id, "field_grain", 2)
    db.add_item(character.id, "spring_water", 1)
    result = crafting.craft_recipe(
        db, character.id, "cook_trail_flatbread", station_key="cookfire"
    )
    assert result.success, result.message
    assert db.item_quantity(character.id, "trail_flatbread") == 1
    assert db.get_trade_skill_progress(character.id, "cooking")["skill_xp"] == 0

    # Starter Enchanting follows the same trivial-recipe rule.
    db.add_item(character.id, "iron_dagger", 1)
    db.add_item(character.id, "arcane_residue", 1)
    db.add_item(character.id, "lavender_essential_oil", 1)
    result = crafting.craft_recipe(
        db, character.id, "enchant_runed_iron_dagger", station_key="enchanting_table"
    )
    assert result.success, result.message
    assert db.item_quantity(character.id, "runed_iron_dagger") == 1
    assert db.get_trade_skill_progress(character.id, "enchanting")["skill_xp"] == 0

    # Prepared food is not decorative inventory: EAT consumes it, heals, and
    # applies its authored temporary nourishment bonus.
    db.add_item(character.id, "greenleaf_broth", 1)
    class Combatant:
        current_hp = 5
        max_hp = 20
        current_mana = 10
        max_mana = 20
        stats = CharacterStats()
    session.combatant = Combatant()
    async def send_client_state():
        return None
    session.send_client_state = send_client_state
    asyncio.run(workshops._eat(session, "greenleaf broth"))
    assert db.item_quantity(character.id, "greenleaf_broth") == 0
    assert session.combatant.current_hp == 17
    assert session.combatant.stats.love == 1

    # The common gathering dashboard sees the new cooking resource route.
    db.set_character_room(character.id, "forest_elf_greenway")
    session.character = db.get_character_by_name(character.name)
    session.outputs.clear()
    asyncio.run(workshops._show_gathering_skill(session, "harvesting"))
    harvesting = ANSI.sub("", "".join(session.outputs))
    assert "HARVESTING" in harvesting
    assert "Field-Grain Patch" in harvesting
    assert "Field Grain" in harvesting
    assert "Cotton Patch" in harvesting

    # It also adapts the custom Goblin gathering service, not just generic nodes.
    db.set_character_room(character.id, "goblin_rootsnag_bank")
    session.character = db.get_character_by_name(character.name)
    session.outputs.clear()
    asyncio.run(workshops._show_gathering_skill(session, "herbalism"))
    herbalism = ANSI.sub("", "".join(session.outputs))
    assert "HERBALISM" in herbalism
    assert "Rootsnag Bitterroot" in herbalism
    assert "Bitterroot" in herbalism

# Recipe book receives the two newly real professions too.
assert any(r.trade_skill_key == "enchanting" for r in crafting.ALL_RECIPES)
assert any(r.trade_skill_key == "cooking" for r in crafting.ALL_RECIPES)
print("PROFESSION_OVERHAUL_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROFESSION_OVERHAUL_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
