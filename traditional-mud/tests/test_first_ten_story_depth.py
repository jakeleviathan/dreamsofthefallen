import os
import subprocess
import sys
import unittest
from pathlib import Path

from mud.first_ten_progression import RACE_FIRST_TEN_ARCS
from mud.first_ten_story_depth import (
    PARTNER_LINES,
    RELATIONSHIP_LINES,
    STORY_PARTNERS,
    STORY_SCENES,
)


class FirstTenStoryDepthDesignTests(unittest.TestCase):
    def test_every_origin_has_a_second_named_character_and_relationship_arc(self):
        races = set(RACE_FIRST_TEN_ARCS)
        self.assertEqual(set(STORY_PARTNERS), races)
        self.assertEqual(set(RELATIONSHIP_LINES), races)
        self.assertEqual(set(PARTNER_LINES), races)
        for race_key in races:
            with self.subTest(race=race_key):
                self.assertEqual(len(RELATIONSHIP_LINES[race_key]), 4)
                self.assertEqual(len(PARTNER_LINES[race_key]), 4)
                self.assertTrue(STORY_PARTNERS[race_key].name)
                self.assertTrue(STORY_PARTNERS[race_key].talk_alias)

    def test_all_twenty_four_acts_have_setup_disagreement_decision_and_aftermath(self):
        self.assertEqual(len(STORY_SCENES), 24)
        for race_key, arc in RACE_FIRST_TEN_ARCS.items():
            for beat in arc.beats:
                with self.subTest(race=race_key, beat=beat.key):
                    scene = STORY_SCENES[(race_key, beat.key)]
                    self.assertTrue(scene.setup)
                    self.assertTrue(scene.disagreement)
                    self.assertTrue(scene.decision)
                    self.assertTrue(scene.aftermath)
                    self.assertTrue(scene.reveal_echo)
                    self.assertTrue(scene.decision_echo)
                    self.assertTrue(scene.aftermath_echo)

    def test_production_installs_story_partners_and_persistent_room_consequences(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.world as world
from mud.first_ten_progression import RACE_FIRST_TEN_ARCS
from mud.first_ten_story_depth import (
    STORY_PARTNERS,
    validate_first_ten_story_depth_contract,
)
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE

assert server.PlayerSession._first_ten_story_depth_installed
validate_first_ten_story_depth_contract(server.WORLD)
for race_key, partner in STORY_PARTNERS.items():
    start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
    assert partner.key in world.NPCS_BY_KEY, race_key
    assert partner.key in world.ROOMS_BY_KEY[start].npc_keys, race_key
    for beat in RACE_FIRST_TEN_ARCS[race_key].beats:
        layer_key = f"first_ten_{race_key}_{beat.key}_aftermath"
        assert any(
            layer.key == layer_key
            for augmentation in server.WORLD.augmentations.values()
            for layer in augmentation.description_layers
        ), (race_key, beat.key)
print("FIRST_TEN_STORY_DEPTH_PRODUCTION_OK")
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
        self.assertIn("FIRST_TEN_STORY_DEPTH_PRODUCTION_OK", result.stdout)

    def test_goblin_story_has_scenes_memory_and_visible_consequences(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import asyncio
from types import SimpleNamespace

import server
import mud.first_ten_progression as first_ten
from mud.first_ten_adventures import ADVENTURE_ROUTES
from mud.room_engine import PlayerRoomContext
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
    def __init__(self):
        self.character = SimpleNamespace(
            id=313, name="Rivet", race="goblin", character_class="brute",
            deity_key=None, level=4,
            current_room=STARTER_RACE_LOOPS_BY_RACE["goblin"].starting_room_key,
        )
        self.database = FakeDB(self.character)
        self.messages = []
    async def send(self, text): self.messages.append(text)

async def main():
    session = FakeSession()
    arc = first_ten.RACE_FIRST_TEN_ARCS["goblin"]
    beat = arc.act_two
    route = ADVENTURE_ROUTES[("goblin", beat.key)]

    handled = await first_ten._handle_arc_command(session, "talk pella")
    assert handled
    before = "".join(session.messages)
    assert "still think a good fix and a good system are the same thing" in before

    session.messages.clear()
    for step in route.steps:
        session.character.current_room = step.room_key
        handled = await first_ten._handle_arc_command(session, step.command)
        assert handled, (step.key, step.command)

    text = "".join(session.messages)
    assert "--- The Problem Arrives ---" in text
    assert "Nix" in text
    assert "--- The Story Turns ---" in text
    assert "--- What Your Decision Changes ---" in text
    assert "--- Afterward ---" in text
    assert beat.completion_flag("goblin") in session.database.flags
    assert "first_ten_scene_goblin_home_crisis_truth_seen" in session.database.flags
    assert "first_ten_scene_goblin_home_crisis_decision_made" in session.database.flags

    session.character.current_room = STARTER_RACE_LOOPS_BY_RACE["goblin"].starting_room_key
    session.messages.clear()
    handled = await first_ten._handle_arc_command(session, "talk pella")
    assert handled
    after = "".join(session.messages)
    assert "Held yesterday. Held today." in after
    assert after != before

    context = PlayerRoomContext(
        character_id=session.character.id,
        race_key="goblin",
        class_key="brute",
        level=4,
        character_flags=frozenset(session.database.flags),
    )
    view = server.WORLD.build_view(route.steps[1].room_key, context)
    assert view is not None
    assert "whole structure" in view.description or "whole span" in view.description
    assert "claim board" in view.description

asyncio.run(main())
print("FIRST_TEN_STORY_DEPTH_GOBLIN_OK")
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
        self.assertIn("FIRST_TEN_STORY_DEPTH_GOBLIN_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
