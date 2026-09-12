from __future__ import annotations

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.greywake_march import GREYWAKE_WEST_MILE_KEY
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.waymeet_frontier import WAYMEET_SCRIP_KEY
from mud.world import NpcDefinition, RoomDefinition


BLACKREED_REGION_KEY = "blackreed_holdfast"
BLACKREED_TRAILHEAD_KEY = "blackreed_trailhead"
BLACKREED_CAUSEWAY_KEY = "blackreed_collapsed_causeway"
BLACKREED_OUTER_GATE_KEY = "blackreed_outer_gate"
BLACKREED_LOWER_YARD_KEY = "blackreed_lower_yard"
BLACKREED_KENNELS_KEY = "blackreed_kennels"
BLACKREED_BARRACKS_KEY = "blackreed_barracks"
BLACKREED_SIGNAL_YARD_KEY = "blackreed_signal_yard"
BLACKREED_INNER_KEEP_KEY = "blackreed_inner_keep"
BLACKREED_STORES_KEY = "blackreed_stores"
BLACKREED_ARROW_GALLERY_KEY = "blackreed_arrow_gallery"
BLACKREED_CAPTAIN_HALL_KEY = "blackreed_captains_hall"
BLACKREED_PARAPET_KEY = "blackreed_river_parapet"

BLACKREED_ROOM_KEYS = (
    BLACKREED_TRAILHEAD_KEY,
    BLACKREED_CAUSEWAY_KEY,
    BLACKREED_OUTER_GATE_KEY,
    BLACKREED_LOWER_YARD_KEY,
    BLACKREED_KENNELS_KEY,
    BLACKREED_BARRACKS_KEY,
    BLACKREED_SIGNAL_YARD_KEY,
    BLACKREED_INNER_KEEP_KEY,
    BLACKREED_STORES_KEY,
    BLACKREED_ARROW_GALLERY_KEY,
    BLACKREED_CAPTAIN_HALL_KEY,
    BLACKREED_PARAPET_KEY,
)

BLACKREED_QUEST_KEY = "blackreed_black_flag_on_the_mile"
BLACKREED_COMPLETE_FLAG = "blackreed_first_clear_complete"
BLACKREED_RUNNER_DEFEATED_FLAG = "blackreed_signal_runner_defeated"
BLACKREED_YARDMASTER_DEFEATED_FLAG = "blackreed_yardmaster_defeated"
BLACKREED_CHIEF_DEFEATED_FLAG = "blackreed_captain_defeated"

BLACKREED_FITTING_KEY = "blackreed_iron_fitting"
BLACKREED_ROUTE_TOKEN_KEY = "blackreed_route_token"

SCOUT_KEY = "blackreed_roadwarden_scout"
KNIFEHAND_KEY = "blackreed_knifehand"
BOWHAND_KEY = "blackreed_bowhand"
SHIELDMAN_KEY = "blackreed_shieldman"
BRUISER_KEY = "blackreed_bruiser"
HOUND_KEY = "blackreed_gang_hound"
SIGNAL_RUNNER_KEY = "blackreed_signal_runner"
YARDMASTER_KEY = "blackreed_yardmaster"
REINFORCED_YARDMASTER_KEY = "blackreed_yardmaster_reinforced"
CHIEF_SHIELDED_KEY = "blackreed_captain_shielded"
CHIEF_EXPOSED_KEY = "blackreed_captain_exposed"


BLACKREED_QUEST = QuestDefinition(
    key=BLACKREED_QUEST_KEY,
    name="The Black Flag on the Mile",
    style="structured",
    minimum_level=5,
    description=(
        "A gang calling itself the Black Reed Company has occupied an abandoned road fort south of Greywake West Mile. "
        "Roadwarden Scout Brenn Kest wants the route reopened before extortion becomes a permanent border."
    ),
    objective_steps=(
        ("talk_scout", "TALK SCOUT at the Blackreed Trailhead."),
        ("enter_hold", "Cross the collapsed causeway and enter the occupied holdfast."),
        ("break_signal_yard", "Clear the Signal Runner and Yardmaster Kelm. Focusing the runner first prevents reinforcements."),
        ("defeat_chief", "Reach the Captain's Hall and defeat Captain Vara Skell."),
        ("raise_lantern", "Reach the River Parapet and RAISE ROAD LANTERN."),
        ("complete", "The old road fort is back in public hands, at least until the next patrol cycle."),
    ),
)

