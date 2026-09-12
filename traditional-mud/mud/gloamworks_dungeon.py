from __future__ import annotations

import weakref
from dataclasses import replace
from typing import Iterable

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY, WAYMEET_INTRO_COMPLETE_FLAG


GLOAMWORKS_REGION_KEY = "gloamworks"

GLOAM_ENTRY_KEY = "gloamworks_entry_cage"
GLOAM_CHAIN_GALLERY_KEY = "gloamworks_chain_gallery"
GLOAM_BROKEN_WINCH_KEY = "gloamworks_broken_winch"
GLOAM_SORTING_FLOOR_KEY = "gloamworks_sorting_floor"
GLOAM_PUMP_HALL_KEY = "gloamworks_pump_hall"
GLOAM_GLASS_FAULT_KEY = "gloamworks_glass_fault"
GLOAM_RESONANCE_SHAFT_KEY = "gloamworks_resonance_shaft"
GLOAM_BRAKE_CHAPEL_KEY = "gloamworks_brake_chapel"
GLOAM_SUSPENDED_BRIDGE_KEY = "gloamworks_suspended_bridge"
GLOAM_COLD_FOUNDRY_KEY = "gloamworks_cold_foundry"
GLOAM_CRAWLER_NURSERY_KEY = "gloamworks_crawler_nursery"
GLOAM_SWITCHYARD_KEY = "gloamworks_switchyard"
GLOAM_HOLLOW_DYNAMO_KEY = "gloamworks_hollow_dynamo"
GLOAM_IMPOSSIBLE_CUT_KEY = "gloamworks_impossible_cut"
GLOAM_TWIN_SEAL_KEY = "gloamworks_twin_seal_vestibule"
GLOAM_LEFT_OBSERVATORY_KEY = "gloamworks_left_observatory"
GLOAM_BURIED_COURT_KEY = "gloamworks_buried_court"
GLOAM_BREACH_VAULT_KEY = "gloamworks_breach_vault"

GLOAMWORKS_ROOM_KEYS = (
    GLOAM_ENTRY_KEY,
    GLOAM_CHAIN_GALLERY_KEY,
    GLOAM_BROKEN_WINCH_KEY,
    GLOAM_SORTING_FLOOR_KEY,
    GLOAM_PUMP_HALL_KEY,
    GLOAM_GLASS_FAULT_KEY,
    GLOAM_RESONANCE_SHAFT_KEY,
    GLOAM_BRAKE_CHAPEL_KEY,
    GLOAM_SUSPENDED_BRIDGE_KEY,
    GLOAM_COLD_FOUNDRY_KEY,
    GLOAM_CRAWLER_NURSERY_KEY,
    GLOAM_SWITCHYARD_KEY,
    GLOAM_HOLLOW_DYNAMO_KEY,
    GLOAM_IMPOSSIBLE_CUT_KEY,
    GLOAM_TWIN_SEAL_KEY,
    GLOAM_LEFT_OBSERVATORY_KEY,
    GLOAM_BURIED_COURT_KEY,
    GLOAM_BREACH_VAULT_KEY,
)

GLOAMWORKS_QUEST_KEY = "gloamworks_below_the_sealed_door"
GLOAMWORKS_COMPLETE_FLAG = "gloamworks_descent_complete"
GLOAMWORKS_REGENT_FLAG = "gloamworks_regent_defeated"
GLOAMWORKS_TWIN_SEAL_FLAG = "gloamworks_twin_seal_synced"
GLOAMWORKS_FAULT_READ_FLAG = "gloamworks_fault_read"
GLOAMWORKS_BRAKE_FLAG = "gloamworks_brake_saint_defeated"
GLOAMWORKS_DYNAMO_FLAG = "gloamworks_mother_sparks_defeated"

REGENT_SHARD_KEY = "gloamworks_regent_shard"
RESONANT_COG_KEY = "gloamworks_resonant_cog"
COLD_GLASS_KEY = "gloamworks_cold_glass"

CHAINMOTE_KEY = "gloamworks_chainmote_swarm"
GLASSLUNG_KEY = "gloamworks_glasslung_crawler"
ECHO_HUSK_KEY = "gloamworks_echo_husk"
FOLDED_MAW_KEY = "gloamworks_folded_maw"
BRAKE_SAINT_KEY = "gloamworks_brake_saint"
MOTHER_SPARKS_KEY = "gloamworks_mother_sparks"
BURIED_REGENT_KEY = "gloamworks_buried_regent"

SURVEYOR_KEY = "gloamworks_surveyor_pell_ashmark"


