import unittest

from mud.astralis_calendar import (
    ASTRALIS_DAYS_PER_YEAR,
    MOON_CYCLE_DAYS,
    MOON_PHASES,
    SEASONS,
    calendar_for_day,
    regional_calendar_context,
)
from mud.astralis_time import AstralisMoment, _seasonally_weighted_candidates


class AstralisCalendarTests(unittest.TestCase):
    def test_year_is_exactly_ninety_days(self):
        self.assertEqual(ASTRALIS_DAYS_PER_YEAR, 90)
        self.assertEqual(sum(season.length_days for season in SEASONS), 90)
        self.assertEqual(SEASONS[0].start_day, 1)
        self.assertEqual(SEASONS[-1].end_day, 90)

    def test_classic_four_seasons_cover_year_without_gaps(self):
        self.assertEqual([season.key for season in SEASONS], ["spring", "summer", "autumn", "winter"])
        covered = []
        for season in SEASONS:
            covered.extend(range(season.start_day, season.end_day + 1))
        self.assertEqual(covered, list(range(1, 91)))

    def test_year_rollover(self):
        last = calendar_for_day(90)
        first_next = calendar_for_day(91)
        self.assertEqual((last.year, last.day_of_year), (1, 90))
        self.assertEqual((first_next.year, first_next.day_of_year), (2, 1))
        self.assertEqual(first_next.season_key, "spring")

    def test_season_boundaries(self):
        expected = {
            1: "spring",
            23: "spring",
            24: "summer",
            45: "summer",
            46: "autumn",
            68: "autumn",
            69: "winter",
            90: "winter",
        }
        for day, season in expected.items():
            with self.subTest(day=day):
                self.assertEqual(calendar_for_day(day).season_key, season)

    def test_minimalist_four_phase_moon_cycle(self):
        self.assertEqual(MOON_PHASES, ("new", "waxing", "full", "waning"))
        self.assertEqual(MOON_CYCLE_DAYS, 28)
        self.assertEqual(calendar_for_day(1).moon_phase, "new")
        self.assertEqual(calendar_for_day(8).moon_phase, "waxing")
        self.assertEqual(calendar_for_day(15).moon_phase, "full")
        self.assertEqual(calendar_for_day(22).moon_phase, "waning")
        self.assertEqual(calendar_for_day(29).moon_phase, "new")

    def test_moon_does_not_reset_at_new_year(self):
        self.assertNotEqual(calendar_for_day(90).moon_cycle_day, 28)
        self.assertEqual(calendar_for_day(91).moon_cycle_day, ((91 - 1) % 28) + 1)

    def test_astralis_moment_exposes_calendar_values(self):
        moment = AstralisMoment(day_number=46, hour=19, minute=30, total_minutes=0)
        self.assertEqual(moment.year, 1)
        self.assertEqual(moment.day_of_year, 46)
        self.assertEqual(moment.season, "autumn")
        self.assertEqual(moment.season_name, "Autumn")
        self.assertIn(moment.moon_phase, MOON_PHASES)
        self.assertIn("Year 1", moment.calendar_display)
        self.assertIn("Autumn", moment.calendar_display)

    def test_regions_can_read_season_and_moon_context(self):
        context = regional_calendar_context("moon_peaks", 69)
        self.assertEqual(context.region_key, "moon_peaks")
        self.assertEqual(context.season, "winter")
        self.assertIn(context.moon_phase, MOON_PHASES)

    def test_season_bias_only_duplicates_existing_weather_candidates(self):
        candidates = ("clear", "cloudy", "mist", "rain")
        spring = _seasonally_weighted_candidates(candidates, "spring")
        winter = _seasonally_weighted_candidates(candidates, "winter")
        self.assertGreater(spring.count("rain"), candidates.count("rain"))
        self.assertGreater(winter.count("cloudy"), candidates.count("cloudy"))
        self.assertNotIn("snow", winter)


if __name__ == "__main__":
    unittest.main()
