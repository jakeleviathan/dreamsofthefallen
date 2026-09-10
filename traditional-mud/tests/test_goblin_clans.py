import asyncio
import unittest
from types import SimpleNamespace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.goblin_clans import (
    COPPERCAP_FORMULA_PACKET,
    FLOODPICK_COPPERCAP,
    FLOODPICK_MIREHOOK,
    FLOODPICK_TINLEDGER,
    GOBLIN_CLOSED_FORMULA,
    GOBLIN_FRESH_CLAIMS,
    GOBLIN_WEIGHT_OF_A_MAP,
    HADRIK_COILPRESS,
    JEX_MIREHOOK,
    SNIK_TINLEDGER,
    TALLA_COPPERCAP,
    TINLEDGER_ROUTE_REPORT,
    _handle_clan_choice,
    _reconcile_clan_quests,
    _talk_hadrik,
    _talk_jex,
    _talk_pella_for_formula,
    _talk_snik,
    _talk_talla,
    clan_signal_counts,
    install_goblin_clan_content,
)
from mud.goblin_deep_mire import GOBLIN_SOURREED_TERRACE_KEY
from mud.goblin_outer_route import GOBLIN_OUTER_ROUTE_COMPLETE_FLAG
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_TINKER_ROW_KEY,
    install_goblin_world,
)
from mud.goblin_swamp import GOBLIN_APOTHECARY_BLIND_KEY


class FakeDatabase:
    def __init__(self):
        self.items = {}
        self.flags = set()
        self.quests = {}

    def item_quantity(self, character_id, item_key):
        return self.items.get((character_id, item_key), 0)

    def add_item(self, character_id, item_key, quantity=1):
        key = (character_id, item_key)
        self.items[key] = self.items.get(key, 0) + quantity

    def consume_item(self, character_id, item_key, quantity=1):
        key = (character_id, item_key)
        current = self.items.get(key, 0)
        if current < quantity:
            return False
        self.items[key] = current - quantity
        return True

    def grant_flag(self, character_id, flag_key):
        self.flags.add((character_id, flag_key))

    def list_flags(self, character_id):
        return frozenset(flag for owner, flag in self.flags if owner == character_id)

    def get_quest(self, character_id, quest_key):
        value = self.quests.get((character_id, quest_key))
        return None if value is None else dict(value)

    def start_quest(self, character_id, quest_key, current_step):
        self.quests.setdefault((character_id, quest_key), {"status": "active", "current_step": current_step})

    def advance_quest(self, character_id, quest_key, current_step):
        value = self.quests[(character_id, quest_key)]
        if value["status"] == "active":
            value["current_step"] = current_step

    def complete_quest(self, character_id, quest_key):
        value = self.quests[(character_id, quest_key)]
        value["status"] = "completed"
        value["current_step"] = "complete"


class FakeSession:
    def __init__(self):
        self.character = SimpleNamespace(id=808, name="Nib", race="goblin", current_room=GOBLIN_BRASSGUT_MARKET_KEY)
        self.database = FakeDatabase()
        self.outputs = []
        self.database.grant_flag(808, GOBLIN_OUTER_ROUTE_COMPLETE_FLAG)

    async def send(self, text):
        self.outputs.append(text)


class GoblinClanTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_goblin_world()

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
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

    def test_clan_npcs_and_quests_register_in_existing_city(self):
        install_goblin_clan_content()
        market = world.ROOMS_BY_KEY[GOBLIN_BRASSGUT_MARKET_KEY]
        tinker = world.ROOMS_BY_KEY[GOBLIN_TINKER_ROW_KEY]
        ledger = world.ROOMS_BY_KEY[GOBLIN_LEDGER_HALL_KEY]

        self.assertIn(JEX_MIREHOOK.key, market.npc_keys)
        self.assertIn(HADRIK_COILPRESS.key, market.npc_keys)
        self.assertIn(TALLA_COPPERCAP.key, tinker.npc_keys)
        self.assertIn(SNIK_TINLEDGER.key, ledger.npc_keys)
        for quest in (GOBLIN_FRESH_CLAIMS, GOBLIN_CLOSED_FORMULA, GOBLIN_WEIGHT_OF_A_MAP):
            self.assertIn(quest.key, quests.QUESTS_BY_KEY)

    def test_three_quest_chain_can_signal_three_different_groups_without_locking(self):
        install_goblin_clan_content()
        session = FakeSession()

        # Fresh Claims -> Coppercap.
        self.assertTrue(asyncio.run(_talk_jex(session)))
        session.character.current_room = GOBLIN_SOURREED_TERRACE_KEY
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "examine claim stakes")))
        session.character.current_room = GOBLIN_TINKER_ROW_KEY
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "report coppercap")))
        self.assertEqual(session.database.get_quest(808, GOBLIN_FRESH_CLAIMS.key)["status"], "completed")

        # Closed Formula -> share it, signaling Mirehook-style open fieldcraft.
        self.assertTrue(asyncio.run(_talk_talla(session)))
        self.assertEqual(session.database.item_quantity(808, COPPERCAP_FORMULA_PACKET.key), 1)
        session.character.current_room = GOBLIN_APOTHECARY_BLIND_KEY
        self.assertTrue(asyncio.run(_talk_pella_for_formula(session)))
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "share formula with pella")))
        self.assertEqual(session.database.item_quantity(808, COPPERCAP_FORMULA_PACKET.key), 0)
        self.assertEqual(session.database.get_quest(808, GOBLIN_CLOSED_FORMULA.key)["status"], "completed")

        # Weight of a Map -> complete the Tinledger sale to the Dwarf.
        session.character.current_room = GOBLIN_LEDGER_HALL_KEY
        self.assertTrue(asyncio.run(_talk_snik(session)))
        self.assertEqual(session.database.item_quantity(808, TINLEDGER_ROUTE_REPORT.key), 1)
        session.character.current_room = GOBLIN_BRASSGUT_MARKET_KEY
        self.assertTrue(asyncio.run(_talk_hadrik(session)))
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "deliver report")))
        self.assertEqual(session.database.item_quantity(808, TINLEDGER_ROUTE_REPORT.key), 0)
        self.assertEqual(session.database.get_quest(808, GOBLIN_WEIGHT_OF_A_MAP.key)["status"], "completed")

        counts = clan_signal_counts(session.database.list_flags(808))
        self.assertEqual(counts[FLOODPICK_COPPERCAP], 1)
        self.assertEqual(counts[FLOODPICK_MIREHOOK], 1)
        self.assertEqual(counts[FLOODPICK_TINLEDGER], 1)

    def test_formula_can_be_kept_sealed_for_coppercap_instead(self):
        install_goblin_clan_content()
        session = FakeSession()
        session.database.start_quest(808, GOBLIN_FRESH_CLAIMS.key, "complete")
        session.database.complete_quest(808, GOBLIN_FRESH_CLAIMS.key)
        session.character.current_room = GOBLIN_TINKER_ROW_KEY
        asyncio.run(_talk_talla(session))
        session.character.current_room = GOBLIN_APOTHECARY_BLIND_KEY
        asyncio.run(_talk_pella_for_formula(session))
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "keep formula sealed")))
        counts = clan_signal_counts(session.database.list_flags(808))
        self.assertEqual(counts[FLOODPICK_COPPERCAP], 1)
        self.assertEqual(counts[FLOODPICK_MIREHOOK], 0)

    def test_route_report_can_be_made_public_instead_of_sold(self):
        install_goblin_clan_content()
        session = FakeSession()
        session.database.start_quest(808, GOBLIN_CLOSED_FORMULA.key, "complete")
        session.database.complete_quest(808, GOBLIN_CLOSED_FORMULA.key)
        session.character.current_room = GOBLIN_LEDGER_HALL_KEY
        asyncio.run(_talk_snik(session))
        self.assertTrue(asyncio.run(_handle_clan_choice(session, "file report publicly")))
        counts = clan_signal_counts(session.database.list_flags(808))
        self.assertEqual(counts[FLOODPICK_MIREHOOK], 1)
        self.assertEqual(counts[FLOODPICK_TINLEDGER], 0)

    def test_reconciliation_restores_unique_delivery_items_after_interrupted_save(self):
        install_goblin_clan_content()
        session = FakeSession()
        session.database.start_quest(808, GOBLIN_CLOSED_FORMULA.key, "deliver_formula")
        session.database.start_quest(808, GOBLIN_WEIGHT_OF_A_MAP.key, "choose_delivery")
        self.assertEqual(session.database.item_quantity(808, COPPERCAP_FORMULA_PACKET.key), 0)
        self.assertEqual(session.database.item_quantity(808, TINLEDGER_ROUTE_REPORT.key), 0)

        _reconcile_clan_quests(session)
        self.assertEqual(session.database.item_quantity(808, COPPERCAP_FORMULA_PACKET.key), 1)
        self.assertEqual(session.database.item_quantity(808, TINLEDGER_ROUTE_REPORT.key), 1)

        # Reconciliation is idempotent rather than duplicating cargo every login.
        _reconcile_clan_quests(session)
        self.assertEqual(session.database.item_quantity(808, COPPERCAP_FORMULA_PACKET.key), 1)
        self.assertEqual(session.database.item_quantity(808, TINLEDGER_ROUTE_REPORT.key), 1)


if __name__ == "__main__":
    unittest.main()
