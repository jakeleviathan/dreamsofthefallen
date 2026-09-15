from __future__ import annotations

import mud.forest_elf_nurture as forest_nurture
import mud.goblin_deep_mire as deep_mire
import mud.goblin_swamp as goblin_swamp
import mud.troll_start as troll_start
import mud.waymeet_adventure_arc as waymeet


# Waymeet's adventure runtime was originally installed as a global command
# wrapper. Its SEARCH/LISTEN/CLIMB/PULL/TOUCH helpers intentionally print useful
# fallback text when a player uses the wrong target *inside the adventure*, but
# those helpers also returned handled=True everywhere else in Astralis. That
# meant an outer Waymeet wrapper could swallow a command before an older authored
# system saw it.

SEARCH_ROOMS = frozenset(
    {
        waymeet.TOLL_LEDGER,
        waymeet.TOLL_COUNTING,
        waymeet.BELL_BELFRY,
        waymeet.SCAR_DEEP_FACE,
    }
)

LISTEN_ROOMS = frozenset(
    {
        waymeet.BELL_NAVE,
        waymeet.BELL_EAST_GALLERY,
        waymeet.ECHO_LISTENER_COURT,
    }
)

CLIMB_ROOMS = frozenset({waymeet.SCAR_LIFT})

PULL_ROOMS = frozenset(
    {
        waymeet.BELL_ROPE_ROOM,
        waymeet.SCAR_WINCH,
        waymeet.ECHO_LISTENER_COURT,
    }
)

TOUCH_ROOMS = frozenset({*waymeet.ECHO_PLATE_FLAGS.keys(), waymeet.ECHO_MIRROR_CHOIR})

OWNED_ROOMS_BY_HELPER = {
    "_search": SEARCH_ROOMS,
    "_listen": LISTEN_ROOMS,
    "_climb": CLIMB_ROOMS,
    "_pull": PULL_ROOMS,
    "_touch": TOUCH_ROOMS,
}


def _scope_helper(helper_name: str, owned_rooms: frozenset[str]) -> None:
    original = getattr(waymeet, helper_name)
    if getattr(original, "_dotf_context_scoped", False):
        return

    async def scoped(session, *args, **kwargs) -> bool:
        character = getattr(session, "character", None)
        if character is None or (character.current_room or "") not in owned_rooms:
            return False
        return await original(session, *args, **kwargs)

    scoped.__name__ = getattr(original, "__name__", helper_name)
    scoped.__doc__ = getattr(original, "__doc__", None)
    scoped._dotf_context_scoped = True  # type: ignore[attr-defined]
    scoped._dotf_unscoped_helper = original  # type: ignore[attr-defined]
    setattr(waymeet, helper_name, scoped)


def _normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def _first_word(normalized: str) -> str:
    return normalized.split(maxsplit=1)[0] if normalized else ""


async def _dispatch_authored_economy_command(session, command: str) -> bool:
    """Give room-authored gathering/crafting interactions first refusal.

    The generic economy runtime is intentionally broad, but it was installed
    outside several older tutorial/adventure systems. That made commands the
    quests explicitly teach (for example GATHER DEADFALL or HARVEST GLASSROOT)
    disappear into the generic "no resource here" fallback. This dispatcher is
    deliberately narrow: it only invokes an authored handler in rooms where that
    authored system owns the interaction, and only returns handled when that
    handler actually accepts the command.
    """

    character = getattr(session, "character", None)
    if character is None:
        return False

    room = character.current_room or ""
    normalized = _normalize(command)
    first = _first_word(normalized)

    # Troll survival tutorial: the quest explicitly teaches GATHER DEADFALL.
    if room == troll_start.TROLL_HIDEWIND_RING_KEY and first in {"gather", "collect", "take"}:
        if any(word in normalized for word in ("deadfall", "wood")):
            if await troll_start._handle_cold_quest(session, normalized):
                return True

    # Forest Elf stewardship tutorial: Silvermoss is an authored single-use
    # Herbalism lesson, not one of the generic economy loop's renewable nodes.
    if room == forest_nurture.FOREST_ELF_START_ROOM_KEY and first in {"gather", "harvest", "pick"}:
        if any(word in normalized for word in ("silvermoss", "moss")):
            if await forest_nurture._handle_forest_elf_nurture(session, normalized):
                return True

    # The Goblin deep mire has its own persistent gathering nodes and alchemy
    # recipes. Let those handlers resolve the exact target before the generic
    # economy layer claims GATHER/HARVEST/HERBALISM/CRAFT.
    if room in deep_mire.GOBLIN_DEEP_MIRE_ROOM_KEYS:
        if first in {"gather", "harvest", "herbalism", "pick", "collect"}:
            if await deep_mire._handle_deep_gathering(session, normalized):
                return True
        if first in {"brew", "prepare", "craft", "make"}:
            if await deep_mire._handle_deep_alchemy(session, command):
                return True

    # Beginner Goblin swamp alchemy accepts CRAFT as an alias in addition to
    # BREW/PREPARE. The final swamp gathering bridge already owns gathering; this
    # catches the crafting alias that the generic recipe catalog otherwise sees
    # first.
    if room in goblin_swamp.GOBLIN_SWAMP_ROOM_KEYS and first == "craft":
        if await goblin_swamp._handle_alchemy(session, command):
            return True

    return False


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def _install_authored_economy_router(player_session_class) -> None:
    if getattr(player_session_class, "_authored_economy_router_installed", False):
        return
    # Some focused unit tests use a tiny stand-in class only to validate the
    # Waymeet helper scoping. Production PlayerSession always has playing_prompt;
    # don't force unrelated test doubles to implement a command loop.
    if not hasattr(player_session_class, "playing_prompt"):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            disconnected = getattr(type(state), "DISCONNECTED", None) if state is not None else None
            if disconnected is not None:
                self.state = disconnected
            return

        if await _dispatch_authored_economy_command(self, command):
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._authored_economy_router_installed = True


def install_contextual_command_routing_guard(player_session_class) -> None:
    """Prevent broad/global command layers from stealing authored interactions."""

    if getattr(player_session_class, "_contextual_command_routing_guard_installed", False):
        return

    for helper_name, owned_rooms in OWNED_ROOMS_BY_HELPER.items():
        _scope_helper(helper_name, owned_rooms)

    _install_authored_economy_router(player_session_class)
    player_session_class._contextual_command_routing_guard_installed = True
