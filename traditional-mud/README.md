# Dreams of the Fallen — Astralis

A traditional Telnet MUD being built collaboratively from account creation through endgame content.

## Game identity

The official game title is **Dreams of the Fallen**, set on the world of **Astralis**. New Telnet connections receive a compact dark-gothic ASCII startup screen before the account prompt, including the current tagline: **“Where the dead still dream.”**

## Current runnable milestone

- Async TCP/Telnet-compatible Python server on port 4000
- Independent session per connected player
- SQLite persistence with in-place development migrations
- Secure password hashing using Python's built-in scrypt
- Account creation and login
- Up to **8 characters per account**
- Character creation order: **race -> class -> deity (Priest only) -> player stat allocation -> name -> confirmation**
- Eight playable launch races
- Five selected classes with locked early-game and endgame identities
- Every race/class combination is legal
- Hybrid starting stats: race + class baseline plus player-allocated discretionary points
- Approved Brute baseline: Might 10 / Grace 6 / Love 5 / Mind 5 / HP 15, plus AC 8 from starter armor
- Approved Brute race adjustments so far: Dwarf +2 Might/+3 HP; Forest Elf +2 Grace/+2 Love; Goblin -1 Might/+2 Grace; Troll +3 Might/+3 HP/-1 Grace; Human baseline; Moon Elf -2 Might/+2 Grace/+2 Mind; Sporekin -1 Might/+2 Love/+2 Mind
- Character level and XP persisted separately from ability progression
- Per-ability use count and skill XP persistence
- Fixed class ability policy: class ability sets are authored and not player-customized
- Authored early ability kits for Brute, Wizard, Druid, and Necromancer
- Priest deity-path selection and persistence with **Zerjz (Z-E-R-J-Z)**, **Tenebrous**, and **Leviathan**
- Enemy hate-list foundation with level-scaling Brute `TAUNT` (30% at level 1, +2 percentage points per level, 95% cap)
- Persistent starter-weapon inventory entry for every new character
- Persistent item catalyst + active-pet foundation for Necromancer Skeleton summoning
- **Playable real-time combat** with automatic weapon attacks, live enemy retaliation, target selection, disengaging, HP/mana session state, and XP awards
- Ability foundation supporting both mana costs and cooldowns
- Custom Astralis stat system: **Might, Grace, Love, Mind, HP**
- Old-school equipment foundation focused on raw stat bonuses and equipment-derived **Armor Class (AC)**, with universal, race-restricted, and class-restricted gear
- Rare/special item hook for scripted item effects
- Gear acquisition foundations for **crafting, enemy drops, and quest rewards**
- Named-enemy special loot support and persistent use-based trade-skill progression for high-end crafting
- Locked crafting profession roster: **Blacksmithing, Tailoring, Enchanting, Alchemy, Cooking**
- Node-based **Mining**, **Harvesting**, and **Herbalism** gathering foundations
- Full baseline Tailoring textile ladder: **Cotton -> Wool -> Silk -> Moonweave -> Spidersilk -> Ghostweave -> Astralweave**
- Early **Alchemy** loop with herb gathering, healing potions, antidotes, tinctures, essential oils, and perfume
- Full baseline Blacksmithing metal ladder: **Iron -> Steel -> Cobalt -> Moonsteel -> Emberite -> Stariron -> Astralite**
- Racial HP regeneration hooks
- Race-specific starting-region metadata
- NPC social-policy hooks for race/class-based respect, distrust, fear, hostility, and rare authored service refusal
- Mostly-open-world access system with persistent character **keys** and **flags**
- Group-size gates for raids and selected high-end/group content
- Mixed quest philosophy: structured early guidance plus freeform discovery/exploration
- The **Human starting experience is now room-based and playable**: Demon Gate -> Ashen Way -> Cathedral Square -> Grand Cathedral
- New Human characters receive a **Sealed Cathedral Note** and the structured introductory quest **A Summons to the Cathedral**
- The Human start teaches `INVENTORY`, `READ NOTE`, directional movement, `QUESTS`, and `TALK HIGH ACOLYTE`
- The **High Acolyte** is an authored enigmatic mentor NPC in the cathedral; meeting them completes the introduction, persists the `met_high_acolyte` flag, marks the reverse of the Cathedral Note, and launches the first combat-training quest
- Cathedral Square establishes the visible clerical order and hints at an **unnamed occult secret society** without inventing its final name or structure yet
- The Human combat tutorial is now room-based: **Outer Drill Road -> Training Yard -> Practice Ring -> Vermin Pens**
- After completing combat training, returning to the **High Acolyte** can launch **Marks in the Ash**, the first Human investigation quest in the Lower Wards
- The new Lower Wards branch is **Ashen Way -> The Sootstairs -> Cinder Lane**, with the **Blackglass Arch** occult mark and a **Grey-Cloaked Informant** in Lantern Court
- The structured quest **Lessons Beyond the Gate** teaches the player to reread the High Acolyte-marked note, find the training grounds, defeat a non-retaliating Training Dummy, then defeat a retaliating Sewer Rat or Small Imp
- Human training enemies are authored as **Training Dummy**, **Sewer Rat**, and **Small Imp**; the rat and imp award small amounts of XP
- Characters can use `LOOK`, `EXAMINE`, `TOUCH`, `LISTEN`, `EXITS`, cardinal directions, `SCORE`, `STATS`, `HEALTH`, `LORE`, `PROGRESS`/`ABILITIES`, `ATTACK`/`KILL`, `USE`/`CAST`, `FLEE`, `BIND`, `ACCESS`, `INVENTORY`, `READ`, `QUESTS`, `TALK`, `TRADES`, `PROFESSIONS`, `RECIPES`, `CRAFT`, `MINE`, `HARVEST`, `HERBALISM`, `MENU`, and `QUIT`

