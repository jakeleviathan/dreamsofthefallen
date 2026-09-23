"""The Brassgut cast: existing quest contacts with real routines and shared memory.

The static NPC records remain canonical for quests, trade and name audits. Each
mobile definition uses the SAME key as its static counterpart, so these are not
additional people. Presentation and the outer TALK layer follow the mobile
position; scripted market conversations keep their original quest handlers.
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field

import mud.npcs as mobile_registry
from mud.astralis_time import ASTRALIS_CLOCK
from mud.goblin_clans import HADRIK_COILPRESS, JEX_MIREHOOK
from mud.goblin_rattlefen_opening import MARA_VALE
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY as MARKET,
    GOBLIN_FLOODGATE_WALK_KEY as FLOODGATE,
    GOBLIN_LEDGER_HALL_KEY as LEDGER,
    GOBLIN_PATCHWORK_PLAZA_KEY as PLAZA,
    GOBLIN_REGION_KEY,
    GOBLIN_SORTING_SPINE_KEY as SORTING,
    GOBLIN_TINKER_ROW_KEY as TINKER,
    RUSKLE_COIL,
)
from mud.npc_conversation import _delegate_prompt
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcDefinition, MobileNpcManager, RoutineStop
from mud.waymeet_living_npcs import phase_at

# Keep all four on the existing, bidirectional city graph. Jex's scouting
# reaches the floodgate rather than sending a noncombatant into hostile mire.
CITY_ROOMS = (MARKET, PLAZA, SORTING, TINKER, LEDGER, FLOODGATE)
CHATTER_ROOMS = frozenset(CITY_ROOMS)
STORM = ("storm", "thunderstorm", "snow", "duststorm")
WET = frozenset(("rain", *STORM))


def _resident(static, description: str, aliases: tuple[str, ...],
              schedule: tuple[RoutineStop, ...], shelter: str) -> MobileNpcDefinition:
    return MobileNpcDefinition(
        key=static.key,
        name=static.name,
        short_description=description,
        spawn_room_key=MARKET,
        allowed_room_keys=CITY_ROOMS,
        behavior=BEHAVIOR_ROUTINE,
        move_chance_per_tick=1.0,
        aliases=aliases,
        routine_schedule=schedule,
        weather_shelter_room_key=shelter,
        shelter_weathers=WET,
    )


RUSKLE = _resident(
    RUSKLE_COIL,
    "a salvage broker pricing oddments while keeping one eye on the claim board",
    ("ruskle", "coil", "goblin ruskle coil", "broker", "salvage broker"),
    (RoutineStop(0, MARKET), RoutineStop(7, MARKET),
     RoutineStop(10, SORTING), RoutineStop(12, MARKET),
     RoutineStop(19, PLAZA), RoutineStop(21, MARKET)),
    MARKET,
)
JEX = _resident(
    JEX_MIREHOOK,
    "a mud-booted route foreman checking hook-marked supply tags",
    ("jex", "mirehook", "route foreman"),
    (RoutineStop(0, PLAZA), RoutineStop(5, FLOODGATE),
     RoutineStop(8, MARKET), RoutineStop(12, SORTING),
     RoutineStop(14, MARKET), RoutineStop(19, PLAZA)),
    MARKET,
)
HADRIK = _resident(
    HADRIK_COILPRESS,
    "a Dwarven trade factor measuring freight loads against a folding brass rule",
    ("hadrik", "coilpress", "dwarf", "dwarven trader", "trade factor"),
    (RoutineStop(0, LEDGER), RoutineStop(7, MARKET),
     RoutineStop(11, TINKER), RoutineStop(13, MARKET),
     RoutineStop(19, LEDGER), RoutineStop(22, MARKET)),
    LEDGER,
)
TRESSA = _resident(
    MARA_VALE,
    "a Human antiquities buyer carefully inspecting Earth-marked curios",
    ("tressa", "vale", "mara", "mara vale", "human factor"),
    (RoutineStop(0, LEDGER), RoutineStop(8, MARKET),
     RoutineStop(12, PLAZA), RoutineStop(13, MARKET),
     RoutineStop(18, LEDGER), RoutineStop(20, MARKET),
     RoutineStop(23, LEDGER)),
    LEDGER,
)
BRASSGUT_LIVING_NPCS = (RUSKLE, JEX, HADRIK, TRESSA)
BRASSGUT_KEYS = frozenset(npc.key for npc in BRASSGUT_LIVING_NPCS)
BY_KEY = {npc.key: npc for npc in BRASSGUT_LIVING_NPCS}


def register_brassgut_living_npcs() -> None:
    """Register after legacy quest contacts; repeated imports are harmless."""
    additions = []
    for npc in BRASSGUT_LIVING_NPCS:
        existing = mobile_registry.MOBILE_NPCS_BY_KEY.get(npc.key)
        if existing is not None and existing != npc:
            raise ValueError("Conflicting Brassgut resident: " + npc.key)
        if existing is None:
            additions.append(npc)
        mobile_registry.MOBILE_NPCS_BY_KEY[npc.key] = npc
    if additions:
        mobile_registry.MOBILE_NPC_DEFINITIONS += tuple(additions)


register_brassgut_living_npcs()


def static_contact_visible(manager: MobileNpcManager | None, key: str, room: str) -> bool:
    """Suppress a legacy market placeholder when its real actor is elsewhere.

    Static-only and standalone test worlds still display the original contact.
    """
    if key not in BRASSGUT_KEYS or manager is None:
        return True
    state = manager.states.get(key)
    return state is None or (state.active and state.current_room_key == room)


def residents_here(manager: MobileNpcManager | None, room: str) -> tuple[MobileNpcDefinition, ...]:
    if manager is None or room not in CHATTER_ROOMS:
        return ()
    return tuple(
        state.definition for state in manager.npcs_in_room(room)
        if state.definition.key in BRASSGUT_KEYS
    )


# The first encounter and next-day aftermath are separate authored exchanges.
# The SQLite journal records which one was heard, including after a restart.
@dataclass(frozen=True, slots=True)
class RelationshipScene:
    first: tuple[str, str]
    aftermath: tuple[str, str]
    ongoing: tuple[str, str]
    starting_rapport: int


def _pair(first: MobileNpcDefinition, second: MobileNpcDefinition) -> str:
    return "|".join(sorted((first.key, second.key)))


RELATIONSHIPS = {
    _pair(RUSKLE, JEX): RelationshipScene(
        ("Ruskle Coil taps a claim tag. 'You cannot sell the same useful hinge to three crews, Jex.'",
         "Jex Mirehook snorts. 'Then tell your buyers to stop calling dibs before my crews haul it in.'"),
        ("Jex Mirehook says, 'My people marked the next load before sunrise, like you asked yesterday.'",
         "Ruskle Coil inspects the marks. 'And I told my buyers whose hooks are on it. We both remembered.'"),
        ("Ruskle and Jex compare fresh salvage tags in terse but practiced silence.",
         "Jex finally nods. 'No double claims today. Keep it that way.'"),
        -1,
    ),
    _pair(RUSKLE, HADRIK): RelationshipScene(
        ("Hadrik Coilpress says, 'This freight price assumes all your salvage is sound.'",
         "Ruskle Coil replies, 'Your offer assumes none of it is. Shall we try counting the actual bolts?'"),
        ("Ruskle spreads yesterday's sorted bolts across a cloth. 'Count them yourself this time.'",
         "Hadrik checks the measure. 'I brought a better offer. You brought better evidence.'"),
        ("Hadrik checks Ruskle's weights; Ruskle checks Hadrik's figures. Neither looks offended.",
         "The two mark the same total on separate scraps of paper."),
        -1,
    ),
    _pair(RUSKLE, TRESSA): RelationshipScene(
        ("Tressa Vale cradles a corroded Earth token. 'The lettering is worth more to me than the metal.'",
         "Ruskle Coil answers, 'Then stop paying scrap rates for things you call priceless.'"),
        ("Tressa produces the token they argued over yesterday. 'I've written down its marks.'",
         "Ruskle smiles. 'Good. Now I can price the next one without pretending it is only brass.'"),
        ("Ruskle sets aside a stamped fragment instead of throwing it in a melt basket.",
         "Tressa notices and quietly adds it to her notebook."),
        0,
    ),
    _pair(JEX, HADRIK): RelationshipScene(
        ("Jex Mirehook says, 'Your freight carts tore two planks from our highwater path.'",
         "Hadrik Coilpress answers, 'Show me the damage. My drivers can carry replacement iron.'"),
        ("Hadrik brings Jex the replacement fasteners he promised after yesterday's argument.",
         "Jex counts them. 'The route crew will remember who actually showed up.'"),
        ("Jex lays out a route map while Hadrik calculates which carts can cross safely.",
         "For once the argument is about the same road, not who ought to pay for it."),
        0,
    ),
    _pair(JEX, TRESSA): RelationshipScene(
        ("Tressa Vale asks Jex whether any of his crews found marked Earth glass in the mire.",
         "Jex says, 'I can ask, but my people will not wade into a sinkhole for your nostalgia.'"),
        ("Jex tells Tressa, 'I put a notice on the safe-route board, like we discussed.'",
         "Tressa replies, 'That is all I needed. Nobody should risk a life for a souvenir.'"),
        ("Tressa shows Jex a map of safe salvage sites rather than offering another bounty.",
         "Jex approves the marked approaches with a muddy thumb."),
        1,
    ),
    _pair(HADRIK, TRESSA): RelationshipScene(
        ("Hadrik studies an old Earth fitting Tressa has laid beside a Dwarven hinge.",
         "Tressa says, 'Different countries. Same urge to build something that lasts.'"),
        ("Tressa shows Hadrik the sketches she made after their talk yesterday.",
         "Hadrik says, 'The fitting would fail our load test. The idea behind it would not.'"),
        ("Hadrik and Tressa compare two objects made centuries and worlds apart.",
         "Neither tries to put a price on the conversation."),
        1,
    ),
}


class BrassgutMemoryStore:
    """Persistent world relationship events and per-character conversation memory."""

    def __init__(self, database):
        self.database = database
        with database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS brassgut_relationships (
                    pair_key TEXT PRIMARY KEY,
                    first_day INTEGER NOT NULL,
                    last_day INTEGER NOT NULL,
                    encounters INTEGER NOT NULL DEFAULT 1,
                    rapport INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS brassgut_player_memory (
                    character_id INTEGER NOT NULL,
                    npc_key TEXT NOT NULL,
                    last_day INTEGER NOT NULL,
                    encounters INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (character_id, npc_key),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );
            """)

    def encounter(self, pair_key: str, day: int, rapport: int) -> str:
        """First meeting, later-day fallout, or ongoing same-day business."""
        with self.database.connect() as db:
            row = db.execute(
                "SELECT last_day FROM brassgut_relationships WHERE pair_key = ?",
                (pair_key,),
            ).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO brassgut_relationships (pair_key, first_day, last_day, rapport) VALUES (?, ?, ?, ?)",
                    (pair_key, day, day, rapport),
                )
                return "first"
            if day > row["last_day"]:
                db.execute(
                    "UPDATE brassgut_relationships SET last_day = ?, encounters = encounters + 1, "
                    "rapport = min(3, rapport + 1) WHERE pair_key = ?",
                    (day, pair_key),
                )
                return "aftermath"
            return "ongoing"

    def remember_player(self, character_id: int, npc_key: str, day: int) -> bool:
        """Returns True on the first conversation of a *later* world day."""
        with self.database.connect() as db:
            row = db.execute(
                "SELECT last_day FROM brassgut_player_memory WHERE character_id = ? AND npc_key = ?",
                (character_id, npc_key),
            ).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO brassgut_player_memory (character_id, npc_key, last_day) VALUES (?, ?, ?)",
                    (character_id, npc_key, day),
                )
                return False
            if day > row["last_day"]:
                db.execute(
                    "UPDATE brassgut_player_memory SET last_day = ?, encounters = encounters + 1 "
                    "WHERE character_id = ? AND npc_key = ?",
                    (day, character_id, npc_key),
                )
                return True
            return False


