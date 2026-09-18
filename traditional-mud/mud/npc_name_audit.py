from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


TITLE_PREFIXES = {
    "road-captain",
    "keeper",
    "recorder",
    "shiftmaster",
    "claimwright",
    "hunter-mother",
    "free-name",
    "scribe",
    "guide",
    "marshal",
    "captain",
    "foreman",
    "warden",
    "steward",
    "quartermaster",
    "registrar",
    "priest",
    "high",
    "elder",
    "master",
    "mistress",
    "doctor",
    "factor",
    "broker",
    "chief",
    "sergeant",
    "archivist",
    "curator",
    "custodian",
    "engineer",
    "surveyor",
    "ranger",
    "hunter",
    "mother",
    "druid",
    "necromancer",
    "pathwarden",
    "scout",
    "witness",
    "wizard",
    "sergeant",
    "surveyor",
    "registrar",
    "healer",
    "mayor",
    "tender",
    "riveter",
    "pressure-clerk",
}

ROLE_NOUNS = {
    "guard",
    "informant",
    "peddler",
    "merchant",
    "trader",
    "clerk",
    "keeper",
    "warden",
    "priest",
    "acolyte",
    "hunter",
    "captain",
    "foreman",
    "steward",
    "factor",
    "broker",
    "scribe",
    "guide",
    "registrar",
    "engineer",
    "surveyor",
    "ranger",
    "hare",
    "squirrel",
    "wren",
    "stalker",
    "vendor",
    "worker",
    "watchman",
    "watcher",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


@dataclass(frozen=True, slots=True)
class NpcNameRecord:
    key: str
    name: str
    source: str


def _tokens(name: str) -> list[str]:
    return _TOKEN_RE.findall(name)


def likely_given_name(name: str) -> str | None:
    """Extract a likely personal first name from an authored NPC display name.

    This intentionally ignores role-only labels such as Blackwall Guard and
    Grey-Cloaked Informant. It is conservative: exact full-name duplication is
    audited separately, so a mononym still cannot silently duplicate exactly.
    """

    tokens = _tokens(name)
    while tokens and tokens[0].casefold() in TITLE_PREFIXES:
        tokens.pop(0)

    if len(tokens) < 2:
        return None
    if tokens[-1].casefold() in ROLE_NOUNS:
        return None
    return tokens[0].casefold()


def duplicate_full_names(records: Iterable[NpcNameRecord]) -> dict[str, tuple[NpcNameRecord, ...]]:
    grouped: dict[str, list[NpcNameRecord]] = defaultdict(list)
    for record in records:
        grouped[" ".join(record.name.casefold().split())].append(record)
    return {
        name: tuple(rows)
        for name, rows in grouped.items()
        if len({row.key for row in rows}) > 1
    }


def duplicate_given_names(records: Iterable[NpcNameRecord]) -> dict[str, tuple[NpcNameRecord, ...]]:
    grouped: dict[str, list[NpcNameRecord]] = defaultdict(list)
    for record in records:
        given = likely_given_name(record.name)
        if given:
            grouped[given].append(record)
    return {
        name: tuple(rows)
        for name, rows in grouped.items()
        if len({row.key for row in rows}) > 1
    }


def production_npc_name_records(world_module, mobile_module=None) -> tuple[NpcNameRecord, ...]:
    records: list[NpcNameRecord] = []
    seen_keys: set[tuple[str, str]] = set()

    for npc in world_module.NPCS_BY_KEY.values():
        identity = ("static", npc.key)
        if identity in seen_keys:
            continue
        seen_keys.add(identity)
        records.append(NpcNameRecord(npc.key, npc.name, "static"))

    if mobile_module is not None:
        for npc in mobile_module.MOBILE_NPCS_BY_KEY.values():
            identity = ("mobile", npc.key)
            if identity in seen_keys:
                continue
            seen_keys.add(identity)
            records.append(NpcNameRecord(npc.key, npc.name, "mobile"))

    return tuple(records)


def format_duplicate_report(
    full_names: dict[str, tuple[NpcNameRecord, ...]],
    given_names: dict[str, tuple[NpcNameRecord, ...]],
) -> str:
    lines: list[str] = []
    if full_names:
        lines.append("Duplicate full NPC display names:")
        for name, rows in sorted(full_names.items()):
            lines.append(
                f"- {name}: "
                + ", ".join(f"{row.key}={row.name!r}" for row in rows)
            )
    if given_names:
        lines.append("Duplicate likely NPC given names:")
        for name, rows in sorted(given_names.items()):
            lines.append(
                f"- {name}: "
                + ", ".join(f"{row.key}={row.name!r}" for row in rows)
            )
    return "\n".join(lines)
