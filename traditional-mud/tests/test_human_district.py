import unittest
from datetime import datetime

from mud.crafting import ITEMS_BY_KEY
from mud.human_district import (
    BLACK_LANTERN_PROVISIONS,
    CINDERHOOK_SALVAGE,
    HUMAN_BUSINESSES,
    HUMAN_DISTRICT_ROOMS,
    HUMAN_REGION_KEY,
    HumanDistrictService,
    QUARTERMASTERS_CAGE,
    SAINT_ORRAS_REMEDIES,
)
from mud.room_engine import PersistenceScope, RoomStateStore


class HumanDistrictLivingWorldTests(unittest.TestCase):
    def setUp(self):
        self.state = RoomStateStore()
        self.service = HumanDistrictService()

    def test_all_business_stock_points_to_real_items(self):
        for business in HUMAN_BUSINESSES:
            with self.subTest(business=business.key):
                self.assertTrue(business.proprietor)
                self.assertTrue(business.stock_item_keys)
                for item_key in business.stock_item_keys:
                    self.assertIn(item_key, ITEMS_BY_KEY)

    def test_initialize_sets_real_door_state_from_posted_hours(self):
        self.service.initialize(datetime(2026, 9, 9, 10, 0), self.state)
        for business in HUMAN_BUSINESSES:
            with self.subTest(business=business.key):
                door = self.state.door_state(business.door_key)
                self.assertEqual(door.open, business.scheduled_open(10))
                self.assertEqual(door.locked, not business.scheduled_open(10))

    def test_black_lantern_closes_and_locks_at_22(self):
        self.service.initialize(datetime(2026, 9, 9, 21, 59), self.state)
        self.assertTrue(self.state.door_state(BLACK_LANTERN_PROVISIONS.door_key).open)

        events = self.service.sync(datetime(2026, 9, 9, 22, 0), self.state)
        door = self.state.door_state(BLACK_LANTERN_PROVISIONS.door_key)
        self.assertFalse(door.open)
        self.assertTrue(door.locked)
        categories = {event.category for event in events}
        self.assertIn("business_close", categories)
        self.assertIn("cathedral_bell", categories)
        self.assertIn("guard_shift", categories)

    def test_guard_shift_occurs_at_six_fourteen_and_twenty_two(self):
        for shift_hour in (6, 14, 22):
            with self.subTest(hour=shift_hour):
                state = RoomStateStore()
                service = HumanDistrictService()
                service.initialize(datetime(2026, 9, 9, shift_hour - 1, 59), state)
                events = service.sync(datetime(2026, 9, 9, shift_hour, 0), state)
                shifts = [event for event in events if event.category == "guard_shift"]
                self.assertEqual(len(shifts), 1)
                self.assertEqual(
                    set(shifts[0].room_keys),
                    {"human_demon_gate", "human_outer_drill_road", "human_training_yard"},
                )

    def test_hour_change_broadcasts_cathedral_bells_to_human_district(self):
        self.service.initialize(datetime(2026, 9, 9, 10, 59), self.state)
        events = self.service.sync(datetime(2026, 9, 9, 11, 0), self.state)
        bells = [event for event in events if event.category == "cathedral_bell"]
        self.assertEqual(len(bells), 1)
        self.assertEqual(set(bells[0].room_keys), set(HUMAN_DISTRICT_ROOMS))
        self.assertIn("11 deep strokes", bells[0].text)

    def test_rain_closes_temporary_shutters_without_persisting_them(self):
        self.service.initialize(datetime(2026, 9, 9, 10, 0), self.state)
        self.state.set_weather(HUMAN_REGION_KEY, "rain")
        events = self.service.sync(datetime(2026, 9, 9, 10, 1), self.state)

        rain_events = [event for event in events if event.category == "rain_shutters_close"]
        self.assertEqual(len(rain_events), len(HUMAN_BUSINESSES))
        for business in HUMAN_BUSINESSES:
            flag = f"{business.key}_rain_shutters_closed"
            self.assertIn(
                flag,
                self.state.flags_for(business.room_key, PersistenceScope.TEMPORARY),
            )
        self.assertNotIn("temporary_flags", self.state.snapshot_world_state())

    def test_shutters_reopen_when_rain_clears(self):
        self.state.set_weather(HUMAN_REGION_KEY, "rain")
        self.service.initialize(datetime(2026, 9, 9, 10, 0), self.state)
        self.state.set_weather(HUMAN_REGION_KEY, "clear")
        events = self.service.sync(datetime(2026, 9, 9, 10, 1), self.state)
        self.assertEqual(
            len([event for event in events if event.category == "rain_shutters_open"]),
            len(HUMAN_BUSINESSES),
        )
        for business in HUMAN_BUSINESSES:
            self.assertFalse(self.service.shutters_closed(business, self.state))

    def test_proprietor_reopens_player_closed_door_during_business_hours(self):
        self.service.initialize(datetime(2026, 9, 9, 10, 0), self.state)
        business = BLACK_LANTERN_PROVISIONS
        message = self.service.close_door(business, self.state, 10)
        self.assertIn("will not stay that way", message)
        self.assertFalse(self.state.door_state(business.door_key).open)

        events = self.service.sync(datetime(2026, 9, 9, 10, 1), self.state)
        self.assertTrue(self.state.door_state(business.door_key).open)
        self.assertIn("business_reopen", {event.category for event in events})

    def test_closed_business_cannot_be_opened_after_hours(self):
        self.service.initialize(datetime(2026, 9, 9, 23, 0), self.state)
        text = self.service.open_door(BLACK_LANTERN_PROVISIONS, self.state, 23)
        self.assertIn("locked", text.lower())
        self.assertFalse(self.state.door_state(BLACK_LANTERN_PROVISIONS.door_key).open)

    def test_each_business_has_distinct_atmosphere_and_player_interactions(self):
        self.service.initialize(datetime(2026, 9, 9, 10, 0), self.state)
        for business in HUMAN_BUSINESSES:
            with self.subTest(business=business.key):
                self.assertTrue(self.service.examine(business, self.state, 10))
                self.assertIn(business.name, self.service.listen(business, self.state, 10))
                self.assertIn(business.name, self.service.smell(business, self.state, 10))
                if business.scheduled_open(10):
                    self.assertEqual(self.service.talk(business, self.state, 10), business.greeting)

    def test_businesses_cover_four_different_human_district_locations(self):
        self.assertEqual(
            {business.room_key for business in HUMAN_BUSINESSES},
            {
                "human_ashen_way",
                "human_cathedral_square",
                "human_training_yard",
                "human_cinder_lane",
            },
        )
        self.assertEqual(
            {business.key for business in HUMAN_BUSINESSES},
            {
                BLACK_LANTERN_PROVISIONS.key,
                SAINT_ORRAS_REMEDIES.key,
                QUARTERMASTERS_CAGE.key,
                CINDERHOOK_SALVAGE.key,
            },
        )


if __name__ == "__main__":
    unittest.main()
