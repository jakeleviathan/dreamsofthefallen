from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.veyra_city import VEYRA_NORTH_WATERWORKS_KEY, VEYRA_RESIDENT_FLAG
from mud.world import RoomDefinition


UNDERCLOCK_REGION_KEY = "veyra_underclock"
UNDERCLOCK_INTAKE_KEY = "underclock_intake_stair"
UNDERCLOCK_GAUGE_KEY = "underclock_master_gauge_hall"
UNDERCLOCK_PISTON_KEY = "underclock_piston_gallery"
UNDERCLOCK_FLYWHEEL_KEY = "underclock_flywheel_walk"
UNDERCLOCK_STEAM_KEY = "underclock_steam_throat"
UNDERCLOCK_CONDENSER_KEY = "underclock_condenser_court"
UNDERCLOCK_BALANCE_KEY = "underclock_balance_well"
UNDERCLOCK_TEETH_KEY = "underclock_walking_teeth"
UNDERCLOCK_GOVERNOR_KEY = "underclock_governor_gallery"
UNDERCLOCK_ASH_KEY = "underclock_ash_sump"
UNDERCLOCK_MINUTE_KEY = "underclock_minute_chamber"
UNDERCLOCK_LIFT_KEY = "underclock_upper_lift_head"

UNDERCLOCK_ROOM_KEYS = (
    UNDERCLOCK_INTAKE_KEY,
    UNDERCLOCK_GAUGE_KEY,
    UNDERCLOCK_PISTON_KEY,
    UNDERCLOCK_FLYWHEEL_KEY,
    UNDERCLOCK_STEAM_KEY,
    UNDERCLOCK_CONDENSER_KEY,
    UNDERCLOCK_BALANCE_KEY,
    UNDERCLOCK_TEETH_KEY,
    UNDERCLOCK_GOVERNOR_KEY,
    UNDERCLOCK_ASH_KEY,
    UNDERCLOCK_MINUTE_KEY,
    UNDERCLOCK_LIFT_KEY,
)

UNDERCLOCK_QUEST_KEY = "veyra_city_between_ticks"
UNDERCLOCK_COMPLETE_FLAG = "veyra_underclock_complete"
GAUGE_READ_FLAG = "underclock_gauge_read"
PISTONS_CROSSED_FLAG = "underclock_pistons_crossed"
STEAM_CROSSED_FLAG = "underclock_steam_crossed"
TEETH_CROSSED_FLAG = "underclock_teeth_crossed"
INTAKE_SET_FLAG = "underclock_intake_set"
FLYWHEEL_LOCKED_FLAG = "underclock_flywheel_locked"
GOVERNOR_BLED_FLAG = "underclock_governor_bled"
GOVERNOR_ENGAGED_FLAG = "underclock_governor_engaged"
GOVERNOR_DEFEATED_FLAG = "underclock_governor_defeated"

SOOTBACK_KEY = "underclock_sootback_rat"
GREASEWASP_KEY = "underclock_grease_wasp"
VALVECRAWLER_KEY = "underclock_valve_crawler"
GOVERNOR_KEY = "underclock_cinder_governor"
GOVERNOR_BEARING_KEY = "underclock_governor_bearing"

PHASES = ("intake", "pressure", "vent", "reset")
PHASE_SECONDS = 8.0
_PHASE_OVERRIDE: str | None = None


@dataclass(frozen=True, slots=True)
class ClockState:
    phase: str
    seconds_remaining: int


UNDERCLOCK_QUEST = QuestDefinition(
    key=UNDERCLOCK_QUEST_KEY,
    name="The City Between Ticks",
    style="structured",
    minimum_level=8,
    description=(
        "Veyra's oldest high-water lift has begun losing pressure beneath the North Waterworks. "
        "The Underclock is a municipal machine, not a Gloam anomaly: read its four-beat cycle, cross moving hazards at the right moment, and restart the lift without becoming part of the mechanism."
    ),
    objective_steps=(
        ("read_cycle", "Reach the Master Gauge Hall and EXAMINE MASTER GAUGE."),
        ("cross_pistons", "At the Piston Gallery use CLOCK, then CROSS PISTONS during RESET."),
        ("cross_steam", "At the Steam Throat use CLOCK, then CROSS STEAM during INTAKE."),
        ("cross_teeth", "At the Walking Teeth use CLOCK, then CROSS TEETH during VENT."),
        ("calibrate_governor", "At the Governor Gallery SET INTAKE VALVE during INTAKE, LOCK FLYWHEEL during RESET, and BLEED GOVERNOR during VENT."),
        ("engage_governor", "When all three controls are set, ENGAGE GOVERNOR."),
        ("defeat_governor", "Defeat the Cinder Governor after taking its pressure controls away."),
        ("restart_lift", "Enter the Minute Chamber and START LIFT."),
        ("complete", "You restored the Underclock by learning its rhythm instead of overpowering the whole machine."),
    ),
)

