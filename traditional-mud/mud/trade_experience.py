from __future__ import annotations

import re
from dataclasses import dataclass, field
from weakref import WeakSet

import mud.crafting as crafting
from mud.equipment_system import equipped_item_keys
from mud.social_experience import social_allows_message_from


_ACTIVE_SESSIONS: WeakSet = WeakSet()
_PENDING_INVITES: dict[int, int] = {}
_TRADES_BY_CHARACTER: dict[int, "TradeSession"] = {}
_INTEGER = re.compile(r"^[+-]?\d+$")


@dataclass(slots=True)
class TradeSession:
    first_character_id: int
    second_character_id: int
    offers: dict[int, dict[str, int]] = field(default_factory=dict)
    confirmed: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.offers.setdefault(self.first_character_id, {})
        self.offers.setdefault(self.second_character_id, {})

    def partner_id(self, character_id: int) -> int:
        if character_id == self.first_character_id:
            return self.second_character_id
        if character_id == self.second_character_id:
            return self.first_character_id
        raise KeyError(character_id)


def reset_trade_runtime_state() -> None:
    """Clear process-local trade state. Primarily useful for tests and hot reloads."""
    _ACTIVE_SESSIONS.clear()
    _PENDING_INVITES.clear()
    _TRADES_BY_CHARACTER.clear()


def _character(session):
    return getattr(session, "character", None)


def _session_for_character_id(character_id: int):
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and int(character.id) == int(character_id):
            return session
    return None


def _session_for_name(name: str):
    needle = name.strip().lower()
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and str(character.name).lower() == needle:
            return session
    return None


async def _safe_send(session, text: str) -> None:
    if session is None:
        return
    try:
        await session.send(text)
    except (ConnectionError, RuntimeError):
        return


def _same_room(first_session, second_session) -> bool:
    first = _character(first_session)
    second = _character(second_session)
    if first is None or second is None:
        return False
    return bool(first.current_room) and first.current_room == second.current_room


def _in_combat(session) -> bool:
    return getattr(session, "active_enemy", None) is not None


def _normalize_item_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _item_names(item_key: str) -> set[str]:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    names = {_normalize_item_text(item_key)}
    if definition is not None:
        names.add(_normalize_item_text(definition.name))
    return names


def _resolve_owned_item(session, target: str) -> tuple[str | None, str | None]:
    character = _character(session)
    if character is None:
        return None, "No active character."
    wanted = _normalize_item_text(target)
    if not wanted:
        return None, "Name an item."

    exact: list[str] = []
    partial: list[str] = []
    for row in session.database.list_items(character.id):
        if int(row["quantity"]) <= 0:
            continue
        item_key = str(row["item_key"])
        names = _item_names(item_key)
        if wanted in names:
            exact.append(item_key)
        elif any(wanted in name for name in names):
            partial.append(item_key)

    matches = exact or partial
    unique = tuple(dict.fromkeys(matches))
    if not unique:
        return None, "You do not carry an item by that name."
    if len(unique) > 1:
        labels = [crafting.ITEMS_BY_KEY.get(key).name if key in crafting.ITEMS_BY_KEY else key for key in unique]
        return None, "Be more specific: " + ", ".join(labels) + "."
    return unique[0], None


def _resolve_offered_item(trade: TradeSession, character_id: int, target: str) -> tuple[str | None, str | None]:
    wanted = _normalize_item_text(target)
    offered = trade.offers.get(character_id, {})
    exact = [key for key in offered if wanted in _item_names(key)]
    partial = [key for key in offered if any(wanted in name for name in _item_names(key))]
    matches = exact or partial
    unique = tuple(dict.fromkeys(matches))
    if not unique:
        return None, "That item is not in your offer."
    if len(unique) > 1:
        return None, "Be more specific about which offered item to remove."
    return unique[0], None


