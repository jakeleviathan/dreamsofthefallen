from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import mud.room_runtime as room_runtime
from mud.room_presentation import _legacy_room_overlays, _remove_contiguous_subsequence


ROOT = Path(__file__).resolve().parents[1]


class _Session:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


class RoomPresentationCompositionTests(unittest.IsolatedAsyncioTestCase):
    def test_core_subsequence_can_be_removed_without_losing_surrounding_overlays(self):
        full = ["before\r\n", "core a\r\n", "core b\r\n", "after\r\n"]
        core = ["core a\r\n", "core b\r\n"]
        self.assertEqual(
            _remove_contiguous_subsequence(full, core),
            ["before\r\n", "after\r\n"],
        )

    def test_unmatched_core_fails_closed_instead_of_printing_duplicate_room(self):
        self.assertEqual(
            _remove_contiguous_subsequence(["different\r\n"], ["core\r\n"]),
            [],
        )

    async def test_legacy_chain_preserves_only_pre_and_post_core_overlays(self):
        session = _Session()

        async def fake_core(current_session, _fallback) -> None:
            await current_session.send("legacy title\r\n")
            await current_session.send("legacy description\r\n")

        async def old_chain(current_session) -> None:
            await current_session.send("pre-core authored overlay\r\n")
            await room_runtime._render_current_room(current_session, lambda _s: None)
            await current_session.send("Gloam Surge warning\r\n")
            await current_session.send("Floodpick status\r\n")

        with patch.object(room_runtime, "_render_current_room", new=fake_core):
            overlays = await _legacy_room_overlays(session, old_chain)

        self.assertEqual(
            overlays,
            [
                "pre-core authored overlay\r\n",
                "Gloam Surge warning\r\n",
                "Floodpick status\r\n",
            ],
        )
        self.assertEqual(session.messages, [])


class ProductionRoomCompositionTests(unittest.TestCase):
    def test_production_entrypoint_keeps_final_semantic_renderer(self):
        code = r'''
import server
assert server.PlayerSession._room_presentation_runtime_installed
print("ROOM_COMPOSITION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ROOM_COMPOSITION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
