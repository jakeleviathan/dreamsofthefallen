from __future__ import annotations

import mud.crafting as crafting
import mud.quests as quests
from mud.astralis_calendar import calendar_for_day
from mud.astralis_time import ASTRALIS_CLOCK
from mud.crafting import ItemDefinition
from mud.goblin_clans import (
    CLAN_DESCRIPTIONS,
    FLOODPICK_COPPERCAP,
    FLOODPICK_MIREHOOK,
    FLOODPICK_TINLEDGER,
    GOBLIN_WEIGHT_OF_A_MAP,
    clan_signal_counts,
    clan_signal_flag,
)
from mud.goblin_deep_mire import FLOODPICK_CLAN_NAMES, floodpick_control_text, floodpick_controller
from mud.goblin_return_loop import (
    GOBLIN_BOTTLEWIRE_RETURN_KEY,
    GOBLIN_RETURN_LOOP_DISCOVERED_FLAG,
    install_goblin_return_loop_content,
)
from mud.goblin_start import GOBLIN_BRASSGUT_MARKET_KEY, GOBLIN_LEDGER_HALL_KEY, GOBLIN_TINKER_ROW_KEY
from mud.goblin_swamp import GOBLIN_APOTHECARY_BLIND_KEY
from mud.quests import QuestDefinition


# ---------------------------------------------------------------------------
# Standing: remembered choices now provide information, not access locks.
# ---------------------------------------------------------------------------

TRUSTED_SIGNAL_THRESHOLD = 2


def clan_relationship_label(count: int) -> str:
    if count <= 0:
        return "Uncommitted"
    if count == 1:
        return "Recognized"
    if count == 2:
        return "Trusted"
    if count == 3:
        return "Known Associate"
    return "Frequent Ally"


def _signal_count(session, clan_key: str) -> int:
    assert session.character is not None
    return clan_signal_counts(session.database.list_flags(session.character.id))[clan_key]


def _recognized_line(session, clan_key: str) -> str:
    count = _signal_count(session, clan_key)
    if count >= TRUSTED_SIGNAL_THRESHOLD:
        return "You've done enough work around us that I don't need to explain every edge of the job."
    if count == 1:
        return "I've seen your name attached to one decision already. That is enough to know you listen before choosing."
    return "You haven't made a habit of backing us, but these are city jobs, not membership tests."


# ---------------------------------------------------------------------------
# Second-wave quest items and definitions
# ---------------------------------------------------------------------------

COPPERCAP_CALIBRATION_AMPOULE = ItemDefinition(
    "coppercap_calibration_ampoule",
    "Coppercap Calibration Ampoule",
    "A sealed reference ampoule containing a precisely standardized marsh extract. Its value is in being a known measurement, not a powerful potion.",
    "quest_item",
    tier=0,
)

TINLEDGER_MARKET_SLIP = ItemDefinition(
    "tinledger_market_slip",
    "Tinledger Market Slip",
    "A waxed note predicting short-term demand for Glassroot preparations among Dwarven freight crews. It is useful because it is early, not because it is secret.",
    "quest_item",
    tier=0,
)

FOLLOWUP_ITEMS = (COPPERCAP_CALIBRATION_AMPOULE, TINLEDGER_MARKET_SLIP)


GOBLIN_DRY_WAY_HOME = QuestDefinition(
    key="goblin_dry_way_home",
    name="A Dry Way Home",
    style="structured",
    description=(
        "Jex Mirehook wants a newly formalized highwater return route checked from the ground. After reading its marker system, decide whether to emphasize it as shared route infrastructure or register it with Tinledger as a commercial service corridor."
    ),
    objective_steps=(
        ("inspect_return_markers", "Use the deep-mire return loop and EXAMINE RETURN MARKERS at Bottlewire Return."),
        ("choose_route_use", "Choose POST RETURN ROUTE with Jex or REGISTER RETURN ROUTE with Snik."),
        ("complete", "You helped decide how Junk City talks about a useful new route home."),
    ),
)

