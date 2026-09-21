import random
import unittest

from mud.astralis_time import (
    AstralisWeatherService,
    TEMPERATE,
    WILDERNESS,
    _transition_candidates,
    profile_for_biome,
)
from mud.npcs import BLACKWALL_GUARD, MobileNpcManager
from mud.room_engine import RoomStateStore
from mud.stats import EquipmentItem
from mud.weather_gameplay import (
    adjusted_attack_roll,
    effects_for_weather,
    fire_spell_disrupted,
    flee_success_chance,
    room_is_weather_exposed,
    seasonal_sky_text,
    surface_condition,
)


class FixedLowRoll:
    def random(self):
        return 0.0


class WeatherGameplayTests(unittest.TestCase):
    def test_storm_penalizes_ranged_attacks_but_not_melee(self):
        self.assertEqual(
            adjusted_attack_roll(15, "storm", ranged=True, exposed=True),
            11,
        )
        self.assertEqual(
            adjusted_attack_roll(15, "storm", ranged=False, exposed=True),
            15,
        )
        self.assertEqual(
            adjusted_attack_roll(15, "storm", ranged=True, exposed=False),
            15,
        )

    def test_weather_concealment_improves_escape_without_exceeding_cap(self):
        self.assertAlmostEqual(flee_success_chance(0.70, "storm", exposed=True), 0.88)
        self.assertAlmostEqual(flee_success_chance(0.90, "duststorm", exposed=True), 0.95)
        self.assertAlmostEqual(flee_success_chance(0.70, "storm", exposed=False), 0.70)

    def test_heavy_rain_can_disrupt_fire_magic_only_when_exposed(self):
        self.assertTrue(
            fire_spell_disrupted("storm", 0.10, element="fire", exposed=True)
        )
        self.assertFalse(
            fire_spell_disrupted("storm", 0.10, element="arcane", exposed=True)
        )
        self.assertFalse(
            fire_spell_disrupted("storm", 0.10, element="fire", exposed=False)
        )

    def test_weather_surfaces_distinguish_soft_ground_from_hard_surface(self):
        muddy = surface_condition(("deep_forest", "trail"), "rain", exposed=True)
        slick = surface_condition(("gothic", "city_gate"), "rain", exposed=True)
        self.assertIsNotNone(muddy)
        self.assertIsNotNone(slick)
        self.assertEqual(muddy.key, "mud")
        self.assertEqual(slick.key, "slick")
        self.assertGreater(muddy.travel_delay_seconds, slick.travel_delay_seconds)

    def test_indoor_and_underground_tags_block_direct_weather_mechanics(self):
        self.assertFalse(room_is_weather_exposed(("cathedral", "clerical_order")))
        self.assertFalse(room_is_weather_exposed(("underground", "roots")))
        self.assertTrue(room_is_weather_exposed(("deep_forest", "tracks")))

    def test_first_night_of_major_season_gets_special_sky_text(self):
        self.assertIn(
            "first winter night",
            seasonal_sky_text("winter", 1, "night", "waning").lower(),
        )
        self.assertEqual(seasonal_sky_text("winter", 2, "day", "full"), "")

    def test_ranged_equipment_metadata_is_explicit(self):
        self.assertTrue(EquipmentItem("Hunting Bow", "weapon", attack_style="ranged").is_ranged)
        self.assertFalse(EquipmentItem("Iron Sword", "weapon").is_ranged)

    def test_weather_effect_table_marks_storm_as_severe(self):
        effects = effects_for_weather("storm")
        self.assertTrue(effects.severe)
        self.assertEqual(effects.ranged_attack_penalty, 4)
        self.assertGreater(effects.fire_disruption_chance, 0)

    def test_clear_weather_cannot_jump_directly_to_a_severe_front(self):
        candidates = _transition_candidates(TEMPERATE, "clear")
        self.assertIn("cloudy", candidates)
        self.assertNotIn("storm", candidates)
        self.assertNotIn("rain", candidates)

    def test_troll_mixed_forest_tundra_biome_uses_snow_capable_profile(self):
        profile = profile_for_biome("deep forests, wilderness, and tundra")
        self.assertIs(profile, WILDERNESS)
        self.assertIn("snow", profile.states)


class WeatherWorldEventTests(unittest.TestCase):
    def test_stormwake_is_a_distinct_rare_weather_event(self):
        state = RoomStateStore()
        state.set_weather("human_kingdom", "storm")
        service = AstralisWeatherService(rng=FixedLowRoll())
        event = service._roll_phenomenon(
            "human_kingdom",
            "Human Kingdom",
            state,
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.phenomenon_key, "stormwake")
        self.assertEqual(event.category, "weather_phenomenon")
        self.assertEqual(event.old_weather, event.new_weather)

    def test_blackwall_guard_seeks_authored_shelter_during_storm(self):
        manager = MobileNpcManager(definitions=(BLACKWALL_GUARD,))
        manager.regional_pools.clear()
        manager._regional_next_spawn_tick.clear()
        state = manager.states[BLACKWALL_GUARD.key]
        state.current_room_key = "human_training_yard"
        state.patrol_index = 2

        movements = manager.tick(
            rng=random.Random(1),
            hour=12,
            weather_provider=lambda _region_key: "storm",
        )
        self.assertEqual(len(movements), 1)
        movement = movements[0]
        self.assertEqual(movement.reason, "sheltering")
        self.assertEqual(movement.destination_room_key, "human_outer_drill_road")


if __name__ == "__main__":
    unittest.main()
