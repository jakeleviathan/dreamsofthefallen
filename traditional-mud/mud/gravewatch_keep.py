from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.stats import CharacterStats, EquipmentItem
from mud.veyra_city import VEYRA_EAST_RIVER_GATE_KEY, VEYRA_RESIDENT_FLAG
from mud.world import NpcDefinition, RoomDefinition


GRAVEWATCH_REGION_KEY = "gravewatch_keep"

# Two approach rooms make the keep feel like a place outside the capital rather
# than another door hidden inside Veyra.
GRAVEWATCH_RIVER_MILE_KEY = "gravewatch_river_mile"
GRAVEWATCH_FERRY_RUIN_KEY = "gravewatch_ferry_ruin"

# The keep itself is intentionally traditional: gatehouse -> yard -> barracks /
# kennels -> courtyard captain -> chapel -> crypts -> final commander.
GRAVEWATCH_BARBICAN_KEY = "gravewatch_broken_barbican"
GRAVEWATCH_GATEHOUSE_KEY = "gravewatch_gatehouse"
GRAVEWATCH_OUTER_YARD_KEY = "gravewatch_outer_yard"
GRAVEWATCH_KENNEL_KEY = "gravewatch_kennel_run"
GRAVEWATCH_BARRACKS_KEY = "gravewatch_barracks"
GRAVEWATCH_ARMORY_KEY = "gravewatch_armory"
GRAVEWATCH_RAMPART_KEY = "gravewatch_west_rampart"
GRAVEWATCH_COURTYARD_KEY = "gravewatch_courtyard_of_standards"
GRAVEWATCH_CHAPEL_KEY = "gravewatch_chapel_nave"
GRAVEWATCH_VESTRY_KEY = "gravewatch_bell_vestry"
GRAVEWATCH_OSSUARY_KEY = "gravewatch_ossuary_stair"
GRAVEWATCH_CRYPT_KEY = "gravewatch_crypt_hall"
GRAVEWATCH_TOMB_KEY = "gravewatch_officers_tomb"
GRAVEWATCH_PORTCULLIS_KEY = "gravewatch_inner_portcullis"
GRAVEWATCH_GREAT_HALL_KEY = "gravewatch_great_hall"
GRAVEWATCH_MAP_ROOM_KEY = "gravewatch_castellans_map_room"

GRAVEWATCH_KEEP_ROOM_KEYS = (
    GRAVEWATCH_BARBICAN_KEY,
    GRAVEWATCH_GATEHOUSE_KEY,
    GRAVEWATCH_OUTER_YARD_KEY,
    GRAVEWATCH_KENNEL_KEY,
    GRAVEWATCH_BARRACKS_KEY,
    GRAVEWATCH_ARMORY_KEY,
    GRAVEWATCH_RAMPART_KEY,
    GRAVEWATCH_COURTYARD_KEY,
    GRAVEWATCH_CHAPEL_KEY,
    GRAVEWATCH_VESTRY_KEY,
    GRAVEWATCH_OSSUARY_KEY,
    GRAVEWATCH_CRYPT_KEY,
    GRAVEWATCH_TOMB_KEY,
    GRAVEWATCH_PORTCULLIS_KEY,
    GRAVEWATCH_GREAT_HALL_KEY,
    GRAVEWATCH_MAP_ROOM_KEY,
)
GRAVEWATCH_ROOM_KEYS = (
    GRAVEWATCH_RIVER_MILE_KEY,
    GRAVEWATCH_FERRY_RUIN_KEY,
    *GRAVEWATCH_KEEP_ROOM_KEYS,
)

GRAVEWATCH_QUEST_KEY = "gravewatch_the_dead_garrison"
GRAVEWATCH_COMPLETE_FLAG = "gravewatch_first_clear_complete"
GRAVEWATCH_CAPTAIN_DEFEATED_FLAG = "gravewatch_captain_defeated"
GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG = "gravewatch_chaplain_defeated"
GRAVEWATCH_GATE_OPEN_FLAG = "gravewatch_inner_gate_open"
GRAVEWATCH_CASTELLAN_DEFEATED_FLAG = "gravewatch_castellan_defeated"
GRAVEWATCH_HOUND_PULL_FLAG = "gravewatch_courtyard_hound_cleared"
GRAVEWATCH_ARCHER_PULL_FLAG = "gravewatch_courtyard_archer_cleared"
GRAVEWATCH_PIKE_PULL_FLAG = "gravewatch_courtyard_pike_cleared"
GRAVEWATCH_PULL_FLAGS = frozenset(
    {GRAVEWATCH_HOUND_PULL_FLAG, GRAVEWATCH_ARCHER_PULL_FLAG, GRAVEWATCH_PIKE_PULL_FLAG}
)

SERGEANT_NPC_KEY = "gravewatch_sergeant_toma_reed"

SENTRY_KEY = "gravewatch_skeletal_sentry"
HOUND_KEY = "gravewatch_bone_hound"
ARCHER_KEY = "gravewatch_crossbowman"
PIKE_KEY = "gravewatch_pikeguard"
CHAMPION_KEY = "gravewatch_crypt_champion"
COURTYARD_HOUND_KEY = "gravewatch_courtyard_bone_hound"
COURTYARD_ARCHER_KEY = "gravewatch_courtyard_crossbowman"
COURTYARD_PIKE_KEY = "gravewatch_courtyard_pikeguard"
CAPTAIN_KEY = "gravewatch_wight_captain"
REINFORCED_CAPTAIN_KEY = "gravewatch_wight_captain_reinforced"
CHAPLAIN_KEY = "gravewatch_bell_wight"
CASTELLAN_KEY = "gravewatch_last_castellan"

