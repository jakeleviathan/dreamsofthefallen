from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MerchantStockEntry:
    """An item a merchant normally keeps available.

    Dreams of the Fallen has not finalized its currency name or economy yet, so
    stock availability is authored independently of price. This lets class
    mechanics depend on common merchant goods without silently inventing a
    permanent money system.
    """

    item_key: str
    common_stock: bool = False
    price_units: int | None = None


# Bone Chips are intentionally ubiquitous so a level-2 Necromancer is not
# locked out of its defining pet because of rare catalyst availability.
COMMON_MERCHANT_STOCK: tuple[MerchantStockEntry, ...] = (
    MerchantStockEntry("bone_chips", common_stock=True, price_units=None),
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

MERCHANTS: tuple[MerchantDefinition, ...] = (ASHEN_WAY_CURIO_PEDDLER_MERCHANT,)
MERCHANTS_BY_NPC_KEY = {merchant.npc_key: merchant for merchant in MERCHANTS}
