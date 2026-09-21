from __future__ import annotations

from dataclasses import replace

import mud.quests as quests


# Player progression is persisted by these stable keys, not by the display title.
# Keep the original authored title on one quest in each collision and make only the
# conflicting later title more specific.
QUEST_DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "first_ten_undead_capstone": "No Voice Above You - Necropolis Capstone",
    "broken_reach_three_claims": "Three Claims on One Road - Broken Reach",
}


def install_unique_quest_display_names() -> None:
    """Apply presentation-only title overrides after production content assembly."""

    replacements: dict[str, quests.QuestDefinition] = {}
    for key, display_name in QUEST_DISPLAY_NAME_OVERRIDES.items():
        quest = quests.QUESTS_BY_KEY.get(key)
        if quest is None:
            continue
        replacements[key] = replace(quest, name=display_name)

    if not replacements:
        return

    quests.QUESTS = tuple(replacements.get(quest.key, quest) for quest in quests.QUESTS)
    for key, quest in tuple(quests.QUESTS_BY_KEY.items()):
        quests.QUESTS_BY_KEY[key] = replacements.get(key, quest)
