from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


class LiveTelnetSessionConstructionTests(unittest.TestCase):
    def test_production_player_session_constructs_with_slotted_telnet_connection(self) -> None:
        """Regression for the live-only crash seen when Mudlet connected.

        Importing the production entrypoint installs the full authored world and
        mutates process-global registries. Run this regression in a child Python
        process so those production boot side effects cannot contaminate the
        rest of the unit-test suite.
        """

        script = textwrap.dedent(
            r"""
            import asyncio
            import tempfile
            from pathlib import Path

            import server
            from mud.database import Database


            class Writer:
                def __init__(self) -> None:
                    self.data = bytearray()

                def get_extra_info(self, name: str):
                    if name == "peername":
                        return ("127.0.0.1", 40000)
                    return None

                def write(self, data: bytes) -> None:
                    self.data.extend(data)

                async def drain(self) -> None:
                    return None


            async def main() -> None:
                with tempfile.TemporaryDirectory() as tmp:
                    database = Database(Path(tmp) / "mud.db")
                    reader = asyncio.StreamReader()
                    writer = Writer()

                    session = server.PlayerSession(reader, writer, database)

                    assert session.telnet.gmcp_send_allowed is not None
                    assert session._dotf_preference_gmcp_policy is True

                    session.telnet.gmcp_enabled = True

                    sent = await session.telnet.send_gmcp(
                        "Char.Status", {"name": "Probe"}
                    )
                    assert sent is True
                    assert len(writer.data) > 0

                    session._mudlet_enhancements_enabled = False
                    before = len(writer.data)
                    sent = await session.telnet.send_gmcp(
                        "Char.Status", {"name": "Blocked"}
                    )
                    assert sent is False
                    assert len(writer.data) == before


            asyncio.run(main())
            """
        )

        mud_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=mud_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "Production PlayerSession construction failed in isolated process.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
