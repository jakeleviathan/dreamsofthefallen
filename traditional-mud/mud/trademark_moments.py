from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class TrademarkMoment:
    key: str
    event: str
    text: str
    classes: tuple[str, ...] = ()
    races: tuple[str, ...] = ()
    minimum_level: int = 1
    room_tags: tuple[str, ...] = ()
    weather: tuple[str, ...] = ()
    required_flags: tuple[str, ...] = ()
    forbidden_flags: tuple[str, ...] = ()
    once: bool = True
    weight: int = 1

    @property
    def flag_key(self) -> str:
        return f"trademark_moment_{self.key}"


@dataclass(frozen=True, slots=True)
class TrademarkContext:
    event: str
    character_class: str
    race: str
    level: int
    room_tags: frozenset[str] = frozenset()
    weather: str | None = None
    flags: frozenset[str] = frozenset()


MOMENTS: tuple[TrademarkMoment, ...] = (
    TrademarkMoment("occultist_extra_shadow", "enter_room", "For one breath, you count one more shadow than there are things here to cast it.", classes=("occultist",), minimum_level=2, room_tags=("settlement",), weight=2),
    TrademarkMoment("occultist_wrong_distance", "enter_room", "The far wall feels nearer than the floor beneath your feet. The sensation passes when you look directly at it.", classes=("occultist",), minimum_level=5, room_tags=("road",)),
    TrademarkMoment("priest_unanswered_hurt", "enter_room", "Something in the room catches at the part of you trained to answer suffering. You cannot yet tell whether it is body, spirit, or memory.", classes=("priest",), minimum_level=3),
    TrademarkMoment("necromancer_last_name", "corpse_seen", "The dead thing is silent, but for an instant you feel the shape of a name it once answered to.", classes=("necromancer",), minimum_level=3),
    TrademarkMoment("druid_rain_root", "weather_change", "Beneath the rain, one patch of living ground answers a rhythm the rest of the soil does not share.", classes=("druid",), weather=("rain",)),
    TrademarkMoment("wizard_residual_pattern", "spell_aftermath", "The magic is gone. Its geometry is not. You can still see where the working pressed against the world.", classes=("wizard",), minimum_level=3),
    TrademarkMoment("brute_bad_ground", "combat_start", "Before the first blow lands, you notice the bad footing and the narrow line an enemy would have to cross to reach anyone behind you.", classes=("brute",)),
    TrademarkMoment("goblin_useful_scrap", "examine", "Most people would call it rubbish. Your eye catches the one piece that failed cleanly enough to still be useful.", races=("goblin",)),
    TrademarkMoment("moon_elf_second_angle", "examine", "From where you stand the scene says one thing. A few steps aside, you suspect it would say another.", races=("moon_elf",)),
    TrademarkMoment("undead_old_reflex", "enter_room", "Your dead body remembers this kind of place before your mind decides whether it ever knew one.", races=("undead",), minimum_level=2),
    TrademarkMoment("sporekin_missing_voice", "enter_room", "The Chorus has impressions for places like this. Strangely, around one detail there is only absence.", races=("sporekin",), minimum_level=2),
    TrademarkMoment("troll_weather_turn", "weather_change", "Your skin notices the weather's turn before the landscape shows it.", races=("troll",)),
    TrademarkMoment("forest_elf_living_interruption", "enter_room", "A small living rhythm nearby breaks pattern, then resumes. Nothing else in the room seems to have noticed.", races=("forest_elf",)),
    TrademarkMoment("human_earth_echo", "examine", "Something about the object's proportions feels inherited rather than Astralan. You cannot say why.", races=("human",), minimum_level=4),
    TrademarkMoment("goblin_priest_junk_reliquary", "examine", "For a ridiculous instant the scrap in front of you has the composure of a reliquary. Useful and sacred may not be opposites after all.", classes=("priest",), races=("goblin",), minimum_level=4, weight=3),
)


def eligible_moments(context: TrademarkContext, moments: Iterable[TrademarkMoment] = MOMENTS) -> tuple[TrademarkMoment, ...]:
    eligible: list[TrademarkMoment] = []
    for moment in moments:
        if moment.event != context.event or context.level < moment.minimum_level:
            continue
        if moment.classes and context.character_class not in moment.classes:
            continue
        if moment.races and context.race not in moment.races:
            continue
        if moment.room_tags and not set(moment.room_tags).issubset(context.room_tags):
            continue
        if moment.weather and context.weather not in moment.weather:
            continue
        if not set(moment.required_flags).issubset(context.flags):
            continue
        if set(moment.forbidden_flags).intersection(context.flags):
            continue
        if moment.once and moment.flag_key in context.flags:
            continue
        eligible.append(moment)
    return tuple(sorted(eligible, key=lambda m: (-m.weight, m.key)))


def choose_trademark_moment(context: TrademarkContext, moments: Iterable[TrademarkMoment] = MOMENTS) -> TrademarkMoment | None:
    """Deterministic director: highest-priority eligible beat wins.

    Runtime integrations can add pacing before calling this function. Keeping
    selection deterministic makes authored moments easy to test and prevents
    random spam from becoming part of player progression.
    """
    eligible = eligible_moments(context, moments)
    return eligible[0] if eligible else None


def record_trademark_moment(database, character_id: int, moment: TrademarkMoment) -> None:
    if moment.once:
        database.grant_flag(character_id, moment.flag_key)
