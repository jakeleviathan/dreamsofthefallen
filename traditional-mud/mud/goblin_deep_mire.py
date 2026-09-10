from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.astralis_calendar import AstralisCalendarDate
from mud.astralis_time import ASTRALIS_CLOCK
from mud.combat import EnemyDefinition
from mud.crafting import ConsumableEffect, ItemDefinition, craft_recipe, trade_skill_value
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.goblin_outer_route import GOBLIN_OUTER_ROUTE_COMPLETE_FLAG
from mud.goblin_start import GOBLIN_REGION_KEY
from mud.goblin_swamp import GOBLIN_MUDGLASS_CROSSING_KEY, install_goblin_swamp_content
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.stats import CharacterStats
from mud.world import RoomDefinition


# ---------------------------------------------------------------------------
# Region topology
# ---------------------------------------------------------------------------

GOBLIN_BLACKREED_GATE_KEY = "goblin_blackreed_gate"
GOBLIN_SILTKNNIFE_BOARDWALK_KEY = "goblin_siltknife_boardwalk"
GOBLIN_SOURREED_TERRACE_KEY = "goblin_sourreed_terrace"
GOBLIN_RESIN_FEN_KEY = "goblin_resin_fen"
GOBLIN_CROOKED_FERRY_KEY = "goblin_crooked_ferry"
GOBLIN_TOADBELL_HOLLOW_KEY = "goblin_toadbell_hollow"
GOBLIN_SUNKEN_SURVEY_POST_KEY = "goblin_sunken_survey_post"
GOBLIN_THREE_STAKE_JUNCTION_KEY = "goblin_three_stake_junction"
GOBLIN_OLD_PUMP_TRACK_KEY = "goblin_old_pump_track"
GOBLIN_GREENHOUSE_APPROACH_KEY = "goblin_greenhouse_approach"
GOBLIN_GREENHOUSE_VESTIBULE_KEY = "goblin_greenhouse_vestibule"
GOBLIN_GREENHOUSE_FLOODED_HALL_KEY = "goblin_greenhouse_flooded_hall"
GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY = "goblin_greenhouse_pump_gallery"
GOBLIN_GREENHOUSE_CONSERVATORY_KEY = "goblin_greenhouse_conservatory"

GOBLIN_DEEP_MIRE_ROOM_KEYS: tuple[str, ...] = (
    GOBLIN_BLACKREED_GATE_KEY,
    GOBLIN_SILTKNNIFE_BOARDWALK_KEY,
    GOBLIN_SOURREED_TERRACE_KEY,
    GOBLIN_RESIN_FEN_KEY,
    GOBLIN_CROOKED_FERRY_KEY,
    GOBLIN_TOADBELL_HOLLOW_KEY,
    GOBLIN_SUNKEN_SURVEY_POST_KEY,
    GOBLIN_THREE_STAKE_JUNCTION_KEY,
    GOBLIN_OLD_PUMP_TRACK_KEY,
    GOBLIN_GREENHOUSE_APPROACH_KEY,
    GOBLIN_GREENHOUSE_VESTIBULE_KEY,
    GOBLIN_GREENHOUSE_FLOODED_HALL_KEY,
    GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY,
    GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
)

GOBLIN_GREENHOUSE_ROOM_KEYS = frozenset(
    {
        GOBLIN_GREENHOUSE_APPROACH_KEY,
        GOBLIN_GREENHOUSE_VESTIBULE_KEY,
        GOBLIN_GREENHOUSE_FLOODED_HALL_KEY,
        GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY,
        GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
    }
)

GOBLIN_DEEP_MIRE_ENTERED_FLAG = "goblin_deep_mire_entered"
GREENHOUSE_DRAINED_FLAG = "goblin_greenhouse_drain_open"
GREENHOUSE_LOUVERS_FLAG = "goblin_greenhouse_louvers_open"
GREENHOUSE_GLASSROOT_FLAG = "goblin_greenhouse_glassroot_harvested"


# ---------------------------------------------------------------------------
# Floodpick seasonal route control
# ---------------------------------------------------------------------------

FLOODPICK_MIREHOOK = "mirehook"
FLOODPICK_COPPERCAP = "coppercap"
FLOODPICK_TINLEDGER = "tinledger"
FLOODPICK_CLAN_KEYS: tuple[str, ...] = (
    FLOODPICK_MIREHOOK,
    FLOODPICK_COPPERCAP,
    FLOODPICK_TINLEDGER,
)
FLOODPICK_CLAN_NAMES = {
    FLOODPICK_MIREHOOK: "Mirehook Clan",
    FLOODPICK_COPPERCAP: "Coppercap Family",
    FLOODPICK_TINLEDGER: "Tinledger Clan",
}
FLOODPICK_CONTROL_BLOCK_DAYS = 3


def floodpick_controller(calendar: AstralisCalendarDate | None = None) -> str | None:
    """Return the clan holding the Sourreed Floodpick claim for this block.

    Floodpick only exists in spring. Control changes every three Astralis days
    (twelve real hours with the current clock), which keeps the world moving
    without making route ownership flicker constantly.
    """
    calendar = calendar or ASTRALIS_CLOCK.now().calendar
    if calendar.season_key != "spring":
        return None
    block = (calendar.season_day - 1) // FLOODPICK_CONTROL_BLOCK_DAYS
    return FLOODPICK_CLAN_KEYS[(calendar.year - 1 + block) % len(FLOODPICK_CLAN_KEYS)]


def floodpick_control_text(calendar: AstralisCalendarDate | None = None) -> str:
    calendar = calendar or ASTRALIS_CLOCK.now().calendar
    controller = floodpick_controller(calendar)
    if controller is None:
        return (
            "Floodpick is not active this season. Sourreed Terrace is being worked as a shared maintained herb route rather than a spring claim."
        )
    name = FLOODPICK_CLAN_NAMES[controller]
    return (
        f"Floodpick control: {name} currently holds the Sourreed Terrace route claim. "
        f"Spring claims are reviewed in {FLOODPICK_CONTROL_BLOCK_DAYS}-day blocks, so control can change as the flood exposes new ground."
    )


# ---------------------------------------------------------------------------
# Enemies: a step above the beginner swamp, still low-level and boss-free.
# ---------------------------------------------------------------------------

FEN_LEECH_CLUSTER = EnemyDefinition(
    key="fen_leech_cluster",
    name="Fen Leech Cluster",
    aliases=("leeches", "leech cluster", "fen leeches", "fen leech cluster"),
    description="a ropey knot of thumb-long leeches pulling itself across the wet boards toward warmth",
    max_hp=24,
    armor_class=4,
    auto_attack_damage=2,
    auto_attack_interval=3.7,
    xp_reward=35,
    retaliates=True,
    tutorial=False,
)

MARSH_RAZORCRAB = EnemyDefinition(
    key="marsh_razorcrab",
    name="Marsh Razorcrab",
    aliases=("razorcrab", "crab", "marsh crab", "marsh razorcrab"),
    description="a broad swamp crab with one chipped cutting claw and a shell stained the color of old pennies",
    max_hp=30,
    armor_class=5,
    auto_attack_damage=3,
    auto_attack_interval=3.5,
    xp_reward=45,
    retaliates=True,
    tutorial=False,
)

