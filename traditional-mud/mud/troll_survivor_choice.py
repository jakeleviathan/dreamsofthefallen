from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.quests as quests
import mud.troll_raid_opening as troll_raid
import mud.troll_start as troll_start
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.quests import QuestDefinition
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import RoomDefinition


TROLL_FIRST_DUTY_QUEST_KEY = "troll_first_duty_after_raid"
TROLL_FIRST_DUTY_COMPLETE_FLAG = "troll_first_duty_complete"
TROLL_FIRST_DUTY_SEEN_FLAG = "troll_first_duty_choice_seen"
TROLL_FIRST_DUTY_GRANDFATHERED_FLAG = "troll_first_duty_grandfathered"

TROLL_TRACK_CHOICE_FLAG = "troll_first_duty_track_raiders"
TROLL_CAMP_CHOICE_FLAG = "troll_first_duty_secure_camp"
TROLL_RETREAT_TRACKS_READ_FLAG = "troll_retreat_tracks_read"
TROLL_RETREAT_FOLLOWED_FLAG = "troll_retreat_trail_followed"
TROLL_REARGUARD_DEFEATED_FLAG = "troll_rearguard_defeated"
TROLL_RAIDER_CLUE_FLAG = "troll_raider_clue_recovered"
TROLL_TRACK_ROUTE_COMPLETE_FLAG = "troll_first_duty_track_complete"
TROLL_SHELTERS_CHECKED_FLAG = "troll_raid_shelters_checked"
TROLL_FOOD_SAVED_FLAG = "troll_raid_food_saved"
TROLL_SHELTER_PATCHED_FLAG = "troll_raid_shelter_patched"
TROLL_EMBERS_BANKED_FLAG = "troll_raid_embers_banked"
TROLL_CAMP_ROUTE_COMPLETE_FLAG = "troll_first_duty_camp_complete"

TROLL_BREACH_YARD_KEY = "troll_south_breach_yard"
TROLL_SMOLDERING_TRAIL_KEY = "troll_smoldering_retreat_trail"
TROLL_CHURNED_GULLY_KEY = "troll_churned_retreat_gully"
TROLL_ASHEN_SHELTER_ROW_KEY = "troll_ashen_shelter_row"
TROLL_REARGUARD_ENEMY_KEY = "troll_masked_rearguard"

TROLL_FIRST_DUTY_ROOM_KEYS = (
    TROLL_BREACH_YARD_KEY,
    TROLL_SMOLDERING_TRAIL_KEY,
    TROLL_CHURNED_GULLY_KEY,
    TROLL_ASHEN_SHELTER_ROW_KEY,
)


TROLL_FIRST_DUTY_QUEST = QuestDefinition(
    key=TROLL_FIRST_DUTY_QUEST_KEY,
    name="What Still Needs Doing",
    style="structured",
    description=(
        "The immediate attack on Frostroot is over, but the stronghold is still in danger. "
        "Raska gives the new Troll a real choice between two urgent needs: follow the raiders' "
        "retreat before weather erases it, or stay behind to keep damaged shelter and food "
        "stores from becoming the next disaster. Both choices teach that survival is useful "
        "work, not performance."
    ),
    objective_steps=(
        (
            "choose_duty",
            "Choose the next urgent job: TRACK RAIDERS or SECURE CAMP.",
        ),
        (
            "track_read",
            "Go SOUTH through the breach yard, then SOUTH to the Smoldering Trail and READ TRACKS.",
        ),
        (
            "track_follow",
            "FOLLOW RAIDERS only after reading which retreat trail is actually fresh.",
        ),
        (
            "track_fight",
            "Go SOUTH into Churned Gully and ATTACK REARGUARD.",
        ),
        (
            "track_search",
            "SEARCH REARGUARD after the fight and learn what the retreat tells you.",
        ),
        (
            "camp_check",
            "Go SOUTH to the breach yard, WEST to Ashen Shelter Row, and CHECK SHELTERS.",
        ),
        (
            "camp_salvage",
            "SALVAGE FOOD before meltwater and smoke ruin what the camp can still eat.",
        ),
        (
            "camp_patch",
            "PATCH SHELTER so the wounded have a dry place before the next weather comes through.",
        ),
        (
            "camp_embers",
            "BANK EMBERS so the repaired shelter has dependable heat without wasting fuel.",
        ),
        (
            "return_raska",
            "Return to Frostroot Camp and TALK RASKA.",
        ),
        (
            "complete",
            "Your first choice after the raid became part of Frostroot's recovery.",
        ),
    ),
)


MASKED_REARGUARD = EnemyDefinition(
    key=TROLL_REARGUARD_ENEMY_KEY,
    name="Masked Raid Rearguard",
    aliases=(
        "rearguard",
        "raider",
        "masked raider",
        "raid rearguard",
        "masked rearguard",
    ),
    description=(
        "a wounded, hide-masked raider left behind on the retreat trail, one sleeve dark with "
        "blood and every obvious badge or clan mark cut away"
    ),
    max_hp=18,
    armor_class=1,
    auto_attack_damage=1,
    auto_attack_interval=2.8,
    xp_reward=20,
    retaliates=True,
    tutorial=False,
)


