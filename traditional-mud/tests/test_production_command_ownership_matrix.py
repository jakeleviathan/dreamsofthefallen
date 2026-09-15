from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductionCommandOwnershipMatrixTests(unittest.TestCase):
    def test_fully_assembled_player_session_preserves_command_owners(self) -> None:
        # Run the real production entrypoint in a subprocess so its installer stack
        # cannot leak global registry mutations into neighboring unit tests.
        code = r'''
import asyncio
import tempfile
from pathlib import Path

import server
from mud.database import Database
from mud.sporekin_depth import SPOREKIN_MEMORY_PATH_ROOM_KEY
from mud.waymeet_frontier import WAYMEET_CROSSROADS_KEY

assert server.PlayerSession._command_collision_policy_installed
assert server.PlayerSession._canonical_command_help_installed
assert server.PlayerSession._final_command_telemetry_installed

MATRIX = (
    # race, class, room, command, required owner/presentation marker
    ("sporekin", "wizard", SPOREKIN_MEMORY_PATH_ROOM_KEY, "guide", "The Discipline of Guidance"),
    ("human", "priest", WAYMEET_CROSSROADS_KEY, "guide", "--- Command Guide ---"),
    ("human", "brute", WAYMEET_CROSSROADS_KEY, "frontier", "Waymeet is the first shared level 2-5 region"),
    ("goblin", "priest", "goblin_clattergate", "commands", "Categories: basics, character, combat"),
    ("human", "priest", WAYMEET_CROSSROADS_KEY, "help", "The same command catalog powers HELP and COMMANDS"),
    ("human", "brute", WAYMEET_CROSSROADS_KEY, "sit", "You settle down and rest"),
)


async def run_case(index, race, class_name, room_key, command, marker):
    with tempfile.TemporaryDirectory() as tmp:
        database = Database(Path(tmp) / "mud.db")
        account = database.create_account(f"matrix_{index}", "not-a-real-hash")
        character = database.create_character(
            account.id,
            f"Matrix{index}",
            race,
            class_name,
        )
        database.set_character_room(character.id, room_key)
        character = database.get_character_by_name(character.name)
        assert character is not None

        # Use the fully assembled production class, but bypass transport setup so
        # the matrix stays deterministic and has no socket/telnet side effects.
        session = object.__new__(server.PlayerSession)
        session.database = database
        session.character = character
        session.active_enemy = None
        session.combatant = None
        session.current_opponent = None
        session._movement_resting = False
        output = []

        async def prompt(_text):
            return command

        async def send(text):
            output.append(text)

        async def send_client_state():
            return None

        session.prompt = prompt
        session.send = send
        session.send_client_state = send_client_state

        await session.playing_prompt()
        text = "".join(output)
        assert marker in text, (race, class_name, room_key, command, text)

        # #69's outer telemetry must still see every command in this matrix,
        # including commands that intentionally short-circuit in outer owners.
        with database.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) FROM alpha_ux_events WHERE character_id=? AND event_key='command'",
                (character.id,),
            ).fetchone()
        assert row is not None and int(row[0]) == 1, (command, row)


async def main():
    for index, case in enumerate(MATRIX, start=1):
        await run_case(index, *case)


asyncio.run(main())
print("PRODUCTION_COMMAND_OWNERSHIP_MATRIX_OK", len(MATRIX))
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PRODUCTION_COMMAND_OWNERSHIP_MATRIX_OK 6", result.stdout)


if __name__ == "__main__":
    unittest.main()