GLOAMWORKS_QUEST = QuestDefinition(
    key=GLOAMWORKS_QUEST_KEY,
    name="Below the Sealed Door",
    style="structured",
    minimum_level=4,
    description=(
        "Waymeet finally opens the abandoned Gloamworks long enough for a survey. The old industrial excavation is dangerous in familiar ways near the surface, then increasingly wrong in ways no local engineering tradition explains."
    ),
    objective_steps=(
        ("talk_surveyor", "TALK SURVEYOR at Gloam Mouth."),
        ("enter_works", "Descend through the opened survey cage into the Gloamworks."),
        ("read_fault", "Reach the Glass Fault and EXAMINE FAULT. Compare what you perceive with other travelers."),
        ("defeat_brake_saint", "Pass the Resonance Shaft and defeat the Brake Saint in the old safety chapel."),
        ("defeat_mother_sparks", "Cross the lower works and defeat Mother-of-Sparks in the Hollow Dynamo."),
        ("sync_seals", "At the Twin-Seal Vestibule, two players must HOLD LEFT SEAL and HOLD RIGHT SEAL together."),
        ("defeat_regent", "Keep at least two synchronized explorers in the Buried Court and defeat the Buried Regent."),
        ("return_surveyor", "Return to Surveyor Pell at Gloam Mouth with what the group learned."),
        ("complete", "The Gloamworks were an excavation before they became a breach. Something beneath Astralis answered the digging."),
    ),
)

REGENT_SHARD = ItemDefinition(
    key=REGENT_SHARD_KEY,
    name="Regent Shard",
    description="A palm-sized piece of black-violet material broken from the Buried Regent. Every edge feels straight until viewed from the side.",
    category="material",
    tier=2,
)
RESONANT_COG = ItemDefinition(
    key=RESONANT_COG_KEY,
    name="Resonant Cog",
    description="An old Gloamworks safety cog that rings a different note depending on which face is held upward.",
    category="material",
    tier=2,
)
COLD_GLASS = ItemDefinition(
    key=COLD_GLASS_KEY,
    name="Cold Glass Flake",
    description="A translucent flake from the impossible fault. It remains colder than the room without frost or condensation.",
    category="material",
    tier=2,
)
GLOAMWORKS_ITEMS = (REGENT_SHARD, RESONANT_COG, COLD_GLASS)


CHAINMOTE = EnemyDefinition(
    key=CHAINMOTE_KEY,
    name="Chainmote Swarm",
    aliases=("chainmote", "chainmotes", "swarm", "chainmote swarm"),
    description="a fistful of iron-bright mites moving as one body along hanging chain, each using the links as if they were bones",
    max_hp=46,
    armor_class=6,
    auto_attack_damage=5,
    auto_attack_interval=3.0,
    xp_reward=34,
)
GLASSLUNG = EnemyDefinition(
    key=GLASSLUNG_KEY,
    name="Glasslung Crawler",
    aliases=("glasslung", "crawler", "glasslung crawler"),
    description="a translucent six-legged mine animal whose ribbed lung sacs glow violet only when it exhales",
    max_hp=64,
    armor_class=8,
    auto_attack_damage=6,
    auto_attack_interval=3.1,
    xp_reward=48,
)
ECHO_HUSK = EnemyDefinition(
    key=ECHO_HUSK_KEY,
    name="Echo Husk",
    aliases=("husk", "echo", "echo husk"),
    description="an empty old work coat and helmet held upright by a shivering outline, repeating motions no worker is inside to remember",
    max_hp=78,
    armor_class=9,
    auto_attack_damage=7,
    auto_attack_interval=3.0,
    xp_reward=62,
)
FOLDED_MAW = EnemyDefinition(
    key=FOLDED_MAW_KEY,
    name="Folded Maw",
    aliases=("maw", "folded", "folded maw"),
    description="a pale predator that seems to have too many shoulders until it turns, when several of them prove to be the same shoulder seen from incompatible angles",
    max_hp=94,
    armor_class=10,
    auto_attack_damage=8,
    auto_attack_interval=2.9,
    xp_reward=78,
)
BRAKE_SAINT = EnemyDefinition(
    key=BRAKE_SAINT_KEY,
    name="The Brake Saint",
    aliases=("brake saint", "saint", "brake automaton"),
    description="a towering emergency-brake automaton wrapped in snapped red safety pennants, endlessly trying to stop machinery that has been dead for centuries",
    max_hp=138,
    armor_class=12,
    auto_attack_damage=8,
    auto_attack_interval=2.8,
    xp_reward=118,
)
MOTHER_SPARKS = EnemyDefinition(
    key=MOTHER_SPARKS_KEY,
    name="Mother-of-Sparks",
    aliases=("mother", "mother of sparks", "mother-of-sparks", "dynamo parasite"),
    description="a huge copper-shelled parasite rooted through the dead dynamo, feeding on charge that should not exist and birthing blue-white sparks from a ring of glassy vents",
    max_hp=168,
    armor_class=12,
    auto_attack_damage=9,
    auto_attack_interval=2.7,
    xp_reward=142,
)
BURIED_REGENT = EnemyDefinition(
    key=BURIED_REGENT_KEY,
    name="The Buried Regent",
    aliases=("regent", "buried regent", "the buried regent"),
    description="a many-limbed mineral organism fused around an ancient excavation frame, wearing broken beams and drill teeth like an accidental crown",
    max_hp=270,
    armor_class=14,
    auto_attack_damage=11,
    auto_attack_interval=2.6,
    xp_reward=260,
)

