# Progression coverage audit

This document answers a narrow production question: **how far can a character actually progress with the game that exists today?** It intentionally separates what the engine permits from what the authored game meaningfully supports.

## Bottom line

- There is currently **no hard character level cap** in the XP engine. `level_for_experience()` keeps calculating levels as XP increases.
- The current class progression pass is fully authored through **level 9**. Every class has a working level-1 identity and additional tools through level 9; there are no new class ability unlocks above level 9 yet.
- Current authored zone/combat content reaches through approximately **level 12**. The Drowned Tollhouse carries the main level 10-11 tail, while the optional White Room Annex is tagged through level 12.
- The coherent, densely supported vertical slice is therefore **levels 1-10, with real tail content through levels 11-12**.
- Levels **13-60 are mechanically reachable but are not presently an authored progression game**. A character can earn the XP, but the server does not yet supply level-specific zones, class unlocks, stat growth, gear tiers, or a designed content ladder for those levels.

That means it is incorrect to describe Dreams of the Fallen as a completed level-60 game today. Level 60 is useful as a long-range audit target, not the current playable content ceiling.

## What was audited

The production server was imported, not just isolated modules. The audit checks the actual assembled registries and progression rules.

### XP and level math

The XP curve works past level 10 and has no hard stop. Exact cumulative XP landmarks under the current provisional formula are:

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

The formula itself is valid through level 60 and beyond. That is **mechanical reachability**, not proof of sufficient content.

### Five-class level sweep, 1-60

All five classes were checked at every level from 1 through 60. Priest was checked for all three spiritual paths.

Current final class unlocks are:

| Class | Last authored unlock |
| --- | --- |
| Brute | Level 8 — Rallying Roar |
| Wizard | Level 9 — Rift Lance |
| Druid | Level 9 — Verdant Pulse |
| Priest | Level 9 — Sanctuary; Resurrection is level 5 and common support unlocks fill the path |
| Necromancer | Level 9 — Wither |

The ability lists remain legal at levels 10-60, but they stop growing. Existing abilities can continue improving through use-based skill progression.

### Stats

Leveling currently does **not** grant automatic innate stat points or a level-based HP/mana/stat growth curve. Character power comes primarily from starting race/class stats, equipment, ability unlocks, skill use, and authored item progression. That is viable for the current early game, but it is another reason levels 12-60 should not be presented as finished progression yet.

### Authored content bands

| Level band | Current authored content |
| --- | --- |
| 1 | Eight distinct racial openings, all 40 race/class starting moments, starter economies and local culture |
| 2-5 | Waymeet shared frontier, contracts, Old Toll, Crooked Bell, Gloamworks and surrounding adventure content |
| 5-7 | Greywake March, Blackreed Holdfast, King's Scar and stronger shared/group encounters |
| 6-8 | Sablewater Reach and the road/faction progression toward Veyra |
| 8-10 | Veyra, Underclock, Gravewatch Keep, Vault of the First Echo, five class field commissions and broader midgame systems |
| 8-11 | Drowned Tollhouse, including rooms explicitly tagged for level 10-11 |
| 10-12 | Optional White Room Annex deep challenge |
| 13-60 | No complete authored level-specific progression ladder yet |

There are also level-agnostic systems—crafting, economy, social play, collectibles, hidden planes, living-world events, secrets, repeatables and exploration—that can continue entertaining a character outside a strict level band. They do not substitute for a complete 13-60 combat/progression ladder.

## Production guardrail

`mud/progression_coverage.py` records the current coverage boundary explicitly. The regression suite sweeps levels 1-60 for XP reversibility and all five classes, including all Priest paths. If somebody later claims a higher content ceiling, the correct process is to expand the authored content first and then deliberately raise the coverage constants and tests.

This file should be updated whenever a new level band becomes genuinely playable end to end.
