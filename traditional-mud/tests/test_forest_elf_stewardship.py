import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.mechanics as mechanics
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.forest_elf_nurture import (
    FOREST_ELF_HEARTSEED_QUEST,
    FOREST_ELF_NURTURE_COMPLETE_FLAG,
    _examine_heartseed,
    _gather_silvermoss,
    _initialize_or_reconcile_forest_elf,
    _talk_maelis,
    _wait_for_heartseed,
    forest_elf_nurture_augmentations,
    install_forest_elf_nurture_content,
)
from mud.forest_elf_stewardship import (
    AVEN_ROOTWAKE,
    DRUID_CIRCLE_FIRST_LESSON_FLAG,
    DRUID_FALSE_BLIGHT_COMPLETE_FLAG,
    DRUID_FALSE_BLIGHT_DIAGNOSED_FLAG,
    DRUID_FALSE_BLIGHT_QUEST,
    DRUID_LIVING_ANSWER_QUEST,
    DRUID_NURTURE_FIRST_USE_FLAG,
    FOREST_ELF_GREENWAY_KEY,
    FOREST_ELF_KEEPER_NURSERY_KEY,
    FOREST_ELF_OVERGROWTH_HOLLOW_KEY,
    FOREST_ELF_RAIN_BALANCED_FLAG,
    FOREST_ELF_RAINPOOL_TERRACE_KEY,
    FOREST_ELF_SEEPSTONE_RUN_KEY,
    FOREST_ELF_STEWARDSHIP_ROOM_KEYS,
    NURTURE_ABILITY,
    RAINPOOL_BALANCE_QUEST,
    SELA_RAINBOUGH,
    _druid_nurture_heartseed,
    _handle_druid_class_arc,
    _handle_rainpool_quest,
    _talk_aven,
    _talk_sela,
    forest_elf_stewardship_augmentations,
    install_forest_elf_stewardship_content,
)
from mud.room_engine import PlayerRoomContext, RoomAugmentation, WorldService
from mud.stats import CharacterStats
from mud.world import FOREST_ELF_START_ROOM_KEY


class LiveLikeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)

    def move_to(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        self.character = self.database.get_character_by_name(self.character.name)


class ForestElfStewardshipTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.druid_abilities = mechanics.FIXED_CLASS_ABILITIES.get("druid", ())
        install_forest_elf_nurture_content()
        install_forest_elf_stewardship_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        mechanics.FIXED_CLASS_ABILITIES["druid"] = self.druid_abilities

    def _session(self, *, name: str, race: str, class_key: str):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "forest_stewardship.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            race,
            class_key,
            CharacterStats(might=5, grace=7, love=8, mind=8, hp=9),
        )
        return temp, database, LiveLikeSession(database, character)

    def test_expansion_adds_four_safe_rooms_and_a_mixed_keeper_circle(self):
        self.assertEqual(len(FOREST_ELF_STEWARDSHIP_ROOM_KEYS), 4)
        for room_key in FOREST_ELF_STEWARDSHIP_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertEqual(room.region_key, "great_elf_forest")
            self.assertIn("safe", room.tags)
            self.assertEqual(room.enemy_keys, ())

        self.assertIn(FOREST_ELF_KEEPER_NURSERY_KEY, world.ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY].exits.values())
        self.assertEqual(world.NPCS_BY_KEY[SELA_RAINBOUGH.key].role, "non-Druid Circle water steward and Forest Elf starter mentor")
        self.assertIn("Druid", world.NPCS_BY_KEY[AVEN_ROOTWAKE.key].role)

    def test_nurture_is_registered_as_a_real_level_one_druid_ability(self):
        abilities = mechanics.FIXED_CLASS_ABILITIES["druid"]
        nurture = next((ability for ability in abilities if ability.key == "nurture"), None)
        self.assertIsNotNone(nurture)
        self.assertEqual(nurture, NURTURE_ABILITY)
        self.assertEqual(nurture.unlock_level, 1)
        self.assertEqual(nurture.category, "nature_utility")
        self.assertIn("does not create life", nurture.description.lower())

    def test_druid_only_overgrowth_route_is_hidden_from_other_classes(self):
        augmentations = forest_elf_stewardship_augmentations()
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=augmentations)
        druid = PlayerRoomContext(character_id=1, race_key="human", class_key="druid", level=1)
        brute = PlayerRoomContext(character_id=2, race_key="forest_elf", class_key="brute", level=1)

        allowed = service.resolve_exit(FOREST_ELF_KEEPER_NURSERY_KEY, "north", druid)
        denied = service.resolve_exit(FOREST_ELF_KEEPER_NURSERY_KEY, "north", brute)
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.exit.destination_key, FOREST_ELF_OVERGROWTH_HOLLOW_KEY)
        self.assertFalse(denied.allowed)

    def test_forest_elf_druid_heartseed_uses_nurture_and_records_ability_progress(self):
        temp, database, session = self._session(name="FernDruid", race="forest_elf", class_key="druid")
        self.addCleanup(temp.cleanup)
        _initialize_or_reconcile_forest_elf(session)

        self.assertTrue(asyncio.run(_talk_maelis(session)))
        self.assertTrue(asyncio.run(_examine_heartseed(session)))
        self.assertTrue(asyncio.run(_gather_silvermoss(session)))
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "tend_heartseed")

        self.assertTrue(asyncio.run(_druid_nurture_heartseed(session)))
        self.assertEqual(database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)["current_step"], "wait_for_growth")
        self.assertIn(DRUID_NURTURE_FIRST_USE_FLAG, database.list_flags(session.character.id))
        progress = {row["ability_key"]: row for row in database.list_ability_progress(session.character.id)}
        self.assertEqual(progress["nurture"]["uses"], 1)

        self.assertTrue(asyncio.run(_wait_for_heartseed(session)))
        self.assertTrue(asyncio.run(_talk_maelis(session)))
        self.assertIn(FOREST_ELF_NURTURE_COMPLETE_FLAG, database.list_flags(session.character.id))

    def test_non_druid_forest_elf_gets_water_stewardship_without_class_requirement(self):
        temp, database, session = self._session(name="RiverBrute", race="forest_elf", class_key="brute")
        self.addCleanup(temp.cleanup)
        database.grant_flag(session.character.id, FOREST_ELF_NURTURE_COMPLETE_FLAG)
        session.move_to(FOREST_ELF_GREENWAY_KEY)

        self.assertTrue(asyncio.run(_talk_sela(session)))
        self.assertEqual(database.get_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key)["current_step"], "inspect_pools")

        session.move_to(FOREST_ELF_RAINPOOL_TERRACE_KEY)
        self.assertTrue(asyncio.run(_handle_rainpool_quest(session, "examine rain pools")))
        session.move_to(FOREST_ELF_SEEPSTONE_RUN_KEY)
        self.assertTrue(asyncio.run(_handle_rainpool_quest(session, "examine leaf dam")))
        self.assertTrue(asyncio.run(_handle_rainpool_quest(session, "clear leaf dam")))
        self.assertTrue(asyncio.run(_handle_rainpool_quest(session, "listen water")))
        session.move_to(FOREST_ELF_GREENWAY_KEY)
        self.assertTrue(asyncio.run(_talk_sela(session)))

        quest = database.get_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(FOREST_ELF_RAIN_BALANCED_FLAG, database.list_flags(session.character.id))
        self.assertNotIn("nurture", {row["ability_key"] for row in database.list_ability_progress(session.character.id)})

    def test_visiting_non_elf_druid_can_complete_both_circle_class_lessons(self):
        temp, database, session = self._session(name="HumanDruid", race="human", class_key="druid")
        self.addCleanup(temp.cleanup)
        session.move_to(FOREST_ELF_KEEPER_NURSERY_KEY)

        self.assertTrue(asyncio.run(_talk_aven(session)))
        self.assertEqual(database.get_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key)["current_step"], "inspect_runner")
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "examine teaching runner")))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "nurture runner")))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "wait")))
        self.assertTrue(asyncio.run(_talk_aven(session)))
        self.assertIn(DRUID_CIRCLE_FIRST_LESSON_FLAG, database.list_flags(session.character.id))

        # A second conversation begins the diagnosis lesson.
        self.assertTrue(asyncio.run(_talk_aven(session)))
        self.assertEqual(database.get_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key)["current_step"], "inspect_overgrowth")
        session.move_to(FOREST_ELF_OVERGROWTH_HOLLOW_KEY)
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "cut vine")))
        self.assertEqual(database.get_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key)["current_step"], "inspect_overgrowth")
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "examine overgrowth")))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "examine sapling")))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "diagnose overgrowth")))
        self.assertIn(DRUID_FALSE_BLIGHT_DIAGNOSED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "nurture sapling")))
        self.assertTrue(asyncio.run(_handle_druid_class_arc(session, "wait")))
        session.move_to(FOREST_ELF_KEEPER_NURSERY_KEY)
        self.assertTrue(asyncio.run(_talk_aven(session)))

        second = database.get_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key)
        self.assertEqual(second["status"], "completed")
        self.assertIn(DRUID_FALSE_BLIGHT_COMPLETE_FLAG, database.list_flags(session.character.id))
        progress = {row["ability_key"]: row for row in database.list_ability_progress(session.character.id)}
        self.assertEqual(progress["nurture"]["uses"], 2)

    def test_new_rooms_have_rich_features_and_named_routes(self):
        combined: dict[str, RoomAugmentation] = dict(forest_elf_nurture_augmentations())
        for room_key, extra in forest_elf_stewardship_augmentations().items():
            existing = combined.get(room_key)
            if existing is None:
                combined[room_key] = extra
            else:
                combined[room_key] = RoomAugmentation(
                    exit_overrides=existing.exit_overrides + extra.exit_overrides,
                    extra_exits=existing.extra_exits + extra.extra_exits,
                    features=existing.features + extra.features,
                    description_layers=existing.description_layers + extra.description_layers,
                )
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=combined)
        context = PlayerRoomContext(character_id=1, race_key="forest_elf", class_key="druid", level=1)
        for room_key in FOREST_ELF_STEWARDSHIP_ROOM_KEYS:
            view = service.build_view(room_key, context)
            self.assertIsNotNone(view)
            self.assertGreaterEqual(len(view.features), 1)
            for exit_view in view.exits:
                self.assertTrue(exit_view.name)


if __name__ == "__main__":
    unittest.main()
