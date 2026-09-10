from __future__ import annotations

from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition
import mud.world as world


GOBLIN_REGION_KEY = "junk_city_and_swamps"
GOBLIN_START_ROOM_KEY = "goblin_clattergate"
GOBLIN_BRASSGUT_MARKET_KEY = "goblin_brassgut_market"
GOBLIN_SORTING_SPINE_KEY = "goblin_sorting_spine"
GOBLIN_PATCHWORK_PLAZA_KEY = "goblin_patchwork_plaza"
GOBLIN_TINKER_ROW_KEY = "goblin_tinker_row"
GOBLIN_LEDGER_HALL_KEY = "goblin_ledger_hall"
GOBLIN_FLOODGATE_WALK_KEY = "goblin_floodgate_walk"


GOBLIN_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=GOBLIN_START_ROOM_KEY,
        name="The Clattergate",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A broad gate assembled from mismatched bridge trusses, ship plates, boiler doors, and three different kinds of rivet opens directly into Junk City's core. "
            "Nothing matches except by function. Hand-painted clan marks cover the metal in overlapping layers, while pulley baskets, handcarts, couriers, and salvage crews pass beneath without ever quite stopping. "
            "A waist-high intake counter has been welded to one side of the gate. Beyond it, the city rises in bright tiers of patched metal, timber, canvas, glass, and scavenged stone."
        ),
        exits={"east": GOBLIN_BRASSGUT_MARKET_KEY, "north": GOBLIN_SORTING_SPINE_KEY},
        npc_keys=("goblin_vikka_three_nails",),
        tags=("goblin_start", "safe", "junk_city_core", "salvage", "busy"),
    ),
    RoomDefinition(
        key=GOBLIN_BRASSGUT_MARKET_KEY,
        name="Brassgut Market",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A roofless market sprawls between leaning stacks of scrap-built shops. Copper tubing hangs beside old lantern glass, repaired boots, cookware, gears, rope, cracked instruments, Earth-looking curios of uncertain authenticity, and parts whose original purpose no one bothers to remember. "
            "Vendors shout prices, counterprices, insults, and family connections across aisles barely wide enough for a handcart. The market is cluttered, loud, and remarkably efficient."
        ),
        exits={"west": GOBLIN_START_ROOM_KEY, "north": GOBLIN_PATCHWORK_PLAZA_KEY},
        npc_keys=("goblin_ruskle_coil",),
        tags=("safe", "market", "junk_city_core", "commerce", "salvage"),
    ),
    RoomDefinition(
        key=GOBLIN_SORTING_SPINE_KEY,
        name="The Sorting Spine",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A long raised lane cuts through the city beneath cranes made from timber spars, wagon axles, and repurposed ship winches. Salvage arrives in baskets and carts, then breaks apart into streams: metal left, cloth right, glass uphill, working mechanisms under guard. "
            "Chalk boards record weights and claims faster than crews can erase them. The lane feels chaotic until the sorting rhythm becomes visible; then the whole place resembles a machine made of people."
        ),
        exits={"south": GOBLIN_START_ROOM_KEY, "east": GOBLIN_PATCHWORK_PLAZA_KEY, "north": GOBLIN_TINKER_ROW_KEY},
        tags=("safe", "salvage", "sorting", "junk_city_core", "industrial"),
    ),
    RoomDefinition(
        key=GOBLIN_PATCHWORK_PLAZA_KEY,
        name="Patchwork Plaza",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Junk City's central plaza is paved with hundreds of unrelated slabs fitted together by stubbornness rather than symmetry. An old mill wheel turns above a public water trough even though no stream runs here; a belt drive disappears through three buildings to whatever machine actually powers it. "
            "Messengers, repair crews, clan representatives, customers, children, and scavengers use the plaza as a crossing point. Every wall carries notices, offers, warnings, maps, and claims layered one over another."
        ),
        exits={"south": GOBLIN_BRASSGUT_MARKET_KEY, "west": GOBLIN_SORTING_SPINE_KEY, "east": GOBLIN_LEDGER_HALL_KEY, "north": GOBLIN_FLOODGATE_WALK_KEY},
        tags=("safe", "plaza", "junk_city_core", "social", "busy"),
    ),
    RoomDefinition(
        key=GOBLIN_TINKER_ROW_KEY,
        name="Tinker Row",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Small repair shops crowd both sides of a narrow metal-decked street, each open to the daylight behind curtains of chains, beads, wire, or hanging tools. Goblins hammer bent hinges flat, splice cracked handles, rewire lamps, patch kettles, fit mismatched gears, and argue over whether a thing is repaired when it works better than it did originally. "
            "Almost nothing here is new. Almost nothing here is useless."
        ),
        exits={"south": GOBLIN_SORTING_SPINE_KEY},
        tags=("safe", "repair", "crafting", "junk_city_core", "workshops"),
    ),
    RoomDefinition(
        key=GOBLIN_LEDGER_HALL_KEY,
        name="The Ledger Hall",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A surprisingly solid hall of brick, iron shelving, and reinforced timber stands amid the improvised city around it. Inside, contracts are witnessed, salvage claims copied, courier bonds recorded, clan debts disputed, and merchant-family agreements stamped in ink thick enough to survive swamp humidity. "
            "Goblin society may look improvised from the street, but very little valuable changes hands without someone remembering exactly who owes whom."
        ),
        exits={"west": GOBLIN_PATCHWORK_PLAZA_KEY},
        tags=("safe", "contracts", "clans", "commerce", "junk_city_core"),
    ),
    RoomDefinition(
        key=GOBLIN_FLOODGATE_WALK_KEY,
        name="Floodgate Walk",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A high catwalk runs along Junk City's northern flood barrier, built from old bridge sections driven into dark swamp mud. From here the dense city drops away into reed beds, shallow channels, salvage mounds, and distant clan roads raised above the water on crooked pilings. "
            "A painted checkpoint marks where city-safe traffic ends. Beyond it, the swamp routes become less supervised and far less forgiving. For now, the core district remains behind you to the south."
        ),
        exits={"south": GOBLIN_PATCHWORK_PLAZA_KEY},
        tags=("safe", "city_edge", "swamp_view", "danger_hint", "future_route"),
    ),
)


