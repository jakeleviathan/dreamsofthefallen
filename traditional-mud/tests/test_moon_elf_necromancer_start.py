from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.moon_elf_city import MOON_ELF_JOURNAL_GALLERY_KEY, install_moon_elf_city_content
from mud.moon_elf_necromancer_start import (
    MOON_ELF_AFTERIMAGE_NICHE_KEY,
    MOON_ELF_NECROMANCER_COMPLETE_FLAG,
    MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG,
    MOON_ELF_NECROMANCER_EDGES_FLAG,
    MOON_ELF_NECROMANCER_FADED_FLAG,
    MOON_ELF_NECROMANCER_QUEST,
    MOON_ELF_NECROMANCER_QUEST_KEY,
    MOON_ELF_NECROMANCER_TRACE_FLAG,
    MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG,
    SAEL_ORUNE_KEY,
    install_moon_elf_necromancer_content,
    install_moon_elf_necromancer_runtime,
    moon_elf_necromancer_augmentations,
)
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG, install_third_chair_content
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self, *, third_chair_complete: bool = True) -> None:
        self.flags: set[str] = set()
        if third_chair_complete:
            self.flags.add(MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG)
        self.quests: dict[str, dict[str, str | None]] = {}
        self.ability_uses: list[tuple[int, str, int]] = []

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def get_quest(self, _character_id: int, quest_key: str):
        row = self.quests.get(quest_key)
        return None if row is None else dict(row)

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

    def record_ability_use(self, character_id: int, ability_key: str, skill_xp_gain: int = 1):
        self.ability_uses.append((character_id, ability_key, skill_xp_gain))


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Vaelis"
    race: str = "moon_elf"
    character_class: str = "necromancer"
    deity_key: str | None = None
    current_room: str = MOON_ELF_JOURNAL_GALLERY_KEY
    level: int = 1


class FakeState:
    DISCONNECTED = "disconnected"


class FakeSession:
    def __init__(self, command: str = "", *, character=None, database=None) -> None:
        self.character = character or FakeCharacter()
        self.database = database or FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = FakeState()

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


class MoonElfNecromancerStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_moon_elf_city_content()
        install_third_chair_content()
        install_moon_elf_necromancer_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quest_map)

    def test_content_adds_safe_afterimage_niche_and_grounded_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[MOON_ELF_NECROMANCER_QUEST_KEY], MOON_ELF_NECROMANCER_QUEST)
        room = world.ROOMS_BY_KEY[MOON_ELF_AFTERIMAGE_NICHE_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("necromancer", room.tags)
        self.assertIn("observation", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(SAEL_ORUNE_KEY, room.npc_keys)
        self.assertEqual(
            world.ROOMS_BY_KEY[MOON_ELF_JOURNAL_GALLERY_KEY].exits["north"],
            MOON_ELF_AFTERIMAGE_NICHE_KEY,
        )

        augmentation = moon_elf_necromancer_augmentations()[MOON_ELF_AFTERIMAGE_NICHE_KEY]
        self.assertGreaterEqual(len(augmentation.features), 5)
        self.assertGreaterEqual(len(augmentation.description_layers), 3)

    def test_world_service_gets_named_route_from_journal_gallery(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_moon_elf_necromancer_content(service)
        context = PlayerRoomContext(character_id=1, race_key="moon_elf", class_key="necromancer", level=1)
        result = service.resolve_exit(MOON_ELF_JOURNAL_GALLERY_KEY, "north", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, MOON_ELF_AFTERIMAGE_NICHE_KEY)
        self.assertEqual(result.exit.name, "Afterimage Niche")

    def test_only_moon_elf_necromancer_gets_extension_after_third_chair(self):
        class NecromancerSession(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(NecromancerSession)
        necromancer = NecromancerSession()
        asyncio.run(necromancer.enter_character())
        quest = necromancer.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_sael")
        self.assertIn("The Shape Left Behind", "".join(necromancer.outputs))

        class WizardSession(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard"))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY))

        class ForestNecromancerSession(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(ForestNecromancerSession)
        forest_necromancer = ForestNecromancerSession(character=FakeCharacter(race="forest_elf"))
        asyncio.run(forest_necromancer.enter_character())
        self.assertIsNone(forest_necromancer.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY))

    def test_extension_waits_until_shared_moon_elf_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(Session)
        session = Session(database=FakeDatabase(third_chair_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY))

    def test_full_sequence_maps_two_views_and_lets_residue_fade_without_spell_use(self):
        class Session(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_AFTERIMAGE_NICHE_KEY

        for command, expected_step in (
            ("talk sael", "inspect_niche"),
            ("examine cushion", "trace_residue"),
            ("trace residue", "compare_views"),
            ("view from doorway", "compare_views"),
            ("view from window", "map_edges"),
            ("mark edges", "let_fade"),
            ("wait for fade", "return_sael"),
        ):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(MOON_ELF_NECROMANCER_TRACE_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_NECROMANCER_EDGES_FLAG, session.database.flags)
        self.assertIn(MOON_ELF_NECROMANCER_FADED_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [])

        session.command = "talk sael"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(MOON_ELF_NECROMANCER_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("not everything that lingers is a voice", output)
        self.assertIn("no voice answers", output)
        self.assertIn("perspective did not make the first reading false", output)
        self.assertIn("no final message arrives", output)
        self.assertIn("none of those facts made it teren", output)
        self.assertIn("discern first", output)

    def test_dramatic_interference_is_refused_and_does_not_advance_quest(self):
        class Session(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_AFTERIMAGE_NICHE_KEY
        session.database.advance_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY, "trace_residue")

        for command in ("talk teren", "bind residue", "life tap residue", "raise corpse"):
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)
            self.assertEqual(quest["current_step"], "trace_residue")

        self.assertEqual(session.database.ability_uses, [])
        output = "".join(session.outputs).lower()
        self.assertIn("do not manufacture permission from atmosphere", output)

    def test_compare_views_can_be_done_in_either_order(self):
        class Session(FakeSession):
            pass

        install_moon_elf_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = MOON_ELF_AFTERIMAGE_NICHE_KEY
        session.database.advance_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY, "compare_views")

        session.command = "view from window"
        asyncio.run(session.playing_prompt())
        self.assertEqual(
            session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)["current_step"],
            "compare_views",
        )
        session.command = "view from doorway"
        asyncio.run(session.playing_prompt())
        self.assertEqual(
            session.database.get_quest(1, MOON_ELF_NECROMANCER_QUEST_KEY)["current_step"],
            "map_edges",
        )


if __name__ == "__main__":
    unittest.main()
