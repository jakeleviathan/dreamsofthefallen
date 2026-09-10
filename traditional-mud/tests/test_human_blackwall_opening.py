from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.human_blackwall_opening import (
    HUMAN_BEYOND_WALL_QUEST,
    HUMAN_BURROWER_DEFEATED_FLAG,
    HUMAN_CARAVAN_DEMON_WORD_FLAG,
    HUMAN_CARAVAN_QUEST,
    HUMAN_CARAVAN_COURT_KEY,
    HUMAN_CINDER_WARD_KEY,
    HUMAN_DAMAGE_READ_FLAG,
    HUMAN_EARTH_ARTIFACT_IDENTIFIED_FLAG,
    HUMAN_EARTH_CACHE_QUEST,
    HUMAN_EARTH_HANDSET_KEY,
    HUMAN_FAST_LEARNER_DRILL_FLAG,
    HUMAN_GATE_CLEARANCE_FLAG,
    HUMAN_NEST_SEARCHED_FLAG,
    HUMAN_OPENING_COMPLETE_FLAG,
    HUMAN_OPENING_GRANDFATHERED_FLAG,
    HUMAN_OPENING_ROOM_KEYS,
    HUMAN_OUTER_CARAVAN_ROAD_KEY,
    HUMAN_READINESS_QUEST,
    HUMAN_READINESS_YARD_KEY,
    HUMAN_SMUGGLER_CACHE_FLAG,
    HUMAN_SMUGGLER_CISTERN_KEY,
    HUMAN_SOOTSTEP_MOUTH_KEY,
    HUMAN_SOOTSTEP_TUNNEL_KEY,
    HUMAN_ARCHIVE_ANNEX_KEY,
    complete_first_outside_step,
    handle_human_opening_command,
    human_opening_augmentations,
    install_human_blackwall_content,
    prepare_human_blackwall_opening,
    record_burrower_defeat,
)


class FakeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []

    async def send(self, text: str):
        self.outputs.append(text)


