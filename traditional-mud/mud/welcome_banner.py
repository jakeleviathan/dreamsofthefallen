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
    # Python's str.center() puts the odd padding column on the right. On an
    # even-width terminal that shifts the visual axis of odd-width glyphs one
    # column left. Bias the spare column to the left so |, V and other central
    # skyline marks sit on BANNER_WIDTH // 2.
    padding = max(0, BANNER_WIDTH - len(text))
    left = (padding + 1) // 2
    right = padding - left
    return (" " * left) + text + (" " * right)


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


# A true terminal illustration: no image escape sequences or Unicode dependency.
# The artwork is arranged in 76 interior columns between two frame characters.
# Symbol painting provides much more texture than one ANSI color per text line.
INK = "\x1b[38;5;238m"
STONE = "\x1b[38;5;250m"
BLUE = "\x1b[38;5;33m"
WATER = "\x1b[38;5;45m"
VIOLET = "\x1b[38;5;135m"
PINK = "\x1b[38;5;201m"
GREEN = "\x1b[38;5;48m"
FIRE = "\x1b[38;5;214m"

ART = (
    "       .       *     .                 *     .    +          .       ",
    "    *      .       .----.               .        /\\     .          ",
    "         .       .'      '.       *           /\\ /||\\       *      ",
    "  +             /   .--.   \\            /\\  /||\\||||\\   +          ",
    "      *         |  /    \\  |       .   /||\\ ||[]||||[]|             ",
    "   .            \\  \\    /  /       /\\  |||| ||[]||||[]|   .         ",
    "           +     '._'--'_.'  *    /||\\ |||| ||[]||||[]|         *   ",
    "       .             ''       /\\  |[]| ||[]||||[]|||||    .         ",
    "    *          +          /\\ /||\\ |[]| ||[]||||[]|||||             ",
    "           /\\         /\\ /||\\|[]| |[]| ||[]||||[]|||||      /\\     ",
    "     /\\   /||\\  /\\   /||\\|[]||[]|_|[]|_||[]||||[]||||| /\\  /||\\   ",
    "   _/||\\__|[]|__|[]|_|[]||[]||[][][][][][][][][][][][]|_|[]|__|[]|_",
    "   |[][][][][][][][][][][][][][][][][][][][][][][][][][][][][][][]|",
    "   |___    ____    ____    ____    ____    ____    ____    ____ __|",
    "       |  |    |  |    |  |    |  |    |  |    |  |    |  |       ",
    "  ~~~~~|~~|~~~~|~~|~~~~|~~|~~~~|~~|~~~~|~~|~~~~|~~|~~~~|~~~~~~~~",
    "  ~=~~~==~~~~==~~~==~~~~==~~~~==~~~~==~~~~==~~~~==~~~~==~~~~==~~~",
)

# Symmetric guardians and banners evoke the reference art in an 80-column client.
GUARDIANS = (
    "   /\\                                                  /\\",
    "  /##\\             +               +                /##\\",
    "  ||||          [*]                 [*]              ||||",
    "  ||||           |                   |               ||||",
    "  ||||         .-^-.               .-^-.             ||||",
    "  ||||        / ___ \\             / ___ \\            ||||",
    "  ||||       / /   \\ \\           / /   \\ \\           ||||",
    "  ||||       | |   | |           | |   | |           ||||",
    "  ||||       | |___| |           | |___| |           ||||",
    "  ||||       \\_______/           \\_______/           ||||",
)

def _symbol_style(char: str, base: str) -> str:
    if char in "*+":
        return GOLD
    if char in "[]#":
        return FIRE
    if char in "~=":
        return WATER
    if char in "/\\|_":
        return BLUE
    if char in ".'-":
        return TWILIGHT
    return base

def _mosaic(text: str, base: str = DREAMLIGHT) -> str:
    """Group adjacent pixels of the same shade, avoiding per-character resets."""
    result = []
    last = None
    for char in text:
        style = _symbol_style(char, base) if char != " " else last
        if style != last and style is not None:
            result.append(style)
            last = style
        result.append(char)
    return "".join(result) + RESET

