from __future__ import annotations

from dataclasses import dataclass, replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.frontier_convergence import (
    ASHCROSS_CULVERT_KEY,
    ASHCROSS_GATE_KEY,
    ASHCROSS_HUSHWOOD_KEY,
    ASHCROSS_MILESTONE_KEY,
    ASHCROSS_SUNKEN_WATCH_KEY,
    INTRO_QUEST_KEY,
    OUTER_COMPLETE_FLAG,
    OUTER_DEEP_GATE_KEY,
)
from mud.midgame_three_roads import (
    DWARF_COMPLETE_FLAG,
    MERIDIAN_ALIGNED_FLAG,
    MERIDIAN_CAMP_KEY,
    MERIDIAN_QUEST_KEY,
    MERIDIAN_WITNESS_KEY,
    MOON_COMPLETE_FLAG,
    TROLL_COMPLETE_FLAG,
)
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition
from mud.veyra_city import (
    VEYRA_GREENHALL_KEY,
    VEYRA_LOWER_QUAYS_KEY,
    VEYRA_OLD_BRIDGE_KEY,
    VEYRA_PUBLIC_HEARTH_KEY,
    VEYRA_SOUTH_SPRAWL_KEY,
)
from mud.world import NpcDefinition, RoomDefinition


WITNESSES_REQUIRED = 3

HUMAN_REGION_KEY = "blackglass_march"
FOREST_REGION_KEY = "alderwake_road"
GOBLIN_REGION_KEY = "rattlechain_run"
UNDEAD_REGION_KEY = "pale_pilgrim_road"
SPOREKIN_REGION_KEY = "rainroot_threadway"

HUMAN_COMPLETE_FLAG = "midgame_human_witness_complete"
FOREST_COMPLETE_FLAG = "midgame_forest_witness_complete"
GOBLIN_COMPLETE_FLAG = "midgame_goblin_witness_complete"
UNDEAD_COMPLETE_FLAG = "midgame_undead_witness_complete"
SPOREKIN_COMPLETE_FLAG = "midgame_sporekin_witness_complete"

HUMAN_ARCHIVE_FLAG = "midgame_human_choice_archive"
HUMAN_SHARE_FLAG = "midgame_human_choice_share"
FOREST_REST_FLAG = "midgame_forest_choice_rest"
FOREST_WARD_FLAG = "midgame_forest_choice_ward"
GOBLIN_SPLIT_FLAG = "midgame_goblin_choice_split"
GOBLIN_AUCTION_FLAG = "midgame_goblin_choice_auction"
UNDEAD_SEAL_FLAG = "midgame_undead_choice_seal"
UNDEAD_PUBLISH_FLAG = "midgame_undead_choice_publish"
SPOREKIN_OPEN_FLAG = "midgame_sporekin_choice_open"
SPOREKIN_VEIL_FLAG = "midgame_sporekin_choice_veil"

HUMAN_BOSS_FLAG = "midgame_human_hollowhorn_defeated"
FOREST_BOSS_FLAG = "midgame_forest_ringboar_defeated"
GOBLIN_BOSS_FLAG = "midgame_goblin_claimbreaker_defeated"
UNDEAD_BOSS_FLAG = "midgame_undead_mnemonic_husk_defeated"
SPOREKIN_BOSS_FLAG = "midgame_sporekin_root_borer_defeated"

HUMAN_WITNESS_ITEM_KEY = "blackglass_bearing_lens"
FOREST_WITNESS_ITEM_KEY = "alderwake_yearring_slice"
GOBLIN_WITNESS_ITEM_KEY = "rattlechain_fit_plate"
UNDEAD_WITNESS_ITEM_KEY = "pale_road_memory_slate"
SPOREKIN_WITNESS_ITEM_KEY = "rainroot_silence_knot"

HUMAN_QUEST_KEY = "blackglass_bearing"
FOREST_QUEST_KEY = "alderwake_absence"
GOBLIN_QUEST_KEY = "rattlechain_fit"
UNDEAD_QUEST_KEY = "pale_road_memory"
SPOREKIN_QUEST_KEY = "rainroot_silence"

HUMAN_ENTRY_KEY = "blackglass_south_ferry"
HUMAN_MENTOR_KEY = "blackglass_relay_court"
HUMAN_BOSS_ROOM_KEY = "blackglass_hollowhorn_den"
HUMAN_CLUE_KEY = "blackglass_bearing_chamber"
HUMAN_ENDPOINT_KEY = "blackglass_ashcross_approach"

FOREST_ENTRY_KEY = "alderwake_green_lane"
FOREST_MENTOR_KEY = "alderwake_circle_camp"
FOREST_BOSS_ROOM_KEY = "alderwake_scarboar_hollow"
FOREST_CLUE_KEY = "alderwake_yearring_stump"
FOREST_ENDPOINT_KEY = "alderwake_hushwood_edge"

GOBLIN_ENTRY_KEY = "rattlechain_dock_cut"
GOBLIN_MENTOR_KEY = "rattlechain_claimhouse"
GOBLIN_BOSS_ROOM_KEY = "rattlechain_claimbreaker_pit"
GOBLIN_CLUE_KEY = "rattlechain_impossible_fit"
GOBLIN_ENDPOINT_KEY = "rattlechain_culvert_mouth"

UNDEAD_ENTRY_KEY = "pale_road_arch"
UNDEAD_MENTOR_KEY = "pale_road_record_house"
UNDEAD_BOSS_ROOM_KEY = "pale_road_mnemonic_hollow"
UNDEAD_CLUE_KEY = "pale_road_false_memory_crypt"
UNDEAD_ENDPOINT_KEY = "pale_road_sunken_approach"

SPOREKIN_ENTRY_KEY = "rainroot_hearth_cellar"
SPOREKIN_MENTOR_KEY = "rainroot_guide_nexus"
SPOREKIN_BOSS_ROOM_KEY = "rainroot_borer_nest"
SPOREKIN_CLUE_KEY = "rainroot_silent_seam"
SPOREKIN_ENDPOINT_KEY = "rainroot_hushwood_below"

HUMAN_NPC_KEY = "blackglass_archivist_marra"
FOREST_NPC_KEY = "alderwake_keeper_leth"
GOBLIN_NPC_KEY = "rattlechain_fixer_skrit"
UNDEAD_NPC_KEY = "pale_road_recorder_ossan"
SPOREKIN_NPC_KEY = "rainroot_guide_somn"

HUMAN_BOSS_KEY = "blackglass_hollowhorn_stalker"
FOREST_BOSS_KEY = "alderwake_ring_scar_boar"
GOBLIN_BOSS_KEY = "rattlechain_old_claimbreaker"
UNDEAD_BOSS_KEY = "pale_road_mnemonic_husk"
SPOREKIN_BOSS_KEY = "rainroot_borer_matriarch"


@dataclass(frozen=True, slots=True)
class WitnessRoute:
    key: str
    race_key: str
    label: str
    region_key: str
    quest: QuestDefinition
    room_keys: tuple[str, ...]
    mentor_room_key: str
    boss_room_key: str
    clue_room_key: str
    completion_flag: str
    boss_flag: str
    witness_item_key: str
    choice_a_flag: str
    choice_b_flag: str
    talk_commands: tuple[str, ...]
    study_commands: tuple[str, ...]
    choice_a_commands: tuple[str, ...]
    choice_b_commands: tuple[str, ...]
    mentor_text: str
    study_text: str
    choice_a_text: str
    choice_b_text: str
    xp_reward: int


def _quest(key: str, name: str, description: str, mentor: str, boss: str, study: str, choices: str) -> QuestDefinition:
    return QuestDefinition(
        key=key,
        name=name,
        style="structured",
        minimum_level=12,
        description=description,
        objective_steps=(
            ("talk_mentor", mentor),
            ("reach_boss", boss),
            ("defeat_boss", "Defeat the threat blocking the regional witness site."),
            ("study_witness", study),
            ("choose_response", choices),
            ("complete", "Carry this road's independent witness toward Ashcross."),
        ),
    )


