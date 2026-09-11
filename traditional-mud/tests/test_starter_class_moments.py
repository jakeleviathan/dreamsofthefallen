from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from mud.starter_class_moments import (
    CLASS_PRACTICE,
    RACE_OPENING_TRIGGERS,
    RACE_SETTINGS,
    all_starter_class_moments,
    install_starter_class_moment_runtime,
    starter_class_moment,
)


class FakeDatabase:
    def __init__(self) -> None:
        self.flags: set[str] = set()
        self.quests: dict[str, dict[str, str]] = {}
        self.advance_on_command = True

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def get_quest(self, _character_id: int, quest_key: str):
        quest = self.quests.get(quest_key)
        return None if quest is None else dict(quest)

    def set_trigger_quest(self, quest_key: str, step: str):
        self.quests[quest_key] = {
            "quest_key": quest_key,
            "status": "active",
            "current_step": step,
        }

    def advance_trigger_quest(self):
        if not self.advance_on_command:
            return
        for quest in self.quests.values():
            if quest["status"] == "active":
                quest["current_step"] = "next_authored_step"
                return


@dataclass
class FakeCharacter:
    id: int = 1
    race: str = "forest_elf"
    character_class: str = "wizard"
    level: int = 1
    deity_key: str | None = None


class FakeState:
    DISCONNECTED = "disconnected"


class FakeSession:
    def __init__(self, command: str = "talk mentor", character=None) -> None:
        self.character = character or FakeCharacter()
        self.database = FakeDatabase()
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
        self.database.advance_trigger_quest()


class StarterClassMomentTests(unittest.TestCase):
    def test_all_eight_by_five_combinations_exist(self):
        moments = all_starter_class_moments()
        self.assertEqual(len(RACE_SETTINGS), 8)
        self.assertEqual(len(CLASS_PRACTICE), 5)
        self.assertEqual(len(RACE_OPENING_TRIGGERS), 8)
        self.assertEqual(len(moments), 40)
        self.assertEqual(len({moment.flag_key for moment in moments}), 40)
        for race_key in RACE_SETTINGS:
            for class_key in CLASS_PRACTICE:
                self.assertIsNotNone(starter_class_moment(race_key, class_key))

    def test_moments_are_racially_framed_but_class_specific(self):
        forest_wizard = starter_class_moment("forest_elf", "wizard")
        dwarf_wizard = starter_class_moment("dwarf", "wizard")
        forest_brute = starter_class_moment("forest_elf", "brute")
        assert forest_wizard and dwarf_wizard and forest_brute
        self.assertNotEqual(forest_wizard.setting, dwarf_wizard.setting)
        self.assertEqual(forest_wizard.practice_text, dwarf_wizard.practice_text)
        self.assertNotEqual(forest_wizard.practice_text, forest_brute.practice_text)
        self.assertIn("Coldfire Burst", forest_wizard.practice_text)
        self.assertIn("Taunt", forest_brute.practice_text)

    def test_every_race_gets_class_training_when_real_opening_step_advances(self):
        for race_key, trigger in RACE_OPENING_TRIGGERS.items():
            with self.subTest(race=race_key):
                class Session(FakeSession):
                    pass

                install_starter_class_moment_runtime(Session)
                character = FakeCharacter(race=race_key, character_class="wizard")
                session = Session(character=character)
                session.database.set_trigger_quest(trigger.quest_key, trigger.trigger_step)

                asyncio.run(session.playing_prompt())
                output = "".join(session.outputs)
                moment = starter_class_moment(race_key, "wizard")
                assert moment is not None
                self.assertIn(moment.title, output)
                self.assertIn("Coldfire Burst", output)
                self.assertIn(trigger.closing, output)
                self.assertIn(moment.flag_key, session.database.flags)
                self.assertNotIn("CLASS MOMENT", output)
                self.assertNotIn("optional", output.lower())

    def test_invalid_or_nonadvancing_command_does_not_summon_training_scene(self):
        class Session(FakeSession):
            pass

        install_starter_class_moment_runtime(Session)
        session = Session(command="class moment")
        trigger = RACE_OPENING_TRIGGERS["forest_elf"]
        session.database.set_trigger_quest(trigger.quest_key, trigger.trigger_step)
        session.database.advance_on_command = False

        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("BASE COMMAND: class moment", output)
        self.assertNotIn("A Skill Among Living Things", output)
        self.assertNotIn("starter_class_moment_forest_elf_wizard", session.database.flags)

    def test_existing_completion_flag_prevents_replay(self):
        class Session(FakeSession):
            pass

        install_starter_class_moment_runtime(Session)
        session = Session()
        trigger = RACE_OPENING_TRIGGERS["forest_elf"]
        session.database.set_trigger_quest(trigger.quest_key, trigger.trigger_step)
        session.database.flags.add("starter_class_moment_forest_elf_wizard")

        asyncio.run(session.playing_prompt())
        self.assertNotIn("A Skill Among Living Things", "".join(session.outputs))

    def test_unknown_combination_is_not_invented(self):
        self.assertIsNone(starter_class_moment("dragon", "bard"))


if __name__ == "__main__":
    unittest.main()