MIRE_WASP_CLOUD = EnemyDefinition(
    key="mire_wasp_cloud",
    name="Mire Wasp Cloud",
    aliases=("wasps", "wasp cloud", "mire wasps", "mire wasp cloud"),
    description="a low cloud of dark marsh wasps orbiting a half-drowned paper nest",
    max_hp=26,
    armor_class=5,
    auto_attack_damage=2,
    auto_attack_interval=3.2,
    xp_reward=40,
    retaliates=True,
    tutorial=False,
)

GLASSHOUSE_MOLDLING = EnemyDefinition(
    key="glasshouse_moldling",
    name="Glasshouse Moldling",
    aliases=("moldling", "mold", "glasshouse moldling"),
    description="a knee-high mass of fibrous greenhouse mold animated by trapped roots, irrigation wire, and stubborn wet growth",
    max_hp=32,
    armor_class=5,
    auto_attack_damage=3,
    auto_attack_interval=3.8,
    xp_reward=50,
    retaliates=True,
    tutorial=False,
)


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

GOBLIN_DEEP_MIRE_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=GOBLIN_BLACKREED_GATE_KEY,
        name="Blackreed Gate",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Beyond Mudglass Crossing, the maintained swamp stops pretending to be a city path. Two blackened reed bundles stand like gateposts around a narrow boardwalk, each wrapped in old warning ribbon and newer clan tags. Three routes split here: north over the Siltknife boards, east toward a raised herb terrace, and west into resin-dark water. The safer beginner routes remain south."
        ),
        exits={
            "south": GOBLIN_MUDGLASS_CROSSING_KEY,
            "north": GOBLIN_SILTKNNIFE_BOARDWALK_KEY,
            "east": GOBLIN_SOURREED_TERRACE_KEY,
            "west": GOBLIN_RESIN_FEN_KEY,
        },
        tags=("goblin_deep_mire", "low_level_wilderness", "branch_hub", "warning_boundary"),
    ),
    RoomDefinition(
        key=GOBLIN_SILTKNNIFE_BOARDWALK_KEY,
        name="Siltknife Boardwalk",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A narrow boardwalk cuts through mud flats where water rises and falls around blade-thin ridges of silt. Goblins have hammered broken knife blades into the rail as depth markers, not decoration. Bogmint grows in mats where the boards stay damp but not submerged. Blackreed Gate is south; a ferry landing lies east and a three-way junction north."
        ),
        exits={"south": GOBLIN_BLACKREED_GATE_KEY, "east": GOBLIN_CROOKED_FERRY_KEY, "north": GOBLIN_THREE_STAKE_JUNCTION_KEY},
        enemy_keys=(FEN_LEECH_CLUSTER.key,),
        tags=("goblin_deep_mire", "herbalism", "boardwalk", "light_combat"),
    ),
    RoomDefinition(
        key=GOBLIN_SOURREED_TERRACE_KEY,
        name="Sourreed Terrace",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A naturally raised shelf of packed peat supports one of the best herb beds close to Junk City. Sour reeds ring the terrace while useful medicinal growth fills the drier center. Claim stakes from several Goblin families crowd one corner, some old enough to have sunk nearly flush with the peat. Blackreed Gate lies west; a narrow north path reaches Crooked Ferry."
        ),
        exits={"west": GOBLIN_BLACKREED_GATE_KEY, "north": GOBLIN_CROOKED_FERRY_KEY},
        tags=("goblin_deep_mire", "herbalism", "contested_claim", "floodpick_route"),
    ),
    RoomDefinition(
        key=GOBLIN_RESIN_FEN_KEY,
        name="Resin Fen",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Low swamp trees lean over amber-black water, their bark split by old cuts that bead with thick aromatic resin. Small clay cups and scavenged bottle bottoms catch the drips. A westward breeze carries the sharp medicinal smell across the route. Blackreed Gate is east; a hummock trail continues north."
        ),
        exits={"east": GOBLIN_BLACKREED_GATE_KEY, "north": GOBLIN_TOADBELL_HOLLOW_KEY},
        enemy_keys=(MIRE_WASP_CLOUD.key,),
        tags=("goblin_deep_mire", "alchemy_resource", "resin", "light_combat"),
    ),
    RoomDefinition(
        key=GOBLIN_CROOKED_FERRY_KEY,
        name="Crooked Ferry",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A square raft rides a guide rope across a channel too deep for the surrounding boardwalks. The raft lists noticeably to one side, compensated by a stack of scrap iron bolted beneath the opposite rail. Paths return west to Siltknife and south to Sourreed; north, a raised track heads toward an abandoned pump district."
        ),
        exits={"west": GOBLIN_SILTKNNIFE_BOARDWALK_KEY, "south": GOBLIN_SOURREED_TERRACE_KEY, "north": GOBLIN_OLD_PUMP_TRACK_KEY},
        tags=("goblin_deep_mire", "ferry", "route_connector"),
    ),
    RoomDefinition(
        key=GOBLIN_TOADBELL_HOLLOW_KEY,
        name="Toadbell Hollow",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Bell-shaped marsh fungi grow beneath a ring of bowed trees, their caps making soft hollow knocks when rain or falling twigs strike them. Goblin gatherers have marked the useful Mirecaps with white thread. Resin Fen lies south; east reaches the Three-Stake Junction, while north climbs toward a drowned survey ruin."
        ),
        exits={"south": GOBLIN_RESIN_FEN_KEY, "east": GOBLIN_THREE_STAKE_JUNCTION_KEY, "north": GOBLIN_SUNKEN_SURVEY_POST_KEY},
        tags=("goblin_deep_mire", "alchemy_resource", "fungal", "route_connector"),
    ),
    RoomDefinition(
        key=GOBLIN_SUNKEN_SURVEY_POST_KEY,
        name="Sunken Survey Post",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Only the upper half of an old brick survey hut remains above the water. A newer Goblin platform has been built through its empty windows, leaving warped cabinets and corroded measuring rods visible below the surface. Faded Human numerals survive on one interior wall. Toadbell Hollow is south and Three-Stake Junction east."
        ),
        exits={"south": GOBLIN_TOADBELL_HOLLOW_KEY, "east": GOBLIN_THREE_STAKE_JUNCTION_KEY},
        tags=("goblin_deep_mire", "semi_submerged_ruin", "human_ruin", "exploration"),
    ),
    RoomDefinition(
        key=GOBLIN_THREE_STAKE_JUNCTION_KEY,
        name="Three-Stake Junction",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Three enormous pilings rise from a knot of boardwalks, each painted with a different emergency route code. The junction reconnects the western and eastern mire paths, giving gatherers more than one way home when water or wildlife blocks a branch. Siltknife lies south, the survey post west, and the old pump track north."
        ),
        exits={"south": GOBLIN_SILTKNNIFE_BOARDWALK_KEY, "west": GOBLIN_SUNKEN_SURVEY_POST_KEY, "north": GOBLIN_OLD_PUMP_TRACK_KEY},
        enemy_keys=(MARSH_RAZORCRAB.key,),
        tags=("goblin_deep_mire", "junction", "route_connector", "light_combat"),
    ),
    RoomDefinition(
        key=GOBLIN_OLD_PUMP_TRACK_KEY,
        name="Old Pump Track",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A rusted narrow-gauge rail emerges from the mud beside the remains of a pipe trench. Both point north toward a huge tilted frame of cloudy glass rising above the reeds. Goblins have scavenged obvious metal from the old installation but left the buried pumps, pressure pipes, and unstable masonry alone. Crooked Ferry is south and Three-Stake Junction west."
        ),
        exits={"south": GOBLIN_CROOKED_FERRY_KEY, "west": GOBLIN_THREE_STAKE_JUNCTION_KEY, "north": GOBLIN_GREENHOUSE_APPROACH_KEY},
        tags=("goblin_deep_mire", "human_ruin", "industrial_ruin", "glasshouse_route"),
    ),
    RoomDefinition(
        key=GOBLIN_GREENHOUSE_APPROACH_KEY,
        name="Drowned Glasshouse Approach",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A massive greenhouse leans into the swamp ahead, its iron ribs still holding hundreds of cloudy glass panes above a foundation sunk unevenly into peat. A stone plaque beside the entrance identifies it as an early Human acclimation project: an attempt to grow familiar medicinal plants in Astralis soil. A later line, cut much more crudely, records abandonment after repeated flooding and pump failure. The Old Pump Track leads south."
        ),
        exits={"south": GOBLIN_OLD_PUMP_TRACK_KEY, "north": GOBLIN_GREENHOUSE_VESTIBULE_KEY},
        tags=("goblin_deep_mire", "alchemy_dungeon", "human_ruin", "greenhouse", "puzzle"),
    ),
    RoomDefinition(
        key=GOBLIN_GREENHOUSE_VESTIBULE_KEY,
        name="Broken Glasshouse Vestibule",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "The greenhouse entry chamber is ankle-deep in brown water. Cracked specimen cabinets line one wall beside a corroded diagram of the old irrigation system. North, the main cultivation hall is visibly deeper underwater. East, a maintenance door opens into the pump gallery. The approach is south."
        ),
        exits={"south": GOBLIN_GREENHOUSE_APPROACH_KEY, "north": GOBLIN_GREENHOUSE_FLOODED_HALL_KEY, "east": GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY},
        tags=("goblin_deep_mire", "alchemy_dungeon", "human_ruin", "puzzle_clue"),
    ),
    RoomDefinition(
        key=GOBLIN_GREENHOUSE_FLOODED_HALL_KEY,
        name="Flooded Cultivation Hall",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Long planting tables vanish beneath opaque water between rows of iron supports. Old labels hang from wires over empty beds, and collapsed trellises make the flooded floor difficult to read. A glass door at the north end leads into a brighter conservatory but its lower frame is jammed by water pressure and debris. The vestibule is south; the pump gallery can be reached east along a maintenance ledge."
        ),
        exits={"south": GOBLIN_GREENHOUSE_VESTIBULE_KEY, "east": GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY, "north": GOBLIN_GREENHOUSE_CONSERVATORY_KEY},
        enemy_keys=(GLASSHOUSE_MOLDLING.key,),
        tags=("goblin_deep_mire", "alchemy_dungeon", "flooded", "puzzle_gate"),
    ),
    RoomDefinition(
        key=GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY,
        name="Pump Gallery",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Three enormous hand valves stand above a brick sump: blue-painted intake, red-painted return, and black-painted drain. Most paint has flaked away, but arrows on a surviving pipe map still show blue water entering the beds, red water circulating back through them, and black water leaving toward a low drainage channel. The vestibule is west and the flooded hall south."
        ),
        exits={"west": GOBLIN_GREENHOUSE_VESTIBULE_KEY, "south": GOBLIN_GREENHOUSE_FLOODED_HALL_KEY},
        tags=("goblin_deep_mire", "alchemy_dungeon", "human_ruin", "environmental_puzzle", "pump_room"),
    ),
    RoomDefinition(
        key=GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
        name="Glassroot Conservatory",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "The final chamber is a high glass conservatory built around raised stone beds. Most plants are long dead, but pale roots have grown through cracked ceramic trays and into the mineral-rich foundation itself. Overhead shade louvers remain closed, leaving the surviving growth thin and colorless. A manual chain hangs beside the north wall. The cultivation hall is south."
        ),
        exits={"south": GOBLIN_GREENHOUSE_FLOODED_HALL_KEY},
        tags=("goblin_deep_mire", "alchemy_dungeon", "human_ruin", "environmental_puzzle", "rare_reagent"),
    ),
)


