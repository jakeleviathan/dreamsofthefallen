from __future__ import annotations

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.veyra_city import VEYRA_RESIDENT_FLAG, VEYRA_SOUTH_SPRAWL_KEY
from mud.world import NpcDefinition, RoomDefinition


SABLEWATER_REGION_KEY = "sablewater_reach"
SABLEWATER_NORTH_FERRY_KEY = "sablewater_north_ferry"
SABLEWATER_FLOOD_ROAD_KEY = "sablewater_flood_road"
SABLEWATER_REED_FARMS_KEY = "sablewater_reed_farms"
SABLEWATER_EEL_DOCK_KEY = "sablewater_eelmarket_dock"
SABLEWATER_HERON_FLATS_KEY = "sablewater_heron_flats"
SABLEWATER_BROKEN_LEVEE_KEY = "sablewater_broken_levee"
SABLEWATER_WILLOW_FERRY_KEY = "sablewater_willow_ferry"
SABLEWATER_SALTGRASS_BEND_KEY = "sablewater_saltgrass_bend"
SABLEWATER_OLD_CUSTOMS_KEY = "sablewater_old_customs_road"
SABLEWATER_TOLL_ISLAND_KEY = "sablewater_toll_island"
SABLEWATER_ROOKERY_KEY = "sablewater_rookery"
SABLEWATER_DRIFTWOOD_SHRINE_KEY = "sablewater_driftwood_shrine"
SABLEWATER_TOLLHOUSE_MOUTH_KEY = "sablewater_drowned_tollhouse_mouth"

SABLEWATER_ROOM_KEYS = (
    SABLEWATER_NORTH_FERRY_KEY,
    SABLEWATER_FLOOD_ROAD_KEY,
    SABLEWATER_REED_FARMS_KEY,
    SABLEWATER_EEL_DOCK_KEY,
    SABLEWATER_HERON_FLATS_KEY,
    SABLEWATER_BROKEN_LEVEE_KEY,
    SABLEWATER_WILLOW_FERRY_KEY,
    SABLEWATER_SALTGRASS_BEND_KEY,
    SABLEWATER_OLD_CUSTOMS_KEY,
    SABLEWATER_TOLL_ISLAND_KEY,
    SABLEWATER_ROOKERY_KEY,
    SABLEWATER_DRIFTWOOD_SHRINE_KEY,
    SABLEWATER_TOLLHOUSE_MOUTH_KEY,
)

DROWNED_ENTRY_KEY = "drowned_tollhouse_entry"
DROWNED_TOLL_HALL_KEY = "drowned_tollhouse_toll_hall"
DROWNED_LEDGER_GALLERY_KEY = "drowned_tollhouse_ledger_gallery"
DROWNED_SLUICE_CHAMBER_KEY = "drowned_tollhouse_sluice_chamber"
DROWNED_CHAIN_LIFT_KEY = "drowned_tollhouse_chain_lift"
DROWNED_FLOODED_ARCHIVE_KEY = "drowned_tollhouse_flooded_archive"
DROWNED_COIN_VAULT_KEY = "drowned_tollhouse_coin_vault"
DROWNED_OLD_KITCHEN_KEY = "drowned_tollhouse_old_kitchen"
DROWNED_MAGISTRATE_ROOM_KEY = "drowned_tollhouse_magistrate_room"
DROWNED_CLOCK_CHAMBER_KEY = "drowned_tollhouse_clock_chamber"
DROWNED_BRASS_TRIBUNAL_KEY = "drowned_tollhouse_brass_tribunal"
DROWNED_COLLECTOR_WELL_KEY = "drowned_tollhouse_collector_well"

DROWNED_ROOM_KEYS = (
    DROWNED_ENTRY_KEY,
    DROWNED_TOLL_HALL_KEY,
    DROWNED_LEDGER_GALLERY_KEY,
    DROWNED_SLUICE_CHAMBER_KEY,
    DROWNED_CHAIN_LIFT_KEY,
    DROWNED_FLOODED_ARCHIVE_KEY,
    DROWNED_COIN_VAULT_KEY,
    DROWNED_OLD_KITCHEN_KEY,
    DROWNED_MAGISTRATE_ROOM_KEY,
    DROWNED_CLOCK_CHAMBER_KEY,
    DROWNED_BRASS_TRIBUNAL_KEY,
    DROWNED_COLLECTOR_WELL_KEY,
)

LOW_WATER_QUEST_KEY = "sablewater_low_water_old_debts"
TOLL_NOBODY_OWES_QUEST_KEY = "sablewater_toll_nobody_owes"
PRICE_OF_CROSSING_QUEST_KEY = "drowned_tollhouse_price_of_crossing"
SABLEWATER_INTRO_COMPLETE_FLAG = "sablewater_first_route_complete"
TOLLHOUSE_UNLOCKED_FLAG = "drowned_tollhouse_unlocked"
SLUICE_WARDEN_DEFEATED_FLAG = "drowned_sluice_warden_defeated"
AUDITOR_AUTHORIZED_FLAG = "drowned_auditor_authorized"
AUDITOR_DEFEATED_FLAG = "drowned_auditor_defeated"
DROWNED_TOLLHOUSE_COMPLETE_FLAG = "drowned_tollhouse_complete"
ARCHIVE_SEAL_FLAG = "drowned_archive_seal_found"
VAULT_SEAL_FLAG = "drowned_vault_seal_found"
MAGISTRATE_SEAL_FLAG = "drowned_magistrate_seal_found"

CUSTOMS_SEAL_KEY = "obsolete_customs_seal"
DROWNED_BRASS_SCRAP_KEY = "drowned_brass_scrap"
AUDITOR_GEAR_KEY = "brass_auditor_gear"

REEDCAT_KEY = "sablewater_reedcat"
MUDPLATE_KEY = "sablewater_mudplate"
ROPEJAW_KEY = "sablewater_ropejaw_eel"
KNOTJACK_KEY = "sablewater_knotjack"
INKLEECH_KEY = "drowned_inkleech"
TARIFF_CRAB_KEY = "drowned_tariff_crab"
BRASS_CLERK_KEY = "drowned_brass_clerk"
SLUICE_WARDEN_KEY = "drowned_sluice_warden"
BRASS_AUDITOR_KEY = "drowned_brass_auditor"

