import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.combat as combat
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.room_engine import PlayerRoomContext, WorldService
from mud.stats import CharacterStats
from mud import troll_raid_opening as raid
from mud import troll_start
from mud.troll_survivor_choice import (
    TROLL_ASHEN_SHELTER_ROW_KEY,
    TROLL_BREACH_YARD_KEY,
    TROLL_CAMP_CHOICE_FLAG,
    TROLL_CAMP_ROUTE_COMPLETE_FLAG,
    TROLL_CHURNED_GULLY_KEY,
    TROLL_EMBERS_BANKED_FLAG,
    TROLL_FIRST_DUTY_COMPLETE_FLAG,
    TROLL_FIRST_DUTY_GRANDFATHERED_FLAG,
    TROLL_FIRST_DUTY_QUEST,
    TROLL_FIRST_DUTY_ROOM_KEYS,
    TROLL_FOOD_SAVED_FLAG,
    TROLL_RAIDER_CLUE_FLAG,
    TROLL_REARGUARD_DEFEATED_FLAG,
    TROLL_RETREAT_FOLLOWED_FLAG,
    TROLL_RETREAT_TRACKS_READ_FLAG,
    TROLL_SHELTER_PATCHED_FLAG,
    TROLL_SMOLDERING_TRAIL_KEY,
    TROLL_TRACK_CHOICE_FLAG,
    TROLL_TRACK_ROUTE_COMPLETE_FLAG,
    _choose_first_duty,
    _ensure_first_duty,
    _handle_camp_route,
    _handle_track_route,
    _record_rearguard_defeat,
    _talk_raska_first_duty,
    first_duty_room_augmentations,
    install_troll_survivor_choice_content,
)


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)

    def move_to(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed


class TrollSurvivorChoiceTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.enemy_tuple = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)

        troll_start.install_troll_content()
        install_troll_survivor_choice_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        combat.ENEMIES = self.enemy_tuple
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)

    def _session(self, name: str):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "troll_first_duty.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            "troll",
            "brute",
            CharacterStats(might=9, grace=5, love=5, mind=5, hp=12),
        )
        database.set_character_room(character.id, troll_start.TROLL_START_ROOM_KEY)
        database.set_bind_room(character.id, troll_start.TROLL_START_ROOM_KEY)
        character = database.get_character_by_name(name)
        assert character is not None

        # The new branch begins only after the desperate raid opening is complete.
        database.start_quest(character.id, raid.TROLL_RAID_QUEST.key, "complete")
        database.complete_quest(character.id, raid.TROLL_RAID_QUEST.key)
        database.grant_flag(character.id, raid.TROLL_RAID_COMPLETE_FLAG)
        database.start_quest(character.id, troll_start.TROLL_COLD_QUEST.key, "speak_raska")
        return temp, database, LiveLikeSession(database, character)

    def test_track_raiders_route_is_combat_heavy_then_reconverges_on_raska(self):
        temp, database, session = self._session("Trailwatch")
        self.addCleanup(temp.cleanup)

        duty = _ensure_first_duty(session)
        self.assertEqual(duty["current_step"], "choose_duty")
        self.assertTrue(asyncio.run(_choose_first_duty(session, "track raiders")))
        self.assertIn(TROLL_TRACK_CHOICE_FLAG, database.list_flags(session.character.id))

        session.move_to(TROLL_SMOLDERING_TRAIL_KEY)
        self.assertTrue(asyncio.run(_handle_track_route(session, "read tracks")))
        self.assertIn(TROLL_RETREAT_TRACKS_READ_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(_handle_track_route(session, "follow raiders")))
        self.assertIn(TROLL_RETREAT_FOLLOWED_FLAG, database.list_flags(session.character.id))

        session.move_to(TROLL_CHURNED_GULLY_KEY)
        _record_rearguard_defeat(session)
        self.assertIn(TROLL_REARGUARD_DEFEATED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(_handle_track_route(session, "search rearguard")))
        self.assertIn(TROLL_RAIDER_CLUE_FLAG, database.list_flags(session.character.id))

        session.move_to(troll_start.TROLL_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_talk_raska_first_duty(session)))
        finished = database.get_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key)
        self.assertEqual(finished["status"], "completed")
        flags = database.list_flags(session.character.id)
        self.assertIn(TROLL_FIRST_DUTY_COMPLETE_FLAG, flags)
        self.assertIn(TROLL_TRACK_ROUTE_COMPLETE_FLAG, flags)
        self.assertNotIn(TROLL_CAMP_ROUTE_COMPLETE_FLAG, flags)
        self.assertEqual(
            database.get_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key)["current_step"],
            "speak_raska",
        )
        combined = "".join(session.outputs).lower()
        self.assertIn("tracking is not revenge", combined)
        self.assertIn("facts", combined)

    def test_secure_camp_route_saves_food_shelter_and_heat_then_reconverges(self):
        temp, database, session = self._session("Hearthhand")
        self.addCleanup(temp.cleanup)

        _ensure_first_duty(session)
        self.assertTrue(asyncio.run(_choose_first_duty(session, "secure camp")))
        self.assertIn(TROLL_CAMP_CHOICE_FLAG, database.list_flags(session.character.id))

        session.move_to(TROLL_ASHEN_SHELTER_ROW_KEY)
        self.assertTrue(asyncio.run(_handle_camp_route(session, "check shelters")))
        self.assertTrue(asyncio.run(_handle_camp_route(session, "salvage food")))
        self.assertTrue(asyncio.run(_handle_camp_route(session, "patch shelter")))
        self.assertTrue(asyncio.run(_handle_camp_route(session, "bank embers")))

        flags = database.list_flags(session.character.id)
        self.assertIn(TROLL_FOOD_SAVED_FLAG, flags)
        self.assertIn(TROLL_SHELTER_PATCHED_FLAG, flags)
        self.assertIn(TROLL_EMBERS_BANKED_FLAG, flags)

        session.move_to(troll_start.TROLL_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_talk_raska_first_duty(session)))
        finished = database.get_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key)
        self.assertEqual(finished["status"], "completed")
        flags = database.list_flags(session.character.id)
        self.assertIn(TROLL_FIRST_DUTY_COMPLETE_FLAG, flags)
        self.assertIn(TROLL_CAMP_ROUTE_COMPLETE_FLAG, flags)
        self.assertNotIn(TROLL_TRACK_ROUTE_COMPLETE_FLAG, flags)
        combined = "".join(session.outputs).lower()
        self.assertIn("three hours from now", combined)
        self.assertIn("different work. same rule", combined)

    def test_choice_routes_are_small_mutually_exclusive_world_branches(self):
        self.assertEqual(len(TROLL_FIRST_DUTY_ROOM_KEYS), 4)
        for room_key in TROLL_FIRST_DUTY_ROOM_KEYS:
            self.assertIn(room_key, world.ROOMS_BY_KEY)
            self.assertEqual(world.ROOMS_BY_KEY[room_key].region_key, troll_start.TROLL_REGION_KEY)

        service = WorldService(
            rooms=world.ROOMS_BY_KEY,
            augmentations=first_duty_room_augmentations(),
        )
        track_context = PlayerRoomContext(
            character_id=1,
            race_key="troll",
            class_key="brute",
            level=1,
            character_flags=frozenset({TROLL_TRACK_CHOICE_FLAG}),
        )
        camp_context = PlayerRoomContext(
            character_id=2,
            race_key="troll",
            class_key="druid",
            level=1,
            character_flags=frozenset({TROLL_CAMP_CHOICE_FLAG}),
        )
        self.assertTrue(service.resolve_exit(TROLL_BREACH_YARD_KEY, "south", track_context).allowed)
        self.assertFalse(service.resolve_exit(TROLL_BREACH_YARD_KEY, "west", track_context).allowed)
        self.assertFalse(service.resolve_exit(TROLL_BREACH_YARD_KEY, "south", camp_context).allowed)
        self.assertTrue(service.resolve_exit(TROLL_BREACH_YARD_KEY, "west", camp_context).allowed)

        blocked_gully = service.resolve_exit(TROLL_SMOLDERING_TRAIL_KEY, "south", track_context)
        self.assertFalse(blocked_gully.allowed)
        followed_context = PlayerRoomContext(
            character_id=1,
            race_key="troll",
            class_key="brute",
            level=1,
            character_flags=frozenset({TROLL_TRACK_CHOICE_FLAG, TROLL_RETREAT_FOLLOWED_FLAG}),
        )
        self.assertTrue(service.resolve_exit(TROLL_SMOLDERING_TRAIL_KEY, "south", followed_context).allowed)

    def test_troll_already_past_first_cold_step_is_grandfathered(self):
        temp, database, session = self._session("OldPath")
        self.addCleanup(temp.cleanup)
        database.advance_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key, "read_wind")

        duty = _ensure_first_duty(session)
        self.assertEqual(duty["status"], "completed")
        flags = database.list_flags(session.character.id)
        self.assertIn(TROLL_FIRST_DUTY_COMPLETE_FLAG, flags)
        self.assertIn(TROLL_FIRST_DUTY_GRANDFATHERED_FLAG, flags)


if __name__ == "__main__":
    unittest.main()
