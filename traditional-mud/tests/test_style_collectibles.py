from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import mud.command_guide as guide
import mud.style_collectibles as style
from mud.database import Database


class DummyTelnet:
    gmcp_enabled = False

    async def send_gmcp(self, package, payload):
        return None


class DummySession:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.telnet = DummyTelnet()
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class StyleCollectiblesTests(unittest.TestCase):
    def setUp(self) -> None:
        style.install_style_content()

    def _characters(self, root: Path):
        db = Database(root / "style.db")
        account = db.create_account("style_account", "x")
        first = db.create_character(account.id, "Velvet", "human", "wizard")
        second = db.create_character(account.id, "Morrow", "moon_elf", "priest")
        return db, first, second

    def test_launch_style_catalog_is_substantial_and_metadata_complete(self):
        self.assertGreaterEqual(len(style.STYLE_ITEMS), 20)
        self.assertEqual(len(style.FRAGRANCE_ITEMS), 9)
        self.assertEqual(set(style.STYLE_META_BY_KEY), {item.key for item in style.STYLE_ITEMS})
        for meta in style.STYLE_META:
            self.assertIn(meta.rarity, style.RARITY_ORDER)
            self.assertIn(meta.style_slot, style.STYLE_SLOTS)
            self.assertTrue(meta.style_tags)
            self.assertTrue(meta.house)
            self.assertTrue(meta.collection)

    def test_every_launch_fragrance_is_modest_timed_xp_not_combat_power(self):
        self.assertEqual(len(style.FRAGRANCES), 9)
        self.assertEqual({fragrance.xp_bonus_percent for fragrance in style.FRAGRANCES}, {10})
        self.assertEqual({fragrance.duration_seconds for fragrance in style.FRAGRANCES}, {3600})
        self.assertEqual({fragrance.house for fragrance in style.FRAGRANCES}, {"House Veyr", "Atelier Vael", "Root & Reed"})
        for fragrance in style.FRAGRANCES:
            item = style.crafting.ITEMS_BY_KEY[fragrance.item_key]
            self.assertEqual(item.category, "fragrance")
            self.assertIsNone(item.equipment)

    def test_fragrance_xp_hook_preserves_a_true_ten_percent_over_small_awards(self):
        with tempfile.TemporaryDirectory() as temp:
            db, first, _ = self._characters(Path(temp))
            style.ensure_style_schema(db)
            now = int(time.time())
            with db.connect() as conn:
                conn.execute(
                    "INSERT INTO character_fragrance_effects (character_id, fragrance_key, applied_at_epoch, expires_at_epoch, bonus_fraction, bonus_xp_earned) VALUES (?, ?, ?, ?, 0.0, 0)",
                    (first.id, "fragrance_blackglass_no7", now, now + 3600),
                )
            style._install_xp_bonus_hook()
            # Ten awards of 1 XP should become 11 total, not 20 through minimum-one rounding.
            for _ in range(10):
                db.add_experience(first.id, 1)
            refreshed = db.get_character_by_name(first.name)
            self.assertEqual(refreshed.experience, 11)
            effect = style._active_fragrance(db, first.id)
            self.assertEqual(int(effect["bonus_xp_earned"]), 1)

    def test_wearing_fashion_uses_independent_slots_and_does_not_consume_item(self):
        with tempfile.TemporaryDirectory() as temp:
            db, first, _ = self._characters(Path(temp))
            db.add_item(first.id, "style_veyra_cutaway_coat", 1)
            session = DummySession(db, first)
            asyncio.run(style._wear_style(session, "Veyra Cutaway Coat"))
            worn = style._worn_style(db, first.id)
            self.assertEqual(worn["chest"], "style_veyra_cutaway_coat")
            self.assertEqual(db.item_quantity(first.id, "style_veyra_cutaway_coat"), 1)
            self.assertIn("changes appearance, not combat stats", "".join(session.messages))

    def test_heritage_piece_has_serial_origin_and_direct_trade_history(self):
        with tempfile.TemporaryDirectory() as temp:
            db, first, second = self._characters(Path(temp))
            key = "style_listener_echo_veil"
            db.add_item(first.id, key, 1)
            serial = style._register_instance(db, first.id, key, "Test Listener clear.")
            style._patch_trade_for_provenance()
            moved = style.trade_experience.exchange_items(db, first.id, {key: 1}, second.id, {})
            self.assertTrue(moved)
            self.assertEqual(db.item_quantity(first.id, key), 0)
            self.assertEqual(db.item_quantity(second.id, key), 1)
            owned = style._owned_instances(db, second.id, key)
            self.assertEqual(len(owned), 1)
            self.assertEqual(str(owned[0]["serial"]), serial)
            with db.connect() as conn:
                history = conn.execute(
                    "SELECT action, from_character_id, to_character_id FROM style_item_history WHERE instance_id = ? ORDER BY id",
                    (int(owned[0]["id"]),),
                ).fetchall()
            self.assertEqual([row["action"] for row in history], ["origin", "trade"])
            self.assertEqual(int(history[-1]["from_character_id"]), first.id)
            self.assertEqual(int(history[-1]["to_character_id"]), second.id)

    def test_seasonal_catalog_has_one_limited_heritage_piece_per_season(self):
        self.assertEqual(set(style.SEASONAL_STYLE), {"spring", "summer", "autumn", "winter"})
        for key in style.SEASONAL_STYLE.values():
            meta = style.STYLE_META_BY_KEY[key]
            self.assertTrue(meta.limited)
            self.assertTrue(meta.provenance_track)
            self.assertEqual(meta.rarity, "epic")

    def test_command_guide_has_searchable_categories_and_new_style_surface(self):
        self.assertIn("style", guide.CATEGORIES)
        self.assertIn("dungeons", guide.CATEGORIES)
        self.assertIn("economy", guide.CATEGORIES)
        style_rows = [entry for entry in guide.COMMANDS if entry.category == "style"]
        syntaxes = {entry.syntax for entry in style_rows}
        self.assertIn("STYLE / WARDROBE / OUTFIT / FASHION", syntaxes)
        self.assertIn("APPLY FRAGRANCE <name> / SPRAY <name>", syntaxes)
        self.assertIn("PROVENANCE <item>", syntaxes)
        self.assertGreaterEqual(len(guide.COMMANDS), 100)

    def test_production_server_installs_style_and_command_guide_before_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.style_collectibles as style
import mud.command_guide as guide
assert server.PlayerSession._style_collectibles_runtime_installed
assert server.PlayerSession._command_guide_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
assert "style_listener_echo_veil" in style.crafting.ITEMS_BY_KEY
assert len(style.FRAGRANCES) == 9
assert len(guide.COMMANDS) >= 100
print("STYLE_GUIDE_OK")
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
        self.assertIn("STYLE_GUIDE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
