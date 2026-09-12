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
from mud.living_world import _chronicle_insert
from mud.party_system import _party_sessions_here
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.waymeet_frontier import (
    WAYMEET_BRIARCUT_KEY,
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_HIGH_ROAD_KEY,
    WAYMEET_QUARRY_KEY,
)
from mud.world import NpcDefinition, RoomDefinition


ADVENTURE_VERSION = "1.0.0"
ADVENTURE_REGION_KEY = "waymeet_outer_adventure"
TOLL_REGION_KEY = "tollmans_cellar"
BELL_REGION_KEY = "crooked_bell"
SCAR_REGION_KEY = "kings_scar"
ECHO_REGION_KEY = "vault_first_echo"

# ---------------------------------------------------------------------------
# The explorable ring around Waymeet
# ---------------------------------------------------------------------------
OLD_TOLL_ROAD = "adventure_old_toll_road"
CROSSWIND_FARM = "adventure_crosswind_farm"
BRIARWOOD_EDGE = "adventure_briarwood_edge"
ASH_BRIDGE = "adventure_ash_bridge"
KINGS_SCAR_APPROACH = "adventure_kings_scar_approach"
ECHO_RIDGE = "adventure_echo_ridge"
ADVENTURE_OVERWORLD_KEYS = (
    OLD_TOLL_ROAD,
    CROSSWIND_FARM,
    BRIARWOOD_EDGE,
    ASH_BRIDGE,
    KINGS_SCAR_APPROACH,
    ECHO_RIDGE,
)

# Tollman's Cellar: exactly ten rooms.
TOLL_ENTRY = "toll_cellar_entry"
TOLL_FEE_ROOM = "toll_fee_room"
TOLL_STORAGE = "toll_storage"
TOLL_RAT_RUN = "toll_rat_run"
TOLL_SMUGGLER_CUT = "toll_smuggler_cut"
TOLL_LEDGER = "toll_ledger_room"
TOLL_KENNEL = "toll_burrow_kennel"
TOLL_COUNTING = "toll_counting_room"
TOLL_HIDDEN_STAIR = "toll_hidden_stair"
TOLL_CARVED_SUBLEVEL = "toll_carved_sublevel"
TOLL_ROOM_KEYS = (
    TOLL_ENTRY, TOLL_FEE_ROOM, TOLL_STORAGE, TOLL_RAT_RUN, TOLL_SMUGGLER_CUT,
    TOLL_LEDGER, TOLL_KENNEL, TOLL_COUNTING, TOLL_HIDDEN_STAIR, TOLL_CARVED_SUBLEVEL,
)

# The Crooked Bell: exactly ten rooms.
BELL_GATE = "bell_briar_gate"
BELL_NAVE = "bell_ruined_nave"
BELL_CHOIR = "bell_rotten_choir"
BELL_ROOT_CELLAR = "bell_root_cellar"
BELL_WEST_GALLERY = "bell_west_gallery"
BELL_EAST_GALLERY = "bell_east_gallery"
BELL_STAIR = "bell_cracked_stair"
BELL_ROPE_ROOM = "bell_rope_room"
BELL_BELFRY = "bell_belfry"
BELL_ECHO_LOFT = "bell_echo_loft"
BELL_ROOM_KEYS = (
    BELL_GATE, BELL_NAVE, BELL_CHOIR, BELL_ROOT_CELLAR, BELL_WEST_GALLERY,
    BELL_EAST_GALLERY, BELL_STAIR, BELL_ROPE_ROOM, BELL_BELFRY, BELL_ECHO_LOFT,
)

# King's Scar: exactly twelve rooms.
SCAR_GATE = "scar_quarry_gate"
SCAR_LIFT = "scar_lift_house"
SCAR_LOWER_CUT = "scar_lower_cut"
SCAR_POWDER = "scar_powder_store"
SCAR_BROKEN_BRIDGE = "scar_broken_bridge"
SCAR_CRANE_WALK = "scar_crane_walk"
SCAR_FOREMAN = "scar_foreman_booth"
SCAR_FLOODED = "scar_flooded_shaft"
SCAR_DEEP_FACE = "scar_deep_face"
SCAR_KINGS_TOOTH = "scar_kings_tooth"
SCAR_WINCH = "scar_winch_chamber"
SCAR_BREAKER_PIT = "scar_breaker_pit"
SCAR_ROOM_KEYS = (
    SCAR_GATE, SCAR_LIFT, SCAR_LOWER_CUT, SCAR_POWDER, SCAR_BROKEN_BRIDGE,
    SCAR_CRANE_WALK, SCAR_FOREMAN, SCAR_FLOODED, SCAR_DEEP_FACE,
    SCAR_KINGS_TOOTH, SCAR_WINCH, SCAR_BREAKER_PIT,
)

# Vault of the First Echo: exactly fourteen rooms.
ECHO_THRESHOLD = "echo_threshold"
ECHO_WHISPER_HALL = "echo_whisper_hall"
ECHO_BREATH_GALLERY = "echo_breath_gallery"
ECHO_RESONANCE_WELL = "echo_resonance_well"
ECHO_PLATE_WEST = "echo_plate_west"
ECHO_PLATE_EAST = "echo_plate_east"
ECHO_PLATE_DEEP = "echo_plate_deep"
ECHO_ARCHIVE = "echo_archive"
ECHO_BLIND_STAIR = "echo_blind_stair"
ECHO_LISTENING_BRIDGE = "echo_listening_bridge"
ECHO_LUNG_CHAMBER = "echo_lung_chamber"
ECHO_MIRROR_CHOIR = "echo_mirror_choir"
ECHO_LISTENER_COURT = "echo_listener_court"
ECHO_FIRST_BREATH_MARGIN = "echo_first_breath_margin"
ECHO_ROOM_KEYS = (
    ECHO_THRESHOLD, ECHO_WHISPER_HALL, ECHO_BREATH_GALLERY, ECHO_RESONANCE_WELL,
    ECHO_PLATE_WEST, ECHO_PLATE_EAST, ECHO_PLATE_DEEP, ECHO_ARCHIVE,
    ECHO_BLIND_STAIR, ECHO_LISTENING_BRIDGE, ECHO_LUNG_CHAMBER,
    ECHO_MIRROR_CHOIR, ECHO_LISTENER_COURT, ECHO_FIRST_BREATH_MARGIN,
)

ALL_ADVENTURE_ROOM_KEYS = (
    *ADVENTURE_OVERWORLD_KEYS, *TOLL_ROOM_KEYS, *BELL_ROOM_KEYS, *SCAR_ROOM_KEYS, *ECHO_ROOM_KEYS,
)

# ---------------------------------------------------------------------------
# Progress flags and quests
# ---------------------------------------------------------------------------
TOLL_COMPLETE = "adventure_toll_complete"
BELL_COMPLETE = "adventure_bell_complete"
SCAR_COMPLETE = "adventure_scar_complete"
ECHO_COMPLETE = "adventure_first_echo_complete"

TOLL_BOSS_DOWN = "adventure_toll_boss_down"
TOLL_STAIR_FOUND = "adventure_toll_stair_found"
TOLL_SECRET = "adventure_toll_wall_secret"
BELL_NAVE_HEARD = "adventure_bell_nave_heard"
BELL_GALLERY_HEARD = "adventure_bell_gallery_heard"
BELL_ROPES_SOLVED = "adventure_bell_ropes_solved"
BELL_BOSS_DOWN = "adventure_bell_boss_down"
BELL_SECRET = "adventure_bell_loft_secret"
SCAR_SURVEYED = "adventure_scar_surveyed"
SCAR_GANTRY_CLIMBED = "adventure_scar_gantry_climbed"
SCAR_BRAKE_RELEASED = "adventure_scar_brake_released"
SCAR_BOSS_DOWN = "adventure_scar_boss_down"
SCAR_SECRET = "adventure_scar_cache_secret"
ECHO_PLATE_FLAGS = {
    ECHO_PLATE_WEST: "adventure_echo_plate_west",
    ECHO_PLATE_EAST: "adventure_echo_plate_east",
    ECHO_PLATE_DEEP: "adventure_echo_plate_deep",
}
ECHO_GATE_OPEN = "adventure_echo_gate_open"
LISTENER_DOWN = "adventure_listener_down"
DEEP_SECRET_OPEN = "adventure_deep_secret_open"

TOLL_QUEST_KEY = "adventure_under_old_toll"
BELL_QUEST_KEY = "adventure_crooked_bell"
SCAR_QUEST_KEY = "adventure_kings_scar"
ECHO_QUEST_KEY = "adventure_vault_first_echo"

TOLL_QUEST = QuestDefinition(
    key=TOLL_QUEST_KEY,
    name="Under the Old Toll",
    style="structured",
    minimum_level=2,
    description="An abandoned tollhouse south of the Broken Mile has acquired fresh footprints, missing road cargo, and noises below its floorboards.",
    objective_steps=(
        ("enter_cellar", "Find the old toll road and descend into the cellar."),
        ("read_ledger", "SEARCH LEDGER in the old account room."),
        ("defeat_tollmaster", "Reach the counting room and defeat Tollmaster Vesk."),
        ("find_sublevel", "SEARCH WALL in the counting room after the fight."),
        ("read_carving", "Descend and EXAMINE CARVED WALL in the hidden sublevel."),
        ("complete", "You cleared the cellar and found a much older carved wall that the thieves did not make."),
    ),
)

BELL_QUEST = QuestDefinition(
    key=BELL_QUEST_KEY,
    name="The Crooked Bell",
    style="structured",
    minimum_level=3,
    description="A ruined roadside chapel in the Briarwood rings at the wrong hours. The safest way through is to listen before touching the ropes.",
    objective_steps=(
        ("hear_nave", "LISTEN in the ruined nave."),
        ("hear_gallery", "LISTEN in the east gallery."),
        ("solve_ropes", "Use the rope-room clues to PULL LOW and PULL HIGH in the heard sequence."),
        ("defeat_bellkeeper", "Climb to the belfry and defeat the Hollow Bellkeeper."),
        ("complete", "The Crooked Bell is quiet enough for travelers to use the Briarwood road again."),
    ),
)

