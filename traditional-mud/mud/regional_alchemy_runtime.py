"""Live regional alchemy teaching, books, experiments and weather-sensitive yields."""
from __future__ import annotations

import random

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.regional_alchemy as catalog
from mud.astralis_time import ASTRALIS_CLOCK
from mud.room_runtime import WORLD
from mud.world import ROOMS_BY_KEY


FAVORABLE_WEATHER = {
    "goblin": ("rain", "storm", "thunderstorm"),
    "dwarf": ("snow", "storm"),
    "forest": ("rain", "mist"),
    "moon": ("clear",),
    "human": ("rain", "storm"),
    "troll": ("snow", "storm"),
    "undead": ("duststorm", "windy"),
    "spore": ("damp", "mist", "rain"),
    "waymeet": ("rain", "mist"),
}


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").split())


def _current_tradition(session):
    room = (getattr(session, "character", None) and
            session.character.current_room) or ""
    return next((t for t in catalog.TRADITIONS if t.hall == room), None)


def _weather(session) -> str:
    room = ROOMS_BY_KEY.get(getattr(session.character, "current_room", "") or "")
    if room is None:
        return "clear"
    try:
        return str(WORLD.state.weather_for(room.region_key) or "clear").lower()
    except (AttributeError, KeyError):
        return "clear"


def _visitor():
    moment = ASTRALIS_CLOCK.now()
    return catalog.TRADITIONS[(moment.day_number + 2) % len(catalog.TRADITIONS)]


def _visitor_here(session) -> bool:
    moment = ASTRALIS_CLOCK.now()
    return bool(
        session.character and
        session.character.current_room == "waymeet_lantern_market" and
        8 <= moment.hour < 17
    )


def _seller(session):
    return _current_tradition(session) or (
        _visitor() if _visitor_here(session) else None
    )


def _known(session) -> set[str]:
    return set(session.database.list_flags(session.character.id))


def _alchemy_skill(session) -> int:
    return crafting.trade_skill_value(session.database, session.character.id, "alchemy")


async def _show_help(session) -> None:
    await session.send(
        "\r\n=== REGIONAL ALCHEMY ===\r\n"
        "ALCHEMY REGIONS        See the nine teaching traditions.\r\n"
        "STUDY ALCHEMY          Learn the first local lesson from a master.\r\n"
        "ALCHEMY BOOKS          Browse manuals at a trainer or visiting seller.\r\n"
        "BUY ALCHEMY BOOK <name>  Buy a portable manual for Sols.\r\n"
        "READ ALCHEMY BOOK <name> Study your manual; it is reusable and tradeable.\r\n"
        "ALCHEMY PROGRESS       See your learned cultural lessons.\r\n"
        "ALCHEMY VISITOR        Find out when a traveling alchemist is in Waymeet.\r\n"
        "ALCHEMY CONDITIONS     Check local reagent weather.\r\n"
        "EXPERIMENT ALCHEMY     Risk local materials on a hidden discovery.\r\n"
        "EXAMINE <clue>         Investigate workshop objects for rare recipes.\r\n"
        "RECIPES ALCHEMY SEARCH <text> searches learned formula names.\r\n"
        "RECIPE <name> gives ingredients; CRAFT <name> uses your actual skill "
        "and nearby alchemy station.\r\n"
        "True Gold is a permanent Dwarven master transmutation. "
        "Licensed Auric Fixative is expensive, consumed, and sold only "
        "by the Dwarven master with sufficient Alchemy skill.\r\n"
    )


async def _show_regions(session) -> None:
    known = _known(session)
    await session.send("\r\n=== NINE TRADITIONS OF ASTRALIS ===\r\n")
    for t in catalog.TRADITIONS:
        hall = ROOMS_BY_KEY[t.hall]
        learned = sum(catalog.lesson_flag(t.key, b) in known for b in range(5))
        await session.send(
            f"{t.name:<12} {learned}/5 volumes | {hall.name} | "
            f"{t.trainer}\r\n  {t.description}\r\n"
        )
    await session.send(
        "Each tradition has five volumes. First lessons are taught in person; "
        "advanced volumes are portable manuals you can buy or trade.\r\n"
    )


async def _show_progress(session) -> None:
    known = _known(session)
    await session.send(
        f"\r\n=== ALCHEMY JOURNAL ===\r\nSkill: {_alchemy_skill(session)}\r\n"
    )
    for t in catalog.TRADITIONS:
        levels = ", ".join(
            catalog.BANDS[i][0]
            for i in range(5) if catalog.lesson_flag(t.key, i) in known
        ) or "Not studied"
        await session.send(f"{t.name:<12} {levels}\r\n")
    discovered = sum(
        flag in known
        for (room, clue), (tradition, stage) in catalog.SECRET_CLUES.items()
        for flag in (catalog.secret_flag(tradition, stage),)
    )
    await session.send(
        f"Hidden discoveries: {discovered}/30. "
        "Undiscovered formulas are absent from ordinary recipe lists.\r\n"
    )


