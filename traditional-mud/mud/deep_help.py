from __future__ import annotations

from dataclasses import dataclass

import mud.command_guide as command_guide
from mud.command_guide import CommandEntry


@dataclass(frozen=True, slots=True)
class HelpTopic:
    key: str
    title: str
    category: str
    summary: str
    sections: tuple[tuple[str, tuple[str, ...]], ...]
    aliases: tuple[str, ...] = ()
    see_also: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


CATEGORY_INFO: dict[str, tuple[str, str]] = {
    "start": (
        "Getting Started",
        "The shortest path from a fresh character to confidently moving, fighting, looting, recovering, and finding the next thing to do.",
    ),
    "exploration": (
        "Movement & Exploration",
        "Rooms, exits, maps, waymaps, local interactions, travel, environmental clues, and finding useful things without a checklist.",
    ),
    "combat": (
        "Combat & Survival",
        "Targeting, auto-attacks, abilities, reactions, death, recovery, resurrection, corpses, and sustained hunting.",
    ),
    "character": (
        "Character & Progression",
        "Stats, levels, class abilities, mastery, racial abilities, quests, access, movement, bind points, and identity.",
    ),
    "items": (
        "Items, Gear & Inventory",
        "Inventory, equipment, comparison, ground items, loot, item inspection, provenance, bags, fashion, and fragrances.",
    ),
    "crafting": (
        "Gathering & Crafting",
        "Resources, gathering professions, recipes, stations, crafting professions, food, potions, and material planning.",
    ),
    "economy": (
        "Economy & Trade",
        "Sols, merchants, valuation, player trading, Veyra markets, storage, civic demand, and contracts.",
    ),
    "social": (
        "Social & Communication",
        "Room speech, world chat, tells, friends, ignores, custom channels, mail, emotes, taverns, and public notes.",
    ),
    "party": (
        "Parties & Group Play",
        "Invites, following, party chat, assist, focus, loot rules, ready checks, cohesion, and group dungeon habits.",
    ),
    "world": (
        "World & Living Systems",
        "Astralis time, weather, ecology, rumors, Chronicle history, factions, living-world pulses, roads, and cities.",
    ),
    "adventure": (
        "Adventures, Dungeons & Secrets",
        "How authored adventures communicate danger, puzzle verbs, dungeon mechanisms, optional mysteries, and spoiler-light discovery.",
    ),
    "style": (
        "Style & Collections",
        "Wardrobes, copied looks, boutiques, fragrances, collectibles, seasonal style, titles, auras, and sigils.",
    ),
    "settings": (
        "Settings & Accessibility",
        "Prompt detail, ANSI color, contrast, hints, screen-reader output, Mudlet enhancements, and restoring defaults.",
    ),
    "support": (
        "Community Support",
        "Voting support, Echoes of Favour, cosmetic rewards, and other account-wide community systems.",
    ),
    "reference": (
        "Reference",
        "The complete command catalog, alphabetical index, search tools, command-specific help, and help-system navigation.",
    ),
}


