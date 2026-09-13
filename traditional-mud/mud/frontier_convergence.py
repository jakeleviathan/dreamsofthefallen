from __future__ import annotations

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.midgame_three_roads import (
    DWARF_COMPLETE_FLAG,
    DWARF_HUB_KEY,
    FINAL_REQUIRED_FLAGS,
    MERIDIAN_CAMP_KEY,
    MOON_COMPLETE_FLAG,
    MOON_HUB_KEY,
    TROLL_COMPLETE_FLAG,
    TROLL_CLUE_KEY,
)
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FRONTIER_REGION_KEY = "ashcross_frontier"
OUTERWORKS_REGION_KEY = "meridian_outerworks"

ASHCROSS_ROOTROAD_KEY = "ashcross_rootroad"
ASHCROSS_IRON_CAUSEWAY_KEY = "ashcross_iron_causeway"
ASHCROSS_SKYROAD_KEY = "ashcross_skyroad"
ASHCROSS_MILESTONE_KEY = "ashcross_broken_milestone"
ASHCROSS_SUNKEN_WATCH_KEY = "ashcross_sunken_watch"
ASHCROSS_CULVERT_KEY = "ashcross_abandoned_culvert"
ASHCROSS_HUSHWOOD_KEY = "ashcross_hushwood_pocket"
ASHCROSS_GATE_KEY = "ashcross_gate"
ASHCROSS_COMMON_KEY = "ashcross_common"
ASHCROSS_MARKET_KEY = "ashcross_market_row"
ASHCROSS_BUNKHOUSE_KEY = "ashcross_bunkhouse"
ASHCROSS_DELVERS_KEY = "ashcross_delvers_yard"

OUTER_THRESHOLD_KEY = "outerworks_threshold"
OUTER_SURVEY_KEY = "outerworks_survey_gallery"
OUTER_FLOOD_RING_KEY = "outerworks_flood_ring"
OUTER_CISTERN_KEY = "outerworks_cistern"
OUTER_PUMP_KEY = "outerworks_pump_gallery"
OUTER_ROOT_GALLERY_KEY = "outerworks_root_gallery"
OUTER_FOSSIL_BEND_KEY = "outerworks_fossil_bend"
OUTER_SEAM_BALCONY_KEY = "outerworks_seam_balcony"
OUTER_LOCK_APPROACH_KEY = "outerworks_lock_approach"
OUTER_BOSS_KEY = "outerworks_lockwarden_chamber"
OUTER_DEEP_GATE_KEY = "outerworks_deep_seam_gate"

INTRO_QUEST_KEY = "ashcross_town_of_other_roads"
PACK_QUEST_KEY = "ashcross_lost_dispatch"
OUTER_QUEST_KEY = "ashcross_beneath_the_crossing"

INTRO_COMPLETE_FLAG = "ashcross_introduction_complete"
PACK_COMPLETE_FLAG = "ashcross_dispatch_recovered"
OUTER_BOSS_FLAG = "ashcross_outerworks_lockwarden_defeated"
OUTER_COMPLETE_FLAG = "ashcross_outerworks_route_complete"

DELVERS_TOKEN_KEY = "ashcross_delvers_token"
DISPATCH_SATCHEL_KEY = "ashcross_dispatch_satchel"
LOCKWARDEN_PLATE_KEY = "outerworks_lockwarden_plate"

STEWARD_NPC_KEY = "ashcross_steward_sere"
BROKER_NPC_KEY = "ashcross_broker_kell"
LOCKWARDEN_KEY = "outerworks_lockwarden"


INTRO_QUEST = QuestDefinition(
    key=INTRO_QUEST_KEY,
    name="A Town Made of Other Roads",
    style="structured",
    minimum_level=15,
    description=(
        "Three dangerous roads meet at Ashcross, a rough frontier settlement where Troll hunters, "
        "Dwarven freight crews, Moon Elf surveyors, Goblin salvagers, Humans, Forest Elves, Undead, "
        "and Sporekin have learned to share a wall without pretending they share a culture."
    ),
    objective_steps=(
        ("reach_common", "Reach Ashcross Common."),
        ("meet_steward", "TALK SERE in Ashcross Common."),
        ("complete", "Receive Ashcross's local delver token."),
    ),
)

PACK_QUEST = QuestDefinition(
    key=PACK_QUEST_KEY,
    name="The Lost Dispatch",
    style="structured",
    minimum_level=15,
    description=(
        "A courier vanished among the abandoned causeways outside Ashcross. Kell wants the satchel back, "
        "not a heroic story about why it was lost."
    ),
    objective_steps=(
        ("recover_pack", "Search the Sunken Watch for the missing dispatch satchel."),
        ("return_broker", "Return to Kell in the Delvers' Yard."),
        ("complete", "Close the missing-courier contract."),
    ),
)

OUTER_QUEST = QuestDefinition(
    key=OUTER_QUEST_KEY,
    name="Beneath the Crossing",
    style="structured",
    minimum_level=17,
    description=(
        "The old complex beneath Ashcross is not a straight dungeon. Floodworks, fossil-root galleries, "
        "and a sealed inner route loop around one another. Map both loops, break the Lockwarden, report back, "
        "and only then use the deep seam as a route toward the Meridian Vault."
    ),
    objective_steps=(
        ("enter_outerworks", "Descend from the Delvers' Yard into the Outerworks."),
        ("mark_waterline", "At the old cistern, MARK WATERLINE."),
        ("mark_rootline", "At Fossil Bend, MARK ROOTLINE."),
        ("defeat_lockwarden", "Defeat the Outerworks Lockwarden."),
        ("report_route", "Return to Kell in the Delvers' Yard."),
        ("complete", "Open the level 19 route toward the Meridian Vault."),
    ),
)

