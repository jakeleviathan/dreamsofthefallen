from __future__ import annotations

import re


# The login splash is deliberately built as terminal art rather than a rectangular
# plaque. It stays under 90 visible columns so it fits a normal Mudlet window and
# remains readable in ordinary Telnet clients.
BANNER_WIDTH = 88

RESET = "\x1b[0m"
IRON = "\x1b[37m"
SHADOW = "\x1b[90m"
GOLD = "\x1b[1;93m"
DREAMLIGHT = "\x1b[96m"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


DREAMS_WORDMARK = (
    "██████╗ ██████╗ ███████╗ █████╗ ███╗   ███╗███████╗",
    "██╔══██╗██╔══██╗██╔════╝██╔══██╗████╗ ████║██╔════╝",
    "██║  ██║██████╔╝█████╗  ███████║██╔████╔██║███████╗",
    "██║  ██║██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║╚════██║",
    "██████╔╝██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████║",
    "╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝",
)

FALLEN_WORDMARK = (
    "███████╗ █████╗ ██╗     ██╗     ███████╗███╗   ██╗",
    "██╔════╝██╔══██╗██║     ██║     ██╔════╝████╗  ██║",
    "█████╗  ███████║██║     ██║     █████╗  ██╔██╗ ██║",
    "██╔══╝  ██╔══██║██║     ██║     ██╔══╝  ██║╚██╗██║",
    "██║     ██║  ██║███████╗███████╗███████╗██║ ╚████║",
    "╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═══╝",
)


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{RESET}"


def _center(text: str) -> str:
    return text.center(BANNER_WIDTH)


def _visible_width(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def build_welcome_banner() -> str:
    """Return the large heavy-metal title treatment used before login."""

    lines: list[str] = [
        "",
        _paint(SHADOW, _center(" /\\              /\\                    /\\              /\\ ")),
        _paint(SHADOW, _center("/  \\      /\\    /  \\      /\\      /  \\    /\\      /  \\")),
        _paint(SHADOW, _center("___/    \\____/  \\__/    \\____/  \\____/    \\__/  \\____/    \\___")),
        _paint(SHADOW, _center("\\      \\                                                  /      /")),
        "",
    ]

    lines.extend(_paint(IRON, _center(line)) for line in DREAMS_WORDMARK)
    lines.extend(
        (
            "",
            _paint(GOLD, _center("O F   T H E")),
            "",
        )
    )
    lines.extend(_paint(IRON, _center(line)) for line in FALLEN_WORDMARK)

    lines.extend(
        (
            "",
            _paint(SHADOW, _center("\\____      ____________      ____________      ____________      ____/")),
            _paint(SHADOW, _center("     \\    /            \\    /            \\    /            \\    /")),
            _paint(SHADOW, _center("      \\  /              \\  /              \\  /              \\  /")),
            _paint(SHADOW, _center("       \\/                \\/                \\/                \\/")),
            "",
            _paint(DREAMLIGHT, _center("\\        |        /")),
            _paint(DREAMLIGHT, _center("\\       |       /")),
            _paint(DREAMLIGHT, _center("\\      |      /")),
            _paint(DREAMLIGHT, _center("──────\\     |     /──────")),
            _paint(DREAMLIGHT, _center("\\    |    /")),
            _paint(DREAMLIGHT, _center("\\   |   /")),
            _paint(DREAMLIGHT, _center("\\  |  /")),
            _paint(DREAMLIGHT, _center("\\ | /")),
            _paint(DREAMLIGHT, _center("\\|/")),
            _paint(DREAMLIGHT, _center("▼")),
            "",
            _paint(GOLD, _center("A S T R A L I S")),
            _paint(SHADOW, _center("Beneath Astralis, something dreams.")),
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
