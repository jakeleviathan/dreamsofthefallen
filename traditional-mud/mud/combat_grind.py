from __future__ import annotations

import random
from dataclasses import dataclass
from time import monotonic

import mud.crafting as crafting
from mud.corpse_loot import add_corpse_item, loot_table_for_enemy
from mud.world import ROOMS_BY_KEY


HUNT_CHAIN_WINDOW_SECONDS = 90.0
HUNT_LOOT_MILESTONE = 5


@dataclass(slots=True)
class HuntChainState:
    """Session-local combat momentum for one character in one region."""

    character_id: int | None = None
    region_key: str = ""
    kills: int = 0
    last_kill_at: float = 0.0

    def record(self, character_id: int, region_key: str, now: float) -> int:
        same_hunt = (
            self.character_id == int(character_id)
            and self.region_key == region_key
            and self.kills > 0
            and 0.0 <= now - self.last_kill_at <= HUNT_CHAIN_WINDOW_SECONDS
        )
        self.character_id = int(character_id)
        self.region_key = region_key
        self.kills = self.kills + 1 if same_hunt else 1
        self.last_kill_at = now
        return self.kills

    def active_for(self, character_id: int, region_key: str, now: float) -> bool:
        return bool(
            self.character_id == int(character_id)
            and self.region_key == region_key
            and self.kills > 0
            and 0.0 <= now - self.last_kill_at <= HUNT_CHAIN_WINDOW_SECONDS
        )

    def reset(self) -> None:
        self.character_id = None
        self.region_key = ""
        self.kills = 0
        self.last_kill_at = 0.0


def chain_bonus_percent(kills: int) -> int:
    """Small capped XP acceleration for sustained ordinary hunting."""
    if kills >= 10:
        return 15
    if kills >= 6:
        return 10
    if kills >= 3:
        return 5
    return 0


def _chain_state(session) -> HuntChainState:
    state = getattr(session, "_hunt_chain_state", None)
    if not isinstance(state, HuntChainState):
        state = HuntChainState()
        session._hunt_chain_state = state
    return state


def _victory_sessions(session, enemy) -> tuple:
    """Capture everyone who will actually receive credit before party cleanup.

    Party encounters remove their transient encounter record while resolving a
    kill. Capturing participants here lets hunting momentum follow each hunter's
    own XP share rather than rewarding only whichever player landed the final hit.
    """
    resolver = getattr(session, "party_victory_sessions", None)
    if callable(resolver):
        try:
            candidates = tuple(resolver(enemy))
        except Exception:
            candidates = (session,)
    else:
        candidates = (session,)

    result = []
    seen_character_ids: set[int] = set()
    for member in candidates or (session,):
        character = getattr(member, "character", None)
        if character is None:
            continue
        character_id = int(character.id)
        if character_id in seen_character_ids:
            continue
        seen_character_ids.add(character_id)
        result.append(member)
    return tuple(result)


def _current_hunt_context(session, enemy) -> tuple[str, str, bool, bool] | None:
    character = getattr(session, "character", None)
    manager = getattr(session, "mobile_npcs", None)
    if character is None or manager is None:
        return None

    room_key = str(getattr(character, "current_room", "") or "")
    room = ROOMS_BY_KEY.get(room_key)
    if room is None or not manager.is_hunting_room(room_key):
        return None

    definition = getattr(enemy, "definition", None)
    xp_reward = int(getattr(definition, "xp_reward", 0) or 0)
    if (
        definition is None
        or xp_reward <= 0
        or bool(getattr(definition, "tutorial", False))
        or str(getattr(definition, "key", "")) == "training_dummy"
    ):
        return None

    mobile_key = getattr(session, "active_mobile_npc_key", None)
    mobile_state = manager.states.get(mobile_key) if mobile_key else None
    is_rare = bool(
        mobile_state is not None
        and bool(getattr(mobile_state.definition, "rare", False))
    )
    # Ordinary hunting mobs participate. Authored elite/boss set pieces do not
    # become an efficient repeatable XP chain merely because they sit near wilds.
    if xp_reward >= 100 and not is_rare:
        return None

    region_key = str(getattr(room, "region_key", "") or "")
    if not region_key:
        return None
    return room_key, region_key, bool(mobile_key), is_rare


