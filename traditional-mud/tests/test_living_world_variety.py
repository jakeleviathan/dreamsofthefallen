from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import mud.actor_inspection as actor_inspection
import mud.living_world as living
from mud.astralis_time import AstralisMoment
from mud.database import Database


def _moment(day: int) -> AstralisMoment:
    return AstralisMoment(day_number=day, hour=12, minute=0, total_minutes=((day - 1) * 1440) + 720)


class _World:
    def scene(self, _room_key):
        return SimpleNamespace(npc_keys=(), enemy_keys=())


class _Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.mobile_npcs = None
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class LivingWorldVarietyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        import mud.living_world_variety as variety
        cls.variety = variety

    def test_catalog_is_huge_and_regionally_distributed(self):
        v = self.variety
        self.assertEqual(v.LIVING_WORLD_VARIETY_VERSION, "2.0.0")
        self.assertGreaterEqual(len(v.GENERATED_PULSES), 200)
        self.assertEqual(len({pulse.key for pulse in v.ALL_PULSES}), len(v.ALL_PULSES))
        self.assertEqual({pulse.kind for pulse in v.GENERATED_PULSES}, {"merchant", "resource", "threat", "story"})
        for region in v.REGIONS:
            count = sum(1 for pulse in v.GENERATED_PULSES if v.EVENT_META_BY_KEY[pulse.key].region_key == region.region_key)
            self.assertGreaterEqual(count, 25, region.region_key)

    def test_day_selection_is_stable_and_reaches_far_more_than_twelve_events(self):
        v = self.variety
        first = [v.pulse_for_day(day) for day in range(1, 1001)]
        second = [v.pulse_for_day(day) for day in range(1, 1001)]
        self.assertEqual(first, second)
        self.assertGreaterEqual(len({pulse.key for pulse in first}), 150)
        self.assertEqual({pulse.kind for pulse in first}, {"merchant", "resource", "threat", "story"})
        self.assertEqual(v.pulse_for_day(1).key, "copperwake_caravan")
        self.assertEqual(v.pulse_for_day(3).key, "briar_bloom")

    def test_every_generated_event_points_to_real_world_system_data(self):
        v = self.variety
        import mud.combat as combat
        import mud.crafting as crafting
        from mud.world import ROOMS_BY_KEY
        for pulse in v.GENERATED_PULSES:
            self.assertIn(pulse.room_key, ROOMS_BY_KEY, pulse.key)
            if pulse.kind == "resource":
                self.assertIn(pulse.resource_node, crafting.RESOURCE_NODES_BY_KEY, pulse.key)
            elif pulse.kind == "threat":
                self.assertIn(pulse.threat_key, combat.ENEMIES_BY_KEY, pulse.key)

    def test_return_mail_has_many_voices_and_still_points_to_real_event(self):
        v = self.variety
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "mail.db")
            account = database.create_account("variety_mail", "x")
            character = database.create_character(account.id, "Postreader", "goblin", "priest")
            session = _Session(database, character)
            living.ensure_living_world_schema(database)
            for day in range(20, 80):
                self.assertTrue(v.create_return_letter(session, day - 1, day))
            with database.connect() as db:
                rows = db.execute("SELECT sender, subject, body FROM living_mail WHERE character_id = ? ORDER BY astralis_day", (character.id,)).fetchall()
            self.assertEqual(len(rows), 60)
            self.assertGreaterEqual(len({str(row["sender"]) for row in rows}), 5)
            self.assertGreaterEqual(len({str(row["subject"]) for row in rows}), 40)
            self.assertGreaterEqual(len({str(row["body"]) for row in rows}), 45)
            self.assertLess(sum("Nothing in this letter" in str(row["body"]) for row in rows), len(rows) // 3)
            self.assertTrue(all("go to " in str(row["body"]) and " use " in str(row["body"]) for row in rows))

    def test_story_event_is_a_real_room_local_interaction(self):
        v = self.variety
        day = next(day for day in range(13, 500) if v.pulse_for_day(day).kind == "story" and v.pulse_for_day(day).key.startswith("variety:"))
        pulse = v.pulse_for_day(day)
        meta = v.EVENT_META_BY_KEY[pulse.key]
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "scene.db")
            account = database.create_account("variety_scene", "x")
            character = database.create_character(account.id, "Watcher", "human", "brute")
            database.set_character_room(character.id, pulse.room_key)
            character = database.get_character_by_name("Watcher")
            session = _Session(database, character)
            asyncio.run(v._observe_story(session, pulse, meta, day))
            self.assertTrue(living._event_done(session, day, pulse.key))
            self.assertIn("actually happening here today", "".join(session.messages))

    def test_generated_merchant_is_visible_as_temporary_actor(self):
        v = self.variety
        day = next(day for day in range(13, 500) if v.pulse_for_day(day).kind == "merchant" and v.pulse_for_day(day).key.startswith("variety:"))
        pulse = v.pulse_for_day(day)
        meta = v.EVENT_META_BY_KEY[pulse.key]
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "merchant.db")
            account = database.create_account("variety_actor", "x")
            character = database.create_character(account.id, "Buyer", "human", "brute")
            database.set_character_room(character.id, pulse.room_key)
            character = database.get_character_by_name("Buyer")
            session = _Session(database, character)
            class _Clock:
                def now(self, real_seconds=None):
                    return _moment(day)
            with patch.object(living, "ASTRALIS_CLOCK", _Clock()):
                actors = actor_inspection.visible_actors(session, _World())
            self.assertIn(meta.actor_name, {actor.name for actor in actors})

    def test_old_return_mail_contract_still_passes_without_forcing_same_sentence_every_day(self):
        v = self.variety
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "compat.db")
            account = database.create_account("compat_mail", "x")
            character = database.create_character(account.id, "Returner", "human", "brute")
            session = _Session(database, character)
            living.ensure_living_world_schema(database)
            self.assertTrue(v.create_return_letter(session, 10, 13))
            with database.connect() as db:
                row = db.execute("SELECT subject, body FROM living_mail WHERE character_id = ?", (character.id,)).fetchone()
            self.assertIn("away for 3 Astralis days", row["body"])
            self.assertIn("missed reward", row["body"].lower())
            self.assertIn("nothing in this letter", row["body"].lower())
            self.assertIn("Day 13", row["subject"])

    def test_production_server_applies_variety(self):
        self.assertTrue(self.server.PlayerSession._living_world_variety_runtime_applied)


if __name__ == "__main__":
    unittest.main()