TOPICS: tuple[HelpTopic, ...] = (
    HelpTopic(
        "getting-started",
        "Getting Started",
        "start",
        "A practical first-session route through the core game loop.",
        (
            ("First five minutes", (
                "Use LOOK to read the room, EXITS to see obvious routes, and EXAMINE on nouns that sound important.",
                "Use QUESTS when you have an authored objective. The objective text is the most reliable statement of what your current quest expects.",
                "Use INVENTORY and EQUIPMENT early so you know what you are carrying and what is actually worn.",
            )),
            ("When danger appears", (
                "CONSIDER <target> gives a spoiler-light danger read without starting a fight.",
                "ATTACK <target> begins combat. Auto-attacks continue while you use class abilities with USE or CAST.",
                "If a fight is going badly, FLEE is a normal survival tool. It is not a failure state.",
            )),
            ("After a kill", (
                "LOOK CORPSE or CORPSES shows physical remains and available drops.",
                "LOOT CORPSE takes everything currently available to you. Specific GET ... FROM ... forms let you be selective.",
                "HUNT shows whether the current area supports sustained combat grinding and whether you have momentum.",
            )),
            ("When unsure", (
                "HELP HERE is contextual and short. HELP SEARCH <word> searches the entire help library.",
                "HELP INDEX is the alphabetical rabbit hole. COMMANDS remains the concise raw command catalog.",
            )),
        ),
        aliases=("start", "new player", "newbie", "beginner", "basics"),
        see_also=("exploration", "combat-basics", "items", "quests", "help-system"),
        keywords=("tutorial", "first session", "learn"),
    ),
    HelpTopic(
        "exploration",
        "Exploration",
        "exploration",
        "How to read a text world, move through it, and recognize authored interaction clues.",
        (
            ("Read the room like an interface", (
                "Room text is gameplay UI. Named objects, unusual sounds, repeated landmarks, mechanisms, roads, and physical changes are often meaningful.",
                "LOOK refreshes the scene. FEATURES, DETAILS, or LANDMARKS can surface visible authored features where supported.",
                "HELP HERE intentionally suggests only interactions relevant to the current room and state.",
            )),
            ("Use precise verbs", (
                "EXAMINE is the safest first probe. SEARCH, LISTEN, TOUCH, READ, PULL, TURN, CLIMB, OPEN, and other verbs are used when the fiction supports them.",
                "The game avoids requiring blind parser guessing for critical progression. Important interactions should be signaled by room text, quest text, or prior clues.",
            )),
            ("Travel", (
                "Use cardinal directions or their one-letter aliases. EXITS shows visible routes.",
                "MAP shows only rooms your character has personally discovered. WAYMAPS are physical destination maps that can guide automated route travel.",
            )),
        ),
        aliases=("explore", "navigation", "travel"),
        see_also=("maps", "waymaps", "room-interactions", "secrets", "world"),
    ),
    HelpTopic(
        "maps",
        "Discovery Map",
        "exploration",
        "Your persistent map is based on places this character has actually discovered.",
        (
            ("Commands", (
                "MAP or MAP HERE shows the local discovered-room map.",
                "MAP 1 through MAP 4 changes the local radius.",
            )),
            ("What it does not do", (
                "The map does not reveal undiscovered rooms, hidden exits, or secret completion percentages.",
                "It is a memory aid, not an omniscient world map.",
            )),
        ),
        aliases=("map", "mapper", "discovery map"),
        see_also=("exploration", "waymaps", "secrets"),
    ),
    HelpTopic(
        "waymaps",
        "Waymaps",
        "exploration",
        "Physical reusable destination maps that remember a real room and can guide travel back to it.",
        (
            ("Create a destination", (
                "Carry a Blank Waymap, stand where you want the destination to be, then use MARK WAYMAP or USE BLANK WAYMAP.",
                "Marked Waymaps are individually numbered so multiple maps can point to different destinations.",
            )),
            ("Travel", (
                "WAYMAPS lists your maps. USE WAYMAP #<number> follows the shortest currently passable room route.",
                "STOP TRAVEL interrupts automated movement immediately.",
                "Waymap travel uses the real movement stack. Closed routes, gates, combat, and world changes can still matter.",
            )),
        ),
        aliases=("waymap", "autotravel", "auto travel"),
        see_also=("maps", "exploration", "crafting"),
    ),
    HelpTopic(
        "room-interactions",
        "Room Interactions",
        "exploration",
        "The shared language for examining and manipulating authored places.",
        (
            ("Core verbs", (
                "EXAMINE inspects. SEARCH looks through or around. LISTEN pays attention to sound. TOUCH tests a physical feature. READ handles written objects.",
                "PULL, TURN, CLIMB, OPEN, and other mechanical verbs appear when the room or an earlier clue makes them reasonable.",
            )),
            ("Context matters", (
                "The same word can have a local authored meaning in one room and a global convenience meaning elsewhere.",
                "The command-routing layer gives authored room interactions first refusal so a local puzzle or scene is not swallowed by a broad global command.",
            )),
        ),
        aliases=("interactions", "features", "details", "landmarks"),
        see_also=("exploration", "dungeons", "secrets", "help-here"),
    ),
    HelpTopic(
        "combat-basics",
        "Combat Basics",
        "combat",
        "The core real-time loop: engage, auto-attack, use abilities, react, survive, loot, repeat.",
        (
            ("Starting combat", (
                "CONSIDER <target> is safe reconnaissance. TARGET <name> selects without automatically attacking.",
                "ATTACK <target> or KILL <target> engages. Once engaged, auto-attacks continue on their timing while you issue other commands.",
            )),
            ("During combat", (
                "ABILITIES shows what your class can currently use. ABILITY <name> explains one ability in depth.",
                "USE <ability> and CAST <ability> invoke class actions. Some abilities require a target and some spells have interruptible cast timing.",
                "Telegraphed encounters can ask for reactions such as BRACE, COVER EARS, or STEP ASIDE.",
            )),
            ("Leaving combat", (
                "FLEE attempts to break away. Death uses the release and bind-point systems instead of deleting the character.",
            )),
        ),
        aliases=("combat", "fighting", "fight"),
        see_also=("targeting", "abilities", "death", "hunting", "stats"),
    ),
    HelpTopic(
        "targeting",
        "Targeting",
        "combat",
        "Selecting a player or enemy independently from starting combat.",
        (
            ("Selection", (
                "TARGET <name> selects a compatible visible target. TARGET with no argument reports the current selection.",
                "CLEAR TARGET or UNTARGET clears the selection.",
            )),
            ("Combat relationship", (
                "Selecting an enemy does not itself start a fight.",
                "ATTACK with no name can engage your selected enemy. Enemy-targeted abilities can also promote the selection into active combat when they resolve.",
            )),
        ),
        aliases=("target", "targets"),
        see_also=("combat-basics", "abilities", "party"),
    ),
    HelpTopic(
        "abilities",
        "Class Abilities",
        "character",
        "How to inspect, use, and master your fixed class kit.",
        (
            ("What you know", (
                "ABILITIES shows currently unlocked abilities. ABILITIES ALL shows the authored progression, including future level unlocks.",
                "ABILITY <name> shows the command form, resource cost, cooldown, mastery progress, current bonuses, and next mastery milestone.",
            )),
            ("Using abilities", (
                "USE and CAST are the general forms. Some signature low-level abilities also accept a direct convenience command.",
                "Healing and ally-protection abilities can require an explicit friendly target.",
            )),
            ("Mastery", (
                "Meaningful ability use builds skill mastery separately from character level.",
                "SKILLS or PROGRESS shows practiced ability mastery, XP bars, uses, and upcoming class progression.",
            )),
        ),
        aliases=("ability", "spells", "skills", "class abilities"),
        see_also=("classes", "progression", "combat-basics", "mana"),
    ),
    HelpTopic(
        "death",
        "Death, Release & Resurrection",
        "combat",
        "What happens when HP reaches zero and how recovery works.",
        (
            ("Death state", (
                "A fallen character can RELEASE to accept the normal release penalty and return to the persistent bind point.",
                "BIND shows the current bind point. Supported bind services can change it.",
            )),
            ("Resurrection", (
                "Priests with RESURRECT can return an unreleased fallen player without the normal release XP loss.",
                "Resurrection is a group utility, not a substitute for the ordinary solo release flow.",
            )),
        ),
        aliases=("release", "resurrection", "resurrect", "bind point"),
        see_also=("combat-basics", "health", "party"),
    ),
    HelpTopic(
        "hunting",
        "Hunting & Combat Grinding",
        "combat",
        "Sustained monster combat as a real progression path instead of a one-monster room novelty.",
        (
            ("Hunting grounds", (
                "HUNT or HUNT STATUS reads the current hunting ground and your combat momentum.",
                "Hunting areas can support multiple active enemies, respawn pressure, ecology effects, chain XP, material milestones, and rare predators.",
            )),
            ("Efficient grinding", (
                "CONSIDER before committing to unfamiliar enemies. Keep your recovery resources and escape route in mind.",
                "Loot is physical. Corpses and their drops remain part of the room loop instead of instantly teleporting rewards into inventory.",
            )),
        ),
        aliases=("hunt", "grinding", "grind", "combat grinding", "momentum"),
        see_also=("combat-basics", "corpses", "ecology", "progression"),
    ),
    HelpTopic(
        "stats",
        "Stats & Derived Values",
        "character",
        "The main character attributes and the systems they influence.",
        (
            ("Core attributes", (
                "Might drives auto-attack damage. Grace influences auto-attack speed. Love contributes to healing and mana. Mind contributes to spell power and mana.",
                "HP increases maximum health. Armor Class primarily comes from equipment and affects combat defenses according to the live combat rules.",
            )),
            ("Inspecting your character", (
                "SCORE, STATUS, SHEET, and STATS show the character overview and derived values.",
                "HEALTH or HP shows current health state. MANA shows current mana state. MOVEMENT shows endurance and fatigue.",
            )),
        ),
        aliases=("attributes", "might", "grace", "love", "mind", "hp stat", "armor class", "ac"),
        see_also=("health", "mana", "movement-points", "equipment", "progression"),
    ),
    HelpTopic(
        "health",
        "Health & Regeneration",
        "character",
        "Current HP, out-of-combat recovery, resting bonuses, and racial regeneration.",
        (
            ("Checking health", (
                "HEALTH or HP reports current and maximum HP alongside combat state.",
                "Health changes occur when the underlying event happens. Regeneration is not only a delayed text summary.",
            )),
            ("Recovery", (
                "Out-of-combat health regenerates over time. Resting improves recovery, and restful places can improve it further.",
                "Troll and Sporekin racial regeneration layers on top of the shared recovery system.",
            )),
        ),
        aliases=("hp", "regeneration", "regen", "healing"),
        see_also=("resting", "death", "racial-abilities", "combat-basics"),
    ),
    HelpTopic(
        "mana",
        "Mana",
        "character",
        "The resource used by many class abilities and spells.",
        (
            ("Capacity", (
                "Love and Mind both contribute to maximum mana in addition to the base class resource model.",
            )),
            ("Recovery and spending", (
                "Abilities can have mana costs and cooldowns. Resting improves mana recovery.",
                "ABILITY <name> is the best place to inspect the live cost and cooldown of a specific action.",
            )),
        ),
        aliases=("mp", "magic points"),
        see_also=("abilities", "stats", "resting"),
    ),
    HelpTopic(
        "movement-points",
        "Movement, Fatigue & Rest",
        "character",
        "Travel has an endurance layer separate from HP and mana.",
        (
            ("Movement points", (
                "MOVEMENT, MOVE POINTS, FATIGUE, or ENDURANCE shows current movement and the fatigue band.",
                "Normal travel spends movement according to the live movement system.",
            )),
            ("Resting", (
                "REST or SIT begins recovery when the local room does not own SIT for an authored interaction.",
                "STAND, STAND UP, or RISE ends resting. Restful locations recover more efficiently.",
            )),
        ),
        aliases=("movement", "fatigue", "endurance", "resting", "rest", "sit", "stand"),
        see_also=("exploration", "health", "mana"),
    ),
    HelpTopic(
        "progression",
        "Levels, XP & Mastery",
        "character",
        "Character level and ability mastery are related but separate progression tracks.",
        (
            ("Character level", (
                "Combat, authored quests, exploration systems, and other activities can award character XP.",
                "SCORE shows total XP and the next level threshold.",
            )),
            ("Ability mastery", (
                "Meaningful ability use builds per-ability mastery from novice toward grandmaster tiers.",
                "SKILLS, PROGRESS, and ABILITY <name> expose mastery progress without replacing class level progression.",
            )),
        ),
        aliases=("xp", "level", "levels", "mastery", "skill xp"),
        see_also=("abilities", "quests", "hunting", "classes"),
    ),
    HelpTopic(
        "races",
        "Races",
        "character",
        "The eight playable peoples are mechanically and culturally distinct without restricting class choice.",
        (
            ("Identity", (
                "Every race has authored culture, a starting experience, a passive identity, and an active racial command.",
                "LORE focuses on your own people's world identity. RACIAL shows your mechanical racial kit.",
            )),
            ("Class freedom", (
                "Every race can play every class. Race changes the opening, culture, reactions, and racial mechanics rather than locking class access.",
            )),
        ),
        aliases=("race", "peoples"),
        see_also=("racial-abilities", "classes", "lore"),
    ),
    HelpTopic(
        "classes",
        "Classes",
        "character",
        "Brute, Wizard, Druid, Priest, and Necromancer each have a fixed authored progression.",
        (
            ("Inspecting a class", (
                "CLASS shows role, known abilities, costs, cooldowns, and upcoming progression.",
                "ABILITIES and ABILITY <name> focus on actions you can actually use and master.",
            )),
            ("Design", (
                "Class identity deepens through authored ability unlocks rather than a talent-tree respec system.",
                "Priests additionally follow a deity path that changes their authored ability progression.",
            )),
        ),
        aliases=("class", "brute", "wizard", "druid", "priest", "necromancer"),
        see_also=("abilities", "progression", "combat-basics"),
    ),
    HelpTopic(
        "racial-abilities",
        "Racial Abilities",
        "character",
        "Each race has a passive identity and an active racial command.",
        (
            ("Finding yours", (
                "RACIAL shows the current character's passive, active ability, and cooldown information.",
                "The exact command differs by race. Examples include ADAPT, SLIPSTEP, RECONSIDER, BRACE, SCROUNGE, BLOODSCENT, STILLNESS, and CHORUS BLOOM.",
            )),
            ("Interaction with class", (
                "Racial mechanics are available to every class combination for that race and sit alongside, not inside, the class ability progression.",
            )),
        ),
        aliases=("racial", "racial ability", "racial passive"),
        see_also=("races", "classes", "abilities"),
    ),
    HelpTopic(
        "quests",
        "Quests & Objectives",
        "character",
        "Structured authored goals with persistent progress and explicit current objectives.",
        (
            ("Journal", (
                "QUESTS or JOURNAL shows active and completed quests.",
                "Active quests display their current objective. When a quest requires a specific parser verb, the objective should provide the exact command or a clear clue.",
            )),
            ("Relationship to exploration", (
                "Not every interesting thing is a quest. Secrets, optional rooms, living-world changes, hunting, trade, crafting, and social play can exist outside the journal.",
            )),
        ),
        aliases=("quest", "journal", "objectives"),
        see_also=("getting-started", "exploration", "secrets", "world"),
    ),
    HelpTopic(
        "lore",
        "Lore & Cultural Commands",
        "character",
        "Character-facing cultural information without requiring an external wiki.",
        (
            ("Personal lore", (
                "LORE explains your race and its authored identity.",
                "Some cultures expose additional commands for beliefs, home, government, ritual, social philosophy, or shared consciousness.",
            )),
            ("Discovery", (
                "The help system documents controls and systems. It intentionally does not flatten undiscovered world secrets into a lore checklist.",
            )),
        ),
        aliases=("culture", "cultural commands"),
        see_also=("races", "world", "secrets"),
    ),
    HelpTopic(
        "items",
        "Items & Inventory",
        "items",
        "How carried objects, equipment, ground items, loot, and special item history fit together.",
        (
            ("Carrying things", (
                "INVENTORY lists carried items and capacity. Bags use a real equipment slot and increase shared carrying capacity rather than creating nested container inventories.",
                "DROP leaves an item physically in the room. GET or TAKE picks up a ground item.",
            )),
            ("Inspect before acting", (
                "ITEM or INSPECT ITEM shows item metadata. COMPARE checks gear against the item in the compatible slot.",
                "PROVENANCE or HERITAGE exposes serialized history when an item is one of the tracked special or crafted objects.",
            )),
        ),
        aliases=("inventory", "item", "items"),
        see_also=("equipment", "corpses", "provenance", "style"),
    ),
    HelpTopic(
        "equipment",
        "Equipment",
        "items",
        "Combat gear is slot-aware and separate from cosmetic visual overrides.",
        (
            ("Core commands", (
                "EQUIPMENT, GEAR, or WORN shows equipped combat items.",
                "EQUIP, WEAR, or WIELD equips compatible gear. UNEQUIP or REMOVE takes it off. COMPARE evaluates a carried item against the same combat slot.",
            )),
            ("Slots matter", (
                "Items only fit their authored compatible slots. A hood does not become an off-hand item just because the parser can name it.",
                "Dedicated fashion and copied looks use the style system without replacing combat stats.",
            )),
        ),
        aliases=("gear", "worn", "equip", "wear", "wield"),
        see_also=("items", "style", "stats"),
    ),
    HelpTopic(
        "corpses",
        "Corpses & Physical Loot",
        "items",
        "Defeated enemies leave persistent room corpses with real loot state.",
        (
            ("Inspect", (
                "CORPSES lists remains in the room. LOOK CORPSE or EXAMINE CORPSE shows drops, protection state, and remaining loot.",
            )),
            ("Loot", (
                "LOOT CORPSE or LOOT <enemy> takes everything currently assigned or available to you.",
                "GET ALL FROM <corpse> and GET <item> FROM <corpse> provide explicit control. TAKE forms work too.",
            )),
            ("Group play", (
                "Party loot rules can affect who is assigned a drop. The corpse system preserves that ownership instead of bypassing it.",
            )),
        ),
        aliases=("corpse", "loot", "drops", "remains", "bodies"),
        see_also=("hunting", "party", "items"),
    ),
    HelpTopic(
        "provenance",
        "Item Provenance & Heritage",
        "items",
        "Tracked objects can carry maker marks, discovery editions, and ownership history.",
        (
            ("Crafted items", (
                "Crafted gear can carry a maker mark and craft record tied to the player who made it.",
                "Use PROVENANCE <item> or HERITAGE <item> to inspect tracked history.",
            )),
            ("Special discoveries", (
                "Selected special items can be serialized by discovery order so a copy can represent, for example, the fourth one ever found while the global count continues to grow.",
                "HISTORY <serial> reads the ownership chain when a serial is known.",
            )),
            ("Ordinary items", (
                "Not every object needs serialization. Ordinary anonymous items correctly report that they have no individual heritage.",
            )),
        ),
        aliases=("heritage", "maker mark", "serial", "item history"),
        see_also=("items", "crafting", "collections"),
    ),
    HelpTopic(
        "gathering",
        "Gathering",
        "crafting",
        "Mining, Harvesting, Herbalism, and authored local resource interactions feed the material economy.",
        (
            ("Find resources", (
                "RESOURCES and STATIONS show visible gatherables and crafting facilities in the current room.",
                "GATHER <resource> is the shared generic form. MINE, HARVEST, and HERBALISM use their profession-specific routes.",
            )),
            ("Progression", (
                "MINING, HARVESTING, or HERBALISM with no target shows that skill's tier, progress, next milestone, and useful local information.",
                "Regional ecology and authored tutorial interactions can change what is available without turning gathering into a static vending machine.",
            )),
        ),
        aliases=("gather", "mining", "harvesting", "herbalism", "resources"),
        see_also=("crafting", "ecology", "economy"),
    ),
    HelpTopic(
        "crafting",
        "Crafting & Recipes",
        "crafting",
        "Blacksmithing, Tailoring, Enchanting, Cooking, Alchemy branches, and profession workshops.",
        (
            ("Recipe book", (
                "RECIPES opens the concise recipe book. Filters include profession, READY, CRAFTABLE, and ALL.",
                "RECIPE <name> shows skill, station, ingredients, owned quantities, description, and current craft readiness.",
                "NEEDS <item or recipe> focuses on missing materials and source hints.",
            )),
            ("Making things", (
                "CRAFT <recipe> uses real inventory materials at the required station.",
                "FORGE, TAILOR or SEW, ENCHANT, and COOK provide profession-specific workshop flows.",
            )),
            ("Profession sheet", (
                "PROFESSIONS or TRADESKILLS shows skill bars, tiers, recipe counts, and upcoming milestones.",
            )),
        ),
        aliases=("recipes", "recipe", "professions", "tradeskills", "craft"),
        see_also=("gathering", "economy", "provenance", "food-and-potions"),
    ),
    HelpTopic(
        "food-and-potions",
        "Food, Potions & Fragrances",
        "crafting",
        "Consumables use physical inventory and can provide restorative or temporary effects.",
        (
            ("Food", (
                "FOOD lists carried prepared food. EAT <food> consumes it and applies its authored restorative or nourishment effect.",
            )),
            ("Potions", (
                "POTIONS lists carried alchemical drinks. DRINK <potion> consumes one for its authored effect.",
            )),
            ("Fragrance", (
                "Fragrances belong to the style/perfumery ecosystem. APPLY FRAGRANCE activates one scent at a time, and SCENT shows its remaining duration and bonus details.",
            )),
        ),
        aliases=("food", "potions", "potion", "consume"),
        see_also=("crafting", "style", "health"),
    ),
    HelpTopic(
        "economy",
        "Sols, Merchants & Value",
        "economy",
        "The ordinary currency loop connects hunting, gathering, crafting, shops, and civic demand.",
        (
            ("Currency", (
                "SOLS, COINS, or MONEY shows the Sol balance in sparks, embers, and flames.",
                "SHOP, LIST, or WARES shows nearby merchant stock. BUY purchases and SELL sells eligible carried items.",
                "VALUE <item> asks a nearby merchant what they would currently pay.",
            )),
            ("The loop", (
                "ECONOMY or ECONOMY ROUTE explains the intended hunt-gather-craft-trade loop and a starter route through it.",
            )),
        ),
        aliases=("sols", "coins", "money", "merchant", "shop", "buy", "sell"),
        see_also=("trade", "gathering", "crafting", "veyra"),
    ),
    HelpTopic(
        "trade",
        "Player Trade",
        "economy",
        "Direct gifts and a confirmation-based two-sided trade flow.",
        (
            ("Direct transfer", (
                "GIVE <player> [qty] <item> transfers a tradeable item to a nearby player.",
            )),
            ("Safe trade", (
                "TRADE <player> starts the two-sided flow. TRADE ADD and TRADE REMOVE edit your offer.",
                "TRADE STATUS shows the current state. TRADE CONFIRM locks your current view of the offer; both players must confirm the same state.",
                "Any offer change resets confirmation. TRADE CANCEL exits safely.",
            )),
        ),
        aliases=("player trade", "trading", "give"),
        see_also=("economy", "party", "provenance"),
    ),
    HelpTopic(
        "veyra",
        "Veyra Services",
        "economy",
        "The major shared city has storage, player barter, training, civic demand, contracts, factions, and travel services.",
        (
            ("Storage and market", (
                "VAULT, DEPOSIT, and WITHDRAW operate Keyhouse storage where available.",
                "MARKET browses barter listings. LIST <qty> <item> FOR <qty> <item>, FILL <listing id>, and CANCEL LISTING <id> operate the escrow market.",
            )),
            ("Civic systems", (
                "MARKET DAY or DEMAND shows rotating civic material demand. CONTRACT commands manage weekly civic material work.",
                "FACTION STATUS, FACTION DUTY, and FACTION PROMOTE handle deeper Veyra service progression.",
            )),
        ),
        aliases=("city", "city services", "veyra city"),
        see_also=("economy", "factions", "world"),
    ),
    HelpTopic(
        "communication",
        "Communication",
        "social",
        "Room speech, global channels, private messages, contacts, and blocking.",
        (
            ("Immediate speech", (
                "SAY speaks to the current room. CHAT and OOC use built-in world channels.",
                "TELL <name> <message> sends a private message to an online character. REPLY answers the most recent private sender.",
            )),
            ("Control", (
                "CHANNEL CHAT ON|OFF and CHANNEL OOC ON|OFF control reception of built-in global channels.",
                "FRIENDS, FRIEND, and UNFRIEND manage contacts. IGNORES, IGNORE, and UNIGNORE block another character's supported communication.",
            )),
        ),
        aliases=("chat", "say", "tell", "reply", "friends", "ignore"),
        see_also=("custom-channels", "mail", "social-play"),
    ),
    HelpTopic(
        "custom-channels",
        "Player-Created Channels",
        "social",
        "Persistent public or private chat spaces created and moderated by players.",
        (
            ("Discover and join", (
                "CHANNELS or CHANNEL LIST opens the channel screen. CHANNEL INFO <name> inspects one channel.",
                "CHANNEL CREATE <name>, CHANNEL JOIN <name>, and CHANNEL LEAVE <name> manage membership.",
            )),
            ("Speak", (
                "CHANNEL <name> <message> speaks in a joined channel.",
                "#<channel> <message> is the compact shortcut.",
            )),
            ("Owner moderation", (
                "Owners can INVITE, KICK, MUTE, UNMUTE, switch PUBLIC or PRIVATE state, RENAME, and CLOSE a channel.",
                "CHANNEL CLOSE requires confirmation so a mistyped command cannot casually destroy the space.",
            )),
        ),
        aliases=("channels", "channel", "player channels", "custom chat"),
        see_also=("communication", "mail", "social-play"),
    ),
    HelpTopic(
        "mail",
        "Persistent Mail",
        "social",
        "Letters that survive logout and can reach offline characters.",
        (
            ("Inbox", (
                "MAIL, POST, or INBOX lists letters. Unread messages are marked.",
                "MAIL READ <number> reads a letter and marks it read.",
            )),
            ("Send and clean up", (
                "MAIL SEND <player> enters the persistent mail composition flow.",
                "MAIL DELETE <number> soft-deletes one letter. MAIL CLEAR READ and MAIL CLEAR ALL are bulk cleanup commands with confirmation.",
            )),
        ),
        aliases=("post", "inbox", "letters"),
        see_also=("communication", "custom-channels", "world"),
    ),
    HelpTopic(
        "social-play",
        "Social Play & Pastimes",
        "social",
        "Low-stakes interaction that is not combat, progression pressure, or a required quest.",
        (
            ("Emotes and taverns", (
                "WAVE, NOD, SMILE, LAUGH, BOW, SHRUG, and CHEER are lightweight room emotes.",
                "TAVERN is a cross-hearth social channel where the living-world layer exposes it.",
            )),
            ("Pastimes", (
                "PASTIMES or GAMES shows organized local activities such as Three Bones, arm wrestling, knife throwing, riddles, guessing jars, drinking rounds, and performances where present.",
                "KEEPSAKES or TROPHIES reviews statless social mementos.",
            )),
        ),
        aliases=("pastimes", "games", "emotes", "tavern"),
        see_also=("communication", "party", "world"),
    ),
    HelpTopic(
        "party",
        "Parties & Group Play",
        "party",
        "A persistent group-control layer for shared movement, combat coordination, and loot.",
        (
            ("Forming a party", (
                "PARTY INVITE <player> invites a nearby character. PARTY ACCEPT or PARTY DECLINE answers.",
                "PARTY LEAVE exits. Leaders can PARTY KICK and transfer PARTY LEADER.",
            )),
            ("Coordination", (
                "PARTY SAY is private group chat. PARTY FOLLOW controls movement following.",
                "ASSIST joins a party member's active target. FOCUS calls a shared target. READY CHECK coordinates encounter starts.",
                "PARTY HUD or COHESION shows compact group state and separation.",
            )),
            ("Loot", (
                "PARTY LOOT commands inspect or change supported assignment rules. Physical corpse loot honors the active group rules.",
            )),
        ),
        aliases=("group", "groups", "party system", "cohesion"),
        see_also=("combat-basics", "corpses", "dungeons", "communication"),
    ),
    HelpTopic(
        "world",
        "The Living World",
        "world",
        "Astralis continues to express time, weather, ecology, public history, recurring people, and regional state through ordinary play.",
        (
            ("Time and conditions", (
                "TIME, DATE, CALENDAR, TODAY, SEASON, and WEATHER expose the shared world clock and current conditions.",
                "The calendar and weather can affect presentation, travel texture, encounters, ecology, and authored interactions.",
            )),
            ("Public memory", (
                "GOSSIP or RUMOR surfaces current texture. CHRONICLE or HISTORY reads persistent public history and recorded firsts.",
                "LOCALS shows recurring living-world people currently present where supported.",
            )),
        ),
        aliases=("living world", "astralis", "time", "calendar", "weather"),
        see_also=("ecology", "factions", "quests", "exploration"),
    ),
    HelpTopic(
        "ecology",
        "Ecology & Signs of the Land",
        "world",
        "Outdoor regions have persistent ecological pressure, wildlife signs, resources, and migration state.",
        (
            ("Reading the land", (
                "TRACKS, WILDLIFE, READ LAND, CONDITIONS, or ECOLOGY gives a deeper local read when the room is ecological.",
                "Built-up or enclosed rooms may correctly have no useful ecological reading.",
            )),
            ("Why it matters", (
                "Ecology can influence ambient signs, resource pressure, regional mobile populations, migration routes, and sustained hunting texture.",
                "The interface stays descriptive rather than exposing raw simulation numbers.",
            )),
        ),
        aliases=("tracks", "wildlife", "read land", "conditions"),
        see_also=("hunting", "gathering", "world"),
    ),
    HelpTopic(
        "factions",
        "Factions, Standing & Renown",
        "world",
        "Persistent social memory records how groups regard a character and how widely the character is known.",
        (
            ("Inspecting reputation", (
                "REPUTATION, REP, STANDING, or FACTIONS shows the persistent faction view.",
            )),
            ("What changes it", (
                "Quest deeds, allied or rival word-of-mouth, civic service, NPC reactions, and local merchant treatment can share the same reputation layer.",
                "Standing is not identical to renown: being widely known and being well liked are separate ideas.",
            )),
        ),
        aliases=("reputation", "rep", "standing", "renown"),
        see_also=("world", "veyra", "quests", "economy"),
    ),
    HelpTopic(
        "dungeons",
        "Dungeons & Encounter Mechanics",
        "adventure",
        "Authored dungeons combine combat with readable environmental mechanics and cooperative interactions.",
        (
            ("Read before acting", (
                "LOOK, EXAMINE, LISTEN, and IMPRESSION often tell you more than immediately attacking or spamming verbs.",
                "Major mechanics use telegraphed verbs such as HOLD SEAL, CROSS PISTONS, SET INTAKE VALVE, PULL HOUND, TOUCH PLATE, or PULL RESONATOR only where their dungeon actually supports them.",
            )),
            ("Group awareness", (
                "PARTY HUD, READY CHECK, FOCUS, and ASSIST make multi-player mechanics easier to coordinate.",
                "Dungeon help explains control grammar but avoids publishing step-by-step solutions to undiscovered puzzles.",
            )),
        ),
        aliases=("dungeon", "boss mechanics", "encounters"),
        see_also=("party", "combat-basics", "room-interactions", "secrets"),
    ),
    HelpTopic(
        "secrets",
        "Secrets & Mysteries",
        "adventure",
        "How optional discoveries are surfaced without converting the world into a spoiler checklist.",
        (
            ("Clue language", (
                "Secrets are expected to have fiction-facing clues: a visible ditch, an odd sound, an inconsistent object, weather-dependent detail, repeated rumor, physical mark, or another observable reason to investigate.",
                "SEARCH, LISTEN, EXAMINE, TOUCH, READ, and other local verbs matter when the scene gives you a reason to try them.",
            )),
            ("Spoiler policy", (
                "SECRETS or MYSTERIES can show limited spoiler-light progress in supported adventure content without naming every missing location.",
                "The discovery engine deliberately avoids a global completion percentage or omniscient hidden-room checklist.",
            )),
        ),
        aliases=("secret", "mysteries", "discovery", "hidden"),
        see_also=("exploration", "room-interactions", "dungeons", "maps"),
    ),
    HelpTopic(
        "style",
        "Style, Wardrobe & Fragrance",
        "style",
        "Visual identity is separate from combat equipment and includes permanent copied looks and scent.",
        (
            ("Wardrobe", (
                "STYLE, WARDROBE, OUTFIT, or FASHION shows cosmetic overrides and saved looks.",
                "STYLE WEAR equips a compatible visual look without changing combat gear. STYLE REMOVE clears one override.",
            )),
            ("Atelier and boutique", (
                "ATELIER opens Pavo Vellum's style-copy service where available. STYLE COPY preserves an ordinary equipment look without consuming the source or copying its stats.",
                "BOUTIQUE and BUY STYLE purchase authored fashion. COLLECTION tracks discovered style and fragrance items.",
            )),
            ("Fragrance", (
                "FRAGRANCES lists bottles. APPLY FRAGRANCE consumes one and activates its timed authored bonus. SCENT shows the active fragrance.",
            )),
        ),
        aliases=("wardrobe", "outfit", "fashion", "fragrance", "perfume"),
        see_also=("equipment", "collections", "support"),
    ),
    HelpTopic(
        "collections",
        "Collections & Keepsakes",
        "style",
        "A place for statless social trophies, fashion discovery, fragrances, heritage pieces, and seasonal presentation.",
        (
            ("Style collection", (
                "COLLECTION shows discovered fashion and fragrance counts by rarity. Consumed fragrance bottles remain discovered.",
                "SEASONAL STYLE shows the current limited seasonal edition and how it is earned.",
            )),
            ("Social keepsakes", (
                "KEEPSAKES or TROPHIES shows statless objects earned from social pastimes.",
            )),
        ),
        aliases=("collection", "keepsakes", "trophies", "seasonal style"),
        see_also=("style", "provenance", "social-play"),
    ),
    HelpTopic(
        "settings",
        "Settings",
        "settings",
        "Persistent presentation and accessibility preferences.",
        (
            ("Prompt and guidance", (
                "SETTINGS or PREFERENCES opens the unified settings screen.",
                "PROMPT QUIET, COMPACT, or FULL controls prompt density. SET HINTS OFF, GENTLE, or FULL controls automatic guidance.",
            )),
            ("Visual output", (
                "SET COLOR AUTO|ON|OFF controls ANSI color. SET CONTRAST STANDARD|HIGH controls contrast.",
                "SET SCREENREADER ON|OFF switches to plain output, quiet prompts, no ANSI, and no server-supplied HUD state.",
            )),
            ("Client integration", (
                "SET MUDLET ON|OFF controls server-supplied Mudlet HUD and GMCP enhancements.",
                "SETTINGS RESET restores recommended defaults.",
            )),
        ),
        aliases=("preferences", "accessibility", "screenreader", "screen reader", "mudlet", "prompt", "color", "contrast", "hints"),
        see_also=("help-system", "getting-started"),
    ),
    HelpTopic(
        "support",
        "Voting, Echoes & Community Support",
        "support",
        "Account-wide support rewards are cosmetic and kept separate from the ordinary Sol economy.",
        (
            ("Voting", (
                "VOTE shows the MUDVerse voting link and arms an account-wide vote claim.",
                "VOTE CLAIM checks a pending vote and claims the available daily reward.",
            )),
            ("Echoes of Favour", (
                "ECHOES shows your Echo balance and active presentation rewards.",
                "ECHOES SHOP and ECHOES BUY browse and unlock cosmetic rewards.",
                "TITLES, TITLE SET, TITLE CLEAR, COSMETICS, COSMETIC SET, and COSMETIC CLEAR manage unlocked presentation choices.",
            )),
        ),
        aliases=("vote", "voting", "echoes", "echoes of favour", "echoes of favor", "titles", "cosmetics"),
        see_also=("style", "collections"),
    ),
    HelpTopic(
        "help-system",
        "Using the Help Library",
        "reference",
        "The help system is a navigable in-game manual rather than one giant command dump.",
        (
            ("Core navigation", (
                "HELP opens the library home. HELP <topic> opens a conceptual topic or category.",
                "HELP COMMAND <name> opens documentation for one command family.",
                "HELP SEARCH <word or phrase> searches topics, aliases, keywords, syntax, and command descriptions.",
                "HELP INDEX shows an alphabetical topic index. HELP CATEGORIES shows the category map.",
            )),
            ("Command catalog", (
                "COMMANDS remains the concise command catalog. COMMANDS <category> and COMMAND SEARCH <word> are fast command-only views.",
                "HELP CATALOG prints the complete categorized command family list for deep browsing.",
            )),
            ("Rabbit holes", (
                "Every topic ends with related topics. Every cataloged command can produce a help page even when it does not have a hand-written concept page.",
                "That means adding a command to the canonical catalog automatically makes it discoverable through HELP COMMAND and HELP SEARCH.",
            )),
        ),
        aliases=("help", "help library", "help menu", "manual", "guide"),
        see_also=("help-here", "command-reference", "getting-started"),
    ),
    HelpTopic(
        "help-here",
        "Contextual Help",
        "reference",
        "A small situational command list for the room and state you are in right now.",
        (
            ("Purpose", (
                "HELP HERE or SUGGEST is intentionally short. It answers 'what is useful here?' instead of printing the full manual.",
                "It can account for room features, combat state, carried waymaps, local services, region-specific mechanics, and nearby authored content.",
            )),
            ("When to use something else", (
                "Use HELP SEARCH when you remember an idea but not a command.",
                "Use HELP CATALOG or COMMANDS ALL when you want exhaustive browsing.",
            )),
        ),
        aliases=("suggest", "suggestions", "what can i do", "what can i do here"),
        see_also=("help-system", "exploration", "getting-started"),
    ),
    HelpTopic(
        "command-reference",
        "Command Reference",
        "reference",
        "The canonical catalog of player-facing command families and aliases.",
        (
            ("Browse", (
                "HELP CATALOG prints the catalog grouped by category.",
                "COMMANDS shows the compact command categories. COMMANDS ALL prints the full command catalog.",
            )),
            ("Search", (
                "HELP COMMAND <name> is best when you know the command.",
                "HELP SEARCH <phrase> searches both conceptual help and command documentation.",
                "COMMAND SEARCH <word> searches command syntax and descriptions only.",
            )),
        ),
        aliases=("commands", "command catalog", "catalog", "command guide"),
        see_also=("help-system", "help-here"),
    ),
)