OLD_GARRISON_IRON_KEY = "gravewatch_old_garrison_iron"
CASTELLAN_SIGNET_KEY = "gravewatch_castellan_signet"
RELIEF_SURCOAT_KEY = "gravewatch_relief_surcoat"


GRAVEWATCH_QUEST = QuestDefinition(
    key=GRAVEWATCH_QUEST_KEY,
    name="The Dead Garrison",
    style="structured",
    minimum_level=8,
    description=(
        "Gravewatch Keep was a plain river fort long before Veyra became a capital. Its dead garrison has begun walking again. "
        "No one suspects the Gloamworks and no machine is malfunctioning: this is an old fortress full of armed skeletons, and the east river road needs it cleared."
    ),
    objective_steps=(
        ("report_sergeant", "TALK SERGEANT on the River Mile east of Veyra."),
        ("enter_keep", "Reach the Broken Barbican and enter Gravewatch Keep."),
        ("defeat_captain", "Clear the Courtyard of Standards and defeat Wight Captain Rell. Careful pulls make the fight easier."),
        ("silence_chapel", "Push through the chapel and defeat the Bell-Wight in the vestry."),
        ("open_inner_gate", "At the Inner Portcullis OPEN PORTCULLIS after both officers are down."),
        ("defeat_castellan", "Enter the Great Hall and ATTACK CASTELLAN."),
        ("light_beacon", "After the Last Castellan falls, enter his map room and LIGHT BEACON for the Veyra road crews."),
        ("complete", "You completed a straight fortress clear and made Gravewatch a sanctioned repeatable delve from Veyra."),
    ),
)

OLD_GARRISON_IRON = ItemDefinition(
    key=OLD_GARRISON_IRON_KEY,
    name="Old Garrison Iron",
    description=(
        "Heavy black iron recovered from Gravewatch weapons and fittings. It is old-fashioned, scarred, and still perfectly usable by a smith who values material over polish."
    ),
    category="material",
    tier=2,
)
CASTELLAN_SIGNET = ItemDefinition(
    key=CASTELLAN_SIGNET_KEY,
    name="Gravewatch Castellan Signet",
    description=(
        "A river-fort signet taken from the Last Castellan's command chain. The seal shows a square tower over three horizontal river lines."
    ),
    category="trophy",
    tier=2,
)
RELIEF_SURCOAT = ItemDefinition(
    key=RELIEF_SURCOAT_KEY,
    name="Gravewatch Relief Surcoat",
    description=(
        "A dark Veyran surcoat issued for the first confirmed Gravewatch clear. Its reinforced shoulders and short hem are meant for cramped fortress fighting, not ceremony."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Gravewatch Relief Surcoat",
        "chest",
        armor_class=3,
        stat_bonuses=CharacterStats(hp=2),
    ),
    tier=2,
)
GRAVEWATCH_ITEMS = (OLD_GARRISON_IRON, CASTELLAN_SIGNET, RELIEF_SURCOAT)


SKELETAL_SENTRY = EnemyDefinition(
    key=SENTRY_KEY,
    name="Gravewatch Sentry",
    aliases=("sentry", "skeleton", "skeletal sentry", "gravewatch sentry"),
    description="a yellowed infantry skeleton in river-rusted mail, sword and shield held with the dull correctness of an old drill",
    max_hp=112,
    armor_class=11,
    auto_attack_damage=9,
    auto_attack_interval=3.0,
    xp_reward=88,
)
BONE_HOUND = EnemyDefinition(
    key=HOUND_KEY,
    name="Bone Hound",
    aliases=("hound", "bone hound", "skeletal hound"),
    description="a war hound reduced to white ribs, iron collar, and a frightening amount of remembered momentum",
    max_hp=92,
    armor_class=9,
    auto_attack_damage=10,
    auto_attack_interval=2.35,
    xp_reward=82,
)
CROSSBOWMAN = EnemyDefinition(
    key=ARCHER_KEY,
    name="Gravewatch Crossbowman",
    aliases=("archer", "crossbowman", "skeletal archer", "gravewatch crossbowman"),
    description="a skeletal wall guard working a compact old crossbow with patient mechanical precision",
    max_hp=104,
    armor_class=10,
    auto_attack_damage=10,
    auto_attack_interval=2.75,
    xp_reward=92,
)
PIKEGUARD = EnemyDefinition(
    key=PIKE_KEY,
    name="Pikeguard Skeleton",
    aliases=("pike", "pikeguard", "pikeguard skeleton", "guard"),
    description="a broad-shouldered skeleton braced behind a long garrison pike and scraps of rectangular tower shield",
    max_hp=148,
    armor_class=14,
    auto_attack_damage=11,
    auto_attack_interval=3.15,
    xp_reward=112,
)
CRYPT_CHAMPION = EnemyDefinition(
    key=CHAMPION_KEY,
    name="Crypt Champion",
    aliases=("champion", "crypt champion", "skeletal champion"),
    description="a veteran skeleton wearing the surviving pieces of officer-grade plate over a body that no longer needs protection from weather",
    max_hp=178,
    armor_class=16,
    auto_attack_damage=13,
    auto_attack_interval=3.0,
    xp_reward=142,
)

# Courtyard versions are separate keys so their defeats can be recognized as the
# three optional pull elements without confusing ordinary hounds/archers/guards
# elsewhere in the keep.
COURTYARD_HOUND = replace(BONE_HOUND, key=COURTYARD_HOUND_KEY, name="Courtyard Bone Hound")
COURTYARD_ARCHER = replace(CROSSBOWMAN, key=COURTYARD_ARCHER_KEY, name="Courtyard Crossbowman")
COURTYARD_PIKE = replace(PIKEGUARD, key=COURTYARD_PIKE_KEY, name="Courtyard Pikeguard")

