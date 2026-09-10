from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


DWARF_REGION_KEY = "dwarven_mountain_industry"
DWARF_START_ROOM_KEY = "dwarf_foundry_concourse"
DWARF_REGISTRY_HALL_KEY = "dwarf_civic_registry"
DWARF_UNION_HALL_KEY = "dwarf_union_hall"
DWARF_PRESSURE_GALLERY_KEY = "dwarf_pressure_gallery"
DWARF_LIFT_PLATFORM_KEY = "dwarf_grand_lift_platform"
DWARF_TRADE_ARCADE_KEY = "dwarf_trade_house_arcade"
DWARF_WORKSHOP_TIER_KEY = "dwarf_workshop_tier"
DWARF_UPPER_FREIGHT_KEY = "dwarf_upper_freight_deck"

DWARF_START_ROOM_KEYS = (
    DWARF_START_ROOM_KEY,
    DWARF_REGISTRY_HALL_KEY,
    DWARF_UNION_HALL_KEY,
    DWARF_PRESSURE_GALLERY_KEY,
    DWARF_LIFT_PLATFORM_KEY,
    DWARF_TRADE_ARCADE_KEY,
    DWARF_WORKSHOP_TIER_KEY,
    DWARF_UPPER_FREIGHT_KEY,
)

DWARF_REGISTRY_FLAG = "dwarf_first_work_order_registered"
DWARF_UNION_FLAG = "dwarf_first_work_order_countersealed"
DWARF_PRESSURE_FLAG = "dwarf_pressure_training_complete"
DWARF_LIFT_FLAG = "dwarf_lift_training_complete"
DWARF_CIVIC_CLEARANCE_FLAG = "dwarf_civic_work_clearance"
DWARF_FIRST_OBLIGATION_FLAG = "dwarf_first_obligation_completed"


