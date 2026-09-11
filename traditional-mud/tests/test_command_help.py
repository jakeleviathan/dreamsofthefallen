from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

# Importing the belief module registers the Moon Elf Witness Priest path in the
# same mechanics registry used by the live server and command-help system.
import mud.moon_elf_beliefs  # noqa: F401
from mud.command_help import install_command_help_runtime


class FakeDatabase:
    def __init__(self, quests=None) -> None:
        self.quests = list(quests or ())

    def list_quests(self, _character_id: int):
        return list(self.quests)


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Lethra"
    race: str = "forest_elf"
    character_class: str = "wizard"
    level: int = 1
    deity_key: str | None = None
    current_room: str = "forest_elf_circle_clearing"


class FakeState:
    DISCONNECTED = "disconnected"


class FakeSession:
    def __init__(self, command: str = "help", character=None, quests=None) -> None:
        self.character = character or FakeCharacter()
        self.database = FakeDatabase(quests)
        self.command = command
        self.outputs: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text: str):
        return self.command

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.outputs.append(f"BASE COMMAND: {command}\n")


class CommandHelpTests(unittest.TestCase):
    def _session(self, command="help", character=None, quests=None):
        class Session(FakeSession):
            pass

        install_command_help_runtime(Session)
        return Session(command=command, character=character, quests=quests)

    def test_quick_help_is_short_and_points_to_full_index(self):
        session = self._session("help")
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("--- Help ---", output)
        self.assertIn("COMMANDS or HELP ALL", output)
        self.assertIn("QUESTS", output)
        self.assertIn("RACIAL", output)
        self.assertNotIn("[Crafts, Gathering & Shops]", output)

    def test_full_help_is_tailored_to_forest_elf_wizard(self):
        session = self._session("commands")
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("[Movement & Exploration]", output)
        self.assertIn("USE COLDFIRE BURST", output)
        self.assertIn("SLIPSTEP", output)
        self.assertIn("HOME, FOREST OPENING", output)
        self.assertNotIn("RECONSIDER", output)
        self.assertNotIn("PENTHOUSE", output)

    def test_moon_elf_witness_ability_is_derived_from_live_path(self):
        character = FakeCharacter(
            name="Ilyen",
            race="moon_elf",
            character_class="priest",
            level=1,
            deity_key="moon_elf_witness",
        )
        session = self._session("help all", character=character)
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("USE CLEARVIEW MENDING", output)
        self.assertIn("Clearview Mending", output)
        self.assertIn("RECONSIDER", output)
        self.assertIn("BELIEFS", output)
        self.assertIn("WITNESS MAGIC", output)
        self.assertNotIn("Restoring Light - Restoring Light", output)

    def test_active_quest_objective_is_shown_in_help(self):
        quests = [
            {
                "quest_key": "forest_elf_first_walk",
                "status": "active",
                "current_step": "study_waystone",
            }
        ]
        session = self._session("commands", quests=quests)
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("Quest - The Old River Path", output)
        self.assertIn("EXAMINE WAYSTONE", output)

    def test_people_in_current_room_are_surfaced(self):
        character = FakeCharacter(
            name="Mara",
            race="human",
            character_class="brute",
            level=1,
            current_room="human_grand_cathedral",
        )
        session = self._session("commands", character=character)
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("People here: High Acolyte", output)
        self.assertIn("TALK <person>", output)

    def test_non_help_commands_delegate_unchanged(self):
        session = self._session("look")
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("BASE COMMAND: look", output)
        self.assertNotIn("--- Help ---", output)


if __name__ == "__main__":
    unittest.main()
