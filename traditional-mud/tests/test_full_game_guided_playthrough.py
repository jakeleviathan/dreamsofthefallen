from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FullGameGuidedPlaythroughTests(unittest.TestCase):
    def test_fresh_goblin_priest_can_complete_current_story_ceiling_through_player_commands(self):
        code = r'''
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

import server
import mud.broken_reach_midgame as reach
import mud.crownfire_march_31_40 as crown
import mud.gloamworks_dungeon as gloam
import mud.greywake_march as greywake
import mud.sablewater_reach as sable
import mud.salt_kingdoms_midgame as salt
import mud.veyra_city as veyra
from mud.alpha_ux import ensure_alpha_ux_schema
from mud.database import Database
from mud.goblin_rattlefen_opening import RATTLEFEN_OPENING_COMPLETE_FLAG
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_START_ROOM_KEY,
    GOBLIN_TINKER_ROW_KEY,
)
from mud.mechanics import CombatantState, PROGRESSION_RULES
from mud.session import SessionState
from mud.stats import starting_armor_class
from mud.waymaps import shortest_route
from mud.waymeet_frontier import (
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_GLOAM_MOUTH_KEY,
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
        account = database.create_account("wayfarer_account", "not-a-real-hash")
        character = database.create_character(account.id, "Wayfarer", "goblin", "priest")
        character = database.get_character_by_name("Wayfarer")
        assert character is not None
        assert character.level == 1
        assert character.current_room == GOBLIN_START_ROOM_KEY

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
        output = []

        def rebuild_combatant():
            ch = session.character
            session.combatant = CombatantState(
                character_id=ch.id,
                race_key=ch.race or "",
                current_hp=ch.stats.maximum_hp(25),
                max_hp=ch.stats.maximum_hp(25),
                current_mana=ch.stats.maximum_mana(20),
                max_mana=ch.stats.maximum_mana(20),
                auto_attack_interval=2.5,
                current_movement=100,
                max_movement=100,
                stats=ch.stats,
                armor_class=starting_armor_class(ch.character_class or ""),
            )

        rebuild_combatant()

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
                    assert marker not in folded, (session.character.level, session.character.current_room, command, marker, text)
            return text

        def room():
            return session.character.current_room

        def refresh():
            updated = database.get_character_by_name(session.character.name)
            assert updated is not None
            session.character = updated
            rebuild_combatant()

        def raise_to(level):
            target = PROGRESSION_RULES.cumulative_xp_for_level(level)
            if session.character.experience < target:
                database.add_experience(session.character.id, target - session.character.experience)
                refresh()
            assert session.character.level >= level, (level, session.character.level, session.character.experience)

        def route_to(target):
            route = shortest_route(server.WORLD, session, room(), target)
            assert route is not None, (session.character.level, room(), target)
            return route

        async def walk_to(target):
            route = route_to(target)
            for direction in route:
                await run(direction)
            assert room() == target, (room(), target, route)
            return route

        async def resolve_fight(command):
            text = await run(command)
            enemy = session.active_enemy
            assert enemy is not None, (session.character.level, room(), command, text)
            enemy.take_damage(enemy.current_hp)
            await session._finish_enemy_defeat(enemy)
            assert session.active_enemy is None, command
            refresh()
            return text

        # ------------------------------------------------------------------
        # LEVEL 1: Rattlefen opening. Every action is a normal player command.
        # ------------------------------------------------------------------
        text = await run("goals")
        assert "Three Bells" in text or "fresh wreck" in text.lower(), text
        await walk_to(GOBLIN_SORTING_SPINE_KEY)
        await run("examine fresh wreck")
        await run("claim spring")
        await walk_to(GOBLIN_BRASSGUT_MARKET_KEY)
        await run("talk ruskle")
        await run("counter fair")
        await walk_to(GOBLIN_LEDGER_HALL_KEY)
        await run("talk sella")
        await run("negotiate claim")
        await walk_to(GOBLIN_TINKER_ROW_KEY)
        await run("talk brin")
        await run("repurpose salvage")
        await walk_to(GOBLIN_BRASSGUT_MARKET_KEY)
        await run("talk tressa")
        await run("keep token")
        await walk_to(GOBLIN_START_ROOM_KEY)
        await run("talk vikka")
        await run("mark spiral")
        assert RATTLEFEN_OPENING_COMPLETE_FLAG in database.list_flags(session.character.id)

        # Waymeet is explicitly a level 2+ shared road. Ordinary starter combat/
        # side content supplies this XP in play; the story harness raises only to
        # the exact gate so it can test the route and quest rather than grind.
        raise_to(2)
        await walk_to(GOBLIN_FLOODGATE_WALK_KEY)
        await walk_to(WAYMEET_CROSSROADS_KEY)
        await run("talk marshal")
        await walk_to(WAYMEET_BROKEN_MILE_KEY)
        await run("examine collapse")
        await walk_to(WAYMEET_GLOAM_MOUTH_KEY)
        await run("examine sealed door")
        await walk_to(WAYMEET_CROSSROADS_KEY)
        await run("talk marshal")

        # ------------------------------------------------------------------
        # LEVEL 4-5: Gloamworks, including the solo-safe Twin Seal.
        # ------------------------------------------------------------------
        raise_to(4)
        await walk_to(WAYMEET_GLOAM_MOUTH_KEY)
        await run("talk surveyor")
        await walk_to(gloam.GLOAM_ENTRY_KEY)
        await walk_to(gloam.GLOAM_GLASS_FAULT_KEY)
        await run("examine fault")
        await walk_to(gloam.GLOAM_BRAKE_CHAPEL_KEY)
        await resolve_fight("attack saint")
        await walk_to(gloam.GLOAM_HOLLOW_DYNAMO_KEY)
        await resolve_fight("attack mother")
        await walk_to(gloam.GLOAM_TWIN_SEAL_KEY)
        await run("hold left seal")
        await run("hold right seal")
        await walk_to(gloam.GLOAM_BURIED_COURT_KEY)
        await resolve_fight("attack regent")
        await walk_to(WAYMEET_GLOAM_MOUTH_KEY)
        await run("talk surveyor")
        assert gloam.GLOAMWORKS_COMPLETE_FLAG in database.list_flags(session.character.id)

        # ------------------------------------------------------------------
        # LEVELS 6-10: the audited shared road.
        # ------------------------------------------------------------------
        raise_to(6)
        await walk_to(greywake.GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")
        await walk_to(greywake.GREYWAKE_HEATH_KEY)
        await run("examine grey crust")
        await walk_to(greywake.GREYWAKE_RESONANT_ORCHARD_KEY)
        await run("examine trees")
        await walk_to(greywake.GREYWAKE_RIFTFIELD_KEY)
        await run("examine seam")
        await walk_to(greywake.GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")
        await walk_to(greywake.GREYWAKE_WARDEN_POST_KEY)
        await run("talk captain")
        await walk_to(greywake.GREYWAKE_LEDGER_CUT_KEY)
        await run("talk factor")
        await walk_to(greywake.GREYWAKE_LANTERN_HOSPICE_KEY)
        await run("talk keeper")
        await walk_to(greywake.GREYWAKE_THREE_BANNER_KEY)
        await run("support ledger")
        assert session.character.level >= 7
        await walk_to(greywake.GREYWAKE_SIGNAL_HILL_KEY)
        await run("rally surge")
        for _ in range(6):
            await greywake._record_surge_kill(session)
        await walk_to(greywake.GREYWAKE_THREE_BANNER_KEY)
        await run("talk captain")
        assert greywake.GREYWAKE_CHAIN_COMPLETE_FLAG in database.list_flags(session.character.id)

        await walk_to(sable.SABLEWATER_NORTH_FERRY_KEY)
        await run("talk ferrymaster")
        await walk_to(sable.SABLEWATER_BROKEN_LEVEE_KEY)
        await run("examine breach")
        await walk_to(sable.SABLEWATER_WILLOW_FERRY_KEY)
        await run("examine ferry chain")
        await walk_to(sable.SABLEWATER_NORTH_FERRY_KEY)
        await run("talk ferrymaster")
        await walk_to(sable.SABLEWATER_OLD_CUSTOMS_KEY)
        await run("examine toll marker")
        await walk_to(sable.SABLEWATER_TOLLHOUSE_MOUTH_KEY)
        await run("examine sunken gate")
        await run("talk diver")
        assert session.character.level >= 8

        await walk_to(veyra.VEYRA_GATE_WARD_KEY)
        await walk_to(veyra.VEYRA_GRAND_CROSSING_KEY)
        await walk_to(veyra.VEYRA_BRASSMARKET_KEY)
        await walk_to(veyra.VEYRA_KEYHOUSE_KEY)
        await walk_to(veyra.VEYRA_FIVE_WAYS_KEY)
        await run("train")
        await walk_to(veyra.VEYRA_NOTICE_HALL_KEY)
        await run("read board")
        await walk_to(veyra.VEYRA_CIVIC_STEPS_KEY)
        await run("talk steward")
        assert veyra.VEYRA_RESIDENT_FLAG in database.list_flags(session.character.id)

        await walk_to(veyra.VEYRA_LEDGER_OFFICE_KEY)
        await run("talk factor")
        await walk_to(veyra.VEYRA_BRASSMARKET_KEY)
        await run("appraise cargo")
        await walk_to(veyra.VEYRA_LEDGER_OFFICE_KEY)
        await run("talk factor")
        assert veyra.VEYRA_FACTION_RANK_FLAG in database.list_flags(session.character.id)

        await walk_to(sable.DROWNED_ENTRY_KEY)
        await walk_to(sable.DROWNED_SLUICE_CHAMBER_KEY)
        await resolve_fight("attack warden")
        await walk_to(sable.DROWNED_FLOODED_ARCHIVE_KEY)
        await run("search ledgers")
        await walk_to(sable.DROWNED_COIN_VAULT_KEY)
        await run("search coin vault")
        await walk_to(sable.DROWNED_MAGISTRATE_ROOM_KEY)
        await run("search magistrate desk")
        await walk_to(sable.DROWNED_BRASS_TRIBUNAL_KEY)
        await run("present seals")
        await resolve_fight("attack auditor")
        await walk_to(sable.DROWNED_COLLECTOR_WELL_KEY)
        await run("turn final sluice")
        assert sable.DROWNED_TOLLHOUSE_COMPLETE_FLAG in database.list_flags(session.character.id)
        assert session.character.level >= 10
        text = await run("journey")
        assert "level 11" in text.lower() and "Broken Reach" in text, text

        # ------------------------------------------------------------------
        # LEVELS 11-20: Broken Reach. Raise only at authored chapter gates.
        # ------------------------------------------------------------------
        raise_to(11)
        text = await run("journey")
        assert "Broken Reach" in text and "Ragged Caravanserai" in text, text
        await walk_to(reach.OLD_TOLL_ROAD_KEY)
        await walk_to(reach.CARAVANSERAI_KEY)
        await run("talk hesta")
        await walk_to(reach.LEANING_ORCHARD_KEY)
        await run("examine wagon")
        await walk_to(reach.GRINNING_CAMP_KEY)
        await run("talk jory")
        await walk_to(reach.SPLIT_LANTERN_BRIDGE_KEY)
        await run("examine lanterns")
        await walk_to(reach.CARAVANSERAI_KEY)
        await run("talk hesta")
        assert reach.FIRST_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(14)
        await run("talk hesta")
        await walk_to(reach.GRINNING_CAMP_KEY)
        await run("talk jory")
        await walk_to(reach.CINDER_FORD_KEY)
        await run("talk vessa")
        await run("examine tally")
        await walk_to(reach.CARAVANSERAI_KEY)
        await run("choose road")
        assert reach.FACTION_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(17)
        await walk_to(reach.HOUSE_THRESHOLD_KEY)
        await run("talk rook")
        await walk_to(reach.HOUSE_PARLOUR_KEY)
        await run("read guestbook")
        await walk_to(reach.HOUSE_DEEP_HEARTH_KEY)
        await run("examine hearth")
        await walk_to(reach.HOUSE_KEEPER_LOCK_KEY)
        blocked = await run("attack warden")
        assert "RELEASE LEFT BAR" in blocked and "RELEASE RIGHT BAR" in blocked, blocked
        await run("release left bar")
        await run("release right bar")
        await resolve_fight("attack warden")
        await run("examine lock")
        await walk_to(reach.HOUSE_BLACK_BELL_KEY)
        await run("listen bell")
        await walk_to(reach.HOUSE_CONTAINMENT_RING_KEY)
        await resolve_fight("attack guest")
        assert reach.HOUSE_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(20)
        await walk_to(reach.CARAVANSERAI_KEY)
        await run("talk hesta")
        await walk_to(reach.HOUSE_CONTAINMENT_RING_KEY)
        await run("set anchors")
        await walk_to(reach.SPLIT_LANTERN_BRIDGE_KEY)
        await run("drop span")
        await walk_to(reach.HOUSE_WAKE_GATE_KEY)
        await run("open bypass")
        assert reach.CAPSTONE_COMPLETE_FLAG in database.list_flags(session.character.id)

        # ------------------------------------------------------------------
        # LEVELS 21-30: Salt Kingdoms.
        # ------------------------------------------------------------------
        raise_to(21)
        text = await run("journey")
        assert "Salt Kingdoms" in text and "Saltwind Gate" in text, text
        await walk_to(salt.SALTWIND_GATE_KEY)
        await run("talk enna")
        await walk_to(salt.TIDEMARK_SINK_KEY)
        await run("examine sink")
        await walk_to(salt.KEELSPIRE_GATE_KEY)
        await walk_to(salt.KEELSPIRE_ARCHIVE_KEY)
        await run("read tidemarks")
        await walk_to(salt.SALTWIND_GATE_KEY)
        await run("talk enna")
        assert salt.ARRIVAL_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(23)
        await walk_to(salt.KEELSPIRE_QUAYS_KEY)
        await run("talk orro")
        await walk_to(salt.GLASS_KEEL_CAPTAIN_KEY)
        await run("read log")
        await walk_to(salt.GLASS_KEEL_BALLAST_KEY)
        blocked = await run("attack matriarch")
        assert "CUT PORT WEIGHT" in blocked and "CUT STARBOARD WEIGHT" in blocked, blocked
        await run("cut port weight")
        await run("cut starboard weight")
        await resolve_fight("attack matriarch")
        await walk_to(salt.GLASS_KEEL_TIDEHOLD_KEY)
        await run("examine tideglass")
        assert salt.GLASS_KEEL_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(26)
        await walk_to(salt.KEELSPIRE_CROWN_SQUARE_KEY)
        await run("talk caldrin")
        await walk_to(salt.KEELSPIRE_ROPEMARKET_KEY)
        await run("talk nima")
        await walk_to(salt.KEELSPIRE_THREE_WELLS_KEY)
        await run("talk sela")
        await run("read rations")
        await walk_to(salt.KEELSPIRE_CROWN_SQUARE_KEY)
        await run("priority wells")
        assert salt.FACTION_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(27)
        await walk_to(salt.KEELSPIRE_HARBOR_VAULT_KEY)
        await run("talk tavik")
        await walk_to(salt.UNDERTIDE_PRESSURE_WALK_KEY)
        await run("read gauges")
        await walk_to(salt.UNDERTIDE_COUNTERWEIGHT_KEY)
        await run("set counterweight")
        await walk_to(salt.UNDERTIDE_REGENT_KEY)
        blocked = await run("attack regent")
        assert "VENT EAST" in blocked and "CLOSE HIGH" in blocked and "OPEN RETURN" in blocked, blocked
        await run("vent east")
        await run("close high")
        await run("open return")
        await resolve_fight("attack regent")
        await walk_to(salt.UNDERTIDE_DISTRIBUTOR_KEY)
        await run("examine distributor")
        await walk_to(salt.UNDERTIDE_HEART_KEY)
        await run("listen water")
        assert salt.UNDERTIDE_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(30)
        await walk_to(salt.UNDERTIDE_RELEASE_KEY)
        await run("free current")
        assert salt.CAPSTONE_COMPLETE_FLAG in database.list_flags(session.character.id)

        # ------------------------------------------------------------------
        # LEVELS 31-40: Crownfire March and current authored ending.
        # ------------------------------------------------------------------
        raise_to(31)
        text = await run("journey")
        assert "Crownfire March" in text and "Marchward Post" in text, text
        await walk_to(crown.MARCHWARD_POST_KEY)
        await run("talk evara")
        await walk_to(crown.BURNED_TOLL_KEY)
        await run("examine wagon")
        await walk_to(crown.GALLOWS_MILE_KEY)
        await resolve_fight("attack captain")
        await run("read orders")
        await walk_to(crown.MARCHWARD_POST_KEY)
        await run("talk evara")
        assert crown.ARRIVAL_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(33)
        await walk_to(crown.MORROWGATE_COUNCIL_KEY)
        await run("talk iven")
        await walk_to(crown.MORROWGATE_HEALERS_KEY)
        await run("talk della")
        await walk_to(crown.MORROWGATE_MARKET_KEY)
        await run("search contracts")
        await run("accuse varek")
        assert crown.BLOCKADE_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(34)
        await walk_to(crown.MORROWGATE_RAMPART_KEY)
        await run("talk renna")
        await walk_to(crown.REDOUBT_SIGNAL_KEY)
        await run("cut signal rope")
        await walk_to(crown.REDOUBT_PRISON_KEY)
        await run("free prisoners")
        await walk_to(crown.REDOUBT_OFFICE_KEY)
        await resolve_fight("attack venn")
        assert crown.REDOUBT_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(36)
        await walk_to(crown.REFUGEE_FORD_KEY)
        await run("talk lysa")
        await walk_to(crown.REDOUBT_OFFICE_KEY)
        await run("read conscription rolls")
        await walk_to(crown.REFUGEE_FORD_KEY)
        await run("protect deserters")
        assert crown.DESERTER_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(37)
        await walk_to(crown.MORROWGATE_RAMPART_KEY)
        await run("talk renna")
        await walk_to(crown.PALACE_SIGNAL_KEY)
        await run("break signal mirror")
        await walk_to(crown.PALACE_HOSTAGES_KEY)
        await run("free hostages")
        await walk_to(crown.PALACE_MAP_KEY)
        await run("read war map")
        await walk_to(crown.PALACE_COMMAND_KEY)
        await resolve_fight("attack hadrik")
        await run("take black ledger")
        assert crown.PALACE_COMPLETE_FLAG in database.list_flags(session.character.id)

        raise_to(40)
        await walk_to(crown.PALACE_TREATY_KEY)
        await resolve_fight("attack dask")
        await run("demand trial")
        assert crown.CAPSTONE_COMPLETE_FLAG in database.list_flags(session.character.id)
        assert crown.TRIAL_ENDING_FLAG in database.list_flags(session.character.id)
        assert session.character.level >= 40
        text = await run("journey")
        assert "Current story complete" in text and "level-40 campaign ceiling" in text, text

        print(
            "FULL_GAME_GUIDED_PLAYTHROUGH_COMPLETE",
            session.character.name,
            session.character.race,
            session.character.character_class,
            session.character.level,
            session.character.experience,
        )

asyncio.run(main())
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=240,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("FULL_GAME_GUIDED_PLAYTHROUGH_COMPLETE Wayfarer goblin priest 40", result.stdout)


if __name__ == "__main__":
    unittest.main()
