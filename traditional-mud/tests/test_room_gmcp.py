from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.room_gmcp import ROOM_PACKAGE, push_room_snapshot
from mud.telnet import GMCP, IAC, SB, SE, TelnetConnection


class FakeTelnet:
    def __init__(self):
        self.gmcp_enabled = True
        self.accept = True
        self.messages = []

    async def send_gmcp(self, package, payload):
        if not self.accept:
            return False
        self.messages.append((package, json.loads(json.dumps(payload))))
        return True


def room_data(room_id="waymeet_crossroads", *, players=None):
    return {
        "schema_version": 1,
        "id": room_id,
        "title": "Waymeet Crossroads",
        "description": "Four roads meet here.",
        "region_id": "waymeet_frontier",
        "region": "Waymeet Frontier",
        "notable": [],
        "people": [],
        "players": list(players or []),
        "creatures": [],
        "hostile": [],
        "on_ground": [],
        "corpses": [],
        "business": [],
        "exits": [{"direction": "north", "title": "The Fifth Lantern", "room_id": "the_fifth_lantern"}],
    }


class RoomGmcpUnitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = SimpleNamespace(
            character=SimpleNamespace(current_room="waymeet_crossroads"),
            telnet=FakeTelnet(),
        )

    async def test_complete_room_is_one_message_with_its_own_boundary(self):
        data = room_data()
        sent = await push_room_snapshot(self.session, None, room_data=data, force=True)
        self.assertTrue(sent)
        self.assertEqual(len(self.session.telnet.messages), 1)
        package, payload = self.session.telnet.messages[0]
        self.assertEqual(package, ROOM_PACKAGE)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["revision"], 1)
        self.assertEqual(payload["id"], "waymeet_crossroads")
        self.assertEqual(payload["exits"][0]["direction"], "north")
        self.assertEqual(payload["overlays"], [])
        self.assertNotIn("revision", data)  # renderer-owned dict is unchanged

    async def test_repeated_look_forces_snapshot_but_unmodified_poll_is_silent(self):
        data = room_data()
        await push_room_snapshot(self.session, None, room_data=data, force=True)
        await push_room_snapshot(self.session, None, room_data=data, force=True)
        self.assertEqual([m[1]["revision"] for m in self.session.telnet.messages], [1, 2])

        self.session._room_gmcp_next_check = 0
        with patch("mud.room_presentation.render_room_lines") as render:
            render.side_effect = lambda _s, _w, **kw: (kw["room_data"].update(data), ("visible",))[1]
            changed = await push_room_snapshot(self.session, None)
        self.assertFalse(changed)
        self.assertEqual(len(self.session.telnet.messages), 2)

    async def test_idle_poll_detects_other_players_activity_and_removal(self):
        current = room_data(players=[{"name": "Prime", "activity": "standing nearby"}])

        def render(_s, _w, **kw):
            kw["room_data"].update(current)
            self.assertFalse(kw["record_discovery"])
            return ("visible",)

        with patch("mud.room_presentation.render_room_lines", side_effect=render):
            self.assertTrue(await push_room_snapshot(self.session, None, force=True))
            self.session._room_gmcp_next_check = 0
            current = room_data(players=[{"name": "Prime", "activity": "resting"}])
            self.assertTrue(await push_room_snapshot(self.session, None))
            self.session._room_gmcp_next_check = 0
            current = room_data(players=[])
            self.assertTrue(await push_room_snapshot(self.session, None))
            self.session._room_gmcp_next_check = 0
            self.assertFalse(await push_room_snapshot(self.session, None))
        self.assertEqual([m[1]["revision"] for m in self.session.telnet.messages], [1, 2, 3])
        self.assertEqual(self.session.telnet.messages[-1][1]["players"], [])

    async def test_room_transition_resets_revision_and_never_sends_old_room(self):
        await push_room_snapshot(self.session, None, room_data=room_data(), force=True)
        self.session.character.current_room = "fifth_lantern"
        self.assertFalse(await push_room_snapshot(
            self.session, None, room_data=room_data("waymeet_crossroads"), force=True,
        ))
        self.assertTrue(await push_room_snapshot(
            self.session, None, room_data=room_data("fifth_lantern"), force=True,
        ))
        self.assertEqual([m[1]["revision"] for m in self.session.telnet.messages], [1, 1])

    async def test_overlays_are_plain_text_and_remain_across_dynamic_refresh(self):
        data = room_data()
        await push_room_snapshot(
            self.session, None, room_data=data,
            overlays=["\x1b[96mThe rain grows colder.\x1b[0m\r\n"], force=True,
        )
        self.assertEqual(
            self.session.telnet.messages[0][1]["overlays"], ["The rain grows colder."]
        )
        self.session._room_gmcp_next_check = 0
        data["people"] = [{"name": "Valline", "description": "checking her ledger"}]
        await push_room_snapshot(self.session, None, room_data=data)
        self.assertEqual(
            self.session.telnet.messages[-1][1]["overlays"], ["The rain grows colder."]
        )

    async def test_non_gmcp_and_rejected_packets_do_not_update_cache(self):
        self.session.telnet.gmcp_enabled = False
        self.assertFalse(await push_room_snapshot(
            self.session, None, room_data=room_data(), force=True,
        ))
        self.session.telnet.gmcp_enabled = True
        self.session.telnet.accept = False
        self.assertFalse(await push_room_snapshot(
            self.session, None, room_data=room_data(), force=True,
        ))
        self.assertIsNone(getattr(self.session, "_room_gmcp_last_snapshot", None))
        self.session.telnet.accept = True
        self.assertTrue(await push_room_snapshot(
            self.session, None, room_data=room_data(), force=True,
        ))
        self.assertEqual(self.session.telnet.messages[0][1]["revision"], 1)


