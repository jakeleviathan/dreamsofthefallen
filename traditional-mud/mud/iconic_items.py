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
    item_type: str = "trophy"
    slot: str | None = None
    armor: int = 0
    might: int = 0
    grace: int = 0
    love: int = 0
    mind: int = 0
    hp: int = 0
    quirk: str = ""


# These are never called "iconics" to players. This is an internal content bible:
# memorable objects with names, sources, silhouettes, stories, and occasional
# rule-bending quirks. Many are deliberately not best-in-slot.
_RAW = (
# Early-world legends: useful, strange, tradable things a new player can hear about.
("fungus_warm_scale_tunic","Warmcap Scale Tunic","early","Sporekin deep-market rare","Living fungal scales stay warm and faintly pulse after rain.","equipment","chest",2,0,0,0,0,2,"Resting outdoors restores a little extra health."),
("sleepless_mans_coat","Sleepless Man's Coat","early","night road wanderer","A road coat whose cuffs are always cold, associated with a traveler nobody sees arrive.","equipment","chest",1,0,1,0,0,1,"A famous travel coat; its value is utility and story rather than raw armor."),
("blackwall_demon_horn","Blackwall Demon-Horn Buckler","early","Human Blackwall veteran cache","Black glass and old Earth alloy shaped to resemble the horns outsiders expect Humans to have.","equipment","off_hand",2,1,0,0,0,0,"A culturally defiant Human heirloom."),
("heartseed_bark_sash","Heartseed Bark Sash","early","Forest Elf stewardship secret","A supple strip of living bark that closes tiny cuts in itself overnight.","equipment","waist",0,0,1,1,0,1,"Recognized by Forest Elf gardeners."),
("third_chair_pin","Third Chair Pin","early","Moon Elf civic resolution","A lavender-silver pin made for the seat deliberately left open in an argument.","fashion",None,0,0,0,0,0,0,"NPCs who know High Horizon politics recognize it."),
("steam_union_knuckles","Union-Stamped Steam Knuckles","early","Dwarf shift commendation","Brass work gloves bearing too many inspection stamps.","equipment","hands",1,1,0,0,0,0,"Looks bureaucratic; hits surprisingly hard."),
("three_bells_purse","Three-Bells Purse","early","Goblin salvage bargain","A hide coin pouch with three mismatched brass bells and six hidden pockets.","trophy",None,0,0,0,0,0,0,"A notorious Goblin bargaining charm."),
("fire_before_pride_cloak","Fire-Before-Pride Cloak","early","Troll winter survival trial","Heavy green-gray wool smelling permanently of pine smoke.","equipment","back",1,0,0,0,0,3,"A practical survival flex among Trolls."),
("no_voice_collar","No Voice Above You Collar","early","Undead autonomy rite","A broken command collar polished until the fracture is the ornament.","fashion",None,0,0,0,0,0,0,"An Undead symbol of personhood."),
("chorus_single_spore","Single-Spore Lantern","early","Sporekin Chorus hollow","A thumb-sized bioluminescent fungus kept in a pierced silver cage.","trophy",None,0,0,0,0,0,0,"Brightens when several Sporekin gather."),
("milewalkers_red_boots","Milewalker's Red Boots","early","Waymeet Broken Mile rare","Red leather boots scarred by hundreds of repaired cuts.","equipment","feet",1,0,2,0,0,0,"A beloved low-level travel item."),
("nix_coils_lucky_scale","Nix Coil's Lucky Scale","early","Waymeet merchant oddment","One brass balance-pan scale engraved WRONG SIDE UP.","trophy",None,0,0,0,0,0,0,"Collectors argue whether Nix ever owned it."),
("reedmaw_tusk_ring","Reedmaw Tusk Ring","early","rare Reedmaw Boar","A polished tusk ring too large for most fingers and worn on a cord.","fashion",None,0,0,0,0,0,0,"Early hunter bragging right."),
("slateback_splitter","Slateback Splitter","early","Old Waymeet Quarry rare","A short iron cleaver with a Slateback claw set into the pommel.","equipment","main_hand",0,2,0,0,0,0,"Cheap-looking weapon with a cult following."),
("tollmans_unpaid_key","Tollman's Unpaid Key","early","Tollman's Cellar secret","A large key tagged PAID IN FULL despite opening no known lock.","trophy",None,0,0,0,0,0,0,"Rumored to open something players have not found."),
("crooked_bell_earguard","Crooked Bell Earguard","early","Hollow Bellkeeper","One padded bronze ear cup attached to a green cord.","equipment","head",1,0,0,0,1,0,"A recognizable souvenir of learning to listen."),
("kings_scar_hook","King's Scar Climbing Hook","early","Riftback Matriarch","A quarry hook bent into a shape no smith can quite reproduce.","equipment","off_hand",1,0,1,0,0,0,"Associated with reckless quarry explorers."),
("first_echo_reed","First Echo Reed","early","Vault of the First Echo secret","A black reed that produces no note when blown, only a pressure in the teeth.","trophy",None,0,0,0,0,0,0,"One of the first objects that hints the world's echo can inhabit matter."),
("listeners_small_mask","Listener's Small Mask","early","Listener Below rare","A smooth gray half-mask with no mouth opening.","fashion",None,0,0,0,0,0,0,"A coveted early capstone flex."),
("waymeet_wardens_lantern","Warden's Bent Lantern","early","Waymeet road contract rare","A dented lantern whose shutter clicks exactly three times.","trophy",None,0,0,0,0,0,0,"Old players recognize it immediately."),
("thornback_whistle","Thornback Whistle","early","Broken Mile rare","A fang whistle that makes jackals answer from farther away than seems sensible.","trophy",None,0,0,0,0,0,0,"Socially notorious because people insist on blowing it."),
("blackreed_captains_buckle","Blackreed Captain's Buckle","early","Blackreed shield captain rare","A broad iron buckle scored by repeated shield rims.","equipment","waist",1,1,0,0,0,1,"A tank-flavored trophy that remains wearable later."),
("gravewatch_bonewhite_mantle","Bonewhite Watch Mantle","early","Gravewatch commander rare","A faded watch mantle bleached almost white by river fog.","equipment","back",1,0,0,0,1,2,"Traditional-dungeon prestige piece."),
("gravewatch_commanders_spur","Commander's Single Spur","early","Gravewatch officer cache","One silver riding spur; nobody has found its mate.","trophy",None,0,0,0,0,0,0,"Its missing pair is a standing community joke."),
("gloam_coldglass_eye","Coldglass Eye","early","Gloamworks rare","A lens of impossible cold glass that reflects a room a fraction late.","trophy",None,0,0,0,0,0,0,"Unsettling Gloamworks collector piece."),
("buried_regent_chain","Buried Regent's Chain","early","Buried Regent rare","A dark ceremonial chain with one link that cannot lie flat.","equipment","neck",1,0,0,0,2,0,"A recognizable co-op dungeon status item."),
("greywake_bellhide_cape","Bellhide Cape","early","rare Bellhide Grazer","A short cape of tawny hide with naturally resonant scales at the collar.","equipment","back",1,0,1,0,0,1,"Makes a soft chime when entering a room."),
("roadwarden_blue_scarf","Roadwarden Blue Scarf","early","Roadwarden service rare","A narrow blue road scarf faded nearly gray at the ends.","fashion",None,0,0,0,0,0,0,"Faction veterans wear it long after better gear."),
("ledger_black_abacus","Deep Ledger Black Abacus","early","Deep Ledger contract oddity","A pocket abacus with black-glass beads and one red bead nobody accounts for.","trophy",None,0,0,0,0,0,0,"A trader's status object."),
("lantern_oath_candle","Never-Out Lantern Candle","early","Lantern Oath service rare","A stubby white candle that seems to last far longer than its size permits.","trophy",None,0,0,0,0,0,0,"Often displayed in rented rooms."),

# Midgame legends: travel/economy drivers and pieces people build characters around.
("veyra_bridgecoat","Veyra Bridgecoat","mid","Veyra civic stores rare","A sharply cut charcoal coat reinforced at the shoulder like bridge-worker harness.","equipment","chest",3,0,1,0,1,3,"The quintessential Veyra all-purpose coat."),
("keykeepers_seven_ring","Keykeeper's Seven-Ring","mid","Veyra Keyhouse heritage","Seven tiny keys on one finger ring; six are decorative.","fashion",None,0,0,0,0,0,0,"Nobody agrees which key is real."),
("ninepins_green_gloves","Ninepins Green Gloves","mid","Pikka Ninepins rare boutique event","Acid-green gloves with immaculate black stitching.","fashion",None,0,0,0,0,0,0,"Fashion players recognize them across a room."),
("riversteps_silver_shoes","Riversteps Silver Shoes","mid","Veyra Riversteps hidden vendor","Soft gray shoes with soles stitched in silver thread.","equipment","feet",1,0,2,0,1,0,"Stylish travel footwear."),
("brassmarket_perfume_case","Brassmarket Perfume Case","mid","Veyra fragrance collector milestone","A six-bottle travel case with a mirrored brass lid.","trophy",None,0,0,0,0,0,0,"Collector flex for fragrance devotees."),
("underclock_governors_heart","Governor's Second Heart","mid","Cinder Governor rare","A warm brass regulator that ticks only while carried.","trophy",None,0,0,0,0,0,0,"Players use its ticking as an Underclock badge."),
("underclock_minutehand_spear","Minute-Hand Spear","mid","Underclock craft secret","A long black spear balanced around a salvaged clock hand.","equipment","main_hand",0,3,1,0,0,0,"Famous for its silhouette, not maximal damage."),
("drowned_auditors_visor","Auditor's Green Visor","mid","Brass Auditor rare","A translucent green visor on a drowned brass frame.","equipment","head",1,0,0,0,2,0,"A bureaucracy-dungeon cult item."),
("tollhouse_last_receipt","Last Receipt of Sablewater","mid","Drowned Tollhouse secret","A waterproof receipt for a toll abolished before the writer was born.","trophy",None,0,0,0,0,0,0,"One of Astralis's favorite absurd collectibles."),
("eelmarket_stormcloak","Eelmarket Stormcloak","mid","Sablewater rare weather vendor","Oil-dark cloth that beads rain into perfect spheres.","equipment","back",2,0,1,0,0,2,"Desired whenever wetland travel matters."),
("blackwing_feather_crown","Blackwing Feather Crown","mid","Blackwing Rookery rare","An intentionally ridiculous crown of glossy black rook feathers.","fashion",None,0,0,0,0,0,0,"Pure bragging rights."),
("driftwood_saints_rope","Driftwood Saint's Rope","mid","Driftwood Shrine mystery","A salt-stiff rope belt with seven knots and no known saint.","equipment","waist",1,0,0,1,1,1,"Players invent contradictory lore about it."),
("glassfruit_ringblade","Glassfruit Ringblade","mid","Glass Orchard craft","A circular orchard blade with translucent teeth.","equipment","main_hand",0,3,2,0,0,0,"Signature Glass Orchard weapon."),
("orchard_widows_slippers","Orchard Widow's Slippers","mid","Orchard Widow very rare","Elegant translucent slippers woven from widow-silk.","fashion",None,0,0,0,0,0,0,"Deliberately absurd boss-fashion jackpot."),
("ash_driver_ticket_punch","Ash Driver's Ticket Punch","mid","Ash Driver rare","A heavy brass punch that stamps a tiny skull-shaped hole.","trophy",None,0,0,0,0,0,0,"Players punch paper notes with it in roleplay."),
("farecoat_black","Black Farecoat","mid","Ash Driver very rare","Long soot-black coat with an obsolete fare schedule sewn into the lining.","equipment","chest",3,1,1,0,0,2,"Iconic roadwear with recognizable flavor."),
("nine_vapors_silver_fan","Nine-Vapor Silver Fan","mid","Pale Distiller rare","A folding scent fan with nine perforated silver leaves.","fashion",None,0,0,0,0,0,0,"Fragrance-community status piece."),
("perfumer_no_zero","Perfumer's No. 0","mid","House of Nine Vapors secret","A blank white bottle whose scent is rain, paper, and something remembered incorrectly.","fragrance",None,0,0,0,0,0,0,"A collectible scent people seek for the name alone."),
("silverhart_moonbow","Silverhart Moonbow","mid","Silverhart rare-spawn craft","A pale recurved bow made around a naturally shed Silverhart antler.","equipment","main_hand",0,2,3,0,0,0,"Rare-spawn craft that drives exploration and trade."),
("rainthread_longcoat","Rainthread Longcoat","mid","Rainthread Serpent craft","A translucent gray longcoat that never appears fully wet.","equipment","chest",2,0,2,0,1,2,"Weather-linked prestige utility."),
("mechanical_moon","The Little Mechanical Moon","mid","full-moon Veyra oddity","A palm-sized silver moon with internal gears and one tiny opening door.","trophy",None,0,0,0,0,0,0,"Only opens under the real full moon."),
("dead_earth_zippo","The Dead Lighter","mid","lost Human Earth cache","A scratched Earth lighter with an alien maker's mark and no usable fuel.","trophy",None,0,0,0,0,0,0,"One of the most coveted Human antiquities despite doing nothing."),
("moonelf_starglass_monocle","Starglass Monocle","mid","High Horizon rare artisan","A lavender lens that makes stars visible a little before sunset.","equipment","face",0,0,0,0,2,0,"Moon Elf fashion-science icon."),
("dwarf_foremans_red_helmet","Foreman's Red Helmet","mid","Dwarf union masterwork","A battered red steamworks helmet covered in legitimate inspection stamps.","equipment","head",3,1,0,0,0,3,"A famous defensive hat with working-class prestige."),
("goblin_everything_tool","Everything Tool","mid","Goblin master salvager","A folding implement with nineteen tools, three unidentified.","equipment","off_hand",1,1,1,0,1,0,"Beloved because it sounds useful even when it isn't optimal."),
("troll_snowmother_fur","Snowmother's Fur","mid","tundra Troll hunt rare","Enormous white-gray fur mantle with blue beadwork.","equipment","back",3,1,0,0,0,4,"A huge visual flex."),
("undead_first_name_ring","Ring of the First Name","mid","Undead memory quest rare","A plain iron ring engraved inside with the wearer's chosen name.","equipment","finger",0,0,0,1,2,1,"Culturally important rather than numerically dominant."),
("sporekin_dreamcap","Dreamcap Crown","mid","Sporekin deep chorus rare","A living crown of tiny violet mushrooms that rearrange overnight.","equipment","head",1,0,0,2,2,1,"Distinctive living fashion."),
("forest_elf_white_stag_cloak","White Stag Leafcloak","mid","Forest Elf delayed stag consequence","Leaves, shed white hair, and fine green thread woven without killing the stag.","equipment","back",2,0,2,1,0,2,"Its acquisition story matters more than rarity."),

# Deep-world legends: raid goals, impossible oddities, and long-term server mythology.
("leviathans_silent_scale","Leviathan's Silent Scale","deep","unknown First Breath mystery","A black scale-shaped object that may not be a scale at all. Sound seems reluctant near it.","trophy",None,0,0,0,0,0,0,"No tooltip confirms what it truly is."),
("again_blade","Again","deep","Listener mythology chain","A narrow gray blade with the single word AGAIN cut through the metal.","equipment","main_hand",0,4,2,0,2,0,"Its name is the entire inscription."),
("one_breath_circlet","Circlet of One Breath","deep","First Echo raid secret","A thin dark circlet that fogs once when equipped and never again for that owner.","equipment","head",2,0,0,2,3,2,"A lore prestige piece."),
("regents_impossible_boot","Regent's Impossible Boot","deep","Buried Regent mythic rare","One beautifully made ceremonial boot; the other has never dropped.","equipment","feet",2,0,2,0,2,1,"The missing mate becomes server folklore."),
("gloam_mirror_sword","Sword in the Late Mirror","deep","deep Gloam anomaly","A sword whose reflection completes swings a heartbeat after the wielder.","equipment","main_hand",0,4,2,0,2,0,"Visually and narratively unmistakable."),
("veyra_first_bridge_nail","Nail of the First Bridge","deep","Veyra civic heritage chain","A fist-long black nail claimed to come from the bridge beneath every later bridge.","trophy",None,0,0,0,0,0,0,"City-history status relic."),
("king_without_country_crown","Crown of the King Without a Country","deep","future ruined court","A narrow tarnished crown sized for no known race.","equipment","head",2,1,0,1,2,2,"Starts arguments about who the king was."),
("saint_of_small_fires_lantern","Lantern of the Saint of Small Fires","deep","future pilgrimage dungeon","A tiny lantern whose flame is barely enough to read by and almost impossible to extinguish.","equipment","off_hand",1,0,0,3,2,1,"Priests covet it for story and utility."),
("thirteen_button_coat","Thirteen-Button Coat","deep","wandering night tailor","A perfect black coat with thirteen buttons; counting again sometimes gives twelve.","equipment","chest",3,0,2,0,2,3,"An iconic traveling-tailor chase item."),
("empty_scabbard","The Empty Scabbard","deep","unknown world drop","An ornate scabbard that rejects every weapon players try to sheath in it.","trophy",None,0,0,0,0,0,0,"Designed to sustain years of speculation."),
("last_green_leaf","The Last Green Leaf","deep","ancient Forest Elf grove","A living leaf that never browns after being plucked.","trophy",None,0,0,0,0,0,0,"Quiet, simple, immediately memorable."),
("moon_that_fell","Shard of the Moon That Fell","deep","Moon Elf high-altitude raid","Lavender-white stone that casts a shadow toward the moon.","equipment","neck",1,0,0,1,4,1,"Moon Elf cosmology prestige."),
("dwarven_zero_gauge","Gauge Zero","deep","sealed Dwarf pressure vault","A pressure gauge whose needle rests below zero and moves when nobody watches.","equipment","off_hand",2,0,0,0,3,2,"Engineers insist the reading is impossible."),
("goblin_original_part","The Original Part","deep","Goblin junk-city legend","A small immaculate gear every Goblin claims came before all the replacement parts.","trophy",None,0,0,0,0,0,0,"Comedic cultural relic with real collector prestige."),
("troll_first_spear","The First Spear's Tip","deep","old Troll stronghold","A huge green-black stone spearhead polished by generations of hands.","equipment","main_hand",0,5,0,0,0,4,"Ancient Troll martial icon."),
("undead_funeral_bell","Bell for Someone Already Dead","deep","Undead necropolis","A little silver funeral bell that rings only once for each owner.","trophy",None,0,0,0,0,0,0,"A deeply personal collectible."),
("sporekin_lonely_cap","The Lonely Cap","deep","isolated Sporekin cavern","A pale mushroom that refuses to join the Chorus but remains alive indefinitely.","equipment","head",1,0,0,2,4,2,"A philosophical Sporekin icon."),
("human_blue_plastic_card","Blue Plastic Card","deep","sealed Earth artifact cache","A rectangle of blue Earth plastic embossed with dead numbers and a stranger's name.","trophy",None,0,0,0,0,0,0,"Humans treasure it despite having no idea what it purchased."),
("forest_elf_rainknife","Knife That Cuts Rain","deep","Forest Elf storm mystery","A leaf-shaped knife on which raindrops divide cleanly before touching the blade.","equipment","main_hand",0,3,4,0,1,0,"Elegant utility legend."),
("moonelf_third_shadow","Third Shadow Mantle","deep","High Horizon lunar alignment","A lavender mantle that seems to cast one shadow too many under moonlight.","equipment","back",2,0,2,0,3,2,"Extremely recognizable night fashion."),
("veyra_thousandth_key","The Thousandth Key","deep","Keyhouse long collection","A plain brass key numbered 1000; the Keyhouse denies numbering keys.","trophy",None,0,0,0,0,0,0,"Citywide mystery object."),
("blackreed_unbroken_shield","Unbroken Blackreed Shield","deep","Blackreed perfect-run rare","A battered shield with no structural crack despite decades of impacts.","equipment","off_hand",5,1,0,0,0,4,"A tank's long-term bragging-rights item."),
("gravewatch_last_watch","The Last Watch","deep","Gravewatch midnight condition","A dead commander's pocket watch that advances only inside Gravewatch.","trophy",None,0,0,0,0,0,0,"Makes old content mysterious again."),
("sablewater_dry_boots","Dry Boots of Sablewater","deep","flood-season secret","Ordinary-looking brown boots that somehow remain dry in standing water.","equipment","feet",2,0,3,0,0,2,"Simple utility makes them famous."),
("underclock_eighth_minute","The Eighth Minute","deep","Underclock impossible cycle rare","A brass minute hand engraved VIII despite the clock having no eighth phase.","trophy",None,0,0,0,0,0,0,"Suggests the machine has behavior players haven't seen."),
("crooked_lantern_lead_mask","Crooked Lantern Lead Mask","deep","traveling troupe ultra-rare performance","The actual lead performer's cracked stage mask, retired after a legendary production.","fashion",None,0,0,0,0,0,0,"Social-world prestige rather than combat prestige."),
("jar_prophets_actual_jar","Jar Prophet's Actual Jar","deep","market pastime impossible jackpot","The cloudy guessing jar itself, retired with its final stones still inside.","trophy",None,0,0,0,0,0,0,"Absurdly prestigious because everyone knows the minigame."),
("bent_spoon_gold","The Straight Spoon","deep","Three Bones legendary streak","A perfectly straight golden spoon awarded by people famous for giving bent ones.","trophy",None,0,0,0,0,0,0,"Community-joke prestige item."),
("perfume_levis_breath","Breath Without a Second","deep","master fragrance pilgrimage","A one-use black crystal fragrance ampoule with no written notes.","fragrance",None,0,0,0,0,0,0,"The scent is described differently to each race."),
("veyra_red_door_key","Key to the Red Door","deep","unknown Veyra rare","A red-enamel key. No currently mapped Veyra door is red.","trophy",None,0,0,0,0,0,0,"A deliberate community mystery."),
("road_end_sign","Sign From the End of the Road","deep","far-road future content","A weathered direction sign pointing only BACK.","trophy",None,0,0,0,0,0,0,"Explorer status object."),
("astralis_first_coin","Coin From Before Money","deep","ancient trade mystery","A heavy electrum disk older than every known mint, stamped with an open mouth.","trophy",None,0,0,0,0,0,0,"Currency historians obsess over it."),
("silent_orchestra_baton","Silent Orchestra Baton","deep","future acoustic dungeon","A black conductor's baton that makes nearby idle ambience briefly cease when raised.","equipment","off_hand",0,0,0,2,3,0,"A tiny world-bending social effect."),
("white_room_chair","Chair From the White Room","deep","unknown extradimensional room","A miniature white chair carved from one piece of bone-like material.","trophy",None,0,0,0,0,0,0,"No one knows what the White Room is at launch."),
("leviathan_word_fragment","A Word That Wasn't Spoken","deep","ultimate First Breath mystery","A smooth object the inventory can name but characters cannot comfortably describe.","trophy",None,0,0,0,0,0,0,"An endgame mystery anchor, intentionally unexplained."),
)

