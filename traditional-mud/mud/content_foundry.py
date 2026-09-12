from __future__ import annotations

import random
from dataclasses import dataclass

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.style_collectibles as style
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.greywake_march import GREYWAKE_RESONANT_ORCHARD_KEY
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.sablewater_reach import DROWNED_BRASS_SCRAP_KEY, SABLEWATER_SALTGRASS_BEND_KEY
from mud.stats import CharacterStats, EquipmentItem
from mud.veyra_city import VEYRA_BRASSMARKET_KEY, VEYRA_CARAVAN_COURT_KEY, VEYRA_RESIDENT_FLAG, VEYRA_SCHOLARS_RISE_KEY
from mud.waymeet_frontier import WAYMEET_BROKEN_MILE_KEY, WAYMEET_SCRIP_KEY
from mud.world import RoomDefinition


@dataclass(frozen=True, slots=True)
class LootIdentity:
    region_key: str
    signature_materials: tuple[str, ...]
    recipe_family: str
    style_language: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DungeonTemplate:
    key: str
    name: str
    region_key: str
    level_band: tuple[int, int]
    entrance_room_key: str
    room_keys: tuple[str, ...]
    boss_key: str
    reliable_material_key: str
    rare_style_key: str
    hook: str


CONTENT_PIPELINE_RULES = (
    "Every dungeon teaches one readable mechanic before the boss asks for it.",
    "Every boss has a reliable material drop plus a very rare style trophy.",
    "Every region owns a recognizable material/style identity instead of random global loot.",
    "At least one recipe in each wave crosses regional material boundaries so trade stays useful.",
    "World oddities are condition-driven discoveries, not scheduled login chores.",
)

GLASS_REGION = "glass_orchard_underbough"
GLASS_GATE = "glass_orchard_shattered_gate"
GLASS_PEAR_ROWS = "glass_orchard_pear_rows"
GLASS_TRENCH = "glass_orchard_irrigation_trench"
GLASS_GLASSHOUSE = "glass_orchard_broken_glasshouse"
GLASS_COCOON = "glass_orchard_cocoon_arcade"
GLASS_ROOT_CELLAR = "glass_orchard_root_cellar"
GLASS_NAVE = "glass_orchard_widow_nave"
GLASS_LOFT = "glass_orchard_pruning_loft"
GLASS_ROOM_KEYS = (GLASS_GATE, GLASS_PEAR_ROWS, GLASS_TRENCH, GLASS_GLASSHOUSE, GLASS_COCOON, GLASS_ROOT_CELLAR, GLASS_NAVE, GLASS_LOFT)

ASH_REGION = "ash_driver_relay"
ASH_ENTRY = "ash_driver_relay_entry"
ASH_YARD = "ash_driver_ash_yard"
ASH_BAYS = "ash_driver_coach_bays"
ASH_HALL = "ash_driver_passenger_hall"
ASH_CAGE = "ash_driver_fare_cage"
ASH_PIT = "ash_driver_axle_pit"
ASH_PLATFORM = "ash_driver_black_platform"
ASH_TURNTABLE = "ash_driver_turntable"
ASH_ROOM_KEYS = (ASH_ENTRY, ASH_YARD, ASH_BAYS, ASH_HALL, ASH_CAGE, ASH_PIT, ASH_PLATFORM, ASH_TURNTABLE)

VAPOR_REGION = "house_of_nine_vapors"
VAPOR_ENTRY = "nine_vapors_scent_cellar"
VAPOR_GREEN = "nine_vapors_green_room"
VAPOR_AMBER = "nine_vapors_amber_room"
VAPOR_SILVER = "nine_vapors_silver_room"
VAPOR_HALL = "nine_vapors_distillation_hall"
VAPOR_VAULT = "nine_vapors_bottle_vault"
VAPOR_GALLERY = "nine_vapors_mask_gallery"
VAPOR_CHAMBER = "nine_vapors_final_chamber"
VAPOR_ROOM_KEYS = (VAPOR_ENTRY, VAPOR_GREEN, VAPOR_AMBER, VAPOR_SILVER, VAPOR_HALL, VAPOR_VAULT, VAPOR_GALLERY, VAPOR_CHAMBER)

GLASSFRUIT_SHARD = "glassfruit_shard"
WIDOW_SILK = "widow_silk_bundle"
ASHWHEEL_SPOKE = "ashwheel_spoke"
CINDER_TICKET = "cinder_ticket_scrap"
NINTH_VAPOR_RESIN = "ninth_vapor_resin"
PERFUMER_SILVER_SALT = "perfumer_silver_salt"
SILVERHART_ANTLER = "silverhart_antler"
RAINTHREAD_SCALE = "rainthread_scale"
MOONWORK_TOKEN = "moonwork_token"
EARTH_LIGHTER = "dead_earth_lighter"

WIDOWGLASS_KNIFE = "widowglass_knife"
ASHWHEEL_BOOTS = "ashwheel_road_boots"
VAPORWARD_MASK = "vaporward_mask"
ROADGLASS_HALFCOAT = "style_roadglass_halfcoat"
AFTERIMAGE_NO9 = "fragrance_afterimage_no9"

STYLE_WIDOW_VEIL = "style_orchard_widow_veil"
STYLE_DRIVER_COAT = "style_ash_driver_coat"
STYLE_NINE_VAPOR_BROOCH = "style_ninth_vapor_brooch"

GLASS_DRONE = "glass_orchard_drone"
ORCHARD_HUSK = "glass_orchard_husk"
SILK_TENDER = "glass_orchard_silk_tender"
ORCHARD_WIDOW = "glass_orchard_widow"
ASH_HOUND = "ash_driver_hound"
CHARRED_PORTER = "ash_driver_porter"
TICKET_WIGHT = "ash_driver_ticket_wight"
ASH_DRIVER = "ash_driver_boss"
SCENTBOUND_ATTENDANT = "nine_vapors_attendant"
VAPOR_SLIME = "nine_vapors_slime"
GLASS_WASP = "nine_vapors_glass_wasp"
PALE_DISTILLER = "nine_vapors_pale_distiller"
SILVERHART = "rare_silverhart"
RAINTHREAD_SERPENT = "rare_rainthread_serpent"

