from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.dwarf_start import (
    DWARF_FIRST_OBLIGATION_FLAG,
    DWARF_FIRST_WORK_ORDER,
    DWARF_REGION_KEY,
    DWARF_TRADE_ARCADE_KEY,
    DWARF_WORKSHOP_TIER_KEY,
)
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


DWARF_BELLOWSWORKS_FLOOR_KEY = "dwarf_bellowsworks_shift_floor"

DWARF_FIRST_SHIFT_QUEST_KEY = "dwarf_first_shift"
DWARF_TRADE_INTEREST_QUEST_KEY = "dwarf_trade_house_interest"

DWARF_FIRST_SHIFT_STARTED_FLAG = "dwarf_first_shift_started"
DWARF_FIRST_SHIFT_MANIFOLD_CHECKED_FLAG = "dwarf_first_shift_manifold_checked"
DWARF_FIRST_SHIFT_SHUTOFF_FLAG = "dwarf_first_shift_emergency_shutoff"
DWARF_FIRST_SHIFT_COWORKER_CHECKED_FLAG = "dwarf_first_shift_coworker_checked"
DWARF_FIRST_SHIFT_FAULT_IDENTIFIED_FLAG = "dwarf_first_shift_fault_identified"
DWARF_FIRST_SHIFT_REPORTED_FLAG = "dwarf_first_shift_reported"
DWARF_FIRST_SHIFT_COMPLETE_FLAG = "dwarf_first_shift_complete"

DWARF_HEARD_DEEPFORGE_FLAG = "dwarf_heard_deepforge_house"
DWARF_HEARD_CLOCKGLASS_FLAG = "dwarf_heard_clockglass_house"
DWARF_TRADE_INTEREST_DEEPFORGE_FLAG = "dwarf_trade_interest_deepforge"
DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG = "dwarf_trade_interest_clockglass"
DWARF_TRADE_INTEREST_RECORDED_FLAG = "dwarf_trade_interest_recorded"

KETTA_RIVETBRAID_KEY = "dwarf_forewoman_ketta_rivetbraid"
BRUNI_SPARKHEEL_KEY = "dwarf_apprentice_bruni_sparkheel"
ORSA_DEEPFORGE_KEY = "dwarf_factor_orsa_deepforge"
PELLIN_CLOCKGLASS_KEY = "dwarf_factor_pellin_clockglass"


DWARF_FIRST_SHIFT = QuestDefinition(
    key=DWARF_FIRST_SHIFT_QUEST_KEY,
    name="Second Bell, First Shift",
    style="structured",
    description=(
        "Your civic clearance is finally valid, which means the practice work is over. Report for a first ordinary apprentice shift at Bellowsworks, "
        "follow the inspection list, and learn what Dwarven competence looks like when a routine machine stops behaving routinely."
    ),
    objective_steps=(
        ("report_shift", "Go south to the Public Workshop Tier, then east to Bellowsworks Shift Floor and TALK KETTA."),
        ("check_manifold", "Perform the ordinary start-of-shift check: CHECK MANIFOLD."),
        ("emergency_shutoff", "The relief linkage has failed. PULL EMERGENCY SHUTOFF."),
        ("check_coworker", "The line is isolated. CHECK BRUNI before touching the failed assembly."),
        ("identify_fault", "With everyone safe, EXAMINE SHEARED PIN to identify the failure."),
        ("report_forewoman", "TALK KETTA and give the facts in order."),
        ("file_incident", "Take the incident tag to Civic Registry Hall and TALK HELGA to file it."),
        ("complete", "Your first real shift ended with the system safer than you found it."),
    ),
)

DWARF_TRADE_INTEREST = QuestDefinition(
    key=DWARF_TRADE_INTEREST_QUEST_KEY,
    name="The Next Page",
    style="structured",
    description=(
        "Two trade houses heard how you handled the Bellowsworks failure. Hear both offers, then record which kind of work you want to see more of first. "
        "This is an apprenticeship interest, not a binding contract or permanent faction choice."
    ),
    objective_steps=(
        ("hear_houses", "Go to the Trade House Arcade. TALK ORSA and TALK PELLIN; hear both before choosing."),
        ("record_interest", "Choose a first direction: INTEREST DEEPFORGE or INTEREST CLOCKGLASS."),
        ("complete", "Your first trade-house interest is on record, without closing any other door."),
    ),
)