FIRST_DUTY_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=TROLL_BREACH_YARD_KEY,
        name="South Breach Yard",
        region_key=troll_start.TROLL_REGION_KEY,
        description=(
            "The ground immediately inside Frostroot's broken southern wall has become a work "
            "yard without anyone deciding to call it one. Snapped palisade stakes lie in piles, "
            "blood-dark snow has been shoveled away from the walking path, and every usable "
            "piece of rope, hide, timber, and food container has been separated from what must "
            "be burned. South, retreat tracks disappear between the spruce. West, a line of "
            "damaged shelters sags under wet hide roofs."
        ),
        exits={
            "north": troll_start.TROLL_START_ROOM_KEY,
            "south": TROLL_SMOLDERING_TRAIL_KEY,
            "west": TROLL_ASHEN_SHELTER_ROW_KEY,
        },
        tags=("troll_start", "raid_aftermath", "choice_hub", "survival_crisis"),
    ),
    RoomDefinition(
        key=TROLL_SMOLDERING_TRAIL_KEY,
        name="Smoldering Trail",
        region_key=troll_start.TROLL_REGION_KEY,
        description=(
            "A narrow game trail leaves the broken wall and threads between black spruce. Wet "
            "ash from a burned brush pile smears across the snow, making every fresh print "
            "obvious for a few dozen paces. Several sets of boots fled this way in poor order, "
            "but the trail is not simple: old hunter sign, wolf tracks, and retreat prints cross "
            "one another where the ground rises."
        ),
        exits={"north": TROLL_BREACH_YARD_KEY, "south": TROLL_CHURNED_GULLY_KEY},
        tags=("troll_start", "tracking", "raid_aftermath", "dangerous_route"),
    ),
    RoomDefinition(
        key=TROLL_CHURNED_GULLY_KEY,
        name="Churned Gully",
        region_key=troll_start.TROLL_REGION_KEY,
        description=(
            "The retreat trail drops into a shallow gully where thaw-soft earth has been kicked "
            "through the snow. One side offers cover behind a fallen spruce; the other climbs "
            "toward exposed stone. Whoever passed through here expected pursuit. A boot has "
            "scraped a deliberate false track uphill while the heavier traffic stayed low."
        ),
        exits={"north": TROLL_SMOLDERING_TRAIL_KEY},
        tags=("troll_start", "combat_route", "raid_aftermath", "tracking"),
    ),
    RoomDefinition(
        key=TROLL_ASHEN_SHELTER_ROW_KEY,
        name="Ashen Shelter Row",
        region_key=troll_start.TROLL_REGION_KEY,
        description=(
            "A row of low family shelters hugs the inner palisade west of the breach. One hide "
            "roof has split along a support seam, and sleet is dripping onto bedding meant for "
            "the wounded. An overturned ration sledge has dumped sealed and unsealed food sacks "
            "into smoky meltwater. Nearby, a hearth still holds useful coals beneath too much "
            "open flame. None of these problems look dramatic. By morning, any one of them "
            "could become worse than the fight that caused it."
        ),
        exits={"east": TROLL_BREACH_YARD_KEY},
        tags=("troll_start", "survival_route", "raid_aftermath", "shelter", "supplies"),
    ),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    condition: ViewCondition | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        condition=condition or ViewCondition(),
    )


