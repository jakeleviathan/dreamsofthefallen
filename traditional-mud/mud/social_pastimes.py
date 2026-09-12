from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import mud.living_world as living
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment
from mud.social_experience import _ACTIVE_SESSIONS
from mud.veyra_city import VEYRA_BRASSMARKET_KEY, VEYRA_PUBLIC_HEARTH_KEY
from mud.waymeet_frontier import WAYMEET_COMMONHOUSE_KEY, WAYMEET_LANTERN_MARKET_KEY


SOCIAL_PASTIMES_VERSION = "1.0.0"
SOCIAL_HUBS = frozenset({WAYMEET_COMMONHOUSE_KEY, VEYRA_PUBLIC_HEARTH_KEY})
MARKET_GAME_ROOMS = frozenset({WAYMEET_LANTERN_MARKET_KEY, VEYRA_BRASSMARKET_KEY})
KNIFE_ROOMS = frozenset({WAYMEET_COMMONHOUSE_KEY, VEYRA_BRASSMARKET_KEY})


@dataclass(frozen=True, slots=True)
class PastimeDefinition:
    key: str
    name: str
    description: str
    rooms: frozenset[str]
    command_hint: str


PASTIMES: tuple[PastimeDefinition, ...] = (
    PastimeDefinition("bones", "Three Bones", "Roll three carved bones against a regular at the table. Pairs win bragging rights; triples are rare.", SOCIAL_HUBS, "BONES"),
    PastimeDefinition("arm_wrestle", "Arm Wrestling", "Challenge another player in the same hearth room. Might helps, but the table still has opinions.", SOCIAL_HUBS, "ARM WRESTLE <name>"),
    PastimeDefinition("knife_throw", "Knife Throw", "Three throws at a battered practice target. Grace helps your score; today's best scores are public.", KNIFE_ROOMS, "THROW KNIFE"),
    PastimeDefinition("drinking_game", "Five-Round Mug Game", "A harmless five-round tavern endurance bit with increasingly ridiculous narration and no combat penalty.", SOCIAL_HUBS, "DRINK ROUND"),
    PastimeDefinition("riddle", "Market Riddle", "A small daily riddle chalked near the market scales. Solve it for nothing more important than being right.", MARKET_GAME_ROOMS, "RIDDLE / ANSWER <text>"),
    PastimeDefinition("guess_jar", "Guess Jar", "Guess the number of little river stones in today's jar. Three guesses per Astralis day.", MARKET_GAME_ROOMS, "JAR / GUESS JAR <number>"),
)
PASTIMES_BY_KEY = {pastime.key: pastime for pastime in PASTIMES}


RIDDLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("I have roads but no wagons, rivers but no water, and cities nobody can enter. What am I?", ("map", "a map")),
    ("The more of me you take, the more you leave behind. What am I?", ("steps", "footsteps", "tracks")),
    ("I can fill a hall but take up no room. I vanish when nobody makes me. What am I?", ("sound", "noise", "music")),
    ("I travel every road without boots and arrive before every letter is opened. What am I?", ("news", "rumor", "a rumor")),
    ("I am lighter than a feather, but nobody can hold me for long. What am I?", ("breath", "a breath")),
    ("I have a face and two hands but no arms or legs. What am I?", ("clock", "a clock")),
)


SHOW_SCENES: tuple[tuple[str, str], ...] = (
    (
        "The Prince Who Misplaced Tuesday",
        "A paper-crowned prince keeps demanding that the cast return Tuesday to him. The stagehand playing Time eventually walks on, checks a ledger, and explains that Tuesday was never royal property.",
    ),
    (
        "The Hero and the Very Small Dragon",
        "A heroic knight arrives with an absurdly large shield. The dragon is a puppet the size of a kettle and spends most of the scene objecting to the knight's inaccurate measurements.",
    ),
    (
        "Three Funerals and a Wedding",
        "The same actor keeps changing hats to play increasingly distant relatives of the deceased until the wedding guest list becomes mathematically impossible.",
    ),
    (
        "The Tax Collector of the Moon",
        "A pompous official announces that moonlight now requires a civic permit. Every other actor keeps moving one step into shadow to avoid the fee until the collector is standing alone under the lantern.",
    ),
)