WIGHT_CAPTAIN = EnemyDefinition(
    key=CAPTAIN_KEY,
    name="Wight Captain Rell",
    aliases=("captain", "rell", "wight captain", "captain rell"),
    description=(
        "a dry-armored wight officer with one intact eye and a notched cavalry saber, still turning his head to check flanks that died centuries ago"
    ),
    max_hp=265,
    armor_class=17,
    auto_attack_damage=15,
    auto_attack_interval=2.85,
    xp_reward=220,
)
REINFORCED_WIGHT_CAPTAIN = EnemyDefinition(
    key=REINFORCED_CAPTAIN_KEY,
    name="Wight Captain Rell with Formation",
    aliases=("captain", "rell", "wight captain", "captain rell"),
    description=(
        "Wight Captain Rell fighting with the remaining courtyard patrol collapsed around him; every opening is covered by bone hounds, crossbow bolts, or pike points"
    ),
    max_hp=360,
    armor_class=19,
    auto_attack_damage=18,
    auto_attack_interval=2.65,
    xp_reward=285,
)
BELL_WIGHT = EnemyDefinition(
    key=CHAPLAIN_KEY,
    name="Bell-Wight Halden",
    aliases=("chaplain", "bell wight", "bell-wight", "halden", "wight"),
    description=(
        "the keep's former chaplain in cracked ceremonial mail, one hand wrapped around a bell rope polished smooth by fingers that should not still move"
    ),
    max_hp=238,
    armor_class=16,
    auto_attack_damage=14,
    auto_attack_interval=2.85,
    xp_reward=205,
)
LAST_CASTELLAN = EnemyDefinition(
    key=CASTELLAN_KEY,
    name="Castellan Merrow Kade",
    aliases=("castellan", "merrow", "kade", "merrow kade", "last castellan", "commander"),
    description=(
        "a tall wight commander in blackened river-plate, carrying a two-handed garrison blade and nothing theatrical except centuries of practice refusing to leave his post"
    ),
    max_hp=430,
    armor_class=20,
    auto_attack_damage=18,
    auto_attack_interval=2.8,
    xp_reward=365,
)
GRAVEWATCH_ENEMIES = (
    SKELETAL_SENTRY,
    BONE_HOUND,
    CROSSBOWMAN,
    PIKEGUARD,
    CRYPT_CHAMPION,
    COURTYARD_HOUND,
    COURTYARD_ARCHER,
    COURTYARD_PIKE,
    WIGHT_CAPTAIN,
    REINFORCED_WIGHT_CAPTAIN,
    BELL_WIGHT,
    LAST_CASTELLAN,
)


SERGEANT = NpcDefinition(
    key=SERGEANT_NPC_KEY,
    name="Sergeant Toma Reed",
    short_description="a Veyran road sergeant watching Gravewatch's broken tower line through a battered brass fieldglass",
    room_key=GRAVEWATCH_RIVER_MILE_KEY,
    role="Gravewatch expedition marshal",
    dialogue=(
        "'For once the report is exactly what it looks like. Old keep. Skeletons. Wights. Bad road.'",
        "'The courtyard is the dangerous pull. Strip the patrol off Captain Rell before you commit, unless you enjoy fighting an officer with his whole formation on top of you.'",
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
        region_key=GRAVEWATCH_REGION_KEY,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "gravewatch", "level_8_10", *tags),
    )