The other five racial starting areas, most enemies beyond the Human tutorial, later-level class ability names, most combat tuning, most race-specific starting-stat adjustments, final XP balance, later Priest-path spells, and finalized racial at-will abilities are intentionally **not invented yet**. The framework is executable, while provisional tuning is centralized so we can rebalance it as we design.

## Locked gameplay direction

## Character stats

Astralis uses custom names for familiar RPG functions:

- **Might** — adds directly to normal auto-attack damage.
- **Grace** — increases auto-attack speed. The current engine uses a provisional +1% attack-speed effect per Grace point so the relationship is executable; this tuning value is centralized and not balance-locked.
- **Love** — adds directly to healing done and contributes to maximum mana.
- **Mind** — adds directly to spell damage and contributes to maximum mana.
- **HP** — adds raw hit points directly to maximum HP.
- **Armor Class (AC)** is **not** a core character stat. AC comes from equipped items and governs how difficult the character is to hit; higher AC requires a higher attack roll.

Love and Mind both contribute additively to the mana pool. Starting stats now use the agreed hybrid structure: a baseline is influenced by both race and class, then the player allocates discretionary points during character creation. The current numerical modifiers and five-point allocation pool are **provisional development tuning**, not final balance. Existing characters remain compatible through database migrations.

### Combat

Combat is **real-time** rather than turn-based. Once engaged, normal weapon attacks occur automatically on an attack timer. Players can type active abilities while auto-attacks continue. Active abilities are designed to use both:

- a mana-like resource; and
- cooldown timers.

The timing engine now understands Might-based auto-attack damage, Grace-based attack speed, Love-based healing, Mind-based spell damage, Love+Mind mana contribution, HP-based maximum-health bonuses, and equipment-derived AC. The Human tutorial now uses a provisional d20-style enemy AC check, real enemy retaliation timers, and session HP/mana so combat is playable. Final attack formulas and final balance values remain open. A persistent bind-point death system is now implemented.

### Human combat tutorial

After the first Cathedral quest, the High Acolyte writes new instructions on the reverse of the player's existing **Sealed Cathedral Note**. `READ NOTE` then points outside the Demon Gate. The route is:

`Grand Cathedral -> Cathedral Square -> Ashen Way -> Demon Gate -> Outer Drill Road -> Training Yard`

The Training Yard branches into:

- **Practice Ring** — contains a Training Dummy. `ATTACK DUMMY` begins real-time auto-attacks; the dummy does not retaliate.
- **Vermin Pens** — contains a Sewer Rat and Small Imp. Both are low-risk live enemies and strike back. Defeating either completes the tutorial.

While engaged, players can continue typing commands. `USE <ability>` or `CAST <ability>` executes unlocked abilities where an executable effect has been authored. `FLEE` is now a real combat action rather than guaranteed disengagement: the provisional base success chance is 70%. A successful breakaway chooses a legal exit; an engaged mobile predator may then attempt to pursue, but only through rooms inside its explicit habitat. `HEALTH` shows current HP, mana, and target HP. Tutorial spell costs/cooldowns and enemy numbers remain provisional tuning. If a trainee is reduced to 0 HP in the Vermin Pens, guards recover them in the Training Yard before a true death occurs. Ordinary lethal combat now uses the persistent death/bind system described below.

### Progression

- Character level is driven by **experience points**.
- Levels **1-10 are intentionally quick**, especially the earliest levels, to keep the opening progression active and rewarding.
- XP requirements become noticeably steeper after level 10. The current numbers are provisional and centralized for tuning.
- Individual abilities improve through **use-based skill progression**.
- The database tracks every ability's uses and skill XP independently.
- Every class is intended to be able to **solo to the end-level progression**. Group content is additional/gated content, not a requirement to reach end level.
- Humans have **Fast Learner**, meaning their practiced abilities will improve faster than other races; the exact multiplier is still open for balance discussion.

### Class abilities

Each class has an authored, fixed ability set. Players do **not** build a class by selecting abilities from a shared talent pool. Abilities can unlock as the character progresses and then improve through use. The five class ability lists themselves have not yet been authored.

The early class kits now established are:

- **Brute** — `Taunt` at level 1 and `Heavy Strike` at level 2. Taunt costs **10 mana**, has a **5-second cooldown**, starts at a **30%** success chance at level 1, gains **2 percentage points per character level**, and caps at **95%**. On success it moves the Brute to the top of the target enemy's hate list.
- **Wizard** — `Coldfire Burst` at level 1, `Minor Barrier` at level 2, and `Arcane Bolt` at level 3.
- **Druid** — class Foraging utility and `Minor Heal` at level 1, then an ally/self HP buff at level 2. Druids explicitly **do not shapeshift**.
- **Necromancer** — `Minor Life Tap` at level 1, `Raise Skeleton` at level 2 consuming common merchant-stock **Bone Chips**, then `Rot` at level 3 as the first damage-over-time spell. Bone Chips replace the older generic Bones catalyst and old inventories migrate automatically.
- **Priest** — spell progression branches from the Priest's chosen deity:
  - **Zerjz (Z-E-R-J-Z)** — Healing path; level 1 `Restoring Light`.
  - **Tenebrous** — Protection path; level 1 `Guardian Ward`.
  - **Leviathan** — Vengeance path; level 1 `Judgment Bolt`.
  Each deity path has its own fixed progression of stronger themed spells as the Priest levels. Later spell names and tuning remain to be authored.

Exact mana costs, cooldowns, damage/healing values, and skill-rank curves remain balance work unless explicitly noted otherwise.

