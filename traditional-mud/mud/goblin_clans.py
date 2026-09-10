from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.goblin_deep_mire import (
    FLOODPICK_CLAN_NAMES,
    FLOODPICK_COPPERCAP,
    FLOODPICK_MIREHOOK,
    FLOODPICK_TINLEDGER,
    GOBLIN_SOURREED_TERRACE_KEY,
    floodpick_controller,
    floodpick_control_text,
    install_goblin_deep_mire_content,
)
from mud.goblin_outer_route import GOBLIN_OUTER_ROUTE_COMPLETE_FLAG
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_START_ROOM_KEY,
    GOBLIN_TINKER_ROW_KEY,
)
from mud.goblin_swamp import GOBLIN_APOTHECARY_BLIND_KEY
from mud.quests import QuestDefinition
from mud.world import NpcDefinition, RoomDefinition


# ---------------------------------------------------------------------------
# Three early political groups. These are not exclusive player factions.
# ---------------------------------------------------------------------------

CLAN_DESCRIPTIONS = {
    FLOODPICK_MIREHOOK: (
        "Mirehook Clan",
        "Route cutters, herb gatherers, piling crews, and field workers who prefer useful knowledge to circulate among the people actually doing the work.",
    ),
    FLOODPICK_COPPERCAP: (
        "Coppercap Family",
        "Apothecaries and compounders who treat a reliable formula as skilled property: worth teaching carefully, trading deliberately, and protecting from sloppy copying.",
    ),
    FLOODPICK_TINLEDGER: (
        "Tinledger Clan",
        "Brokers, tally-keepers, and information traders who make money by knowing which routes, prices, floods, and shortages matter before somebody else does.",
    ),
}

CLAN_SIGNAL_PREFIX = "goblin_clan_signal:"


def clan_signal_flag(clan_key: str, reason: str) -> str:
    return f"{CLAN_SIGNAL_PREFIX}{clan_key}:{reason}"


def clan_signal_counts(flags: frozenset[str] | set[str]) -> dict[str, int]:
    result = {key: 0 for key in CLAN_DESCRIPTIONS}
    for flag in flags:
        if not flag.startswith(CLAN_SIGNAL_PREFIX):
            continue
        remainder = flag[len(CLAN_SIGNAL_PREFIX):]
        clan_key = remainder.split(":", 1)[0]
        if clan_key in result:
            result[clan_key] += 1
    return result


# ---------------------------------------------------------------------------
# NPCs and quest items
# ---------------------------------------------------------------------------

JEX_MIREHOOK = NpcDefinition(
    key="goblin_jex_mirehook",
    name="Jex Mirehook",
    short_description="a mud-booted route foreman carrying three generations of claim tags on one belt",
    room_key=GOBLIN_BRASSGUT_MARKET_KEY,
    role="Mirehook route foreman and early clan-politics contact",
    dialogue=(
        "Jex rolls a bent claim tag across his knuckles. 'Swamp remembers water. Goblins remember arguments.'",
        "'Mirehook crews build routes because routes are useful. If somebody learns something that keeps a piling upright, I would rather hear it before the piling falls.'",
    ),
)

TALLA_COPPERCAP = NpcDefinition(
    key="goblin_talla_coppercap",
    name="Talla Coppercap",
    short_description="an immaculate apothecary with copper-capped vials arranged by smell as well as label",
    room_key=GOBLIN_TINKER_ROW_KEY,
    role="Coppercap apothecary and proprietary-formula contact",
    dialogue=(
        "Talla taps one capped vial. 'A formula is not a secret because secrets are exciting. It is controlled because one copied measurement can poison twelve customers.'",
        "'Craft has value. If everybody gets the method, everybody also gets the responsibility to do it correctly. Most people only want the first half.'",
    ),
)

SNIK_TINLEDGER = NpcDefinition(
    key="goblin_snik_tinledger",
    name="Snik Tinledger",
    short_description="a neat little broker with waterproof notebooks tucked into every available pocket",
    room_key=GOBLIN_LEDGER_HALL_KEY,
    role="Tinledger information broker and trade-route contact",
    dialogue=(
        "Snik pats a waxed notebook. 'Iron has a price. Herbs have a price. Knowing the north boardwalk washed out before the Dwarves load a wagon also has a price.'",
        "'Information is cargo with no weight. That is why people get sentimental about whether selling it counts as trade.'",
    ),
)