GRAVEWATCH_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        GRAVEWATCH_RIVER_MILE_KEY,
        "Gravewatch River Mile",
        "Veyra's downstream road narrows between willow scrub and a high green river. Half a day's travel is compressed into old milestones, cart ruts, and the distant square silhouette of Gravewatch Keep. A small road camp marks the last reliably safe place to stop.",
        {"west": VEYRA_EAST_RIVER_GATE_KEY, "east": GRAVEWATCH_FERRY_RUIN_KEY},
        npcs=(SERGEANT_NPC_KEY,), tags=("approach", "safe"),
    ),
    _room(
        GRAVEWATCH_FERRY_RUIN_KEY,
        "Gravewatch Ferry Ruin",
        "A collapsed ferry landing sits below the keep. The old chain still runs from a stone bollard into the water, but the ferry itself is three ribs of timber in the mud. Above, the road climbs directly toward a broken barbican where something in old mail occasionally crosses the gap.",
        {"west": GRAVEWATCH_RIVER_MILE_KEY, "north": GRAVEWATCH_BARBICAN_KEY},
        enemies=(BONE_HOUND.key,), tags=("approach",),
    ),
    _room(
        GRAVEWATCH_BARBICAN_KEY,
        "Broken Barbican",
        "The outer arch has lost half its roof and gained a tree growing through the murder-hole gallery. Rusted portcullis teeth hang high overhead. The bones below are less decorative: a sentry still walks the same six paces between arrow slits.",
        {"south": GRAVEWATCH_FERRY_RUIN_KEY, "north": GRAVEWATCH_GATEHOUSE_KEY},
        enemies=(SENTRY_KEY,), tags=("dungeon", "entrance"),
    ),
    _room(
        GRAVEWATCH_GATEHOUSE_KEY,
        "Gatehouse",
        "A cramped stone gate chamber forces everyone through the same narrow lane. Shield hooks line the walls. A collapsed stair climbs toward the west rampart while the main passage opens into daylight beyond.",
        {"south": GRAVEWATCH_BARBICAN_KEY, "north": GRAVEWATCH_OUTER_YARD_KEY, "up": GRAVEWATCH_RAMPART_KEY},
        enemies=(SENTRY_KEY, ARCHER_KEY), tags=("dungeon", "trash_pack"),
    ),
    _room(
        GRAVEWATCH_OUTER_YARD_KEY,
        "Outer Yard",
        "Rain has turned the old mustering yard into weeds and black puddles. Kennel arches gape to the west; the barracks block stands east. Bone hounds nose through collapsed straw while infantry skeletons drift between the doors in pairs rather than dramatic hordes.",
        {"south": GRAVEWATCH_GATEHOUSE_KEY, "west": GRAVEWATCH_KENNEL_KEY, "east": GRAVEWATCH_BARRACKS_KEY},
        enemies=(HOUND_KEY, SENTRY_KEY), tags=("dungeon", "trash_pack"),
    ),
    _room(
        GRAVEWATCH_KENNEL_KEY,
        "Kennel Run",
        "Low stone kennels line a narrow service court. Iron rings remain set into the walls, several still holding lengths of chain. The hounds here do not bark; claws and collar links give enough warning.",
        {"east": GRAVEWATCH_OUTER_YARD_KEY, "north": GRAVEWATCH_COURTYARD_KEY},
        enemies=(HOUND_KEY,), tags=("dungeon", "tight_combat"),
    ),
    _room(
        GRAVEWATCH_BARRACKS_KEY,
        "Garrison Barracks",
        "Rows of stone bed ledges make the room feel orderly even after the roof fell in. Spears lean where living hands left them. Skeleton infantry still forms around the center aisle, leaving little room to circle a bad engagement.",
        {"west": GRAVEWATCH_OUTER_YARD_KEY, "north": GRAVEWATCH_ARMORY_KEY, "east": GRAVEWATCH_COURTYARD_KEY},
        enemies=(SENTRY_KEY, PIKE_KEY), tags=("dungeon", "trash_pack"),
    ),
    _room(
        GRAVEWATCH_ARMORY_KEY,
        "Old Armory",
        "Most useful weapons vanished generations ago, but racks of corroded pikes and shield frames remain. One heavy guard stands where the quartermaster's cage used to be, as though inventory can still be protected from thieves who are all dead.",
        {"south": GRAVEWATCH_BARRACKS_KEY}, enemies=(PIKE_KEY,), tags=("dungeon", "side_room"),
    ),
    _room(
        GRAVEWATCH_RAMPART_KEY,
        "West Rampart",
        "The rampart gives a clean view of the green river and Veyra's distant haze upstream. Crossbow embrasures overlook the courtyard below. Wind moves through empty helmets hanging from old pegs and occasionally through archers that are not empty enough.",
        {"down": GRAVEWATCH_GATEHOUSE_KEY, "east": GRAVEWATCH_COURTYARD_KEY},
        enemies=(ARCHER_KEY,), tags=("dungeon", "side_route"),
    ),
    _room(
        GRAVEWATCH_COURTYARD_KEY,
        "Courtyard of Standards",
        "Three shredded garrison standards hang above a rectangular court. Wight Captain Rell waits beneath them while a bone hound circles the low wall, a crossbowman watches from the stair, and a pikeguard holds the chapel lane. The formation overlaps just enough to punish anyone who charges the officer first.",
        {"west": GRAVEWATCH_KENNEL_KEY, "south": GRAVEWATCH_BARRACKS_KEY, "up": GRAVEWATCH_RAMPART_KEY, "north": GRAVEWATCH_CHAPEL_KEY},
        tags=("dungeon", "miniboss", "pull_tutorial"),
    ),
    _room(
        GRAVEWATCH_CHAPEL_KEY,
        "Chapel Nave",
        "A narrow chapel keeps its rows of stone benches because nobody ever needed to loot them. Broken saint figures look down on a center aisle barely wide enough for two shield lines. The fights here are simple and cramped: no mystery, just poor room to recover from a bad target choice.",
        {"south": GRAVEWATCH_COURTYARD_KEY, "north": GRAVEWATCH_VESTRY_KEY},
        enemies=(SENTRY_KEY, PIKE_KEY), tags=("dungeon", "tight_combat"),
    ),
    _room(
        GRAVEWATCH_VESTRY_KEY,
        "Bell Vestry",
        "The chapel bell hangs one floor lower than it should after its tower partially collapsed. A black rope drops beside an old prayer desk. Bell-Wight Halden stands between the rope and an east-hand ossuary door, as if every alarm still needs his permission.",
        {"south": GRAVEWATCH_CHAPEL_KEY, "east": GRAVEWATCH_OSSUARY_KEY},
        tags=("dungeon", "miniboss"),
    ),
    _room(
        GRAVEWATCH_OSSUARY_KEY,
        "Ossuary Stair",
        "A descending stair passes shelves of sorted garrison bones, most of them empty now. Those that remain shift when footsteps pass, producing the dry sound of dice being stirred in a cup.",
        {"west": GRAVEWATCH_VESTRY_KEY, "down": GRAVEWATCH_CRYPT_KEY},
        enemies=(CHAMPION_KEY, HOUND_KEY), tags=("dungeon", "undercroft"),
    ),
    _room(
        GRAVEWATCH_CRYPT_KEY,
        "Garrison Crypt Hall",
        "Officer niches and common burial trenches share the same long undercroft. Water from the river sweats through the north wall. A straight corridor leads to the keep's inner portcullis while a side arch opens into the officers' tomb.",
        {"up": GRAVEWATCH_OSSUARY_KEY, "east": GRAVEWATCH_TOMB_KEY, "north": GRAVEWATCH_PORTCULLIS_KEY},
        enemies=(PIKE_KEY, CHAMPION_KEY), tags=("dungeon", "trash_pack"),
    ),
    _room(
        GRAVEWATCH_TOMB_KEY,
        "Officers' Tomb",
        "Stone shelves hold the names of people whose rank once mattered more than the condition of their bones. A single champion stands among cracked memorial shields. Scratched into the lintel is an old command formula: HOLD THE RIVER GATE UNTIL RELIEVED.",
        {"west": GRAVEWATCH_CRYPT_KEY}, enemies=(CHAMPION_KEY,), tags=("dungeon", "side_room", "lore"),
    ),
    _room(
        GRAVEWATCH_PORTCULLIS_KEY,
        "Inner Portcullis",
        "An iron lattice divides the undercroft from a steep stair into the keep proper. Two old officer seals sit in the lifting mechanism: one marked for the courtyard captain, one for the chapel. The gate is not clever. It simply expects both chains of command to be accounted for.",
        {"south": GRAVEWATCH_CRYPT_KEY, "north": GRAVEWATCH_GREAT_HALL_KEY},
        tags=("dungeon", "boss_gate"),
    ),
    _room(
        GRAVEWATCH_GREAT_HALL_KEY,
        "Gravewatch Great Hall",
        "The keep's great hall is disappointingly practical: long tables, a cold hearth, drainage channels, and a command dais facing the doors. Castellan Merrow Kade waits on that dais with a two-handed garrison blade. There is no puzzle left in the room. He is simply the hardest soldier in the keep.",
        {"south": GRAVEWATCH_PORTCULLIS_KEY, "east": GRAVEWATCH_MAP_ROOM_KEY},
        tags=("dungeon", "boss"),
    ),
    _room(
        GRAVEWATCH_MAP_ROOM_KEY,
        "Castellan's Map Room",
        "A dry chamber behind the dais still holds river maps pinned beneath iron strips. A shuttered relief beacon faces Veyra upstream. Lighting it would tell the road crews one useful thing: somebody reached the end of Gravewatch and came back in control of the room.",
        {"west": GRAVEWATCH_GREAT_HALL_KEY}, tags=("dungeon", "completion", "safe"),
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


def gravewatch_augmentations() -> dict[str, RoomAugmentation]:
    return {
        VEYRA_EAST_RIVER_GATE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=GRAVEWATCH_RIVER_MILE_KEY,
                    name="Gravewatch River Road",
                    travel_text="You follow the downstream river road beyond Veyra toward the square ruin of Gravewatch Keep.",
                    condition=ViewCondition(required_flags=(VEYRA_RESIDENT_FLAG,), min_level=8),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "gravewatch_road_notice",
                    "Gravewatch Road Notice",
                    "a fresh watch notice naming an undead-held keep downriver",
                    "GRAVEWATCH KEEP — ROAD HAZARD. Confirmed skeletal garrison, bone hounds, and at least two wight officers. Experienced travelers may report to Sergeant Toma Reed at the river-mile camp. This notice contains no mention of Gloam activity.",
                    ("notice", "gravewatch notice", "road notice", "gravewatch"),
                ),
            ),
        ),
        GRAVEWATCH_COURTYARD_KEY: RoomAugmentation(
            features=(
                _feature(
                    "gravewatch_formation",
                    "Overlapping Formation",
                    "three patrol elements covering Captain Rell's approach",
                    "The hound can be drawn around the low wall, the crossbowman can be baited down from the stair, and the pikeguard can be pulled out of the chapel lane. Use PULL HOUND, PULL ARCHER, and PULL PIKEGUARD. Charging ATTACK CAPTAIN before clearing them gives Rell his whole formation.",
                    ("formation", "patrol", "patrols", "captain formation"),
                ),
            ),
        ),
        GRAVEWATCH_PORTCULLIS_KEY: RoomAugmentation(
            features=(
                _feature(
                    "gravewatch_portcullis_mechanism",
                    "Officer-Seal Winch",
                    "a simple winch requiring the captain and chapel chains to be broken",
                    "The old mechanism has two weighted catches. Once Wight Captain Rell and Bell-Wight Halden are down, OPEN PORTCULLIS can lift the inner gate.",
                    ("winch", "portcullis", "gate", "mechanism"),
                ),
            ),
        ),
        GRAVEWATCH_MAP_ROOM_KEY: RoomAugmentation(
            features=(
                _feature(
                    "gravewatch_relief_beacon",
                    "Relief Beacon",
                    "a shuttered oil beacon facing the Veyra road upstream",
                    "The beacon is mundane: oil cup, mirrored backplate, river-facing shutters. LIGHT BEACON after defeating the Castellan to mark the first confirmed clear.",
                    ("beacon", "relief beacon", "lamp"),
                ),
            ),
        ),
    }


