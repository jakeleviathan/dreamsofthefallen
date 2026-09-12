from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import mud.veyra_city as veyra
from mud.greywake_march import LANTERN_FLAG, LEDGER_FLAG, ROADWARDEN_FLAG
from mud.sablewater_reach import DROWNED_BRASS_SCRAP_KEY, SABLEWATER_NORTH_FERRY_KEY
from mud.waymeet_frontier import WAYMEET_GLOAM_MOUTH_KEY, WAYMEET_SCRIP_KEY


@dataclass(frozen=True, slots=True)
class MarketDemand:
    item_key: str
    bundle_size: int
    scrip_per_bundle: int


@dataclass(frozen=True, slots=True)
class MarketDay:
    key: str
    name: str
    description: str
    demands: tuple[MarketDemand, ...]


@dataclass(frozen=True, slots=True)
class WeeklyContract:
    key: str
    name: str
    description: str
    item_key: str
    quantity: int
    xp_reward: int
    scrip_reward: int


MARKET_DAYS: tuple[MarketDay, ...] = (
    MarketDay(
        "smiths_day",
        "Smiths' Day",
        "Repair crews and small forges buy raw metal and fuel faster than caravans can sort it.",
        (MarketDemand("iron_ore", 2, 1), MarketDemand("coal", 2, 1), MarketDemand("iron_ingot", 1, 1)),
    ),
    MarketDay(
        "cloth_day",
        "Cloth Day",
        "Tailors, ropewalks, boarding houses, and wagon crews all want ordinary fiber at once.",
        (MarketDemand("raw_cotton", 3, 1), MarketDemand("cotton_thread", 2, 1), MarketDemand("cotton_cloth", 1, 1)),
    ),
    MarketDay(
        "physickers_day",
        "Physickers' Day",
        "Hospices and apothecaries restock common medicines before they start paying rare-herb prices.",
        (MarketDemand("greenleaf", 3, 1), MarketDemand("bitterroot", 2, 1), MarketDemand("lavender_blossom", 3, 1)),
    ),
    MarketDay(
        "repair_day",
        "Repair Day",
        "The city buys the ugly useful things: hide, old fittings, and brass that can become something else.",
        (MarketDemand("rough_hide", 2, 1), MarketDemand(DROWNED_BRASS_SCRAP_KEY, 2, 2), MarketDemand("iron_ingot", 1, 1)),
    ),
    MarketDay(
        "caravan_day",
        "Caravan Day",
        "Outbound teams pay for processed stock because a wagon leaving at dusk does not care that raw materials are cheaper.",
        (MarketDemand("iron_ingot", 1, 1), MarketDemand("cotton_cloth", 1, 1), MarketDemand("cotton_thread", 2, 1)),
    ),
    MarketDay(
        "oddments_day",
        "Oddments Day",
        "Small specialists arrive looking for materials too peculiar to justify permanent stalls.",
        (MarketDemand("imp_horn", 2, 1), MarketDemand("lavender_blossom", 3, 1), MarketDemand(DROWNED_BRASS_SCRAP_KEY, 2, 2)),
    ),
    MarketDay(
        "civic_stores_day",
        "Civic Stores Day",
        "Public kitchens, repair sheds, clinics, and ward depots replenish basic reserves for the coming week.",
        (MarketDemand("iron_ore", 2, 1), MarketDemand("raw_cotton", 3, 1), MarketDemand("greenleaf", 3, 1)),
    ),
)


WEEKLY_CONTRACTS: tuple[WeeklyContract, ...] = (
    WeeklyContract(
        "bridge_stores",
        "Bridge Stores",
        "Grand Crossing is replacing sacrificial bearing pieces. Deliver ordinary iron before ordinary wear becomes an emergency.",
        "iron_ore",
        5,
        160,
        2,
    ),
    WeeklyContract(
        "hospice_dressings",
        "Hospice Dressings",
        "The public hospices want clean fiber for bandages and bedding before the next Greywake caravan arrives.",
        "raw_cotton",
        6,
        160,
        2,
    ),
    WeeklyContract(
        "greenhall_reserve",
        "Greenhall Reserve",
        "Greenhall is rebuilding its common-remedy shelf from ingredients beginners can actually gather.",
        "greenleaf",
        5,
        160,
        2,
    ),
    WeeklyContract(
        "river_reclamation",
        "River Reclamation",
        "Sablewater crews need reusable brass sorted out of the Drowned Tollhouse instead of left in the mud.",
        DROWNED_BRASS_SCRAP_KEY,
        3,
        200,
        3,
    ),
)


