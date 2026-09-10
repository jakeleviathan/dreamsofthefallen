from __future__ import annotations

from dataclasses import dataclass

from mud.stats import CharacterStats, EquipmentItem


ACQUISITION_METHODS = ("crafting", "drop", "quest")


@dataclass(frozen=True, slots=True)
class GearAcquisitionRules:
    crafting_enabled: bool = True
    enemy_drops_enabled: bool = True
    quest_rewards_enabled: bool = True
    some_items_are_primarily_crafted: bool = True
    some_items_are_primarily_dropped: bool = True
    named_enemies_can_have_unique_high_stat_drops: bool = True
    high_skill_crafters_can_make_very_good_equipment: bool = True
    ordinary_enemies_need_not_share_named_enemy_loot: bool = True


GEAR_ACQUISITION_RULES = GearAcquisitionRules()


@dataclass(frozen=True, slots=True)
class GearSource:
    """Where an authored equipment item normally comes from."""

    primary_method: str
    source_key: str | None = None
    source_name: str | None = None

    def __post_init__(self) -> None:
        if self.primary_method not in ACQUISITION_METHODS:
            raise ValueError(f"Unsupported gear acquisition method: {self.primary_method}")


@dataclass(frozen=True, slots=True)
class NamedEnemyLootEntry:
    """A special item attached to an authored named enemy's loot table."""

    enemy_key: str
    enemy_name: str
    item_key: str
    notable_stats: CharacterStats = CharacterStats()
    armor_class: int = 0
    unique_to_enemy: bool = True


@dataclass(frozen=True, slots=True)
class MaterialRequirement:
    item_key: str
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Crafting material quantity must be positive.")


@dataclass(frozen=True, slots=True)
class CraftingRecipe:
    key: str
    trade_skill_key: str
    output_item_key: str
    minimum_skill: int
    high_skill_quality_threshold: int
    materials: tuple[MaterialRequirement, ...] = ()
    output_quantity: int = 1
    station_key: str | None = None
    description: str = ""
    design_status: str = "provisional_tuning"

    def __post_init__(self) -> None:
        if self.output_quantity <= 0:
            raise ValueError("Crafting output quantity must be positive.")

    def can_craft(self, skill_value: int) -> bool:
        return skill_value >= self.minimum_skill

    def produces_high_quality_result(self, skill_value: int) -> bool:
        return skill_value >= self.high_skill_quality_threshold


@dataclass(frozen=True, slots=True)
class CraftingProgressionRules:
    trade_skills_improve_with_practice: bool = True
    extensive_skill_investment_is_required_for_best_gear: bool = True
    master_crafting_can_compete_with_strong_drops: bool = True


CRAFTING_PROGRESSION_RULES = CraftingProgressionRules()


def can_equip_item(item: EquipmentItem, race_key: str, class_key: str) -> bool:
    return item.can_equip(race_key=race_key, class_key=class_key)
