from __future__ import annotations

import random
from dataclasses import dataclass

import mud.crafting as crafting
import mud.world as legacy_world
from mud.content_loot import loot_family_for
from mud.merchants import MERCHANTS_BY_NPC_KEY, MerchantDefinition, MerchantStockEntry


SPARKS_PER_EMBER = 10
SPARKS_PER_FLAME = 100
MERCHANT_BUYBACK_RATE = 0.35
LEGACY_SCRIP_TO_SPARKS = 10


@dataclass(frozen=True, slots=True)
class SolDenominations:
    flames: int
    embers: int
    sparks: int


def split_sols(total_sparks: int) -> SolDenominations:
    total = max(0, int(total_sparks))
    flames, remainder = divmod(total, SPARKS_PER_FLAME)
    embers, sparks = divmod(remainder, SPARKS_PER_EMBER)
    return SolDenominations(flames=flames, embers=embers, sparks=sparks)


def format_sols(total_sparks: int) -> str:
    """Render a base-unit balance using the sun-themed Sol denominations."""
    parts: list[str] = []
    values = split_sols(total_sparks)
    for amount, singular in (
        (values.flames, "flame"),
        (values.embers, "ember"),
        (values.sparks, "spark"),
    ):
        if amount:
            parts.append(f"{amount} {singular if amount == 1 else singular + 's'}")
    return ", ".join(parts) if parts else "0 sparks"


def quest_sol_reward(quest) -> int:
    """Return a reliable Sol reward for a completed authored quest.

    Explicit quest rewards win. Otherwise early structured quests pay in embers,
    discovery/repeatable work pays less, and long/high-level stories can reach a
    flame or more without making low-level coin values meaningless.
    """
    explicit = getattr(quest, "sol_reward", None)
    if explicit is not None:
        return max(0, int(explicit))

    level = max(1, int(getattr(quest, "minimum_level", 1) or 1))
    style = str(getattr(quest, "style", "structured") or "structured").strip().lower()
    steps = len(tuple(getattr(quest, "objective_steps", ()) or ()))

    reward = 10 + (level - 1) * 5
    if style in {"discovery", "repeatable"}:
        reward = max(5, int(round(reward * 0.6)))
    if style == "structured" and (steps >= 7 or level >= 10):
        reward = max(100, reward)
    return reward


def item_list_price(item_key: str) -> int:
    """Return the baseline merchant retail value in sparks.

    The catalog intentionally derives prices from existing item semantics so new
    authored content participates in the Sol economy without a second giant price
    table. Individual merchant stock can still override its sale price.
    """
    item = crafting.ITEMS_BY_KEY.get(item_key)
    if item is None:
        return 0

    category = str(getattr(item, "category", "") or "").strip().lower()
    tier = max(0, int(getattr(item, "tier", 0) or 0))

    # Story credentials, obsolete currency tokens, and fashion/provenance pieces
    # are not generic-vendor fodder. Their owning systems remain authoritative.
    if category in {
        "quest_item",
        "credential",
        "currency",
        "style",
        "fashion",
        "cosmetic",
        "fragrance",
    }:
        return 0

    if category in {"material", "reagent", "ingredient", "resource", "trophy"}:
        return max(1, 2 + tier * 2)
    if category in {"consumable", "food", "potion", "elixir", "tincture"}:
        return max(1, 2 + tier * 3)
    if category == "equipment":
        # Tier-1 useful gear lands at 3 embers 5 sparks. Tier-2 approaches a
        # flame; stronger/special gear naturally crosses the one-flame line.
        return max(15, 20 + (15 * tier * tier))
    return max(1, 3 + tier * 4)


def merchant_buyback_price(item_key: str) -> int:
    retail = item_list_price(item_key)
    if retail <= 0:
        return 0
    return max(1, int(retail * MERCHANT_BUYBACK_RATE))


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _parse_quantity_target(text: str) -> tuple[int, str]:
    stripped = text.strip()
    if not stripped:
        return 1, ""
    parts = stripped.split(maxsplit=1)
    if len(parts) == 2 and parts[0].isdigit():
        return max(1, int(parts[0])), parts[1]
    return 1, stripped


def _item_names(item_key: str) -> frozenset[str]:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    names = {_normalize(item_key)}
    if item is not None:
        names.add(_normalize(item.name))
    return frozenset(name for name in names if name)