HUMAN_QUEST = _quest(
    HUMAN_QUEST_KEY,
    "The Blackglass Bearing",
    "South of Veyra, Human archivists are documenting a blackglass relay road built by generations who remembered Earth more clearly than anyone alive does now. A recovered lens points somewhere no road goes.",
    "TALK MARRA at Blackglass Relay Court.",
    "Reach the Hollowhorn Den beyond the shattered mile marker.",
    "At the Bearing Chamber, INSPECT BEARING.",
    "Choose ARCHIVE RELIC or SHARE RELIC.",
)
FOREST_QUEST = _quest(
    FOREST_QUEST_KEY,
    "Rings Around an Absence",
    "A managed Forest Elf road has begun producing trees whose growth rings bend around the same perfectly straight absence. The local circle is arguing over how much frontier traffic the grove should absorb.",
    "TALK LETH at Alderwake Circle Camp.",
    "Reach Scarboar Hollow beyond the ringfield.",
    "At the Yearring Stump, READ RINGS.",
    "Choose REST GROVE or WARD CROSSING.",
)
GOBLIN_QUEST = _quest(
    GOBLIN_QUEST_KEY,
    "Everything Fits Somewhere",
    "Goblin salvage crews on the river road keep finding unrelated pieces that fit one impossible straight-edged gap as though the missing part was manufactured before any of them were.",
    "TALK SKRIT at the Rattlechain Claimhouse.",
    "Reach the Old Claimbreaker pit beyond the sorting yard.",
    "At the Impossible Fit Bench, FIT PLATES.",
    "Choose SPLIT CLAIM or OPEN AUCTION.",
)
UNDEAD_QUEST = _quest(
    UNDEAD_QUEST_KEY,
    "The Memory No One Lived",
    "Several Undead travelers have independently recorded the same remembered corridor despite dying in different centuries and places. The record house wants evidence before anyone calls it revelation.",
    "TALK OSSAN at the Pale Road Record House.",
    "Reach the Mnemonic Hollow beyond the name stones.",
    "At the False-Memory Crypt, COMPARE MEMORIES.",
    "Choose SEAL RECORD or PUBLISH RECORD.",
)
SPOREKIN_QUEST = _quest(
    SPOREKIN_QUEST_KEY,
    "The Silence Between Threads",
    "A Sporekin guide-route beneath Veyra reaches a place where healthy mycelium refuses to cross one perfectly straight seam. The shared consciousness goes quiet at exactly the same boundary.",
    "TALK SOMN at the Rainroot Guide Nexus.",
    "Reach the Root-Borer Nest beyond the spore bridge.",
    "At the Silent Seam, LISTEN SILENCE.",
    "Choose OPEN THREAD or VEIL THREAD.",
)

FIVE_ROAD_QUESTS = (
    HUMAN_QUEST,
    FOREST_QUEST,
    GOBLIN_QUEST,
    UNDEAD_QUEST,
    SPOREKIN_QUEST,
)


FIVE_ROAD_ITEMS = (
    ItemDefinition(
        HUMAN_WITNESS_ITEM_KEY,
        "Blackglass Bearing Lens",
        "A smoke-dark Human archive lens. When leveled against known road marks, its old scratches converge on a bearing below the frontier rather than across it.",
        "trophy",
        tier=4,
    ),
    ItemDefinition(
        FOREST_WITNESS_ITEM_KEY,
        "Yearring Witness Slice",
        "A carefully cut tree-ring sample showing decades of healthy growth bending around one ruler-straight absence.",
        "trophy",
        tier=4,
    ),
    ItemDefinition(
        GOBLIN_WITNESS_ITEM_KEY,
        "Impossible-Fit Salvage Plate",
        "Several unrelated scrap fragments clamped into a perfect frame around a missing straight-edged center that none of the crews actually found.",
        "trophy",
        tier=4,
    ),
    ItemDefinition(
        UNDEAD_WITNESS_ITEM_KEY,
        "Borrowed-Memory Slate",
        "A funerary slate comparing testimony from unrelated Undead who all remember the same impossible downward corridor that none of them lived.",
        "trophy",
        tier=4,
    ),
    ItemDefinition(
        SPOREKIN_WITNESS_ITEM_KEY,
        "Silent Mycelial Knot",
        "A living knot of pale mycelium that grows vigorously in every direction except across one perfectly straight dead boundary.",
        "trophy",
        tier=4,
    ),
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
    )


BLACKGLASS_ROADCROW = _enemy(
    "blackglass_roadcrow",
    "Ash Roadcrow",
    ("roadcrow", "ash roadcrow", "crow"),
    "a dog-sized black carrion bird that has learned to harry isolated travelers",
    245, 12, 17, 2.6, 185,
)
HOLLOWHORN_STALKER = _enemy(
    HUMAN_BOSS_KEY,
    "Hollowhorn Stalker",
    ("hollowhorn", "stalker", "hollowhorn stalker"),
    "a scarred antlered predator nesting among broken blackglass markers, one horn grown around a perfectly straight groove",
    720, 16, 25, 2.8, 1150,
)
ALDERWAKE_TUSKER = _enemy(
    "alderwake_tusker",
    "Bramble Tusker",
    ("tusker", "bramble tusker", "boar"),
    "a heavy forest boar carrying burrs, snapped survey ribbons, and no interest in giving the road back",
    270, 13, 18, 2.8, 205,
)
RING_SCAR_BOAR = _enemy(
    FOREST_BOSS_KEY,
    "Ring-Scar Boar",
    ("ring-scar", "ring scar boar", "boar"),
    "an enormous old boar whose flank carries pale concentric scars matching the distorted rings of nearby trees",
    760, 16, 25, 2.9, 1200,
)
RATTLECHAIN_SCAVENGER = _enemy(
    "rattlechain_mireclamp",
    "Mireclamp",
    ("mireclamp", "crab", "salvage crab"),
    "a broad swamp crustacean wearing discarded washers and wire like accidental armor",
    285, 14, 19, 2.8, 220,
)
OLD_CLAIMBREAKER = _enemy(
    GOBLIN_BOSS_KEY,
    "Old Claimbreaker",
    ("claimbreaker", "old claimbreaker", "rig"),
    "an abandoned pre-Goblin hauling machine that wakes whenever salvage chains tighten around its buried frame",
    810, 17, 26, 3.0, 1280,
)
PALE_ROAD_HOUND = _enemy(
    "pale_road_ossuary_hound",
    "Ossuary Hound",
    ("hound", "ossuary hound"),
    "a bone-pale scavenger trained generations ago to guard roadside name stones and now answering to nobody",
    300, 14, 20, 2.7, 235,
)
MNEMONIC_HUSK = _enemy(
    UNDEAD_BOSS_KEY,
    "Mnemonic Husk",
    ("husk", "mnemonic husk", "memory husk"),
    "a jointed gray shell that repeats fragments of nearby voices several heartbeats after they were spoken",
    835, 17, 27, 2.9, 1325,
)
RAINROOT_BORER = _enemy(
    "rainroot_pale_borer",
    "Pale Root-Borer",
    ("borer", "root-borer", "pale borer"),
    "a blind segmented burrower chewing through dead wood but carefully avoiding living mycelial threads",
    295, 13, 20, 2.8, 230,
)
ROOT_BORER_MATRIARCH = _enemy(
    SPOREKIN_BOSS_KEY,
    "Root-Borer Matriarch",
    ("matriarch", "root-borer matriarch", "borer matriarch"),
    "a massive pale burrower nesting beside the silent seam, its tunnels stopping in ruler-straight lines",
    800, 16, 26, 2.9, 1275,
)

FIVE_ROAD_ENEMIES = (
    BLACKGLASS_ROADCROW,
    HOLLOWHORN_STALKER,
    ALDERWAKE_TUSKER,
    RING_SCAR_BOAR,
    RATTLECHAIN_SCAVENGER,
    OLD_CLAIMBREAKER,
    PALE_ROAD_HOUND,
    MNEMONIC_HUSK,
    RAINROOT_BORER,
    ROOT_BORER_MATRIARCH,
)


