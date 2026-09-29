"""Live Brewing runtime: persistent batches, cellaring, drinking and shared pours."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import random
import re

import mud.brewing as brewing
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_workshops as workshops
import mud.regional_brewing as catalog
from mud.astralis_time import ASTRALIS_CLOCK
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats
from mud.world import ROOMS_BY_KEY


SCHEMA = """
CREATE TABLE IF NOT EXISTS brewing_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    recipe_key TEXT NOT NULL,
    output_item_key TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    yeast_key TEXT,
    water_key TEXT,
    stage TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ferment_ready_at TEXT NOT NULL,
    age_ready_at TEXT,
    aged_output_item_key TEXT,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_brewing_batches_character
    ON brewing_batches(character_id, id);

CREATE TABLE IF NOT EXISTS brewing_rounds (
    room_key TEXT NOT NULL,
    item_key TEXT NOT NULL,
    host_character_id INTEGER NOT NULL,
    host_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    cups INTEGER NOT NULL CHECK (cups >= 0),
    poured_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (room_key, item_key, host_character_id),
    FOREIGN KEY (host_character_id) REFERENCES characters(id) ON DELETE CASCADE
);
"""


BREW_TICK_SECONDS = 5.0


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").split())


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(SCHEMA)


def _local(session):
    room = session.character.current_room or ""
    return next((t for t in catalog.TRADITIONS if t.hall == room), None)


def _skill(session) -> int:
    return int(
        session.database.get_trade_skill_progress(
            session.character.id, "brewing"
        )["skill_xp"]
    )


def _learned(session) -> set[str]:
    return set(session.database.list_flags(session.character.id))


def _publish_secret(session, recipe) -> None:
    from mud.collective_wiki import WikiFact, record_wiki_entry

    room_key = session.character.current_room or ""
    room = ROOMS_BY_KEY.get(room_key)
    record_wiki_entry(
        session.database,
        category="recipe",
        entry_key=recipe.key,
        title=crafting.ITEMS_BY_KEY[recipe.output_item_key].name,
        summary="A hidden regional brewing process recovered through world conditions and experimentation.",
        region_key=room.region_key if room is not None else "",
        room_key=room_key,
        facts=(
            WikiFact(
                "technique",
                "Recovered Brewing Technique",
                recipe.description,
                "brewing_discovery",
            ),
        ),
        character_id=session.character.id,
        character_name=session.character.name,
    )


async def _train(session) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send(
            "A regional brewer must teach you here. Find a working cultural brewhouse, cellar, or tavern brewery.\r\n"
        )
        return

    skill = _skill(session)
    eligible = [
        (i, band)
        for i, band in enumerate(
            __import__(
                "mud.profession_expansion", fromlist=["PROFESSION_BANDS"]
            ).PROFESSION_BANDS
        )
        if band.trivial <= skill
    ]
    if not eligible:
        await session.send(
            "Your Brewing skill is not ready for this house's first lesson.\r\n"
        )
        return

    known = _learned(session)
    learned_now = []
    for i, band in eligible:
        flag = catalog.lesson_flag(tradition.key, i)
        if flag not in known:
            session.database.grant_flag(session.character.id, flag)
            learned_now.append(band.name)

    if not learned_now:
        await session.send(
            f"{tradition.brewer} has no new {tradition.identity} lesson for your current Brewing skill.\r\n"
        )
        return

    await session.send(
        f"{tradition.brewer} walks you through the house culture, water, timing and cellar marks for "
        + ", ".join(learned_now)
        + " recipe band"
        + ("s" if len(learned_now) != 1 else "")
        + ". New house drinks are now visible in RECIPES BREWING.\r\n"
    )


async def _experiment(session, target: str) -> None:
    tradition = _local(session)
    if tradition is None:
        await session.send(
            "There is no regional brewhouse here with a house process to investigate.\r\n"
        )
        return

    wanted = _normalize(target)
    valid = {
        _normalize(tradition.ingredient_key),
        _normalize(tradition.ingredient_name),
        _normalize(tradition.clue),
    }
    if wanted not in valid:
        await session.send(
            f"The useful lead here is {tradition.ingredient_name} and the {tradition.clue}. "
            f"Try BREW EXPERIMENT {tradition.ingredient_name.upper()}.\r\n"
        )
        return
    if (
        session.database.item_quantity(
            session.character.id, tradition.ingredient_key
        )
        < 1
    ):
        await session.send(
            f"You need {tradition.ingredient_name} in your inventory to test the house process.\r\n"
        )
        return

    weather_getter = getattr(session, "current_weather", None)
    weather = str(
        weather_getter() if callable(weather_getter) else "clear"
    ).lower()
    season = ASTRALIS_CLOCK.now().season
    if (
        season != tradition.experiment_season
        or weather not in tradition.experiment_weather
    ):
        await session.send(
            f"You work the {tradition.ingredient_name} through the clue, but the process does not resolve. "
            f"It points toward {tradition.experiment_season} and weather like "
            f"{', '.join(tradition.experiment_weather)}.\r\n"
        )
        return

    session.database.consume_item(
        session.character.id, tradition.ingredient_key, 1
    )
    flag = catalog.secret_flag(tradition.key)
    recipe = catalog.RECIPES_BY_KEY[f"brew_secret_{tradition.key}"]
    if flag not in _learned(session):
        session.database.grant_flag(session.character.id, flag)
        _publish_secret(session, recipe)
        await session.send(
            f"The weather changes how {tradition.ingredient_name} takes the culture. "
            f"The old cellar clue finally makes sense. Secret brew discovered: "
            f"{crafting.item_display_name(recipe.output_item_key)}.\r\n"
        )
    else:
        await session.send(
            "You reproduce the hidden house observation you already discovered.\r\n"
        )
    await economy._show_recipe_detail(
        session, crafting.item_display_name(recipe.output_item_key)
    )


def _parse_brew_target(argument: str) -> tuple[str, str | None, str | None]:
    """Parse optional yeast and water choices without making recipe names rigid."""

    target = " ".join(argument.strip().split())
    yeast_key = None
    water_key = None

    yeast_match = re.search(
        r"\s+with\s+(clean|wild)(?:\s+(?:brewer(?:'s)?\s+)?yeast|\s+culture)?\b",
        target,
        flags=re.IGNORECASE,
    )
    if yeast_match:
        yeast_key = (
            "wild_yeast_culture"
            if yeast_match.group(1).lower() == "wild"
            else "brewers_yeast"
        )
        target = (target[: yeast_match.start()] + target[yeast_match.end() :]).strip()

    water_match = re.search(
        r"\s+using\s+(spring|filtered)(?:\s+(?:brewing\s+)?water)?\b",
        target,
        flags=re.IGNORECASE,
    )
    if water_match:
        water_key = (
            "filtered_brewing_water"
            if water_match.group(1).lower() == "filtered"
            else "spring_water"
        )
        target = (target[: water_match.start()] + target[water_match.end() :]).strip()

    return target, yeast_key, water_key


def _selected_materials(
    recipe: CraftingRecipe,
    process: brewing.BrewProcess,
    *,
    requested_yeast: str | None,
    requested_water: str | None,
) -> tuple[tuple[MaterialRequirement, ...] | None, str | None, str | None, str | None]:
    yeast = requested_yeast or process.default_yeast_key
    water = requested_water or process.default_water_key

    if requested_yeast is not None and not process.can_swap_yeast:
        return None, None, None, "That brew does not use a selectable yeast culture."
    if requested_water is not None and not process.can_swap_water:
        return None, None, None, "That brew does not have a selectable water profile."

    materials = []
    for req in recipe.materials:
        key = req.item_key
        if (
            process.default_yeast_key is not None
            and key == process.default_yeast_key
            and yeast is not None
        ):
            key = yeast
        if (
            process.default_water_key is not None
            and key == process.default_water_key
            and water is not None
        ):
            key = water
        materials.append(MaterialRequirement(key, req.quantity))
    return tuple(materials), yeast, water, None


async def _filter_water(session) -> None:
    if "brewhouse" not in economy._stations_here(session):
        await session.send(
            "You need a Brewhouse / Fermenter to prepare brewing water.\r\n"
        )
        return
    if session.database.item_quantity(session.character.id, "spring_water") < 1:
        await session.send("You need Spring Water to filter.\r\n")
        return
    can_receive = getattr(session, "can_receive_item", None)
    if callable(can_receive) and not can_receive("filtered_brewing_water", 1):
        await session.send(
            "Your inventory has no room for the filtered water.\r\n"
        )
        return
    if not session.database.consume_item(
        session.character.id, "spring_water", 1
    ):
        await session.send("The Spring Water is no longer in your inventory.\r\n")
        return
    session.database.add_item(
        session.character.id, "filtered_brewing_water", 1
    )
    await session.send(
        "You pass Spring Water through the brewhouse filter bed and collect 1x Filtered Brewing Water.\r\n"
    )


async def start_brew(
    session,
    recipe: CraftingRecipe,
    *,
    requested_yeast: str | None = None,
    requested_water: str | None = None,
) -> None:
    """Consume one recipe attempt and, on success, create a persistent batch."""

    if recipe.trade_skill_key != "brewing":
        await session.send("That is not a Brewing recipe.\r\n")
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send(
            "You cannot start a brewing batch while fighting.\r\n"
        )
        return
    if not economy._recipe_visible(session, recipe):
        await session.send("You have not learned that brewing process yet.\r\n")
        return
    if "brewhouse" not in economy._stations_here(session):
        await session.send(
            "This recipe requires a Brewhouse / Fermenter. Use RESOURCES to find a local station.\r\n"
        )
        return

    process = brewing.process_for(recipe.key)
    if process is None:
        await session.send(
            "That Brewing recipe has no fermentation process attached to it.\r\n"
        )
        return

    skill = crafting.trade_skill_value(
        session.database, session.character.id, "brewing"
    )
    if not recipe.can_attempt(
        skill, max_gap=crafting.MAX_CRAFT_DIFFICULTY_GAP
    ):
        await session.send(
            f"{crafting.item_display_name(recipe.output_item_key)} is too difficult to attempt. "
            f"Your Brewing is {skill}; the recipe trivial is {recipe.trivial_skill}.\r\n"
        )
        return

    materials, yeast_key, water_key, selection_error = _selected_materials(
        recipe,
        process,
        requested_yeast=requested_yeast,
        requested_water=requested_water,
    )
    if selection_error:
        await session.send(selection_error + "\r\n")
        return
    assert materials is not None

    missing = [
        (
            req,
            req.quantity
            - session.database.item_quantity(
                session.character.id, req.item_key
            ),
        )
        for req in materials
        if session.database.item_quantity(
            session.character.id, req.item_key
        )
        < req.quantity
    ]
    if missing:
        await session.send(
            "Missing materials: "
            + ", ".join(
                f"{shortfall}x {crafting.item_display_name(req.item_key)}"
                for req, shortfall in missing
            )
            + ".\r\n"
        )
        return

    success_chance = crafting.craft_success_chance(
        skill, recipe.trivial_skill
    )
    skillup_chance = crafting.craft_skillup_chance(
        skill, recipe.trivial_skill
    )
    succeeded = (
        True
        if success_chance >= 1.0
        else random.random() < success_chance
    )
    skill_increased = (
        skillup_chance > 0.0 and random.random() < skillup_chance
    )

    committed = session.database.complete_crafting_transaction(
        session.character.id,
        trade_skill_key="brewing",
        materials=materials,
        output_item_key=recipe.output_item_key,
        output_quantity=recipe.output_quantity,
        skill_xp_gain=1 if skill_increased else 0,
        craft_succeeded=False,
    )
    if not committed:
        await session.send(
            "The required brewing materials were no longer available.\r\n"
        )
        return

    new_skill = skill + int(skill_increased)
    feedback = crafting.crafting_skill_feedback(
        recipe,
        new_skill_value=new_skill,
        skill_increased=skill_increased,
    )
    if not succeeded:
        await session.send(
            "The batch fails during preparation and the ingredients are lost. "
            + feedback
            + "\r\n"
        )
        return

    seconds = brewing.adjusted_seconds(
        process, yeast_key=yeast_key, water_key=water_key
    )
    now = datetime.now(timezone.utc)
    ready = now + timedelta(seconds=seconds)
    _ensure_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            """INSERT INTO brewing_batches(
                   character_id,recipe_key,output_item_key,quantity,yeast_key,water_key,
                   stage,started_at,ferment_ready_at,age_ready_at,aged_output_item_key
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session.character.id,
                recipe.key,
                recipe.output_item_key,
                recipe.output_quantity,
                yeast_key,
                water_key,
                "fermenting",
                now.isoformat(),
                ready.isoformat(),
                None,
                process.aged_output_item_key,
            ),
        )
        batch_id = int(cursor.lastrowid)

    profile = []
    if yeast_key:
        profile.append(
            brewing.YEAST_OPTIONS.get(
                yeast_key, (crafting.item_display_name(yeast_key), 1.0)
            )[0]
        )
    if water_key:
        profile.append(
            brewing.WATER_OPTIONS.get(
                water_key, (crafting.item_display_name(water_key), 1.0)
            )[0]
        )
    detail = f" using {' and '.join(profile)}" if profile else ""
    await session.send(
        f"You start batch #{batch_id}: {crafting.item_display_name(recipe.output_item_key)}{detail}. "
        f"It will finish its first stage in about {seconds} seconds. {feedback}\r\n"
    )


