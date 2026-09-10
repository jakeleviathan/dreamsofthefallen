from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


TROLL_REGION_KEY = "troll_strongholds"
TROLL_START_ROOM_KEY = "troll_frostroot_camp"
TROLL_HIDEWIND_RING_KEY = "troll_hidewind_ring"
TROLL_EMBER_HOLLOW_KEY = "troll_ember_hollow"
TROLL_TRACKLINE_VERGE_KEY = "troll_trackline_verge"
TROLL_WHITEHORN_HOLLOW_KEY = "troll_whitehorn_hollow"
TROLL_TETHER_YARD_KEY = "troll_tether_yard"
TROLL_WINDSCAR_SHELF_KEY = "troll_windscar_shelf"
TROLL_STONEJAW_PASS_KEY = "troll_stonejaw_pass"

TROLL_SURVIVAL_ROOM_KEYS = (
    TROLL_START_ROOM_KEY,
    TROLL_HIDEWIND_RING_KEY,
    TROLL_EMBER_HOLLOW_KEY,
    TROLL_TRACKLINE_VERGE_KEY,
    TROLL_WHITEHORN_HOLLOW_KEY,
    TROLL_TETHER_YARD_KEY,
    TROLL_WINDSCAR_SHELF_KEY,
    TROLL_STONEJAW_PASS_KEY,
)

TROLL_WIND_READ_FLAG = "troll_survival_wind_read"
TROLL_DEADFALL_GATHERED_FLAG = "troll_survival_deadfall_gathered"
TROLL_WINDBREAK_FLAG = "troll_survival_windbreak_built"
TROLL_FIRE_LAID_FLAG = "troll_survival_fire_laid"
TROLL_FIRE_LIT_FLAG = "troll_survival_fire_lit"
TROLL_REGEN_LEARNED_FLAG = "troll_survival_regeneration_observed"
TROLL_COLD_COMPLETE_FLAG = "troll_first_cold_complete"
TROLL_TRACKS_READ_FLAG = "troll_tracks_read"
TROLL_QUARRY_JUDGMENT_FLAG = "troll_quarry_judgment"
TROLL_ANIMAL_HANDLING_FLAG = "troll_animal_handling_lesson"
TROLL_TRACK_COMPLETE_FLAG = "troll_first_hunt_lesson_complete"
TROLL_OUTSIDER_PROBLEM_READ_FLAG = "troll_outsider_problem_read"
TROLL_OUTSIDER_RAM_CALMED_FLAG = "troll_outsider_ram_calmed"
TROLL_OUTSIDER_HARNESS_FREED_FLAG = "troll_outsider_harness_freed"
TROLL_OUTSIDER_LOAD_BALANCED_FLAG = "troll_outsider_load_balanced"
TROLL_OUTSIDER_ROUTE_READ_FLAG = "troll_outsider_route_read"
TROLL_OUTSIDER_COMPLETE_FLAG = "troll_outsider_competence_shown"

TROLL_COLD_QUEST_KEY = "troll_fire_before_pride"
TROLL_TRACK_QUEST_KEY = "troll_tracks_have_reasons"
TROLL_OUTSIDER_QUEST_KEY = "troll_what_they_expected"


TROLL_COLD_QUEST = QuestDefinition(
    key=TROLL_COLD_QUEST_KEY,
    name="A Fire Before Pride",
    style="structured",
    description=(
        "Hunter Raska Greybark teaches a new Troll that surviving hard country begins before danger appears: read the wind, build shelter, make fire, and understand Troll regeneration as steady resilience rather than invulnerability."
    ),
    objective_steps=(
        ("speak_raska", "TALK RASKA at Frostroot Camp."),
        ("read_wind", "Go east to Hidewind Ring and EXAMINE WIND before building anything."),
        ("gather_deadfall", "GATHER DEADFALL after identifying the sheltered side of the practice ring."),
        ("build_windbreak", "BUILD WINDBREAK from the gathered deadfall."),
        ("lay_fire", "Return through camp to Ember Hollow and LAY FIRE in the protected hearth."),
        ("light_fire", "LIGHT FIRE only after the fuel bed is properly laid."),
        ("endure_cold", "Use ENDURE COLD for a brief controlled exposure beside the ready hearth."),
        ("recover_by_fire", "REST BY FIRE and observe how Troll regeneration adds to ordinary recovery."),
        ("return_raska", "Return to Frostroot Camp and TALK RASKA."),
        ("complete", "You learned that toughness begins with preparation, not bravado."),
    ),
)


TROLL_TRACK_QUEST = QuestDefinition(
    key=TROLL_TRACK_QUEST_KEY,
    name="Tracks Have Reasons",
    style="structured",
    description=(
        "Raska sends the new Troll beyond the shelter line to read animal sign, judge whether quarry should actually be taken, and handle one of the camp's working elk without frightening it."
    ),
    objective_steps=(
        ("study_tracks", "Follow an opened route to Trackline Verge and EXAMINE TRACKS."),
        ("follow_tracks", "Use TRACK WHITEHORN to decide which trail is fresh enough to follow."),
        ("observe_quarry", "Go east to Whitehorn Hollow and OBSERVE WHITEHORN before deciding whether to hunt."),
        ("leave_quarry", "Use LEAVE DOE once you understand why this animal should not be taken."),
        ("approach_elk", "Reach the Tether Yard and APPROACH ELK without crowding it."),
        ("inspect_harness", "CHECK HARNESS before asking anything of the pack elk."),
        ("calm_elk", "CALM ELK and let the animal accept your presence on its own terms."),
        ("return_raska", "Return to Frostroot Camp and TALK RASKA."),
        ("complete", "You practiced tracking, hunting judgment, and animal handling as related skills."),
    ),
)


TROLL_OUTSIDER_QUEST = QuestDefinition(
    key=TROLL_OUTSIDER_QUEST_KEY,
    name="What They Expected",
    style="structured",
    description=(
        "A Dwarven courier has stalled a freight sledge on Windscar Shelf and assumes the nearest Troll's best contribution will be brute force. The actual solution requires animal handling, load sense, and reading the snow."
    ),
    objective_steps=(
        ("meet_outsider", "Go to Windscar Shelf and TALK BRANNIK."),
        ("inspect_problem", "EXAMINE PACK RAM before trying to drag the sledge."),
        ("calm_ram", "CALM RAM so the frightened animal stops fighting its tack."),
        ("free_harness", "LOOSEN HARNESS after the ram is calm enough to handle safely."),
        ("balance_load", "SHIFT LOAD so the sledge no longer twists sideways behind the animal."),
        ("read_route", "READ SNOW and identify the firmer route around the drift."),
        ("return_outsider", "TALK BRANNIK after the animal, load, and route are all corrected."),
        ("complete", "You solved the courier's problem without proving anyone's stereotype for them."),
    ),
)


