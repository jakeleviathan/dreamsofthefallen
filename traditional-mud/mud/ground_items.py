from __future__ import annotations

from dataclasses import dataclass

import mud.crafting as crafting
from mud.equipment_system import equipped_item_keys


GROUND_ITEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS room_ground_items (
    room_key TEXT NOT NULL,
    item_key TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_key, item_key)
);
"""


@dataclass(frozen=True, slots=True)
class ItemMatch:
    item_key: str | None
    ambiguous_names: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.item_key is not None

    @property
    def ambiguous(self) -> bool:
        return bool(self.ambiguous_names)


def ensure_ground_item_storage(database) -> None:
    with database.connect() as db:
        db.execute(GROUND_ITEMS_TABLE_SQL)


def list_ground_items(database, room_key: str) -> list[dict[str, int | str]]:
    ensure_ground_item_storage(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT item_key, quantity
            FROM room_ground_items
            WHERE room_key = ? AND quantity > 0
            ORDER BY item_key
            """,
            (room_key,),
        ).fetchall()
    return [
        {"item_key": str(row["item_key"]), "quantity": int(row["quantity"])}
        for row in rows
    ]


def ground_item_quantity(database, room_key: str, item_key: str) -> int:
    ensure_ground_item_storage(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT quantity FROM room_ground_items WHERE room_key = ? AND item_key = ?",
            (room_key, item_key),
        ).fetchone()
    return 0 if row is None else int(row["quantity"])