KETTA_RIVETBRAID = NpcDefinition(
    key=KETTA_RIVETBRAID_KEY,
    name="Forewoman Ketta Rivetbraid",
    short_description="a soot-marked shift forewoman carrying a grease pencil, a folded inspection sheet, and no visible patience for theatrical incompetence",
    room_key=DWARF_BELLOWSWORKS_FLOOR_KEY,
    role="first-shift supervisor and industrial safety mentor",
    dialogue=(
        "Ketta scans the line without looking impressed by it. 'A good shift is one where the machine does its work, the crew does theirs, and nobody has to become a story.'",
        "'Competence is not never seeing a failure. Competence is noticing it early, making the room safe, checking the people, and leaving a record the next crew can use.'",
    ),
)

BRUNI_SPARKHEEL = NpcDefinition(
    key=BRUNI_SPARKHEEL_KEY,
    name="Bruni Sparkheel",
    short_description="another newly cleared apprentice with a tool satchel too neatly organized to have survived many shifts yet",
    room_key=DWARF_BELLOWSWORKS_FLOOR_KEY,
    role="coworker and peer apprentice",
    dialogue=(
        "Bruni checks a wrench against the rack silhouette before returning it. 'First real shift. Apparently the secret is doing exactly what the checklist says until you understand why it says it.'",
        "'If I make a stupid mistake, stop me. If you make one, I will return the favor.'",
    ),
)

ORSA_DEEPFORGE = NpcDefinition(
    key=ORSA_DEEPFORGE_KEY,
    name="Factor Orsa Deepforge",
    short_description="a heavy-industry factor in a practical wool coat whose cuffs carry old foundry burns instead of decorative braid",
    room_key=DWARF_TRADE_ARCADE_KEY,
    role="Deepforge Industrial House apprenticeship contact",
    dialogue=(
        "Orsa taps a contract folio stamped with rail, furnace, and pressure-main seals. 'Deepforge handles the work nobody notices until it stops: municipal steam, structural iron, freight rail, pumps, furnaces.'",
        "'We heard you shut a line down before trying to look clever. That is a useful instinct in heavy work.'",
    ),
)

PELLIN_CLOCKGLASS = NpcDefinition(
    key=PELLIN_CLOCKGLASS_KEY,
    name="Factor Pellin Clockglass",
    short_description="a precision-house factor wearing a loupe on a neck chain and carrying three pocket watches that disagree by less than a second",
    room_key=DWARF_TRADE_ARCADE_KEY,
    role="Clockglass Instrument House apprenticeship contact",
    dialogue=(
        "Pellin turns a tiny lift governor between two fingers. 'Clockglass builds the parts that tell larger machines when they are lying: gauges, governors, clocks, measuring heads, signal mechanisms.'",
        "'You bothered to identify the failed pin after the danger was over. That is the part of the story I care about.'",
    ),
)

DWARF_FIRST_SHIFT_NPCS = (
    KETTA_RIVETBRAID,
    BRUNI_SPARKHEEL,
    ORSA_DEEPFORGE,
    PELLIN_CLOCKGLASS,
)


BELLOWSWORKS_SHIFT_FLOOR = RoomDefinition(
    key=DWARF_BELLOWSWORKS_FLOOR_KEY,
    name="Bellowsworks Shift Floor",
    region_key=DWARF_REGION_KEY,
    description=(
        "A long production bay runs beside a waist-high steam manifold feeding public forges, rivet heaters, and two belt-driven presses. Nothing here is ceremonial. "
        "Chalk marks identify today's work, tool shadows show where every wrench belongs, and a shift bell hangs beside the time clock. A broad red emergency cut bar spans the manifold walkway where any worker can reach it. "
        "This is the sort of place that keeps the mountain city functioning on an ordinary day."
    ),
    exits={"west": DWARF_WORKSHOP_TIER_KEY},
    npc_keys=(KETTA_RIVETBRAID_KEY, BRUNI_SPARKHEEL_KEY),
    tags=("dwarf_start", "industry", "apprenticeship", "shift_floor", "steam", "safe_until_incident"),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = (), *, listen: str = "", touch: str = "") -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        listen_text=listen,
        touch_text=touch,
    )


def _layer(key: str, text: str, *, flags: tuple[str, ...] = (), priority: int = 50) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=priority, condition=ViewCondition(required_flags=flags))


