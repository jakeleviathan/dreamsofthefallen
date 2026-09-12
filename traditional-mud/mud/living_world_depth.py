from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import mud.living_world as living
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment
from mud.equipment_system import equipped_item_keys
from mud.greywake_march import GREYWAKE_SIGNAL_HILL_KEY, GREYWAKE_THREE_BANNER_KEY
from mud.sablewater_reach import (
    SABLEWATER_EEL_DOCK_KEY,
    SABLEWATER_HERON_FLATS_KEY,
    SABLEWATER_REED_FARMS_KEY,
    SABLEWATER_WILLOW_FERRY_KEY,
)
from mud.veyra_city import (
    VEYRA_BRASSMARKET_KEY,
    VEYRA_GRAND_CROSSING_KEY,
    VEYRA_PUBLIC_HEARTH_KEY,
)
from mud.waymeet_frontier import (
    WAYMEET_BRIARCUT_KEY,
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_QUARRY_KEY,
    WAYMEET_SCRIP_KEY,
)


LIVING_WORLD_DEPTH_VERSION = "1.0.0"
BOARD_NOTE_MAX_LENGTH = 160
BOARD_NOTE_COOLDOWN_DAYS = 3
BOARD_NOTE_LIFETIME_DAYS = 7
ARC_CYCLE_DAYS = 28


@dataclass(frozen=True, slots=True)
class DailyTexture:
    key: str
    category: str
    room_key: str
    room_name: str
    dispatch: str
    gossip: str
    ambient: str


@dataclass(frozen=True, slots=True)
class AmbientScene:
    key: str
    room_key: str
    phases: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class ScheduledVisitor:
    key: str
    name: str
    aliases: tuple[str, ...]
    role: str
    presence: str
    talk_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArcStage:
    label: str
    room_key: str
    room_name: str
    dispatch: str
    gossip: str
    ambient: str


@dataclass(frozen=True, slots=True)
class WorldArc:
    key: str
    title: str
    start_record: str
    resolution_record: str
    stages: tuple[ArcStage, ...]