VIKKA_THREE_NAILS = NpcDefinition(
    key="goblin_vikka_three_nails",
    name="Vikka Three-Nails",
    short_description="a sharp-eyed intake clerk sorting tags, claims, and newcomers with equal speed",
    room_key=GOBLIN_START_ROOM_KEY,
    role="Junk City starter guide and intake clerk",
    dialogue=(
        "Vikka flicks a brass claim tag between two fingers. 'New face? Fine. City rule one: if it has a mark, somebody claims it. City rule two: if it has two marks, somebody's arguing about it.'",
        "She points east without looking. 'Brassgut Market if you need things. North if you want to see where things come from. Patchwork Plaza if you need everybody eventually.'",
        "'And don't call it junk like it means worthless. Junk is what a thing becomes before a Goblin figures out what it is next.'",
    ),
)

RUSKLE_COIL = NpcDefinition(
    key="goblin_ruskle_coil",
    name="Ruskle Coil",
    short_description="a compact salvage broker wearing six measuring tapes and no two matching gloves",
    room_key=GOBLIN_BRASSGUT_MARKET_KEY,
    role="market broker and cultural contact",
    dialogue=(
        "Ruskle looks you over with the reflexive appraisal of someone who prices everything. 'Buying, selling, repairing, carrying, finding, proving ownership, or pretending you had ownership first?'",
        "He grins before you can answer. 'Relax. First one's free: working ugly beats broken pretty. That's why half this city is still standing.'",
        "'If you want to understand us, watch Tinker Row. If you want to understand why we yell so much, read the Ledger Hall after.'",
    ),
)

GOBLIN_NPCS: tuple[NpcDefinition, ...] = (VIKKA_THREE_NAILS, RUSKLE_COIL)


