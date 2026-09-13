from __future__ import annotations

from dataclasses import dataclass, replace

import mud.first_ten_adventures as adventures
import mud.first_ten_progression as first_ten
import mud.world as legacy_world
from mud.room_engine import DescriptionLayer, RoomAugmentation, ViewCondition
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE
from mud.waymeet_frontier import WAYMEET_CROSSROADS_KEY
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class StoryPartner:
    key: str
    name: str
    short_description: str
    role: str
    talk_alias: str


@dataclass(frozen=True, slots=True)
class StoryScene:
    setup: tuple[str, ...]
    disagreement: tuple[str, ...]
    decision: tuple[str, ...]
    aftermath: tuple[str, ...]
    reveal_echo: str
    decision_echo: str
    aftermath_echo: str


def _scene(
    setup: tuple[str, ...],
    disagreement: tuple[str, ...],
    decision: tuple[str, ...],
    aftermath: tuple[str, ...],
    reveal_echo: str,
    decision_echo: str,
    aftermath_echo: str,
) -> StoryScene:
    return StoryScene(setup, disagreement, decision, aftermath, reveal_echo, decision_echo, aftermath_echo)


STORY_PARTNERS: dict[str, StoryPartner] = {
    "human": StoryPartner(
        "first_ten_human_gate_clerk_mara_vale",
        "Gate-Clerk Mara Vale",
        "a sharp-eyed gate clerk with three bundles of reports tied in different colors",
        "Blackwall gate clerk who challenges Elian's confidence in the paperwork",
        "mara",
    ),
    "forest_elf": StoryPartner(
        "first_ten_forest_pathwarden_ilye_mosswake",
        "Pathwarden Ilye Mosswake",
        "a young pathwarden with wet boots, a bark knife, and strong opinions about old boundaries",
        "Forest pathwarden who pushes Sael to defend tradition rather than merely repeat it",
        "ilye",
    ),
    "moon_elf": StoryPartner(
        "first_ten_moon_surveyor_tel_ardan",
        "Surveyor Tel Ardan",
        "a narrow-faced surveyor carrying a brass sighting frame and several impatient corrections",
        "High Horizon surveyor who prefers one clean answer to Yra's unfinished records",
        "tel",
    ),
    "dwarf": StoryPartner(
        "first_ten_dwarf_clerk_bren_coppervein",
        "Pressure-Clerk Bren Coppervein",
        "a square-bearded clerk with ink on both cuffs and a pressure chart folded into his belt",
        "Foundry pressure clerk who believes procedure should be trusted until evidence proves otherwise",
        "bren",
    ),
    "goblin": StoryPartner(
        "first_ten_goblin_riveter_nix_hookspit",
        "Riveter Nix Hookspit",
        "a wiry riveter with one brass tooth and a belt full of bolts sorted by whether they still work",
        "Rattlefen riveter who distrusts any repair that cannot survive being kicked",
        "nix",
    ),
    "troll": StoryPartner(
        "first_ten_troll_hunter_orr_redtooth",
        "Hunter Orr Redtooth",
        "a broad young hunter wearing far more trophy teeth than Varka thinks are necessary",
        "Frostroot hunter learning the difference between courage and needing to prove courage",
        "orr",
    ),
    "undead": StoryPartner(
        "first_ten_undead_archivist_pell_ashbone",
        "Archivist Pell Ashbone",
        "a carefully jointed archivist carrying old ownership tablets in padded sleeves",
        "Necropolis archivist who values accurate memory enough to argue about when it stops being authority",
        "pell",
    ),
    "sporekin": StoryPartner(
        "first_ten_sporekin_tender_moss_under_stone",
        "Tender Moss-Under-Stone",
        "a squat amber-capped Sporekin with fresh mycelial bandages wrapped around both hands",
        "Lumen Hollow tender who trusts the Chorus instinctively but is learning to hear its seams",
        "moss",
    ),
}