async def _start_from_argument(session, argument: str) -> None:
    target, yeast, water = _parse_brew_target(argument)
    recipe, error = economy._resolve_recipe(target, session)
    if error:
        await session.send(error + "\r\n")
        return
    assert recipe is not None
    if recipe.trade_skill_key != "brewing":
        await session.send(
            f"{economy._recipe_output_name(recipe)} is a {economy._profession_name(recipe.trade_skill_key)} recipe, not Brewing.\r\n"
        )
        return
    await start_brew(
        session,
        recipe,
        requested_yeast=yeast,
        requested_water=water,
    )


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _batch_rows(session):
    _ensure_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """SELECT id,recipe_key,output_item_key,quantity,yeast_key,water_key,
                      stage,started_at,ferment_ready_at,age_ready_at,aged_output_item_key
               FROM brewing_batches
               WHERE character_id=?
               ORDER BY id""",
            (session.character.id,),
        ).fetchall()


def _batch_row(session, batch_id: int):
    _ensure_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            """SELECT id,recipe_key,output_item_key,quantity,yeast_key,water_key,
                      stage,started_at,ferment_ready_at,age_ready_at,aged_output_item_key
               FROM brewing_batches
               WHERE character_id=? AND id=?""",
            (session.character.id, batch_id),
        ).fetchone()


