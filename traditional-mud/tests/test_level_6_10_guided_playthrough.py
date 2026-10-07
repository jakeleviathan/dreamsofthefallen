from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LevelSixToTenGuidedPlaythroughTests(unittest.TestCase):
    def test_production_stack_guides_exact_floor_player_to_veyra_without_admin_explanation(self):
        code = r'''
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

import server
import mud.greywake_march as greywake
from mud.alpha_ux import ensure_alpha_ux_schema
from mud.database import Database
from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
from mud.mechanics import CombatantState, PROGRESSION_RULES
from mud.session import SessionState
from mud.stats import starting_armor_class
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY
from mud.greywake_march import (
    GREYWAKE_CHAIN_COMPLETE_FLAG,
    GREYWAKE_THREE_BANNER_KEY,
    GREYWAKE_WARDEN_POST_KEY,
    GREYWAKE_LEDGER_CUT_KEY,
    GREYWAKE_LANTERN_HOSPICE_KEY,
    GREYWAKE_HEATH_KEY,
    GREYWAKE_RESONANT_ORCHARD_KEY,
    GREYWAKE_RIFTFIELD_KEY,
    GREYWAKE_SIGNAL_HILL_KEY,
    GREYWAKE_SUNK_CAUSEWAY_KEY,
    GREYWAKE_VEYRA_GATE_KEY,
    THREE_CLAIMS_QUEST_KEY,
)
from mud.sablewater_reach import (
    SABLEWATER_NORTH_FERRY_KEY,
    SABLEWATER_FLOOD_ROAD_KEY,
    SABLEWATER_REED_FARMS_KEY,
    SABLEWATER_BROKEN_LEVEE_KEY,
    SABLEWATER_WILLOW_FERRY_KEY,
    SABLEWATER_OLD_CUSTOMS_KEY,
    SABLEWATER_TOLL_ISLAND_KEY,
    SABLEWATER_TOLLHOUSE_MOUTH_KEY,
    TOLLHOUSE_UNLOCKED_FLAG,
    DROWNED_ENTRY_KEY,
    DROWNED_TOLL_HALL_KEY,
    DROWNED_LEDGER_GALLERY_KEY,
    DROWNED_SLUICE_CHAMBER_KEY,
    DROWNED_FLOODED_ARCHIVE_KEY,
    DROWNED_COIN_VAULT_KEY,
    DROWNED_MAGISTRATE_ROOM_KEY,
    DROWNED_CLOCK_CHAMBER_KEY,
    DROWNED_BRASS_TRIBUNAL_KEY,
    DROWNED_COLLECTOR_WELL_KEY,
    DROWNED_TOLLHOUSE_COMPLETE_FLAG,
)
from mud.veyra_city import (
    VEYRA_GATE_WARD_KEY,
    VEYRA_CARAVAN_COURT_KEY,
    VEYRA_GRAND_CROSSING_KEY,
    VEYRA_BRASSMARKET_KEY,
    VEYRA_KEYHOUSE_KEY,
    VEYRA_CIVIC_STEPS_KEY,
    VEYRA_FIVE_WAYS_KEY,
    VEYRA_NOTICE_HALL_KEY,
    VEYRA_THREE_OFFICES_KEY,
    VEYRA_LEDGER_OFFICE_KEY,
    VEYRA_SOUTH_SPRAWL_KEY,
    VEYRA_RESIDENT_FLAG,
    VEYRA_FACTION_RANK_FLAG,
)

BAD_TEXT = (
    "unknown command",
    "you cannot go that way",
    "that way is locked",
    "that way is closed",
    "there are no authored exits",
)

async def main():
    with tempfile.TemporaryDirectory() as tmp:
        database = Database(Path(tmp) / "mud.db")
        ensure_alpha_ux_schema(database)
        account = database.create_account("guided610", "not-a-real-hash")
        character = database.create_character(account.id, "Roadtest", "goblin", "brute")
        database.add_experience(
            character.id,
            PROGRESSION_RULES.cumulative_xp_for_level(6),
        )
        database.grant_flag(character.id, GLOAMWORKS_COMPLETE_FLAG)
        database.set_character_room(character.id, WAYMEET_GLOAM_MOUTH_KEY)
        character = database.get_character_by_name(character.name)
        assert character is not None and character.level == 6

        session = object.__new__(server.PlayerSession)
        session.database = database
        session.account = account
        session.character = character
        session.state = SessionState.PLAYING
        session.active_enemy = None
        session.selected_enemy = None
        session.selected_mobile_npc_key = None
        session.selected_enemy_room_key = None
        session.selected_player_character_id = None
        session.selected_player_room_key = None
        session.selected_target_kind = None
        session.active_mobile_npc_key = None
        session.current_opponent = None
        session.combat_task = None
        session.dot_tasks = set()
        session.ward_until = 0.0
        session.mobile_npcs = None
        session.mobile_npc_movement_callback = None
        session.room_players_callback = None
        session._movement_resting = False
        session.telnet = SimpleNamespace(gmcp_enabled=False)
        session.combatant = CombatantState(
            character_id=character.id,
            race_key=character.race or "",
            current_hp=character.stats.maximum_hp(25),
            max_hp=character.stats.maximum_hp(25),
            current_mana=character.stats.maximum_mana(20),
            max_mana=character.stats.maximum_mana(20),
            auto_attack_interval=2.5,
            current_movement=100,
            max_movement=100,
            stats=character.stats,
            armor_class=starting_armor_class(character.character_class or ""),
        )
        output = []

        async def send(text):
            output.append(text)

        async def send_client_state():
            return None

        session.send = send
        session.send_client_state = send_client_state

        async def run(command, *, allow_bad=False):
            output.clear()
            used = False

            async def prompt(_text):
                nonlocal used
                if used:
                    return None
                used = True
                return command

            session.prompt = prompt
            await session.playing_prompt()
            text = "".join(output)
            if not allow_bad:
                folded = text.casefold()
                for marker in BAD_TEXT:
                    assert marker not in folded, (command, marker, text)
            return text

        def room():
            return session.character.current_room

        async def move(direction, expected):
            await run(direction)
            assert room() == expected, (direction, room(), expected)

        async def resolve_fight(command):
            text = await run(command)
            enemy = session.active_enemy
            assert enemy is not None, (command, text)
            enemy.take_damage(enemy.current_hp)
            await session._finish_enemy_defeat(enemy)
            assert session.active_enemy is None, command
            return text

        # The player asks the game, not a developer, where the shared road goes.
        text = await run("journey")
        assert "Greywake March" in text and "EAST" in text, text

        await move("east", "greywake_west_mile")
        await move("east", GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")
        text = await run("goals")
        assert "EXAMINE GREY CRUST" in text, text

        await move("north", GREYWAKE_WARDEN_POST_KEY)
        await move("east", GREYWAKE_HEATH_KEY)
        await run("examine grey crust")
        await move("south", GREYWAKE_SIGNAL_HILL_KEY)
        await move("west", GREYWAKE_RESONANT_ORCHARD_KEY)
        await run("examine trees")
        await move("north", GREYWAKE_SIGNAL_HILL_KEY)
        await move("east", GREYWAKE_RIFTFIELD_KEY)
        await run("examine seam")
        await move("west", GREYWAKE_SIGNAL_HILL_KEY)
        await move("south", GREYWAKE_SUNK_CAUSEWAY_KEY)
        await move("west", GREYWAKE_LEDGER_CUT_KEY)
        await move("north", GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")

        # This exact objective used to be impossible because TALK CAPTAIN was
        # swallowed by the generic captain handler.
        text = await run("journey")
        assert "TALK CAPTAIN at the Roadwarden Post" in text, text
        await move("north", GREYWAKE_WARDEN_POST_KEY)
        await run("talk captain")
        q = database.get_quest(character.id, THREE_CLAIMS_QUEST_KEY)
        assert q and q["current_step"] == "hear_ledger", q

        await move("south", GREYWAKE_THREE_BANNER_KEY)
        await move("south", GREYWAKE_LEDGER_CUT_KEY)
        await run("talk factor")
        await move("north", GREYWAKE_THREE_BANNER_KEY)
        await move("east", GREYWAKE_LANTERN_HOSPICE_KEY)
        await run("talk keeper")
        await move("west", GREYWAKE_THREE_BANNER_KEY)
        text = await run("support ledger")
        assert session.character.level == 7, session.character.experience
        assert "Signal Hill" in text and "RALLY SURGE" in text, text
        text = await run("journey")
        assert "Bell Below the Wind" in text and "RALLY SURGE" in text, text

        await move("south", GREYWAKE_LEDGER_CUT_KEY)
        await move("east", GREYWAKE_SUNK_CAUSEWAY_KEY)
        await move("north", GREYWAKE_SIGNAL_HILL_KEY)
        await run("rally surge")
        for _ in range(6):
            await greywake._record_surge_kill(session)
        await move("south", GREYWAKE_SUNK_CAUSEWAY_KEY)
        await move("west", GREYWAKE_LEDGER_CUT_KEY)
        await move("north", GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")
        assert GREYWAKE_CHAIN_COMPLETE_FLAG in database.list_flags(character.id)

        # The game now gives the whole handoff instead of requiring a remembered map.
        text = await run("journey")
        assert "SOUTH to Ledger Cut" in text and "TALK FERRYMASTER" in text, text
        await move("south", GREYWAKE_LEDGER_CUT_KEY)
        await move("south", SABLEWATER_REED_FARMS_KEY)
        await move("east", SABLEWATER_FLOOD_ROAD_KEY)
        await move("north", SABLEWATER_NORTH_FERRY_KEY)
        await run("talk ferrymaster")

        await move("south", SABLEWATER_FLOOD_ROAD_KEY)
        await move("south", SABLEWATER_BROKEN_LEVEE_KEY)
        await run("examine breach")
        await move("east", SABLEWATER_WILLOW_FERRY_KEY)
        await run("examine ferry chain")
        await move("west", SABLEWATER_BROKEN_LEVEE_KEY)
        await move("north", SABLEWATER_FLOOD_ROAD_KEY)
        await move("north", SABLEWATER_NORTH_FERRY_KEY)
        await run("talk ferrymaster")

        await move("south", SABLEWATER_FLOOD_ROAD_KEY)
        await move("south", SABLEWATER_BROKEN_LEVEE_KEY)
        await move("east", SABLEWATER_WILLOW_FERRY_KEY)
        await move("south", SABLEWATER_OLD_CUSTOMS_KEY)
        await run("examine toll marker")
        await move("east", SABLEWATER_TOLL_ISLAND_KEY)
        await move("east", SABLEWATER_TOLLHOUSE_MOUTH_KEY)
        await run("examine sunken gate")
        text = await run("talk diver")
        assert TOLLHOUSE_UNLOCKED_FLAG in database.list_flags(character.id)
        assert session.character.level >= 8, session.character.experience
        assert "Drowned Tollhouse is open DOWN" in text, text

        # If the player asks for the main road instead, the game explains the long
        # return to Veyra rather than requiring us to give directions out of band.
        text = await run("journey")
        assert "North Ferry" in text and "WEST to Reed Farms" in text and "Veyra Outer Gate" in text, text

        await move("west", SABLEWATER_TOLL_ISLAND_KEY)
        await move("west", SABLEWATER_OLD_CUSTOMS_KEY)
        await move("north", SABLEWATER_WILLOW_FERRY_KEY)
        await move("west", SABLEWATER_BROKEN_LEVEE_KEY)
        await move("north", SABLEWATER_FLOOD_ROAD_KEY)
        await move("west", SABLEWATER_REED_FARMS_KEY)
        await move("north", GREYWAKE_LEDGER_CUT_KEY)
        await move("east", GREYWAKE_SUNK_CAUSEWAY_KEY)
        await move("east", GREYWAKE_RIFTFIELD_KEY)
        await move("east", "greywake_old_aqueduct")
        await move("east", "greywake_veyra_road")
        await move("east", GREYWAKE_VEYRA_GATE_KEY)
        await move("east", VEYRA_GATE_WARD_KEY)

        # Arrival tour: every next action is player-facing and executable.
        await move("east", VEYRA_CARAVAN_COURT_KEY)
        await move("east", VEYRA_GRAND_CROSSING_KEY)
        await move("west", VEYRA_CARAVAN_COURT_KEY)
        await move("south", VEYRA_BRASSMARKET_KEY)
        await move("north", VEYRA_CARAVAN_COURT_KEY)
        await move("north", VEYRA_KEYHOUSE_KEY)
        await move("south", VEYRA_CARAVAN_COURT_KEY)
        await move("east", VEYRA_GRAND_CROSSING_KEY)
        await move("east", VEYRA_CIVIC_STEPS_KEY)
        await move("north", VEYRA_FIVE_WAYS_KEY)
        await run("train")
        await move("south", VEYRA_CIVIC_STEPS_KEY)
        await move("east", VEYRA_NOTICE_HALL_KEY)
        await run("read board")
        await move("west", VEYRA_CIVIC_STEPS_KEY)
        await run("talk steward")
        assert VEYRA_RESIDENT_FLAG in database.list_flags(character.id)

        # Our Greywake choice was Deep Ledger. The city quest must remain executable.
        await move("south", VEYRA_THREE_OFFICES_KEY)
        await move("south", VEYRA_LEDGER_OFFICE_KEY)
        await run("talk factor")
        await move("north", VEYRA_THREE_OFFICES_KEY)
        await move("north", VEYRA_CIVIC_STEPS_KEY)
        await move("west", VEYRA_GRAND_CROSSING_KEY)
        await move("west", VEYRA_CARAVAN_COURT_KEY)
        await move("south", VEYRA_BRASSMARKET_KEY)
        await run("appraise cargo")
        await move("north", VEYRA_CARAVAN_COURT_KEY)
        await move("east", VEYRA_GRAND_CROSSING_KEY)
        await move("east", VEYRA_CIVIC_STEPS_KEY)
        await move("south", VEYRA_THREE_OFFICES_KEY)
        await move("south", VEYRA_LEDGER_OFFICE_KEY)
        await run("talk factor")
        assert VEYRA_FACTION_RANK_FLAG in database.list_flags(character.id)

        # The player has an active Drowned quest, so JOURNEY must explain how to
        # return there from the city instead of merely restating "defeat warden".
        text = await run("journey")
        assert "Civic Steps" in text and "North Ferry" in text and "Tollhouse Mouth" in text and "DOWN" in text, text

        # Follow only the route the game itself just supplied.
        await move("north", VEYRA_THREE_OFFICES_KEY)
        await move("north", VEYRA_CIVIC_STEPS_KEY)
        await move("west", VEYRA_GRAND_CROSSING_KEY)
        await move("west", VEYRA_CARAVAN_COURT_KEY)
        await move("west", VEYRA_GATE_WARD_KEY)
        await move("south", VEYRA_SOUTH_SPRAWL_KEY)
        await move("south", SABLEWATER_NORTH_FERRY_KEY)
        await move("south", SABLEWATER_FLOOD_ROAD_KEY)
        await move("south", SABLEWATER_BROKEN_LEVEE_KEY)
        await move("east", SABLEWATER_WILLOW_FERRY_KEY)
        await move("south", SABLEWATER_OLD_CUSTOMS_KEY)
        await move("east", SABLEWATER_TOLL_ISLAND_KEY)
        await move("east", SABLEWATER_TOLLHOUSE_MOUTH_KEY)
        await move("down", DROWNED_ENTRY_KEY)

        await move("east", DROWNED_TOLL_HALL_KEY)
        await move("east", DROWNED_LEDGER_GALLERY_KEY)
        await move("east", DROWNED_SLUICE_CHAMBER_KEY)
        await resolve_fight("attack warden")

        text = await run("goals")
        assert "SEARCH LEDGERS" in text and "SEARCH COIN VAULT" in text and "SEARCH MAGISTRATE DESK" in text, text
        await move("west", DROWNED_LEDGER_GALLERY_KEY)
        await move("north", DROWNED_FLOODED_ARCHIVE_KEY)
        await run("search ledgers")
        await move("east", DROWNED_COIN_VAULT_KEY)
        await run("search coin vault")
        await move("east", DROWNED_MAGISTRATE_ROOM_KEY)
        await run("search magistrate desk")
        await move("east", DROWNED_CLOCK_CHAMBER_KEY)
        await move("east", DROWNED_BRASS_TRIBUNAL_KEY)
        await run("present seals")
        await resolve_fight("attack auditor")
        await move("east", DROWNED_COLLECTOR_WELL_KEY)
        await run("turn final sluice")

        assert DROWNED_TOLLHOUSE_COMPLETE_FLAG in database.list_flags(character.id)
        assert session.character.level >= 10, (session.character.level, session.character.experience)
        text = await run("journey")
        assert "Level 10 reached" in text, text

        print("GUIDED_6_10_PLAYTHROUGH_COMPLETE", session.character.level, session.character.experience)

asyncio.run(main())
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=150,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("GUIDED_6_10_PLAYTHROUGH_COMPLETE", result.stdout)


if __name__ == "__main__":
    unittest.main()
