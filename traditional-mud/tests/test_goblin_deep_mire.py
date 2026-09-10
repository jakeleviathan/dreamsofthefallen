import asyncio
import unittest
from types import SimpleNamespace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.astralis_calendar import calendar_for_day
from mud.goblin_deep_mire import (
    BOGMINT_LEAF,
    DEEP_MIRE_ALCHEMY_RECIPES,
    FLOODPICK_CLAN_KEYS,
    FLOODPICK_OUTPUTS,
    GLASSROOT_SHARD,
    GOBLIN_BLACKREED_GATE_KEY,
    GOBLIN_DEEP_MIRE_GATHERING,
    GOBLIN_DEEP_MIRE_ROOM_KEYS,
    GOBLIN_DROWNED_GLASSHOUSE_QUEST,
    GOBLIN_GREENHOUSE_APPROACH_KEY,
    GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
    GOBLIN_GREENHOUSE_FLOODED_HALL_KEY,
    GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY,
    GOBLIN_GREENHOUSE_ROOM_KEYS,
    GOBLIN_MUDGLASS_CROSSING_KEY,
    GOBLIN_SOURREED_TERRACE_KEY,
    GREENHOUSE_DRAINED_FLAG,
    GREENHOUSE_GLASSROOT_FLAG,
    GREENHOUSE_LOUVERS_FLAG,
    DeepMireGatheringService,
    _handle_deep_gathering,
    _handle_glasshouse_puzzle,
    floodpick_controller,
    install_goblin_deep_mire_content,
)
from mud.goblin_start import goblin_room_augmentations, install_goblin_world
from mud.goblin_swamp import install_goblin_swamp_content
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self):
        self.items = {}
        self.skills = {}
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

    def get_trade_skill_progress(self, character_id, trade_skill_key):
        value = self.skills.get((character_id, trade_skill_key), 0)
        return {"uses": value, "skill_xp": value}

    def record_trade_skill_use(self, character_id, trade_skill_key, skill_xp_gain=1):
        key = (character_id, trade_skill_key)
        self.skills[key] = self.skills.get(key, 0) + skill_xp_gain

    def complete_crafting_transaction(
        self,
        character_id,
        *,
        trade_skill_key,
        materials,
        output_item_key,
        output_quantity=1,
        skill_xp_gain=1,
    ):
        if any(self.item_quantity(character_id, req.item_key) < req.quantity for req in materials):
            return False
        for req in materials:
            self.consume_item(character_id, req.item_key, req.quantity)
        self.add_item(character_id, output_item_key, output_quantity)
        self.record_trade_skill_use(character_id, trade_skill_key, skill_xp_gain)
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
    def __init__(self, room_key):
        self.character = SimpleNamespace(id=501, name="Nib", race="goblin", current_room=room_key)
        self.database = FakeDatabase()
        self.outputs = []

    async def send(self, text):
        self.outputs.append(text)


class GoblinDeepMireTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.alchemy_recipes = crafting.ALCHEMY_RECIPES
        self.alchemy_by_key = dict(crafting.ALCHEMY_RECIPES_BY_KEY)
        self.all_recipes = crafting.ALL_RECIPES
        self.recipes_by_key = dict(crafting.RECIPES_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        install_goblin_world()
        GOBLIN_DEEP_MIRE_GATHERING.reset()

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
        crafting.ALCHEMY_RECIPES = self.alchemy_recipes
        crafting.ALCHEMY_RECIPES_BY_KEY.clear()
        crafting.ALCHEMY_RECIPES_BY_KEY.update(self.alchemy_by_key)
        crafting.ALL_RECIPES = self.all_recipes
        crafting.RECIPES_BY_KEY.clear()
        crafting.RECIPES_BY_KEY.update(self.recipes_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        GOBLIN_DEEP_MIRE_GATHERING.reset()

    def _service(self):
        install_goblin_swamp_content()
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=goblin_room_augmentations())
        install_goblin_deep_mire_content(service)
        return service

    def test_deeper_mire_is_fourteen_room_branching_network(self):
        self._service()
        self.assertEqual(len(GOBLIN_DEEP_MIRE_ROOM_KEYS), 14)
        self.assertEqual(len(GOBLIN_GREENHOUSE_ROOM_KEYS), 5)
        for room_key in GOBLIN_DEEP_MIRE_ROOM_KEYS:
            self.assertIn(room_key, world.ROOMS_BY_KEY)
            self.assertIn("goblin_deep_mire", world.ROOMS_BY_KEY[room_key].tags)

        mudglass = world.ROOMS_BY_KEY[GOBLIN_MUDGLASS_CROSSING_KEY]
        self.assertEqual(mudglass.exits["north"], GOBLIN_BLACKREED_GATE_KEY)
        blackreed = world.ROOMS_BY_KEY[GOBLIN_BLACKREED_GATE_KEY]
        self.assertEqual(set(blackreed.exits), {"south", "north", "east", "west"})

        # The network reconnects rather than acting like a corridor.
        destinations = [destination for room_key in GOBLIN_DEEP_MIRE_ROOM_KEYS for destination in world.ROOMS_BY_KEY[room_key].exits.values()]
        self.assertGreaterEqual(destinations.count("goblin_three_stake_junction"), 2)
        self.assertGreaterEqual(destinations.count("goblin_old_pump_track"), 2)

    def test_deep_mire_has_no_boss_and_combat_stays_light(self):
        self._service()
        enemy_rooms = [world.ROOMS_BY_KEY[key] for key in GOBLIN_DEEP_MIRE_ROOM_KEYS if world.ROOMS_BY_KEY[key].enemy_keys]
        self.assertGreaterEqual(len(enemy_rooms), 3)
        for room in enemy_rooms:
            self.assertLessEqual(len(room.enemy_keys), 1)
            enemy = combat.ENEMIES_BY_KEY[room.enemy_keys[0]]
            self.assertNotIn("boss", enemy.key)
            self.assertLessEqual(enemy.auto_attack_damage, 3)
            self.assertLessEqual(enemy.max_hp, 32)

    def test_floodpick_control_is_stable_for_three_days_then_rotates(self):
        first = floodpick_controller(calendar_for_day(1))
        self.assertIn(first, FLOODPICK_CLAN_KEYS)
        self.assertEqual(first, floodpick_controller(calendar_for_day(2)))
        self.assertEqual(first, floodpick_controller(calendar_for_day(3)))
        second = floodpick_controller(calendar_for_day(4))
        self.assertIn(second, FLOODPICK_CLAN_KEYS)
        self.assertNotEqual(first, second)
        self.assertIsNone(floodpick_controller(calendar_for_day(24)))  # Summer begins.

    def test_spring_claim_changes_which_reagent_appears(self):
        outputs = []
        for day in (1, 4, 7):
            service = DeepMireGatheringService(calendar_provider=lambda day=day: calendar_for_day(day))
            node = service.resolve(GOBLIN_SOURREED_TERRACE_KEY, "herb patch")
            self.assertIsNotNone(node)
            outputs.append(service.output_for(node))
        self.assertEqual(set(outputs), set(FLOODPICK_OUTPUTS.values()))

        summer = DeepMireGatheringService(calendar_provider=lambda: calendar_for_day(24))
        self.assertEqual(summer.nodes_in_room(GOBLIN_SOURREED_TERRACE_KEY), ())

    def test_glasshouse_north_door_requires_drain_flag(self):
        service = self._service()
        locked = PlayerRoomContext(character_id=501, race_key="goblin", class_key="wizard", level=2)
        open_context = PlayerRoomContext(
            character_id=501,
            race_key="goblin",
            class_key="wizard",
            level=2,
            character_flags=frozenset({GREENHOUSE_DRAINED_FLAG}),
        )
        blocked = service.resolve_exit(GOBLIN_GREENHOUSE_FLOODED_HALL_KEY, "north", locked)
        opened = service.resolve_exit(GOBLIN_GREENHOUSE_FLOODED_HALL_KEY, "north", open_context)
        self.assertFalse(blocked.allowed)
        self.assertIn("pump", blocked.message.lower())
        self.assertTrue(opened.allowed)
        self.assertEqual(opened.destination_key, GOBLIN_GREENHOUSE_CONSERVATORY_KEY)

    def test_environmental_puzzle_completes_without_combat(self):
        self._service()
        session = FakeSession(GOBLIN_GREENHOUSE_APPROACH_KEY)
        session.database.skills[(501, "herbalism")] = 10

        self.assertTrue(asyncio.run(_handle_glasshouse_puzzle(session, "examine plaque")))
        self.assertEqual(session.database.get_quest(501, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)["current_step"], "read_pipe_map")

        session.character.current_room = GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY
        self.assertTrue(asyncio.run(_handle_glasshouse_puzzle(session, "examine pipe map")))
        self.assertEqual(session.database.get_quest(501, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)["current_step"], "drain_hall")

        # Wrong valve is informative but harmless and does not solve the gate.
        self.assertTrue(asyncio.run(_handle_glasshouse_puzzle(session, "turn blue valve")))
        self.assertNotIn(GREENHOUSE_DRAINED_FLAG, session.database.list_flags(501))

        self.assertTrue(asyncio.run(_handle_glasshouse_puzzle(session, "turn black valve")))
        self.assertIn(GREENHOUSE_DRAINED_FLAG, session.database.list_flags(501))

        session.character.current_room = GOBLIN_GREENHOUSE_CONSERVATORY_KEY
        self.assertTrue(asyncio.run(_handle_glasshouse_puzzle(session, "open louvers")))
        self.assertIn(GREENHOUSE_LOUVERS_FLAG, session.database.list_flags(501))
        self.assertEqual(session.database.get_quest(501, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)["current_step"], "harvest_glassroot")

        self.assertTrue(asyncio.run(_handle_deep_gathering(session, "harvest glassroot")))
        self.assertEqual(session.database.item_quantity(501, GLASSROOT_SHARD.key), 1)
        self.assertIn(GREENHOUSE_GLASSROOT_FLAG, session.database.list_flags(501))
        self.assertEqual(session.database.get_quest(501, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)["status"], "completed")

    def test_deep_mire_registers_real_tier_two_alchemy_recipes(self):
        self._service()
        self.assertEqual(len(DEEP_MIRE_ALCHEMY_RECIPES), 3)
        self.assertIn(BOGMINT_LEAF.key, crafting.ITEMS_BY_KEY)
        for recipe in DEEP_MIRE_ALCHEMY_RECIPES:
            self.assertIn(recipe.key, crafting.ALCHEMY_RECIPES_BY_KEY)
            self.assertIn(recipe.key, crafting.RECIPES_BY_KEY)
            self.assertGreaterEqual(recipe.minimum_skill, 5)
            self.assertLessEqual(recipe.minimum_skill, 12)


if __name__ == "__main__":
    unittest.main()
