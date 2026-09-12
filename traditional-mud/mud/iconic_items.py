from __future__ import annotations

from dataclasses import dataclass

import mud.crafting as crafting
from mud.crafting import ItemDefinition
from mud.stats import CharacterStats, EquipmentItem


@dataclass(frozen=True, slots=True)
class IconicItem:
    key: str
    name: str
    level_band: str
    source: str
    identity: str
    slot: str | None = None
    armor: int = 0
    might: int = 0
    grace: int = 0
    love: int = 0
    mind: int = 0
    hp: int = 0
    quirk: str = ""


# Internal design anchors only. Players never see an "iconic" rarity tag.
_EARLY_NAMES = (
    ("warmcap_scale_tunic", "Warmcap Scale Tunic", "Sporekin deep-market rare", "Living fungal scales stay warm and faintly pulse after rain.", "chest"),
    ("sleepless_mans_coat", "Sleepless Man's Coat", "night-road wanderer", "A cold-cuffed road coat associated with a traveler nobody sees arrive.", "chest"),
    ("blackwall_demon_horn_buckler", "Blackwall Demon-Horn Buckler", "Human Blackwall cache", "Black glass shaped in the horned style Humans made their own.", "off_hand"),
    ("heartseed_bark_gloves", "Heartseed Bark Gloves", "Forest Elf stewardship secret", "Supple bark gloves whose tiny scratches close by morning.", "hands"),
    ("third_chair_pin", "Third Chair Pin", "Moon Elf civic resolution", "A lavender-silver pin honoring the seat deliberately left open in an argument.", None),
    ("union_stamped_steam_gauntlets", "Union-Stamped Steam Gauntlets", "Dwarf shift commendation", "Brass work gauntlets bearing too many legitimate inspection stamps.", "hands"),
    ("three_bells_purse", "Three-Bells Purse", "Goblin salvage bargain", "A hide purse with three mismatched bells and six hidden pockets.", None),
    ("fire_before_pride_boots", "Fire-Before-Pride Boots", "Troll survival trial", "Smoke-dark boots with pine pitch worked into every seam.", "feet"),
    ("no_voice_above_you_mask", "No Voice Above You Mask", "Undead autonomy rite", "A broken command mask polished until the fracture became the ornament.", "head"),
    ("single_spore_lantern", "Single-Spore Lantern", "Sporekin chorus hollow", "One luminous fungus kept in a pierced silver cage.", None),
    ("milewalkers_red_boots", "Milewalker's Red Boots", "Waymeet Broken Mile rare", "Red leather boots repaired so many times the repairs became the design.", "feet"),
    ("nix_coils_lucky_scale", "Nix Coil's Lucky Scale", "Waymeet market oddment", "A brass balance-pan scale engraved WRONG SIDE UP.", None),
    ("reedmaw_tusk_guard", "Reedmaw Tusk Guard", "rare Reedmaw Boar", "A polished tusk fitted into a practical wrist guard.", "off_hand"),
    ("slateback_splitter", "Slateback Splitter", "Old Waymeet Quarry rare", "A short iron cleaver with a Slateback claw set into the pommel.", "main_hand"),
    ("tollmans_unpaid_key", "Tollman's Unpaid Key", "Tollman's Cellar secret", "A large key tagged PAID IN FULL despite opening no known lock.", None),
    ("crooked_bell_earguard", "Crooked Bell Earguard", "Hollow Bellkeeper", "A single padded bronze earguard on a green cord.", "head"),
    ("kings_scar_hook", "King's Scar Hook", "Riftback Matriarch", "A quarry hook bent into a shape no smith quite reproduces.", "off_hand"),
    ("first_echo_reed", "First Echo Reed", "Vault of the First Echo secret", "A black reed that makes no note when blown, only pressure in the teeth.", None),
    ("listeners_small_mask", "Listener's Small Mask", "Listener Below rare", "A smooth gray mask with no mouth opening.", "head"),
    ("wardens_bent_lantern", "Warden's Bent Lantern", "Waymeet road contract rare", "A dented lantern whose shutter clicks exactly three times.", None),
    ("thornback_whistle", "Thornback Whistle", "Broken Mile rare", "A fang whistle that makes distant jackals answer.", None),
    ("blackreed_captains_buckle", "Blackreed Captain's Buckle", "Captain Vara Skell rare", "A broad iron buckle scored by repeated shield rims.", "chest"),
    ("bonewhite_watch_helm", "Bonewhite Watch Helm", "Gravewatch commander rare", "A river-fog bleached garrison helm with the crest filed away.", "head"),
    ("commanders_single_spur", "Commander's Single Spur", "Gravewatch officer cache", "One silver riding spur; nobody has found its mate.", None),
    ("coldglass_eye", "Coldglass Eye", "Gloamworks rare", "A lens of impossible cold glass that reflects a room a fraction late.", None),
    ("buried_regent_chainmail", "Buried Regent Chainmail", "Buried Regent rare", "Black articulated mail with one link that never lies flat.", "chest"),
    ("bellhide_leggings", "Bellhide Leggings", "rare Bellhide Grazer", "Tawny hide leggings with naturally resonant scales at the knees.", "legs"),
    ("roadwarden_blue_hood", "Roadwarden Blue Hood", "Roadwarden service rare", "A blue road hood faded nearly gray at the edges.", "head"),
    ("deep_ledger_black_abacus", "Deep Ledger Black Abacus", "Deep Ledger contract oddity", "A pocket abacus with one unexplained red bead.", None),
    ("never_out_candle", "Never-Out Lantern Candle", "Lantern Oath service rare", "A white candle stub that lasts far longer than its size permits.", None),
)
_MID_NAMES = (
    ("veyra_bridgecoat", "Veyra Bridgecoat", "Veyra civic stores rare", "A charcoal coat reinforced like a bridge-worker harness.", "chest"),
    ("keykeepers_seven_ring", "Keykeeper's Seven-Ring", "Veyra Keyhouse heritage", "Seven tiny keys on one ring; six are decorative.", None),
    ("ninepins_green_gloves", "Ninepins Green Gloves", "Pikka Ninepins rare event", "Acid-green gloves with immaculate black stitching.", "hands"),
    ("riversteps_silver_shoes", "Riversteps Silver Shoes", "Veyra hidden vendor", "Soft gray shoes with silver-thread soles.", "feet"),
    ("brassmarket_perfume_case", "Brassmarket Perfume Case", "fragrance collector milestone", "A six-bottle case with a mirrored brass lid.", None),
    ("governors_second_heart", "Governor's Second Heart", "Cinder Governor rare", "A warm brass regulator that ticks only while carried.", None),
    ("minute_hand_spear", "Minute-Hand Spear", "Underclock craft secret", "A black spear balanced around a salvaged clock hand.", "main_hand"),
    ("auditors_green_visor", "Auditor's Green Visor", "Brass Auditor rare", "A translucent green visor on a drowned brass frame.", "head"),
    ("last_receipt_sablewater", "Last Receipt of Sablewater", "Drowned Tollhouse secret", "A waterproof receipt for a toll abolished generations ago.", None),
    ("eelmarket_stormboots", "Eelmarket Stormboots", "Sablewater weather vendor rare", "Oil-dark boots that bead rain into perfect spheres.", "feet"),
    ("blackwing_feather_helm", "Blackwing Feather Helm", "Rookery rare", "A helmet with an intentionally ridiculous crown of rook feathers.", "head"),
    ("driftwood_saints_belt", "Driftwood Saint's Belt", "Driftwood Shrine mystery", "A salt-stiff rope belt with seven knots and no known saint.", "legs"),
    ("glassfruit_ringblade", "Glassfruit Ringblade", "Glass Orchard craft", "A circular orchard blade with translucent teeth.", "main_hand"),
    ("orchard_widows_slippers", "Orchard Widow's Slippers", "Orchard Widow very rare", "Elegant translucent slippers woven from widow-silk.", "feet"),
    ("ash_drivers_ticket_punch", "Ash Driver's Ticket Punch", "Ash Driver rare", "A heavy brass punch that stamps a skull-shaped hole.", "off_hand"),
    ("black_farecoat", "Black Farecoat", "Ash Driver very rare", "A soot-black coat with an obsolete fare schedule sewn into the lining.", "chest"),
    ("nine_vapor_silver_fan", "Nine-Vapor Silver Fan", "Pale Distiller rare", "A folding scent fan with nine perforated silver leaves.", "off_hand"),
    ("perfumer_no_zero", "Perfumer's No. 0", "House of Nine Vapors secret", "A blank white bottle whose scent is rain, paper and something remembered incorrectly.", None),
    ("silverhart_moonbow", "Silverhart Moonbow", "Silverhart rare-spawn craft", "A pale bow built around a naturally shed Silverhart antler.", "main_hand"),
    ("rainthread_longcoat", "Rainthread Longcoat", "Rainthread Serpent craft", "A translucent gray coat that never looks fully wet.", "chest"),
    ("little_mechanical_moon", "The Little Mechanical Moon", "full-moon Veyra oddity", "A palm-sized silver moon with one tiny opening door.", None),
    ("dead_earth_lighter", "The Dead Lighter", "lost Human Earth cache", "A scratched Earth lighter whose fuel no Astralian can reproduce.", None),
    ("starglass_monocle_helm", "Starglass Monocle Helm", "High Horizon artisan rare", "A light helm mounting a lavender lens that catches stars before sunset.", "head"),
    ("foremans_red_helmet", "Foreman's Red Helmet", "Dwarf union masterwork", "A battered red steamworks helmet covered in legitimate inspection stamps.", "head"),
    ("everything_tool", "Everything Tool", "Goblin master salvager", "A folding tool with nineteen implements and three unidentified parts.", "off_hand"),
    ("snowmothers_fur_armor", "Snowmother's Fur Armor", "Troll tundra hunt rare", "Enormous white-gray fur armor with blue beadwork.", "chest"),
    ("ring_of_first_name", "Ring of the First Name", "Undead memory quest rare", "A plain iron ring engraved inside with the wearer's chosen name.", None),
    ("dreamcap_crown", "Dreamcap Crown", "Sporekin deep chorus rare", "A living violet mushroom crown that rearranges overnight.", "head"),
    ("white_stag_leafcloak_armor", "White Stag Leafcloak Armor", "Forest Elf delayed stag consequence", "Leaf-layered armor woven with naturally shed white stag hair.", "chest"),
    ("three_banner_travelers_greaves", "Three-Banner Traveler's Greaves", "Greywake veteran rare", "Dust-gray greaves repaired with three schools of field work.", "legs"),
)
_DEEP_NAMES = (
    ("leviathans_silent_scale", "Leviathan's Silent Scale", "unknown First Breath mystery", "A black scale-shaped object that may not be a scale at all.", None),
    ("again_blade", "Again", "Listener mythology chain", "A narrow gray blade with the word AGAIN cut through the metal.", "main_hand"),
    ("circlet_of_one_breath", "Circlet of One Breath", "First Echo raid secret", "A dark helm-ring that fogs once when equipped and never again for that owner.", "head"),
    ("regents_impossible_boot", "Regent's Impossible Boot", "Buried Regent mythic rare", "One beautifully made ceremonial boot; the other has never dropped.", "feet"),
    ("sword_in_late_mirror", "Sword in the Late Mirror", "deep Gloam anomaly", "A sword whose reflection completes swings a heartbeat late.", "main_hand"),
    ("nail_of_first_bridge", "Nail of the First Bridge", "Veyra civic heritage chain", "A fist-long black nail claimed to predate every current bridge.", None),
    ("king_without_country_crown", "Crown of the King Without a Country", "ruined court", "A narrow tarnished crown sized for no known race.", "head"),
    ("saint_small_fires_lantern", "Lantern of the Saint of Small Fires", "pilgrimage dungeon", "A tiny lantern whose flame is nearly impossible to extinguish.", "off_hand"),
    ("thirteen_button_coat", "Thirteen-Button Coat", "wandering night tailor", "A perfect black coat with thirteen buttons; recounting sometimes gives twelve.", "chest"),
    ("empty_scabbard", "The Empty Scabbard", "unknown world drop", "An ornate scabbard that rejects every known weapon.", None),
    ("last_green_leaf", "The Last Green Leaf", "ancient Forest Elf grove", "A living leaf that never browns after being plucked.", None),
    ("moon_that_fell_helm", "Helm of the Moon That Fell", "Moon Elf high-altitude raid", "Lavender-white stone set into a pale helm; its shadow leans toward the moon.", "head"),
    ("gauge_zero", "Gauge Zero", "sealed Dwarf pressure vault", "A pressure gauge whose needle rests below zero and moves when nobody watches.", "off_hand"),
    ("goblin_original_part", "The Original Part", "Goblin junk-city legend", "A small immaculate gear every Goblin claims predates all replacement parts.", None),
    ("first_spear", "The First Spear", "old Troll stronghold", "A huge green-black spear polished by generations of hands.", "main_hand"),
    ("bell_for_someone_already_dead", "Bell for Someone Already Dead", "Undead necropolis", "A little silver bell that rings only once for each owner.", None),
    ("lonely_cap_helm", "The Lonely Cap", "isolated Sporekin cavern", "A pale living mushroom cap that refuses to join the Chorus.", "head"),
    ("blue_plastic_card", "Blue Plastic Card", "sealed Earth artifact cache", "A rectangle of blue Earth plastic embossed with dead numbers and a stranger's name.", None),
    ("knife_that_cuts_rain", "Knife That Cuts Rain", "Forest Elf storm mystery", "A leaf-shaped knife on which raindrops divide before touching the blade.", "main_hand"),
    ("third_shadow_armor", "Third Shadow Mantle", "High Horizon lunar alignment", "Lavender armor that seems to cast one shadow too many at night.", "chest"),
    ("thousandth_key", "The Thousandth Key", "Keyhouse long collection", "A plain brass key numbered 1000; the Keyhouse denies numbering keys.", None),
    ("unbroken_blackreed_shield", "Unbroken Blackreed Shield", "Blackreed perfect-run rare", "A battered shield with no structural crack despite decades of impacts.", "off_hand"),
    ("last_watch", "The Last Watch", "Gravewatch midnight condition", "A dead commander's pocket watch that advances only inside Gravewatch.", None),
    ("dry_boots_sablewater", "Dry Boots of Sablewater", "flood-season secret", "Ordinary brown boots that somehow remain dry in standing water.", "feet"),
    ("eighth_minute", "The Eighth Minute", "Underclock impossible cycle rare", "A brass minute hand engraved VIII despite the clock having no eighth phase.", None),
    ("crooked_lantern_lead_mask", "Crooked Lantern Lead Mask", "traveling troupe ultra-rare", "The retired cracked mask from a legendary production.", "head"),
    ("jar_prophets_actual_jar", "Jar Prophet's Actual Jar", "market pastime jackpot", "The cloudy guessing jar itself, retired with its final stones inside.", None),
    ("the_straight_spoon", "The Straight Spoon", "Three Bones legendary streak", "A perfectly straight golden spoon awarded by people famous for bent ones.", None),
    ("key_to_red_door", "Key to the Red Door", "unknown Veyra rare", "A red-enamel key. No mapped Veyra door is red.", None),
    ("word_that_wasnt_spoken", "A Word That Wasn't Spoken", "ultimate First Breath mystery", "A smooth object the inventory can name but characters cannot comfortably describe.", None),
)


