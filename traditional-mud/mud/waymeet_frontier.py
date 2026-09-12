from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


WAYMEET_REGION_KEY = "waymeet_frontier"
WAYMEET_CROSSROADS_KEY = "waymeet_crossroads"
WAYMEET_WEST_ROAD_KEY = "waymeet_west_road"
WAYMEET_GREEN_APPROACH_KEY = "waymeet_green_approach"
WAYMEET_HIGH_ROAD_KEY = "waymeet_high_road"
WAYMEET_MARSH_ROAD_KEY = "waymeet_marsh_road"
WAYMEET_LANTERN_MARKET_KEY = "waymeet_lantern_market"
WAYMEET_COMMONHOUSE_KEY = "waymeet_commonhouse_yard"
WAYMEET_CRAFT_ROW_KEY = "waymeet_hammer_thread_row"
WAYMEET_BROKEN_MILE_KEY = "waymeet_broken_mile"
WAYMEET_BRIARCUT_KEY = "waymeet_briarcut_fields"
WAYMEET_QUARRY_KEY = "waymeet_old_quarry"
WAYMEET_CULVERT_KEY = "waymeet_flooded_culvert"
WAYMEET_GLOAM_MOUTH_KEY = "waymeet_gloam_mouth"

WAYMEET_ROOM_KEYS = (
    WAYMEET_WEST_ROAD_KEY,
    WAYMEET_GREEN_APPROACH_KEY,
    WAYMEET_HIGH_ROAD_KEY,
    WAYMEET_MARSH_ROAD_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_BRIARCUT_KEY,
    WAYMEET_QUARRY_KEY,
    WAYMEET_CULVERT_KEY,
    WAYMEET_GLOAM_MOUTH_KEY,
)

WAYMEET_INTRO_QUEST_KEY = "waymeet_roads_meet_here"
WAYMEET_JACKAL_QUEST_KEY = "waymeet_keep_mile_clear"
WAYMEET_QUARRY_QUEST_KEY = "waymeet_quarry_teeth"
WAYMEET_INTRO_COMPLETE_FLAG = "waymeet_roads_meet_here_complete"
WAYMEET_GLOAM_SEEN_FLAG = "waymeet_gloam_mouth_seen"

WAYMEET_SCRIP_KEY = "waymeet_trade_scrip"
THORNBACK_FANG_KEY = "waymeet_thornback_fang"
SLATEBACK_CLAW_KEY = "waymeet_slateback_claw"
GLOAM_RESIDUE_KEY = "waymeet_gloam_residue"

THORNBACK_JACKAL_KEY = "waymeet_thornback_jackal"
REEDMAW_BOAR_KEY = "waymeet_reedmaw_boar"
SLATEBACK_SKULK_KEY = "waymeet_slateback_skulk"
CULVERT_LURKER_KEY = "waymeet_culvert_lurker"
GLOAM_DELVER_KEY = "waymeet_gloam_delver"

MARSHAL_KEY = "waymeet_marshal_aven_marr"
WARDEN_KEY = "waymeet_warden_korr_snowhand"
FOREMAN_KEY = "waymeet_foreman_hedda_rivetstone"
BROKER_KEY = "waymeet_broker_nix_coil"
PROVISIONER_KEY = "waymeet_provisioner_sevra_lent"


WAYMEET_INTRO_QUEST = QuestDefinition(
    key=WAYMEET_INTRO_QUEST_KEY,
    name="Where the Roads Meet",
    style="structured",
    description=(
        "Waymeet survives because travelers from several homelands keep the same roads open. Marshal Aven Marr needs a newcomer to learn the settlement by helping investigate why carts have begun refusing the Broken Mile after dark."
    ),
    objective_steps=(
        ("talk_marshal", "TALK MARSHAL at Waymeet Crossroads."),
        ("inspect_broken_mile", "Go through Lantern Market to the Broken Mile and EXAMINE COLLAPSE."),
        ("reach_gloam", "Follow the damaged road through the culvert to Gloam Mouth."),
        ("inspect_gloam", "EXAMINE SEALED DOOR at Gloam Mouth."),
        ("return_marshal", "Return to Waymeet Crossroads and TALK MARSHAL."),
        ("complete", "You learned the local roads and found the first evidence that the abandoned Gloamworks below them are not as empty as Waymeet hoped."),
    ),
)

WAYMEET_JACKAL_QUEST = QuestDefinition(
    key=WAYMEET_JACKAL_QUEST_KEY,
    name="Keep the Mile Clear",
    style="repeatable",
    description=(
        "Thornback jackals have learned to stalk stalled wagons along the Broken Mile. Warden Korr pays for three fresh fangs as proof that the road has actually been cleared."
    ),
    objective_steps=(
        ("collect", "Defeat Thornback Jackals around the Broken Mile and bring 3 Thornback Fangs to Warden Korr."),
        ("turn_in", "TALK WARDEN with 3 Thornback Fangs."),
        ("complete", "The road is a little safer for the next caravan. The contract can be taken again."),
    ),
)

