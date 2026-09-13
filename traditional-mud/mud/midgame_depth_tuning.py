from __future__ import annotations

from dataclasses import replace

import mud.midgame_depth as depth
import mud.quests as quests
from mud.access import ContentGate


def apply_midgame_depth_quest_tuning() -> None:
    """Normalize the compact side-quest constructors into QuestDefinition fields."""

    normalized = []
    for quest in depth.SIDE_QUESTS:
        if isinstance(quest.gate, str) and isinstance(quest.description, tuple) and not quest.objective_steps:
            quest = replace(
                quest,
                gate=ContentGate(),
                description=quest.gate,
                objective_steps=quest.description,
            )
        normalized.append(quest)

    depth.SIDE_QUESTS = tuple(normalized)
    by_key = {quest.key: quest for quest in depth.SIDE_QUESTS}
    depth.LOCKMAKER_QUEST = by_key[depth.LOCKMAKER_QUEST_KEY]
    depth.LAST_CARGO_QUEST = by_key[depth.LAST_CARGO_QUEST_KEY]
    depth.QUIET_GAUGE_QUEST = by_key[depth.QUIET_GAUGE_QUEST_KEY]

    for quest in depth.SIDE_QUESTS:
        if quest.key in quests.QUESTS_BY_KEY:
            quests.QUESTS = tuple(quest if old.key == quest.key else old for old in quests.QUESTS)
        else:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
