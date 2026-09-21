from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.appearance import (
    appearance_description,
    creation_preview_text,
    defaults_for_race,
    traits_for_race,
)
from mud.appearance_storage import get_appearance
from mud.database import Database
from mud.session import PlayerSession
from mud.stats import CharacterStats


class FakeCreationSession:
    choose_creation_appearance = PlayerSession.choose_creation_appearance

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.outputs: list[str] = []

    async def send(self, text: str) -> None:
        self.outputs.append(text)

    async def prompt(self, text: str) -> str | None:
        self.outputs.append(text)
        if not self.answers:
            raise AssertionError("appearance prompt requested more answers than the test supplied")
        return self.answers.pop(0)


class CharacterAppearanceCreationTests(unittest.TestCase):
    def test_every_playable_race_has_its_own_trait_set(self):
        race_keys = {
            "human",
            "forest_elf",
            "moon_elf",
            "dwarf",
            "goblin",
            "troll",
            "undead",
            "sporekin",
        }
        self.assertEqual(race_keys, {key for key in race_keys if traits_for_race(key)})
        self.assertIn("beard_style", defaults_for_race("dwarf"))
        self.assertNotIn("beard_style", defaults_for_race("undead"))
        self.assertNotIn("hair_style", defaults_for_race("undead"))
        self.assertIn("nose_shape", defaults_for_race("goblin"))
        self.assertIn("tusks", defaults_for_race("troll"))
        self.assertIn("lunar_marking", defaults_for_race("moon_elf"))
        self.assertIn("cap_shape", defaults_for_race("sporekin"))

    def test_dwarf_creation_can_choose_a_braided_beard(self):
        session = FakeCreationSession([
            "",  # build default
            "",  # complexion default
            "",  # hair color default
            "5", # braided beard
            "",  # beard adornment default
            "",  # eye color default
            "y",
        ])
        result = asyncio.run(session.choose_creation_appearance("dwarf", "Dwarf"))
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["beard_style"], "braided")
        output = "".join(session.outputs)
        self.assertIn("--- Shape Your Dwarf ---", output)
        self.assertIn("Beard style", output)
        self.assertIn("Appearance Preview", output)

    def test_creation_appearance_is_persisted_with_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "appearance_creation.db")
            account = database.create_account("appearance_creation", "x")
            appearance = defaults_for_race("goblin")
            appearance["ear_style"] = "notched"
            appearance["nose_shape"] = "crooked"
            character = database.create_character(
                account.id,
                "Rivet",
                "goblin",
                "brute",
                CharacterStats(might=6, grace=6, love=4, mind=4, hp=6),
                appearance=appearance,
            )
            stored = get_appearance(database, character.id)
            self.assertEqual(stored["ear_style"], "notched")
            self.assertEqual(stored["nose_shape"], "crooked")

    def test_description_reads_like_character_description(self):
        dwarf = defaults_for_race("dwarf")
        dwarf["beard_style"] = "double-braided"
        dwarf["beard_adornment"] = "brass clasps"
        description = appearance_description("Brom", "dwarf", dwarf)
        self.assertIn("Brom is a Dwarf", description)
        self.assertIn("double-braided brown beard", description)
        self.assertIn("brass clasps worked into the beard", description)
        self.assertNotIn("beard_style", description)

        preview = creation_preview_text("undead", defaults_for_race("undead"))
        self.assertIn("Your Undead will have", preview)
        self.assertNotIn("hair", preview.lower())


if __name__ == "__main__":
    unittest.main()
