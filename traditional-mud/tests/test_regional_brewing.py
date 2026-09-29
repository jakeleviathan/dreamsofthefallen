from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RegionalBrewingTests(unittest.TestCase):
    def test_full_brewing_system_is_persistent_regional_and_social(self):
        code = r"""
import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import server
import mud.brewing as brewing
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.regional_brewing as regional
import mud.regional_brewing_runtime as runtime
import mud.world as world
from mud.database import Database
from mud.stats import CharacterStats

assert "brewing" in crafting.PROFESSIONS_BY_KEY
assert "enchanting" not in crafting.PROFESSIONS_BY_KEY
assert not [r for r in crafting.ALL_RECIPES if r.trade_skill_key == "enchanting"]

counts = expansion.production_recipe_counts()
assert counts["brewing"] >= 80, counts
assert regional.catalog_counts()["traditions"] == 9
assert regional.catalog_counts()["regional_drinks"] == 9 * 8 * 2
assert regional.catalog_counts()["hidden_drinks"] == 9
assert len(brewing.BREW_PROCESSES) >= 80 + 9 * 8 * 2 + 9

for tradition in regional.TRADITIONS:
    assert "brewhouse" in economy.ROOM_STATIONS[tradition.hall]
    assert "brewers_yeast_crock" in economy.ROOM_RESOURCE_NODE_KEYS[tradition.hall]
    assert "wild_yeast_jar" in economy.ROOM_RESOURCE_NODE_KEYS[tradition.hall]
    npc_key = f"regional_brewer_{tradition.key}"
    assert npc_key in world.NPCS_BY_KEY
    assert npc_key in world.ROOMS_BY_KEY[tradition.hall].npc_keys

assert "wild_honeycomb" in crafting.RESOURCE_NODES_BY_KEY
assert "cinderbean_shrub" in crafting.RESOURCE_NODES_BY_KEY

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "brewing.db")
    account = db.create_account("brewer", "x")
    character = db.create_character(account.id, "BottleTester", "human", "druid")
    db.set_character_room(character.id, "waymeet_fifth_lantern")
    character = db.get_character_by_name(character.name)

    class Session:
        def __init__(self):
            self.database = db
            self.character = character
            self.outputs = []
            self.active_enemy = None
            self.combatant = SimpleNamespace(
                current_hp=20,
                max_hp=40,
                current_mana=20,
                max_mana=40,
                stats=CharacterStats(),
            )
        async def send(self, text):
            self.outputs.append(text)
        async def send_client_state(self):
            return None

    session = Session()

    async def flow():
        # Regional teaching exposes the first Waymeet house band at skill 0.
        await runtime._train(session)
        assert regional.lesson_flag("waymeet", 0) in db.list_flags(character.id)

        # Water quality is an actual preparation choice.
        db.add_item(character.id, "spring_water", 1)
        await runtime._filter_water(session)
        assert db.item_quantity(character.id, "filtered_brewing_water") == 1

        # Base brewing can swap both yeast and water profiles. Successful work
        # creates a persistent batch instead of an immediate inventory item.
        db.add_item(character.id, "field_grain", 2)
        db.add_item(character.id, "sunberry", 1)
        db.add_item(character.id, "wild_yeast_culture", 1)
        recipe = crafting.RECIPES_BY_KEY["brew_greenward_field_ale"]
        await runtime.start_brew(
            session,
            recipe,
            requested_yeast="wild_yeast_culture",
            requested_water="filtered_brewing_water",
        )
        rows = runtime._batch_rows(session)
        assert len(rows) == 1, rows
        row = rows[0]
        assert row["yeast_key"] == "wild_yeast_culture"
        assert row["water_key"] == "filtered_brewing_water"
        assert int(row["quantity"]) == 2
        assert db.item_quantity(character.id, recipe.output_item_key) == 0

        # Force the test clock past fermentation, choose optional cellaring, then
        # force that stage ready and bottle the cellared variant.
        batch_id = int(row["id"])
        past = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat()
        with db.connect() as conn:
            conn.execute(
                "UPDATE brewing_batches SET ferment_ready_at=? WHERE id=?",
                (past, batch_id),
            )
        await runtime._age(session, str(batch_id))
        aged = runtime._batch_row(session, batch_id)
        assert aged["stage"] == "aging"
        with db.connect() as conn:
            conn.execute(
                "UPDATE brewing_batches SET age_ready_at=? WHERE id=?",
                (past, batch_id),
            )
        await runtime._bottle(session, str(batch_id))
        aged_key = brewing.process_for(recipe.key).aged_output_item_key
        assert aged_key
        assert db.item_quantity(character.id, aged_key) == 2
        assert runtime._batch_row(session, batch_id) is None

        # Brew refreshment is a single slot separate from food nourishment.
        before_might = session.combatant.stats.might
        await runtime._apply_brew(
            session,
            crafting.ITEMS_BY_KEY[aged_key],
            consume_inventory=True,
        )
        assert db.item_quantity(character.id, aged_key) == 1
        assert session.combatant.stats.might >= before_might

        # A bottle can be turned into a room-visible shared tasting round.
        await runtime._pour(session, crafting.ITEMS_BY_KEY[aged_key].name)
        bar = runtime.room_bar_entries(session)
        assert len(bar) == 1
        cups_before = int(bar[0]["cups"])
        await runtime._taste(session, crafting.ITEMS_BY_KEY[aged_key].name)
        bar_after = runtime.room_bar_entries(session)
        assert int(bar_after[0]["cups"]) == cups_before - 1

    asyncio.run(flow())

    assert any("start batch" in text.lower() for text in session.outputs)
    assert any("cellar" in text.lower() for text in session.outputs)
    assert any("tasting round" in text.lower() for text in session.outputs)

print("REGIONAL_BREWING_OK")
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
        self.assertIn("REGIONAL_BREWING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