HADRIK_COILPRESS = NpcDefinition(
    key="dwarf_hadrik_coilpress",
    name="Hadrik Coilpress",
    short_description="a Dwarven trade factor checking route measurements against a brass folding rule",
    room_key=GOBLIN_BRASSGUT_MARKET_KEY,
    role="Dwarven trade factor buying lawful route and freight intelligence",
    dialogue=(
        "Hadrik folds his brass rule shut. 'Your city changes routes faster than ours changes forms. I pay for accurate information because guessing axle depth is more expensive.'",
        "He glances at the market traffic. 'The Tinledgers understand that a measurement can be merchandise without becoming a conspiracy.'",
    ),
)

CLAN_NPCS: tuple[NpcDefinition, ...] = (JEX_MIREHOOK, TALLA_COPPERCAP, SNIK_TINLEDGER, HADRIK_COILPRESS)

COPPERCAP_FORMULA_PACKET = ItemDefinition(
    "coppercap_formula_packet",
    "Sealed Coppercap Formula Packet",
    "A waxed packet of precise alchemical measurements marked for Pella Mireglass. The Coppercap seal is intact.",
    "quest_item",
    tier=0,
)
TINLEDGER_ROUTE_REPORT = ItemDefinition(
    "tinledger_route_report",
    "Tinledger Route Report",
    "A waterproof route report describing flood depth, usable pilings, and expected freight delays on the Junk City-Dwarven trade line.",
    "quest_item",
    tier=0,
)
CLAN_QUEST_ITEMS = (COPPERCAP_FORMULA_PACKET, TINLEDGER_ROUTE_REPORT)


# ---------------------------------------------------------------------------
# Three small quests with soft, non-exclusive choices.
# ---------------------------------------------------------------------------

GOBLIN_FRESH_CLAIMS = QuestDefinition(
    key="goblin_fresh_claims",
    name="Fresh Claims",
    style="structured",
    description=(
        "Mirehook and Coppercap disagree over Sourreed Terrace after the flood shifted the herb bed. Inspect the physical claim evidence, then decide whose interpretation you support."
    ),
    objective_steps=(
        ("inspect_stakes", "Travel to Sourreed Terrace in the deeper mire and EXAMINE CLAIM STAKES."),
        ("choose_report", "Choose how to report the evidence: REPORT MIREHOOK to Jex, or REPORT COPPERCAP to Talla."),
        ("complete", "You made one small choice in Junk City's ongoing argument over useful ground."),
    ),
)

GOBLIN_CLOSED_FORMULA = QuestDefinition(
    key="goblin_closed_formula",
    name="A Formula With a Lock On It",
    style="structured",
    description=(
        "Talla Coppercap entrusts you with a sealed field formula for Pella Mireglass. Pella can use it as delivered, or you can choose to let the public route apothecary copy the method."
    ),
    objective_steps=(
        ("deliver_formula", "Carry the Sealed Coppercap Formula Packet to Pella Mireglass at the Apothecary Blind and TALK PELLA."),
        ("choose_formula", "Choose KEEP FORMULA SEALED or SHARE FORMULA WITH PELLA."),
        ("complete", "You decided how much control a craft family should keep over a useful method."),
    ),
)

GOBLIN_WEIGHT_OF_A_MAP = QuestDefinition(
    key="goblin_weight_of_a_map",
    name="The Weight of a Map",
    style="structured",
    description=(
        "Snik Tinledger asks you to carry a swamp route report to a Dwarven trade factor. You can complete the private information sale or file the same route information publicly in Junk City instead."
    ),
    objective_steps=(
        ("choose_delivery", "Either TALK HADRIK in Brassgut Market and DELIVER REPORT, or return to the Ledger Hall and FILE REPORT PUBLICLY."),
        ("complete", "You decided whether this piece of route knowledge was private merchandise or shared infrastructure."),
    ),
)

CLAN_QUESTS = (GOBLIN_FRESH_CLAIMS, GOBLIN_CLOSED_FORMULA, GOBLIN_WEIGHT_OF_A_MAP)