DWARF_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=DWARF_START_ROOM_KEY,
        name="Foundry Concourse",
        region_key=DWARF_REGION_KEY,
        description=(
            "A vaulted civic concourse has been cut directly through the mountain, broad enough for freight carts to pass three abreast. "
            "Steam mains run overhead in disciplined rows, each pipe painted with inspection bands and fitted with brass service plates. "
            "Clock faces, shift boards, union notices, trade-house directories, and numbered work-order windows cover the stone walls without making the place feel disorderly. "
            "The mountain city is loud, crowded, and intensely organized: hammers ring below, lift cables hum above, and every moving load seems to have both a destination and paperwork."
        ),
        exits={
            "east": DWARF_REGISTRY_HALL_KEY,
            "north": DWARF_LIFT_PLATFORM_KEY,
            "west": DWARF_TRADE_ARCADE_KEY,
            "south": DWARF_WORKSHOP_TIER_KEY,
        },
        tags=("dwarf_start", "safe", "industrial_city", "steam", "civic_core", "cosmopolitan"),
    ),
    RoomDefinition(
        key=DWARF_REGISTRY_HALL_KEY,
        name="Civic Registry Hall",
        region_key=DWARF_REGION_KEY,
        description=(
            "Long stone counters divide this hall into numbered service bays beneath signs for work orders, inspections, freight claims, apprenticeships, and civic permits. "
            "Clerks move paper with the speed of practiced machinists, feeding completed forms into brass document lifts that vanish into the walls. "
            "Nothing here suggests that bureaucracy is separate from industry; records are treated as another load-bearing system that keeps thousands of workers from colliding with one another."
        ),
        exits={"west": DWARF_START_ROOM_KEY, "north": DWARF_UNION_HALL_KEY},
        npc_keys=("dwarf_registrar_helga_brassmeasure",),
        tags=("safe", "registry", "bureaucracy", "civic_core", "work_orders"),
    ),
    RoomDefinition(
        key=DWARF_UNION_HALL_KEY,
        name="Ironworkers' Union Hall",
        region_key=DWARF_REGION_KEY,
        description=(
            "A heavy but welcoming hall occupies an old machine chamber above the registry. Work crews eat at long tables beneath boards listing shifts, grievances, safety rulings, apprenticeship standards, and names of members injured on the job. "
            "Trade-house crests appear here too, but never above the union charter carved into the main wall. Dwarven civic life clearly expects powerful employers and powerful workers to negotiate in the same city rather than pretend the other side does not exist."
        ),
        exits={"south": DWARF_REGISTRY_HALL_KEY, "east": DWARF_PRESSURE_GALLERY_KEY, "west": DWARF_LIFT_PLATFORM_KEY},
        npc_keys=("dwarf_steward_torren_coalhand",),
        tags=("safe", "union", "labor", "apprenticeship", "civic_core"),
    ),
    RoomDefinition(
        key=DWARF_PRESSURE_GALLERY_KEY,
        name="Pressure Gallery",
        region_key=DWARF_REGION_KEY,
        description=(
            "Three steam mains cross this tiled service gallery behind waist-high safety rails. Each line has a large analog pressure gauge, isolation wheels, a spring-loaded intake valve, and a black-handled bleed valve routed into a muffled condenser. "
            "The apparatus is full-sized city infrastructure, but this particular bay has training interlocks that prevent a beginner from changing the live system outside a narrow safe range."
        ),
        exits={"west": DWARF_UNION_HALL_KEY, "south": DWARF_LIFT_PLATFORM_KEY},
        tags=("safe", "steam", "training", "infrastructure", "interaction"),
    ),
    RoomDefinition(
        key=DWARF_LIFT_PLATFORM_KEY,
        name="Grand Lift Platform",
        region_key=DWARF_REGION_KEY,
        description=(
            "A freight-and-passenger lift occupies a vertical shaft so large that its far wall disappears into steam haze. Twin cages move on separate counterweighted tracks while signal lamps and mechanical indicators show which levels are clear. "
            "The local training cage is isolated from freight traffic, allowing new workers to learn the signal sequence without putting a cargo crew beneath them. The Foundry Concourse lies south and the union hall west."
        ),
        exits={"south": DWARF_START_ROOM_KEY, "west": DWARF_UNION_HALL_KEY, "north": DWARF_PRESSURE_GALLERY_KEY, "up": DWARF_UPPER_FREIGHT_KEY},
        npc_keys=("dwarf_liftmaster_dori_chainmark",),
        tags=("safe", "lift", "steam", "training", "transit_hub"),
    ),
    RoomDefinition(
        key=DWARF_TRADE_ARCADE_KEY,
        name="Trade House Arcade",
        region_key=DWARF_REGION_KEY,
        description=(
            "Tall offices and counting rooms line a polished arcade built around an old ore-haul tunnel. Brass plaques identify Dwarven trade houses beside foreign factors, insurers, contract witnesses, tool sellers, and freight brokers. "
            "The largest houses display wealth without pretending to rule alone: every loading contract posted here carries union rates, civic inspection marks, or both. The crowd is noticeably mixed by Astralis standards."
        ),
        exits={"east": DWARF_START_ROOM_KEY, "south": DWARF_WORKSHOP_TIER_KEY},
        tags=("safe", "trade_houses", "commerce", "cosmopolitan", "offices"),
    ),
    RoomDefinition(
        key=DWARF_WORKSHOP_TIER_KEY,
        name="Public Workshop Tier",
        region_key=DWARF_REGION_KEY,
        description=(
            "A descending terrace of public work bays surrounds communal forges, vises, drill presses, measuring tables, and tool lockers. Some bays belong to established shops; others are rented by the hour to apprentices and independent craftspeople. "
            "Finished pieces are displayed beside rejected ones with notes explaining the defect. Craftsmanship here is presented less as secret genius than as documented, repeatable work that can survive inspection."
        ),
        exits={"north": DWARF_START_ROOM_KEY, "west": DWARF_TRADE_ARCADE_KEY},
        tags=("safe", "crafting", "workshops", "public_infrastructure", "apprenticeship"),
    ),
    RoomDefinition(
        key=DWARF_UPPER_FREIGHT_KEY,
        name="Upper Freight Deck",
        region_key=DWARF_REGION_KEY,
        description=(
            "The lift opens onto a higher cavern where freight rails divide toward foundries, surface depots, residential vaults, and distant mountain districts not yet mapped into the local starter routes. "
            "Signal towers blink through the haze while loaded wagons vanish into tunnels large enough to swallow buildings. This is the first clear glimpse of how enormous the Dwarven mountain settlement really is."
        ),
        exits={"down": DWARF_LIFT_PLATFORM_KEY},
        tags=("safe", "starter_boundary", "freight", "future_city_routes", "industrial_city"),
    ),
)


HELGA_BRASSMEASURE = NpcDefinition(
    key="dwarf_registrar_helga_brassmeasure",
    name="Registrar Helga Brassmeasure",
    short_description="a square-spectacled registrar working three stamp pads and two document lifts at once",
    room_key=DWARF_REGISTRY_HALL_KEY,
    role="starter registrar and civic-work mentor",
    dialogue=(
        "Helga taps a blank line on a work order. 'If a task can kill somebody, move freight, spend public money, or block a corridor, somebody signs for it. Usually more than one somebody.'",
        "'Paper is not the opposite of work. Paper is how the next crew knows what the last crew changed.'",
    ),
)

TORREN_COALHAND = NpcDefinition(
    key="dwarf_steward_torren_coalhand",
    name="Steward Torren Coalhand",
    short_description="a broad union steward with a slate pencil tucked behind one ear and old burn scars across both hands",
    room_key=DWARF_UNION_HALL_KEY,
    role="union steward and apprenticeship counterseal officer",
    dialogue=(
        "Torren points at the union charter. 'A house can own the machine. It does not own the worker standing beside it.'",
        "'Your first order gets a civic stamp and a union counterseal. That way the city knows the work is permitted and we know somebody bothered to tell you how not to die doing it.'",
    ),
)

