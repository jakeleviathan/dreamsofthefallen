from __future__ import annotations

import asyncio
import random
from dataclasses import replace
from time import monotonic

import mud.character_options as character_options
from mud.combat import FLEE_RULES
from mud.database import Database
from mud.mechanics import class_abilities_for_level
from mud.scavenging import RUMMAGE_NODES
from mud.stats import CharacterStats


# Racial abilities are intentionally self-contained. In particular, Forest Elf
# Slipstep never requires a room author to add hidden tracks, special exits, or
# race-only scenery just to make the racial button useful.
RACIAL_ACTIVE_COOLDOWNS: dict[str, float] = {
    "human": 30.0,
    "forest_elf": 30.0,
    "moon_elf": 30.0,
    "dwarf": 30.0,
    "goblin": 8.0,
    "troll": 20.0,
    "undead": 45.0,
    "sporekin": 30.0,
}

RACIAL_ACTIVE_KEYS: dict[str, str] = {
    "human": "racial_adapt",
    "forest_elf": "racial_slipstep",
    "moon_elf": "racial_reconsider",
    "dwarf": "racial_brace",
    "goblin": "racial_scrounge",
    "troll": "racial_bloodscent",
    "undead": "racial_stillness",
    "sporekin": "racial_chorus_bloom",
}

RACIAL_ACTIVE_ALIASES: dict[str, tuple[str, ...]] = {
    "human": ("adapt",),
    "forest_elf": ("slipstep", "slip step"),
    "moon_elf": ("reconsider",),
    "dwarf": ("brace",),
    "goblin": ("scrounge",),
    "troll": ("bloodscent", "blood scent"),
    "undead": ("stillness",),
    "sporekin": ("chorus bloom", "chorus"),
}


RACIAL_TEXT: dict[str, tuple[str, str, str, str]] = {
    "human": (
        "Fast Learner",
        "Human practiced abilities gain skill experience 10% faster over the normal use cadence; every tenth successful one-point ability use earns one additional skill XP.",
        "Adapt",
        "At will, choose MIGHT, GRACE, LOVE, or MIND to gain +2 to that stat for 12 seconds. Cooldown: 30 seconds.",
    ),
    "forest_elf": (
        "Elven Grace",
        "Forest Elves begin with their existing +2 racial Grace advantage; the passive is always useful and requires no special room content.",
        "Slipstep",
        "For 10 seconds, subtle Elven movement softens incoming blows and makes fleeing substantially easier. Cooldown: 30 seconds.",
    ),
    "moon_elf": (
        "Long View",
        "While staying focused on the same combat target, a Moon Elf gradually reads its movement more clearly, improving normal attack accuracy over time.",
        "Reconsider",
        "Reassess the current fight and shave 3 seconds from every class ability cooldown that is still running. Cooldown: 30 seconds.",
    ),
    "dwarf": (
        "Resilience",
        "Dwarves are unusually resistant to stagger and forced movement. The hook is locked now even though knockback and stagger are not yet live combat systems.",
        "Brace",
        "Set your stance for 10 seconds, softening incoming basic damage. This uses mitigation rather than hidden racial AC so Astralis keeps AC equipment-derived. Cooldown: 30 seconds.",
    ),
    "goblin": (
        "Junkwise",
        "Goblins are unusually good at noticing when discarded material has practical salvage value.",
        "Scrounge",
        "Check the current room for already-authored salvage or rummage opportunities. It never creates generic free loot and does not require every room to contain Goblin-only rewards. Cooldown: 8 seconds.",
    ),
    "troll": (
        "Regeneration",
        "Trolls recover 1 additional hit point whenever normal server regeneration occurs.",
        "Bloodscent",
        "Against an enemy at half health or below, lock onto its weakness and reduce its effective armor by 2 for 12 seconds. Cooldown: 20 seconds.",
    ),
    "undead": (
        "Unliving",
        "Undead need no food, drink, sleep, or breath, and poison and disease have reduced effect on them.",
        "Stillness",
        "Become unnaturally still, breaking ordinary combat attention and gaining temporary protection until you take an action or 20 seconds pass. Cooldown: 45 seconds.",
    ),
    "sporekin": (
        "Deep Regeneration",
        "Sporekin recover 2 additional hit points whenever normal server regeneration occurs.",
        "Chorus Bloom",
        "For a brief pulse, you and other player characters sharing your room recover a small amount of health over time. Cooldown: 30 seconds.",
    ),
}