HUMAN_NPC = NpcDefinition(
    HUMAN_NPC_KEY,
    "Archivist Marra Vale",
    "a Human road archivist in a soot-dark coat carrying more rubbing paper than weapons",
    HUMAN_MENTOR_KEY,
    "Human relay-road archivist",
    dialogue=(
        "'Earth is history, not a personality trait. If somebody tells you otherwise, ask them to name three things about it that were not in a museum ledger.'",
        "'The lens is real. The bearing is real. What either of those facts means is still our problem.'",
    ),
)
FOREST_NPC = NpcDefinition(
    FOREST_NPC_KEY,
    "Circle-Keeper Leth Rowan",
    "a Forest Elf steward with mud on both knees and survey twine around one wrist",
    FOREST_MENTOR_KEY,
    "Alderwake road and grove steward",
    dialogue=(
        "'A road through a forest is still part of the forest. That does not mean every road belongs everywhere.'",
        "'Read the rings before you decide whether this is damage, adaptation, or something we do not have a word for.'",
    ),
)
GOBLIN_NPC = NpcDefinition(
    GOBLIN_NPC_KEY,
    "Fixer Skrit Patchmark",
    "a Goblin salvage arbitrator wearing six claim tags and trusting none of them without a witness",
    GOBLIN_MENTOR_KEY,
    "Rattlechain salvage arbitrator",
    dialogue=(
        "'If two clans both dragged it out, both clans own an argument. That is what the claimhouse is for.'",
        "'The weird part is not that the scraps fit. Goblins make things fit. The weird part is who cut the hole first.'",
    ),
)
UNDEAD_NPC = NpcDefinition(
    UNDEAD_NPC_KEY,
    "Recorder Ossan",
    "an Undead funerary clerk carrying wax tablets labeled by witness rather than by doctrine",
    UNDEAD_MENTOR_KEY,
    "Pale Road memory recorder",
    dialogue=(
        "'The dead misremember. So do the living. Repetition becomes evidence only after you rule out repetition as contagion.'",
        "'Five witnesses died in different centuries. None walked this road alive. All remember the same corridor.'",
    ),
)
SPOREKIN_NPC = NpcDefinition(
    SPOREKIN_NPC_KEY,
    "Guide Somn-of-Rain",
    "a broad-capped Sporekin guide whose lantern is woven into a living belt of pale fungus",
    SPOREKIN_MENTOR_KEY,
    "Rainroot guide and shared-thread interpreter",
    dialogue=(
        "'Shared thought is not shared certainty. We still walk to the place and look.'",
        "'The network does not fear the seam. Fear is noisy. This is absence.'",
    ),
)
FIVE_ROAD_NPCS = (HUMAN_NPC, FOREST_NPC, GOBLIN_NPC, UNDEAD_NPC, SPOREKIN_NPC)


def _room(
    key: str,
    name: str,
    region: str,
    description: str,
    exits: dict[str, str],
    *,
    npcs: tuple[str, ...] = (),
    enemies: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=region,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "eight_roads", *tags),
    )


HUMAN_ROOMS = (
    _room(
        HUMAN_ENTRY_KEY, "South Ferry Road", HUMAN_REGION_KEY,
        "The timber sprawl gives way to a floodplain road where Human teamsters paint old horned civic marks beside ordinary ferry prices. Nothing here pretends the descendants of Earth are still from Earth.",
        {"north": VEYRA_SOUTH_SPRAWL_KEY, "south": "blackglass_cinder_road"},
        enemies=(BLACKGLASS_ROADCROW.key,), tags=("level_12_13", "human_road"),
    ),
    _room(
        "blackglass_cinder_road", "Cinder Road", HUMAN_REGION_KEY,
        "Black slag gravel crunches underfoot between drainage ditches and low farms. Broken panes of smoke-dark glass have been set into mile markers as reflective road signs.",
        {"north": HUMAN_ENTRY_KEY, "south": HUMAN_MENTOR_KEY},
        tags=("level_12_13", "human_road"),
    ),
    _room(
        HUMAN_MENTOR_KEY, "Blackglass Relay Court", HUMAN_REGION_KEY,
        "A walled relay yard serves archivists, ferrymen, and freight crews. Copies of old Human road rubbings hang beside current repair notices so history has to share wall space with maintenance.",
        {"north": "blackglass_cinder_road", "south": "blackglass_ashfield"},
        npcs=(HUMAN_NPC_KEY,), tags=("level_12_13", "safe", "human_history"),
    ),
    _room(
        "blackglass_ashfield", "Ashfield Verge", HUMAN_REGION_KEY,
        "Wind moves through dry grass around the foundations of a settlement abandoned before anyone alive was born. The road stays busy enough that the ruins never become sacred by accident.",
        {"north": HUMAN_MENTOR_KEY, "south": "blackglass_shattered_marker"},
        enemies=(BLACKGLASS_ROADCROW.key,), tags=("level_13_14", "ruins"),
    ),
    _room(
        "blackglass_shattered_marker", "Shattered Mile Marker", HUMAN_REGION_KEY,
        "A horned blackglass marker lies in three pieces. The surviving survey lines all agree on the road ahead except for one scratch that points straight down.",
        {"north": "blackglass_ashfield", "east": HUMAN_BOSS_ROOM_KEY},
        tags=("level_14", "anomaly_hint"),
    ),
    _room(
        HUMAN_BOSS_ROOM_KEY, "Hollowhorn Den", HUMAN_REGION_KEY,
        "A shallow quarry has become a predator den around broken archive stone. The largest tracks circle a blackglass pedestal without ever crossing its center.",
        {"west": "blackglass_shattered_marker", "south": HUMAN_CLUE_KEY},
        tags=("level_14_15", "boss"),
    ),
    _room(
        HUMAN_CLUE_KEY, "Bearing Chamber", HUMAN_REGION_KEY,
        "A roofless survey chamber holds a surviving blackglass sighting frame. Its old road bearings make sense until the final engraved line drops below the horizon.",
        {"north": HUMAN_BOSS_ROOM_KEY, "south": HUMAN_ENDPOINT_KEY},
        tags=("level_15", "witness", "choice"),
    ),
    _room(
        HUMAN_ENDPOINT_KEY, "Blackglass Frontier Approach", HUMAN_REGION_KEY,
        "The old Human relay road becomes a patched frontier track. Ashcross's palisade is visible through the dust, built from everybody's materials rather than anybody's style.",
        {"north": HUMAN_CLUE_KEY, "east": ASHCROSS_GATE_KEY},
        tags=("level_15", "regional_link"),
    ),
)