GLOAMWORKS_ENEMIES = (CHAINMOTE, GLASSLUNG, ECHO_HUSK, FOLDED_MAW, BRAKE_SAINT, MOTHER_SPARKS, BURIED_REGENT)
GLOAMWORKS_MINIBOSS_KEYS = (BRAKE_SAINT_KEY, MOTHER_SPARKS_KEY)
GLOAMWORKS_BOSS_KEY = BURIED_REGENT_KEY


SURVEYOR = NpcDefinition(
    key=SURVEYOR_KEY,
    name="Surveyor Pell Ashmark",
    short_description="a soot-haired surveyor checking a rope harness beside the newly loosened Gloamworks chains",
    room_key=WAYMEET_GLOAM_MOUTH_KEY,
    role="Gloamworks expedition contact",
    dialogue=(
        "Pell keeps one hand on the old chain. 'The upper works were built by ordinary hands. That is the reassuring part.'",
        "'If two people tell me the deep rooms looked different, I want both reports. Do not average the strange parts away.'",
        "'And nobody opens the last seal alone. Whatever the old crews feared, they designed that lock to require disagreement with witnesses.'",
    ),
)


def _room(key: str, name: str, description: str, exits: dict[str, str], *, enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=GLOAMWORKS_REGION_KEY,
        description=description,
        exits=exits,
        enemy_keys=enemies,
        tags=("dungeon", "gloamworks", *tags),
    )


