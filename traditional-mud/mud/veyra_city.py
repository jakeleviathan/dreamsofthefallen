from __future__ import annotations

import re
from dataclasses import replace

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.equipment_system import equipped_item_keys
from mud.greywake_march import (
    GREYWAKE_CHAIN_COMPLETE_FLAG,
    GREYWAKE_THREE_BANNER_KEY,
    GREYWAKE_VEYRA_GATE_KEY,
    LANTERN_FLAG,
    LEDGER_FLAG,
    ROADWARDEN_FLAG,
    SURGE_STATE,
)
from mud.mechanics import FIXED_CLASS_ABILITIES, class_abilities_for_level
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.waymeet_frontier import WAYMEET_CROSSROADS_KEY
from mud.world import NpcDefinition, RoomDefinition


VEYRA_REGION_KEY = "veyra_city"
VEYRA_GATE_WARD_KEY = "veyra_gate_ward"
VEYRA_CARAVAN_COURT_KEY = "veyra_caravan_court"
VEYRA_GRAND_CROSSING_KEY = "veyra_grand_crossing"
VEYRA_RIVERSTEPS_KEY = "veyra_riversteps"
VEYRA_LOWER_QUAYS_KEY = "veyra_lower_quays"
VEYRA_BRASSMARKET_KEY = "veyra_brassmarket"
VEYRA_EXCHANGE_KEY = "veyra_exchange_arcade"
VEYRA_KEYHOUSE_KEY = "veyra_keyhouse_vault"
VEYRA_GUILD_ROW_KEY = "veyra_guildhall_row"
VEYRA_HAMMER_HALL_KEY = "veyra_hammer_hall"
VEYRA_LOOM_HALL_KEY = "veyra_loom_hall"
VEYRA_GREENHALL_KEY = "veyra_greenhall"
VEYRA_FIVE_WAYS_KEY = "veyra_five_ways_yard"
VEYRA_CIVIC_STEPS_KEY = "veyra_civic_steps"
VEYRA_NOTICE_HALL_KEY = "veyra_notice_hall"
VEYRA_THREE_OFFICES_KEY = "veyra_three_offices_court"
VEYRA_ROADWARDEN_OFFICE_KEY = "veyra_roadwarden_house"
VEYRA_LEDGER_OFFICE_KEY = "veyra_deep_ledger_exchange"
VEYRA_LANTERN_OFFICE_KEY = "veyra_lantern_court"
VEYRA_SCHOLARS_RISE_KEY = "veyra_scholars_rise"
VEYRA_OLD_BRIDGE_KEY = "veyra_old_bridge_quarter"
VEYRA_SOUTH_SPRAWL_KEY = "veyra_south_timber_sprawl"
VEYRA_NORTH_WATERWORKS_KEY = "veyra_north_waterworks"
VEYRA_EAST_RIVER_GATE_KEY = "veyra_east_river_gate"
VEYRA_PUBLIC_HEARTH_KEY = "veyra_public_hearth"

VEYRA_ROOM_KEYS = (
    VEYRA_GATE_WARD_KEY,
    VEYRA_CARAVAN_COURT_KEY,
    VEYRA_GRAND_CROSSING_KEY,
    VEYRA_RIVERSTEPS_KEY,
    VEYRA_LOWER_QUAYS_KEY,
    VEYRA_BRASSMARKET_KEY,
    VEYRA_EXCHANGE_KEY,
    VEYRA_KEYHOUSE_KEY,
    VEYRA_GUILD_ROW_KEY,
    VEYRA_HAMMER_HALL_KEY,
    VEYRA_LOOM_HALL_KEY,
    VEYRA_GREENHALL_KEY,
    VEYRA_FIVE_WAYS_KEY,
    VEYRA_CIVIC_STEPS_KEY,
    VEYRA_NOTICE_HALL_KEY,
    VEYRA_THREE_OFFICES_KEY,
    VEYRA_ROADWARDEN_OFFICE_KEY,
    VEYRA_LEDGER_OFFICE_KEY,
    VEYRA_LANTERN_OFFICE_KEY,
    VEYRA_SCHOLARS_RISE_KEY,
    VEYRA_OLD_BRIDGE_KEY,
    VEYRA_SOUTH_SPRAWL_KEY,
    VEYRA_NORTH_WATERWORKS_KEY,
    VEYRA_EAST_RIVER_GATE_KEY,
    VEYRA_PUBLIC_HEARTH_KEY,
)

VEYRA_ARRIVAL_QUEST_KEY = "veyra_first_day"
VEYRA_FACTION_SERVICE_QUEST_KEY = "veyra_faction_service"
VEYRA_RESIDENT_FLAG = "veyra_resident"
VEYRA_FACTION_RANK_FLAG = "veyra_faction_rank_one"
VEYRA_SERVICE_SEAL_KEY = "veyra_service_seal"
VEYRA_RESIDENT_CHIT_KEY = "veyra_resident_chit"

STEWARD_KEY = "veyra_steward_ossa_venn"
REGISTRAR_KEY = "veyra_registrar_mira_noll"
KEYKEEPER_KEY = "veyra_keykeeper_vell_orin"
CRIER_KEY = "veyra_crier_pikka_ninepins"
TRAINER_KEY = "veyra_trainer_coordinator_sable"
ROADWARDEN_CITY_KEY = "veyra_warden_nera_ashfoot"
LEDGER_CITY_KEY = "veyra_factor_ilyr_vael"
LANTERN_CITY_KEY = "veyra_keeper_amel_reed"


VEYRA_ARRIVAL_QUEST = QuestDefinition(
    key=VEYRA_ARRIVAL_QUEST_KEY,
    name="A City Larger Than the Road",
    style="structured",
    minimum_level=8,
    description=(
        "Veyra is the first place where the roads from several peoples become ordinary city streets. "
        "Learn the services that make the city useful before deciding where in it you belong."
    ),
    objective_steps=(
        ("reach_crossing", "Pass the Gate Ward and reach Grand Crossing."),
        ("visit_market", "Visit Brassmarket and see where ordinary goods enter the city economy."),
        ("visit_vault", "Visit the Keyhouse Vault and learn how persistent storage works."),
        ("visit_trainers", "Visit Five Ways Yard and TRAIN to review your class progression."),
        ("read_board", "Go to Notice Hall and READ BOARD."),
        ("report_steward", "Return to Civic Steps and TALK STEWARD."),
        ("complete", "You learned Veyra as a usable place rather than a backdrop."),
    ),
)

VEYRA_FACTION_SERVICE_QUEST = QuestDefinition(
    key=VEYRA_FACTION_SERVICE_QUEST_KEY,
    name="One Office, One Obligation",
    style="structured",
    minimum_level=8,
    description=(
        "The faction you supported in Greywake has a Veyra office. Do one piece of ordinary city work for it. "
        "The reward is not moral victory; it is access to a practical service perk and a deeper place in that organization."
    ),
    objective_steps=(
        ("report_office", "Report to the Veyra office of the faction you supported in Greywake."),
        ("roadwarden_field", "Roadwarden: INSPECT BRIDGE PINS at Grand Crossing."),
        ("ledger_field", "Deep Ledger: APPRAISE CARGO at Brassmarket."),
        ("lantern_water", "Lantern Oath: INSPECT WATER at North Waterworks."),
        ("lantern_notice", "Lantern Oath: POST NOTICE at Notice Hall."),
        ("return_office", "Return to your faction office and report the completed work."),
        ("complete", "Your Greywake alignment now has a concrete Veyra service perk."),
    ),
)

