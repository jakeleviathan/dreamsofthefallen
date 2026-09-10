from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Iterable

from mud.room_engine import PersistenceScope, RoomStateStore


HUMAN_REGION_KEY = "human_kingdom"
HUMAN_DISTRICT_ROOMS: tuple[str, ...] = (
    "human_demon_gate",
    "human_ashen_way",
    "human_cathedral_square",
    "human_grand_cathedral",
    "human_outer_drill_road",
    "human_training_yard",
    "human_practice_ring",
    "human_vermin_pens",
    "human_sootstairs",
    "human_cinder_lane",
    "human_blackglass_arch",
    "human_lantern_court",
)


@dataclass(frozen=True, slots=True)
class BusinessDefinition:
    key: str
    name: str
    proprietor: str
    proprietor_aliases: tuple[str, ...]
    room_key: str
    open_hour: int
    close_hour: int
    door_key: str
    aliases: tuple[str, ...]
    stock_item_keys: tuple[str, ...]
    storefront_description: str
    interior_glimpse: str
    smell: str
    sound: str
    greeting: str
    opening_event: str
    closing_event: str
    rain_event: str
    clearing_event: str
    rain_shutters: bool = True

    def scheduled_open(self, hour: int) -> bool:
        if self.open_hour == self.close_hour:
            return True
        if self.open_hour < self.close_hour:
            return self.open_hour <= hour < self.close_hour
        return hour >= self.open_hour or hour < self.close_hour

    @property
    def hours_text(self) -> str:
        return f"{self.open_hour:02d}:00-{self.close_hour:02d}:00"

    def matches(self, text: str) -> bool:
        normalized = text.strip().lower()
        values = {
            self.key.replace("_", " "),
            self.name.lower(),
            self.proprietor.lower(),
            *(alias.lower() for alias in self.aliases),
            *(alias.lower() for alias in self.proprietor_aliases),
        }
        return normalized in values


BLACK_LANTERN_PROVISIONS = BusinessDefinition(
    key="black_lantern_provisions",
    name="Black Lantern Provisions",
    proprietor="Edda Vane",
    proprietor_aliases=("edda", "vane", "shopkeeper", "proprietor", "merchant"),
    room_key="human_ashen_way",
    open_hour=6,
    close_hour=22,
    door_key="black_lantern_provisions_door",
    aliases=("black lantern", "provisions", "provisioner", "shop", "store", "storefront", "door", "shutters"),
    stock_item_keys=("spring_water", "grain_alcohol", "bone_chips", "greenleaf"),
    storefront_description=(
        "A narrow provisioner's shop occupies the ground floor beneath a black glass lantern. Its shelves press close to the front windows: "
        "bottles, wrapped herbs, lamp oil, cheap reagents, and practical goods for people leaving the city."
    ),
    interior_glimpse=(
        "Inside, every inch of wall is shelved. Bundles of herbs hang from ceiling hooks above barrels, stoppered bottles, waxed paper parcels, and a locked reagent cabinet."
    ),
    smell="lamp oil, dried herbs, grain alcohol, and cedar packing shavings",
    sound="glass stoppers clicking, paper wrapping, and Edda Vane's quick mental arithmetic under her breath",
    greeting="Edda Vane looks up from a ledger. 'If you're leaving the walls, buy what you forgot before the road reminds you.'",
    opening_event="Edda Vane unbolts Black Lantern Provisions and turns the black glass lamp over the door to its bright side.",
    closing_event="Edda Vane turns the black lantern dark, draws the door shut, and slides two heavy bolts into place.",
    rain_event="At Black Lantern Provisions, Edda Vane leans outside just long enough to pull the rain shutters nearly closed over the merchandise windows.",
    clearing_event="Edda Vane pushes Black Lantern Provisions' rain shutters wide again, letting the street light back across the shelves.",
)

