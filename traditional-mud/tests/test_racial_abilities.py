from __future__ import annotations

import asyncio
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import mud.character_options as character_options
from mud.combat import EnemyDefinition, EnemyState
from mud.database import Database
from mud.mechanics import CombatantState
from mud.racial_abilities import (
    RACIAL_ACTIVE_KEYS,
    RACIAL_TEXT,
    _use_racial,
    install_fast_learner_database_hook,
    install_racial_ability_definitions,
    long_view_armor_reduction,
)
from mud.stats import CharacterStats, RACE_STARTING_MODIFIERS


class FakeDatabase:
    def __init__(self):
        self.uses: list[str] = []

    def record_ability_use(self, _character_id: int, ability_key: str, skill_xp_gain: int = 1):
        self.uses.extend([ability_key] * skill_xp_gain)


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "RacialTest"
    race: str = "human"
    character_class: str = "wizard"
    deity_key: str | None = None
    level: int = 5
    current_room: str = "test_room"


class FakeSession:
    _racial_live_sessions: set[object] = set()

    def __init__(self, race: str):
        self.character = FakeCharacter(race=race)
        self.database = FakeDatabase()
        self.combatant = CombatantState(
            character_id=1,
            race_key=race,
            current_hp=20,
            max_hp=30,
            current_mana=20,
            max_mana=20,
            auto_attack_interval=2.5,
            stats=CharacterStats(might=6, grace=6, love=6, mind=6, hp=5),
        )
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.mobile_npcs = None
        self.mobile_npc_movement_callback = None
        self.ward_until = 0.0
        self.outputs: list[str] = []
        type(self)._racial_live_sessions.add(self)

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def _stop_combat(self):
        self.active_enemy = None


