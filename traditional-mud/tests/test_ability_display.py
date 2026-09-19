from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import mud.ability_mastery as mastery


ROOT = Path(__file__).resolve().parents[1]


class MasteryDisplayMathTests(unittest.TestCase):
    def test_progress_bar_is_progress_within_current_skill_level(self):
        state = mastery.MasteryProgress(
            ability_key="blessing_of_resolve",
            uses=4,
            skill_xp=4,
            level=3,
            band="Novice",
            next_level_xp=6,
        )
        earned, needed = mastery.mastery_level_progress(state)
        self.assertEqual((earned, needed), (1, 3))
        bar = mastery.mastery_progress_bar(state, width=12)
        self.assertTrue(bar.startswith("["))
        self.assertTrue(bar.endswith("]"))
        self.assertIn("█", bar)
        self.assertIn("░", bar)

    def test_next_mastery_band_is_the_next_named_milestone(self):
        self.assertEqual(mastery.next_mastery_band(3), (10, "Practiced"))
        self.assertEqual(mastery.next_mastery_band(10), (25, "Skilled"))
        self.assertIsNone(mastery.next_mastery_band(100))


class ProductionAbilityDisplayTests(unittest.TestCase):
    def test_skills_abilities_and_detail_have_distinct_player_facing_jobs(self):
        code = r"""
import asyncio
import re
import tempfile
from pathlib import Path

import server
import mud.class_progression as class_progression
import mud.session as session_module
from mud.database import Database

ANSI = re.compile(r"\x1b\[[0-9;]*m")

with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "display.db")
    account = db.create_account("display_test", "x")
    character = db.create_character(account.id, "DisplayPriest", "goblin", "priest")
    with db.connect() as conn:
        conn.execute(
            "UPDATE characters SET level = 4, deity_key = 'zerjz' WHERE id = ?",
            (character.id,),
        )
    character = db.get_character_by_name("DisplayPriest")

    for _ in range(4):
        db.record_ability_use(character.id, "blessing_of_resolve", skill_xp_gain=1)
    db.record_ability_use(character.id, "restoring_light", skill_xp_gain=1)

    class Session:
        def __init__(self):
            self.database = db
            self.character = character
            self.outputs = []
        async def send(self, text):
            self.outputs.append(text)

    session = Session()

    asyncio.run(session_module._show_mastery_skills(session))
    skills = ANSI.sub("", "".join(session.outputs))
    assert "PRIEST SKILLS" in skills
    assert "Blessing of Resolve" in skills
    assert "Restoring Light" in skills
    assert "blessing_of_resolve" not in skills
    assert "Novice" in skills
    assert "Skill 3 / 100" in skills
    assert "1 / 3 XP" in skills
    assert "Uses     4" in skills
    assert "NEXT CLASS ABILITIES" in skills
    assert "Lv 5" in skills and "Resurrection" in skills
    assert "Lv 6" in skills and "Purifying Light" in skills
    assert "Lv 7" in skills and "Prayer of Renewal" in skills
    assert "Abundant Grace" not in skills

    session.outputs.clear()
    asyncio.run(session_module._show_unlocked_abilities(session))
    available = ANSI.sub("", "".join(session.outputs))
    assert "PRIEST ABILITIES" in available
    assert "Restoring Light" in available
    assert "Blessing of Resolve" in available
    assert "Greater Mend" in available
    assert "Cast 1s" in available
    assert "Cast 2s" in available
    assert "Resurrection" not in available
    assert "ABILITIES ALL" in available

    session.outputs.clear()
    asyncio.run(session_module._show_all_abilities(session))
    all_abilities = ANSI.sub("", "".join(session.outputs))
    assert "PRIEST ABILITY PROGRESSION" in all_abilities
    assert "Resurrection" in all_abilities
    assert "Abundant Grace" in all_abilities
    assert "LOCKED" in all_abilities
    assert "UNLOCKED" in all_abilities

    session.outputs.clear()
    asyncio.run(class_progression._show_ability_detail(session, "restoring light"))
    detail = ANSI.sub("", "".join(session.outputs))
    assert "Ability Detail" in detail
    assert "Restoring Light" in detail
    assert "Novice" in detail
    assert "Skill 2 / 100" in detail
    assert "0 / 2 XP toward Skill 3" in detail
    assert "Current Mastery Effects" in detail
    assert "Healing power:" in detail
    assert "Mana cost:" in detail
    assert "Next Milestone: Practiced at Skill 10" in detail

print("ABILITY_DISPLAY_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ABILITY_DISPLAY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
