from __future__ import annotations

from dataclasses import dataclass

import mud.living_world as living
import mud.living_world_depth as depth
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment
from mud.greywake_march import GREYWAKE_SIGNAL_HILL_KEY, GREYWAKE_THREE_BANNER_KEY
from mud.sablewater_reach import SABLEWATER_EEL_DOCK_KEY
from mud.veyra_city import VEYRA_BRASSMARKET_KEY, VEYRA_GRAND_CROSSING_KEY, VEYRA_PUBLIC_HEARTH_KEY
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_LANTERN_MARKET_KEY


LIVING_WORLD_CONTINUITY_VERSION = "1.0.0"


# This pass deliberately stays small. The previous living-world layer already
# supplies the machinery; these entries add density in places players naturally
# linger instead of creating another progression system or event menu.
EXTRA_DAILY_TEXTURES: tuple[depth.DailyTexture, ...] = (
    depth.DailyTexture(
        "commonhouse_mug_shelf",
        "social",
        WAYMEET_COMMONHOUSE_KEY,
        "Waymeet Commonhouse Yard",
        "The Commonhouse has started a shelf for mugs travelers forgot and then came back looking for.",
        "'That blue mug has been reclaimed four times by three different people.'",
        "A narrow shelf by the door holds a mismatched row of forgotten mugs, each with a chalk guess at its owner's name.",
    ),
    depth.DailyTexture(
        "commonhouse_boot_exchange",
        "social",
        WAYMEET_COMMONHOUSE_KEY,
        "Waymeet Commonhouse Yard",
        "Two travelers are trying to prove they accidentally left Waymeet wearing each other's nearly identical boots.",
        "'Same size, same mud, different complaints. The boots are refusing testimony.'",
        "Two pairs of road boots sit in the middle of an increasingly serious discussion about ownership and left-foot wear.",
    ),
    depth.DailyTexture(
        "lantern_tarp_repair",
        "craft",
        WAYMEET_LANTERN_MARKET_KEY,
        "Waymeet Lantern Market",
        "Lantern Market merchants are stitching yesterday's rain tears out of one enormous shared awning.",
        "'Nobody owns the whole tarp, which means everybody owns the hole over their own stall.'",
        "A patched market awning lies across three tables while merchants sew from opposite sides and argue about whose stitch line is straighter.",
    ),
    depth.DailyTexture(
        "veyra_hearth_game",
        "social",
        VEYRA_PUBLIC_HEARTH_KEY,
        "Veyra Public Hearth",
        "A carved travel game at the Public Hearth has acquired a standing crowd and no agreed rules.",
        "'Every homeland knows this game. Apparently every homeland learned a different game.'",
        "Carved stones click across a little board while spectators object to moves for mutually incompatible reasons.",
    ),
    depth.DailyTexture(
        "brassmarket_lunch_bell",
        "trade",
        VEYRA_BRASSMARKET_KEY,
        "Veyra Brassmarket",
        "Someone has started ringing a handbell when the cheap lunch pots open, and half of Brassmarket now reacts on instinct.",
        "'You can tell who works this district by how fast they move when that bell rings.'",
        "A small brass bell rings from somewhere between the stalls. Several merchants immediately abandon negotiations in favor of lunch.",
    ),
    depth.DailyTexture(
        "three_banner_laundry_truce",
        "social",
        GREYWAKE_THREE_BANNER_KEY,
        "Three-Banner Camp",
        "Three-Banner Camp has declared the central laundry line politically neutral until the blankets dry.",
        "'Roadwarden socks next to Ledger shirts. Peace was possible all along.'",
        "A long laundry line crosses three unofficial camp boundaries without respecting a single one of them.",
    ),
)


IVEN = depth.ScheduledVisitor(
    key="iven_candlemark",
    name="Iven Candlemark",
    aliases=("iven", "candlemark", "lamplighter", "lamp inspector"),
    role="Undead lamplighter and road-lamp inspector",
    presence=(
        "Iven Candlemark is here with a blackened lamp-hook, a notebook of tiny failures, "
        "and the patient posture of someone who has outlasted several maintenance budgets."
    ),
    talk_lines=(
        "'A lamp is successful when nobody tells a story about it. I am trying to make the roads very boring.'",
        "'People notice darkness immediately. Reliable light becomes invisible. That is infrastructure for you.'",
        "'I was a clerk before I died. Lamplighting has fewer forms and more ladders.'",
        "'You can learn a road by its lamps. Bent cages mean wind. Sooted glass means cheap oil. Missing lamps mean people.'",
    ),
)


