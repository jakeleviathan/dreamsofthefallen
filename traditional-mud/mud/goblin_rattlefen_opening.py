from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.goblin_salvage_quest import (
    GOBLIN_SALVAGE_COMPLETE_FLAG,
    GOBLIN_SALVAGE_CREDIT_FLAG,
    GOBLIN_SALVAGE_QUEST,
)
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_START_ROOM_KEY,
    GOBLIN_TINKER_ROW_KEY,
)
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, FeatureDefinition, RoomAugmentation
from mud.world import NpcDefinition, RoomDefinition


RATTLEFEN_NAME = "Rattlefen"
RATTLEFEN_OPENING_COMPLETE_FLAG = "goblin_rattlefen_opening_complete"
RATTLEFEN_CLAIM_CHECKED_FLAG = "goblin_rattlefen_old_claim_checked"
RATTLEFEN_TOKEN_SOLD_FLAG = "goblin_rattlefen_earth_token_sold"
RATTLEFEN_TOKEN_KEPT_FLAG = "goblin_rattlefen_earth_token_kept"

RATTLEFEN_CHOICE_SPRING_FLAG = "goblin_rattlefen_claimed_spring_cage"
RATTLEFEN_CHOICE_LENS_FLAG = "goblin_rattlefen_claimed_lens_frame"
RATTLEFEN_CHOICE_SWITCH_FLAG = "goblin_rattlefen_claimed_switchplate"
RATTLEFEN_DISPUTE_RETURN_FLAG = "goblin_rattlefen_returned_old_claim"
RATTLEFEN_DISPUTE_EXPIRED_FLAG = "goblin_rattlefen_proved_claim_expired"
RATTLEFEN_DISPUTE_NEGOTIATE_FLAG = "goblin_rattlefen_negotiated_old_claim"
RATTLEFEN_MARK_HOOK_FLAG = "goblin_rattlefen_mark_hook"
RATTLEFEN_MARK_SPIRAL_FLAG = "goblin_rattlefen_mark_spiral"
RATTLEFEN_MARK_BOLT_FLAG = "goblin_rattlefen_mark_bolt"
RATTLEFEN_PERSONAL_MARK_FLAG = "goblin_personal_salvage_mark_registered"

CLAIM_TAG_KEY = "goblin_single_claim_tag"
SPRING_CAGE_KEY = "goblin_salvage_spring_cage"
LENS_FRAME_KEY = "goblin_salvage_lens_frame"
SWITCHPLATE_KEY = "goblin_salvage_switchplate"
GIFT_HOUSING_KEY = "goblin_sella_signal_housing"
RATTLELIGHT_KEY = "goblin_rattlelight_pocket_beacon"
EARTH_TOKEN_KEY = "goblin_earth_stamped_token"
HUMAN_TOOL_ROLL_KEY = "goblin_human_trade_tool_roll"
PERSONAL_STAMP_KEY = "goblin_personal_claim_stamp"


THREE_BELLS = QuestDefinition(
    key="goblin_rattlefen_three_bells",
    name="Three Bells",
    style="structured",
    description=(
        "Three quick salvage bells announce a fresh swamp recovery at the Sorting Spine. "
        "A new Goblin gets one claim tag and one chance to decide what in the wreck is actually worth carrying."
    ),
    objective_steps=(
        ("inspect_wreck", "Go north to the Sorting Spine and EXAMINE FRESH WRECK."),
        ("choose_salvage", "Spend your one claim tag with CLAIM SPRING, CLAIM LENS, or CLAIM SWITCHPLATE."),
        ("complete", "You made your first salvage choice instead of simply taking the largest piece."),
    ),
)

WHATS_IT_WORTH = QuestDefinition(
    key="goblin_rattlefen_whats_it_worth",
    name="What's It Worth?",
    style="structured",
    description=(
        "Take the claimed piece to Ruskle Coil and learn the first market lesson: usefulness, price, urgency, and sentiment are not the same kind of value."
    ),
    objective_steps=(
        ("seek_broker", "Take your claimed salvage to Ruskle Coil in Brassgut Market and TALK RUSKLE."),
        ("bargain", "Respond to the offer: ACCEPT OFFER, COUNTER FAIR, COUNTER HIGH, or WALK AWAY."),
        ("complete", "You learned that a price is an agreement, not a property of the object."),
    ),
)

SOMEBODY_ELSES_MARK = QuestDefinition(
    key="goblin_rattlefen_somebody_elses_mark",
    name="Somebody Else's Mark",
    style="structured",
    description=(
        "A faded claim mark appears beneath the grime on your salvage. The original claimant is alive, and Rattlefen expects ownership disputes to be settled rather than wished away."
    ),
    objective_steps=(
        ("meet_owner", "Go to the Ledger Hall and TALK SELLA, the Goblin whose old mark is on the piece."),
        ("resolve_claim", "Choose how to settle it: RETURN SALVAGE, CHECK OLD CLAIM then PROVE CLAIM EXPIRED, or NEGOTIATE CLAIM."),
        ("complete", "The disputed claim is settled and recorded."),
    ),
)

BETTER_THAN_IT_WAS = QuestDefinition(
    key="goblin_rattlefen_better_than_it_was",
    name="Better Than It Was",
    style="structured",
    description=(
        "Bring the salvage you legitimately ended up with to Tinker Row. Brin Copperhand does not want to restore its old purpose; the lesson is to give it a better new one."
    ),
    objective_steps=(
        ("meet_brin", "Go to Tinker Row and TALK BRIN."),
        ("repurpose", "At Brin's starter bench, REPURPOSE SALVAGE."),
        ("complete", "The old component has become a Rattlelight Pocket Beacon instead of a repaired copy of what it used to be."),
    ),
)