VEYRA_QUESTS = (VEYRA_ARRIVAL_QUEST, VEYRA_FACTION_SERVICE_QUEST)

VEYRA_RESIDENT_CHIT = ItemDefinition(
    key=VEYRA_RESIDENT_CHIT_KEY,
    name="Veyra Resident Chit",
    description=(
        "A small punched brass-and-wood identity chit issued after a newcomer learns Veyra's public services. "
        "It is proof of registration, not citizenship or nobility."
    ),
    category="credential",
    tier=2,
)
VEYRA_SERVICE_SEAL = ItemDefinition(
    key=VEYRA_SERVICE_SEAL_KEY,
    name="Veyra Service Seal",
    description=(
        "A practical service seal stamped by one of Veyra's Greywake offices. The reverse explicitly says the mark records work performed, not ideological purity."
    ),
    category="credential",
    tier=2,
)
VEYRA_ITEMS = (VEYRA_RESIDENT_CHIT, VEYRA_SERVICE_SEAL)


STEWARD = NpcDefinition(
    key=STEWARD_KEY,
    name="Steward Ossa Venn",
    short_description="a civic steward answering three questions at once while keeping a fourth place in a public ledger with one finger",
    room_key=VEYRA_CIVIC_STEPS_KEY,
    role="Veyra newcomer and civic-services guide",
    dialogue=(
        "'A capital is just a place where everybody else's problem eventually gets a desk.'",
        "'If you cannot find a service, read the board. If the board is wrong, tell us. A city is maintenance with witnesses.'",
    ),
)
REGISTRAR = NpcDefinition(
    key=REGISTRAR_KEY,
    name="Registrar Mira Noll",
    short_description="a gate registrar waving farm carts, pilgrims, mercenaries, and diplomats into different lines without raising her voice",
    room_key=VEYRA_GATE_WARD_KEY,
    role="city arrival registrar",
    dialogue=(
        "'Veyra does not care what your homeland calls you until somebody needs the spelling for a receipt.'",
        "'Grand Crossing is east. Market south, vault north, civic offices beyond the bridge. Do not stand in the wagon lane.'",
    ),
)
KEYKEEPER = NpcDefinition(
    key=KEYKEEPER_KEY,
    name="Vell Orin",
    short_description="an Undead keykeeper counting sealed storage tags with the unhurried patience of someone who never needs to blink",
    room_key=VEYRA_KEYHOUSE_KEY,
    role="persistent storage clerk",
    dialogue=(
        "'VAULT shows what you have stored. DEPOSIT and WITHDRAW move ordinary items. Quest items stay with the person whose quest they are ruining.'",
        "'Your possessions are safer here than under an inn bed. This is not the same thing as saying they are interesting.'",
    ),
)
CRIER = NpcDefinition(
    key=CRIER_KEY,
    name="Pikka Ninepins",
    short_description="a Goblin market crier ringing a tiny brass triangle whenever two strangers successfully trade without involving her",
    room_key=VEYRA_EXCHANGE_KEY,
    role="player barter exchange guide",
    dialogue=(
        "'MARKET shows live player listings. LIST 2 IRON ORE FOR 1 COTTON THREAD puts the iron in escrow. FILL 3 takes listing three if you have what they want.'",
        "'No invisible auction money. Goods for goods. If you hate the price, congratulations, you understand a market.'",
    ),
)
TRAINER = NpcDefinition(
    key=TRAINER_KEY,
    name="Sable-of-Five-Ways",
    short_description="a Moon Elf coordinator keeping five very different instructors from all trying to use the same practice circle",
    room_key=VEYRA_FIVE_WAYS_KEY,
    role="class progression trainer and ability guide",
    dialogue=(
        "'TRAIN does not purchase your identity. It tells you what your class can currently do and reminds you that use improves ability skill.'",
        "'Five classes share the yard because enemies rarely organize themselves into five convenient buildings.'",
    ),
)
ROADWARDEN_CITY = NpcDefinition(
    key=ROADWARDEN_CITY_KEY,
    name="Warden Nera Ashfoot",
    short_description="a Troll Roadwarden comparing bridge-pin inspection slips against caravan delay reports",
    room_key=VEYRA_ROADWARDEN_OFFICE_KEY,
    role="Roadwarden Compact Veyra representative",
    dialogue=(
        "'Greywake taught you the argument. Veyra teaches you the paperwork that keeps the argument from dropping a cart into the river.'",
        "'Ranked Roadwardens can use the caravan office for fast RIDE WAYMEET and RIDE GREYWAKE travel.'",
    ),
)
LEDGER_CITY = NpcDefinition(
    key=LEDGER_CITY_KEY,
    name="Factor Ilyr Vael",
    short_description="a Moon Elf factor checking cargo value from two ledgers before signing either one",
    room_key=VEYRA_LEDGER_OFFICE_KEY,
    role="Deep Ledger Consortium Veyra representative",
    dialogue=(
        "'A price is a claim about reality. APPRAISE CARGO before repeating the claim.'",
        "'Ranked Ledger members may keep five barter listings active instead of three. Information should create options.'",
    ),
)
LANTERN_CITY = NpcDefinition(
    key=LANTERN_CITY_KEY,
    name="Keeper Amel Reed",
    short_description="a Forest Elf Lantern keeper pinning public water-test results where anyone can read them",
    room_key=VEYRA_LANTERN_OFFICE_KEY,
    role="Lantern Oath Veyra representative",
    dialogue=(
        "'Containment without public information is just authority asking to be trusted.'",
        "'Ranked Lantern members receive larger Keyhouse vault allotments because clean separation and labeled storage are part of the work.'",
    ),
)
VEYRA_NPCS = (STEWARD, REGISTRAR, KEYKEEPER, CRIER, TRAINER, ROADWARDEN_CITY, LEDGER_CITY, LANTERN_CITY)


def _room(key: str, name: str, description: str, exits: dict[str, str], *, npcs: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=VEYRA_REGION_KEY,
        description=description,
        exits=exits,
        npc_keys=npcs,
        tags=("shared_world", "city", "veyra", "safe", *tags),
    )