# ---------------------------------------------------------------------------
# Slightly higher beginner Alchemy materials and recipes
# ---------------------------------------------------------------------------

BOGMINT_LEAF = ItemDefinition(
    "bogmint_leaf",
    "Bogmint Leaf",
    "A cool, sharp-scented marsh leaf used by Goblin alchemists to stabilize restorative mixtures.",
    "herb",
    tier=2,
)
FEN_RESIN = ItemDefinition(
    "fen_resin",
    "Fen Resin",
    "Amber-black resin collected from deep-mire trees; sticky, aromatic, and useful in salves.",
    "alchemical_reagent",
    tier=2,
)
MIRECAP_SPORES = ItemDefinition(
    "mirecap_spores",
    "Mirecap Spores",
    "Fine spores brushed from bell-shaped marsh fungi and dried for controlled alchemical use.",
    "alchemical_reagent",
    tier=2,
)
GLASSROOT_SHARD = ItemDefinition(
    "glassroot_shard",
    "Glassroot Shard",
    "A translucent mineral-fed root fragment from the drowned Human glasshouse, prized for clarity-focused mixtures.",
    "alchemical_reagent",
    tier=2,
)

MIREGLASS_TONIC = ItemDefinition(
    "mireglass_tonic",
    "Mireglass Tonic",
    "A cool green Goblin restorative sharpened with Bogmint.",
    "consumable",
    consumable=ConsumableEffect(use_mode="drink", heal_hp=22, effect_tags=("healing", "goblin_alchemy")),
    tier=2,
)
FEN_RESIN_SALVE = ItemDefinition(
    "fen_resin_salve",
    "Fen Resin Salve",
    "A sticky medicinal salve that smells strongly of resin and crushed Greenleaf.",
    "consumable",
    consumable=ConsumableEffect(use_mode="apply", heal_hp=12, effect_tags=("healing", "salve")),
    tier=2,
)
GLASSROOT_FOCUS_DRAUGHT = ItemDefinition(
    "glassroot_focus_draught",
    "Glassroot Focus Draught",
    "A pale, faintly opalescent draught made from Glassroot and dried Mirecap spores.",
    "consumable",
    consumable=ConsumableEffect(
        use_mode="drink",
        heal_hp=4,
        temporary_stat_bonuses=CharacterStats(mind=1),
        duration_ticks=60,
        effect_tags=("focus", "goblin_alchemy"),
    ),
    tier=2,
)

DEEP_MIRE_ITEMS: tuple[ItemDefinition, ...] = (
    BOGMINT_LEAF,
    FEN_RESIN,
    MIRECAP_SPORES,
    GLASSROOT_SHARD,
    MIREGLASS_TONIC,
    FEN_RESIN_SALVE,
    GLASSROOT_FOCUS_DRAUGHT,
)

