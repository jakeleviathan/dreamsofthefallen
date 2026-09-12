from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment
from mud.combat import EnemyDefinition, EnemyState
from mud.equipment_system import equipped_item_keys
from mud.gloamworks_dungeon import BURIED_REGENT_KEY
from mud.gravewatch_keep import CASTELLAN_KEY
from mud.greywake_march import GREYWAKE_SIGNAL_HILL_KEY, GREYWAKE_THREE_BANNER_KEY
from mud.party_system import _party_for_session
from mud.sablewater_reach import (
    BRASS_AUDITOR_KEY,
    SABLEWATER_EEL_DOCK_KEY,
    SABLEWATER_HERON_FLATS_KEY,
    SABLEWATER_REED_FARMS_KEY,
)
from mud.trade_experience import _cancel_invites_for, _cancel_trade_for
from mud.veyra_city import VEYRA_BRASSMARKET_KEY, VEYRA_GRAND_CROSSING_KEY, VEYRA_PUBLIC_HEARTH_KEY
from mud.veyra_underclock import GOVERNOR_KEY
from mud.waymeet_frontier import (
    WAYMEET_BRIARCUT_KEY,
    WAYMEET_BROKEN_MILE_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
    WAYMEET_QUARRY_KEY,
    WAYMEET_SCRIP_KEY,
)
from mud.world import ROOMS_BY_KEY


LIVING_WORLD_VERSION = "1.0.0"
ROOM_STORAGE_CAPACITY = 20
ROOM_DISPLAY_SLOTS = 5
ROOM_RENT_COST_SCRIP = 2
PRIVATE_ROOM_PREFIX = "living_private_room_"

SOCIAL_HUBS = {
    WAYMEET_COMMONHOUSE_KEY: "Waymeet Commonhouse Yard",
    VEYRA_PUBLIC_HEARTH_KEY: "Veyra Public Hearth",
}


@dataclass(frozen=True, slots=True)
class DailyPulse:
    key: str
    kind: str
    headline: str
    summary: str
    gossip: str
    room_key: str
    room_name: str
    command_hint: str = ""
    resource_node: str = ""
    threat_key: str = ""
    merchant_wares: tuple[tuple[str, int], ...] = ()


MIREHORN_STRAY = EnemyDefinition(
    key="living_mirehorn_stray",
    name="Mirehorn Stray",
    aliases=("mirehorn", "stray", "mirehorn stray"),
    description="a mud-dark antlered grazer driven too close to the road, wild-eyed and striking at anything that corners it",
    max_hp=62,
    armor_class=8,
    auto_attack_damage=7,
    auto_attack_interval=3.2,
    xp_reward=48,
    retaliates=True,
)
ASHWING_MARAUDER = EnemyDefinition(
    key="living_ashwing_marauder",
    name="Ashwing Marauder",
    aliases=("ashwing", "marauder", "ashwing marauder"),
    description="a broad black kite with ember-gray feathers and a habit of diving at packs, signal cloth, and exposed hands",
    max_hp=74,
    armor_class=10,
    auto_attack_damage=8,
    auto_attack_interval=3.0,
    xp_reward=58,
    retaliates=True,
)
FLOODJAW_SCAVENGER = EnemyDefinition(
    key="living_floodjaw_scavenger",
    name="Floodjaw Scavenger",
    aliases=("floodjaw", "scavenger", "floodjaw scavenger"),
    description="a long-backed floodplain predator nosing through ferry refuse, its jaw scarred white by old hooks",
    max_hp=86,
    armor_class=11,
    auto_attack_damage=9,
    auto_attack_interval=3.1,
    xp_reward=68,
    retaliates=True,
)
LIVING_EVENT_ENEMIES = (MIREHORN_STRAY, ASHWING_MARAUDER, FLOODJAW_SCAVENGER)