VEYRA_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        VEYRA_GATE_WARD_KEY,
        "Gate Ward",
        "The outer checkpoint opens into a broad ward where old stone fortifications have been swallowed by newer timber offices, food stalls, hitching rails, and ten kinds of directional sign. Dwarven freight gauges are painted beside Goblin axle marks. Forest Elf herb bundles hang from awnings. Human hornwork decorates a cheap boarding house. Nobody pauses to explain the mixture because everyone is trying to get somewhere.",
        {"west": GREYWAKE_VEYRA_GATE_KEY, "east": VEYRA_CARAVAN_COURT_KEY, "south": VEYRA_SOUTH_SPRAWL_KEY},
        npcs=(REGISTRAR_KEY,), tags=("arrival", "multicultural"),
    ),
    _room(
        VEYRA_CARAVAN_COURT_KEY,
        "Caravan Court",
        "An enormous paved court sorts incoming traffic by destination rather than origin. Troll drovers argue weight limits with Dwarf teamsters while an Undead clerk records a Forest Elf medicine cart and a Goblin salvage wagon under the same heading: PERISHABLE / DELAY COSTLY.",
        {"west": VEYRA_GATE_WARD_KEY, "east": VEYRA_GRAND_CROSSING_KEY, "north": VEYRA_KEYHOUSE_KEY, "south": VEYRA_BRASSMARKET_KEY},
        tags=("caravan", "roadwarden_perk"),
    ),
    _room(
        VEYRA_GRAND_CROSSING_KEY,
        "Grand Crossing",
        "Veyra's main bridge spans a fast green river on five mismatched stone arches. The oldest pier is Dwarven, one repair bay carries Goblin platework, Moon Elf sighting marks track seasonal load, and fresh timber pins wait beneath a Roadwarden inspection stamp. Above all of it, citizens simply cross: carts, lovers, porters, priests, couriers, children, and people late for work.",
        {"west": VEYRA_CARAVAN_COURT_KEY, "east": VEYRA_CIVIC_STEPS_KEY, "north": VEYRA_RIVERSTEPS_KEY, "south": VEYRA_GUILD_ROW_KEY},
        tags=("bridge", "civic_spine"),
    ),
    _room(
        VEYRA_RIVERSTEPS_KEY,
        "Riversteps",
        "Broad steps descend from the bridge to public landings cut into the river bluff. Washer lines, passenger skiffs, fish baskets, shrine ribbons, and cargo tally boards occupy the same stone without anybody successfully claiming the whole edge.",
        {"south": VEYRA_GRAND_CROSSING_KEY, "east": VEYRA_LOWER_QUAYS_KEY, "north": VEYRA_NORTH_WATERWORKS_KEY},
        tags=("river", "social"),
    ),
    _room(
        VEYRA_LOWER_QUAYS_KEY,
        "Lower Quays",
        "The working riverfront smells of wet rope, lamp oil, fish scales, fruit peel, sawdust, and hot metal from repair braziers. Long barges arrive from settlements that do not appear on any beginner map. Dock crews switch languages without ceremony when a shouted warning needs to travel faster than pride.",
        {"west": VEYRA_RIVERSTEPS_KEY, "east": VEYRA_EAST_RIVER_GATE_KEY},
        tags=("river", "trade", "docks"),
    ),
    _room(
        VEYRA_BRASSMARKET_KEY,
        "Brassmarket",
        "A roofed market fills the old wagon square south of Caravan Court. Brass price tabs hang from hooks because chalk washes away in river weather. The important thing is not exotic luxury but density: ore beside cloth beside herbs beside salvage beside preserved food, with enough buyers present that specialization finally feels practical.",
        {"north": VEYRA_CARAVAN_COURT_KEY, "east": VEYRA_EXCHANGE_KEY, "west": VEYRA_SOUTH_SPRAWL_KEY},
        tags=("market", "economy"),
    ),
    _room(
        VEYRA_EXCHANGE_KEY,
        "Exchange Arcade",
        "An old arcade has been converted into a player-run barter exchange. Numbered iron rings mark escrow lockers behind a public board. The city does not pretend every useful thing has one universal price; it simply records what one adventurer is willing to give for what another adventurer actually has.",
        {"west": VEYRA_BRASSMARKET_KEY},
        npcs=(CRIER_KEY,), tags=("player_market", "economy"),
    ),
    _room(
        VEYRA_KEYHOUSE_KEY,
        "Keyhouse Vault",
        "Thick stone rooms climb the north side of Caravan Court behind three ordinary-looking doors. Inside, storage cages are identified by account marks and character tags instead of social rank. The vault is intentionally boring: dry, labeled, witnessed, and much harder to lose than the bottom of a backpack.",
        {"south": VEYRA_CARAVAN_COURT_KEY},
        npcs=(KEYKEEPER_KEY,), tags=("bank", "storage"),
    ),
    _room(
        VEYRA_GUILD_ROW_KEY,
        "Guildhall Row",
        "Three public craft halls face a stone yard littered with harmless evidence of work: scale, thread ends, herb stems, charcoal grit, cracked practice pieces, and carts collecting finished orders. The halls compete for prestige and share a fire brigade.",
        {"north": VEYRA_GRAND_CROSSING_KEY, "east": VEYRA_HAMMER_HALL_KEY, "west": VEYRA_LOOM_HALL_KEY, "south": VEYRA_GREENHALL_KEY},
        tags=("crafting", "guilds"),
    ),
    _room(
        VEYRA_HAMMER_HALL_KEY,
        "Hammer Hall",
        "A long forge hall holds communal hearths, quench troughs, vices, tongs, and rentable work blocks. Dwarven masters are common here but not exclusive; a Human smith is teaching a Goblin apprentice why one repair should not involve seven rivets when four will hold.",
        {"west": VEYRA_GUILD_ROW_KEY}, tags=("crafting", "forge"),
    ),
    _room(
        VEYRA_LOOM_HALL_KEY,
        "Loom Hall",
        "Tall windows keep dust visible above rows of looms and sewing benches. Forest Elf natural fibers, Moon Elf fine weave, Troll hide stitching, Human uniforms, Goblin patchwork, and Sporekin cured fiber all pass through the same cutting tables.",
        {"east": VEYRA_GUILD_ROW_KEY}, tags=("crafting", "loom"),
    ),
    _room(
        VEYRA_GREENHALL_KEY,
        "Greenhall",
        "Warm glass, drying racks, mortars, copper condensers, and labeled reagent cabinets fill a hall that smells different every ten steps. Alchemists are required to mark dangerous mixtures in symbols legible to people who do not speak their language.",
        {"north": VEYRA_GUILD_ROW_KEY}, tags=("crafting", "alchemy"),
    ),
    _room(
        VEYRA_FIVE_WAYS_KEY,
        "Five Ways Yard",
        "Five training circles overlap around one central water trough. Brutes practice control of space, Wizards precise casting, Druids recovery and field utility, Priests path-specific discipline, and Necromancers containment. The walls carry the same rule in several scripts: YOUR CLASS IS A TOOLKIT, NOT AN EXCUSE TO IGNORE THE ROOM.",
        {"south": VEYRA_CIVIC_STEPS_KEY}, npcs=(TRAINER_KEY,), tags=("trainer", "classes"),
    ),
    _room(
        VEYRA_CIVIC_STEPS_KEY,
        "Civic Steps",
        "Broad steps climb toward a modest council building deliberately smaller than the bridge below it. Petitioners, contractors, faction messengers, street vendors, and bored children occupy more stone than officials do. Veyra's government is visible mostly as queues, notices, repairs, arguments, and somebody eventually signing the correct page.",
        {"west": VEYRA_GRAND_CROSSING_KEY, "east": VEYRA_NOTICE_HALL_KEY, "north": VEYRA_FIVE_WAYS_KEY, "south": VEYRA_THREE_OFFICES_KEY},
        npcs=(STEWARD_KEY,), tags=("civic", "hub"),
    ),
    _room(
        VEYRA_NOTICE_HALL_KEY,
        "Notice Hall",
        "A long public gallery is covered in job slips, missing-person notices, road closures, market disputes, expedition calls, faction reports, performance bills, guild recruitment, and corrections to yesterday's corrections. Blank paper and charcoal are free because stale information costs the city more.",
        {"west": VEYRA_CIVIC_STEPS_KEY, "east": VEYRA_SCHOLARS_RISE_KEY},
        tags=("board", "jobs", "world_events"),
    ),
    _room(
        VEYRA_THREE_OFFICES_KEY,
        "Three Offices Court",
        "Three Greywake organizations maintain offices around one paved court. Their signs face inward, which citizens joke is the only reason the Roadwardens, Deep Ledger, and Lantern Oath remember to look at each other while arguing.",
        {"north": VEYRA_CIVIC_STEPS_KEY, "west": VEYRA_ROADWARDEN_OFFICE_KEY, "south": VEYRA_LEDGER_OFFICE_KEY, "east": VEYRA_LANTERN_OFFICE_KEY},
        tags=("factions", "politics"),
    ),
    _room(
        VEYRA_ROADWARDEN_OFFICE_KEY,
        "Roadwarden House",
        "Bridge pins, road maps, tow-rope samples, axle gauges, storm reports, and caravan delay charts cover a working office that treats transportation as public survival rather than scenery.",
        {"east": VEYRA_THREE_OFFICES_KEY}, npcs=(ROADWARDEN_CITY_KEY,), tags=("faction", "roadwarden"),
    ),
    _room(
        VEYRA_LEDGER_OFFICE_KEY,
        "Deep Ledger Exchange",
        "Assay tables and contract desks share space with a public archive of failed ventures. Profitable discoveries are displayed beside expensive mistakes so nobody can claim the institution only remembers being right.",
        {"north": VEYRA_THREE_OFFICES_KEY}, npcs=(LEDGER_CITY_KEY,), tags=("faction", "deep_ledger"),
    ),
    _room(
        VEYRA_LANTERN_OFFICE_KEY,
        "Lantern Court",
        "Clean-water jars, exposure notices, quarantine maps, witness forms, and medical supply crates fill a bright courtyard office. Every closure order has a review date written on it in large ink.",
        {"west": VEYRA_THREE_OFFICES_KEY}, npcs=(LANTERN_CITY_KEY,), tags=("faction", "lantern_oath"),
    ),
    _room(
        VEYRA_SCHOLARS_RISE_KEY,
        "Scholar's Rise",
        "A steep street climbs through bookbinders, surveyors, translators, instrument repairers, private tutors, and three rival map shops. Moon Elf debate circles form in doorways until delivery carts force them to move.",
        {"west": VEYRA_NOTICE_HALL_KEY, "east": VEYRA_OLD_BRIDGE_KEY}, tags=("learning", "maps"),
    ),
    _room(
        VEYRA_OLD_BRIDGE_KEY,
        "Old Bridge Quarter",
        "The first bridge no longer spans the main river channel, so its stone arches have become buildings. Homes, kitchens, tiny workshops, shrines, and taverns occupy former bridge bays above a narrow canal. The neighborhood is old enough that nobody agrees which culture built the first wall.",
        {"west": VEYRA_SCHOLARS_RISE_KEY, "north": VEYRA_PUBLIC_HEARTH_KEY}, tags=("residential", "old_city"),
    ),
    _room(
        VEYRA_SOUTH_SPRAWL_KEY,
        "South Timber Sprawl",
        "Outside the oldest stone line, timber streets spread downhill toward ferry farms and the southern floodplain. Cheap boarding houses, wagon sheds, boatwrights, ropewalks, and new immigrant businesses appear faster than surveyors can update the ward map.",
        {"north": VEYRA_GATE_WARD_KEY, "east": VEYRA_BRASSMARKET_KEY}, tags=("outer_district", "south_road"),
    ),
    _room(
        VEYRA_NORTH_WATERWORKS_KEY,
        "North Waterworks",
        "Stone channels carry mountain water into settling basins above the city. Dwarf-cut gates regulate flow while Forest Elf reed beds polish overflow and Goblin patch plates mark exactly where old masonry cracked last winter. Public test slates hang at eye level.",
        {"south": VEYRA_RIVERSTEPS_KEY}, tags=("infrastructure", "water"),
    ),
    _room(
        VEYRA_EAST_RIVER_GATE_KEY,
        "East River Gate",
        "A water gate opens onto downstream traffic. Barges queue beneath chain booms while customs clerks inspect cargo for pests, rot, undeclared hazards, and occasionally things that are simply too alive to be called luggage.",
        {"west": VEYRA_LOWER_QUAYS_KEY}, tags=("river_gate", "future_route"),
    ),
    _room(
        VEYRA_PUBLIC_HEARTH_KEY,
        "Public Hearth",
        "A city commonhouse occupies two old bridge arches around a huge shared hearth. Travelers sleep upstairs, locals eat downstairs, and nobody is asked to purchase a drink before using the notice slate or warming wet clothes. This is a legal bind point for adventurers who want Veyra to become home base.",
        {"south": VEYRA_OLD_BRIDGE_KEY}, tags=("rest", "bind", "social"),
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


def veyra_augmentations() -> dict[str, RoomAugmentation]:
    return {
        GREYWAKE_VEYRA_GATE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=VEYRA_GATE_WARD_KEY,
                    name="Veyra Gate Ward",
                    travel_text="The checkpoint opens and you pass east beneath Veyra's layered wall into the Gate Ward.",
                    condition=ViewCondition(required_flags=(GREYWAKE_CHAIN_COMPLETE_FLAG,), min_level=8),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        VEYRA_GRAND_CROSSING_KEY: RoomAugmentation(
            features=(
                _feature(
                    "veyra_bridge_pins",
                    "Bridge Pins",
                    "fresh timber-and-iron bearing pins waiting beneath inspection marks",
                    "The pins are intentionally replaceable sacrificial pieces. Wear appears first at the west bearing, where heavy freight enters from Greywake. Roadwarden chalk marks distinguish harmless polishing from cracks that actually change load behavior.",
                    ("pins", "bridge pins", "bearing pins"),
                ),
            ),
        ),
        VEYRA_BRASSMARKET_KEY: RoomAugmentation(
            features=(
                _feature(
                    "veyra_sample_cargo",
                    "Mixed Cargo Lot",
                    "a disputed mixed lot of ore, cloth, salvage, and sealed herbs",
                    "The lot is a perfect lesson in valuation: some pieces are useful but common, some scarce but damaged, and one sealed herb crate is worth more only if the buyer can verify it stayed dry.",
                    ("cargo", "mixed cargo", "lot"),
                ),
            ),
        ),
        VEYRA_NORTH_WATERWORKS_KEY: RoomAugmentation(
            features=(
                _feature(
                    "veyra_public_water",
                    "Public Test Channel",
                    "a clear side channel beside dated water-quality slates",
                    "The water is visually clear, but the Lantern procedure does not stop at appearance: source gate, settling basin, reed bed, smell, residue, and the date of the last upstream repair are all recorded before anyone writes SAFE.",
                    ("water", "channel", "test channel", "slates"),
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


def install_veyra_content(world_service=None) -> None:
    for quest in VEYRA_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in VEYRA_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for npc in VEYRA_NPCS:
        _replace_npc(npc)
    for room in VEYRA_ROOMS:
        _replace_room(room)

    economy.ROOM_STATIONS[VEYRA_HAMMER_HALL_KEY] = ("forge",)
    economy.ROOM_STATIONS[VEYRA_LOOM_HALL_KEY] = ("loom",)
    economy.ROOM_STATIONS[VEYRA_GREENHALL_KEY] = ("mortar_and_pestle", "alchemy_table")

    if world_service is None:
        return
    for room in VEYRA_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in veyra_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*VEYRA_ROOM_KEYS, GREYWAKE_VEYRA_GATE_KEY):
            cache.pop(key, None)


def ensure_veyra_service_tables(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS veyra_vault_items (
                character_id INTEGER NOT NULL,
                item_key TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                PRIMARY KEY (character_id, item_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS veyra_market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_character_id INTEGER NOT NULL,
                offered_item_key TEXT NOT NULL,
                offered_quantity INTEGER NOT NULL CHECK (offered_quantity > 0),
                wanted_item_key TEXT NOT NULL,
                wanted_quantity INTEGER NOT NULL CHECK (wanted_quantity > 0),
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                filled_by_character_id INTEGER,
                filled_at TEXT,
                FOREIGN KEY (seller_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (filled_by_character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_veyra_market_active
            ON veyra_market_listings(status, id);
            """
        )


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _supported_faction(session) -> str | None:
    flags = _flags(session)
    if ROADWARDEN_FLAG in flags:
        return "roadwarden"
    if LEDGER_FLAG in flags:
        return "ledger"
    if LANTERN_FLAG in flags:
        return "lantern"
    return None


def _ensure_arrival_quest(session) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    if GREYWAKE_CHAIN_COMPLETE_FLAG not in flags or session.character.level < 8:
        return False
    if VEYRA_RESIDENT_FLAG in flags:
        return True
    if _quest(session, VEYRA_ARRIVAL_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY, "reach_crossing")
    return True


def _advance_arrival_by_room(session) -> str | None:
    if session.character is None:
        return None
    q = _quest(session, VEYRA_ARRIVAL_QUEST_KEY)
    if not q or q["status"] != "active":
        return None
    transitions = {
        ("reach_crossing", VEYRA_GRAND_CROSSING_KEY): ("visit_market", "Grand Crossing turns the city from a gate into a network. Next: visit Brassmarket."),
        ("visit_market", VEYRA_BRASSMARKET_KEY): ("visit_vault", "Brassmarket shows why specialization works here: there are enough buyers and sellers for materials to move. Next: visit the Keyhouse Vault."),
        ("visit_vault", VEYRA_KEYHOUSE_KEY): ("visit_trainers", "Vell points out the dry storage cages. VAULT, DEPOSIT, and WITHDRAW are persistent here. Next: visit Five Ways Yard."),
        ("visit_trainers", VEYRA_FIVE_WAYS_KEY): ("visit_trainers", "Five class circles share one yard. Use TRAIN here to review your current toolkit."),
        ("read_board", VEYRA_NOTICE_HALL_KEY): ("read_board", "The Notice Hall is where Veyra turns changing world state into public information. READ BOARD when you are ready."),
    }
    transition = transitions.get((q["current_step"], session.character.current_room))
    if transition is None:
        return None
    next_step, text = transition
    if next_step != q["current_step"]:
        session.database.advance_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY, next_step)
    return text


def _item_name(item_key: str) -> str:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    return item.name if item is not None else item_key.replace("_", " ").title()


def _resolve_item(text: str) -> ItemDefinition | None:
    normalized = " ".join(text.strip().lower().replace("_", " ").split())
    for item in crafting.ITEMS_BY_KEY.values():
        if normalized in {
            " ".join(item.key.lower().replace("_", " ").split()),
            " ".join(item.name.lower().split()),
        }:
            return item
    return None


def _equipped_reserve(session, item_key: str) -> int:
    if session.character is None:
        return 0
    equipped = equipped_item_keys(session.database, session.character.id)
    return 1 if item_key in equipped.values() else 0


def _vault_capacity(session) -> int:
    flags = _flags(session)
    if LANTERN_FLAG in flags and VEYRA_FACTION_RANK_FLAG in flags:
        return 60
    return 40


def _listing_capacity(session) -> int:
    flags = _flags(session)
    if LEDGER_FLAG in flags and VEYRA_FACTION_RANK_FLAG in flags:
        return 5
    return 3


def _vault_rows(database, character_id: int) -> list[dict[str, int | str]]:
    ensure_veyra_service_tables(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT item_key, quantity FROM veyra_vault_items WHERE character_id = ? AND quantity > 0 ORDER BY item_key",
            (character_id,),
        ).fetchall()
    return [{"item_key": str(row["item_key"]), "quantity": int(row["quantity"])} for row in rows]


def _vault_total(database, character_id: int) -> int:
    ensure_veyra_service_tables(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total FROM veyra_vault_items WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    return int(row["total"])


def deposit_to_vault(session, item_text: str, quantity: int = 1) -> tuple[bool, str]:
    if session.character is None:
        return False, "No active character."
    ensure_veyra_service_tables(session.database)
    item = _resolve_item(item_text)
    if item is None:
        return False, "The Keyhouse cannot identify that item. Use the exact inventory name."
    if item.category == "quest_item":
        return False, "Quest items stay with you; the Keyhouse will not store something another objective expects in your hands."
    quantity = max(1, quantity)
    inventory = session.database.item_quantity(session.character.id, item.key)
    available = max(0, inventory - _equipped_reserve(session, item.key))
    if available < quantity:
        return False, f"You only have {available} unstowed, unequipped {_item_name(item.key)} available."
    used = _vault_total(session.database, session.character.id)
    capacity = _vault_capacity(session)
    if used + quantity > capacity:
        return False, f"Your Veyra vault allotment is {capacity} item-units; {used} are already stored."
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (session.character.id, item.key),
        ).fetchone()
        if row is None or int(row["quantity"]) - _equipped_reserve(session, item.key) < quantity:
            return False, "Your inventory changed before the deposit could be recorded."
        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute("UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?", (remaining, session.character.id, item.key))
        else:
            db.execute("DELETE FROM character_items WHERE character_id = ? AND item_key = ?", (session.character.id, item.key))
        db.execute(
            """
            INSERT INTO veyra_vault_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (session.character.id, item.key, quantity),
        )
    return True, f"Stored {quantity} x {item.name}. Vault use: {used + quantity}/{capacity}."


def withdraw_from_vault(session, item_text: str, quantity: int = 1) -> tuple[bool, str]:
    if session.character is None:
        return False, "No active character."
    ensure_veyra_service_tables(session.database)
    item = _resolve_item(item_text)
    if item is None:
        return False, "The Keyhouse cannot identify that item."
    quantity = max(1, quantity)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM veyra_vault_items WHERE character_id = ? AND item_key = ?",
            (session.character.id, item.key),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            return False, f"Your vault does not contain {quantity} x {item.name}."
        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute("UPDATE veyra_vault_items SET quantity = ? WHERE character_id = ? AND item_key = ?", (remaining, session.character.id, item.key))
        else:
            db.execute("DELETE FROM veyra_vault_items WHERE character_id = ? AND item_key = ?", (session.character.id, item.key))
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (session.character.id, item.key, quantity),
        )
    return True, f"Withdrew {quantity} x {item.name}."


def create_market_listing(session, offered_text: str, offered_quantity: int, wanted_text: str, wanted_quantity: int) -> tuple[bool, str]:
    if session.character is None:
        return False, "No active character."
    ensure_veyra_service_tables(session.database)
    offered = _resolve_item(offered_text)
    wanted = _resolve_item(wanted_text)
    if offered is None or wanted is None:
        return False, "The Exchange could not identify one of those item names."
    if offered.category == "quest_item" or wanted.category == "quest_item":
        return False, "Quest items cannot be placed on the public exchange."
    if offered.key == wanted.key:
        return False, "Pikka refuses to post a listing that asks for the same thing it offers."
    offered_quantity = max(1, offered_quantity)
    wanted_quantity = max(1, wanted_quantity)
    available = session.database.item_quantity(session.character.id, offered.key) - _equipped_reserve(session, offered.key)
    if available < offered_quantity:
        return False, f"You only have {max(0, available)} unequipped {offered.name} available."
    with session.database.connect() as db:
        active = db.execute(
            "SELECT COUNT(*) AS n FROM veyra_market_listings WHERE seller_character_id = ? AND status = 'active'",
            (session.character.id,),
        ).fetchone()
        capacity = _listing_capacity(session)
        if int(active["n"]) >= capacity:
            return False, f"You already use all {capacity} of your active Veyra listing slots."
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?", (session.character.id, offered.key)).fetchone()
        if row is None or int(row["quantity"]) - _equipped_reserve(session, offered.key) < offered_quantity:
            return False, "Your inventory changed before the Exchange could escrow the goods."
        remaining = int(row["quantity"]) - offered_quantity
        if remaining:
            db.execute("UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?", (remaining, session.character.id, offered.key))
        else:
            db.execute("DELETE FROM character_items WHERE character_id = ? AND item_key = ?", (session.character.id, offered.key))
        cursor = db.execute(
            """
            INSERT INTO veyra_market_listings
            (seller_character_id, offered_item_key, offered_quantity, wanted_item_key, wanted_quantity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session.character.id, offered.key, offered_quantity, wanted.key, wanted_quantity),
        )
        listing_id = int(cursor.lastrowid)
    return True, f"Listing {listing_id} posted: {offered_quantity} x {offered.name} FOR {wanted_quantity} x {wanted.name}."


def list_market(database) -> list[dict[str, int | str]]:
    ensure_veyra_service_tables(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT l.id, l.seller_character_id, c.name AS seller_name,
                   l.offered_item_key, l.offered_quantity, l.wanted_item_key, l.wanted_quantity
            FROM veyra_market_listings l
            JOIN characters c ON c.id = l.seller_character_id
            WHERE l.status = 'active'
            ORDER BY l.id
            """
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "seller_character_id": int(row["seller_character_id"]),
            "seller_name": str(row["seller_name"]),
            "offered_item_key": str(row["offered_item_key"]),
            "offered_quantity": int(row["offered_quantity"]),
            "wanted_item_key": str(row["wanted_item_key"]),
            "wanted_quantity": int(row["wanted_quantity"]),
        }
        for row in rows
    ]


def fill_market_listing(session, listing_id: int) -> tuple[bool, str]:
    if session.character is None:
        return False, "No active character."
    ensure_veyra_service_tables(session.database)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM veyra_market_listings WHERE id = ? AND status = 'active'",
            (listing_id,),
        ).fetchone()
        if row is None:
            return False, "That listing is no longer active."
        seller_id = int(row["seller_character_id"])
        if seller_id == session.character.id:
            return False, "You cannot fill your own listing. Use CANCEL LISTING instead."
        wanted_key = str(row["wanted_item_key"])
        wanted_qty = int(row["wanted_quantity"])
        offered_key = str(row["offered_item_key"])
        offered_qty = int(row["offered_quantity"])
        buyer_row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (session.character.id, wanted_key),
        ).fetchone()
        reserved = _equipped_reserve(session, wanted_key)
        if buyer_row is None or int(buyer_row["quantity"]) - reserved < wanted_qty:
            return False, f"You do not have {wanted_qty} unequipped {_item_name(wanted_key)} to fill that listing."
        remaining = int(buyer_row["quantity"]) - wanted_qty
        if remaining:
            db.execute("UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?", (remaining, session.character.id, wanted_key))
        else:
            db.execute("DELETE FROM character_items WHERE character_id = ? AND item_key = ?", (session.character.id, wanted_key))
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (seller_id, wanted_key, wanted_qty),
        )
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (session.character.id, offered_key, offered_qty),
        )
        db.execute(
            "UPDATE veyra_market_listings SET status = 'filled', filled_by_character_id = ?, filled_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session.character.id, listing_id),
        )
    return True, f"Filled listing {listing_id}: received {offered_qty} x {_item_name(offered_key)} for {wanted_qty} x {_item_name(wanted_key)}."


def cancel_market_listing(session, listing_id: int) -> tuple[bool, str]:
    if session.character is None:
        return False, "No active character."
    ensure_veyra_service_tables(session.database)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT offered_item_key, offered_quantity FROM veyra_market_listings WHERE id = ? AND seller_character_id = ? AND status = 'active'",
            (listing_id, session.character.id),
        ).fetchone()
        if row is None:
            return False, "You do not own an active listing with that number."
        item_key = str(row["offered_item_key"])
        qty = int(row["offered_quantity"])
        db.execute("UPDATE veyra_market_listings SET status = 'cancelled' WHERE id = ?", (listing_id,))
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (session.character.id, item_key, qty),
        )
    return True, f"Cancelled listing {listing_id}; {qty} x {_item_name(item_key)} returned from escrow."