ITEMS = (
    ItemDefinition(GLASSFRUIT_SHARD, "Glassfruit Shard", "A translucent wedge from a fruit that grew hard as bottle glass while still hanging from a living branch. It rings faintly when tapped against metal.", "material", tier=2),
    ItemDefinition(WIDOW_SILK, "Widow-Silk Bundle", "A bundle of pale orchard silk, stronger than ordinary thread and faintly reflective in low light.", "material", tier=2),
    ItemDefinition(ASHWHEEL_SPOKE, "Ashwheel Spoke", "A blackened coach-wheel spoke reinforced with old road iron. It smells of soot no matter how often it is washed.", "material", tier=3),
    ItemDefinition(CINDER_TICKET, "Cinder Ticket Scrap", "A punched strip of heat-darkened brass bearing half of a route number that no modern road office recognizes.", "material", tier=3),
    ItemDefinition(NINTH_VAPOR_RESIN, "Ninth-Vapor Resin", "A dark aromatic resin that seems to change character between first smell and second breath.", "material", tier=3),
    ItemDefinition(PERFUMER_SILVER_SALT, "Perfumer's Silver Salt", "Fine silver-gray crystals used to fix volatile scent accords so they linger on cloth and skin.", "material", tier=3),
    ItemDefinition(SILVERHART_ANTLER, "Silverhart Antler", "A moon-pale antler whose growth rings show only under full moonlight.", "material", tier=3),
    ItemDefinition(RAINTHREAD_SCALE, "Rainthread Scale", "A translucent wetland scale that sheds water almost instantly.", "material", tier=3),
    ItemDefinition(MOONWORK_TOKEN, "Clockwork Moon Token", "A tiny silver disk released from an old mechanical moon. Its geared edge advances one notch when the real moon reaches fullness.", "trophy", tier=3),
    ItemDefinition(EARTH_LIGHTER, "Dead Earth Lighter", "A scratched metal lighter from Humanity's lost Earth. The wheel still turns and the lid still clicks, but nobody in Astralis knows what fuel once made it burn.", "trophy", tier=4),
    ItemDefinition(WIDOWGLASS_KNIFE, "Widowglass Knife", "A narrow black-iron knife set with a ringing Glassfruit edge.", "equipment", equipment=EquipmentItem("Widowglass Knife", "main_hand", stat_bonuses=CharacterStats(might=2, grace=1)), tier=2),
    ItemDefinition(ASHWHEEL_BOOTS, "Ashwheel Road Boots", "Heavy road boots with spring-steel heel plates cut from an old relay spoke.", "equipment", equipment=EquipmentItem("Ashwheel Road Boots", "feet", armor_class=2, stat_bonuses=CharacterStats(grace=1, hp=1)), tier=3),
    ItemDefinition(VAPORWARD_MASK, "Vaporward Mask", "A half-mask of silvered cloth and perforated brass made for unstable perfumes and fumes.", "equipment", equipment=EquipmentItem("Vaporward Mask", "head", armor_class=1, stat_bonuses=CharacterStats(mind=2, love=1)), tier=3),
    ItemDefinition(ROADGLASS_HALFCOAT, "Roadglass Half-Coat", "A sharply cut traveling half-coat with widow-silk lining and a single clear glassfruit bead at the throat.", "fashion", tier=3),
    ItemDefinition(AFTERIMAGE_NO9, "Afterimage No. 9", "A low rectangular bottle of gray-green glass. The first spray smells mineral and cool; ten seconds later it turns quietly floral.", "fragrance", tier=3),
    ItemDefinition(STYLE_WIDOW_VEIL, "Orchard Widow Veil", "A smoke-clear face veil threaded with pale orchard silk and tiny glass beads.", "fashion", tier=4),
    ItemDefinition(STYLE_DRIVER_COAT, "Ash Driver's Farecoat", "A long coal-black driving coat with one brass ticket punch chained inside the breast.", "fashion", tier=4),
    ItemDefinition(STYLE_NINE_VAPOR_BROOCH, "Ninth Vapor Brooch", "A tiny silver scent fan with nine articulated leaves.", "fashion", tier=4),
)

RECIPES = (
    CraftingRecipe("forge_widowglass_knife", "blacksmithing", WIDOWGLASS_KNIFE, 18, 45, (MaterialRequirement(GLASSFRUIT_SHARD, 2), MaterialRequirement("blackreed_iron_fitting", 1), MaterialRequirement("iron_ingot", 1)), station_key="forge", description="A Greywake shard becomes useful only after Blackreed iron gives it a spine.", design_status="content_wave_one"),
    CraftingRecipe("forge_ashwheel_boots", "blacksmithing", ASHWHEEL_BOOTS, 28, 55, (MaterialRequirement(ASHWHEEL_SPOKE, 1), MaterialRequirement("rough_hide", 2), MaterialRequirement("steel_ingot", 1)), station_key="forge", description="Rebuild old relay springwork into durable road footwear.", design_status="content_wave_one"),
    CraftingRecipe("tailor_vaporward_mask", "tailoring", VAPORWARD_MASK, 32, 60, (MaterialRequirement(NINTH_VAPOR_RESIN, 1), MaterialRequirement(WIDOW_SILK, 1), MaterialRequirement(DROWNED_BRASS_SCRAP_KEY, 1)), station_key="loom", description="Combine perfume-house filtration cloth, orchard silk, and reclaimed Tollhouse brass.", design_status="content_wave_one"),
    CraftingRecipe("tailor_roadglass_halfcoat", "tailoring", ROADGLASS_HALFCOAT, 26, 55, (MaterialRequirement(WIDOW_SILK, 2), MaterialRequirement(CINDER_TICKET, 1), MaterialRequirement("cotton_cloth", 1)), station_key="loom", description="A fashion piece built from two dungeon identities instead of one self-contained drop table.", design_status="content_wave_one"),
    CraftingRecipe("blend_afterimage_no9", "alchemy", AFTERIMAGE_NO9, 30, 60, (MaterialRequirement(NINTH_VAPOR_RESIN, 1), MaterialRequirement(GLASSFRUIT_SHARD, 1), MaterialRequirement("lavender_blossom", 2)), station_key="alchemy_table", description="Fix Ninth-Vapor resin with ringing glassfruit mineral and lavender.", design_status="content_wave_one"),
)

