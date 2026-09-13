# Progression coverage audit

This document answers a narrow production question: **how far can a character actually progress with the game that exists today?** It intentionally separates what the engine permits from what the authored game meaningfully supports.

## Bottom line

- There is currently **no hard character level cap** in the XP engine. `level_for_experience()` keeps calculating levels as XP increases.
- The authored class progression now has a deliberate major milestone at **level 20**. The original level 1-9 kits remain the foundation, and every class receives a new defining level-20 tool.
- Current authored zone/combat content now reaches through **level 20**.
- Levels 12-20 stop being one guided corridor. From Veyra, players can travel north into Troll country, east into the Dwarven industrial corridor, or upward along the Moon Elf highroad. Those routes overlap in level range and can be tackled in different orders.
- The three regional investigations converge at levels 19-20 in the Meridian Vault, an ancient complex that none of the three cultures can fully explain.
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
| 12-16 | **Thornwake Troll country**: deep forest, hunting culture, priests, strongholds, and a civil conflict with a real player choice rather than an evil-Troll extermination plot |
| 12-18 | **Deepwheel Dwarven corridor**: freight rails, pressure infrastructure, checkpoints, steam lifts, registries, and increasingly deep mountain travel |
| 13-18 | **Counterstar highroad**: thin air, huge sky, old Moon Elf observing stations, contradictory charts, and evidence that changes with altitude |
| 19-20 | **Meridian Vault**: all three investigations identify the same impossible coordinate, opening an ancient multi-cultural capstone dungeon and the level-20 class milestone |
| 21-60 | No complete authored level-specific progression ladder yet |

### The level 12-20 world shape

The key production change is structural: **Veyra becomes a hub instead of the next link in a single chain.** A level-12 character can head north or east, while the high road opens shortly afterward. Each branch has its own culture, enemies, local conflict, boss, evidence, and persistent choice. No branch is presented as the one canonical order.

The three stories share an underlying physical anomaly without sharing an explanation:

- Troll roots have spent decades growing around a perfectly straight absence.
- Dwarven instruments independently register a location below mapped zero depth.
- Moon Elf observation plates turn an apparently missing star into a line pointing down through the range.

Only after completing all three regional witness threads can a level-19 character reach the Meridian Vault. The final complex deliberately does **not** resolve into an easy prophecy, creator reveal, or singular villain. It establishes that Astralis contains structures older and stranger than the cultures currently living above them.

There are also level-agnostic systems—crafting, economy, social play, collectibles, hidden planes, living-world events, secrets, repeatables and exploration—that continue to add breadth around the progression ladder. They complement the 1-20 path rather than replacing future 21-60 authored progression.

## Production guardrail

`mud/progression_coverage.py` records the current coverage boundary explicitly. The regression suite sweeps levels 1-60 for XP reversibility and all five classes, including all Priest paths. If somebody later claims a higher content ceiling, the correct process is to expand the authored content first and then deliberately raise the coverage constants and tests.

This file should be updated whenever a new level band becomes genuinely playable end to end.
