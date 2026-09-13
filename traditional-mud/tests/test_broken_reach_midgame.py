import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.broken_reach_midgame as reach


class BrokenReachDesignTests(unittest.TestCase):
    def test_region_has_real_breadth_dungeon_and_optional_oddities(self):
        self.assertEqual(len(reach.SURFACE_ROOM_KEYS), 14)
        self.assertEqual(len(reach.HOUSE_ROOM_KEYS), 14)
        self.assertEqual(len(reach.BROKEN_REACH_ROOMS), 28)
        self.assertEqual(len(reach.BROKEN_REACH_QUESTS), 4)
        self.assertEqual(len(reach.ODDITY_FLAGS), 4)
        self.assertIn(reach.SLEEPING_TOLLHOUSE_KEY, reach.SURFACE_ROOM_KEYS)
        self.assertIn(reach.WITCHPOST_MEADOW_KEY, reach.SURFACE_ROOM_KEYS)
        self.assertIn(reach.CROW_COURT_KEY, reach.SURFACE_ROOM_KEYS)
        self.assertIn(reach.HOUSE_NINE_BOOTS_KEY, reach.HOUSE_ROOM_KEYS)
        self.assertIn(reach.HILL_WARDEN_KEY, {enemy.key for enemy in reach.BROKEN_REACH_ENEMIES})
        self.assertIn(reach.NAMELESS_GUEST_KEY, {enemy.key for enemy in reach.BROKEN_REACH_ENEMIES})

    def test_story_band_matches_11_to_20_plan(self):
        self.assertEqual(reach.FIRST_QUEST.minimum_level, 11)
        self.assertEqual(reach.FACTION_QUEST.minimum_level, 14)
        self.assertEqual(reach.HOUSE_QUEST.minimum_level, 17)
        self.assertEqual(reach.CAPSTONE_QUEST.minimum_level, 20)
        self.assertIn("Grinning Men", reach.FIRST_QUEST.description)
        self.assertIn("three groups", reach.FACTION_QUEST.description)
        self.assertIn("older structure", reach.HOUSE_QUEST.description)
        self.assertIn("buried road", reach.CAPSTONE_QUEST.description)

    def test_actual_production_entrypoint_installs_region_and_map_change(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.broken_reach_midgame import (
    BROKEN_REACH_ROOM_KEYS,
    OLD_TOLL_ROAD_KEY,
    SPLIT_LANTERN_BRIDGE_KEY,
    FAR_WATCH_KEY,
    HOUSE_KEEPER_LOCK_KEY,
    HOUSE_UNDERHOUSE_SHAFT_KEY,
    HOUSE_BURIED_ROAD_KEY,
    HOUSE_WAKE_GATE_KEY,
    WARDEN_DEFEATED_FLAG,
    REACH_CHANGED_FLAG,
    CAPSTONE_COMPLETE_FLAG,
)
from mud.room_engine import PlayerRoomContext
from mud.waymeet_adventure_arc import OLD_TOLL_ROAD as WAYMEET_OLD_TOLL_ROAD
from mud.waymeet_frontier import WAYMEET_BROKEN_MILE_KEY
from mud.veyra_city import VEYRA_SOUTH_SPRAWL_KEY
from mud.world import ROOMS_BY_KEY

assert server.PlayerSession._broken_reach_midgame_installed
for key in BROKEN_REACH_ROOM_KEYS:
    assert key in ROOMS_BY_KEY, key
    assert key in server.WORLD.legacy_rooms, key

low = PlayerRoomContext(1, "goblin", "priest", 9, frozenset())
level11 = PlayerRoomContext(1, "goblin", "priest", 11, frozenset())
# Broken Reach must not steal the existing level-2 south route from the Broken Mile.
early_road = server.WORLD.resolve_exit(WAYMEET_BROKEN_MILE_KEY, "south", level11)
assert early_road.allowed and early_road.exit.destination_key == WAYMEET_OLD_TOLL_ROAD
# It continues beyond that familiar early-game road only once the midgame gate is reached.
assert "south" not in {item.direction for item in server.WORLD.build_view(WAYMEET_OLD_TOLL_ROAD, low).exits}
entry = server.WORLD.resolve_exit(WAYMEET_OLD_TOLL_ROAD, "south", level11)
assert entry.allowed and entry.exit.destination_key == OLD_TOLL_ROAD_KEY
# Veyra's SOUTH exit still belongs to Sablewater; Broken Reach returns from the west.
veyra_back = server.WORLD.resolve_exit(VEYRA_SOUTH_SPRAWL_KEY, "west", level11)
assert veyra_back.allowed and veyra_back.exit.destination_key == FAR_WATCH_KEY

before = PlayerRoomContext(1, "goblin", "priest", 19, frozenset())
locked = server.WORLD.build_view(HOUSE_KEEPER_LOCK_KEY, before)
assert "down" not in {item.direction for item in locked.exits}
after_warden = PlayerRoomContext(1, "goblin", "priest", 19, frozenset({WARDEN_DEFEATED_FLAG}))
unlocked = server.WORLD.resolve_exit(HOUSE_KEEPER_LOCK_KEY, "down", after_warden)
assert unlocked.allowed and unlocked.exit.destination_key == HOUSE_UNDERHOUSE_SHAFT_KEY

pre_event = server.WORLD.build_view(SPLIT_LANTERN_BRIDGE_KEY, PlayerRoomContext(1, "goblin", "priest", 20, frozenset()))
pre_dirs = {item.direction: item.destination_key for item in pre_event.exits}
assert pre_dirs["south"] == FAR_WATCH_KEY
assert "down" not in pre_dirs

post_flags = frozenset({REACH_CHANGED_FLAG, CAPSTONE_COMPLETE_FLAG})
post = server.WORLD.build_view(SPLIT_LANTERN_BRIDGE_KEY, PlayerRoomContext(1, "goblin", "priest", 20, post_flags))
post_dirs = {item.direction: item.destination_key for item in post.exits}
assert "south" not in post_dirs
assert post_dirs["down"] == HOUSE_BURIED_ROAD_KEY
far = server.WORLD.build_view(FAR_WATCH_KEY, PlayerRoomContext(1, "goblin", "priest", 20, post_flags))
far_dirs = {item.direction: item.destination_key for item in far.exits}
assert "north" not in far_dirs
assert far_dirs["down"] == HOUSE_WAKE_GATE_KEY
print("BROKEN_REACH_PRODUCTION_OK")
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
        self.assertIn("BROKEN_REACH_PRODUCTION_OK", result.stdout)


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
    def __init__(self, level=11):
        self.character = SimpleNamespace(
            id=911,
            name="ReachTester",
            race="goblin",
            character_class="priest",
            deity_key=None,
            level=level,
            current_room=reach.OLD_TOLL_ROAD_KEY,
        )
        self.database = FakeDB(self.character)
        self.messages = []

    async def send(self, text):
        self.messages.append(text)


class BrokenReachProgressionTests(unittest.TestCase):
    def test_level_11_story_proves_grinning_men_are_not_simple_villains(self):
        async def run():
            session = FakeSession(11)
            message = reach._ensure_story(session)
            self.assertIn("No Smiling Matter", message)

            session.character.current_room = reach.CARAVANSERAI_KEY
            self.assertTrue(await reach._talk_hesta(session))
            session.character.current_room = reach.LEANING_ORCHARD_KEY
            self.assertTrue(await reach._inspect_wagon(session))
            session.character.current_room = reach.GRINNING_CAMP_KEY
            self.assertTrue(await reach._talk_jory(session))
            session.character.current_room = reach.SPLIT_LANTERN_BRIDGE_KEY
            self.assertTrue(await reach._inspect_lanterns(session))
            session.character.current_room = reach.CARAVANSERAI_KEY
            self.assertTrue(await reach._talk_hesta(session))

            self.assertIn(reach.FIRST_COMPLETE_FLAG, session.database.flags)
            self.assertEqual(session.database.items.get(reach.SURVEY_RIBBON_KEY), 1)
            text = "".join(session.messages)
            self.assertIn("not guilty of making wagons walk toward a hill", text)
            self.assertIn("warning mark, not claim mark", text)

        asyncio.run(run())

    def test_level_20_capstone_replaces_surface_route_with_underroad(self):
        async def run():
            session = FakeSession(20)
            session.database.flags.update({
                reach.FIRST_COMPLETE_FLAG,
                reach.FACTION_COMPLETE_FLAG,
                reach.HOUSE_COMPLETE_FLAG,
            })
            session.character.current_room = reach.CARAVANSERAI_KEY
            message = reach._ensure_story(session)
            self.assertIn("Night the Hill Opened", message)

            self.assertTrue(await reach._talk_hesta(session))
            session.character.current_room = reach.HOUSE_CONTAINMENT_RING_KEY
            self.assertTrue(await reach._set_anchors(session))
            session.character.current_room = reach.SPLIT_LANTERN_BRIDGE_KEY
            self.assertTrue(await reach._drop_span(session))
            self.assertIn(reach.REACH_CHANGED_FLAG, session.database.flags)
            session.character.current_room = reach.HOUSE_WAKE_GATE_KEY
            self.assertTrue(await reach._open_bypass(session))

            self.assertIn(reach.CAPSTONE_COMPLETE_FLAG, session.database.flags)
            self.assertEqual(session.database.items.get(reach.UNDERROAD_WRIT_KEY), 1)
            self.assertEqual(session.database.quests[reach.CAPSTONE_QUEST_KEY]["status"], "completed")
            self.assertIn("map has permanently changed", "".join(session.messages))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()