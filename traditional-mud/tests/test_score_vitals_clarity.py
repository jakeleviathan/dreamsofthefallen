from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.equipment_system as equipment
from mud.database import Database
from mud.equipment_accessory import _show_live_stats_with_vitals, install_accessory_slot
from mud.mechanics import CombatantState
from mud.stats import CharacterStats


class DummyTelnet:
    gmcp_enabled = False

    async def send_gmcp(self, *_args, **_kwargs):
        return False


class ScoreSession:
    def __init__(self, database: Database, character):
        self.database = database
        self.character = character
        self.active_enemy = None
        self.outputs: list[str] = []
        self.telnet = DummyTelnet()
        base = character.stats
        self.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "",
            current_hp=26,
            max_hp=27,
            current_mana=38,
            max_mana=38,
            current_movement=102,
            max_movement=102,
            auto_attack_interval=2.5,
            stats=base,
            armor_class=0,
        )

    async def send(self, text: str):
        self.outputs.append(text)


class ScoreVitalsClarityTests(unittest.TestCase):
    def setUp(self):
        self.original_slots = equipment.EQUIPMENT_SLOTS
        self.original_labels = dict(equipment.SLOT_LABELS)
        self.original_aliases = dict(equipment._SLOT_ALIASES)
        self.original_items = crafting.ITEMS
        self.original_items_by_key = dict(crafting.ITEMS_BY_KEY)
        equipment.install_equipment_content()
        install_accessory_slot()

    def tearDown(self):
        equipment.EQUIPMENT_SLOTS = self.original_slots
        equipment.SLOT_LABELS.clear()
        equipment.SLOT_LABELS.update(self.original_labels)
        equipment._SLOT_ALIASES.clear()
        equipment._SLOT_ALIASES.update(self.original_aliases)
        crafting.ITEMS = self.original_items
        crafting.ITEMS_BY_KEY.clear()
        crafting.ITEMS_BY_KEY.update(self.original_items_by_key)

    def _session(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "score-vitals.db")
        account = database.create_account("score_vitals", "not-a-real-hash")
        character = database.create_character(
            account.id,
            "Prime",
            "goblin",
            "priest",
            CharacterStats(might=4, grace=7, love=12, mind=6, hp=5),
            deity_key="zerjz",
        )
        return temp, database, ScoreSession(database, character)

    def test_score_shows_live_health_mana_and_movement_totals(self):
        temp, _database, session = self._session()
        self.addCleanup(temp.cleanup)

        asyncio.run(_show_live_stats_with_vitals(session))
        output = "".join(session.outputs)

        self.assertIn("--- Vitals (current / maximum) ---", output)
        self.assertIn("Health   : 26 / 27", output)
        self.assertIn("Mana     : 38 / 38", output)
        self.assertIn("Movement : 102 / 102", output)
        self.assertIn("--- Attributes (base + equipment = total) ---", output)

    def test_hp_attribute_is_explicitly_not_the_live_health_total(self):
        temp, database, session = self._session()
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, "goblin_reedfen_patchvest", 1)
        equipment.set_equipped_item(
            database,
            session.character.id,
            "chest",
            "goblin_reedfen_patchvest",
        )

        asyncio.run(_show_live_stats_with_vitals(session))
        output = "".join(session.outputs)

        self.assertIn("HP stat: 5 +1 = 6", output)
        self.assertIn("adds +6 to maximum Health", output)
        self.assertNotIn("\r\nHP   : 5 +1 = 6", output)
        self.assertIn("Mana bonus from Love + Mind: 18", output)

    def test_score_uses_current_combatant_vitals_instead_of_recomputing_static_totals(self):
        temp, _database, session = self._session()
        self.addCleanup(temp.cleanup)
        session.combatant.current_hp = 11
        session.combatant.max_hp = 35
        session.combatant.current_mana = 9
        session.combatant.max_mana = 41
        session.combatant.current_movement = 77
        session.combatant.max_movement = 109

        asyncio.run(_show_live_stats_with_vitals(session))
        output = "".join(session.outputs)

        self.assertIn("Health   : 11 / 35", output)
        self.assertIn("Mana     : 9 / 41", output)
        self.assertIn("Movement : 77 / 109", output)


if __name__ == "__main__":
    unittest.main()
