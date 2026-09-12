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


# Internal design anchors only. The player-facing game never labels these
# "iconic"; their status is meant to emerge from utility, names, stories and
# social memory. Exactly thirty early, thirty mid and thirty deep-world pieces.
_RAW = (
# EARLY 1-30
("warmcap_scale_tunic","Warmcap Scale Tunic","early","Sporekin deep-market rare","Living fungal scales stay warm and faintly pulse after rain.","chest",2,0,0,0,0,2,"Resting outdoors with it became a road-traveler superstition."),
("sleepless_mans_coat","Sleepless Man's Coat","early","night-road wanderer","A cold-cuffed road coat associated with a traveler nobody sees arrive.","chest",1,0,1,0,0,1,"People swear it is easier to stay awake on long roads while wearing it."),
("blackwall_demon_horn_buckler","Blackwall Demon-Horn Buckler","early","Human Blackwall cache","Black glass and old alloy shaped in the horned style Humans made their own.","off_hand",2,1,0,0,0,0,"A defiant Human heirloom."),
("heartseed_bark_gloves","Heartseed Bark Gloves","early","Forest Elf stewardship secret","Supple bark gloves whose tiny scratches close by morning.","hands",1,0,1,1,0,0,"Forest gardeners recognize them immediately."),
("third_chair_pin","Third Chair Pin","early","Moon Elf civic resolution","A lavender-silver pin honoring the seat deliberately left open in an argument.",None,0,0,0,0,0,0,"A quiet High Horizon status symbol."),
("union_stamped_steam_gauntlets","Union-Stamped Steam Gauntlets","early","Dwarf shift commendation","Brass work gauntlets bearing too many legitimate inspection stamps.","hands",2,1,0,0,0,1,"Nobody agrees which stamp is the important one."),
("three_bells_purse","Three-Bells Purse","early","Goblin salvage bargain","A hide purse with three mismatched bells and six hidden pockets.",None,0,0,0,0,0,0,"Goblin merchants insist it improves bargaining."),
("fire_before_pride_boots","Fire-Before-Pride Boots","early","Troll survival trial","Smoke-dark boots with pine pitch worked into every seam.","feet",1,0,1,0,0,2,"Trolls value the story more than the armor."),
("no_voice_above_you_mask","No Voice Above You Mask","early","Undead autonomy rite","A broken command mask polished until the fracture became the ornament.","head",1,0,0,1,1,0,"An Undead symbol of self-ownership."),
("single_spore_lantern","Single-Spore Lantern","early","Sporekin chorus hollow","One luminous fungus kept in a pierced silver cage.",None,0,0,0,0,0,0,"It glows more strongly near a gathered Chorus."),
("milewalkers_red_boots","Milewalker's Red Boots","early","Waymeet Broken Mile rare","Red leather boots repaired so many times the repairs became the design.","feet",1,0,2,0,0,0,"A beloved early travel item."),
("nix_coils_lucky_scale","Nix Coil's Lucky Scale","early","Waymeet market oddment","A brass balance-pan scale engraved WRONG SIDE UP.",None,0,0,0,0,0,0,"Collectors argue whether Nix ever owned it."),
("reedmaw_tusk_guard","Reedmaw Tusk Guard","early","rare Reedmaw Boar","A polished tusk fitted into a practical wrist guard.","off_hand",1,1,0,0,0,0,"An early hunter's flex."),
("slateback_splitter","Slateback Splitter","early","Old Waymeet Quarry rare","A short iron cleaver with a Slateback claw set into the pommel.","main_hand",0,2,0,0,0,0,"Cheap-looking and surprisingly beloved."),
("tollmans_unpaid_key","Tollman's Unpaid Key","early","Tollman's Cellar secret","A large key tagged PAID IN FULL despite opening no known lock.",None,0,0,0,0,0,0,"Players keep trying it everywhere."),
("crooked_bell_earguard","Crooked Bell Earguard","early","Hollow Bellkeeper","A single padded bronze earguard on a green cord.","head",1,0,0,0,1,0,"Recognizable proof that somebody learned to listen."),
("kings_scar_hook","King's Scar Hook","early","Riftback Matriarch","A quarry hook bent into a shape no smith quite reproduces.","off_hand",1,0,1,0,0,0,"Associated with reckless climbers."),
("first_echo_reed","First Echo Reed","early","Vault of the First Echo secret","A black reed that makes no note when blown, only pressure in the teeth.",None,0,0,0,0,0,0,"One of the first material hints of the world's echo."),
("listeners_small_mask","Listener's Small Mask","early","Listener Below rare","A smooth gray mask with no mouth opening.","head",1,0,0,0,2,0,"A coveted first capstone trophy."),
("wardens_bent_lantern","Warden's Bent Lantern","early","Waymeet road contract rare","A dented lantern whose shutter clicks exactly three times.",None,0,0,0,0,0,0,"Old Waymeet players know it instantly."),
("thornback_whistle","Thornback Whistle","early","Broken Mile rare","A fang whistle that makes distant jackals answer.",None,0,0,0,0,0,0,"People blow it in taverns despite being asked not to."),
("blackreed_captains_buckle","Blackreed Captain's Buckle","early","Captain Vara Skell rare","A broad iron buckle scored by repeated shield rims.","chest",1,1,0,0,0,1,"A tank-flavored keepsake that stays wearable."),
("bonewhite_watch_helm","Bonewhite Watch Helm","early","Gravewatch commander rare","A river-fog bleached garrison helm with the crest filed away.","head",2,1,0,0,0,2,"Classic-dungeon prestige."),
("commanders_single_spur","Commander's Single Spur","early","Gravewatch officer cache","One silver riding spur; nobody has found its mate.",None,0,0,0,0,0,0,"The missing pair is a standing community joke."),
("coldglass_eye","Coldglass Eye","early","Gloamworks rare","A lens of impossible cold glass that reflects a room a fraction late.",None,0,0,0,0,0,0,"An unsettling collector piece."),
("buried_regent_chainmail","Buried Regent Chainmail","early","Buried Regent rare","Black articulated mail with one link that never lies flat.","chest",3,0,0,0,2,1,"A recognizable cooperative-dungeon item."),
("bellhide_leggings","Bellhide Leggings","early","rare Bellhide Grazer","Tawny hide leggings with naturally resonant scales at the knees.","legs",1,0,1,0,0,1,"They softly chime when the wearer sits."),
("roadwarden_blue_hood","Roadwarden Blue Hood","early","Roadwarden service rare","A blue road hood faded nearly gray at the edges.","head",1,0,1,0,0,1,"Faction veterans keep wearing it after upgrades."),
("deep_ledger_black_abacus","Deep Ledger Black Abacus","early","Deep Ledger contract oddity","A pocket abacus with one unexplained red bead.",None,0,0,0,0,0,0,"A trader's status object."),
("never_out_candle","Never-Out Lantern Candle","early","Lantern Oath service rare","A white candle stub that lasts far longer than its size permits.",None,0,0,0,0,0,0,"Commonly displayed in personal rooms."),
# MID 31-60
("veyra_bridgecoat","Veyra Bridgecoat","mid","Veyra civic stores rare","A charcoal coat reinforced like a bridge-worker harness.","chest",3,0,1,0,1,3,"The quintessential Veyra all-purpose coat."),
("keykeepers_seven_ring","Keykeeper's Seven-Ring","mid","Veyra Keyhouse heritage","Seven tiny keys on one ring; six are decorative.",None,0,0,0,0,0,0,"Nobody agrees which key is real."),
("ninepins_green_gloves","Ninepins Green Gloves","mid","Pikka Ninepins rare event","Acid-green gloves with immaculate black stitching.","hands",1,0,2,0,0,0,"Fashion players recognize them across a room."),
("riversteps_silver_shoes","Riversteps Silver Shoes","mid","Veyra hidden vendor","Soft gray shoes with silver-thread soles.","feet",1,0,2,0,1,0,"Stylish travel footwear."),
("brassmarket_perfume_case","Brassmarket Perfume Case","mid","fragrance collector milestone","A six-bottle case with a mirrored brass lid.",None,0,0,0,0,0,0,"Collector prestige for scent devotees."),
("governors_second_heart","Governor's Second Heart","mid","Cinder Governor rare","A warm brass regulator that ticks only while carried.",None,0,0,0,0,0,0,"Underclock veterans use its ticking as a badge."),
("minute_hand_spear","Minute-Hand Spear","mid","Underclock craft secret","A black spear balanced around a salvaged clock hand.","main_hand",0,3,1,0,0,0,"Famous for silhouette more than damage."),
("auditors_green_visor","Auditor's Green Visor","mid","Brass Auditor rare","A translucent green visor on a drowned brass frame.","head",1,0,0,0,2,0,"A cult bureaucracy-dungeon item."),
("last_receipt_sablewater","Last Receipt of Sablewater","mid","Drowned Tollhouse secret","A waterproof receipt for a toll abolished generations ago.",None,0,0,0,0,0,0,"Astralis's favorite absurd paperwork collectible."),
("eelmarket_stormboots","Eelmarket Stormboots","mid","Sablewater weather vendor rare","Oil-dark boots that bead rain into perfect spheres.","feet",2,0,1,0,0,2,"Desired whenever wetland travel matters."),
("blackwing_feather_helm","Blackwing Feather Helm","mid","Rookery rare","A helmet with an intentionally ridiculous crown of rook feathers.","head",2,0,1,0,0,1,"Pure bragging rights with enough armor to justify wearing it."),
("driftwood_saints_belt","Driftwood Saint's Belt","mid","Driftwood Shrine mystery","A salt-stiff rope belt with seven knots and no known saint.","legs",1,0,0,1,1,1,"Players invent contradictory lore about it."),
("glassfruit_ringblade","Glassfruit Ringblade","mid","Glass Orchard craft","A circular orchard blade with translucent teeth.","main_hand",0,3,2,0,0,0,"Signature Glass Orchard weapon."),
("orchard_widows_slippers","Orchard Widow's Slippers","mid","Orchard Widow very rare","Elegant translucent slippers woven from widow-silk.","feet",1,0,3,0,0,0,"An absurd boss-fashion jackpot."),
("ash_drivers_ticket_punch","Ash Driver's Ticket Punch","mid","Ash Driver rare","A heavy brass punch that stamps a skull-shaped hole.","off_hand",1,1,0,0,1,0,"Players use it on notes during roleplay."),
("black_farecoat","Black Farecoat","mid","Ash Driver very rare","A soot-black coat with an obsolete fare schedule sewn into the lining.","chest",3,1,1,0,0,2,"Iconic roadwear."),
("nine_vapor_silver_fan","Nine-Vapor Silver Fan","mid","Pale Distiller rare","A folding scent fan with nine perforated silver leaves.","off_hand",1,0,1,1,2,0,"Fragrance-community status piece."),
("perfumer_no_zero","Perfumer's No. 0","mid","House of Nine Vapors secret","A blank white bottle whose scent is rain, paper and something remembered incorrectly.",None,0,0,0,0,0,0,"Sought for the name alone."),
("silverhart_moonbow","Silverhart Moonbow","mid","Silverhart rare-spawn craft","A pale bow built around a naturally shed Silverhart antler.","main_hand",0,2,3,0,0,0,"Rare-spawn craft that drives exploration and trade."),
("rainthread_longcoat","Rainthread Longcoat","mid","Rainthread Serpent craft","A translucent gray coat that never looks fully wet.","chest",2,0,2,0,1,2,"Weather-linked prestige utility."),
("little_mechanical_moon","The Little Mechanical Moon","mid","full-moon Veyra oddity","A palm-sized silver moon with one tiny opening door.",None,0,0,0,0,0,0,"Only opens under a full moon."),
("dead_earth_lighter","The Dead Lighter","mid","lost Human Earth cache","A scratched Earth lighter whose fuel no Astralian can reproduce.",None,0,0,0,0,0,0,"Coveted despite doing almost nothing."),
("starglass_monocle_helm","Starglass Monocle Helm","mid","High Horizon artisan rare","A light helm mounting a lavender lens that catches stars before sunset.","head",1,0,0,0,2,0,"Moon Elf fashion-science icon."),
("foremans_red_helmet","Foreman's Red Helmet","mid","Dwarf union masterwork","A battered red steamworks helmet covered in legitimate inspection stamps.","head",3,1,0,0,0,3,"Working-class prestige."),
("everything_tool","Everything Tool","mid","Goblin master salvager","A folding tool with nineteen implements and three unidentified parts.","off_hand",1,1,1,0,1,0,"Beloved because it always feels useful."),
("snowmothers_fur_armor","Snowmother's Fur Armor","mid","Troll tundra hunt rare","Enormous white-gray fur armor with blue beadwork.","chest",4,1,0,0,0,4,"A huge visual flex."),
("ring_of_first_name","Ring of the First Name","mid","Undead memory quest rare","A plain iron ring engraved inside with the wearer's chosen name.",None,0,0,0,0,0,0,"Culturally important rather than numerically dominant."),
("dreamcap_crown","Dreamcap Crown","mid","Sporekin deep chorus rare","A living violet mushroom crown that rearranges overnight.","head",1,0,0,2,2,1,"Distinctive living gear."),
("white_stag_leafcloak_armor","White Stag Leafcloak Armor","mid","Forest Elf delayed stag consequence","Leaf-layered armor woven with naturally shed white stag hair.","chest",2,0,2,1,0,2,"Its acquisition story matters more than rarity."),
("three_banner_travelers_greaves","Three-Banner Traveler's Greaves","mid","Greywake veteran rare","Dust-gray greaves repaired with three visibly different schools of field work.","legs",3,1,1,0,0,2,"A visible record of surviving all three factions' roads."),
# DEEP 61-90
("leviathans_silent_scale","Leviathan's Silent Scale","deep","unknown First Breath mystery","A black scale-shaped object that may not be a scale at all.",None,0,0,0,0,0,0,"Sound seems reluctant near it."),
("again_blade","Again","deep","Listener mythology chain","A narrow gray blade with the word AGAIN cut through the metal.","main_hand",0,4,2,0,2,0,"Its name is the entire inscription."),
("circlet_of_one_breath","Circlet of One Breath","deep","First Echo raid secret","A dark helm-ring that fogs once when equipped and never again for that owner.","head",2,0,0,2,3,2,"A lore prestige piece."),
("regents_impossible_boot","Regent's Impossible Boot","deep","Buried Regent mythic rare","One beautifully made ceremonial boot; the other has never dropped.","feet",2,0,2,0,2,1,"The missing mate becomes server folklore."),
("sword_in_late_mirror","Sword in the Late Mirror","deep","deep Gloam anomaly","A sword whose reflection completes swings a heartbeat late.","main_hand",0,4,2,0,2,0,"Immediately recognizable."),
("nail_of_first_bridge","Nail of the First Bridge","deep","Veyra civic heritage chain","A fist-long black nail claimed to predate every current bridge.",None,0,0,0,0,0,0,"City-history status relic."),
("king_without_country_crown","Crown of the King Without a Country","deep","ruined court","A narrow tarnished crown sized for no known race.","head",2,1,0,1,2,2,"Starts arguments about who the king was."),
("saint_small_fires_lantern","Lantern of the Saint of Small Fires","deep","pilgrimage dungeon","A tiny lantern whose flame is barely enough to read by and nearly impossible to extinguish.","off_hand",1,0,0,3,2,1,"Priests covet its story and utility."),
("thirteen_button_coat","Thirteen-Button Coat","deep","wandering night tailor","A perfect black coat with thirteen buttons; recounting sometimes gives twelve.","chest",3,0,2,0,2,3,"A traveling-tailor chase item."),
("empty_scabbard","The Empty Scabbard","deep","unknown world drop","An ornate scabbard that rejects every known weapon.",None,0,0,0,0,0,0,"Designed to sustain years of speculation."),
("last_green_leaf","The Last Green Leaf","deep","ancient Forest Elf grove","A living leaf that never browns after being plucked.",None,0,0,0,0,0,0,"Quiet and immediately memorable."),
("moon_that_fell_helm","Helm of the Moon That Fell","deep","Moon Elf high-altitude raid","Lavender-white stone set into a pale helm; its shadow leans toward the moon.","head",3,0,1,1,4,1,"Moon Elf cosmology prestige."),
("gauge_zero","Gauge Zero","deep","sealed Dwarf pressure vault","A pressure gauge whose needle rests below zero and moves when nobody watches.","off_hand",2,0,0,0,3,2,"Engineers insist its reading is impossible."),
("goblin_original_part","The Original Part","deep","Goblin junk-city legend","A small immaculate gear every Goblin claims predates all replacement parts.",None,0,0,0,0,0,0,"Comedic cultural prestige."),
("first_spear","The First Spear","deep","old Troll stronghold","A huge green-black spear polished by generations of hands.","main_hand",0,5,0,0,0,4,"Ancient Troll martial icon."),
("bell_for_someone_already_dead","Bell for Someone Already Dead","deep","Undead necropolis","A little silver bell that rings only once for each owner.",None,0,0,0,0,0,0,"A deeply personal collectible."),
("lonely_cap_helm","The Lonely Cap","deep","isolated Sporekin cavern","A pale living mushroom cap that refuses to join the Chorus.","head",1,0,0,2,4,2,"A philosophical Sporekin icon."),
("blue_plastic_card","Blue Plastic Card","deep","sealed Earth artifact cache","A rectangle of blue Earth plastic embossed with dead numbers and a stranger's name.",None,0,0,0,0,0,0,"Humans treasure it without knowing what it bought."),
("knife_that_cuts_rain","Knife That Cuts Rain","deep","Forest Elf storm mystery","A leaf-shaped knife on which raindrops divide before touching the blade.","main_hand",0,3,4,0,1,0,"Elegant utility legend."),
("third_shadow_armor","Third Shadow Mantle","deep","High Horizon lunar alignment","Lavender armor that seems to cast one shadow too many at night.","chest",3,0,2,0,3,2,"Extremely recognizable moonlit gear."),
("thousandth_key","The Thousandth Key","deep","Keyhouse long collection","A plain brass key numbered 1000; the Keyhouse denies numbering keys.",None,0,0,0,0,0,0,"Citywide mystery object."),
("unbroken_blackreed_shield","Unbroken Blackreed Shield","deep","Blackreed perfect-run rare","A battered shield with no structural crack despite decades of impacts.","off_hand",5,1,0,0,0,4,"A tank's long-term bragging-rights item."),
("last_watch","The Last Watch","deep","Gravewatch midnight condition","A dead commander's pocket watch that advances only inside Gravewatch.",None,0,0,0,0,0,0,"Makes old content mysterious again."),
("dry_boots_sablewater","Dry Boots of Sablewater","deep","flood-season secret","Ordinary brown boots that somehow remain dry in standing water.","feet",2,0,3,0,0,2,"Simple utility makes them famous."),
("eighth_minute","The Eighth Minute","deep","Underclock impossible cycle rare","A brass minute hand engraved VIII despite the clock having no eighth phase.",None,0,0,0,0,0,0,"Suggests unseen machine behavior."),
("crooked_lantern_lead_mask","Crooked Lantern Lead Mask","deep","traveling troupe ultra-rare","The retired cracked mask from a legendary production.","head",1,0,1,1,1,0,"Social-world prestige rather than raid prestige."),
("jar_prophets_actual_jar","Jar Prophet's Actual Jar","deep","market pastime jackpot","The cloudy guessing jar itself, retired with its final stones inside.",None,0,0,0,0,0,0,"Absurdly prestigious because everyone knows the game."),
("the_straight_spoon","The Straight Spoon","deep","Three Bones legendary streak","A perfectly straight golden spoon awarded by people famous for bent ones.",None,0,0,0,0,0,0,"Community-joke prestige."),
("key_to_red_door","Key to the Red Door","deep","unknown Veyra rare","A red-enamel key. No mapped Veyra door is red.",None,0,0,0,0,0,0,"A deliberate community mystery."),
("word_that_wasnt_spoken","A Word That Wasn't Spoken","deep","ultimate First Breath mystery","A smooth object the inventory can name but characters cannot comfortably describe.",None,0,0,0,0,0,0,"An intentionally unexplained endgame mystery anchor."),
)

ICONIC_ITEMS = tuple(IconicItem(*row) for row in _RAW)
assert len(ICONIC_ITEMS) == 90
assert len({item.key for item in ICONIC_ITEMS}) == 90
ICONIC_BY_KEY = {item.key: item for item in ICONIC_ITEMS}


def _definition(icon: IconicItem) -> ItemDefinition:
    equipment = None
    category = "trophy"
    if icon.slot is not None:
        category = "equipment"
        equipment = EquipmentItem(
            icon.name,
            icon.slot,
            armor_class=icon.armor,
            stat_bonuses=CharacterStats(icon.might, icon.grace, icon.love, icon.mind, icon.hp),
        )
    description = icon.identity + (f" {icon.quirk}" if icon.quirk else "")
    tier = 2 if icon.level_band == "early" else 3 if icon.level_band == "mid" else 4
    return ItemDefinition(icon.key, icon.name, description, category, equipment=equipment, tier=tier)


def install_iconic_items() -> None:
    for icon in ICONIC_ITEMS:
        if icon.key not in crafting.ITEMS_BY_KEY:
            crafting.register_item(_definition(icon))


def iconic_design_note(item_key: str) -> IconicItem | None:
    return ICONIC_BY_KEY.get(item_key)