PERSONAL_RECOGNITION = {
    RUSKLE.key: "Back again, {name}? I kept your last figures. Tell me what changed.",
    JEX.key: "I remember you, {name}. Any change on those routes since we last talked?",
    HADRIK.key: "Good to see you again, {name}. I have not forgotten our previous measurements.",
    TRESSA.key: "Welcome back, {name}. I have been thinking about our last conversation.",
}
PHASE_LINES = {
    RUSKLE.key: {
        "dawn": "First claim comes before the first sale. Everything after is an argument.",
        "day": "Good salvage takes three people: one to find it, one to recognize it, and one to argue over the price.",
        "dusk": "I close the tally when the last marked cart is back, not when the lamps come on.",
        "night": "The market quiets down. My price book does not.",
    },
    JEX.key: {
        "dawn": "I inspect the floodgate before my crews head out. A bad piling announces itself early.",
        "day": "If the sorting crews marked it properly, I will know whose load went where.",
        "dusk": "The last thing I do is count my people back in.",
        "night": "A route is not safe just because you walked it yesterday.",
    },
    HADRIK.key: {
        "dawn": "Before I buy a single load, I check the roads and the scales.",
        "day": "A useful measurement is worth more than a confident guess.",
        "dusk": "Freight paid for is freight I can finally stop worrying about.",
        "night": "I send my tallies home at night. The city changes them again by dawn.",
    },
    TRESSA.key: {
        "dawn": "The morning light is good for reading the marks on old metal.",
        "day": "These fragments are not worthless. They are only worth something different to me.",
        "dusk": "I try to finish my notes before the lantern smoke makes the lettering vanish.",
        "night": "An old name from Earth is still a name, even if no one here remembers its bearer.",
    },
}
WEATHER_LINES = {
    RUSKLE.key: "Rain means half the market is bargaining over dry canvas instead of metal.",
    JEX.key: "The flooded route changes every time the water rises. Tell the crews before they learn the hard way.",
    HADRIK.key: "Wet roads make my freight estimates less certain and my drivers much louder.",
    TRESSA.key: "I packed the Earth fragments beneath waxed cloth. I am not losing another inscription to rain.",
}
SOLO_LINES = {
    RUSKLE.key: (
        "Ruskle Coil weighs a bent hinge, then records its maker's mark before naming a price.",
        "Ruskle Coil pauses mid-haggle to check an old claim against a new one.",
    ),
    JEX.key: (
        "Jex Mirehook counts the route crews returning across the floodgate.",
        "Jex Mirehook scratches a safe approach onto the public salvage board.",
    ),
    HADRIK.key: (
        "Hadrik Coilpress checks three freight weights and quietly rejects the fourth.",
        "Hadrik Coilpress fits a damaged brass rule back into its leather case.",
    ),
    TRESSA.key: (
        "Tressa Vale turns a weathered relic toward the light and carefully copies the surviving letters.",
        "Tressa Vale wraps a stamped fragment in clean cloth instead of dropping it in the scrap basket.",
    ),
}


