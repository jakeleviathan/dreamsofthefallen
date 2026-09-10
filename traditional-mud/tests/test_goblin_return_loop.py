import asyncio
import unittest
from types import SimpleNamespace

import mud.world as world
from mud.goblin_deep_mire import GOBLIN_OLD_PUMP_TRACK_KEY, goblin_deep_mire_augmentations, install_goblin_deep_mire_content
from mud.goblin_return_loop import (
    GOBLIN_BOTTLEWIRE_RETURN_KEY,
    GOBLIN_HIGHWATER_CATWALK_KEY,
    GOBLIN_RETURN_LOOP_DISCOVERED_FLAG,
    GOBLIN_RETURN_LOOP_ROOM_KEYS,
    install_goblin_return_loop_content,
    install_goblin_return_loop_runtime,
)
from mud.goblin_start import goblin_room_augmentations, install_goblin_world
from mud.goblin_swamp import GOBLIN_APOTHECARY_BLIND_KEY, goblin_swamp_augmentations
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self):
        self.flags = set()

    def list_flags(self, character_id):
        return frozenset(flag for owner, flag in self.flags if owner == character_id)

    def grant_flag(self, character_id, flag_key):
        self.flags.add((character_id, flag_key))


class GoblinReturnLoopTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        install_goblin_world()
        install_goblin_deep_mire_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)

    def _service(self):
        augmentations = {}
        augmentations.update(goblin_room_augmentations())
        augmentations.update(goblin_swamp_augmentations())
        augmentations.update(goblin_deep_mire_augmentations())
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=augmentations)
        install_goblin_return_loop_content(service)
        return service

    def test_two_room_safe_loop_connects_deep_mire_to_apothecary(self):
        self._service()
        self.assertEqual(len(GOBLIN_RETURN_LOOP_ROOM_KEYS), 2)
        for room_key in GOBLIN_RETURN_LOOP_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertEqual(room.enemy_keys, ())
            self.assertIn("safe_return_route", room.tags)
            self.assertIn("no_hostiles", room.tags)

        self.assertEqual(world.ROOMS_BY_KEY[GOBLIN_OLD_PUMP_TRACK_KEY].exits["east"], GOBLIN_HIGHWATER_CATWALK_KEY)
        self.assertEqual(world.ROOMS_BY_KEY[GOBLIN_HIGHWATER_CATWALK_KEY].exits["south"], GOBLIN_BOTTLEWIRE_RETURN_KEY)
        self.assertEqual(world.ROOMS_BY_KEY[GOBLIN_BOTTLEWIRE_RETURN_KEY].exits["south"], GOBLIN_APOTHECARY_BLIND_KEY)

    def test_reverse_shortcut_is_hidden_until_player_discovers_marker_code(self):
        service = self._service()
        unknown = PlayerRoomContext(character_id=5, race_key="goblin", class_key="brute", level=2)
        known = PlayerRoomContext(
            character_id=5,
            race_key="goblin",
            class_key="brute",
            level=2,
            character_flags=frozenset({GOBLIN_RETURN_LOOP_DISCOVERED_FLAG}),
        )
        unknown_view = service.build_view(GOBLIN_APOTHECARY_BLIND_KEY, unknown)
        known_view = service.build_view(GOBLIN_APOTHECARY_BLIND_KEY, known)
        self.assertNotIn("north", {value.direction for value in unknown_view.exits})
        north = next(value for value in known_view.exits if value.direction == "north")
        self.assertEqual(north.destination_key, GOBLIN_BOTTLEWIRE_RETURN_KEY)

    def test_entering_return_loop_records_reverse_route_for_goblin(self):
        service = self._service()

        class DummySession:
            async def move_character(self, direction):
                if direction == "east" and self.character.current_room == GOBLIN_OLD_PUMP_TRACK_KEY:
                    self.character.current_room = GOBLIN_HIGHWATER_CATWALK_KEY

        install_goblin_return_loop_runtime(DummySession, service)
        session = DummySession()
        session.character = SimpleNamespace(id=55, race="goblin", current_room=GOBLIN_OLD_PUMP_TRACK_KEY)
        session.database = FakeDatabase()
        session.outputs = []

        async def send(text):
            session.outputs.append(text)

        session.send = send
        asyncio.run(session.move_character("east"))
        self.assertIn(GOBLIN_RETURN_LOOP_DISCOVERED_FLAG, session.database.list_flags(55))
        self.assertTrue(any("shortcut" in text.lower() for text in session.outputs))


if __name__ == "__main__":
    unittest.main()