FRONTIER_QUESTS = (INTRO_QUEST, PACK_QUEST, OUTER_QUEST)


FRONTIER_JACKAL = EnemyDefinition(
    key="ashcross_causeway_jackal",
    name="Causeway Jackal",
    aliases=("jackal", "causeway jackal"),
    description="a rangy ash-gray predator that has learned to hunt between wagon ruts and broken parapets",
    max_hp=270,
    armor_class=13,
    auto_attack_damage=18,
    auto_attack_interval=2.7,
    xp_reward=205,
)
FRONTIER_BRIGAND = EnemyDefinition(
    key="ashcross_roadcut_brigand",
    name="Roadcut Brigand",
    aliases=("brigand", "roadcut brigand", "roadcut"),
    description="an armed toll-thief wearing scavenged pieces from three different trade roads",
    max_hp=340,
    armor_class=15,
    auto_attack_damage=21,
    auto_attack_interval=2.9,
    xp_reward=275,
)
OUTER_SCAVENGER = EnemyDefinition(
    key="outerworks_vault_scavenger",
    name="Vault Scavenger",
    aliases=("scavenger", "vault scavenger"),
    description="a pale many-legged thing that feeds on mineral scale and whatever the old halls leave behind",
    max_hp=390,
    armor_class=16,
    auto_attack_damage=24,
    auto_attack_interval=2.8,
    xp_reward=330,
)
OUTER_SEAM_HUSK = EnemyDefinition(
    key="outerworks_seam_husk",
    name="Seam Husk",
    aliases=("husk", "seam husk"),
    description="a jointed shell of gray mineral and root fiber moving as if pulled by something on the other side of the wall",
    max_hp=455,
    armor_class=17,
    auto_attack_damage=27,
    auto_attack_interval=2.9,
    xp_reward=390,
)
OUTER_LOCKWARDEN = EnemyDefinition(
    key=LOCKWARDEN_KEY,
    name="Outerworks Lockwarden",
    aliases=("lockwarden", "outerworks lockwarden", "warden"),
    description="a broad stone-and-metal custodian whose four locking arms keep trying to close doors that no longer exist",
    max_hp=1080,
    armor_class=19,
    auto_attack_damage=30,
    auto_attack_interval=3.0,
    xp_reward=1800,
)
FRONTIER_ENEMIES = (
    FRONTIER_JACKAL,
    FRONTIER_BRIGAND,
    OUTER_SCAVENGER,
    OUTER_SEAM_HUSK,
    OUTER_LOCKWARDEN,
)


FRONTIER_ITEMS = (
    ItemDefinition(
        DELVERS_TOKEN_KEY,
        "Ashcross Delver Token",
        "A stamped brass token proving that Ashcross's yard has your name, race, and emergency contact written down somewhere.",
        "credential",
        tier=4,
    ),
    ItemDefinition(
        DISPATCH_SATCHEL_KEY,
        "Weathered Dispatch Satchel",
        "A mud-stiff courier satchel recovered from the Sunken Watch; its broken seal carries three road marks.",
        "trophy",
        tier=4,
    ),
    ItemDefinition(
        LOCKWARDEN_PLATE_KEY,
        "Lockwarden Keyplate",
        "A heavy plate taken from the Outerworks Lockwarden. Its grooves match no modern key or gear standard.",
        "trophy",
        tier=4,
    ),
)


STEWARD_NPC = NpcDefinition(
    key=STEWARD_NPC_KEY,
    name="Steward Sere",
    short_description="a tired frontier steward wearing three different road badges and none above the others",
    room_key=ASHCROSS_COMMON_KEY,
    role="Ashcross civic steward and first-contact guide",
    dialogue=(
        "'Ashcross is not neutral because everyone agrees. It is neutral because the walls are expensive and winter is worse.'",
        "'Keep your old feuds outside the palisade. Inside, names matter more than ancestry and work matters more than banners.'",
    ),
)
BROKER_NPC = NpcDefinition(
    key=BROKER_NPC_KEY,
    name="Kell Farstep",
    short_description="an Undead contract broker with a wax tablet, a dry sense of humor, and no need for a bunk",
    room_key=ASHCROSS_DELVERS_KEY,
    role="frontier contract broker and Outerworks expedition coordinator",
    dialogue=(
        "'I do not pay for bravery. I pay for things that come back measured, named, and preferably attached to the correct person.'",
        "'The old halls under us loop. If you think a straight corridor proves you understand the place, turn around before it proves otherwise.'",
    ),
)
FRONTIER_NPCS = (STEWARD_NPC, BROKER_NPC)


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
        tags=("shared_world", "frontier_convergence", *tags),
    )


