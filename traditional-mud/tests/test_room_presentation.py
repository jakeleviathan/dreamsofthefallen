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
from mud.corpse_loot import create_corpse
from mud.database import Database
from mud.enemy_lifecycle import clear_static_enemy_respawn, mark_static_enemy_defeated
from mud.goblin_swamp import GOBLIN_MUDGLASS_CROSSING_KEY, MIRE_TICK_SWARM
from mud.room_presentation import (
    BUSINESS,
    CORPSE,
    CREATURE,
    ENEMY,
    EXIT,
    HOSTILE,
    FEATURE,
    NPC,
    REGION,
    TITLE,
    render_room_lines,
)
from mud.stats import CharacterStats
from mud.waymeet_adventure_arc import CELLAR_RAT, TOLL_RAT_RUN

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
    account = database.create_account("roompresentation", "hash")
    owner = database.create_character(
        account.id,
        "RoomPresentation",
        "goblin",
        "priest",
        CharacterStats(might=5, grace=5, love=5, mind=5, hp=5),
    )
    respawn_session = SimpleNamespace(
        character=SimpleNamespace(
            id=owner.id,
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
    assert f"{CREATURE}[ Creatures ]" in before, before
    assert "[ Danger ]" not in before, before
    assert "[ Hostile ]" not in before, before
    assert "[ Corpses ]" not in before, before

    mark_static_enemy_defeated(
        database,
        GOBLIN_MUDGLASS_CROSSING_KEY,
        MIRE_TICK_SWARM.key,
        120.0,
    )
    create_corpse(
        database,
        GOBLIN_MUDGLASS_CROSSING_KEY,
        MIRE_TICK_SWARM.key,
        MIRE_TICK_SWARM.name,
        owner_character_id=owner.id,
        death_key="room-presentation:mire-tick",
    )
    during = "\r\n".join(render_room_lines(respawn_session, server.WORLD))
    assert "[ Creatures ]" not in during, during
    assert "[ Danger ]" not in during, during
    assert f"{CORPSE}[ Corpses ]" in during, during
    assert f"{CORPSE}Corpse of Mire Tick Swarm (fresh)" in during, during
    assert during.index("[ Corpses ]") < during.index("[ Exits ]"), during

    clear_static_enemy_respawn(
        database,
        GOBLIN_MUDGLASS_CROSSING_KEY,
        MIRE_TICK_SWARM.key,
    )
    after = "\r\n".join(render_room_lines(respawn_session, server.WORLD))
    assert "Mire Tick Swarm" in after, after
    assert "[ Creatures ]" in after, after
    assert "[ Danger ]" not in after, after
    assert "[ Corpses ]" in after, after

    duplicate_session = SimpleNamespace(
        character=SimpleNamespace(
            id=owner.id,
            race="goblin",
            character_class="priest",
            level=6,
            current_room=TOLL_RAT_RUN,
        ),
        database=database,
        mobile_npcs=None,
    )
    duplicate_before = "\r\n".join(render_room_lines(duplicate_session, server.WORLD))
    assert "Cellar Rat x2" not in duplicate_before, duplicate_before
    assert duplicate_before.count(f"{CREATURE}Cellar Rat") == 2, duplicate_before

    mark_static_enemy_defeated(
        database,
        TOLL_RAT_RUN,
        CELLAR_RAT.key,
        120.0,
    )
    duplicate_after_one = "\r\n".join(render_room_lines(duplicate_session, server.WORLD))
    assert "Cellar Rat x2" not in duplicate_after_one, duplicate_after_one
    assert duplicate_after_one.count(f"{CREATURE}Cellar Rat") == 1, duplicate_after_one

# Attackable-but-passive mobiles are creatures; only explicit auto-aggro
# definitions are labeled Hostile.
class FakeMobiles:
    def __init__(self, aggressive):
        self.aggressive = aggressive

    def npcs_in_room(self, _room_key):
        definition = SimpleNamespace(
            name="Test Hunter" if self.aggressive else "Test Grazer",
            short_description=(
                "a predator already watching you"
                if self.aggressive
                else "a wary animal that keeps its distance"
            ),
            aggressive=self.aggressive,
            attackable=True,
        )
        return (SimpleNamespace(definition=definition),)

classification_session = SimpleNamespace(
    character=SimpleNamespace(
        id=1,
        race="goblin",
        character_class="priest",
        level=1,
        current_room="goblin_clattergate",
    ),
    database=DB(),
    mobile_npcs=FakeMobiles(False),
)
passive = "\r\n".join(render_room_lines(classification_session, server.WORLD))
assert f"{CREATURE}[ Creatures ]" in passive, passive
assert "Test Grazer" in passive, passive
assert "[ Hostile ]" not in passive, passive

classification_session.mobile_npcs = FakeMobiles(True)
hostile = "\r\n".join(render_room_lines(classification_session, server.WORLD))
assert f"{HOSTILE}[ Hostile ]" in hostile, hostile
assert "Test Hunter" in hostile, hostile
assert "[ Creatures ]" not in hostile, hostile
assert "[ Danger ]" not in hostile, hostile

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
        from mud.room_presentation import (
            BUSINESS,
            CORPSE,
            CREATURE,
            ENEMY,
            EXIT,
            FEATURE,
            HOSTILE,
            NPC,
            REGION,
            TITLE,
        )

        semantic_colors = {
            TITLE,
            REGION,
            FEATURE,
            NPC,
            CREATURE,
            HOSTILE,
            CORPSE,
            EXIT,
            BUSINESS,
        }
        self.assertEqual(len(semantic_colors), 9)
        self.assertEqual(ENEMY, HOSTILE)
        for color in semantic_colors:
            self.assertTrue(color.startswith("\x1b["))
            self.assertTrue(color.endswith("m"))


if __name__ == "__main__":
    unittest.main()