WAYMEET_QUARRY_QUEST = QuestDefinition(
    key=WAYMEET_QUARRY_QUEST_KEY,
    name="Teeth in the Quarry",
    style="repeatable",
    description=(
        "Slateback skulks have moved into the old quarry and keep attacking ore crews. Foreman Hedda pays for two heavy claws as proof that the nearest den has been thinned."
    ),
    objective_steps=(
        ("collect", "Defeat Slateback Skulks in the Old Quarry and bring 2 Slateback Claws to Foreman Hedda."),
        ("turn_in", "TALK FOREMAN with 2 Slateback Claws."),
        ("complete", "The quarry crew gets another workable shift. The contract can be taken again."),
    ),
)

WAYMEET_QUESTS = (WAYMEET_INTRO_QUEST, WAYMEET_JACKAL_QUEST, WAYMEET_QUARRY_QUEST)


WAYMEET_SCRIP = ItemDefinition(
    key=WAYMEET_SCRIP_KEY,
    name="Waymeet Trade Scrip",
    description=(
        "A stamped brass chit accepted by the practical merchants around Waymeet. It is not intended as Astralis-wide currency; the settlement issues it for road work and takes it back for common supplies."
    ),
    category="currency",
    tier=1,
)
THORNBACK_FANG = ItemDefinition(
    key=THORNBACK_FANG_KEY,
    name="Thornback Fang",
    description="A long yellow fang from one of the jackals hunting the Broken Mile. Waymeet wardens accept fresh fangs as bounty proof.",
    category="trophy",
    tier=1,
)
SLATEBACK_CLAW = ItemDefinition(
    key=SLATEBACK_CLAW_KEY,
    name="Slateback Claw",
    description="A stone-scored claw from a quarry skulk, thick enough to leave pale grooves in slate.",
    category="trophy",
    tier=1,
)
GLOAM_RESIDUE = ItemDefinition(
    key=GLOAM_RESIDUE_KEY,
    name="Gloam Residue",
    description=(
        "A brittle violet-black crust left on creatures lingering near the sealed Gloamworks. It smells faintly of wet iron and cold ash. Nobody at Waymeet yet knows what it is."
    ),
    category="material",
    tier=1,
)
WAYMEET_ITEMS = (WAYMEET_SCRIP, THORNBACK_FANG, SLATEBACK_CLAW, GLOAM_RESIDUE)


THORNBACK_JACKAL = EnemyDefinition(
    key=THORNBACK_JACKAL_KEY,
    name="Thornback Jackal",
    aliases=("jackal", "thornback", "thornback jackal"),
    description="a rangy roadside jackal with briars and old burrs tangled into the coarse ridge of fur along its spine",
    max_hp=28,
    armor_class=4,
    auto_attack_damage=3,
    auto_attack_interval=3.0,
    xp_reward=20,
    retaliates=True,
    tutorial=False,
)
REEDMAW_BOAR = EnemyDefinition(
    key=REEDMAW_BOAR_KEY,
    name="Reedmaw Boar",
    aliases=("boar", "reedmaw", "reedmaw boar"),
    description="a low swamp boar with reed roots caught around its tusks and black mud armored across its shoulders",
    max_hp=38,
    armor_class=5,
    auto_attack_damage=4,
    auto_attack_interval=3.2,
    xp_reward=28,
    retaliates=True,
    tutorial=False,
)
SLATEBACK_SKULK = EnemyDefinition(
    key=SLATEBACK_SKULK_KEY,
    name="Slateback Skulk",
    aliases=("skulk", "slateback", "slateback skulk"),
    description="a broad six-limbed scavenger whose back plates mimic broken quarry stone until it begins to move",
    max_hp=52,
    armor_class=7,
    auto_attack_damage=5,
    auto_attack_interval=3.1,
    xp_reward=40,
    retaliates=True,
    tutorial=False,
)
CULVERT_LURKER = EnemyDefinition(
    key=CULVERT_LURKER_KEY,
    name="Culvert Lurker",
    aliases=("lurker", "culvert lurker", "water lurker"),
    description="a pale amphibious predator folded into the flooded stone channel, almost invisible until its lidless eyes open",
    max_hp=58,
    armor_class=6,
    auto_attack_damage=6,
    auto_attack_interval=3.4,
    xp_reward=46,
    retaliates=True,
    tutorial=False,
)
GLOAM_DELVER = EnemyDefinition(
    key=GLOAM_DELVER_KEY,
    name="Gloam-Touched Delver",
    aliases=("delver", "gloam delver", "gloam-touched delver"),
    description=(
        "a molelike tunnel beast the size of a large dog, its digging claws crusted in violet-black residue and its whiskers twitching toward the sealed works below"
    ),
    max_hp=70,
    armor_class=8,
    auto_attack_damage=7,
    auto_attack_interval=3.0,
    xp_reward=60,
    retaliates=True,
    tutorial=False,
)
WAYMEET_ENEMIES = (THORNBACK_JACKAL, REEDMAW_BOAR, SLATEBACK_SKULK, CULVERT_LURKER, GLOAM_DELVER)