def courtyard_pull_complete(flags: set[str] | frozenset[str]) -> bool:
    return GRAVEWATCH_PULL_FLAGS.issubset(flags)


def captain_definition_for_flags(flags: set[str] | frozenset[str]) -> EnemyDefinition:
    return WIGHT_CAPTAIN if courtyard_pull_complete(flags) else REINFORCED_WIGHT_CAPTAIN


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


def install_gravewatch_content(world_service=None) -> None:
    if GRAVEWATCH_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GRAVEWATCH_QUEST,)
    quests.QUESTS_BY_KEY[GRAVEWATCH_QUEST.key] = GRAVEWATCH_QUEST

    for item in GRAVEWATCH_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in GRAVEWATCH_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    _replace_npc(SERGEANT)
    for room in GRAVEWATCH_ROOMS:
        _replace_room(room)

    # Gravewatch intentionally feeds an existing Necromancer catalyst and a new
    # mundane smithing material into the live social economy.
    for key in (SENTRY_KEY, HOUND_KEY, ARCHER_KEY, PIKE_KEY, CHAMPION_KEY):
        economy.LOOT_TABLES[key] = (economy.LootDrop("bone_chips", 1),)
    economy.LOOT_TABLES[CHAMPION_KEY] = (economy.LootDrop("bone_chips", 2),)
    economy.LOOT_TABLES[CAPTAIN_KEY] = (economy.LootDrop(OLD_GARRISON_IRON_KEY, 1),)
    economy.LOOT_TABLES[REINFORCED_CAPTAIN_KEY] = (economy.LootDrop(OLD_GARRISON_IRON_KEY, 1),)
    economy.LOOT_TABLES[CHAPLAIN_KEY] = (economy.LootDrop(OLD_GARRISON_IRON_KEY, 1),)

    if world_service is None:
        return
    for room in GRAVEWATCH_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in gravewatch_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*GRAVEWATCH_ROOM_KEYS, VEYRA_EAST_RIVER_GATE_KEY):
            cache.pop(key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, GRAVEWATCH_QUEST_KEY)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _ensure_quest(session) -> bool:
    if session.character is None:
        return False
    if session.character.current_room not in GRAVEWATCH_ROOM_KEYS:
        return False
    if VEYRA_RESIDENT_FLAG not in _flags(session) or session.character.level < 8:
        return False
    if GRAVEWATCH_COMPLETE_FLAG in _flags(session):
        return True
    if _quest(session) is None:
        session.database.start_quest(session.character.id, GRAVEWATCH_QUEST_KEY, "report_sergeant")
    return True