DEEP_MIRE_ALCHEMY_RECIPES: tuple[CraftingRecipe, ...] = (
    CraftingRecipe(
        key="brew_mireglass_tonic",
        trade_skill_key="alchemy",
        output_item_key=MIREGLASS_TONIC.key,
        minimum_skill=5,
        high_skill_quality_threshold=30,
        materials=(MaterialRequirement(BOGMINT_LEAF.key, 2), MaterialRequirement("spring_water", 1)),
        station_key="mortar_and_pestle",
        description="Crush Bogmint with clean water into a stronger beginner restorative.",
        design_status="goblin_deep_mire_alchemy",
    ),
    CraftingRecipe(
        key="prepare_fen_resin_salve",
        trade_skill_key="alchemy",
        output_item_key=FEN_RESIN_SALVE.key,
        minimum_skill=8,
        high_skill_quality_threshold=35,
        materials=(MaterialRequirement(FEN_RESIN.key, 1), MaterialRequirement("greenleaf", 1)),
        station_key="alchemy_table",
        description="Work Fen Resin and Greenleaf into a portable medicinal salve.",
        design_status="goblin_deep_mire_alchemy",
    ),
    CraftingRecipe(
        key="brew_glassroot_focus_draught",
        trade_skill_key="alchemy",
        output_item_key=GLASSROOT_FOCUS_DRAUGHT.key,
        minimum_skill=12,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement(GLASSROOT_SHARD.key, 1),
            MaterialRequirement(MIRECAP_SPORES.key, 1),
            MaterialRequirement("spring_water", 1),
        ),
        station_key="alchemy_table",
        description="Suspend prepared Glassroot and Mirecap spores in clean water to make a focus draught.",
        design_status="goblin_glasshouse_alchemy",
    ),
)


# ---------------------------------------------------------------------------
# Gathering nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DeepMireNodeDefinition:
    key: str
    room_key: str
    name: str
    aliases: tuple[str, ...]
    output_item_key: str
    minimum_herbalism: int
    maximum_uses: int = 3
    respawn_world_hours: int = 2
    spring_floodpick: bool = False
    required_flag: str | None = None

    def matches(self, target: str) -> bool:
        normalized = target.strip().lower()
        names = {self.name.lower(), self.key.replace("_", " "), *(alias.lower() for alias in self.aliases)}
        return normalized in names


@dataclass(slots=True)
class DeepMireNodeState:
    definition: DeepMireNodeDefinition
    remaining_uses: int
    depleted_at_hour: int | None = None

    def refresh(self, total_hour: int) -> None:
        if self.remaining_uses > 0 or self.depleted_at_hour is None:
            return
        if total_hour - self.depleted_at_hour >= self.definition.respawn_world_hours:
            self.remaining_uses = self.definition.maximum_uses
            self.depleted_at_hour = None


DEEP_MIRE_NODES: tuple[DeepMireNodeDefinition, ...] = (
    DeepMireNodeDefinition(
        "siltknife_bogmint",
        GOBLIN_SILTKNNIFE_BOARDWALK_KEY,
        "Siltknife Bogmint",
        ("bogmint", "bogmint leaf", "mint", "herbs"),
        BOGMINT_LEAF.key,
        6,
    ),
    DeepMireNodeDefinition(
        "resin_fen_drips",
        GOBLIN_RESIN_FEN_KEY,
        "Fen Resin Drips",
        ("resin", "fen resin", "resin drips", "tree resin"),
        FEN_RESIN.key,
        7,
    ),
    DeepMireNodeDefinition(
        "toadbell_mirecaps",
        GOBLIN_TOADBELL_HOLLOW_KEY,
        "Toadbell Mirecaps",
        ("mirecaps", "mirecap", "spores", "mushrooms", "fungi"),
        MIRECAP_SPORES.key,
        8,
    ),
    # The spring node's output is substituted at gather time according to the
    # clan currently holding the Floodpick claim.
    DeepMireNodeDefinition(
        "sourreed_floodpick_patch",
        GOBLIN_SOURREED_TERRACE_KEY,
        "Floodpick Herb Patch",
        ("floodpick patch", "seasonal herbs", "claimed herbs", "herb patch"),
        BOGMINT_LEAF.key,
        6,
        maximum_uses=2,
        spring_floodpick=True,
    ),
    DeepMireNodeDefinition(
        "glassroot_bed",
        GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
        "Glassroot Bed",
        ("glassroot", "glassroot bed", "pale roots", "roots"),
        GLASSROOT_SHARD.key,
        10,
        maximum_uses=2,
        respawn_world_hours=4,
        required_flag=GREENHOUSE_LOUVERS_FLAG,
    ),
)

FLOODPICK_OUTPUTS = {
    FLOODPICK_MIREHOOK: BOGMINT_LEAF.key,
    FLOODPICK_COPPERCAP: MIRECAP_SPORES.key,
    FLOODPICK_TINLEDGER: FEN_RESIN.key,
}


class DeepMireGatheringService:
    def __init__(self, calendar_provider: Callable[[], AstralisCalendarDate] | None = None) -> None:
        self.calendar_provider = calendar_provider or (lambda: ASTRALIS_CLOCK.now().calendar)
        self.states: dict[str, DeepMireNodeState] = {}
        self.reset()

    def reset(self) -> None:
        self.states = {node.key: DeepMireNodeState(node, node.maximum_uses) for node in DEEP_MIRE_NODES}

    def nodes_in_room(self, room_key: str, flags: frozenset[str] = frozenset()) -> tuple[DeepMireNodeState, ...]:
        calendar = self.calendar_provider()
        total_hour = ASTRALIS_CLOCK.now().total_hours
        result: list[DeepMireNodeState] = []
        for state in self.states.values():
            definition = state.definition
            if definition.room_key != room_key:
                continue
            if definition.spring_floodpick and calendar.season_key != "spring":
                continue
            if definition.required_flag and definition.required_flag not in flags:
                continue
            state.refresh(total_hour)
            result.append(state)
        return tuple(result)

    def resolve(self, room_key: str, target: str, flags: frozenset[str] = frozenset()) -> DeepMireNodeState | None:
        for state in self.nodes_in_room(room_key, flags):
            if state.definition.matches(target):
                return state
        return None

    def output_for(self, state: DeepMireNodeState) -> str:
        if not state.definition.spring_floodpick:
            return state.definition.output_item_key
        controller = floodpick_controller(self.calendar_provider())
        return FLOODPICK_OUTPUTS.get(controller or "", state.definition.output_item_key)

    def gather(self, database, character_id: int, state: DeepMireNodeState) -> tuple[bool, str]:
        total_hour = ASTRALIS_CLOCK.now().total_hours
        state.refresh(total_hour)
        if state.remaining_uses <= 0:
            return False, (
                f"The {state.definition.name} has been worked over for now. Deep-mire gatherers normally give a patch about "
                f"{state.definition.respawn_world_hours} Astralis hours before cutting it again."
            )
        skill = trade_skill_value(database, character_id, "herbalism")
        if skill < state.definition.minimum_herbalism:
            return False, (
                f"Harvesting the {state.definition.name} cleanly requires herbalism skill "
                f"{state.definition.minimum_herbalism}; yours is {skill}."
            )
        output_key = self.output_for(state)
        database.add_item(character_id, output_key, 1)
        database.record_trade_skill_use(character_id, "herbalism", 1)
        state.remaining_uses -= 1
        if state.remaining_uses <= 0:
            state.depleted_at_hour = total_hour
        return True, output_key


