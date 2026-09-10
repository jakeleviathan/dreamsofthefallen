from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatDefinition:
    key: str
    name: str
    description: str


# The player-facing attribute names chosen for Astralis. They intentionally
# perform familiar RPG jobs while avoiding the standard STR/DEX/INT labels.
STATS: tuple[StatDefinition, ...] = (
    StatDefinition("might", "Might", "Adds directly to normal auto-attack damage."),
    StatDefinition("grace", "Grace", "Increases auto-attack speed."),
    StatDefinition("love", "Love", "Adds directly to healing done and also contributes to maximum mana."),
    StatDefinition("mind", "Mind", "Adds directly to spell damage and also contributes to maximum mana."),
    StatDefinition("hp", "HP", "Adds raw hit points directly to maximum HP."),
)
STATS_BY_KEY = {stat.key: stat for stat in STATS}
STAT_KEYS = tuple(stat.key for stat in STATS)


@dataclass(frozen=True, slots=True)
class CharacterStats:
    might: int = 0
    grace: int = 0
    love: int = 0
    mind: int = 0
    hp: int = 0

    @property
    def mana_bonus(self) -> int:
        return self.love + self.mind

    def auto_attack_damage(self, base_damage: int) -> int:
        return max(0, base_damage + self.might)

    def healing_amount(self, base_healing: int) -> int:
        return max(0, base_healing + self.love)

    def spell_damage(self, base_damage: int) -> int:
        return max(0, base_damage + self.mind)

    def maximum_hp(self, base_max_hp: int) -> int:
        return max(1, base_max_hp + self.hp)

    def maximum_mana(self, base_max_mana: int) -> int:
        return max(0, base_max_mana + self.mana_bonus)

    def plus(self, other: "CharacterStats") -> "CharacterStats":
        return CharacterStats(
            might=self.might + other.might,
            grace=self.grace + other.grace,
            love=self.love + other.love,
            mind=self.mind + other.mind,
            hp=self.hp + other.hp,
        )

    def with_added_point(self, stat_key: str, amount: int = 1) -> "CharacterStats":
        if stat_key not in STAT_KEYS:
            raise KeyError(stat_key)
        if amount < 0:
            raise ValueError("Stat allocation cannot be negative.")
        values = self.as_dict()
        values[stat_key] += amount
        return CharacterStats(**values)

    def as_dict(self) -> dict[str, int]:
        return {
            "might": self.might,
            "grace": self.grace,
            "love": self.love,
            "mind": self.mind,
            "hp": self.hp,
        }


@dataclass(frozen=True, slots=True)
class StartingStatRules:
    """Hybrid race + class + player-allocation character creation.

    The structure is locked. The exact numbers below are deliberately centralized
    development tuning values because we have not balanced starting attributes yet.
    """

    base_stat_value: int = 5
    discretionary_points: int = 5


STARTING_STAT_RULES = StartingStatRules()

# Racial starting modifiers are added after the class baseline. Approved Brute
# stat-pass modifiers currently include: Dwarf +2 Might/+3 HP; Forest Elf +2
# Grace/+2 Love; Goblin -1 Might/+2 Grace; Troll +3 Might/+3 HP/-1 Grace;
# Human no modifier; Moon Elf -2 Might/+2 Grace/+2 Mind; Sporekin -1 Might/+2 Love/+2 Mind.
# Undead remains earlier provisional tuning until we walk through it.
RACE_STARTING_MODIFIERS: dict[str, CharacterStats] = {
    "human": CharacterStats(),
    "forest_elf": CharacterStats(grace=2, love=2),
    "moon_elf": CharacterStats(might=-2, grace=2, mind=2),
    "dwarf": CharacterStats(might=2, hp=3),
    "goblin": CharacterStats(might=-1, grace=2),
    "troll": CharacterStats(might=3, grace=-1, hp=3),
    "undead": CharacterStats(hp=1),
    "sporekin": CharacterStats(might=-1, love=2, mind=2),
}

# Explicit class baselines let us tune each class as a real archetype instead of
# forcing every class to start from the same five-point template. Brute is the
# first class whose complete baseline has been approved.
CLASS_STARTING_BASELINES: dict[str, CharacterStats] = {
    "brute": CharacterStats(might=10, grace=6, love=5, mind=5, hp=15),
}

# Classes we have not walked through numerically yet keep the earlier provisional
# nudges on top of the generic base value.
CLASS_STARTING_MODIFIERS: dict[str, CharacterStats] = {
    "wizard": CharacterStats(mind=2, love=1),
    "druid": CharacterStats(love=1, mind=1, hp=1),
    "priest": CharacterStats(love=2, mind=1),
    "necromancer": CharacterStats(mind=2, hp=1),
}