GOVERNOR_BEARING = ItemDefinition(
    key=GOVERNOR_BEARING_KEY,
    name="Governor Bearing",
    description="A heat-dark precision bearing from Veyra's old pressure governor. It is valuable because it survived decades of real work, not because it is magical.",
    category="material",
    tier=3,
)

SOOTBACK = EnemyDefinition(
    key=SOOTBACK_KEY,
    name="Sootback Rat",
    aliases=("rat", "sootback", "sootback rat"),
    description="a dog-sized maintenance-tunnel rat with blackened fur and pale whiskers stained by mineral steam",
    max_hp=96,
    armor_class=9,
    auto_attack_damage=8,
    auto_attack_interval=2.9,
    xp_reward=72,
)
GREASEWASP = EnemyDefinition(
    key=GREASEWASP_KEY,
    name="Grease Wasp",
    aliases=("wasp", "grease wasp", "greasewasp"),
    description="a heavy tunnel wasp nesting in warm bearing grease, its wings clicking against iron housings when it turns",
    max_hp=118,
    armor_class=11,
    auto_attack_damage=10,
    auto_attack_interval=2.6,
    xp_reward=88,
)
VALVECRAWLER = EnemyDefinition(
    key=VALVECRAWLER_KEY,
    name="Valve Crawler",
    aliases=("crawler", "valve crawler", "valvecrawler"),
    description="a broad pale arthropod that clamps itself around warm pipes and attacks anything that changes the pressure around its nest",
    max_hp=145,
    armor_class=13,
    auto_attack_damage=12,
    auto_attack_interval=3.0,
    xp_reward=112,
)
CINDER_GOVERNOR = EnemyDefinition(
    key=GOVERNOR_KEY,
    name="Cinder Governor",
    aliases=("governor", "cinder governor", "pressure governor"),
    description=(
        "a man-high pressure regulator walking on four braced legs, with flyballs spinning above a furnace-red core; "
        "it was built to correct dangerous pressure and has eventually concluded that unauthorized people are pressure"
    ),
    max_hp=330,
    armor_class=18,
    auto_attack_damage=16,
    auto_attack_interval=2.8,
    xp_reward=300,
)
UNDERCLOCK_ENEMIES = (SOOTBACK, GREASEWASP, VALVECRAWLER, CINDER_GOVERNOR)


def _room(key: str, name: str, description: str, exits: dict[str, str], *, enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=UNDERCLOCK_REGION_KEY,
        description=description,
        exits=exits,
        enemy_keys=enemies,
        tags=("dungeon", "veyra", "underclock", "level_8_10", *tags),
    )