FOREST_ROOMS = (
    _room(
        FOREST_ENTRY_KEY, "Green Lane", FOREST_REGION_KEY,
        "Behind Veyra's alchemy hall, a service lane becomes a planted road of alder and willow maintained by Forest Elf herb caravans and anyone willing to follow their pruning marks.",
        {"north": VEYRA_GREENHALL_KEY, "south": "alderwake_lantern_grove"},
        enemies=(ALDERWAKE_TUSKER.key,), tags=("level_12_13", "forest_elf_road"),
    ),
    _room(
        "alderwake_lantern_grove", "Lantern Grove", FOREST_REGION_KEY,
        "Glass-covered trail lamps hang from living branches without nails. The road is cultivated rather than wild, and every repaired bank shows generations of practical stewardship.",
        {"north": FOREST_ENTRY_KEY, "south": FOREST_MENTOR_KEY},
        tags=("level_12_13", "managed_forest"),
    ),
    _room(
        FOREST_MENTOR_KEY, "Alderwake Circle Camp", FOREST_REGION_KEY,
        "A temporary Druidic Circle camp surrounds a work table of maps, pruning knives, water samples, and traffic tallies. Governance here looks mostly like people arguing over maintenance.",
        {"north": "alderwake_lantern_grove", "south": "alderwake_wetroot_walk"},
        npcs=(FOREST_NPC_KEY,), tags=("level_12_13", "safe", "circle"),
    ),
    _room(
        "alderwake_wetroot_walk", "Wetroot Walk", FOREST_REGION_KEY,
        "Raised planks carry the road across saturated ground. Fresh hoof damage has forced travelers onto narrower paths marked with patient, increasingly irritated repair signs.",
        {"north": FOREST_MENTOR_KEY, "south": "alderwake_ringfield"},
        enemies=(ALDERWAKE_TUSKER.key,), tags=("level_13_14", "managed_forest"),
    ),
    _room(
        "alderwake_ringfield", "Ringfield", FOREST_REGION_KEY,
        "Dozens of young trees lean away from an invisible straight boundary. None are sick. None have died. They simply refuse one line of otherwise healthy soil.",
        {"north": "alderwake_wetroot_walk", "east": FOREST_BOSS_ROOM_KEY},
        tags=("level_14", "anomaly_hint"),
    ),
    _room(
        FOREST_BOSS_ROOM_KEY, "Scarboar Hollow", FOREST_REGION_KEY,
        "A churned wallow blocks the oldest path. Bark stripped from nearby trunks reveals ring scars repeating the same impossible straight edge.",
        {"west": "alderwake_ringfield", "south": FOREST_CLUE_KEY},
        tags=("level_14_15", "boss"),
    ),
    _room(
        FOREST_CLUE_KEY, "Yearring Stump", FOREST_REGION_KEY,
        "A storm-felled alder has been cut cleanly for study. Its rings curve around a ruler-straight absence that persisted through drought, flood, and thirty-seven ordinary growing seasons.",
        {"north": FOREST_BOSS_ROOM_KEY, "south": FOREST_ENDPOINT_KEY},
        tags=("level_15", "witness", "choice"),
    ),
    _room(
        FOREST_ENDPOINT_KEY, "Hushwood Edge", FOREST_REGION_KEY,
        "The managed grove thins into older frontier forest. Ahead, Ashcross's Hushwood pocket begins where the same strange quiet touches an abandoned foundation.",
        {"north": FOREST_CLUE_KEY, "west": ASHCROSS_HUSHWOOD_KEY},
        tags=("level_15", "regional_link"),
    ),
)

GOBLIN_ROOMS = (
    _room(
        GOBLIN_ENTRY_KEY, "Dock Cut", GOBLIN_REGION_KEY,
        "A side channel below Veyra's quays is crowded with patched barges, salvage cages, and Goblin claim tags. Everything looks improvised until you notice the traffic never actually jams.",
        {"north": VEYRA_LOWER_QUAYS_KEY, "south": "rattlechain_scrapbank"},
        enemies=(RATTLECHAIN_SCAVENGER.key,), tags=("level_12_13", "goblin_road"),
    ),
    _room(
        "rattlechain_scrapbank", "Scrapbank", GOBLIN_REGION_KEY,
        "Sorted piles of useful metal sit on stone pads above the mud: bent plate, good hinges, questionable springs, perfect bolts, and a locked bin labeled DO NOT GET CLEVER.",
        {"north": GOBLIN_ENTRY_KEY, "south": GOBLIN_MENTOR_KEY},
        tags=("level_12_13", "salvage"),
    ),
    _room(
        GOBLIN_MENTOR_KEY, "Rattlechain Claimhouse", GOBLIN_REGION_KEY,
        "A low office serves three rival salvage crews. Claim boards cover every wall, and the only rule posted larger than the prices is BRING A WITNESS.",
        {"north": "rattlechain_scrapbank", "south": "rattlechain_tin_bridge"},
        npcs=(GOBLIN_NPC_KEY,), tags=("level_12_13", "safe", "commerce"),
    ),
    _room(
        "rattlechain_tin_bridge", "Tin Bridge", GOBLIN_REGION_KEY,
        "A narrow bridge of mismatched plates flexes under traffic but has outlasted two expensive stone replacements. Mireclamps pick through the silt underneath.",
        {"north": GOBLIN_MENTOR_KEY, "south": "rattlechain_sorting_yard"},
        enemies=(RATTLECHAIN_SCAVENGER.key,), tags=("level_13_14", "salvage"),
    ),
    _room(
        "rattlechain_sorting_yard", "Sorting Yard", GOBLIN_REGION_KEY,
        "Crews have laid unrelated finds into chalk outlines. Five pieces from five sites fit around the same empty straight-edged shape with insulting precision.",
        {"north": "rattlechain_tin_bridge", "east": GOBLIN_BOSS_ROOM_KEY},
        tags=("level_14", "anomaly_hint"),
    ),
    _room(
        GOBLIN_BOSS_ROOM_KEY, "Claimbreaker Pit", GOBLIN_REGION_KEY,
        "An ancient hauling frame jerks beneath salvage chains whenever anyone tries to pull it free. No Goblin claims to have built it, which is probably why everyone wants it.",
        {"west": "rattlechain_sorting_yard", "south": GOBLIN_CLUE_KEY},
        tags=("level_14_15", "boss"),
    ),
    _room(
        GOBLIN_CLUE_KEY, "Impossible Fit Bench", GOBLIN_REGION_KEY,
        "A reinforced workbench holds the best pieces under clamps. Their outer edges disagree in age, alloy, and workmanship; their inner edges make one perfect missing line.",
        {"north": GOBLIN_BOSS_ROOM_KEY, "south": GOBLIN_ENDPOINT_KEY},
        tags=("level_15", "witness", "choice"),
    ),
    _room(
        GOBLIN_ENDPOINT_KEY, "Culvert Mouth", GOBLIN_REGION_KEY,
        "The salvage run narrows into an old drainage channel. Goblin repair marks stop exactly where Ashcross's abandoned culvert begins.",
        {"north": GOBLIN_CLUE_KEY, "west": ASHCROSS_CULVERT_KEY},
        tags=("level_15", "regional_link"),
    ),
)

UNDEAD_ROOMS = (
    _room(
        UNDEAD_ENTRY_KEY, "Pale Road Arch", UNDEAD_REGION_KEY,
        "An old arch beyond Veyra's bridge quarter marks a funerary road now used by couriers, pilgrims, and Undead record houses. Nobody lowers their voice unless someone is actually being buried.",
        {"west": VEYRA_OLD_BRIDGE_KEY, "east": "pale_road_dry_canal"},
        enemies=(PALE_ROAD_HOUND.key,), tags=("level_12_13", "undead_road"),
    ),
    _room(
        "pale_road_dry_canal", "Dry Canal", UNDEAD_REGION_KEY,
        "A drained stone channel makes a flat walking road between old tomb walls. Names have been repaired more carefully than the masonry.",
        {"west": UNDEAD_ENTRY_KEY, "east": UNDEAD_MENTOR_KEY},
        tags=("level_12_13", "funerary"),
    ),
    _room(
        UNDEAD_MENTOR_KEY, "Pale Road Record House", UNDEAD_REGION_KEY,
        "Shelves of wax, stone, and paper testimony fill a cool roadside archive. Each account is filed by witness, date of first death, date of reanimation, and confidence.",
        {"west": "pale_road_dry_canal", "east": "pale_road_name_stones"},
        npcs=(UNDEAD_NPC_KEY,), tags=("level_12_13", "safe", "archive"),
    ),
    _room(
        "pale_road_name_stones", "Name Stones", UNDEAD_REGION_KEY,
        "Rows of memorial stones record travelers who died permanently, travelers later reanimated elsewhere, and travelers whose fate remains unknown. The categories matter here.",
        {"west": UNDEAD_MENTOR_KEY, "east": "pale_road_echo_field"},
        enemies=(PALE_ROAD_HOUND.key,), tags=("level_13_14", "funerary"),
    ),
    _room(
        "pale_road_echo_field", "Echo Field", UNDEAD_REGION_KEY,
        "Broken walls throw voices back with unusual clarity. Several copied testimonies describe a corridor descending beneath this field even though no entrance appears on any survey.",
        {"west": "pale_road_name_stones", "south": UNDEAD_BOSS_ROOM_KEY},
        tags=("level_14", "anomaly_hint"),
    ),
    _room(
        UNDEAD_BOSS_ROOM_KEY, "Mnemonic Hollow", UNDEAD_REGION_KEY,
        "Gray shell fragments lie around a depression where delayed voices answer statements nobody made. The road archive has marked the site CONTAMINATED TESTIMONY.",
        {"north": "pale_road_echo_field", "east": UNDEAD_CLUE_KEY},
        tags=("level_14_15", "boss"),
    ),
    _room(
        UNDEAD_CLUE_KEY, "False-Memory Crypt", UNDEAD_REGION_KEY,
        "Five sealed testimony slates rest beside five biographies that never intersect. Every witness remembers the same downward turn here. None was alive here to take it.",
        {"west": UNDEAD_BOSS_ROOM_KEY, "east": UNDEAD_ENDPOINT_KEY},
        tags=("level_15", "witness", "choice"),
    ),
    _room(
        UNDEAD_ENDPOINT_KEY, "Sunken Approach", UNDEAD_REGION_KEY,
        "The funerary road reaches a collapsed watch line where old courier hooks survive above black water. Ashcross's Sunken Watch lies just beyond.",
        {"west": UNDEAD_CLUE_KEY, "east": ASHCROSS_SUNKEN_WATCH_KEY},
        tags=("level_15", "regional_link"),
    ),
)