RELATIONSHIP_LINES: dict[str, tuple[str, str, str, str]] = {
    "human": (
        "Elian gives you the same measuring look he gives a new road crew. 'Finish one problem cleanly and I may start believing the next report you bring me.'",
        "Elian taps the repaired entry in his slate. 'You found the failure between people, not the crack everybody could see. That was useful.'",
        "Elian no longer checks your account against Mara's notes before answering. 'Waymeet knows your name now. Try not to make me regret that.'",
        "Elian offers the slate instead of holding it away from you. 'You are past errands. Tell me what Blackwall is missing.'",
    ),
    "forest_elf": (
        "Sael studies your boots before your face. 'Come back with mud on them and I will know you actually looked.'",
        "Sael nods toward the grove you helped correct. 'You were willing to admit an old good choice had become a new bad one. Keep that habit.'",
        "Sael smiles when you mention Waymeet. 'You learned to translate a boundary instead of demanding strangers inherit our instincts.'",
        "Sael shifts aside to make room at the keeper's map. 'I do not need to tell you where to kneel anymore. Show me what you noticed.'",
    ),
    "moon_elf": (
        "Yra keeps one notebook closed. 'I would rather see whether you notice the missing account without being told where it is.'",
        "Yra writes your name beside two incompatible witness marks. 'You did not force agreement where the world offered perspective instead.'",
        "Yra hands you the lowland map first. 'You have stopped confusing elegance with completeness. That makes you useful outside the terraces.'",
        "Yra leaves the fourth page open when you approach. 'You know why it is blank. Sit.'",
    ),
    "dwarf": (
        "Orla points at the machinery before acknowledging you. 'Machines are honest. Departments are creative. Learn which one you are listening to.'",
        "Orla closes the fault ledger. 'You found three correct procedures making one dangerous system. That is better than finding one fool.'",
        "Orla slides an off-spec fitting across the bench. 'You came back from Waymeet with evidence instead of embarrassment. Good.'",
        "Orla stops calling you trainee. 'If I disagree with your safety call now, I expect you to argue back.'",
    ),
    "goblin": (
        "Pella squints at you over three ledgers. 'You look new enough to still think a good fix and a good system are the same thing.'",
        "Pella knocks a knuckle against the span you helped save. 'Held yesterday. Held today. Now I care what you think.'",
        "Pella flicks a Waymeet claim chit toward you and catches it again. 'You explained Goblin law without making it less Goblin. That's a trick worth keeping.'",
        "Pella shoves one of the ledgers into your hands. 'Quit waiting for me to tell you what's useful. You have your own eyes now.'",
    ),
    "troll": (
        "Varka glances at your weapon, then at the weather. 'If you looked at the first thing longer than the second, start over.'",
        "Varka scratches out the hunt mark beside the old tracks. 'You let evidence spoil a good story about a monster. That is harder than hunting.'",
        "Varka gives you the warm side of the fire without comment. 'Waymeet did not make you softer. It made you clearer.'",
        "Varka asks your reading of the wind before giving hers. That is the first sign she now treats you as another hunter rather than a student.",
    ),
    "undead": (
        "Esh turns an old ownership tablet face down. 'A record can tell you where you came from. Watch carefully for the moment it starts telling you where you must go.'",
        "Esh has already entered your correction into the new ledger. 'You preserved the memory and removed its teeth. Correct.'",
        "Esh sets a living traveler's petition beside an old death record. 'You now know why neither deserves automatic obedience.'",
        "Esh leaves the registrar's chair opposite them empty for you. 'Read the record. Then tell me what the dead are choosing now.'",
    ),
    "sporekin": (
        "Seven-Rings lets a long silence pass through the Chorus before speaking aloud. 'I want your own answer first.'",
        "Seven-Rings touches one pale ring on their cap. 'You heard repetition hiding inside consensus. The Chorus remembers that you questioned it.'",
        "Seven-Rings asks what Waymeet smelled like before asking what it taught you. 'Good. Firsthand memory has edges inherited memory loses.'",
        "Seven-Rings does not reach for the Chorus when you arrive. 'Speak as yourself. We can join the answer afterward.'",
    ),
}


PARTNER_LINES: dict[str, tuple[str, str, str, str]] = {
    "human": (
        "Mara mutters, 'If Elian says the forms are clear, ask him which of the six versions he means.'",
        "Mara holds up a retied report bundle. 'Your fix made us change where warnings go. That is rarer than changing stone.'",
        "Mara says, 'Three caravan crews have started using your revised marks without asking what they mean. That is the point.'",
        "Mara grins. 'He gives you the slate now. Took me four years.'",
    ),
    "forest_elf": (
        "Ilye says, 'Sael calls it listening. Mostly it means being willing to be embarrassed by a root.'",
        "Ilye points toward the changed water line. 'I argued for leaving it alone. I was wrong. The tree did not care about my pride.'",
        "Ilye says, 'Outsiders are using the new markers without trampling the old beds. I hated how simple the fix looked.'",
        "Ilye nods once. 'I still disagree with you sometimes. It feels different now.'",
    ),
    "moon_elf": (
        "Tel says, 'Yra thinks every contradiction deserves a chair. I think some deserve arithmetic.'",
        "Tel adjusts his sighting frame. 'You were right about the moving shadow. I dislike how satisfying that was.'",
        "Tel says, 'The lowland road ledger is ugly. I have started carrying a copy.'",
        "Tel offers you his sighting frame without explaining it. 'Check me.'",
    ),
    "dwarf": (
        "Bren says, 'Procedure is what keeps clever people from improvising us into funerals.'",
        "Bren rubs ink from one cuff. 'I still believe that. I also renamed three fault categories this morning.'",
        "Bren lifts the flexible fitting from Waymeet. 'Off-spec. Documented. Tested. Annoyingly excellent.'",
        "Bren says, 'Orla lets you overrule a bell now. Do not enjoy that too much.'",
    ),
    "goblin": (
        "Nix kicks a nearby support. 'Pella hates that test. Support doesn't.'",
        "Nix points at a fresh load mark painted across three old patches. 'Now the whole heap knows where the weight goes.'",
        "Nix says, 'That foreign owner sent back a box of bent fasteners. Called it a thank-you. Good manners, that.'",
        "Nix grins around his brass tooth. 'Your plate held. I kicked it twice.'",
    ),
    "troll": (
        "Orr fingers one of his trophy teeth. 'Sometimes a big track is just a big thing. Sometimes it is dinner.'",
        "Orr has removed one tooth from his necklace. He refuses to explain which hunt it came from.",
        "Orr says, 'The traveler who refused our fire came back with salt. Varka made me accept it politely.'",
        "Orr touches your empty trophy cord. 'I understand it now. Mostly.'",
    ),
    "undead": (
        "Pell says, 'If we alter an old record, we risk lying about the past.'",
        "Pell carefully adds a new annotation beside the untouched old line. 'We found a way to tell the truth without reenacting it.'",
        "Pell says, 'The living petitioners came back. Less afraid. Still afraid. That seems honest.'",
        "Pell has begun indexing records by chosen name first. 'Archives can learn.'",
    ),
    "sporekin": (
        "Moss-Under-Stone says, 'The Chorus feels true because so many of us feel it together.'",
        "Moss flexes newly bandaged fingers. 'One hurt node sounded like all of us. I keep thinking about that.'",
        "Moss says, 'Your Waymeet memory has mud in it. The old shared memory had no mud. I prefer yours.'",
        "Moss lets their own thought finish before joining the Chorus. 'I practice now.'",
    ),
}