GOBLIN_ONE_CLEAN_MEASURE = QuestDefinition(
    key="goblin_one_clean_measure",
    name="One Clean Measure",
    style="structured",
    description=(
        "Talla Coppercap sends a calibration ampoule to Pella's field bench. Decide whether the standardized measure should remain Coppercap reference property or stay at the public apothecary for any careful worker to compare against."
    ),
    objective_steps=(
        ("deliver_measure", "Carry the Coppercap Calibration Ampoule to Pella at the Apothecary Blind and TALK PELLA."),
        ("choose_measure", "Choose LEAVE MEASURE WITH PELLA or RETURN MEASURE TO TALLA."),
        ("return_measure", "Return to Talla in Tinker Row and use RETURN MEASURE TO TALLA."),
        ("complete", "You decided who should hold a reliable alchemical standard."),
    ),
)

GOBLIN_BEFORE_PRICE_MOVES = QuestDefinition(
    key="goblin_before_price_moves",
    name="Before the Price Moves",
    style="structured",
    description=(
        "Snik Tinledger has an early demand forecast for Glassroot preparations. Decide whether to complete the information trade with Hadrik Coilpress or give Talla Coppercap the same early warning so local apothecaries can prepare stock first."
    ),
    objective_steps=(
        ("choose_market_reader", "Choose DELIVER MARKET SLIP to Hadrik in Brassgut Market or SHOW MARKET SLIP TO TALLA in Tinker Row."),
        ("complete", "You decided who received useful market timing first."),
    ),
)

FOLLOWUP_QUESTS = (
    GOBLIN_DRY_WAY_HOME,
    GOBLIN_ONE_CLEAN_MEASURE,
    GOBLIN_BEFORE_PRICE_MOVES,
)


def install_goblin_clan_followup_content(world_service=None) -> None:
    install_goblin_return_loop_content(world_service)
    for item in FOLLOWUP_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for quest in FOLLOWUP_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _quest(session, definition: QuestDefinition):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, definition.key)


def _quest_completed(session, definition: QuestDefinition) -> bool:
    value = _quest(session, definition)
    return bool(value and value.get("status") == "completed")


def _base_clan_arc_complete(session) -> bool:
    return _quest_completed(session, GOBLIN_WEIGHT_OF_A_MAP)


def _consume_all(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _grant_signal(session, clan_key: str, reason: str) -> None:
    assert session.character is not None
    session.database.grant_flag(session.character.id, clan_signal_flag(clan_key, reason))


def _normalize_unique_item(session, item_key: str, should_have: bool) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if should_have:
        if quantity == 0:
            session.database.add_item(session.character.id, item_key, 1)
        elif quantity > 1:
            session.database.consume_item(session.character.id, item_key, quantity - 1)
    elif quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _reconcile_followups(session) -> None:
    if session.character is None:
        return

    measure = _quest(session, GOBLIN_ONE_CLEAN_MEASURE)
    measure_active = bool(
        measure
        and measure.get("status") == "active"
        and measure.get("current_step") in {"deliver_measure", "choose_measure", "return_measure"}
    )
    _normalize_unique_item(session, COPPERCAP_CALIBRATION_AMPOULE.key, measure_active)

    market = _quest(session, GOBLIN_BEFORE_PRICE_MOVES)
    market_active = bool(market and market.get("status") == "active")
    _normalize_unique_item(session, TINLEDGER_MARKET_SLIP.key, market_active)


# ---------------------------------------------------------------------------
# Quest-giver interactions
# ---------------------------------------------------------------------------


async def _talk_jex_followup(session) -> bool:
    if not _base_clan_arc_complete(session):
        return False
    assert session.character is not None
    quest = _quest(session, GOBLIN_DRY_WAY_HOME)
    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_DRY_WAY_HOME.key, "inspect_return_markers")
        await session.send(
            "\r\nJex hooks one thumb toward the swamp. 'The pump crews finally tied the old highwater catwalk into Bottlewire. It gives loaded gatherers a dry way back to Pella instead of walking the whole mire twice.'\r\n"
            f"'{_recognized_line(session, FLOODPICK_MIREHOOK)} Go read the return markers yourself. Then we decide whether the city posts it as shared route infrastructure or Tinledger registers the corridor as a service line.'\r\n"
            "New quest: A Dry Way Home.\r\n"
        )
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nJex taps the route board. 'The highwater return is settled for now. Useful path. Useful argument.'\r\n")
        return True
    objective = GOBLIN_DRY_WAY_HOME.objective_for_step(quest.get("current_step"))
    await session.send("\r\nJex asks about the highwater return.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_talla_followup(session) -> bool:
    if not _base_clan_arc_complete(session):
        return False
    assert session.character is not None
    quest = _quest(session, GOBLIN_ONE_CLEAN_MEASURE)
    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_ONE_CLEAN_MEASURE.key, "deliver_measure")
        session.database.add_item(session.character.id, COPPERCAP_CALIBRATION_AMPOULE.key, 1)
        await session.send(
            "\r\nTalla removes a tiny sealed ampoule from a padded box. 'This is not medicine. It is a known measure. Every batch we test against it tells us whether our instruments are lying.'\r\n"
            f"'{_recognized_line(session, FLOODPICK_COPPERCAP)} Take it to Pella. She can compare her field bench, then we decide whether the reference comes home or lives out there.'\r\n"
            "You receive a Coppercap Calibration Ampoule.\r\n"
            "New quest: One Clean Measure.\r\n"
        )
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nTalla gives a small professional nod. 'I remember where you decided the reference standard belongs.'\r\n")
        return True
    if quest.get("current_step") == "return_measure":
        await session.send("\r\nTalla holds out a padded hand. 'If the reference is coming home, use RETURN MEASURE TO TALLA.'\r\n")
        return True
    objective = GOBLIN_ONE_CLEAN_MEASURE.objective_for_step(quest.get("current_step"))
    if objective:
        await session.send("\r\nCurrent objective: " + objective + "\r\n")
    return True


