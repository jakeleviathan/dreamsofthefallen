from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, RoomAugmentation, ViewCondition
from mud.salt_kingdoms_midgame import CAPSTONE_COMPLETE_FLAG as SALT_CAPSTONE_COMPLETE_FLAG, SALTWIND_GATE_KEY
from mud.world import NpcDefinition, RoomDefinition


# Crownfire deliberately changes the storytelling grammar established by Broken
# Reach and Whitewake. The central danger is not an ancient system doing a job
# nobody understands. It is a living political-military project whose leader
# knows exactly what his orders do and issues them anyway.
CROWNFIRE_REGION_KEY = "crownfire_march"
MORROWGATE_REGION_KEY = "morrowgate"
REDOUBT_REGION_KEY = "gilded_redoubt"
PALACE_REGION_KEY = "banner_palace"

MARCHWARD_POST_KEY = "crownfire_marchward_post"
ASH_ORCHARD_KEY = "crownfire_ash_orchard"
BURNED_TOLL_KEY = "crownfire_burned_toll"
RED_WHEAT_KEY = "crownfire_red_wheat_fields"
REFUGEE_FORD_KEY = "crownfire_refugee_ford"
GALLOWS_MILE_KEY = "crownfire_gallows_mile"
CHALK_RIDGE_KEY = "crownfire_chalk_ridge"
BLACK_KILN_KEY = "crownfire_black_kiln"
WINDMILL_SCAR_KEY = "crownfire_windmill_scar"
MORROWGATE_APPROACH_KEY = "crownfire_morrowgate_approach"

MORROWGATE_GATE_KEY = "morrowgate_south_gate"
MORROWGATE_MARKET_KEY = "morrowgate_canvas_market"
MORROWGATE_GRANARY_KEY = "morrowgate_granary_court"
MORROWGATE_COUNCIL_KEY = "morrowgate_council_hall"
MORROWGATE_HEALERS_KEY = "morrowgate_healers_row"
MORROWGATE_RAMPART_KEY = "morrowgate_east_rampart"

REDOUBT_GATE_KEY = "gilded_redoubt_gate"
REDOUBT_YARD_KEY = "gilded_redoubt_parade_yard"
REDOUBT_SUPPLY_KEY = "gilded_redoubt_supply_hall"
REDOUBT_SIGNAL_KEY = "gilded_redoubt_signal_loft"
REDOUBT_PRISON_KEY = "gilded_redoubt_prison_cage"
REDOUBT_OFFICE_KEY = "gilded_redoubt_quartermaster_office"

PALACE_APPROACH_KEY = "banner_palace_approach"
PALACE_OFFICERS_KEY = "banner_palace_officers_mess"
PALACE_TROPHIES_KEY = "banner_palace_trophy_gallery"
PALACE_MAP_KEY = "banner_palace_map_room"
PALACE_HOSTAGES_KEY = "banner_palace_hostage_wing"
PALACE_SIGNAL_KEY = "banner_palace_signal_stair"
PALACE_COMMAND_KEY = "banner_palace_command_hall"
PALACE_TREATY_KEY = "banner_palace_treaty_chamber"

TRIBUNAL_YARD_KEY = "crownfire_public_tribunal_yard"
DESERTER_ROAD_KEY = "crownfire_open_deserter_road"
DISARMED_ROAD_KEY = "crownfire_disarmed_host_road"

SURFACE_ROOM_KEYS = (
    MARCHWARD_POST_KEY, ASH_ORCHARD_KEY, BURNED_TOLL_KEY, RED_WHEAT_KEY, REFUGEE_FORD_KEY,
    GALLOWS_MILE_KEY, CHALK_RIDGE_KEY, BLACK_KILN_KEY, WINDMILL_SCAR_KEY, MORROWGATE_APPROACH_KEY,
)
CITY_ROOM_KEYS = (
    MORROWGATE_GATE_KEY, MORROWGATE_MARKET_KEY, MORROWGATE_GRANARY_KEY,
    MORROWGATE_COUNCIL_KEY, MORROWGATE_HEALERS_KEY, MORROWGATE_RAMPART_KEY,
)
REDOUBT_ROOM_KEYS = (
    REDOUBT_GATE_KEY, REDOUBT_YARD_KEY, REDOUBT_SUPPLY_KEY,
    REDOUBT_SIGNAL_KEY, REDOUBT_PRISON_KEY, REDOUBT_OFFICE_KEY,
)
PALACE_ROOM_KEYS = (
    PALACE_APPROACH_KEY, PALACE_OFFICERS_KEY, PALACE_TROPHIES_KEY, PALACE_MAP_KEY,
    PALACE_HOSTAGES_KEY, PALACE_SIGNAL_KEY, PALACE_COMMAND_KEY, PALACE_TREATY_KEY,
)
POSTCAP_ROOM_KEYS = (TRIBUNAL_YARD_KEY, DESERTER_ROAD_KEY, DISARMED_ROAD_KEY)
CROWNFIRE_ROOM_KEYS = (*SURFACE_ROOM_KEYS, *CITY_ROOM_KEYS, *REDOUBT_ROOM_KEYS, *PALACE_ROOM_KEYS, *POSTCAP_ROOM_KEYS)

ARRIVAL_QUEST_KEY = "crownfire_smoke_has_orders"
BLOCKADE_QUEST_KEY = "crownfire_city_under_contract"
REDOUBT_QUEST_KEY = "crownfire_break_brass_redoubt"
DESERTER_QUEST_KEY = "crownfire_price_of_desertion"
PALACE_QUEST_KEY = "crownfire_banner_palace"
CAPSTONE_QUEST_KEY = "crownfire_no_misunderstanding"

ARRIVAL_COMPLETE_FLAG = "crownfire_false_flag_orders_proven"
BLOCKADE_COMPLETE_FLAG = "crownfire_collaborator_exposed"
REDOUBT_COMPLETE_FLAG = "crownfire_redoubt_broken"
DESERTER_COMPLETE_FLAG = "crownfire_deserter_question_settled"
DESERTER_SHELTER_FLAG = "crownfire_deserters_sheltered"
DESERTER_TESTIMONY_FLAG = "crownfire_deserters_testify"
PALACE_COMPLETE_FLAG = "crownfire_banner_network_broken"
DASK_DEFEATED_FLAG = "crownfire_dask_defeated"
CAPSTONE_COMPLETE_FLAG = "crownfire_level_40_complete"
TRIAL_ENDING_FLAG = "crownfire_dask_public_trial"
EXILE_ENDING_FLAG = "crownfire_dask_exiled"
JUDGMENT_ENDING_FLAG = "crownfire_dask_field_judgment"

SCOUT_ORDERS_KEY = "crownfire_scout_orders"
BLACK_CONTRACT_KEY = "crownfire_black_contract"
REDOUBT_BRASS_KEY = "crownfire_redoubt_brass"
DESERTER_RIBBON_KEY = "crownfire_deserter_ribbon"
BLACK_LEDGER_KEY = "crownfire_black_ledger"
FREE_MARCH_CHARTER_KEY = "crownfire_free_march_charter"
DASK_SIGNET_KEY = "crownfire_dask_signet"