UNDERCLOCK_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        UNDERCLOCK_INTAKE_KEY,
        "Underclock Intake Stair",
        "A maintenance stair descends beneath Veyra's clean public channels into an older layer of black brick, sweating pipes, and iron labels polished by generations of hands. The machine below is loud enough to feel through the soles of your boots: four different beats repeating in order.",
        {"up": VEYRA_NORTH_WATERWORKS_KEY, "east": UNDERCLOCK_GAUGE_KEY},
        enemies=(SOOTBACK_KEY,), tags=("entrance",),
    ),
    _room(
        UNDERCLOCK_GAUGE_KEY,
        "Master Gauge Hall",
        "Four enormous dial faces share one wall: INTAKE, PRESSURE, VENT, RESET. A brass pointer transfers from one dial to the next as the entire water-lift system breathes through its cycle. A painted maintenance rule survives beneath soot: NEVER CROSS A MOVING PART BECAUSE YOU ARE IN A HURRY.",
        {"west": UNDERCLOCK_INTAKE_KEY, "south": UNDERCLOCK_PISTON_KEY},
        enemies=(GREASEWASP_KEY,), tags=("cycle_tutorial",),
    ),
    _room(
        UNDERCLOCK_PISTON_KEY,
        "Piston Gallery",
        "Three horizontal pump rods cross the passage at chest, knee, and ankle height. During most of the cycle they move with enough force to make the masonry flinch. A recessed maintenance lane lines up only when the rods return completely home.",
        {"north": UNDERCLOCK_GAUGE_KEY}, tags=("timed_hazard",),
    ),
    _room(
        UNDERCLOCK_FLYWHEEL_KEY,
        "Flywheel Walk",
        "A narrow iron walk curves around a flywheel taller than a house. Chalk timing marks on the rim pass the railing with hypnotic regularity. The whole wheel exists to make violent motion predictable.",
        {"west": UNDERCLOCK_PISTON_KEY, "east": UNDERCLOCK_STEAM_KEY},
        enemies=(GREASEWASP_KEY,), tags=("machinery",),
    ),
    _room(
        UNDERCLOCK_STEAM_KEY,
        "Steam Throat",
        "The corridor pinches between paired pressure mains. During the pressure and vent beats, white steam feathers from relief seams and turns the middle of the passage into a bright scalding wall. During intake the mains draw cool enough to pass between them.",
        {"west": UNDERCLOCK_FLYWHEEL_KEY}, tags=("timed_hazard",),
    ),
    _room(
        UNDERCLOCK_CONDENSER_KEY,
        "Condenser Court",
        "Cold pipes web a tall brick chamber where exhausted steam becomes water again and drums into stone gutters. The noise here is rain made by machinery. Old maintenance hooks hang beside newer chalk notes from city crews who stopped coming when the governor began misbehaving.",
        {"west": UNDERCLOCK_STEAM_KEY, "north": UNDERCLOCK_BALANCE_KEY},
        enemies=(SOOTBACK_KEY, VALVECRAWLER_KEY), tags=("machinery",),
    ),
    _room(
        UNDERCLOCK_BALANCE_KEY,
        "Counterweight Well",
        "Stone weights rise and fall inside a shaft whose bottom disappears into mist. Iron stairs spiral around the motion. Every few seconds the descending mass makes the air itself press outward before climbing again.",
        {"south": UNDERCLOCK_CONDENSER_KEY, "east": UNDERCLOCK_TEETH_KEY},
        enemies=(VALVECRAWLER_KEY,), tags=("vertical",),
    ),
    _room(
        UNDERCLOCK_TEETH_KEY,
        "The Walking Teeth",
        "The floor ahead is not a floor. It is the upper edge of a gigantic horizontal gear whose square teeth pass through a gap between two platforms. Most of the time the teeth are moving walls. During the vent beat the clutch releases and, for a few seconds, those same teeth become a perfectly spaced stone-and-iron path across the void.",
        {"west": UNDERCLOCK_BALANCE_KEY}, tags=("timed_hazard", "signature_moment"),
    ),
    _room(
        UNDERCLOCK_GOVERNOR_KEY,
        "Governor Gallery",
        "Three manual stations surround a circular machinery pit: an intake valve wheel, a flywheel lock, and a pressure bleed. In the center, the Cinder Governor paces its rail, correcting the machine more aggressively every cycle. The controls can make it fight on your terms, but each can only be safely set during the right beat.",
        {"west": UNDERCLOCK_TEETH_KEY, "south": UNDERCLOCK_ASH_KEY, "east": UNDERCLOCK_MINUTE_KEY},
        tags=("boss", "timed_controls"),
    ),
    _room(
        UNDERCLOCK_ASH_KEY,
        "Ash Sump",
        "A maintenance sump below the governor catches soot, scale, broken packing, and whatever else falls out of the upper machine. Warm pipes make it a perfect nest for things that prefer their caves engineered.",
        {"north": UNDERCLOCK_GOVERNOR_KEY}, enemies=(VALVECRAWLER_KEY, SOOTBACK_KEY), tags=("combat",),
    ),
    _room(
        UNDERCLOCK_MINUTE_KEY,
        "Minute Chamber",
        "A quiet room sits immediately behind the governor pit. Its only machinery is a single timing shaft and a start lever connected upward toward the water-lift head. The shaft makes one complete turn through all four beats, giving the chamber its old workers' name: the place where the whole city could be reduced to one repeating minute.",
        {"west": UNDERCLOCK_GOVERNOR_KEY, "east": UNDERCLOCK_LIFT_KEY}, tags=("objective",),
    ),
    _room(
        UNDERCLOCK_LIFT_KEY,
        "Upper Lift Head",
        "Massive pump columns disappear upward into the North Waterworks. Through narrow service grilles you can hear Veyra above: cart wheels, distant bells, somebody arguing about fish prices. The hidden machine and the ordinary city are one system after all.",
        {"west": UNDERCLOCK_MINUTE_KEY}, tags=("completion",),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(key=key, name=name, summary=summary, examine_text=examine, aliases=aliases)


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    overrides = {item.direction: item for item in existing.exit_overrides}
    overrides.update({item.direction: item for item in extra.exit_overrides})
    extras = {(item.direction, item.destination_key): item for item in existing.extra_exits}
    extras.update({(item.direction, item.destination_key): item for item in extra.extra_exits})
    features = {item.key: item for item in existing.features}
    features.update({item.key: item for item in extra.features})
    layers = {item.key: item for item in existing.description_layers}
    layers.update({item.key: item for item in extra.description_layers})
    return RoomAugmentation(tuple(overrides.values()), tuple(extras.values()), tuple(features.values()), tuple(layers.values()))


def underclock_augmentations() -> dict[str, RoomAugmentation]:
    return {
        VEYRA_NORTH_WATERWORKS_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=UNDERCLOCK_INTAKE_KEY,
                    name="Underclock Maintenance Stair",
                    travel_text="You pass a maintenance rail and descend below the public water channels into the Underclock.",
                    condition=ViewCondition(required_flags=(VEYRA_RESIDENT_FLAG,), min_level=8),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "underclock_service_hatch",
                    "Underclock Service Hatch",
                    "an old iron maintenance stair descending below the public water channels",
                    "A warning plate lists four words in large stamped letters: INTAKE — PRESSURE — VENT — RESET. Fresh chalk underneath reads: GOVERNOR OUT OF TOLERANCE. EXPERIENCED HANDS ONLY.",
                    ("hatch", "service hatch", "underclock", "stair"),
                ),
            ),
        ),
        UNDERCLOCK_GAUGE_KEY: RoomAugmentation(
            features=(
                _feature(
                    "underclock_master_gauge",
                    "Master Gauge",
                    "four linked dials showing the current mechanical beat",
                    "The four dials are not separate measurements; they are one cycle shown four ways. Intake draws water. Pressure drives it upward. Vent dumps excess force. Reset returns the rods, clutch, and governor to their starting geometry. CLOCK reports the live phase anywhere in the Underclock.",
                    ("gauge", "master gauge", "dials", "dial"),
                ),
            ),
        ),
        UNDERCLOCK_GOVERNOR_KEY: RoomAugmentation(
            features=(
                _feature("underclock_intake_control", "Intake Valve", "a manual wheel that can pin the intake feed at a known setting", "The valve can only be set cleanly while the machine is already drawing water. Use SET INTAKE VALVE during INTAKE.", ("intake", "intake valve", "valve")),
                _feature("underclock_flywheel_lock", "Flywheel Lock", "a heavy pawl aligned to catch the flywheel only when it comes home", "The lock is designed for the RESET beat, when stored motion is at its lowest. Use LOCK FLYWHEEL during RESET.", ("flywheel", "lock", "flywheel lock")),
                _feature("underclock_governor_bleed", "Governor Bleed", "a pressure bleed that strips stored force from the governor rail", "The bleed belongs to the VENT beat. Opening it at the wrong time would add pressure to the exact line you are trying to calm. Use BLEED GOVERNOR during VENT.", ("bleed", "governor bleed", "pressure bleed")),
            ),
        ),
    }


