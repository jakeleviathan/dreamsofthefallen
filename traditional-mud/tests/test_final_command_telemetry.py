from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import mud.alpha_ux as alpha
from mud.database import Database
from mud.final_command_telemetry import install_final_command_telemetry


ROOT = Path(__file__).resolve().parents[1]


class _Runtime:
    def __init__(self, database, character) -> None:
        self.database = database
        self.character = character
        self.active_enemy = None
        self.messages: list[str] = []
        self.next_command = ""

    async def prompt(self, _text: str):
        return self.next_command

    async def send(self, text: str) -> None:
        self.messages.append(text)

    async def playing_prompt(self) -> None:
        command = await self.prompt("\r\n> ")
        if command == "look":
            before = alpha._state_snapshot(self)
            await self.send("You look around.\r\n")
            after = alpha._state_snapshot(self)
            alpha._observe_transition(self, command, before, after, 1)
            return
        # Simulate a command handled by a production wrapper installed outside
        # alpha_ux: it performs its action but emits no telemetry itself.
        await self.send(f"outer:{command}\r\n")


class FinalCommandTelemetryTests(unittest.TestCase):
    def _runtime(self, root: Path):
        db = Database(root / "mud.db")
        account = db.create_account("telemetry_account", "hash")
        character = db.create_character(account.id, "Telemetryhero", "human", "wizard")
        runtime = _Runtime(db, character)
        install_final_command_telemetry(type(runtime))
        return runtime

    def test_outer_command_families_are_backfilled_once(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self._runtime(Path(temp))
            commands = (
                "map",
                "movement",
                "rest",
                "inspect rat",
                "item iron sword",
                "perception",
                "harvest glassroot",
            )
            for command in commands:
                runtime.next_command = command
                asyncio.run(runtime.playing_prompt())

            with runtime.database.connect() as db:
                rows = db.execute(
                    "SELECT command_verb FROM alpha_ux_events WHERE event_key='command' ORDER BY id"
                ).fetchall()
            self.assertEqual(
                [row["command_verb"] for row in rows],
                ["map", "movement", "rest", "inspect", "item", "perception", "harvest"],
            )

    def test_command_already_counted_by_inner_alpha_layer_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self._runtime(Path(temp))
            runtime.next_command = "look"
            asyncio.run(runtime.playing_prompt())
            with runtime.database.connect() as db:
                count = db.execute(
                    "SELECT COUNT(*) FROM alpha_ux_events WHERE event_key='command' AND command_verb='look'"
                ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_backfill_still_stores_only_the_command_family(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self._runtime(Path(temp))
            runtime.next_command = "inspect private-looking-target-name"
            asyncio.run(runtime.playing_prompt())
            with runtime.database.connect() as db:
                row = db.execute(
                    "SELECT command_verb, details FROM alpha_ux_events WHERE event_key='command' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertEqual(row["command_verb"], "inspect")
            self.assertNotIn("private-looking-target-name", row["details"])


class ProductionFinalCommandTelemetryTests(unittest.TestCase):
    def test_production_entrypoint_installs_final_command_telemetry_outer_runtime(self):
        code = r'''
import server
assert server.PlayerSession._alpha_ux_runtime_installed
assert server.PlayerSession._final_command_telemetry_installed
assert server.PlayerSession._runtime_remediation_installed
print("FINAL_COMMAND_TELEMETRY_OK")
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
        self.assertIn("FINAL_COMMAND_TELEMETRY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
