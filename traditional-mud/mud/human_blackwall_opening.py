from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


HUMAN_CINDER_WARD_KEY = "human_cinder_ward"
HUMAN_READINESS_YARD_KEY = "human_blackwall_readiness_yard"
HUMAN_CARAVAN_COURT_KEY = "human_blackwall_caravan_court"
HUMAN_SOOTSTEP_MOUTH_KEY = "human_sootstep_tunnel_mouth"
HUMAN_SOOTSTEP_TUNNEL_KEY = "human_sootstep_service_tunnel"
HUMAN_SMUGGLER_CISTERN_KEY = "human_smuggler_cistern"
HUMAN_ARCHIVE_ANNEX_KEY = "human_blackwall_archive_annex"
HUMAN_OUTER_CARAVAN_ROAD_KEY = "human_outer_caravan_road"

HUMAN_OPENING_ROOM_KEYS = (
    HUMAN_CINDER_WARD_KEY,
    HUMAN_READINESS_YARD_KEY,
    HUMAN_CARAVAN_COURT_KEY,
    HUMAN_SOOTSTEP_MOUTH_KEY,
    HUMAN_SOOTSTEP_TUNNEL_KEY,
    HUMAN_SMUGGLER_CISTERN_KEY,
    HUMAN_ARCHIVE_ANNEX_KEY,
    HUMAN_OUTER_CARAVAN_ROAD_KEY,
)

HUMAN_READINESS_QUEST_KEY = "human_blackwall_readiness"
HUMAN_CARAVAN_QUEST_KEY = "human_blackwall_caravan_damage"
HUMAN_EARTH_CACHE_QUEST_KEY = "human_blackwall_earth_cache"
HUMAN_BEYOND_WALL_QUEST_KEY = "human_blackwall_beyond_wall"

HUMAN_OPENING_COMPLETE_FLAG = "human_blackwall_opening_complete"
HUMAN_OPENING_GRANDFATHERED_FLAG = "human_blackwall_opening_grandfathered"
HUMAN_FAST_LEARNER_DRILL_FLAG = "human_blackwall_fast_learner_drill_seen"
HUMAN_CARAVAN_DEMON_WORD_FLAG = "human_blackwall_demon_word_heard"
HUMAN_DAMAGE_READ_FLAG = "human_blackwall_damage_read"
HUMAN_BURROWER_DEFEATED_FLAG = "human_blackwall_burrower_defeated"
HUMAN_NEST_SEARCHED_FLAG = "human_blackwall_nest_searched"
HUMAN_SMUGGLER_CACHE_FLAG = "human_blackwall_smuggler_cache_found"
HUMAN_EARTH_ARTIFACT_IDENTIFIED_FLAG = "human_blackwall_earth_artifact_identified"
HUMAN_GATE_CLEARANCE_FLAG = "human_blackwall_gate_clearance"
HUMAN_FIRST_OUTSIDE_FLAG = "human_blackwall_first_outside"

HUMAN_EARTH_HANDSET_KEY = "human_dead_glass_handset"
HUMAN_BURROWER_KEY = "human_sootstep_burrower"

SERGEANT_MARA_VEY_KEY = "human_sergeant_mara_vey"
KETTA_BRASSRUN_KEY = "human_dwarf_ketta_brassrun"
ARCHIVIST_ORRIN_VALE_KEY = "human_archivist_orrin_vale"
GATEWARDEN_SERA_THORN_KEY = "human_gatewarden_sera_thorn"


HUMAN_READINESS_QUEST = QuestDefinition(
    key=HUMAN_READINESS_QUEST_KEY,
    name="When the Wall Calls",
    style="structured",
    description=(
        "A routine Blackwall readiness muster teaches the ordinary civic signals that keep the Human capital organized during alarms. "
        "The exercise also gives a small, concrete glimpse of the Human Fast Learner trait before anything dangerous happens."
    ),
    objective_steps=(
        ("report_muster", "Go NORTH from Cinder Ward to the Readiness Yard and TALK MARA."),
        ("inspect_board", "EXAMINE SIGNAL BOARD before attempting the readiness drill."),
        ("drill_signals", "Use DRILL SIGNALS to repeat the wall-call sequence."),
        ("report_ready", "REPORT READY to Sergeant Mara after learning the signal sequence."),
        ("complete", "You completed the ordinary Blackwall readiness muster."),
    ),
)

HUMAN_CARAVAN_QUEST = QuestDefinition(
    key=HUMAN_CARAVAN_QUEST_KEY,
    name="A Wheel Does Not Lie",
    style="structured",
    description=(
        "A damaged Dwarven caravan reaches Blackwall during the readiness muster. Instead of assuming bandits or sabotage, "
        "you are sent to read the actual damage, follow the physical sign, and learn what struck the wagon."
    ),
    objective_steps=(
        ("meet_caravan", "Go EAST from Cinder Ward to Caravan Court and TALK KETTA."),
        ("inspect_wagon", "EXAMINE WAGON before deciding what damaged it."),
        ("read_damage", "READ DAMAGE and compare the axle, harness, road grit, and scrape marks."),
        ("follow_sign", "Go EAST to the Sootstep Tunnel Mouth and FOLLOW SIGN."),
        ("fight_burrower", "Go DOWN into the service tunnel and ATTACK BURROWER."),
        ("search_nest", "After the fight, SEARCH NEST for the rest of the evidence."),
        ("complete", "You proved what struck the caravan and discovered evidence that someone had been using the tunnel in secret."),
    ),
)

HUMAN_EARTH_CACHE_QUEST = QuestDefinition(
    key=HUMAN_EARTH_CACHE_QUEST_KEY,
    name="The Wrong Kind of Old",
    style="structured",
    description=(
        "Fresh Human-made smuggling sign leads to a hidden cistern cache. Among ordinary contraband is an object that looks wrong even beside Astralis's strangest relics. "
        "The Blackwall archive may know what it is."
    ),
    objective_steps=(
        ("search_cache", "Go EAST from the service tunnel into the hidden cistern and SEARCH CACHE."),
        ("return_archive", "Carry the Dead Glass Handset back to Cinder Ward, go WEST to the Archive Annex, and TALK ORRIN."),
        ("complete", "Archivist Orrin identified the dead device as an object made on Earth centuries ago."),
    ),
)

HUMAN_BEYOND_WALL_QUEST = QuestDefinition(
    key=HUMAN_BEYOND_WALL_QUEST_KEY,
    name="Beyond the Blackwall",
    style="structured",
    description=(
        "With the tunnel incident settled, your next lesson is simpler and stranger: leave the Human capital through the Demon Gate and see how Blackwall looks from the outside."
    ),
    objective_steps=(
        ("reach_gate", "Go SOUTH from Cinder Ward to Ashen Way, then SOUTH to the Demon Gate and TALK GATEWARDEN."),
        ("cross_gate", "Travel EAST through the opened caravan gate onto the Outer Caravan Road."),
        ("complete", "You stepped beyond Blackwall and into the wider Astralis that has its own name for your people."),
    ),
)

