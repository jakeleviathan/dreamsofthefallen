from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from mud import mechanics
from mud.casting import (
    INTERRUPT_MANA_REFUND_FRACTION,
    install_casting_runtime,
    interrupt_cast,
    spend_ability_mana,
)
from mud.stats import CharacterStats


class BaseSession:
    def __init__(self):
        self.character = SimpleNamespace(
            id=77,
            character_class="wizard",
            level=1,
            deity_key=None,
            current_room="test_room",
        )
        self.combatant = mechanics.CombatantState(
            character_id=77,
            race_key="human",
            current_hp=30,
            max_hp=30,
            current_mana=100,
            max_mana=100,
            auto_attack_interval=2.0,
            stats=CharacterStats(),
        )
        self.outputs: list[str] = []
        self.completed = 0
        self.closed = False

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def move_character(self, direction: str):
        self.character.current_room = f"moved_{direction}"

    async def close(self):
        self.closed = True

    async def use_ability(self, ability_text: str):
        ability = next(
            a for a in mechanics.class_abilities_for_level("wizard", 1)
            if a.key == "test_meteor"
        )
        cost = int(ability.mana_cost or 0)
        if not spend_ability_mana(self, ability, cost):
            await self.send("NOT ENOUGH MANA\r\n")
            return
        self.completed += 1
        self.combatant.start_cooldown(ability.key, ability.cooldown_seconds or 0.0)


def session_type():
    class Session(BaseSession):
        pass

    install_casting_runtime(Session)
    return Session


class CastingRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.original_wizard = mechanics.FIXED_CLASS_ABILITIES["wizard"]
        self.ability = mechanics.AbilityDefinition(
            key="test_meteor",
            name="Test Meteor",
            unlock_level=1,
            mana_cost=10,
            cooldown_seconds=9.0,
            description="Test-only heavy spell.",
            category="spell_damage",
            skill_improves_effectiveness=False,
            cast_time_seconds=0.03,
        )
        mechanics.FIXED_CLASS_ABILITIES["wizard"] = self.original_wizard + (self.ability,)

    def tearDown(self):
        mechanics.FIXED_CLASS_ABILITIES["wizard"] = self.original_wizard

    def test_cast_reserves_mana_then_completes_without_double_charging(self):
        async def scenario():
            Session = session_type()
            session = Session()

            await session.use_ability("test meteor")
            self.assertEqual(session.combatant.current_mana, 90)
            self.assertEqual(session.completed, 0)
            self.assertIsNotNone(getattr(session, "_active_cast", None))

            await asyncio.sleep(0.06)
            self.assertEqual(session.completed, 1)
            self.assertEqual(session.combatant.current_mana, 90)
            self.assertIsNone(getattr(session, "_active_cast", None))
            self.assertFalse(session.combatant.ability_ready("test_meteor"))

        asyncio.run(scenario())

    def test_damage_interrupt_refunds_most_mana_and_does_not_start_cooldown(self):
        async def scenario():
            Session = session_type()
            session = Session()

            await session.use_ability("Test Meteor")
            self.assertEqual(session.combatant.current_mana, 90)

            interrupted = await interrupt_cast(session, "damage")
            self.assertTrue(interrupted)
            expected_refund = round(10 * INTERRUPT_MANA_REFUND_FRACTION)
            self.assertEqual(session.combatant.current_mana, 90 + expected_refund)

            await asyncio.sleep(0.06)
            self.assertEqual(session.completed, 0)
            self.assertTrue(session.combatant.ability_ready("test_meteor"))
            self.assertIn("interrupted", "".join(session.outputs).lower())

        asyncio.run(scenario())

    def test_movement_interrupts_an_active_cast(self):
        async def scenario():
            Session = session_type()
            session = Session()

            await session.use_ability("Test Meteor")
            await session.move_character("north")
            await asyncio.sleep(0.06)

            self.assertEqual(session.completed, 0)
            self.assertEqual(session.character.current_room, "moved_north")
            self.assertIn("interrupted as you move", "".join(session.outputs).lower())

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
