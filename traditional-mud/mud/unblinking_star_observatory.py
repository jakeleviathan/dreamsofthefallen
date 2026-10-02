from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.frontier_convergence import ASHCROSS_MILESTONE_KEY
from mud.quests import QuestDefinition
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import NpcDefinition, RoomDefinition


STARFALL_REGION_KEY = "starfall_scar"
OBSERVATORY_REGION_KEY = "unblinking_observatory"

STARFALL_APPROACH_KEY = "starfall_scar_approach"
STARFALL_GLASS_FLATS_KEY = "starfall_glass_rain_flats"
STARFALL_MERIDIAN_KEY = "starfall_fallen_meridian"
STARFALL_ORCHARD_KEY = "starfall_black_orchard"
STARFALL_MIRROR_SINK_KEY = "starfall_mirror_sink"
STARFALL_CAMP_KEY = "starfall_witness_camp"
STARFALL_CRATER_RIM_KEY = "starfall_crater_rim"
STARFALL_IMPACT_TERRACE_KEY = "starfall_impact_terrace"
STARFALL_CAUSEWAY_KEY = "starfall_buried_causeway"
STARFALL_STEPS_KEY = "starfall_observatory_steps"

OBS_ENTRY_KEY = "unblinking_entry_rotunda"
OBS_LENS_GALLERY_KEY = "unblinking_lens_gallery"
OBS_ARCHIVE_KEY = "unblinking_archive_of_angles"
OBS_DORMITORY_KEY = "unblinking_sleepless_dormitory"
OBS_GRAVITY_WELL_KEY = "unblinking_gravity_well"
OBS_CHOIR_KEY = "unblinking_choir_of_measures"
OBS_TRANSIT_KEY = "unblinking_transit_gallery"
OBS_MAINTENANCE_KEY = "unblinking_maintenance_spine"
OBS_KEEPER_HALL_KEY = "unblinking_sealkeeper_hall"
OBS_THREE_HAND_GATE_KEY = "unblinking_three_hand_gate"
OBS_INVERSION_STAIR_KEY = "unblinking_inversion_stair"
OBS_NULL_ORRERY_KEY = "unblinking_null_orrery"
OBS_DREAM_RELAY_KEY = "unblinking_dreaming_relay"
OBS_PLANETARIUM_KEY = "unblinking_silent_planetarium"
OBS_APHELION_BRIDGE_KEY = "unblinking_aphelion_bridge"
OBS_LAST_COMMAND_KEY = "unblinking_last_command"
OBS_THRESHOLD_KEY = "unblinking_threshold_ring"
OBS_APERTURE_KEY = "unblinking_aperture"
OBS_SEAL_ENGINE_KEY = "unblinking_seal_engine"

STARFALL_ROOM_KEYS = (
    STARFALL_APPROACH_KEY,
    STARFALL_GLASS_FLATS_KEY,
    STARFALL_MERIDIAN_KEY,
    STARFALL_ORCHARD_KEY,
    STARFALL_MIRROR_SINK_KEY,
    STARFALL_CAMP_KEY,
    STARFALL_CRATER_RIM_KEY,
    STARFALL_IMPACT_TERRACE_KEY,
    STARFALL_CAUSEWAY_KEY,
    STARFALL_STEPS_KEY,
)
OBSERVATORY_ROOM_KEYS = (
    OBS_ENTRY_KEY,
    OBS_LENS_GALLERY_KEY,
    OBS_ARCHIVE_KEY,
    OBS_DORMITORY_KEY,
    OBS_GRAVITY_WELL_KEY,
    OBS_CHOIR_KEY,
    OBS_TRANSIT_KEY,
    OBS_MAINTENANCE_KEY,
    OBS_KEEPER_HALL_KEY,
    OBS_THREE_HAND_GATE_KEY,
    OBS_INVERSION_STAIR_KEY,
    OBS_NULL_ORRERY_KEY,
    OBS_DREAM_RELAY_KEY,
    OBS_PLANETARIUM_KEY,
    OBS_APHELION_BRIDGE_KEY,
    OBS_LAST_COMMAND_KEY,
    OBS_THRESHOLD_KEY,
    OBS_APERTURE_KEY,
    OBS_SEAL_ENGINE_KEY,
)
UNBLINKING_ROOM_KEYS = STARFALL_ROOM_KEYS + OBSERVATORY_ROOM_KEYS

QUEST_KEY = "unblinking_star_the_star_that_looked_back"
COMPLETE_FLAG = "unblinking_star_first_clear"
SCAR_SURVEYED_FLAG = "unblinking_star_scar_surveyed"
LENSES_ALIGNED_FLAG = "unblinking_star_lenses_aligned"
CORE_GATE_FLAG = "unblinking_star_core_gate_synced"
ORRERY_ALIGNED_FLAG = "unblinking_star_orrery_aligned"
BOSS_DEFEATED_FLAG = "unblinking_star_fragment_defeated"
APERTURE_SEALED_FLAG = "unblinking_star_aperture_sealed"
DREAM_TOUCHED_FLAG = "unblinking_star_dream_touched"
CUSTODIAN_AIDED_FLAG = "unblinking_star_custodian_aided"
PATROL_ACTIVE_FLAG = "unblinking_star_patrol_active"

STARFALL_GLASS_KEY = "unblinking_starfall_glass"
APERTURE_SHARD_KEY = "unblinking_aperture_shard"
KEEPERS_MEASURE_KEY = "unblinking_keepers_measure"
PARALLAX_GLASS_KEY = "unblinking_parallax_glass"

GLASSBACK_STALKER_KEY = "unblinking_glassback_stalker"
MERIDIAN_WISP_KEY = "unblinking_meridian_wisp"
DREAM_ASH_PILGRIM_KEY = "unblinking_dream_ash_pilgrim"
PARALLAX_HUNTER_KEY = "unblinking_parallax_hunter"
BROKEN_CUSTODIAN_KEY = "unblinking_broken_custodian"
LENSBOUND_SENTINEL_KEY = "unblinking_lensbound_sentinel"
NULL_CHOIR_KEY = "unblinking_null_choir"
OPEN_EYED_FRAGMENT_KEY = "unblinking_open_eyed_fragment"

ARCHIVIST_KEY = "unblinking_archivist_senn_arclight"
KEEPER_KEY = "unblinking_keeper_nacre"


