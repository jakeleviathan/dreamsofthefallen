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
    _ability_snapshot,
    _effects_snapshot,
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
            self.assertEqual(snapshot["players"], [{"name": "ModernHero (you)", "description": "a Human Brute standing nearby", "is_self": True}])
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

    def test_racial_active_abilities_are_assignable_hotbar_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = Database(root / "racial_hotbar.db")
            account = database.create_account("racial_hotbar", "x")
            goblin = database.create_character(
                account.id,
                "ScroungeTester",
                "goblin",
                "priest",
                CharacterStats(might=5, grace=7, love=8, mind=6, hp=5),
            )
            session = DummySession(database, goblin)

            payload = _ability_snapshot(session)
            by_key = {ability["key"]: ability for ability in payload["abilities"]}
            self.assertIn("racial_scrounge", by_key)
            scrounge = by_key["racial_scrounge"]
            self.assertEqual(scrounge["name"], "Scrounge")
            self.assertEqual(scrounge["command"], "RACIAL SCROUNGE")
            self.assertEqual(scrounge["source"], "racial")
            self.assertEqual(scrounge["race"], "goblin")
            self.assertEqual(scrounge["mana"], 0)
            self.assertEqual(scrounge["cooldown"], 8.0)
            self.assertEqual(scrounge["target_mode"], "self")
            self.assertTrue(scrounge["ready"])

            session.combatant.start_cooldown("racial_scrounge", 8.0)
            cooling = {
                ability["key"]: ability
                for ability in _ability_snapshot(session)["abilities"]
            }["racial_scrounge"]
            self.assertFalse(cooling["ready"])
            self.assertGreater(cooling["cooldown_remaining"], 0.0)

    def test_human_adapt_exposes_each_parameter_as_a_hotbar_choice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            racial = [
                ability
                for ability in _ability_snapshot(session)["abilities"]
                if ability.get("source") == "racial"
            ]
            self.assertEqual(
                {ability["key"] for ability in racial},
                {
                    "racial_adapt_might",
                    "racial_adapt_grace",
                    "racial_adapt_love",
                    "racial_adapt_mind",
                },
            )
            self.assertEqual(
                {ability["command"] for ability in racial},
                {
                    "RACIAL ADAPT MIGHT",
                    "RACIAL ADAPT GRACE",
                    "RACIAL ADAPT LOVE",
                    "RACIAL ADAPT MIND",
                },
            )

    def test_racial_hotbar_use_counts_as_onboarding_ability_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            room = _room_snapshot(session, self._world())
            _mark_onboarding_command(session, "north")
            _mark_onboarding_command(session, "quests")
            _mark_onboarding_command(session, "attack sewer rat")
            self.assertEqual(_onboarding_snapshot(session, room)["stage"], "ability")
            _mark_onboarding_command(session, "racial adapt might")
            self.assertFalse(_onboarding_snapshot(session, room)["active"])

    def test_effect_snapshot_reports_timed_player_effects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            from time import monotonic

            session._priest_resolve_blessing = 4
            session._priest_resolve_blessing_until = monotonic() + 30.0
            session._ward_effect_name = "Aegis of Faith"
            session.ward_until = monotonic() + 12.0
            session._arcane_surge_until = monotonic() + 15.0

            effects = _effects_snapshot(session)["effects"]
            by_key = {effect["key"]: effect for effect in effects}

            self.assertEqual(by_key["blessing_of_resolve"]["detail"], "+4 maximum Health")
            self.assertEqual(by_key["protective_ward"]["name"], "Aegis of Faith")
            self.assertIn("arcane_surge", by_key)
            self.assertGreater(by_key["blessing_of_resolve"]["remaining"], 0)

    def test_effect_snapshot_reports_only_weather_mechanics_affecting_exposed_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            world = self._world()
            world.state.set_weather("human_kingdom", "rain")

            effects = _effects_snapshot(session, world)["effects"]
            weather_effects = {
                effect["key"]: effect
                for effect in effects
                if effect["kind"] == "weather"
            }

            self.assertEqual(
                set(weather_effects),
                {"weather_concealment", "weather_footing_slick"},
            )
            self.assertIn("+8 percentage points to flee chance", weather_effects["weather_concealment"]["detail"])
            self.assertIn("Outdoor movement is slowed", weather_effects["weather_footing_slick"]["detail"])
            self.assertIsNone(weather_effects["weather_concealment"]["remaining"])

    def test_effect_snapshot_hides_weather_mechanics_under_solid_cover(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            session.database.set_character_room(session.character.id, "human_grand_cathedral")
            session.character = session.database.get_character_by_name(session.character.name)
            world = self._world()
            world.state.set_weather("human_kingdom", "rain")

            effects = _effects_snapshot(session, world)["effects"]
            self.assertFalse(any(effect["kind"] == "weather" for effect in effects))

    def test_effect_snapshot_shows_fire_disruption_only_for_character_with_fire_magic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = Database(root / "weather_effects.db")
            account = database.create_account("weather_effects", "x")
            character = database.create_character(
                account.id,
                "WeatherMage",
                "human",
                "wizard",
                CharacterStats(might=5, grace=5, love=6, mind=8, hp=5),
            )
            session = DummySession(database, character)
            world = self._world()
            world.state.set_weather("human_kingdom", "storm")

            effects = _effects_snapshot(session, world)["effects"]
            by_key = {effect["key"]: effect for effect in effects}
            self.assertIn("weather_fire_disruption", by_key)
            self.assertIn("20% chance", by_key["weather_fire_disruption"]["detail"])

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
                    "Dreams.Effects",
                    "Dreams.Context",
                    "Dreams.Onboarding",
                    "Dreams.Inventory",
                    "Dreams.Quests",
                }
                <= packages
            )
            payloads = {package: payload for package, payload in session.telnet.messages}
            self.assertEqual(payloads["Room.Info"]["num"], stable_room_number("human_demon_gate"))
            reflection_features = [
                feature
                for feature in payloads["Dreams.Room"]["features"]
                if str(feature.get("key", "")).startswith("reflection:")
            ]
            self.assertTrue(reflection_features)
            self.assertTrue(any(feature.get("can_use") for feature in reflection_features))
            self.assertTrue(payloads["Dreams.Abilities"]["abilities"])
            self.assertTrue(
                any(
                    ability.get("source") == "racial"
                    for ability in payloads["Dreams.Abilities"]["abilities"]
                )
            )
            self.assertEqual(payloads["Dreams.Effects"]["effects"], [])
            self.assertTrue(payloads["Dreams.Context"]["actions"])
            self.assertTrue(
                any(
                    action.get("command") == "ATELIER"
                    for action in payloads["Dreams.Context"]["actions"]
                )
            )
            self.assertTrue(payloads["Dreams.Inventory"]["items"])
            self.assertTrue(payloads["Dreams.Quests"]["active"])

    def test_official_client_sources_include_discovery_mapper_and_release_version(self):
        self.assertEqual(MODERN_CLIENT_VERSION, "2.0.0")
        self.assertEqual(CURRENT_MUDLET_HUD_VERSION, "2.2.11")
        self.assertEqual(configured_mudlet_gui_offer().version, OFFICIAL_MUDLET_HUD_VERSION)

        root = Path(__file__).resolve().parents[1]
        modern_lua = (root / "mudlet" / "DreamsOfTheFallenHUD" / "src" / "modern.lua").read_text(encoding="utf-8")
        map_lua = (root / "mudlet" / "DreamsOfTheFallenHUD" / "src" / "map.lua").read_text(encoding="utf-8")
        build_source = (root / "mudlet" / "DreamsOfTheFallenHUD" / "build_package.py").read_text(encoding="utf-8")
        for marker in (
            "Dreams.Room",
            "Dreams.Party",
            "Dreams.Quests",
            "Dreams.Inventory",
            "Dreams.Abilities",
            "Dreams.Effects",
            "Dreams.Context",
            "Dreams.Onboarding",
            "Dreams.Crafting",
            "renderCrafting",
            "synthCue",
            "hotbarAssignments",
            "cycleHotbarSlot",
            "table.save",
            "DreamsHUD.HotbarSet",
            "DreamsHUD.EffectsPane",
            "ACTIVE EFFECTS",
            "inspectInventoryItem",
            "echoLink(",
            "string.format(\"send(%q, true)\", \"ITEM \" .. name)",
        ):
            self.assertIn(marker, modern_lua)
        self.assertNotIn("Geyser.Mapper:new", modern_lua)
        self.assertIn('{ "effects", "EFFECTS" }', modern_lua)
        self.assertIn("Dreams.Map", map_lua)
        self.assertIn("discovered_count", map_lua)
        self.assertIn('ROOT / "src" / "modern.lua"', build_source)
        self.assertIn('ROOT / "src" / "map.lua"', build_source)

    def test_production_server_installs_modern_layer_outermost(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
from mud.client_gui import CURRENT_MUDLET_HUD_VERSION, configured_mudlet_gui_offer
from mud.modern_client_experience import MODERN_CLIENT_VERSION

assert server.PlayerSession._modern_client_runtime_installed
assert server.PlayerSession._exploration_map_runtime_installed
assert server.PlayerSession._exploration_map_gmcp_runtime_installed
assert MODERN_CLIENT_VERSION == "2.0.0"
assert CURRENT_MUDLET_HUD_VERSION == "2.2.11"
assert configured_mudlet_gui_offer().enabled
print("MODERN_CLIENT_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("MODERN_CLIENT_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
