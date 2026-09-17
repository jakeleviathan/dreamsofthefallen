from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


class RoomPresentationTests(unittest.TestCase):
    def test_production_goblin_room_has_colored_scan_sections(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import tempfile
from pathlib import Path
from types import SimpleNamespace

import server
from mud.database import Database
from mud.enemy_lifecycle import clear_static_enemy_respawn, mark_static_enemy_defeated
from mud.goblin_swamp import GOBLIN_MUDGLASS_CROSSING_KEY, MIRE_TICK_SWARM
from mud.room_presentation import (
    BUSINESS,
    ENEMY,
    EXIT,
    FEATURE,
    NPC,
    REGION,
    TITLE,
    render_room_lines,
)

class DB:
    def list_flags(self, _character_id):
        return []

session = SimpleNamespace(
    character=SimpleNamespace(
        id=1,
        race="goblin",
        character_class="priest",
        level=1,
        current_room="goblin_clattergate",
    ),
    database=DB(),
    mobile_npcs=None,
)

text = "\r\n".join(render_room_lines(session, server.WORLD))
assert f"{TITLE}The Clattergate" in text, text
assert f"{REGION}Junk City And Swamps" in text, text
assert f"{FEATURE}[ Notable ]" in text, text
assert f"{NPC}[ People ]" in text, text
assert f"{NPC}Vikka Three-Nails" in text, text
assert f"{EXIT}[ Exits ]" in text, text
assert f"{EXIT}NORTH" in text, text
assert "The Sorting Spine" in text, text
assert text.index("The Clattergate") < text.index("[ Notable ]") < text.index("[ People ]") < text.index("[ Exits ]")
assert server.PlayerSession._room_presentation_runtime_installed

with tempfile.TemporaryDirectory() as temp:
    database = Database(Path(temp) / "room-presentation.db")
    respawn_session = SimpleNamespace(
        character=SimpleNamespace(
            id=99,
            race="goblin",
            character_class="priest",
            level=1,
            current_room=GOBLIN_MUDGLASS_CROSSING_KEY,
        ),
        database=database,
        mobile_npcs=None,
    )

    before = "\r\n".join(render_room_lines(respawn_session, server.WORLD))
    assert "Mire Tick Swarm" in before, before
    assert "[ Danger ]" in before, before

    mark_static_enemy_defeated(
        database,
        GOBLIN_MUDGLASS_CROSSING_KEY,
        MIRE_TICK_SWARM.key,
        120.0,
    )
    during = "\r\n".join(render_room_lines(respawn_session, server.WORLD))
    assert "Mire Tick Swarm" not in during, during
    assert "[ Danger ]" not in during, during

    clear_static_enemy_respawn(
        database,
        GOBLIN_MUDGLASS_CROSSING_KEY,
        MIRE_TICK_SWARM.key,
    )
    after = "\r\n".join(render_room_lines(respawn_session, server.WORLD))
    assert "Mire Tick Swarm" in after, after
    assert "[ Danger ]" in after, after

print("ROOM_PRESENTATION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ROOM_PRESENTATION_OK", result.stdout)

    def test_palette_uses_distinct_semantic_colors(self):
        from mud.room_presentation import BUSINESS, ENEMY, EXIT, FEATURE, NPC, REGION, TITLE

        semantic_colors = {TITLE, REGION, FEATURE, NPC, ENEMY, EXIT, BUSINESS}
        self.assertEqual(len(semantic_colors), 7)
        for color in semantic_colors:
            self.assertTrue(color.startswith("\x1b["))
            self.assertTrue(color.endswith("m"))


if __name__ == "__main__":
    unittest.main()
