"""Shared inhabited-region NPC layer built on the existing mobile NPC manager.

Waymeet keeps its hand-authored pilot. Every other principal settlement uses
the same clock, legal room graph and weather shelter rules, with unique people
and conversations instead of global random bark tables.
"""
from __future__ import annotations

import asyncio
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Iterable, Mapping

import mud.npcs as mobile_registry
from mud.astralis_time import ASTRALIS_CLOCK
from mud.npc_conversation import _delegate_prompt
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcDefinition, MobileNpcManager, RoutineStop
from mud.world import ROOMS_BY_KEY
from mud.world_rumors import latest_rumors, pending_rumor, mark_rumor_heard

WET_WEATHER = frozenset(("rain", "storm", "thunderstorm", "snow", "duststorm"))
_FORBIDDEN_ROUTE_TAGS = ("dungeon", "boss", "secret", "instance", "finale")


@dataclass(frozen=True, slots=True)
class Resident:
    key: str
    name: str
    job: str
    description: str
    dawn: str
    daytime: str
    dusk: str
    night: str
    weather: str
    action: str


@dataclass(frozen=True, slots=True)
class Neighborhood:
    region: str
    stops: tuple[str, str, str]  # home, work route, secondary errand
    residents: tuple[Resident, Resident]
    exchange: tuple[str, str]