HUMAN_OPENING_QUESTS = (
    HUMAN_READINESS_QUEST,
    HUMAN_CARAVAN_QUEST,
    HUMAN_EARTH_CACHE_QUEST,
    HUMAN_BEYOND_WALL_QUEST,
)


DEAD_GLASS_HANDSET = ItemDefinition(
    key=HUMAN_EARTH_HANDSET_KEY,
    name="Dead Glass Handset",
    description=(
        "A thin black rectangle with a dead glass face, corroded metal rim, and tiny sealed openings whose purpose is not obvious. "
        "It has no visible magic, no moving parts, and no response to touch. It looks manufactured with a precision that does not match the smuggler cache around it."
    ),
    category="quest_item",
    tier=0,
)

SOOTSTEP_BURROWER = EnemyDefinition(
    key=HUMAN_BURROWER_KEY,
    name="Sootstep Burrower",
    aliases=("burrower", "sootstep", "sootstep burrower", "tunnel beast"),
    description=(
        "a low six-legged tunnel scavenger with slate hide, shovel claws, and a jaw stained black from chewing old drain pitch"
    ),
    max_hp=22,
    armor_class=3,
    auto_attack_damage=2,
    auto_attack_interval=3.4,
    xp_reward=30,
    retaliates=True,
    tutorial=False,
)


SERGEANT_MARA_VEY = NpcDefinition(
    key=SERGEANT_MARA_VEY_KEY,
    name="Sergeant Mara Vey",
    short_description="a Blackwall watch sergeant with a signal slate tucked under one arm and rain darkening her uniform shoulders",
    room_key=HUMAN_READINESS_YARD_KEY,
    role="Human opening mentor and civic-readiness instructor",
    dialogue=(
        "Mara taps the signal slate. 'Readiness is mostly knowing what to do before somebody makes the alarm dramatic.'",
        "'The wall is strong because thousands of boring things happen correctly every day.'",
    ),
)

KETTA_BRASSRUN = NpcDefinition(
    key=KETTA_BRASSRUN_KEY,
    name="Ketta Brassrun",
    short_description="a stocky Dwarven caravan master crouched beside a split wheel hub with road grit across both sleeves",
    room_key=HUMAN_CARAVAN_COURT_KEY,
    role="neighboring Dwarven caravan master and first outsider contact",
    dialogue=(
        "Ketta presses a thumb into the damaged hub. 'I can replace wood. I would rather know why I am replacing it.'",
        "'Roads tell on whatever used them. Wheels do too.'",
    ),
)

ARCHIVIST_ORRIN_VALE = NpcDefinition(
    key=ARCHIVIST_ORRIN_VALE_KEY,
    name="Archivist Orrin Vale",
    short_description="an elderly Human archivist in an ink-stained coat arranging inert relics in padded blackwood trays",
    room_key=HUMAN_ARCHIVE_ANNEX_KEY,
    role="keeper of surviving Earth material and historical records",
    dialogue=(
        "Orrin adjusts a padded tray. 'An artifact is not valuable because it is useful. Sometimes it matters because it proves a story was real.'",
        "'We have excellent records of people leaving Earth. We have no record of anyone learning how to return.'",
    ),
)

GATEWARDEN_SERA_THORN = NpcDefinition(
    key=GATEWARDEN_SERA_THORN_KEY,
    name="Gatewarden Sera Thorn",
    short_description="a senior Blackwall gate officer standing beside the outbound caravan chain and its iron release wheel",
    room_key=legacy_world.HUMAN_START_ROOM_KEY,
    role="Demon Gate outbound officer and Human opening handoff",
    dialogue=(
        "Sera rests one hand on the release wheel. 'Inside the wall, Demon is decoration. Outside, remember that somebody may be saying it because they have never met one of us.'",
    ),
)

HUMAN_OPENING_NPCS = (
    SERGEANT_MARA_VEY,
    KETTA_BRASSRUN,
    ARCHIVIST_ORRIN_VALE,
    GATEWARDEN_SERA_THORN,
)