FRONTIER_ROOMS = (
    _room(
        ASHCROSS_ROOTROAD_KEY,
        "Rootroad Verge",
        FRONTIER_REGION_KEY,
        "Troll trail knots and wagon scars share the same deep-forest road here. Ancient roots have lifted whole slabs of an abandoned stone causeway.",
        {"west": TROLL_CLUE_KEY, "east": ASHCROSS_MILESTONE_KEY, "north": ASHCROSS_HUSHWOOD_KEY},
        enemies=(FRONTIER_JACKAL.key,),
        tags=("level_15_16", "deep_forest", "dangerous_road"),
    ),
    _room(
        ASHCROSS_IRON_CAUSEWAY_KEY,
        "Iron Causeway",
        FRONTIER_REGION_KEY,
        "A raised imperial-era road has been repaired with Dwarven rail plate, Goblin rivets, Troll timber, and whatever else survived the last flood.",
        {"north": DWARF_HUB_KEY, "west": ASHCROSS_MILESTONE_KEY, "south": ASHCROSS_CULVERT_KEY},
        enemies=(FRONTIER_BRIGAND.key,),
        tags=("level_15_16", "abandoned_causeway", "dangerous_road"),
    ),
    _room(
        ASHCROSS_SKYROAD_KEY,
        "Fallen Skyroad",
        FRONTIER_REGION_KEY,
        "A steep road falls away from the high country between wind-shaved standing stones. Old Moon Elf altitude marks have been reused as ordinary mileposts.",
        {"north": MOON_HUB_KEY, "down": ASHCROSS_MILESTONE_KEY},
        enemies=(FRONTIER_JACKAL.key,),
        tags=("level_16", "highroad", "dangerous_road"),
    ),
    _room(
        ASHCROSS_MILESTONE_KEY,
        "The Broken Milestone",
        FRONTIER_REGION_KEY,
        "Three roads meet around a waist-high marker whose original inscription has been chiseled away. Fresh arrows point west to roots, east to iron, up toward the skyroad, and south to Ashcross.",
        {"west": ASHCROSS_ROOTROAD_KEY, "east": ASHCROSS_IRON_CAUSEWAY_KEY, "up": ASHCROSS_SKYROAD_KEY, "south": ASHCROSS_GATE_KEY, "down": ASHCROSS_SUNKEN_WATCH_KEY},
        tags=("level_15_16", "road_network", "crossroads"),
    ),
    _room(
        ASHCROSS_SUNKEN_WATCH_KEY,
        "Sunken Watch",
        FRONTIER_REGION_KEY,
        "Half an old watchtower has slid below the roadbed. Broken bunks, courier hooks, and a dry stone shelf remain above a black pool.",
        {"up": ASHCROSS_MILESTONE_KEY},
        enemies=(FRONTIER_BRIGAND.key,),
        tags=("level_15_17", "optional_pocket", "ruin", "secret"),
    ),
    _room(
        ASHCROSS_CULVERT_KEY,
        "Abandoned Culvert",
        FRONTIER_REGION_KEY,
        "A vaulted drainage tunnel runs beneath the Iron Causeway. Old inspection marks vanish behind newer mineral stains and a suspiciously clean straight seam.",
        {"north": ASHCROSS_IRON_CAUSEWAY_KEY},
        enemies=(FRONTIER_JACKAL.key,),
        tags=("level_15_17", "optional_pocket", "ruin", "meridian_hint"),
    ),
    _room(
        ASHCROSS_HUSHWOOD_KEY,
        "Hushwood Pocket",
        FRONTIER_REGION_KEY,
        "A pocket of deep forest sits strangely quiet between two busy roads. The trees grow around an old circular foundation without crossing its center.",
        {"south": ASHCROSS_ROOTROAD_KEY},
        tags=("level_15_17", "optional_pocket", "deep_forest", "meridian_hint"),
    ),
    _room(
        ASHCROSS_GATE_KEY,
        "Ashcross Palisade",
        FRONTIER_REGION_KEY,
        "The frontier wall is an argument in materials: sharpened trunks, riveted plate, scavenged black stone, and repaired watch platforms. Nobody could mistake it for elegant, but it has survived.",
        {"north": ASHCROSS_MILESTONE_KEY, "south": ASHCROSS_COMMON_KEY},
        tags=("level_15_16", "town", "safe"),
    ),
    _room(
        ASHCROSS_COMMON_KEY,
        "Ashcross Common",
        FRONTIER_REGION_KEY,
        "A hard-packed square sits between a cookfire, a message wall, a water pump, and several buildings that have been rebuilt often enough to stop matching. Every ancestry in Astralis appears somewhere in the traffic.",
        {"north": ASHCROSS_GATE_KEY, "east": ASHCROSS_MARKET_KEY, "west": ASHCROSS_BUNKHOUSE_KEY, "south": ASHCROSS_DELVERS_KEY},
        npcs=(STEWARD_NPC_KEY,),
        tags=("level_15_20", "town", "safe", "multiracial_hub", "reputation"),
    ),
    _room(
        ASHCROSS_MARKET_KEY,
        "Market Row",
        FRONTIER_REGION_KEY,
        "Stalls sell trail food, rail fittings, salvage, moon-cloth, bone needles, fungus cakes, and three incompatible kinds of lamp oil. Prices are written before bargaining starts.",
        {"west": ASHCROSS_COMMON_KEY},
        tags=("level_15_20", "town", "safe", "market"),
    ),
    _room(
        ASHCROSS_BUNKHOUSE_KEY,
        "The Bent Nail Bunkhouse",
        FRONTIER_REGION_KEY,
        "One long room has ordinary bunks, a curtained quiet alcove, a stone bench for travelers who do not sleep, and a cellar kept damp enough that Sporekin guests do not have to ask twice.",
        {"east": ASHCROSS_COMMON_KEY},
        tags=("level_15_20", "town", "safe", "rest"),
    ),
    _room(
        ASHCROSS_DELVERS_KEY,
        "Delvers' Yard",
        FRONTIER_REGION_KEY,
        "Rope coils, chalk boards, stretcher poles, survey stakes, and contract slates surround a reinforced stone stair that disappears beneath town. Nobody calls the stair a mine anymore.",
        {"north": ASHCROSS_COMMON_KEY},
        npcs=(BROKER_NPC_KEY,),
        tags=("level_16_20", "town", "safe", "dungeon_hub"),
    ),
)

