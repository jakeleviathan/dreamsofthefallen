from __future__ import annotations

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.broken_reach_midgame import CAPSTONE_COMPLETE_FLAG as BROKEN_REACH_COMPLETE_FLAG, FAR_WATCH_KEY
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


SALT_REGION_KEY = "salt_kingdoms_whitewake"
KEELSPIRE_REGION_KEY = "salt_kingdoms_keelspire"
GLASS_KEEL_REGION_KEY = "salt_kingdoms_glass_keel"
UNDERTIDE_REGION_KEY = "salt_kingdoms_undertide"

# ---------------------------------------------------------------------------
# Surface and city map: ten basin rooms plus eight rooms in Keelspire.
# ---------------------------------------------------------------------------
SALTWIND_GATE_KEY = "salt_kingdoms_saltwind_gate"
WHITEWAKE_CAUSEWAY_KEY = "salt_kingdoms_whitewake_causeway"
KEELGRAVE_FLATS_KEY = "salt_kingdoms_keelgrave_flats"
SUNKEN_MILE_KEY = "salt_kingdoms_sunken_mile"
DUSTWELL_CAMP_KEY = "salt_kingdoms_dustwell_camp"
PILGRIM_SALT_KEY = "salt_kingdoms_pilgrim_salt"
OLD_BREAKWATER_KEY = "salt_kingdoms_old_breakwater"
TIDEMARK_SINK_KEY = "salt_kingdoms_tidemark_sink"
SPRINGCUT_GORGE_KEY = "salt_kingdoms_springcut_gorge"
CISTERN_ROAD_KEY = "salt_kingdoms_cistern_road"

KEELSPIRE_GATE_KEY = "keelspire_dry_harbor_gate"
KEELSPIRE_QUAYS_KEY = "keelspire_dry_quays"
KEELSPIRE_ROPEMARKET_KEY = "keelspire_ropemarket"
KEELSPIRE_CROWN_SQUARE_KEY = "keelspire_crown_square"
KEELSPIRE_THREE_WELLS_KEY = "keelspire_three_wells_court"
KEELSPIRE_ARCHIVE_KEY = "keelspire_basin_archive"
KEELSPIRE_SURVEY_HALL_KEY = "keelspire_salt_survey_hall"
KEELSPIRE_HARBOR_VAULT_KEY = "keelspire_harbor_vault"

# ---------------------------------------------------------------------------
# Dungeon one: The Glass Keel. A tilted, salt-buried ship rather than a cave.
# ---------------------------------------------------------------------------
GLASS_KEEL_APPROACH_KEY = "glass_keel_wreck_approach"
GLASS_KEEL_SPLIT_DECK_KEY = "glass_keel_split_deck"
GLASS_KEEL_CARGO_KEY = "glass_keel_cargo_gallery"
GLASS_KEEL_CHAPEL_KEY = "glass_keel_salt_chapel"
GLASS_KEEL_BALLAST_KEY = "glass_keel_ballast_spine"
GLASS_KEEL_CAPTAIN_KEY = "glass_keel_captains_round"
GLASS_KEEL_TIDEHOLD_KEY = "glass_keel_tideglass_hold"

# ---------------------------------------------------------------------------
# Dungeon two: the Undertide Engine. Mechanical hydrology beneath the dead sea.
# ---------------------------------------------------------------------------
UNDERTIDE_INTAKE_KEY = "undertide_intake_stair"
UNDERTIDE_PRESSURE_WALK_KEY = "undertide_pressure_walk"
UNDERTIDE_SIPHON_GALLERY_KEY = "undertide_siphon_gallery"
UNDERTIDE_COUNTERWEIGHT_KEY = "undertide_counterweight_well"
UNDERTIDE_REGENT_KEY = "undertide_regent_court"
UNDERTIDE_DISTRIBUTOR_KEY = "undertide_broken_distributor"
UNDERTIDE_HEART_KEY = "undertide_heart"
UNDERTIDE_RELEASE_KEY = "undertide_deep_release_gate"

SURFACE_ROOM_KEYS = (
    SALTWIND_GATE_KEY,
    WHITEWAKE_CAUSEWAY_KEY,
    KEELGRAVE_FLATS_KEY,
    SUNKEN_MILE_KEY,
    DUSTWELL_CAMP_KEY,
    PILGRIM_SALT_KEY,
    OLD_BREAKWATER_KEY,
    TIDEMARK_SINK_KEY,
    SPRINGCUT_GORGE_KEY,
    CISTERN_ROAD_KEY,
)
CITY_ROOM_KEYS = (
    KEELSPIRE_GATE_KEY,
    KEELSPIRE_QUAYS_KEY,
    KEELSPIRE_ROPEMARKET_KEY,
    KEELSPIRE_CROWN_SQUARE_KEY,
    KEELSPIRE_THREE_WELLS_KEY,
    KEELSPIRE_ARCHIVE_KEY,
    KEELSPIRE_SURVEY_HALL_KEY,
    KEELSPIRE_HARBOR_VAULT_KEY,
)
GLASS_KEEL_ROOM_KEYS = (
    GLASS_KEEL_APPROACH_KEY,
    GLASS_KEEL_SPLIT_DECK_KEY,
    GLASS_KEEL_CARGO_KEY,
    GLASS_KEEL_CHAPEL_KEY,
    GLASS_KEEL_BALLAST_KEY,
    GLASS_KEEL_CAPTAIN_KEY,
    GLASS_KEEL_TIDEHOLD_KEY,
)
UNDERTIDE_ROOM_KEYS = (
    UNDERTIDE_INTAKE_KEY,
    UNDERTIDE_PRESSURE_WALK_KEY,
    UNDERTIDE_SIPHON_GALLERY_KEY,
    UNDERTIDE_COUNTERWEIGHT_KEY,
    UNDERTIDE_REGENT_KEY,
    UNDERTIDE_DISTRIBUTOR_KEY,
    UNDERTIDE_HEART_KEY,
    UNDERTIDE_RELEASE_KEY,
)
SALT_KINGDOMS_ROOM_KEYS = (*SURFACE_ROOM_KEYS, *CITY_ROOM_KEYS, *GLASS_KEEL_ROOM_KEYS, *UNDERTIDE_ROOM_KEYS)

# ---------------------------------------------------------------------------
# Story and state.
# ---------------------------------------------------------------------------
ARRIVAL_QUEST_KEY = "salt_kingdoms_road_where_sea_was"
GLASS_KEEL_QUEST_KEY = "salt_kingdoms_ship_that_measures_tide"
FACTION_QUEST_KEY = "salt_kingdoms_three_thirsts"
UNDERTIDE_QUEST_KEY = "salt_kingdoms_undertide_engine"
CAPSTONE_QUEST_KEY = "salt_kingdoms_where_the_water_goes"

ARRIVAL_COMPLETE_FLAG = "salt_kingdoms_arrival_complete"
GLASS_KEEL_COMPLETE_FLAG = "salt_kingdoms_glass_keel_complete"
FACTION_COMPLETE_FLAG = "salt_kingdoms_three_thirsts_complete"
CITY_FIRST_FLAG = "salt_kingdoms_priority_city"
ROAD_FIRST_FLAG = "salt_kingdoms_priority_road"
WELLS_FIRST_FLAG = "salt_kingdoms_priority_wells"
REGENT_DEFEATED_FLAG = "salt_kingdoms_sluice_regent_defeated"
REGENT_TRUTH_FLAG = "salt_kingdoms_regent_truth_known"
UNDERTIDE_COMPLETE_FLAG = "salt_kingdoms_undertide_complete"
CAPSTONE_COMPLETE_FLAG = "salt_kingdoms_level_30_complete"
HARBOR_ENDING_FLAG = "salt_kingdoms_water_to_harbor"
WELLS_ENDING_FLAG = "salt_kingdoms_water_to_wells"
CURRENT_ENDING_FLAG = "salt_kingdoms_water_to_current"

ODDITY_BELL_FLAG = "salt_kingdoms_oddity_buried_bell"
ODDITY_SHADOW_FLAG = "salt_kingdoms_oddity_wet_shadow"
ODDITY_MAP_FLAG = "salt_kingdoms_oddity_shoreless_map"
ODDITY_CUP_FLAG = "salt_kingdoms_oddity_filling_cup"
ODDITY_FLAGS = (ODDITY_BELL_FLAG, ODDITY_SHADOW_FLAG, ODDITY_MAP_FLAG, ODDITY_CUP_FLAG)

WHITEWAKE_PASS_KEY = "salt_kingdoms_whitewake_pass"
TIDEGLASS_SLIVER_KEY = "salt_kingdoms_tideglass_sliver"
THREE_THIRSTS_TOKEN_KEY = "salt_kingdoms_three_thirsts_token"
REGENT_GAUGE_KEY = "salt_kingdoms_regent_gauge"
WATER_DECISION_SEAL_KEY = "salt_kingdoms_water_decision_seal"
SALT_BELL_CLAPPER_KEY = "salt_kingdoms_buried_bell_clapper"