def _bonus_material(enemy) -> tuple[str, int] | None:
    """Choose one modest material from the enemy's existing physical loot table."""
    candidates = []
    weights = []
    for entry in loot_table_for_enemy(enemy):
        item = crafting.ITEMS_BY_KEY.get(entry.item_key)
        category = str(getattr(item, "category", "") or "").lower()
        if item is None or category not in {"material", "resource", "ingredient"}:
            continue
        if entry.chance <= 0.0:
            continue
        candidates.append(entry)
        weights.append(max(0.05, float(entry.chance)))

    if not candidates:
        return None
    entry = random.choices(candidates, weights=weights, k=1)[0]
    # Momentum should improve consistency, not duplicate jackpot quantities.
    return entry.item_key, max(1, int(entry.min_quantity))


def _item_name(item_key: str) -> str:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    return str(getattr(item, "name", "") or item_key.replace("_", " ").title())


def _install_help_entry() -> None:
    try:
        import mud.command_guide as command_guide
        from mud.command_guide import CommandEntry

        entry = CommandEntry(
            "combat",
            "HUNT / HUNT STATUS",
            "Read the local hunting ground and your current combat momentum.",
            ("hunting", "grind", "chain", "momentum"),
        )
        if all(existing.syntax.casefold() != entry.syntax.casefold() for existing in command_guide.COMMANDS):
            command_guide.COMMANDS = command_guide.COMMANDS + (entry,)
            command_guide.CATEGORIES = tuple(
                dict.fromkeys(existing.category for existing in command_guide.COMMANDS)
            )
    except Exception:
        return


async def show_hunt_status(session) -> None:
    character = getattr(session, "character", None)
    manager = getattr(session, "mobile_npcs", None)
    if character is None or manager is None:
        await session.send("You cannot read the hunting ground from here.\r\n")
        return

    room_key = str(getattr(character, "current_room", "") or "")
    room = ROOMS_BY_KEY.get(room_key)
    if room is None or not manager.is_hunting_room(room_key):
        await session.send(
            "This area does not support sustained hunting. Look for wild country where creatures roam between rooms.\r\n"
        )
        return

    depth = manager.hunting_room_depth(room_key)
    capacity = manager.hunting_room_capacity(room_key)
    if depth >= 3 or capacity >= 5:
        ground = "deep hunting country"
    elif depth >= 1 or capacity >= 3:
        ground = "established hunting ground"
    else:
        ground = "the fringe of a hunting ground"

    visible = sum(
        1
        for state in manager.npcs_in_room(room_key)
        if state.definition.key in manager._regional_instance_to_pool
        and (
            state.definition.aggressive
            or bool(getattr(state.definition, "attackable", False))
        )
    )
    await session.send(
        f"\r\nYou are in {ground}. This room can naturally gather about {capacity} roaming threats; "
        f"{visible} are here now. Creatures repopulate through the surrounding habitat rather than appearing in place.\r\n"
    )

    region_key = str(getattr(room, "region_key", "") or "")
    state = _chain_state(session)
    now = monotonic()
    if state.active_for(int(character.id), region_key, now):
        percent = chain_bonus_percent(state.kills)
        remaining = max(0, int(HUNT_CHAIN_WINDOW_SECONDS - (now - state.last_kill_at)))
        await session.send(
            f"Hunting momentum: {state.kills} consecutive kills, "
            f"{percent}% combat XP bonus, about {remaining}s to keep the chain alive.\r\n"
        )
    else:
        await session.send(
            "Hunting momentum: none. Three timely ordinary kills begin the XP bonus; sustained pressure can draw out rarer predators.\r\n"
        )


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
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