async def _talk_sergeant(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_RIVER_MILE_KEY:
        return False
    _ensure_quest(session)
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] == "report_sergeant":
        session.database.advance_quest(session.character.id, GRAVEWATCH_QUEST_KEY, "enter_keep")
        await session.send(
            "Toma lowers the fieldglass. 'Good. This one is simple enough to be dangerous. Sentries in the gate, hounds in the yard, Captain Rell holding the courtyard, a bell-wight in the chapel, and the Castellan above the crypts. Pull Rell's patrol apart before you hit him. Everything after that is doors, corners, and keeping your head.'\r\n"
        )
        return True
    await session.send(
        "Toma says, 'Gravewatch is still there. If you already know the route, run it clean. The keep is a good place to learn whether your fundamentals are actually fundamentals.'\r\n"
    )
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


async def _pull_courtyard(session, kind: str) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_COURTYARD_KEY:
        return False
    definitions = {
        "hound": (COURTYARD_HOUND, GRAVEWATCH_HOUND_PULL_FLAG, "You scrape a boot along the low wall. The bone hound breaks formation and comes around the corner alone."),
        "archer": (COURTYARD_ARCHER, GRAVEWATCH_ARCHER_PULL_FLAG, "You show yourself just long enough to draw the crossbowman down from the stair and out of Captain Rell's covering line."),
        "pike": (COURTYARD_PIKE, GRAVEWATCH_PIKE_PULL_FLAG, "You threaten the chapel lane, then give ground. The pikeguard follows far enough to lose the captain's support."),
    }
    enemy, flag, text = definitions[kind]
    if flag in _flags(session):
        await session.send("That courtyard patrol element has already been cleared from Captain Rell's formation.\r\n")
        return True
    if session.active_enemy is not None:
        await session.send("Finish the fight you already pulled before trying to separate another patrol.\r\n")
        return True
    if not _begin_forced_combat(session, enemy):
        await session.send("You cannot make a clean pull in your current combat state.\r\n")
        return True
    await session.send(text + " Combat begins.\r\n")
    return True


