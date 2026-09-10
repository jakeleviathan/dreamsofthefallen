from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.stats import CharacterStats, STAT_COMBAT_TUNING


@dataclass(frozen=True, slots=True)
class ProgressionRules:
    """Character levels use XP; abilities improve through use.

    Early levels are intentionally fast, levels 6-10 remain brisk, and the curve
    becomes noticeably steeper after level 10. Exact numbers are development
    tuning and are centralized in xp_to_next_level().
    """

    character_level_source: str = "experience_points"
    ability_progression_source: str = "use_based"
    early_fast_leveling_through: int = 10
    steepening_begins_after: int = 10
    every_class_can_solo_to_end_level: bool = True
    fast_learner_multiplier: float | None = None

    def xp_to_next_level(self, level: int) -> int:
        level = max(1, level)
        if level <= 5:
            return 100 + (level - 1) * 50
        if level <= 10:
            return 400 + (level - 6) * 100
        post_ten = level - 10
        return 900 + (post_ten * post_ten * 175)

    def cumulative_xp_for_level(self, level: int) -> int:
        if level <= 1:
            return 0
        return sum(self.xp_to_next_level(current) for current in range(1, level))

    def level_for_experience(self, experience: int) -> int:
        experience = max(0, experience)
        level = 1
        spent = 0
        while True:
            needed = self.xp_to_next_level(level)
            if spent + needed > experience:
                return level
            spent += needed
            level += 1


PROGRESSION_RULES = ProgressionRules()


@dataclass(frozen=True, slots=True)
class DeathRules:
    """Provisional death tuning for Dreams of the Fallen.

    Death loses a fraction of XP earned within the current level, but does not
    de-level the character. Bind travel is handled separately by the session.
    """

    experience_loss_fraction: float = 0.10
    allow_level_loss: bool = False

    def experience_loss(self, level: int, experience: int) -> tuple[int, int]:
        level = max(1, level)
        experience = max(0, experience)
        level_floor = PROGRESSION_RULES.cumulative_xp_for_level(level)
        progress = max(0, experience - level_floor)
        if progress <= 0:
            return 0, level_floor
        loss = max(1, int(progress * self.experience_loss_fraction))
        return min(loss, progress), level_floor


DEATH_RULES = DeathRules()


@dataclass(frozen=True, slots=True)
class AbilityDefinition:
    key: str
    name: str
    unlock_level: int | None = None
    mana_cost: int | None = None
    cooldown_seconds: float | None = None
    description: str = ""
    category: str = "active"
    catalyst_item_key: str | None = None
    catalyst_quantity: int = 0
    skill_improves_effectiveness: bool = True
    design_status: str = "locked_identity_tuning_pending"


