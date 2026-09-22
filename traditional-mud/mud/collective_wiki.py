from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable
from urllib.parse import urlparse

from mud.astralis_time import ASTRALIS_CLOCK


WIKI_SCHEMA = """
CREATE TABLE IF NOT EXISTS collective_wiki_entries (
    category TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    region_key TEXT NOT NULL DEFAULT '',
    room_key TEXT NOT NULL DEFAULT '',
    first_character_id INTEGER,
    first_character_name TEXT NOT NULL DEFAULT '',
    first_astralis_day INTEGER,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category, entry_key),
    FOREIGN KEY (first_character_id) REFERENCES characters(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_collective_wiki_entries_category
ON collective_wiki_entries(category, first_seen_at);

CREATE TABLE IF NOT EXISTS collective_wiki_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    heading TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    source_kind TEXT NOT NULL DEFAULT 'observation',
    first_character_id INTEGER,
    first_character_name TEXT NOT NULL DEFAULT '',
    first_astralis_day INTEGER,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, entry_key, fact_key),
    FOREIGN KEY (category, entry_key)
        REFERENCES collective_wiki_entries(category, entry_key) ON DELETE CASCADE,
    FOREIGN KEY (first_character_id) REFERENCES characters(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_collective_wiki_facts_entry
ON collective_wiki_facts(category, entry_key, id);

CREATE TABLE IF NOT EXISTS collective_wiki_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    fact_key TEXT NOT NULL DEFAULT '',
    event_kind TEXT NOT NULL,
    label TEXT NOT NULL,
    character_name TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_collective_wiki_activity_id
ON collective_wiki_activity(id DESC);
"""


@dataclass(frozen=True, slots=True)
class WikiFact:
    key: str
    heading: str
    text: str
    source_kind: str = "observation"


@dataclass(slots=True)
class WikiServerHandle:
    server: ThreadingHTTPServer
    thread: threading.Thread
    host: str
    port: int

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _humanize(value: str) -> str:
    return _clean(value).replace("_", " ").replace("-", " ").title()


def _character_identity(session) -> tuple[int | None, str]:
    character = getattr(session, "character", None)
    if character is None:
        return None, ""
    try:
        character_id = int(character.id)
    except Exception:
        character_id = None
    return character_id, _clean(getattr(character, "name", ""))


def _astralis_day() -> int | None:
    try:
        return int(ASTRALIS_CLOCK.now().day_number)
    except Exception:
        return None


def ensure_collective_wiki_schema(database) -> None:
    with database.connect() as db:
        db.executescript(WIKI_SCHEMA)


def record_wiki_entry(
    database,
    *,
    category: str,
    entry_key: str,
    title: str,
    summary: str = "",
    region_key: str = "",
    room_key: str = "",
    facts: Iterable[WikiFact] = (),
    character_id: int | None = None,
    character_name: str = "",
    astralis_day: int | None = None,
) -> bool:
    """Publish player-known information without ever reading undiscovered content.

    The ledger only grows. An entry or fact already known by the community is
    left unchanged, while a genuinely new fact creates a live activity event.
    """

    category = _clean(category).casefold().replace(" ", "_")
    entry_key = _clean(entry_key)
    title = _clean(title)
    summary = _clean(summary)
    region_key = _clean(region_key)
    room_key = _clean(room_key)
    character_name = _clean(character_name)
    if not category or not entry_key or not title:
        return False

    ensure_collective_wiki_schema(database)
    changed = False
    day = astralis_day if astralis_day is not None else _astralis_day()

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        entry_cursor = db.execute(
            """
            INSERT OR IGNORE INTO collective_wiki_entries
            (category, entry_key, title, summary, region_key, room_key,
             first_character_id, first_character_name, first_astralis_day)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                entry_key,
                title,
                summary,
                region_key,
                room_key,
                character_id,
                character_name,
                day,
            ),
        )
        if entry_cursor.rowcount:
            changed = True
            db.execute(
                """
                INSERT INTO collective_wiki_activity
                (category, entry_key, event_kind, label, character_name)
                VALUES (?, ?, 'entry', ?, ?)
                """,
                (category, entry_key, title, character_name),
            )
        elif summary:
            db.execute(
                """
                UPDATE collective_wiki_entries
                SET summary = CASE WHEN summary = '' THEN ? ELSE summary END,
                    region_key = CASE WHEN region_key = '' THEN ? ELSE region_key END,
                    room_key = CASE WHEN room_key = '' THEN ? ELSE room_key END
                WHERE category = ? AND entry_key = ?
                """,
                (summary, region_key, room_key, category, entry_key),
            )

        for fact in facts:
            fact_key = _clean(fact.key)
            text = str(fact.text or "").strip()
            if not fact_key or not text:
                continue
            heading = _clean(fact.heading)
            source_kind = _clean(fact.source_kind) or "observation"
            fact_cursor = db.execute(
                """
                INSERT OR IGNORE INTO collective_wiki_facts
                (category, entry_key, fact_key, heading, text, source_kind,
                 first_character_id, first_character_name, first_astralis_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    entry_key,
                    fact_key,
                    heading,
                    text,
                    source_kind,
                    character_id,
                    character_name,
                    day,
                ),
            )
            if fact_cursor.rowcount:
                changed = True
                db.execute(
                    """
                    INSERT INTO collective_wiki_activity
                    (category, entry_key, fact_key, event_kind, label, character_name)
                    VALUES (?, ?, ?, 'fact', ?, ?)
                    """,
                    (
                        category,
                        entry_key,
                        fact_key,
                        heading or title,
                        character_name,
                    ),
                )
    return changed