ARRIVAL_QUEST = QuestDefinition(
    ARRIVAL_QUEST_KEY,
    "The Smoke Has Orders",
    "structured",
    31,
    (
        "Farmsteads are burning north of Whitewake, but the raids are too disciplined to be random. "
        "Survivors report different banners on different nights, as though somebody wants the violence to look fragmented."
    ),
    (
        ("talk_mara", "At Marchward Post, TALK EVARA."),
        ("inspect_wagon", "At Burned Toll, EXAMINE WAGON."),
        ("defeat_scout", "Find and defeat the Gilded Scout-Captain on Gallows Mile."),
        ("read_orders", "READ ORDERS recovered from the scout-captain."),
        ("return_mara", "Return to Evara at Marchward Post."),
        ("complete", "You proved the raids were intentionally staged under false banners by the Gilded Host."),
    ),
)

BLOCKADE_QUEST = QuestDefinition(
    BLOCKADE_QUEST_KEY,
    "A City Under Contract",
    "structured",
    33,
    (
        "Morrowgate is not conquered, but its food, medicine, and road access are being squeezed by contracts written under threat. "
        "Someone inside the city is selling the Host exactly enough access to keep the blockade profitable."
    ),
    (
        ("talk_iven", "TALK IVEN in Council Hall."),
        ("talk_della", "TALK DELLA on Healers' Row."),
        ("search_contracts", "SEARCH CONTRACTS in the Canvas Market."),
        ("accuse_varek", "ACCUSE VAREK in the Canvas Market."),
        ("complete", "Broker Varek's signed side-contract proves the blockade is being managed, not merely endured."),
    ),
)

REDOUBT_QUEST = QuestDefinition(
    REDOUBT_QUEST_KEY,
    "Break the Brass Redoubt",
    "structured",
    34,
    (
        "The Gilded Host's forward redoubt coordinates raids, rations, and signal fires. It is a new fort built by living soldiers, "
        "and breaking it means interrupting a working military organization rather than solving a ruin."
    ),
    (
        ("talk_sera", "TALK RENNA on Morrowgate's East Rampart."),
        ("cut_signal", "Enter the Brass Redoubt and CUT SIGNAL ROPE in the Signal Loft."),
        ("free_prisoners", "FREE PRISONERS in the Prison Cage."),
        ("defeat_quartermaster", "Defeat Quartermaster Venn in his office."),
        ("complete", "The Redoubt loses its signal net, prisoners, quartermaster, and reliable supply ledger in one night."),
    ),
)

DESERTER_QUEST = QuestDefinition(
    DESERTER_QUEST_KEY,
    "The Price of Desertion",
    "structured",
    36,
    (
        "Not every soldier in the Gilded Host volunteered. Captain Lysa Orr deserted after seeing Dask's written orders to burn neutral farms. "
        "The question is not whether Dask is guilty; it is whether frightened deserters are safer hidden or useful as public witnesses."
    ),
    (
        ("talk_lysa", "At Refugee Ford, TALK LYSA."),
        ("read_rolls", "READ CONSCRIPTION ROLLS in the captured Redoubt office."),
        ("choose", "At Refugee Ford choose PROTECT DESERTERS or PUBLIC TESTIMONY."),
        ("complete", "You decide how the deserters will survive the coming campaign without pretending their former command was innocent."),
    ),
)

PALACE_QUEST = QuestDefinition(
    PALACE_QUEST_KEY,
    "The Banner Palace",
    "structured",
    37,
    (
        "Marshal Corven Dask's mobile headquarters has unfolded north of the Redoubt: an active field palace of canvas, timber, signal mirrors, "
        "hostage rooms, clerks, officers, and written plans for the next manufactured crisis."
    ),
    (
        ("talk_sera", "Return to Captain Renna Hald on the East Rampart."),
        ("break_mirror", "BREAK SIGNAL MIRROR in the Banner Palace signal stair."),
        ("free_hostages", "FREE HOSTAGES in the Hostage Wing."),
        ("read_map", "READ WAR MAP in the Map Room."),
        ("defeat_captain", "Defeat Banner-Captain Hadrik in the Command Hall."),
        ("take_ledger", "TAKE BLACK LEDGER from the Command Hall."),
        ("complete", "The Palace can no longer coordinate the March, and Dask's own ledger proves the crises were deliberate policy."),
    ),
)

CAPSTONE_QUEST = QuestDefinition(
    CAPSTONE_QUEST_KEY,
    "No Misunderstanding",
    "structured",
    40,
    (
        "Corven Dask retreats into the Treaty Chamber with the remaining officers and tries to convert a military defeat into a coerced settlement. "
        "There is no hidden machine to reinterpret and no innocent guardian behind him: the orders are his, the signatures are his, and he knows what they did."
    ),
    (
        ("confront_dask", "Enter the Treaty Chamber and defeat Marshal Corven Dask."),
        ("choose_aftermath", "Choose DEMAND TRIAL, ORDER EXILE, or FIELD JUDGMENT."),
        ("complete", "The Gilded Host ceases to function as Dask's private state, and the chosen aftermath permanently changes one route through Crownfire."),
    ),
)

CROWNFIRE_QUESTS = (ARRIVAL_QUEST, BLOCKADE_QUEST, REDOUBT_QUEST, DESERTER_QUEST, PALACE_QUEST, CAPSTONE_QUEST)

CROWNFIRE_ITEMS = (
    ItemDefinition(SCOUT_ORDERS_KEY, "False-Banner Orders", "A signed field order assigning three different stolen banners to three raids and instructing survivors to be left alive to spread contradictory stories.", "quest", tier=7),
    ItemDefinition(BLACK_CONTRACT_KEY, "Black Contract", "Broker Varek's private contract granting the Gilded Host warehouse access in exchange for exemptions from the blockade he publicly condemns.", "quest", tier=7),
    ItemDefinition(REDOUBT_BRASS_KEY, "Redoubt Brass", "A heavy brass signal plate cut from the forward fort after its communications were disabled.", "trophy", tier=8),
    ItemDefinition(DESERTER_RIBBON_KEY, "Unbound Gold Ribbon", "A Gilded Host shoulder ribbon with its oath-knot cut open rather than untied.", "credential", tier=8),
    ItemDefinition(BLACK_LEDGER_KEY, "Dask's Black Ledger", "A campaign ledger in Corven Dask's hand. Columns pair staged crises with projected recruitment, toll, and protection revenue.", "quest", tier=9),
    ItemDefinition(FREE_MARCH_CHARTER_KEY, "Free March Charter", "A witnessed charter recording the end of the Gilded Host's private toll-state and the terms chosen for Dask's aftermath.", "credential", tier=10),
    ItemDefinition(DASK_SIGNET_KEY, "Dask's Broken Signet", "A gold command signet split through the crown-and-road device. It is valuable mostly because nobody can use it to issue another order.", "trophy", tier=10),
)


def _enemy(key: str, name: str, aliases: tuple[str, ...], description: str, hp: int, ac: int, damage: int, interval: float, xp: int) -> EnemyDefinition:
    return EnemyDefinition(key, name, aliases, description, hp, ac, damage, interval, xp, True, False)


