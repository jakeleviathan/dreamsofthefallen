from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.combat as combat
import mud.quests as quests
import mud.world as world
from mud.sporekin_depth import (
    GUIDE_NEMM,
    PRACTICE_HUSK,
    SPOREKIN_CULTURE_LINES,
    SPOREKIN_DEPTH_COMPLETE_FLAG,
    SPOREKIN_DEPTH_QUEST,
    SPOREKIN_DEPTH_QUEST_KEY,
    SPOREKIN_GUIDANCE_LINES,
    SPOREKIN_INDIVIDUAL_VOICE_FLAG,
    SPOREKIN_PRACTICE_HUSK_FLAG,
    SPOREKIN_SELFHOOD_LINES,
    install_sporekin_depth_content,
    install_sporekin_depth_runtime,
)
from mud.world import SPOREKIN_MEMORY_PATH_ROOM_KEY


class FakeDatabase:
    def __init__(self) -> None:
        self.flags: set[str] = {"sporekin_forgotten_pulse_solved"}
        self.quests: dict[str, dict[str, str | None]] = {}

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def get_quest(self, _character_id: int, quest_key: str):
        quest = self.quests.get(quest_key)
        return None if quest is None else dict(quest)

    def start_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests.setdefault(
            quest_key,
            {"quest_key": quest_key, "status": "active", "current_step": current_step},
        )

    def advance_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests[quest_key]["current_step"] = current_step

    def complete_quest(self, _character_id: int, quest_key: str):
        self.quests[quest_key]["status"] = "completed"
        self.quests[quest_key]["current_step"] = "complete"


@dataclass
class FakeCharacter:
    id: int = 1
    race: str = "sporekin"
    character_class: str = "brute"
    current_room: str = SPOREKIN_MEMORY_PATH_ROOM_KEY
    level: int = 1
    deity_key: str | None = None


@dataclass
class FakeEnemy:
    definition: object = PRACTICE_HUSK


class FakeSession:
    def __init__(self, command: str = "") -> None:
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

    async def _finish_enemy_defeat(self, enemy):
        self.outputs.append(f"BASE DEFEAT: {enemy.definition.name}\n")


class SporekinDepthTests(unittest.TestCase):
    def test_content_registers_mentor_training_target_and_quest(self):
        install_sporekin_depth_content()
        self.assertIs(quests.QUESTS_BY_KEY[SPOREKIN_DEPTH_QUEST_KEY], SPOREKIN_DEPTH_QUEST)
        self.assertIs(world.NPCS_BY_KEY[GUIDE_NEMM.key], GUIDE_NEMM)
        self.assertIs(combat.ENEMIES_BY_KEY[PRACTICE_HUSK.key], PRACTICE_HUSK)
        room = world.ROOMS_BY_KEY[SPOREKIN_MEMORY_PATH_ROOM_KEY]
        self.assertIn(GUIDE_NEMM.key, room.npc_keys)
        self.assertIn(PRACTICE_HUSK.key, room.enemy_keys)
        self.assertIn("Practice Husk", room.description)

    def test_culture_defines_collective_memory_without_erasing_selfhood(self):
        culture = " ".join(SPOREKIN_CULTURE_LINES).lower()
        selfhood = " ".join(SPOREKIN_SELFHOOD_LINES).lower()
        guidance = " ".join(SPOREKIN_GUIDANCE_LINES).lower()
        self.assertIn("not a single mind", culture)
        self.assertIn("private", culture)
        self.assertIn("'we remember' and 'i choose'", selfhood)
        self.assertIn("profound violation", selfhood)
        self.assertIn("warning from command", guidance)
        self.assertIn("more capable of choosing", guidance)

    def test_runtime_runs_voice_combat_and_mentor_sequence(self):
        class Session(FakeSession):
            pass

        install_sporekin_depth_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        quest = session.database.get_quest(1, SPOREKIN_DEPTH_QUEST_KEY)
        self.assertEqual(quest["current_step"], "talk_nemm")
        self.assertIn("A Voice of Your Own", "".join(session.outputs))

        session.outputs.clear()
        session.command = "talk nemm"
        asyncio.run(session.playing_prompt())
        self.assertEqual(
            session.database.get_quest(1, SPOREKIN_DEPTH_QUEST_KEY)["current_step"],
            "speak_alone",
        )
        self.assertIn("Shared memory is not shared permission", "".join(session.outputs))

        session.outputs.clear()
        session.command = "speak alone"
        asyncio.run(session.playing_prompt())
        self.assertIn(SPOREKIN_INDIVIDUAL_VOICE_FLAG, session.database.flags)
        self.assertEqual(
            session.database.get_quest(1, SPOREKIN_DEPTH_QUEST_KEY)["current_step"],
            "practice_husk",
        )

        session.outputs.clear()
        asyncio.run(session._finish_enemy_defeat(FakeEnemy()))
        self.assertIn(SPOREKIN_PRACTICE_HUSK_FLAG, session.database.flags)
        self.assertEqual(
            session.database.get_quest(1, SPOREKIN_DEPTH_QUEST_KEY)["current_step"],
            "return_nemm",
        )

        session.outputs.clear()
        session.command = "talk nemm"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, SPOREKIN_DEPTH_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(SPOREKIN_DEPTH_COMPLETE_FLAG, session.database.flags)
        self.assertIn("leave people enough room to become themselves", "".join(session.outputs))

    def test_sporekin_culture_commands_are_available(self):
        class Session(FakeSession):
            pass

        install_sporekin_depth_runtime(Session)
        session = Session("selfhood")
        asyncio.run(session.playing_prompt())
        self.assertIn("Sporekin Selfhood", "".join(session.outputs))


if __name__ == "__main__":
    unittest.main()