def _remaining_text(ready_at: datetime, now: datetime) -> str:
    seconds = max(0, int((ready_at - now).total_seconds()))
    if seconds <= 0:
        return "ready"
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds}s"


async def _show_batches(session) -> None:
    rows = _batch_rows(session)
    await session.send("\r\n=== BREWING CELLAR ===\r\n")
    if not rows:
        await session.send(
            "You have no active batches. Start one with BREW <drink>.\r\n"
        )
        return

    now = datetime.now(timezone.utc)
    for row in rows:
        name = crafting.item_display_name(str(row["output_item_key"]))
        stage = str(row["stage"])
        if stage == "aging":
            ready = _parse_time(str(row["age_ready_at"]))
            status = (
                "CELLARED - READY TO BOTTLE"
                if ready is not None and now >= ready
                else f"cellaring {_remaining_text(ready, now)}"
            )
        else:
            ready = _parse_time(str(row["ferment_ready_at"]))
            if ready is not None and now >= ready:
                process = brewing.process_for(str(row["recipe_key"]))
                can_age = bool(
                    process is not None
                    and process.age_seconds > 0
                    and row["aged_output_item_key"]
                )
                status = "READY - BOTTLE"
                if can_age:
                    status += " or AGE"
            else:
                status = f"fermenting {_remaining_text(ready, now)}"
        await session.send(
            f"  #{row['id']}  {name}  x{row['quantity']}  - {status}\r\n"
        )
    await session.send(
        "\r\nBOTTLE <id> finishes a ready batch. AGE <id> cellars a suitable ready batch instead.\r\n"
    )