GLOAMWORKS_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        GLOAM_ENTRY_KEY,
        "Survey Cage Landing",
        "A freight cage hangs crooked in a stone shaft beneath Waymeet. Rusted rails, numbered hooks, and a chalked casualty board prove the upper works were once an ordinary industrial site. The only unnatural thing is the cold rising from below.",
        {"up": WAYMEET_GLOAM_MOUTH_KEY, "east": GLOAM_CHAIN_GALLERY_KEY},
        tags=("entrance", "level_4"),
    ),
    _room(
        GLOAM_CHAIN_GALLERY_KEY,
        "Chain Gallery",
        "Hundreds of hauling chains hang from an overhead track. Some end in hooks, some in empty ore cradles, and some disappear into cracks too narrow to have received them. Tiny metallic things scuttle whenever the links sway.",
        {"west": GLOAM_ENTRY_KEY, "east": GLOAM_BROKEN_WINCH_KEY, "south": GLOAM_SORTING_FLOOR_KEY},
        enemies=(CHAINMOTE_KEY,), tags=("level_4",),
    ),
    _room(
        GLOAM_BROKEN_WINCH_KEY,
        "Broken Winch House",
        "A drum winch fills the room, its cable wound tight enough to sing despite being severed at both ends. Maintenance tags record escalating complaints about vibration before the final shift simply stops mid-sentence.",
        {"west": GLOAM_CHAIN_GALLERY_KEY, "down": GLOAM_PUMP_HALL_KEY},
        enemies=(ECHO_HUSK_KEY,), tags=("level_4", "industrial"),
    ),
    _room(
        GLOAM_SORTING_FLOOR_KEY,
        "Ore Sorting Floor",
        "Tilted tables divide old stone by grade. Ordinary iron, coal, and slate still sit in labeled bins. A fourth bin was added later and has no material name—only the warning NOT STONE repeated in several hands.",
        {"north": GLOAM_CHAIN_GALLERY_KEY, "east": GLOAM_PUMP_HALL_KEY},
        enemies=(CHAINMOTE_KEY,), tags=("level_4", "evidence"),
    ),
    _room(
        GLOAM_PUMP_HALL_KEY,
        "Drowned Pump Hall",
        "Two piston pumps stand knee-deep in black water. Their flywheels are motionless, but ripples repeatedly travel against the slope toward a dry doorway in the eastern wall.",
        {"up": GLOAM_BROKEN_WINCH_KEY, "west": GLOAM_SORTING_FLOOR_KEY, "east": GLOAM_GLASS_FAULT_KEY},
        enemies=(GLASSLUNG_KEY,), tags=("level_4", "flooded"),
    ),
    _room(
        GLOAM_GLASS_FAULT_KEY,
        "The Glass Fault",
        "The excavation ends at a vertical plane of dark translucent material cutting cleanly through native stone, timber bracing, and an iron pipe without cracking any of them. Looking directly at it is less confusing than deciding where its edges are.",
        {"west": GLOAM_PUMP_HALL_KEY, "east": GLOAM_RESONANCE_SHAFT_KEY},
        enemies=(GLASSLUNG_KEY,), tags=("level_5", "perception_split", "alien"),
    ),
    _room(
        GLOAM_RESONANCE_SHAFT_KEY,
        "Resonance Shaft",
        "A circular shaft drops through levels the original survey maps never contained. Every sound returns once as an echo and once as something almost—but not exactly—the same sound reconstructed from memory.",
        {"west": GLOAM_GLASS_FAULT_KEY, "south": GLOAM_BRAKE_CHAPEL_KEY, "down": GLOAM_SUSPENDED_BRIDGE_KEY},
        enemies=(ECHO_HUSK_KEY,), tags=("level_5", "perception_split", "alien"),
    ),
    _room(
        GLOAM_BRAKE_CHAPEL_KEY,
        "Brake Chapel",
        "Red-painted emergency levers line a vaulted service bay. Workers once nailed names of prevented accidents beside the mechanisms, making a practical shrine to stopping a machine before it killed somebody. One enormous safety automaton still patrols the rails.",
        {"north": GLOAM_RESONANCE_SHAFT_KEY},
        enemies=(BRAKE_SAINT_KEY,), tags=("level_5", "miniboss"),
    ),
    _room(
        GLOAM_SUSPENDED_BRIDGE_KEY,
        "Suspended Haul Bridge",
        "A narrow iron bridge crosses the shaft on chains anchored into both ordinary rock and the black fault material. The two anchor systems vibrate at different tempos, forcing the bridge into a slow breathing motion.",
        {"up": GLOAM_RESONANCE_SHAFT_KEY, "east": GLOAM_COLD_FOUNDRY_KEY},
        enemies=(FOLDED_MAW_KEY,), tags=("level_5", "hazard"),
    ),
    _room(
        GLOAM_COLD_FOUNDRY_KEY,
        "Cold Foundry",
        "Smelting furnaces occupy this chamber, but slag has frozen in mid-pour as smooth black ropes. Tool steel is rusted around it. The unknown material is pristine and cold enough to make nearby breath visible.",
        {"west": GLOAM_SUSPENDED_BRIDGE_KEY, "north": GLOAM_CRAWLER_NURSERY_KEY, "east": GLOAM_SWITCHYARD_KEY},
        enemies=(ECHO_HUSK_KEY,), tags=("level_5", "industrial"),
    ),
    _room(
        GLOAM_CRAWLER_NURSERY_KEY,
        "Glasslung Nursery",
        "Discarded respirator filters have been packed into nests around a warm drainage pipe. Dozens of shed translucent membranes show that the Glasslung Crawlers did not live here when the mine was active; they adapted afterward.",
        {"south": GLOAM_COLD_FOUNDRY_KEY},
        enemies=(GLASSLUNG_KEY,), tags=("level_5", "ecology"),
    ),
    _room(
        GLOAM_SWITCHYARD_KEY,
        "Lower Switchyard",
        "Rail switches fan into dead tunnels. Half the levers operate familiar track points. The rest move nothing visible, yet pulling wind through cracks in the floor as though changing routes somewhere beneath the stone.",
        {"west": GLOAM_COLD_FOUNDRY_KEY, "east": GLOAM_HOLLOW_DYNAMO_KEY, "south": GLOAM_IMPOSSIBLE_CUT_KEY},
        enemies=(FOLDED_MAW_KEY,), tags=("level_6",),
    ),
    _room(
        GLOAM_HOLLOW_DYNAMO_KEY,
        "Hollow Dynamo",
        "A generator the size of a house has been split open from within. Copper windings vanish into the body of something rooted through the armature, and blue-white sparks crawl across glass vents in a rhythm too slow to be electricity.",
        {"west": GLOAM_SWITCHYARD_KEY},
        enemies=(MOTHER_SPARKS_KEY,), tags=("level_6", "miniboss"),
    ),
    _room(
        GLOAM_IMPOSSIBLE_CUT_KEY,
        "The Impossible Cut",
        "The miners drove a test tunnel here after finding the fault. Pick marks begin normally, then appear on the ceiling, then behind the viewer without any turn in the passage. Distance behaves correctly only while nobody tries to measure it.",
        {"north": GLOAM_SWITCHYARD_KEY, "east": GLOAM_TWIN_SEAL_KEY, "south": GLOAM_LEFT_OBSERVATORY_KEY},
        enemies=(FOLDED_MAW_KEY,), tags=("level_6", "alien"),
    ),
    _room(
        GLOAM_LEFT_OBSERVATORY_KEY,
        "Abandoned Observation Niche",
        "A tiny side room holds eight stools and eight contradictory sketches of the same wall. The old survey crew eventually stopped trying to select the correct drawing and began filing all of them together.",
        {"north": GLOAM_IMPOSSIBLE_CUT_KEY},
        tags=("level_6", "lore", "safe_pocket"),
    ),
    _room(
        GLOAM_TWIN_SEAL_KEY,
        "Twin-Seal Vestibule",
        "Two heavy handplates stand on opposite sides of a circular door, too far apart for one body to operate both. The old warning is blunt: TWO WITNESSES. TWO HANDS. IF YOU DISAGREE, LEAVE IT SHUT.",
        {"west": GLOAM_IMPOSSIBLE_CUT_KEY, "east": GLOAM_BURIED_COURT_KEY},
        tags=("level_6", "cooperative_gate"),
    ),
    _room(
        GLOAM_BURIED_COURT_KEY,
        "Buried Court",
        "The final excavation opens into a chamber that no crew built. Black ribs rise from the floor around an old drilling frame. Something enormous has grown through machine and stone together, making the industrial ruin look less invaded than incorporated.",
        {"west": GLOAM_TWIN_SEAL_KEY, "east": GLOAM_BREACH_VAULT_KEY},
        enemies=(BURIED_REGENT_KEY,), tags=("level_7", "boss", "group_required"),
    ),
    _room(
        GLOAM_BREACH_VAULT_KEY,
        "Breach Survey Vault",
        "Beyond the Regent is not a treasure room but a survey station. The last crew mapped a narrow black seam continuing far beneath the frontier and marked several distant surface points where the same resonance later appeared. One line points east beyond Waymeet toward the Greywake March.",
        {"west": GLOAM_BURIED_COURT_KEY},
        tags=("level_7", "aftermath", "world_handoff"),
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
    return RoomAugmentation(
        exit_overrides=tuple(overrides.values()),
        extra_exits=tuple(extras.values()),
        features=tuple(features.values()),
        description_layers=tuple(layers.values()),
    )


RACE_FAULT_TEXT = {
    "human": "The black plane reminds you uncomfortably of the seamless dead-glass Earth relics in Human archives—not because it looks identical, but because both seem manufactured without showing how.",
    "forest_elf": "What troubles you is not that the material is unnatural. It is that root, fungus, water, and lichen all approach it and then redirect before touching it, as though the living forest above has been avoiding this line for generations.",
    "moon_elf": "Your eyes agree on the fault until you shift your head. The near edge moves less than the far edge should, producing a parallax result that cannot belong to a flat plane occupying this distance.",
    "dwarf": "The fault carries roof load without compression, cracking, or any visible transfer into the surrounding stone. Whatever it is doing structurally, it is not behaving like a material under weight.",
    "goblin": "You look automatically for seams, fasteners, weak points, useful scrap, or some ugly way to take the thing apart. For once, the world offers you no obvious handle at all.",
    "troll": "Cold comes off the plane without a draft. Your skin reads it like weather, but there is no direction to the cold and no warmer side to stand on.",
    "undead": "A slow cadence seems to sit behind the fault: not a voice, not a heartbeat, but close enough to an old command rhythm that your dead muscles briefly prepare to obey something that never speaks.",
    "sporekin": "The shared sense that normally makes living ground feel crowded becomes abruptly blank at the fault. Not silent—absent, like a place where connection has no concept to attach to.",
}

CLASS_RESONANCE_TEXT = {
    "necromancer": "The shaft carries something that resembles death residue until you test the feeling carefully. Nothing here is dead enough to have left it. The resemblance is a false friend.",
    "brute": "Your body notices the pressure before your thoughts do. Weight seems to arrive from alternating sides of the shaft, turning balance itself into something you have to actively hold.",
    "wizard": "There is power here, but it does not arrange itself like a spell. The repeating pattern has rules, yet the grammar refuses every magical structure you know.",
    "druid": "The nearby cave life is not poisoned. Moss, insects, and pale roots are all healthy right up to an invisible boundary, then choose different directions as if growth itself has learned a detour.",
    "priest": "You sense no deity claiming this place. What unsettles you is the opposite: the shaft produces the feeling of expectation without any presence to do the expecting.",
}


def gloamworks_augmentations() -> dict[str, RoomAugmentation]:
    race_layers = tuple(
        DescriptionLayer(
            key=f"gloam_fault_{race_key}",
            text=text,
            priority=35,
            condition=ViewCondition(races=(race_key,)),
        )
        for race_key, text in RACE_FAULT_TEXT.items()
    )
    class_layers = tuple(
        DescriptionLayer(
            key=f"gloam_resonance_{class_key}",
            text=text,
            priority=35,
            condition=ViewCondition(classes=(class_key,)),
        )
        for class_key, text in CLASS_RESONANCE_TEXT.items()
    )
    return {
        WAYMEET_GLOAM_MOUTH_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="down",
                    destination_key=GLOAM_ENTRY_KEY,
                    name="Gloamworks Survey Cage",
                    travel_text="Pell unhooks the survey chain and the old cage lowers you beneath the sealed works.",
                    condition=ViewCondition(required_flags=(WAYMEET_INTRO_COMPLETE_FLAG,), min_level=4),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "gloam_survey_cage",
                    "Survey Cage",
                    "an old freight cage newly made just safe enough for a controlled descent",
                    "New rope, Goblin clamps, Dwarven brake blocks, Human chalk marks, and Forest Elf warning cord have all been added to an older cage. Waymeet does not trust the original machinery.",
                    ("cage", "survey cage", "freight cage"),
                ),
            ),
        ),
        GLOAM_GLASS_FAULT_KEY: RoomAugmentation(
            features=(
                _feature(
                    "gloam_glass_fault",
                    "Glass Fault",
                    "the black translucent plane that ignores the ordinary rules of fracture",
                    "Close inspection makes the cut stranger, not clearer. Native rock ends against it without crushed grains, and an iron pipe continues visibly for a finger-width inside before perspective stops agreeing about where the pipe went.",
                    ("fault", "glass", "black plane", "plane"),
                ),
            ),
            description_layers=race_layers,
        ),
        GLOAM_RESONANCE_SHAFT_KEY: RoomAugmentation(
            features=(
                _feature(
                    "gloam_resonance",
                    "Resonance",
                    "the second almost-correct echo following every ordinary sound",
                    "Clap once and the shaft gives the clap back normally. A moment later it produces a second version with the same beginning and a subtly different ending, as if something learned the sound after hearing it once.",
                    ("echo", "resonance", "shaft"),
                ),
            ),
            description_layers=class_layers,
        ),
        GLOAM_TWIN_SEAL_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    direction="east",
                    destination_key=GLOAM_BURIED_COURT_KEY,
                    name="Buried Court",
                    travel_text="Both handplates remain warm behind you as the circular door rolls aside.",
                    condition=ViewCondition(required_flags=(GLOAMWORKS_TWIN_SEAL_FLAG,), min_level=4),
                    hidden_when_unavailable=True,
                    failure_text="The circular door has no single-person release. Two explorers must HOLD LEFT SEAL and HOLD RIGHT SEAL together.",
                ),
            ),
            features=(
                _feature(
                    "gloam_twin_handplates",
                    "Twin Handplates",
                    "two widely separated mechanical seals designed for simultaneous witnesses",
                    "The plates are deliberately beyond one person's reach. Their mechanism is old but mundane: both mechanical locks must carry weight at once. Whatever lies beyond, the builders refused to let one person make the decision alone.",
                    ("seals", "handplates", "left seal", "right seal", "plates"),
                ),
            ),
        ),
        GLOAM_BREACH_VAULT_KEY: RoomAugmentation(
            description_layers=(
                DescriptionLayer(
                    key="gloam_aftermath",
                    text="Your expedition has converted one old rumor into a worse fact: the Gloamworks did not create the anomaly. The miners found one branch of something much larger.",
                    priority=30,
                    condition=ViewCondition(required_flags=(GLOAMWORKS_REGENT_FLAG,)),
                ),
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


def install_gloamworks_content(world_service=None) -> None:
    if GLOAMWORKS_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GLOAMWORKS_QUEST,)
    quests.QUESTS_BY_KEY[GLOAMWORKS_QUEST.key] = GLOAMWORKS_QUEST

    for item in GLOAMWORKS_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for enemy in GLOAMWORKS_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    for room in GLOAMWORKS_ROOMS:
        _replace_room(room)
    _replace_npc(SURVEYOR)

    if world_service is None:
        return
    for room in GLOAMWORKS_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in gloamworks_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*GLOAMWORKS_ROOM_KEYS, WAYMEET_GLOAM_MOUTH_KEY):
            cache.pop(room_key, None)


