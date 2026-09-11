from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from mud.new_player_guidance import (
    CONFIDENT_FLAG,
    INTRO_FLAG,
    MOVE_FLAG,
    SPEAK_FLAG,
    STUCK_HINT_FLAG,
    install_new_player_guidance_runtime,
)


@dataclass
class FakeCharacter:
    id: int
    name: str
    current_room: str = "room_one"
    level: int = 1


class FakeDatabase:
    def __init__(self) -> None:
        self.flags: dict[int, set[str]] = {}

    def list_flags(self, character_id: int):
        return sorted(self.flags.get(character_id, set()))

    def grant_flag(self, character_id: int, flag: str):
        self.flags.setdefault(character_id, set()).add(flag)


class FakeState:
    DISCONNECTED = "disconnected"


class BaseSession:
    def __init__(self, character: FakeCharacter, commands=None) -> None:
        self.character = character
        self.database = FakeDatabase()
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def enter_character(self):
        await self.send("FIRST ROOM DESCRIPTION\r\n")

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is None:
            return
        normalized = " ".join(command.strip().lower().split())
        if normalized in {"look", "l"}:
            await self.send("You look around.\r\n")
            return
        if normalized == "north":
            self.character.current_room = "room_two"
            await self.send("You travel north.\r\n")
            return
        await self.send("Unknown command. Type HELP.\r\n")


def session_type():
    class Session(BaseSession):
        pass

    install_new_player_guidance_runtime(Session)
    return Session


class NewPlayerGuidanceTests(unittest.TestCase):
    def test_first_entry_teaches_typed_commands_once_after_room(self):
        Session = session_type()
        session = Session(FakeCharacter(1, "Mira"))

        asyncio.run(session.enter_character())
        first_output = "".join(session.outputs)
        self.assertLess(
            first_output.index("FIRST ROOM DESCRIPTION"),
            first_output.index("Dreams of the Fallen is a text world"),
        )
        self.assertIn("Try LOOK", first_output)
        self.assertIn("Try SAY HELLO", first_output)
        self.assertIn(INTRO_FLAG, session.database.flags[1])

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("text world", "".join(session.outputs))

    def test_say_is_real_room_speech_not_a_dead_tutorial_example(self):
        Session = session_type()
        speaker = Session(FakeCharacter(1, "Mira", "room_one"), ["say hello there"])
        listener = Session(FakeCharacter(2, "Teren", "room_one"))
        elsewhere = Session(FakeCharacter(3, "Veyra", "room_two"))
        asyncio.run(speaker.enter_character())
        asyncio.run(listener.enter_character())
        asyncio.run(elsewhere.enter_character())
        speaker.outputs.clear()
        listener.outputs.clear()
        elsewhere.outputs.clear()

        asyncio.run(speaker.playing_prompt())

        self.assertIn('You say, "hello there"', "".join(speaker.outputs))
        self.assertIn('Mira says, "hello there"', "".join(listener.outputs))
        self.assertNotIn("Mira says", "".join(elsewhere.outputs))
        self.assertIn(SPEAK_FLAG, speaker.database.flags[1])

    def test_basics_is_short_and_does_not_fall_through_to_unknown_command(self):
        Session = session_type()
        session = Session(FakeCharacter(1, "Mira"), ["basics"])
        asyncio.run(session.enter_character())
        session.outputs.clear()

        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("--- The Tiny Version ---", output)
        self.assertIn("LOOK - see the room again", output)
        self.assertIn("SAY <message>", output)
        self.assertNotIn("Unknown command", output)

    def test_two_unknown_commands_trigger_one_gentle_stuck_hint(self):
        Session = session_type()
        session = Session(FakeCharacter(1, "Mira"), ["frobnicate", "dance wildly", "xyzzy"])
        asyncio.run(session.enter_character())
        session.outputs.clear()

        asyncio.run(session.playing_prompt())
        self.assertNotIn("If you're not sure what the game expects", "".join(session.outputs))

        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("If you're not sure what the game expects", output)
        self.assertIn(STUCK_HINT_FLAG, session.database.flags[1])

        before = output.count("If you're not sure what the game expects")
        asyncio.run(session.playing_prompt())
        after = "".join(session.outputs).count("If you're not sure what the game expects")
        self.assertEqual(before, after)

    def test_successful_basics_quiet_future_stuck_nudges(self):
        Session = session_type()
        session = Session(
            FakeCharacter(1, "Mira"),
            ["look", "north", "bad one", "bad two"],
        )
        asyncio.run(session.enter_character())
        session.outputs.clear()

        asyncio.run(session.playing_prompt())
        asyncio.run(session.playing_prompt())
        flags = session.database.flags[1]
        self.assertIn(MOVE_FLAG, flags)
        self.assertIn(CONFIDENT_FLAG, flags)

        asyncio.run(session.playing_prompt())
        asyncio.run(session.playing_prompt())
        self.assertNotIn("If you're not sure what the game expects", "".join(session.outputs))


if __name__ == "__main__":
    unittest.main()