BLACKREED_FITTING = ItemDefinition(
    key=BLACKREED_FITTING_KEY,
    name="Blackreed Iron Fitting",
    description=(
        "A heavy iron hinge, strap, or shield fitting stripped from the Black Reed Company's repaired fortifications. "
        "The metal is mundane, thick, and useful to practical smiths."
    ),
    category="material",
    tier=2,
)
BLACKREED_ROUTE_TOKEN = ItemDefinition(
    key=BLACKREED_ROUTE_TOKEN_KEY,
    name="Blackreed Route Token",
    description=(
        "A punched brass road token issued after the first confirmed clearing of Blackreed Holdfast. "
        "It proves you helped reopen the Greywake side road rather than merely passing through it."
    ),
    category="trophy",
    tier=2,
)
BLACKREED_ITEMS = (BLACKREED_FITTING, BLACKREED_ROUTE_TOKEN)


KNIFEHAND = EnemyDefinition(
    key=KNIFEHAND_KEY,
    name="Blackreed Knifehand",
    aliases=("knifehand", "bandit", "blackreed", "blackreed knifehand"),
    description="a road bandit in patched mail carrying a short blade meant for wagon crews who look easier than the cargo",
    max_hp=72,
    armor_class=8,
    auto_attack_damage=7,
    auto_attack_interval=2.8,
    xp_reward=48,
)
BOWHAND = EnemyDefinition(
    key=BOWHAND_KEY,
    name="Blackreed Bowhand",
    aliases=("bowhand", "archer", "bandit archer", "blackreed bowhand"),
    description="a bandit archer using the old fort's firing lanes exactly as the original garrison intended",
    max_hp=68,
    armor_class=9,
    auto_attack_damage=7,
    auto_attack_interval=2.7,
    xp_reward=50,
)
SHIELDMAN = EnemyDefinition(
    key=SHIELDMAN_KEY,
    name="Blackreed Shieldman",
    aliases=("shieldman", "shield guard", "bandit guard", "blackreed shieldman"),
    description="a broad-shouldered bandit carrying a scavenged road shield and enough armor to make a narrow doorway annoying",
    max_hp=88,
    armor_class=12,
    auto_attack_damage=8,
    auto_attack_interval=3.1,
    xp_reward=60,
)
BRUISER = EnemyDefinition(
    key=BRUISER_KEY,
    name="Blackreed Bruiser",
    aliases=("bruiser", "enforcer", "bandit bruiser", "blackreed bruiser"),
    description="a club-armed enforcer whose job appears to begin after negotiation has already failed",
    max_hp=102,
    armor_class=9,
    auto_attack_damage=9,
    auto_attack_interval=3.0,
    xp_reward=66,
)
GANG_HOUND = EnemyDefinition(
    key=HOUND_KEY,
    name="Blackreed Hound",
    aliases=("hound", "dog", "gang hound", "blackreed hound"),
    description="a lean fort dog trained to pin travelers against walls until somebody with a knife catches up",
    max_hp=58,
    armor_class=6,
    auto_attack_damage=6,
    auto_attack_interval=2.6,
    xp_reward=40,
)
SIGNAL_RUNNER = EnemyDefinition(
    key=SIGNAL_RUNNER_KEY,
    name="Blackreed Signal Runner",
    aliases=("runner", "signal runner", "horn runner", "blackreed runner"),
    description="a lightly armored runner with a brass alarm horn already hanging from one hand",
    max_hp=54,
    armor_class=6,
    auto_attack_damage=5,
    auto_attack_interval=2.6,
    xp_reward=38,
)
YARDMASTER = EnemyDefinition(
    key=YARDMASTER_KEY,
    name="Yardmaster Kelm",
    aliases=("yardmaster", "kelm", "yardmaster kelm"),
    description="the gang officer responsible for the fort's lower yard, wearing a stolen garrison coat over practical armor",
    max_hp=156,
    armor_class=11,
    auto_attack_damage=10,
    auto_attack_interval=3.0,
    xp_reward=112,
)
REINFORCED_YARDMASTER = EnemyDefinition(
    key=REINFORCED_YARDMASTER_KEY,
    name="Yardmaster Kelm",
    aliases=("yardmaster", "kelm", "yardmaster kelm"),
    description="Kelm fights from the center of a yard that has had time to answer the runner's alarm",
    max_hp=212,
    armor_class=13,
    auto_attack_damage=12,
    auto_attack_interval=2.8,
    xp_reward=142,
)
CAPTAIN_SKELL_SHIELDED = EnemyDefinition(
    key=CHIEF_SHIELDED_KEY,
    name="Captain Vara Skell",
    aliases=("captain", "vara", "skell", "vara skell", "captain skell"),
    description="the Black Reed captain behind an iron-rimmed tower shield, fighting like someone who has survived several better-equipped opponents",
    max_hp=258,
    armor_class=16,
    auto_attack_damage=14,
    auto_attack_interval=2.9,
    xp_reward=195,
)
CAPTAIN_SKELL_EXPOSED = EnemyDefinition(
    key=CHIEF_EXPOSED_KEY,
    name="Captain Vara Skell",
    aliases=CAPTAIN_SKELL_SHIELDED.aliases,
    description="Vara Skell with her shield line broken and her weapon side exposed to the room",
    max_hp=258,
    armor_class=11,
    auto_attack_damage=14,
    auto_attack_interval=2.9,
    xp_reward=195,
)
BLACKREED_ENEMIES = (
    KNIFEHAND,
    BOWHAND,
    SHIELDMAN,
    BRUISER,
    GANG_HOUND,
    SIGNAL_RUNNER,
    YARDMASTER,
    REINFORCED_YARDMASTER,
    CAPTAIN_SKELL_SHIELDED,
    CAPTAIN_SKELL_EXPOSED,
)


