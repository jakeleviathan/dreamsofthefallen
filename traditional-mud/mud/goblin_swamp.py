from __future__ import annotations

from dataclasses import dataclass, replace

import mud.combat as combat
import mud.crafting as crafting
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.combat import EnemyDefinition
from mud.crafting import ResourceNodeDefinition, craft_recipe, trade_skill_value
from mud.goblin_outer_route import (
    GOBLIN_FIRST_PILING_KEY,
    GOBLIN_OUTER_ROUTE_COMPLETE_FLAG,
    install_goblin_outer_route_content,
)
from mud.goblin_start import GOBLIN_REGION_KEY
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import NpcDefinition, RoomDefinition


GOBLIN_REEDFEN_CAUSEWAY_KEY = "goblin_reedfen_causeway"
GOBLIN_BITTERWATER_RUN_KEY = "goblin_bitterwater_run"
GOBLIN_LANTERNMOSS_CUT_KEY = "goblin_lanternmoss_cut"
GOBLIN_MUDGLASS_CROSSING_KEY = "goblin_mudglass_crossing"
GOBLIN_CLEANWATER_SEEP_KEY = "goblin_cleanwater_seep"
GOBLIN_ROOTSNAG_BANK_KEY = "goblin_rootsnag_bank"
GOBLIN_APOTHECARY_BLIND_KEY = "goblin_apothecary_blind"

GOBLIN_SWAMP_ROOM_KEYS: tuple[str, ...] = (
    GOBLIN_REEDFEN_CAUSEWAY_KEY,
    GOBLIN_BITTERWATER_RUN_KEY,
    GOBLIN_LANTERNMOSS_CUT_KEY,
    GOBLIN_MUDGLASS_CROSSING_KEY,
    GOBLIN_CLEANWATER_SEEP_KEY,
    GOBLIN_ROOTSNAG_BANK_KEY,
    GOBLIN_APOTHECARY_BLIND_KEY,
)
GOBLIN_SWAMP_ENTERED_FLAG = "goblin_newbie_swamp_entered"


MIRE_TICK_SWARM = EnemyDefinition(
    key="mire_tick_swarm",
    name="Mire Tick Swarm",
    aliases=("ticks", "tick swarm", "mire ticks", "mire tick swarm"),
    description=(
        "a fist-sized knot of glossy marsh ticks crawling over one another with far more confidence than their size deserves"
    ),
    max_hp=14,
    armor_class=2,
    auto_attack_damage=1,
    auto_attack_interval=4.0,
    xp_reward=15,
    retaliates=True,
    tutorial=False,
)

BOG_SNAPPER = EnemyDefinition(
    key="bog_snapper",
    name="Bog Snapper",
    aliases=("snapper", "bog snapper", "swamp snapper"),
    description=(
        "a squat amphibious scavenger with mud-brown hide, a shovel-shaped head, and a mouth built for convincing careless gatherers to use longer tools"
    ),
    max_hp=22,
    armor_class=4,
    auto_attack_damage=2,
    auto_attack_interval=3.8,
    xp_reward=30,
    retaliates=True,
    tutorial=False,
)