# ---------------------------------------------------------------------------
# Content registration
# ---------------------------------------------------------------------------


def _patch_room_npcs(room: RoomDefinition, extra_keys: tuple[str, ...]) -> RoomDefinition:
    existing = tuple(room.npc_keys)
    merged = existing + tuple(key for key in extra_keys if key not in existing)
    return replace(room, npc_keys=merged)


def install_goblin_clan_content(world_service=None) -> None:
    install_goblin_deep_mire_content()

    room_additions = {
        GOBLIN_BRASSGUT_MARKET_KEY: (JEX_MIREHOOK.key, HADRIK_COILPRESS.key),
        GOBLIN_TINKER_ROW_KEY: (TALLA_COPPERCAP.key,),
        GOBLIN_LEDGER_HALL_KEY: (SNIK_TINLEDGER.key,),
    }
    replacements: dict[str, RoomDefinition] = {}
    for room_key, npc_keys in room_additions.items():
        room = legacy_world.ROOMS_BY_KEY.get(room_key)
        if room is not None:
            replacements[room_key] = _patch_room_npcs(room, npc_keys)

    if replacements:
        legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
        legacy_world.ROOMS_BY_KEY.update(replacements)

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    for npc in CLAN_NPCS:
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    for item in CLAN_QUEST_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for quest in CLAN_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in replacements:
                cache.pop(room_key, None)


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


def _consume_all(session, item_key: str) -> None:
    if session.character is None:
        return
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _reconcile_clan_quests(session) -> None:
    if session.character is None:
        return
    character_id = session.character.id

    formula = _quest(session, GOBLIN_CLOSED_FORMULA)
    if formula and formula.get("status") == "active" and formula.get("current_step") in {"deliver_formula", "choose_formula"}:
        quantity = session.database.item_quantity(character_id, COPPERCAP_FORMULA_PACKET.key)
        if quantity == 0:
            session.database.add_item(character_id, COPPERCAP_FORMULA_PACKET.key, 1)
        elif quantity > 1:
            session.database.consume_item(character_id, COPPERCAP_FORMULA_PACKET.key, quantity - 1)
    elif formula and formula.get("status") == "completed":
        _consume_all(session, COPPERCAP_FORMULA_PACKET.key)

    report = _quest(session, GOBLIN_WEIGHT_OF_A_MAP)
    if report and report.get("status") == "active":
        quantity = session.database.item_quantity(character_id, TINLEDGER_ROUTE_REPORT.key)
        if quantity == 0:
            session.database.add_item(character_id, TINLEDGER_ROUTE_REPORT.key, 1)
        elif quantity > 1:
            session.database.consume_item(character_id, TINLEDGER_ROUTE_REPORT.key, quantity - 1)
    elif report and report.get("status") == "completed":
        _consume_all(session, TINLEDGER_ROUTE_REPORT.key)


def _grant_signal(session, clan_key: str, reason: str) -> None:
    assert session.character is not None
    session.database.grant_flag(session.character.id, clan_signal_flag(clan_key, reason))


def _complete_choice(session, quest: QuestDefinition, clan_key: str | None, reason: str, text: str) -> None:
    assert session.character is not None
    if clan_key is not None:
        _grant_signal(session, clan_key, reason)
    session.database.complete_quest(session.character.id, quest.key)


# ---------------------------------------------------------------------------
# Dialogue / quest flow
# ---------------------------------------------------------------------------


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches(target: str, *names: str) -> bool:
    return target in {name.lower() for name in names}


