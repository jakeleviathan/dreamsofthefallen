from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AlchemyPerfumeryTests(unittest.TestCase):
    def test_production_perfumery_is_craftable_tiered_and_nonstacking(self):
        code = r"""
import asyncio
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import server
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.style_collectibles as style
from mud.database import Database

expected_effects = {
    1: (5, 20 * 60),
    2: (7, 25 * 60),
    3: (10, 30 * 60),
    4: (12, 35 * 60),
    5: (15, 40 * 60),
    6: (18, 45 * 60),
    7: (21, 50 * 60),
    8: (25, 60 * 60),
}
assert expansion.PERFUME_TIER_EFFECTS == expected_effects

perfume_recipes = [
    recipe
    for recipe in crafting.ALL_RECIPES
    if recipe.trade_skill_key == "alchemy"
    and recipe.design_status.startswith("perfumery_")
]
concentrates = [recipe for recipe in perfume_recipes if recipe.design_status == "perfumery_concentrate"]
public_formulas = [recipe for recipe in perfume_recipes if recipe.design_status == "perfumery_formula"]
secret_formulas = [recipe for recipe in perfume_recipes if recipe.design_status == "perfumery_secret_recipe"]
assert len(concentrates) == 8
assert len(public_formulas) == 40
assert len(secret_formulas) == 3
assert len(perfume_recipes) == 51

for tier, (bonus, duration) in expected_effects.items():
    band = expansion.PROFESSION_BANDS[tier - 1]
    tier_public = [
        recipe for recipe in public_formulas
        if recipe.key.startswith(f"blend_perfume_{band.key}_")
    ]
    assert len(tier_public) == 5, (tier, len(tier_public))
    for recipe in tier_public:
        item = crafting.ITEMS_BY_KEY[recipe.output_item_key]
        scent = style.FRAGRANCE_BY_KEY[recipe.output_item_key]
        assert item.category == "fragrance"
        assert item.tier == tier
        assert scent.xp_bonus_percent == bonus
        assert scent.duration_seconds == duration
        assert scent.price_sparks == 0
        assert recipe.station_key == "perfumer_bench"

# Crafted perfume is not silently turned into free boutique stock.
for key in ("perfume_greenward_first_rain", "perfume_astralite_night_market"):
    assert style.FRAGRANCE_BY_KEY[key].price_sparks == 0

# Perfumery has accessible dedicated work surfaces in starter and mature hubs.
assert economy.STATION_LABELS["perfumer_bench"] == "Perfumer's Bench"
for room in (
    "forest_elf_hearthwalk",
    "goblin_apothecary_blind",
    "waymeet_hammer_thread_row",
    "veyra_greenhall",
    "greywake_lantern_hospice",
):
    assert "perfumer_bench" in economy.ROOM_STATIONS[room], room

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "perfumery.db")
    account = db.create_account("perfumer", "x")
    character = db.create_character(account.id, "Perfumer", "human", "wizard")

    class Session:
        def __init__(self):
            self.database = db
            self.character = character
            self.outputs = []
            self.telnet = SimpleNamespace(gmcp_enabled=False)
        async def send(self, text):
            self.outputs.append(text)

    session = Session()

    # Craft the actual starter perfume chain rather than only testing catalog data.
    db.add_item(character.id, "profexp_greenward_catalyst", 1)
    db.add_item(character.id, "sunberry", 2)
    db.add_item(character.id, "grain_alcohol", 2)
    concentrate = crafting.craft_recipe(
        db,
        character.id,
        "distill_greenward_perfume_concentrate",
        station_key="perfumer_bench",
        success_roll=0.0,
        skillup_roll=1.0,
    )
    assert concentrate.success, concentrate.message
    assert db.item_quantity(character.id, "perfume_greenward_concentrate") == 1

    db.add_item(character.id, "lavender_essential_oil", 1)
    finished = crafting.craft_recipe(
        db,
        character.id,
        "blend_perfume_greenward_first_rain",
        station_key="perfumer_bench",
        success_roll=0.0,
        skillup_roll=1.0,
    )
    assert finished.success, finished.message
    assert db.item_quantity(character.id, "perfume_greenward_first_rain") == 1

    # Tier 1 starts the agreed 5% / 20-minute character-XP effect.
    asyncio.run(style._apply_fragrance(session, "Greenward First Rain"))
    active = style._active_fragrance(db, character.id)
    assert str(active["fragrance_key"]) == "perfume_greenward_first_rain"
    remaining = int(active["expires_at_epoch"]) - int(time.time())
    assert 1195 <= remaining <= 1200, remaining
    db.add_experience(character.id, 100)
    assert db.get_character_by_name(character.name).experience == 105

    # Applying another perfume replaces the current one rather than stacking it.
    db.add_item(character.id, "perfume_astralite_night_market", 1)
    asyncio.run(style._apply_fragrance(session, "Astralite Night Market"))
    active = style._active_fragrance(db, character.id)
    assert str(active["fragrance_key"]) == "perfume_astralite_night_market"
    db.add_experience(character.id, 100)
    assert db.get_character_by_name(character.name).experience == 230

    # Secret perfume formulas obey the same hidden-recipe contract and are not
    # stronger than the normal tier-8 cap.
    secret = crafting.RECIPES_BY_KEY["secret_perfume_fallen_star_no7"]
    assert not economy._recipe_visible(session, secret)
    secret_scent = style.FRAGRANCE_BY_KEY[secret.output_item_key]
    assert secret_scent.xp_bonus_percent == 25
    assert secret_scent.duration_seconds == 60 * 60

    db.set_character_room(character.id, "greywake_riftfield")
    session.character = db.get_character_by_name(character.name)
    handled = asyncio.run(expansion._discover_secret(session, "examine fallen star"))
    assert handled
    assert economy._recipe_visible(session, secret)

    # The player-facing Perfumery browser states the non-stacking / XP-only rule.
    session.outputs.clear()
    asyncio.run(expansion._show_perfumery(session))
    output = "".join(session.outputs)
    assert "PERFUMERY" in output
    assert "+5% character XP for 20 real minutes" in output
    assert "+25% character XP for 60 real minutes" in output
    assert "never tradeskill XP" in output
    assert "applying" in output.lower() or "replaces" in output.lower()

print("ALCHEMY_PERFUMERY_OK")
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
        self.assertIn("ALCHEMY_PERFUMERY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
