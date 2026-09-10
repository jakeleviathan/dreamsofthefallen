from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RoomDefinition:
    key: str
    name: str
    description: str
    region_key: str
    exits: dict[str, str] = field(default_factory=dict)
    npc_keys: tuple[str, ...] = ()
    enemy_keys: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NpcDefinition:
    key: str
    name: str
    short_description: str
    room_key: str
    role: str
    dialogue: tuple[str, ...] = ()


# The Human start is the first authored room-by-room area in Astralis.
# Proper names beyond the established High Acolyte title are deliberately
# conservative so the city, cathedral, clerical order, and occult society can
# still receive final names later without changing room keys or progression.
HUMAN_START_ROOM_KEY = "human_demon_gate"
HUMAN_TRAINING_YARD_KEY = "human_training_yard"
HUMAN_PRACTICE_RING_KEY = "human_practice_ring"
HUMAN_VERMIN_PENS_KEY = "human_vermin_pens"
HUMAN_SOOTSTAIRS_KEY = "human_sootstairs"
HUMAN_CINDER_LANE_KEY = "human_cinder_lane"
HUMAN_BLACKGLASS_ARCH_KEY = "human_blackglass_arch"
HUMAN_LANTERN_COURT_KEY = "human_lantern_court"

HUMAN_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key="human_demon_gate",
        name="The Demon Gate",
        region_key="human_kingdom",
        description=(
            "Massive wrought-iron gates stand open beneath a black stone arch carved with horns, wings, and stern demonic faces. "
            "Torchlight crawls across wet cobblestones while guards in dark uniforms watch the road with practiced suspicion. "
            "Beyond the walls, narrow streets climb toward a forest of sharp spires. Far above them all, the great cathedral cuts a "
            "jagged silhouette into the sky. A slow bell sounds somewhere within the city. South of the gate, a hard-packed drill road "
            "runs along the outer wall toward the city's training grounds."
        ),
        exits={"north": "human_ashen_way", "south": "human_outer_drill_road"},
        tags=("human_start", "gothic", "city_gate"),
    ),
    RoomDefinition(
        key="human_ashen_way",
        name="Ashen Way",
        region_key="human_kingdom",
        description=(
            "Tall dark-stone buildings crowd close around a steep cobbled avenue. Iron balconies, horned drainspouts, and red-black "
            "banners turn the old insult 'Demon' into civic decoration. Tavern doors stand open beside guild offices and crowded shops. "
            "Citizens move quickly through the smoky torchlight, while the cathedral bells make the window glass tremble."
        ),
        exits={"south": "human_demon_gate", "north": "human_cathedral_square", "west": HUMAN_SOOTSTAIRS_KEY},
        tags=("gothic", "market_street", "guilds"),
    ),
    RoomDefinition(
        key="human_cathedral_square",
        name="Cathedral Square",
        region_key="human_kingdom",
        description=(
            "The avenue opens into a broad stone square dominated by a vast gothic cathedral. Gargoyles crouch along flying buttresses, "
            "and stained glass throws bruised reds and violets across the pavement. Members of the city's clerical order cross between "
            "the cathedral and nearby chapter houses. In shadowed corners, unfamiliar symbols have been scratched into old masonry and "
            "then carefully scraped away, suggesting that another, less public tradition moves through the city."
        ),
        exits={"south": "human_ashen_way", "north": "human_grand_cathedral"},
        tags=("gothic", "cathedral", "clerical_order", "occult_hint"),
    ),
    RoomDefinition(
        key="human_grand_cathedral",
        name="The Grand Cathedral",
        region_key="human_kingdom",
        description=(
            "The cathedral nave rises into darkness above rows of black wooden pews. Hundreds of candles burn before severe stone saints, "
            "their light reflected in crimson glass and polished iron. Clerics speak in low voices beneath the distant groan of the organ. "
            "Near the crossing stands the High Acolyte, composed and watchful, as though your arrival was expected long before you reached the door."
        ),
        exits={"south": "human_cathedral_square"},
        npc_keys=("human_high_acolyte",),
        tags=("gothic", "cathedral", "clerical_order", "mentor"),
    ),
    RoomDefinition(
        key="human_outer_drill_road",
        name="Outer Drill Road",
        region_key="human_kingdom",
        description=(
            "Outside the Demon Gate, a packed-earth road follows the black city wall beneath iron watchtowers. Boot prints and wagon ruts "
            "score the ground. To the west, the ring of weapon blows and barked instructions carry from a walled training yard. The cathedral "
            "spires remain visible over the battlements, dark against the sky."
        ),
        exits={"north": "human_demon_gate", "west": HUMAN_TRAINING_YARD_KEY},
        tags=("outside_city", "training_route"),
    ),
    RoomDefinition(
        key=HUMAN_TRAINING_YARD_KEY,
        name="The Training Yard",
        region_key="human_kingdom",
        description=(
            "A broad yard of churned earth lies beneath the city's outer wall. Weapon racks, scarred shields, straw bundles, and buckets of sand "
            "line the fence. New fighters drill under the eyes of veteran guards. A practice ring stands to the north, while a low stone passage "
            "to the south leads toward barred vermin pens used for controlled live-combat exercises."
        ),
        exits={"east": "human_outer_drill_road", "north": HUMAN_PRACTICE_RING_KEY, "south": HUMAN_VERMIN_PENS_KEY},
        tags=("training", "safe_combat", "tutorial"),
    ),
    RoomDefinition(
        key=HUMAN_PRACTICE_RING_KEY,
        name="The Practice Ring",
        region_key="human_kingdom",
        description=(
            "A circular patch of packed dirt is surrounded by a waist-high iron rail. Several battered wooden training dummies stand on heavy bases, "
            "their surfaces chopped and scorched by generations of beginners. This is where new citizens learn to start and stop a fight without risking a throat."
        ),
        exits={"south": HUMAN_TRAINING_YARD_KEY},
        enemy_keys=("training_dummy",),
        tags=("training", "safe_combat", "practice_dummy"),
    ),
    RoomDefinition(
        key=HUMAN_VERMIN_PENS_KEY,
        name="The Vermin Pens",
        region_key="human_kingdom",
        description=(
            "Iron-barred pens open onto a shallow fighting floor stained with old mud and newer scorch marks. City catchers keep oversized sewer rats here, "
            "along with small imps trapped inside the walls and judged more troublesome than dangerous. The creatures are real, but the enclosure is built so a "
            "new fighter can learn the difference between striking a dummy and surviving something that strikes back."
        ),
        exits={"north": HUMAN_TRAINING_YARD_KEY},
        enemy_keys=("sewer_rat", "small_imp"),
        tags=("training", "live_combat", "tutorial"),
    ),
    RoomDefinition(
        key=HUMAN_SOOTSTAIRS_KEY,
        name="The Sootstairs",
        region_key="human_kingdom",
        description=(
            "A narrow stair drops sharply away from Ashen Way between soot-black tenements. The cathedral spires vanish behind leaning roofs, "
            "and the polished demonic ornament of the upper city gives way to chipped horned lintels, patched shutters, laundry lines, and old iron lamps. "
            "Coal smoke and wet stone hang in the air. Far below, voices echo through the Lower Wards without carrying clearly enough to understand."
        ),
        exits={"east": "human_ashen_way", "down": HUMAN_CINDER_LANE_KEY},
        tags=("lower_wards", "gothic", "investigation", "urban_descent"),
    ),
    RoomDefinition(
        key=HUMAN_CINDER_LANE_KEY,
        name="Cinder Lane",
        region_key="human_kingdom",
        description=(
            "Cinder Lane twists between old brick workshops and cramped residences built against foundations older than the streets above. "
            "Rainwater runs black along the gutter. Doorways are crowded, windows are guarded, and conversations lower in volume when strangers pass. "
            "To the east, a sealed passage ends beneath an old blackglass arch. A small lantern court opens to the south."
        ),
        exits={"up": HUMAN_SOOTSTAIRS_KEY, "east": HUMAN_BLACKGLASS_ARCH_KEY, "south": HUMAN_LANTERN_COURT_KEY},
        tags=("lower_wards", "gothic", "investigation", "dense_city"),
    ),
    RoomDefinition(
        key=HUMAN_BLACKGLASS_ARCH_KEY,
        name="The Blackglass Arch",
        region_key="human_kingdom",
        description=(
            "An arch of smoke-dark glass and ancient masonry spans a passage that was bricked shut generations ago. Most of its old carvings have been weathered smooth. "
            "Near knee height, however, fresh scratches cut through the soot: three hooked strokes curling inward around a hollow circle. Someone tried to scrape the mark away, "
            "but not carefully enough. The pattern resembles the half-erased symbols hidden around Cathedral Square."
        ),
        exits={"west": HUMAN_CINDER_LANE_KEY},
        tags=("lower_wards", "occult_hint", "investigation", "strange_mark"),
    ),
    RoomDefinition(
        key=HUMAN_LANTERN_COURT_KEY,
        name="Lantern Court",
        region_key="human_kingdom",
        description=(
            "A cramped courtyard sits beneath a web of balconies and fire escapes. A single red lantern burns even in daylight above a public cistern gone dry. "
            "Residents drift through without lingering. Near the dead fountain waits a grey-cloaked local whose carefully neutral posture suggests a profession built on knowing things "
            "other people would rather keep quiet."
        ),
        exits={"north": HUMAN_CINDER_LANE_KEY},
        npc_keys=("human_lower_wards_informant",),
        tags=("lower_wards", "investigation", "informant", "old_cistern"),
    ),
)