def chatter_lines(manager: MobileNpcManager, room_key: str, day: int, hour: int,
                  weather: str, *, memory: BrassgutMemoryStore | None = None,
                  rng: random.Random | None = None) -> tuple[str, ...]:
    """Generate only dialogue whose participants really share the room."""
    present = residents_here(manager, room_key)
    if not present:
        return ()
    rng = rng or random.Random()
    pairs = [
        (_pair(a, b), RELATIONSHIPS[_pair(a, b)])
        for i, a in enumerate(present) for b in present[i + 1:]
        if _pair(a, b) in RELATIONSHIPS
    ]
    if pairs and rng.random() < 0.70:
        key, scene = rng.choice(pairs)
        stage = memory.encounter(key, day, scene.starting_rapport) if memory else "first"
        return getattr(scene, stage)
    actor = rng.choice(present)
    if weather.lower() in WET and rng.random() < 0.65:
        return (actor.name + " remarks, '" + WEATHER_LINES[actor.key] + "'",)
    return (rng.choice(SOLO_LINES[actor.key]),)


@dataclass(slots=True)
class BrassgutChatterDirector:
    memory: BrassgutMemoryStore | None = None
    cooldown_seconds: float = 120.0
    last_spoken: dict[str, float] = field(default_factory=dict)

    def due_lines(self, manager: MobileNpcManager, room: str, day: int, hour: int,
                  weather: str, *, now: float,
                  rng: random.Random | None = None) -> tuple[str, ...]:
        if now - self.last_spoken.get(room, float("-inf")) < self.cooldown_seconds:
            return ()
        lines = chatter_lines(manager, room, day, hour, weather, memory=self.memory, rng=rng)
        if lines:
            self.last_spoken[room] = now
        return lines