def transfer_inventory_to_ground(
    database,
    character_id: int,
    room_key: str,
    item_key: str,
    quantity: int = 1,
) -> bool:
    """Atomically move an item stack from one character into shared room storage."""
    if quantity <= 0:
        raise ValueError("Drop quantity must be positive.")
    if not room_key:
        return False
    ensure_ground_item_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (character_id, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            return False

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

        db.execute(
            """
            INSERT INTO room_ground_items (room_key, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(room_key, item_key) DO UPDATE SET
                quantity = quantity + excluded.quantity,
                updated_at = CURRENT_TIMESTAMP
            """,
            (room_key, item_key, quantity),
        )
    return True


def transfer_ground_to_inventory(
    database,
    character_id: int,
    room_key: str,
    item_key: str,
    quantity: int = 1,
) -> bool:
    """Atomically pick an item stack up from shared room storage."""
    if quantity <= 0:
        raise ValueError("Pickup quantity must be positive.")
    if not room_key:
        return False
    ensure_ground_item_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM room_ground_items WHERE room_key = ? AND item_key = ?",
            (room_key, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            return False

        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute(
                """
                UPDATE room_ground_items
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE room_key = ? AND item_key = ?
                """,
                (remaining, room_key, item_key),
            )
        else:
            db.execute(
                "DELETE FROM room_ground_items WHERE room_key = ? AND item_key = ?",
                (room_key, item_key),
            )

        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET
                quantity = quantity + excluded.quantity
            """,
            (character_id, item_key, quantity),
        )
    return True


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").split())


def _display_name(item_key: str) -> str:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    return definition.name if definition is not None else item_key.replace("_", " ").title()


def _aliases(item_key: str) -> tuple[str, ...]:
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    names = {_normalize(item_key)}
    if definition is not None:
        names.add(_normalize(definition.name))
    return tuple(names)


def _resolve_item(rows, target: str) -> ItemMatch:
    wanted = _normalize(target)
    if not wanted:
        return ItemMatch(None)

    candidates: list[str] = []
    for row in rows:
        item_key = str(row["item_key"])
        aliases = _aliases(item_key)
        if wanted in aliases:
            return ItemMatch(item_key)
        if any(wanted in alias for alias in aliases):
            candidates.append(item_key)

    unique = tuple(dict.fromkeys(candidates))
    if len(unique) == 1:
        return ItemMatch(unique[0])
    if len(unique) > 1:
        return ItemMatch(None, tuple(_display_name(key) for key in unique))
    return ItemMatch(None)


def _parse_quantity_target(argument: str) -> tuple[int | None, str]:
    parts = argument.strip().split(maxsplit=1)
    if not parts:
        return None, ""
    if parts[0].isdigit():
        if len(parts) == 1:
            return None, ""
        quantity = int(parts[0])
        return (quantity if quantity > 0 else None), parts[1]
    return 1, argument.strip()


async def _show_ground_items(session) -> None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return
    rows = list_ground_items(session.database, character.current_room)
    if not rows:
        return
    await session.send("\r\nOn the ground:\r\n")
    for row in rows:
        quantity = int(row["quantity"])
        name = _display_name(str(row["item_key"]))
        if quantity == 1:
            await session.send(f"  {name}\r\n")
        else:
            await session.send(f"  {quantity}x {name}\r\n")


async def drop_item_command(session, argument: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to drop items while fighting.\r\n")
        return
    if not character.current_room:
        await session.send("There is nowhere here to leave an item.\r\n")
        return

    quantity, target = _parse_quantity_target(argument)
    if quantity is None or not target:
        await session.send("Drop what? Use DROP <item> or DROP <quantity> <item>.\r\n")
        return

    rows = session.database.list_items(character.id)
    match = _resolve_item(rows, target)
    if match.ambiguous:
        await session.send("Be more specific: " + ", ".join(match.ambiguous_names) + ".\r\n")
        return
    if not match.found:
        await session.send("You are not carrying an item by that name.\r\n")
        return

    item_key = str(match.item_key)
    definition = crafting.ITEMS_BY_KEY.get(item_key)
    if definition is not None and definition.category == "quest_item":
        await session.send(f"{definition.name} is a quest item and cannot be dropped.\r\n")
        return

    owned = session.database.item_quantity(character.id, item_key)
    if owned < quantity:
        await session.send(f"You only have {owned}x {_display_name(item_key)}.\r\n")
        return

    equipped = equipped_item_keys(session.database, character.id)
    if item_key in equipped.values() and owned - quantity < 1:
        await session.send(f"Unequip {_display_name(item_key)} before dropping your last copy.\r\n")
        return

    if not transfer_inventory_to_ground(
        session.database,
        character.id,
        character.current_room,
        item_key,
        quantity,
    ):
        await session.send("You cannot drop that item right now.\r\n")
        return

    name = _display_name(item_key)
    if quantity == 1:
        await session.send(f"You drop {name}.\r\n")
    else:
        await session.send(f"You drop {quantity}x {name}.\r\n")


async def take_item_command(session, argument: str) -> bool:
    """Take a room-ground item. Return False when no ground item matched.

    Returning False lets older contextual TAKE/GET commands keep ownership of
    authored room interactions such as tutorial props.
    """
    character = getattr(session, "character", None)
    if character is None:
        return False
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop to pick up items while fighting.\r\n")
        return True
    if not character.current_room:
        return False

    quantity, target = _parse_quantity_target(argument)
    if quantity is None or not target:
        await session.send("Take what? Use GET <item> or TAKE <quantity> <item>.\r\n")
        return True

    rows = list_ground_items(session.database, character.current_room)
    match = _resolve_item(rows, target)
    if match.ambiguous:
        await session.send("Be more specific: " + ", ".join(match.ambiguous_names) + ".\r\n")
        return True
    if not match.found:
        return False

    item_key = str(match.item_key)
    available = ground_item_quantity(session.database, character.current_room, item_key)
    if available < quantity:
        await session.send(f"There are only {available}x {_display_name(item_key)} here.\r\n")
        return True

    if not transfer_ground_to_inventory(
        session.database,
        character.id,
        character.current_room,
        item_key,
        quantity,
    ):
        await session.send("You cannot pick that item up right now.\r\n")
        return True

    name = _display_name(item_key)
    if quantity == 1:
        await session.send(f"You pick up {name}.\r\n")
    else:
        await session.send(f"You pick up {quantity}x {name}.\r\n")
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
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


def install_ground_items_runtime(player_session_class) -> None:
    """Install persistent room-ground inventory without stealing contextual verbs."""
    if getattr(player_session_class, "_ground_items_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_show_current_room = getattr(player_session_class, "show_current_room", None)

    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            await _show_ground_items(self)

        player_session_class.show_current_room = show_current_room

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized == "drop":
            await drop_item_command(self, "")
            return
        if normalized.startswith("drop "):
            await drop_item_command(self, normalized[len("drop "):])
            return

        pickup_prefixes = ("get ", "take ", "pickup ", "pick up ")
        if normalized in {"get", "take", "pickup", "pick up"}:
            await take_item_command(self, "")
            return
        for prefix in pickup_prefixes:
            if normalized.startswith(prefix):
                argument = normalized[len(prefix):]
                handled = await take_item_command(self, argument)
                if handled:
                    return
                break

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._ground_items_runtime_installed = True