def clock_state(now: float | None = None) -> ClockState:
    if _PHASE_OVERRIDE in PHASES:
        return ClockState(_PHASE_OVERRIDE, int(PHASE_SECONDS))
    current = monotonic() if now is None else max(0.0, now)
    phase_index = int(current // PHASE_SECONDS) % len(PHASES)
    elapsed = current % PHASE_SECONDS
    remaining = max(1, int(PHASE_SECONDS - elapsed + 0.999))
    return ClockState(PHASES[phase_index], remaining)


def set_underclock_phase_for_tests(phase: str | None) -> None:
    global _PHASE_OVERRIDE
    if phase is not None and phase not in PHASES:
        raise ValueError(f"Unknown Underclock phase: {phase}")
    _PHASE_OVERRIDE = phase


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def install_underclock_content(world_service=None) -> None:
    if UNDERCLOCK_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (UNDERCLOCK_QUEST,)
    quests.QUESTS_BY_KEY[UNDERCLOCK_QUEST.key] = UNDERCLOCK_QUEST

    if GOVERNOR_BEARING.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (GOVERNOR_BEARING,)
    crafting.ITEMS_BY_KEY[GOVERNOR_BEARING.key] = GOVERNOR_BEARING

    for enemy in UNDERCLOCK_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for room in UNDERCLOCK_ROOMS:
        _replace_room(room)

    if world_service is None:
        return
    for room in UNDERCLOCK_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in underclock_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*UNDERCLOCK_ROOM_KEYS, VEYRA_NORTH_WATERWORKS_KEY):
            cache.pop(key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, UNDERCLOCK_QUEST_KEY)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _ensure_quest(session) -> bool:
    if session.character is None:
        return False
    if session.character.current_room not in UNDERCLOCK_ROOM_KEYS:
        return False
    flags = _flags(session)
    if VEYRA_RESIDENT_FLAG not in flags or session.character.level < 8:
        return False
    if UNDERCLOCK_COMPLETE_FLAG in flags:
        return True
    if _quest(session) is None:
        session.database.start_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "read_cycle")
    return True