STYLE_META = (
    style.StyleMetadata(ROADGLASS_HALFCOAT, "rare", "chest", ("travel", "glass", "tailored", "cross-region"), "Nine Bridges Road Atelier", "Roadglass", "Crafted from Glass Orchard and Ash Driver materials", 0),
    style.StyleMetadata(STYLE_WIDOW_VEIL, "epic", "face", ("orchard", "silk", "glass", "boss"), "Unattributed", "Dungeon Oddities", "Very rare Orchard Widow trophy", 0, provenance_track=True),
    style.StyleMetadata(STYLE_DRIVER_COAT, "epic", "chest", ("road", "coal", "brass", "boss"), "Old Relay Cutters", "Dungeon Oddities", "Very rare Ash Driver trophy", 0, provenance_track=True),
    style.StyleMetadata(STYLE_NINE_VAPOR_BROOCH, "epic", "accessory", ("perfume", "silver", "boss"), "House of Nine Vapors", "Dungeon Oddities", "Very rare Pale Distiller trophy", 0, provenance_track=True),
)
AFTERIMAGE_FRAGRANCE = style.FragranceDefinition(AFTERIMAGE_NO9, "House of Nine Vapors", "rare", ("wet slate", "violet leaf", "cool resin"), "low gray-green bottle", 3600, 10, 0)

GLASS_DRONE_DEF = EnemyDefinition(GLASS_DRONE, "Glassback Orchard Drone", ("drone", "glassback", "orchard drone"), "a low six-legged orchard scavenger with clear mineral plates growing through its hide", 92, 9, 8, 2.9, 64)
ORCHARD_HUSK_DEF = EnemyDefinition(ORCHARD_HUSK, "Orchard Husk", ("husk", "orchard husk"), "a dead pruning worker pulled upright by silk around the joints rather than visible necromancy", 108, 10, 9, 3.1, 72)
SILK_TENDER_DEF = EnemyDefinition(SILK_TENDER, "Silk-Tender", ("tender", "silk tender", "silk-tender"), "a long-limbed pale arachnid that wraps branches and living things with the same care", 124, 12, 10, 3.0, 84)
ORCHARD_WIDOW_DEF = EnemyDefinition(ORCHARD_WIDOW, "The Orchard Widow", ("widow", "orchard widow", "the orchard widow"), "a massive orchard spider draped in translucent fruit-silk, three hard glass fruits hanging from the web above her like bells", 285, 16, 15, 2.8, 240)
ASH_HOUND_DEF = EnemyDefinition(ASH_HOUND, "Relay Ash Hound", ("hound", "ash hound", "relay hound"), "a rangy black dog with cinder-gray paws and an old brass route tag wired to its collar", 108, 10, 9, 2.7, 75)
CHARRED_PORTER_DEF = EnemyDefinition(CHARRED_PORTER, "Charred Porter", ("porter", "charred porter"), "an old relay porter in a burned coat, still lifting invisible luggage", 126, 12, 11, 3.0, 90)
TICKET_WIGHT_DEF = EnemyDefinition(TICKET_WIGHT, "Ticket Wight", ("ticket wight", "clerk", "wight"), "a dead fare clerk with a punch in one hand and brass tickets in the other", 138, 13, 12, 3.0, 98)
ASH_DRIVER_DEF = EnemyDefinition(ASH_DRIVER, "The Ash Driver", ("driver", "ash driver", "the ash driver"), "a tall coachman burned black around the edges of his coat, one gloved hand permanently extended for a fare", 330, 18, 16, 2.8, 300)
SCENTBOUND_DEF = EnemyDefinition(SCENTBOUND_ATTENDANT, "Scentbound Attendant", ("attendant", "scentbound"), "a masked attendant moving through old service motions with perfume-soaked sleeves", 118, 11, 10, 3.0, 82)
VAPOR_SLIME_DEF = EnemyDefinition(VAPOR_SLIME, "Vapor Slime", ("slime", "vapor slime"), "a glossy alchemical spill that leaves three different smells behind it", 105, 8, 9, 3.2, 74)
GLASS_WASP_DEF = EnemyDefinition(GLASS_WASP, "Bottle-Glass Wasp", ("wasp", "glass wasp", "bottle wasp"), "a hand-sized wasp with a translucent vial-like abdomen", 96, 13, 9, 2.5, 76)
PALE_DISTILLER_DEF = EnemyDefinition(PALE_DISTILLER, "The Pale Distiller", ("distiller", "pale distiller", "the pale distiller"), "a porcelain-faced distillation automaton on narrow brass legs, nine scent pipes opening and closing behind its shoulders", 350, 18, 17, 2.9, 320)
SILVERHART_DEF = EnemyDefinition(SILVERHART, "Full-Moon Silverhart", ("silverhart", "hart", "moon stag"), "a tall pale stag whose antlers seem to hold more moonlight than the sky around them", 210, 15, 13, 2.8, 155)
RAINTHREAD_DEF = EnemyDefinition(RAINTHREAD_SERPENT, "Rainthread Serpent", ("rainthread", "serpent", "rain serpent"), "a translucent marsh serpent almost invisible except where rain beads along its spine", 196, 14, 13, 2.7, 150)
ENEMIES = (GLASS_DRONE_DEF, ORCHARD_HUSK_DEF, SILK_TENDER_DEF, ORCHARD_WIDOW_DEF, ASH_HOUND_DEF, CHARRED_PORTER_DEF, TICKET_WIGHT_DEF, ASH_DRIVER_DEF, SCENTBOUND_DEF, VAPOR_SLIME_DEF, GLASS_WASP_DEF, PALE_DISTILLER_DEF, SILVERHART_DEF, RAINTHREAD_DEF)