NEIGHBORHOODS: tuple[Neighborhood, ...] = (
    Neighborhood(
        "human_kingdom", ("human_demon_gate", "human_ashen_way", "human_cathedral_square"),
        (
            Resident("human_ledger_runner_ivo", "Ivo Lanternwake", "gate courier",
                "a sharp-eyed human courier checking delivery seals under his dark coat",
                "The gate opens before the merchants wake. Someone has to count the early carts.",
                "If the Ashen Way papers disagree with the gate tally, the papers are usually wrong.",
                "Evening deliveries go first to the cathedral. The rest can wait for tomorrow.",
                "These streets sound different when the last freight wagon has passed.",
                "The ink runs in this rain. I should have kept the waxed ledger.",
                "Ivo Lanternwake checks the seals on his gate dispatches."),
            Resident("human_lamplighter_marella", "Marella Dusksill", "city lamplighter",
                "a human lamplighter carrying a brass pole and a crate of fresh wicks",
                "I start at the gate and finish where the shadows are longest.",
                "There is a broken lamp on Ashen Way every time the night market closes.",
                "Cathedral Square needs its lights before the crowd arrives.",
                "The last lamp is mine. No one else remembers the path down Cinder Lane.",
                "Wind and rain take turns undoing my morning's work.",
                "Marella Dusksill trims a wick and checks the next lamp."),
        ),
        ("Ivo Lanternwake asks, 'Did the cathedral receive the western dispatch?'",
         "Marella Dusksill replies, 'It did. I left a light on for the messenger.'"),
    ),
    Neighborhood(
        "dwarven_mountain_industry", ("dwarf_foundry_concourse", "dwarf_trade_house_arcade", "dwarf_workshop_tier"),
        (
            Resident("dwarf_freight_clerk_odrin", "Odrin Rivetfall", "freight clerk",
                "a dwarven freight clerk with a brass gauge and a soot-smudged slate",
                "The first lift is already carrying ore. They never wait for my breakfast.",
                "The trade houses promised twelve crates. I count eleven.",
                "One loose wheel can stop the night shift. Check them while there is daylight.",
                "I left the freight book beside my boots. That means I am off duty.",
                "Wet rails need double inspection before the upper lift takes a load.",
                "Odrin Rivetfall measures a wagon axle with a brass gauge."),
            Resident("dwarf_toolwright_tessa", "Tessa Sootmeasure", "toolwright",
                "a dwarven toolwright carrying a roll of meticulously labeled repairs",
                "The hammers are cold enough to hear which one is cracked.",
                "The workshop tier wants three new dies and twice as many excuses.",
                "A decent tool comes back for sharpening, not replacement.",
                "I can tell which furnace is still hot without opening my eyes.",
                "A storm over the open freight deck sends everyone indoors asking for repairs.",
                "Tessa Sootmeasure sorts a row of newly sharpened tools."),
        ),
        ("Odrin Rivetfall says, 'The lift wants its new brake before the next shift.'",
         "Tessa Sootmeasure answers, 'Then stop lending the old one to impatient merchants.'"),
    ),
    Neighborhood(
        "great_elf_forest", ("forest_elf_circle_clearing", "forest_elf_greenway", "forest_elf_old_river_path"),
        (
            Resident("forest_pathkeeper_fera", "Fera Mossvale", "pathkeeper",
                "a forest elf pathkeeper brushing fallen branches off the green trail",
                "The morning tracks are clearer before the wagons disturb them.",
                "Every visitor wants the shortest path. The forest does not owe them one.",
                "I leave the western markers where even tired travelers can find them.",
                "The circle sounds peaceful after the last footstep fades.",
                "Heavy rain means checking the low roots before anyone tries to cross.",
                "Fera Mossvale clears a branch away from a narrow path."),
            Resident("forest_seedkeeper_thalen", "Thalen Leafcross", "seedkeeper",
                "a forest elf seedkeeper with woven seed pouches and a bark ledger",
                "Fresh dew tells me which seedlings made it through the night.",
                "The old river path needs shade more than it needs another signpost.",
                "I bring the last seed trays back before the light changes.",
                "Some roots keep working long after the hands that planted them have slept.",
                "Rain is welcome until it carries the loose earth down to the old river.",
                "Thalen Leafcross inspects a seed pouch and closes its woven tie."),
        ),
        ("Fera Mossvale says, 'The western path is wearing thin again.'",
         "Thalen Leafcross answers, 'Then let the roots take back the shortcut.'"),
    ),
    Neighborhood(
        "moon_peaks", ("moon_elf_high_horizon_plaza", "moon_elf_night_market", "moon_elf_skyglass_spire_lobby"),
        (
            Resident("moon_sky_surveyor_caelis", "Caelis Starfold", "sky surveyor",
                "a moon elf surveyor carrying a folded chart of the upper terraces",
                "The dawn light shows cracks the night lamps kindly hide.",
                "Every visiting trader thinks the wind terrace is the shorter route.",
                "The spire needs a fresh wind reading before its evening watch.",
                "There is no quiet like the plaza after the late market goes dark.",
                "Cloud cover makes the sky charts useless, but the railings still need checking.",
                "Caelis Starfold studies the upper walkways through a silver lens."),
            Resident("moon_market_recorder_veyni", "Veyni Glassmere", "market recorder",
                "a moon elf recorder with an ink-stained glove and a delicate glass ledger",
                "The night market leaves more stories than receipts.",
                "I write down both sides of the bargain before either side forgets.",
                "The evening stalls are opening. That is when the real arguments begin.",
                "I never erase a day's entries until I have read them once more.",
                "Mist makes a good excuse for a late delivery and a poor excuse for a missing one.",
                "Veyni Glassmere records a dispute without looking up from her ledger."),
        ),
        ("Caelis Starfold says, 'The wind has shifted above the spire.'",
         "Veyni Glassmere replies, 'So have half the merchants' explanations.'"),
    ),
    Neighborhood(
        "junk_city_and_swamps", ("goblin_clattergate", "goblin_brassgut_market", "goblin_patchwork_plaza"),
        (
            Resident("goblin_scrap_runner_pip", "Pip Rattleknot", "salvage runner",
                "a goblin salvage runner rattling with pockets full of bolts and wire",
                "The first scrap cart always has the good copper. Do not tell the second cart.",
                "This bolt is worth three sparks to the right fool, and I know that fool.",
                "Patchwork Plaza gets the leftovers. Sometimes those are the best pieces.",
                "If a rat steals my inventory tonight, it becomes my business partner.",
                "Rain makes half the salvage rust and the other half mysteriously more valuable.",
                "Pip Rattleknot weighs a bent cog against three mismatched screws."),
            Resident("goblin_patch_vendor_zizzi", "Zizzi Scrapwing", "patch vendor",
                "a goblin stall keeper carrying bright repair patches and a spool of wire",
                "Anyone buying boots before sunrise has a long walk and a short temper.",
                "I mend what the market sells. That makes me everybody's second favorite person.",
                "The last patches go to the floodgate crews, provided they pay me first.",
                "Closing time is when the honest prices come out.",
                "A wet tarp and a dry ledger. That is how you survive this market.",
                "Zizzi Scrapwing holds a patch up to the light, checking for holes."),
        ),
        ("Pip Rattleknot asks, 'What would you pay for a wheel with only one crack?'",
         "Zizzi Scrapwing replies, 'More if you stop telling everyone it has only one.'"),
    ),
    Neighborhood(
        "troll_strongholds", ("troll_frostroot_camp", "troll_ember_hollow", "troll_hidewind_ring"),
        (
            Resident("troll_firekeeper_hroth", "Hroth Flintstep", "firekeeper",
                "a broad-shouldered troll firekeeper carrying a bundle of dry split wood",
                "The fire is lowest just before morning. That is when it matters.",
                "A warm shelter is a promise the whole camp has to keep.",
                "Bring the wet wood inside now or complain about the smoke later.",
                "The embers tell me which wind is coming before the trees do.",
                "Snow gets into every knot. I have learned to tie the fuel twice.",
                "Hroth Flintstep lays dry kindling beside the camp hearth."),
            Resident("troll_trail_reader_sella", "Sella Frostbarrow", "trail reader",
                "a troll trail reader with a battered hide map and a pair of snow shoes",
                "The tracks before dawn belong to animals that did not see us.",
                "Hidewind Ring is safe only if you know where to stand.",
                "The last hunters should already be turning back toward the fire.",
                "I check the trail once after dark, even when there is no reason to worry.",
                "Fresh snow tells the truth and then hides it an hour later.",
                "Sella Frostbarrow studies a trail marker and adjusts a stone cairn."),
        ),
        ("Hroth Flintstep says, 'Did the hunters bring back enough for supper?'",
         "Sella Frostbarrow replies, 'Enough if you stop feeding the travelers first.'"),
    ),
    Neighborhood(
        "desert_necropolis", ("undead_necropolis_concourse", "undead_chisel_market", "undead_freehands_court"),
        (
            Resident("undead_record_bearer_namar", "Namar Quietflint", "record bearer",
                "an undead record bearer carrying sealed tablets in a padded wooden frame",
                "Morning bells still matter even to those who no longer sleep.",
                "Every restored name belongs in the archive before it belongs in a story.",
                "The market ledgers should be sealed before the upper gate closes.",
                "Silence at the concourse is different when nobody expects an order.",
                "A duststorm erases fresh markings. These old tablets can outlast it.",
                "Namar Quietflint brushes the dust from a carved record tablet."),
            Resident("undead_mender_vetha", "Vetha Boneweft", "ceremonial mender",
                "an undead mender with fine thread wound around a narrow bone spindle",
                "The market wakes gently. The damaged garments do not improve by waiting.",
                "A careful repair is a way of telling someone their history matters.",
                "I leave the last work at Freehands Court for its owner to collect.",
                "The seams will still be here tomorrow, but the wearer might not.",
                "Sand gets into every joint and every stitch. I charge for neither.",
                "Vetha Boneweft replaces a torn fastening with a measured stitch."),
        ),
        ("Namar Quietflint says, 'The archive requested a repair that must leave the inscription visible.'",
         "Vetha Boneweft answers, 'Then bring me a frame that is not older than its contents.'"),
    ),
    Neighborhood(
        "sporekin_underways", ("sporekin_lumen_hollow", "sporekin_mycelial_gallery", "sporekin_rootwell_ascent"),
        (
            Resident("sporekin_thread_keeper_moth", "Moth-of-Root", "thread keeper",
                "a sporekin keeper tending the living filaments beneath a bark lantern",
                "The first light of the caps arrives quietly, as all good news should.",
                "The gallery has carried a new pulse from roots farther below.",
                "The ascent is cooling. The smallest growths will need shelter.",
                "We are less alone in stillness than travelers imagine.",
                "Surface rain changes the rhythm of every root that reaches us.",
                "Moth-of-Root brushes loose soil away from a glowing mycelial thread."),
            Resident("sporekin_spore_courier_brindlecap", "Brindlecap-of-Mist", "spore courier",
                "a sporekin courier with a hollow reed satchel full of sealed spores",
                "The younger caps have sent their first message. It smells like spring.",
                "A good message arrives through the network before I do.",
                "The surfaceward thread is dry. I am carrying water toward it.",
                "The gallery remembers footsteps long after their makers leave.",
                "Wet stone makes the long thread sing at a different pitch.",
                "Brindlecap-of-Mist examines a sealed spore packet before continuing."),
        ),
        ("Moth-of-Root murmurs, 'The deep threads have changed their rhythm.'",
         "Brindlecap-of-Mist replies, 'Then I will carry the new pattern up to the rootwell.'"),
    ),
    Neighborhood(
        "veyra_city", ("veyra_grand_crossing", "veyra_brassmarket", "veyra_caravan_court"),
        (
            Resident("veyra_crossing_clerk_rima", "Rima Cartwell", "crossing clerk",
                "a Veyra crossing clerk balancing route tokens against a cart register",
                "The first ferry is already asking which ledger it belongs in.",
                "Three guilds can argue over one damaged axle without agreeing who owns it.",
                "The evening caravans fill the yard faster than we can count them.",
                "The crossing is the quietest when only the river is moving.",
                "River rain means the low quay crews will be late with every cart.",
                "Rima Cartwell checks a crossing chit against her route register."),
            Resident("veyra_bridgehand_joren", "Joren Bridgewick", "bridgehand",
                "a Veyra bridgehand with a rope harness and a fistful of bridge pins",
                "The bridge tells me its troubles before the city tells me mine.",
                "The Brassmarket carts pretend they weigh nothing until a plank complains.",
                "I check every pin before the last heavy wagon heads north.",
                "One day I will hear the river without hearing someone demand a faster crossing.",
                "Rising water means the lower bridge stays closed, whatever the merchants say.",
                "Joren Bridgewick checks a rope knot before pulling another cart through."),
        ),
        ("Rima Cartwell says, 'The western guild insists their wagons have priority.'",
         "Joren Bridgewick replies, 'The river has not signed their paperwork.'"),
    ),
    Neighborhood(
        "sablewater_reach", ("sablewater_north_ferry", "sablewater_reed_farms", "sablewater_eelmarket_dock"),
        (
            Resident("sablewater_ferryman_otta", "Otta Reedline", "ferry hand",
                "a weather-beaten ferry hand counting passengers with a frayed rope",
                "Early ferries carry fewer arguments and more honest cargo.",
                "The farms want passage before the market takes the whole landing.",
                "I tie off at the eel dock before the evening current turns.",
                "You can hear the flood line creeping higher after dark.",
                "Hard rain means no crossing until I can see the opposite post.",
                "Otta Reedline checks the ferry rope for frayed strands."),
            Resident("sablewater_eelmonger_fenrick", "Fenrick Tideglass", "eelmonger",
                "a reed-cloaked eelmonger with a basket of silver fish hooks",
                "The good catch arrives before the gulls become greedy.",
                "Every farm thinks its drainage ditch is the river's most important tributary.",
                "The eel dock smells worse at sunset. That is how you know business was good.",
                "There is always one more hook to clean before tomorrow.",
                "The reeds lie flat in this rain. That makes the channel hard to read.",
                "Fenrick Tideglass untangles a fishing line and checks its hooks."),
        ),
        ("Otta Reedline says, 'The river is already climbing past the lower marker.'",
         "Fenrick Tideglass replies, 'Then I will sell these eels before they swim back home.'"),
    ),
    Neighborhood(
        "greywake_march", ("greywake_three_banner_camp", "greywake_warden_post", "greywake_ledger_cut"),
        (
            Resident("greywake_signalhand_dessa", "Dessa Signalhand", "signal keeper",
                "a road signal keeper folding a patched banner with practiced hands",
                "The first watch can still see the far hill before the haze rolls in.",
                "The warden post wants fresh signal cloth after yesterday's wind.",
                "I send the last road signal before the campfires are lit.",
                "At night I can hear the banner cord tapping against the post.",
                "Bad weather makes one missed signal seem like a broken promise.",
                "Dessa Signalhand tests a signal knot against the next gust."),
            Resident("greywake_camp_factor_torvin", "Torvin Bannerstitch", "camp factor",
                "a watchful camp factor carrying supply receipts in a waxed pouch",
                "Breakfast goes to the night watch first. They earned it.",
                "The ledger cut is missing two wagon seals and somebody's temper.",
                "Anything not counted before sundown becomes tomorrow's argument.",
                "The camp is calmer when all three banners are still flying.",
                "A wet ledger causes more trouble than a wet tent.",
                "Torvin Bannerstitch recounts the camp's dwindling supply tokens."),
        ),
        ("Dessa Signalhand says, 'The west banner is half a length too short.'",
         "Torvin Bannerstitch answers, 'The quartermaster called that a saving.'"),
    ),
    Neighborhood(
        "broken_reach", ("broken_reach_ragged_caravanserai", "broken_reach_old_toll_road", "broken_reach_grinning_camp"),
        (
            Resident("broken_reach_roadguide_marn", "Marn Lowbridge", "road guide",
                "a road guide carrying a patched pack and a map repaired with string",
                "The old toll road looks almost friendly in morning light.",
                "I guide the ones who pay attention to the warnings, not only the signs.",
                "The caravanserai gets crowded when the shadows reach the ditch.",
                "Travelers talk a lot more once the doors are barred.",
                "Rain makes the old stones look freshly laid. Do not trust that.",
                "Marn Lowbridge checks a waymark and tightens the cord on his map."),
            Resident("broken_reach_provisioner_hessi", "Hessi Wayworn", "camp provisioner",
                "a camp provisioner with a kettle, spare bandages and an oversized walking stick",
                "The first walkers get hot broth. The stragglers get questions.",
                "The grinning camp needs dry fuel before it needs another bold story.",
                "I count heads before dark. There is always one who thinks they can outrun it.",
                "At least the caravanserai walls do not pretend to be friendly.",
                "Storms send everyone asking for shelter after ignoring the sky all day.",
                "Hessi Wayworn checks the straps on a stack of travel rations."),
        ),
        ("Marn Lowbridge says, 'Another party took the road after I warned them.'",
         "Hessi Wayworn replies, 'Then put another pot on. Someone will crawl back hungry.'"),
    ),
)
NEIGHBORHOODS_BY_REGION = {entry.region: entry for entry in NEIGHBORHOODS}
RESIDENTS_BY_KEY = {resident.key: (entry, resident)
                    for entry in NEIGHBORHOODS for resident in entry.residents}