PULSE_TEMPLATES: tuple[DailyPulse, ...] = (
    DailyPulse(
        key="copperwake_caravan",
        kind="merchant",
        headline="A copper-painted caravan has made Waymeet before dusk.",
        summary=(
            "A small itinerant factor is unloading practical surplus at Lantern Market. "
            "Nothing is exclusive, but the stock is cheaper to reach than its usual source."
        ),
        gossip="'Copperwake made good time. Nix is pretending not to watch their prices.'",
        room_key=WAYMEET_LANTERN_MARKET_KEY,
        room_name="Waymeet Lantern Market",
        command_hint="BROWSE WANDERER",
        merchant_wares=(("iron_ore", 1), ("raw_cotton", 1), ("greenleaf", 1)),
    ),
    DailyPulse(
        key="glass_thread_peddler",
        kind="merchant",
        headline="A high-road peddler is trading oddments in Veyra.",
        summary=(
            "A Moon Elf peddler has set a folding tray near Brassmarket with small useful materials "
            "collected from several roads."
        ),
        gossip="'The peddler swears every piece has a story. Pikka says the stories cost nothing, which is suspicious.'",
        room_key=VEYRA_BRASSMARKET_KEY,
        room_name="Veyra Brassmarket",
        command_hint="BROWSE WANDERER",
        merchant_wares=(("lavender_blossom", 1), ("cotton_thread", 1), ("coal", 1)),
    ),
    DailyPulse(
        key="briar_bloom",
        kind="resource",
        headline="Warm rain has pushed lavender into the Briarcut margins.",
        summary=(
            "For this Astralis day, a temporary lavender patch can be harvested in the Briarcut Fields. "
            "The patch disappears naturally when the pulse changes."
        ),
        gossip="'Smells like lavender south of the road. That is better than smelling like jackal.'",
        room_key=WAYMEET_BRIARCUT_KEY,
        room_name="Briarcut Fields",
        command_hint="RESOURCES",
        resource_node="lavender_patch",
    ),
    DailyPulse(
        key="quarry_green",
        kind="resource",
        headline="A wet crack in the old quarry has exposed a stubborn greenleaf shelf.",
        summary=(
            "Greenleaf is temporarily gatherable beside the quarry spoil. It is a small shift in the land, "
            "not a permanent new node."
        ),
        gossip="'Hedda says plants growing out of quarry stone are showing off.'",
        room_key=WAYMEET_QUARRY_KEY,
        room_name="Old Waymeet Quarry",
        command_hint="RESOURCES",
        resource_node="greenleaf_patch",
    ),
    DailyPulse(
        key="sablewater_bitterroot",
        kind="resource",
        headline="Low water has uncovered bitterroot along the Reed Farms drainage ditch.",
        summary="A temporary bitterroot cluster is reachable at the Reed Farms until the next Astralis day.",
        gossip="'The farmers are pulling bitterroot with one hand and complaining about mud with the other.'",
        room_key=SABLEWATER_REED_FARMS_KEY,
        room_name="Sablewater Reed Farms",
        command_hint="RESOURCES",
        resource_node="bitterroot_cluster",
    ),
    DailyPulse(
        key="mirehorn_road",
        kind="threat",
        headline="Something antlered has been overturning packs along the Broken Mile.",
        summary=(
            "Wardens have tracked a Mirehorn Stray to the Broken Mile. It is a small roaming disturbance, "
            "not a formal quest."
        ),
        gossip="'Korr says it is frightened, dangerous, and still capable of kicking your ribs inward.'",
        room_key=WAYMEET_BROKEN_MILE_KEY,
        room_name="The Broken Mile",
        command_hint="HUNT DISTURBANCE",
        threat_key=MIREHORN_STRAY.key,
    ),
    DailyPulse(
        key="ashwing_signal",
        kind="threat",
        headline="An Ashwing has started tearing signal cloth from Greywake Hill.",
        summary="A large marauding kite is disrupting the signal post on Greywake Signal Hill.",
        gossip="'The Roadwardens keep replacing the red pennant. The bird keeps taking it personally.'",
        room_key=GREYWAKE_SIGNAL_HILL_KEY,
        room_name="Greywake Signal Hill",
        command_hint="HUNT DISTURBANCE",
        threat_key=ASHWING_MARAUDER.key,
    ),
    DailyPulse(
        key="floodjaw_dock",
        kind="threat",
        headline="Eelmarket workers are keeping one side of the dock suspiciously empty.",
        summary="A Floodjaw Scavenger has learned that fish refuse means easy food and crowded planks mean easier panic.",
        gossip="'Nobody owns the fish guts. Apparently the Floodjaw disagrees.'",
        room_key=SABLEWATER_EEL_DOCK_KEY,
        room_name="Eelmarket Dock",
        command_hint="HUNT DISTURBANCE",
        threat_key=FLOODJAW_SCAVENGER.key,
    ),
    DailyPulse(
        key="three_banner_story",
        kind="story",
        headline="Three-Banner Camp is arguing over the same broken cart in three different ways.",
        summary=(
            "The Roadwardens want it moved, the Deep Ledger wants the cargo counted, and the Lantern Oath wants "
            "the leaking lamp oil contained first. Travelers are already retelling the argument."
        ),
        gossip="'Same cart, three emergencies. That is Greywake in one sentence.'",
        room_key=GREYWAKE_THREE_BANNER_KEY,
        room_name="Three-Banner Camp",
        command_hint="GOSSIP",
    ),
    DailyPulse(
        key="heron_roost",
        kind="story",
        headline="Hundreds of white herons have crowded onto the Sablewater flats.",
        summary=(
            "The migration has turned Heron Flats into a noisy white field of wings. Ferrymen are taking the long route "
            "rather than disturb the roost."
        ),
        gossip="'If you stand still at Heron Flats, the birds eventually decide you are furniture.'",
        room_key=SABLEWATER_HERON_FLATS_KEY,
        room_name="Heron Flats",
        command_hint="LOOK",
    ),
    DailyPulse(
        key="commonhouse_song",
        kind="story",
        headline="A traveling singer has learned a Waymeet song incorrectly and refuses correction.",
        summary=(
            "The Commonhouse has acquired a loud new version of an old road song. Every homeland represented in the room "
            "claims one verse is wrong."
        ),
        gossip="'The singer rhymed Veyra with briar. Nobody has forgiven him.'",
        room_key=WAYMEET_COMMONHOUSE_KEY,
        room_name="Waymeet Commonhouse Yard",
        command_hint="TAVERN WHO",
    ),
    DailyPulse(
        key="crossing_repair",
        kind="story",
        headline="Grand Crossing is wearing a fresh patch no single culture can claim.",
        summary=(
            "A cracked bridge plate was repaired by a mixed crew using Dwarven measurements, Goblin shims, Human horn pins, "
            "and Sporekin binding fiber."
        ),
        gossip="'The repair ledger has four signatures and one thumbprint.'",
        room_key=VEYRA_GRAND_CROSSING_KEY,
        room_name="Veyra Grand Crossing",
        command_hint="LOOK",
    ),
)


BOSS_FIRSTS = {
    BURIED_REGENT_KEY: "the Buried Regent",
    BRASS_AUDITOR_KEY: "the Brass Auditor",
    GOVERNOR_KEY: "the Cinder Governor",
    CASTELLAN_KEY: "the Last Castellan",
}
LEVEL_FIRSTS = (5, 8, 10)

_RESOURCE_SHIFT_STATE: tuple[int, str, str, bool] | None = None


