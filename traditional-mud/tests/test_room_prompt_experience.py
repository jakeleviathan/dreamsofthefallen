from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass
from types import SimpleNamespace

import mud.room_prompt_experience as room_ux


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Mira"
    race: str = "moon_elf"
    character_class: str = "wizard"
    level: int = 1
    current_room: str = "test_room"


class FakeDatabase:
    def __init__(self, quests=None) -> None:
        self.quests = list(quests or ())

    def list_flags(self, _character_id: int):
        return []

    def list_quests(self, _character_id: int):
        return list(self.quests)


class FakeState:
    DISCONNECTED = "disconnected"


class FakeWorld:
    def __init__(self) -> None:
        self.view = SimpleNamespace(
            key="test_room",
            name="The Test Terrace",
            description="A clear room description with enough texture to imagine the place.",
            features=(SimpleNamespace(name="Skyglass Rail"), SimpleNamespace(name="Tea Table")),
            exits=(
                SimpleNamespace(direction="north", name="Upper Walk"),
                SimpleNamespace(direction="west", name=None),
            ),
        )
        self.scene_value = SimpleNamespace(npc_keys=("test_mentor",), enemy_keys=())

    def build_view(self, _room_key, _context):
        return self.view

    def scene(self, _room_key):
        return self.scene_value


class BaseSession:
    def __init__(self, commands=None, quests=None) -> None:
        self.character = FakeCharacter()
        self.database = FakeDatabase(quests)
        self.combatant = SimpleNamespace(
            current_hp=21,
            max_hp=25,
            current_mana=14,
            max_mana=20,
            current_movement=87,
            max_movement=100,
        )
        self.active_enemy = None
        self.mobile_npcs = None
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.prompts: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, text: str):
        self.prompts.append(text)
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def show_current_room(self):
        await self.send("OLD ROOM RENDER\r\n")

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is not None:
            await self.send(f"BASE COMMAND: {command}\r\n")


class FakeQuestDefinition:
    def objective_for_step(self, _step):
        return "Go east and TALK NERA."


def session_type(world=None):
    class Session(BaseSession):
        pass

    room_ux.install_room_prompt_experience_runtime(Session, world or FakeWorld())
    return Session


class RoomPromptExperienceTests(unittest.TestCase):
    def setUp(self):
        self.old_npc = room_ux.NPCS_BY_KEY.get("test_mentor")
        self.old_quest = room_ux.QUESTS_BY_KEY.get("test_quest")
        room_ux.NPCS_BY_KEY["test_mentor"] = SimpleNamespace(
            name="Druid Nera Voss",
            short_description="a practical high-altitude gardener",
            aliases=("nera", "druid nera"),
        )
        room_ux.QUESTS_BY_KEY["test_quest"] = FakeQuestDefinition()

    def tearDown(self):
        if self.old_npc is None:
            room_ux.NPCS_BY_KEY.pop("test_mentor", None)
        else:
            room_ux.NPCS_BY_KEY["test_mentor"] = self.old_npc
        if self.old_quest is None:
            room_ux.QUESTS_BY_KEY.pop("test_quest", None)
        else:
            room_ux.QUESTS_BY_KEY["test_quest"] = self.old_quest

    def test_default_prompt_is_compact_hp_and_mana(self):
        Session = session_type()
        session = Session(commands=["look"])
        asyncio.run(session.playing_prompt())
        self.assertTrue(session.prompts)
        self.assertIn("HP 21/25", session.prompts[0])
        self.assertIn("MP 14/20", session.prompts[0])
        self.assertNotIn("MV 87/100", session.prompts[0])
        self.assertIn("BASE COMMAND: look", "".join(session.outputs))

    def test_prompt_modes_offer_quiet_compact_and_full(self):
        Session = session_type()
        session = Session(commands=["prompt full", "prompt quiet"])

        asyncio.run(session.playing_prompt())
        self.assertIn("Prompt mode set to FULL", "".join(session.outputs))
        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        self.assertIn("MV 87/100", session.prompts[1])
        self.assertIn("Prompt mode set to QUIET", "".join(session.outputs))
        self.assertEqual(session.current_prompt_text(), "> ")

    def test_full_prompt_includes_current_target(self):
        Session = session_type()
        session = Session()
        session._room_ux_prompt_mode = "full"
        session.active_enemy = SimpleNamespace(
            current_hp=7,
            definition=SimpleNamespace(name="Reedjaw", max_hp=12),
        )
        text = room_ux.prompt_text(session, leading_newline=False)
        self.assertIn("Reedjaw 7/12", text)
        self.assertIn("Lv 1", text)

    def test_room_render_has_predictable_description_points_people_and_exits(self):
        Session = session_type()
        session = Session()
        asyncio.run(session.show_current_room())
        output = "".join(session.outputs)
        self.assertIn("The Test Terrace", output)
        self.assertIn("clear room description", output)
        self.assertIn("Notable: Skyglass Rail, Tea Table.", output)
        self.assertIn("People:", output)
        self.assertIn("Druid Nera Voss", output)
        self.assertIn("Exits: NORTH - Upper Walk | WEST", output)
        self.assertNotIn("OLD ROOM RENDER", output)

    def test_quest_talk_hint_is_contextual_and_only_shown_once(self):
        quests = [
            {
                "quest_key": "test_quest",
                "status": "active",
                "current_step": "meet_nera",
            }
        ]
        Session = session_type()
        session = Session(quests=quests)

        asyncio.run(session.show_current_room())
        asyncio.run(session.show_current_room())
        output = "".join(session.outputs)
        self.assertEqual(output.count("You could TALK NERA"), 1)
        self.assertIn("Druid Nera Voss is here", output)

    def test_installer_is_idempotent(self):
        world = FakeWorld()

        class Session(BaseSession):
            pass

        room_ux.install_room_prompt_experience_runtime(Session, world)
        first_prompt = Session.playing_prompt
        room_ux.install_room_prompt_experience_runtime(Session, world)
        self.assertIs(first_prompt, Session.playing_prompt)


if __name__ == "__main__":
    unittest.main()
