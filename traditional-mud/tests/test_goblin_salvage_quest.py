import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.goblin_salvage_quest import (
    BRIN_COPPERHAND,
    GOBLIN_SALVAGE_COMPLETE_FLAG,
    GOBLIN_SALVAGE_CREDIT_FLAG,
    GOBLIN_SALVAGE_ITEM_KEY,
    GOBLIN_SALVAGE_QUEST,
    GOBLIN_SALVAGE_NPCS,
    GOBLIN_SORTING_RUMMAGE,
    NIGHT_SHIFT_LAYERS,
    NALLA_INKTHUMB,
    SKIV_WEIGHTWIRE,
    _reconcile_persistent_state,
    install_goblin_salvage_quest_content,
    install_goblin_salvage_quest_runtime,
)
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_TINKER_ROW_KEY,
    goblin_room_augmentations,
    install_goblin_world,
)
from mud.scavenging import RUMMAGE_NODES
from mud.stats import CharacterStats


class FakeDatabase:
    def __init__(self):
        self.quests = {}
        self.items = {}
        self.flags = set()

    def get_quest(self, character_id, quest_key):
        quest = self.quests.get((character_id, quest_key))
        return None if quest is None else dict(quest)

    def start_quest(self, character_id, quest_key, current_step):
        self.quests.setdefault(
            (character_id, quest_key),
            {"status": "active", "current_step": current_step},
        )

    def advance_quest(self, character_id, quest_key, current_step):
        quest = self.quests[(character_id, quest_key)]
        if quest["status"] == "active":
            quest["current_step"] = current_step

    def complete_quest(self, character_id, quest_key):
        quest = self.quests[(character_id, quest_key)]
        quest["status"] = "completed"
        quest["current_step"] = "complete"

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

    def list_flags(self, character_id):
        return frozenset(flag for cid, flag in self.flags if cid == character_id)


class FakeWorldService:
    def __init__(self):
        self.legacy_rooms = dict(world.ROOMS_BY_KEY)
        self.augmentations = goblin_room_augmentations()
        self._scene_cache = {}


class FakeSession:
    def __init__(self):
        self.character = SimpleNamespace(id=77, race="goblin", current_room=GOBLIN_BRASSGUT_MARKET_KEY)
        self.database = FakeDatabase()
        self.outputs = []
        self.next_command = ""
        self.state = SimpleNamespace()
        self.passthrough_count = 0
        self.enter_count = 0

    async def send_client_state(self):
        return None

    async def prompt(self, _text):
        return self.next_command

    async def send(self, text):
        self.outputs.append(text)

    async def enter_character(self):
        self.enter_count += 1

    async def playing_prompt(self):
        self.passthrough_count += 1