SCAR_QUEST = QuestDefinition(
    key=SCAR_QUEST_KEY,
    name="King's Scar Survey",
    style="structured",
    minimum_level=5,
    description="Dwarf surveyors want the old quarry route reopened, but a vertical cut, a jammed freight brake, and something burrowing in the breaker pit have made the job dangerous.",
    objective_steps=(
        ("talk_brin", "TALK BRIN at King's Scar Approach."),
        ("climb_gantry", "Enter the quarry and CLIMB GANTRY in the lift house."),
        ("release_brake", "Reach the winch chamber and PULL BRAKE."),
        ("defeat_riftback", "Cross into the breaker pit and defeat the Riftback Matriarch."),
        ("complete", "The quarry route is surveyed and the lower freight path is safe enough for a work crew to assess."),
    ),
)

ECHO_QUEST = QuestDefinition(
    key=ECHO_QUEST_KEY,
    name="The Vault of the First Echo",
    style="structured",
    minimum_level=8,
    description=(
        "Three unrelated early expeditions all found the same impossible listening mark. Echo Ridge answers those marks with a stair into an older vault. "
        "Whatever waits below is not another god speaking; it is something studying an echo that has always been there."
    ),
    objective_steps=(
        ("touch_plates", "Find and TOUCH the three resonance plates in the vault."),
        ("reach_listener", "When all three plates answer, enter the Listener's Court."),
        ("defeat_listener", "Defeat the Listener Below. Pay attention when it begins to imitate a breath."),
        ("hear_first_echo", "After the Listener falls, LISTEN in the court."),
        ("complete", "You survived the Vault and learned the oldest surviving Waymeet account of Leviathan's one breath of life."),
    ),
)

ADVENTURE_QUESTS = (TOLL_QUEST, BELL_QUEST, SCAR_QUEST, ECHO_QUEST)

# ---------------------------------------------------------------------------
# Rewards and enemies
# ---------------------------------------------------------------------------
TOLL_KEY_ITEM = ItemDefinition(
    key="adventure_toll_brass_key",
    name="Old Toll Brass Key",
    description="A thick brass key from the cellar counting room. It no longer opens anything important, which makes it a better souvenir than credential.",
    category="trophy",
    tier=1,
)
BELL_CLAPPER_ITEM = ItemDefinition(
    key="adventure_crooked_clapper",
    name="Crooked Bell Clapper",
    description="A thumb-sized broken piece of dark bell metal that rings softly when set on stone.",
    category="trophy",
    tier=1,
)
SCAR_NAIL_ITEM = ItemDefinition(
    key="adventure_survey_nail",
    name="King's Scar Survey Nail",
    description="A broad Dwarven survey nail stamped with a new safe-route mark after the breaker pit was cleared.",
    category="trophy",
    tier=2,
)
FIRST_ECHO_SHARD = ItemDefinition(
    key="adventure_first_echo_shard",
    name="First Echo Shard",
    description="A smooth black sliver from the Listener's Court. It does not speak. Held close to the ear, it seems to return the room a fraction too late.",
    category="trophy",
    tier=2,
)
QUIET_STONE = ItemDefinition(
    key="adventure_quiet_stone",
    name="Quiet Stone",
    description="A plain gray stone from a hidden margin of the Vault. Its only remarkable quality is that every echo around it seems slightly farther away.",
    category="keepsake",
    tier=1,
)
ADVENTURE_ITEMS = (TOLL_KEY_ITEM, BELL_CLAPPER_ITEM, SCAR_NAIL_ITEM, FIRST_ECHO_SHARD, QUIET_STONE)

CELLAR_RAT = EnemyDefinition(
    key="adventure_cellar_rat", name="Cellar Rat", aliases=("rat", "cellar rat"),
    description="a large cellar rat fattened on stolen grain sacks", max_hp=22, armor_class=2,
    auto_attack_damage=3, auto_attack_interval=2.7, xp_reward=12,
)
ROAD_THIEF = EnemyDefinition(
    key="adventure_road_thief", name="Road Thief", aliases=("thief", "road thief", "bandit"),
    description="a road thief in mismatched coats who knows the tollhouse corridors better than the law", max_hp=34, armor_class=4,
    auto_attack_damage=5, auto_attack_interval=2.9, xp_reward=24,
)
BURROW_HOUND = EnemyDefinition(
    key="adventure_burrow_hound", name="Burrow Hound", aliases=("hound", "burrow hound"),
    description="a squat digging hound with clay packed between its teeth and a thief's rope collar", max_hp=46, armor_class=5,
    auto_attack_damage=6, auto_attack_interval=2.6, xp_reward=32,
)
TOLLMASTER = EnemyDefinition(
    key="adventure_tollmaster_vesk", name="Tollmaster Vesk", aliases=("vesk", "tollmaster", "tollmaster vesk"),
    description="the broad leader of the cellar thieves, carrying a hooked road cudgel and the confidence of someone who has charged tolls on a road he does not own",
    max_hp=96, armor_class=8, auto_attack_damage=8, auto_attack_interval=3.0, xp_reward=72,
)

BRIAR_WOLF = EnemyDefinition(
    key="adventure_briar_wolf", name="Briar Wolf", aliases=("wolf", "briar wolf"),
    description="a lean forest wolf with dry briars caught around its shoulders", max_hp=42, armor_class=5,
    auto_attack_damage=6, auto_attack_interval=2.7, xp_reward=30,
)
BELL_MITE = EnemyDefinition(
    key="adventure_bell_mite", name="Bell Mite Swarm", aliases=("mites", "mite", "bell mites", "swarm"),
    description="a glittering knot of hard-winged insects nesting in cracked bell metal", max_hp=52, armor_class=6,
    auto_attack_damage=6, auto_attack_interval=2.5, xp_reward=36,
)
HOLLOW_BELLKEEPER = EnemyDefinition(
    key="adventure_hollow_bellkeeper", name="Hollow Bellkeeper", aliases=("bellkeeper", "keeper", "hollow bellkeeper"),
    description="an old armored caretaker overgrown with pale root fibers, one hand fused around a bell hammer by years of resin and rust",
    max_hp=142, armor_class=10, auto_attack_damage=10, auto_attack_interval=3.0, xp_reward=110,
)

QUARRY_SKITTER = EnemyDefinition(
    key="adventure_quarry_skitter", name="Quarry Skitter", aliases=("skitter", "quarry skitter"),
    description="a slate-colored six-legged scavenger darting between drill holes", max_hp=62, armor_class=8,
    auto_attack_damage=7, auto_attack_interval=2.7, xp_reward=46,
)
STONEBORER = EnemyDefinition(
    key="adventure_stoneborer", name="Stoneborer", aliases=("stoneborer", "borer"),
    description="a thick-bodied burrow beast whose blunt horn is polished by stone", max_hp=82, armor_class=11,
    auto_attack_damage=9, auto_attack_interval=3.1, xp_reward=62,
)
RIFTBACK_MATRIARCH = EnemyDefinition(
    key="adventure_riftback_matriarch", name="Riftback Matriarch", aliases=("riftback", "matriarch", "riftback matriarch"),
    description="a quarry beast as large as a freight cart, its layered back plates split by old blasting scars and its boring horn chipped into a crown",
    max_hp=210, armor_class=15, auto_attack_damage=14, auto_attack_interval=3.0, xp_reward=175,
)

ECHO_WARDEN = EnemyDefinition(
    key="adventure_echo_warden", name="Echo Warden", aliases=("warden", "echo warden"),
    description="a jointed black figure that moves a half-beat after its own footfalls", max_hp=104, armor_class=13,
    auto_attack_damage=11, auto_attack_interval=2.8, xp_reward=82,
)
BREATH_MOTE = EnemyDefinition(
    key="adventure_breath_mote", name="Breath Mote", aliases=("mote", "breath mote"),
    description="a pale knot of air and grit orbiting an empty center", max_hp=88, armor_class=11,
    auto_attack_damage=10, auto_attack_interval=2.5, xp_reward=70,
)
LISTENER_BELOW = EnemyDefinition(
    key="adventure_listener_below", name="The Listener Below", aliases=("listener", "listener below", "the listener below"),
    description="a tall earless thing built from black stone plates and soft gray membranes, forever turning toward sounds that have already happened",
    max_hp=360, armor_class=18, auto_attack_damage=16, auto_attack_interval=2.8, xp_reward=310,
)
ADVENTURE_ENEMIES = (
    CELLAR_RAT, ROAD_THIEF, BURROW_HOUND, TOLLMASTER,
    BRIAR_WOLF, BELL_MITE, HOLLOW_BELLKEEPER,
    QUARRY_SKITTER, STONEBORER, RIFTBACK_MATRIARCH,
    ECHO_WARDEN, BREATH_MOTE, LISTENER_BELOW,
)

SURVEYOR_BRIN = NpcDefinition(
    key="adventure_surveyor_brin",
    name="Surveyor Brin Stonewake",
    short_description="a Dwarf surveyor comparing an old quarry profile against a fresh chalk sketch",
    room_key=KINGS_SCAR_APPROACH,
    role="King's Scar survey lead",
    dialogue=(
        "'The quarry is not cursed. It is vertical, neglected, and occupied. Those are three ordinary problems, which is plenty.'",
        "'CLIMB GANTRY in the lift house. Old freight brake is deeper in. PULL BRAKE when you reach the winch chamber.'",
    ),
)

# ---------------------------------------------------------------------------
# Room data
# ---------------------------------------------------------------------------
def _room(key: str, name: str, region: str, description: str, exits: dict[str, str], *, enemies: tuple[str, ...] = (), npcs: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key, name=name, region_key=region, description=description, exits=exits,
        enemy_keys=enemies, npc_keys=npcs, tags=("shared_world", "adventure_arc", *tags),
    )