def _match_item_key(candidates: tuple[str, ...], target: str) -> tuple[str | None, str | None]:
    wanted = _normalize(target)
    if not wanted:
        return None, "Name an item."

    exact = [key for key in candidates if wanted in _item_names(key)]
    partial = [
        key
        for key in candidates
        if key not in exact and any(wanted in name for name in _item_names(key))
    ]
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "No matching item was found."
    if len(matches) > 1:
        labels = []
        for key in matches:
            item = crafting.ITEMS_BY_KEY.get(key)
            labels.append(item.name if item is not None else key.replace("_", " ").title())
        return None, "Be more specific: " + ", ".join(labels) + "."
    return matches[0], None


def _merchant_name(npc_key: str) -> str:
    definition = legacy_world.NPCS_BY_KEY.get(npc_key)
    if definition is not None:
        return definition.name
    return npc_key.replace("_", " ").title()


def _merchants_here(session) -> tuple[tuple[str, MerchantDefinition], ...]:
    character = getattr(session, "character", None)
    if character is None:
        return ()
    room_key = character.current_room or ""
    result: list[tuple[str, MerchantDefinition]] = []
    seen: set[str] = set()

    mobile = getattr(session, "mobile_npcs", None)
    if mobile is not None:
        for state in mobile.npcs_in_room(room_key):
            merchant = MERCHANTS_BY_NPC_KEY.get(state.definition.key)
            if merchant is None or merchant.npc_key in seen:
                continue
            seen.add(merchant.npc_key)
            result.append((state.definition.name, merchant))

    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is not None:
        for npc_key in getattr(room, "npc_keys", ()):
            merchant = MERCHANTS_BY_NPC_KEY.get(npc_key)
            if merchant is None or merchant.npc_key in seen:
                continue
            seen.add(merchant.npc_key)
            result.append((_merchant_name(npc_key), merchant))

    return tuple(result)


def _stock_price(stock: MerchantStockEntry) -> int:
    if stock.price_units is not None:
        return max(0, int(stock.price_units))
    return item_list_price(stock.item_key)


def _stock_matches(
    merchants: tuple[tuple[str, MerchantDefinition], ...],
    target: str,
) -> tuple[tuple[str, MerchantDefinition, MerchantStockEntry] | None, str | None]:
    wanted = _normalize(target)
    if not wanted:
        return None, "Name something to buy."

    exact: list[tuple[str, MerchantDefinition, MerchantStockEntry]] = []
    partial: list[tuple[str, MerchantDefinition, MerchantStockEntry]] = []
    for merchant_name, merchant in merchants:
        for stock in merchant.stock:
            names = _item_names(stock.item_key)
            row = (merchant_name, merchant, stock)
            if wanted in names:
                exact.append(row)
            elif any(wanted in name for name in names):
                partial.append(row)

    candidates = exact or partial
    if not candidates:
        return None, "No merchant here sells that."

    # If two nearby merchants stock the same item at the same price, the item is
    # not ambiguous to the player. Prefer the first visible merchant.
    unique = {(row[2].item_key, _stock_price(row[2])) for row in candidates}
    if len(unique) > 1:
        labels = []
        for merchant_name, _merchant, stock in candidates:
            item = crafting.ITEMS_BY_KEY.get(stock.item_key)
            name = item.name if item is not None else stock.item_key
            labels.append(f"{name} from {merchant_name}")
        return None, "Be more specific: " + ", ".join(labels) + "."
    return candidates[0], None


def _unreserved_quantity(session, item_key: str) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return 0
    owned = session.database.item_quantity(character.id, item_key)
    try:
        from mud.equipment_system import equipped_item_keys

        equipped = equipped_item_keys(session.database, character.id)
        reserved = sum(1 for key in equipped.values() if key == item_key)
    except Exception:
        reserved = 0
    return max(0, owned - reserved)


async def _show_sols(session) -> None:
    character = session.character
    balance = session.database.get_sols(character.id)
    await session.send(
        "\r\n--- Sols ---\r\n"
        f"{format_sols(balance)}\r\n"
        "Sols are sun-stamped coins used across Astralis. "
        "10 sparks = 1 ember; 10 embers = 1 flame.\r\n"
    )