def _movement_penalty(session, amount: int = 6) -> None:
    combatant = getattr(session, "combatant", None)
    if combatant is not None:
        combatant.current_movement = max(0, combatant.current_movement - amount)


async def _show_clock(session) -> bool:
    if session.character is None or session.character.current_room not in UNDERCLOCK_ROOM_KEYS:
        return False
    state = clock_state()
    await session.send(f"UNDERCLOCK — {state.phase.upper()} phase, about {state.seconds_remaining}s until the next beat. Sequence: INTAKE → PRESSURE → VENT → RESET.\r\n")
    return True


async def _read_gauge(session) -> bool:
    if session.character is None or session.character.current_room != UNDERCLOCK_GAUGE_KEY:
        return False
    _ensure_quest(session)
    q = _quest(session)
    session.database.grant_flag(session.character.id, GAUGE_READ_FLAG)
    if q and q["status"] == "active" and q["current_step"] == "read_cycle":
        session.database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "cross_pistons")
    await session.send(
        "The linked dials reveal one four-beat machine: INTAKE draws, PRESSURE drives, VENT releases, RESET returns everything home. The Piston Gallery is crossable during RESET. Use CLOCK to read the live beat before committing.\r\n"
    )
    return True


async def _timed_cross(session, *, room_key: str, safe_phase: str, destination: str, flag: str, expected_step: str, next_step: str, label: str) -> bool:
    if session.character is None or session.character.current_room != room_key:
        return False
    _ensure_quest(session)
    state = clock_state()
    if state.phase != safe_phase:
        _movement_penalty(session)
        await session.send(
            f"You start toward {label}, but the machinery enters {state.phase.upper()} before the route is safe. You pull back instead of gambling your body against municipal iron. Movement -6. Safe beat: {safe_phase.upper()}.\r\n"
        )
        return True
    session.database.grant_flag(session.character.id, flag)
    session.database.set_character_room(session.character.id, destination)
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] == expected_step:
        session.database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, next_step)
    _refresh(session)
    if room_key == UNDERCLOCK_TEETH_KEY:
        await session.send(
            "The clutch releases. The gear does not stop being enormous; it simply stops. One tooth aligns with the next like stepping stones over a black shaft. You walk across the top of the machine while it is briefly pretending to be architecture.\r\n"
        )
    else:
        await session.send(f"You commit during the {safe_phase.upper()} beat and cross {label} while the machinery is in its safe geometry.\r\n")
    await session.show_current_room()
    return True


