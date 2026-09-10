import unittest

from mud.room_engine import (
    PersistenceScope,
    PlayerRoomContext,
    RoomStateStore,
    WorldService,
)
from mud.world import HUMAN_START_ROOM_KEY, SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY


class AdvancedRoomEngineTests(unittest.TestCase):
    def setUp(self):
        self.state = RoomStateStore()
        self.world = WorldService(state=self.state)

    @staticmethod
    def context(*, race="human", flags=(), hour=12):
        return PlayerRoomContext(
            character_id=1,
            race_key=race,
            class_key="brute",
            level=1,
            character_flags=frozenset(flags),
            hour=hour,
        )

    def test_demon_gate_is_player_specific_and_time_layered(self):
        human_night = self.world.build_view(HUMAN_START_ROOM_KEY, self.context(race="human", hour=23))
        outsider_day = self.world.build_view(HUMAN_START_ROOM_KEY, self.context(race="dwarf", hour=12))

        self.assertIsNotNone(human_night)
        self.assertIsNotNone(outsider_day)
        self.assertIn("To you, the horns", human_night.description)
        self.assertIn("Night turns the gate theatrical", human_night.description)
        self.assertIn("Seen from outside Human culture", outsider_day.description)
        self.assertNotIn("To you, the horns", outsider_day.description)

    def test_demon_gate_has_first_class_named_exits_and_features(self):
        context = self.context()
        view = self.world.build_view(HUMAN_START_ROOM_KEY, context)
        self.assertEqual([value.direction for value in view.exits], ["north", "south"])
        self.assertEqual([value.name for value in view.exits], ["Ashen Way", "Outer Drill Road"])
        feature_names = {value.name for value in view.features}
        self.assertIn("Wrought-Iron Gates", feature_names)
        self.assertIn("Demonic Reliefs", feature_names)
        self.assertIn("Cathedral Skyline", feature_names)
        self.assertIn("Gate Watch", feature_names)

    def test_feature_interactions_are_data_driven(self):
        context = self.context()
        examine = self.world.interact(HUMAN_START_ROOM_KEY, "examine", "gate", context)
        search = self.world.interact(HUMAN_START_ROOM_KEY, "search", "iron gate", context)
        listen = self.world.interact(HUMAN_START_ROOM_KEY, "listen", "cathedral", context)

        self.assertTrue(examine.handled)
        self.assertIn("civic declaration", examine.text)
        self.assertTrue(search.handled)
        self.assertIn("maker's seal", search.text)
        self.assertTrue(listen.handled)
        self.assertIn("cathedral bell", listen.text)

    def test_door_state_can_block_travel_without_changing_room_definition(self):
        context = self.context()
        self.assertTrue(self.world.resolve_exit(HUMAN_START_ROOM_KEY, "south", context).allowed)
        self.state.set_door("demon_gate_outer_portal", open=False)
        blocked = self.world.resolve_exit(HUMAN_START_ROOM_KEY, "south", context)
        self.assertFalse(blocked.allowed)
        self.assertIn("closed", blocked.message.lower())

    def test_character_flag_can_reveal_hidden_exit(self):
        hidden = self.world.build_view(
            SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
            self.context(race="sporekin"),
        )
        revealed = self.world.build_view(
            SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
            self.context(race="sporekin", flags=("sporekin_forgotten_pulse_solved",)),
        )

        self.assertNotIn("north", [value.direction for value in hidden.exits])
        self.assertIn("north", [value.direction for value in revealed.exits])
        self.assertIn("spore-shaped sigil", revealed.description)

    def test_weather_is_a_world_layer_not_a_room_rewrite(self):
        self.state.set_weather("human_kingdom", "rain")
        view = self.world.build_view(HUMAN_START_ROOM_KEY, self.context())
        self.assertIn("Rain beads on black iron", view.description)

    def test_persistence_scopes_are_explicit(self):
        self.state.set_flag(HUMAN_START_ROOM_KEY, "alarm", True, PersistenceScope.WORLD)
        self.state.set_flag(HUMAN_START_ROOM_KEY, "sparks", True, PersistenceScope.TEMPORARY)
        snapshot = self.state.snapshot_world_state()

        self.assertIn("alarm", snapshot["world_flags"][HUMAN_START_ROOM_KEY])
        self.assertNotIn("temporary_flags", snapshot)
        with self.assertRaises(ValueError):
            self.state.set_flag(HUMAN_START_ROOM_KEY, "personal_secret", True, PersistenceScope.CHARACTER)


if __name__ == "__main__":
    unittest.main()