THING_HUMANS_BUY = QuestDefinition(
    key="goblin_rattlefen_thing_humans_buy",
    name="The Thing Humans Buy",
    style="structured",
    description=(
        "Repurposing the salvage reveals a tiny stamped relic from Earth. It is nearly useless as material, but Humans value surviving pieces of their lost ancestral world very differently."
    ),
    objective_steps=(
        ("show_token", "Take the stamped token to Human factor Mara Vale in Brassgut Market and TALK MARA."),
        ("decide_token", "Choose SELL TOKEN or KEEP TOKEN. Neither choice is treated as a mistake."),
        ("complete", "You saw how culture can change an object's value more radically than craftsmanship can."),
    ),
)

YOUR_MARK = QuestDefinition(
    key="goblin_rattlefen_your_mark",
    name="Your Mark",
    style="structured",
    description=(
        "Return to Vikka Three-Nails. After claiming, bargaining, settling ownership, repurposing, and seeing cross-cultural value firsthand, you are ready to register a salvage mark of your own."
    ),
    objective_steps=(
        ("talk_vikka", "Return to the Clattergate and TALK VIKKA."),
        ("choose_mark", "Register one personal mark: MARK HOOK, MARK SPIRAL, or MARK BOLT."),
        ("complete", "Your personal salvage mark is registered in Rattlefen. The wider routes can now treat you as a credited claimant."),
    ),
)

RATTLEFEN_QUESTS = (
    THREE_BELLS,
    WHATS_IT_WORTH,
    SOMEBODY_ELSES_MARK,
    BETTER_THAN_IT_WAS,
    THING_HUMANS_BUY,
    YOUR_MARK,
)


RATTLEFEN_ITEMS = (
    ItemDefinition(
        key=CLAIM_TAG_KEY,
        name="Single Brass Claim Tag",
        description="A plain starter claim tag issued for the three-bell salvage drop. It is valid for exactly one piece.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=SPRING_CAGE_KEY,
        name="Bent Spring Cage",
        description="A compact spring cage from the fresh wreck. The housing is bent, but the spring itself still answers evenly when pressed.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=LENS_FRAME_KEY,
        name="Cracked Lens Frame",
        description="A brass frame holding two cloudy glass elements. The optics are poor, but the adjustable hinge is unusually fine work.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=SWITCHPLATE_KEY,
        name="Sealed Ceramic Switchplate",
        description="A glazed switchplate with corroded contacts and a sealed back. It is too intact to throw away and too strange to price at a glance.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=GIFT_HOUSING_KEY,
        name="Bent Signal Housing",
        description="An obsolete signal housing Sella Reedmark transferred to you cleanly after you returned her old claim. This one is yours without argument.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=RATTLELIGHT_KEY,
        name="Rattlelight Pocket Beacon",
        description="A palm-sized Goblin signal light made from parts that once did something entirely different. It rattles faintly, flashes reliably, and has no interest in being restored to its old purpose.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=EARTH_TOKEN_KEY,
        name="Stamped Earth Token",
        description="A small corroded metal token stamped in old Human lettering. Its original use is forgotten, but the script identifies it as a surviving object from Earth.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=HUMAN_TOOL_ROLL_KEY,
        name="Sealed Human Tool Roll",
        description="A compact roll of clean files, picks, drivers, and measuring tools traded by Mara Vale for a tiny Earth relic. The exchange still feels lopsided in your favor.",
        category="quest_item",
        tier=0,
    ),
    ItemDefinition(
        key=PERSONAL_STAMP_KEY,
        name="Personal Salvage Stamp",
        description="A small steel punch registered to your chosen Rattlefen claim mark. The ledger, not the shape alone, is what makes it yours.",
        category="quest_item",
        tier=0,
    ),
)


SELLA_REEDMARK = NpcDefinition(
    key="goblin_sella_reedmark",
    name="Sella Reedmark",
    short_description="an older salvage hauler waiting beside a ledger shelf with a faded claim rubbing in one hand",
    room_key=GOBLIN_LEDGER_HALL_KEY,
    role="original claimant in the starter ownership dispute",
    dialogue=(
        "Sella holds the rubbing beside the old mark. 'Mine once. Maybe mine now. That is what the ledger is for.'",
        "'If the claim expired, prove it. If you want it anyway, bargain. If you think it is still mine, hand it back. I can live with any answer that leaves a record.'",
    ),
)

MARA_VALE = NpcDefinition(
    key="human_mara_vale_rattlefen_factor",
    name="Mara Vale",
    short_description="a Human factor in travel-dark clothing studying a blanket of Earth-marked curios with uncomfortable concentration",
    room_key=GOBLIN_BRASSGUT_MARKET_KEY,
    role="Human antiquities buyer and cross-cultural value lesson",
    dialogue=(
        "Mara turns old fragments over carefully, searching for lettering rather than useful metal. 'Most of these are nothing to you. That is exactly why I can sometimes afford them.'",
        "'Earth is not a place my people can return to. A useless stamped piece of it can still be worth more to us than a working Goblin hinge.'",
    ),
)

RATTLEFEN_NPCS = (SELLA_REEDMARK, MARA_VALE)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = (), listen: str = "") -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        listen_text=listen,
    )


