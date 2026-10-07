from __future__ import annotations

from mud.mechanics import class_abilities_for_level
from mud.quests import QUESTS_BY_KEY
from mud.room_engine import PlayerRoomContext
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


EARLY_GAME_MAX_LEVEL = 10
GOAL_ALIASES = frozenset({"goal", "goals", "objective", "objectives", "what now", "what next"})
JOURNEY_ALIASES = frozenset({"journey", "main journey", "main road", "progression road"})
DIRECTION_COMMANDS = frozenset({"north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"})

LOOK_FLAG = "early_polish_looked"
MOVE_FLAG = "early_polish_moved"
FIGHT_FLAG = "early_polish_fought"
ABILITY_FLAG = "early_polish_used_ability"
EXIT_RESCUE_FLAG = "early_polish_exit_rescue_seen"

# Mandatory early-road objectives get a physical destination so JOURNEY can
# recover a player from wherever they wandered using the live Waymap pathfinder.
# Keys are stable content IDs on purpose: this guidance layer should not create
# import cycles between every region it can route through.
JOURNEY_STEP_TARGETS: dict[tuple[str, str], tuple[str, str]] = {
    # Waymeet
    ("waymeet_roads_meet_here", "talk_marshal"): ("waymeet_crossroads", "Waymeet Crossroads"),
    ("waymeet_roads_meet_here", "inspect_broken_mile"): ("waymeet_broken_mile", "the Broken Mile"),
    ("waymeet_roads_meet_here", "reach_gloam"): ("waymeet_gloam_mouth", "Gloam Mouth"),
    ("waymeet_roads_meet_here", "inspect_gloam"): ("waymeet_gloam_mouth", "Gloam Mouth"),
    ("waymeet_roads_meet_here", "return_marshal"): ("waymeet_crossroads", "Waymeet Crossroads"),
    # Gloamworks
    ("gloamworks_below_the_sealed_door", "talk_surveyor"): ("waymeet_gloam_mouth", "Gloam Mouth"),
    ("gloamworks_below_the_sealed_door", "enter_works"): ("gloamworks_entry_cage", "Gloamworks Entry Cage"),
    ("gloamworks_below_the_sealed_door", "read_fault"): ("gloamworks_glass_fault", "Glass Fault"),
    ("gloamworks_below_the_sealed_door", "defeat_brake_saint"): ("gloamworks_brake_chapel", "Brake Chapel"),
    ("gloamworks_below_the_sealed_door", "defeat_mother_sparks"): ("gloamworks_hollow_dynamo", "Hollow Dynamo"),
    ("gloamworks_below_the_sealed_door", "sync_seals"): ("gloamworks_twin_seal_vestibule", "Twin-Seal Vestibule"),
    ("gloamworks_below_the_sealed_door", "defeat_regent"): ("gloamworks_buried_court", "Buried Court"),
    ("gloamworks_below_the_sealed_door", "return_surveyor"): ("waymeet_gloam_mouth", "Gloam Mouth"),
    # Greywake
    ("greywake_after_the_gloam", "reach_camp"): ("greywake_three_banner_camp", "Three-Banner Camp"),
    ("greywake_after_the_gloam", "inspect_heath"): ("greywake_heath", "Greywake Heath"),
    ("greywake_after_the_gloam", "inspect_orchard"): ("greywake_resonant_orchard", "Resonant Orchard"),
    ("greywake_after_the_gloam", "inspect_riftfield"): ("greywake_riftfield", "Riftfield"),
    ("greywake_after_the_gloam", "return_camp"): ("greywake_three_banner_camp", "Three-Banner Camp"),
    ("greywake_three_claims", "hear_roadwarden"): ("greywake_warden_post", "Roadwarden Post"),
    ("greywake_three_claims", "hear_ledger"): ("greywake_ledger_cut", "Ledger Cut"),
    ("greywake_three_claims", "hear_lantern"): ("greywake_lantern_hospice", "Lantern Hospice"),
    ("greywake_three_claims", "pledge"): ("greywake_three_banner_camp", "Three-Banner Camp"),
    ("greywake_bell_below_wind", "rally"): ("greywake_signal_hill", "Signal Hill"),
    ("greywake_bell_below_wind", "break_surge"): ("greywake_signal_hill", "Signal Hill"),
    ("greywake_bell_below_wind", "report"): ("greywake_three_banner_camp", "Three-Banner Camp"),
    # Sablewater / Drowned Tollhouse
    ("sablewater_low_water_old_debts", "talk_ferrymaster"): ("sablewater_north_ferry", "North Ferry"),
    ("sablewater_low_water_old_debts", "inspect_levee"): ("sablewater_broken_levee", "Broken Levee"),
    ("sablewater_low_water_old_debts", "inspect_chain"): ("sablewater_willow_ferry", "Willow Ferry"),
    ("sablewater_low_water_old_debts", "return_ferrymaster"): ("sablewater_north_ferry", "North Ferry"),
    ("sablewater_toll_nobody_owes", "inspect_marker"): ("sablewater_old_customs_road", "Old Customs Road"),
    ("sablewater_toll_nobody_owes", "inspect_gate"): ("sablewater_drowned_tollhouse_mouth", "Drowned Tollhouse Mouth"),
    ("sablewater_toll_nobody_owes", "talk_diver"): ("sablewater_drowned_tollhouse_mouth", "Drowned Tollhouse Mouth"),
    ("drowned_tollhouse_price_of_crossing", "defeat_warden"): ("drowned_tollhouse_sluice_chamber", "Sluice Chamber"),
    ("drowned_tollhouse_price_of_crossing", "present_seals"): ("drowned_tollhouse_brass_tribunal", "Brass Tribunal"),
    ("drowned_tollhouse_price_of_crossing", "defeat_auditor"): ("drowned_tollhouse_brass_tribunal", "Brass Tribunal"),
    ("drowned_tollhouse_price_of_crossing", "open_sluice"): ("drowned_tollhouse_collector_well", "Collector's Well"),
    # Veyra arrival and faction service
    ("veyra_first_day", "reach_crossing"): ("veyra_grand_crossing", "Grand Crossing"),
    ("veyra_first_day", "visit_market"): ("veyra_brassmarket", "Brassmarket"),
    ("veyra_first_day", "visit_vault"): ("veyra_keyhouse_vault", "Keyhouse Vault"),
    ("veyra_first_day", "visit_trainers"): ("veyra_five_ways_yard", "Five Ways Yard"),
    ("veyra_first_day", "read_board"): ("veyra_notice_hall", "Notice Hall"),
    ("veyra_first_day", "report_steward"): ("veyra_civic_steps", "Civic Steps"),
    ("veyra_faction_service", "roadwarden_field"): ("veyra_grand_crossing", "Grand Crossing"),
    ("veyra_faction_service", "ledger_field"): ("veyra_brassmarket", "Brassmarket"),
    ("veyra_faction_service", "lantern_water"): ("veyra_north_waterworks", "North Waterworks"),
    ("veyra_faction_service", "lantern_notice"): ("veyra_notice_hall", "Notice Hall"),
    # Underclock
    ("veyra_city_between_ticks", "read_cycle"): ("underclock_master_gauge_hall", "Master Gauge Hall"),
    ("veyra_city_between_ticks", "cross_pistons"): ("underclock_piston_gallery", "Piston Gallery"),
    ("veyra_city_between_ticks", "cross_steam"): ("underclock_steam_throat", "Steam Throat"),
    ("veyra_city_between_ticks", "cross_teeth"): ("underclock_walking_teeth", "Walking Teeth"),
    ("veyra_city_between_ticks", "calibrate_governor"): ("underclock_governor_gallery", "Governor Gallery"),
    ("veyra_city_between_ticks", "engage_governor"): ("underclock_governor_gallery", "Governor Gallery"),
    ("veyra_city_between_ticks", "defeat_governor"): ("underclock_governor_gallery", "Governor Gallery"),
    ("veyra_city_between_ticks", "restart_lift"): ("underclock_minute_chamber", "Minute Chamber"),
    # Gravewatch
    ("gravewatch_the_dead_garrison", "report_sergeant"): ("gravewatch_river_mile", "Gravewatch River Mile"),
    ("gravewatch_the_dead_garrison", "enter_keep"): ("gravewatch_broken_barbican", "Broken Barbican"),
    ("gravewatch_the_dead_garrison", "defeat_captain"): ("gravewatch_courtyard_of_standards", "Courtyard of Standards"),
    ("gravewatch_the_dead_garrison", "silence_chapel"): ("gravewatch_bell_vestry", "Bell Vestry"),
    ("gravewatch_the_dead_garrison", "open_inner_gate"): ("gravewatch_inner_portcullis", "Inner Portcullis"),
    ("gravewatch_the_dead_garrison", "defeat_castellan"): ("gravewatch_great_hall", "Great Hall"),
    ("gravewatch_the_dead_garrison", "light_beacon"): ("gravewatch_castellans_map_room", "Castellan's Map Room"),
}


