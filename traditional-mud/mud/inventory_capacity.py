from __future__ import annotations

from dataclasses import dataclass

import mud.crafting as crafting
import mud.equipment_system as equipment
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import EquipmentItem


BASE_INVENTORY_SLOTS = 20
BAG_SLOT_KEY = "bag"


@dataclass(frozen=True, slots=True)
class BagDefinition:
    key: str
    name: str
    extra_slots: int
    tier: int
    description: str


BAGS: tuple[BagDefinition, ...] = (
    BagDefinition(
        "bag_brassgut_salvage_sack",
        "Brassgut Salvage Sack",
        6,
        1,
        "A squat patched sack with too many reinforced seams and exactly enough structure to keep scrap from escaping through the bottom.",
    ),
    BagDefinition(
        "bag_blackwall_road_satchel",
        "Blackwall Road Satchel",
        8,
        1,
        "A practical dark canvas satchel issued in Human road districts, with broad straps and waxed inner pockets.",
    ),
    BagDefinition(
        "bag_greenway_forager_pack",
        "Greenway Forager Pack",
        8,
        1,
        "A light barkcloth-and-hide pack made to sit close to the body while moving through roots and low branches.",
    ),
    BagDefinition(
        "bag_chainmark_tool_pack",
        "Chainmark Tool Pack",
        10,
        1,
        "A compact Dwarven work pack with reinforced corners, numbered loops, and an aggressively sensible weight distribution.",
    ),
    BagDefinition(
        "bag_frostroot_hide_pack",
        "Frostroot Hide Pack",
        10,
        1,
        "A broad hide pack sewn for cold-weather travel, with thick straps that remain flexible after freezing.",
    ),
    BagDefinition(
        "bag_moonstep_travelers_bag",
        "Moonstep Traveler's Bag",
        12,
        2,
        "A pale high-road travel bag with layered inner folds that keep small items from shifting on steep climbs.",
    ),
    BagDefinition(
        "bag_gravecloth_courier_bag",
        "Gravecloth Courier Bag",
        12,
        2,
        "A severe black courier bag of waxed gravecloth, built to keep documents and tools dry below ground.",
    ),
    BagDefinition(
        "bag_lumen_sporewoven_pack",
        "Lumen Sporewoven Pack",
        12,
        2,
        "A flexible fungal-fiber pack whose woven walls spring back into shape after being compressed.",
    ),
    BagDefinition(
        "bag_waymeet_caravan_pack",
        "Waymeet Caravan Pack",
        14,
        2,
        "A road-tested caravan pack with replaceable straps, a rain flap, and enough loops to survive several owners.",
    ),
    BagDefinition(
        "bag_wool_trail_pack",
        "Wool Trail Pack",
        14,
        2,
        "A warm felted travel pack with a cloth-lined interior and reinforced carrying straps.",
    ),
    BagDefinition(
        "bag_silk_expedition_pack",
        "Silk Expedition Pack",
        18,
        3,
        "A deceptively light expedition pack whose layered silk panels distribute bulky loads without sagging.",
    ),
    BagDefinition(
        "bag_moonweave_expedition_pack",
        "Moonweave Expedition Pack",
        22,
        4,
        "A pale, close-fitting expedition pack that seems to carry its shape even when crowded with gear.",
    ),
    BagDefinition(
        "bag_spidersilk_delver_pack",
        "Spidersilk Delver Pack",
        26,
        5,
        "A deep delver's pack reinforced with spidersilk webbing strong enough to tolerate rough stone and heavy tools.",
    ),
    BagDefinition(
        "bag_ghostweave_pilgrim_pack",
        "Ghostweave Pilgrim Pack",
        30,
        6,
        "A quiet pale pack of layered ghostweave whose many internal ties keep fragile relics from knocking together.",
    ),
    BagDefinition(
        "bag_astralweave_wayfarer_pack",
        "Astralweave Wayfarer Pack",
        36,
        7,
        "A masterwork wayfarer's pack woven from Astral Bloom fiber, extraordinarily strong without becoming bulky.",
    ),
)
BAGS_BY_KEY = {bag.key: bag for bag in BAGS}


def _bag_item(bag: BagDefinition) -> ItemDefinition:
    return ItemDefinition(
        key=bag.key,
        name=bag.name,
        description=bag.description,
        category="equipment",
        equipment=EquipmentItem(
            name=bag.name,
            slot=BAG_SLOT_KEY,
            inventory_slots=bag.extra_slots,
        ),
        tier=bag.tier,
    )


BAG_ITEMS: tuple[ItemDefinition, ...] = tuple(_bag_item(bag) for bag in BAGS)


def _bag_recipe(
    bag_key: str,
    material_key: str,
    trivial: int,
    *,
    material_quantity: int = 3,
) -> CraftingRecipe:
    bag = BAGS_BY_KEY[bag_key]
    return CraftingRecipe(
        key=f"sew_{bag_key}",
        trade_skill_key="tailoring",
        output_item_key=bag_key,
        minimum_skill=trivial,
        high_skill_quality_threshold=trivial + 30,
        materials=(MaterialRequirement(material_key, material_quantity),),
        output_quantity=1,
        station_key="loom",
        description=f"Sew a reinforced {bag.name} for long-distance carrying.",
        design_status="live_inventory_capacity_progression",
    )


BAG_RECIPES: tuple[CraftingRecipe, ...] = (
    _bag_recipe("bag_wool_trail_pack", "wool_cloth", 18),
    _bag_recipe("bag_silk_expedition_pack", "silk_cloth", 33),
    _bag_recipe("bag_moonweave_expedition_pack", "moonweave_cloth", 53),
    _bag_recipe("bag_spidersilk_delver_pack", "spidersilk_cloth", 78),
    _bag_recipe("bag_ghostweave_pilgrim_pack", "ghostweave_cloth", 108),
    _bag_recipe("bag_astralweave_wayfarer_pack", "astralweave_cloth", 143),
)