RASKA_GREYBARK = NpcDefinition(
    key="troll_hunter_raska_greybark",
    name="Hunter Raska Greybark",
    short_description="an older Troll hunter repairing a snowshoe frame with slow, exact knots",
    room_key=TROLL_START_ROOM_KEY,
    role="Troll starter mentor, hunter, and survival instructor",
    dialogue=(
        "Raska tests a knot with one thumb. 'The cold is not impressed by courage. Build the shelter anyway.'",
        "'Outsiders hear that Trolls heal quickly and imagine we survive by ignoring wounds. That is backwards. A body that mends well is worth taking care of.'",
        "'A hunter reads the animal, the ground, the weather, and their own hunger. Killing is one possible answer, not the definition of the skill.'",
    ),
)


MORA_ELKHAND = NpcDefinition(
    key="troll_handler_mora_elkhand",
    name="Mora Elkhand",
    short_description="a broad-shouldered Troll handler brushing ice from a pack elk's chest strap",
    room_key=TROLL_TETHER_YARD_KEY,
    role="working-animal handler and Troll starter instructor",
    dialogue=(
        "Mora keeps her voice low around the tether line. 'Big animals notice impatience before they notice strength.'",
        "'Check the tack before you blame the beast. Half of animal handling is discovering the mistake belongs to the person who tied the strap.'",
    ),
)


BRANNIK_SLATEBOOT = NpcDefinition(
    key="troll_outsider_brannik_slateboot",
    name="Brannik Slateboot",
    short_description="a Dwarven courier standing beside a skewed freight sledge and a visibly unhappy pack ram",
    room_key=TROLL_WINDSCAR_SHELF_KEY,
    role="outsider courier and stereotype-reversal quest contact",
    dialogue=(
        "Brannik eyes the sledge, then your height. 'Good. I was hoping they'd send one of the strong ones.'",
        "The pack ram pins its ears while Brannik keeps one hand on the freight rope. Something about the scene clearly needs more thought than more pulling.",
    ),
)

TROLL_NPCS = (RASKA_GREYBARK, MORA_ELKHAND, BRANNIK_SLATEBOOT)


TROLL_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=TROLL_START_ROOM_KEY,
        name="Frostroot Camp",
        region_key=TROLL_REGION_KEY,
        description=(
            "A Troll stronghold has been built where black spruce forest thins into open tundra. Hide-roofed shelters sit low behind stone wind walls, smoke escapes through stitched vents, and heavy sledges rest on raised timber racks above the snow. Nothing is ornamental without also being useful. Hunters, priests, children, and animal handlers cross the same packed central ground while distant ridges disappear into cold haze."
        ),
        exits={"east": TROLL_HIDEWIND_RING_KEY, "north": TROLL_EMBER_HOLLOW_KEY, "west": TROLL_TETHER_YARD_KEY},
        npc_keys=(RASKA_GREYBARK.key,),
        tags=("troll_start", "safe", "stronghold", "forest_edge", "tundra", "survival"),
    ),
    RoomDefinition(
        key=TROLL_HIDEWIND_RING_KEY,
        name="Hidewind Ring",
        region_key=TROLL_REGION_KEY,
        description=(
            "A shallow practice basin lies east of camp between spruce roots and a shoulder of exposed stone. Old windbreak frames have been dismantled and stacked nearby so every apprentice must read the day's conditions instead of copying yesterday's shelter. Deadfall lies beneath the trees, while ribbons tied at several heights make the shifting wind visible."
        ),
        exits={"west": TROLL_START_ROOM_KEY, "north": TROLL_TRACKLINE_VERGE_KEY},
        tags=("safe", "survival_training", "shelter", "forest_edge", "wind"),
    ),
    RoomDefinition(
        key=TROLL_EMBER_HOLLOW_KEY,
        name="Ember Hollow",
        region_key=TROLL_REGION_KEY,
        description=(
            "A scooped hollow north of camp shelters several stone hearths from the prevailing wind. Split kindling dries beneath an overhang, ash is stored separately from fresh fuel, and a row of blackened kettles hangs where newcomers can see that fire here is infrastructure rather than ceremony. Beyond the hollow, a cairned trail climbs toward Stonejaw Pass."
        ),
        exits={"south": TROLL_START_ROOM_KEY, "east": TROLL_TRACKLINE_VERGE_KEY, "north": TROLL_STONEJAW_PASS_KEY},
        tags=("safe", "survival_training", "fire", "sheltered", "cold"),
    ),
    RoomDefinition(
        key=TROLL_TRACKLINE_VERGE_KEY,
        name="Trackline Verge",
        region_key=TROLL_REGION_KEY,
        description=(
            "Forest and tundra overlap here in a broad strip of wind-packed snow, soft needles, exposed soil, and frozen mud. The mixed ground preserves different kinds of sign side by side: hoof edges, paw pads, dragged brush, droppings, feeding scars, and places where wind has erased only half a trail. It is a classroom with no signs announcing itself as one."
        ),
        exits={"south": TROLL_HIDEWIND_RING_KEY, "west": TROLL_EMBER_HOLLOW_KEY, "east": TROLL_WHITEHORN_HOLLOW_KEY},
        tags=("safe", "tracking", "hunting", "forest_edge", "animal_sign"),
    ),
    RoomDefinition(
        key=TROLL_WHITEHORN_HOLLOW_KEY,
        name="Whitehorn Hollow",
        region_key=TROLL_REGION_KEY,
        description=(
            "A quiet hollow opens among dwarf pines east of the trackline. Browsed twigs and fresh hoofprints show that whitehorn deer feed here when the wind is hard on the open flats. The ground gives a hunter room to observe without having to close distance, and the safest route back toward camp bends south along a low shelf."
        ),
        exits={"west": TROLL_TRACKLINE_VERGE_KEY, "south": TROLL_WINDSCAR_SHELF_KEY},
        tags=("safe", "hunting_lesson", "wildlife", "observation", "forest_edge"),
    ),
    RoomDefinition(
        key=TROLL_TETHER_YARD_KEY,
        name="Tether Yard",
        region_key=TROLL_REGION_KEY,
        description=(
            "A broad yard west of camp is divided by low timber rails rather than cages. Pack elk stand beneath rough awnings while handlers inspect hooves, dry tack, redistribute loads, and teach young animals to tolerate sledges behind them. The yard smells of hay, hide oil, snow, and warm animal breath. A narrow northern trail climbs toward Windscar Shelf."
        ),
        exits={"east": TROLL_START_ROOM_KEY, "north": TROLL_WINDSCAR_SHELF_KEY},
        npc_keys=(MORA_ELKHAND.key,),
        tags=("safe", "animal_handling", "working_animals", "stronghold", "training"),
    ),
    RoomDefinition(
        key=TROLL_WINDSCAR_SHELF_KEY,
        name="Windscar Shelf",
        region_key=TROLL_REGION_KEY,
        description=(
            "A shelf of hard snow and dark rock overlooks the stronghold from the southwest. Freight routes from other peoples occasionally use this exposed crossing because it is faster than the lower forest road. Today a small Dwarven sledge has stopped crooked in a drift, its pack ram tense between the shafts while loose crates pull the load sideways."
        ),
        exits={"north": TROLL_WHITEHORN_HOLLOW_KEY, "west": TROLL_TETHER_YARD_KEY},
        npc_keys=(BRANNIK_SLATEBOOT.key,),
        tags=("safe", "outsider_encounter", "freight_route", "snow", "problem_solving"),
    ),
    RoomDefinition(
        key=TROLL_STONEJAW_PASS_KEY,
        name="Stonejaw Pass",
        region_key=TROLL_REGION_KEY,
        description=(
            "Two slabs of weathered rock narrow the trail above Ember Hollow into a natural gate. Beyond them, cairns continue toward high tundra and deep-forest routes that the starter patrol does not maintain. Claw marks, old camp ash, broken antler, and snow-scoured stone make it clear that Troll country becomes genuinely dangerous beyond this point even when nothing is attacking right now."
        ),
        exits={"south": TROLL_EMBER_HOLLOW_KEY},
        tags=("safe", "starter_boundary", "danger_hint", "tundra", "wilderness"),
    ),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    touch: str = "",
    listen: str = "",
    condition: ViewCondition | None = None,
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
        condition=condition or ViewCondition(),
    )


