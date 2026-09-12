from __future__ import annotations

from mud.gravewatch_keep import (
    CAPTAIN_KEY,
    CHAPLAIN_KEY,
    COURTYARD_ARCHER_KEY,
    COURTYARD_HOUND_KEY,
    COURTYARD_PIKE_KEY,
    GRAVEWATCH_ARCHER_PULL_FLAG,
    GRAVEWATCH_CAPTAIN_DEFEATED_FLAG,
    GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG,
    GRAVEWATCH_GATE_OPEN_FLAG,
    GRAVEWATCH_HOUND_PULL_FLAG,
    GRAVEWATCH_PIKE_PULL_FLAG,
    GRAVEWATCH_QUEST_KEY,
    GRAVEWATCH_CASTELLAN_DEFEATED_FLAG,
    REINFORCED_CAPTAIN_KEY,
    CASTELLAN_KEY,
)


PULL_FLAGS = {
    COURTYARD_HOUND_KEY: GRAVEWATCH_HOUND_PULL_FLAG,
    COURTYARD_ARCHER_KEY: GRAVEWATCH_ARCHER_PULL_FLAG,
    COURTYARD_PIKE_KEY: GRAVEWATCH_PIKE_PULL_FLAG,
}


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, GRAVEWATCH_QUEST_KEY)


def _grant_and_advance(session, flag: str, expected_step: str, next_step: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    existing = set(session.database.list_flags(character.id))
    changed = flag not in existing
    if changed:
        session.database.grant_flag(character.id, flag)
    q = _quest(session)
    if q and q.get("status") == "active" and q.get("current_step") == expected_step:
        session.database.advance_quest(character.id, GRAVEWATCH_QUEST_KEY, next_step)
        changed = True
    return changed


def _victory_sessions(session, enemy) -> list:
    finder = getattr(session, "party_victory_sessions", None)
    if callable(finder):
        result = finder(enemy)
        if result:
            return list(result)
    return [session]


def _room_party_sessions(session) -> list:
    finder = getattr(session, "party_sessions_here", None)
    if callable(finder):
        result = finder()
        if result:
            return list(result)
    return [session]


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_gravewatch_party_runtime(player_session_class) -> None:
    """Share Gravewatch encounter progress with party members who actually fought.

    Gravewatch remains character-progressed, but a group should not defeat the
    same officer once per character just to walk through the same door. Pull and
    boss credit goes to same-room encounter participants; the portcullis action
    goes to party members physically present at the winch. First-clear beacon
    rewards remain personal and must still be claimed by each character.
    """
    if getattr(player_session_class, "_gravewatch_party_runtime_installed", False):
        return

    previous_finish = player_session_class._finish_enemy_defeat
    previous_prompt = player_session_class.playing_prompt

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        participants = _victory_sessions(self, enemy)
        await previous_finish(self, enemy)
        if len(participants) <= 1:
            return

        if key in PULL_FLAGS:
            flag = PULL_FLAGS[key]
            for member in participants:
                if member is self:
                    continue
                character = getattr(member, "character", None)
                if character is None:
                    continue
                if flag not in set(member.database.list_flags(character.id)):
                    member.database.grant_flag(character.id, flag)
                    await member.send("[Party Progress] Your group cleared that Courtyard of Standards patrol element.\r\n")
            return

        if key in {CAPTAIN_KEY, REINFORCED_CAPTAIN_KEY}:
            for member in participants:
                if member is self:
                    continue
                if _grant_and_advance(member, GRAVEWATCH_CAPTAIN_DEFEATED_FLAG, "defeat_captain", "silence_chapel"):
                    await member.send("[Party Progress] Captain Rell is down for your Gravewatch run; the chapel lane is open.\r\n")
            return

        if key == CHAPLAIN_KEY:
            for member in participants:
                if member is self:
                    continue
                if _grant_and_advance(member, GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG, "silence_chapel", "open_inner_gate"):
                    await member.send("[Party Progress] Bell-Wight Halden is down for your Gravewatch run; the ossuary route is clear.\r\n")
            return

        if key == CASTELLAN_KEY:
            for member in participants:
                if member is self:
                    continue
                if _grant_and_advance(member, GRAVEWATCH_CASTELLAN_DEFEATED_FLAG, "defeat_castellan", "light_beacon"):
                    await member.send("[Party Progress] Merrow Kade is down for your Gravewatch run. Reach the map room and LIGHT BEACON to claim your personal first-clear reward.\r\n")

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        opening_gate = normalized in {"open portcullis", "raise portcullis", "open inner gate", "raise gate"}
        members = _room_party_sessions(self) if opening_gate else []

        await _delegate_command(self, previous_prompt, command)

        if not opening_gate or getattr(self, "character", None) is None:
            return
        actor_flags = set(self.database.list_flags(self.character.id))
        if GRAVEWATCH_GATE_OPEN_FLAG not in actor_flags:
            return
        for member in members:
            if member is self:
                continue
            character = getattr(member, "character", None)
            if character is None:
                continue
            flags = set(member.database.list_flags(character.id))
            if GRAVEWATCH_GATE_OPEN_FLAG in flags:
                continue
            required = {GRAVEWATCH_CAPTAIN_DEFEATED_FLAG, GRAVEWATCH_CHAPLAIN_DEFEATED_FLAG}
            if not required.issubset(flags):
                continue
            member.database.grant_flag(character.id, GRAVEWATCH_GATE_OPEN_FLAG)
            q = _quest(member)
            if q and q.get("status") == "active" and q.get("current_step") == "open_inner_gate":
                member.database.advance_quest(character.id, GRAVEWATCH_QUEST_KEY, "defeat_castellan")
            await member.send("[Party Progress] The group raises Gravewatch's inner portcullis; your run advances with it.\r\n")

    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.playing_prompt = playing_prompt
    player_session_class._gravewatch_party_runtime_installed = True