def first_duty_room_augmentations() -> dict[str, RoomAugmentation]:
    track_choice = ViewCondition(required_flags=(TROLL_TRACK_CHOICE_FLAG,))
    camp_choice = ViewCondition(required_flags=(TROLL_CAMP_CHOICE_FLAG,))
    trail_followed = ViewCondition(required_flags=(TROLL_RETREAT_FOLLOWED_FLAG,))
    return {
        TROLL_BREACH_YARD_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    troll_start.TROLL_START_ROOM_KEY,
                    name="Frostroot Camp",
                    travel_text="You step back north through the broken palisade into Frostroot.",
                ),
                ExitDefinition(
                    "south",
                    TROLL_SMOLDERING_TRAIL_KEY,
                    name="Smoldering Trail",
                    travel_text="You leave the work yard and follow the retreat sign south between the spruce.",
                    failure_text="You chose to secure the camp. The retreat trail can wait until Frostroot's immediate shelter problem is handled.",
                    condition=track_choice,
                    hidden_when_unavailable=False,
                ),
                ExitDefinition(
                    "west",
                    TROLL_ASHEN_SHELTER_ROW_KEY,
                    name="Ashen Shelter Row",
                    travel_text="You turn west along the inner palisade toward the damaged shelters.",
                    failure_text="You chose to track the retreat. The shelter crews have their own hands; Raska needs your eyes on the trail.",
                    condition=camp_choice,
                    hidden_when_unavailable=False,
                ),
            ),
            features=(
                _feature(
                    "breach_sorting_piles",
                    "Sorting Piles",
                    "salvaged rope, timber, hide, and containers separated from burned waste",
                    "Frostroot wastes nothing useful after the raid. Straight stakes become splints or roof braces, unburned lashings are coiled, and sealed containers are moved away from ash before anyone worries about making the yard look orderly.",
                    aliases=("piles", "salvage", "supplies"),
                ),
                _feature(
                    "breach_retreat_sign",
                    "Retreat Sign",
                    "fresh boot marks leaving Frostroot between the spruce",
                    "The obvious prints are only the beginning. Some are deep with fatigue, some stagger, and some were placed carefully enough to make a pursuer wonder which direction matters.",
                    aliases=("tracks", "prints", "trail", "raid tracks"),
                ),
            ),
        ),
        TROLL_SMOLDERING_TRAIL_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    TROLL_BREACH_YARD_KEY,
                    name="South Breach Yard",
                    travel_text="You retrace the ash-marked path north toward Frostroot's broken wall.",
                ),
                ExitDefinition(
                    "south",
                    TROLL_CHURNED_GULLY_KEY,
                    name="Churned Gully",
                    travel_text="With the fresh retreat line fixed in your mind, you follow it down into the gully.",
                    failure_text="The tracks fork here. Read and follow the fresh retreat sign before committing to the gully.",
                    condition=trail_followed,
                    hidden_when_unavailable=False,
                ),
            ),
            features=(
                _feature(
                    "retreat_track_fan",
                    "Retreat Track Fan",
                    "overlapping boots, blood drops, and false sign spread across ash-streaked snow",
                    "The deepest group of prints keeps a steady southward line. Two lighter sets wander as if injured. One set doubles back repeatedly along the edges, too deliberate to be panic; someone was watching for pursuit.",
                    aliases=("tracks", "raid tracks", "retreat tracks", "prints", "sign"),
                    search="A blood drop protected beneath a spruce bough is still glossy. The southbound line is fresh enough that weather has not softened its edges.",
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "track_route_chosen",
                    "You are here because Raska trusted you to learn something useful from the retreat, not to turn pursuit into revenge.",
                    priority=70,
                    condition=track_choice,
                ),
            ),
        ),
        TROLL_CHURNED_GULLY_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    TROLL_SMOLDERING_TRAIL_KEY,
                    name="Smoldering Trail",
                    travel_text="You climb north out of the gully toward Frostroot.",
                ),
            ),
            features=(
                _feature(
                    "false_uphill_track",
                    "False Uphill Track",
                    "a deliberately scraped boot line climbing toward bare stone",
                    "The marks are too clean and too evenly spaced. Someone wanted a pursuer to waste time climbing while the real group stayed in the low ground.",
                    aliases=("false track", "uphill track", "scrape"),
                ),
                _feature(
                    "searched_rearguard_site",
                    "Stripped Rearguard Gear",
                    "a few discarded straps and a cut length of black-waxed signal cord",
                    "Every identifying patch was removed before the rearguard was left behind. The useful clue is not a faction emblem but preparation: the retreat expected pursuit and had a system for signaling through bad weather.",
                    aliases=("rearguard gear", "cord", "signal cord", "body"),
                    condition=ViewCondition(required_flags=(TROLL_RAIDER_CLUE_FLAG,)),
                ),
            ),
        ),
        TROLL_ASHEN_SHELTER_ROW_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "east",
                    TROLL_BREACH_YARD_KEY,
                    name="South Breach Yard",
                    travel_text="You leave the shelter row for the breach yard.",
                ),
            ),
            features=(
                _feature(
                    "split_hide_roof",
                    "Split Hide Roof",
                    "a low shelter roof opened along a support seam by the raid",
                    "The main hide is still usable. The failure is at the lashing line, where one support pole twisted and tore the seam wider. A short brace and overlapping patch would keep sleet off the bedding.",
                    aliases=("roof", "shelter", "hide roof", "damaged shelter"),
                ),
                _feature(
                    "overturned_ration_sledge",
                    "Overturned Ration Sledge",
                    "food sacks and sealed hide containers lying in smoky meltwater",
                    "Some grain sacks are already ruined, but waxed meat packets and several tightly stitched root bags are still dry inside. Saving the sealed food first matters more than sorting everything perfectly.",
                    aliases=("food", "rations", "sledge", "stores", "supplies"),
                ),
                _feature(
                    "unbanked_hearth",
                    "Unbanked Hearth",
                    "useful coals burning too openly beside the damaged shelter",
                    "The fire is not out, which is good. It is also wasting fuel and throwing sparks toward torn hide, which is not. Ash and a covered ember pot could turn the same heat into something that lasts until morning.",
                    aliases=("hearth", "embers", "fire", "coals"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "shelter_route_chosen",
                    "You are here because the living still need dry bedding, food, and heat after the fighting ends.",
                    priority=70,
                    condition=camp_choice,
                ),
                DescriptionLayer(
                    "shelter_route_repaired",
                    "One shelter now wears a rough overlapping hide patch; rescued ration bundles sit dry beneath it, and a covered ember pot holds steady heat near the wounded.",
                    priority=90,
                    condition=ViewCondition(required_flags=(TROLL_CAMP_ROUTE_COMPLETE_FLAG,)),
                ),
            ),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    legacy_world.ROOMS = tuple(
        room if existing.key == room.key else existing for existing in legacy_world.ROOMS
    )
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _add_or_replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        _replace_room(room)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        legacy_world.ROOMS_BY_KEY[room.key] = room


def _start_room_with_breach_yard() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[troll_start.TROLL_START_ROOM_KEY]
    exits = dict(original.exits)
    exits["south"] = TROLL_BREACH_YARD_KEY
    return replace(original, exits=exits)


def _start_augmentation_with_choice(world_service) -> RoomAugmentation:
    base = world_service.augmentations.get(troll_start.TROLL_START_ROOM_KEY, RoomAugmentation())
    south_exit = ExitDefinition(
        direction="south",
        destination_key=TROLL_BREACH_YARD_KEY,
        name="South Breach Yard",
        travel_text="You pass through the damaged southern palisade into the emergency work yard.",
        failure_text="The southern breach is still an active danger. Deal with the immediate attack before leaving Frostroot's center.",
        condition=ViewCondition(required_flags=(troll_raid.TROLL_RAID_COMPLETE_FLAG,)),
        hidden_when_unavailable=True,
    )
    route_features = (
        _feature(
            "first_duty_trail_token",
            "Recovered Signal Cord",
            "a short length of black-waxed cord hanging from a peg near Raska's station",
            "You brought this cord back from the retreat trail. It identifies no people by itself, but it proves the raiders expected pursuit and used prepared signals while withdrawing.",
            aliases=("signal cord", "cord", "trail clue"),
            condition=ViewCondition(required_flags=(TROLL_TRACK_ROUTE_COMPLETE_FLAG,)),
        ),
        _feature(
            "first_duty_relief_stack",
            "Dry Relief Stack",
            "rescued ration bundles stored beneath a visibly patched section of hide roof",
            "The bundles stayed edible because someone moved the sealed food before sorting the ruined sacks. The patched shelter behind them is rough, dry, and still in use.",
            aliases=("relief stack", "saved food", "rations", "patched shelter"),
            condition=ViewCondition(required_flags=(TROLL_CAMP_ROUTE_COMPLETE_FLAG,)),
        ),
    )
    route_layers = (
        DescriptionLayer(
            "first_duty_track_memory",
            "A black-waxed signal cord hangs near Raska's station, kept from the retreat trail you followed after the raid.",
            priority=76,
            condition=ViewCondition(required_flags=(TROLL_TRACK_ROUTE_COMPLETE_FLAG,)),
        ),
        DescriptionLayer(
            "first_duty_camp_memory",
            "Near the breach, one rough hide patch still covers the shelter you helped save, with dry ration bundles stacked beneath it.",
            priority=76,
            condition=ViewCondition(required_flags=(TROLL_CAMP_ROUTE_COMPLETE_FLAG,)),
        ),
    )
    exits = tuple(exit_def for exit_def in base.exit_overrides if exit_def.direction != "south") + (south_exit,)
    return replace(
        base,
        exit_overrides=exits,
        features=base.features + route_features,
        description_layers=base.description_layers + route_layers,
    )


def install_troll_survivor_choice_content(world_service=None) -> None:
    """Register the post-raid two-route choice and its small persistent world echoes."""
    if TROLL_FIRST_DUTY_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (TROLL_FIRST_DUTY_QUEST,)
    quests.QUESTS_BY_KEY[TROLL_FIRST_DUTY_QUEST.key] = TROLL_FIRST_DUTY_QUEST

    if TROLL_REARGUARD_ENEMY_KEY not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (MASKED_REARGUARD,)
    combat.ENEMIES_BY_KEY[TROLL_REARGUARD_ENEMY_KEY] = MASKED_REARGUARD

    start_room = _start_room_with_breach_yard()
    _replace_room(start_room)
    for room in FIRST_DUTY_ROOMS:
        _add_or_replace_room(room)

    if world_service is not None:
        world_service.legacy_rooms[start_room.key] = start_room
        for room in FIRST_DUTY_ROOMS:
            world_service.legacy_rooms[room.key] = room
        world_service.augmentations[troll_start.TROLL_START_ROOM_KEY] = _start_augmentation_with_choice(world_service)
        world_service.augmentations.update(first_duty_room_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(troll_start.TROLL_START_ROOM_KEY, None)
            for room_key in TROLL_FIRST_DUTY_ROOM_KEYS:
                cache.pop(room_key, None)


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key)


def _raid_completed(session) -> bool:
    if session.character is None:
        return False
    raid = session.database.get_quest(session.character.id, troll_raid.TROLL_RAID_QUEST.key)
    return bool(raid and raid.get("status") == "completed")


def _grandfather_first_duty(session) -> None:
    assert session.character is not None
    session.database.start_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "complete")
    session.database.complete_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key)
    session.database.grant_flag(session.character.id, TROLL_FIRST_DUTY_COMPLETE_FLAG)
    session.database.grant_flag(session.character.id, TROLL_FIRST_DUTY_GRANDFATHERED_FLAG)