def record_room_view(session, world_service, *, view=None, scene=None) -> bool:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or world_service is None:
        return False

    room_key = _clean(getattr(character, "current_room", ""))
    if not room_key:
        return False
    if scene is None:
        scene = world_service.scene(room_key)
    if scene is None:
        return False
    if view is None:
        try:
            view = world_service.build_view(room_key, None)
        except Exception:
            view = None
    if view is None:
        return False

    character_id, character_name = _character_identity(session)
    facts: list[WikiFact] = []
    description = str(getattr(view, "description", "") or "").strip()
    if description:
        description_id = hashlib.sha1(description.encode("utf-8")).hexdigest()[:12]
        facts.append(
            WikiFact(
                f"description:{description_id}",
                "Observed Description",
                description,
                "room_view",
            )
        )

    for feature in tuple(getattr(view, "features", ()) or ()):
        feature_key = _clean(getattr(feature, "key", "")) or _clean(getattr(feature, "name", ""))
        feature_name = _clean(getattr(feature, "name", ""))
        feature_summary = str(getattr(feature, "summary", "") or "").strip()
        if feature_key and feature_name:
            facts.append(
                WikiFact(
                    f"feature:{feature_key}",
                    feature_name,
                    feature_summary or f"A notable feature observed in {getattr(view, 'name', 'this place')}.",
                    "room_feature",
                )
            )

    for exit_view in tuple(getattr(view, "exits", ()) or ()):
        direction = _clean(getattr(exit_view, "direction", ""))
        if not direction:
            continue
        destination_name = _clean(getattr(exit_view, "name", ""))
        text = f"An exit leads {direction.upper()}."
        if destination_name:
            text = f"The {direction.upper()} exit leads toward {destination_name}."
        route_id = hashlib.sha1((direction.casefold() + "|" + destination_name).encode("utf-8")).hexdigest()[:10]
        facts.append(
            WikiFact(
                f"exit:{direction.casefold()}:{route_id}",
                f"Exit: {direction.upper()}",
                text,
                "room_exit",
            )
        )

    region_key = _clean(getattr(scene, "region_key", ""))
    return record_wiki_entry(
        database,
        category="place",
        entry_key=room_key,
        title=_clean(getattr(view, "name", "")) or _humanize(room_key),
        summary=f"{_humanize(region_key)} · discovered location" if region_key else "Discovered location",
        region_key=region_key,
        room_key=room_key,
        facts=facts,
        character_id=character_id,
        character_name=character_name,
    )


def record_actor_discovery(
    session,
    *,
    category: str,
    entry_key: str,
    name: str,
    description: str = "",
    room_key: str = "",
    region_key: str = "",
) -> bool:
    database = getattr(session, "database", None)
    if database is None:
        return False
    character_id, character_name = _character_identity(session)
    facts = ()
    if str(description or "").strip():
        facts = (WikiFact("description", "Description", str(description).strip(), "visible_actor"),)
    return record_wiki_entry(
        database,
        category=category,
        entry_key=entry_key,
        title=name,
        summary=f"First observed in {_humanize(region_key)}" if region_key else "Observed in Astralis",
        region_key=region_key,
        room_key=room_key,
        facts=facts,
        character_id=character_id,
        character_name=character_name,
    )