def install_racial_ability_definitions() -> None:
    """Attach the approved passive/active identities to all eight launch races."""
    replacements = []
    for race in character_options.RACES:
        authored = RACIAL_TEXT.get(race.key)
        if authored is None:
            replacements.append(race)
            continue
        passive_name, passive_description, ability_name, ability_description = authored
        replacements.append(
            replace(
                race,
                passive_name=passive_name,
                passive_description=passive_description,
                ability_name=ability_name,
                ability_description=ability_description,
                design_status="racial_kit_locked",
            )
        )
    character_options.RACES = tuple(replacements)
    character_options.RACES_BY_KEY.clear()
    character_options.RACES_BY_KEY.update({race.key: race for race in character_options.RACES})


def install_fast_learner_database_hook() -> None:
    """Make Human Fast Learner a real +10% ability-skill progression effect.

    Ability skill XP is integer-valued and normal successful uses currently award
    one point. Awarding one bonus point on every tenth use gives an exact +10%
    over that normal cadence without introducing fractional persistence.
    """
    if getattr(Database, "_fast_learner_hook_installed", False):
        return
    previous = Database.record_ability_use

    def record_ability_use(self, character_id: int, ability_key: str, skill_xp_gain: int = 1) -> None:
        bonus = 0
        if skill_xp_gain > 0:
            with self.connect() as db:
                character = db.execute(
                    "SELECT race FROM characters WHERE id = ?", (character_id,)
                ).fetchone()
                if character is not None and character["race"] == "human":
                    progress = db.execute(
                        "SELECT uses FROM character_abilities WHERE character_id = ? AND ability_key = ?",
                        (character_id, ability_key),
                    ).fetchone()
                    next_use = (0 if progress is None else int(progress["uses"])) + 1
                    if next_use % 10 == 0:
                        bonus = 1
        previous(self, character_id, ability_key, skill_xp_gain + bonus)

    Database.record_ability_use = record_ability_use
    Database._fast_learner_hook_installed = True


def long_view_armor_reduction(elapsed_seconds: float) -> int:
    """Pure tuning helper used by Long View and its regression tests."""
    if elapsed_seconds >= 20.0:
        return 3
    if elapsed_seconds >= 10.0:
        return 2
    if elapsed_seconds >= 5.0:
        return 1
    return 0


def _racial_key(session) -> str | None:
    character = getattr(session, "character", None)
    return None if character is None else getattr(character, "race", None)


def _active_key(race_key: str) -> str:
    return RACIAL_ACTIVE_KEYS[race_key]


def _cooldown_remaining(session, race_key: str) -> float:
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return 0.0
    return max(0.0, combatant.cooldowns.get(_active_key(race_key), 0.0) - monotonic())


def _start_racial_cooldown(session, race_key: str) -> None:
    session.combatant.start_cooldown(
        _active_key(race_key), RACIAL_ACTIVE_COOLDOWNS[race_key]
    )


def _record_racial_use(session, race_key: str) -> None:
    recorder = getattr(session.database, "record_ability_use", None)
    if recorder is not None:
        recorder(session.character.id, _active_key(race_key))


def _adjust_stat(combatant, stat_key: str, amount: int) -> None:
    values = combatant.stats.as_dict()
    values[stat_key] = max(0, values[stat_key] + amount)
    combatant.stats = CharacterStats(**values)