MARSHAL = NpcDefinition(
    key=MARSHAL_KEY,
    name="Marshal Aven Marr",
    short_description="a road marshal studying four different regional maps pinned together with string and knife points",
    room_key=WAYMEET_CROSSROADS_KEY,
    role="Waymeet road marshal and shared-world introduction",
    dialogue=(
        "Aven taps the place where four maps overlap. 'Every homeland draws itself in the middle. Roads are where those drawings have to agree.'",
        "'Waymeet is not neutral because nobody argues here. It is neutral because everybody needs the bridge repaired afterward.'",
    ),
)
WARDEN = NpcDefinition(
    key=WARDEN_KEY,
    name="Warden Korr Snowhand",
    short_description="a Troll road warden mending a leather boot while watching the Broken Mile instead of the people passing him",
    room_key=WAYMEET_BROKEN_MILE_KEY,
    role="repeatable road-clearance contract giver",
    dialogue=(
        "Korr knots the boot lace. 'Three fangs means three jackals that will not test the next broken axle. I pay for proof, not stories.'",
        "'Road work is mostly doing small ugly things before they become large expensive things.'",
    ),
)
FOREMAN = NpcDefinition(
    key=FOREMAN_KEY,
    name="Foreman Hedda Rivetstone",
    short_description="a Dwarf quarry foreman with chalk on one sleeve and a cracked slate helmet tucked beneath the other arm",
    room_key=WAYMEET_QUARRY_KEY,
    role="repeatable quarry contract giver",
    dialogue=(
        "Hedda marks another shift box. 'The stone is useful. The things pretending to be stone are less useful.'",
        "'Two claws buys me enough quiet to put a crew back on the lower face.'",
    ),
)
BROKER = NpcDefinition(
    key=BROKER_KEY,
    name="Nix Coil",
    short_description="a Goblin broker sitting behind neat stacks of ore, fiber, herbs, and locally stamped brass scrip",
    room_key=WAYMEET_LANTERN_MARKET_KEY,
    role="raw-material merchant",
    dialogue=(
        "Nix flicks a brass chit onto the counter. 'Waymeet scrip comes from road work and goes back into road supplies. Nice little circle.'",
        "'BROWSE NIX if you want the boring useful stuff. Boring useful stuff keeps adventurers alive.'",
    ),
)
PROVISIONER = NpcDefinition(
    key=PROVISIONER_KEY,
    name="Sevra Lent",
    short_description="an Undead provisioner calmly counting ingots and thread bundles with chalk marks on one forearm",
    room_key=WAYMEET_LANTERN_MARKET_KEY,
    role="processed-material merchant",
    dialogue=(
        "Sevra stacks two iron ingots. 'Nix sells beginnings. I sell the part after somebody else did a little work.'",
        "'BROWSE SEVRA. Two scrip for processed stock. Convenience should cost something, but not your entire afternoon.'",
    ),
)
WAYMEET_NPCS = (MARSHAL, WARDEN, FOREMAN, BROKER, PROVISIONER)


