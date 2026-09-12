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
from mud.equipment_system import equipped_definitions
from mud.gloamworks_dungeon import BURIED_REGENT_KEY
from mud.gravewatch_keep import CASTELLAN_KEY
from mud.party_system import _party_sessions_here
from mud.sablewater_reach import BRASS_AUDITOR_KEY
from mud.veyra_city import VEYRA_BRASSMARKET_KEY
from mud.veyra_underclock import GOVERNOR_KEY
from mud.waymeet_adventure_arc import LISTENER_BELOW
from mud.waymeet_frontier import WAYMEET_LANTERN_MARKET_KEY, WAYMEET_SCRIP_KEY


STYLE_VERSION = "1.0.0"
RARITY_ORDER = ("common", "uncommon", "rare", "epic", "legendary")
STYLE_SLOTS = (
    "head", "face", "neck", "shoulders", "chest", "hands",
    "waist", "legs", "feet", "back", "jewelry", "accessory",
)
STYLE_SLOT_LABELS = {slot: slot.replace("_", " ").title() for slot in STYLE_SLOTS}


@dataclass(frozen=True, slots=True)
class StyleMetadata:
    item_key: str
    rarity: str
    style_slot: str
    style_tags: tuple[str, ...]
    house: str
    collection: str
    acquisition_hint: str
    price_scrip: int = 0
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
    price_scrip: int = 3


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
        item_key = str(row["item_key"])
        if database.item_quantity(character_id, item_key) <= 0 or item_key not in STYLE_META_BY_KEY:
            with database.connect() as db:
                db.execute("DELETE FROM character_style_slots WHERE character_id = ? AND slot_key = ?", (character_id, slot))
            continue
        result[slot] = item_key
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
    matches = tuple(dict.fromkeys(exact or partial))
    if not matches:
        return None, "You do not own a fashion piece by that name."
    if len(matches) > 1:
        return None, "Be more specific: " + ", ".join(_item_name(key) for key in matches) + "."
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
        keys.extend(meta.item_key for meta in STYLE_META if meta.price_scrip > 0)
    if fragrance_only is not False:
        keys.extend(item.item_key for item in FRAGRANCES)
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
    keys = [meta.item_key for meta in STYLE_META if meta.price_scrip > 0] + [item.item_key for item in FRAGRANCES]
    if session.character.current_room == WAYMEET_LANTERN_MARKET_KEY:
        keys = [key for key in keys if key in WAYMEET_STYLE_KEYS]
    for key in keys:
        if key in STYLE_META_BY_KEY:
            meta = STYLE_META_BY_KEY[key]
            await session.send(f"[{meta.rarity.upper()}] {_item_name(key)} — {meta.price_scrip} scrip — {STYLE_SLOT_LABELS[meta.style_slot]} — {', '.join(meta.style_tags)}\r\n")
        else:
            scent = FRAGRANCE_BY_KEY[key]
            await session.send(f"[{scent.rarity.upper()}] {scent.house} — {_item_name(key)} — {scent.price_scrip} scrip — +{scent.xp_bonus_percent}% XP for {scent.duration_seconds // 60} min\r\n")
    await session.send("BUY STYLE <item> or BUY FRAGRANCE <name>. Fashion has no combat stats; fragrance is the only progression effect here.\r\n")


async def _buy_boutique(session, target: str, *, fragrance: bool) -> None:
    if session.character is None:
        return
    key, error = _resolve_boutique_item(session, target, fragrance_only=fragrance)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None
    price = FRAGRANCE_BY_KEY[key].price_scrip if key in FRAGRANCE_BY_KEY else STYLE_META_BY_KEY[key].price_scrip
    if session.database.item_quantity(session.character.id, WAYMEET_SCRIP_KEY) < price:
        await session.send(f"You need {price} Waymeet Trade Scrip.\r\n")
        return
    session.database.consume_item(session.character.id, WAYMEET_SCRIP_KEY, price)
    session.database.add_item(session.character.id, key, 1)
    _mark_discovered(session.database, session.character.id, key)
    await session.send(f"The counter wraps {_item_name(key)} carefully. You pay {price} Waymeet Trade Scrip.\r\n")


