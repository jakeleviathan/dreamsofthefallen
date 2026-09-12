from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mud.database import Database
from mud.dwarf_start import DWARF_FIRST_OBLIGATION_FLAG, DWARF_UPPER_FREIGHT_KEY
from mud.goblin_rattlefen_opening import RATTLEFEN_OPENING_COMPLETE_FLAG
from mud.goblin_start import GOBLIN_TINKER_ROW_KEY
from mud.human_blackwall_opening import HUMAN_GATE_CLEARANCE_FLAG, HUMAN_OUTER_CARAVAN_ROAD_KEY
from mud.moon_elf_city import MOON_ELF_SKYCOURT_KEY
from mud.moon_elf_third_chair import MOON_ELF_CHOICE_WIND_FLAG, MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.starter_signature_moments import (
    DWARF_SIGNATURE_BRAKE_CHECKED_FLAG,
    DWARF_SIGNATURE_COMPLETE_FLAG,
    GOBLIN_REED_LURE_KEY,
    GOBLIN_SIGNATURE_APPRAISED_FLAG,
    GOBLIN_SIGNATURE_LURE_FLAG,
    HUMAN_SIGNATURE_COMPLETE_FLAG,
    HUMAN_SIGNATURE_WAGON_READ_FLAG,
    MOON_SIGNATURE_COMPLETE_FLAG,
    SIGNATURE_MOMENTS,
    SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG,
    SPOREKIN_SIGNATURE_COMPLETE_FLAG,
    SPOREKIN_SIGNATURE_ECHO_FLAG,
    SPOREKIN_SIGNATURE_STONE_FLAG,
    TROLL_SIGNATURE_COMPLETE_FLAG,
    TROLL_SIGNATURE_DRIFT_READ_FLAG,
    TROLL_SIGNATURE_STUMBLED_FLAG,
    UNDEAD_SIGNATURE_BELL_HEARD_FLAG,
    UNDEAD_SIGNATURE_COMPLETE_FLAG,
    _echo_sporekin_choice_if_ready,
    _handle_dwarf,
    _handle_goblin,
    _handle_human,
    _handle_moon_elf,
    _handle_sporekin,
    _handle_troll,
    _handle_undead,
    install_signature_moment_content,
    signature_moment_augmentations,
)
from mud.troll_start import TROLL_COLD_COMPLETE_FLAG, TROLL_STONEJAW_PASS_KEY
from mud.undead_start import UNDEAD_DESERT_GATE_KEY, UNDEAD_ORDERS_SEVERED_FLAG
from mud.world import SPOREKIN_MEMORY_PATH_ROOM_KEY, SPOREKIN_SURFACE_VERGE_ROOM_KEY


class _Session:
    def __init__(self, database: Database, character) -> None:
        self.database = database
        self.character = character
        self.combatant = SimpleNamespace(current_movement=10)
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def refresh(self) -> None:
        current = self.database.get_character_by_name(self.character.name)
        assert current is not None
        self.character = current

    def text(self) -> str:
        return "".join(self.sent)


