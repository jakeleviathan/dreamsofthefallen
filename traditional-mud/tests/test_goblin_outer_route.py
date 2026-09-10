import asyncio
import unittest
from types import SimpleNamespace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.combat import EnemyState, SEWER_RAT
from mud.goblin_outer_route import (
    GOBLIN_FIRST_PILING_KEY,
    GOBLIN_OUTER_ROUTE_ACCESS_FLAG,
    GOBLIN_OUTER_ROUTE_COMPLETE_FLAG,
    GOBLIN_OUTER_ROUTE_QUEST,
    GOBLIN_REEDJAW_DEFEATED_FLAG,
    GOBLIN_ROUTE_TALLY_ITEM_KEY,
    REEDJAW_SCAVENGER,
    ROUTE_CACHE_RUMMAGE,
    _handle_route_cache,
    _talk_ruskle,
    install_goblin_outer_route_content,
    install_goblin_outer_route_runtime,
)
from mud.goblin_salvage_quest import GOBLIN_SALVAGE_CREDIT_FLAG
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_REGION_KEY,
    goblin_room_augmentations,
    install_goblin_world,
)
from mud.room_engine import PlayerRoomContext, WorldService
from mud.scavenging import RUMMAGE_NODES


class FakeDatabase:
    def __init__(self):
        self.quests = {}
        self.items = {}
        self.flags = set()
        self.room_updates = []

    def get_quest(self, character_id, quest_key):
        value = self.quests.get((character_id, quest_key))
        return None if value is None else dict(value)

    def start_quest(self, character_id, quest_key, current_step):
        self.quests.setdefault(
            (character_id, quest_key),
            {"status": "active", "current_step": current_step},
        )

    def advance_quest(self, character_id, quest_key, current_step):
        value = self.quests[(character_id, quest_key)]
        if value["status"] == "active":
            value["current_step"] = current_step

    def complete_quest(self, character_id, quest_key):
        value = self.quests[(character_id, quest_key)]
        value["status"] = "completed"
        value["current_step"] = "complete"

    def add_item(self, character_id, item_key, quantity=1):
        key = (character_id, item_key)
        self.items[key] = self.items.get(key, 0) + quantity

    def item_quantity(self, character_id, item_key):
        return self.items.get((character_id, item_key), 0)

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

    def set_character_room(self, character_id, room_key):
        self.room_updates.append((character_id, room_key))


class FakeSession:
    def __init__(self):
        self.character = SimpleNamespace(
            id=91,
            name="Nib",
            race="goblin",
            current_room=GOBLIN_BRASSGUT_MARKET_KEY,
        )
        self.database = FakeDatabase()
        self.outputs = []
        self.active_enemy = None
        self.combatant = SimpleNamespace(
            current_hp=0,
            max_hp=30,
            current_mana=0,
            max_mana=18,
        )
        self.stopped_combat = False
        self.base_death_called = False
        self.next_command = ""
        self.state = SimpleNamespace()

    async def send(self, text):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def show_current_room(self):
        return None

    async def _stop_combat(self):
        self.stopped_combat = True
        self.active_enemy = None

    async def enter_character(self):
        return None

    async def prompt(self, _text):
        return self.next_command

    async def playing_prompt(self):
        return None

    async def move_character(self, direction):
        room = world.ROOMS_BY_KEY.get(self.character.current_room)
        if room is not None and direction in room.exits:
            self.character.current_room = room.exits[direction]

    async def _finish_enemy_defeat(self, _enemy):
        return None

    async def _handle_character_death(self, _enemy_name):
        self.base_death_called = True


class GoblinOuterRouteTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_goblin_world()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)

    def _service(self):
        service = WorldService(
            rooms=world.ROOMS_BY_KEY,
            augmentations=goblin_room_augmentations(),
        )
        install_goblin_outer_route_content(service)
        return service

    def test_content_adds_exactly_one_room_beyond_safe_line(self):
        service = self._service()
        room = world.ROOMS_BY_KEY[GOBLIN_FIRST_PILING_KEY]
        self.assertEqual(room.region_key, GOBLIN_REGION_KEY)
        self.assertEqual(room.exits, {"south": GOBLIN_FLOODGATE_WALK_KEY})
        self.assertEqual(room.enemy_keys, (REEDJAW_SCAVENGER.key,))
        self.assertIn("tutorial_danger", room.tags)
        self.assertIn(GOBLIN_FIRST_PILING_KEY, service.legacy_rooms)
        self.assertIs(RUMMAGE_NODES.get(ROUTE_CACHE_RUMMAGE.key), ROUTE_CACHE_RUMMAGE)

    def test_north_route_is_hidden_until_ruskle_authorizes_it(self):
        service = self._service()
        locked_context = PlayerRoomContext(
            character_id=91,
            race_key="goblin",
            class_key="brute",
            level=1,
        )
        unlocked_context = PlayerRoomContext(
            character_id=91,
            race_key="goblin",
            class_key="brute",
            level=1,
            character_flags=frozenset({GOBLIN_OUTER_ROUTE_ACCESS_FLAG}),
        )
        locked = service.build_view(GOBLIN_FLOODGATE_WALK_KEY, locked_context)
        unlocked = service.build_view(GOBLIN_FLOODGATE_WALK_KEY, unlocked_context)
        self.assertNotIn("north", {value.direction for value in locked.exits})
        self.assertIn("north", {value.direction for value in unlocked.exits})
        denied = service.resolve_exit(GOBLIN_FLOODGATE_WALK_KEY, "north", locked_context)
        self.assertFalse(denied.allowed)
        self.assertIn("Ruskle", denied.message)

    def test_reedjaw_is_gentler_than_existing_human_tutorial_vermin(self):
        self.assertLess(REEDJAW_SCAVENGER.max_hp, SEWER_RAT.max_hp)
        self.assertLess(REEDJAW_SCAVENGER.armor_class, SEWER_RAT.armor_class)
        self.assertLess(REEDJAW_SCAVENGER.auto_attack_damage, SEWER_RAT.auto_attack_damage)
        self.assertGreater(REEDJAW_SCAVENGER.auto_attack_interval, SEWER_RAT.auto_attack_interval)
        self.assertGreater(REEDJAW_SCAVENGER.xp_reward, 0)

    def test_ruskle_requires_first_salvage_credit_before_outer_job(self):
        session = FakeSession()
        handled = asyncio.run(_talk_ruskle(session))
        self.assertFalse(handled)
        self.assertIsNone(session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key))

        session.database.grant_flag(91, GOBLIN_SALVAGE_CREDIT_FLAG)
        handled = asyncio.run(_talk_ruskle(session))
        self.assertTrue(handled)
        quest = session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key)
        self.assertEqual(quest["current_step"], "cross_checkpoint")
        self.assertIn(GOBLIN_OUTER_ROUTE_ACCESS_FLAG, session.database.list_flags(91))

    def test_complete_first_danger_loop_and_rescue_are_nonpunitive(self):
        service = self._service()

        class RuntimeSession(FakeSession):
            pass

        install_goblin_outer_route_runtime(RuntimeSession, service)
        session = RuntimeSession()
        session.database.grant_flag(91, GOBLIN_SALVAGE_CREDIT_FLAG)

        asyncio.run(_talk_ruskle(session))
        session.character.current_room = GOBLIN_FLOODGATE_WALK_KEY
        asyncio.run(session.move_character("north"))
        self.assertEqual(session.character.current_room, GOBLIN_FIRST_PILING_KEY)
        self.assertEqual(
            session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key)["current_step"],
            "defeat_scavenger",
        )

        enemy = EnemyState(REEDJAW_SCAVENGER)
        session.active_enemy = enemy
        asyncio.run(session._finish_enemy_defeat(enemy))
        self.assertEqual(
            session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key)["current_step"],
            "recover_tally",
        )
        self.assertIn(GOBLIN_REEDJAW_DEFEATED_FLAG, session.database.list_flags(91))

        handled = asyncio.run(_handle_route_cache(session, "search route cache"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(91, GOBLIN_ROUTE_TALLY_ITEM_KEY), 1)
        self.assertEqual(
            session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key)["current_step"],
            "return_broker",
        )

        session.character.current_room = GOBLIN_BRASSGUT_MARKET_KEY
        asyncio.run(_talk_ruskle(session))
        finished = session.database.get_quest(91, GOBLIN_OUTER_ROUTE_QUEST.key)
        self.assertEqual(finished["status"], "completed")
        self.assertEqual(session.database.item_quantity(91, GOBLIN_ROUTE_TALLY_ITEM_KEY), 0)
        self.assertIn(GOBLIN_OUTER_ROUTE_COMPLETE_FLAG, session.database.list_flags(91))

        # A fresh attempt at the fight uses the quest-specific flood-watch rescue,
        # not normal death handling or XP-loss logic.
        session.character.current_room = GOBLIN_FIRST_PILING_KEY
        session.active_enemy = EnemyState(REEDJAW_SCAVENGER)
        session.combatant.current_hp = 0
        session.combatant.current_mana = 0
        asyncio.run(session._handle_character_death(REEDJAW_SCAVENGER.name))
        self.assertFalse(session.base_death_called)
        self.assertTrue(session.stopped_combat)
        self.assertEqual(session.combatant.current_hp, session.combatant.max_hp)
        self.assertEqual(session.combatant.current_mana, session.combatant.max_mana)
        self.assertIn((91, GOBLIN_FLOODGATE_WALK_KEY), session.database.room_updates)
        self.assertTrue(any("No experience is lost" in text for text in session.outputs))


if __name__ == "__main__":
    unittest.main()
