from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from mud.npc_name_audit import likely_given_name


_TALK_RE = re.compile(
    r"\bTALK(?:\s+TO)?\s+([A-Z][A-Z'-]*(?:\s+[A-Z][A-Z'-]+){0,2})\b"
)

# Quest prose deliberately uses role targets in a few places where the actual
# person is discovered in play rather than named in advance. These are commands,
# not proper-name references, so they are valid without a unique named NPC.
GENERIC_TALK_TARGETS = {
    "acolyte",
    "alchemist",
    "archivist",
    "broker",
    "captain",
    "clerk",
    "druid",
    "diver",
    "engineer",
    "factor",
    "foreman",
    "guard",
    "guide",
    "healer",
    "herbalist",
    "informant",
    "keeper",
    "merchant",
    "mentor",
    "priest",
    "quartermaster",
    "ranger",
    "registrar",
    "scout",
    "scribe",
    "steward",
    "surveyor",
    "trader",
    "vendor",
    "warden",
    "wizard",
}


@dataclass(frozen=True, slots=True)
class QuestTalkReference:
    quest_key: str
    step_key: str
    target: str
    objective: str


def _normalize(value: str) -> str:
    return " ".join(
        value.lower().replace("-", " ").replace("'", " ").split()
    )


def _trim_target(raw: str) -> str:
    # The regexp can consume an all-caps conjunction after a one-word target,
    # e.g. TALK BRIN AND RETURN. Stop those prose continuations here.
    words = raw.split()
    stop = {"ABOUT", "AND", "OR", "THEN", "BEFORE", "AFTER", "TO", "AT", "IN", "ON", "WITH", "FOR"}
    kept: list[str] = []
    for word in words:
        if kept and word in stop:
            break
        kept.append(word)
    return " ".join(kept)


def quest_talk_references(quests_by_key) -> tuple[QuestTalkReference, ...]:
    refs: list[QuestTalkReference] = []
    for quest in quests_by_key.values():
        for step_key, objective in quest.objective_steps:
            for match in _TALK_RE.finditer(objective):
                target = _trim_target(match.group(1))
                if target:
                    refs.append(QuestTalkReference(quest.key, step_key, target, objective))
    return tuple(refs)


def npc_talk_names(npcs_by_key) -> set[str]:
    names: set[str] = set()
    for npc in npcs_by_key.values():
        full = _normalize(npc.name)
        if full:
            names.add(full)
        given = likely_given_name(npc.name, getattr(npc, "role", ""))
        if given:
            names.add(_normalize(given))
        tokens = [
            token
            for token in re.findall(r"[A-Za-z][A-Za-z'-]*", npc.name)
            if token.casefold() not in GENERIC_TALK_TARGETS
        ]
        # Surnames and distinctive name-parts are common MUD talk targets too.
        for token in tokens:
            names.add(_normalize(token))
        for index in range(len(tokens)):
            suffix = _normalize(" ".join(tokens[index:]))
            if suffix:
                names.add(suffix)
    return names


def stale_quest_talk_references(quests_by_key, npcs_by_key) -> tuple[QuestTalkReference, ...]:
    known = npc_talk_names(npcs_by_key)
    stale: list[QuestTalkReference] = []
    for ref in quest_talk_references(quests_by_key):
        target = _normalize(ref.target)
        if target in GENERIC_TALK_TARGETS:
            continue
        if target not in known:
            stale.append(ref)
    return tuple(stale)


def validate_quest_talk_references(quests_by_key, npcs_by_key) -> int:
    refs = quest_talk_references(quests_by_key)
    stale = stale_quest_talk_references(quests_by_key, npcs_by_key)
    if stale:
        details = "\n".join(
            f"- {row.quest_key}:{row.step_key}: TALK {row.target} :: {row.objective}"
            for row in stale
        )
        raise RuntimeError(
            "Quest objectives reference TALK targets that no longer match any authored NPC:\n"
            + details
        )
    return len(refs)
