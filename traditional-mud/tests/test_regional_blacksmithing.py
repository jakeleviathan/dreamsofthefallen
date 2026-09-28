from __future__ import annotations

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_blacksmithing as smith
from mud.crafting import ItemDefinition
from mud.stats import CharacterStats, EquipmentItem


def test_regional_blacksmithing_catalog_has_requested_depth() -> None:
    counts = smith.catalog_counts()

    assert len(smith.TRADITIONS) == 9
    assert counts["regional_patterns"] == 378
    assert counts["components"] == 21
    assert counts["quench_media"] == 9
    assert counts["alloy_billets"] == 3
    assert counts["hidden_techniques"] == 9
    assert len({recipe.key for recipe in smith.RECIPES}) == len(smith.RECIPES)
    assert len({item.key for item in smith.ITEMS}) == len(smith.ITEMS)


def test_every_regional_pattern_uses_components_quench_and_lesson() -> None:
    for tradition in smith.TRADITIONS:
        for metal in crafting.METAL_TIERS:
            rows = [
                recipe
                for recipe in smith.RECIPES
                if recipe.design_status == "regional_blacksmith_pattern"
                and recipe.key.startswith(
                    f"smith_pattern_{tradition.key}_{metal.key}_"
                )
            ]
            assert len(rows) == 6
            assert all(
                recipe.discovery_flag == smith.lesson_flag(tradition.key, metal.key)
                for recipe in rows
            )
            assert all(
                any(
                    requirement.item_key == smith.quench_key(tradition.key)
                    for requirement in recipe.materials
                )
                for recipe in rows
            )
            assert all(
                any(
                    requirement.item_key.startswith(f"smith_{metal.key}_")
                    for requirement in recipe.materials
                )
                for recipe in rows
            )


def test_regional_blacksmithing_static_materials_are_real_items() -> None:
    known = (
        set(crafting.ITEMS_BY_KEY)
        | {item.key for item in economy.ECONOMY_ITEMS}
        | {item.key for item in smith.ITEMS}
    )
    missing = {
        requirement.item_key
        for recipe in smith.RECIPES
        for requirement in recipe.materials
        if requirement.item_key not in known
    }
    assert missing == set()


def test_reforging_never_reduces_base_weapon_stats() -> None:
    base = ItemDefinition(
        "test_old_sword",
        "Test Old Sword",
        "An old test blade.",
        "equipment",
        EquipmentItem(
            "Test Old Sword",
            "weapon",
            stat_bonuses=CharacterStats(might=3, grace=2),
        ),
        tier=1,
    )

    reforged = smith._reforge_stats(
        base,
        crafting.METAL_TIERS_BY_KEY["cobalt"],
    )

    assert reforged.stat_bonuses.might >= 4
    assert reforged.stat_bonuses.grace == 2
    assert reforged.armor_class == 0


def test_reforge_cost_scales_with_piece_size() -> None:
    weapon = ItemDefinition(
        "test_sword",
        "Test Sword",
        "",
        "equipment",
        EquipmentItem("Test Sword", "weapon"),
        tier=1,
    )
    shield = ItemDefinition(
        "test_shield",
        "Test Shield",
        "",
        "equipment",
        EquipmentItem("Test Shield", "off_hand"),
        tier=1,
    )
    armor = ItemDefinition(
        "test_breastplate",
        "Test Breastplate",
        "",
        "equipment",
        EquipmentItem("Test Breastplate", "body"),
        tier=1,
    )

    assert smith._reforge_cost(weapon) == 2
    assert smith._reforge_cost(shield) == 3
    assert smith._reforge_cost(armor) == 4