HUMAN_OPENING_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=HUMAN_CINDER_WARD_KEY,
        name="Cinder Ward",
        region_key="human_kingdom",
        description=(
            "Cinder Ward sits just inside Blackwall where homes, watch offices, guild storehouses, and public cisterns crowd against the immense dark fortification. "
            "Horned rainspouts and little iron gargoyles decorate ordinary doorframes with the same demonic imagery used across the capital. To people raised here it reads as civic style, not menace. "
            "A readiness yard lies north, caravan traffic gathers east, and a quiet archive annex occupies an older building to the west. Ashen Way climbs south toward the heart of the city."
        ),
        exits={
            "north": HUMAN_READINESS_YARD_KEY,
            "east": HUMAN_CARAVAN_COURT_KEY,
            "west": HUMAN_ARCHIVE_ANNEX_KEY,
            "south": "human_ashen_way",
        },
        tags=("human_start", "blackwall", "residential", "watch_district", "safe"),
    ),
    RoomDefinition(
        key=HUMAN_READINESS_YARD_KEY,
        name="Blackwall Readiness Yard",
        region_key="human_kingdom",
        description=(
            "A rectangular stone yard has been painted with evacuation lanes, bucket lines, muster numbers, and three large wall-signal symbols. "
            "Nothing about the place feels heroic. Bakers, apprentices, clerks, guards, and laborers all use the same boards during routine drills so the district can react without waiting for a champion."
        ),
        exits={"south": HUMAN_CINDER_WARD_KEY},
        npc_keys=(SERGEANT_MARA_VEY_KEY,),
        tags=("blackwall", "safe", "civic_training", "readiness"),
    ),
    RoomDefinition(
        key=HUMAN_CARAVAN_COURT_KEY,
        name="Caravan Court",
        region_key="human_kingdom",
        description=(
            "A broad paved court handles freight that has already passed Blackwall customs. Dwarven carts are common enough that wheel gauges are marked directly into the paving stones. "
            "Today one squat mountain wagon sits crooked on a jack, its right rear wheel split and its undercarriage scored with fresh black grit."
        ),
        exits={"west": HUMAN_CINDER_WARD_KEY, "east": HUMAN_SOOTSTEP_MOUTH_KEY},
        npc_keys=(KETTA_BRASSRUN_KEY,),
        tags=("blackwall", "safe", "caravan", "dwarf_contact", "investigation"),
    ),
    RoomDefinition(
        key=HUMAN_SOOTSTEP_MOUTH_KEY,
        name="Sootstep Tunnel Mouth",
        region_key="human_kingdom",
        description=(
            "An old storm-service opening yawns beneath the freight road where Blackwall's foundations meet older brickwork. Fresh wheel gouges stop above it. "
            "Black grit has been kicked from the drain lip onto the road, and a torn strip of leather hangs from a broken iron staple. A maintenance stair descends into darkness."
        ),
        exits={"west": HUMAN_CARAVAN_COURT_KEY, "down": HUMAN_SOOTSTEP_TUNNEL_KEY},
        tags=("blackwall", "tunnel", "investigation", "danger_hint"),
    ),
    RoomDefinition(
        key=HUMAN_SOOTSTEP_TUNNEL_KEY,
        name="Sootstep Service Tunnel",
        region_key="human_kingdom",
        description=(
            "The service tunnel runs between sweating brick, old drain channels, and massive black foundation stones. Sooty animal tracks overlap with fresher boot marks. "
            "Something has nested among broken maintenance crates near the east wall, where a patched timber shutter has been fitted into masonry that should have been solid."
        ),
        exits={"up": HUMAN_SOOTSTEP_MOUTH_KEY, "east": HUMAN_SMUGGLER_CISTERN_KEY},
        tags=("blackwall", "tunnel", "investigation", "combat", "smuggling_hint"),
    ),
    RoomDefinition(
        key=HUMAN_SMUGGLER_CISTERN_KEY,
        name="Hidden Cistern Cache",
        region_key="human_kingdom",
        description=(
            "Behind the patched shutter is a dry cistern no longer connected to the public water system. Bundles wrapped in oilcloth sit on raised bricks beside coils of new rope, false-bottom crates, and customs seals scraped almost clean. "
            "The hiding place is crude but current. Whoever uses it knows Blackwall from the inside."
        ),
        exits={"west": HUMAN_SOOTSTEP_TUNNEL_KEY},
        tags=("blackwall", "hidden_room", "smuggling", "earth_artifact", "investigation"),
    ),
    RoomDefinition(
        key=HUMAN_ARCHIVE_ANNEX_KEY,
        name="Blackwall Archive Annex",
        region_key="human_kingdom",
        description=(
            "A narrow civic archive occupies a converted watch chapel. Most shelves hold ordinary tax ledgers, repair records, old maps, and immigration rolls. "
            "One locked wall of padded cases is different: dead mechanisms, fragments of unfamiliar polymers, printed scraps under glass, and other objects preserved because the oldest Human records say they came from Earth."
        ),
        exits={"east": HUMAN_CINDER_WARD_KEY},
        npc_keys=(ARCHIVIST_ORRIN_VALE_KEY,),
        tags=("blackwall", "archive", "earth_history", "safe"),
    ),
    RoomDefinition(
        key=HUMAN_OUTER_CARAVAN_ROAD_KEY,
        name="Outer Caravan Road",
        region_key="human_kingdom",
        description=(
            "The road outside Blackwall is wider than it looked through the gate. Behind you, the city wall rises like a dark cliff bristling with towers and horned stonework. "
            "Ahead, wagon tracks divide toward farms, Dwarven trade roads, and routes not yet mapped into the local starter district. Travelers who barely glanced at you inside the gate look twice out here."
        ),
        exits={"west": legacy_world.HUMAN_START_ROOM_KEY},
        tags=("outside_city", "caravan_road", "world_handoff", "human_identity"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
    )


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _layer(key: str, text: str) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=45, condition=ViewCondition())


