from __future__ import annotations

import asyncio

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.mechanics as mechanics
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.dwarf_start import DWARF_START_ROOM_KEY
from mud.moon_elf_city import MOON_ELF_START_ROOM_KEY
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition
from mud.troll_start import TROLL_STONEJAW_PASS_KEY
from mud.veyra_city import VEYRA_EAST_RIVER_GATE_KEY, VEYRA_NORTH_WATERWORKS_KEY, VEYRA_SCHOLARS_RISE_KEY
from mud.world import NpcDefinition, RoomDefinition

TROLL_REGION_KEY = "thornwake_troll_country"
DWARF_REGION_KEY = "deepwheel_dwarf_corridor"
MOON_REGION_KEY = "counterstar_highroad"
MERIDIAN_REGION_KEY = "meridian_vault"

TROLL_ENTRY_KEY = "thornwake_northroad_weir"
TROLL_CAMP_KEY = "thornwake_moot_camp"
TROLL_BOSS_KEY = "thornwake_splitroot_hollow"
TROLL_CLUE_KEY = "thornwake_hollow_meridian_root"
TROLL_ENDPOINT_KEY = "thornwake_north_witness_overlook"
DWARF_ENTRY_KEY = "deepwheel_east_freight_mile"
DWARF_HUB_KEY = "deepwheel_surface_terminal"
DWARF_BOSS_KEY = "deepwheel_runaway_drill_bay"
DWARF_CLUE_KEY = "deepwheel_zero_depth_survey"
DWARF_ENDPOINT_KEY = "deepwheel_mountain_exchange"
MOON_ENTRY_KEY = "counterstar_cloudbreak_stair"
MOON_HUB_KEY = "counterstar_highroad_wayhouse"
MOON_BOSS_KEY = "counterstar_skyglass_ward"
MOON_CLUE_KEY = "counterstar_chart_court"
MOON_ENDPOINT_KEY = "counterstar_high_horizon_approach"
MERIDIAN_CAMP_KEY = "meridian_confluence_camp"
MERIDIAN_WITNESS_KEY = "meridian_three_witness_hall"
MERIDIAN_BOSS_KEY = "meridian_nameless_core"
MERIDIAN_DAIS_KEY = "meridian_return_dais"

TROLL_QUEST_KEY = "thornwake_two_futures"
DWARF_QUEST_KEY = "deepwheel_zero_depth"
MOON_QUEST_KEY = "counterstar_false_sky"
MERIDIAN_QUEST_KEY = "meridian_before_names"
TWENTIETH_QUEST_KEY = "meridian_twentieth_step"

TROLL_COMPLETE_FLAG = "midgame_troll_witness_complete"
TROLL_HEARTH_FLAG = "midgame_troll_choice_hearthbound"
TROLL_TRAIL_FLAG = "midgame_troll_choice_longtrail"
TROLL_BOSS_FLAG = "midgame_troll_ravager_defeated"
DWARF_COMPLETE_FLAG = "midgame_dwarf_witness_complete"
DWARF_SEAL_FLAG = "midgame_dwarf_choice_seal_line"
DWARF_OPEN_FLAG = "midgame_dwarf_choice_keep_line"
DWARF_BOSS_FLAG = "midgame_dwarf_drill_defeated"
MOON_COMPLETE_FLAG = "midgame_moon_witness_complete"
MOON_PUBLISH_FLAG = "midgame_moon_choice_publish"
MOON_HOLD_FLAG = "midgame_moon_choice_hold"
MOON_BOSS_FLAG = "midgame_moon_warden_defeated"
MERIDIAN_COMPLETE_FLAG = "midgame_meridian_first_clear"
MERIDIAN_ALIGNED_FLAG = "midgame_meridian_witnesses_aligned"
MERIDIAN_BOSS_FLAG = "midgame_meridian_custodian_defeated"
TWENTIETH_COMPLETE_FLAG = "midgame_level_20_milestone_complete"
FINAL_REQUIRED_FLAGS = (TROLL_COMPLETE_FLAG, DWARF_COMPLETE_FLAG, MOON_COMPLETE_FLAG)

TROLL_WITNESS_ITEM_KEY = "thornwake_root_witness"
DWARF_WITNESS_ITEM_KEY = "deepwheel_zero_depth_gauge"
MOON_WITNESS_ITEM_KEY = "counterstar_plate"
MERIDIAN_TROPHY_KEY = "meridian_nameless_shard"
TWENTIETH_SEAL_KEY = "three_roads_seal"

TROLL_NPC_KEY = "thornwake_speaker_varka_mossback"
DWARF_NPC_KEY = "deepwheel_foreman_nolla_gaugehand"
MOON_NPC_KEY = "counterstar_astronomer_eiren_vael"
MERIDIAN_NPC_KEY = "meridian_archivist_tern"
TROLL_RAVAGER_KEY = "thornwake_antler_ravager"
DWARF_DRILL_KEY = "deepwheel_runaway_drill"
MOON_WARDEN_KEY = "counterstar_skyglass_warden"
MERIDIAN_CUSTODIAN_KEY = "meridian_nameless_custodian"

TROLL_QUEST = QuestDefinition(
    key=TROLL_QUEST_KEY, name="Two Futures Under One Canopy", style="structured", minimum_level=12,
    description="Troll strongholds north of Veyra are splitting over protected hunting corridors versus negotiated roads. Neither side is a monster faction; the deeper problem is what the forest itself is growing around.",
    objective_steps=(("talk_speaker", "TALK VARKA at Thornwake Moot Camp."), ("reach_splitroot", "Reach Splitroot Hollow."), ("defeat_ravager", "Defeat the Antler-Crowned Ravager."), ("study_meridian", "At the Hollow Meridian Root, STUDY ROOTS."), ("choose_future", "Choose SUPPORT HEARTH or SUPPORT TRAIL."), ("complete", "Carry the Troll witness out of Thornwake.")),
)
DWARF_QUEST = QuestDefinition(
    key=DWARF_QUEST_KEY, name="The Zero-Depth Reading", style="structured", minimum_level=12,
    description="East of Veyra, rails, pressure mains, steam lifts, and checkpoints descend toward the Dwarven mountain city. New instruments insist a chamber exists below zero mapped depth.",
    objective_steps=(("talk_foreman", "TALK NOLLA at the Surface Freight Terminal."), ("ride_deep", "Descend through the rail network."), ("defeat_drill", "Stop the Runaway Deep Drill."), ("read_instruments", "At Zero-Depth Survey, READ GAUGES."), ("choose_line", "Choose SEAL DEEP LINE or KEEP DEEP LINE."), ("complete", "Carry the Dwarven witness out of Deepwheel.")),
)
MOON_QUEST = QuestDefinition(
    key=MOON_QUEST_KEY, name="A Star That Is Not Missing", style="structured", minimum_level=13,
    description="Above Veyra, old Moon Elf observatories disagree with the sky in exactly the same way, and the disagreement moves when the observer changes altitude.",
    objective_steps=(("talk_astronomer", "TALK EIREN at the Highroad Wayhouse."), ("reach_ward", "Cross the old observing road."), ("defeat_warden", "Defeat the Skyglass Warden."), ("compare_charts", "At Chart Court, COMPARE CHARTS."), ("choose_record", "Choose PUBLISH CHART or HOLD CHART."), ("complete", "Carry the Moon Elf witness out of the highroad.")),
)
MERIDIAN_QUEST = QuestDefinition(
    key=MERIDIAN_QUEST_KEY, name="The Vault Before Names", style="structured", minimum_level=19,
    description="The Troll root scar, Dwarven zero-depth reading, and Moon Elf counterstar plate identify the same impossible coordinate below all three regions.",
    objective_steps=(("enter_vault", "Reach Confluence Camp after completing all three regional witnesses."), ("align_witnesses", "At Three-Witness Hall, ALIGN WITNESSES."), ("descend", "Descend through the Meridian Vault."), ("defeat_custodian", "Defeat the Nameless Custodian."), ("read_core", "READ CORE."), ("complete", "Confirm that the structure predates the cultures above it.")),
)
TWENTIETH_QUEST = QuestDefinition(
    key=TWENTIETH_QUEST_KEY, name="The Twentieth Step", style="structured", minimum_level=20,
    description="Level twenty is the first deliberate midgame class milestone. Return from the Meridian Vault and claim the stronger tool your class has grown into.",
    objective_steps=(("stand_at_dais", "Reach the Return Dais after clearing the Meridian Vault."), ("claim_milestone", "Use CLAIM TWENTIETH STEP."), ("complete", "Your level-20 class milestone is recognized.")),
)
MIDGAME_QUESTS = (TROLL_QUEST, DWARF_QUEST, MOON_QUEST, MERIDIAN_QUEST, TWENTIETH_QUEST)

