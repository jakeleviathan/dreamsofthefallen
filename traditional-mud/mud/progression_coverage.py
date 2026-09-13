from __future__ import annotations

from dataclasses import dataclass

from mud.mechanics import PROGRESSION_RULES, class_abilities_for_level


AUDIT_MAX_LEVEL = 60
CURRENT_AUTHORED_ZONE_CEILING = 11
CURRENT_CLASS_ABILITY_CEILING = 9
HARD_LEVEL_CAP: int | None = None


@dataclass(frozen=True, slots=True)
class ContentBand:
    start_level: int
    end_level: int
    label: str
    examples: tuple[str, ...]


CONTENT_BANDS: tuple[ContentBand, ...] = (
    ContentBand(1, 1, "Racial openings", ("Eight race starts", "40 race/class opening moments")),
    ContentBand(2, 5, "Waymeet frontier", ("Waymeet", "Old Toll", "Crooked Bell", "Gloamworks")),
    ContentBand(5, 7, "March and group play", ("Greywake March", "Blackreed Holdfast", "King's Scar")),
    ContentBand(6, 8, "Road to Veyra", ("Sablewater Reach", "Greywake faction chain")),
    ContentBand(8, 10, "Veyra early midgame", ("Veyra", "Underclock", "Gravewatch Keep", "Vault of the First Echo", "class field commissions")),
    ContentBand(8, 11, "High end of current authored combat", ("Drowned Tollhouse",)),
)


@dataclass(frozen=True, slots=True)
class LevelCoverage:
    level: int
    xp_floor: int
    xp_to_next: int
    authored_zone_support: bool
    class_unlock_support: bool


def level_coverage(level: int) -> LevelCoverage:
    if level < 1:
        raise ValueError("level must be >= 1")
    return LevelCoverage(
        level=level,
        xp_floor=PROGRESSION_RULES.cumulative_xp_for_level(level),
        xp_to_next=PROGRESSION_RULES.xp_to_next_level(level),
        authored_zone_support=level <= CURRENT_AUTHORED_ZONE_CEILING,
        class_unlock_support=level <= CURRENT_CLASS_ABILITY_CEILING,
    )


def abilities_for_audit(class_key: str, level: int, deity_key: str | None = None) -> tuple[str, ...]:
    return tuple(ability.key for ability in class_abilities_for_level(class_key, level, deity_key))


def progression_summary(max_level: int = AUDIT_MAX_LEVEL) -> dict[str, object]:
    if max_level < 1:
        raise ValueError("max_level must be >= 1")
    return {
        "hard_level_cap": HARD_LEVEL_CAP,
        "audited_through_level": max_level,
        "authored_zone_ceiling": CURRENT_AUTHORED_ZONE_CEILING,
        "class_ability_ceiling": CURRENT_CLASS_ABILITY_CEILING,
        "xp_required_for_level_60": PROGRESSION_RULES.cumulative_xp_for_level(60),
        "levels": tuple(level_coverage(level) for level in range(1, max_level + 1)),
    }
