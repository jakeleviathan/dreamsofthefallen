from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from mud.mechanics import CombatantState
from mud.world import HUMAN_TRAINING_YARD_KEY


@dataclass(frozen=True, slots=True)
class DamageDice:
    """Small old-school damage profile used by physical weapons.

    The profile is deliberately data rather than a hard-coded random percentage so
    future weapons can feel meaningfully different while Might remains a direct,
    predictable bonus on top of the weapon roll.
    """

    count: int
    sides: int
    bonus: int = 0

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("Damage dice count must be positive.")
        if self.sides <= 0:
            raise ValueError("Damage die sides must be positive.")

    @property
    def minimum(self) -> int:
        return self.count + self.bonus

    @property
    def maximum(self) -> int:
        return self.count * self.sides + self.bonus

    @property
    def average(self) -> float:
        return self.count * (self.sides + 1) / 2 + self.bonus

    @property
    def notation(self) -> str:
        suffix = ""
        if self.bonus > 0:
            suffix = f"+{self.bonus}"
        elif self.bonus < 0:
            suffix = str(self.bonus)
        return f"{self.count}d{self.sides}{suffix}"

    def roll(self, rng=None) -> int:
        rng = rng or random
        return max(0, sum(rng.randint(1, self.sides) for _ in range(self.count)) + self.bonus)


# Weapon families. The basic 1d3 profile averages exactly 2 damage, preserving
# the old fixed base damage of 2 while making ordinary swings vary naturally.
BASIC_WEAPON_DAMAGE = DamageDice(1, 3)
DAGGER_DAMAGE = DamageDice(1, 4)
SWORD_DAMAGE = DamageDice(1, 6)
SPEAR_DAMAGE = DamageDice(1, 6)
HEAVY_AXE_DAMAGE = DamageDice(1, 8)
TWO_HANDED_DAMAGE = DamageDice(1, 10)


# Explicit profiles win over name inference. New authored weapons can register
# here (or call register_weapon_damage) without changing the combat loop.
WEAPON_DAMAGE_PROFILES: dict[str, DamageDice] = {
    "starter_weapon": BASIC_WEAPON_DAMAGE,
    "human_blackwall_drill_blade": SWORD_DAMAGE,
    "goblin_patchwork_scrapknife": DAGGER_DAMAGE,
    "frostroot_notched_spear": SPEAR_DAMAGE,
}

_VARIANCE_MARKER = "__combat_damage_variance__"
_WEAPON_DAMAGE_BY_CHARACTER: dict[int, DamageDice] = {}


def register_weapon_damage(item_key: str, profile: DamageDice) -> None:
    if not item_key:
        raise ValueError("Weapon item key cannot be empty.")
    WEAPON_DAMAGE_PROFILES[item_key] = profile


def weapon_damage_for_item(item_key: str, definition=None) -> DamageDice:
    """Resolve an authored weapon profile, with conservative family inference.

    Explicit item-key data is authoritative. Inference gives the existing broad
    item catalog sensible behavior immediately while still falling back to the
    balance-preserving 1d3 profile for unfamiliar main-hand items.
    """

    explicit = WEAPON_DAMAGE_PROFILES.get(item_key)
    if explicit is not None:
        return explicit

    if definition is None:
        try:
            import mud.crafting as crafting

            definition = crafting.ITEMS_BY_KEY.get(item_key)
        except Exception:
            definition = None

    name = str(getattr(definition, "name", "") or item_key).lower().replace("-", " ")

    if any(
        phrase in name
        for phrase in (
            "greatsword",
            "great sword",
            "greataxe",
            "great axe",
            "warhammer",
            "war hammer",
            "maul",
            "two handed",
            "two-handed",
        )
    ):
        return TWO_HANDED_DAMAGE
    if "axe" in name:
        return HEAVY_AXE_DAMAGE
    if any(word in name for word in ("dagger", "knife", "dirk", "shiv")):
        return DAGGER_DAMAGE
    if "spear" in name:
        return SPEAR_DAMAGE
    if any(word in name for word in ("sword", "blade", "sabre", "saber", "rapier")):
        return SWORD_DAMAGE
    return BASIC_WEAPON_DAMAGE


def roll_enemy_attack_damage(base_damage: int, rng=None) -> int:
    """Roll enemy damage around its authored center without moving the average.

    A base of N becomes N-1..N+1. For a 1-damage creature this intentionally
    allows a 0-damage glancing hit so its mathematical average remains 1 rather
    than quietly buffing the weakest starter enemies.
    """

    base = max(0, int(base_damage))
    if base == 0:
        return 0
    rng = rng or random
    return rng.randint(max(0, base - 1), base + 1)


def roll_spell_base_damage(base_damage: int, rng=None) -> int:
    """Give damaging spells a restrained +/-1 base roll.

    Mind is added after this roll, so caster stats stay dependable and most of a
    spell's power remains predictable instead of becoming casino-like.
    """

    base = max(0, int(base_damage))
    if base == 0:
        return 0
    rng = rng or random
    return rng.randint(max(0, base - 1), base + 1)


def roll_player_weapon_damage(might: int, profile: DamageDice, rng=None) -> int:
    return max(0, profile.roll(rng) + int(might))


def _weapon_profile_for_session(session) -> DamageDice:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return BASIC_WEAPON_DAMAGE

    try:
        import mud.equipment_system as equipment

        equipped = equipment.equipped_definitions(database, character.id)
        main_hand = equipped.get("main_hand")
        if main_hand is None:
            return BASIC_WEAPON_DAMAGE
        return weapon_damage_for_item(main_hand.key, main_hand)
    except Exception:
        # Combat should remain playable if a development database has stale gear.
        return BASIC_WEAPON_DAMAGE


