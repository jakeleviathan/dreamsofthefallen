from __future__ import annotations

import unittest
from types import SimpleNamespace

from mud.corpse_decay import (
    corpse_decay_description,
    corpse_decay_label,
    corpse_decay_state,
    decay_family_for,
)


class CorpseDecayVocabularyTests(unittest.TestCase):
    def _corpse(
        self,
        enemy_key: str = "marsh_razorcrab",
        enemy_name: str = "Marsh Razorcrab",
        *,
        created_at: float = 100.0,
        expires_at: float = 400.0,
    ):
        return SimpleNamespace(
            enemy_key=enemy_key,
            enemy_name=enemy_name,
            created_at=created_at,
            expires_at=expires_at,
        )

    def test_living_corpse_walks_through_five_relative_stages(self):
        corpse = self._corpse()
        checkpoints = (
            (100.0, "fresh"),
            (176.0, "cooling"),
            (251.0, "stinking"),
            (326.0, "rotting"),
            (371.0, "collapsing"),
        )
        for moment, expected in checkpoints:
            with self.subTest(moment=moment):
                self.assertEqual(corpse_decay_label(corpse, now=moment), expected)

    def test_decay_vocabulary_changes_with_creature_type(self):
        examples = (
            ("grave_wight", "Grave Wight", "undead", "crumbling"),
            ("clockwork_sentry", "Clockwork Sentry", "construct", "inert"),
            ("spore_husk", "Spore Husk", "fungal", "souring"),
            ("moonfire_wisp", "Moonfire Wisp", "arcane", "fading"),
            ("infernal_imp", "Infernal Imp", "arcane", "fading"),
            ("fen_leech_cluster", "Fen Leech Cluster", "living", "stinking"),
        )
        for key, name, family, label in examples:
            with self.subTest(key=key):
                corpse = self._corpse(key, name)
                state = corpse_decay_state(corpse, now=251.0)
                self.assertEqual(state.family, family)
                self.assertEqual(state.adjective, label)

    def test_family_detection_uses_key_or_display_name(self):
        self.assertEqual(decay_family_for("enemy_42", "Rusting Automaton"), "construct")
        self.assertEqual(decay_family_for("enemy_43", "Ashen Revenant"), "undead")
        self.assertEqual(decay_family_for("enemy_44", "Mycelial Stalker"), "fungal")
        self.assertEqual(decay_family_for("enemy_45", "Astral Apparition"), "arcane")
        self.assertEqual(decay_family_for("enemy_46", "Marsh Razorcrab"), "living")

    def test_long_lived_boss_uses_same_relative_decay_progression(self):
        ordinary = self._corpse(created_at=100.0, expires_at=400.0)
        boss = self._corpse(
            "razorcrab_matriarch",
            "Razorcrab Matriarch",
            created_at=100.0,
            expires_at=1000.0,
        )
        self.assertEqual(corpse_decay_label(ordinary, now=251.0), "stinking")
        self.assertEqual(corpse_decay_label(boss, now=553.0), "stinking")

    def test_inspection_description_stays_in_world_instead_of_exposing_seconds(self):
        corpse = self._corpse()
        description = corpse_decay_description(corpse, now=251.0)
        self.assertIn("stink", description.casefold())
        self.assertNotIn("seconds", description.casefold())
        self.assertNotIn("minutes", description.casefold())


if __name__ == "__main__":
    unittest.main()
