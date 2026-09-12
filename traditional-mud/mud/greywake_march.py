from __future__ import annotations

import asyncio
import weakref
from dataclasses import dataclass, replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY, WAYMEET_SCRIP_KEY
from mud.world import NpcDefinition, RoomDefinition


GREYWAKE_REGION_KEY = "greywake_march"
GREYWAKE_WEST_MILE_KEY = "greywake_west_mile"
GREYWAKE_THREE_BANNER_KEY = "greywake_three_banner_camp"
GREYWAKE_WARDEN_POST_KEY = "greywake_warden_post"
GREYWAKE_LEDGER_CUT_KEY = "greywake_ledger_cut"
GREYWAKE_LANTERN_HOSPICE_KEY = "greywake_lantern_hospice"
GREYWAKE_HEATH_KEY = "greywake_heath"
GREYWAKE_SUNK_CAUSEWAY_KEY = "greywake_sunk_causeway"
GREYWAKE_RESONANT_ORCHARD_KEY = "greywake_resonant_orchard"
GREYWAKE_SIGNAL_HILL_KEY = "greywake_signal_hill"
GREYWAKE_RIFTFIELD_KEY = "greywake_riftfield"
GREYWAKE_OLD_AQUEDUCT_KEY = "greywake_old_aqueduct"
GREYWAKE_VEYRA_ROAD_KEY = "greywake_veyra_road"
GREYWAKE_VEYRA_GATE_KEY = "greywake_veyra_outer_gate"

GREYWAKE_ROOM_KEYS = (
    GREYWAKE_WEST_MILE_KEY,
    GREYWAKE_THREE_BANNER_KEY,
    GREYWAKE_WARDEN_POST_KEY,
    GREYWAKE_LEDGER_CUT_KEY,
    GREYWAKE_LANTERN_HOSPICE_KEY,
    GREYWAKE_HEATH_KEY,
    GREYWAKE_SUNK_CAUSEWAY_KEY,
    GREYWAKE_RESONANT_ORCHARD_KEY,
    GREYWAKE_SIGNAL_HILL_KEY,
    GREYWAKE_RIFTFIELD_KEY,
    GREYWAKE_OLD_AQUEDUCT_KEY,
    GREYWAKE_VEYRA_ROAD_KEY,
    GREYWAKE_VEYRA_GATE_KEY,
)

AFTER_GLOAM_QUEST_KEY = "greywake_after_the_gloam"
THREE_CLAIMS_QUEST_KEY = "greywake_three_claims"
BELL_BELOW_WIND_QUEST_KEY = "greywake_bell_below_wind"
GREYWAKE_CHAIN_COMPLETE_FLAG = "greywake_first_chain_complete"
ROADWARDEN_FLAG = "greywake_support_roadwarden"
LEDGER_FLAG = "greywake_support_deep_ledger"
LANTERN_FLAG = "greywake_support_lantern_oath"
GREYWAKE_SURGE_VETERAN_FLAG = "greywake_surge_veteran"

SURGE_SPLINTER_KEY = "greywake_surge_splinter"
MARCH_TOKEN_KEY = "greywake_march_token"

ASHWING_KEY = "greywake_ashwing_kite"
BELLHIDE_KEY = "greywake_bellhide_grazer"
DITCHSTALKER_KEY = "greywake_ditchstalker"
SHIVER_KEY = "greywake_march_shiver"
RIFTLING_KEY = "greywake_riftling"

ROADWARDEN_NPC_KEY = "greywake_captain_oryn_vale"
LEDGER_NPC_KEY = "greywake_factor_merrit_deepcoin"
LANTERN_NPC_KEY = "greywake_keeper_ela_voss"


@dataclass(frozen=True, slots=True)
class FactionDefinition:
    key: str
    name: str
    belief: str
    risk: str
    support_flag: str


FACTIONS: tuple[FactionDefinition, ...] = (
    FactionDefinition(
        key="roadwarden_compact",
        name="Roadwarden Compact",
        belief="Keep movement possible first. Open roads let every other institution function, including the ones that disagree with the wardens.",
        risk="Their urgency can turn uncertainty into a maintenance problem and push them to reopen dangerous ground too quickly.",
        support_flag=ROADWARDEN_FLAG,
    ),
    FactionDefinition(
        key="deep_ledger_consortium",
        name="Deep Ledger Consortium",
        belief="Study, salvage, and account for the anomaly instead of abandoning valuable material and knowledge to fear.",
        risk="Their appetite for useful discoveries can make containment feel like wasted opportunity.",
        support_flag=LEDGER_FLAG,
    ),
    FactionDefinition(
        key="lantern_oath",
        name="Lantern Oath",
        belief="Protect settlements and publish what is known before anyone decides the strange material belongs to them.",
        risk="Their caution can harden into permanent quarantine even when controlled access would help the March survive.",
        support_flag=LANTERN_FLAG,
    ),
)
FACTIONS_BY_KEY = {faction.key: faction for faction in FACTIONS}


