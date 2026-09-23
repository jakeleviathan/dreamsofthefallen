"""Fifth Lantern integration: physical routes, working hospitality and live patrons."""
from __future__ import annotations

import random
import unittest
from types import SimpleNamespace

from mud.crafting import ITEMS_BY_KEY
from mud.merchants import MERCHANTS_BY_NPC_KEY
from mud.movement_system import is_restful_place
from mud.npc_conversation import resolve_static_talk_target
from mud.npcs import MobileNpcManager
from mud.room_engine import PlayerRoomContext, RoomStateStore, WorldService
from mud.waymeet_frontier import (
    TAVERN_HOST_KEY, TAVERN_COOK_KEY, TAVERN_STEW_KEY, TAVERN_TEA_KEY,
    WAYMEET_COMMONHOUSE_KEY, WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_KITCHEN_KEY,
    WAYMEET_TAVERN_LOFT_KEY, WAYMEET_REGION_KEY, WAYMEET_ROOM_KEYS,
    install_waymeet_content, install_waymeet_runtime,
)
from mud.waymeet_living_npcs import (
    EDRIN, MAREN, WAYMEET_LIVING_NPCS, chatter_lines, resolve_waymeet_talk,
)
from mud.world import NPCS_BY_KEY
from mud.weather_gameplay import room_is_weather_exposed


class FifthLanternTests(unittest.TestCase):
    def setUp(self):
        install_waymeet_content()
        self.world = WorldService(state=RoomStateStore())
        install_waymeet_content(self.world)

    @staticmethod
    def context(level=10, hour=12):
        return PlayerRoomContext(
            character_id=1, race_key="goblin", class_key="priest",
            level=level, hour=hour,
        )

    def test_three_real_rooms_reciprocal_routes_and_rest(self):
        self.assertTrue({
            WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_KITCHEN_KEY,
            WAYMEET_TAVERN_LOFT_KEY,
        } <= set(WAYMEET_ROOM_KEYS))
        expected = (
            (WAYMEET_COMMONHOUSE_KEY, "in", WAYMEET_TAVERN_KEY, "out"),
            (WAYMEET_TAVERN_KEY, "east", WAYMEET_TAVERN_KITCHEN_KEY, "west"),
            (WAYMEET_TAVERN_KEY, "up", WAYMEET_TAVERN_LOFT_KEY, "down"),
        )
        for src, forward, dst, reverse in expected:
            with self.subTest(source=src):
                self.assertEqual(
                    {item.direction: item.destination_key for item in self.world.scene(src).exits}[forward],
                    dst,
                )
                self.assertEqual(
                    {item.direction: item.destination_key for item in self.world.scene(dst).exits}[reverse],
                    src,
                )
        self.assertTrue(is_restful_place(self.world, WAYMEET_TAVERN_KEY))
        self.assertTrue(is_restful_place(self.world, WAYMEET_TAVERN_LOFT_KEY))
        for room_key in (WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_KITCHEN_KEY, WAYMEET_TAVERN_LOFT_KEY):
            self.assertFalse(room_is_weather_exposed(self.world.scene(room_key).tags, room_key))
        for room_key in (WAYMEET_COMMONHOUSE_KEY, WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_KITCHEN_KEY, WAYMEET_TAVERN_LOFT_KEY):
            directions = [item.direction for item in self.world.scene(room_key).exits]
            self.assertEqual(len(directions), len(set(directions)))

    def test_dusk_storm_and_experienced_player_views_are_conditional(self):
        normal = self.world.build_view(WAYMEET_TAVERN_KEY, self.context(level=10, hour=12))
        self.assertNotIn("Broken Reach", normal.description)
        evening = self.world.build_view(WAYMEET_TAVERN_KEY, self.context(level=11, hour=19))
        self.assertIn("last wagons", evening.description)
        self.assertIn("Broken Reach", evening.description)
        self.world.state.set_weather(WAYMEET_REGION_KEY, "rain")
        wet = self.world.build_view(WAYMEET_TAVERN_KEY, self.context())
        self.assertIn("Rain beats", wet.description)
        yard = self.world.build_view(WAYMEET_COMMONHOUSE_KEY, self.context())
        self.assertIn("Wet travelers", yard.description)
        examine = self.world.interact(WAYMEET_TAVERN_KEY, "examine", "ledger", self.context())
        self.assertTrue(examine.handled)
        self.assertIn("TAVERN RUMORS", examine.text)

    def test_host_is_talkable_and_sells_food_that_eat_and_drink_use(self):
        innkeeper, ambiguous = resolve_static_talk_target(
            self.world, NPCS_BY_KEY, WAYMEET_TAVERN_KEY, "valline",
        )
        self.assertFalse(ambiguous)
        self.assertIsNotNone(innkeeper)
        self.assertEqual(innkeeper.key, TAVERN_HOST_KEY)
        self.assertIn(TAVERN_COOK_KEY, self.world.scene(WAYMEET_TAVERN_KITCHEN_KEY).npc_keys)
        stock = MERCHANTS_BY_NPC_KEY[TAVERN_HOST_KEY]
        self.assertTrue(stock.sells(TAVERN_STEW_KEY))
        self.assertTrue(stock.sells(TAVERN_TEA_KEY))
        self.assertEqual(ITEMS_BY_KEY[TAVERN_STEW_KEY].consumable.use_mode, "eat")
        self.assertEqual(ITEMS_BY_KEY[TAVERN_TEA_KEY].consumable.use_mode, "drink")

    def test_caravaner_walks_from_roads_to_tavern_and_returns_to_loft(self):
        manager = MobileNpcManager(definitions=WAYMEET_LIVING_NPCS)
        manager.validate_definitions()
        self.assertEqual(manager._routine_destination(MAREN, 6), "waymeet_west_road")
        self.assertEqual(manager._routine_destination(MAREN, 19), WAYMEET_TAVERN_KEY)
        self.assertEqual(manager._routine_destination(MAREN, 23), WAYMEET_TAVERN_LOFT_KEY)
        for _ in range(7):
            manager.tick(rng=random.Random(3), hour=19, weather_provider=lambda _: "clear")
        self.assertEqual(manager.states[MAREN.key].current_room_key, WAYMEET_TAVERN_KEY)
        resident, ambiguous = resolve_waymeet_talk(manager, WAYMEET_TAVERN_KEY, "maren")
        self.assertEqual(resident, MAREN)
        self.assertFalse(ambiguous)
        # Existing cast comes by the same real route, and tavern dialogue
        # never refers to an absent patron as if physically present.
        manager.states[EDRIN.key].current_room_key = WAYMEET_TAVERN_KEY
        for key, state in manager.states.items():
            if key not in {EDRIN.key, MAREN.key}:
                state.current_room_key = WAYMEET_COMMONHOUSE_KEY
        lines = chatter_lines(manager, WAYMEET_TAVERN_KEY, 19, "rain", rng=random.Random(0))
        self.assertIn("Maren", " ".join(lines))
        self.assertIn("Edrin", " ".join(lines))
        self.assertNotIn("Suvvi", " ".join(lines))
        manager.states[MAREN.key].current_room_key = WAYMEET_TAVERN_LOFT_KEY
        self.assertIsNone(resolve_waymeet_talk(manager, WAYMEET_TAVERN_KEY, "maren")[0])


