from __future__ import annotations

import unittest

import server  # noqa: F401 - production import installs the real class progression
from mud.mechanics import PROGRESSION_RULES, class_abilities_for_level
from mud.progression_coverage import (
    AUDIT_MAX_LEVEL,
    CONTENT_BANDS,
    CURRENT_AUTHORED_ZONE_CEILING,
    CURRENT_CLASS_ABILITY_CEILING,
    HARD_LEVEL_CAP,
    level_coverage,
    progression_summary,
)


class ProgressionCoverageTests(unittest.TestCase):
    def test_xp_curve_round_trips_every_level_one_through_sixty(self):
        previous_floor = -1
        for level in range(1, AUDIT_MAX_LEVEL + 1):
            floor = PROGRESSION_RULES.cumulative_xp_for_level(level)
            self.assertGreater(floor, previous_floor)
            self.assertEqual(PROGRESSION_RULES.level_for_experience(floor), level)
            if level < AUDIT_MAX_LEVEL:
                next_floor = PROGRESSION_RULES.cumulative_xp_for_level(level + 1)
                self.assertEqual(PROGRESSION_RULES.level_for_experience(next_floor - 1), level)
            previous_floor = floor

    def test_all_five_classes_are_legal_at_every_audited_level(self):
        non_priests = ("brute", "wizard", "druid", "necromancer")
        for level in range(1, AUDIT_MAX_LEVEL + 1):
            for class_key in non_priests:
                abilities = class_abilities_for_level(class_key, level)
                self.assertTrue(abilities, (class_key, level))
                self.assertTrue(all((ability.unlock_level or 1) <= level for ability in abilities))
            for deity_key in ("zerjz", "tenebrous", "leviathan"):
                abilities = class_abilities_for_level("priest", level, deity_key)
                self.assertTrue(abilities, ("priest", deity_key, level))
                self.assertTrue(all((ability.unlock_level or 1) <= level for ability in abilities))

    def test_current_class_unlock_ceiling_matches_live_ability_registry(self):
        unlocks = []
        for class_key in ("brute", "wizard", "druid", "necromancer"):
            unlocks.extend(
                ability.unlock_level or 1
                for ability in class_abilities_for_level(class_key, AUDIT_MAX_LEVEL)
            )
        for deity_key in ("zerjz", "tenebrous", "leviathan"):
            unlocks.extend(
                ability.unlock_level or 1
                for ability in class_abilities_for_level("priest", AUDIT_MAX_LEVEL, deity_key)
            )
        self.assertEqual(max(unlocks), CURRENT_CLASS_ABILITY_CEILING)

    def test_levels_beyond_current_authored_zone_ceiling_are_marked_unsupported(self):
        self.assertTrue(level_coverage(CURRENT_AUTHORED_ZONE_CEILING).authored_zone_support)
        self.assertFalse(level_coverage(CURRENT_AUTHORED_ZONE_CEILING + 1).authored_zone_support)
        self.assertFalse(level_coverage(AUDIT_MAX_LEVEL).authored_zone_support)

    def test_current_content_bands_do_not_claim_content_above_level_eleven(self):
        self.assertEqual(max(band.end_level for band in CONTENT_BANDS), CURRENT_AUTHORED_ZONE_CEILING)

    def test_audit_does_not_invent_a_level_sixty_cap(self):
        summary = progression_summary()
        self.assertIsNone(HARD_LEVEL_CAP)
        self.assertIsNone(summary["hard_level_cap"])
        self.assertEqual(summary["audited_through_level"], 60)
        self.assertEqual(summary["xp_required_for_level_60"], 7_122_475)


if __name__ == "__main__":
    unittest.main()