WAYMEET_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=WAYMEET_WEST_ROAD_KEY,
        name="Westbound Common Road",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "Two long-distance roads become one broad packed track here. Blackwall freight marks mix with Dwarven wheel gauges in the mud, and roadside stones carry repairs in several masonry traditions. East lies Waymeet proper; south, lantern roofs show through the trees."
        ),
        exits={"east": WAYMEET_CROSSROADS_KEY, "south": WAYMEET_LANTERN_MARKET_KEY, "west": "human_outer_caravan_road", "north": "dwarf_upper_freight_deck"},
        tags=("shared_world", "road", "human_route", "dwarf_route", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_GREEN_APPROACH_KEY,
        name="Green Approach",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "The southern road narrows between old trees before opening toward Waymeet. Forest Elf trail marks share trunks with small Sporekin route sigils pressed into damp bark. The road is deliberately left broad enough that neither system has to erase the other."
        ),
        exits={"east": WAYMEET_CROSSROADS_KEY, "north": WAYMEET_COMMONHOUSE_KEY, "south": "forest_elf_briarshadow_thicket", "west": "sporekin_memory_path"},
        tags=("shared_world", "road", "forest_elf_route", "sporekin_route", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_HIGH_ROAD_KEY,
        name="High Road Descent",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "A steep road drops from stony high country into the Waymeet basin. Moon Elf survey stakes and Troll cairns occasionally occupy the same patch of ground and disagree about the prettiest route while agreeing exactly where the dangerous ice forms."
        ),
        exits={"south": WAYMEET_CROSSROADS_KEY, "north": "moon_elf_wind_terrace", "west": "troll_stonejaw_pass"},
        tags=("shared_world", "road", "moon_elf_route", "troll_route", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_MARSH_ROAD_KEY,
        name="Marsh Causeway",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "A raised causeway crosses wet ground east of Waymeet. Goblin repair plates reinforce the pilings while smoked-glass Necropolis lamps mark the dry night line. Frogs call under the boards. The shared road lies west."
        ),
        exits={"west": WAYMEET_CROSSROADS_KEY, "east": "goblin_floodgate_walk", "south": "undead_sunscar_road", "north": WAYMEET_CRAFT_ROW_KEY},
        tags=("shared_world", "road", "goblin_route", "undead_route", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_CROSSROADS_KEY,
        name="Waymeet Crossroads",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "Four roads meet around a weather-dark stone post covered in distance marks, repair notices, caravan ribbons, and directions written in several scripts. Waymeet grew around the practical fact that Humans, Elves, Dwarves, Goblins, Trolls, Undead, and Sporekin all eventually needed the same bridge, dry bed, meal, witness, or spare wheel. Nobody designed the settlement to symbolize cooperation. Cooperation happened because the road kept breaking."
        ),
        exits={"west": WAYMEET_WEST_ROAD_KEY, "south": WAYMEET_GREEN_APPROACH_KEY, "north": WAYMEET_HIGH_ROAD_KEY, "east": WAYMEET_MARSH_ROAD_KEY},
        npc_keys=(MARSHAL_KEY,),
        tags=("shared_world", "social_hub", "crossroads", "safe", "level_2_5"),
    ),
    RoomDefinition(
        key=WAYMEET_LANTERN_MARKET_KEY,
        name="Lantern Market",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "A low market has accumulated beside the western road under a roofline of mismatched awnings. The stalls favor supplies travelers actually run out of: ore, thread, herbs, lamp oil, rope, boot nails, dry socks, and arguments about maps. Small brass Waymeet chits change hands here for road work."
        ),
        exits={"north": WAYMEET_WEST_ROAD_KEY, "east": WAYMEET_CRAFT_ROW_KEY, "south": WAYMEET_BROKEN_MILE_KEY},
        npc_keys=(BROKER_KEY, PROVISIONER_KEY),
        tags=("shared_world", "market", "merchant", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_COMMONHOUSE_KEY,
        name="Commonhouse Yard",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "Behind a long public house, rain barrels, hitching posts, benches, cookfires, and laundry lines turn a plain yard into Waymeet's unofficial social square. Travelers who would be conspicuous in one another's homelands become merely another wet person looking for a seat."
        ),
        exits={"south": WAYMEET_GREEN_APPROACH_KEY, "east": WAYMEET_CRAFT_ROW_KEY},
        tags=("shared_world", "social", "rest", "safe", "meeting_place"),
    ),
    RoomDefinition(
        key=WAYMEET_CRAFT_ROW_KEY,
        name="Hammer and Thread Row",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "Open-front work bays line a short muddy lane: a forge, sewing tables, repair benches, and a covered rack where travelers can leave ordinary work for specialists. The tools are communal enough for beginners and busy enough that experienced players have a reason to linger near one another."
        ),
        exits={"west": WAYMEET_COMMONHOUSE_KEY, "south": WAYMEET_MARSH_ROAD_KEY, "north": WAYMEET_LANTERN_MARKET_KEY},
        tags=("shared_world", "crafting", "forge", "loom", "safe"),
    ),
    RoomDefinition(
        key=WAYMEET_BROKEN_MILE_KEY,
        name="The Broken Mile",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "South of the market, the old trade road sags where a section of buried masonry collapsed after heavy rain. Wagon traffic has carved a rough detour through weeds and thorn. Jackal tracks circle the places where carts are forced to slow. West lies abandoned fieldland; north returns to the market; eastward the damaged road climbs toward an old quarry."
        ),
        exits={"north": WAYMEET_LANTERN_MARKET_KEY, "west": WAYMEET_BRIARCUT_KEY, "east": WAYMEET_QUARRY_KEY},
        npc_keys=(WARDEN_KEY,),
        enemy_keys=(THORNBACK_JACKAL_KEY,),
        tags=("shared_world", "combat", "road_problem", "level_2"),
    ),
    RoomDefinition(
        key=WAYMEET_BRIARCUT_KEY,
        name="Briarcut Fields",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "Old farm strips lie half reclaimed by briar and reed. Cotton still volunteers in dry patches while green medicinal weeds crowd the ditches. Something heavy has been rooting beneath the abandoned fences."
        ),
        exits={"east": WAYMEET_BROKEN_MILE_KEY},
        enemy_keys=(REEDMAW_BOAR_KEY,),
        tags=("shared_world", "combat", "gathering", "level_2_3"),
    ),
    RoomDefinition(
        key=WAYMEET_QUARRY_KEY,
        name="Old Waymeet Quarry",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "A shallow slate quarry cuts into the hillside above the road. Iron-bearing seams and black coal bands show between old extraction scars. Work stopped when stone-colored scavengers began nesting in the lower cuts, but enough useful material remains to keep drawing brave miners back."
        ),
        exits={"west": WAYMEET_BROKEN_MILE_KEY, "east": WAYMEET_CULVERT_KEY},
        npc_keys=(FOREMAN_KEY,),
        enemy_keys=(SLATEBACK_SKULK_KEY,),
        tags=("shared_world", "combat", "mining", "level_3_4"),
    ),
    RoomDefinition(
        key=WAYMEET_CULVERT_KEY,
        name="Flooded Culvert",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "The road crosses an older stone watercourse where floodwater has eaten mortar from the arch. A knee-deep side channel disappears under the hill. The masonry bears tool marks much older than Waymeet and newer scratches leading toward the north bank."
        ),
        exits={"west": WAYMEET_QUARRY_KEY, "north": WAYMEET_GLOAM_MOUTH_KEY},
        enemy_keys=(CULVERT_LURKER_KEY,),
        tags=("shared_world", "combat", "water", "old_masonry", "level_4"),
    ),
    RoomDefinition(
        key=WAYMEET_GLOAM_MOUTH_KEY,
        name="Gloam Mouth",
        region_key=WAYMEET_REGION_KEY,
        description=(
            "A cut-stone service entrance stands in a fold of the hill beyond the culvert, half hidden by moss and old spoil. Two iron doors have been chained shut from the outside, but cold air still breathes through their seam. The lintel reads GLOAMWORKS in worn trade script. Fresh digging scars disappear beneath the threshold."
        ),
        exits={"south": WAYMEET_CULVERT_KEY},
        enemy_keys=(GLOAM_DELVER_KEY,),
        tags=("shared_world", "combat", "dungeon_hint", "danger", "level_5"),
    ),
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