_ACTIVE_SESSIONS: weakref.WeakSet = weakref.WeakSet()
_SEAL_HOLDS: dict[int, str] = {}


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, GLOAMWORKS_QUEST_KEY)


def _ensure_quest(session) -> bool:
    if session.character is None or session.character.level < 4:
        return False
    flags = session.database.list_flags(session.character.id)
    if WAYMEET_INTRO_COMPLETE_FLAG not in flags:
        return False
    if session.database.get_quest(session.character.id, GLOAMWORKS_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, GLOAMWORKS_QUEST_KEY, "talk_surveyor")
    return True


async def _talk_surveyor(session) -> bool:
    if session.character is None or session.character.current_room != WAYMEET_GLOAM_MOUTH_KEY:
        return False
    if not _ensure_quest(session):
        await session.send("Pell checks your road marks. 'Finish learning Waymeet first, then come back when you're at least level 4.'\r\n")
        return True
    q = _quest(session)
    if q is None:
        return True
    if q["status"] == "completed":
        await session.send("Pell taps the copied breach map. 'The next problem is east now. Greywake has started hearing the same note.'\r\n")
        return True
    if q["current_step"] == "talk_surveyor":
        session.database.advance_quest(session.character.id, GLOAMWORKS_QUEST_KEY, "enter_works")
        await session.send(
            "Pell clips a second safety line to the cage. 'Upper levels first. If the deep rooms disagree with your eyes, report what you actually perceived. And the last seal takes two people. That part is not negotiable.'\r\n"
        )
    elif q["current_step"] == "return_surveyor":
        session.database.complete_quest(session.character.id, GLOAMWORKS_QUEST_KEY)
        session.database.grant_flag(session.character.id, GLOAMWORKS_COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 180)
        session.database.add_item(session.character.id, REGENT_SHARD_KEY, 1)
        _refresh_character(session)
        await session.send(
            "Pell listens without interrupting, then circles the eastward marks on the final survey. 'So it continues under the Greywake March. Fine. We stop calling this a mine problem.'\r\n"
            "Quest complete: Below the Sealed Door. You gain 180 XP and keep a Regent Shard from the survey evidence.\r\n"
        )
    else:
        await session.send("Pell says, 'Bring me the whole route, not half a theory. The survey is still open.'\r\n")
    return True


