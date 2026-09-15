from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ManaRegenerationRules:
    recovery_interval_seconds: float = 3.0
    passive_recovery: int = 1
    resting_recovery: int = 3
    restful_place_bonus: int = 1


MANA_REGEN_RULES = ManaRegenerationRules()


def _in_combat(session) -> bool:
    return (
        getattr(session, "active_enemy", None) is not None
        or getattr(session, "active_mobile_npc_key", None) is not None
    )


def _is_restful_place(session, world_service) -> bool:
    character = getattr(session, "character", None)
    if character is None or world_service is None:
        return False
    scene = world_service.scene(character.current_room or "")
    if scene is None:
        return False
    restful_tags = {"safe", "inn", "tavern", "camp", "campfire", "hearth", "home", "sanctuary", "rest"}
    tags = {str(tag).lower().replace("_", " ") for tag in getattr(scene, "tags", ())}
    if tags.intersection(restful_tags):
        return True
    restful_words = ("bed", "bedroll", "campfire", "hearth", "bunk", "cot", "inn")
    for feature in getattr(scene, "features", ()):
        name = str(getattr(feature, "name", "")).lower()
        if any(word in name for word in restful_words):
            return True
    return False


def mana_recovery_amount(session, world_service) -> int:
    if _in_combat(session):
        return 0
    resting = bool(getattr(session, "_movement_resting", False))
    amount = MANA_REGEN_RULES.resting_recovery if resting else MANA_REGEN_RULES.passive_recovery
    if resting and _is_restful_place(session, world_service):
        amount += MANA_REGEN_RULES.restful_place_bonus
    try:
        amount += max(0, int(getattr(session, "mana_recovery_bonus", 0)))
    except (TypeError, ValueError):
        pass
    return amount


def restore_mana(session, amount: int) -> int:
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return 0
    before = max(0, int(getattr(combatant, "current_mana", 0)))
    maximum = max(0, int(getattr(combatant, "max_mana", 0)))
    combatant.current_mana = min(maximum, before + max(0, int(amount)))
    return int(combatant.current_mana) - before


def recover_mana_once(session, world_service) -> int:
    combatant = getattr(session, "combatant", None)
    character = getattr(session, "character", None)
    if combatant is None or character is None:
        return 0
    if int(combatant.current_mana) >= int(combatant.max_mana):
        return 0
    amount = mana_recovery_amount(session, world_service)
    if amount <= 0:
        return 0
    return restore_mana(session, amount)


async def _mana_recovery_loop(session, world_service) -> None:
    try:
        while True:
            await asyncio.sleep(MANA_REGEN_RULES.recovery_interval_seconds)
            recovered = recover_mana_once(session, world_service)
            if recovered <= 0:
                continue
            try:
                await session.send_client_state()
            except (ConnectionError, asyncio.CancelledError):
                raise
            except Exception:
                pass
    except asyncio.CancelledError:
        return


def _ensure_mana_recovery_task(session, world_service) -> None:
    task = getattr(session, "_mana_recovery_task", None)
    if task is not None and not task.done():
        return
    try:
        session._mana_recovery_task = asyncio.create_task(_mana_recovery_loop(session, world_service))
    except RuntimeError:
        session._mana_recovery_task = None


def install_mana_regeneration_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_mana_regeneration_runtime_installed", False):
        return
    original_enter_character = player_session_class.enter_character
    original_playing_prompt = player_session_class.playing_prompt
    original_close = player_session_class.close

    async def enter_character(self) -> None:
        await original_enter_character(self)
        if getattr(self, "character", None) is None or getattr(self, "combatant", None) is None:
            return
        _ensure_mana_recovery_task(self, world_service)
        await self.send_client_state()

    async def playing_prompt(self) -> None:
        _ensure_mana_recovery_task(self, world_service)
        await original_playing_prompt(self)

    async def close(self) -> None:
        task = getattr(self, "_mana_recovery_task", None)
        if task is not None and not task.done():
            task.cancel()
        await original_close(self)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class.close = close
    player_session_class._mana_regeneration_runtime_installed = True