def record_character_known_state(session) -> None:
    """Publish durable things this character has actually acquired or begun."""

    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None:
        return
    character_id, character_name = _character_identity(session)
    if character_id is None:
        return

    # Race and class identity are already exposed during character creation, so
    # the community can safely gain those overview pages when somebody actually
    # enters the world with that choice. Deeper lore is not copied wholesale.
    try:
        from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY

        race_key = _clean(getattr(character, "race", ""))
        race = RACES_BY_KEY.get(race_key)
        if race is not None:
            race_facts = [
                WikiFact("description", "Overview", race.description, "character_identity")
            ]
            if getattr(race, "passive_name", None) and getattr(race, "passive_description", None):
                race_facts.append(
                    WikiFact(
                        "passive",
                        str(race.passive_name),
                        str(race.passive_description),
                        "character_identity",
                    )
                )
            record_wiki_entry(
                database,
                category="race",
                entry_key=race_key,
                title=race.name,
                summary="A playable people encountered through the community.",
                facts=race_facts,
                character_id=character_id,
                character_name=character_name,
            )

        class_key = _clean(getattr(character, "character_class", ""))
        character_class = CLASSES_BY_KEY.get(class_key)
        if character_class is not None:
            class_facts = [
                WikiFact(
                    "description",
                    "Overview",
                    character_class.description,
                    "character_identity",
                )
            ]
            record_wiki_entry(
                database,
                category="class",
                entry_key=class_key,
                title=character_class.name,
                summary="A playable class represented by at least one traveler.",
                facts=class_facts,
                character_id=character_id,
                character_name=character_name,
            )
    except Exception:
        pass

    # Abilities become communal knowledge after somebody has actually practiced
    # them. This avoids turning the wiki into an automatic dump of future class
    # progression names that nobody has reached yet.
    try:
        from mud.mechanics import FIXED_CLASS_ABILITIES, PRIEST_DEITY_ABILITIES

        ability_catalog = {}
        for ability_group in tuple(FIXED_CLASS_ABILITIES.values()) + tuple(PRIEST_DEITY_ABILITIES.values()):
            for ability in ability_group:
                ability_catalog.setdefault(ability.key, ability)
        with database.connect() as db:
            ability_rows = db.execute(
                """
                SELECT ability_key, uses, skill_xp
                FROM character_abilities
                WHERE character_id = ? AND (uses > 0 OR skill_xp > 0)
                """,
                (character_id,),
            ).fetchall()
        for row in ability_rows:
            ability_key = str(row["ability_key"])
            ability = ability_catalog.get(ability_key)
            title = _clean(getattr(ability, "name", "")) if ability is not None else _humanize(ability_key)
            description = str(getattr(ability, "description", "") or "").strip() if ability is not None else ""
            facts = [
                WikiFact(
                    "practiced",
                    "Known Technique",
                    "At least one traveler has used this ability in play.",
                    "ability_use",
                )
            ]
            if description:
                facts.append(WikiFact("description", "Description", description, "ability_use"))
            record_wiki_entry(
                database,
                category="ability",
                entry_key=ability_key,
                title=title or _humanize(ability_key),
                summary="An ability practiced by the player community.",
                facts=facts,
                character_id=character_id,
                character_name=character_name,
            )
    except Exception:
        pass

    try:
        from mud.crafting import ITEMS_BY_KEY
        with database.connect() as db:
            item_rows = db.execute(
                """
                SELECT item_key, quantity
                FROM character_items
                WHERE character_id = ? AND quantity > 0
                """,
                (character_id,),
            ).fetchall()
        for row in item_rows:
            item_key = str(row["item_key"])
            item = ITEMS_BY_KEY.get(item_key)
            title = _clean(getattr(item, "name", "")) if item is not None else _humanize(item_key)
            description = str(getattr(item, "description", "") or "").strip() if item is not None else ""
            facts = [WikiFact("obtained", "Known to Exist", "At least one traveler has physically obtained this item.", "inventory")]
            if description:
                facts.append(WikiFact("description", "Description", description, "inventory"))
            record_wiki_entry(
                database,
                category="item",
                entry_key=item_key,
                title=title or _humanize(item_key),
                summary="An item recovered, crafted, purchased, or otherwise obtained in Astralis.",
                facts=facts,
                character_id=character_id,
                character_name=character_name,
            )
    except Exception:
        pass

    try:
        from mud.quests import QUESTS_BY_KEY
        with database.connect() as db:
            quest_rows = db.execute(
                """
                SELECT quest_key, status
                FROM character_quests
                WHERE character_id = ?
                """,
                (character_id,),
            ).fetchall()
        for row in quest_rows:
            quest_key = str(row["quest_key"])
            status = _clean(row["status"]).casefold() or "known"
            quest = QUESTS_BY_KEY.get(quest_key)
            title = ""
            description = ""
            if quest is not None:
                title = _clean(getattr(quest, "name", "") or getattr(quest, "title", ""))
                description = str(
                    getattr(quest, "description", "")
                    or getattr(quest, "summary", "")
                    or ""
                ).strip()
            facts = [
                WikiFact(
                    f"status:{status}",
                    _humanize(status),
                    (
                        "At least one traveler has completed this quest."
                        if status == "completed"
                        else "At least one traveler has encountered this quest."
                    ),
                    "quest_state",
                )
            ]
            if description:
                facts.append(WikiFact("description", "Description", description, "quest_state"))
            record_wiki_entry(
                database,
                category="quest",
                entry_key=quest_key,
                title=title or _humanize(quest_key),
                summary="A quest encountered by the player community.",
                facts=facts,
                character_id=character_id,
                character_name=character_name,
            )
    except Exception:
        pass


