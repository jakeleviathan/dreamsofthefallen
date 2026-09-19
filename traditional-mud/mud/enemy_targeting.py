from __future__ import annotations

import asyncio

from mud.mechanics import class_abilities_for_level
from mud.partial_target_matching import resolve_target_command


_ENEMY_TARGET_CATEGORY_MARKERS = (
    "attack",
    "control",
    "curse",
    "damage",
    "drain",
    "retribution",
    "threat",
)


def _resolve_ability(session, ability_text: str):
    character = getattr(session, "character", None)
    if character is None:
        return None
    normalized = ability_text.strip().lower().replace("_", " ")
    abilities = class_abilities_for_level(
        character.character_class or "",
        character.level,
        character.deity_key,
    )
    return next(
        (
            ability
            for ability in abilities
            if normalized in {ability.key.replace("_", " "), ability.name.lower()}
        ),
        None,
    )


def _enemy_targeted_ability(ability) -> bool:
    if ability is None:
        return False
    category = str(getattr(ability, "category", "") or "").lower()
    return any(marker in category for marker in _ENEMY_TARGET_CATEGORY_MARKERS)


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


async def _clear_selection(session, *, announce: bool = False) -> None:
    had_target = getattr(session, "selected_enemy", None) is not None
    session.selected_enemy = None
    session.selected_mobile_npc_key = None
    session.selected_enemy_room_key = None
    if announce and had_target:
        await session.send("Target cleared.\r\n")
    send_state = getattr(session, "send_client_state", None)
    if send_state is not None:
        await send_state()


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
            await session.send(f"{active.definition.name} is already your combat target.\r\n")
            await session.send_client_state()
            return True
        await session.send(
            f"You are already fighting {active.definition.name}. FLEE before changing enemy targets.\r\n"
        )
        return True

    enemy = session._enemy_in_current_room(target_text)
    mobile_key = None
    if enemy is None:
        mobile_state = session._mobile_npc_in_current_room(target_text)
        if mobile_state is not None and bool(getattr(mobile_state.definition, "aggressive", False)):
            enemy = session._enemy_from_mobile_npc(mobile_state)
            # Preserve current mobile HP if the mobile runtime exposes it.
            current_hp = getattr(mobile_state, "current_hp", None)
            if current_hp is not None:
                enemy.current_hp = max(0, min(enemy.definition.max_hp, int(current_hp)))
            mobile_key = mobile_state.definition.key

    if enemy is None:
        await session.send("You do not see an attackable target by that name here.\r\n")
        return True

    session.selected_enemy = enemy
    session.selected_mobile_npc_key = mobile_key
    session.selected_enemy_room_key = character.current_room
    await session.send(
        f"You target {enemy.definition.name} ({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
    )
    await session.send_client_state()
    return True


async def _engage_selected_enemy(session, *, announce: bool = True) -> bool:
    if getattr(session, "active_enemy", None) is not None:
        return True

    enemy = _selected_enemy(session)
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if enemy is None or character is None or combatant is None:
        await _clear_selection(session)
        return False

    mobile_key = getattr(session, "selected_mobile_npc_key", None)
    if mobile_key:
        mobile_npcs = getattr(session, "mobile_npcs", None)
        if mobile_npcs is None or not mobile_npcs.engage(mobile_key, character.id):
            await session.send(f"{enemy.definition.name} is no longer available to engage.\r\n")
            await _clear_selection(session)
            return False

    session.active_enemy = enemy
    session.active_mobile_npc_key = mobile_key
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
    """Add non-aggro enemy selection that feeds combat abilities and the HUD.

    TARGET chooses an enemy without beginning combat. Enemy-targeted abilities
    promote that selection into the active encounter immediately before the
    ability resolves, so hotbar CAST/USE commands can work naturally without an
    ATTACK command first.
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

        normalized = " ".join(command.strip().lower().split())

        if normalized in {"target", "tgt"}:
            enemy = getattr(self, "active_enemy", None) or _selected_enemy(self)
            if enemy is None:
                await self.send("You have no enemy targeted. Use TARGET <enemy>.\r\n")
            else:
                state = "fighting" if getattr(self, "active_enemy", None) is enemy else "selected"
                await self.send(
                    f"Target: {enemy.definition.name} "
                    f"{enemy.current_hp}/{enemy.definition.max_hp} HP ({state}).\r\n"
                )
            await self.send_client_state()
            return

        if normalized in {"clear target", "target clear", "target none", "untarget"}:
            if getattr(self, "active_enemy", None) is not None:
                await self.send("Your current combat target cannot be cleared while you are fighting. Use FLEE to disengage.\r\n")
                return
            await _clear_selection(self, announce=True)
            return

        if normalized.startswith("target "):
            resolution = resolve_target_command(self, command, world_service)
            if resolution.ambiguous:
                choices = ", ".join(resolution.ambiguous_names)
                await self.send(f"That target name matches more than one enemy: {choices}. Be more specific.\r\n")
                return
            resolved = resolution.command
            target_text = resolved.strip().split(maxsplit=1)[1] if " " in resolved.strip() else ""
            await _select_enemy(self, target_text)
            return

        if normalized in {"attack", "kill"}:
            enemy = _selected_enemy(self)
            if enemy is None:
                await self.send("Attack what? Use TARGET <enemy> or ATTACK <enemy>.\r\n")
                return
            await _engage_selected_enemy(self)
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

    async def use_ability(self, ability_text: str) -> None:
        if getattr(self, "active_enemy", None) is None:
            selected = _selected_enemy(self)
            if selected is not None:
                ability = _resolve_ability(self, ability_text)
                if _enemy_targeted_ability(ability):
                    if not await _engage_selected_enemy(self):
                        await self.send(f"{getattr(ability, 'name', ability_text)} has no valid enemy target.\r\n")
                        return
                    await previous_use_ability(self, ability_text)
                    return

                # Compatibility path for any older or specially-authored ability
                # that asks for active_enemy but lacks a target-signaling category.
                # Expose the selected enemy only for this invocation. If the
                # ability damages it, promote the target into real combat.
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
                    await _clear_selection(self)
                    return
                if int(selected.current_hp or 0) < before_hp and getattr(self, "active_enemy", None) is None:
                    await _engage_selected_enemy(self, announce=False)
                return

        await previous_use_ability(self, ability_text)

    async def move_character(self, *args, **kwargs):
        before = getattr(getattr(self, "character", None), "current_room", None)
        result = await previous_move_character(self, *args, **kwargs)
        after = getattr(getattr(self, "character", None), "current_room", None)
        if before is not None and after != before and getattr(self, "active_enemy", None) is None:
            await _clear_selection(self)
        return result

    async def _stop_combat(self, *args, **kwargs):
        result = await previous_stop_combat(self, *args, **kwargs)
        await _clear_selection(self)
        return result

    player_session_class.playing_prompt = playing_prompt
    player_session_class.use_ability = use_ability
    player_session_class.move_character = move_character
    player_session_class._stop_combat = _stop_combat
    player_session_class.select_enemy_target = _select_enemy
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
