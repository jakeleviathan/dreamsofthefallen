from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
from mud.database import Database
from mud.equipment_system import _show_item_detail, install_equipment_content
from mud.item_heritage import (
    SPECIAL_ITEM_KEYS,
    audit_item_heritage,
    ensure_item_heritage_schema,
    ensure_special_inventory_item,
    owned_heritage_rows,
    render_provenance,
    special_found_total,
)
from mud.item_locations import (
    ItemLocation,
    add_to_location,
    ensure_item_location_storage,
    transfer_item,
)
from mud.trade_experience import exchange_items


class DummyTelnet:
    gmcp_enabled = False

    async def send_gmcp(self, *_args, **_kwargs):
        return False


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.telnet = DummyTelnet()

    async def send(self, text: str) -> None:
        self.outputs.append(text)


class ItemHeritageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_items = crafting.ITEMS
        self.original_items_by_key = dict(crafting.ITEMS_BY_KEY)
        install_equipment_content()

    def tearDown(self) -> None:
        SPECIAL_ITEM_KEYS.discard("iron_ore")
        crafting.ITEMS = self.original_items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.original_items_by_key)

    def _database(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "heritage.db")
        first_account = database.create_account("heritage_one", "hash")
        second_account = database.create_account("heritage_two", "hash")
        first = database.create_character(first_account.id, "Prime", "goblin", "priest")
        second = database.create_character(second_account.id, "Morrow", "human", "wizard")
        return temp, database, first, second

    def _craft_cotton_hood(self, database: Database, character_id: int):
        database.add_item(character_id, "cotton_cloth", 1)
        result = crafting.craft_recipe(
            database,
            character_id,
            "sew_cotton_hood",
            station_key="loom",
            success_roll=0.0,
            skillup_roll=1.0,
        )
        self.assertTrue(result.success, result.message)
        return result

    def test_every_crafted_gear_piece_gets_permanent_maker_mark_and_sequence(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)

        self._craft_cotton_hood(database, prime.id)
        self._craft_cotton_hood(database, prime.id)

        rows = owned_heritage_rows(database, prime.id, "cotton_hood", carried_only=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual([int(row["maker_sequence"]) for row in rows], [1, 2])
        self.assertEqual({str(row["maker_name"]) for row in rows}, {"Prime"})
        self.assertEqual({str(row["recipe_key"]) for row in rows}, {"sew_cotton_hood"})
        self.assertTrue(all(row["recipe_revision"] for row in rows))
        self.assertTrue(all(int(row["recipe_version"]) == 1 for row in rows))
        self.assertTrue(all(str(row["serial"]).startswith("C") for row in rows))

        text = render_provenance(database, prime.id, "cotton_hood")
        self.assertIn("Prime's #1 Cotton Hood", text)
        self.assertIn("Prime's #2 Cotton Hood", text)
        self.assertIn("Recipe: sew_cotton_hood", text)

    def test_non_equipment_crafts_remain_stackable_and_anonymous(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(prime.id, "raw_cotton", 2)

        result = crafting.craft_recipe(
            database,
            prime.id,
            "spin_cotton_thread",
            station_key="loom",
            success_roll=0.0,
            skillup_roll=1.0,
        )
        self.assertTrue(result.success, result.message)
        self.assertEqual(
            owned_heritage_rows(database, prime.id, "cotton_thread", carried_only=True),
            [],
        )

    def test_special_discovery_edition_is_permanent_while_live_total_keeps_growing(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        SPECIAL_ITEM_KEYS.add("iron_ore")

        database.add_item(prime.id, "iron_ore", 17)
        rows = owned_heritage_rows(database, prime.id, "iron_ore", carried_only=True)
        fourth = rows[3]
        serial = str(fourth["serial"])
        self.assertEqual(int(fourth["discovery_ordinal"]), 4)
        self.assertEqual(special_found_total(database, "iron_ore"), 17)

        first_text = render_provenance(database, prime.id, "iron_ore", serial=serial)
        self.assertIn("Discovery: #4 of 17 ever found.", first_text)

        database.add_item(prime.id, "iron_ore", 1)
        second_text = render_provenance(database, prime.id, "iron_ore", serial=serial)
        self.assertIn("Discovery: #4 of 18 ever found.", second_text)

        self.assertTrue(database.consume_item(prime.id, "iron_ore", 5))
        self.assertEqual(special_found_total(database, "iron_ore"), 18)
        with database.connect() as db:
            retired = db.execute(
                "SELECT COUNT(*) AS n FROM item_heritage_instances WHERE item_key = 'iron_ore' AND holder_kind = 'retired'"
            ).fetchone()
        self.assertEqual(int(retired["n"]), 5)

    def test_trade_and_give_core_exchange_preserve_the_same_serial_and_history(self):
        temp, database, prime, morrow = self._database()
        self.addCleanup(temp.cleanup)
        self._craft_cotton_hood(database, prime.id)
        before = owned_heritage_rows(database, prime.id, "cotton_hood", carried_only=True)
        serial = str(before[0]["serial"])

        self.assertTrue(exchange_items(database, prime.id, {"cotton_hood": 1}, morrow.id, {}))

        self.assertEqual(
            owned_heritage_rows(database, prime.id, "cotton_hood", carried_only=True),
            [],
        )
        after = owned_heritage_rows(database, morrow.id, "cotton_hood", carried_only=True)
        self.assertEqual(len(after), 1)
        self.assertEqual(str(after[0]["serial"]), serial)

        text = render_provenance(database, morrow.id, "cotton_hood", serial=serial)
        self.assertIn("Prime's #1 Cotton Hood", text)
        self.assertIn("trade", text.lower())
        self.assertIn("Prime -> Morrow", text)
        self.assertEqual(audit_item_heritage(database), ())

    def test_special_drop_gets_edition_when_it_is_actually_looted(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        SPECIAL_ITEM_KEYS.add("iron_ore")
        ensure_item_heritage_schema(database)
        ensure_item_location_storage(database)

        with database.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO world_containers (
                    room_key, kind, name, source_key, source_name,
                    owner_character_id, created_at_epoch,
                    protection_expires_at_epoch, decay_at_epoch, currency_amount
                )
                VALUES ('test_room', 'corpse', 'Corpse of Briar Beast', 'briar_beast',
                        'Briar Beast', ?, 1, 0, 9999999999, 0)
                """,
                (prime.id,),
            )
            corpse_id = int(cursor.lastrowid)

        add_to_location(
            database,
            ItemLocation.container(corpse_id, prime.id),
            "iron_ore",
            1,
        )
        self.assertEqual(special_found_total(database, "iron_ore"), 0)

        self.assertTrue(
            transfer_item(
                database,
                ItemLocation.container(corpse_id, prime.id),
                ItemLocation.character(prime.id),
                "iron_ore",
                1,
            )
        )
        self.assertEqual(special_found_total(database, "iron_ore"), 1)
        row = owned_heritage_rows(database, prime.id, "iron_ore", carried_only=True)[0]
        self.assertEqual(int(row["discovery_ordinal"]), 1)
        self.assertIn("Briar Beast", str(row["origin_text"]))

    def test_legacy_special_copy_is_registered_without_inventing_exact_old_find_order(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        SPECIAL_ITEM_KEYS.add("iron_ore")
        ensure_item_heritage_schema(database)

        with database.connect() as db:
            db.execute(
                "INSERT INTO character_items (character_id, item_key, quantity) VALUES (?, 'iron_ore', 1)",
                (prime.id,),
            )

        created = ensure_special_inventory_item(database, prime.id, "iron_ore")
        self.assertEqual(len(created), 1)
        row = owned_heritage_rows(database, prime.id, "iron_ore", carried_only=True)[0]
        self.assertFalse(bool(row["discovery_exact"]))
        text = render_provenance(database, prime.id, "iron_ore")
        self.assertIn("predates exact discovery-order tracking", text)

    def test_item_inspection_stays_compact_but_surfaces_maker_mark(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        self._craft_cotton_hood(database, prime.id)
        session = DummySession(database, prime)

        asyncio.run(_show_item_detail(session, "Cotton Hood"))

        text = "".join(session.outputs)
        self.assertIn("Maker's mark: Prime's #1 Cotton Hood", text)
        self.assertIn("Use PROVENANCE <item> for the full heritage record.", text)

    def test_ordinary_found_items_do_not_get_instance_provenance(self):
        temp, database, prime, _ = self._database()
        self.addCleanup(temp.cleanup)
        database.add_item(prime.id, "greenleaf", 3)

        self.assertEqual(
            owned_heritage_rows(database, prime.id, "greenleaf", carried_only=True),
            [],
        )
        text = render_provenance(database, prime.id, "greenleaf")
        self.assertIn("no individual heritage record", text)


if __name__ == "__main__":
    unittest.main()