def _parse_quantity_and_item(text: str) -> tuple[int | None, str | None, str | None]:
    parts = text.strip().split()
    if not parts:
        return None, None, "Name an item."
    quantity = 1
    if _INTEGER.fullmatch(parts[0]):
        quantity = int(parts[0])
        parts = parts[1:]
        if quantity <= 0:
            return None, None, "Quantity must be a positive whole number."
    if not parts:
        return None, None, "Name an item."
    return quantity, " ".join(parts), None


def _transferability_error(session, item_key: str, quantity: int) -> str | None:
    character = _character(session)
    if character is None:
        return "No active character."
    if quantity <= 0:
        return "Quantity must be positive."

    definition = crafting.ITEMS_BY_KEY.get(item_key)
    if definition is None:
        return "That item is not registered as a tradeable game item."
    if definition.category == "quest_item":
        return f"{definition.name} is a quest item and cannot be transferred."

    equipped = set(equipped_item_keys(session.database, character.id).values())
    if item_key in equipped:
        return f"Unequip {definition.name} before transferring it."

    available = session.database.item_quantity(character.id, item_key)
    if available < quantity:
        return f"You only have {available}x {definition.name}."
    return None


def _pair_error(first_session, second_session) -> str | None:
    if _character(first_session) is None or _character(second_session) is None:
        return "Both characters must be online."
    if not _same_room(first_session, second_session):
        return "Both characters must be in the same room."
    if _in_combat(first_session) or _in_combat(second_session):
        return "Finish combat before exchanging items."
    return None


def exchange_items(
    database,
    first_character_id: int,
    first_offer: dict[str, int],
    second_character_id: int,
    second_offer: dict[str, int],
) -> bool:
    """Atomically exchange two inventory offers under a SQLite write lock."""
    if first_character_id == second_character_id:
        raise ValueError("A character cannot trade with itself.")
    for offer in (first_offer, second_offer):
        if any(quantity <= 0 for quantity in offer.values()):
            raise ValueError("Trade quantities must be positive.")

    db = database.connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        for character_id, offer in (
            (first_character_id, first_offer),
            (second_character_id, second_offer),
        ):
            for item_key, quantity in offer.items():
                row = db.execute(
                    "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, item_key),
                ).fetchone()
                if row is None or int(row["quantity"]) < quantity:
                    db.rollback()
                    return False

        def debit(character_id: int, offer: dict[str, int]) -> None:
            for item_key, quantity in offer.items():
                row = db.execute(
                    "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
                    (character_id, item_key),
                ).fetchone()
                remaining = int(row["quantity"]) - quantity
                if remaining:
                    db.execute(
                        "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                        (remaining, character_id, item_key),
                    )
                else:
                    db.execute(
                        "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                        (character_id, item_key),
                    )

        def credit(character_id: int, offer: dict[str, int]) -> None:
            for item_key, quantity in offer.items():
                db.execute(
                    """
                    INSERT INTO character_items (character_id, item_key, quantity)
                    VALUES (?, ?, ?)
                    ON CONFLICT(character_id, item_key) DO UPDATE SET
                        quantity = quantity + excluded.quantity
                    """,
                    (character_id, item_key, quantity),
                )

        debit(first_character_id, first_offer)
        debit(second_character_id, second_offer)
        credit(second_character_id, first_offer)
        credit(first_character_id, second_offer)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _format_offer(offer: dict[str, int]) -> str:
    if not offer:
        return "nothing"
    parts: list[str] = []
    for item_key, quantity in sorted(offer.items()):
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        name = definition.name if definition is not None else item_key
        parts.append(f"{quantity}x {name}")
    return ", ".join(parts)


async def _show_trade_status(session, trade: TradeSession) -> None:
    character = _character(session)
    if character is None:
        return
    partner_id = trade.partner_id(character.id)
    partner_session = _session_for_character_id(partner_id)
    partner = _character(partner_session)
    partner_name = partner.name if partner is not None else "the other player"
    await session.send(
        "\r\n--- Trade ---\r\n"
        f"You offer: {_format_offer(trade.offers[character.id])}\r\n"
        f"{partner_name} offers: {_format_offer(trade.offers[partner_id])}\r\n"
        f"Confirmed: you {'YES' if character.id in trade.confirmed else 'NO'} | "
        f"{partner_name} {'YES' if partner_id in trade.confirmed else 'NO'}\r\n"
        "Commands: TRADE ADD [qty] <item>, TRADE REMOVE [qty] <item>, TRADE CONFIRM, TRADE CANCEL.\r\n"
    )