def _ensure_first_duty(session):
    """Create the choice after the raid while leaving already-progressed Trolls alone."""
    if session.character is None or session.character.race != "troll" or not _raid_completed(session):
        return None
    existing = _quest(session)
    if existing is not None:
        return existing

    cold = session.database.get_quest(session.character.id, troll_start.TROLL_COLD_QUEST.key)
    if cold is not None and (
        cold.get("status") == "completed"
        or (
            cold.get("status") == "active"
            and cold.get("current_step") not in {None, "speak_raska"}
        )
    ):
        _grandfather_first_duty(session)
        return _quest(session)

    session.database.start_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "choose_duty")
    return _quest(session)


def _step(session) -> str | None:
    duty = _quest(session)
    if duty and duty.get("status") == "active":
        return duty.get("current_step")
    return None


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


async def _announce_choice(session, *, force: bool = False) -> None:
    if session.character is None or _step(session) != "choose_duty":
        return
    flags = _flags(session)
    if not force and TROLL_FIRST_DUTY_SEEN_FLAG in flags:
        return
    session.database.grant_flag(session.character.id, TROLL_FIRST_DUTY_SEEN_FLAG)
    await session.send(
        "\r\nRaska looks past the dead wolf, past the broken wall, and into the rest of the damage.\r\n"
        "'The night is not over just because nothing is biting you right now.'\r\n"
        "He points south. 'The raiders left a fresh retreat line. Snow will eat it. Someone needs to learn where they went before it is gone.'\r\n"
        "Then he points toward the sagging shelter row. 'Food is sitting in meltwater, a roof is open, and wounded Trolls need heat. Someone needs to make sure the living survive the next few hours.'\r\n"
        "Raska meets your eyes. 'I have one of you and two useful jobs. Choose the one you can finish.'\r\n"
        "\r\n  TRACK RAIDERS  - follow the retreat trail; expect danger.\r\n"
        "  SECURE CAMP    - save food, shelter, and heat for the wounded.\r\n"
        "\r\nNeither choice is the brave choice. They are both work Frostroot needs.\r\n"
        "New quest: What Still Needs Doing.\r\n"
    )