async def _age(session, raw_id: str) -> None:
    try:
        batch_id = int(raw_id.strip().lstrip("#"))
    except ValueError:
        await session.send("Use AGE <batch id>.\r\n")
        return
    row = _batch_row(session, batch_id)
    if row is None:
        await session.send("You do not have a brewing batch by that number.\r\n")
        return
    if str(row["stage"]) == "aging":
        await session.send("That batch is already cellaring.\r\n")
        return

    now = datetime.now(timezone.utc)
    ready = _parse_time(str(row["ferment_ready_at"]))
    if ready is None or now < ready:
        await session.send(
            f"Batch #{batch_id} is still fermenting ({_remaining_text(ready, now)}).\r\n"
        )
        return

    process = brewing.process_for(str(row["recipe_key"]))
    if (
        process is None
        or process.age_seconds <= 0
        or not row["aged_output_item_key"]
    ):
        await session.send(
            "That style is meant to be served fresh rather than cellared.\r\n"
        )
        return

    age_ready = now + timedelta(seconds=process.age_seconds)
    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """UPDATE brewing_batches
               SET stage='aging', age_ready_at=?
               WHERE character_id=? AND id=?""",
            (
                age_ready.isoformat(),
                session.character.id,
                batch_id,
            ),
        )
    await session.send(
        f"You move batch #{batch_id} into the cellar. Its mature bottle will be ready in about {process.age_seconds} seconds.\r\n"
    )