HOST_OUTRIDER_KEY = "crownfire_host_outrider"
HOST_LEVY_KEY = "crownfire_host_levy"
HOST_ARSONIST_KEY = "crownfire_host_arsonist"
HOST_MARKSMAN_KEY = "crownfire_host_marksman"
SCOUT_CAPTAIN_KEY = "crownfire_scout_captain"
QUARTERMASTER_VENN_KEY = "crownfire_quartermaster_venn"
BANNER_CAPTAIN_KEY = "crownfire_banner_captain_hadrik"
WAR_HOUND_KEY = "crownfire_war_hound"
MARSHAL_DASK_KEY = "crownfire_marshal_corven_dask"

CROWNFIRE_ENEMIES = (
    _enemy(HOST_OUTRIDER_KEY, "Gilded Outrider", ("outrider", "gilded outrider"), "a mounted Host scout wearing a gold road-ribbon over practical campaign leathers", 820, 25, 48, 2.6, 900),
    _enemy(HOST_LEVY_KEY, "Pressed Levy", ("levy", "soldier", "pressed levy"), "a frightened infantry soldier with a Host badge sewn over an older local militia patch", 760, 24, 43, 2.8, 820),
    _enemy(HOST_ARSONIST_KEY, "Host Arsonist", ("arsonist", "fire-setter"), "a specialist carrying sealed oil flasks and a bundle of stolen faction pennants", 880, 25, 51, 2.7, 980),
    _enemy(HOST_MARKSMAN_KEY, "Gilded Marksman", ("marksman", "archer"), "a disciplined bowman posted where the Host wants roads to feel watched", 930, 26, 54, 3.0, 1050),
    _enemy(SCOUT_CAPTAIN_KEY, "Gilded Scout-Captain", ("captain", "scout captain"), "a field officer carrying three different stolen banners and one packet of sealed orders", 1450, 28, 60, 2.7, 2600),
    _enemy(QUARTERMASTER_VENN_KEY, "Quartermaster Venn", ("venn", "quartermaster"), "a hard-eyed logistics officer who can quote the cost of a burned farm in lamp oil, horse feed, and recruitment yield", 2600, 31, 66, 2.8, 5200),
    _enemy(BANNER_CAPTAIN_KEY, "Banner-Captain Hadrik", ("hadrik", "banner captain"), "Dask's senior field enforcer, wearing six campaign ribbons and no stolen colors", 3100, 33, 72, 2.7, 6500),
    _enemy(WAR_HOUND_KEY, "Gilded War Hound", ("hound", "war hound"), "a massive trained mastiff in a brass-edged harness, bred for camps and prisoner lines rather than monsters", 1200, 27, 58, 2.5, 1300),
    _enemy(MARSHAL_DASK_KEY, "Marshal Corven Dask", ("dask", "marshal", "corven"), "a living Human commander in polished field plate, carrying the same gold signet that appears beneath the orders in the Black Ledger", 5200, 36, 82, 2.6, 12000),
)

MARA_KEY = "crownfire_mara_quill"
IVEN_KEY = "morrowgate_mayor_iven_rook"
DELLA_KEY = "morrowgate_healer_della_sorn"
SERA_KEY = "morrowgate_captain_sera_hald"
LYSA_KEY = "crownfire_deserter_lysa_orr"
VAREK_KEY = "morrowgate_broker_varek_tess"

CROWNFIRE_NPCS = (
    NpcDefinition(MARA_KEY, "Evara Quill", "a soot-streaked road clerk whose coat still bears the burned outline of a tollhouse badge", MARCHWARD_POST_KEY, "refugee road clerk", dialogue=("'The banners change. The boot nails do not.'", "'Somebody wants us arguing about who attacked us instead of asking who benefits.'")),
    NpcDefinition(IVEN_KEY, "Mayor Iven Rook", "a tired civic mayor wearing the same plain black coat for hearings, ration lines, and wall inspections", MORROWGATE_COUNCIL_KEY, "elected mayor of Morrowgate", dialogue=("'I can survive being unpopular. I cannot survive not knowing which warehouse opens after midnight.'", "'A blockade is just a siege with paperwork if the paperwork still ends in hunger.'")),
    NpcDefinition(DELLA_KEY, "Healer Della Sorn", "an Undead field healer with clean bone hands and an apron marked in charcoal with medicine shortages", MORROWGATE_HEALERS_KEY, "public healer", dialogue=("'The Host calls this pressure. Infection also calls itself pressure if you ask it politely.'", "'Medicine is disappearing in exactly the quantities that keep us sick without letting us die quickly.'")),
    NpcDefinition(SERA_KEY, "Captain Renna Hald", "a Forest Elf militia captain with one gold Host arrow pinned backward through her cloak as a reminder", MORROWGATE_RAMPART_KEY, "Morrowgate defense captain", dialogue=("'Dask is not a storm. Stop talking about him like weather.'", "'If somebody orders a fire, writes the invoice, and recruits from the survivors, the pattern is not mysterious.'")),
    NpcDefinition(LYSA_KEY, "Captain Lysa Orr", "a former Gilded Host captain who has cut every gold braid off her uniform except the one needed to prove what rank she held", REFUGEE_FORD_KEY, "Gilded Host deserter and witness", dialogue=("'I signed ration orders. I did not sign the farm burns. I stayed too long after I learned the difference.'", "'Do not forgive us because some of us deserted. Decide what our testimony is worth, then keep deciding what our actions cost.'")),
    NpcDefinition(VAREK_KEY, "Broker Varek Tess", "a smiling freight broker whose rings are expensive enough to look defensive during a blockade", MORROWGATE_MARKET_KEY, "warehouse broker", dialogue=("'Trade survives by compromise.'", "'People who call every private arrangement treason usually do not own warehouses.'")),
)


def _room(key: str, name: str, region: str, description: str, exits: dict[str, str], *, npcs=(), enemies=(), tags=()) -> RoomDefinition:
    return RoomDefinition(key, name, region, description, exits, tuple(npcs), tuple(enemies), ("shared_world", "crownfire", *tuple(tags)))


