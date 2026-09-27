"""Normal crafting-book integration for regional Tailoring and daily commissions."""
from __future__ import annotations

from datetime import datetime, timezone

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_tailoring as catalog
from mud.mechanics import PROGRESSION_RULES
from mud.world import ROOMS_BY_KEY


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().replace("_", " ").split())


def _local(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return next((t for t in catalog.TRADITIONS if t.hall == character.current_room), None)


def _learned(session) -> set[str]:
    return set(session.database.list_flags(session.character.id))


def _skill(session) -> int:
    return crafting.trade_skill_value(session.database, session.character.id, "tailoring")


def _available_folios(session, *, owned: bool = False):
    if owned:
        return [(t, index) for t in catalog.TRADITIONS
                for index in range(1, len(crafting.TEXTILE_TIERS))
                if session.database.item_quantity(
                    session.character.id, catalog.folio_key(t.key, index)) > 0]
    tradition = _local(session)
    return [(tradition, index) for index in range(1, len(crafting.TEXTILE_TIERS))] if tradition else []


def _match_folio(session, target: str, *, owned: bool = False):
    wanted = _normalize(target)
    if not wanted:
        return None
    possibilities = _available_folios(session, owned=owned)
    exact = []
    partial = []
    for tradition, ti in possibilities:
        textile = crafting.TEXTILE_TIERS[ti]
        item = crafting.ITEMS_BY_KEY[catalog.folio_key(tradition.key, ti)]
        labels = (
            _normalize(item.name),
            _normalize(f"{tradition.name} {textile.name}"),
            _normalize(f"{textile.name} pattern"),
        )
        if wanted in labels:
            exact.append((tradition, ti))
        elif any(wanted in label for label in labels):
            partial.append((tradition, ti))
    matches = exact or partial
    return matches[0] if len(matches) == 1 else None


async def _train(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send(
            "Visit a regional tailor's hall. RECIPES TAILORING shows every teaching location.\r\n")
        return
    flag = catalog.lesson_flag(tradition.key, 0)
    if flag in _learned(session):
        await session.send(
            f"You already know {tradition.identity} apprentice patterns. "
            "BROWSE PATTERNS for advanced folios or check today's COMMISSION.\r\n")
        return
    session.database.grant_flag(session.character.id, flag)
    await session.send(
        f"{tradition.tailor} teaches you six {tradition.identity} cotton patterns. "
        "They are now in RECIPES TAILORING. Gather pigments, mix dye, "
        "cut regional lining and sew at a Loom / Sewing Bench.\r\n")


async def _browse(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send(
            "Pattern folios are sold by the nine master tailors. "
            "Use RECIPES TAILORING for their locations.\r\n")
        return
    skill = _skill(session)
    known = _learned(session)
    await session.send(
        f"\r\n=== {tradition.identity.upper()} PATTERN FOLIOS ===\r\n"
        f"{tradition.tailor}'s pattern table | Tailoring {skill}\r\n")
    for ti, textile in enumerate(crafting.TEXTILE_TIERS):
        if ti == 0:
            state = "LEARNED" if catalog.lesson_flag(tradition.key, ti) in known else "FREE LESSON"
            await session.send(f"  {textile.name:<14} {state} - TRAIN TAILORING\r\n")
        else:
            book = crafting.ITEMS_BY_KEY[catalog.folio_key(tradition.key, ti)]
            price = catalog.FOLIO_PRICES[ti]
            state = (
                "LEARNED" if catalog.lesson_flag(tradition.key, ti) in known
                else "CARRIED" if session.database.item_quantity(session.character.id, book.key) > 0
                else f"{price} sparks"
            )
            await session.send(
                f"  {book.name} - {state}; read at skill {textile.tailoring_skill}\r\n")
    await session.send(
        "BUY <full folio name> here; READ <folio name> from your inventory. "
        "Folios remain portable and may be traded with other players.\r\n")


async def _buy_folio(session, target: str) -> bool:
    selected = _match_folio(session, target)
    if selected is None:
        return False
    tradition, ti = selected
    book_key = catalog.folio_key(tradition.key, ti)
    price = catalog.FOLIO_PRICES[ti]
    checker = getattr(session, "can_receive_item", None)
    if callable(checker) and not checker(book_key, 1):
        await session.send("Your bag has no free slot for that pattern folio.\r\n")
        return True
    if not session.database.complete_merchant_purchase(
        session.character.id, item_key=book_key, quantity=1, total_price=price,
    ):
        await session.send(f"Not enough Sols for this folio ({price} sparks).\r\n")
        return True
    await session.send(
        f"You purchase {crafting.ITEMS_BY_KEY[book_key].name} for {price} sparks. "
        "READ it when your Tailoring skill reaches the required tier.\r\n")
    return True


async def _read_folio(session, target: str) -> bool:
    selected = _match_folio(session, target, owned=True)
    if selected is None:
        return False
    tradition, ti = selected
    textile = crafting.TEXTILE_TIERS[ti]
    current = _skill(session)
    if current < textile.tailoring_skill:
        await session.send(
            f"You need Tailoring {textile.tailoring_skill} to follow this "
            f"{textile.name} folio. Current skill: {current}.\r\n")
        return True
    flag = catalog.lesson_flag(tradition.key, ti)
    if flag in _learned(session):
        await session.send("You already know every pattern in this folio.\r\n")
        return True
    session.database.grant_flag(session.character.id, flag)
    await session.send(
        f"You study {tradition.identity} {textile.name} patterns. Six new "
        "regional designs are available in RECIPES TAILORING. "
        "The folio remains in your inventory for trading or lending.\r\n")
    return True


def _publish_secret(session, recipe) -> None:
    from mud.collective_wiki import WikiFact, record_wiki_entry
    room_key = session.character.current_room or ""
    room = ROOMS_BY_KEY.get(room_key)
    record_wiki_entry(
        session.database, category="recipe", entry_key=recipe.key,
        title=crafting.ITEMS_BY_KEY[recipe.output_item_key].name,
        summary="A hidden regional tailoring pattern recovered through exploration.",
        region_key=room.region_key if room is not None else "", room_key=room_key,
        facts=(WikiFact("pattern", "Recovered Master Pattern",
                       recipe.description, "tailoring_discovery"),),
        character_id=session.character.id, character_name=session.character.name,
    )


async def _study_secret(session, target: str) -> bool:
    tradition = _local(session)
    if tradition is None or _normalize(target) != _normalize(tradition.clue):
        return False
    recipe = catalog.RECIPES_BY_KEY[f"tailor_hidden_{tradition.key}"]
    flag = catalog.secret_flag(tradition.key)
    if flag not in _learned(session):
        session.database.grant_flag(session.character.id, flag)
        _publish_secret(session, recipe)
        await session.send(
            f"The {tradition.clue} reveals a forgotten sequence of folds and "
            f"reinforcing stitches. Secret pattern discovered: "
            f"{crafting.item_display_name(recipe.output_item_key)}.\r\n")
    else:
        await session.send("You recognize the hidden cutting sequence you have already recovered.\r\n")
    await economy._show_recipe_detail(session, crafting.item_display_name(recipe.output_item_key))
    return True


SCHEMA = """
CREATE TABLE IF NOT EXISTS tailoring_daily_commissions (
    character_id INTEGER NOT NULL,
    region_key TEXT NOT NULL,
    utc_day TEXT NOT NULL,
    output_item_key TEXT NOT NULL,
    reward_sparks INTEGER NOT NULL,
    reward_xp INTEGER NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (character_id, region_key, utc_day),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
"""


def _commission_offer(session, tradition, *, now: datetime | None = None):
    """Persist the day's request before displaying it, so skill changes cannot reroll it."""
    clock = now or datetime.now(timezone.utc)
    utc_day = clock.date().isoformat()
    character_id = session.character.id
    with session.database.connect() as db:
        db.execute(SCHEMA)
        existing = db.execute(
            """SELECT * FROM tailoring_daily_commissions
               WHERE character_id = ? AND region_key = ? AND utc_day = ?""",
            (character_id, tradition.key, utc_day),
        ).fetchone()
        if existing is not None:
            return dict(existing)

        skill = _skill(session)
        flags = _learned(session)
        learned = [
            ti for ti, tier in enumerate(crafting.TEXTILE_TIERS)
            if tier.tailoring_skill <= skill
            and catalog.lesson_flag(tradition.key, ti) in flags
        ]
        if not learned:
            return None
        ti = max(learned)
        textile = crafting.TEXTILE_TIERS[ti]
        index = (clock.date().toordinal() + list(catalog.BY_KEY).index(tradition.key)) % 3
        pattern = ("gloves", "vest", "banner")[index]
        output = catalog.piece_key(tradition.key, textile.key, pattern)
        reward = 9 + textile.tier * 6 + (3 if pattern == "vest" else 0)
        xp = 6 + textile.tier * 5
        db.execute(
            """INSERT OR IGNORE INTO tailoring_daily_commissions
               (character_id, region_key, utc_day, output_item_key, reward_sparks, reward_xp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (character_id, tradition.key, utc_day, output, reward, xp),
        )
        row = db.execute(
            """SELECT * FROM tailoring_daily_commissions
               WHERE character_id = ? AND region_key = ? AND utc_day = ?""",
            (character_id, tradition.key, utc_day),
        ).fetchone()
        return dict(row)


async def _commission(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send(
            "Daily tailoring commissions are posted at each regional tailor's hall. "
            "RECIPES TAILORING lists all nine locations.\r\n")
        return
    offer = _commission_offer(session, tradition)
    if offer is None:
        await session.send(
            f"{tradition.tailor} has a commission ready, but you must first "
            "TRAIN TAILORING to learn the local apprentice cuts.\r\n")
        return
    item = crafting.ITEMS_BY_KEY[offer["output_item_key"]]
    owned = session.database.item_quantity(session.character.id, item.key)
    state = "COMPLETE" if offer["completed_at"] else f"carrying {owned}/1"
    await session.send(
        f"\r\n=== {tradition.identity.upper()} DAILY COMMISSION ===\r\n"
        f"{tradition.tailor} requests 1x {item.name} ({state}).\r\n"
        f"Reward: {offer['reward_sparks']} sparks and {offer['reward_xp']} character XP.\r\n"
        f"UTC day: {offer['utc_day']}. One commission per region per UTC day. "
        "Today's request does not change if your skill rises.\r\n"
        "Make it through the ordinary crafting book, then COMMISSION TURN IN "
        "at this tailoring hall. Traded garments are accepted too.\r\n")


async def _turn_in(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send("Return to a regional tailoring hall to turn in its commission.\r\n")
        return
    offer = _commission_offer(session, tradition)
    if offer is None:
        await session.send("TRAIN TAILORING here before taking a daily commission.\r\n")
        return
    if offer["completed_at"]:
        await session.send("You've completed this hall's commission today. Come back tomorrow (UTC).\r\n")
        return

    from mud.item_heritage import (
        ensure_item_heritage_schema, retire_owned_instances_in_connection,
    )
    ensure_item_heritage_schema(session.database)
    character_id = session.character.id
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            """SELECT completed_at FROM tailoring_daily_commissions
               WHERE character_id = ? AND region_key = ? AND utc_day = ?""",
            (character_id, tradition.key, offer["utc_day"]),
        ).fetchone()
        if current is None or current["completed_at"] is not None:
            await session.send("This commission has already been completed or has expired.\r\n")
            return
        stack = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (character_id, offer["output_item_key"]),
        ).fetchone()
        if stack is None or int(stack["quantity"]) < 1:
            await session.send(
                f"You need 1x {crafting.item_display_name(offer['output_item_key'])} "
                "in your inventory to fulfill the commission.\r\n")
            return
        if int(stack["quantity"]) == 1:
            db.execute("DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                       (character_id, offer["output_item_key"]))
        else:
            db.execute(
                "UPDATE character_items SET quantity = quantity - 1 WHERE character_id = ? AND item_key = ?",
                (character_id, offer["output_item_key"]),
            )
        retire_owned_instances_in_connection(
            db, character_id=character_id, item_key=offer["output_item_key"],
            quantity=1, event_type="tailoring_commission",
            note=f"Delivered to {tradition.tailor} for a regional tailoring commission.",
        )
        character = db.execute(
            "SELECT experience FROM characters WHERE id = ?", (character_id,),
        ).fetchone()
        updated_xp = int(character["experience"]) + int(offer["reward_xp"])
        new_level = PROGRESSION_RULES.level_for_experience(updated_xp)
        db.execute(
            "UPDATE characters SET sols = sols + ?, experience = ?, level = ? WHERE id = ?",
            (offer["reward_sparks"], updated_xp, new_level, character_id),
        )
        db.execute(
            """UPDATE tailoring_daily_commissions SET completed_at = ?
               WHERE character_id = ? AND region_key = ? AND utc_day = ?""",
            (datetime.now(timezone.utc).isoformat(), character_id,
             tradition.key, offer["utc_day"]),
        )
    session.character = session.database.get_character_by_name(session.character.name)
    await session.send(
        f"{tradition.tailor} checks the seams and accepts your commission. "
        f"You receive {offer['reward_sparks']} sparks and {offer['reward_xp']} XP. "
        "The next request arrives tomorrow (UTC).\r\n")


async def show_crafting_studies(session) -> None:
    """Append regional teaching and commissions to RECIPES TAILORING."""
    flags = _learned(session)
    skill = _skill(session)
    learned = sum(
        catalog.lesson_flag(tradition.key, ti) in flags
        for tradition in catalog.TRADITIONS
        for ti in range(len(crafting.TEXTILE_TIERS))
    )
    total = len(catalog.TRADITIONS) * len(crafting.TEXTILE_TIERS)
    await session.send(
        f"\r\n=== REGIONAL TAILORING ===\r\n"
        f"Studied pattern collections: {learned}/{total} | "
        f"Masterwork secrets discovered: "
        f"{sum(catalog.secret_flag(t.key) in flags for t in catalog.TRADITIONS)}/"
        f"{len(catalog.TRADITIONS)}\r\n"
        "Nine traditions share one tailoring skill and the normal RECIPES, "
        "RECIPE and CRAFT commands.\r\n")
    for tradition in catalog.TRADITIONS:
        known = sum(catalog.lesson_flag(tradition.key, ti) in flags
                    for ti in range(len(crafting.TEXTILE_TIERS)))
        room = ROOMS_BY_KEY[tradition.hall]
        here = " (HERE)" if _local(session) == tradition else ""
        await session.send(
            f"  {tradition.identity}: {known}/7 collections - "
            f"{room.name}; teacher {tradition.tailor}{here}\r\n")
    await session.send(
        "At a regional hall: TRAIN TAILORING (free first patterns), "
        "BROWSE PATTERNS, BUY <folio>, READ <folio>, COMMISSION, "
        "COMMISSION TURN IN.\r\n"
        "Common pigments can be gathered near each homeland; "
        "higher cloth tiers require regional harvesting and skilled spinning.\r\n")
    if _local(session) is not None:
        await _commission(session)
        carried = _available_folios(session, owned=True)
        if carried:
            await session.send(
                "Carried folios: " + ", ".join(
                    crafting.ITEMS_BY_KEY[catalog.folio_key(t.key, ti)].name
                    for t, ti in carried[:8]
                ) + (" ..." if len(carried) > 8 else "") + "\r\n")


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    prior = self.__dict__.get("prompt")

    async def replay_prompt(_prompt: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = prior
        else:
            self.__dict__.pop("prompt", None)


def install_regional_tailoring_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_regional_tailoring_runtime_installed", False):
        return
    prior = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await prior(self)
            return
        current = getattr(self, "current_prompt_text", None)
        command = await self.prompt("\r\n" + (str(current()) if callable(current) else "> "))
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = _normalize(command)
        if normalized in {"train tailoring", "learn tailoring"}:
            await _train(self)
            return
        if normalized in {"browse patterns", "browse tailoring patterns", "tailoring patterns"}:
            await _browse(self)
            return
        if normalized.startswith("buy ") and _local(self) is not None:
            if await _buy_folio(self, normalized[4:]):
                return
        if normalized.startswith(("read ", "study ")):
            target = normalized.split(" ", 1)[1]
            if normalized.startswith("study ") and await _study_secret(self, target):
                return
            if await _read_folio(self, target):
                return
        if normalized.startswith(("examine ", "look ")):
            if await _study_secret(self, normalized.split(" ", 1)[1]):
                return
        if normalized in {"commission", "tailoring commission", "tailor commission",
                          "commissions", "tailoring commissions"}:
            await _commission(self)
            return
        if normalized in {"commission turn in", "turn in commission",
                          "tailoring turn in"}:
            await _turn_in(self)
            return
        await _delegate(self, prior, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._regional_tailoring_runtime_installed = True
