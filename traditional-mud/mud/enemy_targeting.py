from __future__ import annotations

import asyncio

from mud.mechanics import class_abilities_for_level
from mud.partial_target_matching import resolve_target_command
from mud.social_experience import _ACTIVE_SESSIONS


_ENEMY_TARGET_CATEGORY_MARKERS = (
    "attack",
    "control",
    "curse",
    "damage",
    "drain",
    "retribution",
    "threat",
)

_ALLY_TARGET_CATEGORIES = {
    "healing",
    "ally_buff",
    "healing_over_time",
    "ally_protection",
    "protection",
}


def _normalize(value: str) -> str:
    return " ".join((value or "").strip().casefold().split())


def _resolve_ability(session, ability_text: str):
    character = getattr(session, "character", None)
    if character is None:
        return None, ""
    normalized = _normalize(ability_text.replace("_", " "))
    matches = []
    for ability in class_abilities_for_level(
        character.character_class or "",
        character.level,
        character.deity_key,
    ):
        aliases = {
            _normalize(ability.key.replace("_", " ")),
            _normalize(ability.name),
        }
        for alias in aliases:
            if normalized == alias:
                matches.append((len(alias), ability, ""))
            elif normalized.startswith(alias + " "):
                matches.append((len(alias), ability, normalized[len(alias):].strip()))
    if not matches:
        return None, ""
    _length, ability, target_text = max(matches, key=lambda row: row[0])
    return ability, target_text


def _enemy_targeted_ability(ability) -> bool:
    if ability is None:
        return False
    category = str(getattr(ability, "category", "") or "").lower()
    return any(marker in category for marker in _ENEMY_TARGET_CATEGORY_MARKERS)


def _ally_targeted_ability(ability) -> bool:
    if ability is None:
        return False
    return str(getattr(ability, "category", "") or "").lower() in _ALLY_TARGET_CATEGORIES


def _selected_enemy(session):
    enemy = getattr(session, "selected_enemy", None)
    character = getattr(session, "character", None)
    if enemy is None or character is None:
        return None
    if not enemy.alive:
        return None
    if getattr(session, "selected_enemy_room_key", None) != character.current_room:
        return None

    mobile_key = getattr(session, "selected_mobile_npc_key", None)
    if mobile_key:
        mobile_npcs = getattr(session, "mobile_npcs", None)
        if mobile_npcs is None:
            return None
        state = mobile_npcs.states.get(mobile_key)
        if (
            state is None
            or not state.active
            or state.current_room_key != character.current_room
        ):
            return None
    return enemy


def _selected_player(session):
    character = getattr(session, "character", None)
    target_id = getattr(session, "selected_player_character_id", None)
    if character is None or target_id is None:
        return None

    if int(target_id) == int(character.id):
        return session

    for other in tuple(_ACTIVE_SESSIONS):
        other_character = getattr(other, "character", None)
        if other_character is None:
            continue
        if int(other_character.id) != int(target_id):
            continue
        if other_character.current_room != character.current_room:
            return None
        return other
    return None


def _player_candidates_here(session, target_text: str):
    character = getattr(session, "character", None)
    if character is None:
        return []

    query = _normalize(target_text)
    if query in {"self", "me", "myself"}:
        return [session]

    candidates = []
    seen_ids: set[int] = set()

    def consider(other) -> None:
        other_character = getattr(other, "character", None)
        if other_character is None:
            return
        if other_character.current_room != character.current_room:
            return
        cid = int(other_character.id)
        if cid in seen_ids:
            return
        name = _normalize(other_character.name)
        if query == name or name.startswith(query):
            seen_ids.add(cid)
            candidates.append(other)

    consider(session)
    for other in tuple(_ACTIVE_SESSIONS):
        consider(other)

    exact = [
        other for other in candidates
        if _normalize(other.character.name) == query
    ]
    return exact if exact else candidates


async def _clear_selection(session, *, announce: bool = False) -> None:
    had_target = (
        getattr(session, "selected_enemy", None) is not None
        or getattr(session, "selected_player_character_id", None) is not None
    )
    session.selected_enemy = None
    session.selected_mobile_npc_key = None
    session.selected_enemy_room_key = None
    session.selected_player_character_id = None
    session.selected_player_room_key = None
    session.selected_target_kind = None
    if announce and had_target:
        await session.send("Target cleared.\r\n")
    send_state = getattr(session, "send_client_state", None)
    if send_state is not None:
        await send_state()


async def _clear_enemy_selection(session) -> None:
    session.selected_enemy = None
    session.selected_mobile_npc_key = None
    session.selected_enemy_room_key = None
    if getattr(session, "selected_target_kind", None) == "enemy":
        if _selected_player(session) is not None:
            session.selected_target_kind = "player"
        else:
            session.selected_target_kind = None