_ROOM_LABELS = {
    WAYMEET_COMMONHOUSE_KEY: "the Waymeet Commonhouse",
    WAYMEET_LANTERN_MARKET_KEY: "Lantern Market",
    GREYWAKE_SIGNAL_HILL_KEY: "Greywake Signal Hill",
    GREYWAKE_THREE_BANNER_KEY: "Three-Banner Camp",
    VEYRA_GRAND_CROSSING_KEY: "Grand Crossing",
    VEYRA_BRASSMARKET_KEY: "Brassmarket",
    VEYRA_PUBLIC_HEARTH_KEY: "the Veyra Public Hearth",
    SABLEWATER_EEL_DOCK_KEY: "Eelmarket Dock",
}


_RECOGNITION_LINES = {
    depth.PELL.key: "Pell looks up from tuning and gives you two fingers of greeting. 'You again. Good. Roads should return a few people.'",
    depth.SELLA.key: "Sella gives you the small courier's nod reserved for people she has seen survive another stretch of road.",
    depth.CHIV.key: "Chiv points a screwdriver at you in recognition. 'Still assembled. Excellent.'",
    depth.HESTA.key: "Hesta checks your face before her ledger. 'Seen you before. That saves us both an introduction.'",
    IVEN.key: "Iven Candlemark gives you a dry nod. 'I remember your face. Easier than remembering every lamp.'",
}

_NOTE_ACK_LINES = {
    depth.PELL.key: "'I saw your note on the board. Better opening line than half the songs I hear.'",
    depth.SELLA.key: "'Your note is still pinned. People are reading it.'",
    depth.CHIV.key: "'Saw your note. Useful board, that. Better than shouting.'",
    depth.HESTA.key: "'I saw what you pinned. Didn't buy or sell anything about it, which is probably healthy.'",
    IVEN.key: "'Your note is still pinned straight. Somebody cared enough not to tear it down.'",
}


_ORIGINAL_SCHEDULE = depth._scheduled_location


def _iven_location(moment: AstralisMoment) -> str | None:
    day = int(moment.day_number)
    hour = int(moment.hour)
    weekday = (day - 1) % 7

    # Iven is intentionally not omnipresent. Two western maintenance days and
    # two eastern ones per Astralis week make him recognizable without making
    # him another permanent service NPC.
    if weekday in {1, 4}:
        if 7 <= hour < 13:
            return GREYWAKE_SIGNAL_HILL_KEY
        if 13 <= hour < 18:
            return WAYMEET_LANTERN_MARKET_KEY
        if 18 <= hour < 23:
            return WAYMEET_COMMONHOUSE_KEY
        return None
    if weekday in {2, 5}:
        if 8 <= hour < 14:
            return VEYRA_GRAND_CROSSING_KEY
        if 14 <= hour < 19:
            return VEYRA_BRASSMARKET_KEY
        if 19 <= hour < 24:
            return VEYRA_PUBLIC_HEARTH_KEY
        return None
    return None


def _scheduled_location_with_continuity(visitor: depth.ScheduledVisitor, moment: AstralisMoment) -> str | None:
    if visitor.key == IVEN.key:
        return _iven_location(moment)
    return _ORIGINAL_SCHEDULE(visitor, moment)


def _install_content_extensions() -> None:
    if not any(texture.key == EXTRA_DAILY_TEXTURES[0].key for texture in depth.DAILY_TEXTURES):
        existing = {texture.key for texture in depth.DAILY_TEXTURES}
        depth.DAILY_TEXTURES = depth.DAILY_TEXTURES + tuple(
            texture for texture in EXTRA_DAILY_TEXTURES if texture.key not in existing
        )
    if not any(visitor.key == IVEN.key for visitor in depth.VISITORS):
        depth.VISITORS = depth.VISITORS + (IVEN,)
    if depth._scheduled_location is not _scheduled_location_with_continuity:
        depth._scheduled_location = _scheduled_location_with_continuity
    if depth._talk_visitor is not _talk_visitor_with_memory:
        depth._talk_visitor = _talk_visitor_with_memory


def ensure_continuity_schema(database) -> None:
    depth.ensure_depth_schema(database)
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS living_visitor_memory (
                character_id INTEGER NOT NULL,
                visitor_key TEXT NOT NULL,
                first_met_day INTEGER NOT NULL,
                last_met_day INTEGER NOT NULL,
                times_spoken INTEGER NOT NULL DEFAULT 0,
                last_room_key TEXT NOT NULL,
                PRIMARY KEY (character_id, visitor_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS living_visitor_recognition (
                character_id INTEGER NOT NULL,
                visitor_key TEXT NOT NULL,
                astralis_day INTEGER NOT NULL,
                recognized_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, visitor_key, astralis_day),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _memory_row(session, visitor_key: str):
    character = getattr(session, "character", None)
    if character is None:
        return None
    ensure_continuity_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """
            SELECT first_met_day, last_met_day, times_spoken, last_room_key
            FROM living_visitor_memory
            WHERE character_id = ? AND visitor_key = ?
            """,
            (character.id, visitor_key),
        ).fetchone()


def _record_conversation(session, visitor: depth.ScheduledVisitor, moment: AstralisMoment) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    ensure_continuity_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """
            INSERT INTO living_visitor_memory
            (character_id, visitor_key, first_met_day, last_met_day, times_spoken, last_room_key)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(character_id, visitor_key) DO UPDATE SET
                last_met_day = excluded.last_met_day,
                times_spoken = living_visitor_memory.times_spoken + 1,
                last_room_key = excluded.last_room_key
            """,
            (
                character.id,
                visitor.key,
                moment.day_number,
                moment.day_number,
                character.current_room or "",
            ),
        )


