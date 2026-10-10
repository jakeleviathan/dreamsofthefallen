from __future__ import annotations

import asyncio
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import mud.astronomy as astronomy
import mud.crafting as crafting
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.stats import CharacterStats
from mud.waymeet_frontier import (
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
)
from mud.world import ROOMS_BY_KEY, RoomDefinition

ROOT = Path(__file__).resolve().parents[1]


class World:
    def __init__(self):
        self.legacy_rooms = {
            **ROOMS_BY_KEY,
            WAYMEET_COMMONHOUSE_KEY: RoomDefinition(
                WAYMEET_COMMONHOUSE_KEY, "Commonhouse Yard", "A quiet yard",
                "waymeet_frontier", tags=("safe", "social"),
            ),
            WAYMEET_LANTERN_MARKET_KEY: RoomDefinition(
                WAYMEET_LANTERN_MARKET_KEY, "Lantern Market", "An open market",
                "waymeet_frontier", tags=("market", "safe"),
            ),
            WAYMEET_CRAFT_ROW_KEY: RoomDefinition(
                WAYMEET_CRAFT_ROW_KEY, "Hammer and Thread Row", "Open work bays",
                "waymeet_frontier", tags=("crafting", "safe"),
            ),
            "sablewater_heron_flats": RoomDefinition(
                "sablewater_heron_flats", "Heron Flats", "A riverbank",
                "sablewater_reach", tags=("river", "safe"),
            ),
            "waymeet_fifth_lantern": RoomDefinition(
                "waymeet_fifth_lantern", "The Fifth Lantern", "A tavern",
                "waymeet_frontier", tags=("indoors", "tavern"),
            ),
        }
        self.weather = {}

        class State:
            def __init__(state_self, parent):
                state_self.parent = parent

            def weather_for(state_self, region):
                return state_self.parent.weather.get(region, "clear")

        self.state = State(self)


WORLD = World()


class Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.messages = []
        self.command = ""
        self.state = None
        self.active_enemy = None

    async def prompt(self, _text):
        return self.command

    async def send(self, text):
        self.messages.append(text)

    async def show_current_room(self):
        await self.send("ROOM\r\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        await self.send(f"DELEGATED:{command}\r\n")


def act(session, command):
    session.command = command
    before = len(session.messages)
    asyncio.run(session.playing_prompt())
    return "".join(session.messages[before:])


def moment(day, hour):
    return AstralisMoment(day_number=day, hour=hour, minute=0, total_minutes=(day - 1) * 1440 + hour * 60)


class AstronomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_items = crafting.ITEMS
        cls.previous_by_key = {item.key: crafting.ITEMS_BY_KEY.get(item.key) for item in astronomy.ITEMS}
        astronomy.install_astronomy_runtime(Session, WORLD)

    @classmethod
    def tearDownClass(cls):
        crafting.ITEMS = cls.previous_items
        for key, previous in cls.previous_by_key.items():
            if previous is None:
                crafting.ITEMS_BY_KEY.pop(key, None)
            else:
                crafting.ITEMS_BY_KEY[key] = previous

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Database(Path(self.tmp.name) / "astronomy.db")
        account = self.database.create_account("stargazer", "hash")
        self.character = self.database.create_character(
            account.id, "NightWatcher", "human", "priest",
            CharacterStats(might=5, grace=6, love=8, mind=7, hp=6),
        )
        self.session = Session(self.database, self.character)
        WORLD.weather.clear()
        self.to_room(WAYMEET_COMMONHOUSE_KEY)

    def to_room(self, room):
        self.database.set_character_room(self.character.id, room)
        self.session.character = self.database.get_character_by_name(self.character.name)

    def test_item_registration_is_idempotent_and_combat_neutral(self):
        original_count = len(crafting.ITEMS)
        astronomy.install_astronomy_content()
        self.assertEqual(len(crafting.ITEMS), original_count)
        for item in astronomy.ITEMS:
            self.assertIn(item.key, crafting.ITEMS_BY_KEY)
            self.assertIsNone(item.equipment)
            self.assertIsNone(item.consumable)

    def test_daytime_and_clouds_are_not_journal_discoveries(self):
        self.database.add_item(self.character.id, astronomy.TELESCOPE_KEY)
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 13)):
            self.assertIn("after nightfall", act(self.session, "OBSERVE SKY"))
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            WORLD.weather["waymeet_frontier"] = "cloudy"
            self.assertIn("cloudy", act(self.session, "OBSERVE SKY"))
            WORLD.weather["waymeet_frontier"] = "clear"
        self.assertEqual(astronomy.recorded_sightings(self.database, self.character.id), [])

    def test_no_telescope_no_records_but_naked_eye_can_watch(self):
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            text = act(self.session, "STARGAZE")
        self.assertIn("telescope", text.lower())
        self.assertEqual(len(astronomy.recorded_sightings(self.database, self.character.id)), 0)

    def test_market_purchase_and_bench_assembly_really_use_inventory_and_sols(self):
        self.to_room(WAYMEET_LANTERN_MARKET_KEY)
        self.assertIn("24 sparks", act(self.session, "SKY SHOP"))
        self.assertIn("don't have enough", act(self.session, "BUY TELESCOPE"))
        self.database.add_sols(self.character.id, 40)
        self.assertIn("Field Telescope", act(self.session, "BUY TELESCOPE"))
        self.assertEqual(self.database.get_sols(self.character.id), 16)
        self.assertEqual(self.database.item_quantity(self.character.id, astronomy.TELESCOPE_KEY), 1)
        self.assertIn("already carry", act(self.session, "BUY TELESCOPE"))
        self.database.consume_item(self.character.id, astronomy.TELESCOPE_KEY)
        self.assertIn("Polished Telescope Lens", act(self.session, "BUY LENS"))
        self.assertEqual(self.database.get_sols(self.character.id), 10)
        self.database.add_item(self.character.id, "iron_ingot")
        self.database.add_item(self.character.id, "cotton_thread")
        self.to_room(WAYMEET_CRAFT_ROW_KEY)
        self.assertIn("usable field telescope", act(self.session, "ASSEMBLE TELESCOPE"))
        self.assertEqual(self.database.item_quantity(self.character.id, astronomy.TELESCOPE_KEY), 1)
        for key in astronomy.TELESCOPE_RECIPE:
            self.assertEqual(self.database.item_quantity(self.character.id, key), 0)

    def test_discoveries_are_persistent_and_duplicates_are_not_farmed(self):
        self.database.add_item(self.character.id, astronomy.TELESCOPE_KEY)
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            first = act(self.session, "OBSERVE SKY")
            second = act(self.session, "OBSERVE SKY")
        self.assertIn("Lantern Thread", first)
        self.assertIn("Crossroads Knot", first)
        self.assertIn("not every night", second.lower())
        rows = astronomy.recorded_sightings(self.database, self.character.id)
        self.assertEqual({row["sighting_key"] for row in rows}, {"season_spring", "regional_waymeet_frontier"})
        fresh = Session(Database(self.database.path), self.database.get_character_by_name(self.character.name))
        self.assertIn("Lantern Thread", act(fresh, "SKY JOURNAL"))
        self.assertIn("Astralis day 1", act(fresh, "CONSTELLATIONS"))
        self.assertEqual(fresh.database.item_quantity(self.character.id, astronomy.CHART_KEY), 0)

    def test_regional_and_season_changes_unlock_one_keepsake_not_experience(self):
        self.database.add_item(self.character.id, astronomy.TELESCOPE_KEY)
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            act(self.session, "CHART SKY")
        self.to_room("sablewater_heron_flats")
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            result = act(self.session, "CHART SKY")
            repeat = act(self.session, "CHART SKY")
        self.assertIn("fold your first three sketches", result)
        self.assertEqual(self.database.item_quantity(self.character.id, astronomy.CHART_KEY), 1)
        self.assertIn("not every night", repeat.lower())
        self.assertEqual(len(astronomy.recorded_sightings(self.database, self.character.id)), 3)

    def test_new_moon_anomaly_requires_alignment_and_rewards_one_charm(self):
        self.database.add_item(self.character.id, astronomy.TELESCOPE_KEY)
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(85, 23)):
            self.assertNotIn("Unlisted Star", act(self.session, "OBSERVE SKY"))
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(87, 23)):
            result = act(self.session, "OBSERVE SKY")
            act(self.session, "OBSERVE SKY")
        self.assertIn("Unlisted Star", result)
        self.assertEqual(self.database.item_quantity(self.character.id, astronomy.CHARM_KEY), 1)
        self.assertIn(astronomy.CHARM_FLAG, self.database.list_flags(self.character.id))

    def test_indoor_planar_and_combat_constraints(self):
        self.database.add_item(self.character.id, astronomy.TELESCOPE_KEY)
        self.to_room("waymeet_fifth_lantern")
        with patch.object(astronomy.ASTRALIS_CLOCK, "now", return_value=moment(1, 23)):
            self.assertIn("open sky", act(self.session, "OBSERVE SKY"))
            self.to_room(WAYMEET_COMMONHOUSE_KEY)
            self.session.active_enemy = object()
            self.assertIn("fight", act(self.session, "OBSERVE SKY"))
        self.assertEqual(astronomy.recorded_sightings(self.database, self.character.id), [])

    def test_other_commands_are_delegated_and_catalog_lists_hobby(self):
        from mud.command_guide import COMMANDS
        self.assertIn("DELEGATED:who", act(self.session, "who"))
        self.assertTrue(any("OBSERVE SKY" in entry.syntax for entry in COMMANDS))
        self.assertIn("No experience", act(self.session, "ASTRONOMY"))

    def test_production_server_boots_with_astronomy_installed(self):
        code = """
import server
from mud.crafting import ITEMS_BY_KEY
from mud.astronomy import TELESCOPE_KEY
assert server.PlayerSession._astronomy_installed
assert TELESCOPE_KEY in ITEMS_BY_KEY
print("ASTRONOMY_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)}, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ASTRONOMY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
