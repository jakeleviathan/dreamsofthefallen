from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.crafting as crafting
import mud.world as legacy_world
from mud.collective_wiki import collective_wiki_snapshot
from mud.database import Database
from mud.discovery_engine import attempt_discovery_command, discovery_record
from mud.endgame_omens import (
    BELL_COMPARISON,
    BELL_RESONANCE,
    BURIED_MURAL,
    CHALK_CIPHER,
    CHILD_REFRAIN,
    CLAPPERLESS_BELL_KEY,
    EMPTY_BELFRY,
    MISSING_NOTE,
    NOON_ALIGNMENT,
    OMEN_DEFINITIONS,
    OMEN_FEATURES,
    OMEN_REGISTRY,
    NIMRA,
    install_endgame_omens_content,
    install_endgame_omens_runtime,
    threshold_echoes,
)
from mud.goblin_start import GOBLIN_PATCHWORK_PLAZA_KEY, GOBLIN_ROOMS
from mud.living_world import PULSE_TEMPLATES
from mud.npcs import MobileNpcManager
from mud.npc_conversation import resolve_static_talk_target
from mud.roadside_discoveries import NOON_LENS_KEY, QUIET_BELFRY_KEY, ROADSIDE_ROOMS
from mud.room_engine import WorldService
from mud.waymeet_frontier import (
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_ROOMS,
)
from mud.waymeet_living_npcs import EDRIN, chatter_lines


class TestSession:
    def __init__(self, database, character, world):
        self.database = database
        self.character = character
        self._discovery_world_service = world
        self.outputs = []

    async def send(self, text: str) -> None:
        self.outputs.append(text)


class OmenContentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Database(Path(self.temp.name) / "omens.db")
        account = self.database.create_account("omen_seeker", "hash")
        self.character = self.database.create_character(account.id, "OmenSeeker", "human", "wizard")
        rooms = {r.key: r for r in (*GOBLIN_ROOMS, *WAYMEET_ROOMS, *ROADSIDE_ROOMS)}
        self.world = WorldService(rooms)
        install_endgame_omens_content(self.world)
        self.session = TestSession(self.database, self.character, self.world)

    def move(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        self.character = self.database.get_character_by_name("OmenSeeker")
        self.session.character = self.character

    async def discover(self, room_key: str, command: str):
        self.move(room_key)
        return await attempt_discovery_command(
            self.session, self.world, command, registry=OMEN_REGISTRY,
        )

    def test_installer_is_idempotent_and_preserves_existing_room_features(self):
        before = {
            key: {f.key for f in self.world.scene(key).features}
            for key in OMEN_FEATURES
        }
        install_endgame_omens_content(self.world)
        after = {
            key: {f.key for f in self.world.scene(key).features}
            for key in OMEN_FEATURES
        }
        self.assertEqual(before, after)
        self.assertEqual(
            len(self.world.scene(GOBLIN_PATCHWORK_PLAZA_KEY).features),
            len(before[GOBLIN_PATCHWORK_PLAZA_KEY]),
        )
        self.assertIn(CLAPPERLESS_BELL_KEY, crafting.ITEMS_BY_KEY)
        self.assertEqual(crafting.ITEMS_BY_KEY[CLAPPERLESS_BELL_KEY].category, "curio")
        self.assertEqual(legacy_world.NPCS_BY_KEY[NIMRA.key], NIMRA)
        self.assertEqual(
            len([npc for npc in legacy_world.NPCS if npc.key == NIMRA.key]), 1,
        )
        self.assertIn(NIMRA.key, self.world.scene(WAYMEET_COMMONHOUSE_KEY).npc_keys)
        talk_target, ambiguous = resolve_static_talk_target(
            self.world, legacy_world.NPCS_BY_KEY, WAYMEET_COMMONHOUSE_KEY, "nimra",
        )
        self.assertEqual(talk_target, NIMRA)
        self.assertFalse(ambiguous)

    async def test_mural_is_optional_persistent_and_populates_living_wiki(self):
        first = await self.discover(GOBLIN_PATCHWORK_PLAZA_KEY, "examine mural")
        second = await self.discover(GOBLIN_PATCHWORK_PLAZA_KEY, "examine mural")
        self.assertTrue(first.discovered)
        self.assertTrue(first.handled)
        self.assertFalse(second.discovered)
        self.assertEqual(first.definition.key, BURIED_MURAL)
        self.assertIsNotNone(discovery_record(self.database, self.character.id, BURIED_MURAL))
        self.assertEqual(" ".join(self.session.outputs).count("Whoever made this"), 1)
        wiki = collective_wiki_snapshot(self.database)
        discovered = [entry for entry in wiki["entries"]
                      if entry["category"] == "discovery" and entry["key"] == BURIED_MURAL]
        self.assertEqual(len(discovered), 1)

    async def test_any_race_can_find_waymeet_clues_without_starting_in_junk_city(self):
        self.move(WAYMEET_CROSSROADS_KEY)
        self.assertTrue((await self.discover(WAYMEET_CROSSROADS_KEY, "read chalk marks")).discovered)
        self.assertTrue((await self.discover(WAYMEET_COMMONHOUSE_KEY, "listen humming")).discovered)
        self.assertIsNone(discovery_record(self.database, self.character.id, BURIED_MURAL))
        self.assertIsNotNone(discovery_record(self.database, self.character.id, CHALK_CIPHER))
        self.assertIsNotNone(discovery_record(self.database, self.character.id, CHILD_REFRAIN))
        self.assertNotIn("Hinge", " ".join(self.session.outputs))

    async def test_relic_only_resonates_if_actually_owned_and_merchant_sells_it_occasionally(self):
        self.move(WAYMEET_CROSSROADS_KEY)
        blocked = await attempt_discovery_command(
            self.session, self.world, "listen bell", registry=OMEN_REGISTRY,
        )
        self.assertFalse(blocked.discovered)
        pulses = [pulse for pulse in PULSE_TEMPLATES if pulse.key == "copperwake_caravan"]
        self.assertEqual(len(pulses), 1)
        self.assertIn((CLAPPERLESS_BELL_KEY, 9), pulses[0].merchant_wares)
        self.assertEqual(pulses[0].room_key, WAYMEET_LANTERN_MARKET_KEY)
        self.database.add_item(self.character.id, CLAPPERLESS_BELL_KEY, 1)
        heard = await attempt_discovery_command(
            self.session, self.world, "listen bell", registry=OMEN_REGISTRY,
        )
        self.assertTrue(heard.discovered)
        self.assertEqual(heard.definition.key, BELL_RESONANCE)

    async def test_midgame_secrets_never_require_early_clues_or_purchased_bell(self):
        belfry = await self.discover(QUIET_BELFRY_KEY, "listen frame")
        noon = await self.discover(NOON_LENS_KEY, "read lens scratches")
        self.assertEqual(belfry.definition.key, EMPTY_BELFRY)
        self.assertEqual(noon.definition.key, NOON_ALIGNMENT)
        self.assertFalse((await self.discover(NOON_LENS_KEY, "trace fifth notch")).discovered)
        self.assertFalse((await self.discover(QUIET_BELFRY_KEY, "compare bell")).discovered)
        self.assertEqual(threshold_echoes(self.database, self.character.id)[0][:11], "The missing")

    async def test_attention_adds_optional_fifth_note_and_future_payoff(self):
        await self.discover(WAYMEET_CROSSROADS_KEY, "read chalk marks")
        await self.discover(WAYMEET_COMMONHOUSE_KEY, "listen children")
        extra = await self.discover(NOON_LENS_KEY, "trace fifth notch")
        self.assertTrue(extra.discovered)
        self.assertEqual(extra.definition.key, MISSING_NOTE)
        self.database.add_item(self.character.id, CLAPPERLESS_BELL_KEY, 1)
        await self.discover(WAYMEET_CROSSROADS_KEY, "listen bell")
        self.assertTrue((await self.discover(QUIET_BELFRY_KEY, "compare bell")).discovered)
        self.assertIsNotNone(discovery_record(self.database, self.character.id, BELL_COMPARISON))
        echoes = threshold_echoes(self.database, self.character.id)
        self.assertIn("waybell", echoes[0])
        self.assertIn("Nimra", " ".join(echoes))
        self.assertLessEqual(len(echoes), 3)

    async def test_local_runtime_intercepts_omens_without_stealing_normal_commands(self):
        self.move(WAYMEET_CROSSROADS_KEY)
        parent = self.session

        class DummySession(TestSession):
            async def prompt(self, _text):
                return self.next_command

            async def playing_prompt(self):
                self.base_commands.append(await self.prompt("> "))

        class DummyState:
            DISCONNECTED = "disconnected"

        session = DummySession(parent.database, parent.character, self.world)
        session.base_commands = []
        session.state = DummyState
        install_endgame_omens_runtime(DummySession, self.world)
        install_endgame_omens_runtime(DummySession, self.world)
        session.next_command = "read chalk marks"
        await session.playing_prompt()
        self.assertFalse(session.base_commands)
        self.assertIsNotNone(discovery_record(self.database, self.character.id, CHALK_CIPHER))
        session.next_command = "look"
        await session.playing_prompt()
        self.assertEqual(session.base_commands, ["look"])
        session.next_command = "read chalk marks"
        await session.playing_prompt()
        self.assertIn("rubbed away", " ".join(session.outputs))

    def test_nimra_ambient_refrain_is_room_local_and_respects_daytime(self):
        class RareRng:
            def random(self):
                return 0.0

            def choice(self, values):
                return values[0]

        # Validate the mobile against temporary Waymeet rooms without changing
        # the process-wide world seen by later, independent test classes.
        with patch.dict(
            legacy_world.ROOMS_BY_KEY, {room.key: room for room in WAYMEET_ROOMS},
        ):
            manager = MobileNpcManager(definitions=(EDRIN,))
        manager.states[EDRIN.key].current_room_key = WAYMEET_COMMONHOUSE_KEY
        self.assertIn(
            "Nimra",
            " ".join(chatter_lines(manager, WAYMEET_COMMONHOUSE_KEY, 12, "clear", rng=RareRng())),
        )
        self.assertNotIn(
            "Nimra",
            " ".join(chatter_lines(manager, WAYMEET_COMMONHOUSE_KEY, 23, "clear", rng=RareRng())),
        )
        manager.states[EDRIN.key].current_room_key = WAYMEET_CROSSROADS_KEY
        self.assertIn(
            "chalk",
            " ".join(chatter_lines(manager, WAYMEET_CROSSROADS_KEY, 12, "rain", rng=RareRng())),
        )

    def test_omens_add_no_mandatory_quests_or_experience_power(self):
        self.assertEqual(len(OMEN_DEFINITIONS), 8)
        self.assertTrue(all(definition.experience_reward == 0 for definition in OMEN_DEFINITIONS))
        self.assertTrue(all(definition.kind == "omen" for definition in OMEN_DEFINITIONS))


if __name__ == "__main__":
    unittest.main()