def human_opening_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HUMAN_CINDER_WARD_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", HUMAN_READINESS_YARD_KEY, "Readiness Yard", "You follow painted muster marks north into the readiness yard."),
                _exit("east", HUMAN_CARAVAN_COURT_KEY, "Caravan Court", "You pass under a freight arch into the caravan court."),
                _exit("west", HUMAN_ARCHIVE_ANNEX_KEY, "Archive Annex", "You enter the quiet converted watch chapel used by the archive."),
                _exit("south", "human_ashen_way", "Ashen Way", "You leave the ward and climb toward the busier avenue."),
            ),
            features=(
                _feature("cinder_relief", "Blackwall Relief", "a horned stone relief worn smooth by generations of passing hands", "The carved face would look threatening on a foreign temple. Here children have polished one horn smooth by grabbing it on the way past.", ("relief", "horned relief")),
                _feature("ward_cistern", "Ward Cistern", "a public iron pump beside a row of fire buckets", "The pump, buckets, and painted lane numbers are maintained with almost obsessive regularity. Blackwall readiness is built into ordinary street furniture.", ("cistern", "pump", "fire buckets")),
            ),
            description_layers=(_layer("cinder_daily", "Watch clerks and residents move through the ward with the bored familiarity of people living beside one of Astralis's most intimidating walls."),),
        ),
        HUMAN_READINESS_YARD_KEY: RoomAugmentation(
            exit_overrides=(_exit("south", HUMAN_CINDER_WARD_KEY, "Cinder Ward", "You step back into Cinder Ward."),),
            features=(
                _feature("readiness_signal_board", "Signal Board", "three large wall-call symbols painted beside short written instructions", "One symbol means gather by household count, one means clear the freight lanes, and one means form a bucket line without waiting for a watch officer. The order is deliberately simple enough to remember under stress.", ("signal board", "signals", "board")),
                _feature("readiness_rack", "Readiness Rack", "a rack of buckets, hooks, blankets, and chalk slates", "Most of the equipment is not weaponry. The drill is about preventing panic, moving people, and keeping small emergencies small.", ("rack", "gear rack", "equipment rack")),
            ),
            description_layers=(_layer("readiness_daily", "Somebody is always running a mundane drill here: counting households, checking hooks, or timing how quickly a freight lane can be cleared."),),
        ),
        HUMAN_CARAVAN_COURT_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", HUMAN_CINDER_WARD_KEY, "Cinder Ward", "You leave the freight paving and return to the ward."),
                _exit("east", HUMAN_SOOTSTEP_MOUTH_KEY, "Sootstep Tunnel Mouth", "You follow the damaged wagon's road sign toward the old service opening."),
            ),
            features=(
                _feature("damaged_dwarf_wagon", "Damaged Dwarven Wagon", "a squat mountain wagon jacked up over a split rear wheel", "The wheel is damaged, but the more interesting marks are underneath: black grit, a deep upward strike on the axle housing, and leather torn low rather than cut from above.", ("wagon", "damaged wagon", "dwarven wagon", "wheel")),
                _feature("wheel_gauges", "Wheel-Gauge Stones", "brass lines set into the paving for common Dwarven wagon widths", "The measurements are old and frequently used. Dwarven freight is routine enough here that Blackwall built parts of the court around it.", ("gauges", "stones", "wheel gauges")),
            ),
            description_layers=(_layer("caravan_daily", "Freight crews work around the damaged wagon without treating the Dwarven visitors as unusual. The border between the two peoples is cultural, not closed."),),
        ),
        HUMAN_SOOTSTEP_MOUTH_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", HUMAN_CARAVAN_COURT_KEY, "Caravan Court", "You climb back toward the freight court."),
                _exit("down", HUMAN_SOOTSTEP_TUNNEL_KEY, "Service Tunnel", "You descend the narrow maintenance stair into the soot-dark tunnel."),
            ),
            features=(
                _feature("sootstep_gouge", "Road Gouge", "a fresh gouge where something heavy struck upward from below", "The gouge is too low for a roadside attacker and too irregular for a tool. Black grit packed into it matches the service opening beneath the road.", ("gouge", "road gouge", "axle sign")),
                _feature("sootstep_leather", "Torn Harness Leather", "a strip of wagon harness caught on a broken drain staple", "The leather was dragged toward the tunnel mouth after tearing. Whatever hit the wagon moved below road level, then retreated here.", ("leather", "harness", "torn leather")),
            ),
            description_layers=(_layer("sootstep_air", "Cool drain air carries soot, damp brick, and the faint animal musk of something that has been using the old service route."),),
        ),
        HUMAN_SOOTSTEP_TUNNEL_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("up", HUMAN_SOOTSTEP_MOUTH_KEY, "Tunnel Mouth", "You climb toward daylight and the freight road."),
                _exit("east", HUMAN_SMUGGLER_CISTERN_KEY, "Patched Shutter", "You squeeze through the patched shutter into the hidden cistern beyond."),
            ),
            features=(
                _feature("burrower_nest", "Burrower Nest", "a heap of pitch scraps, chewed leather, and broken maintenance packing", "The animal nest contains wagon leather and black road pitch, but also a clean-cut length of new Human rope that no burrowing animal carried here by accident.", ("nest", "animal nest", "burrower nest")),
                _feature("patched_shutter", "Patched Timber Shutter", "a recent timber panel fitted into much older masonry", "Fresh tool marks, city nails, and a thumb smear of black customs wax make the shutter look less like forgotten infrastructure and more like a door somebody wanted mistaken for repair work.", ("shutter", "timber shutter", "hidden door")),
            ),
            description_layers=(_layer("tunnel_drips", "Water ticks somewhere behind the brick while soot shifts underfoot around tracks both clawed and booted."),),
        ),
        HUMAN_SMUGGLER_CISTERN_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", HUMAN_SOOTSTEP_TUNNEL_KEY, "Patched Shutter", "You return through the false repair panel to the service tunnel."),),
            features=(
                _feature("smuggler_cache", "Smuggler Cache", "oilcloth bundles and false-bottom crates raised above the dry floor", "Most of it is boring contraband: untaxed dye, spirits, foreign tool steel, and copied customs seals. The rope, ration wrappers, and sealing wax are all current Blackwall issue. These smugglers are Human, or work closely with Humans inside the wall.", ("cache", "crates", "contraband", "smuggler cache")),
                _feature("dead_glass_shape", "Black Glass Object", "a thin black rectangle wrapped separately from the ordinary contraband", "Its dead glass face and seamless edges do not resemble Dwarven clockwork, Goblin salvage, or any ordinary Human craft you know. It is inert and strangely precise.", ("device", "glass object", "black glass", "rectangle")),
            ),
            description_layers=(_layer("cistern_secret", "The cache smells of oilcloth and old stone. Nothing about it is ancient except one carefully wrapped object that does not belong with the rest."),),
        ),
        HUMAN_ARCHIVE_ANNEX_KEY: RoomAugmentation(
            exit_overrides=(_exit("east", HUMAN_CINDER_WARD_KEY, "Cinder Ward", "You leave the quiet archive for the ward street."),),
            features=(
                _feature("earth_cases", "Earth Cases", "locked padded cases holding inert relics from the oldest Human collections", "Labels describe materials and purposes more confidently than the objects themselves: polymer housings, printed circuits, fragments of synthetic cloth, dead batteries, and pieces of machines no one can repair.", ("cases", "earth cases", "relic cases")),
                _feature("route_maps", "Dimensional Route Maps", "copies of early Human diagrams showing the one-way crossing into Astralis", "The maps are detailed about departure and almost blank about return. Later archivists added centuries of notes, none describing a verified path back to Earth.", ("maps", "route maps", "dimensional maps")),
            ),
            description_layers=(_layer("archive_hush", "The annex is quieter than the street by design. Here the Human origin story is filed beside tax rolls instead of told as legend."),),
        ),
        HUMAN_OUTER_CARAVAN_ROAD_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", legacy_world.HUMAN_START_ROOM_KEY, "Demon Gate", "You walk back toward Blackwall until the gate swallows the road."),),
            features=(
                _feature("blackwall_silhouette", "Blackwall", "the Human capital's immense dark fortification dominating the western horizon", "From outside, the horned towers and carved faces stop looking like familiar civic decoration. You can understand why a traveler seeing the city for the first time might have chosen the word Demon before learning anyone's name.", ("wall", "blackwall", "city wall")),
                _feature("caravan_markers", "Caravan Road Markers", "stone posts naming farms, Dwarven trade routes, and roads beyond the starter district", "The nearest posts are practical and heavily worn. Several farther destinations are not yet mapped into the playable local routes, but the road clearly belongs to a much larger world.", ("markers", "road markers", "posts")),
            ),
            description_layers=(_layer("outer_attention", "Passing travelers look at Blackwall, then at you, with the extra half-second of attention that never happens inside your own streets."),),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if existing.key == room.key else existing for existing in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if existing.key == npc.key else existing for existing in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _patched_demon_gate() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[legacy_world.HUMAN_START_ROOM_KEY]
    exits = dict(original.exits)
    exits["east"] = HUMAN_OUTER_CARAVAN_ROAD_KEY
    npc_keys = tuple(dict.fromkeys(original.npc_keys + (GATEWARDEN_SERA_THORN_KEY,)))
    return replace(original, exits=exits, npc_keys=npc_keys)


