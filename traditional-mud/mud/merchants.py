from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MerchantStockEntry:
    """An item a merchant normally keeps available.

    Prices are stored in sparks, the base denomination of Astralis's Sol
    currency. A merchant may omit a price to use the catalog-derived baseline.
    """

    item_key: str
    common_stock: bool = False
    price_units: int | None = None


# Bone Chips are intentionally ubiquitous so a level-2 Necromancer is not
# locked out of its defining pet because of rare catalyst availability.
COMMON_MERCHANT_STOCK: tuple[MerchantStockEntry, ...] = (
    MerchantStockEntry("bone_chips", common_stock=True, price_units=3),
)
COMMON_MERCHANT_STOCK_BY_KEY = {entry.item_key: entry for entry in COMMON_MERCHANT_STOCK}


@dataclass(frozen=True, slots=True)
class MerchantDefinition:
    npc_key: str
    additional_stock: tuple[MerchantStockEntry, ...] = ()
    uses_common_stock: bool = True

    @property
    def stock(self) -> tuple[MerchantStockEntry, ...]:
        common = COMMON_MERCHANT_STOCK if self.uses_common_stock else ()
        seen: set[str] = set()
        merged: list[MerchantStockEntry] = []
        for entry in (*common, *self.additional_stock):
            if entry.item_key in seen:
                continue
            seen.add(entry.item_key)
            merged.append(entry)
        return tuple(merged)

    def sells(self, item_key: str) -> bool:
        return any(entry.item_key == item_key for entry in self.stock)


# This is the first authored merchant in the current room world. Future normal
# merchants should default to uses_common_stock=True unless there is a reason
# their inventory is deliberately unusual.
ASHEN_WAY_CURIO_PEDDLER_MERCHANT = MerchantDefinition("ashen_way_curio_peddler")

# Waymeet predates the universal merchant layer and originally traded in local
# scrip. Its static market NPCs now participate in the same Sol economy while
# preserving their distinct raw-vs-processed stock identities.
WAYMEET_VEKK_MERCHANT = MerchantDefinition(
    "waymeet_broker_nix_coil",
    additional_stock=(
        MerchantStockEntry("iron_ore", price_units=4),
        MerchantStockEntry("raw_cotton", price_units=4),
        MerchantStockEntry("greenleaf", price_units=4),
        MerchantStockEntry("coal", price_units=4),
    ),
    uses_common_stock=False,
)
WAYMEET_SEVRA_MERCHANT = MerchantDefinition(
    "waymeet_provisioner_sevra_lent",
    additional_stock=(
        MerchantStockEntry("iron_ingot", price_units=8),
        MerchantStockEntry("cotton_thread", price_units=8),
    ),
    uses_common_stock=False,
)

# Starter-city merchants. These turn authored market/shop scenery into usable
# Sol economy endpoints instead of leaving them as descriptive placeholders.
GOBLIN_BRASSGUT_MERCHANT = MerchantDefinition(
    "goblin_ruskle_coil",
    additional_stock=(
        MerchantStockEntry("iron_ore", price_units=4),
        MerchantStockEntry("coal", price_units=4),
        MerchantStockEntry("raw_cotton", price_units=4),
        MerchantStockEntry("bone_chips", price_units=3),
    ),
)

UNDEAD_CHISEL_MERCHANT = MerchantDefinition(
    "undead_bonewright_kell",
    additional_stock=(
        MerchantStockEntry("bone_chips", price_units=3),
        MerchantStockEntry("iron_ore", price_units=4),
        MerchantStockEntry("coal", price_units=4),
    ),
)

MERCHANTS: tuple[MerchantDefinition, ...] = (
    ASHEN_WAY_CURIO_PEDDLER_MERCHANT,
    WAYMEET_VEKK_MERCHANT,
    WAYMEET_SEVRA_MERCHANT,
    GOBLIN_BRASSGUT_MERCHANT,
    UNDEAD_CHISEL_MERCHANT,
)
MERCHANTS_BY_NPC_KEY = {merchant.npc_key: merchant for merchant in MERCHANTS}