def starting_stat_baseline(race_key: str, class_key: str) -> CharacterStats:
    class_base = CLASS_STARTING_BASELINES.get(class_key)
    if class_base is None:
        class_base = CharacterStats(**{key: STARTING_STAT_RULES.base_stat_value for key in STAT_KEYS})
        class_base = class_base.plus(CLASS_STARTING_MODIFIERS.get(class_key, CharacterStats()))
    return class_base.plus(RACE_STARTING_MODIFIERS.get(race_key, CharacterStats()))


def build_starting_stats(
    race_key: str,
    class_key: str,
    allocation: CharacterStats,
) -> CharacterStats:
    values = allocation.as_dict()
    if any(value < 0 for value in values.values()):
        raise ValueError("Allocated stat points cannot be negative.")
    if sum(values.values()) != STARTING_STAT_RULES.discretionary_points:
        raise ValueError(
            f"Exactly {STARTING_STAT_RULES.discretionary_points} discretionary points must be allocated."
        )
    return starting_stat_baseline(race_key, class_key).plus(allocation)


@dataclass(frozen=True, slots=True)
class EquipmentItem:
    """Old-school equipment model: raw stats first, with authored restrictions and rare effects."""

    name: str
    slot: str
    armor_class: int = 0
    stat_bonuses: CharacterStats = CharacterStats()
    scripted_effects: tuple[str, ...] = ()
    allowed_races: frozenset[str] = frozenset()
    allowed_classes: frozenset[str] = frozenset()

    @property
    def is_special(self) -> bool:
        return bool(self.scripted_effects)

    @property
    def is_universal(self) -> bool:
        return not self.allowed_races and not self.allowed_classes

    def can_equip(self, *, race_key: str, class_key: str) -> bool:
        if self.allowed_races and race_key not in self.allowed_races:
            return False
        if self.allowed_classes and class_key not in self.allowed_classes:
            return False
        return True


@dataclass(frozen=True, slots=True)
class EquipmentDesignRules:
    ordinary_items_focus_on_raw_stats: bool = True
    scripted_effects_are_rare_or_special: bool = True
    armor_class_is_equipment_derived: bool = True
    universal_equipment_exists: bool = True
    race_restricted_equipment_exists: bool = True
    class_restricted_equipment_exists: bool = True


EQUIPMENT_DESIGN_RULES = EquipmentDesignRules()

# Every character begins with one simple weapon. Its final in-world name,
# damage profile, and weapon type can be chosen when the item/combat catalog is
# authored; the persistent inventory key is already stable.
STARTER_WEAPON = EquipmentItem(
    name="Basic Starting Weapon",
    slot="weapon",
)

# The approved Brute baseline includes AC 8. AC remains equipment-derived, so
# this is represented as the Brute's starting training armor rather than an
# innate character stat.
BRUTE_STARTER_ARMOR = EquipmentItem(
    name="Brute Training Harness",
    slot="body",
    armor_class=8,
    allowed_classes=frozenset({"brute"}),
)
STARTER_ARMOR_BY_CLASS: dict[str, EquipmentItem] = {
    "brute": BRUTE_STARTER_ARMOR,
}


def starting_armor_class(class_key: str) -> int:
    armor = STARTER_ARMOR_BY_CLASS.get(class_key)
    return 0 if armor is None else max(0, armor.armor_class)


def total_armor_class(equipped_items: tuple[EquipmentItem, ...] | list[EquipmentItem]) -> int:
    return sum(max(0, item.armor_class) for item in equipped_items)


def total_equipment_stat_bonuses(
    equipped_items: tuple[EquipmentItem, ...] | list[EquipmentItem],
) -> CharacterStats:
    total = CharacterStats()
    for item in equipped_items:
        total = total.plus(item.stat_bonuses)
    return total


@dataclass(frozen=True, slots=True)
class StatCombatTuning:
    # Provisional: one Grace point currently means +1% auto-attack speed.
    grace_attack_speed_percent_per_point: float = 0.01
    minimum_auto_attack_interval: float = 0.25

    def auto_attack_interval(self, base_interval: float, grace: int) -> float:
        speed_multiplier = 1.0 + max(0, grace) * self.grace_attack_speed_percent_per_point
        return max(self.minimum_auto_attack_interval, base_interval / speed_multiplier)


STAT_COMBAT_TUNING = StatCombatTuning()