### Equipment

Equipment follows an old-school stat-first philosophy. Ordinary gear primarily supplies raw values such as Might, Grace, Love, Mind, HP, and AC. The item model also supports scripted effects, but those are reserved for rare or otherwise special items rather than becoming standard on every piece of loot.

Gear can be **universal**, **race-restricted**, **class-restricted**, or restricted by both race and class. Equipment enters the world through a mixture of **crafting, enemy drops, and quest rewards**. Some authored items can be primarily associated with crafting while others are primarily associated with drops. Special named enemies can carry unique, high-stat loot that ordinary versions of that creature do not. Trade skills persist uses and skill XP, and high-skill crafting is explicitly intended to produce very strong equipment capable of competing with strong drops after substantial investment.

### Crafting and gathering

The profession roster is **Blacksmithing, Tailoring, Enchanting, Alchemy, and Cooking**. **Mining**, **Harvesting**, and **Herbalism** are separate node-based gathering skills rather than crafting professions. Harvesting handles fibers and similar general natural materials, while Herbalism specifically handles medicinal and aromatic plants for Alchemy. Resource nodes expose the gathering skill they require and a material output; room persistence and node respawn timing will connect to this system when authored rooms are implemented.

Tailoring now has a full baseline textile progression from beginner through endgame. Harvesting nodes feed the profession, and each tier is processed at a **loom** into thread/yarn and then cloth before being sewn into baseline Hood and Tunic patterns. The progression is:

1. **Cotton** — Cotton Patches -> Raw Cotton -> Cotton Thread -> Cotton Cloth. Common beginner textile from warm lowlands.
2. **Wool** — Sheep Flocks -> Raw Wool -> Wool Yarn -> Wool Cloth. Warm, durable early-game textile from pastoral regions.
3. **Silk** — Silk Cocoon Clusters -> Silk Cocoons -> Silk Thread -> Silk Cloth. Fine mid-game textile from warm groves and silkworm houses.
4. **Moonweave** — Moonflax Beds -> Moonflax Fiber -> Moon Thread -> Moonweave Cloth. Pale, elegant high-altitude textile associated with Moon Elf lands.
5. **Spidersilk** — Giant Spider Nests -> Raw Spidersilk -> Spidersilk Thread -> Spidersilk Cloth. Strong advanced textile from dangerous forests, caves, and ruins.
6. **Ghostweave** — Ghostmoss Patches -> Ghostmoss Fiber -> Ghost Thread -> Ghostweave Cloth. Pale funerary textile from necropolises, catacombs, and other death-soaked places.
7. **Astralweave** — Astral Blooms -> Astral Bloom Fiber -> Astral Thread -> Astralweave Cloth. Rare master Tailoring textile found only in dangerous endgame regions.

Cotton remains the beginner loop, while later tiers require progressively higher **Harvesting** and **Tailoring** skill. Baseline tailored gear remains stat-first, and the current material quantities, skill thresholds, and item stats are provisional balance values. Rare drops, class/race restrictions, and scripted effects can later sit on top of this ladder.

Alchemy now begins as an herb-first profession and branches beyond combat potions. The first authored resource nodes are **Greenleaf Patches**, **Bitterroot Clusters**, and **Lavender Patches**, all gathered with **Herbalism**. The first recipes are:

- **Minor Healing Potion** — Greenleaf + Spring Water, prepared with a mortar and pestle.
- **Lesser Antidote** — Bitterroot + Greenleaf + Spring Water, prepared with a mortar and pestle.
- **Greenleaf Tincture** — Greenleaf steeped in Grain Alcohol.
- **Lavender Essential Oil** — distilled from Lavender Blossoms at an alchemy table.
- **Lavender Perfume** — Grain Alcohol + Lavender Essential Oil, blended at an alchemy table.

Perfume is intentionally a real Alchemy branch rather than flavor-only vendor junk. The first Lavender Perfume carries a small temporary **Grace** bonus as provisional tuning, establishing that perfumes may provide subtle temporary effects without becoming major combat consumables. The item model now stores consumable/application effect metadata for healing, poison-cleansing, tinctures, and temporary perfume buffs. **Spring Water** and **Grain Alcohol** are authored reagents; their eventual world/vendor/brewing sources will be connected when those systems are built.

The baseline Blacksmithing metal ladder is now authored from beginner through endgame:

| Tier | Metal | Skill direction | Material source | Identity |
| --- | --- | ---: | --- | --- |
| 1 | **Iron** | 0+ | Iron Veins | Common, dependable beginner metal |
| 2 | **Steel** | 15+ | Iron Ingot + Coal | Refined early-game upgrade; not mined directly |
| 3 | **Cobalt** | 30+ | Cobalt Veins | Deeper blue-gray metal for accomplished smiths |
| 4 | **Moonsteel** | 50+ | Steel Ingot + Moonsilver Ore | Elegant Astralian alloy tied geographically to high-altitude moonlit ranges |
| 5 | **Emberite** | 75+ | Emberite Veins | Warm dark metal from volcanic and geothermal regions |
| 6 | **Stariron** | 105+ | Stariron Deposits | Dense meteoric metal from ancient impact sites |
| 7 | **Astralite** | 140+ | Astralite Veins | Rare signature endgame metal of Astralis |

Mining thresholds rise alongside the ladder. Coal begins appearing at low skill, followed by Cobalt, Moonsilver, Emberite, Stariron, and finally Astralite nodes in increasingly dangerous regions. Steel is deliberately an alloy rather than an ore: **Iron Ingot + Coal -> Steel Ingot**. Moonsteel is likewise an alloy: **Steel Ingot + Moonsilver Ore -> Moonsteel Ingot**.