SPOREKIN_ROOMS = (
    _room(
        SPOREKIN_ENTRY_KEY, "Hearth Cellar", SPOREKIN_REGION_KEY,
        "Below Veyra's public commonhouse, a legal service cellar shares space with a Sporekin guide-route. Fungal lamps mark which passages belong to the city and which continue farther than the city does.",
        {"up": VEYRA_PUBLIC_HEARTH_KEY, "down": "rainroot_damp_stair"},
        enemies=(RAINROOT_BORER.key,), tags=("level_12_13", "sporekin_road"),
    ),
    _room(
        "rainroot_damp_stair", "Damp Stair", SPOREKIN_REGION_KEY,
        "Water beads on old stone steps threaded with living mycelium. The route feels hidden without being secret; small guide marks appear wherever a stranger might reasonably get lost.",
        {"up": SPOREKIN_ENTRY_KEY, "down": SPOREKIN_MENTOR_KEY},
        tags=("level_12_13", "underway"),
    ),
    _room(
        SPOREKIN_MENTOR_KEY, "Rainroot Guide Nexus", SPOREKIN_REGION_KEY,
        "Several underways meet around a dry shelf where guides exchange route memories, physical maps, and corrections when the two disagree.",
        {"up": "rainroot_damp_stair", "east": "rainroot_threadwalk"},
        npcs=(SPOREKIN_NPC_KEY,), tags=("level_12_13", "safe", "shared_consciousness"),
    ),
    _room(
        "rainroot_threadwalk", "Threadwalk", SPOREKIN_REGION_KEY,
        "Pale mycelial cords trace the walls like living road lines. Individual strands split and rejoin constantly, a physical reminder that shared connection is not sameness.",
        {"west": SPOREKIN_MENTOR_KEY, "east": "rainroot_spore_bridge"},
        enemies=(RAINROOT_BORER.key,), tags=("level_13_14", "underway"),
    ),
    _room(
        "rainroot_spore_bridge", "Spore Bridge", SPOREKIN_REGION_KEY,
        "A root mass bridges a vertical crack. Every living thread stops short of one ruler-straight stripe in the far wall before continuing normally above and below it.",
        {"west": "rainroot_threadwalk", "south": SPOREKIN_BOSS_ROOM_KEY},
        tags=("level_14", "anomaly_hint"),
    ),
    _room(
        SPOREKIN_BOSS_ROOM_KEY, "Root-Borer Nest", SPOREKIN_REGION_KEY,
        "Pulped deadwood and shed shell plates fill a warm chamber. The largest tunnel curves around the silent seam as precisely as the mycelium does.",
        {"north": "rainroot_spore_bridge", "east": SPOREKIN_CLUE_KEY},
        tags=("level_14_15", "boss"),
    ),
    _room(
        SPOREKIN_CLUE_KEY, "Silent Seam", SPOREKIN_REGION_KEY,
        "Healthy mycelium crowds both sides of a perfectly straight bare line. Touching the network here carries thought, emotion, and direction normally until attention crosses the seam and simply fails to arrive.",
        {"west": SPOREKIN_BOSS_ROOM_KEY, "up": SPOREKIN_ENDPOINT_KEY},
        tags=("level_15", "witness", "choice"),
    ),
    _room(
        SPOREKIN_ENDPOINT_KEY, "Below Hushwood", SPOREKIN_REGION_KEY,
        "Rain filters through roots overhead. A narrow ascent reaches the quiet forest pocket outside Ashcross, where surface trees avoid the same hidden center.",
        {"down": SPOREKIN_CLUE_KEY, "up": ASHCROSS_HUSHWOOD_KEY},
        tags=("level_15", "regional_link"),
    ),
)

FIVE_ROAD_ROOMS = HUMAN_ROOMS + FOREST_ROOMS + GOBLIN_ROOMS + UNDEAD_ROOMS + SPOREKIN_ROOMS
FIVE_ROAD_ROOM_KEYS = tuple(room.key for room in FIVE_ROAD_ROOMS)