STORY_SCENES: dict[tuple[str, str], StoryScene] = {
    ("human", "home_crisis"): _scene(
        ("Elian spreads three repair slips over the gate table. 'Same crack, three departments, nobody owns it.'", "Mara answers without looking up. 'Four departments. The hauler report was filed under freight.'"),
        ("A mason insists the wall passed inspection. Mara insists the warning was real. Elian says both can be true and that is exactly the problem.",),
        ("When you carry the warning back through the proper hands, Mara reties the report bundle with one shared color instead of three departmental ones.",),
        ("Elian signs the changed handoff rule with your name in the margin. Mara makes sure the gate crews actually receive it." ,),
        "The old warning mark is now impossible for you to miss; what looked like a masonry failure has become a lesson in lost handoffs.",
        "A fresh cross-department tag hangs beside the repair, linking the stonework to the warning that once vanished between desks.",
        "Blackwall's gate board now carries one shared crack-report procedure, with your investigation cited as the reason it exists.",
    ),
    ("human", "wider_world"): _scene(
        ("Elian hands you a Blackwall road placard. 'Readable at a gallop, according to us.'", "Mara snorts. 'According to people who already know what every horn mark means.'"),
        ("At Waymeet, Marshal Aven places a Goblin driver's sketch beside the official sign. The sketch is crude and instantly understandable; the official mark is elegant and opaque.",),
        ("You help translate the sign into shapes that preserve Blackwall meaning without requiring Blackwall upbringing to decode it.",),
        ("Mara later pins the Waymeet version beside the original rather than replacing it. 'Translation is evidence, not surrender,' she says." ,),
        "Once you have seen the outsider reports, the road signs here read less like neutral instructions and more like a private language painted in public.",
        "The revised shared-road mark uses Blackwall geometry but adds simple travel symbols that a stranger can understand at speed.",
        "Waymeet's road board now displays a Blackwall mark with a plain-language companion symbol, and travelers actually use it.",
    ),
    ("human", "capstone"): _scene(
        ("Elian rings the gate alarm once. 'Wagon jam, wet grade, crowd building. Procedure until procedure stops helping.'", "Mara already has the emergency ledger open. 'And if someone without a badge has the better answer, write that down too.'"),
        ("A Goblin axle hand proposes cutting the pin while a Dwarf braces the wagon. One guard objects that neither is gate crew. Elian looks at you instead of answering for you.",),
        ("You coordinate the mixed crew, preserve the evacuation lane, and let competence outrank uniform long enough to clear the danger.",),
        ("Afterward, Elian has Mara add two new names to the emergency roster: people who do not work for Blackwall but proved they could keep it standing." ,),
        "The blocked gate no longer looks like a Human problem; you can see exactly where strangers' skills became part of Blackwall's survival.",
        "A temporary mixed-crew mark remains chalked beside the gate, recording who braced, cut, carried, and kept the lane open.",
        "The gate watch now keeps an auxiliary emergency roster for trusted outsiders, a small institutional change born from the crisis you resolved.",
    ),
    ("forest_elf", "home_crisis"): _scene(
        ("Sael kneels beside a yellowing root fan. 'Do not call it blight until the tree agrees.'", "Ilye folds his arms. 'The diversion saved three saplings. We were right to build it.'"),
        ("The soaked old root lies directly below the protective channel. Ilye goes quiet when Sael asks whether a correct choice is allowed to expire.",),
        ("You reopen a narrow water path and leave the saplings protected while the old root finally drains.",),
        ("Ilye returns the next morning with a smaller channel marker and places it beside yours without being asked." ,),
        "The sick root now tells a different story: not invasion, but a protection that outlived the conditions that made it wise.",
        "Water threads through a new shallow cut, sparing the saplings without drowning the older root.",
        "The grove's boundary notes now include a date to re-check the diversion, an unusual admission that stewardship decisions can expire.",
    ),
    ("forest_elf", "wider_world"): _scene(
        ("Sael gives you a bundle of trail marks. 'These make perfect sense to anyone raised here.'", "Ilye says, 'That sentence is doing too much work.'"),
        ("At Waymeet, three travelers describe trying to obey the forest signs and reaching three different conclusions. None were careless.",),
        ("You recast the markers around actions—safe water, fragile ground, permitted crossing—instead of inherited symbols alone.",),
        ("Sael keeps both systems side by side. Ilye watches an outsider choose the correct trail without asking for help and finally smiles." ,),
        "The old trail symbols now look beautiful but incomplete to you; you can see the unstated childhood knowledge packed into each one.",
        "New companion marks explain what a traveler should do rather than assuming they already understand why.",
        "Waymeet's green approach carries paired Forest signs: the old cultural marks and the practical translation you helped author.",
    ),
    ("forest_elf", "capstone"): _scene(
        ("Sael shows you claw marks crossing the new safe path. 'Something has learned our boundary faster than we expected.'", "Ilye reaches for his bow. 'Then the boundary failed.'"),
        ("The animal trail follows the resin scent of the new markers. Ilye realizes the supposedly safer system created a hunting line straight through the crossing.",),
        ("You change the marker resin, reroute one segment, and protect travelers without turning the prowler into a villain for following its senses.",),
        ("Sael ties a living knot at the crossing. Ilye leaves the bow unstrung while he helps move the final marker." ,),
        "The predator's route makes the cost of your own earlier solution visible; the forest did not separate your good intentions from their effects.",
        "The safe crossing now bends away from the scent line, and the new markers use a resin the prowler ignores.",
        "The living boundary here has become a maintained relationship rather than a fixed line, with your correction preserved in the keeper notes.",
    ),
    ("moon_elf", "home_crisis"): _scene(
        ("Yra places two witness sketches on the same table. 'Both sworn. Both impossible together.'", "Tel taps the cleaner one. 'Then one witness is wrong.'"),
        ("The tower shadow has moved between observations. Tel measures the angle twice before admitting time, not honesty, created the contradiction.",),
        ("You amend the record to include when each account was taken instead of choosing a preferred witness.",),
        ("Tel adds a time notch to his own sighting frame. Yra leaves both original accounts intact beneath the correction." ,),
        "The two conflicting witness marks now align in your mind once the moving shadow is treated as part of the evidence.",
        "A new time notch accompanies the terrace record, making future observations harder to mistake for simultaneous truth.",
        "High Horizon recorders now stamp observation time beside sight lines in disputes like this, a habit traced to your correction.",
    ),
    ("moon_elf", "wider_world"): _scene(
        ("Yra gives you a beautiful elevation chart. 'Take this to people who navigate by mud and hunger.'", "Tel says, 'And try not to apologize for the fact that it is accurate.'"),
        ("At Waymeet, Aven's ugly road ledger predicts travel time better than the chart while the chart predicts dangerous grade better than the ledger.",),
        ("You combine the two instead of declaring one method superior: elevation where terrain matters, travel time where bodies do.",),
        ("Tel later copies one of Aven's rough timing marks into his own survey book. He does it very small." ,),
        "The elegant High Horizon chart and battered lowland ledger now look like partial instruments rather than rival truths.",
        "A combined route note pairs grade with expected travel time, useful to both surveyors and tired caravan crews.",
        "Waymeet's high-road board now carries Moon Elf elevation marks beside plain travel-time estimates, neither treated as the footnote.",
    ),
    ("moon_elf", "capstone"): _scene(
        ("Yra arranges three chairs around a dispute table and leaves one place empty. 'We have two witnesses and a record. Something is still missing.'", "Tel says, 'Weather is not a witness.'"),
        ("A fast storm crossed the route between observations. Tel stares at the rain trace and says, reluctantly, 'Weather can apparently testify.'",),
        ("You settle the dispute by recording the changing conditions instead of assigning fault to either witness.",),
        ("Yra gives you the unfinished token. Tel, without irony, pulls out the empty fourth chair for the next case." ,),
        "The dispute no longer appears to require a winner; the missing condition is as tangible to you as either witness statement.",
        "The amended record now preserves both accounts and the storm interval that made them diverge.",
        "A fourth chair remains permanently available at this terrace table, a civic reminder to ask what the argument has not represented yet.",
    ),
    ("dwarf", "home_crisis"): _scene(
        ("Orla lays three ledgers open. 'Three shops, one pressure fault, three names for it.'", "Bren says, 'Each name is correct inside its department.'"),
        ("You trace the same vibration through three reporting systems. Bren's defense of procedure becomes quieter as the duplicated fault line emerges.",),
        ("You create one cross-shop fault mark and route it through all three departments before the next shift starts.",),
        ("Bren inks the new category himself. Orla makes him sign the revision instead of pretending the old forms were always meant that way." ,),
        "The pressure symptom is now impossible to see as three unrelated entries; the ledgers have become evidence of a system-level blind spot.",
        "A single cross-shop fault mark now follows the pipe run through every department that touches it.",
        "The foundry's reporting board carries a shared fault category created after your investigation, linking departments that once spoke past each other.",
    ),
    ("dwarf", "wider_world"): _scene(
        ("Orla hands you a standard fitting and a rejection stamp. 'Waymeet has been using something else. Find out whether they are clever or lucky.'", "Bren says, 'Those are not approved categories.'"),
        ("At Waymeet, the off-spec Goblin fitting flexes under road movement while mountain-standard iron shows hairline stress. Bren would hate the test result.",),
        ("You document the exception with load limits and inspection intervals instead of either banning it or pretending standards do not matter.",),
        ("Back home, Bren reads every test twice before filing the flexible fitting under APPROVED EXCEPTION rather than FAILURE." ,),
        "The off-spec fitting now reads as measured evidence rather than sloppy work; its flex is the reason the bridge survives movement.",
        "A stamped exception sheet hangs beside the fitting, recording exactly where its unusual behavior is safer and where it is not.",
        "Waymeet's repair board now carries a Dwarven-approved exception standard, proof that rigor can document adaptation rather than forbid it.",
    ),
    ("dwarf", "capstone"): _scene(
        ("Orla hears the fault bell and says only, 'Crew first.'", "Bren points at the production clock. 'One bell of shutdown triggers a quota review.'"),
        ("The emergency replacement that fits is partly foreign work. Bren looks from the drawing to the hot line and asks whether using it makes the whole repair unofficial.",),
        ("You stop the line, clear the workers, document the mixed repair, and restart only after a fresh inspection.",),
        ("Orla stamps the lost production bell onto brass. Bren signs the exception record beneath your name." ,),
        "The repaired line carries visible evidence that the safest answer came from outside the original drawing.",
        "Fresh inspection marks surround the mixed replacement, documenting why the exception is safe instead of hiding that it is unusual.",
        "The shift board records one deliberately lost production bell as a safety success, and workers point to it when supervisors hurry them.",
    ),
    ("goblin", "home_crisis"): _scene(
        ("Pella dumps six repair tags onto a crate. 'Every one of these says FIXED.'", "Nix kicks the nearest support. 'Every one of them is telling the truth.'"),
        ("The load marks show each successful patch pushed stress into the next one. Nix stops grinning when he realizes his favorite brace is part of the chain.",),
        ("You mark the whole span as one load system, keep the ugly pieces that work, and replace the clever patch that makes three neighbors worse.",),
        ("Nix paints the new load line across everybody's repairs, including his own. Pella makes the mark legally part of every future claim." ,),
        "The heap no longer looks like six unrelated repairs; you can see the weight traveling from one clever fix into the next.",
        "A bright load line now crosses mismatched beams and plates, showing future repairers what the whole structure is doing.",
        "Rattlefen's claim board now requires major repairs to mark what they push on, a small rule born from the span you kept above the mud.",
    ),
    ("goblin", "wider_world"): _scene(
        ("Pella hands you a claim stamp. 'Foreign wreck. Everybody wants the shiny bits. Find out who actually owns what.'", "Nix says, 'I call latch if it is unclaimed.'"),
        ("At Waymeet, the owner ignores the polished latch and grabs a battered map case full of family notes. Nix would have priced them as scrap paper.",),
        ("You separate rescue property, repairable property, and legal salvage in terms both sides can understand before anyone stamps a claim.",),
        ("The owner leaves with the map case and sends Rattlefen the broken brass later. Pella calls that 'repeat business with feelings attached.'" ,),
        "The wreck's value has rearranged itself in your eyes; the battered map case matters more than the polished pieces attracting every scavenger.",
        "Clear rescue, repair, and salvage marks now divide the wreck so nobody has to guess what another culture means by 'claim.'",
        "Waymeet keeps a copy of the Goblin salvage explanation beside its wreck notices, and arguments around new crashes start quieter than they used to.",
    ),
    ("goblin", "capstone"): _scene(
        ("Pella arrives with floodwater around her boots. 'Tower leaning. Everybody saving their own junk. Congratulations, law is now happening at speed.'", "Nix is already hauling boiler skin toward the weakest span. 'Argue while carrying!'"),
        ("The supposed scavengers are mostly neighbors with legitimate claims. Pella asks who gets priority when every claim is reasonable and the water is not waiting.",),
        ("You mark rescue material first, private property second, future salvage third, and brace the tower with whatever bears load now.",),
        ("When a loaded wagon crosses, Nix kicks your final plate. Pella waits for the ring, then stamps it with your mark." ,),
        "The crowd around the flood damage no longer separates neatly into owners and thieves; you can see overlapping claims that need a rule before they become a fight.",
        "Emergency marks divide rescue stock, private property, and future salvage in paint bright enough to read through rain.",
        "The flood district still carries your emergency claim marks, and later repair crews have kept the three-priority system instead of erasing it.",
    ),
    ("troll", "home_crisis"): _scene(
        ("Varka points at the snow. 'Tell me what happened before Orr tells you what he hopes happened.'", "Orr says, 'Big tracks. Big hunt. Simple.'"),
        ("The scent line and stride both lead away from camp. Orr follows the prints backward twice before admitting the creature chose retreat.",),
        ("You set a watch instead of a hunt, keeping horns ready while leaving the unknown animal a way to stay unknown.",),
        ("Orr removes a fresh hunt notch from the board. Varka says nothing, which embarrasses him more than a lecture would." ,),
        "The huge tracks now read as retreat instead of invasion; the wind makes the difference impossible to unsee.",
        "A watch cairn replaces the hunt marker, positioned to observe the ridge without driving anything toward camp.",
        "Frostroot's hunt board records the incident as WATCHED, NO PURSUIT, a rare public example of restraint counting as successful field work.",
    ),
    ("troll", "wider_world"): _scene(
        ("Varka points down the lowland road. 'Storm coming. Guests coming. Try not to make either prove anything.'", "Orr says, 'If they ignored our warning markers, they can sleep cold.'"),
        ("At Waymeet, one traveler admits refusing Troll help on an earlier trip. The same person is now headed toward Frostroot with the storm behind them.",),
        ("You prepare spare shelter and give route directions in wind, rock, and snow behavior instead of Troll place-names.",),
        ("Orr wordlessly sets an extra cup near the fire for the traveler who once refused it. Varka notices and pretends not to." ,),
        "The lowland road now carries a face with the problem: someone who once rejected Troll help and still needs it when the weather closes.",
        "Fresh route marks describe windbreaks and ice behavior rather than assuming travelers know Frostroot's names for every ridge.",
        "Waymeet's high-road notice now repeats Troll weather guidance in plain travel language, and caravans leave earlier when the cairn warnings change.",
    ),
    ("troll", "capstone"): _scene(
        ("Varka shows you a white hair caught on a food-store latch. 'Danger is real. Story is not decided.'", "Orr checks his spear edge. 'This one has been circling us for days.'"),
        ("The trail loops around two half-grown young hidden beyond the road. Orr realizes the beast is guarding hunger, not stalking sleepers.",),
        ("You turn the pack toward an older game trail with bait and pressure, keeping camp and cubs out of each other's path.",),
        ("Orr reaches for a shed claw, then leaves it in the snow. Varka ties an empty trophy cord around your wrist." ,),
        "The white beast's loops now show the shape of a family feeding route rather than a predator choosing victims.",
        "The diverted game trail carries fresh bait scent away from camp, and no pursuit marks cross the den line.",
        "Frostroot remembers the White Hunt with an empty trophy mark on the board: danger ended, no kill claimed.",
    ),
    ("undead", "home_crisis"): _scene(
        ("Esh places an ownership tablet beside a blank modern registry line. 'Both are true. Only one gets to govern now.'", "Pell says, 'Do not damage the old tablet. If we erase it, we lie.'"),
        ("Nothing in the old record is forged. Pell's defense of its accuracy makes the real danger clearer: truth has quietly continued functioning as command.",),
        ("You preserve the historical line, break its live command seal, and enter the present chosen name beside it.",),
        ("Pell adds a new archival notation: ACCURATE, NON-AUTHORITATIVE. Esh calls it the most useful phrase written all week." ,),
        "The ownership line remains legible, but you can now see the difference between preserving what happened and allowing it to keep happening.",
        "A broken command seal lies beside the untouched historical tablet, physically separating memory from present authority.",
        "The Necropolis registry now marks old ownership records as historical evidence rather than active identity, with your case cited in the margin.",
    ),
    ("undead", "wider_world"): _scene(
        ("Esh gives you a copied death-route record. 'Useful memory. Possibly deadly confidence.'", "Pell says, 'The route was accurate when recorded.'"),
        ("At Waymeet, fresh reports show the dunes have shifted across the remembered safe line. The old dead were truthful; the road changed anyway.",),
        ("You combine the old route memory with present landmarks and send a guide who is instructed to observe rather than reenact.",),
        ("Pell appends MOVING LANDSCAPE to the archival category. Esh adds, 'Everything moves. Some things merely take longer.'" ,),
        "The old route record now feels like a witness rather than a map; useful, specific, and incapable of seeing what changed after death.",
        "A revised route note pairs remembered hazards with current landmarks instead of treating either source as sufficient alone.",
        "Waymeet's marsh-road board now identifies Necropolis route records by date, making age visible before travelers mistake memory for current terrain.",
    ),
    ("undead", "capstone"): _scene(
        ("Esh hears the old command phrase from the sealed relic and immediately says, 'Do not answer it.'", "Pell whispers, 'It sounds like morning roll call.'"),
        ("The newly reanimated are not magically dominated. They are obeying because the phrase feels familiar, and familiarity reaches them before judgment does.",),
        ("You break the focusing plate, shelter the fresh dead from the echo, and preserve only inert fragments as evidence.",),
        ("Pell labels the fragments HAZARD, NOT HERITAGE. Esh lights the Free-Name Lamp from an ordinary communal flame." ,),
        "The relic's danger now feels more intimate than possession: an old routine waiting for a frightened mind to mistake familiarity for obligation.",
        "The command plate is broken beyond use while numbered fragments remain available for study without being able to speak.",
        "The Necropolis display case identifies the relic as a defeated authority mechanism, not a sacred artifact, and newly reanimated citizens are taught why.",
    ),
    ("sporekin", "home_crisis"): _scene(
        ("Seven-Rings asks the Chorus for silence around one repeating warning. 'Listen to how perfect it is.'", "Moss-Under-Stone says, 'Perfect repetition means many of us remember the same danger.'"),
        ("The echo traces back to one injured node. Moss hears the same panic repeat without variation and realizes agreement should contain differences.",),
        ("You isolate the damaged thread long enough for other memories to surface, then reconnect it without allowing one panic to define the whole Chorus.",),
        ("Moss touches the repaired thread only after speaking one private thought aloud first. Seven-Rings notices." ,),
        "The repeating warning now sounds too perfect to you, its lack of variation revealing the single damaged source beneath the apparent consensus.",
        "The injured thread is wrapped apart from the main flow while quieter, differing memories move around it again.",
        "Lumen Hollow now teaches young Sporekin that agreement with no variation can be a symptom, not proof.",
    ),
    ("sporekin", "wider_world"): _scene(
        ("Seven-Rings asks you to carry a remembered image of Waymeet to Waymeet itself. 'Find what memory forgot to keep.'", "Moss says, 'The Chorus already knows the road.'"),
        ("At Waymeet, the inherited memory contains layout and danger but none of the mud, jokes, impatience, smells, or accidental kindness that make the place real.",),
        ("You add your own memory without polishing away uncertainty and release a surface message outsiders can read without joining the Chorus.",),
        ("Moss receives your memory and laughs at a joke no inherited route record ever considered important enough to preserve." ,),
        "The inherited image of Waymeet now feels strangely clean beside your firsthand experience; information survived, texture did not.",
        "A simple scent-and-color surface marker carries one Chorus warning without requiring anyone nearby to share a mind.",
        "Waymeet's green approach now includes a Sporekin marker legible to outsiders, while the Chorus preserves your messier firsthand memory beside the old route record.",
    ),
    ("sporekin", "capstone"): _scene(
        ("Seven-Rings stands outside the strongest signal and does not join it. 'Connection is not consent merely because it feels urgent.'", "Moss trembles under the amplified survival pulse. 'It feels like all of us.'"),
        ("The signal comes from a healthy reflex multiplied through damaged routing. No enemy mind exists; the danger is a system with no room for refusal.",),
        ("You separate the signal, speak one judgment alone in the quiet, repair the route, and rejoin only after your answer already exists.",),
        ("Moss follows your example a moment later. Seven-Rings turns the sporeglass until separate threads meet without disappearing into one another." ,),
        "The overwhelming signal now has a shape you can separate from the people carrying it; urgency no longer automatically means consensus.",
        "The repaired routing leaves deliberate quiet gaps where individual minds can refuse, question, or simply finish a thought.",
        "Lumen Hollow preserves a small quiet interval in emergency Chorus practice, explicitly teaching that reconnection must remain possible to choose.",
    ),
}