UNBLINKING_QUEST = QuestDefinition(
    key=QUEST_KEY,
    name="The Star That Looked Back",
    style="structured",
    minimum_level=13,
    description=(
        "Beyond Ashcross, a crater of fused earth surrounds a buried observatory whose builders recorded a dark point moving against the heavens. "
        "Their instruments eventually stopped behaving like instruments. Archivist Senn wants a group to learn why the complex is still operating, and why its oldest surviving instruction is not OPEN, but SEAL."
    ),
    objective_steps=(
        ("talk_archivist", "TALK SENN at the Broken Milestone outside Ashcross."),
        ("survey_scar", "Reach the Starfall Crater Rim and SURVEY SCAR."),
        ("enter_observatory", "Follow the buried causeway and enter the Observatory of the Unblinking Star."),
        ("align_lenses", "At the Lens Gallery, three party members must ALIGN NORTH LENS, ALIGN SOUTH LENS, and ALIGN ZENITH LENS."),
        ("sync_gate", "Reach the Three-Hand Gate with at least three party members and SYNCHRONIZE GATE."),
        ("align_orrery", "At the Null Orrery, three party members must TURN INNER RING, TURN MIDDLE RING, and TURN OUTER RING."),
        ("defeat_fragment", "With at least three level-15 party members, defeat the Open-Eyed Fragment at the aperture."),
        ("seal_aperture", "Enter the Seal Engine with at least three victorious party members and SEAL APERTURE."),
        ("return_archivist", "Return to Archivist Senn at the Broken Milestone."),
        ("complete", "The aperture is sealed. The observatory still dreams, but its last command holds."),
    ),
    sol_reward=180,
)

STARFALL_GLASS = ItemDefinition(
    key=STARFALL_GLASS_KEY,
    name="Starfall Glass",
    description="A thumb-sized piece of fused local soil. Bubbles inside it point in three different directions.",
    category="material",
    tier=3,
)
APERTURE_SHARD = ItemDefinition(
    key=APERTURE_SHARD_KEY,
    name="Aperture Shard",
    description="A cold black-violet flake left where the Open-Eyed Fragment failed to fit cleanly into Astralis.",
    category="material",
    tier=3,
)
KEEPERS_MEASURE = ItemDefinition(
    key=KEEPERS_MEASURE_KEY,
    name="Keeper's Measure",
    description="A narrow calibration token given by Keeper Nacre. Its etched line remains straight even beside warped glass.",
    category="material",
    tier=3,
)
PARALLAX_GLASS = ItemDefinition(
    key=PARALLAX_GLASS_KEY,
    name="Parallax Glass",
    description="A clear sliver recovered during a containment patrol. Its reflection arrives a fraction of a heartbeat late.",
    category="material",
    tier=3,
)
UNBLINKING_ITEMS = (STARFALL_GLASS, APERTURE_SHARD, KEEPERS_MEASURE, PARALLAX_GLASS)


GLASSBACK_STALKER = EnemyDefinition(
    key=GLASSBACK_STALKER_KEY,
    name="Glassback Stalker",
    aliases=("glassback", "stalker", "glassback stalker"),
    description="a long-limbed crater predator with translucent plates grown through the fur along its spine",
    max_hp=112,
    armor_class=11,
    auto_attack_damage=8,
    auto_attack_interval=3.0,
    xp_reward=76,
)
MERIDIAN_WISP = EnemyDefinition(
    key=MERIDIAN_WISP_KEY,
    name="Meridian Wisp",
    aliases=("wisp", "meridian wisp"),
    description="a knot of pale light that repeatedly measures the same impossible angle before snapping to another position",
    max_hp=104,
    armor_class=13,
    auto_attack_damage=8,
    auto_attack_interval=2.8,
    xp_reward=82,
)
DREAM_ASH_PILGRIM = EnemyDefinition(
    key=DREAM_ASH_PILGRIM_KEY,
    name="Dream-Ash Pilgrim",
    aliases=("pilgrim", "dream ash", "dream-ash pilgrim"),
    description="a person-shaped drift of gray dust walking an observatory route remembered by nobody living",
    max_hp=128,
    armor_class=13,
    auto_attack_damage=9,
    auto_attack_interval=3.0,
    xp_reward=94,
)
PARALLAX_HUNTER = EnemyDefinition(
    key=PARALLAX_HUNTER_KEY,
    name="Parallax Hunter",
    aliases=("hunter", "parallax", "parallax hunter"),
    description="a pale four-legged thing whose shoulders occupy slightly different places depending on which eye follows it",
    max_hp=154,
    armor_class=15,
    auto_attack_damage=10,
    auto_attack_interval=2.8,
    xp_reward=112,
)
BROKEN_CUSTODIAN = EnemyDefinition(
    key=BROKEN_CUSTODIAN_KEY,
    name="Broken Custodian",
    aliases=("broken custodian", "custodian", "broken keeper"),
    description="an ancient maintenance frame trapped in a loop of opening shutters that its own surviving instructions command it to close",
    max_hp=172,
    armor_class=16,
    auto_attack_damage=11,
    auto_attack_interval=2.9,
    xp_reward=128,
)
LENSBOUND_SENTINEL = EnemyDefinition(
    key=LENSBOUND_SENTINEL_KEY,
    name="Lensbound Sentinel",
    aliases=("sentinel", "lensbound", "lensbound sentinel"),
    description="a brass-black guardian wrapped around a cracked focusing lens, moving only when the lens turns toward a living observer",
    max_hp=238,
    armor_class=17,
    auto_attack_damage=12,
    auto_attack_interval=2.7,
    xp_reward=188,
)
NULL_CHOIR = EnemyDefinition(
    key=NULL_CHOIR_KEY,
    name="The Null Choir",
    aliases=("null choir", "choir", "the null choir"),
    description="six empty observation robes hanging in a ring, speaking one calculation through six voices without any bodies inside them",
    max_hp=270,
    armor_class=17,
    auto_attack_damage=13,
    auto_attack_interval=2.7,
    xp_reward=216,
)
OPEN_EYED_FRAGMENT = EnemyDefinition(
    key=OPEN_EYED_FRAGMENT_KEY,
    name="The Open-Eyed Fragment",
    aliases=("fragment", "open-eyed fragment", "open eyed fragment", "open-eyed"),
    description=(
        "a narrow projection of something on the far side of the aperture, too large for the opening and therefore present only in pieces; "
        "its edges disagree about distance, but every visible surface behaves like an eye"
    ),
    max_hp=620,
    armor_class=19,
    auto_attack_damage=16,
    auto_attack_interval=2.55,
    xp_reward=520,
)
UNBLINKING_ENEMIES = (
    GLASSBACK_STALKER,
    MERIDIAN_WISP,
    DREAM_ASH_PILGRIM,
    PARALLAX_HUNTER,
    BROKEN_CUSTODIAN,
    LENSBOUND_SENTINEL,
    NULL_CHOIR,
    OPEN_EYED_FRAGMENT,
)