def _feature(
    key: str,
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    summary: str,
    examine: str,
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


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _day_layer(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_day_activity", text, priority=40, condition=ViewCondition(time_buckets=("day",)))


def _night_layer(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_night_activity", text, priority=50, condition=ViewCondition(time_buckets=("night",)))


def goblin_room_augmentations() -> dict[str, RoomAugmentation]:
    """Rich room-engine content for the safe Junk City starter core."""
    return {
        GOBLIN_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", GOBLIN_BRASSGUT_MARKET_KEY, "Brassgut Market", "You pass under a rack of hanging pans and enter the market's shouting aisles."),
                _exit("north", GOBLIN_SORTING_SPINE_KEY, "The Sorting Spine", "You follow a stream of tagged salvage carts onto the raised sorting lane."),
            ),
            features=(
                _feature(
                    "patchwork_gate", "Patchwork Gate", aliases=("gate", "clattergate", "metal gate"),
                    summary="a city gate assembled from several unrelated machines and bridges",
                    examine="Ship plate, bridge iron, boiler doors, wagon springs, and at least one piece of old agricultural machinery have all become one perfectly functional gate. Repair plates are dated in at least five different marking systems.",
                    search="Among the overlapping clan marks you find maintenance notes, courier scratches, and a tiny old human maker's stamp on one plate that probably arrived here as salvage generations ago.",
                    touch="Every plate has a different temperature and texture. None of the seams line up; all of the load-bearing points do.",
                    listen="The gate clicks, rattles, rings, and groans continuously as traffic passes through it—hence the name.",
                ),
                _feature(
                    "intake_counter", "Intake Counter", aliases=("counter", "intake", "claim counter"),
                    summary="Vikka's welded public counter for tags and claims",
                    examine="The counter is covered in shallow grooves from knives, measuring tools, stamps, and impatient fingernails. Bundles of colored claim tags hang from nails driven directly into the steel.",
                    search="You find no unattended valuables. Vikka has apparently planned for exactly this kind of curiosity.",
                    touch="The scarred steel is warm from constant hands and direct sun.",
                ),
                _feature(
                    "claim_marks", "Clan Claim Marks", aliases=("marks", "clan marks", "paint", "symbols"),
                    summary="overlapping clan and merchant-family symbols painted across the gate",
                    examine="Some marks are elaborate crests, others are a single slash of color. Older marks survive underneath newer ones, turning the gate into a layered history of who maintained, controlled, repaired, or merely insisted on being associated with it.",
                ),
            ),
            description_layers=(
                _day_layer("Daylight makes the Clattergate almost aggressively bright: polished scraps flash in the sun, awnings throw blocks of hard color, and the flow of carts and couriers rarely leaves an empty patch of street."),
                _night_layer("After dark, the gate remains staffed but the daytime flood thins. Repaired lamps, furnace glow, and strings of mismatched bulbs turn the metalwork into a quieter constellation."),
                DescriptionLayer("goblin_rain_gate", "Rain drums on every different piece of the gate with a different pitch, turning the entrance into an accidental percussion instrument.", priority=60, condition=ViewCondition(weather=("rain", "storm"))),
            ),
        ),
        GOBLIN_BRASSGUT_MARKET_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", GOBLIN_START_ROOM_KEY, "The Clattergate", "You squeeze back through the market traffic toward the patchwork gate."),
                _exit("north", GOBLIN_PATCHWORK_PLAZA_KEY, "Patchwork Plaza", "You follow the broadest aisle until the stalls open into the central plaza."),
            ),
            features=(
                _feature(
                    "salvage_stalls", "Salvage Stalls", aliases=("stalls", "market", "wares", "salvage"),
                    summary="dense stalls selling repaired, repurposed, and half-understood goods",
                    examine="Goods are grouped by usefulness rather than origin: things that cut, things that hold liquid, things that make light, things with springs, things that probably still work, and things valuable mainly because nobody can identify them.",
                    search="A patient scan turns up dozens of clever repairs and several objects that look suspiciously like old Earth artifacts mixed in with ordinary salvage.",
                    listen="Every sale seems to require at least three raised voices, two witnesses, and one person laughing at somebody else's opening offer.",
                ),
                _feature(
                    "repair_guarantees", "Repair Guarantees", aliases=("guarantees", "tags", "warranty tags"),
                    summary="handwritten tags promising highly specific kinds of functionality",
                    examine="The promises are precise: 'holds soup if kept upright,' 'lamp works except in heavy rain,' 'gearbox guaranteed for one hill or your argument back.' Goblin honesty appears to favor specificity over reassurance.",
                ),
                _feature(
                    "curio_blanket", "Curio Blanket", aliases=("curios", "blanket", "earth artifacts", "artifacts"),
                    summary="a blanket of strange old objects offered without confident identification",
                    examine="Bent badges, smooth molded plastics, fragments of printed lettering, dead electronics, and machine pieces share a blanket. Some may be Human Earth relics; some are obvious Goblin fakes; several could be either.",
                ),
            ),
            description_layers=(
                _day_layer("Brassgut is at full voice during the day. Sunlight pours between awnings, vendors stand on crates to shout over one another, and every useful patch of shade has become part of somebody's stall."),
                _night_layer("At night, many outer stalls fold shut while repair lamps remain burning around the brokers who prefer slower, quieter deals."),
                DescriptionLayer("goblin_market_rain", "Canvas awnings snap into place as rain begins, narrowing the aisles but barely reducing the market's volume.", priority=60, condition=ViewCondition(weather=("rain", "storm"))),
            ),
        ),
        GOBLIN_SORTING_SPINE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_START_ROOM_KEY, "The Clattergate", "You follow empty carts downhill toward the city gate."),
                _exit("east", GOBLIN_PATCHWORK_PLAZA_KEY, "Patchwork Plaza", "You leave the sorting crews and cross onto the central plaza."),
                _exit("north", GOBLIN_TINKER_ROW_KEY, "Tinker Row", "You follow bins of repairable mechanisms toward the sound of smaller hammers."),
            ),
            features=(
                _feature(
                    "sorting_cranes", "Sorting Cranes", aliases=("cranes", "winches", "hoists"),
                    summary="improvised cranes shifting salvage between lanes",
                    examine="The cranes combine ship winches, tree trunks, wagon wheels, gear reductions, counterweights, and a disturbing amount of rope. Their construction is inelegant; their operators place loads with centimeter precision.",
                    listen="Winches chatter, hooks ring against scrap, supervisors whistle, and carts clatter in a repeating industrial rhythm.",
                ),
                _feature(
                    "claim_boards", "Claim Boards", aliases=("boards", "chalk boards", "claims", "tallies"),
                    summary="rapidly changing chalk records of ownership and weight",
                    examine="Each line identifies a load, finder, claimed share, handling fee, destination, and anyone currently disputing the previous five facts.",
                    touch="Chalk dust comes away immediately. Fresh figures are written over old ones every few minutes.",
                ),
                _feature(
                    "sorting_chutes", "Sorting Chutes", aliases=("chutes", "bins", "sorting bins"),
                    summary="painted chutes dividing material by what it can become next",
                    examine="The labels say METAL, GLASS, CLOTH, BURNABLE, MECHANISMS, UNKNOWN BUT INTERESTING, and DO NOT SHAKE.",
                ),
            ),
            description_layers=(
                _day_layer("The daytime Sorting Spine runs at its fastest pace. Crews shout load numbers into the sun while cranes swing baskets continuously above the raised lane."),
                _night_layer("Night crews keep the Spine moving under work lamps, but the flow drops enough that individual winches can finally be heard instead of merging into one continuous roar."),
            ),
        ),
        GOBLIN_PATCHWORK_PLAZA_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_BRASSGUT_MARKET_KEY, "Brassgut Market", "You follow the smell of hot metal and market food back into Brassgut."),
                _exit("west", GOBLIN_SORTING_SPINE_KEY, "The Sorting Spine", "You cross toward the raised salvage lanes and moving crane arms."),
                _exit("east", GOBLIN_LEDGER_HALL_KEY, "The Ledger Hall", "You climb two mismatched stone steps into the city's unusually solid contract hall."),
                _exit("north", GOBLIN_FLOODGATE_WALK_KEY, "Floodgate Walk", "You follow the plaza's north edge toward the flood barrier and open swamp air."),
            ),
            features=(
                _feature(
                    "impossible_millwheel", "Impossible Mill Wheel", aliases=("wheel", "mill wheel", "water wheel"),
                    summary="a turning mill wheel mounted where no stream exists",
                    examine="The wheel is not powered here at all. A belt disappears through a wall, crosses a roof, drops through another building, and probably connects to a distant engine. Nobody nearby considers this unusual.",
                    listen="The wheel turns with a slow wooden knock while the hidden belt hisses across its guides.",
                ),
                _feature(
                    "notice_layers", "Layered Notices", aliases=("notices", "posters", "messages", "wall"),
                    summary="years of contracts, warnings, jobs, maps, jokes, and claims pasted over each other",
                    examine="Fresh courier jobs cover old clan warnings; repair advertisements overlap lost-item notices; a careful eye can see whole neighborhoods of obsolete maps underneath newer ones.",
                    search="One recurring symbol points north toward the floodgate whenever a salvage route is considered unsafe. It appears often enough to be worth remembering.",
                ),
                _feature(
                    "public_trough", "Public Water Trough", aliases=("trough", "water", "pump"),
                    summary="a heavily repaired public water trough beneath the turning wheel",
                    examine="The trough is patched with copper, ceramic, pitch, and one flattened cooking pan. The water is clean despite the container's appearance.",
                    touch="The water is cool and surprisingly clear.",
                ),
            ),
            description_layers=(
                _day_layer("Patchwork Plaza is brightest and busiest in the middle of the day. Couriers cut diagonally through crowds, children run messages for coins or favors, and clan representatives conduct business in public shade."),
                _night_layer("At night the plaza opens up. The wheel still turns, late couriers still cross it, and food braziers take over spaces occupied by daytime clerks."),
            ),
        ),
        GOBLIN_TINKER_ROW_KEY: RoomAugmentation(
            exit_overrides=(_exit("south", GOBLIN_SORTING_SPINE_KEY, "The Sorting Spine", "You leave the repair shops and return to the heavier salvage traffic."),),
            features=(
                _feature(
                    "open_workbenches", "Open Workbenches", aliases=("benches", "workbenches", "repair benches"),
                    summary="street-facing benches crowded with tools and half-repaired objects",
                    examine="Vices, files, mismatched screwdrivers, punches, tiny hammers, improvised clamps, soldering irons, and tools with no obvious names cover the benches. Every shop has arranged the chaos differently.",
                    search="Several tools have clearly been made from other broken tools. The repair ecosystem is recursive.",
                    listen="Small hammers, files, ratchets, and arguments produce a finer metallic chatter than the Sorting Spine below.",
                ),
                _feature(
                    "parts_drawers", "Parts Drawers", aliases=("drawers", "parts", "spares"),
                    summary="walls of tiny drawers labeled by function instead of original machine",
                    examine="Labels include SPRINGS THAT PUSH, SPRINGS THAT PULL, SMALL TEETH, BIG TEETH, GLASS ROUNDISH, COPPER BITS, and FITS SOMETHING COMMON.",
                ),
                _feature(
                    "repair_shelf", "Finished Repair Shelf", aliases=("shelf", "finished repairs", "repaired goods"),
                    summary="completed jobs waiting under handwritten claim tags",
                    examine="Every repaired object is tagged with an owner mark and a short note explaining exactly what was fixed—and, often, what was deliberately left unfixed because it was 'still good enough.'",
                ),
            ),
            description_layers=(
                _day_layer("Sunlight reaches almost every open workbench. Repairs spill into the street, apprentices run parts between shops, and customers inspect fixes before carrying them back into the city."),
                _night_layer("Most shutters never fully close; they simply narrow. Blue-white task lamps remain over the benches of repairers who prefer quieter work after the daytime rush."),
            ),
        ),
        GOBLIN_LEDGER_HALL_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", GOBLIN_PATCHWORK_PLAZA_KEY, "Patchwork Plaza", "You leave the stamped contracts behind and return to the open plaza."),),
            features=(
                _feature(
                    "claim_ledgers", "Claim Ledgers", aliases=("ledgers", "books", "records"),
                    summary="heavy books recording salvage ownership, debts, and disputes",
                    examine="The ledgers are dense, cross-referenced, and full of witness marks. Goblin paperwork is less concerned with elegance than with making it impossible for someone to claim they never agreed to something.",
                    touch="The pages are thick and slightly waxed against humidity. Several volumes are heavier than small shields.",
                ),
                _feature(
                    "witness_tables", "Witness Tables", aliases=("tables", "contract tables", "desks"),
                    summary="scarred tables where agreements become enforceable",
                    examine="Each table has ink, chalk, measuring cord, scales, blank tags, and space for witnesses. Knife cuts in the surface suggest some older negotiation traditions have not entirely vanished.",
                ),
                _feature(
                    "clan_seals", "Clan Seals", aliases=("seals", "stamps", "clan stamps"),
                    summary="locked racks of clan and merchant-family stamps",
                    examine="The seals vary from intricate brass dies to carved hardwood blocks. Their storage is one of the few things in Junk City protected by matching locks.",
                ),
            ),
            description_layers=(
                _day_layer("Daylight floods the high windows while clerks, witnesses, runners, and arguing claimants keep every table occupied."),
                _night_layer("The Ledger Hall closes most public tables after dark, leaving only bonded couriers and emergency dispute clerks working under green-shaded lamps."),
            ),
        ),
        GOBLIN_FLOODGATE_WALK_KEY: RoomAugmentation(
            exit_overrides=(_exit("south", GOBLIN_PATCHWORK_PLAZA_KEY, "Patchwork Plaza", "You leave the open swamp view and descend back toward the central city."),),
            features=(
                _feature(
                    "flood_barrier", "Flood Barrier", aliases=("barrier", "floodgate", "wall", "pilings"),
                    summary="a reinforced barrier holding the swamp's seasonal water away from the city core",
                    examine="The barrier has been rebuilt so many times that its age is impossible to guess. Bridge beams, ship ribs, quarried stone, driven pilings, and packed clay all contribute to the same job: keep Junk City where the Goblins put it.",
                    search="Painted height marks record old floods. Some are far above your head.",
                    touch="The nearest timber is damp, tarred, and scarred by years of floating debris.",
                ),
                _feature(
                    "safe_route_checkpoint", "Safe-Route Checkpoint", aliases=("checkpoint", "safe route", "city limit", "warning sign"),
                    summary="the painted line where supervised city traffic gives way to the outer swamp",
                    examine="The sign is direct: CORE TRAFFIC SAFE SOUTH. NORTH ROUTES CHANGE WITH WATER. CLAIM YOUR OWN MISTAKES. Several smaller warnings have been added beneath it by different hands.",
                    listen="Beyond the checkpoint, city noise falls away into insects, water, distant birds, and the occasional metallic crash from salvage crews outside the walls.",
                ),
                _feature(
                    "swamp_routes", "Swamp Routes", aliases=("swamp", "routes", "salvage mounds", "reed beds"),
                    summary="raised paths and salvage fields extending beyond the safe city core",
                    examine="Crooked walkways divide into the reeds, some maintained, some half-submerged, some ending at enormous piles of rusted material dragged from the mud. Nothing beyond the checkpoint looks immediately lethal, but nothing looks supervised either.",
                ),
            ),
            description_layers=(
                _day_layer("In daylight, the entire swamp edge is visible: bright reed water, moving salvage skiffs, distant smoke, and crews picking through exposed piles beyond the safe-route line."),
                _night_layer("At night, the swamp beyond the barrier becomes mostly black water and scattered clan lamps. The city-safe side of the checkpoint feels much more distinct after sunset."),
                DescriptionLayer("goblin_floodgate_rain", "Rain stipples the swamp into gray motion while water rattles through patched spillways beneath the walk.", priority=60, condition=ViewCondition(weather=("rain", "storm"))),
            ),
        ),
    }


def install_goblin_world() -> None:
    """Register the Goblin starter district into the legacy registries before runtime construction."""
    if GOBLIN_START_ROOM_KEY in world.ROOMS_BY_KEY:
        return
    world.ROOMS = world.ROOMS + GOBLIN_ROOMS
    world.ROOMS_BY_KEY.update({room.key: room for room in GOBLIN_ROOMS})
    world.NPCS = world.NPCS + GOBLIN_NPCS
    world.NPCS_BY_KEY.update({npc.key: npc for npc in GOBLIN_NPCS})
