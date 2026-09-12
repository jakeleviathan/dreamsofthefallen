from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import mud.waymeet_adventure_arc as arc
from mud.database import Database
from mud.waymeet_adventure_runtime import corrected_adventure_augmentations


class DummySession:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.messages: list[str] = []
        self.active_enemy = None
        self.combatant = None

    async def send(self, text: str) -> None:
        self.messages.append(text)


class WaymeetAdventureArcTests(unittest.TestCase):
    def _session(self, root: Path, *, level: int = 8, room_key: str = arc.BELL_ROPE_ROOM) -> DummySession:
        database = Database(root / "adventure.db")
        account = database.create_account("adventure_account", "x")
        character = database.create_character(account.id, "Roadfinder", "human", "wizard")
        # The DB's XP/level helper is intentionally not required for these parser
        # tests; only room placement and persistent flags matter here.
        database.set_character_room(character.id, room_key)
        character = database.get_character_by_name("Roadfinder")
        assert character is not None
        return DummySession(database, character)

    def test_authored_room_counts_form_a_substantial_early_game_ring(self):
        self.assertEqual(len(arc.ADVENTURE_OVERWORLD_KEYS), 6)
        self.assertEqual(len(arc.TOLL_ROOM_KEYS), 10)
        self.assertEqual(len(arc.BELL_ROOM_KEYS), 10)
        self.assertEqual(len(arc.SCAR_ROOM_KEYS), 12)
        self.assertEqual(len(arc.ECHO_ROOM_KEYS), 14)
        self.assertEqual(len(arc.ALL_ADVENTURE_ROOM_KEYS), 52)
        self.assertEqual(len(set(arc.ALL_ADVENTURE_ROOM_KEYS)), 52)

    def test_progression_has_three_early_dungeons_then_level_eight_capstone(self):
        no_flags = set()
        rows = arc.adventure_progress(no_flags, 2)
        self.assertIn("Old Toll: available", rows)
        self.assertIn("Crooked Bell: level 3", rows)
        self.assertIn("King's Scar: level 5", rows)
        self.assertIn("Vault of the First Echo: level 8 and three prior clears", rows)

        cleared = {arc.TOLL_COMPLETE, arc.BELL_COMPLETE, arc.SCAR_COMPLETE}
        rows = arc.adventure_progress(cleared, 8)
        self.assertIn("Vault of the First Echo: Echo Ridge is answering", rows)

    def test_outer_waymeet_links_and_secret_exits_are_conditioned(self):
        augmentations = corrected_adventure_augmentations()

        old_toll = augmentations[arc.WAYMEET_BROKEN_MILE_KEY].extra_exits[0]
        self.assertEqual(old_toll.destination_key, arc.OLD_TOLL_ROAD)
        self.assertEqual(old_toll.condition.min_level, 2)

        bell = augmentations[arc.WAYMEET_BRIARCUT_KEY].extra_exits[0]
        self.assertEqual(bell.destination_key, arc.BRIARWOOD_EDGE)
        self.assertEqual(bell.condition.min_level, 3)

        scar = augmentations[arc.WAYMEET_QUARRY_KEY].extra_exits[0]
        self.assertEqual(scar.destination_key, arc.KINGS_SCAR_APPROACH)
        self.assertEqual(scar.condition.min_level, 5)

        vault = augmentations[arc.ECHO_RIDGE].extra_exits[0]
        self.assertEqual(vault.destination_key, arc.ECHO_THRESHOLD)
        self.assertEqual(vault.condition.min_level, 8)
        self.assertEqual(
            set(vault.condition.required_flags),
            {arc.TOLL_COMPLETE, arc.BELL_COMPLETE, arc.SCAR_COMPLETE},
        )
        self.assertTrue(vault.hidden_when_unavailable)

        hidden_margin = [
            exit_def
            for exit_def in augmentations[arc.ECHO_MIRROR_CHOIR].extra_exits
            if exit_def.destination_key == arc.ECHO_FIRST_BREATH_MARGIN
        ][0]
        self.assertEqual(hidden_margin.condition.required_flags, (arc.DEEP_SECRET_OPEN,))
        self.assertTrue(hidden_margin.hidden_when_unavailable)

    def test_room_features_teach_the_parser_verbs_instead_of_hiding_them(self):
        augmentations = corrected_adventure_augmentations()
        searchable = augmentations[arc.TOLL_LEDGER].features[0].examine_text.upper()
        listenable = augmentations[arc.BELL_NAVE].features[0].examine_text.upper()
        climbable = augmentations[arc.SCAR_LIFT].features[0].examine_text.upper()
        pullable = augmentations[arc.SCAR_WINCH].features[0].examine_text.upper()
        touchable = augmentations[arc.ECHO_PLATE_WEST].features[0].examine_text.upper()
        self.assertIn("SEARCH", searchable)
        self.assertIn("LISTEN", listenable)
        self.assertIn("CLIMB", climbable)
        self.assertIn("PULL", pullable)
        self.assertIn("TOUCH", touchable)

    def test_crooked_bell_sequence_resets_on_error_and_opens_on_low_high_low(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self._session(Path(temp_dir))
            session.database.grant_flag(session.character.id, arc.BELL_NAVE_HEARD)
            session.database.grant_flag(session.character.id, arc.BELL_GALLERY_HEARD)

            asyncio.run(arc._pull(session, "low"))
            self.assertEqual(getattr(session, "_bell_rope_progress"), ("low",))
            asyncio.run(arc._pull(session, "low"))
            self.assertEqual(getattr(session, "_bell_rope_progress"), ())
            self.assertIn("sequence resets", "".join(session.messages).lower())

            session.messages.clear()
            asyncio.run(arc._pull(session, "low"))
            asyncio.run(arc._pull(session, "high"))
            asyncio.run(arc._pull(session, "low"))
            flags = set(session.database.list_flags(session.character.id))
            self.assertIn(arc.BELL_ROPES_SOLVED, flags)
            self.assertIn("up is now open", "".join(session.messages).lower())

    def test_deep_secret_requires_all_three_optional_outer_marks(self):
        self.assertFalse(arc._all_outer_secrets({arc.TOLL_SECRET, arc.BELL_SECRET}))
        self.assertTrue(arc._all_outer_secrets({arc.TOLL_SECRET, arc.BELL_SECRET, arc.SCAR_SECRET}))

    def test_listener_rewards_varied_ability_use_instead_of_one_button_spam(self):
        self.assertEqual(arc._listener_reflection_damage(1), 2)
        self.assertEqual(arc._listener_reflection_damage(2), 4)
        self.assertEqual(arc._listener_reflection_damage(3), 6)
        self.assertEqual(arc._listener_reflection_damage(4), 8)
        self.assertEqual(arc._listener_reflection_damage(50), 8)
        self.assertEqual(arc.LISTENER_BELOW.max_hp, 360)
        self.assertEqual(arc.LISTENER_BELOW.armor_class, 18)

    def test_first_echo_lore_matches_the_established_one_breath_cosmology(self):
        margin = next(room for room in arc.ECHO_ROOMS if room.key == arc.ECHO_FIRST_BREATH_MARGIN)
        text = margin.description.lower()
        self.assertIn("leviathan", text)
        self.assertIn("one breath of life", text)
        self.assertIn("no second word", text)
        self.assertIn("echo is simply there", text)

    def test_bosses_are_distinct_and_not_static_room_furniture(self):
        bosses = {arc.TOLLMASTER.key, arc.HOLLOW_BELLKEEPER.key, arc.RIFTBACK_MATRIARCH.key, arc.LISTENER_BELOW.key}
        static_enemy_keys = {enemy_key for room in arc.ALL_ADVENTURE_ROOMS for enemy_key in room.enemy_keys}
        self.assertTrue(bosses.isdisjoint(static_enemy_keys))
        self.assertEqual(arc.TOLLMASTER.max_hp, 96)
        self.assertEqual(arc.HOLLOW_BELLKEEPER.max_hp, 142)
        self.assertEqual(arc.RIFTBACK_MATRIARCH.max_hp, 210)
        self.assertEqual(arc.LISTENER_BELOW.max_hp, 360)

    def test_production_server_installs_arc_inside_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.waymeet_adventure_arc as arc
assert server.PlayerSession._waymeet_adventure_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
assert len(arc.ALL_ADVENTURE_ROOM_KEYS) == 52
for key in arc.ALL_ADVENTURE_ROOM_KEYS:
    assert key in server.WORLD.legacy_rooms, key
assert arc.ECHO_LISTENER_COURT in server.WORLD.legacy_rooms
print("WAYMEET_ADVENTURE_OK")
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
        self.assertIn("WAYMEET_ADVENTURE_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
