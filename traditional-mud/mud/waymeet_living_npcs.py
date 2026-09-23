"""Waymeet-only living NPC pilot: real routes, weather choices, and local chatter.

Routine movement uses the existing shared MobileNpcManager. This module owns
only the authored Waymeet cast, ambient dialogue and optional TALK responses.
Quest-giving Marshal Aven Marr remains a static NPC so his quest flow is safe.
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field

import mud.npcs as mobile_registry
from mud.astralis_time import ASTRALIS_CLOCK
from mud.npc_conversation import _delegate_prompt
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcDefinition, MobileNpcManager, RoutineStop
from mud.waymeet_frontier import (
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_TAVERN_KEY,
    WAYMEET_TAVERN_LOFT_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_GREEN_APPROACH_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_MARSH_ROAD_KEY,
    WAYMEET_TAVERN_KEY,
    WAYMEET_TAVERN_LOFT_KEY,
    WAYMEET_WEST_ROAD_KEY,
)

WAYMEET_LIVING_ROOMS = (
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_WEST_ROAD_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_GREEN_APPROACH_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_MARSH_ROAD_KEY,
)
WAYMEET_CHATTER_ROOMS = frozenset(WAYMEET_LIVING_ROOMS)
WAYMEET_WEATHER_REGION = "waymeet_frontier"

EDRIN = MobileNpcDefinition(
    key="waymeet_dispatcher_edrin",
    name="Edrin Tallowmark",
    short_description="a human caravan dispatcher checking road tallies against a folded timetable",
    spawn_room_key=WAYMEET_CROSSROADS_KEY,
    allowed_room_keys=WAYMEET_LIVING_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("edrin", "tallowmark", "dispatcher"),
    routine_schedule=(
        RoutineStop(0, WAYMEET_COMMONHOUSE_KEY),
        RoutineStop(6, WAYMEET_WEST_ROAD_KEY),
        RoutineStop(8, WAYMEET_CROSSROADS_KEY),
        RoutineStop(12, WAYMEET_LANTERN_MARKET_KEY),
        RoutineStop(14, WAYMEET_CROSSROADS_KEY),
        RoutineStop(18, WAYMEET_TAVERN_KEY),
        RoutineStop(21, WAYMEET_COMMONHOUSE_KEY),
    ),
    weather_shelter_room_key=WAYMEET_COMMONHOUSE_KEY,
    shelter_weathers=("storm", "thunderstorm", "snow", "duststorm"),
)

SUVVI = MobileNpcDefinition(
    key="waymeet_runner_suvvi",
    name="Suvvi Rainpenny",
    short_description="a goblin errand runner with an overstuffed dispatch satchel and muddy boots",
    spawn_room_key=WAYMEET_LANTERN_MARKET_KEY,
    allowed_room_keys=WAYMEET_LIVING_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("suvvi", "rainpenny", "runner"),
    routine_schedule=(
        RoutineStop(0, WAYMEET_COMMONHOUSE_KEY),
        RoutineStop(7, WAYMEET_LANTERN_MARKET_KEY),
        RoutineStop(9, WAYMEET_CROSSROADS_KEY),
        RoutineStop(11, WAYMEET_CRAFT_ROW_KEY),
        RoutineStop(14, WAYMEET_CROSSROADS_KEY),
        RoutineStop(17, WAYMEET_LANTERN_MARKET_KEY),
        RoutineStop(19, WAYMEET_TAVERN_KEY),
        RoutineStop(21, WAYMEET_COMMONHOUSE_KEY),
    ),
    weather_shelter_room_key=WAYMEET_LANTERN_MARKET_KEY,
    shelter_weathers=("rain", "storm", "thunderstorm", "snow", "duststorm"),
)

BELREK = MobileNpcDefinition(
    key="waymeet_roadwright_belrek",
    name="Belrek Nailsong",
    short_description="a dwarven roadwright with a belt of mismatched tools and a fresh bridge survey",
    spawn_room_key=WAYMEET_CRAFT_ROW_KEY,
    allowed_room_keys=WAYMEET_LIVING_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("belrek", "nailsong", "roadwright"),
    routine_schedule=(
        RoutineStop(0, WAYMEET_COMMONHOUSE_KEY),
        RoutineStop(6, WAYMEET_CRAFT_ROW_KEY),
        RoutineStop(9, WAYMEET_CROSSROADS_KEY),
        RoutineStop(11, WAYMEET_CRAFT_ROW_KEY),
        RoutineStop(15, WAYMEET_CROSSROADS_KEY),
        RoutineStop(18, WAYMEET_TAVERN_KEY),
        RoutineStop(22, WAYMEET_COMMONHOUSE_KEY),
    ),
    weather_shelter_room_key=WAYMEET_CRAFT_ROW_KEY,
    shelter_weathers=("storm", "thunderstorm", "snow", "duststorm"),
)

LESSA = MobileNpcDefinition(
    key="waymeet_trail_courier_lessa",
    name="Lessa Siltward",
    short_description="a forest elf trail courier carrying sealed letters beneath a waxed green cloak",
    spawn_room_key=WAYMEET_GREEN_APPROACH_KEY,
    allowed_room_keys=WAYMEET_LIVING_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("lessa", "siltward", "trail courier"),
    routine_schedule=(
        RoutineStop(0, WAYMEET_COMMONHOUSE_KEY),
        RoutineStop(5, WAYMEET_GREEN_APPROACH_KEY),
        RoutineStop(10, WAYMEET_CROSSROADS_KEY),
        RoutineStop(13, WAYMEET_LANTERN_MARKET_KEY),
        RoutineStop(16, WAYMEET_GREEN_APPROACH_KEY),
        RoutineStop(19, WAYMEET_TAVERN_KEY),
        RoutineStop(21, WAYMEET_COMMONHOUSE_KEY),
    ),
    weather_shelter_room_key=WAYMEET_COMMONHOUSE_KEY,
    shelter_weathers=("storm", "thunderstorm", "snow", "duststorm"),
)

MAREN = MobileNpcDefinition(
    key="waymeet_caravaner_maren",
    name="Maren Copperwake",
    short_description="a Troll caravaner with a brass route token, a rain-creased map and a fondness for a good story",
    spawn_room_key=WAYMEET_TAVERN_LOFT_KEY,
    allowed_room_keys=WAYMEET_LIVING_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("maren", "copperwake", "caravaner"),
    routine_schedule=(
        RoutineStop(0, WAYMEET_TAVERN_LOFT_KEY),
        RoutineStop(6, WAYMEET_WEST_ROAD_KEY),
        RoutineStop(9, WAYMEET_CROSSROADS_KEY),
        RoutineStop(12, WAYMEET_LANTERN_MARKET_KEY),
        RoutineStop(18, WAYMEET_TAVERN_KEY),
        RoutineStop(22, WAYMEET_TAVERN_LOFT_KEY),
    ),
    weather_shelter_room_key=WAYMEET_TAVERN_KEY,
    shelter_weathers=("storm", "thunderstorm", "snow", "duststorm"),
)

WAYMEET_LIVING_NPCS = (EDRIN, SUVVI, BELREK, LESSA, MAREN)
_WAYMEET_KEYS = frozenset(npc.key for npc in WAYMEET_LIVING_NPCS)


def register_waymeet_living_npcs() -> None:
    """Expose this cast to the ordinary manager and production name audit once."""
    additions = []
    for definition in WAYMEET_LIVING_NPCS:
        existing = mobile_registry.MOBILE_NPCS_BY_KEY.get(definition.key)
        if existing is not None and existing != definition:
            raise ValueError("Conflicting Waymeet mobile NPC: " + definition.key)
        if existing is None:
            additions.append(definition)
        mobile_registry.MOBILE_NPCS_BY_KEY[definition.key] = definition
    if additions:
        mobile_registry.MOBILE_NPC_DEFINITIONS += tuple(additions)


# This import occurs during normal server assembly, before name auditing.
register_waymeet_living_npcs()


TALK_LINES: dict[str, dict[str, str]] = {
    EDRIN.key: {
        "dawn": "First wagons are already late. They always blame the roads, never their own sleeping.",
        "day": "Four approaches, one bridge, and a schedule nobody reads until a cart goes missing.",
        "dusk": "I count every wagon back in. The empty spaces are the numbers that matter.",
        "night": "The night watch has the road tally. I can finally put down this pencil.",
    },
    SUVVI.key: {
        "dawn": "Early messages pay more. Early mornings are a terrible invention.",
        "day": "I can carry three parcels in the time these merchants take to argue over one.",
        "dusk": "If you need a parcel sent, make it quick. My boots are declaring a strike.",
        "night": "The satchel stays beside my bed. A runner who loses the post loses breakfast.",
    },
    BELREK.key: {
        "dawn": "The bridge is quiet enough at sunrise that I can hear the bad planks.",
        "day": "A loose rivet is a warning. A missing rivet is somebody else's emergency.",
        "dusk": "The carts are lighter now. Good time to check what their weight shook loose.",
        "night": "I put the tools away, but I can still hear that western rail rattling.",
    },
    LESSA.key: {
        "dawn": "The southern trail tells you who passed before the road wakes up.",
        "day": "Waymeet letters travel farther than most of their writers ever will.",
        "dusk": "I prefer delivering before dark. Not every road gives the favor back.",
        "night": "Tomorrow's letters are dry beneath my cloak. That is enough for tonight.",
    },
    MAREN.key: {
        "dawn": "First wagon out, last one to breakfast. That's how you stay solvent.",
        "day": "I mark the potholes the same way I mark the good inns: so I can find them again.",
        "dusk": "Fifth Lantern by sundown. If you need a party for Broken Reach, try the long table.",
        "night": "I've a clean bunk upstairs and four roads in my dreams. Life's not bad.",
    },
}
WEATHER_LINES: dict[str, str] = {
    EDRIN.key: "Half my timetable has become a list of bridges the drivers refuse to cross.",
    SUVVI.key: "Wet letters cost me twice the running. I am charging the clouds.",
    BELREK.key: "Rain shows every rotten seam in the bridge. The dangerous ones were already there.",
    LESSA.key: "The wind brings the woodland smell this far, even over wet wagon canvas.",
    MAREN.key: "A driver respects a storm, but a dry hearth buys it more respect.",
}
PAIR_LINES: dict[frozenset[str], tuple[str, str]] = {
    frozenset((EDRIN.key, SUVVI.key)): (
        "Edrin Tallowmark says, 'That message goes to the western wagons, not the northern ones.'",
        "Suvvi Rainpenny pats her satchel. 'Then stop tying both bundles with the same red string.'",
    ),
    frozenset((EDRIN.key, BELREK.key)): (
        "Edrin Tallowmark says, 'How much longer until the west rail is repaired?'",
        "Belrek Nailsong answers, 'As long as it takes to fix it, not as long as your ledger allows.'",
    ),
    frozenset((EDRIN.key, LESSA.key)): (
        "Lessa Siltward passes Edrin a folded trail report. 'The southern path is clear again.'",
        "Edrin Tallowmark crosses a line from his road tally. 'That is one fewer argument by noon.'",
    ),
    frozenset((SUVVI.key, BELREK.key)): (
        "Suvvi Rainpenny says, 'The wagon crews keep asking when the bridge will stop groaning.'",
        "Belrek Nailsong replies, 'When they stop driving four wagons across it at once.'",
    ),
    frozenset((SUVVI.key, LESSA.key)): (
        "Suvvi Rainpenny compares muddy boots with Lessa. 'I took the shorter road.'",
        "Lessa Siltward smiles. 'Then you found the deeper puddle.'",
    ),
    frozenset((BELREK.key, LESSA.key)): (
        "Lessa Siltward says, 'There is a new rut where the south road joins the bridge.'",
        "Belrek Nailsong pulls a stub of chalk from his belt. 'Show me before the next heavy cart finds it.'",
    ),
    frozenset((EDRIN.key, MAREN.key)): (
        "Maren Copperwake asks Edrin, 'How many late wagons before you come inside?'",
        "Edrin Tallowmark taps his ledger. 'One fewer if you stop asking me questions.'",
    ),
    frozenset((SUVVI.key, MAREN.key)): (
        "Suvvi Rainpenny slides a parcel across the long table. 'Didn't you promise this would fit in a pocket?'",
        "Maren Copperwake laughs. 'A Troll pocket, yes.'",
    ),
    frozenset((BELREK.key, MAREN.key)): (
        "Belrek Nailsong lays a bent rivet on the long table. 'Tell me exactly which wheel broke it.'",
        "Maren Copperwake points west. 'The wheel that got us home before the rain.'",
    ),
    frozenset((LESSA.key, MAREN.key)): (
        "Lessa Siltward unfolds a trail map by the hearth. 'The southern way is shorter on foot.'",
        "Maren Copperwake shakes her head. 'I've yet to see you pull a wagon on foot.'",
    ),
}
MARSHAL_LINES = {
    EDRIN.key: (
        "Marshal Aven Marr asks, 'Anything missing from the road tally?'",
        "Edrin Tallowmark replies, 'Only the wagons that have not arrived yet. Those are the ones I watch.'",
    ),
    SUVVI.key: (
        "Marshal Aven Marr calls, 'Keep the notices dry, Suvvi.'",
        "Suvvi Rainpenny grins. 'Then give me a roof over all four roads.'",
    ),
    BELREK.key: (
        "Marshal Aven Marr asks, 'How is the bridge holding?'",
        "Belrek Nailsong says, 'Ask me after people stop testing it with overloaded carts.'",
    ),
    LESSA.key: (
        "Marshal Aven Marr asks, 'Anything unusual on the southern approach?'",
        "Lessa Siltward replies, 'Only the usual things in unusual places. I marked them on your map.'",
    ),
    MAREN.key: (
        "Marshal Aven Marr studies Maren's cargo slips. 'Anything missing from your manifest?'",
        "Maren Copperwake replies, 'Only the dry weather you promised me.'",
    ),
}
SOLO_ACTIONS: dict[str, tuple[str, ...]] = {
    EDRIN.key: (
        "Edrin Tallowmark checks the crossroads marker against a creased caravan schedule.",
        "Edrin Tallowmark calls out a wagon's destination and marks it off his tally.",
    ),
    SUVVI.key: (
        "Suvvi Rainpenny sorts three sealed letters by road, then swaps two of them with a frown.",
        "Suvvi Rainpenny trots past, counting delivery stops on muddy fingers.",
    ),
    BELREK.key: (
        "Belrek Nailsong kneels to listen to a wagon rattle, then makes a note on his bridge survey.",
        "Belrek Nailsong tests the head of a loose road nail with his thumb.",
    ),
    LESSA.key: (
        "Lessa Siltward checks the seals on her letters and studies the route stones.",
        "Lessa Siltward pauses to compare the wind with the road dust on her boots.",
    ),
    MAREN.key: (
        "Maren Copperwake pins an updated route note beside the Fifth Lantern's long table.",
        "Maren Copperwake counts the evening wagons from the doorstep, then settles by the hearth.",
    ),
}
WET_WEATHER = frozenset(("rain", "storm", "thunderstorm", "snow", "duststorm"))


def phase_at(hour: int) -> str:
    if 5 <= hour < 8:
        return "dawn"
    if 8 <= hour < 18:
        return "day"
    if 18 <= hour < 21:
        return "dusk"
    return "night"


def _visible_cast(manager: MobileNpcManager, room_key: str) -> tuple[MobileNpcDefinition, ...]:
    return tuple(
        state.definition
        for state in manager.npcs_in_room(room_key)
        if state.definition.key in _WAYMEET_KEYS
    )


def chatter_lines(
    manager: MobileNpcManager,
    room_key: str,
    hour: int,
    weather: str,
    *,
    rng: random.Random | None = None,
) -> tuple[str, ...]:
    """Only speak for actors physically present; exchanges need both speakers."""
    if room_key not in WAYMEET_CHATTER_ROOMS:
        return ()
    present = _visible_cast(manager, room_key)
    if not present:
        return ()
    rng = rng or random.Random()

    # Rare world-story beats use the same physical-visibility and room cooldown
    # rules as ordinary chatter. They are hints, never an automatic quest marker.
    if room_key == WAYMEET_COMMONHOUSE_KEY and 7 <= hour < 20 and rng.random() < 0.055:
        return (
            "Nimra Dawnskein hums four notes on the Commonhouse steps. "
            "She pauses for a fifth, then goes back to sorting painted pebbles.",
        )
    if room_key == WAYMEET_CROSSROADS_KEY and weather.lower() in WET_WEATHER and rng.random() < 0.055:
        actor = rng.choice(present)
        return (
            actor.name + " pauses by the repaired bridge. 'Someone has put those "
            "little chalk marks back again. Rain never seems to wash the last one away.'",
        )

    if room_key == WAYMEET_TAVERN_KEY and rng.random() < 0.35:
        actor = rng.choice(present)
        return (
            "Orla Hearthglass sets a warm cup beside " + actor.name + ". 'Four roads, one hearth. What news?'",
            actor.name + " settles near the gearwheel fire and begins swapping road stories.",
        )

    if len(present) > 1:
        pairs = [
            PAIR_LINES[frozenset((a.key, b.key))]
            for i, a in enumerate(present)
            for b in present[i + 1 :]
            if frozenset((a.key, b.key)) in PAIR_LINES
        ]
        if pairs:
            return rng.choice(pairs)

    actor = rng.choice(present)
    if room_key == WAYMEET_CROSSROADS_KEY and rng.random() < 0.65:
        return MARSHAL_LINES[actor.key]
    if weather.lower() in WET_WEATHER and rng.random() < 0.60:
        return (actor.name + " remarks, '" + WEATHER_LINES[actor.key] + "'",)
    return (rng.choice(SOLO_ACTIONS[actor.key]),)


@dataclass(slots=True)
class WaymeetChatterDirector:
    """Per-room cooldown prevents idle chatter from flooding the Telnet prompt."""

    cooldown_seconds: float = 100.0
    last_spoken: dict[str, float] = field(default_factory=dict)

    def due_lines(
        self,
        manager: MobileNpcManager,
        room_key: str,
        hour: int,
        weather: str,
        *,
        now: float,
        rng: random.Random | None = None,
    ) -> tuple[str, ...]:
        if now - self.last_spoken.get(room_key, float("-inf")) < self.cooldown_seconds:
            return ()
        lines = chatter_lines(manager, room_key, hour, weather, rng=rng)
        if lines:
            self.last_spoken[room_key] = now
        return lines


async def run_waymeet_chatter(
    manager: MobileNpcManager,
    player_rooms_provider: Callable[[], Iterable[str]],
    broadcast: Callable[[str, str], Awaitable[None]],
    weather_provider: Callable[[str], str],
    *,
    interval_seconds: float = 30.0,
) -> None:
    """A single low-cost shared task, active only where players can hear it."""
    loop = asyncio.get_running_loop()
    rng = random.Random()
    director = WaymeetChatterDirector()
    while True:
        await asyncio.sleep(interval_seconds)
        hour = ASTRALIS_CLOCK.now().hour
        weather = weather_provider(WAYMEET_WEATHER_REGION)
        for room_key in sorted(set(player_rooms_provider()) & WAYMEET_CHATTER_ROOMS):
            if rng.random() > 0.72:
                continue
            lines = director.due_lines(
                manager, room_key, hour, weather, now=loop.time(), rng=rng,
            )
            if lines:
                await broadcast(room_key, "\r\n".join(lines))


def resolve_waymeet_talk(
    manager: MobileNpcManager | None, room_key: str, target: str,
) -> tuple[MobileNpcDefinition | None, tuple[str, ...]]:
    if manager is None or room_key not in WAYMEET_CHATTER_ROOMS:
        return None, ()
    query = " ".join(target.casefold().replace("-", " ").split())
    if not query:
        return None, ()
    matches = []
    for definition in _visible_cast(manager, room_key):
        aliases = {
            definition.name.casefold(),
            definition.name.split()[0].casefold(),
            definition.name.split()[-1].casefold(),
            *(alias.casefold() for alias in definition.aliases),
        }
        if query in aliases:
            matches.append(definition)
    if len(matches) == 1:
        return matches[0], ()
    if len(matches) > 1:
        return None, tuple(sorted(definition.name for definition in matches))
    return None, ()


def talk_lines(definition: MobileNpcDefinition, hour: int, weather: str) -> tuple[str, ...]:
    lines = [definition.name + " says, '" + TALK_LINES[definition.key][phase_at(hour)] + "'"]
    if weather.lower() in WET_WEATHER:
        lines.append(definition.name + " adds, '" + WEATHER_LINES[definition.key] + "'")
    return tuple(lines)


def install_waymeet_living_talk_runtime(player_session_class) -> None:
    """Handle only these visible mobile actors; leave quest TALK to its owners."""
    if getattr(player_session_class, "_waymeet_living_talk_installed", False):
        return
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        parts = command.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].casefold() == "talk":
            target = parts[1].strip()
            if target.casefold().startswith("to "):
                target = target[3:].strip()
            npc, ambiguous = resolve_waymeet_talk(
                getattr(self, "mobile_npcs", None),
                self.character.current_room or "",
                target,
            )
            if ambiguous:
                await self.send(
                    "More than one person matches that name: "
                    + ", ".join(ambiguous) + ".\r\n"
                )
                return
            if npc is not None:
                hour = ASTRALIS_CLOCK.now().hour
                scene_weather = "clear"
                try:
                    from mud.room_runtime import WORLD
                    scene_weather = WORLD.state.weather_for(WAYMEET_WEATHER_REGION)
                except (AttributeError, KeyError):
                    pass
                await self.send("\r\n" + "\r\n".join(talk_lines(npc, hour, scene_weather)) + "\r\n")
                return
        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._waymeet_living_talk_installed = True
