# Progression coverage audit

This document answers a narrow production question: **how far can a character actually progress with the game that exists today?** It intentionally separates what the engine permits from what the authored game meaningfully supports.

## Bottom line

- There is currently **no hard character level cap** in the XP engine. `level_for_experience()` keeps calculating levels as XP increases.
- The authored class progression has a deliberate major milestone at **level 20**. The original level 1-9 kits remain the foundation, and every class receives a new defining level-20 tool.
- Current authored zone/combat content reaches through **level 20**.
- Levels 12-15 now have **eight culturally distinct regional roads**, one rooted in each playable people: Troll, Dwarf, Moon Elf, Human, Forest Elf, Goblin, Undead, and Sporekin. None is race-locked; the cultural identity belongs to the region rather than restricting who may explore it.
- At levels 15-16 those roads overlap around **Ashcross**, a rough multi-racial frontier settlement surrounded by dangerous roads, deep-forest pockets, abandoned causeways, salvage cuts, old funerary approaches, and hidden underways.
- At levels 17-18, Ashcross opens the **Meridian Outerworks**, a looping dungeon layer beneath the frontier. Its flood loop and fossil-root loop both return to a central survey gallery, leading to the Outerworks Lockwarden and a shortcut back to town for reporting and re-entry.
- At levels 19-20, the completed Outerworks route plus **any three independent regional witness threads** open the deeper **Meridian Vault**. Players are not forced to complete one specific trio of cultures before continuing.
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
| 12-15 | **Eight Roads regional journey**: Thornwake Troll country, Deepwheel Dwarven industrial travel, Counterstar Moon Elf highroad, Blackglass Human march, Alderwake Forest Elf road, Rattlechain Goblin salvage run, Pale Undead pilgrim road, and the Rainroot Sporekin threadway |
| 15-16 | **Ashcross shared frontier**: all eight cultural approaches can physically feed the same rough frontier network without erasing their regional identity; the town retains race-aware presentation, optional pockets, and shared contracts |
| 17-18 | **Meridian Outerworks**: a first substantial frontier dungeon beneath Ashcross with a Flood Ring loop, Root Gallery loop, survey objectives, the Outerworks Lockwarden, a return winch, and a required report-back before the deeper route is trusted |
| 19-20 | **Meridian Vault**: the completed Outerworks route plus any three independent regional witnesses identify and open the deeper impossible coordinate, leading to the Nameless Custodian and the level-20 class milestone |
| 21-60 | No complete authored level-specific progression ladder yet |

## The eight level-12 regional roads

The original three regional stories remain intact and are joined by five equally concrete approaches. Every road has its own rooms, ordinary hazards, mentor, boss, witness site, local decision, physical evidence item, and Ashcross connection.

| Cultural road | Regional identity | Independent Meridian evidence |
| --- | --- | --- |
| **Thornwake — Troll** | Hunting corridors, strongholds, priests, political disagreement, harsh deep forest | Roots growing for decades around a perfectly straight absence |
| **Deepwheel — Dwarf** | Freight rails, pressure systems, registries, steam lifts, industrial depth | Instruments independently registering a location below mapped zero depth |
| **Counterstar — Moon Elf** | High-altitude observation road, contradictory charts, changing perspective | Observation plates turning a missing star into a line pointing down through the range |
| **Blackglass March — Human** | A practical relay road through remnants of Human history without treating Earth ancestry as mysticism | An archival blackglass bearing lens whose final sight line points below the frontier |
| **Alderwake — Forest Elf** | Managed woodland, road stewardship, Druidic civic maintenance rather than untouched wilderness | Decades of healthy tree rings bending around the same ruler-straight absence |
| **Rattlechain Run — Goblin** | Salvage claims, repurposed infrastructure, commerce, repair culture, rival crews | Unrelated scraps from different sites forming a perfect frame around the same missing straight edge |
| **Pale Pilgrim Road — Undead** | Funerary records, testimony discipline, memory treated as evidence rather than automatic revelation | Unrelated Undead witnesses remembering the same downward corridor none of them walked while alive |
| **Rainroot Threadway — Sporekin** | Hidden underways, guide culture, living mycelial routes, shared consciousness without loss of individual judgment | Healthy mycelium and shared thought both refusing to cross one perfectly straight silent seam |

The new routes deliberately do **not** say that a Human must take the Human road, a Goblin must take the Goblin road, and so on. A player's race changes context and recognition, but Astralis is a shared world. A Goblin can investigate Alderwake; a Forest Elf can walk the Pale Road; a Human can take Rainroot. The cultures own their histories, not the player's permission to travel.

## The level 12-20 world shape

The level 12-20 game has four distinct phases rather than one guided corridor.

**Levels 12-15: Eight Roads.** Veyra remains the launch hub, now with eight authored regional departures. Each route has a distinct cultural texture, local problem, boss, evidence, and persistent choice. Players can explore more than the minimum and can tackle roads in different orders. The five added routes are physically connected from parts of Veyra that fit their identity: the South Timber Sprawl, Greenhall, Lower Quays, Old Bridge Quarter, and Public Hearth cellar.

**Levels 15-16: shared frontier.** The routes acquire physical cross-country links around Ashcross. The approach remains intentionally messy: old causeways, deep woods, repaired freight roads, salvage culverts, a sunken watch, buried guide-routes, and a broken milestone. Ashcross itself is not a giant cosmopolitan capital. It is a practical frontier town where different peoples cooperate because roads, walls, rescue crews, and winter are shared problems. The Common still presents distinct details to all eight playable races.

**Levels 17-18: first major dungeon.** The Delvers' Yard opens the Meridian Outerworks beneath town. The dungeon is deliberately non-linear: the Flood Ring and Root Gallery form separate loops that return to the Loop Survey Gallery. The `Beneath the Crossing` contract requires the player to map both loops, defeat the Outerworks Lockwarden, use the newly opened winch back to Ashcross, and report the route. This creates a real reason to leave the dungeon and re-enter it rather than treating the entire complex as one disposable straight-line clear.

**Levels 19-20: first-act convergence.** The Deep Seam Gate opens east only when the character is level 19, has completed and reported the Outerworks route, and has finished at least **three of the eight** regional witness threads. The Meridian witness hall now compares three adjustable independent evidence sources instead of assuming the Troll, Dwarf, and Moon Elf instruments are the only valid routes to the truth. The final complex deliberately does **not** resolve into an easy prophecy, creator reveal, or singular villain. It establishes that Astralis contains structures older and stranger than the cultures currently living above them. Level 20 remains the first deliberate class capstone and `The Twentieth Step` closes the first major progression act.

This structure creates two useful player behaviors at once: there is a clear minimum route to progress, but the other five witness stories remain real optional regional content rather than becoming obsolete because the player already unlocked Meridian.

There are also level-agnostic systems—crafting, economy, social play, collectibles, hidden planes, living-world events, secrets, repeatables and exploration—that continue to add breadth around the progression ladder. They complement the 1-20 path rather than replacing future 21-60 authored progression.

## Production guardrail

`mud/progression_coverage.py` records the current coverage boundary explicitly. The regression suite sweeps levels 1-60 for XP reversibility and all five classes, including all Priest paths. Dedicated midgame regressions verify the Eight Roads production assembly, five new Veyra departures, forty new regional rooms, five additional bosses and witness items, Ashcross convergence, the any-three witness rule, both Outerworks loops, level gates, and live-server installation.

If somebody later claims a higher content ceiling, the correct process is to expand the authored content first and then deliberately raise the coverage constants and tests. This file should be updated whenever a new level band becomes genuinely playable end to end.