RACE_VERB_FLAVOR: dict[str, str] = {
    "human": "LOOK at the street, question people, and follow the gate roads; civic life is part of the tutorial.",
    "forest_elf": "Read the forest itself: LOOK, LISTEN, EXAMINE, and then follow the path the signs justify.",
    "moon_elf": "Compare viewpoints before acting: LOOK, EXAMINE, TALK, and move only when the route makes sense.",
    "dwarf": "Treat the city like a worksite: LOOK, EXAMINE gauges or machinery, TALK to the responsible worker, then follow posted routes.",
    "goblin": "Treat everything as potentially useful: LOOK, EXAMINE, TALK, and follow the marked salvage lanes instead of guessing.",
    "troll": "Read the land before forcing it: LOOK, EXAMINE, LISTEN, then move by the safe trail you have actually found.",
    "undead": "Start with evidence: LOOK, LISTEN, EXAMINE, TALK, and decide what deserves obedience before you move on.",
    "sporekin": "Notice the shared signs without surrendering judgment: LOOK, LISTEN, EXAMINE, then choose the path yourself.",
}


def _normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def _rows(value) -> list[dict]:
    rows: list[dict] = []
    for row in value or ():
        if isinstance(row, dict):
            rows.append(row)
            continue
        try:
            rows.append(dict(row))
        except (TypeError, ValueError):
            continue
    return rows