ADVENTURE_OVERWORLD_ROOMS = (
    _room(OLD_TOLL_ROAD, "Old Toll Road", ADVENTURE_REGION_KEY,
          "South of the Broken Mile, the public road becomes an older strip of wheel-rutted stone. A roofless tollhouse crouches beside it. The cellar doors are newer than the ruin, and fresh boot marks disappear beneath them.",
          {"north": WAYMEET_BROKEN_MILE_KEY, "east": CROSSWIND_FARM}, tags=("level_2_5", "exploration")),
    _room(CROSSWIND_FARM, "Crosswind Farm Track", ADVENTURE_REGION_KEY,
          "Abandoned field walls make long low rectangles in the grass. The road bends between them toward a darker band of woods. Nothing attacks you here; the place exists mostly to make the distance between dangers feel real.",
          {"west": OLD_TOLL_ROAD, "east": BRIARWOOD_EDGE}, tags=("level_2_5", "road")),
    _room(BRIARWOOD_EDGE, "Briarwood Edge", ADVENTURE_REGION_KEY,
          "A stand of thorny trees leans over the road. Somewhere north, a cracked bell gives one dull note and then waits too long before the next. The undergrowth is thick enough to hide a chapel until you are nearly on top of it.",
          {"west": CROSSWIND_FARM, "south": WAYMEET_BRIARCUT_KEY, "east": ASH_BRIDGE}, tags=("level_3_6", "exploration")),
    _room(ASH_BRIDGE, "Ash Bridge", ADVENTURE_REGION_KEY,
          "A narrow timber bridge crosses a dry wash full of pale ash-colored stones. Cart traffic divides here: south returns toward Waymeet's quarry; east climbs toward a much larger cut in the hills.",
          {"west": BRIARWOOD_EDGE, "east": KINGS_SCAR_APPROACH}, tags=("level_4_7", "road")),
    _room(KINGS_SCAR_APPROACH, "King's Scar Approach", ADVENTURE_REGION_KEY,
          "The hill ahead has been opened by generations of quarrying until the cut resembles a wound visible from miles away. Dwarf survey flags mark a cautious route toward old lift machinery.",
          {"west": ASH_BRIDGE, "south": WAYMEET_QUARRY_KEY, "east": ECHO_RIDGE}, npcs=(SURVEYOR_BRIN.key,), tags=("level_5_8", "exploration")),
    _room(ECHO_RIDGE, "Echo Ridge", ADVENTURE_REGION_KEY,
          "The outer road reaches a bare ridge above Waymeet. Wind moves freely here, but three old stone marks on the ground return footsteps with an extra faint answer. The high road lies west below the ridge.",
          {"west": KINGS_SCAR_APPROACH, "north": WAYMEET_HIGH_ROAD_KEY}, tags=("level_2_10", "mystery")),
)

TOLL_ROOMS = (
    _room(TOLL_ENTRY, "Tollhouse Cellar Steps", TOLL_REGION_KEY, "Stone steps descend beneath the ruined tollhouse. A lantern hook holds a new lamp beside centuries-old mortar.", {"up": OLD_TOLL_ROAD, "east": TOLL_FEE_ROOM}, enemies=(CELLAR_RAT.key,), tags=("dungeon", "level_2_4")),
    _room(TOLL_FEE_ROOM, "Old Fee Room", TOLL_REGION_KEY, "A waist-high counter divides the chamber. The original toll slots are packed with dust; newer chalk marks divide stolen cargo by wagon rather than coin.", {"west": TOLL_ENTRY, "east": TOLL_STORAGE, "south": TOLL_RAT_RUN}, enemies=(ROAD_THIEF.key,), tags=("dungeon",)),
    _room(TOLL_STORAGE, "Stolen Stores", TOLL_REGION_KEY, "Road crates, flour sacks, lamp oil, and three very recognizable Waymeet axle assemblies have been stacked here with no attempt at subtlety.", {"west": TOLL_FEE_ROOM, "south": TOLL_LEDGER}, enemies=(ROAD_THIEF.key,), tags=("dungeon",)),
    _room(TOLL_RAT_RUN, "Rat Run", TOLL_REGION_KEY, "The ceiling drops low over a drainage passage chewed wider by animals. Rats scatter through gaps too small for a person.", {"north": TOLL_FEE_ROOM, "east": TOLL_SMUGGLER_CUT}, enemies=(CELLAR_RAT.key, CELLAR_RAT.key), tags=("dungeon", "side_route")),
    _room(TOLL_SMUGGLER_CUT, "Smuggler Cut", TOLL_REGION_KEY, "A rough newer tunnel bypasses the old toll rooms and joins the back of the cellar. Pick marks stop abruptly where older fitted stone begins again.", {"west": TOLL_RAT_RUN, "north": TOLL_KENNEL}, enemies=(BURROW_HOUND.key,), tags=("dungeon", "side_route")),
    _room(TOLL_LEDGER, "Account Room", TOLL_REGION_KEY, "A warped desk supports two ledgers: one ancient and illegible, one recent enough that several victims are still in Waymeet complaining. SEARCH LEDGER is the obvious next move.", {"north": TOLL_STORAGE, "south": TOLL_KENNEL}, enemies=(ROAD_THIEF.key,), tags=("dungeon", "clue")),
    _room(TOLL_KENNEL, "Burrow Kennel", TOLL_REGION_KEY, "Clay-streaked hounds sleep in collapsed toll cubbies. Beyond them, a reinforced door leads toward the old counting room.", {"north": TOLL_LEDGER, "west": TOLL_SMUGGLER_CUT, "south": TOLL_COUNTING}, enemies=(BURROW_HOUND.key,), tags=("dungeon",)),
    _room(TOLL_COUNTING, "Counting Room", TOLL_REGION_KEY, "The cellar thieves have made their camp around an old ironbound counting table. One wall looks oddly cleaner than the others, as if crates were moved away from it only recently.", {"north": TOLL_KENNEL}, tags=("dungeon", "boss", "secret")),
    _room(TOLL_HIDDEN_STAIR, "Hidden Survey Stair", TOLL_REGION_KEY, "A narrow stair predates the tollhouse above it. The steps descend only a short distance before opening into a chamber cut with tools much finer than the thieves own.", {"up": TOLL_COUNTING, "down": TOLL_CARVED_SUBLEVEL}, tags=("dungeon", "secret")),
    _room(TOLL_CARVED_SUBLEVEL, "Carved Sublevel", TOLL_REGION_KEY, "The chamber is empty except for one long wall carved with repeated wave-like lines around a single open shape. Nothing here matches the tollhouse architecture. EXAMINE CARVED WALL is deliberately obvious.", {"up": TOLL_HIDDEN_STAIR}, tags=("dungeon", "secret", "lore")),
)

BELL_ROOMS = (
    _room(BELL_GATE, "Briar Chapel Gate", BELL_REGION_KEY, "A broken stone arch stands in living briars. The chapel beyond has no roof over its western half, yet its bell still sounds on windless days.", {"south": BRIARWOOD_EDGE, "north": BELL_NAVE}, enemies=(BRIAR_WOLF.key,), tags=("dungeon", "level_3_5")),
    _room(BELL_NAVE, "Ruined Nave", BELL_REGION_KEY, "Rain falls through the roof onto old benches. Each drop should sound random, but the room keeps returning three distinct pitches. LISTEN is printed by experience more clearly than any quest marker.", {"south": BELL_GATE, "north": BELL_CHOIR, "west": BELL_WEST_GALLERY, "east": BELL_EAST_GALLERY}, tags=("dungeon", "sound_puzzle")),
    _room(BELL_CHOIR, "Rotten Choir", BELL_REGION_KEY, "Half a choir loft hangs from the north wall. Old hymn boards have rotted blank except for three nail holes placed low, high, low.", {"south": BELL_NAVE, "down": BELL_ROOT_CELLAR}, enemies=(BELL_MITE.key,), tags=("dungeon", "clue")),
    _room(BELL_ROOT_CELLAR, "Root Cellar", BELL_REGION_KEY, "Tree roots have split the foundation into cramped aisles. Bell mites nest wherever dark metal fragments have fallen through the floor.", {"up": BELL_CHOIR, "east": BELL_STAIR}, enemies=(BELL_MITE.key, BELL_MITE.key), tags=("dungeon",)),
    _room(BELL_WEST_GALLERY, "West Gallery", BELL_REGION_KEY, "The western aisle is open to the woods. A bell rope end has been tied around a pillar to stop it knocking in the wind.", {"east": BELL_NAVE}, enemies=(BRIAR_WOLF.key,), tags=("dungeon", "side_room")),
    _room(BELL_EAST_GALLERY, "East Gallery", BELL_REGION_KEY, "Three cracked bronze plates hang here. Wind touches all three, but only the low plate answers before the high plate and then the low again. LISTEN makes the order unmistakable.", {"west": BELL_NAVE, "north": BELL_STAIR}, tags=("dungeon", "sound_puzzle")),
    _room(BELL_STAIR, "Cracked Bell Stair", BELL_REGION_KEY, "A spiral stair climbs around a hollow center. The upper door is held by a rope-and-counterweight latch whose lines disappear into the room above.", {"south": BELL_EAST_GALLERY, "west": BELL_ROOT_CELLAR, "up": BELL_ROPE_ROOM}, enemies=(BELL_MITE.key,), tags=("dungeon",)),
    _room(BELL_ROPE_ROOM, "Rope Room", BELL_REGION_KEY, "Two surviving ropes hang from the beams, one ending near the floor and one much higher. They are helpfully different enough to call LOW and HIGH. The heard sequence is the key.", {"down": BELL_STAIR}, tags=("dungeon", "puzzle")),
    _room(BELL_BELFRY, "Crooked Belfry", BELL_REGION_KEY, "The surviving bell hangs at a visible angle from a split beam. Beneath it waits the old keeper, less alive than duty and more rooted than corpse.", {"down": BELL_ROPE_ROOM}, tags=("dungeon", "boss")),
    _room(BELL_ECHO_LOFT, "Echo Loft", BELL_REGION_KEY, "A narrow crawlspace above the belfry contains no treasure chest. Someone once came here simply to test how long one quiet bell-note could remain audible in wood.", {"down": BELL_BELFRY}, tags=("dungeon", "secret", "lore")),
)