def _patch_demon_gate_augmentation(world_service) -> None:
    gate = _patched_demon_gate()
    base = world_service.augmentations.get(gate.key, RoomAugmentation())
    exits = tuple(exit_def for exit_def in base.exit_overrides if exit_def.direction != "east") + (
        _exit("east", HUMAN_OUTER_CARAVAN_ROAD_KEY, "Outer Caravan Road", "The outbound caravan chain drops and the eastern road opens beyond Blackwall."),
    )
    feature = _feature(
        "outbound_caravan_chain",
        "Outbound Caravan Chain",
        "a black iron chain controlling the road lane through the outer gate",
        "The chain is heavy enough to stop a freight wagon and simple enough to release in seconds. Gatewarden Sera Thorn controls it from an iron wheel beside the arch.",
        ("chain", "caravan chain", "outbound gate"),
    )
    features = base.features if any(existing.key == feature.key for existing in base.features) else base.features + (feature,)
    layer = _layer("blackwall_outbound_lane", "One gate lane is reserved for outbound caravans and travelers cleared to leave the capital.")
    layers = base.description_layers if any(existing.key == layer.key for existing in base.description_layers) else base.description_layers + (layer,)
    world_service.augmentations[gate.key] = replace(base, exit_overrides=exits, features=features, description_layers=layers)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(gate.key, None)


def install_human_blackwall_content(world_service=None) -> None:
    for quest in HUMAN_OPENING_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    if DEAD_GLASS_HANDSET.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (DEAD_GLASS_HANDSET,)
    crafting.ITEMS_BY_KEY[DEAD_GLASS_HANDSET.key] = DEAD_GLASS_HANDSET

    if HUMAN_BURROWER_KEY not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (SOOTSTEP_BURROWER,)
    combat.ENEMIES_BY_KEY[HUMAN_BURROWER_KEY] = SOOTSTEP_BURROWER

    for npc in HUMAN_OPENING_NPCS:
        _replace_npc(npc)
    for room in HUMAN_OPENING_ROOMS:
        _replace_room(room)
    gate = _patched_demon_gate()
    _replace_room(gate)

    if world_service is not None:
        for room in HUMAN_OPENING_ROOMS:
            world_service.legacy_rooms[room.key] = room
        world_service.legacy_rooms[gate.key] = gate
        world_service.augmentations.update(human_opening_augmentations())
        _patch_demon_gate_augmentation(world_service)
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in HUMAN_OPENING_ROOM_KEYS:
                cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _step(session, key: str) -> str | None:
    quest = _quest(session, key)
    if quest and quest.get("status") == "active":
        return quest.get("current_step")
    return None


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _old_human_progress_exists(session) -> bool:
    if session.character is None:
        return False
    cathedral = _quest(session, quests.HUMAN_CATHEDRAL_SUMMONS.key)
    training = _quest(session, quests.HUMAN_COMBAT_TRAINING.key)
    lower = _quest(session, quests.HUMAN_LOWER_WARDS_INVESTIGATION.key)
    if training is not None or lower is not None:
        return True
    if cathedral is None:
        return False
    if cathedral.get("status") == "completed":
        return True
    return cathedral.get("current_step") not in {None, "read_note", "await_blackwall_handoff"}


def prepare_human_blackwall_opening(session) -> bool:
    """Move fresh/untouched Humans into the new opening without resetting older progress."""
    if session.character is None or session.character.race != "human":
        return False
    flags = _flags(session)
    if HUMAN_OPENING_COMPLETE_FLAG in flags or HUMAN_OPENING_GRANDFATHERED_FLAG in flags:
        return False
    if _quest(session, HUMAN_READINESS_QUEST_KEY) is not None:
        return False

    if _old_human_progress_exists(session):
        session.database.grant_flag(session.character.id, HUMAN_OPENING_GRANDFATHERED_FLAG)
        return False

    session.database.start_quest(session.character.id, HUMAN_READINESS_QUEST_KEY, "report_muster")
    cathedral = _quest(session, quests.HUMAN_CATHEDRAL_SUMMONS.key)
    if cathedral is None:
        session.database.start_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key, "await_blackwall_handoff")
    elif cathedral.get("status") == "active" and cathedral.get("current_step") == "read_note":
        session.database.advance_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key, "await_blackwall_handoff")

    session.database.set_character_room(session.character.id, HUMAN_CINDER_WARD_KEY)
    session.database.set_bind_room(session.character.id, HUMAN_CINDER_WARD_KEY)
    _refresh_character(session)
    return True


def _start_quest_if_missing(session, quest: QuestDefinition, step: str) -> None:
    assert session.character is not None
    if _quest(session, quest.key) is None:
        session.database.start_quest(session.character.id, quest.key, step)


def _complete_and_start(session, completed: QuestDefinition, next_quest: QuestDefinition, next_step: str) -> None:
    assert session.character is not None
    session.database.complete_quest(session.character.id, completed.key)
    _start_quest_if_missing(session, next_quest, next_step)


def _matches_talk(command: str, *names: str) -> bool:
    text = command.strip().lower()
    if not text.startswith("talk"):
        return False
    target = text[4:].strip().removeprefix("to ").strip()
    return target in set(names)


async def _talk_mara(session) -> bool:
    if session.character is None or session.character.current_room != HUMAN_READINESS_YARD_KEY:
        return False
    step = _step(session, HUMAN_READINESS_QUEST_KEY)
    if step == "report_muster":
        session.database.advance_quest(session.character.id, HUMAN_READINESS_QUEST_KEY, "inspect_board")
        await session.send(
            "\r\nMara checks your name against a slate. 'Routine muster. No emergency, which is the best time to learn one.'\r\n"
            "She points to the painted board. 'EXAMINE SIGNAL BOARD. I want you to understand the three calls before you repeat them.'\r\n"
        )
        return True
    if step == "report_ready":
        _complete_and_start(session, HUMAN_READINESS_QUEST, HUMAN_CARAVAN_QUEST, "meet_caravan")
        await session.send(
            "\r\nMara marks the slate. 'Good. Fast, too. Keep that habit and lose the need to show off about it.'\r\n"
            "Before she can dismiss you, a freight bell sounds twice from the east. A Dwarven wagon has limped into Caravan Court with a split wheel and damage nobody can explain yet.\r\n"
            "\r\nQuest complete: When the Wall Calls.\r\n"
            "New quest: A Wheel Does Not Lie. Go EAST from Cinder Ward and TALK KETTA.\r\n"
        )
        return True
    await session.send("\r\nMara glances at the signal slate. 'Do the useful part in the order you were given.'\r\n")
    return True


async def _talk_ketta(session) -> bool:
    if session.character is None or session.character.current_room != HUMAN_CARAVAN_COURT_KEY:
        return False
    step = _step(session, HUMAN_CARAVAN_QUEST_KEY)
    if step == "meet_caravan":
        session.database.grant_flag(session.character.id, HUMAN_CARAVAN_DEMON_WORD_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "inspect_wagon")
        await session.send(
            "\r\nKetta Brassrun looks up from the jack. 'Your demons keep a better freight court than the north cut, I'll give you that. Shame the road outside tried to eat my axle.'\r\n"
            "She says demons the way she says freight court: casually, without insult or apology. Two Blackwall porters keep working. Nobody corrects her.\r\n"
            "Ketta taps the wheel hub. 'Do me a favor and look before somebody decides this was bandits. EXAMINE WAGON.'\r\n"
        )
        return True
    await session.send("\r\nKetta wipes road grit from one hand. 'Damage first. Story second.'\r\n")
    return True