# Class ability identities are fixed rather than selected from a shared talent
# pool. Mana costs, cooldown lengths, exact damage/healing values, and most
# high-level spell names remain tuning/design work for later.
FIXED_CLASS_ABILITIES: dict[str, tuple[AbilityDefinition, ...]] = {
    "brute": (
        AbilityDefinition(
            key="taunt",
            name="Taunt",
            unlock_level=1,
            mana_cost=10,
            cooldown_seconds=5.0,
            description=(
                "Attempts to force the Brute to the top of an enemy's hate list. "
                "Starts at a 30% success chance and becomes more reliable as the Brute levels."
            ),
            category="threat",
            skill_improves_effectiveness=False,
            design_status="approved_initial_tuning",
        ),
        AbilityDefinition(
            key="heavy_strike",
            name="Heavy Strike",
            unlock_level=2,
            description="An early high-impact physical weapon attack.",
            category="physical_attack",
        ),
    ),
    "wizard": (
        AbilityDefinition(
            key="coldfire_burst",
            name="Coldfire Burst",
            unlock_level=1,
            description="A simple burst of cold fire that deals direct spell damage.",
            category="spell_damage",
        ),
        AbilityDefinition(
            key="minor_barrier",
            name="Minor Barrier",
            unlock_level=2,
            description="A small magical protection spell for the Wizard.",
            category="self_protection",
        ),
        AbilityDefinition(
            key="arcane_bolt",
            name="Arcane Bolt",
            unlock_level=3,
            description="A stronger early direct-damage arcane spell.",
            category="spell_damage",
        ),
    ),
    "druid": (
        AbilityDefinition(
            key="forage",
            name="Forage",
            unlock_level=1,
            mana_cost=0,
            cooldown_seconds=0.0,
            description="Searches suitable natural terrain for useful natural materials.",
            category="class_passive_utility",
            design_status="locked_foundation",
        ),
        AbilityDefinition(
            key="minor_heal",
            name="Minor Heal",
            unlock_level=1,
            description="A basic restorative spell usable from the beginning of a Druid's career.",
            category="healing",
        ),
        AbilityDefinition(
            key="hp_buff",
            name="HP Buff",
            unlock_level=2,
            description="Raises maximum HP and can be cast on the Druid or another character.",
            category="ally_buff",
        ),
    ),
    # Priest abilities branch through the character's chosen deity path.
    # The deity-specific lists live below so a Priest only sees abilities from
    # the god they actually worship.
    "priest": (),
    "necromancer": (
        AbilityDefinition(
            key="minor_life_tap",
            name="Minor Life Tap",
            unlock_level=1,
            mana_cost=5,
            cooldown_seconds=4.0,
            description=(
                "Tears a small measure of life from an enemy, dealing spell damage and "
                "restoring the same amount of health to the Necromancer."
            ),
            category="life_drain",
            design_status="approved_initial_tuning",
        ),
        AbilityDefinition(
            key="raise_skeleton",
            name="Raise Skeleton",
            unlock_level=2,
            mana_cost=0,
            cooldown_seconds=3.0,
            description="Consumes Bone Chips from inventory to raise a persistent combat Skeleton pet.",
            category="pet_summon",
            catalyst_item_key="bone_chips",
            catalyst_quantity=1,
            design_status="approved_identity_tuning_pending",
        ),
        AbilityDefinition(
            key="rot",
            name="Rot",
            unlock_level=3,
            mana_cost=6,
            cooldown_seconds=6.0,
            description="Afflicts an enemy with a minor necromantic damage-over-time effect.",
            category="damage_over_time",
            design_status="approved_initial_tuning",
        ),
    ),
}


def class_ability_is_legal(
    class_key: str,
    ability_key: str,
    level: int | None = None,
    deity_key: str | None = None,
) -> bool:
    abilities = (
        priest_abilities_for_level(deity_key, level)
        if class_key == "priest" and deity_key is not None and level is not None
        else PRIEST_DEITY_ABILITIES.get(deity_key or "", ())
        if class_key == "priest" and deity_key is not None
        else FIXED_CLASS_ABILITIES.get(class_key, ())
    )
    for ability in abilities:
        if ability.key != ability_key:
            continue
        if level is None or ability.unlock_level is None:
            return True
        return level >= ability.unlock_level
    return False


def class_abilities_for_level(
    class_key: str,
    level: int,
    deity_key: str | None = None,
) -> tuple[AbilityDefinition, ...]:
    if class_key == "priest":
        return priest_abilities_for_level(deity_key, level)
    return tuple(
        ability
        for ability in FIXED_CLASS_ABILITIES.get(class_key, ())
        if ability.unlock_level is None or level >= ability.unlock_level
    )


@dataclass(frozen=True, slots=True)
class PriestDeityDefinition:
    key: str
    name: str
    domain: str
    description: str
    starter_ability: AbilityDefinition
    progression_identity: str


