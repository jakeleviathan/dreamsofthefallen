from __future__ import annotations

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.veyra_city import VEYRA_SOUTH_SPRAWL_KEY
from mud.waymeet_frontier import WAYMEET_BROKEN_MILE_KEY
from mud.world import NpcDefinition, RoomDefinition


BROKEN_REACH_REGION_KEY = "broken_reach"
HOUSE_REGION_KEY = "house_beneath_hill"

OLD_TOLL_ROAD_KEY = "broken_reach_old_toll_road"
SLEEPING_TOLLHOUSE_KEY = "broken_reach_sleeping_tollhouse"
LEANING_ORCHARD_KEY = "broken_reach_leaning_orchard"
WITCHPOST_MEADOW_KEY = "broken_reach_witchpost_meadow"
REEDGLASS_FLATS_KEY = "broken_reach_reedglass_flats"
ECHO_WELL_KEY = "broken_reach_well_without_echo"
CINDER_FORD_KEY = "broken_reach_cinder_ford"
CARAVANSERAI_KEY = "broken_reach_ragged_caravanserai"
GRINNING_CAMP_KEY = "broken_reach_grinning_camp"
HUSH_CHAPEL_KEY = "broken_reach_hush_chapel"
WINDLESS_CUT_KEY = "broken_reach_windless_cut"
CROW_COURT_KEY = "broken_reach_crow_court"
SPLIT_LANTERN_BRIDGE_KEY = "broken_reach_split_lantern_bridge"
FAR_WATCH_KEY = "broken_reach_far_watch"

HOUSE_THRESHOLD_KEY = "house_beneath_hill_threshold"
HOUSE_PARLOUR_KEY = "house_beneath_hill_stone_parlour"
HOUSE_GALLERY_KEY = "house_beneath_hill_crooked_gallery"
HOUSE_NINE_BOOTS_KEY = "house_beneath_hill_room_of_nine_boots"
HOUSE_LOST_NURSERY_KEY = "house_beneath_hill_lost_nursery"
HOUSE_ROOT_CELLAR_KEY = "house_beneath_hill_root_cellar"
HOUSE_GUEST_HALL_KEY = "house_beneath_hill_guest_hall"
HOUSE_DEEP_HEARTH_KEY = "house_beneath_hill_deep_hearth"
HOUSE_KEEPER_LOCK_KEY = "house_beneath_hill_keeper_lock"
HOUSE_UNDERHOUSE_SHAFT_KEY = "house_beneath_hill_underhouse_shaft"
HOUSE_BLACK_BELL_KEY = "house_beneath_hill_black_bell_chamber"
HOUSE_CONTAINMENT_RING_KEY = "house_beneath_hill_containment_ring"
HOUSE_BURIED_ROAD_KEY = "house_beneath_hill_buried_road"
HOUSE_WAKE_GATE_KEY = "house_beneath_hill_wake_gate"

SURFACE_ROOM_KEYS = (
    OLD_TOLL_ROAD_KEY,
    SLEEPING_TOLLHOUSE_KEY,
    LEANING_ORCHARD_KEY,
    WITCHPOST_MEADOW_KEY,
    REEDGLASS_FLATS_KEY,
    ECHO_WELL_KEY,
    CINDER_FORD_KEY,
    CARAVANSERAI_KEY,
    GRINNING_CAMP_KEY,
    HUSH_CHAPEL_KEY,
    WINDLESS_CUT_KEY,
    CROW_COURT_KEY,
    SPLIT_LANTERN_BRIDGE_KEY,
    FAR_WATCH_KEY,
)
HOUSE_ROOM_KEYS = (
    HOUSE_THRESHOLD_KEY,
    HOUSE_PARLOUR_KEY,
    HOUSE_GALLERY_KEY,
    HOUSE_NINE_BOOTS_KEY,
    HOUSE_LOST_NURSERY_KEY,
    HOUSE_ROOT_CELLAR_KEY,
    HOUSE_GUEST_HALL_KEY,
    HOUSE_DEEP_HEARTH_KEY,
    HOUSE_KEEPER_LOCK_KEY,
    HOUSE_UNDERHOUSE_SHAFT_KEY,
    HOUSE_BLACK_BELL_KEY,
    HOUSE_CONTAINMENT_RING_KEY,
    HOUSE_BURIED_ROAD_KEY,
    HOUSE_WAKE_GATE_KEY,
)
BROKEN_REACH_ROOM_KEYS = (*SURFACE_ROOM_KEYS, *HOUSE_ROOM_KEYS)

FIRST_QUEST_KEY = "broken_reach_no_smiling_matter"
FACTION_QUEST_KEY = "broken_reach_three_claims"
HOUSE_QUEST_KEY = "broken_reach_house_beneath_hill"
CAPSTONE_QUEST_KEY = "broken_reach_night_the_hill_opened"

FIRST_COMPLETE_FLAG = "broken_reach_grinning_truth_known"
FACTION_COMPLETE_FLAG = "broken_reach_claims_settled"
ROAD_STANCE_FLAG = "broken_reach_stance_open_road"
REFUGE_STANCE_FLAG = "broken_reach_stance_protect_refuge"
QUARANTINE_STANCE_FLAG = "broken_reach_stance_quarantine_hill"
WARDEN_DEFEATED_FLAG = "broken_reach_hill_warden_defeated"
CONTAINMENT_TRUTH_FLAG = "broken_reach_containment_truth_known"
HOUSE_COMPLETE_FLAG = "broken_reach_house_guest_driven_back"
REACH_CHANGED_FLAG = "broken_reach_surface_span_dropped"
CAPSTONE_COMPLETE_FLAG = "broken_reach_underroad_opened"

ODDITY_TOLLBOOK_FLAG = "broken_reach_oddity_tollbook"
ODDITY_WELL_FLAG = "broken_reach_oddity_echo_well"
ODDITY_CROWS_FLAG = "broken_reach_oddity_crow_court"
ODDITY_BOOTS_FLAG = "broken_reach_oddity_nine_boots"
ODDITY_FLAGS = (ODDITY_TOLLBOOK_FLAG, ODDITY_WELL_FLAG, ODDITY_CROWS_FLAG, ODDITY_BOOTS_FLAG)

SURVEY_RIBBON_KEY = "broken_reach_survey_ribbon"
ACCORD_TOKEN_KEY = "broken_reach_accord_token"
BENT_HOST_KEY = "broken_reach_bent_host_key"
UNDERROAD_WRIT_KEY = "broken_reach_underroad_writ"
BENT_TOLL_COIN_KEY = "broken_reach_bent_toll_coin"

HESTA_KEY = "broken_reach_surveyor_hesta_vane"
JORY_KEY = "broken_reach_jory_ninegrin"
MIRA_KEY = "broken_reach_factor_mira_sable"
ROOK_KEY = "broken_reach_threshold_warden_rook"

CINDER_HOUND_KEY = "broken_reach_cinder_hound"
REEDGLASS_STALKER_KEY = "broken_reach_reedglass_stalker"
ROAD_REAVER_KEY = "broken_reach_road_reaver"
DUST_ATTENDANT_KEY = "house_dust_attendant"
CROOKED_STEWARD_KEY = "house_crooked_steward"
HILL_WARDEN_KEY = "house_hill_warden"
NAMELESS_GUEST_KEY = "house_guest_without_name"


