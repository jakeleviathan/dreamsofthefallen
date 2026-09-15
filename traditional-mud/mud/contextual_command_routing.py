from __future__ import annotations

import mud.waymeet_adventure_arc as waymeet


# Waymeet's adventure runtime was originally installed as a global command
# wrapper. Its SEARCH/LISTEN/CLIMB/PULL/TOUCH helpers intentionally print useful
# fallback text when a player uses the wrong target *inside the adventure*, but
# those helpers also returned handled=True everywhere else in Astralis. That
# meant an outer Waymeet wrapper could swallow a command before an older authored
# system saw it. The most visible example was LISTEN CONVERSATION after talking
# to a racial story partner, but the same routing bug could affect any earlier
# feature that used one of these five verbs.
#
# Keep the helpful Waymeet fallbacks, but only in rooms where that particular
# verb actually belongs to the Waymeet adventure. Everywhere else the helper
# returns False, allowing the normal wrapper chain to continue until the owning
# content system handles the command.

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


def install_contextual_command_routing_guard(player_session_class) -> None:
    """Prevent one content layer's generic verb fallback from stealing another's command.

    The guard is installed at final production assembly time, after every authored
    runtime has wrapped PlayerSession. It does not reorder those wrappers. Instead
    it narrows Waymeet's five catch-all helper functions to the exact rooms where
    Waymeet owns those interactions, so commands elsewhere naturally continue down
    the established runtime chain.
    """

    if getattr(player_session_class, "_contextual_command_routing_guard_installed", False):
        return

    for helper_name, owned_rooms in OWNED_ROOMS_BY_HELPER.items():
        _scope_helper(helper_name, owned_rooms)

    player_session_class._contextual_command_routing_guard_installed = True