async def _talk_snik_followup(session) -> bool:
    if not _base_clan_arc_complete(session):
        return False
    assert session.character is not None
    quest = _quest(session, GOBLIN_BEFORE_PRICE_MOVES)
    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_BEFORE_PRICE_MOVES.key, "choose_market_reader")
        session.database.add_item(session.character.id, TINLEDGER_MARKET_SLIP.key, 1)
        await session.send(
            "\r\nSnik slides over a waxed slip. 'Three Dwarven freight crews started asking about focus draughts in the same two-hour window. That means demand moves before the next carts do.'\r\n"
            f"'{_recognized_line(session, FLOODPICK_TINLEDGER)} Hadrik will pay attention if he sees this first. Talla will prepare local stock if she sees it first. Timing is the whole cargo.'\r\n"
            "You receive a Tinledger Market Slip.\r\n"
            "New quest: Before the Price Moves.\r\n"
        )
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nSnik taps the margin beside your name. 'Already learned who you think should see a moving price first.'\r\n")
        return True
    await session.send("\r\nSnik says, 'Hadrik in Brassgut or Talla in Tinker Row. Same information. Different first reader.'\r\n")
    return True


async def _talk_pella_followup(session) -> bool:
    if session.character is None:
        return False
    quest = _quest(session, GOBLIN_ONE_CLEAN_MEASURE)
    if not quest or quest.get("status") != "active":
        return False
    if quest.get("current_step") == "deliver_measure":
        session.database.advance_quest(session.character.id, GOBLIN_ONE_CLEAN_MEASURE.key, "choose_measure")
    if quest.get("current_step") in {"deliver_measure", "choose_measure"}:
        await session.send(
            "\r\nPella checks three field measures against the Coppercap ampoule and scratches a correction onto her bench scale. 'Useful standard. Now the political part.'\r\n"
            "Choose LEAVE MEASURE WITH PELLA so the public bench keeps the reference, or RETURN MEASURE TO TALLA so Coppercap retains it.\r\n"
        )
        return True
    return False


async def _talk_hadrik_followup(session) -> bool:
    if session.character is None:
        return False
    quest = _quest(session, GOBLIN_BEFORE_PRICE_MOVES)
    if not quest or quest.get("status") != "active":
        return False
    await session.send(
        "\r\nHadrik notices the Tinledger wax. 'A demand note? If Snik means me to have the early read, use DELIVER MARKET SLIP.'\r\n"
    )
    return True


