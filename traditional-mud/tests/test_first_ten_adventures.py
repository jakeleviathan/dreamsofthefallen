import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.first_ten_adventures import (
    ADVENTURE_ROUTES,
    HERITAGE_REWARDS,
    ORIGIN_CONTACTS,
)
from mud.first_ten_progression import RACE_FIRST_TEN_ARCS
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE
from mud.waymeet_frontier import WAYMEET_CROSSROADS_KEY


class FirstTenAdventureDesignTests(unittest.TestCase):
    def test_every_race_has_three_five_step_routed_adventures(self):
        self.assertEqual(set(ORIGIN_CONTACTS), set(RACE_FIRST_TEN_ARCS))
        self.assertEqual(len(ADVENTURE_ROUTES), 24)
        for race_key, arc in RACE_FIRST_TEN_ARCS.items():
            start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
            for beat in arc.beats:
                with self.subTest(race=race_key, beat=beat.key):
                    route = ADVENTURE_ROUTES[(race_key, beat.key)]
                    self.assertEqual(len(route.steps), 5)
                    self.assertEqual(route.steps[0].room_key, start)
                    self.assertEqual(route.steps[-1].room_key, start)
                    self.assertGreaterEqual(len({step.room_key for step in route.steps}), 2)
                    self.assertEqual(sum(1 for step in route.steps if step.twist), 1)
                    self.assertTrue(all(step.command.strip() for step in route.steps))
                    self.assertTrue(all(step.objective.strip() for step in route.steps))

    def test_level_eight_story_for_every_race_physically_crosses_waymeet(self):
        for race_key, arc in RACE_FIRST_TEN_ARCS.items():
            with self.subTest(race=race_key):
                route = ADVENTURE_ROUTES[(race_key, arc.act_three.key)]
                self.assertIn(WAYMEET_CROSSROADS_KEY, {step.room_key for step in route.steps})
                self.assertTrue(any(step.shared_world for step in route.steps))
                self.assertEqual(route.steps[0].room_key, STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key)
                self.assertEqual(route.steps[-1].room_key, STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key)

    def test_every_origin_has_a_unique_persistent_capstone_keepsake(self):
        reward_keys = {item.key for item in HERITAGE_REWARDS}
        self.assertEqual(len(reward_keys), 8)
        self.assertEqual(reward_keys, {contact.reward_key for contact in ORIGIN_CONTACTS.values()})
        for race_key, arc in RACE_FIRST_TEN_ARCS.items():
            with self.subTest(race=race_key):
                route = ADVENTURE_ROUTES[(race_key, arc.capstone.key)]
                self.assertEqual(route.reward_key, ORIGIN_CONTACTS[race_key].reward_key)

    def test_production_assembles_contacts_routes_quest_journals_and_rewards(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.first_ten_adventures import (
    ADVENTURE_ROUTES,
    ORIGIN_CONTACTS,
    validate_first_ten_adventure_contract,
)
from mud.first_ten_progression import RACE_FIRST_TEN_ARCS
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE

assert server.PlayerSession._first_ten_adventures_installed
validate_first_ten_adventure_contract(server.WORLD)
for race_key, contact in ORIGIN_CONTACTS.items():
    start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
    assert contact.key in world.NPCS_BY_KEY, race_key
    assert contact.key in world.ROOMS_BY_KEY[start].npc_keys, race_key
    assert contact.reward_key in crafting.ITEMS_BY_KEY, race_key
    for beat in RACE_FIRST_TEN_ARCS[race_key].beats:
        route = ADVENTURE_ROUTES[(race_key, beat.key)]
        quest = quests.QUESTS_BY_KEY[beat.quest_key(race_key)]
        assert len(route.steps) == 5, (race_key, beat.key)
        assert len(quest.objective_steps) == 6, (race_key, beat.key)
print("FIRST_TEN_ADVENTURES_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("FIRST_TEN_ADVENTURES_PRODUCTION_OK", result.stdout)

    def test_production_handler_walks_goblin_story_and_awards_capstone_item(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import asyncio
from types import SimpleNamespace

import server
import mud.first_ten_progression as first_ten
from mud.first_ten_adventures import ADVENTURE_ROUTES, ORIGIN_CONTACTS
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE

class FakeDB:
    def __init__(self, character):
        self.character = character
        self.flags = {STARTER_RACE_LOOPS_BY_RACE["goblin"].completion_flag}
        self.quests = {}
        self.items = {}
        self.xp = []
    def list_flags(self, _cid): return frozenset(self.flags)
    def grant_flag(self, _cid, flag): self.flags.add(flag)
    def get_quest(self, _cid, key):
        row = self.quests.get(key)
        return None if row is None else dict(row)
    def start_quest(self, _cid, key, step):
        self.quests.setdefault(key, {"quest_key": key, "status": "active", "current_step": step})
    def advance_quest(self, _cid, key, step): self.quests[key]["current_step"] = step
    def complete_quest(self, _cid, key):
        self.quests[key]["status"] = "completed"
        self.quests[key]["current_step"] = "complete"
    def add_experience(self, _cid, amount):
        self.xp.append(amount)
        return self.character.level
    def get_character_by_name(self, _name): return self.character
    def item_quantity(self, _cid, key): return self.items.get(key, 0)
    def add_item(self, _cid, key, quantity=1): self.items[key] = self.items.get(key, 0) + quantity

class FakeSession:
    def __init__(self, level):
        self.character = SimpleNamespace(
            id=91, name="Rivet", race="goblin", character_class="brute",
            deity_key=None, level=level,
            current_room=STARTER_RACE_LOOPS_BY_RACE["goblin"].starting_room_key,
        )
        self.database = FakeDB(self.character)
        self.messages = []
    async def send(self, text): self.messages.append(text)

async def run_route(session, beat):
    route = ADVENTURE_ROUTES[("goblin", beat.key)]
    for step in route.steps:
        session.character.current_room = step.room_key
        handled = await first_ten._handle_arc_command(session, step.command)
        assert handled, (beat.key, step.key, step.command)
    return route

async def main():
    arc = first_ten.RACE_FIRST_TEN_ARCS["goblin"]

    level_four = FakeSession(4)
    await run_route(level_four, arc.act_two)
    assert arc.act_two.completion_flag("goblin") in level_four.database.flags
    assert level_four.database.xp == [arc.act_two.xp_reward]
    assert "Waymeet" not in " ".join(step.room_key for step in ADVENTURE_ROUTES[("goblin", arc.act_two.key)].steps)

    capstone = FakeSession(10)
    capstone.database.flags.add(arc.act_two.completion_flag("goblin"))
    capstone.database.flags.add(arc.act_three.completion_flag("goblin"))
    route = await run_route(capstone, arc.capstone)
    reward_key = ORIGIN_CONTACTS["goblin"].reward_key
    assert route.reward_key == reward_key
    assert capstone.database.items.get(reward_key) == 1
    assert arc.capstone.completion_flag("goblin") in capstone.database.flags
    text = "".join(capstone.messages)
    assert "Heap-Held Plate" in text
    assert "homeland now has a reason to remember you" in text

asyncio.run(main())
print("FIRST_TEN_ADVENTURE_PLAY_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("FIRST_TEN_ADVENTURE_PLAY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
