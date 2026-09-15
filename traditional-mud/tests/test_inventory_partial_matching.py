from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.crafting import ItemDefinition
from mud.inventory_inspection import item_detail_lines
from mud.partial_target_matching import resolve_target_command
from mud.stats import CharacterStats, EquipmentItem


ROOT = Path(__file__).resolve().parents[1]


class _Database:
    def __init__(self, items):
        self._items = dict(items)

    def list_items(self, _character_id):
        return [
            {"item_key": item_key, "quantity": quantity}
            for item_key, quantity in self._items.items()
        ]

    def item_quantity(self, _character_id, item_key):
        return int(self._items.get(item_key, 0))


class _World:
    def scene(self, _room_key):
        return SimpleNamespace(npc_keys=(), enemy_keys=())


class _Session:
    def __init__(self, items):
        self.character = SimpleNamespace(id=7, current_room="test_room")
        self.database = _Database(items)
        self.mobile_npcs = None


class InventoryPartialMatchingTests(unittest.TestCase):
    def setUp(self):
        self.token = ItemDefinition(
            key="goblin_earth_stamped_token",
            name="Stamped Earth Token",
            description="A small corroded token stamped in old Human lettering.",
            category="quest_item",
            tier=0,
        )
        self.knife = ItemDefinition(
            key="goblin_patchwork_scrapknife",
            name="Patchwork Scrapknife",
            description="A narrow working knife rebuilt from unrelated blades.",
            category="equipment",
            equipment=EquipmentItem(
                name="Patchwork Scrapknife",
                slot="main_hand",
                stat_bonuses=CharacterStats(might=1, grace=1),
            ),
            tier=0,
        )

    def test_item_token_expands_to_stamped_earth_token(self):
        session = _Session({self.token.key: 1})
        with patch.dict(
            "mud.partial_target_matching.crafting.ITEMS_BY_KEY",
            {self.token.key: self.token},
            clear=True,
        ):
            resolved = resolve_target_command(session, "item token", _World())
        self.assertEqual(resolved.command, "item Stamped Earth Token")
        self.assertEqual(resolved.matched_name, "Stamped Earth Token")

    def test_inspect_item_supports_partial_words(self):
        session = _Session({self.token.key: 1})
        with patch.dict(
            "mud.partial_target_matching.crafting.ITEMS_BY_KEY",
            {self.token.key: self.token},
            clear=True,
        ):
            resolved = resolve_target_command(session, "inspect item earth", _World())
        self.assertEqual(resolved.command, "inspect item Stamped Earth Token")

    def test_equipment_commands_only_consider_equipment(self):
        session = _Session({self.token.key: 1, self.knife.key: 1})
        with patch.dict(
            "mud.partial_target_matching.crafting.ITEMS_BY_KEY",
            {self.token.key: self.token, self.knife.key: self.knife},
            clear=True,
        ):
            resolved = resolve_target_command(session, "equip scrap", _World())
            token_attempt = resolve_target_command(session, "equip token", _World())
        self.assertEqual(resolved.command, "equip Patchwork Scrapknife")
        self.assertEqual(token_attempt.command, "equip token")
        self.assertIsNone(token_attempt.matched_name)

    def test_ambiguous_inventory_abbreviation_is_not_guessed(self):
        second = ItemDefinition(
            key="moon_token",
            name="Moon Token",
            description="Another token.",
            category="quest_item",
        )
        session = _Session({self.token.key: 1, second.key: 1})
        with patch.dict(
            "mud.partial_target_matching.crafting.ITEMS_BY_KEY",
            {self.token.key: self.token, second.key: second},
            clear=True,
        ):
            resolved = resolve_target_command(session, "item token", _World())
        self.assertTrue(resolved.ambiguous)
        self.assertEqual(resolved.ambiguous_names, ("Moon Token", "Stamped Earth Token"))

    def test_non_equipment_inventory_item_has_real_detail_view(self):
        session = _Session({self.token.key: 1})
        lines = item_detail_lines(session, self.token)
        joined = "\n".join(lines)
        self.assertIn("Stamped Earth Token", joined)
        self.assertIn(self.token.description, joined)
        self.assertIn("Type: Quest Item", joined)
        self.assertIn("Quantity: 1", joined)
        self.assertNotIn("Slot:", joined)

    def test_equipment_detail_keeps_slot_and_stats(self):
        session = _Session({self.knife.key: 1})
        joined = "\n".join(item_detail_lines(session, self.knife))
        self.assertIn("Slot: Main Hand", joined)
        self.assertIn("Might +1", joined)
        self.assertIn("Grace +1", joined)


class ProductionInventoryPartialMatchingTests(unittest.TestCase):
    def test_production_entrypoint_installs_inventory_inspection(self):
        code = r'''
import server
assert server.PlayerSession._partial_target_matching_runtime_installed
assert server.PlayerSession._inventory_inspection_runtime_installed
print("INVENTORY_PARTIAL_MATCHING_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("INVENTORY_PARTIAL_MATCHING_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
