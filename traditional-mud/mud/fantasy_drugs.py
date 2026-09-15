from __future__ import annotations

from dataclasses import dataclass, replace
from time import monotonic

import mud.crafting as crafting
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.broken_reach_midgame import ECHO_WELL_KEY
from mud.crafting import ItemDefinition
from mud.goblin_start import GOBLIN_BRASSGUT_MARKET_KEY
from mud.world import HUMAN_LANTERN_COURT_KEY, SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY, RoomDefinition


RESET = "\x1b[0m"


@dataclass(frozen=True, slots=True)
class PerceptionDrug:
    key: str
    name: str
    item_key: str
    duration_seconds: float
    aliases: tuple[str, ...]
    color: str
    onset_text: str
    room_overlay: str
    talk_echo: str
    thesis: str


DRUGS: tuple[PerceptionDrug, ...] = (
    PerceptionDrug(
        key="moonwake",
        name="Moonwake Resin",
        item_key="recreational_moonwake_resin",
        duration_seconds=600.0,
        aliases=("moonwake", "moonwake resin"),
        color="\x1b[95m",
        onset_text=(
            "The bitter resin softens under your tongue. Nothing becomes stronger or faster; instead, timing loosens. "
            "Your shadow seems to remember each movement a fraction late."
        ),
        room_overlay=(
            "For a moment the room seems to happen twice: once now, and once just before you notice it. "
            "Shadows lag half a heartbeat behind the things that cast them."
        ),
        talk_echo="The speaker's final word seems to arrive once from their mouth and once from a moment that has not quite happened yet.",
        thesis="Time feels layered rather than accelerated.",
    ),
    PerceptionDrug(
        key="choircap",
        name="Choircap Spores",
        item_key="recreational_choircap_spores",
        duration_seconds=600.0,
        aliases=("choircap", "choircap spores"),
        color="\x1b[92m",
        onset_text=(
            "The pale spores dissolve across your breath. Your body remains entirely your own, but the word 'you' briefly feels insufficient. "
            "Nearby intentions brush the edge of awareness like thoughts remembered from somebody else."
        ),
        room_overlay=(
            "The edges between observer and observed feel unusually thin. For one breath, the room is not around you so much as included in us. "
            "The thought passes before you can decide whose grammar it used."
        ),
        talk_echo="For an instant the sentence feels remembered instead of heard, as though you and the speaker reached it from opposite sides.",
        thesis="Individual perception briefly resembles a tiny, unreliable chorus.",
    ),
    PerceptionDrug(
        key="blue_emberleaf",
        name="Blue Emberleaf",
        item_key="recreational_blue_emberleaf",
        duration_seconds=480.0,
        aliases=("blue emberleaf", "emberleaf"),
        color="\x1b[96m",
        onset_text=(
            "The curled blue leaf burns with almost no heat. A dry sweetness settles behind your teeth and ordinary sounds begin leaving faint colors in their wake."
        ),
        room_overlay=(
            "Hard edges leave blue-green afterimages when you look away. A footstep seems briefly amber; distant metal rings silver-white. "
            "Nothing has changed, but your senses have stopped agreeing about how to report it."
        ),
        talk_echo="The voice leaves a narrow ribbon of color in the air, brightening on emphasized words before fading.",
        thesis="Sound, color, texture, and distance become mildly synesthetic.",
    ),
    PerceptionDrug(
        key="hushglass",
        name="Hushglass Tincture",
        item_key="recreational_hushglass_tincture",
        duration_seconds=720.0,
        aliases=("hushglass", "hushglass tincture"),
        color="\x1b[90m",
        onset_text=(
            "The clear tincture tastes like cold stone and then almost like nothing. Corners acquire depth behind themselves. "
            "Several perfectly ordinary directions begin to feel less convincing than one impossible direction you cannot yet name."
        ),
        room_overlay=(
            "The room's boundaries look technically correct but emotionally unpersuasive. Corners seem to continue somewhere behind their own angles."
        ),
        talk_echo="Meaning seems to arrive from slightly behind the words, as if the sentence had to pass through a thin wall to reach you.",
        thesis="Boundaries and directions feel negotiable without becoming mechanically false.",
    ),
)
DRUGS_BY_KEY = {drug.key: drug for drug in DRUGS}
DRUG_BY_ITEM = {drug.item_key: drug for drug in DRUGS}
DRUG_ALIAS_MAP = {alias: drug for drug in DRUGS for alias in drug.aliases}


