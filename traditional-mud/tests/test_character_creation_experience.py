from __future__ import annotations

import asyncio
import unittest

from mud.character_creation_experience import (
    RACE_PRESENTATIONS,
    choose_race_experience,
    install_character_creation_experience,
)
from mud.character_options import RACES
from mud.session import SessionState


class FakeSession:
    def __init__(self, prompts: list[str]):
        self.prompts = list(prompts)
        self.outputs: list[str] = []
        self.state = SessionState.CHARACTER_MENU

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, text: str):
        self.outputs.append(text)
        if not self.prompts:
            return None
        return self.prompts.pop(0)


class WrappedSession(FakeSession):
    async def choose_creation_option(self, label, options):
        return ("legacy", label, options)


install_character_creation_experience(WrappedSession)


class CharacterCreationExperienceTests(unittest.TestCase):
    def test_all_eight_races_have_hook_first_presentation(self):
        self.assertEqual({race.key for race in RACES}, set(RACE_PRESENTATIONS))
        for race in RACES:
            presentation = RACE_PRESENTATIONS[race.key]
            self.assertTrue(presentation.hook)
            self.assertTrue(presentation.known_for)
            self.assertTrue(presentation.world_view)
            self.assertTrue(presentation.starting_area)

    def test_first_screen_is_short_hook_list_not_full_lore_dump(self):
        session = FakeSession(["0"])
        asyncio.run(choose_race_experience(session, RACES))
        output = "".join(session.outputs)
        self.assertIn("Choose Your People", output)
        self.assertIn("Human - Outsiders who crossed from another world", output)
        self.assertIn("Moon Elf - High-horizon elves", output)
        # Long lore remains opt-in instead of flooding the first screen.
        self.assertNotIn("No known route back to Earth remains", output)
        self.assertNotIn("Many families keep journals across generations", output)

    def test_selecting_race_opens_card_before_commitment(self):
        session = FakeSession(["human", "choose"])
        selected = asyncio.run(choose_race_experience(session, RACES))
        self.assertEqual(selected.key, "human")
        output = "".join(session.outputs)
        self.assertIn("Known for:", output)
        self.assertIn("The world sees you as:", output)
        self.assertIn("Starting area:", output)
        self.assertIn("Racial trait: Fast Learner", output)
        self.assertIn("MORE LORE", output)

    def test_more_lore_is_optional_and_returns_to_same_card_choice(self):
        session = FakeSession(["2", "more lore", "choose"])
        selected = asyncio.run(choose_race_experience(session, RACES))
        self.assertEqual(selected.key, "forest_elf")
        output = "".join(session.outputs)
        self.assertIn("More Lore: Forest Elf", output)
        self.assertIn("They insist that they are simply 'Elves'", output)

    def test_back_returns_to_comparison_list(self):
        session = FakeSession(["1", "back", "8", "choose"])
        selected = asyncio.run(choose_race_experience(session, RACES))
        self.assertEqual(selected.key, "sporekin")
        self.assertGreaterEqual("".join(session.outputs).count("Choose Your People"), 2)

    def test_wrapper_only_replaces_race_choice(self):
        race_session = WrappedSession(["3", "choose"])
        selected = asyncio.run(race_session.choose_creation_option("race", RACES))
        self.assertEqual(selected.key, "moon_elf")

        class_result = asyncio.run(
            WrappedSession([]).choose_creation_option("class", (object(),))
        )
        self.assertEqual(class_result[0], "legacy")
        self.assertEqual(class_result[1], "class")


if __name__ == "__main__":
    unittest.main()