async def _select_player(session, target_text: str):
    candidates = _player_candidates_here(session, target_text)
    if not candidates:
        return False
    if len(candidates) > 1:
        await session.send(
            "That player target is ambiguous: "
            + ", ".join(sorted(other.character.name for other in candidates))
            + ". Be more specific.\r\n"
        )
        return True

    target = candidates[0]
    target_character = target.character
    target_combatant = getattr(target, "combatant", None)
    session.selected_player_character_id = int(target_character.id)
    session.selected_player_room_key = target_character.current_room
    session.selected_target_kind = "player"

    hp = int(getattr(target_combatant, "current_hp", 0) or 0)
    max_hp = int(getattr(target_combatant, "max_hp", 0) or 0)
    relation = "yourself" if target is session else "player"
    await session.send(
        f"You target {target_character.name} ({relation}, {hp}/{max_hp} HP).\r\n"
    )
    await session.send_client_state()
    return True


async def _select_enemy(session, target_text: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False

    active = getattr(session, "active_enemy", None)
    if active is not None:
        if active.definition.matches(target_text):
            session.selected_enemy = active
            session.selected_mobile_npc_key = getattr(session, "active_mobile_npc_key", None)
            session.selected_enemy_room_key = character.current_room
            session.selected_target_kind = "enemy"
            await session.send(f"{active.definition.name} is already your combat target.\r\n")
            await session.send_client_state()
            return True
        await session.send(
            f"You are already fighting {active.definition.name}. You may target yourself or another player, "
            "but FLEE before selecting a different enemy.\r\n"
        )
        return True

    enemy = session._enemy_in_current_room(target_text)
    mobile_key = None
    if enemy is None:
        mobile_state = session._mobile_npc_in_current_room(target_text)
        if mobile_state is not None and bool(getattr(mobile_state.definition, "aggressive", False)):
            enemy = session._enemy_from_mobile_npc(mobile_state)
            current_hp = getattr(mobile_state, "current_hp", None)
            if current_hp is not None:
                enemy.current_hp = max(0, min(enemy.definition.max_hp, int(current_hp)))
            mobile_key = mobile_state.definition.key

    if enemy is None:
        return False

    session.selected_enemy = enemy
    session.selected_mobile_npc_key = mobile_key
    session.selected_enemy_room_key = character.current_room
    session.selected_target_kind = "enemy"
    await session.send(
        f"You target {enemy.definition.name} ({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
    )
    await session.send_client_state()
    return True


async def _select_target(session, target_text: str, raw_command: str, world_service) -> bool:
    # Player names and SELF/ME are resolved first so a character is a first-class
    # target rather than an afterthought to combat targeting.
    if await _select_player(session, target_text):
        return True

    resolution = resolve_target_command(session, raw_command, world_service)
    if resolution.ambiguous:
        choices = ", ".join(resolution.ambiguous_names)
        await session.send(
            f"That enemy target name matches more than one creature: {choices}. Be more specific.\r\n"
        )
        return True

    resolved = resolution.command
    enemy_text = resolved.strip().split(maxsplit=1)[1] if " " in resolved.strip() else target_text
    if await _select_enemy(session, enemy_text):
        return True

    await session.send(
        "You do not see a target by that name here. TARGET can select yourself, "
        "another player in the room, or an attackable enemy.\r\n"
    )
    return True


async def _engage_selected_enemy(session, *, announce: bool = True) -> bool:
    if getattr(session, "active_enemy", None) is not None:
        return True

    enemy = _selected_enemy(session)
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if enemy is None or character is None or combatant is None:
        return False

    mobile_key = getattr(session, "selected_mobile_npc_key", None)
    if mobile_key:
        mobile_npcs = getattr(session, "mobile_npcs", None)
        if mobile_npcs is None or not mobile_npcs.engage(mobile_key, character.id):
            await session.send(f"{enemy.definition.name} is no longer available to engage.\r\n")
            await _clear_enemy_selection(session)
            await session.send_client_state()
            return False

    session.active_enemy = enemy
    session.active_mobile_npc_key = mobile_key
    session.selected_target_kind = "enemy"
    combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(character.id, 1.0)

    if announce:
        await session.send(
            f"You engage {enemy.definition.name}. Your normal weapon attacks will now repeat automatically.\r\n"
        )
    await session.send_client_state()
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


def install_enemy_targeting_runtime(player_session_class, world_service) -> None:
    """Install unified player/enemy target selection.

    TARGET can select yourself, another player sharing the room, or an enemy.
    Player selection is passive and may be changed during combat; enemy selection
    stays tied to the single-opponent encounter model. Ally-targeted abilities
    automatically use a selected player when no explicit name is supplied.
    """

    if getattr(player_session_class, "_enemy_targeting_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_use_ability = player_session_class.use_ability
    previous_move_character = player_session_class.move_character
    previous_stop_combat = player_session_class._stop_combat

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = _normalize(command)

        if normalized in {"target", "tgt"}:
            player = _selected_player(self) if getattr(self, "selected_target_kind", None) == "player" else None
            if player is not None:
                combatant = getattr(player, "combatant", None)
                hp = int(getattr(combatant, "current_hp", 0) or 0)
                max_hp = int(getattr(combatant, "max_hp", 0) or 0)
                label = "self" if player is self else "player"
                await self.send(f"Target: {player.character.name} {hp}/{max_hp} HP ({label}).\r\n")
            else:
                enemy = getattr(self, "active_enemy", None) or _selected_enemy(self)
                if enemy is None:
                    await self.send(
                        "You have no target. Use TARGET SELF, TARGET <player>, or TARGET <enemy>.\r\n"
                    )
                else:
                    state = "fighting" if getattr(self, "active_enemy", None) is enemy else "selected enemy"
                    await self.send(
                        f"Target: {enemy.definition.name} "
                        f"{enemy.current_hp}/{enemy.definition.max_hp} HP ({state}).\r\n"
                    )
            await self.send_client_state()
            return

        if normalized in {"clear target", "target clear", "target none", "untarget"}:
            if (
                getattr(self, "active_enemy", None) is not None
                and getattr(self, "selected_target_kind", None) != "player"
            ):
                await self.send(
                    "Your combat opponent remains active until you FLEE, but you can TARGET SELF or another player at any time.\r\n"
                )
                return
            await _clear_selection(self, announce=True)
            return

        if normalized.startswith("target "):
            target_text = command.strip().split(maxsplit=1)[1].strip()
            await _select_target(self, target_text, command, world_service)
            return

        if normalized in {"attack", "kill"}:
            enemy = _selected_enemy(self)
            if enemy is None:
                if _selected_player(self) is not None:
                    await self.send(
                        "Your selected target is a player, not an attackable enemy. Use ATTACK <enemy> or TARGET <enemy>.\r\n"
                    )
                else:
                    await self.send("Attack what? Use TARGET <enemy> or ATTACK <enemy>.\r\n")
                return
            await _engage_selected_enemy(self)
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    async def use_ability(self, ability_text: str) -> None:
        ability, explicit_target = _resolve_ability(self, ability_text)

        # A selected player becomes the implicit target for heals, buffs, and
        # protections. Explicit CAST ... <name> syntax always wins.
        if (
            ability is not None
            and _ally_targeted_ability(ability)
            and not explicit_target
        ):
            player = _selected_player(self)
            if player is not None and getattr(player, "character", None) is not None:
                await previous_use_ability(
                    self,
                    f"{ability.name} {player.character.name}",
                )
                return

        if getattr(self, "active_enemy", None) is None:
            selected = _selected_enemy(self)
            if selected is not None:
                if _enemy_targeted_ability(ability):
                    if not await _engage_selected_enemy(self):
                        await self.send(
                            f"{getattr(ability, 'name', ability_text)} has no valid enemy target.\r\n"
                        )
                        return
                    await previous_use_ability(self, ability_text)
                    return

                # Compatibility path for older authored hostile abilities whose
                # category predates explicit target-mode metadata.
                before_hp = int(selected.current_hp or 0)
                previous_mobile_key = getattr(self, "active_mobile_npc_key", None)
                self.active_enemy = selected
                self.active_mobile_npc_key = getattr(self, "selected_mobile_npc_key", None)
                try:
                    await previous_use_ability(self, ability_text)
                finally:
                    if getattr(self, "active_enemy", None) is selected and selected.alive:
                        self.active_enemy = None
                        self.active_mobile_npc_key = previous_mobile_key

                if not selected.alive:
                    await _clear_enemy_selection(self)
                    await self.send_client_state()
                    return
                if int(selected.current_hp or 0) < before_hp and getattr(self, "active_enemy", None) is None:
                    await _engage_selected_enemy(self, announce=False)
                return

        await previous_use_ability(self, ability_text)

    async def move_character(self, *args, **kwargs):
        before = getattr(getattr(self, "character", None), "current_room", None)
        result = await previous_move_character(self, *args, **kwargs)
        character = getattr(self, "character", None)
        after = getattr(character, "current_room", None)
        if before is not None and after != before:
            if getattr(self, "active_enemy", None) is None:
                await _clear_enemy_selection(self)

            player = _selected_player(self)
            if player is self:
                self.selected_player_room_key = after
            elif getattr(self, "selected_player_character_id", None) is not None and player is None:
                self.selected_player_character_id = None
                self.selected_player_room_key = None
                if getattr(self, "selected_target_kind", None) == "player":
                    self.selected_target_kind = None
            await self.send_client_state()
        return result

    async def _stop_combat(self, *args, **kwargs):
        result = await previous_stop_combat(self, *args, **kwargs)
        await _clear_enemy_selection(self)
        await self.send_client_state()
        return result

    player_session_class.playing_prompt = playing_prompt
    player_session_class.use_ability = use_ability
    player_session_class.move_character = move_character
    player_session_class._stop_combat = _stop_combat
    player_session_class.select_enemy_target = _select_enemy
    player_session_class.select_target = _select_target
    player_session_class.selected_player_target = _selected_player
    player_session_class.clear_enemy_target = _clear_selection
    player_session_class.engage_selected_enemy = _engage_selected_enemy
    player_session_class._enemy_targeting_runtime_installed = True


async def _delegate_prompt(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    old_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    session.prompt = replay_prompt
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = old_prompt
        else:
            session.__dict__.pop("prompt", None)
