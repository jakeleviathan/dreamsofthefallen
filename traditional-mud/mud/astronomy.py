from __future__ import annotations

"""Quiet, persistent stargazing across the real Astralis clock and weather.

This hobby awards only memories and curios. It never grants combat stats, XP,
currency, daily obligations, or access to story-critical progression.
"""

from dataclasses import dataclass

import mud.crafting as crafting
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.crafting import ItemDefinition
from mud.weather_gameplay import room_is_weather_exposed
from mud.social_experience import _ACTIVE_SESSIONS
from mud.waymeet_frontier import WAYMEET_CRAFT_ROW_KEY, WAYMEET_LANTERN_MARKET_KEY

TELESCOPE_KEY = "astronomy_field_telescope"
LENS_KEY = "astronomy_polished_lens"
CHART_KEY = "astronomy_folded_star_chart"
CHARM_KEY = "astronomy_hushglass_charm"
CHART_FLAG = "astronomy_first_chart_keepsake"
CHARM_FLAG = "astronomy_unlisted_star_keepsake"

TELESCOPE_PRICE = 24
LENS_PRICE = 6
TELESCOPE_RECIPE = {"iron_ingot": 1, "cotton_thread": 1, LENS_KEY: 1}
BLOCKED_WEATHER = frozenset({"cloudy", "mist", "rain", "storm", "thunderstorm", "snow", "duststorm"})
BLOCKED_ROOM_TAGS = frozenset({
    "indoors", "interior", "underground", "cavern", "crypt", "dungeon",
    "tunnel", "underways", "mine", "cellar", "basement", "cave",
})
BLOCKED_REGIONS = frozenset({"veilith"})
REGIONAL_SKIES = {
    "waymeet_frontier": (
        "The Crossroads Knot",
        "Four pale sparks hold the shape of intersecting roads. Their meeting point glows a little warmer than the rest.",
    ),
    "sablewater_reach": (
        "The Heron's Reflection",
        "A long-necked figure bends above the horizon. In the river below, the reflection bends in the opposite direction.",
    ),
    "veyra_city": (
        "The Iron Choir",
        "Narrow stars stand like dark cathedral spires, their tips lit by a thin constellation of bells.",
    ),
    "salt_kingdoms_whitewake": (
        "The Dry Sail",
        "A white triangular sail rises above the old sea basin, forever traveling across empty water.",
    ),
    "starfall_scar": (
        "The Fallen Meridian",
        "The brightest points describe a line that appears to end exactly where the old scar begins.",
    ),
}
SEASONAL_SKIES = {
    "spring": (
        "The Lantern Thread",
        "Tiny lights trail in a winding line like travelers holding lanterns through tall grass.",
    ),
    "summer": (
        "The Glass Heron",
        "Seven cold stars sketch a bird with wings folded, as though waiting patiently beside water.",
    ),
    "autumn": (
        "The Hollow Crown",
        "A circle of amber stars leaves a deliberate gap where its finest jewel ought to be.",
    ),
    "winter": (
        "The Sleeping Engine",
        "Faint silver points form wheels and a long still axle. Nothing in the pattern suggests motion.",
    ),
}
SEASONAL_COMMENT = {
    "spring": "Warm pinpoints gather along the eastern horizon as the season turns.",
    "summer": "The high sky is unusually deep, and its brightest stars seem almost near enough to touch.",
    "autumn": "A haze of bronze light hangs beyond the last thin clouds.",
    "winter": "The stars are painfully crisp against the cold black distance.",
}

ITEMS = (
    ItemDefinition(
        TELESCOPE_KEY, "Field Telescope",
        "A portable brass viewing tube, carefully focused for watching the stars. A companion, not a weapon.",
        "curio", tier=1,
    ),
    ItemDefinition(
        LENS_KEY, "Polished Telescope Lens",
        "A small, carefully ground glass lens for a hand-assembled field telescope.",
        "material", tier=1,
    ),
    ItemDefinition(
        CHART_KEY, "Folded Night-Sky Chart",
        "A hand-drawn keepsake marking three different things you noticed above Astralis. It gives no bonuses.",
        "curio", tier=1,
    ),
    ItemDefinition(
        CHARM_KEY, "Hushglass Star Charm",
        "A small clouded-glass pendant honoring the night you saw a star missing from every chart. Purely decorative.",
        "curio", tier=1,
    ),
)


@dataclass(frozen=True, slots=True)
class SkySighting:
    key: str
    name: str
    description: str


def install_astronomy_content() -> None:
    for item in ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS += (item,)
        crafting.ITEMS_BY_KEY[item.key] = item