SAINT_ORRAS_REMEDIES = BusinessDefinition(
    key="saint_orras_remedies",
    name="Saint Orra's Remedies",
    proprietor="Mirel Quill",
    proprietor_aliases=("mirel", "quill", "apothecary", "proprietor", "merchant"),
    room_key="human_cathedral_square",
    open_hour=7,
    close_hour=20,
    door_key="saint_orras_remedies_door",
    aliases=("saint orra", "remedies", "apothecary", "shop", "store", "storefront", "door", "shutters"),
    stock_item_keys=("greenleaf", "bitterroot", "lavender_blossom", "spring_water", "lavender_essential_oil"),
    storefront_description=(
        "A compact apothecary beneath a weathered stone saint faces the square. Bundled herbs and small blue bottles fill the mullioned window around a painted hand-and-flower sign."
    ),
    interior_glimpse=(
        "The shop beyond is clean and almost clerical: labeled drawers, hanging roots, polished glassware, drying racks, and a narrow consultation counter scrubbed pale with use."
    ),
    smell="lavender, bitterroot, clean alcohol, beeswax, and faint incense drifting in from the cathedral",
    sound="a mortar turning steadily against stone and the soft clink of bottles being sorted into wooden racks",
    greeting="Mirel Quill wipes a pestle clean. 'Simple remedies first. Miracles are across the square, and they charge in other ways.'",
    opening_event="Mirel Quill opens Saint Orra's Remedies and sets fresh bundles of greenleaf beside the painted window sign.",
    closing_event="The herb bundles disappear from Saint Orra's window as Mirel Quill locks the apothecary for the night.",
    rain_event="Mirel Quill lowers the apothecary's slatted rain shutters, leaving only the painted hand-and-flower sign visible.",
    clearing_event="Saint Orra's slatted shutters rise again and the blue glass bottles return to the light.",
)

QUARTERMASTERS_CAGE = BusinessDefinition(
    key="quartermasters_cage",
    name="The Quartermaster's Cage",
    proprietor="Dain Rusk",
    proprietor_aliases=("dain", "rusk", "quartermaster", "proprietor", "merchant"),
    room_key="human_training_yard",
    open_hour=5,
    close_hour=21,
    door_key="quartermasters_cage_door",
    aliases=("quartermaster's cage", "quartermasters cage", "cage", "supply cage", "shop", "store", "door"),
    stock_item_keys=("starter_weapon", "iron_dagger", "iron_sword", "bone_chips"),
    storefront_description=(
        "An iron-mesh supply cage is built into the yard wall beneath a painted inventory board. Weapon bundles, practice blades, straps, and replacement gear sit behind a waist-high issue counter."
    ),
    interior_glimpse=(
        "Beyond the mesh, everything has a hook, chalk number, or inventory tag. Even broken practice weapons are stacked by repair category rather than discarded."
    ),
    smell="oiled leather, iron filings, chalk, sweat, and the sharp soap used on training equipment",
    sound="metal hooks ringing against mesh, inventory boards being chalked, and Dain Rusk calling terse numbers to trainees",
    greeting="Dain Rusk gives you a measuring look. 'Break city equipment and I remember. Buy your own and I only remember if it's interesting.'",
    opening_event="Dain Rusk rolls up the iron shutter on the Quartermaster's Cage and begins counting weapon bundles without looking at the tally sheet.",
    closing_event="The Quartermaster's Cage rattles shut as Dain Rusk chains the iron screen and carries the day's ledger away.",
    rain_event="Dain Rusk drops a canvas awning over the Quartermaster's Cage, protecting the issue counter while leaving the iron service window open.",
    clearing_event="The Quartermaster's Cage awning is rolled back against the wall as the rain passes.",
)

CINDERHOOK_SALVAGE = BusinessDefinition(
    key="cinderhook_salvage",
    name="Cinderhook Salvage",
    proprietor="Nessa Pike",
    proprietor_aliases=("nessa", "pike", "salvager", "proprietor", "merchant"),
    room_key="human_cinder_lane",
    open_hour=9,
    close_hour=19,
    door_key="cinderhook_salvage_door",
    aliases=("cinderhook", "salvage", "salvage shop", "shop", "store", "storefront", "door", "shutters"),
    stock_item_keys=("iron_ore", "coal", "raw_cotton", "bone_chips"),
    storefront_description=(
        "Cinderhook Salvage hides behind a scarred red door between two workshops. Hooks, hinges, short lengths of chain, cracked fittings, and sorted scrap hang outside beneath a hand-painted black hook."
    ),
    interior_glimpse=(
        "The interior is organized chaos: shallow bins of useful metal, folded cloth remnants, reclaimed fittings, jars of odd components, and a back wall reserved for things Nessa Pike has not identified yet."
    ),
    smell="coal dust, wet iron, old cloth, machine grease, and strong black tea",
    sound="scrap being sorted by weight, chain settling in hooks, and the occasional decisive bang of something being tested for soundness",
    greeting="Nessa Pike taps one finger against a tray of sorted hardware. 'New is expensive. Broken is cheap. Useful is somewhere in between.'",
    opening_event="Nessa Pike drags Cinderhook Salvage's red door open and hangs the black-hook sign over the lane.",
    closing_event="Nessa Pike gathers the hanging scrap inside, locks Cinderhook's red door, and leaves the black-hook sign facing the wall.",
    rain_event="Nessa Pike snaps Cinderhook Salvage's patched metal shutters closed over the low display windows before the rain can reach the sorted scrap.",
    clearing_event="With the rain easing, Cinderhook's patched shutters scrape open and Nessa Pike resumes hanging salvage outside.",
)


