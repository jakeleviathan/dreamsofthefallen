from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.ability_mastery as mastery
from mud.database import Database
from mud.mechanics import AbilityDefinition, CombatantState
from mud.stats import CharacterStats


class _Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.active_enemy = None
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "human",
            current_hp=20,
            max_hp=20,
            current_mana=30,
            max_mana=30,
            auto_attack_interval=3.0,
            stats=CharacterStats(love=2, mind=2),
        )

    async def send(self, text: str) -> None:
        self.outputs.append(text)


class AbilityMasteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp.name) / "mastery.db")
        account = self.database.create_account("mastery", "x")
        self.character = self.database.create_character(account.id, "MasteryTester", "human", "priest")
        self.session = _Session(self.database, self.character)

    def tearDown(self):
        self.temp.cleanup()

    def test_mastery_uses_increasing_triangular_thresholds(self):
        self.assertEqual(mastery.xp_for_mastery_level(1), 0)
        self.assertEqual(mastery.xp_for_mastery_level(10), 45)
        self.assertEqual(mastery.xp_for_mastery_level(50), 1225)
        self.assertEqual(mastery.xp_for_mastery_level(100), 4950)
        self.assertEqual(mastery.mastery_level_for_xp(0), 1)
        self.assertEqual(mastery.mastery_level_for_xp(4), 3)
        self.assertEqual(mastery.mastery_level_for_xp(45), 10)
        self.assertEqual(mastery.mastery_level_for_xp(999999), 100)

    def test_meaningful_use_awards_skill_xp_and_announces_new_band(self):
        ability = AbilityDefinition(
            key="practice_heal",
            name="Practice Heal",
            category="healing",
            mana_cost=5,
        )
        self.database.record_ability_use(self.character.id, ability.key, skill_xp_gain=44)

        mastery.begin_use(self.session, ability)
        mastery.mark_healing_practice(self.session, 5)
        state = asyncio.run(mastery.commit_use(self.session))

        self.assertIsNotNone(state)
        self.assertEqual(state.skill_xp, 45)
        self.assertEqual(state.level, 10)
        self.assertEqual(state.band, "Practiced")
        self.assertEqual(state.uses, 2)
        self.assertIn("Practice Heal mastery: Practiced", "".join(self.session.outputs))

    def test_empty_or_idle_use_counts_as_use_but_not_skill_xp(self):
        ability = AbilityDefinition(key="idle_heal", name="Idle Heal", category="healing")
        mastery.begin_use(self.session, ability)
        state = asyncio.run(mastery.commit_use(self.session))

        self.assertEqual(state.uses, 1)
        self.assertEqual(state.skill_xp, 0)
        self.assertEqual(state.level, 1)

    def test_fixed_effect_ability_never_gains_mastery_xp(self):
        ability = AbilityDefinition(
            key="fixed_ward",
            name="Fixed Ward",
            category="self_protection",
            skill_improves_effectiveness=False,
        )
        mastery.begin_use(self.session, ability)
        mastery.mark_meaningful(self.session)
        state = asyncio.run(mastery.commit_use(self.session))

        self.assertEqual(state.uses, 1)
        self.assertEqual(state.skill_xp, 0)
        self.assertEqual(mastery.scale_power(self.session, ability, 20), 20)

    def test_blessing_and_restoring_light_have_distinct_curves(self):
        blessing = AbilityDefinition(
            key="blessing_of_resolve",
            name="Blessing of Resolve",
            mana_cost=5,
            category="ally_buff",
        )
        restoring = AbilityDefinition(
            key="restoring_light",
            name="Restoring Light",
            mana_cost=4,
            category="healing",
        )
        # Put both abilities at mastery 100 without changing their use semantics.
        self.database.record_ability_use(self.character.id, blessing.key, skill_xp_gain=4950)
        self.database.record_ability_use(self.character.id, restoring.key, skill_xp_gain=4950)

        self.assertEqual(mastery.flat_bonus(self.session, blessing), 4)
        self.assertEqual(round(mastery.duration_bonus(self.session, blessing)), 40)
        self.assertEqual(mastery.effective_mana_cost(self.session, blessing), 3)
        self.assertEqual(mastery.scale_power(self.session, restoring, 20), 29)
        self.assertEqual(mastery.effective_mana_cost(self.session, restoring), 1)

    def test_trivial_enemy_does_not_train_offensive_mastery(self):
        ability = AbilityDefinition(key="test_bolt", name="Test Bolt", category="spell_damage")
        with self.database.connect() as db:
            db.execute("UPDATE characters SET level = 20 WHERE id = ?", (self.character.id,))
        self.character = self.database.get_character_by_name(self.character.name)
        self.session.character = self.character
        self.session.active_enemy = SimpleNamespace(
            definition=SimpleNamespace(level=1, xp_reward=5, tutorial=False)
        )

        mastery.begin_use(self.session, ability)
        mastery.mark_damage_practice(self.session, 10, self.session.active_enemy)
        state = asyncio.run(mastery.commit_use(self.session))

        self.assertEqual(state.uses, 1)
        self.assertEqual(state.skill_xp, 0)

    def test_level_appropriate_enemy_trains_offensive_mastery(self):
        ability = AbilityDefinition(key="test_bolt", name="Test Bolt", category="spell_damage")
        with self.database.connect() as db:
            db.execute("UPDATE characters SET level = 20 WHERE id = ?", (self.character.id,))
        self.character = self.database.get_character_by_name(self.character.name)
        self.session.character = self.character
        self.session.active_enemy = SimpleNamespace(
            definition=SimpleNamespace(level=18, xp_reward=200, tutorial=False)
        )

        mastery.begin_use(self.session, ability)
        mastery.mark_damage_practice(self.session, 10, self.session.active_enemy)
        state = asyncio.run(mastery.commit_use(self.session))

        self.assertEqual(state.skill_xp, 1)

    def test_progress_summary_explains_next_skill_level(self):
        self.database.record_ability_use(self.character.id, "blessing_of_resolve", skill_xp_gain=4)
        text = mastery.mastery_summary(
            self.database, self.character.id, "blessing_of_resolve"
        )
        self.assertIn("Novice 3/100", text)
        self.assertIn("4 skill XP", text)
        self.assertIn("2 to next skill level", text)


if __name__ == "__main__":
    unittest.main()