async def _cancel_invites_for(character_id: int, reason: str = "") -> None:
    affected = [
        (target_id, inviter_id)
        for target_id, inviter_id in tuple(_PENDING_INVITES.items())
        if target_id == character_id or inviter_id == character_id
    ]
    for target_id, inviter_id in affected:
        _PENDING_INVITES.pop(target_id, None)
        other_id = inviter_id if target_id == character_id else target_id
        other_session = _session_for_character_id(other_id)
        if other_session is not None:
            suffix = f" ({reason})" if reason else ""
            await _safe_send(other_session, f"The pending trade invitation was canceled{suffix}.\r\n")


async def _cancel_trade_for(character_id: int, reason: str = "Trade canceled.") -> None:
    trade = _TRADES_BY_CHARACTER.get(character_id)
    if trade is None:
        return
    first_id = trade.first_character_id
    second_id = trade.second_character_id
    _TRADES_BY_CHARACTER.pop(first_id, None)
    _TRADES_BY_CHARACTER.pop(second_id, None)
    for participant_id in (first_id, second_id):
        participant = _session_for_character_id(participant_id)
        if participant is not None:
            await _safe_send(participant, reason.rstrip() + "\r\n")


async def _give(session, target_name: str, quantity: int, item_text: str) -> None:
    sender = _character(session)
    if sender is None:
        return
    target_session = _session_for_name(target_name)
    if target_session is None or _character(target_session) is None:
        await session.send("That character is not online.\r\n")
        return
    target = _character(target_session)
    assert target is not None
    if target.id == sender.id:
        await session.send("You cannot give an item to yourself.\r\n")
        return

    pair_error = _pair_error(session, target_session)
    if pair_error:
        await session.send(pair_error + "\r\n")
        return
    if not social_allows_message_from(target_session, sender.name):
        await session.send(f"{target.name} is not accepting transfers from you.\r\n")
        return

    item_key, error = _resolve_owned_item(session, item_text)
    if error:
        await session.send(error + "\r\n")
        return
    assert item_key is not None
    error = _transferability_error(session, item_key, quantity)
    if error:
        await session.send(error + "\r\n")
        return

    try:
        moved = exchange_items(session.database, sender.id, {item_key: quantity}, target.id, {})
    except Exception:
        await session.send("The transfer could not be completed safely. Nothing was moved.\r\n")
        return
    if not moved:
        await session.send("Your inventory changed before the transfer completed. Nothing was moved.\r\n")
        return

    definition = crafting.ITEMS_BY_KEY[item_key]
    await session.send(f"You give {target.name} {quantity}x {definition.name}.\r\n")
    await _safe_send(target_session, f"{sender.name} gives you {quantity}x {definition.name}.\r\n")


async def _invite(session, target_name: str) -> None:
    sender = _character(session)
    if sender is None:
        return
    target_session = _session_for_name(target_name)
    if target_session is None or _character(target_session) is None:
        await session.send("That character is not online.\r\n")
        return
    target = _character(target_session)
    assert target is not None
    if target.id == sender.id:
        await session.send("You cannot trade with yourself.\r\n")
        return
    if sender.id in _TRADES_BY_CHARACTER:
        await session.send("You already have an active trade. Use TRADE CANCEL first.\r\n")
        return
    if target.id in _TRADES_BY_CHARACTER:
        await session.send(f"{target.name} is already trading.\r\n")
        return
    if target.id in _PENDING_INVITES:
        await session.send(f"{target.name} already has a pending trade invitation.\r\n")
        return
    if any(inviter_id == sender.id for inviter_id in _PENDING_INVITES.values()):
        await session.send("You already have a pending trade invitation.\r\n")
        return

    pair_error = _pair_error(session, target_session)
    if pair_error:
        await session.send(pair_error + "\r\n")
        return
    if not social_allows_message_from(target_session, sender.name):
        await session.send(f"{target.name} is not accepting trade invitations from you.\r\n")
        return

    _PENDING_INVITES[target.id] = sender.id
    await session.send(f"Trade invitation sent to {target.name}.\r\n")
    await _safe_send(
        target_session,
        f"{sender.name} wants to trade with you. Use TRADE ACCEPT or TRADE DECLINE.\r\n",
    )