GOBLIN_SWAMP_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=GOBLIN_REEDFEN_CAUSEWAY_KEY,
        name="Reedfen Causeway",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A low causeway of split logs and salvaged metal grating runs north through shoulder-high reeds. Colored bottle shards tied to wire mark the stable footing, flashing whenever daylight reaches them. Small herb baskets have been hooked beneath the rail where Goblin gatherers can keep muddy roots away from cleaner leaves. The First Piling is south. A narrow boardwalk branches east toward clearer water, while the main route continues north."
        ),
        exits={
            "south": GOBLIN_FIRST_PILING_KEY,
            "north": GOBLIN_MUDGLASS_CROSSING_KEY,
            "east": GOBLIN_CLEANWATER_SEEP_KEY,
        },
        tags=("goblin_newbie_swamp", "beginner_wilderness", "herbalism", "causeway"),
    ),
    RoomDefinition(
        key=GOBLIN_BITTERWATER_RUN_KEY,
        name="Bitterwater Run",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Dark water squeezes between two raised banks tangled with roots. Flat stepping plates, each painted with a different merchant-family mark, keep the route mostly above the muck. Goblin herb-cutters have tied pale cord around several places where medicinal roots grow thickest. The First Piling lies west; a rougher bank continues north."
        ),
        exits={"west": GOBLIN_FIRST_PILING_KEY, "north": GOBLIN_ROOTSNAG_BANK_KEY},
        tags=("goblin_newbie_swamp", "beginner_wilderness", "herbalism", "roots"),
    ),
    RoomDefinition(
        key=GOBLIN_LANTERNMOSS_CUT_KEY,
        name="Lanternmoss Cut",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A narrow route has been cut between mossy hummocks and braced with discarded signposts. Pale fungi glow beneath the shadowed sides of the path even during the day, while useful green herbs crowd the drier crowns of the hummocks. Tiny copper tags identify plants worth taking and plants worth leaving alone. The First Piling lies east; a screened field shelter stands north."
        ),
        exits={"east": GOBLIN_FIRST_PILING_KEY, "north": GOBLIN_APOTHECARY_BLIND_KEY},
        tags=("goblin_newbie_swamp", "beginner_wilderness", "herbalism", "fungal"),
    ),
    RoomDefinition(
        key=GOBLIN_MUDGLASS_CROSSING_KEY,
        name="Mudglass Crossing",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "Three beginner routes meet on a broad platform floored with thick panes of salvaged glass laid over timber. Muddy water moves visibly beneath your boots. Northward the maintained markings stop at a crooked warning frame draped with black-and-yellow scraps; beyond it, the reeds close over routes meant for more experienced crews. Reedfen Causeway is south, Rootsnag Bank east, and the apothecary shelter west."
        ),
        exits={
            "south": GOBLIN_REEDFEN_CAUSEWAY_KEY,
            "east": GOBLIN_ROOTSNAG_BANK_KEY,
            "west": GOBLIN_APOTHECARY_BLIND_KEY,
        },
        enemy_keys=(MIRE_TICK_SWARM.key,),
        tags=("goblin_newbie_swamp", "beginner_wilderness", "crossroads", "danger_boundary"),
    ),
    RoomDefinition(
        key=GOBLIN_CLEANWATER_SEEP_KEY,
        name="Cleanwater Seep",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A limestone hump rises above the swamp just enough for clear water to bead from a crack and collect in a stone-lined basin. Goblins have protected the seep with a mesh hood, a little settling trough, and a sign that reads CLEAN ENOUGH FOR POTIONS in three handwriting styles. The only boardwalk returns west to Reedfen Causeway."
        ),
        exits={"west": GOBLIN_REEDFEN_CAUSEWAY_KEY},
        tags=("goblin_newbie_swamp", "beginner_wilderness", "alchemy_resource", "water_source"),
    ),
    RoomDefinition(
        key=GOBLIN_ROOTSNAG_BANK_KEY,
        name="Rootsnag Bank",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A high root mass forms a dry shelf above a sluggish brown channel. Medicinal roots grow between the exposed knots, and old cut marks show where gatherers learned to take only the outer growth instead of killing the whole plant. A few snapped tool handles in the mud suggest that the local wildlife occasionally objects. Bitterwater Run lies south and Mudglass Crossing west."
        ),
        exits={"south": GOBLIN_BITTERWATER_RUN_KEY, "west": GOBLIN_MUDGLASS_CROSSING_KEY},
        enemy_keys=(BOG_SNAPPER.key,),
        tags=("goblin_newbie_swamp", "beginner_wilderness", "herbalism", "light_danger"),
    ),
    RoomDefinition(
        key=GOBLIN_APOTHECARY_BLIND_KEY,
        name="The Apothecary Blind",
        region_key=GOBLIN_REGION_KEY,
        description=(
            "A low field shelter of woven reed panels and mismatched window glass hides among the hummocks. Bundles of herbs hang from labeled wire, stoppered jars occupy fitted scrapwood shelves, and a scarred bench supports mortars, scales, burners, and a compact copper still. This is not a secret laboratory; it is public route infrastructure. Goblin gatherers stop here to identify, dry, grind, steep, and trade notes before carrying ingredients back to Junk City. Lanternmoss Cut is south and Mudglass Crossing east."
        ),
        exits={"south": GOBLIN_LANTERNMOSS_CUT_KEY, "east": GOBLIN_MUDGLASS_CROSSING_KEY},
        npc_keys=("goblin_pella_mireglass",),
        tags=(
            "goblin_newbie_swamp",
            "beginner_wilderness",
            "alchemy_station",
            "mortar_and_pestle",
            "alchemy_table",
            "field_shelter",
        ),
    ),
)


PELLA_MIREGLASS = NpcDefinition(
    key="goblin_pella_mireglass",
    name="Pella Mireglass",
    short_description="a field apothecary labeling damp herb bundles with a grease pencil",
    room_key=GOBLIN_APOTHECARY_BLIND_KEY,
    role="Goblin starter alchemist and swamp fieldcraft guide",
    dialogue=(
        "Pella pinches a Greenleaf stem and turns it so you can see the pale underside. 'Alchemy starts before the bottle. Pick the wrong part, cut too deep, carry it wet, and the clever work at the bench cannot save you.'",
        "She nods toward the swamp. 'Greenleaf is forgiving. Bitterroot teaches patience. Clean water is worth protecting. Learn those three and you can make things that keep a crew moving.'",
        "Pella taps the battered mortar on her bench. 'Other people call alchemy mysterious because they buy it finished. We call it another kind of repair.'",
    ),
)


@dataclass(frozen=True, slots=True)
class SwampGatherNodeDefinition:
    key: str
    room_key: str
    name: str
    aliases: tuple[str, ...]
    resource: ResourceNodeDefinition | None
    output_item_key: str
    maximum_uses: int = 3
    respawn_world_hours: int = 1

    def matches(self, target: str) -> bool:
        normalized = target.strip().lower()
        names = {self.name.lower(), self.key.replace("_", " "), *(alias.lower() for alias in self.aliases)}
        return normalized in names


