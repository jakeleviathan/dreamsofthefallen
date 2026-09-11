from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from mud.starter_class_moments import (
    CLASS_PRACTICE,
    RACE_SETTINGS,
    all_starter_class_moments,
    install_starter_class_moment_runtime,
    starter_class_moment,
)


class FakeDatabase:
    def __init__(self) -> None:
        self.flags: set[str] = set()

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)


@dataclass
class FakeCharacter:
    id: int = 1
    race: str = "forest_elf"
    character_class: str = "wizard"
    level: int = 1
    deity_key: str | None = None


class FakeSession:
    def __init__(self, command: str = "class moment") -> None:
        self.character = FakeCharacter()
        self.database = FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = object()

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text: str):
        return self.command

    async def enter_character(self):
        self.outputs.append("BASE ENTER\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.outputs.append(f"BASE COMMAND: {command}\n")


class StarterClassMomentTests(unittest.TestCase):
    def test_all_eight_by_five_combinations_exist(self):
        moments = all_starter_class_moments()
        self.assertEqual(len(RACE_SETTINGS), 8)
        self.assertEqual(len(CLASS_PRACTICE), 5)
        self.assertEqual(len(moments), 40)
        self.assertEqual(len({moment.flag_key for moment in moments}), 40)
        for race_key in RACE_SETTINGS:
            for class_key in CLASS_PRACTICE:
                self.assertIsNotNone(starter_class_moment(race_key, class_key))

    def test_moments_are_racially_framed_but_class_specific(self):
        forest_wizard = starter_class_moment("forest_elf", "wizard")
        dwarf_wizard = starter_class_moment("dwarf", "wizard")
        forest_brute = starter_class_moment("forest_elf", "brute")
        assert forest_wizard and dwarf_wizard and forest_brute
        self.assertNotEqual(forest_wizard.setting, dwarf_wizard.setting)
        self.assertEqual(forest_wizard.practice_text, dwarf_wizard.practice_text)
        self.assertNotEqual(forest_wizard.practice_text, forest_brute.practice_text)
        self.assertIn("Coldfire Burst", forest_wizard.practice_text)
        self.assertIn("Taunt", forest_brute.practice_text)

    def test_runtime_offers_and_completes_optional_moment(self):
        class Session(FakeSession):
            pass

        install_starter_class_moment_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        opening = "".join(session.outputs)
        self.assertIn("CLASS MOMENT", opening)
        self.assertIn("optional", opening.lower())

        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("Forest Elf Wizard", output)
        self.assertIn("Coldfire Burst", output)
        self.assertIn("Class moment complete", output)
        self.assertIn("starter_class_moment_forest_elf_wizard", session.database.flags)

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("CLASS MOMENT", "".join(session.outputs))

    def test_unknown_combination_is_not_invented(self):
        self.assertIsNone(starter_class_moment("dragon", "bard"))


if __name__ == "__main__":
    unittest.main()
