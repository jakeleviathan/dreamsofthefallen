from __future__ import annotations

from typing import Mapping

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.starter_class_moments import (
    CLASS_PRACTICE,
    RACE_OPENING_TRIGGERS,
    RACE_SETTINGS,
    all_starter_class_moments,
)
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


def starter_matrix_summary() -> dict[str, int]:
    """Return the launch opening matrix in numbers useful to tests/staff tooling."""
    races = len(RACES_BY_KEY)
    classes = len(CLASSES_BY_KEY)
    moments = all_starter_class_moments()
    return {
        "races": races,
        "classes": classes,
        "combinations": races * classes,
        "race_openings": len(STARTER_RACE_LOOPS_BY_RACE),
        "class_moments": len(moments),
        "opening_triggers": len(RACE_OPENING_TRIGGERS),
    }


def validate_starter_matrix_contract(*, quests_by_key: Mapping[str, object]) -> None:
    """Fail production startup if any playable race/class opening falls out of the matrix.

    The game intentionally has one culturally distinct racial opening per race and
    one class-specific practice beat woven into that opening for every legal
    race/class pairing. This check protects the complete 8x5 launch promise rather
    than relying on isolated unit tests that may never be installed by production.
    """
    problems: list[str] = []
    race_keys = set(RACES_BY_KEY)
    class_keys = set(CLASSES_BY_KEY)

    if set(STARTER_RACE_LOOPS_BY_RACE) != race_keys:
        missing = race_keys - set(STARTER_RACE_LOOPS_BY_RACE)
        extra = set(STARTER_RACE_LOOPS_BY_RACE) - race_keys
        if missing:
            problems.append("races without authored starter loops: " + ", ".join(sorted(missing)))
        if extra:
            problems.append("starter loops for unknown races: " + ", ".join(sorted(extra)))

    if set(RACE_SETTINGS) != race_keys:
        missing = race_keys - set(RACE_SETTINGS)
        extra = set(RACE_SETTINGS) - race_keys
        if missing:
            problems.append("races without class framing: " + ", ".join(sorted(missing)))
        if extra:
            problems.append("class framing for unknown races: " + ", ".join(sorted(extra)))

    if set(RACE_OPENING_TRIGGERS) != race_keys:
        missing = race_keys - set(RACE_OPENING_TRIGGERS)
        extra = set(RACE_OPENING_TRIGGERS) - race_keys
        if missing:
            problems.append("races without class-moment triggers: " + ", ".join(sorted(missing)))
        if extra:
            problems.append("class-moment triggers for unknown races: " + ", ".join(sorted(extra)))

    if set(CLASS_PRACTICE) != class_keys:
        missing = class_keys - set(CLASS_PRACTICE)
        extra = set(CLASS_PRACTICE) - class_keys
        if missing:
            problems.append("classes without opening practice: " + ", ".join(sorted(missing)))
        if extra:
            problems.append("opening practice for unknown classes: " + ", ".join(sorted(extra)))

    moments = all_starter_class_moments()
    expected = len(race_keys) * len(class_keys)
    if len(moments) != expected:
        problems.append(f"starter class matrix contains {len(moments)} combinations; expected {expected}")

    pairs = {(moment.race_key, moment.class_key) for moment in moments}
    expected_pairs = {(race, cls) for race in race_keys for cls in class_keys}
    missing_pairs = expected_pairs - pairs
    extra_pairs = pairs - expected_pairs
    if missing_pairs:
        problems.append(
            "missing race/class moments: "
            + ", ".join(f"{race}/{cls}" for race, cls in sorted(missing_pairs))
        )
    if extra_pairs:
        problems.append(
            "unknown race/class moments: "
            + ", ".join(f"{race}/{cls}" for race, cls in sorted(extra_pairs))
        )

    flags = [moment.flag_key for moment in moments]
    if len(flags) != len(set(flags)):
        problems.append("starter race/class completion flags are not unique")

    for race_key, trigger in RACE_OPENING_TRIGGERS.items():
        if trigger.quest_key not in quests_by_key:
            problems.append(f"{race_key}: class-moment trigger quest does not exist: {trigger.quest_key}")
        if not trigger.trigger_step.strip():
            problems.append(f"{race_key}: class-moment trigger step is empty")
        if not trigger.lead_in.strip() or not trigger.closing.strip():
            problems.append(f"{race_key}: class-moment narrative framing is incomplete")

    for class_key, (practice, lesson) in CLASS_PRACTICE.items():
        if not practice.strip() or not lesson.strip():
            problems.append(f"{class_key}: opening class practice text is incomplete")

    if problems:
        raise RuntimeError("Starter race/class matrix contract failed:\n- " + "\n- ".join(problems))