FIRST_QUEST = QuestDefinition(
    key=FIRST_QUEST_KEY,
    name="No Smiling Matter",
    style="structured",
    minimum_level=11,
    description=(
        "Caravans are vanishing on the thin road south of Waymeet. Everybody blames the masked Grinning Men, "
        "but the Reach contains evidence that the outlaws are frightened of the same thing as everyone else."
    ),
    objective_steps=(
        ("talk_hesta", "Reach the Ragged Caravanserai and TALK HESTA."),
        ("inspect_wagon", "Return north to the Leaning Orchard and EXAMINE WAGON."),
        ("talk_jory", "Find the Grinning Camp east of the caravanserai and TALK JORY."),
        ("inspect_lanterns", "Go south to Split-Lantern Bridge and EXAMINE LANTERNS."),
        ("return_hesta", "Return to Hesta at the Ragged Caravanserai."),
        ("complete", "You proved that the Grinning Men are not the cause of every disappearance and that something beneath the hill is pulling travelers off the road."),
    ),
)

FACTION_QUEST = QuestDefinition(
    key=FACTION_QUEST_KEY,
    name="Three Claims on One Road",
    style="structured",
    minimum_level=14,
    description=(
        "With the disappearances understood, three groups want incompatible things from the Reach: the surveyors want a road, "
        "the Grinning Men want a refuge, and the Cinder Compact wants trade restored under enforceable safety rules."
    ),
    objective_steps=(
        ("talk_hesta", "TALK HESTA about reopening the road."),
        ("talk_jory", "TALK JORY about the Grinning Men and the people sheltering with them."),
        ("talk_mira", "TALK VESSA at Cinder Ford about the Cinder Compact."),
        ("inspect_tally", "At Cinder Ford, EXAMINE TALLY."),
        ("choose_stance", "At the Ragged Caravanserai choose CHOOSE ROAD, CHOOSE REFUGE, or CHOOSE QUARANTINE."),
        ("complete", "You forced the Reach to operate under one temporary public agreement instead of three private assumptions."),
    ),
)

HOUSE_QUEST = QuestDefinition(
    key=HOUSE_QUEST_KEY,
    name="The House Beneath the Hill",
    style="structured",
    minimum_level=17,
    description=(
        "The hill-house is not a manor sitting on the ground but the upper rooms of a much older structure. "
        "The thing everybody calls its monster may be the only reason the deeper guest has stayed inside."
    ),
    objective_steps=(
        ("talk_rook", "At the Threshold Under the Hill, TALK ROOK."),
        ("read_guestbook", "In the Stone Parlour, READ GUESTBOOK."),
        ("examine_hearth", "Descend through the house and EXAMINE HEARTH in the Deep Hearth."),
        ("defeat_warden", "Defeat the Hill Warden at the Keeper's Lock."),
        ("inspect_lock", "After the Warden falls, EXAMINE LOCK."),
        ("listen_bell", "Descend and LISTEN BELL in the Black Bell Chamber."),
        ("confront_guest", "Reach the Containment Ring and defeat the Guest Without Name."),
        ("complete", "The Guest is driven back, but the damaged containment has turned the entire hill into a level-20 problem."),
    ),
)

CAPSTONE_QUEST = QuestDefinition(
    key=CAPSTONE_QUEST_KEY,
    name="The Night the Hill Opened",
    style="structured",
    minimum_level=20,
    description=(
        "The house can no longer be hidden behind warnings and masks. Stabilizing it will cost the old surface bridge, "
        "but the buried road beneath the containment ring can become a safer permanent bypass."
    ),
    objective_steps=(
        ("talk_hesta", "Return to the Ragged Caravanserai and TALK HESTA."),
        ("set_anchors", "Return to the Containment Ring and SET ANCHORS."),
        ("drop_span", "At Split-Lantern Bridge, DROP SPAN."),
        ("open_bypass", "Take the newly exposed under-road to Wake Gate and OPEN BYPASS."),
        ("complete", "The surface span is gone and the old buried road is now the controlled route through the Reach."),
    ),
)

BROKEN_REACH_QUESTS = (FIRST_QUEST, FACTION_QUEST, HOUSE_QUEST, CAPSTONE_QUEST)