async def _expire_adapt(session, stat_key: str, token: object) -> None:
    try:
        await asyncio.sleep(12.0)
    except asyncio.CancelledError:
        return
    if getattr(session, "_racial_adapt_token", None) is not token:
        return
    if getattr(session, "combatant", None) is not None:
        _adjust_stat(session.combatant, stat_key, -2)
    session._racial_adapt_stat = None
    session._racial_adapt_token = None
    await session.send(f"Your Human adaptation toward {stat_key.title()} settles back to normal.\r\n")
    await session.send_client_state()


async def _use_adapt(session, argument: str) -> bool:
    stat_key = argument.strip().lower()
    if stat_key not in {"might", "grace", "love", "mind"}:
        await session.send("Adapt to what? Use ADAPT MIGHT, ADAPT GRACE, ADAPT LOVE, or ADAPT MIND.\r\n")
        return False

    old_task = getattr(session, "_racial_adapt_task", None)
    old_stat = getattr(session, "_racial_adapt_stat", None)
    if old_task is not None and not old_task.done():
        old_task.cancel()
    if old_stat and session.combatant is not None:
        _adjust_stat(session.combatant, old_stat, -2)

    _adjust_stat(session.combatant, stat_key, 2)
    token = object()
    session._racial_adapt_token = token
    session._racial_adapt_stat = stat_key
    session._racial_adapt_task = asyncio.create_task(_expire_adapt(session, stat_key, token))
    await session.send(
        f"You adapt your approach toward {stat_key.title()}, gaining +2 {stat_key.title()} for 12 seconds.\r\n"
    )
    return True


async def _use_slipstep(session) -> bool:
    now = asyncio.get_running_loop().time()
    session._racial_slipstep_until = now + 10.0
    # Existing combat already has a generic temporary mitigation hook. Slipstep
    # uses it for glancing blows while the flee wrapper supplies the evasive part.
    session.ward_until = max(getattr(session, "ward_until", 0.0), now + 10.0)
    await session.send(
        "Your footing lightens into Slipstep. For 10 seconds, incoming blows glance more easily and breaking away from combat is much easier.\r\n"
    )
    return True


async def _use_reconsider(session) -> bool:
    now = monotonic()
    abilities = class_abilities_for_level(
        session.character.character_class or "",
        session.character.level,
        session.character.deity_key,
    )
    changed = 0
    for ability in abilities:
        ready_at = session.combatant.cooldowns.get(ability.key)
        if ready_at is None or ready_at <= now:
            continue
        session.combatant.cooldowns[ability.key] = max(now, ready_at - 3.0)
        changed += 1
    if changed:
        await session.send(
            f"You reconsider the rhythm of the fight. {changed} active class cooldown{'s' if changed != 1 else ''} shorten by 3 seconds.\r\n"
        )
    else:
        await session.send("You reconsider your options, but no class ability is currently cooling down.\r\n")
    return True


async def _use_brace(session) -> bool:
    now = asyncio.get_running_loop().time()
    session._racial_brace_until = now + 10.0
    session.ward_until = max(getattr(session, "ward_until", 0.0), now + 10.0)
    await session.send(
        "You brace into a low Dwarven stance. For 10 seconds, incoming basic blows are softened and your footing is set against future forced-movement effects.\r\n"
    )
    return True


async def _use_scrounge(session) -> bool:
    room_key = session.character.current_room or ""
    nodes = RUMMAGE_NODES.nodes_for_room(room_key)
    if not nodes:
        await session.send(
            "You give the area a Goblin once-over. Nothing here stands out as an authored salvage opportunity worth claiming.\r\n"
        )
        return True
    targets: list[str] = []
    for node in nodes:
        if node.targets:
            targets.append(node.targets[0])
    if targets:
        await session.send(
            "Junkwise catches on something useful: " + ", ".join(targets) + ". Try RUMMAGE <target> where appropriate.\r\n"
        )
    else:
        await session.send("Something here looks worth a closer rummage.\r\n")
    return True


async def _restore_bloodscent(session, enemy, original_ac: int) -> None:
    try:
        await asyncio.sleep(12.0)
    except asyncio.CancelledError:
        return
    if getattr(session, "active_enemy", None) is not enemy:
        return
    enemy.definition = replace(enemy.definition, armor_class=original_ac)
    await session.send(f"Your Bloodscent focus on {enemy.definition.name} fades.\r\n")


