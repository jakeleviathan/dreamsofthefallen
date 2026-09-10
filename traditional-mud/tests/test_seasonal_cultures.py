import unittest

from mud.astralis_calendar import calendar_for_day
from mud.astralis_time import AstralisMoment
from mud.character_options import RACES_BY_KEY
from mud.seasonal_cultures import (
    ANCHORS_BY_RACE,
    SEASONAL_CULTURE_ANCHORS,
    SeasonalCultureService,
    active_anchor_for_region,
    find_active_anchor,
)
from mud.world_data import REGIONS_BY_KEY


class SeasonalCultureAnchorTests(unittest.TestCase):
    def test_exactly_one_anchor_exists_for_every_playable_race(self):
        self.assertEqual(len(SEASONAL_CULTURE_ANCHORS), 8)
        self.assertEqual(set(ANCHORS_BY_RACE), set(RACES_BY_KEY))
        self.assertEqual(len({anchor.race_key for anchor in SEASONAL_CULTURE_ANCHORS}), 8)

    def test_every_anchor_targets_an_authored_home_region_and_calendar_season(self):
        for anchor in SEASONAL_CULTURE_ANCHORS:
            with self.subTest(anchor=anchor.key):
                self.assertIn(anchor.region_key, REGIONS_BY_KEY)
                self.assertIn(anchor.season_key, {"spring", "summer", "autumn", "winter"})
                self.assertTrue(anchor.title)
                self.assertTrue(anchor.feature_name)
                self.assertTrue(anchor.ambient_text)
                self.assertTrue(anchor.examine_text)
                self.assertTrue(anchor.use_text)

    def test_known_race_region_mapping_is_preserved(self):
        expected = {
            "human": "human_kingdom",
            "forest_elf": "great_elf_forest",
            "moon_elf": "moon_peaks",
            "dwarf": "dwarven_mountain_industry",
            "goblin": "junk_city_and_swamps",
            "troll": "troll_strongholds",
            "undead": "desert_necropolis",
            "sporekin": "sporekin_underways",
        }
        self.assertEqual(
            {race: ANCHORS_BY_RACE[race].region_key for race in expected},
            expected,
        )

    def test_active_anchor_only_appears_in_its_authored_season(self):
        spring = calendar_for_day(1)
        winter = calendar_for_day(69)
        forest = ANCHORS_BY_RACE["forest_elf"]
        human = ANCHORS_BY_RACE["human"]

        self.assertEqual(active_anchor_for_region(forest.region_key, spring), forest)
        self.assertIsNone(active_anchor_for_region(forest.region_key, winter))
        self.assertEqual(active_anchor_for_region(human.region_key, winter), human)
        self.assertIsNone(active_anchor_for_region(human.region_key, spring))

    def test_feature_aliases_work_for_interaction_targeting(self):
        winter = calendar_for_day(69)
        human = ANCHORS_BY_RACE["human"]
        self.assertEqual(find_active_anchor(human.region_key, winter, "braziers"), human)
        self.assertEqual(find_active_anchor(human.region_key, winter, "Winter Hearths"), human)
        self.assertIsNone(find_active_anchor(human.region_key, calendar_for_day(1), "braziers"))

    def test_observation_flags_are_year_specific(self):
        anchor = ANCHORS_BY_RACE["sporekin"]
        self.assertNotEqual(anchor.observation_flag(1), anchor.observation_flag(2))
        self.assertIn("sporewake", anchor.observation_flag(3))
        self.assertIn("year:3", anchor.observation_flag(3))


class SeasonalCultureTransitionTests(unittest.TestCase):
    @staticmethod
    def moment(day_number: int) -> AstralisMoment:
        return AstralisMoment(
            day_number=day_number,
            hour=6,
            minute=0,
            total_minutes=(day_number - 1) * 1440 + 360,
        )

    def test_transition_into_autumn_starts_quieting(self):
        service = SeasonalCultureService()
        service.initialize(self.moment(45))
        events = service.sync(self.moment(46))
        starts = [event for event in events if event.category == "seasonal_anchor_start"]
        self.assertEqual([event.anchor_key for event in starts], ["quieting"])
        self.assertEqual(starts[0].region_key, "desert_necropolis")

    def test_transition_into_winter_starts_four_cultural_anchors(self):
        service = SeasonalCultureService()
        service.initialize(self.moment(68))
        events = service.sync(self.moment(69))
        starts = {event.anchor_key for event in events if event.category == "seasonal_anchor_start"}
        self.assertEqual(starts, {"blackwall_hearths", "long_moon", "deepfire_shift", "snow_trail"})
        ends = {event.anchor_key for event in events if event.category == "seasonal_anchor_end"}
        self.assertEqual(ends, {"quieting"})

    def test_transition_into_spring_starts_three_cultural_anchors(self):
        service = SeasonalCultureService()
        service.initialize(self.moment(90))
        events = service.sync(self.moment(91))
        starts = {event.anchor_key for event in events if event.category == "seasonal_anchor_start"}
        self.assertEqual(starts, {"firstgreen", "floodpick", "sporewake"})
        ends = {event.anchor_key for event in events if event.category == "seasonal_anchor_end"}
        self.assertEqual(ends, {"blackwall_hearths", "long_moon", "deepfire_shift", "snow_trail"})


if __name__ == "__main__":
    unittest.main()