EXTRA_COMMANDS: tuple[CommandEntry, ...] = (
    CommandEntry("world", "TRACKS / WILDLIFE / READ LAND / CONDITIONS / ECOLOGY", "Read descriptive local ecology, wildlife pressure, and signs of the land.", ("environment", "nature", "migration")),
    CommandEntry("world", "REPUTATION / REP / STANDING / FACTIONS", "Show persistent faction standing and renown.", ("reputation", "renown", "faction")),
    CommandEntry("social", "CHANNELS / CHANNEL LIST / CHANNEL HELP", "List built-in and player-created communication channels and membership state.", ("custom channel", "chat")),
    CommandEntry("social", "CHANNEL CREATE <name> / CHANNEL JOIN <name> / CHANNEL LEAVE <name>", "Create, join, or leave a player-created channel.", ("custom channel", "chat")),
    CommandEntry("social", "CHANNEL INFO <name>", "Inspect a player-created channel's visibility, owner, and membership information.", ("custom channel", "chat")),
    CommandEntry("social", "CHANNEL <name> <message> / #<name> <message>", "Speak in a joined player-created channel.", ("custom channel", "chat")),
    CommandEntry("social", "CHANNEL INVITE / KICK / MUTE / UNMUTE <name> <player>", "Use owner moderation controls on a player-created channel.", ("custom channel", "moderation")),
    CommandEntry("social", "CHANNEL SET <name> PUBLIC|PRIVATE / CHANNEL PRIVATE <name> ON|OFF", "Change a player-created channel's visibility when you own it.", ("custom channel", "privacy")),
    CommandEntry("social", "CHANNEL RENAME <old> <new> / CHANNEL CLOSE <name>", "Rename or safely close a player-created channel you own.", ("custom channel", "moderation")),
    CommandEntry("items", "HISTORY <serial>", "Read the recorded ownership chain for a serialized tracked item.", ("provenance", "heritage", "serial")),
    CommandEntry("support", "VOTE / VOTE CLAIM", "Open the MUDVerse support flow or claim an eligible account-wide daily vote reward.", ("mudverse", "support", "echoes")),
    CommandEntry("support", "ECHOES / ECHOES SHOP / ECHOES BUY <name>", "Inspect or spend Echoes of Favour on unlocked cosmetic presentation rewards.", ("favour", "favor", "cosmetic")),
    CommandEntry("support", "TITLES / TITLE SET <name> / TITLE CLEAR", "Manage an unlocked displayed title.", ("echoes", "cosmetic", "title")),
    CommandEntry("support", "COSMETICS / COSMETIC SET <name> / COSMETIC CLEAR AURA|SIGIL", "Manage unlocked Echo aura and sigil presentation.", ("echoes", "aura", "sigil")),
)