DRUG_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        "recreational_moonwake_resin",
        "Moonwake Resin",
        "A violet-gray bead of aromatic resin traded quietly in night markets. Recreational users describe delayed shadows, repeated moments, and the sense that a room has just finished happening.",
        "recreational",
        tier=2,
    ),
    ItemDefinition(
        "recreational_choircap_spores",
        "Choircap Spores",
        "A wax-paper twist of pale fungal spores. They are valued for a temporary sense of porous identity and shared thought rather than for strength, healing, or combat utility.",
        "recreational",
        tier=2,
    ),
    ItemDefinition(
        "recreational_blue_emberleaf",
        "Blue Emberleaf",
        "A curled blue leaf with a silver underside. When burned, it is known for mild synesthesia: sounds seem colored, textures seem audible, and distances acquire peculiar moods.",
        "recreational",
        tier=2,
    ),
    ItemDefinition(
        "recreational_hushglass_tincture",
        "Hushglass Tincture",
        "A thumb-sized vial of perfectly clear liquid that never reflects the room correctly. Its reputation concerns impossible corners, inward directions, and places that may only exist while perception is altered.",
        "recreational",
        tier=4,
    ),
)


INTERVAL_REGION_KEY = "veiled_interval"
INTERVAL_THRESHOLD = "veiled_interval_soft_threshold"
INTERVAL_GALLERY = "veiled_interval_borrowed_senses"
INTERVAL_CROSSING = "veiled_interval_two_horizons"
INTERVAL_LISTENER = "veiled_interval_listener_door"
INTERVAL_ROOMS = (
    INTERVAL_THRESHOLD,
    INTERVAL_GALLERY,
    INTERVAL_CROSSING,
    INTERVAL_LISTENER,
)

_INTERVAL_ROOM_DEFS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=INTERVAL_THRESHOLD,
        name="The Soft Threshold",
        region_key=INTERVAL_REGION_KEY,
        description="A place exists here, but no sober description survives long enough to be useful.",
        exits={},
        tags=("planar", "hidden_world", "perception_only", "no_combat"),
    ),
    RoomDefinition(
        key=INTERVAL_GALLERY,
        name="The Hall of Borrowed Senses",
        region_key=INTERVAL_REGION_KEY,
        description="The room is shared, but its apparent shape depends on how it is perceived.",
        exits={},
        tags=("planar", "hidden_world", "perception_only", "no_combat"),
    ),
    RoomDefinition(
        key=INTERVAL_CROSSING,
        name="The Room With Two Horizons",
        region_key=INTERVAL_REGION_KEY,
        description="Two incompatible distances occupy one place without touching.",
        exits={},
        tags=("planar", "hidden_world", "perception_only", "no_combat"),
    ),
    RoomDefinition(
        key=INTERVAL_LISTENER,
        name="The Listener at the Door",
        region_key=INTERVAL_REGION_KEY,
        description="Something here appears to be listening from whichever side you are not on.",
        exits={},
        tags=("planar", "hidden_world", "perception_only", "no_combat"),
    ),
)


