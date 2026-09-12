from __future__ import annotations

from dataclasses import dataclass

from mud.style_collectibles import BOUTIQUE_ROOMS


@dataclass(frozen=True, slots=True)
class CommandEntry:
    category: str
    syntax: str
    description: str
    keywords: tuple[str, ...] = ()


# This catalog intentionally describes player-facing command families rather than
# every parser spelling as a separate row. Aliases live in the syntax field, so
# COMMANDS ALL is readable instead of being hundreds of near-duplicate lines.
COMMANDS: tuple[CommandEntry, ...] = (
    CommandEntry("basics", "LOOK / L", "Redisplay the current room."),
    CommandEntry("basics", "LOOK <player>", "Inspect a nearby player's appearance, styled outfit, visible gear, and active fragrance."),
    CommandEntry("basics", "EXITS", "Show visible exits from the current room."),
    CommandEntry("basics", "N / E / S / W / U / D", "Move through a visible exit; full direction words also work."),
    CommandEntry("basics", "EXAMINE <feature>", "Read authored detail about a visible room feature."),
    CommandEntry("basics", "SEARCH <feature>", "Search where a room explicitly suggests searching."),
    CommandEntry("basics", "LISTEN [target]", "Listen where sound is an authored clue or mechanic."),
    CommandEntry("basics", "TOUCH <feature>", "Interact physically when a room explicitly presents a touchable feature."),
    CommandEntry("basics", "PULL <feature>", "Operate a named lever, rope, chain, brake, or resonator."),
    CommandEntry("basics", "CLIMB <feature>", "Use a telegraphed vertical route or inspection feature."),
    CommandEntry("basics", "READ <object>", "Read signs, notes, boards, and authored written objects where supported."),
    CommandEntry("basics", "HELP / ?", "Open the game's normal help output."),
    CommandEntry("basics", "HELP HERE / SUGGEST", "Show commands that are especially relevant in your current room and state."),
    CommandEntry("basics", "COMMANDS", "Show command categories and common starting commands."),
    CommandEntry("basics", "COMMANDS <category>", "Show every cataloged command family in one category."),
    CommandEntry("basics", "COMMANDS ALL", "Print the complete searchable player command catalog."),
    CommandEntry("basics", "COMMAND SEARCH <word>", "Search command syntax and descriptions by word."),
    CommandEntry("basics", "JOURNEY", "Show a spoiler-light sense of the current progression path."),
    CommandEntry("basics", "QUIT", "Leave the current game session safely."),

    CommandEntry("character", "SCORE / STATUS / SHEET / STATS", "Show level, XP, base stats, equipment bonuses, and derived values."),
    CommandEntry("character", "INVENTORY / INV / I", "List items currently carried."),
    CommandEntry("character", "EQUIPMENT / GEAR / WORN", "Show combat-equipment slots and stat totals."),
    CommandEntry("character", "EQUIP / WEAR / WIELD <item>", "Equip ordinary combat gear; WEAR automatically routes fashion pieces to the style system."),
    CommandEntry("character", "UNEQUIP / REMOVE <slot or item>", "Remove combat equipment."),
    CommandEntry("character", "COMPARE <item>", "Compare carried equipment with the item occupying the same combat slot."),
    CommandEntry("character", "ITEM / INSPECT ITEM <item>", "Inspect carried equipment, fashion, or fragrance metadata."),
    CommandEntry("character", "CLASS", "Show class role, known abilities, costs, cooldowns, and upcoming progression."),
    CommandEntry("character", "ABILITIES", "Review known active abilities where the underlying class runtime supports it."),
    CommandEntry("character", "SKILLS", "Review use-based skill progress."),
    CommandEntry("character", "PROFESSIONS / TRADESKILLS", "Review crafting and gathering skill progress."),
    CommandEntry("character", "QUESTS", "Show active and completed structured quests."),
    CommandEntry("character", "ACCESS", "Show major authored access flags and level gates."),
    CommandEntry("character", "BIND", "Use an available bind service where the room supports one."),

    CommandEntry("combat", "ATTACK / KILL <enemy>", "Engage an available enemy or explicitly authored boss."),
    CommandEntry("combat", "FLEE", "Attempt to leave active combat."),
    CommandEntry("combat", "USE / CAST <ability>", "Use a class ability by its known name or runtime command."),
    CommandEntry("combat", "BRACE", "React to an explicitly telegraphed heavy impact in encounters that support it."),
    CommandEntry("combat", "COVER EARS", "React to an explicitly telegraphed sound attack where supported."),
    CommandEntry("combat", "STEP ASIDE", "React to an explicitly telegraphed charge where supported."),
    CommandEntry("combat", "RELEASE", "After death, accept the XP-loss release and return to your bind point."),
    CommandEntry("combat", "RESURRECT <player>", "Priest utility that can return an unreleased fallen player without their release XP loss."),

    CommandEntry("social", "SAY <message>", "Speak to everyone in the current room."),
    CommandEntry("social", "CHAT <message>", "Speak on world chat."),
    CommandEntry("social", "OOC <message>", "Speak on the out-of-character channel."),
    CommandEntry("social", "TELL <name> <message>", "Send a private message to an online character."),
    CommandEntry("social", "REPLY <message>", "Reply to the most recent private sender."),
    CommandEntry("social", "CHANNEL CHAT|OOC ON|OFF", "Mute or unmute global channels."),
    CommandEntry("social", "WHO", "List currently connected characters."),
    CommandEntry("social", "FRIENDS / FRIEND / UNFRIEND", "Manage the persistent friend list."),
    CommandEntry("social", "IGNORES / IGNORE / UNIGNORE", "Manage blocked player communication."),
    CommandEntry("social", "TAVERN <message>", "Use the cross-hearth social channel where the living-world layer exposes it."),
    CommandEntry("social", "WAVE / NOD / SMILE / LAUGH / BOW / SHRUG / CHEER", "Use lightweight room emotes."),

    CommandEntry("party", "PARTY INVITE <player>", "Invite a nearby character to a party."),
    CommandEntry("party", "PARTY ACCEPT / PARTY DECLINE", "Answer a party invitation."),
    CommandEntry("party", "PARTY LEAVE", "Leave the current party."),
    CommandEntry("party", "PARTY KICK <player>", "Leader removes a party member."),
    CommandEntry("party", "PARTY LEADER <player>", "Transfer party leadership where supported."),
    CommandEntry("party", "PARTY FOLLOW ON|OFF", "Control party movement following."),
    CommandEntry("party", "PARTY SAY <message>", "Speak only to party members."),
    CommandEntry("party", "ASSIST <player>", "Join a party member's active target where supported."),
    CommandEntry("party", "PARTY LOOT ...", "View or change supported party loot assignment rules."),
    CommandEntry("party", "READY / READY CHECK", "Participate in a party ready check."),
    CommandEntry("party", "FOCUS <target>", "Call a shared party focus target."),
    CommandEntry("party", "PARTY HUD / COHESION", "Show compact party status and separation information."),

    CommandEntry("economy", "RESOURCES / STATIONS", "Show gatherable resources and crafting stations in the room."),
    CommandEntry("economy", "GATHER <resource>", "Gather from a visible authored resource node."),
    CommandEntry("economy", "MINE [resource]", "Gather with Mining from a compatible node."),
    CommandEntry("economy", "HARVEST [resource]", "Gather with Harvesting from a compatible node."),
    CommandEntry("economy", "HERBALISM [resource]", "Gather with Herbalism from a compatible node."),
    CommandEntry("economy", "RECIPES [profession]", "Browse known craftable recipes and their requirements."),
    CommandEntry("economy", "CRAFT <recipe>", "Craft at the required station using real inventory materials."),
    CommandEntry("economy", "ECONOMY / ECONOMY ROUTE", "Explain the hunt-gather-craft-trade loop and starter route."),
    CommandEntry("economy", "NEEDS <item or recipe>", "Show missing materials and useful source hints."),
    CommandEntry("economy", "GIVE <player> [qty] <item>", "Directly transfer a tradeable item to a nearby player."),
    CommandEntry("economy", "TRADE <player>", "Begin the safe two-sided trade flow."),
    CommandEntry("economy", "TRADE ACCEPT / DECLINE / STATUS / CANCEL", "Manage a pending or active trade."),
    CommandEntry("economy", "TRADE ADD / REMOVE [qty] <item>", "Edit your trade offer; changes reset confirmation."),
    CommandEntry("economy", "TRADE CONFIRM", "Confirm the current trade offer; both players must confirm the same state."),

    CommandEntry("world", "TIME / DATE / CALENDAR", "Read the persistent accelerated Astralis clock and calendar."),
    CommandEntry("world", "WEATHER", "Read current regional weather where the calendar runtime exposes it."),
    CommandEntry("world", "TODAY / DISPATCH", "Read the current living-world pulse without turning it into a daily quest."),
    CommandEntry("world", "GOSSIP / RUMOR", "Hear the current event and public-history texture through in-world rumor."),
    CommandEntry("world", "CHRONICLE / HISTORY", "Read persistent public server history and recorded firsts."),
    CommandEntry("world", "MAIL", "List return letters generated while Astralis continued without you."),
    CommandEntry("world", "READ MAIL <number>", "Read one return letter."),
    CommandEntry("world", "LOCALS", "See recurring living-world people currently present."),
    CommandEntry("world", "PIN NOTE <message>", "Post a short temporary player note at a supported public hearth."),
    CommandEntry("world", "BOARD NOTES", "Read temporary player notes at the current supported hearth."),
    CommandEntry("world", "REMOVE NOTE <number>", "Remove one of your own temporary notes."),
    CommandEntry("world", "ASK KEEPER RUMOR", "Hear a keeper repeat a current player note or Chronicle memory."),
    CommandEntry("world", "RENT ROOM / ENTER ROOM", "Rent or enter your small persistent personal room at a supported hearth."),
    CommandEntry("world", "ROOM STORAGE / ROOM STORE / ROOM TAKE", "Manage the personal room's storage chest."),
    CommandEntry("world", "DISPLAY <item> / SHELF / TAKE DISPLAY <slot>", "Use the personal room's five physical display slots."),

    CommandEntry("veyra", "CITY / VEYRA / CITY SERVICES", "Review Veyra's major public services."),
    CommandEntry("veyra", "VAULT", "Inspect Keyhouse storage."),
    CommandEntry("veyra", "DEPOSIT / WITHDRAW [qty] <item>", "Move items into or out of persistent Keyhouse storage."),
    CommandEntry("veyra", "MARKET", "Browse the real player barter market."),
    CommandEntry("veyra", "LIST <qty> <item> FOR <qty> <item>", "Place a barter listing into escrow."),
    CommandEntry("veyra", "FILL <listing id>", "Fill a barter listing using the requested real item."),
    CommandEntry("veyra", "CANCEL LISTING <id>", "Cancel your own open listing."),
    CommandEntry("veyra", "TRAIN", "Review class training and upcoming known unlocks."),
    CommandEntry("veyra", "MARKET DAY / DEMAND", "See the current rotating civic material demand."),
    CommandEntry("veyra", "SELL DEMAND <qty> <item>", "Sell complete demand bundles for civic scrip."),
    CommandEntry("veyra", "CONTRACT / ACCEPT CONTRACT / TURN IN CONTRACT", "Work the current weekly civic material contract."),
    CommandEntry("veyra", "FACTION STATUS / FACTION DUTY / FACTION PROMOTE", "Review and advance deeper Veyra faction service."),
    CommandEntry("veyra", "RIDE WAYMEET / GREYWAKE / SABLEWATER / GLOAM", "Use Roadwarden travel privileges when your rank unlocks them."),

    CommandEntry("dungeons", "IMPRESSION", "Re-read perception-dependent Gloamworks observations for your race/class."),
    CommandEntry("dungeons", "HOLD SEAL", "Operate one side of the Gloamworks two-player witness-seal mechanism."),
    CommandEntry("dungeons", "CLOCK / CYCLE / UNDERCLOCK", "Read the Underclock's live four-phase machine cycle."),
    CommandEntry("dungeons", "CROSS PISTONS / CROSS STEAM / CROSS TEETH", "Attempt Underclock hazard crossings during the correct cycle phase."),
    CommandEntry("dungeons", "SET INTAKE VALVE / LOCK FLYWHEEL / BLEED GOVERNOR", "Calibrate the Underclock boss environment on the correct phases."),
    CommandEntry("dungeons", "ENGAGE GOVERNOR / START LIFT", "Start the Underclock boss and complete the municipal repair after victory."),
    CommandEntry("dungeons", "PULL HOUND / ARCHER / PIKEGUARD", "Separate Gravewatch courtyard patrol elements before fighting the captain."),
    CommandEntry("dungeons", "OPEN PORTCULLIS / LIGHT BEACON", "Advance Gravewatch after clearing its officers and final commander."),
    CommandEntry("dungeons", "EXPLORE / ADVENTURE", "Show spoiler-light progress through Waymeet's outer-road adventure ring."),
    CommandEntry("dungeons", "SECRETS / MYSTERIES", "Show only how many optional outer listening marks you found, never their missing locations."),
    CommandEntry("dungeons", "PULL LOW / PULL HIGH", "Operate the Crooked Bell rope puzzle using the sequence learned by listening."),
    CommandEntry("dungeons", "CLIMB GANTRY / PULL BRAKE", "Use King's Scar's vertical survey and freight-route mechanics."),
    CommandEntry("dungeons", "TOUCH PLATE", "Activate a resonance plate in the Vault of the First Echo."),
    CommandEntry("dungeons", "PULL RESONATOR", "Interrupt the Listener Below's false-breath phase after LISTEN reveals the mechanism."),

    CommandEntry("pastimes", "PASTIMES / GAMES", "Show organized low-stakes activities available in the current room."),
    CommandEntry("pastimes", "BONES", "Play a quick Three Bones tavern game for bragging-rights keepsakes."),
    CommandEntry("pastimes", "ARM WRESTLE <player> / ARM ACCEPT / ARM DECLINE", "Run a nearby player-vs-player Might contest with no combat consequences."),
    CommandEntry("pastimes", "THROW KNIFE", "Make three Grace-influenced practice throws."),
    CommandEntry("pastimes", "SCORES", "Show today's local knife-throw high scores."),
    CommandEntry("pastimes", "DRINK ROUND", "Advance the five-round humorous tavern mug game; it applies no gameplay debuff."),
    CommandEntry("pastimes", "RIDDLE / ANSWER <answer>", "Try the market's rotating chalk riddle."),
    CommandEntry("pastimes", "JAR / GUESS JAR <number>", "Play the market guessing jar with three daily guesses."),
    CommandEntry("pastimes", "WATCH SHOW / HECKLE / APPLAUD", "Interact with the Crooked Lantern Company when the troupe is performing."),
    CommandEntry("pastimes", "KEEPSAKES / TROPHIES", "Review statless social keepsakes and bragging-rights objects."),

    CommandEntry("style", "STYLE / WARDROBE / OUTFIT / FASHION", "Show your worn fashion and fashion pieces currently carried."),
    CommandEntry("style", "STYLE WEAR <item>", "Wear a cosmetic piece in its independent fashion slot without changing combat gear."),
    CommandEntry("style", "STYLE REMOVE <slot or item>", "Remove one cosmetic piece from the styled outfit."),
    CommandEntry("style", "BOUTIQUE", "Browse fashion and fragrance stock at Veyra Brassmarket or the smaller Waymeet traveling trunk."),
    CommandEntry("style", "BUY STYLE <item>", "Buy a normal designer fashion piece with Waymeet Trade Scrip."),
    CommandEntry("style", "FRAGRANCES / PERFUMES", "List fragrance bottles you currently carry, including notes and effect length."),
    CommandEntry("style", "BUY FRAGRANCE <name>", "Buy a fragrance bottle from a supported style counter."),
    CommandEntry("style", "APPLY FRAGRANCE <name> / SPRAY <name>", "Consume one bottle and activate its real-time +10% character-XP effect."),
    CommandEntry("style", "SCENT", "Show the fragrance currently worn, notes, remaining time, and bonus XP earned."),
    CommandEntry("style", "COLLECTION", "Show discovered fashion and fragrance counts by rarity; consumed bottles remain discovered."),
    CommandEntry("style", "PROVENANCE <item>", "Read serialized origin and previous-owner history for a heritage fashion piece."),
    CommandEntry("style", "SEASONAL STYLE", "Show the current limited seasonal edition and how it is earned."),
)