def ensure_astronomy_schema(database) -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS astronomy_sightings (
                character_id INTEGER NOT NULL,
                sighting_key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                room_key TEXT NOT NULL,
                region_key TEXT NOT NULL,
                day_number INTEGER NOT NULL,
                season TEXT NOT NULL,
                moon_phase TEXT NOT NULL,
                weather TEXT NOT NULL,
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(character_id, sighting_key),
                FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )


def recorded_sightings(database, character_id: int) -> list[dict]:
    ensure_astronomy_schema(database)
    with database.connect() as db:
        rows = db.execute(
            """SELECT sighting_key, name, description, room_key, day_number,
                      season, moon_phase, weather
               FROM astronomy_sightings WHERE character_id = ?
               ORDER BY day_number, name""",
            (character_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def record_sighting(database, character_id: int, sighting: SkySighting, room, moment, weather: str) -> bool:
    ensure_astronomy_schema(database)
    with database.connect() as db:
        result = db.execute(
            """INSERT OR IGNORE INTO astronomy_sightings
               (character_id, sighting_key, name, description, room_key,
                region_key, day_number, season, moon_phase, weather)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                character_id, sighting.key, sighting.name, sighting.description,
                room.key, room.region_key, moment.day_number,
                moment.season, moment.moon_phase, weather,
            ),
        )
        return result.rowcount == 1


def sky_sightings(moment, region_key: str, weather: str) -> tuple[SkySighting, ...]:
    if moment.phase != "night" or weather in BLOCKED_WEATHER:
        return ()
    season_name, season_description = SEASONAL_SKIES[moment.season]
    sights = [SkySighting("season_" + moment.season, season_name, season_description)]
    regional = REGIONAL_SKIES.get(region_key)
    if regional:
        sights.append(SkySighting("regional_" + region_key, regional[0], regional[1]))
    # A rare, deterministic alignment: available to anyone, not gated on combat.
    if (
        moment.moon_phase == "new"
        and (moment.hour >= 23 or moment.hour < 3)
        and moment.day_number % 3 == 0
        and weather == "clear"
    ):
        sights.append(
            SkySighting(
                "unlisted_star", "The Unlisted Star",
                "There is an extra star beside a familiar pattern. When you look away and return, the sky contains its absence instead.",
            )
        )
    return tuple(sights)


def open_sky(room) -> bool:
    if room is None:
        return False
    if room.region_key in BLOCKED_REGIONS or room.region_key.startswith("plane_"):
        return False
    if any(tag in BLOCKED_ROOM_TAGS for tag in room.tags):
        return False
    if any(word in room.key for word in ("underground", "dungeon", "cathedral", "tollhouse", "underclock", "gloamworks", "crypt")):
        return False
    return room_is_weather_exposed(room.tags, room.key)


def _setting(session, world):
    room_key = session.character.current_room or ""
    room = world.legacy_rooms.get(room_key) or legacy_world.ROOMS_BY_KEY.get(room_key)
    moment = ASTRALIS_CLOCK.now()
    weather = world.state.weather_for(room.region_key) if room is not None else "clear"
    return room, moment, weather


def _has_telescope(session) -> bool:
    return session.database.item_quantity(session.character.id, TELESCOPE_KEY) > 0


async def _show_help(session) -> None:
    await session.send(
        "\r\n--- Astronomy: Quiet Nights of Astralis ---\r\n"
        "ASTRONOMY / SKY: sky conditions and observation hints\r\n"
        "OBSERVE SKY / STARGAZE / CHART SKY: watch the sky, chart what you discover\r\n"
        "SKY JOURNAL / CONSTELLATIONS: read your own persistent notes\r\n"
        "SHOW STAR CHART: share your keepsake with people nearby\r\n"
        "SKY SHOP (Lantern Market): buy a telescope or a lens\r\n"
        "ASSEMBLE TELESCOPE (Hammer and Thread Row): iron ingot, cotton thread, polished lens\r\n"
        "Clear, open nights are best. Different seasons and places have different skies.\r\n"
        "No experience, combat rewards, daily tasks, or completion pressure.\r\n"
    )


async def _show_journal(session) -> None:
    rows = recorded_sightings(session.database, session.character.id)
    await session.send("\r\n--- Your Night-Sky Journal ---\r\n")
    if not rows:
        await session.send("The pages are blank. On a clear night, find an open place and OBSERVE SKY with a telescope.\r\n")
        return
    for entry in rows:
        await session.send(
            f"* {entry['name']} - first seen Astralis day {entry['day_number']}, "
            f"{entry['season']}, under the {entry['moon_phase']} moon.\r\n"
            f"  {entry['description']}\r\n"
        )
    await session.send(
        f"{len(rows)} distinct observations. A journal is a record of curiosity, not a score.\r\n"
    )


async def _sky_conditions(session, world) -> None:
    room, moment, weather = _setting(session, world)
    if not open_sky(room):
        await session.send("There is no clear view of Astralis's sky from here. Find an open outdoor place.\r\n")
        return
    await session.send(
        f"Above {room.name}: {moment.season_name}, {moment.phase}, "
        f"{moment.moon_phase_name.lower()} moon. Weather: {weather}.\r\n"
    )
    if moment.phase != "night":
        await session.send("A few pale lights will return when night settles. There is no need to hurry.\r\n")
    elif weather in BLOCKED_WEATHER:
        await session.send("The sky is hidden tonight. Even a telescope cannot chart what clouds conceal.\r\n")
    else:
        await session.send(SEASONAL_COMMENT[moment.season] + " OBSERVE SKY to spend a quiet moment looking.\r\n")


async def _observe(session, world) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send("Your attention is on surviving the fight. You can stargaze when you are safe.\r\n")
        return
    room, moment, weather = _setting(session, world)
    if not open_sky(room):
        await session.send("You need the open sky overhead to watch the stars.\r\n")
        return
    if moment.phase != "night":
        await session.send(
            f"The {moment.phase} sky is beautiful in its own way. "
            "The constellations will become legible after nightfall.\r\n"
        )
        return
    if weather in BLOCKED_WEATHER:
        await session.send(
            f"Only {weather} fills the sky above {room.name}. "
            "You can wait for another evening; nothing is lost by missing a night.\r\n"
        )
        return
    if not _has_telescope(session):
        await session.send(
            "You lie back and watch an immense scatter of stars. "
            + SEASONAL_COMMENT[moment.season]
            + " A telescope would help you trace the patterns into your journal. "
            "Find one at Waymeet's Lantern Market.\r\n"
        )
        return

    await session.send(
        f"You settle the telescope, wait for your breath to steady, and look above {room.name}. "
        + SEASONAL_COMMENT[moment.season] + "\r\n"
    )
    new_count = 0
    for sighting in sky_sightings(moment, room.region_key, weather):
        await session.send(f"{sighting.name}: {sighting.description}\r\n")
        if record_sighting(session.database, session.character.id, sighting, room, moment, weather):
            new_count += 1
            await session.send("  New drawing added to your night-sky journal.\r\n")
    if new_count == 0:
        await session.send(
            "The shapes are familiar tonight. You can still enjoy the view; not every night needs a discovery.\r\n"
        )

    records = recorded_sightings(session.database, session.character.id)
    flags = session.database.list_flags(session.character.id)
    if len(records) >= 3 and CHART_FLAG not in flags:
        session.database.grant_flag(session.character.id, CHART_FLAG)
        session.database.add_item(session.character.id, CHART_KEY, 1)
        await session.send(
            "You fold your first three sketches into a small physical star chart. "
            "It is yours to keep or show another traveler; it gives no combat advantage.\r\n"
        )
    if any(row["sighting_key"] == "unlisted_star" for row in records) and CHARM_FLAG not in flags:
        session.database.grant_flag(session.character.id, CHARM_FLAG)
        session.database.add_item(session.character.id, CHARM_KEY, 1)
        await session.send(
            "You set aside a tiny hushglass charm to remember the star that should not be there. "
            "It is only a keepsake.\r\n"
        )



async def _share_chart(session) -> None:
    if session.database.item_quantity(session.character.id, CHART_KEY) < 1:
        await session.send("You do not carry a folded night-sky chart to show.\r\n")
        return
    sightings = recorded_sightings(session.database, session.character.id)
    favorites = ", ".join(entry["name"] for entry in sightings[:3])
    await session.send(
        "You unfold your hand-drawn night-sky chart for anyone nearby. "
        + (f"It shows {favorites}.\r\n" if favorites else "\r\n")
    )
    for other in tuple(_ACTIVE_SESSIONS):
        character = getattr(other, "character", None)
        if other is session or character is None:
            continue
        if character.current_room == session.character.current_room:
            await other.send(
                f"{session.character.name} unfolds a hand-drawn star chart. "
                + (f"It shows {favorites}.\r\n" if favorites else "\r\n")
            )


async def _sky_shop(session) -> None:
    if session.character.current_room != WAYMEET_LANTERN_MARKET_KEY:
        await session.send("A small telescope stall operates at Waymeet's Lantern Market.\r\n")
        return
    await session.send(
        "\r\n--- Lantern Market: Skywatcher's Stall ---\r\n"
        f"Field Telescope: {TELESCOPE_PRICE} sparks (BUY TELESCOPE)\r\n"
        f"Polished Telescope Lens: {LENS_PRICE} sparks (BUY LENS)\r\n"
        "You can assemble a telescope yourself at Hammer and Thread Row with "
        "one iron ingot, one cotton thread, and one polished lens.\r\n"
    )


async def _buy(session, key: str, price: int, name: str) -> None:
    if session.character.current_room != WAYMEET_LANTERN_MARKET_KEY:
        await session.send("That skywatching item is sold at Waymeet's Lantern Market.\r\n")
        return
    if key == TELESCOPE_KEY and _has_telescope(session):
        await session.send("You already carry a field telescope.\r\n")
        return
    if not session.database.spend_sols(session.character.id, price):
        await session.send(f"The {name} costs {price} sparks. You don't have enough Sols.\r\n")
        return
    session.database.add_item(session.character.id, key, 1)
    await session.send(f"You buy a {name} for {price} sparks. Clear nights are waiting.\r\n")


async def _assemble(session) -> None:
    if session.character.current_room != WAYMEET_CRAFT_ROW_KEY:
        await session.send("Use the open workbenches at Waymeet's Hammer and Thread Row.\r\n")
        return
    if _has_telescope(session):
        await session.send("You already have a field telescope ready for the sky.\r\n")
        return
    lacking = [
        f"{amount} {crafting.ITEMS_BY_KEY[key].name}"
        for key, amount in TELESCOPE_RECIPE.items()
        if session.database.item_quantity(session.character.id, key) < amount
    ]
    if lacking:
        await session.send("To assemble a field telescope, bring " + ", ".join(lacking) + ".\r\n")
        return
    # A session handles a single command at a time. Preflight all quantities
    # before consuming, using the game's normal persistent inventory methods.
    for key, amount in TELESCOPE_RECIPE.items():
        if not session.database.consume_item(session.character.id, key, amount):
            await session.send("Your materials changed. Check your pack and try again.\r\n")
            return
    session.database.add_item(session.character.id, TELESCOPE_KEY, 1)
    await session.send(
        "You fit the lens into an iron housing, pad the focusing ring with thread, "
        "and assemble a usable field telescope. No trade-skill grind required.\r\n"
    )


async def _delegate(session, old_prompt, command):
    previous = session.__dict__.get("prompt")
    owned = "prompt" in session.__dict__

    async def replay(_text=""):
        return command

    session.prompt = replay
    try:
        await old_prompt(session)
    finally:
        if owned:
            session.prompt = previous
        else:
            session.__dict__.pop("prompt", None)


def install_astronomy_runtime(player_session_class, world) -> None:
    install_astronomy_content()
    if getattr(player_session_class, "_astronomy_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_show_current_room = player_session_class.show_current_room

    async def show_current_room(self):
        await previous_show_current_room(self)
        character = getattr(self, "character", None)
        if character is not None and character.current_room in {WAYMEET_LANTERN_MARKET_KEY, WAYMEET_CRAFT_ROW_KEY}:
            await self.send(
                "A skywatcher's hobby is available here. ASTRONOMY lists the quiet-night commands.\r\n"
            )

    async def playing_prompt(self):
        if getattr(self, "character", None) is None:
            return await previous_playing_prompt(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        action = " ".join(command.casefold().strip().split())
        if action in {"astronomy", "help astronomy", "stargazing help"}:
            return await _show_help(self)
        if action in {"sky", "sky conditions", "look sky", "look at sky"}:
            return await _sky_conditions(self, world)
        if action in {"observe sky", "observe stars", "stargaze", "chart sky", "look through telescope"}:
            return await _observe(self, world)
        if action in {"sky journal", "astronomy journal", "constellations", "star journal", "star chart", "read star chart"}:
            return await _show_journal(self)
        if action in {"show star chart", "show sky chart", "share star chart"}:
            return await _share_chart(self)
        if action in {"sky shop", "astronomy shop"}:
            return await _sky_shop(self)
        if action in {"buy telescope", "buy field telescope"}:
            return await _buy(self, TELESCOPE_KEY, TELESCOPE_PRICE, "Field Telescope")
        if action in {"buy lens", "buy telescope lens", "buy polished telescope lens"}:
            return await _buy(self, LENS_KEY, LENS_PRICE, "Polished Telescope Lens")
        if action in {"assemble telescope", "craft telescope", "make telescope"}:
            return await _assemble(self)
        return await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class.show_current_room = show_current_room
    player_session_class._astronomy_installed = True
