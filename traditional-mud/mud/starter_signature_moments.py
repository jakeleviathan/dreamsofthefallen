from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
from mud.crafting import ItemDefinition
from mud.dwarf_start import DWARF_FIRST_OBLIGATION_FLAG, DWARF_UPPER_FREIGHT_KEY
from mud.goblin_rattlefen_opening import (
    RATTLEFEN_MARK_BOLT_FLAG,
    RATTLEFEN_MARK_HOOK_FLAG,
    RATTLEFEN_MARK_SPIRAL_FLAG,
    RATTLEFEN_OPENING_COMPLETE_FLAG,
)
from mud.goblin_start import GOBLIN_TINKER_ROW_KEY
from mud.human_blackwall_opening import HUMAN_GATE_CLEARANCE_FLAG, HUMAN_OUTER_CARAVAN_ROAD_KEY
from mud.moon_elf_city import MOON_ELF_SKYCOURT_KEY
from mud.moon_elf_third_chair import (
    MOON_ELF_CHOICE_KEEP_FLAG,
    MOON_ELF_CHOICE_NEIGHBORS_FLAG,
    MOON_ELF_CHOICE_REDRAW_FLAG,
    MOON_ELF_CHOICE_WIND_FLAG,
    MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG,
)
from mud.quests import SPOREKIN_FIRST_CALL
from mud.room_engine import DescriptionLayer, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.troll_start import TROLL_COLD_COMPLETE_FLAG, TROLL_STONEJAW_PASS_KEY
from mud.undead_start import UNDEAD_DESERT_GATE_KEY, UNDEAD_ORDERS_SEVERED_FLAG
from mud.world import SPOREKIN_MEMORY_PATH_ROOM_KEY, SPOREKIN_SURFACE_VERGE_ROOM_KEY


# These moments deliberately do not add another formal quest chain. They are
# small one-time consequences layered onto the already-authored race openings.
# Forest Elves have their equivalent in forest_elf_reading_forest.py.

HUMAN_SIGNATURE_SEEN_FLAG = "human_signature_roadside_seen"
HUMAN_SIGNATURE_WAGON_READ_FLAG = "human_signature_wagon_read"
HUMAN_SIGNATURE_COMPLETE_FLAG = "human_signature_roadside_chock"

MOON_SIGNATURE_SEEN_FLAG = "moon_elf_signature_result_seen"
MOON_SIGNATURE_COMPLETE_FLAG = "moon_elf_signature_result_read"

DWARF_SIGNATURE_SEEN_FLAG = "dwarf_signature_brake_seen"
DWARF_SIGNATURE_BRAKE_CHECKED_FLAG = "dwarf_signature_brake_checked"
DWARF_SIGNATURE_COMPLETE_FLAG = "dwarf_signature_brake_tagged"

GOBLIN_SIGNATURE_SEEN_FLAG = "goblin_signature_scrap_seen"
GOBLIN_SIGNATURE_APPRAISED_FLAG = "goblin_signature_scrap_appraised"
GOBLIN_SIGNATURE_CLIP_FLAG = "goblin_signature_made_clip"
GOBLIN_SIGNATURE_LURE_FLAG = "goblin_signature_made_lure"

TROLL_SIGNATURE_SEEN_FLAG = "troll_signature_drift_seen"
TROLL_SIGNATURE_DRIFT_READ_FLAG = "troll_signature_drift_read"
TROLL_SIGNATURE_STUMBLED_FLAG = "troll_signature_drift_stumbled"
TROLL_SIGNATURE_COMPLETE_FLAG = "troll_signature_pass_safe"

UNDEAD_SIGNATURE_SEEN_FLAG = "undead_signature_bell_seen"
UNDEAD_SIGNATURE_BELL_HEARD_FLAG = "undead_signature_bell_heard"
UNDEAD_SIGNATURE_COMPLETE_FLAG = "undead_signature_reflex_released"

SPOREKIN_SIGNATURE_SEEN_FLAG = "sporekin_signature_fork_seen"
SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG = "sporekin_signature_chorus_listened"
SPOREKIN_SIGNATURE_RAIN_FLAG = "sporekin_signature_rain_choice"
SPOREKIN_SIGNATURE_STONE_FLAG = "sporekin_signature_stone_choice"
SPOREKIN_SIGNATURE_COMPLETE_FLAG = "sporekin_signature_individual_route"
SPOREKIN_SIGNATURE_ECHO_FLAG = "sporekin_signature_choice_echoed"


