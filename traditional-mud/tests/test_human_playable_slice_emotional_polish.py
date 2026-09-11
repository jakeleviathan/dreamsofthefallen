from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.database import Database
from mud.human_blackwall_opening import (
    HUMAN_CARAVAN_QUEST_KEY,
    HUMAN_SOOTSTEP_TUNNEL_KEY,
    install_human_blackwall_content,
    prepare_human_blackwall_opening,
)
from mud.human_playable_slice import (
    HUMAN_FIRST_MILE_OVERLOOK_KEY,
    SliceAward,
    announce_slice_awards,
    human_playable_slice_augmentations,
    install_human_playable_slice_content,
    newly_unlocked_class_abilities,
    recover_first_burrower_defeat,
)


class FakeSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.active_enemy = None
        self.combatant = SimpleNamespace(current_hp=1, max_hp=31, current_mana=2, max_mana=28)

    async def send(self, text: str):
        self.outputs.append(text)

    async def _stop_combat(self, **_kwargs):
        self.active_enemy = None

    async def show_current_room(self):
        return None

    async def send_client_state(self):
        return None


def move(session: FakeSession, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    refreshed = session.database.get_character_by_name(session.character.name)
    assert refreshed is not None
    session.character = refreshed


class HumanPlayableSliceEmotionalPolishTests(unittest.TestCase):
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
        install_human_playable_slice_content()

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

    def _session(self, name: str = "Polish", character_class: str = "wizard"):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "polish.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(account.id, name, "human", character_class)
        session = FakeSession(database, character)
        prepare_human_blackwall_opening(session)
        return temp, database, session

    def test_overlook_looks_back_at_people_not_only_scenery(self):
        augmentation = human_playable_slice_augmentations()[HUMAN_FIRST_MILE_OVERLOOK_KEY]
        memory = next(feature for feature in augmentation.features if feature.key == "first_mile_blackwall_behind")
        text = memory.examine_text
        self.assertIn("Mara Vey", text)
        self.assertIn("Ketta Brassrun", text)
        self.assertIn("Orrin Vale", text)
        self.assertIn("Sera Thorn", text)
        self.assertIn("ordinary work", text)

    def test_level_two_names_the_actual_new_class_tool(self):
        character = SimpleNamespace(character_class="wizard", deity_key=None)
        self.assertEqual(newly_unlocked_class_abilities(character, 1, 2), ("Minor Barrier",))

        session = SimpleNamespace(character=character, outputs=[])

        async def send(text: str):
            session.outputs.append(text)

        session.send = send
        asyncio.run(
            announce_slice_awards(
                session,
                (SliceAward("Beyond the Blackwall", 10, 1, 2, 100),),
            )
        )
        output = "".join(session.outputs)
        self.assertIn("LEVEL 2", output)
        self.assertIn("Minor Barrier", output)
        self.assertIn("ABILITIES", output)

    def test_first_loss_calls_back_to_mara_as_a_person(self):
        temp, database, session = self._session("RememberMara")
        self.addCleanup(temp.cleanup)
        move(session, HUMAN_SOOTSTEP_TUNNEL_KEY)
        quest = database.get_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY)
        if quest is None:
            database.start_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "fight_burrower")
        else:
            database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "fight_burrower")

        self.assertTrue(asyncio.run(recover_first_burrower_defeat(session, "Sootstep Burrower")))
        output = "".join(session.outputs)
        self.assertIn("Sergeant Mara Vey", output)
        self.assertIn("bad attempt is still information", output.lower())


if __name__ == "__main__":
    unittest.main()
