from __future__ import annotations

"""Veilith's optional level-25 opening: a physical place, not a hallucination.

This is deliberately an opening slice, not the complete higher-level dungeon.
There are no friendly inhabitants or combat encounters in the Silver Expanse.
"""

from dataclasses import replace, is_dataclass
from time import monotonic

import mud.crafting as crafting
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.salt_kingdoms_midgame import TIDEMARK_SINK_KEY
from mud.world import RoomDefinition


REGION_KEY = "veilith"
LAB_KEY = "veilith_abandoned_alchemist_lab"
FIELD_KEY = "veilith_silver_expanse"
CAUSEWAY_KEY = "veilith_light_causeway"
STILLPOINT_KEY = "veilith_stillpoint"
ROOM_KEYS = (LAB_KEY, FIELD_KEY, CAUSEWAY_KEY, STILLPOINT_KEY)
VEILITH_ROOM_KEYS = (FIELD_KEY, CAUSEWAY_KEY, STILLPOINT_KEY)

DISCOVERED_LAB_FLAG = "veilith_hidden_lab_discovered"
NOTES_FLAG = "veilith_formula_read"
ENTERED_FLAG = "veilith_first_crossing"
ATTUNED_FLAG = "veilith_attuned"
DRAUGHT_KEY = "veilith_dreamless_draught"
DOSE_SECONDS = 600.0

DRAUGHT = ItemDefinition(
    key=DRAUGHT_KEY,
    name="Dreamless Draught",
    description=(
        "An experimental alchemical preparation intended to quiet nightmares. "
        "It changes perception without increasing health, mana, or combat power."
    ),
    category="recreational",
    tier=3,
)

ROOMS = (
    RoomDefinition(
        key=LAB_KEY,
        name="The Abandoned Sleep Laboratory",
        region_key=REGION_KEY,
        description=(
            "A salt-encrusted hollow has been fitted with careful glasswork. An empty cot "
            "faces a wall without a door. Someone left a notebook open beside a small "
            "distillation bench. The apparatus is clean, though nobody has tended it "
            "for years. The wall behind the cot is perfectly smooth."
        ),
        tags=("hidden_world", "optional_discovery", "level_25", "safe"),
    ),
    RoomDefinition(
        key=FIELD_KEY,
        name="The Silver Expanse",
        region_key=REGION_KEY,
        description=(
            "An immeasurable field of silver grass ripples beneath a lavender sky. "
            "Translucent flowers glow between the blades. Pale marble structures hang "
            "above a distant motionless sea. There is no wind, but every flower moves. "
            "A worn trail marker stands amid the grass. Nothing living greets you."
        ),
        tags=("planar", "hidden_world", "optional_dungeon", "level_25", "safe"),
    ),
    RoomDefinition(
        key=CAUSEWAY_KEY,
        name="The Unfinished Causeway",
        region_key=REGION_KEY,
        description=(
            "The grass ends at an expanse of open lavender air. A narrow ribbon of light "
            "holds your weight, but its next span is invisible. No wind rises from the "
            "distance below. The silver meadow waits behind you."
        ),
        tags=("planar", "hidden_world", "optional_dungeon", "level_25", "puzzle"),
    ),
    RoomDefinition(
        key=STILLPOINT_KEY,
        name="The Stillpoint",
        region_key=REGION_KEY,
        description=(
            "A round platform of white stone hangs above the silver field, unsupported "
            "and perfectly quiet. Pale grooves in the floor hold the pattern of the "
            "path you just crossed. For an instant, your shadow stays behind when you "
            "move. Farther into Veilith, silent architectures wait beyond a veil of haze."
        ),
        tags=("planar", "hidden_world", "optional_dungeon", "level_25", "safe", "opening_complete"),
    ),
)