def install_bag_slot() -> None:
    if BAG_SLOT_KEY not in equipment.EQUIPMENT_SLOTS:
        equipment.EQUIPMENT_SLOTS = equipment.EQUIPMENT_SLOTS + (BAG_SLOT_KEY,)
    equipment.SLOT_LABELS[BAG_SLOT_KEY] = "Bag"
    equipment._SLOT_ALIASES.update(
        {
            "bag": BAG_SLOT_KEY,
            "pack": BAG_SLOT_KEY,
            "backpack": BAG_SLOT_KEY,
            "satchel": BAG_SLOT_KEY,
            "sack": BAG_SLOT_KEY,
        }
    )


def install_bag_content() -> None:
    known_items = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in BAG_ITEMS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})

    known_tailoring = set(crafting.TAILORING_RECIPES_BY_KEY)
    recipe_additions = tuple(recipe for recipe in BAG_RECIPES if recipe.key not in known_tailoring)
    if recipe_additions:
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + recipe_additions
        crafting.TAILORING_RECIPES_BY_KEY.update({recipe.key: recipe for recipe in recipe_additions})
        crafting.ALL_RECIPES = crafting.ALL_RECIPES + recipe_additions
        crafting.RECIPES_BY_KEY.update({recipe.key: recipe for recipe in recipe_additions})


def _inventory_rows(database, character_id: int) -> list[dict[str, int | str]]:
    lister = getattr(database, "list_items", None)
    if callable(lister):
        return list(lister(character_id))

    # Lightweight test doubles used by some authored regional suites expose the
    # same inventory state as a {(character_id, item_key): quantity} mapping.
    raw = getattr(database, "items", None)
    if isinstance(raw, dict):
        return [
            {"item_key": str(item_key), "quantity": int(quantity)}
            for (owner, item_key), quantity in raw.items()
            if int(owner) == int(character_id) and int(quantity) > 0
        ]
    return []


def inventory_slots_used(database, character_id: int) -> int:
    return len(_inventory_rows(database, character_id))


def equipped_bag_bonus(database, character_id: int) -> int:
    if not callable(getattr(database, "connect", None)):
        return 0
    definition = equipment.equipped_definitions(database, character_id).get(BAG_SLOT_KEY)
    if definition is None or definition.equipment is None:
        return 0
    return max(0, int(definition.equipment.inventory_slots))


def inventory_slot_capacity(database, character_id: int) -> int:
    return BASE_INVENTORY_SLOTS + equipped_bag_bonus(database, character_id)


def inventory_capacity_status(database, character_id: int) -> tuple[int, int]:
    return inventory_slots_used(database, character_id), inventory_slot_capacity(database, character_id)


def slots_needed_for_item(database, character_id: int, item_key: str) -> int:
    quantity = getattr(database, "item_quantity", None)
    if callable(quantity):
        return 0 if quantity(character_id, item_key) > 0 else 1
    return 0 if any(str(row["item_key"]) == item_key for row in _inventory_rows(database, character_id)) else 1


def can_receive_item(database, character_id: int, item_key: str, quantity: int = 1) -> bool:
    if quantity <= 0:
        return True
    needed = slots_needed_for_item(database, character_id, item_key)
    if needed == 0:
        return True
    used, capacity = inventory_capacity_status(database, character_id)
    return used + needed <= capacity


def projected_trade_fits(
    database,
    character_id: int,
    *,
    incoming: dict[str, int],
    outgoing: dict[str, int],
) -> bool:
    rows = {str(row["item_key"]): int(row["quantity"]) for row in _inventory_rows(database, character_id)}
    for item_key, quantity in outgoing.items():
        if quantity <= 0:
            continue
        remaining = rows.get(item_key, 0) - quantity
        if remaining > 0:
            rows[item_key] = remaining
        else:
            rows.pop(item_key, None)
    for item_key, quantity in incoming.items():
        if quantity <= 0:
            continue
        rows[item_key] = rows.get(item_key, 0) + quantity
    return len(rows) <= inventory_slot_capacity(database, character_id)


def crafting_output_fits(database, character_id: int, recipe: CraftingRecipe) -> bool:
    rows = {str(row["item_key"]): int(row["quantity"]) for row in _inventory_rows(database, character_id)}
    for requirement in recipe.materials:
        remaining = rows.get(requirement.item_key, 0) - requirement.quantity
        if remaining > 0:
            rows[requirement.item_key] = remaining
        else:
            rows.pop(requirement.item_key, None)
    rows[recipe.output_item_key] = rows.get(recipe.output_item_key, 0) + recipe.output_quantity
    return len(rows) <= inventory_slot_capacity(database, character_id)


def capacity_message(database, character_id: int) -> str:
    used, capacity = inventory_capacity_status(database, character_id)
    if used > capacity:
        return (
            f"Inventory: {used}/{capacity} slots — OVERFULL. "
            "You can keep what you already carry, but cannot add a new item type until you free space or equip a larger bag."
        )
    return f"Inventory: {used}/{capacity} slots."


def install_inventory_capacity_runtime(player_session_class) -> None:
    install_bag_slot()
    install_bag_content()

    if getattr(player_session_class, "_inventory_capacity_runtime_installed", False):
        return

    def can_receive_item_for_session(self, item_key: str, quantity: int = 1) -> bool:
        character = getattr(self, "character", None)
        if character is None:
            return False
        return can_receive_item(self.database, character.id, item_key, quantity)

    player_session_class.can_receive_item = can_receive_item_for_session
    player_session_class._inventory_capacity_runtime_installed = True