def _exit(direction: str, destination: str, name: str, text: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, **kwargs)


def _day(key: str, text: str) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=30, condition=ViewCondition(time_buckets=("day",)))


def _night(key: str, text: str) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=35, condition=ViewCondition(time_buckets=("night",)))


def _snow(key: str, text: str) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=45, condition=ViewCondition(weather=("snow",)))


def _storm(key: str, text: str) -> DescriptionLayer:
    return DescriptionLayer(key, text, priority=50, condition=ViewCondition(weather=("storm",)))


def troll_room_augmentations() -> dict[str, RoomAugmentation]:
    cold_ready = ViewCondition(required_flags=(TROLL_COLD_COMPLETE_FLAG,))
    return {
        TROLL_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", TROLL_HIDEWIND_RING_KEY, "Hidewind Ring", "You leave the packed camp center for the shelter-training basin."),
                _exit("north", TROLL_EMBER_HOLLOW_KEY, "Ember Hollow", "You follow a smoke-dark path north into the protected hearth hollow."),
                _exit("west", TROLL_TETHER_YARD_KEY, "Tether Yard", "You pass sled racks and feed bundles into the working-animal yard."),
            ),
            features=(
                _feature("frostroot_hearth", "Common Hearth", "the camp's broad central fire, banked low against the cold", "The common hearth is never allowed to burn wastefully. Coals are banked under ash between meals and watches, and every nearby shelter keeps a covered ember pot for emergencies.", aliases=("hearth", "fire", "common fire"), listen="Low voices mix with the pop of resinous wood and the scrape of snow from boots."),
                _feature("migration_sledges", "Migration Sledges", "heavy sledges stored above the snow on timber racks", "The sledges are built for dismantling. Lash points, replaceable runners, hide covers, and spare pegs let a stronghold move part of itself without pretending every camp is permanent.", aliases=("sledges", "sleds", "racks"), search="Repair bundles under the racks contain cordage, runner pegs, hide patches, and spare harness buckles."),
            ),
            description_layers=(
                _day("troll_start_day", "Daylight makes the camp busy rather than comfortable; every clear hour is used to dry hides, repair tack, split fuel, or check routes."),
                _night("troll_start_night", "At night the stronghold contracts around its fires. Watches change quietly while distant animals call beyond the last shelters."),
                _snow("troll_start_snow", "Fresh snow softens the camp's edges, but swept paths and raised storage keep the stronghold functioning without hurry."),
                _storm("troll_start_storm", "Wind lashes the hide roofs, yet the low shelters and stone walls turn the storm into a maintenance problem rather than a panic."),
            ),
        ),
        TROLL_HIDEWIND_RING_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", TROLL_START_ROOM_KEY, "Frostroot Camp", "You return west to the stronghold's central ground."),
                ExitDefinition(
                    direction="north",
                    destination_key=TROLL_TRACKLINE_VERGE_KEY,
                    name="Trackline Verge",
                    travel_text="Prepared for the cold, you leave the practice ring for the first tracking ground.",
                    failure_text="Raska has not sent you beyond the shelter line yet. Learn wind, shelter, and fire before following animal sign.",
                    condition=cold_ready,
                    hidden_when_unavailable=False,
                ),
            ),
            features=(
                _feature("wind_ribbons", "Wind Ribbons", "hide ribbons tied at several heights to reveal crosswinds and ground eddies", "The highest ribbons pull from the northwest, but the lowest ones curl back behind the stone shoulder. A shelter built blindly in the center would catch the full wind; the lee side of the rock offers a stable pocket.", aliases=("wind", "ribbons", "wind signs", "weather ribbons"), listen="The upper ribbons snap sharply while the lower ones barely stir behind the stone."),
                _feature("deadfall_patch", "Dry Deadfall", "storm-broken spruce limbs protected beneath living branches", "The deadfall is dry enough to use because it never settled into the wet ground. Troll apprentices are taught to take broken wood before cutting live shelter trees.", aliases=("deadfall", "branches", "wood", "fuel")),
                _feature("finished_windbreak", "Practice Windbreak", "a low angled wall of deadfall and hide ties facing the prevailing wind", "The windbreak is deliberately low and ugly. Air spills over it instead of catching under it, and the sheltered side is already noticeably quieter.", aliases=("windbreak", "shelter", "practice shelter"), condition=ViewCondition(required_flags=(TROLL_WINDBREAK_FLAG,))),
            ),
            description_layers=(
                DescriptionLayer("troll_windbreak_built", "Your practice windbreak stands in the stone shoulder's lee, turning the worst of the wind over the basin instead of through it.", priority=70, condition=ViewCondition(required_flags=(TROLL_WINDBREAK_FLAG,))),
                _snow("troll_hidewind_snow", "Snow grains reveal every eddy around the rock, making the difference between exposed and sheltered ground easy to see."),
            ),
        ),
        TROLL_EMBER_HOLLOW_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", TROLL_START_ROOM_KEY, "Frostroot Camp", "You follow the protected path south to camp."),
                ExitDefinition(
                    direction="east",
                    destination_key=TROLL_TRACKLINE_VERGE_KEY,
                    name="Trackline Verge",
                    travel_text="You leave the hearth hollow for the mixed ground of Trackline Verge.",
                    failure_text="The tracking ground can wait. Raska's first lesson is to make sure you can shelter and warm yourself before ranging farther.",
                    condition=cold_ready,
                    hidden_when_unavailable=False,
                ),
                _exit("north", TROLL_STONEJAW_PASS_KEY, "Stonejaw Pass", "You climb between black rocks toward the maintained starter boundary."),
            ),
            features=(
                _feature("protected_hearth", "Practice Hearth", "a shallow stone hearth tucked below the wind line", "The hearth is shaped to draw air from the sheltered side while a stone lip blocks gusts from scattering sparks. Char patterns show generations of small, controlled fires rather than bonfires.", aliases=("hearth", "fire pit", "practice hearth", "stones")),
                _feature("laid_fire", "Laid Fire", "a compact fuel bed of tinder, finger wood, and split deadfall waiting for flame", "The fuel graduates from fine tinder to thicker pieces with enough air between them to catch without constant blowing.", aliases=("fuel bed", "laid fire", "kindling"), condition=ViewCondition(required_flags=(TROLL_FIRE_LAID_FLAG,), forbidden_flags=(TROLL_FIRE_LIT_FLAG,))),
                _feature("lit_fire", "Training Fire", "a small clean fire burning low inside the protected hearth", "The fire is intentionally modest. It burns hot enough to restore feeling and dry gloves without consuming a night's fuel in a few impressive minutes.", aliases=("fire", "training fire", "flames", "embers"), touch="You hold your hands near the heat rather than in it. The warmth returns gradually.", condition=ViewCondition(required_flags=(TROLL_FIRE_LIT_FLAG,))),
            ),
            description_layers=(
                DescriptionLayer("troll_fire_lit_layer", "A small fire now burns in your practice hearth, its flame almost motionless behind the stone lip.", priority=70, condition=ViewCondition(required_flags=(TROLL_FIRE_LIT_FLAG,))),
                _night("troll_ember_night", "At night even the unlit hearth stones seem to hold the memory of old warmth."),
                _storm("troll_ember_storm", "The hollow proves its design in the storm: gusts roar overhead while the hearth level remains comparatively calm."),
            ),
        ),
        TROLL_TRACKLINE_VERGE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", TROLL_HIDEWIND_RING_KEY, "Hidewind Ring", "You follow your own boot marks south toward the shelter basin."),
                _exit("west", TROLL_EMBER_HOLLOW_KEY, "Ember Hollow", "You angle west toward smoke rising from the protected hearths."),
                _exit("east", TROLL_WHITEHORN_HOLLOW_KEY, "Whitehorn Hollow", "You follow the firmer animal trail east among dwarf pines."),
            ),
            features=(
                _feature("track_fan", "Mixed Tracks", "overlapping animal signs preserved across snow, needles, and frozen mud", "Several trails cross here. Hare prints are old and softened. A fox passed after the last powder. Fresh whitehorn hoof edges still hold sharp walls, and one smaller set travels beside an adult's tracks.", aliases=("tracks", "trail", "sign", "animal tracks", "hoofprints"), search="Broken browse tips point east. The fresh whitehorn trail is traveling, not fleeing."),
                _feature("wind_erasure", "Wind-Erased Sign", "half-preserved tracks showing how weather changes evidence", "On the exposed side of the verge, the same tracks are nearly gone. Under spruce cover they remain crisp. Raska's lesson is obvious: absence of sign is not proof of absence.", aliases=("wind sign", "erased tracks", "weathered tracks")),
            ),
            description_layers=(
                _snow("troll_trackline_snow", "New flakes begin softening the oldest prints first, putting a visible clock on every trail."),
                _night("troll_trackline_night", "Moonlight catches depressions in the snow differently from daylight; depth and shadow become part of reading the ground."),
            ),
        ),
        TROLL_WHITEHORN_HOLLOW_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", TROLL_TRACKLINE_VERGE_KEY, "Trackline Verge", "You withdraw west along the trail without crowding the feeding hollow."),
                _exit("south", TROLL_WINDSCAR_SHELF_KEY, "Windscar Shelf", "You take a low shelf south toward the freight crossing."),
            ),
            features=(
                _feature("whitehorn_doe", "Whitehorn Doe", "an adult whitehorn feeding at the edge of the dwarf pines", "The doe is healthy and well-fed. A much smaller set of tracks circles close behind her, and a pale fawn is bedded under the branches where its outline nearly disappears against old snow. Taking the doe would leave dependent young at exactly the wrong time.", aliases=("whitehorn", "doe", "deer", "quarry", "animal"), listen="The doe tears browse quietly, pausing whenever the fawn shifts beneath the pines."),
                _feature("fawn_bed", "Hidden Fawn Bed", "a shallow sheltered depression beneath the pines", "The fawn is not abandoned. Its mother's fresh tracks circle the bed repeatedly. A competent hunter notices the relationship before deciding the adult is available quarry.", aliases=("fawn", "bed", "young", "small tracks")),
            ),
            description_layers=(_day("troll_whitehorn_day", "The hollow offers excellent visibility without forcing a hunter closer than necessary."), _snow("troll_whitehorn_snow", "Snow gathers on the doe's back in a thin line while the fawn remains dry beneath the pines.")),
        ),
        TROLL_TETHER_YARD_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", TROLL_START_ROOM_KEY, "Frostroot Camp", "You leave the working animals for the central camp."),
                _exit("north", TROLL_WINDSCAR_SHELF_KEY, "Windscar Shelf", "You follow a freight path north toward the exposed shelf."),
            ),
            features=(
                _feature("mossback_elk", "Mossback Pack Elk", "a tall working elk waiting beside an unloaded practice sledge", "The elk watches people closely but shows no fear. Its broad chest strap sits clear of the shoulder, the traces hang without twists, and the animal has enough slack to lower its head. Good handling here begins with noticing that the tack is already correct.", aliases=("elk", "pack elk", "mossback", "animal"), listen="The elk exhales through its nose and shifts one hoof when someone moves too quickly nearby."),
                _feature("harness_rack", "Harness Rack", "oiled straps and traces hung in matched working sets", "Each harness is marked to a particular animal and adjusted over time. Troll handlers do not treat working animals as interchangeable engines merely because they are strong.", aliases=("harness", "tack", "straps", "rack")),
            ),
            description_layers=(_day("troll_tether_day", "Handlers move steadily among the animals, checking feet and tack before loading a single sledge."), _night("troll_tether_night", "Most working animals are bedded down, and the yard's conversations drop to the same quiet volume used around sleeping children.")),
        ),
        TROLL_WINDSCAR_SHELF_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", TROLL_WHITEHORN_HOLLOW_KEY, "Whitehorn Hollow", "You leave the freight shelf for the quieter whitehorn hollow."),
                _exit("west", TROLL_TETHER_YARD_KEY, "Tether Yard", "You follow the lower freight track west toward the camp animals."),
            ),
            features=(
                _feature("dwarf_sledge", "Skewed Freight Sledge", "a loaded Dwarven sledge sitting diagonally in a wind-packed rut", "The sledge is not deeply buried. Its right runner is riding a soft drift because two heavy crates were lashed too far to that side. Pulling harder would increase the twist instead of fixing it.", aliases=("sledge", "sled", "freight", "crates", "load"), search="The firmer snow lies several paces upslope where wind has stripped loose powder down to hard crust."),
                _feature("pack_ram", "Pack Ram", "a stout Dwarven pack ram standing tense between the sledge shafts", "The ram's ears are pinned and one rear strap has rolled into a narrow twist against its flank. Every time the sledge pulls sideways, the strap pinches harder. The animal is resisting pain and bad balance, not refusing work.", aliases=("ram", "pack ram", "animal", "dwarf ram"), listen="The ram breathes fast and gives a short irritated grunt whenever the skewed load tugs the harness."),
            ),
            description_layers=(
                DescriptionLayer("troll_outsider_solved_layer", "Brannik's sledge now sits square on firm snow, its load balanced and the pack ram standing quietly in comfortable tack.", priority=80, condition=ViewCondition(required_flags=(TROLL_OUTSIDER_COMPLETE_FLAG,))),
                _storm("troll_windscar_storm", "Wind tears across the shelf hard enough to erase shallow tracks, making every sheltered patch and hard-crusted route more valuable."),
            ),
        ),
        TROLL_STONEJAW_PASS_KEY: RoomAugmentation(
            exit_overrides=(_exit("south", TROLL_EMBER_HOLLOW_KEY, "Ember Hollow", "You descend from the boundary cairns toward the protected hearths."),),
            features=(
                _feature("boundary_cairns", "Boundary Cairns", "low stone markers indicating the limit of the maintained apprentice routes", "Each cairn carries practical marks for water, shelter distance, seasonal game movement, and known hazards. Beyond them, the trails stop promising that someone else has checked the weather first.", aliases=("cairns", "markers", "boundary", "stones"), search="One fresh marker warns that the upper ravine is unstable after recent freeze-thaw cycles."),
                _feature("old_claw_sign", "Old Claw Sign", "deep animal scratches on one wind-polished slab", "The marks are old enough that lichen grows inside them. Whatever made them is not waiting here now, but the stone preserves a useful reminder that a quiet wilderness is not an empty one.", aliases=("claw marks", "claws", "sign", "scratches")),
            ),
            description_layers=(_snow("troll_pass_snow", "Snow closes over the farther cairns one by one, making the maintained boundary more important rather than less."), _night("troll_pass_night", "Beyond the last cairn the land becomes a sequence of silhouettes with no village light to promise an easy return.")),
        ),
    }


