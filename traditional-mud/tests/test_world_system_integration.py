from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.discovery_engine import (
    DiscoveryCondition,
    DiscoveryDefinition,
    DiscoveryRegistry,
    discovery_tell,
)
from mud.equipment_system import ensure_equipment_storage, set_equipped_item
from mud.faction_reputation import _quest_faction, adjust_reputation, regional_reaction
from mud.item_heritage import (
    HeritageHolder,
    _insert_instance_in_connection,
    ensure_item_heritage_schema,
    record_equipped_boss_victory,
)
from mud.room_presentation import render_room_lines


class _WeatherState:
    def __init__(self, weather: str) -> None:
        self.weather = weather

    def weather_for(self, _region_key: str) -> str:
        return self.weather


class _DiscoveryWorld:
    def __init__(self, weather: str = "rain") -> None:
        self.state = _WeatherState(weather)
        self._scene = SimpleNamespace(
            key="integration_test_room",
            name="Integration Test Road",
            region_key="human_kingdom",
            tags=("road", "frontier"),
        )

    def scene(self, room_key: str):
        return self._scene if room_key == self._scene.key else None


class WorldSystemIntegrationTests(unittest.TestCase):
    def _character(self, database: Database, suffix: str):
        account = database.create_account(f"integration_{suffix}", "not-a-real-hash")
        return database.create_character(
            account.id,
            f"Integration{suffix}",
            "human",
            "priest",
        )

    def test_legacy_cultural_quests_map_to_their_home_factions(self) -> None:
        expectations = {
            "human_cathedral_summons": "blackglass_crown",
            "forest_elf_first_walk": "green_circle",
            "moon_elf_third_chair": "moon_courts",
            "dwarf_first_shift": "chainmark_houses",
            "goblin_salvage": "brassgut_clans",
            "troll_raid": "troll_tribes",
            "undead_first_rites": "pale_houses",
            "sporekin_first_call": "rainroot_chorus",
        }
        for quest_key, faction_key in expectations.items():
            with self.subTest(quest_key=quest_key):
                self.assertEqual(
                    _quest_faction(SimpleNamespace(key=quest_key)),
                    faction_key,
                )
        self.assertIsNone(_quest_faction(SimpleNamespace(key="waymeet_shared_errand")))

    def test_faction_reputation_produces_a_local_world_reaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "mud.db")
            character = self._character(database, "Faction")

            self.assertEqual(
                regional_reaction(database, character.id, "human_kingdom"),
                "",
            )
            adjust_reputation(
                database,
                character.id,
                "blackglass_crown",
                standing=400,
                renown=100,
                reason="integration test",
                propagate=False,
            )

            reaction = regional_reaction(database, character.id, "human_kingdom")
            self.assertIn("Blackglass Crown", reaction)
            self.assertIn("recognizes you", reaction)

    def test_dynamic_discovery_conditions_leave_a_fair_room_tell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "mud.db")
            stored = self._character(database, "Discovery")
            character = SimpleNamespace(
                id=stored.id,
                name=stored.name,
                race="human",
                character_class="priest",
                level=5,
                current_room="integration_test_room",
            )
            session = SimpleNamespace(database=database, character=character)
            world = _DiscoveryWorld("rain")
            definition = DiscoveryDefinition(
                key="integration:rain_ditch",
                kind="secret",
                trigger="command",
                text="You uncover the hidden object.",
                verbs=("search",),
                targets=("ditch",),
                condition=DiscoveryCondition(
                    room_keys=("integration_test_room",),
                    weather=("rain",),
                ),
            )
            registry = DiscoveryRegistry((definition,))

            tell = discovery_tell(session, world, registry=registry)
            self.assertEqual(
                tell,
                "The ditch catches your attention under the current conditions.",
            )
            self.assertNotIn("search", tell.casefold())
            self.assertNotIn("hidden object", tell.casefold())

            world.state.weather = "clear"
            self.assertIsNone(discovery_tell(session, world, registry=registry))

    def test_equipped_tracked_items_remember_named_boss_victories_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "mud.db")
            character = self._character(database, "Heritage")
            ensure_item_heritage_schema(database)
            ensure_equipment_storage(database)

            with database.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                equipped = _insert_instance_in_connection(
                    db,
                    item_key="integration_test_relic",
                    heritage_kind="crafted",
                    owner_character_id=character.id,
                    holder=HeritageHolder.character(character.id),
                    maker_character_id=character.id,
                    maker_name=character.name,
                    maker_sequence=1,
                    origin_text="Integration test relic.",
                )
                unequipped = _insert_instance_in_connection(
                    db,
                    item_key="integration_test_spare",
                    heritage_kind="crafted",
                    owner_character_id=character.id,
                    holder=HeritageHolder.character(character.id),
                    maker_character_id=character.id,
                    maker_name=character.name,
                    maker_sequence=1,
                    origin_text="Integration test spare.",
                )

            set_equipped_item(database, character.id, "head", "integration_test_relic")

            first = record_equipped_boss_victory(
                database,
                character_id=character.id,
                enemy_key="integration_boss",
                enemy_name="the Integration Boss",
            )
            second = record_equipped_boss_victory(
                database,
                character_id=character.id,
                enemy_key="integration_boss",
                enemy_name="the Integration Boss",
            )

            self.assertEqual(first, 1)
            self.assertEqual(second, 0)
            with database.connect() as db:
                equipped_events = db.execute(
                    """
                    SELECT event_type, note
                    FROM item_heritage_events
                    WHERE instance_id = ?
                    """,
                    (int(equipped["id"]),),
                ).fetchall()
                spare_events = db.execute(
                    "SELECT event_type FROM item_heritage_events WHERE instance_id = ?",
                    (int(unequipped["id"]),),
                ).fetchall()

            self.assertEqual(len(equipped_events), 1)
            self.assertEqual(str(equipped_events[0]["event_type"]), "boss_victory")
            self.assertIn("[boss:integration_boss]", str(equipped_events[0]["note"]))
            self.assertEqual(spare_events, [])

    def test_room_renderer_keeps_the_cross_system_bridges(self) -> None:
        source = inspect.getsource(render_room_lines)
        self.assertIn("discovery_tell", source)
        self.assertIn("regional_reaction", source)


if __name__ == "__main__":
    unittest.main()
