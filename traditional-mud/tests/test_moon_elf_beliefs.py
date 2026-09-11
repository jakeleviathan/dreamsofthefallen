from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from mud.character_options import RACES_BY_KEY
from mud.mechanics import PRIEST_DEITIES, class_abilities_for_level
from mud.moon_elf_beliefs import (
    MOON_ELF_BELIEF_INTRO_FLAG,
    MOON_ELF_RELIGION_GRANTS_PRIEST_PATH,
    MOON_ELF_RELIGION_HAS_PERSONAL_DEITY,
    MOON_ELF_WITNESS_INTRO_FLAG,
    MOON_ELF_WITNESS_PATH,
    MOON_ELF_WITNESS_PATH_KEY,
    MOON_PHASE_MEANINGS,
    WITNESS_ABILITIES,
    belief_summary_lines,
    forest_elf_rivalry_lines,
    horizon_lines,
    install_moon_elf_belief_runtime,
    journal_lines,
    phase_meaning,
    prayer_lines,
    religion_lines,
    shrine_lines,
    witness_lines,
    witness_magic_lines,
)


class FakeDatabase:
    def __init__(self):
        self.flags: set[str] = set()
        self.character = None

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def set_character_deity(self, _character_id: int, deity_key: str | None):
        if self.character is not None:
            self.character.deity_key = deity_key

    def get_character_by_name(self, _name: str):
        return self.character


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Selene"
    race: str = "moon_elf"
    character_class: str = "wizard"
    deity_key: str | None = None


@dataclass
class FakeChoice:
    key: str
    name: str = "Choice"


class FakeSession:
    def __init__(self, command: str = ""):
        self.character = FakeCharacter()
        self.database = FakeDatabase()
        self.database.character = self.character
        self.command = command
        self.outputs: list[str] = []
        self.state = None
        self.base_deity_calls = 0

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

    async def choose_creation_option(self, _label, options):
        return options[0] if options else None

    async def choose_priest_deity(self):
        self.base_deity_calls += 1
        return FakeChoice("base_deity", "Base Deity")


