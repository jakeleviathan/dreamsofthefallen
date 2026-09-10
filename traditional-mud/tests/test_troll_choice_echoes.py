import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as world
from mud.database import Database
from mud.mechanics import CombatantState
from mud.stats import CharacterStats
from mud import troll_start
from mud import troll_survivor_choice as survivor
from mud.troll_choice_echoes import (
    HARKA_PINE_EYE_KEY,
    ODA_WARMSTONE_KEY,
    TROLL_BRANNIK_CHOICE_ECHO_FLAG,
    TROLL_RATION_GIFT_FLAG,
    TROLL_RATION_KEY,
    TROLL_RATION_USED_FLAG,
    TROLL_TRAIL_MARKER_GIFT_FLAG,
    TROLL_TRAIL_MARKER_KEY,
    TROLL_TRAIL_MARKER_USED_FLAG,
    _brannik_choice_echo,
    _check_trail_marker,
    _eat_ration,
    _marker_room_flag,
    _talk_harka,
    _talk_oda,
    _use_trail_marker,
    install_troll_choice_echo_content,
)


class EchoSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.outputs: list[str] = []
        self.combatant = CombatantState(
            character_id=character.id,
            race_key="troll",
            current_hp=10,
            max_hp=10,
            current_mana=10,
            max_mana=10,
            auto_attack_interval=2.0,
            stats=character.stats,
        )

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    def move_to(self, room_key: str):
        self.database.set_character_room(self.character.id, room_key)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed


class TrollChoiceEchoTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.items = crafting.ITEMS
        self.items_by_key = dict(crafting.ITEMS_BY_KEY)
        self.quests = quests.QUESTS
        self.quests_by_key = dict(quests.QUESTS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)

        troll_start.install_troll_content()
        survivor.install_troll_survivor_choice_content()
        install_troll_choice_echo_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        crafting.ITEMS = self.items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.items_by_key)
        quests.QUESTS = self.quests
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quests_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)

    def _session(self, name: str):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "troll_echoes.db")
        account = database.create_account(f"acct_{name.lower()}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            name,
            "troll",
            "brute",
            CharacterStats(might=9, grace=5, love=5, mind=5, hp=12),
        )
        database.set_character_room(character.id, troll_start.TROLL_START_ROOM_KEY)
        database.set_bind_room(character.id, troll_start.TROLL_START_ROOM_KEY)
        character = database.get_character_by_name(name)
        assert character is not None
        return temp, database, EchoSession(database, character)

    def test_echo_content_adds_two_later_contacts_and_two_small_keepsakes(self):
        self.assertIn(HARKA_PINE_EYE_KEY, world.NPCS_BY_KEY)
        self.assertIn(ODA_WARMSTONE_KEY, world.NPCS_BY_KEY)
        self.assertIn(HARKA_PINE_EYE_KEY, world.ROOMS_BY_KEY[troll_start.TROLL_TRACKLINE_VERGE_KEY].npc_keys)
        self.assertIn(ODA_WARMSTONE_KEY, world.ROOMS_BY_KEY[troll_start.TROLL_EMBER_HOLLOW_KEY].npc_keys)
        self.assertIn(TROLL_TRAIL_MARKER_KEY, crafting.ITEMS_BY_KEY)
        self.assertIn(TROLL_RATION_KEY, crafting.ITEMS_BY_KEY)
        self.assertEqual(crafting.ITEMS_BY_KEY[TROLL_RATION_KEY].consumable.heal_hp, 4)

    def test_tracker_is_recognized_by_scout_and_gets_one_persistent_trail_marker(self):
        temp, database, session = self._session("TrailEcho")
        self.addCleanup(temp.cleanup)
        database.grant_flag(session.character.id, survivor.TROLL_TRACK_ROUTE_COMPLETE_FLAG)
        database.grant_flag(session.character.id, survivor.TROLL_FIRST_DUTY_COMPLETE_FLAG)
        session.move_to(troll_start.TROLL_TRACKLINE_VERGE_KEY)

        self.assertTrue(asyncio.run(_talk_harka(session)))
        self.assertEqual(database.item_quantity(session.character.id, TROLL_TRAIL_MARKER_KEY), 1)
        self.assertIn(TROLL_TRAIL_MARKER_GIFT_FLAG, database.list_flags(session.character.id))
        first_output = "".join(session.outputs).lower()
        self.assertIn("insurance against weather", first_output)
        self.assertIn("mark trail", first_output)

        # Talking again never duplicates the route reward.
        self.assertTrue(asyncio.run(_talk_harka(session)))
        self.assertEqual(database.item_quantity(session.character.id, TROLL_TRAIL_MARKER_KEY), 1)

        self.assertTrue(asyncio.run(_use_trail_marker(session, "mark trail")))
        self.assertEqual(database.item_quantity(session.character.id, TROLL_TRAIL_MARKER_KEY), 0)
        flags = database.list_flags(session.character.id)
        self.assertIn(TROLL_TRAIL_MARKER_USED_FLAG, flags)
        self.assertIn(_marker_room_flag(troll_start.TROLL_TRACKLINE_VERGE_KEY), flags)
        self.assertIn("west", "".join(session.outputs).lower())

        session.outputs.clear()
        self.assertTrue(asyncio.run(_check_trail_marker(session, "check marker")))
        self.assertIn("west", "".join(session.outputs).lower())

    def test_camp_helper_is_recognized_by_hearthkeeper_and_gets_one_healing_ration(self):
        temp, database, session = self._session("HearthEcho")
        self.addCleanup(temp.cleanup)
        database.grant_flag(session.character.id, survivor.TROLL_CAMP_ROUTE_COMPLETE_FLAG)
        database.grant_flag(session.character.id, survivor.TROLL_FIRST_DUTY_COMPLETE_FLAG)
        session.move_to(troll_start.TROLL_EMBER_HOLLOW_KEY)

        self.assertTrue(asyncio.run(_talk_oda(session)))
        self.assertEqual(database.item_quantity(session.character.id, TROLL_RATION_KEY), 1)
        self.assertIn(TROLL_RATION_GIFT_FLAG, database.list_flags(session.character.id))
        output = "".join(session.outputs).lower()
        self.assertIn("sealed food", output)
        self.assertIn("restore 4 hp", output)

        session.combatant.current_hp = 5
        self.assertTrue(asyncio.run(_eat_ration(session, "eat smoked root ration")))
        self.assertEqual(session.combatant.current_hp, 9)
        self.assertEqual(database.item_quantity(session.character.id, TROLL_RATION_KEY), 0)
        self.assertIn(TROLL_RATION_USED_FLAG, database.list_flags(session.character.id))

        # The social reward is one-time even after the ration has been consumed.
        self.assertTrue(asyncio.run(_talk_oda(session)))
        self.assertEqual(database.item_quantity(session.character.id, TROLL_RATION_KEY), 0)

    def test_brannik_gets_a_single_subtle_callback_for_each_earlier_choice(self):
        cases = (
            (
                "TrackCallback",
                survivor.TROLL_TRACK_ROUTE_COMPLETE_FLAG,
                "false retreat sign",
            ),
            (
                "CampCallback",
                survivor.TROLL_CAMP_ROUTE_COMPLETE_FLAG,
                "which problem is getting worse first",
            ),
        )
        for name, route_flag, expected in cases:
            with self.subTest(route=route_flag):
                temp, database, session = self._session(name)
                self.addCleanup(temp.cleanup)
                database.grant_flag(session.character.id, route_flag)
                database.start_quest(
                    session.character.id,
                    troll_start.TROLL_OUTSIDER_QUEST.key,
                    "meet_outsider",
                )
                session.move_to(troll_start.TROLL_WINDSCAR_SHELF_KEY)

                self.assertTrue(asyncio.run(_brannik_choice_echo(session)))
                self.assertIn(expected, "".join(session.outputs).lower())
                self.assertIn(
                    TROLL_BRANNIK_CHOICE_ECHO_FLAG,
                    database.list_flags(session.character.id),
                )
                session.outputs.clear()
                self.assertFalse(asyncio.run(_brannik_choice_echo(session)))
                self.assertEqual(session.outputs, [])

    def test_grandfathered_or_unbranched_trolls_do_not_receive_fake_choice_history(self):
        temp, database, session = self._session("NoFakeHistory")
        self.addCleanup(temp.cleanup)
        database.start_quest(
            session.character.id,
            troll_start.TROLL_OUTSIDER_QUEST.key,
            "meet_outsider",
        )
        session.move_to(troll_start.TROLL_WINDSCAR_SHELF_KEY)
        self.assertFalse(asyncio.run(_brannik_choice_echo(session)))
        self.assertNotIn(
            TROLL_BRANNIK_CHOICE_ECHO_FLAG,
            database.list_flags(session.character.id),
        )


if __name__ == "__main__":
    unittest.main()