CROWNFIRE_ROOMS = (
    _room(MARCHWARD_POST_KEY, "Marchward Post", CROWNFIRE_REGION_KEY, "North of Whitewake the salt glare gives way to red soil and smoke. A road post has become a refugee desk, message wall, and bucket line. Three different faction banners hang from one peg, all recovered from raids survivors swear were carried out by the same boots.", {"south": SALTWIND_GATE_KEY, "north": ASH_ORCHARD_KEY}, npcs=(MARA_KEY,), tags=("level_31_32", "entry", "safe")),
    _room(ASH_ORCHARD_KEY, "Ash Orchard", CROWNFIRE_REGION_KEY, "Half an apple orchard has burned in a clean military crescent. The untouched half is tagged with Gilded Host protection seals offering paid security against 'further instability.'", {"south": MARCHWARD_POST_KEY, "north": BURNED_TOLL_KEY, "east": RED_WHEAT_KEY}, enemies=(HOST_OUTRIDER_KEY,), tags=("level_31_33", "road")),
    _room(BURNED_TOLL_KEY, "Burned Toll", CROWNFIRE_REGION_KEY, "A toll shelter and two wagons burned here. The wagons were emptied of people before they were fired, and one axle bears a neat chalk notation marking how long the smoke column should remain visible from Morrowgate.", {"south": ASH_ORCHARD_KEY, "north": REFUGEE_FORD_KEY}, enemies=(HOST_ARSONIST_KEY,), tags=("level_31_33", "evidence")),
    _room(RED_WHEAT_KEY, "Red Wheat Fields", CROWNFIRE_REGION_KEY, "Late wheat moves in red-dust wind around three farms whose owners paid for Host protection. Their fences are intact. The neighboring farm that refused is a black rectangle.", {"west": ASH_ORCHARD_KEY, "north": CHALK_RIDGE_KEY}, enemies=(HOST_OUTRIDER_KEY,), tags=("level_32_34", "farmland")),
    _room(REFUGEE_FORD_KEY, "Refugee Ford", CROWNFIRE_REGION_KEY, "Canvas shelters line a shallow ford where displaced families wash smoke from cooking pots. Former Host soldiers keep to one bank, visibly unarmed. Lysa Orr has chosen the most public patch of mud to make hiding impossible.", {"south": BURNED_TOLL_KEY, "north": GALLOWS_MILE_KEY, "east": BLACK_KILN_KEY}, npcs=(LYSA_KEY,), tags=("level_32_36", "safe", "refugee")),
    _room(GALLOWS_MILE_KEY, "Gallows Mile", CROWNFIRE_REGION_KEY, "The old execution road is lined with empty gallows the Host now uses as signal frames. Stolen banners flap from crossbeams so distant observers report a different enemy depending on which way the wind turns.", {"south": REFUGEE_FORD_KEY, "north": MORROWGATE_APPROACH_KEY, "east": REDOUBT_GATE_KEY}, enemies=(SCOUT_CAPTAIN_KEY, HOST_MARKSMAN_KEY), tags=("level_32_35", "host_control")),
    _room(CHALK_RIDGE_KEY, "Chalk Ridge", CROWNFIRE_REGION_KEY, "White chalk cliffs interrupt the red country. Fresh wheel ruts vanish into a quarry cut where Host wagons have been hauling stone for fortifications built this season, not centuries ago.", {"south": RED_WHEAT_KEY, "west": WINDMILL_SCAR_KEY}, enemies=(HOST_LEVY_KEY,), tags=("level_33_35", "flank")),
    _room(BLACK_KILN_KEY, "Black Kiln", CROWNFIRE_REGION_KEY, "An abandoned tile kiln has become a field kitchen and deserter cache. Names are scratched into the bricks beside dates, proving the flow of people out of Dask's army began before his victories stopped.", {"west": REFUGEE_FORD_KEY}, tags=("level_34_36", "optional", "safe")),
    _room(WINDMILL_SCAR_KEY, "Windmill Scar", CROWNFIRE_REGION_KEY, "A dismantled windmill lies in orderly piles beside a road cut. The Host did not destroy it in anger; its timber became watch platforms and its millstone became a redoubt gate weight.", {"east": CHALK_RIDGE_KEY, "west": MORROWGATE_APPROACH_KEY}, enemies=(HOST_LEVY_KEY,), tags=("level_33_35", "evidence")),
    _room(MORROWGATE_APPROACH_KEY, "Morrowgate Approach", CROWNFIRE_REGION_KEY, "The city wall is visible behind a belt of stripped orchards. Gilded Host range stakes stop exactly outside bowshot, turning the approach into a measured threat rather than a battlefield accident.", {"south": GALLOWS_MILE_KEY, "east": WINDMILL_SCAR_KEY, "north": MORROWGATE_GATE_KEY}, enemies=(HOST_MARKSMAN_KEY,), tags=("level_33_36", "city_approach")),

    _room(MORROWGATE_GATE_KEY, "Morrowgate South Gate", MORROWGATE_REGION_KEY, "Morrowgate's gate remains open by civic vote even under blockade. Every wagon is searched twice: once for weapons and once for medicine people may be trying to hoard.", {"south": MORROWGATE_APPROACH_KEY, "north": MORROWGATE_MARKET_KEY}, tags=("level_33_40", "city", "safe")),
    _room(MORROWGATE_MARKET_KEY, "Canvas Market", MORROWGATE_REGION_KEY, "Permanent stalls have been dismantled for firewood, leaving a market of patched awnings and chalk ration prices. Varek Tess still operates three warehouses and smiles as though scarcity were a networking opportunity.", {"south": MORROWGATE_GATE_KEY, "north": MORROWGATE_COUNCIL_KEY, "east": MORROWGATE_GRANARY_KEY}, npcs=(VAREK_KEY,), tags=("level_33_40", "city", "market", "safe")),
    _room(MORROWGATE_GRANARY_KEY, "Granary Court", MORROWGATE_REGION_KEY, "Public grain bins stand under militia guard. The ledger board is updated every four hours so rumors about starvation cannot outrun the actual numbers.", {"west": MORROWGATE_MARKET_KEY, "north": MORROWGATE_HEALERS_KEY}, tags=("level_33_40", "city", "safe")),
    _room(MORROWGATE_COUNCIL_KEY, "Council Hall", MORROWGATE_REGION_KEY, "The council meets in a former dye hall because the old chamber was converted into a clinic. Maps, ration boards, witness statements, and captured Host seals cover the walls. Iven Rook has stopped pretending the crisis is temporary.", {"south": MORROWGATE_MARKET_KEY, "east": MORROWGATE_HEALERS_KEY, "north": MORROWGATE_RAMPART_KEY}, npcs=(IVEN_KEY,), tags=("level_33_40", "city", "hub", "safe")),
    _room(MORROWGATE_HEALERS_KEY, "Healers' Row", MORROWGATE_REGION_KEY, "Three adjoining workshops have become a public infirmary. Della Sorn keeps medicine shortages chalked directly on the doors so no council member can call them abstract.", {"west": MORROWGATE_COUNCIL_KEY, "south": MORROWGATE_GRANARY_KEY}, npcs=(DELLA_KEY,), tags=("level_33_40", "city", "safe")),
    _room(MORROWGATE_RAMPART_KEY, "East Rampart", MORROWGATE_REGION_KEY, "From the wall, the Brass Redoubt's signal loft flashes above the fields and a larger field headquarters glitters farther north. Captain Renna Hald has marked every Host patrol route with plain black charcoal instead of heroic symbols.", {"south": MORROWGATE_COUNCIL_KEY, "east": PALACE_APPROACH_KEY}, npcs=(SERA_KEY,), tags=("level_34_40", "city", "military", "safe")),

    _room(REDOUBT_GATE_KEY, "Brass Redoubt Gate", REDOUBT_REGION_KEY, "The forward fort is new enough that sap still bleeds from some timbers. Brass plates make it look richer than it is; most are signal reflectors and standardized fittings, not decoration.", {"west": GALLOWS_MILE_KEY, "east": REDOUBT_YARD_KEY}, enemies=(HOST_LEVY_KEY, WAR_HOUND_KEY), tags=("dungeon", "level_34_35")),
    _room(REDOUBT_YARD_KEY, "Redoubt Parade Yard", REDOUBT_REGION_KEY, "Training squares, feed troughs, ration lines, and punishment posts all fit inside one brutally efficient rectangle. This is a working fort with tomorrow's assignments already posted.", {"west": REDOUBT_GATE_KEY, "east": REDOUBT_SUPPLY_KEY, "north": REDOUBT_PRISON_KEY}, enemies=(HOST_LEVY_KEY,), tags=("dungeon", "level_34_35")),
    _room(REDOUBT_SUPPLY_KEY, "Redoubt Supply Hall", REDOUBT_REGION_KEY, "Shelves hold oil, grain, spare bowstrings, stolen pennants, and preprinted protection seals. The coexistence of arson oil and protection paperwork is not subtle.", {"west": REDOUBT_YARD_KEY, "up": REDOUBT_SIGNAL_KEY, "east": REDOUBT_OFFICE_KEY}, enemies=(HOST_ARSONIST_KEY,), tags=("dungeon", "level_34_35")),
    _room(REDOUBT_SIGNAL_KEY, "Signal Loft", REDOUBT_REGION_KEY, "Three polished brass shutters can flash orders from ridge to ridge. Thick ropes connect the shutters to labeled sequences: RAID, WITHDRAW, FIRE, ESCORT, COLLECT.", {"down": REDOUBT_SUPPLY_KEY}, enemies=(HOST_MARKSMAN_KEY,), tags=("dungeon", "mechanic", "level_34_35")),
    _room(REDOUBT_PRISON_KEY, "Prison Cage", REDOUBT_REGION_KEY, "A timber cage holds civilians, deserters, and two Host levies arrested for refusing a farm-burning order. Their names are already crossed off tomorrow's ration list.", {"south": REDOUBT_YARD_KEY}, enemies=(WAR_HOUND_KEY,), tags=("dungeon", "level_35")),
    _room(REDOUBT_OFFICE_KEY, "Quartermaster Office", REDOUBT_REGION_KEY, "Every raid has a cost column and an expected return column. Quartermaster Venn's desk treats burned roofs, recruited survivors, seized grain, and protection fees as parts of one supply equation.", {"west": REDOUBT_SUPPLY_KEY, "north": PALACE_APPROACH_KEY}, enemies=(QUARTERMASTER_VENN_KEY,), tags=("dungeon", "boss", "level_35_36")),

    _room(PALACE_APPROACH_KEY, "Banner Palace Approach", PALACE_REGION_KEY, "Dask's headquarters is not a stone palace but a campaign town built to move: gold-edged canvas halls, modular timber floors, mirrored signal towers, horse lines, archive wagons, and guard lanes. It can fold onto the road in a day.", {"west": MORROWGATE_RAMPART_KEY, "south": REDOUBT_OFFICE_KEY, "north": PALACE_OFFICERS_KEY}, enemies=(HOST_OUTRIDER_KEY,), tags=("dungeon", "level_37")),
    _room(PALACE_OFFICERS_KEY, "Officers' Mess", PALACE_REGION_KEY, "Maps are used as tablecloths under real silver plates. Officers have written wagers in the margins about which villages will buy Host protection first after the next fires.", {"south": PALACE_APPROACH_KEY, "east": PALACE_TROPHIES_KEY, "north": PALACE_MAP_KEY}, enemies=(HOST_LEVY_KEY, HOST_MARKSMAN_KEY), tags=("dungeon", "level_37_38")),
    _room(PALACE_TROPHIES_KEY, "Trophy Gallery", PALACE_REGION_KEY, "Captured standards hang beside tax seals, mayoral chains, and road markers. Several banners are duplicates of the stolen colors used in the false-flag raids.", {"west": PALACE_OFFICERS_KEY, "north": PALACE_HOSTAGES_KEY}, enemies=(WAR_HOUND_KEY,), tags=("dungeon", "level_37_38")),
    _room(PALACE_MAP_KEY, "Campaign Map Room", PALACE_REGION_KEY, "Current maps show not only Host territory but projected fear responses: likely refugee routes, towns expected to request protection, and which rival banners should be planted after each staged attack.", {"south": PALACE_OFFICERS_KEY, "east": PALACE_SIGNAL_KEY, "north": PALACE_COMMAND_KEY}, enemies=(HOST_ARSONIST_KEY,), tags=("dungeon", "revelation", "level_38_39")),
    _room(PALACE_HOSTAGES_KEY, "Hostage Wing", PALACE_REGION_KEY, "Local officials and family members of resistant merchants are kept in clean, well-fed rooms. Dask wants leverage that survives long enough to sign documents.", {"south": PALACE_TROPHIES_KEY, "east": PALACE_COMMAND_KEY}, enemies=(HOST_LEVY_KEY,), tags=("dungeon", "level_38_39")),
    _room(PALACE_SIGNAL_KEY, "Signal Stair", PALACE_REGION_KEY, "A mirrored mast rises through the roof. Its shutters can reach every surviving Host post in the March. One strike at the central alignment mirror would turn an army-wide network into isolated camps.", {"west": PALACE_MAP_KEY, "up": PALACE_COMMAND_KEY}, enemies=(HOST_MARKSMAN_KEY,), tags=("dungeon", "mechanic", "level_38_39")),
    _room(PALACE_COMMAND_KEY, "Command Hall", PALACE_REGION_KEY, "Dispatch clerks work around a long black table. Banner-Captain Hadrik guards the campaign archive while junior officers burn papers too slowly to hide how much there is to burn.", {"south": PALACE_MAP_KEY, "west": PALACE_HOSTAGES_KEY, "down": PALACE_SIGNAL_KEY, "north": PALACE_TREATY_KEY}, enemies=(BANNER_CAPTAIN_KEY,), tags=("dungeon", "boss", "level_39")),
    _room(PALACE_TREATY_KEY, "Treaty Chamber", PALACE_REGION_KEY, "A portable treaty chamber has been assembled with absurd care: clean carpets, neutral-colored walls, water for every delegation, and armed guards behind the fabric. Corven Dask has prepared a civilized room in which to demand surrender to problems he deliberately created.", {"south": PALACE_COMMAND_KEY}, enemies=(MARSHAL_DASK_KEY,), tags=("dungeon", "boss", "level_40", "capstone")),

    _room(TRIBUNAL_YARD_KEY, "Public Tribunal Yard", MORROWGATE_REGION_KEY, "A former freight court has become an open-air tribunal. Dask's ledger is copied on public boards before testimony begins so the case cannot disappear into a private chamber.", {"west": MORROWGATE_COUNCIL_KEY}, tags=("level_40", "post_capstone", "trial")),
    _room(DESERTER_ROAD_KEY, "Open Deserter Road", CROWNFIRE_REGION_KEY, "The old hidden escape path is now publicly marked. Former Host soldiers travel it unarmed toward supervised resettlement, exile, testimony, or whatever judgment their individual actions earn.", {"south": REFUGEE_FORD_KEY}, tags=("level_40", "post_capstone", "exile")),
    _room(DISARMED_ROAD_KEY, "Disarmed Host Road", CROWNFIRE_REGION_KEY, "Host brass has been stripped from the road posts and piled in baskets for reuse. Morrowgate militia patrols here under temporary authority with the patrol end-date painted on every checkpoint.", {"west": REDOUBT_GATE_KEY}, tags=("level_40", "post_capstone", "judgment")),
)