def _room(key, name, region, description, exits, enemies=(), tags=()):
    return RoomDefinition(key=key, name=name, region_key=region, description=description, exits=exits, enemy_keys=enemies, tags=("shared_world", "dungeon", "content_wave_one", *tags))

GLASS_ROOMS = (
    _room(GLASS_GATE, "Shattered Orchard Gate", GLASS_REGION, "The Resonant Orchard continues through a wrought gate pushed inward by roots. Beyond it, living pear trees carry fruit gone clear and hard as glass. Pale silk crosses the path like a warning nobody wrote down.", {"west": GREYWAKE_RESONANT_ORCHARD_KEY, "east": GLASS_PEAR_ROWS}, (GLASS_DRONE,), ("level_5_7", "entry")),
    _room(GLASS_PEAR_ROWS, "Glass Pear Rows", GLASS_REGION, "Rows of old orchard trees stand too straight, every third branch stitched to the next by pale silk. Red glassfruit hangs on the north row.", {"west": GLASS_GATE, "east": GLASS_TRENCH, "north": GLASS_GLASSHOUSE}, (ORCHARD_HUSK,), ("level_5_7",)),
    _room(GLASS_TRENCH, "Irrigation Trench", GLASS_REGION, "A dry stone irrigation trench divides the orchard. Blue glassfruit has grown around one old sluice wheel, turning it into a brittle blue crown.", {"west": GLASS_PEAR_ROWS, "east": GLASS_COCOON}, (GLASS_DRONE,), ("level_5_7",)),
    _room(GLASS_GLASSHOUSE, "Broken Glasshouse", GLASS_REGION, "Most panes are gone, but the surviving roof feeds one impossible clear-fruited tree. Silk-Tenders have webbed broken frames into usable architecture.", {"south": GLASS_PEAR_ROWS, "east": GLASS_ROOT_CELLAR}, (SILK_TENDER,), ("level_5_7", "side_room")),
    _room(GLASS_COCOON, "Cocoon Arcade", GLASS_REGION, "Tree arches form a low tunnel wrapped in old cocoons. Some contain tools. Some contain animal bones. One contains an intact pruning ladder, which somehow makes the rest worse.", {"west": GLASS_TRENCH, "east": GLASS_NAVE}, (SILK_TENDER,), ("level_5_7",)),
    _room(GLASS_ROOT_CELLAR, "Root Cellar", GLASS_REGION, "The cellar is full of grafting knives, clay labels, and one ledger whose final pages simply repeat: fruit rang again tonight.", {"west": GLASS_GLASSHOUSE, "south": GLASS_NAVE}, (ORCHARD_HUSK,), ("level_5_7", "side_room")),
    _room(GLASS_NAVE, "Widow's Nave", GLASS_REGION, "Old pear trees curve overhead like ribs. Three enormous fruits—red, blue, and clear—hang in silk above a central nest. The web tightens every time the fruit moves.", {"west": GLASS_COCOON, "north": GLASS_ROOT_CELLAR, "east": GLASS_LOFT}, (), ("level_5_7", "boss")),
    _room(GLASS_LOFT, "Pruning Loft", GLASS_REGION, "A narrow maintenance loft overlooks the orchard canopy. The ordinary Greywake road is visible through roof slats, almost offensively normal.", {"west": GLASS_NAVE}, (), ("level_5_7", "reward_room")),
)
ASH_ROOMS = (
    _room(ASH_ENTRY, "Abandoned Relay", ASH_REGION, "A disused coach relay crouches below Veyra's caravan road. Its sign has burned away except for one word stamped deep enough to survive: FARE.", {"north": VEYRA_CARAVAN_COURT_KEY, "south": ASH_YARD}, (ASH_HOUND,), ("level_7_9", "entry")),
    _room(ASH_YARD, "Ash Yard", ASH_REGION, "Coach ruts cross a yard permanently gray with fine ash. Nothing here is hot. Footprints appear anyway, beginning at the gate and ending at empty coach bays.", {"north": ASH_ENTRY, "east": ASH_BAYS, "south": ASH_HALL}, (ASH_HOUND,), ("level_7_9",)),
    _room(ASH_BAYS, "Coach Bays", ASH_REGION, "Three roofed bays hold iron skeletons of passenger coaches. Their wheels are missing one spoke each, all removed from exactly the same position.", {"west": ASH_YARD, "south": ASH_PIT}, (CHARRED_PORTER,), ("level_7_9", "side_room")),
    _room(ASH_HALL, "Passenger Hall", ASH_REGION, "Long benches face a ticket window. A brass bell is polished bright by hands that have been dead for decades. The timetable lists departures every hour and no destinations at all.", {"north": ASH_YARD, "east": ASH_CAGE, "south": ASH_PLATFORM}, (TICKET_WIGHT,), ("level_7_9",)),
    _room(ASH_CAGE, "Fare Cage", ASH_REGION, "Hundreds of punched brass scraps have been sorted by route, then resorted by something less understandable.", {"west": ASH_HALL}, (TICKET_WIGHT,), ("level_7_9", "side_room")),
    _room(ASH_PIT, "Axle Pit", ASH_REGION, "A maintenance trench runs beneath the coach bays. Old road springs, wheel hubs, and one intact blackened spoke lie where mechanics dropped them during the relay's last evacuation.", {"north": ASH_BAYS, "east": ASH_PLATFORM}, (CHARRED_PORTER,), ("level_7_9",)),
    _room(ASH_PLATFORM, "Black Platform", ASH_REGION, "A passenger platform faces an indoor stretch of road ending in darkness. A painted line reads WAIT BEHIND THIS MARK UNTIL CALLED. Something beyond occasionally rings a hand bell.", {"north": ASH_HALL, "west": ASH_PIT, "east": ASH_TURNTABLE}, (), ("level_7_9",)),
    _room(ASH_TURNTABLE, "Driver's Turntable", ASH_REGION, "A circular coach turntable fills the chamber. Ash lies in perfect wheel tracks around its edge. At the center waits a driver's stool and an open brass fare box.", {"west": ASH_PLATFORM}, (), ("level_7_9", "boss")),
)
VAPOR_ROOMS = (
    _room(VAPOR_ENTRY, "Scent Cellar", VAPOR_REGION, "A narrow stair beneath Brassmarket ends in a cellar lined with dead scent pipes. The old House of Nine Vapors mark—nine silver leaves around an empty center—survives above the door.", {"up": VEYRA_BRASSMARKET_KEY, "south": VAPOR_GREEN}, (SCENTBOUND_ATTENDANT,), ("level_8_10", "entry")),
    _room(VAPOR_GREEN, "Green Room", VAPOR_REGION, "Green ceramic tiles cover the walls. Crushed stems, mint resin, and bitter leaves cling to drying racks. A wall vent is labeled GREEN SERVICE.", {"north": VAPOR_ENTRY, "east": VAPOR_AMBER}, (VAPOR_SLIME,), ("level_8_10",)),
    _room(VAPOR_AMBER, "Amber Room", VAPOR_REGION, "Amber glass jars fill floor-to-ceiling cabinets. Even sealed, they smell warm, resinous, and slightly medicinal.", {"west": VAPOR_GREEN, "east": VAPOR_SILVER, "south": VAPOR_HALL}, (SCENTBOUND_ATTENDANT,), ("level_8_10",)),
    _room(VAPOR_SILVER, "Silver Room", VAPOR_REGION, "A cold preparation room holds silver salts, pale powders, and metal scent fans. The third service vent is polished almost mirror-bright.", {"west": VAPOR_AMBER, "south": VAPOR_VAULT}, (GLASS_WASP,), ("level_8_10",)),
    _room(VAPOR_HALL, "Distillation Hall", VAPOR_REGION, "Copper coils cross overhead like organ pipes. Broken condensers drip clean water into bowls that remain strangely free of dust.", {"north": VAPOR_AMBER, "east": VAPOR_GALLERY}, (VAPOR_SLIME, GLASS_WASP), ("level_8_10",)),
    _room(VAPOR_VAULT, "Bottle Vault", VAPOR_REGION, "Thousands of bottle-shaped slots honeycomb the walls. A few still hold labels for scents whose houses, flowers, and customers have all vanished.", {"north": VAPOR_SILVER, "west": VAPOR_GALLERY}, (SCENTBOUND_ATTENDANT,), ("level_8_10", "side_room")),
    _room(VAPOR_GALLERY, "Mask Gallery", VAPOR_REGION, "Porcelain work masks hang in two rows, each with different filter holes. Every mask faces the final door.", {"west": VAPOR_HALL, "east": VAPOR_VAULT, "south": VAPOR_CHAMBER}, (GLASS_WASP,), ("level_8_10",)),
    _room(VAPOR_CHAMBER, "Ninth-Vapor Chamber", VAPOR_REGION, "Nine pipes descend around a circular brass floor. Three controls—GREEN, AMBER, SILVER—feed the chamber. The air here should be read before anything is opened.", {"north": VAPOR_GALLERY}, (), ("level_8_10", "boss")),
)
ROOMS = GLASS_ROOMS + ASH_ROOMS + VAPOR_ROOMS

