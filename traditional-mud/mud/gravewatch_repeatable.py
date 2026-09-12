from __future__ import annotations

from mud.gravewatch_keep import (
    GRAVEWATCH_ARCHER_PULL_FLAG,
    GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
    GRAVEWATCH_CASTELLAN_DEFEATED_FLAG,
    GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
    GRAVEWATCH_COMPLETE_FLAG,
    GRAVEWATCH_GATE_OPEN_FLAG,
    GRAVEWATCH_HOUND_PULL_FLAG,
    GRAVEWATCH_PIKE_PULL_FLAG,
    GRAVEWATCH_RIVER_MILE_KEY,
)


GRAVEWATCH_REPEAT_RUN_FLAGS = (
    GRAVEWATCH_HOUND_PULL_FLAG,
    GRAVEWATCH_ARCHER_PULL_FLAG,
    GRAVEWATCH_PIKE_PULL_FLAG,
    GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
    GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
    GRAVEWATCH_GATE_OPEN_FLAG,
    GRAVEWATCH_CASTELLAN_DEFEATED_FLAG,
)


def reset_gravewatch_patrol(session) -> tuple[bool, str]:
    """Issue a fresh repeat-run slate after the one-time first clear.

    Gravewatch is an open-world MUD dungeon rather than a private instance. The
    reset is framed as taking a new Veyran patrol assignment; mechanically it
    clears only the run-state flags. The one-time quest completion, XP, signet,
    and surcoat remain permanent.
    """
    if session.character is None:
        return False, "No active character."
    if session.character.current_room != GRAVEWATCH_RIVER_MILE_KEY:
        return False, "Fresh Gravewatch patrols are issued only at Sergeant Toma Reed's River Mile camp."
    flags = set(session.database.list_flags(session.character.id))
    if GRAVEWATCH_COMPLETE_FLAG not in flags:
        return False, "Complete The Dead Garrison once before taking repeat Gravewatch patrols."
    for flag in GRAVEWATCH_REPEAT_RUN_FLAGS:
        session.database.revoke_flag(session.character.id, flag)
    return True, (
        "Toma scratches a new date across a patrol slate. 'Same keep, fresh clear. "
        "The dead pull themselves back into the old formation eventually. Strip Rell's courtyard again if you want the clean captain fight.' "
        "Gravewatch run state reset; your first-clear rewards and completion remain recorded."
    )


def install_gravewatch_repeatable_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_gravewatch_repeatable_runtime_installed", False):
        return

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        if normalized in {
            "take gravewatch patrol",
            "take new patrol",
            "new gravewatch run",
            "start gravewatch run",
            "reset gravewatch",
            "reset keep",
        }:
            ok, message = reset_gravewatch_patrol(self)
            await self.send(message + "\r\n")
            if ok:
                return
            # The command was still intentionally handled even if the player is
            # in the wrong place or has not earned repeat access yet.
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str):
            return command

        self.prompt = replay_prompt
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._gravewatch_repeatable_runtime_installed = True