HUMAN_ROUTE = WitnessRoute(
    key="human", race_key="human", label="Blackglass March", region_key=HUMAN_REGION_KEY,
    quest=HUMAN_QUEST, room_keys=tuple(room.key for room in HUMAN_ROOMS), mentor_room_key=HUMAN_MENTOR_KEY,
    boss_room_key=HUMAN_BOSS_ROOM_KEY, clue_room_key=HUMAN_CLUE_KEY, completion_flag=HUMAN_COMPLETE_FLAG,
    boss_flag=HUMAN_BOSS_FLAG, witness_item_key=HUMAN_WITNESS_ITEM_KEY, choice_a_flag=HUMAN_ARCHIVE_FLAG,
    choice_b_flag=HUMAN_SHARE_FLAG, talk_commands=("talk marra", "talk archivist", "talk vale"),
    study_commands=("inspect bearing", "read lens", "study lens"), choice_a_commands=("archive relic", "archive lens"),
    choice_b_commands=("share relic", "share lens"),
    mentor_text="Marra unfolds three generations of road rubbings. 'Follow the old markers to the Hollowhorn den. The lens is evidence; do not turn it into ancestry theater.'",
    study_text="The blackglass sighting lines agree with modern bearings until the final mark. It points below the frontier on the same impossible straight axis.",
    choice_a_text="You recommend placing the original lens in controlled archive storage while circulating exact rubbings and measurements.",
    choice_b_text="You recommend putting the original lens on public display in Veyra with provenance, uncertainty, and measurements attached.", xp_reward=2300,
)
FOREST_ROUTE = WitnessRoute(
    key="forest", race_key="forest_elf", label="Alderwake Road", region_key=FOREST_REGION_KEY,
    quest=FOREST_QUEST, room_keys=tuple(room.key for room in FOREST_ROOMS), mentor_room_key=FOREST_MENTOR_KEY,
    boss_room_key=FOREST_BOSS_ROOM_KEY, clue_room_key=FOREST_CLUE_KEY, completion_flag=FOREST_COMPLETE_FLAG,
    boss_flag=FOREST_BOSS_FLAG, witness_item_key=FOREST_WITNESS_ITEM_KEY, choice_a_flag=FOREST_REST_FLAG,
    choice_b_flag=FOREST_WARD_FLAG, talk_commands=("talk leth", "talk keeper", "talk circle-keeper"),
    study_commands=("read rings", "inspect rings", "study stump"), choice_a_commands=("rest grove", "close grove"),
    choice_b_commands=("ward crossing", "keep crossing"),
    mentor_text="Leth presses a muddy map flat. 'The grove is not asking us a question. Trees do not owe us metaphors. Clear the Scarboar path and read what actually grew.'",
    study_text="Thirty-seven years of growth bend around the same straight absence. The tree remained healthy; something simply occupied a line that roots and rings would not cross.",
    choice_a_text="You back a seasonal rest period for the grove while traffic is rerouted and the anomaly is measured without constant disturbance.",
    choice_b_text="You keep the crossing open under a warded, narrow route with traffic limits and continuing ring measurements.", xp_reward=2350,
)
GOBLIN_ROUTE = WitnessRoute(
    key="goblin", race_key="goblin", label="Rattlechain Run", region_key=GOBLIN_REGION_KEY,
    quest=GOBLIN_QUEST, room_keys=tuple(room.key for room in GOBLIN_ROOMS), mentor_room_key=GOBLIN_MENTOR_KEY,
    boss_room_key=GOBLIN_BOSS_ROOM_KEY, clue_room_key=GOBLIN_CLUE_KEY, completion_flag=GOBLIN_COMPLETE_FLAG,
    boss_flag=GOBLIN_BOSS_FLAG, witness_item_key=GOBLIN_WITNESS_ITEM_KEY, choice_a_flag=GOBLIN_SPLIT_FLAG,
    choice_b_flag=GOBLIN_AUCTION_FLAG, talk_commands=("talk skrit", "talk fixer", "talk patchmark"),
    study_commands=("fit plates", "assemble plates", "inspect fit"), choice_a_commands=("split claim", "divide claim"),
    choice_b_commands=("open auction", "auction claim"),
    mentor_text="Skrit slaps five claim tags onto one board. 'Nobody gets to call dibs on a hole. Stop the old hauler, then bring me measurements from the fit bench.'",
    study_text="Different alloys, different ages, different tool marks. Yet every fragment terminates at the same mathematically straight missing edge.",
    choice_a_text="You split custody among the crews and require duplicate measurements so no single clan can bury or monopolize the find.",
    choice_b_text="You open the find to a witnessed public auction with the measurements released first, making the information impossible to own.", xp_reward=2400,
)
UNDEAD_ROUTE = WitnessRoute(
    key="undead", race_key="undead", label="Pale Pilgrim Road", region_key=UNDEAD_REGION_KEY,
    quest=UNDEAD_QUEST, room_keys=tuple(room.key for room in UNDEAD_ROOMS), mentor_room_key=UNDEAD_MENTOR_KEY,
    boss_room_key=UNDEAD_BOSS_ROOM_KEY, clue_room_key=UNDEAD_CLUE_KEY, completion_flag=UNDEAD_COMPLETE_FLAG,
    boss_flag=UNDEAD_BOSS_FLAG, witness_item_key=UNDEAD_WITNESS_ITEM_KEY, choice_a_flag=UNDEAD_SEAL_FLAG,
    choice_b_flag=UNDEAD_PUBLISH_FLAG, talk_commands=("talk ossan", "talk recorder", "talk clerk"),
    study_commands=("compare memories", "read slate", "compare slates"), choice_a_commands=("seal record", "hold record"),
    choice_b_commands=("publish record", "release record"),
    mentor_text="Ossan separates five slates. 'Do not call it ancestral memory. The witnesses do not share ancestry. Clear the echo contamination and compare the statements yourself.'",
    study_text="The biographies never intersect, yet every testimony includes the same turn into a downward corridor at the same coordinate. None of the witnesses ever walked it alive.",
    choice_a_text="You seal identifying details while preserving the measurements and shared corridor description for controlled verification.",
    choice_b_text="You publish the full testimony set with confidence notes so other record houses can test for matching false memories.", xp_reward=2450,
)
SPOREKIN_ROUTE = WitnessRoute(
    key="sporekin", race_key="sporekin", label="Rainroot Threadway", region_key=SPOREKIN_REGION_KEY,
    quest=SPOREKIN_QUEST, room_keys=tuple(room.key for room in SPOREKIN_ROOMS), mentor_room_key=SPOREKIN_MENTOR_KEY,
    boss_room_key=SPOREKIN_BOSS_ROOM_KEY, clue_room_key=SPOREKIN_CLUE_KEY, completion_flag=SPOREKIN_COMPLETE_FLAG,
    boss_flag=SPOREKIN_BOSS_FLAG, witness_item_key=SPOREKIN_WITNESS_ITEM_KEY, choice_a_flag=SPOREKIN_OPEN_FLAG,
    choice_b_flag=SPOREKIN_VEIL_FLAG, talk_commands=("talk somn", "talk guide", "talk somn-of-rain"),
    study_commands=("listen silence", "trace threads", "study seam"), choice_a_commands=("open thread", "open route"),
    choice_b_commands=("veil thread", "hide route"),
    mentor_text="Somn rests one hand on the living wall. 'The shared thread goes quiet there. That is not permission to guess why. Walk, clear the borers, and listen from both sides.'",
    study_text="The shared consciousness remains vivid on either side, but no impression crosses the straight seam. The silence has a shape, a location, and no known biological cause.",
    choice_a_text="You open a marked guide-thread to outside researchers, with Sporekin guides controlling traffic through the sensitive network.",
    choice_b_text="You veil the living route while releasing physical samples and measurements, protecting the network without hiding the anomaly.", xp_reward=2500,
)

FIVE_ROUTES = (HUMAN_ROUTE, FOREST_ROUTE, GOBLIN_ROUTE, UNDEAD_ROUTE, SPOREKIN_ROUTE)
ROUTE_BY_BOSS_KEY = {
    HUMAN_BOSS_KEY: HUMAN_ROUTE,
    FOREST_BOSS_KEY: FOREST_ROUTE,
    GOBLIN_BOSS_KEY: GOBLIN_ROUTE,
    UNDEAD_BOSS_KEY: UNDEAD_ROUTE,
    SPOREKIN_BOSS_KEY: SPOREKIN_ROUTE,
}
BOSS_BY_ROUTE_KEY = {
    "human": HOLLOWHORN_STALKER,
    "forest": RING_SCAR_BOAR,
    "goblin": OLD_CLAIMBREAKER,
    "undead": MNEMONIC_HUSK,
    "sporekin": ROOT_BORER_MATRIARCH,
}

ALL_WITNESS_FLAGS = (
    TROLL_COMPLETE_FLAG,
    DWARF_COMPLETE_FLAG,
    MOON_COMPLETE_FLAG,
    HUMAN_COMPLETE_FLAG,
    FOREST_COMPLETE_FLAG,
    GOBLIN_COMPLETE_FLAG,
    UNDEAD_COMPLETE_FLAG,
    SPOREKIN_COMPLETE_FLAG,
)

WITNESS_LABELS = (
    ("Thornwake root witness", TROLL_COMPLETE_FLAG),
    ("Deepwheel zero-depth gauge", DWARF_COMPLETE_FLAG),
    ("Counterstar plate", MOON_COMPLETE_FLAG),
    ("Blackglass bearing lens", HUMAN_COMPLETE_FLAG),
    ("Alderwake yearring slice", FOREST_COMPLETE_FLAG),
    ("Rattlechain impossible-fit plate", GOBLIN_COMPLETE_FLAG),
    ("Pale Road memory slate", UNDEAD_COMPLETE_FLAG),
    ("Rainroot silence knot", SPOREKIN_COMPLETE_FLAG),
)


def witness_count(flags) -> int:
    flag_set = set(flags)
    return sum(flag in flag_set for flag in ALL_WITNESS_FLAGS)