LOOT_IDENTITIES = (
    LootIdentity(GLASS_REGION, (GLASSFRUIT_SHARD, WIDOW_SILK), "ringing glass + orchard silk", ("translucent", "silk", "orchard", "bell-like")),
    LootIdentity(ASH_REGION, (ASHWHEEL_SPOKE, CINDER_TICKET), "road iron + obsolete farework", ("coal-black", "brass", "travel", "uniform")),
    LootIdentity(VAPOR_REGION, (NINTH_VAPOR_RESIN, PERFUMER_SILVER_SALT), "aromatic resin + silver fixatives", ("perfume", "porcelain", "silver", "controlled excess")),
)
DUNGEONS = (
    DungeonTemplate("glass_orchard", "Glass Orchard Underbough", GLASS_REGION, (5, 7), GREYWAKE_RESONANT_ORCHARD_KEY, GLASS_ROOM_KEYS, ORCHARD_WIDOW, GLASSFRUIT_SHARD, STYLE_WIDOW_VEIL, "Break the three resonant fruits before challenging the Widow."),
    DungeonTemplate("ash_driver_relay", "The Ash Driver's Relay", ASH_REGION, (7, 9), VEYRA_CARAVAN_COURT_KEY, ASH_ROOM_KEYS, ASH_DRIVER, ASHWHEEL_SPOKE, STYLE_DRIVER_COAT, "Declare a fare before the old driver will acknowledge the fight."),
    DungeonTemplate("nine_vapors", "House of Nine Vapors", VAPOR_REGION, (8, 10), VEYRA_BRASSMARKET_KEY, VAPOR_ROOM_KEYS, PALE_DISTILLER, NINTH_VAPOR_RESIN, STYLE_NINE_VAPOR_BROOCH, "Read the weather-borne scent and choose a vent before the Distiller wakes."),
)


def _merge_augmentation(existing, extra):
    if existing is None:
        return extra
    return RoomAugmentation(
        exit_overrides=existing.exit_overrides + extra.exit_overrides,
        extra_exits=existing.extra_exits + extra.extra_exits,
        features=existing.features + extra.features,
        description_layers=existing.description_layers + extra.description_layers,
    )