class RacialAbilityTests(unittest.TestCase):
    def setUp(self):
        install_racial_ability_definitions()
        FakeSession._racial_live_sessions = set()

    def test_all_eight_launch_races_have_locked_passive_and_at_will(self):
        expected = {
            "human": ("Fast Learner", "Adapt"),
            "forest_elf": ("Elven Grace", "Slipstep"),
            "moon_elf": ("Long View", "Reconsider"),
            "dwarf": ("Resilience", "Brace"),
            "goblin": ("Junkwise", "Scrounge"),
            "troll": ("Regeneration", "Bloodscent"),
            "undead": ("Unliving", "Stillness"),
            "sporekin": ("Deep Regeneration", "Chorus Bloom"),
        }
        self.assertEqual(set(RACIAL_ACTIVE_KEYS), set(expected))
        self.assertEqual(set(RACIAL_TEXT), set(expected))
        for race_key, names in expected.items():
            with self.subTest(race=race_key):
                race = character_options.RACES_BY_KEY[race_key]
                self.assertEqual((race.passive_name, race.ability_name), names)
                self.assertTrue(race.passive_description)
                self.assertTrue(race.ability_description)
                self.assertEqual(race.design_status, "racial_kit_locked")

    def test_human_fast_learner_is_exact_ten_percent_on_normal_use_cadence(self):
        install_fast_learner_database_hook()
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp) / "racial.db")
            account = db.create_account("racial_test", "not-a-real-hash")
            human = db.create_character(
                account.id,
                "HumanRacial",
                "human",
                "wizard",
                CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
            )
            elf = db.create_character(
                account.id,
                "ElfRacial",
                "forest_elf",
                "wizard",
                CharacterStats(might=5, grace=7, love=7, mind=5, hp=5),
            )
            for _ in range(10):
                db.record_ability_use(human.id, "coldfire_burst")
                db.record_ability_use(elf.id, "coldfire_burst")
            human_progress = next(
                row for row in db.list_ability_progress(human.id)
                if row["ability_key"] == "coldfire_burst"
            )
            elf_progress = next(
                row for row in db.list_ability_progress(elf.id)
                if row["ability_key"] == "coldfire_burst"
            )
            self.assertEqual(human_progress["uses"], 10)
            self.assertEqual(human_progress["skill_xp"], 11)
            self.assertEqual(elf_progress["skill_xp"], 10)

    def test_forest_elf_uses_existing_grace_bonus_and_slipstep_needs_no_room_content(self):
        self.assertEqual(RACE_STARTING_MODIFIERS["forest_elf"].grace, 2)
        session = FakeSession("forest_elf")
        asyncio.run(_use_racial(session))
        self.assertGreater(session._racial_slipstep_until, 0.0)
        self.assertGreater(session.ward_until, 0.0)
        text = " ".join(session.outputs).lower()
        self.assertIn("breaking away", text)
        self.assertNotIn("track", character_options.RACES_BY_KEY["forest_elf"].ability_description.lower())
        self.assertNotIn("hidden exit", character_options.RACES_BY_KEY["forest_elf"].ability_description.lower())

    def test_human_adapt_temporarily_adds_two_to_chosen_stat(self):
        session = FakeSession("human")
        before = session.combatant.stats.might
        asyncio.run(_use_racial(session, "might"))
        self.assertEqual(session.combatant.stats.might, before + 2)
        self.assertEqual(session._racial_adapt_stat, "might")

    def test_moon_elf_long_view_scales_only_while_focus_is_maintained(self):
        self.assertEqual(long_view_armor_reduction(4.9), 0)
        self.assertEqual(long_view_armor_reduction(5.0), 1)
        self.assertEqual(long_view_armor_reduction(10.0), 2)
        self.assertEqual(long_view_armor_reduction(20.0), 3)

    def test_reconsider_reduces_running_class_cooldowns_by_three_seconds(self):
        session = FakeSession("moon_elf")
        session.combatant.start_cooldown("coldfire_burst", 12.0)
        before = session.combatant.cooldowns["coldfire_burst"]
        asyncio.run(_use_racial(session))
        after = session.combatant.cooldowns["coldfire_burst"]
        self.assertAlmostEqual(before - after, 3.0, delta=0.1)
        self.assertIn("shorten by 3 seconds", " ".join(session.outputs).lower())

    def test_dwarf_brace_is_real_mitigation_without_breaking_equipment_ac_rule(self):
        session = FakeSession("dwarf")
        original_ac = session.combatant.armor_class
        asyncio.run(_use_racial(session))
        self.assertGreater(session.ward_until, 0.0)
        self.assertEqual(session.combatant.armor_class, original_ac)
        self.assertIn("equipment-derived", character_options.RACES_BY_KEY["dwarf"].ability_description)
        self.assertAlmostEqual(getattr(session, "racial_forced_movement_resistance", 0.0), 0.0)

    def test_goblin_scrounge_does_not_create_generic_free_loot(self):
        session = FakeSession("goblin")
        asyncio.run(_use_racial(session))
        text = " ".join(session.outputs).lower()
        self.assertIn("nothing here stands out", text)
        self.assertIn("never creates generic free loot", character_options.RACES_BY_KEY["goblin"].ability_description.lower())

    def test_troll_bloodscent_requires_a_wounded_target_and_reduces_armor(self):
        session = FakeSession("troll")
        definition = EnemyDefinition(
            key="test_enemy",
            name="Test Enemy",
            aliases=("enemy",),
            description="test",
            max_hp=20,
            armor_class=6,
            auto_attack_damage=2,
            auto_attack_interval=3.0,
            xp_reward=0,
        )
        session.active_enemy = EnemyState(definition, current_hp=9)
        asyncio.run(_use_racial(session))
        self.assertEqual(session.active_enemy.definition.armor_class, 4)
        self.assertIn("effective armor is reduced by 2", " ".join(session.outputs).lower())

    def test_undead_stillness_breaks_current_combat_attention(self):
        session = FakeSession("undead")
        definition = EnemyDefinition(
            key="test_enemy",
            name="Test Enemy",
            aliases=("enemy",),
            description="test",
            max_hp=20,
            armor_class=3,
            auto_attack_damage=2,
            auto_attack_interval=3.0,
            xp_reward=0,
        )
        session.active_enemy = EnemyState(definition)
        asyncio.run(_use_racial(session))
        self.assertIsNone(session.active_enemy)
        self.assertTrue(session._racial_stillness_active)
        self.assertGreater(session.ward_until, 0.0)

    def test_sporekin_chorus_bloom_heals_same_room_player_characters(self):
        caster = FakeSession("sporekin")
        ally = FakeSession("human")
        outsider = FakeSession("human")
        outsider.character.current_room = "somewhere_else"
        caster.combatant.current_hp = 20
        ally.combatant.current_hp = 20
        outsider.combatant.current_hp = 20
        asyncio.run(_use_racial(caster))
        self.assertEqual(caster.combatant.current_hp, 21)
        self.assertEqual(ally.combatant.current_hp, 21)
        self.assertEqual(outsider.combatant.current_hp, 20)

    def test_existing_regeneration_values_remain_troll_one_sporekin_two(self):
        self.assertEqual(character_options.RACES_BY_KEY["troll"].regen_bonus_per_tick, 1)
        self.assertEqual(character_options.RACES_BY_KEY["sporekin"].regen_bonus_per_tick, 2)
        troll = CombatantState(1, "troll", 10, 20, 0, 0, 2.5)
        sporekin = CombatantState(2, "sporekin", 10, 20, 0, 0, 2.5)
        self.assertEqual(troll.apply_normal_regeneration(1), 2)
        self.assertEqual(sporekin.apply_normal_regeneration(1), 3)


if __name__ == "__main__":
    unittest.main()
