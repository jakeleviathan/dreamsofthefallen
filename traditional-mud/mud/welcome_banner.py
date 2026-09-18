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

# 256-color stops for the title-art gradient. In capable clients the logo falls
# from electric blue through violet into hot pink. Accessibility/plain-Telnet
# policy still strips these ANSI sequences completely.
GRADIENT_256 = (
    33,   # deep electric blue
    39,
    45,
    63,
    69,
    99,
    105,
    135,
    141,
    171,
    177,
    207,
    213,  # pink
)

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


def _mirror_ascii(text: str) -> str:
    """Geometrically mirror a half-row, including slash direction."""
    mirrored: list[str] = []
    for char in reversed(text):
        if char == "/":
            mirrored.append("\\")
        elif char == "\\":
            mirrored.append("/")
        elif char == "<":
            mirrored.append(">")
        elif char == ">":
            mirrored.append("<")
        elif char == "(":
            mirrored.append(")")
        elif char == ")":
            mirrored.append("(")
        else:
            mirrored.append(char)
    return "".join(mirrored)


def _mirrored_row(left: str, center: str = " ") -> str:
    """Build one 77-column row around the splash's fixed center column."""
    if len(center) != 1:
        raise ValueError("Mirrored banner rows require one center character.")
    half_width = (BANNER_WIDTH - 2) // 2  # 38; 38 + center + 38 = 77.
    if len(left) > half_width:
        raise ValueError(f"Banner half-row is too wide: {left!r}")
    left = left.rjust(half_width)
    return left + center + _mirror_ascii(left)


# Every decorative row below is authored only once on the left. The right side is
# generated, so a hand-spaced edit can no longer make one side drift away from
# the other.
TOP_ORNAMENT = (
    _mirrored_row("      /\\       /\\       /\\", "^"),
    _mirrored_row(" /\\__/  \\_____/  \\_____/  \\", "|"),
    _mirrored_row(r"_/                                  ", "V"),
)

MID_ORNAMENT = (
    _mirrored_row(r"\__      ________      ________", "|"),
    _mirrored_row(r"   \____/        \____/       ", "V"),
)

DREAM_SIGIL = (
    r"\        |        /",
    r"\       |       /",
    r"\      |      /",
    r"------\     |     /------",
    r"\    |    /",
    r"\   |   /",
    r"\  |  /",
    r"\ | /",
    r"\|/",
    "V",
)


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{RESET}"


def _center(text: str) -> str:
    return text.center(BANNER_WIDTH)


def _visible_width(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def _gradient_style(position: int, total: int) -> str:
    if total <= 1:
        stop = GRADIENT_256[0]
    else:
        ratio = max(0.0, min(1.0, position / (total - 1)))
        index = round(ratio * (len(GRADIENT_256) - 1))
        stop = GRADIENT_256[index]
    return f"\x1b[1;38;5;{stop}m"


def _gradient_rows(rows: tuple[str, ...]) -> tuple[str, ...]:
    colored_positions = [index for index, row in enumerate(rows) if row]
    total = len(colored_positions)
    painted: list[str] = []
    color_position = 0
    for row in rows:
        if not row:
            painted.append("")
            continue
        painted.append(_paint(_gradient_style(color_position, total), _center(row)))
        color_position += 1
    return tuple(painted)


def build_welcome_banner() -> str:
    """Return the symmetric blue-purple-pink metal title treatment."""

    art_rows = (
        *TOP_ORNAMENT,
        "",
        *DREAMS_WORDMARK,
        "",
        "O F   T H E",
        "",
        *FALLEN_WORDMARK,
        "",
        *MID_ORNAMENT,
        "",
        *DREAM_SIGIL,
        "",
        "A S T R A L I S",
    )

    lines: list[str] = ["", *_gradient_rows(art_rows)]
    lines.extend(
        (
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
