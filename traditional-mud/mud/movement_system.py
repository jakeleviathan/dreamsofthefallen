from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovementRules:
    """First production tuning for travel fatigue in Astralis.

    Movement is deliberately a pressure system, not a permission system. Reaching
    zero never turns a character into a statue; it makes continued travel slow
    until the character recovers.
    """

    base_maximum: int = 100
    maximum_per_level_after_first: int = 1
    ordinary_room_cost: int = 1
    rough_room_cost: int = 2
    difficult_room_cost: int = 3
    severe_room_cost: int = 4
    flee_cost: int = 6
    recovery_interval_seconds: float = 3.0
    passive_recovery: int = 1
    resting_recovery: int = 5
    restful_place_bonus: int = 2
    exhausted_delay_seconds: float = 0.70
    spent_delay_seconds: float = 1.50


MOVEMENT_RULES = MovementRules()

# These words are intentionally broad enough to cover the authored world without
# requiring hundreds of per-room overrides. SAFE rooms win first so a starter
# city overlooking a swamp does not become expensive merely because "swamp" is
# present in its regional flavor.
_SEVERE_PHRASES = (
    "deep snow",
    "deep mire",
    "quagmire",
    "bog",
    "steep climb",
    "flooded channel",
    "lava",
    "volcanic",
    "avalanche",
)
_DIFFICULT_PHRASES = (
    "swamp",
    "marsh",
    "mire",
    "tundra",
    "snow",
    "mountain",
    "scree",
    "deep cavern",
)
_ROUGH_PHRASES = (
    "forest",
    "woods",
    "thicket",
    "wilderness",
    "ruin",
    "cave",
    "cavern",
    "crypt",
    "catacomb",
    "dungeon",
    "mine",
    "underworks",
    "underclock",
    "holdfast",
    "keep",
    "salt waste",
    "desert",
)
_EASY_PHRASES = (
    "road",
    "street",
    "market",
    "plaza",
    "hall",
    "bridge",
    "city",
    "court",
    "square",
)
_RESTFUL_TAGS = {
    "safe",
    "inn",
    "tavern",
    "camp",
    "campfire",
    "hearth",
    "home",
    "sanctuary",
    "rest",
}
_RESTFUL_FEATURE_WORDS = ("bed", "bedroll", "campfire", "hearth", "bunk", "cot", "inn")
_STATE_RANK = {"Normal": 0, "Winded": 1, "Exhausted": 2, "Spent": 3}


def maximum_movement_for_level(level: int, bonus: int = 0) -> int:
    """Movement grows modestly with level and deliberately ignores Grace."""

    return max(
        1,
        MOVEMENT_RULES.base_maximum
        + max(0, int(level) - 1) * MOVEMENT_RULES.maximum_per_level_after_first
        + max(0, int(bonus)),
    )


def movement_state_name(current: int, maximum: int | None = None) -> str:
    """Return the player-facing fatigue band agreed for the HUD and text game."""

    value = max(0, int(current))
    if value <= 0:
        return "Spent"
    if value <= 9:
        return "Exhausted"
    if value <= 24:
        return "Winded"
    return "Normal"


def _scene_text(scene) -> str:
    tags = tuple(str(tag).lower().replace("_", " ") for tag in getattr(scene, "tags", ()))
    return " ".join(
        (
            str(getattr(scene, "key", "")).lower().replace("_", " "),
            str(getattr(scene, "name", "")).lower(),
            *tags,
        )
    )


def movement_cost_for_room(world_service, room_key: str) -> int:
    """Price entry into a room from its authored terrain identity.

    SAFE rooms remain ordinary-cost even when their prose happens to mention a
    harsh biome. Roads and streets are also intentionally cheap. Wilderness,
    dungeons, swamp, snow, mountains, and truly severe terrain progressively cost
    more without requiring every room author to remember a numeric field.
    """

    scene = world_service.scene(room_key) if world_service is not None else None
    if scene is None:
        return MOVEMENT_RULES.ordinary_room_cost

    tags = {str(tag).lower().replace("_", " ") for tag in getattr(scene, "tags", ())}
    if "safe" in tags:
        return MOVEMENT_RULES.ordinary_room_cost

    text = _scene_text(scene)
    if any(phrase in text for phrase in _EASY_PHRASES):
        return MOVEMENT_RULES.ordinary_room_cost
    if any(phrase in text for phrase in _SEVERE_PHRASES):
        return MOVEMENT_RULES.severe_room_cost
    if any(phrase in text for phrase in _DIFFICULT_PHRASES):
        return MOVEMENT_RULES.difficult_room_cost
    if any(phrase in text for phrase in _ROUGH_PHRASES):
        return MOVEMENT_RULES.rough_room_cost
    return MOVEMENT_RULES.ordinary_room_cost