# A second, quieter daily layer sits beside the primary DailyPulse rather than
# replacing it. That preserves the established event schedule while giving each
# Astralis day another piece of texture that can be heard in dispatches, gossip,
# or simply encountered in a room.
DAILY_TEXTURES: tuple[DailyTexture, ...] = (
    DailyTexture(
        "waymeet_boot_mender", "trade", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard",
        "A boot-mender has taken the sunny wall at the Commonhouse and is doing brisk road work.",
        "'If your left boot squeaks, she charges extra because she says it has already learned bad habits.'",
        "A boot-mender works an awl through three different kinds of road leather while customers stand around in their socks.",
    ),
    DailyTexture(
        "waymeet_children_maps", "culture", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard",
        "Children at Waymeet have started drawing competing maps of where every road really begins.",
        "'The Goblin child put Junk City in the middle of the page. The Dwarf child called that cartographically aggressive.'",
        "Three children have chalked incompatible maps across the same paving stone and are defending them with absolute confidence.",
    ),
    DailyTexture(
        "lantern_market_spice", "trade", WAYMEET_LANTERN_MARKET_KEY, "Waymeet Lantern Market",
        "A spice sack split at Lantern Market, and half the crossroads now smells sharply of pepper and dried citrus.",
        "'Nix says the road smells expensive today.'",
        "Every few breaths somebody sneezes. A merchant keeps insisting the bright orange powder on the stones is still saleable.",
    ),
    DailyTexture(
        "briar_seed_wind", "weather", WAYMEET_BRIARCUT_KEY, "Briarcut Fields",
        "A west wind is carrying white seed-fluff through Briarcut like slow snow.",
        "'Pretty from the road. Less pretty when it gets into your stew.'",
        "White seed-fluff drifts waist-high through the field, catching on buckles, thorns, and anything else willing to carry it farther.",
    ),
    DailyTexture(
        "quarry_echo_game", "social", WAYMEET_QUARRY_KEY, "Old Waymeet Quarry",
        "Quarry workers have spent the slow hour testing which wall returns the rudest echo.",
        "'Hedda won, but only because she knows more rude words than the apprentices.'",
        "Somebody shouts a word into the quarry. A delayed answer comes back from the stone, followed by embarrassed laughter.",
    ),
    DailyTexture(
        "broken_mile_marker", "travel", WAYMEET_BROKEN_MILE_KEY, "The Broken Mile",
        "A fresh stack of painted route stones has appeared along the worst bend of the Broken Mile.",
        "'Roadwardens paint arrows. Travelers still follow whichever cart looks most confident.'",
        "New route stones gleam too cleanly beside the road, their arrows already collecting argumentative bootprints.",
    ),
    DailyTexture(
        "three_banner_kettle", "social", GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp",
        "Someone at Three-Banner Camp has declared one kettle neutral territory between the three factions.",
        "'The kettle has more successful diplomacy than the officers.'",
        "A black kettle sits precisely between three different camp tables. Everyone uses it. Nobody admits to cleaning it.",
    ),
    DailyTexture(
        "greywake_signal_practice", "travel", GREYWAKE_SIGNAL_HILL_KEY, "Greywake Signal Hill",
        "Signal Hill is drilling a new flag sequence for flooded-road warnings.",
        "'Red-white-red means water. Red-red-white apparently means Oryn dropped the flags again.'",
        "Two wardens repeat the same flag pattern until the movement becomes almost musical against the sky.",
    ),
    DailyTexture(
        "veyra_bridge_measure", "craft", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing",
        "Surveyors are measuring Grand Crossing again, mostly to prove last month's measurements were not imaginary.",
        "'Four cultures built that bridge and six professions now argue about who gets to measure it.'",
        "A survey string spans one side of the bridge. Pedestrians step over it without breaking stride.",
    ),
    DailyTexture(
        "veyra_market_clock", "trade", VEYRA_BRASSMARKET_KEY, "Veyra Brassmarket",
        "Brassmarket merchants are arguing about whether the public clock is three minutes slow or commerce is three minutes fast.",
        "'Pikka says a late customer is late even if the clock sympathizes.'",
        "Three merchants glance at the same clock and somehow arrive at four different conclusions.",
    ),
    DailyTexture(
        "veyra_hearth_stew", "social", VEYRA_PUBLIC_HEARTH_KEY, "Veyra Public Hearth",
        "The Public Hearth is serving a stew nobody can identify but everyone can identify one ingredient from home in.",
        "'It tastes Human until the aftertaste, then it becomes somebody else's childhood.'",
        "Steam from the communal pot carries herbs, smoke, mushroom, and something peppery enough to make strangers compare guesses.",
    ),
    DailyTexture(
        "veyra_lost_glove", "social", VEYRA_PUBLIC_HEARTH_KEY, "Veyra Public Hearth",
        "A single enormous Troll glove has been pinned to the hearth board with increasingly elaborate ownership theories.",
        "'The glove has had three claimed owners and none of them has the other glove.'",
        "A huge green-dyed glove hangs from the notice rail beneath a card reading: YOURS? PROVE IT.",
    ),
    DailyTexture(
        "sablewater_frog_chorus", "wildlife", SABLEWATER_REED_FARMS_KEY, "Sablewater Reed Farms",
        "The Reed Farms frogs have reached the part of the season where conversation requires shouting.",
        "'You stop hearing them after an hour. Then one stops and suddenly you hear everything.'",
        "Frogs pulse from ditch to ditch in overlapping waves, as if the whole floodplain is breathing through small throats.",
    ),
    DailyTexture(
        "eelmarket_blue_rope", "trade", SABLEWATER_EEL_DOCK_KEY, "Eelmarket Dock",
        "Eelmarket has acquired a shipment of blue rope so bright nobody trusts it near serious boats.",
        "'It holds the same as brown rope. That has not helped its reputation.'",
        "A coil of violently blue rope sits on the dock while every passing worker finds a reason to comment on it.",
    ),
    DailyTexture(
        "willow_ferry_story", "culture", SABLEWATER_WILLOW_FERRY_KEY, "Willow Ferry",
        "The Willow Ferry crew is retelling the same flood story, but today's version contains a suspiciously larger fish.",
        "'By next week the fish will own the ferry.'",
        "A ferryman demonstrates the alleged size of a long-ago fish with both arms while the other crew members quietly make the gesture larger.",
    ),
    DailyTexture(
        "heron_flat_feather", "wildlife", SABLEWATER_HERON_FLATS_KEY, "Heron Flats",
        "A pale heron feather has become the subject of an earnest argument about luck at the flats.",
        "'Lucky if you find it. Unlucky if the heron is still attached.'",
        "A long white feather rolls end over end through the grass, repeatedly almost caught and then taken by the wind again.",
    ),
    DailyTexture(
        "waymeet_old_coin", "history", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard",
        "Someone found an obsolete road token under a Commonhouse bench and six people remember six different uses for it.",
        "'It was a toll token.' 'Meal chit.' 'Laundry mark.' 'You are all wrong.'",
        "A worn brass disc passes from hand to hand. Each person turns it over as if the reverse side might settle the argument.",
    ),
    DailyTexture(
        "veyra_paper_birds", "culture", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing",
        "Paper birds have appeared along Grand Crossing, folded from discarded freight receipts.",
        "'Ledger waste becoming art is either charming or an accounting offense.'",
        "Tiny paper birds perch in bolt holes and rail gaps, each one carrying fragments of old cargo numbers on its wings.",
    ),
    DailyTexture(
        "greywake_bootprints", "travel", GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp",
        "A dozen unfamiliar bootprints crossed camp before dawn and nobody agrees which road they took out.",
        "'Travelers, scouts, smugglers, surveyors. Depends which banner you ask.'",
        "Fresh mud tracks cut through three camp jurisdictions and vanish beneath the churn of ordinary traffic.",
    ),
    DailyTexture(
        "brassmarket_language", "culture", VEYRA_BRASSMARKET_KEY, "Veyra Brassmarket",
        "A Brassmarket stall has started labeling prices in four scripts and one set of Goblin tally scratches.",
        "'The tally scratches are the only part nobody has misread yet.'",
        "Price cards hang in several scripts, plus a row of notches that somehow communicates itself perfectly to every impatient customer.",
    ),
    DailyTexture(
        "commonhouse_chair", "social", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard",
        "The Commonhouse has repaired the same crooked chair again and left the old repair layers visible.",
        "'That chair is more patch than chair. It belongs here.'",
        "A famously crooked chair now has a new brace screwed over three older braces. Someone has painted TODAY on the newest one.",
    ),
    DailyTexture(
        "reed_farm_kite", "culture", SABLEWATER_REED_FARMS_KEY, "Sablewater Reed Farms",
        "A child's reed-paper kite has been stuck above the drainage ditch since breakfast.",
        "'Every adult has offered advice. None have offered to climb.'",
        "A red paper kite jerks stubbornly from a willow branch while farmhands pretend not to monitor its rescue prospects.",
    ),
    DailyTexture(
        "lantern_market_measure", "craft", WAYMEET_LANTERN_MARKET_KEY, "Waymeet Lantern Market",
        "A Dwarf measure inspector and a Goblin scoop-maker are publicly proving both of their tools are correct.",
        "'They have reached the dangerous stage where both sides have produced paperwork.'",
        "Grain is poured from scoop to cup to scale under the attention of a growing and completely unhelpful audience.",
    ),
    DailyTexture(
        "veyra_hearth_letters", "social", VEYRA_PUBLIC_HEARTH_KEY, "Veyra Public Hearth",
        "The hearth scribe is helping travelers write letters home in languages they can speak but never learned to write.",
        "'Half the job is spelling names. The other half is pretending not to hear the personal parts.'",
        "A public scribe pauses over a page while a road-worn traveler slowly dictates a message meant for somewhere far from Veyra.",
    ),
)