_INTERVAL_VIEWS: dict[str, dict[str, tuple[str, str]]] = {
    "moonwake": {
        INTERVAL_THRESHOLD: ("The Threshold That Already Happened", "A corridor finishes forming a moment before you enter it. Your own footprints are waiting ahead of you, fresh and pointed both ways."),
        INTERVAL_GALLERY: ("Gallery of Earlier Faces", "Portraits show expressions you have not made yet. When you turn away, several repaint themselves as memories instead."),
        INTERVAL_CROSSING: ("The Double Horizon", "One horizon approaches while the other recedes. Neither changes distance. A version of your shadow leaves before you do."),
        INTERVAL_LISTENER: ("The Door After the Knock", "A door stands open because, somehow, you have already knocked. Something beyond it waits for the sound to catch up."),
    },
    "choircap": {
        INTERVAL_THRESHOLD: ("The Shared Threshold", "The floor arrives beneath our feet. The correction to 'my feet' comes too late to feel completely convincing."),
        INTERVAL_GALLERY: ("Hall of Borrowed Selves", "Thoughts move through the room like people at a market. Most are meaningless. A few recognize you before you recognize them."),
        INTERVAL_CROSSING: ("Where We Divide", "Two horizons separate every thought into mine and ours. Neither side can agree which one is the original."),
        INTERVAL_LISTENER: ("The One Who Hears Us", "Something behind a closed door listens to the chorus without joining it. The silence around that fact feels deliberate."),
    },
    "blue_emberleaf": {
        INTERVAL_THRESHOLD: ("The Cobalt Threshold", "Distance is blue here. Nearness is warm brass. Your footsteps bloom orange under you and fade upward instead of behind."),
        INTERVAL_GALLERY: ("Gallery of Audible Colors", "Each surface hums a color and each color has texture. A violet note feels like velvet dragged across glass."),
        INTERVAL_CROSSING: ("The Bright and Dim Horizons", "One horizon is painfully bright but silent. The other is black and ringing. Both smell faintly of rain on iron."),
        INTERVAL_LISTENER: ("The Color Behind the Door", "Something listens behind the door in a shade you cannot name. Looking directly at it makes the color sound farther away."),
    },
    "hushglass": {
        INTERVAL_THRESHOLD: ("The Inward Threshold", "The room has an inside beyond its interior. Every corner points toward it while pretending to meet the walls normally."),
        INTERVAL_GALLERY: ("Hall Behind the Walls", "You can see the backs of surfaces without seeing through them. Several doors have depth but no width."),
        INTERVAL_CROSSING: ("The Near-Far Crossing", "One horizon is impossibly close and the other is inside your sense of distance. Neither appears to belong to Astralis."),
        INTERVAL_LISTENER: ("The Door Listening Back", "A narrow door has no visible opening side. Something behind it seems less interested in you than in the fact that you found a way to stand here."),
    },
}

_FORWARD_VERBS = {
    "moonwake": "later",
    "choircap": "with",
    "blue_emberleaf": "bright",
    "hushglass": "inward",
}
_BACK_VERBS = {
    "moonwake": "earlier",
    "choircap": "apart",
    "blue_emberleaf": "dim",
    "hushglass": "outward",
}
_INTERVAL_ORDER = (INTERVAL_THRESHOLD, INTERVAL_GALLERY, INTERVAL_CROSSING, INTERVAL_LISTENER)


