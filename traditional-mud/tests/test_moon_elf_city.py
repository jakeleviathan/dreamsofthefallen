from __future__ import annotations

import asyncio
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import mud.character_options as character_options
import mud.world as world
from mud.database import Database
from mud.moon_elf_city import (
    CITY_LINES,
    GOVERNMENT_LINES,
    MOON_ELF_CITY_INTRO_FLAG,
    MOON_ELF_CITY_ROOM_KEYS,
    MOON_ELF_HORIZON_DECK_KEY,
    MOON_ELF_PENTHOUSE_ACCESS_FLAG,
    MOON_ELF_PENTHOUSE_KEY,
    MOON_ELF_REGION_KEY,
    MOON_ELF_START_ROOM_KEY,
    PENTHOUSE_LINES,
    SPIRE_LINES,
    _prepare_moon_elf_city,
    install_moon_elf_city_content,
    install_moon_elf_city_runtime,
    moon_elf_city_augmentations,
)
from mud.room_engine import PlayerRoomContext, WorldService
from mud.stats import CharacterStats


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
    name: str = "SelTest"
    race: str = "moon_elf"
    current_room: str = MOON_ELF_START_ROOM_KEY
    bind_room: str = MOON_ELF_START_ROOM_KEY


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


class MoonElfCityTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.races = character_options.RACES
        self.races_by_key = dict(character_options.RACES_BY_KEY)
        install_moon_elf_city_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        character_options.RACES = self.races
        character_options.RACES_BY_KEY.clear()
        character_options.RACES_BY_KEY.update(self.races_by_key)

    def test_horizon_council_turns_perspective_into_government_procedure(self):
        text = " ".join(GOVERNMENT_LINES).lower()
        self.assertIn("small rotating council", text)
        self.assertIn("rather than a monarch", text)
        self.assertIn("staggered civic terms", text)
        self.assertIn("counterview", text)
        self.assertIn("strongest serious case against", text)
        self.assertIn("conditions that would justify reopening", text)
        self.assertIn("changing one's mind in public", text)
        self.assertIn("civic institution, not a priesthood", text)

    def test_high_horizon_is_a_nine_room_safe_lived_in_starter_city(self):
        self.assertEqual(len(MOON_ELF_CITY_ROOM_KEYS), 9)
        augmentations = moon_elf_city_augmentations()
        for room_key in MOON_ELF_CITY_ROOM_KEYS:
            with self.subTest(room=room_key):
                room = world.ROOMS_BY_KEY[room_key]
                self.assertEqual(room.region_key, MOON_ELF_REGION_KEY)
                self.assertIn("safe", room.tags)
                self.assertEqual(room.enemy_keys, ())
                augmentation = augmentations[room_key]
                self.assertGreaterEqual(len(augmentation.features), 2)
                self.assertGreaterEqual(len(augmentation.description_layers), 1)
                overrides = {exit_def.direction: exit_def for exit_def in augmentation.exit_overrides}
                self.assertEqual(set(overrides), set(room.exits))

        city_text = " ".join(CITY_LINES).lower()
        self.assertIn("calm without being sleepy", city_text)
        self.assertIn("night", city_text)
        self.assertIn("small markets", city_text)
        self.assertIn("fantasy skyscraper", city_text)

    def test_city_scenes_are_rich_and_buildable(self):
        service = WorldService(
            rooms={room.key: room for room in world.ROOMS if room.key in MOON_ELF_CITY_ROOM_KEYS},
            augmentations=moon_elf_city_augmentations(),
        )
        context = PlayerRoomContext(
            character_id=1,
            race_key="moon_elf",
            class_key="wizard",
            level=1,
            hour=20,
        )
        for room_key in MOON_ELF_CITY_ROOM_KEYS:
            with self.subTest(room=room_key):
                view = service.build_view(room_key, context)
                self.assertIsNotNone(view)
                self.assertTrue(view.description.strip())
                self.assertGreaterEqual(len(view.features), 2)

    def test_skyglass_spire_is_skyscraper_and_penthouse_is_real_but_private(self):
        spire = " ".join(SPIRE_LINES).lower()
        penthouse = " ".join(PENTHOUSE_LINES).lower()
        self.assertIn("dozens of stories", spire)
        self.assertIn("skyscraper", spire)
        self.assertIn("high aerie penthouse", spire)
        self.assertIn("private penthouse suite", penthouse)
        self.assertIn("private observatory", penthouse)
        self.assertIn("rooftop garden", penthouse)
        self.assertIn("real home", penthouse)

        route = next(
            exit_def
            for exit_def in moon_elf_city_augmentations()[MOON_ELF_HORIZON_DECK_KEY].exit_overrides
            if exit_def.direction == "up"
        )
        self.assertEqual(route.destination_key, MOON_ELF_PENTHOUSE_KEY)
        self.assertEqual(route.condition.required_flags, (MOON_ELF_PENTHOUSE_ACCESS_FLAG,))
        self.assertFalse(route.hidden_when_unavailable)
        self.assertIn("residence", route.failure_text.lower())

    def test_new_moon_elf_without_location_is_placed_and_bound_in_high_horizon(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "moon-city.db")
            account = database.create_account("moon_city_test", "not-a-real-hash")
            character = database.create_character(
                account.id,
                "MoonCityTest",
                "moon_elf",
                "wizard",
                CharacterStats(might=5, grace=8, love=6, mind=10, hp=6),
            )
            self.assertIsNone(character.current_room)
            self.assertIsNone(character.bind_room)

            class Session:
                pass

            session = Session()
            session.database = database
            session.character = character
            self.assertTrue(_prepare_moon_elf_city(session))
            self.assertEqual(session.character.current_room, MOON_ELF_START_ROOM_KEY)
            self.assertEqual(session.character.bind_room, MOON_ELF_START_ROOM_KEY)

    def test_runtime_introduces_city_once_and_exposes_civic_and_penthouse_commands(self):
        class Session(FakeSession):
            pass

        world_service = WorldService(
            rooms={room.key: room for room in world.ROOMS if room.key in MOON_ELF_CITY_ROOM_KEYS},
            augmentations=moon_elf_city_augmentations(),
        )
        install_moon_elf_city_runtime(Session, world_service)
        session = Session("government")

        asyncio.run(session.enter_character())
        first = "".join(session.outputs).lower()
        self.assertIn("high horizon is home", first)
        self.assertIn("skyglass spire", first)
        self.assertIn(MOON_ELF_CITY_INTRO_FLAG, session.database.flags)

        session.outputs.clear()
        asyncio.run(session.enter_character())
        self.assertNotIn("high horizon is home", "".join(session.outputs).lower())

        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        government = "".join(session.outputs).lower()
        self.assertIn("horizon council", government)
        self.assertIn("counterview", government)

        session.outputs.clear()
        session.command = "skyscraper"
        asyncio.run(session.playing_prompt())
        self.assertIn("fantasy skyscraper", "".join(session.outputs).lower())

        session.outputs.clear()
        session.command = "my penthouse"
        asyncio.run(session.playing_prompt())
        penthouse = "".join(session.outputs).lower()
        self.assertIn("high aerie penthouse", penthouse)
        self.assertIn("not yet unlocked", penthouse)

        session.outputs.clear()
        session.command = "look"
        asyncio.run(session.playing_prompt())
        self.assertIn("base command: look", "".join(session.outputs).lower())

    def test_live_race_lore_includes_city_government_and_spire_without_inventing_deity(self):
        moon_elf = character_options.RACES_BY_KEY["moon_elf"]
        lore = " ".join(moon_elf.lore).lower()
        self.assertIn("high horizon", lore)
        self.assertIn("horizon council", lore)
        self.assertIn("counterview", lore)
        self.assertIn("skyglass spire", lore)
        self.assertIn("high aerie penthouse", lore)
        self.assertNotIn("moon god", lore)


if __name__ == "__main__":
    unittest.main()