SCOUT = NpcDefinition(
    key=SCOUT_KEY,
    name="Scout Brenn Kest",
    short_description="a Roadwarden scout studying a charcoal sketch of the occupied fort and its firing lanes",
    room_key=BLACKREED_TRAILHEAD_KEY,
    role="Blackreed dungeon guide",
    dialogue=(
        "'Nothing supernatural in there. Doors, dogs, arrows, bad people, and one very good shield.'",
        "'When you reach the signal yard, kill the runner first. If that horn sounds, Kelm gets the whole yard instead of the clean fight.'",
        "'Skell's shield faces whoever she hates most. Somebody else gets around the side. That is the whole trick.'",
    ),
)


def _room(
    key: str,
    name: str,
    description: str,
    exits: dict[str, str],
    *,
    npcs: tuple[str, ...] = (),
    enemies: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=BLACKREED_REGION_KEY,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "dungeon", "blackreed", "level_5_7", *tags),
    )


BLACKREED_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        BLACKREED_TRAILHEAD_KEY,
        "Blackreed Trailhead",
        "A neglected side road leaves Greywake's main mile and drops toward an old river bluff. A Roadwarden field camp has been reduced to one scout, two lanterns, and a very direct map of the fort below.",
        {"north": GREYWAKE_WEST_MILE_KEY, "east": BLACKREED_CAUSEWAY_KEY},
        npcs=(SCOUT_KEY,),
        tags=("safe", "dungeon_approach"),
    ),
    _room(
        BLACKREED_CAUSEWAY_KEY,
        "Collapsed Causeway",
        "Half the old stone causeway has slumped into a reed-filled drainage cut. The surviving lane is narrow enough that one lookout can make every approaching traveler obvious.",
        {"west": BLACKREED_TRAILHEAD_KEY, "east": BLACKREED_OUTER_GATE_KEY},
        enemies=(KNIFEHAND_KEY,),
        tags=("entry",),
    ),
    _room(
        BLACKREED_OUTER_GATE_KEY,
        "Outer Gate",
        "The fort's original doors are gone. The Black Reed Company replaced them with wagon planks, stolen bridge spikes, and a gap just wide enough to funnel visitors past a shield position.",
        {"west": BLACKREED_CAUSEWAY_KEY, "east": BLACKREED_LOWER_YARD_KEY},
        enemies=(SHIELDMAN_KEY,),
    ),
    _room(
        BLACKREED_LOWER_YARD_KEY,
        "Lower Yard",
        "Rain barrels, cookfires, practice posts, and confiscated wagon parts crowd the old parade ground. Paths split toward kennels and barracks before converging on the signal yard deeper in the holdfast.",
        {"west": BLACKREED_OUTER_GATE_KEY, "north": BLACKREED_BARRACKS_KEY, "south": BLACKREED_KENNELS_KEY, "east": BLACKREED_SIGNAL_YARD_KEY},
        enemies=(KNIFEHAND_KEY,),
        tags=("pull_room",),
    ),
    _room(
        BLACKREED_KENNELS_KEY,
        "Kennel Run",
        "Old cavalry stalls have been partitioned into dog runs with rope, doors, and whatever boards the gang did not need for the outer gate.",
        {"north": BLACKREED_LOWER_YARD_KEY},
        enemies=(HOUND_KEY,),
        tags=("side_room",),
    ),
    _room(
        BLACKREED_BARRACKS_KEY,
        "Occupied Barracks",
        "Rows of garrison bunks have become gang sleeping platforms. Wet boots hang from rafters, stolen road cloaks mark claimed beds, and a bruiser keeps the aisle clear by standing in it.",
        {"south": BLACKREED_LOWER_YARD_KEY},
        enemies=(BRUISER_KEY,),
        tags=("side_room",),
    ),
    _room(
        BLACKREED_SIGNAL_YARD_KEY,
        "Signal Yard",
        "A brass alarm horn hangs beside the old fort bell. Yardmaster Kelm controls the stair beyond while a lightly armored runner keeps one hand close to the horn. This is the obvious priority target the room is asking you to notice.",
        {"west": BLACKREED_LOWER_YARD_KEY},
        tags=("miniboss", "focus_fire_lesson"),
    ),
    _room(
        BLACKREED_INNER_KEEP_KEY,
        "Inner Keep",
        "The surviving stone core is narrower and better maintained than the outer fort. Loot crates line one wall while arrow slits cover the only route toward the captain's floor.",
        {"west": BLACKREED_SIGNAL_YARD_KEY, "north": BLACKREED_STORES_KEY, "east": BLACKREED_ARROW_GALLERY_KEY},
        enemies=(SHIELDMAN_KEY,),
    ),
    _room(
        BLACKREED_STORES_KEY,
        "Stolen Stores",
        "Crates are sorted by usefulness instead of ownership: lamp oil, dried grain, spare rope, axle grease, nails, and several merchant marks from wagons that clearly did not donate them.",
        {"south": BLACKREED_INNER_KEEP_KEY},
        enemies=(BRUISER_KEY,),
        tags=("side_room",),
    ),
    _room(
        BLACKREED_ARROW_GALLERY_KEY,
        "Arrow Gallery",
        "A long upper corridor overlooks the lower approach through narrow firing slits. The bandits have stacked spare arrows in clay jars exactly where a real garrison once would have.",
        {"west": BLACKREED_INNER_KEEP_KEY, "east": BLACKREED_CAPTAIN_HALL_KEY},
        enemies=(BOWHAND_KEY,),
        tags=("ranged_lane",),
    ),
    _room(
        BLACKREED_CAPTAIN_HALL_KEY,
        "Captain's Hall",
        "An old briefing room has been stripped to a trestle table, a road map, and Captain Vara Skell's iron-rimmed shield. The shield is excellent from the front and much less impressive if somebody else is keeping her attention.",
        {"west": BLACKREED_ARROW_GALLERY_KEY},
        tags=("boss", "flank_lesson"),
    ),
    _room(
        BLACKREED_PARAPET_KEY,
        "River Parapet",
        "The fort's highest surviving wall overlooks the side road, reed flats, and the distant Greywake mile. A black gang pennant hangs above an older public road lantern whose shutters still face the route.",
        {"west": BLACKREED_CAPTAIN_HALL_KEY},
        tags=("dungeon_end", "safe_after_clear"),
    ),
)


