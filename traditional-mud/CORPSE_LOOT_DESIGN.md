# Corpse Loot Runtime

Monster item rewards are physical room objects rather than automatic inventory grants.

- XP and quest credit still resolve immediately on the kill.
- Ordinary monster corpses persist for 5 minutes; named/boss-like corpses persist for 15 minutes unless content registers an override.
- Loot is protected for 60 seconds. Party loot assignment is honored during that window; after it expires, anything left becomes public.
- `LOOT CORPSE`, `GET/TAKE ALL FROM ...`, and `GET/TAKE <item> FROM ...` move items from the corpse into inventory.
- `LOOK/EXAMINE CORPSE` shows the contents and current protection state.
- `CORPSES` lists persistent remains in the room.
- Capacity-aware clients/runtimes can expose `can_receive_item`; blocked items remain on the corpse.
- Ground drops and corpse contents use the same atomic item-location transfer layer.
- Static-spawn lifecycle claims and persistent death keys prevent duplicate corpses/rewards from concurrent kills.
- Existing guaranteed and secondary economy drops are automatically adapted into the data-driven percentage/quantity loot-table model. New content can register explicit `LootTableEntry` tables.

Quest rewards and authored personal rewards are not redirected into corpses.