OUTERWORKS_ROOMS = (
    _room(
        OUTER_THRESHOLD_KEY,
        "Outerworks Threshold",
        OUTERWORKS_REGION_KEY,
        "The town stair ends at fitted gray stone older than Ashcross. Water runs north, fossil roots break through the southern wall, and a survey passage continues east.",
        {"up": ASHCROSS_DELVERS_KEY, "east": OUTER_SURVEY_KEY},
        tags=("level_17_18", "dungeon", "entry"),
    ),
    _room(
        OUTER_SURVEY_KEY,
        "Loop Survey Gallery",
        OUTERWORKS_REGION_KEY,
        "Chalk arrows from generations of delvers point in contradictory directions because both side passages eventually return here. The lock route waits east.",
        {"west": OUTER_THRESHOLD_KEY, "north": OUTER_FLOOD_RING_KEY, "south": OUTER_ROOT_GALLERY_KEY, "east": OUTER_LOCK_APPROACH_KEY},
        enemies=(OUTER_SCAVENGER.key,),
        tags=("level_17_18", "dungeon", "loop_hub"),
    ),
    _room(
        OUTER_FLOOD_RING_KEY,
        "Flood Ring",
        OUTERWORKS_REGION_KEY,
        "A circular service corridor carries ankle-deep water around a dry central wall. Every turn seems to put the survey chalk on the wrong side.",
        {"south": OUTER_SURVEY_KEY, "east": OUTER_CISTERN_KEY},
        enemies=(OUTER_SCAVENGER.key,),
        tags=("level_17_18", "dungeon", "flood_loop"),
    ),
    _room(
        OUTER_CISTERN_KEY,
        "Old Cistern",
        OUTERWORKS_REGION_KEY,
        "A black reservoir fills half the chamber. A modern survey nail has been hammered beside an ancient waterline that remains perfectly level across cracked stone.",
        {"west": OUTER_FLOOD_RING_KEY, "south": OUTER_PUMP_KEY},
        tags=("level_17_18", "dungeon", "flood_loop", "survey_marker"),
    ),
    _room(
        OUTER_PUMP_KEY,
        "Dead Pump Gallery",
        OUTERWORKS_REGION_KEY,
        "Dwarven pumps added centuries later sit idle beside channels that drained themselves long before the machinery arrived.",
        {"north": OUTER_CISTERN_KEY, "west": OUTER_SURVEY_KEY},
        enemies=(OUTER_SEAM_HUSK.key,),
        tags=("level_17_18", "dungeon", "flood_loop"),
    ),
    _room(
        OUTER_ROOT_GALLERY_KEY,
        "Root Gallery",
        OUTERWORKS_REGION_KEY,
        "Dead roots penetrate the ceiling, then bend away from a straight vertical strip of untouched wall.",
        {"north": OUTER_SURVEY_KEY, "east": OUTER_FOSSIL_BEND_KEY},
        enemies=(OUTER_SEAM_HUSK.key,),
        tags=("level_17_18", "dungeon", "root_loop"),
    ),
    _room(
        OUTER_FOSSIL_BEND_KEY,
        "Fossil Bend",
        OUTERWORKS_REGION_KEY,
        "Stone-preserved roots cross three geological layers, yet each generation curves around the same empty meridian.",
        {"west": OUTER_ROOT_GALLERY_KEY, "north": OUTER_SEAM_BALCONY_KEY},
        tags=("level_17_18", "dungeon", "root_loop", "survey_marker"),
    ),
    _room(
        OUTER_SEAM_BALCONY_KEY,
        "Seam Balcony",
        OUTERWORKS_REGION_KEY,
        "A narrow balcony overlooks the survey gallery through a gap cut with impossible precision. The loop returns west.",
        {"south": OUTER_FOSSIL_BEND_KEY, "west": OUTER_SURVEY_KEY},
        enemies=(OUTER_SCAVENGER.key,),
        tags=("level_17_18", "dungeon", "root_loop"),
    ),
    _room(
        OUTER_LOCK_APPROACH_KEY,
        "Lock Approach",
        OUTERWORKS_REGION_KEY,
        "The two looping service systems meet at a hall lined with sockets for mechanisms that were removed before any current culture recorded the place.",
        {"west": OUTER_SURVEY_KEY, "east": OUTER_BOSS_KEY},
        enemies=(OUTER_SEAM_HUSK.key,),
        tags=("level_18", "dungeon", "boss_approach"),
    ),
    _room(
        OUTER_BOSS_KEY,
        "Lockwarden Chamber",
        OUTERWORKS_REGION_KEY,
        "Four doorways have been sealed flush with the walls. In the center, a broad custodian waits with locking arms folded across its chest.",
        {"west": OUTER_LOCK_APPROACH_KEY, "east": OUTER_DEEP_GATE_KEY},
        tags=("level_18_19", "dungeon", "boss"),
    ),
    _room(
        OUTER_DEEP_GATE_KEY,
        "Deep Seam Gate",
        OUTERWORKS_REGION_KEY,
        "Beyond the broken Lockwarden, the masonry changes from repaired frontier ruin to featureless gray construction. A sealed route continues east toward the deeper anomaly.",
        {"west": OUTER_BOSS_KEY},
        tags=("level_18_20", "dungeon", "return_point", "meridian_link"),
    ),
)