def _path(rooms: Mapping, start: str, end: str, region: str) -> tuple[str, ...] | None:
    """Stay in one region and keep ordinary residents out of scripted dungeons."""
    if start not in rooms or end not in rooms:
        return None
    if start == end:
        return (start,)
    queue = deque([(start, (start,))])
    seen = {start}
    while queue:
        here, path = queue.popleft()
        for destination in rooms[here].exits.values():
            if destination in seen or destination not in rooms:
                continue
            room = rooms[destination]
            if room.region_key != region:
                continue
            if destination != end and any(
                token in str(tag).casefold()
                for tag in getattr(room, "tags", ())
                for token in _FORBIDDEN_ROUTE_TAGS
            ):
                continue
            new_path = (*path, destination)
            if destination == end:
                return new_path
            seen.add(destination)
            queue.append((destination, new_path))
    return None


def build_world_residents(rooms: Mapping = ROOMS_BY_KEY) -> tuple[MobileNpcDefinition, ...]:
    """Build valid schedules after production installs all authored regions."""
    definitions = []
    for region in NEIGHBORHOODS:
        home, preferred_work, preferred_errand = region.stops
        if home not in rooms or rooms[home].region_key != region.region:
            raise ValueError("Missing living NPC settlement anchor: " + home)
        destinations = []
        for preferred in (preferred_work, preferred_errand):
            route = _path(rooms, home, preferred, region.region)
            if route is None:
                raise ValueError("Living NPC destination is unreachable: " + home + " -> " + preferred)
            destinations.append((preferred, route))
        allowed = tuple(sorted(set(destinations[0][1]) | set(destinations[1][1])))
        work, errand = destinations[0][0], destinations[1][0]
        for index, resident in enumerate(region.residents):
            primary, secondary = (work, errand) if index == 0 else (errand, work)
            definitions.append(
                MobileNpcDefinition(
                    key=resident.key,
                    name=resident.name,
                    short_description=resident.description,
                    spawn_room_key=home,
                    allowed_room_keys=allowed,
                    behavior=BEHAVIOR_ROUTINE,
                    move_chance_per_tick=1.0,
                    aliases=(resident.name.split()[0], resident.name.split()[-1], resident.job),
                    routine_schedule=(
                        RoutineStop(0, home),
                        RoutineStop(6 + index, primary),
                        RoutineStop(11, secondary),
                        RoutineStop(15, primary),
                        RoutineStop(20, home),
                    ),
                    weather_shelter_room_key=home,
                    shelter_weathers=("storm", "thunderstorm", "snow", "duststorm", "rain"),
                )
            )
    return tuple(definitions)


