from __future__ import annotations

import mud.crafting as crafting


_SLOT_LABELS = {
    "head": "Head",
    "chest": "Chest",
    "legs": "Legs",
    "feet": "Feet",
    "hands": "Hands",
    "main_hand": "Main Hand",
    "main hand": "Main Hand",
    "weapon": "Main Hand",
    "off_hand": "Off Hand",
    "off hand": "Off Hand",
    "shield": "Off Hand",
    "accessory": "Accessory",
}


def _category_label(category: str) -> str:
    return category.replace("_", " ").strip().title() or "Item"


def _slot_label(raw_slot: str) -> str:
    normalized = raw_slot.strip().lower().replace("-", " ").replace("_", " ")
    return _SLOT_LABELS.get(normalized, normalized.title())


def _stat_parts(equipment) -> tuple[str, ...]:
    parts: list[str] = []
    armor_class = int(getattr(equipment, "armor_class", 0) or 0)
    if armor_class:
        parts.append(f"AC +{armor_class}")

    bonuses = getattr(equipment, "stat_bonuses", None)
    if bonuses is not None:
        for key, label in (
            ("might", "Might"),
            ("grace", "Grace"),
            ("love", "Love"),
            ("mind", "Mind"),
            ("hp", "HP"),
        ):
            value = int(getattr(bonuses, key, 0) or 0)
            if value:
                sign = "+" if value > 0 else ""
                parts.append(f"{label} {sign}{value}")
    return tuple(parts) or ("no stat modifiers",)


def _temporary_stat_parts(consumable) -> tuple[str, ...]:
    bonuses = getattr(consumable, "temporary_stat_bonuses", None)
    if bonuses is None:
        return ()
    parts: list[str] = []
    for key, label in (
        ("might", "Might"),
        ("grace", "Grace"),
        ("love", "Love"),
        ("mind", "Mind"),
        ("hp", "HP"),
    ):
        value = int(getattr(bonuses, key, 0) or 0)
        if value:
            sign = "+" if value > 0 else ""
            parts.append(f"{label} {sign}{value}")
    return tuple(parts)


def _owned_item(session, target: str):
    """Resolve an already-expanded inventory name without exposing internal keys."""

    if session.character is None:
        return None
    wanted = " ".join(target.strip().lower().split())
    for row in session.database.list_items(session.character.id):
        if int(row["quantity"]) <= 0:
            continue
        item_key = str(row["item_key"])
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        if definition is not None and definition.name.lower() == wanted:
            return definition
    return None


def item_detail_lines(session, definition) -> tuple[str, ...]:
    """Build truthful player-facing details for every inventory category."""

    quantity = session.database.item_quantity(session.character.id, definition.key)
    lines: list[str] = [
        "",
        definition.name,
        definition.description,
        f"Type: {_category_label(definition.category)}",
        f"Quantity: {quantity}",
    ]

    sell_value = merchant_buyback_price(definition.key)
    lines.append(f"Merchant value: {format_sols(sell_value)}" if sell_value > 0 else "Merchant value: not bought by ordinary merchants")

    if int(getattr(definition, "tier", 0) or 0) > 0:
        lines.append(f"Tier: {definition.tier}")

    equipment = getattr(definition, "equipment", None)
    if equipment is not None:
        lines.append(f"Slot: {_slot_label(equipment.slot)}")
        lines.append(f"Stats: {', '.join(_stat_parts(equipment))}")
        effects = tuple(getattr(equipment, "scripted_effects", ()) or ())
        if effects:
            lines.append("Special effects: " + ", ".join(effects))

    consumable = getattr(definition, "consumable", None)
    if consumable is not None:
        use_mode = str(getattr(consumable, "use_mode", "use") or "use")
        lines.append(f"Use: {use_mode.title()}")
        heal_hp = int(getattr(consumable, "heal_hp", 0) or 0)
        if heal_hp:
            lines.append(f"Restores: {heal_hp} HP")
        temporary = _temporary_stat_parts(consumable)
        if temporary:
            lines.append("Temporary bonuses: " + ", ".join(temporary))
        duration = int(getattr(consumable, "duration_ticks", 0) or 0)
        if duration:
            lines.append(f"Effect duration: {duration} ticks")
        effect_tags = tuple(getattr(consumable, "effect_tags", ()) or ())
        if effect_tags:
            lines.append("Effects: " + ", ".join(tag.replace("_", " ") for tag in effect_tags))

    return tuple(lines)


async def show_inventory_item_detail(session, target: str) -> bool:
    definition = _owned_item(session, target)
    if definition is None:
        return False
    await session.send("\r\n".join(item_detail_lines(session, definition)) + "\r\n")
    return True


async def _delegate_prompt(session, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in session.__dict__
    previous_instance_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    session.prompt = replay_prompt
    try:
        await previous_playing_prompt(session)
    finally:
        if had_instance_prompt:
            session.prompt = previous_instance_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_inventory_inspection_runtime(player_session_class) -> None:
    """Make ITEM/INSPECT ITEM work for every carried object, not just equipment.

    This layer sits outside the older equipment runtime. Equipment therefore keeps
    all of its existing equip/compare behavior while quest items, materials,
    curios, and other ordinary inventory objects finally have a readable detail
    view too. Specialized outer systems, such as altered-perception drugs, may
    still provide richer item-specific presentation before delegating here.
    """

    if getattr(player_session_class, "_inventory_inspection_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        target: str | None = None
        if normalized.startswith("inspect item "):
            target = stripped[len("inspect item "):].strip()
        elif normalized.startswith("item "):
            target = stripped[len("item "):].strip()

        if target:
            if await show_inventory_item_detail(self, target):
                return
            # Preserve the older equipment/drug error handling for unknown names.
            # In normal play the partial matcher has already expanded any unique
            # abbreviation, so this path mainly covers genuine misses.

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._inventory_inspection_runtime_installed = True