class MoonElfBeliefTests(unittest.TestCase):
    def test_moon_is_perspective_symbol_not_deity_or_horoscope(self):
        text = " ".join(belief_summary_lines()).lower()
        self.assertIn("moon is not a god", text)
        self.assertIn("symbol of perspective", text)
        self.assertIn("sacred", text)
        self.assertIn("not because it is believed to be a person", text)
        self.assertIn("rather than fate", text)
        self.assertIn("clarity and honesty", text)
        self.assertIn("privacy and beginnings", text)

    def test_sacred_tradition_has_witness_priests_without_personal_lunar_deity(self):
        self.assertFalse(MOON_ELF_RELIGION_HAS_PERSONAL_DEITY)
        self.assertTrue(MOON_ELF_RELIGION_GRANTS_PRIEST_PATH)
        text = " ".join(religion_lines()).lower()
        self.assertIn("no personal lunar deity", text)
        self.assertIn("sacred lens", text)
        self.assertIn("does not require believing that the moon thinks", text)
        self.assertIn("reverent language", text)
        self.assertIn("philosophy", text)
        self.assertIn("invite reflection rather than enforce obedience", text)
        self.assertIn("called witnesses", text)
        self.assertIn("does not serve a moon god", text)

    def test_shrines_are_for_perspective_not_bargaining_for_favors(self):
        text = " ".join(shrine_lines()).lower()
        self.assertIn("perspective rather than places to bargain for miracles", text)
        self.assertIn("open-air alcoves", text)
        self.assertIn("does not need an idol", text)
        self.assertIn("not required intermediaries", text)
        self.assertIn("no answer is ready yet", text)

    def test_prayer_can_be_reverent_philosophical_or_silent(self):
        text = " ".join(prayer_lines()).lower()
        self.assertIn("no single required", text)
        self.assertIn("old companion", text)
        self.assertIn("silence", text)
        self.assertIn("not persuading a supernatural listener", text)
        self.assertIn("not a gatekeeper", text)
        self.assertIn("reverent language and philosophical language comfortably coexist", text)

    def test_witness_social_role_preserves_clarity_without_claiming_divine_authority(self):
        text = " ".join(witness_lines()).lower()
        self.assertIn("called witnesses", text)
        self.assertIn("not a servant or mouthpiece", text)
        self.assertIn("mediate disputes", text)
        self.assertIn("sit with the dying", text)
        self.assertIn("conflicting histories", text)
        self.assertIn("no automatic government office", text)

    def test_witness_magic_is_healing_protection_and_deliberately_ambiguous_in_source(self):
        text = " ".join(witness_magic_lines()).lower()
        self.assertIn("healing, protection, and clarity", text)
        self.assertIn("clearview mending", text)
        self.assertIn("second view ward", text)
        self.assertIn("power is granted", text)
        self.assertIn("power is accessed", text)
        self.assertIn("neither explanation has been proven", text)

        self.assertEqual(WITNESS_ABILITIES[0].key, "restoring_light")
        self.assertEqual(WITNESS_ABILITIES[0].name, "Clearview Mending")
        self.assertEqual(WITNESS_ABILITIES[1].key, "guardian_ward")
        self.assertEqual(WITNESS_ABILITIES[1].name, "Second View Ward")
        level_one = class_abilities_for_level("priest", 1, MOON_ELF_WITNESS_PATH_KEY)
        level_two = class_abilities_for_level("priest", 2, MOON_ELF_WITNESS_PATH_KEY)
        self.assertEqual([ability.name for ability in level_one], ["Clearview Mending"])
        self.assertEqual(
            [ability.name for ability in level_two],
            ["Clearview Mending", "Second View Ward"],
        )

    def test_witness_is_not_added_as_a_fourth_deity(self):
        deity_keys = [deity.key for deity in PRIEST_DEITIES]
        self.assertEqual(deity_keys, ["zerjz", "tenebrous", "leviathan"])
        self.assertNotIn(MOON_ELF_WITNESS_PATH_KEY, deity_keys)
        self.assertEqual(MOON_ELF_WITNESS_PATH.domain, "clarity")

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

    def test_character_roster_lore_carries_witness_tradition(self):
        moon_elf = RACES_BY_KEY["moon_elf"]
        lore = " ".join(moon_elf.lore).lower()
        self.assertIn("not generally worshiped as a god", lore)
        self.assertIn("broad clear horizons", lore)
        self.assertIn("changing one's mind", lore)
        self.assertIn("journals across generations", lore)
        self.assertIn("new moon for privacy and beginnings", lore)
        self.assertIn("called witnesses", lore)
        self.assertIn("accompany the dying", lore)
        self.assertIn("power accessed through clarity", lore)

    def test_character_creation_routes_moon_elf_priest_to_witness_without_deity_menu(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session()
        race = FakeChoice("moon_elf", "Moon Elf")
        selected = asyncio.run(session.choose_creation_option("race", (race,)))
        self.assertEqual(selected.key, "moon_elf")

        path = asyncio.run(session.choose_priest_deity())
        self.assertEqual(path.key, MOON_ELF_WITNESS_PATH_KEY)
        self.assertEqual(session.base_deity_calls, 0)
        output = "".join(session.outputs).lower()
        self.assertIn("priest tradition: witness", output)
        self.assertIn("no patron deity is selected", output)

    def test_non_moon_elf_priest_still_uses_normal_deity_selection(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session()
        race = FakeChoice("human", "Human")
        asyncio.run(session.choose_creation_option("race", (race,)))
        path = asyncio.run(session.choose_priest_deity())
        self.assertEqual(path.key, "base_deity")
        self.assertEqual(session.base_deity_calls, 1)

    def test_runtime_introduces_culture_once_and_exposes_commands(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session("beliefs")

        asyncio.run(session.enter_character())
        first_output = "".join(session.outputs).lower()
        self.assertIn("moon is not a god", first_output)
        self.assertIn("sacred lens", first_output)
        self.assertIn("reverently", first_output)
        self.assertIn(MOON_ELF_BELIEF_INTRO_FLAG, session.database.flags)

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("moon is not a god", "".join(session.outputs).lower())

        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        beliefs_output = "".join(session.outputs).lower()
        self.assertIn("elven lunar tradition", beliefs_output)
        self.assertIn("change your mind", beliefs_output)

        session.outputs.clear()
        session.command = "religion"
        asyncio.run(session.playing_prompt())
        religion_output = "".join(session.outputs).lower()
        self.assertIn("sacred lunar tradition", religion_output)
        self.assertIn("no personal lunar deity", religion_output)
        self.assertIn("invite reflection", religion_output)
        self.assertIn("witnesses", religion_output)

        session.outputs.clear()
        session.command = "shrine"
        asyncio.run(session.playing_prompt())
        shrine_output = "".join(session.outputs).lower()
        self.assertIn("shrines of perspective", shrine_output)
        self.assertIn("bargain for miracles", shrine_output)

        session.outputs.clear()
        session.command = "prayer"
        asyncio.run(session.playing_prompt())
        prayer_output = "".join(session.outputs).lower()
        self.assertIn("prayer and reflection", prayer_output)
        self.assertIn("no single required", prayer_output)

        session.outputs.clear()
        session.command = "witness"
        asyncio.run(session.playing_prompt())
        witness_output = "".join(session.outputs).lower()
        self.assertIn("the witnesses", witness_output)
        self.assertIn("conflicting histories", witness_output)

        session.outputs.clear()
        session.command = "witness magic"
        asyncio.run(session.playing_prompt())
        magic_output = "".join(session.outputs).lower()
        self.assertIn("witness magic", magic_output)
        self.assertIn("neither explanation has been proven", magic_output)

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

    def test_unassigned_existing_moon_elf_priest_is_migrated_to_witness_once(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session()
        session.character.character_class = "priest"
        session.character.deity_key = None

        asyncio.run(session.enter_character())
        self.assertEqual(session.character.deity_key, MOON_ELF_WITNESS_PATH_KEY)
        self.assertIn(MOON_ELF_WITNESS_INTRO_FLAG, session.database.flags)
        output = "".join(session.outputs).lower()
        self.assertIn("your priest tradition names you a witness", output)
        self.assertIn("granted", output)
        self.assertIn("accessed", output)

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("your priest tradition names you a witness", "".join(session.outputs).lower())

    def test_existing_explicit_patron_choice_is_not_silently_overwritten(self):
        class Session(FakeSession):
            pass

        install_moon_elf_belief_runtime(Session)
        session = Session()
        session.character.character_class = "priest"
        session.character.deity_key = "zerjz"

        asyncio.run(session.enter_character())
        self.assertEqual(session.character.deity_key, "zerjz")
        self.assertNotIn(MOON_ELF_WITNESS_INTRO_FLAG, session.database.flags)


if __name__ == "__main__":
    unittest.main()