async def _bottle(session, raw_id: str) -> None:
    try:
        batch_id = int(raw_id.strip().lstrip("#"))
    except ValueError:
        await session.send("Use BOTTLE <batch id>.\r\n")
        return
    row = _batch_row(session, batch_id)
    if row is None:
        await session.send("You do not have a brewing batch by that number.\r\n")
        return

    now = datetime.now(timezone.utc)
    stage = str(row["stage"])
    if stage == "aging":
        ready = _parse_time(str(row["age_ready_at"]))
        if ready is None or now < ready:
            await session.send(
                f"Batch #{batch_id} is still cellaring ({_remaining_text(ready, now)}).\r\n"
            )
            return
        output_key = str(
            row["aged_output_item_key"] or row["output_item_key"]
        )
    else:
        ready = _parse_time(str(row["ferment_ready_at"]))
        if ready is None or now < ready:
            await session.send(
                f"Batch #{batch_id} is still fermenting ({_remaining_text(ready, now)}).\r\n"
            )
            return
        output_key = str(row["output_item_key"])

    quantity = int(row["quantity"])
    can_receive = getattr(session, "can_receive_item", None)
    if callable(can_receive) and not can_receive(output_key, quantity):
        await session.send(
            "Your inventory has no room for those bottles. Free a slot or equip a larger bag first.\r\n"
        )
        return

    session.database.add_item(
        session.character.id, output_key, quantity
    )
    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM brewing_batches WHERE character_id=? AND id=?",
            (session.character.id, batch_id),
        )
    await session.send(
        f"You bottle batch #{batch_id}: {quantity}x {crafting.item_display_name(output_key)}.\r\n"
    )


def _brew_items(session) -> list[tuple[crafting.ItemDefinition, int]]:
    rows = []
    for row in session.database.list_items(session.character.id):
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        if (
            item is None
            or item.consumable is None
            or item.consumable.use_mode != "drink"
            or "brew" not in set(item.consumable.effect_tags)
        ):
            continue
        rows.append((item, int(row["quantity"])))
    return rows


def _resolve_brew_item(session, target: str):
    wanted = _normalize(target)
    candidates = []
    for item, _quantity in _brew_items(session):
        names = {_normalize(item.key), _normalize(item.name)}
        quality = (
            2
            if wanted in names
            else 1
            if wanted and any(wanted in name for name in names)
            else 0
        )
        if quality:
            candidates.append((quality, item))
    if not candidates:
        return None, None
    best = max(q for q, _ in candidates)
    unique = {item.key: item for q, item in candidates if q == best}
    if len(unique) != 1:
        return None, "Be more specific: " + ", ".join(
            item.name for item in unique.values()
        ) + "."
    return next(iter(unique.values())), None


def _revert_refreshment(combatant, bonus: CharacterStats) -> None:
    inverse = CharacterStats(
        might=-bonus.might,
        grace=-bonus.grace,
        love=-bonus.love,
        mind=-bonus.mind,
        hp=-bonus.hp,
    )
    combatant.stats = combatant.stats.plus(inverse)
    combatant.max_hp = max(1, combatant.max_hp - max(0, bonus.hp))
    combatant.current_hp = min(
        combatant.current_hp, combatant.max_hp
    )
    mana_bonus = max(0, bonus.mana_bonus)
    combatant.max_mana = max(
        0, combatant.max_mana - mana_bonus
    )
    combatant.current_mana = min(
        combatant.current_mana, combatant.max_mana
    )


