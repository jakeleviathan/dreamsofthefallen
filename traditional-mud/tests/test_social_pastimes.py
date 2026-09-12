from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.social_pastimes as leisure
from mud.astralis_time import AstralisMoment
from mud.database import Database
from mud.mechanics import CombatantState
from mud.social_experience import _ACTIVE_SESSIONS
from mud.veyra_city import VEYRA_BRASSMARKET_KEY, VEYRA_PUBLIC_HEARTH_KEY
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_LANTERN_MARKET_KEY


class DummyClock:
    def __init__(self, moment: AstralisMoment) -> None:
        self.moment = moment

    def now(self, real_seconds=None) -> AstralisMoment:
        return self.moment


class DummyTelnet:
    def __init__(self) -> None:
        self.gmcp_enabled = True
        self.packets: list[tuple[str, dict]] = []

    async def send_gmcp(self, package: str, payload: dict) -> bool:
        self.packets.append((package, payload))
        return True


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []
        self.telnet = DummyTelnet()
        self.active_enemy = None
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "human",
            current_hp=30,
            max_hp=30,
            current_mana=20,
            max_mana=20,
            auto_attack_interval=2.5,
            current_movement=100,
            max_movement=100,
            stats=character.stats,
            armor_class=0,
        )

    async def send(self, text: str) -> None:
        self.messages.append(text)

    def refresh(self) -> None:
        refreshed = self.database.get_character_by_name(self.character.name)
        assert refreshed is not None
        self.character = refreshed