@dataclass(slots=True)
class SwampGatherNodeState:
    definition: SwampGatherNodeDefinition
    remaining_uses: int
    depleted_at_hour: int | None = None

    def refresh(self, total_hour: int) -> None:
        if self.remaining_uses > 0 or self.depleted_at_hour is None:
            return
        if total_hour - self.depleted_at_hour >= self.definition.respawn_world_hours:
            self.remaining_uses = self.definition.maximum_uses
            self.depleted_at_hour = None


REEDFEN_GREENLEAF = SwampGatherNodeDefinition(
    key="reedfen_greenleaf",
    room_key=GOBLIN_REEDFEN_CAUSEWAY_KEY,
    name="Reedfen Greenleaf",
    aliases=("greenleaf", "greenleaf patch", "herbs", "green herbs"),
    resource=ResourceNodeDefinition(
        key="reedfen_greenleaf",
        name="Reedfen Greenleaf",
        gathering_skill_key="herbalism",
        output_item_key="greenleaf",
        minimum_skill=0,
        design_status="goblin_beginner_alchemy_resource",
        tier=1,
        region_hint="Junk City's maintained beginner swamp routes.",
    ),
    output_item_key="greenleaf",
)

LANTERNMOSS_GREENLEAF = SwampGatherNodeDefinition(
    key="lanternmoss_greenleaf",
    room_key=GOBLIN_LANTERNMOSS_CUT_KEY,
    name="Hummock Greenleaf",
    aliases=("greenleaf", "greenleaf patch", "herbs", "hummock herbs"),
    resource=ResourceNodeDefinition(
        key="lanternmoss_greenleaf",
        name="Hummock Greenleaf",
        gathering_skill_key="herbalism",
        output_item_key="greenleaf",
        minimum_skill=0,
        design_status="goblin_beginner_alchemy_resource",
        tier=1,
        region_hint="Dry hummocks along Junk City's maintained swamp routes.",
    ),
    output_item_key="greenleaf",
)

BITTERWATER_BITTERROOT = SwampGatherNodeDefinition(
    key="bitterwater_bitterroot",
    room_key=GOBLIN_BITTERWATER_RUN_KEY,
    name="Bitterwater Bitterroot",
    aliases=("bitterroot", "bitterroot cluster", "roots", "medicinal roots"),
    resource=ResourceNodeDefinition(
        key="bitterwater_bitterroot",
        name="Bitterwater Bitterroot",
        gathering_skill_key="herbalism",
        output_item_key="bitterroot",
        minimum_skill=5,
        design_status="goblin_beginner_alchemy_resource",
        tier=1,
        region_hint="Damp banks along Junk City's beginner swamp routes.",
    ),
    output_item_key="bitterroot",
)

ROOTSNAG_BITTERROOT = SwampGatherNodeDefinition(
    key="rootsnag_bitterroot",
    room_key=GOBLIN_ROOTSNAG_BANK_KEY,
    name="Rootsnag Bitterroot",
    aliases=("bitterroot", "bitterroot cluster", "roots", "medicinal roots"),
    resource=ResourceNodeDefinition(
        key="rootsnag_bitterroot",
        name="Rootsnag Bitterroot",
        gathering_skill_key="herbalism",
        output_item_key="bitterroot",
        minimum_skill=5,
        design_status="goblin_beginner_alchemy_resource",
        tier=1,
        region_hint="Exposed root shelves along Junk City's beginner swamp routes.",
    ),
    output_item_key="bitterroot",
)

CLEANWATER_SOURCE = SwampGatherNodeDefinition(
    key="cleanwater_seep",
    room_key=GOBLIN_CLEANWATER_SEEP_KEY,
    name="Cleanwater Seep",
    aliases=("water", "clean water", "seep", "basin", "spring water"),
    resource=None,
    output_item_key="spring_water",
    maximum_uses=4,
)

GOBLIN_SWAMP_GATHER_NODES: tuple[SwampGatherNodeDefinition, ...] = (
    REEDFEN_GREENLEAF,
    LANTERNMOSS_GREENLEAF,
    BITTERWATER_BITTERROOT,
    ROOTSNAG_BITTERROOT,
    CLEANWATER_SOURCE,
)


