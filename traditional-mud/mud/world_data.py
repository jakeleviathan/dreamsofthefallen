from __future__ import annotations

from dataclasses import dataclass


WORLD_NAME = "Astralis"
WORLD_STRUCTURE = {
    "continents": "multiple",
    "separation": "seas",
    "continent_names_locked": False,
}


@dataclass(frozen=True, slots=True)
class RegionDefinition:
    key: str
    name: str
    biome: str
    description: str
    primary_races: tuple[str, ...] = ()
    adjacent_regions: tuple[str, ...] = ()
    starting_tone: str | None = None
    is_major_start: bool = False


# These are deliberately descriptive placeholders rather than final proper nouns.
# We can name kingdoms, cities, forests, mountain ranges, and continents later
# without having to change the world topology or character records.
REGIONS: tuple[RegionDefinition, ...] = (
    RegionDefinition(
        key="human_kingdom",
        name="The Human Kingdom",
        biome="temperate kingdom",
        description=(
            "The least-populous race's single large kingdom. Its central walled city is dense with taverns, guards, merchants, "
            "guilds, dark stone, sharp spires, and demonic imagery deliberately reclaimed from how outsiders describe humans. "
            "A few surviving Earth artifacts are preserved as legendary relics."
        ),
        primary_races=("human",),
        adjacent_regions=("dwarven_mountain_industry",),
        starting_tone="busy, fortified, culturally insular, and faintly uncanny",
        is_major_start=True,
    ),
    RegionDefinition(
        key="dwarven_mountain_industry",
        name="The Dwarven Mountain Settlements",
        biome="mountains and industrial towns",
        description=(
            "An enormous steam-powered urban system extending from a great underground mountain city into above-ground towns. "
            "Trade houses, unions, workshops, freight routes, lifts, and foundries make it one of Astralis's most cosmopolitan regions."
        ),
        primary_races=("dwarf",),
        adjacent_regions=("human_kingdom",),
        starting_tone="working industrial city rather than fantasy mine",
        is_major_start=True,
    ),
    RegionDefinition(
        key="great_elf_forest",
        name="The Great Elven Forest",
        biome="ancient forest",
        description=(
            "A vast woodland containing isolated Forest Elf towns governed by Druidic Circles. The protected interior is beautiful "
            "and comfortable, while danger increases as travelers move away from settled groves."
        ),
        primary_races=("forest_elf",),
        starting_tone="beautiful and safe at first, then gradually dangerous",
        is_major_start=True,
    ),
    RegionDefinition(
        key="moon_peaks",
        name="The Moon Peaks",
        biome="high-altitude mountains",
        description=(
            "High mountain settlements of the Moon Elves, whose elegant ancient civilization is culturally and mystically tied to Astralis's moon."
        ),
        primary_races=("moon_elf",),
        starting_tone="ancient, mystical, elegant, and high above the lowlands",
        is_major_start=True,
    ),
    RegionDefinition(
        key="junk_city_and_swamps",
        name="The Goblin Swamps and Junk City",
        biome="swamps and dense salvage metropolis",
        description=(
            "Loosely connected Goblin swamp clans surround the Junk City, their noisy metropolitan heart of markets, salvage, repair, "
            "couriers, gangs, merchant families, and improvised structures."
        ),
        primary_races=("goblin",),
        starting_tone="busy, noisy, cramped, transactional, and highly interactive",
        is_major_start=True,
    ),
    RegionDefinition(
        key="troll_strongholds",
        name="The Troll Strongholds",
        biome="deep forests, wilderness, and tundra",
        description=(
            "Scattered nomadic strongholds and tribal routes rather than a single homeland. Deep-forest Trolls and tundra Snow Trolls "
            "share an ancient cultural ancestry while living in very different climates."
        ),
        primary_races=("troll",),
        starting_tone="harsh and dangerous immediately",
        is_major_start=True,
    ),
    RegionDefinition(
        key="desert_necropolis",
        name="The Desert Necropolis",
        biome="desolate desert and underground necropolis",
        description=(
            "A vast Undead city hidden beneath a desolate desert, surrounded at greater distances by remnants of ruined Undead kingdoms."
        ),
        primary_races=("undead",),
        starting_tone="quiet, eerie, gloomy, and funerary",
        is_major_start=True,
    ),
    RegionDefinition(
        key="sporekin_underways",
        name="The Sporekin Underways",
        biome="fungal caverns with scattered surface groves",
        description=(
            "A mostly hidden underground civilization of fungal towns, living networks, and shared consciousness, with only a limited "
            "surface presence visible to the other peoples of Astralis."
        ),
        primary_races=("sporekin",),
        starting_tone="wise, secluded, biological, and quietly communal",
        is_major_start=True,
    ),
    RegionDefinition(
        key="central_trade_city",
        name="The Central Trade City",
        biome="river crossroads",
        description=(
            "A neutral metropolitan crossroads built around major trade routes and rivers. All peoples of Astralis mingle here for commerce, "
            "diplomacy, work, and opportunity, making it the world's clearest cultural melting pot."
        ),
        primary_races=("human", "forest_elf", "moon_elf", "dwarf", "goblin", "troll", "undead", "sporekin"),
        starting_tone="neutral, crowded, cosmopolitan, and politically useful",
        is_major_start=False,
    ),
)

REGIONS_BY_KEY = {region.key: region for region in REGIONS}