async def _use_bloodscent(session) -> bool:
    enemy = getattr(session, "active_enemy", None)
    if enemy is None:
        await session.send("Bloodscent needs a wounded enemy in front of you.\r\n")
        return False
    if enemy.current_hp is None or enemy.current_hp * 2 > enemy.definition.max_hp:
        await session.send("The target is not wounded deeply enough for Bloodscent to lock on yet.\r\n")
        return False
    original_ac = enemy.definition.armor_class
    enemy.definition = replace(enemy.definition, armor_class=max(0, original_ac - 2))
    old = getattr(session, "_racial_bloodscent_task", None)
    if old is not None and not old.done():
        old.cancel()
    session._racial_bloodscent_task = asyncio.create_task(
        _restore_bloodscent(session, enemy, original_ac)
    )
    await session.send(
        f"Bloodscent fixes on {enemy.definition.name}'s weakness. Its effective armor is reduced by 2 for 12 seconds.\r\n"
    )
    return True


def _clear_stillness(session) -> None:
    if not getattr(session, "_racial_stillness_active", False):
        return
    session._racial_stillness_active = False
    prior = getattr(session, "_racial_pre_stillness_ward", 0.0)
    still_until = getattr(session, "_racial_stillness_until", 0.0)
    if getattr(session, "ward_until", 0.0) <= still_until + 0.001:
        session.ward_until = prior


async def _expire_stillness(session, token: object) -> None:
    try:
        await asyncio.sleep(20.0)
    except asyncio.CancelledError:
        return
    if getattr(session, "_racial_stillness_token", None) is not token:
        return
    _clear_stillness(session)
    session._racial_stillness_token = None
    await session.send("Your unnatural Stillness loosens after twenty seconds.\r\n")


async def _use_stillness(session) -> bool:
    now = asyncio.get_running_loop().time()
    if getattr(session, "active_enemy", None) is not None:
        await session._stop_combat()
    session._racial_pre_stillness_ward = getattr(session, "ward_until", 0.0)
    session._racial_stillness_until = now + 20.0
    session.ward_until = max(session._racial_pre_stillness_ward, session._racial_stillness_until)
    session._racial_stillness_active = True
    token = object()
    session._racial_stillness_token = token
    old = getattr(session, "_racial_stillness_task", None)
    if old is not None and not old.done():
        old.cancel()
    session._racial_stillness_task = asyncio.create_task(_expire_stillness(session, token))
    await session.send(
        "You become corpse-still. Ordinary combat attention breaks from you, and the stillness protects you until you act or twenty seconds pass.\r\n"
    )
    return True


async def _chorus_pulse(session) -> int:
    race_sessions = getattr(type(session), "_racial_live_sessions", set())
    room_key = session.character.current_room
    restored_total = 0
    for other in tuple(race_sessions):
        if getattr(other, "character", None) is None or getattr(other, "combatant", None) is None:
            continue
        if other.character.current_room != room_key:
            continue
        before = other.combatant.current_hp
        other.combatant.current_hp = min(other.combatant.max_hp, other.combatant.current_hp + 1)
        restored = other.combatant.current_hp - before
        restored_total += restored
        if restored:
            await other.send("A soft Chorus Bloom pulse restores 1 HP.\r\n")
            await other.send_client_state()
    return restored_total


async def _continue_chorus_bloom(session) -> None:
    try:
        for _ in range(3):
            await asyncio.sleep(3.0)
            if getattr(session, "character", None) is None:
                return
            await _chorus_pulse(session)
    except asyncio.CancelledError:
        return


async def _use_chorus_bloom(session) -> bool:
    await session.send(
        "You open a brief place in the shared chorus. Four gentle regenerative pulses spread through player characters sharing your room.\r\n"
    )
    await _chorus_pulse(session)
    old = getattr(session, "_racial_bloom_task", None)
    if old is not None and not old.done():
        old.cancel()
    session._racial_bloom_task = asyncio.create_task(_continue_chorus_bloom(session))
    return True


