from __future__ import annotations

import re

from mud.player_preferences import color_enabled, load_preferences, mudlet_enhancements_enabled
from mud.runtime_remediation import install_runtime_remediation


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
    if telnet is None or getattr(session, "_dotf_preference_gmcp_policy", False):
        return

    def gmcp_send_allowed(_package: str, _payload=None) -> bool:
        if getattr(session, "account", None) is not None:
            try:
                load_preferences(session)
            except Exception:
                pass
        return mudlet_enhancements_enabled(session)

    # TelnetConnection is a slotted dataclass, so policy must use its declared
    # callback slot instead of replacing send_gmcp on the individual instance.
    telnet.gmcp_send_allowed = gmcp_send_allowed
    session._dotf_preference_gmcp_policy = True


def install_accessibility_policy_runtime(player_session_class) -> None:
    """Make color, screen-reader and Mudlet settings authoritative everywhere."""

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

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            if getattr(self, "account", None) is not None:
                load_preferences(self, force=True)
            _install_telnet_gmcp_policy(self)
            await previous_enter_character(self)

        player_session_class.enter_character = enter_character

    player_session_class._accessibility_policy_runtime_installed = True


def _is_generic_play_prompt(text: str) -> bool:
    return text.replace("\r", "").replace("\n", "").strip() == ">"


def _preferred_play_prompt(session, requested: str) -> str:
    """Replace only generic gameplay prompts, never login/menu questions."""

    if getattr(session, "character", None) is None or not _is_generic_play_prompt(requested):
        return requested

    # current_prompt_text is installed by the room/prompt experience and already
    # honors QUIET/COMPACT/FULL plus screen-reader quiet mode. Import lazily as a
    # fallback so this policy stays safe in focused tests that omit that runtime.
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        text = current()
    else:
        from mud.room_prompt_experience import prompt_text
        text = prompt_text(session, leading_newline=False)

    if requested.startswith("\r\n"):
        return "\r\n" + text
    if requested.startswith("\n"):
        return "\n" + text
    return text


def install_prompt_policy_runtime(player_session_class) -> None:
    """Make prompt preference ownership independent of command-wrapper order."""

    if getattr(player_session_class, "_prompt_policy_runtime_installed", False):
        return

    previous_prompt = player_session_class.prompt

    async def prompt(self, text: str) -> str | None:
        if getattr(self, "account", None) is not None:
            try:
                load_preferences(self)
            except Exception:
                pass
        return await previous_prompt(self, _preferred_play_prompt(self, text))

    player_session_class.prompt = prompt
    player_session_class._prompt_policy_runtime_installed = True


def install_final_runtime_policy(player_session_class) -> None:
    """Anchor final cross-cutting policies after the production stack is assembled."""

    install_accessibility_policy_runtime(player_session_class)
    install_prompt_policy_runtime(player_session_class)

    # Audit remediations intentionally sit after every authored/global command
    # wrapper so ownership decisions cannot be changed by later install order.
    install_runtime_remediation(player_session_class)

    player_session_class._final_runtime_policy_installed = True
