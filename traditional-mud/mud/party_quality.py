from __future__ import annotations

import asyncio

import mud.party_loot as party_loot
import mud.party_system as party_system


_READY_BY_PARTY: dict[int, set[int]] = {}
_FOCUS_BY_PARTY: dict[int, str] = {}
_AGGRO_BY_ENEMY: dict[int, int] = {}
_DANGER_BY_ENEMY_MEMBER: dict[tuple[int, int], str] = {}
_MONITORS: dict[int, asyncio.Task] = {}


def reset_party_quality_state() -> None:
    _READY_BY_PARTY.clear()
    _FOCUS_BY_PARTY.clear()
    _AGGRO_BY_ENEMY.clear()
    _DANGER_BY_ENEMY_MEMBER.clear()
    for task in tuple(_MONITORS.values()):
        if not task.done():
            task.cancel()
    _MONITORS.clear()


def _party_key(party) -> int:
    return id(party)


def _character(session):
    return getattr(session, "character", None)


def _name(session) -> str:
    character = _character(session)
    return character.name if character is not None else "unknown"


def _hp_percent(session) -> int | None:
    combatant = getattr(session, "combatant", None)
    if combatant is None or not getattr(combatant, "max_hp", 0):
        return None
    return max(0, min(100, round(100 * combatant.current_hp / combatant.max_hp)))


def _danger_band(session) -> str:
    percent = _hp_percent(session)
    if percent is None:
        return "unknown"
    if percent <= 25:
        return "critical"
    if percent <= 50:
        return "wounded"
    return "steady"


def _nearby_open_sessions(session) -> list:
    character = _character(session)
    if character is None:
        return []
    room = character.current_room
    result = []
    for other in tuple(party_system._ACTIVE_SESSIONS):
        if other is session:
            continue
        other_character = _character(other)
        if other_character is None or other_character.current_room != room:
            continue
        if party_system._party_for_session(other) is not None:
            continue
        result.append(other)
    result.sort(key=lambda other: _name(other).lower())
    return result


async def _show_nearby(session) -> None:
    candidates = _nearby_open_sessions(session)
    await session.send("\r\n--- Nearby Adventurers ---\r\n")
    if not candidates:
        await session.send("No ungrouped adventurers are standing here right now.\r\n")
        return
    for other in candidates:
        character = _character(other)
        await session.send(
            f"- {character.name}: level {character.level} {character.race.replace('_', ' ').title()}\r\n"
        )
    await session.send("Use PARTY INVITE <name>, or PARTY INVITE ALL to invite nearby ungrouped players up to your open slots.\r\n")


async def _invite_all_nearby(session) -> None:
    character = _character(session)
    if character is None:
        return
    party = party_system._party_for_session(session)
    if party is not None and party.leader_id != character.id:
        await session.send("Only the party leader can invite nearby adventurers.\r\n")
        return
    current_members = len(party.member_ids) if party is not None else 1
    open_slots = max(0, party_system.PARTY_MAX_MEMBERS - current_members)
    if open_slots <= 0:
        await session.send("Your party is already full.\r\n")
        return
    candidates = _nearby_open_sessions(session)[:open_slots]
    if not candidates:
        await session.send("There are no ungrouped adventurers here to invite.\r\n")
        return
    invited = []
    for other in candidates:
        await party_system._invite(session, _name(other))
        invited.append(_name(other))
    await session.send("[Party] Nearby invitations sent: " + ", ".join(invited) + ".\r\n")


async def _start_ready_check(session) -> None:
    character = _character(session)
    party = party_system._party_for_session(session)
    if character is None or party is None:
        await session.send("You need a party before starting a ready check.\r\n")
        return
    if party.leader_id != character.id:
        await session.send("Only the party leader can start a ready check.\r\n")
        return
    ready = {int(character.id)}
    _READY_BY_PARTY[_party_key(party)] = ready
    await party_system._send_party(
        party,
        f"[Ready Check] {_name(session)} is READY. Type READY when prepared or NOT READY if the group should wait.\r\n",
    )