# Forest Elf characters begin inside an isolated, comfortable woodland town and
# are encouraged to learn the surrounding forest by observation rather than
# immediate combat. Their nature magic is deliberately subtle rather than
# spectacular.
FOREST_ELF_START_ROOM_KEY = "forest_elf_circle_clearing"
FOREST_ELF_OLD_RIVER_PATH_KEY = "forest_elf_old_river_path"
FOREST_ELF_WAYSTONE_BEND_KEY = "forest_elf_waystone_bend"
FOREST_ELF_LISTENING_POOL_KEY = "forest_elf_listening_pool"
FOREST_ELF_OUTER_GROVE_KEY = "forest_elf_outer_grove"
FOREST_ELF_BRIARSHADOW_THICKET_KEY = "forest_elf_briarshadow_thicket"

FOREST_ELF_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=FOREST_ELF_START_ROOM_KEY,
        name="Circle Clearing",
        region_key="great_elf_forest",
        description=(
            "Morning light falls through a high green canopy onto an immaculate clearing at the heart of an isolated Elven town. "
            "Low timber homes curve around living trunks without swallowing them, and narrow wooden walks disappear between ferns and gardens. "
            "At the center, seven weathered stones mark the meeting place of the local Druidic Circle. Nothing here feels wild or dangerous; "
            "the forest has the quiet familiarity of a well-kept home. A soft path leaves the clearing to the north."
        ),
        exits={"north": "forest_elf_greenway"},
        tags=("forest_elf_start", "peaceful", "druidic_circle", "forest_town"),
    ),
    RoomDefinition(
        key="forest_elf_greenway",
        name="The Greenway",
        region_key="great_elf_forest",
        description=(
            "A broad footpath winds beneath old beeches and silver-barked birches. Ferns brush the edges of the trail, and small carved markers "
            "show which side paths lead back toward homes, gardens, and gathering halls. The town remains close enough that distant voices can still "
            "be heard behind you. To the east, the sound of running water marks the old river path."
        ),
        exits={"south": FOREST_ELF_START_ROOM_KEY, "east": FOREST_ELF_OLD_RIVER_PATH_KEY},
        tags=("peaceful", "forest_town_edge", "exploration"),
    ),
    RoomDefinition(
        key=FOREST_ELF_OLD_RIVER_PATH_KEY,
        name="The Old River Path",
        region_key="great_elf_forest",
        description=(
            "The path narrows beside a clear, shallow river sliding over flat brown stones. Moss-covered roots make natural steps along the bank, "
            "and tiny white flowers grow in patches where sunlight reaches the ground. An old trail continues north beside the water. Farther ahead, "
            "a weathered stone marker leans beneath a cedar."
        ),
        exits={"west": "forest_elf_greenway", "north": FOREST_ELF_WAYSTONE_BEND_KEY},
        tags=("river", "peaceful", "exploration", "old_path"),
    ),
    RoomDefinition(
        key=FOREST_ELF_WAYSTONE_BEND_KEY,
        name="Waystone Bend",
        region_key="great_elf_forest",
        description=(
            "The river bends around a shelf of dark stone. Beneath an ancient cedar stands a waist-high waystone softened by moss and age. "
            "A simple leaf-and-circle emblem has been cut into its face, with shallow marks beneath it that are easy to miss unless studied closely. "
            "The river path continues east through curtains of willow."
        ),
        exits={"south": FOREST_ELF_OLD_RIVER_PATH_KEY, "east": FOREST_ELF_LISTENING_POOL_KEY},
        tags=("river", "waystone", "exploration", "subtle_magic"),
    ),
    RoomDefinition(
        key=FOREST_ELF_LISTENING_POOL_KEY,
        name="The Listening Pool",
        region_key="great_elf_forest",
        description=(
            "The river widens into a glassy pool beneath drooping willow branches. Water passes over a low shelf of stone with barely a splash. "
            "Dragonflies hover above the surface, and the forest seems unusually still here—not silent, simply attentive. A narrow trail continues north "
            "toward older, less-tended woodland."
        ),
        exits={"west": FOREST_ELF_WAYSTONE_BEND_KEY, "north": FOREST_ELF_OUTER_GROVE_KEY},
        tags=("river", "listening", "subtle_magic", "exploration"),
    ),
    RoomDefinition(
        key=FOREST_ELF_OUTER_GROVE_KEY,
        name="The Outer Grove",
        region_key="great_elf_forest",
        description=(
            "The tended paths of the Elven town finally give way to older forest. Tall trunks crowd closer together, brambles gather beneath them, "
            "and the ground is marked by tracks that do not belong to townsfolk. A boundary oak bears three old claw marks above a newer strip of red cloth, "
            "a quiet warning from the Circle that the comfortable forest does not continue forever. The Listening Pool lies south. Beyond the boundary oak, "
            "a narrow trail pushes north beneath a darker wall of thorn and shadow."
        ),
        exits={"south": FOREST_ELF_LISTENING_POOL_KEY, "north": FOREST_ELF_BRIARSHADOW_THICKET_KEY},
        tags=("forest_edge", "danger_hint", "exploration", "boundary"),
    ),
    RoomDefinition(
        key=FOREST_ELF_BRIARSHADOW_THICKET_KEY,
        name="Briarshadow Thicket",
        region_key="great_elf_forest",
        description=(
            "The forest changes almost immediately beyond the boundary oak. Interlocking branches choke out much of the daylight, and thorny briars crowd "
            "the trail until every step must be chosen carefully. The neat leaf-markers used nearer the Elven town are gone. One strip of red warning cloth "
            "hangs torn from a blackthorn branch, its lower half missing. Damp earth is pressed flat in several places by broad, fresh tracks, and something "
            "has snapped young saplings well above the height of a deer. The air carries the smell of wet bark, crushed fern, and a faint animal musk. "
            "The safer Outer Grove lies south; deeper woodland closes in on every other side."
        ),
        exits={"south": FOREST_ELF_OUTER_GROVE_KEY},
        tags=("dangerous", "deep_forest", "thicket", "tracks", "future_encounter"),
    ),
)


