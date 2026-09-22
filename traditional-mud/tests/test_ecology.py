from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.ecology import RegionalEcologyService
from mud.room_engine import RoomStateStore
from mud.room_state_storage import load_world_room_state, save_world_room_state


class FakeRoom:
    def __init__(self, key: str, region_key: str, *, exits=None, tags=()):
        self.key = key
        self.region_key = region_key
        self.exits = dict(exits or {})
        self.tags = tuple(tags)


def moment(hour: int, season: str = "spring"):
    return SimpleNamespace(total_hours=hour, season=season)


class RegionalEcologyTests(unittest.TestCase):
    def setUp(self):
        self.rooms = {
            "forest_a": FakeRoom(
                "forest_a",
                "great_elf_forest",
                exits={"east": "forest_b"},
                tags=("forest", "wilderness"),
            ),
            "forest_b": FakeRoom(
                "forest_b",
                "great_elf_forest",
                exits={"west": "forest_a"},
                tags=("forest", "trail"),
            ),
        }
        self.state = RoomStateStore()
        self.service = RegionalEcologyService()
        self.service.initialize(moment(100), self.state, self.rooms)

    def test_rain_feeds_persistent_regional_moisture(self):
        before = self.service.state_for("great_elf_forest").moisture
        self.state.set_weather("great_elf_forest", "rain")
        self.assertTrue(self.service.sync(moment(101), self.state))
        after = self.service.state_for("great_elf_forest").moisture
        self.assertGreater(after, before)

    def test_clear_weather_dries_a_wet_region_gradually(self):
        payload = self.state.region_ecology["great_elf_forest"]
        payload["moisture"] = 0.90
        self.state.set_weather("great_elf_forest", "clear")
        self.service.sync(moment(101), self.state)
        self.assertLess(self.service.state_for("great_elf_forest").moisture, 0.90)

    def test_repeated_harvesting_can_pick_a_region_thin(self):
        allowed, _ = self.service.gathering_allowed(
            "great_elf_forest",
            skill_key="herbalism",
        )
        self.assertTrue(allowed)

        for _ in range(40):
            self.service.record_harvest(
                "great_elf_forest",
                skill_key="herbalism",
            )

        allowed, message = self.service.gathering_allowed(
            "great_elf_forest",
            skill_key="herbalism",
        )
        self.assertFalse(allowed)
        self.assertIn("picked thin", message.lower())

    def test_wildlife_kills_feed_carrion_and_reduce_the_hunted_population(self):
        creature = SimpleNamespace(
            key="silverleaf_hare",
            name="Silverleaf Hare",
            description="a small forest hare",
        )
        before = self.service.state_for("great_elf_forest")
        prey_before = before.prey
        carrion_before = before.carrion

        self.service.record_creature_kill("great_elf_forest", creature)
        after = self.service.state_for("great_elf_forest")

        self.assertLess(after.prey, prey_before)
        self.assertGreater(after.carrion, carrion_before)

    def test_ecology_is_discovered_from_world_rooms_not_a_fixed_region_list(self):
        rooms = {
            "new_a": FakeRoom(
                "new_a",
                "future_marsh",
                exits={"east": "new_b"},
                tags=("swamp", "wilderness"),
            ),
            "new_b": FakeRoom(
                "new_b",
                "future_marsh",
                exits={"west": "new_a"},
                tags=("swamp", "trail"),
            ),
        }
        state = RoomStateStore()
        service = RegionalEcologyService()
        service.initialize(moment(5), state, rooms)

        ecology = service.state_for("future_marsh")
        self.assertIsNotNone(ecology)
        self.assertGreater(ecology.moisture, 0.70)

    def test_adjacent_regions_exchange_wildlife_toward_better_habitat(self):
        rooms = {
            "dry": FakeRoom(
                "dry",
                "dry_reach",
                exits={"east": "green"},
                tags=("desert", "wilderness"),
            ),
            "green": FakeRoom(
                "green",
                "green_reach",
                exits={"west": "dry"},
                tags=("forest", "wilderness"),
            ),
        }
        state = RoomStateStore()
        service = RegionalEcologyService()
        service.initialize(moment(20), state, rooms)

        dry = state.region_ecology["dry_reach"]
        green = state.region_ecology["green_reach"]
        dry.update({
            "prey": 0.80,
            "vegetation": 0.12,
            "insects": 0.12,
            "resource_stock": 0.18,
            "moisture": 0.12,
            "predators": 0.50,
            "disturbance": 0.30,
        })
        green.update({
            "prey": 0.40,
            "vegetation": 0.90,
            "insects": 0.80,
            "resource_stock": 0.90,
            "moisture": 0.75,
            "predators": 0.20,
            "disturbance": 0.02,
        })
        dry_before = float(dry["prey"])
        green_before = float(green["prey"])

        service._migrate()

        self.assertLess(service.state_for("dry_reach").prey, dry_before)
        self.assertGreater(service.state_for("green_reach").prey, green_before)

    def test_player_facing_land_reading_uses_descriptions_not_simulation_numbers(self):
        lines = self.service.describe_region("great_elf_forest")
        rendered = " ".join(lines)
        self.assertTrue(rendered)
        self.assertFalse(any(character.isdigit() for character in rendered))
        self.assertNotIn("%", rendered)

    def test_ecology_round_trips_with_shared_world_state(self):
        self.service.record_harvest(
            "great_elf_forest",
            skill_key="herbalism",
        )
        expected = dict(self.state.region_ecology["great_elf_forest"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            save_world_room_state(self.state, path)
            restored = RoomStateStore()
            self.assertTrue(load_world_room_state(restored, path))

        self.assertEqual(restored.region_ecology["great_elf_forest"], expected)


if __name__ == "__main__":
    unittest.main()
