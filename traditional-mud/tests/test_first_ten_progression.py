import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.mechanics as mechanics
import mud.quests as quests
from mud.first_ten_progression import (
    CLASS_CAPSTONE_ABILITIES,
    RACE_FIRST_TEN_ARCS,
    install_first_ten_content,
    install_first_ten_runtime,
)
from mud.priest_early_progression import PRIEST_FOUNDATION_ABILITIES
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


class _FakeDatabase:
    def __init__(self, character):
        self.character = character
        self.flags = {STARTER_RACE_LOOPS_BY_RACE[character.race].completion_flag}
        self.quests = {}
        self.xp_awards = []

    def list_flags(self, _character_id):
        return frozenset(self.flags)

    def grant_flag(self, _character_id, flag_key):
        self.flags.add(flag_key)

    def get_quest(self, _character_id, quest_key):
        row = self.quests.get(quest_key)
        return None if row is None else dict(row)

    def start_quest(self, _character_id, quest_key, current_step):
        self.quests.setdefault(quest_key, {
            "quest_key": quest_key,
            "status": "active",
            "current_step": current_step,
        })

    def advance_quest(self, _character_id, quest_key, current_step):
        self.quests[quest_key]["current_step"] = current_step

    def complete_quest(self, _character_id, quest_key):
        self.quests[quest_key]["status"] = "completed"
        self.quests[quest_key]["current_step"] = "complete"

    def add_experience(self, _character_id, amount):
        self.xp_awards.append(amount)
        return self.character.level

    def get_character_by_name(self, _name):
        return self.character


class _FakeSession:
    _first_ten_runtime_installed = False

    def __init__(self):
        loop = STARTER_RACE_LOOPS_BY_RACE["goblin"]
        self.character = SimpleNamespace(
            id=7,
            name="Rivet",
            race="goblin",
            character_class="brute",
            deity_key=None,
            level=4,
            current_room=loop.starting_room_key,
        )
        self.database = _FakeDatabase(self.character)
        self.messages = []
        self.commands = []
        self.delegated = []
        self.combatant = None
        self.active_enemy = None

    async def send(self, text):
        self.messages.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text):
        return self.commands.pop(0) if self.commands else "look"

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.delegated.append(command)

    async def use_ability(self, _ability_text):
        return None


def _install_runtime_for_fake_session(session_class):
    """Satisfy the production contract without polluting global Priest catalogs.

    Production installs the Priest 1-10 foundation immediately before this runtime.
    These small fake-session tests do not boot the production entrypoint, so we
    temporarily expose the canonical Priest foundation only while the installer
    validates its dependency, then restore the exact original deity registries.
    """
    original = {
        path_key: tuple(abilities)
        for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items()
    }
    try:
        for path_key, current in tuple(mechanics.PRIEST_DEITY_ABILITIES.items()):
            by_key = {ability.key: ability for ability in current}
            for definition in PRIEST_FOUNDATION_ABILITIES:
                by_key[definition.key] = definition
            mechanics.PRIEST_DEITY_ABILITIES[path_key] = tuple(by_key.values())
        install_first_ten_runtime(session_class)
    finally:
        mechanics.PRIEST_DEITY_ABILITIES.clear()
        mechanics.PRIEST_DEITY_ABILITIES.update(original)


class FirstTenProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register the new non-Priest capstones and racial quests in this process.
        # Priest foundation installation is deliberately tested in subprocesses so
        # the historic level-one deity catalog tests remain isolated and exact.
        install_first_ten_content()

    def test_all_eight_races_have_three_real_post_opening_beats(self):
        self.assertEqual(set(RACE_FIRST_TEN_ARCS), set(STARTER_RACE_LOOPS_BY_RACE))
        for race_key, arc in RACE_FIRST_TEN_ARCS.items():
            with self.subTest(race=race_key):
                self.assertEqual(tuple(beat.unlock_level for beat in arc.beats), (4, 8, 10))
                for beat in arc.beats:
                    self.assertGreaterEqual(len(beat.steps), 3)
                    self.assertIn(beat.quest_key(race_key), quests.QUESTS_BY_KEY)

    def test_every_class_has_a_level_ten_capstone(self):
        for class_key in ("brute", "wizard", "druid", "necromancer"):
            with self.subTest(character_class=class_key):
                expected = CLASS_CAPSTONE_ABILITIES[class_key].key
                level_ten = mechanics.class_abilities_for_level(class_key, 10)
                self.assertIn(expected, {ability.key for ability in level_ten})

        # Priest's complete 1-10 foundation is installed by the production entrypoint.
        # Check its canonical definition here without mutating the shared deity registry.
        priest_capstones = {
            ability.key: ability.unlock_level for ability in PRIEST_FOUNDATION_ABILITIES
        }
        self.assertEqual(priest_capstones.get("divine_concord"), 10)

    def test_contract_validator_accepts_complete_first_ten(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
from mud.priest_early_progression import install_priest_early_progression_content
from mud.first_ten_progression import install_first_ten_content, validate_first_ten_contract

install_priest_early_progression_content()
install_first_ten_content()
validate_first_ten_contract()
print("FIRST_TEN_CONTRACT_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("FIRST_TEN_CONTRACT_OK", result.stdout)

    def test_goblin_level_four_arc_is_persistent_playable_content(self):
        class Session(_FakeSession):
            _first_ten_runtime_installed = False

        _install_runtime_for_fake_session(Session)
        session = Session()
        beat = RACE_FIRST_TEN_ARCS["goblin"].act_two

        async def play():
            session.commands = [step.command for step in beat.steps]
            for _ in beat.steps:
                await session.playing_prompt()

        asyncio.run(play())

        self.assertIn(beat.completion_flag("goblin"), session.database.flags)
        state = session.database.get_quest(session.character.id, beat.quest_key("goblin"))
        self.assertEqual(state["status"], "completed")
        self.assertEqual(session.database.xp_awards, [beat.xp_reward])
        text = "".join(session.messages)
        self.assertIn("The Sinking Heap complete", text)
        self.assertIn("Goblin usefulness", text)

    def test_heritage_command_exposes_current_act_and_future_level_gates(self):
        class Session(_FakeSession):
            _first_ten_runtime_installed = False

        _install_runtime_for_fake_session(Session)

        # First, a normal level-four Goblin sees the immediately playable home crisis.
        session = Session()
        session.commands = ["heritage"]
        asyncio.run(session.playing_prompt())
        text = "".join(session.messages)
        self.assertIn("Level 1-10 Heritage Arc", text)
        self.assertIn("Act II - The Sinking Heap: active", text)

        # Once that act is complete, HERITAGE shows the next two level gates without
        # starting them early or turning all three acts into simultaneous quests.
        gated = Session()
        act_two = RACE_FIRST_TEN_ARCS["goblin"].act_two
        gated.database.grant_flag(gated.character.id, act_two.completion_flag("goblin"))
        gated.commands = ["heritage"]
        asyncio.run(gated.playing_prompt())
        gated_text = "".join(gated.messages)
        self.assertIn("Act II - The Sinking Heap: complete", gated_text)
        self.assertIn("Act III - Useful to Strangers: unlocks at level 8", gated_text)
        self.assertIn("Capstone - The Heap That Stayed Up: unlocks at level 10", gated_text)

    def test_production_entrypoint_installs_first_ten_runtime(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.mechanics as mechanics
import mud.quests as quests
from mud.first_ten_progression import RACE_FIRST_TEN_ARCS

assert server.PlayerSession._first_ten_runtime_installed
assert len(RACE_FIRST_TEN_ARCS) == 8
assert len([key for key in quests.QUESTS_BY_KEY if key.startswith("first_ten_")]) == 24
for class_key in ("brute", "wizard", "druid", "necromancer"):
    assert any(a.unlock_level == 10 for a in mechanics.FIXED_CLASS_ABILITIES[class_key]), class_key
for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items():
    assert any(a.key == "divine_concord" and a.unlock_level == 10 for a in abilities), path_key
print("FIRST_TEN_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("FIRST_TEN_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