_SOURCE_ACTIONS: dict[tuple[str, str], tuple[str, str]] = {
    (GOBLIN_BRASSGUT_MARKET_KEY, "ask for emberleaf"): (
        "recreational_blue_emberleaf",
        "A vendor beneath a patched blue awning slides you a single twist of Blue Emberleaf. 'For looking, not fighting,' she says. 'Come back when you've used it.'",
    ),
    (GOBLIN_BRASSGUT_MARKET_KEY, "ask ruskle for emberleaf"): (
        "recreational_blue_emberleaf",
        "Ruskle Coil produces one folded twist of Blue Emberleaf from a pocket you were certain was empty. 'Makes music look expensive,' he says.",
    ),
    (SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY, "gather choircap spores"): (
        "recreational_choircap_spores",
        "A mature choircap releases a small pale cloud into your waiting paper fold. You gather one dose without disturbing the ring around it.",
    ),
    (HUMAN_LANTERN_COURT_KEY, "ask informant about moonwake"): (
        "recreational_moonwake_resin",
        "The grey-cloaked informant studies you, then presses one bead of Moonwake Resin into your palm. 'Don't mistake what it shows you for testimony.'",
    ),
    (ECHO_WELL_KEY, "draw hushglass"): (
        "recreational_hushglass_tincture",
        "The well gives no echo, but a glass vial lowered into it returns holding a perfectly clear mouthful that reflects the rope instead of the sky: Hushglass Tincture.",
    ),
    (ECHO_WELL_KEY, "bottle hushglass"): (
        "recreational_hushglass_tincture",
        "You draw one small vial of Hushglass from the echo-less water. The liquid reflects a corner that is not present.",
    ),
}


def install_perception_content(world_service) -> None:
    """Register the recreational items and shared drug-only dimension."""

    for item in DRUG_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for room in _INTERVAL_ROOM_DEFS:
        legacy_world.ROOMS_BY_KEY[room.key] = room
        if not any(existing.key == room.key for existing in legacy_world.ROOMS):
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        world_service.legacy_rooms[room.key] = room
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(room.key, None)


def _set_room(session, room_key: str) -> None:
    session.database.set_character_room(session.character.id, room_key)
    try:
        session.character = replace(session.character, current_room=room_key)
    except TypeError:
        session.character.current_room = room_key


def _drug_from_target(target: str) -> PerceptionDrug | None:
    normalized = " ".join(target.strip().lower().split())
    return DRUG_ALIAS_MAP.get(normalized)


def _active_drug(session, *, now: float | None = None) -> PerceptionDrug | None:
    key = getattr(session, "_perception_drug_key", None)
    if key not in DRUGS_BY_KEY:
        return None
    current = monotonic() if now is None else now
    if current >= float(getattr(session, "_perception_expires_at", 0.0)):
        return None
    return DRUGS_BY_KEY[key]


def active_perception_name(session, *, now: float | None = None) -> str | None:
    drug = _active_drug(session, now=now)
    return None if drug is None else drug.name


def interval_exits(drug_key: str, room_key: str) -> tuple[tuple[str, str], ...]:
    if drug_key not in DRUGS_BY_KEY or room_key not in _INTERVAL_ORDER:
        return ()
    index = _INTERVAL_ORDER.index(room_key)
    exits: list[tuple[str, str]] = []
    if index > 0:
        exits.append((_BACK_VERBS[drug_key], _INTERVAL_ORDER[index - 1]))
    if index < len(_INTERVAL_ORDER) - 1:
        exits.append((_FORWARD_VERBS[drug_key], _INTERVAL_ORDER[index + 1]))
    exits.append(("return", ECHO_WELL_KEY))
    return tuple(exits)


def interval_view(drug_key: str, room_key: str) -> tuple[str, str]:
    return _INTERVAL_VIEWS[drug_key][room_key]


def _should_follow(character_id: int, day_number: int) -> bool:
    """Deterministic one-in-four chance so behavior is testable and not farmable by reconnecting."""

    return ((int(character_id) * 17 + int(day_number) * 11) % 4) == 0


def _paint(drug: PerceptionDrug, text: str) -> str:
    return f"{drug.color}{text}{RESET}"


async def _delegate_prompt(session, previous_prompt, command: str):
    previous = session.prompt

    async def replay(_text=""):
        return command

    session.prompt = replay
    try:
        return await previous_prompt(session)
    finally:
        session.prompt = previous