async def _use_racial(session, argument: str = "") -> bool:
    race_key = _racial_key(session)
    if race_key not in RACIAL_ACTIVE_KEYS or getattr(session, "combatant", None) is None:
        return False
    remaining = _cooldown_remaining(session, race_key)
    if remaining > 0.0:
        await session.send(f"Your racial at-will is still recovering ({remaining:.1f}s).\r\n")
        return True

    used = False
    if race_key == "human":
        used = await _use_adapt(session, argument)
    elif race_key == "forest_elf":
        used = await _use_slipstep(session)
    elif race_key == "moon_elf":
        used = await _use_reconsider(session)
    elif race_key == "dwarf":
        used = await _use_brace(session)
    elif race_key == "goblin":
        used = await _use_scrounge(session)
    elif race_key == "troll":
        used = await _use_bloodscent(session)
    elif race_key == "undead":
        used = await _use_stillness(session)
    elif race_key == "sporekin":
        used = await _use_chorus_bloom(session)

    if used:
        _start_racial_cooldown(session, race_key)
        _record_racial_use(session, race_key)
        await session.send_client_state()
    return True


async def _show_racial(session) -> None:
    race_key = _racial_key(session)
    race = character_options.RACES_BY_KEY.get(race_key or "")
    if race is None:
        await session.send("No racial kit is available.\r\n")
        return
    await session.send(f"\r\n--- {race.name} Racial Kit ---\r\n")
    if race.passive_name:
        await session.send(f"Passive: {race.passive_name} - {race.passive_description}\r\n")
    if race.ability_name:
        await session.send(f"At-will: {race.ability_name} - {race.ability_description}\r\n")
    remaining = _cooldown_remaining(session, race.key) if race.key in RACIAL_ACTIVE_KEYS else 0.0
    if remaining > 0.0:
        await session.send(f"Current racial cooldown: {remaining:.1f}s.\r\n")
    else:
        await session.send("Current racial cooldown: ready.\r\n")


async def _long_view_task(session, enemy) -> None:
    original_ac = enemy.definition.armor_class
    start = monotonic()
    applied = 0
    try:
        while getattr(session, "active_enemy", None) is enemy and enemy.alive:
            await asyncio.sleep(1.0)
            reduction = long_view_armor_reduction(monotonic() - start)
            if reduction <= applied:
                continue
            enemy.definition = replace(
                enemy.definition,
                armor_class=max(0, original_ac - reduction),
            )
            applied = reduction
            if reduction == 1:
                await session.send(
                    f"Long View begins to settle on {enemy.definition.name}; its movements are becoming easier to read.\r\n"
                )
    except asyncio.CancelledError:
        return


