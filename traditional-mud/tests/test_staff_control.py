from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.npcs import MobileNpcManager
from mud.staff_control import (
    _ACTIVE_SESSIONS,
    _ensure_schema,
    _role_for,
    install_staff_control_runtime,
)


class FakeState:
    DISCONNECTED = "disconnected"


class BaseSession:
    def __init__(self, database, account, character, mobile_npcs=None, commands=None):
        self.database = database
        self.account = account
        self.character = character
        self.mobile_npcs = mobile_npcs or MobileNpcManager()
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
        await self.send("ENTERED\r\n")

    async def close(self):
        return None

    async def playing_prompt(self):
        command = await self.prompt("> ")
        if command is not None:
            await self.send(f"BASE: {command}\r\n")

    async def show_current_room(self):
        await self.send(f"ROOM: {self.character.current_room}\r\n")

    async def _stop_combat(self):
        return None

    def current_prompt_text(self):
        return "> "


def session_type():
    class Session(BaseSession):
        pass

    install_staff_control_runtime(Session)
    return Session


class StaffControlTests(unittest.TestCase):
    def setUp(self):
        _ACTIVE_SESSIONS.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mud.db")
        _ensure_schema(self.db)
        self.gm_account = self.db.create_account("gmaccount", "hash")
        self.player_account = self.db.create_account("playeraccount", "hash")
        self.helper_account = self.db.create_account("helperaccount", "hash")
        self.gm_character = self.db.create_character(self.gm_account.id, "Galen", "human", "wizard")
        self.player_character = self.db.create_character(self.player_account.id, "Mira", "human", "druid")
        self.helper_character = self.db.create_character(self.helper_account.id, "Teren", "human", "priest")
        with self.db.connect() as db:
            db.execute("INSERT INTO staff_roles (account_id, role) VALUES (?, 'gm')", (self.gm_account.id,))
            db.execute("INSERT INTO staff_roles (account_id, role) VALUES (?, 'helper')", (self.helper_account.id,))

    def tearDown(self):
        _ACTIVE_SESSIONS.clear()
        self.tempdir.cleanup()

    def _session(self, account, character, commands=None, manager=None):
        Session = session_type()
        return Session(self.db, account, character, mobile_npcs=manager, commands=commands)

    def test_player_cannot_enable_staff_mode(self):
        session = self._session(self.player_account, self.player_character, ["staff on"])
        asyncio.run(session.enter_character())
        session.outputs.clear()
        asyncio.run(session.playing_prompt())
        self.assertIn("does not have staff access", "".join(session.outputs))
        self.assertFalse(getattr(session, "_staff_mode", False))

    def test_helper_dashboard_and_player_card_are_observation_only(self):
        helper = self._session(self.helper_account, self.helper_character, ["staff on", "gm", "gm Mira"])
        player = self._session(self.player_account, self.player_character)
        asyncio.run(helper.enter_character())
        asyncio.run(player.enter_character())
        helper.outputs.clear()

        asyncio.run(helper.playing_prompt())
        asyncio.run(helper.playing_prompt())
        asyncio.run(helper.playing_prompt())
        output = "".join(helper.outputs)
        self.assertIn("Staff Console", output)
        self.assertIn("Mira", output)
        self.assertIn("GM: Mira", output)
        self.assertIn("A Summons to the Cathedral", output)

    def test_bring_requires_confirmation_and_persists_room(self):
        manager = MobileNpcManager()
        gm = self._session(self.gm_account, self.gm_character, ["staff on", "gm bring Mira", "confirm"], manager)
        player = self._session(self.player_account, self.player_character, manager=manager)
        self.db.set_character_room(gm.character.id, "human_cathedral_square")
        gm.character = self.db.get_character_by_name("Galen")
        asyncio.run(gm.enter_character())
        asyncio.run(player.enter_character())
        gm.outputs.clear()
        player.outputs.clear()

        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        self.assertEqual(player.character.current_room, "human_demon_gate")
        self.assertIn("Confirmation required", "".join(gm.outputs))
        asyncio.run(gm.playing_prompt())
        self.assertEqual(player.character.current_room, "human_cathedral_square")
        persisted = self.db.get_character_by_name("Mira")
        self.assertEqual(persisted.current_room, "human_cathedral_square")
        self.assertIn("A GM has relocated you", "".join(player.outputs))

    def test_safe_quest_reset_only_rewinds_journal_step(self):
        with self.db.connect() as db:
            db.execute(
                "UPDATE character_quests SET current_step = 'find_cathedral' WHERE character_id = ? AND quest_key = 'human_cathedral_summons'",
                (self.player_character.id,),
            )
        gm = self._session(
            self.gm_account,
            self.gm_character,
            ["staff on", "gm reset quest Mira A Summons to the Cathedral", "confirm"],
        )
        asyncio.run(gm.enter_character())
        gm.outputs.clear()
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        quest = next(row for row in self.db.list_quests(self.player_character.id) if row["quest_key"] == "human_cathedral_summons")
        self.assertEqual(quest["current_step"], "read_note")
        self.assertIn("World flags, rewards, and inventory were intentionally left untouched", "".join(gm.outputs))

    def test_restore_mobile_npc_requires_confirmation(self):
        manager = MobileNpcManager()
        state = manager.states["blackwall_guard"]
        state.current_room_key = "human_training_yard"
        state.inactive_ticks = 5
        gm = self._session(self.gm_account, self.gm_character, ["staff on", "gm restore npc Blackwall Guard", "confirm"], manager)
        asyncio.run(gm.enter_character())
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        self.assertEqual(state.current_room_key, "human_training_yard")
        asyncio.run(gm.playing_prompt())
        self.assertEqual(state.current_room_key, state.definition.spawn_room_key)
        self.assertEqual(state.inactive_ticks, 0)

    def test_possess_mobile_npc_creates_short_live_performance(self):
        manager = MobileNpcManager()
        peddler = manager.states["ashen_way_curio_peddler"]
        self.db.set_character_room(self.player_character.id, peddler.current_room_key)
        player_character = self.db.get_character_by_name("Mira")
        gm = self._session(self.gm_account, self.gm_character, ["staff on", "gm possess Ashen Way Curio Peddler", "gm speak Fresh charms, no refunds."], manager)
        player = self._session(self.player_account, player_character, manager=manager)
        asyncio.run(gm.enter_character())
        asyncio.run(player.enter_character())
        player.outputs.clear()
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        self.assertIn('Ashen Way Curio Peddler says, "Fresh charms, no refunds."', "".join(player.outputs))

    def test_gm_actions_are_audited(self):
        gm = self._session(self.gm_account, self.gm_character, ["staff on", "gm invisible"])
        asyncio.run(gm.enter_character())
        asyncio.run(gm.playing_prompt())
        asyncio.run(gm.playing_prompt())
        with self.db.connect() as db:
            rows = db.execute("SELECT action FROM staff_audit_log ORDER BY id").fetchall()
        actions = [row["action"] for row in rows]
        self.assertIn("staff_mode_on", actions)
        self.assertIn("visibility", actions)

    def test_owner_can_assign_roles_and_admin_can_view_audit(self):
        with self.db.connect() as db:
            db.execute("UPDATE staff_roles SET role = 'owner' WHERE account_id = ?", (self.gm_account.id,))
        owner = self._session(self.gm_account, self.gm_character, ["staff on", "staff role playeraccount admin"])
        asyncio.run(owner.enter_character())
        asyncio.run(owner.playing_prompt())
        asyncio.run(owner.playing_prompt())
        admin = self._session(self.player_account, self.player_character, ["staff on", "staff audit 5"])
        asyncio.run(admin.enter_character())
        self.assertEqual(_role_for(admin), "admin")
        asyncio.run(admin.playing_prompt())
        asyncio.run(admin.playing_prompt())
        self.assertIn("Staff Audit", "".join(admin.outputs))
        self.assertIn("assign_role", "".join(admin.outputs))


if __name__ == "__main__":
    unittest.main()