def dwarf_first_shift_augmentations() -> dict[str, RoomAugmentation]:
    return {
        DWARF_BELLOWSWORKS_FLOOR_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="west",
                    destination_key=DWARF_WORKSHOP_TIER_KEY,
                    name="Public Workshop Tier",
                    travel_text="You step out of Bellowsworks into the wider public workshop terraces.",
                ),
            ),
            features=(
                _feature(
                    "bellowsworks_manifold",
                    "Shift Manifold",
                    "the labeled steam manifold that feeds the work bays",
                    "Each branch has a gauge, isolation cock, relief linkage, service date, and a place for a yellow incident tag. The start-of-shift sheet requires the apprentice to verify gauge motion, relief linkage, and visible leaks before the presses are brought fully online.",
                    ("manifold", "steam manifold", "line", "steam line"),
                    listen="Under normal load the manifold has a steady layered hiss. A changing pitch would be reason to stop and look.",
                    touch="The insulated casing is warm. The exposed controls are deliberately spaced so gloved hands can reach them without crossing another valve.",
                ),
                _feature(
                    "emergency_cut_bar",
                    "Emergency Cut Bar",
                    "a broad red mechanical bar connected to the local isolation valves",
                    "The bar is intentionally crude, mechanical, and reachable from either side of the walkway. The engraved instruction is only four words: PULL. CLEAR. COUNT. CHECK PEOPLE.",
                    ("cut bar", "emergency bar", "shutoff", "emergency shutoff", "red bar"),
                ),
                _feature(
                    "relief_linkage",
                    "Relief Linkage",
                    "a spring-and-pin linkage on the second manifold branch",
                    "The linkage is a replaceable mechanical safety component. Its retaining pin is small, cheap, and exactly the kind of part that can stop an expensive system when fatigue finally wins.",
                    ("linkage", "relief", "pin", "retaining pin", "sheared pin"),
                ),
            ),
            description_layers=(
                _layer(
                    "bellowsworks_after_incident",
                    "A yellow incident tag now hangs from the second branch. The failed retaining pin has been bagged for inspection, and the isolated line waits for a replacement rather than being quietly put back into service.",
                    flags=(DWARF_FIRST_SHIFT_REPORTED_FLAG,),
                    priority=90,
                ),
            ),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _patch_workshop_room() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[DWARF_WORKSHOP_TIER_KEY]
    exits = dict(original.exits)
    exits["east"] = DWARF_BELLOWSWORKS_FLOOR_KEY
    description = original.description
    if "Bellowsworks" not in description:
        description += " An east passage marked BELLOWSWORKS - ACTIVE SHIFT FLOOR leads into one of the tier's ordinary production bays."
    return replace(original, description=description, exits=exits)


def _patch_trade_arcade_npcs() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[DWARF_TRADE_ARCADE_KEY]
    extras = (ORSA_DEEPFORGE_KEY, PELLIN_CLOCKGLASS_KEY)
    npc_keys = tuple(dict.fromkeys(original.npc_keys + extras))
    return replace(original, npc_keys=npc_keys)


def _patch_world_augmentation(world_service, room_key: str, *, exits: tuple[ExitDefinition, ...] = (), layers: tuple[DescriptionLayer, ...] = ()) -> None:
    base = world_service.augmentations.get(room_key, RoomAugmentation())
    new_exits = list(base.exit_overrides)
    for exit_def in exits:
        new_exits = [old for old in new_exits if old.direction != exit_def.direction]
        new_exits.append(exit_def)
    new_layers = list(base.description_layers)
    for layer in layers:
        if not any(old.key == layer.key for old in new_layers):
            new_layers.append(layer)
    world_service.augmentations[room_key] = replace(
        base,
        exit_overrides=tuple(new_exits),
        description_layers=tuple(new_layers),
    )
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(room_key, None)