class GoblinSwampGatheringService:
    """Shared beginner resource state for the maintained Junk City swamp routes.

    Nodes are intentionally generous and refill after one Astralis hour. The
    state is shared across players like a normal MUD resource node, while the
    short refill prevents a busy starter zone from remaining stripped bare.
    """

    def __init__(self) -> None:
        self.states: dict[str, SwampGatherNodeState] = {}
        self.reset()

    def reset(self) -> None:
        self.states = {
            node.key: SwampGatherNodeState(node, node.maximum_uses)
            for node in GOBLIN_SWAMP_GATHER_NODES
        }

    def nodes_in_room(self, room_key: str) -> tuple[SwampGatherNodeState, ...]:
        total_hour = ASTRALIS_CLOCK.now().total_hours
        result: list[SwampGatherNodeState] = []
        for state in self.states.values():
            if state.definition.room_key != room_key:
                continue
            state.refresh(total_hour)
            result.append(state)
        return tuple(result)

    def resolve(self, room_key: str, target: str) -> SwampGatherNodeState | None:
        for state in self.nodes_in_room(room_key):
            if state.definition.matches(target):
                return state
        return None

    def gather(self, database, character_id: int, state: SwampGatherNodeState) -> tuple[bool, str]:
        total_hour = ASTRALIS_CLOCK.now().total_hours
        state.refresh(total_hour)
        if state.remaining_uses <= 0:
            return False, f"The {state.definition.name} has been picked clean for now. The maintained route should recover within about one Astralis hour."

        resource = state.definition.resource
        if resource is not None:
            skill = trade_skill_value(database, character_id, resource.gathering_skill_key)
            if skill < resource.minimum_skill:
                return False, (
                    f"You recognize the {state.definition.name}, but harvesting it cleanly requires "
                    f"{resource.gathering_skill_key} skill {resource.minimum_skill}; yours is {skill}."
                )
            database.add_item(character_id, state.definition.output_item_key, 1)
            database.record_trade_skill_use(character_id, resource.gathering_skill_key, 1)
        else:
            database.add_item(character_id, state.definition.output_item_key, 1)

        state.remaining_uses -= 1
        if state.remaining_uses <= 0:
            state.depleted_at_hour = total_hour
        return True, state.definition.output_item_key


GOBLIN_SWAMP_GATHERING = GoblinSwampGatheringService()


def _feature(
    key: str,
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    summary: str,
    examine: str,
    search: str = "",
    touch: str = "",
    listen: str = "",
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
    )


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _swamp_access_exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(
        direction=direction,
        destination_key=destination,
        name=name,
        travel_text=travel,
        condition=ViewCondition(required_flags=(GOBLIN_OUTER_ROUTE_COMPLETE_FLAG,)),
        hidden_when_unavailable=True,
        failure_text="Finish Ruskle Coil's first route lesson before taking the maintained swamp branches beyond the First Piling.",
    )


