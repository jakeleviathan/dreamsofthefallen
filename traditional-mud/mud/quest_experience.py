from __future__ import annotations

from dataclasses import dataclass

from mud.mechanics import PROGRESSION_RULES


@dataclass(frozen=True, slots=True)
class QuestExperienceRules:
    """Quest completion contributes meaningfully to leveling without replacing combat.

    Structured quests carry the larger default reward; discovery quests carry a
    smaller reward so optional exploration matters without becoming the dominant
    leveling strategy. Rewards are based on the quest's authored minimum level,
    not how long a player waits before turning it in, and completion can only pay
    once because only an active -> completed transition is eligible.
    """

    structured_fraction: float = 0.25
    discovery_fraction: float = 0.12
    minimum_structured_reward: int = 25
    minimum_discovery_reward: int = 12


QUEST_EXPERIENCE_RULES = QuestExperienceRules()


def quest_experience_reward(quest) -> int:
    """Return the one-time XP reward for an authored quest definition."""

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

    # Structured is the normal story path and the safe default for any older
    # authored quest that predates the style distinction.
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
    """Make every registered authored quest completion grant XP exactly once."""

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

        # Content modules register quests during server assembly, so import the
        # live registry at completion time rather than freezing an early snapshot.
        from mud.quests import QUESTS_BY_KEY

        quest = QUESTS_BY_KEY.get(quest_key)
        if quest is None:
            return result

        old_level, old_experience = before_progress
        reward = quest_experience_reward(quest)
        if reward <= 0:
            return result

        self.add_experience(character_id, reward)
        after_progress = _character_progress(self, character_id)
        if after_progress is None:
            return result

        new_level, new_experience = after_progress
        actual_gain = max(0, new_experience - old_experience)
        _queue_reward_event(
            self,
            character_id,
            {
                "quest_key": quest_key,
                "quest_name": getattr(quest, "name", quest_key),
                "experience": actual_gain,
                "old_level": old_level,
                "new_level": new_level,
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

    refreshed = database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed

    for event in events:
        gained = int(event.get("experience", 0))
        name = str(event.get("quest_name", "Quest"))
        if gained > 0:
            await session.send(f"Quest reward - {name}: you gain {gained} experience.\r\n")

        old_level = int(event.get("old_level", 1))
        new_level = int(event.get("new_level", old_level))
        if new_level > old_level:
            await session.send(f"*** You have reached level {new_level}! ***\r\n")

    # Level changes can unlock abilities and increase maximum movement. Existing
    # client-state wrappers rebuild those derived values for the HUD immediately.
    try:
        await session.send_client_state()
    except Exception:
        pass


def install_quest_experience_runtime(player_session_class, database_class) -> None:
    """Install persistent quest XP plus player-facing reward messages."""

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