def is_restful_place(world_service, room_key: str) -> bool:
    scene = world_service.scene(room_key) if world_service is not None else None
    if scene is None:
        return False
    tags = {str(tag).lower().replace("_", " ") for tag in getattr(scene, "tags", ())}
    if tags.intersection(_RESTFUL_TAGS):
        return True
    for feature in getattr(scene, "features", ()):
        name = str(getattr(feature, "name", "")).lower()
        if any(word in name for word in _RESTFUL_FEATURE_WORDS):
            return True
    return False


def _capacity_bonus(session) -> int:
    # Deliberate hook for future equipment, food, spells, mounts, or world effects.
    # Grace is *not* consulted here; it already owns attack-speed identity.
    try:
        return max(0, int(getattr(session, "movement_capacity_bonus", 0)))
    except (TypeError, ValueError):
        return 0


def _recovery_bonus(session) -> int:
    # Same principle as capacity: authored effects can opt in later without
    # changing the core travel rules.
    try:
        return max(0, int(getattr(session, "movement_recovery_bonus", 0)))
    except (TypeError, ValueError):
        return 0


def _sync_capacity(session) -> None:
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if character is None or combatant is None:
        return

    desired = maximum_movement_for_level(character.level, _capacity_bonus(session))
    old_max = max(1, int(getattr(combatant, "max_movement", MOVEMENT_RULES.base_maximum)))
    current = max(0, int(getattr(combatant, "current_movement", old_max)))
    if desired > old_max:
        # Gaining capacity (normally by leveling) gives the newly earned points
        # immediately instead of creating an invisible deficit.
        current += desired - old_max
    combatant.max_movement = desired
    combatant.current_movement = min(desired, current)


def restore_movement(session, amount: int) -> int:
    """Public hook for food/spells/world effects to restore movement safely."""

    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return 0
    _sync_capacity(session)
    before = int(combatant.current_movement)
    combatant.current_movement = min(
        int(combatant.max_movement),
        before + max(0, int(amount)),
    )
    return int(combatant.current_movement) - before


def spend_movement(session, amount: int) -> tuple[int, str, str]:
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return 0, "Normal", "Normal"
    _sync_capacity(session)
    before = max(0, int(combatant.current_movement))
    before_state = movement_state_name(before, combatant.max_movement)
    spent = min(before, max(0, int(amount)))
    combatant.current_movement = max(0, before - max(0, int(amount)))
    after_state = movement_state_name(combatant.current_movement, combatant.max_movement)
    return spent, before_state, after_state


def _recovery_amount(session, world_service) -> int:
    if getattr(session, "active_enemy", None) is not None:
        return 0
    resting = bool(getattr(session, "_movement_resting", False))
    amount = MOVEMENT_RULES.resting_recovery if resting else MOVEMENT_RULES.passive_recovery
    if resting and getattr(session, "character", None) is not None:
        if is_restful_place(world_service, session.character.current_room or ""):
            amount += MOVEMENT_RULES.restful_place_bonus
    return amount + _recovery_bonus(session)


def recover_movement_once(session, world_service) -> int:
    combatant = getattr(session, "combatant", None)
    character = getattr(session, "character", None)
    if combatant is None or character is None:
        return 0
    _sync_capacity(session)
    amount = _recovery_amount(session, world_service)
    if amount <= 0 or combatant.current_movement >= combatant.max_movement:
        return 0
    before = int(combatant.current_movement)
    combatant.current_movement = min(combatant.max_movement, before + amount)
    return int(combatant.current_movement) - before


def _destination_for_direction(world_service, room_key: str, direction: str) -> str | None:
    scene = world_service.scene(room_key) if world_service is not None else None
    if scene is None:
        return None
    for exit_definition in getattr(scene, "exits", ()):
        try:
            if exit_definition.matches_direction(direction):
                return exit_definition.destination_key
        except AttributeError:
            if str(getattr(exit_definition, "direction", "")).lower() == direction.strip().lower():
                return getattr(exit_definition, "destination_key", None)
    return None