CATEGORIES = tuple(dict.fromkeys(entry.category for entry in COMMANDS))


def _matches(entry: CommandEntry, query: str) -> bool:
    wanted = query.strip().lower()
    haystack = " ".join((entry.category, entry.syntax, entry.description, *entry.keywords)).lower()
    return wanted in haystack


async def _show_categories(session) -> None:
    await session.send("\r\n--- Command Guide ---\r\n")
    await session.send("Categories: " + ", ".join(CATEGORIES) + ".\r\n")
    await session.send("Common: LOOK, EXITS, SCORE, INVENTORY, EQUIPMENT, CLASS, QUESTS, SAY, PARTY HUD, HELP HERE.\r\n")
    await session.send("Use COMMANDS <category>, COMMANDS ALL, or COMMAND SEARCH <word>. HELP HERE is contextual and intentionally short.\r\n")


async def _show_category(session, category: str) -> None:
    wanted = category.strip().lower()
    rows = [entry for entry in COMMANDS if entry.category == wanted]
    if not rows:
        await session.send("Unknown command category. Available: " + ", ".join(CATEGORIES) + ".\r\n")
        return
    await session.send(f"\r\n--- Commands: {wanted.title()} ---\r\n")
    for entry in rows:
        await session.send(f"{entry.syntax} — {entry.description}\r\n")


