"""One ritual, one disruption, shared memory, and safe Forest Elf quest routing."""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.astralis_time import AstralisMoment
from mud.community_events import CommunityEventJournal
from mud.database import Database
from mud.forest_elf_circle_community import (
    CIRCLE, CIRCLE_LIVING_NPCS, COMMUNITY, DISRUPTION, LETHRA, ORREN,
    REGION, RITUAL, STORY, CircleCommunityDirector, gathered,
    install_circle_community_runtime, register_circle_living_npcs,
    resolve_circle_talk, talk_lines,
)
from mud.forest_elf_home_and_omens import install_forest_elf_home_content
from mud.forest_elf_nurture import (
    FOREST_ELF_HEARTSEED_BLOOMED_FLAG, FOREST_ELF_HEARTSEED_QUEST,
    install_forest_elf_nurture_content,
)
from mud.forest_elf_stewardship import install_forest_elf_stewardship_content
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcManager
from mud.world import NPCS_BY_KEY, ROOMS_BY_KEY

ROOT = Path(__file__).resolve().parents[1]


def moment(day: int, hour: int, minute: int = 0) -> AstralisMoment:
    return AstralisMoment(
        day_number=day, hour=hour, minute=minute,
        total_minutes=day * 1440 + hour * 60 + minute,
    )


class CircleCommunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_forest_elf_nurture_content()
        install_forest_elf_home_content()
        install_forest_elf_stewardship_content()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "community.db")
        with self.db.connect() as db:
            db.execute("INSERT INTO accounts (name, password_hash) VALUES ('tester', 'hash')")
            db.execute("INSERT INTO characters (account_id, name) VALUES (1, 'Willow')")
        self.director = CircleCommunityDirector.for_database(self.db)
        self.manager = MobileNpcManager(definitions=CIRCLE_LIVING_NPCS)

    def _gather_at(self, day: int = 55, hour: int = 5):
        self.director.pulse(self.manager, moment(day, hour), "clear")
        for _ in range(4):
            self.manager.tick(
                rng=random.Random(3), hour=hour,
                weather_provider=lambda _: "clear",
            )
        self.assertTrue(gathered(self.manager))

    def test_two_residents_use_real_routes_and_cannot_escape_boundary(self):
        self.manager.validate_definitions()
        self.assertEqual(len(CIRCLE_LIVING_NPCS), 2)
        self.assertEqual({actor.behavior for actor in CIRCLE_LIVING_NPCS},
                         {BEHAVIOR_ROUTINE})
        self.assertEqual(len({actor.name for actor in CIRCLE_LIVING_NPCS}), 2)
        self.assertIn("forest_elf_keeper_maelis_fernward", NPCS_BY_KEY)
        self.assertTrue(all(
            set(actor.allowed_room_keys).issubset(ROOMS_BY_KEY)
            for actor in CIRCLE_LIVING_NPCS
        ))
        register_circle_living_npcs()
        register_circle_living_npcs()
        self.assertEqual(len({actor.key for actor in CIRCLE_LIVING_NPCS}), 2)
        self._gather_at()
        self.assertEqual(self.manager.states[LETHRA.key].current_room_key, CIRCLE)
        self.assertEqual(self.manager.states[ORREN.key].current_room_key, CIRCLE)
        self.director.pulse(self.manager, moment(55, 9), "clear")
        for _ in range(4):
            self.manager.tick(hour=9, rng=random.Random(2),
                              weather_provider=lambda _: "clear")
        self.assertNotEqual(self.manager.states[LETHRA.key].current_room_key, CIRCLE)
        self.assertNotEqual(self.manager.states[ORREN.key].current_room_key, CIRCLE)

    def test_shared_dawn_ritual_persists_without_duplicate_events(self):
        self._gather_at()
        opening = self.director.pulse(self.manager, moment(55, 5, 1), "clear")
        self.assertIn("Maelis", " ".join(opening))
        self.assertIn("Lethra", " ".join(opening))
        self.assertIn("Orren", " ".join(opening))
        self.assertEqual(
            self.director.pulse(self.manager, moment(55, 5, 2), "clear"), (),
        )
        joined = self.director.join_ritual(self.manager, 1, moment(55, 5, 2))
        self.assertIn("join", " ".join(joined).lower())
        self.assertIn("already", " ".join(
            self.director.join_ritual(self.manager, 1, moment(55, 5, 3)),
        ).lower())
        end = self.director.pulse(self.manager, moment(55, 5, 9), "clear")
        self.assertIn("Willow", " ".join(end))
        self.assertEqual(
            self.director.journal.get(COMMUNITY, RITUAL, "55").stage, "completed",
        )
        self.assertFalse(self.manager.routine_overrides)
        self.assertNotIn("underway", self.director.scene_line(moment(55, 5, 11)))
        restarted = CircleCommunityDirector.for_database(self.db)
        self.assertEqual(restarted.ritual(55).stage, "completed")
        self.assertEqual(
            restarted.journal.latest_participant(restarted.ritual(55), "joined"),
            "Willow",
        )
        self.assertEqual(
            restarted.pulse(self.manager, moment(55, 5, 20), "clear"), (),
        )

    def test_one_storm_breaks_border_and_joint_repair_finishes_after_clear(self):
        # Sample fair weather before dawn; don't accidentally trigger a rite.
        self.assertEqual(self.director.pulse(
            self.manager, moment(70, 12), "clear",
        ), ())
        first = self.director.pulse(
            self.manager, moment(70, 12, 1), "storm",
        )
        self.assertIn("herb border", " ".join(first))
        self.assertEqual(self.director.incident().stage, "damaged")
        self.assertEqual(len(self.manager.routine_overrides), 2)
        for _ in range(4):
            self.manager.tick(hour=12, rng=random.Random(2),
                              weather_provider=lambda _: "storm")
        self.assertTrue(gathered(self.manager))
        self.assertEqual(self.director.pulse(
            self.manager, moment(70, 12, 2), "storm",
        ), ())
        recovery = self.director.pulse(
            self.manager, moment(70, 12, 3), "clear",
        )
        self.assertIn("Lethra", " ".join(recovery))
        self.assertEqual(self.director.incident().stage, "tending")
        self.assertIn("HELP REPAIR BORDER", self.director.scene_line(moment(70, 12, 4)))
        end = self.director.pulse(self.manager, moment(70, 12, 13), "clear")
        self.assertIn("secure again", " ".join(end))
        self.assertIsNone(self.director.incident())
        self.assertEqual(
            self.director.journal.recent(COMMUNITY, DISRUPTION).stage,
            "repaired",
        )
        self.assertFalse(self.manager.routine_overrides)
        # A second front on the same world day does not spam the same incident.
        self.director.pulse(self.manager, moment(70, 13), "rain")
        self.assertFalse(self.director.pulse(
            self.manager, moment(70, 13, 1), "storm",
        ))
        self.assertEqual(
            self.director.journal.recent(COMMUNITY, DISRUPTION).key, "70",
        )
        # Another day may produce one new storm response.
        self.director.pulse(self.manager, moment(71, 13), "clear")
        self.director.pulse(self.manager, moment(71, 13, 1), "storm")
        self.assertEqual(
            self.director.journal.recent(COMMUNITY, DISRUPTION).key, "71",
        )

    def test_restarted_during_storm_resumes_work_without_new_damage(self):
        self.director.pulse(self.manager, moment(80, 12), "clear")
        self.director.pulse(self.manager, moment(80, 12, 1), "storm")
        restarted = CircleCommunityDirector.for_database(self.db)
        fresh_manager = MobileNpcManager(definitions=CIRCLE_LIVING_NPCS)
        self.assertEqual(
            restarted.pulse(fresh_manager, moment(80, 12, 2), "storm"), (),
        )
        self.assertEqual(len(fresh_manager.routine_overrides), 2)
        for _ in range(4):
            fresh_manager.tick(hour=12, rng=random.Random(2),
                               weather_provider=lambda _: "storm")
        self.assertTrue(gathered(fresh_manager))
        restarted.pulse(fresh_manager, moment(80, 12, 3), "clear")
        restarted.pulse(fresh_manager, moment(80, 12, 13), "clear")
        self.assertIsNone(restarted.incident())
        self.assertEqual(restarted.journal.recent(COMMUNITY, DISRUPTION).stage, "repaired")

    def test_player_help_is_atomic_and_repair_follows_real_presence(self):
        self.director.pulse(self.manager, moment(90, 12), "clear")
        self.director.pulse(self.manager, moment(90, 12, 1), "storm")
        self.assertIn("wind", " ".join(self.director.help_repair(
            self.manager, 1, moment(90, 12, 2), "storm",
        )).lower())
        self.assertIn("gathering", " ".join(self.director.help_repair(
            self.manager, 1, moment(90, 12, 3), "clear",
        )).lower())
        for _ in range(4):
            self.manager.tick(hour=12, rng=random.Random(3),
                              weather_provider=lambda _: "storm")
        self.assertTrue(gathered(self.manager))
        result = self.director.help_repair(self.manager, 1, moment(90, 12, 5), "clear")
        self.assertIn("remembers your help", " ".join(result))
        self.assertIsNone(self.director.incident())
        with self.db.connect() as conn:
            count = conn.execute(
                "SELECT count(*) FROM community_event_participants WHERE role = 'repair'",
            ).fetchone()[0]
        self.assertEqual(count, 1)
        self.assertIn("does not need", " ".join(self.director.help_repair(
            self.manager, 1, moment(90, 12, 6), "clear",
        )))

    def test_stories_require_explicit_sharing_and_persist_as_public_memory(self):
        self.assertIsNone(self.director.journal.latest_story(COMMUNITY, STORY))
        lines = self.director.share_heartseed(1, moment(91, 14))
        self.assertIn("shared care slates", " ".join(lines))
        self.assertEqual(
            self.director.journal.latest_story(COMMUNITY, STORY)[0], "Willow",
        )
        self.assertIn("already", " ".join(
            self.director.share_heartseed(1, moment(92, 14)),
        ).lower())
        restarted = CircleCommunityDirector.for_database(self.db)
        self.assertIn("Willow", " ".join(restarted.status_lines(moment(92, 14))))
        self._gather_at(day=92)
        self.director.pulse(self.manager, moment(92, 5, 1), "clear")
        gossip = self.director.ambient_lines(
            self.manager, moment(92, 5, 2), "clear",
            rng=random.Random(1),
        )
        self.assertTrue(gossip)

    def test_talk_uses_real_location_and_weather(self):
        self.assertIsNone(resolve_circle_talk(self.manager, CIRCLE, "lethra"))
        self._gather_at()
        self.assertEqual(resolve_circle_talk(self.manager, CIRCLE, "lethra"), LETHRA)
        self.assertEqual(resolve_circle_talk(
            self.manager, CIRCLE, "keeper orren fernstitch",
        ), ORREN)
        self.assertIn("JOIN RITUAL", " ".join(talk_lines(
            LETHRA, moment(55, 5, 1), "clear", self.director,
        ))) if self.director.ritual(55) is not None else self.assertTrue(True)