def install_veilith_content(world_service=None) -> None:
    """Register real persistent room keys without a public map entrance."""
    if DRAUGHT_KEY not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (DRAUGHT,)
    crafting.ITEMS_BY_KEY[DRAUGHT_KEY] = DRAUGHT

    for room in ROOMS:
        if room.key in legacy_world.ROOMS_BY_KEY:
            legacy_world.ROOMS = tuple(room if previous.key == room.key else previous for previous in legacy_world.ROOMS)
        else:
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        legacy_world.ROOMS_BY_KEY[room.key] = room
        if world_service is not None:
            world_service.legacy_rooms[room.key] = room
            world_service._scene_cache.pop(room.key, None)


def _flags(session) -> frozenset[str]:
    return frozenset(session.database.list_flags(session.character.id))


def _remember(session, flag: str) -> None:
    if flag not in _flags(session):
        session.database.grant_flag(session.character.id, flag)


def _move(session, destination: str) -> None:
    session.database.set_character_room(session.character.id, destination)
    if is_dataclass(session.character):
        session.character = replace(session.character, current_room=destination)
    else:
        session.character.current_room = destination


def _has_perception(session) -> bool:
    return monotonic() < float(getattr(session, "_veilith_perception_until", 0.0))


def _normalize(command: str) -> str:
    return " ".join(command.casefold().strip().split())


async def _delegate(session, previous_prompt, command: str) -> None:
    had = "prompt" in session.__dict__
    old = session.__dict__.get("prompt")

    async def replay(_text=""):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had:
            session.prompt = old
        else:
            session.__dict__.pop("prompt", None)


