from __future__ import annotations

from dataclasses import replace

import mud.mechanics as mechanics


# Several level-one abilities predate the live class-progression pass and kept
# their executable mana/cooldown tuning only inside PlayerSession. The expanded
# runtime reads AbilityDefinition directly, so make those old values first-class
# data without renaming deity/Witness-specific presentations.
INHERITED_ABILITY_TUNING: dict[str, tuple[int, float]] = {
    "coldfire_burst": (5, 4.0),
    "minor_heal": (4, 5.0),
    "restoring_light": (4, 4.0),
    "guardian_ward": (4, 8.0),
    "judgment_bolt": (5, 4.0),
}


def _tuned(ability):
    tuning = INHERITED_ABILITY_TUNING.get(ability.key)
    if tuning is None:
        return ability
    mana, cooldown = tuning
    return replace(
        ability,
        mana_cost=mana if ability.mana_cost is None else ability.mana_cost,
        cooldown_seconds=cooldown if ability.cooldown_seconds is None else ability.cooldown_seconds,
    )


def apply_inherited_class_tuning() -> None:
    """Promote old session-only starter tuning into the live ability catalog."""
    for class_key, abilities in tuple(mechanics.FIXED_CLASS_ABILITIES.items()):
        mechanics.FIXED_CLASS_ABILITIES[class_key] = tuple(_tuned(ability) for ability in abilities)
    for path_key, abilities in tuple(mechanics.PRIEST_DEITY_ABILITIES.items()):
        mechanics.PRIEST_DEITY_ABILITIES[path_key] = tuple(_tuned(ability) for ability in abilities)