def _clear_refreshment(session) -> str | None:
    active = getattr(session, "_active_brew_effect", None)
    if not isinstance(active, dict):
        return None
    task = active.get("task")
    if task is not None and not task.done():
        task.cancel()
    combatant = getattr(session, "combatant", None)
    bonus = active.get("bonus")
    if combatant is not None and isinstance(bonus, CharacterStats):
        _revert_refreshment(combatant, bonus)
    session._active_brew_effect = None
    return str(active.get("item_name") or "your previous drink")


async def _expire_refreshment(
    session,
    item_name: str,
    bonus: CharacterStats,
    seconds: float,
    token: object,
) -> None:
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        return
    active = getattr(session, "_active_brew_effect", None)
    if not isinstance(active, dict) or active.get("token") is not token:
        return
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        session._active_brew_effect = None
        return
    _revert_refreshment(combatant, bonus)
    session._active_brew_effect = None
    await session.send(
        f"\r\nThe lingering refreshment from {item_name} fades.\r\n"
    )
    sender = getattr(session, "send_client_state", None)
    if callable(sender):
        await sender()


async def _apply_brew(
    session,
    item,
    *,
    consume_inventory: bool,
    duration_scale: float = 1.0,
    action: str = "drink",
) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send(
            "You cannot stop for a brewed drink while fighting.\r\n"
        )
        return
    assert item.consumable is not None

    if consume_inventory and not session.database.consume_item(
        session.character.id, item.key, 1
    ):
        await session.send(
            "That drink is no longer in your inventory.\r\n"
        )
        return

    effect = item.consumable
    combatant = getattr(session, "combatant", None)
    healed = 0
    duration = 0.0
    replaced = None
    if combatant is not None:
        bonus = effect.temporary_stat_bonuses
        if (
            effect.duration_ticks > 0
            and bonus != CharacterStats()
        ):
            replaced = _clear_refreshment(session)
            combatant.stats = combatant.stats.plus(bonus)
            combatant.max_hp += max(0, bonus.hp)
            combatant.max_mana += max(0, bonus.mana_bonus)
            duration = max(
                1.0,
                effect.duration_ticks
                * BREW_TICK_SECONDS
                * max(0.1, duration_scale),
            )
            token = object()
            task = asyncio.create_task(
                _expire_refreshment(
                    session, item.name, bonus, duration, token
                )
            )
            session._active_brew_effect = {
                "token": token,
                "item_name": item.name,
                "bonus": bonus,
                "task": task,
            }
            tasks = getattr(session, "_brew_effect_tasks", None)
            if tasks is None:
                tasks = set()
                session._brew_effect_tasks = tasks
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        before = combatant.current_hp
        combatant.current_hp = min(
            combatant.max_hp,
            combatant.current_hp + max(0, effect.heal_hp),
        )
        healed = combatant.current_hp - before

    verb = "taste" if action == "taste" else "drink"
    text = f"You {verb} {item.name}."
    if healed:
        text += f" You recover {healed} HP."
    if replaced:
        text += (
            f" Its refreshment replaces the effect from {replaced}."
        )
    if duration:
        text += (
            f" Its temporary refreshment lasts about {int(duration)} seconds."
        )
    await session.send(text + "\r\n")

    tags = set(effect.effect_tags)
    if "belch" in tags:
        await session.send(
            "The sharp little finish comes back as an unapologetic belch.\r\n"
        )
    sender = getattr(session, "send_client_state", None)
    if callable(sender):
        await sender()


async def _show_brews(session) -> None:
    rows = _brew_items(session)
    await session.send("\r\n=== BREWED DRINKS ===\r\n")
    if not rows:
        await session.send(
            "You are not carrying any bottled brews.\r\n"
        )
        return
    for item, quantity in rows:
        await session.send(
            f"  {quantity}x {item.name} - {item.description}\r\n"
        )
    await session.send(
        "\r\nUse DRINK <brew>, or POUR <brew> to share a tasting round in the current room.\r\n"
    )


def _round_rows(session, room_key: str | None = None):
    _ensure_schema(session.database)
    room = (
        room_key
        if room_key is not None
        else (session.character.current_room or "")
    )
    now = datetime.now(timezone.utc).isoformat()
    with session.database.connect() as db:
        db.execute(
            "DELETE FROM brewing_rounds WHERE expires_at <= ? OR cups <= 0",
            (now,),
        )
        return db.execute(
            """SELECT item_key,host_character_id,host_name,display_name,cups
               FROM brewing_rounds
               WHERE room_key=? AND cups>0
               ORDER BY poured_at""",
            (room,),
        ).fetchall()


