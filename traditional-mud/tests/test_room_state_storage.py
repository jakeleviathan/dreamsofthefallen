import tempfile
import unittest
from pathlib import Path

from mud.room_engine import PersistenceScope, RoomStateStore
from mud.room_state_storage import load_world_room_state, save_world_room_state


class RoomStateStorageTests(unittest.TestCase):
    def test_world_state_round_trips_but_temporary_state_does_not(self):
        original = RoomStateStore()
        original.set_flag("room_a", "world_alarm", True, PersistenceScope.WORLD)
        original.set_flag("room_a", "temporary_sparks", True, PersistenceScope.TEMPORARY)
        original.set_door("door_a", open=False, locked=True)
        original.set_weather("region_a", "rain")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "world_room_state.json"
            save_world_room_state(original, path)

            restored = RoomStateStore()
            self.assertTrue(load_world_room_state(restored, path))

        self.assertIn("world_alarm", restored.world_flags["room_a"])
        self.assertNotIn("room_a", restored.temporary_flags)
        self.assertFalse(restored.doors["door_a"].open)
        self.assertTrue(restored.doors["door_a"].locked)
        self.assertEqual(restored.weather_for("region_a"), "rain")


if __name__ == "__main__":
    unittest.main()
