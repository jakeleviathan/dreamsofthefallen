from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from mud.character_options import RACES_BY_KEY
from mud.moon_elf_beliefs import (
    MOON_ELF_BELIEF_INTRO_FLAG,
    MOON_PHASE_MEANINGS,
    belief_summary_lines,
    forest_elf_rivalry_lines,
    horizon_lines,
    install_moon_elf_belief_runtime,
    journal_lines,
    phase_meaning,
)


class FakeDatabase:
    def __init__(self):
        self.flags: set[str] = set()

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)


@dataclass
class FakeCharacter:
    id: int = 1
    race: str = "moon_elf"


class FakeSession:
    def __init__(self, command: str = ""):
        self.character = FakeCharacter()
        self.database = FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = None

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


class MoonElfBeliefTests(unittest.TestCase):
    def test_moon_is_perspective_symbol_not_deity_or_horoscope(self):
        text = " ".join(belief_summary_lines()).lower()
        self.assertIn("moon is not a god", text)
        self.assertIn("symbol of perspective", text)
        self.assertIn("rather than fate", text)
        self.assertIn("clarity and honesty", text)
        self.assertIn("privacy and beginnings", text)

    def test_all_four_existing_astralis_phases_have_cultural_modes(self):
        self.assertEqual(
            [meaning.key for meaning in MOON_PHASE_MEANINGS],
            ["new", "waxing", "full", "waning"],
        )
        self.assertEqual(phase_meaning("new").emphasis, "privacy and beginnings")
        self.assertEqual(phase_meaning("full").emphasis, "clarity and honesty")
        self.assertIn("inquiry", phase_meaning("waxing").emphasis)
        self.assertIn("revision", phase_meaning("waning").emphasis)
        with self.assertRaises(ValueError):
            phase_meaning("eclipse")

    def test_high_places_are_about_horizon_not_superiority(self):
        text = " ".join(horizon_lines()).lower()
        self.assertIn("clear horizon", text)
        self.assertIn("not 'we stand above others.'", text)
        self.assertIn("step far enough back", text)

    def test_generational_journals_preserve_changed_minds(self):
        text = " ".join(journal_lines()).lower()
        self.assertIn("several generations", text)
        self.assertIn("corrections", text)
        self.assertIn("not to make ancestors look infallible", text)

    def test_forest_elf_difference_is_rivalry_not_default_war(self):
        text = " ".join(forest_elf_rivalry_lines()).lower()
        self.assertIn("watching life", text)
        self.assertIn("rootedness can become narrowness", text)
        self.assertIn("cultural rivalry", text)
        self.assertIn("rather than automatic hatred or war", text)

    def test_character_roster_lore_carries_new_beliefs(self):
        moon_elf = RACES_BY_KEY["moon_elf"]
        lore = " ".join(moon_elf.lore).lower()
        self.assertIn("not generally worshiped as a god", lore)
        self.assertIn("broad clear horizons", lore)
        self.assertIn("changing one's mind", lore)
        self.assertIn("journals across generations", lore)
        self.assertIn("new moon for privacy and beginnings", lore)

    def test_runtime_introduces_culture_once_and_exposes_commands(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session("beliefs")

        asyncio.run(session.enter_character())
        first_output = "".join(session.outputs).lower()
        self.assertIn("moon is not a god", first_output)
        self.assertIn("distance can change understanding", first_output)
        self.assertIn(MOON_ELF_BELIEF_INTRO_FLAG, session.database.flags)

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("moon is not a god", "".join(session.outputs).lower())

        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        beliefs_output = "".join(session.outputs).lower()
        self.assertIn("elven lunar tradition", beliefs_output)
        self.assertIn("changing your mind", beliefs_output)

        session.outputs.clear()
        session.command = "moon"
        asyncio.run(session.playing_prompt())
        moon_output = "".join(session.outputs).lower()
        self.assertIn("does not predict fate", moon_output)
        self.assertIn("use calendar", moon_output)

        session.outputs.clear()
        session.command = "look"
        asyncio.run(session.playing_prompt())
        self.assertIn("base command: look", "".join(session.outputs).lower())


if __name__ == "__main__":
    unittest.main()