DORI_CHAINMARK = NpcDefinition(
    key="dwarf_liftmaster_dori_chainmark",
    name="Liftmaster Dori Chainmark",
    short_description="a compact liftmaster wearing a signal whistle, inspection hammer, and a watch with two minute hands",
    room_key=DWARF_LIFT_PLATFORM_KEY,
    role="lift instructor and transit safety officer",
    dialogue=(
        "Dori rests one hand on the training cage lever. 'A lift is simple right up until three hundred feet of cable disagree with you.'",
        "'Signals first, pressure second, motion third. Anyone teaching those in another order is buying drinks for the undertakers.'",
    ),
)

DWARF_NPCS = (HELGA_BRASSMEASURE, TORREN_COALHAND, DORI_CHAINMARK)


APPRENTICE_WORK_ORDER = ItemDefinition(
    "dwarf_apprentice_work_order",
    "Apprentice Work Order",
    "A fresh civic work order assigning one supervised pressure-and-lift inspection. The registry and union signature fields are still blank.",
    "quest_item",
    tier=0,
)
REGISTERED_WORK_ORDER = ItemDefinition(
    "dwarf_registered_work_order",
    "Registered Apprentice Work Order",
    "The same work order, now carrying the Civic Registry's embossed brass stamp. It still requires a union safety counterseal.",
    "quest_item",
    tier=0,
)
COUNTERSIGNED_WORK_ORDER = ItemDefinition(
    "dwarf_countersigned_work_order",
    "Countersigned Apprentice Work Order",
    "A properly registered and union-countersealed order authorizing a supervised pressure check and lift test.",
    "quest_item",
    tier=0,
)
COMPLETED_WORK_ORDER = ItemDefinition(
    "dwarf_completed_work_order",
    "Completed First Work Order",
    "Your first closed Dwarven work order. Registry, union, pressure, and lift marks show the obligation was completed in the proper sequence.",
    "quest_item",
    tier=0,
)
DWARF_WORK_ORDER_ITEMS = (
    APPRENTICE_WORK_ORDER,
    REGISTERED_WORK_ORDER,
    COUNTERSIGNED_WORK_ORDER,
    COMPLETED_WORK_ORDER,
)

DWARF_FIRST_WORK_ORDER = QuestDefinition(
    key="dwarf_first_work_order",
    name="By Stamp and Steam",
    style="structured",
    description=(
        "Complete a first supervised civic work order through the same registry, union, inspection, and machinery procedures used by the mountain city's real crews."
    ),
    objective_steps=(
        ("registry_stamp", "Take your Apprentice Work Order east to Civic Registry Hall and TALK HELGA."),
        ("union_counterseal", "Take the Registered Apprentice Work Order north to the Union Hall and TALK TORREN."),
        ("inspect_pressure", "Go east to the Pressure Gallery and EXAMINE PRESSURE GAUGE before touching the controls."),
        ("set_pressure", "Use TURN BLEED VALVE to bring the training line into its marked operating band."),
        ("operate_lift", "Go to the Grand Lift Platform and OPERATE LIFT for the supervised test cycle."),
        ("return_registry", "Return to Civic Registry Hall and TALK HELGA to close the work order."),
        ("complete", "Your first formal obligation to the mountain city is complete."),
    ),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    touch: str = "",
    listen: str = "",
) -> FeatureDefinition:
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


def _exit(direction: str, destination: str, name: str, text: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, **kwargs)


def _day(text: str) -> DescriptionLayer:
    return DescriptionLayer("dwarf_day_shift", text, priority=40, condition=ViewCondition(time_buckets=("day",)))


def _night(text: str) -> DescriptionLayer:
    return DescriptionLayer("dwarf_night_shift", text, priority=50, condition=ViewCondition(time_buckets=("night",)))