class StarterSignatureMomentTests(unittest.TestCase):
    def setUp(self) -> None:
        install_signature_moment_content()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        self.accounts = {}

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def session_for(self, race: str, room_key: str, name: str) -> _Session:
        account = self.db.create_account(f"acct_{name.lower()}", "hash")
        character = self.db.create_character(account.id, name, race, "wizard")
        self.db.set_character_room(character.id, room_key)
        character = self.db.get_character_by_name(name)
        assert character is not None
        return _Session(self.db, character)

    def flags(self, session: _Session) -> set[str]:
        return set(self.db.list_flags(session.character.id))

    def test_signature_layer_covers_every_non_forest_launch_race_once(self) -> None:
        self.assertEqual(
            set(SIGNATURE_MOMENTS),
            {"human", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin"},
        )
        rooms = {data["room"] for data in SIGNATURE_MOMENTS.values()}
        self.assertEqual(len(rooms), 7)
        self.assertNotIn("forest_elf", SIGNATURE_MOMENTS)

        augmentations = signature_moment_augmentations()
        for data in SIGNATURE_MOMENTS.values():
            self.assertIn(data["room"], augmentations)
            self.assertTrue(augmentations[data["room"]].features)

    def test_human_outsider_changes_language_after_practical_help(self) -> None:
        session = self.session_for("human", HUMAN_OUTER_CARAVAN_ROAD_KEY, "Cinder")
        self.db.grant_flag(session.character.id, HUMAN_GATE_CLEARANCE_FLAG)

        self.assertTrue(asyncio.run(_handle_human(session, "read wagon")))
        self.assertIn(HUMAN_SIGNATURE_WAGON_READ_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_human(session, "set chock")))
        self.assertIn(HUMAN_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        self.assertIn("Thanks, Cinder", session.text())
        self.assertIn("Demon never gets finished", session.text())

    def test_moon_elf_choice_returns_as_provisional_civic_result(self) -> None:
        session = self.session_for("moon_elf", MOON_ELF_SKYCOURT_KEY, "Vale")
        self.db.grant_flag(session.character.id, MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG)
        self.db.grant_flag(session.character.id, MOON_ELF_CHOICE_WIND_FLAG)

        self.assertTrue(asyncio.run(_handle_moon_elf(session, "read result")))
        self.assertIn(MOON_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        output = session.text().lower()
        self.assertIn("wind ribbons", output)
        self.assertIn("no seal", output)
        self.assertIn("correct", output)

    def test_dwarf_marks_suspect_equipment_out_of_service_instead_of_forcing_it(self) -> None:
        session = self.session_for("dwarf", DWARF_UPPER_FREIGHT_KEY, "Brass")
        self.db.grant_flag(session.character.id, DWARF_FIRST_OBLIGATION_FLAG)

        self.assertTrue(asyncio.run(_handle_dwarf(session, "force brake")))
        self.assertNotIn(DWARF_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_dwarf(session, "check brake")))
        self.assertIn(DWARF_SIGNATURE_BRAKE_CHECKED_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_dwarf(session, "tag brake")))
        self.assertIn(DWARF_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        self.assertIn("out of service", session.text().lower())

    def test_goblin_turns_same_bad_part_into_a_chosen_new_use(self) -> None:
        session = self.session_for("goblin", GOBLIN_TINKER_ROW_KEY, "Rivet")
        self.db.grant_flag(session.character.id, RATTLEFEN_OPENING_COMPLETE_FLAG)

        self.assertTrue(asyncio.run(_handle_goblin(session, "appraise scrap")))
        self.assertIn(GOBLIN_SIGNATURE_APPRAISED_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_goblin(session, "make lure")))
        self.assertIn(GOBLIN_SIGNATURE_LURE_FLAG, self.flags(session))
        self.assertEqual(self.db.item_quantity(session.character.id, GOBLIN_REED_LURE_KEY), 1)
        self.assertIn("different future", session.text().lower())

    def test_troll_can_learn_the_expensive_way_but_still_finishes_by_reading_land(self) -> None:
        session = self.session_for("troll", TROLL_STONEJAW_PASS_KEY, "Rime")
        self.db.grant_flag(session.character.id, TROLL_COLD_COMPLETE_FLAG)

        self.assertTrue(asyncio.run(_handle_troll(session, "cross drift")))
        self.assertIn(TROLL_SIGNATURE_STUMBLED_FLAG, self.flags(session))
        self.assertIn(TROLL_SIGNATURE_DRIFT_READ_FLAG, self.flags(session))
        self.assertEqual(session.combatant.current_movement, 8)

        self.assertTrue(asyncio.run(_handle_troll(session, "take lee route")))
        self.assertIn(TROLL_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        self.assertIn("longer", session.text().lower())

    def test_undead_old_reflex_has_no_authority_after_severance(self) -> None:
        session = self.session_for("undead", UNDEAD_DESERT_GATE_KEY, "Ashbone")
        self.db.grant_flag(session.character.id, UNDEAD_ORDERS_SEVERED_FLAG)

        self.assertTrue(asyncio.run(_handle_undead(session, "listen bell")))
        self.assertIn(UNDEAD_SIGNATURE_BELL_HEARD_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_undead(session, "lower hand")))
        self.assertIn(UNDEAD_SIGNATURE_COMPLETE_FLAG, self.flags(session))
        self.assertIn("because you decided", session.text().lower())

    def test_sporekin_gets_no_consensus_and_personal_choice_becomes_shared_memory_later(self) -> None:
        session = self.session_for("sporekin", SPOREKIN_SURFACE_VERGE_ROOM_KEY, "Morrowcap")
        self.db.grant_flag(session.character.id, "sporekin_first_call_answered")

        self.assertTrue(asyncio.run(_handle_sporekin(session, "listen chorus")))
        self.assertIn(SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG, self.flags(session))
        self.assertTrue(asyncio.run(_handle_sporekin(session, "choose stone")))
        flags = self.flags(session)
        self.assertIn(SPOREKIN_SIGNATURE_STONE_FLAG, flags)
        self.assertIn(SPOREKIN_SIGNATURE_COMPLETE_FLAG, flags)
        self.assertIn("supplies no preference", session.text().lower())

        self.db.set_character_room(session.character.id, SPOREKIN_MEMORY_PATH_ROOM_KEY)
        session.refresh()
        self.assertTrue(asyncio.run(_echo_sporekin_choice_if_ready(session)))
        self.assertIn(SPOREKIN_SIGNATURE_ECHO_FLAG, self.flags(session))
        self.assertIn("something one sporekin chose", session.text().lower())


if __name__ == "__main__":
    unittest.main()
