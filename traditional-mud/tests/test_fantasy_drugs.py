from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.fantasy_drugs import (
    DRUGS,
    DRUG_ITEMS,
    ECHO_WELL_KEY,
    INTERVAL_GALLERY,
    INTERVAL_ROOMS,
    INTERVAL_THRESHOLD,
    active_perception_name,
    install_perception_runtime,
    interval_exits,
    interval_view,
)


ROOT = Path(__file__).resolve().parents[1]


class _World:
    def __init__(self):
        self.legacy_rooms = {}
        self._scene_cache = {}


class _Database:
    def __init__(self):
        self.items = {}
        self.flags = set()
        self.room = ECHO_WELL_KEY

    def item_quantity(self, _character_id, item_key):
        return self.items.get(item_key, 0)

    def add_item(self, _character_id, item_key, quantity=1):
        self.items[item_key] = self.items.get(item_key, 0) + quantity

    def consume_item(self, _character_id, item_key, quantity=1):
        current = self.items.get(item_key, 0)
        if current < quantity:
            return False
        remaining = current - quantity
        if remaining:
            self.items[item_key] = remaining
        else:
            self.items.pop(item_key, None)
        return True

    def set_character_room(self, _character_id, room_key):
        self.room = room_key

    def grant_flag(self, _character_id, flag):
        self.flags.add(flag)

    def list_flags(self, _character_id):
        return frozenset(self.flags)


class _Telnet:
    def __init__(self):
        self.gmcp_enabled = True
        self.packets = []

    async def send_gmcp(self, package, payload):
        self.packets.append((package, payload))
        return True


class _Session:
    def __init__(self):
        self.database = _Database()
        self.character = SimpleNamespace(
            id=1,
            level=17,
            current_room=ECHO_WELL_KEY,
            race="human",
            character_class="wizard",
        )
        self.active_enemy = None
        self.telnet = _Telnet()
        self.messages = []
        self.next_command = ""
        self.state = SimpleNamespace(DISCONNECTED="disconnected")

    async def send(self, text):
        self.messages.append(text)

    async def prompt(self, _text):
        return self.next_command

    async def enter_character(self):
        return None

    async def show_current_room(self):
        self.messages.append("BASE ROOM\r\n")

    async def move_character(self, _direction):
        return None

    async def send_client_state(self):
        return None

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.messages.append(f"DELEGATED:{command}\r\n")


class PerceptionDesignTests(unittest.TestCase):
    def test_recreational_items_have_no_stat_or_normal_consumable_effects(self):
        self.assertEqual(len(DRUGS), 4)
        self.assertEqual(len(DRUG_ITEMS), 4)
        for item in DRUG_ITEMS:
            self.assertEqual(item.category, "recreational")
            self.assertIsNone(item.equipment)
            self.assertIsNone(item.consumable)
            self.assertNotIn("Basic", item.name)
            self.assertNotIn("Generic", item.name)

    def test_same_interval_rooms_are_tuned_differently_by_drug(self):
        moon_title, moon_text = interval_view("moonwake", INTERVAL_GALLERY)
        choir_title, choir_text = interval_view("choircap", INTERVAL_GALLERY)
        self.assertNotEqual(moon_title, choir_title)
        self.assertNotEqual(moon_text, choir_text)
        self.assertEqual(interval_exits("moonwake", INTERVAL_THRESHOLD)[0][0], "later")
        self.assertEqual(interval_exits("choircap", INTERVAL_THRESHOLD)[0][0], "with")
        self.assertEqual(interval_exits("blue_emberleaf", INTERVAL_THRESHOLD)[0][0], "bright")
        self.assertEqual(interval_exits("hushglass", INTERVAL_THRESHOLD)[0][0], "inward")


class PerceptionRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.Session = type("PerceptionSession", (_Session,), {})
        self.world = _World()
        install_perception_runtime(self.Session, self.world)

    async def test_using_recreational_substance_consumes_one_and_alters_only_perception(self):
        session = self.Session()
        session.database.add_item(1, "recreational_moonwake_resin", 1)
        session.next_command = "use moonwake resin"
        await session.playing_prompt()
        self.assertEqual(session.database.item_quantity(1, "recreational_moonwake_resin"), 0)
        self.assertEqual(active_perception_name(session), "Moonwake Resin")
        text = "".join(session.messages)
        self.assertIn("core game state remains authoritative", text)
        self.assertIn("INWARD", text)

    async def test_sober_player_cannot_enter_drug_only_dimension(self):
        session = self.Session()
        session.next_command = "inward"
        await session.playing_prompt()
        self.assertEqual(session.character.current_room, ECHO_WELL_KEY)
        self.assertIn("sober perception cannot find it", "".join(session.messages))

    async def test_altered_player_enters_shared_interval_and_uses_drug_specific_direction(self):
        session = self.Session()
        session.database.add_item(1, "recreational_choircap_spores", 1)
        session.next_command = "inhale choircap spores"
        await session.playing_prompt()
        session.next_command = "inward"
        await session.playing_prompt()
        self.assertEqual(session.character.current_room, INTERVAL_THRESHOLD)
        self.assertIn("perception_discovered_veiled_interval", session.database.flags)

        session.next_command = "with"
        await session.playing_prompt()
        self.assertEqual(session.character.current_room, INTERVAL_GALLERY)
        rendered = "".join(session.messages)
        self.assertIn("Hall of Borrowed Selves", rendered)

    async def test_reconnect_inside_interval_repairs_location_to_echo_well(self):
        session = self.Session()
        session.character.current_room = INTERVAL_GALLERY
        session.database.room = INTERVAL_GALLERY
        await session.enter_character()
        self.assertEqual(session.character.current_room, ECHO_WELL_KEY)
        self.assertEqual(session.database.room, ECHO_WELL_KEY)
        self.assertIn("return to consciousness", "".join(session.messages))

    async def test_source_does_not_allow_free_stockpiling(self):
        from mud.goblin_start import GOBLIN_BRASSGUT_MARKET_KEY

        session = self.Session()
        session.character.current_room = GOBLIN_BRASSGUT_MARKET_KEY
        session.next_command = "ask for emberleaf"
        await session.playing_prompt()
        self.assertEqual(session.database.item_quantity(1, "recreational_blue_emberleaf"), 1)
        await session.playing_prompt()
        self.assertEqual(session.database.item_quantity(1, "recreational_blue_emberleaf"), 1)

    async def test_gmcp_exposes_altered_state_without_overwriting_core_state(self):
        session = self.Session()
        session.database.add_item(1, "recreational_hushglass_tincture", 1)
        session.next_command = "drink hushglass"
        await session.playing_prompt()
        await session.send_client_state()
        packets = [payload for package, payload in session.telnet.packets if package == "Dreams.Perception"]
        self.assertTrue(packets)
        self.assertTrue(packets[-1]["altered"])
        self.assertEqual(packets[-1]["effect"], "hushglass")


class ProductionPerceptionContractTests(unittest.TestCase):
    def test_production_server_installs_perception_layer_and_shared_dimension(self):
        code = r'''
import server
import mud.crafting as crafting
from mud.fantasy_drugs import INTERVAL_ROOMS, DRUG_ITEMS

assert server.PlayerSession._perception_runtime_installed
for room_key in INTERVAL_ROOMS:
    assert server.WORLD.scene(room_key) is not None, room_key
for item in DRUG_ITEMS:
    live = crafting.ITEMS_BY_KEY[item.key]
    assert live.name == item.name
    assert live.equipment is None
    assert live.consumable is None
print("PERCEPTION_LAYER_OK")
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
        self.assertIn("PERCEPTION_LAYER_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