def _travel_delay(current: int, cost: int) -> float:
    state = movement_state_name(current)
    if state == "Spent" or current < cost:
        return MOVEMENT_RULES.spent_delay_seconds
    if state == "Exhausted":
        return MOVEMENT_RULES.exhausted_delay_seconds
    return 0.0


async def _announce_fatigue_drop(session, before_state: str, after_state: str) -> None:
    if _STATE_RANK.get(after_state, 0) <= _STATE_RANK.get(before_state, 0):
        return
    messages = {
        "Winded": "You are getting winded. Long travel will start to matter if you keep pushing.",
        "Exhausted": "You are exhausted. You can keep moving, but your pace is slowing.",
        "Spent": "Your movement reserve is spent. You can still travel, but every step is slow until you recover.",
    }
    text = messages.get(after_state)
    if text:
        await session.send(text + "\r\n")


async def _movement_recovery_loop(session, world_service) -> None:
    try:
        while True:
            await asyncio.sleep(MOVEMENT_RULES.recovery_interval_seconds)
            recovered = recover_movement_once(session, world_service)
            if recovered > 0:
                try:
                    await session.send_client_state()
                except (ConnectionError, asyncio.CancelledError):
                    raise
                except Exception:
                    # Client-state presentation should never be able to kill the
                    # recovery loop or the player session.
                    pass
    except asyncio.CancelledError:
        return


def _ensure_recovery_task(session, world_service) -> None:
    task = getattr(session, "_movement_recovery_task", None)
    if task is not None and not task.done():
        return
    try:
        session._movement_recovery_task = asyncio.create_task(
            _movement_recovery_loop(session, world_service)
        )
    except RuntimeError:
        # Unit construction outside a running event loop is allowed; the first
        # real playing prompt/character entry will try again.
        session._movement_recovery_task = None


async def _show_movement_status(session, world_service) -> None:
    combatant = getattr(session, "combatant", None)
    character = getattr(session, "character", None)
    if combatant is None or character is None:
        await session.send("Movement is not initialized yet.\r\n")
        return
    _sync_capacity(session)
    state = movement_state_name(combatant.current_movement, combatant.max_movement)
    resting = bool(getattr(session, "_movement_resting", False))
    recovery = _recovery_amount(session, world_service)
    await session.send(
        f"Movement: {combatant.current_movement}/{combatant.max_movement} ({state}). "
        f"Recovery: {recovery} every {MOVEMENT_RULES.recovery_interval_seconds:g}s"
        + (" while resting" if resting else " while out of combat")
        + ".\r\n"
    )
    await session.send(
        "Ordinary rooms cost 1 movement; rough wilderness/dungeons cost more. "
        "FLEE costs 6. At 0 movement you can still travel, but slowly. REST recovers faster; STAND stops resting.\r\n"
    )


