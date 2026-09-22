from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.command_help import _full_help_text, _quick_help_text
from mud.database import Database
from mud.equipment_system import equipped_item_keys, set_equipped_item
from mud.ground_items import (
    _item_detail_lines,
    _show_ground_items,
    drop_item_command,
    inspect_ground_item_command,
    ground_item_quantity,
    list_ground_items,
    take_item_command,
    transfer_ground_to_inventory,
    transfer_inventory_to_ground,
)
from mud.stats import CharacterStats


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.active_enemy = None
        self.outputs: list[str] = []

    async def send(self, text: str) -> None:
        self.outputs.append(text)


class GroundItemTests(unittest.TestCase):
    def _session(self, name: str = "Grounder"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "ground-items.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            "human",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        return temp, database, LiveLikeSession(database, character)

    def test_drop_and_pickup_are_atomic_inventory_room_transfers(self):
        temp, database, session = self._session("Atomic")
        self.addCleanup(temp.cleanup)
        character_id = session.character.id
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        database.add_item(character_id, "bone_chips", 4)

        self.assertTrue(
            transfer_inventory_to_ground(database, character_id, room_key, "bone_chips", 3)
        )
        self.assertEqual(database.item_quantity(character_id, "bone_chips"), 1)
        self.assertEqual(ground_item_quantity(database, room_key, "bone_chips"), 3)

        self.assertTrue(
            transfer_ground_to_inventory(database, character_id, room_key, "bone_chips", 2)
        )
        self.assertEqual(database.item_quantity(character_id, "bone_chips"), 3)
        self.assertEqual(ground_item_quantity(database, room_key, "bone_chips"), 1)

    def test_ground_items_persist_across_database_reopen(self):
        temp, database, session = self._session("PersistGround")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        database.add_item(session.character.id, "bone_chips", 2)
        self.assertTrue(
            transfer_inventory_to_ground(database, session.character.id, room_key, "bone_chips", 2)
        )

        reopened = Database(database.path)
        self.assertEqual(ground_item_quantity(reopened, room_key, "bone_chips"), 2)
        self.assertEqual(
            list_ground_items(reopened, room_key),
            [{"item_key": "bone_chips", "quantity": 2}],
        )

    def test_drop_command_supports_quantities_and_take_picks_them_back_up(self):
        temp, database, session = self._session("Commands")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        database.add_item(session.character.id, "bone_chips", 5)

        asyncio.run(drop_item_command(session, "3 bone chips"))
        self.assertEqual(database.item_quantity(session.character.id, "bone_chips"), 2)
        self.assertEqual(ground_item_quantity(database, room_key, "bone_chips"), 3)
        self.assertIn("You drop 3x Bone Chips.", "".join(session.outputs))

        session.outputs.clear()
        handled = asyncio.run(take_item_command(session, "2 bone chips"))
        self.assertTrue(handled)
        self.assertEqual(database.item_quantity(session.character.id, "bone_chips"), 4)
        self.assertEqual(ground_item_quantity(database, room_key, "bone_chips"), 1)
        self.assertIn("You pick up 2x Bone Chips.", "".join(session.outputs))

    def test_quest_items_cannot_be_dropped(self):
        temp, database, session = self._session("QuestSafe")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None

        self.assertEqual(database.item_quantity(session.character.id, "sealed_cathedral_note"), 1)
        asyncio.run(drop_item_command(session, "cathedral note"))

        self.assertEqual(database.item_quantity(session.character.id, "sealed_cathedral_note"), 1)
        self.assertEqual(ground_item_quantity(database, room_key, "sealed_cathedral_note"), 0)
        self.assertIn("quest item and cannot be dropped", "".join(session.outputs).lower())

    def test_last_equipped_copy_must_be_unequipped_before_drop(self):
        temp, database, session = self._session("EquippedSafe")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        set_equipped_item(database, session.character.id, "main_hand", "starter_weapon")

        asyncio.run(drop_item_command(session, "basic starting weapon"))
        self.assertEqual(database.item_quantity(session.character.id, "starter_weapon"), 1)
        self.assertEqual(ground_item_quantity(database, room_key, "starter_weapon"), 0)
        self.assertEqual(equipped_item_keys(database, session.character.id)["main_hand"], "starter_weapon")
        self.assertIn("unequip", "".join(session.outputs).lower())

        # Owning a spare copy is safe: the equipped copy remains represented in inventory.
        database.add_item(session.character.id, "starter_weapon", 1)
        session.outputs.clear()
        asyncio.run(drop_item_command(session, "basic starting weapon"))
        self.assertEqual(database.item_quantity(session.character.id, "starter_weapon"), 1)
        self.assertEqual(ground_item_quantity(database, room_key, "starter_weapon"), 1)
        self.assertEqual(equipped_item_keys(database, session.character.id)["main_hand"], "starter_weapon")

    def test_room_ground_items_are_visible_to_look_output(self):
        temp, database, session = self._session("Visible")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        database.add_item(session.character.id, "bone_chips", 2)
        transfer_inventory_to_ground(database, session.character.id, room_key, "bone_chips", 2)

        asyncio.run(_show_ground_items(session))
        output = "".join(session.outputs)
        self.assertIn("On the ground:", output)
        self.assertIn("2x Bone Chips", output)

    def test_dropped_items_can_be_looked_at_by_partial_name(self):
        temp, database, session = self._session("InspectGround")
        self.addCleanup(temp.cleanup)
        room_key = session.character.current_room
        self.assertIsNotNone(room_key)
        assert room_key is not None
        database.add_item(session.character.id, "cotton_hood", 1)
        transfer_inventory_to_ground(database, session.character.id, room_key, "cotton_hood", 1)

        handled = asyncio.run(inspect_ground_item_command(session, "hood"))
        self.assertTrue(handled)
        output = "".join(session.outputs)
        self.assertIn("Cotton Hood", output)
        self.assertIn("hood sewn from cotton cloth", output)
        self.assertIn("Slot: Head", output)
        self.assertIn("AC +1", output)

    def test_ground_item_detail_reports_stack_quantity(self):
        rendered = "\n".join(_item_detail_lines("bone_chips", 3))
        self.assertIn("Quantity here: 3", rendered)

    def test_missing_ground_item_defers_to_older_contextual_take_handlers(self):
        temp, _database, session = self._session("ContextSafe")
        self.addCleanup(temp.cleanup)
        handled = asyncio.run(take_item_command(session, "tutorial spear"))
        self.assertFalse(handled)
        self.assertEqual(session.outputs, [])

    def test_help_advertises_drop_and_pickup_commands(self):
        temp, _database, session = self._session("HelpGround")
        self.addCleanup(temp.cleanup)
        quick = _quick_help_text(session)
        full = _full_help_text(session)
        self.assertIn("DROP", quick)
        self.assertIn("GET", quick)
        self.assertIn("DROP <item>", full)
        self.assertIn("TAKE <item>", full)


if __name__ == "__main__":
    unittest.main()