HOMELAND_LINKS: tuple[tuple[str, str, str, str, str], ...] = (
    ("human_outer_caravan_road", "east", WAYMEET_WEST_ROAD_KEY, "Waymeet Road", "human_blackwall_opening_complete"),
    ("dwarf_upper_freight_deck", "south", WAYMEET_WEST_ROAD_KEY, "Common Freight Road", "dwarf_first_obligation_completed"),
    ("forest_elf_briarshadow_thicket", "east", WAYMEET_GREEN_APPROACH_KEY, "Old Boundary Road", "forest_elf_first_walk_completed"),
    ("sporekin_memory_path", "east", WAYMEET_GREEN_APPROACH_KEY, "Surface Trade Path", "sporekin_first_call_answered"),
    ("moon_elf_wind_terrace", "south", WAYMEET_HIGH_ROAD_KEY, "Valley Road", "moon_elf_third_chair_complete"),
    ("troll_stonejaw_pass", "east", WAYMEET_HIGH_ROAD_KEY, "Lowland Cairn Road", "troll_first_cold_complete"),
    ("goblin_floodgate_walk", "east", WAYMEET_MARSH_ROAD_KEY, "Waymeet Causeway", "goblin_rattlefen_opening_complete"),
    ("undead_sunscar_road", "north", WAYMEET_MARSH_ROAD_KEY, "North Trade Road", "undead_opening_complete"),
)


def waymeet_augmentations() -> dict[str, RoomAugmentation]:
    result: dict[str, RoomAugmentation] = {
        WAYMEET_CROSSROADS_KEY: RoomAugmentation(
            features=(
                _feature(
                    "waymeet_stone",
                    "Waymeet Stone",
                    "a weather-dark distance post carrying directions in many scripts",
                    "No script is given pride of place. Human numerals, Dwarven freight marks, Goblin corrections, Elven trail symbols, Troll cairn cuts, Necropolis lamp codes, and tiny Sporekin route impressions have accumulated around one practical statement: the roads all reach here.",
                    aliases=("stone", "waystone", "post", "distance post"),
                ),
                _feature(
                    "road_notice_board",
                    "Road Notice Board",
                    "a public board of repairs, bounties, missing loads, and caravan needs",
                    "Most notices are painfully ordinary: axle wanted, bridge crew needed, three missing sheep, room for two passengers eastbound. One newer notice warns that carts have begun stopping near the Broken Mile after dark and that old Gloamworks masonry may be shifting again.",
                    aliases=("board", "notice board", "notices"),
                ),
            ),
        ),
        WAYMEET_BROKEN_MILE_KEY: RoomAugmentation(
            features=(
                _feature(
                    "broken_mile_collapse",
                    "Road Collapse",
                    "a rain-cut break exposing older fitted stone beneath the trade road",
                    "The collapse is not a simple washout. Beneath the roadbed is a much older fitted ceiling, cracked from below. Fine violet-black dust clings to the newest fracture. Something under the road has been moving upward.",
                    aliases=("collapse", "break", "road collapse", "hole"),
                ),
            ),
        ),
        WAYMEET_GLOAM_MOUTH_KEY: RoomAugmentation(
            features=(
                _feature(
                    "sealed_gloam_door",
                    "Sealed Gloamworks Door",
                    "two chained iron doors breathing cold air through their seam",
                    "The chains are recent Waymeet work. The doors are not. Deep scratches score the inside edge of the threshold, and violet-black residue has collected where something repeatedly brushed past the seam. The draft below carries a slow metallic knock far too regular to be loose stone. This is not an open dungeon yet, but it is very clearly a future problem.",
                    aliases=("door", "doors", "sealed door", "gloamworks", "entrance"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    key="gloam_seen",
                    text="Now that you know what to look for, the residue here matches the dust exposed beneath the Broken Mile.",
                    priority=70,
                    condition=ViewCondition(required_flags=(WAYMEET_GLOAM_SEEN_FLAG,)),
                ),
            ),
        ),
    }

    for room_key, direction, destination, name, flag in HOMELAND_LINKS:
        addition = RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction=direction,
                    destination_key=destination,
                    name=name,
                    travel_text=f"You take the established road toward Waymeet and the first country shared by travelers from several homelands.",
                    condition=ViewCondition(required_flags=(flag,), min_level=2),
                    hidden_when_unavailable=True,
                ),
            ),
        )
        result[room_key] = _merge_augmentation(result.get(room_key), addition)
    return result


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


