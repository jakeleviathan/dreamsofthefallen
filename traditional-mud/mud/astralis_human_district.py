from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment, RAINY_WEATHER
from mud.human_district import (
    DistrictEvent,
    HUMAN_BUSINESSES,
    HUMAN_BUSINESSES_BY_ROOM,
    HUMAN_DISTRICT_ROOMS,
    HUMAN_REGION_KEY,
    BusinessDefinition,
    HumanDistrictService,
)
from mud.room_engine import PersistenceScope, RoomStateStore


class AstralisHumanDistrictService(HumanDistrictService):
    """Human civic life driven by the accelerated Astralis world clock.

    Posted hours remain stable public information. A small deterministic daily
    variation gives proprietors personality without changing every tick. Heavy
    storms add stronger leeway for civilian shops. The Quartermaster's Cage is
    intentionally more reliable because the training yard depends on it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.last_day_number: int | None = None

    @staticmethod
    def _daily_variation(business: BusinessDefinition, day_number: int) -> tuple[int, int]:
        # Stable for the entire Astralis day: no random flickering.
        seed = sum((index + 1) * ord(char) for index, char in enumerate(business.key)) + day_number * 131
        open_delay = 1 if seed % 7 == 0 else 0
        close_early = 1 if (seed // 7) % 7 == 0 else 0
        return open_delay, close_early

    def effective_hours(
        self,
        business: BusinessDefinition,
        day_number: int,
        weather: str,
    ) -> tuple[int, int]:
        open_delay, close_early = self._daily_variation(business, day_number)
        if weather in {"storm", "thunderstorm"} and business.key != "quartermasters_cage":
            open_delay += 1
            close_early += 1
        open_hour = (business.open_hour + open_delay) % 24
        close_hour = (business.close_hour - close_early) % 24
        return open_hour, close_hour

    def effective_hours_text(self, business: BusinessDefinition, day_number: int, weather: str) -> str:
        open_hour, close_hour = self.effective_hours(business, day_number, weather)
        if (open_hour, close_hour) == (business.open_hour, business.close_hour):
            return business.hours_text
        return f"{open_hour:02d}:00-{close_hour:02d}:00 today (posted {business.hours_text})"

    def effective_scheduled_open(
        self,
        business: BusinessDefinition,
        hour: int,
        day_number: int,
        weather: str,
    ) -> bool:
        open_hour, close_hour = self.effective_hours(business, day_number, weather)
        if open_hour == close_hour:
            return True
        if open_hour < close_hour:
            return open_hour <= hour < close_hour
        return hour >= open_hour or hour < close_hour

    def _day(self, day_number: int | None = None) -> int:
        if day_number is not None:
            return day_number
        if self.last_day_number is not None:
            return self.last_day_number
        return ASTRALIS_CLOCK.now().day_number

    def is_open(
        self,
        business: BusinessDefinition,
        state: RoomStateStore,
        hour: int,
        day_number: int | None = None,
    ) -> bool:
        day = self._day(day_number)
        weather = state.weather_for(HUMAN_REGION_KEY)
        door = state.door_state(business.door_key)
        return self.effective_scheduled_open(business, hour, day, weather) and door.open and not door.locked

    def initialize(self, now: AstralisMoment, state: RoomStateStore) -> None:
        self.last_hour = now.hour
        self.last_day_number = now.day_number
        self.last_weather = state.weather_for(HUMAN_REGION_KEY)
        self.last_business_schedule.clear()
        for business in HUMAN_BUSINESSES:
            scheduled_open = self.effective_scheduled_open(
                business, now.hour, now.day_number, self.last_weather
            )
            self.last_business_schedule[business.key] = scheduled_open
            state.set_door(business.door_key, open=scheduled_open, locked=not scheduled_open)
            self._set_shutters(business, state, self.last_weather in RAINY_WEATHER)

    def sync(self, now: AstralisMoment, state: RoomStateStore) -> tuple[DistrictEvent, ...]:
        events: list[DistrictEvent] = []
        hour = now.hour
        day = now.day_number
        weather = state.weather_for(HUMAN_REGION_KEY)

        if self.last_hour is None:
            self.initialize(now, state)
            return ()

        if hour != self.last_hour:
            bell_count = ((hour - 1) % 12) + 1
            stroke_word = "stroke" if bell_count == 1 else "strokes"
            events.append(
                DistrictEvent(
                    HUMAN_DISTRICT_ROOMS,
                    f"The Grand Cathedral answers the Astralis hour with {bell_count} deep {stroke_word}, each note rolling through the stone streets.",
                    "cathedral_bell",
                )
            )
            if hour in self.guard_shift_hours:
                events.append(
                    DistrictEvent(
                        self.guard_rooms,
                        "A watch sergeant's whistle cuts across the district. Boots answer from the wall road as one Blackwall Guard shift formally relieves another.",
                        "guard_shift",
                    )
                )

        for business in HUMAN_BUSINESSES:
            scheduled_open = self.effective_scheduled_open(business, hour, day, weather)
            previous = self.last_business_schedule.get(business.key)
            door = state.door_state(business.door_key)

            if previous is None or scheduled_open != previous:
                state.set_door(business.door_key, open=scheduled_open, locked=not scheduled_open)
                if scheduled_open:
                    text = business.opening_event
                else:
                    text = business.closing_event
                    if weather in {"storm", "thunderstorm"} and hour < business.close_hour:
                        text += " The worsening storm has pushed the closing earlier than the posted schedule."
                events.append(
                    DistrictEvent(
                        (business.room_key,),
                        text,
                        "business_open" if scheduled_open else "business_close",
                    )
                )
            elif scheduled_open:
                if door.locked or not door.open:
                    state.set_door(business.door_key, open=True, locked=False)
                    events.append(
                        DistrictEvent(
                            (business.room_key,),
                            f"{business.proprietor} notices the closed door and opens {business.name} again for business.",
                            "business_reopen",
                        )
                    )
            elif door.open or not door.locked:
                state.set_door(business.door_key, open=False, locked=True)

            self.last_business_schedule[business.key] = scheduled_open

        rainy = weather in RAINY_WEATHER
        was_rainy = self.last_weather in RAINY_WEATHER
        if weather != self.last_weather and rainy != was_rainy:
            for business in HUMAN_BUSINESSES:
                if not business.rain_shutters:
                    continue
                self._set_shutters(business, state, rainy)
                events.append(
                    DistrictEvent(
                        (business.room_key,),
                        business.rain_event if rainy else business.clearing_event,
                        "rain_shutters_close" if rainy else "rain_shutters_open",
                    )
                )

        self.last_hour = hour
        self.last_day_number = day
        self.last_weather = weather
        return tuple(events)

    def storefront_lines(
        self,
        room_key: str,
        state: RoomStateStore,
        hour: int,
        day_number: int | None = None,
    ) -> tuple[str, ...]:
        business = HUMAN_BUSINESSES_BY_ROOM.get(room_key)
        if business is None:
            return ()
        day = self._day(day_number)
        weather = state.weather_for(HUMAN_REGION_KEY)
        door = state.door_state(business.door_key)
        scheduled = self.effective_scheduled_open(business, hour, day, weather)
        shutters = self.shutters_closed(business, state)
        hours = self.effective_hours_text(business, day, weather)

        if scheduled and door.open and not door.locked:
            status = f"{business.name} is OPEN ({hours}). {business.proprietor} is working the counter."
            atmosphere = f"From the open doorway come the smell of {business.smell}; you hear {business.sound}."
            if shutters:
                atmosphere += " Its rain shutters are drawn in against the weather, muting the light from the street."
            return (status, atmosphere)
        if scheduled and not door.locked:
            return (f"{business.name} should be open ({hours}), but its door is presently closed. {business.proprietor} is visible inside.",)
        return (f"{business.name} is CLOSED and locked. Today's hours: {hours}.",)

    def examine(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        door = state.door_state(business.door_key)
        text = business.storefront_description
        if self.is_open(business, state, hour, day_number):
            text += " " + business.interior_glimpse
        else:
            text += " The entrance is secured for the current closed hours."
        if self.shutters_closed(business, state):
            text += " Rain shutters cover most of the display openings."
        return text

    def listen(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        if self.is_open(business, state, hour, day_number):
            return f"From {business.name} you hear {business.sound}."
        return f"{business.name} is closed; only the street and the occasional settling creak of the storefront answer you."

    def smell(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        if self.is_open(business, state, hour, day_number):
            return f"The air around {business.name} carries {business.smell}."
        return f"With {business.name} closed, only a faint trace of {business.smell} remains near the door."

    def talk(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        if not self.is_open(business, state, hour, day_number):
            return f"{business.proprietor} is not available; {business.name} is closed."
        return business.greeting

    def shop_lines(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> tuple[str, ...]:
        day = self._day(day_number)
        weather = state.weather_for(HUMAN_REGION_KEY)
        hours = self.effective_hours_text(business, day, weather)
        if not self.is_open(business, state, hour, day):
            return (f"{business.name} is closed. Today's hours: {hours}.",)
        return (
            f"--- {business.name} ---",
            f"Proprietor: {business.proprietor}",
            f"Hours: {hours}",
            *business.stock_item_keys,
        )

    def open_door(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        day = self._day(day_number)
        weather = state.weather_for(HUMAN_REGION_KEY)
        door = state.door_state(business.door_key)
        if not self.effective_scheduled_open(business, hour, day, weather):
            state.set_door(business.door_key, open=False, locked=True)
            hours = self.effective_hours_text(business, day, weather)
            return f"{business.name}'s door is locked. Today's hours: {hours}."
        if door.locked:
            return f"{business.name}'s door is locked from inside."
        if door.open:
            return f"{business.name}'s door is already open."
        state.set_door(business.door_key, open=True, locked=False)
        return f"You open the door to {business.name}."

    def close_door(self, business: BusinessDefinition, state: RoomStateStore, hour: int, day_number: int | None = None) -> str:
        day = self._day(day_number)
        weather = state.weather_for(HUMAN_REGION_KEY)
        door = state.door_state(business.door_key)
        if not door.open:
            return f"{business.name}'s door is already closed."
        scheduled = self.effective_scheduled_open(business, hour, day, weather)
        state.set_door(business.door_key, open=False, locked=not scheduled)
        if scheduled:
            return f"You pull {business.name}'s door closed. {business.proprietor} gives you a look that suggests it will not stay that way for long."
        return f"You close {business.name}'s door. The lock catches from within."

    async def run(
        self,
        state: RoomStateStore,
        broadcast: Callable[[DistrictEvent], Awaitable[None]],
        *,
        now_provider: Callable[[], AstralisMoment] = ASTRALIS_CLOCK.now,
        interval_seconds: float = 5.0,
    ) -> None:
        if self.last_hour is None:
            self.initialize(now_provider(), state)
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                for event in self.sync(now_provider(), state):
                    await broadcast(event)
        except asyncio.CancelledError:
            return


HUMAN_DISTRICT = AstralisHumanDistrictService()
