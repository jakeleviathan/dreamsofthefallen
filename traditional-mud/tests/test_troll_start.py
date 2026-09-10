import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.mechanics import CombatantState
from mud.room_engine import PlayerRoomContext, WorldService
from mud.stats import CharacterStats
from mud.troll_start import (
    BRANNIK_SLATEBOOT,
    MORA_ELKHAND,
    RASKA_GREYBARK,
    TROLL_ANIMAL_HANDLING_FLAG,
    TROLL_COLD_COMPLETE_FLAG,
    TROLL_COLD_QUEST,
    TROLL_EMBER_HOLLOW_KEY,
    TROLL_FIRE_LIT_FLAG,
    TROLL_HIDEWIND_RING_KEY,
    TROLL_OUTSIDER_COMPLETE_FLAG,
    TROLL_OUTSIDER_QUEST,
    TROLL_QUARRY_JUDGMENT_FLAG,
    TROLL_REGEN_LEARNED_FLAG,
    TROLL_START_ROOM_KEY,
    TROLL_STONEJAW_PASS_KEY,
    TROLL_SURVIVAL_ROOM_KEYS,
    TROLL_TETHER_YARD_KEY,
    TROLL_TRACK_COMPLETE_FLAG,
    TROLL_TRACK_QUEST,
    TROLL_TRACKLINE_VERGE_KEY,
    TROLL_WHITEHORN_HOLLOW_KEY,
    TROLL_WINDSCAR_SHELF_KEY,
    TROLL_WINDBREAK_FLAG,
    _handle_cold_quest,
    _handle_outsider_quest,
    _handle_track_quest,
    _initialize_or_reconcile_troll,
    _talk_brannik,
    _talk_raska,
    install_troll_content,
    troll_room_augmentations,
)


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.combatant = CombatantState(
            character_id=character.id,
            race_key="troll",
            current_hp=20,
            max_hp=20,
            current_mana=10,
            max_mana=10,
            auto_attack_interval=2.0,
        )

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    def move_to(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        self.character = self.database.get_character_by_name(self.character.name)


class TrollStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_troll_content()

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

    def _session(self, name: str = "Rime"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "troll_start.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            "troll",
            "brute",
            CharacterStats(might=9, grace=5, love=5, mind=5, hp=12),
        )
        return temp, database, LiveLikeSession(database, character)

    def _finish_cold(self, session: LiveLikeSession):
        _initialize_or_reconcile_troll(session)
        self.assertTrue(asyncio.run(_talk_raska(session)))
        session.move_to(TROLL_HIDEWIND_RING_KEY)
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "examine wind")))
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "gather deadfall")))
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "build windbreak")))
        session.move_to(TROLL_EMBER_HOLLOW_KEY)
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "lay fire")))
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "light fire")))
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "endure cold")))
        self.assertTrue(asyncio.run(_handle_cold_quest(session, "rest by fire")))
        session.move_to(TROLL_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_talk_raska(session)))

    def _finish_tracking(self, session: LiveLikeSession):
        session.move_to(TROLL_TRACKLINE_VERGE_KEY)
        self.assertTrue(asyncio.run(_handle_track_quest(session, "examine tracks")))
        self.assertTrue(asyncio.run(_handle_track_quest(session, "track whitehorn")))
        session.move_to(TROLL_WHITEHORN_HOLLOW_KEY)
        self.assertTrue(asyncio.run(_handle_track_quest(session, "observe whitehorn")))
        self.assertTrue(asyncio.run(_handle_track_quest(session, "leave doe")))
        session.move_to(TROLL_TETHER_YARD_KEY)
        self.assertTrue(asyncio.run(_handle_track_quest(session, "approach elk")))
        self.assertTrue(asyncio.run(_handle_track_quest(session, "check harness")))
        self.assertTrue(asyncio.run(_handle_track_quest(session, "calm elk")))
        session.move_to(TROLL_START_ROOM_KEY)
        self.assertTrue(asyncio.run(_talk_raska(session)))

    def test_eight_room_starter_is_harsh_in_tone_but_safe_in_failure_model(self):
        self.assertEqual(len(TROLL_SURVIVAL_ROOM_KEYS), 8)
        for room_key in TROLL_SURVIVAL_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertEqual(room.region_key, "troll_strongholds")
            self.assertIn("safe", room.tags)
            self.assertEqual(room.enemy_keys, ())
        self.assertIn("troll_start", world.ROOMS_BY_KEY[TROLL_START_ROOM_KEY].tags)
        self.assertIn("danger_hint", world.ROOMS_BY_KEY[TROLL_STONEJAW_PASS_KEY].tags)
        self.assertEqual(world.NPCS_BY_KEY[RASKA_GREYBARK.key].role, "Troll starter mentor, hunter, and survival instructor")
        self.assertIn("animal", world.NPCS_BY_KEY[MORA_ELKHAND.key].role.lower())
        self.assertIn("stereotype", world.NPCS_BY_KEY[BRANNIK_SLATEBOOT.key].role.lower())

    def test_legacy_troll_without_location_is_upgraded_into_frostroot_and_given_first_lesson(self):
        temp, database, session = self._session("OldTroll")
        self.addCleanup(temp.cleanup)
        self.assertIsNone(session.character.current_room)
        self.assertIsNone(session.character.bind_room)

        _initialize_or_reconcile_troll(session)
        self.assertEqual(session.character.current_room, TROLL_START_ROOM_KEY)
        self.assertEqual(session.character.bind_room, TROLL_START_ROOM_KEY)
        quest = database.get_quest(session.character.id, TROLL_COLD_QUEST.key)
        self.assertEqual(quest["status"], "active")
        self.assertEqual(quest["current_step"], "speak_raska")

    def test_first_cold_teaches_shelter_fire_and_exact_troll_regeneration_without_lethal_risk(self):
        temp, database, session = self._session("Coldlesson")
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_troll(session)
        asyncio.run(_talk_raska(session))
        session.move_to(TROLL_HIDEWIND_RING_KEY)
        asyncio.run(_handle_cold_quest(session, "examine wind"))
        asyncio.run(_handle_cold_quest(session, "gather deadfall"))
        asyncio.run(_handle_cold_quest(session, "build windbreak"))
        self.assertIn(TROLL_WINDBREAK_FLAG, database.list_flags(session.character.id))

        session.move_to(TROLL_EMBER_HOLLOW_KEY)
        asyncio.run(_handle_cold_quest(session, "lay fire"))
        asyncio.run(_handle_cold_quest(session, "light fire"))
        self.assertIn(TROLL_FIRE_LIT_FLAG, database.list_flags(session.character.id))

        self.assertEqual(session.combatant.current_hp, 20)
        asyncio.run(_handle_cold_quest(session, "endure cold"))
        self.assertEqual(session.combatant.current_hp, 17)
        asyncio.run(_handle_cold_quest(session, "rest by fire"))
        # Base rest is 2; Troll Regeneration contributes +1, restoring all 3 controlled HP.
        self.assertEqual(session.combatant.current_hp, 20)
        self.assertIn(TROLL_REGEN_LEARNED_FLAG, database.list_flags(session.character.id))

        # The controlled exposure can never reduce an already-wounded beginner below 1 HP.
        database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "endure_cold")
        session.combatant.current_hp = 2
        asyncio.run(_handle_cold_quest(session, "endure cold"))
        self.assertEqual(session.combatant.current_hp, 1)

        database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "return_raska")
        session.move_to(TROLL_START_ROOM_KEY)
        asyncio.run(_talk_raska(session))
        self.assertIn(TROLL_COLD_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, TROLL_COLD_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, TROLL_TRACK_QUEST.key)["current_step"], "study_tracks")

    def test_hunting_lesson_rewards_reading_quarry_and_animal_handling_not_killing(self):
        temp, database, session = self._session("Tracker")
        self.addCleanup(temp.cleanup)
        self._finish_cold(session)

        session.move_to(TROLL_TRACKLINE_VERGE_KEY)
        asyncio.run(_handle_track_quest(session, "examine tracks"))
        asyncio.run(_handle_track_quest(session, "track whitehorn"))
        session.move_to(TROLL_WHITEHORN_HOLLOW_KEY)
        step_before = database.get_quest(session.character.id, TROLL_TRACK_QUEST.key)["current_step"]
        self.assertTrue(asyncio.run(_handle_track_quest(session, "attack doe")))
        self.assertEqual(database.get_quest(session.character.id, TROLL_TRACK_QUEST.key)["current_step"], step_before)
        self.assertEqual(world.ROOMS_BY_KEY[TROLL_WHITEHORN_HOLLOW_KEY].enemy_keys, ())

        asyncio.run(_handle_track_quest(session, "observe whitehorn"))
        asyncio.run(_handle_track_quest(session, "leave doe"))
        self.assertIn(TROLL_QUARRY_JUDGMENT_FLAG, database.list_flags(session.character.id))
        session.move_to(TROLL_TETHER_YARD_KEY)
        asyncio.run(_handle_track_quest(session, "approach elk"))
        asyncio.run(_handle_track_quest(session, "check harness"))
        asyncio.run(_handle_track_quest(session, "calm elk"))
        self.assertIn(TROLL_ANIMAL_HANDLING_FLAG, database.list_flags(session.character.id))
        session.move_to(TROLL_START_ROOM_KEY)
        asyncio.run(_talk_raska(session))
        self.assertIn(TROLL_TRACK_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, TROLL_OUTSIDER_QUEST.key)["current_step"], "meet_outsider")

    def test_outsider_problem_rejects_brute_force_then_flips_stereotype_through_competence(self):
        temp, database, session = self._session("Freightwise")
        self.addCleanup(temp.cleanup)
        self._finish_cold(session)
        self._finish_tracking(session)
        session.move_to(TROLL_WINDSCAR_SHELF_KEY)

        self.assertTrue(asyncio.run(_talk_brannik(session)))
        self.assertEqual(database.get_quest(session.character.id, TROLL_OUTSIDER_QUEST.key)["current_step"], "inspect_problem")
        hp_before = session.combatant.current_hp
        self.assertTrue(asyncio.run(_handle_outsider_quest(session, "pull sledge")))
        self.assertEqual(session.combatant.current_hp, hp_before)
        self.assertEqual(database.get_quest(session.character.id, TROLL_OUTSIDER_QUEST.key)["current_step"], "inspect_problem")

        asyncio.run(_handle_outsider_quest(session, "examine pack ram"))
        asyncio.run(_handle_outsider_quest(session, "calm ram"))
        asyncio.run(_handle_outsider_quest(session, "loosen harness"))
        asyncio.run(_handle_outsider_quest(session, "shift load"))
        asyncio.run(_handle_outsider_quest(session, "read snow"))
        self.assertTrue(asyncio.run(_talk_brannik(session)))

        quest = database.get_quest(session.character.id, TROLL_OUTSIDER_QUEST.key)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(TROLL_OUTSIDER_COMPLETE_FLAG, database.list_flags(session.character.id))
        combined = "".join(session.outputs).lower()
        self.assertIn("biggest person", combined)
        self.assertIn("three smaller problems", combined)

    def test_trackline_gate_requires_preparation_and_all_rooms_have_rich_named_routes(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=troll_room_augmentations())
        unprepared = PlayerRoomContext(character_id=1, race_key="troll", class_key="brute", level=1)
        prepared = PlayerRoomContext(
            character_id=1,
            race_key="troll",
            class_key="brute",
            level=1,
            character_flags=frozenset({TROLL_COLD_COMPLETE_FLAG}),
        )
        blocked = service.resolve_exit(TROLL_HIDEWIND_RING_KEY, "north", unprepared)
        opened = service.resolve_exit(TROLL_HIDEWIND_RING_KEY, "north", prepared)
        self.assertFalse(blocked.allowed)
        self.assertIn("shelter", blocked.message.lower())
        self.assertTrue(opened.allowed)
        self.assertEqual(opened.exit.destination_key, TROLL_TRACKLINE_VERGE_KEY)

        snow_context = PlayerRoomContext(
            character_id=2,
            race_key="troll",
            class_key="druid",
            level=1,
            character_flags=frozenset({TROLL_COLD_COMPLETE_FLAG}),
            weather="snow",
            hour=12,
        )
        for room_key in TROLL_SURVIVAL_ROOM_KEYS:
            view = service.build_view(room_key, snow_context)
            self.assertIsNotNone(view)
            self.assertGreaterEqual(len(view.features), 1)
            for exit_view in view.exits:
                self.assertTrue(exit_view.name)
        camp = service.build_view(TROLL_START_ROOM_KEY, snow_context)
        self.assertIn("fresh snow", camp.description.lower())


if __name__ == "__main__":
    unittest.main()