async def _set_control(session, control: str) -> bool:
    if session.character is None or session.character.current_room != UNDERCLOCK_GOVERNOR_KEY:
        return False
    _ensure_quest(session)
    requirements = {
        "intake": ("intake", INTAKE_SET_FLAG, "You pin the intake valve exactly while the mains are already drawing. The feed stops wandering."),
        "flywheel": ("reset", FLYWHEEL_LOCKED_FLAG, "The flywheel reaches home and the heavy pawl drops into its maintenance notch with a sound like a door closing on a storm."),
        "bleed": ("vent", GOVERNOR_BLED_FLAG, "You open the governor bleed during VENT. Stored pressure empties into the condenser instead of fighting your hands."),
    }
    needed_phase, flag, success = requirements[control]
    if flag in _flags(session):
        await session.send("That Underclock control is already set for this repair.\r\n")
        return True
    state = clock_state()
    if state.phase != needed_phase:
        _movement_penalty(session, 4)
        await session.send(f"The control fights you because the machine is in {state.phase.upper()}. You let go before forcing it. Movement -4. Set this control during {needed_phase.upper()}.\r\n")
        return True
    session.database.grant_flag(session.character.id, flag)
    await session.send(success + "\r\n")
    flags = _flags(session)
    if {INTAKE_SET_FLAG, FLYWHEEL_LOCKED_FLAG, GOVERNOR_BLED_FLAG}.issubset(flags):
        q = _quest(session)
        if q and q["status"] == "active" and q["current_step"] == "calibrate_governor":
            session.database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "engage_governor")
        await session.send("All three controls are now pinned to known states. The Cinder Governor has nowhere left to hide excess pressure. ENGAGE GOVERNOR when ready.\r\n")
    return True


def _begin_forced_combat(session, enemy_definition: EnemyDefinition) -> bool:
    if session.character is None or session.combatant is None or session.active_enemy is not None:
        return False
    enemy = EnemyState(enemy_definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


async def _engage_governor(session) -> bool:
    if session.character is None or session.character.current_room != UNDERCLOCK_GOVERNOR_KEY:
        return False
    _ensure_quest(session)
    flags = _flags(session)
    needed = {INTAKE_SET_FLAG, FLYWHEEL_LOCKED_FLAG, GOVERNOR_BLED_FLAG}
    if not needed.issubset(flags):
        missing = ", ".join(sorted(flag.replace("underclock_", "").replace("_", " ") for flag in needed - flags))
        await session.send(f"The Governor is still protected by live pressure. Missing control states: {missing}.\r\n")
        return True
    if GOVERNOR_DEFEATED_FLAG in flags:
        await session.send("The Cinder Governor is already down; the Minute Chamber to the east is open.\r\n")
        return True
    if session.active_enemy is not None:
        await session.send("You are already in combat.\r\n")
        return True
    session.database.grant_flag(session.character.id, GOVERNOR_ENGAGED_FLAG)
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] == "engage_governor":
        session.database.advance_quest(session.character.id, UNDERCLOCK_QUEST_KEY, "defeat_governor")
    if not _begin_forced_combat(session, CINDER_GOVERNOR):
        await session.send("The Governor is exposed, but your combat state is not ready to engage it yet.\r\n")
        return True
    await session.send(
        "You throw the engagement lever. The intake stays pinned, the flywheel cannot surge, and the bleed steals the Governor's reserve pressure. Its four legs unlock from the rail anyway. The fight begins—but now it is a machine with limits instead of the whole room trying to kill you.\r\n"
    )
    return True


async def _start_lift(session) -> bool:
    if session.character is None or session.character.current_room != UNDERCLOCK_MINUTE_KEY:
        return False
    if GOVERNOR_DEFEATED_FLAG not in _flags(session):
        await session.send("The start lever is mechanically blocked while the Cinder Governor remains active.\r\n")
        return True
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] == "restart_lift":
        session.database.complete_quest(session.character.id, UNDERCLOCK_QUEST_KEY)
        session.database.grant_flag(session.character.id, UNDERCLOCK_COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 360)
        _refresh(session)
        await session.send(
            "You pull the lift start. Intake, pressure, vent, reset: the four beats settle into the same interval. Far above, water begins climbing toward Veyra's upper basins again. Nothing glows. No prophecy speaks. Somewhere in the city, a tap that would have run dry tomorrow simply keeps working. The City Between Ticks complete: 360 XP.\r\n"
        )
        return True
    await session.send("The lift is already running on a stable four-beat cycle.\r\n")
    return True