class _MemoryWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        return None


class RoomGmcpFramingTests(unittest.IsolatedAsyncioTestCase):
    async def test_telnet_gmcp_frame_contains_one_json_object_and_end_marker(self):
        writer = _MemoryWriter()
        connection = TelnetConnection(asyncio.StreamReader(), writer)
        connection.gmcp_enabled = True
        await connection.send_gmcp(ROOM_PACKAGE, room_data())
        raw = bytes(writer.data)
        start = bytes((IAC, SB, GMCP))
        end = bytes((IAC, SE))
        self.assertTrue(raw.startswith(start))
        self.assertTrue(raw.endswith(end))
        self.assertEqual(raw.count(start), 1)
        self.assertEqual(raw.count(end), 1)
        package, body = raw[len(start):-len(end)].split(b" ", 1)
        self.assertEqual(package, b"Dreams.Room")
        self.assertEqual(json.loads(body)["id"], "waymeet_crossroads")


class ProductionRoomGmcpTests(unittest.TestCase):
    def test_live_room_renderer_and_gmcp_share_one_snapshot(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import json
from types import SimpleNamespace
from unittest.mock import patch
import server
from mud.room_presentation import render_room_lines
from mud.waymeet_frontier import WAYMEET_TAVERN_KEY

class DB:
    def list_flags(self, _character_id):
        return []

session = SimpleNamespace(
    character=SimpleNamespace(
        id=1, name="Prime", race="goblin", character_class="priest",
        level=6, current_room=WAYMEET_TAVERN_KEY,
    ),
    database=DB(), mobile_npcs=None, _movement_resting=True,
)
data = {}
with patch("mud.room_presentation.record_room_view") as discovery:
    with patch("mud.room_presentation.record_actor_discovery") as actors:
        text = "\r\n".join(render_room_lines(
            session, server.WORLD, room_data=data, record_discovery=False,
        ))
        discovery.assert_not_called()
        actors.assert_not_called()

assert data["schema_version"] == 1
assert data["id"] == WAYMEET_TAVERN_KEY
assert data["title"] in text
assert data["region"] in text
assert data["description"].split("\n")[0] in text
assert data["notable"] and data["people"]
assert data["exits"] and all("room_id" in entry for entry in data["exits"])
assert data["players"][0]["name"] == "Prime"
assert data["players"][0]["is_self"]
assert data["players"][0]["activity"] == "resting beside the gearwheel hearth"
assert "[ Players ]" in text
assert "[ Exits ]" in text
assert server.PlayerSession._room_gmcp_runtime_installed
json.dumps(data)
print("ROOM_GMCP_PRODUCTION_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=root, text=True,
            capture_output=True, timeout=90, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ROOM_GMCP_PRODUCTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