async def _set_ready(session, ready: bool) -> None:
    character = _character(session)
    party = party_system._party_for_session(session)
    if character is None or party is None:
        await session.send("You are not in a party.\r\n")
        return
    key = _party_key(party)
    if key not in _READY_BY_PARTY:
        await session.send("There is no active ready check. The leader can use PARTY READY.\r\n")
        return
    ready_ids = _READY_BY_PARTY[key]
    if ready:
        ready_ids.add(int(character.id))
        await party_system._send_party(party, f"[Ready Check] {character.name}: READY.\r\n")
    else:
        ready_ids.discard(int(character.id))
        await party_system._send_party(party, f"[Ready Check] {character.name}: NOT READY.\r\n")

    online_ids = {
        int(_character(member).id)
        for member in party_system._member_sessions(party)
        if _character(member) is not None
    }
    offline_ids = set(party.member_ids) - online_ids
    if online_ids and online_ids.issubset(ready_ids) and not offline_ids:
        await party_system._send_party(
            party,
            f"[Ready Check] ALL READY ({len(online_ids)}/{len(party.member_ids)}). Move when the leader is ready.\r\n",
        )


async def _show_ready_status(session) -> None:
    party = party_system._party_for_session(session)
    if party is None:
        await session.send("You are not in a party.\r\n")
        return
    ready_ids = _READY_BY_PARTY.get(_party_key(party), set())
    active = _party_key(party) in _READY_BY_PARTY
    await session.send("\r\n--- Ready Check ---\r\n")
    if not active:
        await session.send("No ready check is active.\r\n")
        return
    for member_id in party.member_ids:
        member = party_system._session_for_character_id(member_id)
        if member is None or _character(member) is None:
            await session.send(f"- Character #{member_id}: OFFLINE\r\n")
            continue
        await session.send(f"- {_name(member)}: {'READY' if member_id in ready_ids else 'WAITING'}\r\n")


async def _set_focus(session, target: str) -> None:
    character = _character(session)
    party = party_system._party_for_session(session)
    if character is None or party is None:
        await session.send("You are not in a party.\r\n")
        return
    if party.leader_id != character.id:
        await session.send("Only the party leader can set the party focus target.\r\n")
        return
    cleaned = " ".join(target.strip().split())[:80]
    key = _party_key(party)
    if cleaned.lower() in {"", "clear", "none", "off"}:
        _FOCUS_BY_PARTY.pop(key, None)
        await party_system._send_party(party, "[Party Focus] Focus target cleared.\r\n")
        return
    _FOCUS_BY_PARTY[key] = cleaned
    await party_system._send_party(
        party,
        f"[Party Focus] {character.name} calls: {cleaned}. Put shared damage here first.\r\n",
    )


def _current_aggro_session(party):
    for member in party_system._member_sessions(party):
        enemy = getattr(member, "active_enemy", None)
        if enemy is None:
            continue
        encounter = party_system._encounter_for(enemy)
        if encounter is None:
            continue
        target = party_system._active_encounter_target(encounter)
        if target is not None:
            return target
    return None


async def _show_party_hud(session) -> None:
    character = _character(session)
    party = party_system._party_for_session(session)
    if character is None or party is None:
        await session.send("You are not in a party.\r\n")
        return
    leader = party_system._session_for_character_id(party.leader_id)
    leader_room = _character(leader).current_room if leader is not None and _character(leader) is not None else None
    aggro = _current_aggro_session(party)
    focus = _FOCUS_BY_PARTY.get(_party_key(party))
    ready_ids = _READY_BY_PARTY.get(_party_key(party), set())
    ready_active = _party_key(party) in _READY_BY_PARTY

    await session.send("\r\n--- Party HUD ---\r\n")
    if focus:
        await session.send(f"Focus: {focus}\r\n")
    for member_id in party.member_ids:
        member = party_system._session_for_character_id(member_id)
        member_character = _character(member) if member is not None else None
        if member_character is None:
            await session.send(f"- Character #{member_id}: OFFLINE\r\n")
            continue
        percent = _hp_percent(member)
        hp = f"{percent}% HP" if percent is not None else "HP ?"
        together = "WITH LEADER" if member_character.current_room == leader_room else "SEPARATED"
        follow = "LEADS" if member_id == party.leader_id else ("FOLLOW" if member_id in party.follow_ids else "MANUAL")
        tags = []
        if aggro is member:
            tags.append("AGGRO")
        if _danger_band(member) == "wounded":
            tags.append("WOUNDED")
        elif _danger_band(member) == "critical":
            tags.append("CRITICAL")
        if ready_active:
            tags.append("READY" if member_id in ready_ids else "WAITING")
        tag_text = f" [{' | '.join(tags)}]" if tags else ""
        await session.send(f"- {member_character.name}: {hp} | {together} | {follow}{tag_text}\r\n")