async def _show_first_duty_status(session) -> None:
    duty = _quest(session)
    await session.send("\r\n--- Frostroot: First Duty After the Raid ---\r\n")
    if duty is None:
        await session.send("No first duty has been assigned yet.\r\n")
        return
    flags = _flags(session)
    if duty.get("status") == "completed":
        if TROLL_TRACK_ROUTE_COMPLETE_FLAG in flags:
            await session.send("First duty: followed the raiders' retreat and returned with useful trail evidence.\r\n")
        elif TROLL_CAMP_ROUTE_COMPLETE_FLAG in flags:
            await session.send("First duty: secured damaged shelter, food, and heat for Frostroot's wounded.\r\n")
        elif TROLL_FIRST_DUTY_GRANDFATHERED_FLAG in flags:
            await session.send("First duty: grandfathered for a Troll who had already progressed beyond this new opening.\r\n")
        else:
            await session.send("First duty: complete.\r\n")
        return
    if TROLL_TRACK_CHOICE_FLAG in flags:
        await session.send("Chosen route: TRACK RAIDERS.\r\n")
    elif TROLL_CAMP_CHOICE_FLAG in flags:
        await session.send("Chosen route: SECURE CAMP.\r\n")
    else:
        await session.send("Chosen route: not yet chosen.\r\n")
    objective = TROLL_FIRST_DUTY_QUEST.objective_for_step(duty.get("current_step"))
    if objective:
        await session.send(f"Current objective: {objective}\r\n")