def install_dwarf_first_shift_content(world_service=None) -> None:
    """Extend the established Dwarf certification sequence into a first real shift."""
    for quest in (DWARF_FIRST_SHIFT, DWARF_TRADE_INTEREST):
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for npc in DWARF_FIRST_SHIFT_NPCS:
        _replace_npc(npc)

    _replace_room(BELLOWSWORKS_SHIFT_FLOOR)
    workshop = _patch_workshop_room()
    trade_arcade = _patch_trade_arcade_npcs()
    _replace_room(workshop)
    _replace_room(trade_arcade)

    if world_service is None:
        return

    world_service.legacy_rooms[BELLOWSWORKS_SHIFT_FLOOR_KEY] = BELLOWSWORKS_SHIFT_FLOOR
    world_service.legacy_rooms[DWARF_WORKSHOP_TIER_KEY] = workshop
    world_service.legacy_rooms[DWARF_TRADE_ARCADE_KEY] = trade_arcade
    world_service.augmentations.update(dwarf_first_shift_augmentations())
    _patch_world_augmentation(
        world_service,
        DWARF_WORKSHOP_TIER_KEY,
        exits=(
            ExitDefinition(
                direction="east",
                destination_key=DWARF_BELLOWSWORKS_FLOOR_KEY,
                name="Bellowsworks Shift Floor",
                travel_text="You follow the marked east passage onto the active Bellowsworks shift floor.",
            ),
        ),
    )
    _patch_world_augmentation(
        world_service,
        DWARF_TRADE_ARCADE_KEY,
        layers=(
            _layer(
                "deepforge_interest_echo",
                "A Deepforge runner has left a heavy-work contract digest at the public desk with your name written on the corner. It is an invitation to look, not an obligation to sign.",
                flags=(DWARF_TRADE_INTEREST_DEEPFORGE_FLAG,),
                priority=80,
            ),
            _layer(
                "clockglass_interest_echo",
                "A Clockglass clerk has left a slim packet of instrument-shop observation hours at the public desk with your name on it. Nothing in the packet calls itself exclusive.",
                flags=(DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG,),
                priority=80,
            ),
        ),
    )
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (DWARF_BELLOWSWORKS_FLOOR_KEY, DWARF_WORKSHOP_TIER_KEY, DWARF_TRADE_ARCADE_KEY):
            cache.pop(room_key, None)


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _start_first_shift_if_ready(session, *, announce: bool = False):
    if session.character is None or session.character.race != "dwarf":
        return False
    first_order = _quest(session, DWARF_FIRST_WORK_ORDER.key)
    first_shift = _quest(session, DWARF_FIRST_SHIFT.key)
    if not first_order or first_order.get("status") != "completed" or first_shift is not None:
        return False
    session.database.start_quest(session.character.id, DWARF_FIRST_SHIFT.key, "report_shift")
    session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_STARTED_FLAG)
    return True


def _start_trade_interest_if_ready(session) -> bool:
    if session.character is None or session.character.race != "dwarf":
        return False
    first_shift = _quest(session, DWARF_FIRST_SHIFT.key)
    interest = _quest(session, DWARF_TRADE_INTEREST.key)
    if not first_shift or first_shift.get("status") != "completed" or interest is not None:
        return False
    session.database.start_quest(session.character.id, DWARF_TRADE_INTEREST.key, "hear_houses")
    return True


def reconcile_dwarf_first_shift(session) -> tuple[bool, bool]:
    """Catch old cleared Dwarves up without changing their prior work-order history."""
    started_shift = _start_first_shift_if_ready(session)
    started_interest = _start_trade_interest_if_ready(session)
    return started_shift, started_interest


async def _announce_new_shift(session) -> None:
    await session.send(
        "\r\nYour civic clearance is no longer theoretical. A first paid apprentice shift has been posted to your record.\r\n"
        "Bellowsworks, second bell. Ordinary production work. Report to Forewoman Ketta Rivetbraid on the active shift floor east of the Public Workshop Tier.\r\n"
        "\r\nNew quest: Second Bell, First Shift.\r\n"
        "This is the first job where the machinery is not pretending to be safe for your education.\r\n"
    )


async def _announce_trade_interest(session) -> None:
    await session.send(
        "\r\nThe Bellowsworks incident report travels faster than gossip because it has a serial number. Two trade houses have asked to speak with you.\r\n"
        "Go to the Trade House Arcade and hear both before deciding which kind of work you want to observe first.\r\n"
        "\r\nNew quest: The Next Page.\r\n"
        "This is not a faction lock, employment contract, or permanent profession choice.\r\n"
    )


def _active_step(session, key: str) -> str | None:
    row = _quest(session, key)
    if row and row.get("status") == "active":
        return str(row.get("current_step"))
    return None


