from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field, replace

from mud.combat import EnemyState
from mud.social_experience import _ACTIVE_SESSIONS


PARTY_MAX_MEMBERS = 5
PARTY_XP_BONUS_PER_EXTRA_MEMBER = 0.20
PARTY_LOOT_MODES = {"roundrobin", "killer"}


@dataclass(slots=True)
class PartyState:
    leader_id: int
    member_ids: list[int]
    follow_ids: set[int] = field(default_factory=set)
    loot_mode: str = "roundrobin"
    loot_cursor: int = 0


@dataclass(slots=True)
class PartyEncounter:
    enemy: EnemyState
    party: PartyState
    participant_ids: set[int] = field(default_factory=set)
    next_enemy_attack_at: float = 0.0
    resolved: bool = False


_PARTY_BY_MEMBER: dict[int, PartyState] = {}
_PENDING_INVITES: dict[int, int] = {}
_PARTY_ENCOUNTERS: dict[int, PartyEncounter] = {}


def reset_party_runtime_state() -> None:
    """Clear transient party state for tests and development reloads."""
    _PARTY_BY_MEMBER.clear()
    _PENDING_INVITES.clear()
    _PARTY_ENCOUNTERS.clear()


def _character(session):
    return getattr(session, "character", None)


def _session_for_character_id(character_id: int):
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and int(character.id) == int(character_id):
            return session
    return None


def _session_for_name(name: str):
    needle = name.strip().lower()
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and str(character.name).lower() == needle:
            return session
    return None


def _party_for_session(session) -> PartyState | None:
    character = _character(session)
    if character is None:
        return None
    return _PARTY_BY_MEMBER.get(int(character.id))


def _member_sessions(party: PartyState) -> list:
    result = []
    for character_id in party.member_ids:
        session = _session_for_character_id(character_id)
        if session is not None and _character(session) is not None:
            result.append(session)
    return result


def _party_sessions_here(session) -> list:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        return [session] if character is not None else []
    room = character.current_room
    return [
        other
        for other in _member_sessions(party)
        if _character(other).current_room == room
    ]


def _encounter_for(enemy: EnemyState) -> PartyEncounter | None:
    return _PARTY_ENCOUNTERS.get(id(enemy))


def _ensure_encounter(session, enemy: EnemyState) -> PartyEncounter | None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        return None
    encounter = _PARTY_ENCOUNTERS.get(id(enemy))
    if encounter is None:
        loop = asyncio.get_running_loop()
        encounter = PartyEncounter(
            enemy=enemy,
            party=party,
            participant_ids=set(),
            next_enemy_attack_at=loop.time() + enemy.definition.auto_attack_interval,
        )
        _PARTY_ENCOUNTERS[id(enemy)] = encounter
    encounter.participant_ids.add(int(character.id))
    return encounter


def _encounter_sessions(session, enemy: EnemyState) -> list:
    character = _character(session)
    encounter = _encounter_for(enemy)
    if character is None or encounter is None:
        return [session] if character is not None else []
    room = character.current_room
    result = []
    for character_id in encounter.party.member_ids:
        if character_id not in encounter.participant_ids:
            continue
        other = _session_for_character_id(character_id)
        other_character = _character(other) if other is not None else None
        if other_character is None or other_character.current_room != room:
            continue
        result.append(other)
    return result