def _make_band(rows, band: str, base: int) -> tuple[IconicItem, ...]:
    result = []
    for i, (key, name, source, identity, slot) in enumerate(rows):
        power = base + (i % 2)
        result.append(IconicItem(
            key, name, band, source, identity, slot,
            armor=power if slot in {"head", "chest", "legs", "feet", "hands", "off_hand"} else 0,
            might=power if slot == "main_hand" else 0,
            grace=1 if slot in {"feet", "hands"} else 0,
            mind=1 if i % 7 == 0 and slot is not None else 0,
            hp=power if slot == "chest" else 0,
        ))
    return tuple(result)


ICONIC_ITEMS = _make_band(_EARLY_NAMES, "early", 1) + _make_band(_MID_NAMES, "mid", 2) + _make_band(_DEEP_NAMES, "deep", 3)
assert len(ICONIC_ITEMS) == 90
assert len({item.key for item in ICONIC_ITEMS}) == 90
ICONIC_BY_KEY = {item.key: item for item in ICONIC_ITEMS}


def _definition(icon: IconicItem) -> ItemDefinition:
    equipment = None
    category = "trophy"
    if icon.slot is not None:
        category = "equipment"
        equipment = EquipmentItem(
            icon.name, icon.slot, armor_class=icon.armor,
            stat_bonuses=CharacterStats(icon.might, icon.grace, icon.love, icon.mind, icon.hp),
        )
    tier = 2 if icon.level_band == "early" else 3 if icon.level_band == "mid" else 4
    return ItemDefinition(icon.key, icon.name, icon.identity, category, equipment=equipment, tier=tier)


def install_iconic_items() -> None:
    additions = []
    for icon in ICONIC_ITEMS:
        if icon.key not in crafting.ITEMS_BY_KEY:
            definition = _definition(icon)
            additions.append(definition)
            crafting.ITEMS_BY_KEY[icon.key] = definition
    if additions:
        crafting.ITEMS = crafting.ITEMS + tuple(additions)


def iconic_design_note(item_key: str) -> IconicItem | None:
    return ICONIC_BY_KEY.get(item_key)
