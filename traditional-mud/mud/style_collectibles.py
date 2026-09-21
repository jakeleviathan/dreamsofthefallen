from __future__ import annotations

import time
from dataclasses import dataclass

import mud.crafting as crafting
import mud.social_experience as social_experience
import mud.trade_experience as trade_experience
from mud.appearance import normalized_appearance, traits_for_race
from mud.appearance_storage import get_appearance
from mud.astralis_time import ASTRALIS_CLOCK
from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.crafting import ItemDefinition
from mud.database import Database
from mud.equipment_system import equipped_definitions, normalize_slot
from mud.gloamworks_dungeon import BURIED_REGENT_KEY
from mud.gravewatch_keep import CASTELLAN_KEY
from mud.party_system import _party_sessions_here
from mud.sablewater_reach import BRASS_AUDITOR_KEY
from mud.veyra_city import VEYRA_BRASSMARKET_KEY
from mud.veyra_underclock import GOVERNOR_KEY
from mud.waymeet_adventure_arc import LISTENER_BELOW
from mud.sols import format_sols
from mud.starter_race_loops import STARTER_RACE_LOOPS
from mud.waymeet_frontier import WAYMEET_LANTERN_MARKET_KEY


STYLE_VERSION = "2.0.1"
RARITY_ORDER = ("common", "uncommon", "rare", "epic", "legendary")
# Style is a visual layer independent of combat equipment, but silhouettes still
# belong to sensible body/equipment slots. A hood is Head, boots are Feet, a
# sword is Main Hand, and a shield is Off Hand. Style never changes real stats.
STYLE_SLOTS = (
    "head", "face", "neck", "shoulders", "chest", "hands",
    "waist", "legs", "feet", "back", "jewelry", "accessory",
    "main_hand", "off_hand",
)
STYLE_SLOT_LABELS = {
    **{slot: slot.replace("_", " ").title() for slot in STYLE_SLOTS},
    "main_hand": "Main Hand",
    "off_hand": "Off Hand",
}

PAVO_NAME = "Pavo Vellum"
PAVO_TITLE = "Master of Appearances"
PAVO_ATELIER_NAME = "Pavo's Impossible Atelier"
PAVO_SHORT_DESCRIPTION = (
    "an impeccably dressed, aggressively theatrical stylist surrounded by mirrors, "
    "measuring tape, garment forms, and entirely too much confidence"
)
STYLE_COPY_BASE_COST_SPARKS = 10
STYLE_COPY_TIER_COST_SPARKS = 5
COPIED_STYLE_PREFIX = "copy:"

# Pavo is recurring, not ubiquitous room furniture. Each homeland gets one
# reliable atelier at its starter settlement, while the two largest shared
# commercial hubs get one flagship counter each. Nearby markets, inns, civic
# rooms, and exchanges do not automatically spawn duplicate Pavos.
PAVO_ATELIER_ROOMS = frozenset(
    {loop.starting_room_key for loop in STARTER_RACE_LOOPS}
    | {VEYRA_BRASSMARKET_KEY, WAYMEET_LANTERN_MARKET_KEY}
)

PAVO_DIALOGUE = (
    "\"Armor is for surviving, darling. Style is for being remembered. We can do both.\"",
    "\"Yes, you saw me in another city. No, we are not wasting good daylight on logistics.\"",
    "\"There is only one atelier,\" Pavo says. \"It simply has an unreasonable number of front doors.\"",
    "\"I do not destroy the garment. I preserve the idea of it. Much more civilized.\"",
    "\"Bring me something with a silhouette worth saving and enough Sols to prove you mean it.\"",
)


@dataclass(frozen=True, slots=True)
class StyleMetadata:
    item_key: str
    rarity: str
    style_slot: str
    style_tags: tuple[str, ...]
    house: str
    collection: str
    acquisition_hint: str
    price_sparks: int = 0
    provenance_track: bool = False
    limited: bool = False


@dataclass(frozen=True, slots=True)
class FragranceDefinition:
    item_key: str
    house: str
    rarity: str
    notes: tuple[str, ...]
    bottle: str
    duration_seconds: int = 3600
    xp_bonus_percent: int = 10
    price_sparks: int = 30


# ---------------------------------------------------------------------------
# A first real fashion catalog. Combat equipment remains mechanically separate:
# these pieces exist to be seen, collected, traded, remembered, and combined.
# ---------------------------------------------------------------------------
STYLE_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition("style_veyra_cutaway_coat", "Veyra Cutaway Coat", "A sharply cut charcoal coat with a high split tail, narrow river-blue piping, and brass buttons small enough not to turn the wearer into a walking uniform.", "fashion", tier=1),
    ItemDefinition("style_brassmarket_silk_scarf", "Brassmarket Silk Scarf", "A long silk scarf dyed deep peacock blue. The ends are printed with tiny market awnings visible only when the cloth moves.", "fashion", tier=1),
    ItemDefinition("style_riverglass_signet", "Riverglass Signet", "A slim silver signet set with smoky riverglass. The stone looks gray indoors and green beside moving water.", "fashion", tier=1),
    ItemDefinition("style_blackglass_opera_gloves", "Blackglass Opera Gloves", "Elbow-length black gloves finished with a subtle glass-bead seam. They are impractical for forge work and completely unapologetic about it.", "fashion", tier=1),
    ItemDefinition("style_moonweave_half_cape", "Moonweave Half-Cape", "A pale asymmetric half-cape fastened at one shoulder. Moonweave thread gives the folds a cool sheen without making them luminous.", "fashion", tier=2),
    ItemDefinition("style_high_horizon_ear_cuff", "High Horizon Ear Cuff", "A narrow lavender-silver cuff designed to trace the outer edge of a long ear or sit cleanly on a Human, Dwarf, Troll, Goblin, Undead, or Sporekin equivalent.", "fashion", tier=2),
    ItemDefinition("style_reedcut_travel_boots", "Reed-Cut Travel Boots", "Tall dark boots with diagonal reed-pattern stitching and a polished low heel. They look expensive without pretending roads are clean.", "fashion", tier=1),
    ItemDefinition("style_copper_thread_sash", "Copper-Thread Sash", "A soft black sash woven through with hair-thin copper. In firelight it flashes once, then goes dark again.", "fashion", tier=1),
    ItemDefinition("style_white_heron_pin", "White Heron Lapel Pin", "A tiny white-enamel heron with one absurdly fine silver leg. Sablewater ferrymen insist the posture is anatomically wrong.", "fashion", tier=1),
    ItemDefinition("style_ashblue_court_trousers", "Ash-Blue Court Trousers", "High-waisted ash-blue trousers with a severe crease and side closures hidden under braided cord.", "fashion", tier=1),
    ItemDefinition("style_lantern_evening_mantle", "Lantern Evening Mantle", "A soft ivory shoulder mantle clasped with a dark lantern-shaped pin. It borrows Lantern Oath lines without claiming office.", "fashion", tier=2),
    ItemDefinition("style_crooked_lantern_mask", "Crooked Lantern Playhouse Mask", "A lacquered half-mask from a Crooked Lantern Company costume trunk, painted with one raised eyebrow and a smile that is clearly up to something.", "fashion", tier=2),

    # Heritage pieces are not stronger. Their value is scarcity and a readable
    # ownership history that follows them through direct player trades.
    ItemDefinition("style_regent_resonant_gorget", "Regent's Resonant Gorget", "A black collar of articulated plates cut from material recovered after the Buried Regent fell. Very faint room noise seems to collect along its edge.", "fashion", tier=3),
    ItemDefinition("style_auditor_floodsilk_gloves", "Auditor's Flood-Silk Gloves", "Ink-black flood-silk gloves closed with tiny obsolete brass tariff seals. They look bureaucratic enough to be threatening.", "fashion", tier=3),
    ItemDefinition("style_governor_ember_cuff", "Governor's Ember Cuff", "A broad dark cuff inset with one harmless furnace-red governor bearing. It stays warm against the wrist long after the machine itself is cold.", "fashion", tier=3),
    ItemDefinition("style_castellan_ashcloak", "Castellan's Ashcloak", "A long smoke-gray cloak recut from Gravewatch officer cloth. The hem retains one line of old silver command embroidery and deliberately leaves the rest unfinished.", "fashion", tier=4),
    ItemDefinition("style_listener_echo_veil", "Listener's Echo Veil", "A translucent charcoal face veil edged with soft gray membrane-thread. Spoken words behind it seem to arrive a fraction late, though the wearer hears no delay.", "fashion", tier=4),

    # Limited seasonal pieces are earned from a real boss victory during that
    # Astralis season. They never carry combat stats.
    ItemDefinition("style_spring_first_rain_rosette", "First Rain Rosette", "A folded blue-green rosette made to resemble the first wet leaves of Spring, finished with a single clear bead like a raindrop.", "fashion", tier=3),
    ItemDefinition("style_summer_suncaught_veil", "Sun-Caught Shoulder Veil", "An airy gold-ivory shoulder veil woven loosely enough to move in the smallest breeze. Tiny glass threads catch Summer light and immediately let it go.", "fashion", tier=3),
    ItemDefinition("style_autumn_copperleaf_cape", "Copperleaf Half-Cape", "A short russet half-cape cut into overlapping leaf-shaped panels, each backed with dark copper thread.", "fashion", tier=3),
    ItemDefinition("style_winter_frostglass_collar", "Frostglass Collar", "A high translucent collar of layered pale glasscloth. The edge looks rimed with frost but remains soft and room-temperature.", "fashion", tier=3),
)