RANK_THRESHOLDS = {1: 0, 2: 3, 3: 7}
FACTION_NAMES = {
    "roadwarden": "Roadwarden Compact",
    "ledger": "Deep Ledger Consortium",
    "lantern": "Lantern Oath",
}
FACTION_OFFICES = {
    "roadwarden": veyra.VEYRA_ROADWARDEN_OFFICE_KEY,
    "ledger": veyra.VEYRA_LEDGER_OFFICE_KEY,
    "lantern": veyra.VEYRA_LANTERN_OFFICE_KEY,
}
FACTION_DUTY_ITEMS = {
    "roadwarden": ("iron_ingot", 1, "A replacement bridge fitting is due for the west freight bearing."),
    "ledger": (DROWNED_BRASS_SCRAP_KEY, 1, "The Consortium wants one verifiable reclaimed sample with provenance."),
    "lantern": ("greenleaf", 2, "The hospice shelf is below its published reserve line."),
}


_ORIGINAL_VAULT_CAPACITY = veyra._vault_capacity
_ORIGINAL_LISTING_CAPACITY = veyra._listing_capacity
_ORIGINAL_READ_BOARD = veyra._read_board


def market_day(on_date: date | None = None) -> MarketDay:
    current = on_date or date.today()
    return MARKET_DAYS[current.weekday()]


def weekly_contract(on_date: date | None = None) -> tuple[int, WeeklyContract]:
    current = on_date or date.today()
    iso = current.isocalendar()
    week_id = iso.year * 100 + iso.week
    contract = WEEKLY_CONTRACTS[iso.week % len(WEEKLY_CONTRACTS)]
    return week_id, contract