def _register_recipe(recipe):
    if recipe.key in crafting.RECIPES_BY_KEY:
        return
    crafting.ALL_RECIPES = crafting.ALL_RECIPES + (recipe,)
    crafting.RECIPES_BY_KEY[recipe.key] = recipe
    mapping = {
        "blacksmithing": ("BLACKSMITHING_RECIPES", "BLACKSMITHING_RECIPES_BY_KEY"),
        "tailoring": ("TAILORING_RECIPES", "TAILORING_RECIPES_BY_KEY"),
        "alchemy": ("ALCHEMY_RECIPES", "ALCHEMY_RECIPES_BY_KEY"),
    }
    names = mapping.get(recipe.trade_skill_key)
    if names:
        tuple_name, dict_name = names
        setattr(crafting, tuple_name, getattr(crafting, tuple_name) + (recipe,))
        getattr(crafting, dict_name)[recipe.key] = recipe


def register_content_wave_one(world_service):
    for item in ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for recipe in RECIPES:
        _register_recipe(recipe)
    for enemy in ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for room in ROOMS:
        legacy_world.ROOMS_BY_KEY[room.key] = room
        if not any(existing.key == room.key for existing in legacy_world.ROOMS):
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        world_service.legacy_rooms[room.key] = room

    economy.LOOT_TABLES[ORCHARD_WIDOW] = (economy.LootDrop(GLASSFRUIT_SHARD, 2), economy.LootDrop(WIDOW_SILK, 1))
    economy.LOOT_TABLES[ASH_DRIVER] = (economy.LootDrop(ASHWHEEL_SPOKE, 1), economy.LootDrop(CINDER_TICKET, 2))
    economy.LOOT_TABLES[PALE_DISTILLER] = (economy.LootDrop(NINTH_VAPOR_RESIN, 1), economy.LootDrop(PERFUMER_SILVER_SALT, 2))
    economy.LOOT_TABLES[SILVERHART] = (economy.LootDrop(SILVERHART_ANTLER, 1),)
    economy.LOOT_TABLES[RAINTHREAD_SERPENT] = (economy.LootDrop(RAINTHREAD_SCALE, 1),)

    for meta in STYLE_META:
        if meta.item_key not in style.STYLE_META_BY_KEY:
            style.STYLE_META = style.STYLE_META + (meta,)
            style.STYLE_META_BY_KEY[meta.item_key] = meta
    if AFTERIMAGE_NO9 not in style.FRAGRANCE_BY_KEY:
        style.FRAGRANCES = style.FRAGRANCES + (AFTERIMAGE_FRAGRANCE,)
        style.FRAGRANCE_BY_KEY[AFTERIMAGE_NO9] = AFTERIMAGE_FRAGRANCE

    augmentations = {
        GREYWAKE_RESONANT_ORCHARD_KEY: RoomAugmentation(
            extra_exits=(ExitDefinition("east", GLASS_GATE, "broken orchard gate", aliases=("orchard", "underbough"), travel_text="You pass through the root-bent gate into the glass-fruited underbough.", condition=ViewCondition(min_level=5), hidden_when_unavailable=True),),
            features=(FeatureDefinition("root_bent_gate", "Root-Bent Orchard Gate", aliases=("gate", "orchard gate", "glass orchard"), summary="a root-bent gate leading into stranger orchard rows", examine_text="Beyond the gate, several pears have gone perfectly transparent. Pale silk links the branches."),),
        ),
        VEYRA_CARAVAN_COURT_KEY: RoomAugmentation(
            extra_exits=(ExitDefinition("down", ASH_ENTRY, "old relay ramp", aliases=("relay", "old relay"), travel_text="You follow the disused coach ramp down beneath the active caravan court.", condition=ViewCondition(required_flags=(VEYRA_RESIDENT_FLAG,), min_level=7), hidden_when_unavailable=True),),
            features=(FeatureDefinition("old_relay_ramp", "Old Relay Ramp", aliases=("ramp", "relay"), summary="a chained-off coach ramp descending beneath the newer court", examine_text="The chain has long since been cut. Ash lies in the wheel grooves below."),),
        ),
        VEYRA_BRASSMARKET_KEY: RoomAugmentation(
            extra_exits=(ExitDefinition("down", VAPOR_ENTRY, "sealed perfume stair", aliases=("perfume stair", "nine vapors"), travel_text="You descend through the old Nine Vapors service stair.", condition=ViewCondition(required_flags=(VEYRA_RESIDENT_FLAG,), min_level=8), hidden_when_unavailable=True),),
            features=(FeatureDefinition("nine_vapors_door", "Nine Vapors Door", aliases=("perfume door", "silver leaf door"), summary="a cellar door stamped with nine silver leaves", examine_text="The guild seal has expired, the lock has been cut, and somebody has written KEEP THE VENTS CLOSED in fresh chalk."),),
        ),
        VEYRA_SCHOLARS_RISE_KEY: RoomAugmentation(features=(FeatureDefinition("mechanical_moon", "Silver Mechanical Moon", aliases=("moon", "clockwork moon", "silver moon"), summary="a palm-sized mechanical moon mounted in a public astronomy niche", examine_text="A geared silver sphere tracks the lunar cycle. A tiny winding key can be turned by hand. During the Full Moon, one narrow seam aligns all the way around it."),)),
        WAYMEET_BROKEN_MILE_KEY: RoomAugmentation(description_layers=(DescriptionLayer("rain_ditch_glint", "Rainwater has exposed something metallic in the roadside ditch, too rectangular to be a stone.", priority=70, condition=ViewCondition(weather=("rain", "storm"))),)),
        SABLEWATER_SALTGRASS_BEND_KEY: RoomAugmentation(description_layers=(DescriptionLayer("rainthread_trace", "Heavy rain draws one unnaturally straight ripple through the saltgrass, moving against the wind.", priority=70, condition=ViewCondition(weather=("rain", "storm"))),)),
    }
    for key, augmentation in augmentations.items():
        world_service.augmentations[key] = _merge_augmentation(world_service.augmentations.get(key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*GLASS_ROOM_KEYS, *ASH_ROOM_KEYS, *VAPOR_ROOM_KEYS, *augmentations):
            cache.pop(key, None)


def _flag(session, key):
    return session.character is not None and key in session.database.list_flags(session.character.id)


def _grant_flag(session, key):
    if session.character is not None:
        session.database.grant_flag(session.character.id, key)


def _weather(session):
    service = getattr(session.__class__, "_content_foundry_world", None)
    if service is None or session.character is None:
        return "clear"
    scene = service.scene(session.character.current_room or "")
    return service.state.weather_for(scene.region_key) if scene is not None else "clear"


def _vapor_safe_color(weather):
    if weather in {"rain", "storm", "mist"}:
        return "green"
    if weather in {"cloudy", "snow", "damp"}:
        return "amber"
    return "silver"


def _boss_for_target(room_key, target):
    boss = {GLASS_NAVE: ORCHARD_WIDOW_DEF, ASH_TURNTABLE: ASH_DRIVER_DEF, VAPOR_CHAMBER: PALE_DISTILLER_DEF}.get(room_key)
    return boss if boss is not None and boss.matches(target) else None


async def _spawn_boss(session, definition):
    import asyncio
    if session.active_enemy is not None:
        await session.send(f"You are already fighting {session.active_enemy.definition.name}.\r\n")
        return
    enemy = EnemyState(definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    await session.send(f"You engage {definition.name}. Your normal weapon attacks begin automatically.\r\n")
    await session.send_client_state()
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))