GOBLIN_DEEP_MIRE_GATHERING = DeepMireGatheringService()


# ---------------------------------------------------------------------------
# First real alchemy dungeon: The Drowned Glasshouse
# ---------------------------------------------------------------------------

GOBLIN_DROWNED_GLASSHOUSE_QUEST = QuestDefinition(
    key="goblin_drowned_glasshouse",
    name="The Drowned Glasshouse",
    style="discovery",
    description=(
        "An early Human medicinal greenhouse is sinking into the mire. Its old pump diagram and surviving shade controls provide a way into the flooded cultivation rooms without forcing the structure."
    ),
    objective_steps=(
        ("study_plaque", "Study the old Human plaque at the glasshouse approach."),
        ("read_pipe_map", "Find the pump gallery and EXAMINE PIPE MAP to understand the old water circuit."),
        ("drain_hall", "Use the pipe diagram to choose the valve that drains water out of the cultivation beds."),
        ("open_louvers", "Reach the conservatory and OPEN LOUVERS so the surviving root bed receives light."),
        ("harvest_glassroot", "HARVEST GLASSROOT from the revived bed."),
        ("complete", "You recovered Glassroot by understanding and reusing the failed Human greenhouse systems."),
    ),
)


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)


def _start_glasshouse_quest(session) -> None:
    if session.character is None or _quest(session) is not None:
        return
    session.database.start_quest(session.character.id, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key, "study_plaque")


def _advance_glasshouse(session, step: str) -> None:
    if session.character is None:
        return
    quest = _quest(session)
    if quest and quest.get("status") == "active":
        session.database.advance_quest(session.character.id, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key, step)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = (), search: str = "", touch: str = "", listen: str = "") -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
    )


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _day(text: str) -> DescriptionLayer:
    return DescriptionLayer("deep_mire_day", text, priority=40, condition=ViewCondition(time_buckets=("day",)))


def _night(text: str) -> DescriptionLayer:
    return DescriptionLayer("deep_mire_night", text, priority=50, condition=ViewCondition(time_buckets=("night",)))


def _rain(text: str) -> DescriptionLayer:
    return DescriptionLayer("deep_mire_rain", text, priority=60, condition=ViewCondition(weather=("rain", "storm")))


def _basic_aug(room_key: str) -> RoomAugmentation:
    feature_by_room = {
        GOBLIN_BLACKREED_GATE_KEY: _feature(
            "deep_route_markers", "Deep-Route Markers", "black reed bundles and layered route tags",
            "The tags combine flood depth, clan maintenance marks, and danger ratings. None says DO NOT ENTER; they say, more usefully, what kind of mistake is likely beyond each branch.",
            aliases=("markers", "tags", "black reeds"),
        ),
        GOBLIN_SILTKNNIFE_BOARDWALK_KEY: _feature(
            "knife_depth_marks", "Knife Depth Marks", "broken blades used as flood gauges",
            "Each old blade is driven at a measured height. Goblins read which blades are submerged to judge whether the lower walkways are still usable.",
            aliases=("knives", "depth marks", "blades"),
        ),
        GOBLIN_SOURREED_TERRACE_KEY: _feature(
            "claim_stakes", "Claim Stakes", "competing family stakes at the herb terrace",
            "An old iron Mirehook stake sits deeper in the peat than a newer Coppercap tag. Tinledger tally scratches record several seasons of arguments without pretending that age alone settles who maintained the bed.",
            aliases=("stakes", "claims", "claim markers", "tags"),
            search="Beneath spring silt, the oldest intact mark is Mirehook iron; the freshest maintenance cuts are Coppercap. The evidence explains the argument rather than solving it.",
        ),
        GOBLIN_RESIN_FEN_KEY: _feature(
            "resin_cups", "Resin Cups", "improvised collectors wired beneath bark cuts",
            "Each cup is positioned to collect resin without girdling the tree. Several carry dates showing when a cut should be left alone to heal.",
            aliases=("cups", "resin", "trees"),
        ),
        GOBLIN_CROOKED_FERRY_KEY: _feature(
            "crooked_raft", "Crooked Ferry Raft", "a deliberately counterweighted swamp raft",
            "What looks like bad construction is compensation: the submerged iron counterweight makes the raft level once two loaded herb baskets are placed on its high side.",
            aliases=("raft", "ferry", "counterweight"),
        ),
        GOBLIN_TOADBELL_HOLLOW_KEY: _feature(
            "toadbell_fungi", "Toadbell Fungi", "bell-shaped marsh fungi marked for spore gathering",
            "White-thread tags identify mature caps whose spores can be brushed without pulling the fruiting body from the mycelium.",
            aliases=("toadbells", "fungi", "mirecaps", "mushrooms"),
        ),
        GOBLIN_SUNKEN_SURVEY_POST_KEY: _feature(
            "sunken_cabinets", "Sunken Survey Cabinets", "Human measuring equipment beneath the waterline",
            "Warped drawers still hold ceramic tags, brass rulers, and broken glass tubes. The surviving Human marks repeatedly mention soil acidity and pump depth.",
            aliases=("cabinets", "survey gear", "human equipment"),
        ),
        GOBLIN_THREE_STAKE_JUNCTION_KEY: _feature(
            "emergency_stakes", "Emergency Stakes", "three coded pilings for alternate routes",
            "The paint codes describe three different ways back toward Junk City if floodwater, a broken boardwalk, or an animal blocks the usual path.",
            aliases=("stakes", "pilings", "route codes"),
        ),
        GOBLIN_OLD_PUMP_TRACK_KEY: _feature(
            "buried_pipes", "Buried Pump Pipes", "old Human irrigation mains surfacing through the mud",
            "Blue, red, and black paint survives in protected seams. The same colors continue toward the glasshouse, suggesting separate intake, return, and drainage circuits.",
            aliases=("pipes", "pump pipes", "rails", "track"),
        ),
    }
    feature = feature_by_room.get(room_key)
    return RoomAugmentation(
        features=(feature,) if feature else (),
        description_layers=(
            _day("Daylight turns standing water into hard glare and makes every Goblin route mark easier to read."),
            _night("At night the deeper mire becomes a web of hooded route lamps, reflected markers, and large stretches of darkness between them."),
            _rain("Rain raises the smell of peat and resin while every plank, glass shard, and sheet-metal patch begins sounding at once."),
        ),
    )