CATEGORY_TOPIC_ORDER: dict[str, tuple[str, ...]] = {
    "start": ("getting-started",),
    "exploration": ("exploration", "maps", "waymaps", "room-interactions"),
    "combat": ("combat-basics", "targeting", "death", "hunting"),
    "character": ("stats", "health", "mana", "movement-points", "progression", "abilities", "races", "classes", "racial-abilities", "quests", "lore"),
    "items": ("items", "equipment", "corpses", "provenance"),
    "crafting": ("gathering", "crafting", "food-and-potions"),
    "economy": ("economy", "trade", "veyra"),
    "social": ("communication", "custom-channels", "mail", "social-play"),
    "party": ("party",),
    "world": ("world", "ecology", "factions"),
    "adventure": ("dungeons", "secrets"),
    "style": ("style", "collections"),
    "settings": ("settings",),
    "support": ("support",),
    "reference": ("help-system", "help-here", "command-reference"),
}


CATEGORY_COMMAND_MAP: dict[str, tuple[str, ...]] = {
    "start": ("basics",),
    "exploration": ("basics",),
    "combat": ("combat",),
    "character": ("character",),
    "items": ("character", "style"),
    "crafting": ("economy",),
    "economy": ("economy", "veyra"),
    "social": ("social", "world", "pastimes"),
    "party": ("party",),
    "world": ("world", "veyra"),
    "adventure": ("dungeons",),
    "style": ("style", "pastimes"),
    "settings": ("basics",),
    "support": ("support",),
    "reference": (),
}


