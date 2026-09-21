from __future__ import annotations

import asyncio
from dataclasses import dataclass

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_workshops as workshops
import mud.style_collectibles as style
from mud.crafting import ConsumableEffect, ItemDefinition, ResourceNodeDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem


@dataclass(frozen=True, slots=True)
class ProfessionBand:
    key: str
    name: str
    trivial: int
    tier: int
    reagent_key: str


PROFESSION_BANDS: tuple[ProfessionBand, ...] = (
    ProfessionBand("greenward", "Greenward", 0, 1, "greenleaf"),
    ProfessionBand("bitterroad", "Bitterroad", 15, 2, "bitterroot"),
    ProfessionBand("lavender", "Lavender", 30, 3, "lavender_blossom"),
    ProfessionBand("moonlit", "Moonlit", 50, 4, "moonflax_fiber"),
    ProfessionBand("emberward", "Emberward", 75, 5, "emberite_ore"),
    ProfessionBand("starbound", "Starbound", 105, 6, "stariron_ore"),
    ProfessionBand("astral", "Astral", 140, 7, "astral_bloom_fiber"),
    ProfessionBand("astralite", "Astralite", 175, 8, "astralite_ore"),
)

# Perfumery is an Alchemy specialization with deliberately simple power rules:
# one real-time fragrance effect at a time, character XP only, never tradeskill XP.
# Higher tiers improve both strength and duration; applying another perfume replaces
# the current scent instead of stacking with it.
PERFUME_TIER_EFFECTS: dict[int, tuple[int, int]] = {
    1: (5, 20 * 60),
    2: (7, 25 * 60),
    3: (10, 30 * 60),
    4: (12, 35 * 60),
    5: (15, 40 * 60),
    6: (18, 45 * 60),
    7: (21, 50 * 60),
    8: (25, 60 * 60),
}

PERFUME_FORMULAS: tuple[tuple[str, str, tuple[str, str]], ...] = (
    ("first_rain", "First Rain", ("rain air", "clean herbs")),
    ("velvet_road", "Velvet Road", ("warm spice", "dark resin")),
    ("quiet_lantern", "Quiet Lantern", ("lavender", "soft smoke")),
    ("glass_orchard", "Glass Orchard", ("cool water", "mineral fruit")),
    ("night_market", "Night Market", ("green tincture", "soft amber")),
)

SECRET_RECIPE_FLAGS = {
    "secret_fallen_star_greatblade": "recipe_secret_fallen_star_greatblade",
    "secret_astral_dreamcloak": "recipe_secret_astral_dreamcloak",
    "secret_one_breath_elixir": "recipe_secret_one_breath_elixir",
    "secret_last_door_focus": "recipe_secret_last_door_focus",
    "secret_seven_roads_feast": "recipe_secret_seven_roads_feast",
    "secret_perfume_fallen_star_no7": "recipe_secret_perfume_fallen_star_no7",
    "secret_perfume_queens_funeral": "recipe_secret_perfume_queens_funeral",
    "secret_perfume_brassgut_nocturne": "recipe_secret_perfume_brassgut_nocturne",
}


@dataclass(frozen=True, slots=True)
class PantryIngredient:
    key: str
    name: str
    node_key: str
    node_name: str
    gathering_skill: str
    minimum_skill: int
    tier: int
    room_key: str
    description: str


PANTRY_INGREDIENTS: tuple[PantryIngredient, ...] = (
    PantryIngredient(
        "sunberry",
        "Sunberry",
        "sunberry_brake",
        "Sunberry Brake",
        "harvesting",
        0,
        1,
        "forest_elf_greenway",
        "A tart gold-red berry cultivated along warm paths and eaten fresh or cooked down into sauces.",
    ),
    PantryIngredient(
        "pepperreed",
        "Pepperreed",
        "pepperreed_bed",
        "Pepperreed Bed",
        "harvesting",
        15,
        2,
        "waymeet_briarcut_fields",
        "A crisp roadside reed whose seed heads carry a clean peppery heat.",
    ),
    PantryIngredient(
        "resonant_pear",
        "Resonant Pear",
        "resonant_pear_tree",
        "Resonant Pear Tree",
        "harvesting",
        30,
        3,
        "greywake_resonant_orchard",
        "A pale orchard pear with a faint mineral sweetness from Greywake soil.",
    ),
    PantryIngredient(
        "saltgrass_shoot",
        "Saltgrass Shoot",
        "saltgrass_shoot_patch",
        "Saltgrass Shoot Patch",
        "harvesting",
        50,
        4,
        "sablewater_saltgrass_bend",
        "A tender briny shoot gathered before the marsh grass toughens in the sun.",
    ),
    PantryIngredient(
        "brasscap_mushroom",
        "Brasscap Mushroom",
        "brasscap_cluster",
        "Brasscap Cluster",
        "herbalism",
        75,
        5,
        "veyra_north_waterworks",
        "A nutty brown mushroom that favors warm brick, steam, and mineral-rich runoff.",
    ),
    PantryIngredient(
        "grave_sage",
        "Grave Sage",
        "grave_sage_patch",
        "Grave Sage Patch",
        "herbalism",
        105,
        6,
        "gravewatch_chapel_nave",
        "A silver-green culinary sage that survives in cold old masonry and gives food a deep smoky aroma.",
    ),
    PantryIngredient(
        "rift_truffle",
        "Rift Truffle",
        "rift_truffle_patch",
        "Rift Truffle Patch",
        "herbalism",
        140,
        7,
        "greywake_riftfield",
        "A dark subterranean fungus found where Greywake soil has been repeatedly disturbed by strange energy.",
    ),
    PantryIngredient(
        "astral_plum",
        "Astral Plum",
        "astral_plum_tree",
        "Astral Plum Tree",
        "harvesting",
        175,
        8,
        "greywake_resonant_orchard",
        "An exceptionally rare violet fruit that appears on only the oldest resonant orchard trees.",
    ),
)


def _equipment(
    key: str,
    name: str,
    description: str,
    tier: int,
    slot: str,
    *,
    armor_class: int = 0,
    stats: CharacterStats = CharacterStats(),
) -> ItemDefinition:
    return ItemDefinition(
        key,
        name,
        description,
        "equipment",
        equipment=EquipmentItem(
            name,
            slot,
            armor_class=max(0, armor_class),
            stat_bonuses=stats,
        ),
        tier=tier,
    )