def _character_flags(session) -> set[str]:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_flags"):
        return set()
    try:
        return set(database.list_flags(character.id))
    except Exception:
        return set()


def _grant(session, flag: str) -> None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "grant_flag"):
        return
    database.grant_flag(character.id, flag)


def _local_quest_prefixes(room_key: str) -> tuple[str, ...]:
    if room_key.startswith("greywake_"):
        return ("greywake_",)
    if room_key.startswith("sablewater_"):
        return ("sablewater_", "drowned_tollhouse_")
    if room_key.startswith("drowned_tollhouse_"):
        return ("drowned_tollhouse_", "sablewater_")
    if room_key.startswith("veyra_"):
        return ("veyra_",)
    if room_key.startswith("underclock_"):
        return ("veyra_city_",)
    if room_key.startswith("gravewatch_"):
        return ("gravewatch_",)
    if room_key.startswith("gloamworks_"):
        return ("gloamworks_", "waymeet_")
    if room_key.startswith("waymeet_"):
        return ("waymeet_", "adventure_", "gloamworks_")
    return ()


def _active_objective(session) -> tuple[str, str] | None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_quests"):
        return None
    level = int(getattr(character, "level", 1) or 1)
    eligible: list[tuple[dict, object]] = []
    for row in _rows(database.list_quests(character.id)):
        if row.get("status") != "active":
            continue
        definition = QUESTS_BY_KEY.get(str(row.get("quest_key") or ""))
        if definition is None or int(getattr(definition, "minimum_level", 1) or 1) > level:
            continue
        eligible.append((row, definition))

    local_prefixes = _local_quest_prefixes(str(getattr(character, "current_room", "") or ""))
    if local_prefixes:
        eligible.sort(
            key=lambda item: 0
            if str(item[0].get("quest_key") or "").startswith(local_prefixes)
            else 1
        )

    for row, definition in eligible:
        objective = definition.objective_for_step(row.get("current_step")) or "Continue the current quest."
        return definition.name, objective
    return None