def _mark_recognition(session, visitor_key: str, day: int) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    ensure_continuity_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO living_visitor_recognition
            (character_id, visitor_key, astralis_day)
            VALUES (?, ?, ?)
            """,
            (character.id, visitor_key, int(day)),
        )
    return bool(cursor.rowcount)


def _has_active_note_here(session, day: int) -> bool:
    character = getattr(session, "character", None)
    if character is None or character.current_room not in living.SOCIAL_HUBS:
        return False
    depth.ensure_depth_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            """
            SELECT 1
            FROM living_board_notes
            WHERE character_id = ? AND hub_room_key = ? AND expires_day >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (character.id, character.current_room, int(day)),
        ).fetchone()
    return row is not None


def _returning_greeting(visitor: depth.ScheduledVisitor, memory, character_name: str) -> str:
    old_room = _ROOM_LABELS.get(str(memory["last_room_key"]), "the road")
    if visitor.key == IVEN.key:
        return f"Iven closes his notebook for a moment. 'I remember you, {character_name}. Last time was around {old_room}.'"
    if visitor.key == depth.PELL.key:
        return f"Pell smiles before you speak. 'There you are, {character_name}. I last saw you around {old_room}.'"
    if visitor.key == depth.SELLA.key:
        return f"Sella glances up. 'Back on my route, {character_name}. Last crossing was around {old_room}.'"
    if visitor.key == depth.CHIV.key:
        return f"Chiv squints, then grins. 'Knew I had seen you before, {character_name}. Around {old_room}, yes?'"
    if visitor.key == depth.HESTA.key:
        return f"Hesta nods once. 'Returning customer or returning conversation, {character_name}. Last time: {old_room}.'"
    return f"{visitor.name} recognizes {character_name} from an earlier meeting around {old_room}."


async def _show_recognition(session, moment: AstralisMoment) -> None:
    character = getattr(session, "character", None)
    if character is None or living._is_private_room(session):
        return
    for visitor in depth.visitors_in_room(moment, character.current_room or ""):
        memory = _memory_row(session, visitor.key)
        if memory is None or int(memory["last_met_day"]) >= int(moment.day_number):
            continue
        if not _mark_recognition(session, visitor.key, moment.day_number):
            continue
        line = _RECOGNITION_LINES.get(visitor.key)
        if line:
            await session.send(f"\r\n[Familiar face] {line}\r\n")


async def _talk_visitor_with_memory(session, target: str) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    moment = ASTRALIS_CLOCK.now()
    present = depth.visitors_in_room(moment, character.current_room or "")
    visitor = next((value for value in present if depth._visitor_matches(value, target)), None)
    if visitor is None:
        return False

    memory = _memory_row(session, visitor.key)
    if memory is not None and int(memory["last_met_day"]) < int(moment.day_number):
        await session.send("\r\n" + _returning_greeting(visitor, memory, character.name) + "\r\n")

    line = visitor.talk_lines[
        depth._stable_index(f"visitor:{visitor.key}:{moment.day_number}:{character.id}", len(visitor.talk_lines))
    ]
    await session.send(f"\r\n{visitor.name} says, {line}\r\n")

    if memory is not None and _has_active_note_here(session, moment.day_number):
        ack = _NOTE_ACK_LINES.get(visitor.key)
        if ack:
            await session.send(f"{visitor.name} adds, {ack}\r\n")

    _record_conversation(session, visitor, moment)

    if visitor.key == depth.HESTA.key:
        await session.send("Hesta is today's weekly factor. BROWSE HESTA shows her ordinary road stock.\r\n")
    return True


def install_living_world_continuity_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_living_world_continuity_runtime_installed", False):
        return

    _install_content_extensions()

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            character = getattr(self, "character", None)
            if character is not None:
                ensure_continuity_schema(self.database)

        player_session_class.enter_character = enter_character

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            character = getattr(self, "character", None)
            if character is None or living._is_private_room(self):
                return
            await _show_recognition(self, ASTRALIS_CLOCK.now())

        player_session_class.show_current_room = show_current_room

    player_session_class._living_world_continuity_runtime_installed = True