PRIEST_DEITIES: tuple[PriestDeityDefinition, ...] = (
    PriestDeityDefinition(
        key="zerjz",
        name="Zerjz",
        domain="healing",
        description="The Priest path of healing and restoration.",
        starter_ability=AbilityDefinition(
            key="restoring_light",
            name="Restoring Light",
            unlock_level=1,
            description="A basic targeted healing spell granted to Priests of Zerjz.",
            category="healing",
        ),
        progression_identity=(
            "Unlocks an authored progression of increasingly powerful healing and restorative spells as the Priest levels."
        ),
    ),
    PriestDeityDefinition(
        key="tenebrous",
        name="Tenebrous",
        domain="protection",
        description="The Priest path of protection, wards, and defensive magic.",
        starter_ability=AbilityDefinition(
            key="guardian_ward",
            name="Guardian Ward",
            unlock_level=1,
            description="A basic defensive ward granted to Priests of Tenebrous.",
            category="protection",
        ),
        progression_identity=(
            "Unlocks an authored progression of increasingly powerful protection, HP, AC, and defensive-support spells as the Priest levels."
        ),
    ),
    PriestDeityDefinition(
        key="leviathan",
        name="Leviathan",
        domain="vengeance",
        description="The Priest path of vengeance and retributive divine damage.",
        starter_ability=AbilityDefinition(
            key="judgment_bolt",
            name="Judgment Bolt",
            unlock_level=1,
            description="A basic retributive damage spell granted to Priests of Leviathan.",
            category="divine_damage",
        ),
        progression_identity=(
            "Unlocks an authored progression of increasingly powerful vengeance and judgment spells as the Priest levels."
        ),
    ),
)
PRIEST_DEITIES_BY_KEY = {deity.key: deity for deity in PRIEST_DEITIES}
PRIEST_DEITY_ABILITIES: dict[str, tuple[AbilityDefinition, ...]] = {
    deity.key: (deity.starter_ability,) for deity in PRIEST_DEITIES
}


def priest_abilities_for_level(
    deity_key: str | None, level: int
) -> tuple[AbilityDefinition, ...]:
    if deity_key is None:
        return ()
    return tuple(
        ability
        for ability in PRIEST_DEITY_ABILITIES.get(deity_key, ())
        if ability.unlock_level is None or level >= ability.unlock_level
    )


@dataclass(frozen=True, slots=True)
class PriestDeityRules:
    deity_choice_defines_spell_path: bool = True
    deity_choice_is_part_of_class_identity: bool = True
    deity_roster_authored: bool = True
    each_path_has_distinct_progression: bool = True
    path_progression_is_fixed_not_player_selected: bool = True


PRIEST_DEITY_RULES = PriestDeityRules()


@dataclass(frozen=True, slots=True)
class StarterKitRules:
    every_character_receives_basic_weapon: bool = True
    basic_weapon_key: str = "starter_weapon"
    brute_begins_with_solid_weapon_skill: bool = True


STARTER_KIT_RULES = StarterKitRules()


@dataclass(frozen=True, slots=True)
class EndgameClassRules:
    brute_primary_tank: bool = True
    brute_gear_and_weapons_critical: bool = True
    wizard_single_target_nuke_specialist: bool = True
    wizard_world_teleportation: bool = True
    wizard_self_protection_not_party_buffing: bool = True
    priest_prime_healer: bool = True
    priest_resurrects_allies: bool = True
    priest_hp_and_ac_buffs: bool = True
    priest_heavy_plate: bool = True
    necromancer_powerful_undead_pet: bool = True
    necromancer_lich_like_form: bool = True
    necromancer_dot_specialist: bool = True
    druid_reliable_secondary_healer: bool = True
    druid_shapeshifting: bool = False


ENDGAME_CLASS_RULES = EndgameClassRules()


@dataclass(frozen=True, slots=True)
class TauntRules:
    """Approved first-pass tuning for the Brute's level-1 hate-control ability."""

    base_success_chance: float = 0.30
    success_chance_per_level: float = 0.02
    maximum_success_chance: float = 0.95
    mana_cost: int = 10
    cooldown_seconds: float = 5.0

    def success_chance(self, character_level: int) -> float:
        level = max(1, character_level)
        chance = self.base_success_chance + (level - 1) * self.success_chance_per_level
        return min(self.maximum_success_chance, chance)


TAUNT_RULES = TauntRules()


@dataclass(frozen=True, slots=True)
class ClassAbilityRules:
    player_selects_class_abilities: bool = False
    ability_sets_are_fixed_by_class: bool = True
    abilities_unlock_through_progression: bool = True
    abilities_improve_through_use: bool = True