class SocialPastimeTests(unittest.TestCase):
    def setUp(self) -> None:
        _ACTIVE_SESSIONS.clear()
        leisure._PENDING_ARM_WRESTLES.clear()

    def tearDown(self) -> None:
        _ACTIVE_SESSIONS.clear()
        leisure._PENDING_ARM_WRESTLES.clear()

    @staticmethod
    def _moment(day: int, hour: int = 12) -> AstralisMoment:
        return AstralisMoment(
            day_number=day,
            hour=hour,
            minute=0,
            total_minutes=((day - 1) * 24 * 60) + hour * 60,
        )

    def _session(self, root: Path, name: str, room: str, class_key: str = "brute") -> DummySession:
        database = Database(root / "pastimes.db")
        account = database.create_account(f"account_{name.lower()}", "x")
        character = database.create_character(account.id, name, "human", class_key)
        database.set_character_room(character.id, room)
        character = database.get_character_by_name(name)
        assert character is not None
        return DummySession(database, character)

    def test_catalog_is_small_social_and_location_based(self):
        self.assertEqual(len(leisure.PASTIMES), 6)
        self.assertEqual({p.key for p in leisure.PASTIMES}, {
            "bones", "arm_wrestle", "knife_throw", "drinking_game", "riddle", "guess_jar"
        })
        self.assertIn(WAYMEET_COMMONHOUSE_KEY, leisure.PASTIMES_BY_KEY["bones"].rooms)
        self.assertIn(VEYRA_PUBLIC_HEARTH_KEY, leisure.PASTIMES_BY_KEY["drinking_game"].rooms)
        self.assertIn(WAYMEET_LANTERN_MARKET_KEY, leisure.PASTIMES_BY_KEY["riddle"].rooms)
        self.assertIn(VEYRA_BRASSMARKET_KEY, leisure.PASTIMES_BY_KEY["guess_jar"].rooms)

    def test_three_bones_is_repeatable_social_play_with_statless_keepsake(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Boneroll", WAYMEET_COMMONHOUSE_KEY)
            _ACTIVE_SESSIONS.add(session)
            moment = self._moment(8, 19)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                for _ in range(30):
                    asyncio.run(leisure._play_bones(session))
                    with session.database.connect() as db:
                        keepsake = db.execute(
                            "SELECT keepsake_name FROM leisure_keepsakes WHERE character_id = ? AND keepsake_key = ?",
                            (session.character.id, "bent_spoon_of_triumph"),
                        ).fetchone()
                    if keepsake is not None:
                        break
            self.assertIsNotNone(keepsake)
            self.assertEqual(keepsake["keepsake_name"], "Bent Spoon of Triumph")
            self.assertIn("Three Bones", "".join(session.messages))
            # Keepsakes deliberately live outside item/equipment progression.
            self.assertEqual(session.database.item_quantity(session.character.id, "bent_spoon_of_triumph"), 0)

    def test_arm_wrestling_is_real_room_local_player_contest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            a = self._session(root, "Mara", WAYMEET_COMMONHOUSE_KEY)
            b_db = a.database
            account = b_db.create_account("account_tovin", "x")
            b_char = b_db.create_character(account.id, "Tovin", "dwarf", "brute")
            b_db.set_character_room(b_char.id, WAYMEET_COMMONHOUSE_KEY)
            b_char = b_db.get_character_by_name("Tovin")
            assert b_char is not None
            b = DummySession(b_db, b_char)
            _ACTIVE_SESSIONS.add(a)
            _ACTIVE_SESSIONS.add(b)
            moment = self._moment(9, 20)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(leisure._challenge_arm(a, "Tovin"))
                self.assertIn(b.character.id, leisure._PENDING_ARM_WRESTLES)
                asyncio.run(leisure._accept_arm(b, "Mara"))
            combined = "".join(a.messages + b.messages)
            self.assertIn("Arm Wrestling", combined)
            self.assertIn("table creaks", combined)
            with b_db.connect() as db:
                count = db.execute("SELECT COUNT(*) AS n FROM leisure_keepsakes WHERE keepsake_key = 'bent_copper_thumb'").fetchone()["n"]
            self.assertEqual(int(count), 1)

    def test_knife_throw_has_daily_scores_and_grace_based_three_throw_total(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            a = self._session(root, "KnifeA", WAYMEET_COMMONHOUSE_KEY)
            db = a.database
            account = db.create_account("account_knifeb", "x")
            char = db.create_character(account.id, "KnifeB", "forest_elf", "wizard")
            db.set_character_room(char.id, WAYMEET_COMMONHOUSE_KEY)
            char = db.get_character_by_name("KnifeB")
            assert char is not None
            b = DummySession(db, char)
            _ACTIVE_SESSIONS.add(a)
            _ACTIVE_SESSIONS.add(b)
            moment = self._moment(10, 16)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(leisure._throw_knives(a))
                asyncio.run(leisure._throw_knives(b))
                asyncio.run(leisure._show_scores(a))
            text = "".join(a.messages)
            self.assertIn("Knife Throw", text)
            self.assertIn("Today's Knife-Throw Board", text)
            self.assertIn("/30", text)

    def test_five_round_mug_game_is_flavor_only_and_caps_the_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Mugger", VEYRA_PUBLIC_HEARTH_KEY)
            _ACTIVE_SESSIONS.add(session)
            before = session.character.stats
            moment = self._moment(11, 21)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                for _ in range(6):
                    asyncio.run(leisure._drink_round(session))
            self.assertEqual(session.character.stats, before)
            row = leisure._attempt_row(session, moment.day_number, "drinking_game")
            self.assertEqual(int(row["attempts"]), 5)
            with session.database.connect() as db:
                keepsake = db.execute(
                    "SELECT keepsake_name FROM leisure_keepsakes WHERE character_id = ? AND keepsake_key = 'pickled_onion_crown'",
                    (session.character.id,),
                ).fetchone()
            self.assertEqual(keepsake["keepsake_name"], "Pickled Onion Crown")
            self.assertIn("replaced the next mug with water", "".join(session.messages))

    def test_daily_market_riddle_and_guess_jar_reward_only_novelty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "MarketMind", WAYMEET_LANTERN_MARKET_KEY, "wizard")
            moment = self._moment(12, 13)
            question, answers = leisure._riddle_for_day(moment.day_number)
            self.assertTrue(question)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(leisure._show_riddle(session))
                asyncio.run(leisure._answer_riddle(session, answers[0]))
                asyncio.run(leisure._guess_jar(session, str(leisure._jar_number(moment.day_number))))
            with session.database.connect() as db:
                keys = {
                    row["keepsake_key"]
                    for row in db.execute(
                        "SELECT keepsake_key FROM leisure_keepsakes WHERE character_id = ?",
                        (session.character.id,),
                    ).fetchall()
                }
            self.assertIn("riddle_wax_seal", keys)
            self.assertIn("jar_prophets_blue_bead", keys)
            self.assertEqual(session.database.item_quantity(session.character.id, "riddle_wax_seal"), 0)

    def test_crooked_lantern_company_is_periodic_watchable_and_heckleable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "Audience", WAYMEET_COMMONHOUSE_KEY)
            _ACTIVE_SESSIONS.add(session)
            moment = self._moment(6, 12)
            self.assertEqual(leisure._show_location(moment), WAYMEET_COMMONHOUSE_KEY)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(leisure._arrival_nudge(session))
                first = len(session.messages)
                asyncio.run(leisure._arrival_nudge(session))
                self.assertEqual(len(session.messages), first)
                asyncio.run(leisure._watch_show(session))
                asyncio.run(leisure._heckle(session))
                asyncio.run(leisure._applaud(session))
            text = "".join(session.messages)
            self.assertIn("Crooked Lantern Company", text)
            self.assertIn("heckles", text)
            with session.database.connect() as db:
                playbill = db.execute(
                    "SELECT keepsake_name FROM leisure_keepsakes WHERE character_id = ? AND keepsake_key = 'crooked_lantern_playbill'",
                    (session.character.id,),
                ).fetchone()
            self.assertEqual(playbill["keepsake_name"], "Folded Crooked Lantern Playbill")

    def test_gmcp_exposes_only_current_optional_pastimes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir), "MudletFun", VEYRA_PUBLIC_HEARTH_KEY)
            moment = self._moment(6, 20)
            with patch.object(leisure, "ASTRALIS_CLOCK", DummyClock(moment)):
                asyncio.run(leisure._push_gmcp(session))
            payload = next(payload for package, payload in session.telnet.packets if package == "Dreams.Pastimes")
            keys = {entry["key"] for entry in payload["available"]}
            self.assertIn("bones", keys)
            self.assertIn("arm_wrestle", keys)
            self.assertTrue(payload["show_here"])
            self.assertTrue(payload["show_title"])

    def test_production_server_installs_pastimes_before_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.social_pastimes import SOCIAL_PASTIMES_VERSION, PASTIMES
assert SOCIAL_PASTIMES_VERSION == "1.0.0"
assert len(PASTIMES) == 6
assert server.PlayerSession._living_world_continuity_runtime_installed
assert server.PlayerSession._social_pastimes_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
print("SOCIAL_PASTIMES_OK")
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
        self.assertIn("SOCIAL_PASTIMES_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