def _merge(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    extras = {(item.direction, item.destination_key): item for item in existing.extra_exits}
    extras.update({(item.direction, item.destination_key): item for item in extra.extra_exits})
    layers = {item.key: item for item in existing.description_layers}
    layers.update({item.key: item for item in extra.description_layers})
    return replace(existing, extra_exits=tuple(extras.values()), description_layers=tuple(layers.values()))


def crownfire_augmentations() -> dict[str, RoomAugmentation]:
    return {
        SALTWIND_GATE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("north", MARCHWARD_POST_KEY, "Crownfire Road", travel_text="You leave Whitewake's chalk glare and climb north into red fields stained by recent smoke.", condition=ViewCondition(required_flags=(SALT_CAPSTONE_COMPLETE_FLAG,), min_level=31), hidden_when_unavailable=True),
        )),
        GALLOWS_MILE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("east", REDOUBT_GATE_KEY, "Brass Redoubt Track", condition=ViewCondition(required_flags=(BLOCKADE_COMPLETE_FLAG,), min_level=34), hidden_when_unavailable=True),
        )),
        MORROWGATE_RAMPART_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("east", PALACE_APPROACH_KEY, "Banner Palace Road", condition=ViewCondition(required_flags=(REDOUBT_COMPLETE_FLAG, DESERTER_COMPLETE_FLAG), min_level=37), hidden_when_unavailable=True),
        )),
        MORROWGATE_COUNCIL_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("east", TRIBUNAL_YARD_KEY, "Public Tribunal Yard", condition=ViewCondition(required_flags=(TRIAL_ENDING_FLAG,)), hidden_when_unavailable=True),
        ), description_layers=(
            DescriptionLayer("trial_aftermath", "Copies of Dask's Black Ledger cover the public notice wall, each page stamped for use at the open tribunal.", 20, ViewCondition(required_flags=(TRIAL_ENDING_FLAG,))),
        )),
        REFUGEE_FORD_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("north", DESERTER_ROAD_KEY, "Open Deserter Road", condition=ViewCondition(required_flags=(EXILE_ENDING_FLAG,)), hidden_when_unavailable=True),
        ), description_layers=(
            DescriptionLayer("exile_aftermath", "The once-hidden deserter path now has public mile markers and named civilian witnesses at every crossing.", 20, ViewCondition(required_flags=(EXILE_ENDING_FLAG,))),
        )),
        REDOUBT_GATE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("east", DISARMED_ROAD_KEY, "Disarmed Host Road", condition=ViewCondition(required_flags=(JUDGMENT_ENDING_FLAG,)), hidden_when_unavailable=True),
        ), description_layers=(
            DescriptionLayer("judgment_aftermath", "The Redoubt's gold plates lie in sorted salvage baskets. Every temporary militia checkpoint carries a painted removal date.", 20, ViewCondition(required_flags=(JUDGMENT_ENDING_FLAG,))),
        )),
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