Every tier currently supports a readable baseline set of **Dagger, Sword, Helmet, and Breastplate** recipes at a forge. These pieces remain mostly raw-stat/AC gear in keeping with the old-school equipment philosophy; named drops, rare scripted effects, class/race equipment, enchanting, and masterwork items can deliberately break that simple pattern later.

Each successful gathering or crafting action advances its persistent skill through use. The current skill thresholds, material quantities, item stats, and high-quality thresholds are **provisional tuning**. The progression identities and order are authored; the numbers can be rebalanced as combat and the economy mature. Crafting remains transactional, so materials are consumed and outputs/skill gains are committed together.

The playable shell exposes `PROFESSIONS`, `TRADES`, `RECIPES`, and `INVENTORY`. `MINE`, `HARVEST`, and `HERBALISM` intentionally require authored resource nodes, and `CRAFT` respects station requirements; there is no invisible forge, loom, mortar-and-pestle station, alchemy table, mine, fiber patch, or herb patch available everywhere before the room system exists.

### Exploration, access, and quests

### Sporekin starting experience

The Sporekin are now the second race with a room-by-room opening area. New Sporekin begin in **Lumen Hollow**, a quiet underground cave lit by blue-green bioluminescent fungi and rich with wet-earth scent, pale roots, and living mycelium. Their first exploratory route is:

`Lumen Hollow -> The Mycelial Gallery -> Rootwell Ascent -> The Veiled Grotto`

The route gradually moves from the deep hidden fungal civilization toward the surface. The **Mycelial Gallery** subtly introduces the Sporekin shared consciousness through the living network beneath the player's feet. **Rootwell Ascent** becomes cooler and airier as roots form a natural climb, and **The Veiled Grotto** lets filtered daylight and the smell of rain enter the experience while remaining concealed just below the true surface.

The Sporekin opening now begins with the structured starter quest **The Chorus Beneath**. Instead of receiving a physical quest item or speaking to an NPC, the newly awakened character is contacted directly by the **shared consciousness**. The message is telepathic, familiar, and plural: it tells the character that the collective can feel them and guides them north along the living mycelial threads. The chorus speaks again as the player reaches the Mycelial Gallery and Rootwell Ascent, using cool air, roots, rain, and natural light as landmarks rather than conventional signposts.

The quest route is:

`Follow the living threads -> follow the cool air -> climb toward the light -> reach the Veiled Grotto`

Reaching the Veiled Grotto completes **The Chorus Beneath** and persists the `sporekin_first_call_answered` flag. The final mental message reminds the character that the surface world is filled with separate voices, encourages them to listen and guide where they can, and reinforces that the shared consciousness remains beneath them even when they travel alone.

That completion now immediately launches the second structured Sporekin quest, **The Forgotten Pulse**. The root veil opens north into **Rainroot Verge**, the character's first true surface room, where rain, insects, leaves, and ordinary forest noise contrast with the quiet Underways. A weak remembered pulse leads east into **The Forgotten Grove**.

The grove contains an ancient ring of four distinct bioluminescent mushrooms around a black stone: **blue, amber, violet, and ivory**. The puzzle is deliberately built for MUD controls rather than movement commands. `EXAMINE RING` or `EXAMINE STONE` reveals the old spore-stained sequence, and the player reproduces it with commands such as `TOUCH BLUE MUSHROOM`. The correct sequence is **blue -> amber -> violet -> ivory**. Touching the wrong cap extinguishes the ring and resets the sequence to blue. `LISTEN` provides an additional atmospheric clue through a faint four-beat memory.

Solving the sequence completes **The Forgotten Pulse**, persists the `sporekin_forgotten_pulse_solved` flag, causes silver spores to form a floating spore-shaped sigil, and reveals a previously hidden north exit into **The Memory Path**. The north exit is genuinely conditional: it does not appear in `LOOK` or `EXITS` until the puzzle is solved. The Memory Path intentionally stops before the next major Sporekin story beat so that discovery can be designed collaboratively. There is still no Sporekin mentor NPC or combat tutorial. Older development Sporekin characters without a room are safely placed into Lumen Hollow, and characters that completed the first call before this quest existed receive **The Forgotten Pulse** when they next enter the world.

### Human starting experience

The Human kingdom is the first racial start to move from regional metadata into a real room graph. New Humans begin at **The Demon Gate**, a wrought-iron entrance built into black stone and covered in deliberately reclaimed demonic imagery. The initial route is:

`The Demon Gate -> Ashen Way -> Cathedral Square -> The Grand Cathedral`

The rooms establish the agreed dark gothic atmosphere through black stone, ironwork, horned civic imagery, sharp spires, torchlight, stained glass, gargoyles, taverns, guild offices, and the cathedral dominating the skyline. Cathedral Square visibly features the city's clerical order and contains subtle erased symbols hinting that an unnamed occult society operates in the Human capital. The society remains deliberately unnamed until its lore is designed.

New Human characters receive a **Sealed Cathedral Note** directing them to the **High Acolyte**, an authoritative but enigmatic mentor inside the Grand Cathedral. The structured introductory quest **A Summons to the Cathedral** teaches the player to inspect inventory, read a quest item, navigate by room exits, check the quest journal, locate an NPC, and talk to them. Completing the meeting persists the `met_high_acolyte` flag for future story use. Existing Human development characters are upgraded into this starting sequence safely on login if they predate the room system.

After **Lessons Beyond the Gate** is completed, speaking to the High Acolyte again launches the first non-tutorial Human investigation, **Marks in the Ash**. The Acolyte sends the player west from Ashen Way into a poorer, older layer of the capital rather than giving them another combat exercise. The Lower Wards route currently branches through **The Sootstairs** into **Cinder Lane**, with side destinations at **The Blackglass Arch** and **Lantern Court**.