def dwarf_room_augmentations() -> dict[str, RoomAugmentation]:
    return {
        DWARF_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", DWARF_REGISTRY_HALL_KEY, "Civic Registry Hall", "You follow the numbered brass floor line east into the registry."),
                _exit("north", DWARF_LIFT_PLATFORM_KEY, "Grand Lift Platform", "You follow the vibration of heavy cables toward the grand lift shaft."),
                _exit("west", DWARF_TRADE_ARCADE_KEY, "Trade House Arcade", "You pass beneath engraved house directories into the commercial arcade."),
                _exit("south", DWARF_WORKSHOP_TIER_KEY, "Public Workshop Tier", "You descend a short stone ramp toward the public work bays."),
            ),
            features=(
                _feature("shift_board", "Shift Board", "a clock-driven board tracking active crews and civic works", "Hundreds of sliding brass tabs identify crews, job numbers, inspection windows, and delayed loads. The board makes the city look less like a collection of workshops than one enormous coordinated project.", aliases=("board", "shift board", "work board"), listen="Every few minutes a mechanism clicks and an entire row of crew markers advances."),
                _feature("steam_mains", "Steam Mains", "disciplined rows of insulated pipes crossing the vault", "Each pipe is labeled for pressure class, inspection date, owner, and emergency shutoff zone. Dwarven engineering is visible here as maintenance discipline rather than mysterious genius.", aliases=("pipes", "steam pipes", "mains"), touch="The outer insulation is warm but intentionally safe to touch."),
                _feature("work_order_windows", "Work-Order Windows", "numbered civic counters issuing and routing authorized work", "The windows are divided by task rather than social rank. Apprentices, house agents, independent craftspeople, and union officers all wait beneath the same sequence numbers.", aliases=("windows", "counters", "work orders")),
            ),
            description_layers=(
                _day("First and second shifts overlap here, filling the concourse with tool cases, freight manifests, lunch tins, and arguments conducted while walking."),
                _night("Third shift is quieter but far from asleep. Maintenance crews own the concourse now, and inspection lamps shine brighter than the commercial signs."),
            ),
        ),
        DWARF_REGISTRY_HALL_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", DWARF_START_ROOM_KEY, "Foundry Concourse", "You leave the counters for the broad Foundry Concourse."),
                _exit("north", DWARF_UNION_HALL_KEY, "Ironworkers' Union Hall", "You climb the short stair marked APPRENTICESHIP AND SAFETY COUNTERSEALS."),
            ),
            features=(
                _feature("brass_stamps", "Registry Stamps", "rows of numbered embossing stamps secured to the service counters", "Every stamp leaves both a raised seal and a tiny serial number. Altering one would be harder than simply completing the form honestly.", aliases=("stamps", "stamp", "seals")),
                _feature("document_lifts", "Document Lifts", "small brass carriers moving paperwork through wall shafts", "Pneumatic tubes would be faster, but the Dwarves apparently prefer compact chain lifts because a jam can be opened and repaired by hand.", aliases=("document lifts", "paper lifts", "carriers"), listen="Chains whisper inside the walls as forms travel between departments."),
            ),
            description_layers=(_day("Every numbered bay is open, and the queue advances with intimidating efficiency."), _night("Only essential permit and safety bays remain staffed, but apprenticeship work orders are explicitly one of them.")),
        ),
        DWARF_UNION_HALL_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", DWARF_REGISTRY_HALL_KEY, "Civic Registry Hall", "You descend from the union hall to the registry counters."),
                _exit("east", DWARF_PRESSURE_GALLERY_KEY, "Pressure Gallery", "You follow safety diagrams east into the supervised steam gallery."),
                _exit("west", DWARF_LIFT_PLATFORM_KEY, "Grand Lift Platform", "You pass through the crew door toward the lift platform."),
            ),
            features=(
                _feature("union_charter", "Union Charter", "a labor charter carved permanently into the machine-hall wall", "The charter is practical rather than poetic: stop-work rights, injury obligations, apprentice supervision ratios, arbitration rules, and the limits of trade-house authority.", aliases=("charter", "labor charter", "wall charter")),
                _feature("grievance_board", "Grievance Board", "an open board of active safety disputes and resolved rulings", "Resolved disputes remain posted beside current ones so later crews can see not only what rule exists, but what accident or argument caused it.", aliases=("grievances", "board", "rulings")),
            ),
            description_layers=(_day("Meal tables are crowded between shift changes, making the hall half union office and half neighborhood canteen."), _night("A smaller night committee works under shaded lamps while off-shift crews play quiet games at the far tables.")),
        ),
        DWARF_PRESSURE_GALLERY_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", DWARF_UNION_HALL_KEY, "Ironworkers' Union Hall", "You leave the training mains for the union hall."),
                _exit("south", DWARF_LIFT_PLATFORM_KEY, "Grand Lift Platform", "You follow the marked service route south to the lift machinery."),
            ),
            features=(
                _feature("pressure_gauge", "Pressure Gauge", "a large training-line gauge with a clearly painted operating band", "The needle sits slightly above the green operating band. A diagram below it says excess training pressure should be relieved through the BLACK BLEED circuit, not the intake or bypass.", aliases=("gauge", "pressure gauge", "needle", "dial"), search="A maintenance plate confirms the training interlock will prevent dangerous pressure changes."),
                _feature("training_valves", "Training Valves", "three labeled controls fitted with mechanical safety interlocks", "The brass intake valve admits pressure, the red bypass recirculates it, and the black bleed valve vents excess steam safely into a condenser. The controls are intentionally obvious because this is where apprentices learn procedure.", aliases=("valves", "controls", "bleed valve", "intake valve", "bypass valve"), touch="The hand wheels are warm and heavy, but none can move fast enough to surprise you."),
                _feature("condenser", "Training Condenser", "a muffled tank that safely receives vented steam", "Instead of dumping steam into the room, the training bleed line condenses it into warm water for cleaning the gallery floor.", aliases=("condenser", "tank", "bleed tank"), listen="A steady internal drip shows the condenser is already cooling ordinary system losses."),
            ),
            description_layers=(_day("Inspection students cycle through the gallery in pairs, each reading gauges aloud before touching anything."), _night("The gallery is almost empty except for instrument lamps and the slow breathing sound of the steam mains.")),
        ),
        DWARF_LIFT_PLATFORM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", DWARF_START_ROOM_KEY, "Foundry Concourse", "You step away from the shaft into the Foundry Concourse."),
                _exit("west", DWARF_UNION_HALL_KEY, "Ironworkers' Union Hall", "You use the crew passage west into the union hall."),
                _exit("north", DWARF_PRESSURE_GALLERY_KEY, "Pressure Gallery", "You follow the service line north into the pressure gallery."),
                ExitDefinition(
                    direction="up",
                    destination_key=DWARF_UPPER_FREIGHT_KEY,
                    name="Upper Freight Deck",
                    travel_text="With your first civic work clearance recorded, you ride a passenger cage up toward the wider mountain city.",
                    failure_text="The upper-city passenger signal rejects the call. Your first work order has not been formally closed yet.",
                    condition=ViewCondition(required_flags=(DWARF_CIVIC_CLEARANCE_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature("training_cage", "Training Lift Cage", "a small lift cage isolated from live freight traffic", "The cage has the same brake, signal, counterweight, and door interlocks as a working freight lift, but its track only spans a short supervised test section.", aliases=("cage", "lift", "training lift"), listen="The counterweight chain settles with a slow metallic ticking between test cycles."),
                _feature("signal_panel", "Lift Signal Panel", "a mechanical panel showing track clearance and pressure readiness", "Three indicators must agree before the training lever releases: doors latched, line pressure in band, and track clear. The system is designed to make correct procedure easier than reckless improvisation.", aliases=("panel", "signals", "signal lamps")),
            ),
            description_layers=(_day("Freight cages rise and fall almost continuously on the live tracks beyond the training rail."), _night("Commercial traffic thins, leaving long maintenance windows where crews inspect cable strands one section at a time.")),
        ),
        DWARF_TRADE_ARCADE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", DWARF_START_ROOM_KEY, "Foundry Concourse", "You return east beneath the civic clocks."),
                _exit("south", DWARF_WORKSHOP_TIER_KEY, "Public Workshop Tier", "You descend from contracts and offices toward the workshops that fulfill them."),
            ),
            features=(
                _feature("house_directory", "Trade-House Directory", "a rotating directory of firms, unions, factors, and service offices", "No single trade house occupies the top permanently. Listings are grouped by current contract category, making influence look dynamic and negotiated rather than hereditary.", aliases=("directory", "houses", "trade houses", "firms")),
                _feature("contract_wall", "Contract Wall", "publicly posted freight and fabrication contracts", "Each posting lists price, inspection standard, responsible house, union rate, deadline, and arbitration office. Even wealthy houses are expected to put obligations in writing.", aliases=("contracts", "wall", "contract board")),
            ),
            description_layers=(_day("Factors from several peoples move between offices while Dwarven clerks translate measurements, rates, and contract terms into shared standards."), _night("The arcade loses its salesmanship after dark and becomes a quieter world of freight accountants and night clerks.")),
        ),
        DWARF_WORKSHOP_TIER_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", DWARF_START_ROOM_KEY, "Foundry Concourse", "You climb back toward the civic concourse."),
                _exit("west", DWARF_TRADE_ARCADE_KEY, "Trade House Arcade", "You follow finished goods west toward the contract offices."),
            ),
            features=(
                _feature("inspection_table", "Inspection Table", "a granite measuring table covered in gauges and sample pieces", "Good and rejected work are displayed side by side. The notes focus on tolerances, heat treatment, joinery, and repeatability rather than the maker's reputation.", aliases=("table", "inspection table", "samples", "rejected work")),
                _feature("public_tools", "Public Tool Bays", "rentable civic tools maintained for apprentices and independent workers", "Every tool has a service card. A Dwarf without a wealthy house can still learn and work here, provided they follow the same inspection rules as everyone else.", aliases=("tools", "tool bays", "work bays"), listen="Hammers, files, treadles, and belt-driven machines create a dense but rhythmic industrial noise."),
            ),
            description_layers=(_day("Nearly every bay is active, and inspectors move from bench to bench carrying gauges instead of clipboards."), _night("Night workers spread out into the quieter bays, using the reduced traffic for careful fitting and repairs.")),
        ),
        DWARF_UPPER_FREIGHT_KEY: RoomAugmentation(
            exit_overrides=(_exit("down", DWARF_LIFT_PLATFORM_KEY, "Grand Lift Platform", "You ride the passenger cage down to the starter works."),),
            features=(
                _feature("district_signals", "District Signals", "a forest of mechanical signals pointing deeper into the mountain city", "The signs identify foundry levels, surface depots, residential vaults, rail exchanges, civic baths, guild schools, and districts far beyond the starter works. Most are deliberately left as future routes for now.", aliases=("signals", "signs", "districts", "signal towers")),
            ),
            description_layers=(_day("Upper freight traffic arrives in waves synchronized to the city's main shifts."), _night("Fewer wagons move at night, making the enormous scale of the surrounding cavern easier to appreciate.")),
        ),
    }