async def _search_commands(session, query: str) -> None:
    wanted = query.strip()
    if not wanted:
        await session.send("Use COMMAND SEARCH <word>.\r\n")
        return
    rows = [entry for entry in COMMANDS if _matches(entry, wanted)]
    await session.send(f"\r\n--- Command Search: {wanted} ---\r\n")
    if not rows:
        await session.send("No cataloged command family matched. Try a broader word or HELP HERE.\r\n")
        return
    for entry in rows[:30]:
        await session.send(f"[{entry.category}] {entry.syntax} — {entry.description}\r\n")
    if len(rows) > 30:
        await session.send(f"...and {len(rows) - 30} more matches; narrow the search term.\r\n")


def _feature_command_hints(world_service, room_key: str) -> list[str]:
    augmentation = world_service.augmentations.get(room_key)
    if augmentation is None:
        return []
    hints: list[str] = []
    verbs = ("SEARCH", "LISTEN", "CLIMB", "PULL", "TOUCH", "EXAMINE", "OPEN", "READ")
    for feature in augmentation.features:
        text = f"{feature.summary} {feature.examine_text} {feature.search_text} {feature.listen_text} {feature.touch_text}".upper()
        for verb in verbs:
            if verb in text and verb not in hints:
                hints.append(verb)
    return hints


