import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.living_world as living
import mud.player_mail as post
import mud.social_experience as social
from mud.database import Database


class _Session:
    def __init__(self, database, character, prompts=None):
        self.database = database
        self.character = character
        self.outputs = []
        self._prompts = list(prompts or [])

    async def send(self, text):
        self.outputs.append(text)

    async def prompt(self, _text):
        if not self._prompts:
            return None
        return self._prompts.pop(0)


class PlayerMailTests(unittest.TestCase):
    def make_world(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "mail.db")
        a = database.create_account("mail_a", "x")
        b = database.create_account("mail_b", "x")
        alice = database.create_character(a.id, "AlicePost", "human", "brute")
        bob = database.create_character(b.id, "BobPost", "goblin", "priest")
        return temp, database, alice, bob

    def test_schema_upgrade_preserves_world_mail_and_removes_old_subject_uniqueness(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        living.ensure_living_world_schema(database)
        with database.connect() as db:
            db.execute(
                """
                INSERT INTO living_mail
                    (character_id, astralis_day, sender, subject, body)
                VALUES (?, 7, 'Waymeet Road Post', 'Road news', 'Old road letter')
                """,
                (bob.id,),
            )

        post.ensure_player_mail_schema(database)
        with database.connect() as db:
            sql = db.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'living_mail'"
            ).fetchone()["sql"]
            columns = {
                row["name"] for row in db.execute("PRAGMA table_info(living_mail)").fetchall()
            }
            row = db.execute(
                "SELECT sender, subject, body, mail_type, is_deleted FROM living_mail"
            ).fetchone()

        self.assertNotIn("UNIQUE(character_id, astralis_day, subject)", sql)
        self.assertTrue({"mail_type", "sender_character_id", "is_deleted", "deleted_at"} <= columns)
        self.assertEqual(row["subject"], "Road news")
        self.assertEqual(row["mail_type"], "world")
        self.assertEqual(int(row["is_deleted"]), 0)

    def test_player_mail_is_persistent_offline_and_same_subject_can_repeat(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)
        recipient = post.MailRecipient(bob.id, bob.name)

        first = post._store_player_mail(session, recipient, "Meet me", "At the bridge.")
        second = post._store_player_mail(session, recipient, "Meet me", "Actually, the market.")

        self.assertNotEqual(first, second)
        with database.connect() as db:
            rows = db.execute(
                """
                SELECT sender, sender_character_id, subject, body, mail_type
                FROM living_mail
                WHERE character_id = ?
                ORDER BY id
                """,
                (bob.id,),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["mail_type"] == "player" for row in rows))
        self.assertTrue(all(int(row["sender_character_id"]) == alice.id for row in rows))
        self.assertEqual(rows[0]["sender"], alice.name)

    def test_compose_uses_multiline_editor_and_delivers_to_offline_character(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(
            database,
            alice,
            prompts=["A road question", "Did you see the caravan?", "I can meet tomorrow.", "."],
        )

        asyncio.run(post._compose_mail(session, bob.name))

        with database.connect() as db:
            row = db.execute(
                "SELECT subject, body, mail_type FROM living_mail WHERE character_id = ?",
                (bob.id,),
            ).fetchone()
        self.assertEqual(row["subject"], "A road question")
        self.assertEqual(row["body"], "Did you see the caravan?\nI can meet tomorrow.")
        self.assertEqual(row["mail_type"], "player")
        self.assertIn("Letter sent to BobPost.", "".join(session.outputs))

    def test_ignore_list_blocks_player_mail_before_composition(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice, prompts=["should never be consumed"])
        social._ensure_schema(database)
        with database.connect() as db:
            db.execute(
                """
                INSERT INTO character_ignores (character_id, ignored_character_id)
                VALUES (?, ?)
                """,
                (bob.id, alice.id),
            )

        asyncio.run(post._compose_mail(session, bob.name))

        with database.connect() as db:
            count = db.execute(
                "SELECT COUNT(*) AS n FROM living_mail WHERE character_id = ?",
                (bob.id,),
            ).fetchone()["n"]
        self.assertEqual(int(count), 0)
        self.assertIn("not accepting messages", "".join(session.outputs))
        self.assertEqual(session._prompts, ["should never be consumed"])

    def test_lightweight_burst_rate_limit_applies_to_sent_player_mail(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)
        recipient = post.MailRecipient(bob.id, bob.name)
        for number in range(post.MAIL_BURST_LIMIT):
            post._store_player_mail(session, recipient, f"Note {number}", "Body")

        error = post._rate_limit_error(session, alice.id)

        self.assertIsNotNone(error)
        self.assertIn("slow down", error.lower())

    def test_mail_listing_labels_world_and_player_messages_and_marks_unread(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        post.ensure_player_mail_schema(database)
        with database.connect() as db:
            db.execute(
                """
                INSERT INTO living_mail
                    (character_id, astralis_day, sender, subject, body, mail_type)
                VALUES (?, 2, 'Waymeet Road Post', 'World note', 'roads changed', 'world')
                """,
                (bob.id,),
            )
        post._store_player_mail(_Session(database, alice), post.MailRecipient(bob.id, bob.name), "Hello", "Hi.")
        session = _Session(database, bob)

        asyncio.run(post._show_mail(session))
        output = "".join(session.outputs)

        self.assertIn("* [WORLD]", output)
        self.assertIn("* [PLAYER]", output)
        self.assertIn("MAIL SEND <player>", output)

    def test_read_delete_and_unread_count_respect_soft_delete(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        sender_session = _Session(database, alice)
        mail_id = post._store_player_mail(
            sender_session,
            post.MailRecipient(bob.id, bob.name),
            "Private note",
            "Body",
        )
        recipient_session = _Session(database, bob)
        self.assertEqual(post._unread_count(recipient_session), 1)

        asyncio.run(post._read_mail(recipient_session, mail_id))
        self.assertEqual(post._unread_count(recipient_session), 0)
        asyncio.run(post._delete_mail(recipient_session, mail_id))

        with database.connect() as db:
            row = db.execute(
                "SELECT is_read, is_deleted, deleted_at FROM living_mail WHERE id = ?",
                (mail_id,),
            ).fetchone()
        self.assertEqual(int(row["is_read"]), 1)
        self.assertEqual(int(row["is_deleted"]), 1)
        self.assertIsNotNone(row["deleted_at"])
        self.assertEqual(post._mail_rows(recipient_session), [])

    def test_clear_read_keeps_unread_then_clear_all_removes_remaining(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        sender = _Session(database, alice)
        recipient = post.MailRecipient(bob.id, bob.name)
        read_id = post._store_player_mail(sender, recipient, "Read one", "Body")
        unread_id = post._store_player_mail(sender, recipient, "Unread one", "Body")
        bob_session = _Session(database, bob)
        asyncio.run(post._read_mail(bob_session, read_id))

        bob_session._prompts = ["yes"]
        asyncio.run(post._clear_mail(bob_session, read_only=True))
        with database.connect() as db:
            read_row = db.execute("SELECT is_deleted FROM living_mail WHERE id = ?", (read_id,)).fetchone()
            unread_row = db.execute("SELECT is_deleted FROM living_mail WHERE id = ?", (unread_id,)).fetchone()
        self.assertEqual(int(read_row["is_deleted"]), 1)
        self.assertEqual(int(unread_row["is_deleted"]), 0)
        self.assertEqual(post._unread_count(bob_session), 1)

        bob_session._prompts = ["yes"]
        asyncio.run(post._clear_mail(bob_session, read_only=False))
        self.assertEqual(post._mail_rows(bob_session), [])
        self.assertEqual(post._unread_count(bob_session), 0)

    def test_bulk_clear_requires_confirmation(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        sender = _Session(database, alice)
        mail_id = post._store_player_mail(sender, post.MailRecipient(bob.id, bob.name), "Keep me", "Body")
        bob_session = _Session(database, bob, prompts=["no"])

        asyncio.run(post._clear_mail(bob_session, read_only=False))

        with database.connect() as db:
            row = db.execute("SELECT is_deleted FROM living_mail WHERE id = ?", (mail_id,)).fetchone()
        self.assertEqual(int(row["is_deleted"]), 0)
        self.assertIn("canceled", "".join(bob_session.outputs).lower())


class ProductionPlayerMailTests(unittest.TestCase):
    def test_production_installs_player_mail_and_catalogs_controls(self):
        import server
        import mud.command_guide as guide

        self.assertTrue(server.PlayerSession._player_mail_runtime_installed)
        syntaxes = {entry.syntax for entry in guide.COMMANDS}
        self.assertIn("MAIL / POST / INBOX", syntaxes)
        self.assertIn("MAIL SEND [TO] <player>", syntaxes)
        self.assertIn("MAIL DELETE <number>", syntaxes)
        self.assertIn("MAIL CLEAR READ / MAIL CLEAR ALL", syntaxes)


if __name__ == "__main__":
    unittest.main()
