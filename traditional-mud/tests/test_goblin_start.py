import unittest

from mud.astralis_calendar import calendar_for_day
from mud.goblin_start import (
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_NPCS,
    GOBLIN_REGION_KEY,
    GOBLIN_ROOMS,
    GOBLIN_START_ROOM_KEY,
    goblin_room_augmentations,
    install_goblin_world,
)
from mud.seasonal_cultures import ANCHORS_BY_RACE
import mud.world as world


class GoblinJunkCityStartTests(unittest.TestCase):
    def test_seven_room_safe_city_core_is_authored(self):
        self.assertEqual(len(GOBLIN_ROOMS), 7)
        self.assertEqual(GOBLIN_ROOMS[0].key, GOBLIN_START_ROOM_KEY)
        for room in GOBLIN_ROOMS:
            self.assertEqual(room.region_key, GOBLIN_REGION_KEY)
            self.assertIn("safe", room.tags)
            self.assertFalse(room.enemy_keys, f"{room.key} unexpectedly contains a hostile starter enemy")

    def test_every_authored_route_stays_inside_safe_core(self):
        keys = {room.key for room in GOBLIN_ROOMS}
        for room in GOBLIN_ROOMS:
            for destination in room.exits.values():
                self.assertIn(destination, keys, f"{room.key} leaves the supervised starter core")

    def test_floodgate_is_safe_boundary_with_future_danger_hint(self):
        floodgate = next(room for room in GOBLIN_ROOMS if room.key == GOBLIN_FLOODGATE_WALK_KEY)
        self.assertIn("city_edge", floodgate.tags)
        self.assertIn("danger_hint", floodgate.tags)
        self.assertIn("future_route", floodgate.tags)
        self.assertEqual(floodgate.exits, {"south": "goblin_patchwork_plaza"})

    def test_every_room_has_rich_features_and_daytime_activity_layer(self):
        augmentations = goblin_room_augmentations()
        self.assertEqual(set(augmentations), {room.key for room in GOBLIN_ROOMS})
        for room in GOBLIN_ROOMS:
            augmentation = augmentations[room.key]
            self.assertGreaterEqual(len(augmentation.features), 2)
            day_layers = [
                layer for layer in augmentation.description_layers
                if "day" in layer.condition.time_buckets
            ]
            self.assertTrue(day_layers, f"{room.key} lacks its bright daytime activity layer")

    def test_goblin_start_has_real_social_contacts(self):
        self.assertEqual(len(GOBLIN_NPCS), 2)
        self.assertEqual({npc.room_key for npc in GOBLIN_NPCS}, {"goblin_clattergate", "goblin_brassgut_market"})
        for npc in GOBLIN_NPCS:
            self.assertTrue(npc.dialogue)

    def test_installation_registers_rooms_and_npcs_idempotently(self):
        original_rooms = world.ROOMS
        original_npcs = world.NPCS
        original_rooms_by_key = dict(world.ROOMS_BY_KEY)
        original_npcs_by_key = dict(world.NPCS_BY_KEY)
        try:
            install_goblin_world()
            before_rooms = len(world.ROOMS)
            before_npcs = len(world.NPCS)
            install_goblin_world()
            self.assertEqual(len(world.ROOMS), before_rooms)
            self.assertEqual(len(world.NPCS), before_npcs)
            self.assertIsNotNone(world.ROOMS_BY_KEY.get(GOBLIN_START_ROOM_KEY))
            for npc in GOBLIN_NPCS:
                self.assertIsNotNone(world.NPCS_BY_KEY.get(npc.key))
        finally:
            world.ROOMS = original_rooms
            world.NPCS = original_npcs
            world.ROOMS_BY_KEY.clear()
            world.ROOMS_BY_KEY.update(original_rooms_by_key)
            world.NPCS_BY_KEY.clear()
            world.NPCS_BY_KEY.update(original_npcs_by_key)

    def test_existing_floodpick_seasonal_anchor_matches_junk_city(self):
        anchor = ANCHORS_BY_RACE["goblin"]
        self.assertEqual(anchor.region_key, GOBLIN_REGION_KEY)
        self.assertEqual(anchor.key, "floodpick")
        spring = calendar_for_day(1)
        self.assertTrue(anchor.active(spring))


if __name__ == "__main__":
    unittest.main()