BROKEN_REACH_ITEMS = (
    ItemDefinition(SURVEY_RIBBON_KEY, "Broken Reach Survey Ribbon", "A faded road ribbon stamped with Hesta Vane's correction mark: MASKS ARE NOT EVIDENCE.", "credential", tier=3),
    ItemDefinition(ACCORD_TOKEN_KEY, "Three-Claims Accord Token", "A three-notched token recording the temporary agreement that kept the Broken Reach from becoming three private roads.", "credential", tier=4),
    ItemDefinition(BENT_HOST_KEY, "Bent Host Key", "A heavy iron key taken from the House Beneath the Hill. Its teeth do not match any ordinary lock; they match the Warden's broken chest plate.", "trophy", tier=4),
    ItemDefinition(UNDERROAD_WRIT_KEY, "Underroad Writ", "A witnessed travel writ recognizing the buried road as the safe public bypass after the old surface span was dropped.", "credential", tier=5),
    ItemDefinition(BENT_TOLL_COIN_KEY, "Bent Toll Coin", "A copper toll coin folded almost in half around an old nail. The tollhouse ledger insists this exact coin was paid twice, eighty years apart.", "curio", tier=3),
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


CINDER_HOUND = _enemy(CINDER_HOUND_KEY, "Cinder Hound", ("hound", "cinder hound"), "a long-legged ash-gray hound with ember-colored eyes and road dust packed between its claws", 235, 11, 15, 2.8, 175)
REEDGLASS_STALKER = _enemy(REEDGLASS_STALKER_KEY, "Reedglass Stalker", ("stalker", "reedglass stalker"), "a mantislike marsh predator whose translucent wing cases look exactly like broken bottles among the reeds", 310, 13, 18, 2.7, 230)
ROAD_REAVER = _enemy(ROAD_REAVER_KEY, "Road Reaver", ("reaver", "road reaver"), "a splinter-band raider wearing no Grinning mask and carrying three stolen road signs as a shield", 390, 15, 22, 2.9, 310)
DUST_ATTENDANT = _enemy(DUST_ATTENDANT_KEY, "Dust Attendant", ("attendant", "dust attendant"), "a human-shaped accumulation of lint, ash, hair, and house dust politely blocking the hall", 510, 16, 25, 2.8, 430)
CROOKED_STEWARD = _enemy(CROOKED_STEWARD_KEY, "Crooked Steward", ("steward", "crooked steward"), "a tall wooden servant frame bent at the waist as if still bowing to guests who died centuries ago", 720, 17, 29, 2.9, 650)
HILL_WARDEN = _enemy(HILL_WARDEN_KEY, "Hill Warden", ("warden", "hill warden", "keeper"), "a huge stone-and-iron guardian built directly around three black locking bars that disappear into the walls", 1320, 19, 33, 2.8, 1800)
NAMELESS_GUEST = _enemy(NAMELESS_GUEST_KEY, "Guest Without Name", ("guest", "nameless guest", "guest without name"), "a person-shaped absence wearing scraps of remembered voices like formal clothes", 1850, 21, 38, 2.7, 2850)
BROKEN_REACH_ENEMIES = (CINDER_HOUND, REEDGLASS_STALKER, ROAD_REAVER, DUST_ATTENDANT, CROOKED_STEWARD, HILL_WARDEN, NAMELESS_GUEST)

BROKEN_REACH_NPCS = (
    NpcDefinition(
        HESTA_KEY,
        "Surveyor Hesta Vane",
        "a road surveyor with a cracked transit, six contradictory witness statements, and no patience for convenient conclusions",
        CARAVANSERAI_KEY,
        "Waymeet surveyor coordinating the Broken Reach investigation",
        dialogue=(
            "'A mask is not proof of a kidnapping. A missing wagon is not proof of a monster. Bring me things that survive being checked.'",
            "'A road is a promise strangers make to one another without meeting. That is why bad information breaks one faster than rain.'",
        ),
    ),
    NpcDefinition(
        JORY_KEY,
        "Jory Ninegrin",
        "an older outlaw wearing a carved smile-mask pushed up onto his forehead so you can see how tired he actually is",
        GRINNING_CAMP_KEY,
        "speaker for the Grinning Men and the families sheltering with them",
        dialogue=(
            "'We rob people sometimes. We also drag fools away from that hill. Both statements can be true.'",
            "'The smiles started because frightened travelers remembered masks better than warnings. Fine. Let them remember us.'",
        ),
    ),
    NpcDefinition(
        MIRA_KEY,
        "Factor Vessa Sable",
        "a compact caravan factor carrying a waterproof loss ledger tied shut with red cord",
        CINDER_FORD_KEY,
        "Cinder Compact factor representing stranded traders and haulers",
        dialogue=(
            "'Trade is not sacred. People eating through winter is. Sometimes those are the same problem.'",
            "'I want the road open only if open means witnessed, marked, patrolled, and closeable again.'",
        ),
    ),
    NpcDefinition(
        ROOK_KEY,
        "Rook of the Threshold",
        "a soot-dark traveler who has spent so long watching the hill-door that nobody is sure whether Rook is a title or a name",
        HOUSE_THRESHOLD_KEY,
        "keeper of the last reliable notes about the House Beneath the Hill",
        dialogue=(
            "'Do not accept hospitality from this house. It has forgotten the difference between sheltering a guest and keeping one.'",
            "'If you meet the Warden, remember that locks and jailers are not always on opposite sides of a door.'",
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
        tags=("shared_world", "broken_reach", *tags),
    )


BROKEN_REACH_ROOMS: tuple[RoomDefinition, ...] = (
    _room(OLD_TOLL_ROAD_KEY, "Old Toll Road", BROKEN_REACH_REGION_KEY, "The maintained stone of Waymeet gives up almost immediately. A weed-split toll road runs south between leaning marker posts whose mile numbers no longer agree. The Broken Reach begins less like a border than a place where everybody stopped repairing the same things.", {"north": WAYMEET_BROKEN_MILE_KEY, "south": LEANING_ORCHARD_KEY, "west": SLEEPING_TOLLHOUSE_KEY}, enemies=(CINDER_HOUND_KEY,), tags=("level_11_12", "road")),
    _room(SLEEPING_TOLLHOUSE_KEY, "The Sleeping Tollhouse", BROKEN_REACH_REGION_KEY, "A one-room tollhouse sags behind a counter polished by hands long gone. The shutters are nailed open. A ledger remains chained to the desk even though the road has not officially collected a toll in generations.", {"east": OLD_TOLL_ROAD_KEY}, tags=("oddity", "discovery")),
    _room(LEANING_ORCHARD_KEY, "Leaning Orchard", BROKEN_REACH_REGION_KEY, "Old pear trees lean in the same direction as if a single enormous wind passed through once and never quite released them. A merchant wagon lies on its side between two trunks. Nothing valuable has been neatly removed; useful things were left in the mud.", {"north": OLD_TOLL_ROAD_KEY, "south": REEDGLASS_FLATS_KEY, "east": WITCHPOST_MEADOW_KEY}, enemies=(CINDER_HOUND_KEY,), tags=("level_11_12", "investigation")),
    _room(WITCHPOST_MEADOW_KEY, "Witchpost Meadow", BROKEN_REACH_REGION_KEY, "Hundreds of ordinary fence posts stand in a meadow with no fence between them. Every post carries one rusted nail at eye height. Moths gather on only seven of the nails, regardless of weather.", {"west": LEANING_ORCHARD_KEY}, tags=("oddity", "unmarked_story")),
    _room(REEDGLASS_FLATS_KEY, "Reedglass Flats", BROKEN_REACH_REGION_KEY, "The road crosses a low wet flat where clear hollow reeds clatter like glass in the wind. Broken wagon boards have been laid down as stepping paths. More than one board carries the same carved smiling face.", {"north": LEANING_ORCHARD_KEY, "south": CINDER_FORD_KEY, "west": ECHO_WELL_KEY}, enemies=(REEDGLASS_STALKER_KEY,), tags=("level_12_13", "marsh")),
    _room(ECHO_WELL_KEY, "The Well Without Echo", BROKEN_REACH_REGION_KEY, "A waist-high stone well stands on a dry patch of ground. Dropped pebbles strike water after three heartbeats, but shouted words never return an echo. Someone has written PLEASE STOP ASKING IT YOUR NAME around the rim.", {"east": REEDGLASS_FLATS_KEY}, tags=("oddity", "discovery")),
    _room(CINDER_FORD_KEY, "Cinder Ford", BROKEN_REACH_REGION_KEY, "Black gravel makes the shallow ford look burned. Three stranded freight wagons have become a temporary counting house where the Cinder Compact records lost loads, delayed food, and drivers unwilling to continue south.", {"north": REEDGLASS_FLATS_KEY, "south": CARAVANSERAI_KEY}, npcs=(MIRA_KEY,), enemies=(REEDGLASS_STALKER_KEY,), tags=("level_13_15", "faction")),
    _room(CARAVANSERAI_KEY, "Ragged Caravanserai", BROKEN_REACH_REGION_KEY, "A roofless roadside inn survives as walls, cookfires, patched awnings, and stubborn routine. Surveyors, haulers, refugees, adventurers, and people pretending not to be Grinning Men share the same cistern while arguing about what the Reach should become.", {"north": CINDER_FORD_KEY, "south": WINDLESS_CUT_KEY, "east": GRINNING_CAMP_KEY}, npcs=(HESTA_KEY,), tags=("level_13_16", "hub", "safe", "factions")),
    _room(GRINNING_CAMP_KEY, "Camp of the Grinning Men", BROKEN_REACH_REGION_KEY, "Painted and carved smile-masks hang from lines between patched tents. The camp looks less like a bandit fort than a refugee settlement with weapons. Children have added ridiculous eyebrows to several feared outlaw masks.", {"west": CARAVANSERAI_KEY, "east": HUSH_CHAPEL_KEY}, npcs=(JORY_KEY,), tags=("level_13_16", "faction", "refuge")),
    _room(HUSH_CHAPEL_KEY, "Hush Chapel", BROKEN_REACH_REGION_KEY, "A tiny roadside chapel has had its bell removed, its clapper buried beneath the altar, and every reflective surface painted dull. The Grinning Men use the benches for sleeping when the camp is full. Nobody whispers here; they either speak normally or not at all.", {"west": GRINNING_CAMP_KEY}, tags=("lore", "safe")),
    _room(WINDLESS_CUT_KEY, "Windless Cut", BROKEN_REACH_REGION_KEY, "The road narrows between chalk banks. Grass bends at both ends of the cut, but the air inside stays perfectly still. Old caravan ribbons tied to the rock point toward the hill even when their knots were made to point away.", {"north": CARAVANSERAI_KEY, "south": SPLIT_LANTERN_BRIDGE_KEY, "east": CROW_COURT_KEY}, enemies=(ROAD_REAVER_KEY,), tags=("level_15_17", "danger")),
    _room(CROW_COURT_KEY, "Crow Court", BROKEN_REACH_REGION_KEY, "A circular foundation has become a meeting place for dozens of black crows. They leave a clean human-sized gap in the center and become offended, rather than frightened, when anyone steps into it.", {"west": WINDLESS_CUT_KEY}, tags=("oddity", "discovery")),
    _room(SPLIT_LANTERN_BRIDGE_KEY, "Split-Lantern Bridge", BROKEN_REACH_REGION_KEY, "A narrow bridge crosses a deep dry cut beneath the hill. Every third lantern faces the wrong direction. South continues toward Veyra; west, a path climbs to an iron door set directly into the hillside.", {"north": WINDLESS_CUT_KEY, "south": FAR_WATCH_KEY, "west": HOUSE_THRESHOLD_KEY}, enemies=(ROAD_REAVER_KEY,), tags=("level_16_18", "crossroads", "house_approach")),
    _room(FAR_WATCH_KEY, "Far Watch", BROKEN_REACH_REGION_KEY, "A ruined watch platform overlooks both the Reach and the first timber outskirts of Veyra. From here the whole region looks deceptively ordinary: one bad road, one low hill, one broken line of lanterns, and far too many places for a caravan to disappear.", {"north": SPLIT_LANTERN_BRIDGE_KEY, "east": VEYRA_SOUTH_SPRAWL_KEY}, tags=("level_16_20", "road", "veyra_route")),

    _room(HOUSE_THRESHOLD_KEY, "Threshold Under the Hill", HOUSE_REGION_KEY, "The door in the hill opens into a proper entry hall built too far below ground to be a house entrance. Hooks wait for coats that never came back. A brass plaque says WELCOME, EXPECTED GUEST in a script older than the road above it.", {"east": SPLIT_LANTERN_BRIDGE_KEY, "west": HOUSE_PARLOUR_KEY}, npcs=(ROOK_KEY,), tags=("dungeon", "level_17_18")),
    _room(HOUSE_PARLOUR_KEY, "Stone Parlour", HOUSE_REGION_KEY, "Stone chairs have cushions carved into them. A guestbook rests open on a table that is part of the floor. The newest ink is older than Waymeet, yet several entries use the names of people who vanished this season.", {"east": HOUSE_THRESHOLD_KEY, "west": HOUSE_GALLERY_KEY, "south": HOUSE_NINE_BOOTS_KEY}, enemies=(DUST_ATTENDANT_KEY,), tags=("dungeon", "level_17_18")),
    _room(HOUSE_NINE_BOOTS_KEY, "Room of Nine Boots", HOUSE_REGION_KEY, "Nine single boots stand in a neat line beneath nine empty coat hooks. None form a pair. Fresh road mud darkens the sole of the seventh boot although the room is dry.", {"north": HOUSE_PARLOUR_KEY}, tags=("dungeon", "oddity", "discovery")),
    _room(HOUSE_GALLERY_KEY, "Crooked Gallery", HOUSE_REGION_KEY, "Portrait frames line a corridor whose floor rises and falls by inches. The canvases have been cut away, but the painted shadows remain on the wall behind them. One shadow has changed position since you entered.", {"east": HOUSE_PARLOUR_KEY, "west": HOUSE_ROOT_CELLAR_KEY, "north": HOUSE_LOST_NURSERY_KEY}, enemies=(DUST_ATTENDANT_KEY,), tags=("dungeon", "level_17_18")),
    _room(HOUSE_LOST_NURSERY_KEY, "Lost Nursery", HOUSE_REGION_KEY, "Tiny stone beds circle a cold stove. Names scratched into the bedframes have all been carefully crossed out except one word repeated on every frame: GUEST.", {"south": HOUSE_GALLERY_KEY}, tags=("dungeon", "lore", "optional")),
    _room(HOUSE_ROOT_CELLAR_KEY, "Root Cellar", HOUSE_REGION_KEY, "Tree roots pass through fitted stone without cracking it, then turn neatly to follow grooves cut for them centuries ago. Clay storage jars contain dirt from places no map places near the Broken Reach.", {"east": HOUSE_GALLERY_KEY, "west": HOUSE_GUEST_HALL_KEY}, enemies=(CROOKED_STEWARD_KEY,), tags=("dungeon", "level_18")),
    _room(HOUSE_GUEST_HALL_KEY, "Guest Hall", HOUSE_REGION_KEY, "A long dining hall has settings for thirty-two guests and no host's chair. Each place contains a shallow depression where a nameplate once sat. The far doors are scarred from something trying to leave the deeper house.", {"east": HOUSE_ROOT_CELLAR_KEY, "west": HOUSE_DEEP_HEARTH_KEY}, enemies=(CROOKED_STEWARD_KEY,), tags=("dungeon", "level_18_19")),
    _room(HOUSE_DEEP_HEARTH_KEY, "Deep Hearth", HOUSE_REGION_KEY, "A hearth large enough to heat a manor stands cold beneath a chimney that goes down instead of up. Soot marks flow toward the floor. Three black iron bars emerge from the masonry and continue west toward the Keeper's Lock.", {"east": HOUSE_GUEST_HALL_KEY, "west": HOUSE_KEEPER_LOCK_KEY}, enemies=(DUST_ATTENDANT_KEY,), tags=("dungeon", "level_18_19")),
    _room(HOUSE_KEEPER_LOCK_KEY, "Keeper's Lock", HOUSE_REGION_KEY, "Three black locking bars terminate inside the torso of a giant stone-and-iron guardian. It has been mistaken for a jailer because nobody on the surface knew the lock and the Warden were literally the same machine.", {"east": HOUSE_DEEP_HEARTH_KEY}, enemies=(HILL_WARDEN_KEY,), tags=("dungeon", "boss", "level_19")),
    _room(HOUSE_UNDERHOUSE_SHAFT_KEY, "Underhouse Shaft", HOUSE_REGION_KEY, "A maintenance shaft drops beneath the rooms that look like a house. Here the architecture stops pretending to be domestic. Black braces, tension rings, and channels cut through raw stone around a descending iron stair.", {"up": HOUSE_KEEPER_LOCK_KEY, "down": HOUSE_BLACK_BELL_KEY}, enemies=(DUST_ATTENDANT_KEY,), tags=("dungeon", "level_19")),
    _room(HOUSE_BLACK_BELL_KEY, "Black Bell Chamber", HOUSE_REGION_KEY, "A bell without a clapper hangs inside a cage of metal ribs. It rings anyway, but only when nobody moves. Every vibration travels outward into the hill rather than through the air.", {"up": HOUSE_UNDERHOUSE_SHAFT_KEY, "west": HOUSE_CONTAINMENT_RING_KEY}, enemies=(CROOKED_STEWARD_KEY,), tags=("dungeon", "level_19")),
    _room(HOUSE_CONTAINMENT_RING_KEY, "Containment Ring", HOUSE_REGION_KEY, "The deepest chamber is not a prison cell but a circular machine wrapped around an empty chair. Names, voices, and fragments of remembered greetings whisper from the seams. The House was built to hold one impossible guest without ever admitting it had become a host.", {"east": HOUSE_BLACK_BELL_KEY}, enemies=(NAMELESS_GUEST_KEY,), tags=("dungeon", "boss", "level_19_20")),
    _room(HOUSE_BURIED_ROAD_KEY, "The Buried Road", HOUSE_REGION_KEY, "Below the containment ring runs a broad engineered passage large enough for wagons. It predates the surface toll road and was deliberately filled from both ends. Fresh fractures now reveal that it can be reopened as a bypass.", {"up": SPLIT_LANTERN_BRIDGE_KEY, "east": HOUSE_WAKE_GATE_KEY}, tags=("dungeon", "post_event_route", "level_20")),
    _room(HOUSE_WAKE_GATE_KEY, "Wake Gate", HOUSE_REGION_KEY, "A counterweighted stone gate waits beneath Far Watch. Once raised, the buried road would let traffic bypass the hill's most unstable surface cut without passing through the domestic rooms above.", {"west": HOUSE_BURIED_ROAD_KEY, "up": FAR_WATCH_KEY}, tags=("dungeon", "post_event_route", "level_20")),
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


def broken_reach_augmentations() -> dict[str, RoomAugmentation]:
    return {
        WAYMEET_BROKEN_MILE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=OLD_TOLL_ROAD_KEY,
                    name="Thin South Road",
                    travel_text="You leave Waymeet's maintained road and follow the weed-split toll stones into the Broken Reach.",
                    condition=ViewCondition(min_level=10),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        VEYRA_SOUTH_SPRAWL_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=FAR_WATCH_KEY,
                    name="Broken Reach Road",
                    travel_text="Timber streets thin into the northbound road through Far Watch and the Broken Reach.",
                    condition=ViewCondition(min_level=10),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        LEANING_ORCHARD_KEY: RoomAugmentation(
            features=(
                _feature("vanished_wagon", "Abandoned Merchant Wagon", "an overturned wagon whose useful cargo was strangely left behind", "The axle is intact. The lockbox is still sealed. Food, blankets, and tools remain. Deep boot marks leave the road, turn toward the hill, then simply stop beside one carved smiling mark.", ("wagon", "merchant wagon", "abandoned wagon")),
            ),
        ),
        CINDER_FORD_KEY: RoomAugmentation(
            features=(
                _feature("compact_tally", "Cinder Compact Loss Tally", "a waterproof ledger of missing loads and delayed food", "The ledger proves the closed road has costs beyond merchant profit: lamp oil, grain, medicine, replacement tools, and winter cloth are all arriving late or not at all. The Compact's argument for reopening is materially real even if its preferred answer is not automatically right.", ("tally", "ledger", "loss tally")),
            ),
        ),
        SPLIT_LANTERN_BRIDGE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="south",
                    destination_key=FAR_WATCH_KEY,
                    name="Surface Span",
                    condition=ViewCondition(forbidden_flags=(REACH_CHANGED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=HOUSE_BURIED_ROAD_KEY,
                    name="Opened Underroad",
                    travel_text="You descend through the broken bridge abutment into the newly opened buried road.",
                    condition=ViewCondition(required_flags=(REACH_CHANGED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature("split_lanterns", "Split Lantern Line", "a line of road lanterns with every third lamp turned toward the hill", "The misaligned lanterns are deliberate. Their soot patterns show they were turned while lit, one after another, by travelers who left the road. Scratches on the parapet face west toward the House, not east toward the Grinning Camp.", ("lanterns", "lantern line", "split lanterns")),
            ),
            description_layers=(
                DescriptionLayer("reach_span_dropped", "The old surface span is now a deliberate gap of stone and black air. Traffic signs point DOWN through the abutment to the buried road instead.", priority=20, condition=ViewCondition(required_flags=(REACH_CHANGED_FLAG,))),
            ),
        ),
        FAR_WATCH_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="north",
                    destination_key=SPLIT_LANTERN_BRIDGE_KEY,
                    name="Old Surface Span",
                    condition=ViewCondition(forbidden_flags=(REACH_CHANGED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=HOUSE_WAKE_GATE_KEY,
                    name="Wake Gate",
                    travel_text="You descend to the reopened Wake Gate and the controlled under-road beneath the hill.",
                    condition=ViewCondition(required_flags=(CAPSTONE_COMPLETE_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("reach_far_watch_after", "The road north no longer crosses the old bridge. A marked stair descends to Wake Gate, where travelers now pass beneath the dangerous cut instead of beside the House.", priority=20, condition=ViewCondition(required_flags=(CAPSTONE_COMPLETE_FLAG,))),
            ),
        ),
        CARAVANSERAI_KEY: RoomAugmentation(
            description_layers=(
                DescriptionLayer("reach_road_stance", "Your accord has put survey stakes and public patrol timings on the wall. The road faction got its reopening, but only under witnessed rules.", priority=40, condition=ViewCondition(required_flags=(ROAD_STANCE_FLAG,))),
                DescriptionLayer("reach_refuge_stance", "One courtyard is now formally marked as protected refuge. Caravans may use the cistern, but nobody may clear the camp simply to make the map look tidy.", priority=40, condition=ViewCondition(required_flags=(REFUGE_STANCE_FLAG,))),
                DescriptionLayer("reach_quarantine_stance", "A black-and-amber boundary map now defines the hill quarantine precisely instead of letting fear close the whole region.", priority=40, condition=ViewCondition(required_flags=(QUARANTINE_STANCE_FLAG,))),
            ),
        ),
        HOUSE_KEEPER_LOCK_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=HOUSE_UNDERHOUSE_SHAFT_KEY,
                    name="Opened Keeper Shaft",
                    travel_text="With the Warden broken, the locking bars retract just far enough to expose a stair descending below the false house.",
                    condition=ViewCondition(required_flags=(WARDEN_DEFEATED_FLAG,)),
                    hidden_when_unavailable=True,
                ),
            ),
            description_layers=(
                DescriptionLayer("warden_truth", "The fallen Warden's chest is not an armor shell but a lock body. Three broken bars retract into the walls, exposing the maintenance stair it had been physically holding shut.", priority=20, condition=ViewCondition(required_flags=(WARDEN_DEFEATED_FLAG,))),
            ),
        ),
        HOUSE_CONTAINMENT_RING_KEY: RoomAugmentation(
            description_layers=(
                DescriptionLayer("containment_known", "You now understand the ring as containment rather than ritual: every domestic room above was camouflage around a machine built to keep one Guest from becoming everybody's host.", priority=25, condition=ViewCondition(required_flags=(CONTAINMENT_TRUTH_FLAG,))),
                DescriptionLayer("containment_stabilized", "Fresh anchor marks cut across the ring. The worst pressure now bleeds toward the buried road instead of up into the surface bridge.", priority=15, condition=ViewCondition(required_flags=(REACH_CHANGED_FLAG,))),
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


def install_broken_reach_content(world_service=None) -> None:
    for quest in BROKEN_REACH_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in BROKEN_REACH_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in BROKEN_REACH_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for npc in BROKEN_REACH_NPCS:
        _replace_npc(npc)
    for room in BROKEN_REACH_ROOMS:
        _replace_room(room)

    if world_service is None:
        return
    for room in BROKEN_REACH_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in broken_reach_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*BROKEN_REACH_ROOM_KEYS, WAYMEET_BROKEN_MILE_KEY, VEYRA_SOUTH_SPRAWL_KEY):
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


def _in_reach(session) -> bool:
    return bool(session.character and (session.character.current_room or "") in BROKEN_REACH_ROOM_KEYS)


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
    if session.character is None or not _in_reach(session):
        return None
    flags = _flags(session)
    level = session.character.level

    if level >= 11 and FIRST_COMPLETE_FLAG not in flags and _quest(session, FIRST_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, FIRST_QUEST_KEY, "talk_hesta")
        return "New region story: No Smiling Matter. Find Surveyor Hesta Vane at the Ragged Caravanserai."
    if FIRST_COMPLETE_FLAG in flags and level >= 14 and FACTION_COMPLETE_FLAG not in flags and _quest(session, FACTION_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, FACTION_QUEST_KEY, "talk_hesta")
        return "New region story: Three Claims on One Road. Hesta wants a public settlement before the Reach tears itself into private territories."
    if FACTION_COMPLETE_FLAG in flags and level >= 17 and HOUSE_COMPLETE_FLAG not in flags and _quest(session, HOUSE_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, HOUSE_QUEST_KEY, "talk_rook")
        return "New dungeon story: The House Beneath the Hill. Find Rook at the threshold west of Split-Lantern Bridge."
    if HOUSE_COMPLETE_FLAG in flags and level >= 20 and CAPSTONE_COMPLETE_FLAG not in flags and _quest(session, CAPSTONE_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, CAPSTONE_QUEST_KEY, "talk_hesta")
        return "Level-20 region capstone: The Night the Hill Opened. Return to Hesta at the Ragged Caravanserai."
    return None


async def _talk_hesta(session) -> bool:
    if session.character is None or session.character.current_room != CARAVANSERAI_KEY:
        return False
    _ensure_story(session)
    first = _quest(session, FIRST_QUEST_KEY)
    if first and first["status"] == "active":
        step = first["current_step"]
        if step == "talk_hesta":
            session.database.advance_quest(session.character.id, FIRST_QUEST_KEY, "inspect_wagon")
            await session.send("Hesta spreads six disappearance reports over a broken table. 'Everybody wrote GRINNING MEN before they wrote what they actually saw. Start with the wagon in the Leaning Orchard. EXAMINE WAGON. Bring me evidence, not a favorite suspect.'\r\n")
            return True
        if step == "return_hesta":
            session.database.complete_quest(session.character.id, FIRST_QUEST_KEY)
            session.database.grant_flag(session.character.id, FIRST_COMPLETE_FLAG)
            gained = _award(session, 650, SURVEY_RIBBON_KEY)
            await session.send("Hesta crosses out the heading BANDIT ABDUCTIONS and writes ROAD/HILL INCIDENTS. 'Jory's people are guilty of plenty. They are not guilty of making wagons walk toward a hill.'\r\nQuest complete: No Smiling Matter. Reward: 650 XP and Broken Reach Survey Ribbon.\r\n")
            if gained:
                await session.send(f"You gained {gained} level.\r\n")
            follow = _ensure_story(session)
            if follow:
                await session.send(f"{follow}\r\n")
            return True
        await session.send("Hesta taps the current report. 'Finish the evidence in front of you. Then we can change the story people are telling.'\r\n")
        return True

    faction = _quest(session, FACTION_QUEST_KEY)
    if faction and faction["status"] == "active":
        if faction["current_step"] == "talk_hesta":
            session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "talk_jory")
            await session.send("Hesta says, 'My answer is a public road: surveyed, patrolled, and closeable when the hill becomes unstable. Jory thinks that turns his people into a problem to be moved. Hear him before you agree with me.'\r\nNext: TALK JORY.\r\n")
        else:
            await session.send("Hesta says, 'An agreement nobody else helped define is just another private map.'\r\n")
        return True

    capstone = _quest(session, CAPSTONE_QUEST_KEY)
    if capstone and capstone["status"] == "active":
        if capstone["current_step"] == "talk_hesta":
            session.database.advance_quest(session.character.id, CAPSTONE_QUEST_KEY, "set_anchors")
            await session.send("Hesta has stopped pretending the bridge can be saved. 'The House is pushing through the abutment. Rook found an older wagon road beneath the containment ring. Stabilize the ring first: SET ANCHORS. Then we sacrifice the span and reopen the buried route.'\r\n")
        else:
            await session.send("Hesta looks south. 'Do the ugly permanent thing correctly. Temporary cleverness is how this became a crisis.'\r\n")
        return True

    await session.send("Hesta checks the current road board. 'The Reach is quieter than it was. Quiet is maintenance, not victory.'\r\n")
    return True


async def _inspect_wagon(session) -> bool:
    if session.character is None or session.character.current_room != LEANING_ORCHARD_KEY:
        return False
    q = _quest(session, FIRST_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_wagon":
        return False
    session.database.advance_quest(session.character.id, FIRST_QUEST_KEY, "talk_jory")
    await session.send("The wagon was not looted. Food, blankets, tools, and the sealed lockbox remain. Boot marks leave the road toward the hill and stop beside a carved smile. The smile was added after the wagon fell: warning mark, not claim mark. Find the Grinning Camp and TALK JORY.\r\n")
    return True


async def _talk_jory(session) -> bool:
    if session.character is None or session.character.current_room != GRINNING_CAMP_KEY:
        return False
    first = _quest(session, FIRST_QUEST_KEY)
    if first and first["status"] == "active" and first["current_step"] == "talk_jory":
        session.database.advance_quest(session.character.id, FIRST_QUEST_KEY, "inspect_lanterns")
        await session.send("Jory lowers his mask. 'We diverted three caravans. Robbed one. Saved two. The fourth driver heard his dead sister calling from the hill and walked off before we reached him.' He points south. 'Look at the lanterns on the bridge. They turn themselves only after somebody starts listening.'\r\nNext: EXAMINE LANTERNS at Split-Lantern Bridge.\r\n")
        return True
    faction = _quest(session, FACTION_QUEST_KEY)
    if faction and faction["status"] == "active" and faction["current_step"] == "talk_jory":
        session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "talk_mira")
        await session.send("Jory gestures across the tents. 'Hesta draws this as a road problem. We live here because respectable places pushed us out before the hill ever did. Reopen what you want. Just do not erase a refuge to make survey lines straight.'\r\nNext: TALK VESSA at Cinder Ford.\r\n")
        return True
    await session.send("Jory taps the smile carved into his mask. 'People remember the grin. Good. Maybe they remember there was a warning attached to it.'\r\n")
    return True


async def _inspect_lanterns(session) -> bool:
    if session.character is None or session.character.current_room != SPLIT_LANTERN_BRIDGE_KEY:
        return False
    q = _quest(session, FIRST_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_lanterns":
        return False
    session.database.advance_quest(session.character.id, FIRST_QUEST_KEY, "return_hesta")
    await session.send("Every third lantern was turned while burning. Soot trails across the brackets in the same direction: west, toward the hill-door. Several parapet scratches are fingernail-deep. Nothing points east toward the Grinning Camp. Return to Hesta with what you found.\r\n")
    return True


async def _talk_mira(session) -> bool:
    if session.character is None or session.character.current_room != CINDER_FORD_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_mira":
        session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "inspect_tally")
        await session.send("Vessa unties the red cord around her ledger. 'I am not asking you to love trade. I am asking you to look at what does not arrive when the road stays closed.' She turns the book toward you. EXAMINE TALLY.\r\n")
        return True
    await session.send("Vessa says, 'If a route cannot be closed safely, it was never safely open.'\r\n")
    return True


async def _inspect_tally(session) -> bool:
    if session.character is None or session.character.current_room != CINDER_FORD_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_tally":
        return False
    session.database.advance_quest(session.character.id, FACTION_QUEST_KEY, "choose_stance")
    await session.send("The losses are not luxury cargo. Grain, lamp oil, medicine, iron fittings, winter cloth, and replacement tools all sit in the delayed column. The Compact has self-interest, but the road's closure is hurting people who never signed a trade contract. Return to the Ragged Caravanserai and choose the rule that leads: CHOOSE ROAD, CHOOSE REFUGE, or CHOOSE QUARANTINE.\r\n")
    return True


async def _choose_stance(session, stance: str) -> bool:
    if session.character is None or session.character.current_room != CARAVANSERAI_KEY:
        return False
    q = _quest(session, FACTION_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "choose_stance":
        return False
    mapping = {
        "road": (ROAD_STANCE_FLAG, "You put reopening the public road first, but bind it to patrol schedules, closure rules, and public reporting."),
        "refuge": (REFUGE_STANCE_FLAG, "You protect the Grinning settlement first, forcing future road plans to route around a legally recognized refuge instead of clearing it."),
        "quarantine": (QUARANTINE_STANCE_FLAG, "You define a narrow quarantine around the hill itself, reopening the rest of the Reach while forbidding vague fear from closing everything."),
    }
    chosen = mapping.get(stance)
    if chosen is None:
        return False
    flag, text = chosen
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, FACTION_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, FACTION_QUEST_KEY)
    gained = _award(session, 950, ACCORD_TOKEN_KEY)
    await session.send(f"{text}\r\nHesta, Jory, and Vessa each sign the same temporary map without pretending they wanted the same outcome. Quest complete: Three Claims on One Road. Reward: 950 XP and Three-Claims Accord Token.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    follow = _ensure_story(session)
    if follow:
        await session.send(f"{follow}\r\n")
    return True


async def _talk_rook(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_THRESHOLD_KEY:
        return False
    _ensure_story(session)
    q = _quest(session, HOUSE_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "talk_rook":
        session.database.advance_quest(session.character.id, HOUSE_QUEST_KEY, "read_guestbook")
        await session.send("Rook says, 'The rooms above want you to think this is a house. Do not let familiar furniture make the machinery friendly. Start with the guestbook. READ GUESTBOOK in the Stone Parlour, and do not answer if it greets you first.'\r\n")
        return True
    await session.send("Rook keeps one hand on the hill-door. 'A threshold is useful because it admits you can still choose a side.'\r\n")
    return True


async def _read_guestbook(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_PARLOUR_KEY:
        return False
    q = _quest(session, HOUSE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "read_guestbook":
        return False
    session.database.advance_quest(session.character.id, HOUSE_QUEST_KEY, "examine_hearth")
    await session.send("The guestbook is older than the road, but the newest page contains names from this season's missing-person notices in fresh-looking ink. None are signatures. Each name is written in the same hand beneath the phrase EXPECTED GUEST. The House is recording people before they arrive. Go deeper and EXAMINE HEARTH.\r\n")
    return True


async def _examine_hearth(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_DEEP_HEARTH_KEY:
        return False
    q = _quest(session, HOUSE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "examine_hearth":
        return False
    session.database.advance_quest(session.character.id, HOUSE_QUEST_KEY, "defeat_warden")
    await session.send("The chimney draws downward. Soot, warmth, and faint whispers are being pulled into the foundation, not vented away. Three black bars run west from the hearth into the Warden's chamber. Whatever the Warden is doing, it is part of the House's deepest mechanism. Defeat it only if you are ready to find out what the lock is holding.\r\n")
    return True


async def _inspect_lock(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_KEEPER_LOCK_KEY:
        return False
    q = _quest(session, HOUSE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "inspect_lock":
        return False
    session.database.grant_flag(session.character.id, CONTAINMENT_TRUTH_FLAG)
    session.database.advance_quest(session.character.id, HOUSE_QUEST_KEY, "listen_bell")
    await session.send("Broken open, the Warden's torso reveals no pilot chamber and no treasure. It is a lock body. The three bars through its ribs held tension across the whole hill. You did not defeat the thing imprisoning the House. You defeated part of what was containing it. A stair opens DOWN. Find the Black Bell Chamber and LISTEN BELL.\r\n")
    return True


async def _listen_bell(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_BLACK_BELL_KEY:
        return False
    q = _quest(session, HOUSE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "listen_bell":
        return False
    session.database.advance_quest(session.character.id, HOUSE_QUEST_KEY, "confront_guest")
    await session.send("You stand still. The clapperless bell sounds once without moving. Instead of noise, you feel a remembered welcome spoken in the voice of someone you trust. Then another. Then your own voice says, 'Come in.' The west door opens onto the Containment Ring. The Warden was keeping a Guest from learning enough voices to leave.\r\n")
    return True


async def _set_anchors(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_CONTAINMENT_RING_KEY:
        return False
    q = _quest(session, CAPSTONE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "set_anchors":
        return False
    session.database.advance_quest(session.character.id, CAPSTONE_QUEST_KEY, "drop_span")
    await session.send("You reset the three surviving anchor lines to bleed pressure away from the domestic rooms and toward the buried wagon passage. The ring stops climbing toward the surface. It cannot stabilize while the cracked bridge abutment still carries the old route. Return to Split-Lantern Bridge and DROP SPAN.\r\n")
    return True


async def _drop_span(session) -> bool:
    if session.character is None or session.character.current_room != SPLIT_LANTERN_BRIDGE_KEY:
        return False
    q = _quest(session, CAPSTONE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "drop_span":
        return False
    session.database.grant_flag(session.character.id, REACH_CHANGED_FLAG)
    session.database.advance_quest(session.character.id, CAPSTONE_QUEST_KEY, "open_bypass")
    await session.send("You pull the marked release pins. The old surface span does not explode; it folds downward in three deliberate failures, taking the unstable abutment with it. The road you used is gone. Beneath the broken stone, an older engineered passage is visible. A new exit opens DOWN into the Buried Road. Follow it to Wake Gate and OPEN BYPASS.\r\n")
    return True


async def _open_bypass(session) -> bool:
    if session.character is None or session.character.current_room != HOUSE_WAKE_GATE_KEY:
        return False
    q = _quest(session, CAPSTONE_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "open_bypass":
        return False
    session.database.complete_quest(session.character.id, CAPSTONE_QUEST_KEY)
    session.database.grant_flag(session.character.id, CAPSTONE_COMPLETE_FLAG)
    gained = _award(session, 2200, UNDERROAD_WRIT_KEY)
    await session.send("The counterweights groan upward and daylight reaches the buried road from Far Watch. By dusk, Hesta's signs send traffic down through Wake Gate instead of across the sacrificed span. Jory's camp remains protected. Vessa's freight can move. The House is now a watched hazard instead of a rumor people stumble into.\r\nRegion capstone complete: The Night the Hill Opened. Reward: 2200 XP and Underroad Writ. The Broken Reach map has permanently changed for this character.\r\n")
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
    gained = _award(session, 75, item_key)
    await session.send(f"{text}\r\nDiscovery recorded: +75 XP.\r\n")
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


def install_broken_reach_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_broken_reach_midgame_installed", False):
        return
    install_broken_reach_content(world_service)

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
        message = _ensure_story(self)
        if message:
            await self.send(f"\r\n{message}\r\n")

    async def _finish_enemy_defeat(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish_enemy(self, enemy)
        if not eligible or self.character is None:
            return
        q = _quest(self, HOUSE_QUEST_KEY)
        if key == HILL_WARDEN_KEY and q and q["status"] == "active" and q["current_step"] == "defeat_warden":
            self.database.grant_flag(self.character.id, WARDEN_DEFEATED_FLAG)
            self.database.advance_quest(self.character.id, HOUSE_QUEST_KEY, "inspect_lock")
            await self.send("The Hill Warden crashes backward. The three bars through its torso go slack, and somewhere below you a bell rings once. Do not leave yet: EXAMINE LOCK.\r\n")
        elif key == NAMELESS_GUEST_KEY and q and q["status"] == "active" and q["current_step"] == "confront_guest":
            self.database.complete_quest(self.character.id, HOUSE_QUEST_KEY)
            self.database.grant_flag(self.character.id, HOUSE_COMPLETE_FLAG)
            gained = _award(self, 1700, BENT_HOST_KEY)
            await self.send("The Guest does not die. It collapses inward, shedding borrowed voices until the empty chair at the center of the ring is empty again. The damaged ring holds—for now.\r\nQuest complete: The House Beneath the Hill. Reward: 1700 XP and Bent Host Key.\r\n")
            if gained:
                await self.send(f"You gained {gained} level.\r\n")
            follow = _ensure_story(self)
            if follow:
                await self.send(f"{follow}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = _normalize(command)

        if normalized in {"talk hesta", "talk to hesta", "talk surveyor", "talk to surveyor"} and await _talk_hesta(self):
            return
        if normalized in {"talk jory", "talk to jory", "talk ninegrin", "talk to ninegrin"} and await _talk_jory(self):
            return
        if normalized in {"talk vessa", "talk mira", "talk to vessa", "talk to mira", "talk factor", "talk to factor"} and await _talk_mira(self):
            return
        if normalized in {"talk rook", "talk to rook", "talk threshold warden"} and await _talk_rook(self):
            return
        if normalized in {"examine wagon", "look wagon", "inspect wagon"} and await _inspect_wagon(self):
            return
        if normalized in {"examine lanterns", "look lanterns", "inspect lanterns", "examine split lanterns"} and await _inspect_lanterns(self):
            return
        if normalized in {"examine tally", "read tally", "inspect tally", "read ledger"} and await _inspect_tally(self):
            return
        if normalized.startswith("choose "):
            stance = normalized.split(maxsplit=1)[1]
            if stance in {"road", "refuge", "quarantine"} and await _choose_stance(self, stance):
                return
        if normalized in {"read guestbook", "examine guestbook", "look guestbook"} and await _read_guestbook(self):
            return
        if normalized in {"examine hearth", "inspect hearth", "look hearth"} and await _examine_hearth(self):
            return
        if normalized in {"examine lock", "inspect lock", "look lock"} and await _inspect_lock(self):
            return
        if normalized in {"listen bell", "listen to bell", "listen black bell"} and await _listen_bell(self):
            return
        if normalized in {"set anchors", "reset anchors", "align anchors"} and await _set_anchors(self):
            return
        if normalized in {"drop span", "drop bridge", "release span"} and await _drop_span(self):
            return
        if normalized in {"open bypass", "open gate", "raise gate"} and await _open_bypass(self):
            return

        if self.character.current_room == SLEEPING_TOLLHOUSE_KEY and normalized in {"read tollbook", "read ledger", "examine ledger"}:
            await _discover_oddity(self, ODDITY_TOLLBOOK_FLAG, "The tollbook records the same bent copper coin twice, eighty years apart, with the same tiny nick beside the date. You find the coin still wedged beneath the chained desk.", item_key=BENT_TOLL_COIN_KEY)
            return
        if self.character.current_room == ECHO_WELL_KEY and normalized in {"listen well", "listen to well", "ask well"}:
            await _discover_oddity(self, ODDITY_WELL_FLAG, "You speak toward the water. No echo returns. Several breaths later, a voice at water level quietly repeats only the final word you said, using a voice that is not yours.")
            return
        if self.character.current_room == CROW_COURT_KEY and normalized in {"wait", "wait crows", "watch crows"}:
            await _discover_oddity(self, ODDITY_CROWS_FLAG, "You stand in the clean center. The crows rotate around you one perch at a time until every bird faces west toward the hill. Then they resume arguing as if nothing happened.")
            return
        if self.character.current_room == HOUSE_NINE_BOOTS_KEY and normalized in {"count boots", "examine boots", "look boots"}:
            await _discover_oddity(self, ODDITY_BOOTS_FLAG, "You count nine boots. When you count again there are ten, and the newest one matches the kind you are wearing. Looking down confirms both of yours are still on your feet. On the third count there are nine again.")
            return

        if normalized in {"broken reach", "reach", "reach help"} and _in_reach(self):
            flags = _flags(self)
            completed = sum(flag in flags for flag in (FIRST_COMPLETE_FLAG, FACTION_COMPLETE_FLAG, HOUSE_COMPLETE_FLAG, CAPSTONE_COMPLETE_FLAG))
            oddities = sum(flag in flags for flag in ODDITY_FLAGS)
            await self.send(
                f"Broken Reach: {completed}/4 major stories completed; {oddities}/4 recorded oddities found.\r\n"
                "Levels 11-13 investigate the vanishings. Levels 14-16 settle the three competing claims. Levels 17-19 descend through the House Beneath the Hill. Level 20 changes the route through the region. Optional rooms are deliberately not required by any quest.\r\n"
            )
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._broken_reach_midgame_installed = True