def install_troll_content(world_service=None) -> None:
    known = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in TROLL_ROOMS if room.key not in known)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    legacy_world.ROOMS_BY_KEY.update({room.key: room for room in TROLL_ROOMS})

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    for npc in TROLL_NPCS:
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    for quest in (TROLL_COLD_QUEST, TROLL_TRACK_QUEST, TROLL_OUTSIDER_QUEST):
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    if world_service is not None:
        world_service.legacy_rooms.update({room.key: room for room in TROLL_ROOMS})
        world_service.augmentations.update(troll_room_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in TROLL_SURVIVAL_ROOM_KEYS:
                cache.pop(room_key, None)


def _quest(session, definition: QuestDefinition):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, definition.key)


def _initialize_or_reconcile_troll(session) -> None:
    if session.character is None or session.character.race != "troll":
        return
    character_id = session.character.id
    if not session.character.current_room:
        session.database.set_character_room(character_id, TROLL_START_ROOM_KEY)
        if not session.character.bind_room:
            session.database.set_bind_room(character_id, TROLL_START_ROOM_KEY)
        refreshed = session.database.get_character_by_name(session.character.name)
        if refreshed is not None:
            session.character = refreshed

    cold = _quest(session, TROLL_COLD_QUEST)
    if cold is None:
        session.database.start_quest(character_id, TROLL_COLD_QUEST.key, "speak_raska")
    elif cold.get("status") == "completed":
        session.database.grant_flag(character_id, TROLL_COLD_COMPLETE_FLAG)

    track = _quest(session, TROLL_TRACK_QUEST)
    if track and track.get("status") == "completed":
        session.database.grant_flag(character_id, TROLL_TRACK_COMPLETE_FLAG)

    outsider = _quest(session, TROLL_OUTSIDER_QUEST)
    if outsider and outsider.get("status") == "completed":
        session.database.grant_flag(character_id, TROLL_OUTSIDER_COMPLETE_FLAG)


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches(target: str, *names: str) -> bool:
    return target in {name.lower() for name in names}