async def _show_wardrobe(session) -> None:
    if session.character is None:
        return
    worn = _worn_style(session.database, session.character.id)
    await session.send("\r\n--- Outfit ---\r\n")
    if not worn:
        await session.send("No fashion pieces are currently styled. Your combat equipment still exists separately.\r\n")
    else:
        for slot in STYLE_SLOTS:
            key = worn.get(slot)
            if key:
                meta = STYLE_META_BY_KEY[key]
                await session.send(f"{STYLE_SLOT_LABELS[slot]:<10}: {_item_name(key)} [{meta.rarity.upper()}] — {meta.house}\r\n")
    await session.send("\r\n--- Wardrobe You Carry ---\r\n")
    found = False
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        meta = STYLE_META_BY_KEY.get(key)
        if meta is None:
            continue
        found = True
        marker = " [WORN]" if key in worn.values() else ""
        limited = " LIMITED" if meta.limited else ""
        await session.send(f"{int(row['quantity'])}x {_item_name(key)} [{meta.rarity.upper()}{limited}] — {STYLE_SLOT_LABELS[meta.style_slot]}{marker}\r\n")
    if not found:
        await session.send("No fashion pieces yet. BOUTIQUE shows ordinary designer pieces; dungeon and seasonal heritage pieces come from play.\r\n")
    await session.send("STYLE WEAR <item> | STYLE REMOVE <slot> | LOOK <player> | COLLECTION | PROVENANCE <item>\r\n")


async def _wear_style(session, target: str) -> None:
    if session.character is None:
        return
    key, error = _resolve_owned_style(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert key is not None
    meta = STYLE_META_BY_KEY[key]
    ensure_style_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT INTO character_style_slots (character_id, slot_key, item_key) VALUES (?, ?, ?) ON CONFLICT(character_id, slot_key) DO UPDATE SET item_key = excluded.item_key, worn_at = CURRENT_TIMESTAMP",
            (session.character.id, meta.style_slot, key),
        )
    _mark_discovered(session.database, session.character.id, key)
    await session.send(f"You style {_item_name(key)} in your {STYLE_SLOT_LABELS[meta.style_slot]} slot. It changes appearance, not combat stats.\r\n")
    await _send_style_gmcp(session)


async def _remove_style(session, target: str) -> None:
    if session.character is None:
        return
    wanted = _normalize(target)
    worn = _worn_style(session.database, session.character.id)
    slot = next((slot for slot in STYLE_SLOTS if wanted in {_normalize(slot), _normalize(STYLE_SLOT_LABELS[slot])}), None)
    if slot is None:
        slot = next((slot for slot, key in worn.items() if wanted in {_normalize(key), _normalize(_item_name(key))}), None)
    if slot is None or slot not in worn:
        await session.send("No worn fashion piece matches that slot or name.\r\n")
        return
    key = worn[slot]
    with session.database.connect() as db:
        db.execute("DELETE FROM character_style_slots WHERE character_id = ? AND slot_key = ?", (session.character.id, slot))
    await session.send(f"You remove {_item_name(key)} from your styled outfit.\r\n")
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
        await session.send("No bottles currently carried. Boutiques in Veyra and Waymeet sell fragrance.\r\n")
    for key, quantity in owned:
        scent = FRAGRANCE_BY_KEY[key]
        await session.send(f"{quantity}x {scent.house} — {_item_name(key)} [{scent.rarity.upper()}] — {', '.join(scent.notes)} — +{scent.xp_bonus_percent}% XP / {scent.duration_seconds // 60} min\r\n")
    await session.send("APPLY FRAGRANCE <name> consumes one bottle and starts its real-time effect. SCENT shows the current fragrance.\r\n")


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
        f"Current fragrance: {scent.house} — {_item_name(scent.item_key)} [{scent.rarity.upper()}]\r\n"
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
        f"Current Astralis seasonal edition — Year {moment.year}, {moment.season_name}: {_item_name(key)} [{meta.rarity.upper()} LIMITED].\r\n"
        "Earn it on your first tracked major-boss victory this Astralis season. It has no combat stats, and its provenance records the season, year, boss, and ownership chain.\r\n"
    )