def _rare_style_roll(session, boss_key, item_key):
    if random.random() >= 0.04 or session.character is None:
        return False
    session.database.add_item(session.character.id, item_key, 1)
    try:
        style._register_instance(session.database, session.character.id, item_key, f"Recovered from {combat.ENEMIES_BY_KEY[boss_key].name} on Astralis Day {ASTRALIS_CLOCK.now().day_number}.")
    except Exception:
        pass
    return True


def _cycle_flag(prefix):
    calendar = ASTRALIS_CLOCK.now().calendar
    return f"{prefix}_{(calendar.absolute_day - 1) // 28}"


def install_content_foundry_runtime(player_session_class, world_service):
    if getattr(player_session_class, "_content_foundry_installed", False):
        return
    register_content_wave_one(world_service)
    player_session_class._content_foundry_world = world_service
    original_start = player_session_class.start_combat
    original_finish = player_session_class._finish_enemy_defeat
    original_prompt = player_session_class.playing_prompt

    async def start_combat(self, target_text):
        if self.character is None or self.combatant is None:
            return await original_start(self, target_text)
        boss = _boss_for_target(self.character.current_room or "", target_text)
        if boss is None:
            return await original_start(self, target_text)
        if boss.key == ORCHARD_WIDOW and not all(_flag(self, f) for f in ("glassfruit_red_broken", "glassfruit_blue_broken", "glassfruit_clear_broken")):
            await self.send("The Widow's web is tensioned through three hanging glass fruits. BREAK RED FRUIT, BREAK BLUE FRUIT, and BREAK CLEAR FRUIT first.\r\n")
            return
        if boss.key == ASH_DRIVER and not _flag(self, "ash_driver_fare_declared"):
            await self.send("The driver does not move. One gloved hand remains extended. 'Fare.' OFFER NAME or OFFER SCRIP.\r\n")
            return
        if boss.key == PALE_DISTILLER and not _flag(self, "nine_vapors_vent_chosen"):
            await self.send("The Distiller is dormant behind mixed vapor. SMELL AIR, then OPEN GREEN VENT, OPEN AMBER VENT, or OPEN SILVER VENT.\r\n")
            return
        await _spawn_boss(self, boss)

    async def finish(self, enemy):
        key = enemy.definition.key
        result = await original_finish(self, enemy)
        if self.character is None:
            return result
        if key == ORCHARD_WIDOW:
            _grant_flag(self, "glass_orchard_cleared")
            if _rare_style_roll(self, key, STYLE_WIDOW_VEIL):
                await self.send("Something almost impossible survives the nest intact: an Orchard Widow Veil. A rare style trophy.\r\n")
            await self.send("The orchard does not become normal. It merely becomes quiet enough to hear ordinary wind again.\r\n")
        elif key == ASH_DRIVER:
            _grant_flag(self, "ash_driver_relay_cleared")
            if _rare_style_roll(self, key, STYLE_DRIVER_COAT):
                await self.send("The fare box opens after the Driver falls. Folded inside is an Ash Driver's Farecoat.\r\n")
            await self.send("The turntable rolls half a revolution. Somewhere in the relay, a clerk announces: 'Last service complete.'\r\n")
        elif key == PALE_DISTILLER:
            _grant_flag(self, "nine_vapors_cleared")
            if _rare_style_roll(self, key, STYLE_NINE_VAPOR_BROOCH):
                await self.send("One of the Distiller's nine silver scent leaves detaches as a complete brooch.\r\n")
            await self.send("The chamber clears one layer at a time until Brassmarket air smells shockingly plain.\r\n")
        elif key == SILVERHART:
            _grant_flag(self, _cycle_flag("silverhart_seen"))
        elif key == RAINTHREAD_SERPENT:
            _grant_flag(self, f"rainthread_seen_day_{ASTRALIS_CLOCK.now().day_number}")
        return result

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is None:
            from mud.session import SessionState
            self.state = SessionState.DISCONNECTED
            return
        verb = " ".join(command.strip().lower().split())
        room = self.character.current_room if self.character else ""

        if room == GLASS_NAVE and verb in {"break red fruit", "break blue fruit", "break clear fruit"}:
            color = verb.split()[1]
            flag = f"glassfruit_{color}_broken"
            if _flag(self, flag):
                await self.send(f"The {color} fruit already lies in ringing shards.\r\n")
            else:
                _grant_flag(self, flag)
                await self.send(f"You strike the {color} glassfruit. It bursts with a bell-like crack, and one span of the Widow's web goes slack.\r\n")
                if all(_flag(self, f) for f in ("glassfruit_red_broken", "glassfruit_blue_broken", "glassfruit_clear_broken")):
                    await self.send("All three tension fruits are gone. The Orchard Widow drops from the branches. ATTACK WIDOW.\r\n")
            return

        if room == ASH_TURNTABLE and verb in {"offer name", "offer scrip"}:
            if _flag(self, "ash_driver_fare_declared"):
                await self.send("The Ash Driver has already accepted your fare.\r\n")
                return
            if verb == "offer scrip":
                if self.database.item_quantity(self.character.id, WAYMEET_SCRIP_KEY) <= 0:
                    await self.send("You have no Waymeet Trade Scrip. OFFER NAME is also valid.\r\n")
                    return
                self.database.consume_item(self.character.id, WAYMEET_SCRIP_KEY, 1)
                await self.send("You place one modern scrip token in the ancient fare box. The Driver punches it anyway. 'Transfer accepted.'\r\n")
            else:
                await self.send(f"You give your name: {self.character.name}. The Driver punches an empty brass ticket and files it under a route that no longer exists. 'Fare accepted.'\r\n")
            _grant_flag(self, "ash_driver_fare_declared")
            await self.send("The Driver takes both hands off the fare box. ATTACK ASH DRIVER.\r\n")
            return

        if room == VAPOR_CHAMBER and verb == "smell air":
            weather = _weather(self)
            color = _vapor_safe_color(weather)
            text = {
                "green": "Rain-cooled air is pushing damp mineral odor down the pipes. The GREEN line smells cleanest against it.",
                "amber": "Flat cold air is holding heavy notes low. The AMBER line carries the only stable warm resin accord.",
                "silver": "Dry clear air makes every resin sharp. The SILVER line smells nearly neutral by comparison.",
            }[color]
            await self.send(text + f" Current Veyra weather: {weather}.\r\n")
            return

        if room == VAPOR_CHAMBER and verb in {"open green vent", "open amber vent", "open silver vent"}:
            color = verb.split()[1]
            safe = _vapor_safe_color(_weather(self))
            _grant_flag(self, "nine_vapors_vent_chosen")
            if color == safe:
                _grant_flag(self, "nine_vapors_safe_vent")
                await self.send(f"The {color.upper()} vent opens. The chamber clears instead of thickening. The Pale Distiller wakes already bleeding pressure.\r\n")
            else:
                await self.send(f"The {color.upper()} vent opens into the wrong air. Perfume fog rolls across the floor before emergency louvers catch it. The Distiller wakes fully pressurized.\r\n")
            await self.send("ATTACK PALE DISTILLER when ready.\r\n")
            return

        if room == GREYWAKE_RESONANT_ORCHARD_KEY and verb in {"track silverhart", "follow silver tracks"}:
            moment = ASTRALIS_CLOCK.now()
            if moment.moon_phase != "full" or moment.phase != "night":
                await self.send("Whatever made those pale hoof marks is not moving through the orchard now.\r\n")
                return
            if _flag(self, _cycle_flag("silverhart_seen")):
                await self.send("You already crossed the Silverhart's trail during this lunar cycle.\r\n")
                return
            await self.send("Moonlight gathers ahead into the shape of a tall stag. The Full-Moon Silverhart turns to face you.\r\n")
            await _spawn_boss(self, SILVERHART_DEF)
            return

        if room == SABLEWATER_SALTGRASS_BEND_KEY and verb in {"follow ripple", "track ripple"}:
            weather = _weather(self)
            day_flag = f"rainthread_seen_day_{ASTRALIS_CLOCK.now().day_number}"
            if weather not in {"rain", "storm"}:
                await self.send("Without hard rain, the saltgrass shows no coherent trail.\r\n")
                return
            if _flag(self, day_flag):
                await self.send("The strange ripple is gone for today.\r\n")
                return
            await self.send("A translucent serpent rises from the flooded grass, rain outlining every scale.\r\n")
            await _spawn_boss(self, RAINTHREAD_DEF)
            return

        if room == VEYRA_SCHOLARS_RISE_KEY and verb == "wind moon":
            moment = ASTRALIS_CLOCK.now()
            if moment.moon_phase != "full":
                await self.send("The silver sphere clicks twice and refuses to open. Its seam aligns only during the Full Moon.\r\n")
                return
            flag = _cycle_flag("moonwork_claimed")
            if _flag(self, flag):
                await self.send("The mechanical moon has already given you its token this lunar cycle.\r\n")
                return
            _grant_flag(self, flag)
            self.database.add_item(self.character.id, MOONWORK_TOKEN, 1)
            await self.send("The mechanism completes one perfect orbit. A tiny silver disk drops from a hidden slot: a Clockwork Moon Token. No quest updates. No fanfare.\r\n")
            return

        if room == WAYMEET_BROKEN_MILE_KEY and verb in {"search ditch", "search roadside ditch"}:
            weather = _weather(self)
            if weather not in {"rain", "storm"}:
                await self.send("The ditch holds weeds, wagon splinters, and ordinary road trash.\r\n")
                return
            if _flag(self, "earth_lighter_found"):
                await self.send("You already searched the washed-out pocket where the strange metal object lay.\r\n")
                return
            _grant_flag(self, "earth_lighter_found")
            self.database.add_item(self.character.id, EARTH_LIGHTER, 1)
            await self.send("Rain has cut a fresh groove through the clay. You pull out a metal object with a hinged lid and spark wheel. Human script marks the bottom in a language almost nobody can still read. You found a Dead Earth Lighter.\r\n")
            return

        if verb in {"content", "delves", "dungeons nearby"}:
            await self.send("\r\n--- New Delves ---\r\n")
            for dungeon in DUNGEONS:
                await self.send(f"{dungeon.name} (levels {dungeon.level_band[0]}-{dungeon.level_band[1]}) — {dungeon.hook}\r\n")
            await self.send("These are places, not a daily checklist. Their entrances are in the existing Greywake/Veyra world.\r\n")
            return

        async def one_shot_prompt(_text=""):
            return command
        prior = self.prompt
        self.prompt = one_shot_prompt
        try:
            return await original_prompt(self)
        finally:
            self.prompt = prior

    player_session_class.start_combat = start_combat
    player_session_class._finish_enemy_defeat = finish
    player_session_class.playing_prompt = playing_prompt
    player_session_class._content_foundry_installed = True