async def _accept_invite(session, expected_name: str = "") -> None:
    character = _character(session)
    if character is None:
        return
    inviter_id = _PENDING_INVITES.get(character.id)
    if inviter_id is None:
        await session.send("You do not have a pending trade invitation.\r\n")
        return
    inviter_session = _session_for_character_id(inviter_id)
    inviter = _character(inviter_session)
    if inviter_session is None or inviter is None:
        _PENDING_INVITES.pop(character.id, None)
        await session.send("That trade invitation is no longer available.\r\n")
        return
    if expected_name and inviter.name.lower() != expected_name.strip().lower():
        await session.send(f"Your pending invitation is from {inviter.name}.\r\n")
        return

    pair_error = _pair_error(session, inviter_session)
    if pair_error:
        _PENDING_INVITES.pop(character.id, None)
        await session.send(pair_error + " The invitation was canceled.\r\n")
        await _safe_send(inviter_session, "The trade invitation was canceled because you are no longer together.\r\n")
        return

    _PENDING_INVITES.pop(character.id, None)
    trade = TradeSession(inviter.id, character.id)
    _TRADES_BY_CHARACTER[inviter.id] = trade
    _TRADES_BY_CHARACTER[character.id] = trade
    await session.send(f"You begin trading with {inviter.name}.\r\n")
    await _safe_send(inviter_session, f"{character.name} accepts your trade invitation.\r\n")
    await _show_trade_status(session, trade)


async def _decline_invite(session, expected_name: str = "") -> None:
    character = _character(session)
    if character is None:
        return
    inviter_id = _PENDING_INVITES.get(character.id)
    if inviter_id is None:
        await session.send("You do not have a pending trade invitation.\r\n")
        return
    inviter_session = _session_for_character_id(inviter_id)
    inviter = _character(inviter_session)
    if expected_name and inviter is not None and inviter.name.lower() != expected_name.strip().lower():
        await session.send(f"Your pending invitation is from {inviter.name}.\r\n")
        return
    _PENDING_INVITES.pop(character.id, None)
    await session.send("Trade invitation declined.\r\n")
    if inviter_session is not None:
        await _safe_send(inviter_session, f"{character.name} declines your trade invitation.\r\n")


async def _change_offer(session, *, add: bool, quantity: int, item_text: str) -> None:
    character = _character(session)
    if character is None:
        return
    trade = _TRADES_BY_CHARACTER.get(character.id)
    if trade is None:
        await session.send("You do not have an active trade. Use TRADE <player> first.\r\n")
        return
    partner_session = _session_for_character_id(trade.partner_id(character.id))
    pair_error = _pair_error(session, partner_session) if partner_session is not None else "The other player is no longer online."
    if pair_error:
        await _cancel_trade_for(character.id, f"Trade canceled: {pair_error}")
        return

    if add:
        item_key, error = _resolve_owned_item(session, item_text)
        if error:
            await session.send(error + "\r\n")
            return
        assert item_key is not None
        new_quantity = trade.offers[character.id].get(item_key, 0) + quantity
        error = _transferability_error(session, item_key, new_quantity)
        if error:
            await session.send(error + "\r\n")
            return
        trade.offers[character.id][item_key] = new_quantity
    else:
        item_key, error = _resolve_offered_item(trade, character.id, item_text)
        if error:
            await session.send(error + "\r\n")
            return
        assert item_key is not None
        current = trade.offers[character.id][item_key]
        if quantity >= current:
            trade.offers[character.id].pop(item_key, None)
        else:
            trade.offers[character.id][item_key] = current - quantity

    had_confirmations = bool(trade.confirmed)
    trade.confirmed.clear()
    action = "added to" if add else "removed from"
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    name = definition.name if definition is not None else item_key
    await session.send(f"{quantity}x {name} {action} your offer.\r\n")
    if had_confirmations:
        await session.send("The offer changed, so both confirmations were reset.\r\n")
        await _safe_send(partner_session, "The trade offer changed; both confirmations were reset.\r\n")
    await _show_trade_status(session, trade)


