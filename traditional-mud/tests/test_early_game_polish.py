from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

from mud.early_game_polish import (
    ABILITY_FLAG,
    EARLY_GAME_MAX_LEVEL,
    EXIT_RESCUE_FLAG,
    FIGHT_FLAG,
    LOOK_FLAG,
    MOVE_FLAG,
    RACE_VERB_FLAVOR,
    install_early_game_polish_runtime,
)
from mud.room_engine import WorldService
from mud.world import RoomDefinition


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Tester"
    race: str = "goblin"
    character_class: str = "wizard"
    deity_key: str | None = None
    level: int = 4
    current_room: str = "start"


class FakeDatabase:
    def __init__(self):
        self.flags: dict[int, set[str]] = {}
        self.quests: list[dict] = []

    def list_flags(self, character_id: int):
        return sorted(self.flags.get(character_id, set()))

    def grant_flag(self, character_id: int, flag: str):
        self.flags.setdefault(character_id, set()).add(flag)

    def list_quests(self, _character_id: int):
        return list(self.quests)


class BaseSession:
    def __init__(self, commands=()):
        self.character = FakeCharacter()
        self.database = FakeDatabase()
        self.commands = list(commands)
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        return self.commands.pop(0) if self.commands else None

    async def enter_character(self):
        await self.send("ROOM\r\n")

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is None:
            return
        normalized = command.strip().lower()
        if normalized in {"look", "l"}:
            await self.send("You look around.\r\n")
        elif normalized in {"north", "n"}:
            self.character.current_room = "north_room"
            await self.send("You travel north.\r\n")
        elif normalized in {"west", "w"}:
            await self.send("You cannot go that way.\r\n")
        elif normalized.startswith("attack "):
            await self.send("You attack the target.\r\n")
        elif normalized.startswith("use "):
            await self.send("You use an ability.\r\n")
        else:
            await self.send("Unknown command.\r\n")


def fake_world() -> WorldService:
    rooms = {
        "start": RoomDefinition(
            key="start",
            name="Start",
            region_key="test",
            description="A test start.",
            exits={"north": "north_room"},
        ),
        "north_room": RoomDefinition(
            key="north_room",
            name="North Room",
            region_key="test",
            description="A second room.",
            exits={"south": "start"},
        ),
    }
    return WorldService(rooms=rooms)


def session_type():
    class Session(BaseSession):
        pass

    install_early_game_polish_runtime(Session, fake_world())
    return Session


class EarlyGamePolishTests(unittest.TestCase):
    def test_same_core_verbs_get_distinct_racial_framing(self):
        self.assertEqual(
            set(RACE_VERB_FLAVOR),
            {"human", "forest_elf", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin"},
        )
        self.assertEqual(len(set(RACE_VERB_FLAVOR.values())), 8)
        for text in RACE_VERB_FLAVOR.values():
            self.assertIn("LOOK", text)

    def test_first_entry_explains_goals_without_a_checklist(self):
        Session = session_type()
        session = Session()
        asyncio.run(session.enter_character())
        output = "".join(session.outputs)
        self.assertIn("Type GOALS", output)
        self.assertIn("salvage", output.lower())
        self.assertNotIn("1/4", output)
        self.assertNotIn("checklist", output.lower())

    def test_goals_is_one_short_current_objective_surface(self):
        Session = session_type()
        session = Session(["goals"])
        # No active quest in this fake DB means the race's opening hook is used.
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("Current goal - Three Bells", output)
        self.assertNotIn("Quest Journal", output)

    def test_look_move_fight_and_ability_are_quietly_recorded(self):
        Session = session_type()
        session = Session(["look", "north", "attack rat", "use coldfire burst"])
        for _ in range(4):
            asyncio.run(session.playing_prompt())
        flags = session.database.flags[1]
        self.assertTrue({LOOK_FLAG, MOVE_FLAG, FIGHT_FLAG, ABILITY_FLAG}.issubset(flags))

    def test_bad_early_direction_shows_actual_available_exit_once(self):
        Session = session_type()
        session = Session(["west", "west"])
        asyncio.run(session.playing_prompt())
        first = "".join(session.outputs)
        self.assertIn("Available exits here: NORTH", first)
        self.assertIn(EXIT_RESCUE_FLAG, session.database.flags[1])
        count = first.count("Available exits here")
        asyncio.run(session.playing_prompt())
        self.assertEqual("".join(session.outputs).count("Available exits here"), count)

    def test_rescue_and_tracking_are_limited_to_levels_one_through_ten(self):
        self.assertEqual(EARLY_GAME_MAX_LEVEL, 10)
        Session = session_type()
        session = Session(["west"])
        session.character.level = 11
        asyncio.run(session.playing_prompt())
        self.assertNotIn("Available exits here", "".join(session.outputs))
        self.assertFalse(session.database.flags.get(1))


class ProductionEarlyGameContractTests(unittest.TestCase):
    def test_real_production_entrypoint_keeps_all_40_race_class_starts_walkable_to_level_ten(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.early_game_polish import validate_level_ten_playability_contract

races = ("human", "forest_elf", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin")
classes = ("brute", "wizard", "druid", "priest", "necromancer")
assert server.PlayerSession._early_game_polish_runtime_installed
validate_level_ten_playability_contract(server.WORLD, races, classes)
print("40/40 early-game race/class contracts OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=90,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
        self.assertIn("40/40 early-game race/class contracts OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
