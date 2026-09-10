from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.character_options as character_options
import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.undead_start import (
    UNDEAD_BINDING_EXAMINED_FLAG,
    UNDEAD_BOUND_SENTINEL_KEY,
    UNDEAD_CHISEL_MARKET_KEY,
    UNDEAD_CHOSEN_REQUEST_QUEST,
    UNDEAD_COMMAND_SIGIL_BROKEN_FLAG,
    UNDEAD_COMMAND_VAULT_KEY,
    UNDEAD_CONCOURSE_KEY,
    UNDEAD_DESERT_GATE_KEY,
    UNDEAD_EFFECTS_EXAMINED_FLAG,
    UNDEAD_FIRST_OUTSIDE_FLAG,
    UNDEAD_FORMER_LIVES_ARCHIVE_KEY,
    UNDEAD_FREEHANDS_COURT_KEY,
    UNDEAD_LAMP_DELIVERED_FLAG,
    UNDEAD_MARKET_SEEN_FLAG,
    UNDEAD_MASTER_SILENCE_HEARD_FLAG,
    UNDEAD_MEMORY_DONATE_FLAG,
    UNDEAD_MEMORY_KEEP_FLAG,
    UNDEAD_MEMORY_KEY_ITEM,
    UNDEAD_MEMORY_QUEST,
    UNDEAD_MEMORY_SPARKED_FLAG,
    UNDEAD_NO_VOICE_QUEST,
    UNDEAD_OPENING_COMPLETE_FLAG,
    UNDEAD_ORDERS_SEVERED_FLAG,
    UNDEAD_REMAINING_ORDER_QUEST,
    UNDEAD_REQUEST_DECLINE_FLAG,
    UNDEAD_REQUEST_HELP_FLAG,
    UNDEAD_SENTINEL_DEFEATED_FLAG,
    UNDEAD_SEVERANCE_HALL_KEY,
    UNDEAD_START_ROOM_KEY,
    UNDEAD_START_ROOM_KEYS,
    UNDEAD_SUNSCAR_ROAD_KEY,
    _post_move_progress,
    _record_sentinel_defeat,
    handle_undead_start_command,
    install_undead_content,
    prepare_undead_start,
    undead_room_augmentations,
)


class FakeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)