async def _inspect_fault(session) -> bool:
    if session.character is None or session.character.current_room != GLOAM_GLASS_FAULT_KEY:
        return False
    q = _quest(session)
    if q and q["status"] == "active" and q["current_step"] in {"enter_works", "read_fault"}:
        session.database.grant_flag(session.character.id, GLOAMWORKS_FAULT_READ_FLAG)
        session.database.advance_quest(session.character.id, GLOAMWORKS_QUEST_KEY, "defeat_brake_saint")
        session.database.add_item(session.character.id, COLD_GLASS_KEY, 1)
        await session.send(
            "You record what the fault actually does to your perception rather than forcing it into somebody else's explanation. A thin flake lies loose at the base; you bag it without touching the main plane.\r\n"
            "The expedition journal updates: compare impressions, then continue toward the Brake Chapel.\r\n"
        )
    return True


def _sessions_in_room(room_key: str, peers: Iterable | None = None) -> list:
    pool = list(peers) if peers is not None else list(_ACTIVE_SESSIONS)
    result = []
    for other in pool:
        character = getattr(other, "character", None)
        if character is not None and character.current_room == room_key:
            result.append(other)
    return result


async def _attempt_seal_hold(session, side: str, peers: Iterable | None = None) -> bool:
    if session.character is None or session.character.current_room != GLOAM_TWIN_SEAL_KEY:
        return False
    side = side.strip().lower()
    if side not in {"left", "right"}:
        await session.send("Choose HOLD LEFT SEAL or HOLD RIGHT SEAL.\r\n")
        return True
    _SEAL_HOLDS[session.character.id] = side
    opposite = "right" if side == "left" else "left"
    partner = None
    for other in _sessions_in_room(GLOAM_TWIN_SEAL_KEY, peers):
        if other is session or other.character is None:
            continue
        if _SEAL_HOLDS.get(other.character.id) == opposite:
            partner = other
            break
    if partner is None:
        await session.send(
            f"You lean into the {side} handplate. The mechanism takes your weight, but the opposite lock stays hard. Another player must HOLD {opposite.upper()} SEAL while you remain here.\r\n"
        )
        return True

    pair = (session, partner)
    for explorer in pair:
        if explorer.character is None:
            continue
        explorer.database.grant_flag(explorer.character.id, GLOAMWORKS_TWIN_SEAL_FLAG)
        q = explorer.database.get_quest(explorer.character.id, GLOAMWORKS_QUEST_KEY)
        if q and q["status"] == "active" and q["current_step"] == "sync_seals":
            explorer.database.advance_quest(explorer.character.id, GLOAMWORKS_QUEST_KEY, "defeat_regent")
        await explorer.send(
            "Both handplates sink at once. Two independent locks answer with the same deep click, and the circular door begins to roll aside. No class, creed, or race was required—only another person willing to hold the other side.\r\n"
        )
    return True