async def _talk_orrin(session) -> bool:
    if session.character is None or session.character.current_room != HUMAN_ARCHIVE_ANNEX_KEY:
        return False
    step = _step(session, HUMAN_EARTH_CACHE_QUEST_KEY)
    if step != "return_archive":
        await session.send("\r\nOrrin nods toward the locked cases. 'Most of our past is paper describing things we can no longer make. Sometimes an object survives the description.'\r\n")
        return True
    if session.database.item_quantity(session.character.id, HUMAN_EARTH_HANDSET_KEY) <= 0:
        await session.send("\r\nOrrin holds out a padded tray. 'You said you found an object. Bring it to me intact.'\r\n")
        return True

    session.database.consume_item(session.character.id, HUMAN_EARTH_HANDSET_KEY, 1)
    session.database.grant_flag(session.character.id, HUMAN_EARTH_ARTIFACT_IDENTIFIED_FLAG)
    _complete_and_start(session, HUMAN_EARTH_CACHE_QUEST, HUMAN_BEYOND_WALL_QUEST, "reach_gate")
    await session.send(
        "\r\nOrrin does not recognize the object immediately. That is somehow more unsettling than if he had. He brings out an old illustrated catalog, compares the proportions twice, then sits down.\r\n"
        "'Earth,' he says. 'A personal communications handset. Dead, obviously. The power system is gone, the network it expected is gone, and nobody living could make it speak again.'\r\n"
        "He turns the black glass under the lamp. 'Our ancestors crossed intentionally. We know that much. They brought objects like this with them. What we do not have—after centuries of looking—is a road back.'\r\n"
        "Orrin places the handset in a padded tray rather than trying to activate it. 'Useful? No. Important? Yes. It means the old story touched your hands.'\r\n"
        "\r\nQuest complete: The Wrong Kind of Old.\r\n"
        "New quest: Beyond the Blackwall. Go to the Demon Gate and TALK GATEWARDEN.\r\n"
    )
    return True


async def _talk_gatewarden(session) -> bool:
    if session.character is None or session.character.current_room != legacy_world.HUMAN_START_ROOM_KEY:
        return False
    step = _step(session, HUMAN_BEYOND_WALL_QUEST_KEY)
    if step == "reach_gate":
        session.database.grant_flag(session.character.id, HUMAN_GATE_CLEARANCE_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_BEYOND_WALL_QUEST_KEY, "cross_gate")
        await session.send(
            "\r\nGatewarden Sera Thorn checks your ward mark, then releases the outbound caravan chain with three turns of the iron wheel.\r\n"
            "'Inside Blackwall, Demon is carved over bakeries and school doors. Outside, someone may say it because all they know about you is a story.'\r\n"
            "She nods toward the open road. 'Go EAST. See the wall from their side once.'\r\n"
        )
        return True
    await session.send("\r\nSera keeps one hand near the release wheel. 'The gate is a road, not a finish line.'\r\n")
    return True


