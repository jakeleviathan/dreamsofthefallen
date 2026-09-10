from __future__ import annotations

from mud.forest_elf_home_and_omens import (
    FOREST_ELF_HUSHED_VERGE_KEY,
    FOREST_ELF_OPENING_COMPLETE_FLAG,
    FOREST_ELF_VERGE_STUDIED_FLAG,
    ONE_TURN_FARTHER,
    _class_lens,
)
from mud.world import FOREST_ELF_START_ROOM_KEY


FOREST_ELF_HOMECOMING_FLAG = "forest_elf_returned_home_by_wayroot"
FOREST_ELF_CLOSING_SEEN_FLAG = "forest_elf_opening_closing_seen"
FOREST_ELF_HOMECOMING_STEP = "return_home"


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, ONE_TURN_FARTHER.key)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


async def study_signs_with_homecoming(session) -> bool:
    """Replace the old walk-home instruction with a deliberate homecoming beat."""
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "study_signs":
        return False
    if session.character.current_room != FOREST_ELF_HUSHED_VERGE_KEY:
        return False

    flag, text = _class_lens(session.character.character_class or "")
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, FOREST_ELF_VERGE_STUDIED_FLAG)
    session.database.advance_quest(session.character.id, ONE_TURN_FARTHER.key, FOREST_ELF_HOMECOMING_STEP)
    await session.send(
        "\r\n" + text + "\r\n\r\n"
        "Talen listens without trying to translate your discipline into his own. 'Good. One useful fact. Do not turn it into five facts because you want the answer early.'\r\n"
        "\r\nHe kneels beside an old root knot half-hidden under moss and brushes away a thumb-sized leaf-and-circle mark. A faint green line wakes beneath the bark.\r\n"
        "'The Circle keeps a few wayroots for wardens who need to bring someone home without dragging danger back along the path. It is a prepared road, not a trick for going anywhere you please.'\r\n"
        "When you are ready, type RETURN HOME.\r\n"
    )
    return True


async def return_home_by_wayroot(session) -> bool:
    """Carry a Forest Elf safely back to Circle Clearing through the prepared wayroot."""
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session)
    if not quest or quest.get("status") != "active":
        return False

    step = quest.get("current_step")
    if step not in {FOREST_ELF_HOMECOMING_STEP, "report_circle"}:
        return False
    if session.character.current_room != FOREST_ELF_HUSHED_VERGE_KEY:
        return False

    session.database.grant_flag(session.character.id, FOREST_ELF_HOMECOMING_FLAG)
    if step == FOREST_ELF_HOMECOMING_STEP:
        session.database.advance_quest(session.character.id, ONE_TURN_FARTHER.key, "report_circle")

    await session.send(
        "\r\nTalen puts two fingers against the old wayroot mark. The green line in the bark spreads into the surrounding roots, not bright enough to light the ground so much as make the shadows remember a different place.\r\n"
        "'Step where I step.'\r\n"
        "\r\nFor one breath there is wet earth under your boots, the smell of cedar, and the pressure of a path folding shorter than it should be. Then birdsong returns all at once.\r\n"
    )

    session.database.set_character_room(session.character.id, FOREST_ELF_START_ROOM_KEY)
    _refresh_character(session)

    await session.send(
        "You are back in Circle Clearing. The cups you set this morning are still beside the seven stones. Somebody has moved one bench. Bread smoke drifts in from Hearthwalk. Home did not stop while you were gone.\r\n"
        "\r\nThe Circle is waiting for the one thing you actually learned. REPORT SIGNS.\r\n\r\n"
    )
    show_room = getattr(session, "show_current_room", None)
    if callable(show_room):
        await show_room()
    return True


async def append_opening_closing_if_needed(session, *, was_active: bool) -> bool:
    """Add a one-time quiet completion beat after the older report handler finishes."""
    if session.character is None or session.character.race != "forest_elf" or not was_active:
        return False
    quest = _quest(session)
    if not quest or quest.get("status") != "completed":
        return False
    flags = _flags(session)
    if FOREST_ELF_CLOSING_SEEN_FLAG in flags:
        return False

    session.database.grant_flag(session.character.id, FOREST_ELF_CLOSING_SEEN_FLAG)
    session.database.grant_flag(session.character.id, FOREST_ELF_OPENING_COMPLETE_FLAG)
    await session.send(
        "\r\nFor a few moments the Circle keeps discussing the unsolved signs without you. Nobody turns the morning into a ceremony. Neris calls from Hearthwalk that somebody left a pruning knife by the oven. Sela remembers the rest of her lunch. A child runs across the clearing carrying too many apples.\r\n"
        "\r\nMaelis catches your eye once and nods toward the paths beyond the stones.\r\n"
        "'You know where home is now. The rest of Astralis is yours to walk.'\r\n"
        "\r\n--- Forest Elf opening complete. ---\r\n"
    )
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_forest_elf_homecoming_runtime(player_session_class) -> None:
    """Install the final Forest Elf return-home and quiet completion beats."""
    if getattr(player_session_class, "_forest_elf_homecoming_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "forest_elf":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {
            "study signs", "study disturbance", "read signs", "examine signs", "inspect signs", "study evidence"
        }:
            if await study_signs_with_homecoming(self):
                return

        if normalized in {
            "return home", "go home", "take wayroot", "use wayroot", "step through wayroot", "wayroot"
        }:
            if await return_home_by_wayroot(self):
                return

        before = _quest(self)
        was_active = bool(before and before.get("status") == "active")
        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {
            "report signs", "report verge", "report to circle", "share signs", "report disturbance"
        }:
            await append_opening_closing_if_needed(self, was_active=was_active)

        if normalized in {"help", "?"}:
            quest = _quest(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == FOREST_ELF_HOMECOMING_STEP:
                await self.send("Forest Elf homecoming: type RETURN HOME to take Talen's prepared wayroot back to Circle Clearing.\r\n")

    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_homecoming_runtime_installed = True