async def run_brassgut_chatter(
    manager: MobileNpcManager,
    database,
    player_rooms_provider: Callable[[], Iterable[str]],
    broadcast: Callable[[str, str], Awaitable[None]],
    weather_provider: Callable[[str], str],
    *,
    interval_seconds: float = 30.0,
) -> None:
    """One throttled shared task, producing dialogue only in occupied rooms."""
    loop = asyncio.get_running_loop()
    rng = random.Random()
    director = BrassgutChatterDirector(memory=BrassgutMemoryStore(database))
    while True:
        await asyncio.sleep(interval_seconds)
        moment = ASTRALIS_CLOCK.now()
        weather = weather_provider(GOBLIN_REGION_KEY)
        for room in sorted(set(player_rooms_provider()) & CHATTER_ROOMS):
            if rng.random() > 0.72:
                continue
            lines = director.due_lines(
                manager, room, moment.day_number, moment.hour, weather,
                now=loop.time(), rng=rng,
            )
            if lines:
                await broadcast(room, "\r\n".join(lines))


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def resolve_brassgut_talk(manager: MobileNpcManager | None, room: str, target: str
                          ) -> tuple[MobileNpcDefinition | None, bool]:
    """Resolve only this cast, including an absent market actor's known name."""
    query = _normalize(target)
    if not query or (room not in CHATTER_ROOMS and room != MARKET):
        return None, False
    if query.startswith("to "):
        query = query[3:]
    candidates = []
    for npc in BRASSGUT_LIVING_NPCS:
        aliases = {
            _normalize(npc.name), *(_normalize(alias) for alias in npc.aliases),
            *(_normalize(word) for word in npc.name.split()),
        }
        if query in aliases:
            candidates.append(npc)
    if len(candidates) != 1:
        return None, len(candidates) > 1
    npc = candidates[0]
    # When off duty, only the market counter can tell you who is missing.
    if room != MARKET and npc not in residents_here(manager, room):
        return None, False
    return npc, False


