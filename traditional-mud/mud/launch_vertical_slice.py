from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.social_experience as social
import mud.waymeet_frontier as waymeet
from mud.crafting import ItemDefinition
from mud.gloamworks_dungeon import GLOAMWORKS_COMPLETE_FLAG
from mud.greywake_march import GREYWAKE_CHAIN_COMPLETE_FLAG
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE
from mud.stats import CharacterStats, EquipmentItem
from mud.veyra_city import (
    VEYRA_GATE_WARD_KEY,
    VEYRA_GRAND_CROSSING_KEY,
    VEYRA_PUBLIC_HEARTH_KEY,
    VEYRA_RESIDENT_FLAG,
)
from mud.waymeet_frontier import (
    CULVERT_LURKER_KEY,
    GLOAM_DELVER_KEY,
    REEDMAW_BOAR_KEY,
    SLATEBACK_SKULK_KEY,
    THORNBACK_JACKAL_KEY,
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_INTRO_COMPLETE_FLAG,
)


LAUNCH_VERTICAL_SLICE_VERSION = "1.0.0"

# This pass deliberately does not replace the eight authored openings. Their
# quests are already the strongest part of the first hour. Instead it gives each
# opening a short, race-specific closing beat and makes the transition into the
# shared game legible without turning Astralis into a checklist.
OPENING_EPILOGUES: dict[str, tuple[str, str]] = {
    "human": (
        "Blackwall keeps moving around you: another wagon is waved through, another signal is answered, another ordinary problem becomes somebody's work.",
        "You did not learn what Humans are from a speech. You learned what they do when a wall, a road, and a stranger all need attention at once.",
    ),
    "forest_elf": (
        "When you return, the forest has not become safer or more sinister. It has become more specific: a silence can be a warning, a track can be a sentence, and care begins by noticing.",
        "The Old River Path is still there behind you. The difference is that now you know how to read some of what it says.",
    ),
    "moon_elf": (
        "The Third Chair is already being used by someone else. Your answer did not end the disagreement; it became one more recorded view inside it.",
        "High Horizon has taught you its most ordinary habit: certainty is allowed, but it has to survive another angle.",
    ),
    "dwarf": (
        "The lift runs, the pressure mark is signed, and somebody has already put a new work order over the one you finished.",
        "Your first obligation was not heroic. That is why it mattered: a Dwarven city works because thousands of small jobs are done as if other lives depend on them.",
    ),
    "goblin": (
        "Your mark remains on something that used to be somebody else's junk. Around Rattlefen, that is as close to a declaration of adulthood as most people need.",
        "You learned the Goblin rule nobody bothers carving in stone: value is what survives use, argument, ownership, and one more clever idea.",
    ),
    "troll": (
        "The fire settles into coals. Nobody praises you for surviving the cold; they simply make room near the heat because you proved you knew how to get there.",
        "Frostroot's lesson is plain: toughness is not ignoring danger. Toughness is understanding it early enough to still be standing afterward.",
    ),
    "undead": (
        "Nothing answers from the severed command link. The silence remains exactly what it was before: silence.",
        "For the first time, that absence belongs to you. Whatever you become next will not be because an old voice ordered it.",
    ),
    "sporekin": (
        "The Chorus is still present, immense and familiar, but your last choice remains distinctly yours inside it.",
        "You have learned the difference between sharing a memory and surrendering a self. The paths above now belong to both the Chorus and the person walking them.",
    ),
}


# The first shared zone should be brisk. These are intentionally modest HP-only
# changes: the danger curve, damage, armor, rewards, and encounter identities all
# remain intact, while the first run through Waymeet spends less time watching
# low-level auto-attacks grind through health bars.
WAYMEET_PACING_HP: dict[str, int] = {
    THORNBACK_JACKAL_KEY: 24,
    REEDMAW_BOAR_KEY: 34,
    SLATEBACK_SKULK_KEY: 48,
    CULVERT_LURKER_KEY: 54,
    GLOAM_DELVER_KEY: 66,
}


