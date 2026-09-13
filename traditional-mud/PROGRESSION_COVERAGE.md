# Progression coverage audit

This document answers a narrow production question: **how far can a character actually progress with the game that exists today?** It intentionally separates what the engine permits from what the authored game meaningfully supports.

## Bottom line

- There is currently **no hard character level cap** in the XP engine. `level_for_experience()` keeps calculating levels as XP increases.
- The authored class progression has a deliberate major milestone at **level 20**. The original level 1-9 kits remain the foundation, and every class receives a new defining level-20 tool.
- Current authored zone/combat content reaches through **level 20**.
- Levels 12-18 begin with the Three Roads out of Veyra: north into Troll country, east into the Dwarven industrial corridor, and upward along the Moon Elf highroad. Those routes overlap in level range and can be tackled in different orders.
- At levels 15-16 the roads physically overlap at **Ashcross**, a rough multi-racial frontier settlement surrounded by dangerous roads, deep-forest pockets, abandoned causeways, and optional ruins. Ashcross is the first shared frontier hub where race-specific treatment and the consequences of regional choices are visible together.
- At levels 17-18, Ashcross opens the **Meridian Outerworks**, a real looping dungeon layer beneath the frontier. Its flood loop and fossil-root loop both return to a central survey gallery, leading to the Outerworks Lockwarden and a shortcut back to town for reporting and re-entry.
- At levels 19-20, the completed Outerworks route and all three regional witness threads open the deeper **Meridian Vault**, an ancient complex that none of the three cultures can fully explain.
- Levels **21-60 are mechanically reachable but are not yet a complete authored progression ladder**. A character can earn the XP, but those levels still need level-specific regions, encounters, rewards, and later class milestones.

Dreams of the Fallen should therefore be described as an authored **level 1-20 game today**, with the engine and XP audit continuing through level 60.

## What was audited

The production server is imported, not just isolated modules. The audit checks the actual assembled registries and progression rules.

### XP and level math

The XP curve works past level 20 and has no hard stop. Exact cumulative XP landmarks under the current provisional formula are:

| Level reached | Total XP required |
| ---: | ---: |
| 2 | 100 |
| 5 | 700 |
| 10 | 3,200 |
| 11 | 4,000 |
| 20 | 61,975 |
| 30 | 453,350 |
| 40 | 1,527,225 |
| 50 | 3,633,600 |
| 60 | 7,122,475 |

The formula itself is valid through level 60 and beyond. That is **mechanical reachability**, not proof of authored content after level 20.

### Five-class level sweep, 1-60

All five classes are checked at every level from 1 through 60. Priest is checked for all three spiritual paths.

Current final class unlocks are:

| Class | Last authored unlock |
| --- | --- |
| Brute | Level 20 — **Unbroken Stance**, a major threat/survival stance that seizes attention, restores health, and hardens the front line |
| Wizard | Level 20 — **Starbreaker**, a high-impact single-target arcane strike |
| Druid | Level 20 — **Deep Roots**, a party-wide recovery and protection pulse |
| Priest | Level 20 — **Last Light**, a stronger party recovery and sanctuary effect available across all Priest paths |
| Necromancer | Level 20 — **Raise Grave Knight**, upgrading the persistent undead-servant identity beyond the early Skeleton |

Existing abilities still improve through the use-based ability progression system. Level 20 is intentionally a noticeable class milestone rather than simply another numerical level.

### Stats

Leveling still does **not** grant automatic innate stat points or a generic level-based stat-growth curve. Character power comes from race/class foundations, equipment, ability unlocks, skill use, authored rewards, and encounter knowledge. Future 21-60 work should decide whether that remains the long-term philosophy or whether later level bands need an additional growth layer.

### Authored content bands

