from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.crafting as crafting
import mud.equipment_system as equipment
from mud.crafting import ItemDefinition
from mud.database import Database
from mud.equipment_accessory import ACCESSORY_SLOT_KEY, install_accessory_slot
from mud.mechanics import CombatantState
from mud.stats import CharacterStats, EquipmentItem


class DummyTelnet:
    gmcp_enabled = False

    async def send_gmcp(self, *_args, **_kwargs):
        return False


class AccessorySession:
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
            current_hp=base.maximum_hp(25),
            max_hp=base.maximum_hp(25),
            current_mana=base.maximum_mana(20),
            max_mana=base.maximum_mana(20),
            auto_attack_interval=2.5,
            stats=base,
            armor_class=0,
        )

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None


class EquipmentAccessoryTests(unittest.TestCase):
    def setUp(self):
        self.original_slots = equipment.EQUIPMENT_SLOTS
        self.original_labels = dict(equipment.SLOT_LABELS)
        self.original_aliases = dict(equipment._SLOT_ALIASES)
        self.original_items = crafting.ITEMS
        self.original_items_by_key = dict(crafting.ITEMS_BY_KEY)

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
        database = Database(Path(temp.name) / "accessory.db")
        account = database.create_account("accessory_acct", "not-a-real-hash")
        character = database.create_character(
            account.id,
            "Charmtest",
            "troll",
            "wizard",
            CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
        )
        return temp, database, AccessorySession(database, character)

    def test_accessory_is_the_eighth_single_equipment_slot(self):
        install_accessory_slot()

        self.assertEqual(
            equipment.EQUIPMENT_SLOTS,
            (
                "head",
                "chest",
                "legs",
                "feet",
                "hands",
                "main_hand",
                "off_hand",
                "accessory",
            ),
        )
        self.assertEqual(equipment.SLOT_LABELS[ACCESSORY_SLOT_KEY], "Accessory")
        for alias in ("accessory", "acc", "ring", "charm", "amulet", "neck", "necklace", "pendant"):
            self.assertEqual(equipment.normalize_slot(alias), ACCESSORY_SLOT_KEY)

        # Idempotent installation must never create a second accessory position.
        install_accessory_slot()
        self.assertEqual(equipment.EQUIPMENT_SLOTS.count(ACCESSORY_SLOT_KEY), 1)

    def test_accessory_uses_normal_stat_equipment_rules(self):
        install_accessory_slot()
        charm = ItemDefinition(
            key="test_winter_charm",
            name="Winter Charm",
            description="A test charm with ordinary stat bonuses and no scripted effect.",
            category="equipment",
            equipment=EquipmentItem(
                name="Winter Charm",
                slot="accessory",
                stat_bonuses=CharacterStats(mind=1, hp=2),
            ),
            tier=0,
        )
        crafting.ITEMS = crafting.ITEMS + (charm,)
        crafting.ITEMS_BY_KEY[charm.key] = charm

        temp, database, session = self._session()
        self.addCleanup(temp.cleanup)
        database.add_item(session.character.id, charm.key, 1)

        asyncio.run(equipment._equip(session, "winter charm"))
        worn = equipment.equipped_item_keys(database, session.character.id)
        self.assertEqual(worn[ACCESSORY_SLOT_KEY], charm.key)

        equipment.apply_equipment_to_combatant(session)
        self.assertEqual(session.combatant.stats.mind, session.character.mind + 1)
        self.assertEqual(session.combatant.stats.hp, session.character.hp_stat + 2)
        self.assertEqual(session.combatant.max_hp, session.character.stats.maximum_hp(25) + 2)
        self.assertFalse(charm.equipment.scripted_effects)

        asyncio.run(equipment._unequip(session, "ring"))
        self.assertNotIn(ACCESSORY_SLOT_KEY, equipment.equipped_item_keys(database, session.character.id))
        self.assertEqual(session.combatant.stats, session.character.stats)

    def test_equipment_display_includes_accessory_slot_even_when_empty(self):
        install_accessory_slot()
        temp, _database, session = self._session()
        self.addCleanup(temp.cleanup)

        asyncio.run(equipment._show_equipment(session))
        output = "".join(session.outputs)
        self.assertIn("Accessory", output)
        self.assertIn("[empty]", output)


if __name__ == "__main__":
    unittest.main()