FERRYMASTER_KEY = "sablewater_ferrymaster_jessa_pike"
LEVEE_KEEPER_KEY = "sablewater_keeper_orren_span"
DIVER_KEY = "sablewater_diver_nym_underhook"


LOW_WATER_QUEST = QuestDefinition(
    key=LOW_WATER_QUEST_KEY,
    name="Low Water, Old Debts",
    style="structured",
    minimum_level=6,
    description=(
        "Veyra's southern floodplain is changing for ordinary river reasons: silt, levees, old channels, and people maintaining some structures while forgetting others. "
        "Ferrymaster Jessa needs facts before another boat grounds."
    ),
    objective_steps=(
        ("talk_ferrymaster", "TALK FERRYMASTER at North Ferry."),
        ("inspect_levee", "Reach Broken Levee and EXAMINE BREACH."),
        ("inspect_chain", "At Willow Ferry EXAMINE FERRY CHAIN."),
        ("return_ferrymaster", "Return to North Ferry and TALK FERRYMASTER."),
        ("complete", "You traced the low-water problem to neglected riverworks and an old side channel rather than a supernatural cause."),
    ),
)

TOLL_NOBODY_OWES_QUEST = QuestDefinition(
    key=TOLL_NOBODY_OWES_QUEST_KEY,
    name="A Toll Nobody Owes",
    style="structured",
    minimum_level=7,
    description=(
        "The blocked side channel runs past an abandoned customs road and a toll fortress that has been obsolete for generations. "
        "Find out why its machinery is still pulling against the river."
    ),
    objective_steps=(
        ("inspect_marker", "At Old Customs Road EXAMINE TOLL MARKER."),
        ("inspect_gate", "Reach Drowned Tollhouse Mouth and EXAMINE SUNKEN GATE."),
        ("talk_diver", "TALK DIVER at the Tollhouse Mouth."),
        ("complete", "You opened a safe descent into the old tollhouse and learned that obsolete civic machinery is still operating below."),
    ),
)

PRICE_OF_CROSSING_QUEST = QuestDefinition(
    key=PRICE_OF_CROSSING_QUEST_KEY,
    name="The Price of Crossing",
    style="structured",
    minimum_level=8,
    description=(
        "The Drowned Tollhouse is not haunted by Greywake. It is a different kind of problem: a centuries-old customs complex whose clockwork enforcement system never received the news that its law expired."
    ),
    objective_steps=(
        ("defeat_warden", "Defeat the Sluice Warden in the old water-control chamber."),
        ("collect_seals", "Recover three Obsolete Customs Seals by SEARCH LEDGERS, SEARCH COIN VAULT, and SEARCH MAGISTRATE DESK."),
        ("present_seals", "At the Brass Tribunal PRESENT SEALS."),
        ("defeat_auditor", "ATTACK AUDITOR after the obsolete seals satisfy its authorization check."),
        ("open_sluice", "Enter Collector's Well and TURN FINAL SLUICE."),
        ("complete", "You shut down the obsolete toll engine and reopened the old side channel to the living river."),
    ),
)

SABLEWATER_QUESTS = (LOW_WATER_QUEST, TOLL_NOBODY_OWES_QUEST, PRICE_OF_CROSSING_QUEST)

CUSTOMS_SEAL = ItemDefinition(
    key=CUSTOMS_SEAL_KEY,
    name="Obsolete Customs Seal",
    description="A stamped brass customs seal from a government that stopped collecting this river toll generations ago. The mechanism below has not accepted that fact.",
    category="quest_item",
    tier=2,
)
DROWNED_BRASS_SCRAP = ItemDefinition(
    key=DROWNED_BRASS_SCRAP_KEY,
    name="Drowned Brass Scrap",
    description="Water-dark brass gears, tags, and cage pieces recovered from the old tollhouse. Still useful to artificers and repair-minded smiths.",
    category="material",
    tier=2,
)
AUDITOR_GEAR = ItemDefinition(
    key=AUDITOR_GEAR_KEY,
    name="Brass Auditor Gear",
    description="A large precision gear removed from the stopped toll engine. One face is engraved with an obsolete tariff schedule; the other is excellent metal.",
    category="material",
    tier=3,
)
SABLEWATER_ITEMS = (CUSTOMS_SEAL, DROWNED_BRASS_SCRAP, AUDITOR_GEAR)


