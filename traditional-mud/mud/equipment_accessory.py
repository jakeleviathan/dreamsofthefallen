from __future__ import annotations

import mud.equipment_system as equipment
from mud.combat_variance import install_combat_variance_runtime


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


# Equipment owns the production SCORE command. Keep a stable reference to its
# original renderer, then make the accessory layer clarify derived resources
# without duplicating the rest of the character-sheet implementation.
_BASE_SHOW_LIVE_STATS = equipment._show_live_stats


def _clarify_score_text(session, text: str) -> str:
    """Add live vitals and distinguish the HP attribute from current Health."""
    character = getattr(session, "character", None)
    if character is None:
        return text

    combatant = getattr(session, "combatant", None)
    if combatant is not None:
        vitals = (
            "\r\n--- Vitals (current / maximum) ---\r\n"
            f"Health   : {combatant.current_hp} / {combatant.max_hp}\r\n"
            f"Mana     : {combatant.current_mana} / {combatant.max_mana}\r\n"
            f"Movement : {combatant.current_movement} / {combatant.max_movement}\r\n"
            "\r\n--- Attributes (base + equipment = total) ---\r\n"
        )
        text = text.replace(
            "\r\n--- Stats (base + equipment = total) ---\r\n",
            vitals,
            1,
        )
    else:
        text = text.replace(
            "\r\n--- Stats (base + equipment = total) ---\r\n",
            "\r\n--- Attributes (base + equipment = total) ---\r\n",
            1,
        )

    bonus, _armor_class = equipment.equipment_totals(session.database, character.id)
    total = character.stats.plus(bonus)
    old_hp_line = f"HP   : {character.hp_stat} {bonus.hp:+d} = {total.hp}\r\n"
    new_hp_line = (
        f"HP stat: {character.hp_stat} {bonus.hp:+d} = {total.hp}  "
        f"(adds +{total.hp} to maximum Health)\r\n"
    )
    text = text.replace(old_hp_line, new_hp_line, 1)
    text = text.replace(
        "Mana bonus:",
        "Mana bonus from Love + Mind:",
        1,
    )
    return text


async def _show_live_stats_with_vitals(session) -> None:
    """Render SCORE with live resource totals from the same combat state as the HUD."""
    original_send = session.send
    captured: list[str] = []
    had_instance_send = "send" in session.__dict__
    prior_instance_send = session.__dict__.get("send")

    async def capture(text: str) -> None:
        captured.append(text)

    session.send = capture
    try:
        await _BASE_SHOW_LIVE_STATS(session)
    finally:
        if had_instance_send:
            session.send = prior_instance_send
        else:
            session.__dict__.pop("send", None)

    for text in captured:
        await original_send(_clarify_score_text(session, text))


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
    """Add the accessory slot, clarify SCORE, and finalize weapon-aware combat damage."""
    install_accessory_slot()

    # Equipment's command wrapper resolves this module-global renderer at command
    # time, so replacing it here makes SCORE clearer without adding another
    # competing command owner. Vitals come directly from CombatantState, exactly
    # like the HUD/client-state path, while the HP stat remains an attribute.
    equipment._show_live_stats = _show_live_stats_with_vitals

    # Equipment is fully installed immediately before this layer in production.
    # Finalize combat damage here so the live main-hand item can own its damage
    # profile while later quest/class wrappers keep using the same combat API.
    install_combat_variance_runtime(player_session_class)

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
