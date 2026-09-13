from __future__ import annotations

import mud.economy_loop as economy
from mud.midgame_three_roads import (
    DWARF_DRILL_KEY,
    MERIDIAN_CUSTODIAN_KEY,
    MERIDIAN_TROPHY_KEY,
    MOON_WARDEN_KEY,
    TROLL_RAVAGER_KEY,
)


def apply_midgame_three_roads_tuning() -> None:
    """Keep the new boss tables inside the canonical item registry.

    The three regional bosses intentionally feed materials already understood by
    the economy instead of introducing one-off placeholder item keys. The final
    Meridian boss retains its authored trophy drop.
    """

    economy.LOOT_TABLES[TROLL_RAVAGER_KEY] = (economy.LootDrop("bone_chips", 2),)
    economy.LOOT_TABLES[DWARF_DRILL_KEY] = (economy.LootDrop("iron_ore", 3),)
    economy.LOOT_TABLES[MOON_WARDEN_KEY] = (economy.LootDrop("moonsilver_ore", 1),)
    economy.LOOT_TABLES[MERIDIAN_CUSTODIAN_KEY] = (economy.LootDrop(MERIDIAN_TROPHY_KEY, 1),)