def register_world_residents(rooms: Mapping = ROOMS_BY_KEY) -> tuple[MobileNpcDefinition, ...]:
    """Idempotent registration before the game's final NPC-name audit."""
    definitions = build_world_residents(rooms)
    additions = []
    for definition in definitions:
        prior = mobile_registry.MOBILE_NPCS_BY_KEY.get(definition.key)
        if prior is not None and prior != definition:
            raise ValueError("Conflicting living resident definition: " + definition.key)
        if prior is None:
            additions.append(definition)
            mobile_registry.MOBILE_NPCS_BY_KEY[definition.key] = definition
    if additions:
        mobile_registry.MOBILE_NPC_DEFINITIONS += tuple(additions)
    return definitions


def _cast_here(manager: MobileNpcManager, room_key: str):
    return tuple(
        RESIDENTS_BY_KEY[state.definition.key]
        for state in manager.npcs_in_room(room_key)
        if state.definition.key in RESIDENTS_BY_KEY
    )


def phase_line(person: Resident, hour: int, weather: str) -> tuple[str, ...]:
    if 5 <= hour < 8:
        speech = person.dawn
    elif 8 <= hour < 18:
        speech = person.daytime
    elif 18 <= hour < 21:
        speech = person.dusk
    else:
        speech = person.night
    lines = [person.name + " says, '" + speech + "'"]
    if weather in WET_WEATHER:
        lines.append(person.name + " adds, '" + person.weather + "'")
    return tuple(lines)