def _day(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_swamp_day", text, priority=40, condition=ViewCondition(time_buckets=("day",)))


def _night(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_swamp_night", text, priority=50, condition=ViewCondition(time_buckets=("night",)))


def _rain(text: str) -> DescriptionLayer:
    return DescriptionLayer("goblin_swamp_rain", text, priority=60, condition=ViewCondition(weather=("rain", "storm")))


def goblin_swamp_augmentations() -> dict[str, RoomAugmentation]:
    return {
        GOBLIN_REEDFEN_CAUSEWAY_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_FIRST_PILING_KEY, "The First Piling", "You follow the bottle-marked causeway south toward the first numbered piling."),
                _exit("north", GOBLIN_MUDGLASS_CROSSING_KEY, "Mudglass Crossing", "You follow the main maintained route north until the reeds open around a glass-floored platform."),
                _exit("east", GOBLIN_CLEANWATER_SEEP_KEY, "Cleanwater Seep", "You take the narrow east boardwalk toward the protected seep."),
            ),
            features=(
                _feature(
                    "reedfen_greenleaf_feature", "Reedfen Greenleaf", aliases=("greenleaf", "herbs", "greenleaf patch"),
                    summary="low medicinal leaves growing on the drier edge of the causeway",
                    examine="Copper plant tags show where beginners should cut above the pale second joint, leaving the root and youngest leaves intact.",
                    search="The healthiest usable leaves grow between two bottle-marked rail posts. GATHER GREENLEAF to harvest them.",
                    touch="The leaves are cool, slightly waxy, and carry a clean medicinal scent when bruised.",
                ),
                _feature(
                    "bottle_route_marks", "Bottle Route Marks", aliases=("bottles", "route marks", "glass markers"),
                    summary="colored bottle glass wired along the safest footing",
                    examine="The colors are functional: bright pieces mark stable boards, dark pieces mark repairs due soon, and doubled wire marks a route safe enough for new gatherers.",
                ),
            ),
            description_layers=(
                _day("Sunlight catches hundreds of bottle markers and turns the beginner route into a line of green, amber, and blue flashes through the reeds."),
                _night("Small hooded lamps replace the bottle flashes at night, each fixed low enough to illuminate footing without advertising the route across the whole swamp."),
                _rain("Rain rattles against the metal grating and weighs the reeds down over the rails, but the maintained causeway remains easy to follow."),
            ),
        ),
        GOBLIN_BITTERWATER_RUN_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", GOBLIN_FIRST_PILING_KEY, "The First Piling", "You follow the stepping plates west toward the First Piling."),
                _exit("north", GOBLIN_ROOTSNAG_BANK_KEY, "Rootsnag Bank", "You pick your way north where exposed roots lift the bank higher above the water."),
            ),
            features=(
                _feature(
                    "bitterwater_bitterroot_feature", "Bitterwater Bitterroot", aliases=("bitterroot", "roots", "medicinal roots"),
                    summary="pale medicinal roots tagged along the damp bank",
                    examine="The tagged plants are mature enough to trim, but the outer roots must be cut without damaging the darker central crown.",
                    search="Several usable outer roots are visible above the damp soil. GATHER BITTERROOT once your Herbalism is practiced enough.",
                    touch="The exposed root skin is fibrous and leaves a sharp bitter smell on your fingers.",
                ),
            ),
            description_layers=(
                _day("Dragonflies patrol the narrow channel while herb-cutters work by sight, comparing roots against stained field cards."),
                _night("Reflective paint on the stepping plates makes the safe line visible by lantern light, though the root tangles beyond it vanish into shadow."),
                _rain("The water rises against the lower stepping plates and carries a bitter green smell from freshly disturbed roots."),
            ),
        ),
        GOBLIN_LANTERNMOSS_CUT_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", GOBLIN_FIRST_PILING_KEY, "The First Piling", "You follow the cut east toward the open platform of the First Piling."),
                _exit("north", GOBLIN_APOTHECARY_BLIND_KEY, "The Apothecary Blind", "You follow a line of copper plant tags north to the screened field shelter."),
            ),
            features=(
                _feature(
                    "lanternmoss_greenleaf_feature", "Hummock Greenleaf", aliases=("greenleaf", "herbs", "greenleaf patch"),
                    summary="a second beginner patch of Greenleaf on a dry mossy crown",
                    examine="These plants are smaller than the Reedfen patch but healthy. Their copper tags repeat the same beginner cut marks used across the maintained route.",
                    search="Usable leaves crowd the sunny side of the hummock. GATHER GREENLEAF to take a careful cutting.",
                ),
                _feature(
                    "lanternmoss", "Lanternmoss", aliases=("moss", "glowing moss", "fungi"),
                    summary="pale fungal growth lighting the shaded sides of the path",
                    examine="The glow is beautiful but the nearby tags carry a crossed-vial symbol. Whatever its chemistry, beginners are being told not to put it in anything yet.",
                ),
            ),
            description_layers=(
                _day("Even in full daylight the Lanternmoss keeps a ghostly glow beneath the hummocks, while tagged herbs on top drink in the sun."),
                _night("After dark the path almost marks itself: pale fungal light outlines the hummocks while copper tags wink in the glow."),
                _rain("Water beads on the Lanternmoss until each pale patch shines through a skin of rain."),
            ),
        ),
        GOBLIN_MUDGLASS_CROSSING_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_REEDFEN_CAUSEWAY_KEY, "Reedfen Causeway", "You leave the glass platform south along the bottle-marked causeway."),
                _exit("east", GOBLIN_ROOTSNAG_BANK_KEY, "Rootsnag Bank", "You follow the east rail toward a high shelf of exposed roots."),
                _exit("west", GOBLIN_APOTHECARY_BLIND_KEY, "The Apothecary Blind", "You follow a west spur toward the screened apothecary shelter."),
            ),
            features=(
                _feature(
                    "deep_mire_warning", "Deep Mire Warning Frame", aliases=("warning", "frame", "deep mire", "black yellow scraps"),
                    summary="a deliberately ugly boundary marker where beginner maintenance ends",
                    examine="The frame carries tally marks, broken tool heads, and a clear painted warning: NEW CREWS TURN AROUND HERE. No maintained exit continues north yet.",
                    listen="Beyond the warning frame the swamp sounds larger: frogs, insects, distant splashes, and something heavy moving where the maintained boards do not go.",
                ),
                _feature(
                    "mudglass_floor", "Mudglass Floor", aliases=("glass", "floor", "glass floor"),
                    summary="thick salvaged panes laid over the dark water",
                    examine="None of the panes match, but each rests on a redundant timber frame. Looking down shows mud, bubbles, roots, and the occasional tiny creature moving beneath your boots.",
                ),
            ),
            description_layers=(
                _day("The crossing is bright enough to see the muddy water moving beneath every glass panel—and to see exactly where the maintained routes stop."),
                _night("Lanterns mounted below the glass make the platform glow from underneath, illuminating ripples and small moving shadows in the water."),
                _rain("Rain makes the glass dangerously glossy, and yellow grit has been scattered across the main walking lines for traction."),
            ),
        ),
        GOBLIN_CLEANWATER_SEEP_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", GOBLIN_REEDFEN_CAUSEWAY_KEY, "Reedfen Causeway", "You follow the narrow boardwalk west back to the causeway."),
            ),
            features=(
                _feature(
                    "cleanwater_seep_feature", "Cleanwater Seep", aliases=("water", "clean water", "seep", "basin", "spring water"),
                    summary="a protected trickle of clean mineral water reserved for cooking and alchemy",
                    examine="The mesh hood keeps leaves and insects out while a gravel settling trough feeds the stone basin. A painted fill line prevents gatherers from draining it faster than it refills.",
                    search="The water is clear and cool. COLLECT WATER to fill a small alchemical measure.",
                    touch="The seep water is noticeably cooler than the swamp around it.",
                    listen="A steady drip passes through the settling stones, quiet but constant.",
                ),
            ),
            description_layers=(
                _day("The little basin shines almost unnaturally clear against the black mud surrounding the limestone hump."),
                _night("A single blue bottle lamp marks the clean-water station, its color reserved on these routes for drinkable or potion-safe water."),
                _rain("Rainwater runs off the mesh hood rather than into the basin, keeping the protected seep from becoming ordinary swamp runoff."),
            ),
        ),
        GOBLIN_ROOTSNAG_BANK_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_BITTERWATER_RUN_KEY, "Bitterwater Run", "You follow the high bank south toward the painted stepping plates."),
                _exit("west", GOBLIN_MUDGLASS_CROSSING_KEY, "Mudglass Crossing", "You follow the reinforced root shelf west toward the glass-floored crossing."),
            ),
            features=(
                _feature(
                    "rootsnag_bitterroot_feature", "Rootsnag Bitterroot", aliases=("bitterroot", "roots", "medicinal roots"),
                    summary="mature Bitterroot growing between exposed tree roots",
                    examine="Old harvest cuts have healed into thick scars, proof that careful gatherers have been taking outer roots here for years without killing the crowns.",
                    search="Several outer roots are ready for a clean cut. GATHER BITTERROOT to harvest one if your Herbalism is high enough.",
                ),
                _feature(
                    "broken_gathering_tools", "Broken Gathering Tools", aliases=("tools", "broken tools", "handles"),
                    summary="a few snapped handles and bent digging forks left in the mud",
                    examine="Most are ordinary accidents. One handle has a neat semicircle of tooth marks around the break, which explains why experienced gatherers keep one eye on the channel.",
                ),
            ),
            description_layers=(
                _day("The raised bank is dry enough for careful herb work, but every gatherer periodically checks the brown channel before bending down again."),
                _night("The route lamps leave the channel itself dark, making every small splash sound closer than it probably is."),
                _rain("Fresh runoff exposes more pale root tips while turning the lower bank into slick clay."),
            ),
        ),
        GOBLIN_APOTHECARY_BLIND_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", GOBLIN_LANTERNMOSS_CUT_KEY, "Lanternmoss Cut", "You push through the reed screen and follow the tagged path south."),
                _exit("east", GOBLIN_MUDGLASS_CROSSING_KEY, "Mudglass Crossing", "You leave the field shelter by the east boardwalk toward the glass crossing."),
            ),
            features=(
                _feature(
                    "field_alchemy_bench", "Field Alchemy Bench", aliases=("bench", "alchemy bench", "mortar", "mortar and pestle", "still", "alchemy table"),
                    summary="a public Goblin workbench equipped for beginner potion-making and small-batch distillation",
                    examine="Mortars, pestles, drying screens, a balance, burners, labeled spoons, and a compact copper still all have their own fitted places. Repairs are obvious and numerous, but every measuring mark has been kept precise.",
                    search="A chalk strip lists the first two route recipes: Minor Healing Potion and Lesser Antidote. Type ALCHEMY for details or BREW <recipe> to work here.",
                    touch="The bench is scarred by years of grinding bowls and hot glassware, but the measuring surfaces have been sanded flat.",
                ),
                _feature(
                    "ingredient_rack", "Ingredient Rack", aliases=("rack", "herbs", "jars", "ingredients"),
                    summary="labeled examples of common swamp ingredients used for identification",
                    examine="Reference bundles of Greenleaf and Bitterroot hang beside color cards, cut diagrams, and notes on drying time. They are teaching samples, not free ingredients.",
                ),
            ),
            description_layers=(
                _day("Pella keeps the blind open to the daylight while gatherers compare fresh cuttings against the reference rack and grind small test batches."),
                _night("At night the reed screens close around the bench and a shielded burner gives the whole shelter a warm copper glow."),
                _rain("Rain chatters on the patched roof while damp herb bundles are spread farther apart on the drying wires."),
            ),
        ),
    }