async def _show_help_here(session, world_service) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    room_key = character.current_room or ""
    room = world_service.legacy_rooms.get(room_key)
    region = room.region_key if room is not None else ""
    suggestions: list[tuple[str, str]] = [
        ("LOOK", "redisplay this room"),
        ("EXITS", "see visible travel routes"),
    ]
    if getattr(session, "active_enemy", None) is not None:
        suggestions.extend((("CLASS", "review your combat kit"), ("FLEE", "try to break combat"), ("PARTY HUD", "check nearby party state")))
    else:
        suggestions.append(("EXAMINE <feature>", "inspect something named in the room text"))

    for verb in _feature_command_hints(world_service, room_key):
        suggestions.append((f"{verb} <named feature>", "this room contains authored text that points at this interaction"))

    if room_key in BOUTIQUE_ROOMS:
        suggestions.extend((("BOUTIQUE", "browse fashion and fragrance"), ("WARDROBE", "review your current style")))
    if "waymeet" in region or room_key.startswith("waymeet_"):
        suggestions.extend((("EXPLORE", "see spoiler-light outer-road adventure progress"), ("ECONOMY ROUTE", "review the shared hunt/gather/craft loop"), ("PASTIMES", "see local social games")))
    if "veyra" in region or room_key.startswith("veyra_"):
        suggestions.extend((("CITY", "review Veyra services"), ("MARKET", "browse player barter listings"), ("FACTION STATUS", "review Veyra faction standing")))
    if region == "gloamworks":
        suggestions.extend((("IMPRESSION", "re-read what your character perceives here"), ("PARTY HUD", "check cooperative dungeon state")))
    if region == "veyra_underclock":
        suggestions.append(("CLOCK", "read the Underclock's current machine phase"))
    if region == "gravewatch_keep":
        suggestions.append(("LOOK", "watch room text for pullable patrols and ordinary military routes"))
    if region in {"tollmans_cellar", "crooked_bell", "kings_scar", "vault_first_echo", "waymeet_outer_adventure"}:
        suggestions.append(("SECRETS", "see only how many optional outer mysteries you have noticed"))
    if "sablewater" in region:
        suggestions.append(("LOOK", "Sablewater progression is carried by physical roads, waterworks, and civic machinery"))

    # De-duplicate while preserving the authored order.
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for command, reason in suggestions:
        if command not in seen:
            seen.add(command)
            unique.append((command, reason))

    await session.send("\r\n--- Useful Here ---\r\n")
    if room is not None:
        await session.send(f"{room.name} [{region}]\r\n")
    for command, reason in unique[:12]:
        await session.send(f"{command} — {reason}.\r\n")
    await session.send("This is a suggestion list, not a checklist. COMMANDS searches the complete guide.\r\n")


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