async def _study(session) -> None:
    t = _current_tradition(session)
    if t is None:
        await session.send(
            "There is no regional alchemy mentor here. ALCHEMY REGIONS "
            "shows the nine teaching halls.\r\n"
        )
        return
    flag = catalog.lesson_flag(t.key, 0)
    if flag in _known(session):
        await session.send(
            f"{t.trainer} reviews your notes. You already know the apprentice "
            f"{t.name} formulas. For further study use ALCHEMY BOOKS here.\r\n"
        )
        return
    session.database.grant_flag(session.character.id, flag)
    await session.send(
        f"{t.trainer} teaches you the first {t.name} tradition. "
        f"{len(t.patterns)} apprentice recipes are now in your recipe book. "
        f"Gather {t.common} and {t.rare} locally; use RECIPE <name> for details.\r\n"
    )


async def _show_books(session) -> None:
    seller = _seller(session)
    known = _known(session)
    if seller is None:
        await session.send(
            "No alchemical manuscript seller is here. Visit one of the "
            "nine regional trainers or look for the Waymeet traveling "
            "alchemist during the daytime. ALCHEMY REGIONS lists the halls.\r\n"
        )
        return
    visiting = _current_tradition(session) is None
    greeting = ("The visiting alchemist has brought" if visiting
                else f"{seller.trainer} offers")
    await session.send(
        f"\r\n=== ALCHEMICAL MANUSCRIPTS ===\r\n"
        f"{greeting} {seller.name} manuals.\r\n"
    )
    for bi, (rank, trivial, tier, _reagent) in enumerate(catalog.BANDS):
        book = crafting.ITEMS_BY_KEY[catalog.book_key(seller.key, bi)]
        flag = catalog.lesson_flag(seller.key, bi)
        price = catalog.BOOK_PRICES[bi]
        skill_floor = max(0, trivial - crafting.MAX_CRAFT_DIFFICULTY_GAP)
        status = (
            "LEARNED" if flag in known
            else "IN PACK" if session.database.item_quantity(session.character.id, book.key)
            else "TRAINER" if bi == 0 and not visiting
            else f"{price} sparks (skill {skill_floor}+)"
        )
        await session.send(f"  {book.name}: {status}\r\n")
    await session.send(
        "Use BUY ALCHEMY BOOK <name> then READ ALCHEMY BOOK <name>. "
        "The apprentice lesson is free from its home trainer.\r\n"
    )


async def _buy_book(session, target: str) -> None:
    seller = _seller(session)
    if seller is None:
        await session.send("No manuscript seller is available here.\r\n")
        return
    wanted = _normalize(target)
    matching = [
        bi for bi in range(1, 5)
        if wanted in {
            _normalize(catalog.BANDS[bi][0]),
            _normalize(crafting.ITEMS_BY_KEY[catalog.book_key(seller.key, bi)].name),
            _normalize(f"{catalog.BANDS[bi][0]} {seller.name}"),
        }
    ]
    if len(matching) != 1:
        await session.send(
            "Name an advanced volume sold here. Use ALCHEMY BOOKS to see titles.\r\n"
        )
        return
    bi = matching[0]
    rank, trivial, tier, reagent = catalog.BANDS[bi]
    book = crafting.ITEMS_BY_KEY[catalog.book_key(seller.key, bi)]
    minimum = max(0, trivial - crafting.MAX_CRAFT_DIFFICULTY_GAP)
    if _alchemy_skill(session) < minimum:
        await session.send(f"This manual requires Alchemy {minimum} before purchase.\r\n")
        return
    checker = getattr(session, "can_receive_item", None)
    if callable(checker) and not checker(book.key, 1):
        await session.send("Your inventory is full; make room for the manual.\r\n")
        return
    price = catalog.BOOK_PRICES[bi]
    if not session.database.spend_sols(session.character.id, price):
        await session.send(f"{book.name} costs {price} sparks. You cannot afford it.\r\n")
        return
    session.database.add_item(session.character.id, book.key, 1)
    await session.send(
        f"Purchased {book.name} for {price} sparks. "
        f"Use READ ALCHEMY BOOK {book.name} to learn the formulas.\r\n"
    )