async def _pour(session, target: str) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send(
            "You cannot pour a social round while fighting.\r\n"
        )
        return
    item, error = _resolve_brew_item(session, target)
    if error:
        await session.send(error + "\r\n")
        return
    if item is None:
        await session.send(
            "You are not carrying a bottled brew by that name.\r\n"
        )
        return
    if not session.database.consume_item(
        session.character.id, item.key, 1
    ):
        await session.send(
            "That bottle is no longer in your inventory.\r\n"
        )
        return

    tags = set(item.consumable.effect_tags)
    cups = (
        3
        if tags.intersection({"tea", "coffee", "tonic"})
        else 6
        if "regional_secret" in tags
        else 4
    )
    room = session.character.current_room or ""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=2)
    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """INSERT INTO brewing_rounds(
                   room_key,item_key,host_character_id,host_name,
                   display_name,cups,poured_at,expires_at
               ) VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(room_key,item_key,host_character_id) DO UPDATE SET
                   cups=brewing_rounds.cups+excluded.cups,
                   poured_at=excluded.poured_at,
                   expires_at=excluded.expires_at""",
            (
                room,
                item.key,
                session.character.id,
                session.character.name,
                item.name,
                cups,
                now.isoformat(),
                expires.isoformat(),
            ),
        )
    await session.send(
        f"You pour {item.name} as a tasting round with {cups} cups. Anyone here can use BAR and TASTE <drink>.\r\n"
    )


async def _show_bar(session) -> None:
    rows = _round_rows(session)
    await session.send("\r\n=== SHARED TASTING BAR ===\r\n")
    if not rows:
        await session.send(
            "No tasting rounds are currently poured here.\r\n"
        )
        return
    for row in rows:
        await session.send(
            f"  {row['display_name']} - {row['cups']} cups - poured by {row['host_name']}\r\n"
        )
    await session.send(
        "\r\nUse TASTE <drink> to take one cup. A tasting gives the same character of the drink for a shorter time.\r\n"
    )


async def _taste(session, target: str) -> None:
    if getattr(session, "active_enemy", None) is not None:
        await session.send(
            "You cannot stop for a tasting while fighting.\r\n"
        )
        return
    wanted = _normalize(target)
    rows = _round_rows(session)
    candidates = []
    for row in rows:
        item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
        names = {
            _normalize(str(row["display_name"])),
            _normalize(item.name) if item is not None else "",
        }
        quality = (
            2
            if wanted in names
            else 1
            if wanted and any(wanted in name for name in names)
            else 0
        )
        if quality:
            candidates.append((quality, row))
    if not candidates:
        await session.send(
            "No tasting by that name is on the shared bar.\r\n"
        )
        return

    best = max(q for q, _ in candidates)
    matches = [row for q, row in candidates if q == best]
    if len(matches) != 1:
        await session.send(
            "Be more specific about which tasting you mean.\r\n"
        )
        return
    row = matches[0]

    _ensure_schema(session.database)
    with session.database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        fresh = db.execute(
            """SELECT cups FROM brewing_rounds
               WHERE room_key=? AND item_key=? AND host_character_id=?""",
            (
                session.character.current_room or "",
                row["item_key"],
                row["host_character_id"],
            ),
        ).fetchone()
        if fresh is None or int(fresh["cups"]) <= 0:
            await session.send("That tasting has just run out.\r\n")
            return
        db.execute(
            """UPDATE brewing_rounds SET cups=cups-1
               WHERE room_key=? AND item_key=? AND host_character_id=?""",
            (
                session.character.current_room or "",
                row["item_key"],
                row["host_character_id"],
            ),
        )

    item = crafting.ITEMS_BY_KEY.get(str(row["item_key"]))
    if item is None or item.consumable is None:
        await session.send(
            "That tasting can no longer be resolved.\r\n"
        )
        return
    await _apply_brew(
        session,
        item,
        consume_inventory=False,
        duration_scale=0.5,
        action="taste",
    )


