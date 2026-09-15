from __future__ import annotations

from dataclasses import dataclass

from mud.mechanics import PROGRESSION_RULES


@dataclass(frozen=True, slots=True)
class QuestExperienceRules:
    """Quest completion contributes meaningfully to leveling without replacing combat.

    Structured quests carry the larger default reward; discovery quests carry a
    smaller reward so optional exploration matters without becoming the dominant
    leveling strategy. Rewards are based on the quest's authored minimum level,
    not how long a player waits before turning it in.
    """

    structured_fraction: float = 0.25
    discovery_fraction: float = 0.12
    minimum_structured_reward: int = 25
    minimum_discovery_reward: int = 12


QUEST_EXPERIENCE_RULES = QuestExperienceRules()


def quest_experience_reward(quest) -> int:
    """Return the fallback XP reward for an authored quest definition."""

    explicit = getattr(quest, "experience_reward", None)
    if explicit is not None:
        return max(0, int(explicit))

    authored_level = max(1, int(getattr(quest, "minimum_level", 1) or 1))
    requirement = PROGRESSION_RULES.xp_to_next_level(authored_level)
    style = str(getattr(quest, "style", "")).strip().lower()

    if style == "discovery":
        return max(
            QUEST_EXPERIENCE_RULES.minimum_discovery_reward,
            int(round(requirement * QUEST_EXPERIENCE_RULES.discovery_fraction)),
        )

    return max(
        QUEST_EXPERIENCE_RULES.minimum_structured_reward,
        int(round(requirement * QUEST_EXPERIENCE_RULES.structured_fraction)),
    )


def _character_progress(database, character_id: int) -> tuple[int, int] | None:
    with database.connect() as db:
        row = db.execute(
            "SELECT level, experience FROM characters WHERE id = ?",
            (character_id,),
        ).fetchone()
    if row is None:
        return None
    return int(row["level"]), int(row["experience"])


def _progress_advanced(
    progress: tuple[int, int] | None,
    old_level: int,
    old_experience: int,
) -> bool:
    if progress is None:
        return False
    level, experience = progress
    return level > old_level or (level == old_level and experience > old_experience)


def _queue_reward_event(database, character_id: int, event: dict) -> None:
    events = getattr(database, "_quest_experience_events", None)
    if events is None:
        events = {}
        database._quest_experience_events = events
    events.setdefault(int(character_id), []).append(event)


def _drain_reward_events(database, character_id: int) -> list[dict]:
    events = getattr(database, "_quest_experience_events", None)
    if not events:
        return []
    return list(events.pop(int(character_id), []))


def install_quest_experience_database_hook(database_class) -> None:
    """Queue fallback quest XP without stacking on authored rewards.

    Older content frequently calls ``complete_quest`` and then awards its own
    hand-tuned XP. The universal system therefore waits until the command has
    finished. If XP/level progress changed after completion, the authored reward
    wins. Otherwise the universal formula fills the gap exactly once.
    """

    if getattr(database_class, "_quest_experience_hook_installed", False):
        return

    previous_complete_quest = database_class.complete_quest

    def complete_quest(self, character_id: int, quest_key: str):
        before_quest = self.get_quest(character_id, quest_key)
        if before_quest is None or str(before_quest.get("status", "")) != "active":
            return previous_complete_quest(self, character_id, quest_key)

        before_progress = _character_progress(self, character_id)
        result = previous_complete_quest(self, character_id, quest_key)
        after_quest = self.get_quest(character_id, quest_key)
        if (
            before_progress is None
            or after_quest is None
            or str(after_quest.get("status", "")) != "completed"
        ):
            return result

        from mud.quests import QUESTS_BY_KEY

        quest = QUESTS_BY_KEY.get(quest_key)
        if quest is None:
            return result

        reward = quest_experience_reward(quest)
        if reward <= 0:
            return result

        old_level, old_experience = before_progress
        _queue_reward_event(
            self,
            character_id,
            {
                "quest_key": quest_key,
                "quest_name": getattr(quest, "name", quest_key),
                "fallback_experience": reward,
                "old_level": old_level,
                "old_experience": old_experience,
            },
        )
        return result

    database_class.complete_quest = complete_quest
    database_class._quest_experience_hook_installed = True


async def _flush_reward_events(session) -> None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return

    events = _drain_reward_events(database, character.id)
    if not events:
        return

    # Snapshot before applying any fallback rewards. Content that supplied an
    # authored reward after complete_quest has already advanced this progress.
    progress_before_fallback = _character_progress(database, character.id)

    for event in events:
        old_level = int(event.get("old_level", 1))
        old_experience = int(event.get("old_experience", 0))

        if _progress_advanced(
            progress_before_fallback,
            old_level,
            old_experience,
        ):
            # Authored content already paid this completion. Do not stack the
            # formula-driven fallback or duplicate its player-facing message.
            continue

        reward = max(0, int(event.get("fallback_experience", 0)))
        if reward <= 0:
            continue

        database.add_experience(character.id, reward)
        after_progress = _character_progress(database, character.id)
        name = str(event.get("quest_name", "Quest"))
        await session.send(f"Quest reward - {name}: you gain {reward} experience.\r\n")

        if after_progress is not None and after_progress[0] > old_level:
            await session.send(
                f"*** You have reached level {after_progress[0]}! ***\r\n"
            )

    refreshed = database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed

    try:
        await session.send_client_state()
    except Exception:
        pass


def install_quest_experience_runtime(player_session_class, database_class) -> None:
    """Install fallback quest XP plus player-facing reward messages."""

    install_quest_experience_database_hook(database_class)

    if getattr(player_session_class, "_quest_experience_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        try:
            await previous_playing_prompt(self)
        finally:
            await _flush_reward_events(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._quest_experience_runtime_installed = True
