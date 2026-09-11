from __future__ import annotations

import asyncio
import unittest

from mud.character_creation_experience import (
    CLASS_PRESENTATIONS,
    RACE_PRESENTATIONS,
    choose_class_experience,
    choose_race_experience,
    install_character_creation_experience,
)
from mud.character_options import CLASSES, RACES
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

    def test_first_race_screen_is_short_hook_list_not_full_lore_dump(self):
        session = FakeSession(["0"])
        asyncio.run(choose_race_experience(session, RACES))
        output = "".join(session.outputs)
        self.assertIn("Choose Your People", output)
        self.assertIn("Human - Outsiders who crossed from another world", output)
        self.assertIn("Moon Elf - High-horizon elves", output)
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

    def test_race_back_returns_to_comparison_list(self):
        session = FakeSession(["1", "back", "8", "choose"])
        selected = asyncio.run(choose_race_experience(session, RACES))
        self.assertEqual(selected.key, "sporekin")
        self.assertGreaterEqual("".join(session.outputs).count("Choose Your People"), 2)

    def test_all_five_classes_have_hook_first_presentation(self):
        self.assertEqual({character_class.key for character_class in CLASSES}, set(CLASS_PRESENTATIONS))
        for character_class in CLASSES:
            presentation = CLASS_PRESENTATIONS[character_class.key]
            self.assertTrue(presentation.hook)
            self.assertTrue(presentation.play_style)
            self.assertTrue(presentation.good_if)

    def test_first_class_screen_is_short_hook_list_not_mechanical_dump(self):
        session = FakeSession(["0"])
        asyncio.run(choose_class_experience(session, CLASSES))
        output = "".join(session.outputs)
        self.assertIn("Choose Your Calling", output)
        self.assertIn("Wizard - Careful power through understanding.", output)
        self.assertIn("Priest - Ritual care without easy answers.", output)
        self.assertIn("Necromancer - Death work with consequences.", output)
        self.assertIn("Every people can follow every calling", output)
        self.assertNotIn("Single-target magical nuke powerhouse", output)
        self.assertNotIn("Raise Skeleton at level 2", output)

    def test_selecting_class_opens_play_style_card_before_commitment(self):
        session = FakeSession(["necromancer", "choose"])
        selected = asyncio.run(choose_class_experience(session, CLASSES))
        self.assertEqual(selected.key, "necromancer")
        output = "".join(session.outputs)
        self.assertIn("Vibe: Death work with consequences.", output)
        self.assertIn("How it plays:", output)
        self.assertIn("Good if you like:", output)
        self.assertIn("At the start:", output)
        self.assertIn("MORE DETAILS", output)

    def test_class_more_details_is_optional_and_preserves_choice(self):
        session = FakeSession(["druid", "more details", "choose"])
        selected = asyncio.run(choose_class_experience(session, CLASSES))
        self.assertEqual(selected.key, "druid")
        output = "".join(session.outputs)
        self.assertIn("More Details: Druid", output)
        self.assertIn("Later identity:", output)
        self.assertIn("Equipment:", output)
        self.assertIn("do not shapeshift", output)
        self.assertIn("authored ability path", output)

    def test_priest_card_explains_followup_spiritual_path_without_lore_dump(self):
        session = FakeSession(["priest", "choose"])
        selected = asyncio.run(choose_class_experience(session, CLASSES))
        self.assertEqual(selected.key, "priest")
        output = "".join(session.outputs)
        self.assertIn("tradition or patron is chosen immediately after class selection", output)
        self.assertNotIn("Zerjz", output)
        self.assertNotIn("Tenebrous", output)
        self.assertNotIn("Leviathan", output)

    def test_class_back_returns_to_comparison_list(self):
        session = FakeSession(["wizard", "back", "brute", "choose"])
        selected = asyncio.run(choose_class_experience(session, CLASSES))
        self.assertEqual(selected.key, "brute")
        self.assertGreaterEqual("".join(session.outputs).count("Choose Your Calling"), 2)

    def test_wrapper_replaces_race_and_class_choice_but_delegates_other_labels(self):
        race_session = WrappedSession(["3", "choose"])
        selected_race = asyncio.run(race_session.choose_creation_option("race", RACES))
        self.assertEqual(selected_race.key, "moon_elf")

        class_session = WrappedSession(["5", "choose"])
        selected_class = asyncio.run(class_session.choose_creation_option("class", CLASSES))
        self.assertEqual(selected_class.key, "necromancer")

        other_result = asyncio.run(
            WrappedSession([]).choose_creation_option("background", (object(),))
        )
        self.assertEqual(other_result[0], "legacy")
        self.assertEqual(other_result[1], "background")


if __name__ == "__main__":
    unittest.main()