async def show_brewing_studies(session) -> None:
    tradition = _local(session)
    if tradition is None:
        return
    learned = _learned(session)
    known_bands = sum(
        catalog.lesson_flag(tradition.key, i) in learned
        for i, _ in enumerate(
            __import__(
                "mud.profession_expansion", fromlist=["PROFESSION_BANDS"]
            ).PROFESSION_BANDS
        )
    )
    await session.send(
        f"\r\nREGIONAL BREWING\r\n"
        f"  House      {tradition.identity}\r\n"
        f"  Brewer     {tradition.brewer}\r\n"
        f"  Produce    {tradition.ingredient_name}\r\n"
        f"  Styles     {tradition.primary_label} / {tradition.secondary_label}\r\n"
        f"  Lessons    {known_bands}/8 recipe bands known at this brewhouse\r\n"
        "  Commands   TRAIN BREWING | BREWBOOK | BREW EXPERIMENT <ingredient> | BATCHES | FILTER WATER\r\n"
    )


async def _brewbook(session) -> None:
    learned = _learned(session)
    await session.send("\r\n=== BREWER'S BOOK ===\r\n")
    found = False
    for tradition in catalog.TRADITIONS:
        lessons = sum(
            catalog.lesson_flag(tradition.key, i) in learned
            for i in range(8)
        )
        secret = catalog.secret_flag(tradition.key) in learned
        if lessons or secret:
            found = True
            await session.send(
                f"  {tradition.identity}: {lessons}/8 bands - "
                f"{tradition.primary_label}, {tradition.secondary_label}"
                + (" | SECRET RESERVE RECOVERED" if secret else "")
                + "\r\n"
            )
    if not found:
        await session.send(
            "  No regional house traditions learned yet.\r\n"
        )
    await session.send(
        "\r\nThe book records only houses you have actually learned. Masters, clues, seasons and experimentation reveal the rest.\r\n"
    )


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


def install_regional_brewing_runtime(player_session_class) -> None:
    if getattr(
        player_session_class, "_regional_brewing_runtime_installed", False
    ):
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

        if normalized == "train brewing":
            await _train(self)
            return
        if normalized == "brewbook":
            await _brewbook(self)
            return
        if normalized.startswith("brew experiment "):
            await _experiment(
                self, stripped.split(maxsplit=2)[2]
            )
            return
        if normalized == "brew experiment":
            await self.send(
                "Use BREW EXPERIMENT <regional ingredient or clue>.\r\n"
            )
            return
        if normalized in {"filter water", "filter brewing water"}:
            await _filter_water(self)
            return
        if normalized in {"batches", "cellar", "brewing batches"}:
            await _show_batches(self)
            return
        if normalized == "age":
            await self.send("Use AGE <batch id>.\r\n")
            return
        if normalized.startswith("age "):
            await _age(self, stripped.split(maxsplit=1)[1])
            return
        if normalized == "bottle":
            await self.send("Use BOTTLE <batch id>.\r\n")
            return
        if normalized.startswith("bottle "):
            await _bottle(self, stripped.split(maxsplit=1)[1])
            return
        if normalized in {"brews", "brewed drinks"}:
            await _show_brews(self)
            return
        if normalized in {"bar", "tastings", "tasting bar"}:
            await _show_bar(self)
            return
        if normalized == "pour":
            await self.send("Use POUR <brew>.\r\n")
            return
        if normalized.startswith("pour "):
            target = stripped.split(maxsplit=1)[1]
            if _normalize(target).startswith("round "):
                target = target.split(maxsplit=1)[1]
            await _pour(self, target)
            return
        if normalized == "taste":
            await self.send("Use TASTE <drink>.\r\n")
            return
        if normalized.startswith("taste "):
            await _taste(self, stripped.split(maxsplit=1)[1])
            return
        if normalized in {"brewing studies", "regional brewing"}:
            await show_brewing_studies(self)
            return

        if normalized in {"brew", "brewing", "brewhouse"}:
            await workshops._show_workshop(self, "brewing")
            return
        if normalized.startswith("brew "):
            await _start_from_argument(
                self, stripped.split(maxsplit=1)[1]
            )
            return

        if normalized == "drink":
            # Keep the existing potion help when there is no explicit target.
            await _delegate(self, previous_playing_prompt, command)
            return
        if normalized.startswith("drink "):
            target = stripped.split(maxsplit=1)[1]
            item, error = _resolve_brew_item(self, target)
            if error:
                await self.send(error + "\r\n")
                return
            if item is not None:
                await _apply_brew(
                    self, item, consume_inventory=True
                )
                return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._regional_brewing_runtime_installed = True