def rattlefen_augmentations() -> dict[str, RoomAugmentation]:
    return {
        GOBLIN_START_ROOM_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_mark_board",
                    "Personal Mark Board",
                    "a scarred steel board carrying hundreds of registered personal salvage marks",
                    "Hooks, spirals, bolts, eyes, teeth, lines, knots, and private little jokes cover the board. Many shapes repeat; each legal mark is distinguished by the name and ledger entry behind it. A symbol without a record is only graffiti.",
                    aliases=("mark board", "marks board", "personal marks", "claim marks"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "rattlefen_city_name",
                    "The city around you is Rattlefen. Older route books and plenty of outsiders still call it Junk City, a nickname locals tolerate because arguing over the name takes time that could be spent arguing over price.",
                    priority=35,
                ),
            ),
        ),
        GOBLIN_SORTING_SPINE_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_salvage_bell",
                    "Salvage Bell",
                    "a dented bronze bell used to announce newly opened salvage lots",
                    "Different strike patterns mean different things. Three quick bells means a fresh public starter lot: one tag, one piece, no shoving somebody into a chute to get there first.",
                    aliases=("bell", "three bells", "salvage bell"),
                    listen="The bell's cracked tone carries surprisingly far over the sorting crews.",
                ),
                _feature(
                    "rattlefen_fresh_wreck",
                    "Fresh Wreck",
                    "a swamp-dragged mechanism split open across a sorting cradle",
                    "Most of it is dead weight: waterlogged casing, split belt, warped plates. Three smaller pieces are less obvious: a bent spring cage that still answers evenly, a cracked lens frame with a fine hinge, and a sealed ceramic switchplate whose back has not corroded through. You have one starter claim tag, not three.",
                    aliases=("wreck", "fresh wreck", "salvage drop", "new salvage", "starter lot"),
                ),
            ),
        ),
        GOBLIN_BRASSGUT_MARKET_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_offer_board",
                    "Offer Board",
                    "a chalk board covered in prices that have been crossed out, argued over, and rewritten",
                    "The same kinds of objects appear at wildly different prices depending on urgency, buyer, condition, weather, and who has already promised what to whom. Nothing on the board pretends price is an intrinsic property.",
                    aliases=("offer board", "price board", "prices", "chalk board"),
                ),
            ),
        ),
        GOBLIN_LEDGER_HALL_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_old_claim_shelf",
                    "Old Claim Shelf",
                    "a humidity-sealed shelf of expired and disputed salvage records",
                    "The older claim books distinguish possession, abandonment, transfer, expiration, and shared recovery rights with exhausting precision. Goblins may argue loudly about ownership, but they dislike having to argue the same case twice.",
                    aliases=("old claims", "claim shelf", "old claim shelf", "claim records", "old ledger"),
                ),
            ),
        ),
        GOBLIN_TINKER_ROW_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_repurpose_bench",
                    "Repurpose Bench",
                    "a starter workbench surrounded by bins labeled by possible future use rather than original purpose",
                    "The bins say LIGHT, SPRING, HOLD, CUT, TURN, SEAL, FASTEN, and WEIRD BUT KEEP. Brin's bench is arranged around what a component could become, not what factory first made it.",
                    aliases=("repurpose bench", "starter bench", "bench", "workbench"),
                ),
            ),
        ),
        GOBLIN_FLOODGATE_WALK_KEY: RoomAugmentation(
            features=(
                _feature(
                    "rattlefen_bargain_gate",
                    "Bargain Gate",
                    "the painted checkpoint where Rattlefen's safe streets give way to negotiated swamp routes",
                    "The gate is less a door than a collection of posted obligations: route claims, rescue terms, flood warnings, clan notices, and who currently promises to maintain which piling. Locals call it the Bargain Gate because almost every safe road beyond it exists because somebody agreed to something.",
                    aliases=("bargain gate", "gate", "checkpoint", "painted gate"),
                ),
            ),
        ),
    }


def _patch_room_npcs(room: RoomDefinition, npc_keys: tuple[str, ...]) -> RoomDefinition:
    merged = room.npc_keys + tuple(key for key in npc_keys if key not in room.npc_keys)
    return replace(room, npc_keys=merged)


def _merge_augmentation(base: RoomAugmentation, extra: RoomAugmentation) -> RoomAugmentation:
    feature_keys = {feature.key for feature in base.features}
    layer_keys = {layer.key for layer in base.description_layers}
    return replace(
        base,
        features=base.features + tuple(feature for feature in extra.features if feature.key not in feature_keys),
        description_layers=base.description_layers + tuple(layer for layer in extra.description_layers if layer.key not in layer_keys),
    )


def install_rattlefen_opening_content(world_service=None) -> None:
    for definition in RATTLEFEN_QUESTS:
        if definition.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (definition,)
        quests.QUESTS_BY_KEY[definition.key] = definition

    for item in RATTLEFEN_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    for npc in RATTLEFEN_NPCS:
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    replacements: dict[str, RoomDefinition] = {}
    plan = {
        GOBLIN_LEDGER_HALL_KEY: (SELLA_REEDMARK.key,),
        GOBLIN_BRASSGUT_MARKET_KEY: (MARA_VALE.key,),
    }
    for room_key, npc_keys in plan.items():
        room = legacy_world.ROOMS_BY_KEY.get(room_key)
        if room is not None:
            replacements[room_key] = _patch_room_npcs(room, npc_keys)
    if replacements:
        legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
        legacy_world.ROOMS_BY_KEY.update(replacements)

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        for room_key, extra in rattlefen_augmentations().items():
            base = world_service.augmentations.get(room_key, RoomAugmentation())
            world_service.augmentations[room_key] = _merge_augmentation(base, extra)
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(room_key, None)