def _framed(text: str = "", base: str = DREAMLIGHT) -> str:
    if len(text) > BANNER_WIDTH - 4:
        raise ValueError("Splash row exceeds a traditional 80-column terminal")
    inside = text.center(BANNER_WIDTH - 4)
    return _paint(GOLD, "|") + " " + _mosaic(inside, base) + " " + _paint(GOLD, "|")

def _headline(rows: tuple[str, ...], shades: tuple[str, ...]) -> list[str]:
    result = []
    for row in rows:
        offset = max(0, (BANNER_WIDTH - 4 - len(row)) // 2)
        pieces = []
        for index, char in enumerate(row):
            if char == " ":
                pieces.append(" ")
            else:
                pieces.append(shades[min(len(shades) - 1, index * len(shades) // max(len(row), 1))] + char)
        visible = " " * offset + "".join(pieces) + RESET
        pad = BANNER_WIDTH - 4 - offset - len(row)
        result.append(_paint(GOLD, "|") + " " + visible + " " * pad + " " + _paint(GOLD, "|"))
    return result

def build_welcome_banner() -> str:
    """A dense 78-column ANSI/ASCII Astralis cityscape for real Telnet clients."""
    lines = [
        "",
        _paint(GOLD, "+" + "=" * (BANNER_WIDTH - 2) + "+"),
        _framed(" .  *     D R E A M S   O F   T H E   F A L L E N      *  ."),
        _framed("  R E A L M S      Q U E S T S      M A G I C      L E G E N D S ", VIOLET),
        _paint(GOLD, "+" + "-" * (BANNER_WIDTH - 2) + "+"),
    ]
    lines.extend(_framed(row, (GOLD if i < 7 and 13 <= row.find(".") <= 25 else (WATER if i >= 14 else DREAMLIGHT))) for i, row in enumerate(ART[:13]))
    lines.extend(_framed(row, BLUE) for row in GUARDIANS[:4])
    lines.append(_framed("       *        THE CITY BEYOND THE FALLING STARS        *", GOLD))
    lines.extend(_headline(DREAMS_WORDMARK, (GOLD, FIRE, PINK, VIOLET)))
    lines.append(_framed("= = = = = = =    O F   T H E    = = = = = = =", GOLD))
    lines.extend(_headline(FALLEN_WORDMARK, (STARLIGHT, WATER, BLUE, VIOLET, PINK)))
    lines.extend(_framed(row, BLUE) for row in GUARDIANS[4:])
    lines.extend(_framed(row, WATER) for row in ART[13:])
    lines.extend([
        _framed("  A   T E X T - B A S E D   F A N T A S Y   A D V E N T U R E", GOLD),
        _framed(" < < <     E N T E R   T H E   W O R L D   O F   A S T R A L I S     > > >", WATER),
        _framed("RUINS  +  MYSTERY  +  MAGIC  +  EXPLORATION  +  COMMUNITY", PINK),
        _framed("The road remembers every soul that crossed it.", TWILIGHT),
        _paint(GOLD, "+" + "-" * (BANNER_WIDTH - 2) + "+"),
        _framed("A S T R A L I S", STARLIGHT),
        _framed("[ LOGIN / CREATE ACCOUNT ]", GOLD),
        _framed("Discord: https://discord.gg/MyW5XJWgzW", DREAMLIGHT),
        _framed("Enter your account name below to awaken.", SHADOW),
        _paint(GOLD, "+" + "=" * (BANNER_WIDTH - 2) + "+"),
        "",
    ])
    return "\r\n".join(lines) + "\r\n"


WELCOME_BANNER = build_welcome_banner()


def plain_welcome_banner() -> str:
    return _ANSI_RE.sub("", WELCOME_BANNER)


def visible_banner_widths() -> tuple[int, ...]:
    return tuple(_visible_width(line) for line in WELCOME_BANNER.splitlines())