async def _show_shop(session) -> bool:
    merchants = _merchants_here(session)
    if not merchants:
        return False

    await session.send("\r\n--- Merchant Wares ---\r\n")
    for merchant_name, merchant in merchants:
        await session.send(f"{merchant_name}:\r\n")
        for stock in merchant.stock:
            item = crafting.ITEMS_BY_KEY.get(stock.item_key)
            name = item.name if item is not None else stock.item_key.replace("_", " ").title()
            await session.send(f"  {name} — {format_sols(_stock_price(stock))}\r\n")
    await session.send(
        f"Your Sols: {format_sols(session.database.get_sols(session.character.id))}\r\n"
        "BUY [qty] <item> | SELL [qty] <item> | VALUE <item>\r\n"
    )
    return True


async def _buy(session, target: str) -> bool:
    merchants = _merchants_here(session)
    if not merchants:
        return False

    quantity, item_text = _parse_quantity_target(target)
    match, error = _stock_matches(merchants, item_text)
    if match is None:
        await session.send((error or "That item is not sold here.") + "\r\n")
        return True

    merchant_name, _merchant, stock = match
    unit_price = _stock_price(stock)
    total = unit_price * quantity
    if total <= 0:
        await session.send(f"{merchant_name} is not offering that item for sale right now.\r\n")
        return True

    balance = session.database.get_sols(session.character.id)
    if balance < total:
        await session.send(
            f"You need {format_sols(total)} but have {format_sols(balance)}.\r\n"
        )
        return True

    if not session.database.complete_merchant_purchase(
        session.character.id,
        item_key=stock.item_key,
        quantity=quantity,
        total_price=total,
    ):
        await session.send("The purchase could not be completed safely.\r\n")
        return True

    item = crafting.ITEMS_BY_KEY.get(stock.item_key)
    name = item.name if item is not None else stock.item_key.replace("_", " ").title()
    await session.send(
        f"You buy {quantity}x {name} from {merchant_name} for {format_sols(total)}. "
        f"Balance: {format_sols(session.database.get_sols(session.character.id))}.\r\n"
    )
    return True


async def _sell(session, target: str) -> bool:
    merchants = _merchants_here(session)
    if not merchants:
        return False

    quantity, item_text = _parse_quantity_target(target)
    rows = session.database.list_items(session.character.id)
    candidates = tuple(str(row["item_key"]) for row in rows if int(row["quantity"]) > 0)
    item_key, error = _match_item_key(candidates, item_text)
    if item_key is None:
        await session.send((error or "You are not carrying that.") + "\r\n")
        return True

    unit_price = merchant_buyback_price(item_key)
    if unit_price <= 0:
        item = crafting.ITEMS_BY_KEY.get(item_key)
        name = item.name if item is not None else item_key.replace("_", " ").title()
        await session.send(f"{name} is not something ordinary merchants will buy.\r\n")
        return True

    available = _unreserved_quantity(session, item_key)
    if available < quantity:
        if session.database.item_quantity(session.character.id, item_key) >= quantity:
            await session.send("Unequip that item first; merchants will not buy gear you are wearing or wielding.\r\n")
        else:
            await session.send(f"You only have {available} available to sell.\r\n")
        return True

    proceeds = unit_price * quantity
    if not session.database.complete_merchant_sale(
        session.character.id,
        item_key=item_key,
        quantity=quantity,
        proceeds=proceeds,
    ):
        await session.send("The sale could not be completed safely.\r\n")
        return True

    item = crafting.ITEMS_BY_KEY.get(item_key)
    name = item.name if item is not None else item_key.replace("_", " ").title()
    await session.send(
        f"You sell {quantity}x {name} for {format_sols(proceeds)}. "
        f"Balance: {format_sols(session.database.get_sols(session.character.id))}.\r\n"
    )
    return True


async def _value(session, target: str) -> bool:
    merchants = _merchants_here(session)
    if not merchants:
        return False

    rows = session.database.list_items(session.character.id)
    candidates = tuple(str(row["item_key"]) for row in rows if int(row["quantity"]) > 0)
    item_key, error = _match_item_key(candidates, target)
    if item_key is None:
        await session.send((error or "You are not carrying that.") + "\r\n")
        return True
    price = merchant_buyback_price(item_key)
    item = crafting.ITEMS_BY_KEY.get(item_key)
    name = item.name if item is not None else item_key.replace("_", " ").title()
    if price <= 0:
        await session.send(f"{name} has no ordinary merchant buyback value.\r\n")
    else:
        await session.send(
            f"{name}: merchant value {format_sols(price)} each "
            f"(35% of its {format_sols(item_list_price(item_key))} baseline value).\r\n"
        )
    return True