ALL_FRONTIER_ROOMS = FRONTIER_ROOMS + OUTERWORKS_ROOMS
ALL_FRONTIER_ROOM_KEYS = tuple(room.key for room in ALL_FRONTIER_ROOMS)


def _town_layers() -> tuple[DescriptionLayer, ...]:
    return (
        DescriptionLayer(
            "ashcross_human_reaction",
            "A few locals glance at your Human demonic styling, then return to work. Ashcross has seen stranger uniforms and worse manners.",
            priority=210,
            condition=ViewCondition(races=("human",)),
        ),
        DescriptionLayer(
            "ashcross_forest_elf_reaction",
            "A Forest Elf trail sign has been tied beside the message wall rather than translated over; somebody here expects you to read it as itself.",
            priority=210,
            condition=ViewCondition(races=("forest_elf",)),
        ),
        DescriptionLayer(
            "ashcross_moon_elf_reaction",
            "A clear strip of wall has been left for altitude notes and counterviews. Nobody calls it a shrine or asks you to.",
            priority=210,
            condition=ViewCondition(races=("moon_elf",)),
        ),
        DescriptionLayer(
            "ashcross_dwarf_reaction",
            "Freight clerks nod toward a public weight board before you can ask. The numbers are current, signed, and annoyingly thorough.",
            priority=210,
            condition=ViewCondition(races=("dwarf",)),
        ),
        DescriptionLayer(
            "ashcross_goblin_reaction",
            "The salvage stalls post buy prices openly. A Goblin trader catches your eye and taps the board: no outsider surcharge today.",
            priority=210,
            condition=ViewCondition(races=("goblin",)),
        ),
        DescriptionLayer(
            "ashcross_troll_reaction",
            "The gate beams are high enough that you do not have to duck. A Troll hunter notices you noticing and looks quietly pleased about it.",
            priority=210,
            condition=ViewCondition(races=("troll",)),
        ),
        DescriptionLayer(
            "ashcross_undead_reaction",
            "A notice outside the bunkhouse lists night work separately from sleeping space. Nobody has assumed you need either.",
            priority=210,
            condition=ViewCondition(races=("undead",)),
        ),
        DescriptionLayer(
            "ashcross_sporekin_reaction",
            "A shaded water trough and damp cellar vent have been marked with a small fungal spiral. Someone planned for Sporekin travelers before you arrived.",
            priority=210,
            condition=ViewCondition(races=("sporekin",)),
        ),
    )


def frontier_augmentations() -> dict[str, RoomAugmentation]:
    regional_flags = tuple(FINAL_REQUIRED_FLAGS)
    return {
        TROLL_CLUE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=ASHCROSS_ROOTROAD_KEY,
                    name="Rootroad Verge",
                    travel_text="You follow the cross-country trail east toward the old frontier roads.",
                    condition=ViewCondition(min_level=15),
                    failure_text="The frontier road is too dangerous to take yet.",
                ),
            ),
        ),
        DWARF_HUB_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=ASHCROSS_IRON_CAUSEWAY_KEY,
                    name="Iron Causeway",
                    travel_text="You leave the freight terminal on the patched causeway toward Ashcross.",
                    condition=ViewCondition(min_level=15),
                    failure_text="The causeway contracts are not open to you yet.",
                ),
            ),
        ),
        MOON_HUB_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="south",
                    destination_key=ASHCROSS_SKYROAD_KEY,
                    name="Fallen Skyroad",
                    travel_text="You take the steep survey road down toward the frontier crossing.",
                    condition=ViewCondition(min_level=16),
                    failure_text="The lower skyroad is still beyond your safe range.",
                ),
            ),
        ),
        ASHCROSS_COMMON_KEY: RoomAugmentation(description_layers=_town_layers()),
        ASHCROSS_DELVERS_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=OUTER_THRESHOLD_KEY,
                    name="Outerworks Stair",
                    travel_text="You descend beneath Ashcross into the mapped edge of the old complex.",
                    condition=ViewCondition(min_level=17),
                    failure_text="Kell stops you at the stair. 'Seventeen first. The Outerworks punish optimism.'",
                ),
            ),
        ),
        OUTER_DEEP_GATE_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="up",
                    destination_key=ASHCROSS_DELVERS_KEY,
                    name="Delver Winch",
                    aliases=("winch",),
                    travel_text="The repaired delver winch hauls you directly back to Ashcross.",
                    condition=ViewCondition(required_flags=(OUTER_BOSS_FLAG,)),
                    failure_text="The old winch is still locked behind the Lockwarden's controls.",
                ),
                ExitDefinition(
                    direction="east",
                    destination_key=MERIDIAN_CAMP_KEY,
                    name="Meridian Confluence",
                    travel_text="With all three regional witnesses complete, you pass through the deep seam toward Confluence Camp.",
                    condition=ViewCondition(
                        min_level=19,
                        required_flags=(OUTER_COMPLETE_FLAG, *regional_flags),
                    ),
                    failure_text=(
                        "The deep seam remains unreadable. Ashcross needs your completed Outerworks route, "
                        "all three regional witnesses, and level 19 before this road is safe."
                    ),
                ),
            ),
        ),
        MERIDIAN_CAMP_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="west",
                    destination_key=OUTER_DEEP_GATE_KEY,
                    name="Ashcross Outerworks",
                    travel_text="You climb back through the deep seam toward the Outerworks and Ashcross.",
                    condition=ViewCondition(min_level=19, required_flags=(OUTER_COMPLETE_FLAG,)),
                ),
            ),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    by_key = {item.key: item for item in legacy_world.ROOMS}
    by_key[room.key] = room
    legacy_world.ROOMS = tuple(by_key.values())
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    by_key = {item.key: item for item in legacy_world.NPCS}
    by_key[npc.key] = npc
    legacy_world.NPCS = tuple(by_key.values())
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    return RoomAugmentation(
        exit_overrides=existing.exit_overrides + extra.exit_overrides,
        extra_exits=existing.extra_exits + extra.extra_exits,
        features=existing.features + extra.features,
        description_layers=existing.description_layers + extra.description_layers,
    )