| Level band | Current authored content |
| --- | --- |
| 1 | Eight distinct racial openings, all 40 race/class starting moments, starter economies and local culture |
| 2-5 | Waymeet shared frontier, contracts, Old Toll, Crooked Bell, Gloamworks and surrounding adventure content |
| 5-7 | Greywake March, Blackreed Holdfast, King's Scar and stronger shared/group encounters |
| 6-8 | Sablewater Reach and the road/faction progression toward Veyra |
| 8-10 | Veyra, Underclock, Gravewatch Keep, Vault of the First Echo, five class field commissions and broader midgame systems |
| 8-11 | Drowned Tollhouse and the upper edge of the original Veyra-era combat ladder |
| 12-18 | **Three Roads regional journey**: Thornwake Troll country, Deepwheel Dwarven industrial travel, and the Counterstar Moon Elf highroad remain independent regional investigations with their own choices, bosses, and witness evidence |
| 15-16 | **Ashcross shared frontier**: the three routes can converge through a dangerous road network into a rough multi-racial town, with race-aware room presentation, regional-choice echoes, deep-forest pockets, an abandoned culvert, and the Sunken Watch side contract |
| 17-18 | **Meridian Outerworks**: a first substantial frontier dungeon beneath Ashcross with a Flood Ring loop, Root Gallery loop, survey objectives, the Outerworks Lockwarden, a return winch, and a required report-back before the deeper route is trusted |
| 19-20 | **Meridian Vault**: the completed Outerworks route plus all three regional witnesses identify and open the deeper impossible coordinate, leading to the Nameless Custodian and the level-20 class milestone |
| 21-60 | No complete authored level-specific progression ladder yet |

### The level 12-20 world shape

The level 12-20 game now has four distinct phases rather than one guided corridor.

**Levels 12-15: regional departure.** Veyra remains the launch hub. Players can travel into Thornwake Troll country, the Deepwheel Dwarven corridor, or the Counterstar highroad. Each branch has its own culture, enemies, local conflict, boss, evidence, and persistent choice. No branch is presented as the canonical first choice.

**Levels 15-16: shared frontier.** The branches acquire physical cross-country links that meet at Ashcross. The approach is intentionally messy: old causeways, deep woods, repaired freight roads, a broken milestone, and optional pockets such as the Sunken Watch, Abandoned Culvert, and Hushwood Pocket. Ashcross itself is not a giant cosmopolitan capital. It is a practical frontier town where different peoples cooperate because roads, walls, rescue crews, and winter are shared problems. The Common presents distinct details to all eight playable races, and Steward Sere also recognizes completed regional witness work.

**Levels 17-18: first major dungeon.** The Delvers' Yard opens the Meridian Outerworks beneath town. The dungeon is deliberately non-linear: the Flood Ring and Root Gallery form separate loops that return to the Loop Survey Gallery. The `Beneath the Crossing` contract requires the player to map both loops, defeat the Outerworks Lockwarden, use the newly opened winch back to Ashcross, and report the route. This creates a real reason to leave the dungeon and re-enter it rather than treating the entire complex as one disposable straight-line clear.

**Levels 19-20: first-act convergence.** The Deep Seam Gate opens east only when the character is level 19, has completed the Ashcross Outerworks route, and carries completion flags from all three regional witness threads. It then connects physically to Confluence Camp and the existing Meridian Vault. The final complex deliberately does **not** resolve into an easy prophecy, creator reveal, or singular villain. It establishes that Astralis contains structures older and stranger than the cultures currently living above them. Level 20 remains the first deliberate class capstone and `The Twentieth Step` closes the first major progression act.

The three original witness phenomena remain unchanged:

- Troll roots have spent decades growing around a perfectly straight absence.
- Dwarven instruments independently register a location below mapped zero depth.
- Moon Elf observation plates turn an apparently missing star into a line pointing down through the range.

Ashcross and the Outerworks do not replace those stories; they make the world between them feel physically connected and give the 15-18 range a shared social center and dungeon spine before the final Meridian descent.

There are also level-agnostic systems—crafting, economy, social play, collectibles, hidden planes, living-world events, secrets, repeatables and exploration—that continue to add breadth around the progression ladder. They complement the 1-20 path rather than replacing future 21-60 authored progression.

## Production guardrail

`mud/progression_coverage.py` records the current coverage boundary explicitly. The regression suite sweeps levels 1-60 for XP reversibility and all five classes, including all Priest paths. The Ashcross/Outerworks production assembly is also covered by a dedicated regression test that checks route convergence, all eight race-aware town layers, both dungeon loops, level gates, and live-server installation.

If somebody later claims a higher content ceiling, the correct process is to expand the authored content first and then deliberately raise the coverage constants and tests. This file should be updated whenever a new level band becomes genuinely playable end to end.