async def _talk_raska(session) -> bool:
    assert session.character is not None
    if session.character.race != "troll":
        return False
    cold = _quest(session, TROLL_COLD_QUEST)
    if cold is None:
        _initialize_or_reconcile_troll(session)
        cold = _quest(session, TROLL_COLD_QUEST)
    if not cold:
        return False

    if cold.get("status") == "active":
        step = cold.get("current_step")
        if step == "speak_raska":
            session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "read_wind")
            await session.send(
                "\r\nRaska looks past you toward the open country. 'Before you hunt it, cross it, fight in it, or boast about surviving it, learn what the cold is doing.'\r\n"
                "'East is Hidewind Ring. EXAMINE WIND. Build where the air tells you, not where your pride thinks a shelter ought to stand.'\r\n"
                "New quest: A Fire Before Pride.\r\n"
            )
            return True
        if step == "return_raska":
            session.database.grant_flag(session.character.id, TROLL_COLD_COMPLETE_FLAG)
            session.database.complete_quest(session.character.id, TROLL_COLD_QUEST.key)
            if _quest(session, TROLL_TRACK_QUEST) is None:
                session.database.start_quest(session.character.id, TROLL_TRACK_QUEST.key, "study_tracks")
            await session.send(
                "\r\nRaska inspects the soot on your hands and the fact that you came back warm enough to complain. 'Good. Regeneration is not permission to be careless. It is one more advantage for a Troll who prepared correctly.'\r\n"
                "'Now north from the practice ground, or east from Ember Hollow, to Trackline Verge. EXAMINE TRACKS. Hunting begins before you ever see the animal.'\r\n"
                "Quest complete: A Fire Before Pride.\r\n"
                "New quest: Tracks Have Reasons.\r\n"
            )
            return True
        objective = TROLL_COLD_QUEST.objective_for_step(step)
        await session.send("\r\nRaska does not hurry the lesson. 'Do the next thing because you understand why it comes next.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    track = _quest(session, TROLL_TRACK_QUEST)
    if track and track.get("status") == "active":
        step = track.get("current_step")
        if step == "return_raska":
            session.database.grant_flag(session.character.id, TROLL_TRACK_COMPLETE_FLAG)
            session.database.complete_quest(session.character.id, TROLL_TRACK_QUEST.key)
            if _quest(session, TROLL_OUTSIDER_QUEST) is None:
                session.database.start_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "meet_outsider")
            await session.send(
                "\r\nRaska listens to your account of the doe and the pack elk. 'You found prey and chose not to take it. You handled a stronger animal without making strength into an argument. That is hunting too.'\r\n"
                "He glances toward Windscar Shelf. 'A Dwarf has managed to make a freight problem out of snow, straps, and assumptions. Go see which one is actually stopping him.'\r\n"
                "Quest complete: Tracks Have Reasons.\r\n"
                "New quest: What They Expected.\r\n"
            )
            return True
        objective = TROLL_TRACK_QUEST.objective_for_step(step)
        await session.send("\r\nRaska says, 'Tracks are statements. Read the whole sentence.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    outsider = _quest(session, TROLL_OUTSIDER_QUEST)
    if outsider and outsider.get("status") == "active":
        objective = TROLL_OUTSIDER_QUEST.objective_for_step(outsider.get("current_step"))
        await session.send("\r\nRaska tilts his head toward Windscar Shelf. 'The courier is still there. Try solving the problem he has instead of the one he expects you to solve.'\r\n")
        if objective:
            await session.send(f"Current objective: {objective}\r\n")
        return True

    await session.send(
        "\r\nRaska returns to his snowshoe frame. 'Shelter before pride. Read before chasing. Calm before force. Those lessons work outside Troll country too.'\r\n"
    )
    return True


async def _talk_mora(session) -> bool:
    assert session.character is not None
    if session.character.race != "troll":
        return False
    track = _quest(session, TROLL_TRACK_QUEST)
    if not track or track.get("status") != "active":
        await session.send("\r\nMora scratches the pack elk under its jaw. 'Working animals are not practice equipment. If Raska sends you here, I'll know what he expects you to learn.'\r\n")
        return True
    objective = TROLL_TRACK_QUEST.objective_for_step(track.get("current_step"))
    await session.send("\r\nMora keeps one hand loose at her side. 'Let the elk notice you. Then look at the harness before you ask the animal to accept anything from you.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_brannik(session) -> bool:
    assert session.character is not None
    if session.character.race != "troll":
        return False
    outsider = _quest(session, TROLL_OUTSIDER_QUEST)
    if outsider is None:
        await session.send("\r\nBrannik looks relieved to see someone from the stronghold, then embarrassed that he has no idea who is actually responsible for the route. 'I'll wait for your people to send whoever handles freight trouble.'\r\n")
        return True
    if outsider.get("status") == "completed":
        await session.send("\r\nBrannik checks the comfortable ram before looking at the sledge. 'I've been trying to remember that order.'\r\n")
        return True
    step = outsider.get("current_step")
    if step == "meet_outsider":
        session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "inspect_problem")
        await session.send(
            "\r\nBrannik gives you an appraising look that stops at your shoulders. 'Good. I was hoping they'd send one of the strong ones. If you can just drag the rear of this thing out of the drift—'\r\n"
            "The pack ram flinches as the crooked sledge tugs its harness. Brannik notices your attention shift to the animal. 'What? The ram's stubborn. Always has been.'\r\n"
            "Before pulling anything, EXAMINE PACK RAM.\r\n"
        )
        return True
    if step == "return_outsider":
        session.database.grant_flag(session.character.id, TROLL_OUTSIDER_COMPLETE_FLAG)
        session.database.complete_quest(session.character.id, TROLL_OUTSIDER_QUEST.key)
        await session.send(
            "\r\nBrannik walks the ram forward. With the strap flat, the crates centered, and the runners on hard crust, the sledge follows with almost insulting ease.\r\n"
            "He looks at the Troll he had expected to use as a spare draft animal, then at the solved problem. 'I thought the obvious answer was asking the biggest person in camp to pull harder.'\r\n"
            "After a moment he adds, more carefully, 'You solved three smaller problems before strength mattered at all. I'll remember that.'\r\n"
            "Quest complete: What They Expected.\r\n"
        )
        return True
    objective = TROLL_OUTSIDER_QUEST.objective_for_step(step)
    await session.send("\r\nBrannik waits beside the sledge, increasingly willing to let you decide what the problem actually is.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _handle_cold_quest(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    quest = _quest(session, TROLL_COLD_QUEST)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == TROLL_HIDEWIND_RING_KEY and normalized in {"examine wind", "look wind", "read wind", "examine ribbons", "look ribbons", "check wind"}:
        if step == "read_wind":
            session.database.grant_flag(session.character.id, TROLL_WIND_READ_FLAG)
            session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "gather_deadfall")
        await session.send(
            "\r\nThe high ribbons pull northwest while the low ribbons curl almost still behind the stone shoulder. The right shelter site is not the flattest ground; it is the pocket where the rock has already done half the work. GATHER DEADFALL from beneath the spruce.\r\n"
        )
        return True

    if room == TROLL_HIDEWIND_RING_KEY and normalized in {"gather deadfall", "collect deadfall", "gather wood", "collect wood", "take deadfall"}:
        if step != "gather_deadfall":
            await session.send("\r\nThere is useful deadfall here, but Raska's exercise expects you to choose the shelter site before collecting material for it. EXAMINE WIND.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_DEADFALL_GATHERED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "build_windbreak")
        await session.send(
            "\r\nYou take storm-broken spruce from dry branches caught above the wet ground, leaving living limbs alone. The bundle is awkward but manageable. BUILD WINDBREAK in the stone's lee.\r\n"
        )
        return True

    if room == TROLL_HIDEWIND_RING_KEY and normalized in {"build windbreak", "make windbreak", "build shelter", "make shelter", "construct windbreak"}:
        if step != "build_windbreak":
            await session.send("\r\nA shelter built without reading the wind is just a wall waiting to be in the wrong place. Follow Raska's sequence first.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_WINDBREAK_FLAG)
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "lay_fire")
        await session.send(
            "\r\nYou angle the deadfall low across the lee side and lash only enough crosspieces to keep it from spreading. The wind climbs over the barrier instead of catching beneath it. No grand shelter—just a dry, quiet pocket that works.\r\n"
            "Return through camp to Ember Hollow and LAY FIRE.\r\n"
        )
        return True

    if room == TROLL_EMBER_HOLLOW_KEY and normalized in {"lay fire", "build fire", "prepare fire", "lay fuel", "make fire"}:
        if step != "lay_fire":
            await session.send("\r\nThe hearth is available, but the lesson is about sequence. Shelter and wind-reading come before relying on flame.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_FIRE_LAID_FLAG)
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "light_fire")
        await session.send(
            "\r\nYou lay dry fiber beneath pencil-thin kindling, bridge thicker pieces above it, and leave open air through the center. The fire is ready before any spark touches it. LIGHT FIRE.\r\n"
        )
        return True

    if room == TROLL_EMBER_HOLLOW_KEY and normalized in {"light fire", "ignite fire", "light hearth", "start fire"}:
        if step != "light_fire":
            await session.send("\r\nA spark without a prepared fuel bed would teach nothing except how to waste tinder. LAY FIRE first.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_FIRE_LIT_FLAG)
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "endure_cold")
        await session.send(
            "\r\nThe tinder catches, then the finger wood, then the split deadfall. Within moments a small clean flame is drawing steadily behind the stone lip. Raska's next instruction is deliberately controlled: ENDURE COLD, then come back to the fire before pride turns a lesson into an injury.\r\n"
        )
        return True

    if room == TROLL_EMBER_HOLLOW_KEY and normalized in {"endure cold", "test cold", "step into cold", "endure wind", "test endurance"}:
        if step != "endure_cold":
            await session.send("\r\nThere is no value in proving you can be cold before a ready fire and shelter exist. Finish the preparation first.\r\n")
            return True
        if session.combatant is None:
            await session.send("\r\nYour combat state is not initialized, so the controlled endurance lesson cannot measure recovery yet.\r\n")
            return True
        loss = min(3, max(0, session.combatant.current_hp - 1))
        session.combatant.current_hp -= loss
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "recover_by_fire")
        await session.send(
            f"\r\nYou step into the exposed edge of the hollow long enough for cold stress to become real, then stop exactly when the exercise says to stop. The controlled exposure costs {loss} HP and cannot reduce you below 1 HP.\r\n"
            "This is not a contest. Return your hands to the prepared heat and REST BY FIRE.\r\n"
        )
        await session.send_client_state()
        return True

    if room == TROLL_EMBER_HOLLOW_KEY and normalized in {"rest by fire", "rest at fire", "rest fire", "warm by fire", "recover by fire", "rest"}:
        if step != "recover_by_fire":
            return False
        if session.combatant is None:
            return False
        before = session.combatant.current_hp
        restored = session.combatant.apply_normal_regeneration(2)
        racial_part = 1
        session.database.grant_flag(session.character.id, TROLL_REGEN_LEARNED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_COLD_QUEST.key, "return_raska")
        await session.send(
            f"\r\nYou warm gradually instead of trying to ignore the cold. Ordinary rest supplies 2 points of recovery; Troll Regeneration adds {racial_part} more when there is room to heal. You recover {restored} HP ({before} -> {session.combatant.current_hp}).\r\n"
            "Raska's point is plain: regeneration rewards good recovery habits; it does not make exposure harmless. Return to Frostroot Camp and TALK RASKA.\r\n"
        )
        await session.send_client_state()
        return True

    return False


async def _handle_track_quest(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    quest = _quest(session, TROLL_TRACK_QUEST)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == TROLL_TRACKLINE_VERGE_KEY and normalized in {"examine tracks", "look tracks", "inspect tracks", "read tracks", "examine sign", "look sign"}:
        if step == "study_tracks":
            session.database.grant_flag(session.character.id, TROLL_TRACKS_READ_FLAG)
            session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "follow_tracks")
        await session.send(
            "\r\nYou compare edges, depth, wind damage, and the ground beneath each print. Hare sign is old. Fox sign is newer. The whitehorn trail is freshest, and a smaller set of hooves stays close beside the adult. Broken browse points east. TRACK WHITEHORN.\r\n"
        )
        return True

    if room == TROLL_TRACKLINE_VERGE_KEY and normalized in {"track whitehorn", "track deer", "follow whitehorn", "follow deer", "track hoofprints", "track trail"}:
        if step != "follow_tracks":
            await session.send("\r\nFollowing the first obvious print is not tracking. EXAMINE TRACKS and decide which trail actually tells you something current.\r\n")
            return True
        session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "observe_quarry")
        await session.send(
            "\r\nYou follow sharp hoof edges, fresh browse, and one place where the smaller animal stepped directly into the adult's print. The trail leads east into Whitehorn Hollow. Go EAST and OBSERVE WHITEHORN before deciding whether this is a hunt.\r\n"
        )
        return True

    if room == TROLL_WHITEHORN_HOLLOW_KEY and normalized in {"observe whitehorn", "observe doe", "examine whitehorn", "look whitehorn", "watch doe", "study doe", "examine doe"}:
        if step == "observe_quarry":
            session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "leave_quarry")
        await session.send(
            "\r\nThe adult is healthy. Then the smaller tracks make sense: a pale fawn is bedded beneath the dwarf pines, still dependent and perfectly camouflaged until you know where to look. The doe is possible prey, but poor quarry today. A hunter who cannot decide not to kill is just following appetite. LEAVE DOE.\r\n"
        )
        return True

    if room == TROLL_WHITEHORN_HOLLOW_KEY and normalized in {"leave doe", "leave whitehorn", "spare doe", "do not hunt", "leave deer", "leave quarry"}:
        if step != "leave_quarry":
            await session.send("\r\nFirst determine what the animal's condition and tracks are telling you. OBSERVE WHITEHORN.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_QUARRY_JUDGMENT_FLAG)
        session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "approach_elk")
        await session.send(
            "\r\nYou back out along your own route rather than pushing the doe from the feeding hollow. The choice leaves no trophy, which is part of the lesson.\r\n"
            "Next, reach the Tether Yard and APPROACH ELK.\r\n"
        )
        return True

    if room == TROLL_WHITEHORN_HOLLOW_KEY and normalized in {"attack doe", "kill doe", "attack whitehorn", "kill whitehorn", "hunt doe", "hunt whitehorn"}:
        await session.send(
            "\r\nThere is no need to turn this lesson into a kill. The fawn's presence is information a Troll hunter is expected to use, not an obstacle the tutorial lets you ignore. OBSERVE WHITEHORN, then decide accordingly.\r\n"
        )
        return True

    if room == TROLL_TETHER_YARD_KEY and normalized in {"approach elk", "approach pack elk", "approach mossback", "go to elk"}:
        if step != "approach_elk":
            await session.send("\r\nMora keeps you outside the elk's space until Raska's tracking lesson actually sends you here.\r\n")
            return True
        session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "inspect_harness")
        await session.send(
            "\r\nYou approach on a shallow angle, stop before the elk has to move away, and let it look and scent you. One ear turns toward you; the body stays loose. CHECK HARNESS before asking for closer contact.\r\n"
        )
        return True

    if room == TROLL_TETHER_YARD_KEY and normalized in {"check harness", "examine harness", "inspect harness", "check tack", "examine tack"}:
        if step != "inspect_harness":
            await session.send("\r\nLet the elk accept your presence first. APPROACH ELK without crowding it.\r\n")
            return True
        session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "calm_elk")
        await session.send(
            "\r\nThe chest strap lies flat, the traces are untwisted, and nothing rubs behind the foreleg. There is no hidden tack problem to fix. The exercise is simply whether you can make yourself easy for the animal to accept. CALM ELK.\r\n"
        )
        return True

    if room == TROLL_TETHER_YARD_KEY and normalized in {"calm elk", "soothe elk", "calm pack elk", "soothe pack elk", "handle elk"}:
        if step != "calm_elk":
            await session.send("\r\nCalming an animal starts before touching it. Approach and inspect first.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_ANIMAL_HANDLING_FLAG)
        session.database.advance_quest(session.character.id, TROLL_TRACK_QUEST.key, "return_raska")
        await session.send(
            "\r\nYou soften your posture, breathe slowly, and wait. When the elk chooses to stretch its nose toward your hand, you rub the base of its jaw once and stop before tolerance becomes pressure. Mora gives a small approving grunt.\r\n"
            "Return to Frostroot Camp and TALK RASKA.\r\n"
        )
        return True

    return False


async def _handle_outsider_quest(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    quest = _quest(session, TROLL_OUTSIDER_QUEST)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    if session.character.current_room != TROLL_WINDSCAR_SHELF_KEY:
        return False

    if normalized in {"pull sledge", "drag sledge", "lift sledge", "pull sled", "drag sled", "use strength", "heave sledge"}:
        await session.send(
            "\r\nYou put a hand to the sledge, but the moment the load twists, the ram braces and the pinched strap bites tighter. More force would make every part of the problem worse. You stop before anyone is hurt. EXAMINE PACK RAM.\r\n"
        )
        return True

    if normalized in {"examine pack ram", "look pack ram", "examine ram", "look ram", "inspect ram", "check ram"}:
        if step == "inspect_problem":
            session.database.grant_flag(session.character.id, TROLL_OUTSIDER_PROBLEM_READ_FLAG)
            session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "calm_ram")
        await session.send(
            "\r\nThe ram is not stubborn. One rear strap has rolled into a hard narrow twist against its flank, and the right-heavy load makes that strap bite every time the sledge yaws. The animal needs to stop fighting the pressure before you can safely reach the buckle. CALM RAM.\r\n"
        )
        return True

    if normalized in {"calm ram", "soothe ram", "calm pack ram", "soothe pack ram"}:
        if step != "calm_ram":
            await session.send("\r\nFirst identify why the ram is distressed. EXAMINE PACK RAM.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_OUTSIDER_RAM_CALMED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "free_harness")
        await session.send(
            "\r\nYou step out of the ram's forward line, lower your hands, and wait for the breathing to slow. When the ears come halfway forward again, you touch the shoulder before reaching toward the tack. LOOSEN HARNESS.\r\n"
        )
        return True

    if normalized in {"loosen harness", "free harness", "fix harness", "untwist strap", "loosen strap", "fix strap"}:
        if step != "free_harness":
            await session.send("\r\nThe ram is too tense to reach under safely. Calm the animal before correcting the strap.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_OUTSIDER_HARNESS_FREED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "balance_load")
        await session.send(
            "\r\nYou take the weight off the rear trace, flatten the rolled strap, and refasten it with room for the ram's flank to move. The animal shifts once and no longer flinches. The sledge is still badly balanced. SHIFT LOAD.\r\n"
        )
        return True

    if normalized in {"shift load", "balance load", "move crates", "redistribute load", "center load", "repack sledge"}:
        if step != "balance_load":
            await session.send("\r\nFix the animal's painful harness before moving heavy freight around its shafts.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_OUTSIDER_LOAD_BALANCED_FLAG)
        session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "read_route")
        await session.send(
            "\r\nYou move the two heaviest crates toward the centerline and retension the lashings. The sledge settles square behind the ram instead of dragging right. The remaining question is where to move it. READ SNOW.\r\n"
        )
        return True

    if normalized in {"read snow", "examine snow", "look snow", "read route", "examine route", "find route", "check snow"}:
        if step != "read_route":
            await session.send("\r\nThe route matters, but not until the ram and load can move without hurting each other.\r\n")
            return True
        session.database.grant_flag(session.character.id, TROLL_OUTSIDER_ROUTE_READ_FLAG)
        session.database.advance_quest(session.character.id, TROLL_OUTSIDER_QUEST.key, "return_outsider")
        await session.send(
            "\r\nThe shortest line crosses soft drift. Several paces upslope, wind has shaved the snow down to a firm blue-white crust. Old runner polish confirms freight already uses that shoulder when conditions are like this. You point out the harder arc to Brannik. TALK BRANNIK.\r\n"
        )
        return True

    return False


async def _show_survival_record(session) -> None:
    assert session.character is not None
    flags = session.database.list_flags(session.character.id)
    await session.send("\r\n--- Frostroot Survival Apprenticeship ---\r\n")
    checks = (
        ("Wind reading", TROLL_WIND_READ_FLAG),
        ("Shelter construction", TROLL_WINDBREAK_FLAG),
        ("Fire preparation", TROLL_FIRE_LIT_FLAG),
        ("Regeneration understood", TROLL_REGEN_LEARNED_FLAG),
        ("Tracking sign", TROLL_TRACKS_READ_FLAG),
        ("Hunting judgment", TROLL_QUARRY_JUDGMENT_FLAG),
        ("Animal handling", TROLL_ANIMAL_HANDLING_FLAG),
        ("Outsider freight problem", TROLL_OUTSIDER_COMPLETE_FLAG),
    )
    for label, flag in checks:
        await session.send(f"{label}: {'LEARNED' if flag in flags else 'pending'}\r\n")
    for definition in (TROLL_COLD_QUEST, TROLL_TRACK_QUEST, TROLL_OUTSIDER_QUEST):
        quest = _quest(session, definition)
        if quest and quest.get("status") == "active":
            objective = definition.objective_for_step(quest.get("current_step"))
            if objective:
                await session.send(f"Current lesson: {definition.name} - {objective}\r\n")
            break
    await session.send("Frostroot teaches practical competence. These marks are lessons completed, not faction rank or proof of toughness.\r\n")


def install_troll_runtime(player_session_class, world_service) -> None:
    install_troll_content(world_service)
    if getattr(player_session_class, "_troll_start_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "troll":
            _initialize_or_reconcile_troll(self)
        await previous_enter_character(self)
        if self.character is not None and self.character.race == "troll":
            _initialize_or_reconcile_troll(self)
            cold = _quest(self, TROLL_COLD_QUEST)
            track = _quest(self, TROLL_TRACK_QUEST)
            outsider = _quest(self, TROLL_OUTSIDER_QUEST)
            active = next((pair for pair in ((TROLL_COLD_QUEST, cold), (TROLL_TRACK_QUEST, track), (TROLL_OUTSIDER_QUEST, outsider)) if pair[1] and pair[1].get("status") == "active"), None)
            if active:
                definition, state = active
                await self.send(f"\r\nTroll starter lesson: {definition.name}.\r\n")
                objective = definition.objective_for_step(state.get("current_step"))
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")
                await self.send("Use SURVIVAL at any time to review your Frostroot apprenticeship.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "troll":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"survival", "survival record", "apprenticeship", "lessons", "frostroot"}:
            await _show_survival_record(self)
            return

        if await _handle_cold_quest(self, normalized):
            return
        if await _handle_track_quest(self, normalized):
            return
        if await _handle_outsider_quest(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == TROLL_START_ROOM_KEY and _matches(target, "raska", "hunter", "hunter raska", "raska greybark", "mentor"):
                if await _talk_raska(self):
                    return
            if self.character.current_room == TROLL_TETHER_YARD_KEY and _matches(target, "mora", "handler", "mora elkhand", "elkhand"):
                if await _talk_mora(self):
                    return
            if self.character.current_room == TROLL_WINDSCAR_SHELF_KEY and _matches(target, "brannik", "courier", "dwarf", "dwarven courier", "brannik slateboot", "slateboot"):
                if await _talk_brannik(self):
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

        if normalized in {"help", "?"}:
            await self.send(
                "Troll starter: TALK RASKA and use SURVIVAL to review the apprenticeship. Authored survival verbs include EXAMINE WIND, GATHER DEADFALL, BUILD WINDBREAK, LAY/LIGHT FIRE, ENDURE COLD, REST BY FIRE, TRACK WHITEHORN, OBSERVE/LEAVE DOE, APPROACH/CHECK/CALM ELK, and the Windscar freight interactions.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._troll_start_runtime_installed = True