def goblin_deep_mire_augmentations() -> dict[str, RoomAugmentation]:
    augmentations = {room_key: _basic_aug(room_key) for room_key in GOBLIN_DEEP_MIRE_ROOM_KEYS}

    augmentations[GOBLIN_GREENHOUSE_APPROACH_KEY] = RoomAugmentation(
        features=(
            _feature(
                "human_acclimation_plaque", "Human Acclimation Plaque", "a weathered stone project plaque",
                "The old inscription describes a medicinal acclimation greenhouse built by early Human settlers trying to reproduce familiar remedies in Astralis soil. Later chisel marks record flood losses, pump failures, and eventual abandonment.",
                aliases=("plaque", "human plaque", "project plaque", "inscription"),
                search="A tiny maintenance notation points visitors toward the interior irrigation diagram before operating any pump controls.",
            ),
            _feature(
                "tilted_glasshouse", "Tilted Glasshouse", "a huge iron-and-glass structure sinking into peat",
                "The building failed structurally but not completely. Enough iron ribs remain sound that a careful explorer can use the original corridors rather than breaking through walls.",
                aliases=("glasshouse", "greenhouse", "structure"),
            ),
        ),
        description_layers=(
            _day("Sunlight flashes across hundreds of mismatched surviving panes, making the ruined greenhouse look briefly whole from the right angle."),
            _night("Moonlight and route lamps turn the greenhouse frame into a black lattice over dim water."),
            _rain("Rain sheets down the tilted panes and pours from one broken gutter directly into the swamp."),
        ),
    )
    augmentations[GOBLIN_GREENHOUSE_VESTIBULE_KEY] = RoomAugmentation(
        features=(
            _feature(
                "irrigation_diagram", "Irrigation Diagram", "a corroded overview of the greenhouse water circuit",
                "The overview sends maintenance workers east to the pump gallery for detailed valve instructions. Three circuit colors repeat everywhere: blue, red, and black.",
                aliases=("diagram", "water diagram", "irrigation map"),
            ),
            _feature(
                "specimen_cabinets", "Specimen Cabinets", "cracked Human plant cabinets",
                "Most labels are unreadable, but surviving cards compare Earth medicinal plants with Astralis analogues. Several notes complain that swamp minerals changed root structure in unexpected ways.",
                aliases=("cabinets", "specimens", "plant cabinets"),
            ),
        ),
        description_layers=(_day("Cloudy daylight filters through algae-streaked glass."), _night("The vestibule is lit mainly by swamp glow and reflected route lamps."), _rain("Fresh rainwater threads down the inside walls.")),
    )
    augmentations[GOBLIN_GREENHOUSE_FLOODED_HALL_KEY] = RoomAugmentation(
        exit_overrides=(
            _exit("south", GOBLIN_GREENHOUSE_VESTIBULE_KEY, "Broken Vestibule", "You pick your way south through the shallowest flooded aisle."),
            _exit("east", GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY, "Pump Gallery", "You use the narrow maintenance ledge east to the old pump controls."),
            ExitDefinition(
                direction="north",
                destination_key=GOBLIN_GREENHOUSE_CONSERVATORY_KEY,
                name="Glassroot Conservatory",
                travel_text="With the water pressure relieved, you pull the north glass door free and enter the conservatory.",
                failure_text="Floodwater and debris still pin the north glass door shut. The pump system was built to move this water somewhere.",
                condition=ViewCondition(required_flags=(GREENHOUSE_DRAINED_FLAG,)),
                hidden_when_unavailable=False,
            ),
        ),
        features=(
            _feature(
                "flooded_beds", "Flooded Planting Beds", "old planting tables beneath brown water",
                "The water is not merely standing rain. A faint current moves toward a floor grate, suggesting the original drainage route may still be usable if the correct valve is opened.",
                aliases=("beds", "planting beds", "water", "floor grate"),
            ),
        ),
        description_layers=(_day("Light from the roof makes submerged trellises visible just below the surface."), _night("The flooded hall reflects every small light twice, making distances hard to judge."), _rain("Rain adds a constant hiss to the water already trapped inside.")),
    )
    augmentations[GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY] = RoomAugmentation(
        features=(
            _feature(
                "pipe_map", "Pipe Map", "a surviving color-coded pump diagram",
                "Blue arrows point from the swamp intake into the cultivation beds. Red arrows loop water back through the beds. Black arrows leave the building through a low drain channel. If the goal is to lower the water, the black circuit is the only one that actually goes out.",
                aliases=("map", "pipe map", "pump map", "diagram"),
                search="A maintenance note warns that opening intake and return valves during a flood only adds pressure to the cultivation hall.",
            ),
            _feature(
                "three_valves", "Three Hand Valves", "blue, red, and black pump valves",
                "Blue is labeled INTAKE, red RETURN, black DRAIN. All three still move, though each takes both hands and patience.",
                aliases=("valves", "blue valve", "red valve", "black valve", "hand valves"),
            ),
        ),
        description_layers=(_day("Thin light catches mineral deposits on the old pipes."), _night("The colored valve paint is almost impossible to distinguish without examining it closely."), _rain("The sump echoes with water arriving from somewhere above.")),
    )
    augmentations[GOBLIN_GREENHOUSE_CONSERVATORY_KEY] = RoomAugmentation(
        features=(
            _feature(
                "shade_louvers", "Shade Louvers", "closed overhead slats with a manual chain",
                "The louvers were meant to protect delicate transplants from harsh light. After centuries closed, the surviving pale roots below are starved of it. The manual chain still connects to the slat mechanism.",
                aliases=("louvers", "shades", "shade louvers", "chain"),
            ),
            _feature(
                "glassroot_bed_feature", "Glassroot Bed", "mineral-fed pale roots in cracked ceramic beds",
                "The roots have incorporated glittering mineral deposits from the sinking foundation. They are alive, but their useful translucent growth is concentrated where light can reach them.",
                aliases=("glassroot", "root bed", "pale roots", "roots"),
            ),
        ),
        description_layers=(
            _day("Diffuse daylight presses against the closed louvers overhead."),
            _night("The conservatory is almost completely dark beneath the closed shade system."),
            _rain("Rain rattles the high glass roof while droplets trace old cracks down the iron ribs."),
            DescriptionLayer(
                "glasshouse_louvers_open",
                "The shade louvers stand open now. A broad wash of light reaches the central beds, and translucent Glassroot growth gleams between the cracked tiles.",
                priority=80,
                condition=ViewCondition(required_flags=(GREENHOUSE_LOUVERS_FLAG,)),
            ),
        ),
    )
    return augmentations


def _patch_mudglass(room: RoomDefinition) -> RoomDefinition:
    exits = dict(room.exits)
    exits["north"] = GOBLIN_BLACKREED_GATE_KEY
    return replace(room, exits=exits)


def _register_items_and_recipes() -> None:
    for item in DEEP_MIRE_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for recipe in DEEP_MIRE_ALCHEMY_RECIPES:
        if recipe.key not in crafting.RECIPES_BY_KEY:
            crafting.ALCHEMY_RECIPES = crafting.ALCHEMY_RECIPES + (recipe,)
            crafting.ALL_RECIPES = crafting.ALL_RECIPES + (recipe,)
        crafting.ALCHEMY_RECIPES_BY_KEY[recipe.key] = recipe
        crafting.RECIPES_BY_KEY[recipe.key] = recipe