def runtime_session_class():
    class RuntimeSession(FakeSession):
        pass

    return RuntimeSession


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

    def test_title_changes_without_breaking_saved_quest_key(self):
        self.assertEqual(GOBLIN_SALVAGE_QUEST.name, "A Piece Worth Keeping")
        self.assertEqual(GOBLIN_SALVAGE_QUEST.key, "goblin_from_scrap_to_claim")

    def test_quest_is_short_safe_salvage_loop(self):
        self.assertEqual(
            [key for key, _ in GOBLIN_SALVAGE_QUEST.objective_steps],
            ["find_salvage", "weigh_salvage", "stamp_claim", "repair_salvage", "return_broker", "complete"],
        )
        text = " ".join(objective for _, objective in GOBLIN_SALVAGE_QUEST.objective_steps).lower()
        self.assertNotIn("attack", text)
        self.assertNotIn("kill", text)
        self.assertNotIn("defeat", text)

    def test_content_registration_adds_quest_item_contacts_and_rummage_node(self):
        service = FakeWorldService()
        install_goblin_salvage_quest_content(service)
        install_goblin_salvage_quest_content(service)

        self.assertIs(quests.QUESTS_BY_KEY[GOBLIN_SALVAGE_QUEST.key], GOBLIN_SALVAGE_QUEST)
        self.assertEqual(crafting.ITEMS_BY_KEY[GOBLIN_SALVAGE_ITEM_KEY].category, "quest_item")
        self.assertIs(RUMMAGE_NODES.get(GOBLIN_SORTING_RUMMAGE.key), GOBLIN_SORTING_RUMMAGE)
        self.assertEqual({npc.key for npc in GOBLIN_SALVAGE_NPCS}, {
            "goblin_skiv_weightwire",
            "goblin_nalla_inkthumb",
            "goblin_brin_copperhand",
        })
        self.assertIn(SKIV_WEIGHTWIRE.key, service.legacy_rooms[GOBLIN_SORTING_SPINE_KEY].npc_keys)
        self.assertIn(NALLA_INKTHUMB.key, service.legacy_rooms[GOBLIN_LEDGER_HALL_KEY].npc_keys)
        self.assertIn(BRIN_COPPERHAND.key, service.legacy_rooms[GOBLIN_TINKER_ROW_KEY].npc_keys)
        self.assertEqual(sum(1 for npc in world.NPCS if npc.key == SKIV_WEIGHTWIRE.key), 1)

    def test_critical_starter_services_have_explicit_night_shift_layers(self):
        service = FakeWorldService()
        install_goblin_salvage_quest_content(service)

        self.assertEqual(
            set(NIGHT_SHIFT_LAYERS),
            {
                GOBLIN_BRASSGUT_MARKET_KEY,
                GOBLIN_SORTING_SPINE_KEY,
                GOBLIN_LEDGER_HALL_KEY,
                GOBLIN_TINKER_ROW_KEY,
            },
        )
        for room_key, expected in NIGHT_SHIFT_LAYERS.items():
            installed = [
                layer
                for layer in service.augmentations[room_key].description_layers
                if layer.key == expected.key
            ]
            self.assertEqual(len(installed), 1)
            self.assertEqual(installed[0].condition.time_buckets, ("night",))

    def test_complete_salvage_transaction_command_flow_and_duplicate_guard(self):
        service = FakeWorldService()
        RuntimeSession = runtime_session_class()
        install_goblin_salvage_quest_runtime(RuntimeSession, service)
        session = RuntimeSession()

        async def issue(command, room_key):
            session.next_command = command
            session.character.current_room = room_key
            await session.playing_prompt()

        asyncio.run(issue("talk ruskle", GOBLIN_BRASSGUT_MARKET_KEY))
        quest = session.database.get_quest(77, GOBLIN_SALVAGE_QUEST.key)
        self.assertEqual(quest["current_step"], "find_salvage")

        asyncio.run(issue("rummage sorting bins", GOBLIN_SORTING_SPINE_KEY))
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
        expected_flags = {
            (77, GOBLIN_SALVAGE_COMPLETE_FLAG),
            (77, GOBLIN_SALVAGE_CREDIT_FLAG),
        }
        self.assertTrue(expected_flags.issubset(session.database.flags))
        flag_snapshot = set(session.database.flags)

        asyncio.run(issue("talk ruskle", GOBLIN_BRASSGUT_MARKET_KEY))
        self.assertEqual(session.database.flags, flag_snapshot)
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 0)
        self.assertEqual(
            sum("Quest complete: A Piece Worth Keeping" in output for output in session.outputs),
            1,
        )

    def test_reconciliation_restores_unique_cargo_and_normalizes_duplicates(self):
        session = FakeSession()
        session.database.start_quest(77, GOBLIN_SALVAGE_QUEST.key, "return_broker")
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 0)

        self.assertEqual(_reconcile_persistent_state(session), "return_broker")
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 1)

        session.database.add_item(77, GOBLIN_SALVAGE_ITEM_KEY, 3)
        _reconcile_persistent_state(session)
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 1)

    def test_login_resume_reconciles_and_displays_current_objective(self):
        service = FakeWorldService()
        RuntimeSession = runtime_session_class()
        install_goblin_salvage_quest_runtime(RuntimeSession, service)
        session = RuntimeSession()
        session.database.start_quest(77, GOBLIN_SALVAGE_QUEST.key, "stamp_claim")

        asyncio.run(session.enter_character())
        self.assertEqual(session.enter_count, 1)
        self.assertEqual(session.database.item_quantity(77, GOBLIN_SALVAGE_ITEM_KEY), 1)
        self.assertTrue(any("still recorded in the ledger" in output for output in session.outputs))
        self.assertTrue(any("Nalla Inkthumb" in output for output in session.outputs))

    def test_sqlite_keeps_step_item_and_credit_across_database_reopen(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mud.db"
            database = Database(path)
            account = database.create_account("goblintest", "not-a-real-login-hash")
            character = database.create_character(
                account.id,
                "Scrapling",
                "goblin",
                "wizard",
                CharacterStats(),
            )
            database.start_quest(character.id, GOBLIN_SALVAGE_QUEST.key, "repair_salvage")
            database.add_item(character.id, GOBLIN_SALVAGE_ITEM_KEY, 1)
            database.grant_flag(character.id, "test_persisted_marker")

            reopened = Database(path)
            quest = reopened.get_quest(character.id, GOBLIN_SALVAGE_QUEST.key)
            self.assertEqual(quest["status"], "active")
            self.assertEqual(quest["current_step"], "repair_salvage")
            self.assertEqual(reopened.item_quantity(character.id, GOBLIN_SALVAGE_ITEM_KEY), 1)
            self.assertIn("test_persisted_marker", reopened.list_flags(character.id))


if __name__ == "__main__":
    unittest.main()