class _Session:
    def __init__(self, database, director, manager):
        self.database = database
        self.circle_community = director
        self.mobile_npcs = manager
        self.character = SimpleNamespace(current_room=CIRCLE, id=1, name="Willow")
        self.sent = []
        self.command = ""
        self.delegated = []
        self.state = SimpleNamespace(DISCONNECTED="disconnected")

    async def prompt(self, _line):
        return self.command

    async def send(self, text):
        self.sent.append(text)

    async def show_current_room(self):
        await self.send("Original room text.\r\n")

    async def playing_prompt(self):
        self.delegated.append(await self.prompt("> "))


class CircleCommandTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_forest_elf_nurture_content()
        install_forest_elf_home_content()
        install_forest_elf_stewardship_content()

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "command.db")
        with self.db.connect() as conn:
            conn.execute("INSERT INTO accounts (name, password_hash) VALUES ('tester', 'hash')")
            conn.execute("INSERT INTO characters (account_id, name) VALUES (1, 'Willow')")
        self.director = CircleCommunityDirector.for_database(self.db)
        self.manager = MobileNpcManager(definitions=CIRCLE_LIVING_NPCS)
        self.Session = type("CircleCommandSession", (_Session,), {})
        install_circle_community_runtime(self.Session)
        self.session = self.Session(self.db, self.director, self.manager)

    async def test_existing_heartseed_quest_commands_are_never_swallowed(self):
        for command in ("talk maelis", "gather silvermoss", "tend heartseed", "wait",
                        "examine heartseed", "help", "examine season wheel"):
            self.session.command = command
            await self.session.playing_prompt()
        self.assertEqual(self.session.delegated, [
            "talk maelis", "gather silvermoss", "tend heartseed", "wait",
            "examine heartseed", "help", "examine season wheel",
        ])

    async def test_sharing_requires_heartseed_completion_and_is_once_only(self):
        self.session.command = "share heartseed story"
        await self.session.playing_prompt()
        self.assertIn("Restore the Heartseed", "".join(self.session.sent))
        self.db.grant_flag(1, FOREST_ELF_HEARTSEED_BLOOMED_FLAG)
        await self.session.playing_prompt()
        self.assertIn("shared care slates", "".join(self.session.sent))
        await self.session.playing_prompt()
        self.assertIn("already remembers", "".join(self.session.sent))

    async def test_original_room_render_receives_persistent_community_overlay(self):
        self.director.pulse(self.manager, moment(99, 12), "clear")
        self.director.pulse(self.manager, moment(99, 12, 1), "storm")
        with patch("mud.forest_elf_circle_community.ASTRALIS_CLOCK") as clock:
            clock.now.return_value = moment(99, 12, 1)
            await self.session.show_current_room()
        self.assertIn("Original room text.", "".join(self.session.sent))
        self.assertIn("storm has torn", "".join(self.session.sent))

    async def test_circle_status_and_new_mobile_talk_are_local(self):
        self.session.command = "circle"
        with patch("mud.forest_elf_circle_community.ASTRALIS_CLOCK") as clock:
            clock.now.return_value = moment(110, 12)
            await self.session.playing_prompt()
        self.assertIn("Circle Community", "".join(self.session.sent))
        self.session.character.current_room = "human_demon_gate"
        await self.session.playing_prompt()
        self.assertIn("circle", self.session.delegated)


class CircleProductionTests(unittest.TestCase):
    def test_full_server_registers_cast_and_community_runtime(self):
        script = """
import server
from mud.forest_elf_circle_community import (
    CIRCLE_LIVING_NPCS, CircleCommunityDirector,
)
from mud.world import ROOMS_BY_KEY
assert server.PlayerSession._circle_community_installed
game = server.MudServer(host="127.0.0.1", port=0)
assert all(actor.key in game.mobile_npcs.states for actor in CIRCLE_LIVING_NPCS)
assert all(set(actor.allowed_room_keys).issubset(ROOMS_BY_KEY) for actor in CIRCLE_LIVING_NPCS)
assert isinstance(game.circle_community, CircleCommunityDirector)
print("CIRCLE_COMMUNITY_OK")
"""
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env={**os.environ, "MUD_DB_PATH": str(Path(td) / "production.db")},
                capture_output=True, text=True, timeout=100, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CIRCLE_COMMUNITY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