AFTER_GLOAM_QUEST = QuestDefinition(
    key=AFTER_GLOAM_QUEST_KEY,
    name="After the Gloam",
    style="structured",
    minimum_level=5,
    description="The final Gloamworks map points east. Follow the same resonance into the Greywake March and determine whether the underground breach is already affecting the surface.",
    objective_steps=(
        ("reach_camp", "Reach Three-Banner Camp east of Gloam Mouth and TALK CAPTAIN."),
        ("inspect_heath", "EXAMINE GREY CRUST on Greywake Heath."),
        ("inspect_orchard", "EXAMINE TREES in the Resonant Orchard."),
        ("inspect_riftfield", "EXAMINE SEAM at Riftfield."),
        ("return_camp", "Return to Three-Banner Camp and TALK CAPTAIN."),
        ("complete", "You proved the Gloamworks resonance is appearing at multiple surface sites across the March."),
    ),
)

THREE_CLAIMS_QUEST = QuestDefinition(
    key=THREE_CLAIMS_QUEST_KEY,
    name="Three Claims on One Road",
    style="structured",
    minimum_level=6,
    description="Three groups agree the March is in danger and disagree about what responsibility means. Hear each argument before choosing whose plan you will support first.",
    objective_steps=(
        ("hear_roadwarden", "TALK CAPTAIN at the Roadwarden Post."),
        ("hear_ledger", "TALK FACTOR at Ledger Cut."),
        ("hear_lantern", "TALK KEEPER at Lantern Hospice."),
        ("pledge", "At Three-Banner Camp choose SUPPORT ROADWARDEN, SUPPORT LEDGER, or SUPPORT LANTERN."),
        ("complete", "You chose which practical risk you are willing to accept first. The other factions remain part of the March."),
    ),
)

BELL_BELOW_WIND_QUEST = QuestDefinition(
    key=BELL_BELOW_WIND_QUEST_KEY,
    name="The Bell Below the Wind",
    style="structured",
    minimum_level=7,
    description="The signal bell on Greywake Hill has started answering a second note from underground. Rally travelers when a Gloam Surge breaks the surface and hold the road until the event collapses.",
    objective_steps=(
        ("rally", "At Signal Hill use RALLY SURGE to sound the March alarm."),
        ("break_surge", "Defeat Greywake Riftlings during the shared Gloam Surge until the event counter reaches zero."),
        ("report", "Return to Three-Banner Camp and TALK CAPTAIN."),
        ("complete", "You helped hold a live world event and opened the eastern road toward Veyra."),
    ),
)

GREYWAKE_QUESTS = (AFTER_GLOAM_QUEST, THREE_CLAIMS_QUEST, BELL_BELOW_WIND_QUEST)


SURGE_SPLINTER = ItemDefinition(
    key=SURGE_SPLINTER_KEY,
    name="Surge Splinter",
    description="A needle of black-violet material cooled after a Greywake Riftling collapsed. It hums only during active surges.",
    category="material",
    tier=2,
)
MARCH_TOKEN = ItemDefinition(
    key=MARCH_TOKEN_KEY,
    name="Greywake March Token",
    description="A three-stamped brass token marking service during a Greywake surge: road, ledger, and lantern marks share the same face.",
    category="trophy",
    tier=2,
)
GREYWAKE_ITEMS = (SURGE_SPLINTER, MARCH_TOKEN)