def _patch_room_npcs(room: RoomDefinition, extra_keys: tuple[str, ...]) -> RoomDefinition:
    merged = tuple(room.npc_keys) + tuple(key for key in extra_keys if key not in room.npc_keys)
    return replace(room, npc_keys=merged)


def install_dwarf_content(world_service=None) -> None:
    """Register the first Dwarven mountain-city district, quest, items, and rich room scenes."""
    known = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in DWARF_ROOMS if room.key not in known)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    legacy_world.ROOMS_BY_KEY.update({room.key: room for room in DWARF_ROOMS})

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    for npc in DWARF_NPCS:
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    for item in DWARF_WORK_ORDER_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    if DWARF_FIRST_WORK_ORDER.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (DWARF_FIRST_WORK_ORDER,)
    quests.QUESTS_BY_KEY[DWARF_FIRST_WORK_ORDER.key] = DWARF_FIRST_WORK_ORDER

    if world_service is not None:
        world_service.legacy_rooms.update({room.key: room for room in DWARF_ROOMS})
        world_service.augmentations.update(dwarf_room_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in DWARF_START_ROOM_KEYS:
                cache.pop(room_key, None)


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key)


def _consume_all(session, item_key: str) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, item_key)
    if quantity > 0:
        session.database.consume_item(session.character.id, item_key, quantity)