MIDGAME_ITEMS = (
    ItemDefinition(TROLL_WITNESS_ITEM_KEY, "Root-Witness Knot", "A cut of living-black root grown around a perfectly straight empty seam.", "trophy", tier=4),
    ItemDefinition(DWARF_WITNESS_ITEM_KEY, "Zero-Depth Gauge", "A sealed Dwarven pressure gauge whose witness needle crossed below its mechanical stop.", "trophy", tier=4),
    ItemDefinition(MOON_WITNESS_ITEM_KEY, "Counterstar Plate", "A Moon Elf observation plate whose starless meridian points down through the mountain.", "trophy", tier=4),
    ItemDefinition(MERIDIAN_TROPHY_KEY, "Nameless Meridian Shard", "A warm gray fragment from the Meridian Core with no known tool marks.", "trophy", tier=5),
    ItemDefinition(TWENTIETH_SEAL_KEY, "Three Roads Seal", "A Veyran seal stamped with root, gauge, and star-plate marks.", "credential", tier=5),
)

MIDGAME_NPCS = (
    NpcDefinition(TROLL_NPC_KEY, "Speaker Varka Mossback", "a scarred Troll mediator carrying one war-token from each side on the same staff", TROLL_CAMP_KEY, "Thornwake civil-war mediator", dialogue=("'Hearthbound protect migration corridors. Longtrail want roads and trade. Both have buried people this season.'", "'Find what is twisting the roots before you decide what our argument means.'")),
    NpcDefinition(DWARF_NPC_KEY, "Foreman Nolla Gaugehand", "a Dwarf survey foreman carrying three pressure ledgers and one well-used hammer", DWARF_HUB_KEY, "Deepwheel survey foreman", dialogue=("'Different crews. Different instruments. Same impossible depth.'", "'If the line closes, say why. If it stays open, say what makes that responsible.'")),
    NpcDefinition(MOON_NPC_KEY, "Astronomer Eiren Vael", "a Moon Elf carrying two contradictory star journals and treating neither as an insult", MOON_HUB_KEY, "Counterstar survey astronomer", dialogue=("'A wrong chart is useful if it tells you exactly how it is wrong.'", "'This is data, not prophecy.'")),
    NpcDefinition(MERIDIAN_NPC_KEY, "Archivist Tern", "an Undead field archivist sitting among three cultures' instruments", MERIDIAN_CAMP_KEY, "Meridian expedition recorder", dialogue=("'Agreement is not the same as explanation.'", "'If the complex gives you a story too quickly, distrust the story before the measurements.'")),
)

def _enemy(key, name, aliases, description, hp, ac, damage, interval, xp):
    return EnemyDefinition(key=key, name=name, aliases=aliases, description=description, max_hp=hp, armor_class=ac, auto_attack_damage=damage, auto_attack_interval=interval, xp_reward=xp)

THORNWAKE_WOLF = _enemy("thornwake_boneback_wolf", "Boneback Wolf", ("wolf", "boneback", "boneback wolf"), "a huge forest wolf with pale scar ridges along its spine", 220, 11, 16, 2.7, 170)
THORNWAKE_SKIRMISHER = _enemy("thornwake_breakaway_skirmisher", "Breakaway Skirmisher", ("skirmisher", "breakaway", "troll skirmisher"), "an armed Troll from a splinter band that abandoned both main camps for road robbery", 285, 13, 18, 2.9, 220)
TROLL_RAVAGER = _enemy(TROLL_RAVAGER_KEY, "Antler-Crowned Ravager", ("ravager", "antler ravager", "antler-crowned ravager"), "a massive whitehorn bull with black root growth wound around one antler", 720, 15, 24, 2.8, 1100)
DEEPWHEEL_CRAWLER = _enemy("deepwheel_rail_crawler", "Rail Crawler", ("crawler", "rail crawler", "vermin"), "a plated cave scavenger feeding on grease and hot mineral scale", 250, 12, 17, 2.9, 190)
DEEPWHEEL_AUTOMATON = _enemy("deepwheel_pressure_automaton", "Pressure Automaton", ("automaton", "pressure automaton", "machine"), "a maintenance machine continuing an abandoned repair order", 330, 15, 20, 3.1, 260)
DWARF_DRILL = _enemy(DWARF_DRILL_KEY, "Runaway Deep Drill", ("drill", "deep drill", "runaway drill"), "a locomotive-sized boring rig bucking against locked rails without a crew", 880, 17, 27, 3.0, 1350)
COUNTERSTAR_RAPTOR = _enemy("counterstar_cliff_raptor", "Cliff Raptor", ("raptor", "cliff raptor", "bird"), "a broad-winged mountain predator riding the highroad wind", 260, 13, 18, 2.5, 205)
COUNTERSTAR_SENTINEL = _enemy("counterstar_old_sentinel", "Old Skyglass Sentinel", ("sentinel", "skyglass sentinel", "old sentinel"), "a pale stone-and-glass construct enforcing an obsolete boundary", 360, 16, 21, 3.0, 290)
MOON_WARDEN = _enemy(MOON_WARDEN_KEY, "Skyglass Warden", ("warden", "skyglass warden", "glass warden"), "a faceless construct holding a circular plate that reflects the wrong stars", 940, 18, 28, 2.9, 1500)
MERIDIAN_SENTINEL = _enemy("meridian_seam_sentinel", "Seam Sentinel", ("sentinel", "seam sentinel", "vault sentinel"), "a jointless gray figure that seems redrawn between steps", 430, 17, 25, 2.8, 360)
MERIDIAN_ECHO = _enemy("meridian_measure_echo", "Measure Echo", ("echo", "measure echo", "vault echo"), "a moving distortion that repeats the corridor half a heartbeat late", 390, 15, 27, 2.6, 340)
MERIDIAN_CUSTODIAN = _enemy(MERIDIAN_CUSTODIAN_KEY, "The Nameless Custodian", ("custodian", "nameless custodian", "keeper"), "a towering gray custodian assembled around a hollow center", 1550, 20, 34, 2.8, 3200)
MIDGAME_ENEMIES = (THORNWAKE_WOLF, THORNWAKE_SKIRMISHER, TROLL_RAVAGER, DEEPWHEEL_CRAWLER, DEEPWHEEL_AUTOMATON, DWARF_DRILL, COUNTERSTAR_RAPTOR, COUNTERSTAR_SENTINEL, MOON_WARDEN, MERIDIAN_SENTINEL, MERIDIAN_ECHO, MERIDIAN_CUSTODIAN)

def _room(key, name, region, description, exits, *, npcs=(), enemies=(), tags=()):
    return RoomDefinition(key=key, name=name, region_key=region, description=description, exits=exits, npc_keys=npcs, enemy_keys=enemies, tags=("shared_world", "midgame_12_20", *tags))

