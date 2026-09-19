from __future__ import annotations

import asyncio
from time import monotonic

from mud import ability_mastery, mechanics


INTERRUPT_MANA_REFUND_FRACTION = 0.80


def _resolve_ability(session, ability_text: str):
    character = getattr(session, "character", None)
    if character is None:
        return None
    normalized = " ".join(ability_text.strip().lower().replace("_", " ").split())
    matches = []
    for ability in mechanics.class_abilities_for_level(
        character.character_class or "",
        character.level,
        character.deity_key,
    ):
        aliases = {ability.key.replace("_", " ").lower(), ability.name.lower()}
        for alias in aliases:
            if normalized == alias or normalized.startswith(alias + " "):
                matches.append((len(alias), ability))
    if not matches:
        return None
    return max(matches, key=lambda row: row[0])[1]


def _cooldown_remaining(session, ability) -> float:
    now = monotonic()
    combatant = getattr(session, "combatant", None)
    if combatant is not None and not combatant.ability_ready(ability.key, now):
        return max(0.0, float(combatant.cooldowns.get(ability.key, now)) - now)
    for attribute in ("_upper_class_cooldowns", "_late_class_cooldowns"):
        table = getattr(session, attribute, None)
        if isinstance(table, dict):
            ready_at = float(table.get(ability.key, 0.0) or 0.0)
            if ready_at > now:
                return ready_at - now
    return 0.0


def spend_ability_mana(session, ability, amount: int) -> bool:
    """Spend mana, consuming a cast-time reservation when one exists.

    Cast-time abilities pay at the beginning of the cast. Their eventual runtime
    still calls its ordinary payment path, so this helper prevents a second
    charge while preserving the same activation code for instant abilities.
    """
    amount = max(0, int(amount))
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return False

    prepaid = getattr(session, "_casting_prepaid", None)
    if isinstance(prepaid, dict) and prepaid.get("ability_key") == getattr(ability, "key", None):
        paid = max(0, int(prepaid.get("mana_spent", 0) or 0))
        session._casting_prepaid = None
        if paid < amount:
            extra = amount - paid
            if not combatant.spend_mana(extra):
                combatant.current_mana = min(combatant.max_mana, combatant.current_mana + paid)
                return False
        elif paid > amount:
            combatant.current_mana = min(combatant.max_mana, combatant.current_mana + (paid - amount))
        return True

    return combatant.spend_mana(amount)


async def interrupt_cast(session, reason: str = "damage") -> bool:
    state = getattr(session, "_active_cast", None)
    if not isinstance(state, dict):
        return False

    session._active_cast = None
    task = state.get("task")
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()

    combatant = getattr(session, "combatant", None)
    mana_spent = max(0, int(state.get("mana_spent", 0) or 0))
    refund = int(round(mana_spent * INTERRUPT_MANA_REFUND_FRACTION))
    if combatant is not None and refund:
        combatant.current_mana = min(combatant.max_mana, combatant.current_mana + refund)

    ability = state.get("ability")
    name = getattr(ability, "name", "Your spell")
    if reason == "damage":
        message = f"{name} is interrupted as the hit breaks your concentration."
    elif reason == "movement":
        message = f"{name} is interrupted as you move."
    else:
        message = f"{name} is interrupted."

    if mana_spent:
        lost = mana_spent - refund
        message += f" You recover {refund} mana; {lost} mana is lost."
    await session.send(message + "\r\n")
    send_state = getattr(session, "send_client_state", None)
    if send_state is not None:
        await send_state()
    return True


async def _refund_unfinished_cast(session, state: dict, message: str) -> None:
    if getattr(session, "_active_cast", None) is state:
        session._active_cast = None
    combatant = getattr(session, "combatant", None)
    mana_spent = max(0, int(state.get("mana_spent", 0) or 0))
    refund = int(round(mana_spent * INTERRUPT_MANA_REFUND_FRACTION))
    if combatant is not None and refund:
        combatant.current_mana = min(combatant.max_mana, combatant.current_mana + refund)
    if mana_spent:
        message += f" You recover {refund} of the {mana_spent} mana committed to the cast."
    await session.send(message + "\r\n")
    send_state = getattr(session, "send_client_state", None)
    if send_state is not None:
        await send_state()


