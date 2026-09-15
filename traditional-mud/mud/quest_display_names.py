from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

import mud.quests as quests


def _quest_context_label(quest_key: str) -> str:
    """Return a short, stable presentation label derived from a quest key."""

    return quest_key.split("_", 1)[0].replace("_", " ").title()


def install_unique_quest_display_names() -> None:
    """Disambiguate duplicate quest titles without changing stable quest keys.

    Quest progress is persisted by ``QuestDefinition.key``.  This pass runs after
    production content assembly and changes only the player-facing ``name`` field.
    Both the tuple and dictionary registries are kept coherent, and the dictionary
    is mutated in place so modules that imported it earlier retain the same object.
    """

    # Some legacy installers append to QUESTS while newer code may register only
    # in QUESTS_BY_KEY. Audit the union so every production-visible definition is
    # covered without duplicating objects that already occur in the tuple.
    definitions_by_key = {quest.key: quest for quest in quests.QUESTS}
    definitions_by_key.update(quests.QUESTS_BY_KEY)

    by_name: dict[str, list[quests.QuestDefinition]] = defaultdict(list)
    for quest in definitions_by_key.values():
        by_name[quest.name].append(quest)

    replacements: dict[str, quests.QuestDefinition] = {}
    for display_name, group in by_name.items():
        if len(group) < 2:
            continue

        ordered = sorted(group, key=lambda quest: quest.key)
        short_labels = [_quest_context_label(quest.key) for quest in ordered]
        short_labels_are_unique = len(set(short_labels)) == len(short_labels)

        for quest, short_label in zip(ordered, short_labels):
            context = (
                short_label
                if short_labels_are_unique
                else quest.key.replace("_", " ").title()
            )
            replacements[quest.key] = replace(
                quest,
                name=f"{display_name} — {context}",
            )

    if not replacements:
        return

    quests.QUESTS = tuple(replacements.get(quest.key, quest) for quest in quests.QUESTS)
    for key, quest in tuple(quests.QUESTS_BY_KEY.items()):
        quests.QUESTS_BY_KEY[key] = replacements.get(key, quest)
