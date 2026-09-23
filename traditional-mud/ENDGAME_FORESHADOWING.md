# The Hinge: early-game foreshadowing contract

This is an optional, spoiler-aware bridge between the current levels 1-40 world
and the proposed level 41-50 Hinge storyline / level 50 Unstruck Bell raid.
**This change does not create the Hinge region or raid.** It plants tangible
details now and provides durable, per-character callbacks for later content.

## Player experience

| When | Place | Natural affordance | Optional discovery |
| --- | --- | --- | --- |
| Starter | Junk City, Patchwork Plaza | Ancient arc under busy paving | EXAMINE MURAL |
| Early shared world | Waymeet Crossroads | Weathered marks beneath a bridge notice | READ CHALK MARKS |
| Early shared world | Waymeet Commonhouse Yard | Nimra Dawnskein, a child with a pebble game | TALK NIMRA, LISTEN CHILDREN |
| Copperwake caravan days | Waymeet Lantern Market | An itinerant trader's oddment tray | BROWSE WANDERER, BUY WANDERER CLAPPERLESS WAYBELL |
| While carrying the bell | Waymeet Crossroads / Commonhouse | The bell has no clapper | LISTEN BELL |
| Optional level ~18 | Quiet Belfry | Empty, still-loaded bell frame | LISTEN FRAME; bell owners may COMPARE BELL |
| Optional level ~34 | Noonwatch Lens Room | An old civilian sighting frame with a blank bearing | READ LENS SCRATCHES; players who heard Nimra **and** read the chalk may TRACE FIFTH NOTCH |

The Copperwake bell is priced at **nine sparks**, with no combat statistics
and no gameplay power. Its appearances follow the existing daily event
rotation, so it is intermittent, not a permanent hidden shop. The bell
is an extra connection, not required to understand or finish any story.
Every race can encounter shared Waymeet clues without visiting Junk City.

Nimra is a named, talkable character, not an anonymous one-shot clue.
Her pebble game and grandmother's unfinished tune work as ordinary local
color now. Rare ambient chatter lets nearby residents notice recurring
chalk after wet weather, and Nimra sometimes hums during daytime. These
use the established Waymeet presence requirement and cooldowns.

## Memory and payoff

The eight named discoveries are stored in the existing per-character
character_discoveries table and published to the collective wiki **only
after a player actually uncovers them**. There is no new tracked quest,
mandatory flag, XP prize, completion counter, class gate or race gate.
The existing 360-secret discovery catalog is unchanged.

mud.endgame_omens.threshold_echoes(database, character_id) is the future
level-50 integration seam. Once the Hinge raid is authored, play its same
core introduction to everyone. Then append **at most three** optional
character-specific recognition lines returned by this function. Those
lines connect the gateway's ground plan to the Junk City mural, ward script
to Waymeet chalk, opening notes to Nimra, bell mechanism to Quiet Belfry,
fifth bearing to Noonwatch, and carried waybell to its larger counterpart.
Deliver these once at a dramatic moment, not every time the door is viewed.

The level-50 climax can reveal why the sealed Hinge exists. Early content
intentionally avoids declaring what is beyond it, the gods' motives, or
what the missing fifth sign means. The keeper's twist and any god-killing
arc remain future story beats.

## Authoring rules

- Early text must sound locally ordinary. Goblins see salvaged stone;
  road workers see suspect chalk; children know a rhyme; merchants sell junk.
- Shared clues must not assume a character completed one homeland's
  opening, met a particular faction, or kept a purchasable trinket.
- Midgame clues stand on their own. Remembering early details offers
  an additional line, never access or progression.
- No early NPC is omniscient. Nimra does not know the fifth road's
  destination. The merchant does not know the bell's purpose.
- The endgame should revisit these specific people and objects rather
  than replacing the mysteries with unrelated exposition.
- Avoid spoilers in global broadcasts, UI objectives, quest completion
  text, or the public wiki before actual player discovery.

## Engineering

Production assembles omen content after install_roadside_discoveries_runtime
so every destination room already exists. The separate omen registry uses
attempt_discovery_command and the normal database/wiki machinery; this
does not change the validated size of the main discovery catalog. The runtime
wraps commands after the regular discovery layer so ordinary LOOK, TALK,
shops, movement, quest interactions and combat keep their handlers. Room
augmentations merge on feature/layer key and do not replace exits. Content
and runtime installers are idempotent.

Unit coverage is in tests/test_endgame_omens.py. Production's installer
reachability tests additionally ensure both installers are connected.