STYLE_META: tuple[StyleMetadata, ...] = (
    StyleMetadata("style_veyra_cutaway_coat", "uncommon", "chest", ("tailored", "urban", "formal", "dark"), "Atelier Nine Bridges", "Veyra Street Formal", "Veyra Brassmarket boutique", 3),
    StyleMetadata("style_brassmarket_silk_scarf", "common", "neck", ("silk", "color", "market"), "Pikka & Thread", "Veyra Street Formal", "Veyra Brassmarket or Waymeet trunk", 1),
    StyleMetadata("style_riverglass_signet", "uncommon", "jewelry", ("silver", "river", "minimal"), "Orin Riverworks", "Riverglass", "Veyra Brassmarket boutique", 3),
    StyleMetadata("style_blackglass_opera_gloves", "uncommon", "hands", ("black", "formal", "glass"), "House Veyr", "Blackglass Evening", "Veyra Brassmarket boutique", 3),
    StyleMetadata("style_moonweave_half_cape", "rare", "back", ("moonweave", "pale", "asymmetric"), "Atelier Vael", "High Horizon After Dark", "Veyra Brassmarket boutique", 5),
    StyleMetadata("style_high_horizon_ear_cuff", "uncommon", "jewelry", ("silver", "moon-elf", "minimal"), "Atelier Vael", "High Horizon After Dark", "Veyra Brassmarket boutique", 3),
    StyleMetadata("style_reedcut_travel_boots", "common", "feet", ("travel", "dark", "reed"), "Sable & Reed", "Road Beautiful", "Waymeet trunk", 2),
    StyleMetadata("style_copper_thread_sash", "common", "waist", ("copper", "soft", "dark"), "Chiv Copperbell", "Road Beautiful", "Waymeet trunk", 1),
    StyleMetadata("style_white_heron_pin", "uncommon", "accessory", ("white", "bird", "sablewater"), "Eelmarket Enamel", "Riverglass", "Veyra Brassmarket boutique", 2),
    StyleMetadata("style_ashblue_court_trousers", "common", "legs", ("tailored", "blue", "formal"), "Atelier Nine Bridges", "Veyra Street Formal", "Veyra Brassmarket boutique", 2),
    StyleMetadata("style_lantern_evening_mantle", "rare", "shoulders", ("ivory", "lantern", "formal"), "Reed & Vow", "Lantern Evening", "Veyra Brassmarket boutique", 5),
    StyleMetadata("style_crooked_lantern_mask", "uncommon", "face", ("theatre", "lacquer", "mischief"), "Crooked Lantern Company", "Playhouse Trunk", "Waymeet trunk", 2),

    StyleMetadata("style_regent_resonant_gorget", "rare", "neck", ("black", "gloamworks", "resonant"), "Unattributed", "Dungeon Heritage", "One-time Buried Regent style trophy", provenance_track=True),
    StyleMetadata("style_auditor_floodsilk_gloves", "rare", "hands", ("black", "brass", "tollhouse"), "Reclaimed Civic Work", "Dungeon Heritage", "One-time Brass Auditor style trophy", provenance_track=True),
    StyleMetadata("style_governor_ember_cuff", "rare", "jewelry", ("industrial", "ember", "brass"), "Underclock Reclamation", "Dungeon Heritage", "One-time Cinder Governor style trophy", provenance_track=True),
    StyleMetadata("style_castellan_ashcloak", "epic", "back", ("gravewatch", "ash", "officer"), "Veyra Recutters", "Dungeon Heritage", "One-time Last Castellan style trophy", provenance_track=True),
    StyleMetadata("style_listener_echo_veil", "epic", "face", ("echo", "charcoal", "strange"), "Unattributed", "First Echo Heritage", "One-time Listener Below style trophy", provenance_track=True),

    StyleMetadata("style_spring_first_rain_rosette", "epic", "accessory", ("spring", "limited", "rain"), "Astralis Seasonal", "Yearly Seasonal Edition", "First tracked boss victory during Spring", provenance_track=True, limited=True),
    StyleMetadata("style_summer_suncaught_veil", "epic", "shoulders", ("summer", "limited", "light"), "Astralis Seasonal", "Yearly Seasonal Edition", "First tracked boss victory during Summer", provenance_track=True, limited=True),
    StyleMetadata("style_autumn_copperleaf_cape", "epic", "back", ("autumn", "limited", "copper"), "Astralis Seasonal", "Yearly Seasonal Edition", "First tracked boss victory during Autumn", provenance_track=True, limited=True),
    StyleMetadata("style_winter_frostglass_collar", "epic", "neck", ("winter", "limited", "frost"), "Astralis Seasonal", "Yearly Seasonal Edition", "First tracked boss victory during Winter", provenance_track=True, limited=True),
)
STYLE_META_BY_KEY = {meta.item_key: meta for meta in STYLE_META}


FRAGRANCE_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition("fragrance_blackglass_no7", "Blackglass No. 7", "A squared smoke-black bottle with a clear vertical window no wider than a matchstick.", "fragrance", tier=2),
    ItemDefinition("fragrance_brass_after_rain", "Brass After Rain", "A flat brushed-brass flask with the name punched into the underside instead of printed on the face.", "fragrance", tier=1),
    ItemDefinition("fragrance_cinder_rose", "Cinder Rose", "A deep red bottle whose black glass stopper is cut like a small burned petal.", "fragrance", tier=2),
    ItemDefinition("fragrance_pale_horizon", "Pale Horizon", "A tall colorless bottle with a lavender-gray cap and almost no label at all.", "fragrance", tier=1),
    ItemDefinition("fragrance_silver_orchard", "Silver Orchard", "A rounded pale bottle wrapped once in fine silver wire like a branch around fruit.", "fragrance", tier=2),
    ItemDefinition("fragrance_nightglass", "Nightglass", "A violet-gray bottle so dark the liquid line can only be seen against a lamp.", "fragrance", tier=3),
    ItemDefinition("fragrance_green_cathedral", "Green Cathedral", "A heavy green bottle sealed with wax stamped by a tiny fern frond.", "fragrance", tier=1),
    ItemDefinition("fragrance_bitter_bloom", "Bitter Bloom", "A slim amber bottle with a medicinal-looking label that becomes less medicinal the closer one reads it.", "fragrance", tier=2),
    ItemDefinition("fragrance_lumen_spores", "Lumen Spores", "A round blue-green bottle with a faintly glowing stopper made from cured fungal glass.", "fragrance", tier=3),
)

FRAGRANCES: tuple[FragranceDefinition, ...] = (
    FragranceDefinition("fragrance_blackglass_no7", "House Veyr", "rare", ("smoked cedar", "black pepper", "wet stone"), "smoke-black squared bottle", 3600, 10, 5),
    FragranceDefinition("fragrance_brass_after_rain", "House Veyr", "uncommon", ("rain air", "warm brass", "iris"), "brushed-brass flask", 3600, 10, 3),
    FragranceDefinition("fragrance_cinder_rose", "House Veyr", "rare", ("dark rose", "warm iron", "soft smoke"), "deep red bottle with black petal stopper", 3600, 10, 5),
    FragranceDefinition("fragrance_pale_horizon", "Atelier Vael", "uncommon", ("cold air", "moonflax", "white tea"), "minimal colorless bottle", 3600, 10, 3),
    FragranceDefinition("fragrance_silver_orchard", "Atelier Vael", "rare", ("green pear", "silver leaf", "mineral water"), "pale bottle bound in silver wire", 3600, 10, 5),
    FragranceDefinition("fragrance_nightglass", "Atelier Vael", "rare", ("violet", "quiet incense", "high stone"), "violet-gray night bottle", 3600, 10, 5),
    FragranceDefinition("fragrance_green_cathedral", "Root & Reed", "uncommon", ("moss", "fern", "wet bark"), "green wax-sealed bottle", 3600, 10, 3),
    FragranceDefinition("fragrance_bitter_bloom", "Root & Reed", "rare", ("bitterroot", "lavender", "dark herbs"), "slim amber apothecary bottle", 3600, 10, 5),
    FragranceDefinition("fragrance_lumen_spores", "Root & Reed", "rare", ("soft earth", "amber resin", "luminous mushroom"), "blue-green fungal-glass bottle", 3600, 10, 5),
)
FRAGRANCE_BY_KEY = {item.item_key: item for item in FRAGRANCES}

SEASONAL_STYLE = {
    "spring": "style_spring_first_rain_rosette",
    "summer": "style_summer_suncaught_veil",
    "autumn": "style_autumn_copperleaf_cape",
    "winter": "style_winter_frostglass_collar",
}

