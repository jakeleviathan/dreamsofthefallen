import random
import tempfile
import unittest
from pathlib import Path

from mud.appearance import defaults_for_race, reflection_text, validate_choice
from mud.appearance_storage import get_appearance, set_appearance
from mud.astralis_human_district import AstralisHumanDistrictService
from mud.astralis_time import (
    ASTRALIS_EPOCH_MINUTES,
    REAL_EPOCH_SECONDS,
    REAL_SECONDS_PER_ASTRALIS_DAY,
    REAL_SECONDS_PER_ASTRALIS_HOUR,
    AstralisClock,
    AstralisWeatherService,
    puddle_available,
)
from mud.database import Database
from mud.human_district import BLACK_LANTERN_PROVISIONS, QUARTERMASTERS_CAGE
from mud.room_engine import RoomStateStore


class AstralisClockTests(unittest.TestCase):
    def test_four_real_hours_equal_one_full_astralis_day(self):
        clock = AstralisClock()
        start = clock.now(REAL_EPOCH_SECONDS)
        later = clock.now(REAL_EPOCH_SECONDS + REAL_SECONDS_PER_ASTRALIS_DAY)
        self.assertEqual((start.hour, start.minute), (6, 0))
        self.assertEqual((later.hour, later.minute), (6, 0))
        self.assertEqual(later.day_number, start.day_number + 1)

    def test_one_astralis_hour_is_ten_real_minutes(self):
        clock = AstralisClock()
        start = clock.now(REAL_EPOCH_SECONDS)
        later = clock.now(REAL_EPOCH_SECONDS + REAL_SECONDS_PER_ASTRALIS_HOUR)
        self.assertEqual(later.total_hours, start.total_hours + 1)
        self.assertEqual(later.hour, 7)

    def test_time_phases_are_authored(self):
        clock = AstralisClock()
        self.assertEqual(clock.now(REAL_EPOCH_SECONDS).phase, "dawn")
        noon_real = REAL_EPOCH_SECONDS + 6 * REAL_SECONDS_PER_ASTRALIS_HOUR
        self.assertEqual(clock.now(noon_real).phase, "day")


class WeatherAndPuddleTests(unittest.TestCase):
    def test_weather_only_checks_when_an_astralis_hour_changes(self):
        state = RoomStateStore()
        clock = AstralisClock()
        service = AstralisWeatherService(rng=random.Random(7))
        first = clock.now(REAL_EPOCH_SECONDS)
        service.initialize(first, state)
        before = dict(state.region_weather)
        same_hour = clock.now(REAL_EPOCH_SECONDS + 30)
        self.assertEqual(service.sync(same_hour, state), ())
        self.assertEqual(state.region_weather, before)

    def test_puddles_are_weather_driven_and_room_specific(self):
        state = RoomStateStore()
        state.set_weather("human_kingdom", "rain")
        self.assertTrue(puddle_available("human_ashen_way", "human_kingdom", state))
        self.assertFalse(puddle_available("human_grand_cathedral", "human_kingdom", state))
        state.set_weather("human_kingdom", "clear")
        self.assertFalse(puddle_available("human_ashen_way", "human_kingdom", state))


class ReflectionAppearanceTests(unittest.TestCase):
    def test_sporekin_and_undead_have_race_specific_reflection_choices(self):
        self.assertIn("cap_pattern", defaults_for_race("sporekin"))
        self.assertIn("bone_finish", defaults_for_race("undead"))
        self.assertIn("hair_style", defaults_for_race("human"))

    def test_invalid_reflection_choice_is_rejected(self):
        valid, _ = validate_choice("human", "hair_style", "braided")
        invalid, message = validate_choice("human", "hair_style", "made-of-fire")
        self.assertTrue(valid)
        self.assertFalse(invalid)
        self.assertIn("Choose one of", message)

    def test_appearance_choices_persist_in_character_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "mud.db")
            with database.connect() as db:
                account_id = db.execute(
                    "INSERT INTO accounts (name, password_hash) VALUES ('reflection_test', 'x')"
                ).lastrowid
                character_id = db.execute(
                    "INSERT INTO characters (account_id, name, race, character_class) VALUES (?, 'Mirror', 'human', 'brute')",
                    (account_id,),
                ).lastrowid
            set_appearance(database, int(character_id), "hair_style", "braided")
            stored = get_appearance(database, int(character_id))
            self.assertEqual(stored["hair_style"], "braided")
            self.assertIn("braided", reflection_text("Mirror", "human", stored))


class AstralisBusinessLeewayTests(unittest.TestCase):
    def test_daily_leeway_is_stable_within_same_day(self):
        service = AstralisHumanDistrictService()
        first = service.effective_hours(BLACK_LANTERN_PROVISIONS, 42, "clear")
        second = service.effective_hours(BLACK_LANTERN_PROVISIONS, 42, "clear")
        self.assertEqual(first, second)

    def test_storms_can_shorten_civilian_business_day(self):
        service = AstralisHumanDistrictService()
        clear_open, clear_close = service.effective_hours(BLACK_LANTERN_PROVISIONS, 42, "clear")
        storm_open, storm_close = service.effective_hours(BLACK_LANTERN_PROVISIONS, 42, "storm")
        self.assertGreaterEqual(storm_open, clear_open)
        self.assertLessEqual(storm_close, clear_close)

    def test_training_quartermaster_does_not_take_extra_storm_penalty(self):
        service = AstralisHumanDistrictService()
        self.assertEqual(
            service.effective_hours(QUARTERMASTERS_CAGE, 42, "clear"),
            service.effective_hours(QUARTERMASTERS_CAGE, 42, "storm"),
        )


if __name__ == "__main__":
    unittest.main()
