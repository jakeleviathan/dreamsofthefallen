from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import mud.combat as combat
import mud.social_experience as social
import mud.waymeet_frontier as waymeet
from mud.database import Database
from mud.launch_vertical_slice import (
    BRIAR_EYE_CHARM,
    EMOTE_VERBS,
    LAUNCH_VERTICAL_SLICE_VERSION,
    NOTABLE_FIND_BY_ENEMY,
    OPENING_EPILOGUES,
    SOCIAL_HUBS,
    VEYRA_CROSSING_MEMORY_FLAG,
    VEYRA_GATE_MEMORY_FLAG,
    WAYMEET_PACING_HP,
    _award_first_notable_find,
    _broadcast_room_emote,
    _broadcast_tavern,
    _maybe_send_veyra_arrival,
    _notify_friend_presence,
    apply_first_hours_combat_tuning,
    install_launch_vertical_slice_content,
    journey_stage_for,
)
from mud.starter_race_loops import STARTER_RACE_LOOPS, STARTER_RACE_LOOPS_BY_RACE
from mud.veyra_city import VEYRA_GRAND_CROSSING_KEY, VEYRA_PUBLIC_HEARTH_KEY, VEYRA_RESIDENT_FLAG
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_INTRO_COMPLETE_FLAG
from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
from mud.greywake_march import GREYWAKE_CHAIN_COMPLETE_FLAG


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)

    def refresh(self) -> None:
        loaded = self.database.get_character_by_name(self.character.name)
        assert loaded is not None
        self.character = loaded


class LaunchVerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        social._ACTIVE_SESSIONS.clear()
        waymeet.install_waymeet_content()
        install_launch_vertical_slice_content()

    def tearDown(self) -> None:
        social._ACTIVE_SESSIONS.clear()

    def _session(self, root: Path, name: str = "LaunchHero", race: str = "human") -> DummySession:
        database = Database(root / "launch.db")
        account = database.create_account(f"account_{name.lower()}", "x")
        character = database.create_character(account.id, name, race, "brute")
        return DummySession(database, character)

    def test_all_eight_openings_get_distinct_closing_beats_without_replacing_contracts(self):
        self.assertEqual(len(STARTER_RACE_LOOPS), 8)
        self.assertEqual(set(OPENING_EPILOGUES), set(STARTER_RACE_LOOPS_BY_RACE))
        self.assertEqual(len(set(OPENING_EPILOGUES.values())), 8)
        for race_key, paragraphs in OPENING_EPILOGUES.items():
            self.assertEqual(len(paragraphs), 2)
            self.assertGreater(len(paragraphs[0]), 50, race_key)
            self.assertGreater(len(paragraphs[1]), 50, race_key)

    def test_first_hours_journey_is_a_connected_horizon_not_a_second_quest_log(self):
        human = STARTER_RACE_LOOPS_BY_RACE["human"]
        title, text = journey_stage_for(race_key="human", level=1, flags=set())
        self.assertEqual(title, human.hook_name)
        self.assertIn("caravan", text.lower())

        flags = {human.completion_flag}
        title, _ = journey_stage_for(race_key="human", level=2, flags=flags)
        self.assertEqual(title, "Where the Roads Meet")

        flags.add(WAYMEET_INTRO_COMPLETE_FLAG)
        title, _ = journey_stage_for(race_key="human", level=4, flags=flags)
        self.assertEqual(title, "Below the Sealed Door")

        flags.add(GLOAMWORKS_COMPLETE_FLAG)
        title, _ = journey_stage_for(race_key="human", level=5, flags=flags)
        self.assertEqual(title, "The Greywake road")

        flags.add(GREYWAKE_CHAIN_COMPLETE_FLAG)
        title, _ = journey_stage_for(race_key="human", level=8, flags=flags)
        self.assertEqual(title, "The city at the end of the road")

        flags.add(VEYRA_RESIDENT_FLAG)
        title, text = journey_stage_for(race_key="human", level=8, flags=flags)
        self.assertEqual(title, "A place in the wider world")
        self.assertIn("order that interests you", text)

    def test_waymeet_pacing_tuning_is_modest_and_keeps_danger_curve(self):
        original_damage = {
            key: combat.ENEMIES_BY_KEY[key].auto_attack_damage for key in WAYMEET_PACING_HP
        }
        original_rewards = {
            key: combat.ENEMIES_BY_KEY[key].xp_reward for key in WAYMEET_PACING_HP
        }
        apply_first_hours_combat_tuning()
        tuned = [combat.ENEMIES_BY_KEY[key] for key in WAYMEET_PACING_HP]
        self.assertEqual([enemy.max_hp for enemy in tuned], [24, 34, 48, 54, 66])
        self.assertEqual([enemy.max_hp for enemy in tuned], sorted(enemy.max_hp for enemy in tuned))
        for key in WAYMEET_PACING_HP:
            self.assertEqual(combat.ENEMIES_BY_KEY[key].auto_attack_damage, original_damage[key])
            self.assertEqual(combat.ENEMIES_BY_KEY[key].xp_reward, original_rewards[key])

    def test_five_first_specimen_trophies_are_real_tradeable_accessories(self):
        self.assertEqual(len(NOTABLE_FIND_BY_ENEMY), 5)
        self.assertEqual(BRIAR_EYE_CHARM.equipment.slot, "accessory")
        for item in NOTABLE_FIND_BY_ENEMY.values():
            self.assertEqual(item.category, "equipment")
            self.assertEqual(item.equipment.slot, "accessory")
            self.assertNotEqual(item.key, "")

        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            enemy_key = waymeet.THORNBACK_JACKAL_KEY
            first = asyncio.run(_award_first_notable_find(session, enemy_key))
            second = asyncio.run(_award_first_notable_find(session, enemy_key))
            self.assertTrue(first)
            self.assertFalse(second)
            self.assertEqual(session.database.item_quantity(session.character.id, BRIAR_EYE_CHARM.key), 1)
            self.assertIn("NOTABLE FIND", "".join(session.messages))

    def test_veyra_arrival_has_two_persistent_one_time_beats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="VeyraWalker")
            session.database.set_character_room(session.character.id, VEYRA_GRAND_CROSSING_KEY)
            session.refresh()
            first = asyncio.run(_maybe_send_veyra_arrival(session))
            second = asyncio.run(_maybe_send_veyra_arrival(session))
            self.assertTrue(first)
            self.assertFalse(second)
            flags = session.database.list_flags(session.character.id)
            self.assertIn(VEYRA_CROSSING_MEMORY_FLAG, flags)
            self.assertNotIn(VEYRA_GATE_MEMORY_FLAG, flags)
            text = "".join(session.messages).lower()
            self.assertIn("larger world", text)
            self.assertIn("dwarven load marks", text)

    def test_local_emotes_are_labeled_and_tavern_channel_requires_social_hubs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self._session(root, name="Aster")
            # Reuse the same database/account namespace through a separate account.
            database = first.database
            account = database.create_account("account_bram", "x")
            second_character = database.create_character(account.id, "Bram", "dwarf", "wizard")
            second = DummySession(database, second_character)

            first.database.set_character_room(first.character.id, WAYMEET_COMMONHOUSE_KEY)
            second.database.set_character_room(second.character.id, VEYRA_PUBLIC_HEARTH_KEY)
            first.refresh()
            second.refresh()
            social._ACTIVE_SESSIONS.add(first)
            social._ACTIVE_SESSIONS.add(second)

            asyncio.run(_broadcast_room_emote(first, "studies the commonhouse map."))
            self.assertIn("[Emote] Aster studies the commonhouse map.", "".join(first.messages))
            self.assertNotIn("[Emote] Aster", "".join(second.messages))

            asyncio.run(_broadcast_tavern(first, "Anyone headed east?"))
            self.assertIn("Anyone headed east?", "".join(first.messages))
            self.assertIn("Anyone headed east?", "".join(second.messages))
            self.assertEqual(set(SOCIAL_HUBS), {WAYMEET_COMMONHOUSE_KEY, VEYRA_PUBLIC_HEARTH_KEY})
            self.assertIn("wave", EMOTE_VERBS)

    def test_saved_friends_get_presence_notice_without_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self._session(root, name="FriendOne")
            database = first.database
            account = database.create_account("account_friendtwo", "x")
            second_character = database.create_character(account.id, "FriendTwo", "goblin", "druid")
            second = DummySession(database, second_character)
            social._ensure_schema(database)
            with database.connect() as db:
                db.execute(
                    "INSERT INTO character_friends (character_id, friend_character_id) VALUES (?, ?)",
                    (first.character.id, second.character.id),
                )
            social._ACTIVE_SESSIONS.add(first)
            social._ACTIVE_SESSIONS.add(second)

            asyncio.run(_notify_friend_presence(second, online=True))
            notice = "".join(first.messages)
            self.assertIn("[Friend] FriendTwo has entered Astralis.", notice)
            self.assertNotIn("room", notice.lower())
            self.assertNotIn("waymeet", notice.lower())

    def test_production_server_installs_launch_polish_inside_modern_presentation(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.combat as combat
import mud.crafting as crafting
from mud.launch_vertical_slice import LAUNCH_VERTICAL_SLICE_VERSION

assert LAUNCH_VERTICAL_SLICE_VERSION == "1.0.0"
assert server.PlayerSession._launch_vertical_slice_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
assert combat.ENEMIES_BY_KEY["waymeet_thornback_jackal"].max_hp == 24
assert "launch_briar_eye_charm" in crafting.ITEMS_BY_KEY
print("LAUNCH_VERTICAL_SLICE_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("LAUNCH_VERTICAL_SLICE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