REEDCAT = EnemyDefinition(
    key=REEDCAT_KEY,
    name="Reedcat",
    aliases=("reedcat", "reed cat"),
    description="a long-legged floodplain cat whose striped coat breaks into vertical reed shadows when it crouches",
    max_hp=84,
    armor_class=8,
    auto_attack_damage=7,
    auto_attack_interval=2.9,
    xp_reward=60,
)
MUDPLATE = EnemyDefinition(
    key=MUDPLATE_KEY,
    name="Mudplate Turtle",
    aliases=("turtle", "mudplate", "mudplate turtle"),
    description="a wagon-wheel-sized river turtle with silt-caked shell plates and the temperament of a door being forced open",
    max_hp=112,
    armor_class=14,
    auto_attack_damage=8,
    auto_attack_interval=3.5,
    xp_reward=78,
)
ROPEJAW = EnemyDefinition(
    key=ROPEJAW_KEY,
    name="Ropejaw Eel",
    aliases=("eel", "ropejaw", "ropejaw eel"),
    description="a thick river eel with fibrous whiskers strong enough to snag ferry lines and a jaw built for shellfish rather than good decisions",
    max_hp=124,
    armor_class=10,
    auto_attack_damage=10,
    auto_attack_interval=2.8,
    xp_reward=90,
)
KNOTJACK = EnemyDefinition(
    key=KNOTJACK_KEY,
    name="Knotjack",
    aliases=("knotjack", "knot jack"),
    description="a six-limbed marsh scavenger famous for stealing rope, bright buckles, and occasionally the unsecured end of a boat",
    max_hp=138,
    armor_class=11,
    auto_attack_damage=11,
    auto_attack_interval=2.7,
    xp_reward=102,
)
INKLEECH = EnemyDefinition(
    key=INKLEECH_KEY,
    name="Ink Leech",
    aliases=("leech", "ink leech", "inkleech"),
    description="a hand-long black leech swollen on mineral-rich floodwater until its skin shines like spilled writing ink",
    max_hp=118,
    armor_class=9,
    auto_attack_damage=9,
    auto_attack_interval=2.7,
    xp_reward=82,
)
TARIFF_CRAB = EnemyDefinition(
    key=TARIFF_CRAB_KEY,
    name="Tariff Crab",
    aliases=("crab", "tariff crab"),
    description="a broad river crab nesting inside a brass customs cage, wearing stamped fee tags across its shell like accidental armor",
    max_hp=146,
    armor_class=15,
    auto_attack_damage=10,
    auto_attack_interval=3.1,
    xp_reward=104,
)
BRASS_CLERK = EnemyDefinition(
    key=BRASS_CLERK_KEY,
    name="Brass Clerk",
    aliases=("clerk", "brass clerk", "clockwork clerk"),
    description="a waist-high clockwork filing construct that still sorts anything entering its corridor into PAID, UNPAID, or PHYSICALLY RESISTANT",
    max_hp=164,
    armor_class=14,
    auto_attack_damage=12,
    auto_attack_interval=2.8,
    xp_reward=122,
)
SLUICE_WARDEN = EnemyDefinition(
    key=SLUICE_WARDEN_KEY,
    name="Sluice Warden",
    aliases=("warden", "sluice warden", "clockwork warden"),
    description="a heavy brass-and-iron maintenance automaton with paddle-shaped arms built to clear jammed floodgates and, apparently, adventurers",
    max_hp=235,
    armor_class=17,
    auto_attack_damage=14,
    auto_attack_interval=3.0,
    xp_reward=190,
)
BRASS_AUDITOR = EnemyDefinition(
    key=BRASS_AUDITOR_KEY,
    name="Brass Auditor",
    aliases=("auditor", "brass auditor", "last collector"),
    description="a towering customs engine of counterweights, stamp arms, rotating tariff drums, and one red glass lens that has spent centuries waiting for paperwork nobody owes it",
    max_hp=340,
    armor_class=19,
    auto_attack_damage=16,
    auto_attack_interval=2.8,
    xp_reward=285,
)
SABLEWATER_ENEMIES = (REEDCAT, MUDPLATE, ROPEJAW, KNOTJACK, INKLEECH, TARIFF_CRAB, BRASS_CLERK, SLUICE_WARDEN, BRASS_AUDITOR)


FERRYMASTER = NpcDefinition(
    key=FERRYMASTER_KEY,
    name="Ferrymaster Jessa Pike",
    short_description="a sun-browned ferrymaster moving pebbles across a board to represent river depth reports",
    room_key=SABLEWATER_NORTH_FERRY_KEY,
    role="Sablewater route quest giver",
    dialogue=(
        "'A river is a road that edits itself. Anybody telling you otherwise is selling a bridge.'",
        "'The south ferry grounded twice this week. I want the cause before I want a villain.'",
    ),
)
LEVEE_KEEPER = NpcDefinition(
    key=LEVEE_KEEPER_KEY,
    name="Orren Span",
    short_description="a levee keeper carrying three shovels and trusting none of them as much as the waterline carved into the posts",
    room_key=SABLEWATER_BROKEN_LEVEE_KEY,
    role="riverworks caretaker",
    dialogue=(
        "'This break did not happen in one night. People just started noticing in one night.'",
        "'Old customs works diverted a side channel here. Close a river path long enough and the river sends the bill somewhere else.'",
    ),
)
DIVER = NpcDefinition(
    key=DIVER_KEY,
    name="Nym Underhook",
    short_description="a Goblin salvage diver drying a coil of rope beside the half-submerged customs gate",
    room_key=SABLEWATER_TOLLHOUSE_MOUTH_KEY,
    role="Drowned Tollhouse guide",
    dialogue=(
        "'Good news: not cursed. Bad news: still legally open according to a machine older than my grandmother's grandmother's favorite debt.'",
        "'I cleared a person-sized descent. The big mechanisms below are still moving. Bring paperwork or a hammer. Probably both.'",
    ),
)
SABLEWATER_NPCS = (FERRYMASTER, LEVEE_KEEPER, DIVER)


def _room(key: str, name: str, description: str, exits: dict[str, str], *, npcs: tuple[str, ...] = (), enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=SABLEWATER_REGION_KEY,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "sablewater", "midgame", *tags),
    )