HUMAN_BUSINESSES: tuple[BusinessDefinition, ...] = (
    BLACK_LANTERN_PROVISIONS,
    SAINT_ORRAS_REMEDIES,
    QUARTERMASTERS_CAGE,
    CINDERHOOK_SALVAGE,
)
HUMAN_BUSINESSES_BY_KEY = {business.key: business for business in HUMAN_BUSINESSES}
HUMAN_BUSINESSES_BY_ROOM = {business.room_key: business for business in HUMAN_BUSINESSES}


@dataclass(frozen=True, slots=True)
class DistrictEvent:
    room_keys: tuple[str, ...]
    text: str
    category: str


class HumanDistrictService:
    """Real-time civic schedule for the Human starting district.

    Business doors are shared world state. Rain shutters are temporary derived
    state. Bells and guard shifts are ambient events broadcast only to players
    who are physically in affected rooms.
    """

    guard_shift_hours = frozenset({6, 14, 22})
    guard_rooms = (
        "human_demon_gate",
        "human_outer_drill_road",
        "human_training_yard",
    )

    def __init__(self) -> None:
        self.last_hour: int | None = None
        self.last_weather: str | None = None
        self.last_business_schedule: dict[str, bool] = {}

    def business_in_room(self, room_key: str) -> BusinessDefinition | None:
        return HUMAN_BUSINESSES_BY_ROOM.get(room_key)

    def find_business(self, room_key: str, target: str = "") -> BusinessDefinition | None:
        business = self.business_in_room(room_key)
        if business is None:
            return None
        if not target.strip():
            return business
        return business if business.matches(target) else None

    def is_open(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> bool:
        door = state.door_state(business.door_key)
        return business.scheduled_open(hour) and door.open and not door.locked

    def shutters_closed(self, business: BusinessDefinition, state: RoomStateStore) -> bool:
        flag = f"{business.key}_rain_shutters_closed"
        return flag in state.flags_for(business.room_key, PersistenceScope.TEMPORARY)

    def _set_shutters(self, business: BusinessDefinition, state: RoomStateStore, closed: bool) -> None:
        if not business.rain_shutters:
            return
        state.set_flag(
            business.room_key,
            f"{business.key}_rain_shutters_closed",
            closed,
            PersistenceScope.TEMPORARY,
        )

    def initialize(self, now: datetime, state: RoomStateStore) -> None:
        self.last_hour = now.hour
        self.last_weather = state.weather_for(HUMAN_REGION_KEY)
        self.last_business_schedule.clear()
        for business in HUMAN_BUSINESSES:
            scheduled_open = business.scheduled_open(now.hour)
            self.last_business_schedule[business.key] = scheduled_open
            state.set_door(
                business.door_key,
                open=scheduled_open,
                locked=not scheduled_open,
            )
            self._set_shutters(
                business,
                state,
                self.last_weather in {"rain", "storm", "thunderstorm"},
            )

    def sync(self, now: datetime, state: RoomStateStore) -> tuple[DistrictEvent, ...]:
        events: list[DistrictEvent] = []
        hour = now.hour
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
                    f"The Grand Cathedral answers the hour with {bell_count} deep {stroke_word}, each note rolling through the stone streets.",
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
            scheduled_open = business.scheduled_open(hour)
            previous = self.last_business_schedule.get(business.key)
            door = state.door_state(business.door_key)

            if previous is None or scheduled_open != previous:
                state.set_door(
                    business.door_key,
                    open=scheduled_open,
                    locked=not scheduled_open,
                )
                events.append(
                    DistrictEvent(
                        (business.room_key,),
                        business.opening_event if scheduled_open else business.closing_event,
                        "business_open" if scheduled_open else "business_close",
                    )
                )
            elif scheduled_open:
                # Shopkeepers do not let a passer-by leave their business shut
                # during posted hours. A player may close the door briefly, but
                # the proprietor will restore normal operation on the next tick.
                if door.locked or not door.open:
                    state.set_door(business.door_key, open=True, locked=False)
                    events.append(
                        DistrictEvent(
                            (business.room_key,),
                            f"{business.proprietor} notices the closed door and opens {business.name} again for business.",
                            "business_reopen",
                        )
                    )
            else:
                if door.open or not door.locked:
                    state.set_door(business.door_key, open=False, locked=True)

            self.last_business_schedule[business.key] = scheduled_open

        rainy = weather in {"rain", "storm", "thunderstorm"}
        was_rainy = self.last_weather in {"rain", "storm", "thunderstorm"}
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
        self.last_weather = weather
        return tuple(events)

    def storefront_lines(self, room_key: str, state: RoomStateStore, hour: int) -> tuple[str, ...]:
        business = self.business_in_room(room_key)
        if business is None:
            return ()
        door = state.door_state(business.door_key)
        scheduled = business.scheduled_open(hour)
        shutters = self.shutters_closed(business, state)

        if scheduled and door.open and not door.locked:
            status = f"{business.name} is OPEN ({business.hours_text}). {business.proprietor} is working the counter."
            atmosphere = f"From the open doorway come the smell of {business.smell}; you hear {business.sound}."
            if shutters:
                atmosphere += " Its rain shutters are drawn in against the weather, muting the light from the street."
            return (status, atmosphere)

        if scheduled and not door.locked:
            return (
                f"{business.name} should be open ({business.hours_text}), but its door is presently closed. {business.proprietor} is visible inside.",
            )

        return (
            f"{business.name} is CLOSED and locked. Posted hours: {business.hours_text}.",
        )

    def examine(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        door = state.door_state(business.door_key)
        text = business.storefront_description
        if business.scheduled_open(hour) and door.open and not door.locked:
            text += " " + business.interior_glimpse
        else:
            text += " The entrance is secured for the closed hours."
        if self.shutters_closed(business, state):
            text += " Rain shutters cover most of the display openings."
        return text

    def listen(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        if self.is_open(business, state, hour):
            return f"From {business.name} you hear {business.sound}."
        return f"{business.name} is closed; only the street and the occasional settling creak of the storefront answer you."

    def smell(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        if self.is_open(business, state, hour):
            return f"The air around {business.name} carries {business.smell}."
        return f"With {business.name} closed, only a faint trace of {business.smell} remains near the door."

    def talk(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        if not self.is_open(business, state, hour):
            return f"{business.proprietor} is not available; {business.name} is closed."
        return business.greeting

    def shop_lines(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> tuple[str, ...]:
        if not self.is_open(business, state, hour):
            return (
                f"{business.name} is closed. Posted hours: {business.hours_text}.",
            )
        return (
            f"--- {business.name} ---",
            f"Proprietor: {business.proprietor}",
            f"Hours: {business.hours_text}",
            *business.stock_item_keys,
        )

    def open_door(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        door = state.door_state(business.door_key)
        if not business.scheduled_open(hour):
            state.set_door(business.door_key, open=False, locked=True)
            return f"{business.name}'s door is locked for the night. Posted hours: {business.hours_text}."
        if door.locked:
            return f"{business.name}'s door is locked from inside."
        if door.open:
            return f"{business.name}'s door is already open."
        state.set_door(business.door_key, open=True, locked=False)
        return f"You open the door to {business.name}."

    def close_door(self, business: BusinessDefinition, state: RoomStateStore, hour: int) -> str:
        door = state.door_state(business.door_key)
        if not door.open:
            return f"{business.name}'s door is already closed."
        state.set_door(business.door_key, open=False, locked=not business.scheduled_open(hour))
        if business.scheduled_open(hour):
            return f"You pull {business.name}'s door closed. {business.proprietor} gives you a look that suggests it will not stay that way for long."
        return f"You close {business.name}'s door. The lock catches from within."

    async def run(
        self,
        state: RoomStateStore,
        broadcast: Callable[[DistrictEvent], Awaitable[None]],
        *,
        now_provider: Callable[[], datetime] = datetime.now,
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


HUMAN_DISTRICT = HumanDistrictService()