async def _talk_jex(session) -> bool:
    assert session.character is not None
    flags = session.database.list_flags(session.character.id)
    if GOBLIN_OUTER_ROUTE_COMPLETE_FLAG not in flags:
        return False

    quest = _quest(session, GOBLIN_FRESH_CLAIMS)
    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_FRESH_CLAIMS.key, "inspect_stakes")
        await session.send(
            "\r\nJex Mirehook pushes two claim tags across a crate: one old iron, one bright copper.\r\n"
            "'Spring water moved Sourreed Terrace again. Mirehook found that bed years ago. Coppercap says maintaining the herbs matters more than who hammered the first stake.'\r\n"
            "He shrugs. 'Go look. Not listen—look. EXAMINE CLAIM STAKES at Sourreed Terrace, then tell one of us what you think counts.'\r\n"
            "\r\nNew quest: Fresh Claims.\r\n"
        )
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nJex nods once. 'Already heard your answer. Doesn't mean the swamp stopped arguing.'\r\n")
        return True
    objective = GOBLIN_FRESH_CLAIMS.objective_for_step(quest.get("current_step"))
    await session.send("\r\nJex asks, 'What does the ground say?'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_talla(session) -> bool:
    assert session.character is not None
    fresh = _quest(session, GOBLIN_FRESH_CLAIMS)
    if fresh and fresh.get("status") == "active" and fresh.get("current_step") == "choose_report":
        await session.send("\r\nTalla folds her arms. 'If you think maintenance gives Coppercap the stronger claim, say REPORT COPPERCAP. I prefer an answer stated clearly.'\r\n")
        return True

    if not _quest_completed(session, GOBLIN_FRESH_CLAIMS):
        return False

    formula = _quest(session, GOBLIN_CLOSED_FORMULA)
    if formula is None:
        session.database.start_quest(session.character.id, GOBLIN_CLOSED_FORMULA.key, "deliver_formula")
        session.database.add_item(session.character.id, COPPERCAP_FORMULA_PACKET.key, 1)
        await session.send(
            "\r\nTalla places a waxed packet in your hand. 'Pella Mireglass needs these measurements for a marsh stabilizer. She needs the formula; the whole route does not.'\r\n"
            "'Take it to the Apothecary Blind. Keep the seal intact. Precision is work, and work has an owner even when it helps people.'\r\n"
            "You receive a Sealed Coppercap Formula Packet.\r\n"
            "\r\nNew quest: A Formula With a Lock On It.\r\n"
        )
        return True
    if formula.get("status") == "completed":
        await session.send("\r\nTalla glances at you, then at her locked formula cabinet. 'I remember what you decided about the packet.'\r\n")
        return True
    objective = GOBLIN_CLOSED_FORMULA.objective_for_step(formula.get("current_step"))
    if objective:
        await session.send("\r\n" + objective + "\r\n")
    return True


async def _talk_pella_for_formula(session) -> bool:
    if session.character is None:
        return False
    formula = _quest(session, GOBLIN_CLOSED_FORMULA)
    if not formula or formula.get("status") != "active":
        return False
    if formula.get("current_step") == "deliver_formula":
        session.database.advance_quest(session.character.id, GOBLIN_CLOSED_FORMULA.key, "choose_formula")
    await session.send(
        "\r\nPella turns the sealed packet over in both hands. 'Coppercap measurements. Good ones, usually.'\r\n"
        "She does not break the seal. 'I can use this and send it back closed. Or I can copy the method into the public route book before I return it. Talla will know which happened.'\r\n"
        "Choose KEEP FORMULA SEALED or SHARE FORMULA WITH PELLA.\r\n"
    )
    return True


async def _talk_snik(session) -> bool:
    assert session.character is not None
    if not _quest_completed(session, GOBLIN_CLOSED_FORMULA):
        return False
    report = _quest(session, GOBLIN_WEIGHT_OF_A_MAP)
    if report is None:
        session.database.start_quest(session.character.id, GOBLIN_WEIGHT_OF_A_MAP.key, "choose_delivery")
        session.database.add_item(session.character.id, TINLEDGER_ROUTE_REPORT.key, 1)
        await session.send(
            "\r\nSnik slides a waterproof report across the Ledger Hall desk. 'Flood depth, piling condition, freight delay. Hadrik Coilpress pays for this because Dwarven wagons dislike surprises.'\r\n"
            "He smiles thinly. 'Some Goblins think route information belongs on a public board. I think information gathered on my time can be sold on my time.'\r\n"
            "You receive a Tinledger Route Report.\r\n"
            "\r\nNew quest: The Weight of a Map.\r\n"
            "Take it to Hadrik in Brassgut Market, or FILE REPORT PUBLICLY here if you reject the private sale.\r\n"
        )
        return True
    if report.get("status") == "completed":
        await session.send("\r\nSnik taps his notebook. 'Your opinion on the price of information is already in my records.'\r\n")
        return True
    await session.send("\r\nSnik says, 'Hadrik is in Brassgut. Unless you decide the whole city deserves my report for free.'\r\n")
    return True


async def _talk_hadrik(session) -> bool:
    if session.character is None:
        return False
    report = _quest(session, GOBLIN_WEIGHT_OF_A_MAP)
    if not report or report.get("status") != "active":
        return False
    await session.send(
        "\r\nHadrik sees the Tinledger wax on the report. 'That will be the route measurements I commissioned. If you are completing the delivery, say DELIVER REPORT.'\r\n"
    )
    return True


async def _handle_clan_choice(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "goblin":
        return False
    room = session.character.current_room

    fresh = _quest(session, GOBLIN_FRESH_CLAIMS)
    if fresh and fresh.get("status") == "active":
        step = fresh.get("current_step")
        if room == GOBLIN_SOURREED_TERRACE_KEY and normalized in {"examine claim stakes", "look claim stakes", "search claim stakes", "examine stakes", "search stakes"}:
            if step == "inspect_stakes":
                session.database.advance_quest(session.character.id, GOBLIN_FRESH_CLAIMS.key, "choose_report")
            await session.send(
                "\r\nThe oldest intact stake is Mirehook iron, sunk deep enough to predate the current flood line. Coppercap's tag is newer, but fresh cut marks show their gatherers have maintained the herb bed recently. The evidence supports two different ideas of ownership: first claim, or continuing care.\r\n"
                "Quest updated: Fresh Claims. REPORT MIREHOOK to Jex or REPORT COPPERCAP to Talla.\r\n"
            )
            return True
        if step == "choose_report" and normalized == "report mirehook" and room == GOBLIN_BRASSGUT_MARKET_KEY:
            _grant_signal(session, FLOODPICK_MIREHOOK, "fresh_claim")
            session.database.complete_quest(session.character.id, GOBLIN_FRESH_CLAIMS.key)
            await session.send(
                "\r\nJex listens, then pockets the old iron tag. 'First stake counts for something. Good. Doesn't mean Coppercap stops cutting herbs tomorrow.'\r\n"
                "Quest complete: Fresh Claims. Mirehook remembers that you backed the older route claim.\r\n"
            )
            return True
        if step == "choose_report" and normalized == "report coppercap" and room == GOBLIN_TINKER_ROW_KEY:
            _grant_signal(session, FLOODPICK_COPPERCAP, "fresh_claim")
            session.database.complete_quest(session.character.id, GOBLIN_FRESH_CLAIMS.key)
            await session.send(
                "\r\nTalla accepts your report. 'A dead claim marker does not weed a medicinal bed. Maintenance has value.'\r\n"
                "Quest complete: Fresh Claims. Coppercap remembers that you backed continuing care over first discovery.\r\n"
            )
            return True

    formula = _quest(session, GOBLIN_CLOSED_FORMULA)
    if formula and formula.get("status") == "active" and formula.get("current_step") == "choose_formula" and room == GOBLIN_APOTHECARY_BLIND_KEY:
        if normalized in {"keep formula sealed", "keep sealed", "return sealed"}:
            _grant_signal(session, FLOODPICK_COPPERCAP, "closed_formula")
            session.database.complete_quest(session.character.id, GOBLIN_CLOSED_FORMULA.key)
            _consume_all(session, COPPERCAP_FORMULA_PACKET.key)
            await session.send(
                "\r\nPella uses the measurements without copying them, reseals the packet, and nods. 'Controlled craft, then. Talla will approve.'\r\n"
                "Quest complete: A Formula With a Lock On It. Coppercap remembers that you respected the closed method.\r\n"
            )
            return True
        if normalized in {"share formula", "share formula with pella", "copy formula", "share method"}:
            _grant_signal(session, FLOODPICK_MIREHOOK, "shared_formula")
            session.database.complete_quest(session.character.id, GOBLIN_CLOSED_FORMULA.key)
            _consume_all(session, COPPERCAP_FORMULA_PACKET.key)
            session.database.grant_flag(session.character.id, "goblin_public_alchemy_method_shared")
            await session.send(
                "\r\nPella copies the measurements into the public route book before resealing the packet. 'Useful knowledge should survive the person carrying it. Talla and I can argue about that ourselves.'\r\n"
                "Quest complete: A Formula With a Lock On It. Mirehook-style open fieldcraft gains another small precedent.\r\n"
            )
            return True

    report = _quest(session, GOBLIN_WEIGHT_OF_A_MAP)
    if report and report.get("status") == "active":
        if normalized == "deliver report" and room == GOBLIN_BRASSGUT_MARKET_KEY:
            _grant_signal(session, FLOODPICK_TINLEDGER, "dwarf_report")
            session.database.complete_quest(session.character.id, GOBLIN_WEIGHT_OF_A_MAP.key)
            _consume_all(session, TINLEDGER_ROUTE_REPORT.key)
            await session.send(
                "\r\nHadrik checks the flood measurements, folds the report into his case, and marks the delivery accepted. Snik's information has become trade exactly as intended.\r\n"
                "Quest complete: The Weight of a Map. Tinledger remembers that you completed the private information sale.\r\n"
            )
            return True
        if normalized in {"file report publicly", "file report", "post report publicly", "post report"} and room == GOBLIN_LEDGER_HALL_KEY:
            _grant_signal(session, FLOODPICK_MIREHOOK, "public_report")
            session.database.complete_quest(session.character.id, GOBLIN_WEIGHT_OF_A_MAP.key)
            _consume_all(session, TINLEDGER_ROUTE_REPORT.key)
            session.database.grant_flag(session.character.id, "goblin_route_report_made_public")
            await session.send(
                "\r\nYou copy the route measurements onto the Ledger Hall's public board instead of carrying them to the Dwarven buyer. By the time the ink dries, two freight crews are already reading it.\r\n"
                "Quest complete: The Weight of a Map. Route crews remember that you treated the information as shared infrastructure.\r\n"
            )
            return True

    return False


async def _show_clans(session) -> None:
    assert session.character is not None
    flags = session.database.list_flags(session.character.id)
    counts = clan_signal_counts(flags)
    await session.send("\r\n--- Junk City Clan Signals ---\r\n")
    for key in (FLOODPICK_MIREHOOK, FLOODPICK_COPPERCAP, FLOODPICK_TINLEDGER):
        name, description = CLAN_DESCRIPTIONS[key]
        await session.send(f"{name}: {counts[key]} signal(s). {description}\r\n")
    await session.send(
        "These are remembered choices, not exclusive faction membership. Helping one group does not lock you out of the others.\r\n"
    )
    await session.send(floodpick_control_text() + "\r\n")


def install_goblin_clan_runtime(player_session_class, world_service) -> None:
    install_goblin_clan_content(world_service)
    if getattr(player_session_class, "_goblin_clan_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "goblin":
            return
        _reconcile_clan_quests(self)

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
            await _show_clans(self)
            return

        if await _handle_clan_choice(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == GOBLIN_BRASSGUT_MARKET_KEY and _matches(target, "jex", "jex mirehook", "mirehook", "route foreman"):
                if await _talk_jex(self):
                    return
            if self.character.current_room == GOBLIN_TINKER_ROW_KEY and _matches(target, "talla", "talla coppercap", "coppercap", "apothecary"):
                if await _talk_talla(self):
                    return
            if self.character.current_room == GOBLIN_APOTHECARY_BLIND_KEY and _matches(target, "pella", "pella mireglass", "mireglass"):
                if await _talk_pella_for_formula(self):
                    return
            if self.character.current_room == GOBLIN_LEDGER_HALL_KEY and _matches(target, "snik", "snik tinledger", "tinledger", "broker"):
                if await _talk_snik(self):
                    return
            if self.character.current_room == GOBLIN_BRASSGUT_MARKET_KEY and _matches(target, "hadrik", "hadrik coilpress", "dwarf", "dwarven trader", "trade factor"):
                if await _talk_hadrik(self):
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

        if normalized in {"help", "?"}:
            flags = self.database.list_flags(self.character.id)
            if GOBLIN_OUTER_ROUTE_COMPLETE_FLAG in flags:
                await self.send(
                    "Goblin politics: CLANS shows your non-exclusive clan signals. Early clan errands use TALK JEX, TALK TALLA, TALK SNIK, and situational choices such as REPORT, KEEP/SHARE, DELIVER, or FILE REPORT PUBLICLY.\r\n"
                )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_clan_runtime_installed = True