BOSS_STYLE_DROPS = {
    BURIED_REGENT_KEY: ("style_regent_resonant_gorget", "the Buried Regent"),
    BRASS_AUDITOR_KEY: ("style_auditor_floodsilk_gloves", "the Brass Auditor"),
    GOVERNOR_KEY: ("style_governor_ember_cuff", "the Cinder Governor"),
    CASTELLAN_KEY: ("style_castellan_ashcloak", "the Last Castellan"),
    LISTENER_BELOW.key: ("style_listener_echo_veil", "the Listener Below"),
}

BOUTIQUE_ROOMS = {VEYRA_BRASSMARKET_KEY, WAYMEET_LANTERN_MARKET_KEY}
WAYMEET_STYLE_KEYS = {
    "style_brassmarket_silk_scarf", "style_reedcut_travel_boots", "style_copper_thread_sash",
    "style_crooked_lantern_mask", "fragrance_brass_after_rain", "fragrance_pale_horizon",
    "fragrance_green_cathedral",
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _item_name(item_key: str) -> str:
    item = crafting.ITEMS_BY_KEY.get(item_key)
    return item.name if item is not None else item_key.replace("_", " ").title()


def install_style_content() -> None:
    additions = tuple(item for item in (*STYLE_ITEMS, *FRAGRANCE_ITEMS) if item.key not in crafting.ITEMS_BY_KEY)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
        crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})