def _blacksmithing_expansion() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    patterns = (
        ("handaxe", "Handaxe", "weapon", 1, 1),
        ("warhammer", "Warhammer", "weapon", 2, 2),
        ("spear", "Spear", "weapon", 2, 2),
        ("greatsword", "Greatsword", "weapon", 3, 3),
        ("shield", "Shield", "off_hand", 2, 4),
        ("gauntlets", "Gauntlets", "hands", 1, 6),
        ("greaves", "Greaves", "legs", 2, 8),
        ("boots", "Boots", "feet", 2, 10),
    )
    for metal in crafting.METAL_TIERS:
        for slug, label, slot, ingots, offset in patterns:
            item_key = f"artisan_{metal.key}_{slug}"
            item_name = f"{metal.name} {label}"
            tier = metal.tier
            if slug == "handaxe":
                stats = CharacterStats(might=tier + 1)
                ac = 0
            elif slug == "warhammer":
                stats = CharacterStats(might=tier + 2)
                ac = 0
            elif slug == "spear":
                stats = CharacterStats(might=tier, grace=1)
                ac = 0
            elif slug == "greatsword":
                stats = CharacterStats(might=tier + 2, hp=max(0, tier // 3))
                ac = 0
            elif slug == "shield":
                stats = CharacterStats(hp=tier)
                ac = tier + 1
            elif slug == "gauntlets":
                stats = CharacterStats(might=1 if tier >= 2 else 0)
                ac = max(1, tier // 2)
            elif slug == "greaves":
                stats = CharacterStats(hp=max(1, tier // 2))
                ac = tier + 1
            else:
                stats = CharacterStats(grace=1 if tier >= 2 else 0)
                ac = max(1, tier)
            items.append(
                _equipment(
                    item_key,
                    item_name,
                    f"A carefully fitted {metal.name.lower()} {label.lower()} made by an experienced smith.",
                    tier,
                    slot,
                    armor_class=ac,
                    stats=stats,
                )
            )
            trivial = metal.blacksmithing_skill + offset
            recipes.append(
                CraftingRecipe(
                    f"artisan_forge_{metal.key}_{slug}",
                    "blacksmithing",
                    item_key,
                    trivial,
                    trivial + 30,
                    (MaterialRequirement(metal.ingot_key, ingots),),
                    station_key="forge",
                    description=f"Forge {ingots} {metal.name} ingot{'s' if ingots != 1 else ''} into a {item_name}.",
                    design_status="deep_profession_expansion",
                )
            )

    master_patterns = (
        ("handaxe", "Handaxe", "weapon", 3, CharacterStats(might=9)),
        ("warhammer", "Warhammer", "weapon", 4, CharacterStats(might=10, hp=2)),
        ("spear", "Spear", "weapon", 4, CharacterStats(might=8, grace=2)),
        ("greatsword", "Greatsword", "weapon", 5, CharacterStats(might=11, hp=2)),
        ("shield", "Tower Shield", "off_hand", 5, CharacterStats(hp=8)),
        ("gauntlets", "Gauntlets", "hands", 3, CharacterStats(might=2)),
        ("greaves", "Greaves", "legs", 4, CharacterStats(hp=5)),
        ("boots", "Boots", "feet", 3, CharacterStats(grace=2, hp=2)),
    )
    for index, (slug, label, slot, ingots, stats) in enumerate(master_patterns):
        item_key = f"artisan_master_astralite_{slug}"
        item_name = f"Masterwork Astralite {label}"
        ac = 0 if slot == "weapon" else 9 if slot == "off_hand" else 5
        items.append(
            _equipment(
                item_key,
                item_name,
                "Astralite worked beyond ordinary tier patterns, with every seam and striking surface finished by hand.",
                8,
                slot,
                armor_class=ac,
                stats=stats,
            )
        )
        recipes.append(
            CraftingRecipe(
                f"artisan_master_forge_astralite_{slug}",
                "blacksmithing",
                item_key,
                175 + index * 2,
                210 + index * 2,
                (MaterialRequirement("astralite_ingot", ingots),),
                station_key="forge",
                description=f"Produce a true masterwork {label.lower()} from exceptionally clean Astralite.",
                design_status="masterwork_profession_expansion",
            )
        )
    return tuple(items), tuple(recipes)


def _tailoring_expansion() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    patterns = (
        ("gloves", "Gloves", "hands", 1, 2),
        ("boots", "Soft Boots", "feet", 1, 4),
        ("trousers", "Trousers", "legs", 2, 6),
        ("robe", "Robe", "body", 2, 8),
        ("cloak", "Cloak", "body", 2, 10),
        ("wraps", "Hand Wraps", "hands", 1, 12),
        ("leggings", "Leggings", "legs", 2, 14),
        ("veil", "Veil", "head", 1, 16),
    )
    for textile in crafting.TEXTILE_TIERS:
        tier = textile.tier
        for slug, label, slot, cloth, offset in patterns:
            item_key = f"artisan_{textile.key}_{slug}"
            item_name = f"{textile.name} {label}"
            if slug in {"gloves", "wraps"}:
                stats = CharacterStats(grace=1 if tier >= 2 else 0, love=1 if slug == "wraps" and tier >= 4 else 0)
                ac = max(0, tier // 3)
            elif slug == "boots":
                stats = CharacterStats(grace=1 if tier >= 2 else 0)
                ac = max(0, tier // 3)
            elif slug in {"trousers", "leggings"}:
                stats = CharacterStats(grace=1 if tier >= 3 else 0, hp=max(0, tier // 3))
                ac = max(1, tier // 2)
            elif slug == "robe":
                stats = CharacterStats(mind=max(1, tier // 2), love=max(0, tier // 3))
                ac = max(0, tier // 3)
            elif slug == "cloak":
                stats = CharacterStats(grace=max(1, tier // 3), hp=max(0, tier // 3))
                ac = max(0, tier // 3)
            else:
                stats = CharacterStats(mind=max(1, tier // 3), love=max(1, tier // 3))
                ac = max(0, tier // 4)
            items.append(
                _equipment(
                    item_key,
                    item_name,
                    f"A fitted {textile.name.lower()} {label.lower()} with reinforced seams and careful finishing.",
                    tier,
                    slot,
                    armor_class=ac,
                    stats=stats,
                )
            )
            trivial = textile.tailoring_skill + offset
            recipes.append(
                CraftingRecipe(
                    f"artisan_sew_{textile.key}_{slug}",
                    "tailoring",
                    item_key,
                    trivial,
                    trivial + 30,
                    (MaterialRequirement(textile.cloth_item_key, cloth),),
                    station_key="loom",
                    description=f"Cut and sew {cloth} piece{'s' if cloth != 1 else ''} of {textile.cloth_item_name} into {item_name}.",
                    design_status="deep_profession_expansion",
                )
            )

    master_patterns = (
        ("gloves", "Gloves", "hands", 2, CharacterStats(grace=2, mind=2)),
        ("boots", "Soft Boots", "feet", 2, CharacterStats(grace=3, hp=2)),
        ("trousers", "Trousers", "legs", 3, CharacterStats(grace=2, hp=4)),
        ("robe", "Robe", "body", 4, CharacterStats(mind=4, love=3)),
        ("cloak", "Cloak", "body", 4, CharacterStats(grace=3, hp=3)),
        ("wraps", "Hand Wraps", "hands", 2, CharacterStats(love=3, mind=2)),
        ("leggings", "Leggings", "legs", 3, CharacterStats(grace=3, hp=3)),
        ("veil", "Veil", "head", 2, CharacterStats(mind=3, love=3)),
    )
    for index, (slug, label, slot, cloth, stats) in enumerate(master_patterns):
        item_key = f"artisan_master_astralweave_{slug}"
        item_name = f"Masterwork Astralweave {label}"
        items.append(
            _equipment(
                item_key,
                item_name,
                "Astralweave cut with unusually fine tension control, leaving the finished piece light, durable, and precise.",
                8,
                slot,
                armor_class=4 if slot in {"body", "legs"} else 2,
                stats=stats,
            )
        )
        recipes.append(
            CraftingRecipe(
                f"artisan_master_sew_astralweave_{slug}",
                "tailoring",
                item_key,
                175 + index * 2,
                210 + index * 2,
                (MaterialRequirement("astralweave_cloth", cloth),),
                station_key="loom",
                description=f"Sew a masterwork Astralweave {label.lower()} from perfectly matched cloth.",
                design_status="masterwork_profession_expansion",
            )
        )
    return tuple(items), tuple(recipes)


def _alchemy_expansion() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    potion_patterns = (
        ("healing_draught", "Healing Draught", "healing"),
        ("vigor_elixir", "Vigor Elixir", "might"),
        ("quickstep_elixir", "Quickstep Elixir", "grace"),
        ("clarity_elixir", "Clarity Elixir", "mind"),
        ("mercy_elixir", "Mercy Elixir", "love"),
        ("fortitude_elixir", "Fortitude Elixir", "hp"),
        ("cleansing_tonic", "Cleansing Tonic", "cleansing"),
        ("warding_tonic", "Warding Tonic", "warding"),
        ("restorative_cordial", "Restorative Cordial", "restorative"),
    )
    for band in PROFESSION_BANDS:
        catalyst_key = f"profexp_{band.key}_catalyst"
        catalyst_name = f"{band.name} Catalyst"
        items.append(
            ItemDefinition(
                catalyst_key,
                catalyst_name,
                f"A concentrated alchemical base carrying the useful character of {band.name.lower()} ingredients.",
                "alchemy_material",
                tier=band.tier,
            )
        )
        solvent = "spring_water" if band.tier <= 2 else "grain_alcohol"
        recipes.append(
            CraftingRecipe(
                f"refine_{band.key}_catalyst",
                "alchemy",
                catalyst_key,
                band.trivial,
                band.trivial + 25,
                (
                    MaterialRequirement(band.reagent_key, 2),
                    MaterialRequirement(solvent, 1),
                ),
                station_key="alchemy_table" if band.tier >= 3 else "mortar_and_pestle",
                description=f"Refine {band.name.lower()} source material into a stable catalyst for stronger preparations.",
                design_status="deep_profession_expansion",
            )
        )
        for index, (slug, label, effect_kind) in enumerate(potion_patterns, start=1):
            key = f"profexp_{band.key}_{slug}"
            name = f"{band.name} {label}"
            boost = 1 + (1 if band.tier >= 5 else 0)
            bonus = CharacterStats()
            heal = 0
            if effect_kind == "healing":
                heal = 8 + band.tier * 5
            elif effect_kind == "might":
                bonus = CharacterStats(might=boost)
            elif effect_kind == "grace":
                bonus = CharacterStats(grace=boost)
            elif effect_kind == "mind":
                bonus = CharacterStats(mind=boost)
            elif effect_kind == "love":
                bonus = CharacterStats(love=boost)
            elif effect_kind == "hp":
                bonus = CharacterStats(hp=2 + band.tier)
            elif effect_kind == "cleansing":
                heal = 3 + band.tier * 2
                bonus = CharacterStats(love=boost)
            elif effect_kind == "warding":
                bonus = CharacterStats(hp=1 + band.tier, mind=1 if band.tier >= 3 else 0)
            elif effect_kind == "restorative":
                heal = 5 + band.tier * 4
                bonus = CharacterStats(love=boost, hp=max(1, band.tier // 2))
            items.append(
                ItemDefinition(
                    key,
                    name,
                    f"A tier {band.tier} alchemical preparation built on {catalyst_name}.",
                    "potion",
                    consumable=ConsumableEffect(
                        use_mode="drink",
                        heal_hp=heal,
                        temporary_stat_bonuses=bonus,
                        duration_ticks=12 + band.tier * 4,
                        effect_tags=("alchemy", effect_kind, band.key),
                    ),
                    tier=band.tier,
                )
            )
            catalyst_quantity = 2 if index >= 7 else 1
            recipes.append(
                CraftingRecipe(
                    f"brew_{band.key}_{slug}",
                    "alchemy",
                    key,
                    band.trivial + index,
                    band.trivial + index + 30,
                    (
                        MaterialRequirement(catalyst_key, catalyst_quantity),
                        MaterialRequirement("spring_water", 1),
                    ),
                    station_key="alchemy_table",
                    description=f"Balance {catalyst_name} into {name}, controlling concentration rather than simply adding more reagent.",
                    design_status="deep_profession_expansion",
                )
            )
    return tuple(items), tuple(recipes)


def _pantry_content() -> tuple[tuple[ItemDefinition, ...], tuple[ResourceNodeDefinition, ...]]:
    items = tuple(
        ItemDefinition(
            ingredient.key,
            ingredient.name,
            ingredient.description,
            "food_material",
            tier=ingredient.tier,
        )
        for ingredient in PANTRY_INGREDIENTS
    )
    nodes = tuple(
        ResourceNodeDefinition(
            ingredient.node_key,
            ingredient.node_name,
            ingredient.gathering_skill,
            ingredient.key,
            minimum_skill=ingredient.minimum_skill,
            design_status="deep_cooking_pantry",
            tier=ingredient.tier,
            region_hint=ingredient.room_key.replace("_", " ").title(),
        )
        for ingredient in PANTRY_INGREDIENTS
    )
    return items, nodes


def _cooking_expansion() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    dish_patterns = (
        ("flatcake", "Flatcake", (("field_grain", 2), ("ingredient", 1), ("spring_water", 1))),
        ("broth", "Broth", (("ingredient", 1), ("marsh_onion", 1), ("spring_water", 1))),
        ("porridge", "Porridge", (("field_grain", 2), ("ingredient", 1), ("spring_water", 1))),
        ("dumplings", "Dumplings", (("field_grain", 2), ("marsh_onion", 1), ("ingredient", 1))),
        ("stew", "Stew", (("field_grain", 1), ("marsh_onion", 1), ("ingredient", 2), ("spring_water", 1))),
        ("roast", "Roast", (("ingredient", 2), ("marsh_onion", 1))),
        ("handpie", "Handpie", (("field_grain", 2), ("ingredient", 1))),
        ("trail_ration", "Trail Ration", (("field_grain", 2), ("ingredient", 1))),
        ("savory_cake", "Savory Cake", (("field_grain", 2), ("ingredient", 1), ("greenleaf", 1))),
        ("feast_platter", "Feast Platter", (("field_grain", 2), ("marsh_onion", 1), ("ingredient", 2), ("greenleaf", 1))),
    )
    for band, ingredient in zip(PROFESSION_BANDS, PANTRY_INGREDIENTS):
        for index, (slug, label, material_rows) in enumerate(dish_patterns):
            key = f"profexp_{ingredient.key}_{slug}"
            name = f"{ingredient.name} {label}"
            stat_index = index % 5
            boost = 1 + (1 if band.tier >= 6 and index in {4, 9} else 0)
            bonus = (
                CharacterStats(might=boost)
                if stat_index == 0
                else CharacterStats(grace=boost)
                if stat_index == 1
                else CharacterStats(love=boost)
                if stat_index == 2
                else CharacterStats(mind=boost)
                if stat_index == 3
                else CharacterStats(hp=2 + band.tier)
            )
            heal = 4 + band.tier * 4 + index
            items.append(
                ItemDefinition(
                    key,
                    name,
                    f"A carefully prepared {label.lower()} centered on {ingredient.name}, built as practical adventuring food rather than a decorative collectible.",
                    "food",
                    consumable=ConsumableEffect(
                        use_mode="eat",
                        heal_hp=heal,
                        temporary_stat_bonuses=bonus,
                        duration_ticks=10 + band.tier * 3,
                        effect_tags=("food", ingredient.key, slug),
                    ),
                    tier=band.tier,
                )
            )
            materials = tuple(
                MaterialRequirement(
                    ingredient.key if item_key == "ingredient" else item_key,
                    quantity,
                )
                for item_key, quantity in material_rows
            )
            recipes.append(
                CraftingRecipe(
                    f"cook_{ingredient.key}_{slug}",
                    "cooking",
                    key,
                    band.trivial + index,
                    band.trivial + index + 25,
                    materials,
                    station_key="cookfire",
                    description=f"Prepare {name} with enough attention to texture and timing that the ingredient remains recognizable.",
                    design_status="deep_profession_expansion",
                )
            )
    return tuple(items), tuple(recipes)


def _enchanting_expansion() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    metals = (*crafting.METAL_TIERS, crafting.METAL_TIERS[-1])
    textiles = (*crafting.TEXTILE_TIERS, crafting.TEXTILE_TIERS[-1])
    for band, metal, textile in zip(PROFESSION_BANDS, metals, textiles):
        tier = band.tier
        sigil_key = f"profexp_{band.key}_sigil"
        sigil_name = f"{band.name} Binding Sigil"
        catalyst_key = f"profexp_{band.key}_catalyst"
        items.append(
            ItemDefinition(
                sigil_key,
                sigil_name,
                f"A prepared rune medium that lets an enchanter bind {band.name.lower()} power to finished equipment.",
                "enchanting_material",
                tier=tier,
            )
        )
        recipes.append(
            CraftingRecipe(
                f"scribe_{band.key}_binding_sigil",
                "enchanting",
                sigil_key,
                band.trivial,
                band.trivial + 25,
                (
                    MaterialRequirement(catalyst_key, 1),
                    MaterialRequirement("arcane_residue", 1 + tier // 3),
                ),
                station_key="enchanting_table",
                description=f"Scribe and wake a {sigil_name} from alchemical catalyst and Arcane Residue.",
                design_status="deep_profession_expansion",
            )
        )

        patterns = (
            ("sword", f"{metal.key}_sword", f"{band.name} Runed {metal.name} Sword", "weapon"),
            ("dagger", f"{metal.key}_dagger", f"{band.name} Runed {metal.name} Dagger", "weapon"),
            ("shield", f"artisan_{metal.key}_shield", f"{band.name} Warded {metal.name} Shield", "off_hand"),
            ("helmet", f"{metal.key}_helmet", f"{band.name} Warded {metal.name} Helmet", "head"),
            ("breastplate", f"{metal.key}_breastplate", f"{band.name} Warded {metal.name} Breastplate", "body"),
            ("robe", f"artisan_{textile.key}_robe", f"{band.name} Runed {textile.name} Robe", "body"),
            ("gloves", f"artisan_{textile.key}_gloves", f"{band.name} Runed {textile.name} Gloves", "hands"),
            ("boots", f"artisan_{textile.key}_boots", f"{band.name} Runed {textile.name} Boots", "feet"),
        )
        for index, (slug, base_key, name, slot) in enumerate(patterns, start=1):
            output_key = f"profexp_enchanted_{band.key}_{slug}"
            ac = 0
            stats = CharacterStats()
            if slug == "sword":
                stats = CharacterStats(might=tier + 1, mind=max(1, tier // 2))
            elif slug == "dagger":
                stats = CharacterStats(might=tier, grace=1 + tier // 4, mind=max(1, tier // 3))
            elif slug == "shield":
                ac = tier + 2
                stats = CharacterStats(hp=tier + 1, love=max(1, tier // 3))
            elif slug == "helmet":
                ac = tier
                stats = CharacterStats(mind=max(1, tier // 2), hp=max(0, tier // 3))
            elif slug == "breastplate":
                ac = 2 * tier + 2
                stats = CharacterStats(hp=tier + 2, love=max(0, tier // 3))
            elif slug == "robe":
                ac = max(1, tier // 2)
                stats = CharacterStats(mind=max(1, tier // 2 + 1), love=max(1, tier // 3))
            elif slug == "gloves":
                ac = max(0, tier // 3)
                stats = CharacterStats(grace=1, mind=max(1, tier // 3))
            elif slug == "boots":
                ac = max(0, tier // 3)
                stats = CharacterStats(grace=1 + tier // 4, hp=max(0, tier // 2))
            items.append(
                _equipment(
                    output_key,
                    name,
                    f"A finished piece carrying a stable {band.name.lower()} binding without replacing the underlying craftsmanship.",
                    tier,
                    slot,
                    armor_class=ac,
                    stats=stats,
                )
            )
            recipes.append(
                CraftingRecipe(
                    f"enchant_{band.key}_{slug}",
                    "enchanting",
                    output_key,
                    band.trivial + index,
                    band.trivial + index + 30,
                    (
                        MaterialRequirement(base_key, 1),
                        MaterialRequirement(sigil_key, 1),
                    ),
                    station_key="enchanting_table",
                    description=f"Bind {sigil_name} into {name}, preserving the base item's physical strengths.",
                    design_status="deep_profession_expansion",
                )
            )

        focus_key = f"profexp_enchanted_{band.key}_focus"
        focus_name = f"{band.name} Runic Focus"
        items.append(
            _equipment(
                focus_key,
                focus_name,
                f"A compact off-hand focus assembled from {metal.name.lower()} and {textile.name.lower()} components around a binding sigil.",
                tier,
                "off_hand",
                stats=CharacterStats(mind=max(1, tier // 2 + 1), love=max(1, tier // 3)),
            )
        )
        recipes.append(
            CraftingRecipe(
                f"enchant_{band.key}_runic_focus",
                "enchanting",
                focus_key,
                band.trivial + 9,
                band.trivial + 39,
                (
                    MaterialRequirement(sigil_key, 1),
                    MaterialRequirement(metal.ingot_key, 1),
                    MaterialRequirement(textile.thread_item_key, 1),
                ),
                station_key="enchanting_table",
                description=f"Build a {focus_name} around a metal core and tightly wound enchanted thread.",
                design_status="deep_profession_expansion",
            )
        )
    return tuple(items), tuple(recipes)


def _perfumery_expansion() -> tuple[
    tuple[ItemDefinition, ...],
    tuple[CraftingRecipe, ...],
    tuple[style.FragranceDefinition, ...],
]:
    """Build the Alchemy perfumery ladder and its finished XP fragrances."""

    items: list[ItemDefinition] = []
    recipes: list[CraftingRecipe] = []
    fragrances: list[style.FragranceDefinition] = []

    rarity_by_tier = {
        1: "common",
        2: "uncommon",
        3: "uncommon",
        4: "rare",
        5: "rare",
        6: "rare",
        7: "epic",
        8: "epic",
    }
    fixatives = (
        "lavender_essential_oil",
        "greenleaf_tincture",
        "spring_water",
        "arcane_residue",
        None,
    )

    for band, ingredient in zip(PROFESSION_BANDS, PANTRY_INGREDIENTS):
        xp_bonus, duration_seconds = PERFUME_TIER_EFFECTS[band.tier]
        concentrate_key = f"perfume_{band.key}_concentrate"
        concentrate_name = f"{band.name} Perfume Concentrate"
        items.append(
            ItemDefinition(
                concentrate_key,
                concentrate_name,
                f"A concentrated aromatic base distilled for tier {band.tier} perfumery. "
                "It is intentionally too strong to wear until diluted and fixed into a finished perfume.",
                "alchemy_material",
                tier=band.tier,
            )
        )
        recipes.append(
            CraftingRecipe(
                f"distill_{band.key}_perfume_concentrate",
                "alchemy",
                concentrate_key,
                band.trivial + 2,
                band.trivial + 27,
                (
                    MaterialRequirement(f"profexp_{band.key}_catalyst", 1),
                    MaterialRequirement(ingredient.key, 2),
                    MaterialRequirement("grain_alcohol", 1),
                ),
                station_key="perfumer_bench",
                description=f"Distill {ingredient.name} through a {band.name} Catalyst into a stable aromatic concentrate.",
                design_status="perfumery_concentrate",
            )
        )

        for index, ((slug, label, supporting_notes), fixative) in enumerate(
            zip(PERFUME_FORMULAS, fixatives),
            start=1,
        ):
            item_key = f"perfume_{band.key}_{slug}"
            item_name = f"{band.name} {label}"
            notes = (ingredient.name.lower(), *supporting_notes)
            bottle = (
                f"a tier {band.tier} artisan bottle marked with a narrow {band.name.lower()} band "
                "and a hand-written batch number"
            )
            items.append(
                ItemDefinition(
                    item_key,
                    item_name,
                    f"An Alchemist-crafted perfume of {', '.join(notes)}. "
                    f"When applied, it grants +{xp_bonus}% character XP for {duration_seconds // 60} real minutes.",
                    "fragrance",
                    tier=band.tier,
                )
            )
            fragrances.append(
                style.FragranceDefinition(
                    item_key,
                    "Astralis Perfumers' Guild",
                    rarity_by_tier[band.tier],
                    notes,
                    bottle,
                    duration_seconds,
                    xp_bonus,
                    0,
                )
            )

            materials = [
                MaterialRequirement(concentrate_key, 1),
                MaterialRequirement("grain_alcohol", 1),
            ]
            if fixative is None:
                materials.append(MaterialRequirement(ingredient.key, 1))
            else:
                materials.append(MaterialRequirement(fixative, 1))
            recipes.append(
                CraftingRecipe(
                    f"blend_perfume_{band.key}_{slug}",
                    "alchemy",
                    item_key,
                    band.trivial + 4 + index * 2,
                    band.trivial + 34 + index * 2,
                    tuple(materials),
                    station_key="perfumer_bench",
                    description=f"Blend {item_name} from {concentrate_name}, then dilute and fix the scent for safe wear.",
                    design_status="perfumery_formula",
                )
            )

    secret_specs = (
        (
            "perfume_fallen_star_no7",
            "Fallen Star No. 7",
            ("cold iron", "night air", "violet smoke"),
            "secret_perfume_fallen_star_no7",
            (
                MaterialRequirement("perfume_astralite_concentrate", 1),
                MaterialRequirement("stariron_ore", 1),
                MaterialRequirement("lavender_essential_oil", 1),
                MaterialRequirement("grain_alcohol", 1),
            ),
        ),
        (
            "perfume_queens_funeral",
            "Queen's Funeral",
            ("grave sage", "white flowers", "quiet incense"),
            "secret_perfume_queens_funeral",
            (
                MaterialRequirement("perfume_astralite_concentrate", 1),
                MaterialRequirement("grave_sage", 1),
                MaterialRequirement("greenleaf_tincture", 1),
                MaterialRequirement("grain_alcohol", 1),
            ),
        ),
        (
            "perfume_brassgut_nocturne",
            "Brassgut Nocturne",
            ("brasscap", "burnt sugar", "warm machinery"),
            "secret_perfume_brassgut_nocturne",
            (
                MaterialRequirement("perfume_astralite_concentrate", 1),
                MaterialRequirement("brasscap_mushroom", 1),
                MaterialRequirement("arcane_residue", 1),
                MaterialRequirement("grain_alcohol", 1),
            ),
        ),
    )
    max_bonus, max_duration = PERFUME_TIER_EFFECTS[8]
    for offset, (item_key, item_name, notes, recipe_key, materials) in enumerate(secret_specs):
        items.append(
            ItemDefinition(
                item_key,
                item_name,
                f"A secret master-perfumer formula of {', '.join(notes)}. "
                f"It grants +{max_bonus}% character XP for {max_duration // 60} real minutes.",
                "fragrance",
                tier=8,
            )
        )
        fragrances.append(
            style.FragranceDefinition(
                item_key,
                "Unattributed Formula",
                "epic",
                notes,
                "an unmarked master-perfumer bottle with no commercial seal",
                max_duration,
                max_bonus,
                0,
            )
        )
        recipes.append(
            CraftingRecipe(
                recipe_key,
                "alchemy",
                item_key,
                190 + offset * 2,
                225 + offset * 2,
                materials,
                station_key="perfumer_bench",
                description=f"Blend the hidden master formula for {item_name}. Its effect matches top-tier perfume; its distinction is discovery and craft identity.",
                design_status="perfumery_secret_recipe",
                discovery_flag=SECRET_RECIPE_FLAGS[recipe_key],
            )
        )

    return tuple(items), tuple(recipes), tuple(fragrances)


def _secret_content() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items = (
        _equipment(
            "secret_fallen_star_greatblade_item",
            "Fallen-Star Greatblade",
            "A dark Astralite greatblade with a narrow Stariron seam through its center, made from a workshop trick rarely written down.",
            8,
            "weapon",
            stats=CharacterStats(might=12, mind=2, hp=2),
        ),
        _equipment(
            "secret_astral_dreamcloak_item",
            "Astral Dreamcloak",
            "A masterwork cloak whose Astralweave layers are cut so the cloth seems to settle before the wearer stops moving.",
            8,
            "body",
            armor_class=4,
            stats=CharacterStats(grace=3, love=3, mind=3, hp=3),
        ),
        ItemDefinition(
            "secret_one_breath_elixir_item",
            "One-Breath Elixir",
            "A clear master alchemist's cordial that briefly sharpens every trained instinct at once.",
            "potion",
            consumable=ConsumableEffect(
                use_mode="drink",
                heal_hp=50,
                temporary_stat_bonuses=CharacterStats(might=1, grace=1, love=1, mind=1, hp=4),
                duration_ticks=45,
                effect_tags=("alchemy", "secret_recipe", "one_breath"),
            ),
            tier=8,
        ),
        _equipment(
            "secret_last_door_focus_item",
            "Last-Door Focus",
            "A compact focus of Astralite, Astral Thread, and layered sigils that rewards careful magical control.",
            8,
            "off_hand",
            armor_class=2,
            stats=CharacterStats(mind=5, love=4, hp=2),
        ),
        ItemDefinition(
            "secret_seven_roads_feast_item",
            "Seven Roads Feast",
            "A sprawling shared dish built from ingredients gathered across Astralis, adapted into a single traveler's portion.",
            "food",
            consumable=ConsumableEffect(
                use_mode="eat",
                heal_hp=60,
                temporary_stat_bonuses=CharacterStats(might=1, grace=1, love=1, mind=1, hp=5),
                duration_ticks=50,
                effect_tags=("food", "secret_recipe", "seven_roads"),
            ),
            tier=8,
        ),
    )
    recipes = (
        CraftingRecipe(
            "secret_fallen_star_greatblade",
            "blacksmithing",
            "secret_fallen_star_greatblade_item",
            190,
            225,
            (
                MaterialRequirement("artisan_master_astralite_greatsword", 1),
                MaterialRequirement("stariron_ingot", 2),
                MaterialRequirement("astralite_ingot", 2),
            ),
            station_key="forge",
            description="Split a finished Astralite greatblade and forge a Stariron seam through the center without losing alignment.",
            design_status="secret_master_recipe",
            discovery_flag=SECRET_RECIPE_FLAGS["secret_fallen_star_greatblade"],
        ),
        CraftingRecipe(
            "secret_astral_dreamcloak",
            "tailoring",
            "secret_astral_dreamcloak_item",
            190,
            225,
            (
                MaterialRequirement("artisan_master_astralweave_cloak", 1),
                MaterialRequirement("ghost_thread", 2),
                MaterialRequirement("astral_thread", 2),
            ),
            station_key="loom",
            description="Re-cut a finished Astralweave cloak around hidden tension seams learned by observation rather than formal instruction.",
            design_status="secret_master_recipe",
            discovery_flag=SECRET_RECIPE_FLAGS["secret_astral_dreamcloak"],
        ),
        CraftingRecipe(
            "secret_one_breath_elixir",
            "alchemy",
            "secret_one_breath_elixir_item",
            190,
            225,
            (
                MaterialRequirement("profexp_astralite_catalyst", 2),
                MaterialRequirement("lavender_perfume", 1),
                MaterialRequirement("spring_water", 1),
            ),
            station_key="alchemy_table",
            description="Suspend an Astralite catalyst in an aromatic carrier without allowing the mineral fraction to precipitate.",
            design_status="secret_master_recipe",
            discovery_flag=SECRET_RECIPE_FLAGS["secret_one_breath_elixir"],
        ),
        CraftingRecipe(
            "secret_last_door_focus",
            "enchanting",
            "secret_last_door_focus_item",
            190,
            225,
            (
                MaterialRequirement("profexp_enchanted_astralite_focus", 1),
                MaterialRequirement("profexp_astralite_sigil", 2),
                MaterialRequirement("astral_thread", 2),
            ),
            station_key="enchanting_table",
            description="Layer two complete Astralite bindings around an existing focus while leaving the center deliberately uninscribed.",
            design_status="secret_master_recipe",
            discovery_flag=SECRET_RECIPE_FLAGS["secret_last_door_focus"],
        ),
        CraftingRecipe(
            "secret_seven_roads_feast",
            "cooking",
            "secret_seven_roads_feast_item",
            190,
            225,
            (
                *(MaterialRequirement(ingredient.key, 1) for ingredient in PANTRY_INGREDIENTS),
                MaterialRequirement("field_grain", 2),
                MaterialRequirement("marsh_onion", 1),
            ),
            station_key="cookfire",
            description="Balance ingredients from eight distant environments into one dish without letting any single region dominate it.",
            design_status="secret_master_recipe",
            discovery_flag=SECRET_RECIPE_FLAGS["secret_seven_roads_feast"],
        ),
    )
    return items, recipes


def _register_items(items: tuple[ItemDefinition, ...]) -> None:
    additions = tuple(item for item in items if item.key not in crafting.ITEMS_BY_KEY)
    if not additions:
        return
    crafting.ITEMS = crafting.ITEMS + additions
    crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})


def _register_fragrances(
    items: tuple[ItemDefinition, ...],
    fragrances: tuple[style.FragranceDefinition, ...],
) -> None:
    known_item_keys = {item.key for item in style.FRAGRANCE_ITEMS}
    item_additions = tuple(item for item in items if item.category == "fragrance" and item.key not in known_item_keys)
    if item_additions:
        style.FRAGRANCE_ITEMS = style.FRAGRANCE_ITEMS + item_additions

    known_fragrances = set(style.FRAGRANCE_BY_KEY)
    additions = tuple(fragrance for fragrance in fragrances if fragrance.item_key not in known_fragrances)
    if additions:
        style.FRAGRANCES = style.FRAGRANCES + additions
        style.FRAGRANCE_BY_KEY.update({fragrance.item_key: fragrance for fragrance in additions})


def _register_nodes(nodes: tuple[ResourceNodeDefinition, ...]) -> None:
    additions = tuple(node for node in nodes if node.key not in crafting.RESOURCE_NODES_BY_KEY)
    if not additions:
        return
    crafting.RESOURCE_NODES = crafting.RESOURCE_NODES + additions
    crafting.RESOURCE_NODES_BY_KEY.update({node.key: node for node in additions})


def _register_recipes(recipes: tuple[CraftingRecipe, ...]) -> None:
    by_profession: dict[str, list[CraftingRecipe]] = {}
    for recipe in recipes:
        by_profession.setdefault(recipe.trade_skill_key, []).append(recipe)

    attr_by_profession = {
        "blacksmithing": "BLACKSMITHING_RECIPES",
        "tailoring": "TAILORING_RECIPES",
        "alchemy": "ALCHEMY_RECIPES",
        "enchanting": "ENCHANTING_RECIPES",
        "cooking": "COOKING_RECIPES",
    }
    for profession, rows in by_profession.items():
        attr = attr_by_profession[profession]
        existing = tuple(getattr(crafting, attr, ()))
        existing_keys = {recipe.key for recipe in existing}
        additions = tuple(recipe for recipe in rows if recipe.key not in existing_keys)
        if additions:
            setattr(crafting, attr, existing + additions)
        by_key_attr = attr + "_BY_KEY"
        table = dict(getattr(crafting, by_key_attr, {}))
        table.update({recipe.key: recipe for recipe in additions})
        setattr(crafting, by_key_attr, table)

    known = set(crafting.RECIPES_BY_KEY)
    additions = tuple(recipe for recipe in recipes if recipe.key not in known)
    if additions:
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in additions})


def _install_world_access() -> None:
    for ingredient in PANTRY_INGREDIENTS:
        current = economy.ROOM_RESOURCE_NODE_KEYS.get(ingredient.room_key, ())
        if ingredient.node_key not in current:
            economy.ROOM_RESOURCE_NODE_KEYS[ingredient.room_key] = current + (ingredient.node_key,)

    economy.STATION_LABELS.setdefault("perfumer_bench", "Perfumer's Bench")

    station_additions = {
        "waymeet_hammer_thread_row": ("forge", "loom", "enchanting_table", "perfumer_bench"),
        "waymeet_commonhouse_yard": ("cookfire",),
        "veyra_hammer_hall": ("forge", "enchanting_table"),
        "veyra_loom_hall": ("loom",),
        "veyra_greenhall": ("mortar_and_pestle", "alchemy_table", "perfumer_bench"),
        "veyra_scholars_rise": ("enchanting_table", "alchemy_table"),
        "veyra_public_hearth": ("cookfire",),
        "sablewater_reed_farms": ("cookfire",),
        "greywake_lantern_hospice": ("mortar_and_pestle", "alchemy_table", "perfumer_bench", "cookfire"),
        "forest_elf_hearthwalk": ("perfumer_bench",),
        "goblin_apothecary_blind": ("perfumer_bench",),
    }
    for room_key, station_keys in station_additions.items():
        current = economy.ROOM_STATIONS.get(room_key, ())
        economy.ROOM_STATIONS[room_key] = current + tuple(key for key in station_keys if key not in current)


def production_recipe_counts() -> dict[str, int]:
    return {
        profession.key: sum(1 for recipe in crafting.ALL_RECIPES if recipe.trade_skill_key == profession.key)
        for profession in crafting.PROFESSIONS
    }


def validate_profession_expansion() -> dict[str, int]:
    missing_materials = sorted(
        {
            requirement.item_key
            for recipe in crafting.ALL_RECIPES
            for requirement in recipe.materials
            if requirement.item_key not in crafting.ITEMS_BY_KEY
        }
    )
    missing_outputs = sorted(
        {
            recipe.output_item_key
            for recipe in crafting.ALL_RECIPES
            if recipe.output_item_key not in crafting.ITEMS_BY_KEY
        }
    )
    if missing_materials or missing_outputs:
        raise RuntimeError(
            f"Profession expansion has missing materials={missing_materials} outputs={missing_outputs}"
        )
    counts = production_recipe_counts()
    thin = {key: count for key, count in counts.items() if count < 80}
    if thin:
        raise RuntimeError(f"Every crafting profession must have at least 80 recipes: {thin}")

    perfume_recipes = [
        recipe for recipe in crafting.ALL_RECIPES
        if recipe.trade_skill_key == "alchemy" and recipe.design_status.startswith("perfumery_")
    ]
    if len(perfume_recipes) < 51:
        raise RuntimeError(f"Perfumery must expose at least 51 Alchemy recipes, found {len(perfume_recipes)}")
    missing_fragrance_definitions = sorted(
        recipe.output_item_key
        for recipe in perfume_recipes
        if recipe.design_status != "perfumery_concentrate"
        and recipe.output_item_key not in style.FRAGRANCE_BY_KEY
    )
    if missing_fragrance_definitions:
        raise RuntimeError(f"Perfumery outputs are missing fragrance behavior: {missing_fragrance_definitions}")
    return counts


def install_profession_expansion_content() -> dict[str, int]:
    if getattr(crafting, "_deep_profession_expansion_installed", False):
        return production_recipe_counts()

    workshops.install_missing_profession_content()

    blacksmith_items, blacksmith_recipes = _blacksmithing_expansion()
    tailoring_items, tailoring_recipes = _tailoring_expansion()
    alchemy_items, alchemy_recipes = _alchemy_expansion()
    pantry_items, pantry_nodes = _pantry_content()
    cooking_items, cooking_recipes = _cooking_expansion()
    enchanting_items, enchanting_recipes = _enchanting_expansion()
    perfume_items, perfume_recipes, perfume_fragrances = _perfumery_expansion()
    secret_items, secret_recipes = _secret_content()

    all_items = (
        blacksmith_items
        + tailoring_items
        + alchemy_items
        + pantry_items
        + cooking_items
        + enchanting_items
        + perfume_items
        + secret_items
    )
    all_recipes = (
        blacksmith_recipes
        + tailoring_recipes
        + alchemy_recipes
        + cooking_recipes
        + enchanting_recipes
        + perfume_recipes
        + secret_recipes
    )

    _register_items(all_items)
    _register_fragrances(perfume_items, perfume_fragrances)
    _register_nodes(pantry_nodes)
    _register_recipes(all_recipes)
    _install_world_access()

    crafting._deep_profession_expansion_installed = True
    return validate_profession_expansion()


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _resolve_drink(session, target: str) -> tuple[ItemDefinition | None, str | None]:
    wanted = _normalize(target)
    candidates: list[tuple[int, ItemDefinition]] = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if item is None or item.consumable is None or item.consumable.use_mode != "drink":
            continue
        names = {_normalize(item.key), _normalize(item.name)}
        quality = 2 if wanted in names else 1 if wanted and any(wanted in name for name in names) else 0
        if quality:
            candidates.append((quality, item))
    if not candidates:
        return None, "You are not carrying a drinkable crafted preparation by that name."
    best = max(quality for quality, _item in candidates)
    unique = {item.key: item for quality, item in candidates if quality == best}
    if len(unique) != 1:
        return None, "Be more specific: " + ", ".join(item.name for item in unique.values()) + "."
    return next(iter(unique.values())), None


async def _drink(session, target: str) -> None:
    item, error = _resolve_drink(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert item is not None and item.consumable is not None
    if not session.database.consume_item(session.character.id, item.key, 1):
        await session.send("That preparation is no longer in your inventory.\r\n")
        return

    effect = item.consumable
    combatant = getattr(session, "combatant", None)
    healed = 0
    duration = 0.0
    if combatant is not None:
        before = combatant.current_hp
        combatant.current_hp = min(combatant.max_hp, combatant.current_hp + max(0, effect.heal_hp))
        healed = combatant.current_hp - before

        bonus = effect.temporary_stat_bonuses
        if effect.duration_ticks > 0 and bonus != CharacterStats():
            combatant.stats = combatant.stats.plus(bonus)
            combatant.max_hp += max(0, bonus.hp)
            combatant.max_mana += max(0, bonus.mana_bonus)
            duration = effect.duration_ticks * workshops.FOOD_TICK_SECONDS
            task = asyncio.create_task(workshops._expire_food_bonus(session, item.name, bonus, duration))
            tasks = getattr(session, "_consumable_effect_tasks", None)
            if tasks is None:
                tasks = set()
                session._consumable_effect_tasks = tasks
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    text = f"You drink {item.name}."
    if healed:
        text += f" You recover {healed} HP."
    if duration:
        text += f" Its temporary effect lasts about {int(duration)} seconds."
    await session.send(text + "\r\n")
    sender = getattr(session, "send_client_state", None)
    if callable(sender):
        await sender()


async def _show_potions(session) -> None:
    rows: list[tuple[ItemDefinition, int]] = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if item is None or item.consumable is None or item.consumable.use_mode != "drink":
            continue
        rows.append((item, int(row["quantity"])))

    await session.send("\r\n=== POTIONS & ELIXIRS ===\r\n")
    if not rows:
        await session.send("You are not carrying any drinkable crafted preparations.\r\n")
        return
    for item, quantity in rows:
        await session.send(f"  {quantity}x {item.name} - {item.description}\r\n")
    await session.send("\r\nUse DRINK <name>.\r\n")


async def _show_perfumery(session) -> None:
    recipes = [
        recipe
        for recipe in crafting.ALL_RECIPES
        if recipe.trade_skill_key == "alchemy"
        and recipe.design_status.startswith("perfumery_")
        and economy._recipe_visible(session, recipe)
    ]
    recipes.sort(key=lambda recipe: (recipe.trivial_skill, economy._recipe_output_name(recipe).lower()))

    await session.send("\r\n=== PERFUMERY - ALCHEMY SPECIALIZATION ===\r\n")
    await session.send(
        "Perfumes are wearable XP consumables: one scent can be active at a time, "
        "a new application replaces the old one, and bonuses affect character XP only - never tradeskill XP.\r\n"
    )

    current_tier = None
    for recipe in recipes:
        output = crafting.ITEMS_BY_KEY[recipe.output_item_key]
        tier = max(1, output.tier)
        if tier != current_tier:
            current_tier = tier
            bonus, seconds = PERFUME_TIER_EFFECTS[tier]
            await session.send(
                f"\r\nTier {tier} - +{bonus}% character XP for {seconds // 60} real minutes\r\n"
            )
        await session.send(economy._recipe_line(session, recipe))

    await session.send(
        "\r\nUse RECIPE <name> for ingredients, CRAFT <name> at a Perfumer's Bench, "
        "PERFUMES to list carried bottles, and APPLY PERFUME <name> or SPRAY <name> to use one.\r\n"
    )


async def _show_recipe_summary(session) -> None:
    visible = [
        recipe
        for recipe in crafting.ALL_RECIPES
        if economy._recipe_visible(session, recipe)
    ]
    await session.send("\r\n=== TRADESKILL RECIPE SUMMARY ===\r\n")
    for profession in crafting.PROFESSIONS:
        count = sum(1 for recipe in visible if recipe.trade_skill_key == profession.key)
        total = sum(1 for recipe in crafting.ALL_RECIPES if recipe.trade_skill_key == profession.key)
        hidden = total - count
        suffix = f" (+{hidden} undiscovered)" if hidden else ""
        await session.send(f"  {profession.name:<16} {count:>3} known recipes{suffix}\r\n")
    await session.send("Undiscovered secret recipes do not appear in ordinary recipe lists.\r\n")


_SECRET_DISCOVERIES = {
    ("human_cinder_lane", "examine anvil"): (
        SECRET_RECIPE_FLAGS["secret_fallen_star_greatblade"],
        "secret_fallen_star_greatblade",
        "Under old scale on the anvil face, you notice a narrow groove showing how two different metals can be seam-forged after the blade is already shaped.",
    ),
    ("human_cinder_lane", "examine blackened anvil"): (
        SECRET_RECIPE_FLAGS["secret_fallen_star_greatblade"],
        "secret_fallen_star_greatblade",
        "Under old scale on the anvil face, you notice a narrow groove showing how two different metals can be seam-forged after the blade is already shaped.",
    ),
    ("forest_elf_hearthwalk", "examine loom"): (
        SECRET_RECIPE_FLAGS["secret_astral_dreamcloak"],
        "secret_astral_dreamcloak",
        "A nearly invisible set of tension marks on the loom suggests a cloak pattern that is cut only after the cloth has been stretched under load.",
    ),
    ("goblin_apothecary_blind", "examine mortar"): (
        SECRET_RECIPE_FLAGS["secret_one_breath_elixir"],
        "secret_one_breath_elixir",
        "The old mortar has a second grinding channel hidden beneath its lip, sized for suspending mineral catalyst instead of crushing herbs.",
    ),
    ("dwarf_workshop_tier", "examine runic workbench"): (
        SECRET_RECIPE_FLAGS["secret_last_door_focus"],
        "secret_last_door_focus",
        "One scarred corner of the runic bench carries a deliberately blank center surrounded by two complete binding rings. The omission is the technique.",
    ),
    ("veyra_public_hearth", "examine hearth tiles"): (
        SECRET_RECIPE_FLAGS["secret_seven_roads_feast"],
        "secret_seven_roads_feast",
        "Tiny ingredient marks scratched into eight hearth tiles form an old cook's mnemonic for balancing foods gathered from distant roads.",
    ),
    ("greywake_riftfield", "examine fallen star"): (
        SECRET_RECIPE_FLAGS["secret_perfume_fallen_star_no7"],
        "secret_perfume_fallen_star_no7",
        "A sharp metallic scent rises from a glassy stone seam. Scratched measurements beside it describe a seven-stage cold infusion rather than a mining assay.",
    ),
    ("gravewatch_chapel_nave", "examine funerary incense"): (
        SECRET_RECIPE_FLAGS["secret_perfume_queens_funeral"],
        "secret_perfume_queens_funeral",
        "The old incense formula is written as a memorial prayer, but the repeated quantities resolve into a complete perfume accord when read as an alchemist's ratio.",
    ),
    ("goblin_apothecary_blind", "examine perfume ledger"): (
        SECRET_RECIPE_FLAGS["secret_perfume_brassgut_nocturne"],
        "secret_perfume_brassgut_nocturne",
        "A grease-stained ledger hides an unsigned night-market perfume formula between ordinary salvage invoices. The measurements are precise enough to reproduce.",
    ),
}


async def _discover_secret(session, normalized: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    row = _SECRET_DISCOVERIES.get((character.current_room or "", normalized))
    if row is None:
        return False
    flag, recipe_key, flavor = row
    known = set(session.database.list_flags(character.id))
    recipe = crafting.RECIPES_BY_KEY[recipe_key]
    if flag not in known:
        session.database.grant_flag(character.id, flag)
        await session.send(flavor + "\r\n")
        await session.send(f"Secret recipe discovered: {economy._recipe_output_name(recipe)}.\r\n")
    else:
        await session.send("You recognize the hidden technique you already copied from here.\r\n")
    await economy._show_recipe_detail(session, economy._recipe_output_name(recipe))
    return True


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    prior = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = prior
        else:
            self.__dict__.pop("prompt", None)


def _live_prompt(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_profession_expansion_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_deep_profession_runtime_installed", False):
        return

    install_profession_expansion_content()
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt(_live_prompt(self))
        if command is None:
            await previous_playing_prompt(self)
            return

        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"potions", "elixirs", "alchemy drinks"}:
            await _show_potions(self)
            return
        if normalized in {"perfumery", "perfume recipes", "perfumes recipes", "recipes perfume", "recipes perfumes", "recipes perfumery"}:
            await _show_perfumery(self)
            return
        if normalized == "drink":
            await self.send("Use DRINK <potion or elixir>. Type POTIONS to see what you are carrying.\r\n")
            return
        if normalized.startswith("drink "):
            await _drink(self, stripped.split(maxsplit=1)[1])
            return
        if normalized in {"recipes summary", "recipe summary", "recipe counts", "recipes counts"}:
            await _show_recipe_summary(self)
            return
        if await _discover_secret(self, normalized):
            return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._deep_profession_runtime_installed = True
