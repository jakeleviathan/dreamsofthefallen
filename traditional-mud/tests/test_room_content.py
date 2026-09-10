import unittest

from mud.room_content import complete_room_augmentations
from mud.room_engine import PlayerRoomContext, WorldService
from mud.world import ROOMS, ROOMS_BY_KEY


class CompleteRoomContentTests(unittest.TestCase):
    def setUp(self):
        self.augmentations = complete_room_augmentations()
        self.world = WorldService(augmentations=self.augmentations)
        self.context = PlayerRoomContext(
            character_id=1,
            race_key="human",
            class_key="brute",
            level=1,
            hour=12,
        )

    def test_every_authored_room_has_rich_scene_content(self):
        self.assertEqual(len(ROOMS), 26)
        self.assertEqual(set(self.augmentations), set(ROOMS_BY_KEY))

        for room in ROOMS:
            with self.subTest(room=room.key):
                augmentation = self.augmentations[room.key]
                self.assertGreaterEqual(len(augmentation.features), 2)
                self.assertGreaterEqual(len(augmentation.description_layers), 1)

    def test_every_legacy_exit_has_named_route_and_authored_travel_text(self):
        for room in ROOMS:
            augmentation = self.augmentations[room.key]
            overrides = {exit_def.direction: exit_def for exit_def in augmentation.exit_overrides}
            with self.subTest(room=room.key):
                self.assertEqual(set(overrides), set(room.exits))
                for direction, destination_key in room.exits.items():
                    exit_def = overrides[direction]
                    self.assertEqual(exit_def.destination_key, destination_key)
                    self.assertTrue(exit_def.name.strip())
                    self.assertTrue(exit_def.travel_text.strip())

    def test_every_room_builds_a_visible_scene_with_features_and_named_routes(self):
        for room in ROOMS:
            with self.subTest(room=room.key):
                view = self.world.build_view(room.key, self.context)
                self.assertIsNotNone(view)
                self.assertEqual(view.key, room.key)
                self.assertTrue(view.description.strip())
                self.assertGreaterEqual(len(view.features), 2)
                for route in view.exits:
                    self.assertTrue(route.name.strip())

    def test_all_feature_aliases_can_be_interacted_with(self):
        for room in ROOMS:
            context = self.context
            view = self.world.build_view(room.key, context)
            for feature in view.features:
                with self.subTest(room=room.key, feature=feature.key):
                    target = feature.aliases[0] if feature.aliases else feature.name
                    result = self.world.interact(room.key, "examine", target, context)
                    self.assertTrue(result.handled)
                    self.assertTrue(result.text.strip())


if __name__ == "__main__":
    unittest.main()