def ensure_style_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS character_style_slots (
                character_id INTEGER NOT NULL,
                slot_key TEXT NOT NULL,
                item_key TEXT NOT NULL,
                worn_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, slot_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_style_discoveries (
                character_id INTEGER NOT NULL,
                item_key TEXT NOT NULL,
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, item_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_style_copies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                source_item_key TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_description TEXT NOT NULL,
                source_equipment_slot TEXT NOT NULL,
                copied_by TEXT NOT NULL DEFAULT 'Pavo Vellum',
                copied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(character_id, source_item_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_character_style_copies_character
            ON character_style_copies(character_id);

            CREATE TABLE IF NOT EXISTS character_fragrance_effects (
                character_id INTEGER PRIMARY KEY,
                fragrance_key TEXT NOT NULL,
                applied_at_epoch INTEGER NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                bonus_fraction REAL NOT NULL DEFAULT 0.0,
                bonus_xp_earned INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS style_item_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial TEXT UNIQUE,
                item_key TEXT NOT NULL,
                current_owner_character_id INTEGER,
                origin_text TEXT NOT NULL,
                created_day INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_owner_character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS style_item_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER NOT NULL,
                from_character_id INTEGER,
                to_character_id INTEGER,
                action TEXT NOT NULL,
                astralis_day INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (instance_id) REFERENCES style_item_instances(id) ON DELETE CASCADE,
                FOREIGN KEY (from_character_id) REFERENCES characters(id) ON DELETE SET NULL,
                FOREIGN KEY (to_character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS character_style_boss_awards (
                character_id INTEGER NOT NULL,
                boss_key TEXT NOT NULL,
                item_key TEXT NOT NULL,
                awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, boss_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_style_season_awards (
                character_id INTEGER NOT NULL,
                astralis_year INTEGER NOT NULL,
                season_key TEXT NOT NULL,
                item_key TEXT NOT NULL,
                awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, astralis_year, season_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _mark_discovered(database, character_id: int, item_key: str) -> None:
    ensure_style_schema(database)
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO character_style_discoveries (character_id, item_key) VALUES (?, ?)",
            (character_id, item_key),
        )


def _sync_discoveries(session) -> None:
    if session.character is None:
        return
    ensure_style_schema(session.database)
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        if key in STYLE_META_BY_KEY or key in FRAGRANCE_BY_KEY:
            _mark_discovered(session.database, session.character.id, key)
            meta = STYLE_META_BY_KEY.get(key)
            if meta is not None and meta.provenance_track:
                _ensure_instances_for_inventory(session.database, session.character.id, key)


def style_atelier_available(world_service, room_key: str) -> bool:
    """Return whether this room is one of Pavo's deliberately spaced atelier locations."""
    del world_service
    return bool(room_key and room_key in PAVO_ATELIER_ROOMS)


def _is_pavo_target(target: str) -> bool:
    wanted = _normalize(target)
    return wanted in {
        "pavo",
        "pavo vellum",
        "vellum",
        "master vellum",
        "master of appearances",
        "stylist",
        "atelier master",
    }


def _copy_token(copy_id: int) -> str:
    return f"{COPIED_STYLE_PREFIX}{int(copy_id)}"


def _copy_id(style_key: str) -> int | None:
    if not style_key.startswith(COPIED_STYLE_PREFIX):
        return None
    value = style_key[len(COPIED_STYLE_PREFIX):]
    return int(value) if value.isdigit() else None


def _copied_style_rows(database, character_id: int):
    ensure_style_schema(database)
    with database.connect() as db:
        return db.execute(
            """
            SELECT id, source_item_key, source_name, source_description,
                   source_equipment_slot, copied_by, copied_at
            FROM character_style_copies
            WHERE character_id = ?
            ORDER BY source_name COLLATE NOCASE, id
            """,
            (character_id,),
        ).fetchall()


def _copied_style_row(database, character_id: int, style_key: str):
    copy_id = _copy_id(style_key)
    if copy_id is None:
        return None
    ensure_style_schema(database)
    with database.connect() as db:
        return db.execute(
            """
            SELECT id, source_item_key, source_name, source_description,
                   source_equipment_slot, copied_by, copied_at
            FROM character_style_copies
            WHERE id = ? AND character_id = ?
            """,
            (copy_id, character_id),
        ).fetchone()


def _style_slot_from_equipment_slot(slot: str) -> str:
    try:
        normalized = normalize_slot(slot)
    except ValueError:
        return "accessory"
    return normalized if normalized in STYLE_SLOTS else "accessory"


def _resolve_style_slot(value: str) -> str | None:
    wanted = _normalize(value)
    for slot in STYLE_SLOTS:
        if wanted in {_normalize(slot), _normalize(STYLE_SLOT_LABELS[slot])}:
            return slot
    return None


def _style_entry(database, character_id: int, style_key: str) -> dict | None:
    meta = STYLE_META_BY_KEY.get(style_key)
    if meta is not None:
        return {
            "key": style_key,
            "name": _item_name(style_key),
            "description": crafting.ITEMS_BY_KEY[style_key].description,
            "rarity": meta.rarity,
            "house": meta.house,
            "collection": meta.collection,
            "default_slot": meta.style_slot,
            "source_kind": "fashion",
            "source_item_key": style_key,
        }

    row = _copied_style_row(database, character_id, style_key)
    if row is None:
        return None
    return {
        "key": style_key,
        "name": str(row["source_name"]),
        "description": str(row["source_description"]),
        "rarity": "copied",
        "house": PAVO_ATELIER_NAME,
        "collection": "Copied Looks",
        "default_slot": _style_slot_from_equipment_slot(str(row["source_equipment_slot"])),
        "source_kind": "copied",
        "source_item_key": str(row["source_item_key"]),
    }


def _style_copy_cost(definition: ItemDefinition) -> int:
    return STYLE_COPY_BASE_COST_SPARKS + max(0, int(definition.tier)) * STYLE_COPY_TIER_COST_SPARKS


def _eligible_equipment_matches(session, target: str) -> list[ItemDefinition]:
    if session.character is None:
        return []
    wanted = _normalize(target)
    exact: list[ItemDefinition] = []
    partial: list[ItemDefinition] = []
    for row in session.database.list_items(session.character.id):
        if int(row["quantity"]) <= 0:
            continue
        key = str(row["item_key"])
        definition = crafting.ITEMS_BY_KEY.get(key)
        if definition is None or definition.equipment is None:
            continue
        names = {_normalize(definition.key), _normalize(definition.name)}
        if wanted in names:
            exact.append(definition)
        elif any(wanted in name for name in names):
            partial.append(definition)
    unique = {item.key: item for item in (exact or partial)}
    return list(unique.values())


def _split_target_and_style_slot(target: str) -> tuple[str, str | None, str | None]:
    raw = target.strip()
    lowered = raw.lower()
    marker = lowered.rfind(" as ")
    if marker < 0:
        return raw, None, None
    item_target = raw[:marker].strip()
    slot_text = raw[marker + 4:].strip()
    slot = _resolve_style_slot(slot_text)
    if slot is None:
        return item_target, None, (
            "Unknown style slot. Choose: "
            + ", ".join(STYLE_SLOT_LABELS[value] for value in STYLE_SLOTS)
            + "."
        )
    return item_target, slot, None


def _worn_style(database, character_id: int) -> dict[str, str]:
    ensure_style_schema(database)
    with database.connect() as db:
        rows = db.execute(
            "SELECT slot_key, item_key FROM character_style_slots WHERE character_id = ? ORDER BY slot_key",
            (character_id,),
        ).fetchall()
    result: dict[str, str] = {}
    for row in rows:
        slot = str(row["slot_key"])
        style_key = str(row["item_key"])
        valid = False
        if style_key in STYLE_META_BY_KEY:
            valid = database.item_quantity(character_id, style_key) > 0
        elif _copy_id(style_key) is not None:
            valid = _copied_style_row(database, character_id, style_key) is not None

        entry = _style_entry(database, character_id, style_key) if valid else None
        expected_slot = str(entry["default_slot"]) if entry is not None else None
        if slot not in STYLE_SLOTS or not valid or slot != expected_slot:
            # Sanitize any incompatible rows created by older style rules. This
            # never deletes the copied look or fashion item, only the invalid
            # visual assignment.
            with database.connect() as db:
                db.execute(
                    "DELETE FROM character_style_slots WHERE character_id = ? AND slot_key = ?",
                    (character_id, slot),
                )
            continue
        result[slot] = style_key
    return result

def _is_style_worn(database, character_id: int, item_key: str) -> bool:
    return item_key in _worn_style(database, character_id).values()


def _resolve_owned_style(session, target: str) -> tuple[str | None, str | None]:
    if session.character is None:
        return None, "No active character."
    wanted = _normalize(target)
    exact: list[str] = []
    partial: list[str] = []

    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        if key not in STYLE_META_BY_KEY or int(row["quantity"]) <= 0:
            continue
        names = {_normalize(key), _normalize(_item_name(key))}
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)

    for row in _copied_style_rows(session.database, session.character.id):
        key = _copy_token(int(row["id"]))
        names = {
            _normalize(str(row["source_item_key"])),
            _normalize(str(row["source_name"])),
            _normalize("copied " + str(row["source_name"])),
        }
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)

    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "You do not own a fashion piece or copied look by that name."
    if len(matches) > 1:
        names = [
            (_style_entry(session.database, session.character.id, key) or {"name": key})["name"]
            for key in matches
        ]
        return None, "Be more specific: " + ", ".join(names) + "."
    return matches[0], None

def _resolve_owned_fragrance(session, target: str) -> tuple[str | None, str | None]:
    if session.character is None:
        return None, "No active character."
    wanted = _normalize(target)
    exact: list[str] = []
    partial: list[str] = []
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        if key not in FRAGRANCE_BY_KEY or int(row["quantity"]) <= 0:
            continue
        fragrance = FRAGRANCE_BY_KEY[key]
        names = {_normalize(key), _normalize(_item_name(key)), _normalize(fragrance.house + " " + _item_name(key))}
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "You do not own a fragrance by that name."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(_item_name(key) for key in matches) + "."
    return matches[0], None


def _resolve_boutique_item(session, target: str, *, fragrance_only: bool | None = None) -> tuple[str | None, str | None]:
    if session.character is None or session.character.current_room not in BOUTIQUE_ROOMS:
        return None, "There is no style boutique here."
    wanted = _normalize(target)
    keys = []
    if fragrance_only is not True:
        keys.extend(meta.item_key for meta in STYLE_META if meta.price_sparks > 0)
    if fragrance_only is not False:
        keys.extend(item.item_key for item in FRAGRANCES if item.price_sparks > 0)
    if session.character.current_room == WAYMEET_LANTERN_MARKET_KEY:
        keys = [key for key in keys if key in WAYMEET_STYLE_KEYS]
    exact = [key for key in keys if wanted in {_normalize(key), _normalize(_item_name(key))}]
    partial = [key for key in keys if wanted in _normalize(_item_name(key))]
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "That piece is not in this boutique's current catalog."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(_item_name(key) for key in matches) + "."
    return matches[0], None


def _register_instance(database, character_id: int, item_key: str, origin_text: str) -> str:
    moment = ASTRALIS_CLOCK.now()
    ensure_style_schema(database)
    with database.connect() as db:
        cursor = db.execute(
            "INSERT INTO style_item_instances (item_key, current_owner_character_id, origin_text, created_day) VALUES (?, ?, ?, ?)",
            (item_key, character_id, origin_text, moment.day_number),
        )
        instance_id = int(cursor.lastrowid)
        serial = f"A{moment.year:02d}-{instance_id:06d}"
        db.execute("UPDATE style_item_instances SET serial = ? WHERE id = ?", (serial, instance_id))
        db.execute(
            "INSERT INTO style_item_history (instance_id, to_character_id, action, astralis_day, note) VALUES (?, ?, 'origin', ?, ?)",
            (instance_id, character_id, moment.day_number, origin_text),
        )
    return serial


def _owned_instances(database, character_id: int, item_key: str) -> list:
    ensure_style_schema(database)
    with database.connect() as db:
        return db.execute(
            "SELECT id, serial, origin_text, created_day FROM style_item_instances WHERE current_owner_character_id = ? AND item_key = ? ORDER BY id",
            (character_id, item_key),
        ).fetchall()


def _ensure_instances_for_inventory(database, character_id: int, item_key: str) -> None:
    meta = STYLE_META_BY_KEY.get(item_key)
    if meta is None or not meta.provenance_track:
        return
    inventory_count = database.item_quantity(character_id, item_key)
    known_count = len(_owned_instances(database, character_id, item_key))
    for _ in range(max(0, inventory_count - known_count)):
        _register_instance(database, character_id, item_key, "Entered the Veyra heritage registry from an existing collection.")


def _move_instances(database, from_character_id: int, to_character_id: int, item_key: str, quantity: int, note: str) -> None:
    meta = STYLE_META_BY_KEY.get(item_key)
    if meta is None or not meta.provenance_track or quantity <= 0:
        return
    _ensure_instances_for_inventory(database, from_character_id, item_key)
    rows = _owned_instances(database, from_character_id, item_key)[:quantity]
    day = ASTRALIS_CLOCK.now().day_number
    with database.connect() as db:
        for row in rows:
            instance_id = int(row["id"])
            db.execute("UPDATE style_item_instances SET current_owner_character_id = ? WHERE id = ?", (to_character_id, instance_id))
            db.execute(
                "INSERT INTO style_item_history (instance_id, from_character_id, to_character_id, action, astralis_day, note) VALUES (?, ?, ?, 'trade', ?, ?)",
                (instance_id, from_character_id, to_character_id, day, note),
            )


def _active_fragrance(database, character_id: int, now: int | None = None):
    ensure_style_schema(database)
    current = int(time.time()) if now is None else int(now)
    with database.connect() as db:
        row = db.execute(
            "SELECT fragrance_key, applied_at_epoch, expires_at_epoch, bonus_fraction, bonus_xp_earned FROM character_fragrance_effects WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    if row is None or int(row["expires_at_epoch"]) <= current:
        return None
    return row


def _install_xp_bonus_hook() -> None:
    if getattr(Database, "_style_xp_hook_installed", False):
        return
    original = Database.add_experience

    def add_experience(self, character_id: int, amount: int) -> int:
        if amount < 0:
            return original(self, character_id, amount)
        ensure_style_schema(self)
        effect = _active_fragrance(self, character_id)
        if effect is None or amount == 0:
            return original(self, character_id, amount)
        fragrance = FRAGRANCE_BY_KEY.get(str(effect["fragrance_key"]))
        if fragrance is None:
            return original(self, character_id, amount)
        raw_bonus = (amount * fragrance.xp_bonus_percent / 100.0) + float(effect["bonus_fraction"])
        bonus = int(raw_bonus)
        remainder = raw_bonus - bonus
        level = original(self, character_id, amount + bonus)
        with self.connect() as db:
            db.execute(
                "UPDATE character_fragrance_effects SET bonus_fraction = ?, bonus_xp_earned = bonus_xp_earned + ? WHERE character_id = ?",
                (remainder, bonus, character_id),
            )
        return level

    Database.add_experience = add_experience
    Database._style_xp_hook_installed = True
    Database._style_xp_original = original


async def _show_boutique(session) -> None:
    if session.character is None or session.character.current_room not in BOUTIQUE_ROOMS:
        await session.send("There is no fashion counter here. Veyra Brassmarket has the full boutique; Waymeet Lantern Market carries a smaller traveling trunk.\r\n")
        return
    await session.send("\r\n--- Astralis Style Counter ---\r\n")
    keys = [meta.item_key for meta in STYLE_META if meta.price_sparks > 0] + [item.item_key for item in FRAGRANCES if item.price_sparks > 0]
    if session.character.current_room == WAYMEET_LANTERN_MARKET_KEY:
        keys = [key for key in keys if key in WAYMEET_STYLE_KEYS]
    for key in keys:
        if key in STYLE_META_BY_KEY:
            meta = STYLE_META_BY_KEY[key]
            await session.send(f"[{meta.rarity.upper()}] {_item_name(key)} - {format_sols(meta.price_sparks)} - {STYLE_SLOT_LABELS[meta.style_slot]} - {', '.join(meta.style_tags)}\r\n")
        else:
            scent = FRAGRANCE_BY_KEY[key]
            await session.send(f"[{scent.rarity.upper()}] {scent.house} - {_item_name(key)} - {format_sols(scent.price_sparks)} - +{scent.xp_bonus_percent}% XP for {scent.duration_seconds // 60} min\r\n")
    await session.send("BUY STYLE <item> or BUY FRAGRANCE <name>. Fashion has no combat stats; fragrance is the only progression effect here.\r\n")


async def _buy_boutique(session, target: str, *, fragrance: bool) -> None:
    if session.character is None:
        return
    key, error = _resolve_boutique_item(session, target, fragrance_only=fragrance)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None
    price = FRAGRANCE_BY_KEY[key].price_sparks if key in FRAGRANCE_BY_KEY else STYLE_META_BY_KEY[key].price_sparks
    if session.database.get_sols(session.character.id) < price:
        await session.send(f"You need {format_sols(price)}.\r\n")
        return
    if not session.database.complete_merchant_purchase(
        session.character.id, item_key=key, quantity=1, total_price=price
    ):
        await session.send("The purchase could not be completed safely.\r\n")
        return
    _mark_discovered(session.database, session.character.id, key)
    await session.send(f"The counter wraps {_item_name(key)} carefully. You pay {format_sols(price)}.\r\n")


async def _show_pavo(session, world_service) -> None:
    if session.character is None:
        return
    if not style_atelier_available(world_service, session.character.current_room or ""):
        await session.send(
            "Pavo Vellum is not here. His ateliers are scattered across the major homelands, "
            "with flagship counters in Waymeet and Veyra.\r\n"
        )
        return
    await session.send(
        f"\r\n--- {PAVO_NAME}, {PAVO_TITLE} ---\r\n"
        f"{PAVO_SHORT_DESCRIPTION.capitalize()}.\r\n"
        "\"There is only one atelier,\" Pavo says, flicking open a measuring tape. "
        "\"It simply has an unreasonable number of front doors.\"\r\n"
        "He can preserve the visible design of any ordinary piece of equipment as a permanent copied look. "
        "The original item stays in your inventory, keeps all of its real stats, and can later be sold, traded, "
        "replaced, or lost without removing the copied look from your wardrobe.\r\n"
        "Commands: ATELIER | STYLE COPY <equipment> | STYLE WEAR <look>\r\n"
    )


async def _talk_pavo(session, world_service) -> None:
    if session.character is None:
        return
    if not style_atelier_available(world_service, session.character.current_room or ""):
        await session.send("Pavo Vellum is not here. Somehow, this is one of the few places where that is true.\r\n")
        return
    index = (session.character.id + ASTRALIS_CLOCK.now().day_number) % len(PAVO_DIALOGUE)
    await session.send(f"\r\n{PAVO_NAME} smiles as if your arrival completed a composition.\r\n")
    await session.send(PAVO_DIALOGUE[index] + "\r\n")
    await session.send(
        "Pavo taps a brass plaque: STYLE COPY <equipment>. "
        "ATELIER lists what you are carrying, its style slot, and what each copy costs.\r\n"
    )


async def _show_atelier(session, world_service) -> None:
    if session.character is None:
        return
    if not style_atelier_available(world_service, session.character.current_room or ""):
        await session.send(
            "There is no Impossible Atelier here. Pavo keeps one reliable counter in each homeland "
            "and flagship shops in Waymeet and Veyra.\r\n"
        )
        return

    await session.send(f"\r\n--- {PAVO_ATELIER_NAME} ---\r\n")
    await session.send(
        f"{PAVO_NAME} has somehow arranged the same mirrors, plum-colored drapes, and brass measuring stand here too.\r\n"
        "\"Do not confuse equipment with appearance,\" he says. \"One keeps you alive. The other gives witnesses useful details.\"\r\n"
    )

    copies = {
        str(row["source_item_key"]): row
        for row in _copied_style_rows(session.database, session.character.id)
    }
    equipment: list[ItemDefinition] = []
    for row in session.database.list_items(session.character.id):
        if int(row["quantity"]) <= 0:
            continue
        definition = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if definition is not None and definition.equipment is not None:
            equipment.append(definition)
    equipment.sort(key=lambda item: (item.tier, item.name.lower()))

    if not equipment:
        await session.send("You are not carrying any ordinary equipment for Pavo to copy.\r\n")
    else:
        await session.send("Carried equipment eligible for a permanent style copy:\r\n")
        for definition in equipment:
            copied = " [ALREADY COPIED]" if definition.key in copies else ""
            slot = _style_slot_from_equipment_slot(definition.equipment.slot)
            await session.send(
                f"  {definition.name} - {STYLE_SLOT_LABELS[slot]} - "
                f"{format_sols(_style_copy_cost(definition))}{copied}\r\n"
            )

    await session.send(
        "\r\nSTYLE COPY <equipment> preserves only the look. The source item is not consumed and its stats are never copied.\r\n"
        "Copied looks keep the source item's natural slot: hoods stay Head, boots stay Feet, weapons stay Main Hand, "
        "and shields stay Off Hand. STYLE WEAR <look> applies it to that slot automatically.\r\n"
    )


async def _wear_style_key(session, style_key: str, slot: str) -> None:
    if session.character is None:
        return
    entry = _style_entry(session.database, session.character.id, style_key)
    if entry is None:
        await session.send("That style appearance is no longer available.\r\n")
        return

    expected_slot = str(entry["default_slot"])
    if slot != expected_slot:
        await session.send(
            f"{entry['name']} is a {STYLE_SLOT_LABELS[expected_slot]} appearance and cannot be styled as "
            f"{STYLE_SLOT_LABELS[slot]}. Style copies keep the physical slot of the item they came from.\r\n"
        )
        return

    ensure_style_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM character_style_slots WHERE character_id = ? AND item_key = ?",
            (session.character.id, style_key),
        )
        db.execute(
            "INSERT INTO character_style_slots (character_id, slot_key, item_key) VALUES (?, ?, ?) "
            "ON CONFLICT(character_id, slot_key) DO UPDATE SET "
            "item_key = excluded.item_key, worn_at = CURRENT_TIMESTAMP",
            (session.character.id, expected_slot, style_key),
        )

    if style_key in STYLE_META_BY_KEY:
        _mark_discovered(session.database, session.character.id, style_key)
    source_note = "copied equipment look" if entry["source_kind"] == "copied" else "fashion piece"
    await session.send(
        f"You style {entry['name']} in your {STYLE_SLOT_LABELS[expected_slot]} slot as a {source_note}. "
        "It changes appearance, not combat stats; your practical equipment remains equipped underneath.\r\n"
    )
    await _send_style_gmcp(session)


async def _copy_style_from_equipment(session, target: str, world_service) -> None:
    if session.character is None:
        return
    if not style_atelier_available(world_service, session.character.current_room or ""):
        await session.send(
            "STYLE COPY is a Pavo Vellum service. Find one of his Impossible Atelier counters first.\r\n"
        )
        return

    item_target, requested_slot, slot_error = _split_target_and_style_slot(target)
    if slot_error:
        await session.send(slot_error + "\r\n")
        return
    matches = _eligible_equipment_matches(session, item_target)
    if not matches:
        await session.send(
            "Pavo can copy ordinary equipment you currently carry. That name does not match any carried equipment.\r\n"
        )
        return
    if len(matches) > 1:
        await session.send("Be more specific: " + ", ".join(item.name for item in matches) + ".\r\n")
        return

    definition = matches[0]
    assert definition.equipment is not None
    natural_slot = _style_slot_from_equipment_slot(definition.equipment.slot)
    if requested_slot is not None and requested_slot != natural_slot:
        await session.send(
            f"Pavo refuses the placement with offended precision. {definition.name} is a "
            f"{STYLE_SLOT_LABELS[natural_slot]} appearance, not {STYLE_SLOT_LABELS[requested_slot]}. "
            "The copied look must use the same kind of slot as the original equipment.\r\n"
        )
        return
    ensure_style_schema(session.database)

    with session.database.connect() as db:
        existing = db.execute(
            "SELECT id FROM character_style_copies WHERE character_id = ? AND source_item_key = ?",
            (session.character.id, definition.key),
        ).fetchone()
    if existing is not None:
        style_key = _copy_token(int(existing["id"]))
        await session.send(
            f"Pavo looks wounded. \"Darling. I already preserved {definition.name}. I do excellent work once.\"\r\n"
        )
        if requested_slot is not None:
            await _wear_style_key(session, style_key, requested_slot)
        else:
            await session.send(
                "Use STYLE WEAR " + definition.name.upper() + " whenever you want that look. "
                f"It always occupies {STYLE_SLOT_LABELS[natural_slot]}.\r\n"
            )
        return

    price = _style_copy_cost(definition)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        balance = db.execute(
            "SELECT sols FROM characters WHERE id = ?",
            (session.character.id,),
        ).fetchone()
        if balance is None or int(balance["sols"]) < price:
            await session.send(
                f"Pavo names the fee without blinking: {format_sols(price)}. You do not have enough Sols.\r\n"
            )
            return
        db.execute(
            "UPDATE characters SET sols = sols - ? WHERE id = ?",
            (price, session.character.id),
        )
        cursor = db.execute(
            """
            INSERT INTO character_style_copies (
                character_id, source_item_key, source_name, source_description,
                source_equipment_slot, copied_by
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session.character.id,
                definition.key,
                definition.name,
                definition.description,
                normalize_slot(definition.equipment.slot),
                PAVO_NAME,
            ),
        )
        copy_id = int(cursor.lastrowid)

    style_key = _copy_token(copy_id)
    await session.send(
        f"Pavo circles {definition.name}, makes three impossible measurements, and sketches exactly one line. "
        f"\"There. The object may someday be obsolete. The silhouette is now immortal.\"\r\n"
        f"Style copy added permanently: {definition.name}. Fee: {format_sols(price)}. "
        "The original item was not consumed and no stats were copied.\r\n"
    )
    if requested_slot is not None:
        await _wear_style_key(session, style_key, requested_slot)
    else:
        await session.send(
            f"Style slot: {STYLE_SLOT_LABELS[natural_slot]}. "
            f"Use STYLE WEAR {definition.name.upper()} whenever you want that look.\r\n"
        )
    await _send_style_gmcp(session)


async def _show_wardrobe(session) -> None:
    if session.character is None:
        return
    worn = _worn_style(session.database, session.character.id)
    await session.send("\r\n--- Styled Outfit ---\r\n")
    if not worn:
        await session.send(
            "No visual overrides are currently styled. Your practical equipment remains fully active underneath.\r\n"
        )
    else:
        for slot in STYLE_SLOTS:
            key = worn.get(slot)
            if not key:
                continue
            entry = _style_entry(session.database, session.character.id, key)
            if entry is None:
                continue
            tag = entry["rarity"].upper() if entry["source_kind"] == "fashion" else "COPIED LOOK"
            await session.send(
                f"{STYLE_SLOT_LABELS[slot]:<10}: {entry['name']} [{tag}] - {entry['house']}\r\n"
            )

    await session.send("\r\n--- Fashion Pieces You Carry ---\r\n")
    found = False
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        meta = STYLE_META_BY_KEY.get(key)
        if meta is None:
            continue
        found = True
        marker = " [WORN]" if key in worn.values() else ""
        limited = " LIMITED" if meta.limited else ""
        await session.send(
            f"{int(row['quantity'])}x {_item_name(key)} [{meta.rarity.upper()}{limited}] - "
            f"default {STYLE_SLOT_LABELS[meta.style_slot]}{marker}\r\n"
        )
    if not found:
        await session.send("No dedicated fashion pieces currently carried.\r\n")

    await session.send("\r\n--- Copied Looks ---\r\n")
    copies = _copied_style_rows(session.database, session.character.id)
    if not copies:
        await session.send(
            f"None yet. Find {PAVO_NAME} and use STYLE COPY <equipment> to preserve ordinary gear as fashion.\r\n"
        )
    else:
        for row in copies:
            key = _copy_token(int(row["id"]))
            marker = " [WORN]" if key in worn.values() else ""
            default_slot = _style_slot_from_equipment_slot(str(row["source_equipment_slot"]))
            await session.send(
                f"{row['source_name']} [COPIED LOOK] - default {STYLE_SLOT_LABELS[default_slot]}{marker}\r\n"
            )

    await session.send(
        "STYLE WEAR <look> | STYLE REMOVE <slot or look> | ATELIER | "
        "LOOK <player> | COLLECTION | PROVENANCE <item>\r\n"
    )


async def _wear_style(session, target: str) -> None:
    if session.character is None:
        return
    item_target, requested_slot, slot_error = _split_target_and_style_slot(target)
    if slot_error:
        await session.send(slot_error + "\r\n")
        return
    key, error = _resolve_owned_style(session, item_target)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None
    entry = _style_entry(session.database, session.character.id, key)
    if entry is None:
        await session.send("That style appearance is no longer available.\r\n")
        return
    natural_slot = str(entry["default_slot"])
    if requested_slot is not None and requested_slot != natural_slot:
        await session.send(
            f"{entry['name']} belongs in the {STYLE_SLOT_LABELS[natural_slot]} style slot, "
            f"not {STYLE_SLOT_LABELS[requested_slot]}.\r\n"
        )
        return
    await _wear_style_key(session, key, natural_slot)


async def _remove_style(session, target: str) -> None:
    if session.character is None:
        return
    wanted = _normalize(target)
    worn = _worn_style(session.database, session.character.id)
    slot = next(
        (
            slot
            for slot in STYLE_SLOTS
            if wanted in {_normalize(slot), _normalize(STYLE_SLOT_LABELS[slot])}
        ),
        None,
    )
    if slot is None:
        for candidate_slot, key in worn.items():
            entry = _style_entry(session.database, session.character.id, key)
            if entry is None:
                continue
            if wanted in {
                _normalize(key),
                _normalize(str(entry["name"])),
                _normalize("copied " + str(entry["name"])),
            }:
                slot = candidate_slot
                break
    if slot is None or slot not in worn:
        await session.send("No worn style appearance matches that slot or name.\r\n")
        return
    key = worn[slot]
    entry = _style_entry(session.database, session.character.id, key)
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM character_style_slots WHERE character_id = ? AND slot_key = ?",
            (session.character.id, slot),
        )
    await session.send(
        f"You remove {entry['name'] if entry else key} from your styled outfit. "
        "Your practical equipment remains unchanged.\r\n"
    )
    await _send_style_gmcp(session)


async def _show_fragrances(session) -> None:
    if session.character is None:
        return
    await session.send("\r\n--- Fragrance Wardrobe ---\r\n")
    owned = []
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        if key in FRAGRANCE_BY_KEY:
            owned.append((key, int(row["quantity"])))
    if not owned:
        await session.send("No bottles currently carried. Boutiques in Veyra and Waymeet sell select fragrances, and Alchemists can craft perfumes.\r\n")
    for key, quantity in owned:
        scent = FRAGRANCE_BY_KEY[key]
        await session.send(f"{quantity}x {scent.house} - {_item_name(key)} [{scent.rarity.upper()}] - {', '.join(scent.notes)} - +{scent.xp_bonus_percent}% XP / {scent.duration_seconds // 60} min\r\n")
    await session.send("APPLY FRAGRANCE <name>, APPLY PERFUME <name>, or SPRAY <name> consumes one bottle and starts its real-time XP effect. SCENT shows the current fragrance.\r\n")


async def _apply_fragrance(session, target: str) -> None:
    if session.character is None:
        return
    key, error = _resolve_owned_fragrance(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None
    scent = FRAGRANCE_BY_KEY[key]
    if not session.database.consume_item(session.character.id, key, 1):
        await session.send("That bottle is no longer in your inventory.\r\n")
        return
    now = int(time.time())
    ensure_style_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO character_fragrance_effects (character_id, fragrance_key, applied_at_epoch, expires_at_epoch, bonus_fraction, bonus_xp_earned) VALUES (?, ?, ?, ?, 0.0, 0) ON CONFLICT(character_id) DO UPDATE SET fragrance_key = excluded.fragrance_key, applied_at_epoch = excluded.applied_at_epoch, expires_at_epoch = excluded.expires_at_epoch, bonus_fraction = 0.0, bonus_xp_earned = 0",
            (session.character.id, key, now, now + scent.duration_seconds),
        )
    _mark_discovered(session.database, session.character.id, key)
    await session.send(
        f"You apply {scent.house}'s {_item_name(key)}. {', '.join(scent.notes).capitalize()} settle around you. "
        f"For the next {scent.duration_seconds // 60} real minutes, earned character XP is increased by {scent.xp_bonus_percent}%.\r\n"
    )
    await _send_style_gmcp(session)


async def _show_scent(session) -> None:
    if session.character is None:
        return
    row = _active_fragrance(session.database, session.character.id)
    if row is None:
        await session.send("You are not currently wearing an active fragrance.\r\n")
        return
    scent = FRAGRANCE_BY_KEY[str(row["fragrance_key"])]
    remaining = max(0, int(row["expires_at_epoch"]) - int(time.time()))
    minutes, seconds = divmod(remaining, 60)
    await session.send(
        f"Current fragrance: {scent.house} - {_item_name(scent.item_key)} [{scent.rarity.upper()}]\r\n"
        f"Notes: {', '.join(scent.notes)}.\r\n"
        f"Effect: +{scent.xp_bonus_percent}% character XP; {minutes}m {seconds}s remaining. Bonus XP earned from this application: {int(row['bonus_xp_earned'])}.\r\n"
    )


async def _show_collection(session) -> None:
    if session.character is None:
        return
    _sync_discoveries(session)
    ensure_style_schema(session.database)
    with session.database.connect() as db:
        rows = db.execute("SELECT item_key FROM character_style_discoveries WHERE character_id = ? ORDER BY item_key", (session.character.id,)).fetchall()
    keys = {str(row["item_key"]) for row in rows}
    await session.send("\r\n--- Style Collection ---\r\n")
    for rarity in RARITY_ORDER:
        style_keys = [key for key in keys if key in STYLE_META_BY_KEY and STYLE_META_BY_KEY[key].rarity == rarity]
        scent_keys = [key for key in keys if key in FRAGRANCE_BY_KEY and FRAGRANCE_BY_KEY[key].rarity == rarity]
        if style_keys or scent_keys:
            await session.send(f"{rarity.upper()}: {len(style_keys)} fashion, {len(scent_keys)} fragrances\r\n")
    await session.send(f"Discovered: {len(keys)} / {len(STYLE_META_BY_KEY) + len(FRAGRANCE_BY_KEY)} launch style entries. Consumed fragrance still counts as discovered.\r\n")
    await session.send("This is a collection record, not a power score. Rare labels describe scarcity and story, not combat strength.\r\n")


async def _show_seasonal(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    key = SEASONAL_STYLE[moment.season]
    meta = STYLE_META_BY_KEY[key]
    await session.send(
        f"Current Astralis seasonal edition - Year {moment.year}, {moment.season_name}: {_item_name(key)} [{meta.rarity.upper()} LIMITED].\r\n"
        "Earn it on your first tracked major-boss victory this Astralis season. It has no combat stats, and its provenance records the season, year, boss, and ownership chain.\r\n"
    )


async def _show_style_detail(session, key: str) -> None:
    if key in STYLE_META_BY_KEY:
        item = crafting.ITEMS_BY_KEY[key]
        meta = STYLE_META_BY_KEY[key]
        await session.send(
            f"\r\n{item.name} [{meta.rarity.upper()}{' - LIMITED' if meta.limited else ''}]\r\n"
            f"{item.description}\r\nStyle slot: {STYLE_SLOT_LABELS[meta.style_slot]}\r\n"
            f"House / maker: {meta.house}\r\nCollection: {meta.collection}\r\nStyle tags: {', '.join(meta.style_tags)}\r\nSource: {meta.acquisition_hint}\r\n"
            f"Combat effect: none. Provenance: {'tracked' if meta.provenance_track else 'ordinary item history only'}.\r\n"
        )
        return
    scent = FRAGRANCE_BY_KEY[key]
    item = crafting.ITEMS_BY_KEY[key]
    await session.send(
        f"\r\n{scent.house} - {item.name} [{scent.rarity.upper()}]\r\n{item.description}\r\n"
        f"Notes: {', '.join(scent.notes)}. Bottle: {scent.bottle}.\r\n"
        f"Effect when applied: +{scent.xp_bonus_percent}% character XP for {scent.duration_seconds // 60} real minutes.\r\n"
        "Applying consumes one bottle; the scent itself is visible when another player LOOKs at you.\r\n"
    )


async def _show_provenance(session, target: str) -> None:
    if session.character is None:
        return
    key, error = _resolve_owned_style(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None

    copied = _copied_style_row(session.database, session.character.id, key)
    if copied is not None:
        await session.send(
            f"\r\n--- Style Copy: {copied['source_name']} ---\r\n"
            f"Copied by {copied['copied_by']} from the ordinary equipment item "
            f"{copied['source_name']}.\r\n"
            "This is a personal wardrobe appearance, not a physical object. It cannot be traded, "
            "does not carry the source item's stats, and remains available even if the original gear leaves your possession.\r\n"
        )
        return

    meta = STYLE_META_BY_KEY[key]
    if not meta.provenance_track:
        await session.send(
            f"{_item_name(key)} is an ordinary {meta.house} piece. Its maker and collection are known, "
            "but individual ownership is not serialized.\r\n"
        )
        return
    _ensure_instances_for_inventory(session.database, session.character.id, key)
    instances = _owned_instances(session.database, session.character.id, key)
    await session.send(f"\r\n--- Provenance: {_item_name(key)} ---\r\n")
    with session.database.connect() as db:
        for instance in instances:
            await session.send(
                f"Serial {instance['serial']} - origin Day {instance['created_day']}: {instance['origin_text']}\r\n"
            )
            history = db.execute(
                """
                SELECT h.astralis_day, h.action, h.note,
                       f.name AS from_name, t.name AS to_name
                FROM style_item_history h
                LEFT JOIN characters f ON f.id = h.from_character_id
                LEFT JOIN characters t ON t.id = h.to_character_id
                WHERE h.instance_id = ? ORDER BY h.id
                """,
                (int(instance["id"]),),
            ).fetchall()
            for row in history:
                if row["action"] == "origin":
                    await session.send(
                        f"  Day {row['astralis_day']}: entered the collection of "
                        f"{row['to_name'] or 'an unknown owner'}.\r\n"
                    )
                else:
                    await session.send(
                        f"  Day {row['astralis_day']}: {row['from_name'] or 'unknown'} -> "
                        f"{row['to_name'] or 'unknown'} ({row['note']}).\r\n"
                    )

def _appearance_line(target_session) -> str:
    character = target_session.character
    stored = get_appearance(target_session.database, character.id)
    appearance = normalized_appearance(character.race or "human", stored)
    trait_map = {trait.key: trait.label.lower() for trait in traits_for_race(character.race or "human")}
    parts = [f"{trait_map[key]} {value}" for key, value in appearance.items() if key in trait_map and value != "none"]
    return ", ".join(parts) if parts else "an intentionally simple appearance"


async def _look_player(session, target_name: str) -> bool:
    if session.character is None:
        return False
    needle = target_name.strip().lower()
    target_session = None
    for other in tuple(social_experience._ACTIVE_SESSIONS):
        character = getattr(other, "character", None)
        if character is not None and character.name.lower() == needle and character.current_room == session.character.current_room:
            target_session = other
            break
    if target_session is None:
        return False
    target = target_session.character
    race = RACES_BY_KEY.get(target.race or "")
    klass = CLASSES_BY_KEY.get(target.character_class or "")
    await session.send(f"\r\n--- {target.name} ---\r\n")
    await session.send(f"Level {target.level} {race.name if race else target.race} {klass.name if klass else target.character_class}.\r\n")
    await session.send(f"Appearance: {_appearance_line(target_session)}.\r\n")
    worn = _worn_style(target_session.database, target.id)
    if worn:
        await session.send("Styled outfit:\r\n")
        for slot in STYLE_SLOTS:
            key = worn.get(slot)
            if not key:
                continue
            entry = _style_entry(target_session.database, target.id, key)
            if entry is None:
                continue
            label = entry["rarity"].upper() if entry["source_kind"] == "fashion" else "COPIED LOOK"
            await session.send(
                f"  {STYLE_SLOT_LABELS[slot]}: {entry['name']} [{label}]\r\n"
            )
    else:
        await session.send("Styled outfit: no visual overrides currently worn.\r\n")
    gear = equipped_definitions(target_session.database, target.id)
    visible_gear = [
        _item_name(definition.key)
        for slot, definition in gear.items()
        if slot not in worn
    ]
    if visible_gear:
        await session.send("Practical gear: " + ", ".join(visible_gear) + ".\r\n")
    scent_row = _active_fragrance(target_session.database, target.id)
    if scent_row is not None:
        scent = FRAGRANCE_BY_KEY[str(scent_row["fragrance_key"])]
        await session.send(f"Scent: {scent.house}'s {_item_name(scent.item_key)} - {', '.join(scent.notes)}.\r\n")
    return True


async def _send_style_gmcp(session) -> None:
    if session.character is None or not getattr(session.telnet, "gmcp_enabled", False):
        return
    worn = _worn_style(session.database, session.character.id)
    effect = _active_fragrance(session.database, session.character.id)
    outfit = {}
    for slot, key in worn.items():
        entry = _style_entry(session.database, session.character.id, key)
        if entry is None:
            continue
        outfit[slot] = {
            "item_key": key,
            "source_item_key": entry["source_item_key"],
            "name": entry["name"],
            "rarity": entry["rarity"],
            "source_kind": entry["source_kind"],
            "collection": entry["collection"],
        }
    payload = {
        "outfit": outfit,
        "copied_looks": [
            {
                "style_key": _copy_token(int(row["id"])),
                "source_item_key": str(row["source_item_key"]),
                "name": str(row["source_name"]),
                "default_slot": _style_slot_from_equipment_slot(str(row["source_equipment_slot"])),
            }
            for row in _copied_style_rows(session.database, session.character.id)
        ],
        "fragrance": None,
    }
    if effect is not None:
        scent = FRAGRANCE_BY_KEY[str(effect["fragrance_key"])]
        payload["fragrance"] = {
            "item_key": scent.item_key,
            "name": _item_name(scent.item_key),
            "house": scent.house,
            "notes": list(scent.notes),
            "xp_bonus_percent": scent.xp_bonus_percent,
            "expires_at_epoch": int(effect["expires_at_epoch"]),
        }
    await session.telnet.send_gmcp("Dreams.Style", payload)


async def _award_style_for_boss(session, enemy_key: str) -> None:
    if enemy_key not in BOSS_STYLE_DROPS:
        return
    try:
        participants = _party_sessions_here(session) or [session]
    except Exception:
        participants = [session]
    item_key, boss_name = BOSS_STYLE_DROPS[enemy_key]
    moment = ASTRALIS_CLOCK.now()
    seasonal_key = SEASONAL_STYLE[moment.season]
    for member in participants:
        if getattr(member, "character", None) is None:
            continue
        character = member.character
        ensure_style_schema(member.database)
        with member.database.connect() as db:
            boss_row = db.execute("SELECT 1 FROM character_style_boss_awards WHERE character_id = ? AND boss_key = ?", (character.id, enemy_key)).fetchone()
        if boss_row is None:
            member.database.add_item(character.id, item_key, 1)
            _mark_discovered(member.database, character.id, item_key)
            serial = _register_instance(member.database, character.id, item_key, f"Earned from {boss_name} by {character.name}.")
            with member.database.connect() as db:
                db.execute("INSERT INTO character_style_boss_awards (character_id, boss_key, item_key) VALUES (?, ?, ?)", (character.id, enemy_key, item_key))
            await member.send(f"\r\nHeritage style drop: {_item_name(item_key)} [{STYLE_META_BY_KEY[item_key].rarity.upper()}], serial {serial}. It has no combat stats; its provenance begins with this victory.\r\n")

        with member.database.connect() as db:
            season_row = db.execute("SELECT 1 FROM character_style_season_awards WHERE character_id = ? AND astralis_year = ? AND season_key = ?", (character.id, moment.year, moment.season)).fetchone()
        if season_row is None:
            member.database.add_item(character.id, seasonal_key, 1)
            _mark_discovered(member.database, character.id, seasonal_key)
            serial = _register_instance(member.database, character.id, seasonal_key, f"Year {moment.year} {moment.season_name} edition earned by {character.name} after defeating {boss_name}.")
            with member.database.connect() as db:
                db.execute("INSERT INTO character_style_season_awards (character_id, astralis_year, season_key, item_key) VALUES (?, ?, ?, ?)", (character.id, moment.year, moment.season, seasonal_key))
            await member.send(f"Seasonal edition earned: {_item_name(seasonal_key)} [EPIC LIMITED], serial {serial}. This is the Year {moment.year} {moment.season_name} edition.\r\n")
        await _send_style_gmcp(member)


def _patch_trade_for_provenance() -> None:
    if getattr(trade_experience, "_style_provenance_patch_installed", False):
        return
    original_exchange = trade_experience.exchange_items
    original_error = trade_experience._transferability_error

    def transferability_error(session, item_key: str, quantity: int):
        error = original_error(session, item_key, quantity)
        if error:
            return error
        character = getattr(session, "character", None)
        if character is not None and item_key in STYLE_META_BY_KEY and _is_style_worn(session.database, character.id, item_key):
            return f"Remove {_item_name(item_key)} from your styled outfit before transferring it."
        return None

    def exchange_items(database, first_character_id: int, first_offer: dict[str, int], second_character_id: int, second_offer: dict[str, int]) -> bool:
        for source_id, offer in ((first_character_id, first_offer), (second_character_id, second_offer)):
            for item_key in offer:
                if STYLE_META_BY_KEY.get(item_key) and STYLE_META_BY_KEY[item_key].provenance_track:
                    _ensure_instances_for_inventory(database, source_id, item_key)
        moved = original_exchange(database, first_character_id, first_offer, second_character_id, second_offer)
        if not moved:
            return False
        for item_key, quantity in first_offer.items():
            _move_instances(database, first_character_id, second_character_id, item_key, quantity, "direct player exchange")
        for item_key, quantity in second_offer.items():
            _move_instances(database, second_character_id, first_character_id, item_key, quantity, "direct player exchange")
        return True

    trade_experience._transferability_error = transferability_error
    trade_experience.exchange_items = exchange_items
    trade_experience._style_provenance_patch_installed = True


async def _delegate(self, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")
    async def replay(_text: str):
        return command
    self.prompt = replay
    try:
        await previous_prompt(self)
    finally:
        if had_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def _listed_style_key(session, command: str) -> str | None:
    # Veyra's player market uses LIST <qty> <item> FOR <qty> <item>.
    # Copied looks are wardrobe records, not transferable inventory objects.
    body = command.strip()[5:] if command.strip().lower().startswith("list ") else ""
    left = body.split(" for ", 1)[0].strip()
    parts = left.split()
    if parts and parts[0].isdigit():
        left = " ".join(parts[1:])
    key, _ = _resolve_owned_style(session, left)
    return key if key in STYLE_META_BY_KEY else None


def install_style_collectibles_runtime(player_session_class, world_service=None) -> None:
    install_style_content()
    _install_xp_bonus_hook()
    _patch_trade_for_provenance()
    if getattr(player_session_class, "_style_collectibles_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt
    previous_finish = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is None:
            return
        ensure_style_schema(self.database)
        _sync_discoveries(self)
        await self.send("\r\nStyle is live: WARDROBE shows fashion, FRAGRANCES shows scent bottles, and LOOK <player> now shows outfits. Fashion is cosmetic; fragrances provide the modest timed XP effect.\r\n")
        await _send_style_gmcp(self)

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        active = self.active_enemy is enemy
        await previous_finish(self, enemy)
        if active and key in BOSS_STYLE_DROPS:
            await _award_style_for_boss(self, key)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"style", "wardrobe", "outfit", "fashion"}:
            await _show_wardrobe(self); return
        if normalized in {"atelier", "style service", "style services", "style atelier"}:
            await _show_atelier(self, world_service); return
        if normalized in {"style slots", "fashion slots"}:
            await self.send(
                "Style slots: " + ", ".join(STYLE_SLOT_LABELS[slot] for slot in STYLE_SLOTS) + ".\r\n"
                "Each appearance keeps a compatible slot based on what it is: Head, Chest, Feet, Main Hand, "
                "Off Hand, and so on. A hood cannot be styled as a weapon or shield. "
                "Style never alters the real equipment underneath.\r\n"
            ); return
        if normalized.startswith("style copy "):
            await _copy_style_from_equipment(self, stripped[len("style copy "):], world_service); return
        if normalized.startswith("style wear "):
            await _wear_style(self, stripped[len("style wear "):]); return
        if normalized.startswith("style remove "):
            await _remove_style(self, stripped[len("style remove "):]); return
        if normalized.startswith("wear "):
            key, _ = _resolve_owned_style(self, stripped[len("wear "):])
            if key:
                await _wear_style(self, stripped[len("wear "):]); return
        if normalized in {"fragrance", "fragrances", "perfume", "perfumes"}:
            await _show_fragrances(self); return
        if normalized.startswith("apply fragrance "):
            await _apply_fragrance(self, stripped[len("apply fragrance "):]); return
        if normalized.startswith("apply perfume "):
            await _apply_fragrance(self, stripped[len("apply perfume "):]); return
        if normalized.startswith("spray "):
            await _apply_fragrance(self, stripped[len("spray "):]); return
        if normalized.startswith("apply "):
            key, _ = _resolve_owned_fragrance(self, stripped[len("apply "):])
            if key:
                await _apply_fragrance(self, stripped[len("apply "):]); return
        if normalized in {"scent", "current scent", "fragrance status"}:
            await _show_scent(self); return
        if normalized in {"boutique", "style shop", "fashion shop"}:
            await _show_boutique(self); return
        if normalized.startswith("buy style "):
            await _buy_boutique(self, stripped[len("buy style "):], fragrance=False); return
        if normalized.startswith("buy fragrance "):
            await _buy_boutique(self, stripped[len("buy fragrance "):], fragrance=True); return
        if normalized in {"collection", "style collection", "fashion collection"}:
            await _show_collection(self); return
        if normalized in {"seasonal style", "seasonal fashion", "limited style"}:
            await _show_seasonal(self); return
        if normalized.startswith("provenance "):
            await _show_provenance(self, stripped[len("provenance "):]); return
        if normalized.startswith("talk to ") and _is_pavo_target(stripped[len("talk to "):]):
            await _talk_pavo(self, world_service); return
        if normalized.startswith("talk ") and _is_pavo_target(stripped[len("talk "):]):
            await _talk_pavo(self, world_service); return
        if normalized.startswith("look at ") and _is_pavo_target(stripped[len("look at "):]):
            await _show_pavo(self, world_service); return
        if normalized.startswith("look ") and _is_pavo_target(stripped[len("look "):]):
            await _show_pavo(self, world_service); return
        if normalized.startswith("examine ") and _is_pavo_target(stripped[len("examine "):]):
            await _show_pavo(self, world_service); return
        if normalized.startswith("look "):
            if await _look_player(self, stripped[len("look "):]): return
        if normalized.startswith("item ") or normalized.startswith("inspect item "):
            target = stripped[len("item "):] if normalized.startswith("item ") else stripped[len("inspect item "):]
            wanted = _normalize(target)
            keys = [key for key in (*STYLE_META_BY_KEY.keys(), *FRAGRANCE_BY_KEY.keys()) if wanted in {_normalize(key), _normalize(_item_name(key))}]
            if len(keys) == 1 and self.database.item_quantity(self.character.id, keys[0]) > 0:
                await _show_style_detail(self, keys[0]); return
        if normalized.startswith("list ") and self.character.current_room == VEYRA_BRASSMARKET_KEY:
            key = _listed_style_key(self, stripped)
            if key and _is_style_worn(self.database, self.character.id, key):
                await self.send(f"Remove {_item_name(key)} from your styled outfit before listing it.\r\n"); return
            if key and STYLE_META_BY_KEY[key].provenance_track:
                await self.send("Serialized heritage fashion is exchanged directly with GIVE or TRADE so its ownership chain stays intact; the public escrow market does not accept it.\r\n"); return

        await _delegate(self, previous_prompt, command)
        if self.character is not None:
            _sync_discoveries(self)
            await _send_style_gmcp(self)

    player_session_class.enter_character = enter_character
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.playing_prompt = playing_prompt
    player_session_class._style_collectibles_runtime_installed = True
