from __future__ import annotations

import asyncio
from dataclasses import dataclass

from mud.character_options import RACES_BY_KEY
from mud.movement_system import is_restful_place


@dataclass(frozen=True, slots=True)
class HealthRegenerationRules:
    recovery_interval_seconds: float = 6.0
    passive_recovery: int = 1
    resting_recovery: int = 2
    restful_place_bonus: int = 1


HEALTH_REGEN_RULES = HealthRegenerationRules()


def _in_combat(session) -> bool:
    return (
        getattr(session, "active_enemy", None) is not None
        or getattr(session, "active_mobile_npc_key", None) is not None
    )


def base_health_recovery_amount(session, world_service) -> int:
    """Return ordinary out-of-combat recovery before racial regeneration."""

    if _in_combat(session):
        return 0

    resting = bool(getattr(session, "_movement_resting", False))
    amount = (
        HEALTH_REGEN_RULES.resting_recovery
        if resting
        else HEALTH_REGEN_RULES.passive_recovery
    )
    character = getattr(session, "character", None)
    if (
        resting
        and character is not None
        and is_restful_place(world_service, character.current_room or "")
    ):
        amount += HEALTH_REGEN_RULES.restful_place_bonus

    try:
        amount += max(0, int(getattr(session, "health_recovery_bonus", 0)))
    except (TypeError, ValueError):
        pass
    return amount


def racial_health_recovery_bonus(session) -> int:
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    race_key = (
        getattr(combatant, "race_key", "")
        if combatant is not None
        else getattr(character, "race", "")
        if character is not None
        else ""
    )
    race = RACES_BY_KEY.get(race_key or "")
    return max(0, int(race.regen_bonus_per_tick)) if race is not None else 0


def health_recovery_amount(session, world_service) -> int:
    base = base_health_recovery_amount(session, world_service)
    if base <= 0:
        return 0
    return base + racial_health_recovery_bonus(session)


def restore_health(session, amount: int) -> int:
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return 0
    before = max(0, int(getattr(combatant, "current_hp", 0)))
    maximum = max(1, int(getattr(combatant, "max_hp", 1)))
    combatant.current_hp = min(maximum, before + max(0, int(amount)))
    return int(combatant.current_hp) - before


def recover_health_once(session, world_service) -> int:
    combatant = getattr(session, "combatant", None)
    character = getattr(session, "character", None)
    if combatant is None or character is None:
        return 0
    if int(combatant.current_hp) >= int(combatant.max_hp):
        return 0

    base = base_health_recovery_amount(session, world_service)
    if base <= 0:
        return 0

    # Use the canonical CombatantState hook when available so Troll (+1/tick)
    # and Sporekin (+2/tick) racial identity remains centralized in mechanics.
    apply_regeneration = getattr(combatant, "apply_normal_regeneration", None)
    if callable(apply_regeneration):
        return int(apply_regeneration(base))

    # Small test/tools sessions may use a lightweight combatant object.
    return restore_health(session, base + racial_health_recovery_bonus(session))


async def _health_recovery_loop(session, world_service) -> None:
    try:
        while True:
            await asyncio.sleep(HEALTH_REGEN_RULES.recovery_interval_seconds)
            recovered = recover_health_once(session, world_service)
            if recovered <= 0:
                continue
            try:
                await session.send_client_state()
            except (ConnectionError, asyncio.CancelledError):
                raise
            except Exception:
                # HUD presentation must never kill character recovery.
                pass
    except asyncio.CancelledError:
        return


def _ensure_health_recovery_task(session, world_service) -> None:
    task = getattr(session, "_health_recovery_task", None)
    if task is not None and not task.done():
        return
    try:
        session._health_recovery_task = asyncio.create_task(
            _health_recovery_loop(session, world_service)
        )
    except RuntimeError:
        # Unit/tool construction may occur outside a running event loop. The
        # first real character entry or PLAYING prompt will try again.
        session._health_recovery_task = None


def install_health_regeneration_runtime(player_session_class, world_service) -> None:
    """Install passive out-of-combat HP recovery.

    Normal characters recover 1 HP every six seconds out of combat. REST raises
    that to 2, and resting in a restful room raises it to 3. Troll and Sporekin
    racial regeneration is added on every successful normal regeneration tick.
    """

    if getattr(player_session_class, "_health_regeneration_runtime_installed", False):
        return

    original_enter_character = player_session_class.enter_character
    original_playing_prompt = player_session_class.playing_prompt
    original_close = player_session_class.close

    async def enter_character(self) -> None:
        await original_enter_character(self)
        if getattr(self, "character", None) is None or getattr(self, "combatant", None) is None:
            return
        _ensure_health_recovery_task(self, world_service)
        await self.send_client_state()

    async def playing_prompt(self) -> None:
        _ensure_health_recovery_task(self, world_service)
        await original_playing_prompt(self)

    async def close(self) -> None:
        task = getattr(self, "_health_recovery_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await original_close(self)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class.close = close
    player_session_class._health_regeneration_runtime_installed = True