async def handle_human_opening_command(session, command: str) -> bool:
    if session.character is None or session.character.race != "human":
        return False
    normalized = command.strip().lower()
    room = session.character.current_room

    if normalized.startswith("talk"):
        if _matches_talk(command, "mara", "sergeant", "sergeant mara", "mara vey", "sergeant mara vey"):
            return await _talk_mara(session)
        if _matches_talk(command, "ketta", "ketta brassrun", "caravan master", "dwarf", "dwarven caravan master"):
            return await _talk_ketta(session)
        if _matches_talk(command, "orrin", "orrin vale", "archivist", "archivist orrin", "archivist orrin vale"):
            return await _talk_orrin(session)
        if _matches_talk(command, "gatewarden", "sera", "sera thorn", "gatewarden sera", "gatewarden sera thorn"):
            return await _talk_gatewarden(session)

    readiness_step = _step(session, HUMAN_READINESS_QUEST_KEY)
    if room == HUMAN_READINESS_YARD_KEY and normalized in {"examine signal board", "inspect signal board", "look signal board", "examine signals", "read signals"}:
        if readiness_step == "inspect_board":
            session.database.advance_quest(session.character.id, HUMAN_READINESS_QUEST_KEY, "drill_signals")
            await session.send(
                "\r\nThe board reduces a district emergency to three actions: COUNT at the household marks, CLEAR the freight lane, then FORM the bucket line if the third bell sounds. No flourish, no secret code.\r\n"
                "Mara watches from across the yard. DRILL SIGNALS when you have it.\r\n"
            )
        else:
            await session.send("\r\nThe three readiness calls remain exactly where the watch painted them: count, clear, form.\r\n")
        return True

    if room == HUMAN_READINESS_YARD_KEY and normalized in {"drill signals", "practice signals", "repeat signals", "run drill", "practice drill"}:
        if readiness_step != "drill_signals":
            await session.send("\r\nMara points back to the board. 'Understand it before you perform it.'\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_FAST_LEARNER_DRILL_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_READINESS_QUEST_KEY, "report_ready")
        await session.send(
            "\r\nYou run the sequence once: household count, freight lane clear, bucket line formed on the third call. On the second pass Mara stops you before you begin.\r\n"
            "'You have it. Humans usually do once the pattern has a reason behind it. Fast Learner is only useful if you spend the saved time noticing what changed.'\r\n"
            "REPORT READY.\r\n"
        )
        return True

    if room == HUMAN_READINESS_YARD_KEY and normalized in {"report ready", "report readiness", "ready", "finish drill"}:
        if readiness_step == "report_ready":
            return await _talk_mara(session)
        await session.send("\r\nYou are not ready to report the drill complete yet.\r\n")
        return True

    caravan_step = _step(session, HUMAN_CARAVAN_QUEST_KEY)
    if room == HUMAN_CARAVAN_COURT_KEY and normalized in {"examine wagon", "inspect wagon", "look wagon", "examine wheel", "inspect wheel", "examine damaged wagon"}:
        if caravan_step == "inspect_wagon":
            session.database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "read_damage")
            await session.send(
                "\r\nThe obvious break is the wheel, but it broke after something hit the undercarriage from below and behind. One harness strap tore downward. Black grit is packed into the axle housing, and a broad claw scrape crosses the lower brace.\r\n"
                "The wagon was damaged by something low to the road, not by a weapon swung from beside it. READ DAMAGE before following the sign.\r\n"
            )
        else:
            await session.send("\r\nThe wagon still shows the same low strike, black grit, and torn harness sign.\r\n")
        return True

    if room == HUMAN_CARAVAN_COURT_KEY and normalized in {"read damage", "trace damage", "read sign", "analyze damage", "assess damage"}:
        if caravan_step != "read_damage":
            await session.send("\r\nStart with the wagon itself. EXAMINE WAGON before deciding what the marks mean.\r\n")
            return True
        session.database.grant_flag(session.character.id, HUMAN_DAMAGE_READ_FLAG)
        session.database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "follow_sign")
        await session.send(
            "\r\nThe black grit is drain pitch. The claw angle rises toward the wagon, then turns east. A dragged strip of harness leather continues toward the old Sootstep service opening.\r\n"
            "Ketta was right: the wheel does not tell a bandit story. Go EAST and FOLLOW SIGN at the tunnel mouth.\r\n"
        )
        return True

    if room == HUMAN_SOOTSTEP_MOUTH_KEY and normalized in {"follow sign", "follow tracks", "track damage", "track burrower", "follow damage"}:
        if caravan_step != "follow_sign":
            await session.send("\r\nThere is sign here, but you have not yet established what you are following. Read the wagon damage first.\r\n")
            return True
        session.database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "fight_burrower")
        await session.send(
            "\r\nYou follow the dragged leather and broad claw prints over the drain lip. The animal came up beneath the road, struck the wagon in panic or hunger, then retreated DOWN into the service tunnel.\r\n"
            "Fresh boot scuffs overlap the animal tracks. Someone else has been using the same tunnel. Go DOWN and ATTACK BURROWER.\r\n"
        )
        return True

    if room == HUMAN_SOOTSTEP_TUNNEL_KEY and normalized in {"search nest", "search burrower nest", "examine nest", "inspect nest"}:
        if caravan_step == "fight_burrower":
            await session.send("\r\nThe burrower is still defending the nest. Deal with the threat first.\r\n")
            return True
        if caravan_step != "search_nest":
            if HUMAN_NEST_SEARCHED_FLAG in _flags(session):
                await session.send("\r\nYou already separated the animal sign from the fresh Human-made evidence here.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, HUMAN_NEST_SEARCHED_FLAG)
        _complete_and_start(session, HUMAN_CARAVAN_QUEST, HUMAN_EARTH_CACHE_QUEST, "search_cache")
        await session.send(
            "\r\nThe nest explains the wagon: pitch scraps, chewed leather, and the same black grit from the axle. But under the nesting material is a clean-cut length of new rope stamped with a Blackwall stores mark.\r\n"
            "The patched shutter in the east wall has fresh city nails and customs wax on its edge. The animal found the tunnel by chance. Someone inside Blackwall was already using it deliberately.\r\n"
            "\r\nQuest complete: A Wheel Does Not Lie.\r\n"
            "New quest: The Wrong Kind of Old. The hidden shutter to the EAST can now be investigated.\r\n"
        )
        return True

    earth_step = _step(session, HUMAN_EARTH_CACHE_QUEST_KEY)
    if room == HUMAN_SMUGGLER_CISTERN_KEY and normalized in {"search cache", "search smuggler cache", "search crates", "inspect cache", "examine cache"}:
        if earth_step != "search_cache":
            if HUMAN_SMUGGLER_CACHE_FLAG in _flags(session):
                await session.send("\r\nThe cache has already given up its useful evidence.\r\n")
                return True
            return False
        session.database.grant_flag(session.character.id, HUMAN_SMUGGLER_CACHE_FLAG)
        if session.database.item_quantity(session.character.id, HUMAN_EARTH_HANDSET_KEY) <= 0:
            session.database.add_item(session.character.id, HUMAN_EARTH_HANDSET_KEY, 1)
        session.database.advance_quest(session.character.id, HUMAN_EARTH_CACHE_QUEST_KEY, "return_archive")
        await session.send(
            "\r\nMost of the cache is ordinary smuggling: untaxed dye, spirits, foreign tool steel, copied seals. The rope, ration wrappers, and wax are Human issue. This is not an outsider hideout.\r\n"
            "Wrapped separately is a thin black rectangle with a dead glass face. You do not recognize the material stack or its purpose. It does nothing when touched.\r\n"
            "You take the Dead Glass Handset as evidence. Return to the Blackwall Archive Annex and TALK ORRIN.\r\n"
        )
        return True

    if normalized in {"examine dead glass handset", "examine handset", "look handset", "inspect handset", "examine device", "look device"} and session.database.item_quantity(session.character.id, HUMAN_EARTH_HANDSET_KEY) > 0:
        await session.send(
            "\r\nThe object is too precise to be crude salvage and too inert to be obvious magic. Its glass face is completely dead. Tiny sealed openings and a corroded metal edge suggest a manufactured purpose you were never taught to recognize.\r\n"
        )
        return True

    if normalized in {"read note", "read cathedral note", "read sealed note", "read sealed cathedral note"}:
        readiness = _quest(session, HUMAN_READINESS_QUEST_KEY)
        opening_active = readiness is not None and HUMAN_OPENING_COMPLETE_FLAG not in _flags(session) and HUMAN_OPENING_GRANDFATHERED_FLAG not in _flags(session)
        if opening_active:
            await session.send(
                "\r\nThe cathedral note is sealed and valid, but Blackwall readiness duty is already in progress. Finish the immediate ward assignment before answering a separate summons across the city.\r\n"
            )
            return True

    return False


def _burrower_target(text: str) -> bool:
    return SOOTSTEP_BURROWER.matches(text)


def record_burrower_defeat(session) -> bool:
    if session.character is None or _step(session, HUMAN_CARAVAN_QUEST_KEY) != "fight_burrower":
        return False
    session.database.grant_flag(session.character.id, HUMAN_BURROWER_DEFEATED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY, "search_nest")
    return True


def complete_first_outside_step(session) -> bool:
    if session.character is None or _step(session, HUMAN_BEYOND_WALL_QUEST_KEY) != "cross_gate":
        return False
    session.database.grant_flag(session.character.id, HUMAN_FIRST_OUTSIDE_FLAG)
    session.database.grant_flag(session.character.id, HUMAN_OPENING_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, HUMAN_BEYOND_WALL_QUEST_KEY)
    cathedral = _quest(session, quests.HUMAN_CATHEDRAL_SUMMONS.key)
    if cathedral is None:
        session.database.start_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key, "read_note")
    elif cathedral.get("status") == "active" and cathedral.get("current_step") == "await_blackwall_handoff":
        session.database.advance_quest(session.character.id, quests.HUMAN_CATHEDRAL_SUMMONS.key, "read_note")
    if session.database.item_quantity(session.character.id, "sealed_cathedral_note") <= 0:
        session.database.add_item(session.character.id, "sealed_cathedral_note", 1)
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_human_blackwall_runtime(player_session_class, world_service) -> None:
    install_human_blackwall_content(world_service)
    if getattr(player_session_class, "_human_blackwall_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = player_session_class.move_character
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        migrated = prepare_human_blackwall_opening(self)
        await previous_enter_character(self)
        if self.character is None or self.character.race != "human":
            return
        readiness = _quest(self, HUMAN_READINESS_QUEST_KEY)
        if readiness and readiness.get("status") == "active":
            if migrated or readiness.get("current_step") == "report_muster":
                await self.send(
                    "\r\nA Blackwall district bell sounds one measured note: routine muster, not alarm. "
                    "Your first obligation is ordinary civic readiness, the kind of thing citizens here learn before anybody needs it.\r\n"
                    "\r\nNew quest: When the Wall Calls. Go NORTH to the Readiness Yard and TALK MARA.\r\n"
                )
            else:
                objective = HUMAN_READINESS_QUEST.objective_for_step(readiness.get("current_step"))
                if objective:
                    await self.send(f"\r\nBlackwall opening objective: {objective}\r\n")

    async def move_character(self, direction: str) -> None:
        if self.character is None or self.character.race != "human":
            await previous_move_character(self, direction)
            return
        origin = self.character.current_room
        normalized = direction.lower()
        if origin == HUMAN_SOOTSTEP_TUNNEL_KEY and normalized == "east" and HUMAN_NEST_SEARCHED_FLAG not in _flags(self):
            await self.send("The patched shutter is still part of the investigation. Deal with the tunnel threat and SEARCH NEST before forcing it open.\r\n")
            return
        if origin == legacy_world.HUMAN_START_ROOM_KEY and normalized == "east":
            beyond = _quest(self, HUMAN_BEYOND_WALL_QUEST_KEY)
            if beyond and beyond.get("status") == "active" and beyond.get("current_step") != "cross_gate":
                await self.send("The outbound caravan chain is still raised. TALK GATEWARDEN before leaving through this lane.\r\n")
                return
            if beyond and beyond.get("status") == "active" and HUMAN_GATE_CLEARANCE_FLAG not in _flags(self):
                await self.send("The outbound caravan chain is still raised. TALK GATEWARDEN before leaving through this lane.\r\n")
                return
        await previous_move_character(self, direction)
        if self.character is None:
            return
        if origin == legacy_world.HUMAN_START_ROOM_KEY and normalized == "east" and self.character.current_room == HUMAN_OUTER_CARAVAN_ROAD_KEY:
            if complete_first_outside_step(self):
                await self.send(
                    "\r\nThe gate opens behind you with chain, wheel, and ordinary shouted traffic instructions—not ceremony. Then you are outside.\r\n"
                    "A Dwarven teamster coming the other way glances up and calls, 'Morning, Demon,' as casually as Ketta did. Farther down the road, another traveler looks at the horned Blackwall skyline, then at you, and keeps a little more distance than the road requires.\r\n"
                    "Inside, the word was architecture. Out here, it belongs to other people's stories about you. Neither reaction tells you everything about the person having it.\r\n"
                    "You turn once and see Blackwall from the road: enormous, black, horned, and suddenly understandable as something a stranger might fear.\r\n"
                    "\r\nQuest complete: Beyond the Blackwall. The wider road is open.\r\n"
                    "The sealed cathedral summons in your belongings is now yours to answer when you return inside. READ NOTE when you want to follow that city thread.\r\n"
                )

    def _enemy_in_current_room(self, target_text: str):
        if (
            self.character is not None
            and self.character.race == "human"
            and self.character.current_room == HUMAN_SOOTSTEP_TUNNEL_KEY
            and _step(self, HUMAN_CARAVAN_QUEST_KEY) == "fight_burrower"
            and _burrower_target(target_text)
        ):
            return EnemyState(SOOTSTEP_BURROWER)
        return previous_enemy_lookup(self, target_text)

    async def _finish_enemy_defeat(self, enemy) -> None:
        is_burrower = (
            self.character is not None
            and self.character.race == "human"
            and enemy.definition.key == HUMAN_BURROWER_KEY
            and _step(self, HUMAN_CARAVAN_QUEST_KEY) == "fight_burrower"
        )
        await previous_finish_enemy(self, enemy)
        if not is_burrower or self.character is None:
            return
        if record_burrower_defeat(self):
            await self.send(
                "\r\nThe Sootstep Burrower collapses among the pitch scraps. With the immediate threat gone, the tunnel becomes evidence again.\r\n"
                "SEARCH NEST before deciding the animal explains everything you saw.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "human":
            await previous_playing_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"blackwall", "opening", "human opening", "readiness"}:
            await self.send("\r\n--- Blackwall Opening ---\r\n")
            for quest_def in HUMAN_OPENING_QUESTS:
                row = _quest(self, quest_def.key)
                if row is None:
                    continue
                await self.send(f"{quest_def.name}: {str(row.get('status')).upper()}\r\n")
                if row.get("status") == "active":
                    objective = quest_def.objective_for_step(row.get("current_step"))
                    if objective:
                        await self.send(f"  Objective: {objective}\r\n")
            return

        if await handle_human_opening_command(self, command):
            return

        if normalized.startswith("attack ") or normalized.startswith("kill "):
            target = command.strip().split(maxsplit=1)[1]
            if _burrower_target(target) and _step(self, HUMAN_CARAVAN_QUEST_KEY) != "fight_burrower":
                await self.send("There is no tunnel burrower here to fight at this stage of the investigation.\r\n")
                return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is None:
            return
        if normalized in {"look", "l"} and self.character.current_room == HUMAN_SOOTSTEP_TUNNEL_KEY and _step(self, HUMAN_CARAVAN_QUEST_KEY) == "fight_burrower":
            await self.send("A Sootstep Burrower is crouched over the pitch-scrap nest. ATTACK BURROWER.\r\n")
        if normalized in {"help", "?"}:
            await self.send(
                "Blackwall opening commands include TALK MARA/KETTA/ORRIN/GATEWARDEN, EXAMINE SIGNAL BOARD, DRILL SIGNALS, REPORT READY, EXAMINE WAGON, READ DAMAGE, FOLLOW SIGN, ATTACK BURROWER, SEARCH NEST, and SEARCH CACHE. Type BLACKWALL for your current opening objective.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class._enemy_in_current_room = _enemy_in_current_room
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class.playing_prompt = playing_prompt
    player_session_class._human_blackwall_runtime_installed = True