RUN_FLAGS = (
    BLACKREED_RUNNER_DEFEATED_FLAG,
    BLACKREED_YARDMASTER_DEFEATED_FLAG,
    BLACKREED_CHIEF_DEFEATED_FLAG,
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


def blackreed_augmentations() -> dict[str, RoomAugmentation]:
    return {
        GREYWAKE_WEST_MILE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=BLACKREED_TRAILHEAD_KEY,
                    name="Blackreed Side Road",
                    travel_text="You leave the main Greywake mile and follow an old garrison spur down toward the river bluff.",
                    condition=ViewCondition(min_level=5),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        BLACKREED_TRAILHEAD_KEY: RoomAugmentation(
            features=(
                _feature(
                    "blackreed_scout_map",
                    "Scout's Fort Sketch",
                    "a charcoal map labeling gate, yard, signal horn, captain, and river parapet",
                    "Brenn has deliberately left the map simple. SIGNAL YARD is underlined twice with RUNNER FIRST. CAPTAIN is annotated: shield faces top threat; second fighter FLANKS.",
                    ("map", "sketch", "fort sketch"),
                ),
            ),
        ),
        BLACKREED_SIGNAL_YARD_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=BLACKREED_INNER_KEEP_KEY,
                    name="Inner Keep Stair",
                    travel_text="With Kelm and the signal runner down, you climb the stone stair into the inner keep.",
                    condition=ViewCondition(required_flags=(BLACKREED_RUNNER_DEFEATED_FLAG, BLACKREED_YARDMASTER_DEFEATED_FLAG)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "blackreed_alarm_horn",
                    "Alarm Horn",
                    "a brass alarm horn within a few running steps of the signal runner",
                    "The lesson is not subtle: if the runner stays upright, Kelm gets time to pull more bodies into the yard. ATTACK RUNNER and have party members ASSIST the same target before taking Kelm.",
                    ("horn", "alarm horn", "signal horn", "runner"),
                ),
            ),
        ),
        BLACKREED_CAPTAIN_HALL_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=BLACKREED_PARAPET_KEY,
                    name="River Parapet",
                    travel_text="With Captain Skell down, you pass through the command door onto the river parapet.",
                    condition=ViewCondition(required_flags=(BLACKREED_CHIEF_DEFEATED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "blackreed_tower_shield",
                    "Iron-Rimmed Tower Shield",
                    "Captain Skell's broad shield covering most of her front",
                    "Skell uses the shield against whoever currently owns her attention. In a shared fight, one character can hold top threat while another uses FLANK CAPTAIN to get around the shield. Solo players can still fight her head-on, just less efficiently.",
                    ("shield", "tower shield", "captain shield"),
                ),
            ),
        ),
        BLACKREED_PARAPET_KEY: RoomAugmentation(
            features=(
                _feature(
                    "blackreed_road_lantern",
                    "Road Lantern",
                    "an old public route lantern hidden behind the gang's black pennant",
                    "The lamp is dry enough to use. RAISE ROAD LANTERN after defeating Skell to mark the side road open and claim a personal first-clear record.",
                    ("lantern", "road lantern", "lamp", "black flag", "pennant"),
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


def install_blackreed_content(world_service=None) -> None:
    if BLACKREED_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (BLACKREED_QUEST,)
    quests.QUESTS_BY_KEY[BLACKREED_QUEST.key] = BLACKREED_QUEST

    for item in BLACKREED_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in BLACKREED_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    _replace_npc(SCOUT)
    for room in BLACKREED_ROOMS:
        _replace_room(room)

    economy.LOOT_TABLES[YARDMASTER_KEY] = (economy.LootDrop(BLACKREED_FITTING_KEY, 1),)
    economy.LOOT_TABLES[REINFORCED_YARDMASTER_KEY] = (economy.LootDrop(BLACKREED_FITTING_KEY, 1),)
    economy.LOOT_TABLES[CHIEF_SHIELDED_KEY] = (economy.LootDrop(BLACKREED_FITTING_KEY, 2),)
    economy.LOOT_TABLES[CHIEF_EXPOSED_KEY] = (economy.LootDrop(BLACKREED_FITTING_KEY, 2),)

    if world_service is None:
        return
    for room in BLACKREED_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in blackreed_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*BLACKREED_ROOM_KEYS, GREYWAKE_WEST_MILE_KEY):
            cache.pop(key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, BLACKREED_QUEST_KEY)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _ensure_quest(session) -> bool:
    if session.character is None:
        return False
    if session.character.current_room not in BLACKREED_ROOM_KEYS or session.character.level < 5:
        return False
    if BLACKREED_COMPLETE_FLAG in _flags(session):
        return True
    if _quest(session) is None:
        session.database.start_quest(session.character.id, BLACKREED_QUEST_KEY, "talk_scout")
    return True


def signal_yard_clear(flags: set[str] | frozenset[str]) -> bool:
    return {BLACKREED_RUNNER_DEFEATED_FLAG, BLACKREED_YARDMASTER_DEFEATED_FLAG}.issubset(flags)


def yardmaster_definition_for_flags(flags: set[str] | frozenset[str]) -> EnemyDefinition:
    return YARDMASTER if BLACKREED_RUNNER_DEFEATED_FLAG in flags else REINFORCED_YARDMASTER


def _victory_sessions(session, enemy) -> list:
    finder = getattr(session, "party_victory_sessions", None)
    if callable(finder):
        result = finder(enemy)
        if result:
            return list(result)
    return [session]


def _room_party_sessions(session) -> list:
    finder = getattr(session, "party_sessions_here", None)
    if callable(finder):
        result = finder()
        if result:
            return list(result)
    return [session]


def _grant_flag(session, flag: str) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    if flag in flags:
        return False
    session.database.grant_flag(session.character.id, flag)
    return True


def _maybe_advance_signal_quest(session) -> bool:
    if session.character is None or not signal_yard_clear(_flags(session)):
        return False
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == "break_signal_yard":
        session.database.advance_quest(session.character.id, BLACKREED_QUEST_KEY, "defeat_chief")
        return True
    return False


async def _talk_scout(session) -> bool:
    if session.character is None or session.character.current_room != BLACKREED_TRAILHEAD_KEY:
        return False
    _ensure_quest(session)
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == "talk_scout":
        session.database.advance_quest(session.character.id, BLACKREED_QUEST_KEY, "enter_hold")
        await session.send(
            "Brenn taps the signal yard on his sketch. 'This is a short fort, not a mystery. Clear your rooms. When you see the horn runner, everybody piles onto him first. If he stays up, Kelm gets reinforcements. Skell at the top has a tower shield: whoever she hates most keeps her front while somebody else FLANKS. Bring the public road lantern back when you're done.'\r\n"
        )
        return True
    if BLACKREED_COMPLETE_FLAG in _flags(session):
        await session.send(
            "Brenn says, 'You've already opened it once. TAKE BLACKREED PATROL if your group wants a fresh clear. Same fort, fresh occupation.'\r\n"
        )
        return True
    await session.send("Brenn says, 'Keep moving. The fort is short enough that hesitation helps them more than it helps you.'\r\n")
    return True


def _reset_run_flags(session) -> None:
    if session.character is None:
        return
    for flag in RUN_FLAGS:
        session.database.revoke_flag(session.character.id, flag)


async def _take_repeat_patrol(session) -> bool:
    if session.character is None or session.character.current_room != BLACKREED_TRAILHEAD_KEY:
        return False
    if session.active_enemy is not None:
        await session.send("Finish your current fight before taking a fresh patrol slate.\r\n")
        return True
    members = _room_party_sessions(session)
    reset_names: list[str] = []
    for member in members:
        character = getattr(member, "character", None)
        if character is None:
            continue
        flags = set(member.database.list_flags(character.id))
        if BLACKREED_COMPLETE_FLAG not in flags:
            continue
        _reset_run_flags(member)
        reset_names.append(character.name)
        if member is not session:
            await member.send("[Party Progress] Brenn adds your name to the fresh Blackreed patrol slate. Run-state encounters reset; first-clear rewards stay recorded.\r\n")
    if not reset_names:
        await session.send("Complete The Black Flag on the Mile once before taking repeat Blackreed patrols.\r\n")
        return True
    await session.send(
        "Brenn tears yesterday's date from the slate. 'Fresh clear. Runner first, Kelm second, Skell last.' "
        f"Patrol reset for: {', '.join(reset_names)}. First-clear completion and rewards remain permanent.\r\n"
    )
    return True


async def _raise_road_lantern(session) -> bool:
    if session.character is None or session.character.current_room != BLACKREED_PARAPET_KEY:
        return False
    if BLACKREED_CHIEF_DEFEATED_FLAG not in _flags(session):
        await session.send("Captain Skell still controls the holdfast. Raising the public road lantern now would be a lie.\r\n")
        return True
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == "raise_lantern":
        session.database.complete_quest(session.character.id, BLACKREED_QUEST_KEY)
        session.database.grant_flag(session.character.id, BLACKREED_COMPLETE_FLAG)
        session.database.add_item(session.character.id, BLACKREED_ROUTE_TOKEN_KEY, 1)
        session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 2)
        session.database.add_experience(session.character.id, 240)
        _refresh(session)
        await session.send(
            "You drag down the Black Reed pennant, trim the old route lamp, and raise its shutter toward Greywake. The light is deliberately boring: one public road is open again. The Black Flag on the Mile complete: 240 XP, 2 Waymeet Trade Scrip, and a Blackreed Route Token.\r\n"
        )
        return True
    if BLACKREED_COMPLETE_FLAG in _flags(session):
        await session.send("The road lantern already carries the record of your first clear. Brenn can issue repeat patrols from the trailhead.\r\n")
        return True
    await session.send("You have not yet reached the first-clear lantern objective.\r\n")
    return True


async def _flank_captain(session) -> bool:
    if session.character is None or session.character.current_room != BLACKREED_CAPTAIN_HALL_KEY:
        return False
    enemy = getattr(session, "active_enemy", None)
    if enemy is None or enemy.definition.key not in {CHIEF_SHIELDED_KEY, CHIEF_EXPOSED_KEY}:
        await session.send("Captain Skell must be actively fighting before anybody can work around her shield.\r\n")
        return True
    if enemy.definition.key == CHIEF_EXPOSED_KEY:
        await session.send("Skell's shield line is already broken for this fight. Keep the pressure on.\r\n")
        return True

    participants = _victory_sessions(session, enemy)
    unique_ids = {
        int(member.character.id)
        for member in participants
        if getattr(member, "character", None) is not None
    }
    if len(unique_ids) < 2:
        await session.send("You need another participating party member to hold Skell's attention before you can get around the shield.\r\n")
        return True

    top_target = enemy.hate.top_target()
    if top_target is None or int(top_target) == int(session.character.id):
        await session.send("Skell is watching you. Keep her attention or let another party member take top threat so somebody else can FLANK CAPTAIN.\r\n")
        return True

    enemy.definition = CAPTAIN_SKELL_EXPOSED
    for member in participants:
        if member is session:
            continue
        await member.send(
            f"[Party Combat] {session.character.name} gets around Skell's shield side. Her defensive line is broken for the rest of the fight.\r\n"
        )
    await session.send(
        "You move while Skell is committed to somebody else, get past the tower shield, and force her to turn with no wall at her back. Her defensive line is broken for the rest of the fight.\r\n"
    )
    return True


async def _status(session) -> bool:
    if session.character is None or session.character.current_room not in BLACKREED_ROOM_KEYS:
        return False
    flags = _flags(session)
    q = _quest(session)
    step = q.get("current_step") if q and q.get("status") == "active" else "first clear complete" if BLACKREED_COMPLETE_FLAG in flags else "not started"
    await session.send(
        "BLACKREED STATUS\r\n"
        f" - First-clear objective: {step}.\r\n"
        f" - Signal runner: {'down' if BLACKREED_RUNNER_DEFEATED_FLAG in flags else 'active'}.\r\n"
        f" - Yardmaster Kelm: {'down' if BLACKREED_YARDMASTER_DEFEATED_FLAG in flags else 'active'}.\r\n"
        f" - Captain Vara Skell: {'down' if BLACKREED_CHIEF_DEFEATED_FLAG in flags else 'active'}.\r\n"
        " - Party lesson: ASSIST onto the runner first; at Skell, one character holds top threat while another uses FLANK CAPTAIN.\r\n"
    )
    return True


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_blackreed_runtime(player_session_class, world_service) -> None:
    """Install the quick level 5-7 traditional bandit dungeon and party-aware progression."""
    if getattr(player_session_class, "_blackreed_runtime_installed", False):
        return
    install_blackreed_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        _ensure_quest(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        _ensure_quest(self)
        if self.character is None or self.character.current_room == before:
            return
        if self.character.current_room == BLACKREED_OUTER_GATE_KEY:
            q = _quest(self)
            if q and q.get("status") == "active" and q.get("current_step") == "enter_hold":
                self.database.advance_quest(self.character.id, BLACKREED_QUEST_KEY, "break_signal_yard")
                await self.send(
                    "The improvised gate closes the easy retreat behind you. The fort is small: clear the lower rooms, then deal with the signal yard. Runner first keeps Kelm clean.\r\n"
                )

    def enemy_in_room(self, target_text: str):
        if self.character is not None:
            room = self.character.current_room
            flags = _flags(self)
            if room == BLACKREED_SIGNAL_YARD_KEY:
                if BLACKREED_RUNNER_DEFEATED_FLAG not in flags and SIGNAL_RUNNER.matches(target_text):
                    return EnemyState(SIGNAL_RUNNER)
                if BLACKREED_YARDMASTER_DEFEATED_FLAG not in flags and YARDMASTER.matches(target_text):
                    return EnemyState(yardmaster_definition_for_flags(flags))
            if (
                room == BLACKREED_CAPTAIN_HALL_KEY
                and BLACKREED_CHIEF_DEFEATED_FLAG not in flags
                and CAPTAIN_SKELL_SHIELDED.matches(target_text)
            ):
                return EnemyState(CAPTAIN_SKELL_SHIELDED)
        return previous_enemy_lookup(self, target_text)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        participants = _victory_sessions(self, enemy)
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active:
            return

        if key == SIGNAL_RUNNER_KEY:
            for member in participants:
                if getattr(member, "character", None) is None:
                    continue
                changed = _grant_flag(member, BLACKREED_RUNNER_DEFEATED_FLAG)
                advanced = _maybe_advance_signal_quest(member)
                if member is not self and changed:
                    await member.send("[Party Progress] The Blackreed signal runner is down for your current patrol.\r\n")
                if advanced:
                    await member.send("[Party Progress] The signal yard is clear. Push into the inner keep and find Captain Skell.\r\n")
            await self.send("The runner drops before the horn can organize the yard. Kelm has to fight with whoever is already here.\r\n")
            return

        if key in {YARDMASTER_KEY, REINFORCED_YARDMASTER_KEY}:
            for member in participants:
                if getattr(member, "character", None) is None:
                    continue
                changed = _grant_flag(member, BLACKREED_YARDMASTER_DEFEATED_FLAG)
                advanced = _maybe_advance_signal_quest(member)
                if member is not self and changed:
                    await member.send("[Party Progress] Yardmaster Kelm is down for your current patrol.\r\n")
                if advanced:
                    await member.send("[Party Progress] The signal yard is clear. Push into the inner keep and find Captain Skell.\r\n")
            if key == REINFORCED_YARDMASTER_KEY:
                await self.send("Kelm finally drops after a much uglier yard fight. The runner was allowed to buy him exactly the advantage Brenn warned about.\r\n")
            else:
                await self.send("Kelm drops in an isolated yard. Killing the runner first turned a gang formation into one ordinary officer fight.\r\n")
            return

        if key in {CHIEF_SHIELDED_KEY, CHIEF_EXPOSED_KEY}:
            for member in participants:
                character = getattr(member, "character", None)
                if character is None:
                    continue
                changed = _grant_flag(member, BLACKREED_CHIEF_DEFEATED_FLAG)
                q = _quest(member)
                advanced = False
                if q and q.get("status") == "active" and q.get("current_step") == "defeat_chief":
                    member.database.advance_quest(character.id, BLACKREED_QUEST_KEY, "raise_lantern")
                    advanced = True
                if member is not self and changed:
                    await member.send("[Party Progress] Captain Vara Skell is down for your current Blackreed patrol.\r\n")
                if advanced:
                    await member.send("[Party Progress] Reach the River Parapet and RAISE ROAD LANTERN to claim your personal first-clear record.\r\n")
            await self.send("Vara Skell goes down beside the road map. The command door east opens onto the river parapet.\r\n")
            return

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        handled = False

        if normalized in {"talk scout", "talk brenn", "talk brenn kest", "speak scout"}:
            handled = await _talk_scout(self)
        elif normalized in {"blackreed status", "holdfast status", "dungeon status"}:
            handled = await _status(self)
        elif normalized in {"flank captain", "flank skell", "flank vara", "get behind captain"}:
            handled = await _flank_captain(self)
        elif normalized in {"raise road lantern", "raise lantern", "light road lantern", "lower black flag"}:
            handled = await _raise_road_lantern(self)
        elif normalized in {
            "take blackreed patrol",
            "take new blackreed patrol",
            "new blackreed run",
            "start blackreed run",
            "reset blackreed",
        }:
            handled = await _take_repeat_patrol(self)

        if handled:
            return
        await _delegate_command(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = enemy_in_room
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._blackreed_runtime_installed = True
