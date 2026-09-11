from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.equipment_system import set_equipped_item
from mud.trade_experience import install_trade_experience_runtime, reset_trade_runtime_state


class FakeState:
    DISCONNECTED = "disconnected"


class BaseSession:
    def __init__(self, database, character, commands=None):
        self.database = database
        self.character = character
        self.commands = list(commands or ())
        self.outputs: list[str] = []
        self.state = FakeState()
        self.active_enemy = None

    async def send(self, text: str):
        self.outputs.append(text)

    async def prompt(self, _text: str):
        if not self.commands:
            return None
        return self.commands.pop(0)

    async def enter_character(self):
        return None

    async def close(self):
        return None

    async def playing_prompt(self):
        command = await self.prompt("> ")
        if command is None:
            return
        if command.strip().lower() == "north":
            self.database.set_character_room(self.character.id, "human_ashen_way")
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed
            await self.send("You move north.\r\n")
            return
        await self.send(f"BASE: {command}\r\n")


def trade_session_type():
    class Session(BaseSession):
        pass

    install_trade_experience_runtime(Session)
    return Session


class TradeExperienceTests(unittest.TestCase):
    def setUp(self):
        reset_trade_runtime_state()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        alice_account = self.db.create_account("aliceaccount", "hash")
        bob_account = self.db.create_account("bobaccount", "hash")
        self.alice_character = self.db.create_character(alice_account.id, "Alice", "human", "wizard")
        self.bob_character = self.db.create_character(bob_account.id, "Bob", "dwarf", "brute")
        self.db.set_character_room(self.alice_character.id, "human_demon_gate")
        self.db.set_character_room(self.bob_character.id, "human_demon_gate")
        self.alice_character = self.db.get_character_by_name("Alice")
        self.bob_character = self.db.get_character_by_name("Bob")

    def tearDown(self):
        reset_trade_runtime_state()
        self.tempdir.cleanup()

    def _pair(self, alice_commands=None, bob_commands=None):
        Session = trade_session_type()
        alice = Session(self.db, self.alice_character, alice_commands)
        bob = Session(self.db, self.bob_character, bob_commands)
        asyncio.run(alice.enter_character())
        asyncio.run(bob.enter_character())
        return alice, bob

    def test_give_moves_positive_quantity_and_rejects_quest_items(self):
        self.db.add_item(self.alice_character.id, "iron_ore", 3)
        self.db.add_item(self.alice_character.id, "sealed_cathedral_note", 1)
        alice, bob = self._pair(
            ["give Bob 2 iron ore", "give Bob sealed cathedral note"],
            [],
        )

        asyncio.run(alice.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.alice_character.id, "iron_ore"), 1)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "iron_ore"), 2)
        self.assertIn("Alice gives you 2x Iron Ore", "".join(bob.outputs))

        asyncio.run(alice.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.alice_character.id, "sealed_cathedral_note"), 1)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "sealed_cathedral_note"), 0)
        self.assertIn("quest item", "".join(alice.outputs).lower())

    def test_equipped_items_must_be_unequipped_before_transfer(self):
        if self.db.item_quantity(self.alice_character.id, "starter_weapon") <= 0:
            self.db.add_item(self.alice_character.id, "starter_weapon", 1)
        set_equipped_item(self.db, self.alice_character.id, "main_hand", "starter_weapon")
        alice, _bob = self._pair(["give Bob basic starting weapon"], [])

        asyncio.run(alice.playing_prompt())

        self.assertGreater(self.db.item_quantity(self.alice_character.id, "starter_weapon"), 0)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "starter_weapon"), 0)
        self.assertIn("unequip", "".join(alice.outputs).lower())

    def test_two_party_trade_commits_both_offers_atomically(self):
        self.db.add_item(self.alice_character.id, "iron_ore", 2)
        self.db.add_item(self.bob_character.id, "raw_cotton", 3)
        alice, bob = self._pair(
            ["trade Bob", "trade add 2 iron ore", "trade confirm"],
            ["trade accept", "trade add 3 raw cotton", "trade confirm"],
        )

        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.alice_character.id, "iron_ore"), 0)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "iron_ore"), 2)
        self.assertEqual(self.db.item_quantity(self.alice_character.id, "raw_cotton"), 3)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "raw_cotton"), 0)
        self.assertIn("Trade complete", "".join(alice.outputs))
        self.assertIn("Trade complete", "".join(bob.outputs))

    def test_offer_change_resets_confirmation(self):
        self.db.add_item(self.alice_character.id, "iron_ore", 1)
        self.db.add_item(self.bob_character.id, "raw_cotton", 1)
        alice, bob = self._pair(
            ["trade Bob", "trade add iron ore", "trade confirm", "trade confirm"],
            ["trade accept", "trade add raw cotton", "trade confirm"],
        )

        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        asyncio.run(alice.playing_prompt())
        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        self.assertIn("confirmations were reset", "".join(bob.outputs).lower())

        asyncio.run(bob.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.alice_character.id, "iron_ore"), 1)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "raw_cotton"), 1)

        asyncio.run(alice.playing_prompt())
        self.assertEqual(self.db.item_quantity(self.alice_character.id, "raw_cotton"), 1)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "iron_ore"), 1)

    def test_moving_away_cancels_trade_without_moving_items(self):
        self.db.add_item(self.alice_character.id, "iron_ore", 1)
        alice, bob = self._pair(
            ["trade Bob", "trade add iron ore", "north"],
            ["trade accept"],
        )

        asyncio.run(alice.playing_prompt())
        asyncio.run(bob.playing_prompt())
        asyncio.run(alice.playing_prompt())
        asyncio.run(alice.playing_prompt())

        self.assertEqual(self.db.item_quantity(self.alice_character.id, "iron_ore"), 1)
        self.assertEqual(self.db.item_quantity(self.bob_character.id, "iron_ore"), 0)
        self.assertIn("moved away", "".join(bob.outputs).lower())


if __name__ == "__main__":
    unittest.main()