async def _show_style_detail(session, key: str) -> None:
    if key in STYLE_META_BY_KEY:
        item = crafting.ITEMS_BY_KEY[key]
        meta = STYLE_META_BY_KEY[key]
        await session.send(
            f"\r\n{item.name} [{meta.rarity.upper()}{' — LIMITED' if meta.limited else ''}]\r\n"
            f"{item.description}\r\nStyle slot: {STYLE_SLOT_LABELS[meta.style_slot]}\r\n"
            f"House / maker: {meta.house}\r\nCollection: {meta.collection}\r\nStyle tags: {', '.join(meta.style_tags)}\r\nSource: {meta.acquisition_hint}\r\n"
            f"Combat effect: none. Provenance: {'tracked' if meta.provenance_track else 'ordinary item history only'}.\r\n"
        )
        return
    scent = FRAGRANCE_BY_KEY[key]
    item = crafting.ITEMS_BY_KEY[key]
    await session.send(
        f"\r\n{scent.house} — {item.name} [{scent.rarity.upper()}]\r\n{item.description}\r\n"
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
    meta = STYLE_META_BY_KEY[key]
    if not meta.provenance_track:
        await session.send(f"{_item_name(key)} is an ordinary {meta.house} piece. Its maker and collection are known, but individual ownership is not serialized.\r\n")
        return
    _ensure_instances_for_inventory(session.database, session.character.id, key)
    instances = _owned_instances(session.database, session.character.id, key)
    await session.send(f"\r\n--- Provenance: {_item_name(key)} ---\r\n")
    with session.database.connect() as db:
        for instance in instances:
            await session.send(f"Serial {instance['serial']} — origin Day {instance['created_day']}: {instance['origin_text']}\r\n")
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
                    await session.send(f"  Day {row['astralis_day']}: entered the collection of {row['to_name'] or 'an unknown owner'}.\r\n")
                else:
                    await session.send(f"  Day {row['astralis_day']}: {row['from_name'] or 'unknown'} → {row['to_name'] or 'unknown'} ({row['note']}).\r\n")


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
            if key:
                meta = STYLE_META_BY_KEY[key]
                await session.send(f"  {STYLE_SLOT_LABELS[slot]}: {_item_name(key)} [{meta.rarity.upper()}]\r\n")
    else:
        await session.send("Styled outfit: no separate fashion pieces currently worn.\r\n")
    gear = equipped_definitions(target_session.database, target.id)
    visible_gear = [_item_name(definition.key) for slot, definition in gear.items() if slot not in worn]
    if visible_gear:
        await session.send("Practical gear: " + ", ".join(visible_gear) + ".\r\n")
    scent_row = _active_fragrance(target_session.database, target.id)
    if scent_row is not None:
        scent = FRAGRANCE_BY_KEY[str(scent_row["fragrance_key"])]
        await session.send(f"Scent: {scent.house}'s {_item_name(scent.item_key)} — {', '.join(scent.notes)}.\r\n")
    return True


async def _send_style_gmcp(session) -> None:
    if session.character is None or not getattr(session.telnet, "gmcp_enabled", False):
        return
    worn = _worn_style(session.database, session.character.id)
    effect = _active_fragrance(session.database, session.character.id)
    payload = {
        "outfit": {slot: {"item_key": key, "name": _item_name(key), "rarity": STYLE_META_BY_KEY[key].rarity} for slot, key in worn.items()},
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
    body = command.strip()[5:] if command.strip().lower().startswith("list ") else ""
    left = body.split(" for ", 1)[0].strip()
    parts = left.split()
    if parts and parts[0].isdigit():
        left = " ".join(parts[1:])
    key, _ = _resolve_owned_style(session, left)
    return key


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