HECKLE_RESPONSES = (
    "The lead actor points into the crowd. 'Excellent note. We will ignore it professionally.'",
    "A stagehand leans out from behind the curtain. 'We tried your version in rehearsal. Two chairs died.'",
    "The actor bows deeply. 'At last, a critic with the courage to perform from a seat.'",
    "The puppet dragon turns toward the crowd and slowly shakes its head at you.",
)


DRINK_LINES = (
    "The first mug is mostly foam and confidence. You remain completely certain the table is level.",
    "Round two arrives with a pickled onion. Someone insists the onion is an official witness.",
    "By round three, the room has not moved, but the table has become suspiciously persuasive.",
    "Round four inspires an argument about whether heroic songs contain enough sitting down.",
    "The fifth mug is replaced halfway through by water. The keeper declares you victorious over your own enthusiasm.",
)


_PENDING_ARM_WRESTLES: dict[int, int] = {}


def _stable_int(seed: str, low: int, high: int) -> int:
    if high < low:
        low, high = high, low
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    span = high - low + 1
    return low + (int.from_bytes(digest[:8], "big") % span)


def _character(session):
    return getattr(session, "character", None)


def _session_for_name(name: str):
    wanted = name.strip().lower()
    for session in tuple(_ACTIVE_SESSIONS):
        character = _character(session)
        if character is not None and str(character.name).lower() == wanted:
            return session
    return None


def _sessions_here(session):
    character = _character(session)
    if character is None:
        return []
    return [
        other
        for other in tuple(_ACTIVE_SESSIONS)
        if _character(other) is not None and _character(other).current_room == character.current_room
    ]


async def _broadcast_room(session, text: str) -> None:
    delivered = False
    for other in _sessions_here(session):
        try:
            await other.send(text)
            delivered = delivered or other is session
        except (ConnectionError, RuntimeError):
            continue
    if not delivered:
        await session.send(text)