ARRIVAL_QUEST = QuestDefinition(
    key=ARRIVAL_QUEST_KEY,
    name="The Road Where the Sea Was",
    style="structured",
    minimum_level=21,
    description=(
        "West of the Broken Reach, caravans cross the bed of a dead inland sea between stranded shipwrecks and old harbor walls. "
        "The immediate problem is practical: road markers are sinking, wells are failing, and whole wagons have begun dropping through salt that looked solid."
    ),
    objective_steps=(
        ("talk_enna", "At Saltwind Gate, TALK ENNA."),
        ("inspect_sink", "Cross Whitewake and EXAMINE SINK at Tidemark Sink."),
        ("reach_city", "Reach Keelspire, the city built around the dead harbor."),
        ("read_tidemarks", "At the Basin Archive, READ TIDEMARKS."),
        ("return_enna", "Report what you learned to Enna at Saltwind Gate."),
        ("complete", "You proved the road failures are being caused by moving water below the dead seabed, not by ordinary erosion alone."),
    ),
)

GLASS_KEEL_QUEST = QuestDefinition(
    key=GLASS_KEEL_QUEST_KEY,
    name="The Ship That Still Measures Tide",
    style="structured",
    minimum_level=23,
    description=(
        "A salt-buried ship called the Glass Keel has not floated for centuries, yet one surviving tide instrument in its lowest hold is still moving. "
        "Its log may show whether the sea vanished once or was taken away in stages."
    ),
    objective_steps=(
        ("talk_orro", "At Keelspire's Dry Quays, TALK ORRO."),
        ("read_log", "Enter the Glass Keel and READ LOG in the Captain's Round."),
        ("defeat_matriarch", "Reach the Ballast Spine and defeat the Ballast Matriarch."),
        ("inspect_tideglass", "Descend to the Tideglass Hold and EXAMINE TIDEGLASS."),
        ("complete", "The instrument proves a strong underground tide is still moving beneath Whitewake."),
    ),
)

FACTION_QUEST = QuestDefinition(
    key=FACTION_QUEST_KEY,
    name="Three Thirsts, One Basin",
    style="structured",
    minimum_level=26,
    description=(
        "The underground flow is real, but knowing that does not decide who should receive it. Keelspire wants a secure city supply, "
        "the caravan league wants the road cistern chain restored, and basin settlements want the old wells and aquifers fed first."
    ),
    objective_steps=(
        ("talk_crown", "At Crown Square, TALK CALDRIN."),
        ("talk_caravan", "At Ropemarket, TALK NIMA."),
        ("talk_wells", "At Three Wells Court, TALK SELA."),
        ("read_rations", "At Three Wells Court, READ RATIONS."),
        ("choose_priority", "Return to Crown Square and choose PRIORITY CITY, PRIORITY ROAD, or PRIORITY WELLS."),
        ("complete", "You recorded which need should lead while the deeper mechanism is investigated; the choice is policy, not yet the final hydraulic decision."),
    ),
)

UNDERTIDE_QUEST = QuestDefinition(
    key=UNDERTIDE_QUEST_KEY,
    name="The Undertide Engine",
    style="structured",
    minimum_level=27,
    description=(
        "Below Keelspire's oldest harbor vault, an engineered intake descends toward machinery that still moves water beneath the dead sea. "
        "The obvious guardian is not necessarily the cause of the failure."
    ),
    objective_steps=(
        ("talk_tavik", "At the Harbor Vault, TALK TAVIK."),
        ("read_gauges", "Descend and READ GAUGES on the Pressure Walk."),
        ("set_counterweight", "At the Counterweight Well, SET COUNTERWEIGHT."),
        ("defeat_regent", "Defeat the Sluice Regent in Regent Court."),
        ("inspect_distributor", "After the Regent falls, EXAMINE DISTRIBUTOR."),
        ("listen_water", "Reach the Undertide Heart and LISTEN WATER."),
        ("complete", "You learned the Regent was compensating for a failed distributor, and that the remaining system can send the recovered flow in more than one direction."),
    ),
)

CAPSTONE_QUEST = QuestDefinition(
    key=CAPSTONE_QUEST_KEY,
    name="Where the Water Goes",
    style="structured",
    minimum_level=30,
    description=(
        "The Undertide can be stabilized, but there is not enough pressure to restore every historical channel at once. "
        "At the Deep Release Gate, decide what the next generation of the Salt Kingdoms will physically be built around."
    ),
    objective_steps=(
        ("reach_release", "Reach the Deep Release Gate below the Undertide Heart."),
        ("choose_water", "Choose SEND HARBOR, FEED WELLS, or FREE CURRENT."),
        ("complete", "Your hydraulic decision permanently changes routes and visible water across the Salt Kingdoms for this character."),
    ),
)

SALT_KINGDOMS_QUESTS = (ARRIVAL_QUEST, GLASS_KEEL_QUEST, FACTION_QUEST, UNDERTIDE_QUEST, CAPSTONE_QUEST)

SALT_KINGDOMS_ITEMS = (
    ItemDefinition(WHITEWAKE_PASS_KEY, "Whitewake Basin Pass", "A road pass stamped with a warning that SOLID SALT IS NOT THE SAME THING AS SOLID GROUND.", "credential", tier=5),
    ItemDefinition(TIDEGLASS_SLIVER_KEY, "Living Tideglass Sliver", "A blue-white sliver from the Glass Keel's surviving tide instrument. It trembles faintly when held over deep stone.", "trophy", tier=5),
    ItemDefinition(THREE_THIRSTS_TOKEN_KEY, "Three Thirsts Token", "A triangular public token with CITY, ROAD, and WELL stamped on separate edges; one edge carries your witnessed priority mark.", "credential", tier=6),
    ItemDefinition(REGENT_GAUGE_KEY, "Regent's Counter-Gauge", "A bronze pressure gauge removed from the Sluice Regent. Its needle points toward the pressure it was trying to reduce, not the water it was trying to steal.", "trophy", tier=6),
    ItemDefinition(WATER_DECISION_SEAL_KEY, "Salt Kingdoms Water Seal", "A heavy ceramic seal recording the release pattern chosen at the Undertide Engine. The back is intentionally blank for whoever has to revise it later.", "credential", tier=7),
    ItemDefinition(SALT_BELL_CLAPPER_KEY, "Dry Bell Clapper", "A ship-bell clapper polished by motion despite having been buried under salt for generations.", "curio", tier=5),
)


def _enemy(key: str, name: str, aliases: tuple[str, ...], description: str, hp: int, ac: int, damage: int, interval: float, xp: int) -> EnemyDefinition:
    return EnemyDefinition(
        key=key,
        name=name,
        aliases=aliases,
        description=description,
        max_hp=hp,
        armor_class=ac,
        auto_attack_damage=damage,
        auto_attack_interval=interval,
        xp_reward=xp,
        retaliates=True,
        tutorial=False,
    )


SALT_HOUND_KEY = "salt_kingdoms_white_hound"
GLASS_SCORPION_KEY = "salt_kingdoms_glass_scorpion"
KEEL_CRAWLER_KEY = "glass_keel_deck_crawler"
BRINE_WIGHT_KEY = "glass_keel_brine_wight"
BALLAST_MATRIARCH_KEY = "glass_keel_ballast_matriarch"
PRESSURE_MITE_KEY = "undertide_pressure_mite"
BRINE_WORM_KEY = "undertide_brine_worm"
VALVE_SENTINEL_KEY = "undertide_valve_sentinel"
SLUICE_REGENT_KEY = "undertide_sluice_regent"

SALT_HOUND = _enemy(SALT_HOUND_KEY, "White Salt Hound", ("hound", "salt hound", "white hound"), "a rangy basin predator dusted so white that only its eyes and tongue break the horizon line", 420, 16, 26, 2.6, 360)
GLASS_SCORPION = _enemy(GLASS_SCORPION_KEY, "Glass Scorpion", ("scorpion", "glass scorpion"), "a translucent salt-flat scorpion large enough to leave cart-width drag marks", 470, 18, 29, 2.9, 410)
KEEL_CRAWLER = _enemy(KEEL_CRAWLER_KEY, "Keel Crawler", ("crawler", "keel crawler"), "a many-legged scavenger flattened to move between the ship's tilted deck beams", 510, 18, 30, 2.7, 450)
BRINE_WIGHT = _enemy(BRINE_WIGHT_KEY, "Brine Wight", ("wight", "brine wight", "sailor"), "a salt-stiffened dead sailor animated less by memory than by the mineral crust binding its joints", 560, 19, 32, 3.0, 500)
BALLAST_MATRIARCH = _enemy(BALLAST_MATRIARCH_KEY, "Ballast Matriarch", ("matriarch", "ballast matriarch", "crab"), "an enormous pale crustacean that has built a nest around the ship's lowest surviving ballast channels", 1650, 22, 42, 2.8, 2700)
PRESSURE_MITE = _enemy(PRESSURE_MITE_KEY, "Pressure Mite", ("mite", "pressure mite"), "a bronze-shelled maintenance vermin feeding on mineral scale around vibrating pipe seams", 590, 20, 34, 2.5, 520)
BRINE_WORM = _enemy(BRINE_WORM_KEY, "Brine Worm", ("worm", "brine worm"), "a blind white worm moving through wet mineral channels as if the stone were mud", 660, 20, 38, 2.9, 610)
VALVE_SENTINEL = _enemy(VALVE_SENTINEL_KEY, "Valve Sentinel", ("sentinel", "valve sentinel"), "a four-armed stone service construct carrying different wrench heads instead of hands", 760, 23, 39, 3.0, 700)
SLUICE_REGENT = _enemy(SLUICE_REGENT_KEY, "Sluice Regent", ("regent", "sluice regent"), "a towering hydraulic custodian pivoting around a crown of pressure vanes and counterweighted arms", 2450, 25, 49, 2.8, 4300)