def _replace_room(room: RoomDefinition) -> None:
    legacy_world.ROOMS = tuple(existing for existing in legacy_world.ROOMS if existing.key != room.key) + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    legacy_world.NPCS = tuple(existing for existing in legacy_world.NPCS if existing.key != npc.key) + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _merge_augmentation(existing: RoomAugmentation | None, added: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return added
    return RoomAugmentation(
        exit_overrides=existing.exit_overrides + added.exit_overrides,
        extra_exits=existing.extra_exits + added.extra_exits,
        features=existing.features + added.features,
        description_layers=existing.description_layers + added.description_layers,
    )


def eight_road_augmentations() -> dict[str, RoomAugmentation]:
    return {
        VEYRA_SOUTH_SPRAWL_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="south", destination_key=HUMAN_ENTRY_KEY, name="Blackglass March", aliases=("blackglass", "human road"), travel_text="You leave Veyra's timber sprawl by the old Human ferry road.", condition=ViewCondition(min_level=12), failure_text="The southern relay road is rated for experienced travelers: level 12."),
        )),
        VEYRA_GREENHALL_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="south", destination_key=FOREST_ENTRY_KEY, name="Alderwake Road", aliases=("alderwake", "green lane"), travel_text="You follow herb caravans out along the planted Green Lane.", condition=ViewCondition(min_level=12), failure_text="The Alderwake road is level-12 frontier work."),
        )),
        VEYRA_LOWER_QUAYS_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="south", destination_key=GOBLIN_ENTRY_KEY, name="Rattlechain Run", aliases=("rattlechain", "dock cut"), travel_text="You take the salvage cut beneath the working quays.", condition=ViewCondition(min_level=12), failure_text="The salvage crews will not clear you for Rattlechain before level 12."),
        )),
        VEYRA_OLD_BRIDGE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="east", destination_key=UNDEAD_ENTRY_KEY, name="Pale Pilgrim Road", aliases=("pale road", "pilgrim road"), travel_text="You pass beneath the old funerary arch and onto the Pale Road.", condition=ViewCondition(min_level=12), failure_text="The record houses recommend level 12 before the outer Pale Road."),
        )),
        VEYRA_PUBLIC_HEARTH_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="down", destination_key=SPOREKIN_ENTRY_KEY, name="Rainroot Threadway", aliases=("rainroot", "threadway", "cellar"), travel_text="You descend through the marked public cellar into the Rainroot guide-route.", condition=ViewCondition(min_level=12), failure_text="The Rainroot guides reserve the deeper threadway for level-12 travelers."),
        )),
        ASHCROSS_GATE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="west", destination_key=HUMAN_ENDPOINT_KEY, name="Blackglass Approach", aliases=("blackglass",), travel_text="You leave the palisade by the blackglass-marked western track."),
        )),
        ASHCROSS_HUSHWOOD_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="east", destination_key=FOREST_ENDPOINT_KEY, name="Alderwake Edge", aliases=("alderwake",), travel_text="You follow cultivated trail marks east into Alderwake."),
            ExitDefinition(direction="down", destination_key=SPOREKIN_ENDPOINT_KEY, name="Rainroot Descent", aliases=("rainroot", "threadway"), travel_text="A guide-marked root stair descends beneath Hushwood."),
        )),
        ASHCROSS_CULVERT_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="east", destination_key=GOBLIN_ENDPOINT_KEY, name="Rattlechain Culvert", aliases=("rattlechain",), travel_text="Goblin repair scratches lead east into the salvage run."),
        )),
        ASHCROSS_SUNKEN_WATCH_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(direction="west", destination_key=UNDEAD_ENDPOINT_KEY, name="Pale Road Approach", aliases=("pale road",), travel_text="You follow the old courier hooks west onto the funerary road."),
        )),
    }


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _active_quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _ensure_route_quest(session) -> None:
    if session.character is None or session.character.level < 12:
        return
    room = session.character.current_room
    flags = _flags(session)
    for route in FIVE_ROUTES:
        if room in route.room_keys and _active_quest(session, route.quest.key) is None and route.completion_flag not in flags:
            session.database.start_quest(session.character.id, route.quest.key, "talk_mentor")
            return


def _route_for_current_room(session) -> WitnessRoute | None:
    if session.character is None:
        return None
    room = session.character.current_room
    return next((route for route in FIVE_ROUTES if room in route.room_keys), None)


def _can_enter_meridian(session) -> bool:
    if session.character is None:
        return False
    flags = _flags(session)
    return session.character.level >= 19 and OUTER_COMPLETE_FLAG in flags and witness_count(flags) >= WITNESSES_REQUIRED


def _grant_once(session, flag: str) -> bool:
    if session.character is None or flag in _flags(session):
        return False
    session.database.grant_flag(session.character.id, flag)
    return True


def _victory_sessions(session, enemy):
    finder = getattr(session, "party_victory_sessions", None)
    if callable(finder):
        found = finder(enemy)
        if found:
            return list(found)
    return [session]


async def _talk_route_mentor(session, route: WitnessRoute) -> bool:
    if session.character is None or session.character.current_room != route.mentor_room_key:
        return False
    _ensure_route_quest(session)
    q = _active_quest(session, route.quest.key)
    if q and q["status"] == "active" and q["current_step"] == "talk_mentor":
        session.database.advance_quest(session.character.id, route.quest.key, "reach_boss")
    own = session.character.race == route.race_key
    prefix = "This is one of your culture's frontier roads. " if own else ""
    await session.send(prefix + route.mentor_text + "\r\n")
    return True


async def _study_route(session, route: WitnessRoute) -> bool:
    if session.character is None or session.character.current_room != route.clue_room_key:
        return False
    q = _active_quest(session, route.quest.key)
    if not q or q["status"] != "active":
        return False
    if route.boss_flag not in _flags(session):
        await session.send("The witness site is not secure enough to study yet.\r\n")
        return True
    if q["current_step"] == "study_witness":
        session.database.advance_quest(session.character.id, route.quest.key, "choose_response")
    await session.send(route.study_text + " Choose one of the two recorded responses for this road.\r\n")
    return True


async def _choose_route(session, route: WitnessRoute, first: bool) -> bool:
    if session.character is None or session.character.current_room != route.clue_room_key:
        return False
    q = _active_quest(session, route.quest.key)
    if not q or q["status"] != "active" or q["current_step"] != "choose_response":
        return False
    session.database.grant_flag(session.character.id, route.choice_a_flag if first else route.choice_b_flag)
    session.database.grant_flag(session.character.id, route.completion_flag)
    if session.database.item_quantity(session.character.id, route.witness_item_key) <= 0:
        session.database.add_item(session.character.id, route.witness_item_key, 1)
    session.database.add_experience(session.character.id, route.xp_reward)
    session.database.complete_quest(session.character.id, route.quest.key)
    _refresh(session)
    text = route.choice_a_text if first else route.choice_b_text
    await session.send(f"{text} Quest complete: {route.xp_reward} XP and an independent Meridian witness.\r\n")
    return True


async def _align_any_three(session) -> bool:
    if session.character is None or session.character.current_room != MERIDIAN_WITNESS_KEY:
        return False
    flags = _flags(session)
    count = witness_count(flags)
    if session.character.level < 19:
        await session.send("The Meridian descent is level-19 work.\r\n")
        return True
    if OUTER_COMPLETE_FLAG not in flags:
        await session.send("Map and report the Meridian Outerworks before trusting the deeper route.\r\n")
        return True
    if count < WITNESSES_REQUIRED:
        await session.send(f"The witness cradles need three independent regional lines of evidence. You have {count}/3.\r\n")
        return True
    q = _active_quest(session, MERIDIAN_QUEST_KEY)
    if q is None:
        session.database.start_quest(session.character.id, MERIDIAN_QUEST_KEY, "align_witnesses")
    elif q["status"] == "active" and q["current_step"] == "enter_vault":
        session.database.advance_quest(session.character.id, MERIDIAN_QUEST_KEY, "align_witnesses")
    session.database.advance_quest(session.character.id, MERIDIAN_QUEST_KEY, "descend")
    _grant_once(session, MERIDIAN_ALIGNED_FLAG)
    labels = [label for label, flag in WITNESS_LABELS if flag in flags][:WITNESSES_REQUIRED]
    await session.send("Three adjustable witness cradles lock around independent evidence from " + ", ".join(labels) + ". Different cultures, different measurements, same impossible coordinate. The deeper lock opens east.\r\n")
    return True