TROLL_ROOMS = (
    _room(TROLL_ENTRY_KEY, "Northroad Weir", TROLL_REGION_KEY, "Veyra's watercourse ends where Troll trail marks begin beside the north road.", {"south": VEYRA_NORTH_WATERWORKS_KEY, "north": "thornwake_pinebreak_mile"}, tags=("level_12_13", "troll_country")),
    _room("thornwake_pinebreak_mile", "Pinebreak Mile", TROLL_REGION_KEY, "Old hunting trails cross a newer wagon cut while fresh branch barriers show an unresolved dispute.", {"south": TROLL_ENTRY_KEY, "north": TROLL_CAMP_KEY, "east": "thornwake_longtrail_camp"}, enemies=(THORNWAKE_WOLF.key,), tags=("level_12_13", "forest")),
    _room(TROLL_CAMP_KEY, "Thornwake Moot Camp", TROLL_REGION_KEY, "Hearthbound and Longtrail camps face the same neutral fire instead of pretending either side has left.", {"south": "thornwake_pinebreak_mile", "north": "thornwake_ashbough_fork", "east": "thornwake_longtrail_camp", "west": "thornwake_hearthbound_watch"}, npcs=(TROLL_NPC_KEY,), tags=("level_12_14", "safe", "civil_war", "choice_hub")),
    _room("thornwake_hearthbound_watch", "Hearthbound Watch", TROLL_REGION_KEY, "Hunters protect a migration corridor that newer freight routes keep disturbing.", {"east": TROLL_CAMP_KEY, "north": "thornwake_ashbough_fork"}, tags=("level_13_14", "civil_war")),
    _room("thornwake_longtrail_camp", "Longtrail Camp", TROLL_REGION_KEY, "Pack elk, route ledgers, and trade sledges support clans who want negotiated roads instead of isolation.", {"west": TROLL_CAMP_KEY, "north": "thornwake_ashbough_fork"}, tags=("level_13_14", "civil_war")),
    _room("thornwake_ashbough_fork", "Ashbough Fork", TROLL_REGION_KEY, "Both political trails converge around a lightning-killed cedar carved with names from both factions.", {"south": TROLL_CAMP_KEY, "east": TROLL_BOSS_KEY, "north": "thornwake_war_cairn"}, enemies=(THORNWAKE_SKIRMISHER.key,), tags=("level_14_15", "contested")),
    _room(TROLL_BOSS_KEY, "Splitroot Hollow", TROLL_REGION_KEY, "A whitehorn wallow has been torn open around a root mass split by a perfectly straight dark seam.", {"west": "thornwake_ashbough_fork"}, tags=("level_14_16", "boss")),
    _room("thornwake_war_cairn", "War Cairn", TROLL_REGION_KEY, "Broken weapons from kin-fights record the cost of a civil war without calling anyone heroic for it.", {"south": "thornwake_ashbough_fork", "east": "thornwake_priest_grove"}, tags=("level_14_15", "civil_war")),
    _room("thornwake_priest_grove", "Priest Grove", TROLL_REGION_KEY, "Troll priests treat wounded hunters, frightened animals, and political envoys in the same quiet grove.", {"west": TROLL_BOSS_KEY, "south": "thornwake_war_cairn", "north": TROLL_CLUE_KEY}, tags=("level_15_16", "safe", "priests")),
    _room(TROLL_CLUE_KEY, "Hollow Meridian Root", TROLL_REGION_KEY, "An ancient spruce has grown for decades around a vertical absence that remains perfectly straight.", {"south": "thornwake_priest_grove", "north": "thornwake_stonejaw_road"}, tags=("level_15_16", "phenomenon", "choice")),
    _room("thornwake_stonejaw_road", "Stonejaw Road", TROLL_REGION_KEY, "An old migration road climbs beyond the political camps toward colder strongholds.", {"south": TROLL_CLUE_KEY, "north": TROLL_ENDPOINT_KEY}, enemies=(THORNWAKE_WOLF.key,), tags=("level_16", "travel")),
    _room(TROLL_ENDPOINT_KEY, "North Witness Overlook", TROLL_REGION_KEY, "Stonejaw Pass is visible ahead, reconnecting this midgame road to the Troll homeland.", {"south": "thornwake_stonejaw_road", "north": TROLL_STONEJAW_PASS_KEY}, tags=("level_16", "safe", "regional_link")),
)
DWARF_ROOMS = (
    _room(DWARF_ENTRY_KEY, "East Freight Mile", DWARF_REGION_KEY, "Ore wagons leave Veyra on a raised road where paired iron rails gradually take over the traffic.", {"west": VEYRA_EAST_RIVER_GATE_KEY, "east": "deepwheel_pressure_checkpoint"}, tags=("level_12_13", "dwarf_route")),
    _room("deepwheel_pressure_checkpoint", "Pressure Checkpoint", DWARF_REGION_KEY, "A gatehouse checks cargo papers and steam fittings with equal seriousness.", {"west": DWARF_ENTRY_KEY, "east": DWARF_HUB_KEY}, enemies=(DEEPWHEEL_CRAWLER.key,), tags=("level_12_13", "checkpoint")),
    _room(DWARF_HUB_KEY, "Surface Freight Terminal", DWARF_REGION_KEY, "Rail gauges, freight lifts, and Nolla's survey table crowd the last major station outside the mountain.", {"west": "deepwheel_pressure_checkpoint", "east": "deepwheel_rail_cut", "down": "deepwheel_steam_lift"}, npcs=(DWARF_NPC_KEY,), tags=("level_12_14", "safe", "rail_hub")),
    _room("deepwheel_rail_cut", "Basalt Rail Cut", DWARF_REGION_KEY, "The first proper rail line slices through basalt under numbered pressure call boxes.", {"west": DWARF_HUB_KEY, "east": "deepwheel_switchyard"}, enemies=(DEEPWHEEL_CRAWLER.key,), tags=("level_13_14", "rail")),
    _room("deepwheel_switchyard", "Nine-Switch Yard", DWARF_REGION_KEY, "Interlocked mechanical points route ore cars toward nine shafts without allowing conflicting paths.", {"west": "deepwheel_rail_cut", "south": "deepwheel_steam_lift", "east": "deepwheel_second_registry"}, enemies=(DEEPWHEEL_AUTOMATON.key,), tags=("level_14_15", "rail")),
    _room("deepwheel_steam_lift", "Grand Descent Cage", DWARF_REGION_KEY, "A freight cage the size of a house drops beside pressure mains into hot darkness.", {"up": DWARF_HUB_KEY, "north": "deepwheel_switchyard", "down": "deepwheel_second_registry"}, tags=("level_14_16", "steam_lift")),
    _room("deepwheel_second_registry", "Second Registry", DWARF_REGION_KEY, "Far below the surface, another civic desk signs every deep-line crew in and out.", {"up": "deepwheel_steam_lift", "west": "deepwheel_switchyard", "east": "deepwheel_deepwheel_station"}, tags=("level_15_16", "safe", "bureaucracy")),
    _room("deepwheel_deepwheel_station", "Deepwheel Station", DWARF_REGION_KEY, "Locomotives turn on a circular stone table while one chained spur pulses with pressure from beyond its wall.", {"west": "deepwheel_second_registry", "east": DWARF_BOSS_KEY, "south": DWARF_CLUE_KEY}, enemies=(DEEPWHEEL_AUTOMATON.key,), tags=("level_16_17", "rail")),
    _room(DWARF_BOSS_KEY, "Runaway Drill Bay", DWARF_REGION_KEY, "An obsolete boring machine bucks against locked rails without a crew.", {"west": "deepwheel_deepwheel_station"}, tags=("level_16_17", "boss")),
    _room(DWARF_CLUE_KEY, "Zero-Depth Survey", DWARF_REGION_KEY, "Mechanical, hydraulic, and plumb-line instruments all point below the mountain's mapped zero depth.", {"north": "deepwheel_deepwheel_station", "east": "deepwheel_lower_exchange"}, tags=("level_17_18", "phenomenon", "choice")),
    _room("deepwheel_lower_exchange", "Lower Exchange", DWARF_REGION_KEY, "Ore, food, parts, and workers transfer between the new deep line and much older city tunnels.", {"west": DWARF_CLUE_KEY, "east": DWARF_ENDPOINT_KEY}, tags=("level_17_18", "safe", "trade")),
    _room(DWARF_ENDPOINT_KEY, "Mountain Exchange", DWARF_REGION_KEY, "The Deepwheel corridor joins the old civic tunnel directly beneath Foundry Concourse.", {"west": "deepwheel_lower_exchange", "up": DWARF_START_ROOM_KEY}, tags=("level_18", "safe", "regional_link")),
)
MOON_ROOMS = (
    _room(MOON_ENTRY_KEY, "Cloudbreak Stair", MOON_REGION_KEY, "The stair above Veyra climbs until altitude markers replace ordinary mile stones.", {"down": VEYRA_SCHOLARS_RISE_KEY, "up": "counterstar_thin_air_shelf"}, tags=("level_13_14", "moon_route", "high_altitude")),
    _room("counterstar_thin_air_shelf", "Thin-Air Shelf", MOON_REGION_KEY, "The road crosses above the cloud line while cliff raptors ride the updrafts.", {"down": MOON_ENTRY_KEY, "up": MOON_HUB_KEY}, enemies=(COUNTERSTAR_RAPTOR.key,), tags=("level_13_14", "high_altitude")),
    _room(MOON_HUB_KEY, "Highroad Wayhouse", MOON_REGION_KEY, "A warm stone wayhouse shelters travelers and three rival mapmakers; Eiren has covered one table in contradictory journals.", {"down": "counterstar_thin_air_shelf", "north": "counterstar_mirrored_cut"}, npcs=(MOON_NPC_KEY,), tags=("level_13_15", "safe", "survey")),
    _room("counterstar_mirrored_cut", "Mirrored Cut", MOON_REGION_KEY, "Cliff mirrors let observers compare the same sky from two sides of a blind turn.", {"south": MOON_HUB_KEY, "north": "counterstar_whitewind_bridge"}, enemies=(COUNTERSTAR_RAPTOR.key,), tags=("level_14_15", "observation")),
    _room("counterstar_whitewind_bridge", "Whitewind Bridge", MOON_REGION_KEY, "A cable-braced bridge crosses a drop so deep that weather moves below it.", {"south": "counterstar_mirrored_cut", "north": "counterstar_fallen_observatory"}, tags=("level_14_16", "bridge")),
    _room("counterstar_fallen_observatory", "Fallen Observatory", MOON_REGION_KEY, "A roofless observatory points its sighting stones into the mountain instead of at moon or horizon.", {"south": "counterstar_whitewind_bridge", "east": "counterstar_long_sky_terrace"}, enemies=(COUNTERSTAR_SENTINEL.key,), tags=("level_15_16", "ruins")),
    _room("counterstar_long_sky_terrace", "Long-Sky Terrace", MOON_REGION_KEY, "Snow ranges and enormous sky make Veyra feel very far from the center of anything.", {"west": "counterstar_fallen_observatory", "east": "counterstar_archive"}, tags=("level_16_17", "vista")),
    _room("counterstar_archive", "Counterstar Archive", MOON_REGION_KEY, "Generations of journals record the same moving absence, usually followed by embarrassed corrections.", {"west": "counterstar_long_sky_terrace", "east": MOON_BOSS_KEY}, tags=("level_16_17", "archive")),
    _room(MOON_BOSS_KEY, "Skyglass Ward", MOON_REGION_KEY, "A faceless Warden wakes between pale columns holding a plate that reflects stars not visible here.", {"west": "counterstar_archive"}, tags=("level_17_18", "boss")),
    _room("counterstar_horizon_scar", "Horizon Scar", MOON_REGION_KEY, "An ancient straight cut crosses rock and boulders that should have shifted over centuries.", {"west": MOON_BOSS_KEY, "east": MOON_CLUE_KEY}, tags=("level_17_18", "phenomenon")),
    _room(MOON_CLUE_KEY, "Chart Court", MOON_REGION_KEY, "Three observation plates at different heights turn the apparent missing star into a line pointing down through the range.", {"west": "counterstar_horizon_scar", "up": MOON_ENDPOINT_KEY}, tags=("level_18", "choice", "observation")),
    _room(MOON_ENDPOINT_KEY, "High Horizon Approach", MOON_REGION_KEY, "The survey road crests onto the ridge below High Horizon, reconnecting the midgame to the Moon Elf homeland.", {"down": MOON_CLUE_KEY, "up": MOON_ELF_START_ROOM_KEY}, tags=("level_18", "safe", "regional_link")),
)
MERIDIAN_ROOMS = (
    _room(MERIDIAN_CAMP_KEY, "Confluence Camp", MERIDIAN_REGION_KEY, "Troll roots, Dwarven instruments, and Moon Elf plates all point through the same unmarked wall.", {"east": MERIDIAN_WITNESS_KEY}, npcs=(MERIDIAN_NPC_KEY,), tags=("level_19_20", "safe", "dungeon_approach")),
    _room(MERIDIAN_WITNESS_KEY, "Three-Witness Hall", MERIDIAN_REGION_KEY, "Three recesses fit three independently made witness objects with impossible precision.", {"west": MERIDIAN_CAMP_KEY}, tags=("level_19_20", "puzzle")),
    _room("meridian_outer_lock", "Outer Lock", MERIDIAN_REGION_KEY, "The first door has no hinge or mechanism; after alignment the wall simply occupies somewhere else.", {"west": MERIDIAN_WITNESS_KEY, "east": "meridian_stone_lens"}, enemies=(MERIDIAN_SENTINEL.key,), tags=("level_19_20", "dungeon")),
    _room("meridian_stone_lens", "Stone Lens", MERIDIAN_REGION_KEY, "A circular aperture makes straight lines beyond it appear to bend around an unseen center.", {"west": "meridian_outer_lock", "down": "meridian_null_stair"}, tags=("level_19_20", "dungeon")),
    _room("meridian_null_stair", "Null Stair", MERIDIAN_REGION_KEY, "Steps descend while every carried gauge insists altitude is unchanged.", {"up": "meridian_stone_lens", "down": "meridian_gearless_lift"}, enemies=(MERIDIAN_ECHO.key,), tags=("level_19_20", "dungeon")),
    _room("meridian_gearless_lift", "Gearless Lift", MERIDIAN_REGION_KEY, "A platform moves without cable, pressure, counterweight, rune, or visible magic.", {"up": "meridian_null_stair", "down": "meridian_root_archive"}, tags=("level_19_20", "dungeon")),
    _room("meridian_root_archive", "Root Archive", MERIDIAN_REGION_KEY, "Fossil roots bend around the same hollow seam seen in Thornwake, but some are far older than known Troll strongholds.", {"up": "meridian_gearless_lift", "east": "meridian_skyless_observatory"}, enemies=(MERIDIAN_SENTINEL.key,), tags=("level_19_20", "dungeon", "troll_evidence")),
    _room("meridian_skyless_observatory", "Skyless Observatory", MERIDIAN_REGION_KEY, "Sighting frames point into solid stone using the same ratios as the Counterstar plates.", {"west": "meridian_root_archive", "east": "meridian_broken_causeway"}, tags=("level_19_20", "dungeon", "moon_evidence")),
    _room("meridian_broken_causeway", "Broken Causeway", MERIDIAN_REGION_KEY, "A bridge's missing center casts a complete shadow as if unseen material remains there.", {"west": "meridian_skyless_observatory", "east": "meridian_custodian_gallery"}, enemies=(MERIDIAN_ECHO.key,), tags=("level_19_20", "dungeon")),
    _room("meridian_custodian_gallery", "Custodian Gallery", MERIDIAN_REGION_KEY, "Wall niches hold gray figures in proportions matching no current people of Astralis.", {"west": "meridian_broken_causeway", "down": "meridian_resonance_well"}, enemies=(MERIDIAN_SENTINEL.key,), tags=("level_19_20", "dungeon")),
    _room("meridian_resonance_well", "Resonance Well", MERIDIAN_REGION_KEY, "A deep shaft answers footsteps with root-creak, pressure knock, and struck-skyglass tone.", {"up": "meridian_custodian_gallery", "down": "meridian_hinge_engine"}, tags=("level_19_20", "dungeon")),
    _room("meridian_hinge_engine", "Hinge Engine", MERIDIAN_REGION_KEY, "An engine-sized structure rotates around an axis that cannot be located.", {"up": "meridian_resonance_well", "east": "meridian_antechamber"}, enemies=(MERIDIAN_ECHO.key,), tags=("level_19_20", "dungeon")),
    _room("meridian_antechamber", "Nameless Antechamber", MERIDIAN_REGION_KEY, "There are no letters, crowns, gods, tools, or faces here—only engineered proportions with no cultural signature.", {"west": "meridian_hinge_engine", "east": MERIDIAN_BOSS_KEY}, tags=("level_19_20", "dungeon")),
    _room(MERIDIAN_BOSS_KEY, "Nameless Core", MERIDIAN_REGION_KEY, "A hollow gray sphere hangs above the Hollow Meridian while the Custodian unfolds around it.", {"west": "meridian_antechamber"}, tags=("level_20", "boss", "capstone")),
    _room(MERIDIAN_DAIS_KEY, "Return Dais", MERIDIAN_REGION_KEY, "A plain platform faces the route back. The reward is realizing the unanswered question is larger than it was before.", {"west": MERIDIAN_BOSS_KEY}, tags=("level_20", "safe", "capstone_end")),
)
MIDGAME_ROOMS = TROLL_ROOMS + DWARF_ROOMS + MOON_ROOMS + MERIDIAN_ROOMS
MIDGAME_ROOM_KEYS = tuple(room.key for room in MIDGAME_ROOMS)

