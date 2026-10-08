import unittest
from datetime import datetime, timedelta, timezone
from mud.lanternkeeper_wisp import Lanternkeeper, LanternWisp, wisp_room_entities

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


class LanternWispTests(unittest.TestCase):
    def setUp(self):
        self.member = Lanternkeeper(stripe_status="active", current_period_end=NOW + timedelta(days=1))
        self.wisp = LanternWisp()

    def test_active_subscription_controls_visibility(self):
        self.assertFalse(self.wisp.visible(self.member, True, NOW))
        self.wisp.summon(self.member, NOW)
        self.assertTrue(self.wisp.visible(self.member, True, NOW))
        self.assertFalse(self.wisp.visible(self.member, False, NOW))
        self.assertFalse(self.wisp.visible(self.member, True, NOW + timedelta(days=2)))

    def test_dormancy_preserves_cosmetics(self):
        self.wisp.set_color("rose")
        self.wisp.set_name("Glimmer")
        self.wisp.unlock_appearance("starlight")
        self.wisp.set_appearance("starlight")
        self.wisp.summon(self.member, NOW)
        self.assertFalse(self.wisp.visible(Lanternkeeper(), True, NOW))
        self.assertEqual((self.wisp.color, self.wisp.name, self.wisp.appearance), ("rose", "Glimmer", "starlight"))

    def test_room_entity_not_mob(self):
        self.wisp.summon(self.member, NOW)
        entities = wisp_room_entities([(1, "Prime", True, "crossroads")],
                                     {1: self.member}, {1: self.wisp}, NOW)
        self.assertEqual(entities[0]["label"], "Prime's wisp")
        self.assertEqual(entities[0]["type"], "lantern_wisp")
        self.assertNotIn("combat", entities[0])

    def test_unearned_appearance_rejected(self):
        self.assertIn("not been unlocked", self.wisp.set_appearance("starlight"))

    def test_invalid_name_rejected(self):
        self.assertIn("Choose a name", self.wisp.set_name("><script"))


if __name__ == "__main__":
    unittest.main()