def _first_piling_swamp_exits() -> tuple[ExitDefinition, ...]:
    return (
        _swamp_access_exit(
            "north",
            GOBLIN_REEDFEN_CAUSEWAY_KEY,
            "Reedfen Causeway",
            "You leave the First Piling north along a bottle-marked beginner causeway through the reeds.",
        ),
        _swamp_access_exit(
            "east",
            GOBLIN_BITTERWATER_RUN_KEY,
            "Bitterwater Run",
            "You take the east stepping route where pale cord marks the medicinal root banks.",
        ),
        _swamp_access_exit(
            "west",
            GOBLIN_LANTERNMOSS_CUT_KEY,
            "Lanternmoss Cut",
            "You follow the west cut between mossy hummocks and copper-tagged herbs.",
        ),
    )


def _patch_first_piling(room: RoomDefinition) -> RoomDefinition:
    exits = dict(room.exits)
    exits.update(
        {
            "north": GOBLIN_REEDFEN_CAUSEWAY_KEY,
            "east": GOBLIN_BITTERWATER_RUN_KEY,
            "west": GOBLIN_LANTERNMOSS_CUT_KEY,
        }
    )
    return replace(room, exits=exits)


def _merge_world_augmentations(world_service) -> None:
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return

    first_piling = augmentations.get(GOBLIN_FIRST_PILING_KEY, RoomAugmentation())
    directions = {"north", "east", "west"}
    extra_exits = tuple(exit_def for exit_def in first_piling.extra_exits if exit_def.direction not in directions)
    extra_exits += _first_piling_swamp_exits()
    access_layer = DescriptionLayer(
        key="goblin_swamp_routes_open",
        text=(
            "With Ruskle's first route lesson behind you, three maintained beginner routes are now yours to use: Reedfen north, Bitterwater east, and Lanternmoss west. Copper herb tags and bottle markers make it obvious that these paths exist as much for alchemists as for salvage crews."
        ),
        priority=75,
        condition=ViewCondition(required_flags=(GOBLIN_OUTER_ROUTE_COMPLETE_FLAG,)),
    )
    layers = first_piling.description_layers
    if not any(layer.key == access_layer.key for layer in layers):
        layers = layers + (access_layer,)
    augmentations[GOBLIN_FIRST_PILING_KEY] = replace(
        first_piling,
        extra_exits=extra_exits,
        description_layers=layers,
    )
    augmentations.update(goblin_swamp_augmentations())

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(GOBLIN_FIRST_PILING_KEY, None)
        for room_key in GOBLIN_SWAMP_ROOM_KEYS:
            cache.pop(room_key, None)