async def _choose_first_duty(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "troll" or _step(session) != "choose_duty":
        return False
    track_commands = {
        "track raiders",
        "track the raiders",
        "follow raiders",
        "choose track raiders",
        "choose track",
        "track retreat",
    }
    camp_commands = {
        "secure camp",
        "secure the camp",
        "secure food and shelter",
        "help camp",
        "save food and shelter",
        "choose secure camp",
        "stay and help",
    }
    if normalized in track_commands:
        session.database.grant_flag(session.character.id, TROLL_TRACK_CHOICE_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "track_read")
        await session.send(
            "\r\nRaska nods once. 'Then learn something. Do not turn pursuit into revenge.'\r\n"
            "'Go SOUTH into the breach yard, then SOUTH again to the Smoldering Trail. READ TRACKS before you follow anyone into ground they chose.'\r\n"
            "You have chosen: TRACK RAIDERS.\r\n"
        )
        return True
    if normalized in camp_commands:
        session.database.grant_flag(session.character.id, TROLL_CAMP_CHOICE_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "camp_check")
        await session.send(
            "\r\nRaska nods once. 'Good. The dead do not need a roof. The living do.'\r\n"
            "'Go SOUTH into the breach yard, then WEST to Ashen Shelter Row. CHECK SHELTERS before you start moving things around.'\r\n"
            "You have chosen: SECURE CAMP.\r\n"
        )
        return True
    return False


async def _handle_track_route(session, normalized: str) -> bool:
    if session.character is None or TROLL_TRACK_CHOICE_FLAG not in _flags(session):
        return False
    step = _step(session)
    room = session.character.current_room

    if room == TROLL_SMOLDERING_TRAIL_KEY and normalized in {
        "read tracks",
        "read raid tracks",
        "examine tracks",
        "inspect tracks",
        "read retreat tracks",
        "examine retreat tracks",
    }:
        if step != "track_read":
            if TROLL_RETREAT_TRACKS_READ_FLAG in _flags(session):
                await session.send("\r\nYou already separated the fresh retreat line from the older sign.\r\n")
                return True
            await session.send("\r\nThere is sign here, but your current duty is not at the reading step.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_RETREAT_TRACKS_READ_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "track_follow")
        await session.send(
            "\r\nYou ignore the first print that looks dramatic and read the whole trail. The main group went south in a hurry. Two sets stagger from injury. One set repeatedly doubles back along the edges, stepping lightly and choosing cover.\r\n"
            "That last walker was not lost. Someone was guarding the retreat. FOLLOW RAIDERS.\r\n"
        )
        return True

    if room == TROLL_SMOLDERING_TRAIL_KEY and normalized in {
        "follow raiders",
        "follow the raiders",
        "follow retreat",
        "track raiders",
        "track retreat",
    }:
        if step != "track_follow":
            await session.send("\r\nFollowing before reading is how a pursuer walks into someone else's plan. READ TRACKS first.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_RETREAT_FOLLOWED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "track_fight")
        await session.send(
            "\r\nYou follow the guarded line rather than the loudest prints. It drops south into a churned gully where a false track climbs exposed stone. A shape shifts behind a fallen spruce below.\r\n"
            "The rearguard waited where a pursuer would have to commit. Go SOUTH and ATTACK REARGUARD.\r\n"
        )
        return True

    if room == TROLL_CHURNED_GULLY_KEY and normalized in {
        "search rearguard",
        "search raider",
        "search body",
        "examine rearguard",
        "examine raider",
        "inspect rearguard",
    }:
        if step != "track_search":
            if step == "track_fight":
                await session.send("\r\nThe rearguard is still a threat. Deal with the fight before searching anything.\r\n")
                return True
            if TROLL_RAIDER_CLUE_FLAG in _flags(session):
                await session.send("\r\nYou already recovered everything the rearguard left that could tell Raska something useful.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, TROLL_RAIDER_CLUE_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "return_raska")
        await session.send(
            "\r\nThe mask and outer coat tell you almost nothing because someone cut away every obvious badge before the retreat. That is information by itself.\r\n"
            "A short length of black-waxed cord is knotted through the belt in a repeating pattern, protected from weather beneath the coat. The boot soles also carry pale mineral grit that does not match Frostroot's dark forest soil.\r\n"
            "They expected pursuit, prepared to hide who they were, and were signaling through bad weather. That is enough to bring home.\r\n"
            "Return NORTH through the Smoldering Trail and breach yard, then TALK RASKA.\r\n"
        )
        return True

    return False


async def _handle_camp_route(session, normalized: str) -> bool:
    if session.character is None or TROLL_CAMP_CHOICE_FLAG not in _flags(session):
        return False
    if session.character.current_room != TROLL_ASHEN_SHELTER_ROW_KEY:
        return False
    step = _step(session)

    if normalized in {
        "check shelters",
        "check shelter",
        "inspect shelters",
        "inspect shelter",
        "examine shelters",
        "assess shelters",
    }:
        if step != "camp_check":
            if TROLL_SHELTERS_CHECKED_FLAG in _flags(session):
                await session.send("\r\nYou already know the order: save dry food, close the roof, then preserve the fire.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, TROLL_SHELTERS_CHECKED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "camp_salvage")
        await session.send(
            "\r\nThe roof damage matters, but the ration sledge is getting worse by the minute. Unsealed grain is already lost. Waxed meat packets and several stitched root bags are still dry inside if they are moved now.\r\n"
            "The hearth can wait a few minutes. SALVAGE FOOD first.\r\n"
        )
        return True

    if normalized in {
        "salvage food",
        "save food",
        "save rations",
        "salvage rations",
        "move food",
        "recover food",
    }:
        if step != "camp_salvage":
            await session.send("\r\nCheck the whole shelter row before deciding what to move first. CHECK SHELTERS.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_FOOD_SAVED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "camp_patch")
        await session.send(
            "\r\nYou pull sealed packets and tightly stitched root bags onto dry stones beneath the eaves. The soaked grain stays where it is; wasting time rescuing ruined food would cost the food that is still good.\r\n"
            "With the stores safe from the meltwater, PATCH SHELTER.\r\n"
        )
        return True

    if normalized in {
        "patch shelter",
        "repair shelter",
        "patch roof",
        "repair roof",
        "fix shelter",
        "fix roof",
    }:
        if step != "camp_patch":
            if step == "camp_salvage":
                await session.send("\r\nThe roof can survive another few minutes. The food in meltwater cannot. SALVAGE FOOD first.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, TROLL_SHELTER_PATCHED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "camp_embers")
        await session.send(
            "\r\nYou brace the twisted support with a straight length from a broken sledge, overlap an intact hide patch above the tear, and lash it low enough that the next gust presses the repair closed instead of lifting it. The dripping stops over the wounded bedding.\r\n"
            "One problem remains before this shelter is useful through the night. BANK EMBERS.\r\n"
        )
        return True

    if normalized in {
        "bank embers",
        "bank fire",
        "bank coals",
        "cover embers",
        "save embers",
        "tend hearth",
    }:
        if step != "camp_embers":
            if step == "camp_patch":
                await session.send("\r\nDo not preserve a fire beneath a roof that is still leaking and throwing loose hide toward sparks. PATCH SHELTER first.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, TROLL_EMBERS_BANKED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "return_raska")
        await session.send(
            "\r\nYou rake the hottest coals together, cover most of them with ash, and transfer a small live core into the shelter's lidded ember pot. The open flame shrinks, sparks stop reaching for the repaired hide, and the same fuel will now last hours longer.\r\n"
            "The rescued food is dry, the wounded have a roof, and the heat will last. Go EAST to the breach yard, NORTH to Frostroot Camp, and TALK RASKA.\r\n"
        )
        return True

    return False


def _record_rearguard_defeat(session) -> None:
    if session.character is None or _step(session) != "track_fight":
        return
    session.database.grant_flag(session.character.id, TROLL_REARGUARD_DEFEATED_FLAG)
    session.database.advance_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key, "track_search")


async def _talk_raska_first_duty(session) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    duty = _quest(session)
    if not duty or duty.get("status") != "active":
        return False
    step = duty.get("current_step")

    if step == "choose_duty":
        await _announce_choice(session, force=True)
        return True

    if step == "return_raska":
        if session.character.current_room != troll_start.TROLL_START_ROOM_KEY:
            await session.send("\r\nRaska is back at Frostroot Camp. Finish returning before reporting the job.\r\n")
            return True
        flags = _flags(session)
        if TROLL_TRACK_CHOICE_FLAG in flags:
            session.database.grant_flag(session.character.id, TROLL_TRACK_ROUTE_COMPLETE_FLAG)
            route_text = (
                "Raska turns the black-waxed cord over between two fingers. 'No badge. False tracks. "
                "A prepared signal cord. Good. You came back with facts instead of a story about how far you chased them.'\r\n"
                "He hangs the cord from a peg beside his gear. 'Tracking is not revenge. Knowing when you know enough is part of coming home.'"
            )
        else:
            session.database.grant_flag(session.character.id, TROLL_CAMP_ROUTE_COMPLETE_FLAG)
            route_text = (
                "Raska looks toward the patched shelter and the dry ration stack. 'Good. A stronghold does not survive because everyone runs toward the loudest danger.'\r\n"
                "He watches a wounded Troll carry the covered ember pot under the repaired roof. 'You noticed what would have killed us three hours from now and made it smaller.'"
            )
        session.database.grant_flag(session.character.id, TROLL_FIRST_DUTY_COMPLETE_FLAG)
        session.database.complete_quest(session.character.id, TROLL_FIRST_DUTY_QUEST.key)
        troll_start._initialize_or_reconcile_troll(session)
        await session.send(
            "\r\n" + route_text + "\r\n"
            "Raska settles back against the palisade. 'Different work. Same rule. Survival is choosing the useful thing before pride chooses for you.'\r\n"
            "Quest complete: What Still Needs Doing.\r\n"
            "Your choice will remain part of Frostroot's raid aftermath.\r\n"
            "Next: A Fire Before Pride. TALK RASKA again when you are ready for the first formal survival lesson.\r\n"
        )
        return True

    objective = TROLL_FIRST_DUTY_QUEST.objective_for_step(step)
    await session.send("\r\nRaska says, 'Finish the job you chose. Frostroot needs completed work more than good intentions.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


def _rearguard_target(text: str) -> bool:
    return MASKED_REARGUARD.matches(text)


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_troll_survivor_choice_runtime(player_session_class, world_service) -> None:
    """Layer the two-route first duty after the raid and before Frostroot's formal lessons."""
    install_troll_survivor_choice_content(world_service)
    if getattr(player_session_class, "_troll_survivor_choice_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "troll":
            return
        duty = _ensure_first_duty(self)
        if duty and duty.get("status") == "active":
            if duty.get("current_step") == "choose_duty":
                await _announce_choice(self)
            else:
                objective = TROLL_FIRST_DUTY_QUEST.objective_for_step(duty.get("current_step"))
                await self.send("\r\nFrostroot first duty still unresolved: What Still Needs Doing.\r\n")
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")

    def _enemy_in_current_room(self, target_text: str):
        if (
            self.character is not None
            and self.character.race == "troll"
            and self.character.current_room == TROLL_CHURNED_GULLY_KEY
            and _step(self) == "track_fight"
            and _rearguard_target(target_text)
        ):
            return EnemyState(MASKED_REARGUARD)
        return previous_enemy_lookup(self, target_text)

    async def _finish_enemy_defeat(self, enemy) -> None:
        is_rearguard = (
            self.character is not None
            and self.character.race == "troll"
            and enemy.definition.key == TROLL_REARGUARD_ENEMY_KEY
            and _step(self) == "track_fight"
        )
        await previous_finish_enemy(self, enemy)
        if not is_rearguard or self.character is None:
            return
        _record_rearguard_defeat(self)
        await self.send(
            "\r\nThe masked rearguard drops beside the fallen spruce. The rest of the retreat is already farther south; chasing blindly would trade information for distance.\r\n"
            "SEARCH REARGUARD before deciding what Raska actually needs to know.\r\n"
        )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "troll":
            await previous_playing_prompt(self)
            return

        duty = _ensure_first_duty(self)
        if not duty or duty.get("status") != "active":
            raid_before = self.database.get_quest(self.character.id, troll_raid.TROLL_RAID_QUEST.key)
            raid_was_return = bool(
                raid_before
                and raid_before.get("status") == "active"
                and raid_before.get("current_step") == "return_raska"
            )
            await previous_playing_prompt(self)
            if self.character is None or self.character.race != "troll":
                return
            duty_after = _ensure_first_duty(self)
            if raid_was_return and duty_after and duty_after.get("status") == "active":
                await _announce_choice(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()
        room = self.character.current_room
        step = _step(self)

        if normalized in {"duty", "first duty", "survivor", "survival", "survival record"}:
            await _show_first_duty_status(self)
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = troll_start._talk_target(command)
            if (
                room == troll_start.TROLL_START_ROOM_KEY
                and troll_start._matches(
                    target,
                    "raska",
                    "hunter",
                    "hunter raska",
                    "raska greybark",
                    "mentor",
                )
            ):
                if await _talk_raska_first_duty(self):
                    return

        if await _choose_first_duty(self, normalized):
            return
        if await _handle_track_route(self, normalized):
            return
        if await _handle_camp_route(self, normalized):
            return

        direction_aliases = {
            "n": "north",
            "s": "south",
            "e": "east",
            "w": "west",
            "u": "up",
            "d": "down",
        }
        direction = direction_aliases.get(normalized, normalized)
        if direction in {"north", "south", "east", "west", "up", "down"}:
            if step == "choose_duty":
                await self.send(
                    "\r\nRaska stops you before you leave. 'Choose the job first. TRACK RAIDERS or SECURE CAMP. I need to know which problem still has hands on it.'\r\n"
                )
                return
            if room == troll_start.TROLL_START_ROOM_KEY and direction != "south":
                await self.send(
                    "\r\nThe formal Frostroot lessons can wait. Your first duty after the raid is still unfinished; the emergency routes begin SOUTH at the breach.\r\n"
                )
                return

        if normalized.startswith("attack ") or normalized.startswith("kill "):
            target = command.strip().split(maxsplit=1)[1]
            if _rearguard_target(target) and step != "track_fight":
                await self.send("\r\nThere is no rearguard here to fight at this stage of the trail. Read the situation in order.\r\n")
                return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if self.character is None:
            return
        if normalized in {"look", "l"} and self.character.current_room == TROLL_CHURNED_GULLY_KEY and _step(self) == "track_fight":
            await self.send(
                "A Masked Raid Rearguard is crouched behind the fallen spruce, wounded but waiting for pursuit. ATTACK REARGUARD.\r\n"
            )
        if normalized in {"help", "?"}:
            await self.send(
                "Troll first duty: choose TRACK RAIDERS or SECURE CAMP. Use DUTY to review the current objective. The tracking route uses READ TRACKS, FOLLOW RAIDERS, ATTACK REARGUARD, and SEARCH REARGUARD. The camp route uses CHECK SHELTERS, SALVAGE FOOD, PATCH SHELTER, and BANK EMBERS.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = _enemy_in_current_room
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._troll_survivor_choice_runtime_installed = True