# The Sporekin start is a quiet exploratory introduction to their mostly hidden
# underground civilization, then crosses the root veil to a small surface quest
# built around shared-consciousness guidance and an object-interaction puzzle.
SPOREKIN_START_ROOM_KEY = "sporekin_lumen_hollow"
SPOREKIN_SURFACEWARD_ROOM_KEY = "sporekin_veiled_grotto"
SPOREKIN_SURFACE_VERGE_ROOM_KEY = "sporekin_rainroot_verge"
SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY = "sporekin_forgotten_grove"
SPOREKIN_MEMORY_PATH_ROOM_KEY = "sporekin_memory_path"

SPOREKIN_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=SPOREKIN_START_ROOM_KEY,
        name="Lumen Hollow",
        region_key="sporekin_underways",
        description=(
            "Soft blue-green light spills from shelves of broad fungi along the cavern walls, bright enough to reveal "
            "dark soil, pale roots, and slow beads of water gathering on stone. The air is cool and rich with the smell "
            "of wet earth. No torch burns here; the cavern seems to breathe by its own quiet light. A narrow passage winds "
            "north between curtains of mycelium."
        ),
        exits={"north": "sporekin_mycelial_gallery"},
        tags=("sporekin_start", "bioluminescent", "underground", "quiet"),
    ),
    RoomDefinition(
        key="sporekin_mycelial_gallery",
        name="The Mycelial Gallery",
        region_key="sporekin_underways",
        description=(
            "Threads of living mycelium web the floor and climb the stone in branching white patterns. Bioluminescent "
            "caps glow between them like low stars. The place is nearly silent, yet standing here brings the peculiar "
            "sense of being among many others just beyond sight, as if distant thoughts travel through the living network "
            "beneath your feet. The Lumen Hollow lies south. A root-choked tunnel rises east."
        ),
        exits={"south": SPOREKIN_START_ROOM_KEY, "east": "sporekin_rootwell_ascent"},
        tags=("bioluminescent", "mycelium", "shared_consciousness", "underground"),
    ),
    RoomDefinition(
        key="sporekin_rootwell_ascent",
        name="Rootwell Ascent",
        region_key="sporekin_underways",
        description=(
            "Massive roots pierce the ceiling and walls of a steep natural shaft, forming handholds and narrow ledges "
            "among clusters of amber mushrooms. The earthy warmth of the deeper caverns gives way here to cooler moving "
            "air. Somewhere far above, water drips with the irregular rhythm of rainfall. The gallery is west, while a "
            "winding path continues upward toward a faint wash of natural light."
        ),
        exits={"west": "sporekin_mycelial_gallery", "up": SPOREKIN_SURFACEWARD_ROOM_KEY},
        tags=("underground", "roots", "surfaceward", "vertical"),
    ),
    RoomDefinition(
        key=SPOREKIN_SURFACEWARD_ROOM_KEY,
        name="The Veiled Grotto",
        region_key="sporekin_underways",
        description=(
            "The ascent ends in a broad grotto hidden beneath a woven ceiling of roots, moss, and stone. Daylight filters "
            "through hairline openings overhead, strange and pale after the fungal glow below. Small luminous mushrooms "
            "still cluster around the edges, but here the scent of soil mixes with rain and growing leaves. A passage leads "
            "down into the unseen Sporekin world. To the north, the root veil finally opens onto the breathing surface."
        ),
        exits={"down": "sporekin_rootwell_ascent", "north": SPOREKIN_SURFACE_VERGE_ROOM_KEY},
        tags=("underground", "surface_edge", "hidden", "bioluminescent"),
    ),
    RoomDefinition(
        key=SPOREKIN_SURFACE_VERGE_ROOM_KEY,
        name="Rainroot Verge",
        region_key="sporekin_underways",
        description=(
            "For the first time the cavern roof is gone. Rain beads on broad leaves and dark roots while mist hangs low among "
            "the trees. Behind you, the entrance to the Underways is almost invisible beneath moss and stone. The ordinary forest "
            "seems loud after the quiet below: insects, dripping branches, distant birds. Eastward, beneath an ancient bent tree, "
            "a faint blue-green pulse appears and vanishes between the trunks."
        ),
        exits={"south": SPOREKIN_SURFACEWARD_ROOM_KEY, "east": SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY},
        tags=("surface", "rain", "hidden_entrance", "sporekin_quest"),
    ),
    RoomDefinition(
        key=SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
        name="The Forgotten Grove",
        region_key="sporekin_underways",
        description=(
            "An old ring of four bioluminescent mushrooms surrounds a flat black stone half-swallowed by moss. One cap glows "
            "deep blue, one amber, one violet, and one pale ivory. Their light does not pulse together; each seems to be waiting "
            "for the others. Thin mycelial scars radiate from the stone into the soil, too deliberate to be natural. The rainy verge "
            "lies west. Whatever once continued beyond this grove has been hidden by roots and years."
        ),
        exits={"west": SPOREKIN_SURFACE_VERGE_ROOM_KEY},
        tags=("surface", "forgotten", "puzzle", "bioluminescent", "shared_consciousness"),
    ),
    RoomDefinition(
        key=SPOREKIN_MEMORY_PATH_ROOM_KEY,
        name="The Memory Path",
        region_key="sporekin_underways",
        description=(
            "A narrow path winds north beneath old roots, revealed only after the grove remembered its pulse. Flecks of fungal "
            "light cling to stones along the trail like a fading constellation. The hovering spore sigil has vanished, but its direction "
            "is unmistakable. South lies the forgotten mushroom ring; ahead waits a part of the Sporekin past not yet explored."
        ),
        exits={"south": SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY},
        tags=("surface", "revealed_path", "sporekin_quest"),
    ),
)