SALT_KINGDOMS_ENEMIES = (
    SALT_HOUND,
    GLASS_SCORPION,
    KEEL_CRAWLER,
    BRINE_WIGHT,
    BALLAST_MATRIARCH,
    PRESSURE_MITE,
    BRINE_WORM,
    VALVE_SENTINEL,
    SLUICE_REGENT,
)

ENNA_KEY = "salt_kingdoms_cartographer_enna_vale"
ORRO_KEY = "keelspire_salvager_orro_pike"
CALDRIN_KEY = "keelspire_steward_caldrin_vey"
NIMA_KEY = "keelspire_caravan_speaker_nima_rell"
SELA_KEY = "keelspire_wellkeeper_sela_marr"
TAVIK_KEY = "keelspire_engine_reader_tavik_bronzehand"

SALT_KINGDOMS_NPCS = (
    NpcDefinition(
        ENNA_KEY,
        "Cartographer Enna Vale",
        "a sun-browned Human cartographer carrying a map board full of crossed-out roads and fresh sinkhole circles",
        SALTWIND_GATE_KEY,
        "Whitewake road cartographer",
        dialogue=(
            "'The dangerous part of a dead sea is believing dead means still.'",
            "'If the salt sounds hollow, believe it before the wagon proves it for you.'",
        ),
    ),
    NpcDefinition(
        ORRO_KEY,
        "Salvager Orro Pike",
        "a Goblin wreck salvager wearing a ship's brass nameplate as a belt buckle",
        KEELSPIRE_QUAYS_KEY,
        "Glass Keel expedition lead",
        dialogue=(
            "'A shipwreck in a desert is only funny until you remember somebody once sailed over your head.'",
            "'The Glass Keel's tideglass still moves. I want to know what water it thinks it is measuring.'",
        ),
    ),
    NpcDefinition(
        CALDRIN_KEY,
        "Harbor Steward Caldrin Vey",
        "a severe Moon Elf administrator whose desk is made from a dry-dock gate that has not touched water in three centuries",
        KEELSPIRE_CROWN_SQUARE_KEY,
        "Keelspire civic steward",
        dialogue=(
            "'A city is not selfish for needing water. It becomes selfish when it pretends nobody else does.'",
            "'If Keelspire fails, every road through Whitewake loses its largest repair market, archive, and clinic.'",
        ),
    ),
    NpcDefinition(
        NIMA_KEY,
        "Caravan Speaker Nima Rell",
        "a Forest Elf caravan speaker with six water ledgers tied to the same travel staff",
        KEELSPIRE_ROPEMARKET_KEY,
        "Whitewake caravan league speaker",
        dialogue=(
            "'A road without wells is a line on a map, not infrastructure.'",
            "'Cities can ration behind walls. A caravan halfway across the basin cannot ration distance.'",
        ),
    ),
    NpcDefinition(
        SELA_KEY,
        "Wellkeeper Sela Marr",
        "a broad Troll wellkeeper with white salt crust on both sleeves and a measuring cup hanging from her neck",
        KEELSPIRE_THREE_WELLS_KEY,
        "basin settlement representative",
        dialogue=(
            "'The little wells fail first because nobody important is standing beside them when they go dry.'",
            "'Feed the ground and some water will choose its own villages. That is less tidy than a pipe and harder to own.'",
        ),
    ),
    NpcDefinition(
        TAVIK_KEY,
        "Engine Reader Tavik Bronzehand",
        "a Dwarf hydraulic reader carrying a listening hammer and a notebook written vertically to match pipe shafts",
        KEELSPIRE_HARBOR_VAULT_KEY,
        "Undertide Engine expedition engineer",
        dialogue=(
            "'The pressure numbers are impossible only if the water is where our maps put it.'",
            "'Do not call the Regent broken until you know what load it is carrying for the broken part.'",
        ),
    ),
)


def _room(key: str, name: str, region: str, description: str, exits: dict[str, str], *, npcs: tuple[str, ...] = (), enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=region,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "salt_kingdoms", *tags),
    )