def ensure_pastime_schema(database) -> None:
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS leisure_attempts (
                character_id INTEGER NOT NULL,
                astralis_day INTEGER NOT NULL,
                activity_key TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                best_score INTEGER,
                last_result TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (character_id, astralis_day, activity_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leisure_keepsakes (
                character_id INTEGER NOT NULL,
                keepsake_key TEXT NOT NULL,
                keepsake_name TEXT NOT NULL,
                earned_day INTEGER NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (character_id, keepsake_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leisure_seen (
                character_id INTEGER NOT NULL,
                astralis_day INTEGER NOT NULL,
                scene_key TEXT NOT NULL,
                PRIMARY KEY (character_id, astralis_day, scene_key),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            );
            """
        )


def _attempt_row(session, day: int, activity_key: str):
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        return db.execute(
            "SELECT attempts, best_score, last_result FROM leisure_attempts WHERE character_id = ? AND astralis_day = ? AND activity_key = ?",
            (session.character.id, int(day), activity_key),
        ).fetchone()


def _next_attempt(session, day: int, activity_key: str) -> int:
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO leisure_attempts (character_id, astralis_day, activity_key) VALUES (?, ?, ?)",
            (session.character.id, int(day), activity_key),
        )
        db.execute(
            "UPDATE leisure_attempts SET attempts = attempts + 1 WHERE character_id = ? AND astralis_day = ? AND activity_key = ?",
            (session.character.id, int(day), activity_key),
        )
        row = db.execute(
            "SELECT attempts FROM leisure_attempts WHERE character_id = ? AND astralis_day = ? AND activity_key = ?",
            (session.character.id, int(day), activity_key),
        ).fetchone()
    return int(row["attempts"])


def _record_score(session, day: int, activity_key: str, score: int, result: str) -> None:
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO leisure_attempts (character_id, astralis_day, activity_key) VALUES (?, ?, ?)",
            (session.character.id, int(day), activity_key),
        )
        db.execute(
            """
            UPDATE leisure_attempts
            SET best_score = CASE WHEN best_score IS NULL OR ? > best_score THEN ? ELSE best_score END,
                last_result = ?
            WHERE character_id = ? AND astralis_day = ? AND activity_key = ?
            """,
            (int(score), int(score), result, session.character.id, int(day), activity_key),
        )


def _award_keepsake(session, day: int, key: str, name: str, source: str) -> bool:
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO leisure_keepsakes (character_id, keepsake_key, keepsake_name, earned_day, source) VALUES (?, ?, ?, ?, ?)",
            (session.character.id, key, name, int(day), source),
        )
    return bool(cursor.rowcount)


async def _show_keepsakes(session) -> None:
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        rows = db.execute(
            "SELECT keepsake_name, earned_day, source FROM leisure_keepsakes WHERE character_id = ? ORDER BY earned_day, keepsake_name",
            (session.character.id,),
        ).fetchall()
    await session.send("\r\n--- Completely Unimportant Trophies ---\r\n")
    if not rows:
        await session.send("You have not collected any social keepsakes yet. They carry no stats and prove almost nothing.\r\n")
        return
    for row in rows:
        await session.send(f"- {row['keepsake_name']} [Day {row['earned_day']}] — {row['source']}\r\n")


def _available_pastimes(room_key: str) -> tuple[PastimeDefinition, ...]:
    return tuple(pastime for pastime in PASTIMES if room_key in pastime.rooms)


def _show_location(moment: AstralisMoment) -> str | None:
    # Every sixth Astralis day the company performs. It does not carry exclusive
    # rewards; missing the show means only that you missed a show.
    if int(moment.day_number) % 6 != 0:
        return None
    if 10 <= int(moment.hour) < 17:
        return WAYMEET_COMMONHOUSE_KEY
    if 18 <= int(moment.hour) < 24:
        return VEYRA_PUBLIC_HEARTH_KEY
    return None


def _show_title(moment: AstralisMoment) -> tuple[str, str]:
    return SHOW_SCENES[_stable_int(f"crooked-lantern:{moment.day_number}", 0, len(SHOW_SCENES) - 1)]


def _riddle_for_day(day: int):
    return RIDDLES[_stable_int(f"market-riddle:{int(day)}", 0, len(RIDDLES) - 1)]


def _jar_number(day: int) -> int:
    return _stable_int(f"guess-jar:{int(day)}", 23, 87)


async def _show_pastimes(session) -> None:
    character = _character(session)
    if character is None:
        return
    moment = ASTRALIS_CLOCK.now()
    activities = _available_pastimes(character.current_room or "")
    await session.send("\r\n--- Things People Are Doing Here ---\r\n")
    if not activities and _show_location(moment) != character.current_room:
        await session.send("Nothing organized is happening here. The world is under no obligation to entertain you in every room.\r\n")
        return
    for pastime in activities:
        await session.send(f"{pastime.name}: {pastime.description}\r\n  {pastime.command_hint}\r\n")
    if _show_location(moment) == character.current_room:
        title, _scene = _show_title(moment)
        await session.send(f"Crooked Lantern Company: performing {title}. WATCH SHOW, HECKLE, or APPLAUD.\r\n")


async def _play_bones(session) -> None:
    if session.character.current_room not in SOCIAL_HUBS:
        await session.send("Three Bones is played at the Waymeet Commonhouse and Veyra Public Hearth.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    attempt = _next_attempt(session, moment.day_number, "bones")
    rolls = tuple(_stable_int(f"bones:{moment.day_number}:{session.character.id}:{attempt}:{i}", 1, 6) for i in range(3))
    counts = {face: rolls.count(face) for face in set(rolls)}
    triple = any(count == 3 for count in counts.values())
    pair = any(count == 2 for count in counts.values())
    score = 30 if triple else (10 + next(face for face, count in counts.items() if count == 2) if pair else sum(rolls))
    if triple:
        result = "triple"
        text = f"You rattle the cup and spill {rolls[0]}, {rolls[1]}, {rolls[2]}. Three alike. The table erupts as though something important happened."
    elif pair:
        result = "pair"
        text = f"You roll {rolls[0]}, {rolls[1]}, {rolls[2]}. A pair. The regular across from you grudgingly slides over the ceremonial bent spoon."
    else:
        result = "miss"
        text = f"You roll {rolls[0]}, {rolls[1]}, {rolls[2]}. No pair. A nearby regular nods with the solemnity normally reserved for funerals."
    _record_score(session, moment.day_number, "bones", score, result)
    await _broadcast_room(session, f"[Three Bones] {session.character.name}: {text}\r\n")
    if pair or triple:
        if _award_keepsake(session, moment.day_number, "bent_spoon_of_triumph", "Bent Spoon of Triumph", "won a respectable hand of Three Bones"):
            await session.send("You keep the Bent Spoon of Triumph. It has no stats, no value, and a magnificent title.\r\n")
    npc = tuple(_stable_int(f"bones-npc:{moment.day_number}:{attempt}:{i}", 1, 6) for i in range(3))
    await session.send(f"A Commonhouse regular answers with {npc[0]}, {npc[1]}, {npc[2]}, then immediately claims the cup is biased.\r\n")


async def _challenge_arm(session, target_name: str) -> None:
    if session.character.current_room not in SOCIAL_HUBS:
        await session.send("Arm wrestling belongs at a public hearth table.\r\n")
        return
    target = _session_for_name(target_name)
    target_character = _character(target) if target is not None else None
    if target_character is None or target_character.current_room != session.character.current_room:
        await session.send("That character is not here.\r\n")
        return
    if target_character.id == session.character.id:
        await session.send("You cannot meaningfully arm wrestle yourself.\r\n")
        return
    _PENDING_ARM_WRESTLES[int(target_character.id)] = int(session.character.id)
    await session.send(f"You challenge {target_character.name} to an arm wrestle.\r\n")
    await target.send(f"{session.character.name} plants an elbow on the table and challenges you. ARM ACCEPT {session.character.name} or ARM DECLINE.\r\n")


async def _accept_arm(session, inviter_name: str = "") -> None:
    inviter_id = _PENDING_ARM_WRESTLES.get(int(session.character.id))
    if inviter_id is None:
        await session.send("Nobody is waiting on your arm-wrestling answer.\r\n")
        return
    inviter = next((s for s in tuple(_ACTIVE_SESSIONS) if _character(s) is not None and int(_character(s).id) == inviter_id), None)
    inviter_character = _character(inviter) if inviter is not None else None
    if inviter_character is None or inviter_character.current_room != session.character.current_room:
        _PENDING_ARM_WRESTLES.pop(int(session.character.id), None)
        await session.send("That challenge is no longer at this table.\r\n")
        return
    if inviter_name and inviter_character.name.lower() != inviter_name.strip().lower():
        await session.send(f"Your challenge is from {inviter_character.name}.\r\n")
        return
    _PENDING_ARM_WRESTLES.pop(int(session.character.id), None)
    moment = ASTRALIS_CLOCK.now()
    a_attempt = _next_attempt(inviter, moment.day_number, "arm_wrestle")
    b_attempt = _next_attempt(session, moment.day_number, "arm_wrestle")
    a_roll = _stable_int(f"arm:{moment.day_number}:{inviter_character.id}:{a_attempt}", 1, 20) + int(inviter_character.stats.might)
    b_roll = _stable_int(f"arm:{moment.day_number}:{session.character.id}:{b_attempt}", 1, 20) + int(session.character.stats.might)
    if a_roll == b_roll:
        a_roll += _stable_int(f"arm-tie:{moment.day_number}:{inviter_character.id}:{a_attempt}", 0, 5)
        b_roll += _stable_int(f"arm-tie:{moment.day_number}:{session.character.id}:{b_attempt}", 0, 5)
    winner = inviter if a_roll >= b_roll else session
    loser = session if winner is inviter else inviter
    _record_score(inviter, moment.day_number, "arm_wrestle", a_roll, "contest")
    _record_score(session, moment.day_number, "arm_wrestle", b_roll, "contest")
    await _broadcast_room(session, f"[Arm Wrestling] {inviter_character.name} and {session.character.name} lock hands. The table creaks. {winner.character.name} finally drives the other hand down while somebody loudly claims the table favored that side.\r\n")
    if _award_keepsake(winner, moment.day_number, "bent_copper_thumb", "Bent Copper Thumb", "won an arm-wrestling table match"):
        await winner.send("Someone awards you a Bent Copper Thumb on a string. It confers no authority whatsoever.\r\n")
    await loser.send("You lose with dignity, which the spectators immediately undermine by reenacting it.\r\n")


async def _decline_arm(session) -> None:
    inviter_id = _PENDING_ARM_WRESTLES.pop(int(session.character.id), None)
    if inviter_id is None:
        await session.send("Nobody is waiting on your answer.\r\n")
        return
    inviter = next((s for s in tuple(_ACTIVE_SESSIONS) if _character(s) is not None and int(_character(s).id) == inviter_id), None)
    await session.send("You decline the arm-wrestling challenge.\r\n")
    if inviter is not None:
        await inviter.send(f"{session.character.name} declines your arm-wrestling challenge.\r\n")


async def _throw_knives(session) -> None:
    if session.character.current_room not in KNIFE_ROOMS:
        await session.send("The practice knife targets are at Waymeet Commonhouse and Veyra Brassmarket.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    attempt = _next_attempt(session, moment.day_number, "knife_throw")
    grace = int(session.character.stats.grace)
    throws = []
    for index in range(3):
        raw = _stable_int(f"knife:{moment.day_number}:{session.character.id}:{attempt}:{index}", 1, 20) + grace
        throws.append(max(1, min(10, raw // 3)))
    total = sum(throws)
    _record_score(session, moment.day_number, "knife_throw", total, ",".join(str(value) for value in throws))
    await _broadcast_room(session, f"[Knife Throw] {session.character.name} scores {throws[0]} + {throws[1]} + {throws[2]} = {total}/30 on the battered target.\r\n")
    if total >= 28 and _award_keepsake(session, moment.day_number, "crooked_tin_medal", "Crooked Tin Medal", "scored at least 28 on the knife target"):
        await session.send("The scorekeeper pins a Crooked Tin Medal to you, then admits it was already crooked.\r\n")


async def _drink_round(session) -> None:
    if session.character.current_room not in SOCIAL_HUBS:
        await session.send("The five-round mug game is played at the public hearths.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    row = _attempt_row(session, moment.day_number, "drinking_game")
    already = int(row["attempts"]) if row is not None else 0
    if already >= len(DRINK_LINES):
        await session.send("The keeper has ended your run for today and replaced the next mug with water. You have proven enough.\r\n")
        return
    round_number = _next_attempt(session, moment.day_number, "drinking_game")
    line = DRINK_LINES[round_number - 1]
    _record_score(session, moment.day_number, "drinking_game", round_number, f"round {round_number}")
    await _broadcast_room(session, f"[Mug Game] {session.character.name}: {line}\r\n")
    if round_number == len(DRINK_LINES):
        if _award_keepsake(session, moment.day_number, "pickled_onion_crown", "Pickled Onion Crown", "finished all five rounds of the mug game"):
            await session.send("The official witness-onion is placed briefly on a little wooden crown and presented to you. Nobody explains the tradition.\r\n")


async def _show_riddle(session) -> None:
    if session.character.current_room not in MARKET_GAME_ROOMS:
        await session.send("The chalk riddle boards are at Lantern Market and Veyra Brassmarket.\r\n")
        return
    question, _answers = _riddle_for_day(ASTRALIS_CLOCK.now().day_number)
    await session.send(f"Today's chalk riddle:\r\n  {question}\r\nANSWER <your guess>\r\n")


async def _answer_riddle(session, answer: str) -> None:
    if session.character.current_room not in MARKET_GAME_ROOMS:
        await session.send("There is no riddle board here.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    row = _attempt_row(session, moment.day_number, "riddle")
    if row is not None and str(row["last_result"]) == "solved":
        await session.send("You already solved today's riddle. Leave somebody else the satisfaction.\r\n")
        return
    attempt = _next_attempt(session, moment.day_number, "riddle")
    question, answers = _riddle_for_day(moment.day_number)
    cleaned = " ".join(re.sub(r"[^a-z0-9 ]", "", answer.lower()).split())
    if cleaned in answers:
        _record_score(session, moment.day_number, "riddle", max(1, 10 - attempt), "solved")
        await session.send("The market keeper taps the chalkboard twice. Correct. A nearby merchant looks annoyed that you got there first.\r\n")
        if _award_keepsake(session, moment.day_number, "riddle_wax_seal", "Riddle-Solver's Wax Seal", "solved a market riddle"):
            await session.send("You are handed a tiny cracked wax seal stamped CORRECT, as if this were an office.\r\n")
    else:
        _record_score(session, moment.day_number, "riddle", 0, "wrong")
        await session.send("The chalk keeper shakes their head. Not today's answer.\r\n")


async def _show_jar(session) -> None:
    if session.character.current_room not in MARKET_GAME_ROOMS:
        await session.send("The guess jars are at Lantern Market and Veyra Brassmarket.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    row = _attempt_row(session, moment.day_number, "guess_jar")
    used = int(row["attempts"]) if row is not None else 0
    await session.send(f"A cloudy glass jar holds somewhere between 23 and 87 little river stones. You have {max(0, 3-used)} guess(es) left today. GUESS JAR <number>\r\n")


async def _guess_jar(session, text: str) -> None:
    if session.character.current_room not in MARKET_GAME_ROOMS:
        await session.send("There is no guess jar here.\r\n")
        return
    try:
        guess = int(text.strip())
    except ValueError:
        await session.send("Guess a whole number.\r\n")
        return
    moment = ASTRALIS_CLOCK.now()
    row = _attempt_row(session, moment.day_number, "guess_jar")
    used = int(row["attempts"]) if row is not None else 0
    if used >= 3 or (row is not None and str(row["last_result"]) == "exact"):
        await session.send("Your guessing for today's jar is finished.\r\n")
        return
    _next_attempt(session, moment.day_number, "guess_jar")
    answer = _jar_number(moment.day_number)
    if guess == answer:
        _record_score(session, moment.day_number, "guess_jar", 100, "exact")
        await _broadcast_room(session, f"[Guess Jar] {session.character.name} says {guess}. The keeper counts twice. Exactly right. This causes far more celebration than it deserves.\r\n")
        if _award_keepsake(session, moment.day_number, "jar_prophets_blue_bead", "Jar Prophet's Blue Bead", "guessed a market jar exactly"):
            await session.send("The keeper gives you one blue glass bead from a completely different jar. Apparently this is the prize.\r\n")
    elif guess < answer:
        _record_score(session, moment.day_number, "guess_jar", max(0, 50 - (answer - guess)), "low")
        await session.send("Too low. The stones remain smugly numerous.\r\n")
    else:
        _record_score(session, moment.day_number, "guess_jar", max(0, 50 - (guess - answer)), "high")
        await session.send("Too high. The jar looks smaller now that somebody has said it aloud.\r\n")


async def _show_scores(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        rows = db.execute(
            """
            SELECT c.name, a.best_score
            FROM leisure_attempts a
            JOIN characters c ON c.id = a.character_id
            WHERE a.astralis_day = ? AND a.activity_key = 'knife_throw' AND a.best_score IS NOT NULL
            ORDER BY a.best_score DESC, c.name COLLATE NOCASE
            LIMIT 5
            """,
            (moment.day_number,),
        ).fetchall()
    await session.send("\r\n--- Today's Knife-Throw Board ---\r\n")
    if not rows:
        await session.send("No scores yet today. A very confident chalk number 30 waits at the top.\r\n")
        return
    for index, row in enumerate(rows, start=1):
        await session.send(f"{index}. {row['name']} — {row['best_score']}/30\r\n")


async def _watch_show(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    if _show_location(moment) != session.character.current_room:
        await session.send("The Crooked Lantern Company is not performing here right now.\r\n")
        return
    title, scene = _show_title(moment)
    await session.send(f"\r\n--- Crooked Lantern Company: {title} ---\r\n{scene}\r\n")
    _next_attempt(session, moment.day_number, "stage_show")
    _record_score(session, moment.day_number, "stage_show", 1, title)
    if _award_keepsake(session, moment.day_number, "crooked_lantern_playbill", "Folded Crooked Lantern Playbill", f"watched {title}"):
        await session.send("A stagehand hands you a badly folded playbill. One actor's name has been corrected three times in ink.\r\n")


async def _heckle(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    if _show_location(moment) != session.character.current_room:
        await session.send("There is currently nobody here paid to tolerate heckling.\r\n")
        return
    attempt = _next_attempt(session, moment.day_number, "heckle")
    response = HECKLE_RESPONSES[_stable_int(f"heckle:{moment.day_number}:{session.character.id}:{attempt}", 0, len(HECKLE_RESPONSES)-1)]
    await _broadcast_room(session, f"[Stage] {session.character.name} heckles the Crooked Lantern Company. {response}\r\n")


async def _applaud(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    if _show_location(moment) != session.character.current_room:
        await session.send("You applaud. The room accepts this without context.\r\n")
        return
    await _broadcast_room(session, f"[Stage] {session.character.name} applauds. The company bows with wildly inconsistent seriousness.\r\n")


def _mark_seen(session, day: int, key: str) -> bool:
    ensure_pastime_schema(session.database)
    with session.database.connect() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO leisure_seen (character_id, astralis_day, scene_key) VALUES (?, ?, ?)",
            (session.character.id, int(day), key),
        )
    return bool(cursor.rowcount)


async def _arrival_nudge(session) -> None:
    character = _character(session)
    if character is None:
        return
    moment = ASTRALIS_CLOCK.now()
    if _show_location(moment) == character.current_room and _mark_seen(session, moment.day_number, "crooked-lantern-arrival"):
        title, _scene = _show_title(moment)
        await session.send(f"\r\n[At the hearth] The Crooked Lantern Company is setting up {title}. WATCH SHOW if you feel like staying.\r\n")


async def _push_gmcp(session) -> None:
    telnet = getattr(session, "telnet", None)
    character = _character(session)
    if telnet is None or character is None or not getattr(telnet, "gmcp_enabled", False):
        return
    moment = ASTRALIS_CLOCK.now()
    activities = _available_pastimes(character.current_room or "")
    await telnet.send_gmcp(
        "Dreams.Pastimes",
        {
            "available": [{"key": p.key, "name": p.name, "command": p.command_hint} for p in activities],
            "show_here": _show_location(moment) == character.current_room,
            "show_title": _show_title(moment)[0] if _show_location(moment) == character.current_room else None,
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


def install_social_pastimes_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_social_pastimes_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if _character(self) is not None:
                ensure_pastime_schema(self.database)
                await _push_gmcp(self)

        player_session_class.enter_character = enter_character

    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if previous_show_current_room is not None:
        async def show_current_room(self) -> None:
            await previous_show_current_room(self)
            if _character(self) is None or living._is_private_room(self):
                return
            await _arrival_nudge(self)
            await _push_gmcp(self)

        player_session_class.show_current_room = show_current_room

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if _character(self) is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"pastimes", "games", "fun", "activities"}:
            await _show_pastimes(self)
            return
        if normalized in {"keepsakes", "trophies", "brag"}:
            await _show_keepsakes(self)
            return
        if normalized in {"bones", "roll bones", "three bones"}:
            await _play_bones(self)
            return
        if normalized.startswith("arm wrestle "):
            await _challenge_arm(self, stripped[len("arm wrestle "):])
            return
        if normalized.startswith("arm accept"):
            target = stripped[len("arm accept"):].strip()
            await _accept_arm(self, target)
            return
        if normalized in {"arm decline", "decline arm"}:
            await _decline_arm(self)
            return
        if normalized in {"throw knife", "knife throw", "throw knives", "knife throwing"}:
            await _throw_knives(self)
            return
        if normalized in {"scores", "knife scores", "leaderboard"}:
            await _show_scores(self)
            return
        if normalized in {"drink round", "drinking game", "mug game", "drink game"}:
            await _drink_round(self)
            return
        if normalized in {"riddle", "market riddle"}:
            await _show_riddle(self)
            return
        if normalized.startswith("answer "):
            await _answer_riddle(self, stripped[len("answer "):])
            return
        if normalized in {"jar", "guess jar", "guessing jar"}:
            await _show_jar(self)
            return
        if normalized.startswith("guess jar "):
            await _guess_jar(self, stripped[len("guess jar "):])
            return
        if normalized in {"show", "stage", "stage show"}:
            moment = ASTRALIS_CLOCK.now()
            if _show_location(moment) == self.character.current_room:
                title, _scene = _show_title(moment)
                await self.send(f"The Crooked Lantern Company is performing {title}. WATCH SHOW, HECKLE, or APPLAUD.\r\n")
            else:
                await self.send("No traveling company is performing here right now.\r\n")
            return
        if normalized in {"watch show", "watch stage", "watch play"}:
            await _watch_show(self)
            return
        if normalized in {"heckle", "heckle stage", "heckle show"}:
            await _heckle(self)
            return
        if normalized in {"applaud", "clap"}:
            await _applaud(self)
            return

        await _delegate_command(self, previous_playing_prompt, command)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed
        await _push_gmcp(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._social_pastimes_runtime_installed = True