def _ensure_exactly_one(session, desired_key: str) -> None:
    assert session.character is not None
    for item in DWARF_WORK_ORDER_ITEMS:
        quantity = session.database.item_quantity(session.character.id, item.key)
        if item.key == desired_key:
            if quantity == 0:
                session.database.add_item(session.character.id, item.key, 1)
            elif quantity > 1:
                session.database.consume_item(session.character.id, item.key, quantity - 1)
        elif quantity > 0:
            session.database.consume_item(session.character.id, item.key, quantity)


def _replace_order(session, old_key: str, new_key: str) -> None:
    _consume_all(session, old_key)
    _ensure_exactly_one(session, new_key)


def _initialize_or_reconcile_dwarf(session) -> None:
    if session.character is None or session.character.race != "dwarf":
        return
    character_id = session.character.id

    if not session.character.current_room:
        session.database.set_character_room(character_id, DWARF_START_ROOM_KEY)
        if not session.character.bind_room:
            session.database.set_bind_room(character_id, DWARF_START_ROOM_KEY)
        refreshed = session.database.get_character_by_name(session.character.name)
        if refreshed is not None:
            session.character = refreshed

    quest = _quest(session)
    if quest is None:
        session.database.start_quest(character_id, DWARF_FIRST_WORK_ORDER.key, "registry_stamp")
        _ensure_exactly_one(session, APPRENTICE_WORK_ORDER.key)
        return

    if quest.get("status") == "completed":
        _ensure_exactly_one(session, COMPLETED_WORK_ORDER.key)
        return

    step = quest.get("current_step")
    if step == "registry_stamp":
        _ensure_exactly_one(session, APPRENTICE_WORK_ORDER.key)
    elif step == "union_counterseal":
        _ensure_exactly_one(session, REGISTERED_WORK_ORDER.key)
    else:
        _ensure_exactly_one(session, COUNTERSIGNED_WORK_ORDER.key)


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches(target: str, *names: str) -> bool:
    return target in {name.lower() for name in names}


