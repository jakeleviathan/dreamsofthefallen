from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.economy_loop as economy
import mud.living_world as living
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.mechanics import CombatantState
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_SCRIP_KEY


class DummyClock:
    def __init__(self, moment: AstralisMoment) -> None:
        self.moment = moment

    def now(self, real_seconds=None) -> AstralisMoment:
        return self.moment


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []
        self.active_enemy = None
        self.active_mobile_npc_key = None
        self.combat_task = None
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "human",
            current_hp=10,
            max_hp=30,
            current_mana=4,
            max_mana=20,
            auto_attack_interval=2.5,
            current_movement=25,
            max_movement=100,
            stats=character.stats,
            armor_class=0,
        )

    async def send(self, text: str) -> None:
        self.messages.append(text)

    async def send_client_state(self) -> None:
        return

    def refresh(self) -> None:
        refreshed = self.database.get_character_by_name(self.character.name)
        assert refreshed is not None
        self.character = refreshed


class LivingWorldTests(unittest.TestCase):
    def setUp(self) -> None:
        living._RESOURCE_SHIFT_STATE = None

    def tearDown(self) -> None:
        living._RESOURCE_SHIFT_STATE = None

    def _session(self, root: Path, name: str = "Pulsewalker") -> DummySession:
        database = Database(root / "living.db")
        account = database.create_account(f"account_{name.lower()}", "x")
        character = database.create_character(account.id, name, "human", "brute")
        return DummySession(database, character)

    @staticmethod
    def _moment(day: int, hour: int = 12, minute: int = 0) -> AstralisMoment:
        return AstralisMoment(
            day_number=day,
            hour=hour,
            minute=minute,
            total_minutes=((day - 1) * 24 * 60) + (hour * 60) + minute,
        )

    def test_daily_pulse_is_stable_varied_and_not_only_combat(self):
        same_first = living.pulse_for_day(42)
        same_second = living.pulse_for_day(42)
        self.assertEqual(same_first, same_second)
        pulses = [living.pulse_for_day(day) for day in range(1, 500)]
        self.assertEqual({pulse.kind for pulse in pulses}, {"merchant", "resource", "threat", "story"})
        self.assertGreaterEqual(len({pulse.key for pulse in pulses}), 10)
        self.assertTrue(all(pulse.headline and pulse.gossip and pulse.room_key for pulse in living.PULSE_TEMPLATES))

    def test_resource_pulse_changes_real_gathering_map_then_rolls_away(self):
        day = next(
            number for number in range(1, 1000)
            if living.pulse_for_day(number).key == "briar_bloom"
        )
        backup = dict(economy.ROOM_RESOURCE_NODE_KEYS)
        try:
            before = economy.ROOM_RESOURCE_NODE_KEYS.get(living.WAYMEET_BRIARCUT_KEY, ())
            self.assertNotIn("lavender_patch", before)
            pulse = living._sync_resource_shift(self._moment(day))
            self.assertEqual(pulse.key, "briar_bloom")
            self.assertIn(
                "lavender_patch",
                economy.ROOM_RESOURCE_NODE_KEYS[living.WAYMEET_BRIARCUT_KEY],
            )
            living._sync_resource_shift(self._moment(day + 1))
            self.assertNotIn(
                "lavender_patch",
                economy.ROOM_RESOURCE_NODE_KEYS.get(living.WAYMEET_BRIARCUT_KEY, ()),
            )
        finally:
            economy.ROOM_RESOURCE_NODE_KEYS.clear()
            economy.ROOM_RESOURCE_NODE_KEYS.update(backup)
            living._RESOURCE_SHIFT_STATE = None

    def test_violet_moon_is_rare_world_history_not_a_reward_schedule(self):
        special = self._moment(61, 23)
        daylight = self._moment(61, 12)
        ordinary_night = self._moment(62, 23)
        self.assertEqual(living.rare_world_moment(special), "violet_moon")
        self.assertIsNone(living.rare_world_moment(daylight))
        self.assertIsNone(living.rare_world_moment(ordinary_night))

        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            living._record_rare_moment(session.database, special)
            living._record_rare_moment(session.database, special)
            rows = living.latest_chronicle(session.database, 10)
            violet = [row for row in rows if "moon turned violet" in row["entry_text"]]
            self.assertEqual(len(violet), 1)
            self.assertNotIn("reward", violet[0]["entry_text"].lower())

    def test_return_mail_reports_change_without_creating_fomo_reward(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="Returner")
            living.ensure_living_world_schema(session.database)
            with session.database.connect() as db:
                db.execute(
                    "INSERT INTO living_character_state (character_id, last_seen_day, last_room_hint_day) VALUES (?, 10, 0)",
                    (session.character.id,),
                )
            previous_day, created = living._touch_login_state(session, self._moment(13))
            self.assertEqual(previous_day, 10)
            self.assertTrue(created)
            self.assertEqual(living._unread_mail_count(session), 1)
            with session.database.connect() as db:
                row = db.execute(
                    "SELECT sender, subject, body FROM living_mail WHERE character_id = ?",
                    (session.character.id,),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertIn("away for 3 Astralis days", row["body"])
            self.assertIn("no missed reward", row["body"].lower())
            self.assertIn("Day 13", row["subject"])

    def test_chronicle_records_a_server_first_only_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="FirstName")
            first = living._chronicle_insert(
                session.database,
                event_key="first:test:thing",
                day=7,
                character_id=session.character.id,
                character_name=session.character.name,
                category="first",
                text="FirstName did the thing first.",
            )
            second = living._chronicle_insert(
                session.database,
                event_key="first:test:thing",
                day=8,
                character_id=session.character.id,
                character_name=session.character.name,
                category="first",
                text="This duplicate should never replace history.",
            )
            self.assertTrue(first)
            self.assertFalse(second)
            rows = living.latest_chronicle(session.database, 10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["astralis_day"], 7)
            self.assertEqual(rows[0]["entry_text"], "FirstName did the thing first.")

    def test_small_room_is_a_real_persistent_place_with_storage_and_five_display_slots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="Homekeeper")
            session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 5)
            session.database.add_item(session.character.id, "raw_cotton", 8)
            session.database.set_character_room(session.character.id, WAYMEET_COMMONHOUSE_KEY)
            session.refresh()

            with patch.object(living, "ASTRALIS_CLOCK", DummyClock(self._moment(20))):
                asyncio.run(living._rent_room(session))
            row = living._quarters_row(session)
            self.assertIsNotNone(row)
            self.assertEqual(str(row["hub_room_key"]), WAYMEET_COMMONHOUSE_KEY)
            self.assertEqual(session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 3)

            asyncio.run(living._enter_room(session))
            self.assertTrue(living._is_private_room(session))
            asyncio.run(living._room_store(session, "3 raw cotton"))
            self.assertEqual(session.database.item_quantity(session.character.id, "raw_cotton"), 5)
            self.assertEqual(living._room_storage_total(session), 3)

            asyncio.run(living._display_item(session, "raw cotton"))
            self.assertEqual(living._display_count(session), 1)
            self.assertEqual(session.database.item_quantity(session.character.id, "raw_cotton"), 4)
            asyncio.run(living._take_display(session, 1))
            self.assertEqual(living._display_count(session), 0)
            self.assertEqual(session.database.item_quantity(session.character.id, "raw_cotton"), 5)

            with session.database.connect() as db:
                row = db.execute(
                    "SELECT COUNT(*) AS n FROM living_room_display WHERE character_id = ?",
                    (session.character.id,),
                ).fetchone()
            self.assertEqual(int(row["n"]), 0)
            self.assertEqual(living.ROOM_DISPLAY_SLOTS, 5)
            self.assertEqual(living.ROOM_STORAGE_CAPACITY, 20)

    def test_room_bed_recovers_character_without_streak_or_daily_reward(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="Sleeper")
            living.ensure_living_world_schema(session.database)
            with session.database.connect() as db:
                db.execute(
                    "INSERT INTO living_quarters (character_id, hub_room_key, rented_day) VALUES (?, ?, 1)",
                    (session.character.id, WAYMEET_COMMONHOUSE_KEY),
                )
            session.database.set_character_room(session.character.id, living._private_room_key(session.character.id))
            session.refresh()
            asyncio.run(living._sleep_room(session))
            self.assertEqual(session.combatant.current_hp, session.combatant.max_hp)
            self.assertEqual(session.combatant.current_mana, session.combatant.max_mana)
            self.assertEqual(session.combatant.current_movement, session.combatant.max_movement)
            message = "".join(session.messages).lower()
            self.assertIn("without an alarm", message)
            self.assertIn("reward streak", message)

    def test_wandering_merchant_is_temporary_convenience_bought_with_real_scrip(self):
        day = next(
            number for number in range(1, 1000)
            if living.pulse_for_day(number).key == "copperwake_caravan"
        )
        moment = self._moment(day)
        pulse = living.pulse_for_day(day)
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="Shopper")
            session.database.set_character_room(session.character.id, pulse.room_key)
            session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 3)
            session.refresh()
            with patch.object(living, "ASTRALIS_CLOCK", DummyClock(moment)):
                self.assertTrue(asyncio.run(living._browse_wanderer(session)))
                self.assertTrue(asyncio.run(living._buy_wanderer(session, "iron ore")))
            self.assertEqual(session.database.item_quantity(session.character.id, "iron_ore"), 1)
            self.assertEqual(session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY), 2)

    def test_daily_disturbance_participation_cannot_be_farmed_for_repeat_payouts(self):
        day = next(
            number for number in range(1, 1000)
            if living.pulse_for_day(number).kind == "threat"
        )
        pulse = living.pulse_for_day(day)
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), name="WardenFriend")
            self.assertTrue(living._mark_event_done(session, day, pulse))
            self.assertFalse(living._mark_event_done(session, day, pulse))
            self.assertTrue(living._event_done(session, day, pulse.key))

    def test_production_server_installs_living_world_inside_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.living_world import LIVING_WORLD_VERSION, PULSE_TEMPLATES
assert LIVING_WORLD_VERSION == "1.0.0"
assert len(PULSE_TEMPLATES) >= 10
assert server.PlayerSession._living_world_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
print("LIVING_WORLD_OK")
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
        self.assertIn("LIVING_WORLD_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