SABLEWATER_ROOMS: tuple[RoomDefinition, ...] = (
    _room(SABLEWATER_NORTH_FERRY_KEY, "North Ferry Steps", "Veyra's timber sprawl gives way to a broad ferry landing where the river divides around reed islands. Depth poles stand in neat rows and every ferryman has a different opinion about yesterday's current.", {"north": VEYRA_SOUTH_SPRAWL_KEY, "south": SABLEWATER_FLOOD_ROAD_KEY, "east": SABLEWATER_EEL_DOCK_KEY}, npcs=(FERRYMASTER_KEY,), tags=("safe", "level_6", "quest_hub")),
    _room(SABLEWATER_FLOOD_ROAD_KEY, "Flood Road", "A raised dirt road crosses wet pasture between drainage ditches. Wheel ruts show where traffic moves when the road is dry and where traffic regrets moving when it is not.", {"north": SABLEWATER_NORTH_FERRY_KEY, "west": SABLEWATER_REED_FARMS_KEY, "south": SABLEWATER_BROKEN_LEVEE_KEY}, enemies=(REEDCAT_KEY,), tags=("level_6", "road")),
    _room(SABLEWATER_REED_FARMS_KEY, "Reed Farms", "Long narrow plots grow basket reed, cotton, cooking greens, and medicinal ditch herbs in strips divided by footpaths no cart could use. Farm families sell to Veyra without pretending the city invented the food.", {"east": SABLEWATER_FLOOD_ROAD_KEY, "south": SABLEWATER_HERON_FLATS_KEY}, enemies=(MUDPLATE_KEY,), tags=("level_6", "gathering")),
    _room(SABLEWATER_EEL_DOCK_KEY, "Eelmarket Dock", "A low dock supports smoke sheds, bait tables, ferry repair, and a morning fish market famous for selling animals that still seem undecided about being merchandise.", {"west": SABLEWATER_NORTH_FERRY_KEY, "south": SABLEWATER_WILLOW_FERRY_KEY}, enemies=(ROPEJAW_KEY,), tags=("level_6_7", "river")),
    _room(SABLEWATER_HERON_FLATS_KEY, "Heron Flats", "Shallow water mirrors open sky between sedge hummocks. Tall white herons stalk fish while travelers pick their way along old stone stepping lines revealed only at low water.", {"north": SABLEWATER_REED_FARMS_KEY, "east": SABLEWATER_BROKEN_LEVEE_KEY, "south": SABLEWATER_SALTGRASS_BEND_KEY}, enemies=(REEDCAT_KEY, KNOTJACK_KEY), tags=("level_7", "wetland")),
    _room(SABLEWATER_BROKEN_LEVEE_KEY, "Broken Levee", "A century of repairs has turned the levee into a visible history of flood fear: stone core, timber cribbing, packed clay, Goblin plate, fresh sandbags. One old section has slumped toward a forgotten side channel.", {"north": SABLEWATER_FLOOD_ROAD_KEY, "west": SABLEWATER_HERON_FLATS_KEY, "east": SABLEWATER_WILLOW_FERRY_KEY}, npcs=(LEVEE_KEEPER_KEY,), enemies=(MUDPLATE_KEY,), tags=("level_7", "evidence")),
    _room(SABLEWATER_WILLOW_FERRY_KEY, "Willow Ferry", "A cable ferry crosses a narrow branch under leaning willows. The main chain hangs at the wrong angle and scrapes an older submerged cable every time the boat reaches midstream.", {"north": SABLEWATER_EEL_DOCK_KEY, "west": SABLEWATER_BROKEN_LEVEE_KEY, "south": SABLEWATER_OLD_CUSTOMS_KEY}, enemies=(ROPEJAW_KEY,), tags=("level_7", "ferry")),
    _room(SABLEWATER_SALTGRASS_BEND_KEY, "Saltgrass Bend", "The floodplain broadens into pale grass around mineral springs. Old ferry stakes emerge from the mud far from today's channel, proof that the river has been changing its mind longer than Veyra has been keeping records.", {"north": SABLEWATER_HERON_FLATS_KEY, "east": SABLEWATER_OLD_CUSTOMS_KEY, "south": SABLEWATER_DRIFTWOOD_SHRINE_KEY}, enemies=(KNOTJACK_KEY,), tags=("level_7_8", "gathering")),
    _room(SABLEWATER_OLD_CUSTOMS_KEY, "Old Customs Road", "A paved strip rises unexpectedly from the wetland. Half-buried milestones carry obsolete tariff marks instead of distances. The road points toward an island fortress that no living government claims as a toll station.", {"north": SABLEWATER_WILLOW_FERRY_KEY, "west": SABLEWATER_SALTGRASS_BEND_KEY, "east": SABLEWATER_TOLL_ISLAND_KEY}, enemies=(KNOTJACK_KEY,), tags=("level_8", "old_road")),
    _room(SABLEWATER_TOLL_ISLAND_KEY, "Toll Island", "Stone retaining walls hold a small artificial island against the current. Rusted mooring rings still line the edge. The old customs fortress crouches downstream behind reeds, its lower floor drowned and its upper machinery improbably ticking.", {"west": SABLEWATER_OLD_CUSTOMS_KEY, "north": SABLEWATER_ROOKERY_KEY, "east": SABLEWATER_TOLLHOUSE_MOUTH_KEY}, enemies=(MUDPLATE_KEY,), tags=("level_8", "dungeon_approach")),
    _room(SABLEWATER_ROOKERY_KEY, "Blackwing Rookery", "Hundreds of glossy marsh birds nest in dead trees around a dry hummock. They have stolen bright customs tags, buckles, spoons, mirror chips, and one tiny brass stamp from somewhere downstream.", {"south": SABLEWATER_TOLL_ISLAND_KEY, "west": SABLEWATER_DRIFTWOOD_SHRINE_KEY}, enemies=(REEDCAT_KEY,), tags=("level_8", "exploration")),
    _room(SABLEWATER_DRIFTWOOD_SHRINE_KEY, "Driftwood Shrine", "Travelers have wedged bits of driftwood into a stone niche for so many years that nobody remembers which religion started it. Current ferrymen leave knots of rope; farmers leave seed; children leave things they found and adults wish they had not.", {"north": SABLEWATER_SALTGRASS_BEND_KEY, "east": SABLEWATER_ROOKERY_KEY}, tags=("safe", "social", "rest")),
    _room(SABLEWATER_TOLLHOUSE_MOUTH_KEY, "Drowned Tollhouse Mouth", "An arched customs gate descends directly into dark riverwater beneath the old fortress. Nym has rigged a rope line through a person-sized gap. Deep inside, something stamps metal at perfectly regular intervals.", {"west": SABLEWATER_TOLL_ISLAND_KEY}, npcs=(DIVER_KEY,), enemies=(ROPEJAW_KEY,), tags=("level_8", "dungeon_entrance")),
)


def _droom(key: str, name: str, description: str, exits: dict[str, str], *, enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key="drowned_tollhouse",
        description=description,
        exits=exits,
        enemy_keys=enemies,
        tags=("shared_world", "dungeon", "drowned_tollhouse", "level_8_11", *tags),
    )


