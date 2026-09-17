from __future__ import annotations

import math
from dataclasses import dataclass


MAX_MASTERY_LEVEL = 100
MASTERY_BANDS: tuple[tuple[int, str], ...] = (
    (1, "Novice"),
    (10, "Practiced"),
    (25, "Skilled"),
    (50, "Expert"),
    (75, "Master"),
    (100, "Grandmaster"),
)


@dataclass(frozen=True, slots=True)
class MasteryProgress:
    ability_key: str
    uses: int
    skill_xp: int
    level: int
    band: str
    next_level_xp: int | None


@dataclass(frozen=True, slots=True)
class MasteryCurve:
    power: tuple[tuple[int, float], ...] = ((1, 1.0), (100, 1.0))
    mana_discount: tuple[tuple[int, float], ...] = ((1, 0.0), (100, 0.0))
    duration_bonus: tuple[tuple[int, float], ...] = ((1, 0.0), (100, 0.0))
    flat_bonus: tuple[tuple[int, float], ...] = ((1, 0.0), (100, 0.0))


DAMAGE_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.03), (25, 1.08), (50, 1.15), (75, 1.23), (100, 1.32)),
    mana_discount=((1, 0), (25, 0), (50, 1), (75, 1), (100, 2)),
)
HEALING_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.04), (25, 1.10), (50, 1.18), (75, 1.28), (100, 1.40)),
    mana_discount=((1, 0), (25, 1), (50, 1), (75, 2), (100, 3)),
)
EMERGENCY_HEAL_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.03), (25, 1.09), (50, 1.20), (75, 1.33), (100, 1.48)),
    mana_discount=((1, 0), (25, 0), (50, 1), (75, 2), (100, 3)),
)
LIFE_DRAIN_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.03), (25, 1.08), (50, 1.16), (75, 1.25), (100, 1.35)),
    mana_discount=((1, 0), (25, 0), (50, 1), (75, 2), (100, 2)),
)
SUPPORT_BUFF_CURVE = MasteryCurve(
    mana_discount=((1, 0), (25, 0), (50, 1), (75, 1), (100, 2)),
    duration_bonus=((1, 0), (10, 3), (25, 8), (50, 15), (75, 25), (100, 40)),
    flat_bonus=((1, 0), (10, 0), (25, 1), (50, 2), (75, 3), (100, 4)),
)
RESTORING_LIGHT_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.05), (25, 1.12), (50, 1.22), (75, 1.33), (100, 1.45)),
    mana_discount=((1, 0), (25, 1), (50, 1), (75, 2), (100, 3)),
)
WELLSPRING_CURVE = MasteryCurve(
    power=((1, 1.00), (10, 1.03), (25, 1.08), (50, 1.15), (75, 1.23), (100, 1.32)),
    mana_discount=((1, 0), (10, 0), (25, 1), (50, 2), (75, 3), (100, 4)),
)


ABILITY_CURVE_OVERRIDES: dict[str, MasteryCurve] = {
    "blessing_of_resolve": SUPPORT_BUFF_CURVE,
    "hp_buff": SUPPORT_BUFF_CURVE,
    "restoring_light": RESTORING_LIGHT_CURVE,
    "wellspring": WELLSPRING_CURVE,
    "second_breath": EMERGENCY_HEAL_CURVE,
    "refuse_the_grave": EMERGENCY_HEAL_CURVE,
    "minor_life_tap": LIFE_DRAIN_CURVE,
    "soul_harvest": LIFE_DRAIN_CURVE,
    "soul_hook": LIFE_DRAIN_CURVE,
}


_HEALING_CATEGORIES = {
    "healing", "group_healing", "healing_over_time", "capstone_healing",
    "healing_protection", "emergency_healing",
}
_DAMAGE_WORDS = (
    "damage", "attack", "strike", "control", "curse", "retribution",
    "sequence", "judgment", "nature_setup",
)
_SUPPORT_CATEGORIES = {"ally_buff"}


def xp_for_mastery_level(level: int) -> int:
    """Cumulative skill XP required for a 1-100 mastery level.

    Triangular thresholds keep early growth visible while making very high
    mastery a long-term achievement: level 10 = 45 XP, 50 = 1,225 XP,
    and 100 = 4,950 XP.
    """

    level = max(1, min(MAX_MASTERY_LEVEL, int(level)))
    return (level - 1) * level // 2


