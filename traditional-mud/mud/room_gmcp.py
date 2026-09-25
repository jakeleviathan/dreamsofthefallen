from __future__ import annotations

"""Versioned, complete GMCP room snapshots for modern clients.

A GMCP subnegotiation is a single framed message, so Dreams.Room itself is the
start/end boundary. No protocol markers ever appear in ordinary Telnet text.
"""

import asyncio
import re
from time import monotonic


ROOM_PACKAGE = "Dreams.Room"
ROOM_SCHEMA_VERSION = 1
ROOM_REFRESH_SECONDS = 2.5
_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def _plain_overlays(overlays) -> list[str]:
    return [
        _ANSI_SGR.sub("", str(text)).replace("\r\n", "\n").strip()
        for text in overlays
        if str(text).strip()
    ]


async def push_room_snapshot(
    session, world_service, *, room_data: dict | None = None,
    overlays: list[str] | None = None, force: bool = False,
) -> bool:
    """Send a full, self-contained Dreams.Room frame if the visible room changed.

    Explicit LOOK/movement passes an already-rendered room_data object so both
    formats reflect the *same* world observation. Passive refreshes reuse the
    renderer without discovery writes, and send only when the payload changes.
    """
    character = getattr(session, "character", None)
    telnet = getattr(session, "telnet", None)
    if (
        character is None or not getattr(character, "current_room", None)
        or telnet is None or not getattr(telnet, "gmcp_enabled", False)
        or getattr(session, "_room_gmcp_suspended", False)
    ):
        return False

    lock = getattr(session, "_room_gmcp_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        session._room_gmcp_lock = lock

    async with lock:
        now = monotonic()
        if not force and now < getattr(session, "_room_gmcp_next_check", 0.0):
            return False
        session._room_gmcp_next_check = now + ROOM_REFRESH_SECONDS

        if room_data is None:
            # Import lazily so the production room installer can import this
            # module without creating an initialization cycle.
            from mud.room_presentation import render_room_lines

            room_data = {}
            render_room_lines(
                session, world_service, room_data=room_data,
                record_discovery=False,
            )
        if not room_data or room_data.get("id") != character.current_room:
            return False

        snapshot = dict(room_data)
        previous = getattr(session, "_room_gmcp_last_snapshot", None)
        if overlays is not None:
            snapshot["overlays"] = _plain_overlays(overlays)
        elif previous is not None and previous.get("id") == snapshot["id"]:
            snapshot["overlays"] = previous.get("overlays", [])
        else:
            snapshot["overlays"] = []

        if not force and previous == snapshot:
            return False

        # A new room always starts at revision 1; within that room, revisions
        # increase for each successfully emitted snapshot. A whole snapshot
        # replaces the previous one, including empty lists for vanished actors.
        previous_id = previous.get("id") if previous is not None else None
        revision = (
            int(getattr(session, "_room_gmcp_revision", 0)) + 1
            if previous_id == snapshot["id"] else 1
        )
        payload = dict(snapshot, revision=revision)
        sent = await telnet.send_gmcp(ROOM_PACKAGE, payload)
        if sent:
            session._room_gmcp_revision = revision
            session._room_gmcp_last_snapshot = snapshot
        return bool(sent)


def install_room_gmcp_runtime(player_session_class, world_service) -> None:
    """Connect full room snapshots to existing vitals and world refresh events."""
    if getattr(player_session_class, "_room_gmcp_runtime_installed", False):
        return

    previous_send_client_state = player_session_class.send_client_state

    async def send_client_state(self) -> None:
        await previous_send_client_state(self)
        await push_room_snapshot(self, world_service)

    async def send_room_snapshot(
        self, *, room_data: dict | None = None,
        overlays: list[str] | None = None, force: bool = False,
    ) -> bool:
        return await push_room_snapshot(
            self, world_service, room_data=room_data,
            overlays=overlays, force=force,
        )

    player_session_class.send_client_state = send_client_state
    player_session_class.push_room_snapshot = send_room_snapshot
    player_session_class._room_gmcp_runtime_installed = True