def install_command_guide_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_command_guide_runtime_installed", False):
        return
    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None:
            await self.send("Command discovery: HELP HERE shows only what is useful in your current situation; COMMANDS searches the full catalog.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"commands", "command guide", "help commands"}:
            await _show_categories(self); return
        if normalized == "commands all":
            for category in CATEGORIES:
                await _show_category(self, category)
            return
        if normalized.startswith("commands "):
            await _show_category(self, stripped[len("commands "):]); return
        if normalized.startswith("command search "):
            await _search_commands(self, stripped[len("command search "):]); return
        if normalized.startswith("find command "):
            await _search_commands(self, stripped[len("find command "):]); return
        if normalized in {"help here", "suggest", "suggestions", "what can i do", "what can i do here"}:
            await _show_help_here(self, world_service); return
        if normalized.startswith("help "):
            query = stripped[len("help "):].strip()
            if query.lower() in CATEGORIES:
                await _show_category(self, query); return
            rows = [entry for entry in COMMANDS if _matches(entry, query)]
            if rows:
                await self.send(f"\r\n--- Help: {query} ---\r\n")
                for entry in rows[:12]:
                    await self.send(f"[{entry.category}] {entry.syntax} — {entry.description}\r\n")
                return

        await _delegate(self, previous_prompt, command)

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._command_guide_runtime_installed = True