class _FakeDatabase:
    def get_quest(self, *_args):
        return None


class _TavernSession:
    def __init__(self):
        self.character = SimpleNamespace(id=11, current_room=WAYMEET_TAVERN_KEY, level=11)
        self.database = _FakeDatabase()
        self.state = SimpleNamespace(DISCONNECTED="disconnected")
        self.mobile_npcs = MobileNpcManager(definitions=(MAREN,))
        self.mobile_npcs.states[MAREN.key].current_room_key = WAYMEET_TAVERN_KEY
        self.input_line = ""
        self.sent = []
        self.delegated = False

    async def prompt(self, _prompt):
        return self.input_line

    async def send(self, text):
        self.sent.append(text)

    async def enter_character(self):
        pass

    async def move_character(self, _direction):
        pass

    async def _finish_enemy_defeat(self, _enemy):
        pass

    async def playing_prompt(self):
        self.delegated = True


class TavernCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_road_reports_use_actual_weather_and_party_level(self):
        world = WorldService(state=RoomStateStore())
        Session = type("FifthLanternSession", (_TavernSession,), {})
        install_waymeet_runtime(Session, world)
        s = Session()
        s.input_line = "tavern rumors"
        world.state.set_weather(WAYMEET_REGION_KEY, "storm")
        await s.playing_prompt()
        spoken = "".join(s.sent)
        self.assertIn("Wet-road report", spoken)
        self.assertIn("Broken Reach", spoken)
        self.assertFalse(s.delegated)

    async def test_regulars_command_uses_live_npc_positions(self):
        world = WorldService(state=RoomStateStore())
        Session = type("FifthLanternPositionsSession", (_TavernSession,), {})
        install_waymeet_runtime(Session, world)
        s = Session()
        s.input_line = "tavern regulars"
        await s.playing_prompt()
        self.assertIn("Maren Copperwake", "".join(s.sent))
        s.sent.clear()
        s.mobile_npcs.states[MAREN.key].current_room_key = WAYMEET_TAVERN_LOFT_KEY
        await s.playing_prompt()
        self.assertNotIn("Maren Copperwake", "".join(s.sent))


if __name__ == "__main__":
    unittest.main()