def pulse_for_day(day_number: int) -> DailyPulse:
    digest = hashlib.sha256(f"dreams-living-world-v1:{int(day_number)}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(PULSE_TEMPLATES)
    return PULSE_TEMPLATES[index]


def rare_world_moment(moment: AstralisMoment) -> str | None:
    if moment.day_number % 137 == 61 and moment.phase == "night":
        return "violet_moon"
    return None


def _private_room_key(character_id: int) -> str:
    return f"{PRIVATE_ROOM_PREFIX}{int(character_id)}"


def _is_private_room(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == _private_room_key(character.id))


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _parse_quantity(text: str) -> tuple[int, str]:
    parts = text.strip().split()
    if not parts:
        return 1, ""
    if parts[0].isdigit():
        return max(1, int(parts[0])), " ".join(parts[1:])
    return 1, text.strip()


def _item_label(item_key: str) -> str:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    return item.name if item is not None else item_key.replace("_", " ").title()


def _resolve_inventory_item(session, text: str) -> tuple[str | None, str | None]:
    character = getattr(session, "character", None)
    if character is None:
        return None, "No active character."
    wanted = _normalize(text)
    if not wanted:
        return None, "Name an item."
    exact: list[str] = []
    partial: list[str] = []
    for row in session.database.list_items(character.id):
        key = str(row["item_key"])
        if int(row["quantity"]) <= 0:
            continue
        item = crafting.ITEMS_BY_KEY.get(key)
        names = {_normalize(key)}
        if item is not None:
            names.add(_normalize(item.name))
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "You do not carry an item by that name."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(_item_label(key) for key in matches) + "."
    return matches[0], None


def _equipped_reserve(session, item_key: str) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return 0
    equipped = equipped_item_keys(session.database, character.id)
    return sum(1 for value in equipped.values() if value == item_key)


def ensure_living_world_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS living_world_chronicle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                astralis_day INTEGER NOT NULL,
                character_id INTEGER,
                character_name TEXT,
                category TEXT NOT NULL,
                entry_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS living_character_state (
                character_id INTEGER PRIMARY KEY,
                last_seen_day INTEGER NOT NULL,
                last_room_hint_day INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_mail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                astralis_day INTEGER NOT NULL,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(character_id, astralis_day, subject),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_event_participation (
                character_id INTEGER NOT NULL,
                astralis_day INTEGER NOT NULL,
                pulse_key TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, astralis_day, pulse_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_quarters (
                character_id INTEGER PRIMARY KEY,
                hub_room_key TEXT NOT NULL,
                rented_day INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_room_storage (
                character_id INTEGER NOT NULL,
                item_key TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                PRIMARY KEY (character_id, item_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_room_display (
                character_id INTEGER NOT NULL,
                slot_number INTEGER NOT NULL CHECK (slot_number BETWEEN 1 AND 5),
                item_key TEXT NOT NULL,
                PRIMARY KEY (character_id, slot_number),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _chronicle_insert(database, *, event_key: str, day: int, category: str, text: str, character_id: int | None = None, character_name: str | None = None) -> bool:
    ensure_living_world_schema(database)
    with database.connect() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO living_world_chronicle
            (event_key, astralis_day, character_id, character_name, category, entry_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_key, int(day), character_id, character_name, category, text),
        )
    return bool(cursor.rowcount)


def latest_chronicle(database, limit: int = 8) -> list[dict[str, object]]:
    ensure_living_world_schema(database)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT id, astralis_day, character_name, category, entry_text
            FROM living_world_chronicle
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(25, int(limit))),),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "astralis_day": int(row["astralis_day"]),
            "character_name": row["character_name"],
            "category": str(row["category"]),
            "entry_text": str(row["entry_text"]),
        }
        for row in rows
    ]


def _sync_resource_shift(moment: AstralisMoment) -> DailyPulse:
    global _RESOURCE_SHIFT_STATE
    pulse = pulse_for_day(moment.day_number)
    if _RESOURCE_SHIFT_STATE is not None and _RESOURCE_SHIFT_STATE[0] != moment.day_number:
        _, old_room, old_node, was_added = _RESOURCE_SHIFT_STATE
        if was_added:
            current = list(economy.ROOM_RESOURCE_NODE_KEYS.get(old_room, ()))
            if old_node in current:
                current.remove(old_node)
                if current:
                    economy.ROOM_RESOURCE_NODE_KEYS[old_room] = tuple(current)
                else:
                    economy.ROOM_RESOURCE_NODE_KEYS.pop(old_room, None)
        _RESOURCE_SHIFT_STATE = None

    if pulse.kind == "resource":
        current = list(economy.ROOM_RESOURCE_NODE_KEYS.get(pulse.room_key, ()))
        added = pulse.resource_node not in current
        if added:
            current.append(pulse.resource_node)
            economy.ROOM_RESOURCE_NODE_KEYS[pulse.room_key] = tuple(current)
        _RESOURCE_SHIFT_STATE = (moment.day_number, pulse.room_key, pulse.resource_node, added)
    return pulse


def _register_event_enemies() -> None:
    additions = []
    for definition in LIVING_EVENT_ENEMIES:
        if definition.key not in combat.ENEMIES_BY_KEY:
            additions.append(definition)
        combat.ENEMIES_BY_KEY[definition.key] = definition
    if additions:
        combat.ENEMIES = combat.ENEMIES + tuple(additions)


def install_living_world_content() -> None:
    _register_event_enemies()


def _room_hint_seen(session, day: int) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return True
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT last_room_hint_day FROM living_character_state WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    return bool(row and int(row["last_room_hint_day"]) == int(day))


def _mark_room_hint_seen(session, day: int) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """
            INSERT INTO living_character_state (character_id, last_seen_day, last_room_hint_day)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id) DO UPDATE SET last_room_hint_day = excluded.last_room_hint_day
            """,
            (character.id, int(day), int(day)),
        )


async def _send_room_pulse_if_here(session) -> bool:
    character = getattr(session, "character", None)
    if character is None or _is_private_room(session):
        return False
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    if character.current_room != pulse.room_key or _room_hint_seen(session, moment.day_number):
        return False
    _mark_room_hint_seen(session, moment.day_number)
    await session.send(
        f"\r\n[The world today] {pulse.headline}\r\n"
        f"{pulse.summary}\r\n"
        + (f"Hint: {pulse.command_hint}\r\n" if pulse.command_hint else "")
    )
    return True


def _rare_moon_text(session, moment: AstralisMoment) -> str | None:
    if rare_world_moment(moment) != "violet_moon":
        return None
    character = getattr(session, "character", None)
    if character is None or _is_private_room(session):
        return None
    room = ROOMS_BY_KEY.get(character.current_room or "")
    if room is None:
        return None
    if room.region_key in {"gloamworks", "drowned_tollhouse", "veyra_underclock"}:
        return None
    if character.race == "moon_elf":
        return (
            "Above Astralis, the moon has gone violet. High Horizon has no doctrine for it; "
            "that absence is already becoming part of the conversation."
        )
    return "Above the roofs and roads, the moon is unmistakably violet tonight. People keep stopping mid-sentence to look."


def _record_rare_moment(database, moment: AstralisMoment) -> None:
    if rare_world_moment(moment) != "violet_moon":
        return
    _chronicle_insert(
        database,
        event_key=f"world:violet_moon:{moment.day_number}",
        day=moment.day_number,
        category="world",
        text=f"On Astralis Day {moment.day_number}, the moon turned violet for one night. No accepted explanation was recorded.",
    )


async def _show_dispatch(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    _record_rare_moment(session.database, moment)
    rare = rare_world_moment(moment)
    await session.send(
        "\r\n--- Astralis Dispatch ---\r\n"
        f"{moment.calendar_display}\r\n"
        f"Today: {pulse.headline}\r\n"
        f"{pulse.summary}\r\n"
        f"Where people are talking about it: {pulse.room_name}.\r\n"
    )
    if pulse.command_hint:
        await session.send(f"If you find it yourself: {pulse.command_hint}.\r\n")
    if rare == "violet_moon":
        await session.send("\r\nUNUSUAL SKY: The moon is violet tonight. No task is attached to it. People are simply noticing.\r\n")
    rows = latest_chronicle(session.database, 3)
    if rows:
        await session.send("\r\nRecent names in the public chronicle:\r\n")
        for row in rows:
            await session.send(f"- Day {row['astralis_day']}: {row['entry_text']}\r\n")
    await session.send("\r\nThis dispatch is news, not a daily quest. Nothing here expires as a punishment for not logging in.\r\n")


async def _show_gossip(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    rare = rare_world_moment(moment)
    await session.send("\r\n--- What People Are Saying ---\r\n")
    await session.send(pulse.gossip + "\r\n")
    if rare == "violet_moon":
        character = getattr(session, "character", None)
        if character is not None and character.race == "moon_elf":
            await session.send("'High Horizon has six explanations and has officially adopted none of them.'\r\n")
        else:
            await session.send("'Nobody has agreed on why the moon is violet. That has not stopped anyone from explaining it.'\r\n")
    rows = latest_chronicle(session.database, 2)
    for row in rows:
        await session.send(f"Someone adds: \"{row['entry_text']}\"\r\n")


async def _show_chronicle(session, limit: int = 10) -> None:
    rows = latest_chronicle(session.database, limit)
    await session.send("\r\n--- The Astralis Chronicle ---\r\n")
    if not rows:
        await session.send("The public pages are still mostly blank. The world is waiting for names.\r\n")
        return
    for row in rows:
        await session.send(f"Day {row['astralis_day']}: {row['entry_text']}\r\n")
    await session.send("These entries record shared happenings and server firsts. They are history, not a leaderboard.\r\n")


def _event_done(session, day: int, pulse_key: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT 1 FROM living_event_participation WHERE character_id = ? AND astralis_day = ? AND pulse_key = ?",
            (character.id, int(day), pulse_key),
        ).fetchone()
    return row is not None


def _mark_event_done(session, day: int, pulse: DailyPulse) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO living_event_participation (character_id, astralis_day, pulse_key) VALUES (?, ?, ?)",
            (character.id, int(day), pulse.key),
        )
    return bool(cursor.rowcount)


async def _browse_wanderer(session) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    if pulse.kind != "merchant" or character.current_room != pulse.room_key:
        return False
    await session.send(f"\r\n--- Wandering Stock: {pulse.headline} ---\r\n")
    for item_key, cost in pulse.merchant_wares:
        await session.send(f"{_item_label(item_key)} - {cost} Waymeet Trade Scrip\r\n")
    await session.send("BUY WANDERER <item> purchases one. The stock leaves when the Astralis day changes.\r\n")
    return True


async def _buy_wanderer(session, item_text: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    if pulse.kind != "merchant" or character.current_room != pulse.room_key:
        return False
    wanted = _normalize(item_text)
    match = None
    for item_key, cost in pulse.merchant_wares:
        if wanted in {_normalize(item_key), _normalize(_item_label(item_key))}:
            match = (item_key, cost)
            break
    if match is None:
        await session.send("The wanderer is not carrying that today. Use BROWSE WANDERER.\r\n")
        return True
    item_key, cost = match
    if session.database.item_quantity(character.id, WAYMEET_SCRIP_KEY) < cost:
        await session.send(f"You need {cost} Waymeet Trade Scrip.\r\n")
        return True
    session.database.consume_item(character.id, WAYMEET_SCRIP_KEY, cost)
    session.database.add_item(character.id, item_key, 1)
    await session.send(f"You trade {cost} scrip for 1x {_item_label(item_key)}.\r\n")
    return True


async def _hunt_disturbance(session) -> bool:
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if character is None or combatant is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    if pulse.kind != "threat" or character.current_room != pulse.room_key:
        return False
    if getattr(session, "active_enemy", None) is not None:
        await session.send("Finish the fight you are already in first.\r\n")
        return True
    if _event_done(session, moment.day_number, pulse.key):
        await session.send("You already helped quiet this disturbance today. The wardens do not need you to farm it.\r\n")
        return True
    definition = combat.ENEMIES_BY_KEY[pulse.threat_key]
    enemy = EnemyState(definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(character.id, 1.0)
    session._living_event_enemy = (id(enemy), moment.day_number, pulse.key)
    await session.send(
        f"You follow the fresh sign until {definition.name} wheels on you. Your normal attacks begin automatically.\r\n"
    )
    await session.send_client_state()
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))
    return True


def _character_state(database, character_id: int):
    ensure_living_world_schema(database)
    with database.connect() as db:
        return db.execute(
            "SELECT last_seen_day, last_room_hint_day FROM living_character_state WHERE character_id = ?",
            (character_id,),
        ).fetchone()


def _create_return_letter(session, from_day: int, to_day: int) -> bool:
    character = getattr(session, "character", None)
    if character is None or to_day <= from_day:
        return False
    pulse = pulse_for_day(to_day)
    recent = latest_chronicle(session.database, 1)
    chronicle_note = f" The public board also carries this line: {recent[0]['entry_text']}" if recent else ""
    sender = "Pikka Ninepins, Veyra Exchange" if int(character.level) >= 8 else "Waymeet Road Post"
    subject = f"While you were away — Day {to_day}"
    body = (
        f"You were away for {to_day - from_day} Astralis day{'s' if to_day - from_day != 1 else ''}. "
        f"The roads did not wait for you. {pulse.headline} {pulse.summary}{chronicle_note} "
        "Nothing in this letter is a missed reward. It is simply what changed while you were gone."
    )
    with session.database.connect() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO living_mail (character_id, astralis_day, sender, subject, body) VALUES (?, ?, ?, ?, ?)",
            (character.id, int(to_day), sender, subject, body),
        )
    return bool(cursor.rowcount)


def _touch_login_state(session, moment: AstralisMoment) -> tuple[int, bool]:
    character = getattr(session, "character", None)
    if character is None:
        return 0, False
    ensure_living_world_schema(session.database)
    row = _character_state(session.database, character.id)
    created_mail = False
    if row is None:
        previous_day = moment.day_number
        with session.database.connect() as db:
            db.execute(
                "INSERT INTO living_character_state (character_id, last_seen_day, last_room_hint_day) VALUES (?, ?, 0)",
                (character.id, moment.day_number),
            )
    else:
        previous_day = int(row["last_seen_day"])
        if previous_day < moment.day_number:
            created_mail = _create_return_letter(session, previous_day, moment.day_number)
        with session.database.connect() as db:
            db.execute(
                "UPDATE living_character_state SET last_seen_day = ? WHERE character_id = ?",
                (moment.day_number, character.id),
            )
    return previous_day, created_mail


def _unread_mail_count(session) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return 0
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM living_mail WHERE character_id = ? AND is_read = 0",
            (character.id,),
        ).fetchone()
    return int(row["n"])


