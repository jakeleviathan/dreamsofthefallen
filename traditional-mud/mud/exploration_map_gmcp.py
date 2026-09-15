from __future__ import annotations

from mud.exploration_map import (
    MAX_MAP_RADIUS,
    build_discovered_map_snapshot,
    note_room_visited,
)


async def push_discovered_map_state(session, world_service) -> bool:
    """Push the character's discovered local graph to GMCP-capable clients.

    The graphical client receives the same no-spoiler knowledge as the ASCII MAP
    command: only rooms this character has actually entered are included.
    """

    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    telnet = getattr(session, "telnet", None)
    if (
        character is None
        or combatant is None
        or telnet is None
        or not getattr(telnet, "gmcp_enabled", False)
    ):
        return False

    note_room_visited(session)
    payload = build_discovered_map_snapshot(session, world_service, MAX_MAP_RADIUS)
    cache = getattr(session, "_exploration_map_gmcp_cache", None)
    if cache == payload:
        return False
    session._exploration_map_gmcp_cache = payload
    return await telnet.send_gmcp("Dreams.Map", payload)


def install_exploration_map_gmcp_runtime(player_session_class, world_service) -> None:
    """Keep the Mudlet mapper synchronized with the persistent discovery map."""

    if getattr(player_session_class, "_exploration_map_gmcp_runtime_installed", False):
        return

    previous_send_client_state = player_session_class.send_client_state
    previous_enter_character = player_session_class.enter_character
    previous_show_current_room = player_session_class.show_current_room

    async def send_client_state(self) -> None:
        await previous_send_client_state(self)
        await push_discovered_map_state(self, world_service)

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if getattr(self, "character", None) is not None:
            note_room_visited(self)
            await push_discovered_map_state(self, world_service)

    async def show_current_room(self) -> None:
        if getattr(self, "character", None) is not None:
            note_room_visited(self)
        await previous_show_current_room(self)
        await push_discovered_map_state(self, world_service)

    player_session_class.send_client_state = send_client_state
    player_session_class.enter_character = enter_character
    player_session_class.show_current_room = show_current_room
    player_session_class._exploration_map_gmcp_runtime_installed = True
