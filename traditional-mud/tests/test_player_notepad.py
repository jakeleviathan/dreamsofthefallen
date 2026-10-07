import asyncio
import tempfile
import unittest
from pathlib import Path

import mud.player_notepad as notes
from mud.database import Database


class _Session:
    def __init__(self, database, character):
        self.database = database
        self.character = character
        self.outputs = []
        self._notepad_interaction = None

    async def send(self, text):
        self.outputs.append(text)


class PlayerNotepadTests(unittest.TestCase):
    def make_world(self):
        temp = tempfile.TemporaryDirectory()
        database = Database(Path(temp.name) / "notepad.db")
        account_a = database.create_account("notes_a", "x")
        account_b = database.create_account("notes_b", "x")
        alice = database.create_character(account_a.id, "AliceNotes", "human", "brute")
        bob = database.create_character(account_b.id, "BobNotes", "goblin", "priest")
        return temp, database, alice, bob

    def test_multiline_note_is_persistent_and_private_to_character(self):
        temp, database, alice, bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)

        asyncio.run(notes._begin_new_note(session, "King's Scar"))
        asyncio.run(notes._handle_notepad_interaction(session, "Brake lever is in the winch chamber."))
        asyncio.run(notes._handle_notepad_interaction(session, "Breaker pit is east after the bridge."))
        asyncio.run(notes._handle_notepad_interaction(session, "."))

        with database.connect() as db:
            row = db.execute(
                "SELECT id, title, body FROM character_notes WHERE character_id = ?",
                (alice.id,),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "King's Scar")
        self.assertEqual(
            row["body"],
            "Brake lever is in the winch chamber.\nBreaker pit is east after the bridge.",
        )

        bob_session = _Session(database, bob)
        self.assertIsNone(notes._get_note(bob_session, int(row["id"])))
        self.assertFalse(
            notes._update_note(bob_session, int(row["id"]), "Stolen", "Nope")
        )
        self.assertFalse(notes._delete_note(bob_session, int(row["id"])))

    def test_editing_supports_line_changes_title_changes_and_append(self):
        temp, database, alice, _bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)
        note_id = notes._create_note(session, "Route", "north\neast\nsouth")

        asyncio.run(notes._begin_edit_note(session, note_id))
        asyncio.run(notes._handle_notepad_interaction(session, "/set 2 west"))
        asyncio.run(notes._handle_notepad_interaction(session, "/insert 3 down"))
        asyncio.run(notes._handle_notepad_interaction(session, "/delete 1"))
        asyncio.run(notes._handle_notepad_interaction(session, "/title Toll Route"))
        asyncio.run(notes._handle_notepad_interaction(session, "search wall"))
        asyncio.run(notes._handle_notepad_interaction(session, "."))

        row = notes._get_note(session, note_id)
        self.assertEqual(row["title"], "Toll Route")
        self.assertEqual(row["body"], "west\ndown\nsouth\nsearch wall")
        self.assertIsNone(session._notepad_interaction)

    def test_delete_requires_confirmation_and_can_be_canceled(self):
        temp, database, alice, _bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)
        note_id = notes._create_note(session, "Keep me", "Important")

        asyncio.run(notes._begin_delete_note(session, note_id))
        asyncio.run(notes._handle_notepad_interaction(session, "no"))
        self.assertIsNotNone(notes._get_note(session, note_id))

        asyncio.run(notes._begin_delete_note(session, note_id))
        asyncio.run(notes._handle_notepad_interaction(session, "yes"))
        self.assertIsNone(notes._get_note(session, note_id))
        self.assertIn("deleted", "".join(session.outputs).lower())

    def test_new_note_without_title_uses_title_stage_then_body(self):
        temp, database, alice, _bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)

        asyncio.run(notes._begin_new_note(session, ""))
        self.assertEqual(session._notepad_interaction["stage"], "title")
        asyncio.run(notes._handle_notepad_interaction(session, "Alchemy Shopping"))
        self.assertEqual(session._notepad_interaction["stage"], "body")
        asyncio.run(notes._handle_notepad_interaction(session, "coal"))
        asyncio.run(notes._handle_notepad_interaction(session, "greenleaf"))
        asyncio.run(notes._handle_notepad_interaction(session, "."))

        rows = notes._note_rows(session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Alchemy Shopping")

    def test_cancel_discards_unsaved_new_note(self):
        temp, database, alice, _bob = self.make_world()
        self.addCleanup(temp.cleanup)
        session = _Session(database, alice)

        asyncio.run(notes._begin_new_note(session, "Temporary"))
        asyncio.run(notes._handle_notepad_interaction(session, "do not save"))
        asyncio.run(notes._handle_notepad_interaction(session, "/cancel"))

        self.assertEqual(notes._note_count(session), 0)
        self.assertIsNone(session._notepad_interaction)


if __name__ == "__main__":
    unittest.main()
