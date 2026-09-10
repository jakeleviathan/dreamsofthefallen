from __future__ import annotations

from dataclasses import dataclass


ASTRALIS_DAYS_PER_YEAR = 90


@dataclass(frozen=True, slots=True)
class SeasonDefinition:
    key: str
    name: str
    start_day: int
    length_days: int

    @property
    def end_day(self) -> int:
        return self.start_day + self.length_days - 1

    def contains(self, day_of_year: int) -> bool:
        return self.start_day <= day_of_year <= self.end_day


# Ninety does not divide evenly into four whole-day seasons. The two extra
# days alternate between Spring and Autumn so no season differs by more than
# one day and the year remains entirely day-based rather than changing seasons
# halfway through an Astralis day.
SEASONS: tuple[SeasonDefinition, ...] = (
    SeasonDefinition("spring", "Spring", 1, 23),
    SeasonDefinition("summer", "Summer", 24, 22),
    SeasonDefinition("autumn", "Autumn", 46, 23),
    SeasonDefinition("winter", "Winter", 69, 22),
)
SEASONS_BY_KEY = {season.key: season for season in SEASONS}


# Minimalist moon model: four readable phases, each lasting seven Astralis
# days. A complete lunar cycle therefore lasts 28 days and intentionally does
# not reset at the beginning of a new year.
MOON_PHASES: tuple[str, ...] = ("new", "waxing", "full", "waning")
MOON_PHASE_NAMES = {
    "new": "New Moon",
    "waxing": "Waxing Moon",
    "full": "Full Moon",
    "waning": "Waning Moon",
}
MOON_DAYS_PER_PHASE = 7
MOON_CYCLE_DAYS = len(MOON_PHASES) * MOON_DAYS_PER_PHASE


@dataclass(frozen=True, slots=True)
class AstralisCalendarDate:
    absolute_day: int
    year: int
    day_of_year: int
    season_key: str
    season_name: str
    season_day: int
    season_length: int
    moon_phase: str
    moon_phase_name: str
    moon_phase_day: int
    moon_cycle_day: int

    @property
    def display(self) -> str:
        return (
            f"Year {self.year}, Day {self.day_of_year} of {ASTRALIS_DAYS_PER_YEAR} — "
            f"{self.season_name}, day {self.season_day} — {self.moon_phase_name}"
        )


@dataclass(frozen=True, slots=True)
class RegionalCalendarContext:
    """Calendar/celestial values a region can consume without owning calendar math."""

    region_key: str
    year: int
    day_of_year: int
    season: str
    moon_phase: str


def calendar_for_day(absolute_day: int) -> AstralisCalendarDate:
    safe_day = max(1, int(absolute_day))
    zero_based = safe_day - 1
    year, day_index = divmod(zero_based, ASTRALIS_DAYS_PER_YEAR)
    day_of_year = day_index + 1

    season = next(value for value in SEASONS if value.contains(day_of_year))
    season_day = day_of_year - season.start_day + 1

    moon_index = zero_based % MOON_CYCLE_DAYS
    phase_index, phase_day_index = divmod(moon_index, MOON_DAYS_PER_PHASE)
    moon_phase = MOON_PHASES[phase_index]

    return AstralisCalendarDate(
        absolute_day=safe_day,
        year=year + 1,
        day_of_year=day_of_year,
        season_key=season.key,
        season_name=season.name,
        season_day=season_day,
        season_length=season.length_days,
        moon_phase=moon_phase,
        moon_phase_name=MOON_PHASE_NAMES[moon_phase],
        moon_phase_day=phase_day_index + 1,
        moon_cycle_day=moon_index + 1,
    )


def regional_calendar_context(region_key: str, absolute_day: int) -> RegionalCalendarContext:
    date = calendar_for_day(absolute_day)
    return RegionalCalendarContext(
        region_key=region_key,
        year=date.year,
        day_of_year=date.day_of_year,
        season=date.season_key,
        moon_phase=date.moon_phase,
    )


def calendar_rules_text() -> str:
    season_text = ", ".join(
        f"{season.name} {season.start_day}-{season.end_day}"
        for season in SEASONS
    )
    return (
        f"An Astralis year contains {ASTRALIS_DAYS_PER_YEAR} days. "
        f"Seasons: {season_text}. "
        f"The moon follows a minimalist {MOON_CYCLE_DAYS}-day cycle: "
        "New Moon, Waxing Moon, Full Moon, Waning Moon."
    )
