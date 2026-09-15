from __future__ import annotations

import re

from mud.player_preferences import color_enabled, load_preferences, mudlet_enhancements_enabled


_ANSI_SGR = re.compile(r"\x1b\[([0-9;]*)m")
_HIGH_CONTRAST_SGR = {
    "90": "1;97",
    "37": "1;97",
    "96": "1;96",
    "92": "1;92",
    "1;91": "1;91",
    "94": "1;94",
    "95": "1;95",
    "1;93": "1;93",
}


def _presentation_text(session, text: str) -> str:
    """Apply the account's final accessibility policy to arbitrary text output."""

    if "\x1b[" not in text:
        return text
    if not color_enabled(session):
        return _ANSI_SGR.sub("", text)

    if str(getattr(session, "_player_contrast_mode", "standard")).lower() != "high":
        return text

    def remap(match: re.Match[str]) -> str:
        code = match.group(1)
        if code == "0":
            return match.group(0)
        return f"\x1b[{_HIGH_CONTRAST_SGR.get(code, '1;97')}m"

    return _ANSI_SGR.sub(remap, text)


def _install_telnet_gmcp_policy(session) -> None:
    telnet = getattr(session, "telnet", None)
    if telnet is None or getattr(telnet, "_dotf_preference_gmcp_policy", False):
        return

    previous_send_gmcp = telnet.send_gmcp

    async def send_gmcp(package: str, payload=None) -> bool:
        # Account preferences are authoritative even for outer runtime layers
        # that call telnet.send_gmcp directly instead of send_client_state.
        if getattr(session, "account", None) is not None:
            try:
                load_preferences(session)
            except Exception:
                pass
        if not mudlet_enhancements_enabled(session):
            return False
        return await previous_send_gmcp(package, payload)

    telnet.send_gmcp = send_gmcp
    telnet._dotf_preference_gmcp_policy = True


def install_accessibility_policy_runtime(player_session_class) -> None:
    """Make color, screen-reader and Mudlet settings authoritative everywhere.

    Earlier preference wrappers could only govern the systems installed beneath
    them. Newer room/map/movement/perception layers sit outside that stack, so a
    final transport-level policy is required: text is filtered at PlayerSession.send
    and every GMCP packet is checked at the individual TelnetConnection instance.
    """

    if getattr(player_session_class, "_accessibility_policy_runtime_installed", False):
        return

    previous_init = player_session_class.__init__

    def __init__(self, *args, **kwargs) -> None:
        previous_init(self, *args, **kwargs)
        _install_telnet_gmcp_policy(self)

    player_session_class.__init__ = __init__

    previous_send = player_session_class.send

    async def send(self, text: str) -> None:
        if getattr(self, "account", None) is not None:
            try:
                load_preferences(self)
            except Exception:
                pass
        await previous_send(self, _presentation_text(self, text))

    player_session_class.send = send

    # Preferences must be loaded before the entering-room presentation, not
    # afterward, otherwise a saved COLOR OFF or SCREENREADER setting can leak one
    # colored/GMCP-rich room during login.
    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            if getattr(self, "account", None) is not None:
                load_preferences(self, force=True)
            _install_telnet_gmcp_policy(self)
            await previous_enter_character(self)

        player_session_class.enter_character = enter_character

    player_session_class._accessibility_policy_runtime_installed = True


def install_final_runtime_policy(player_session_class) -> None:
    """Anchor final cross-cutting policies after the production stack is assembled."""

    install_accessibility_policy_runtime(player_session_class)
    player_session_class._final_runtime_policy_installed = True