def _active_objective_for_keys(session, quest_keys: tuple[str, ...]) -> tuple[str, str] | None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_quests"):
        return None
    level = int(getattr(character, "level", 1) or 1)
    by_key = {
        str(row.get("quest_key") or ""): row
        for row in _rows(database.list_quests(character.id))
        if row.get("status") == "active"
    }
    for quest_key in quest_keys:
        row = by_key.get(quest_key)
        if row is None:
            continue
        definition = QUESTS_BY_KEY.get(quest_key)
        if definition is None or int(getattr(definition, "minimum_level", 1) or 1) > level:
            continue
        objective = definition.objective_for_step(row.get("current_step")) or "Continue the current quest."
        return definition.name, objective
    return None


def _live_route_hint(session, destination_key: str, destination_name: str) -> str:
    character = getattr(session, "character", None)
    if character is None:
        return f"Destination: {destination_name}."
    start = str(getattr(character, "current_room", "") or "")
    if not start:
        return f"Destination: {destination_name}."

    # Reuse the same live passability-aware pathfinder as marked waymaps. This
    # keeps JOURNEY aligned with final topology normalization, gates, doors,
    # weather and character flags instead of duplicating compass directions.
    from mud.room_runtime import WORLD
    from mud.waymaps import shortest_route

    route = shortest_route(WORLD, session, start, destination_key)
    if route is None:
        return f"Destination: {destination_name}. No fully traversable route is visible from here yet."
    if not route:
        return f"You are already at {destination_name}."
    return f"Route from here to {destination_name}: " + " -> ".join(direction.upper() for direction in route) + "."


def _active_journey_row(session, quest_keys: tuple[str, ...]) -> tuple[str, str, str, str] | None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "list_quests"):
        return None
    level = int(getattr(character, "level", 1) or 1)
    by_key = {
        str(row.get("quest_key") or ""): row
        for row in _rows(database.list_quests(character.id))
        if row.get("status") == "active"
    }
    for quest_key in quest_keys:
        row = by_key.get(quest_key)
        if row is None:
            continue
        definition = QUESTS_BY_KEY.get(quest_key)
        if definition is None or int(getattr(definition, "minimum_level", 1) or 1) > level:
            continue
        step = str(row.get("current_step") or "")
        objective = definition.objective_for_step(step) or "Continue the current quest."
        return quest_key, step, definition.name, objective
    return None


def _journey_target_for_step(session, quest_key: str, step: str) -> tuple[str, str] | None:
    # A few objectives have a destination determined by prior choices or which
    # sub-objective remains. Resolve those from persistent flags first.
    flags = _character_flags(session)
    if quest_key == "drowned_tollhouse_price_of_crossing" and step == "collect_seals":
        if "drowned_archive_seal_found" not in flags:
            return "drowned_tollhouse_flooded_archive", "Flooded Archive"
        if "drowned_vault_seal_found" not in flags:
            return "drowned_tollhouse_coin_vault", "Coin Vault"
        return "drowned_tollhouse_magistrate_room", "Magistrate's Room"
    if quest_key == "veyra_faction_service" and step in {"report_office", "return_office"}:
        if "greywake_support_roadwarden" in flags:
            return "veyra_roadwarden_house", "Roadwarden House"
        if "greywake_support_deep_ledger" in flags:
            return "veyra_deep_ledger_exchange", "Deep Ledger Exchange"
        if "greywake_support_lantern_oath" in flags:
            return "veyra_lantern_court", "Lantern Court"
    return JOURNEY_STEP_TARGETS.get((quest_key, step))


