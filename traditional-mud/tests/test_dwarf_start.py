import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.dwarf_start import (
    APPRENTICE_WORK_ORDER,
    COMPLETED_WORK_ORDER,
    COUNTERSIGNED_WORK_ORDER,
    DWARF_CIVIC_CLEARANCE_FLAG,
    DWARF_FIRST_OBLIGATION_FLAG,
    DWARF_FIRST_WORK_ORDER,
    DWARF_LIFT_FLAG,
    DWARF_LIFT_PLATFORM_KEY,
    DWARF_PRESSURE_FLAG,
    DWARF_PRESSURE_GALLERY_KEY,
    DWARF_REGISTRY_FLAG,
    DWARF_REGISTRY_HALL_KEY,
    DWARF_START_ROOM_KEY,
    DWARF_START_ROOM_KEYS,
    DWARF_UNION_FLAG,
    DWARF_UNION_HALL_KEY,
    REGISTERED_WORK_ORDER,
    _handle_dwarf_tutorial,
    _initialize_or_reconcile_dwarf,
    _show_obligations,
    _talk_helga,
    _talk_torren,
    dwarf_room_augmentations,
    install_dwarf_content,
)
from mud.room_engine import PlayerRoomContext, WorldService
from mud.stats import CharacterStats


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs = []

    async def send(self, text):
        self.outputs.append(text)

    def move_to(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        self.character = self.database.get_character_by_name(self.character.name)


class DwarfStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_dwarf_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

    def _database_session(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "dwarf.db")
        account = database.create_account("dwarf_test", "not-a-real-hash")
        character = database.create_character(
            account.id,
            "BramTest",
            "dwarf",
            "brute",
            CharacterStats(might=10, grace=6, love=5, mind=5, hp=15),
        )
        session = LiveLikeSession(database, character)
        return temp, database, session

    def test_dwarf_start_is_eight_room_safe_industrial_city_core(self):
        self.assertEqual(len(DWARF_START_ROOM_KEYS), 8)
        for room_key in DWARF_START_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertEqual(room.region_key, "dwarven_mountain_industry")
            self.assertIn("safe", room.tags)
            self.assertEqual(room.enemy_keys, ())

        start = world.ROOMS_BY_KEY[DWARF_START_ROOM_KEY]
        self.assertIn("steam", start.tags)
        self.assertIn("cosmopolitan", start.tags)
        self.assertIn("Trade House Arcade", world.ROOMS_BY_KEY["dwarf_trade_house_arcade"].name)
        self.assertIn("union", world.ROOMS_BY_KEY[DWARF_UNION_HALL_KEY].tags)

    def test_every_dwarf_start_room_has_rich_scene_and_named_routes(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=dwarf_room_augmentations())
        context = PlayerRoomContext(character_id=1, race_key="dwarf", class_key="brute", level=1)
        for room_key in DWARF_START_ROOM_KEYS:
            view = service.build_view(room_key, context)
            self.assertIsNotNone(view)
            self.assertGreaterEqual(len(view.features), 1)
            for visible_exit in view.exits:
                self.assertTrue(visible_exit.name)

    def test_upper_freight_route_is_hidden_until_first_obligation_closes(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=dwarf_room_augmentations())
        unready = PlayerRoomContext(character_id=1, race_key="dwarf", class_key="brute", level=1)
        ready = PlayerRoomContext(
            character_id=1,
            race_key="dwarf",
            class_key="brute",
            level=1,
            character_flags=frozenset({DWARF_CIVIC_CLEARANCE_FLAG}),
        )
        hidden = service.resolve_exit(DWARF_LIFT_PLATFORM_KEY, "up", unready)
        opened = service.resolve_exit(DWARF_LIFT_PLATFORM_KEY, "up", ready)
        self.assertFalse(hidden.allowed)
        self.assertTrue(opened.allowed)
        self.assertEqual(opened.exit.destination_key, "dwarf_upper_freight_deck")

    def test_new_dwarf_is_upgraded_into_authored_start_with_persistent_work_order(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        self.assertIsNone(session.character.current_room)

        _initialize_or_reconcile_dwarf(session)
        self.assertEqual(session.character.current_room, DWARF_START_ROOM_KEY)
        self.assertEqual(session.character.bind_room, DWARF_START_ROOM_KEY)
        quest = database.get_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key)
        self.assertEqual(quest["status"], "active")
        self.assertEqual(quest["current_step"], "registry_stamp")
        self.assertEqual(database.item_quantity(session.character.id, APPRENTICE_WORK_ORDER.key), 1)

        # Reopening the SQLite database and reconciling does not duplicate cargo.
        reopened = Database(database.path)
        session.database = reopened
        session.character = reopened.get_character_by_name("BramTest")
        _initialize_or_reconcile_dwarf(session)
        self.assertEqual(reopened.item_quantity(session.character.id, APPRENTICE_WORK_ORDER.key), 1)
        self.assertEqual(reopened.get_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "registry_stamp")

    def test_full_work_order_teaches_registry_union_pressure_and_lift_in_order(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_dwarf(session)
        character_id = session.character.id

        session.move_to(DWARF_REGISTRY_HALL_KEY)
        self.assertTrue(asyncio.run(_talk_helga(session)))
        self.assertEqual(database.item_quantity(character_id, APPRENTICE_WORK_ORDER.key), 0)
        self.assertEqual(database.item_quantity(character_id, REGISTERED_WORK_ORDER.key), 1)
        self.assertIn(DWARF_REGISTRY_FLAG, database.list_flags(character_id))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "union_counterseal")

        session.move_to(DWARF_UNION_HALL_KEY)
        self.assertTrue(asyncio.run(_talk_torren(session)))
        self.assertEqual(database.item_quantity(character_id, REGISTERED_WORK_ORDER.key), 0)
        self.assertEqual(database.item_quantity(character_id, COUNTERSIGNED_WORK_ORDER.key), 1)
        self.assertIn(DWARF_UNION_FLAG, database.list_flags(character_id))

        session.move_to(DWARF_PRESSURE_GALLERY_KEY)
        self.assertTrue(asyncio.run(_handle_dwarf_tutorial(session, "turn intake valve")))
        self.assertNotIn(DWARF_PRESSURE_FLAG, database.list_flags(character_id))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "inspect_pressure")

        self.assertTrue(asyncio.run(_handle_dwarf_tutorial(session, "examine pressure gauge")))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "set_pressure")
        self.assertTrue(asyncio.run(_handle_dwarf_tutorial(session, "turn bypass valve")))
        self.assertNotIn(DWARF_PRESSURE_FLAG, database.list_flags(character_id))

        self.assertTrue(asyncio.run(_handle_dwarf_tutorial(session, "turn bleed valve")))
        self.assertIn(DWARF_PRESSURE_FLAG, database.list_flags(character_id))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "operate_lift")

        session.move_to(DWARF_LIFT_PLATFORM_KEY)
        self.assertTrue(asyncio.run(_handle_dwarf_tutorial(session, "operate lift")))
        self.assertIn(DWARF_LIFT_FLAG, database.list_flags(character_id))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["current_step"], "return_registry")

        session.move_to(DWARF_REGISTRY_HALL_KEY)
        self.assertTrue(asyncio.run(_talk_helga(session)))
        self.assertEqual(database.get_quest(character_id, DWARF_FIRST_WORK_ORDER.key)["status"], "completed")
        self.assertIn(DWARF_CIVIC_CLEARANCE_FLAG, database.list_flags(character_id))
        self.assertIn(DWARF_FIRST_OBLIGATION_FLAG, database.list_flags(character_id))
        self.assertEqual(database.item_quantity(character_id, COUNTERSIGNED_WORK_ORDER.key), 0)
        self.assertEqual(database.item_quantity(character_id, COMPLETED_WORK_ORDER.key), 1)

        # Completion and reconciliation are idempotent.
        self.assertTrue(asyncio.run(_talk_helga(session)))
        _initialize_or_reconcile_dwarf(session)
        self.assertEqual(database.item_quantity(character_id, COMPLETED_WORK_ORDER.key), 1)

    def test_obligations_command_reports_procedure_not_faction_membership(self):
        temp, database, session = self._database_session()
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_dwarf(session)
        asyncio.run(_show_obligations(session))
        output = "".join(session.outputs).lower()
        self.assertIn("dwarven civic record", output)
        self.assertIn("registry authorization", output)
        self.assertIn("union safety counterseal", output)
        self.assertIn("not exclusive trade-house or union membership", output)


if __name__ == "__main__":
    unittest.main()
