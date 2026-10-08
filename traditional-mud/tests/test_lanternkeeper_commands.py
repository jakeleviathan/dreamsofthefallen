"""In-game Lanternkeeper discover, subscribe, status and manage integration."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_runtime import (
    ensure_schema, install_lanternkeeper_runtime,
)


class LanternkeeperGameCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "game.sqlite3")
        ensure_schema(self.db)
        with self.db.connect() as db:
            db.execute(
                "INSERT INTO accounts(name,password_hash) VALUES ('tester','hash')"
            )
            db.execute(
                "INSERT INTO characters(account_id,name,current_room) "
                "VALUES (1,'LanternTest','waymeet_crossroads')"
            )
        self.env = patch.dict(os.environ, {
            "DOTF_LANTERNKEEPER_LINKS_ENABLED": "1",
            "DOTF_BILLING_ORIGIN": "https://mud.lvthn.io",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

        class Session:
            async def playing_prompt(self):
                self.delegated = True

            async def prompt(self, _text):
                return self.command

            async def send(self, message):
                self.messages.append(message)

            def __init__(self, db, command):
                self.database = db
                self.character = SimpleNamespace(id=1, account_id=1)
                self.command = command
                self.messages = []
                self.delegated = False

        install_lanternkeeper_runtime(Session)
        self.session_class = Session

    async def run_command(self, command):
        session = self.session_class(self.db, command)
        await session.playing_prompt()
        return session

    async def test_info_explains_price_cosmetics_and_payment_safety(self):
        session = await self.run_command("LANTERNKEEPER")
        output = "".join(session.messages)
        self.assertIn("$4.99", output)
        self.assertIn("cosmetic only", output)
        self.assertIn("LANTERNKEEPER SUBSCRIBE", output)
        self.assertIn("browser", output)

    async def test_subscribe_command_issues_private_browser_url(self):
        session = await self.run_command("LANTERNKEEPER SUBSCRIBE")
        output = "".join(session.messages)
        self.assertIn("https://mud.lvthn.io/lanternkeeper/confirm?ticket=", output)
        self.assertIn("expires in 10 minutes", output)

    async def test_manage_requires_billing_customer(self):
        session = await self.run_command("LANTERNKEEPER MANAGE")
        self.assertIn("No linked billing account", "".join(session.messages))
        with self.db.connect() as db:
            db.execute(
                "INSERT INTO lanternkeeper_memberships "
                "(account_id,stripe_customer_id,stripe_subscription_id,stripe_status) "
                "VALUES (1,'cus_game_test','sub_game_test','active')"
            )
        session = await self.run_command("LANTERNKEEPER MANAGE")
        self.assertIn("/lanternkeeper/confirm?ticket=", "".join(session.messages))

    async def test_existing_subscription_cannot_start_new_checkout(self):
        with self.db.connect() as db:
            db.execute(
                "INSERT INTO lanternkeeper_memberships "
                "(account_id,stripe_customer_id,stripe_subscription_id,stripe_status) "
                "VALUES (1,'cus_game_test','sub_game_test','active')"
            )
        session = await self.run_command("LANTERNKEEPER BUY")
        self.assertIn("already have a Lanternkeeper subscription", "".join(session.messages))

    async def test_issuing_links_is_disabled_until_billing_is_approved(self):
        with patch.dict(os.environ, {"DOTF_LANTERNKEEPER_LINKS_ENABLED": "0"}):
            session = await self.run_command("LANTERNKEEPER SUBSCRIBE")
            self.assertIn("not open yet", "".join(session.messages))
            session = await self.run_command("LANTERNKEEPER INFO")
            self.assertIn("not open yet", "".join(session.messages))

    async def test_unrelated_commands_reach_existing_game_handler(self):
        session = await self.run_command("LOOK")
        self.assertTrue(session.delegated)
        self.assertEqual(session.messages, [])


if __name__ == "__main__":
    unittest.main()