async def _talk_ketta(session) -> bool:
    if session.character is None or session.character.current_room != DWARF_BELLOWSWORKS_FLOOR_KEY:
        return False
    step = _active_step(session, DWARF_FIRST_SHIFT.key)
    if step == "report_shift":
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "check_manifold")
        await session.send(
            "\r\nKetta checks your new clearance number, circles a line on the shift sheet, and hands it back.\r\n"
            "'Congratulations. You are now qualified enough to be responsible for ordinary things.'\r\n"
            "She points at the steam manifold. 'Start-of-shift check. Gauge movement, relief linkage, visible leaks. CHECK MANIFOLD. If it is boring, you did not waste the morning.'\r\n"
        )
        return True
    if step == "report_forewoman":
        flags = _flags(session)
        required = {
            DWARF_FIRST_SHIFT_SHUTOFF_FLAG,
            DWARF_FIRST_SHIFT_COWORKER_CHECKED_FLAG,
            DWARF_FIRST_SHIFT_FAULT_IDENTIFIED_FLAG,
        }
        if not required.issubset(flags):
            await session.send("\r\nKetta cuts you off. 'Do not give me a story before you have checked the worker and identified the failed part.'\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_REPORTED_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "file_incident")
        await session.send(
            "\r\nYou give Ketta the sequence without decoration: rising pressure, failed relief linkage, local isolation, Bruni checked, retaining pin sheared.\r\n"
            "Ketta writes each point onto a yellow incident tag. 'Good. No heroics. The machine failed, you made the room safe, and now the next crew gets facts instead of folklore.'\r\n"
            "She tears off the registry copy. 'File this with Helga. We do not quietly replace the pin and pretend it never happened.'\r\n"
            "Quest updated: take the incident tag to Civic Registry Hall and TALK HELGA.\r\n"
        )
        return True
    if _quest(session, DWARF_FIRST_SHIFT.key) and _quest(session, DWARF_FIRST_SHIFT.key).get("status") == "completed":
        await session.send("\r\nKetta nods toward the repaired branch. 'Your first shift already gave you a better lesson than a week of staged failures.'\r\n")
        return True
    if step:
        objective = DWARF_FIRST_SHIFT.objective_for_step(step)
        await session.send("\r\nKetta taps the shift sheet. 'Finish the thing in front of you before asking for the next thing.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True
    return False


async def _talk_bruni(session) -> bool:
    if session.character is None or session.character.current_room != DWARF_BELLOWSWORKS_FLOOR_KEY:
        return False
    step = _active_step(session, DWARF_FIRST_SHIFT.key)
    if step == "check_coworker":
        session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_COWORKER_CHECKED_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "identify_fault")
        await session.send(
            "\r\nYou check Bruni before reaching for the failed hardware. A splash of hot condensate has reddened one glove and the back of one wrist, but the skin beneath is intact and Bruni can move every finger.\r\n"
            "Bruni flexes the hand, annoyed more than hurt. 'Fine. Embarrassed. Fine.' Then points at the dead branch. 'Now find out what tried to make us interesting.'\r\n"
            "EXAMINE SHEARED PIN.\r\n"
        )
        return True
    await session.send("\r\nBruni says, 'If you are asking whether I am all right, use CHECK BRUNI. If you are making conversation, I remain tragically assigned to this shift.'\r\n")
    return True


async def _talk_orsa(session) -> bool:
    if session.character is None or session.character.current_room != DWARF_TRADE_ARCADE_KEY:
        return False
    interest = _quest(session, DWARF_TRADE_INTEREST.key)
    if not interest:
        await session.send("\r\nOrsa is willing to discuss Deepforge work, but no apprenticeship introduction is currently attached to your record.\r\n")
        return True
    flags = _flags(session)
    session.database.grant_flag(session.character.id, DWARF_HEARD_DEEPFORGE_FLAG)
    await session.send(
        "\r\nOrsa opens a folio of furnace, rail, pump, and municipal pressure contracts.\r\n"
        "'Deepforge is heavy work. Big tolerances do not mean sloppy tolerances. When a main ruptures, a district notices.'\r\n"
        "She closes the folio. 'You can observe a crew before you ever sign with us. I prefer apprentices who know what the work feels like before they call it a calling.'\r\n"
    )
    if DWARF_HEARD_CLOCKGLASS_FLAG in flags and interest.get("status") == "active" and interest.get("current_step") == "hear_houses":
        session.database.advance_quest(session.character.id, DWARF_TRADE_INTEREST.key, "record_interest")
        await session.send("You have now heard both houses. Choose INTEREST DEEPFORGE or INTEREST CLOCKGLASS.\r\n")
    else:
        await session.send("Hear Pellin Clockglass as well before choosing.\r\n")
    return True


async def _talk_pellin(session) -> bool:
    if session.character is None or session.character.current_room != DWARF_TRADE_ARCADE_KEY:
        return False
    interest = _quest(session, DWARF_TRADE_INTEREST.key)
    if not interest:
        await session.send("\r\nPellin can explain Clockglass work, but no apprenticeship introduction is currently attached to your record.\r\n")
        return True
    flags = _flags(session)
    session.database.grant_flag(session.character.id, DWARF_HEARD_CLOCKGLASS_FLAG)
    await session.send(
        "\r\nPellin lays out three objects: a pressure gauge movement, a lift governor escapement, and a clockwork signal relay.\r\n"
        "'Precision work is mostly discovering how a large system can be wrong by a very small amount.'\r\n"
        "He returns the parts to their cases. 'Observe first. Choose later. A house that needs your ignorance to keep you loyal is a poor house.'\r\n"
    )
    if DWARF_HEARD_DEEPFORGE_FLAG in flags and interest.get("status") == "active" and interest.get("current_step") == "hear_houses":
        session.database.advance_quest(session.character.id, DWARF_TRADE_INTEREST.key, "record_interest")
        await session.send("You have now heard both houses. Choose INTEREST DEEPFORGE or INTEREST CLOCKGLASS.\r\n")
    else:
        await session.send("Hear Orsa Deepforge as well before choosing.\r\n")
    return True


async def _file_incident_with_helga(session) -> bool:
    if session.character is None or session.character.current_room != "dwarf_civic_registry":
        return False
    if _active_step(session, DWARF_FIRST_SHIFT.key) != "file_incident":
        return False
    session.database.complete_quest(session.character.id, DWARF_FIRST_SHIFT.key)
    session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_COMPLETE_FLAG)
    await session.send(
        "\r\nHelga reads the incident tag twice, stamps the registry copy, and routes duplicates to Bellowsworks maintenance, the union safety desk, and the component-inspection office.\r\n"
        "'A failed pin is cheap. An undocumented failed pin is expensive.' She slides your copy back. 'First real shift complete. Nobody dead, nobody blamed for metal fatigue, and the next crew knows what changed.'\r\n"
        "\r\nQuest complete: Second Bell, First Shift.\r\n"
    )
    if _start_trade_interest_if_ready(session):
        await _announce_trade_interest(session)
    return True