def _party_xp_share(base_xp: int, member_count: int) -> int:
    if base_xp <= 0:
        return 0
    if member_count <= 1:
        return base_xp
    pool = round(base_xp * (1.0 + PARTY_XP_BONUS_PER_EXTRA_MEMBER * (member_count - 1)))
    return max(1, pool // member_count)


async def _send_party(party: PartyState, text: str, *, exclude=None) -> None:
    for member in _member_sessions(party):
        if member is exclude:
            continue
        try:
            await member.send(text)
        except (ConnectionError, RuntimeError):
            continue


async def _show_party(session) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None:
        return
    await session.send("\r\n--- Adventuring Party ---\r\n")
    if party is None:
        await session.send(
            "You are not in a party. PARTY INVITE <name> starts one. Parties support up to five characters.\r\n"
            "Commands: PARTY INVITE, PARTY ACCEPT, PARTY DECLINE, PARTY LEAVE, PARTY KICK, PARTY LEADER, PARTY FOLLOW ON|OFF, PARTY LOOT ROUNDROBIN|KILLER, PARTY SAY <message>, ASSIST [name].\r\n"
        )
        return

    leader_session = _session_for_character_id(party.leader_id)
    leader_character = _character(leader_session) if leader_session is not None else None
    leader_name = leader_character.name if leader_character is not None else "offline leader"
    await session.send(
        f"Leader: {leader_name} | Loot: {party.loot_mode.upper()} | Members: {len(party.member_ids)}/{PARTY_MAX_MEMBERS}\r\n"
    )
    for member_id in party.member_ids:
        member = _session_for_character_id(member_id)
        member_character = _character(member) if member is not None else None
        if member_character is None:
            await session.send(f"- Character #{member_id}: offline\r\n")
            continue
        room_status = "here" if member_character.current_room == character.current_room else "away"
        follow = "leader" if member_id == party.leader_id else ("follow" if member_id in party.follow_ids else "manual")
        combatant = getattr(member, "combatant", None)
        hp = f" HP {combatant.current_hp}/{combatant.max_hp}" if combatant is not None else ""
        role = " (leader)" if member_id == party.leader_id else ""
        await session.send(
            f"- {member_character.name}{role}: level {member_character.level}, {room_status}, {follow}{hp}\r\n"
        )


async def _invite(session, target_name: str) -> None:
    character = _character(session)
    if character is None:
        return
    target = _session_for_name(target_name)
    target_character = _character(target) if target is not None else None
    if target_character is None:
        await session.send("That character is not online.\r\n")
        return
    if target_character.id == character.id:
        await session.send("You are already traveling with yourself.\r\n")
        return
    if _party_for_session(target) is not None:
        await session.send(f"{target_character.name} is already in a party.\r\n")
        return
    party = _party_for_session(session)
    if party is not None:
        if party.leader_id != character.id:
            await session.send("Only the party leader can invite new members.\r\n")
            return
        if len(party.member_ids) >= PARTY_MAX_MEMBERS:
            await session.send("Your party is full.\r\n")
            return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("Finish your current fight before changing the party roster.\r\n")
        return
    _PENDING_INVITES[int(target_character.id)] = int(character.id)
    await session.send(f"Party invitation sent to {target_character.name}.\r\n")
    await target.send(
        f"{character.name} invites you to an adventuring party. Type PARTY ACCEPT {character.name} or PARTY DECLINE {character.name}.\r\n"
    )


async def _accept(session, inviter_name: str = "") -> None:
    character = _character(session)
    if character is None:
        return
    if _party_for_session(session) is not None:
        await session.send("You are already in a party.\r\n")
        return
    inviter_id = _PENDING_INVITES.get(int(character.id))
    if inviter_id is None:
        await session.send("You do not have a pending party invitation.\r\n")
        return
    inviter = _session_for_character_id(inviter_id)
    inviter_character = _character(inviter) if inviter is not None else None
    if inviter_character is None:
        _PENDING_INVITES.pop(int(character.id), None)
        await session.send("That party invitation is no longer available.\r\n")
        return
    if inviter_name and inviter_character.name.lower() != inviter_name.strip().lower():
        await session.send(f"Your pending invitation is from {inviter_character.name}, not {inviter_name}.\r\n")
        return

    party = _party_for_session(inviter)
    if party is None:
        party = PartyState(
            leader_id=int(inviter_character.id),
            member_ids=[int(inviter_character.id), int(character.id)],
            follow_ids={int(character.id)},
        )
        _PARTY_BY_MEMBER[int(inviter_character.id)] = party
    else:
        if party.leader_id != inviter_character.id:
            _PENDING_INVITES.pop(int(character.id), None)
            await session.send("The inviting character is no longer the party leader. Ask the new leader for an invitation.\r\n")
            return
        if len(party.member_ids) >= PARTY_MAX_MEMBERS:
            _PENDING_INVITES.pop(int(character.id), None)
            await session.send("That party filled before you could accept.\r\n")
            return
        party.member_ids.append(int(character.id))
        party.follow_ids.add(int(character.id))

    _PARTY_BY_MEMBER[int(character.id)] = party
    _PENDING_INVITES.pop(int(character.id), None)
    await _send_party(party, f"[Party] {character.name} joins the party. Follow is ON by default.\r\n")


async def _decline(session, inviter_name: str = "") -> None:
    character = _character(session)
    if character is None:
        return
    inviter_id = _PENDING_INVITES.get(int(character.id))
    if inviter_id is None:
        await session.send("You do not have a pending party invitation.\r\n")
        return
    inviter = _session_for_character_id(inviter_id)
    inviter_character = _character(inviter) if inviter is not None else None
    if inviter_name and inviter_character is not None and inviter_character.name.lower() != inviter_name.strip().lower():
        await session.send(f"Your pending invitation is from {inviter_character.name}, not {inviter_name}.\r\n")
        return
    _PENDING_INVITES.pop(int(character.id), None)
    await session.send("Party invitation declined.\r\n")
    if inviter is not None and inviter_character is not None:
        await inviter.send(f"{character.name} declines your party invitation.\r\n")


def _remove_from_encounters(character_id: int) -> None:
    for encounter in tuple(_PARTY_ENCOUNTERS.values()):
        encounter.participant_ids.discard(character_id)
        encounter.enemy.hate.threat.pop(character_id, None)


async def _remove_member(session, target_id: int, *, reason: str, announce: bool = True) -> None:
    party = _PARTY_BY_MEMBER.get(target_id)
    if party is None:
        return
    target_session = _session_for_character_id(target_id)
    target_character = _character(target_session) if target_session is not None else None
    target_name = target_character.name if target_character is not None else f"Character #{target_id}"
    if target_id in party.member_ids:
        party.member_ids.remove(target_id)
    party.follow_ids.discard(target_id)
    _PARTY_BY_MEMBER.pop(target_id, None)
    _remove_from_encounters(target_id)

    if len(party.member_ids) <= 1:
        for last_id in tuple(party.member_ids):
            _PARTY_BY_MEMBER.pop(last_id, None)
            last = _session_for_character_id(last_id)
            if announce and last is not None:
                await last.send(f"[Party] {target_name} {reason}. The party disbands because only one member remains.\r\n")
        party.member_ids.clear()
        party.follow_ids.clear()
        return

    if party.leader_id == target_id:
        party.leader_id = party.member_ids[0]
        party.follow_ids.discard(party.leader_id)
        new_leader = _session_for_character_id(party.leader_id)
        new_character = _character(new_leader) if new_leader is not None else None
        if announce:
            await _send_party(
                party,
                f"[Party] {target_name} {reason}. {new_character.name if new_character else 'The next member'} is now party leader.\r\n",
            )
    elif announce:
        await _send_party(party, f"[Party] {target_name} {reason}.\r\n")


async def _leave(session) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None:
        return
    if party is None:
        await session.send("You are not in a party.\r\n")
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("Finish or flee your current fight before leaving the party.\r\n")
        return
    await _remove_member(session, int(character.id), reason="leaves the party")
    await session.send("You leave the party.\r\n")


async def _kick(session, target_name: str) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        await session.send("You are not leading a party.\r\n")
        return
    if party.leader_id != character.id:
        await session.send("Only the party leader can remove members.\r\n")
        return
    target = _session_for_name(target_name)
    target_character = _character(target) if target is not None else None
    if target_character is None or target_character.id not in party.member_ids:
        await session.send("That character is not an online member of your party.\r\n")
        return
    if target_character.id == character.id:
        await session.send("Use PARTY LEAVE if you want to leave your own party.\r\n")
        return
    if getattr(target, "active_enemy", None) is not None or getattr(session, "active_enemy", None) is not None:
        await session.send("Do not change the party roster during an active fight.\r\n")
        return
    await _remove_member(session, int(target_character.id), reason="is removed from the party")
    await target.send("You have been removed from the party.\r\n")


async def _transfer_leader(session, target_name: str) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None or party.leader_id != character.id:
        await session.send("Only the current party leader can transfer leadership.\r\n")
        return
    target = _session_for_name(target_name)
    target_character = _character(target) if target is not None else None
    if target_character is None or target_character.id not in party.member_ids:
        await session.send("That character is not an online member of your party.\r\n")
        return
    if target_character.id == character.id:
        await session.send("You are already the party leader.\r\n")
        return
    party.leader_id = int(target_character.id)
    party.follow_ids.discard(int(target_character.id))
    party.follow_ids.add(int(character.id))
    await _send_party(party, f"[Party] {target_character.name} is now party leader.\r\n")


async def _set_follow(session, enabled: bool) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        await session.send("You are not in a party.\r\n")
        return
    if character.id == party.leader_id:
        await session.send("The party leader sets the route; there is nobody for you to auto-follow.\r\n")
        return
    if enabled:
        party.follow_ids.add(int(character.id))
    else:
        party.follow_ids.discard(int(character.id))
    await session.send(f"Party follow is now {'ON' if enabled else 'OFF'}.\r\n")


async def _set_loot(session, mode: str) -> None:
    character = _character(session)
    party = _party_for_session(session)
    normalized = mode.strip().lower().replace("_", "")
    aliases = {"roundrobin": "roundrobin", "round robin": "roundrobin", "killer": "killer"}
    selected = aliases.get(normalized, aliases.get(mode.strip().lower()))
    if character is None or party is None or party.leader_id != character.id:
        await session.send("Only the party leader can change loot rules.\r\n")
        return
    if selected not in PARTY_LOOT_MODES:
        await session.send("Party loot modes: ROUNDROBIN or KILLER. Quest rewards always remain personal.\r\n")
        return
    party.loot_mode = selected
    party.loot_cursor = 0
    await _send_party(party, f"[Party] Loot mode is now {selected.upper()}. Monster drops follow this rule; quest rewards remain personal.\r\n")


async def _party_chat(session, message: str) -> None:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        await session.send("You are not in a party.\r\n")
        return
    cleaned = " ".join(message.replace("\r", " ").replace("\n", " ").split())[:500]
    if not cleaned:
        await session.send("PARTY SAY what?\r\n")
        return
    await _send_party(party, f"[Party] {character.name}: {cleaned}\r\n")


async def _assist(session, target_name: str = "") -> bool:
    character = _character(session)
    party = _party_for_session(session)
    if character is None or party is None:
        await session.send("You need to be in a party to use ASSIST.\r\n")
        return True
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You are already fighting.\r\n")
        return True

    candidates = []
    for other in _member_sessions(party):
        if other is session:
            continue
        other_character = _character(other)
        enemy = getattr(other, "active_enemy", None)
        if other_character is None or other_character.current_room != character.current_room or enemy is None or not enemy.alive:
            continue
        if target_name and other_character.name.lower() != target_name.strip().lower():
            continue
        candidates.append(other)
    if not candidates:
        await session.send("No party member here is fighting a target you can assist.\r\n")
        return True
    target = candidates[0]
    target_character = _character(target)
    enemy = target.active_enemy
    if getattr(target, "active_mobile_npc_key", None) is not None:
        await session.send("ASSIST currently joins shared room-enemy encounters; roaming NPC fights still resolve one character at a time.\r\n")
        return True

    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    if getattr(session, "combatant", None) is None:
        await session.send("Your combat state is not ready.\r\n")
        session.active_enemy = None
        return True
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(int(character.id), 1.0)
    encounter = _ensure_encounter(target, enemy)
    if encounter is not None:
        encounter.participant_ids.add(int(character.id))
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    await _send_party(
        party,
        f"[Party] {character.name} assists {target_character.name} against {enemy.definition.name}.\r\n",
    )
    await session.send_client_state()
    return True


def _active_encounter_target(encounter: PartyEncounter):
    candidates = []
    for character_id in encounter.participant_ids:
        session = _session_for_character_id(character_id)
        character = _character(session) if session is not None else None
        if character is None or getattr(session, "active_enemy", None) is not encounter.enemy:
            continue
        combatant = getattr(session, "combatant", None)
        if combatant is None or combatant.current_hp <= 0:
            continue
        candidates.append((float(encounter.enemy.hate.threat.get(character_id, 0.0)), character_id, session))
    if not candidates:
        return None
    candidates.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    return candidates[0][2]


async def _party_combat_loop(session, enemy: EnemyState) -> None:
    character = _character(session)
    combatant = getattr(session, "combatant", None)
    if character is None or combatant is None:
        return
    encounter = _ensure_encounter(session, enemy)
    if encounter is None:
        return
    loop = asyncio.get_running_loop()
    try:
        while getattr(session, "active_enemy", None) is enemy and enemy.alive and not encounter.resolved:
            now = loop.time()
            if combatant.auto_attack_ready(now):
                combatant.consume_auto_attack(now)
                attack_roll = random.randint(1, 20)
                if attack_roll >= enemy.definition.armor_class:
                    damage = combatant.auto_attack_damage(2)
                    dealt = enemy.take_damage(damage)
                    enemy.hate.add_threat(int(character.id), max(1.0, float(dealt)))
                    await session.send(
                        f"\r\nYou strike {enemy.definition.name} for {dealt} damage ({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
                    )
                    await _send_party(
                        encounter.party,
                        f"[Party Combat] {character.name} hits {enemy.definition.name} for {dealt} ({enemy.current_hp}/{enemy.definition.max_hp}).\r\n",
                        exclude=session,
                    )
                    await session.send_client_state()
                    if not enemy.alive:
                        await session._finish_enemy_defeat(enemy)
                        return
                else:
                    await session.send(f"\r\nYour attack misses {enemy.definition.name}.\r\n")

            if enemy.definition.retaliates and enemy.alive and now >= encounter.next_enemy_attack_at:
                target = _active_encounter_target(encounter)
                encounter.next_enemy_attack_at = now + enemy.definition.auto_attack_interval
                if target is not None and target.combatant is not None and target.character is not None:
                    damage = enemy.definition.auto_attack_damage
                    if now < getattr(target, "ward_until", 0.0):
                        damage = max(1, damage // 2)
                    target.combatant.current_hp = max(0, target.combatant.current_hp - damage)
                    await target.send(
                        f"\r\n{enemy.definition.name} hits you for {damage} damage ({target.combatant.current_hp}/{target.combatant.max_hp} HP).\r\n"
                    )
                    await _send_party(
                        encounter.party,
                        f"[Party Combat] {enemy.definition.name} hits {target.character.name} for {damage} ({target.combatant.current_hp}/{target.combatant.max_hp}).\r\n",
                        exclude=target,
                    )
                    await target.send_client_state()
                    if target.combatant.current_hp <= 0:
                        if enemy.definition.tutorial:
                            # Party combat is not intended for tutorial targets; fall back to the ordinary recovery behavior.
                            await target._stop_combat()
                        else:
                            fallen_id = int(target.character.id)
                            encounter.participant_ids.discard(fallen_id)
                            enemy.hate.threat.pop(fallen_id, None)
                            await target._handle_character_death(enemy.definition.name)
                            await _send_party(encounter.party, f"[Party] {target.character.name if target.character else 'A party member'} falls and returns to their bind point.\r\n", exclude=target)
            await asyncio.sleep(0.15)
    except asyncio.CancelledError:
        return


def _loot_recipient(session, enemy: EnemyState, _item_key: str):
    character = _character(session)
    if character is None:
        return session
    party = _party_for_session(session)
    encounter = _encounter_for(enemy)
    if party is None or encounter is None or encounter.party is not party:
        return session
    if party.loot_mode == "killer":
        return session
    eligible = _encounter_sessions(session, enemy)
    if not eligible:
        return session
    eligible_by_id = {int(_character(member).id): member for member in eligible if _character(member) is not None}
    ordered = [eligible_by_id[mid] for mid in party.member_ids if mid in eligible_by_id]
    if not ordered:
        return session
    recipient = ordered[party.loot_cursor % len(ordered)]
    party.loot_cursor = (party.loot_cursor + 1) % max(1, len(ordered))
    return recipient


async def _shared_enemy_finish(session, enemy: EnemyState, previous_finish) -> None:
    encounter = _encounter_for(enemy)
    if encounter is None or encounter.resolved:
        await previous_finish(session, enemy)
        return
    participants = _encounter_sessions(session, enemy)
    if len(participants) <= 1:
        await previous_finish(session, enemy)
        _PARTY_ENCOUNTERS.pop(id(enemy), None)
        return

    encounter.resolved = True
    base_xp = int(enemy.definition.xp_reward)
    original_definition = enemy.definition
    enemy.definition = replace(original_definition, xp_reward=0)
    try:
        await previous_finish(session, enemy)
    finally:
        enemy.definition = original_definition

    share = _party_xp_share(base_xp, len(participants))
    if share > 0:
        for member in participants:
            member_character = _character(member)
            if member_character is None:
                continue
            previous_level = int(member_character.level)
            new_level = member.database.add_experience(member_character.id, share)
            refreshed = member.database.get_character_by_name(member_character.name)
            if refreshed is not None:
                member.character = refreshed
            await member.send(
                f"[Party XP] {original_definition.name}: {share} experience shared among {len(participants)} participants.\r\n"
            )
            if new_level > previous_level:
                await member.send(f"*** You have reached level {new_level}! ***\r\n")

    await _send_party(
        encounter.party,
        f"[Party] {original_definition.name} is defeated by the group.\r\n",
    )
    for member in participants:
        if member is session:
            continue
        if getattr(member, "active_enemy", None) is enemy:
            await member._stop_combat()
            await member.send_client_state()
    _PARTY_ENCOUNTERS.pop(id(enemy), None)


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


def install_party_runtime(player_session_class) -> None:
    """Install transient adventuring parties, shared combat, XP, follow, and loot rules."""
    if getattr(player_session_class, "_party_runtime_installed", False):
        return

    # These hooks are deliberately small and synchronous so authored dungeons and
    # loot systems can ask who participated without depending on this module.
    player_session_class.party_sessions_here = _party_sessions_here
    player_session_class.party_victory_sessions = _encounter_sessions
    player_session_class._party_loot_recipient = _loot_recipient

    previous_move = player_session_class.move_character
    previous_start_combat = player_session_class.start_combat
    previous_combat_loop = player_session_class._combat_loop
    previous_finish = player_session_class._finish_enemy_defeat
    previous_close = player_session_class.close
    previous_prompt = player_session_class.playing_prompt

    async def move_character(self, direction: str) -> None:
        character = _character(self)
        party = _party_for_session(self)
        before = character.current_room if character is not None else None
        followers = []
        if character is not None and party is not None and party.leader_id == character.id:
            for other in _member_sessions(party):
                other_character = _character(other)
                if (
                    other is not self
                    and other_character is not None
                    and other_character.id in party.follow_ids
                    and other_character.current_room == before
                    and getattr(other, "active_enemy", None) is None
                ):
                    followers.append(other)
        await previous_move(self, direction)
        character = _character(self)
        after = character.current_room if character is not None else None
        if before is None or after == before:
            return
        for follower in followers:
            follower_character = _character(follower)
            if follower_character is None or follower_character.current_room != before:
                continue
            await follower.send(f"[Party] You follow {character.name} {direction}.\r\n")
            await follower.move_character(direction)

    async def start_combat(self, target_text: str) -> None:
        character = _character(self)
        party = _party_for_session(self)
        if character is not None and party is not None and getattr(self, "active_enemy", None) is None:
            for other in _member_sessions(party):
                if other is self:
                    continue
                other_character = _character(other)
                enemy = getattr(other, "active_enemy", None)
                if (
                    other_character is not None
                    and other_character.current_room == character.current_room
                    and enemy is not None
                    and enemy.alive
                    and enemy.definition.matches(target_text)
                ):
                    await _assist(self, other_character.name)
                    return
        await previous_start_combat(self, target_text)

    async def combat_loop(self, enemy: EnemyState) -> None:
        if _party_for_session(self) is None and _encounter_for(enemy) is None:
            await previous_combat_loop(self, enemy)
            return
        await _party_combat_loop(self, enemy)

    async def finish_enemy(self, enemy: EnemyState) -> None:
        if _encounter_for(enemy) is None:
            await previous_finish(self, enemy)
            return
        await _shared_enemy_finish(self, enemy, previous_finish)

    async def close(self) -> None:
        character = _character(self)
        if character is not None and _party_for_session(self) is not None:
            await _remove_member(self, int(character.id), reason="disconnects", announce=True)
        await previous_close(self)

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

        if normalized in {"party", "group", "party status", "group status"}:
            await _show_party(self)
            return
        if normalized.startswith("party invite ") or normalized.startswith("group invite "):
            await _invite(self, stripped.split(maxsplit=2)[2])
            return
        if normalized == "party accept" or normalized == "group accept":
            await _accept(self)
            return
        if normalized.startswith("party accept ") or normalized.startswith("group accept "):
            await _accept(self, stripped.split(maxsplit=2)[2])
            return
        if normalized == "party decline" or normalized == "group decline":
            await _decline(self)
            return
        if normalized.startswith("party decline ") or normalized.startswith("group decline "):
            await _decline(self, stripped.split(maxsplit=2)[2])
            return
        if normalized in {"party leave", "group leave"}:
            await _leave(self)
            return
        if normalized.startswith("party kick ") or normalized.startswith("group kick "):
            await _kick(self, stripped.split(maxsplit=2)[2])
            return
        if normalized.startswith("party leader ") or normalized.startswith("group leader "):
            await _transfer_leader(self, stripped.split(maxsplit=2)[2])
            return
        if normalized in {"party follow on", "group follow on", "follow party on"}:
            await _set_follow(self, True)
            return
        if normalized in {"party follow off", "group follow off", "follow party off"}:
            await _set_follow(self, False)
            return
        if normalized.startswith("party loot ") or normalized.startswith("group loot "):
            await _set_loot(self, stripped.split(maxsplit=2)[2])
            return
        if normalized.startswith("party say ") or normalized.startswith("group say "):
            await _party_chat(self, stripped.split(maxsplit=2)[2])
            return
        if normalized == "assist":
            await _assist(self)
            return
        if normalized.startswith("assist "):
            await _assist(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_prompt, command)

    player_session_class.move_character = move_character
    player_session_class.start_combat = start_combat
    player_session_class._combat_loop = combat_loop
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.close = close
    player_session_class.playing_prompt = playing_prompt
    player_session_class._party_runtime_installed = True