def record_hidden_discovery(session, world_service, definition, *, trigger: str = "") -> None:
    database = getattr(session, "database", None)
    character = getattr(session, "character", None)
    if database is None or character is None or definition is None:
        return

    room_key = _clean(getattr(character, "current_room", ""))
    scene = world_service.scene(room_key) if world_service is not None and room_key else None
    room_name = _clean(getattr(scene, "name", "")) or "an unknown place"
    region_key = _clean(getattr(scene, "region_key", "")) if scene is not None else ""
    character_id, character_name = _character_identity(session)
    kind = _humanize(_clean(getattr(definition, "kind", "discovery"))) or "Discovery"
    discovery_text = str(getattr(definition, "text", "") or "").strip()

    facts: list[WikiFact] = []
    if discovery_text:
        facts.append(WikiFact("revelation", "What Was Learned", discovery_text, "hidden_discovery"))
    normalized_trigger = _clean(trigger.replace(":", " "))
    if normalized_trigger and normalized_trigger != "enter":
        facts.append(
            WikiFact(
                "method",
                "How It Was Found",
                f"A traveler uncovered it by trying: {normalized_trigger}.",
                "hidden_discovery",
            )
        )
    elif normalized_trigger == "enter":
        facts.append(
            WikiFact(
                "method",
                "How It Was Found",
                "A traveler uncovered it simply by arriving while the right world conditions were in place.",
                "hidden_discovery",
            )
        )

    record_wiki_entry(
        database,
        category="discovery",
        entry_key=_clean(getattr(definition, "key", "")),
        title=f"{kind} — {room_name}",
        summary=f"A communal discovery first recorded near {room_name}.",
        region_key=region_key,
        room_key=room_key,
        facts=facts,
        character_id=character_id,
        character_name=character_name,
    )

    if discovery_text and room_key:
        record_wiki_entry(
            database,
            category="place",
            entry_key=room_key,
            title=room_name,
            summary=f"{_humanize(region_key)} · discovered location" if region_key else "Discovered location",
            region_key=region_key,
            room_key=room_key,
            facts=(
                WikiFact(
                    f"discovery:{_clean(getattr(definition, 'key', ''))}",
                    kind,
                    discovery_text,
                    "hidden_discovery",
                ),
            ),
            character_id=character_id,
            character_name=character_name,
        )


