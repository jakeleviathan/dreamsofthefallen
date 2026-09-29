"""Runtime for regional cooking discovery, masters, communal meals and signatures."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_workshops as workshops
import mud.regional_cooking as catalog
from mud.astralis_time import ASTRALIS_CLOCK
from mud.world import ROOMS_BY_KEY


SCHEMA = """
CREATE TABLE IF NOT EXISTS cooking_shared_tables (
    room_key TEXT NOT NULL,
    item_key TEXT NOT NULL,
    chef_character_id INTEGER NOT NULL,
    chef_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    portions INTEGER NOT NULL CHECK (portions >= 0),
    served_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (room_key, item_key, chef_character_id),
    FOREIGN KEY (chef_character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cooking_signatures (
    character_id INTEGER PRIMARY KEY,
    item_key TEXT NOT NULL,
    signature_name TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
"""


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").split())


def _local(session):
    room = session.character.current_room or ""
    return next((t for t in catalog.TRADITIONS if t.hall == room), None)


def _skill(session) -> int:
    return int(session.database.get_trade_skill_progress(session.character.id, "cooking")["skill_xp"])


def _learned(session) -> set[str]:
    return set(session.database.list_flags(session.character.id))


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(SCHEMA)


def _publish_secret(session, recipe) -> None:
    from mud.collective_wiki import WikiFact, record_wiki_entry
    room_key = session.character.current_room or ""
    room = ROOMS_BY_KEY.get(room_key)
    record_wiki_entry(
        session.database, category="recipe", entry_key=recipe.key,
        title=crafting.ITEMS_BY_KEY[recipe.output_item_key].name,
        summary="A hidden regional cooking technique recovered through world conditions and experimentation.",
        region_key=room.region_key if room is not None else "", room_key=room_key,
        facts=(WikiFact("technique", "Recovered Culinary Technique", recipe.description, "cooking_discovery"),),
        character_id=session.character.id, character_name=session.character.name,
    )


async def _train(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send("A regional cooking master must teach you here. Find a working cultural kitchen or hearth.\r\n")
        return
    skill = _skill(session)
    eligible = [
        (i, band) for i, band in enumerate(__import__("mud.profession_expansion", fromlist=["PROFESSION_BANDS"]).PROFESSION_BANDS)
        if band.trivial <= skill
    ]
    if not eligible:
        await session.send("Your Cooking skill is not ready for this kitchen's first lesson.\r\n")
        return
    known = _learned(session)
    new = []
    for i, band in eligible:
        flag = catalog.lesson_flag(tradition.key, i)
        if flag not in known:
            session.database.grant_flag(session.character.id, flag)
            new.append(band.name)
    if not new:
        await session.send(f"{tradition.chef} has no new {tradition.identity} lesson for your current Cooking skill.\r\n")
        return
    await session.send(
        f"{tradition.chef} teaches you {tradition.technique} through the "
        + ", ".join(new)
        + " recipe band"
        + ("s" if len(new) != 1 else "")
        + ". New regional dishes are now visible in RECIPES COOKING.\r\n"
    )


async def _experiment(session, target: str) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send("There is no regional hearth here with a culinary technique to investigate.\r\n")
        return
    if _normalize(target) not in {_normalize(tradition.ingredient_key), _normalize(tradition.ingredient_name), _normalize(tradition.clue)}:
        await session.send(
            f"The useful lead here is {tradition.ingredient_name} and the {tradition.clue}. "
            f"Try COOK EXPERIMENT {tradition.ingredient_name.upper()}.\r\n")
        return
    if session.database.item_quantity(session.character.id, tradition.ingredient_key) < 1:
        await session.send(f"You need {tradition.ingredient_name} in your inventory to experiment with this method.\r\n")
        return

    weather_getter = getattr(session, "current_weather", None)
    weather = str(weather_getter() if callable(weather_getter) else "clear").lower()
    season = ASTRALIS_CLOCK.now().season
    if season != tradition.experiment_season or weather not in tradition.experiment_weather:
        await session.send(
            f"You try the {tradition.technique} method, but the clue does not resolve. "
            f"It points toward {tradition.experiment_season} and weather like "
            f"{', '.join(tradition.experiment_weather)}.\r\n")
        return

    session.database.consume_item(session.character.id, tradition.ingredient_key, 1)
    flag = catalog.secret_flag(tradition.key)
    recipe = catalog.RECIPES_BY_KEY[f"cook_secret_{tradition.key}"]
    if flag not in _learned(session):
        session.database.grant_flag(session.character.id, flag)
        _publish_secret(session, recipe)
        await session.send(
            f"The weather changes how {tradition.ingredient_name} behaves under {tradition.technique}. "
            f"The old clue finally makes sense. Secret dish discovered: "
            f"{crafting.item_display_name(recipe.output_item_key)}.\r\n")
    else:
        await session.send("You reproduce the hidden method you already discovered and confirm the old clue.\r\n")
    await economy._show_recipe_detail(session, crafting.item_display_name(recipe.output_item_key))


def _food_match(session, target: str):
    wanted = _normalize(target)
    matches = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if item is None or item.consumable is None or item.consumable.use_mode != "eat":
            continue
        names = {_normalize(item.key), _normalize(item.name)}
        quality = 2 if wanted in names else 1 if wanted and any(wanted in n for n in names) else 0
        if quality:
            matches.append((quality, item))
    if not matches:
        return None, "You are not carrying prepared food by that name."
    best = max(q for q, _ in matches)
    unique = {i.key: i for q, i in matches if q == best}
    if len(unique) != 1:
        return None, "Be more specific: " + ", ".join(i.name for i in unique.values()) + "."
    return next(iter(unique.values())), None


def _signature_for(session, item_key: str) -> str | None:
    _ensure_schema(session.database)
    with session.database.connect() as db:
        row = db.execute(
            "SELECT signature_name FROM cooking_signatures WHERE character_id = ? AND item_key = ?",
            (session.character.id, item_key),
        ).fetchone()
    return None if row is None else str(row["signature_name"])


async def _signature(session, argument: str) -> None:
    if _skill(session) < 75:
        await session.send("Signature dishes unlock at Cooking skill 75, after you have enough technique to make a style your own.\r\n")
        return
    if " as " in argument.lower():
        raw_target, raw_name = re.split(r"\s+as\s+", argument, maxsplit=1, flags=re.IGNORECASE)
    else:
        raw_target, raw_name = argument, ""
    item, error = _food_match(session, raw_target)
    if error:
        await session.send(error + "\r\n")
        return
    assert item is not None
    name = " ".join(raw_name.strip().split())
    if not name:
        name = f"{session.character.name}'s {item.name}"
    name = name[:60]
    _ensure_schema(session.database)
    now = datetime.now(timezone.utc).isoformat()
    with session.database.connect() as db:
        db.execute(
            """INSERT INTO cooking_signatures(character_id,item_key,signature_name,updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(character_id) DO UPDATE SET
                 item_key=excluded.item_key, signature_name=excluded.signature_name, updated_at=excluded.updated_at""",
            (session.character.id, item.key, name, now),
        )
    await session.send(f"Your current signature dish is now {name}. When you serve it, the table records your name with it.\r\n")


async def _serve(session, target: str) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot lay out a communal meal while fighting.\r\n")
        return
    item, error = _food_match(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    assert item is not None and item.consumable is not None
    if not session.database.consume_item(session.character.id, item.key, 1):
        await session.send("That food is no longer in your inventory.\r\n")
        return
    tags = set(item.consumable.effect_tags)
    portions = 8 if "feast" in tags else 4 if "meal" in tags else 2
    room = session.character.current_room or ""
    signature = _signature_for(session, item.key)
    display = signature or item.name
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=2)
    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """INSERT INTO cooking_shared_tables(room_key,item_key,chef_character_id,chef_name,display_name,portions,served_at,expires_at)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(room_key,item_key,chef_character_id) DO UPDATE SET
                 display_name=excluded.display_name,
                 portions=cooking_shared_tables.portions+excluded.portions,
                 served_at=excluded.served_at, expires_at=excluded.expires_at""",
            (room, item.key, session.character.id, session.character.name, display, portions,
             now.isoformat(), expires.isoformat()),
        )
    await session.send(
        f"You set out {display} as a communal meal with {portions} portions. "
        "Anyone here can use TABLE and EAT TABLE <dish>.\r\n")


def _table_rows(session, room_key: str | None = None):
    _ensure_schema(session.database)
    room = room_key if room_key is not None else (session.character.current_room or "")
    now = datetime.now(timezone.utc).isoformat()
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM cooking_shared_tables WHERE expires_at <= ? OR portions <= 0",
            (now,),
        )
        return db.execute(
            """SELECT item_key, chef_character_id, chef_name, display_name, portions
               FROM cooking_shared_tables WHERE room_key = ? AND portions > 0
               ORDER BY served_at""",
            (room,),
        ).fetchall()


def room_table_entries(session, room_key: str | None = None) -> list[dict[str, object]]:
    """Stable room-presentation view of live communal food."""
    return [
        {
            "item_key": str(row["item_key"]),
            "name": str(row["display_name"]),
            "chef": str(row["chef_name"]),
            "portions": int(row["portions"]),
        }
        for row in _table_rows(session, room_key)
    ]


async def _show_table(session) -> None:
    rows = _table_rows(session)
    await session.send("\r\n=== COMMUNAL TABLE ===\r\n")
    if not rows:
        await session.send("No prepared dishes are currently laid out here.\r\n")
        return
    for row in rows:
        await session.send(f"  {row['display_name']} - {row['portions']} portions - served by {row['chef_name']}\r\n")
    await session.send("\r\nUse EAT TABLE <dish> to take one portion.\r\n")


async def _eat_table(session, target: str) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot stop for a communal meal while fighting.\r\n")
        return
    wanted = _normalize(target)
    rows = _table_rows(session)
    candidates = []
    for row in rows:
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        names = {_normalize(str(row["display_name"])), _normalize(item.name) if item else ""}
        q = 2 if wanted in names else 1 if wanted and any(wanted in n for n in names) else 0
        if q:
            candidates.append((q, row))
    if not candidates:
        await session.send("No dish by that name is on the communal table.\r\n")
        return
    best = max(q for q, _ in candidates)
    matches = [row for q, row in candidates if q == best]
    if len(matches) != 1:
        await session.send("Be more specific about which table dish you mean.\r\n")
        return
    row = matches[0]
    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        fresh = db.execute(
            """SELECT portions FROM cooking_shared_tables
               WHERE room_key=? AND item_key=? AND chef_character_id=?""",
            (session.character.current_room or "", row["item_key"], row["chef_character_id"])).fetchone()
        if fresh is None or int(fresh["portions"]) <= 0:
            await session.send("That dish has just run out.\r\n")
            return
        db.execute(
            """UPDATE cooking_shared_tables SET portions=portions-1
               WHERE room_key=? AND item_key=? AND chef_character_id=?""",
            (session.character.current_room or "", row["item_key"], row["chef_character_id"]))
    session.database.add_item(session.character.id, str(row["item_key"]), 1)
    await workshops._eat(session, crafting.item_display_name(str(row["item_key"])))


async def show_cooking_studies(session) -> None:
    tradition = _local(session)
    if tradition is None:
        return
    skill = _skill(session)
    learned = _learned(session)
    await session.send(
        f"\r\nREGIONAL COOKING\r\n"
        f"  Tradition  {tradition.identity}\r\n"
        f"  Master     {tradition.chef}\r\n"
        f"  Technique  {tradition.technique}\r\n"
        f"  Ingredient {tradition.ingredient_name}\r\n")
    known_bands = sum(catalog.lesson_flag(tradition.key, i) in learned for i, _ in enumerate(__import__("mud.profession_expansion", fromlist=["PROFESSION_BANDS"]).PROFESSION_BANDS))
    await session.send(f"  Lessons    {known_bands}/8 recipe bands known at this kitchen\r\n")
    await session.send(
        "  Commands   TRAIN COOKING | COOKBOOK | COOK EXPERIMENT <ingredient> | SERVE <food> | TABLE | SIGNATURE <food> [AS name]\r\n")


async def _cookbook(session) -> None:
    learned = _learned(session)
    await session.send("\r\n=== DISCOVERY COOKBOOK ===\r\n")
    for tradition in catalog.TRADITIONS:
        lesson_count = sum(catalog.lesson_flag(tradition.key, i) in learned for i in range(8))
        secret = catalog.secret_flag(tradition.key) in learned
        if lesson_count or secret:
            await session.send(
                f"  {tradition.identity}: {lesson_count}/8 bands, {tradition.technique}"
                + (" | SECRET MASTER DISH RECOVERED" if secret else "")
                + "\r\n")
    await session.send(
        "\r\nThe cookbook only records traditions you have actually learned. "
        "Regional masters, clues, world conditions and experimentation reveal the rest.\r\n")


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")
    async def replay(_text: str):
        return command
    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = old
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


def install_regional_cooking_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_regional_cooking_runtime_installed", False):
        return
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt(_live_prompt(self))
        if command is None:
            await previous_playing_prompt(self)
            return
        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized == "train cooking":
            await _train(self); return
        if normalized == "cookbook":
            await _cookbook(self); return
        if normalized.startswith("cook experiment "):
            await _experiment(self, stripped.split(maxsplit=2)[2]); return
        if normalized == "cook experiment":
            await self.send("Use COOK EXPERIMENT <regional ingredient or clue>.\r\n"); return
        if normalized == "table":
            await _show_table(self); return
        if normalized.startswith("serve "):
            await _serve(self, stripped.split(maxsplit=1)[1]); return
        if normalized.startswith("eat table "):
            await _eat_table(self, stripped.split(maxsplit=2)[2]); return
        if normalized.startswith("signature "):
            await _signature(self, stripped.split(maxsplit=1)[1]); return
        if normalized in {"cooking studies", "regional cooking"}:
            await show_cooking_studies(self); return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._regional_cooking_runtime_installed = True