def install_goblin_swamp_content(world_service=None) -> None:
    """Register the branching beginner swamp and its visible Goblin alchemy culture."""
    install_goblin_outer_route_content(world_service)

    first_piling = legacy_world.ROOMS_BY_KEY.get(GOBLIN_FIRST_PILING_KEY)
    replacements: dict[str, RoomDefinition] = {}
    if first_piling is not None:
        replacements[GOBLIN_FIRST_PILING_KEY] = _patch_first_piling(first_piling)

    known_rooms = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in GOBLIN_SWAMP_ROOMS if room.key not in known_rooms)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    replacements.update({room.key: room for room in GOBLIN_SWAMP_ROOMS})
    legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY.update(replacements)

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    if PELLA_MIREGLASS.key not in known_npcs:
        legacy_world.NPCS = legacy_world.NPCS + (PELLA_MIREGLASS,)
    legacy_world.NPCS_BY_KEY[PELLA_MIREGLASS.key] = PELLA_MIREGLASS

    for enemy in (MIRE_TICK_SWARM, BOG_SNAPPER):
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        _merge_world_augmentations(world_service)


def _command_target(command: str) -> str:
    parts = command.strip().split(maxsplit=1)
    return parts[1].strip().lower() if len(parts) == 2 else ""


def _room_is_swamp(room_key: str | None) -> bool:
    return bool(room_key and (room_key in GOBLIN_SWAMP_ROOM_KEYS or room_key == GOBLIN_FIRST_PILING_KEY))


async def _handle_swamp_gathering(session, normalized: str) -> bool:
    if session.character is None or session.character.current_room not in GOBLIN_SWAMP_ROOM_KEYS:
        return False

    first = normalized.split(maxsplit=1)[0] if normalized else ""
    if first not in {"gather", "harvest", "herbalism", "pick", "collect", "fill"}:
        return False

    room_key = session.character.current_room
    target = _command_target(normalized)
    local_nodes = GOBLIN_SWAMP_GATHERING.nodes_in_room(room_key)

    if not target:
        if first in {"herbalism", "gather", "harvest"}:
            herb_skill = trade_skill_value(session.database, session.character.id, "herbalism")
            await session.send(f"\r\nHerbalism skill: {herb_skill}.\r\n")
            if local_nodes:
                await session.send("Gatherable here: " + ", ".join(state.definition.name for state in local_nodes) + ".\r\n")
            else:
                await session.send("There are no maintained beginner gathering nodes in this room.\r\n")
            return True
        return False

    state = GOBLIN_SWAMP_GATHERING.resolve(room_key, target)
    if state is None:
        # Only claim the command if this is clearly a gathering attempt inside
        # the authored beginner swamp. Other command layers remain untouched.
        if first in {"gather", "harvest", "herbalism", "pick", "collect", "fill"}:
            await session.send("\r\nYou do not recognize that as one of the maintained gathering sources here.\r\n")
            return True
        return False

    success, result = GOBLIN_SWAMP_GATHERING.gather(session.database, session.character.id, state)
    if not success:
        await session.send("\r\n" + result + "\r\n")
        return True

    item = crafting.ITEMS_BY_KEY.get(result)
    item_name = item.name if item else result
    if state.definition.resource is None:
        await session.send(
            f"\r\nYou collect one clean alchemical measure of {item_name} from the protected seep.\r\n"
        )
    else:
        new_skill = trade_skill_value(session.database, session.character.id, state.definition.resource.gathering_skill_key)
        await session.send(
            f"\r\nYou harvest 1x {item_name} without damaging the maintained patch. "
            f"{state.definition.resource.gathering_skill_key.title()} improves through use (skill {new_skill}).\r\n"
        )
    return True