def move(session: FakeSession, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    refreshed = session.database.get_character_by_name(session.character.name)
    assert refreshed is not None
    session.character = refreshed


def arrive(session: FakeSession, room_key: str) -> list[str]:
    move(session, room_key)
    return _post_move_progress(session, room_key)


class UndeadStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        self.races = character_options.RACES
        self.races_by_key = dict(character_options.RACES_BY_KEY)
        install_undead_content()

    def tearDown(self):
        legacy_world.ROOMS = self.rooms
        legacy_world.ROOMS_BY_KEY.clear()
        legacy_world.ROOMS_BY_KEY.update(self.rooms_by_key)
        legacy_world.NPCS = self.npcs
        legacy_world.NPCS_BY_KEY.clear()
        legacy_world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quest_map)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)
        character_options.RACES = self.races
        character_options.RACES_BY_KEY.clear()
        character_options.RACES_BY_KEY.update(self.races_by_key)

    def _session(self, name: str = "Rattle"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "undead.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(account.id, name, "undead", "wizard")
        return temp, database, FakeSession(database, character)

    def test_identity_is_literal_undead_but_centered_on_freedom_not_reclaimed_slur(self):
        race = character_options.RACES_BY_KEY["undead"]
        self.assertIn("Literal skeletal Undead", race.description)
        lore = " ".join(race.lore).lower()
        self.assertIn("soldiers", lore)
        self.assertIn("command networks", lore)
        self.assertIn("freedom after ownership", lore)
        self.assertIn("personhood", lore)
        self.assertIn("skeletons", lore)
        self.assertFalse(race.needs_food)
        self.assertFalse(race.needs_drink)
        self.assertFalse(race.needs_sleep)
        self.assertFalse(race.needs_breath)
        self.assertTrue(race.normal_healing_magic)

    def test_start_is_nine_room_necropolis_slice_with_rich_scenes_and_real_society(self):
        self.assertEqual(len(UNDEAD_START_ROOM_KEYS), 9)
        augmentations = undead_room_augmentations()
        self.assertEqual(set(augmentations), set(UNDEAD_START_ROOM_KEYS))
        for room_key in UNDEAD_START_ROOM_KEYS:
            self.assertIn(room_key, legacy_world.ROOMS_BY_KEY)
            augmentation = augmentations[room_key]
            self.assertGreaterEqual(len(augmentation.features), 2)
            self.assertGreaterEqual(len(augmentation.description_layers), 1)
            self.assertEqual(
                {exit_def.direction for exit_def in augmentation.exit_overrides},
                set(legacy_world.ROOMS_BY_KEY[room_key].exits),
            )
        market = legacy_world.ROOMS_BY_KEY[UNDEAD_CHISEL_MARKET_KEY].description.lower()
        self.assertIn("argues", market)
        self.assertIn("laughs", market)
        self.assertIn("bonewrights", market)

    def test_new_undead_wakes_unowned_then_severs_the_last_command_thread(self):
        temp, database, session = self._session("Sever")
        self.addCleanup(temp.cleanup)
        self.assertIsNone(session.character.current_room)
        self.assertTrue(prepare_undead_start(session))
        self.assertEqual(session.character.current_room, UNDEAD_START_ROOM_KEY)
        self.assertEqual(session.character.bind_room, UNDEAD_START_ROOM_KEY)
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key)["current_step"], "listen_silence")

        self.assertTrue(asyncio.run(handle_undead_start_command(session, "listen")))
        self.assertIn(UNDEAD_MASTER_SILENCE_HEARD_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "talk reclaimer")))
        move(session, UNDEAD_SEVERANCE_HALL_KEY)
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "examine binding")))
        self.assertIn(UNDEAD_BINDING_EXAMINED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "sever orders")))
        self.assertIn(UNDEAD_ORDERS_SEVERED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_MEMORY_QUEST.key)["current_step"], "reach_archive")
        output = "".join(session.outputs).lower()
        self.assertIn("nobody here owns you either", output)
        self.assertIn("no required gratitude", output)

    def test_memory_fragment_is_ordinary_and_player_can_keep_donate_or_destroy_it(self):
        for choice, expected_flag in (
            ("keep key", UNDEAD_MEMORY_KEEP_FLAG),
            ("donate key", UNDEAD_MEMORY_DONATE_FLAG),
            ("destroy key", "undead_memory_key_destroyed"),
        ):
            with self.subTest(choice=choice):
                temp, database, session = self._session("Memory" + choice.split()[0])
                self.addCleanup(temp.cleanup)
                prepare_undead_start(session)
                database.complete_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key)
                database.start_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "reach_archive")
                arrive(session, UNDEAD_FORMER_LIVES_ARCHIVE_KEY)
                self.assertTrue(asyncio.run(handle_undead_start_command(session, "examine effects")))
                self.assertIn(UNDEAD_EFFECTS_EXAMINED_FLAG, database.list_flags(session.character.id))
                self.assertTrue(asyncio.run(handle_undead_start_command(session, "touch key")))
                self.assertIn(UNDEAD_MEMORY_SPARKED_FLAG, database.list_flags(session.character.id))
                self.assertEqual(database.item_quantity(session.character.id, UNDEAD_MEMORY_KEY_ITEM), 1)
                self.assertTrue(asyncio.run(handle_undead_start_command(session, choice)))
                self.assertIn(expected_flag, database.list_flags(session.character.id))
                expected_quantity = 1 if choice == "keep key" else 0
                self.assertEqual(database.item_quantity(session.character.id, UNDEAD_MEMORY_KEY_ITEM), expected_quantity)
                self.assertEqual(database.get_quest(session.character.id, UNDEAD_MEMORY_QUEST.key)["status"], "completed")
                self.assertEqual(database.get_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key)["current_step"], "reach_vault")
                output = "".join(session.outputs).lower()
                self.assertIn("rain", output)
                self.assertIn("no face", output)
                self.assertIn("no name", output)

    def test_bound_sentinel_is_what_player_could_have_remained_and_order_must_be_broken(self):
        temp, database, session = self._session("Order")
        self.addCleanup(temp.cleanup)
        prepare_undead_start(session)
        database.complete_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key)
        database.start_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "complete")
        database.complete_quest(session.character.id, UNDEAD_MEMORY_QUEST.key)
        database.start_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key, "reach_vault")

        messages = arrive(session, UNDEAD_COMMAND_VAULT_KEY)
        self.assertTrue(any("ATTACK SENTINEL" in message for message in messages))
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key)["current_step"], "fight_sentinel")
        self.assertEqual(combat.ENEMIES_BY_KEY[UNDEAD_BOUND_SENTINEL_KEY].max_hp, 20)
        _record_sentinel_defeat(session)
        self.assertIn(UNDEAD_SENTINEL_DEFEATED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key)["current_step"], "break_sigil")
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "break sigil")))
        self.assertIn(UNDEAD_COMMAND_SIGIL_BROKEN_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key)["current_step"], "walk_market")
        self.assertIn("self that may remain", "".join(session.outputs).lower())

    def _advance_to_request(self, session: FakeSession, database: Database) -> None:
        prepare_undead_start(session)
        database.complete_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key)
        database.start_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "complete")
        database.complete_quest(session.character.id, UNDEAD_MEMORY_QUEST.key)
        database.start_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key, "complete")
        database.complete_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key)
        database.start_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key, "walk_market")
        messages = arrive(session, UNDEAD_CHISEL_MARKET_KEY)
        self.assertTrue(messages)
        self.assertIn(UNDEAD_MARKET_SEEN_FLAG, database.list_flags(session.character.id))
        move(session, UNDEAD_FREEHANDS_COURT_KEY)
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "talk tal")))

    def test_final_request_is_actual_choice_and_declining_does_not_punish_player(self):
        temp, database, session = self._session("Decline")
        self.addCleanup(temp.cleanup)
        self._advance_to_request(session, database)
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "decline tal")))
        flags = database.list_flags(session.character.id)
        self.assertIn(UNDEAD_REQUEST_DECLINE_FLAG, flags)
        self.assertIn(UNDEAD_OPENING_COMPLETE_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key)["status"], "completed")
        self.assertIn("entire consequence", "".join(session.outputs).lower())
        arrive(session, UNDEAD_SUNSCAR_ROAD_KEY)
        self.assertIn(UNDEAD_FIRST_OUTSIDE_FLAG, database.list_flags(session.character.id))

    def test_help_route_is_voluntary_and_ends_with_an_ordinary_civic_delivery(self):
        temp, database, session = self._session("Help")
        self.addCleanup(temp.cleanup)
        self._advance_to_request(session, database)
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "help tal")))
        self.assertIn(UNDEAD_REQUEST_HELP_FLAG, database.list_flags(session.character.id))
        move(session, UNDEAD_DESERT_GATE_KEY)
        self.assertTrue(asyncio.run(handle_undead_start_command(session, "deliver lamp")))
        flags = database.list_flags(session.character.id)
        self.assertIn(UNDEAD_LAMP_DELIVERED_FLAG, flags)
        self.assertIn(UNDEAD_OPENING_COMPLETE_FLAG, flags)
        self.assertEqual(database.get_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key)["status"], "completed")
        output = "".join(session.outputs).lower()
        self.assertIn("somebody asked", output)
        self.assertIn("decided the answer was yes", output)


if __name__ == "__main__":
    unittest.main()