LEVEL_20_BRUTE = mechanics.AbilityDefinition(key="unbroken_stance", name="Unbroken Stance", unlock_level=20, mana_cost=14, cooldown_seconds=30.0, description="Seize top threat, recover a fifth of your health, and halve incoming damage for twelve seconds.", category="threat_survival", skill_improves_effectiveness=False, design_status="approved_level_20_live")
LEVEL_20_WIZARD = mechanics.AbilityDefinition(key="starbreaker", name="Starbreaker", unlock_level=20, mana_cost=16, cooldown_seconds=15.0, description="Collapse a precise arcane line through one target for extreme direct spell damage.", category="spell_damage", design_status="approved_level_20_live")
LEVEL_20_DRUID = mechanics.AbilityDefinition(key="deep_roots", name="Deep Roots", unlock_level=20, mana_cost=16, cooldown_seconds=28.0, description="Restore a large pulse of party health and ward everyone present for eight seconds.", category="group_healing", skill_improves_effectiveness=False, design_status="approved_level_20_live")
LEVEL_20_PRIEST = mechanics.AbilityDefinition(key="last_light", name="Last Light", unlock_level=20, mana_cost=18, cooldown_seconds=32.0, description="Heal every living party member present and leave a ten-second sanctuary ward.", category="group_healing", skill_improves_effectiveness=False, design_status="approved_level_20_live")
LEVEL_20_NECRO = mechanics.AbilityDefinition(key="raise_grave_knight", name="Raise Grave Knight", unlock_level=20, mana_cost=14, cooldown_seconds=20.0, description="Consume four Bone Chips to replace your Skeleton with a persistent Grave Knight whose Grave Command strikes harder.", category="pet_summon", catalyst_item_key="bone_chips", catalyst_quantity=4, design_status="approved_level_20_live")
LEVEL_20_ABILITIES = {"brute": LEVEL_20_BRUTE, "wizard": LEVEL_20_WIZARD, "druid": LEVEL_20_DRUID, "priest": LEVEL_20_PRIEST, "necromancer": LEVEL_20_NECRO}
LEVEL_20_ABILITY_KEYS = {ability.key for ability in LEVEL_20_ABILITIES.values()}