def install_waymeet_content(world_service=None) -> None:
    for quest in WAYMEET_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    known_items = {item.key for item in crafting.ITEMS}
    additions = tuple(item for item in WAYMEET_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
    crafting.ITEMS_BY_KEY.update({item.key: item for item in WAYMEET_ITEMS})

    for enemy in WAYMEET_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for npc in WAYMEET_NPCS:
        _replace_npc(npc)
    for room in WAYMEET_ROOMS:
        _replace_room(room)

    economy.ROOM_RESOURCE_NODE_KEYS[WAYMEET_BRIARCUT_KEY] = ("cotton_patch", "greenleaf_patch")
    economy.ROOM_RESOURCE_NODE_KEYS[WAYMEET_QUARRY_KEY] = ("iron_vein", "coal_seam")
    economy.ROOM_RESOURCE_NODE_KEYS[WAYMEET_CULVERT_KEY] = ("bitterroot_cluster",)
    economy.ROOM_STATIONS[WAYMEET_CRAFT_ROW_KEY] = ("forge", "loom")

    if world_service is None:
        return
    for room in WAYMEET_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in waymeet_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*WAYMEET_ROOM_KEYS, *(entry[0] for entry in HOMELAND_LINKS)):
            cache.pop(room_key, None)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _in_waymeet(session) -> bool:
    return bool(session.character and (session.character.current_room or "") in WAYMEET_ROOM_KEYS)


def _quest(session, quest_key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, quest_key)


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _ensure_intro(session) -> bool:
    if session.character is None or not _in_waymeet(session):
        return False
    if WAYMEET_INTRO_COMPLETE_FLAG in session.database.list_flags(session.character.id):
        return False
    if _quest(session, WAYMEET_INTRO_QUEST_KEY) is not None:
        return False
    session.database.start_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY, "talk_marshal")
    return True


def _restart_repeatable(session, quest_key: str) -> None:
    assert session.character is not None
    with session.database.connect() as db:
        db.execute(
            """
            INSERT INTO character_quests (character_id, quest_key, status, current_step)
            VALUES (?, ?, 'active', 'collect')
            ON CONFLICT(character_id, quest_key) DO UPDATE SET
                status = 'active', current_step = 'collect',
                started_at = CURRENT_TIMESTAMP, completed_at = NULL
            """,
            (session.character.id, quest_key),
        )


def _award(session, xp: int, scrip: int) -> int:
    assert session.character is not None
    old_level = session.character.level
    new_level = session.database.add_experience(session.character.id, xp)
    session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, scrip)
    _refresh_character(session)
    return max(0, new_level - old_level)


async def _talk_marshal(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_CROSSROADS_KEY:
        return False
    quest = _quest(session, WAYMEET_INTRO_QUEST_KEY)
    if quest is None:
        _ensure_intro(session)
        quest = _quest(session, WAYMEET_INTRO_QUEST_KEY)
    if quest is None:
        return False
    if quest["status"] == "completed":
        await session.send("Aven looks over the patched road reports. 'If you want more work, Korr watches the Broken Mile and Hedda is still hiring claws out of the quarry.'\r\n")
        return True
    step = quest["current_step"]
    if step == "talk_marshal":
        session.database.advance_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY, "inspect_broken_mile")
        await session.send(
            "Aven pins a fresh cart report over an older one. 'Three wagons stopped on the Broken Mile this week. Drivers blame jackals. Jackals do not crack buried masonry from underneath.'\r\n"
            "'Go south through Lantern Market. EXAMINE COLLAPSE before you decide what caused it.'\r\n"
        )
        return True
    if step == "return_marshal":
        session.database.complete_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY)
        session.database.grant_flag(session.character.id, WAYMEET_INTRO_COMPLETE_FLAG)
        gained = _award(session, 70, 2)
        await session.send(
            "Aven listens without interrupting. When you mention the cold draft and the knocking below the sealed door, the strings between his maps suddenly look less decorative.\r\n"
            "'Then the Gloamworks are our first shared problem, not somebody else's old ruin.'\r\n"
            "Quest complete: Where the Roads Meet. Reward: 70 XP and 2 Waymeet Trade Scrip.\r\n"
        )
        if gained:
            await session.send(f"You gained {gained} level.\r\n")
        return True
    await session.send("Aven points toward the road. 'Finish the part in front of you. The map will still be here.'\r\n")
    return True


