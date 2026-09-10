from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.goblin_rattlefen_opening import (
    BETTER_THAN_IT_WAS,
    CLAIM_TAG_KEY,
    EARTH_TOKEN_KEY,
    GIFT_HOUSING_KEY,
    HUMAN_TOOL_ROLL_KEY,
    MARA_VALE,
    PERSONAL_STAMP_KEY,
    RATTLEFEN_CLAIM_CHECKED_FLAG,
    RATTLEFEN_DISPUTE_EXPIRED_FLAG,
    RATTLEFEN_DISPUTE_NEGOTIATE_FLAG,
    RATTLEFEN_DISPUTE_RETURN_FLAG,
    RATTLEFEN_MARK_SPIRAL_FLAG,
    RATTLEFEN_OPENING_COMPLETE_FLAG,
    RATTLEFEN_QUESTS,
    RATTLEFEN_TOKEN_KEPT_FLAG,
    RATTLELIGHT_KEY,
    SELLA_REEDMARK,
    SOMEBODY_ELSES_MARK,
    SPRING_CAGE_KEY,
    THING_HUMANS_BUY,
    THREE_BELLS,
    WHATS_IT_WORTH,
    YOUR_MARK,
    _handle_opening_action,
    _talk_brin,
    _talk_mara,
    _talk_ruskle,
    _talk_sella,
    _talk_vikka,
    install_rattlefen_opening_content,
    rattlefen_augmentations,
    reconcile_rattlefen_opening,
)
from mud.goblin_salvage_quest import (
    GOBLIN_SALVAGE_COMPLETE_FLAG,
    GOBLIN_SALVAGE_CREDIT_FLAG,
    GOBLIN_SALVAGE_QUEST,
    install_goblin_salvage_quest_content,
)
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_START_ROOM_KEY,
    GOBLIN_TINKER_ROW_KEY,
    install_goblin_world,
)
from mud.stats import CharacterStats


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


class RattlefenOpeningTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        self.item_tuple = crafting.ITEMS
        self.item_map = dict(crafting.ITEMS_BY_KEY)
        install_goblin_world()
        install_goblin_salvage_quest_content()
        install_rattlefen_opening_content()

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
        crafting.ITEMS = self.item_tuple
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.item_map)

    def _session(self, name: str = "Rattle"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "rattlefen.db")
        account = database.create_account(f"acct_{name.lower()}", "hash")
        character = database.create_character(
            account.id,
            name,
            "goblin",
            "brute",
            stats=CharacterStats(),
        )
        database.set_character_room(character.id, GOBLIN_START_ROOM_KEY)
        character = database.get_character_by_name(name)
        return temp, database, FakeSession(database, character)

    def test_content_registers_six_part_opening_and_rattlefen_social_features(self):
        self.assertEqual(
            [quest.name for quest in RATTLEFEN_QUESTS],
            [
                "Three Bells",
                "What's It Worth?",
                "Somebody Else's Mark",
                "Better Than It Was",
                "The Thing Humans Buy",
                "Your Mark",
            ],
        )
        self.assertIn(SELLA_REEDMARK.key, legacy_world.ROOMS_BY_KEY[GOBLIN_LEDGER_HALL_KEY].npc_keys)
        self.assertIn(MARA_VALE.key, legacy_world.ROOMS_BY_KEY[GOBLIN_BRASSGUT_MARKET_KEY].npc_keys)
        augmentations = rattlefen_augmentations()
        sorting_features = {feature.key for feature in augmentations[GOBLIN_SORTING_SPINE_KEY].features}
        start_features = {feature.key for feature in augmentations[GOBLIN_START_ROOM_KEY].features}
        self.assertIn("rattlefen_fresh_wreck", sorting_features)
        self.assertIn("rattlefen_salvage_bell", sorting_features)
        self.assertIn("rattlefen_mark_board", start_features)
        self.assertIn("Rattlefen", augmentations[GOBLIN_START_ROOM_KEY].description_layers[0].text)

    def test_fresh_goblin_gets_one_tag_and_legacy_goblin_is_not_rewound(self):
        temp, database, session = self._session("Fresh")
        self.addCleanup(temp.cleanup)
        self.assertTrue(reconcile_rattlefen_opening(session))
        state = database.get_quest(session.character.id, THREE_BELLS.key)
        self.assertEqual(state["current_step"], "inspect_wreck")
        self.assertEqual(database.item_quantity(session.character.id, CLAIM_TAG_KEY), 1)
        self.assertIsNone(database.get_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key))

        temp2, database2, legacy = self._session("Legacy")
        self.addCleanup(temp2.cleanup)
        database2.start_quest(legacy.character.id, GOBLIN_SALVAGE_QUEST.key, "find_salvage")
        self.assertFalse(reconcile_rattlefen_opening(legacy))
        self.assertIsNone(database2.get_quest(legacy.character.id, THREE_BELLS.key))

    def test_three_bells_forces_one_attention_based_claim(self):
        temp, database, session = self._session("Bell")
        self.addCleanup(temp.cleanup)
        reconcile_rattlefen_opening(session)
        move(session, GOBLIN_SORTING_SPINE_KEY)

        self.assertTrue(asyncio.run(_handle_opening_action(session, "examine fresh wreck")))
        self.assertEqual(database.get_quest(session.character.id, THREE_BELLS.key)["current_step"], "choose_salvage")
        self.assertTrue(asyncio.run(_handle_opening_action(session, "claim spring")))
        self.assertEqual(database.item_quantity(session.character.id, CLAIM_TAG_KEY), 0)
        self.assertEqual(database.item_quantity(session.character.id, SPRING_CAGE_KEY), 1)
        self.assertEqual(database.get_quest(session.character.id, THREE_BELLS.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, WHATS_IT_WORTH.key)["current_step"], "seek_broker")

    def test_market_can_reject_counter_and_ownership_has_three_valid_resolutions(self):
        temp, database, session = self._session("Bargain")
        self.addCleanup(temp.cleanup)
        reconcile_rattlefen_opening(session)
        move(session, GOBLIN_SORTING_SPINE_KEY)
        asyncio.run(_handle_opening_action(session, "examine fresh wreck"))
        asyncio.run(_handle_opening_action(session, "claim spring"))
        move(session, GOBLIN_BRASSGUT_MARKET_KEY)
        self.assertTrue(asyncio.run(_talk_ruskle(session)))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "counter high")))
        self.assertEqual(database.get_quest(session.character.id, WHATS_IT_WORTH.key)["current_step"], "bargain")
        self.assertTrue(asyncio.run(_handle_opening_action(session, "counter fair")))
        self.assertEqual(database.get_quest(session.character.id, SOMEBODY_ELSES_MARK.key)["current_step"], "meet_owner")
        self.assertIn("no.", "".join(session.outputs).lower())

        move(session, GOBLIN_LEDGER_HALL_KEY)
        self.assertTrue(asyncio.run(_talk_sella(session)))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "prove claim expired")))
        self.assertNotIn(RATTLEFEN_DISPUTE_EXPIRED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "check old claim")))
        self.assertIn(RATTLEFEN_CLAIM_CHECKED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "prove claim expired")))
        self.assertIn(RATTLEFEN_DISPUTE_EXPIRED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, BETTER_THAN_IT_WAS.key)["current_step"], "meet_brin")

    def test_returning_old_claim_is_not_punished_and_still_feeds_repurpose(self):
        temp, database, session = self._session("Return")
        self.addCleanup(temp.cleanup)
        reconcile_rattlefen_opening(session)
        move(session, GOBLIN_SORTING_SPINE_KEY)
        asyncio.run(_handle_opening_action(session, "examine fresh wreck"))
        asyncio.run(_handle_opening_action(session, "claim spring"))
        move(session, GOBLIN_BRASSGUT_MARKET_KEY)
        asyncio.run(_talk_ruskle(session))
        asyncio.run(_handle_opening_action(session, "walk away"))
        move(session, GOBLIN_LEDGER_HALL_KEY)
        asyncio.run(_talk_sella(session))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "return salvage")))
        self.assertIn(RATTLEFEN_DISPUTE_RETURN_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.item_quantity(session.character.id, SPRING_CAGE_KEY), 0)
        self.assertEqual(database.item_quantity(session.character.id, GIFT_HOUSING_KEY), 1)

        move(session, GOBLIN_TINKER_ROW_KEY)
        asyncio.run(_talk_brin(session))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "repurpose salvage")))
        self.assertEqual(database.item_quantity(session.character.id, GIFT_HOUSING_KEY), 0)
        self.assertEqual(database.item_quantity(session.character.id, RATTLELIGHT_KEY), 1)
        self.assertEqual(database.item_quantity(session.character.id, EARTH_TOKEN_KEY), 1)
        self.assertEqual(database.get_quest(session.character.id, THING_HUMANS_BUY.key)["current_step"], "show_token")

    def test_full_arc_can_keep_human_relic_then_register_mark_and_unlock_old_progression(self):
        temp, database, session = self._session("Mark")
        self.addCleanup(temp.cleanup)
        reconcile_rattlefen_opening(session)
        move(session, GOBLIN_SORTING_SPINE_KEY)
        asyncio.run(_handle_opening_action(session, "examine fresh wreck"))
        asyncio.run(_handle_opening_action(session, "claim spring"))
        move(session, GOBLIN_BRASSGUT_MARKET_KEY)
        asyncio.run(_talk_ruskle(session))
        asyncio.run(_handle_opening_action(session, "accept offer"))
        move(session, GOBLIN_LEDGER_HALL_KEY)
        asyncio.run(_talk_sella(session))
        asyncio.run(_handle_opening_action(session, "negotiate claim"))
        self.assertIn(RATTLEFEN_DISPUTE_NEGOTIATE_FLAG, database.list_flags(session.character.id))
        move(session, GOBLIN_TINKER_ROW_KEY)
        asyncio.run(_talk_brin(session))
        asyncio.run(_handle_opening_action(session, "repurpose salvage"))
        move(session, GOBLIN_BRASSGUT_MARKET_KEY)
        asyncio.run(_talk_mara(session))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "keep token")))
        self.assertIn(RATTLEFEN_TOKEN_KEPT_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.item_quantity(session.character.id, EARTH_TOKEN_KEY), 1)
        self.assertEqual(database.item_quantity(session.character.id, HUMAN_TOOL_ROLL_KEY), 0)
        move(session, GOBLIN_START_ROOM_KEY)
        asyncio.run(_talk_vikka(session))
        self.assertTrue(asyncio.run(_handle_opening_action(session, "mark spiral")))

        flags = database.list_flags(session.character.id)
        self.assertIn(RATTLEFEN_OPENING_COMPLETE_FLAG, flags)
        self.assertIn(RATTLEFEN_MARK_SPIRAL_FLAG, flags)
        self.assertIn(GOBLIN_SALVAGE_COMPLETE_FLAG, flags)
        self.assertIn(GOBLIN_SALVAGE_CREDIT_FLAG, flags)
        self.assertEqual(database.item_quantity(session.character.id, PERSONAL_STAMP_KEY), 1)
        self.assertEqual(database.get_quest(session.character.id, YOUR_MARK.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key)["status"], "completed")
        output = "".join(session.outputs).lower()
        self.assertIn("bargain gate", output)
        self.assertIn("nobody rings a heroic bell", output)


if __name__ == "__main__":
    unittest.main()