async def _read_book(session, target: str) -> None:
    wanted = _normalize(target)
    candidates = [
        (t, bi)
        for t in catalog.TRADITIONS for bi in range(5)
        if session.database.item_quantity(
            session.character.id, catalog.book_key(t.key, bi)
        ) > 0
    ]
    exact = [
        (t, bi) for t, bi in candidates
        if wanted in {
            _normalize(crafting.ITEMS_BY_KEY[catalog.book_key(t.key, bi)].name),
            _normalize(f"{catalog.BANDS[bi][0]} {t.name}"),
        }
    ]
    if not exact:
        exact = [
            (t, bi) for t, bi in candidates
            if wanted and wanted in _normalize(
                crafting.ITEMS_BY_KEY[catalog.book_key(t.key, bi)].name
            )
        ]
    if len(exact) != 1:
        await session.send(
            "You need one matching carried manual. Use INVENTORY or "
            "give a more specific book title.\r\n"
        )
        return
    t, bi = exact[0]
    flag = catalog.lesson_flag(t.key, bi)
    if flag in _known(session):
        await session.send("You have already copied these formulas into your journal.\r\n")
        return
    session.database.grant_flag(session.character.id, flag)
    await session.send(
        f"You carefully study the {catalog.BANDS[bi][0]} {t.name} manuscript. "
        f"{len(t.patterns)} permanent recipes are added to your journal. "
        "The book remains in your pack and can be shared.\r\n"
    )


async def _buy_fixative(session) -> None:
    t = _current_tradition(session)
    if t is None or t.key != "dwarf":
        await session.send(
            "Licensed Auric Fixative is sold only at the Dwarven alchemical hall.\r\n"
        )
        return
    if _alchemy_skill(session) < 135:
        await session.send("The assay house only sells fixative to Alchemy 135+.\r\n")
        return
    key = "alch_auric_fixative"
    checker = getattr(session, "can_receive_item", None)
    if callable(checker) and not checker(key, 1):
        await session.send("Your pack cannot fit the sealed fixative bottle.\r\n")
        return
    if not session.database.spend_sols(
        session.character.id, catalog.GOLD_FIXATIVE_PRICE
    ):
        await session.send(
            f"Licensed fixative costs {catalog.GOLD_FIXATIVE_PRICE} sparks. "
            "You need more Sols.\r\n"
        )
        return
    session.database.add_item(session.character.id, key, 1)
    await session.send(
        f"Purchased one Licensed Auric Fixative for "
        f"{catalog.GOLD_FIXATIVE_PRICE} sparks. "
        "One bottle is consumed per true-gold transmutation.\r\n"
    )


async def _secret(session, clue: str) -> bool:
    room = session.character.current_room or ""
    found = catalog.SECRET_CLUES.get((room, clue))
    if found is None:
        return False
    tradition, stage = found
    flag = catalog.secret_flag(tradition, stage)
    if flag in _known(session):
        await session.send(
            "You recognize the hidden formulation already copied into your journal.\r\n"
        )
        return True
    session.database.grant_flag(session.character.id, flag)
    recipe = next(
        r for r in catalog.RECIPES
        if r.discovery_flag == flag
    )
    await session.send(
        f"Careful inspection of the {clue} reveals an overlooked alchemical "
        f"sequence. Secret formula discovered: "
        f"{crafting.ITEMS_BY_KEY[recipe.output_item_key].name}.\r\n"
    )
    await economy._show_recipe_detail(
        session, crafting.ITEMS_BY_KEY[recipe.output_item_key].name
    )
    return True


async def _experiment(session, roll: float | None = None) -> None:
    t = _current_tradition(session)
    if t is None:
        await session.send(
            "Experiments need a cultural trainer's alchemy table. "
            "Visit one of the regional teaching halls.\r\n"
        )
        return
    skill = _alchemy_skill(session)
    known = _known(session)
    possible = [
        stage for stage, requirement in enumerate(catalog.SECRET_SKILLS)
        if skill >= requirement - 30 and
        catalog.secret_flag(t.key, stage) not in known
    ]
    if not possible:
        await session.send(
            "Your skill is not ready for another unknown local experiment. "
            "Inspect the alchemical workshop for clues or return with more practice.\r\n"
        )
        return
    ingredients = (
        (catalog.sample_key(t.key), 1),
        (catalog.sample_key(t.key, True), 1),
        ("spring_water", 1),
    )
    missing = [
        crafting.item_display_name(key) for key, qty in ingredients
        if session.database.item_quantity(session.character.id, key) < qty
    ]
    if missing:
        await session.send(
            "Experimental reagents missing: " + ", ".join(missing) + ".\r\n"
        )
        return
    for key, qty in ingredients:
        if not session.database.consume_item(session.character.id, key, qty):
            await session.send("The experiment was interrupted by missing ingredients.\r\n")
            return
    stage = possible[0]
    if (random.random() if roll is None else roll) >= 0.35:
        await session.send(
            "The mixture reacts and settles, but yields no new discovery. "
            "Your reagents were consumed. A different attempt may succeed.\r\n"
        )
        return
    flag = catalog.secret_flag(t.key, stage)
    session.database.grant_flag(session.character.id, flag)
    recipe = next(r for r in catalog.RECIPES if r.discovery_flag == flag)
    await session.send(
        "A tiny reaction you almost discarded proves to be the missing step. "
        "Secret recipe discovered: "
        f"{crafting.ITEMS_BY_KEY[recipe.output_item_key].name}.\r\n"
    )