BRIAR_EYE_CHARM = ItemDefinition(
    key="launch_briar_eye_charm",
    name="Briar-Eye Charm",
    description=(
        "A little amber-brown knot found in the thorn-matted ridge of a Thornback Jackal. "
        "Waymeet hunters argue whether it is resin, old glass, or simply a very lucky burr."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Briar-Eye Charm",
        "accessory",
        stat_bonuses=CharacterStats(grace=1),
    ),
    tier=1,
)
REEDMAW_TUSK_TOGGLE = ItemDefinition(
    key="launch_reedmaw_tusk_toggle",
    name="Reedmaw Tusk Toggle",
    description=(
        "A thumb-sized section of river-polished tusk, already grooved where reeds rubbed against it for years. "
        "Travelers wear them as tough little toggles and trade stories about the boars that supplied them."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Reedmaw Tusk Toggle",
        "accessory",
        stat_bonuses=CharacterStats(hp=1),
    ),
    tier=1,
)
SLATEBACK_MIRROR_PLATE = ItemDefinition(
    key="launch_slateback_mirror_plate",
    name="Slateback Mirror Plate",
    description=(
        "One unusually smooth plate from a Slateback Skulk. Its stone-gray face takes a dim reflection "
        "when polished and is often drilled into a small protective token."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Slateback Mirror Plate",
        "accessory",
        armor_class=1,
    ),
    tier=1,
)
CULVERT_MOON_PEARL = ItemDefinition(
    key="launch_culvert_moon_pearl",
    name="Culvert Moon-Pearl",
    description=(
        "A pale mineral bead taken from the calcified growths around a Culvert Lurker's gill ridge. "
        "In low light it seems to keep a little more brightness than it should."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Culvert Moon-Pearl",
        "accessory",
        stat_bonuses=CharacterStats(love=1),
    ),
    tier=1,
)
VIOLET_DELVER_COIL = ItemDefinition(
    key="launch_violet_delver_coil",
    name="Violet Delver Coil",
    description=(
        "A tiny coil made from one rigid whisker of a Gloam-Touched Delver. The violet-black crust along it "
        "does not flake away, even when the whisker is bent into a ring."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Violet Delver Coil",
        "accessory",
        stat_bonuses=CharacterStats(mind=1),
    ),
    tier=1,
)

NOTABLE_FIND_BY_ENEMY: dict[str, ItemDefinition] = {
    THORNBACK_JACKAL_KEY: BRIAR_EYE_CHARM,
    REEDMAW_BOAR_KEY: REEDMAW_TUSK_TOGGLE,
    SLATEBACK_SKULK_KEY: SLATEBACK_MIRROR_PLATE,
    CULVERT_LURKER_KEY: CULVERT_MOON_PEARL,
    GLOAM_DELVER_KEY: VIOLET_DELVER_COIL,
}
NOTABLE_FIND_ITEMS = tuple(NOTABLE_FIND_BY_ENEMY.values())


VEYRA_GATE_MEMORY_FLAG = "launch_veyra_gate_arrival_seen"
VEYRA_CROSSING_MEMORY_FLAG = "launch_veyra_crossing_arrival_seen"

VEYRA_GATE_ARRIVAL = (
    "Veyra does not arrive like a capital in a story. It arrives as traffic. A Dwarf freight cart waits behind a Troll drover; "
    "a Goblin axle crew is already under somebody else's wagon; a Moon Elf clerk is arguing measurements with a Human teamster. "
    "Registrar Mira Noll glances at you only long enough to decide which line you are blocking."
)
VEYRA_CROSSING_ARRIVAL = (
    "Halfway across Grand Crossing, the scale of the city finally lands. The bridge beneath you contains repairs from several peoples: "
    "Dwarven load marks, Goblin plate patches, Forest Elf riverwood, Human hornwork, Sporekin binding fiber. An Undead porter passes a priest; "
    "a Troll child points at a Moon Elf courier; nobody stops to explain the combination. For the first time, your homeland feels like one place in a larger world."
)