ROOMS: tuple[RoomDefinition, ...] = HUMAN_ROOMS + FOREST_ELF_ROOMS + SPOREKIN_ROOMS
ROOMS_BY_KEY = {room.key: room for room in ROOMS}

HIGH_ACOLYTE = NpcDefinition(
    key="human_high_acolyte",
    name="High Acolyte",
    short_description="a senior cleric whose calm attention is difficult to read",
    room_key="human_grand_cathedral",
    role="enigmatic mentor and early quest guide",
    dialogue=(
        "The High Acolyte studies the seal on your note, then looks back to you. 'Good. You found your way here without an escort.'",
        "'This city rewards those who learn its streets, its people, and the difference between what is displayed openly and what is deliberately hidden.'",
        "The Acolyte turns the note over and writes a short instruction across its reverse. 'Now learn what happens when something hits back. The training grounds are outside the Demon Gate.'",
        "Their expression gives away very little. 'Begin with the practice ring. Then enter the vermin pens. Return alive, and the city will have taught you its first useful lesson.'",
    ),
)

LOWER_WARDS_INFORMANT = NpcDefinition(
    key="human_lower_wards_informant",
    name="Grey-Cloaked Informant",
    short_description="a watchful local lingering beside the dry cistern",
    room_key=HUMAN_LANTERN_COURT_KEY,
    role="Lower Wards informant and occult-investigation contact",
    dialogue=(
        "The informant looks at you only after you describe the scratched symbol. 'Three hooks around an empty center. Yes. I've seen it.'",
        "'It isn't a gang mark, and it isn't a prayer. People use it when they want someone else to know a way below has been left open.'",
        "Their eyes flick toward the dry cistern. 'The old water tunnels under this ward were sealed on the city plans. The city plans are lying.'",
        "'If your Acolyte wants to know why the Lower Wards have started whispering, tell them to start with the cistern tunnels.'",
    ),
)

NPCS: tuple[NpcDefinition, ...] = (HIGH_ACOLYTE, LOWER_WARDS_INFORMANT)
NPCS_BY_KEY = {npc.key: npc for npc in NPCS}


def room_for_key(room_key: str | None) -> RoomDefinition | None:
    if not room_key:
        return None
    return ROOMS_BY_KEY.get(room_key)