GOBLIN_PACK_CLIP_KEY = "goblin_springjaw_pack_clip"
GOBLIN_REED_LURE_KEY = "goblin_rattlefen_reed_lure"

GOBLIN_PACK_CLIP = ItemDefinition(
    key=GOBLIN_PACK_CLIP_KEY,
    name="Springjaw Pack Clip",
    description=(
        "A compact spring clip made from a warped salvage cage. The old machine is gone; what remains "
        "is a useful fastener with a faintly ridiculous amount of clamping force."
    ),
    category="keepsake",
    tier=0,
)

GOBLIN_REED_LURE = ItemDefinition(
    key=GOBLIN_REED_LURE_KEY,
    name="Rattlefen Reed Lure",
    description=(
        "A small clicking fish lure made from the same kind of spring cage somebody else would have "
        "thrown away. It rattles unevenly in exactly the way swamp fish seem to notice."
    ),
    category="keepsake",
    tier=0,
)

GOBLIN_SIGNATURE_ITEMS = (GOBLIN_PACK_CLIP, GOBLIN_REED_LURE)


SIGNATURE_MOMENTS = {
    "human": {
        "room": HUMAN_OUTER_CARAVAN_ROAD_KEY,
        "completion_flag": HUMAN_SIGNATURE_COMPLETE_FLAG,
        "hook": "An outsider says 'Demon' until ordinary competence gives them a better word.",
    },
    "moon_elf": {
        "room": MOON_ELF_SKYCOURT_KEY,
        "completion_flag": MOON_SIGNATURE_COMPLETE_FLAG,
        "hook": "A civic choice returns as a provisional public result rather than a correct-answer stamp.",
    },
    "dwarf": {
        "room": DWARF_UPPER_FREIGHT_KEY,
        "completion_flag": DWARF_SIGNATURE_COMPLETE_FLAG,
        "hook": "Good engineering means taking a suspect machine out of service before it becomes dramatic.",
    },
    "goblin": {
        "room": GOBLIN_TINKER_ROW_KEY,
        "completion_flag": (GOBLIN_SIGNATURE_CLIP_FLAG, GOBLIN_SIGNATURE_LURE_FLAG),
        "hook": "One useless old part becomes one of two useful new things because the player decides what it is for now.",
    },
    "troll": {
        "room": TROLL_STONEJAW_PASS_KEY,
        "completion_flag": TROLL_SIGNATURE_COMPLETE_FLAG,
        "hook": "The shortest route is dangerous unless the player actually reads the snow.",
    },
    "undead": {
        "room": UNDEAD_DESERT_GATE_KEY,
        "completion_flag": UNDEAD_SIGNATURE_COMPLETE_FLAG,
        "hook": "An old command cadence can still trigger a reflex without possessing any authority.",
    },
    "sporekin": {
        "room": SPOREKIN_SURFACE_VERGE_ROOM_KEY,
        "completion_flag": SPOREKIN_SIGNATURE_COMPLETE_FLAG,
        "hook": "The Chorus presents two equally valid routes and leaves the individual to choose.",
    },
}


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    overrides = {value.direction: value for value in existing.exit_overrides}
    overrides.update({value.direction: value for value in extra.exit_overrides})
    extras = {(value.direction, value.destination_key): value for value in existing.extra_exits}
    extras.update({(value.direction, value.destination_key): value for value in extra.extra_exits})
    features = {value.key: value for value in existing.features}
    features.update({value.key: value for value in extra.features})
    layers = {value.key: value for value in existing.description_layers}
    layers.update({value.key: value for value in extra.description_layers})
    return replace(
        existing,
        exit_overrides=tuple(overrides.values()),
        extra_exits=tuple(extras.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


def signature_moment_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HUMAN_OUTER_CARAVAN_ROAD_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="foreign_wagon_chock",
                    name="Crooked Foreign Wagon",
                    aliases=("wagon", "foreign wagon", "wheel", "wheel chock", "chock"),
                    summary="a road-stained wagon whose rear wheel is beginning to creep on the grade",
                    examine_text=(
                        "The wagon itself is sound. The problem is smaller: a wheel chock was kicked sideways during unloading, "
                        "and the rear wheel has started to press over its edge. The driver is still arguing with a cargo strap."
                    ),
                    condition=ViewCondition(
                        races=("human",),
                        required_flags=(HUMAN_GATE_CLEARANCE_FLAG,),
                        forbidden_flags=(HUMAN_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="human_signature_after_chock",
                    text="A pair of fresh wedge marks beside the road are a small reminder that the first problem you solved outside Blackwall was not a monster, prophecy, or diplomatic crisis. It was a rolling wagon.",
                    priority=72,
                    condition=ViewCondition(
                        races=("human",), required_flags=(HUMAN_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
        MOON_ELF_SKYCOURT_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="third_chair_result_board",
                    name="Third Chair Result Notice",
                    aliases=("result", "result notice", "third chair result", "notice", "result board"),
                    summary="a fresh civic notice posted beneath the public mediation schedule",
                    examine_text=(
                        "The heading names the orchard-path dispute you helped mediate. Below it is a short procedural update, "
                        "not a declaration that anybody won. READ RESULT to see what happened next."
                    ),
                    condition=ViewCondition(
                        races=("moon_elf",),
                        required_flags=(MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG,),
                        forbidden_flags=(MOON_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="moon_signature_result_remains",
                    text="The orchard-path result notice remains among dozens of other civic updates. Your first public decision has already become ordinary city paperwork.",
                    priority=68,
                    condition=ViewCondition(
                        races=("moon_elf",), required_flags=(MOON_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
        DWARF_UPPER_FREIGHT_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="chattering_freight_brake",
                    name="Chattering Freight Brake",
                    aliases=("brake", "freight brake", "handcart", "cart", "red tag"),
                    summary="an unattended ore handcart making one wrong metallic click every wheel turn",
                    examine_text=(
                        "The cart is parked and chained, but the brake pawl chatters against its ratchet instead of seating cleanly. "
                        "Nothing has failed yet. That is exactly why there is still time to inspect it properly."
                    ),
                    listen_text="Click. Roll. Click. Roll. One tooth sounds thinner than the rest.",
                    condition=ViewCondition(
                        races=("dwarf",),
                        required_flags=(DWARF_FIRST_OBLIGATION_FLAG,),
                        forbidden_flags=(DWARF_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="dwarf_signature_red_tag",
                    text="A red OUT OF SERVICE tag hangs from one freight cart's brake lever. Traffic simply routes around it while maintenance handles the defect.",
                    priority=72,
                    condition=ViewCondition(
                        races=("dwarf",), required_flags=(DWARF_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
        GOBLIN_TINKER_ROW_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="weird_but_keep_spring",
                    name="Warped Spring Cage",
                    aliases=("scrap", "spring cage", "warped spring", "weird but keep", "spring"),
                    summary="a bent spring cage sitting in the WEIRD BUT KEEP bin",
                    examine_text=(
                        "The original mechanism is beyond sensible repair, but the spring still snaps shut evenly and the frame has two good mounting holes. "
                        "That makes it useless for what it was and potentially useful for several things it has never been."
                    ),
                    condition=ViewCondition(
                        races=("goblin",),
                        required_flags=(RATTLEFEN_OPENING_COMPLETE_FLAG,),
                        forbidden_flags=(GOBLIN_SIGNATURE_CLIP_FLAG, GOBLIN_SIGNATURE_LURE_FLAG),
                    ),
                ),
            ),
        ),
        TROLL_STONEJAW_PASS_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="lying_drift",
                    name="Smooth White Drift",
                    aliases=("drift", "snow drift", "white drift", "snow", "short route", "lee route"),
                    summary="a clean-looking drift covering the shortest line through Stonejaw Pass",
                    examine_text=(
                        "From camp it would look like easy snow. Up close the wind has polished the top while stealing support from underneath. "
                        "A lower line along the lee-side stones is longer and uglier. READ DRIFT before trusting either."
                    ),
                    condition=ViewCondition(
                        races=("troll",),
                        required_flags=(TROLL_COLD_COMPLETE_FLAG,),
                        forbidden_flags=(TROLL_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="troll_signature_lee_marks",
                    text="A few heavy footprints now follow the less impressive lee-side stones around the smooth drift. The longer line is the safer line.",
                    priority=72,
                    condition=ViewCondition(
                        races=("troll",), required_flags=(TROLL_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
        UNDEAD_DESERT_GATE_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="gate_shift_bell",
                    name="Gate Shift Bell",
                    aliases=("bell", "shift bell", "gate bell", "cadence"),
                    summary="a three-note brass bell used to mark ordinary gate shift changes",
                    examine_text=(
                        "Three notes, descending. The cadence is civic and harmless now, but some buried motor memory in your frame recognizes a rhythm "
                        "that once meant stand, turn, await command. LISTEN BELL if you want to face the reflex directly."
                    ),
                    listen_text="Three notes descend through the stone. No command rides inside them.",
                    condition=ViewCondition(
                        races=("undead",),
                        required_flags=(UNDEAD_ORDERS_SEVERED_FLAG,),
                        forbidden_flags=(UNDEAD_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="undead_signature_bell_after",
                    text="The gate bell marks another shift change. Your hands do nothing unless you decide they should.",
                    priority=72,
                    condition=ViewCondition(
                        races=("undead",), required_flags=(UNDEAD_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
        SPOREKIN_SURFACE_VERGE_ROOM_KEY: RoomAugmentation(
            features=(
                FeatureDefinition(
                    key="chorus_fork",
                    name="Two-Thread Fork",
                    aliases=("fork", "chorus", "two threads", "rain route", "stone route", "routes"),
                    summary="two faint Chorus impressions pulling with exactly equal confidence in different directions",
                    examine_text=(
                        "One remembered route carries the feel of rain on leaves. The other carries warm stone and open sky. "
                        "Neither impression is stronger, older, safer, or more approved. LISTEN CHORUS and you may discover that there is no consensus to obey."
                    ),
                    condition=ViewCondition(
                        races=("sporekin",),
                        required_flags=("sporekin_first_call_answered",),
                        forbidden_flags=(SPOREKIN_SIGNATURE_COMPLETE_FLAG,),
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="sporekin_signature_fork_after",
                    text="At the old two-thread fork, both remembered routes still feel equally real. One of them is also yours now, because you chose it.",
                    priority=72,
                    condition=ViewCondition(
                        races=("sporekin",), required_flags=(SPOREKIN_SIGNATURE_COMPLETE_FLAG,)
                    ),
                ),
            ),
        ),
    }


def install_signature_moment_content(world_service=None) -> None:
    known_items = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in GOBLIN_SIGNATURE_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    if world_service is None:
        return
    for room_key, augmentation in signature_moment_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(
            world_service.augmentations.get(room_key), augmentation
        )
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in signature_moment_augmentations():
            cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _has_any(flags: set[str], *keys: str) -> bool:
    return any(key in flags for key in keys)


def _sporekin_first_call_complete(session) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    if "sporekin_first_call_answered" in flags:
        return True
    quest = session.database.get_quest(session.character.id, SPOREKIN_FIRST_CALL.key)
    return bool(quest and quest.get("status") == "completed")


def _moment_ready(session, race: str | None = None) -> bool:
    character = session.character
    if character is None:
        return False
    race_key = race or character.race
    flags = _flags(session)
    if race_key == "human":
        return character.current_room == HUMAN_OUTER_CARAVAN_ROAD_KEY and HUMAN_GATE_CLEARANCE_FLAG in flags and HUMAN_SIGNATURE_COMPLETE_FLAG not in flags
    if race_key == "moon_elf":
        return character.current_room == MOON_ELF_SKYCOURT_KEY and MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG in flags and MOON_SIGNATURE_COMPLETE_FLAG not in flags
    if race_key == "dwarf":
        return character.current_room == DWARF_UPPER_FREIGHT_KEY and DWARF_FIRST_OBLIGATION_FLAG in flags and DWARF_SIGNATURE_COMPLETE_FLAG not in flags
    if race_key == "goblin":
        return character.current_room == GOBLIN_TINKER_ROW_KEY and RATTLEFEN_OPENING_COMPLETE_FLAG in flags and not _has_any(flags, GOBLIN_SIGNATURE_CLIP_FLAG, GOBLIN_SIGNATURE_LURE_FLAG)
    if race_key == "troll":
        return character.current_room == TROLL_STONEJAW_PASS_KEY and TROLL_COLD_COMPLETE_FLAG in flags and TROLL_SIGNATURE_COMPLETE_FLAG not in flags
    if race_key == "undead":
        return character.current_room == UNDEAD_DESERT_GATE_KEY and UNDEAD_ORDERS_SEVERED_FLAG in flags and UNDEAD_SIGNATURE_COMPLETE_FLAG not in flags
    if race_key == "sporekin":
        return character.current_room == SPOREKIN_SURFACE_VERGE_ROOM_KEY and _sporekin_first_call_complete(session) and SPOREKIN_SIGNATURE_COMPLETE_FLAG not in flags
    return False


async def _announce_if_ready(session) -> bool:
    if session.character is None:
        return False
    race = session.character.race
    if not _moment_ready(session, race):
        return False
    flags = _flags(session)
    data = {
        "human": (
            HUMAN_SIGNATURE_SEEN_FLAG,
            "A foreign wagon driver glances at your Blackwall silhouette and starts with, 'Demon—' before the wagon shifts behind them. One rear wheel is beginning to move. EXAMINE WAGON or READ WAGON.\r\n",
        ),
        "moon_elf": (
            MOON_SIGNATURE_SEEN_FLAG,
            "A fresh notice beneath the Skycourt mediation schedule carries the orchard-path case number from your Third Chair session. READ RESULT.\r\n",
        ),
        "dwarf": (
            DWARF_SIGNATURE_SEEN_FLAG,
            "One unattended freight handcart makes a thin metallic click every wheel turn. Nobody is shouting because nothing has failed yet. CHECK BRAKE.\r\n",
        ),
        "goblin": (
            GOBLIN_SIGNATURE_SEEN_FLAG,
            "Something in Brin's WEIRD BUT KEEP bin snaps shut with a healthy little clack. A warped spring cage is ruined for its old job and not obviously ruined for everything else. APPRAISE SCRAP.\r\n",
        ),
        "troll": (
            TROLL_SIGNATURE_SEEN_FLAG,
            "A smooth white drift covers the shortest line through Stonejaw Pass. It looks easier than the broken lee-side stones. That is not the same thing as being safer. READ DRIFT or CROSS DRIFT.\r\n",
        ),
        "undead": (
            UNDEAD_SIGNATURE_SEEN_FLAG,
            "The Desert Gate shift bell sounds three descending notes. Your right hand twitches toward an old command posture before thought catches up. LISTEN BELL.\r\n",
        ),
        "sporekin": (
            SPOREKIN_SIGNATURE_SEEN_FLAG,
            "At a fork near the surface, the Chorus carries two route-memories with exactly equal weight: rain on leaves, warm stone under open sky. LISTEN CHORUS.\r\n",
        ),
    }.get(race)
    if data is None:
        return False
    seen_flag, text = data
    if seen_flag in flags:
        return False
    session.database.grant_flag(session.character.id, seen_flag)
    await session.send("\r\n" + text)
    return True


async def _handle_human(session, normalized: str) -> bool:
    if not _moment_ready(session, "human"):
        return False
    flags = _flags(session)
    if normalized in {"examine wagon", "look wagon", "read wagon", "inspect wagon", "examine wheel", "check wagon"}:
        session.database.grant_flag(session.character.id, HUMAN_SIGNATURE_WAGON_READ_FLAG)
        await session.send(
            "\r\nYou read the problem before touching it. The axle is fine, the road is firm, and the harness is slack. A loading crew kicked the rear wheel chock half out from under the tire. The wagon is simply beginning to roll downhill.\r\n"
            "The driver finally sees it too. SET CHOCK.\r\n"
        )
        return True
    if normalized in {"set chock", "set wheel chock", "wedge wheel", "chock wheel", "replace chock"}:
        if HUMAN_SIGNATURE_WAGON_READ_FLAG not in flags:
            await session.send("\r\nDo not start kicking pieces of a stranger's wagon at random. READ WAGON first.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_SIGNATURE_COMPLETE_FLAG)
        await session.send(
            "\r\nYou plant the chock squarely under the tire and lean your weight into it. The wagon settles with an ordinary wooden creak. No spell, weapon, or alarm was needed.\r\n"
            f"The driver exhales. 'Thanks, {session.character.name}.' The word Demon never gets finished.\r\n"
        )
        return True
    return False


def _moon_result_text(flags: set[str]) -> str:
    if MOON_ELF_CHOICE_REDRAW_FLAG in flags:
        return (
            "The survey office has redrawn the proposed path into a narrower line that preserves more of the orchard windbreak. "
            "Winter safety review remains open until the new grade is measured on the ground."
        )
    if MOON_ELF_CHOICE_KEEP_FLAG in flags:
        return (
            "The old path remains in service provisionally, but the city has ordered temporary winter rail, grit bins, and a meltwater study. "
            "Keeping the route did not make its danger disappear."
        )
    if MOON_ELF_CHOICE_WIND_FLAG in flags:
        return (
            "Colored wind ribbons and two small gauges now stand above and below the orchard. The final path decision is delayed until the city has a week of ridge data."
        )
    if MOON_ELF_CHOICE_NEIGHBORS_FLAG in flags:
        return (
            "Witnesses are interviewing the lower households that live behind the orchard windbreak. The route decision is delayed until their winter experience is part of the record."
        )
    return (
        "The case remains open for one more round of observation. High Horizon records uncertainty as a state of work, not a civic failure."
    )


async def _handle_moon_elf(session, normalized: str) -> bool:
    if not _moment_ready(session, "moon_elf"):
        return False
    if normalized not in {"read result", "read notice", "read result notice", "read third chair result", "examine result"}:
        return False
    flags = _flags(session)
    await session.send(
        "\r\nTHIRD CHAIR CASE — ORCHARD PATH\r\n"
        + _moon_result_text(flags)
        + "\r\n\r\nNo seal on the notice says CORRECT. It names the next work, the people responsible, and the date the decision will be looked at again.\r\n"
    )
    session.database.grant_flag(session.character.id, MOON_SIGNATURE_COMPLETE_FLAG)
    return True


async def _handle_dwarf(session, normalized: str) -> bool:
    if not _moment_ready(session, "dwarf"):
        return False
    flags = _flags(session)
    if normalized in {"check brake", "inspect brake", "examine brake", "listen brake", "check cart", "inspect cart"}:
        session.database.grant_flag(session.character.id, DWARF_SIGNATURE_BRAKE_CHECKED_FLAG)
        await session.send(
            "\r\nYou turn the wheel only far enough to make the brake pawl seat twice. The third tooth is chipped and the spring is beginning to cant sideways. The brake works now. It should not be trusted with a loaded cart later.\r\n"
            "There is a red maintenance tag on the rack beside the lane. TAG BRAKE.\r\n"
        )
        return True
    if normalized in {"tag brake", "red tag brake", "pull red tag", "tag cart", "mark out of service"}:
        if DWARF_SIGNATURE_BRAKE_CHECKED_FLAG not in flags:
            await session.send("\r\nA red tag takes equipment out of service. CHECK BRAKE before you shut down somebody else's cart.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_SIGNATURE_COMPLETE_FLAG)
        await session.send(
            "\r\nYou loop the red OUT OF SERVICE tag through the brake lever and write the defect number on its slate tab. The next freight crew diverts around the cart without argument. Maintenance will replace the pawl before the cart becomes a story.\r\n"
        )
        return True
    if normalized in {"kick brake", "force brake", "release brake", "use cart", "push cart"}:
        await session.send(
            "\r\nThe freight rules are built around a simple idea: if a machine is telling you something is wrong, making it move anyway is not a test of skill. CHECK BRAKE.\r\n"
        )
        return True
    return False


def _goblin_mark_name(flags: set[str]) -> str:
    if RATTLEFEN_MARK_HOOK_FLAG in flags:
        return "hook mark"
    if RATTLEFEN_MARK_SPIRAL_FLAG in flags:
        return "spiral mark"
    if RATTLEFEN_MARK_BOLT_FLAG in flags:
        return "bolt mark"
    return "personal mark"


async def _handle_goblin(session, normalized: str) -> bool:
    if not _moment_ready(session, "goblin"):
        return False
    flags = _flags(session)
    if normalized in {"appraise scrap", "appraise spring", "inspect scrap", "examine scrap", "appraise spring cage"}:
        session.database.grant_flag(session.character.id, GOBLIN_SIGNATURE_APPRAISED_FLAG)
        await session.send(
            "\r\nThe cage cannot hold alignment for its old machine, so restoring it would be expensive stupidity. But the spring closes hard, the hinge is good, and two mounting holes survived.\r\n"
            "You can make a brutal little pack fastener or a clicking swamp lure. MAKE CLIP or MAKE LURE. Same scrap. Different future.\r\n"
        )
        return True
    if normalized in {"make clip", "make pack clip", "repurpose clip"}:
        if GOBLIN_SIGNATURE_APPRAISED_FLAG not in flags:
            await session.send("\r\nAPPRAISE SCRAP before deciding what the part wants to become.\r\n")
            return True
        session.database.add_item(session.character.id, GOBLIN_PACK_CLIP_KEY, 1)
        session.database.grant_flag(session.character.id, GOBLIN_SIGNATURE_CLIP_FLAG)
        await session.send(
            f"\r\nYou flatten the useless frame, keep the good spring, and turn the old cage into a Springjaw Pack Clip. A quick punch of your {_goblin_mark_name(flags)} makes the new purpose yours.\r\n"
            "You receive: Springjaw Pack Clip.\r\n"
        )
        return True
    if normalized in {"make lure", "make fish lure", "repurpose lure"}:
        if GOBLIN_SIGNATURE_APPRAISED_FLAG not in flags:
            await session.send("\r\nAPPRAISE SCRAP before deciding what the part wants to become.\r\n")
            return True
        session.database.add_item(session.character.id, GOBLIN_REED_LURE_KEY, 1)
        session.database.grant_flag(session.character.id, GOBLIN_SIGNATURE_LURE_FLAG)
        await session.send(
            f"\r\nYou trim the cage down to a clicking little body and leave one loose plate because the ugly rattle is useful. A quick punch of your {_goblin_mark_name(flags)} finishes the Rattlefen Reed Lure.\r\n"
            "You receive: Rattlefen Reed Lure.\r\n"
        )
        return True
    return False


async def _handle_troll(session, normalized: str) -> bool:
    if not _moment_ready(session, "troll"):
        return False
    flags = _flags(session)
    if normalized in {"read drift", "examine drift", "inspect drift", "read snow", "check drift"}:
        session.database.grant_flag(session.character.id, TROLL_SIGNATURE_DRIFT_READ_FLAG)
        await session.send(
            "\r\nThe clean top is the lie. Wind packed a hard lip over softer snow and hollowed the far side around buried brush. The direct crossing could hold ten steps or collapse on the first.\r\n"
            "The lee-side stones are slower, rougher, and supported all the way through. TAKE LEE ROUTE.\r\n"
        )
        return True
    if normalized in {"cross drift", "take drift", "cross snow", "take short route", "go across drift"}:
        if TROLL_SIGNATURE_DRIFT_READ_FLAG in flags:
            await session.send("\r\nYou already know the drift is hollowed underneath. Toughness does not make bad footing good. TAKE LEE ROUTE.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_SIGNATURE_STUMBLED_FLAG)
        session.database.grant_flag(session.character.id, TROLL_SIGNATURE_DRIFT_READ_FLAG)
        combatant = getattr(session, "combatant", None)
        movement_lost = 0
        if combatant is not None and hasattr(combatant, "current_movement"):
            before = max(0, int(combatant.current_movement))
            combatant.current_movement = max(0, before - 2)
            movement_lost = before - combatant.current_movement
        suffix = f" You spend {movement_lost} movement hauling yourself clear." if movement_lost else ""
        await session.send(
            "\r\nThe crust takes your first step and betrays the second. One leg punches through to the thigh and the slab cracks outward around you. Nothing is injured except your dignity, but getting free costs more effort than reading the snow would have."
            + suffix
            + "\r\nNow you can see the hollow under the drift. TAKE LEE ROUTE.\r\n"
        )
        return True
    if normalized in {"take lee route", "use lee route", "follow lee route", "take long route", "go lee"}:
        if TROLL_SIGNATURE_DRIFT_READ_FLAG not in flags:
            await session.send("\r\nYou can take the longer line, but first READ DRIFT so you know why.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_SIGNATURE_COMPLETE_FLAG)
        await session.send(
            "\r\nYou work the ugly line beside the lee stones. It takes longer and never once asks whether you are strong enough to survive a collapse. By the time you rejoin the pass, the smooth drift is behind you and still looks inviting from this side.\r\n"
        )
        return True
    return False


async def _handle_undead(session, normalized: str) -> bool:
    if not _moment_ready(session, "undead"):
        return False
    flags = _flags(session)
    if normalized in {"listen bell", "listen to bell", "listen shift bell", "hear bell", "examine bell"}:
        session.database.grant_flag(session.character.id, UNDEAD_SIGNATURE_BELL_HEARD_FLAG)
        await session.send(
            "\r\nThree notes descend through the gatehouse. Your arm remembers a posture your mind does not choose. You wait for the pressure of command that once followed the cadence. Nothing comes.\r\n"
            "The reflex is yours now too. You can LOWER HAND deliberately or IGNORE BELL and let the old motion die unfinished.\r\n"
        )
        return True
    if normalized in {"lower hand", "lower my hand", "relax hand", "drop hand", "ignore bell", "ignore the bell", "do nothing"}:
        if UNDEAD_SIGNATURE_BELL_HEARD_FLAG not in flags:
            await session.send("\r\nLISTEN BELL long enough to separate the old reflex from an actual command.\r\n")
            return True
        session.database.grant_flag(session.character.id, UNDEAD_SIGNATURE_COMPLETE_FLAG)
        if normalized.startswith("ignore") or normalized == "do nothing":
            action = "You let the half-raised hand remain unfinished until gravity lowers it for you."
        else:
            action = "You lower the hand because you decided to lower it."
        await session.send(
            "\r\n" + action + " The bell rings for gate workers, not masters. Nothing in your bones argues.\r\n"
        )
        return True
    return False


async def _handle_sporekin(session, normalized: str) -> bool:
    if not _moment_ready(session, "sporekin"):
        return False
    flags = _flags(session)
    if normalized in {"listen chorus", "listen to chorus", "feel chorus", "listen fork", "examine fork", "read chorus"}:
        session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG)
        await session.send(
            "\r\nYou open your attention fully. Rainward carries wet leaves, insects, and remembered shelter. Stoneward carries warmth, visibility, and an old safe resting shelf. The Chorus contains both memories and supplies no preference between them.\r\n"
            "No consensus is coming. CHOOSE RAIN or CHOOSE STONE.\r\n"
        )
        return True
    if normalized in {"choose rain", "take rain route", "choose rainward", "go rainward"}:
        if SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG not in flags:
            await session.send("\r\nLISTEN CHORUS first. The point is to know whether the network is actually choosing for you.\r\n")
            return True
        session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_RAIN_FLAG)
        session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_COMPLETE_FLAG)
        await session.send(
            "\r\nYou choose the rainward line. The Chorus does not brighten in approval or dim in disappointment. It simply receives one new fact: you went this way.\r\n"
        )
        return True
    if normalized in {"choose stone", "take stone route", "choose stoneward", "go stoneward"}:
        if SPOREKIN_SIGNATURE_CHORUS_LISTENED_FLAG not in flags:
            await session.send("\r\nLISTEN CHORUS first. The point is to know whether the network is actually choosing for you.\r\n")
            return True
        session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_STONE_FLAG)
        session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_COMPLETE_FLAG)
        await session.send(
            "\r\nYou choose the stoneward line. The Chorus does not brighten in approval or dim in disappointment. It simply receives one new fact: you went this way.\r\n"
        )
        return True
    return False


async def _handle_signature_command(session, normalized: str) -> bool:
    if session.character is None:
        return False
    race = session.character.race
    if race == "human":
        return await _handle_human(session, normalized)
    if race == "moon_elf":
        return await _handle_moon_elf(session, normalized)
    if race == "dwarf":
        return await _handle_dwarf(session, normalized)
    if race == "goblin":
        return await _handle_goblin(session, normalized)
    if race == "troll":
        return await _handle_troll(session, normalized)
    if race == "undead":
        return await _handle_undead(session, normalized)
    if race == "sporekin":
        return await _handle_sporekin(session, normalized)
    return False


async def _echo_sporekin_choice_if_ready(session) -> bool:
    if session.character is None or session.character.race != "sporekin":
        return False
    if session.character.current_room != SPOREKIN_MEMORY_PATH_ROOM_KEY:
        return False
    flags = _flags(session)
    if SPOREKIN_SIGNATURE_COMPLETE_FLAG not in flags or SPOREKIN_SIGNATURE_ECHO_FLAG in flags:
        return False
    session.database.grant_flag(session.character.id, SPOREKIN_SIGNATURE_ECHO_FLAG)
    route = "rainward" if SPOREKIN_SIGNATURE_RAIN_FLAG in flags else "stoneward"
    await session.send(
        f"\r\nThe Memory Path brushes the Chorus more strongly here. Your earlier {route} choice returns as a shared memory now—not as an instruction, simply as something one Sporekin chose and the network remembers.\r\n"
    )
    return True


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


def install_signature_moment_runtime(player_session_class, world_service) -> None:
    install_signature_moment_content(world_service)
    if getattr(player_session_class, "_starter_signature_moments_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_move_character = player_session_class.move_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        await _announce_if_ready(self)
        await _echo_sporekin_choice_if_ready(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        after = self.character.current_room if self.character is not None else None
        if before != after:
            await _announce_if_ready(self)
            await _echo_sporekin_choice_if_ready(self)

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race == "forest_elf":
            await previous_playing_prompt(self)
            return

        await _announce_if_ready(self)
        await _echo_sporekin_choice_if_ready(self)
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if await _handle_signature_command(self, normalized):
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._starter_signature_moments_installed = True