def _resolve_alchemy_recipe(target: str):
    normalized = target.strip().lower().replace("_", " ")
    for prefix in ("brew ", "craft ", "make ", "prepare ", "distill ", "blend "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break

    for recipe in crafting.ALCHEMY_RECIPES:
        output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
        aliases = {
            recipe.key.lower().replace("_", " "),
            recipe.key.lower(),
            recipe.output_item_key.lower().replace("_", " "),
        }
        if output is not None:
            aliases.add(output.name.lower())
        for action in ("brew", "prepare", "distill", "blend"):
            key_text = recipe.key.lower().replace("_", " ")
            if key_text.startswith(action + " "):
                aliases.add(key_text[len(action) + 1 :])
        if normalized in aliases:
            return recipe
    return None


async def _show_goblin_alchemy(session) -> None:
    assert session.character is not None
    skill = trade_skill_value(session.database, session.character.id, "alchemy")
    await session.send(
        "\r\n--- Goblin Field Alchemy ---\r\n"
        "Junk City treats alchemy as practical route craft: identify well, harvest cleanly, measure precisely, and make useful things from what the swamp provides.\r\n"
        f"Your Alchemy skill: {skill}.\r\n"
    )
    if session.character.current_room == GOBLIN_APOTHECARY_BLIND_KEY:
        await session.send("This field bench supports mortar_and_pestle and alchemy_table recipes.\r\n")
        for recipe in crafting.ALCHEMY_RECIPES:
            output = crafting.ITEMS_BY_KEY.get(recipe.output_item_key)
            output_name = output.name if output else recipe.output_item_key
            materials = ", ".join(f"{requirement.quantity}x {requirement.item_key}" for requirement in recipe.materials)
            await session.send(
                f"  {output_name} — skill {recipe.minimum_skill}; {materials}; station {recipe.station_key}.\r\n"
            )
        await session.send("Use BREW <item name> here. Example: BREW MINOR HEALING POTION.\r\n")
    else:
        await session.send("The beginner public field bench is at the Apothecary Blind in the maintained Goblin swamp.\r\n")


async def _handle_alchemy(session, command: str) -> bool:
    if session.character is None or not _room_is_swamp(session.character.current_room):
        return False
    normalized = command.strip().lower()

    if normalized in {"alchemy", "brew"}:
        await _show_goblin_alchemy(session)
        return True

    if not (
        normalized.startswith("brew ")
        or normalized.startswith("craft ")
        or normalized.startswith("prepare ")
        or normalized.startswith("distill ")
        or normalized.startswith("blend ")
    ):
        return False

    target = _command_target(command)
    recipe = _resolve_alchemy_recipe(target)
    if recipe is None:
        if normalized.startswith("brew "):
            await session.send("\r\nPella's field notes do not list an Alchemy recipe by that name. Type ALCHEMY to review the available recipes.\r\n")
            return True
        return False

    if session.character.current_room != GOBLIN_APOTHECARY_BLIND_KEY:
        await session.send("\r\nYou need an equipped alchemy workspace. The maintained beginner bench is at the Apothecary Blind.\r\n")
        return True

    if recipe.station_key not in {"mortar_and_pestle", "alchemy_table"}:
        await session.send(f"\r\nThis field bench cannot provide the required {recipe.station_key}.\r\n")
        return True

    result = craft_recipe(
        session.database,
        session.character.id,
        recipe.key,
        station_key=recipe.station_key,
    )
    if result.success and result.output_item_key:
        output = crafting.ITEMS_BY_KEY.get(result.output_item_key)
        output_name = output.name if output else result.output_item_key
        new_skill = trade_skill_value(session.database, session.character.id, "alchemy")
        await session.send(
            f"\r\nYou work through the measured steps at the field bench and produce {result.output_quantity}x {output_name}. "
            f"Alchemy improves through use (skill {new_skill}).\r\n"
        )
    else:
        await session.send("\r\n" + result.message + "\r\n")
    return True


def install_goblin_swamp_runtime(player_session_class, world_service) -> None:
    install_goblin_swamp_content(world_service)
    if getattr(player_session_class, "_goblin_swamp_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = player_session_class.move_character

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        if self.character is None:
            return
        after = self.character.current_room
        if before == after or after not in GOBLIN_SWAMP_ROOM_KEYS:
            return
        if self.character.race == "goblin":
            flags = self.database.list_flags(self.character.id)
            if GOBLIN_SWAMP_ENTERED_FLAG not in flags:
                self.database.grant_flag(self.character.id, GOBLIN_SWAMP_ENTERED_FLAG)
                await self.send(
                    "\r\nThe maintained paths branch around you instead of pointing toward one required objective. This is the Goblin beginner swamp: gathering routes, light wildlife, alchemy stations, and a clearly marked boundary before the deeper mire.\r\n"
                    "Try HERBALISM to inspect local gathering opportunities.\r\n"
                )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if await _handle_swamp_gathering(self, normalized):
            return
        if await _handle_alchemy(self, command):
            return

        had_instance_prompt = "prompt" in self.__dict__
        prior_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await previous_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = prior_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"} and _room_is_swamp(self.character.current_room):
            await self.send(
                "Goblin swamp commands: HERBALISM [target], GATHER <target>, COLLECT WATER, ALCHEMY, BREW <recipe>. "
                "The maintained beginner routes branch north/east/west from the First Piling after Beyond the Painted Line.\r\n"
            )

    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_swamp_runtime_installed = True