ICONIC_ITEMS = tuple(IconicItem(*row) for row in _RAW)
assert len(ICONIC_ITEMS) == 90, f"Expected exactly 90 iconic items, got {len(ICONIC_ITEMS)}"
ICONIC_BY_KEY = {item.key: item for item in ICONIC_ITEMS}


def _definition(icon: IconicItem) -> ItemDefinition:
    equipment = None
    category = icon.item_type
    if icon.slot:
        category = "equipment"
        equipment = EquipmentItem(
            icon.name,
            icon.slot,
            armor_class=icon.armor,
            stat_bonuses=CharacterStats(
                might=icon.might,
                grace=icon.grace,
                love=icon.love,
                mind=icon.mind,
                hp=icon.hp,
            ),
        )
    description = icon.identity + (f" {icon.quirk}" if icon.quirk else "")
    return ItemDefinition(icon.key, icon.name, description, category, equipment=equipment, tier=4 if icon.level_band == "deep" else (3 if icon.level_band == "mid" else 2))


def install_iconic_items() -> None:
    """Register the 90-item identity catalog without exposing an 'iconic' label in play."""
    for icon in ICONIC_ITEMS:
        if icon.key not in crafting.ITEMS_BY_KEY:
            crafting.register_item(_definition(icon))


def iconic_design_note(item_key: str) -> IconicItem | None:
    """Internal hook for loot/content modules to attach these objects organically."""
    return ICONIC_BY_KEY.get(item_key)