def world_chatter_lines(manager: MobileNpcManager, room_key: str, hour: int,
                        weather: str, *, rng: random.Random | None = None) -> tuple[str, ...]:
    cast = _cast_here(manager, room_key)
    if not cast:
        return ()
    rng = rng or random.Random()
    if len(cast) >= 2:
        for entry, first in cast:
            if any(other.key != first.key and other.key in
                   {person.key for person in entry.residents} for _, other in cast):
                return entry.exchange
    _entry, actor = rng.choice(cast)
    if weather in WET_WEATHER and rng.random() < 0.5:
        return (actor.name + " remarks, '" + actor.weather + "'",)
    return (actor.action,)


@dataclass(slots=True)
class WorldChatterDirector:
    cooldown_seconds: float = 120.0
    last_spoken: dict[str, float] = field(default_factory=dict)

    def ready(self, room_key: str, now: float) -> bool:
        return now - self.last_spoken.get(room_key, float("-inf")) >= self.cooldown_seconds

    def mark(self, room_key: str, now: float) -> None:
        self.last_spoken[room_key] = now


async def run_world_chatter(
    manager: MobileNpcManager,
    rooms: Mapping,
    database,
    player_rooms_provider: Callable[[], Iterable[str]],
    broadcast: Callable[[str, str], Awaitable[None]],
    weather_provider: Callable[[str], str],
    *,
    interval_seconds: float = 30.0,
) -> None:
    """One task over occupied hubs, not an NPC process per entity."""
    loop = asyncio.get_running_loop()
    rng = random.Random()
    director = WorldChatterDirector()
    from mud.waymeet_living_npcs import WAYMEET_WEATHER_REGION
    while True:
        await asyncio.sleep(interval_seconds)
        hour = ASTRALIS_CLOCK.now().hour
        total_hour = ASTRALIS_CLOCK.now().total_hours
        for room_key in sorted(set(player_rooms_provider())):
            if room_key not in rooms or not director.ready(room_key, loop.time()):
                continue
            region = rooms[room_key].region_key
            is_waymeet = region == WAYMEET_WEATHER_REGION
            cast = _cast_here(manager, room_key)
            waymeet_present = is_waymeet and any(
                state.definition.key.startswith("waymeet_")
                for state in manager.npcs_in_room(room_key)
            )
            if not cast and not waymeet_present:
                continue
            rumor = pending_rumor(database, region, total_hour)
            if rumor is not None:
                await broadcast(room_key, rumor["text"])
                mark_rumor_heard(database, int(rumor["id"]), region)
                director.mark(room_key, loop.time())
                continue
            if is_waymeet or rng.random() > 0.70:
                continue  # The existing Waymeet director owns its local chatter.
            lines = world_chatter_lines(
                manager, room_key, hour, weather_provider(region), rng=rng,
            )
            if lines:
                await broadcast(room_key, "\r\n".join(lines))
                director.mark(room_key, loop.time())