ASHWING = EnemyDefinition(
    key=ASHWING_KEY,
    name="Ashwing Kite",
    aliases=("kite", "ashwing", "ashwing kite"),
    description="a broad-winged scavenger that uses warm updrafts over resonant ground and drops stone hard seed-pods at threats below",
    max_hp=82,
    armor_class=8,
    auto_attack_damage=7,
    auto_attack_interval=3.0,
    xp_reward=58,
)
BELLHIDE = EnemyDefinition(
    key=BELLHIDE_KEY,
    name="Bellhide Grazer",
    aliases=("grazer", "bellhide", "bellhide grazer"),
    description="a heavy antlered herbivore whose hollow shoulder plates ring softly when it runs, agitated by underground resonance",
    max_hp=108,
    armor_class=10,
    auto_attack_damage=8,
    auto_attack_interval=3.1,
    xp_reward=76,
)
DITCHSTALKER = EnemyDefinition(
    key=DITCHSTALKER_KEY,
    name="Ditchstalker",
    aliases=("stalker", "ditchstalker", "ditch stalker"),
    description="a long-bodied ambush animal that buries itself in wet roadside cuts with only its reedlike whiskers exposed",
    max_hp=118,
    armor_class=11,
    auto_attack_damage=9,
    auto_attack_interval=2.9,
    xp_reward=86,
)
SHIVER = EnemyDefinition(
    key=SHIVER_KEY,
    name="March Shiver",
    aliases=("shiver", "march shiver"),
    description="a loose constellation of black mineral flakes that travels against the wind as if deciding where to become solid next",
    max_hp=132,
    armor_class=12,
    auto_attack_damage=10,
    auto_attack_interval=2.8,
    xp_reward=98,
)
RIFTLING = EnemyDefinition(
    key=RIFTLING_KEY,
    name="Greywake Riftling",
    aliases=("riftling", "greywake riftling", "gloam riftling"),
    description="a temporary animal-shaped extrusion of black-violet matter, assembling itself from local stone and grass around a moving empty center",
    max_hp=96,
    armor_class=11,
    auto_attack_damage=9,
    auto_attack_interval=2.7,
    xp_reward=82,
)
GREYWAKE_ENEMIES = (ASHWING, BELLHIDE, DITCHSTALKER, SHIVER, RIFTLING)


ROADWARDEN_NPC = NpcDefinition(
    key=ROADWARDEN_NPC_KEY,
    name="Captain Oryn Vale",
    short_description="a Roadwarden captain pinning repair priorities over a map already patched in six places",
    room_key=GREYWAKE_WARDEN_POST_KEY,
    role="Roadwarden Compact representative",
    dialogue=(
        "'A road is not scenery. It is food, medicine, witnesses, reinforcements, funerals, marriages, and the ability to leave.'",
        "'I will accept the accusation that we reopen things too quickly. I would rather argue about a road we can still reach.'",
    ),
)
LEDGER_NPC = NpcDefinition(
    key=LEDGER_NPC_KEY,
    name="Factor Merrit Deepcoin",
    short_description="a Deep Ledger factor weighing a black splinter against three perfectly ordinary ore samples",
    room_key=GREYWAKE_LEDGER_CUT_KEY,
    role="Deep Ledger Consortium representative",
    dialogue=(
        "'Fear is not a measurement. Neither is greed. We take samples, record losses, price risk, and learn what the thing actually does.'",
        "'Yes, discovery can make fools reckless. Ignorance can make whole countries helpless.'",
    ),
)
LANTERN_NPC = NpcDefinition(
    key=LANTERN_NPC_KEY,
    name="Keeper Ela Voss",
    short_description="a Lantern Oath keeper copying exposure notes beside clean bandages and sealed sample jars",
    room_key=GREYWAKE_LANTERN_HOSPICE_KEY,
    role="Lantern Oath representative",
    dialogue=(
        "'Containment is not cowardice. It is deciding that the person downstream gets a vote before we pour something into the river.'",
        "'But quarantine can become laziness too. If we close a place, we owe people evidence for why it stays closed.'",
    ),
)
GREYWAKE_NPCS = (ROADWARDEN_NPC, LEDGER_NPC, LANTERN_NPC)


def _room(key: str, name: str, description: str, exits: dict[str, str], *, npcs: tuple[str, ...] = (), enemies: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=GREYWAKE_REGION_KEY,
        description=description,
        exits=exits,
        npc_keys=npcs,
        enemy_keys=enemies,
        tags=("shared_world", "greywake", "level_5_10", *tags),
    )