def install_frontier_convergence_content(world_service=None) -> None:
    for quest in FRONTIER_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in FRONTIER_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in FRONTIER_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for npc in FRONTIER_NPCS:
        _replace_npc(npc)
    for room in ALL_FRONTIER_ROOMS:
        _replace_room(room)

    economy.LOOT_TABLES[LOCKWARDEN_KEY] = (economy.LootDrop(LOCKWARDEN_PLATE_KEY, 1),)

    if world_service is None:
        return

    for room in ALL_FRONTIER_ROOMS:
        world_service.legacy_rooms[room.key] = room

    for room_key, augmentation in frontier_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(
            world_service.augmentations.get(room_key),
            augmentation,
        )

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (
            *ALL_FRONTIER_ROOM_KEYS,
            TROLL_CLUE_KEY,
            DWARF_HUB_KEY,
            MOON_HUB_KEY,
            MERIDIAN_CAMP_KEY,
        ):
            cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _refresh(session) -> None:
    if session.character is None:
        return
    updated = session.database.get_character_by_name(session.character.name)
    if updated is not None:
        session.character = updated


def _grant_once(session, flag: str) -> bool:
    if session.character is None or flag in _flags(session):
        return False
    session.database.grant_flag(session.character.id, flag)
    return True


def _ensure_frontier_quests(session) -> None:
    if session.character is None:
        return
    if (
        session.character.current_room in ALL_FRONTIER_ROOM_KEYS
        and session.character.level >= INTRO_QUEST.minimum_level
        and _quest(session, INTRO_QUEST_KEY) is None
        and INTRO_COMPLETE_FLAG not in _flags(session)
    ):
        session.database.start_quest(session.character.id, INTRO_QUEST_KEY, "reach_common")


def _steward_line(session) -> str:
    race = (session.character.race if session.character is not None else "") or ""
    lines = {
        "human": "Sere glances at your Human styling. 'Keep the Blackwall's city feuds south of the palisade and nobody here cares what outsiders call your people.'",
        "forest_elf": "Sere nods toward the living trail signs. 'We leave Forest Elf marks untranslated when translation would flatten the useful part.'",
        "moon_elf": "Sere points toward a clean slate by the gate. 'Counterviews go there. Nobody in Ashcross wins an argument by pretending only one height exists.'",
        "dwarf": "Sere taps the public freight board. 'Weights are signed, revisions are dated, and the complaint box is unfortunately real.'",
        "goblin": "Sere hooks a thumb toward Market Row. 'Salvage rights are posted before bids. If somebody invents an outsider fee, bring me the slate.'",
        "troll": "Sere looks toward the high gate beams. 'We rebuilt those after the third Troll traveler got tired of ducking. Should have done it after the first.'",
        "undead": "Sere gestures toward the night-work board. 'No curfew, no mandatory meal ticket, no pretending sleep is universal.'",
        "sporekin": "Sere points out the shaded water and damp cellar vent. 'The accommodations are ordinary now. That was the point.'",
    }
    text = lines.get(race, "Sere gives you a practical once-over. 'Ashcross records what you do here, not what someone else says your ancestry means.'")

    flags = _flags(session)
    echoes: list[str] = []
    if TROLL_COMPLETE_FLAG in flags:
        echoes.append("Your Thornwake witness has already reached the message wall.")
    if DWARF_COMPLETE_FLAG in flags:
        echoes.append("The freight office has copied your Deepwheel survey result.")
    if MOON_COMPLETE_FLAG in flags:
        echoes.append("The survey slate carries a note from the Counterstar highroad.")
    if echoes:
        text += " " + " ".join(echoes)
    return text