def _quest(session, definition: QuestDefinition):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, definition.key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _ensure_one(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity == 0:
        session.database.add_item(session.character.id, item_key, 1)
    elif quantity > 1:
        session.database.consume_item(session.character.id, item_key, quantity - 1)


def _consume_all(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _active_salvage_key(session) -> str | None:
    assert session.character is not None
    for key in (SPRING_CAGE_KEY, LENS_FRAME_KEY, SWITCHPLATE_KEY, GIFT_HOUSING_KEY):
        if session.database.item_quantity(session.character.id, key) > 0:
            return key
    return None


def _legacy_started(session) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    if GOBLIN_SALVAGE_COMPLETE_FLAG in flags or GOBLIN_SALVAGE_CREDIT_FLAG in flags:
        return True
    return session.database.get_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key) is not None


def _complete_and_start(session, completed: QuestDefinition, next_quest: QuestDefinition, next_step: str) -> None:
    assert session.character is not None
    session.database.complete_quest(session.character.id, completed.key)
    if session.database.get_quest(session.character.id, next_quest.key) is None:
        session.database.start_quest(session.character.id, next_quest.key, next_step)


def _ensure_legacy_credit(session) -> None:
    assert session.character is not None
    character_id = session.character.id
    session.database.grant_flag(character_id, GOBLIN_SALVAGE_COMPLETE_FLAG)
    session.database.grant_flag(character_id, GOBLIN_SALVAGE_CREDIT_FLAG)
    legacy = session.database.get_quest(character_id, GOBLIN_SALVAGE_QUEST.key)
    if legacy is None:
        session.database.start_quest(character_id, GOBLIN_SALVAGE_QUEST.key, "complete")
    session.database.complete_quest(character_id, GOBLIN_SALVAGE_QUEST.key)


def reconcile_rattlefen_opening(session) -> bool:
    """Start or repair the new Goblin opening without rewinding legacy Goblins."""
    if session.character is None or session.character.race != "goblin":
        return False

    character_id = session.character.id
    flags = _flags(session)
    if RATTLEFEN_OPENING_COMPLETE_FLAG in flags:
        _ensure_legacy_credit(session)
        _ensure_one(session, PERSONAL_STAMP_KEY)
        return False

    first = _quest(session, THREE_BELLS)
    if first is None:
        if _legacy_started(session):
            return False
        session.database.start_quest(character_id, THREE_BELLS.key, "inspect_wreck")
        _ensure_one(session, CLAIM_TAG_KEY)
        return True

    if first.get("status") == "active":
        _ensure_one(session, CLAIM_TAG_KEY)
        return False

    chain = (
        (WHATS_IT_WORTH, "seek_broker"),
        (SOMEBODY_ELSES_MARK, "meet_owner"),
        (BETTER_THAN_IT_WAS, "meet_brin"),
        (THING_HUMANS_BUY, "show_token"),
        (YOUR_MARK, "talk_vikka"),
    )
    previous = first
    for definition, start_step in chain:
        current = _quest(session, definition)
        if current is None:
            if _quest(session, previous).get("status") == "completed":
                session.database.start_quest(character_id, definition.key, start_step)
            return False
        if current.get("status") != "completed":
            if definition is BETTER_THAN_IT_WAS and _active_salvage_key(session) is None:
                _ensure_one(session, GIFT_HOUSING_KEY)
            if definition is THING_HUMANS_BUY:
                _ensure_one(session, EARTH_TOKEN_KEY)
            return False
        previous = definition

    session.database.grant_flag(character_id, RATTLEFEN_OPENING_COMPLETE_FLAG)
    session.database.grant_flag(character_id, RATTLEFEN_PERSONAL_MARK_FLAG)
    _ensure_one(session, PERSONAL_STAMP_KEY)
    _ensure_legacy_credit(session)
    return False


def _target_after_talk(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _is_target(target: str, *names: str) -> bool:
    return target in {name.lower() for name in names}


async def _talk_ruskle(session) -> bool:
    quest = _quest(session, WHATS_IT_WORTH)
    if quest is None or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_BRASSGUT_MARKET_KEY:
        await session.send("Ruskle Coil is not here. His broker counter is in Brassgut Market.\r\n")
        return True
    step = quest.get("current_step")
    if step == "seek_broker":
        session.database.advance_quest(session.character.id, WHATS_IT_WORTH.key, "bargain")
        await session.send(
            "\r\nRuskle turns your salvage over twice, checks the moving part, then names a deliberately ordinary opening offer.\r\n"
            "'That is my price,' he says. 'Not its value. My price includes how badly I want it, how long I think it will sit, and how much I enjoy arguing with you.'\r\n"
            "You can ACCEPT OFFER, COUNTER FAIR, COUNTER HIGH, or WALK AWAY.\r\n"
        )
        return True
    await session.send("\r\nRuskle drums his fingers on the counter. 'Offer is still open until one of us changes our mind.'\r\n")
    return True


async def _finish_bargain(session, outcome: str) -> bool:
    quest = _quest(session, WHATS_IT_WORTH)
    if quest is None or quest.get("status") != "active" or quest.get("current_step") != "bargain":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_BRASSGUT_MARKET_KEY:
        return False

    if outcome == "high":
        await session.send(
            "\r\nRuskle laughs once. 'No.' He slides the piece back toward you. 'A counteroffer is not a spell. You still need somebody on the other side willing to say yes.'\r\n"
            "The negotiation remains open. Try COUNTER FAIR, ACCEPT OFFER, or WALK AWAY.\r\n"
        )
        return True

    if outcome == "accept":
        lead = "You accept the first offer. Ruskle nods. 'Fast certainty has value too. Do not let loud hagglers convince you every deal needs three rounds.'"
    elif outcome == "fair":
        lead = "You make a firmer but plausible counter. Ruskle narrows his eyes, considers the resale risk, and finally taps the counter once. 'That one I can live with.'"
    else:
        lead = "You take the piece back instead. Ruskle shrugs. 'Walking away is a price decision too. If nobody has to trade, nobody owes the market a sale.'"

    _complete_and_start(session, WHATS_IT_WORTH, SOMEBODY_ELSES_MARK, "meet_owner")
    await session.send(
        "\r\n" + lead + "\r\n"
        "Before the deal can go any farther, Ruskle scrapes mud from the underside and stops. A faded personal claim mark appears beneath the grime.\r\n"
        "'Well. Price lesson over. Ownership lesson starts now.' He makes a rubbing of the mark. 'Ledger Hall. Nalla says the old claimant is Sella Reedmark, and Sella is very much not dead.'\r\n"
        "Quest complete: What's It Worth?\r\n"
        "New quest: Somebody Else's Mark. Go to the Ledger Hall and TALK SELLA.\r\n"
    )
    return True


async def _talk_sella(session) -> bool:
    quest = _quest(session, SOMEBODY_ELSES_MARK)
    if quest is None or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_LEDGER_HALL_KEY:
        await session.send("Sella Reedmark is waiting in the Ledger Hall.\r\n")
        return True
    if quest.get("current_step") == "meet_owner":
        session.database.advance_quest(session.character.id, SOMEBODY_ELSES_MARK.key, "resolve_claim")
        await session.send(
            "\r\nSella compares Ruskle's rubbing with a mark in an old ledger and gives you a long, level look.\r\n"
            "'That was mine. Lost on a flood haul years ago. I never filed recovery because I thought the whole rig sank.'\r\n"
            "She does not reach for your bag. 'You have choices. RETURN SALVAGE if you think the old claim still settles it. CHECK OLD CLAIM if you want to test whether it legally expired. Or NEGOTIATE CLAIM if you want the piece and do not care to make a courtroom out of it.'\r\n"
        )
        return True
    await session.send("\r\nSella waits. 'I said I can live with any answer that leaves a record.'\r\n")
    return True


async def _resolve_claim(session, outcome: str) -> bool:
    quest = _quest(session, SOMEBODY_ELSES_MARK)
    if quest is None or quest.get("status") != "active" or quest.get("current_step") != "resolve_claim":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_LEDGER_HALL_KEY:
        return False

    if outcome == "check":
        session.database.grant_flag(session.character.id, RATTLEFEN_CLAIM_CHECKED_FLAG)
        await session.send(
            "\r\nNalla pulls the old claim book and finds the rule attached to Sella's mark: an unrecovered flood-loss claim expires after the owner records the loss and two full salvage seasons pass without recovery. Both conditions are recorded here.\r\n"
            "You now have enough evidence to PROVE CLAIM EXPIRED if that is the settlement you want. RETURN SALVAGE and NEGOTIATE CLAIM remain valid too.\r\n"
        )
        return True

    flags = _flags(session)
    if outcome == "expired" and RATTLEFEN_CLAIM_CHECKED_FLAG not in flags:
        await session.send("\r\nYou cannot prove an expiration you have not checked. Use CHECK OLD CLAIM first.\r\n")
        return True

    if outcome == "return":
        salvage_key = _active_salvage_key(session)
        if salvage_key:
            _consume_all(session, salvage_key)
        _ensure_one(session, GIFT_HOUSING_KEY)
        session.database.grant_flag(session.character.id, RATTLEFEN_DISPUTE_RETURN_FLAG)
        text = (
            "You return the disputed piece. Sella accepts it without triumph, then digs through her own haul bag and hands you a bent signal housing. "
            "'This one is mine, and now I give it to you. Clean transfer. Marks should work in both directions.'"
        )
    elif outcome == "expired":
        session.database.grant_flag(session.character.id, RATTLEFEN_DISPUTE_EXPIRED_FLAG)
        text = (
            "You point to the loss record and the expired recovery window. Sella reads the same lines, grunts once, and signs the old claim closed. "
            "'Then it is yours. Not because you shouted louder. Because the record says the old obligation ended.'"
        )
    else:
        session.database.grant_flag(session.character.id, RATTLEFEN_DISPUTE_NEGOTIATE_FLAG)
        text = (
            "You offer Sella a clean provenance share: her old mark remains recorded in the history of the piece, but the present salvage claim transfers to you. "
            "She considers it, adds one condition about future resale disclosure, and signs. 'Good. Cheaper than a feud.'"
        )

    _complete_and_start(session, SOMEBODY_ELSES_MARK, BETTER_THAN_IT_WAS, "meet_brin")
    await session.send(
        "\r\n" + text + "\r\n"
        "Nalla copies the settlement into the ledger. Nobody declares you morally correct. The dispute is simply settled.\r\n"
        "Quest complete: Somebody Else's Mark.\r\n"
        "New quest: Better Than It Was. Take the salvage you legitimately ended up with to Tinker Row and TALK BRIN.\r\n"
    )
    return True


async def _talk_brin(session) -> bool:
    quest = _quest(session, BETTER_THAN_IT_WAS)
    if quest is None or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_TINKER_ROW_KEY:
        await session.send("Brin Copperhand works the starter bench on Tinker Row.\r\n")
        return True
    if quest.get("current_step") == "meet_brin":
        session.database.advance_quest(session.character.id, BETTER_THAN_IT_WAS.key, "repurpose")
        await session.send(
            "\r\nBrin studies what you brought, then pushes three repair tools aside and reaches for a completely different tray.\r\n"
            "'No. We are not fixing it back into what it was. If the old thing was so perfect, it would not be sitting on my bench as salvage.'\r\n"
            "He points to bins marked LIGHT, SPRING, HOLD, TURN, and WEIRD BUT KEEP. 'REPURPOSE SALVAGE. Make the part answer a new question.'\r\n"
        )
        return True
    await session.send("\r\nBrin taps the starter bench. 'Whenever you are done mourning the machine it used to be: REPURPOSE SALVAGE.'\r\n")
    return True


async def _repurpose(session) -> bool:
    quest = _quest(session, BETTER_THAN_IT_WAS)
    if quest is None or quest.get("status") != "active" or quest.get("current_step") != "repurpose":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_TINKER_ROW_KEY:
        return False
    salvage_key = _active_salvage_key(session)
    if salvage_key is None:
        _ensure_one(session, GIFT_HOUSING_KEY)
        salvage_key = GIFT_HOUSING_KEY
    _consume_all(session, salvage_key)
    _ensure_one(session, RATTLELIGHT_KEY)
    _ensure_one(session, EARTH_TOKEN_KEY)
    _complete_and_start(session, BETTER_THAN_IT_WAS, THING_HUMANS_BUY, "show_token")
    await session.send(
        "\r\nYou and Brin strip the piece for the parts that still deserve another life. A spring becomes a latch, a hinge becomes an aimable shutter, ceramic becomes an insulator, and mismatched scraps become a palm-sized blinking signal lamp.\r\n"
        "Brin shakes it. It rattles. The light stays on. 'Rattlelight. Better.'\r\n"
        "When you pry apart one sealed backing plate, a tiny corroded token drops onto the bench. Old Human lettering is still visible beneath the green tarnish. Brin weighs it in his palm and snorts. 'Terrible metal. Humans will probably pay stupidly for it.'\r\n"
        "Quest complete: Better Than It Was.\r\n"
        "New quest: The Thing Humans Buy. Take the Stamped Earth Token to Mara Vale in Brassgut Market and TALK MARA.\r\n"
    )
    return True


async def _talk_mara(session) -> bool:
    quest = _quest(session, THING_HUMANS_BUY)
    if quest is None or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_BRASSGUT_MARKET_KEY:
        await session.send("Mara Vale is examining old curios in Brassgut Market.\r\n")
        return True
    if quest.get("current_step") == "show_token":
        session.database.advance_quest(session.character.id, THING_HUMANS_BUY.key, "decide_token")
        await session.send(
            "\r\nMara takes the token by its edges. Her expression changes before she has even finished cleaning the lettering.\r\n"
            "'Earth.' The word comes out quietly. 'I cannot tell you what this bought there, or whose hand carried it. That knowledge is gone. But the script is old Human script. It came from the world our ancestors lost.'\r\n"
            "She offers a sealed roll of clean precision tools in exchange. The tool roll is obviously more useful than the token. That fact appears completely irrelevant to her.\r\n"
            "You can SELL TOKEN or KEEP TOKEN.\r\n"
        )
        return True
    await session.send("\r\nMara leaves the choice with you. 'I want it. That does not mean you owe it to me.'\r\n")
    return True


async def _decide_token(session, sell: bool) -> bool:
    quest = _quest(session, THING_HUMANS_BUY)
    if quest is None or quest.get("status") != "active" or quest.get("current_step") != "decide_token":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_BRASSGUT_MARKET_KEY:
        return False
    if sell:
        _consume_all(session, EARTH_TOKEN_KEY)
        _ensure_one(session, HUMAN_TOOL_ROLL_KEY)
        session.database.grant_flag(session.character.id, RATTLEFEN_TOKEN_SOLD_FLAG)
        text = (
            "You trade the token. Mara hands over the sealed tool roll without bargaining down her own offer. To a Goblin eye, you received the more useful object. To Mara, the exchange plainly runs the other direction."
        )
    else:
        session.database.grant_flag(session.character.id, RATTLEFEN_TOKEN_KEPT_FLAG)
        text = (
            "You keep the token. Mara looks disappointed but not offended. 'Fair. Knowing why I value it does not make it mine.' The useless little disk suddenly feels more complicated than it did on Brin's bench."
        )
    _complete_and_start(session, THING_HUMANS_BUY, YOUR_MARK, "talk_vikka")
    await session.send(
        "\r\n" + text + "\r\n"
        "Quest complete: The Thing Humans Buy.\r\n"
        "New quest: Your Mark. Return to Vikka Three-Nails at the Clattergate and TALK VIKKA.\r\n"
    )
    return True


async def _talk_vikka(session) -> bool:
    quest = _quest(session, YOUR_MARK)
    if quest is None or quest.get("status") != "active":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_START_ROOM_KEY:
        await session.send("Vikka Three-Nails is at the Clattergate intake counter.\r\n")
        return True
    if quest.get("current_step") == "talk_vikka":
        session.database.advance_quest(session.character.id, YOUR_MARK.key, "choose_mark")
        await session.send(
            "\r\nVikka listens to the whole chain without pretending any one decision was the point. Claim. Price. Old ownership. New use. Human value. Then she slides a blank steel punch across the counter.\r\n"
            "'Good. You have argued with enough parts of the city that your arguments can have a signature now.'\r\n"
            "Choose a starter mark for the registry: MARK HOOK, MARK SPIRAL, or MARK BOLT. The shape is yours because the ledger ties it to you, not because nobody else has ever drawn a hook before.\r\n"
        )
        return True
    await session.send("\r\nVikka taps the blank punch. 'Hook, spiral, or bolt. Pick one. You can invent poetry about it later.'\r\n")
    return True


async def _choose_mark(session, mark: str) -> bool:
    quest = _quest(session, YOUR_MARK)
    if quest is None or quest.get("status") != "active" or quest.get("current_step") != "choose_mark":
        return False
    assert session.character is not None
    if session.character.current_room != GOBLIN_START_ROOM_KEY:
        return False
    flag = {
        "hook": RATTLEFEN_MARK_HOOK_FLAG,
        "spiral": RATTLEFEN_MARK_SPIRAL_FLAG,
        "bolt": RATTLEFEN_MARK_BOLT_FLAG,
    }[mark]
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, RATTLEFEN_PERSONAL_MARK_FLAG)
    session.database.grant_flag(session.character.id, RATTLEFEN_OPENING_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, YOUR_MARK.key)
    _ensure_one(session, PERSONAL_STAMP_KEY)
    _ensure_legacy_credit(session)
    await session.send(
        f"\r\nVikka cuts the {mark.upper()} pattern into the punch, stamps it once into soft lead, and files the impression under your name.\r\n"
        "'There. Your mark. Put it on what you can actually claim, not what you merely want.'\r\n"
        "Around you, Rattlefen keeps shouting, hauling, repairing, buying, cheating badly, catching the cheating, and finding new uses for old things. Nobody rings a heroic bell. You simply have standing here now.\r\n"
        "Quest complete: Your Mark. Your personal salvage mark and first salvage credit are registered.\r\n"
        "The Bargain Gate at Floodgate Walk leads toward the wider swamp routes. TALK RUSKLE when you are ready for the existing first supervised route beyond the painted line.\r\n"
    )
    return True


async def _handle_opening_action(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "goblin":
        return False
    room = session.character.current_room

    first = _quest(session, THREE_BELLS)
    if first and first.get("status") == "active":
        step = first.get("current_step")
        if room == GOBLIN_SORTING_SPINE_KEY and normalized in {
            "examine fresh wreck", "look fresh wreck", "examine wreck", "look wreck", "examine salvage drop", "look salvage drop"
        }:
            if step == "inspect_wreck":
                session.database.advance_quest(session.character.id, THREE_BELLS.key, "choose_salvage")
            await session.send(
                "\r\nThe big pieces are obvious and mostly worthless. The interesting pieces are smaller: a BENT SPRING CAGE that still moves evenly, a CRACKED LENS FRAME with a fine adjustable hinge, and a SEALED CERAMIC SWITCHPLATE protected from the swamp by its own casing.\r\n"
                "Your single brass tag can claim only one: CLAIM SPRING, CLAIM LENS, or CLAIM SWITCHPLATE.\r\n"
            )
            return True
        choice = {
            "claim spring": (SPRING_CAGE_KEY, RATTLEFEN_CHOICE_SPRING_FLAG, "Bent Spring Cage"),
            "claim spring cage": (SPRING_CAGE_KEY, RATTLEFEN_CHOICE_SPRING_FLAG, "Bent Spring Cage"),
            "claim lens": (LENS_FRAME_KEY, RATTLEFEN_CHOICE_LENS_FLAG, "Cracked Lens Frame"),
            "claim lens frame": (LENS_FRAME_KEY, RATTLEFEN_CHOICE_LENS_FLAG, "Cracked Lens Frame"),
            "claim switch": (SWITCHPLATE_KEY, RATTLEFEN_CHOICE_SWITCH_FLAG, "Sealed Ceramic Switchplate"),
            "claim switchplate": (SWITCHPLATE_KEY, RATTLEFEN_CHOICE_SWITCH_FLAG, "Sealed Ceramic Switchplate"),
        }.get(normalized)
        if choice is not None and room == GOBLIN_SORTING_SPINE_KEY:
            if step != "choose_salvage":
                await session.send("\r\nLook at the fresh wreck before spending your one claim tag. EXAMINE FRESH WRECK.\r\n")
                return True
            item_key, flag, name = choice
            _consume_all(session, CLAIM_TAG_KEY)
            _ensure_one(session, item_key)
            session.database.grant_flag(session.character.id, flag)
            _complete_and_start(session, THREE_BELLS, WHATS_IT_WORTH, "seek_broker")
            await session.send(
                f"\r\nYou press your one brass claim tag onto the {name}. The other two pieces remain in the public lot for somebody else.\r\n"
                "Nobody congratulates you for taking the biggest object, because you did not. You picked the one you think still has a future.\r\n"
                "Quest complete: Three Bells.\r\n"
                "New quest: What's It Worth? Take your claimed piece to Ruskle Coil in Brassgut Market and TALK RUSKLE.\r\n"
            )
            return True

    if normalized in {"accept offer", "accept", "take offer"}:
        return await _finish_bargain(session, "accept")
    if normalized in {"counter fair", "fair counter", "counter reasonable"}:
        return await _finish_bargain(session, "fair")
    if normalized in {"counter high", "high counter", "demand more"}:
        return await _finish_bargain(session, "high")
    if normalized in {"walk away", "decline offer", "keep salvage"}:
        return await _finish_bargain(session, "walk")

    claim = _quest(session, SOMEBODY_ELSES_MARK)
    if claim and claim.get("status") == "active":
        if normalized in {"check old claim", "read old claim", "examine old claim", "check claim", "read claim record"}:
            return await _resolve_claim(session, "check")
        if normalized in {"return salvage", "give back salvage", "return claim"}:
            return await _resolve_claim(session, "return")
        if normalized in {"prove claim expired", "prove expired", "claim expired"}:
            return await _resolve_claim(session, "expired")
        if normalized in {"negotiate claim", "negotiate ownership", "bargain claim"}:
            return await _resolve_claim(session, "negotiate")

    if normalized in {"repurpose salvage", "repurpose", "make something else", "use repurpose bench"}:
        return await _repurpose(session)
    if normalized in {"sell token", "trade token", "sell earth token"}:
        return await _decide_token(session, True)
    if normalized in {"keep token", "keep earth token", "decline token sale"}:
        return await _decide_token(session, False)
    if normalized in {"mark hook", "choose mark hook", "register hook"}:
        return await _choose_mark(session, "hook")
    if normalized in {"mark spiral", "choose mark spiral", "register spiral"}:
        return await _choose_mark(session, "spiral")
    if normalized in {"mark bolt", "choose mark bolt", "register bolt"}:
        return await _choose_mark(session, "bolt")

    return False


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def _current_rattlefen_objective(session) -> str | None:
    for definition in RATTLEFEN_QUESTS:
        state = _quest(session, definition)
        if state and state.get("status") == "active":
            return definition.objective_for_step(state.get("current_step"))
    return None


def install_rattlefen_opening_runtime(player_session_class, world_service) -> None:
    install_rattlefen_opening_content(world_service)
    if getattr(player_session_class, "_rattlefen_opening_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        fresh_candidate = (
            self.character is not None
            and self.character.race == "goblin"
            and _quest(self, THREE_BELLS) is None
            and not _legacy_started(self)
        )
        if fresh_candidate:
            # Suppress the older generic one-line Goblin welcome. The richer
            # Rattlefen opening below now owns the new-character first beat.
            self.database.grant_flag(self.character.id, "goblin_junk_city_welcomed")
        await previous_enter_character(self)
        if self.character is None or self.character.race != "goblin":
            return
        started = reconcile_rattlefen_opening(self)
        if started:
            await self.send(
                "\r\nThree fast bells crack across Rattlefen from the Sorting Spine. Conversations bend around the sound without stopping. A fresh salvage lot has just been opened.\r\n"
                "Vikka Three-Nails slaps one plain brass claim tag onto the intake counter in front of you. 'Starter rule. One tag. One piece. If you cannot decide what is worth carrying, the swamp will happily make the decision for you.'\r\n"
                "\r\nNew quest: Three Bells. Go NORTH to the Sorting Spine and EXAMINE FRESH WRECK.\r\n"
            )
        else:
            objective = _current_rattlefen_objective(self)
            if objective and RATTLEFEN_OPENING_COMPLETE_FLAG not in _flags(self):
                await self.send(f"\r\nRattlefen starter objective: {objective}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "goblin":
            await previous_playing_prompt(self)
            return

        reconcile_rattlefen_opening(self)
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"rattlefen", "city", "junk city", "district", "where am i"}:
            await self.send(
                "\r\n--- Rattlefen ---\r\n"
                "Rattlefen is the Goblin salvage city older ledgers and many outsiders still call Junk City. Its safe core runs from the Clattergate through Brassgut Market, the Sorting Spine, Patchwork Plaza, Tinker Row, and the Ledger Hall to the Bargain Gate at Floodgate Walk. It is crowded, transactional, improvised, and home.\r\n"
                "Goblin craft asks a different question from restoration: not only 'what was this built to do?' but 'what else can this do now?'\r\n"
            )
            return

        if await _handle_opening_action(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _target_after_talk(command)
            opening_incomplete = RATTLEFEN_OPENING_COMPLETE_FLAG not in _flags(self) and _quest(self, THREE_BELLS) is not None
            if _is_target(target, "ruskle", "ruskle coil", "broker", "salvage broker"):
                if await _talk_ruskle(self):
                    return
                if opening_incomplete:
                    await self.send("\r\nRuskle is not the next part of your current Rattlefen lesson. Check QUESTS for the active objective.\r\n")
                    return
            if _is_target(target, "sella", "sella reedmark", "reedmark") and await _talk_sella(self):
                return
            if _is_target(target, "brin", "brin copperhand", "repairer") and await _talk_brin(self):
                return
            if _is_target(target, "mara", "mara vale", "human factor", "factor") and await _talk_mara(self):
                return
            if _is_target(target, "vikka", "vikka three-nails", "intake clerk", "clerk"):
                if await _talk_vikka(self):
                    return
                if opening_incomplete:
                    await self.send("\r\nVikka points toward your current starter business. 'Finish the thing in front of you. Then come back and make it a story.'\r\n")
                    return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {"help", "?"}:
            await self.send(
                "Rattlefen opening: Three Bells uses EXAMINE FRESH WRECK and one CLAIM choice. Bargaining uses ACCEPT OFFER / COUNTER FAIR / COUNTER HIGH / WALK AWAY. Ownership uses TALK SELLA plus RETURN SALVAGE, CHECK OLD CLAIM + PROVE CLAIM EXPIRED, or NEGOTIATE CLAIM. Then TALK BRIN + REPURPOSE SALVAGE, TALK MARA + SELL TOKEN/KEEP TOKEN, and finally TALK VIKKA + MARK HOOK/SPIRAL/BOLT.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._rattlefen_opening_runtime_installed = True