def talk_lines(npc: MobileNpcDefinition, hour: int, weather: str) -> tuple[str, ...]:
    lines = [npc.name + " says, '" + PHASE_LINES[npc.key][phase_at(hour)] + "'"]
    if weather.lower() in WET:
        lines.append(npc.name + " adds, '" + WEATHER_LINES[npc.key] + "'")
    return tuple(lines)


# These location-dependent actions were originally written with permanently
# stationary NPCs. Do not silently let an absent person buy, settle or accept.
MARKET_ACTION_OWNER = {
    "report mirehook": JEX.key, "post return route": JEX.key,
    "post route": JEX.key, "mark route public": JEX.key,
    "deliver report": HADRIK.key, "deliver market slip": HADRIK.key,
    "deliver slip": HADRIK.key, "give market slip": HADRIK.key,
    "sell token": TRESSA.key, "keep token": TRESSA.key,
}


def install_brassgut_living_talk_runtime(player_session_class) -> None:
    """Keep market quest TALK primary; offer personal chatter everywhere else."""
    if getattr(player_session_class, "_brassgut_living_talk_installed", False):
        return
    previous = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        parts = command.strip().split(maxsplit=1)
        verb = parts[0].casefold() if parts else ""
        room = character.current_room or ""
        normalized = _normalize(command)
        manager = getattr(self, "mobile_npcs", None)

        if room == MARKET and normalized in MARKET_ACTION_OWNER:
            key = MARKET_ACTION_OWNER[normalized]
            if not static_contact_visible(manager, key, room):
                await self.send("\r\n" + BY_KEY[key].name
                                + " is out on their rounds. Try again when they return to the market.\r\n")
                return

        if verb == "talk" and len(parts) == 2:
            npc, ambiguous = resolve_brassgut_talk(manager, room, parts[1])
            if ambiguous:
                await self.send("\r\nPlease use the person's full name.\r\n")
                return
            if npc is not None:
                present = static_contact_visible(manager, npc.key, room)
                if not present:
                    await self.send("\r\n" + npc.name
                                    + " is out on their rounds. Ask again when they return.\r\n")
                    return
                moment = ASTRALIS_CLOCK.now()
                memory = BrassgutMemoryStore(self.database)
                returned = memory.remember_player(character.id, npc.key, moment.day_number)
                if returned:
                    await self.send("\r\n" + npc.name + " says, '"
                                    + PERSONAL_RECOGNITION[npc.key].format(name=character.name)
                                    + "'\r\n")
                if room != MARKET:
                    try:
                        from mud.room_runtime import WORLD
                        weather = WORLD.state.weather_for(GOBLIN_REGION_KEY)
                    except (AttributeError, KeyError):
                        weather = "clear"
                    await self.send("\r\n" + "\r\n".join(talk_lines(npc, moment.hour, weather)) + "\r\n")
                    return
                # The original market handlers still own tutorials, quest
                # progression, item trades and rewards. Do not replace them.
        await _delegate_prompt(self, previous, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._brassgut_living_talk_installed = True