def resolve_world_talk(manager: MobileNpcManager | None, room_key: str,
                       target: str) -> tuple[Resident | None, tuple[str, ...]]:
    if manager is None:
        return None, ()
    query = " ".join(target.casefold().replace("-", " ").split())
    matches = []
    for _region, resident in _cast_here(manager, room_key):
        aliases = (
            resident.name, resident.name.split()[0], resident.name.split()[-1],
            resident.job,
        )
        if query in {" ".join(value.casefold().replace("-", " ").split()) for value in aliases}:
            matches.append(resident)
    if len(matches) == 1:
        return matches[0], ()
    if len(matches) > 1:
        return None, tuple(sorted(value.name for value in matches))
    return None, ()


def install_world_living_talk_runtime(player_session_class, world_service) -> None:
    """Outside existing quest/Waymeet TALK handlers: catch only our mobile cast."""
    if getattr(player_session_class, "_world_living_talk_installed", False):
        return
    previous = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        parts = command.strip().split(maxsplit=1)
        normalized = " ".join(command.lower().split())
        room_key = self.character.current_room or ""
        scene = world_service.scene(room_key)
        if normalized in {"local rumors", "rumors here", "hear rumors"} and scene is not None:
            heard = latest_rumors(self.database, scene.region_key, ASTRALIS_CLOCK.now().total_hours)
            if not heard:
                await self.send("No news has made it here yet.\r\n")
            else:
                await self.send("\r\nLocal word of mouth:\r\n")
                for rumor in heard:
                    await self.send("- " + str(rumor["text"]) + "\r\n")
            return
        if len(parts) == 2 and parts[0].casefold() == "talk":
            target = parts[1].strip()
            if target.casefold().startswith("to "):
                target = target[3:].strip()
            resident, ambiguous = resolve_world_talk(
                getattr(self, "mobile_npcs", None), room_key, target,
            )
            if ambiguous:
                await self.send("That name matches: " + ", ".join(ambiguous) + ".\r\n")
                return
            if resident is not None:
                hour = ASTRALIS_CLOCK.now().hour
                weather = world_service.state.weather_for(scene.region_key) if scene else "clear"
                lines = phase_line(resident, hour, weather)
                if scene is not None:
                    news = latest_rumors(self.database, scene.region_key, ASTRALIS_CLOCK.now().total_hours, limit=1)
                    if news:
                        lines += (resident.name + " adds, '" + str(news[0]["text"]) + "'",)
                await self.send("\r\n" + "\r\n".join(lines) + "\r\n")
                return
        await _delegate_prompt(self, previous, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._world_living_talk_installed = True