async def _leave_interval(session, *, expired: bool = False) -> None:
    return_room = getattr(session, "_perception_return_room", None) or ECHO_WELL_KEY
    _set_room(session, return_room)
    session._perception_return_room = None
    if expired:
        session._perception_drug_key = None
        session._perception_expires_at = 0.0
        await session.send("The altered geometry loses coherence. Astralis returns all at once, heavy and ordinary beneath your feet.\r\n")
    else:
        await session.send("You choose the direction that means return. The Veiled Interval folds shut behind ordinary space.\r\n")

    moment = ASTRALIS_CLOCK.now()
    if _should_follow(session.character.id, moment.day_number):
        session._perception_follow_steps = 3
        await session.send("For one uncomfortable second, another set of footsteps seems to arrive with you. Then there is only your own.\r\n")
    await session.show_current_room()


async def _expire_if_needed(session) -> bool:
    key = getattr(session, "_perception_drug_key", None)
    if key not in DRUGS_BY_KEY:
        return False
    if monotonic() < float(getattr(session, "_perception_expires_at", 0.0)):
        return False
    if session.character and session.character.current_room in INTERVAL_ROOMS:
        await _leave_interval(session, expired=True)
        return True
    session._perception_drug_key = None
    session._perception_expires_at = 0.0
    return False


async def _show_interval(session, drug: PerceptionDrug) -> None:
    room_key = session.character.current_room
    title, description = interval_view(drug.key, room_key)
    await session.send("\r\n" + _paint(drug, title) + "\r\n")
    await session.send(_paint(drug, "The Veiled Interval — perception is supplying part of the geography.") + "\r\n")
    await session.send("-" * 64 + "\r\n")
    await session.send(_paint(drug, description) + "\r\n")
    await session.send(
        _paint(
            drug,
            "You are physically sharing this room with any other altered travelers here, even if their version of it looks different.",
        )
        + "\r\n"
    )
    await session.send("\r\n[ Perceived Exits ]\r\n")
    for verb, _destination in interval_exits(drug.key, room_key):
        await session.send(f"  {_paint(drug, verb.upper())}\r\n")
    await session.send("\r\n")


async def _show_drug_item(session, drug: PerceptionDrug) -> None:
    if session.database.item_quantity(session.character.id, drug.item_key) <= 0:
        await session.send("You are not carrying that substance.\r\n")
        return
    item = crafting.ITEMS_BY_KEY[drug.item_key]
    await session.send(
        f"\r\n{item.name}\r\n{item.description}\r\nCategory: Recreational / perception-altering\r\n"
        "Direct stat effects: none. It does not heal, increase damage, falsify HP, or create imaginary inventory.\r\n"
    )


async def _consume(session, drug: PerceptionDrug) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send("This is recreational, not a combat stimulant. You are too occupied with the fight to use it now.\r\n")
        return
    if session.database.item_quantity(session.character.id, drug.item_key) <= 0:
        await session.send(f"You are not carrying {drug.name}.\r\n")
        return
    if not session.database.consume_item(session.character.id, drug.item_key, 1):
        await session.send(f"You cannot use {drug.name} right now.\r\n")
        return
    previous = _active_drug(session)
    session._perception_drug_key = drug.key
    session._perception_expires_at = monotonic() + drug.duration_seconds
    if previous is not None and previous.key != drug.key:
        await session.send(f"The {previous.name} perception folds into a different pattern.\r\n")
    await session.send(_paint(drug, drug.onset_text) + "\r\n")
    await session.send(
        "Your core game state remains authoritative: HP, mana, movement, equipment, inventory, and combat numbers are not hallucinated.\r\n"
    )
    if session.character.current_room == ECHO_WELL_KEY:
        await session.send(_paint(drug, "The Well Without Echo now seems to possess an impossible exit: INWARD.") + "\r\n")
    await session.send_client_state()