def _normalized(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _scene_flag(race_key: str, beat_key: str, moment: str) -> str:
    return f"first_ten_scene_{race_key}_{beat_key}_{moment}"


def _relationship_stage(session, race_key: str) -> int:
    flags = session.database.list_flags(session.character.id)
    arc = first_ten.RACE_FIRST_TEN_ARCS[race_key]
    if arc.capstone.completion_flag(race_key) in flags:
        return 3
    if arc.act_three.completion_flag(race_key) in flags:
        return 2
    if arc.act_two.completion_flag(race_key) in flags:
        return 1
    return 0


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _install_story_partners(world_service=None) -> None:
    for race_key, partner in STORY_PARTNERS.items():
        start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
        npc = NpcDefinition(
            key=partner.key,
            name=partner.name,
            short_description=partner.short_description,
            room_key=start,
            role=partner.role,
            dialogue=PARTNER_LINES[race_key],
        )
        _replace_npc(npc)
        room = legacy_world.ROOMS_BY_KEY.get(start)
        if room is None:
            continue
        if partner.key not in room.npc_keys:
            room = replace(room, npc_keys=room.npc_keys + (partner.key,))
            legacy_world.ROOMS = tuple(room if old.key == start else old for old in legacy_world.ROOMS)
            legacy_world.ROOMS_BY_KEY[start] = room
        if world_service is not None:
            world_service.legacy_rooms[start] = room
            world_service._scene_cache.pop(start, None)


def _append_layer(world_service, room_key: str, layer: DescriptionLayer) -> None:
    existing = world_service.augmentations.get(room_key, RoomAugmentation())
    layers = {item.key: item for item in existing.description_layers}
    layers[layer.key] = layer
    world_service.augmentations[room_key] = RoomAugmentation(
        exit_overrides=existing.exit_overrides,
        extra_exits=existing.extra_exits,
        features=existing.features,
        description_layers=tuple(layers.values()),
    )
    world_service._scene_cache.pop(room_key, None)


def _install_consequence_layers(world_service) -> None:
    if world_service is None:
        return
    for (race_key, beat_key), route in adventures.ADVENTURE_ROUTES.items():
        scene = STORY_SCENES[(race_key, beat_key)]
        beat = next(b for b in first_ten.RACE_FIRST_TEN_ARCS[race_key].beats if b.key == beat_key)
        reveal_room = route.steps[2].room_key
        decision_room = route.steps[3].room_key
        if beat_key == "wider_world":
            aftermath_room = WAYMEET_CROSSROADS_KEY
        elif beat_key == "home_crisis":
            aftermath_room = route.steps[1].room_key
        else:
            aftermath_room = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key

        _append_layer(
            world_service,
            reveal_room,
            DescriptionLayer(
                key=f"first_ten_{race_key}_{beat_key}_reveal",
                priority=84,
                condition=ViewCondition(required_flags=(_scene_flag(race_key, beat_key, "truth_seen"),)),
                text=scene.reveal_echo,
            ),
        )
        _append_layer(
            world_service,
            decision_room,
            DescriptionLayer(
                key=f"first_ten_{race_key}_{beat_key}_decision",
                priority=86,
                condition=ViewCondition(required_flags=(_scene_flag(race_key, beat_key, "decision_made"),)),
                text=scene.decision_echo,
            ),
        )
        _append_layer(
            world_service,
            aftermath_room,
            DescriptionLayer(
                key=f"first_ten_{race_key}_{beat_key}_aftermath",
                priority=88,
                condition=ViewCondition(required_flags=(beat.completion_flag(race_key),)),
                text=scene.aftermath_echo,
            ),
        )


async def _send_scene(session, heading: str, lines: tuple[str, ...]) -> None:
    if not lines:
        return
    await session.send(f"\r\n--- {heading} ---\r\n")
    for line in lines:
        await session.send(line + "\r\n")


async def _relationship_talk(session, race_key: str, normalized: str) -> bool:
    start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
    if session.character.current_room != start:
        return False
    contact = adventures.ORIGIN_CONTACTS[race_key]
    partner = STORY_PARTNERS[race_key]
    contact_forms = {
        f"talk {contact.talk_alias}",
        f"talk to {contact.talk_alias}",
        f"talk {contact.name.lower()}",
        f"talk to {contact.name.lower()}",
    }
    partner_forms = {
        f"talk {partner.talk_alias}",
        f"talk to {partner.talk_alias}",
        f"talk {partner.name.lower()}",
        f"talk to {partner.name.lower()}",
    }
    stage = _relationship_stage(session, race_key)
    if normalized in contact_forms:
        await session.send(RELATIONSHIP_LINES[race_key][stage] + "\r\n")
        await session.send(PARTNER_LINES[race_key][stage] + "\r\n")
        await session.send("You can LISTEN CONVERSATION to hear how their working relationship has changed around your story.\r\n")
        return True
    if normalized in partner_forms:
        await session.send(PARTNER_LINES[race_key][stage] + "\r\n")
        return True
    if normalized in {"listen conversation", "listen to conversation", "listen heritage"}:
        await session.send(f"{adventures.ORIGIN_CONTACTS[race_key].name} and {partner.name} are talking quietly nearby.\r\n")
        await session.send(RELATIONSHIP_LINES[race_key][stage] + "\r\n")
        await session.send(PARTNER_LINES[race_key][stage] + "\r\n")
        return True
    return False


def validate_first_ten_story_depth_contract(world_service=None) -> None:
    problems: list[str] = []
    races = set(first_ten.RACE_FIRST_TEN_ARCS)
    if set(STORY_PARTNERS) != races:
        problems.append("story partner roster does not match racial first-ten roster")
    if set(RELATIONSHIP_LINES) != races or set(PARTNER_LINES) != races:
        problems.append("relationship dialogue roster does not match racial first-ten roster")
    if len(STORY_SCENES) != 24:
        problems.append("expected 24 authored act scenes")

    for race_key, arc in first_ten.RACE_FIRST_TEN_ARCS.items():
        if len(RELATIONSHIP_LINES[race_key]) != 4 or len(PARTNER_LINES[race_key]) != 4:
            problems.append(f"{race_key}: expected four relationship stages")
        start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
        partner = STORY_PARTNERS[race_key]
        if partner.key not in legacy_world.NPCS_BY_KEY:
            problems.append(f"{race_key}: story partner is not registered")
        room = legacy_world.ROOMS_BY_KEY.get(start)
        if room is None or partner.key not in room.npc_keys:
            problems.append(f"{race_key}: story partner is not physically present")
        for beat in arc.beats:
            scene = STORY_SCENES.get((race_key, beat.key))
            if scene is None:
                problems.append(f"{race_key}/{beat.key}: missing authored scene")
                continue
            if not all((scene.setup, scene.disagreement, scene.decision, scene.aftermath)):
                problems.append(f"{race_key}/{beat.key}: incomplete scene structure")
            if not all((scene.reveal_echo, scene.decision_echo, scene.aftermath_echo)):
                problems.append(f"{race_key}/{beat.key}: incomplete persistent consequences")

    if world_service is not None:
        for race_key, arc in first_ten.RACE_FIRST_TEN_ARCS.items():
            for beat in arc.beats:
                route = adventures.ADVENTURE_ROUTES[(race_key, beat.key)]
                relevant = {route.steps[2].room_key, route.steps[3].room_key}
                relevant.add(
                    WAYMEET_CROSSROADS_KEY if beat.key == "wider_world"
                    else route.steps[1].room_key if beat.key == "home_crisis"
                    else STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
                )
                if any(room_key not in world_service.augmentations for room_key in relevant):
                    problems.append(f"{race_key}/{beat.key}: consequence layers missing from world")

    if problems:
        raise RuntimeError("First-ten story depth contract failed:\n- " + "\n- ".join(problems))


def install_first_ten_story_depth_runtime(player_session_class, world_service=None) -> None:
    if getattr(player_session_class, "_first_ten_story_depth_installed", False):
        return

    _install_story_partners(world_service)
    _install_consequence_layers(world_service)
    validate_first_ten_story_depth_contract(world_service)

    previous_complete = adventures._complete_adventure_step
    previous_handle = adventures._handle_adventure_command

    async def complete_with_story(session, arc, beat, route, step):
        scene = STORY_SCENES[(arc.race_key, beat.key)]
        index = route.steps.index(step)
        if index == 0:
            await _send_scene(session, "The Problem Arrives", scene.setup)
        elif index == 2:
            await _send_scene(session, "The Story Turns", scene.disagreement)

        await previous_complete(session, arc, beat, route, step)

        if index == 2:
            session.database.grant_flag(session.character.id, _scene_flag(arc.race_key, beat.key, "truth_seen"))
        elif index == 3:
            session.database.grant_flag(session.character.id, _scene_flag(arc.race_key, beat.key, "decision_made"))
            await _send_scene(session, "What Your Decision Changes", scene.decision)
        elif index == 4:
            await _send_scene(session, "Afterward", scene.aftermath)

    adventures._complete_adventure_step = complete_with_story

    async def handle_with_relationship(session, command):
        if session.character is not None:
            race_key = session.character.race or ""
            if race_key in STORY_PARTNERS:
                normalized = _normalized(command)
                if await _relationship_talk(session, race_key, normalized):
                    return True
        return await previous_handle(session, command)

    adventures._handle_adventure_command = handle_with_relationship
    first_ten._handle_arc_command = handle_with_relationship
    player_session_class._first_ten_story_depth_installed = True
