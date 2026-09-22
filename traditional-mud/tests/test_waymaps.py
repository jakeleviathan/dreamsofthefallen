from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.crafting as crafting
import mud.waymaps as waymaps
from mud.database import Database
from mud.ground_items import (
    ground_item_quantity,
    transfer_ground_to_inventory,
    transfer_inventory_to_ground,
)
from mud.merchants import COMMON_MERCHANT_STOCK_BY_KEY
from mud.room_engine import (
    ExitDefinition,
    PlayerRoomContext,
    RoomAugmentation,
    WorldService,
)
from mud.stats import CharacterStats
from mud.world import RoomDefinition


class WaymapSession:
    def __init__(self, database: Database, character, world: WorldService):
        self.database = database
        self.character = character
        self.world = world
        self.active_enemy = None
        self.outputs: list[str] = []
        self._waymap_travel_task = None
        self._waymap_travel_id = None
        self._waymap_internal_move = False

    async def send(self, text: str) -> None:
        self.outputs.append(text)

    async def move_character(self, direction: str) -> None:
        context = PlayerRoomContext(
            character_id=self.character.id,
            race_key=self.character.race,
            class_key=self.character.character_class,
            level=self.character.level,
            character_flags=frozenset(self.database.list_flags(self.character.id)),
        )
        resolution = self.world.resolve_exit(self.character.current_room, direction, context)
        if resolution.allowed and resolution.exit is not None:
            self.character.current_room = resolution.exit.destination_key


def simple_world() -> WorldService:
    rooms = {
        "a": RoomDefinition(
            key="a",
            name="A",
            description="Room A.",
            region_key="test",
            exits={"east": "b"},
        ),
        "b": RoomDefinition(
            key="b",
            name="B",
            description="Room B.",
            region_key="test",
            exits={"west": "a", "east": "c"},
        ),
        "c": RoomDefinition(
            key="c",
            name="C",
            description="Room C.",
            region_key="test",
            exits={"west": "b"},
        ),
    }
    augmentations = {
        "b": RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="east",
                    destination_key="c",
                    name="C",
                    door_key="b_to_c",
                    failure_text="The test gate is closed.",
                ),
            ),
        ),
    }
    return WorldService(rooms=rooms, augmentations=augmentations)