ARCHIVIST = NpcDefinition(
    key=ARCHIVIST_KEY,
    name="Archivist Senn Arclight",
    short_description="a road archivist surrounded by copied star charts and black-glass survey plates",
    room_key=ASHCROSS_MILESTONE_KEY,
    role="Starfall expedition archivist",
    dialogue=(
        "Senn lays two charts on the milestone. 'Same sky, different centuries. That black point moves against everything else.'",
        "'Do not call the scar a meteor crater. The glass is local earth, fused where it stood. Nothing useful fell into it.'",
        "'Three people minimum beyond the old gate. The machinery was built around independent witnesses, and I am not arguing with a civilization that buried its own observatory.'",
    ),
)
KEEPER = NpcDefinition(
    key=KEEPER_KEY,
    name="Keeper Nacre",
    short_description="an ivory-black maintenance figure patiently resetting seal indicators one at a time",
    room_key=OBS_KEEPER_HALL_KEY,
    role="surviving observatory sealkeeper",
    dialogue=(
        "Nacre's faceplate turns toward you. 'Designation lost. Function remains. Observe if you must. Do not widen the aperture.'",
        "'The first astronomers believed sight traveled in one direction. Their final records corrected the error.'",
        "'Last command: SEAL. Duration: until observation ceases from the other side.'",
    ),
)
UNBLINKING_NPCS = (ARCHIVIST, KEEPER)


def _room(
    key: str,
    name: str,
    region: str,
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
        region_key=region,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=tags,
    )


