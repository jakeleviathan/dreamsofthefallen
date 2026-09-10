import asyncio
import unittest
from types import SimpleNamespace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.goblin_clan_followups import (
    COPPERCAP_CALIBRATION_AMPOULE,
    GOBLIN_BEFORE_PRICE_MOVES,
    GOBLIN_DRY_WAY_HOME,
    GOBLIN_ONE_CLEAN_MEASURE,
    TINLEDGER_MARKET_SLIP,
    TRUSTED_SIGNAL_THRESHOLD,
    _ask_jex_routes,
    _ask_snik_claims,
    _ask_talla_reagents,
    _handle_followup_choice,
    _reconcile_followups,
    _talk_hadrik_followup,
    _talk_jex_followup,
    _talk_pella_followup,
    _talk_snik_followup,
    _talk_talla_followup,
    clan_relationship_label,
    install_goblin_clan_followup_content,
)
from mud.goblin_clans import (
    FLOODPICK_COPPERCAP,
    FLOODPICK_MIREHOOK,
    FLOODPICK_TINLEDGER,
    GOBLIN_WEIGHT_OF_A_MAP,
    clan_signal_counts,
    clan_signal_flag,
    install_goblin_clan_content,
)
from mud.goblin_return_loop import GOBLIN_BOTTLEWIRE_RETURN_KEY, GOBLIN_RETURN_LOOP_DISCOVERED_FLAG
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
        self.character = SimpleNamespace(id=909, name="Nib", race="goblin", current_room=GOBLIN_BRASSGUT_MARKET_KEY)
        self.database = FakeDatabase()
        self.outputs = []
        self.database.start_quest(909, GOBLIN_WEIGHT_OF_A_MAP.key, "complete")
        self.database.complete_quest(909, GOBLIN_WEIGHT_OF_A_MAP.key)

    async def send(self, text):
        self.outputs.append(text)


class GoblinClanFollowupTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_goblin_world()
        install_goblin_clan_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

    def test_second_wave_registers_three_nonexclusive_quests_and_persistent_cargo(self):
        install_goblin_clan_followup_content()
        for quest in (GOBLIN_DRY_WAY_HOME, GOBLIN_ONE_CLEAN_MEASURE, GOBLIN_BEFORE_PRICE_MOVES):
            self.assertIn(quest.key, quests.QUESTS_BY_KEY)
        self.assertIn(COPPERCAP_CALIBRATION_AMPOULE.key, crafting.ITEMS_BY_KEY)
        self.assertIn(TINLEDGER_MARKET_SLIP.key, crafting.ITEMS_BY_KEY)

    def test_mirehook_followup_can_choose_tinledger_without_locking_mirehook_out(self):
        install_goblin_clan_followup_content()
        session = FakeSession()
        self.assertTrue(asyncio.run(_talk_jex_followup(session)))
        session.character.current_room = GOBLIN_BOTTLEWIRE_RETURN_KEY
        self.assertTrue(asyncio.run(_handle_followup_choice(session, "examine return markers")))
        session.character.current_room = GOBLIN_LEDGER_HALL_KEY
        self.assertTrue(asyncio.run(_handle_followup_choice(session, "register return route")))
        self.assertEqual(session.database.get_quest(909, GOBLIN_DRY_WAY_HOME.key)["status"], "completed")
        counts = clan_signal_counts(session.database.list_flags(909))
        self.assertEqual(counts[FLOODPICK_TINLEDGER], 1)
        self.assertEqual(counts[FLOODPICK_MIREHOOK], 0)

        # Choosing Tinledger does not prevent a later Mirehook signal.
        session.database.grant_flag(909, clan_signal_flag(FLOODPICK_MIREHOOK, "later_help"))
        counts = clan_signal_counts(session.database.list_flags(909))
        self.assertEqual(counts[FLOODPICK_TINLEDGER], 1)
        self.assertEqual(counts[FLOODPICK_MIREHOOK], 1)

    def test_coppercap_followup_can_return_or_publicly_leave_standard(self):
        install_goblin_clan_followup_content()
        session = FakeSession()
        session.character.current_room = GOBLIN_TINKER_ROW_KEY
        self.assertTrue(asyncio.run(_talk_talla_followup(session)))
        self.assertEqual(session.database.item_quantity(909, COPPERCAP_CALIBRATION_AMPOULE.key), 1)

        session.character.current_room = GOBLIN_APOTHECARY_BLIND_KEY
        self.assertTrue(asyncio.run(_talk_pella_followup(session)))
        self.assertTrue(asyncio.run(_handle_followup_choice(session, "return measure to talla")))
        session.character.current_room = GOBLIN_TINKER_ROW_KEY
        self.assertTrue(asyncio.run(_handle_followup_choice(session, "return measure to talla")))
        self.assertEqual(session.database.item_quantity(909, COPPERCAP_CALIBRATION_AMPOULE.key), 0)
        self.assertEqual(clan_signal_counts(session.database.list_flags(909))[FLOODPICK_COPPERCAP], 1)

        # A different character could choose the public-bench outcome instead.
        public = FakeSession()
        public.character.current_room = GOBLIN_TINKER_ROW_KEY
        asyncio.run(_talk_talla_followup(public))
        public.character.current_room = GOBLIN_APOTHECARY_BLIND_KEY
        asyncio.run(_talk_pella_followup(public))
        self.assertTrue(asyncio.run(_handle_followup_choice(public, "leave measure with pella")))
        self.assertIn("goblin_public_calibration_standard", public.database.list_flags(909))
        self.assertEqual(clan_signal_counts(public.database.list_flags(909))[FLOODPICK_MIREHOOK], 1)

    def test_tinledger_followup_can_prioritize_trade_or_local_supply(self):
        install_goblin_clan_followup_content()
        session = FakeSession()
        session.character.current_room = GOBLIN_LEDGER_HALL_KEY
        self.assertTrue(asyncio.run(_talk_snik_followup(session)))
        self.assertEqual(session.database.item_quantity(909, TINLEDGER_MARKET_SLIP.key), 1)
        session.character.current_room = GOBLIN_BRASSGUT_MARKET_KEY
        self.assertTrue(asyncio.run(_talk_hadrik_followup(session)))
        self.assertTrue(asyncio.run(_handle_followup_choice(session, "deliver market slip")))
        self.assertEqual(clan_signal_counts(session.database.list_flags(909))[FLOODPICK_TINLEDGER], 1)

        local = FakeSession()
        local.character.current_room = GOBLIN_LEDGER_HALL_KEY
        asyncio.run(_talk_snik_followup(local))
        local.character.current_room = GOBLIN_TINKER_ROW_KEY
        self.assertTrue(asyncio.run(_handle_followup_choice(local, "show market slip to talla")))
        self.assertEqual(clan_signal_counts(local.database.list_flags(909))[FLOODPICK_COPPERCAP], 1)

    def test_two_signals_unlock_information_only_trusted_services(self):
        install_goblin_clan_followup_content()
        session = FakeSession()
        for clan_key in (FLOODPICK_MIREHOOK, FLOODPICK_COPPERCAP, FLOODPICK_TINLEDGER):
            for index in range(TRUSTED_SIGNAL_THRESHOLD):
                session.database.grant_flag(909, clan_signal_flag(clan_key, f"test_{index}"))
        session.database.grant_flag(909, GOBLIN_RETURN_LOOP_DISCOVERED_FLAG)

        session.character.current_room = GOBLIN_BRASSGUT_MARKET_KEY
        self.assertTrue(asyncio.run(_ask_jex_routes(session)))
        session.character.current_room = GOBLIN_TINKER_ROW_KEY
        self.assertTrue(asyncio.run(_ask_talla_reagents(session)))
        session.character.current_room = GOBLIN_LEDGER_HALL_KEY
        self.assertTrue(asyncio.run(_ask_snik_claims(session)))

        joined = "\n".join(session.outputs).lower()
        self.assertIn("mirehook route briefing", joined)
        self.assertIn("bogmint: herbalism 6", joined)
        self.assertIn("tinledger claim forecast", joined)
        self.assertEqual(clan_relationship_label(0), "Uncommitted")
        self.assertEqual(clan_relationship_label(1), "Recognized")
        self.assertEqual(clan_relationship_label(2), "Trusted")

    def test_followup_cargo_reconciliation_is_idempotent(self):
        install_goblin_clan_followup_content()
        session = FakeSession()
        session.database.start_quest(909, GOBLIN_ONE_CLEAN_MEASURE.key, "deliver_measure")
        session.database.start_quest(909, GOBLIN_BEFORE_PRICE_MOVES.key, "choose_market_reader")
        _reconcile_followups(session)
        _reconcile_followups(session)
        self.assertEqual(session.database.item_quantity(909, COPPERCAP_CALIBRATION_AMPOULE.key), 1)
        self.assertEqual(session.database.item_quantity(909, TINLEDGER_MARKET_SLIP.key), 1)


if __name__ == "__main__":
    unittest.main()