At the Blackglass Arch, fresh scratches form **three hooked strokes curling inward around a hollow circle**, a symbol visibly related to the half-erased occult signs in Cathedral Square. `EXAMINE MARK` advances the investigation and sends the player looking for someone who recognizes it. In Lantern Court, `TALK INFORMANT` engages a **Grey-Cloaked Informant** who explains that the symbol is neither a gang mark nor a prayer: it is used to signal that a route below has been left open. The informant points specifically toward old cistern tunnels beneath the Lower Wards, where official city plans appear to be false or incomplete. Completing the investigation persists the `human_lower_wards_mark_traced` flag. The occult society itself remains unnamed, and the cistern tunnels intentionally remain the next unresolved Human story hook.

### Forest Elf starting experience

Forest Elves are now the third race with a fully authored room-based opening. New Forest Elves begin in **Circle Clearing**, a peaceful town center surrounded by timber homes, gardens, and the seven weathered stones of the local Druidic Circle. Their first route is:

`Circle Clearing -> The Greenway -> The Old River Path -> Waystone Bend -> The Listening Pool -> The Outer Grove`

The structured quest **The Old River Path** reflects the Forest Elves' isolated culture and only slight connection to nature magic. The Druidic Circle gives the new character a simple charge: walk the river path slowly, follow the carved leaf, listen where the water becomes still, and travel only as far as the boundary oak. The quest teaches movement and environmental interaction through `EXAMINE WAYSTONE` and `LISTEN` rather than combat.

The route begins deliberately beautiful, comfortable, and safe. The Waystone uses practical symbolic trail marks rather than overt magical spectacle, while the Listening Pool gives only a subtle suggestion that current, roots, or magic can be sensed by careful attention. Reaching **The Outer Grove** completes the quest, persists the `forest_elf_first_walk_completed` flag, and introduces the first signs of danger through animal tracks, old claw marks, brambles, and a red warning cloth placed by the Circle. Older Forest Elf development characters without a room or quest are safely upgraded into this opening on login.

Astralis is intended to be **mostly open-world**. Selected locations can require a persistent character flag, a specific key, or both. Raids and some difficult/high-end areas can also require a minimum group size. Race itself does not globally lock a civilization away.

Questing uses a mixture: structured quests provide direction and momentum early, while exploration, discovery, and less-scripted adventuring become increasingly important. Structured quests are not intended to be the only viable way to progress.

### Solo and group play

Every class should be capable of soloing the main level journey to the end levels. Along that journey, optional content such as raids, dangerous high-end zones, bosses, and other special encounters can require coordinated groups.

## Class roster

All race/class combinations are legal.

1. **Brute** — warrior-like physical tank. Endgame Brutes control threat, taunt enemies, use high-damage melee attacks, carry only a few defensive self-buffs, and depend heavily on gear and weapons. Most major buffs are expected to come from other classes.
2. **Wizard** — arcane nuke caster. Endgame Wizards specialize in very high single-target spell damage, world teleportation for players, self-protection, and smaller utility such as rooting enemies in place rather than buffing the group.
3. **Druid** — nature support/healer. Druids forage, heal, buff, ward, and use nature-themed utility/control. At endgame they are reliable healers but deliberately not as strong at pure healing as Priests. They do not shapeshift.
4. **Priest** — deity-path heavy-plate healer. The three locked deity paths are **Zerjz (healing)**, **Tenebrous (protection)**, and **Leviathan (vengeance)**. Their level-1 spells are `Restoring Light`, `Guardian Ward`, and `Judgment Bolt` respectively. Each path has its own fixed progression. Endgame Priests are the game's prime healers, resurrect fallen allies, and provide major HP and AC buffs.
5. **Necromancer** — undead-pet and damage-over-time caster. Endgame Necromancers command powerful undead pets, specialize in rot/DoT magic, gain a lich-like skeletal form, and have distinctive dark utility.

The names and these class arcs are locked. Ability sets remain fixed by class rather than player-customized. Later-level ability names and exact numerical balance are still to be designed.

## Race roster

All eight playable races are humanoid enough to use one shared equipment anatomy.

### Human

- Humans are the **least numerous** playable people on Astralis.
- Their ancestors intentionally traveled from **Earth** several centuries ago during experiments with dimensional-travel technology.
- Modern humans are Astralis-born. Earth is almost legendary, and there is no known route back.
- Almost no Earth culture survived. Rare surviving Earth objects are treated as historical artifacts.
- Humans maintain **one large kingdom** and are one of the least socially mixed peoples.
- Other races commonly call humans **Demons** because of their outsider origin.
- Human culture embraced the label generations ago; their main city and kingdom use dark stone, sharp spires, statues, heraldry, and other demonic imagery as an intentional aesthetic.
- Their closest major neighbors are the dwarves.
- Humans are not unusually skilled engineers on Astralis merely because their ancestors once had dimensional technology.
- **Passive: Fast Learner.** Humans improve practiced abilities faster; exact balance tuning remains open.
- At-will racial ability remains open.

### Forest Elf

- Player-facing label: **Forest Elf**. They themselves insist they are simply **Elves**.
- Live mainly in isolated towns inside a vast forest.
- Their magical connection to nature is real but slight.
- Lifespan is roughly the same as humans, averaging around **80 years**.
- Somewhat more graceful/attractive than humans on average, but not ethereal or supernaturally beautiful.
- Long pointed ears are their clearest physical hallmark.
- Governed by **Druidic Circles**.
- Believe they are the superior and only true elven people.
- They deny that Moon Elves are actually elves.
- Starting experience begins beautiful, peaceful, and comfortable, then gradually introduces danger.
- Passive and at-will racial ability remain open.