SOCIAL_HUBS: dict[str, str] = {
    WAYMEET_COMMONHOUSE_KEY: "Waymeet Commonhouse Yard",
    VEYRA_PUBLIC_HEARTH_KEY: "Veyra Public Hearth",
}

EMOTE_VERBS: dict[str, tuple[str, str]] = {
    "wave": ("raises a hand in greeting.", "waves to {target}."),
    "nod": ("nods.", "nods to {target}."),
    "smile": ("smiles.", "smiles at {target}."),
    "laugh": ("laughs.", "laughs with {target}."),
    "bow": ("gives a small bow.", "bows to {target}."),
    "shrug": ("shrugs.", "shrugs at {target}."),
    "cheer": ("cheers.", "cheers for {target}."),
}


def install_launch_vertical_slice_content() -> None:
    known = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in NOTABLE_FIND_ITEMS if item.key not in known)
    if not additions:
        return
    crafting.ITEMS = crafting.ITEMS + additions
    crafting.ITEMS_BY_KEY.update({item.key: item for item in additions})


def apply_first_hours_combat_tuning() -> None:
    """Apply a conservative time-to-kill polish pass to Waymeet enemies."""
    replacements: dict[str, combat.EnemyDefinition] = {}
    for enemy_key, max_hp in WAYMEET_PACING_HP.items():
        definition = combat.ENEMIES_BY_KEY.get(enemy_key)
        if definition is None:
            continue
        if definition.max_hp == max_hp:
            replacements[enemy_key] = definition
            continue
        replacements[enemy_key] = replace(definition, max_hp=max_hp)
        combat.ENEMIES_BY_KEY[enemy_key] = replacements[enemy_key]

    if not replacements:
        return
    combat.ENEMIES = tuple(replacements.get(enemy.key, enemy) for enemy in combat.ENEMIES)
    waymeet.WAYMEET_ENEMIES = tuple(replacements.get(enemy.key, enemy) for enemy in waymeet.WAYMEET_ENEMIES)


def _notable_flag(enemy_key: str) -> str:
    return f"launch_notable_find_{enemy_key}"


async def _award_first_notable_find(session, enemy_key: str) -> bool:
    character = getattr(session, "character", None)
    item = NOTABLE_FIND_BY_ENEMY.get(enemy_key)
    if character is None or item is None:
        return False
    flag = _notable_flag(enemy_key)
    flags = session.database.list_flags(character.id)
    if flag in flags:
        return False
    session.database.grant_flag(character.id, flag)
    session.database.add_item(character.id, item.key, 1)
    await session.send(
        f"\r\nNOTABLE FIND: {item.name}\r\n"
        f"{item.description}\r\n"
        "This first-specimen trophy is yours only once. It fits the accessory slot and can be traded to another player.\r\n"
    )
    return True


def journey_stage_for(*, race_key: str, level: int, flags: frozenset[str] | set[str]) -> tuple[str, str]:
    loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
    if loop is None:
        return "Find your footing", "Explore your current home and use QUESTS to see the story already in motion."
    if loop.completion_flag not in flags:
        return loop.hook_name, loop.hook_summary
    if level < 2:
        return (
            "The road beyond home",
            "Your first local story is complete. Stay in your homeland long enough to reach level 2, gather what looks useful, and learn what your class can do; the shared roads open from there.",
        )
    if WAYMEET_INTRO_COMPLETE_FLAG not in flags:
        return (
            "Where the Roads Meet",
            "Your homeland road now leads toward Waymeet. This is the first place where the eight origins begin sharing one problem, one market, and eventually one dungeon entrance.",
        )
    if level < 4:
        return (
            "Waymeet before the sealed door",
            "The road problem has a name now: the Gloamworks. Hunt, trade, gather, craft, and meet other travelers around Waymeet until level 4 makes the first shared descent practical.",
        )
    if GLOAMWORKS_COMPLETE_FLAG not in flags:
        return (
            "Below the Sealed Door",
            "The Gloamworks are the first place Astralis asks you to coordinate rather than merely coexist. The descent begins at Gloam Mouth and eventually requires another actual player.",
        )
    if GREYWAKE_CHAIN_COMPLETE_FLAG not in flags:
        return (
            "The Greywake road",
            "What came out of the Gloamworks points east. Greywake turns one dungeon discovery into a regional argument about roads, risk, trade, and public safety—and lets you choose whose approach you support.",
        )
    if VEYRA_RESIDENT_FLAG not in flags:
        return (
            "The city at the end of the road",
            "Greywake ends at Veyra. At level 8, pass the outer gate and learn the city by using it: cross the bridge, visit its market and vault, meet trainers, read the public board, then report to the civic steps.",
        )
    return (
        "A place in the wider world",
        "You have reached Veyra and completed the launch journey from private homeland to shared city. From here, dungeons, factions, crafting, player trade, class commissions, Sablewater, Gravewatch, and the Underclock can be pursued in the order that interests you.",
    )