SCAR_ROOMS = (
    _room(SCAR_GATE, "King's Scar Gate", SCAR_REGION_KEY, "Two Dwarf-cut pillars mark the quarry entrance. Safety notices have been refreshed more recently than the road.", {"west": KINGS_SCAR_APPROACH, "east": SCAR_LIFT}, enemies=(QUARRY_SKITTER.key,), tags=("dungeon", "level_5_7")),
    _room(SCAR_LIFT, "Lift House", SCAR_REGION_KEY, "A dead freight lift occupies half the room. Above it, an inspection gantry still spans the shaft. CLIMB GANTRY is stenciled directly on an old maintenance board.", {"west": SCAR_GATE, "east": SCAR_LOWER_CUT}, tags=("dungeon", "vertical")),
    _room(SCAR_LOWER_CUT, "Lower Cut", SCAR_REGION_KEY, "The quarry floor falls away in benches. Old drill holes create black rows in pale stone while skitters dart between spoil piles.", {"west": SCAR_LIFT, "north": SCAR_POWDER, "east": SCAR_BROKEN_BRIDGE}, enemies=(QUARRY_SKITTER.key,), tags=("dungeon",)),
    _room(SCAR_POWDER, "Powder Store", SCAR_REGION_KEY, "The blasting powder is long gone. Empty waxed barrels remain, along with warning plaques so thoroughly bureaucratic they survived looting.", {"south": SCAR_LOWER_CUT, "east": SCAR_FOREMAN}, enemies=(STONEBORER.key,), tags=("dungeon", "side_room")),
    _room(SCAR_BROKEN_BRIDGE, "Broken Freight Bridge", SCAR_REGION_KEY, "A retractable freight bridge hangs six feet short of the opposite ledge. The brake cable disappears toward a winch chamber deeper in the cut.", {"west": SCAR_LOWER_CUT, "up": SCAR_CRANE_WALK}, tags=("dungeon", "vertical")),
    _room(SCAR_CRANE_WALK, "Crane Walk", SCAR_REGION_KEY, "A narrow iron walkway follows the old quarry crane track above the cut. The view makes the whole dungeon legible: lift house behind, flooded shaft below, breaker pit farther east.", {"down": SCAR_BROKEN_BRIDGE, "east": SCAR_FOREMAN}, enemies=(QUARRY_SKITTER.key,), tags=("dungeon", "vertical")),
    _room(SCAR_FOREMAN, "Foreman's Booth", SCAR_REGION_KEY, "A stone booth overlooks the workface. Shift boards show that the last crew abandoned the lower levels after repeated tunnel collapses from something moving under the blast line.", {"west": SCAR_CRANE_WALK, "south": SCAR_POWDER, "east": SCAR_FLOODED}, tags=("dungeon", "lore")),
    _room(SCAR_FLOODED, "Flooded Shaft", SCAR_REGION_KEY, "Groundwater fills the bottom of an old prospect shaft. A ledge continues along the eastern wall toward fresh claw marks.", {"west": SCAR_FOREMAN, "east": SCAR_DEEP_FACE}, enemies=(STONEBORER.key,), tags=("dungeon",)),
    _room(SCAR_DEEP_FACE, "Deep Face", SCAR_REGION_KEY, "The last worked quarry face is covered in survey marks from several eras. Some marks are fresh chalk; one much older cluster has been deliberately chipped almost away. SEARCH SURVEY MARKS may reward curiosity.", {"west": SCAR_FLOODED, "east": SCAR_KINGS_TOOTH}, enemies=(QUARRY_SKITTER.key,), tags=("dungeon", "secret")),
    _room(SCAR_KINGS_TOOTH, "King's Tooth", SCAR_REGION_KEY, "A triangular pillar of untouched stone divides two quarry cuts. Workers nicknamed it the King's Tooth and built the freight brake around its base.", {"west": SCAR_DEEP_FACE, "east": SCAR_WINCH}, enemies=(STONEBORER.key,), tags=("dungeon",)),
    _room(SCAR_WINCH, "Freight Winch Chamber", SCAR_REGION_KEY, "A geared brake drum fills the wall. The release lever is rusted but intact. PULL BRAKE will either solve the route problem or make a memorable noise.", {"west": SCAR_KINGS_TOOTH}, tags=("dungeon", "puzzle")),
    _room(SCAR_BREAKER_PIT, "Breaker Pit", SCAR_REGION_KEY, "Beyond the restored freight bridge, the quarry ends in a circular pit gouged by a single enormous burrower. Loose stone trembles each time the creature turns beneath it.", {"west": SCAR_WINCH}, tags=("dungeon", "boss")),
)

ECHO_ROOMS = (
    _room(ECHO_THRESHOLD, "Vault Threshold", ECHO_REGION_KEY, "A stair descends from Echo Ridge into fitted black stone. The first inscription is practical rather than grand: LISTEN BEFORE YOU ANSWER.", {"up": ECHO_RIDGE, "east": ECHO_WHISPER_HALL}, enemies=(ECHO_WARDEN.key,), tags=("dungeon", "level_8_10")),
    _room(ECHO_WHISPER_HALL, "Whisper Hall", ECHO_REGION_KEY, "Your footfalls return from the wrong direction. No voice follows them, only their shape.", {"west": ECHO_THRESHOLD, "east": ECHO_BREATH_GALLERY, "south": ECHO_PLATE_WEST}, enemies=(BREATH_MOTE.key,), tags=("dungeon", "acoustic")),
    _room(ECHO_BREATH_GALLERY, "Breath Gallery", ECHO_REGION_KEY, "Shallow grooves flow across the walls like diagrams of air moving around an unseen body. None form letters.", {"west": ECHO_WHISPER_HALL, "east": ECHO_RESONANCE_WELL, "north": ECHO_PLATE_EAST}, enemies=(ECHO_WARDEN.key,), tags=("dungeon", "lore")),
    _room(ECHO_RESONANCE_WELL, "Resonance Well", ECHO_REGION_KEY, "A dry circular shaft drops farther than thrown pebbles can explain. Three side passages lead toward three identical stone plates.", {"west": ECHO_BREATH_GALLERY, "south": ECHO_PLATE_DEEP, "east": ECHO_ARCHIVE}, enemies=(BREATH_MOTE.key,), tags=("dungeon", "hub")),
    _room(ECHO_PLATE_WEST, "Western Resonance Plate", ECHO_REGION_KEY, "A hand-sized black plate is set into the wall. Its worn center invites exactly one verb: TOUCH PLATE.", {"north": ECHO_WHISPER_HALL}, tags=("dungeon", "puzzle")),
    _room(ECHO_PLATE_EAST, "Eastern Resonance Plate", ECHO_REGION_KEY, "The second plate is identical except for a shallow ring around its edge. TOUCH PLATE and see whether it answers differently.", {"south": ECHO_BREATH_GALLERY}, tags=("dungeon", "puzzle")),
    _room(ECHO_PLATE_DEEP, "Deep Resonance Plate", ECHO_REGION_KEY, "The third plate sits at shoulder height above old scrape marks in the floor. TOUCH PLATE completes the obvious set.", {"north": ECHO_RESONANCE_WELL}, tags=("dungeon", "puzzle")),
    _room(ECHO_ARCHIVE, "Soundless Archive", ECHO_REGION_KEY, "Stone shelves hold tablets whose markings are grooves meant to be traced rather than read. One repeated image resembles the marks found beneath the old tollhouse.", {"west": ECHO_RESONANCE_WELL, "east": ECHO_BLIND_STAIR}, enemies=(ECHO_WARDEN.key,), tags=("dungeon", "lore")),
    _room(ECHO_BLIND_STAIR, "Blind Stair", ECHO_REGION_KEY, "The stair turns so tightly that each landing hides the next. Sound is a better map than sight here.", {"west": ECHO_ARCHIVE, "up": ECHO_LISTENING_BRIDGE}, enemies=(BREATH_MOTE.key,), tags=("dungeon",)),
    _room(ECHO_LISTENING_BRIDGE, "Listening Bridge", ECHO_REGION_KEY, "A narrow span crosses the resonance well at its deepest point. Every party member's steps return at a slightly different delay.", {"down": ECHO_BLIND_STAIR, "east": ECHO_LUNG_CHAMBER}, enemies=(ECHO_WARDEN.key,), tags=("dungeon", "acoustic")),
    _room(ECHO_LUNG_CHAMBER, "False Lung Chamber", ECHO_REGION_KEY, "Flexible gray membranes line a stone frame like an anatomical model built by someone who had only heard breathing described. A chain runs toward the Listener's Court.", {"west": ECHO_LISTENING_BRIDGE, "east": ECHO_MIRROR_CHOIR}, enemies=(BREATH_MOTE.key,), tags=("dungeon", "lore")),
    _room(ECHO_MIRROR_CHOIR, "Mirror Choir", ECHO_REGION_KEY, "Black panels repeat your outline without reflecting light. Three tiny marks at the base resemble the hidden signs from the tollhouse, bell loft, and quarry face.", {"west": ECHO_LUNG_CHAMBER}, tags=("dungeon", "secret", "boss_gate")),
    _room(ECHO_LISTENER_COURT, "Listener's Court", ECHO_REGION_KEY, "The court is built around a shallow central depression. Four resonator chains hang at the corners. The Listener Below waits in the middle, perfectly still until somebody makes a deliberate sound.", {"west": ECHO_MIRROR_CHOIR}, tags=("dungeon", "boss", "capstone")),
    _room(ECHO_FIRST_BREATH_MARGIN, "Margin of the First Breath", ECHO_REGION_KEY, "A hidden margin chamber contains one surviving statement in plain later script: Leviathan spoke everything into being in one breath of life. No second word is promised or expected. The echo is simply there. The room offers no doctrine beyond that sentence.", {"north": ECHO_MIRROR_CHOIR}, tags=("dungeon", "deep_secret", "lore")),
)

ALL_ADVENTURE_ROOMS = (*ADVENTURE_OVERWORLD_ROOMS, *TOLL_ROOMS, *BELL_ROOMS, *SCAR_ROOMS, *ECHO_ROOMS)

# ---------------------------------------------------------------------------
# Room features: descriptions tell players the useful verbs rather than forcing
# them to guess parser vocabulary.
# ---------------------------------------------------------------------------
def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(key=key, name=name, summary=summary, examine_text=examine, aliases=aliases)