class WaymapTests(unittest.TestCase):
    def _database(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "waymaps.db")
        account = database.create_account("waymap_acct", "hash")
        character = database.create_character(
            account.id,
            "Cartographer",
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        return temp, database, account, character

    def test_tailoring_recipe_and_common_vendor_stock_create_blank_maps(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)

        self.assertIn("tailoring", crafting.PROFESSIONS_BY_KEY)
        self.assertEqual(
            crafting.RECIPES_BY_KEY["prepare_blank_waymap"].trade_skill_key,
            "tailoring",
        )
        self.assertIn(waymaps.BLANK_WAYMAP_KEY, COMMON_MERCHANT_STOCK_BY_KEY)
        self.assertEqual(
            COMMON_MERCHANT_STOCK_BY_KEY[waymaps.BLANK_WAYMAP_KEY].price_units,
            8,
        )

        database.add_item(character.id, "cotton_cloth", 1)
        result = crafting.craft_recipe(
            database,
            character.id,
            "prepare_blank_waymap",
            station_key=None,
            success_roll=0.0,
            skillup_roll=1.0,
        )
        self.assertTrue(result.success, result.message)
        self.assertEqual(database.item_quantity(character.id, waymaps.BLANK_WAYMAP_KEY), 1)

    def test_marking_consumes_one_blank_and_creates_persistent_map_identity(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(character.id, waymaps.BLANK_WAYMAP_KEY, 2)

        row = waymaps.mark_blank_waymap(
            database,
            character_id=character.id,
            destination_room_key="human_demon_gate",
            destination_name="The Demon Gate",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(database.item_quantity(character.id, waymaps.BLANK_WAYMAP_KEY), 1)
        self.assertEqual(database.item_quantity(character.id, waymaps.MARKED_WAYMAP_KEY), 1)
        self.assertEqual(row.cartographer_name, "Cartographer")
        self.assertEqual(row.destination_name, "The Demon Gate")
        self.assertEqual(waymaps.audit_waymaps(database), ())

        reopened = Database(database.path)
        carried = waymaps.list_character_waymaps(reopened, character.id)
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0].id, row.id)
        self.assertEqual(carried[0].destination_room_key, "human_demon_gate")
        self.assertEqual(waymaps.audit_waymaps(reopened), ())

    def test_drop_and_pickup_preserve_the_same_marked_waymap(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(character.id, waymaps.BLANK_WAYMAP_KEY, 1)
        row = waymaps.mark_blank_waymap(
            database,
            character_id=character.id,
            destination_room_key="human_demon_gate",
            destination_name="The Demon Gate",
        )
        assert row is not None
        room_key = character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None

        self.assertTrue(
            transfer_inventory_to_ground(
                database,
                character.id,
                room_key,
                waymaps.MARKED_WAYMAP_KEY,
                1,
            )
        )
        self.assertEqual(database.item_quantity(character.id, waymaps.MARKED_WAYMAP_KEY), 0)
        self.assertEqual(ground_item_quantity(database, room_key, waymaps.MARKED_WAYMAP_KEY), 1)
        on_ground = waymaps.list_room_waymaps(database, room_key)
        self.assertEqual([item.id for item in on_ground], [row.id])
        self.assertEqual(waymaps.audit_waymaps(database), ())

        self.assertTrue(
            transfer_ground_to_inventory(
                database,
                character.id,
                room_key,
                waymaps.MARKED_WAYMAP_KEY,
                1,
            )
        )
        carried = waymaps.list_character_waymaps(database, character.id)
        self.assertEqual([item.id for item in carried], [row.id])
        self.assertEqual(waymaps.audit_waymaps(database), ())

    def test_specific_waymap_can_be_given_without_losing_destination_or_cartographer(self):
        temp, database, account, first = self._database()
        self.addCleanup(temp.cleanup)
        second = database.create_character(
            account.id,
            "Buyer",
            "dwarf",
            "brute",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        database.add_item(first.id, waymaps.BLANK_WAYMAP_KEY, 1)
        row = waymaps.mark_blank_waymap(
            database,
            character_id=first.id,
            destination_room_key="human_demon_gate",
            destination_name="The Demon Gate",
        )
        assert row is not None

        moved = waymaps.transfer_specific_waymap_between_characters(
            database,
            waymap_id=row.id,
            from_character_id=first.id,
            to_character_id=second.id,
        )
        self.assertIsNotNone(moved)
        assert moved is not None
        self.assertEqual(moved.id, row.id)
        self.assertEqual(moved.destination_room_key, row.destination_room_key)
        self.assertEqual(moved.cartographer_name, "Cartographer")
        self.assertEqual(waymaps.list_character_waymaps(database, first.id), ())
        buyer_maps = waymaps.list_character_waymaps(database, second.id)
        self.assertEqual([item.id for item in buyer_maps], [row.id])
        self.assertEqual(waymaps.audit_waymaps(database), ())

    def test_shortest_route_uses_real_passability_and_reacts_to_closed_doors(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        world = simple_world()
        fake_character = SimpleNamespace(
            id=character.id,
            race="human",
            character_class="wizard",
            level=1,
            current_room="a",
        )
        session = WaymapSession(database, fake_character, world)

        self.assertEqual(waymaps.shortest_route(world, session, "a", "c"), ("east", "east"))

        world.state.set_door("b_to_c", open=False)
        self.assertIsNone(waymaps.shortest_route(world, session, "a", "c"))

        world.state.set_door("b_to_c", open=True, locked=True)
        self.assertIsNone(waymaps.shortest_route(world, session, "a", "c"))

    def test_autowalk_moves_room_by_room_and_records_completed_journey(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        world = simple_world()
        fake_character = SimpleNamespace(
            id=character.id,
            race="human",
            character_class="wizard",
            level=1,
            current_room="a",
        )
        session = WaymapSession(database, fake_character, world)
        database.add_item(character.id, waymaps.BLANK_WAYMAP_KEY, 1)
        row = waymaps.mark_blank_waymap(
            database,
            character_id=character.id,
            destination_room_key="c",
            destination_name="C",
        )
        assert row is not None

        previous_delay = waymaps.WAYMAP_STEP_DELAY_SECONDS
        waymaps.WAYMAP_STEP_DELAY_SECONDS = 0.0
        try:
            asyncio.run(waymaps._walk_waymap(session, world, row))
        finally:
            waymaps.WAYMAP_STEP_DELAY_SECONDS = previous_delay

        self.assertEqual(fake_character.current_room, "c")
        updated = waymaps.list_character_waymaps(database, character.id)[0]
        self.assertEqual(updated.journeys_completed, 1)
        output = "".join(session.outputs)
        self.assertIn("guides you east", output)
        self.assertIn("arrived at C", output)

    def test_autowalk_stops_before_a_newly_blocked_step(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        world = simple_world()
        world.state.set_door("b_to_c", open=False)
        fake_character = SimpleNamespace(
            id=character.id,
            race="human",
            character_class="wizard",
            level=1,
            current_room="a",
        )
        session = WaymapSession(database, fake_character, world)
        database.add_item(character.id, waymaps.BLANK_WAYMAP_KEY, 1)
        row = waymaps.mark_blank_waymap(
            database,
            character_id=character.id,
            destination_room_key="c",
            destination_name="C",
        )
        assert row is not None

        previous_delay = waymaps.WAYMAP_STEP_DELAY_SECONDS
        waymaps.WAYMAP_STEP_DELAY_SECONDS = 0.0
        try:
            asyncio.run(waymaps._walk_waymap(session, world, row))
        finally:
            waymaps.WAYMAP_STEP_DELAY_SECONDS = previous_delay

        self.assertEqual(fake_character.current_room, "a")
        self.assertEqual(
            waymaps.list_character_waymaps(database, character.id)[0].journeys_completed,
            0,
        )
        self.assertIn("can no longer trace a passable route", "".join(session.outputs))

    def test_waymap_audit_detects_a_stack_without_an_identity(self):
        temp, database, _account, character = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(character.id, waymaps.MARKED_WAYMAP_KEY, 1)
        problems = waymaps.audit_waymaps(database)
        self.assertTrue(any("character" in problem and "stack 1" in problem for problem in problems))

    def test_deleting_a_character_retires_held_waymap_provenance(self):
        temp, database, account, character = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(character.id, waymaps.BLANK_WAYMAP_KEY, 1)
        row = waymaps.mark_blank_waymap(
            database,
            character_id=character.id,
            destination_room_key="human_demon_gate",
            destination_name="The Demon Gate",
        )
        assert row is not None

        self.assertTrue(database.delete_character(account.id, character.id))
        with database.connect() as db:
            stored = db.execute(
                "SELECT holder_kind, holder_key FROM waymap_instances WHERE id = ?",
                (row.id,),
            ).fetchone()
        self.assertIsNotNone(stored)
        self.assertEqual(stored["holder_kind"], "retired")
        self.assertEqual(stored["holder_key"], "character_deleted")


if __name__ == "__main__":
    unittest.main()