DROWNED_ROOMS: tuple[RoomDefinition, ...] = (
    _droom(DROWNED_ENTRY_KEY, "Submerged Entry", "A rope descent reaches a stone landing one step above black water. Old customs arrows still direct arrivals toward DECLARATIONS and DEPARTURES, both equally flooded.", {"up": SABLEWATER_TOLLHOUSE_MOUTH_KEY, "east": DROWNED_TOLL_HALL_KEY}, enemies=(INKLEECH_KEY,), tags=("entry",)),
    _droom(DROWNED_TOLL_HALL_KEY, "Toll Hall", "Six empty clerk windows face a hall where floor grooves once guided wagons past inspection. Brass stamp mechanisms click behind the walls whenever weight crosses the old lanes.", {"west": DROWNED_ENTRY_KEY, "east": DROWNED_LEDGER_GALLERY_KEY, "south": DROWNED_OLD_KITCHEN_KEY}, enemies=(TARIFF_CRAB_KEY,), tags=("level_8",)),
    _droom(DROWNED_LEDGER_GALLERY_KEY, "Ledger Gallery", "Waterlogged tariff boards hang beside carved stone tables. Every fee has been amended, superseded, crossed out, reinstated, and finally abandoned by history rather than by the mechanism that recorded it.", {"west": DROWNED_TOLL_HALL_KEY, "east": DROWNED_SLUICE_CHAMBER_KEY, "north": DROWNED_FLOODED_ARCHIVE_KEY}, enemies=(BRASS_CLERK_KEY,), tags=("level_8_9",)),
    _droom(DROWNED_SLUICE_CHAMBER_KEY, "Sluice Chamber", "A massive gate wheel controls a side channel beneath the fortress. The wheel is still powered by river current through a gear train, and a broad maintenance construct patrols the catwalk as if closure orders were never filed.", {"west": DROWNED_LEDGER_GALLERY_KEY, "east": DROWNED_CHAIN_LIFT_KEY}, enemies=(SLUICE_WARDEN_KEY,), tags=("miniboss", "level_9")),
    _droom(DROWNED_CHAIN_LIFT_KEY, "Chain Lift", "A freight platform hangs over a vertical shaft on thick black chains. Counterweights move a few inches every minute under power from somewhere deeper, patiently trying to service floors that collapsed generations ago.", {"west": DROWNED_SLUICE_CHAMBER_KEY, "north": DROWNED_COIN_VAULT_KEY, "south": DROWNED_CLOCK_CHAMBER_KEY}, enemies=(INKLEECH_KEY,), tags=("level_9",)),
    _droom(DROWNED_FLOODED_ARCHIVE_KEY, "Flooded Archive", "Shelves stand waist-deep in still water, their paper long dissolved into grey pulp. Brass document tubes survive in wall niches above the flood line.", {"south": DROWNED_LEDGER_GALLERY_KEY, "east": DROWNED_COIN_VAULT_KEY}, enemies=(INKLEECH_KEY,), tags=("seal_room",)),
    _droom(DROWNED_COIN_VAULT_KEY, "Coin Vault", "The vault is almost empty of currency and completely full of river crabs. Old accounting cages remain bolted to the floor, each labeled for a denomination no current market recognizes.", {"west": DROWNED_FLOODED_ARCHIVE_KEY, "south": DROWNED_CHAIN_LIFT_KEY, "east": DROWNED_MAGISTRATE_ROOM_KEY}, enemies=(TARIFF_CRAB_KEY,), tags=("seal_room", "level_9")),
    _droom(DROWNED_OLD_KITCHEN_KEY, "Clerks' Kitchen", "A dry upper room still holds stone ovens, cracked mugs, tally scratches, and a wall joke complaining that toll collectors somehow taxed lunch twice. It is the most human room in the complex.", {"north": DROWNED_TOLL_HALL_KEY, "east": DROWNED_MAGISTRATE_ROOM_KEY}, enemies=(BRASS_CLERK_KEY,), tags=("level_9",)),
    _droom(DROWNED_MAGISTRATE_ROOM_KEY, "Magistrate's Room", "A raised desk overlooks a private inspection bay. The official seal press remains locked open beside a decree box whose contents were protected from water by wax and institutional paranoia.", {"west": DROWNED_OLD_KITCHEN_KEY, "north": DROWNED_COIN_VAULT_KEY, "east": DROWNED_CLOCK_CHAMBER_KEY}, enemies=(BRASS_CLERK_KEY,), tags=("seal_room",)),
    _droom(DROWNED_CLOCK_CHAMBER_KEY, "Clock Chamber", "Vertical shafts, tariff drums, water clocks, and counterweights fill a chamber built to synchronize gates, records, fees, and inspection signals. The machine has no mind, but centuries of maintenance logic make it look stubbornly purposeful.", {"north": DROWNED_CHAIN_LIFT_KEY, "west": DROWNED_MAGISTRATE_ROOM_KEY, "east": DROWNED_BRASS_TRIBUNAL_KEY}, enemies=(BRASS_CLERK_KEY, TARIFF_CRAB_KEY), tags=("level_10",)),
    _droom(DROWNED_BRASS_TRIBUNAL_KEY, "Brass Tribunal", "A circular customs chamber surrounds a motionless central machine taller than a Troll. Three seal slots wait beneath an engraved instruction: PRESENT VALID AUTHORITY BEFORE DISPUTING ASSESSMENT. The law is dead. The interlock is not.", {"west": DROWNED_CLOCK_CHAMBER_KEY}, tags=("boss", "level_10_11")),
    _droom(DROWNED_COLLECTOR_WELL_KEY, "Collector's Well", "Behind the Tribunal, a final sluice wheel controls the forgotten side channel that once carried customs traffic around the island. Opening it would give floodwater somewhere useful to go again.", {"west": DROWNED_BRASS_TRIBUNAL_KEY}, tags=("dungeon_end", "level_10")),
)