async def _show_visitor(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    t = _visitor()
    if _visitor_here(session):
        await session.send(
            f"{t.trainer} has arrived at Waymeet Lantern Market with "
            f"{t.name} alchemy manuals. The stall closes at Astralis 17:00. "
            "Use ALCHEMY BOOKS here.\r\n"
        )
    else:
        await session.send(
            "Traveling alchemists sell rotating regional manuals at Waymeet "
            "Lantern Market from Astralis 08:00 to 17:00. "
            f"Today's visiting tradition is {t.name}.\r\n"
        )


async def _show_conditions(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    weather = _weather(session)
    room = session.character.current_room or ""
    source = next(
        (t for t in catalog.TRADITIONS
         if t.gathering_room == room or t.hall == room), None
    )
    await session.send(
        f"Regional conditions: {weather}. Astralis {moment.hour:02d}:"
        f"{moment.minute:02d}; moon: {moment.moon_phase_name}.\r\n"
    )
    if source is not None:
        good = weather in FAVORABLE_WEATHER[source.key]
        await session.send(
            f"{source.name} rare reagents: "
            + ("favorable weather; careful gathering can yield an extra sample."
               if good else "ordinary yields in current weather.")
            + "\r\n"
        )


async def _delegate(session, prior, command: str) -> None:
    had = "prompt" in session.__dict__
    previous = session.__dict__.get("prompt")

    async def replay(_text: str) -> str:
        return command

    session.prompt = replay
    try:
        await prior(session)
    finally:
        if had:
            session.prompt = previous
        else:
            session.__dict__.pop("prompt", None)


def install_regional_alchemy_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_regional_alchemy_runtime_installed", False):
        return
    catalog.install_regional_alchemy_content()

    # Weather affects the yield of nine optional rare nodes, never blocks core
    # progression or encourages waiting for a storm just to brew a healing potion.
    old_gather = economy._gather

    async def regional_gather(session, target: str, skill_key=None) -> None:
        t = next(
            (t for t in catalog.TRADITIONS
             if getattr(session, "character", None) and
             session.character.current_room == t.gathering_room), None
        )
        before = (
            session.database.item_quantity(session.character.id,
                catalog.sample_key(t.key, True))
            if t is not None else 0
        )
        await old_gather(session, target, skill_key)
        if t is None or _weather(session) not in FAVORABLE_WEATHER[t.key]:
            return
        key = catalog.sample_key(t.key, True)
        after = session.database.item_quantity(session.character.id, key)
        if after <= before:
            return
        checker = getattr(session, "can_receive_item", None)
        if callable(checker) and not checker(key, 1):
            return
        if random.random() < 0.25:
            session.database.add_item(session.character.id, key, 1)
            await session.send(
                f"The {t.name.lower()} weather favors the reaction. "
                f"You recover a second {crafting.item_display_name(key)}.\r\n"
            )

    economy._gather = regional_gather
    prior = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await prior(self)
            return
        current = getattr(self, "current_prompt_text", None)
        prompt = "\r\n" + (str(current()) if callable(current) else "> ")
        command = await self.prompt(prompt)
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = _normalize(command)
        if normalized in {"alchemy help", "regional alchemy"}:
            await _show_help(self)
            return
        if normalized in {"alchemy regions", "alchemy trainers"}:
            await _show_regions(self)
            return
        if normalized in {"study alchemy", "train alchemy"}:
            await _study(self)
            return
        if normalized in {"alchemy progress", "alchemy journal"}:
            await _show_progress(self)
            return
        if normalized in {"alchemy books", "alchemy manuals"}:
            await _show_books(self)
            return
        if normalized.startswith("buy alchemy book "):
            await _buy_book(self, command.strip()[len("buy alchemy book "):])
            return
        if normalized.startswith("read alchemy book "):
            await _read_book(self, command.strip()[len("read alchemy book "):])
            return
        if normalized == "buy auric fixative":
            await _buy_fixative(self)
            return
        if normalized in {"alchemy visitor", "traveling alchemist"}:
            await _show_visitor(self)
            return
        if normalized in {"alchemy conditions", "alchemy weather"}:
            await _show_conditions(self)
            return
        if normalized in {"experiment alchemy", "alchemy experiment"}:
            await _experiment(self)
            return
        if normalized.startswith(("examine ", "look ")):
            clue = normalized.split(" ", 1)[1]
            if await _secret(self, clue):
                return
        await _delegate(self, prior, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._regional_alchemy_runtime_installed = True