COMMAND_EXAMPLES: dict[str, tuple[str, ...]] = {
    "look": ("LOOK", "LOOK AT RUSKLE"),
    "exits": ("EXITS",),
    "map": ("MAP", "MAP 3"),
    "examine": ("EXAMINE WAYSTONE",),
    "search": ("SEARCH DITCH",),
    "listen": ("LISTEN", "LISTEN TO BELL"),
    "target": ("TARGET MIRE LIZARD", "CLEAR TARGET"),
    "attack": ("CONSIDER MIRE LIZARD", "ATTACK MIRE LIZARD"),
    "use": ("USE TAUNT",),
    "cast": ("CAST MINOR HEAL PRIME",),
    "inventory": ("INVENTORY",),
    "equip": ("EQUIP REED BOOTS",),
    "compare": ("COMPARE REED BOOTS",),
    "loot corpse": ("LOOK CORPSE", "LOOT CORPSE"),
    "recipes": ("RECIPES", "RECIPES CRAFTABLE"),
    "recipe": ("RECIPE BLANK WAYMAP",),
    "craft": ("CRAFT BLANK WAYMAP",),
    "sols": ("SOLS",),
    "shop": ("SHOP", "VALUE REED BOOTS"),
    "trade": ("TRADE PRIME", "TRADE STATUS"),
    "say": ("SAY Anyone heading toward Waymeet?",),
    "tell": ("TELL PRIME Want to group?",),
    "party invite": ("PARTY INVITE PRIME",),
    "party hud": ("PARTY HUD",),
    "mail": ("MAIL", "MAIL READ 1"),
    "channel": ("CHANNELS", "#traders Anyone selling iron?"),
    "reputation": ("REPUTATION",),
    "tracks": ("TRACKS",),
    "vote": ("VOTE", "VOTE CLAIM"),
    "provenance": ("PROVENANCE BRIAR-EYE CHARM",),
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _register_extra_commands() -> None:
    existing = {entry.syntax.casefold() for entry in command_guide.COMMANDS}
    additions = tuple(entry for entry in EXTRA_COMMANDS if entry.syntax.casefold() not in existing)
    if additions:
        command_guide.COMMANDS = command_guide.COMMANDS + additions
    command_guide.CATEGORIES = tuple(dict.fromkeys(entry.category for entry in command_guide.COMMANDS))


def _topic_maps() -> tuple[dict[str, HelpTopic], dict[str, str]]:
    by_key = {topic.key: topic for topic in TOPICS}
    aliases: dict[str, str] = {}
    for topic in TOPICS:
        for alias in (topic.key, topic.title, *topic.aliases):
            aliases[_normalize(alias)] = topic.key
    return by_key, aliases


TOPICS_BY_KEY, TOPIC_ALIASES = _topic_maps()


def _clean_syntax_fragment(fragment: str) -> str:
    value = fragment.strip()
    for marker in ("<", "[", "..."):
        index = value.find(marker)
        if index >= 0:
            value = value[:index].strip()
    value = value.replace("|", " ")
    return _normalize(value)


def _command_aliases(entry: CommandEntry) -> tuple[str, ...]:
    values: list[str] = []
    for fragment in entry.syntax.split("/"):
        clean = _clean_syntax_fragment(fragment)
        if clean and clean not in values:
            values.append(clean)
    if values:
        first = values[0]
        first_word = first.split(maxsplit=1)[0]
        if first_word and first_word not in values:
            values.append(first_word)
    return tuple(values)


def _find_exact_commands(query: str) -> list[CommandEntry]:
    wanted = _normalize(query)
    if not wanted:
        return []
    exact: list[CommandEntry] = []
    for entry in command_guide.COMMANDS:
        if wanted in _command_aliases(entry):
            exact.append(entry)
    return exact


def _search_commands(query: str) -> list[CommandEntry]:
    wanted = _normalize(query)
    if not wanted:
        return []
    rows: list[tuple[int, CommandEntry]] = []
    for entry in command_guide.COMMANDS:
        aliases = _command_aliases(entry)
        haystack = _normalize(" ".join((entry.category, entry.syntax, entry.description, *entry.keywords)))
        score = 0
        if wanted in aliases:
            score += 100
        if any(alias.startswith(wanted) for alias in aliases):
            score += 40
        if wanted in _normalize(entry.syntax):
            score += 30
        if wanted in haystack:
            score += 10
        if score:
            rows.append((score, entry))
    rows.sort(key=lambda pair: (-pair[0], pair[1].category, pair[1].syntax))
    return [entry for _, entry in rows]


def _search_topics(query: str) -> list[HelpTopic]:
    wanted = _normalize(query)
    if not wanted:
        return []
    rows: list[tuple[int, HelpTopic]] = []
    for topic in TOPICS:
        aliases = tuple(_normalize(value) for value in (topic.key, topic.title, *topic.aliases))
        body = " ".join(line for _, lines in topic.sections for line in lines)
        haystack = _normalize(" ".join((topic.category, topic.summary, body, *topic.keywords, *aliases)))
        score = 0
        if wanted in aliases:
            score += 100
        if any(alias.startswith(wanted) for alias in aliases):
            score += 40
        if wanted in haystack:
            score += 10
        if score:
            rows.append((score, topic))
    rows.sort(key=lambda pair: (-pair[0], pair[1].title))
    return [topic for _, topic in rows]


def _topic_label(key: str) -> str:
    topic = TOPICS_BY_KEY.get(key)
    return topic.title if topic else key.replace("-", " ").title()


def _topic_command_rows(topic: HelpTopic) -> list[CommandEntry]:
    command_categories = CATEGORY_COMMAND_MAP.get(topic.category, ())
    keywords = {_normalize(topic.key), *(_normalize(alias) for alias in topic.aliases), *(_normalize(word) for word in topic.keywords)}
    rows: list[CommandEntry] = []
    for entry in command_guide.COMMANDS:
        aliases = set(_command_aliases(entry))
        haystack = _normalize(" ".join((entry.syntax, entry.description, *entry.keywords)))
        relevant = entry.category in command_categories and (
            any(keyword and keyword in haystack for keyword in keywords)
            or any(alias in keywords for alias in aliases)
        )
        if relevant and entry not in rows:
            rows.append(entry)
    return rows[:12]


async def _show_home(session) -> None:
    await session.send("\r\n=== Dreams of the Fallen Help Library ===\r\n")
    await session.send("A deep in-game manual. Browse by system, search by idea, or open one command directly.\r\n\r\n")
    for key, (title, summary) in CATEGORY_INFO.items():
        topics = CATEGORY_TOPIC_ORDER.get(key, ())
        await session.send(f"{title:<28} HELP {key.upper():<12} {len(topics):>2} topic(s) - {summary}\r\n")
    await session.send(
        "\r\nNavigation: HELP <topic> | HELP COMMAND <command> | HELP SEARCH <words> | "
        "HELP INDEX | HELP CATALOG | HELP HERE\r\n"
    )
    await session.send("Try HELP GETTING STARTED if you want a guided first-session path.\r\n")


async def _show_categories(session) -> None:
    await session.send("\r\n=== Help Categories ===\r\n")
    for key, (title, summary) in CATEGORY_INFO.items():
        await session.send(f"{key.upper():<12} {title}\r\n  {summary}\r\n")


async def _show_category(session, category: str) -> None:
    key = _normalize(category).replace(" ", "-")
    if key not in CATEGORY_INFO:
        await session.send("Unknown help category. Type HELP CATEGORIES to browse the library.\r\n")
        return
    title, summary = CATEGORY_INFO[key]
    await session.send(f"\r\n=== {title} ===\r\n{summary}\r\n")
    topics = CATEGORY_TOPIC_ORDER.get(key, ())
    if topics:
        await session.send("\r\nTopics:\r\n")
        for topic_key in topics:
            topic = TOPICS_BY_KEY[topic_key]
            await session.send(f"  HELP {topic.key.upper():<22} {topic.summary}\r\n")

    command_categories = CATEGORY_COMMAND_MAP.get(key, ())
    rows = [entry for entry in command_guide.COMMANDS if entry.category in command_categories]
    if rows:
        await session.send(f"\r\nCommand families in this area: {len(rows)}. Use HELP CATALOG for the full list.\r\n")
        for entry in rows[:10]:
            await session.send(f"  {entry.syntax} - {entry.description}\r\n")
        if len(rows) > 10:
            await session.send(f"  ...and {len(rows) - 10} more.\r\n")


async def _show_topic(session, topic: HelpTopic) -> None:
    await session.send(f"\r\n=== {topic.title} ===\r\n")
    await session.send(topic.summary + "\r\n")
    for heading, lines in topic.sections:
        await session.send(f"\r\n[{heading}]\r\n")
        for line in lines:
            await session.send(line + "\r\n")

    rows = _topic_command_rows(topic)
    if rows:
        await session.send("\r\n[Useful command families]\r\n")
        for entry in rows:
            await session.send(f"{entry.syntax} - {entry.description}\r\n")

    if topic.see_also:
        related = ", ".join(f"HELP {_topic_label(key).upper()}" for key in topic.see_also)
        await session.send(f"\r\nSee also: {related}\r\n")


def _example_key(entry: CommandEntry) -> str:
    aliases = _command_aliases(entry)
    return aliases[0] if aliases else _normalize(entry.syntax)


def _related_topics_for_command(entry: CommandEntry) -> tuple[str, ...]:
    mapping = {
        "basics": ("getting-started", "exploration", "help-system"),
        "character": ("items", "progression", "stats"),
        "combat": ("combat-basics", "hunting", "corpses"),
        "social": ("communication", "custom-channels", "social-play"),
        "party": ("party", "combat-basics"),
        "economy": ("economy", "crafting", "trade"),
        "world": ("world", "ecology", "factions"),
        "veyra": ("veyra", "economy"),
        "dungeons": ("dungeons", "secrets"),
        "pastimes": ("social-play", "collections"),
        "style": ("style", "collections"),
        "items": ("items", "provenance"),
        "support": ("support", "style"),
    }
    return mapping.get(entry.category, ("command-reference",))


async def _show_command(session, entry: CommandEntry) -> None:
    await session.send(f"\r\n=== Command Help: {entry.syntax} ===\r\n")
    await session.send(f"Category: {entry.category}\r\n")
    await session.send(f"Purpose : {entry.description}\r\n")
    aliases = _command_aliases(entry)
    if aliases:
        await session.send("Aliases : " + ", ".join(alias.upper() for alias in aliases) + "\r\n")
    if entry.keywords:
        await session.send("Search  : " + ", ".join(entry.keywords) + "\r\n")
    examples = COMMAND_EXAMPLES.get(_example_key(entry), ())
    if examples:
        await session.send("\r\nExamples:\r\n")
        for example in examples:
            await session.send(f"  {example}\r\n")
    related = _related_topics_for_command(entry)
    await session.send("\r\nRelated: " + ", ".join(f"HELP {_topic_label(key).upper()}" for key in related) + "\r\n")


async def _show_command_query(session, query: str) -> None:
    rows = _find_exact_commands(query)
    if not rows:
        rows = _search_commands(query)
    if not rows:
        await session.send(f"No cataloged command matched '{query}'. Try HELP SEARCH {query}.\r\n")
        return
    if len(rows) == 1:
        await _show_command(session, rows[0])
        return
    await session.send(f"\r\n=== Command Matches: {query} ===\r\n")
    for entry in rows[:20]:
        await session.send(f"[{entry.category}] {entry.syntax} - {entry.description}\r\n")
    await session.send("Use HELP COMMAND followed by a more specific command phrase to open one page.\r\n")


async def _show_search(session, query: str) -> None:
    wanted = query.strip()
    if not wanted:
        await session.send("Use HELP SEARCH <word or phrase>.\r\n")
        return
    topics = _search_topics(wanted)
    commands = _search_commands(wanted)
    await session.send(f"\r\n=== Help Search: {wanted} ===\r\n")
    if not topics and not commands:
        await session.send("No help topic or command family matched. Try a broader term or HELP INDEX.\r\n")
        return
    if topics:
        await session.send("\r\nTopics:\r\n")
        for topic in topics[:12]:
            await session.send(f"  HELP {topic.key.upper():<22} {topic.summary}\r\n")
    if commands:
        await session.send("\r\nCommands:\r\n")
        for entry in commands[:20]:
            await session.send(f"  [{entry.category}] {entry.syntax} - {entry.description}\r\n")
    if len(topics) > 12 or len(commands) > 20:
        await session.send("\r\nMore matches exist. Narrow the search phrase for a shorter result.\r\n")


async def _show_index(session) -> None:
    await session.send("\r\n=== Help Index ===\r\n")
    for topic in sorted(TOPICS, key=lambda item: item.title.casefold()):
        aliases = ", ".join(topic.aliases[:3])
        suffix = f" ({aliases})" if aliases else ""
        await session.send(f"HELP {topic.key.upper():<22} {topic.title}{suffix}\r\n")
    await session.send(f"\r\n{len(TOPICS)} conceptual topics. Every command family is also available through HELP COMMAND.\r\n")


async def _show_catalog(session) -> None:
    await session.send("\r\n=== Complete Command Catalog ===\r\n")
    for category in command_guide.CATEGORIES:
        rows = [entry for entry in command_guide.COMMANDS if entry.category == category]
        if not rows:
            continue
        await session.send(f"\r\n[{category.upper()}] {len(rows)} command families\r\n")
        for entry in rows:
            await session.send(f"{entry.syntax} - {entry.description}\r\n")
    await session.send(
        f"\r\nCatalog total: {len(command_guide.COMMANDS)} command families. "
        "Use HELP COMMAND <command> for one page or HELP SEARCH <words> across the whole library.\r\n"
    )


def validate_help_library() -> tuple[str, ...]:
    problems: list[str] = []
    keys = [topic.key for topic in TOPICS]
    if len(keys) != len(set(keys)):
        problems.append("duplicate topic key")
    aliases: dict[str, str] = {}
    for topic in TOPICS:
        if topic.category not in CATEGORY_INFO:
            problems.append(f"{topic.key}: unknown category {topic.category}")
        if not topic.summary.strip():
            problems.append(f"{topic.key}: blank summary")
        if not topic.sections:
            problems.append(f"{topic.key}: no sections")
        for alias in (topic.key, topic.title, *topic.aliases):
            normalized = _normalize(alias)
            owner = aliases.get(normalized)
            if owner is not None and owner != topic.key:
                problems.append(f"alias collision {alias!r}: {owner} vs {topic.key}")
            aliases[normalized] = topic.key
        for related in topic.see_also:
            if related not in TOPICS_BY_KEY:
                problems.append(f"{topic.key}: broken see-also {related}")
    for category, topic_keys in CATEGORY_TOPIC_ORDER.items():
        if category not in CATEGORY_INFO:
            problems.append(f"unknown category order {category}")
        for topic_key in topic_keys:
            if topic_key not in TOPICS_BY_KEY:
                problems.append(f"{category}: missing topic {topic_key}")
    for entry in command_guide.COMMANDS:
        if not entry.syntax.strip() or not entry.description.strip() or not entry.category.strip():
            problems.append(f"incomplete command entry {entry!r}")
    return tuple(problems)


async def _delegate(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    old_prompt = session.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = old_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_deep_help_runtime(player_session_class) -> None:
    """Install the navigable help library at the final command edge."""

    if getattr(player_session_class, "_deep_help_runtime_installed", False):
        return

    _register_extra_commands()
    problems = validate_help_library()
    if problems:
        raise RuntimeError("Help library validation failed: " + "; ".join(problems))

    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"help", "?", "help home", "help menu", "manual"}:
            await _show_home(self)
            return
        if normalized in {"help categories", "help category", "help sections"}:
            await _show_categories(self)
            return
        if normalized in {"help index", "help topics", "help topic"}:
            await _show_index(self)
            return
        if normalized in {"help catalog", "help all", "help commands all"}:
            await _show_catalog(self)
            return
        if normalized.startswith("help search "):
            await _show_search(self, stripped[len("help search "):])
            return
        if normalized.startswith("help find "):
            await _show_search(self, stripped[len("help find "):])
            return
        if normalized.startswith("help command "):
            await _show_command_query(self, stripped[len("help command "):])
            return

        if normalized.startswith("help "):
            query = stripped[len("help "):].strip()
            query_norm = _normalize(query)
            category_key = query_norm.replace(" ", "-")
            if category_key in CATEGORY_INFO:
                await _show_category(self, category_key)
                return
            topic_key = TOPIC_ALIASES.get(query_norm)
            if topic_key is not None:
                await _show_topic(self, TOPICS_BY_KEY[topic_key])
                return
            command_rows = _find_exact_commands(query)
            if len(command_rows) == 1:
                await _show_command(self, command_rows[0])
                return
            await _show_search(self, query)
            return

        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._deep_help_runtime_installed = True


_register_extra_commands()