async def _talk_steward(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_COMMON_KEY:
        return False
    _ensure_frontier_quests(session)
    await session.send(_steward_line(session) + "\r\n")
    q = _quest(session, INTRO_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "reach_common":
        session.database.advance_quest(session.character.id, INTRO_QUEST_KEY, "meet_steward")
        q = _quest(session, INTRO_QUEST_KEY)
    if q and q["status"] == "active" and q["current_step"] == "meet_steward":
        session.database.complete_quest(session.character.id, INTRO_QUEST_KEY)
        session.database.grant_flag(session.character.id, INTRO_COMPLETE_FLAG)
        if session.database.item_quantity(session.character.id, DELVERS_TOKEN_KEY) <= 0:
            session.database.add_item(session.character.id, DELVERS_TOKEN_KEY, 1)
        session.database.add_experience(session.character.id, 900)
        _refresh(session)
        await session.send(
            "Sere scratches your name onto the local roll and hands over a brass Delver Token. "
            "Quest complete: 900 XP. The token is recognition, not citizenship.\r\n"
        )
    return True


async def _talk_broker(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_DELVERS_KEY:
        return False
    flags = _flags(session)
    pack = _quest(session, PACK_QUEST_KEY)
    outer = _quest(session, OUTER_QUEST_KEY)

    if pack and pack["status"] == "active" and pack["current_step"] == "return_broker":
        session.database.complete_quest(session.character.id, PACK_QUEST_KEY)
        session.database.grant_flag(session.character.id, PACK_COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 1200)
        _refresh(session)
        await session.send(
            "Kell checks the satchel seal, then leaves the weathered bag with you. "
            "'Courier was not so lucky. The route still matters.' Quest complete: 1200 XP.\r\n"
        )
        return True

    if outer and outer["status"] == "active" and outer["current_step"] == "report_route":
        session.database.complete_quest(session.character.id, OUTER_QUEST_KEY)
        session.database.grant_flag(session.character.id, OUTER_COMPLETE_FLAG)
        if session.database.item_quantity(session.character.id, LOCKWARDEN_PLATE_KEY) <= 0:
            session.database.add_item(session.character.id, LOCKWARDEN_PLATE_KEY, 1)
        session.database.add_experience(session.character.id, 4000)
        _refresh(session)
        await session.send(
            "Kell marks both loops, the Lockwarden chamber, and the deep seam on a fresh board. "
            "'Good. Now it is a route instead of a rumor.' Quest complete: 4000 XP and a Lockwarden Keyplate. "
            "At level 19, the deep gate can carry all three regional witnesses toward the Meridian Vault.\r\n"
        )
        return True

    if INTRO_COMPLETE_FLAG not in flags:
        await session.send("'Talk to Sere in the Common first. I prefer contracts attached to people the town has actually met.'\r\n")
        return True

    if pack is None and PACK_COMPLETE_FLAG not in flags:
        session.database.start_quest(session.character.id, PACK_QUEST_KEY, "recover_pack")
        await session.send(
            "Kell slides a courier hook across the desk. 'Sunken Watch, below the broken milestone. "
            "Bring back the dispatch satchel. SEARCH SATCHEL when you find the old watch.'\r\n"
        )
        return True

    await session.send(
        "'For the Outerworks contract, ASK KELL ABOUT OUTERWORKS once you are level 17. "
        "The stair is not a sightseeing route.'\r\n"
    )
    return True


async def _ask_outerworks(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_DELVERS_KEY:
        return False
    flags = _flags(session)
    if session.character.level < 17:
        await session.send("'Level seventeen first. The old halls punish optimism faster than I can write contracts.'\r\n")
        return True
    if INTRO_COMPLETE_FLAG not in flags:
        await session.send("'Sere first. I need your name on the town roll before I send you under it.'\r\n")
        return True
    q = _quest(session, OUTER_QUEST_KEY)
    if OUTER_COMPLETE_FLAG in flags:
        await session.send(
            "'You mapped it already. The deep seam is your next problem: level nineteen, all three regional witnesses, then east from the Deep Seam Gate.'\r\n"
        )
        return True
    if q is None:
        session.database.start_quest(session.character.id, OUTER_QUEST_KEY, "enter_outerworks")
        await session.send(
            "Kell draws two circles that share one center. 'Flood loop north. Root loop south. "
            "MARK WATERLINE in the cistern, MARK ROOTLINE at Fossil Bend, then break the Lockwarden. "
            "Use the winch back here and report before you trust the deeper route.'\r\n"
        )
        return True
    await session.send(f"'Your current Outerworks step is: {q['current_step'].replace('_', ' ')}.'\r\n")
    return True


async def _search_satchel(session) -> bool:
    if session.character is None or session.character.current_room != ASHCROSS_SUNKEN_WATCH_KEY:
        return False
    q = _quest(session, PACK_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "recover_pack":
        await session.send("You search the old courier hooks and find only broken straps and water-stained wood.\r\n")
        return True
    if session.database.item_quantity(session.character.id, DISPATCH_SATCHEL_KEY) <= 0:
        session.database.add_item(session.character.id, DISPATCH_SATCHEL_KEY, 1)
    session.database.advance_quest(session.character.id, PACK_QUEST_KEY, "return_broker")
    await session.send(
        "Behind a fallen bunk you find the weathered dispatch satchel, still caught on its courier hook. "
        "Return it to Kell in the Delvers' Yard.\r\n"
    )
    return True


async def _mark_outerworks(session, marker: str) -> bool:
    if session.character is None:
        return False
    config = {
        "water": (
            OUTER_CISTERN_KEY,
            "mark_waterline",
            "mark_rootline",
            "You score a fresh survey mark beside the impossible level waterline. The root loop is next: MARK ROOTLINE at Fossil Bend.",
        ),
        "root": (
            OUTER_FOSSIL_BEND_KEY,
            "mark_rootline",
            "defeat_lockwarden",
            "You mark where three ages of fossil roots bend around the same empty line. Both loops are mapped. Break the Lockwarden east of the survey gallery.",
        ),
    }[marker]
    room_key, expected_step, next_step, text = config
    if session.character.current_room != room_key:
        return False
    q = _quest(session, OUTER_QUEST_KEY)
    if not q or q["status"] != "active":
        await session.send("You make a private note, but no Ashcross Outerworks contract is active.\r\n")
        return True
    if q["current_step"] != expected_step:
        await session.send(f"That survey mark is not your current contract step ({q['current_step'].replace('_', ' ')}).\r\n")
        return True
    session.database.advance_quest(session.character.id, OUTER_QUEST_KEY, next_step)
    if marker == "root" and OUTER_BOSS_FLAG in _flags(session):
        session.database.advance_quest(session.character.id, OUTER_QUEST_KEY, "report_route")
        text += " The Lockwarden is already down, so the contract advances directly to reporting the route."
    await session.send(text + "\r\n")
    return True


async def _delegate(session, previous_prompt, command: str) -> None:
    had = "prompt" in session.__dict__
    old = session.__dict__.get("prompt")

    async def replay(_text):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had:
            session.prompt = old
        else:
            session.__dict__.pop("prompt", None)


def install_frontier_convergence_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_frontier_convergence_runtime_installed", False):
        return

    install_frontier_convergence_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self):
        await previous_enter(self)
        _ensure_frontier_quests(self)

    async def move_character(self, direction):
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        _ensure_frontier_quests(self)
        if self.character is None or self.character.current_room == before:
            return

        room = self.character.current_room
        intro = _quest(self, INTRO_QUEST_KEY)
        if (
            room == ASHCROSS_COMMON_KEY
            and intro
            and intro["status"] == "active"
            and intro["current_step"] == "reach_common"
        ):
            self.database.advance_quest(self.character.id, INTRO_QUEST_KEY, "meet_steward")
            await self.send("Ashcross opens around the Common. TALK SERE before taking local contracts.\r\n")

        outer = _quest(self, OUTER_QUEST_KEY)
        if (
            room == OUTER_THRESHOLD_KEY
            and outer
            and outer["status"] == "active"
            and outer["current_step"] == "enter_outerworks"
        ):
            self.database.advance_quest(self.character.id, OUTER_QUEST_KEY, "mark_waterline")
            await self.send(
                "The Outerworks split around the survey gallery. Map the flood loop first and MARK WATERLINE in the Old Cistern.\r\n"
            )

    def enemy_in_room(self, target_text):
        if (
            self.character is not None
            and self.character.current_room == OUTER_BOSS_KEY
            and OUTER_BOSS_FLAG not in _flags(self)
            and OUTER_LOCKWARDEN.matches(target_text)
        ):
            return EnemyState(OUTER_LOCKWARDEN)
        return previous_lookup(self, target_text)

    async def finish_enemy(self, enemy):
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if not was_active or enemy.definition.key != LOCKWARDEN_KEY or self.character is None:
            return
        if not _grant_once(self, OUTER_BOSS_FLAG):
            return
        q = _quest(self, OUTER_QUEST_KEY)
        if q and q["status"] == "active" and q["current_step"] == "defeat_lockwarden":
            self.database.advance_quest(self.character.id, OUTER_QUEST_KEY, "report_route")
        await self.send(
            "The Lockwarden's arms seize open. A delver winch at the Deep Seam Gate is now usable. "
            "Go east, take the winch up, and report the mapped route to Kell.\r\n"
        )

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
        handled = False

        if normalized in {"talk sere", "talk steward", "talk steward sere"}:
            handled = await _talk_steward(self)
        elif normalized in {"talk kell", "talk broker", "talk farstep"}:
            handled = await _talk_broker(self)
        elif normalized in {"ask kell about outerworks", "ask broker about outerworks", "outerworks contract"}:
            handled = await _ask_outerworks(self)
        elif normalized in {"search satchel", "search dispatch", "search courier satchel"}:
            handled = await _search_satchel(self)
        elif normalized in {"mark waterline", "mark water line"}:
            handled = await _mark_outerworks(self, "water")
        elif normalized in {"mark rootline", "mark root line"}:
            handled = await _mark_outerworks(self, "root")
        elif normalized in {"ashcross", "frontier", "frontier arc", "levels 12 20"}:
            await self.send(
                "FRONTIER ARC (12-20)\r\n"
                " - Levels 12-15: the Three Roads leave Veyra through Troll, Dwarven, and Moon Elf country.\r\n"
                " - Levels 15-16: those roads cross at Ashcross, a rough multi-racial frontier town with optional ruins and side routes.\r\n"
                " - Levels 17-18: descend from the Delvers' Yard into the looping Meridian Outerworks; map both loops and defeat the Lockwarden.\r\n"
                " - Levels 19-20: all three regional witnesses and the mapped Outerworks route open the Meridian Vault.\r\n"
                " - Level 20 remains the first-act class capstone and Twentieth Step.\r\n"
            )
            return

        if handled:
            return
        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = enemy_in_room
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._frontier_convergence_runtime_installed = True