async def _confirm_trade(session) -> None:
    character = _character(session)
    if character is None:
        return
    trade = _TRADES_BY_CHARACTER.get(character.id)
    if trade is None:
        await session.send("You do not have an active trade.\r\n")
        return
    partner_id = trade.partner_id(character.id)
    partner_session = _session_for_character_id(partner_id)
    pair_error = _pair_error(session, partner_session) if partner_session is not None else "The other player is no longer online."
    if pair_error:
        await _cancel_trade_for(character.id, f"Trade canceled: {pair_error}")
        return

    for participant_id in (trade.first_character_id, trade.second_character_id):
        participant = _session_for_character_id(participant_id)
        if participant is None:
            await _cancel_trade_for(character.id, "Trade canceled: a player disconnected.")
            return
        for item_key, quantity in trade.offers[participant_id].items():
            error = _transferability_error(participant, item_key, quantity)
            if error:
                trade.confirmed.clear()
                await session.send(f"Trade cannot be confirmed: {error}\r\n")
                return

    trade.confirmed.add(character.id)
    await session.send("Trade confirmed. Waiting for the other player.\r\n")
    await _safe_send(partner_session, f"{character.name} confirms the current trade offer.\r\n")
    if len(trade.confirmed) < 2:
        return

    first_offer = dict(trade.offers[trade.first_character_id])
    second_offer = dict(trade.offers[trade.second_character_id])
    try:
        success = exchange_items(
            session.database,
            trade.first_character_id,
            first_offer,
            trade.second_character_id,
            second_offer,
        )
    except Exception:
        trade.confirmed.clear()
        await _safe_send(session, "The trade could not be committed safely. Nothing was moved.\r\n")
        await _safe_send(partner_session, "The trade could not be committed safely. Nothing was moved.\r\n")
        return

    if not success:
        trade.confirmed.clear()
        await _safe_send(session, "An offered inventory changed before commit. Nothing was moved; review and confirm again.\r\n")
        await _safe_send(partner_session, "An offered inventory changed before commit. Nothing was moved; review and confirm again.\r\n")
        return

    _TRADES_BY_CHARACTER.pop(trade.first_character_id, None)
    _TRADES_BY_CHARACTER.pop(trade.second_character_id, None)
    await _safe_send(session, "Trade complete. All offered items were exchanged atomically.\r\n")
    await _safe_send(partner_session, "Trade complete. All offered items were exchanged atomically.\r\n")


