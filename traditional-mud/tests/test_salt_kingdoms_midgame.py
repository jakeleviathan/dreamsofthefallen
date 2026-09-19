import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.salt_kingdoms_midgame as salt


class SaltKingdomsDesignTests(unittest.TestCase):
    def test_region_is_major_city_plus_two_distinct_dungeons(self):
        self.assertEqual(len(salt.SURFACE_ROOM_KEYS), 10)
        self.assertEqual(len(salt.CITY_ROOM_KEYS), 8)
        self.assertEqual(len(salt.GLASS_KEEL_ROOM_KEYS), 7)
        self.assertEqual(len(salt.UNDERTIDE_ROOM_KEYS), 8)
        self.assertEqual(len(salt.SALT_KINGDOMS_ROOMS), 33)
        self.assertTrue(set(salt.GLASS_KEEL_ROOM_KEYS).isdisjoint(salt.UNDERTIDE_ROOM_KEYS))
        self.assertIn(salt.KEELSPIRE_CROWN_SQUARE_KEY, salt.CITY_ROOM_KEYS)
        self.assertIn(salt.GLASS_KEEL_TIDEHOLD_KEY, salt.GLASS_KEEL_ROOM_KEYS)
        self.assertIn(salt.UNDERTIDE_RELEASE_KEY, salt.UNDERTIDE_ROOM_KEYS)

    def test_story_band_reaches_level_thirty_with_expected_shape(self):
        self.assertEqual(
            [quest.minimum_level for quest in salt.SALT_KINGDOMS_QUESTS],
            [21, 23, 26, 27, 30],
        )
        self.assertIn("dead inland sea", salt.ARRIVAL_QUEST.description)
        self.assertIn("tide instrument", salt.GLASS_KEEL_QUEST.description)
        self.assertIn("Keelspire", salt.FACTION_QUEST.description)
        self.assertIn("obvious guardian", salt.UNDERTIDE_QUEST.description)
        self.assertIn("permanently changes routes", salt.CAPSTONE_QUEST.objective_steps[-1][1])

    def test_actual_production_entrypoint_installs_region_and_all_three_map_endings(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.broken_reach_midgame import CAPSTONE_COMPLETE_FLAG as BROKEN_COMPLETE, FAR_WATCH_KEY
from mud.room_engine import PlayerRoomContext
from mud.salt_kingdoms_midgame import (
    SALT_KINGDOMS_ROOM_KEYS,
    SALTWIND_GATE_KEY,
    KEELSPIRE_HARBOR_VAULT_KEY,
    UNDERTIDE_INTAKE_KEY,
    GLASS_KEEL_COMPLETE_FLAG,
    FACTION_COMPLETE_FLAG,
    KEELSPIRE_GATE_KEY,
    KEELSPIRE_QUAYS_KEY,
    OLD_BREAKWATER_KEY,
    TIDEMARK_SINK_KEY,
    HARBOR_ENDING_FLAG,
    KEELSPIRE_THREE_WELLS_KEY,
    DUSTWELL_CAMP_KEY,
    CISTERN_ROAD_KEY,
    WELLS_ENDING_FLAG,
    PILGRIM_SALT_KEY,
    SPRINGCUT_GORGE_KEY,
    CURRENT_ENDING_FLAG,
)
from mud.world import ROOMS_BY_KEY

assert server.PlayerSession._salt_kingdoms_midgame_installed
for key in SALT_KINGDOMS_ROOM_KEYS:
    assert key in ROOMS_BY_KEY, key
    assert key in server.WORLD.legacy_rooms, key

low = PlayerRoomContext(1, "goblin", "priest", 20, frozenset({BROKEN_COMPLETE}))
assert "west" not in {item.direction for item in server.WORLD.build_view(FAR_WATCH_KEY, low).exits}
no_clear = PlayerRoomContext(1, "goblin", "priest", 21, frozenset())
assert "west" not in {item.direction for item in server.WORLD.build_view(FAR_WATCH_KEY, no_clear).exits}
ready = PlayerRoomContext(1, "goblin", "priest", 21, frozenset({BROKEN_COMPLETE}))
entry = server.WORLD.resolve_exit(FAR_WATCH_KEY, "west", ready)
assert entry.allowed and entry.exit.destination_key == SALTWIND_GATE_KEY

locked = PlayerRoomContext(1, "goblin", "priest", 27, frozenset())
assert "down" not in {item.direction for item in server.WORLD.build_view(KEELSPIRE_HARBOR_VAULT_KEY, locked).exits}
engine_ready = PlayerRoomContext(1, "goblin", "priest", 27, frozenset({GLASS_KEEL_COMPLETE_FLAG, FACTION_COMPLETE_FLAG}))
engine_entry = server.WORLD.resolve_exit(KEELSPIRE_HARBOR_VAULT_KEY, "down", engine_ready)
assert engine_entry.allowed and engine_entry.exit.destination_key == UNDERTIDE_INTAKE_KEY

pre = PlayerRoomContext(1, "goblin", "priest", 30, frozenset())
pre_gate = {item.direction: item.destination_key for item in server.WORLD.build_view(KEELSPIRE_GATE_KEY, pre).exits}
assert pre_gate["north"] == OLD_BREAKWATER_KEY
pre_quays = {item.direction for item in server.WORLD.build_view(KEELSPIRE_QUAYS_KEY, pre).exits}
assert "north" not in pre_quays

harbor = PlayerRoomContext(1, "goblin", "priest", 30, frozenset({HARBOR_ENDING_FLAG}))
harbor_gate = {item.direction: item.destination_key for item in server.WORLD.build_view(KEELSPIRE_GATE_KEY, harbor).exits}
assert "north" not in harbor_gate
harbor_quays = {item.direction: item.destination_key for item in server.WORLD.build_view(KEELSPIRE_QUAYS_KEY, harbor).exits}
assert harbor_quays["north"] == TIDEMARK_SINK_KEY

wells = PlayerRoomContext(1, "goblin", "priest", 30, frozenset({WELLS_ENDING_FLAG}))
well_city = {item.direction: item.destination_key for item in server.WORLD.build_view(KEELSPIRE_THREE_WELLS_KEY, wells).exits}
well_road = {item.direction: item.destination_key for item in server.WORLD.build_view(DUSTWELL_CAMP_KEY, wells).exits}
assert well_city["north"] == CISTERN_ROAD_KEY
assert well_road["east"] == CISTERN_ROAD_KEY

current = PlayerRoomContext(1, "goblin", "priest", 30, frozenset({CURRENT_ENDING_FLAG}))
current_route = {item.direction: item.destination_key for item in server.WORLD.build_view(PILGRIM_SALT_KEY, current).exits}
assert current_route["down"] == SPRINGCUT_GORGE_KEY
print("SALT_KINGDOMS_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("SALT_KINGDOMS_PRODUCTION_OK", result.stdout)


class FakeDB:
    def __init__(self, character):
        self.character = character
        self.flags = set()
        self.quests = {}
        self.items = {}
        self.xp = []

    def list_flags(self, _cid):
        return frozenset(self.flags)

    def grant_flag(self, _cid, flag):
        self.flags.add(flag)

    def get_quest(self, _cid, key):
        row = self.quests.get(key)
        return None if row is None else dict(row)

    def start_quest(self, _cid, key, step):
        self.quests.setdefault(key, {"quest_key": key, "status": "active", "current_step": step})

    def advance_quest(self, _cid, key, step):
        self.quests[key]["current_step"] = step

    def complete_quest(self, _cid, key):
        self.quests[key]["status"] = "completed"
        self.quests[key]["current_step"] = "complete"

    def add_experience(self, _cid, amount):
        self.xp.append(amount)
        return self.character.level

    def get_character_by_name(self, _name):
        return self.character

    def item_quantity(self, _cid, key):
        return self.items.get(key, 0)

    def add_item(self, _cid, key, quantity=1):
        self.items[key] = self.items.get(key, 0) + quantity


class FakeSession:
    def __init__(self, level=30, room=salt.UNDERTIDE_RELEASE_KEY):
        self.character = SimpleNamespace(
            id=1230,
            name="WhitewakeTester",
            race="goblin",
            character_class="priest",
            deity_key=None,
            level=level,
            current_room=room,
        )
        self.database = FakeDB(self.character)
        self.messages = []

    async def send(self, text):
        self.messages.append(text)


class SaltKingdomsProgressionTests(unittest.TestCase):
    def test_undertide_twist_makes_regent_emergency_response_not_simple_villain(self):
        async def run():
            session = FakeSession(29, salt.UNDERTIDE_DISTRIBUTOR_KEY)
            session.database.quests[salt.UNDERTIDE_QUEST_KEY] = {
                "quest_key": salt.UNDERTIDE_QUEST_KEY,
                "status": "active",
                "current_step": "inspect_distributor",
            }
            handled = await salt._inspect_distributor(session)
            self.assertTrue(handled)
            self.assertIn(salt.REGENT_TRUTH_FLAG, session.database.flags)
            self.assertEqual(session.database.quests[salt.UNDERTIDE_QUEST_KEY]["current_step"], "listen_water")
            text = "".join(session.messages)
            self.assertIn("emergency response", text)
            self.assertIn("keep one broken hub from rupturing everything", text)

        asyncio.run(run())

    def test_level_thirty_choice_is_persistent_and_awards_real_keepsake(self):
        async def run():
            for ending, flag in (
                ("harbor", salt.HARBOR_ENDING_FLAG),
                ("wells", salt.WELLS_ENDING_FLAG),
                ("current", salt.CURRENT_ENDING_FLAG),
            ):
                session = FakeSession(30, salt.UNDERTIDE_RELEASE_KEY)
                session.database.flags.add(salt.UNDERTIDE_COMPLETE_FLAG)
                session.database.quests[salt.CAPSTONE_QUEST_KEY] = {
                    "quest_key": salt.CAPSTONE_QUEST_KEY,
                    "status": "active",
                    "current_step": "reach_release",
                }
                handled = await salt._choose_water(session, ending)
                self.assertTrue(handled)
                self.assertIn(flag, session.database.flags)
                self.assertIn(salt.CAPSTONE_COMPLETE_FLAG, session.database.flags)
                self.assertEqual(session.database.items.get(salt.WATER_DECISION_SEAL_KEY), 1)
                self.assertEqual(session.database.quests[salt.CAPSTONE_QUEST_KEY]["status"], "completed")
                self.assertIn("map has permanently changed", "".join(session.messages))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