def install_underclock_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_underclock_runtime_installed", False):
        return
    install_underclock_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        _ensure_quest(self)

    async def move_character(self, direction: str) -> None:
        # The boss chamber's east door is physically ordinary, but the live governor rail crosses it until defeated.
        if (
            self.character is not None
            and self.character.current_room == UNDERCLOCK_GOVERNOR_KEY
            and direction.strip().lower() in {"east", "e"}
            and GOVERNOR_DEFEATED_FLAG not in _flags(self)
        ):
            await self.send("The live Governor rail crosses the east service door. Calibrate and defeat the Cinder Governor before entering the Minute Chamber.\r\n")
            return
        await previous_move(self, direction)
        _ensure_quest(self)

    def enemy_in_room(self, target_text: str):
        if (
            self.character is not None
            and self.character.current_room == UNDERCLOCK_GOVERNOR_KEY
            and GOVERNOR_ENGAGED_FLAG in _flags(self)
            and GOVERNOR_DEFEATED_FLAG not in _flags(self)
            and CINDER_GOVERNOR.matches(target_text)
        ):
            return EnemyState(CINDER_GOVERNOR)
        return previous_enemy_lookup(self, target_text)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active or self.character is None or key != GOVERNOR_KEY:
            return
        if GOVERNOR_DEFEATED_FLAG in _flags(self):
            return
        self.database.grant_flag(self.character.id, GOVERNOR_DEFEATED_FLAG)
        self.database.add_item(self.character.id, GOVERNOR_BEARING_KEY, 1)
        q = _quest(self)
        if q and q["status"] == "active" and q["current_step"] == "defeat_governor":
            self.database.advance_quest(self.character.id, UNDERCLOCK_QUEST_KEY, "restart_lift")
        await self.send("The Cinder Governor settles against its rail, flyballs slowing until individual brass arms become visible. You recover one intact Governor Bearing. The east service door to the Minute Chamber is clear.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        handled = False

        if normalized in {"clock", "cycle", "underclock", "read cycle"}:
            handled = await _show_clock(self)
        elif normalized in {"examine master gauge", "examine gauge", "read gauge", "look gauge"}:
            handled = await _read_gauge(self)
        elif normalized in {"cross pistons", "cross piston gallery"}:
            handled = await _timed_cross(
                self, room_key=UNDERCLOCK_PISTON_KEY, safe_phase="reset", destination=UNDERCLOCK_FLYWHEEL_KEY,
                flag=PISTONS_CROSSED_FLAG, expected_step="cross_pistons", next_step="cross_steam", label="the Piston Gallery",
            )
        elif normalized in {"cross steam", "cross steam throat"}:
            handled = await _timed_cross(
                self, room_key=UNDERCLOCK_STEAM_KEY, safe_phase="intake", destination=UNDERCLOCK_CONDENSER_KEY,
                flag=STEAM_CROSSED_FLAG, expected_step="cross_steam", next_step="cross_teeth", label="the Steam Throat",
            )
        elif normalized in {"cross teeth", "cross walking teeth", "walk teeth"}:
            handled = await _timed_cross(
                self, room_key=UNDERCLOCK_TEETH_KEY, safe_phase="vent", destination=UNDERCLOCK_GOVERNOR_KEY,
                flag=TEETH_CROSSED_FLAG, expected_step="cross_teeth", next_step="calibrate_governor", label="the Walking Teeth",
            )
        elif normalized in {"set intake", "set intake valve", "turn intake valve"}:
            handled = await _set_control(self, "intake")
        elif normalized in {"lock flywheel", "set flywheel lock"}:
            handled = await _set_control(self, "flywheel")
        elif normalized in {"bleed governor", "open governor bleed", "bleed pressure"}:
            handled = await _set_control(self, "bleed")
        elif normalized in {"engage governor", "start governor fight"}:
            handled = await _engage_governor(self)
        elif normalized in {"start lift", "restart lift", "pull start lever"}:
            handled = await _start_lift(self)

        if handled:
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str):
            return command

        self.prompt = replay_prompt
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = enemy_in_room
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._underclock_runtime_installed = True