def _journey_step_extra(quest_key: str, step: str) -> str:
    if quest_key == "greywake_bell_below_wind" and step == "break_surge":
        return " From Signal Hill, NORTH reaches the Heath, SOUTH the Sunk Causeway, and EAST Riftfield; Riftlings can surface at all three event sites."
    if quest_key == "gloamworks_below_the_sealed_door" and step == "sync_seals":
        return " A lone explorer can HOLD LEFT SEAL then HOLD RIGHT SEAL using the maintenance stays; a second explorer may operate the opposite plate instead."
    if quest_key == "drowned_tollhouse_price_of_crossing" and step == "collect_seals":
        return " JOURNEY routes to the next seal you have not recovered yet."
    return ""


def _shared_journey_line(session, quest_keys: tuple[str, ...]) -> str | None:
    active = _active_journey_row(session, quest_keys)
    if active is None:
        return None
    quest_key, step, name, objective = active
    target = _journey_target_for_step(session, quest_key, step)
    route = ""
    if target is not None:
        route = " " + _live_route_hint(session, target[0], target[1])
    return f"\r\nMain journey - {name}: {objective}{route}{_journey_step_extra(quest_key, step)}\r\n"


def _journey_text(session) -> str:
    character = getattr(session, "character", None)
    if character is None:
        return "\r\nNo character is active.\r\n"

    # Imported lazily because this guidance layer is also used by isolated early-game tests.
    # In production these modules are fully assembled before a player can type JOURNEY.
    from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
    from mud.greywake_march import (
        AFTER_GLOAM_QUEST_KEY,
        BELL_BELOW_WIND_QUEST_KEY,
        GREYWAKE_CHAIN_COMPLETE_FLAG,
        GREYWAKE_THREE_BANNER_KEY,
        THREE_CLAIMS_QUEST_KEY,
    )
    from mud.sablewater_reach import (
        DROWNED_ENTRY_KEY,
        DROWNED_TOLLHOUSE_COMPLETE_FLAG,
        LOW_WATER_QUEST_KEY,
        PRICE_OF_CROSSING_QUEST_KEY,
        SABLEWATER_INTRO_COMPLETE_FLAG,
        SABLEWATER_NORTH_FERRY_KEY,
        TOLLHOUSE_UNLOCKED_FLAG,
        TOLL_NOBODY_OWES_QUEST_KEY,
    )
    from mud.veyra_city import (
        VEYRA_ARRIVAL_QUEST_KEY,
        VEYRA_FACTION_RANK_FLAG,
        VEYRA_FACTION_SERVICE_QUEST_KEY,
        VEYRA_GATE_WARD_KEY,
        VEYRA_RESIDENT_FLAG,
    )
    from mud.veyra_underclock import UNDERCLOCK_COMPLETE_FLAG, UNDERCLOCK_INTAKE_KEY, UNDERCLOCK_QUEST_KEY
    from mud.gravewatch_keep import GRAVEWATCH_COMPLETE_FLAG, GRAVEWATCH_QUEST_KEY, GRAVEWATCH_RIVER_MILE_KEY

    level = int(getattr(character, "level", 1) or 1)
    flags = _character_flags(session)
    greywake_quests = (AFTER_GLOAM_QUEST_KEY, THREE_CLAIMS_QUEST_KEY, BELL_BELOW_WIND_QUEST_KEY)
    sablewater_quests = (LOW_WATER_QUEST_KEY, TOLL_NOBODY_OWES_QUEST_KEY, PRICE_OF_CROSSING_QUEST_KEY)

    if level > EARLY_GAME_MAX_LEVEL:
        return (
            "\r\nJOURNEY currently covers the opening shared road through level 10. "
            "Use GOALS for your current objective or JOURNAL for all active quests.\r\n"
        )

    if GLOAMWORKS_COMPLETE_FLAG not in flags:
        line = _shared_journey_line(session, ("waymeet_roads_meet_here", "gloamworks_below_the_sealed_door"))
        if line is not None:
            return line
        return (
            "\r\nMain journey - Waymeet and Gloamworks: use GOALS for the current local objective and JOURNEY again after accepting the Waymeet or Gloamworks quest. "
            "After Gloamworks, the eastern road from Gloam Mouth opens into Greywake.\r\n"
        )

    if GREYWAKE_CHAIN_COMPLETE_FLAG not in flags:
        line = _shared_journey_line(session, greywake_quests)
        if line is not None:
            return line
        route = _live_route_hint(session, GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp")
        return (
            "\r\nMain journey - Greywake March: " + route + " "
            "At Three-Banner Camp, TALK CAPTAIN.\r\n"
        )

    if level < 8:
        line = _shared_journey_line(session, (LOW_WATER_QUEST_KEY, TOLL_NOBODY_OWES_QUEST_KEY))
        if line is not None:
            return line
        if SABLEWATER_INTRO_COMPLETE_FLAG not in flags:
            route = _live_route_hint(session, SABLEWATER_NORTH_FERRY_KEY, "North Ferry")
            return (
                "\r\nMain journey - Sablewater Reach: " + route + " "
                "At North Ferry, TALK FERRYMASTER. This is the level 6-7 road while Veyra remains ahead.\r\n"
            )
        if TOLLHOUSE_UNLOCKED_FLAG not in flags:
            return (
                "\r\nMain journey - Sablewater Reach: continue south and east through the floodplain toward Old Customs Road. "
                "Follow A Toll Nobody Owes until the Drowned Tollhouse descent is opened.\r\n"
            )
        return (
            "\r\nMain journey - Veyra approach: you have opened the Drowned Tollhouse. Keep working the Greywake/Sablewater roads until level 8; "
            "then return to Veyra Outer Gate and go EAST into the city.\r\n"
        )

    if VEYRA_RESIDENT_FLAG not in flags:
        line = _shared_journey_line(session, (VEYRA_ARRIVAL_QUEST_KEY,))
        if line is not None:
            return line
        route = _live_route_hint(session, VEYRA_GATE_WARD_KEY, "Veyra Gate Ward")
        return (
            "\r\nMain journey - Veyra: " + route + " "
            "Once inside the Gate Ward, follow the arrival tour until you receive a Resident Chit.\r\n"
        )

    if VEYRA_FACTION_RANK_FLAG not in flags:
        line = _shared_journey_line(session, (VEYRA_FACTION_SERVICE_QUEST_KEY,))
        if line is not None:
            return line

    if DROWNED_TOLLHOUSE_COMPLETE_FLAG not in flags:
        current_room = str(getattr(character, "current_room", "") or "")
        if current_room.startswith("veyra_") and TOLLHOUSE_UNLOCKED_FLAG in flags:
            active = _active_objective_for_keys(session, (PRICE_OF_CROSSING_QUEST_KEY,))
            objective = (
                f" Current objective: {active[1]}"
                if active is not None
                else ""
            )
            route = _live_route_hint(session, DROWNED_ENTRY_KEY, "Drowned Tollhouse entry")
            return (
                "\r\nMain journey - Drowned Tollhouse: " + route
                + objective
                + "\r\n"
            )
        line = _shared_journey_line(session, sablewater_quests)
        if line is not None:
            return line
        if TOLLHOUSE_UNLOCKED_FLAG in flags:
            route = _live_route_hint(session, DROWNED_ENTRY_KEY, "Drowned Tollhouse entry")
            return (
                "\r\nMain journey - Drowned Tollhouse: " + route + " "
                "The Price of Crossing carries the shared road through the level 8-9 stretch.\r\n"
            )
        return (
            "\r\nMain journey - Sablewater Reach: leave Veyra south for North Ferry and TALK FERRYMASTER. "
            "The floodplain and Drowned Tollhouse carry the shared road toward level 10.\r\n"
        )

    if level < 10 and UNDERCLOCK_COMPLETE_FLAG not in flags:
        line = _shared_journey_line(session, (UNDERCLOCK_QUEST_KEY,))
        if line is not None:
            return line
        route = _live_route_hint(session, UNDERCLOCK_INTAKE_KEY, "Underclock Intake Stair")
        return (
            "\r\nMain journey - The City Between Ticks: " + route + " "
            "Once the quest starts, GOALS gives the current machine step.\r\n"
        )

    if level < 10 and GRAVEWATCH_COMPLETE_FLAG not in flags:
        line = _shared_journey_line(session, (GRAVEWATCH_QUEST_KEY,))
        if line is not None:
            return line
        route = _live_route_hint(session, GRAVEWATCH_RIVER_MILE_KEY, "Gravewatch River Mile")
        return (
            "\r\nMain journey - Gravewatch Keep: " + route + " "
            "At the River Mile, TALK SERGEANT. The Dead Garrison is the next full clear on the road to level 10.\r\n"
        )

    if level < 10:
        return (
            "\r\nMain journey - Level 10 approach: the shared Greywake, Sablewater, Underclock, and Gravewatch route is complete. "
            "Use HERITAGE for your level-8 origin story, then GOALS for any remaining level-appropriate objective; ordinary combat and city work can close any XP left by earlier optional choices.\r\n"
        )

    return (
        "\r\nMain journey - Level 10 reached: the opening shared road through Waymeet, Greywake, Sablewater, and Veyra is established. "
        "Use HERITAGE to finish your level-10 origin capstone if it remains active, then GOALS or JOURNAL for the roads beyond.\r\n"
    )


def _goal_text(session) -> str:
    active = _active_objective(session)
    if active is not None:
        name, objective = active
        return f"\r\nCurrent goal - {name}: {objective}\r\n"

    character = getattr(session, "character", None)
    if character is None:
        return "\r\nNo character is active.\r\n"
    if int(getattr(character, "level", 1) or 1) <= EARLY_GAME_MAX_LEVEL:
        loop = STARTER_RACE_LOOPS_BY_RACE.get(getattr(character, "race", None))
        flags = _character_flags(session)
        if loop is not None and loop.completion_flag not in flags:
            return f"\r\nCurrent goal - {loop.hook_name}: keep exploring your opening and follow the people, signs, and routes it introduces.\r\n"
        return "\r\nYou have no level-appropriate active quest objective right now. Type JOURNEY for the next step on the main shared road.\r\n"
    return "\r\nYou have no active quest objective right now. LOOK and EXITS will re-orient you; TALK to local people when you want another lead.\r\n"


def _early_context(session) -> PlayerRoomContext | None:
    character = getattr(session, "character", None)
    if character is None or int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
        return None
    return PlayerRoomContext(
        character_id=character.id,
        race_key=getattr(character, "race", "") or "",
        class_key=getattr(character, "character_class", "") or "",
        level=int(getattr(character, "level", 1) or 1),
        character_flags=frozenset(_character_flags(session)),
    )


def _visible_exit_hint(session, world) -> str | None:
    character = getattr(session, "character", None)
    context = _early_context(session)
    if character is None or context is None:
        return None
    view = world.build_view(getattr(character, "current_room", "") or "", context)
    if view is None or not view.exits:
        return None
    exits = ", ".join(exit_def.direction.upper() for exit_def in view.exits)
    return f"Available exits here: {exits}. Type EXITS any time to see them again."


def _successful(captured: list[str]) -> bool:
    text = "".join(captured).lower()
    return not any(
        marker in text
        for marker in (
            "unknown command",
            "you cannot go that way",
            "there are no authored exits",
            "that way is locked",
            "that way is closed",
        )
    )


def install_early_game_polish_runtime(player_session_class, world) -> None:
    """Keep levels 1-10 easy to read without flattening the game's depth."""
    if getattr(player_session_class, "_early_game_polish_runtime_installed", False):
        return

    if hasattr(player_session_class, "enter_character"):
        previous_enter = player_session_class.enter_character

        async def enter_character(self) -> None:
            await previous_enter(self)
            character = getattr(self, "character", None)
            if character is None or int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
                return
            if getattr(self, "_early_polish_flavor_shown", False):
                return
            race_key = getattr(character, "race", "") or ""
            flavor = RACE_VERB_FLAVOR.get(race_key)
            if flavor:
                await self.send(
                    f"\r\n{flavor}\r\n"
                    "Type GOALS whenever you forget what you were doing; it gives one current objective without spoiling the road ahead. "
                    "Type JOURNEY when you want the next step on the main shared progression road.\r\n"
                )
            self._early_polish_flavor_shown = True

        player_session_class.enter_character = enter_character

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            return
        normalized = _normalize(command)
        if normalized in GOAL_ALIASES:
            await self.send(_goal_text(self))
            return
        if normalized in JOURNEY_ALIASES:
            await self.send(_journey_text(self))
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")
        had_send = "send" in self.__dict__
        old_send = self.__dict__.get("send")
        real_send = self.send
        captured: list[str] = []

        async def replay_prompt(_text: str) -> str:
            return command

        async def capture_send(text: str) -> None:
            captured.append(text)
            await real_send(text)

        before_room = getattr(character, "current_room", None)
        self.prompt = replay_prompt
        self.send = capture_send
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)
            if had_send:
                self.send = old_send
            else:
                self.__dict__.pop("send", None)

        if int(getattr(character, "level", 1) or 1) > EARLY_GAME_MAX_LEVEL:
            return

        after_room = getattr(character, "current_room", None)
        ok = _successful(captured)
        if ok and normalized in {"look", "l"}:
            _grant(self, LOOK_FLAG)
        if before_room and after_room and before_room != after_room:
            _grant(self, MOVE_FLAG)
        if ok and (normalized.startswith("attack ") or normalized.startswith("kill ")):
            _grant(self, FIGHT_FLAG)
        if ok and (normalized.startswith("use ") or normalized.startswith("cast ") or normalized.startswith("nurture")):
            _grant(self, ABILITY_FLAG)

        if normalized in DIRECTION_COMMANDS and not ok:
            flags = _character_flags(self)
            if EXIT_RESCUE_FLAG not in flags:
                hint = _visible_exit_hint(self, world)
                if hint:
                    await real_send(f"\r\n{hint}\r\n")
                    _grant(self, EXIT_RESCUE_FLAG)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._early_game_polish_runtime_installed = True


