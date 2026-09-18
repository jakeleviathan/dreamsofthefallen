from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LivingWorldVarietyTests(unittest.TestCase):
    def test_production_catalog_mail_and_interactions_are_large_real_and_varied(self):
        # Importing the real production entrypoint mutates the intentionally shared
        # world registries. Run this contract in its own process so those production
        # mutations cannot leak into later unit tests that assemble smaller slices.
        code = r'''
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import server
import mud.actor_inspection as actor_inspection
import mud.combat as combat
import mud.crafting as crafting
import mud.living_world as living
import mud.living_world_variety as variety
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.world import ROOMS_BY_KEY

assert server.PlayerSession._living_world_variety_runtime_applied
assert variety.LIVING_WORLD_VARIETY_VERSION == "2.1.0"
assert len(variety.GENERATED_PULSES) >= 200
assert len(variety.ALL_PULSES) >= 220
assert len({pulse.key for pulse in variety.ALL_PULSES}) == len(variety.ALL_PULSES)
assert {pulse.kind for pulse in variety.GENERATED_PULSES} == {"merchant", "resource", "threat", "story"}

for region in variety.REGIONS:
    count = sum(
        1
        for pulse in variety.GENERATED_PULSES
        if variety.EVENT_META_BY_KEY[pulse.key].region_key == region.region_key
    )
    assert count >= 25, (region.region_key, count)

first = [variety.pulse_for_day(day) for day in range(1, 1001)]
second = [variety.pulse_for_day(day) for day in range(1, 1001)]
assert first == second
assert len({pulse.key for pulse in first}) >= 150
assert {pulse.kind for pulse in first} == {"merchant", "resource", "threat", "story"}
assert variety.pulse_for_day(1).key == "copperwake_caravan"
assert variety.pulse_for_day(3).key == "briar_bloom"

for pulse in variety.GENERATED_PULSES:
    assert pulse.room_key in ROOMS_BY_KEY, pulse.key
    if pulse.kind == "resource":
        assert pulse.resource_node in crafting.RESOURCE_NODES_BY_KEY, pulse.key
    elif pulse.kind == "threat":
        assert pulse.threat_key in combat.ENEMIES_BY_KEY, pulse.key

class Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.mobile_npcs = None
        self.messages = []

    async def send(self, text):
        self.messages.append(text)

class EmptyWorld:
    def scene(self, _room_key):
        return SimpleNamespace(npc_keys=(), enemy_keys=())

with tempfile.TemporaryDirectory() as temp_dir:
    database = Database(Path(temp_dir) / "mail.db")
    account = database.create_account("variety_mail", "x")
    character = database.create_character(account.id, "Postreader", "goblin", "priest")
    session = Session(database, character)
    living.ensure_living_world_schema(database)

    for day in range(20, 80):
        assert variety.create_return_letter(session, day - 1, day)

    with database.connect() as db:
        rows = db.execute(
            "SELECT sender, subject, body FROM living_mail WHERE character_id = ? ORDER BY astralis_day",
            (character.id,),
        ).fetchall()

    assert len(rows) == 60
    assert len({str(row["sender"]) for row in rows}) >= 5
    assert len({str(row["subject"]) for row in rows}) >= 40
    assert len({str(row["body"]) for row in rows}) >= 45
    forbidden_mail_phrases = (
        "missed reward",
        "nothing in this letter",
        "penalty for being away",
        "actually present",
        "current astralis day",
        "demand completion",
        "not an assignment",
        "keeping attendance",
        "punish you",
        "no deadline",
        "formal quest",
        "quest marker",
        "genuinely gatherable",
        "normal gathering system",
        "decorative text",
        "real temporary disturbance",
        "normal combat",
    )
    assert all(
        not any(phrase in str(row["body"]).lower() for phrase in forbidden_mail_phrases)
        for row in rows
    )
    assert all("stop at " in str(row["body"]) for row in rows)

with tempfile.TemporaryDirectory() as temp_dir:
    database = Database(Path(temp_dir) / "compat.db")
    account = database.create_account("compat_mail", "x")
    character = database.create_character(account.id, "Returner", "human", "brute")
    session = Session(database, character)
    living.ensure_living_world_schema(database)
    assert variety.create_return_letter(session, 10, 13)
    with database.connect() as db:
        row = db.execute(
            "SELECT subject, body FROM living_mail WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    assert "3 Astralis days" in row["body"]
    assert "away" in row["body"].lower()
    assert "missed reward" not in row["body"].lower()
    assert "nothing in this letter" not in row["body"].lower()
    assert "penalty" not in row["body"].lower()
    assert "Day 13" in row["subject"]

story_day = next(
    day
    for day in range(13, 500)
    if variety.pulse_for_day(day).kind == "story"
    and variety.pulse_for_day(day).key.startswith("variety:")
)
story = variety.pulse_for_day(story_day)
meta = variety.EVENT_META_BY_KEY[story.key]
with tempfile.TemporaryDirectory() as temp_dir:
    database = Database(Path(temp_dir) / "scene.db")
    account = database.create_account("variety_scene", "x")
    character = database.create_character(account.id, "Watcher", "human", "brute")
    database.set_character_room(character.id, story.room_key)
    character = database.get_character_by_name("Watcher")
    session = Session(database, character)
    living.ensure_living_world_schema(database)
    asyncio.run(variety._observe_story(session, story, meta, story_day))
    assert living._event_done(session, story_day, story.key)
    observed = "".join(session.messages).lower()
    assert "conversation keeps moving" in observed
    assert "payout" not in observed
    assert "actually happening here today" not in observed

merchant_day = next(
    day
    for day in range(13, 500)
    if variety.pulse_for_day(day).kind == "merchant"
    and variety.pulse_for_day(day).key.startswith("variety:")
)
merchant = variety.pulse_for_day(merchant_day)
merchant_meta = variety.EVENT_META_BY_KEY[merchant.key]
with tempfile.TemporaryDirectory() as temp_dir:
    database = Database(Path(temp_dir) / "merchant.db")
    account = database.create_account("variety_actor", "x")
    character = database.create_character(account.id, "Buyer", "human", "brute")
    database.set_character_room(character.id, merchant.room_key)
    character = database.get_character_by_name("Buyer")
    session = Session(database, character)

    class Clock:
        def now(self, real_seconds=None):
            return AstralisMoment(
                day_number=merchant_day,
                hour=12,
                minute=0,
                total_minutes=((merchant_day - 1) * 1440) + 720,
            )

    with patch.object(living, "ASTRALIS_CLOCK", Clock()):
        actors = actor_inspection.visible_actors(session, EmptyWorld())
    assert merchant_meta.actor_name in {actor.name for actor in actors}

print("LIVING_WORLD_VARIETY_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("LIVING_WORLD_VARIETY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
