from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mud.client_gui import (
    CURRENT_MUDLET_HUD_VERSION,
    OFFICIAL_MUDLET_HUD_VERSION,
    configured_mudlet_gui_offer,
)
from mud.database import Database
from mud.mechanics import CombatantState
from mud.modern_client_experience import (
    MODERN_CLIENT_VERSION,
    _mark_onboarding_command,
    _onboarding_snapshot,
    _room_snapshot,
    push_modern_state,
    stable_room_number,
)
from mud.room_engine import WorldService
from mud.stats import CharacterStats


class FakeTelnet:
    def __init__(self) -> None:
        self.gmcp_enabled = True
        self.messages: list[tuple[str, object]] = []

    async def send_gmcp(self, package: str, payload=None) -> bool:
        self.messages.append((package, payload))
        return True


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "human",
            current_hp=40,
            max_hp=40,
            current_mana=24,
            max_mana=24,
            auto_attack_interval=3.0,
            stats=CharacterStats(might=10, grace=6, love=5, mind=5, hp=15),
            armor_class=8,
        )
        self.active_enemy = None
        self.telnet = FakeTelnet()


class ModernClientExperienceTests(unittest.TestCase):
    def _session(self, root: Path) -> DummySession:
        database = Database(root / "modern.db")
        account = database.create_account("modern_test", "x")
        character = database.create_character(
            account.id,
            "ModernHero",
            "human",
            "brute",
            CharacterStats(might=10, grace=6, love=5, mind=5, hp=15),
        )
        return DummySession(database, character)

    @staticmethod
    def _world() -> WorldService:
        # Unit tests intentionally use a fresh base world. Importing mud.server at
        # discovery time assembles every authored runtime into shared module state
        # and contaminates unrelated isolation tests. Production assembly is
        # verified separately in a subprocess below.
        return WorldService()

    def test_room_numbers_are_stable_positive_mapper_ids(self):
        first = stable_room_number("human_demon_gate")
        second = stable_room_number("human_ashen_way")
        self.assertGreater(first, 0)
        self.assertGreater(second, 0)
        self.assertNotEqual(first, second)
        self.assertEqual(first, stable_room_number("human_demon_gate"))

    def test_room_snapshot_exposes_visible_mapper_data_without_text_scraping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            snapshot = _room_snapshot(session, self._world())
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot["key"], "human_demon_gate")
            self.assertEqual(snapshot["num"], stable_room_number("human_demon_gate"))
            self.assertTrue(snapshot["name"])
            self.assertIsInstance(snapshot["exits"], dict)
            self.assertTrue(all(isinstance(value, int) and value > 0 for value in snapshot["exits"].values()))

    def test_onboarding_is_persistent_and_gets_out_of_the_way(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            room = _room_snapshot(session, self._world())
            self.assertEqual(_onboarding_snapshot(session, room)["stage"], "movement")
            _mark_onboarding_command(session, "north")
            self.assertEqual(_onboarding_snapshot(session, room)["stage"], "reference")
            _mark_onboarding_command(session, "quests")
            self.assertEqual(_onboarding_snapshot(session, room)["stage"], "combat")
            _mark_onboarding_command(session, "attack sewer rat")
            self.assertEqual(_onboarding_snapshot(session, room)["stage"], "ability")
            _mark_onboarding_command(session, "cast heavy strike")
            self.assertFalse(_onboarding_snapshot(session, room)["active"])

    def test_full_push_emits_modern_structured_surfaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            asyncio.run(push_modern_state(session, self._world(), full=True))
            packages = {package for package, _payload in session.telnet.messages}
            self.assertTrue(
                {
                    "Room.Info",
                    "Dreams.Room",
                    "Dreams.Party",
                    "Dreams.Abilities",
                    "Dreams.Context",
                    "Dreams.Onboarding",
                    "Dreams.Inventory",
                    "Dreams.Quests",
                }
                <= packages
            )
            payloads = {package: payload for package, payload in session.telnet.messages}
            self.assertEqual(payloads["Room.Info"]["num"], stable_room_number("human_demon_gate"))
            self.assertTrue(payloads["Dreams.Abilities"]["abilities"])
            self.assertTrue(payloads["Dreams.Context"]["actions"])
            self.assertTrue(payloads["Dreams.Inventory"]["items"])
            self.assertTrue(payloads["Dreams.Quests"]["active"])

    def test_official_client_sources_are_hud_two_with_legacy_offer_compatibility(self):
        self.assertEqual(MODERN_CLIENT_VERSION, "2.0.0")
        self.assertEqual(CURRENT_MUDLET_HUD_VERSION, "2.0.0")
        self.assertEqual(configured_mudlet_gui_offer().version, OFFICIAL_MUDLET_HUD_VERSION)

        root = Path(__file__).resolve().parents[1]
        modern_lua = (root / "mudlet" / "DreamsOfTheFallenHUD" / "src" / "modern.lua").read_text(encoding="utf-8")
        build_source = (root / "mudlet" / "DreamsOfTheFallenHUD" / "build_package.py").read_text(encoding="utf-8")
        for marker in (
            "Geyser.Mapper",
            "Dreams.Room",
            "Dreams.Party",
            "Dreams.Quests",
            "Dreams.Inventory",
            "Dreams.Abilities",
            "Dreams.Context",
            "Dreams.Onboarding",
            "synthCue",
        ):
            self.assertIn(marker, modern_lua)
        self.assertIn('ROOT / "src" / "modern.lua"', build_source)

    def test_production_server_installs_modern_layer_outermost(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.client_gui import CURRENT_MUDLET_HUD_VERSION, configured_mudlet_gui_offer
from mud.modern_client_experience import MODERN_CLIENT_VERSION

assert server.PlayerSession._modern_client_runtime_installed
assert MODERN_CLIENT_VERSION == "2.0.0"
assert CURRENT_MUDLET_HUD_VERSION == "2.0.0"
assert configured_mudlet_gui_offer().enabled
print("MODERN_CLIENT_OK")
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
        self.assertIn("MODERN_CLIENT_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