async def _show_journey(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    flags = session.database.list_flags(character.id)
    title, text = journey_stage_for(
        race_key=character.race or "",
        level=int(character.level),
        flags=flags,
    )
    loop = STARTER_RACE_LOOPS_BY_RACE.get(character.race or "")
    origin = loop.hook_name if loop is not None else "Your origin"
    await session.send(
        "\r\n--- Your Journey ---\r\n"
        f"Origin: {origin}\r\n"
        f"Now: {title}\r\n"
        f"{text}\r\n"
        "This is a horizon, not a mandatory checklist. QUESTS shows concrete objectives; JOURNEY only reminds you how the larger adventure connects.\r\n"
    )


def _epilogue_flag(race_key: str) -> str:
    return f"launch_opening_epilogue_seen_{race_key}"


async def _maybe_send_opening_epilogue(session, before_flags: frozenset[str] | set[str]) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    race_key = character.race or ""
    loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
    text = OPENING_EPILOGUES.get(race_key)
    if loop is None or text is None:
        return False
    after_flags = session.database.list_flags(character.id)
    seen_flag = _epilogue_flag(race_key)
    if loop.completion_flag not in after_flags or loop.completion_flag in before_flags or seen_flag in after_flags:
        return False
    session.database.grant_flag(character.id, seen_flag)
    await session.send(
        f"\r\n--- {loop.hook_name} ---\r\n"
        f"{text[0]}\r\n\r\n{text[1]}\r\n"
        "Type JOURNEY whenever you want the larger road ahead without spoiling the route.\r\n"
    )
    return True


async def _maybe_send_veyra_arrival(session) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    room_key = character.current_room or ""
    flags = session.database.list_flags(character.id)
    if room_key == VEYRA_GATE_WARD_KEY and VEYRA_GATE_MEMORY_FLAG not in flags:
        session.database.grant_flag(character.id, VEYRA_GATE_MEMORY_FLAG)
        await session.send(f"\r\n{VEYRA_GATE_ARRIVAL}\r\n")
        return True
    if room_key == VEYRA_GRAND_CROSSING_KEY and VEYRA_CROSSING_MEMORY_FLAG not in flags:
        session.database.grant_flag(character.id, VEYRA_CROSSING_MEMORY_FLAG)
        await session.send(
            f"\r\n{VEYRA_CROSSING_ARRIVAL}\r\n"
            "For a moment, Grand Crossing is not a service on a city map. It is the proof that all those separate beginnings were happening in the same world.\r\n"
        )
        return True
    return False


def _clean_social_text(value: str, *, limit: int = 300) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())[:limit]


def _room_player(session, name: str):
    character = getattr(session, "character", None)
    if character is None:
        return None
    wanted = name.strip().lower()
    for other in tuple(social._ACTIVE_SESSIONS):
        other_character = getattr(other, "character", None)
        if (
            other_character is not None
            and (other_character.current_room or "") == (character.current_room or "")
            and other_character.name.lower() == wanted
        ):
            return other_character
    return None