async def _delegate(self, previous_prompt, command):
    had = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")

    async def replay(_text):
        return command

    self.prompt = replay
    try:
        await previous_prompt(self)
    finally:
        if had:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_eight_roads_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_eight_roads_runtime_installed", False):
        return

    for quest in FIVE_ROAD_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in FIVE_ROAD_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in FIVE_ROAD_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for npc in FIVE_ROAD_NPCS:
        _replace_npc(npc)
    for room in FIVE_ROAD_ROOMS:
        _replace_room(room)

    for room_key, description in (
        (ASHCROSS_MILESTONE_KEY, "Regional roads, trails, culverts, guide-routes, and old causeways meet around a battered marker whose original inscription is gone. Ashcross is south; every other direction seems to remember a different people."),
        (MERIDIAN_CAMP_KEY, "Independent evidence from roads across Astralis points through the same unmarked wall. No single culture owns the measurement, and none of the measurements explain the structure."),
        (MERIDIAN_WITNESS_KEY, "Three adjustable witness cradles stand before the inner lock. They were rebuilt by the Ashcross expedition specifically so three independent regional records can be compared without pretending one culture's instrument is universal."),
    ):
        old_room = legacy_world.ROOMS_BY_KEY.get(room_key)
        if old_room is not None:
            _replace_room(replace(old_room, description=description))

    old_intro = quests.QUESTS_BY_KEY.get(INTRO_QUEST_KEY)
    if old_intro is not None:
        patched_intro = QuestDefinition(
            key=old_intro.key,
            name=old_intro.name,
            style=old_intro.style,
            minimum_level=old_intro.minimum_level,
            description="Eight culturally distinct level-12 frontier approaches now feed the Ashcross network. The town is where those roads overlap without flattening the peoples who built them.",
            objective_steps=old_intro.objective_steps,
        )
        quests.QUESTS = tuple(q for q in quests.QUESTS if q.key != INTRO_QUEST_KEY) + (patched_intro,)
        quests.QUESTS_BY_KEY[INTRO_QUEST_KEY] = patched_intro

    for room in FIVE_ROAD_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for key in (ASHCROSS_MILESTONE_KEY, MERIDIAN_CAMP_KEY, MERIDIAN_WITNESS_KEY):
        if key in legacy_world.ROOMS_BY_KEY:
            world_service.legacy_rooms[key] = legacy_world.ROOMS_BY_KEY[key]

    for room_key, augmentation in eight_road_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)

    current = world_service.augmentations.get(OUTER_DEEP_GATE_KEY, RoomAugmentation())
    deep_exits = tuple(exit_def for exit_def in current.extra_exits if exit_def.direction != "east") + (
        ExitDefinition(
            direction="east",
            destination_key=MERIDIAN_CAMP_KEY,
            name="Meridian Descent",
            aliases=("meridian", "deep seam", "vault"),
            travel_text="The deep seam opens into the expedition's Confluence Camp.",
            condition=ViewCondition(min_level=19, required_flags=(OUTER_COMPLETE_FLAG,)),
            failure_text="Map and report the Outerworks first; the deeper seam is level-19 work.",
        ),
    )
    world_service.augmentations[OUTER_DEEP_GATE_KEY] = replace(current, extra_exits=deep_exits)

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*FIVE_ROAD_ROOM_KEYS, VEYRA_SOUTH_SPRAWL_KEY, VEYRA_GREENHALL_KEY, VEYRA_LOWER_QUAYS_KEY, VEYRA_OLD_BRIDGE_KEY, VEYRA_PUBLIC_HEARTH_KEY, ASHCROSS_GATE_KEY, ASHCROSS_HUSHWOOD_KEY, ASHCROSS_CULVERT_KEY, ASHCROSS_SUNKEN_WATCH_KEY, ASHCROSS_MILESTONE_KEY, OUTER_DEEP_GATE_KEY, MERIDIAN_CAMP_KEY, MERIDIAN_WITNESS_KEY):
            cache.pop(key, None)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self):
        await previous_enter(self)
        _ensure_route_quest(self)

    async def move_character(self, direction):
        if self.character is not None and self.character.current_room == OUTER_DEEP_GATE_KEY and direction.strip().lower() in {"east", "e", "meridian", "deep seam", "vault"} and not _can_enter_meridian(self):
            flags = _flags(self)
            if self.character.level < 19:
                await self.send("The Meridian descent opens at level 19.\r\n")
            elif OUTER_COMPLETE_FLAG not in flags:
                await self.send("Map and report the Outerworks before taking the deep seam.\r\n")
            else:
                count = witness_count(flags)
                await self.send(f"The expedition requires three independent regional witnesses before descent. You have {count}/3.\r\n")
            return

        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        _ensure_route_quest(self)
        if self.character is None or self.character.current_room == before:
            return

        current_room = self.character.current_room
        route = _route_for_current_room(self)
        if route is not None and current_room == route.boss_room_key:
            q = _active_quest(self, route.quest.key)
            if q and q["status"] == "active" and q["current_step"] == "reach_boss":
                self.database.advance_quest(self.character.id, route.quest.key, "defeat_boss")
                await self.send("The road's witness site is close, but the local threat blocks it.\r\n")

        if current_room == MERIDIAN_CAMP_KEY and _can_enter_meridian(self):
            q = _active_quest(self, MERIDIAN_QUEST_KEY)
            if q is None:
                self.database.start_quest(self.character.id, MERIDIAN_QUEST_KEY, "align_witnesses")
            await self.send("The Confluence Camp accepts your three independent witness lines. Take them east to the witness hall.\r\n")

    def enemy_in_current_room(self, target_text):
        if self.character is not None:
            room = self.character.current_room
            for route in FIVE_ROUTES:
                if room == route.boss_room_key and route.boss_flag not in _flags(self):
                    enemy = BOSS_BY_ROUTE_KEY[route.key]
                    if enemy.matches(target_text):
                        return EnemyState(enemy)
        return previous_lookup(self, target_text)

    async def finish_enemy(self, enemy):
        key = enemy.definition.key
        participants = _victory_sessions(self, enemy)
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active:
            return
        route = ROUTE_BY_BOSS_KEY.get(key)
        if route is None:
            return
        for member in participants:
            if getattr(member, "character", None) is None:
                continue
            _grant_once(member, route.boss_flag)
            q = _active_quest(member, route.quest.key)
            if q and q["status"] == "active" and q["current_step"] == "defeat_boss":
                member.database.advance_quest(member.character.id, route.quest.key, "study_witness")
            if member is not self:
                await member.send("[Party Progress] The route boss is down; study the regional witness site.\r\n")
        await self.send("The way to the regional witness is clear. Continue to the marked study site.\r\n")

    async def playing_prompt(self):
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"eight roads", "three roads", "midgame roads", "roads 12 20"}:
            await self.send(
                "EIGHT ROADS (12-20)\r\n"
                " - Thornwake: Troll deep-forest politics and root witness.\r\n"
                " - Deepwheel: Dwarven rail/pressure corridor and zero-depth gauge.\r\n"
                " - Counterstar: Moon Elf highroad and counterstar plate.\r\n"
                " - Blackglass March: Human history road and bearing lens.\r\n"
                " - Alderwake: Forest Elf stewardship road and yearring witness.\r\n"
                " - Rattlechain: Goblin salvage road and impossible-fit plate.\r\n"
                " - Pale Pilgrim Road: Undead testimony road and memory slate.\r\n"
                " - Rainroot Threadway: Sporekin underroad and silence knot.\r\n"
                "Complete any THREE independent witness roads. All routes can be explored by any race.\r\n"
                "Ashcross converges them at 15-16; Meridian Outerworks is 17-18; Meridian Vault opens at 19.\r\n"
            )
            return

        if normalized in {"align witnesses", "align witness", "place witnesses"}:
            if await _align_any_three(self):
                return

        if normalized in {"talk kell", "talk broker", "talk farstep"} and self.character.current_room == "ashcross_delvers_yard" and OUTER_COMPLETE_FLAG in _flags(self):
            count = witness_count(_flags(self))
            await self.send(f"Kell checks your route notes. 'Outerworks mapped. Deep seam at nineteen. Bring three independent regional witnesses; you have {count}/3.'\r\n")
            return

        for route in FIVE_ROUTES:
            if normalized in route.talk_commands and await _talk_route_mentor(self, route):
                return
            if normalized in route.study_commands and await _study_route(self, route):
                return
            if normalized in route.choice_a_commands and await _choose_route(self, route, True):
                return
            if normalized in route.choice_b_commands and await _choose_route(self, route, False):
                return

        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = enemy_in_current_room
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._eight_roads_runtime_installed = True