def ensure_living_core_tables(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS veyra_weekly_contracts (
                character_id INTEGER NOT NULL,
                week_id INTEGER NOT NULL,
                contract_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                PRIMARY KEY (character_id, week_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS veyra_faction_standing (
                character_id INTEGER PRIMARY KEY,
                faction_key TEXT NOT NULL,
                service_points INTEGER NOT NULL DEFAULT 0 CHECK (service_points >= 0),
                rank INTEGER NOT NULL DEFAULT 1 CHECK (rank BETWEEN 1 AND 3),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS veyra_faction_weekly_duties (
                character_id INTEGER NOT NULL,
                week_id INTEGER NOT NULL,
                faction_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                PRIMARY KEY (character_id, week_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _faction_key(session) -> str | None:
    if session.character is None:
        return None
    flags = set(session.database.list_flags(session.character.id))
    if ROADWARDEN_FLAG in flags:
        return "roadwarden"
    if LEDGER_FLAG in flags:
        return "ledger"
    if LANTERN_FLAG in flags:
        return "lantern"
    return None


def ensure_faction_standing(session) -> tuple[str, int, int] | None:
    if session.character is None:
        return None
    faction = _faction_key(session)
    if faction is None:
        return None
    flags = set(session.database.list_flags(session.character.id))
    if veyra.VEYRA_FACTION_RANK_FLAG not in flags:
        return None
    ensure_living_core_tables(session.database)
    with session.database.connect() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO veyra_faction_standing (character_id, faction_key, service_points, rank)
            VALUES (?, ?, 0, 1)
            """,
            (session.character.id, faction),
        )
        row = db.execute(
            "SELECT faction_key, service_points, rank FROM veyra_faction_standing WHERE character_id = ?",
            (session.character.id,),
        ).fetchone()
    if row is None:
        return None
    return str(row["faction_key"]), int(row["service_points"]), int(row["rank"])


def faction_rank(session) -> int:
    standing = ensure_faction_standing(session)
    return 0 if standing is None else standing[2]


def add_faction_service(session, amount: int = 1) -> int:
    standing = ensure_faction_standing(session)
    if standing is None or session.character is None:
        return 0
    ensure_living_core_tables(session.database)
    with session.database.connect() as db:
        db.execute(
            "UPDATE veyra_faction_standing SET service_points = service_points + ?, updated_at = CURRENT_TIMESTAMP WHERE character_id = ?",
            (max(0, amount), session.character.id),
        )
        row = db.execute(
            "SELECT service_points FROM veyra_faction_standing WHERE character_id = ?",
            (session.character.id,),
        ).fetchone()
    return int(row["service_points"]) if row else 0


def _rank_perk_text(faction: str, rank: int) -> str:
    if faction == "roadwarden":
        if rank >= 3:
            return "Rank III: priority rides reach Waymeet, Greywake, Sablewater, and Gloam Mouth. Tradeoff: 30 general Keyhouse item-units while active-service road kit occupies the rest."
        if rank >= 2:
            return "Rank II: priority rides also reach Sablewater. Tradeoff: 35 general Keyhouse item-units while active-service road kit occupies part of your allotment."
        return "Rank I: priority rides connect Veyra to Waymeet and Greywake."
    if faction == "ledger":
        if rank >= 3:
            return "Rank III: up to 9 Exchange listings. Tradeoff: general Keyhouse space falls to 30 item-units while bonded samples occupy reserved cages."
        if rank >= 2:
            return "Rank II: up to 7 Exchange listings. Tradeoff: general Keyhouse space falls to 35 item-units while bonded samples occupy reserved cages."
        return "Rank I: up to 5 Exchange listings."
    if rank >= 3:
        return "Rank III: 100 Keyhouse item-units. Tradeoff: only 2 simultaneous public Exchange listings under stricter chain-of-custody rules."
    if rank >= 2:
        return "Rank II: 80 Keyhouse item-units. Tradeoff: ordinary 3-listing Exchange cap remains in place."
    return "Rank I: 60 Keyhouse item-units."


def living_vault_capacity(session) -> int:
    base = _ORIGINAL_VAULT_CAPACITY(session)
    standing = ensure_faction_standing(session)
    if standing is None:
        return base
    faction, _points, rank = standing
    if faction == "lantern":
        return {1: max(base, 60), 2: 80, 3: 100}[rank]
    if faction in {"roadwarden", "ledger"} and rank >= 2:
        return 35 if rank == 2 else 30
    return base


def living_listing_capacity(session) -> int:
    base = _ORIGINAL_LISTING_CAPACITY(session)
    standing = ensure_faction_standing(session)
    if standing is None:
        return base
    faction, _points, rank = standing
    if faction == "ledger":
        return {1: max(base, 5), 2: 7, 3: 9}[rank]
    if faction == "lantern" and rank >= 3:
        return 2
    return base


def _item_name(item_key: str) -> str:
    item = veyra.crafting.ITEMS_BY_KEY.get(item_key)
    return item.name if item is not None else item_key.replace("_", " ").title()


async def _show_market_day(session) -> bool:
    if session.character is None or session.character.current_room not in {veyra.VEYRA_BRASSMARKET_KEY, veyra.VEYRA_NOTICE_HALL_KEY}:
        return False
    day = market_day()
    lines = [f"VEYRA MARKET DAY — {day.name}", day.description]
    for demand in day.demands:
        lines.append(f" - {_item_name(demand.item_key)}: {demand.bundle_size} for {demand.scrip_per_bundle} Waymeet Trade Scrip")
    lines.append("At Brassmarket use SELL DEMAND <qty> <item>. Partial bundles stay in your inventory.")
    await session.send("\r\n".join(lines) + "\r\n")
    return True


async def _sell_demand(session, quantity: int, item_text: str) -> bool:
    if session.character is None or session.character.current_room != veyra.VEYRA_BRASSMARKET_KEY:
        return False
    item = veyra._resolve_item(item_text)
    if item is None:
        await session.send("The demand desk cannot identify that item. Use its inventory name.\r\n")
        return True
    day = market_day()
    demand = next((entry for entry in day.demands if entry.item_key == item.key), None)
    if demand is None:
        await session.send(f"{_item_name(item.key)} is not on today's posted demand sheet. MARKET DAY shows today's buyers.\r\n")
        return True
    quantity = max(1, quantity)
    bundles = quantity // demand.bundle_size
    if bundles <= 0:
        await session.send(f"Today's buyers take {_item_name(item.key)} in bundles of {demand.bundle_size}.\r\n")
        return True
    consumed = bundles * demand.bundle_size
    if session.database.item_quantity(session.character.id, item.key) < consumed:
        await session.send(f"You do not have {consumed} x {_item_name(item.key)} available.\r\n")
        return True
    if not session.database.consume_item(session.character.id, item.key, consumed):
        await session.send("The sale could not be completed because your inventory changed.\r\n")
        return True
    payout = bundles * demand.scrip_per_bundle
    session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, payout)
    await session.send(f"The demand desk takes {consumed} x {_item_name(item.key)} and pays {payout} Waymeet Trade Scrip. Veyra's demand is a real material sink, not an infinite generic vendor.\r\n")
    return True


def _contract_row(session, week_id: int):
    if session.character is None:
        return None
    ensure_living_core_tables(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT contract_key, status FROM veyra_weekly_contracts WHERE character_id = ? AND week_id = ?",
            (session.character.id, week_id),
        ).fetchone()


async def _show_weekly_contract(session) -> bool:
    if session.character is None or session.character.current_room != veyra.VEYRA_NOTICE_HALL_KEY:
        return False
    week_id, contract = weekly_contract()
    row = _contract_row(session, week_id)
    state = "not accepted" if row is None else str(row["status"])
    await session.send(
        f"VEYRA WEEKLY CONTRACT {week_id} — {contract.name}\r\n"
        f"{contract.description}\r\n"
        f"Deliver {contract.quantity} x {_item_name(contract.item_key)}. Reward: {contract.xp_reward} XP, {contract.scrip_reward} Waymeet Trade Scrip, and 1 faction service point if you hold a ranked Veyra faction seal.\r\n"
        f"Status: {state}. Use ACCEPT CONTRACT, then TURN IN CONTRACT here.\r\n"
    )
    return True


async def _accept_weekly_contract(session) -> bool:
    if session.character is None or session.character.current_room != veyra.VEYRA_NOTICE_HALL_KEY:
        return False
    ensure_living_core_tables(session.database)
    week_id, contract = weekly_contract()
    row = _contract_row(session, week_id)
    if row is not None:
        await session.send(f"This week's contract is already {row['status']}.\r\n")
        return True
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO veyra_weekly_contracts (character_id, week_id, contract_key, status) VALUES (?, ?, ?, 'active')",
            (session.character.id, week_id, contract.key),
        )
    await session.send(f"Accepted weekly contract: {contract.name}. Deliver {contract.quantity} x {_item_name(contract.item_key)} to Notice Hall before the rotation changes.\r\n")
    return True


async def _turn_in_weekly_contract(session) -> bool:
    if session.character is None or session.character.current_room != veyra.VEYRA_NOTICE_HALL_KEY:
        return False
    ensure_living_core_tables(session.database)
    week_id, contract = weekly_contract()
    row = _contract_row(session, week_id)
    if row is None or str(row["status"]) != "active":
        await session.send("You do not have this week's Veyra contract active.\r\n")
        return True
    if session.database.item_quantity(session.character.id, contract.item_key) < contract.quantity:
        await session.send(f"The contract requires {contract.quantity} x {_item_name(contract.item_key)}.\r\n")
        return True
    if not session.database.consume_item(session.character.id, contract.item_key, contract.quantity):
        await session.send("The turn-in failed because your inventory changed.\r\n")
        return True
    session.database.add_experience(session.character.id, contract.xp_reward)
    session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, contract.scrip_reward)
    points = add_faction_service(session, 1)
    with session.database.connect() as db:
        db.execute(
            "UPDATE veyra_weekly_contracts SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE character_id = ? AND week_id = ?",
            (session.character.id, week_id),
        )
    veyra._refresh(session)
    extra = f" Faction service now {points} point(s)." if points else ""
    await session.send(f"Weekly contract complete: {contract.xp_reward} XP and {contract.scrip_reward} Waymeet Trade Scrip.{extra}\r\n")
    return True


async def _faction_status(session) -> bool:
    if session.character is None or session.character.current_room not in veyra.VEYRA_ROOM_KEYS:
        return False
    standing = ensure_faction_standing(session)
    if standing is None:
        await session.send("Your Greywake alignment has not yet become ranked Veyra service. Complete One Office, One Obligation first.\r\n")
        return True
    faction, points, rank = standing
    next_text = "maximum authored rank" if rank >= 3 else f"Rank {rank + 1} requires {RANK_THRESHOLDS[rank + 1]} service points"
    await session.send(
        f"{FACTION_NAMES[faction]} — Rank {rank}, {points} service point(s); {next_text}.\r\n"
        f"{_rank_perk_text(faction, rank)}\r\n"
        "Public weekly contracts and one faction duty per weekly rotation build service. Promotion is explicit at your faction office.\r\n"
    )
    return True


def _duty_row(session, week_id: int):
    if session.character is None:
        return None
    ensure_living_core_tables(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT faction_key, status FROM veyra_faction_weekly_duties WHERE character_id = ? AND week_id = ?",
            (session.character.id, week_id),
        ).fetchone()


async def _faction_duty(session, accept: bool = False, turn_in: bool = False) -> bool:
    if session.character is None:
        return False
    standing = ensure_faction_standing(session)
    if standing is None:
        return False
    faction, _points, _rank = standing
    if session.character.current_room != FACTION_OFFICES[faction]:
        return False
    week_id, _contract = weekly_contract()
    item_key, qty, description = FACTION_DUTY_ITEMS[faction]
    row = _duty_row(session, week_id)
    if accept:
        if row is not None:
            await session.send(f"This week's faction duty is already {row['status']}.\r\n")
            return True
        with session.database.connect() as db:
            db.execute(
                "INSERT INTO veyra_faction_weekly_duties (character_id, week_id, faction_key, status) VALUES (?, ?, ?, 'active')",
                (session.character.id, week_id, faction),
            )
        await session.send(f"Faction duty accepted. {description} Bring {qty} x {_item_name(item_key)} and TURN IN FACTION DUTY here.\r\n")
        return True
    if turn_in:
        if row is None or str(row["status"]) != "active":
            await session.send("You do not have an active faction duty this week.\r\n")
            return True
        if session.database.item_quantity(session.character.id, item_key) < qty:
            await session.send(f"Duty requires {qty} x {_item_name(item_key)}.\r\n")
            return True
        if not session.database.consume_item(session.character.id, item_key, qty):
            await session.send("The duty turn-in failed because your inventory changed.\r\n")
            return True
        session.database.add_experience(session.character.id, 110)
        session.database.add_item(session.character.id, WAYMEET_SCRIP_KEY, 1)
        points = add_faction_service(session, 1)
        with session.database.connect() as db:
            db.execute(
                "UPDATE veyra_faction_weekly_duties SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE character_id = ? AND week_id = ?",
                (session.character.id, week_id),
            )
        veyra._refresh(session)
        await session.send(f"Faction duty complete: 110 XP, 1 Waymeet Trade Scrip, and 1 service point. Standing: {points}.\r\n")
        return True
    state = "not accepted" if row is None else str(row["status"])
    await session.send(f"Weekly {FACTION_NAMES[faction]} duty: {description} Deliver {qty} x {_item_name(item_key)}. Status: {state}. Use ACCEPT FACTION DUTY or TURN IN FACTION DUTY.\r\n")
    return True


async def _promote(session) -> bool:
    if session.character is None:
        return False
    standing = ensure_faction_standing(session)
    if standing is None:
        return False
    faction, points, rank = standing
    if session.character.current_room != FACTION_OFFICES[faction]:
        return False
    if rank >= 3:
        await session.send("Rank III is the highest Veyra faction rank authored in the current progression band.\r\n")
        return True
    needed = RANK_THRESHOLDS[rank + 1]
    if points < needed:
        await session.send(f"Promotion requires {needed} service points; you currently have {points}.\r\n")
        return True
    new_rank = rank + 1
    with session.database.connect() as db:
        db.execute(
            "UPDATE veyra_faction_standing SET rank = ?, updated_at = CURRENT_TIMESTAMP WHERE character_id = ?",
            (new_rank, session.character.id),
        )
    await session.send(f"{FACTION_NAMES[faction]} promotion accepted: Rank {new_rank}. {_rank_perk_text(faction, new_rank)}\r\n")
    return True


async def _expanded_ride(session, destination: str) -> bool:
    if session.character is None or session.character.current_room != veyra.VEYRA_CARAVAN_COURT_KEY:
        return False
    standing = ensure_faction_standing(session)
    if standing is None or standing[0] != "roadwarden":
        return False
    _faction, _points, rank = standing
    destinations = {
        "sablewater": (2, SABLEWATER_NORTH_FERRY_KEY, "Sablewater North Ferry"),
        "gloam": (3, WAYMEET_GLOAM_MOUTH_KEY, "Gloam Mouth"),
    }
    if destination not in destinations:
        return False
    needed, room_key, label = destinations[destination]
    if rank < needed:
        await session.send(f"Roadwarden Rank {needed} is required for priority transit to {label}.\r\n")
        return True
    session.database.set_character_room(session.character.id, room_key)
    veyra._refresh(session)
    await session.send(f"A Roadwarden dispatch wagon takes the maintained corridor to {label}.\r\n")
    await session.show_current_room()
    return True


async def living_board(session) -> bool:
    handled = await _ORIGINAL_READ_BOARD(session)
    if not handled:
        return False
    day = market_day()
    week_id, contract = weekly_contract()
    await session.send(
        f" - Today's Brassmarket demand: {day.name}. Use MARKET DAY for posted bundles.\r\n"
        f" - Weekly contract {week_id}: {contract.name}. Use CONTRACT at Notice Hall.\r\n"
    )
    return True


def install_veyra_living_core_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_veyra_living_core_installed", False):
        return

    # Layer faction rank consequences into the services already owned by veyra_city.
    veyra._vault_capacity = living_vault_capacity
    veyra._listing_capacity = living_listing_capacity
    veyra._read_board = living_board

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None and self.character.current_room in veyra.VEYRA_ROOM_KEYS:
            ensure_living_core_tables(self.database)
            ensure_faction_standing(self)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        handled = False

        if normalized in {"market day", "demand", "today's demand", "todays demand"}:
            handled = await _show_market_day(self)
        elif normalized.startswith("sell demand "):
            rest = normalized[len("sell demand "):]
            parts = rest.split(" ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                handled = await _sell_demand(self, int(parts[0]), parts[1])
        elif normalized in {"contract", "weekly contract", "contract board"}:
            handled = await _show_weekly_contract(self)
        elif normalized == "accept contract":
            handled = await _accept_weekly_contract(self)
        elif normalized in {"turn in contract", "turnin contract"}:
            handled = await _turn_in_weekly_contract(self)
        elif normalized in {"faction status", "faction rank", "standing"}:
            handled = await _faction_status(self)
        elif normalized in {"faction duty", "weekly duty"}:
            handled = await _faction_duty(self)
        elif normalized == "accept faction duty":
            handled = await _faction_duty(self, accept=True)
        elif normalized in {"turn in faction duty", "turnin faction duty"}:
            handled = await _faction_duty(self, turn_in=True)
        elif normalized in {"faction promote", "request promotion", "promote"}:
            handled = await _promote(self)
        elif normalized in {"ride sablewater", "ride sablewater ferry"}:
            handled = await _expanded_ride(self, "sablewater")
        elif normalized in {"ride gloam", "ride gloam mouth"}:
            handled = await _expanded_ride(self, "gloam")

        if handled:
            return

        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str):
            return command

        self.prompt = replay_prompt
        try:
            await previous_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._veyra_living_core_installed = True