def install_veilith_runtime(player_session_class, world_service) -> None:
    install_veilith_content(world_service)
    if getattr(player_session_class, "_veilith_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_show_current_room = player_session_class.show_current_room
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self):
        await previous_enter_character(self)
        # No temporary drug effect or puzzle timing survives a login.
        self._veilith_perception_until = 0.0
        self._veilith_field_ready = False
        self._veilith_span_ready = False

    async def show_current_room(self):
        await previous_show_current_room(self)
        if self.character is None:
            return
        room = self.character.current_room
        if room == TIDEMARK_SINK_KEY and self.character.level >= 25:
            await self.send("Two bands of dry salt meet in a hairline crack. The line looks deeper than the surrounding stone.\r\n")
        elif room == LAB_KEY:
            if ATTUNED_FLAG in _flags(self):
                await self.send("The featureless wall is visible to you as an open seam. ENTER SEAM or OUT.\r\n")
            elif _has_perception(self):
                await self.send("A slender seam of lavender light now cuts the blank wall. ENTER SEAM or OUT.\r\n")
            else:
                await self.send("The notebook and distillation bench remain intact. READ NOTES or OUT.\r\n")
        elif room == FIELD_KEY:
            if getattr(self, "_veilith_field_ready", False):
                await self.send("A ribbon of light has appeared to the EAST. WEST returns to the laboratory.\r\n")
            else:
                await self.send("A trail marker and a patch of translucent flowers stand nearby. LISTEN or WAIT.\r\n")
        elif room == CAUSEWAY_KEY:
            await self.send("The next span is invisible. WAIT for the light, EAST to cross, or WEST to retreat.\r\n")
        elif room == STILLPOINT_KEY:
            await self.send("The deeper dimension remains out of reach for now. WEST returns to the causeway, RETURN to the laboratory.\r\n")

    async def playing_prompt(self):
        if self.character is None:
            return await previous_playing_prompt(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        action = _normalize(command)
        room = self.character.current_room or ""

        if room == TIDEMARK_SINK_KEY and action in {"examine crack", "search crack", "search salt", "examine salt crack"}:
            if self.character.level < 25:
                await self.send("The salt breaks beneath your fingers. Nothing here offers a safe passage yet.\r\n")
                return
            _remember(self, DISCOVERED_LAB_FLAG)
            await self.send(
                "Behind the narrow split is a worked stone passage, hidden by salt deposits. "
                "It leads inward, not down. You could ENTER CRACK.\r\n"
            )
            return

        if room == TIDEMARK_SINK_KEY and action in {"enter crack", "enter passage"}:
            if self.character.level < 25 or DISCOVERED_LAB_FLAG not in _flags(self):
                await self.send("You find no passage through the salt.\r\n")
                return
            _move(self, LAB_KEY)
            await self.send("You slip sideways between the salt beds into an abandoned room.\r\n")
            return await self.show_current_room()

        if room == LAB_KEY:
            if action in {"out", "exit", "return salt", "leave lab"}:
                _move(self, TIDEMARK_SINK_KEY)
                await self.send("The salt passage closes into an ordinary crevice behind you.\r\n")
                return await self.show_current_room()
            if action in {"read notes", "read notebook", "examine notebook"}:
                _remember(self, NOTES_FLAG)
                await self.send(
                    "Three patients dreamed of the same silver meadow. One woke holding a flower "
                    "that has never grown on Astralis. The final page describes the Dreamless "
                    "Draught: an attempt to silence nightmares that instead reveals a real "
                    "overlapping place. The bench still holds enough reagent for another dose. "
                    "PREPARE DRAUGHT.\r\n"
                )
                return
            if action in {"prepare draught", "brew draught", "compound draught", "prepare dreamless draught"}:
                if NOTES_FLAG not in _flags(self):
                    await self.send("The glasswork is unfamiliar. The notebook might explain it.\r\n")
                    return
                if self.database.item_quantity(self.character.id, DRAUGHT_KEY) > 0:
                    await self.send("You already have a prepared Dreamless Draught.\r\n")
                    return
                self.database.add_item(self.character.id, DRAUGHT_KEY, 1)
                await self.send(
                    "You follow the abandoned formula using the reagents still in the bench. "
                    "One silver-clear Dreamless Draught settles into a phial.\r\n"
                )
                return
            if action in {"drink draught", "use draught", "drink dreamless draught", "use dreamless draught", "consume dreamless draught"}:
                if getattr(self, "active_enemy", None) is not None:
                    await self.send("You cannot prepare your senses while fighting.\r\n")
                    return
                if not self.database.consume_item(self.character.id, DRAUGHT_KEY, 1):
                    await self.send("You have no Dreamless Draught. READ NOTES and PREPARE DRAUGHT.\r\n")
                    return
                self._veilith_perception_until = monotonic() + DOSE_SECONDS
                await self.send(
                    "The draught is cool and almost tasteless. The room remains the same, "
                    "except a hairline of lavender light appears in the blank wall. "
                    "Your body has not left Astralis. ENTER SEAM.\r\n"
                )
                return
            if action in {"examine wall", "look wall", "examine seam", "look seam"}:
                if ATTUNED_FLAG in _flags(self) or _has_perception(self):
                    await self.send("A narrow doorway of lavender light occupies the smooth wall. ENTER SEAM.\r\n")
                else:
                    await self.send("The wall is perfectly smooth, with no door, lock, or joint.\r\n")
                return
            if action in {"enter seam", "enter doorway", "enter veilith"}:
                if ATTUNED_FLAG not in _flags(self) and not _has_perception(self):
                    await self.send("Your hand meets solid stone. The notebook mentions altered perception.\r\n")
                    return
                _remember(self, ENTERED_FLAG)
                self._veilith_field_ready = False
                self._veilith_span_ready = False
                _move(self, FIELD_KEY)
                await self.send(
                    "You step through the seam. The laboratory disappears without moving away. "
                    "Beneath an immense lavender sky lies the silver field from the notebook. "
                    "This is no dream.\r\n"
                )
                return await self.show_current_room()

        if room in VEILITH_ROOM_KEYS:
            if action in {"return", "return astralis", "go home", "leave veilith"} or (room == FIELD_KEY and action == "west"):
                _move(self, LAB_KEY)
                await self.send("You follow your own shadow home. The silver field closes behind you.\r\n")
                return await self.show_current_room()

            if action in {"exits", "exit"}:
                if room == FIELD_KEY:
                    ways = "EAST along the revealed ribbon, WEST to the laboratory" if getattr(self, "_veilith_field_ready", False) else "no visible forward path; WEST to the laboratory"
                elif room == CAUSEWAY_KEY:
                    ways = "EAST across the unformed span, WEST to the field"
                else:
                    ways = "WEST to the causeway, RETURN to the laboratory"
                await self.send(f"Visible ways: {ways}.\r\n")
                return

            if room == FIELD_KEY:
                if action in {"examine marker", "read marker", "look marker", "examine trail marker"}:
                    await self.send(
                        "The trail marker has the shape of a Waymeet milestone, but the lettering "
                        "is wrong. It reads WAYMEET. When you look again, it reads WAYMET. "
                        "No hand touched it.\r\n"
                    )
                    return
                if action in {"examine flowers", "look flowers", "touch flowers", "examine flower"}:
                    await self.send(
                        f"Every translucent flower turns toward you in the windless grass. "
                        f"A small voice, made of many petals, whispers '{self.character.name}'. "
                        "Nothing answers when you speak.\r\n"
                    )
                    return
                if action == "listen":
                    await self.send(
                        "A low hum rises through the soil and falls into time with your heartbeat. "
                        "Your last footstep answers half a beat late.\r\n"
                    )
                    return
                if action in {"wait", "stand still", "be still"}:
                    self._veilith_field_ready = True
                    await self.send(
                        "You stand motionless. Grass that has no wind parts in a straight line. "
                        "A delicate causeway of light takes shape to the EAST.\r\n"
                    )
                    return
                if action in {"east", "e"}:
                    if not getattr(self, "_veilith_field_ready", False):
                        await self.send("You walk east through silver grass. There is no path until you are still.\r\n")
                        return
                    self._veilith_field_ready = False
                    self._veilith_span_ready = False
                    _move(self, CAUSEWAY_KEY)
                    await self.send("You take a few measured steps onto the first solid thread of light.\r\n")
                    return await self.show_current_room()

            if room == CAUSEWAY_KEY:
                if action in {"west", "w"}:
                    self._veilith_span_ready = False
                    _move(self, FIELD_KEY)
                    await self.send("You step back into the whispering silver grass.\r\n")
                    return await self.show_current_room()
                if action in {"wait", "stand still", "be still", "listen"}:
                    self._veilith_span_ready = True
                    await self.send(
                        "You stop. The hum settles with your breath. One step of light, then another, "
                        "draws itself across the open air. The way EAST holds, for now.\r\n"
                    )
                    return
                if action in {"east", "e", "cross", "cross causeway"}:
                    if not getattr(self, "_veilith_span_ready", False):
                        _move(self, FIELD_KEY)
                        self._veilith_field_ready = False
                        await self.send(
                            "You hurry toward empty space. The path withdraws, and the field receives "
                            "you gently where you began. No injury, only the hum.\r\n"
                        )
                        return await self.show_current_room()
                    self._veilith_span_ready = False
                    _move(self, STILLPOINT_KEY)
                    if ATTUNED_FLAG not in _flags(self):
                        _remember(self, ATTUNED_FLAG)
                        await self.send(
                            "The light folds into your shadow. You now recognize Veilith's seam "
                            "without the draught; the path back can never be entirely hidden again. "
                            "You are attuned to Veilith.\r\n"
                        )
                    else:
                        await self.send("The light remembers your pace and carries you across.\r\n")
                    return await self.show_current_room()

            if room == STILLPOINT_KEY:
                if action in {"west", "w"}:
                    self._veilith_span_ready = False
                    _move(self, CAUSEWAY_KEY)
                    return await self.show_current_room()
                if action in {"examine horizon", "look horizon", "listen", "wait"}:
                    await self.send(
                        "Far beyond the platform, white arches turn without moving. "
                        "The deeper ways of Veilith remain a mystery.\r\n"
                    )
                    return

        return await _delegate(self, previous_playing_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class._veilith_runtime_installed = True