def _group_ready_for_regent(session, peers: Iterable | None = None) -> bool:
    if session.character is None:
        return False
    ready = 0
    for other in _sessions_in_room(GLOAM_BURIED_COURT_KEY, peers):
        if other.character is None:
            continue
        flags = other.database.list_flags(other.character.id)
        if GLOAMWORKS_TWIN_SEAL_FLAG in flags:
            ready += 1
    return ready >= 2


async def _record_enemy_defeat(session, enemy_key: str) -> None:
    if session.character is None:
        return
    q = _quest(session)
    if enemy_key == BRAKE_SAINT_KEY:
        session.database.grant_flag(session.character.id, GLOAMWORKS_BRAKE_FLAG)
        session.database.add_item(session.character.id, RESONANT_COG_KEY, 1)
        if q and q["status"] == "active" and q["current_step"] == "defeat_brake_saint":
            session.database.advance_quest(session.character.id, GLOAMWORKS_QUEST_KEY, "defeat_mother_sparks")
        await session.send("The Brake Saint collapses with both emergency arms still trying to pull STOP. You recover one resonant safety cog.\r\n")
    elif enemy_key == MOTHER_SPARKS_KEY:
        session.database.grant_flag(session.character.id, GLOAMWORKS_DYNAMO_FLAG)
        if q and q["status"] == "active" and q["current_step"] == "defeat_mother_sparks":
            session.database.advance_quest(session.character.id, GLOAMWORKS_QUEST_KEY, "sync_seals")
        await session.send("Mother-of-Sparks tears free of the dynamo. The false current dies, leaving the deeper seal mechanically reachable.\r\n")
    elif enemy_key == BURIED_REGENT_KEY:
        # Credit every synchronized explorer still sharing the boss chamber.
        participants = _sessions_in_room(GLOAM_BURIED_COURT_KEY)
        if session not in participants:
            participants.append(session)
        for explorer in participants:
            if explorer.character is None:
                continue
            flags = explorer.database.list_flags(explorer.character.id)
            if GLOAMWORKS_TWIN_SEAL_FLAG not in flags:
                continue
            explorer.database.grant_flag(explorer.character.id, GLOAMWORKS_REGENT_FLAG)
            q2 = explorer.database.get_quest(explorer.character.id, GLOAMWORKS_QUEST_KEY)
            if q2 and q2["status"] == "active" and q2["current_step"] == "defeat_regent":
                explorer.database.advance_quest(explorer.character.id, GLOAMWORKS_QUEST_KEY, "return_surveyor")
            if explorer is not session:
                explorer.database.add_experience(explorer.character.id, 90)
                _refresh_character(explorer)
            await explorer.send(
                "The Buried Regent finally comes apart where old drill frame meets impossible mineral. Behind it, the breach survey vault stands open. The expedition journal says one thing clearly: return to Pell when you are ready.\r\n"
            )