UNBLINKING_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        STARFALL_APPROACH_KEY,
        "Starfall Scar Approach",
        STARFALL_REGION_KEY,
        "The Ashcross roads give way to a shallow basin where grass stops in an almost perfect curve. Beyond it, gray-black earth shines beneath the weeds as though the ground was fired in place. Survey stakes carry three generations of warnings, none agreeing on what caused the scar.",
        {"southwest": ASHCROSS_MILESTONE_KEY, "east": STARFALL_GLASS_FLATS_KEY},
        enemies=(GLASSBACK_STALKER_KEY,),
        tags=("shared_world", "starfall_scar", "level_13_14"),
    ),
    _room(
        STARFALL_GLASS_FLATS_KEY,
        "Glass-Rain Flats",
        STARFALL_REGION_KEY,
        "Fused soil lies in overlapping sheets, some smooth as pond ice and others blistered around roots that became charcoal without burning away. Fine glass needles click against one another whenever the wind crosses the flats.",
        {"west": STARFALL_APPROACH_KEY, "east": STARFALL_MERIDIAN_KEY, "south": STARFALL_ORCHARD_KEY},
        enemies=(GLASSBACK_STALKER_KEY, MERIDIAN_WISP_KEY),
        tags=("shared_world", "starfall_scar", "level_13_14", "glass_field"),
    ),
    _room(
        STARFALL_MERIDIAN_KEY,
        "Fallen Meridian",
        STARFALL_REGION_KEY,
        "A line of waist-high sighting stones cuts across the fused basin. Every stone aims toward the crater except one, which points into empty sky several handspans away from any visible star.",
        {"west": STARFALL_GLASS_FLATS_KEY, "east": STARFALL_MIRROR_SINK_KEY},
        enemies=(MERIDIAN_WISP_KEY,),
        tags=("shared_world", "starfall_scar", "level_13_14", "lore"),
    ),
    _room(
        STARFALL_ORCHARD_KEY,
        "Black Orchard",
        STARFALL_REGION_KEY,
        "Dead fruit trees stand preserved in glassy collars. New shoots grow normally outside the old burn line, but every root bends away from the crater before crossing it. Small predators use the trunks as cover.",
        {"north": STARFALL_GLASS_FLATS_KEY, "east": STARFALL_CAMP_KEY},
        enemies=(GLASSBACK_STALKER_KEY,),
        tags=("shared_world", "starfall_scar", "level_13_14", "ecology"),
    ),
    _room(
        STARFALL_MIRROR_SINK_KEY,
        "Mirror Sink",
        STARFALL_REGION_KEY,
        "Rainwater fills a shallow depression in flawless black glass. The pool reflects clouds, moons, and travelers correctly. It also reflects one perfectly dark point that is not present in the sky above.",
        {"west": STARFALL_MERIDIAN_KEY, "south": STARFALL_CRATER_RIM_KEY},
        enemies=(MERIDIAN_WISP_KEY,),
        tags=("shared_world", "starfall_scar", "level_14", "unblinking_hint"),
    ),
    _room(
        STARFALL_CAMP_KEY,
        "Witness Camp",
        STARFALL_REGION_KEY,
        "Three canvas shelters surround separate survey tables. Ashcross crews deliberately keep their measurements apart until dusk, then compare them in public so no one person's certainty becomes the expedition's evidence.",
        {"west": STARFALL_ORCHARD_KEY, "north": STARFALL_CRATER_RIM_KEY},
        tags=("shared_world", "starfall_scar", "level_14", "safe", "group_staging"),
    ),
    _room(
        STARFALL_CRATER_RIM_KEY,
        "Starfall Crater Rim",
        STARFALL_REGION_KEY,
        "The land drops into a vast shallow crater lined with gray glass and exposed stone. Near the center, the upper rings of a buried structure break through the fused earth. There is no impact stone, no ejecta field, and no sensible direction from which anything arrived.",
        {"north": STARFALL_MIRROR_SINK_KEY, "south": STARFALL_CAMP_KEY, "east": STARFALL_IMPACT_TERRACE_KEY},
        enemies=(DREAM_ASH_PILGRIM_KEY,),
        tags=("shared_world", "starfall_scar", "level_14", "survey_site"),
    ),
    _room(
        STARFALL_IMPACT_TERRACE_KEY,
        "Impact Terrace",
        STARFALL_REGION_KEY,
        "Broad steps descend through layers of glass that bend downward around the buried complex. The pattern resembles pressure from below more than impact from above. Dream-ash footprints end at walls and resume on the far side.",
        {"west": STARFALL_CRATER_RIM_KEY, "east": STARFALL_CAUSEWAY_KEY},
        enemies=(DREAM_ASH_PILGRIM_KEY, PARALLAX_HUNTER_KEY),
        tags=("shared_world", "starfall_scar", "level_14", "dangerous_road"),
    ),
    _room(
        STARFALL_CAUSEWAY_KEY,
        "Buried Causeway",
        STARFALL_REGION_KEY,
        "A processional road emerges from beneath vitrified soil. Its paving stones carry no royal names, gods, or racial heraldry, only repeated marks for angle, interval, witness, and correction.",
        {"west": STARFALL_IMPACT_TERRACE_KEY, "up": STARFALL_STEPS_KEY},
        enemies=(PARALLAX_HUNTER_KEY,),
        tags=("shared_world", "starfall_scar", "level_14", "ancient_road"),
    ),
    _room(
        STARFALL_STEPS_KEY,
        "Steps Beneath the Sky",
        STARFALL_REGION_KEY,
        "The causeway climbs to a circular doorway set into the crater wall. Half the observatory is still buried above it. A surviving inscription has been translated by modern crews as: OBSERVATION REQUIRES A WITNESS. SAFE OBSERVATION REQUIRES ANOTHER.",
        {"down": STARFALL_CAUSEWAY_KEY, "in": OBS_ENTRY_KEY},
        enemies=(LENSBOUND_SENTINEL_KEY,),
        tags=("shared_world", "starfall_scar", "level_14_15", "dungeon_entrance"),
    ),
    _room(
        OBS_ENTRY_KEY,
        "Entry Rotunda",
        OBSERVATORY_REGION_KEY,
        "A circular chamber turns the night sky into architecture. Brass sight lines radiate from a floor mark toward sealed shafts overhead. Modern dust covers everything except a narrow path repeatedly swept clean by machinery that should have stopped centuries ago.",
        {"out": STARFALL_STEPS_KEY, "north": OBS_LENS_GALLERY_KEY, "east": OBS_ARCHIVE_KEY},
        enemies=(BROKEN_CUSTODIAN_KEY,),
        tags=("dungeon", "unblinking_star", "level_14_15", "outer_observatory"),
    ),
    _room(
        OBS_LENS_GALLERY_KEY,
        "Lens Gallery",
        OBSERVATORY_REGION_KEY,
        "Three enormous lens cradles face a blackened dome. NORTH and SOUTH are mounted at opposite ends of the gallery. A third cradle marked ZENITH hangs above a central pit. No single control station can move more than one lens.",
        {"south": OBS_ENTRY_KEY, "east": OBS_CHOIR_KEY, "north": OBS_GRAVITY_WELL_KEY},
        enemies=(LENSBOUND_SENTINEL_KEY,),
        tags=("dungeon", "unblinking_star", "level_14_15", "group_puzzle"),
    ),
    _room(
        OBS_ARCHIVE_KEY,
        "Archive of Angles",
        OBSERVATORY_REGION_KEY,
        "Stone shelves hold thin metal observation plates. Early charts treat a moving patch of perfect dark as a curiosity. Later charts call it the Unblinking Star. The final plates stop drawing the heavens and begin drawing the observatory as seen from somewhere outside it.",
        {"west": OBS_ENTRY_KEY, "south": OBS_DORMITORY_KEY, "east": OBS_TRANSIT_KEY},
        enemies=(DREAM_ASH_PILGRIM_KEY,),
        tags=("dungeon", "unblinking_star", "level_14_15", "lore"),
    ),
    _room(
        OBS_DORMITORY_KEY,
        "Sleepless Dormitory",
        OBSERVATORY_REGION_KEY,
        "Stone sleeping alcoves line both walls. Hundreds of scratched notes describe the same dream in different hands: a sky with one point missing, followed by the certainty that the missing point is looking inward.",
        {"north": OBS_ARCHIVE_KEY, "east": OBS_MAINTENANCE_KEY},
        enemies=(DREAM_ASH_PILGRIM_KEY,),
        tags=("dungeon", "unblinking_star", "level_14_15", "dream_leak"),
    ),
    _room(
        OBS_GRAVITY_WELL_KEY,
        "Gravity Well",
        OBSERVATORY_REGION_KEY,
        "A cylindrical shaft rises and falls at once. Loose screws rest against the eastern wall as if it were the floor, while a broken lantern hangs straight toward the ceiling. The safest path is whichever surface your body currently believes.",
        {"south": OBS_LENS_GALLERY_KEY, "east": OBS_CHOIR_KEY},
        enemies=(PARALLAX_HUNTER_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "gravity"),
    ),
    _room(
        OBS_CHOIR_KEY,
        "Choir of Measures",
        OBSERVATORY_REGION_KEY,
        "Six observation stations surround a central calculation table. Their speaking tubes still whisper corrections to one another, repeating measurements until every station agrees. Tonight, none of them agree about the distance to the same dark point.",
        {"west": OBS_LENS_GALLERY_KEY, "north": OBS_GRAVITY_WELL_KEY, "south": OBS_TRANSIT_KEY},
        enemies=(NULL_CHOIR_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "miniboss"),
    ),
    _room(
        OBS_TRANSIT_KEY,
        "Transit Gallery",
        OBSERVATORY_REGION_KEY,
        "A long hall is divided by brass lines marking fractions of a second. Halfway across, the numbering skips backward. Dusty footprints appear twice around that seam, one set arriving before the other set leaves.",
        {"west": OBS_ARCHIVE_KEY, "north": OBS_CHOIR_KEY, "east": OBS_MAINTENANCE_KEY},
        enemies=(PARALLAX_HUNTER_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "time_slip"),
    ),
    _room(
        OBS_MAINTENANCE_KEY,
        "Maintenance Spine",
        OBSERVATORY_REGION_KEY,
        "Tool recesses, shutter cables, counterweights, and narrow service tracks run through the observatory's backbone. Most mechanisms are dead. The few that still move all serve the same direction: inward, toward the core.",
        {"west": OBS_TRANSIT_KEY, "south": OBS_DORMITORY_KEY, "north": OBS_KEEPER_HALL_KEY},
        enemies=(BROKEN_CUSTODIAN_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "maintenance"),
    ),
    _room(
        OBS_KEEPER_HALL_KEY,
        "Sealkeeper Hall",
        OBSERVATORY_REGION_KEY,
        "Rows of dead maintenance frames stand against the walls with their hands folded over tool chests. One figure still moves. Every working indicator around Keeper Nacre is labeled with some variation of CLOSE, NARROW, HOLD, or SEAL.",
        {"south": OBS_MAINTENANCE_KEY, "east": OBS_THREE_HAND_GATE_KEY},
        npcs=(KEEPER_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "safe_pocket", "lore"),
    ),
    _room(
        OBS_THREE_HAND_GATE_KEY,
        "Three-Hand Gate",
        OBSERVATORY_REGION_KEY,
        "A black circular door is surrounded by three widely separated witness plates. The old builders could have linked them. They deliberately did not. A surviving warning reads: NO SINGLE OBSERVER MAY AUTHORIZE DEEP SIGHT.",
        {"west": OBS_KEEPER_HALL_KEY},
        tags=("dungeon", "unblinking_star", "level_15", "group_required", "cooperative_gate"),
    ),
    _room(
        OBS_INVERSION_STAIR_KEY,
        "Inversion Stair",
        OBSERVATORY_REGION_KEY,
        "The stair curls around an open shaft and slowly becomes a wall, then a ceiling, then a floor again. Looking back at the gate makes the route seem impossible, although every individual step remains ordinary beneath your boots.",
        {"west": OBS_THREE_HAND_GATE_KEY, "east": OBS_NULL_ORRERY_KEY},
        enemies=(PARALLAX_HUNTER_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "core", "group_required"),
    ),
    _room(
        OBS_NULL_ORRERY_KEY,
        "Null Orrery",
        OBSERVATORY_REGION_KEY,
        "Three concentric black-metal rings rotate around an empty center. Every known moon and planet is engraved along the outer mechanisms. The center is reserved for a point that has no engraved body at all.",
        {"west": OBS_INVERSION_STAIR_KEY, "south": OBS_DREAM_RELAY_KEY},
        enemies=(BROKEN_CUSTODIAN_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "core", "group_puzzle"),
    ),
    _room(
        OBS_DREAM_RELAY_KEY,
        "Dreaming Relay",
        OBSERVATORY_REGION_KEY,
        "Copper-black filaments run from the old dormitory circuits into a sealed column. The builders eventually wired their own sleeping chambers into the instrument array, trying to measure why hundreds of observers had begun dreaming the same impossible sky.",
        {"north": OBS_NULL_ORRERY_KEY, "east": OBS_PLANETARIUM_KEY},
        enemies=(DREAM_ASH_PILGRIM_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "core", "dream_leak"),
    ),
    _room(
        OBS_PLANETARIUM_KEY,
        "Silent Planetarium",
        OBSERVATORY_REGION_KEY,
        "A perfect model of the local heavens hangs frozen overhead. One mechanism moves alone: an unmarked black bead traveling against the gears. Each time it crosses the room's meridian, every other model stops for exactly one heartbeat.",
        {"west": OBS_DREAM_RELAY_KEY, "east": OBS_APHELION_BRIDGE_KEY},
        enemies=(MERIDIAN_WISP_KEY, PARALLAX_HUNTER_KEY),
        tags=("dungeon", "unblinking_star", "level_15", "core", "lore"),
    ),
    _room(
        OBS_APHELION_BRIDGE_KEY,
        "Aphelion Bridge",
        OBSERVATORY_REGION_KEY,
        "A narrow bridge crosses a chamber too dark to judge. Handrails continue farther than the floor beneath them. On the opposite side, three seal lamps burn with a cold white light.",
        {"west": OBS_PLANETARIUM_KEY, "north": OBS_LAST_COMMAND_KEY},
        enemies=(LENSBOUND_SENTINEL_KEY,),
        tags=("dungeon", "unblinking_star", "level_15", "core", "hazard"),
    ),
    _room(
        OBS_LAST_COMMAND_KEY,
        "The Last Command",
        OBSERVATORY_REGION_KEY,
        "A wall of control plates records the observatory's final operating order. Earlier instructions concern calibration, observation, and pursuit. The last surviving command is enormous, repeated in every maintenance notation the expedition can translate: NARROW APERTURE. BREAK RECIPROCITY. SEAL.",
        {"south": OBS_APHELION_BRIDGE_KEY, "east": OBS_THRESHOLD_KEY},
        tags=("dungeon", "unblinking_star", "level_15", "core", "revelation"),
    ),
    _room(
        OBS_THRESHOLD_KEY,
        "Threshold Ring",
        OBSERVATORY_REGION_KEY,
        "Concentric shutters surround a vertical slit of impossible darkness. The shutters are nearly closed, held apart by a pressure that produces no wind. Every surface facing the slit has been polished smooth by centuries of microscopic movement.",
        {"west": OBS_LAST_COMMAND_KEY, "east": OBS_APERTURE_KEY},
        enemies=(NULL_CHOIR_KEY,),
        tags=("dungeon", "unblinking_star", "level_15_16", "core", "boss_approach"),
    ),
    _room(
        OBS_APERTURE_KEY,
        "The Aperture",
        OBSERVATORY_REGION_KEY,
        "The observatory ends at a slit narrower than a doorway. Beyond it is not sky, stone, or ordinary darkness. Something occupies the far side without fitting through. When it presses close, pieces of one presence appear at incompatible depths, each piece turning toward the observers.",
        {"west": OBS_THRESHOLD_KEY},
        enemies=(OPEN_EYED_FRAGMENT_KEY,),
        tags=("dungeon", "unblinking_star", "level_15_16", "core", "boss", "group_required"),
    ),
    _room(
        OBS_SEAL_ENGINE_KEY,
        "Seal Engine",
        OBSERVATORY_REGION_KEY,
        "Behind the aperture chamber, three mechanical witness locks converge on a massive shutter drive. The machine has spent centuries trying to finish one interrupted motion. Its final indicator is still waiting for three living confirmations.",
        {"west": OBS_APERTURE_KEY},
        tags=("dungeon", "unblinking_star", "level_15_16", "core", "finale", "group_required"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        summary=summary,
        examine_text=examine,
        aliases=aliases,
    )


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
    return RoomAugmentation(
        exit_overrides=tuple(overrides.values()),
        extra_exits=tuple(extras.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


def unblinking_augmentations() -> dict[str, RoomAugmentation]:
    return {
        ASHCROSS_MILESTONE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="northeast",
                    destination_key=STARFALL_APPROACH_KEY,
                    name="Starfall Scar",
                    aliases=("ne", "starfall", "scar", "starfall scar"),
                    travel_text="You follow Senn's black-glass survey stakes northeast toward the Starfall Scar.",
                    condition=ViewCondition(min_level=13),
                    failure_text="The Starfall survey is marked for level-13 travelers and stronger.",
                    hidden_when_unavailable=False,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="unblinking_star_survey_presence",
                    text="Fresh black-glass survey stakes now lead northeast toward a fused basin that Ashcross maps label STARFALL SCAR.",
                    priority=160,
                    condition=ViewCondition(min_level=13),
                ),
            ),
        ),
        STARFALL_CRATER_RIM_KEY: RoomAugmentation(
            features=(
                _feature(
                    "starfall_crater_glass",
                    "Crater Glass",
                    "fused earth bending around the buried observatory",
                    "The material contains local sand, roots, road grit, and bits of old topsoil. This is not foreign impact glass. The ground itself was heated and pressed around the complex.",
                    ("glass", "scar", "fused earth"),
                ),
            ),
        ),
        OBS_ARCHIVE_KEY: RoomAugmentation(
            features=(
                _feature(
                    "unblinking_archive_plates",
                    "Observation Plates",
                    "metal star charts progressing from curiosity to alarm",
                    "The earliest plate marks a dark point moving against the mapped heavens. Later plates show lens magnification, then shared-dream tallies, then diagrams of the observatory drawn from impossible exterior viewpoints. The builders never record a god-name for it. Their final term is simply RECIPROCAL OBSERVER.",
                    ("plates", "charts", "star charts", "archive"),
                ),
            ),
        ),
        OBS_THREE_HAND_GATE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=OBS_INVERSION_STAIR_KEY,
                    name="Deep Observatory",
                    aliases=("core", "deep", "inversion"),
                    travel_text="The synchronized witness plates release, and you pass east into the buried core.",
                    condition=ViewCondition(required_flags=(CORE_GATE_FLAG,), min_level=14),
                    failure_text="The three witness plates have not been synchronized for you.",
                    hidden_when_unavailable=False,
                ),
            ),
        ),
        OBS_LAST_COMMAND_KEY: RoomAugmentation(
            features=(
                _feature(
                    "unblinking_last_command_panel",
                    "Last Command Panel",
                    "a bank of controls dominated by the final sealing order",
                    "The sequence is clear even without every symbol translated: observe, detect reciprocity, narrow the aperture, break the link, seal. Whatever happened here, the surviving machinery is not trying to invite the presence into Astralis. It has been trying to close the door.",
                    ("panel", "command", "last command", "controls"),
                ),
            ),
        ),
        OBS_APERTURE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=OBS_SEAL_ENGINE_KEY,
                    name="Seal Engine",
                    aliases=("engine", "seal", "seal engine"),
                    travel_text="With the fragment dispersed, you squeeze through the maintenance opening into the seal engine.",
                    condition=ViewCondition(required_flags=(BOSS_DEFEATED_FLAG,)),
                    failure_text="The Open-Eyed Fragment still occupies the aperture. The seal engine cannot be reached safely.",
                    hidden_when_unavailable=False,
                ),
            ),
        ),
        OBS_SEAL_ENGINE_KEY: RoomAugmentation(
            features=(
                _feature(
                    "unblinking_three_confirmations",
                    "Three Confirmation Levers",
                    "three witness levers feeding one ancient shutter drive",
                    "The levers are mechanically independent until the final gear. The builders wanted three living confirmations before any change to the aperture could be made. The safe direction is still labeled SEAL.",
                    ("levers", "confirmations", "witness levers", "seal controls"),
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


def install_unblinking_star_content(world_service=None) -> None:
    if UNBLINKING_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (UNBLINKING_QUEST,)
    quests.QUESTS_BY_KEY[UNBLINKING_QUEST.key] = UNBLINKING_QUEST

    for item in UNBLINKING_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in UNBLINKING_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for room in UNBLINKING_ROOMS:
        _replace_room(room)
    for npc in UNBLINKING_NPCS:
        _replace_npc(npc)

    milestone = legacy_world.ROOMS_BY_KEY.get(ASHCROSS_MILESTONE_KEY)
    if milestone is not None and ARCHIVIST_KEY not in milestone.npc_keys:
        milestone = replace(milestone, npc_keys=(*milestone.npc_keys, ARCHIVIST_KEY))
        _replace_room(milestone)

    if world_service is None:
        return
    for room in UNBLINKING_ROOMS:
        world_service.legacy_rooms[room.key] = room
    if milestone is not None:
        world_service.legacy_rooms[ASHCROSS_MILESTONE_KEY] = milestone
    for room_key, augmentation in unblinking_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(
            world_service.augmentations.get(room_key),
            augmentation,
        )
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*UNBLINKING_ROOM_KEYS, ASHCROSS_MILESTONE_KEY):
            cache.pop(room_key, None)


_LENS_ASSIGNMENTS: dict[int, str] = {}
_ORRERY_ASSIGNMENTS: dict[int, str] = {}
_LENS_STATIONS = {"north", "south", "zenith"}
_ORRERY_STATIONS = {"inner", "middle", "outer"}
_BOSS_ALIASES = {
    OPEN_EYED_FRAGMENT.key.replace("_", " "),
    OPEN_EYED_FRAGMENT.name.lower(),
    *(alias.lower() for alias in OPEN_EYED_FRAGMENT.aliases),
}


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, QUEST_KEY)


def _party_here(session) -> list:
    finder = getattr(session, "party_sessions_here", None)
    if callable(finder):
        members = list(finder())
        if members:
            return members
    return [session] if session.character is not None else []


def _victory_sessions(session, enemy) -> list:
    finder = getattr(session, "party_victory_sessions", None)
    if callable(finder):
        members = list(finder(enemy))
        if members:
            return members
    return [session] if session.character is not None else []


def _eligible_party_here(session, *, min_level: int = 1, required_flag: str | None = None) -> list:
    room_key = session.character.current_room if session.character is not None else None
    result = []
    for member in _party_here(session):
        character = getattr(member, "character", None)
        if character is None or character.current_room != room_key or character.level < min_level:
            continue
        if required_flag is not None and required_flag not in _flags(member):
            continue
        result.append(member)
    return result


def _ensure_quest(session) -> bool:
    character = session.character
    if character is None or character.level < 13:
        return False
    if COMPLETE_FLAG in _flags(session):
        return True
    if session.database.get_quest(character.id, QUEST_KEY) is None:
        session.database.start_quest(character.id, QUEST_KEY, "talk_archivist")
    return True


def _advance_if(session, expected: str, next_step: str) -> bool:
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == expected:
        session.database.advance_quest(session.character.id, QUEST_KEY, next_step)
        return True
    return False


async def _talk_archivist(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_MILESTONE_KEY:
        return False
    if session.character.level < 13:
        await session.send(
            "Senn glances from you to the black-glass stakes. 'Come back around level thirteen. The scar is survivable earlier. The observatory is not.'\r\n"
        )
        return True
    _ensure_quest(session)
    flags = _flags(session)
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == "talk_archivist":
        session.database.advance_quest(session.character.id, QUEST_KEY, "survey_scar")
        await session.send(
            "Senn slides three independently copied charts across the milestone. 'The old astronomers tracked a dark point moving against the sky. They magnified it. Then their journals start describing the same dreams.'\r\n"
            "'Follow the stakes northeast. SURVEY SCAR at the crater rim. Once you enter the observatory, bring a real party. Three witnesses minimum. Do not kill something merely because it is still maintaining the seal.'\r\n"
        )
        return True
    if q and q.get("status") == "active" and q.get("current_step") == "return_archivist":
        session.database.complete_quest(session.character.id, QUEST_KEY)
        session.database.grant_flag(session.character.id, COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 600)
        session.database.add_item(session.character.id, STARFALL_GLASS_KEY, 1)
        bonus = ""
        if CUSTODIAN_AIDED_FLAG in flags:
            session.database.add_experience(session.character.id, 120)
            session.database.add_item(session.character.id, KEEPERS_MEASURE_KEY, 1)
            bonus = " Keeper Nacre's surviving maintenance record earns you another 120 XP and a Keeper's Measure."
        _refresh_character(session)
        await session.send(
            "Senn listens twice: once to your account, and once to the silence after it. 'So the machine was still doing its job. The disaster was not the seal failing. It was observation becoming reciprocal.'\r\n"
            "Quest complete: The Star That Looked Back. You gain 600 XP and keep a piece of Starfall Glass."
            + bonus
            + "\r\nSenn adds one final note to the map: the aperture is closed, but the shared dreams have not stopped everywhere.\r\n"
        )
        return True
    if COMPLETE_FLAG in flags:
        if PATROL_ACTIVE_FLAG in flags:
            await session.send(
                "Senn checks your patrol slate. 'Containment circuit is active. Recalibrate the three witness systems and close the aperture again if it starts to breathe.'\r\n"
            )
        else:
            await session.send(
                "Senn taps a stack of blank containment slates. 'The seal drifts. If you want another group run, TAKE STARFALL PATROL and I will issue a fresh calibration circuit.'\r\n"
            )
        return True
    await session.send(
        "Senn looks toward the northeast stakes. 'Your expedition is still open. Follow the journal. The observatory rewards agreement between witnesses, not confidence from one.'\r\n"
    )
    return True


async def _survey_scar(session) -> bool:
    if session.character is None or session.character.current_room != STARFALL_CRATER_RIM_KEY:
        return False
    session.database.grant_flag(session.character.id, SCAR_SURVEYED_FLAG)
    _advance_if(session, "survey_scar", "enter_observatory")
    if session.database.count_item(session.character.id, STARFALL_GLASS_KEY) <= 0:
        session.database.add_item(session.character.id, STARFALL_GLASS_KEY, 1)
    await session.send(
        "You compare glass layers, exposed roots, and the buried rings below. The evidence refuses the easy story: nothing struck this place from above. Local earth was fused around an event centered on the observatory itself.\r\n"
        "A loose piece of Starfall Glass comes free at the rim. Your expedition journal marks the observatory entrance next.\r\n"
    )
    return True


def _station_members(session, assignments: dict[int, str], stations: set[str]) -> dict[str, object]:
    room_key = session.character.current_room if session.character is not None else None
    found: dict[str, object] = {}
    for member in _party_here(session):
        character = getattr(member, "character", None)
        if character is None or character.current_room != room_key:
            continue
        station = assignments.get(int(character.id))
        if station in stations:
            found[station] = member
    return found


async def _align_lens(session, station: str) -> bool:
    if session.character is None or session.character.current_room != OBS_LENS_GALLERY_KEY:
        return False
    if station not in _LENS_STATIONS:
        return False
    members = _party_here(session)
    if len(members) < 3:
        await session.send("The lens controls are too far apart. You need at least three party members here.\r\n")
        return True
    _LENS_ASSIGNMENTS[int(session.character.id)] = station
    await session.send(f"You take the {station.upper()} lens control and hold its calibration mark.\r\n")
    occupied = _station_members(session, _LENS_ASSIGNMENTS, _LENS_STATIONS)
    if set(occupied) != _LENS_STATIONS:
        missing = ", ".join(sorted(_LENS_STATIONS - set(occupied))).upper()
        await session.send(f"The array is not synchronized yet. Unheld station(s): {missing}.\r\n")
        return True

    party = list(dict.fromkeys(occupied.values()))
    for member in party:
        character = member.character
        member.database.grant_flag(character.id, LENSES_ALIGNED_FLAG)
        _advance_if(member, "align_lenses", "sync_gate")
        await member.send(
            "All three lenses lock on the same absence. For one instant the dark point appears in every lens at once, despite each lens facing a different angle. The deeper witness circuit wakes.\r\n"
        )
    return True


async def _synchronize_gate(session) -> bool:
    if session.character is None or session.character.current_room != OBS_THREE_HAND_GATE_KEY:
        return False
    members = _eligible_party_here(session, min_level=14, required_flag=LENSES_ALIGNED_FLAG)
    if len(members) < 3:
        await session.send(
            "Three qualified witnesses must be here together. Each needs the Lens Gallery calibration and must be at least level 14.\r\n"
        )
        return True
    for member in members:
        member.database.grant_flag(member.character.id, CORE_GATE_FLAG)
        _advance_if(member, "sync_gate", "align_orrery")
        await member.send(
            "Three witness plates descend under separate hands. Only after all three report the same safe state does the core door release.\r\n"
        )
    return True


async def _turn_orrery(session, station: str) -> bool:
    if session.character is None or session.character.current_room != OBS_NULL_ORRERY_KEY:
        return False
    if station not in _ORRERY_STATIONS:
        return False
    members = _eligible_party_here(session, min_level=14, required_flag=CORE_GATE_FLAG)
    if len(members) < 3:
        await session.send("The Null Orrery requires three calibrated party members in the chamber.\r\n")
        return True
    _ORRERY_ASSIGNMENTS[int(session.character.id)] = station
    await session.send(f"You take the {station.upper()} ring and turn it toward the witness mark.\r\n")
    occupied = _station_members(session, _ORRERY_ASSIGNMENTS, _ORRERY_STATIONS)
    if set(occupied) != _ORRERY_STATIONS:
        missing = ", ".join(sorted(_ORRERY_STATIONS - set(occupied))).upper()
        await session.send(f"The orrery is still misaligned. Unheld ring(s): {missing}.\r\n")
        return True

    party = list(dict.fromkeys(occupied.values()))
    for member in party:
        member.database.grant_flag(member.character.id, ORRERY_ALIGNED_FLAG)
        _advance_if(member, "align_orrery", "defeat_fragment")
        await member.send(
            "INNER, MIDDLE, and OUTER rings align. The engraved heavens stop moving, but the empty center turns once against them. The route to the aperture is now fully calibrated.\r\n"
        )
    return True


async def _aid_custodian(session) -> bool:
    if session.character is None or session.character.current_room != OBS_KEEPER_HALL_KEY:
        return False
    if CUSTODIAN_AIDED_FLAG in _flags(session):
        await session.send("Keeper Nacre's calibration is already stable. The sealkeeper returns to its endless indicator checks.\r\n")
        return True
    session.database.grant_flag(session.character.id, CUSTODIAN_AIDED_FLAG)
    await session.send(
        "You follow Nacre's gestures instead of treating the surviving keeper as another target. Together you reseat a slipped shutter cable.\r\n"
        "Nacre inclines its faceplate. 'Observer distinguishes guardian from obstruction. Useful.' The maintenance record is now attached to your expedition notes.\r\n"
    )
    return True


async def _take_patrol(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_MILESTONE_KEY:
        return False
    flags = _flags(session)
    if COMPLETE_FLAG not in flags:
        await session.send("Senn will issue containment patrols only after your first full observatory clear.\r\n")
        return True
    if PATROL_ACTIVE_FLAG in flags:
        await session.send("You already have an active Starfall containment patrol.\r\n")
        return True
    for flag in (
        LENSES_ALIGNED_FLAG,
        CORE_GATE_FLAG,
        ORRERY_ALIGNED_FLAG,
        BOSS_DEFEATED_FLAG,
        APERTURE_SEALED_FLAG,
    ):
        session.database.revoke_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, PATROL_ACTIVE_FLAG)
    _LENS_ASSIGNMENTS.pop(int(session.character.id), None)
    _ORRERY_ASSIGNMENTS.pop(int(session.character.id), None)
    await session.send(
        "Senn dates a fresh containment slate. 'Same observatory, fresh calibration. The seal drifts because something on the other side keeps observing back.'\r\n"
        "Starfall patrol active. Recalibrate the Lens Gallery, synchronize the gate, align the Null Orrery, defeat any renewed aperture fragment, and seal the engine.\r\n"
    )
    return True


async def _seal_aperture(session) -> bool:
    if session.character is None or session.character.current_room != OBS_SEAL_ENGINE_KEY:
        return False
    members = _eligible_party_here(session, min_level=15, required_flag=BOSS_DEFEATED_FLAG)
    if len(members) < 3:
        await session.send(
            "The seal engine refuses a single authorization. At least three level-15 victorious party members must confirm the closure together.\r\n"
        )
        return True

    patrol_finishers = []
    for member in members:
        member.database.grant_flag(member.character.id, APERTURE_SEALED_FLAG)
        if _advance_if(member, "seal_aperture", "return_archivist"):
            pass
        if PATROL_ACTIVE_FLAG in _flags(member):
            member.database.revoke_flag(member.character.id, PATROL_ACTIVE_FLAG)
            member.database.add_experience(member.character.id, 160)
            member.database.add_item(member.character.id, PARALLAX_GLASS_KEY, 1)
            _refresh_character(member)
            patrol_finishers.append(member)
        await member.send(
            "Three confirmations arrive independently. The ancient drive finally completes its interrupted motion. Shutters grind together until the impossible slit becomes a hairline, then nothing.\r\n"
        )
    if patrol_finishers:
        for member in patrol_finishers:
            await member.send(
                "Containment patrol complete. You gain 160 XP and recover a sliver of Parallax Glass from the resealed mechanism.\r\n"
            )
    return True


async def _delegate_command(self, previous_prompt, command: str) -> None:
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


def install_unblinking_star_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_unblinking_star_runtime_installed", False):
        return

    install_unblinking_star_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_start_combat = player_session_class.start_combat
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None and self.character.current_room == ASHCROSS_MILESTONE_KEY:
            _ensure_quest(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        if self.character is None:
            return
        after = self.character.current_room
        if after == OBS_ENTRY_KEY and after != before:
            if _advance_if(self, "enter_observatory", "align_lenses"):
                await self.send(
                    "The rotunda closes around you. The expedition journal marks the Lens Gallery as the first cooperative calibration. Three independent controls, three witnesses.\r\n"
                )
        if after == OBS_DREAM_RELAY_KEY and DREAM_TOUCHED_FLAG not in _flags(self):
            self.database.grant_flag(self.character.id, DREAM_TOUCHED_FLAG)
            await self.send(
                "For less than a heartbeat you remember a sky you have never seen: every star in its place except one. The missing point is not absence. It is attention. Then the memory is gone, leaving only the certainty that it was shared.\r\n"
            )
        if before == OBS_LENS_GALLERY_KEY and after != OBS_LENS_GALLERY_KEY:
            _LENS_ASSIGNMENTS.pop(int(self.character.id), None)
        if before == OBS_NULL_ORRERY_KEY and after != OBS_NULL_ORRERY_KEY:
            _ORRERY_ASSIGNMENTS.pop(int(self.character.id), None)

    async def start_combat(self, target_name: str) -> None:
        if self.character is not None and self.character.current_room == OBS_APERTURE_KEY:
            normalized = " ".join((target_name or "").strip().lower().split())
            if normalized in _BOSS_ALIASES:
                members = _eligible_party_here(self, min_level=15, required_flag=ORRERY_ALIGNED_FLAG)
                if len(members) < 3:
                    await self.send(
                        "The aperture widens the instant one observer challenges it. You need at least three level-15 party members here, each aligned at the Null Orrery, before engaging the Open-Eyed Fragment.\r\n"
                    )
                    return
        await previous_start_combat(self, target_name)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        participants = _victory_sessions(self, enemy) if key == OPEN_EYED_FRAGMENT_KEY else []
        await previous_finish(self, enemy)
        if key != OPEN_EYED_FRAGMENT_KEY:
            return
        for member in participants:
            character = getattr(member, "character", None)
            if character is None:
                continue
            member.database.grant_flag(character.id, BOSS_DEFEATED_FLAG)
            member.database.add_item(character.id, APERTURE_SHARD_KEY, 1)
            _advance_if(member, "defeat_fragment", "seal_aperture")
            await member.send(
                "The Open-Eyed Fragment collapses into incompatible shadows and vanishes from the slit. A cold Aperture Shard remains. The final shutter drive is accessible east.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized in {"talk senn", "talk archivist", "talk archivist senn", "talk senn arclight"}:
            if await _talk_archivist(self):
                return
        if normalized in {"survey scar", "survey crater", "survey starfall scar"}:
            if await _survey_scar(self):
                return
        if normalized.startswith("align ") and normalized.endswith(" lens"):
            station = normalized.removeprefix("align ").removesuffix(" lens").strip()
            if station in _LENS_STATIONS and await _align_lens(self, station):
                return
        if normalized in {"synchronize gate", "sync gate", "synchronize three hand gate", "synchronize three-hand gate"}:
            if await _synchronize_gate(self):
                return
        if normalized.startswith("turn ") and normalized.endswith(" ring"):
            station = normalized.removeprefix("turn ").removesuffix(" ring").strip()
            if station in _ORRERY_STATIONS and await _turn_orrery(self, station):
                return
        if normalized in {"aid custodian", "help custodian", "aid nacre", "help nacre"}:
            if await _aid_custodian(self):
                return
        if normalized in {"seal aperture", "close aperture", "engage seal engine"}:
            if await _seal_aperture(self):
                return
        if normalized in {"take starfall patrol", "take containment patrol", "new starfall patrol", "reset starfall"}:
            if await _take_patrol(self):
                return

        await _delegate_command(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class.start_combat = start_combat
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._unblinking_star_runtime_installed = True