async def _begin_long_view_if_needed(session) -> None:
    if _racial_key(session) != "moon_elf" or getattr(session, "active_enemy", None) is None:
        return
    old = getattr(session, "_racial_long_view_task", None)
    if old is not None and not old.done():
        old.cancel()
    session._racial_long_view_task = asyncio.create_task(
        _long_view_task(session, session.active_enemy)
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


def _racial_command_payload(race_key: str, normalized: str) -> tuple[bool, str]:
    """Return (is_racial_command, argument_for_active)."""
    raw = normalized.strip().lower()
    for prefix in ("use ", "cast ", "racial "):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
            break
    aliases = sorted(RACIAL_ACTIVE_ALIASES.get(race_key, ()), key=len, reverse=True)
    for alias in aliases:
        if raw == alias:
            return True, ""
        if raw.startswith(alias + " "):
            return True, raw[len(alias):].strip()
    return False, ""


def install_racial_ability_runtime(player_session_class) -> None:
    """Install all eight racial kits as an outer, reusable session layer."""
    if getattr(player_session_class, "_racial_ability_runtime_installed", False):
        return

    install_racial_ability_definitions()
    install_fast_learner_database_hook()

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_attempt_flee = player_session_class.attempt_flee
    previous_start_combat = player_session_class.start_combat
    previous_start_mobile_npc_combat = player_session_class.start_mobile_npc_combat
    previous_close = getattr(player_session_class, "close", None)

    player_session_class._racial_live_sessions = set()

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is not None:
            type(self)._racial_live_sessions.add(self)
            # This is a future-facing hook: once stagger/knockback enters combat,
            # it already has an authored racial strength to consult.
            self.racial_forced_movement_resistance = 0.35 if self.character.race == "dwarf" else 0.0

    async def start_combat(self, target_text: str) -> None:
        await previous_start_combat(self, target_text)
        await _begin_long_view_if_needed(self)

    async def start_mobile_npc_combat(self, npc_key: str, *, initiated_by_npc: bool = False) -> bool:
        started = await previous_start_mobile_npc_combat(
            self, npc_key, initiated_by_npc=initiated_by_npc
        )
        if started:
            await _begin_long_view_if_needed(self)
        return started

    async def attempt_flee(self) -> None:
        if (
            _racial_key(self) != "forest_elf"
            or getattr(self, "active_enemy", None) is None
            or asyncio.get_running_loop().time() >= getattr(self, "_racial_slipstep_until", 0.0)
        ):
            await previous_attempt_flee(self)
            return

        exits = self._available_flee_exits()
        if not exits:
            await self.send("There is nowhere to flee!\r\n")
            return
        enemy_name = self.active_enemy.definition.name
        # Base flee is 70%. Slipstep adds 25 percentage points, capped at 95%.
        if random.random() > min(0.95, FLEE_RULES.base_success_chance + 0.25):
            await self.send(f"You Slipstep for an opening, but {enemy_name} still cuts it off!\r\n")
            return

        direction, destination = random.choice(exits)
        mobile_key = self.active_mobile_npc_key
        movement = None
        if mobile_key and self.mobile_npcs is not None:
            movement = self.mobile_npcs.attempt_pursuit_after_flee(
                mobile_key, self.character.id, destination, random.Random()
            )

        self.database.set_character_room(self.character.id, destination)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed
        await self.send(f"Slipstep finds the gap. You flee {direction}!\r\n\r\n")
        await self.show_current_room()

        if movement is not None:
            if self.mobile_npc_movement_callback is not None:
                await self.mobile_npc_movement_callback(movement)
            await self.send(f"{enemy_name} follows your escape route!\r\n")
            await self.send_client_state()
            return

        await self._stop_combat()
        await self.send_client_state()
        await self.send(f"You lose {enemy_name} and escape combat.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()
        if normalized in {"racial", "racials", "race ability", "racial ability", "racial kit"}:
            await _show_racial(self)
            return

        race_key = self.character.race or ""
        is_racial, argument = _racial_command_payload(race_key, normalized)
        if is_racial:
            await _use_racial(self, argument)
            return

        if getattr(self, "_racial_stillness_active", False):
            informational = {
                "look", "l", "score", "stats", "health", "lore", "progress", "abilities",
                "quests", "inventory", "help", "?", "exits", "features", "weather", "time",
            }
            if normalized not in informational:
                _clear_stillness(self)
                await self.send("You move again, and Stillness releases you.\r\n")

        await _delegate_prompt(self, previous_playing_prompt, command)

    async def close(self) -> None:
        type(self)._racial_live_sessions.discard(self)
        for attr in (
            "_racial_adapt_task",
            "_racial_long_view_task",
            "_racial_bloodscent_task",
            "_racial_stillness_task",
            "_racial_bloom_task",
        ):
            task = getattr(self, attr, None)
            if task is not None and not task.done():
                task.cancel()
        if previous_close is not None:
            await previous_close(self)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class.attempt_flee = attempt_flee
    player_session_class.start_combat = start_combat
    player_session_class.start_mobile_npc_combat = start_mobile_npc_combat
    if previous_close is not None:
        player_session_class.close = close
    player_session_class._racial_ability_runtime_installed = True
