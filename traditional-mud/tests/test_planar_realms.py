from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import mud.planar_realms as planes


class PlanarRealmTests(unittest.TestCase):
    def test_exactly_seven_unevenly_rare_realms_exist(self):
        self.assertEqual(len(planes.PLANES), 7)
        self.assertEqual({plane.name for plane in planes.PLANES}, {
            "The Pale",
            "Brass Heaven",
            "The Root Below",
            "The Red Country",
            "The Sea Above",
            "The Country Behind the Door",
            "The Unspoken",
        })
        self.assertEqual(sum(1 for plane in planes.PLANES if plane.rarity == "mythic"), 2)
        self.assertFalse(planes.PLANES[-1].chronicle_public)
        self.assertFalse(planes.PLANES[-2].chronicle_public)

    def test_realms_are_places_not_single_teleport_rooms(self):
        self.assertEqual(len(planes.ROOMS), 28)
        self.assertTrue(all(len(plane.rooms) == 4 for plane in planes.PLANES))
        self.assertEqual(len({room.key for room in planes.ROOMS}), 28)
        for plane in planes.PLANES:
            self.assertTrue(all(room in planes.PLANE_BY_ROOM for room in plane.rooms))

    def test_each_plane_has_its_own_material_culture_and_story_objects(self):
        self.assertEqual(len(planes.ITEMS), 21)
        keys = {item.key for item in planes.ITEMS}
        self.assertEqual(len(keys), 21)
        for prefix in (
            "pale_", "brass_heaven_", "root_below_", "red_country_",
            "sea_above_", "behind_door_", "unspoken_",
        ):
            self.assertGreaterEqual(sum(key.startswith(prefix) for key in keys), 3)

    def test_discovery_is_not_presented_as_a_completion_checklist(self):
        source = Path(planes.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"planes"', source.lower())
        self.assertNotIn("7/7", source)
        self.assertIn("no seven-plane checklist", Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8"))

    def test_red_country_keys_the_country_behind_the_door(self):
        source = Path(planes.__file__).read_text(encoding="utf-8")
        self.assertIn('"red_country_key"', source)
        self.assertIn('verb == "try red key"', source)
        self.assertIn('RED_TOWER, "search ladder"', source)

    def test_unspoken_requires_prior_experience_and_rare_alignment(self):
        source = Path(planes.__file__).read_text(encoding="utf-8")
        self.assertIn("_planes_seen(self) < 5", source)
        self.assertIn("moment.day_number % 17 != 3", source)
        self.assertIn("wait for second word", source)
        self.assertIn("ECHO_COMPLETE", source)

    def test_production_server_installs_planar_layer_before_help_and_modern_client(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server
import mud.planar_realms as planes
assert server.PlayerSession._planar_realms_installed
assert server.PlayerSession._command_guide_runtime_installed
assert server.PlayerSession._modern_client_runtime_installed
assert len(planes.PLANES) == 7
assert len(planes.ROOMS) == 28
assert all(room.key in server.WORLD.legacy_rooms for room in planes.ROOMS)
print("PLANES_OK")
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
        self.assertIn("PLANES_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