def _merge_augmentations(world_service) -> None:
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return

    mudglass = augmentations.get(GOBLIN_MUDGLASS_CROSSING_KEY, RoomAugmentation())
    north_exit = _exit(
        "north",
        GOBLIN_BLACKREED_GATE_KEY,
        "Blackreed Gate",
        "You pass beneath the black-reed warning bundles and leave the maintained beginner routes for the deeper mire.",
    )
    overrides = tuple(exit_def for exit_def in mudglass.exit_overrides if exit_def.direction != "north") + (north_exit,)
    augmentations[GOBLIN_MUDGLASS_CROSSING_KEY] = replace(mudglass, exit_overrides=overrides)
    augmentations.update(goblin_deep_mire_augmentations())

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(GOBLIN_MUDGLASS_CROSSING_KEY, None)
        for room_key in GOBLIN_DEEP_MIRE_ROOM_KEYS:
            cache.pop(room_key, None)


def install_goblin_deep_mire_content(world_service=None) -> None:
    """Register the deeper Goblin swamp, alchemy materials, and glasshouse."""
    # Do not merge beginner-swamp augmentations here; the live server already
    # installs them and then applies its authoritative First Piling access gate.
    install_goblin_swamp_content()

    mudglass = legacy_world.ROOMS_BY_KEY.get(GOBLIN_MUDGLASS_CROSSING_KEY)
    replacements: dict[str, RoomDefinition] = {}
    if mudglass is not None:
        replacements[GOBLIN_MUDGLASS_CROSSING_KEY] = _patch_mudglass(mudglass)

    known = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in GOBLIN_DEEP_MIRE_ROOMS if room.key not in known)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    replacements.update({room.key: room for room in GOBLIN_DEEP_MIRE_ROOMS})
    legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY.update(replacements)

    for enemy in (FEN_LEECH_CLUSTER, MARSH_RAZORCRAB, MIRE_WASP_CLOUD, GLASSHOUSE_MOLDLING):
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    _register_items_and_recipes()

    if GOBLIN_DROWNED_GLASSHOUSE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GOBLIN_DROWNED_GLASSHOUSE_QUEST,)
    quests.QUESTS_BY_KEY[GOBLIN_DROWNED_GLASSHOUSE_QUEST.key] = GOBLIN_DROWNED_GLASSHOUSE_QUEST

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        _merge_augmentations(world_service)


def _target(command: str) -> str:
    parts = command.strip().split(maxsplit=1)
    return parts[1].strip().lower() if len(parts) == 2 else ""


async def _handle_deep_gathering(session, normalized: str) -> bool:
    if session.character is None or session.character.current_room not in GOBLIN_DEEP_MIRE_ROOM_KEYS:
        return False
    first = normalized.split(maxsplit=1)[0] if normalized else ""
    if first not in {"gather", "harvest", "herbalism", "pick", "collect"}:
        return False

    flags = session.database.list_flags(session.character.id)
    target = _target(normalized)
    nodes = GOBLIN_DEEP_MIRE_GATHERING.nodes_in_room(session.character.current_room, flags)
    if not target:
        skill = trade_skill_value(session.database, session.character.id, "herbalism")
        await session.send(f"\r\nHerbalism skill: {skill}.\r\n")
        if nodes:
            await session.send("Deep-mire gatherable here: " + ", ".join(node.definition.name for node in nodes) + ".\r\n")
        else:
            await session.send("There is no currently usable alchemical gathering node here.\r\n")
        return True

    node = GOBLIN_DEEP_MIRE_GATHERING.resolve(session.character.current_room, target, flags)
    if node is None:
        if session.character.current_room == GOBLIN_GREENHOUSE_CONSERVATORY_KEY and target in {"glassroot", "glassroot bed", "roots", "pale roots"} and GREENHOUSE_LOUVERS_FLAG not in flags:
            await session.send("\r\nThe surviving roots are too pale and dormant to harvest usefully. The overhead shade louvers are still closed.\r\n")
            return True
        await session.send("\r\nYou do not identify that as a usable alchemical gathering source here.\r\n")
        return True

    success, result = GOBLIN_DEEP_MIRE_GATHERING.gather(session.database, session.character.id, node)
    if not success:
        await session.send("\r\n" + result + "\r\n")
        return True

    item = crafting.ITEMS_BY_KEY.get(result)
    item_name = item.name if item else result
    skill = trade_skill_value(session.database, session.character.id, "herbalism")
    await session.send(f"\r\nYou gather 1x {item_name}. Herbalism improves through use (skill {skill}).\r\n")

    if result == GLASSROOT_SHARD.key:
        flags = session.database.list_flags(session.character.id)
        if GREENHOUSE_GLASSROOT_FLAG not in flags:
            session.database.grant_flag(session.character.id, GREENHOUSE_GLASSROOT_FLAG)
        quest = _quest(session)
        if quest and quest.get("status") == "active" and quest.get("current_step") == "harvest_glassroot":
            session.database.complete_quest(session.character.id, GOBLIN_DROWNED_GLASSHOUSE_QUEST.key)
            await session.send(
                "The translucent root breaks cleanly along a mineral seam. You did not force the ruin open; you made its old systems useful again.\r\n"
                "Quest complete: The Drowned Glasshouse.\r\n"
            )
    return True