async def _talk_helga(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if quest is None:
        _initialize_or_reconcile_dwarf(session)
        quest = _quest(session)
    if not quest:
        return False

    step = quest.get("current_step")
    if quest.get("status") == "completed":
        await session.send("\r\nHelga checks your closed order number. 'Already filed. Your clearance is on the civic record.'\r\n")
        return True
    if step == "registry_stamp":
        _replace_order(session, APPRENTICE_WORK_ORDER.key, REGISTERED_WORK_ORDER.key)
        session.database.grant_flag(session.character.id, DWARF_REGISTRY_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key, "union_counterseal")
        await session.send(
            "\r\nHelga reads every line before setting the order beneath a brass press. The stamp lands with a hard mechanical CLACK.\r\n"
            "'Authorized by the city. Not yet safe work.' She points north. 'Union counterseal next. Civic permission does not replace worker instruction.'\r\n"
            "Your Apprentice Work Order becomes a Registered Apprentice Work Order.\r\n"
            "Quest updated: By Stamp and Steam.\r\n"
        )
        return True
    if step == "return_registry":
        _replace_order(session, COUNTERSIGNED_WORK_ORDER.key, COMPLETED_WORK_ORDER.key)
        session.database.grant_flag(session.character.id, DWARF_CIVIC_CLEARANCE_FLAG)
        session.database.grant_flag(session.character.id, DWARF_FIRST_OBLIGATION_FLAG)
        session.database.complete_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key)
        await session.send(
            "\r\nHelga compares the registry stamp, union counterseal, pressure mark, and liftmaster's test notch. Only then does she close the order.\r\n"
            "'That is your first obligation to the city discharged properly. You were authorized, instructed, inspected, and accountable. Remember the sequence when the jobs stop being practice.'\r\n"
            "She enters your civic work clearance into the register. The upper freight deck is now available from the Grand Lift Platform.\r\n"
            "Quest complete: By Stamp and Steam.\r\n"
        )
        return True

    objective = DWARF_FIRST_WORK_ORDER.objective_for_step(step)
    await session.send("\r\nHelga glances at the current marks on your work order.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_torren(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest:
        return False
    step = quest.get("current_step")
    if step == "union_counterseal":
        _replace_order(session, REGISTERED_WORK_ORDER.key, COUNTERSIGNED_WORK_ORDER.key)
        session.database.grant_flag(session.character.id, DWARF_UNION_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key, "inspect_pressure")
        await session.send(
            "\r\nTorren checks the civic stamp, asks you to repeat the stop-work signal, then presses a black union counterseal beside Helga's mark.\r\n"
            "'Now the job is both permitted and supervised. East to the Pressure Gallery. Read the gauge before you touch a valve. We write that rule in ink because people used to write it in blood.'\r\n"
            "Your work order is now countersigned.\r\n"
        )
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nTorren nods toward your closed order. 'One obligation done. Plenty more in a city this size.'\r\n")
        return True
    objective = DWARF_FIRST_WORK_ORDER.objective_for_step(step)
    await session.send("\r\nTorren will not counterseal work out of sequence.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_dori(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest:
        return False
    if quest.get("current_step") == "operate_lift":
        await session.send("\r\nDori checks the pressure mark on your order. 'Good. Use OPERATE LIFT when you're ready. The training cage will cycle down, brake, signal, and return.'\r\n")
        return True
    if quest.get("status") == "completed":
        await session.send("\r\nDori taps the upper-city signal. 'Your clearance is live now. UP takes you to the freight deck.'\r\n")
        return True
    objective = DWARF_FIRST_WORK_ORDER.objective_for_step(quest.get("current_step"))
    await session.send("\r\nDori says, 'I only move the training cage when the paperwork and pressure marks say it is ready.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _handle_dwarf_tutorial(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "dwarf":
        return False
    room = session.character.current_room
    quest = _quest(session)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")

    if room == DWARF_PRESSURE_GALLERY_KEY and normalized in {
        "examine pressure gauge", "look pressure gauge", "examine gauge", "look gauge", "read gauge"
    }:
        if step == "inspect_pressure":
            session.database.advance_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key, "set_pressure")
        await session.send(
            "\r\nThe needle sits just above the green operating band. The plate beneath it is unambiguous: relieve excess training pressure through the BLACK BLEED valve. Intake adds pressure; bypass recirculates it.\r\n"
            "The training interlock prevents a dangerous setting, but the procedure still expects you to choose the correct control.\r\n"
        )
        return True

    if room == DWARF_PRESSURE_GALLERY_KEY and normalized in {"turn intake valve", "open intake valve", "use intake valve"}:
        await session.send(
            "\r\nThe intake wheel moves a fraction before the training interlock catches it. A brass tab flips up: INTAKE INCREASES LINE PRESSURE. No damage is done and the wheel springs back to neutral.\r\n"
        )
        return True

    if room == DWARF_PRESSURE_GALLERY_KEY and normalized in {"turn bypass valve", "open bypass valve", "use bypass valve"}:
        await session.send(
            "\r\nThe bypass control opens briefly, sending the same pressure around the training loop instead of removing it. The interlock resets the wheel. Nothing is damaged, but the gauge remains high.\r\n"
        )
        return True

    if room == DWARF_PRESSURE_GALLERY_KEY and normalized in {"turn bleed valve", "open bleed valve", "use bleed valve", "bleed pressure"}:
        if step != "set_pressure":
            await session.send("\r\nThe bleed valve is safe to operate, but your work order has not reached that inspection step yet. Read the pressure gauge first.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_PRESSURE_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key, "operate_lift")
        await session.send(
            "\r\nYou turn the black-handled bleed valve slowly. Steam passes into the muffled condenser with a deep hiss, and the gauge needle settles neatly into the green band.\r\n"
            "A mechanical witness tab punches the pressure check onto your countersigned order. No drama, no danger—just a system behaving correctly because you followed the procedure.\r\n"
            "Quest updated: take the marked order to the Grand Lift Platform and OPERATE LIFT.\r\n"
        )
        return True

    if room == DWARF_LIFT_PLATFORM_KEY and normalized in {"operate lift", "use lift", "test lift", "operate training lift", "pull lift lever"}:
        if step != "operate_lift":
            await session.send("\r\nThe training lever remains mechanically locked. Dori's panel requires a countersigned order with a completed pressure check before it will release.\r\n")
            return True
        flags = session.database.list_flags(session.character.id)
        if DWARF_PRESSURE_FLAG not in flags:
            await session.send("\r\nThe pressure-ready indicator is dark. The lift test cannot begin until the Pressure Gallery check is recorded.\r\n")
            return True
        session.database.grant_flag(session.character.id, DWARF_LIFT_FLAG)
        session.database.advance_quest(session.character.id, DWARF_FIRST_WORK_ORDER.key, "return_registry")
        await session.send(
            "\r\nDori calls the signal sequence. You latch the cage, verify the green lamps, and pull the training lever.\r\n"
            "The cage descends one level, the governor catches exactly where it should, a bell answers from below, and the counterweight returns you smoothly to the platform. Dori strikes a completion notch into your order with an inspection hammer.\r\n"
            "'Machinery does not care how confident you feel,' she says. 'It cares whether every condition is actually true.'\r\n"
            "Quest updated: return to Civic Registry Hall and TALK HELGA to close the obligation.\r\n"
        )
        return True

    return False


async def _show_obligations(session) -> None:
    assert session.character is not None
    quest = _quest(session)
    flags = session.database.list_flags(session.character.id)
    await session.send("\r\n--- Dwarven Civic Record ---\r\n")
    if quest is None:
        await session.send("No starter work order is currently recorded.\r\n")
        return
    if quest.get("status") == "completed":
        await session.send("By Stamp and Steam: COMPLETED. First civic obligation discharged.\r\n")
    else:
        objective = DWARF_FIRST_WORK_ORDER.objective_for_step(quest.get("current_step"))
        await session.send("By Stamp and Steam: ACTIVE.\r\n")
        if objective:
            await session.send(f"Current obligation: {objective}\r\n")
    await session.send(
        "Registry authorization: " + ("recorded" if DWARF_REGISTRY_FLAG in flags else "pending") + ".\r\n"
        "Union safety counterseal: " + ("recorded" if DWARF_UNION_FLAG in flags else "pending") + ".\r\n"
        "Pressure inspection: " + ("recorded" if DWARF_PRESSURE_FLAG in flags else "pending") + ".\r\n"
        "Lift test: " + ("recorded" if DWARF_LIFT_FLAG in flags else "pending") + ".\r\n"
        "Civic work clearance: " + ("ACTIVE" if DWARF_CIVIC_CLEARANCE_FLAG in flags else "not yet issued") + ".\r\n"
    )
    await session.send("This record represents obligations and completed procedure, not exclusive trade-house or union membership.\r\n")


def install_dwarf_runtime(player_session_class, world_service) -> None:
    install_dwarf_content(world_service)
    if getattr(player_session_class, "_dwarf_start_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "dwarf":
            _initialize_or_reconcile_dwarf(self)
        await previous_enter_character(self)
        if self.character is not None and self.character.race == "dwarf":
            _initialize_or_reconcile_dwarf(self)
            quest = _quest(self)
            if quest and quest.get("status") == "active":
                objective = DWARF_FIRST_WORK_ORDER.objective_for_step(quest.get("current_step"))
                await self.send("\r\nDwarven starter obligation: By Stamp and Steam.\r\n")
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")
                await self.send("Use OBLIGATIONS at any time to review your civic work record.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "dwarf":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"obligations", "obligation", "civic record", "work record", "work order", "workorder"}:
            await _show_obligations(self)
            return

        if await _handle_dwarf_tutorial(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == DWARF_REGISTRY_HALL_KEY and _matches(target, "helga", "registrar", "registrar helga", "helga brassmeasure", "clerk"):
                if await _talk_helga(self):
                    return
            if self.character.current_room == DWARF_UNION_HALL_KEY and _matches(target, "torren", "steward", "steward torren", "torren coalhand", "union steward"):
                if await _talk_torren(self):
                    return
            if self.character.current_room == DWARF_LIFT_PLATFORM_KEY and _matches(target, "dori", "liftmaster", "liftmaster dori", "dori chainmark"):
                if await _talk_dori(self):
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

        if normalized in {"help", "?"}:
            await self.send(
                "Dwarf starter: OBLIGATIONS shows your civic record. By Stamp and Steam uses TALK HELGA, TALK TORREN, EXAMINE PRESSURE GAUGE, TURN BLEED VALVE, OPERATE LIFT, then TALK HELGA again.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._dwarf_start_runtime_installed = True