async def _show_status(session) -> None:
    drug = _active_drug(session)
    if drug is None:
        await session.send(
            "Perception: sober. Recreational substances can alter descriptive text and, in rare places, reveal routes that do not exist to sober perception. "
            "They do not directly buff damage, healing, HP, mana, movement, or item stats.\r\n"
        )
        return
    remaining = max(0, int(float(session._perception_expires_at) - monotonic()))
    await session.send(
        f"Perception: {drug.name} ({remaining // 60}m {remaining % 60}s remaining). {drug.thesis}\r\n"
        "Mechanical HP, mana, movement, equipment and inventory remain truthful. Perceptual prose and unusual routes may not be.\r\n"
    )


def install_perception_runtime(player_session_class, world_service) -> None:
    """Install recreational perception effects as the outermost presentation layer."""

    install_perception_content(world_service)
    if getattr(player_session_class, "_perception_runtime_installed", False):
        return

    original_enter_character = player_session_class.enter_character
    original_show_current_room = player_session_class.show_current_room
    original_playing_prompt = player_session_class.playing_prompt
    original_move_character = player_session_class.move_character
    original_send_client_state = player_session_class.send_client_state

    async def enter_character(self):
        await original_enter_character(self)
        if getattr(self, "character", None) is None:
            return
        self._perception_drug_key = None
        self._perception_expires_at = 0.0
        self._perception_return_room = None
        self._perception_follow_steps = 0
        # Perception is session-state. A disconnect inside the Interval must never
        # strand a character in a room that only altered perception can navigate.
        if self.character.current_room in INTERVAL_ROOMS:
            _set_room(self, ECHO_WELL_KEY)
            await self.send("You return to consciousness beside the Well Without Echo. Whatever path held you is gone.\r\n")

    async def show_current_room(self):
        if getattr(self, "character", None) is None:
            return await original_show_current_room(self)
        if await _expire_if_needed(self):
            return
        drug = _active_drug(self)
        if self.character.current_room in INTERVAL_ROOMS:
            if drug is None:
                return await _leave_interval(self, expired=True)
            return await _show_interval(self, drug)
        await original_show_current_room(self)
        if drug is not None:
            await self.send(_paint(drug, "[ Altered Perception ] " + drug.room_overlay) + "\r\n")
            if self.character.current_room == ECHO_WELL_KEY:
                await self.send(_paint(drug, "The well has an exit your map cannot express: INWARD.") + "\r\n")

    async def move_character(self, direction: str):
        origin = self.character.current_room if getattr(self, "character", None) else None
        await original_move_character(self, direction)
        if getattr(self, "character", None) is None or self.character.current_room == origin:
            return
        if self.character.current_room in INTERVAL_ROOMS:
            return
        remaining = int(getattr(self, "_perception_follow_steps", 0))
        if remaining > 0:
            echoes = (
                "A second set of footsteps stops exactly when yours do.",
                "Your shadow reaches the wall a fraction later than you do.",
                "Something behind you seems to choose not to enter the room.",
            )
            await self.send(echoes[3 - remaining] + "\r\n")
            self._perception_follow_steps = remaining - 1

    async def send_client_state(self):
        await original_send_client_state(self)
        telnet = getattr(self, "telnet", None)
        if telnet is None or not getattr(telnet, "gmcp_enabled", False):
            return
        drug = _active_drug(self)
        payload = {
            "altered": drug is not None,
            "effect": None if drug is None else drug.key,
            "name": None if drug is None else drug.name,
            "seconds_remaining": 0 if drug is None else max(0, int(self._perception_expires_at - monotonic())),
            "in_veiled_interval": bool(getattr(self, "character", None) and self.character.current_room in INTERVAL_ROOMS),
        }
        try:
            await telnet.send_gmcp("Dreams.Perception", payload)
        except Exception:
            pass

    async def playing_prompt(self):
        if getattr(self, "character", None) is None:
            return await original_playing_prompt(self)
        if await _expire_if_needed(self):
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            from mud.session import SessionState
            self.state = SessionState.DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        room = self.character.current_room or ""
        drug = _active_drug(self)

        if normalized in {"drugs", "perception", "altered", "altered state"}:
            return await _show_status(self)

        # World sources are deliberately local and low-volume: you can replenish a
        # recreational dose after using it, but cannot stockpile infinite free stacks.
        source = _SOURCE_ACTIONS.get((room, normalized))
        if source is not None:
            item_key, text = source
            if self.database.item_quantity(self.character.id, item_key) > 0:
                await self.send("You already have an unused dose of that substance.\r\n")
                return
            self.database.add_item(self.character.id, item_key, 1)
            await self.send(text + "\r\n")
            return

        if normalized == "inward" and room == ECHO_WELL_KEY:
            if drug is None:
                await self.send("The well is only a well. Whatever an inward direction might mean, sober perception cannot find it here.\r\n")
                return
            self._perception_return_room = room
            _set_room(self, INTERVAL_THRESHOLD)
            self.database.grant_flag(self.character.id, "perception_discovered_veiled_interval")
            await self.send(_paint(drug, "You choose INWARD. The well does not move; the meaning of 'here' does.") + "\r\n")
            return await _show_interval(self, drug)

        if room in INTERVAL_ROOMS:
            if normalized in {"return", "return astralis", "go home"}:
                return await _leave_interval(self)
            if normalized in {"look", "l", "exits", "exit"}:
                return await _show_interval(self, drug)
            if normalized == "listen":
                hints = {
                    "moonwake": "You hear one knock before the hand that makes it exists. The effect offers no proof that the sound is prophecy rather than repetition.",
                    "choircap": "A distant collective thought says, WE WERE NOT ALWAYS SEPARATE. You cannot tell whether it came from the place, the spores, or you.",
                    "blue_emberleaf": "A color you cannot name sounds exactly like the first instant before waking. No ordinary sense can confirm the association.",
                    "hushglass": "Several other planes seem to press against this one like rooms sharing walls. None open, and the perception may be lying about the architecture.",
                }
                await self.send(_paint(drug, hints[drug.key]) + "\r\n")
                return
            for exit_verb, destination in interval_exits(drug.key, room):
                if normalized == exit_verb:
                    if exit_verb == "return":
                        return await _leave_interval(self)
                    _set_room(self, destination)
                    return await _show_interval(self, drug)
            await self.send("That direction does not exist in the version of this place you can currently perceive. Type LOOK to see its perceived exits.\r\n")
            return

        # The same inventory-detail language works for recreational items too.
        if normalized.startswith("item ") or normalized.startswith("inspect item "):
            target = command.strip()[len("inspect item "):] if normalized.startswith("inspect item ") else command.strip().split(maxsplit=1)[1]
            target_drug = _drug_from_target(target)
            if target_drug is not None:
                return await _show_drug_item(self, target_drug)

        consume_prefixes = ("use ", "consume ", "take ", "drink ", "chew ", "smoke ", "inhale ")
        for prefix in consume_prefixes:
            if normalized.startswith(prefix):
                target_drug = _drug_from_target(normalized[len(prefix):])
                if target_drug is not None:
                    return await _consume(self, target_drug)

        await _delegate_prompt(self, original_playing_prompt, command)

        # The underlying NPC dialogue remains untouched. Alteration adds a clearly
        # perceptual echo afterward instead of rewriting factual speech.
        if normalized.startswith(("talk ", "speak ")):
            drug = _active_drug(self)
            if drug is not None and self.character is not None and self.character.current_room not in INTERVAL_ROOMS:
                await self.send(_paint(drug, drug.talk_echo) + "\r\n")
        if normalized in {"help", "?"}:
            await self.send("Perception commands: DRUGS/PERCEPTION shows your current altered state. Recreational substances change descriptive perception rather than acting as combat consumables.\r\n")

    player_session_class.enter_character = enter_character
    player_session_class.show_current_room = show_current_room
    player_session_class.move_character = move_character
    player_session_class.send_client_state = send_client_state
    player_session_class.playing_prompt = playing_prompt
    player_session_class._perception_runtime_installed = True