async def _broadcast_room_emote(session, action: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    cleaned = _clean_social_text(action)
    if not cleaned:
        await session.send("EMOTE what? Example: EMOTE studies the map in silence.\r\n")
        return
    line = f"[Emote] {character.name} {cleaned}\r\n"
    for other in tuple(social._ACTIVE_SESSIONS):
        other_character = getattr(other, "character", None)
        if other_character is None or (other_character.current_room or "") != (character.current_room or ""):
            continue
        if other is not session and social._is_ignored_by_id(other, character.id):
            continue
        try:
            await other.send(line)
        except (ConnectionError, RuntimeError):
            continue


async def _shortcut_emote(session, verb: str, target_text: str = "") -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    plain, targeted = EMOTE_VERBS[verb]
    if target_text.strip():
        target = _room_player(session, target_text)
        if target is None:
            await session.send("Nobody by that name is here.\r\n")
            return
        action = targeted.format(target=target.name)
    else:
        action = plain
    await _broadcast_room_emote(session, action)


def _in_social_hub(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character is not None and (character.current_room or "") in SOCIAL_HUBS)


async def _tavern_who(session) -> None:
    if not _in_social_hub(session):
        await session.send(
            "TAVERN is available while you are gathered at Waymeet Commonhouse Yard or Veyra Public Hearth.\r\n"
        )
        return
    people: list[tuple[str, str]] = []
    for other in tuple(social._ACTIVE_SESSIONS):
        character = getattr(other, "character", None)
        if character is None:
            continue
        hub = SOCIAL_HUBS.get(character.current_room or "")
        if hub:
            people.append((character.name, hub))
    people.sort(key=lambda entry: entry[0].lower())
    await session.send("\r\n--- Tavern Crowd ---\r\n")
    if not people:
        await session.send("The public hearths are quiet.\r\n")
        return
    for name, hub in people:
        await session.send(f"{name} — {hub}\r\n")


async def _broadcast_tavern(session, message: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if not _in_social_hub(session):
        await session.send(
            "TAVERN is a player-social channel available only from Waymeet Commonhouse Yard or Veyra Public Hearth.\r\n"
            "It connects characters who are currently gathered at either public hearth; it is not literal shouted dialogue across Astralis.\r\n"
        )
        return
    cleaned = _clean_social_text(message, limit=500)
    if not cleaned:
        await session.send("Use TAVERN <message> or TAVERN WHO.\r\n")
        return
    source = SOCIAL_HUBS[character.current_room or ""]
    line = f"[Tavern — {source}] {character.name}: {cleaned}\r\n"
    delivered = False
    for other in tuple(social._ACTIVE_SESSIONS):
        other_character = getattr(other, "character", None)
        if other_character is None or (other_character.current_room or "") not in SOCIAL_HUBS:
            continue
        if other is not session and social._is_ignored_by_id(other, character.id):
            continue
        try:
            await other.send(line)
            if other is session:
                delivered = True
        except (ConnectionError, RuntimeError):
            continue
    if not delivered:
        await session.send(line)


async def _send_texture_help(session) -> None:
    await session.send(
        "\r\n--- Social Texture ---\r\n"
        "EMOTE <action> - clear, local freeform roleplay; output is always labeled as an emote.\r\n"
        "WAVE / NOD / SMILE / LAUGH / BOW / SHRUG / CHEER [name] - quick local gestures.\r\n"
        "TAVERN <message> - social-hub chat while at Waymeet Commonhouse or Veyra Public Hearth.\r\n"
        "TAVERN WHO - see who is currently gathered at those public hearths.\r\n"
        "Friends also receive a small notice when a saved friend enters or leaves Astralis; no private location is revealed.\r\n"
    )


def _observer_has_friend(observer, target_name: str) -> bool:
    observer_character = getattr(observer, "character", None)
    database = getattr(observer, "database", None)
    if observer_character is None or database is None:
        return False
    social._ensure_schema(database)
    target = database.get_character_by_name(target_name)
    if target is None:
        return False
    with database.connect() as db:
        row = db.execute(
            "SELECT 1 FROM character_friends WHERE character_id = ? AND friend_character_id = ?",
            (observer_character.id, target.id),
        ).fetchone()
    return row is not None


async def _notify_friend_presence(session, *, online: bool) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    state = "entered Astralis" if online else "left Astralis"
    for other in tuple(social._ACTIVE_SESSIONS):
        if other is session or getattr(other, "character", None) is None:
            continue
        if not _observer_has_friend(other, character.name):
            continue
        if social._is_ignored_by_id(other, character.id):
            continue
        try:
            await other.send(f"[Friend] {character.name} has {state}.\r\n")
        except (ConnectionError, RuntimeError):
            continue


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


def _prompt_text(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_launch_vertical_slice_runtime(player_session_class) -> None:
    """Polish the first shared hours without replacing authored race content."""
    if getattr(player_session_class, "_launch_vertical_slice_runtime_installed", False):
        return

    install_launch_vertical_slice_content()
    apply_first_hours_combat_tuning()

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            if getattr(self, "character", None) is not None:
                await _notify_friend_presence(self, online=True)

        player_session_class.enter_character = enter_character

    previous_close = getattr(player_session_class, "close", None)
    if previous_close is not None:
        async def close(self) -> None:
            if getattr(self, "character", None) is not None:
                await _notify_friend_presence(self, online=False)
            await previous_close(self)

        player_session_class.close = close

    previous_move_character = getattr(player_session_class, "move_character", None)
    if previous_move_character is not None:
        async def move_character(self, direction: str) -> None:
            character = getattr(self, "character", None)
            before_flags = self.database.list_flags(character.id) if character is not None else frozenset()
            await previous_move_character(self, direction)
            if getattr(self, "character", None) is not None:
                await _maybe_send_opening_epilogue(self, before_flags)
                await _maybe_send_veyra_arrival(self)

        player_session_class.move_character = move_character

    previous_finish_enemy = getattr(player_session_class, "_finish_enemy_defeat", None)
    if previous_finish_enemy is not None:
        async def _finish_enemy_defeat(self, enemy) -> None:
            enemy_key = str(getattr(getattr(enemy, "definition", None), "key", ""))
            eligible = getattr(self, "active_enemy", None) is enemy
            await previous_finish_enemy(self, enemy)
            if eligible:
                await _award_first_notable_find(self, enemy_key)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_playing_prompt(self)
            return

        before_flags = self.database.list_flags(character.id)
        command = await self.prompt(_prompt_text(self))
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"journey", "story", "horizon", "first hours"}:
            await _show_journey(self)
            return
        if normalized in {"emotes", "gesture", "gestures"}:
            await _send_texture_help(self)
            return
        if normalized in {"social", "communication"}:
            await social._send_channels(self)
            await _send_texture_help(self)
            return
        if normalized == "emote":
            await self.send("Use EMOTE <action>. Example: EMOTE studies the map in silence.\r\n")
            return
        if normalized.startswith("emote "):
            await _broadcast_room_emote(self, stripped.split(maxsplit=1)[1])
            return

        verb = normalized.split(maxsplit=1)[0] if normalized else ""
        if verb in EMOTE_VERBS:
            target = stripped.split(maxsplit=1)[1] if " " in stripped else ""
            await _shortcut_emote(self, verb, target)
            return

        if normalized in {"tavern", "tavern help"}:
            await self.send(
                "TAVERN <message> connects players currently gathered at Waymeet Commonhouse Yard or Veyra Public Hearth. TAVERN WHO lists the current crowd.\r\n"
            )
            return
        if normalized == "tavern who":
            await _tavern_who(self)
            return
        if normalized.startswith("tavern "):
            await _broadcast_tavern(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_playing_prompt, command)
        await _maybe_send_opening_epilogue(self, before_flags)
        await _maybe_send_veyra_arrival(self)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._launch_vertical_slice_runtime_installed = True
