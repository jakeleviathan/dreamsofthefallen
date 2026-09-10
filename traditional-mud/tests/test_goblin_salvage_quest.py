import asyncio
import unittest
from types import SimpleNamespace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.goblin_salvage_quest import (
    BRIN_COPPERHAND,
    GOBLIN_SALVAGE_COMPLETE_FLAG,
    GOBLIN_SALVAGE_CREDIT_FLAG,
    GOBLIN_SALVAGE_ITEM_KEY,
    GOBLIN_SALVAGE_QUEST,
    GOBLIN_SALVAGE_NPCS,
    NALLA_INKTHUMB,
    SKIV_WEIGHTWIRE,
    install_goblin_salvage_quest_content,
    install_goblin_salvage_quest_runtime,
)
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_TINKER_ROW_KEY,
    install_goblin_world,
)


class FakeDatabase:
    def __init__(self):
        self.quests = {}
        self.items = {}
        self.flags = set()

    def get_quest(self, character_id, quest_key):
        quest = self.quests.get((character_id, quest_key))
        return None if quest is None else dict(quest)

    def start_quest(self, character_id, quest_key, current_step):
        self.quests[(character_id, quest_key)] = {
            "status": "active",
            "current_step": current_step,
        }

    def advance_quest(self, character_id, quest_key, current_step):
        self.quests[(character_id, quest_key)]["current_step"] = current_step

    def complete_quest(self, character_id, quest_key):
        self.quests[(character_id, quest_key)]["status"] = "completed"
        self.quests[(character_id, quest_key)]["current_step"] = "complete"

    def add_item(self, character_id, item_key, quantity=1):
        key = (character_id, item_key)
        self.items[key] = self.items.get(key, 0) + quantity

    def item_quantity(self, character_id, item_key):
        return self.items.get((character_id, item_key), 0)

    def consume_item(self, character_id, item_key, quantity=1):
        key = (character_id, item_key)
        if self.items.get(key, 0) < quantity:
            return False
        self.items[key] -= quantity
        return True

    def grant_flag(self, character_id, flag_key):
        self.flags.add((character_id, flag_key))


class FakeWorldService:
    def __init__(self):
        self.legacy_rooms = dict(world.ROOMS_BY_KEY)
        self._scene_cache = {}


class FakeSession:
    def __init__(self):
        self.character = SimpleNamespace(id=77, race="goblin", current_room=GOBLIN_BRASSGUT_MARKET_KEY)
        self.database = FakeDatabase()
        self.outputs = []
        self.next_command = ""
        self.state = SimpleNamespace()
        self.passthrough_count = 0

    async def send_client_state(self):
        return None

    async def prompt(self, _text):
        return self.next_command

    async def send(self, text):
        self.outputs.append(text)

    async def playing_prompt(self):
        self.passthrough_count += 1


class GoblinSalvageQuestTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        install_goblin_world()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)

    def test_quest_is_short_safe_salvage_loop(self):
        self.assertEqual(
            [key for key, _ in GOBLIN_SALVAGE_QUEST.objective_steps],
            ["find_salvage", "weigh_salvage", "stamp_claim", "repair_salvage", "return_broker", "complete"],
        )
        text = " ".join(objective for _, objective in GOBLIN_SALVAGE_QUEST.objective_steps).lower()
        self.assertNotIn("attack", text)
        self.assertNotIn("kill", text)
        self.assertNotIn("defeat", text)

    def test_content_registration_adds_quest_item_and_civic_contacts(self):
        service = FakeWorldService()
        install_goblin_salvage_quest_content(service)
        install_goblin_salvage_quest_content(service)

        self.assertIs(quests.QUESTS_BY_KEY[GOBLIN_SALVAGE_QUEST.key], GOBLIN_SALVAGE_QUEST)
        self.assertEqual(crafting.ITEMS_BY_KEY[GOBLIN_SALVAGE_ITEM_KEY].category, "quest_item")
        self.assertEqual({npc.key for npc in GOBLIN_SALVAGE_NPCS}, {
            "goblin_skiv_weightwire",
            "goblin_nalla_inkthumb",
            "goblin_brin_copperhand",
        })
        self.assertIn(SKIV_WEIGHTWIRE.key, service.legacy_rooms[GOBLIN_SORTING_SPINE_KEY].npc_keys)
        self.assertIn(NALLA_INKTHUMB.key, service.legacy_rooms[GOBLIN_LEDGER_HALL_KEY].npc_keys)
        self.assertIn(BRIN_COPPERHAND.key, service.legacy_rooms[GOBLIN_TINKER_ROW_KEY].npc_keys)
        self.assertEqual(sum(1 for npc in world.NPCS if npc.key == SKIV_WEIGHTWIRE.key), 1)

    def test_complete_salvage_transaction_command_flow(self):
        service = FakeWorldService()
        install_goblin_salvage_quest_runtime(FakeSession, service)
        session = FakeSession()

        async def issue(command, room_key):
            session.next_command = command
            session.character.current_room = room_key
            await session.playing_prompt()

        asyncio.run(issue("talk ruskle", GOBLIN_BRASSGUT_MARKET_KEY))
        quest = session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)
        self.assertEqual(quest["current_step"], "find_salvage")

        asyncio.run(issue("search sorting bins", GOBLIN_SORTING_SPINE_KEY))
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 1)
        self.assertEqual(session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)["current_step"], "weigh_salvage")

        asyncio.run(issue("talk skiv", GOBLIN_SORTING_SPINE_KEY))
        self.assertEqual(session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)["current_step"], "stamp_claim")

        asyncio.run(issue("talk nalla", GOBLIN_LEDGER_HALL_KEY))
        self.assertEqual(session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)["current_step"], "repair_salvage")

        asyncio.run(issue("talk brin", GOBLIN_TINKER_ROW_KEY))
        self.assertEqual(session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)["current_step"], "return_broker")

        asyncio.run(issue("talk ruskle", GOBLIN_BRASSGUT_MARKET_KEY))
        finished = session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)
        self.assertEqual(finished["status"], "completed")
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 0)
        self.assertIn((77, GOBLIN_SALVAGE_COMPLETE_FLAG), session.database.flags)
        self.assertIn((77, GOBLIN_SALVAGE_CREDIT_FLAG), session.database.flags)
        self.assertTrue(any("Quest complete: From Scrap to Claim" in output for output in session.outputs))


if __name__ == "__main__":
    unittest.main()