def install_crownfire_content(world_service=None) -> None:
    for quest in CROWNFIRE_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for item in CROWNFIRE_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for enemy in CROWNFIRE_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for npc in CROWNFIRE_NPCS:
        _replace_npc(npc)
    for room in CROWNFIRE_ROOMS:
        _replace_room(room)
    if world_service is None:
        return
    for room in CROWNFIRE_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for key, aug in crownfire_augmentations().items():
        world_service.augmentations[key] = _merge(world_service.augmentations.get(key), aug)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*CROWNFIRE_ROOM_KEYS, SALTWIND_GATE_KEY):
            cache.pop(key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _award(session, xp: int, item_key: str | None = None) -> int:
    assert session.character is not None
    old = session.character.level
    new = session.database.add_experience(session.character.id, xp)
    if item_key and session.database.item_quantity(session.character.id, item_key) < 1:
        session.database.add_item(session.character.id, item_key, 1)
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed
    return max(0, new - old)


def _in_region(session) -> bool:
    return bool(session.character and session.character.current_room in CROWNFIRE_ROOM_KEYS)


def _ensure_story(session) -> str | None:
    if session.character is None or not _in_region(session):
        return None
    level = session.character.level
    flags = _flags(session)
    chain = (
        (31, ARRIVAL_COMPLETE_FLAG, ARRIVAL_QUEST_KEY, "talk_mara", "New region story: The Smoke Has Orders. TALK EVARA at Marchward Post."),
        (33, BLOCKADE_COMPLETE_FLAG, BLOCKADE_QUEST_KEY, "talk_iven", "New city story: A City Under Contract. Find Mayor Iven Rook in Morrowgate Council Hall."),
        (34, REDOUBT_COMPLETE_FLAG, REDOUBT_QUEST_KEY, "talk_sera", "New campaign story: Break the Brass Redoubt. TALK RENNA on Morrowgate's East Rampart."),
        (36, DESERTER_COMPLETE_FLAG, DESERTER_QUEST_KEY, "talk_lysa", "New story: The Price of Desertion. TALK LYSA at Refugee Ford."),
        (37, PALACE_COMPLETE_FLAG, PALACE_QUEST_KEY, "talk_sera", "New dungeon story: The Banner Palace. Return to Captain Renna Hald."),
        (40, CAPSTONE_COMPLETE_FLAG, CAPSTONE_QUEST_KEY, "confront_dask", "Level-40 capstone: No Misunderstanding. Enter the Banner Palace Treaty Chamber and confront Corven Dask."),
    )
    prerequisites = (None, ARRIVAL_COMPLETE_FLAG, BLOCKADE_COMPLETE_FLAG, REDOUBT_COMPLETE_FLAG, DESERTER_COMPLETE_FLAG, PALACE_COMPLETE_FLAG)
    for index, (minimum, complete_flag, key, step, message) in enumerate(chain):
        prerequisite = prerequisites[index]
        if level >= minimum and complete_flag not in flags and _quest(session, key) is None and (prerequisite is None or prerequisite in flags):
            session.database.start_quest(session.character.id, key, step)
            return message
    return None


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")
    async def replay(_text: str):
        return command
    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_crownfire_runtime(player_session_class, world_service) -> None:
    install_crownfire_content(world_service)
    if getattr(player_session_class, "_crownfire_31_40_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        message = _ensure_story(self)
        if message:
            await self.send("\r\n" + message + "\r\n")

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character else None
        await previous_move(self, direction)
        if self.character is None or self.character.current_room == before:
            return
        message = _ensure_story(self)
        if message:
            await self.send("\r\n" + message + "\r\n")

    async def _finish_enemy_defeat(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish(self, enemy)
        if not eligible or self.character is None:
            return

        if key == SCOUT_CAPTAIN_KEY:
            q = _quest(self, ARRIVAL_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "defeat_scout":
                self.database.add_item(self.character.id, SCOUT_ORDERS_KEY, 1)
                self.database.advance_quest(self.character.id, ARRIVAL_QUEST_KEY, "read_orders")
                await self.send("The scout-captain drops a sealed packet and three stolen banners. The packet is addressed in one hand. READ ORDERS.\r\n")
        elif key == QUARTERMASTER_VENN_KEY:
            q = _quest(self, REDOUBT_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "defeat_quartermaster":
                self.database.complete_quest(self.character.id, REDOUBT_QUEST_KEY)
                self.database.grant_flag(self.character.id, REDOUBT_COMPLETE_FLAG)
                gained = _award(self, 10500, REDOUBT_BRASS_KEY)
                await self.send("Venn goes down beside an open ledger whose columns price burned farms against protection income. The Brass Redoubt is no longer a functioning forward command. Quest complete: Break the Brass Redoubt. Reward: 10,500 XP and Redoubt Brass.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                follow = _ensure_story(self)
                if follow:
                    await self.send(follow + "\r\n")
        elif key == BANNER_CAPTAIN_KEY:
            q = _quest(self, PALACE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "defeat_captain":
                self.database.advance_quest(self.character.id, PALACE_QUEST_KEY, "take_ledger")
                await self.send("Hadrik falls across the campaign archive. A black-bound ledger remains chained to the command table. TAKE BLACK LEDGER.\r\n")
        elif key == MARSHAL_DASK_KEY:
            q = _quest(self, CAPSTONE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "confront_dask":
                self.database.grant_flag(self.character.id, DASK_DEFEATED_FLAG)
                self.database.add_item(self.character.id, DASK_SIGNET_KEY, 1)
                self.database.advance_quest(self.character.id, CAPSTONE_QUEST_KEY, "choose_aftermath")
                await self.send("Corven Dask drops his sword but not his argument. 'You think people want freedom more than roads that stay open.' The Black Ledger answers for him: he closed the roads first. Choose DEMAND TRIAL, ORDER EXILE, or FIELD JUDGMENT.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        n = " ".join(command.strip().lower().split())
        room = self.character.current_room

        if room == MARCHWARD_POST_KEY and n in {"talk evara", "talk mara", "talk to neris", "talk to mara", "talk clerk"}:
            _ensure_story(self)
            q = _quest(self, ARRIVAL_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "talk_mara":
                self.database.advance_quest(self.character.id, ARRIVAL_QUEST_KEY, "inspect_wagon")
                await self.send("Evara lays three stolen banners side by side. 'Different colors. Same brass boot nails, same lamp oil, same wagon timing. Go north to Burned Toll and EXAMINE WAGON.'\r\n")
            elif q and q["status"] == "active" and q["current_step"] == "return_mara":
                self.database.complete_quest(self.character.id, ARRIVAL_QUEST_KEY)
                self.database.grant_flag(self.character.id, ARRIVAL_COMPLETE_FLAG)
                gained = _award(self, 7600)
                await self.send("Evara reads the order and stops at the line LEAVE SURVIVORS TO NAME THE WRONG ENEMY. 'Good. We do not have a mystery anymore. We have a commander.' Quest complete: The Smoke Has Orders. +7,600 XP.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                follow = _ensure_story(self)
                if follow:
                    await self.send(follow + "\r\n")
            else:
                await self.send("Evara says, 'Bring me something with a signature, not another rumor with smoke on it.'\r\n")
            return

        if room == BURNED_TOLL_KEY and n in {"examine wagon", "inspect wagon", "search wagon"}:
            q = _quest(self, ARRIVAL_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "inspect_wagon":
                self.database.advance_quest(self.character.id, ARRIVAL_QUEST_KEY, "defeat_scout")
                await self.send("The wagon was unloaded before it burned. Chalk on the axle notes SMOKE VISIBLE: 18 MIN. Someone timed the fire as a signal. The nearest Host signal frames stand on Gallows Mile. Find the Gilded Scout-Captain.\r\n")
                return

        if n == "read orders" and self.database.item_quantity(self.character.id, SCOUT_ORDERS_KEY) > 0:
            q = _quest(self, ARRIVAL_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "read_orders":
                self.database.advance_quest(self.character.id, ARRIVAL_QUEST_KEY, "return_mara")
                await self.send("The order assigns stolen local banners to raids by date and gives one instruction twice: LEAVE SURVIVORS TO NAME THE WRONG ENEMY. It carries Marshal Corven Dask's gold-road signet. Return to Evara.\r\n")
                return

        if room == MORROWGATE_COUNCIL_KEY and n in {"talk iven", "talk to iven", "talk mayor"}:
            _ensure_story(self)
            q = _quest(self, BLOCKADE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "talk_iven":
                self.database.advance_quest(self.character.id, BLOCKADE_QUEST_KEY, "talk_della")
                await self.send("Iven says, 'Our shortages are too even. Somebody is releasing just enough stock to keep panic below revolt. Talk to Della on Healers' Row; medicine is harder to fake than market gossip.'\r\n")
                return

        if room == MORROWGATE_HEALERS_KEY and n in {"talk della", "talk to della", "talk healer"}:
            q = _quest(self, BLOCKADE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "talk_della":
                self.database.advance_quest(self.character.id, BLOCKADE_QUEST_KEY, "search_contracts")
                await self.send("Della taps the shortage board. 'Every third medicine crate vanishes, never two in a row. That is a contract rhythm, not theft. Search the freight contracts in Canvas Market.'\r\n")
                return

        if room == MORROWGATE_MARKET_KEY and n in {"search contracts", "search ledgers", "inspect contracts"}:
            q = _quest(self, BLOCKADE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "search_contracts":
                self.database.advance_quest(self.character.id, BLOCKADE_QUEST_KEY, "accuse_varek")
                await self.send("A duplicate warehouse contract promises Varek's stores exemption from Host seizure in exchange for night access and exact ration data. His signature is beside a Gilded seal. ACCUSE VAREK.\r\n")
                return
        if room == MORROWGATE_MARKET_KEY and n in {"accuse varek", "confront varek"}:
            q = _quest(self, BLOCKADE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "accuse_varek":
                self.database.complete_quest(self.character.id, BLOCKADE_QUEST_KEY)
                self.database.grant_flag(self.character.id, BLOCKADE_COMPLETE_FLAG)
                gained = _award(self, 8800, BLACK_CONTRACT_KEY)
                await self.send("Varek tries 'necessary compromise' until Iven's clerk reads the medicine clauses aloud. The city seizes the side-contract and opens the exempt warehouses under public inventory. Quest complete: A City Under Contract. Reward: 8,800 XP and the Black Contract record.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                follow = _ensure_story(self)
                if follow:
                    await self.send(follow + "\r\n")
                return

        if room == MORROWGATE_RAMPART_KEY and n in {"talk renna", "talk sera", "talk to renna", "talk to sera", "talk captain"}:
            _ensure_story(self)
            redoubt = _quest(self, REDOUBT_QUEST_KEY)
            if redoubt and redoubt["status"] == "active" and redoubt["current_step"] == "talk_sera":
                self.database.advance_quest(self.character.id, REDOUBT_QUEST_KEY, "cut_signal")
                await self.send("Renna points to the Brass Redoubt. 'Do not heroically charge the office first. Cut the signal loft, free the prisoners, then remove the quartermaster from a fort that can no longer call for a replacement.'\r\n")
                return
            palace = _quest(self, PALACE_QUEST_KEY)
            if palace and palace["status"] == "active" and palace["current_step"] == "talk_sera":
                self.database.advance_quest(self.character.id, PALACE_QUEST_KEY, "break_mirror")
                await self.send("Renna marks the Banner Palace signal mast. 'Dask's strength is coordination. Break the mirror, free the leverage in the hostage wing, read his war map, then take the command hall.'\r\n")
                return

        if room == REDOUBT_SIGNAL_KEY and n in {"cut signal rope", "cut rope", "cut signal"}:
            q = _quest(self, REDOUBT_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "cut_signal":
                self.database.advance_quest(self.character.id, REDOUBT_QUEST_KEY, "free_prisoners")
                await self.send("The main signal rope parts. Three brass shutters slam out of alignment. Distant Host posts keep flashing for a minute before realizing nobody here is answering.\r\n")
                return
        if room == REDOUBT_PRISON_KEY and n in {"free prisoners", "open cage", "release prisoners"}:
            q = _quest(self, REDOUBT_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "free_prisoners":
                self.database.advance_quest(self.character.id, REDOUBT_QUEST_KEY, "defeat_quartermaster")
                await self.send("You open the cage. Civilians leave first; the two jailed levies wait until everyone else is moving, then ask which road does not lead back to Dask. Quartermaster Venn remains east of the Supply Hall.\r\n")
                return

        if room == REFUGEE_FORD_KEY and n in {"talk lysa", "talk to lysa", "talk deserter"}:
            _ensure_story(self)
            q = _quest(self, DESERTER_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "talk_lysa":
                self.database.advance_quest(self.character.id, DESERTER_QUEST_KEY, "read_rolls")
                await self.send("Lysa says, 'Some deserted before the farm burns. Some after. Some only when pay stopped. Read the conscription rolls in Venn's captured office before you decide what the word deserter buys.'\r\n")
                return
        if room == REDOUBT_OFFICE_KEY and n in {"read conscription rolls", "read rolls", "search rolls"}:
            q = _quest(self, DESERTER_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "read_rolls":
                self.database.advance_quest(self.character.id, DESERTER_QUEST_KEY, "choose")
                await self.send("The rolls distinguish volunteers, debt levies, prisoners offered service, and villages assessed one soldier per household. Several later deserters were conscripted as teenagers. Return to Lysa and choose PROTECT DESERTERS or PUBLIC TESTIMONY.\r\n")
                return
        if room == REFUGEE_FORD_KEY and n in {"protect deserters", "public testimony"}:
            q = _quest(self, DESERTER_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "choose":
                flag = DESERTER_SHELTER_FLAG if n == "protect deserters" else DESERTER_TESTIMONY_FLAG
                self.database.grant_flag(self.character.id, flag)
                self.database.grant_flag(self.character.id, DESERTER_COMPLETE_FLAG)
                self.database.complete_quest(self.character.id, DESERTER_QUEST_KEY)
                gained = _award(self, 9800, DESERTER_RIBBON_KEY)
                text = "You establish supervised shelter first, keeping witnesses alive before asking them to perform their guilt in public." if flag == DESERTER_SHELTER_FLAG else "You organize named public testimony with individual records, refusing both blanket pardon and blanket guilt."
                await self.send(text + " Quest complete: The Price of Desertion. Reward: 9,800 XP and Unbound Gold Ribbon.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                follow = _ensure_story(self)
                if follow:
                    await self.send(follow + "\r\n")
                return

        if room == PALACE_SIGNAL_KEY and n in {"break signal mirror", "break mirror", "smash mirror"}:
            q = _quest(self, PALACE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "break_mirror":
                self.database.advance_quest(self.character.id, PALACE_QUEST_KEY, "free_hostages")
                await self.send("The alignment mirror breaks into six bright pieces. Across the March, Host posts can still shout locally, but Dask can no longer make them move like one body.\r\n")
                return
        if room == PALACE_HOSTAGES_KEY and n in {"free hostages", "release hostages", "open rooms"}:
            q = _quest(self, PALACE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "free_hostages":
                self.database.advance_quest(self.character.id, PALACE_QUEST_KEY, "read_map")
                await self.send("You open the hostage rooms and route people south before the officers understand their leverage is walking away. Next: READ WAR MAP.\r\n")
                return
        if room == PALACE_MAP_KEY and n in {"read war map", "read map", "examine map"}:
            q = _quest(self, PALACE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "read_map":
                self.database.advance_quest(self.character.id, PALACE_QUEST_KEY, "defeat_captain")
                await self.send("The map is annotated in Dask's hand: BURN THREE UNALIGNED FARMS; PROTECTION ENROLLMENT PROJECTED +18%. Another note orders two rival banners planted at the scene. There is nothing accidental left to explain. Banner-Captain Hadrik holds the Command Hall.\r\n")
                return
        if room == PALACE_COMMAND_KEY and n in {"take black ledger", "take ledger", "read black ledger"}:
            q = _quest(self, PALACE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "take_ledger":
                if self.database.item_quantity(self.character.id, BLACK_LEDGER_KEY) < 1:
                    self.database.add_item(self.character.id, BLACK_LEDGER_KEY, 1)
                self.database.complete_quest(self.character.id, PALACE_QUEST_KEY)
                self.database.grant_flag(self.character.id, PALACE_COMPLETE_FLAG)
                gained = _award(self, 14500)
                await self.send("The Black Ledger pairs every staged crisis with projected tolls, enlistment, warehouse contracts, and protection revenue. Corven Dask did not misunderstand the consequences; he budgeted them. Quest complete: The Banner Palace. +14,500 XP.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                follow = _ensure_story(self)
                if follow:
                    await self.send(follow + "\r\n")
                return

        if room == PALACE_TREATY_KEY and n in {"demand trial", "order exile", "field judgment"}:
            q = _quest(self, CAPSTONE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "choose_aftermath" and DASK_DEFEATED_FLAG in _flags(self):
                mapping = {
                    "demand trial": (TRIAL_ENDING_FLAG, "Dask is taken alive to an open tribunal. The Black Ledger is copied before anyone can bargain it into a sealed archive."),
                    "order exile": (EXILE_ENDING_FLAG, "Dask is stripped of command, property, signet, and armed followers and expelled under witnessed terms. The deserter road becomes public so hidden flight cannot be turned into another private network."),
                    "field judgment": (JUDGMENT_ENDING_FLAG, "You reject another private negotiation and order immediate field judgment under the captured campaign record. The Host command ends here, and the Redoubt road is disarmed under temporary civic patrol."),
                }
                flag, text = mapping[n]
                self.database.grant_flag(self.character.id, flag)
                self.database.grant_flag(self.character.id, CAPSTONE_COMPLETE_FLAG)
                self.database.complete_quest(self.character.id, CAPSTONE_QUEST_KEY)
                gained = _award(self, 19000, FREE_MARCH_CHARTER_KEY)
                await self.send(text + " Region capstone complete: No Misunderstanding. Reward: 19,000 XP and Free March Charter. Crownfire's postwar map has changed for this character.\r\n")
                if gained:
                    await self.send(f"You gained {gained} level.\r\n")
                return

        if n in {"crownfire", "crownfire help", "march status"} and _in_region(self):
            flags = _flags(self)
            complete = sum(flag in flags for flag in (ARRIVAL_COMPLETE_FLAG, BLOCKADE_COMPLETE_FLAG, REDOUBT_COMPLETE_FLAG, DESERTER_COMPLETE_FLAG, PALACE_COMPLETE_FLAG, CAPSTONE_COMPLETE_FLAG))
            await self.send(f"Crownfire March: {complete}/6 major stories complete. Levels 31-32 prove the raids are ordered false flags; 33 exposes the blockade collaborator; 34-35 breaks the Brass Redoubt; 36 decides how deserters become witnesses or refugees; 37-39 dismantles the Banner Palace; 40 confronts Corven Dask and determines the aftermath.\r\n")
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._crownfire_31_40_installed = True