AMBIENT_SCENES: tuple[AmbientScene, ...] = (
    AmbientScene("commonhouse_breakfast", WAYMEET_COMMONHOUSE_KEY, ("morning",), "Someone carries six breakfast bowls at once, loses one spoon, and never breaks stride."),
    AmbientScene("commonhouse_evening", WAYMEET_COMMONHOUSE_KEY, ("evening", "night"), "A table near the wall has become an improvised card game between people who do not share a first language but apparently share accusations of cheating."),
    AmbientScene("lantern_pack", WAYMEET_LANTERN_MARKET_KEY, ("day",), "A merchant kneels on a crate to repack another merchant's goods more efficiently, charging advice by the knot."),
    AmbientScene("briar_birds", WAYMEET_BRIARCUT_KEY, ("morning", "day"), "Small field birds rise all at once, circle once above the road, and settle fifty paces farther on."),
    AmbientScene("broken_mile_wheel", WAYMEET_BROKEN_MILE_KEY, ("day",), "Two travelers roll a replacement cart wheel past you while debating whether the old wheel failed from age or insult."),
    AmbientScene("three_banner_soup", GREYWAKE_THREE_BANNER_KEY, ("evening",), "Three cooking fires produce three versions of the same thin road soup. Everyone claims theirs is the practical one."),
    AmbientScene("signal_dawn", GREYWAKE_SIGNAL_HILL_KEY, ("morning",), "The first signal flags of the day snap open against the pale sky and are answered from somewhere too distant to see."),
    AmbientScene("crossing_porters", VEYRA_GRAND_CROSSING_KEY, ("day",), "A chain of porters crosses around you in practiced silence, each carrying one absurdly specific piece of somebody else's future."),
    AmbientScene("brassmarket_close", VEYRA_BRASSMARKET_KEY, ("evening",), "Stall shutters come down in an uneven wave while the last buyers suddenly remember everything they meant to purchase."),
    AmbientScene("public_hearth_night", VEYRA_PUBLIC_HEARTH_KEY, ("night",), "The Public Hearth has gone quiet enough that strangers are sharing the same fire without needing to fill the silence."),
    AmbientScene("reedfarm_morning", SABLEWATER_REED_FARMS_KEY, ("morning",), "Farm workers test the ditch depth with marked poles and compare today's mud line to yesterday's."),
    AmbientScene("eelmarket_day", SABLEWATER_EEL_DOCK_KEY, ("day",), "A fish crate changes hands four times before reaching the boat it was apparently meant for all along."),
    AmbientScene("willow_evening", SABLEWATER_WILLOW_FERRY_KEY, ("evening",), "The ferry chain comes in dripping and the crew listens to its links one by one before tying off for the next crossing."),
    AmbientScene("heron_dusk", SABLEWATER_HERON_FLATS_KEY, ("evening",), "A line of herons lifts from the wet grass in sequence, each bird following the next into the darkening sky."),
)


PELL = ScheduledVisitor(
    key="pell_roadsong",
    name="Pell Roadsong",
    aliases=("pell", "roadsong", "singer", "bard"),
    role="traveling singer and collector of road verses",
    presence="Pell Roadsong is here with a scarred little travel-lute and the expression of someone collecting material.",
    talk_lines=(
        "'Every road song is wrong by the third town. That is how you know people kept singing it.'",
        "'I do not collect the best version. I collect the version people argue about.'",
        "'A song is a cheap way to carry a place somewhere else. Cheap until the tavern asks for a cover charge.'",
        "'Waymeet taught me that every people has a verse about bad weather and none of them agree what bad weather is.'",
    ),
)
SELLA = ScheduledVisitor(
    key="sella_marshlight",
    name="Sella Marshlight",
    aliases=("sella", "marshlight", "courier"),
    role="road courier who notices more than she reports",
    presence="Sella Marshlight is here sorting waxed message slips by destination instead of importance.",
    talk_lines=(
        "'Roads tell on themselves. Fresh wheel cuts, wet boots, empty feed bins. You can know a crowd is coming before you see one.'",
        "'If you want a secret, ask a tavern. If you want the truth, ask who just bought six spare axles.'",
        "'I carry sealed letters. The roads around them are not sealed at all.'",
        "'Greywake is calm today. Which means everyone is using the quiet to prepare for their preferred next problem.'",
    ),
)
CHIV = ScheduledVisitor(
    key="chiv_copperbell",
    name="Chiv Copperbell",
    aliases=("chiv", "copperbell", "tinker"),
    role="Goblin repairer following work instead of owning a shop",
    presence="Chiv Copperbell is here with a tool roll, three borrowed screws, and no fixed opinion about where his workshop is.",
    talk_lines=(
        "'Permanent workshop? Then people bring you broken things. Moving workshop? You find broken things before they become customers.'",
        "'I repaired a Dwarf hinge yesterday. He said it was temporary. Temporary has been opening his door for six months.'",
        "'If a thing is useless, first ask who decided the use.'",
        "'Veyra has excellent rubbish. That is praise.'",
    ),
)
HESTA = ScheduledVisitor(
    key="hesta_ashcart",
    name="Hesta Ashcart",
    aliases=("hesta", "ashcart", "weekly merchant", "factor"),
    role="weekly road factor whose little wagon never stays two days",
    presence="Hesta Ashcart is here beside a narrow gray wagon. People greet her like someone they expect to miss if they wait until tomorrow.",
    talk_lines=(
        "'I am here one day. That keeps prices honest and conversations short.'",
        "'Nothing on my wagon is unique. I sell distance, mostly.'",
        "'Buy it because you need it, not because I disappear tomorrow. The material will still exist after I leave.'",
    ),
)
VISITORS = (PELL, SELLA, CHIV, HESTA)