def _enable_session_combatant(session) -> None:
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return
    combatant.cooldowns[_VARIANCE_MARKER] = 0.0
    _WEAPON_DAMAGE_BY_CHARACTER[combatant.character_id] = _weapon_profile_for_session(session)


def _install_combatant_damage_methods() -> None:
    if getattr(CombatantState, "_combat_damage_variance_installed", False):
        return

    original_auto_attack_damage = CombatantState.auto_attack_damage
    original_spell_damage = CombatantState.spell_damage

    def auto_attack_damage(self, base_damage: int) -> int:
        if _VARIANCE_MARKER not in self.cooldowns:
            return original_auto_attack_damage(self, base_damage)
        profile = _WEAPON_DAMAGE_BY_CHARACTER.get(self.character_id, BASIC_WEAPON_DAMAGE)
        return roll_player_weapon_damage(self.stats.might, profile)

    def spell_damage(self, base_damage: int) -> int:
        if _VARIANCE_MARKER not in self.cooldowns:
            return original_spell_damage(self, base_damage)
        rolled_base = roll_spell_base_damage(base_damage)
        return self.stats.spell_damage(rolled_base)

    CombatantState.auto_attack_damage = auto_attack_damage
    CombatantState.spell_damage = spell_damage
    CombatantState._combat_damage_variance_installed = True


def _install_equipment_damage_sync() -> None:
    try:
        import mud.equipment_system as equipment
    except Exception:
        return

    if getattr(equipment, "_combat_damage_variance_sync_installed", False):
        return

    original_apply = equipment.apply_equipment_to_combatant

    def apply_equipment_to_combatant(session) -> None:
        original_apply(session)
        _enable_session_combatant(session)

    equipment.apply_equipment_to_combatant = apply_equipment_to_combatant
    equipment._combat_damage_variance_sync_installed = True


def install_combat_variance_runtime(player_session_class) -> None:
    """Install production damage rolls without disturbing isolated foundation tests.

    Player physical damage and spell damage are enabled only on live combatants
    marked by the production session runtime. CharacterStats remains deterministic
    as the underlying stat formula, which keeps design calculations and tooling
    stable. Enemy retaliation is handled here because the legacy session loop used
    the authored enemy integer directly.
    """

    if getattr(player_session_class, "_combat_damage_variance_runtime_installed", False):
        return

    _install_combatant_damage_methods()
    _install_equipment_damage_sync()

    previous_enter_character = player_session_class.enter_character

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        _enable_session_combatant(self)

    player_session_class.enter_character = enter_character

    previous_combat_loop = getattr(player_session_class, "_combat_loop", None)
    if callable(previous_combat_loop):

        async def _combat_loop(self, enemy) -> None:
            assert self.character is not None and self.combatant is not None
            loop = asyncio.get_running_loop()
            next_enemy_attack = loop.time() + enemy.definition.auto_attack_interval
            playing_state = getattr(type(self.state), "PLAYING", None)
            try:
                while self.state is playing_state and self.active_enemy is enemy and enemy.alive:
                    now = loop.time()
                    if self.combatant.auto_attack_ready(now):
                        self.combatant.consume_auto_attack(now)
                        attack_roll = random.randint(1, 20)
                        if attack_roll >= enemy.definition.armor_class:
                            # The legacy base argument remains for compatibility;
                            # a marked live combatant now rolls its equipped weapon.
                            damage = self.combatant.auto_attack_damage(2)
                            dealt = enemy.take_damage(damage)
                            await self.send(
                                f"\r\nYou strike {enemy.definition.name} for {dealt} damage "
                                f"({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
                            )
                            await self.send_client_state()
                            if not enemy.alive:
                                await self._finish_enemy_defeat(enemy)
                                return
                        else:
                            await self.send(f"\r\nYour attack misses {enemy.definition.name}.\r\n")

                    if enemy.definition.retaliates and now >= next_enemy_attack and enemy.alive:
                        damage = roll_enemy_attack_damage(enemy.definition.auto_attack_damage)
                        if now < self.ward_until and damage > 0:
                            damage = max(1, damage // 2)
                        self.combatant.current_hp = max(0, self.combatant.current_hp - damage)
                        if damage > 0:
                            await self.send(
                                f"\r\n{enemy.definition.name} hits you for {damage} damage "
                                f"({self.combatant.current_hp}/{self.combatant.max_hp} HP).\r\n"
                            )
                        else:
                            await self.send(
                                f"\r\n{enemy.definition.name} catches you with a glancing blow "
                                f"but deals no damage ({self.combatant.current_hp}/{self.combatant.max_hp} HP).\r\n"
                            )
                        await self.send_client_state()
                        next_enemy_attack = now + enemy.definition.auto_attack_interval
                        if self.combatant.current_hp <= 0:
                            if enemy.definition.tutorial:
                                recovery_room = HUMAN_TRAINING_YARD_KEY
                                await self.send(
                                    "\r\nA training guard drags you clear before the creature can finish the job. "
                                    "You recover in the Training Yard.\r\n"
                                )
                            else:
                                await self._handle_character_death(enemy.definition.name)
                                return
                            self.combatant.current_hp = self.combatant.max_hp
                            self.combatant.current_mana = self.combatant.max_mana
                            self.database.set_character_room(self.character.id, recovery_room)
                            refreshed = self.database.get_character_by_name(self.character.name)
                            if refreshed is not None:
                                self.character = refreshed
                            await self._stop_combat()
                            return
                    await asyncio.sleep(0.15)
            except asyncio.CancelledError:
                return

        player_session_class._combat_loop = _combat_loop

    player_session_class._combat_damage_variance_runtime_installed = True