CLASS_ABILITY_RULES = ClassAbilityRules()


@dataclass(slots=True)
class AbilityState:
    key: str
    mana_cost: int
    cooldown_seconds: float
    uses: int = 0
    skill_xp: int = 0
    last_used_at: float | None = None

    def cooldown_remaining(self, now: float | None = None) -> float:
        if self.last_used_at is None:
            return 0.0
        current = monotonic() if now is None else now
        return max(0.0, self.cooldown_seconds - (current - self.last_used_at))

    def is_ready(self, now: float | None = None) -> bool:
        return self.cooldown_remaining(now) <= 0.0

    def record_use(self, skill_xp_gain: int = 1, now: float | None = None) -> None:
        self.uses += 1
        self.skill_xp += max(0, skill_xp_gain)
        self.last_used_at = monotonic() if now is None else now


@dataclass(slots=True)
class CombatantState:
    character_id: int
    race_key: str
    current_hp: int
    max_hp: int
    current_mana: int
    max_mana: int
    auto_attack_interval: float
    # Movement is exposed to capable MUD clients now. Its gameplay costs are
    # intentionally left untuned until the movement/fatigue system is designed.
    current_movement: int = 100
    max_movement: int = 100
    stats: CharacterStats = field(default_factory=CharacterStats)
    armor_class: int = 0
    next_auto_attack_at: float = field(default_factory=monotonic)
    cooldowns: dict[str, float] = field(default_factory=dict)

    def apply_normal_regeneration(self, base_hp_gain: int) -> int:
        race = RACES_BY_KEY.get(self.race_key)
        racial_bonus = race.regen_bonus_per_tick if race else 0
        amount = max(0, base_hp_gain + racial_bonus)
        before = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - before

    def spend_mana(self, amount: int) -> bool:
        if amount < 0:
            raise ValueError("Mana cost cannot be negative.")
        if self.current_mana < amount:
            return False
        self.current_mana -= amount
        return True

    def is_hit_by(self, attack_roll: int) -> bool:
        return attack_roll >= max(0, self.armor_class)

    def ability_ready(self, ability_key: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        return current >= self.cooldowns.get(ability_key, 0.0)

    def start_cooldown(self, ability_key: str, cooldown_seconds: float, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        self.cooldowns[ability_key] = current + max(0.0, cooldown_seconds)

    def auto_attack_damage(self, base_damage: int) -> int:
        return self.stats.auto_attack_damage(base_damage)

    def healing_amount(self, base_healing: int) -> int:
        return self.stats.healing_amount(base_healing)

    def spell_damage(self, base_damage: int) -> int:
        return self.stats.spell_damage(base_damage)

    def effective_max_hp(self, base_max_hp: int) -> int:
        return self.stats.maximum_hp(base_max_hp)

    def effective_max_mana(self, base_max_mana: int) -> int:
        return self.stats.maximum_mana(base_max_mana)

    def effective_auto_attack_interval(self) -> float:
        return STAT_COMBAT_TUNING.auto_attack_interval(self.auto_attack_interval, self.stats.grace)

    def auto_attack_ready(self, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        return current >= self.next_auto_attack_at

    def consume_auto_attack(self, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        self.next_auto_attack_at = current + self.effective_auto_attack_interval()


@dataclass(frozen=True, slots=True)
class CombatRules:
    mode: str = "real_time"
    baseline_attack_behavior: str = "automatic"
    active_abilities_during_auto_attack: bool = True
    abilities_use_mana_like_resource: bool = True
    abilities_use_cooldowns: bool = True
    might_increases_auto_attack_damage: bool = True
    grace_increases_auto_attack_speed: bool = True
    love_increases_healing: bool = True
    mind_increases_spell_damage: bool = True
    love_and_mind_increase_mana: bool = True
    hp_stat_adds_raw_max_hp: bool = True
    hit_resolution_uses_equipment_armor_class: bool = True


COMBAT_RULES = CombatRules()