async def _handle_glasshouse_puzzle(session, normalized: str) -> bool:
    if session.character is None or session.character.current_room not in GOBLIN_GREENHOUSE_ROOM_KEYS:
        return False
    room = session.character.current_room

    if room == GOBLIN_GREENHOUSE_APPROACH_KEY and normalized in {"examine plaque", "look plaque", "read plaque", "read human plaque", "examine human plaque"}:
        _start_glasshouse_quest(session)
        quest = _quest(session)
        if quest and quest.get("status") == "active" and quest.get("current_step") == "study_plaque":
            _advance_glasshouse(session, "read_pipe_map")
        await session.send(
            "\r\nThe plaque identifies the ruin as an early Human medicinal acclimation project. A maintenance note says irrigation changes must be checked against the interior pipe map before any valve is moved.\r\n"
            "Quest updated: The Drowned Glasshouse. Find and EXAMINE PIPE MAP.\r\n"
        )
        return True

    if room == GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY and normalized in {"examine pipe map", "look pipe map", "read pipe map", "examine map", "read map"}:
        _start_glasshouse_quest(session)
        quest = _quest(session)
        if quest and quest.get("status") == "active" and quest.get("current_step") in {"study_plaque", "read_pipe_map"}:
            _advance_glasshouse(session, "drain_hall")
        await session.send(
            "\r\nBlue arrows bring swamp water IN. Red arrows RETURN water through the beds. Black arrows lead OUT through the low drain. Opening blue or red during a flood would add pressure; black is the only circuit that actually lowers the hall.\r\n"
            "Quest updated: The Drowned Glasshouse. Choose the valve that drains the hall.\r\n"
        )
        return True

    if room == GOBLIN_GREENHOUSE_PUMP_GALLERY_KEY and normalized.startswith("turn ") and "valve" in normalized:
        if "black" in normalized or "drain" in normalized:
            session.database.grant_flag(session.character.id, GREENHOUSE_DRAINED_FLAG)
            quest = _quest(session)
            if quest and quest.get("status") == "active" and quest.get("current_step") in {"study_plaque", "read_pipe_map", "drain_hall"}:
                _advance_glasshouse(session, "open_louvers")
            await session.send(
                "\r\nThe black drain valve resists, then turns with a deep iron groan. Somewhere beneath the cultivation hall, old water begins rushing into a lower channel. The pressure against the north glass door slowly falls.\r\n"
                "Quest updated: The Drowned Glasshouse. Reach the conservatory and OPEN LOUVERS.\r\n"
            )
        elif "blue" in normalized or "intake" in normalized:
            await session.send("\r\nThe blue valve is the intake. The pipe map showed this circuit bringing more swamp water into the cultivation beds; you leave it alone.\r\n")
        elif "red" in normalized or "return" in normalized:
            await session.send("\r\nThe red valve recirculates water through the beds. That would move the flood around, not remove it. You leave it alone.\r\n")
        else:
            await session.send("\r\nThere are three surviving valves: BLUE intake, RED return, and BLACK drain. The pipe map explains where each circuit goes.\r\n")
        return True

    if room == GOBLIN_GREENHOUSE_CONSERVATORY_KEY and normalized in {"open louvers", "pull chain", "use chain", "open shades", "raise louvers"}:
        if GREENHOUSE_DRAINED_FLAG not in session.database.list_flags(session.character.id):
            await session.send("\r\nYou could work the shade controls, but the flooded hall behind you is still the more immediate problem.\r\n")
            return True
        session.database.grant_flag(session.character.id, GREENHOUSE_LOUVERS_FLAG)
        quest = _quest(session)
        if quest and quest.get("status") == "active" and quest.get("current_step") in {"open_louvers", "drain_hall"}:
            _advance_glasshouse(session, "harvest_glassroot")
        await session.send(
            "\r\nYou pull the manual chain. Rust flakes fall, gears skip twice, and then the overhead louvers crawl open. Daylight reaches the central beds and catches in translucent mineral-fed roots.\r\n"
            "Quest updated: The Drowned Glasshouse. HARVEST GLASSROOT.\r\n"
        )
        return True

    return False


def _resolve_deep_recipe(command: str):
    normalized = command.strip().lower().replace("_", " ")
    for prefix in ("brew ", "prepare ", "craft ", "make "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    for recipe in DEEP_MIRE_ALCHEMY_RECIPES:
        output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
        aliases = {recipe.key.replace("_", " "), recipe.output_item_key.replace("_", " ")}
        if output:
            aliases.add(output.name.lower())
        if normalized in aliases:
            return recipe
    return None


async def _handle_deep_alchemy(session, command: str) -> bool:
    if session.character is None or session.character.current_room not in GOBLIN_DEEP_MIRE_ROOM_KEYS:
        return False
    normalized = command.strip().lower()
    if normalized == "alchemy":
        skill = trade_skill_value(session.database, session.character.id, "alchemy")
        await session.send("\r\n--- Deep-Mire Alchemy ---\r\n")
        await session.send(f"Alchemy skill: {skill}.\r\n")
        for recipe in DEEP_MIRE_ALCHEMY_RECIPES:
            output = crafting.ITEMS_BY_KEY[recipe.output_item_key]
            materials = ", ".join(f"{req.quantity}x {req.item_key}" for req in recipe.materials)
            await session.send(f"  {output.name} — skill {recipe.minimum_skill}; {materials}; station {recipe.station_key}.\r\n")
        await session.send("The Glassroot Conservatory provides an old alchemy table once you reach it; the beginner Apothecary Blind remains the safest general field bench.\r\n")
        return True

    if not (normalized.startswith("brew ") or normalized.startswith("prepare ") or normalized.startswith("craft ") or normalized.startswith("make ")):
        return False
    recipe = _resolve_deep_recipe(command)
    if recipe is None:
        return False
    if session.character.current_room != GOBLIN_GREENHOUSE_CONSERVATORY_KEY:
        await session.send("\r\nThese deeper-mire preparations need an alchemy workspace. The surviving table in the Glassroot Conservatory can handle them.\r\n")
        return True
    result = craft_recipe(session.database, session.character.id, recipe.key, station_key=recipe.station_key)
    if not result.success:
        await session.send("\r\n" + result.message + "\r\n")
        return True
    item = crafting.ITEMS_BY_KEY[result.output_item_key]
    skill = trade_skill_value(session.database, session.character.id, "alchemy")
    await session.send(f"\r\nYou prepare {result.output_quantity}x {item.name}. Alchemy improves through use (skill {skill}).\r\n")
    return True


async def _show_floodpick_status(session) -> None:
    if session.character is None or session.character.current_room not in {GOBLIN_SOURREED_TERRACE_KEY, GOBLIN_BLACKREED_GATE_KEY, GOBLIN_MUDGLASS_CROSSING_KEY}:
        return
    await session.send("\r\n" + floodpick_control_text() + "\r\n")


def install_goblin_deep_mire_runtime(player_session_class, world_service) -> None:
    install_goblin_deep_mire_content(world_service)
    if getattr(player_session_class, "_goblin_deep_mire_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = player_session_class.move_character
    previous_show_current_room = player_session_class.show_current_room

    async def show_current_room(self) -> None:
        await previous_show_current_room(self)
        await _show_floodpick_status(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        if self.character is None:
            return
        after = self.character.current_room
        if before == after:
            return
        if after in GOBLIN_DEEP_MIRE_ROOM_KEYS and self.character.race == "goblin":
            flags = self.database.list_flags(self.character.id)
            if GOBLIN_DEEP_MIRE_ENTERED_FLAG not in flags:
                self.database.grant_flag(self.character.id, GOBLIN_DEEP_MIRE_ENTERED_FLAG)
                await self.send(
                    "\r\nThe route markings become less instructional here. The deeper mire is still low-level country, but it expects you to read water, wildlife, claims, and gathering signs for yourself.\r\n"
                    "HERBALISM shows usable local reagents. The old glass structure to the north is explorable rather than a boss arena.\r\n"
                )
        if after == GOBLIN_GREENHOUSE_APPROACH_KEY:
            _start_glasshouse_quest(self)
            quest = _quest(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "study_plaque":
                await self.send("\r\nDiscovery quest: The Drowned Glasshouse. Start by examining the Human project plaque.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"floodpick", "route control", "claims"} and self.character.current_room in GOBLIN_DEEP_MIRE_ROOM_KEYS:
            await self.send("\r\n" + floodpick_control_text() + "\r\n")
            return
        if await _handle_glasshouse_puzzle(self, normalized):
            return
        if await _handle_deep_gathering(self, normalized):
            return
        if await _handle_deep_alchemy(self, command):
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

        if normalized in {"help", "?"} and self.character.current_room in GOBLIN_DEEP_MIRE_ROOM_KEYS:
            await self.send(
                "Deep-mire commands: HERBALISM [target], GATHER/HARVEST <target>, FLOODPICK, ALCHEMY. "
                "Glasshouse exploration also uses EXAMINE, READ, TURN <valve>, OPEN LOUVERS, and HARVEST GLASSROOT.\r\n"
            )

    player_session_class.show_current_room = show_current_room
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_deep_mire_runtime_installed = True
