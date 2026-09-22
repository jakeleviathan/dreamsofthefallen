"""Small, observable daily-life layer for Waymeet's two established merchants.

Movement is owned by MobileNpcManager; this module only resolves the shared
static/mobile identity and produces sparse, local, weather-aware conversation.
There is no background AI service and no fabricated global chat: players hear a
line only when they actually share a room with its speaker(s).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from mud.waymeet_frontier import (
    BROKER_KEY,
    PROVISIONER_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_WEST_ROAD_KEY,
)


ROAMING_MERCHANT_KEYS = frozenset((BROKER_KEY, PROVISIONER_KEY))
WAYMEET_SOCIAL_ROOMS = frozenset((
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CRAFT_ROW_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_WEST_ROAD_KEY,
))
SHELTER_WEATHERS = frozenset(("rain", "storm", "thunderstorm", "snow", "duststorm"))


def static_actor_is_visible(session, npc_key: str, room_key: str) -> bool:
    """A static merchant is only a fallback when no mobile copy is running.

    This leaves authored NPCs, merchant definitions, the static-talkability
    audit, and standalone tests intact while letting the live server use the
    *same identity* for the physically scheduled actor.
    """
    if npc_key not in ROAMING_MERCHANT_KEYS:
        return True
    manager = getattr(session, "mobile_npcs", None)
    state = getattr(manager, "states", {}).get(npc_key)
    return state is None or (
        state.active and state.current_room_key == room_key
    )


@dataclass(frozen=True, slots=True)
class WaymeetChatter:
    room_key: str
    text: str


# Text describes observable work, relationships, time and weather, rather
# than a disembodied rumor generator. It deliberately does not grant quests,
# change merchant inventory, or interrupt combat.
_PAIR_LINES = (
    "Vekk flips a worn trade chit across a barrel. 'You still owe me for the rope.' Sevra sends it back. 'And you still owe me for the cart that rope saved.'",
    "Sevra checks a bundle of thread against Vekk's tally. 'You count supplies like they'll walk off.' Vekk replies, 'That's because they keep doing it.'",
    "Vekk asks whether the western caravan is overdue. Sevra answers without looking up: 'Only if you promised them an honest arrival time.'",
)
_PAIR_RAIN = (
    "Vekk wrings rainwater from his sleeve. 'There goes the dry-road price.' Sevra slides his ledger away from the drips. 'There goes your handwriting, more like.'",
    "Sevra sets two damp sacks beside the hearth. 'Next storm, we move the spare stock before the first drop.' Vekk says, 'You said that last storm.'",
    "Vekk listens to the rain battering the awnings. 'No one's buying ore in this.' Sevra replies, 'They will when the road opens again. Count it while we wait.'",
)
_VEKK_LINES = {
    "morning": (
        "Vekk lifts the market awning and begins sorting yesterday's returns into tomorrow's useful things.",
        "Vekk checks the west road between customers. 'First wagons usually bring the best stories. Worst axle repairs, though.'",
    ),
    "day": (
        "Vekk works through a crate of rope and iron, quietly arguing with his own inventory.",
        "Vekk calls over the clatter of wheels, 'Ore, thread, a little common sense. I can only promise two of those.'",
    ),
    "evening": (
        "Vekk counts trade chits by lanternlight, leaving one small pile for repairs along the road.",
        "Vekk gathers loose straps before the lamps burn low. 'Anything left out overnight belongs to the weather.'",
    ),
    "night": (
        "Vekk closes his ledger and tells a passing traveler about the caravan that once arrived with three fewer wheels than it left with.",
        "Vekk rubs his tired hands near the commonhouse fire. 'You can trade all day, but you can't buy a good night's road.'",
    ),
}
_SEVRA_LINES = {
    "morning": (
        "Sevra checks the stitching on a canvas sack, then sets aside the ones unlikely to survive the next trip.",
        "Sevra carries fresh stock toward the market. 'If Vekk has sold the labels again, I swear...'",
    ),
    "day": (
        "Sevra tests the weight of a newly worked ingot. 'Buy the thing that lasts. Saves us both an argument later.'",
        "Sevra inspects the communal worktables and gathers a neat stack of finished thread.",
    ),
    "evening": (
        "Sevra makes one final count of the processed stock before carrying the ledger toward the commonhouse.",
        "Sevra straightens a crooked display and mutters, 'Five minutes' work prevents an hour of explanations.'",
    ),
    "night": (
        "Sevra sits beside the commonhouse fire repairing a frayed strap someone swore was beyond saving.",
        "Sevra puts down her tally and finally joins the conversation about which road has the worst inns.",
    ),
}
_VEKK_RAIN = (
    "Vekk peers toward the dripping market awnings. 'No use keeping good stock in weather that can ruin it.'",
    "Vekk hangs a sodden coat by the hearth and starts planning which wagons will need new rope after the storm.",
)
_SEVRA_RAIN = (
    "Sevra pulls a crate away from the runoff. 'Dry the thread first. Then we'll argue about the price.'",
    "Sevra sorts the weatherproof bundles under cover, keeping the damaged ones aside for repairs.",
)


def _phase(hour: int) -> str:
    if 5 <= hour < 9:
        return "morning"
    if 9 <= hour < 18:
        return "day"
    if 18 <= hour < 22:
        return "evening"
    return "night"


class WaymeetDailyLife:
    """Produces at most one local conversation per room per cooldown.

    Call every 15 real seconds after the movement manager has ticked. One
    conversation a minute per occupied room is enough to suggest real routines
    without flooding combat and command output. No players, no chatter.
    """

    def __init__(self, *, cooldown_ticks: int = 4) -> None:
        if cooldown_ticks < 1:
            raise ValueError("Chatter cooldown must be positive")
        self.cooldown_ticks = cooldown_ticks
        self._tick = 0
        self._last_room_tick: dict[str, int] = {}
        self._line_index: dict[tuple[str, str], int] = {}

    def _next(self, room_key: str, category: str, lines: tuple[str, ...]) -> str:
        key = (room_key, category)
        index = self._line_index.get(key, 0)
        self._line_index[key] = index + 1
        return lines[index % len(lines)]

    def tick(
        self,
        manager,
        *,
        hour: int,
        weather: str,
        player_room_keys: Iterable[str],
    ) -> tuple[WaymeetChatter, ...]:
        self._tick += 1
        occupied = WAYMEET_SOCIAL_ROOMS.intersection(player_room_keys)
        if not occupied or manager is None:
            return ()

        events: list[WaymeetChatter] = []
        rainy = str(weather).lower() in SHELTER_WEATHERS
        for room_key in sorted(occupied):
            if self._tick - self._last_room_tick.get(room_key, -self.cooldown_ticks) < self.cooldown_ticks:
                continue
            present = {
                state.definition.key
                for state in manager.npcs_in_room(room_key)
                if state.definition.key in ROAMING_MERCHANT_KEYS
            }
            if not present:
                continue
            if present == ROAMING_MERCHANT_KEYS:
                category = "pair_rain" if rainy else "pair"
                lines = _PAIR_RAIN if rainy else _PAIR_LINES
            else:
                is_vekk = BROKER_KEY in present
                category = ("vekk" if is_vekk else "sevra") + (
                    "_rain" if rainy else "_" + _phase(hour)
                )
                if rainy:
                    lines = _VEKK_RAIN if is_vekk else _SEVRA_RAIN
                else:
                    lines = (_VEKK_LINES if is_vekk else _SEVRA_LINES)[_phase(hour)]
            self._last_room_tick[room_key] = self._tick
            events.append(WaymeetChatter(room_key, self._next(room_key, category, lines)))
        return tuple(events)
