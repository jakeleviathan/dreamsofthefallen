from __future__ import annotations

import mud.crafting as crafting
import mud.economy_balance as economy_balance
import mud.economy_loop as economy
from mud.party_system import _encounter_for, _loot_recipient


_INSTALLED = False
_ORIGINAL_BASE_AWARD = None
_ORIGINAL_SECONDARY_AWARD = None


async def _announce_distribution(killer, recipient, label: str, names: list[str]) -> None:
    if not names:
        return
    text = ", ".join(names)
    if recipient is killer:
        await killer.send(f"{label}: {text}.\r\n")
        return
    recipient_character = getattr(recipient, "character", None)
    recipient_name = recipient_character.name if recipient_character is not None else "a party member"
    await killer.send(f"Party {label.lower()}: {text} -> {recipient_name}.\r\n")
    await recipient.send(f"[Party Loot] You receive {text}.\r\n")


async def _party_base_award(session, enemy) -> None:
    if _encounter_for(enemy) is None:
        await _ORIGINAL_BASE_AWARD(session, enemy)
        return
    character = getattr(session, "character", None)
    if character is None:
        return
    for drop in economy._loot_for(enemy):
        recipient = _loot_recipient(session, enemy, drop.item_key)
        recipient_character = getattr(recipient, "character", None)
        if recipient_character is None:
            recipient = session
            recipient_character = character
        recipient.database.add_item(recipient_character.id, drop.item_key, drop.quantity)
        definition = crafting.ITEMS_BY_KEY.get(drop.item_key)
        name = definition.name if definition is not None else drop.item_key
        await _announce_distribution(session, recipient, "Loot", [f"{drop.quantity}x {name}"])


async def _party_secondary_award(session, enemy) -> None:
    if _encounter_for(enemy) is None:
        await _ORIGINAL_SECONDARY_AWARD(session, enemy)
        return
    character = getattr(session, "character", None)
    if character is None:
        return
    for drop in economy_balance._secondary_for_enemy(enemy):
        if economy_balance.random() > drop.chance:
            continue
        recipient = _loot_recipient(session, enemy, drop.item_key)
        recipient_character = getattr(recipient, "character", None)
        if recipient_character is None:
            recipient = session
            recipient_character = character
        recipient.database.add_item(recipient_character.id, drop.item_key, drop.quantity)
        definition = crafting.ITEMS_BY_KEY.get(drop.item_key)
        name = definition.name if definition is not None else drop.item_key
        await _announce_distribution(session, recipient, "Bonus loot", [f"{drop.quantity}x {name}"])


def install_party_loot_hooks() -> None:
    """Make existing economy drops obey the party's transient loot mode.

    Only monster loot is redirected. Quest rewards, crafted goods, and authored
    one-time rewards stay personal to the character who earned them.
    """
    global _INSTALLED, _ORIGINAL_BASE_AWARD, _ORIGINAL_SECONDARY_AWARD
    if _INSTALLED:
        return
    _ORIGINAL_BASE_AWARD = economy._award_loot
    _ORIGINAL_SECONDARY_AWARD = economy_balance._award_secondary_loot
    economy._award_loot = _party_base_award
    economy_balance._award_secondary_loot = _party_secondary_award
    _INSTALLED = True