async def _trade_help(session) -> None:
    await session.send(
        "\r\n--- Player Trade ---\r\n"
        "GIVE <player> [qty] <item> - immediate one-way transfer\r\n"
        "TRADE <player> - invite someone in your room\r\n"
        "TRADE ACCEPT / TRADE DECLINE - answer an invitation\r\n"
        "TRADE ADD [qty] <item> / TRADE REMOVE [qty] <item> - edit your offer\r\n"
        "TRADE STATUS - review both offers and confirmations\r\n"
        "TRADE CONFIRM - approve the current offer\r\n"
        "TRADE CANCEL - abort with nothing moved\r\n"
        "Changing an offer resets both confirmations. Moving, disconnecting, or entering combat invalidates a trade. Quest items and equipped items cannot be transferred.\r\n"
    )


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def _live_prompt(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_trade_experience_runtime(player_session_class) -> None:
    """Install room-local GIVE plus a two-confirmation, atomic player trade flow."""
    if getattr(player_session_class, "_trade_experience_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if _character(self) is not None:
                _ACTIVE_SESSIONS.add(self)

        player_session_class.enter_character = enter_character

    previous_close = getattr(player_session_class, "close", None)
    if previous_close is not None:
        async def close(self) -> None:
            character = _character(self)
            if character is not None:
                await _cancel_trade_for(character.id, f"Trade canceled: {character.name} disconnected.")
                await _cancel_invites_for(character.id, "player disconnected")
            _ACTIVE_SESSIONS.discard(self)
            await previous_close(self)

        player_session_class.close = close

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = _character(self)
        if character is None:
            await previous_playing_prompt(self)
            return

        _ACTIVE_SESSIONS.add(self)
        before_id = character.id
        before_room = character.current_room
        command = await self.prompt(_live_prompt(self))
        if command is None:
            await _cancel_trade_for(before_id, f"Trade canceled: {character.name} disconnected.")
            await _cancel_invites_for(before_id, "player disconnected")
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"trade help", "help trade", "trade"}:
            await _trade_help(self)
            return

        if normalized.startswith("give "):
            parts = stripped.split(maxsplit=2)
            if len(parts) < 3:
                await self.send("Use GIVE <player> [qty] <item>.\r\n")
                return
            quantity, item_text, error = _parse_quantity_and_item(parts[2])
            if error:
                await self.send(error + "\r\n")
                return
            assert quantity is not None and item_text is not None
            await _give(self, parts[1], quantity, item_text)
            return
        if normalized == "give":
            await self.send("Use GIVE <player> [qty] <item>.\r\n")
            return

        if normalized.startswith("trade accept"):
            await _accept_invite(self, stripped[len("trade accept"):].strip())
            return
        if normalized.startswith("trade decline"):
            await _decline_invite(self, stripped[len("trade decline"):].strip())
            return
        if normalized == "trade cancel":
            if before_id in _TRADES_BY_CHARACTER:
                await _cancel_trade_for(before_id, f"Trade canceled by {character.name}.")
            else:
                await _cancel_invites_for(before_id, "canceled")
                await self.send("No active trade remains.\r\n")
            return
        if normalized == "trade status":
            trade = _TRADES_BY_CHARACTER.get(before_id)
            if trade is None:
                inviter_id = _PENDING_INVITES.get(before_id)
                if inviter_id is not None:
                    inviter_session = _session_for_character_id(inviter_id)
                    inviter = _character(inviter_session)
                    await self.send(f"Pending invitation from {inviter.name if inviter else 'an offline player'}.\r\n")
                else:
                    await self.send("You do not have an active trade.\r\n")
            else:
                await _show_trade_status(self, trade)
            return
        if normalized.startswith("trade add "):
            quantity, item_text, error = _parse_quantity_and_item(stripped[len("trade add "):])
            if error:
                await self.send(error + "\r\n")
                return
            assert quantity is not None and item_text is not None
            await _change_offer(self, add=True, quantity=quantity, item_text=item_text)
            return
        if normalized.startswith("trade remove "):
            quantity, item_text, error = _parse_quantity_and_item(stripped[len("trade remove "):])
            if error:
                await self.send(error + "\r\n")
                return
            assert quantity is not None and item_text is not None
            await _change_offer(self, add=False, quantity=quantity, item_text=item_text)
            return
        if normalized == "trade confirm":
            await _confirm_trade(self)
            return
        if normalized.startswith("trade "):
            await _invite(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_playing_prompt, command)

        after = _character(self)
        if after is None or after.id != before_id or after.current_room != before_room:
            await _cancel_trade_for(before_id, "Trade canceled because a participant moved away.")
            await _cancel_invites_for(before_id, "participant moved away")
            return
        if _in_combat(self) and before_id in _TRADES_BY_CHARACTER:
            await _cancel_trade_for(before_id, "Trade canceled because combat began.")

    player_session_class.playing_prompt = playing_prompt
    player_session_class._trade_experience_runtime_installed = True
