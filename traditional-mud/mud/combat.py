from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Hashable

from mud.mechanics import CombatantState, TAUNT_RULES


AutoAttackCallback = Callable[[CombatantState, CombatantState], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class FleeRules:
    """Rules for breaking out of real-time combat.

    The current base chance is intentionally centralized so it can be tuned
    without changing session/combat flow. A failed flee leaves the player in
    the room and combat continues.
    """

    base_success_chance: float = 0.70

    def succeeds(self, roll: float) -> bool:
        if not 0.0 <= roll <= 1.0:
            raise ValueError("Flee roll must be between 0 and 1.")
        return roll <= self.base_success_chance


FLEE_RULES = FleeRules()


@dataclass(slots=True)
class CombatPair:
    attacker: CombatantState
    target: CombatantState


class RealTimeCombatLoop:
    """Small real-time combat scheduler.

    It owns real-time scheduling. Character stat hooks, equipment AC checks,
    mana, and cooldown state live on CombatantState; enemies, death rules, and
    authored abilities are added as those systems are designed.
    """

    def __init__(self, tick_seconds: float = 0.1) -> None:
        self.tick_seconds = tick_seconds
        self._pairs: list[CombatPair] = []
        self._running = False

    def engage(self, attacker: CombatantState, target: CombatantState) -> None:
        if any(pair.attacker.character_id == attacker.character_id for pair in self._pairs):
            return
        attacker.next_auto_attack_at = monotonic()
        self._pairs.append(CombatPair(attacker=attacker, target=target))

    def disengage(self, attacker_character_id: int) -> None:
        self._pairs = [
            pair for pair in self._pairs if pair.attacker.character_id != attacker_character_id
        ]

    async def run(self, on_auto_attack: AutoAttackCallback) -> None:
        self._running = True
        try:
            while self._running:
                now = monotonic()
                for pair in tuple(self._pairs):
                    if pair.attacker.auto_attack_ready(now):
                        pair.attacker.consume_auto_attack(now)
                        await on_auto_attack(pair.attacker, pair.target)
                await asyncio.sleep(self.tick_seconds)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False


@dataclass(slots=True)
class EnemyHateList:
    """Minimal threat table used by tanking abilities such as Taunt."""

    threat: dict[Hashable, float] = field(default_factory=dict)

    def add_threat(self, actor_id: Hashable, amount: float) -> None:
        self.threat[actor_id] = self.threat.get(actor_id, 0.0) + max(0.0, amount)

    def top_target(self) -> Hashable | None:
        if not self.threat:
            return None
        return max(self.threat, key=self.threat.get)

    def taunt(self, actor_id: Hashable, character_level: int, roll: float) -> bool:
        """Attempt to move actor_id to the top of the enemy hate list.

        Taunt begins at 30% success and improves by level. The caller supplies
        a roll so tests stay deterministic.
        """
        if not 0.0 <= roll <= 1.0:
            raise ValueError("Taunt roll must be between 0 and 1.")
        if roll > TAUNT_RULES.success_chance(character_level):
            return False
        current_top = max(self.threat.values(), default=0.0)
        self.threat[actor_id] = current_top + 1.0
        return True


@dataclass(frozen=True, slots=True)
class EnemyDefinition:
    key: str
    name: str
    aliases: tuple[str, ...]
    description: str
    max_hp: int
    armor_class: int
    auto_attack_damage: int
    auto_attack_interval: float
    xp_reward: int
    retaliates: bool = True
    tutorial: bool = False

    def matches(self, text: str) -> bool:
        normalized = text.strip().lower()
        return normalized == self.name.lower() or normalized in self.aliases


@dataclass(slots=True)
class EnemyState:
    definition: EnemyDefinition
    current_hp: int | None = None
    hate: EnemyHateList = field(default_factory=EnemyHateList)

    def __post_init__(self) -> None:
        if self.current_hp is None:
            self.current_hp = self.definition.max_hp

    @property
    def alive(self) -> bool:
        return bool(self.current_hp and self.current_hp > 0)

    def take_damage(self, amount: int) -> int:
        amount = max(0, amount)
        assert self.current_hp is not None
        dealt = min(self.current_hp, amount)
        self.current_hp -= dealt
        return dealt


TRAINING_DUMMY = EnemyDefinition(
    key="training_dummy",
    name="Training Dummy",
    aliases=("dummy", "practice dummy", "training dummy"),
    description="a scarred wooden practice dummy mounted on a weighted base",
    max_hp=18,
    armor_class=0,
    auto_attack_damage=0,
    auto_attack_interval=999.0,
    xp_reward=0,
    retaliates=False,
    tutorial=True,
)

SEWER_RAT = EnemyDefinition(
    key="sewer_rat",
    name="Sewer Rat",
    aliases=("rat", "sewer rat"),
    description="an oversized city rat with wet fur and yellow teeth",
    # Production-alpha pacing: trim the first real fight slightly rather than
    # increasing its repeatable reward. The Vermin Pens should teach combat,
    # not become the most efficient place to spend the first hour.
    max_hp=18,
    armor_class=3,
    auto_attack_damage=2,
    auto_attack_interval=3.4,
    xp_reward=15,
    retaliates=True,
    tutorial=True,
)

SMALL_IMP = EnemyDefinition(
    key="small_imp",
    name="Small Imp",
    aliases=("imp", "small imp"),
    description="a knee-high horned imp with ember-bright eyes and a mean little grin",
    # Same principle as the rat: a modest time-to-kill reduction and a little
    # more reaction room, while preserving the existing 20 XP so grinding this
    # cage does not overtake authored quest progression.
    max_hp=24,
    armor_class=5,
    auto_attack_damage=3,
    auto_attack_interval=3.2,
    xp_reward=20,
    retaliates=True,
    tutorial=True,
)

ENEMIES: tuple[EnemyDefinition, ...] = (TRAINING_DUMMY, SEWER_RAT, SMALL_IMP)
ENEMIES_BY_KEY = {enemy.key: enemy for enemy in ENEMIES}