def install_movement_runtime(player_session_class, world_service) -> None:
    """Install real movement cost, fatigue, recovery, rest, and HUD state."""

    if getattr(player_session_class, "_movement_runtime_installed", False):
        return

    original_enter_character = player_session_class.enter_character
    original_move_character = player_session_class.move_character
    original_attempt_flee = player_session_class.attempt_flee
    original_start_combat = player_session_class.start_combat
    original_start_mobile_npc_combat = player_session_class.start_mobile_npc_combat
    original_playing_prompt = player_session_class.playing_prompt
    original_send_client_state = player_session_class.send_client_state
    original_close = player_session_class.close

    async def enter_character(self) -> None:
        await original_enter_character(self)
        if getattr(self, "character", None) is None or getattr(self, "combatant", None) is None:
            return
        self._movement_resting = False
        _sync_capacity(self)
        # A newly entered character begins rested. Movement, like HP/mana in the
        # current game, is session-state rather than a logout-punishment system.
        self.combatant.current_movement = self.combatant.max_movement
        _ensure_recovery_task(self, world_service)
        await self.send_client_state()

    async def move_character(self, direction: str) -> None:
        character = getattr(self, "character", None)
        combatant = getattr(self, "combatant", None)
        if character is None or combatant is None:
            await original_move_character(self, direction)
            return

        origin = character.current_room or ""
        destination = _destination_for_direction(world_service, origin, direction)
        preview_cost = (
            movement_cost_for_room(world_service, destination)
            if destination
            else MOVEMENT_RULES.ordinary_room_cost
        )
        _sync_capacity(self)
        delay = _travel_delay(int(combatant.current_movement), preview_cost)
        if delay > 0:
            if int(combatant.current_movement) <= 0:
                await self.send("You force your tired legs onward at a slower pace.\r\n")
            await asyncio.sleep(delay)

        await original_move_character(self, direction)

        character = getattr(self, "character", None)
        if character is None or (character.current_room or "") == origin:
            return

        self._movement_resting = False
        actual_cost = movement_cost_for_room(world_service, character.current_room or "")
        _spent, before_state, after_state = spend_movement(self, actual_cost)
        await _announce_fatigue_drop(self, before_state, after_state)
        await self.send_client_state()

    async def attempt_flee(self) -> None:
        can_attempt = getattr(self, "active_enemy", None) is not None
        if can_attempt and hasattr(self, "_available_flee_exits"):
            try:
                can_attempt = bool(self._available_flee_exits())
            except Exception:
                pass
        if can_attempt:
            self._movement_resting = False
            combatant = getattr(self, "combatant", None)
            if combatant is not None and int(combatant.current_movement) <= 0:
                await asyncio.sleep(0.35)
        await original_attempt_flee(self)
        if can_attempt and getattr(self, "combatant", None) is not None:
            _spent, before_state, after_state = spend_movement(self, MOVEMENT_RULES.flee_cost)
            await _announce_fatigue_drop(self, before_state, after_state)
            await self.send_client_state()

    async def start_combat(self, target_text: str) -> None:
        self._movement_resting = False
        await original_start_combat(self, target_text)

    async def start_mobile_npc_combat(self, npc_key: str, *, initiated_by_npc: bool = False) -> bool:
        self._movement_resting = False
        return await original_start_mobile_npc_combat(
            self, npc_key, initiated_by_npc=initiated_by_npc
        )

    async def send_client_state(self) -> None:
        _sync_capacity(self)
        await original_send_client_state(self)
        telnet = getattr(self, "telnet", None)
        combatant = getattr(self, "combatant", None)
        character = getattr(self, "character", None)
        if (
            telnet is None
            or combatant is None
            or character is None
            or not getattr(telnet, "gmcp_enabled", False)
        ):
            return
        await telnet.send_gmcp(
            "Dreams.Movement",
            {
                "current": int(combatant.current_movement),
                "maximum": int(combatant.max_movement),
                "state": movement_state_name(combatant.current_movement, combatant.max_movement),
                "resting": bool(getattr(self, "_movement_resting", False)),
                "recovery_per_tick": _recovery_amount(self, world_service),
                "tick_seconds": MOVEMENT_RULES.recovery_interval_seconds,
            },
        )

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await original_playing_prompt(self)
            return

        _ensure_recovery_task(self, world_service)
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized in {"movement", "move points", "movement points", "fatigue", "endurance"}:
            await _show_movement_status(self, world_service)
            return
        if normalized in {"rest", "sit", "sit down"}:
            if getattr(self, "active_enemy", None) is not None:
                await self.send("You cannot settle down to rest while you are fighting.\r\n")
                return
            self._movement_resting = True
            place_text = (
                " This is a good place to recover."
                if is_restful_place(world_service, self.character.current_room or "")
                else ""
            )
            await self.send("You settle down and rest. Movement will recover much faster, and health will recover faster too." + place_text + "\r\n")
            await self.send_client_state()
            return
        if normalized in {"stand", "stand up", "rise"}:
            if bool(getattr(self, "_movement_resting", False)):
                self._movement_resting = False
                await self.send("You get back to your feet.\r\n")
            else:
                await self.send("You are already on your feet.\r\n")
            await self.send_client_state()
            return

        had_instance_prompt = "prompt" in self.__dict__
        previous_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await original_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = previous_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"}:
            await self.send(
                "Travel: MOVEMENT shows fatigue; REST accelerates movement and health recovery; STAND ends resting. "
                "Ordinary travel costs little, difficult terrain costs more, and FLEE consumes movement.\r\n"
            )

    async def close(self) -> None:
        task = getattr(self, "_movement_recovery_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await original_close(self)

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.attempt_flee = attempt_flee
    player_session_class.start_combat = start_combat
    player_session_class.start_mobile_npc_combat = start_mobile_npc_combat
    player_session_class.send_client_state = send_client_state
    player_session_class.playing_prompt = playing_prompt
    player_session_class.close = close
    player_session_class._movement_runtime_installed = True