GREYWAKE_ROOMS: tuple[RoomDefinition, ...] = (
    _room(
        GREYWAKE_WEST_MILE_KEY,
        "Greywake West Mile",
        "The road east of Gloam Mouth crosses open country under a sky that feels much larger after the mine. Waymeet repair marks thin out while milestone stones begin naming Veyra, the first major city on this road.",
        {"west": WAYMEET_GLOAM_MOUTH_KEY, "east": GREYWAKE_THREE_BANNER_KEY},
        enemies=(ASHWING_KEY,), tags=("level_5", "road"),
    ),
    _room(
        GREYWAKE_THREE_BANNER_KEY,
        "Three-Banner Camp",
        "Three practical organizations share one muddy camp and very little philosophy. A Roadwarden repair banner, a Deep Ledger survey pennant, and a Lantern Oath lamp standard stand around the same well because none of them can afford a separate water source.",
        {"west": GREYWAKE_WEST_MILE_KEY, "north": GREYWAKE_WARDEN_POST_KEY, "south": GREYWAKE_LEDGER_CUT_KEY, "east": GREYWAKE_LANTERN_HOSPICE_KEY},
        tags=("safe", "faction_hub", "social"),
    ),
    _room(
        GREYWAKE_WARDEN_POST_KEY,
        "Roadwarden Post",
        "A low palisade surrounds timber, gravel, spare bridge pins, tow ropes, and an aggressively unromantic map of everything currently broken between Waymeet and Veyra.",
        {"south": GREYWAKE_THREE_BANNER_KEY, "east": GREYWAKE_HEATH_KEY},
        npcs=(ROADWARDEN_NPC_KEY,), tags=("safe", "faction", "roadwarden"),
    ),
    _room(
        GREYWAKE_LEDGER_CUT_KEY,
        "Ledger Cut",
        "A shallow commercial excavation exposes several layers of ordinary useful stone beside one roped-off seam that refuses to match any assay. Every sample bag has a number before it has a theory.",
        {"north": GREYWAKE_THREE_BANNER_KEY, "east": GREYWAKE_SUNK_CAUSEWAY_KEY},
        npcs=(LEDGER_NPC_KEY,), enemies=(BELLHIDE_KEY,), tags=("faction", "deep_ledger", "level_6"),
    ),
    _room(
        GREYWAKE_LANTERN_HOSPICE_KEY,
        "Lantern Hospice",
        "A roadside hospice combines sickbeds, clean water, sample lockers, and a public notice wall listing known exposure symptoms beside a much longer list titled THINGS WE DO NOT YET KNOW.",
        {"west": GREYWAKE_THREE_BANNER_KEY, "east": GREYWAKE_RESONANT_ORCHARD_KEY},
        npcs=(LANTERN_NPC_KEY,), tags=("safe", "faction", "lantern_oath"),
    ),
    _room(
        GREYWAKE_HEATH_KEY,
        "Greywake Heath",
        "Low grass bends under constant west wind. Here and there the soil carries patches of brittle grey crust that ring faintly under a boot heel despite containing no visible metal.",
        {"west": GREYWAKE_WARDEN_POST_KEY, "south": GREYWAKE_SIGNAL_HILL_KEY},
        enemies=(ASHWING_KEY, SHIVER_KEY), tags=("event_site", "level_6"),
    ),
    _room(
        GREYWAKE_SUNK_CAUSEWAY_KEY,
        "Sunk Causeway",
        "An old paved road has settled unevenly into marshy ground. Roadwarden cribbing keeps one lane passable while Deep Ledger stakes mark places where the subsidence forms suspiciously straight lines.",
        {"west": GREYWAKE_LEDGER_CUT_KEY, "north": GREYWAKE_SIGNAL_HILL_KEY, "east": GREYWAKE_RIFTFIELD_KEY},
        enemies=(DITCHSTALKER_KEY,), tags=("event_site", "level_6_7"),
    ),
    _room(
        GREYWAKE_RESONANT_ORCHARD_KEY,
        "Resonant Orchard",
        "An abandoned pear orchard still fruits, but every seventh tree has grown its roots away from the same invisible underground line. When wind shakes the branches, one row answers with a low note from the soil.",
        {"west": GREYWAKE_LANTERN_HOSPICE_KEY, "north": GREYWAKE_SIGNAL_HILL_KEY, "east": GREYWAKE_OLD_AQUEDUCT_KEY},
        enemies=(BELLHIDE_KEY,), tags=("level_6_7", "evidence"),
    ),
    _room(
        GREYWAKE_SIGNAL_HILL_KEY,
        "Signal Hill",
        "A timber signal tower stands where three regional roads can see it. The alarm bell was cast for storms and bandit raids. Since the Gloamworks opened, it sometimes produces a second quieter note after nobody has touched it.",
        {"north": GREYWAKE_HEATH_KEY, "south": GREYWAKE_SUNK_CAUSEWAY_KEY, "west": GREYWAKE_RESONANT_ORCHARD_KEY, "east": GREYWAKE_RIFTFIELD_KEY},
        tags=("safe", "world_event_hub", "level_7"),
    ),
    _room(
        GREYWAKE_RIFTFIELD_KEY,
        "Riftfield",
        "A pasture is split by a ruler-straight seam of blackened soil. Nothing dramatic rises from it. That makes the line worse: worms stop at one side, rain drains differently across it, and fence posts on opposite banks disagree about which way is vertical.",
        {"west": GREYWAKE_SIGNAL_HILL_KEY, "south": GREYWAKE_SUNK_CAUSEWAY_KEY, "east": GREYWAKE_OLD_AQUEDUCT_KEY},
        enemies=(SHIVER_KEY,), tags=("event_site", "level_7_8", "alien"),
    ),
    _room(
        GREYWAKE_OLD_AQUEDUCT_KEY,
        "Old Veyra Aqueduct",
        "A weathered aqueduct carries clean mountain water west from Veyra. Lantern Oath seals mark one inspected arch while Roadwardens have built a temporary bridge beneath another. The city is close enough now that its outer towers show above the hills.",
        {"west": GREYWAKE_RIFTFIELD_KEY, "south": GREYWAKE_RESONANT_ORCHARD_KEY, "east": GREYWAKE_VEYRA_ROAD_KEY},
        enemies=(DITCHSTALKER_KEY,), tags=("level_8_9", "city_approach"),
    ),
    _room(
        GREYWAKE_VEYRA_ROAD_KEY,
        "Veyra Gate Road",
        "Traffic thickens into actual city-bound movement: farm carts, couriers, pilgrims, hired guards, merchants, and exhausted Waymeet crews. Greywake stops feeling like empty frontier and starts feeling like the economic shadow of a city.",
        {"west": GREYWAKE_OLD_AQUEDUCT_KEY, "east": GREYWAKE_VEYRA_GATE_KEY},
        enemies=(ASHWING_KEY,), tags=("level_9", "city_approach"),
    ),
    _room(
        GREYWAKE_VEYRA_GATE_KEY,
        "Veyra Outer Gate",
        "Veyra finally occupies the eastern horizon as architecture rather than rumor: layered stone walls, crowded roofs, water towers, bell houses, and high bridges climbing a river bluff. The outer gate district is visible beyond the checkpoint, but that city chapter has not opened yet.",
        {"west": GREYWAKE_VEYRA_ROAD_KEY},
        tags=("safe", "level_10", "first_city_gate", "future_city"),
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


def greywake_augmentations() -> dict[str, RoomAugmentation]:
    return {
        WAYMEET_GLOAM_MOUTH_KEY: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east",
                    destination_key=GREYWAKE_WEST_MILE_KEY,
                    name="Greywake March",
                    travel_text="You follow the final Gloamworks survey mark east onto the Greywake road.",
                    condition=ViewCondition(required_flags=(GLOAMWORKS_COMPLETE_FLAG,), min_level=5),
                    hidden_when_unavailable=True,
                ),
            ),
        ),
        GREYWAKE_HEATH_KEY: RoomAugmentation(
            features=(
                _feature("greywake_crust", "Grey Crust", "brittle ringing mineral skin across patches of soil", "The crust is not growing on the grass. It forms under the roots and lifts them as one sheet. Scraping it reveals ordinary soil underneath and a cold straight boundary below that.", ("crust", "grey crust", "soil")),
            ),
        ),
        GREYWAKE_RESONANT_ORCHARD_KEY: RoomAugmentation(
            features=(
                _feature("greywake_orchard_trees", "Turned Trees", "pear trees whose roots all avoid the same underground line", "The affected trees are alive and fruiting. Their roots simply refuse to cross one shared invisible boundary, repeating the avoidance pattern seen around the deepest Gloamworks fault.", ("trees", "roots", "orchard")),
            ),
        ),
        GREYWAKE_RIFTFIELD_KEY: RoomAugmentation(
            features=(
                _feature("greywake_surface_seam", "Surface Seam", "a ruler-straight boundary where ordinary ground disagrees with itself", "The seam has no open crack. Instead, drainage, worm tracks, grass roots, and even fence-post lean all change by a few degrees exactly at the line. The effect continues northeast toward Veyra.", ("seam", "rift", "black line")),
            ),
        ),
        GREYWAKE_SIGNAL_HILL_KEY: RoomAugmentation(
            features=(
                _feature("greywake_signal_bell", "March Signal Bell", "the shared alarm bell used to rally travelers during regional danger", "Three organizations maintain the same bell. Its rope is ordinary hemp, its frame ordinary timber, and its second underground note is not ordinary at all. Use RALLY SURGE when the Bell Below the Wind quest is active.", ("bell", "signal bell", "alarm")),
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


def install_greywake_content(world_service=None) -> None:
    for quest in GREYWAKE_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for item in GREYWAKE_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for enemy in GREYWAKE_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for room in GREYWAKE_ROOMS:
        _replace_room(room)
    for npc in GREYWAKE_NPCS:
        _replace_npc(npc)
    if world_service is None:
        return
    for room in GREYWAKE_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for room_key, augmentation in greywake_augmentations().items():
        world_service.augmentations[room_key] = _merge_augmentation(world_service.augmentations.get(room_key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*GREYWAKE_ROOM_KEYS, WAYMEET_GLOAM_MOUTH_KEY):
            cache.pop(room_key, None)


@dataclass(slots=True)
class GloamSurgeState:
    active: bool = False
    remaining: int = 0
    generation: int = 0

    def start(self, strength: int = 6) -> None:
        self.active = True
        self.remaining = max(1, strength)
        self.generation += 1

    def record_kill(self) -> bool:
        if not self.active:
            return False
        self.remaining = max(0, self.remaining - 1)
        if self.remaining == 0:
            self.active = False
            return True
        return False


SURGE_STATE = GloamSurgeState()
SURGE_EVENT_ROOMS = (GREYWAKE_HEATH_KEY, GREYWAKE_SUNK_CAUSEWAY_KEY, GREYWAKE_RIFTFIELD_KEY)
_ACTIVE_SESSIONS: weakref.WeakSet = weakref.WeakSet()
_SURGE_PARTICIPANTS: set[int] = set()


def _refresh(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _ensure_after_gloam(session) -> bool:
    if session.character is None or session.character.level < 5:
        return False
    if GLOAMWORKS_COMPLETE_FLAG not in session.database.list_flags(session.character.id):
        return False
    if _quest(session, AFTER_GLOAM_QUEST_KEY) is None:
        session.database.start_quest(session.character.id, AFTER_GLOAM_QUEST_KEY, "reach_camp")
    return True


async def _talk_captain(session) -> bool:
    if session.character is None or session.character.current_room not in {GREYWAKE_THREE_BANNER_KEY, GREYWAKE_WARDEN_POST_KEY}:
        return False
    if not _ensure_after_gloam(session):
        return False
    q1 = _quest(session, AFTER_GLOAM_QUEST_KEY)
    if q1 and q1["status"] == "active":
        if q1["current_step"] == "reach_camp":
            session.database.advance_quest(session.character.id, AFTER_GLOAM_QUEST_KEY, "inspect_heath")
            await session.send("Oryn spreads Pell's copied map beside three new surface reports. 'Good. Check the heath crust, the orchard roots, and Riftfield. Same cause or three different problems—we need to know.'\r\n")
            return True
        if q1["current_step"] == "return_camp":
            session.database.complete_quest(session.character.id, AFTER_GLOAM_QUEST_KEY)
            session.database.start_quest(session.character.id, THREE_CLAIMS_QUEST_KEY, "hear_roadwarden")
            session.database.add_experience(session.character.id, 120)
            _refresh(session)
            await session.send("Oryn pins all three observations to one line. 'Same family of problem. Now hear what each of us wants to do about it before you help anyone.' After the Gloam complete: 120 XP.\r\n")
            return True
    q3 = _quest(session, BELL_BELOW_WIND_QUEST_KEY)
    if q3 and q3["status"] == "active" and q3["current_step"] == "report" and GREYWAKE_SURGE_VETERAN_FLAG in session.database.list_flags(session.character.id):
        session.database.complete_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY)
        session.database.grant_flag(session.character.id, GREYWAKE_CHAIN_COMPLETE_FLAG)
        session.database.add_experience(session.character.id, 220)
        session.database.add_item(session.character.id, MARCH_TOKEN_KEY, 1)
        _refresh(session)
        await session.send("Oryn hears the surge count, then points east. 'Veyra's road is open. Take the result there before the city decides Greywake is only a rumor.' The Bell Below the Wind complete: 220 XP and a Greywake March Token.\r\n")
        return True
    await session.send("Oryn says, 'The March still has work for you. Check your QUESTS and bring back observations, not guesses.'\r\n")
    return True


async def _inspect_site(session, site: str) -> bool:
    if session.character is None:
        return False
    q = _quest(session, AFTER_GLOAM_QUEST_KEY)
    if not q or q["status"] != "active":
        return False
    steps = {
        GREYWAKE_HEATH_KEY: ("inspect_heath", "inspect_orchard", "The grey crust is underground-first growth: it lifts living roots instead of coating them."),
        GREYWAKE_RESONANT_ORCHARD_KEY: ("inspect_orchard", "inspect_riftfield", "The orchard is healthy, but every affected root system independently avoids the same buried line."),
        GREYWAKE_RIFTFIELD_KEY: ("inspect_riftfield", "return_camp", "Riftfield confirms the line reaches the surface without an open crack. The effect continues east."),
    }
    expected, next_step, text = steps[site]
    if q["current_step"] != expected:
        return False
    session.database.advance_quest(session.character.id, AFTER_GLOAM_QUEST_KEY, next_step)
    await session.send(text + "\r\n")
    return True


async def _talk_faction(session, faction_key: str) -> bool:
    if session.character is None:
        return False
    q = _quest(session, THREE_CLAIMS_QUEST_KEY)
    if not q or q["status"] != "active":
        return False
    sequence = {
        "roadwarden_compact": (GREYWAKE_WARDEN_POST_KEY, "hear_roadwarden", "hear_ledger"),
        "deep_ledger_consortium": (GREYWAKE_LEDGER_CUT_KEY, "hear_ledger", "hear_lantern"),
        "lantern_oath": (GREYWAKE_LANTERN_HOSPICE_KEY, "hear_lantern", "pledge"),
    }
    room_key, expected, next_step = sequence[faction_key]
    if session.character.current_room != room_key or q["current_step"] != expected:
        return False
    faction = FACTIONS_BY_KEY[faction_key]
    session.database.advance_quest(session.character.id, THREE_CLAIMS_QUEST_KEY, next_step)
    await session.send(f"{faction.name}: {faction.belief} Risk: {faction.risk}\r\n")
    return True


async def _support_faction(session, faction_key: str) -> bool:
    if session.character is None or session.character.current_room != GREYWAKE_THREE_BANNER_KEY:
        return False
    q = _quest(session, THREE_CLAIMS_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "pledge":
        return False
    faction = FACTIONS_BY_KEY[faction_key]
    for flag in (ROADWARDEN_FLAG, LEDGER_FLAG, LANTERN_FLAG):
        session.database.revoke_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, faction.support_flag)
    session.database.complete_quest(session.character.id, THREE_CLAIMS_QUEST_KEY)
    session.database.start_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY, "rally")
    session.database.add_experience(session.character.id, 140)
    _refresh(session)
    await session.send(
        f"You choose to support the {faction.name} first. The other two banners remain standing beside it; this is a practical alignment, not a declaration that everyone else is evil. Three Claims on One Road complete: 140 XP.\r\n"
    )
    return True


def _begin_forced_combat(session, enemy_definition: EnemyDefinition) -> bool:
    if session.character is None or session.combatant is None or session.active_enemy is not None:
        return False
    enemy = EnemyState(enemy_definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


async def _rally_surge(session, *, strength: int = 6) -> bool:
    if session.character is None or session.character.current_room != GREYWAKE_SIGNAL_HILL_KEY:
        return False
    q = _quest(session, BELL_BELOW_WIND_QUEST_KEY)
    if not q or q["status"] != "active" or q["current_step"] != "rally":
        await session.send("The March bell is for a coordinated alarm. You do not currently have the Bell Below the Wind objective.\r\n")
        return True
    if SURGE_STATE.active:
        await session.send(f"A Greywake Surge is already active. Remaining instability: {SURGE_STATE.remaining}.\r\n")
        return True
    SURGE_STATE.start(strength)
    _SURGE_PARTICIPANTS.clear()
    session.database.advance_quest(session.character.id, BELL_BELOW_WIND_QUEST_KEY, "break_surge")
    await session.send(
        f"You ring the March alarm. The bell answers once from the tower and once from somewhere under the hill. A shared Gloam Surge begins across the Heath, Sunk Causeway, and Riftfield. Event strength: {SURGE_STATE.remaining}.\r\n"
    )
    return True


async def _surge_status(session) -> bool:
    if SURGE_STATE.active:
        await session.send(f"Greywake world event: GLOAM SURGE ACTIVE. Remaining instability: {SURGE_STATE.remaining}. Generation: {SURGE_STATE.generation}.\r\n")
    else:
        await session.send(f"Greywake world event: quiet. Last surge generation: {SURGE_STATE.generation}.\r\n")
    return True


async def _record_surge_kill(session) -> None:
    if session.character is None or not SURGE_STATE.active:
        return
    _SURGE_PARTICIPANTS.add(session.character.id)
    session.database.add_item(session.character.id, SURGE_SPLINTER_KEY, 1)
    ended = SURGE_STATE.record_kill()
    await session.send(f"The Riftling collapses inward. Greywake Surge remaining: {SURGE_STATE.remaining}.\r\n")
    if not ended:
        return
    for explorer in list(_ACTIVE_SESSIONS):
        character = getattr(explorer, "character", None)
        if character is None or character.id not in _SURGE_PARTICIPANTS:
            continue
        explorer.database.grant_flag(character.id, GREYWAKE_SURGE_VETERAN_FLAG)
        explorer.database.add_experience(character.id, 100)
        explorer.database.add_item(character.id, WAYMEET_SCRIP_KEY, 2)
        q = explorer.database.get_quest(character.id, BELL_BELOW_WIND_QUEST_KEY)
        if q and q["status"] == "active" and q["current_step"] == "break_surge":
            explorer.database.advance_quest(character.id, BELL_BELOW_WIND_QUEST_KEY, "report")
        _refresh(explorer)
        await explorer.send("The second note under the March bell stops. The shared Gloam Surge is broken. Participants gain 100 XP and 2 Waymeet Trade Scrip; report at Three-Banner Camp.\r\n")


def _maybe_start_event_enemy(session) -> bool:
    if not SURGE_STATE.active or session.character is None:
        return False
    if session.character.current_room not in SURGE_EVENT_ROOMS:
        return False
    return _begin_forced_combat(session, RIFTLING)


def install_greywake_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_greywake_runtime_installed", False):
        return
    install_greywake_content(world_service)

    previous_enter = player_session_class.enter_character
    previous_move = player_session_class.move_character
    previous_show = player_session_class.show_current_room
    previous_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        _ACTIVE_SESSIONS.add(self)
        if self.character is not None and self.character.current_room in GREYWAKE_ROOM_KEYS:
            _ensure_after_gloam(self)

    async def move_character(self, direction: str) -> None:
        await previous_move(self, direction)
        if self.character is None:
            return
        _ACTIVE_SESSIONS.add(self)
        if self.character.current_room in GREYWAKE_ROOM_KEYS:
            _ensure_after_gloam(self)
            if _maybe_start_event_enemy(self):
                await self.send("The active surge pulls loose stone and grass into a Greywake Riftling directly in your path. Combat begins.\r\n")

    async def show_current_room(self) -> None:
        await previous_show(self)
        if self.character is not None and SURGE_STATE.active and self.character.current_room in SURGE_EVENT_ROOMS:
            await self.send(f"\r\nWORLD EVENT — Gloam Surge: the ground gives off the tower bell's buried second note. Instability remaining: {SURGE_STATE.remaining}.\r\n")

    def enemy_in_room(self, target_text: str):
        if self.character is not None and SURGE_STATE.active and self.character.current_room in SURGE_EVENT_ROOMS and RIFTLING.matches(target_text):
            return EnemyState(RIFTLING)
        return previous_enemy_lookup(self, target_text)

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
        room = self.character.current_room or ""
        handled = False

        if normalized in {"talk captain", "talk oryn", "speak captain"}:
            handled = await _talk_captain(self)
        elif normalized in {"talk factor", "talk merrit", "speak factor"}:
            handled = await _talk_faction(self, "deep_ledger_consortium")
        elif normalized in {"talk keeper", "talk ela", "speak keeper"}:
            handled = await _talk_faction(self, "lantern_oath")
        elif normalized in {"talk roadwarden", "talk roadwarden captain"} and room == GREYWAKE_WARDEN_POST_KEY:
            handled = await _talk_faction(self, "roadwarden_compact")
        elif room == GREYWAKE_WARDEN_POST_KEY and normalized in {"talk captain", "talk oryn"}:
            handled = await _talk_faction(self, "roadwarden_compact")
        elif room == GREYWAKE_HEATH_KEY and normalized in {"examine grey crust", "examine crust", "look crust"}:
            handled = await _inspect_site(self, GREYWAKE_HEATH_KEY)
        elif room == GREYWAKE_RESONANT_ORCHARD_KEY and normalized in {"examine trees", "look trees", "examine roots"}:
            handled = await _inspect_site(self, GREYWAKE_RESONANT_ORCHARD_KEY)
        elif room == GREYWAKE_RIFTFIELD_KEY and normalized in {"examine seam", "look seam", "examine rift"}:
            handled = await _inspect_site(self, GREYWAKE_RIFTFIELD_KEY)
        elif normalized in {"support roadwarden", "support roadwardens", "pledge roadwarden"}:
            handled = await _support_faction(self, "roadwarden_compact")
        elif normalized in {"support ledger", "support deep ledger", "pledge ledger"}:
            handled = await _support_faction(self, "deep_ledger_consortium")
        elif normalized in {"support lantern", "support lantern oath", "pledge lantern"}:
            handled = await _support_faction(self, "lantern_oath")
        elif normalized in {"rally surge", "ring march bell", "ring signal bell"}:
            handled = await _rally_surge(self)
            if handled and SURGE_STATE.active:
                _maybe_start_event_enemy(self)
        elif normalized in {"surge status", "march event", "event status"}:
            handled = await _surge_status(self)
        elif normalized in {"factions", "greywake factions"}:
            await self.send("Greywake factions:\r\n" + "\r\n".join(f" - {f.name}: {f.belief} Risk: {f.risk}" for f in FACTIONS) + "\r\n")
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
        key = enemy.definition.key
        was_active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if was_active and key == RIFTLING_KEY:
            await _record_surge_kill(self)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = enemy_in_room
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class._greywake_runtime_installed = True