def _merge_augmentation(existing, extra):
    if existing is None:
        return extra
    overrides = {item.direction: item for item in existing.exit_overrides}; overrides.update({item.direction: item for item in extra.exit_overrides})
    extras = {(item.direction, item.destination_key): item for item in existing.extra_exits}; extras.update({(item.direction, item.destination_key): item for item in extra.extra_exits})
    features = {item.key: item for item in existing.features}; features.update({item.key: item for item in extra.features})
    layers = {item.key: item for item in existing.description_layers}; layers.update({item.key: item for item in extra.description_layers})
    return RoomAugmentation(tuple(overrides.values()), tuple(extras.values()), tuple(features.values()), tuple(layers.values()))

def _x(direction, destination, name, text, condition):
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, condition=condition, hidden_when_unavailable=True)

def midgame_augmentations():
    all_three = ViewCondition(required_flags=FINAL_REQUIRED_FLAGS, min_level=19)
    return {
        VEYRA_NORTH_WATERWORKS_KEY: RoomAugmentation(extra_exits=(_x("north", TROLL_ENTRY_KEY, "North Road into Thornwake", "You follow the watercourse into Troll-marked forest road.", ViewCondition(min_level=12)),)),
        VEYRA_EAST_RIVER_GATE_KEY: RoomAugmentation(extra_exits=(_x("east", DWARF_ENTRY_KEY, "East Freight Mile", "You follow ore wagons toward the mountain rails.", ViewCondition(min_level=12)),)),
        VEYRA_SCHOLARS_RISE_KEY: RoomAugmentation(extra_exits=(_x("up", MOON_ENTRY_KEY, "Cloudbreak Highroad", "You climb until altitude markers replace mile stones.", ViewCondition(min_level=13)),)),
        TROLL_STONEJAW_PASS_KEY: RoomAugmentation(extra_exits=(_x("north", TROLL_ENDPOINT_KEY, "Thornwake Road", "You continue beyond the starter patrol boundary.", ViewCondition(min_level=12)),)),
        DWARF_START_ROOM_KEY: RoomAugmentation(extra_exits=(_x("down", DWARF_ENDPOINT_KEY, "Deepwheel Exchange", "A public lift descends into the Deepwheel corridor.", ViewCondition(min_level=12)),)),
        MOON_ELF_START_ROOM_KEY: RoomAugmentation(extra_exits=(_x("down", MOON_ENDPOINT_KEY, "Counterstar Highroad", "A ridge road descends toward the old survey route.", ViewCondition(min_level=13)),)),
        TROLL_ENDPOINT_KEY: RoomAugmentation(extra_exits=(_x("down", MERIDIAN_CAMP_KEY, "Hidden Confluence Descent", "The three witnesses reveal a marked descent beneath the roots.", all_three),)),
        DWARF_ENDPOINT_KEY: RoomAugmentation(extra_exits=(_x("down", MERIDIAN_CAMP_KEY, "Zero-Depth Expedition Lift", "A locked expedition lift descends below the mapped mountain.", all_three),)),
        MOON_ENDPOINT_KEY: RoomAugmentation(extra_exits=(_x("down", MERIDIAN_CAMP_KEY, "Counterstar Descent", "The aligned route points down toward Confluence Camp.", all_three),)),
        TROLL_BOSS_KEY: RoomAugmentation(extra_exits=(_x("east", "thornwake_priest_grove", "Priest Road", "With the Ravager down, the priest road opens.", ViewCondition(required_flags=(TROLL_BOSS_FLAG,))),)),
        DWARF_BOSS_KEY: RoomAugmentation(extra_exits=(_x("south", DWARF_CLUE_KEY, "Zero-Depth Survey", "With the drill stopped, the survey line is quiet.", ViewCondition(required_flags=(DWARF_BOSS_FLAG,))),)),
        MOON_BOSS_KEY: RoomAugmentation(extra_exits=(_x("east", "counterstar_horizon_scar", "Horizon Scar", "With the Warden silent, the old observing road continues.", ViewCondition(required_flags=(MOON_BOSS_FLAG,))),)),
        MERIDIAN_WITNESS_KEY: RoomAugmentation(extra_exits=(_x("east", "meridian_outer_lock", "Outer Lock", "The aligned witnesses shift the wall aside.", ViewCondition(required_flags=(MERIDIAN_ALIGNED_FLAG,))),)),
        MERIDIAN_BOSS_KEY: RoomAugmentation(extra_exits=(_x("east", MERIDIAN_DAIS_KEY, "Return Dais", "With the Custodian down, the eastern wall opens.", ViewCondition(required_flags=(MERIDIAN_BOSS_FLAG,))),)),
    }

def _replace_room(room):
    if room.key in legacy_world.ROOMS_BY_KEY: legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else: legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room

def _replace_npc(npc):
    if npc.key in legacy_world.NPCS_BY_KEY: legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else: legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc

def _upsert_ability(class_key, ability):
    by_key = {item.key: item for item in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())}; by_key[ability.key] = ability
    mechanics.FIXED_CLASS_ABILITIES[class_key] = tuple(sorted(by_key.values(), key=lambda item: (item.unlock_level or 1, item.name)))