def collective_wiki_snapshot(database, *, activity_limit: int = 40) -> dict[str, object]:
    ensure_collective_wiki_schema(database)
    with database.connect() as db:
        entries = db.execute(
            """
            SELECT category, entry_key, title, summary, region_key, room_key,
                   first_character_name, first_astralis_day, first_seen_at
            FROM collective_wiki_entries
            ORDER BY category, title COLLATE NOCASE, entry_key
            """
        ).fetchall()
        facts = db.execute(
            """
            SELECT category, entry_key, fact_key, heading, text, source_kind,
                   first_character_name, first_astralis_day, discovered_at
            FROM collective_wiki_facts
            ORDER BY id
            """
        ).fetchall()
        activity = db.execute(
            """
            SELECT id, category, entry_key, fact_key, event_kind, label,
                   character_name, created_at
            FROM collective_wiki_activity
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(activity_limit), 200)),),
        ).fetchall()
        category_rows = db.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM collective_wiki_entries
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
        revision_row = db.execute("SELECT COALESCE(MAX(id), 0) AS revision FROM collective_wiki_activity").fetchone()

    facts_by_entry: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in facts:
        facts_by_entry.setdefault((str(row["category"]), str(row["entry_key"])), []).append(
            {
                "key": str(row["fact_key"]),
                "heading": str(row["heading"]),
                "text": str(row["text"]),
                "source": str(row["source_kind"]),
                "first_discoverer": str(row["first_character_name"] or ""),
                "astralis_day": row["first_astralis_day"],
                "discovered_at": str(row["discovered_at"]),
            }
        )

    payload_entries: list[dict[str, object]] = []
    for row in entries:
        key = (str(row["category"]), str(row["entry_key"]))
        payload_entries.append(
            {
                "category": key[0],
                "key": key[1],
                "title": str(row["title"]),
                "summary": str(row["summary"]),
                "region": str(row["region_key"]),
                "room": str(row["room_key"]),
                "first_discoverer": str(row["first_character_name"] or ""),
                "astralis_day": row["first_astralis_day"],
                "first_seen_at": str(row["first_seen_at"]),
                "facts": facts_by_entry.get(key, []),
            }
        )

    return {
        "revision": int(revision_row["revision"] if revision_row is not None else 0),
        "entry_count": len(payload_entries),
        "categories": {str(row["category"]): int(row["count"]) for row in category_rows},
        "entries": payload_entries,
        "activity": [
            {
                "id": int(row["id"]),
                "category": str(row["category"]),
                "key": str(row["entry_key"]),
                "fact_key": str(row["fact_key"]),
                "event": str(row["event_kind"]),
                "label": str(row["label"]),
                "character": str(row["character_name"] or ""),
                "created_at": str(row["created_at"]),
            }
            for row in activity
        ],
    }


WIKI_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b0b0d">
<title>Dreams of the Fallen — Living Wiki</title>
<style>
:root{--bg:#09090b;--panel:#111114;--panel2:#16161a;--line:#29292f;--text:#f2efe6;--muted:#9b9890;--gold:#d5ad62;--soft:#d9d3c5;--shadow:0 24px 80px rgba(0,0,0,.38)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% -10%,#222027 0,transparent 34%),var(--bg);color:var(--text);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
button,input{font:inherit}.shell{max-width:1440px;margin:0 auto;padding:28px}.mast{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;border-bottom:1px solid var(--line);padding:28px 0 24px}.eyebrow{text-transform:uppercase;letter-spacing:.18em;color:var(--gold);font-size:11px;font-weight:800}.title{font-family:Georgia,"Times New Roman",serif;font-size:clamp(34px,6vw,76px);line-height:.95;margin:10px 0 0;letter-spacing:-.045em}.dek{max-width:700px;color:var(--muted);margin:14px 0 0;font-size:16px}.live{display:flex;align-items:center;gap:9px;color:var(--soft);white-space:nowrap}.dot{width:8px;height:8px;border-radius:50%;background:#7fc48c;box-shadow:0 0 0 5px rgba(127,196,140,.12)}
.toolbar{display:grid;grid-template-columns:minmax(240px,1fr) auto;gap:14px;margin:24px 0}.search{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:14px;color:var(--text);padding:13px 15px;outline:none}.search:focus{border-color:#5d5342}.filters{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.chip{background:transparent;color:var(--muted);border:1px solid var(--line);padding:10px 12px;border-radius:999px;cursor:pointer}.chip.active,.chip:hover{background:var(--soft);color:#121214;border-color:var(--soft)}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:22px}.panel{background:rgba(17,17,20,.9);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}.known{padding:8px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}.card{appearance:none;width:100%;text-align:left;background:var(--panel2);color:var(--text);border:1px solid transparent;border-radius:14px;padding:17px;cursor:pointer;min-height:150px;transition:.18s ease}.card:hover{transform:translateY(-2px);border-color:#454149;background:#1c1c21}.tag{text-transform:uppercase;letter-spacing:.13em;color:var(--gold);font-size:10px;font-weight:800}.card h3{font-family:Georgia,"Times New Roman",serif;font-size:22px;line-height:1.05;margin:11px 0 9px}.card p{margin:0;color:var(--muted);font-size:13px}.meta{margin-top:16px;color:#77736b;font-size:11px}.side{padding:20px;position:sticky;top:18px;align-self:start;max-height:calc(100vh - 36px);overflow:auto}.side h2{font-family:Georgia,"Times New Roman",serif;font-size:26px;margin:4px 0 6px}.side .summary{color:var(--muted);margin-bottom:18px}.fact{border-top:1px solid var(--line);padding:15px 0}.fact h4{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--gold)}.fact p{margin:0;color:var(--soft);white-space:pre-wrap}.credit{color:#77736b;font-size:11px;margin-top:7px}.activity{margin-top:28px}.activity h3{font-size:11px;text-transform:uppercase;letter-spacing:.16em;color:var(--muted)}.event{padding:10px 0;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.event strong{color:var(--soft)}
.blank{padding:70px 28px;text-align:center}.blank .mark{font-family:Georgia,"Times New Roman",serif;font-size:54px;color:var(--gold)}.blank h2{font-family:Georgia,"Times New Roman",serif;font-size:30px;margin:8px 0}.blank p{color:var(--muted);max-width:520px;margin:0 auto}.stats{display:flex;gap:16px;flex-wrap:wrap;margin-top:22px;color:var(--muted);font-size:12px}.stats strong{color:var(--text);font-size:20px;margin-right:5px}.footer{color:#67645d;font-size:11px;padding:25px 4px 50px}.hidden{display:none!important}
@media(max-width:920px){.shell{padding:18px}.mast{align-items:flex-start;flex-direction:column}.toolbar{grid-template-columns:1fr}.filters{justify-content:flex-start}.grid{grid-template-columns:1fr}.side{position:relative;top:auto;max-height:none}.title{font-size:48px}}
</style>
</head>
<body>
<main class="shell">
  <header class="mast">
    <div><div class="eyebrow">Dreams of the Fallen · Astralis</div><h1 class="title">The Living Wiki</h1><p class="dek">A communal record written by play. Nothing appears here until somebody in Astralis actually encounters it.</p></div>
    <div class="live"><span class="dot"></span><span>Live collective knowledge</span></div>
  </header>
  <div class="stats"><span><strong id="entryCount">0</strong>known entries</span><span id="lastUpdate">Waiting for the first discovery…</span></div>
  <section class="toolbar"><input id="search" class="search" type="search" placeholder="Search what the community knows…" autocomplete="off"><div id="filters" class="filters"></div></section>
  <section class="grid">
    <div class="panel known"><div id="cards" class="cards"></div><div id="blank" class="blank"><div class="mark">◇</div><h2>The record is blank.</h2><p>The first room visited, person met, item obtained, quest encountered, creature seen, or secret uncovered will write the opening page.</p></div></div>
    <aside class="panel side"><div class="eyebrow">Selected entry</div><div id="article"><h2>No entry selected</h2><p class="summary">Choose anything the community has discovered to read everything currently known about it.</p></div><div class="activity"><h3>Latest additions</h3><div id="activity"></div></div></aside>
  </section>
  <div class="footer">There is deliberately no “percent complete” display. Undiscovered content remains absent rather than being turned into a checklist.</div>
</main>
<script>
const state={data:null,category:'all',query:'',selected:null};
const el=id=>document.getElementById(id);
const label=s=>String(s||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
function credit(x){const bits=[];if(x.first_discoverer)bits.push('First recorded by '+x.first_discoverer);if(x.astralis_day!=null)bits.push('Astralis day '+x.astralis_day);return bits.join(' · ')}
function renderFilters(){const cats=Object.keys(state.data?.categories||{});el('filters').replaceChildren();[['all','All'],...cats.map(c=>[c,label(c)])].forEach(([key,name])=>{const b=document.createElement('button');b.className='chip'+(state.category===key?' active':'');b.textContent=name+(key==='all'?'':' '+state.data.categories[key]);b.onclick=()=>{state.category=key;renderFilters();renderCards()};el('filters').append(b)})}
function filtered(){const q=state.query.trim().toLowerCase();return (state.data?.entries||[]).filter(x=>(state.category==='all'||x.category===state.category)&&(!q||[x.title,x.summary,x.region,...x.facts.map(f=>f.heading+' '+f.text)].join(' ').toLowerCase().includes(q)))}
function renderCards(){const cards=el('cards');cards.replaceChildren();const items=filtered();el('blank').classList.toggle('hidden',(state.data?.entry_count||0)>0);items.forEach(x=>{const b=document.createElement('button');b.className='card';const t=document.createElement('div');t.className='tag';t.textContent=label(x.category);const h=document.createElement('h3');h.textContent=x.title;const p=document.createElement('p');p.textContent=x.summary||'Known to the community.';const m=document.createElement('div');m.className='meta';m.textContent=credit(x)||((x.facts?.length||0)+' known detail'+(x.facts?.length===1?'':'s'));b.append(t,h,p,m);b.onclick=()=>selectEntry(x);cards.append(b)});if(items.length===0&&(state.data?.entry_count||0)>0){const d=document.createElement('div');d.className='blank';const h=document.createElement('h2');h.textContent='Nothing known matches that search.';d.append(h);cards.append(d)}}
function selectEntry(x){state.selected=x.category+':'+x.key;const box=el('article');box.replaceChildren();const tag=document.createElement('div');tag.className='tag';tag.textContent=label(x.category);const h=document.createElement('h2');h.textContent=x.title;const p=document.createElement('p');p.className='summary';p.textContent=x.summary||'';box.append(tag,h,p);if(credit(x)){const c=document.createElement('div');c.className='credit';c.textContent=credit(x);box.append(c)};(x.facts||[]).forEach(f=>{const d=document.createElement('div');d.className='fact';const fh=document.createElement('h4');fh.textContent=f.heading||'Known detail';const fp=document.createElement('p');fp.textContent=f.text;d.append(fh,fp);const fc=credit(f);if(fc){const c=document.createElement('div');c.className='credit';c.textContent=fc;d.append(c)}box.append(d)})}
function renderActivity(){const box=el('activity');box.replaceChildren();(state.data?.activity||[]).slice(0,12).forEach(x=>{const d=document.createElement('div');d.className='event';const s=document.createElement('strong');s.textContent=x.character||'A traveler';d.append(s,document.createTextNode((x.event==='entry'?' added ':' uncovered ')+x.label));box.append(d)});if(!(state.data?.activity||[]).length){const d=document.createElement('div');d.className='event';d.textContent='No additions yet.';box.append(d)}}
function render(){el('entryCount').textContent=state.data?.entry_count||0;el('lastUpdate').textContent=(state.data?.entry_count||0)?'Updates automatically as Astralis is explored.':'Waiting for the first discovery…';renderFilters();renderCards();renderActivity();if(state.selected){const x=(state.data?.entries||[]).find(y=>y.category+':'+y.key===state.selected);if(x)selectEntry(x)}}
async function refresh(){try{const r=await fetch('/api/wiki',{cache:'no-store'});if(!r.ok)return;const data=await r.json();if(!state.data||data.revision!==state.data.revision){state.data=data;render()}}catch(_){}}
el('search').addEventListener('input',e=>{state.query=e.target.value;renderCards()});refresh();setInterval(refresh,4000);
</script>
</body>
</html>"""


class _WikiHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, database):
        self.database = database
        super().__init__(server_address, handler_class)


class _WikiRequestHandler(BaseHTTPRequestHandler):
    server_version = "DreamsWiki/1.0"

    def log_message(self, _format: str, *_args) -> None:
        return

    def _send(self, status: int, body: bytes, content_type: str, *, cors: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/", "/wiki"}:
            self._send(200, WIKI_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/wiki":
            try:
                payload = collective_wiki_snapshot(self.server.database)  # type: ignore[attr-defined]
                body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8", cors=True)
            except Exception as exc:
                body = json.dumps({"error": "wiki unavailable", "detail": str(exc)}).encode("utf-8")
                self._send(500, body, "application/json; charset=utf-8", cors=True)
            return
        if path == "/healthz":
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8", cors=True)
            return
        self._send(404, b"Not found\n", "text/plain; charset=utf-8")


def start_collective_wiki_server(database, *, host: str = "0.0.0.0", port: int = 8080) -> WikiServerHandle:
    ensure_collective_wiki_schema(database)
    server = _WikiHTTPServer((host, int(port)), _WikiRequestHandler, database)
    thread = threading.Thread(target=server.serve_forever, name="collective-wiki", daemon=True)
    thread.start()
    return WikiServerHandle(server=server, thread=thread, host=host, port=int(port))
