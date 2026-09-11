# Eight-Race Starter Loop Matrix

The launch rule for **Dreams of the Fallen** is simple: a new player should learn what a people is like by **doing something that culture considers normal**, not by reading a lore lecture.

These are not eight copies of the same tutorial with different scenery. Each race gets a compact, playable opening built around a different kind of decision or interaction. Class lessons can layer onto these openings, but the racial hook belongs to the place and culture first.

| Race | First playable hook | What the player actually does | What the play demonstrates |
| --- | --- | --- | --- |
| Human | **Blackwall Civic Readiness** | Read a signal board, run a civic drill, investigate physical evidence, fight a burrower, search what remains | Humans are fast learners living inside a practical, insular civic culture; the “Demon” identity changes meaning once the player meets outsiders |
| Forest Elf | **The Old River Path** | Leave a comfortable town, follow the river, study a waystone, listen at still water, reach the boundary oak | The forest is home rather than scenery, and stewardship means observation before intervention; beauty and danger coexist |
| Moon Elf | **The Third Chair** | Sit in a civic mediation, hear both sides restate each other, inspect the same problem from two physical viewpoints, choose the next step | Perspective and revision are procedures the culture practices, not slogans it recites |
| Dwarf | **By Stamp and Steam** | Register a work order, obtain a union counterseal, read a pressure gauge, operate the correct valve, run a lift test | Industry is social infrastructure: craft, labor rights, paperwork, safety, and machinery all support one another |
| Goblin | **Three Bells** | Claim one piece of salvage, bargain, settle an old ownership mark, repurpose the part, encounter cross-cultural value, register a personal mark | Goblin life is about use, provenance, negotiation, repair, and finding a better next purpose rather than worshiping what something used to be |
| Troll | **A Fire Before Pride** | Read the wind, gather deadfall, build a windbreak, prepare and light a fire, endure controlled cold, recover beside the hearth | Troll toughness is preparation and hard-earned survival knowledge, not reckless strength or low intelligence |
| Undead | **No Voice Above You** | Listen for a dead master, discover silence, inspect the surviving command scar, sever the order, later make voluntary choices about memory and service | Undead society is built around personhood and autonomy after reanimation rather than simply being spooky corpses |
| Sporekin | **The Chorus Beneath** | Follow living mycelial threads, climb by sensory cues, reach the surface, then act where the Chorus becomes quieter | Shared consciousness and individual judgment coexist; connection does not erase personhood |

## Implementation rule

Every launch race must have:

1. an authored starting room with at least one real exit;
2. a registered first quest or opening thread;
3. at least one interaction that could not simply be reskinned for every other race;
4. a clear completion signal for later content to build on; and
5. a persisted starting room and bind point as soon as the character is created.

`mud/starter_race_loops.py` encodes this contract and the production entrypoint validates it at startup. If a future refactor removes a race's first room or quest, the server should fail loudly during development instead of quietly giving that race an unfinished start.