async def _inspect_collapse(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_BROKEN_MILE_KEY:
        return False
    quest = _quest(session, WAYMEET_INTRO_QUEST_KEY)
    if not quest or quest["status"] != "active" or quest["current_step"] != "inspect_broken_mile":
        return False
    session.database.advance_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY, "reach_gloam")
    await session.send(
        "You kneel at the broken edge. Rain damage explains the loose soil, but not the fitted ceiling beneath it. One slab is cracked upward from below. Violet-black dust marks the fracture.\r\n"
        "The old watercourse east of the quarry runs toward the same hill. Quest updated: Where the Roads Meet.\r\n"
    )
    return True


async def _inspect_gloam(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_GLOAM_MOUTH_KEY:
        return False
    quest = _quest(session, WAYMEET_INTRO_QUEST_KEY)
    if not quest or quest["status"] != "active" or quest["current_step"] != "inspect_gloam":
        return False
    session.database.grant_flag(session.character.id, WAYMEET_GLOAM_SEEN_FLAG)
    session.database.advance_quest(session.character.id, WAYMEET_INTRO_QUEST_KEY, "return_marshal")
    await session.send(
        "The chains are intact. The cold draft comes from below them anyway. Violet-black residue matches the dust under the Broken Mile, and from somewhere deep past the doors comes a slow metal knock: three beats, silence, three beats.\r\n"
        "Whatever the Gloamworks were, something below still reaches the road above. Return to Marshal Aven.\r\n"
    )
    return True


async def _talk_warden(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_BROKEN_MILE_KEY:
        return False
    quest = _quest(session, WAYMEET_JACKAL_QUEST_KEY)
    if quest is None or quest["status"] == "completed":
        _restart_repeatable(session, WAYMEET_JACKAL_QUEST_KEY)
        quest = _quest(session, WAYMEET_JACKAL_QUEST_KEY)
        await session.send("Korr holds up three fingers. 'Three Thornback Fangs. Bring them fresh enough that I know the road got quieter today.'\r\n")
    quantity = session.database.item_quantity(session.character.id, THORNBACK_FANG_KEY)
    if quantity < 3:
        await session.send(f"Keep the Mile Clear: {quantity}/3 Thornback Fangs. Thornbacks hunt this stretch repeatedly.\r\n")
        return True
    session.database.consume_item(session.character.id, THORNBACK_FANG_KEY, 3)
    session.database.complete_quest(session.character.id, WAYMEET_JACKAL_QUEST_KEY)
    gained = _award(session, 35, 1)
    await session.send("Korr counts the three fangs, wraps them in scrap cloth, and hands over a brass chit. Repeatable contract complete: 35 XP and 1 Waymeet Trade Scrip. TALK WARDEN again whenever you want another run.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    return True


async def _talk_foreman(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_QUARRY_KEY:
        return False
    quest = _quest(session, WAYMEET_QUARRY_QUEST_KEY)
    if quest is None or quest["status"] == "completed":
        _restart_repeatable(session, WAYMEET_QUARRY_QUEST_KEY)
        quest = _quest(session, WAYMEET_QUARRY_QUEST_KEY)
        await session.send("Hedda taps two chalk marks onto her slate. 'Two Slateback Claws. That is enough evidence for one safer shift.'\r\n")
    quantity = session.database.item_quantity(session.character.id, SLATEBACK_CLAW_KEY)
    if quantity < 2:
        await session.send(f"Teeth in the Quarry: {quantity}/2 Slateback Claws.\r\n")
        return True
    session.database.consume_item(session.character.id, SLATEBACK_CLAW_KEY, 2)
    session.database.complete_quest(session.character.id, WAYMEET_QUARRY_QUEST_KEY)
    gained = _award(session, 45, 1)
    await session.send("Hedda drops the claws into a marked bin and pays one brass chit. Repeatable contract complete: 45 XP and 1 Waymeet Trade Scrip. TALK FOREMAN again to repeat it.\r\n")
    if gained:
        await session.send(f"You gained {gained} level.\r\n")
    return True


RAW_WARES = {
    "iron": ("iron_ore", 1, 1, "Iron Ore"),
    "iron ore": ("iron_ore", 1, 1, "Iron Ore"),
    "cotton": ("raw_cotton", 1, 1, "Raw Cotton"),
    "raw cotton": ("raw_cotton", 1, 1, "Raw Cotton"),
    "herbs": ("greenleaf", 1, 1, "Greenleaf"),
    "greenleaf": ("greenleaf", 1, 1, "Greenleaf"),
    "coal": ("coal", 1, 1, "Coal"),
}
PROCESSED_WARES = {
    "ingot": ("iron_ingot", 1, 2, "Iron Ingot"),
    "iron ingot": ("iron_ingot", 1, 2, "Iron Ingot"),
    "thread": ("cotton_thread", 1, 2, "Cotton Thread"),
    "cotton thread": ("cotton_thread", 1, 2, "Cotton Thread"),
}


async def _browse_market(session, target: str) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_LANTERN_MARKET_KEY:
        return False
    normalized = _normalize(target)
    if not normalized or normalized in {"market", "merchants", "merchant"}:
        await session.send(
            "Waymeet merchants:\r\n"
            "- Nix Coil: raw road supplies. BROWSE NIX.\r\n"
            "- Sevra Lent: processed starter materials. BROWSE SEVRA.\r\n"
            "Waymeet Trade Scrip comes from local road work and repeatable contracts.\r\n"
        )
        return True
    if normalized in {"nix", "nix coil", "broker"}:
        await session.send("Nix Coil - 1 scrip each: BUY IRON, BUY COTTON, BUY HERBS, BUY COAL.\r\n")
        return True
    if normalized in {"sevra", "sevra lent", "provisioner"}:
        await session.send("Sevra Lent - 2 scrip each: BUY INGOT, BUY THREAD.\r\n")
        return True
    return False


async def _buy_market(session, target: str) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_LANTERN_MARKET_KEY:
        return False
    wanted = _normalize(target)
    ware = RAW_WARES.get(wanted) or PROCESSED_WARES.get(wanted)
    if ware is None:
        await session.send("That is not a Waymeet market shorthand. BROWSE NIX or BROWSE SEVRA.\r\n")
        return True
    item_key, quantity, cost, label = ware
    if session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY) < cost:
        await session.send(f"You need {cost} Waymeet Trade Scrip for {label}.\r\n")
        return True
    if not session.database.consume_item(session.character.id, WAYMEET_SCRIP_KEY, cost):
        await session.send("The purchase could not be completed safely.\r\n")
        return True
    session.database.add_item(session.character.id, item_key, quantity)
    await session.send(f"You spend {cost} Waymeet Trade Scrip and receive {quantity}x {label}.\r\n")
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


def install_waymeet_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_waymeet_frontier_runtime_installed", False):
        return
    install_waymeet_content(world_service)

    previous_enter_character = player_session_class.enter_character
    previous_move_character = player_session_class.move_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _ensure_intro(self):
            await self.send("\r\nNew shared-world quest: Where the Roads Meet. Find Marshal Aven at Waymeet Crossroads.\r\n")

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character else None
        await previous_move_character(self, direction)
        if self.character is None or self.character.current_room == before:
            return
        if _ensure_intro(self):
            await self.send("\r\nThe road has finally carried you outside a single homeland. New quest: Where the Roads Meet. Find Marshal Aven at the crossroads.\r\n")
        quest = _quest(self, WAYMEET_INTRO_QUEST_KEY)
        if quest and quest["status"] == "active":
            if self.character.current_room == WAYMEET_GLOAM_MOUTH_KEY and quest["current_step"] == "reach_gloam":
                self.database.advance_quest(self.character.id, WAYMEET_INTRO_QUEST_KEY, "inspect_gloam")
                await self.send("\r\nThe cold draft at Gloam Mouth carries the same mineral smell as the Broken Mile fracture. EXAMINE SEALED DOOR.\r\n")

    async def _finish_enemy_defeat(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish_enemy(self, enemy)
        if not eligible or self.character is None:
            return
        if key == THORNBACK_JACKAL_KEY:
            self.database.add_item(self.character.id, THORNBACK_FANG_KEY, 1)
            await self.send("Bounty proof: 1x Thornback Fang.\r\n")
        elif key == SLATEBACK_SKULK_KEY:
            self.database.add_item(self.character.id, SLATEBACK_CLAW_KEY, 1)
            await self.send("Bounty proof: 1x Slateback Claw.\r\n")
        elif key == GLOAM_DELVER_KEY:
            self.database.add_item(self.character.id, GLOAM_RESIDUE_KEY, 1)
            await self.send("You recover 1x Gloam Residue from the creature's digging claws.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = _normalize(command)

        if normalized in {"talk marshal", "talk aven", "talk to marshal", "talk to aven"} and await _talk_marshal(self):
            return
        if normalized in {"talk warden", "talk korr", "talk to warden", "talk to korr"} and await _talk_warden(self):
            return
        if normalized in {"talk foreman", "talk hedda", "talk to foreman", "talk to hedda"} and await _talk_foreman(self):
            return
        if normalized in {"examine collapse", "look collapse", "examine road collapse", "look road collapse"} and await _inspect_collapse(self):
            return
        if normalized in {"examine sealed door", "look sealed door", "examine door", "look door", "examine gloamworks"} and await _inspect_gloam(self):
            return
        if normalized == "browse":
            if await _browse_market(self, ""):
                return
        if normalized.startswith("browse "):
            if await _browse_market(self, command.strip().split(maxsplit=1)[1]):
                return
        if normalized.startswith("buy "):
            if await _buy_market(self, command.strip().split(maxsplit=1)[1]):
                return
        if normalized in {"waymeet", "waymeet help", "frontier"} and _in_waymeet(self):
            await self.send(
                "Waymeet is the first shared level 2-5 region. TALK MARSHAL for the local story, TALK WARDEN or TALK FOREMAN for repeatable contracts, BROWSE in Lantern Market for merchants, RESOURCES for gathering, and follow the damaged road toward Gloam Mouth for the first dungeon hint.\r\n"
            )
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._waymeet_frontier_runtime_installed = True