def install_midgame_12_20_content(world_service=None):
    for quest in MIDGAME_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY: quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for item in MIDGAME_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY: crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for enemy in MIDGAME_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY: combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for npc in MIDGAME_NPCS: _replace_npc(npc)
    for room in MIDGAME_ROOMS: _replace_room(room)
    economy.LOOT_TABLES[TROLL_RAVAGER_KEY] = (economy.LootDrop("rough_hide", 2),)
    economy.LOOT_TABLES[DWARF_DRILL_KEY] = (economy.LootDrop("iron_ore", 3),)
    economy.LOOT_TABLES[MOON_WARDEN_KEY] = (economy.LootDrop("gloamworks_cold_glass", 1),)
    economy.LOOT_TABLES[MERIDIAN_CUSTODIAN_KEY] = (economy.LootDrop(MERIDIAN_TROPHY_KEY, 1),)
    _upsert_ability("brute", LEVEL_20_BRUTE); _upsert_ability("wizard", LEVEL_20_WIZARD); _upsert_ability("druid", LEVEL_20_DRUID); _upsert_ability("necromancer", LEVEL_20_NECRO)
    for path_key, current in tuple(mechanics.PRIEST_DEITY_ABILITIES.items()):
        by_key = {ability.key: ability for ability in current}; by_key[LEVEL_20_PRIEST.key] = LEVEL_20_PRIEST
        mechanics.PRIEST_DEITY_ABILITIES[path_key] = tuple(sorted(by_key.values(), key=lambda item: (item.unlock_level or 1, item.name)))
    if world_service is None: return
    for room in MIDGAME_ROOMS: world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in midgame_augmentations().items(): world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*MIDGAME_ROOM_KEYS, VEYRA_NORTH_WATERWORKS_KEY, VEYRA_EAST_RIVER_GATE_KEY, VEYRA_SCHOLARS_RISE_KEY, TROLL_STONEJAW_PASS_KEY, DWARF_START_ROOM_KEY, MOON_ELF_START_ROOM_KEY): cache.pop(key, None)

def _flags(session): return set() if session.character is None else set(session.database.list_flags(session.character.id))
def _quest(session, key): return None if session.character is None else session.database.get_quest(session.character.id, key)
def _refresh(session):
    if session.character is not None:
        updated = session.database.get_character_by_name(session.character.name)
        if updated is not None: session.character = updated

def _start_if_needed(session, quest, room_keys, step):
    if session.character is not None and session.character.current_room in room_keys and session.character.level >= quest.minimum_level and _quest(session, quest.key) is None: session.database.start_quest(session.character.id, quest.key, step)

def _ensure_quests(session):
    _start_if_needed(session, TROLL_QUEST, tuple(room.key for room in TROLL_ROOMS), "talk_speaker")
    _start_if_needed(session, DWARF_QUEST, tuple(room.key for room in DWARF_ROOMS), "talk_foreman")
    _start_if_needed(session, MOON_QUEST, tuple(room.key for room in MOON_ROOMS), "talk_astronomer")
    if session.character is None: return
    flags = _flags(session)
    if session.character.current_room in tuple(room.key for room in MERIDIAN_ROOMS) and set(FINAL_REQUIRED_FLAGS).issubset(flags) and _quest(session, MERIDIAN_QUEST_KEY) is None: session.database.start_quest(session.character.id, MERIDIAN_QUEST_KEY, "enter_vault")
    if session.character.current_room == MERIDIAN_DAIS_KEY and session.character.level >= 20 and MERIDIAN_COMPLETE_FLAG in flags and TWENTIETH_COMPLETE_FLAG not in flags and _quest(session, TWENTIETH_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, TWENTIETH_QUEST_KEY, "claim_milestone")

def _grant_once(session, flag):
    if session.character is None or flag in _flags(session): return False
    session.database.grant_flag(session.character.id, flag); return True

def _victory_sessions(session, enemy):
    finder = getattr(session, "party_victory_sessions", None)
    if callable(finder):
        found = finder(enemy)
        if found: return list(found)
    return [session]

async def _talk_mentor(session, region):
    if session.character is None: return False
    config = {
        "troll": (TROLL_CAMP_KEY, TROLL_QUEST_KEY, "talk_speaker", "reach_splitroot", "Varka plants the staff between both camps. 'Hear both sides. Then go to Splitroot. Something under the forest is making every argument more dangerous.'"),
        "dwarf": (DWARF_HUB_KEY, DWARF_QUEST_KEY, "talk_foreman", "ride_deep", "Nolla taps three ledgers. 'Different crews. Different instruments. Same impossible depth. Go down the line and find what is actually wrong.'"),
        "moon": (MOON_HUB_KEY, MOON_QUEST_KEY, "talk_astronomer", "reach_ward", "Eiren lays out three charts. 'Do not decide which is correct yet. Walk the old road and record what changes with height.'"),
    }[region]
    room, quest_key, old_step, new_step, text = config
    if session.character.current_room != room: return False
    _ensure_quests(session); q = _quest(session, quest_key)
    if q and q["status"] == "active" and q["current_step"] == old_step: session.database.advance_quest(session.character.id, quest_key, new_step)
    await session.send(text + "\r\n"); return True

async def _study_troll(session):
    if session.character is None or session.character.current_room != TROLL_CLUE_KEY: return False
    q = _quest(session, TROLL_QUEST_KEY)
    if not q or q["status"] != "active": return False
    if TROLL_BOSS_FLAG not in _flags(session): await session.send("The Ravager still makes the priest road unsafe.\r\n"); return True
    session.database.advance_quest(session.character.id, TROLL_QUEST_KEY, "choose_future")
    await session.send("The root is healthy around a perfectly empty line it has spent decades growing around. Neither Troll faction explains it. Choose SUPPORT HEARTH or SUPPORT TRAIL.\r\n"); return True