async def _show_party_help(session) -> None:
    await session.send(
        "\r\n--- Party Commands ---\r\n"
        "Forming: PARTY NEARBY, PARTY INVITE <name>, PARTY INVITE ALL, PARTY ACCEPT, PARTY DECLINE.\r\n"
        "Travel: PARTY FOLLOW ON|OFF, PARTY HUD. Followers who fail to move are called out as separated.\r\n"
        "Coordination: PARTY READY, READY, NOT READY, PARTY READY STATUS, PARTY FOCUS <target>, PARTY FOCUS CLEAR.\r\n"
        "Combat: ASSIST [name]. Shared encounters announce aggro changes, danger thresholds, victory participants, XP, and party loot distribution.\r\n"
        "Management: PARTY, PARTY SAY <message>, PARTY LOOT ROUNDROBIN|KILLER, PARTY LEADER <name>, PARTY KICK <name>, PARTY LEAVE.\r\n"
    )


async def _monitor_party_combat(seed_session, enemy) -> None:
    enemy_id = id(enemy)
    try:
        while enemy.alive:
            encounter = party_system._encounter_for(enemy)
            if encounter is None or encounter.resolved:
                return
            target = party_system._active_encounter_target(encounter)
            if target is not None and _character(target) is not None:
                target_id = int(_character(target).id)
                if _AGGRO_BY_ENEMY.get(enemy_id) != target_id:
                    _AGGRO_BY_ENEMY[enemy_id] = target_id
                    await party_system._send_party(
                        encounter.party,
                        f"[Party Combat] AGGRO -> {_name(target)}. {enemy.definition.name} is focused on them.\r\n",
                    )

            for member in party_system._encounter_sessions(seed_session, enemy):
                member_character = _character(member)
                if member_character is None:
                    continue
                key = (enemy_id, int(member_character.id))
                band = _danger_band(member)
                previous = _DANGER_BY_ENEMY_MEMBER.get(key, "steady")
                _DANGER_BY_ENEMY_MEMBER[key] = band
                if band == "wounded" and previous == "steady":
                    await party_system._send_party(
                        encounter.party,
                        f"[Party Combat] {member_character.name} is WOUNDED at {_hp_percent(member)}% HP.\r\n",
                    )
                elif band == "critical" and previous != "critical":
                    await party_system._send_party(
                        encounter.party,
                        f"[Party Combat] {member_character.name} is CRITICAL at {_hp_percent(member)}% HP.\r\n",
                    )
            await asyncio.sleep(0.20)
    except asyncio.CancelledError:
        return
    finally:
        _AGGRO_BY_ENEMY.pop(enemy_id, None)
        for key in tuple(_DANGER_BY_ENEMY_MEMBER):
            if key[0] == enemy_id:
                _DANGER_BY_ENEMY_MEMBER.pop(key, None)
        _MONITORS.pop(enemy_id, None)


def _ensure_monitor(session, enemy) -> None:
    enemy_id = id(enemy)
    task = _MONITORS.get(enemy_id)
    if task is not None and not task.done():
        return
    _MONITORS[enemy_id] = asyncio.create_task(_monitor_party_combat(session, enemy))


async def _enhanced_loot_announcement(killer, recipient, label: str, names: list[str]) -> None:
    if not names:
        return
    party = party_system._party_for_session(killer)
    if party is None:
        await _ORIGINAL_LOOT_ANNOUNCE(killer, recipient, label, names)
        return
    recipient_character = _character(recipient)
    recipient_name = recipient_character.name if recipient_character is not None else "a party member"
    text = ", ".join(names)
    await party_system._send_party(
        party,
        f"[Party Loot] {label}: {text} -> {recipient_name} ({party.loot_mode.upper()}).\r\n",
    )