# ---------------------------------------------------------------------------
# Choices and trusted information services
# ---------------------------------------------------------------------------


async def _handle_followup_choice(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "goblin":
        return False
    room = session.character.current_room

    route = _quest(session, GOBLIN_DRY_WAY_HOME)
    if route and route.get("status") == "active":
        if (
            route.get("current_step") == "inspect_return_markers"
            and room == GOBLIN_BOTTLEWIRE_RETURN_KEY
            and normalized in {"examine return markers", "look return markers", "search return markers", "examine markers", "look markers"}
        ):
            session.database.advance_quest(session.character.id, GOBLIN_DRY_WAY_HOME.key, "choose_route_use")
            await session.send(
                "\r\nThe marker code makes the shortcut's purpose clear: it is safer, drier, and maintained as an emergency way home. Mirehook's original hook-mark is still visible beneath newer blank registry tabs.\r\n"
                "Quest updated: A Dry Way Home. POST RETURN ROUTE with Jex or REGISTER RETURN ROUTE with Snik.\r\n"
            )
            return True
        if route.get("current_step") == "choose_route_use":
            if normalized in {"post return route", "post route", "mark route public"} and room == GOBLIN_BRASSGUT_MARKET_KEY:
                _grant_signal(session, FLOODPICK_MIREHOOK, "dry_way_public")
                session.database.complete_quest(session.character.id, GOBLIN_DRY_WAY_HOME.key)
                await session.send(
                    "\r\nJex nails a copy of the return-marker code onto the public route board. 'No ownership argument. If it gets you home dry, use it and report broken boards.'\r\n"
                    "Quest complete: A Dry Way Home. Mirehook remembers that you treated the shortcut as shared infrastructure.\r\n"
                )
                return True
            if normalized in {"register return route", "register route", "list route service"} and room == GOBLIN_LEDGER_HALL_KEY:
                _grant_signal(session, FLOODPICK_TINLEDGER, "dry_way_registry")
                session.database.complete_quest(session.character.id, GOBLIN_DRY_WAY_HOME.key)
                await session.send(
                    "\r\nSnik enters the highwater corridor into the service registry for couriers and freight crews while leaving ordinary passage open. 'Public road, commercial knowledge. Those can coexist.'\r\n"
                    "Quest complete: A Dry Way Home. Tinledger remembers that you formalized the route as useful trade infrastructure.\r\n"
                )
                return True

    measure = _quest(session, GOBLIN_ONE_CLEAN_MEASURE)
    if measure and measure.get("status") == "active":
        if measure.get("current_step") == "choose_measure" and room == GOBLIN_APOTHECARY_BLIND_KEY:
            if normalized in {"leave measure with pella", "leave measure", "leave ampoule"}:
                _grant_signal(session, FLOODPICK_MIREHOOK, "public_measure")
                session.database.complete_quest(session.character.id, GOBLIN_ONE_CLEAN_MEASURE.key)
                _consume_all(session, COPPERCAP_CALIBRATION_AMPOULE.key)
                session.database.grant_flag(session.character.id, "goblin_public_calibration_standard")
                await session.send(
                    "\r\nPella fits the ampoule into a padded slot beside the public bench scale. 'Then anyone careful enough to compare can know whether their measure is drifting.'\r\n"
                    "Quest complete: One Clean Measure. Route workers remember that you left the standard in public hands.\r\n"
                )
                return True
            if normalized in {"return measure to talla", "return measure", "return ampoule"}:
                session.database.advance_quest(session.character.id, GOBLIN_ONE_CLEAN_MEASURE.key, "return_measure")
                await session.send("\r\nYou decide the reference should remain Coppercap property. Return it to Talla in Tinker Row.\r\n")
                return True
        if measure.get("current_step") == "return_measure" and room == GOBLIN_TINKER_ROW_KEY and normalized in {"return measure to talla", "return measure", "return ampoule"}:
            _grant_signal(session, FLOODPICK_COPPERCAP, "kept_standard")
            session.database.complete_quest(session.character.id, GOBLIN_ONE_CLEAN_MEASURE.key)
            _consume_all(session, COPPERCAP_CALIBRATION_AMPOULE.key)
            await session.send(
                "\r\nTalla nests the ampoule back into its padded case. 'A standard only stays a standard if somebody is accountable for it.'\r\n"
                "Quest complete: One Clean Measure. Coppercap remembers that you returned the reference to its keeper.\r\n"
            )
            return True

    market = _quest(session, GOBLIN_BEFORE_PRICE_MOVES)
    if market and market.get("status") == "active":
        if normalized in {"deliver market slip", "deliver slip", "give market slip"} and room == GOBLIN_BRASSGUT_MARKET_KEY:
            _grant_signal(session, FLOODPICK_TINLEDGER, "early_market")
            session.database.complete_quest(session.character.id, GOBLIN_BEFORE_PRICE_MOVES.key)
            _consume_all(session, TINLEDGER_MARKET_SLIP.key)
            await session.send(
                "\r\nHadrik reads the forecast twice, then closes his order book long enough to revise the next freight request. 'Early information is worth more than late certainty.'\r\n"
                "Quest complete: Before the Price Moves. Tinledger remembers that you completed the timing trade.\r\n"
            )
            return True
        if normalized in {"show market slip to talla", "show market slip", "show slip to talla"} and room == GOBLIN_TINKER_ROW_KEY:
            _grant_signal(session, FLOODPICK_COPPERCAP, "local_supply_warning")
            session.database.complete_quest(session.character.id, GOBLIN_BEFORE_PRICE_MOVES.key)
            _consume_all(session, TINLEDGER_MARKET_SLIP.key)
            await session.send(
                "\r\nTalla reads the demand forecast and immediately begins counting clean vials. 'Then local compounders prepare before the freight buyers empty the shelves.'\r\n"
                "Quest complete: Before the Price Moves. Coppercap remembers that you gave local apothecaries the first warning.\r\n"
            )
            return True

    return False


async def _ask_jex_routes(session) -> bool:
    if _signal_count(session, FLOODPICK_MIREHOOK) < TRUSTED_SIGNAL_THRESHOLD:
        await session.send("\r\nJex says, 'Keep showing me how you read a route. I save the detailed crew briefings for people I've seen make more than one useful call.'\r\n")
        return True
    flags = session.database.list_flags(session.character.id)
    shortcut = (
        "You've discovered the Highwater/Bottlewire return; it can be taken north from the Apothecary Blind."
        if GOBLIN_RETURN_LOOP_DISCOVERED_FLAG in flags
        else "The Highwater return starts east from Old Pump Track. Take it once and you'll learn the reverse marker code."
    )
    await session.send("\r\n--- Mirehook Route Briefing ---\r\n" + shortcut + "\r\n" + floodpick_control_text() + "\r\n")
    return True


async def _ask_talla_reagents(session) -> bool:
    if _signal_count(session, FLOODPICK_COPPERCAP) < TRUSTED_SIGNAL_THRESHOLD:
        await session.send("\r\nTalla says, 'I give exact harvesting thresholds to people whose judgment I've seen more than once. Bring me another good decision.'\r\n")
        return True
    await session.send(
        "\r\n--- Coppercap Reagent Notes ---\r\n"
        "Bogmint: Herbalism 6, Siltknife Boardwalk.\r\n"
        "Fen Resin: Herbalism 7, Resin Fen.\r\n"
        "Mirecap Spores: Herbalism 8, Toadbell Hollow.\r\n"
        "Glassroot: Herbalism 10, Drowned Glasshouse conservatory after restoring light to the beds.\r\n"
        "Talla adds, 'Knowing the threshold is not the same as harvesting carefully.'\r\n"
    )
    return True


async def _ask_snik_claims(session) -> bool:
    if _signal_count(session, FLOODPICK_TINLEDGER) < TRUSTED_SIGNAL_THRESHOLD:
        await session.send("\r\nSnik says, 'Current claims are public. Forecasts are work. Give me another reason to put you on the early-information list.'\r\n")
        return True
    calendar = ASTRALIS_CLOCK.now().calendar
    await session.send("\r\n--- Tinledger Claim Forecast ---\r\n" + floodpick_control_text(calendar) + "\r\n")
    controller = floodpick_controller(calendar)
    if controller is None:
        await session.send("No spring Floodpick rotation is active, so there is no near-term claim handoff to forecast.\r\n")
        return True
    days_to_review = 3 - ((calendar.season_day - 1) % 3)
    next_date = calendar_for_day(calendar.absolute_day + days_to_review)
    next_controller = floodpick_controller(next_date)
    if next_controller is None:
        await session.send(f"The current claim reaches the end of spring in {days_to_review} day(s); no next spring holder follows it this year.\r\n")
    else:
        await session.send(
            f"Next review: about {days_to_review} Astralis day(s). If the normal rotation holds, {FLOODPICK_CLAN_NAMES[next_controller]} takes the next block.\r\n"
        )
    return True


async def _show_clan_standing(session) -> None:
    counts = clan_signal_counts(session.database.list_flags(session.character.id))
    await session.send("\r\n--- Junk City Clan Signals ---\r\n")
    for key in (FLOODPICK_MIREHOOK, FLOODPICK_COPPERCAP, FLOODPICK_TINLEDGER):
        name, description = CLAN_DESCRIPTIONS[key]
        count = counts[key]
        await session.send(f"{name}: {count} signal(s) — {clan_relationship_label(count)}. {description}\r\n")
    await session.send(
        "Signals are remembered choices, not exclusive membership. At 2 signals, a contact considers you Trusted and shares a specialist briefing; no quest, room, recipe, or profession is locked behind that status.\r\n"
        "Trusted briefings: ASK JEX ABOUT ROUTES, ASK TALLA ABOUT REAGENTS, ASK SNIK ABOUT CLAIMS.\r\n"
    )
    await session.send(floodpick_control_text() + "\r\n")


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def install_goblin_clan_followup_runtime(player_session_class, world_service) -> None:
    install_goblin_clan_followup_content(world_service)
    if getattr(player_session_class, "_goblin_clan_followup_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is not None and self.character.race == "goblin":
            _reconcile_followups(self)

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "goblin":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"clans", "clan", "clan standing", "clan standings", "politics"}:
            await _show_clan_standing(self)
            return

        if normalized in {"ask jex about routes", "ask jex routes", "route briefing"} and self.character.current_room == GOBLIN_BRASSGUT_MARKET_KEY:
            await _ask_jex_routes(self)
            return
        if normalized in {"ask talla about reagents", "ask talla reagents", "reagent briefing"} and self.character.current_room == GOBLIN_TINKER_ROW_KEY:
            await _ask_talla_reagents(self)
            return
        if normalized in {"ask snik about claims", "ask snik claims", "claim forecast"} and self.character.current_room == GOBLIN_LEDGER_HALL_KEY:
            await _ask_snik_claims(self)
            return

        if await _handle_followup_choice(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            room = self.character.current_room
            if room == GOBLIN_BRASSGUT_MARKET_KEY and target in {"jex", "jex mirehook", "mirehook", "route foreman"}:
                if await _talk_jex_followup(self):
                    return
            if room == GOBLIN_TINKER_ROW_KEY and target in {"talla", "talla coppercap", "coppercap", "apothecary"}:
                if await _talk_talla_followup(self):
                    return
            if room == GOBLIN_LEDGER_HALL_KEY and target in {"snik", "snik tinledger", "tinledger", "broker"}:
                if await _talk_snik_followup(self):
                    return
            if room == GOBLIN_APOTHECARY_BLIND_KEY and target in {"pella", "pella mireglass", "mireglass"}:
                if await _talk_pella_followup(self):
                    return
            if room == GOBLIN_BRASSGUT_MARKET_KEY and target in {"hadrik", "hadrik coilpress", "dwarf", "dwarven trader", "trade factor"}:
                if await _talk_hadrik_followup(self):
                    return

        had_instance_prompt = "prompt" in self.__dict__
        prior_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await previous_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = prior_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"} and _base_clan_arc_complete(self):
            await self.send(
                "Goblin follow-up politics: each clan contact has one more small choice quest. At 2 clan signals, specialist briefings become available through ASK JEX ABOUT ROUTES, ASK TALLA ABOUT REAGENTS, or ASK SNIK ABOUT CLAIMS. These standings never lock other clans.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_clan_followup_runtime_installed = True