def install_combat_grind_runtime(player_session_class, world_service=None) -> None:
    """Install hunting momentum on top of the fully assembled combat stack.

    The regional population manager owns spawn density and ecology. This runtime
    only adds player-facing progression rewards and status, so quest scripts,
    boss encounters, corpse ownership, party loot, and existing kill credit stay
    authoritative.
    """
    if getattr(player_session_class, "_combat_grind_runtime_installed", False):
        return

    _install_help_entry()

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if callable(previous_finish_enemy):
        async def _finish_enemy_defeat(self, enemy) -> None:
            eligible = getattr(self, "active_enemy", None) is enemy
            reward_candidates: list[tuple[object, tuple[str, str, bool, bool], int]] = []
            if eligible:
                for member in _victory_sessions(self, enemy):
                    member_character = getattr(member, "character", None)
                    hunt_context = (
                        _current_hunt_context(member, enemy)
                        if member_character is not None
                        else None
                    )
                    if hunt_context is None or member_character is None:
                        continue
                    reward_candidates.append(
                        (
                            member,
                            hunt_context,
                            int(getattr(member_character, "experience", 0) or 0),
                        )
                    )

            prior_corpse_id = getattr(self, "_last_defeat_corpse_id", None)
            await previous_finish_enemy(self, enemy)

            if not reward_candidates:
                return

            now = monotonic()
            rewarded: list[tuple[object, object, int, tuple[str, str, bool, bool]]] = []
            for member, hunt_context, before_experience in reward_candidates:
                refreshed = getattr(member, "character", None)
                if refreshed is None:
                    continue
                gained = (
                    int(getattr(refreshed, "experience", 0) or 0)
                    - before_experience
                )
                # Shared lifecycle and party systems remain authoritative. A
                # hunter only builds momentum from XP they actually received.
                if gained <= 0:
                    continue

                _room_key, region_key, was_mobile, is_rare = hunt_context
                state = _chain_state(member)
                kills = state.record(int(refreshed.id), region_key, now)
                percent = chain_bonus_percent(kills)

                if percent > 0:
                    # Base the bonus on the player's real award, not the monster's
                    # nominal XP. Party shares and any other progression modifiers
                    # therefore scale cleanly instead of being bypassed.
                    requested_bonus = max(0, round(gained * percent / 100.0))
                    if requested_bonus > 0:
                        level_before_bonus = int(getattr(refreshed, "level", 1) or 1)
                        experience_before_bonus = int(
                            getattr(refreshed, "experience", 0) or 0
                        )
                        new_level = member.database.add_experience(
                            int(refreshed.id),
                            requested_bonus,
                        )
                        latest = member.database.get_character_by_name(refreshed.name)
                        if latest is not None:
                            member.character = latest
                            refreshed = latest
                        actual_bonus = max(
                            0,
                            int(
                                getattr(
                                    refreshed,
                                    "experience",
                                    experience_before_bonus,
                                )
                                or 0
                            )
                            - experience_before_bonus,
                        )
                        await member.send(
                            f"Hunting chain {kills}: +{actual_bonus} bonus experience "
                            f"({percent}% momentum).\r\n"
                        )
                        if new_level > level_before_bonus:
                            await member.send(
                                f"*** You have reached level {new_level}! ***\r\n"
                            )

                rewarded.append((member, refreshed, kills, hunt_context))

            if not rewarded:
                return

            # One defeated creature creates one unit of regional pressure even
            # when a party shares the kill. Roaming regional NPCs already record
            # this inside MobileNpcManager.defeat, so only static hunting prey
            # needs the explicit bridge here.
            if not rewarded[0][3][2]:
                manager = getattr(self, "mobile_npcs", None)
                if manager is not None:
                    manager.note_hunt_kill(rewarded[0][3][1])

            new_corpse_id = getattr(self, "_last_defeat_corpse_id", None)
            corpse_matches = bool(
                new_corpse_id is not None
                and new_corpse_id != prior_corpse_id
                and getattr(self, "_last_defeat_corpse_enemy_key", None)
                == str(getattr(enemy.definition, "key", ""))
            )
            if not corpse_matches:
                return

            for member, refreshed, kills, hunt_context in rewarded:
                _room_key, _region_key, _was_mobile, is_rare = hunt_context
                bonus_loot_due = kills % HUNT_LOOT_MILESTONE == 0 or is_rare
                if not bonus_loot_due:
                    continue
                bonus = _bonus_material(enemy)
                if bonus is None:
                    continue
                item_key, quantity = bonus
                add_corpse_item(
                    self.database,
                    int(new_corpse_id),
                    item_key,
                    quantity,
                    int(refreshed.id),
                )
                reason = "rare prey" if is_rare else "your hunting momentum"
                await member.send(
                    f"{reason.capitalize()} yields extra salvage: "
                    f"{quantity}x {_item_name(item_key)} in the corpse.\r\n"
                )

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_death = getattr(player_session_class, "_handle_character_death", None)
    if callable(previous_death):
        async def _handle_character_death(self, *args, **kwargs):
            _chain_state(self).reset()
            return await previous_death(self, *args, **kwargs)

        player_session_class._handle_character_death = _handle_character_death

    previous_playing_prompt = getattr(player_session_class, "playing_prompt", None)
    if callable(previous_playing_prompt):
        async def playing_prompt(self) -> None:
            if getattr(self, "character", None) is None:
                await previous_playing_prompt(self)
                return

            command = await self.prompt("\r\n> ")
            if command is None:
                state = getattr(self, "state", None)
                if state is not None and hasattr(type(state), "DISCONNECTED"):
                    self.state = type(state).DISCONNECTED
                return

            normalized = " ".join(command.strip().lower().split())
            if normalized in {"hunt", "hunting", "hunt status", "hunting status"}:
                await show_hunt_status(self)
                return
            await _delegate_prompt(self, previous_playing_prompt, command)

        player_session_class.playing_prompt = playing_prompt

    player_session_class._combat_grind_runtime_installed = True