async def _choose_troll(session, hearth):
    if session.character is None or session.character.current_room != TROLL_CLUE_KEY: return False
    q = _quest(session, TROLL_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "choose_future": return False
    session.database.grant_flag(session.character.id, TROLL_HEARTH_FLAG if hearth else TROLL_TRAIL_FLAG); session.database.grant_flag(session.character.id, TROLL_COMPLETE_FLAG)
    session.database.add_item(session.character.id, TROLL_WITNESS_ITEM_KEY, 1); session.database.add_experience(session.character.id, 2200); session.database.complete_quest(session.character.id, TROLL_QUEST_KEY); _refresh(session)
    await session.send(("You back protected migration corridors first." if hearth else "You back a negotiated road bound to hunting protections.") + " The other faction remains real and present. Quest complete: 2200 XP and a Root-Witness Knot.\r\n"); return True

async def _read_dwarf(session):
    if session.character is None or session.character.current_room != DWARF_CLUE_KEY: return False
    q = _quest(session, DWARF_QUEST_KEY)
    if not q or q["status"] != "active": return False
    if DWARF_BOSS_FLAG not in _flags(session): await session.send("Stop the Deep Drill before trusting a precision reading.\r\n"); return True
    session.database.advance_quest(session.character.id, DWARF_QUEST_KEY, "choose_line")
    await session.send("Three independent instruments agree on an impossible direction below zero depth. Choose SEAL DEEP LINE or KEEP DEEP LINE under stricter inspection.\r\n"); return True

async def _choose_dwarf(session, seal):
    if session.character is None or session.character.current_room != DWARF_CLUE_KEY: return False
    q = _quest(session, DWARF_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "choose_line": return False
    session.database.grant_flag(session.character.id, DWARF_SEAL_FLAG if seal else DWARF_OPEN_FLAG); session.database.grant_flag(session.character.id, DWARF_COMPLETE_FLAG)
    session.database.add_item(session.character.id, DWARF_WITNESS_ITEM_KEY, 1); session.database.add_experience(session.character.id, 2700); session.database.complete_quest(session.character.id, DWARF_QUEST_KEY); _refresh(session)
    await session.send(("You recommend sealing the experimental spur for a purpose-built survey." if seal else "You keep the spur open under double inspection and reduced pressure.") + " The alternative remains recorded. Quest complete: 2700 XP and a Zero-Depth Gauge.\r\n"); return True

async def _compare_moon(session):
    if session.character is None or session.character.current_room != MOON_CLUE_KEY: return False
    q = _quest(session, MOON_QUEST_KEY)
    if not q or q["status"] != "active": return False
    if MOON_BOSS_FLAG not in _flags(session): await session.send("The Warden still blocks the final elevation marker.\r\n"); return True
    session.database.advance_quest(session.character.id, MOON_QUEST_KEY, "choose_record")
    await session.send("Aligned by altitude, the missing star becomes a line pointing down through the range. Choose PUBLISH CHART or HOLD CHART for another verification cycle.\r\n"); return True

async def _choose_moon(session, publish):
    if session.character is None or session.character.current_room != MOON_CLUE_KEY: return False
    q = _quest(session, MOON_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "choose_record": return False
    session.database.grant_flag(session.character.id, MOON_PUBLISH_FLAG if publish else MOON_HOLD_FLAG); session.database.grant_flag(session.character.id, MOON_COMPLETE_FLAG)
    session.database.add_item(session.character.id, MOON_WITNESS_ITEM_KEY, 1); session.database.add_experience(session.character.id, 3200); session.database.complete_quest(session.character.id, MOON_QUEST_KEY); _refresh(session)
    await session.send(("You publish the measurements with uncertainty attached." if publish else "You hold the chart for one more verification cycle without hiding the raw measurements.") + " Eiren records the counterview. Quest complete: 3200 XP and a Counterstar Plate.\r\n"); return True

async def _align_witnesses(session):
    if session.character is None or session.character.current_room != MERIDIAN_WITNESS_KEY: return False
    if not set(FINAL_REQUIRED_FLAGS).issubset(_flags(session)): await session.send("Three recesses wait; you do not yet have all three completed witness threads.\r\n"); return True
    q = _quest(session, MERIDIAN_QUEST_KEY)
    if q is None: session.database.start_quest(session.character.id, MERIDIAN_QUEST_KEY, "align_witnesses")
    session.database.advance_quest(session.character.id, MERIDIAN_QUEST_KEY, "descend"); session.database.grant_flag(session.character.id, MERIDIAN_ALIGNED_FLAG)
    await session.send("Root knot, gauge, and counterstar plate settle into unrelated recesses with impossible precision. The featureless outer lock opens east.\r\n"); return True

async def _read_core(session):
    if session.character is None or session.character.current_room != MERIDIAN_BOSS_KEY: return False
    if MERIDIAN_BOSS_FLAG not in _flags(session): await session.send("The Nameless Custodian still stands between you and the core.\r\n"); return True
    q = _quest(session, MERIDIAN_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "read_core":
        session.database.complete_quest(session.character.id, MERIDIAN_QUEST_KEY); session.database.grant_flag(session.character.id, MERIDIAN_COMPLETE_FLAG)
        if session.database.item_quantity(session.character.id, MERIDIAN_TROPHY_KEY) <= 0: session.database.add_item(session.character.id, MERIDIAN_TROPHY_KEY, 1)
        session.database.add_experience(session.character.id, 6500); _refresh(session)
        await session.send("The core offers no creator, prophecy, or convenient villain. All three regional phenomena are side effects of one structure older than their histories. Quest complete: 6500 XP and a Nameless Meridian Shard.\r\n"); return True
    if MERIDIAN_COMPLETE_FLAG in _flags(session): await session.send("You already recorded everything here that can actually be measured.\r\n"); return True
    return False

async def _claim_twentieth(session):
    if session.character is None or session.character.current_room != MERIDIAN_DAIS_KEY: return False
    _ensure_quests(session)
    if session.character.level < 20: await session.send("Your class milestone arrives at level 20. Return when you reach it.\r\n"); return True
    if MERIDIAN_COMPLETE_FLAG not in _flags(session): await session.send("Clear the Meridian Vault and read its core first.\r\n"); return True
    if TWENTIETH_COMPLETE_FLAG in _flags(session): await session.send("Your twentieth-step milestone is already recorded. Type CLASS to review it.\r\n"); return True
    if _quest(session, TWENTIETH_QUEST_KEY) is None: session.database.start_quest(session.character.id, TWENTIETH_QUEST_KEY, "claim_milestone")
    session.database.complete_quest(session.character.id, TWENTIETH_QUEST_KEY); session.database.grant_flag(session.character.id, TWENTIETH_COMPLETE_FLAG); session.database.add_item(session.character.id, TWENTIETH_SEAL_KEY, 1); session.database.add_experience(session.character.id, 2000); _refresh(session)
    ability = LEVEL_20_ABILITIES.get(session.character.character_class or ""); name = ability.name if ability else "your level-20 class tool"
    await session.send(f"The three-road seal is stamped beside your name. The Twentieth Step complete: 2000 XP and a Three Roads Seal. Your class milestone is {name}.\r\n"); return True

def _resolve_ability(session, text):
    if session.character is None: return None
    normalized = " ".join(text.strip().lower().replace("_", " ").split())
    for ability in mechanics.class_abilities_for_level(session.character.character_class or "", session.character.level, session.character.deity_key):
        if normalized in {ability.key.replace("_", " "), ability.name.lower()}: return ability
    return None

async def _spend(session, ability):
    if not session.combatant.ability_ready(ability.key): await session.send(f"{ability.name} is still on cooldown.\r\n"); return False
    cost = ability.mana_cost or 0
    if not session.combatant.spend_mana(cost): await session.send(f"You need {cost} mana for {ability.name}.\r\n"); return False
    return True

async def _finish_ability(session, ability):
    session.database.record_ability_use(session.character.id, ability.key); session.combatant.start_cooldown(ability.key, ability.cooldown_seconds or 0.0); await session.send_client_state()

def _party_here(session):
    finder = getattr(session, "party_sessions_here", None)
    if callable(finder):
        found = finder()
        if found: return [member for member in found if getattr(member, "combatant", None) is not None and member.combatant.current_hp > 0]
    return [session]

async def _use_level20(session, ability):
    if ability.key == "raise_grave_knight":
        if not await _spend(session, ability): return True
        ok = session.database.summon_pet_with_catalyst(session.character.id, pet_key="grave_knight", catalyst_item_key="bone_chips", catalyst_quantity=4)
        if not ok: session.combatant.current_mana += ability.mana_cost or 0; await session.send("Raise Grave Knight requires 4 Bone Chips.\r\n"); return True
        await session.send("Four bone fragments lock into a larger frame. A persistent Grave Knight rises and waits for command.\r\n"); await _finish_ability(session, ability); return True
    if ability.key == "starbreaker" and session.active_enemy is None: await session.send("You need an active enemy target for Starbreaker.\r\n"); return True
    if not await _spend(session, ability): return True
    if ability.key == "unbroken_stance":
        session.ward_until = asyncio.get_running_loop().time() + 12.0
        if session.active_enemy is not None:
            top = max(session.active_enemy.hate.threat.values(), default=0.0); session.active_enemy.hate.threat[session.character.id] = top + 25.0
        heal = max(1, session.combatant.max_hp // 5); before = session.combatant.current_hp; session.combatant.current_hp = min(session.combatant.max_hp, before + heal)
        await session.send(f"You become the line that does not move. You recover {session.combatant.current_hp - before} HP and ward incoming damage for twelve seconds.\r\n")
    elif ability.key == "starbreaker":
        enemy = session.active_enemy; dealt = enemy.take_damage(session.combatant.spell_damage(30)); enemy.hate.add_threat(session.character.id, float(max(1, dealt))); await session.send(f"Starbreaker cuts through {enemy.definition.name} for {dealt} damage.\r\n")
        if not enemy.alive: await session._finish_enemy_defeat(enemy)
    elif ability.key in {"deep_roots", "last_light"}:
        members = _party_here(session); base = 12 if ability.key == "deep_roots" else 16; duration = 8.0 if ability.key == "deep_roots" else 10.0; until = asyncio.get_running_loop().time() + duration; total = 0
        for member in members:
            heal = session.combatant.healing_amount(base); before = member.combatant.current_hp; member.combatant.current_hp = min(member.combatant.max_hp, before + heal); total += member.combatant.current_hp - before; member.ward_until = max(getattr(member, "ward_until", 0.0), until); await member.send_client_state()
            if member is not session: await member.send(f"{session.character.name}'s {ability.name} restores {member.combatant.current_hp - before} HP and wards you.\r\n")
        await session.send(f"{ability.name} reaches {len(members)} party member(s), restoring {total} total HP and leaving a {int(duration)}-second ward.\r\n")
    await _finish_ability(session, ability); return True

async def _grave_knight_command(session):
    if session.character is None or session.character.character_class != "necromancer" or session.character.level < 7 or session.database.get_active_pet(session.character.id) != "grave_knight": return False
    if session.active_enemy is None: await session.send("You need an active enemy target for Grave Command.\r\n"); return True
    ability = next((item for item in mechanics.class_abilities_for_level("necromancer", session.character.level) if item.key == "grave_command"), None)
    if ability is None or not await _spend(session, ability): return True
    enemy = session.active_enemy; dealt = enemy.take_damage(session.combatant.spell_damage(14)); enemy.hate.add_threat(session.character.id, max(1.0, dealt * .75)); await session.send(f"Your Grave Knight drives a two-handed bone strike into {enemy.definition.name} for {dealt} damage.\r\n")
    if not enemy.alive: await session._finish_enemy_defeat(enemy)
    await _finish_ability(session, ability); return True

async def _delegate(self, previous_prompt, command):
    had = "prompt" in self.__dict__; old = self.__dict__.get("prompt")
    async def replay(_text): return command
    self.prompt = replay
    try: await previous_prompt(self)
    finally:
        if had: self.prompt = old
        else: self.__dict__.pop("prompt", None)

def install_midgame_12_20_runtime(player_session_class, world_service):
    if getattr(player_session_class, "_midgame_12_20_runtime_installed", False): return
    install_midgame_12_20_content(world_service)
    previous_enter = player_session_class.enter_character; previous_move = player_session_class.move_character; previous_prompt = player_session_class.playing_prompt; previous_lookup = player_session_class._enemy_in_current_room; previous_finish = player_session_class._finish_enemy_defeat; previous_use = player_session_class.use_ability
    async def enter_character(self): await previous_enter(self); _ensure_quests(self)
    async def move_character(self, direction):
        before = self.character.current_room if self.character is not None else None; await previous_move(self, direction); _ensure_quests(self)
        if self.character is None or self.character.current_room == before: return
        room = self.character.current_room
        transitions = ((TROLL_BOSS_KEY, TROLL_QUEST_KEY, "reach_splitroot", "defeat_ravager", "Splitroot Hollow is torn open around the black root seam. Deal with the Ravager."), ("deepwheel_deepwheel_station", DWARF_QUEST_KEY, "ride_deep", "defeat_drill", "The abandoned spur shudders. The runaway drill is east."), (MOON_BOSS_KEY, MOON_QUEST_KEY, "reach_ward", "defeat_warden", "The Skyglass Warden wakes. The final comparison plates lie beyond it."), (MERIDIAN_CAMP_KEY, MERIDIAN_QUEST_KEY, "enter_vault", "align_witnesses", "All three lines of evidence end here. Take them east to Three-Witness Hall."))
        for target, quest_key, old_step, new_step, text in transitions:
            if room == target:
                q = _quest(self, quest_key)
                if q and q["status"] == "active" and q["current_step"] == old_step: self.database.advance_quest(self.character.id, quest_key, new_step); await self.send(text + "\r\n")
        if room == MERIDIAN_DAIS_KEY: _ensure_quests(self)
    def enemy_in_room(self, target_text):
        if self.character is not None:
            room = self.character.current_room; flags = _flags(self)
            if room == TROLL_BOSS_KEY and TROLL_BOSS_FLAG not in flags and TROLL_RAVAGER.matches(target_text): return EnemyState(TROLL_RAVAGER)
            if room == DWARF_BOSS_KEY and DWARF_BOSS_FLAG not in flags and DWARF_DRILL.matches(target_text): return EnemyState(DWARF_DRILL)
            if room == MOON_BOSS_KEY and MOON_BOSS_FLAG not in flags and MOON_WARDEN.matches(target_text): return EnemyState(MOON_WARDEN)
            if room == MERIDIAN_BOSS_KEY and MERIDIAN_BOSS_FLAG not in flags and MERIDIAN_CUSTODIAN.matches(target_text): return EnemyState(MERIDIAN_CUSTODIAN)
        return previous_lookup(self, target_text)
    async def finish_enemy(self, enemy):
        key = enemy.definition.key; participants = _victory_sessions(self, enemy); was_active = self.active_enemy is enemy; await previous_finish(self, enemy)
        if not was_active: return
        updates = {TROLL_RAVAGER_KEY: (TROLL_BOSS_FLAG, TROLL_QUEST_KEY, "defeat_ravager", "study_meridian", "The Ravager falls. Follow the black-root evidence toward the priest grove."), DWARF_DRILL_KEY: (DWARF_BOSS_FLAG, DWARF_QUEST_KEY, "defeat_drill", "read_instruments", "The drill winds down. The zero-depth instruments can be read cleanly."), MOON_WARDEN_KEY: (MOON_BOSS_FLAG, MOON_QUEST_KEY, "defeat_warden", "compare_charts", "The Warden folds into silence. Chart Court now has the final viewpoint."), MERIDIAN_CUSTODIAN_KEY: (MERIDIAN_BOSS_FLAG, MERIDIAN_QUEST_KEY, "defeat_custodian", "read_core", "The Nameless Custodian collapses. READ CORE before leaving.")}
        update = updates.get(key)
        if update is None: return
        flag, quest_key, old_step, new_step, message = update
        for member in participants:
            if getattr(member, "character", None) is None: continue
            _grant_once(member, flag); q = _quest(member, quest_key)
            if q and q["status"] == "active" and q["current_step"] == old_step: member.database.advance_quest(member.character.id, quest_key, new_step)
            if member is not self: await member.send("[Party Progress] " + message + "\r\n")
        await self.send(message + "\r\n")
    async def use_ability(self, ability_text):
        normalized = " ".join(ability_text.strip().lower().replace("_", " ").split())
        if normalized == "grave command" and await _grave_knight_command(self): return
        ability = _resolve_ability(self, ability_text)
        if ability is not None and ability.key in LEVEL_20_ABILITY_KEYS: await _use_level20(self, ability); return
        await previous_use(self, ability_text)
    async def playing_prompt(self):
        if self.character is None: await previous_prompt(self); return
        command = await self.prompt("\r\n> ")
        if command is None: self.state = type(self.state).DISCONNECTED; return
        stripped = command.strip(); normalized = " ".join(stripped.lower().split()); handled = False
        if normalized in {"talk varka", "talk speaker", "talk mossback"}: handled = await _talk_mentor(self, "troll")
        elif normalized in {"study roots", "study root", "examine meridian root"}: handled = await _study_troll(self)
        elif normalized in {"support hearth", "support hearthbound"}: handled = await _choose_troll(self, True)
        elif normalized in {"support trail", "support longtrail"}: handled = await _choose_troll(self, False)
        elif normalized in {"talk nolla", "talk foreman", "talk gaugehand"}: handled = await _talk_mentor(self, "dwarf")
        elif normalized in {"read gauges", "read instruments", "inspect gauges"}: handled = await _read_dwarf(self)
        elif normalized in {"seal deep line", "close deep line"}: handled = await _choose_dwarf(self, True)
        elif normalized in {"keep deep line", "keep line open"}: handled = await _choose_dwarf(self, False)
        elif normalized in {"talk eiren", "talk astronomer", "talk vael"}: handled = await _talk_mentor(self, "moon")
        elif normalized in {"compare charts", "compare plates", "align charts"}: handled = await _compare_moon(self)
        elif normalized in {"publish chart", "publish charts"}: handled = await _choose_moon(self, True)
        elif normalized in {"hold chart", "hold charts"}: handled = await _choose_moon(self, False)
        elif normalized in {"align witnesses", "align witness", "place witnesses"}: handled = await _align_witnesses(self)
        elif normalized in {"read core", "study core", "examine core"}: handled = await _read_core(self)
        elif normalized in {"claim twentieth step", "claim milestone", "twentieth step"}: handled = await _claim_twentieth(self)
        elif normalized in {"three roads", "midgame roads", "roads 12 20"}:
            await self.send("THREE ROADS (12-20)\r\n - North from Veyra Waterworks: Thornwake Troll country, 12-16.\r\n - East from Veyra River Gate: Deepwheel Dwarven corridor, 12-18.\r\n - Up from Scholar's Rise: Counterstar highroad, 13-18.\r\n - Complete all three to reveal the level 19-20 Meridian Vault.\r\n - Level 20 unlocks a major class ability and the Twentieth Step.\r\n"); return
        if handled: return
        ability = _resolve_ability(self, stripped)
        if ability is not None and ability.key in LEVEL_20_ABILITY_KEYS and normalized in {ability.name.lower(), ability.key.replace("_", " ")}: await self.use_ability(stripped); return
        if normalized == "grave command" and self.database.get_active_pet(self.character.id) == "grave_knight": await self.use_ability("grave command"); return
        await _delegate(self, previous_prompt, command)
    player_session_class.enter_character = enter_character; player_session_class.move_character = move_character; player_session_class.playing_prompt = playing_prompt; player_session_class._enemy_in_current_room = enemy_in_room; player_session_class._finish_enemy_defeat = finish_enemy; player_session_class.use_ability = use_ability; player_session_class._midgame_12_20_runtime_installed = True