def install_casting_runtime(player_session_class) -> None:
    """Add interruptible cast times without blocking the real-time combat loop."""
    if getattr(player_session_class, "_casting_runtime_installed", False):
        return

    previous_use_ability = player_session_class.use_ability
    previous_close = player_session_class.close
    previous_move = player_session_class.move_character

    async def use_ability(self, ability_text: str) -> None:
        ability = _resolve_ability(self, ability_text)
        cast_time = float(getattr(ability, "cast_time_seconds", 0.0) or 0.0) if ability is not None else 0.0
        if ability is None or cast_time <= 0.0:
            await previous_use_ability(self, ability_text)
            return

        active = getattr(self, "_active_cast", None)
        if isinstance(active, dict):
            active_ability = active.get("ability")
            await self.send(
                f"You are already casting {getattr(active_ability, 'name', 'another ability')}.\r\n"
            )
            return

        combatant = getattr(self, "combatant", None)
        character = getattr(self, "character", None)
        if combatant is None or character is None or combatant.current_hp <= 0:
            await self.send("You cannot begin that cast right now.\r\n")
            return

        cooldown = _cooldown_remaining(self, ability)
        if cooldown > 0.0:
            await self.send(f"{ability.name} is still on cooldown for {cooldown:.1f}s.\r\n")
            return

        mana_cost = ability_mastery.effective_mana_cost(self, ability)
        if not combatant.spend_mana(mana_cost):
            await self.send(f"You need {mana_cost} mana for {ability.name}.\r\n")
            return

        state = {
            "ability": ability,
            "ability_text": ability_text,
            "mana_spent": mana_cost,
            "character_id": character.id,
            "room_key": character.current_room,
            "task": None,
        }
        self._active_cast = state
        await self.send(f"You begin casting {ability.name} ({cast_time:g}s).\r\n")
        send_state = getattr(self, "send_client_state", None)
        if send_state is not None:
            await send_state()

        async def finish_cast() -> None:
            try:
                await asyncio.sleep(cast_time)
                if getattr(self, "_active_cast", None) is not state:
                    return

                current_character = getattr(self, "character", None)
                current_combatant = getattr(self, "combatant", None)
                if (
                    current_character is None
                    or current_character.id != state["character_id"]
                    or current_combatant is None
                    or current_combatant.current_hp <= 0
                ):
                    await _refund_unfinished_cast(self, state, f"{ability.name} unravels before it can complete.")
                    return
                if current_character.current_room != state["room_key"]:
                    await _refund_unfinished_cast(self, state, f"{ability.name} unravels because you left the casting location.")
                    return

                self._active_cast = None
                self._casting_prepaid = {
                    "ability_key": ability.key,
                    "mana_spent": mana_cost,
                }
                await self.send(f"You finish casting {ability.name}.\r\n")
                await previous_use_ability(self, ability_text)

                prepaid = getattr(self, "_casting_prepaid", None)
                if isinstance(prepaid, dict) and prepaid.get("ability_key") == ability.key:
                    self._casting_prepaid = None
                    if mana_cost:
                        current_combatant.current_mana = min(
                            current_combatant.max_mana,
                            current_combatant.current_mana + mana_cost,
                        )
                        await self.send(
                            f"{ability.name} does not take hold, and the committed mana returns to you.\r\n"
                        )
                        if send_state is not None:
                            await send_state()
            except asyncio.CancelledError:
                return
            finally:
                if getattr(self, "_active_cast", None) is state:
                    self._active_cast = None

        task = asyncio.create_task(finish_cast())
        state["task"] = task

    async def move_character(self, *args, **kwargs):
        if isinstance(getattr(self, "_active_cast", None), dict):
            await interrupt_cast(self, "movement")
        return await previous_move(self, *args, **kwargs)

    async def close(self) -> None:
        state = getattr(self, "_active_cast", None)
        if isinstance(state, dict):
            task = state.get("task")
            if task is not None and not task.done():
                task.cancel()
            self._active_cast = None
        self._casting_prepaid = None
        await previous_close(self)

    player_session_class.use_ability = use_ability
    player_session_class.move_character = move_character
    player_session_class.close = close
    player_session_class._casting_runtime_installed = True