async def _show_mail(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        rows = db.execute(
            "SELECT id, astralis_day, sender, subject, is_read FROM living_mail WHERE character_id = ? ORDER BY id DESC LIMIT 20",
            (character.id,),
        ).fetchall()
    await session.send("\r\n--- Post ---\r\n")
    if not rows:
        await session.send("No letters are waiting.\r\n")
        return
    for row in rows:
        marker = " " if int(row["is_read"]) else "*"
        await session.send(f"{marker} {row['id']}) {row['subject']} — {row['sender']} [Day {row['astralis_day']}]\r\n")
    await session.send("READ MAIL <number> opens a letter. * means unread.\r\n")


async def _read_mail(session, mail_id: int) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT id, astralis_day, sender, subject, body FROM living_mail WHERE id = ? AND character_id = ?",
            (int(mail_id), character.id),
        ).fetchone()
        if row is not None:
            db.execute("UPDATE living_mail SET is_read = 1 WHERE id = ?", (int(mail_id),))
    if row is None:
        await session.send("You do not have a letter with that number.\r\n")
        return
    await session.send(f"\r\n--- {row['subject']} ---\r\nFrom: {row['sender']}\r\n{row['body']}\r\n")


def _quarters_row(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT hub_room_key, rented_day FROM living_quarters WHERE character_id = ?",
            (character.id,),
        ).fetchone()