async def _handle_shift_actions(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "dwarf":
        return False
    room = session.character.current_room
    step = _active_step(session, DWARF_FIRST_SHIFT.key)

    if room == DWARF_BELLOWSWORKS_FLOOR_KEY and normalized in {"check manifold", "inspect manifold", "check steam manifold", "perform manifold check"}:
        if step != "check_manifold":
            await session.send("\r\nYou check the manifold. Nothing in your current work step requires a formal start-of-shift inspection.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_MANIFOLD_CHECKED_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "emergency_shutoff")
        await session.send(
            "\r\nYou work down the checklist. First gauge moves. Second gauge moves. No visible leak. You put two fingers against the relief linkage to check free travel.\r\n"
            "The retaining pin gives a tiny metallic SNAP. The relief arm jumps out of alignment and the gauge needle starts climbing. A hose bucks hard enough to knock Bruni sideways into the rail.\r\n"
            "Ketta does not shout instructions. The emergency procedure is already painted in red at eye level.\r\n"
            "PULL EMERGENCY SHUTOFF.\r\n"
        )
        return True

    if room == DWARF_BELLOWSWORKS_FLOOR_KEY and normalized in {"pull emergency shutoff", "pull shutoff", "pull cut bar", "pull emergency bar", "pull red bar", "shut down line", "isolate line"}:
        if step != "emergency_shutoff":
            await session.send("\r\nThe cut bar is for an active local emergency. The line is not presently in that state.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_SHUTOFF_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "check_coworker")
        await session.send(
            "\r\nYou pull the red cut bar through its full travel. Mechanical dogs slam shut on both sides of the branch. The press winds down. Steam collapses into the condenser with a violent hiss, then silence.\r\n"
            "You count the indicator lamps until both isolation flags turn black. The room is safe enough to think again.\r\n"
            "Bruni is sitting against the rail, staring at one reddened glove. CHECK BRUNI.\r\n"
        )
        return True

    if room == DWARF_BELLOWSWORKS_FLOOR_KEY and normalized in {"check bruni", "check coworker", "check apprentice", "check on bruni", "help bruni"}:
        return await _talk_bruni(session)

    if room == DWARF_BELLOWSWORKS_FLOOR_KEY and normalized in {"examine sheared pin", "examine pin", "inspect pin", "examine retaining pin", "inspect retaining pin", "examine linkage", "inspect linkage"}:
        if step != "identify_fault":
            await session.send("\r\nThe relief linkage is visible, but you do not yet have a safe reason to put your attention there. Follow the emergency sequence first.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_FIRST_SHIFT_FAULT_IDENTIFIED_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_SHIFT.key, "report_forewoman")
        await session.send(
            "\r\nThe retaining pin has sheared cleanly at an old fatigue line. No sabotage, no dramatic defect, no missing inspection stamp. The part was within its service interval and failed early.\r\n"
            "That makes the incident less exciting and more important: if one batch aged badly, maintenance needs the serial number before another branch discovers it under pressure.\r\n"
            "TALK KETTA and report what happened.\r\n"
        )
        return True

    if room == DWARF_BELLOWSWORKS_FLOOR_KEY and normalized in {"turn intake valve", "open intake", "increase pressure", "restart line", "start press"} and step == "emergency_shutoff":
        await session.send(
            "\r\nA red mechanical interlock blocks the control. More importantly, the emergency diagram gives you no reason to add pressure to a line whose relief linkage just failed. The cut bar is within reach.\r\n"
        )
        return True

    if normalized in {"interest deepforge", "choose deepforge", "deepforge interest"}:
        interest = _quest(session, DWARF_TRADE_INTEREST.key)
        if not interest or interest.get("status") != "active" or interest.get("current_step") != "record_interest":
            await session.send("\r\nYou need to hear both apprenticeship introductions before recording a trade-house interest.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_TRADE_INTEREST_DEEPFORGE_FLAG)
        session.database.grant_flag(session.character.id, DWARF_TRADE_INTEREST_RECORDED_FLAG)
        session.database.complete_quest(session.character.id, DWARF_TRADE_INTEREST.key)
        await session.send(
            "\r\nYou mark DEEPFORGE as the kind of work you want to observe first: furnaces, rails, pumps, structural iron, and municipal pressure systems.\r\n"
            "The clerk writes INTEREST, not CONTRACT. You have not joined Deepforge, left the union, chosen a permanent profession, or closed Clockglass work to yourself.\r\n"
            "Quest complete: The Next Page.\r\n"
        )
        return True

    if normalized in {"interest clockglass", "choose clockglass", "clockglass interest"}:
        interest = _quest(session, DWARF_TRADE_INTEREST.key)
        if not interest or interest.get("status") != "active" or interest.get("current_step") != "record_interest":
            await session.send("\r\nYou need to hear both apprenticeship introductions before recording a trade-house interest.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG)
        session.database.grant_flag(session.character.id, DWARF_TRADE_INTEREST_RECORDED_FLAG)
        session.database.complete_quest(session.character.id, DWARF_TRADE_INTEREST.key)
        await session.send(
            "\r\nYou mark CLOCKGLASS as the kind of work you want to observe first: gauges, governors, clocks, relays, and the small mechanisms that keep large machines honest.\r\n"
            "The clerk writes INTEREST, not CONTRACT. You have not joined Clockglass, left the union, chosen a permanent profession, or closed Deepforge work to yourself.\r\n"
            "Quest complete: The Next Page.\r\n"
        )
        return True

    return False


async def _show_shift_record(session) -> None:
    if session.character is None:
        return
    await session.send("\r\n--- Apprenticeship Record ---\r\n")
    first_order = _quest(session, DWARF_FIRST_WORK_ORDER.key)
    first_shift = _quest(session, DWARF_FIRST_SHIFT.key)
    interest = _quest(session, DWARF_TRADE_INTEREST.key)
    await session.send(f"Civic qualification: {'CLEARED' if first_order and first_order.get('status') == 'completed' else 'in progress'}.\r\n")
    if first_shift:
        await session.send(f"First real shift: {str(first_shift.get('status')).upper()}.\r\n")
        if first_shift.get("status") == "active":
            objective = DWARF_FIRST_SHIFT.objective_for_step(first_shift.get("current_step"))
            if objective:
                await session.send(f"  {objective}\r\n")
    if interest:
        await session.send(f"Trade-house introduction: {str(interest.get('status')).upper()}.\r\n")
        if interest.get("status") == "active":
            objective = DWARF_TRADE_INTEREST.objective_for_step(interest.get("current_step"))
            if objective:
                await session.send(f"  {objective}\r\n")
    flags = _flags(session)
    if DWARF_TRADE_INTEREST_DEEPFORGE_FLAG in flags:
        await session.send("Current first-look interest: Deepforge Industrial House (non-binding).\r\n")
    elif DWARF_TRADE_INTEREST_CLOCKGLASS_FLAG in flags:
        await session.send("Current first-look interest: Clockglass Instrument House (non-binding).\r\n")
    else:
        await session.send("Current first-look interest: none recorded.\r\n")


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


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def install_dwarf_first_shift_runtime(player_session_class, world_service) -> None:
    install_dwarf_first_shift_content(world_service)
    if getattr(player_session_class, "_dwarf_first_shift_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "dwarf":
            return
        started_shift, started_interest = reconcile_dwarf_first_shift(self)
        if started_shift:
            await _announce_new_shift(self)
        elif started_interest:
            await _announce_trade_interest(self)
        first_shift = _quest(self, DWARF_FIRST_SHIFT.key)
        if first_shift and first_shift.get("status") == "active":
            objective = DWARF_FIRST_SHIFT.objective_for_step(first_shift.get("current_step"))
            await self.send("\r\nApprenticeship duty: Second Bell, First Shift.\r\n")
            if objective:
                await self.send(f"Current objective: {objective}\r\n")
        interest = _quest(self, DWARF_TRADE_INTEREST.key)
        if interest and interest.get("status") == "active":
            objective = DWARF_TRADE_INTEREST.objective_for_step(interest.get("current_step"))
            await self.send("\r\nApprenticeship introduction: The Next Page.\r\n")
            if objective:
                await self.send(f"Current objective: {objective}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "dwarf":
            await previous_playing_prompt(self)
            return

        started_shift, started_interest = reconcile_dwarf_first_shift(self)
        if started_shift:
            await _announce_new_shift(self)
        elif started_interest:
            await _announce_trade_interest(self)

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"shift", "shift record", "apprenticeship", "apprentice", "first shift", "trade interest"}:
            await _show_shift_record(self)
            return

        if await _handle_shift_actions(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == DWARF_BELLOWSWORKS_FLOOR_KEY:
                if target in {"ketta", "forewoman", "forewoman ketta", "ketta rivetbraid"} and await _talk_ketta(self):
                    return
                if target in {"bruni", "apprentice", "apprentice bruni", "bruni sparkheel", "coworker"} and await _talk_bruni(self):
                    return
            if self.character.current_room == DWARF_TRADE_ARCADE_KEY:
                if target in {"orsa", "deepforge", "factor orsa", "orsa deepforge"} and await _talk_orsa(self):
                    return
                if target in {"pellin", "clockglass", "factor pellin", "pellin clockglass"} and await _talk_pellin(self):
                    return
            if target in {"helga", "registrar", "registrar helga", "helga brassmeasure", "clerk"} and await _file_incident_with_helga(self):
                return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if self.character is None or self.character.race != "dwarf":
            return
        started_shift, started_interest = reconcile_dwarf_first_shift(self)
        if started_shift:
            await _announce_new_shift(self)
        elif started_interest:
            await _announce_trade_interest(self)

        if normalized in {"help", "?"}:
            await self.send(
                "Dwarf first shift: use SHIFT or APPRENTICESHIP to review the current duty. Bellowsworks uses TALK KETTA, CHECK MANIFOLD, PULL EMERGENCY SHUTOFF, CHECK BRUNI, EXAMINE SHEARED PIN, TALK KETTA, then TALK HELGA. Trade-house introductions use TALK ORSA, TALK PELLIN, then INTEREST DEEPFORGE or INTEREST CLOCKGLASS; the interest is explicitly non-binding.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._dwarf_first_shift_runtime_installed = True