def install_gloamworks_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_gloamworks_runtime_installed", False):
        return
    install_gloamworks_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_prompt = player_session_class.playing_prompt
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        _ACTIVE_SESSIONS.add(self)
        if self.character is not None and self.character.current_room == WAYMEET_GLOAM_MOUTH_KEY:
            _ensure_quest(self)

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move(self, direction)
        if self.character is None:
            return
        _ACTIVE_SESSIONS.add(self)
        after = self.character.current_room
        if after == GLOAM_ENTRY_KEY:
            q = _quest(self)
            if q and q["status"] == "active" and q["current_step"] == "enter_works":
                self.database.advance_quest(self.character.id, GLOAMWORKS_QUEST_KEY, "read_fault")
                await self.send("The cage settles beneath Waymeet. The expedition journal marks the Glass Fault as your first deep objective.\r\n")
        if before == GLOAM_TWIN_SEAL_KEY and after != GLOAM_TWIN_SEAL_KEY:
            _SEAL_HOLDS.pop(self.character.id, None)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        _ACTIVE_SESSIONS.add(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()
        room_key = self.character.current_room or ""

        handled = False
        if normalized in {"talk surveyor", "talk pell", "speak surveyor", "speak pell"}:
            handled = await _talk_surveyor(self)
        elif room_key == GLOAM_GLASS_FAULT_KEY and normalized in {"examine fault", "look fault", "examine glass fault", "look glass fault"}:
            handled = await _inspect_fault(self)
        elif normalized in {"hold left seal", "hold left", "press left seal"}:
            handled = await _attempt_seal_hold(self, "left")
        elif normalized in {"hold right seal", "hold right", "press right seal"}:
            handled = await _attempt_seal_hold(self, "right")
        elif room_key in {GLOAM_GLASS_FAULT_KEY, GLOAM_RESONANCE_SHAFT_KEY} and normalized in {"impression", "what did i see", "compare impression"}:
            context = world_service.build_view(room_key, __import__("mud.room_runtime", fromlist=["_context_for"])._context_for(self))
            if context is not None:
                await self.send(context.description + "\r\n")
            handled = True
        elif room_key == GLOAM_BURIED_COURT_KEY and normalized.startswith("attack ") and ("regent" in normalized):
            if not _group_ready_for_regent(self):
                await self.send(
                    "The Regent's pressure field turns a lone attack aside. The old two-witness seal was a warning as much as a lock: at least two synchronized players must remain in the Buried Court for this encounter.\r\n"
                )
                handled = True

        if handled:
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str):
            return command

        self.prompt = replay_prompt
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    async def finish_enemy(self, enemy) -> None:
        enemy_key = enemy.definition.key
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if was_active and self.character is not None:
            await _record_enemy_defeat(self, enemy_key)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._gloamworks_runtime_installed = True
