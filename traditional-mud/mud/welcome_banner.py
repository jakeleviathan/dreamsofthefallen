from __future__ import annotations

import re


# Classic MUD clients still assume an 80-column terminal. The splash deliberately
# keeps every visible line at 78 columns or fewer so it remains clean in old
# Telnet clients while still looking intentional in modern Mudlet windows.
BANNER_WIDTH = 78

RESET = "\x1b[0m"
STARLIGHT = "\x1b[1;97m"
DREAMLIGHT = "\x1b[96m"
TWILIGHT = "\x1b[38;5;141m"
GOLD = "\x1b[1;38;5;220m"
SHADOW = "\x1b[90m"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# Hand-built slanted wordmarks. They use only 7-bit ASCII so the title remains
# readable in basic Telnet clients and when ANSI color is stripped.
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


# The upper silhouette suggests a celestial gate opening in cloudbanks. Beneath
# the title, a luminous skyline now makes the destination feel like an actual
# impossible city suspended above Astralis rather than an abstract rune.
CELESTIAL_GATE = (
    ".        *            |            *        .",
    "       .-----.        |        .-----.",
    ".----'       `---.    |    .---'       `----.",
    "___/                  \\___|___/                  \\___",
    "_/       .--.        .---\\ | /---.        .--.       \\_",
    "------'________/    \\______/      \\|/      \\______/    \\________`------",
    "|",
    "*",
)

CELESTIAL_SKYLINE = (
    ".              *              .",
    "*              |              *",
    "/\\             /|\\             /\\",
    "/  \\       /\\ / | \\ /\\       /  \\",
    "|[]|      /  \\  |  /  \\      |[]|",
    "|  |  /\\  | [] .-+-. [] |  /\\  |  |",
    "|__|_/  \\_|____|_|_|____|_/  \\_|__|",
    "/____| [] |  .-/___\\-.  | [] |____\\",
    "| [] |____|__|  _  |__|____| [] |",
    "|_____|____|__|_|_|__|____|_____|",
    "------------|_______|------------",
    "\\             |             /",
    "\\            |            /",
    "\\           |           /",
    "\\          |          /",
    "\\         |         /",
    "\\        |        /",
    "\\       |       /",
    "\\      |      /",
    "\\     |     /",
    "\\    |    /",
    "\\   |   /",
    "\\  |  /",
    "\\ | /",
    "\\|/",
    "V",
)

# Backwards-compatible name for any older imports or tools that referenced the
# previous abstract lower sigil.
FALLING_SIGIL = CELESTIAL_SKYLINE


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{RESET}"


def _center(text: str) -> str:
    return text.center(BANNER_WIDTH)


def _visible_width(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def _paint_rows(rows: tuple[str, ...], styles: tuple[str, ...]) -> tuple[str, ...]:
    if len(rows) != len(styles):
        raise ValueError("Each banner row requires exactly one style.")
    return tuple(_paint(style, _center(row)) for row, style in zip(rows, styles))


def _paint_wordmark(rows: tuple[str, ...], style: str) -> tuple[str, ...]:
    """Center a hand-spaced ASCII wordmark as one block, preserving its slant."""
    width = max(len(row) for row in rows)
    left = max(0, (BANNER_WIDTH - width) // 2)
    return tuple(_paint(style, (" " * left) + row) for row in rows)


def build_welcome_banner() -> str:
    """Return the terminal-native celestial Dreams of the Fallen splash."""

    gate = _paint_rows(
        CELESTIAL_GATE,
        (
            GOLD,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            STARLIGHT,
            DREAMLIGHT,
            TWILIGHT,
            GOLD,
        ),
    )
    dreams = _paint_wordmark(DREAMS_WORDMARK, STARLIGHT)
    fallen = _paint_wordmark(FALLEN_WORDMARK, STARLIGHT)
    skyline = _paint_rows(
        CELESTIAL_SKYLINE,
        (
            TWILIGHT,
            GOLD,
            DREAMLIGHT,
            STARLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            STARLIGHT,
            STARLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            TWILIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            DREAMLIGHT,
            GOLD,
        ),
    )

    lines: list[str] = [
        "",
        *gate,
        "",
        *dreams,
        _paint(GOLD, _center("O F   T H E")),
        *fallen,
        "",
        _paint(TWILIGHT, _center("The road remembers every soul that crossed it.")),
        "",
        *skyline,
        "",
        _paint(STARLIGHT, _center("A S T R A L I S")),
        _paint(DREAMLIGHT, _center("-----+-----+-----")),
        "",
        _paint(GOLD, _center("[ LOGIN / CREATE ACCOUNT ]")),
        _paint(DREAMLIGHT, _center("Discord: https://discord.gg/MyW5XJWgzW")),
        _paint(SHADOW, _center("Enter your account name below to awaken.")),
        "",
    ]
    return "\r\n".join(lines) + "\r\n"


WELCOME_BANNER = build_welcome_banner()


def plain_welcome_banner() -> str:
    """ANSI-free banner used by tests and accessibility presentation."""
    return _ANSI_RE.sub("", WELCOME_BANNER)


def visible_banner_widths() -> tuple[int, ...]:
    return tuple(_visible_width(line) for line in WELCOME_BANNER.splitlines())