_ORIGINAL_LOOT_ANNOUNCE = party_loot._announce_distribution


def install_party_quality_runtime(player_session_class) -> None:
    """Add high-signal party UI and social friction reduction on top of live parties."""
    if getattr(player_session_class, "_party_quality_runtime_installed", False):
        return

    previous_move = player_session_class.move_character
    previous_combat_loop = player_session_class._combat_loop
    previous_finish = player_session_class._finish_enemy_defeat
    previous_prompt = player_session_class.playing_prompt

    async def move_character(self, direction: str) -> None:
        character = _character(self)
        party = party_system._party_for_session(self)
        before = character.current_room if character is not None else None
        tracked = []
        if character is not None and party is not None and party.leader_id == character.id:
            for member in party_system._member_sessions(party):
                member_character = _character(member)
                if member is self or member_character is None:
                    continue
                if member_character.current_room == before and member_character.id in party.follow_ids:
                    tracked.append((member, bool(getattr(member, "active_enemy", None))))
        await previous_move(self, direction)
        character = _character(self)
        after = character.current_room if character is not None else None
        if before is None or after == before:
            return
        if party is not None:
            _READY_BY_PARTY.pop(_party_key(party), None)
        for member, was_fighting in tracked:
            member_character = _character(member)
            if member_character is None or member_character.current_room == after:
                continue
            reason = "they were in combat" if was_fighting else "a room gate or movement condition stopped them"
            await self.send(f"[Party Sync] {member_character.name} fell behind; {reason}.\r\n")
            await member.send(
                f"[Party Sync] You are SEPARATED from {_name(self)}; {reason}. Use PARTY HUD before the next pull.\r\n"
            )

    async def combat_loop(self, enemy) -> None:
        if party_system._encounter_for(enemy) is not None or party_system._party_for_session(self) is not None:
            _ensure_monitor(self, enemy)
        await previous_combat_loop(self, enemy)

    async def finish_enemy(self, enemy) -> None:
        participants = []
        finder = getattr(self, "party_victory_sessions", None)
        if callable(finder):
            participants = list(finder(enemy) or [])
        party = party_system._party_for_session(self)
        await previous_finish(self, enemy)
        if party is not None and len(participants) > 1:
            names = [
                _name(member)
                for member in participants
                if _character(member) is not None
            ]
            await party_system._send_party(
                party,
                f"[Party Victory] {enemy.definition.name}: shared combat participation recorded for {', '.join(names)}.\r\n",
            )

    async def playing_prompt(self) -> None:
        if _character(self) is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"party help", "group help"}:
            await _show_party_help(self)
            return
        if normalized in {"party nearby", "group nearby", "party form", "group form"}:
            await _show_nearby(self)
            return
        if normalized in {"party invite all", "group invite all"}:
            await _invite_all_nearby(self)
            return
        if normalized in {"party ready", "group ready", "party ready check", "group ready check"}:
            await _start_ready_check(self)
            return
        if normalized in {"ready", "party ready yes", "group ready yes"}:
            await _set_ready(self, True)
            return
        if normalized in {"not ready", "notready", "party not ready", "group not ready"}:
            await _set_ready(self, False)
            return
        if normalized in {"party ready status", "group ready status", "ready status"}:
            await _show_ready_status(self)
            return
        if normalized in {"party hud", "group hud", "party cohesion", "group cohesion"}:
            await _show_party_hud(self)
            return
        if normalized.startswith("party focus ") or normalized.startswith("group focus "):
            await _set_focus(self, stripped.split(maxsplit=2)[2])
            return
        if normalized in {"party focus", "group focus"}:
            party = party_system._party_for_session(self)
            focus = _FOCUS_BY_PARTY.get(_party_key(party)) if party is not None else None
            await self.send(f"Party focus: {focus or 'none'}.\r\n")
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

    player_session_class.move_character = move_character
    player_session_class._combat_loop = combat_loop
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.playing_prompt = playing_prompt
    player_session_class._party_quality_runtime_installed = True

    party_loot._announce_distribution = _enhanced_loot_announcement