SALT_KINGDOMS_ROOMS: tuple[RoomDefinition, ...] = (
    _room(SALTWIND_GATE_KEY, "Saltwind Gate", SALT_REGION_KEY, "Far Watch disappears behind a chalk ridge and the world opens into white distance. A dead inland sea fills the horizon, its floor crossed by wagon tracks, stranded hulls, and stone harbor markers impossibly far from water. Enna's map board is nailed to a ship mast planted upright beside the road.", {"east": FAR_WATCH_KEY, "west": WHITEWAKE_CAUSEWAY_KEY}, npcs=(ENNA_KEY,), tags=("level_21_22", "entry", "safe")),
    _room(WHITEWAKE_CAUSEWAY_KEY, "Whitewake Causeway", SALT_REGION_KEY, "A raised road of black stone cuts through dazzling salt. Old depth numbers are carved into its sides at head height, reminders that loaded ships once floated above the wagons using the road now.", {"east": SALTWIND_GATE_KEY, "west": KEELGRAVE_FLATS_KEY}, enemies=(SALT_HOUND_KEY,), tags=("level_21_22", "road")),
    _room(KEELGRAVE_FLATS_KEY, "Keelgrave Flats", SALT_REGION_KEY, "Dozens of ship ribs break through the basin floor like dark fences. Caravans camp in their shadows because wood that survived three centuries of salt makes excellent windbreaks. North, the largest wreck rises on its side like a glass-white cliff.", {"east": WHITEWAKE_CAUSEWAY_KEY, "west": SUNKEN_MILE_KEY, "south": DUSTWELL_CAMP_KEY, "north": GLASS_KEEL_APPROACH_KEY}, enemies=(GLASS_SCORPION_KEY,), tags=("level_22_24", "wreck_field")),
    _room(SUNKEN_MILE_KEY, "The Sunken Mile", SALT_REGION_KEY, "The old road drops several yards without changing slope, as though a rectangular section of seabed settled intact. Fresh survey poles lean toward the same low point. Wheel tracks stop abruptly at three crusted holes where wagons punched through.", {"east": KEELGRAVE_FLATS_KEY, "west": TIDEMARK_SINK_KEY}, enemies=(SALT_HOUND_KEY, GLASS_SCORPION_KEY), tags=("level_22_24", "sinkholes")),
    _room(DUSTWELL_CAMP_KEY, "Dustwell Camp", SALT_REGION_KEY, "A caravan camp circles a stone well whose bucket now returns with damp rope and no water. Drivers ration by cup, not skin, and have started trading route news more urgently than merchandise.", {"north": KEELGRAVE_FLATS_KEY, "south": PILGRIM_SALT_KEY}, tags=("level_22_26", "caravan", "safe")),
    _room(PILGRIM_SALT_KEY, "Pilgrim Salt", SALT_REGION_KEY, "Thousands of small offerings have been pressed into the salt along an old walking route: buttons, carved bones, bottle glass, tiny wheels, and ship nails. The path survives because travelers keep finding it useful even when they disagree about why it began.", {"north": DUSTWELL_CAMP_KEY, "west": OLD_BREAKWATER_KEY}, enemies=(SALT_HOUND_KEY,), tags=("level_24_27", "road", "culture")),
    _room(OLD_BREAKWATER_KEY, "Old Breakwater", SALT_REGION_KEY, "A harbor breakwater runs across dry land toward Keelspire. Warehouses were built against its landward face after the sea vanished, turning marine infrastructure into a city wall one generation at a time.", {"east": PILGRIM_SALT_KEY, "south": KEELSPIRE_GATE_KEY}, tags=("level_24_30", "city_approach")),
    _room(TIDEMARK_SINK_KEY, "Tidemark Sink", SALT_REGION_KEY, "A fresh collapse exposes layers of salt, mud, and old harbor silt. The lowest crack is wet. Blue mineral lines on the walls form a tide mark several yards below the supposedly dry basin floor.", {"east": SUNKEN_MILE_KEY, "south": KEELSPIRE_GATE_KEY}, enemies=(GLASS_SCORPION_KEY,), tags=("level_21_26", "evidence")),
    _room(SPRINGCUT_GORGE_KEY, "Springcut Gorge", SALT_REGION_KEY, "A new stream has cut a narrow brown-green gorge through salt that was white yesterday. Water runs openly here only because the Undertide was released back into the natural southward fault channels.", {"up": PILGRIM_SALT_KEY, "north": TIDEMARK_SINK_KEY}, tags=("level_30", "post_capstone", "current_route")),
    _room(CISTERN_ROAD_KEY, "The Refilled Cistern Road", SALT_REGION_KEY, "A chain of roadside cistern mouths gleams dark with new water. Painted depth marks replace emergency ration notices, and caravans stop here to refill without entering Keelspire first.", {"east": KEELSPIRE_THREE_WELLS_KEY, "west": DUSTWELL_CAMP_KEY}, tags=("level_30", "post_capstone", "wells_route")),

    _room(KEELSPIRE_GATE_KEY, "Keelspire Dry Harbor Gate", KEELSPIRE_REGION_KEY, "Keelspire rises inside the bowl of an ancient harbor. Stone quays now form streets, lighthouse towers are watch posts, and several buildings incorporate whole ship hulls into their upper floors. The city's gate occupies what was once a harbor chainhouse.", {"north": OLD_BREAKWATER_KEY, "south": KEELSPIRE_CROWN_SQUARE_KEY, "west": KEELSPIRE_QUAYS_KEY}, tags=("level_22_30", "city", "safe")),
    _room(KEELSPIRE_QUAYS_KEY, "The Dry Quays", KEELSPIRE_REGION_KEY, "Broad quay stairs descend to dust instead of water. Salvage cranes swing over market carts, and shipwright sheds now repair wagons beneath beams originally sized for masts. Orro Pike has claimed one bollard as an expedition desk.", {"east": KEELSPIRE_GATE_KEY, "south": KEELSPIRE_ROPEMARKET_KEY}, npcs=(ORRO_KEY,), tags=("level_22_30", "city", "salvage", "safe")),
    _room(KEELSPIRE_ROPEMARKET_KEY, "Ropemarket", KEELSPIRE_REGION_KEY, "An old sailmakers' district sells rope, canvas, water skins, axle line, shade cloth, and every kind of knot somebody can insist has a proper name. Caravan boards list water intervals beside prices.", {"north": KEELSPIRE_QUAYS_KEY, "east": KEELSPIRE_CROWN_SQUARE_KEY}, npcs=(NIMA_KEY,), tags=("level_22_30", "city", "market", "safe")),
    _room(KEELSPIRE_CROWN_SQUARE_KEY, "Crown Square", KEELSPIRE_REGION_KEY, "Three old royal customs houses face one square and none contains a king anymore. Their balconies now hold city offices, public hearings, and flags from the small Salt Kingdoms that still argue over who inherited the dead sea. Caldrin's desk sits under the only awning large enough for all three delegations.", {"north": KEELSPIRE_GATE_KEY, "west": KEELSPIRE_ROPEMARKET_KEY, "east": KEELSPIRE_THREE_WELLS_KEY, "south": KEELSPIRE_SURVEY_HALL_KEY}, npcs=(CALDRIN_KEY,), tags=("level_22_30", "city", "hub", "factions", "safe")),
    _room(KEELSPIRE_THREE_WELLS_KEY, "Three Wells Court", KEELSPIRE_REGION_KEY, "Three public wells stand in the same courtyard: one sweet, one mineral, one historically unreliable. Today all three ropes hang lower than the painted ration lines. Sela Marr measures every bucket in public.", {"west": KEELSPIRE_CROWN_SQUARE_KEY, "south": KEELSPIRE_ARCHIVE_KEY}, npcs=(SELA_KEY,), tags=("level_24_30", "city", "water", "safe")),
    _room(KEELSPIRE_ARCHIVE_KEY, "Basin Archive", KEELSPIRE_REGION_KEY, "Maps fill racks from floor to ceiling: coastlines, drought lines, old shipping lanes, new wagon tracks, royal boundaries, well depths, sinkholes, and centuries of people redrawing the same basin as if the newest version could make the old ones stop being true.", {"north": KEELSPIRE_THREE_WELLS_KEY, "west": KEELSPIRE_SURVEY_HALL_KEY}, tags=("level_22_30", "city", "archive", "safe")),
    _room(KEELSPIRE_SURVEY_HALL_KEY, "Salt Survey Hall", KEELSPIRE_REGION_KEY, "Long tables hold core samples, salt columns, broken depth poles, ship timber, and bowls of mud sealed with dates. A floor mosaic of the old sea has been repeatedly patched where new collapses changed what surveyors thought lay beneath it.", {"north": KEELSPIRE_CROWN_SQUARE_KEY, "east": KEELSPIRE_ARCHIVE_KEY, "south": KEELSPIRE_HARBOR_VAULT_KEY}, tags=("level_25_30", "city", "survey", "safe")),
    _room(KEELSPIRE_HARBOR_VAULT_KEY, "Harbor Vault", KEELSPIRE_REGION_KEY, "Beneath the survey hall, a stone vault contains the original harbor's gate chains and drainage records. One wall vibrates faintly. Tavik has cleared a circular floor seal whose inscription translates roughly as INTAKE SERVICE, NOT PUBLIC STAIRS.", {"north": KEELSPIRE_SURVEY_HALL_KEY}, npcs=(TAVIK_KEY,), tags=("level_27_30", "city", "dungeon_entrance", "safe")),

    _room(GLASS_KEEL_APPROACH_KEY, "Glass Keel Wreck Approach", GLASS_KEEL_REGION_KEY, "The basin's largest wreck lies almost on its side, salt fused over the hull until planks and mineral crust look cast from one white substance. A torn opening in the upper hull serves as the entrance.", {"south": KEELGRAVE_FLATS_KEY, "down": GLASS_KEEL_SPLIT_DECK_KEY}, enemies=(KEEL_CRAWLER_KEY,), tags=("dungeon", "level_23_24")),
    _room(GLASS_KEEL_SPLIT_DECK_KEY, "Split Deck", GLASS_KEEL_REGION_KEY, "Because the ship lies at an angle, the old port wall is now the floor. Doorways stack diagonally overhead. Salt falls in thin sheets whenever the hull creaks in the heat.", {"up": GLASS_KEEL_APPROACH_KEY, "west": GLASS_KEEL_CARGO_KEY, "east": GLASS_KEEL_CHAPEL_KEY}, enemies=(KEEL_CRAWLER_KEY,), tags=("dungeon", "level_23_24")),
    _room(GLASS_KEEL_CARGO_KEY, "Cargo Gallery", GLASS_KEEL_REGION_KEY, "Broken cargo cages form a steep gallery. Amphorae once packed for sea travel now contain only salt crystals shaped like the liquids they replaced.", {"east": GLASS_KEEL_SPLIT_DECK_KEY, "down": GLASS_KEEL_BALLAST_KEY}, enemies=(KEEL_CRAWLER_KEY, BRINE_WIGHT_KEY), tags=("dungeon", "level_24")),
    _room(GLASS_KEEL_CHAPEL_KEY, "Salt Chapel", GLASS_KEEL_REGION_KEY, "A tiny sailors' shrine remains bolted to what is now a sloping wall. The ship's bronze bell has no clapper, yet a clean circular mark beneath it suggests something still swings here when nobody is looking.", {"west": GLASS_KEEL_SPLIT_DECK_KEY, "down": GLASS_KEEL_CAPTAIN_KEY}, enemies=(BRINE_WIGHT_KEY,), tags=("dungeon", "level_24", "oddity")),
    _room(GLASS_KEEL_BALLAST_KEY, "Ballast Spine", GLASS_KEEL_REGION_KEY, "Stone ballast has spilled into the ship's lower frame around a nest of pale shells. Copper channels along the keel remain damp enough to attract a monstrous crustacean that has made the old pumps its territory.", {"up": GLASS_KEEL_CARGO_KEY, "east": GLASS_KEEL_CAPTAIN_KEY}, enemies=(BALLAST_MATRIARCH_KEY,), tags=("dungeon", "boss", "level_24_25")),
    _room(GLASS_KEEL_CAPTAIN_KEY, "Captain's Round", GLASS_KEEL_REGION_KEY, "The captain's cabin survived because it was built like a box inside the hull. A log remains sealed in waxed copper leaves beside a circular chart showing tide heights from the sea's final decades.", {"up": GLASS_KEEL_CHAPEL_KEY, "west": GLASS_KEEL_BALLAST_KEY, "down": GLASS_KEEL_TIDEHOLD_KEY}, enemies=(BRINE_WIGHT_KEY,), tags=("dungeon", "clue", "level_24_25")),
    _room(GLASS_KEEL_TIDEHOLD_KEY, "Tideglass Hold", GLASS_KEEL_REGION_KEY, "The lowest hold contains one blue-white glass column connected to a tube that disappears through the keel into salt and stone. The sea is gone, but the liquid line inside the column rises and falls by a finger's width every few minutes.", {"up": GLASS_KEEL_CAPTAIN_KEY}, tags=("dungeon", "dungeon_end", "level_25")),

    _room(UNDERTIDE_INTAKE_KEY, "Undertide Intake Stair", UNDERTIDE_REGION_KEY, "The service stair descends below every mapped Keelspire cellar. Damp stone quickly replaces dry salt, and old directional arrows distinguish CITY, ROAD, SHALLOW WELLS, and DEEP CURRENT as if water distribution were ordinary civic machinery.", {"up": KEELSPIRE_HARBOR_VAULT_KEY, "down": UNDERTIDE_PRESSURE_WALK_KEY}, enemies=(PRESSURE_MITE_KEY,), tags=("dungeon", "level_27")),
    _room(UNDERTIDE_PRESSURE_WALK_KEY, "Pressure Walk", UNDERTIDE_REGION_KEY, "A narrow bridge crosses six enormous pipes. Gauges on five lines pulse together; the sixth stays pinned near its red mark while a compensator line shudders violently beside it.", {"up": UNDERTIDE_INTAKE_KEY, "east": UNDERTIDE_SIPHON_GALLERY_KEY}, enemies=(PRESSURE_MITE_KEY,), tags=("dungeon", "level_27", "clue")),
    _room(UNDERTIDE_SIPHON_GALLERY_KEY, "Siphon Gallery", UNDERTIDE_REGION_KEY, "Stone siphons curve overhead like ribs. Water can be heard moving inside every wall, sometimes uphill. Maintenance figures have scratched pressure calculations over older decorative carvings until function won the argument.", {"west": UNDERTIDE_PRESSURE_WALK_KEY, "down": UNDERTIDE_COUNTERWEIGHT_KEY}, enemies=(BRINE_WORM_KEY, PRESSURE_MITE_KEY), tags=("dungeon", "level_27_28")),
    _room(UNDERTIDE_COUNTERWEIGHT_KEY, "Counterweight Well", UNDERTIDE_REGION_KEY, "Three mineral-crusted counterweights hang over a black shaft. One has been lashed in place by a later repair crew, forcing the remaining two to carry an uneven load toward Regent Court.", {"up": UNDERTIDE_SIPHON_GALLERY_KEY, "east": UNDERTIDE_REGENT_KEY}, enemies=(VALVE_SENTINEL_KEY,), tags=("dungeon", "level_28", "mechanism")),
    _room(UNDERTIDE_REGENT_KEY, "Regent Court", UNDERTIDE_REGION_KEY, "The chamber floor is a pressure diagram made physical. In its center turns the Sluice Regent, opening and closing valves faster than any living operator could. Every motion sends water away from a line marked FAILURE CASCADE.", {"west": UNDERTIDE_COUNTERWEIGHT_KEY}, enemies=(SLUICE_REGENT_KEY,), tags=("dungeon", "boss", "level_28_29")),
    _room(UNDERTIDE_DISTRIBUTOR_KEY, "Broken Distributor", UNDERTIDE_REGION_KEY, "Beyond Regent Court, a circular distributor has split along one bearing. The Regent's emergency bypasses converge here from every direction, proving the machine was working around this failure rather than causing it.", {"west": UNDERTIDE_REGENT_KEY, "down": UNDERTIDE_HEART_KEY}, enemies=(VALVE_SENTINEL_KEY,), tags=("dungeon", "level_29", "revelation")),
    _room(UNDERTIDE_HEART_KEY, "Undertide Heart", UNDERTIDE_REGION_KEY, "A vaulted chamber surrounds a deep column of moving water. There is no pump here large enough to explain the flow. The engine does not create the Undertide; it intercepts, divides, and releases a natural underground current crossing the basin.", {"up": UNDERTIDE_DISTRIBUTOR_KEY, "down": UNDERTIDE_RELEASE_KEY}, enemies=(BRINE_WORM_KEY,), tags=("dungeon", "level_29_30", "clue")),
    _room(UNDERTIDE_RELEASE_KEY, "Deep Release Gate", UNDERTIDE_REGION_KEY, "Three immense release channels leave the engine: one climbs toward Keelspire's dead harbor, one branches into the old roadside cistern and well network, and one descends south along the basin's natural fault. Only one can receive full restoring pressure now.", {"up": UNDERTIDE_HEART_KEY}, tags=("dungeon", "level_30", "capstone")),
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


def salt_kingdoms_augmentations() -> dict[str, RoomAugmentation]:
    return {
        FAR_WATCH_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="west",
                    destination_key=SALTWIND_GATE_KEY,
                    name="Whitewake Road",
                    travel_text="You leave the Broken Reach westward. Chalk ridges fall away and the dead white floor of an inland sea opens before you.",
                    condition=ViewCondition(required_flags=(BROKEN_REACH_COMPLETE_FLAG,), min_level=21),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        TIDEMARK_SINK_KEY: RoomAugmentation(
            features=(
                _feature("whitewake_sink", "Wet Sinkhole", "a fresh collapse exposing wet blue mineral lines under dry salt", "The upper layers are ordinary salt crust. The deepest fracture is wet, and the blue line on its wall has formed recently. Water is moving below Whitewake strongly enough to change the basin floor from underneath.", ("sink", "sinkhole", "wet sink", "tidemark")),
            ),
            description_layers=(
                DescriptionLayer("harbor_tide_seen", "Far south, a blue-white strip now reflects light where Keelspire's harbor was dry.", priority=30, condition=ViewCondition(required_flags=(HARBOR_ENDING_FLAG,))),
                DescriptionLayer("wells_route_seen", "Fresh wagon marks turn southeast toward newly refilled roadside cisterns.", priority=30, condition=ViewCondition(required_flags=(WELLS_ENDING_FLAG,))),
                DescriptionLayer("current_cut_seen", "A thin running-water sound comes from the new gorge south of Pilgrim Salt.", priority=30, condition=ViewCondition(required_flags=(CURRENT_ENDING_FLAG,))),
            ),
        ),
        KEELSPIRE_ARCHIVE_KEY: RoomAugmentation(
            features=(
                _feature("basin_tidemarks", "Tide History Wall", "three centuries of shoreline and well-depth records pinned together", "The sea did not simply retreat year by year. It fell in distinct steps. Each major drop corresponds to reports of new springs appearing far from the basin, then drying again decades later. The newest well records show the same stepped pattern beginning underground now.", ("tidemarks", "tide marks", "maps", "history wall")),
            ),
        ),
        KEELSPIRE_THREE_WELLS_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="west",
                    destination_key=CISTERN_ROAD_KEY,
                    name="Refilled Cistern Road",
                    travel_text="You follow the new public water line west through the reopened cistern chain.",
                    condition=ViewCondition(required_flags=(WELLS_ENDING_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature("three_wells_rations", "Public Ration Slate", "a chalk slate listing bucket limits for city, caravan, and basin households", "The slate makes scarcity concrete. Keelspire households get less than comfort, caravans get enough only for scheduled crossings, and smaller basin wells are already receiving emergency carted water. Nobody on the board is getting everything they need.", ("rations", "ration slate", "slate", "water board")),
            ),
            description_layers=(
                DescriptionLayer("wells_restored", "All three well ropes are wet now. Nobody has removed the ration slate; Sela has only written REVIEW WEEKLY across it.", priority=20, condition=ViewCondition(required_flags=(WELLS_ENDING_FLAG,))),
            ),
        ),
        DUSTWELL_CAMP_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=CISTERN_ROAD_KEY,
                    name="Refilled Cistern Road",
                    travel_text="You take the newly marked cistern road east toward Keelspire's public wells.",
                    condition=ViewCondition(required_flags=(WELLS_ENDING_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("dustwell_restored", "The old well is working again. Drivers still measure by cup, but now to track consumption rather than decide who goes thirsty.", priority=20, condition=ViewCondition(required_flags=(WELLS_ENDING_FLAG,))),
            ),
        ),
        PILGRIM_SALT_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=SPRINGCUT_GORGE_KEY,
                    name="Springcut Gorge",
                    travel_text="You descend beside the new stream where released groundwater has cut through the salt crust.",
                    condition=ViewCondition(required_flags=(CURRENT_ENDING_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("current_restored", "A green-brown cut now crosses the white basin below the pilgrim path. Travelers have already moved several offerings to the new waterline.", priority=20, condition=ViewCondition(required_flags=(CURRENT_ENDING_FLAG,))),
            ),
        ),
        KEELSPIRE_GATE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="north",
                    destination_key=OLD_BREAKWATER_KEY,
                    name="Old Breakwater Road",
                    condition=ViewCondition(forbidden_flags=(HARBOR_ENDING_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("harbor_returned", "North of the gate, the old dry approach ends in new water. Traffic now reaches the city by the skiff channel from the Dry Quays instead of walking the former harbor floor.", priority=20, condition=ViewCondition(required_flags=(HARBOR_ENDING_FLAG,))),
            ),
        ),
        KEELSPIRE_QUAYS_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="north",
                    destination_key=TIDEMARK_SINK_KEY,
                    name="Whitewake Skiff Channel",
                    travel_text="A shallow public skiff carries you north across the newly returned harbor water to the edge of Tidemark Sink.",
                    condition=ViewCondition(required_flags=(HARBOR_ENDING_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("dry_quays_wet", "Water stands against the lowest quay stairs for the first time in generations. Children have already been told six times not to jump in from the crane arms.", priority=20, condition=ViewCondition(required_flags=(HARBOR_ENDING_FLAG,))),
            ),
        ),
        GLASS_KEEL_CHAPEL_KEY: RoomAugmentation(
            features=(
                _feature("buried_ship_bell", "Clapperless Ship Bell", "a bronze bell with no visible clapper and a clean circle beneath it", "The bell is firmly bolted. The clean circle below it is exactly clapper-sized. Nothing should be moving here, but fresh polish marks say otherwise.", ("bell", "ship bell", "bronze bell")),
            ),
        ),
        GLASS_KEEL_CAPTAIN_KEY: RoomAugmentation(
            features=(
                _feature("captains_tide_log", "Copper Tide Log", "waxed copper leaves recording the sea's final measured decades", "The final sea did not shrink smoothly. The water dropped in pulses separated by years of stability. On the last page the captain writes: 'Current below keel persists when surface wind is dead.'", ("log", "tide log", "captains log", "copper log")),
            ),
        ),
        GLASS_KEEL_TIDEHOLD_KEY: RoomAugmentation(
            features=(
                _feature("living_tideglass", "Living Tideglass", "a blue-white fluid column still rising and falling beneath a ship stranded on dry land", "The tube disappears below the keel into stone. The liquid rises, pauses, and falls with no relation to wind or surface temperature. It is measuring pressure from moving water far below the dead seabed.", ("tideglass", "tide glass", "glass", "column")),
            ),
        ),
        KEELSPIRE_HARBOR_VAULT_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=UNDERTIDE_INTAKE_KEY,
                    name="Undertide Service Stair",
                    travel_text="You break the inspection seal and descend into the Undertide service works.",
                    condition=ViewCondition(required_flags=(GLASS_KEEL_COMPLETE_FLAG, FACTION_COMPLETE_FLAG), min_level=27),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        UNDERTIDE_PRESSURE_WALK_KEY: RoomAugmentation(
            features=(
                _feature("undertide_gauges", "Six Pressure Gauges", "six old gauges with one failed line and one overworked compensator", "Five gauges rise and fall in sequence. The failed distributor line remains high while a smaller compensator line cycles almost continuously. Something downstream has been preventing the imbalance from becoming a rupture.", ("gauges", "pressure gauges", "gauge")),
            ),
        ),
        UNDERTIDE_COUNTERWEIGHT_KEY: RoomAugmentation(
            features=(
                _feature("undertide_counterweights", "Distributor Counterweights", "three hanging weights, one locked and two overloaded", "The locking pin is a later emergency repair. Rebalancing the three weights will reduce the load on Regent Court without pretending the broken distributor is fixed.", ("counterweights", "weights", "counterweight")),
            ),
        ),
        UNDERTIDE_DISTRIBUTOR_KEY: RoomAugmentation(
            features=(
                _feature("broken_distributor", "Broken Distributor", "a split central bearing surrounded by the Regent's emergency bypasses", "Every emergency line from Regent Court terminates here. The Sluice Regent was not hoarding water. It had spent generations stealing pressure from healthy channels to keep this failed distributor from tearing the whole engine apart.", ("distributor", "bearing", "broken distributor")),
            ),
            description_layers=(
                DescriptionLayer("regent_understood", "With the Regent gone, the emergency lines sit still long enough to read. Their purpose is unmistakable: compensation, not theft.", priority=20, condition=ViewCondition(required_flags=(REGENT_TRUTH_FLAG,))),
            ),
        ),
        UNDERTIDE_HEART_KEY: RoomAugmentation(
            features=(
                _feature("undertide_water", "Undertide Current", "a deep natural column of moving groundwater passing through the engine", "The water is older than the machinery around it. The builders intercepted a natural current and gave it choices. Keelspire, road cisterns, shallow aquifers, and the deep southern fault were all outlets, not sources.", ("water", "current", "undertide", "heart")),
            ),
        ),
        KEELSPIRE_CROWN_SQUARE_KEY: RoomAugmentation(
            description_layers=(
                DescriptionLayer("priority_city", "A temporary priority notice places Keelspire's civic wells first until the Undertide can be understood safely.", priority=40, condition=ViewCondition(required_flags=(CITY_FIRST_FLAG,))),
                DescriptionLayer("priority_road", "A temporary priority notice protects the caravan cistern chain from being cut off whenever city rationing tightens.", priority=40, condition=ViewCondition(required_flags=(ROAD_FIRST_FLAG,))),
                DescriptionLayer("priority_wells", "A temporary priority notice requires basin settlements to receive measured water before surplus can be claimed by any crown office.", priority=40, condition=ViewCondition(required_flags=(WELLS_FIRST_FLAG,))),
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


def install_salt_kingdoms_content(world_service=None) -> None:
    for quest in SALT_KINGDOMS_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in SALT_KINGDOMS_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in SALT_KINGDOMS_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for npc in SALT_KINGDOMS_NPCS:
        _replace_npc(npc)
    for room in SALT_KINGDOMS_ROOMS:
        _replace_room(room)

    if world_service is None:
        return
    for room in SALT_KINGDOMS_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in salt_kingdoms_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*SALT_KINGDOMS_ROOM_KEYS, FAR_WATCH_KEY):
            cache.pop(room_key, None)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _in_salt_kingdoms(session) -> bool:
    return bool(session.character and (session.character.current_room or "") in SALT_KINGDOMS_ROOM_KEYS)


def _refresh(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _award(session, xp: int, item_key: str | None = None) -> int:
    assert session.character is not None
    old_level = session.character.level
    new_level = session.database.add_experience(session.character.id, xp)
    if item_key is not None and session.database.item_quantity(session.character.id, item_key) < 1:
        session.database.add_item(session.character.id, item_key, 1)
    _refresh(session)
    return max(0, new_level - old_level)


def _ensure_story(session) -> str | None:
    if session.character is None or not _in_salt_kingdoms(session):
        return None
    flags = _flags(session)
    level = session.character.level
    if level >= 21 and ARRIVAL_COMPLETE_FLAG not in flags and _quest(session, ARRIVAL_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, ARRIVAL_QUEST_KEY, "talk_enna")
        return "New region story: The Road Where the Sea Was. Talk to Cartographer Enna Vale at Saltwind Gate."
    if ARRIVAL_COMPLETE_FLAG in flags and level >= 23 and GLASS_KEEL_COMPLETE_FLAG not in flags and _quest(session, GLASS_KEEL_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, GLASS_KEEL_QUEST_KEY, "talk_orro")
        return "New dungeon story: The Ship That Still Measures Tide. Find Salvager Orro Pike on Keelspire's Dry Quays."
    if GLASS_KEEL_COMPLETE_FLAG in flags and level >= 26 and FACTION_COMPLETE_FLAG not in flags and _quest(session, FACTION_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, FACTION_QUEST_KEY, "talk_crown")
        return "New city story: Three Thirsts, One Basin. Start with Harbor Steward Caldrin Vey in Crown Square."
    if FACTION_COMPLETE_FLAG in flags and level >= 27 and UNDERTIDE_COMPLETE_FLAG not in flags and _quest(session, UNDERTIDE_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, UNDERTIDE_QUEST_KEY, "talk_tavik")
        return "New dungeon story: The Undertide Engine. Engine Reader Tavik Bronzehand is waiting in the Harbor Vault."
    if UNDERTIDE_COMPLETE_FLAG in flags and level >= 30 and CAPSTONE_COMPLETE_FLAG not in flags and _quest(session, CAPSTONE_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, CAPSTONE_QUEST_KEY, "reach_release")
        return "Level-30 region capstone: Where the Water Goes. Return to the Deep Release Gate and decide which channel receives restoring pressure."
    return None


async def _talk_enna(session) -> bool:
    if session.character is None or session.character.current_room != SALTWIND_GATE_KEY:
        return False
    _ensure_story(session)
    q = _quest(session, ARRIVAL_QUEST_KEY)
    if q and q["status"] == "active":
        if q["current_step"] == "talk_enna":
            session.database.advance_quest(session.character.id, ARRIVAL_QUEST_KEY, "inspect_sink")
            await session.send("Enna turns the map board sideways. 'Three wagon losses looked like bad driving until the holes lined up with old depth contours. Cross the basin and EXAMINE SINK at Tidemark Sink. If the bottom is wet, we stop calling this a dry-road problem.'\r\n")
            return True
        if q["current_step"] == "return_enna":
            session.database.complete_quest(session.character.id, ARRIVAL_QUEST_KEY)
            session.database.grant_flag(session.character.id, ARRIVAL_COMPLETE_FLAG)
            gained = _award(session, 2600, WHITEWAKE_PASS_KEY)
            await session.send("Enna marks a blue line beneath the white map instead of on top of it. 'Good. The sea is gone. The water is not. That distinction may save more wagons than another hundred warning posts.'\r\nQuest complete: The Road Where the Sea Was. Reward: 2600 XP and Whitewake Basin Pass.\r\n")
            if gained:
                await session.send(f"You gained {gained} level.\r\n")
            follow = _ensure_story(session)
            if follow:
                await session.send(f"{follow}\r\n")
            return True
        await session.send("Enna taps the unfinished blue line. 'Finish the route evidence. The basin is already moving whether our map admits it or not.'\r\n")
        return True
    await session.send("Enna says, 'Every useful map is an argument with yesterday.'\r\n")
    return True


async def _inspect_sink(session) -> bool:
    if session.character is None or session.character.current_room != TIDEMARK_SINK_KEY:
        return False
    q = _quest(session, ARRIVAL_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_sink":
        return False
    session.database.advance_quest(session.character.id, ARRIVAL_QUEST_KEY, "reach_city")
    await session.send("The deepest crack is wet. More important, fresh blue mineral lines cross old silt below the salt crust. Water is moving under Whitewake hard enough to dissolve support from beneath the road. Reach Keelspire and find the Basin Archive.\r\n")
    return True


async def _read_tidemarks(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_ARCHIVE_KEY:
        return False
    q = _quest(session, ARRIVAL_QUEST_KEY)
    if not q or q["status"] != "active":
        return False
    if q["current_step"] == "reach_city":
        session.database.advance_quest(session.character.id, ARRIVAL_QUEST_KEY, "read_tidemarks")
        q = _quest(session, ARRIVAL_QUEST_KEY)
    if q["current_step"] != "read_tidemarks":
        return False
    session.database.advance_quest(session.character.id, ARRIVAL_QUEST_KEY, "return_enna")
    await session.send("The archive shows the old sea dropping in steps, not as one long drought. Each historical drop coincides with springs appearing elsewhere, then failing later. The newest well charts show the same pressure migration happening again below the basin. Return to Enna at Saltwind Gate.\r\n")
    return True


async def _talk_orro(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_QUAYS_KEY:
        return False
    _ensure_story(session)
    q = _quest(session, GLASS_KEEL_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_orro":
        session.database.advance_quest(session.character.id, GLASS_KEEL_QUEST_KEY, "read_log")
        await session.send("Orro points north toward the giant wreck. 'Glass Keel sailed when this was water. Its captain logged the last real tides. READ LOG in the Captain's Round. If the old fool measured anything below the keel, I want the exact words.'\r\n")
        return True
    await session.send("Orro grins. 'Best thing about ship salvage in a desert? Nobody asks whether the weather is good for sailing.'\r\n")
    return True


async def _read_log(session) -> bool:
    if session.character is None or session.character.current_room != GLASS_KEEL_CAPTAIN_KEY:
        return False
    q = _quest(session, GLASS_KEEL_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "read_log":
        return False
    session.database.advance_quest(session.character.id, GLASS_KEEL_QUEST_KEY, "defeat_matriarch")
    await session.send("The copper leaves record a sea that fell in pulses. The final entry reads: 'Surface calm. Wind dead. Current below keel persists north to south.' The tideglass line ran through the ballast spaces. Something nesting down there has blocked the safest route.\r\n")
    return True


async def _inspect_tideglass(session) -> bool:
    if session.character is None or session.character.current_room != GLASS_KEEL_TIDEHOLD_KEY:
        return False
    q = _quest(session, GLASS_KEEL_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_tideglass":
        return False
    session.database.complete_quest(session.character.id, GLASS_KEEL_QUEST_KEY)
    session.database.grant_flag(session.character.id, GLASS_KEEL_COMPLETE_FLAG)
    gained = _award(session, 3400, TIDEGLASS_SLIVER_KEY)
    await session.send("The blue-white column rises and falls against pressure from below the keel. A dead ship is still measuring a living tide—only the tide is underground now. You chip one loose sliver from the cracked instrument housing without breaking the tube.\r\nQuest complete: The Ship That Still Measures Tide. Reward: 3400 XP and Living Tideglass Sliver.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    follow = _ensure_story(session)
    if follow:
        await session.send(f"{follow}\r\n")
    return True


async def _talk_caldrin(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_CROWN_SQUARE_KEY:
        return False
    _ensure_story(session)
    q = _quest(session, FACTION_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_crown":
        session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "talk_caravan")
        await session.send("Caldrin says, 'Keelspire's wells support the basin's largest clinic, archive, repair yards, and market. I will argue for the city first. I will not pretend that makes everyone outside the gate imaginary. Hear Nima at Ropemarket.'\r\n")
        return True
    await session.send("Caldrin says, 'A crown is a claim. Infrastructure is a promise. They should not be confused.'\r\n")
    return True


async def _talk_nima(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_ROPEMARKET_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_caravan":
        session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "talk_wells")
        await session.send("Nima rests both hands on her travel staff. 'A city can shorten baths. A caravan cannot shorten forty miles of salt. The road cisterns are not merchant luxury; they are what makes crossing possible at all. Now hear Sela at Three Wells Court.'\r\n")
        return True
    await session.send("Nima says, 'Trade is only interesting after everyone survives the road.'\r\n")
    return True


async def _talk_sela(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_THREE_WELLS_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_wells":
        session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "read_rations")
        await session.send("Sela lifts one nearly empty bucket. 'Little wells die quietly. No gate closes. No caravan vanishes. A family just walks farther tomorrow. READ RATIONS before you decide whose thirst looks most official.'\r\n")
        return True
    await session.send("Sela says, 'Water that reaches everybody slowly is still more useful than water that reaches one flag quickly.'\r\n")
    return True


async def _read_rations(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_THREE_WELLS_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "read_rations":
        return False
    session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "choose_priority")
    await session.send("The ration slate makes all three cases uncomfortable. The city is cutting clinic reserves. Caravans are abandoning crossings. Outlying settlements are hauling water by cart. Return to Crown Square and choose which need leads while the engine is investigated: PRIORITY CITY, PRIORITY ROAD, or PRIORITY WELLS.\r\n")
    return True


async def _choose_priority(session, priority: str) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_CROWN_SQUARE_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "choose_priority":
        return False
    mapping = {
        "city": (CITY_FIRST_FLAG, "You place Keelspire's civic wells first while requiring the city to publish every diversion."),
        "road": (ROAD_FIRST_FLAG, "You protect the caravan cistern chain first so distance itself does not become a private toll."),
        "wells": (WELLS_FIRST_FLAG, "You place the shallow basin wells first, accepting a messier distribution that is harder for any one authority to control."),
    }
    chosen = mapping.get(priority)
    if chosen is None:
        return False
    flag, text = chosen
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, FACTION_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, FACTION_QUEST_KEY)
    gained = _award(session, 3900, THREE_THIRSTS_TOKEN_KEY)
    await session.send(f"{text}\r\nCaldrin, Nima, and Sela all sign the same temporary allocation sheet. Nobody calls it permanent because none of them has seen the machine yet.\r\nQuest complete: Three Thirsts, One Basin. Reward: 3900 XP and Three Thirsts Token.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    follow = _ensure_story(session)
    if follow:
        await session.send(f"{follow}\r\n")
    return True


async def _talk_tavik(session) -> bool:
    if session.character is None or session.character.current_room != KEELSPIRE_HARBOR_VAULT_KEY:
        return False
    _ensure_story(session)
    q = _quest(session, UNDERTIDE_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_tavik":
        session.database.advance_quest(session.character.id, UNDERTIDE_QUEST_KEY, "read_gauges")
        await session.send("Tavik puts an ear to the floor. 'The service stair is open. READ GAUGES before touching anything. If the Sluice Regent is stealing pressure, the gauges will show it. If it is spending pressure, that is a different accusation.'\r\n")
        return True
    await session.send("Tavik says, 'Machines lie less often than interpreters, but they can still answer the wrong question perfectly.'\r\n")
    return True


async def _read_gauges(session) -> bool:
    if session.character is None or session.character.current_room != UNDERTIDE_PRESSURE_WALK_KEY:
        return False
    q = _quest(session, UNDERTIDE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "read_gauges":
        return False
    session.database.advance_quest(session.character.id, UNDERTIDE_QUEST_KEY, "set_counterweight")
    await session.send("Five lines pulse normally. One distributor line stays dangerously high while a smaller compensator cycles almost without rest. The Regent is drawing pressure into itself from the failing line, not pushing pressure into it. Continue to the Counterweight Well and SET COUNTERWEIGHT before the fight.\r\n")
    return True


async def _set_counterweight(session) -> bool:
    if session.character is None or session.character.current_room != UNDERTIDE_COUNTERWEIGHT_KEY:
        return False
    q = _quest(session, UNDERTIDE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "set_counterweight":
        return False
    session.database.advance_quest(session.character.id, UNDERTIDE_QUEST_KEY, "defeat_regent")
    await session.send("You free the emergency locking pin and rebalance all three weights. The pipe-hammering drops from a frantic rhythm to a heavy pulse. Regent Court opens. Whatever the Sluice Regent has been compensating for, you have at least taken some of the load off before confronting it.\r\n")
    return True


async def _inspect_distributor(session) -> bool:
    if session.character is None or session.character.current_room != UNDERTIDE_DISTRIBUTOR_KEY:
        return False
    q = _quest(session, UNDERTIDE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_distributor":
        return False
    session.database.grant_flag(session.character.id, REGENT_TRUTH_FLAG)
    session.database.advance_quest(session.character.id, UNDERTIDE_QUEST_KEY, "listen_water")
    await session.send("The distributor's central bearing failed long ago. Every bypass from the Sluice Regent leads here. It was not the machine stealing Whitewake's water; it was the machine sacrificing healthy channels to keep one broken hub from rupturing everything. You fought the emergency response because it looked like control. Descend to the Undertide Heart and LISTEN WATER.\r\n")
    return True


async def _listen_water(session) -> bool:
    if session.character is None or session.character.current_room != UNDERTIDE_HEART_KEY:
        return False
    q = _quest(session, UNDERTIDE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "listen_water":
        return False
    session.database.complete_quest(session.character.id, UNDERTIDE_QUEST_KEY)
    session.database.grant_flag(session.character.id, UNDERTIDE_COMPLETE_FLAG)
    gained = _award(session, 5200, REGENT_GAUGE_KEY)
    await session.send("The water below is not pump-driven. Its rhythm continues when the remaining machinery pauses. The Undertide Engine was built across a natural underground current and gave that current controlled exits: harbor, road cisterns, shallow wells, and the deep southern fault. The broken distributor can be bypassed, but not at full pressure in every direction at once.\r\nQuest complete: The Undertide Engine. Reward: 5200 XP and Regent's Counter-Gauge.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    follow = _ensure_story(session)
    if follow:
        await session.send(f"{follow}\r\n")
    return True


async def _choose_water(session, ending: str) -> bool:
    if session.character is None or session.character.current_room != UNDERTIDE_RELEASE_KEY:
        return False
    q = _quest(session, CAPSTONE_QUEST_KEY)
    if not q or q["status"] != "active":
        return False
    if q["current_step"] == "reach_release":
        session.database.advance_quest(session.character.id, CAPSTONE_QUEST_KEY, "choose_water")
        q = _quest(session, CAPSTONE_QUEST_KEY)
    if q["current_step"] != "choose_water":
        return False
    mapping = {
        "harbor": (
            HARBOR_ENDING_FLAG,
            "You give restoring pressure to Keelspire's harbor channel. Water rises against the lowest dry quays, swallowing the old north gate approach and opening a shallow skiff route across the basin edge.",
        ),
        "wells": (
            WELLS_ENDING_FLAG,
            "You feed the old cistern and shallow-well network. The dead sea stays dead, but dark water returns to roadside wells and a new public cistern road links Dustwell directly to Keelspire.",
        ),
        "current": (
            CURRENT_ENDING_FLAG,
            "You free the Undertide into its natural southern fault. A new spring cuts through Pilgrim Salt, restoring a living stream nobody in Keelspire can completely own or predict.",
        ),
    }
    chosen = mapping.get(ending)
    if chosen is None:
        return False
    flag, text = chosen
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, CAPSTONE_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, CAPSTONE_QUEST_KEY)
    gained = _award(session, 7000, WATER_DECISION_SEAL_KEY)
    await session.send(f"{text}\r\nRegion capstone complete: Where the Water Goes. Reward: 7000 XP and Salt Kingdoms Water Seal. The Whitewake map has permanently changed for this character.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    return True


async def _discover_oddity(session, flag: str, text: str, *, item_key: str | None = None) -> bool:
    if session.character is None:
        return False
    if flag in _flags(session):
        await session.send(f"{text}\r\n")
        return True
    session.database.grant_flag(session.character.id, flag)
    gained = _award(session, 160, item_key)
    await session.send(f"{text}\r\nDiscovery recorded: +160 XP.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
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


def install_salt_kingdoms_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_salt_kingdoms_midgame_installed", False):
        return
    install_salt_kingdoms_content(world_service)

    previous_enter_character = player_session_class.enter_character
    previous_move_character = player_session_class.move_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        message = _ensure_story(self)
        if message:
            await self.send(f"\r\n{message}\r\n")

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character else None
        await previous_move_character(self, direction)
        if self.character is None or self.character.current_room == before:
            return
        q = _quest(self, ARRIVAL_QUEST_KEY)
        if q and q["status"] == "active" and q["current_step"] == "reach_city" and self.character.current_room in CITY_ROOM_KEYS:
            self.database.advance_quest(self.character.id, ARRIVAL_QUEST_KEY, "read_tidemarks")
            await self.send("\r\nKeelspire is the first city you have seen built around the absence of water. The Basin Archive east of Three Wells Court holds the old tide record. READ TIDEMARKS there.\r\n")
        message = _ensure_story(self)
        if message:
            await self.send(f"\r\n{message}\r\n")

    async def _finish_enemy_defeat(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish_enemy(self, enemy)
        if not eligible or self.character is None:
            return
        glass_q = _quest(self, GLASS_KEEL_QUEST_KEY)
        if key == BALLAST_MATRIARCH_KEY and glass_q and glass_q["status"] == "active" and glass_q["current_step"] == "defeat_matriarch":
            self.database.advance_quest(self.character.id, GLASS_KEEL_QUEST_KEY, "inspect_tideglass")
            await self.send("The Ballast Matriarch folds into its shattered shell nest. Behind it, the old tide tube disappears through the keel. The route to the Tideglass Hold is clear. EXAMINE TIDEGLASS below.\r\n")
            return
        engine_q = _quest(self, UNDERTIDE_QUEST_KEY)
        if key == SLUICE_REGENT_KEY and engine_q and engine_q["status"] == "active" and engine_q["current_step"] == "defeat_regent":
            self.database.grant_flag(self.character.id, REGENT_DEFEATED_FLAG)
            self.database.advance_quest(self.character.id, UNDERTIDE_QUEST_KEY, "inspect_distributor")
            await self.send("The Sluice Regent stops with two arms still braced against the high-pressure line. The door beyond unlocks. Before deciding what you just defeated, go east and EXAMINE DISTRIBUTOR.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = _normalize(command)

        if normalized in {"talk enna", "talk to enna", "talk cartographer", "talk to cartographer"} and await _talk_enna(self):
            return
        if normalized in {"examine sink", "inspect sink", "look sink", "examine sinkhole"} and await _inspect_sink(self):
            return
        if normalized in {"read tidemarks", "read tide marks", "examine tidemarks", "read maps"} and await _read_tidemarks(self):
            return
        if normalized in {"talk orro", "talk to orro", "talk salvager", "talk to salvager"} and await _talk_orro(self):
            return
        if normalized in {"read log", "read tide log", "read captains log", "examine log"} and await _read_log(self):
            return
        if normalized in {"examine tideglass", "inspect tideglass", "look tideglass", "examine tide glass"} and await _inspect_tideglass(self):
            return
        if normalized in {"talk caldrin", "talk to caldrin", "talk steward", "talk to steward"} and await _talk_caldrin(self):
            return
        if normalized in {"talk nima", "talk to nima", "talk caravan", "talk speaker"} and await _talk_nima(self):
            return
        if normalized in {"talk sela", "talk to sela", "talk wellkeeper", "talk to wellkeeper"} and await _talk_sela(self):
            return
        if normalized in {"read rations", "read ration slate", "examine rations", "read water board"} and await _read_rations(self):
            return
        if normalized.startswith("priority "):
            priority = normalized.split(maxsplit=1)[1]
            if priority in {"city", "road", "wells"} and await _choose_priority(self, priority):
                return
        if normalized in {"talk tavik", "talk to tavik", "talk engine reader", "talk engineer"} and await _talk_tavik(self):
            return
        if normalized in {"read gauges", "examine gauges", "inspect gauges"} and await _read_gauges(self):
            return
        if normalized in {"set counterweight", "set counterweights", "balance counterweight", "balance counterweights"} and await _set_counterweight(self):
            return
        if normalized in {"examine distributor", "inspect distributor", "look distributor"} and await _inspect_distributor(self):
            return
        if normalized in {"listen water", "listen to water", "listen current", "listen undertide"} and await _listen_water(self):
            return
        if normalized in {"send harbor", "send water harbor", "send to harbor"} and await _choose_water(self, "harbor"):
            return
        if normalized in {"feed wells", "send wells", "send to wells"} and await _choose_water(self, "wells"):
            return
        if normalized in {"free current", "release current", "send current"} and await _choose_water(self, "current"):
            return

        if self.character.current_room == GLASS_KEEL_CHAPEL_KEY and normalized in {"wait", "listen bell", "watch bell"}:
            await _discover_oddity(self, ODDITY_BELL_FLAG, "You wait until the hull stops creaking. The clapperless bell gives one dull note anyway. Digging beneath it reveals the missing clapper, polished bright along one edge as if it has continued swinging under the salt.", item_key=SALT_BELL_CLAPPER_KEY)
            return
        if self.character.current_room == WHITEWAKE_CAUSEWAY_KEY and normalized in {"watch shadows", "examine shadows", "look shadows"}:
            await _discover_oddity(self, ODDITY_SHADOW_FLAG, "At noon, the old depth markers cast dry black shadows. One marker's shadow looks wet at the edges and reflects a sky that is not visible anywhere else.")
            return
        if self.character.current_room == KEELSPIRE_ARCHIVE_KEY and normalized in {"search maps", "search archive", "examine old map"}:
            await _discover_oddity(self, ODDITY_MAP_FLAG, "Behind a royal survey you find a much older basin map depicting open water but no shoreline at all—the blue simply continues beyond every edge of the page.")
            return
        if self.character.current_room == UNDERTIDE_RELEASE_KEY and normalized in {"wait", "watch cup", "examine cup"}:
            await _discover_oddity(self, ODDITY_CUP_FLAG, "A forgotten measuring cup sits dry beside the release gate. While you watch, one clear drop appears in it from nowhere. Then another. The cup stops at exactly one-third full.")
            return

        if normalized in {"salt kingdoms", "whitewake", "salt help"} and _in_salt_kingdoms(self):
            flags = _flags(self)
            completed = sum(flag in flags for flag in (ARRIVAL_COMPLETE_FLAG, GLASS_KEEL_COMPLETE_FLAG, FACTION_COMPLETE_FLAG, UNDERTIDE_COMPLETE_FLAG, CAPSTONE_COMPLETE_FLAG))
            oddities = sum(flag in flags for flag in ODDITY_FLAGS)
            await self.send(
                f"Salt Kingdoms: {completed}/5 major stories completed; {oddities}/4 recorded oddities found.\r\n"
                "Levels 21-22 cross the dead sea and learn why the roads are failing. Levels 23-25 explore the Glass Keel. Level 26 forces the city, caravan league, and basin wells into one public priority. Levels 27-29 descend through the Undertide Engine. Level 30 decides where the restored water goes and changes the map.\r\n"
            )
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._salt_kingdoms_midgame_installed = True