def _merge(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    overrides = {x.direction: x for x in existing.exit_overrides}
    overrides.update({x.direction: x for x in extra.exit_overrides})
    exits = {(x.direction, x.destination_key): x for x in existing.extra_exits}
    exits.update({(x.direction, x.destination_key): x for x in extra.extra_exits})
    features = {x.key: x for x in existing.features}
    features.update({x.key: x for x in extra.features})
    layers = {x.key: x for x in existing.description_layers}
    layers.update({x.key: x for x in extra.description_layers})
    return RoomAugmentation(tuple(overrides.values()), tuple(exits.values()), tuple(features.values()), tuple(layers.values()))


def adventure_augmentations() -> dict[str, RoomAugmentation]:
    return {
        WAYMEET_BROKEN_MILE_KEY: RoomAugmentation(extra_exits=(ExitDefinition("south", OLD_TOLL_ROAD, "Old Toll Road", "You follow the older road south toward a roofless tollhouse.", ViewCondition(min_level=2)),)),
        WAYMEET_BRIARCUT_KEY: RoomAugmentation(extra_exits=(ExitDefinition("east", BRIARWOOD_EDGE, "Briarwood Track", "You take the narrow east track beneath the briars.", ViewCondition(min_level=3)),)),
        WAYMEET_QUARRY_KEY: RoomAugmentation(extra_exits=(ExitDefinition("north", KINGS_SCAR_APPROACH, "King's Scar Track", "You follow old quarry stakes toward the larger cut in the hills.", ViewCondition(min_level=5)),)),
        WAYMEET_HIGH_ROAD_KEY: RoomAugmentation(extra_exits=(ExitDefinition("east", ECHO_RIDGE, "Echo Ridge", "You climb a bare side ridge where the wind returns footsteps strangely.", ViewCondition(min_level=2)),)),
        OLD_TOLL_ROAD: RoomAugmentation(
            extra_exits=(ExitDefinition("down", TOLL_ENTRY, "Tollhouse Cellar", "You descend through the newer cellar doors.", ViewCondition(min_level=2)),),
            features=(_feature("toll_cellar_doors", "Cellar Doors", "freshly repaired doors beneath a ruined tollhouse", "The doors are not locked. Fresh boot marks go down. DOWN enters the first compact dungeon.", ("doors", "cellar", "tollhouse")),),
        ),
        BRIARWOOD_EDGE: RoomAugmentation(
            extra_exits=(ExitDefinition("north", BELL_GATE, "Crooked Bell Chapel", "You push north through the briars toward the cracked bell.", ViewCondition(min_level=3)),),
            features=(_feature("crooked_bell_sound", "Crooked Bell", "one dull bell-note arriving at the wrong interval", "The bell is north. This dungeon rewards LISTEN before PULL.", ("bell", "sound", "chapel")),),
        ),
        KINGS_SCAR_APPROACH: RoomAugmentation(
            extra_exits=(ExitDefinition("east", SCAR_GATE, "King's Scar Quarry", "You pass the survey flags into the abandoned quarry.", ViewCondition(min_level=5)),),
            features=(_feature("scar_survey_flags", "Survey Flags", "fresh Dwarven flags marking the safer quarry line", "The flags repeatedly mark the old lift house. TALK BRIN before committing to the deeper cut.", ("flags", "survey", "quarry")),),
        ),
        ECHO_RIDGE: RoomAugmentation(
            extra_exits=(ExitDefinition(
                "down", ECHO_THRESHOLD, "Vault Stair", "The three marks answer together and a seam in the ridge opens onto a descending stair.",
                ViewCondition(required_flags=(TOLL_COMPLETE, BELL_COMPLETE, SCAR_COMPLETE), min_level=8), hidden_when_unavailable=True,
            ),),
            features=(_feature("echo_ridge_marks", "Three Listening Marks", "three old marks that return footsteps with an extra answer", "Three early expeditions elsewhere around Waymeet contain matching marks. The ridge opens only after all three dungeon clears and level 8.", ("marks", "echo marks", "listening marks")),),
        ),
        TOLL_LEDGER: RoomAugmentation(features=(_feature("recent_ledger", "Recent Ledger", "a thief's ledger naming stolen wagons and payments", "SEARCH LEDGER to compare entries and identify who is running the cellar.", ("ledger", "book", "accounts")),)),
        TOLL_COUNTING: RoomAugmentation(
            extra_exits=(ExitDefinition("down", TOLL_HIDDEN_STAIR, "Hidden Stair", "You squeeze through the newly exposed wall seam and descend.", ViewCondition(required_flags=(TOLL_STAIR_FOUND,), min_level=2), hidden_when_unavailable=True),),
            features=(_feature("clean_wall", "Clean Wall", "one suspiciously clean cellar wall", "After Tollmaster Vesk is down, SEARCH WALL can reveal whether the clean stone hides anything.", ("wall", "clean wall", "stone")),),
        ),
        TOLL_CARVED_SUBLEVEL: RoomAugmentation(features=(_feature("carved_wall", "Carved Wall", "wave-like lines surrounding one open shape", "EXAMINE CARVED WALL. The pattern will matter much later, but the cellar itself does not explain it.", ("wall", "carving", "carved wall", "marks")),)),
        BELL_NAVE: RoomAugmentation(features=(_feature("three_pitches", "Three Returning Pitches", "rain notes repeating more regularly than rain should", "LISTEN. The game tells you the usable clue rather than asking you to guess an audio verb.", ("pitches", "rain", "sound")),)),
        BELL_EAST_GALLERY: RoomAugmentation(features=(_feature("bronze_plates", "Cracked Bronze Plates", "low, high, and low plates touched by wind", "LISTEN here after the nave. The rope order becomes explicit.", ("plates", "bronze plates", "sound")),)),
        BELL_ROPE_ROOM: RoomAugmentation(
            extra_exits=(ExitDefinition("up", BELL_BELFRY, "Belfry Latch", "The solved rope latch releases and the upper door swings inward.", ViewCondition(required_flags=(BELL_ROPES_SOLVED,), min_level=3), hidden_when_unavailable=True),),
            features=(_feature("bell_ropes", "Low and High Ropes", "two surviving bell-control ropes", "Use PULL LOW and PULL HIGH in the three-note sequence you heard. Wrong pulls reset the sequence without consuming anything.", ("ropes", "low rope", "high rope")),),
        ),
        BELL_BELFRY: RoomAugmentation(
            extra_exits=(ExitDefinition("up", BELL_ECHO_LOFT, "Echo Loft", "You climb into the crawlspace above the bell.", ViewCondition(required_flags=(BELL_SECRET,), min_level=3), hidden_when_unavailable=True),),
            features=(_feature("bell_rafters", "Split Rafters", "old rafters disappearing above the bell frame", "After the Bellkeeper falls, SEARCH RAFTERS may reveal a place the old caretaker used for listening tests.", ("rafters", "loft", "beams")),),
        ),
        SCAR_LIFT: RoomAugmentation(features=(_feature("inspection_gantry", "Inspection Gantry", "a narrow maintenance walk above the dead lift", "CLIMB GANTRY. The command demonstrates vertical exploration before the quarry asks you to rely on it.", ("gantry", "lift", "walk")),)),
        SCAR_DEEP_FACE: RoomAugmentation(features=(_feature("survey_marks", "Old Survey Marks", "a nearly erased cluster among newer chalk", "SEARCH SURVEY MARKS if you care about the older history. It is optional and gives no power reward.", ("marks", "survey marks", "chalk")),)),
        SCAR_WINCH: RoomAugmentation(
            extra_exits=(ExitDefinition("east", SCAR_BREAKER_PIT, "Restored Freight Bridge", "The released brake lets the freight bridge settle across the gap to the breaker pit.", ViewCondition(required_flags=(SCAR_BRAKE_RELEASED,), min_level=5), hidden_when_unavailable=True),),
            features=(_feature("freight_brake", "Freight Brake", "a rusted but intact geared brake lever", "PULL BRAKE to release the bridge. This is an environmental action, not a hidden parser trick.", ("brake", "lever", "winch")),),
        ),
        ECHO_PLATE_WEST: RoomAugmentation(features=(_feature("west_plate", "Resonance Plate", "a worn black plate", "TOUCH PLATE.", ("plate", "stone", "resonance plate")),)),
        ECHO_PLATE_EAST: RoomAugmentation(features=(_feature("east_plate", "Resonance Plate", "a ringed black plate", "TOUCH PLATE.", ("plate", "stone", "resonance plate")),)),
        ECHO_PLATE_DEEP: RoomAugmentation(features=(_feature("deep_plate", "Resonance Plate", "the deepest black plate", "TOUCH PLATE.", ("plate", "stone", "resonance plate")),)),
        ECHO_MIRROR_CHOIR: RoomAugmentation(
            extra_exits=(
                ExitDefinition("east", ECHO_LISTENER_COURT, "Listener's Court", "All three resonance plates answer and the black panels separate.", ViewCondition(required_flags=(ECHO_GATE_OPEN,), min_level=8), hidden_when_unavailable=True),
                ExitDefinition("south", ECHO_FIRST_BREATH_MARGIN, "Hidden Margin", "The three optional marks align and a narrow margin opens in the wall.", ViewCondition(required_flags=(DEEP_SECRET_OPEN,), min_level=8), hidden_when_unavailable=True),
            ),
            features=(_feature("three_secret_marks", "Three Tiny Marks", "three tiny signs matching optional discoveries elsewhere", "If you found all three outer secrets, TOUCH THREE MARKS here. Otherwise the marks remain inert and unexplained.", ("marks", "three marks", "tiny marks")),),
        ),
        ECHO_LISTENER_COURT: RoomAugmentation(features=(
            _feature("resonator_chains", "Resonator Chains", "four chains at the corners of the court", "If the Listener begins imitating a breath, LISTEN first. When you understand the false rhythm, PULL RESONATOR to collapse it.", ("chains", "resonator", "resonators")),
        )),
    }

# ---------------------------------------------------------------------------
# Content registration
# ---------------------------------------------------------------------------
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


def install_adventure_content(world_service=None) -> None:
    for quest in ADVENTURE_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for item in ADVENTURE_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for enemy in ADVENTURE_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    _replace_npc(SURVEYOR_BRIN)
    for room in ALL_ADVENTURE_ROOMS:
        _replace_room(room)

    economy.LOOT_TABLES[CELLAR_RAT.key] = (economy.LootDrop("rough_hide", 1, chance=0.35),)
    economy.LOOT_TABLES[ROAD_THIEF.key] = (economy.LootDrop("iron_ore", 1, chance=0.30),)
    economy.LOOT_TABLES[BURROW_HOUND.key] = (economy.LootDrop("rough_hide", 1),)
    economy.LOOT_TABLES[BRIAR_WOLF.key] = (economy.LootDrop("rough_hide", 1, chance=0.55),)
    economy.LOOT_TABLES[QUARRY_SKITTER.key] = (economy.LootDrop("iron_ore", 1, chance=0.40),)
    economy.LOOT_TABLES[STONEBORER.key] = (economy.LootDrop("coal", 1, chance=0.50),)

    if world_service is None:
        return
    for room in ALL_ADVENTURE_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in adventure_augmentations().items():
        world_service.augmentations[room_key] = _merge(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*ALL_ADVENTURE_ROOM_KEYS, WAYMEET_BROKEN_MILE_KEY, WAYMEET_BRIARCUT_KEY, WAYMEET_QUARRY_KEY, WAYMEET_HIGH_ROAD_KEY):
            cache.pop(key, None)

# ---------------------------------------------------------------------------
# Runtime helpers
# ---------------------------------------------------------------------------
def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _refresh(session) -> None:
    if session.character is None:
        return
    current = session.database.get_character_by_name(session.character.name)
    if current is not None:
        session.character = current


def _start_if_needed(session, quest_key: str, first_step: str, minimum_level: int, complete_flag: str) -> None:
    if session.character is None or session.character.level < minimum_level or complete_flag in _flags(session):
        return
    if _quest(session, quest_key) is None:
        session.database.start_quest(session.character.id, quest_key, first_step)


def _advance(session, quest_key: str, expected: str, next_step: str) -> bool:
    if session.character is None:
        return False
    q = _quest(session, quest_key)
    if q and q["status"] == "active" and q["current_step"] == expected:
        session.database.advance_quest(session.character.id, quest_key, next_step)
        return True
    return False


def _complete(session, quest_key: str, complete_flag: str, *, xp: int, item_key: str, text: str) -> bool:
    if session.character is None or complete_flag in _flags(session):
        return False
    session.database.complete_quest(session.character.id, quest_key)
    session.database.grant_flag(session.character.id, complete_flag)
    session.database.add_experience(session.character.id, xp)
    session.database.add_item(session.character.id, item_key, 1)
    _refresh(session)
    return True


def _participants_here(session) -> list:
    try:
        members = _party_sessions_here(session)
    except Exception:
        members = [session]
    return members or [session]


def _begin_combat(session, definition: EnemyDefinition) -> bool:
    if session.character is None or session.combatant is None or session.active_enemy is not None:
        return False
    enemy = EnemyState(definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


def _all_outer_secrets(flags: set[str]) -> bool:
    return {TOLL_SECRET, BELL_SECRET, SCAR_SECRET}.issubset(flags)


def adventure_progress(flags: set[str], level: int) -> tuple[str, ...]:
    rows = []
    rows.append("Old Toll: CLEARED" if TOLL_COMPLETE in flags else ("Old Toll: available" if level >= 2 else "Old Toll: level 2"))
    rows.append("Crooked Bell: CLEARED" if BELL_COMPLETE in flags else ("Crooked Bell: available" if level >= 3 else "Crooked Bell: level 3"))
    rows.append("King's Scar: CLEARED" if SCAR_COMPLETE in flags else ("King's Scar: available" if level >= 5 else "King's Scar: level 5"))
    if ECHO_COMPLETE in flags:
        rows.append("Vault of the First Echo: CLEARED")
    elif level < 8:
        rows.append("Vault of the First Echo: level 8 and three prior clears")
    elif {TOLL_COMPLETE, BELL_COMPLETE, SCAR_COMPLETE}.issubset(flags):
        rows.append("Vault of the First Echo: Echo Ridge is answering")
    else:
        rows.append("Vault of the First Echo: three prior clears still required")
    return tuple(rows)


async def _show_explore(session) -> None:
    flags = _flags(session)
    await session.send("\r\n--- Waymeet Outer Roads ---\r\n")
    await session.send("The roads around Waymeet form a connected adventure ring rather than four menu-selected instances. Explore south of the Broken Mile, east of Briarcut, north of the quarry, and along Echo Ridge.\r\n")
    for row in adventure_progress(flags, session.character.level):
        await session.send(f"- {row}\r\n")
    secret_count = len({TOLL_SECRET, BELL_SECRET, SCAR_SECRET} & flags)
    await session.send(f"Optional outer secrets noticed: {secret_count}/3. The game will not name the missing locations.\r\n")
    await session.send("Useful exploration verbs are written into room features when relevant: SEARCH, LISTEN, CLIMB, PULL, TOUCH. CLASS shows the combat kit you already have for real-time fights.\r\n")


async def _talk_brin(session) -> bool:
    if session.character is None or session.character.current_room != KINGS_SCAR_APPROACH:
        return False
    _start_if_needed(session, SCAR_QUEST_KEY, "talk_brin", 5, SCAR_COMPLETE)
    if SCAR_SURVEYED not in _flags(session):
        session.database.grant_flag(session.character.id, SCAR_SURVEYED)
    _advance(session, SCAR_QUEST_KEY, "talk_brin", "climb_gantry")
    await session.send("Brin taps three points on the quarry profile. 'Old lift house first. CLIMB GANTRY so you can read the cut from above. Deeper in, the freight brake is jammed. PULL BRAKE when you find the winch. The thing in the breaker pit is an animal, not a prophecy.'\r\n")
    return True


async def _search(session, target: str) -> bool:
    if session.character is None:
        return False
    room = session.character.current_room
    wanted = " ".join(target.lower().split())
    if room == TOLL_LEDGER and (not wanted or "ledger" in wanted or "desk" in wanted):
        _start_if_needed(session, TOLL_QUEST_KEY, "enter_cellar", 2, TOLL_COMPLETE)
        _advance(session, TOLL_QUEST_KEY, "read_ledger", "defeat_tollmaster")
        await session.send("You compare the recent entries. Every extorted wagon points to the same hand: Vesk, calling himself Tollmaster without any authority beyond a cudgel. The last line says he moved the oldest crates away from the counting-room wall because 'the stone hums.'\r\n")
        return True
    if room == TOLL_COUNTING and (not wanted or "wall" in wanted or "stone" in wanted):
        if TOLL_BOSS_DOWN not in _flags(session):
            await session.send("Vesk is still controlling the room. Searching masonry while he swings a hooked cudgel at you would be ambitious.\r\n")
            return True
        if TOLL_STAIR_FOUND not in _flags(session):
            session.database.grant_flag(session.character.id, TOLL_STAIR_FOUND)
            _advance(session, TOLL_QUEST_KEY, "find_sublevel", "read_carving")
        await session.send("Behind the recently moved crates, one block pivots inward. A narrow seam opens onto a stair that is clearly older than the tollhouse. DOWN is now available.\r\n")
        return True
    if room == BELL_BELFRY and (not wanted or "rafter" in wanted or "beam" in wanted or "loft" in wanted):
        if BELL_BOSS_DOWN not in _flags(session):
            await session.send("The Hollow Bellkeeper is still beneath the rafters. Deal with the keeper first.\r\n")
            return True
        if BELL_SECRET not in _flags(session):
            session.database.grant_flag(session.character.id, BELL_SECRET)
            await session.send("One split beam hides a handhold and a crawlspace above the bell. UP now leads to the Echo Loft. This is optional history, not progression power.\r\n")
        else:
            await session.send("You already found the crawlspace above the belfry.\r\n")
        return True
    if room == SCAR_DEEP_FACE and (not wanted or "mark" in wanted or "survey" in wanted or "chalk" in wanted):
        if SCAR_SECRET not in _flags(session):
            session.database.grant_flag(session.character.id, SCAR_SECRET)
            await session.send("Beneath the chipped survey marks you find the same open-centered listening sign seen in much older stone elsewhere. A Dwarf hand later tried to erase it, then stopped halfway. You record the shape and leave the wall intact.\r\n")
        else:
            await session.send("The almost-erased listening mark is still here. You have already recorded it.\r\n")
        return True
    await session.send("You search carefully, but this room does not expose a special SEARCH interaction. Important searches are telegraphed in descriptions or EXAMINE text.\r\n")
    return True


async def _listen(session, target: str = "") -> bool:
    if session.character is None:
        return False
    room = session.character.current_room
    flags = _flags(session)
    if room == BELL_NAVE:
        if BELL_NAVE_HEARD not in flags:
            session.database.grant_flag(session.character.id, BELL_NAVE_HEARD)
        _start_if_needed(session, BELL_QUEST_KEY, "hear_nave", 3, BELL_COMPLETE)
        _advance(session, BELL_QUEST_KEY, "hear_nave", "hear_gallery")
        await session.send("You stop moving. Beneath rain and leaf noise, the room keeps returning three notes with a gap after the third. Low. High. Low. The pattern is too regular to be weather.\r\n")
        return True
    if room == BELL_EAST_GALLERY:
        if BELL_GALLERY_HEARD not in flags:
            session.database.grant_flag(session.character.id, BELL_GALLERY_HEARD)
        _advance(session, BELL_QUEST_KEY, "hear_gallery", "solve_ropes")
        await session.send("The cracked plates confirm it without ambiguity: LOW, HIGH, LOW. Whatever the ropes upstairs control, that is the sequence.\r\n")
        return True
    if room == ECHO_LISTENER_COURT and getattr(session, "_listener_breath_pending", False):
        session._listener_breath_heard = True
        await session.send("You listen past the combat. The chamber is not producing a living breath; four corner resonators are forcing air through the false lung next door in sequence. The imitation is mechanical enough to interrupt. PULL RESONATOR now.\r\n")
        return True
    if room == ECHO_LISTENER_COURT and LISTENER_DOWN in flags:
        if _complete(session, ECHO_QUEST_KEY, ECHO_COMPLETE, xp=320, item_key=FIRST_ECHO_SHARD.key, text=""):
            moment_day = 0
            try:
                from mud.astralis_time import ASTRALIS_CLOCK
                moment_day = ASTRALIS_CLOCK.now().day_number
            except Exception:
                moment_day = 0
            _chronicle_insert(
                session.database,
                event_key="adventure:first_echo:first_clear",
                day=moment_day,
                category="discovery",
                text=f"{session.character.name} returned from the Vault of the First Echo after defeating the Listener Below.",
                character_id=session.character.id,
                character_name=session.character.name,
            )
            await session.send("You let the court become quiet. What remains is not a new voice. The oldest record says Leviathan spoke everything into being in one breath of life, and the echo simply remains. The Vault offers no promise of a second word. The Vault of the First Echo complete: 320 XP and a First Echo Shard.\r\n")
        else:
            await session.send("The court is quiet now. What you hear is only the room returning what already happened.\r\n")
        return True
    await session.send("You listen. Ordinary room sounds separate themselves, but no special LISTEN interaction is active here. Important listening moments are telegraphed in the room text.\r\n")
    return True


async def _climb(session, target: str) -> bool:
    if session.character is None:
        return False
    if session.character.current_room == SCAR_LIFT and (not target or "gantry" in target.lower() or "lift" in target.lower()):
        _start_if_needed(session, SCAR_QUEST_KEY, "talk_brin", 5, SCAR_COMPLETE)
        if SCAR_SURVEYED not in _flags(session):
            await session.send("You can climb it, but Brin is standing outside with the current survey. TALK BRIN first if you want the route to make sense.\r\n")
            return True
        session.database.grant_flag(session.character.id, SCAR_GANTRY_CLIMBED)
        _advance(session, SCAR_QUEST_KEY, "climb_gantry", "release_brake")
        await session.send("You climb the inspection gantry and look down the quarry as a connected machine of paths rather than a pile of rooms. The broken freight bridge, deep face, and eastern winch line up. You climb back down knowing exactly where the route problem is.\r\n")
        return True
    await session.send("There is nothing here that needs a special CLIMB command. When climbing matters, the room description names the object.\r\n")
    return True


async def _pull(session, target: str) -> bool:
    if session.character is None:
        return False
    room = session.character.current_room
    normalized = " ".join(target.lower().split())
    if room == BELL_ROPE_ROOM and normalized in {"low", "low rope", "high", "high rope"}:
        if not {BELL_NAVE_HEARD, BELL_GALLERY_HEARD}.issubset(_flags(session)):
            await session.send("You can pull the ropes blindly, but the chapel has already given you a way to know the order. LISTEN in the nave and east gallery first.\r\n")
            return True
        expected = ("low", "high", "low")
        value = "high" if normalized.startswith("high") else "low"
        progress = list(getattr(session, "_bell_rope_progress", ()))
        if value != expected[len(progress)]:
            session._bell_rope_progress = ()
            await session.send("The wrong bell note collides with the room and the latch drops back into place. The sequence resets. Nothing is consumed.\r\n")
            return True
        progress.append(value)
        session._bell_rope_progress = tuple(progress)
        if len(progress) == len(expected):
            session.database.grant_flag(session.character.id, BELL_ROPES_SOLVED)
            _advance(session, BELL_QUEST_KEY, "solve_ropes", "defeat_bellkeeper")
            session._bell_rope_progress = ()
            await session.send("LOW. HIGH. LOW. The three notes return through the ruined chapel and the belfry latch lifts with a wooden knock. UP is now open.\r\n")
        else:
            await session.send(f"The {value.upper()} rope sounds cleanly. {len(progress)}/3 notes correct.\r\n")
        return True
    if room == SCAR_WINCH and (not normalized or "brake" in normalized or "lever" in normalized):
        if SCAR_GANTRY_CLIMBED not in _flags(session):
            await session.send("You could release the brake, but you have not yet climbed the lift gantry to understand what the cable is holding. CLIMB GANTRY back in the lift house first.\r\n")
            return True
        session.database.grant_flag(session.character.id, SCAR_BRAKE_RELEASED)
        _advance(session, SCAR_QUEST_KEY, "release_brake", "defeat_riftback")
        await session.send("You put both hands on the brake lever. The gears complain, the cable pays out, and somewhere across the cut the freight bridge settles onto stone. EAST now leads into the breaker pit.\r\n")
        return True
    if room == ECHO_LISTENER_COURT and "resonator" in normalized:
        if not getattr(session, "_listener_breath_pending", False):
            await session.send("The resonator chains are quiet. There is no false breath to interrupt right now.\r\n")
            return True
        if not getattr(session, "_listener_breath_heard", False):
            await session.send("Four chains are moving at once. LISTEN before yanking one blindly.\r\n")
            return True
        enemy = session.active_enemy
        if enemy is not None and enemy.definition.key == LISTENER_BELOW.key:
            original = getattr(session, "_listener_original_definition", LISTENER_BELOW)
            enemy.definition = original
            enemy.take_damage(18)
            await session.send(f"You pull on the rhythm rather than the loudest chain. The false lung collapses out of sequence and the imitation breath tears itself apart. The Listener takes 18 damage ({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n")
        session._listener_breath_pending = False
        session._listener_breath_heard = False
        return True
    await session.send("Nothing here answers that PULL command. Important pull interactions are named directly in room text.\r\n")
    return True


async def _touch(session, target: str) -> bool:
    if session.character is None:
        return False
    room = session.character.current_room
    normalized = " ".join(target.lower().split())
    if room in ECHO_PLATE_FLAGS and (not normalized or "plate" in normalized or "stone" in normalized):
        flag = ECHO_PLATE_FLAGS[room]
        if flag not in _flags(session):
            session.database.grant_flag(session.character.id, flag)
        flags = _flags(session)
        touched = len(set(ECHO_PLATE_FLAGS.values()) & flags)
        await session.send(f"The plate gives one soft answer through the floor, more felt than heard. Resonance plates answered: {touched}/3.\r\n")
        if touched == 3 and ECHO_GATE_OPEN not in flags:
            session.database.grant_flag(session.character.id, ECHO_GATE_OPEN)
            _advance(session, ECHO_QUEST_KEY, "touch_plates", "reach_listener")
            await session.send("All three answers overlap. Somewhere beyond the Mirror Choir, stone panels begin to separate.\r\n")
        return True
    if room == ECHO_MIRROR_CHOIR and ("three" in normalized or "mark" in normalized):
        flags = _flags(session)
        if not _all_outer_secrets(flags):
            await session.send("The three marks do not answer you. They resemble things you may or may not have noticed elsewhere around Waymeet.\r\n")
            return True
        session.database.grant_flag(session.character.id, DEEP_SECRET_OPEN)
        if session.database.item_quantity(session.character.id, QUIET_STONE.key) <= 0:
            session.database.add_item(session.character.id, QUIET_STONE.key, 1)
        await session.send("The three remembered shapes align under your fingertips. A narrow seam opens SOUTH into a margin room omitted from the main vault plan. You keep one plain Quiet Stone from the threshold; it has no stats and no progression value.\r\n")
        return True
    await session.send("Touching that has no special effect. Important TOUCH interactions are explicitly described.\r\n")
    return True


async def _examine_carving(session) -> bool:
    if session.character is None or session.character.current_room != TOLL_CARVED_SUBLEVEL:
        return False
    if TOLL_SECRET not in _flags(session):
        session.database.grant_flag(session.character.id, TOLL_SECRET)
    if TOLL_COMPLETE not in _flags(session):
        _complete(session, TOLL_QUEST_KEY, TOLL_COMPLETE, xp=85, item_key=TOLL_KEY_ITEM.key, text="")
        await session.send("The wall is far older than the tollhouse. Its repeated shape is not a map and not writing you can read, but one open-centered listening mark recurs three times. You copy it before leaving. Under the Old Toll complete: 85 XP and an Old Toll Brass Key.\r\n")
    else:
        await session.send("The older listening mark is unchanged. You already copied it.\r\n")
    return True


async def _engage_boss(session, definition: EnemyDefinition) -> bool:
    if session.active_enemy is not None:
        await session.send("You are already in combat.\r\n")
        return True
    if not _begin_combat(session, definition):
        await session.send("You cannot begin that fight in your current state.\r\n")
        return True
    if definition.key == TOLLMASTER.key:
        session._adventure_reaction = "brace"
        await session.send("Vesk kicks the counting table aside and raises his hooked cudgel over one shoulder. TELEGRAPH: BRACE will soften his opening punishment, but your normal class abilities remain the real fight.\r\n")
    elif definition.key == HOLLOW_BELLKEEPER.key:
        session._adventure_reaction = "cover ears"
        await session.send("The Bellkeeper drags the hammer toward the cracked bell. TELEGRAPH: COVER EARS before the next impact; then use your normal class kit to control the fight.\r\n")
    elif definition.key == RIFTBACK_MATRIARCH.key:
        session._adventure_reaction = "step aside"
        await session.send("The Matriarch lowers its crown-like horn and paws stone out of the pit. TELEGRAPH: STEP ASIDE to take the charge off-center.\r\n")
    elif definition.key == LISTENER_BELOW.key:
        session._listener_memory = {}
        session._listener_breath_pending = False
        session._listener_breath_heard = False
        session._listener_original_definition = definition
        await session.send("The Listener turns toward the first deliberate sound you make. It does not cast a spell. It waits to learn your habits. Repeating the same class ability will teach it how to echo that shape back at you.\r\n")
    return True


async def _react(session, command: str) -> bool:
    expected = getattr(session, "_adventure_reaction", None)
    if expected is None:
        return False
    normalized = " ".join(command.lower().split())
    if normalized != expected:
        return False
    session._adventure_reaction = None
    session.ward_until = asyncio.get_running_loop().time() + 6.0
    if normalized == "brace":
        await session.send("You plant your feet before Vesk's hooked swing arrives. The opening blow lands into your brace instead of folding you over the table.\r\n")
    elif normalized == "cover ears":
        await session.send("You cover and turn before the cracked bell is struck. The note still shakes your teeth, but the worst of the impact passes through the room instead of through you.\r\n")
    else:
        await session.send("You step off the Matriarch's line. Stone explodes where you were standing, and the charge loses its clean impact.\r\n")
    return True


def _listener_reflection_damage(count: int) -> int:
    return min(8, 2 + max(0, count - 1) * 2)


async def _after_listener_ability(session, ability_text: str, enemy_before) -> None:
    if enemy_before is None or enemy_before.definition.key != LISTENER_BELOW.key or not enemy_before.alive:
        return
    normalized = " ".join(ability_text.lower().replace("_", " ").split())
    if not normalized:
        return
    memory = getattr(session, "_listener_memory", None)
    if memory is None:
        memory = {}
        session._listener_memory = memory
    count = int(memory.get(normalized, 0)) + 1
    memory[normalized] = count
    if count == 1:
        await session.send(f"The Listener tilts toward the shape of {normalized.upper()}. It has heard that tool once and remembers it.\r\n")
    else:
        damage = _listener_reflection_damage(count)
        before = session.combatant.current_hp
        session.combatant.current_hp = max(1, before - damage)
        await session.send(f"The Listener returns a crude echo of {normalized.upper()} through the chamber. Repetition costs you {before - session.combatant.current_hp} HP. Change tools, interrupt it, or accept the echo.\r\n")
        await session.send_client_state()
    if enemy_before.current_hp <= enemy_before.definition.max_hp // 2 and not getattr(session, "_listener_breath_triggered", False):
        session._listener_breath_triggered = True
        session._listener_breath_pending = True
        session._listener_breath_heard = False
        session._listener_original_definition = LISTENER_BELOW
        enemy_before.definition = replace(
            enemy_before.definition,
            armor_class=enemy_before.definition.armor_class + 8,
            auto_attack_damage=enemy_before.definition.auto_attack_damage + 4,
        )
        await session.send("\r\nThe Listener folds toward the center of the court. The gray membranes in the next chamber inflate. For the first time, it tries to imitate a BREATH. Its armor tightens and its strikes become heavier. LISTEN if you want to understand what the room is doing.\r\n")


async def _award_boss(session, key: str) -> None:
    for member in _participants_here(session):
        if member.character is None:
            continue
        flags = _flags(member)
        if key == TOLLMASTER.key and TOLL_BOSS_DOWN not in flags:
            member.database.grant_flag(member.character.id, TOLL_BOSS_DOWN)
            _advance(member, TOLL_QUEST_KEY, "defeat_tollmaster", "find_sublevel")
            await member.send("Vesk goes down beside the counting table. The clean wall is finally safe to SEARCH.\r\n")
        elif key == HOLLOW_BELLKEEPER.key and BELL_BOSS_DOWN not in flags:
            member.database.grant_flag(member.character.id, BELL_BOSS_DOWN)
            if BELL_COMPLETE not in flags:
                _complete(member, BELL_QUEST_KEY, BELL_COMPLETE, xp=115, item_key=BELL_CLAPPER_ITEM.key, text="")
                await member.send("The Hollow Bellkeeper drops the hammer and the crooked bell settles into silence. The Crooked Bell complete: 115 XP and a Crooked Bell Clapper. The rafters remain worth SEARCHing if you are curious.\r\n")
        elif key == RIFTBACK_MATRIARCH.key and SCAR_BOSS_DOWN not in flags:
            member.database.grant_flag(member.character.id, SCAR_BOSS_DOWN)
            if SCAR_COMPLETE not in flags:
                _complete(member, SCAR_QUEST_KEY, SCAR_COMPLETE, xp=175, item_key=SCAR_NAIL_ITEM.key, text="")
                await member.send("The Riftback Matriarch crashes into the spoil slope and does not rise. King's Scar Survey complete: 175 XP and a King's Scar Survey Nail. Brin can put a real crew back on the route.\r\n")
        elif key == LISTENER_BELOW.key and LISTENER_DOWN not in flags:
            member.database.grant_flag(member.character.id, LISTENER_DOWN)
            _advance(member, ECHO_QUEST_KEY, "defeat_listener", "hear_first_echo")
            await member.send("The Listener goes still. It does not scream. It turns toward the room one last time, as if waiting for the world to repeat itself, and says one dry word: \"Again.\" LISTEN now that the court is quiet.\r\n")


def _start_quest_for_room(session) -> None:
    if session.character is None:
        return
    room = session.character.current_room
    if room in TOLL_ROOM_KEYS:
        _start_if_needed(session, TOLL_QUEST_KEY, "enter_cellar", 2, TOLL_COMPLETE)
        _advance(session, TOLL_QUEST_KEY, "enter_cellar", "read_ledger")
    elif room in BELL_ROOM_KEYS:
        _start_if_needed(session, BELL_QUEST_KEY, "hear_nave", 3, BELL_COMPLETE)
    elif room in SCAR_ROOM_KEYS or room == KINGS_SCAR_APPROACH:
        _start_if_needed(session, SCAR_QUEST_KEY, "talk_brin", 5, SCAR_COMPLETE)
    elif room in ECHO_ROOM_KEYS:
        if {TOLL_COMPLETE, BELL_COMPLETE, SCAR_COMPLETE}.issubset(_flags(session)):
            _start_if_needed(session, ECHO_QUEST_KEY, "touch_plates", 8, ECHO_COMPLETE)


async def _maybe_open_deep_secret(session) -> None:
    if session.character is None or session.character.current_room != ECHO_MIRROR_CHOIR:
        return
    if _all_outer_secrets(_flags(session)) and DEEP_SECRET_OPEN not in _flags(session):
        await session.send("\r\nThree tiny marks at the base of the choir panels look familiar in a way the main quest does not explain. If you remember where you saw them, TOUCH THREE MARKS.\r\n")


# ---------------------------------------------------------------------------
# Runtime installation
# ---------------------------------------------------------------------------
def install_waymeet_adventure_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_waymeet_adventure_runtime_installed", False):
        return
    install_adventure_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_finish = player_session_class._finish_enemy_defeat
    previous_use_ability = player_session_class.use_ability

    async def enter_character(self) -> None:
        await previous_enter(self)
        _start_quest_for_room(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        if self.character is None:
            return
        if self.character.current_room != before:
            _start_quest_for_room(self)
            await _maybe_open_deep_secret(self)

    async def use_ability(self, ability_text: str) -> None:
        enemy_before = getattr(self, "active_enemy", None)
        await previous_use_ability(self, ability_text)
        if enemy_before is not None and enemy_before is getattr(self, "active_enemy", enemy_before):
            await _after_listener_ability(self, ability_text, enemy_before)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if active and key in {TOLLMASTER.key, HOLLOW_BELLKEEPER.key, RIFTBACK_MATRIARCH.key, LISTENER_BELOW.key}:
            await _award_boss(self, key)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        handled = False

        if normalized in {"explore", "adventure", "outer roads", "waymeet adventure"}:
            await _show_explore(self)
            return
        if normalized in {"secrets", "mysteries"}:
            flags = _flags(self)
            count = len({TOLL_SECRET, BELL_SECRET, SCAR_SECRET} & flags)
            await self.send(f"You have personally noticed {count}/3 optional outer listening marks. Their missing locations are intentionally not listed. Deep response: {'OPEN' if DEEP_SECRET_OPEN in flags else 'unresolved'}.\r\n")
            return
        if normalized in {"talk brin", "talk surveyor", "speak brin", "talk brin stonewake"}:
            handled = await _talk_brin(self)
        elif normalized == "search" or normalized.startswith("search "):
            handled = await _search(self, stripped[6:].strip() if len(stripped) > 6 else "")
        elif normalized == "listen" or normalized.startswith("listen "):
            handled = await _listen(self, stripped[6:].strip() if len(stripped) > 6 else "")
        elif normalized == "climb" or normalized.startswith("climb "):
            handled = await _climb(self, stripped[5:].strip() if len(stripped) > 5 else "")
        elif normalized == "pull" or normalized.startswith("pull "):
            handled = await _pull(self, stripped[4:].strip() if len(stripped) > 4 else "")
        elif normalized == "touch" or normalized.startswith("touch "):
            handled = await _touch(self, stripped[5:].strip() if len(stripped) > 5 else "")
        elif normalized in {"examine carved wall", "examine carving", "look carved wall", "read carved wall"}:
            handled = await _examine_carving(self)
        elif normalized in {"attack tollmaster", "attack vesk", "fight tollmaster"} and self.character.current_room == TOLL_COUNTING:
            if TOLL_BOSS_DOWN in _flags(self):
                await self.send("Tollmaster Vesk is already down on this clear. SEARCH WALL if you have not investigated the counting room.\r\n")
                return
            handled = await _engage_boss(self, TOLLMASTER)
        elif normalized in {"attack bellkeeper", "attack keeper", "fight bellkeeper"} and self.character.current_room == BELL_BELFRY:
            if BELL_BOSS_DOWN in _flags(self):
                await self.send("The Hollow Bellkeeper is already down. SEARCH RAFTERS if you are curious.\r\n")
                return
            handled = await _engage_boss(self, HOLLOW_BELLKEEPER)
        elif normalized in {"attack riftback", "attack matriarch", "fight matriarch"} and self.character.current_room == SCAR_BREAKER_PIT:
            if SCAR_BOSS_DOWN in _flags(self):
                await self.send("The Riftback Matriarch is already down on your first clear.\r\n")
                return
            handled = await _engage_boss(self, RIFTBACK_MATRIARCH)
        elif normalized in {"attack listener", "attack listener below", "fight listener"} and self.character.current_room == ECHO_LISTENER_COURT:
            if LISTENER_DOWN in _flags(self):
                await self.send("The Listener Below is already silent. LISTEN to the court.\r\n")
                return
            _advance(self, ECHO_QUEST_KEY, "reach_listener", "defeat_listener")
            handled = await _engage_boss(self, LISTENER_BELOW)
        elif normalized in {"brace", "cover ears", "step aside"}:
            handled = await _react(self, normalized)

        if handled:
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")
        async def replay(_text: str):
            return command
        self.prompt = replay
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.use_ability = use_ability
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.playing_prompt = playing_prompt
    player_session_class._waymeet_adventure_runtime_installed = True