def _room_storage_total(session) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return 0
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total FROM living_room_storage WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    return int(row["total"])


def _display_count(session) -> int:
    character = getattr(session, "character", None)
    if character is None:
        return 0
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM living_room_display WHERE character_id = ?",
            (character.id,),
        ).fetchone()
    return int(row["n"])


def _display_rows(session):
    character = getattr(session, "character", None)
    if character is None:
        return []
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT slot_number, item_key FROM living_room_display WHERE character_id = ? ORDER BY slot_number",
            (character.id,),
        ).fetchall()


def _storage_rows(session):
    character = getattr(session, "character", None)
    if character is None:
        return []
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT item_key, quantity FROM living_room_storage WHERE character_id = ? AND quantity > 0 ORDER BY item_key",
            (character.id,),
        ).fetchall()


async def _show_room_status(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    row = _quarters_row(session)
    await session.send("\r\n--- Your Room ---\r\n")
    if row is None:
        await session.send(
            f"You have not rented a small room yet. At Waymeet Commonhouse or Veyra Public Hearth, RENT ROOM costs {ROOM_RENT_COST_SCRIP} Waymeet Trade Scrip.\r\n"
        )
        return
    hub = SOCIAL_HUBS.get(str(row["hub_room_key"]), str(row["hub_room_key"]))
    await session.send(
        f"Home hearth: {hub} | Storage: {_room_storage_total(session)}/{ROOM_STORAGE_CAPACITY} item-units | "
        f"Display shelf: {_display_count(session)}/{ROOM_DISPLAY_SLOTS} slots\r\n"
        "From your home hearth: ENTER ROOM. Inside: SLEEP, ROOM STORAGE, ROOM STORE, ROOM TAKE, SHELF, DISPLAY, TAKE DISPLAY, LEAVE ROOM.\r\n"
    )


async def _rent_room(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if _quarters_row(session) is not None:
        await session.send("You already keep a room. Use ROOM to see its home hearth.\r\n")
        return
    if character.current_room not in SOCIAL_HUBS:
        await session.send("Rooms are rented through the Waymeet Commonhouse or Veyra Public Hearth.\r\n")
        return
    if session.database.item_quantity(character.id, WAYMEET_SCRIP_KEY) < ROOM_RENT_COST_SCRIP:
        await session.send(f"A small long-term room deposit costs {ROOM_RENT_COST_SCRIP} Waymeet Trade Scrip.\r\n")
        return
    session.database.consume_item(character.id, WAYMEET_SCRIP_KEY, ROOM_RENT_COST_SCRIP)
    moment = ASTRALIS_CLOCK.now()
    ensure_living_world_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO living_quarters (character_id, hub_room_key, rented_day) VALUES (?, ?, ?)",
            (character.id, character.current_room, moment.day_number),
        )
    await session.send(
        "A key and a narrow room are assigned to you. It is not a palace: one bed, one storage chest, one five-place display shelf, and a door that is yours to close.\r\n"
    )


async def _enter_room(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    row = _quarters_row(session)
    if row is None:
        await session.send("You do not have a rented room. Use RENT ROOM at a public hearth.\r\n")
        return
    if _party_for_session(session) is not None:
        await session.send("Leave your adventuring party before entering a private room.\r\n")
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot disappear into your room during combat.\r\n")
        return
    hub = str(row["hub_room_key"])
    if character.current_room != hub:
        await session.send(f"Your room is reached from {SOCIAL_HUBS.get(hub, hub)}.\r\n")
        return
    await _cancel_trade_for(character.id, "Trade canceled as one participant leaves for private quarters.")
    await _cancel_invites_for(character.id, "left for private quarters")
    session.database.set_character_room(character.id, _private_room_key(character.id))
    refreshed = session.database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed
    await session.send("\r\n")
    await _show_private_room(session)


async def _leave_room(session) -> None:
    character = getattr(session, "character", None)
    if character is None or not _is_private_room(session):
        await session.send("You are not in your rented room.\r\n")
        return
    row = _quarters_row(session)
    hub = str(row["hub_room_key"]) if row is not None else VEYRA_PUBLIC_HEARTH_KEY
    session.database.set_character_room(character.id, hub)
    refreshed = session.database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed
    await session.send("You lock your room and return to the public hearth.\r\n\r\n")
    await session.show_current_room()


async def _show_private_room(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    await session.send(
        f"{character.name}'s Rented Room\r\n"
        "A narrow private room sits above the public noise: a real bed, a lockable storage chest, a washstand, and a five-place shelf meant for things worth looking at instead of selling. The room is intentionally small. Over time, what you choose to keep here becomes the decoration.\r\n"
    )
    rows = _display_rows(session)
    if rows:
        await session.send("On the display shelf:\r\n")
        for row in rows:
            await session.send(f"  [{row['slot_number']}] {_item_label(str(row['item_key']))}\r\n")
    else:
        await session.send("The five-place display shelf is empty.\r\n")
    await session.send(
        f"Storage chest: {_room_storage_total(session)}/{ROOM_STORAGE_CAPACITY} item-units.\r\n"
        "Commands: SLEEP, ROOM STORAGE, ROOM STORE [qty] <item>, ROOM TAKE [qty] <item>, SHELF, DISPLAY <item>, TAKE DISPLAY <slot>, LEAVE ROOM.\r\n"
    )


async def _sleep_room(session) -> None:
    if not _is_private_room(session):
        await session.send("You need your own bed for that kind of uninterrupted rest.\r\n")
        return
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        return
    combatant.current_hp = combatant.max_hp
    combatant.current_mana = combatant.max_mana
    combatant.current_movement = combatant.max_movement
    await session.send(
        "You sleep without an alarm, a quest timer, or a reward streak waiting at the other end. When you wake, you feel fully recovered.\r\n"
    )
    await session.send_client_state()


async def _show_storage(session) -> None:
    if not _is_private_room(session):
        await session.send("Your room storage can only be opened from inside your room.\r\n")
        return
    rows = _storage_rows(session)
    used = _room_storage_total(session)
    await session.send(f"\r\n--- Room Storage ({used}/{ROOM_STORAGE_CAPACITY}) ---\r\n")
    if not rows:
        await session.send("The chest is empty.\r\n")
    for row in rows:
        await session.send(f"{row['quantity']} x {_item_label(str(row['item_key']))}\r\n")


async def _room_store(session, text: str) -> None:
    if not _is_private_room(session):
        await session.send("Use your storage chest from inside your room.\r\n")
        return
    character = session.character
    quantity, item_text = _parse_quantity(text)
    item_key, error = _resolve_inventory_item(session, item_text)
    if error:
        await session.send(error + "\r\n")
        return
    assert item_key is not None
    item = crafting.ITEMS_BY_KEY.get(item_key)
    if item is not None and item.category == "quest_item":
        await session.send("Quest items stay with you rather than disappearing into private storage.\r\n")
        return
    available = session.database.item_quantity(character.id, item_key) - _equipped_reserve(session, item_key)
    if available < quantity:
        await session.send(f"You only have {max(0, available)} unequipped {_item_label(item_key)} available.\r\n")
        return
    used = _room_storage_total(session)
    if used + quantity > ROOM_STORAGE_CAPACITY:
        await session.send(f"That would exceed the {ROOM_STORAGE_CAPACITY}-unit storage chest.\r\n")
        return
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (character.id, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) - _equipped_reserve(session, item_key) < quantity:
            db.rollback()
            await session.send("Your inventory changed before the item could be stored.\r\n")
            return
        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute(
                "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                (remaining, character.id, item_key),
            )
        else:
            db.execute(
                "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                (character.id, item_key),
            )
        db.execute(
            """
            INSERT INTO living_room_storage (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (character.id, item_key, quantity),
        )
    await session.send(f"Stored {quantity} x {_item_label(item_key)} in your room chest.\r\n")


async def _room_take(session, text: str) -> None:
    if not _is_private_room(session):
        await session.send("Use your storage chest from inside your room.\r\n")
        return
    character = session.character
    quantity, item_text = _parse_quantity(text)
    wanted = _normalize(item_text)
    rows = _storage_rows(session)
    matches = [
        row for row in rows
        if wanted in {_normalize(str(row["item_key"])), _normalize(_item_label(str(row["item_key"])))}
        or wanted in _normalize(_item_label(str(row["item_key"])))
    ]
    if len(matches) != 1:
        await session.send("Name one item currently in ROOM STORAGE.\r\n")
        return
    item_key = str(matches[0]["item_key"])
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM living_room_storage WHERE character_id = ? AND item_key = ?",
            (character.id, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) < quantity:
            db.rollback()
            await session.send("The chest does not hold that many.\r\n")
            return
        remaining = int(row["quantity"]) - quantity
        if remaining:
            db.execute(
                "UPDATE living_room_storage SET quantity = ? WHERE character_id = ? AND item_key = ?",
                (remaining, character.id, item_key),
            )
        else:
            db.execute(
                "DELETE FROM living_room_storage WHERE character_id = ? AND item_key = ?",
                (character.id, item_key),
            )
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (character.id, item_key, quantity),
        )
    await session.send(f"Took {quantity} x {_item_label(item_key)} from your room chest.\r\n")


async def _show_shelf(session) -> None:
    if not _is_private_room(session):
        await session.send("Your display shelf is inside your rented room.\r\n")
        return
    rows = {int(row["slot_number"]): str(row["item_key"]) for row in _display_rows(session)}
    await session.send("\r\n--- Five-Place Display Shelf ---\r\n")
    for slot in range(1, ROOM_DISPLAY_SLOTS + 1):
        await session.send(f"[{slot}] {_item_label(rows[slot]) if slot in rows else '(empty)'}\r\n")
    await session.send("DISPLAY <item> uses the first empty slot. TAKE DISPLAY <slot> returns it to inventory.\r\n")


async def _display_item(session, text: str) -> None:
    if not _is_private_room(session):
        await session.send("Your display shelf is inside your rented room.\r\n")
        return
    character = session.character
    rows = {int(row["slot_number"]): str(row["item_key"]) for row in _display_rows(session)}
    free = next((slot for slot in range(1, ROOM_DISPLAY_SLOTS + 1) if slot not in rows), None)
    if free is None:
        await session.send("All five display places are occupied. TAKE DISPLAY <slot> first.\r\n")
        return
    item_key, error = _resolve_inventory_item(session, text)
    if error:
        await session.send(error + "\r\n")
        return
    assert item_key is not None
    item = crafting.ITEMS_BY_KEY.get(item_key)
    if item is not None and item.category == "quest_item":
        await session.send("Quest items belong in your hands, not on a display shelf.\r\n")
        return
    available = session.database.item_quantity(character.id, item_key) - _equipped_reserve(session, item_key)
    if available < 1:
        await session.send(f"Unequip {_item_label(item_key)} before displaying it.\r\n")
        return
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (character.id, item_key),
        ).fetchone()
        if row is None or int(row["quantity"]) - _equipped_reserve(session, item_key) < 1:
            db.rollback()
            await session.send("Your inventory changed before the display was set.\r\n")
            return
        remaining = int(row["quantity"]) - 1
        if remaining:
            db.execute(
                "UPDATE character_items SET quantity = ? WHERE character_id = ? AND item_key = ?",
                (remaining, character.id, item_key),
            )
        else:
            db.execute(
                "DELETE FROM character_items WHERE character_id = ? AND item_key = ?",
                (character.id, item_key),
            )
        db.execute(
            "INSERT INTO living_room_display (character_id, slot_number, item_key) VALUES (?, ?, ?)",
            (character.id, free, item_key),
        )
    await session.send(f"You place {_item_label(item_key)} on display shelf slot {free}.\r\n")


async def _take_display(session, slot: int) -> None:
    if not _is_private_room(session):
        await session.send("Your display shelf is inside your rented room.\r\n")
        return
    character = session.character
    if slot < 1 or slot > ROOM_DISPLAY_SLOTS:
        await session.send("Display slots are numbered 1 through 5.\r\n")
        return
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT item_key FROM living_room_display WHERE character_id = ? AND slot_number = ?",
            (character.id, int(slot)),
        ).fetchone()
        if row is None:
            db.rollback()
            await session.send("That display place is already empty.\r\n")
            return
        item_key = str(row["item_key"])
        db.execute(
            "DELETE FROM living_room_display WHERE character_id = ? AND slot_number = ?",
            (character.id, int(slot)),
        )
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + 1
            """,
            (character.id, item_key),
        )
    await session.send(f"You take {_item_label(item_key)} down from the shelf.\r\n")


async def _record_progress_firsts(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    moment = ASTRALIS_CLOCK.now()
    for threshold in LEVEL_FIRSTS:
        if int(character.level) >= threshold:
            _chronicle_insert(
                session.database,
                event_key=f"first:level:{threshold}",
                day=moment.day_number,
                character_id=character.id,
                character_name=character.name,
                category="first",
                text=f"{character.name} became the first recorded adventurer to reach level {threshold}.",
            )


async def _record_boss_first(session, enemy_key: str) -> None:
    character = getattr(session, "character", None)
    name = BOSS_FIRSTS.get(enemy_key)
    if character is None or name is None:
        return
    moment = ASTRALIS_CLOCK.now()
    inserted = _chronicle_insert(
        session.database,
        event_key=f"first:boss:{enemy_key}",
        day=moment.day_number,
        character_id=character.id,
        character_name=character.name,
        category="first",
        text=f"{character.name} was present for the first recorded defeat of {name}.",
    )
    if inserted:
        await session.send(f"\r\nCHRONICLE: Your name enters the public record beside the first defeat of {name}.\r\n")


async def _record_daily_threat_completion(session, enemy, metadata) -> None:
    character = getattr(session, "character", None)
    if character is None or metadata is None:
        return
    enemy_id, day, pulse_key = metadata
    if id(enemy) != enemy_id:
        return
    pulse = next((value for value in PULSE_TEMPLATES if value.key == pulse_key), None)
    if pulse is None or pulse.kind != "threat":
        return
    if not _mark_event_done(session, day, pulse):
        return
    session.database.add_item(character.id, WAYMEET_SCRIP_KEY, 1)
    _chronicle_insert(
        session.database,
        event_key=f"pulse:{day}:{pulse.key}:{character.id}",
        day=day,
        character_id=character.id,
        character_name=character.name,
        category="daily",
        text=f"{character.name} helped quiet {pulse.headline.rstrip('.').lower()}",
    )
    await session.send(
        "A local warden leaves you 1 Waymeet Trade Scrip for dealing with today's disturbance. There is no repeat payout today.\r\n"
    )


async def _show_board(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    await session.send(
        "\r\n--- Public Hearth Board ---\r\n"
        f"Today: {pulse.headline}\r\n"
        f"Rumor points toward: {pulse.room_name}.\r\n"
    )
    rows = latest_chronicle(session.database, 5)
    if rows:
        await session.send("Pinned underneath:\r\n")
        for row in rows:
            await session.send(f"- {row['entry_text']}\r\n")
    else:
        await session.send("The history section is still blank enough to invite ambition.\r\n")


async def _push_living_gmcp(session) -> None:
    telnet = getattr(session, "telnet", None)
    character = getattr(session, "character", None)
    if telnet is None or character is None or not getattr(telnet, "gmcp_enabled", False):
        return
    moment = ASTRALIS_CLOCK.now()
    pulse = _sync_resource_shift(moment)
    await telnet.send_gmcp(
        "Dreams.WorldPulse",
        {
            "day": moment.day_number,
            "time": moment.calendar_display,
            "headline": pulse.headline,
            "summary": pulse.summary,
            "location": pulse.room_name,
            "kind": pulse.kind,
            "rare": rare_world_moment(moment) or "",
        },
    )
    await telnet.send_gmcp("Dreams.Post", {"unread": _unread_mail_count(session)})
    row = _quarters_row(session)
    await telnet.send_gmcp(
        "Dreams.Quarters",
        {
            "rented": row is not None,
            "inside": _is_private_room(session),
            "storage_used": _room_storage_total(session) if row is not None else 0,
            "storage_capacity": ROOM_STORAGE_CAPACITY,
            "display_used": _display_count(session) if row is not None else 0,
            "display_capacity": ROOM_DISPLAY_SLOTS,
        },
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


def install_living_world_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_living_world_runtime_installed", False):
        return
    install_living_world_content()

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            character = getattr(self, "character", None)
            if character is None:
                return
            moment = ASTRALIS_CLOCK.now()
            _sync_resource_shift(moment)
            _record_rare_moment(self.database, moment)
            _, new_mail = _touch_login_state(self, moment)
            await _record_progress_firsts(self)
            unread = _unread_mail_count(self)
            if new_mail or unread:
                await self.send(
                    f"\r\n[Post] {unread} unread letter{'s' if unread != 1 else ''} wait for you. Type MAIL when you want them.\r\n"
                )
            await self.send(f"[Astralis today] {pulse_for_day(moment.day_number).headline} Type DISPATCH for the day's news.\r\n")
            moon = _rare_moon_text(self, moment)
            if moon:
                await self.send("\r\n" + moon + "\r\n")
            await _push_living_gmcp(self)

        player_session_class.enter_character = enter_character

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            if _is_private_room(self):
                await _show_private_room(self)
                await _push_living_gmcp(self)
                return
            await previous_show_current_room(self)
            moon = _rare_moon_text(self, ASTRALIS_CLOCK.now())
            if moon:
                await self.send("\r\n" + moon + "\r\n")
            await _send_room_pulse_if_here(self)
            await _push_living_gmcp(self)

        player_session_class.show_current_room = show_current_room

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if previous_finish_enemy is not None:
        async def _finish_enemy_defeat(self, enemy) -> None:
            metadata = getattr(self, "_living_event_enemy", None)
            enemy_key = enemy.definition.key
            await previous_finish_enemy(self, enemy)
            await _record_boss_first(self, enemy_key)
            await _record_daily_threat_completion(self, enemy, metadata)
            if metadata is not None and metadata[0] == id(enemy):
                self._living_event_enemy = None
            await _record_progress_firsts(self)
            await _push_living_gmcp(self)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_close = getattr(player_session_class, "close", None)
    if previous_close is not None:
        async def close(self) -> None:
            character = getattr(self, "character", None)
            if character is not None and _is_private_room(self):
                row = _quarters_row(self)
                if row is not None:
                    self.database.set_character_room(character.id, str(row["hub_room_key"]))
                    refreshed = self.database.get_character_by_name(character.name)
                    if refreshed is not None:
                        self.character = refreshed
            await previous_close(self)

        player_session_class.close = close

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_playing_prompt(self)
            return

        moment = ASTRALIS_CLOCK.now()
        _sync_resource_shift(moment)
        _record_rare_moment(self.database, moment)

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"today", "dispatch", "world today", "daily dispatch"}:
            await _show_dispatch(self)
            await _push_living_gmcp(self)
            return
        if normalized in {"gossip", "rumor", "rumors"}:
            await _show_gossip(self)
            return
        if normalized in {"chronicle", "history", "world chronicle"}:
            await _show_chronicle(self)
            return
        if normalized in {"tavern board", "hearth board", "board today"}:
            await _show_board(self)
            return

        if normalized in {"browse wanderer", "browse peddler", "talk wanderer", "talk peddler"}:
            if await _browse_wanderer(self):
                return
        if normalized.startswith("buy wanderer "):
            if await _buy_wanderer(self, stripped.split(maxsplit=2)[2]):
                await _push_living_gmcp(self)
                return
        if normalized in {"hunt disturbance", "track disturbance", "investigate disturbance"}:
            if await _hunt_disturbance(self):
                return

        if normalized in {"mail", "post", "letters"}:
            await _show_mail(self)
            await _push_living_gmcp(self)
            return
        match = re.fullmatch(r"(?:read mail|read letter)\s+(\d+)", normalized)
        if match:
            await _read_mail(self, int(match.group(1)))
            await _push_living_gmcp(self)
            return

        if normalized in {"room", "my room", "quarters", "room status"}:
            await _show_room_status(self)
            return
        if normalized in {"rent room", "room rent"}:
            await _rent_room(self)
            await _push_living_gmcp(self)
            return
        if normalized in {"enter room", "room enter", "go room"}:
            await _enter_room(self)
            await _push_living_gmcp(self)
            return
        if normalized in {"leave room", "room leave", "out"} and _is_private_room(self):
            await _leave_room(self)
            await _push_living_gmcp(self)
            return
        if normalized in {"sleep", "sleep bed", "use bed"} and _is_private_room(self):
            await _sleep_room(self)
            return
        if normalized in {"room storage", "storage", "chest"} and _is_private_room(self):
            await _show_storage(self)
            return
        if normalized.startswith("room store "):
            await _room_store(self, stripped[len("room store "):])
            await _push_living_gmcp(self)
            return
        if normalized.startswith("room take "):
            await _room_take(self, stripped[len("room take "):])
            await _push_living_gmcp(self)
            return
        if normalized in {"shelf", "display shelf"} and _is_private_room(self):
            await _show_shelf(self)
            return
        if normalized.startswith("display ") and not normalized.startswith("display shelf"):
            await _display_item(self, stripped.split(maxsplit=1)[1])
            await _push_living_gmcp(self)
            return
        match = re.fullmatch(r"take display\s+(\d+)", normalized)
        if match:
            await _take_display(self, int(match.group(1)))
            await _push_living_gmcp(self)
            return

        await _delegate_command(self, previous_playing_prompt, command)
        refreshed = self.database.get_character_by_name(character.name)
        if refreshed is not None:
            self.character = refreshed
        await _record_progress_firsts(self)
        await _push_living_gmcp(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._living_world_runtime_installed = True
