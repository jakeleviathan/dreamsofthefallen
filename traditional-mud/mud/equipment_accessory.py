from __future__ import annotations

import mud.equipment_system as equipment


ACCESSORY_SLOT_KEY = "accessory"

ACCESSORY_SLOT_ALIASES: dict[str, str] = {
    "accessory": ACCESSORY_SLOT_KEY,
    "acc": ACCESSORY_SLOT_KEY,
    "charm": ACCESSORY_SLOT_KEY,
    "amulet": ACCESSORY_SLOT_KEY,
    "neck": ACCESSORY_SLOT_KEY,
    "necklace": ACCESSORY_SLOT_KEY,
    "pendant": ACCESSORY_SLOT_KEY,
    "ring": ACCESSORY_SLOT_KEY,
}


def install_accessory_slot() -> None:
    """Extend the live equipment model with one universal accessory slot.

    Dreams of the Fallen intentionally uses a single accessory slot rather than
    separate ring/neck/trinket slots in the first equipment pass. Individual
    accessories remain ordinary stat gear unless a future rare/endgame item
    explicitly opts into the existing scripted-effect hook.
    """
    if ACCESSORY_SLOT_KEY not in equipment.EQUIPMENT_SLOTS:
        equipment.EQUIPMENT_SLOTS = equipment.EQUIPMENT_SLOTS + (ACCESSORY_SLOT_KEY,)

    equipment.SLOT_LABELS[ACCESSORY_SLOT_KEY] = "Accessory"
    equipment._SLOT_ALIASES.update(ACCESSORY_SLOT_ALIASES)


def install_accessory_runtime(player_session_class) -> None:
    """Add the accessory-slot login reminder outside the equipment runtime."""
    install_accessory_slot()
    if getattr(player_session_class, "_accessory_slot_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is not None:
            await self.send(
                "Accessory slot active: one ACCESSORY can be worn at a time. "
                "Rings, charms, amulets, necklaces, and pendants all use this same slot.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class._accessory_slot_runtime_installed = True
