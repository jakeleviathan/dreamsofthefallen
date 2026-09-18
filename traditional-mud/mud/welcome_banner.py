from __future__ import annotations

import re


# Classic MUD clients still assume an 80-column terminal. The splash deliberately
# keeps every visible line at 78 columns or fewer, even though modern Mudlet
# windows are usually much wider.
BANNER_WIDTH = 78

RESET = "\x1b[0m"
IRON = "\x1b[37m"
SHADOW = "\x1b[90m"
GOLD = "\x1b[1;93m"
DREAMLIGHT = "\x1b[96m"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# Custom slanted terminal wordmarks: large enough to feel like a logo, but made
# entirely from 7-bit ASCII so old Telnet clients do not need Unicode glyphs.
DREAMS_WORDMARK = (
    r"    ____  ____  _________    __  _______",
    r"   / __ \/ __ \/ ____/   |  /  |/  / ___/",
    "  / / / / /_/ / __/ / /| | / /|_/ /\\__ \\",
    r" / /_/ / _, _/ /___/ ___ |/ /  / /___/ /",
    r"/_____/_/ |_/_____/_/  |_/_/  /_//____/",
)

FALLEN_WORDMARK = (
    r"    _________    __    __    _______   __",
    r"   / ____/   |  / /   / /   / ____/ | / /",
    r"  / /_  / /| | / /   / /   / __/ /  |/ /",
    r" / __/ / ___ |/ /___/ /___/ /___/ /|  /",
    r"/_/   /_/  |_/_____/_____/_____/_/ |_/",
)


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{RESET}"


def _center(text: str) -> str:
    return text.center(BANNER_WIDTH)


def _visible_width(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def build_welcome_banner() -> str:
    """Return the heavy-metal title treatment used before login."""

    lines: list[str] = [
        "",
        _paint(SHADOW, _center("       /\\          /\\                    /\\          /\\")),
        _paint(SHADOW, _center(r"  /\__/  \___/\___/  \___/\____/\____/  \___/\___/  \__/\  ")),
        _paint(SHADOW, _center(r"_/                                                          \_")),
        "",
    ]

    lines.extend(_paint(IRON, _center(line)) for line in DREAMS_WORDMARK)
    lines.extend(("", _paint(GOLD, _center("O F   T H E")), ""))
    lines.extend(_paint(IRON, _center(line)) for line in FALLEN_WORDMARK)

    lines.extend(
        (
            "",
            _paint(SHADOW, _center(r"\__      ________      ________      ________      ________      __/")),
            _paint(SHADOW, _center(r"   \____/        \____/        \____/        \____/        \____/")),
            "",
            _paint(DREAMLIGHT, _center(r"\        |        /")),
            _paint(DREAMLIGHT, _center(r" \       |       /")),
            _paint(DREAMLIGHT, _center(r"  \      |      /")),
            _paint(DREAMLIGHT, _center(r"------\     |     /------")),
            _paint(DREAMLIGHT, _center(r"      \    |    /")),
            _paint(DREAMLIGHT, _center(r"       \   |   /")),
            _paint(DREAMLIGHT, _center(r"        \  |  /")),
            _paint(DREAMLIGHT, _center(r"         \ | /")),
            _paint(DREAMLIGHT, _center(r"          \|/")),
            _paint(DREAMLIGHT, _center("V")),
            "",
            _paint(GOLD, _center("A S T R A L I S")),
            _paint(SHADOW, _center("DREAMS OF THE FALLEN // ASTRALIS")),
            _paint(SHADOW, _center("Beneath Astralis, something dreams.")),
            "",
            _paint(GOLD, _center("LOGIN     CREATE ACCOUNT")),
            _paint(SHADOW, _center("Type HELP for a brief explanation.")),
            "",
        )
    )
    return "\r\n".join(lines) + "\r\n"


WELCOME_BANNER = build_welcome_banner()


def plain_welcome_banner() -> str:
    """ANSI-free banner used by tests and accessibility checks."""

    return _ANSI_RE.sub("", WELCOME_BANNER)


def visible_banner_widths() -> tuple[int, ...]:
    return tuple(_visible_width(line) for line in WELCOME_BANNER.splitlines())