def humanoid_sol_drop(definition, *, rng: random.Random | None = None) -> int:
    """Roll carried Sols for a humanoid combatant; non-humanoids never drop coins."""
    if definition is None or str(getattr(definition, "key", "")) == "training_dummy":
        return 0
    if loot_family_for(definition) != "humanoid":
        return 0
    xp = max(1, int(getattr(definition, "xp_reward", 0) or 0))
    low = max(1, xp // 12)
    high = max(low, xp // 6 + 1)
    roller = rng or random
    return int(roller.randint(low, high))


def _install_quest_sol_hook(database_class) -> None:
    if getattr(database_class, "_sol_quest_hook_installed", False):
        return

    previous_complete = database_class.complete_quest

    def complete_quest(self, character_id: int, quest_key: str):
        before = self.get_quest(character_id, quest_key)
        result = previous_complete(self, character_id, quest_key)
        after = self.get_quest(character_id, quest_key)
        if (
            before is None
            or str(before.get("status", "")) != "active"
            or after is None
            or str(after.get("status", "")) != "completed"
        ):
            return result

        from mud.quests import QUESTS_BY_KEY

        quest = QUESTS_BY_KEY.get(quest_key)
        if quest is None:
            return result
        reward = quest_sol_reward(quest)
        if reward <= 0:
            return result

        self.add_sols(character_id, reward)
        events = getattr(self, "_sol_quest_events", None)
        if events is None:
            events = {}
            self._sol_quest_events = events
        events.setdefault(int(character_id), []).append(
            (getattr(quest, "name", quest_key), reward)
        )
        return result

    database_class.complete_quest = complete_quest
    database_class._sol_quest_hook_installed = True


async def _flush_quest_events(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    events = getattr(session.database, "_sol_quest_events", None)
    if not events:
        return
    pending = list(events.pop(int(character.id), []))
    for quest_name, reward in pending:
        await session.send(
            f"Quest Sol reward — {quest_name}: {format_sols(int(reward))}.\r\n"
        )


async def _delegate_prompt(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    old_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    session.prompt = replay_prompt
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = old_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_sols_runtime(player_session_class, database_class) -> None:
    """Install Astralis's universal Sol currency and merchant command layer."""
    if getattr(player_session_class, "_sols_runtime_installed", False):
        return

    _install_quest_sol_hook(database_class)

    previous_prompt = player_session_class.playing_prompt
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def _finish_enemy_defeat(self, enemy) -> None:
        eligible = getattr(self, "active_enemy", None) is enemy
        definition = getattr(enemy, "definition", None)
        await previous_finish_enemy(self, enemy)
        if not eligible or self.character is None:
            return
        amount = humanoid_sol_drop(definition)
        if amount <= 0:
            return
        self.database.add_sols(self.character.id, amount)
        await self.send(
            f"You recover {format_sols(amount)} in sun-stamped Sols from the fallen {definition.name}.\r\n"
        )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = _normalize(command)
        try:
            if normalized in {"sol", "sols", "money", "coins", "currency"}:
                await _show_sols(self)
                return
            if normalized in {"shop", "wares", "list"}:
                if await _show_shop(self):
                    return
            if normalized == "buy":
                if _merchants_here(self):
                    await self.send("Buy what? Use SHOP to see the merchant's wares.\r\n")
                    return
            if normalized.startswith("buy "):
                if await _buy(self, command.strip().split(maxsplit=1)[1]):
                    return
            if normalized == "sell":
                if _merchants_here(self):
                    await self.send("Sell what? Use SELL [qty] <item>.\r\n")
                    return
            if normalized.startswith("sell ") and not normalized.startswith("sell demand "):
                if await _sell(self, command.strip().split(maxsplit=1)[1]):
                    return
            if normalized == "value":
                if _merchants_here(self):
                    await self.send("Value what? Use VALUE <item>.\r\n")
                    return
            if normalized.startswith("value "):
                if await _value(self, command.strip().split(maxsplit=1)[1]):
                    return

            await _delegate_prompt(self, previous_prompt, command)
        finally:
            await _flush_quest_events(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._sols_runtime_installed = True