def validate_level_ten_playability_contract(world, race_keys: tuple[str, ...], class_keys: tuple[str, ...]) -> None:
    """Fail fast if any launch race/class combination loses its basic 1-10 path."""
    problems: list[str] = []
    for race_key in race_keys:
        loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
        if loop is None:
            problems.append(f"{race_key}: no starter loop")
            continue
        scene = world.scene(loop.starting_room_key)
        if scene is None:
            problems.append(f"{race_key}: missing live start room {loop.starting_room_key}")
            continue
        for class_key in class_keys:
            context = PlayerRoomContext(1, race_key, class_key, 1, frozenset())
            view = world.build_view(loop.starting_room_key, context)
            if view is None or not view.exits:
                problems.append(f"{race_key}/{class_key}: start has no visible route")
                continue
            if not any(world.resolve_exit(loop.starting_room_key, exit_def.direction, context).allowed for exit_def in view.exits):
                problems.append(f"{race_key}/{class_key}: no walkable start exit")
            deity_key = "zerjz" if class_key == "priest" else None
            if not class_abilities_for_level(class_key, 10, deity_key):
                problems.append(f"{race_key}/{class_key}: no class kit at level 10")
    if problems:
        raise RuntimeError("Early-game playability contract failed: " + "; ".join(problems))