def move(session: FakeSession, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    refreshed = session.database.get_character_by_name(session.character.name)
    assert refreshed is not None
    session.character = refreshed


class HumanBlackwallOpeningTests(unittest.TestCase):
    def setUp(self):
        self.rooms = legacy_world.ROOMS
        self.rooms_by_key = dict(legacy_world.ROOMS_BY_KEY)
        self.npcs = legacy_world.NPCS
        self.npcs_by_key = dict(legacy_world.NPCS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        install_human_blackwall_content()

    def tearDown(self):
        legacy_world.ROOMS = self.rooms
        legacy_world.ROOMS_BY_KEY.clear()
        legacy_world.ROOMS_BY_KEY.update(self.rooms_by_key)
        legacy_world.NPCS = self.npcs
        legacy_world.NPCS_BY_KEY.clear()
        legacy_world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)

    def _session(self, name: str = "Cinder"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "human.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(account.id, name, "human", "wizard")
        return temp, database, FakeSession(database, character)

    def test_fresh_human_is_moved_inside_blackwall_and_cathedral_is_deferred(self):
        temp, database, session = self._session("Fresh")
        self.addCleanup(temp.cleanup)

        self.assertEqual(session.character.current_room, legacy_world.HUMAN_START_ROOM_KEY)
        self.assertTrue(prepare_human_blackwall_opening(session))
        self.assertEqual(session.character.current_room, HUMAN_CINDER_WARD_KEY)
        self.assertEqual(session.character.bind_room, HUMAN_CINDER_WARD_KEY)

        readiness = database.get_quest(session.character.id, HUMAN_READINESS_QUEST.key)
        self.assertEqual(readiness["current_step"], "report_muster")
        cathedral = database.get_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        self.assertEqual(cathedral["status"], "active")
        self.assertEqual(cathedral["current_step"], "await_blackwall_handoff")

    def test_progressed_legacy_human_is_grandfathered_without_reset(self):
        temp, database, session = self._session("Veteran")
        self.addCleanup(temp.cleanup)
        database.complete_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        original_room = session.character.current_room

        self.assertFalse(prepare_human_blackwall_opening(session))
        self.assertEqual(session.character.current_room, original_room)
        self.assertIn(HUMAN_OPENING_GRANDFATHERED_FLAG, database.list_flags(session.character.id))
        self.assertIsNone(database.get_quest(session.character.id, HUMAN_READINESS_QUEST.key))

    def test_new_rooms_are_rich_and_demon_gate_gains_world_handoff(self):
        augmentations = human_opening_augmentations()
        self.assertEqual(set(augmentations), set(HUMAN_OPENING_ROOM_KEYS))
        for room_key in HUMAN_OPENING_ROOM_KEYS:
            room = legacy_world.ROOMS_BY_KEY[room_key]
            augmentation = augmentations[room_key]
            self.assertGreaterEqual(len(augmentation.features), 2)
            self.assertGreaterEqual(len(augmentation.description_layers), 1)
            self.assertEqual(
                {exit_def.direction for exit_def in augmentation.exit_overrides},
                set(room.exits),
            )

        gate = legacy_world.ROOMS_BY_KEY[legacy_world.HUMAN_START_ROOM_KEY]
        self.assertEqual(gate.exits["east"], HUMAN_OUTER_CARAVAN_ROAD_KEY)
        self.assertIn("human_gatewarden_sera_thorn", gate.npc_keys)

    def test_full_four_quest_arc_reveals_identity_by_evidence_not_exposition_dump(self):
        temp, database, session = self._session("Walker")
        self.addCleanup(temp.cleanup)
        self.assertTrue(prepare_human_blackwall_opening(session))

        # Quest 1: ordinary civic readiness and a concrete Fast Learner moment.
        move(session, HUMAN_READINESS_YARD_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "talk mara")))
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "examine signal board")))
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "drill signals")))
        self.assertIn(HUMAN_FAST_LEARNER_DRILL_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "report ready")))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_READINESS_QUEST.key)["status"], "completed")
        self.assertEqual(database.get_quest(session.character.id, HUMAN_CARAVAN_QUEST.key)["current_step"], "meet_caravan")

        # Quest 2: Dwarven neighbor uses "Demon" casually; physical damage leads to a real tunnel threat.
        move(session, HUMAN_CARAVAN_COURT_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "talk ketta")))
        self.assertIn(HUMAN_CARAVAN_DEMON_WORD_FLAG, database.list_flags(session.character.id))
        self.assertIn("demons", "".join(session.outputs).lower())
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "examine wagon")))
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "read damage")))
        self.assertIn(HUMAN_DAMAGE_READ_FLAG, database.list_flags(session.character.id))
        move(session, HUMAN_SOOTSTEP_MOUTH_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "follow sign")))
        move(session, HUMAN_SOOTSTEP_TUNNEL_KEY)
        self.assertTrue(record_burrower_defeat(session))
        self.assertIn(HUMAN_BURROWER_DEFEATED_FLAG, database.list_flags(session.character.id))
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "search nest")))
        self.assertIn(HUMAN_NEST_SEARCHED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_CARAVAN_QUEST.key)["status"], "completed")

        # Quest 3: the secret route is Human-made; an inert Earth object confirms the origin story.
        move(session, HUMAN_SMUGGLER_CISTERN_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "search cache")))
        self.assertIn(HUMAN_SMUGGLER_CACHE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.item_quantity(session.character.id, HUMAN_EARTH_HANDSET_KEY), 1)
        move(session, HUMAN_ARCHIVE_ANNEX_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "talk orrin")))
        self.assertIn(HUMAN_EARTH_ARTIFACT_IDENTIFIED_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.item_quantity(session.character.id, HUMAN_EARTH_HANDSET_KEY), 0)
        self.assertIn("no road back", "".join(session.outputs).lower())
        self.assertEqual(database.get_quest(session.character.id, HUMAN_EARTH_CACHE_QUEST.key)["status"], "completed")

        # Quest 4: the gate opens, then the old cathedral thread is released rather than erased.
        move(session, legacy_world.HUMAN_START_ROOM_KEY)
        self.assertTrue(asyncio.run(handle_human_opening_command(session, "talk gatewarden")))
        self.assertIn(HUMAN_GATE_CLEARANCE_FLAG, database.list_flags(session.character.id))
        move(session, HUMAN_OUTER_CARAVAN_ROAD_KEY)
        self.assertTrue(complete_first_outside_step(session))
        self.assertIn(HUMAN_OPENING_COMPLETE_FLAG, database.list_flags(session.character.id))
        self.assertEqual(database.get_quest(session.character.id, HUMAN_BEYOND_WALL_QUEST.key)["status"], "completed")
        cathedral = database.get_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        self.assertEqual(cathedral["current_step"], "read_note")

    def test_cathedral_note_cannot_skip_the_new_opening(self):
        temp, database, session = self._session("Sealed")
        self.addCleanup(temp.cleanup)
        prepare_human_blackwall_opening(session)
        handled = asyncio.run(handle_human_opening_command(session, "read note"))
        self.assertTrue(handled)
        cathedral = database.get_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key)
        self.assertEqual(cathedral["current_step"], "await_blackwall_handoff")
        self.assertIn("readiness duty", "".join(session.outputs).lower())


if __name__ == "__main__":
    unittest.main()
