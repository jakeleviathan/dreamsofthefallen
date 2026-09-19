from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


class DeepProfessionExpansionTests(unittest.TestCase):
    def test_production_catalog_is_deep_balanced_and_integrated(self):
        code = r"""
import asyncio
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
from mud.database import Database
from mud.stats import CharacterStats

counts = expansion.production_recipe_counts()
print("PROFESSION_COUNTS", counts)
assert set(counts) == {"blacksmithing", "tailoring", "enchanting", "alchemy", "cooking"}
assert all(count >= 80 for count in counts.values()), counts

# Every trade spans a real progression instead of clustering at starter skill.
for profession in counts:
    trivial_values = sorted({
        recipe.trivial_skill
        for recipe in crafting.ALL_RECIPES
        if recipe.trade_skill_key == profession
    })
    assert len(trivial_values) >= 8, (profession, trivial_values)
    assert trivial_values[0] <= 10, (profession, trivial_values[0])
    assert trivial_values[-1] >= 175, (profession, trivial_values[-1])

# Blacksmithing and Tailoring now cover the equipment slots that their old
# sword/chest and hood/tunic ladders left empty.
for key in (
    "artisan_iron_shield",
    "artisan_iron_gauntlets",
    "artisan_iron_greaves",
    "artisan_iron_boots",
    "artisan_cotton_gloves",
    "artisan_cotton_boots",
    "artisan_cotton_trousers",
    "artisan_cotton_robe",
):
    assert key in crafting.ITEMS_BY_KEY, key
    assert crafting.ITEMS_BY_KEY[key].equipment is not None

# Alchemy and Cooking have 8 full bands of ten generated recipes, while
# Enchanting consumes real crafted base gear rather than conjuring gear from
# Arcane Residue alone.
for band in expansion.PROFESSION_BANDS:
    alchemy = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == "alchemy" and band.key in r.key]
    cooking = [
        r for r in crafting.ALL_RECIPES
        if r.trade_skill_key == "cooking"
        and any(i.key in r.key for i in expansion.PANTRY_INGREDIENTS if i.tier == band.tier)
    ]
    enchanting = [r for r in crafting.ALL_RECIPES if r.trade_skill_key == "enchanting" and band.key in r.key]
    assert len(alchemy) >= 10, (band.key, len(alchemy))
    assert len(cooking) >= 10, (band.key, len(cooking))
    assert len(enchanting) >= 10, (band.key, len(enchanting))

# Pantry ingredients are actual gatherables in authored rooms, and mature hubs
# have the stations necessary to use the expanded professions.
for ingredient in expansion.PANTRY_INGREDIENTS:
    assert ingredient.key in crafting.ITEMS_BY_KEY
    assert ingredient.node_key in crafting.RESOURCE_NODES_BY_KEY
    assert ingredient.node_key in economy.ROOM_RESOURCE_NODE_KEYS[ingredient.room_key]

assert "cookfire" in economy.ROOM_STATIONS["veyra_public_hearth"]
assert "alchemy_table" in economy.ROOM_STATIONS["veyra_greenhall"]
assert "enchanting_table" in economy.ROOM_STATIONS["veyra_scholars_rise"]
assert "forge" in economy.ROOM_STATIONS["waymeet_hammer_thread_row"]
assert "loom" in economy.ROOM_STATIONS["waymeet_hammer_thread_row"]

# Production validation guarantees there are no decorative recipes with missing
# materials or missing outputs.
assert expansion.validate_profession_expansion() == counts

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "deep_professions.db")
    account = db.create_account("deep_professions", "x")
    character = db.create_character(account.id, "DeepCrafter", "human", "wizard")

    class Session:
        def __init__(self):
            self.database = db
            self.character = character
            self.outputs = []
            self.active_enemy = None
            self.combatant = SimpleNamespace(
                current_hp=10,
                max_hp=100,
                current_mana=25,
                max_mana=100,
                stats=CharacterStats(),
            )
        async def send(self, text):
            self.outputs.append(text)
        async def send_client_state(self):
            return None

    session = Session()

    # Drinkable Alchemy outputs are real consumables.
    potion_key = "profexp_greenward_healing_draught"
    db.add_item(character.id, potion_key, 1)
    asyncio.run(expansion._drink(session, "greenward healing"))
    assert db.item_quantity(character.id, potion_key) == 0
    assert session.combatant.current_hp > 10
    assert any("You drink Greenward Healing Draught" in text for text in session.outputs)

    # Secret recipes are absent from normal resolution until their physical
    # discovery interaction grants the corresponding character flag.
    secret = crafting.RECIPES_BY_KEY["secret_fallen_star_greatblade"]
    assert not economy._recipe_visible(session, secret)
    resolved, _error = economy._resolve_recipe("fallen-star greatblade", session)
    assert resolved is None

    db.set_character_room(character.id, "human_cinder_lane")
    session.character = db.get_character_by_name(character.name)
    session.outputs.clear()
    handled = asyncio.run(expansion._discover_secret(session, "examine anvil"))
    assert handled
    assert economy._recipe_visible(session, secret)
    resolved, error = economy._resolve_recipe("fallen-star greatblade", session)
    assert error is None
    assert resolved is secret
    assert any("Secret recipe discovered" in text for text in session.outputs)

print("DEEP_PROFESSION_EXPANSION_OK")
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
        self.assertIn("DEEP_PROFESSION_EXPANSION_OK", result.stdout)
        match = re.search(r"PROFESSION_COUNTS (.+)", result.stdout)
        self.assertIsNotNone(match, result.stdout)


if __name__ == "__main__":
    unittest.main()