ALL_SABLEWATER_ROOMS = SABLEWATER_ROOMS + DROWNED_ROOMS
ALL_SABLEWATER_ROOM_KEYS = SABLEWATER_ROOM_KEYS + DROWNED_ROOM_KEYS


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


def sablewater_augmentations() -> dict[str, RoomAugmentation]:
    return {
        VEYRA_SOUTH_SPRAWL_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=SABLEWATER_NORTH_FERRY_KEY,
                    name="Sablewater Reach",
                    travel_text="You follow the ferry road south out of Veyra into the Sablewater floodplain.",
                    condition=ViewCondition(required_flags=(VEYRA_RESIDENT_FLAG,), min_level=6),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        SABLEWATER_BROKEN_LEVEE_KEY: RoomAugmentation(
            features=(
                _feature("sablewater_breach", "Levee Breach", "a slumped old levee section spilling toward a forgotten side channel", "The fresh damage is small. The important failure is old: the side channel beyond was pinched narrower over decades by neglected customs stonework, forcing more flood pressure against this levee every season.", ("breach", "levee", "slump")),
            ),
        ),
        SABLEWATER_WILLOW_FERRY_KEY: RoomAugmentation(
            features=(
                _feature("sablewater_ferry_chain", "Ferry Chain", "the working ferry cable scraping a much older submerged chain", "The active chain is sound. At midstream it drags across a massive obsolete guide chain that once pulled customs barges toward Toll Island. Low water has brought the two systems into conflict.", ("chain", "ferry chain", "cable")),
            ),
        ),
        SABLEWATER_OLD_CUSTOMS_KEY: RoomAugmentation(
            features=(
                _feature("sablewater_toll_marker", "Obsolete Toll Marker", "a half-buried stone listing fees no living government collects", "The marker charges by axle, animal, passenger, cargo class, and one mysterious category translated as 'unlicensed dramatic entrance.' A later chisel mark says TOLL ABOLISHED. The road mechanism beyond clearly did not receive the amendment.", ("marker", "toll marker", "tariff stone")),
            ),
        ),
        SABLEWATER_TOLLHOUSE_MOUTH_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=DROWNED_ENTRY_KEY,
                    name="Drowned Tollhouse",
                    travel_text="You clip onto Nym's rope line and descend through the flooded customs gate.",
                    condition=ViewCondition(required_flags=(TOLLHOUSE_UNLOCKED_FLAG,), min_level=8),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature("sablewater_sunken_gate", "Sunken Customs Gate", "a half-submerged gate whose internal stamp machinery still cycles", "The outer bars are rusted but not load-bearing. Nym's rope route bypasses them. Deeper inside, a powered mechanism stamps once every thirty breaths despite having no customers.", ("gate", "sunken gate", "customs gate")),
            ),
        ),
        DROWNED_FLOODED_ARCHIVE_KEY: RoomAugmentation(
            features=(
                _feature("drowned_archive_tubes", "Archive Tubes", "sealed brass document tubes above the flood line", "Most tubes contain tariff amendments. One holds an embossed authority seal cancelled by a later government but still mechanically valid to the old toll engine. SEARCH LEDGERS can recover it.", ("tubes", "ledgers", "archive")),
            ),
        ),
        DROWNED_COIN_VAULT_KEY: RoomAugmentation(
            features=(
                _feature("drowned_coin_cages", "Coin Cages", "empty accounting cages behind territorial river crabs", "One cage contains no money at all—only a customs officer's emergency seal kit. SEARCH COIN VAULT after dealing with the room's hazards.", ("cages", "coin vault", "vault")),
            ),
        ),
        DROWNED_MAGISTRATE_ROOM_KEY: RoomAugmentation(
            features=(
                _feature("drowned_magistrate_desk", "Magistrate Desk", "a raised desk beside an open seal press", "The drawers are swollen shut except for a wax-lined emergency compartment. SEARCH MAGISTRATE DESK can recover the last authority seal the Tribunal still understands.", ("desk", "magistrate desk", "seal press")),
            ),
        ),
        DROWNED_BRASS_TRIBUNAL_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=DROWNED_COLLECTOR_WELL_KEY,
                    name="Collector's Well",
                    travel_text="With the Brass Auditor stopped, a service gate releases and you pass east to the final sluice.",
                    condition=ViewCondition(required_flags=(AUDITOR_DEFEATED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature("drowned_brass_auditor", "Brass Auditor", "the towering dormant customs engine waiting for valid authority", "Three seal slots sit below the machine's red lens. It will not recognize the abolition of its toll, but it will recognize the obsolete seals of the officials who once had authority over it. PRESENT SEALS when you have all three.", ("auditor", "brass auditor", "machine", "seal slots")),
            ),
        ),
        DROWNED_COLLECTOR_WELL_KEY: RoomAugmentation(
            features=(
                _feature("drowned_final_sluice", "Final Sluice", "a large river gate wheel controlling the forgotten bypass channel", "The wheel is stiff but intact. Opening it will not restore an ancient system; it will repurpose one useful piece of it for the river that exists now. TURN FINAL SLUICE to finish the job.", ("sluice", "wheel", "final sluice")),
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


def install_sablewater_content(world_service=None) -> None:
    for quest in SABLEWATER_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for item in SABLEWATER_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for enemy in SABLEWATER_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for npc in SABLEWATER_NPCS:
        _replace_npc(npc)
    for room in ALL_SABLEWATER_ROOMS:
        _replace_room(room)

    economy.ROOM_RESOURCE_NODE_KEYS[SABLEWATER_REED_FARMS_KEY] = ("cotton_patch", "greenleaf_patch")
    economy.ROOM_RESOURCE_NODE_KEYS[SABLEWATER_SALTGRASS_BEND_KEY] = ("lavender_patch", "bitterroot_cluster")
    economy.LOOT_TABLES[TARIFF_CRAB_KEY] = (economy.LootDrop(DROWNED_BRASS_SCRAP_KEY),)
    economy.LOOT_TABLES[BRASS_CLERK_KEY] = (economy.LootDrop(DROWNED_BRASS_SCRAP_KEY),)
    economy.LOOT_TABLES[SLUICE_WARDEN_KEY] = (economy.LootDrop(DROWNED_BRASS_SCRAP_KEY, 2),)

    if world_service is None:
        return
    for room in ALL_SABLEWATER_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in sablewater_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*ALL_SABLEWATER_ROOM_KEYS, VEYRA_SOUTH_SPRAWL_KEY):
            cache.pop(key, None)


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _ensure_low_water(session) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    if VEYRA_RESIDENT_FLAG not in flags or session.character.level < 6:
        return False
    if SABLEWATER_INTRO_COMPLETE_FLAG in flags:
        return True
    if _quest(session, LOW_WATER_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, LOW_WATER_QUEST_KEY, "talk_ferrymaster")
    return True


async def _talk_ferrymaster(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_NORTH_FERRY_KEY:
        return False
    if not _ensure_low_water(session):
        return False
    q = _quest(session, LOW_WATER_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_ferrymaster":
        session.database.advance_quest(session.character.id, LOW_WATER_QUEST_KEY, "inspect_levee")
        await session.send("Jessa moves two depth pebbles downstream. 'Broken Levee first. EXAMINE BREACH. Then check the Willow Ferry chain. I want to know whether the river moved, the road moved, or we did something stupid.'\r\n")
        return True
    if q and q["status"] == "active" and q["current_step"] == "return_ferrymaster":
        session.database.complete_quest(session.character.id, LOW_WATER_QUEST_KEY)
        session.database.grant_flag(session.character.id, SABLEWATER_INTRO_COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 140)
        if _quest(session, TOLL_NOBODY_OWES_QUEST_KEY) is None:
            session.database.start_quest(session.character.id, TOLL_NOBODY_OWES_QUEST_KEY, "inspect_marker")
        _refresh(session)
        await session.send("Jessa redraws the side channel on her board. 'There. Not a curse. Neglect with excellent masonry.' Low Water, Old Debts complete: 140 XP. Follow the Old Customs Road for the next problem.\r\n")
        return True
    await session.send("Jessa says, 'Depth changes. Notes help. Check your current Sablewater objective.'\r\n")
    return True


async def _inspect_levee(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_BROKEN_LEVEE_KEY:
        return False
    q = _quest(session, LOW_WATER_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_levee":
        return False
    session.database.advance_quest(session.character.id, LOW_WATER_QUEST_KEY, "inspect_chain")
    await session.send("The new breach is only the visible symptom. Old customs stone narrowed the abandoned side channel until flood pressure shifted against this levee. Next: Willow Ferry.\r\n")
    return True


async def _inspect_chain(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_WILLOW_FERRY_KEY:
        return False
    q = _quest(session, LOW_WATER_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_chain":
        return False
    session.database.advance_quest(session.character.id, LOW_WATER_QUEST_KEY, "return_ferrymaster")
    await session.send("The live ferry chain is being pulled off-line by an obsolete customs guide chain exposed by low water. Two separate old systems are now fighting the river together. Return to Jessa.\r\n")
    return True


async def _inspect_marker(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_OLD_CUSTOMS_KEY:
        return False
    q = _quest(session, TOLL_NOBODY_OWES_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_marker":
        return False
    session.database.advance_quest(session.character.id, TOLL_NOBODY_OWES_QUEST_KEY, "inspect_gate")
    await session.send("The marker records the toll's abolition in chisel work newer than the original tariff list. The legal change is clear. Something downstream is simply older than the amendment.\r\n")
    return True


async def _inspect_gate(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_TOLLHOUSE_MOUTH_KEY:
        return False
    q = _quest(session, TOLL_NOBODY_OWES_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_gate":
        return False
    session.database.advance_quest(session.character.id, TOLL_NOBODY_OWES_QUEST_KEY, "talk_diver")
    await session.send("The gate is not magically sealed. It is physically jammed around a customs interlock that still cycles on river power. Nym's rope line bypasses the outer bars. TALK DIVER.\r\n")
    return True


async def _talk_diver(session) -> bool:
    if session.character is None or session.character.current_room != SABLEWATER_TOLLHOUSE_MOUTH_KEY:
        return False
    q = _quest(session, TOLL_NOBODY_OWES_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "talk_diver":
        await session.send("Nym says, 'The rope descent is sound. The rules below are the dangerous part.'\r\n")
        return True
    session.database.complete_quest(session.character.id, TOLL_NOBODY_OWES_QUEST_KEY)
    session.database.grant_flag(session.character.id, TOLLHOUSE_UNLOCKED_FLAG)
    if _quest(session, PRICE_OF_CROSSING_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY, "defeat_warden")
    session.database.add_experience(session.character.id, 170)
    _refresh(session)
    await session.send("Nym clips the descent line to an old mooring ring. 'Down is open. First big maintenance room has a Sluice Warden. It thinks everything living is a blockage.' A Toll Nobody Owes complete: 170 XP. The Drowned Tollhouse is open DOWN.\r\n")
    return True


def _seal_flags(session) -> set[str]:
    return _flags(session).intersection({ARCHIVE_SEAL_FLAG, VAULT_SEAL_FLAG, MAGISTRATE_SEAL_FLAG})


async def _search_seal(session, source: str) -> bool:
    if session.character is None:
        return False
    q = _quest(session, PRICE_OF_CROSSING_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "collect_seals":
        return False
    data = {
        "archive": (DROWNED_FLOODED_ARCHIVE_KEY, ARCHIVE_SEAL_FLAG, "Inside a dry document tube you find an embossed customs authority seal wrapped in a cancellation decree."),
        "vault": (DROWNED_COIN_VAULT_KEY, VAULT_SEAL_FLAG, "Behind an empty coin cage you find an emergency seal kit. The money is gone; the authority stamp remains."),
        "magistrate": (DROWNED_MAGISTRATE_ROOM_KEY, MAGISTRATE_SEAL_FLAG, "The wax-lined desk compartment holds the magistrate's final seal, protected more carefully than the law it represented."),
    }
    room, flag, text = data[source]
    if session.character.current_room != room:
        return False
    if flag in _flags(session):
        await session.send("You already recovered the valid seal from this location.\r\n")
        return True
    session.database.grant_flag(session.character.id, flag)
    session.database.add_item(session.character.id, CUSTOMS_SEAL_KEY, 1)
    found = len(_seal_flags(session))
    if found >= 3:
        session.database.advance_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY, "present_seals")
        text += " You now have all three obsolete seals. Take them to the Brass Tribunal and PRESENT SEALS."
    else:
        text += f" Seal {found}/3 recovered."
    await session.send(text + "\r\n")
    return True


async def _present_seals(session) -> bool:
    if session.character is None or session.character.current_room != DROWNED_BRASS_TRIBUNAL_KEY:
        return False
    q = _quest(session, PRICE_OF_CROSSING_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "present_seals":
        return False
    if session.database.item_quantity(session.character.id, CUSTOMS_SEAL_KEY) < 3:
        await session.send("The Tribunal has three authority slots. You do not have all three obsolete seals.\r\n")
        return True
    session.database.consume_item(session.character.id, CUSTOMS_SEAL_KEY, 3)
    session.database.grant_flag(session.character.id, AUDITOR_AUTHORIZED_FLAG)
    session.database.advance_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY, "defeat_auditor")
    await session.send("The three dead seals fit. The machine accepts authority that history revoked long ago. Locks retract, tariff drums spin, and the Brass Auditor's red lens opens. The obsolete law has finally made itself physically vulnerable. ATTACK AUDITOR.\r\n")
    return True


async def _turn_final_sluice(session) -> bool:
    if session.character is None or session.character.current_room != DROWNED_COLLECTOR_WELL_KEY:
        return False
    q = _quest(session, PRICE_OF_CROSSING_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "open_sluice":
        return False
    session.database.complete_quest(session.character.id, PRICE_OF_CROSSING_QUEST_KEY)
    session.database.grant_flag(session.character.id, DROWNED_TOLLHOUSE_COMPLETE_FLAG)
    session.database.add_item(session.character.id, AUDITOR_GEAR_KEY, 1)
    session.database.add_experience(session.character.id, 350)
    _refresh(session)
    await session.send("You put your weight into the final wheel. Old seals split, the bypass gate rises, and riverwater takes the route nobody has used in generations. Upstream pressure drops by inches rather than miracles. The Price of Crossing complete: 350 XP and a Brass Auditor Gear.\r\n")
    return True


def install_sablewater_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_sablewater_runtime_installed", False):
        return
    install_sablewater_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None and self.character.current_room in SABLEWATER_ROOM_KEYS:
            _ensure_low_water(self)

    async def move_character(self, direction: str) -> None:
        await previous_move(self, direction)
        if self.character is not None and self.character.current_room in SABLEWATER_ROOM_KEYS:
            _ensure_low_water(self)

    def enemy_in_room(self, target_text: str):
        if self.character is not None and self.character.current_room == DROWNED_BRASS_TRIBUNAL_KEY:
            q = _quest(self, PRICE_OF_CROSSING_QUEST_KEY)
            if (
                q
                and q["status"] == "active"
                and q["current_step"] == "defeat_auditor"
                and AUDITOR_AUTHORIZED_FLAG in _flags(self)
                and BRASS_AUDITOR.matches(target_text)
            ):
                return EnemyState(BRASS_AUDITOR)
        return previous_enemy_lookup(self, target_text)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active or self.character is None:
            return
        q = _quest(self, PRICE_OF_CROSSING_QUEST_KEY)
        if key == SLUICE_WARDEN_KEY and q and q["status"] == "active" and q["current_step"] == "defeat_warden":
            self.database.grant_flag(self.character.id, SLUICE_WARDEN_DEFEATED_FLAG)
            self.database.advance_quest(self.character.id, PRICE_OF_CROSSING_QUEST_KEY, "collect_seals")
            await self.send("The Sluice Warden locks in place with both paddle arms raised. The deeper customs interlock still runs. Recover the three obsolete authority seals.\r\n")
        elif key == BRASS_AUDITOR_KEY and q and q["status"] == "active" and q["current_step"] == "defeat_auditor":
            self.database.grant_flag(self.character.id, AUDITOR_DEFEATED_FLAG)
            self.database.advance_quest(self.character.id, PRICE_OF_CROSSING_QUEST_KEY, "open_sluice")
            await self.send("The Brass Auditor's tariff drums spin down to zero. A service gate releases east toward Collector's Well. The last useful task is mechanical, not legal: TURN FINAL SLUICE.\r\n")

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

        if normalized in {"talk ferrymaster", "talk jessa", "speak ferrymaster"}:
            handled = await _talk_ferrymaster(self)
        elif normalized in {"examine breach", "inspect breach", "examine levee"}:
            handled = await _inspect_levee(self)
        elif normalized in {"examine ferry chain", "inspect ferry chain", "examine chain"}:
            handled = await _inspect_chain(self)
        elif normalized in {"examine toll marker", "inspect toll marker", "examine marker"}:
            handled = await _inspect_marker(self)
        elif normalized in {"examine sunken gate", "inspect sunken gate", "examine gate"}:
            handled = await _inspect_gate(self)
        elif normalized in {"talk diver", "talk nym", "speak diver"}:
            handled = await _talk_diver(self)
        elif normalized in {"search ledgers", "search archive", "search tubes"}:
            handled = await _search_seal(self, "archive")
        elif normalized in {"search coin vault", "search cages", "search vault"}:
            handled = await _search_seal(self, "vault")
        elif normalized in {"search magistrate desk", "search desk", "search magistrate"}:
            handled = await _search_seal(self, "magistrate")
        elif normalized in {"present seals", "insert seals", "use seals"}:
            handled = await _present_seals(self)
        elif normalized in {"turn final sluice", "turn sluice", "open final sluice"}:
            handled = await _turn_final_sluice(self)

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
    player_session_class._sablewater_runtime_installed = True