### Moon Elf

- Player-facing label: **Moon Elf**. They also insist they are simply **Elves**.
- Their origin is lost to time. Some traditions say they arrived from beyond Astralis, like humans, but **not through technology**.
- No special technological affinity.
- Lavender-grey skin.
- Oversized eyes with **no visible sclera**.
- Normal hair and otherwise familiar humanoid/elven anatomy.
- Strong cultural, spiritual, and symbolic connection to **Astralis's moon**.
- Civilization is ancient, mystical, and elegant.
- Emotionally and socially understandable rather than alien.
- Broadly accepted by other peoples because they have lived on Astralis for so long.
- Carry a cultural chip on their shoulder about Forest Elf rejection.
- Their homeland is a **high-altitude mountain region**, placing their cities closer to the moonlit sky.
- Passive and at-will racial ability remain open.

### Dwarf

- Live in enormous mountain settlements spanning a main **underground city** and above-ground towns.
- Industry is roughly one level beyond sophisticated clockwork and powered primarily by **steam**.
- Engineering excellence is cultural, not biological.
- Traditional dwarf appearance, generally **4–5 feet tall** and broad-built.
- Governed by powerful **trade houses and labor unions**.
- Cities are highly socially mixed due to industry and trade.
- Culture is bureaucratic and intensely focused on craftsmanship, standards, and professional pride.
- No particular cultural rivalry with goblins.
- Mining, stonework, and metalworking exist but are not the sole focus of dwarven identity.
- Starting experience feels like a **working industrial city** of workshops, foundries, union halls, freight routes, lifts, and steam systems—not a generic fantasy mine.
- Passive and at-will racial ability remain open.

### Goblin

- Goblins are proud of the word **Goblin**.
- Around **5 feet tall**.
- Green skin, large ears, sharp teeth, long noses.
- Somewhat weaker than most races, but not frail; the current provisional starting-stat profile gives them a small Might penalty offset by Grace.
- Many loosely connected clans live in **swamp towns**.
- Nearly all goblins regard the enormous **Junk City** as their main metropolitan home.
- Society is highly transactional and influenced by gangs, merchant families, inventors, and fixers.
- Excellent at repairing, salvaging, and repurposing; less focused on creating wholly new technologies.
- Workmanship is ugly, patched, improvised, and **surprisingly effective**, not randomly unreliable.
- Common livelihoods: salvage, repair, scrap trading, courier work, black markets, mercenary work, and ordinary commerce.
- Treated as a distrusted underclass, but other peoples routinely do business with them.
- Settlements are mostly goblin rather than cosmopolitan.
- Occasionally recover Earth artifacts and sell them to humans for preservation and study.
- Mildly irreverent culture without becoming slapstick or parody.
- Starting experience is busy, noisy, dense, and highly interactive.
- `SCROUNGE` remains a possible future at-will racial ability, but is not locked.

### Troll

- One of the oldest peoples on Astralis.
- Around **7 feet tall**, green-skinned, unmistakably monstrous, and unable to pass for human.
- Average intelligence, despite a persistent outsider stereotype that trolls are stupid.
- No single major homeland.
- Scattered nomadic tribes and rough but organized strongholds around the world.
- Deep-forest troll cultures are common; **Snow Trolls** are a tundra regional culture, not a separate playable race.
- Led by chieftains and priests.
- Strong by nature, though troll culture does not particularly glorify strength.
- Skilled at hunting, warfare, and animal handling.
- Bitter about widespread distrust and condescension.
- Culture is brutal and intimidating in presentation.
- Starting experience is harsh and dangerous immediately.
- **Passive: Regeneration — +1 additional HP per normal server regeneration tick.** This exact bonus is implemented.
- At-will racial ability remains open.

### Undead

- They are **actually dead** and have been reanimated.
- Every Undead was once a living person and may have originated from any other race.
- They remember their former lives.
- Nearly skeletal in appearance but preserved rather than rotten, allowing normal civilization and shared humanoid equipment anatomy.
- Do not need to eat, drink, sleep, or breathe.
- They are not permanently immortal; eventually their bodies deteriorate and they die for good.
- Main civilization is a huge **underground necropolis beneath a desolate desert**.
- Ruined Undead kingdoms are scattered elsewhere in the world.
- Society is gloomy and death-obsessed.
- Governed by **priest-kings and ancient houses**.
- Other peoples generally fear them.
- Necromancy is common in their culture.
- Their dominant religion teaches that after death, one becomes reanimated.
- Most Undead see reanimation as a **gift**, though some consider it a curse.
- Ordinary healing magic works normally on them.
- Poison and disease affect them less strongly than living characters; exact resistance percentages remain open.
- Starting experience is quiet and eerie.
- Final passive and at-will ability naming remain open.

### Sporekin

- Wise humanoid fungal people, fully compatible with ordinary humanoid equipment.
- Civilization exists both above and below ground, but the large majority is **underground and unseen** by other societies.
- Smaller surface settlements and fungal groves provide their visible presence.
- Reproduce through **spores**.
- See themselves as guides to the other races.
- Possess a **shared consciousness**, giving their society a collective dimension.
- **Passive: Deep Regeneration — +2 additional HP per normal server regeneration tick.** This exact bonus is implemented.
- At-will racial ability remains open.

## World geography locked so far

Astralis contains **multiple continents separated by seas**, though the number, shapes, and proper names of those continents are still open.

Current regional anchors are intentionally stored under descriptive placeholder names so we can choose proper in-world names later:

- **Human Kingdom** — humans' single large kingdom; closest major neighbor is dwarven territory.
- **Dwarven Mountain Settlements** — enormous underground/above-ground steam industrial region.
- **Great Elven Forest** — isolated Forest Elf towns in a vast woodland.
- **Moon Peaks** — high-altitude Moon Elf civilization.
- **Goblin Swamps and Junk City** — swamp clans plus the major metropolitan Junk City.
- **Troll Strongholds** — scattered deep-forest, wilderness, and tundra strongholds rather than one homeland.
- **Desert Necropolis** — Undead capital civilization beneath a desolate desert.
- **Sporekin Underways** — predominantly underground fungal civilization with limited surface presence.
- **Central Trade City** — neutral melting-pot city at a major river/trade crossroads where all races mingle for commerce and diplomacy.

All races will eventually be able to travel into every civilization. Race **and class** can affect core NPC reactions such as respect, distrust, fear, hostility, or rare refusal of service, while most dialogue remains universal. Major content is not intended to be hard-locked by race. The world is mostly open, with authored exceptions using persistent keys, character flags, progression state, or group requirements.

## Running the development build

### Windows

Double-click `run_windows.bat`, or run:

```bash
py server.py
```

### macOS / Linux

```bash
python3 server.py
```

Then connect a Telnet-capable client to port `4000` on the host running the server.

## Current source layout

```text
traditional-mud/
├── server.py
├── run_windows.bat
├── README.md
├── data/
└── mud/
    ├── __init__.py
    ├── character_options.py   # race/class definitions and locked lore
    ├── world_data.py          # regional/world anchors
    ├── database.py            # accounts, characters, XP, ability-use persistence
    ├── mechanics.py           # XP curve, class kits/arcs, deity-path rules, mana/cooldowns, regen hooks
    ├── combat.py              # real-time auto-attack scheduler + enemy hate-list foundation
    ├── npcs.py                # mobile NPC state, boundaries, wander/patrol/hunter/routine AI
    ├── access.py              # keys, flags, and group-content gates
    ├── quests.py              # structured + discovery quest framework
    ├── social.py              # authored NPC race/class reaction policies
    ├── stats.py               # custom stats, starting allocation, equipment stat/restriction model
    ├── gear.py                # crafting/drop/quest gear sources, named loot, trade-skill rules
    ├── security.py
    ├── server.py
    └── session.py
```

### Approved Brute racial starting modifiers

The Brute baseline is Might 10, Grace 6, Love 5, Mind 5, HP 15, with AC 8 supplied by the Brute Training Harness before the player's five discretionary stat points.

- Human: no racial modifier (10 / 6 / 5 / 5 / 15)
- Dwarf: +2 Might, +3 HP (12 / 6 / 5 / 5 / 18)
- Forest Elf: +2 Grace, +2 Love (10 / 8 / 7 / 5 / 15)
- Goblin: -1 Might, +2 Grace (9 / 8 / 5 / 5 / 15)
- Troll: +3 Might, -1 Grace, +3 HP (13 / 5 / 5 / 5 / 18)
- Moon Elf: -2 Might, +2 Grace, +2 Mind (8 / 8 / 5 / 7 / 15)
- Sporekin: -1 Might, +2 Love, +2 Mind (9 / 6 / 7 / 7 / 15)

Human Brutes intentionally remain the pure class baseline to reinforce humans as adaptable generalists. Moon Elf Brutes retain their mystical/precise racial profile even in a physical class by trading some of the Brute's Might advantage for Grace and Mind. Sporekin Brutes trade a small amount of Might for stronger Love and Mind, reflecting their wise, communal nature.

### Forest Elf danger boundary

The first authored dangerous room beyond the peaceful Forest Elf introduction is **Briarshadow Thicket**. It lies immediately north of the Outer Grove. The canopy closes, the maintained Elven trail disappears, a red warning marker has been torn, and fresh broad tracks plus snapped saplings signal that something substantial is moving nearby. The first mobile hunter, the **Briarshadow Stalker**, inhabits only Briarshadow Thicket and the Outer Grove and is now integrated with real-time combat.

### Mobile NPC behavior foundation

Mobile NPCs are world-state creatures with a single current room rather than static lines permanently attached to a room definition. The server advances them on an NPC tick (currently 5 seconds, provisional). Every mobile NPC has an explicit allowed-room boundary. **The boundary is authoritative:** no patrol route, chase target, random movement, or schedule is allowed to move an NPC into a room outside its authored habitat/post.

Four behavior types are currently supported:

- **Wander** — chooses a legal neighboring room at random.
- **Patrol** — follows an authored room-by-room circuit.
- **Hunter** — detects players within a configured radius and pathfinds one room at a time toward them, but stops at its habitat boundary. With no target detected, it prowls inside its habitat.
- **Routine** — uses a time-of-day schedule and shortest-path movement to travel toward the room assigned for the current hour. The development build currently uses the host server's local hour until an Astralis-specific world clock is designed.

The ambient Forest Elf wildlife remains:

- **Silverleaf Hare** — wanders the Greenway, Old River Path, Waystone Bend, and Listening Pool.
- **Redtail Squirrel** — wanders Circle Clearing, the Greenway, and Old River Path.
- **Willow Wren** — wanders Old River Path, Waystone Bend, Listening Pool, and the Outer Grove.

Three authored examples exercise the advanced behaviors in the current world:

- **Blackwall Guard (Patrol)** — marches a loop from the Demon Gate to Outer Drill Road, into the Training Yard, and back.
- **Briarshadow Stalker (Hunter)** — inhabits only Briarshadow Thicket and the Outer Grove. It does **not** detect players through adjacent rooms. Aggro begins only when the Stalker and a player share a room. Once combat has begun, a fleeing player can be pursued through the two-room habitat, but the Stalker can never cross south into the Listening Pool.
- **Ashen Way Curio Peddler (Routine)** — moves among the Demon Gate, Ashen Way, and Cathedral Square according to the hour: early gate traffic, daytime market trade, evening cathedral crowds, then back toward the shopfront at night.

Players in an NPC's origin room see it leave, players in the destination room see it arrive, and `LOOK` shows whatever mobile NPCs are actually present at that moment. Movement verbs reflect behavior (`wanders`, `marches`, `stalks`/`prowls`, or `walks`). Movement probabilities and schedules remain provisional tuning values.

### Mobile NPC aggression and pursuit

Aggressive mobile NPCs now use a separate combat state layered on top of movement AI. Passive aggro is currently **same-room only**: a hunter two rooms away cannot notice a player and begin pathfinding toward them. When an aggressive NPC and an eligible player share a room, the NPC can acquire that player, stop autonomous wandering, and begin the same real-time auto-attack combat loop used by authored room enemies.

`FLEE` has a provisional **70% base success chance**. A failed flee leaves the player in place and combat continues. On a successful breakaway, the player moves through a legal room exit. An engaged mobile NPC then makes its own authored pursuit roll (the Briarshadow Stalker currently has a provisional 70% follow chance). Before following, the engine checks the NPC's allowed-room boundary. If the destination is forbidden, pursuit ends automatically regardless of the roll. This prevents players from dragging predators, guards, or future bosses into rooms where they do not belong.

### Death and bind points

Characters now have a persistent **bind point** separate from their current room. New characters whose room-based starting areas are authored default their bind point to their racial starting room. Normal movement never changes the bind point. Future binding spells can change it through the dedicated persisted bind setter, allowing a character to choose a different resurrection location without changing their racial origin. The player-facing `BIND` command reports the current bind point but does not change it.

When ordinary combat reduces a character to 0 HP, the character dies, loses experience, and is returned to the bound room with HP and mana restored. The initial tuning is intentionally conservative: death removes **10% of the experience earned within the current level**, with a minimum loss of 1 XP when there is progress to lose. Death currently **cannot de-level** a character; XP will not fall below the floor for the current level. Both the percentage and de-level rule are centralized provisional tuning and can be changed later.

The Human Vermin Pens remain a special tutorial exception: training guards intervene before true death and recover the trainee in the Training Yard without invoking the ordinary death penalty.

When pursuit ends, the NPC disengages and transitions back toward its duty state. Hunters return toward their spawn/home room, routine NPCs head back toward their current scheduled destination, and patrol NPCs resume their authored post behavior. Engaged NPCs are frozen out of ordinary NPC movement ticks so they cannot randomly wander away mid-combat. Defeated mobile NPCs temporarily despawn and later respawn at their authored spawn point.

## Mudlet UI / GMCP support

Dreams of the Fallen now negotiates GMCP (Telnet option 201) with capable MUD clients such as Mudlet while remaining a normal text Telnet game for clients that do not use GMCP.

The server streams the following out-of-band state while a character is playing:

- `Char.Maxstats` — maximum HP, mana, and movement
- `Char.Vitals` — current/max HP, mana, movement, plus current opponent health while fighting
- `Char.Status` — character identity plus current opponent name and health
- `Dreams.Vitals` — Dreams of the Fallen's stable game-specific vitals payload
- `Dreams.Target` — target name, current/max HP, and whether a target is active

This is intentionally sent outside the visible text stream. Current Mudlet 5.x new profiles can build Mudlet's Base UI from these standard GMCP messages, giving players automatic vitals gauges without writing triggers per character. Dreams of the Fallen now also ships its own official custom Mudlet HUD package.

### Official Dreams of the Fallen Mudlet HUD

The source and generated package live under `mudlet/DreamsOfTheFallenHUD/`. The ready-to-install file is:

`mudlet/DreamsOfTheFallenHUD/DreamsOfTheFallenHUD.mpackage`

Version 1.0.0 provides a maximalist gothic-fantasy interface while intentionally using clean, readable text. It reserves a gothic top shrine for the player state and a right-side target panel so the normal game console never renders underneath the HUD. The UI includes:

- deep-red Health gauge
- midnight-blue Mana gauge
- green Movement gauge
- character name/level/race/class line
- ornate target panel with target name, current/max HP, and percentage
- live updates from `Dreams.Vitals`, `Dreams.Target`, and `Char.Status`

The package uses Mudlet/Geyser primitives and does not bundle or require custom fonts. `build_package.py` regenerates both the Mudlet XML and `.mpackage` from `src/hud.lua`.

The server is also wired for Mudlet's `Client.GUI` automatic package installation/update extension. The official production package is hosted at:

```text
https://mud.lvthn.io/DreamsOfTheFallenHUD.mpackage
```

That address is now the built-in default, so a normal Dreams of the Fallen server launch automatically advertises HUD version `1.0.0` to GMCP-capable Mudlet clients. No server-side environment variable is required for the official deployment. For staging or mirrors, the defaults can still be overridden with:

```text
DREAMS_MUDLET_HUD_URL=https://another-host.example/DreamsOfTheFallenHUD.mpackage
DREAMS_MUDLET_HUD_VERSION=1.0.0
```

Once GMCP is negotiated, the server sends the package version and URL to Mudlet exactly once per connection. Mudlet's own **Allow server to install script packages** preference remains authoritative; the game does not bypass that client security setting.

Movement currently has a 100/100 resource pool for UI integration. Spending and regeneration rules for movement have not yet been designed, so normal room movement does not consume it yet.