def mastery_level_for_xp(skill_xp: int) -> int:
    xp = max(0, int(skill_xp))
    # Invert n(n-1)/2 <= xp, then clamp to the authored cap.
    level = int((1 + math.sqrt(1 + 8 * xp)) // 2)
    return max(1, min(MAX_MASTERY_LEVEL, level))


def mastery_band(level: int) -> str:
    level = max(1, min(MAX_MASTERY_LEVEL, int(level)))
    current = MASTERY_BANDS[0][1]
    for threshold, label in MASTERY_BANDS:
        if level < threshold:
            break
        current = label
    return current


def _raw_progress(database, character_id: int, ability_key: str) -> tuple[int, int]:
    getter = getattr(database, "get_ability_progress", None)
    if callable(getter):
        row = getter(character_id, ability_key)
        if row is not None:
            return int(row.get("uses", 0)), int(row.get("skill_xp", 0))
    lister = getattr(database, "list_ability_progress", None)
    if callable(lister):
        for row in lister(character_id):
            if str(row.get("ability_key", "")) == ability_key:
                return int(row.get("uses", 0)), int(row.get("skill_xp", 0))
    return 0, 0


def progress(database, character_id: int, ability_key: str) -> MasteryProgress:
    uses, skill_xp = _raw_progress(database, character_id, ability_key)
    level = mastery_level_for_xp(skill_xp)
    next_xp = None if level >= MAX_MASTERY_LEVEL else xp_for_mastery_level(level + 1)
    return MasteryProgress(
        ability_key=ability_key,
        uses=uses,
        skill_xp=skill_xp,
        level=level,
        band=mastery_band(level),
        next_level_xp=next_xp,
    )


def _curve_value(points: tuple[tuple[int, float], ...], level: int) -> float:
    level = max(1, min(MAX_MASTERY_LEVEL, int(level)))
    ordered = tuple(sorted(points))
    if level <= ordered[0][0]:
        return float(ordered[0][1])
    for (left_level, left_value), (right_level, right_value) in zip(ordered, ordered[1:]):
        if level <= right_level:
            width = max(1, right_level - left_level)
            ratio = (level - left_level) / width
            return float(left_value) + (float(right_value) - float(left_value)) * ratio
    return float(ordered[-1][1])


def curve_for(ability) -> MasteryCurve:
    if ability is None or not bool(getattr(ability, "skill_improves_effectiveness", True)):
        return MasteryCurve()
    key = str(getattr(ability, "key", ""))
    if key in ABILITY_CURVE_OVERRIDES:
        return ABILITY_CURVE_OVERRIDES[key]
    category = str(getattr(ability, "category", "") or "").lower()
    if category in _HEALING_CATEGORIES:
        return EMERGENCY_HEAL_CURVE if "emergency" in category else HEALING_CURVE
    if category in _SUPPORT_CATEGORIES:
        return SUPPORT_BUFF_CURVE
    if "life_drain" in category:
        return LIFE_DRAIN_CURVE
    if any(word in category for word in _DAMAGE_WORDS):
        return DAMAGE_CURVE
    return DAMAGE_CURVE


def _progress_for_session(session, ability) -> MasteryProgress:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or ability is None:
        return MasteryProgress(
            getattr(ability, "key", "") if ability is not None else "",
            0,
            0,
            1,
            "Novice",
            xp_for_mastery_level(2),
        )
    return progress(database, character.id, ability.key)


def scale_power(session, ability, amount: int | float) -> int:
    if ability is None or not bool(getattr(ability, "skill_improves_effectiveness", True)):
        return max(0, int(round(amount)))
    state = _progress_for_session(session, ability)
    multiplier = _curve_value(curve_for(ability).power, state.level)
    return max(0, int(round(float(amount) * multiplier)))


def effective_mana_cost(session, ability, base_cost: int | None = None) -> int:
    base = int((getattr(ability, "mana_cost", 0) or 0) if base_cost is None else base_cost)
    if ability is None or not bool(getattr(ability, "skill_improves_effectiveness", True)):
        return max(0, base)
    state = _progress_for_session(session, ability)
    discount = int(round(_curve_value(curve_for(ability).mana_discount, state.level)))
    return max(0, base - discount)


def duration_bonus(session, ability) -> float:
    if ability is None or not bool(getattr(ability, "skill_improves_effectiveness", True)):
        return 0.0
    state = _progress_for_session(session, ability)
    return _curve_value(curve_for(ability).duration_bonus, state.level)


def flat_bonus(session, ability) -> int:
    if ability is None or not bool(getattr(ability, "skill_improves_effectiveness", True)):
        return 0
    state = _progress_for_session(session, ability)
    return int(round(_curve_value(curve_for(ability).flat_bonus, state.level)))


def begin_use(session, ability) -> None:
    session._ability_mastery_pending = {
        "ability": ability,
        "meaningful": False,
    }


def pending_ability(session):
    pending = getattr(session, "_ability_mastery_pending", None)
    return pending.get("ability") if isinstance(pending, dict) else None


def mark_meaningful(session) -> None:
    pending = getattr(session, "_ability_mastery_pending", None)
    if isinstance(pending, dict):
        pending["meaningful"] = True


def _enemy_estimated_level(enemy) -> int:
    definition = getattr(enemy, "definition", enemy)
    explicit = getattr(definition, "level", None)
    if explicit is not None:
        return max(1, int(explicit))
    if bool(getattr(definition, "tutorial", False)):
        return 1
    xp = max(1, int(getattr(definition, "xp_reward", 0) or 0))
    return max(1, round(5.0 * math.pow(xp / 48.0, 0.63)))


def enemy_is_meaningful(session, enemy=None) -> bool:
    character = getattr(session, "character", None)
    enemy = enemy or getattr(session, "active_enemy", None)
    if character is None or enemy is None:
        return False
    enemy_level = _enemy_estimated_level(enemy)
    return enemy_level >= max(1, int(getattr(character, "level", 1)) - 5)


def mark_damage_practice(session, dealt: int, enemy=None) -> None:
    if int(dealt) > 0 and enemy_is_meaningful(session, enemy):
        mark_meaningful(session)


def mark_healing_practice(session, restored: int) -> None:
    if int(restored) > 0:
        mark_meaningful(session)


def mark_support_practice(session, target=None, *, target_was_injured: bool = False) -> None:
    target = target or session
    if (
        getattr(session, "active_enemy", None) is not None
        or getattr(target, "active_enemy", None) is not None
        or target_was_injured
    ):
        mark_meaningful(session)


async def commit_use(session) -> MasteryProgress | None:
    pending = getattr(session, "_ability_mastery_pending", None)
    if not isinstance(pending, dict):
        return None
    session._ability_mastery_pending = None

    ability = pending.get("ability")
    character = getattr(session, "character", None)
    if ability is None or character is None:
        return None

    before = progress(session.database, character.id, ability.key)
    improves = bool(getattr(ability, "skill_improves_effectiveness", True))
    xp_gain = 1 if improves and bool(pending.get("meaningful")) else 0
    session.database.record_ability_use(character.id, ability.key, skill_xp_gain=xp_gain)
    after = progress(session.database, character.id, ability.key)

    if xp_gain and after.band != before.band:
        await session.send(
            f"*** {ability.name} mastery: {after.band} (skill {after.level}/100). "
            "Your practice has made the ability more effective. ***\r\n"
        )
    return after


async def record_completed_use(session, ability, *, meaningful: bool) -> MasteryProgress | None:
    begin_use(session, ability)
    if meaningful:
        mark_meaningful(session)
    return await commit_use(session)


def mastery_summary(database, character_id: int, ability_key: str) -> str:
    state = progress(database, character_id, ability_key)
    if state.next_level_xp is None:
        return f"{state.band} {state.level}/100, {state.skill_xp} skill XP (maximum mastery)"
    remaining = max(0, state.next_level_xp - state.skill_xp)
    return (
        f"{state.band} {state.level}/100, {state.skill_xp} skill XP "
        f"({remaining} to next skill level)"
    )