WORLD_ARCS: tuple[WorldArc, ...] = (
    WorldArc(
        key="iron_taste_well",
        title="The Iron Taste at Waymeet",
        start_record="Waymeet began drawing metallic-tasting water from the old Commonhouse well and posted cups for comparison rather than closing the road.",
        resolution_record="Waymeet replaced a rusted buried well sleeve, and the Commonhouse water lost its iron taste without anyone discovering a curse.",
        stages=(
            ArcStage("First complaints", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard", "Commonhouse water has developed a metallic taste, and three travelers have independently complained about it.", "'The water tastes like a Dwarf spoon. No offense to Dwarf spoons.'", "A row of labeled cups sits on a bench: WELL, CISTERN, RAIN BARREL. People keep tasting them and making faces."),
            ArcStage("Comparisons", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard", "Waymeet is comparing water from the well, cistern, and rain barrels before anybody decides what is wrong.", "'Hedda says if the rain barrel tastes like iron too, we can blame the sky.'", "A chalk tally beside the sample cups now has columns for taste, color, smell, and unhelpful opinions."),
            ArcStage("Tracing the pipe", WAYMEET_LANTERN_MARKET_KEY, "Waymeet Lantern Market", "Workers have traced the bad taste toward an old buried sleeve beneath Lantern Market.", "'Not poison. Not ghosts. Old iron, probably. We are almost disappointed.'", "Two paving stones are up and a narrow trench exposes pipework older than the market stalls around it."),
            ArcStage("The rusted sleeve", WAYMEET_LANTERN_MARKET_KEY, "Waymeet Lantern Market", "A badly rusted well sleeve has been exposed beneath Lantern Market. Replacement iron is being measured now.", "'You can see daylight through a part that was meant to hold water. Strong diagnosis.'", "A flaked cylinder of old iron lies beside the trench while three craftspeople disagree about which generation installed it."),
            ArcStage("Repair water", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard", "The replacement sleeve is in. The Commonhouse is flushing the well and telling everyone not to judge the first bucket.", "'First bucket came up orange. Second came up less orange. Progress.'", "Bucket after bucket is drawn and poured into the drain while people inspect each one like a jury."),
            ArcStage("Clear again", WAYMEET_COMMONHOUSE_KEY, "Waymeet Commonhouse Yard", "The Commonhouse well is clear again. Someone has left the comparison cups out as a joke.", "'Water tastes like water. Reviews are mixed.'", "The labeled sample cups remain on the bench, all filled from the same repaired well now."),
        ),
    ),
    WorldArc(
        key="stuck_reed_barge",
        title="The Barge in the Reeds",
        start_record="A freight barge grounded sideways in Sablewater and briefly became both an obstacle and an unsolicited public meeting place.",
        resolution_record="Sablewater crews unloaded and refloated the grounded barge, then argued over who had predicted the successful channel first.",
        stages=(
            ArcStage("Grounded", SABLEWATER_WILLOW_FERRY_KEY, "Willow Ferry", "A freight barge has grounded sideways downstream of Willow Ferry and is making every crossing more complicated.", "'Captain says the river moved. River has declined to comment.'", "The stranded barge sits at an embarrassing angle beyond the ferry, its crew walking the deck with sounding poles."),
            ArcStage("Soundings", SABLEWATER_HERON_FLATS_KEY, "Heron Flats", "Sounding crews are walking the shallows around the grounded barge to find a deeper line out.", "'Everybody knows the deep channel until they have to put a loaded boat in it.'", "Marked poles rise and fall through the shallows while somebody on the barge records depths on a slate."),
            ArcStage("Unloading", SABLEWATER_EEL_DOCK_KEY, "Eelmarket Dock", "Half the grounded barge's cargo is being lightered to Eelmarket to reduce its draft.", "'Good news: the cargo is dry. Bad news: now it is our cargo-shaped problem.'", "Dockhands move sacks from a shallow skiff into temporary stacks marked with frantic chalk numbers."),
            ArcStage("First pull", SABLEWATER_WILLOW_FERRY_KEY, "Willow Ferry", "Teams made a first pull on the lightened barge. It moved three feet and produced thirty feet of cheering.", "'Three feet counts. The river did not move it back yet.'", "Fresh rope scars mark the willow posts where the first hauling lines took the strain."),
            ArcStage("Channel opens", SABLEWATER_HERON_FLATS_KEY, "Heron Flats", "The barge is nearly free and the new sounding line is being marked for the final pull.", "'If this works, everyone involved will claim it was their channel.'", "Reed bundles tied to poles trace a crooked temporary channel across the flats."),
            ArcStage("Refloated", SABLEWATER_WILLOW_FERRY_KEY, "Willow Ferry", "The freight barge is moving again. Willow Ferry has its ordinary traffic problem back.", "'She floats. Nobody apologize to the river.'", "Only flattened reeds and deep rope grooves remain where the stranded barge dominated the view."),
        ),
    ),
    WorldArc(
        key="greywake_lamp_line",
        title="The Dark Lamps of Greywake",
        start_record="A sequence of Greywake road lamps began failing early, drawing three different theories from the three-banner camp.",
        resolution_record="Greywake replaced a batch of damp lamp wicks and restored the whole road line without adopting any faction's more dramatic theory.",
        stages=(
            ArcStage("First dark lamps", GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp", "Several road lamps west of camp went dark before the oil was spent.", "'Roadwarden says weather. Ledger says bad stock. Lantern Oath says inspect before choosing.'", "Three extinguished lamp assemblies sit on a table under three separate handwritten labels."),
            ArcStage("Counting failures", GREYWAKE_SIGNAL_HILL_KEY, "Greywake Signal Hill", "Signal Hill is counting which lamps fail first instead of replacing all of them blindly.", "'There is now a map of dark lamps. Naturally, the map has become political.'", "Small black marks creep along a road map as reports arrive from each signal post."),
            ArcStage("Wick test", GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp", "The failed lamps all carry wicks from the same freight bundle. The oil itself burns cleanly.", "'Turns out a wet wick has no faction loyalty.'", "Cut lengths of wick hang above a brazier to dry beside samples from three supply crates."),
            ArcStage("Dry stores", GREYWAKE_THREE_BANNER_KEY, "Three-Banner Camp", "The camp is moving lamp stores off the ground and rebuilding the wet crate platform.", "'Infrastructure triumph: shelves.'", "New timber blocks lift the lamp crates clear of the wet earth by an aggressively measured handspan."),
            ArcStage("Relighting", GREYWAKE_SIGNAL_HILL_KEY, "Greywake Signal Hill", "Fresh dry wicks are moving down the road, lamp by lamp, toward Signal Hill.", "'You can watch the road come back one light at a time.'", "Far down the road, points of amber appear in sequence as each repaired lamp is lit."),
            ArcStage("All lit", GREYWAKE_SIGNAL_HILL_KEY, "Greywake Signal Hill", "The Greywake lamp line is fully lit again, and the argument has already shifted to who diagnosed it first.", "'Dark road fixed. Credit dispute operating normally.'", "The road lamps burn evenly into the distance, boring in exactly the way good infrastructure should be."),
        ),
    ),
    WorldArc(
        key="crossing_hum",
        title="The Hum Under Grand Crossing",
        start_record="Grand Crossing developed a low vibration under heavy freight, prompting Veyra to restrict one lane while several trades listened to the bridge.",
        resolution_record="A worn brace under Grand Crossing was shimmed, pinned, and documented by a mixed Veyra crew; the freight hum stopped.",
        stages=(
            ArcStage("The hum", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "Heavy carts are producing a low hum through one section of Grand Crossing. One freight lane has been narrowed while crews listen.", "'Bridge sings now. Nobody asked it to.'", "A chalk line diverts heavy carts around one plate while workers put ears, rods, and cups against the stone."),
            ArcStage("Load test", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "Crews are running measured carts over the humming section one axle at a time.", "'Nothing inspires public confidence like intentionally driving the heavy cart over the suspicious noise.'", "A freight cart loaded with numbered stone blocks inches forward while six people watch different instruments."),
            ArcStage("Brace found", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "The vibration has been traced to a worn lower brace beneath an old patch plate.", "'Not the whole bridge. One brace. Everyone may resume having smaller opinions.'", "A Goblin repairer surfaces from beneath the bridge holding a worn metal spacer like a courtroom exhibit."),
            ArcStage("Mixed repair", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "A mixed crew is shimming and pinning the worn brace while the restricted lane stays open to foot traffic.", "'Dwarf measure, Goblin shim, Human pin, Sporekin binding. Veyra recipe.'", "Tools from several trades lie in one shared row beside the opened maintenance plate."),
            ArcStage("Quiet test", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "The repaired section survived its first loaded test without the hum. Crews are repeating it anyway.", "'It passed once. Engineers remain emotionally unavailable.'", "The same stone-loaded cart crosses again. This time everybody listens to the absence of sound."),
            ArcStage("Lane reopened", VEYRA_GRAND_CROSSING_KEY, "Veyra Grand Crossing", "The freight lane is fully open again. A new inspection mark has joined the many older hands on Grand Crossing.", "'Bridge stopped singing. Paperwork began.'", "The chalk diversion is being scrubbed away while a fresh inspection plate dries beneath the rail."),
        ),
    ),
)


def _stable_index(seed: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % size


def texture_for_day(day_number: int) -> DailyTexture:
    return DAILY_TEXTURES[_stable_index(f"astralis-texture-v1:{int(day_number)}", len(DAILY_TEXTURES))]


def _arc_for_cycle(cycle: int) -> WorldArc:
    return WORLD_ARCS[_stable_index(f"astralis-arc-v1:{int(cycle)}", len(WORLD_ARCS))]


def arc_state(day_number: int) -> tuple[WorldArc, ArcStage, int, int] | None:
    if day_number <= 0:
        return None
    zero = int(day_number) - 1
    cycle = zero // ARC_CYCLE_DAYS
    offset = zero % ARC_CYCLE_DAYS
    arc = _arc_for_cycle(cycle)
    if offset >= len(arc.stages):
        return None
    return arc, arc.stages[offset], offset, cycle


def _arc_dates(cycle: int, arc: WorldArc) -> tuple[int, int]:
    start = cycle * ARC_CYCLE_DAYS + 1
    return start, start + len(arc.stages) - 1


def _scheduled_location(visitor: ScheduledVisitor, moment: AstralisMoment) -> str | None:
    day = int(moment.day_number)
    hour = int(moment.hour)
    weekday = (day - 1) % 7

    if visitor.key == PELL.key:
        if weekday == 6:
            return SABLEWATER_EEL_DOCK_KEY if 10 <= hour < 18 else None
        west_week = weekday in {0, 1, 2}
        if 9 <= hour < 17:
            return WAYMEET_LANTERN_MARKET_KEY if west_week else VEYRA_GRAND_CROSSING_KEY
        if 17 <= hour < 24:
            return WAYMEET_COMMONHOUSE_KEY if west_week else VEYRA_PUBLIC_HEARTH_KEY
        return None

    if visitor.key == SELLA.key:
        if 6 <= hour < 12:
            return GREYWAKE_THREE_BANNER_KEY
        if 12 <= hour < 18:
            return VEYRA_GRAND_CROSSING_KEY
        if 18 <= hour < 23:
            return VEYRA_PUBLIC_HEARTH_KEY
        return None

    if visitor.key == CHIV.key:
        if 8 <= hour < 14:
            return WAYMEET_LANTERN_MARKET_KEY if weekday % 2 == 0 else VEYRA_BRASSMARKET_KEY
        if 14 <= hour < 19:
            return VEYRA_BRASSMARKET_KEY if weekday % 2 == 0 else WAYMEET_LANTERN_MARKET_KEY
        return None

    if visitor.key == HESTA.key:
        # Hesta is deliberately visible on only one Astralis weekday. Her stock is
        # convenience rather than exclusive content, so missing her is never a penalty.
        if weekday != 3:
            return None
        if 6 <= hour < 12:
            return WAYMEET_LANTERN_MARKET_KEY
        if 12 <= hour < 18:
            return VEYRA_BRASSMARKET_KEY
        if 18 <= hour < 23:
            return WAYMEET_COMMONHOUSE_KEY
        return None

    return None


def visitors_in_room(moment: AstralisMoment, room_key: str) -> tuple[ScheduledVisitor, ...]:
    return tuple(visitor for visitor in VISITORS if _scheduled_location(visitor, moment) == room_key)


def _visitor_matches(visitor: ScheduledVisitor, text: str) -> bool:
    wanted = " ".join(text.strip().lower().split())
    names = {visitor.key.replace("_", " "), visitor.name.lower(), *(alias.lower() for alias in visitor.aliases)}
    return wanted in names


def _weekly_wares(day_number: int) -> tuple[tuple[str, int], ...]:
    rotations = (
        (("iron_ore", 1), ("raw_cotton", 1), ("greenleaf", 1)),
        (("coal", 1), ("cotton_thread", 1), ("lavender_blossom", 1)),
        (("rough_hide", 1), ("bitterroot", 1), ("imp_horn", 2)),
        (("iron_ore", 1), ("greenleaf", 1), ("cotton_thread", 1)),
    )
    week = (int(day_number) - 1) // 7
    return rotations[week % len(rotations)]


def ensure_depth_schema(database) -> None:
    living.ensure_living_world_schema(database)
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS living_depth_seen (
                character_id INTEGER NOT NULL,
                astralis_day INTEGER NOT NULL,
                scene_key TEXT NOT NULL,
                seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, astralis_day, scene_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_board_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                character_name TEXT NOT NULL,
                hub_room_key TEXT NOT NULL,
                posted_day INTEGER NOT NULL,
                expires_day INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_living_board_notes_hub_expiry
            ON living_board_notes(hub_room_key, expires_day, id);
            """
        )


def _mark_seen(session, day: int, scene_key: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    ensure_depth_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO living_depth_seen (character_id, astralis_day, scene_key) VALUES (?, ?, ?)",
            (character.id, int(day), scene_key),
        )
    return bool(cursor.rowcount)


def _record_arc_history(database, moment: AstralisMoment) -> None:
    zero = max(0, int(moment.day_number) - 1)
    cycle = zero // ARC_CYCLE_DAYS
    arc = _arc_for_cycle(cycle)
    start_day, end_day = _arc_dates(cycle, arc)
    if moment.day_number >= start_day:
        living._chronicle_insert(
            database,
            event_key=f"arc:{cycle}:{arc.key}:start",
            day=start_day,
            category="world",
            text=arc.start_record,
        )
    if moment.day_number >= end_day:
        living._chronicle_insert(
            database,
            event_key=f"arc:{cycle}:{arc.key}:resolved",
            day=end_day,
            category="world",
            text=arc.resolution_record,
        )


def _ambient_candidates(moment: AstralisMoment, room_key: str) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    texture = texture_for_day(moment.day_number)
    if texture.room_key == room_key:
        result.append((f"texture:{texture.key}", texture.ambient))
    for scene in AMBIENT_SCENES:
        if scene.room_key == room_key and (not scene.phases or moment.phase in scene.phases):
            result.append((f"ambient:{scene.key}", scene.text))
    state = arc_state(moment.day_number)
    if state is not None:
        arc, stage, index, _cycle = state
        if stage.room_key == room_key:
            result.append((f"arc:{arc.key}:{index}", stage.ambient))
    return tuple(result)


async def _show_ambient_once(session, moment: AstralisMoment) -> None:
    character = getattr(session, "character", None)
    if character is None or living._is_private_room(session):
        return
    candidates = _ambient_candidates(moment, character.current_room or "")
    if not candidates:
        return
    ordered = list(candidates)
    start = _stable_index(
        f"ambient-choice:{moment.day_number}:{character.current_room}:{character.id}", len(ordered)
    )
    ordered = ordered[start:] + ordered[:start]
    for scene_key, text in ordered:
        if _mark_seen(session, moment.day_number, scene_key):
            await session.send(f"\r\n[Around you] {text}\r\n")
            return


async def _show_visitors(session, moment: AstralisMoment) -> None:
    character = getattr(session, "character", None)
    if character is None or living._is_private_room(session):
        return
    for visitor in visitors_in_room(moment, character.current_room or ""):
        await session.send(f"\r\n{visitor.presence}\r\n")


def _clean_note(text: str) -> str:
    text = text.replace("\x1b", "").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    return text.strip()


def _active_notes(session, hub_room_key: str, day: int, limit: int = 12):
    ensure_depth_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT id, character_id, character_name, posted_day, expires_day, body
            FROM living_board_notes
            WHERE hub_room_key = ? AND expires_day >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (hub_room_key, int(day), max(1, min(25, int(limit)))),
        ).fetchall()


def _days_until_note_allowed(session, day: int) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return BOARD_NOTE_COOLDOWN_DAYS
    ensure_depth_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT MAX(posted_day) AS last_day FROM living_board_notes WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    if row is None or row["last_day"] is None:
        return 0
    elapsed = int(day) - int(row["last_day"])
    return max(0, BOARD_NOTE_COOLDOWN_DAYS - elapsed)


async def _pin_note(session, text: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if character.current_room not in living.SOCIAL_HUBS:
        await session.send("Player notes can only be pinned at the Waymeet Commonhouse or Veyra Public Hearth.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    clean = _clean_note(text)
    if not clean:
        await session.send("Write a short note after PIN NOTE.\r\n")
        return
    if len(clean) > BOARD_NOTE_MAX_LENGTH:
        await session.send(f"Keep public notes to {BOARD_NOTE_MAX_LENGTH} characters or fewer.\r\n")
        return
    if re.search(r"(?:https?://|www\.)", clean, re.IGNORECASE):
        await session.send("Public hearth notes are for in-world messages, not external links.\r\n")
        return
    wait = _days_until_note_allowed(session, moment.day_number)
    if wait > 0:
        await session.send(
            f"You recently pinned a public note. Leave the board some breathing room for {wait} more Astralis day{'s' if wait != 1 else ''}.\r\n"
        )
        return
    ensure_depth_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """
            INSERT INTO living_board_notes
            (character_id, character_name, hub_room_key, posted_day, expires_day, body)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                character.id,
                character.name,
                character.current_room,
                moment.day_number,
                moment.day_number + BOARD_NOTE_LIFETIME_DAYS - 1,
                clean,
            ),
        )
    await session.send(
        f"You pin the note beneath the public notices. It will weather off the board after {BOARD_NOTE_LIFETIME_DAYS} Astralis days.\r\n"
    )


async def _remove_note(session, note_id: int) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if character.current_room not in living.SOCIAL_HUBS:
        await session.send("You need to be at a public hearth board to remove a note.\r\n")
        return
    ensure_depth_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT character_id, hub_room_key FROM living_board_notes WHERE id = ?",
            (int(note_id),),
        ).fetchone()
        if row is None or int(row["character_id"]) != int(character.id):
            await session.send("That is not one of your notes.\r\n")
            return
        if str(row["hub_room_key"]) != character.current_room:
            await session.send("That note is pinned at the other public hearth.\r\n")
            return
        db.execute("DELETE FROM living_board_notes WHERE id = ?", (int(note_id),))
    await session.send("You take your note down. The posting cooldown still applies; removing it does not create extra board space for spam.\r\n")


async def _show_player_notes(session) -> None:
    character = getattr(session, "character", None)
    if character is None or character.current_room not in living.SOCIAL_HUBS:
        await session.send("Player notes are read at the Waymeet Commonhouse or Veyra Public Hearth.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    rows = _active_notes(session, character.current_room, moment.day_number)
    await session.send("\r\n--- Notes Left by Travelers ---\r\n")
    if not rows:
        await session.send("No current traveler notes are pinned here.\r\n")
    else:
        for row in rows:
            await session.send(
                f"#{row['id']} {row['character_name']} [Day {row['posted_day']}]: {row['body']}\r\n"
            )
    wait = _days_until_note_allowed(session, moment.day_number)
    if wait:
        await session.send(f"Your next note can be pinned in {wait} Astralis day{'s' if wait != 1 else ''}.\r\n")
    else:
        await session.send(f"PIN NOTE <message> adds one note up to {BOARD_NOTE_MAX_LENGTH} characters.\r\n")
    await session.send("REMOVE NOTE <number> removes your own note. Notes age off after seven Astralis days.\r\n")


async def _keeper_rumor(session) -> None:
    character = getattr(session, "character", None)
    if character is None or character.current_room not in living.SOCIAL_HUBS:
        await session.send("Ask for hearth gossip at the Waymeet Commonhouse or Veyra Public Hearth.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    rows = _active_notes(session, character.current_room, moment.day_number, 6)
    chronicle = living.latest_chronicle(session.database, 4)
    choices: list[tuple[str, str]] = []
    for row in rows:
        choices.append(("note", f"{row['character_name']} pinned this here: \"{row['body']}\""))
    for row in chronicle:
        choices.append(("history", f"The Chronicle says this was worth writing down on Day {row['astralis_day']}: {row['entry_text']}"))
    if not choices:
        texture = texture_for_day(moment.day_number)
        await session.send(f"The keeper dries a cup. \"Quiet board. But people keep mentioning this: {texture.gossip.strip(chr(39))}\"\r\n")
        return
    _kind, line = choices[_stable_index(f"keeper:{moment.day_number}:{character.current_room}:{character.id}", len(choices))]
    await session.send(f"The keeper leans closer. \"{line}\"\r\n")


async def _talk_visitor(session, target: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    present = visitors_in_room(moment, character.current_room or "")
    visitor = next((value for value in present if _visitor_matches(value, target)), None)
    if visitor is None:
        return False
    line = visitor.talk_lines[_stable_index(f"visitor:{visitor.key}:{moment.day_number}:{character.id}", len(visitor.talk_lines))]
    await session.send(f"\r\n{visitor.name} says, {line}\r\n")
    if visitor.key == HESTA.key:
        await session.send("Hesta is today's weekly factor. BROWSE HESTA shows her ordinary road stock.\r\n")
    return True


async def _browse_hesta(session) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    if _scheduled_location(HESTA, moment) != character.current_room:
        return False
    await session.send("\r\n--- Hesta Ashcart's Weekly Wagon ---\r\n")
    for item_key, cost in _weekly_wares(moment.day_number):
        await session.send(f"{living._item_label(item_key)} - {cost} Waymeet Trade Scrip\r\n")
    await session.send("BUY HESTA <item> purchases one. Hesta carries convenience, never exclusive materials.\r\n")
    return True


async def _buy_hesta(session, item_text: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    if _scheduled_location(HESTA, moment) != character.current_room:
        return False
    wanted = living._normalize(item_text)
    match = None
    for item_key, cost in _weekly_wares(moment.day_number):
        if wanted in {living._normalize(item_key), living._normalize(living._item_label(item_key))}:
            match = (item_key, cost)
            break
    if match is None:
        await session.send("Hesta is not carrying that this week. Use BROWSE HESTA.\r\n")
        return True
    item_key, cost = match
    if session.database.item_quantity(character.id, WAYMEET_SCRIP_KEY) < cost:
        await session.send(f"You need {cost} Waymeet Trade Scrip.\r\n")
        return True
    session.database.consume_item(character.id, WAYMEET_SCRIP_KEY, cost)
    session.database.add_item(character.id, item_key, 1)
    await session.send(f"Hesta trades you 1x {living._item_label(item_key)} for {cost} scrip.\r\n")
    return True


async def _show_depth_dispatch(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    texture = texture_for_day(moment.day_number)
    await session.send(
        "\r\nAround the roads:\r\n"
        f"- {texture.dispatch}\r\n"
        f"  Heard around {texture.room_name}.\r\n"
    )
    state = arc_state(moment.day_number)
    if state is not None:
        arc, stage, index, _cycle = state
        await session.send(
            f"\r\nONGOING: {arc.title} — {stage.label} ({index + 1}/{len(arc.stages)})\r\n"
            f"{stage.dispatch}\r\n"
            f"People following it are gathering around {stage.room_name}.\r\n"
        )
    if _scheduled_location(HESTA, moment) is not None:
        where = living.SOCIAL_HUBS.get(_scheduled_location(HESTA, moment), None)
        if where is None:
            if _scheduled_location(HESTA, moment) == WAYMEET_LANTERN_MARKET_KEY:
                where = "Waymeet Lantern Market"
            elif _scheduled_location(HESTA, moment) == VEYRA_BRASSMARKET_KEY:
                where = "Veyra Brassmarket"
        await session.send(f"\r\nWEEKLY ROAD FACTOR: Hesta Ashcart is in {where or 'the public roads'} for part of today.\r\n")


async def _show_depth_gossip(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    texture = texture_for_day(moment.day_number)
    await session.send(texture.gossip + "\r\n")
    state = arc_state(moment.day_number)
    if state is not None:
        _arc, stage, _index, _cycle = state
        await session.send(stage.gossip + "\r\n")


async def _show_depth_board(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if character.current_room not in living.SOCIAL_HUBS:
        await session.send("The public hearth board is at Waymeet Commonhouse or Veyra Public Hearth.\r\n")
        return
    await _show_player_notes(session)
    moment = ASTRALIS_CLOCK.now()
    present = visitors_in_room(moment, character.current_room)
    if present:
        await session.send("\r\nFamiliar travelers currently here:\r\n")
        for visitor in present:
            await session.send(f"- {visitor.name}, {visitor.role}.\r\n")


async def _show_locals(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    moment = ASTRALIS_CLOCK.now()
    present = visitors_in_room(moment, character.current_room or "")
    await session.send("\r\n--- Familiar Travelers Here ---\r\n")
    if not present:
        await session.send("None of the recurring road faces are here right now. They keep their own routes.\r\n")
        return
    for visitor in present:
        await session.send(f"{visitor.name} — {visitor.role}. TALK {visitor.name.split()[0].upper()} to speak.\r\n")


async def _push_depth_gmcp(session) -> None:
    telnet = getattr(session, "telnet", None)
    character = getattr(session, "character", None)
    if telnet is None or character is None or not getattr(telnet, "gmcp_enabled", False):
        return
    moment = ASTRALIS_CLOCK.now()
    texture = texture_for_day(moment.day_number)
    state = arc_state(moment.day_number)
    arc_payload = None
    if state is not None:
        arc, stage, index, _cycle = state
        arc_payload = {
            "key": arc.key,
            "title": arc.title,
            "stage": stage.label,
            "stage_number": index + 1,
            "stage_count": len(arc.stages),
            "summary": stage.dispatch,
            "location": stage.room_name,
        }
    present = visitors_in_room(moment, character.current_room or "")
    note_count = 0
    if character.current_room in living.SOCIAL_HUBS:
        note_count = len(_active_notes(session, character.current_room, moment.day_number, 25))
    await telnet.send_gmcp(
        "Dreams.WorldTexture",
        {
            "day": moment.day_number,
            "nudge": texture.dispatch,
            "category": texture.category,
            "location": texture.room_name,
            "arc": arc_payload,
            "visitors_here": [visitor.name for visitor in present],
            "board_notes_here": note_count,
            "weekly_factor_here": any(visitor.key == HESTA.key for visitor in present),
        },
    )


def _sync_depth(session, moment: AstralisMoment) -> None:
    ensure_depth_schema(session.database)
    _record_arc_history(session.database, moment)


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_living_world_depth_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_living_world_depth_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            character = getattr(self, "character", None)
            if character is None:
                return
            moment = ASTRALIS_CLOCK.now()
            _sync_depth(self, moment)
            await _push_depth_gmcp(self)

        player_session_class.enter_character = enter_character

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            character = getattr(self, "character", None)
            if character is None or living._is_private_room(self):
                return
            moment = ASTRALIS_CLOCK.now()
            _sync_depth(self, moment)
            await _show_visitors(self, moment)
            await _show_ambient_once(self, moment)
            await _push_depth_gmcp(self)

        player_session_class.show_current_room = show_current_room

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_playing_prompt(self)
            return
        moment = ASTRALIS_CLOCK.now()
        _sync_depth(self, moment)

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"today", "dispatch", "world today", "daily dispatch"}:
            await living._show_dispatch(self)
            await _show_depth_dispatch(self)
            await living._push_living_gmcp(self)
            await _push_depth_gmcp(self)
            return
        if normalized in {"gossip", "rumor", "rumors"}:
            await living._show_gossip(self)
            await _show_depth_gossip(self)
            return
        if normalized in {"tavern board", "hearth board", "board today"}:
            if character.current_room in living.SOCIAL_HUBS:
                await living._show_board(self)
                await _show_depth_board(self)
            else:
                await self.send("The public hearth board is at Waymeet Commonhouse or Veyra Public Hearth.\r\n")
            await _push_depth_gmcp(self)
            return
        if normalized in {"board notes", "notes", "traveler notes"}:
            await _show_player_notes(self)
            return
        if normalized.startswith("pin note "):
            await _pin_note(self, stripped[len("pin note "):])
            await _push_depth_gmcp(self)
            return
        match = re.fullmatch(r"(?:remove|unpin|take down) note\s+(\d+)", normalized)
        if match:
            await _remove_note(self, int(match.group(1)))
            await _push_depth_gmcp(self)
            return
        if normalized in {"ask keeper rumor", "keeper rumor", "ask keeper gossip", "hearth rumor"}:
            await _keeper_rumor(self)
            return
        if normalized in {"locals", "familiar travelers", "who visits", "visitors"}:
            await _show_locals(self)
            return

        if normalized in {"browse hesta", "browse ashcart", "hesta wares"}:
            if await _browse_hesta(self):
                return
            await self.send("Hesta Ashcart is not here right now. She makes this circuit only one Astralis day each week.\r\n")
            return
        if normalized.startswith("buy hesta "):
            if await _buy_hesta(self, stripped[len("buy hesta "):]):
                await _push_depth_gmcp(self)
                return
            await self.send("Hesta Ashcart is not here right now.\r\n")
            return

        talk = re.match(r"^(?:talk|speak)(?: to)?\s+(.+)$", normalized)
        if talk and await _talk_visitor(self, talk.group(1)):
            return
        listen = re.match(r"^(?:listen to|listen)\s+(.+)$", normalized)
        if listen and await _talk_visitor(self, listen.group(1)):
            return

        await _delegate_command(self, previous_playing_prompt, command)
        refreshed = self.database.get_character_by_name(character.name)
        if refreshed is not None:
            self.character = refreshed
        await _push_depth_gmcp(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._living_world_depth_runtime_installed = True