async def _show_vault(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_KEYHOUSE_KEY:
        return False
    rows = _vault_rows(session.database, session.character.id)
    used = _vault_total(session.database, session.character.id)
    capacity = _vault_capacity(session)
    if not rows:
        await session.send(f"Veyra Vault — {used}/{capacity} item-units used. Empty.\r\n")
        return True
    lines = [f"Veyra Vault — {used}/{capacity} item-units used:"]
    lines.extend(f" - {entry['quantity']} x {_item_name(str(entry['item_key']))}" for entry in rows)
    await session.send("\r\n".join(lines) + "\r\n")
    return True


async def _show_market(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_EXCHANGE_KEY:
        return False
    rows = list_market(session.database)
    if not rows:
        await session.send("Veyra Exchange: no active player listings. Use LIST <qty> <item> FOR <qty> <item>.\r\n")
        return True
    lines = ["Veyra Exchange — active player barter listings:"]
    for row in rows:
        lines.append(
            f" #{row['id']} {row['seller_name']}: {row['offered_quantity']} x {_item_name(str(row['offered_item_key']))} FOR {row['wanted_quantity']} x {_item_name(str(row['wanted_item_key']))}"
        )
    lines.append("Use FILL <id> to accept or CANCEL LISTING <id> to reclaim your own escrow.")
    await session.send("\r\n".join(lines) + "\r\n")
    return True


async def _train(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_FIVE_WAYS_KEY:
        return False
    class_key = session.character.character_class or ""
    available = class_abilities_for_level(class_key, session.character.level, session.character.deity_key)
    lines = [f"Five Ways training review — Level {session.character.level} {class_key.replace('_', ' ').title()}:"]
    if available:
        lines.extend(
            f" - {ability.name} (level {ability.unlock_level or 1}): {ability.description}"
            for ability in available
        )
    else:
        lines.append(" - No fixed class abilities are currently registered for this path.")
    if class_key != "priest":
        future = [
            ability for ability in FIXED_CLASS_ABILITIES.get(class_key, ())
            if ability.unlock_level is not None and ability.unlock_level > session.character.level
        ]
        if future:
            next_ability = min(future, key=lambda ability: ability.unlock_level or 999)
            lines.append(f"Next known unlock: {next_ability.name} at level {next_ability.unlock_level}.")
    lines.append("Abilities improve through use; Veyra's trainers explain and practice them rather than selling talent points.")
    await session.send("\r\n".join(lines) + "\r\n")
    q = _quest(session, VEYRA_ARRIVAL_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "visit_trainers":
        session.database.advance_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY, "read_board")
    return True


async def _read_board(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_NOTICE_HALL_KEY:
        return False
    ensure_veyra_service_tables(session.database)
    active_listings = len(list_market(session.database))
    faction = _supported_faction(session) or "unaffiliated"
    surge = f"ACTIVE — {SURGE_STATE.remaining} instability remains" if SURGE_STATE.active else "quiet"
    await session.send(
        "VEYRA PUBLIC BOARD\r\n"
        f" - Greywake: {surge}.\r\n"
        f" - Your Greywake alignment: {faction}.\r\n"
        f" - Exchange: {active_listings} active player barter listing(s).\r\n"
        " - South Timber Sprawl: ferry crews request experienced travelers for floodplain work.\r\n"
        " - East River Gate: downstream traffic normal; old toll-island charts are being recopied.\r\n"
        " - Guildhall Row: forge, loom, mortar, and alchemy stations open to working adventurers.\r\n"
    )
    q = _quest(session, VEYRA_ARRIVAL_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "read_board":
        session.database.advance_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY, "report_steward")
    return True


async def _talk_steward(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_CIVIC_STEPS_KEY:
        return False
    q = _quest(session, VEYRA_ARRIVAL_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "report_steward":
        await session.send("Ossa says, 'Use the city. Market, vault, trainers, board. Then come back when those words mean rooms instead of menu entries.'\r\n")
        return True
    session.database.complete_quest(session.character.id, VEYRA_ARRIVAL_QUEST_KEY)
    session.database.grant_flag(session.character.id, VEYRA_RESIDENT_FLAG)
    session.database.add_item(session.character.id, VEYRA_RESIDENT_CHIT_KEY, 1)
    session.database.add_experience(session.character.id, 250)
    if _quest(session, VEYRA_FACTION_SERVICE_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "report_office")
    _refresh(session)
    await session.send(
        "Ossa punches a resident chit and slides it across the desk. 'Now you know where to put things, trade things, learn things, and find out what changed while you were gone. That is enough to start belonging.' A City Larger Than the Road complete: 250 XP and a Veyra Resident Chit. Your Greywake faction now has a city-service quest.\r\n"
    )
    return True


async def _talk_faction_office(session, faction: str) -> bool:
    if session.character is None:
        return False
    office = {
        "roadwarden": VEYRA_ROADWARDEN_OFFICE_KEY,
        "ledger": VEYRA_LEDGER_OFFICE_KEY,
        "lantern": VEYRA_LANTERN_OFFICE_KEY,
    }[faction]
    if session.character.current_room != office:
        return False
    if _supported_faction(session) != faction:
        await session.send("This office will still answer ordinary questions, but your Greywake service alignment belongs to another organization.\r\n")
        return True
    q = _quest(session, VEYRA_FACTION_SERVICE_QUEST_KEY)
    if q is None:
        session.database.start_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "report_office")
        q = _quest(session, VEYRA_FACTION_SERVICE_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "report_office":
        next_step = {"roadwarden": "roadwarden_field", "ledger": "ledger_field", "lantern": "lantern_water"}[faction]
        session.database.advance_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, next_step)
        text = {
            "roadwarden": "Nera hands you an inspection slip. 'Grand Crossing. Do not tell me the bridge looks sturdy. INSPECT BRIDGE PINS and tell me which bearing is wearing first.'",
            "ledger": "Ilyr points toward Brassmarket. 'APPRAISE CARGO on the mixed lot. Value what is actually there, including uncertainty.'",
            "lantern": "Amel hands you a blank public test form. 'INSPECT WATER at North Waterworks. If the evidence is clean, we still publish the evidence.'",
        }[faction]
        await session.send(text + "\r\n")
        return True
    if q and q["status"] == "active" and q["current_step"] == "return_office":
        session.database.complete_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY)
        session.database.grant_flag(session.character.id, VEYRA_FACTION_RANK_FLAG)
        session.database.add_item(session.character.id, VEYRA_SERVICE_SEAL_KEY, 1)
        session.database.add_experience(session.character.id, 180)
        _refresh(session)
        perk = {
            "roadwarden": "Caravan Court now recognizes RIDE WAYMEET and RIDE GREYWAKE as ranked Roadwarden transit privileges.",
            "ledger": "Your Veyra Exchange active-listing cap rises from 3 to 5.",
            "lantern": "Your Keyhouse vault allotment rises from 40 to 60 item-units.",
        }[faction]
        await session.send(f"Your city service report is accepted. One Office, One Obligation complete: 180 XP and a Veyra Service Seal. {perk}\r\n")
        return True
    await session.send("Your faction office has no new service step for you right now. FACTION PERK summarizes your current benefit.\r\n")
    return True


async def _do_faction_fieldwork(session, action: str) -> bool:
    if session.character is None:
        return False
    q = _quest(session, VEYRA_FACTION_SERVICE_QUEST_KEY)
    if not q or q["status"] != "active":
        return False
    step = q["current_step"]
    if action == "bridge" and session.character.current_room == VEYRA_GRAND_CROSSING_KEY and step == "roadwarden_field":
        session.database.advance_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "return_office")
        await session.send("You inspect polishing, end grain, iron collars, and the chalk datum. The west bearing pin is wearing faster than its twin, not dangerously yet but enough to schedule replacement before freight season. You record the fact instead of waiting for a dramatic failure.\r\n")
        return True
    if action == "cargo" and session.character.current_room == VEYRA_BRASSMARKET_KEY and step == "ledger_field":
        session.database.advance_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "return_office")
        await session.send("You separate price from usefulness: common ore is sound, cloth is ordinary, salvage is repairable, and the sealed herb crate carries value only if its dry-chain claim can be verified. Your appraisal includes the uncertainty instead of hiding it.\r\n")
        return True
    if action == "water" and session.character.current_room == VEYRA_NORTH_WATERWORKS_KEY and step == "lantern_water":
        session.database.advance_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "lantern_notice")
        await session.send("You trace source gate, settling basin, reed bed, smell, residue, and the date of the last upstream repair. The channel is clean by every check available today. The next step is not silence: POST NOTICE at Notice Hall.\r\n")
        return True
    if action == "notice" and session.character.current_room == VEYRA_NOTICE_HALL_KEY and step == "lantern_notice":
        session.database.advance_quest(session.character.id, VEYRA_FACTION_SERVICE_QUEST_KEY, "return_office")
        await session.send("You post the clean-water result with date, method, and the limits of what was tested. The notice does not say TRUST US. It says what was checked and when it should be checked again.\r\n")
        return True
    return False


async def _bind_veyra(session) -> bool:
    if session.character is None or session.character.current_room != VEYRA_PUBLIC_HEARTH_KEY:
        return False
    session.database.set_bind_room(session.character.id, VEYRA_PUBLIC_HEARTH_KEY)
    _refresh(session)
    await session.send("You register the Public Hearth as your bind point. If death returns you to safety, Veyra is now home base.\r\n")
    return True


async def _faction_perk(session) -> bool:
    if session.character is None or session.character.current_room not in VEYRA_ROOM_KEYS:
        return False
    faction = _supported_faction(session)
    ranked = VEYRA_FACTION_RANK_FLAG in _flags(session)
    if faction is None:
        await session.send("You do not currently carry a Greywake faction alignment.\r\n")
        return True
    if not ranked:
        await session.send(f"Your {faction} alignment is recognized, but complete One Office, One Obligation before its Veyra service perk activates.\r\n")
        return True
    text = {
        "roadwarden": "Roadwarden Rank I: RIDE WAYMEET and RIDE GREYWAKE from Caravan Court.",
        "ledger": "Deep Ledger Rank I: up to 5 simultaneous Exchange listings instead of 3.",
        "lantern": "Lantern Oath Rank I: 60 Keyhouse item-units instead of 40.",
    }[faction]
    await session.send(text + "\r\n")
    return True


async def _ride(session, destination: str) -> bool:
    if session.character is None or session.character.current_room != VEYRA_CARAVAN_COURT_KEY:
        return False
    flags = _flags(session)
    if ROADWARDEN_FLAG not in flags or VEYRA_FACTION_RANK_FLAG not in flags:
        await session.send("The long-haul dispatch desk reserves its priority rides for ranked Roadwarden service. Ordinary roads remain open on foot.\r\n")
        return True
    target = WAYMEET_CROSSROADS_KEY if destination == "waymeet" else GREYWAKE_THREE_BANNER_KEY
    session.database.set_character_room(session.character.id, target)
    _refresh(session)
    await session.send(f"A Roadwarden dispatch wagon carries you through the maintained corridor to {destination.title()}.\r\n")
    await session.show_current_room()
    return True


async def _city_guide(session) -> bool:
    if session.character is None or session.character.current_room not in VEYRA_ROOM_KEYS:
        return False
    await session.send(
        "VEYRA CITY SERVICES\r\n"
        " - Exchange Arcade: MARKET, LIST <qty> <item> FOR <qty> <item>, FILL <id>, CANCEL LISTING <id>.\r\n"
        " - Keyhouse Vault: VAULT, DEPOSIT <qty> <item>, WITHDRAW <qty> <item>.\r\n"
        " - Guildhall Row: Hammer Hall forge, Loom Hall loom, Greenhall alchemy stations.\r\n"
        " - Five Ways Yard: TRAIN.\r\n"
        " - Notice Hall: READ BOARD.\r\n"
        " - Three Offices Court: faction service and FACTION PERK.\r\n"
        " - Public Hearth: BIND VEYRA.\r\n"
    )
    return True


def install_veyra_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_veyra_city_runtime_installed", False):
        return
    install_veyra_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None and self.character.current_room in VEYRA_ROOM_KEYS:
            ensure_veyra_service_tables(self.database)
            _ensure_arrival_quest(self)

    async def move_character(self, direction: str) -> None:
        await previous_move(self, direction)
        if self.character is None or self.character.current_room not in VEYRA_ROOM_KEYS:
            return
        ensure_veyra_service_tables(self.database)
        _ensure_arrival_quest(self)
        text = _advance_arrival_by_room(self)
        if text:
            await self.send(text + "\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        room = self.character.current_room or ""
        handled = False

        if normalized in {"city", "veyra", "city services", "veyra services"}:
            handled = await _city_guide(self)
        elif normalized in {"read board", "board", "read notices"}:
            handled = await _read_board(self)
        elif normalized in {"train", "talk trainer", "talk sable"}:
            handled = await _train(self)
        elif normalized in {"talk steward", "talk ossa"}:
            handled = await _talk_steward(self)
        elif normalized in {"vault", "bank", "storage"}:
            handled = await _show_vault(self)
        elif room == VEYRA_KEYHOUSE_KEY and normalized.startswith("deposit "):
            match = re.fullmatch(r"deposit\s+(?:(\d+)\s+)?(.+)", normalized)
            if match:
                ok, text = deposit_to_vault(self, match.group(2), int(match.group(1) or 1))
                await self.send(text + "\r\n")
                handled = True
        elif room == VEYRA_KEYHOUSE_KEY and normalized.startswith("withdraw "):
            match = re.fullmatch(r"withdraw\s+(?:(\d+)\s+)?(.+)", normalized)
            if match:
                ok, text = withdraw_from_vault(self, match.group(2), int(match.group(1) or 1))
                await self.send(text + "\r\n")
                handled = True
        elif normalized in {"market", "exchange", "market listings"}:
            handled = await _show_market(self)
        elif room == VEYRA_EXCHANGE_KEY and normalized.startswith("list "):
            match = re.fullmatch(r"list\s+(\d+)\s+(.+?)\s+for\s+(\d+)\s+(.+)", normalized)
            if match:
                ok, text = create_market_listing(self, match.group(2), int(match.group(1)), match.group(4), int(match.group(3)))
                await self.send(text + "\r\n")
                handled = True
        elif room == VEYRA_EXCHANGE_KEY and normalized.startswith("fill "):
            match = re.fullmatch(r"fill\s+(\d+)", normalized)
            if match:
                ok, text = fill_market_listing(self, int(match.group(1)))
                await self.send(text + "\r\n")
                handled = True
        elif room == VEYRA_EXCHANGE_KEY and normalized.startswith("cancel listing "):
            match = re.fullmatch(r"cancel listing\s+(\d+)", normalized)
            if match:
                ok, text = cancel_market_listing(self, int(match.group(1)))
                await self.send(text + "\r\n")
                handled = True
        elif normalized in {"talk warden", "talk nera", "talk roadwarden"}:
            handled = await _talk_faction_office(self, "roadwarden")
        elif normalized in {"talk factor", "talk ilyr", "talk ledger"}:
            handled = await _talk_faction_office(self, "ledger")
        elif normalized in {"talk keeper", "talk amel", "talk lantern"}:
            handled = await _talk_faction_office(self, "lantern")
        elif normalized in {"inspect bridge pins", "inspect pins", "check bridge pins"}:
            handled = await _do_faction_fieldwork(self, "bridge")
        elif normalized in {"appraise cargo", "inspect cargo", "value cargo"}:
            handled = await _do_faction_fieldwork(self, "cargo")
        elif normalized in {"inspect water", "test water", "check water"}:
            handled = await _do_faction_fieldwork(self, "water")
        elif normalized in {"post notice", "post water notice"}:
            handled = await _do_faction_fieldwork(self, "notice")
        elif normalized in {"faction perk", "city faction", "veyra faction"}:
            handled = await _faction_perk(self)
        elif normalized in {"bind veyra", "bind city", "set bind"}:
            handled = await _bind_veyra(self)
        elif normalized in {"ride waymeet", "caravan waymeet"}:
            handled = await _ride(self, "waymeet")
        elif normalized in {"ride greywake", "caravan greywake"}:
            handled = await _ride(self, "greywake")

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
    player_session_class._veyra_city_runtime_installed = True