async def _engage_captain(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_COURTYARD_KEY:
        return False
    if GRAVEWATCH_CAPTAIN_DEFEATED_FLAG in _flags(session):
        await session.send("Captain Rell has already been broken on this character's first clear. His courtyard remains a repeatable combat space, but the chapel route is open.\r\n")
        return True
    if session.active_enemy is not None:
        await session.send("You are already in combat.\r\n")
        return True
    definition = captain_definition_for_flags(_flags(session))
    if not _begin_forced_combat(session, definition):
        await session.send("You cannot engage Captain Rell in your current combat state.\r\n")
        return True
    if definition.key == REINFORCED_CAPTAIN_KEY:
        await session.send(
            "You charge Captain Rell before stripping away the overlapping patrol. The hound closes one side, the pikeguard owns the chapel lane, and the crossbowman keeps the stair. This is the same captain with every advantage you chose to leave him. Combat begins.\r\n"
        )
    else:
        await session.send(
            "The courtyard is finally quiet enough to see Captain Rell as one opponent instead of a formation. He draws his saber and steps off the standard stone. Combat begins.\r\n"
        )
    return True


async def _engage_chaplain(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_VESTRY_KEY:
        return False
    if GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG in _flags(session):
        await session.send("Bell-Wight Halden has already fallen; the ossuary door stands usable.\r\n")
        return True
    if session.active_enemy is not None:
        await session.send("You are already in combat.\r\n")
        return True
    if not _begin_forced_combat(session, BELL_WIGHT):
        await session.send("You cannot engage the Bell-Wight in your current combat state.\r\n")
        return True
    await session.send(
        "Halden pulls the bell rope once. The note is ugly but ordinary iron, echoing through a room too small to kite comfortably. He releases the rope and comes at you. Combat begins.\r\n"
    )
    return True


async def _open_portcullis(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_PORTCULLIS_KEY:
        return False
    flags = _flags(session)
    missing: list[str] = []
    if GRAVEWATCH_CAPTAIN_DEFEATED_FLAG not in flags:
        missing.append("courtyard captain")
    if GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG not in flags:
        missing.append("chapel bell-wight")
    if missing:
        await session.send("The officer-seal winch will not release yet. Still outstanding: " + ", ".join(missing) + ".\r\n")
        return True
    if GRAVEWATCH_GATE_OPEN_FLAG not in flags:
        session.database.grant_flag(session.character.id, GRAVEWATCH_GATE_OPEN_FLAG)
        q = _quest(session)
        if q and q["status"] == "active" and q["current_step"] == "open_inner_gate":
            session.database.advance_quest(session.character.id, GRAVEWATCH_QUEST_KEY, "defeat_castellan")
        await session.send(
            "Both officer catches hang dead. You put your weight on the winch and the inner portcullis climbs one tooth at a time. No riddle, no hidden rune: the chain of command is gone and the gate works.\r\n"
        )
        return True
    await session.send("The inner portcullis is already raised.\r\n")
    return True


async def _engage_castellan(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_GREAT_HALL_KEY:
        return False
    if GRAVEWATCH_GATE_OPEN_FLAG not in _flags(session):
        await session.send("You have not opened the inner portcullis yet.\r\n")
        return True
    if GRAVEWATCH_CASTELLAN_DEFEATED_FLAG in _flags(session):
        await session.send("Merrow Kade has already fallen on your first clear. The Great Hall remains part of the repeatable delve, but your beacon objective is beyond him.\r\n")
        return True
    if session.active_enemy is not None:
        await session.send("You are already in combat.\r\n")
        return True
    if not _begin_forced_combat(session, LAST_CASTELLAN):
        await session.send("You cannot engage the Castellan in your current combat state.\r\n")
        return True
    await session.send(
        "Merrow Kade steps down from the command dais and takes the center of the room. There is no phase puzzle and no secret control panel. He has reach, armor, a heavy blade, and a great deal of health. The final lesson is the oldest dungeon lesson: execute the fight cleanly. Combat begins.\r\n"
    )
    return True


async def _light_beacon(session) -> bool:
    if session.character is None or session.character.current_room != GRAVEWATCH_MAP_ROOM_KEY:
        return False
    if GRAVEWATCH_CASTELLAN_DEFEATED_FLAG not in _flags(session):
        await session.send("Lighting the relief beacon before controlling the Great Hall would be a dangerously optimistic report.\r\n")
        return True
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] == "light_beacon":
        session.database.complete_quest(session.character.id, GRAVEWATCH_QUEST_KEY)
        session.database.grant_flag(session.character.id, GRAVEWATCH_COMPLETE_FLAG)
        session.database.add_item(session.character.id, CASTELLAN_SIGNET_KEY, 1)
        session.database.add_item(session.character.id, RELIEF_SURCOAT_KEY, 1)
        session.database.add_experience(session.character.id, 420)
        _refresh(session)
        await session.send(
            "You trim the wick, open the river-facing shutters, and light the Gravewatch relief beacon. A plain yellow point appears above the ruined keep where Veyra's road crews can see it upstream. This is not the end of every restless bone in the fortress; it is the first confirmed full clear, enough to turn a forbidden ruin into a sanctioned repeatable delve. The Dead Garrison complete: 420 XP, a Gravewatch Castellan Signet, and a Gravewatch Relief Surcoat.\r\n"
        )
        return True
    await session.send("The relief beacon already carries the record of your first clear. Gravewatch remains open for repeat runs and materials.\r\n")
    return True


async def _status(session) -> bool:
    if session.character is None or session.character.current_room not in GRAVEWATCH_ROOM_KEYS:
        return False
    flags = _flags(session)
    pulls = [
        ("hound", GRAVEWATCH_HOUND_PULL_FLAG),
        ("archer", GRAVEWATCH_ARCHER_PULL_FLAG),
        ("pikeguard", GRAVEWATCH_PIKE_PULL_FLAG),
    ]
    q = _quest(session)
    step = q["current_step"] if q and q["status"] == "active" else "first clear complete" if GRAVEWATCH_COMPLETE_FLAG in flags else "not started"
    await session.send(
        "GRAVEWATCH STATUS\r\n"
        f" - First-clear objective: {step}.\r\n"
        f" - Courtyard pulls cleared: {', '.join(name for name, flag in pulls if flag in flags) or 'none'}.\r\n"
        f" - Captain: {'down' if GRAVEWATCH_CAPTAIN_DEFEATED_FLAG in flags else 'active'}.\r\n"
        f" - Bell-Wight: {'down' if GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG in flags else 'active'}.\r\n"
        f" - Inner gate: {'open' if GRAVEWATCH_GATE_OPEN_FLAG in flags else 'closed'}.\r\n"
        f" - Castellan: {'down' if GRAVEWATCH_CASTELLAN_DEFEATED_FLAG in flags else 'active'}.\r\n"
    )
    return True


def install_gravewatch_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_gravewatch_runtime_installed", False):
        return
    install_gravewatch_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        _ensure_quest(self)

    async def move_character(self, direction: str) -> None:
        normalized = direction.strip().lower()
        if self.character is not None:
            room = self.character.current_room
            flags = _flags(self)
            if room == GRAVEWATCH_COURTYARD_KEY and normalized in {"north", "n"} and GRAVEWATCH_CAPTAIN_DEFEATED_FLAG not in flags:
                await self.send("Captain Rell still owns the chapel lane. Defeat him before pushing north.\r\n")
                return
            if room == GRAVEWATCH_VESTRY_KEY and normalized in {"east", "e"} and GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG not in flags:
                await self.send("Bell-Wight Halden blocks the ossuary door. Defeat him before moving east.\r\n")
                return
            if room == GRAVEWATCH_PORTCULLIS_KEY and normalized in {"north", "n"} and GRAVEWATCH_GATE_OPEN_FLAG not in flags:
                await self.send("The inner portcullis is still down. OPEN PORTCULLIS after defeating both officers.\r\n")
                return
            if room == GRAVEWATCH_GREAT_HALL_KEY and normalized in {"east", "e"} and GRAVEWATCH_CASTELLAN_DEFEATED_FLAG not in flags:
                await self.send("Merrow Kade still controls the dais and the map-room door. Defeat the Castellan first.\r\n")
                return
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        _ensure_quest(self)
        if self.character is None:
            return
        if self.character.current_room == GRAVEWATCH_BARBICAN_KEY and before != GRAVEWATCH_BARBICAN_KEY:
            q = _quest(self)
            if q and q["status"] == "active" and q["current_step"] == "enter_keep":
                self.database.advance_quest(self.character.id, GRAVEWATCH_QUEST_KEY, "defeat_captain")
                await self.send("The broken barbican closes the river road behind you. Gravewatch's first lesson is ordinary: clear rooms, watch corners, and do not let the courtyard formation choose the pull for you.\r\n")

    def enemy_in_room(self, target_text: str):
        if self.character is not None:
            room = self.character.current_room
            flags = _flags(self)
            if room == GRAVEWATCH_COURTYARD_KEY and GRAVEWATCH_CAPTAIN_DEFEATED_FLAG not in flags:
                definition = captain_definition_for_flags(flags)
                if definition.matches(target_text):
                    return EnemyState(definition)
            if room == GRAVEWATCH_VESTRY_KEY and GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG not in flags and BELL_WIGHT.matches(target_text):
                return EnemyState(BELL_WIGHT)
            if room == GRAVEWATCH_GREAT_HALL_KEY and GRAVEWATCH_GATE_OPEN_FLAG in flags and GRAVEWATCH_CASTELLAN_DEFEATED_FLAG not in flags and LAST_CASTELLAN.matches(target_text):
                return EnemyState(LAST_CASTELLAN)
        return previous_enemy_lookup(self, target_text)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active or self.character is None:
            return

        pull_flags = {
            COURTYARD_HOUND_KEY: GRAVEWATCH_HOUND_PULL_FLAG,
            COURTYARD_ARCHER_KEY: GRAVEWATCH_ARCHER_PULL_FLAG,
            COURTYARD_PIKE_KEY: GRAVEWATCH_PIKE_PULL_FLAG,
        }
        if key in pull_flags:
            self.database.grant_flag(self.character.id, pull_flags[key])
            remaining = GRAVEWATCH_PULL_FLAGS - _flags(self)
            if remaining:
                await self.send(f"That patrol element is down. {len(remaining)} courtyard pull(s) still overlap Captain Rell.\r\n")
            else:
                await self.send("The last covering patrol drops. Captain Rell is isolated; ATTACK CAPTAIN now gives you the clean fight.\r\n")
            return

        if key in {CAPTAIN_KEY, REINFORCED_CAPTAIN_KEY}:
            if GRAVEWATCH_CAPTAIN_DEFEATED_FLAG not in _flags(self):
                self.database.grant_flag(self.character.id, GRAVEWATCH_CAPTAIN_DEFEATED_FLAG)
                q = _quest(self)
                if q and q["status"] == "active" and q["current_step"] == "defeat_captain":
                    self.database.advance_quest(self.character.id, GRAVEWATCH_QUEST_KEY, "silence_chapel")
                await self.send("Captain Rell falls beneath the shredded standards. The chapel lane north is open.\r\n")
            return

        if key == CHAPLAIN_KEY:
            if GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG not in _flags(self):
                self.database.grant_flag(self.character.id, GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG)
                q = _quest(self)
                if q and q["status"] == "active" and q["current_step"] == "silence_chapel":
                    self.database.advance_quest(self.character.id, GRAVEWATCH_QUEST_KEY, "open_inner_gate")
                await self.send("Halden collapses beside the rope. The bell stops with him, and the ossuary door east is clear.\r\n")
            return

        if key == CASTELLAN_KEY:
            if GRAVEWATCH_CASTELLAN_DEFEATED_FLAG not in _flags(self):
                self.database.grant_flag(self.character.id, GRAVEWATCH_CASTELLAN_DEFEATED_FLAG)
                self.database.add_item(self.character.id, OLD_GARRISON_IRON_KEY, 2)
                q = _quest(self)
                if q and q["status"] == "active" and q["current_step"] == "defeat_castellan":
                    self.database.advance_quest(self.character.id, GRAVEWATCH_QUEST_KEY, "light_beacon")
                await self.send("Merrow Kade finally loses the center of the hall and goes down beside the command dais. You recover 2 Old Garrison Iron. The map-room door east is open.\r\n")
            return

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

        if normalized in {"talk sergeant", "talk toma", "talk toma reed", "speak sergeant"}:
            handled = await _talk_sergeant(self)
        elif normalized in {"gravewatch status", "keep status", "dungeon status"}:
            handled = await _status(self)
        elif normalized in {"pull hound", "pull bone hound"}:
            handled = await _pull_courtyard(self, "hound")
        elif normalized in {"pull archer", "pull crossbowman"}:
            handled = await _pull_courtyard(self, "archer")
        elif normalized in {"pull pike", "pull pikeguard", "pull guard"}:
            handled = await _pull_courtyard(self, "pike")
        elif normalized in {"attack captain", "attack rell", "fight captain"}:
            handled = await _engage_captain(self)
        elif normalized in {"attack chaplain", "attack bell wight", "attack bell-wight", "fight chaplain"}:
            handled = await _engage_chaplain(self)
        elif normalized in {"open portcullis", "raise portcullis", "open inner gate", "raise gate"}:
            handled = await _open_portcullis(self)
        elif normalized in {"attack castellan", "attack merrow", "attack kade", "fight castellan", "attack commander"}:
            handled = await _engage_castellan(self)
        elif normalized in {"light beacon", "light relief beacon", "ignite beacon"}:
            handled = await _light_beacon(self)

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
    player_session_class._gravewatch_runtime_installed = True
