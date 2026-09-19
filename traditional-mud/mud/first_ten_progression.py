from __future__ import annotations

import asyncio
from dataclasses import dataclass

import mud.class_progression as class_progression
import mud.mechanics as mechanics
import mud.quests as quests
from mud.quests import QuestDefinition
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


@dataclass(frozen=True, slots=True)
class ArcStep:
    key: str
    objective: str
    command: str
    response: str


@dataclass(frozen=True, slots=True)
class ArcBeat:
    key: str
    unlock_level: int
    title: str
    summary: str
    steps: tuple[ArcStep, ...]
    xp_reward: int
    completion_text: str

    def quest_key(self, race_key: str) -> str:
        return f"first_ten_{race_key}_{self.key}"

    def completion_flag(self, race_key: str) -> str:
        return f"first_ten_{race_key}_{self.key}_complete"


@dataclass(frozen=True, slots=True)
class RaceFirstTenArc:
    race_key: str
    act_one_title: str
    act_two: ArcBeat
    act_three: ArcBeat
    capstone: ArcBeat

    @property
    def beats(self) -> tuple[ArcBeat, ...]:
        return (self.act_two, self.act_three, self.capstone)


def _beat(key, level, title, summary, rows, xp, ending):
    return ArcBeat(
        key, level, title, summary,
        tuple(ArcStep(f"step_{i+1}", objective, command, response)
              for i, (objective, command, response) in enumerate(rows)),
        xp, ending,
    )


RACE_FIRST_TEN_ARCS = {
    "human": RaceFirstTenArc(
        "human", "Blackwall Civic Readiness",
        _beat("home_crisis", 4, "Cracks in the Blackwall",
              "A routine wall defect exposes a failure of shared responsibility.",
              [
                  ("INSPECT MORTAR at the Demon Gate.", "inspect mortar", "Three generations of patchwork hide one failing seam. The wall is strong; the handoff between crews is not."),
                  ("QUESTION WATCH about the repair history.", "question watch", "Every shift assumed the next had inherited the defect. Nobody lied; responsibility simply became too diffuse."),
                  ("MARK REPAIR in the gate ledger.", "mark repair", "You chalk the whole seam and sign the ledger. The problem finally belongs to someone because you made it impossible to disappear."),
              ], 250, "You learn that Human civic strength depends on making ordinary responsibility visible."),
        _beat("wider_world", 8, "Road Beyond the Horns",
              "An outsider freight report forces Blackwall to explain itself to people who do not share Human customs.",
              [
                  ("COMPARE OUTSIDER REPORT with the gate ledger.", "compare outsider report", "The outsider is right: the inspection symbols are obvious only to Humans."),
                  ("CHOOSE ENVOY DUTY and translate the process.", "choose envoy duty", "You rewrite the inspection in plain trade-road language that Dwarf, Goblin, and Moon Elf haulers can all follow."),
                  ("SEAL DISPATCH for Veyra.", "seal dispatch", "The new form leaves for the shared roads. A good system is not truly good if only its makers can read it."),
              ], 450, "The kingdom becomes more useful, not less Human, by becoming legible to Astralis."),
        _beat("capstone", 10, "The Gate Holds",
              "A wagon failure blocks Blackwall during a crowded shift.",
              [
                  ("SECURE BREACH before congestion becomes panic.", "secure breach", "You clear the unstable wagon tongue and move bystanders behind the horn-marked line."),
                  ("COMMAND LINE so guards, haulers, and repair hands work as one crew.", "command line", "Guards lift, teamsters brace, and a Goblin axle hand calls the safest cut. Need matters more than status."),
                  ("OPEN ROAD only after the repair is safe.", "open road", "Traffic moves again without ceremony. The ordinary result is the proof that the system worked."),
              ], 700, "LEVEL-10 CAPSTONE: Blackwall trusts you to carry Human civic discipline onto the mixed roads."),
    ),
    "forest_elf": RaceFirstTenArc(
        "forest_elf", "The Old River Path",
        _beat("home_crisis", 4, "The Sick Root",
              "A beautiful grove hides a spreading problem.",
              [
                  ("READ LEAVES around the Circle Clearing.", "read leaves", "The canopy looks healthy, but the youngest leaves curl inward and pale along the veins."),
                  ("TRACE BLIGHT from leaf to root.", "trace blight", "The pattern leads to one waterlogged root carrying rot beneath clean bark."),
                  ("CUT ROT without felling the whole tree.", "cut rot", "You remove only the dead tissue and leave the living root system intact."),
              ], 250, "Home's danger is sometimes subtle enough that beauty makes people stop looking."),
        _beat("wider_world", 8, "Boundary With Footprints",
              "Foreign travelers are crossing a protected nursery without understanding the signs.",
              [
                  ("READ FOREIGN TRACKS.", "read foreign tracks", "Dwarf boots, courier steps, and a Troll stride all used the same stream edge without knowing what grew there."),
                  ("LEAVE SAFE MARKER outsiders can understand.", "leave safe marker", "You combine Elven signs with simple trade-road stones: cross here, not there."),
                  ("INVITE PASSAGE along the safer line.", "invite passage", "The boundary becomes stronger because it now teaches strangers how to respect it."),
              ], 450, "You can protect the forest without pretending nobody else exists beyond it."),
        _beat("capstone", 10, "The Boundary Choice",
              "A prowler follows the new crossing and threatens both grove and travelers.",
              [
                  ("TRACK PROWLER without trampling the nursery.", "track prowler", "You follow pressure marks and broken moss; the animal is hunting the crossing, not nesting in the grove."),
                  ("PROTECT CROSSING by redirecting the threat.", "protect crossing", "Noise, scent, and a shifted food trail pull the prowler away without burning the forest out."),
                  ("OPEN TRAIL once both forest and travelers are safe.", "open trail", "The crossing reopens with better markers and a living boundary intact."),
              ], 700, "LEVEL-10 CAPSTONE: The Circle trusts you to carry Elven stewardship into a shared world."),
    ),
    "moon_elf": RaceFirstTenArc(
        "moon_elf", "The Third Chair",
        _beat("home_crisis", 4, "The Missing Angle",
              "A civic measurement looks impossible because every witness stands in the same place.",
              [
                  ("CHECK SHADOWS around High Horizon Plaza.", "check shadows", "The measurements disagree only when a tower shadow crosses one reference mark."),
                  ("CLIMB OVERLOOK and repeat the observation.", "climb overlook", "From above, both lower measurements prove accurate from their own positions."),
                  ("RECORD ANGLE instead of erasing the contradiction.", "record angle", "You preserve both accounts and add the missing viewpoint."),
              ], 250, "Home's weakness is not argument; it is mistaking a familiar angle for the whole truth."),
        _beat("wider_world", 8, "The Lowland Measure",
              "Lowland maps describe the mountain badly in one way and brilliantly in another.",
              [
                  ("COMPARE HORIZON MAPS with the lowland survey.", "compare horizon maps", "Moon Elf charts capture height; lowland charts capture travel time. Each hides what the other sees."),
                  ("MARK DESCENT using both kinds of information.", "mark descent", "You add grade, time, and visible landmarks so outsiders can actually use the route."),
                  ("ACCEPT UNCERTAINTY where weather defeats precision.", "accept uncertainty", "You leave one weather note deliberately unresolved rather than inventing certainty."),
              ], 450, "Perspective belongs to everyone, not only the people who built the observatory."),
        _beat("capstone", 10, "The Fourth Chair",
              "A mountain/lowland dispute cannot be solved from the old three viewpoints alone.",
              [
                  ("HEAR CONTRADICTION before deciding who is wrong.", "hear contradiction", "Both witnesses describe the same fast-moving storm at different hours."),
                  ("CHOOSE RECORD that preserves time, place, and uncertainty.", "choose record", "You write an account that explains why both testimonies mattered and where each stopped being reliable."),
                  ("LEAVE CHAIR OPEN for the next angle.", "leave chair open", "The fourth chair remains empty as a reminder that a future witness may know what this room does not."),
              ], 700, "LEVEL-10 CAPSTONE: High Horizon recognizes you as a witness fit for the mixed roads."),
    ),
    "dwarf": RaceFirstTenArc(
        "dwarf", "By Stamp and Steam",
        _beat("home_crisis", 4, "Pressure Debt",
              "A harmless-looking gauge wobble reveals a defect hidden by bureaucracy.",
              [
                  ("READ SHIFT GAUGE instead of trusting yesterday's signature.", "read shift gauge", "The needle is within tolerance but repeats a dangerous seventh-pulse wobble."),
                  ("TRACE STEAM through the work-order history.", "trace steam", "Three departments recorded the same symptom under different names; no single ledger showed the whole problem."),
                  ("SIGN SHUTDOWN and accept one lost bell of production.", "sign shutdown", "The line stops long enough to replace a warped regulator before it can cost a crew."),
              ], 250, "Procedure fails when it keeps people from seeing the same problem together."),
        _beat("wider_world", 8, "Contract Beyond the Mountain",
              "A foreign repair works but does not look Dwarven.",
              [
                  ("AUDIT FOREIGN FITTING on its actual use.", "audit foreign fitting", "The Goblin plate is ugly, off-spec, and mechanically sound exactly where the road needs flexibility."),
                  ("PRICE REPAIR including labor, delay, and risk.", "price repair", "Rebuilding everything to mountain standard is clearly worse than adapting the sound design."),
                  ("COUNTERSIGN ROADWORK with the exception documented.", "countersign roadwork", "The contract records why the exception is safe; nobody has to pretend it is Dwarven."),
              ], 450, "Craftsmanship survives contact with the wider world by measuring outcomes as seriously as tradition."),
        _beat("capstone", 10, "Shiftmaster for One Bell",
              "A cascading fault forces a choice between quota and crew.",
              [
                  ("HALT LINE before the fault grows.", "halt line", "You pull the authority cord while supervisors are still debating whether the fault is serious enough."),
                  ("SAVE CREW before saving machinery.", "save crew", "Workers clear the hot section before the coupling fails."),
                  ("RESTART WORKS only after a fresh inspection.", "restart works", "The line returns slower, safer, and documented. Nobody calls the lost bell a failure."),
              ], 700, "LEVEL-10 CAPSTONE: The trade houses trust you to carry Dwarven standards beyond the mountain."),
    ),
    "goblin": RaceFirstTenArc(
        "goblin", "Three Bells",
        _beat("home_crisis", 4, "The Sinking Heap",
              "Generations of clever fixes are settling into the swamp because nobody checked how they work together.",
              [
                  ("TEST PILINGS under the Clattergate.", "test pilings", "Three supports are strong, two are decorative, and one is an old wagon axle that almost held forever."),
                  ("SORT BRACING by what still works.", "sort bracing", "You keep ugly iron, reject pretty warped brass, and pair two mismatched beams whose weaknesses cancel out."),
                  ("PATCH WALKWAY before the mud wins.", "patch walkway", "The repaired span looks like an argument made from six materials. A loaded cart crosses it without a twitch."),
              ], 250, "Goblin usefulness becomes a problem when a thousand good fixes stop forming one good system."),
        _beat("wider_world", 8, "Useful to Strangers",
              "A foreign wreck arrives with owners who assume Goblin salvage law means theft.",
              [
                  ("INSPECT FOREIGN WRECK before claims begin.", "inspect foreign wreck", "The axle is gone, the cargo frame is sound, and the owner cares more about a map case than the shiny latch everyone wants."),
                  ("OFFER SALVAGE in terms the owner understands.", "offer salvage", "You separate rescue, repair, and claim value. Bargaining becomes possible without suspicion."),
                  ("STAMP FAIR CLAIM after both sides agree.", "stamp fair claim", "The map goes home, the frame stays owned, and the broken brass becomes legal salvage."),
              ], 450, "Goblin commerce works outside Rattlefen when its rules are explained instead of merely assumed."),
        _beat("capstone", 10, "The Heap That Stayed Up",
              "Floodwater and scavengers hit the same district at once.",
              [
                  ("BRACE TOWER with whatever bears load now.", "brace tower", "Claim poles, cart rails, and boiler skin become a temporary spine before the tower can peel open."),
                  ("SETTLE SCAVENGERS before rescue becomes a free-for-all.", "settle scavengers", "You mark rescue material, private property, and future claims in public, fast rules."),
                  ("SIGN BUILD after the span survives a full wagon.", "sign build", "You scratch your mark into a plate made from three previous owners' junk. It held."),
              ], 700, "LEVEL-10 CAPSTONE: Rattlefen trusts you to carry Goblin usefulness onto the shared roads."),
    ),
    "troll": RaceFirstTenArc(
        "troll", "A Fire Before Pride",
        _beat("home_crisis", 4, "Tracks Under Snow",
              "Fear is making Frostroot louder than the evidence.",
              [
                  ("READ TRACKS before naming the creature.", "read tracks", "The prints are large but shallow, spaced like a tired animal rather than a stalking one."),
                  ("TEST WIND to learn whether it approaches or retreats.", "test wind", "Old scent blows from camp toward the tracks; the creature smelled Frostroot and chose to move away."),
                  ("SET WATCH instead of starting a hunt.", "set watch", "Two hunters take the ridge with signal horns and no glory to chase."),
              ], 250, "Troll toughness fails when pride needs every unknown thing to become a fight."),
        _beat("wider_world", 8, "Guest Fire",
              "Shared-road travelers reach Frostroot in weather that does not care about custom.",
              [
                  ("PREPARE SPARE SHELTER before the storm closes.", "prepare spare shelter", "You lower a windbreak, weight the hide edge, and leave dry fuel where cold hands can reach it."),
                  ("SHARE FIRE without demanding toughness first.", "share fire", "Human, Undead, and Goblin travelers get the same place near the coals."),
                  ("NAME SAFE ROUTE in terms outsiders understand.", "name safe route", "You describe wind, rock shape, and snow behavior instead of Troll place-names."),
              ], 450, "Frostroot can remain Troll country while still being a place outsiders can survive."),
        _beat("capstone", 10, "The White Hunt",
              "A starving predator shadows both camp and trade road.",
              [
                  ("TRACK WHITE BEAST until you know what it wants.", "track white beast", "The trail circles food stores and pack animals, never sleeping shelters. Hunger is driving it."),
                  ("TURN PACK away from camp instead of chasing blind.", "turn pack", "Hunters hold the flanks while bait and pressure move the predator toward an older game trail."),
                  ("CLAIM NO TROPHY once the danger is gone.", "claim no trophy", "The beast lives, the camp eats, and the road stays open."),
              ], 700, "LEVEL-10 CAPSTONE: Frostroot trusts you to carry Troll survival wisdom into the wider world."),
    ),
    "undead": RaceFirstTenArc(
        "undead", "No Voice Above You",
        _beat("home_crisis", 4, "A Name With No Master",
              "An old burial record tries to define a free Undead entirely by the life that came before.",
              [
                  ("READ OLD NAME in the reclamation ledger.", "read old name", "The ledger lists former name, trade, debts, and master with perfect confidence, but no later choices."),
                  ("BREAK SEAL linking it to the old command registry.", "break seal", "The wax snaps. History remains history and stops functioning as authority."),
                  ("CHOOSE NAME for the new registry line.", "choose name", "A new line acknowledges continuity, denies ownership, and records a present name by choice."),
              ], 250, "The Necropolis becomes a prison if memory is allowed to harden into command."),
        _beat("wider_world", 8, "The Living Knock",
              "Living travelers ask the Necropolis for help while carrying every fear outsiders have about the dead.",
              [
                  ("RECEIVE LIVING PETITION without punishing fear.", "receive living petition", "They stare at exposed bone, but their desert-route problem is legitimate."),
                  ("WEIGH MEMORY against present evidence.", "weigh memory", "Old death records narrow the search, but moving dunes prove memory cannot replace observation."),
                  ("OPEN CRYPT GATE and send a guide.", "open crypt gate", "The living leave with an Undead route-reader beside them. Cooperation begins before comfort does."),
              ], 450, "The dead can participate in Astralis without asking the living to become comfortable first."),
        _beat("capstone", 10, "No Voice Above You",
              "A dormant command relic wakes and calls to newly reanimated minds.",
              [
                  ("SHATTER COMMAND RELIC before authority feels normal.", "shatter command relic", "The relic says obey, return, kneel. You break its focusing plate."),
                  ("PROTECT FRESH DEAD while the echo fades.", "protect fresh dead", "You stand with the newly reanimated until each can hear the silence beneath the old command."),
                  ("CLOSE CRYPT on the relic pieces.", "close crypt", "The fragments are cataloged as evidence and sealed as a hazard, not preserved as sacred authority."),
              ], 700, "LEVEL-10 CAPSTONE: The Necropolis trusts you to carry memory into Astralis without carrying old masters with it."),
    ),
    "sporekin": RaceFirstTenArc(
        "sporekin", "The Chorus Beneath",
        _beat("home_crisis", 4, "A Discordant Thread",
              "The Chorus repeats a damaged memory until repetition begins to sound like truth.",
              [
                  ("LISTEN CHORUS for the part that repeats too perfectly.", "listen chorus", "Most shared impressions vary slightly; one warning repeats with identical texture."),
                  ("TRACE DISCORD through the mycelial memory.", "trace discord", "The false certainty leads to one injured node echoing the last panic it received."),
                  ("ISOLATE THREAD long enough to hear the rest.", "isolate thread", "Other memories disagree immediately. The Chorus becomes less certain and more truthful."),
              ], 250, "Shared memory is dangerous when consensus comes from repetition instead of many minds."),
        _beat("wider_world", 8, "One Voice Carried Far",
              "The Chorus wants to understand the surface roads, but borrowed memory is not firsthand experience.",
              [
                  ("GATHER SURFACE STORY from your own travel.", "gather surface story", "You separate what you saw from what the Chorus expected: traffic, wet stone, impatience, kindness."),
                  ("ADD OWN MEMORY with uncertainty intact.", "add own memory", "You contribute a perspective rather than smoothing it into a lesson."),
                  ("RELEASE SPORE MESSAGE outsiders can understand.", "release spore message", "A simple surface marker carries the warning in scent and color for people who will never hear the Chorus."),
              ], 450, "Joining Astralis means learning how to speak beyond the shared mind."),
        _beat("capstone", 10, "Chorus and Self",
              "A collective signal begins overwhelming individual judgment near Lumen Hollow.",
              [
                  ("SEPARATE SIGNAL from the minds carrying it.", "separate signal", "You identify a damaged emergency reflex amplified through healthy threads."),
                  ("SPEAK ALONE while the Chorus is quiet.", "speak alone", "Your answer enters the silence as one person's judgment before anyone multiplies it."),
                  ("REJOIN BY CHOICE after the signal is repaired.", "rejoin by choice", "The Chorus closes around you again, but the return is an action you chose."),
              ], 700, "LEVEL-10 CAPSTONE: The Chorus accepts that connection is strongest when its people can also stand apart."),
    ),
}


CLASS_CAPSTONE_ABILITIES = {
    "brute": mechanics.AbilityDefinition(
        key="last_stand", name="Last Stand", unlock_level=10, mana_cost=10, cooldown_seconds=30.0,
        description="Recover health and brace yourself behind a short emergency ward.",
        category="self_protection", skill_improves_effectiveness=False, design_status="approved_level_10_live"),
    "wizard": mechanics.AbilityDefinition(
        key="starbreak", name="Starbreak", unlock_level=10, mana_cost=16, cooldown_seconds=20.0,
        description="Collapse a tightly controlled arcane point into one enemy for heavy direct spell damage.",
        category="spell_damage", design_status="approved_level_10_live", cast_time_seconds=3.0),
    "druid": mechanics.AbilityDefinition(
        key="living_chorus", name="Living Chorus", unlock_level=10, mana_cost=14, cooldown_seconds=24.0,
        description="Heal the living party and briefly ward everyone reached.",
        category="group_healing", skill_improves_effectiveness=False, design_status="approved_level_10_live", cast_time_seconds=2.5),
    "necromancer": mechanics.AbilityDefinition(
        key="soul_harvest", name="Soul Harvest", unlock_level=10, mana_cost=13, cooldown_seconds=16.0,
        description="Drain heavy vitality from one enemy and reclaim part of the damage as health.",
        category="life_drain", design_status="approved_level_10_live"),
}

CLASS_CAPSTONE_BEATS = {
    "brute": "Your Brute training reaches Last Stand: survival and threat control become a deliberate emergency tool.",
    "wizard": "Your Wizard training reaches Starbreak: level-ten power focused into one controlled target.",
    "druid": "Your Druid training reaches Living Chorus: group recovery that reinforces your secondary-healer identity.",
    "priest": "Your Priest foundation reaches Divine Concord: the level-ten expression of party healing and protection.",
    "necromancer": "Your Necromancer training reaches Soul Harvest: enemy vitality becomes your staying power.",
}


def install_first_ten_content() -> None:
    additions = []
    for race_key, arc in RACE_FIRST_TEN_ARCS.items():
        for beat in arc.beats:
            qkey = beat.quest_key(race_key)
            if qkey in quests.QUESTS_BY_KEY:
                continue
            definition = QuestDefinition(
                key=qkey, name=beat.title, style="structured",
                minimum_level=beat.unlock_level, description=beat.summary,
                objective_steps=tuple((s.key, s.objective) for s in beat.steps) + (("complete", beat.completion_text),),
            )
            additions.append(definition)
            quests.QUESTS_BY_KEY[qkey] = definition
    if additions:
        quests.QUESTS = quests.QUESTS + tuple(additions)

    for class_key, definition in CLASS_CAPSTONE_ABILITIES.items():
        by_key = {a.key: a for a in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())}
        by_key[definition.key] = definition
        mechanics.FIXED_CLASS_ABILITIES[class_key] = tuple(sorted(
            by_key.values(), key=lambda a: (10_000 if a.unlock_level is None else a.unlock_level, a.name)
        ))


def _current_beat(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    arc = RACE_FIRST_TEN_ARCS.get(character.race or "")
    if arc is None:
        return None
    flags = session.database.list_flags(character.id)
    opening = STARTER_RACE_LOOPS_BY_RACE[arc.race_key]
    if opening.completion_flag not in flags:
        return None
    for beat in arc.beats:
        if beat.completion_flag(arc.race_key) not in flags:
            return arc, beat
    return None


def _ensure_quest(session, race_key, beat):
    state = session.database.get_quest(session.character.id, beat.quest_key(race_key))
    if state is None and session.character.level >= beat.unlock_level:
        session.database.start_quest(session.character.id, beat.quest_key(race_key), beat.steps[0].key)
        state = session.database.get_quest(session.character.id, beat.quest_key(race_key))
    return state


async def _show_heritage(session):
    c = session.character
    arc = RACE_FIRST_TEN_ARCS.get(c.race or "")
    if arc is None:
        await session.send("Your origin does not have a first-ten racial arc yet.\r\n")
        return
    loop = STARTER_RACE_LOOPS_BY_RACE[arc.race_key]
    flags = session.database.list_flags(c.id)
    opening_done = loop.completion_flag in flags
    await session.send("\r\n--- Level 1-10 Heritage Arc ---\r\n")
    await session.send(f"Act I - {arc.act_one_title}: {'complete' if opening_done else 'in progress'}.\r\n")
    for label, beat in (("Act II", arc.act_two), ("Act III", arc.act_three), ("Capstone", arc.capstone)):
        if beat.completion_flag(arc.race_key) in flags:
            await session.send(f"{label} - {beat.title}: complete.\r\n")
            continue
        if not opening_done:
            await session.send(f"{label} - {beat.title}: locked until your opening is complete.\r\n")
            continue
        if c.level < beat.unlock_level:
            await session.send(f"{label} - {beat.title}: unlocks at level {beat.unlock_level}.\r\n")
            continue
        state = _ensure_quest(session, arc.race_key, beat)
        step_key = state.get("current_step") if state else beat.steps[0].key
        step = next((s for s in beat.steps if s.key == step_key), beat.steps[0])
        await session.send(
            f"{label} - {beat.title}: active.\r\n"
            f"Return to {loop.starting_room_key.replace('_', ' ').title()} and {step.objective}\r\n"
        )
        break
    await session.send("These racial beats sit beside the shared Waymeet/Gloamworks/Greywake/Veyra journey; they do not replace it.\r\n")


async def _complete_step(session, arc, beat, step):
    c = session.character
    await session.send("\r\n" + step.response + "\r\n")
    index = beat.steps.index(step)
    if index + 1 < len(beat.steps):
        nxt = beat.steps[index + 1]
        session.database.advance_quest(c.id, beat.quest_key(arc.race_key), nxt.key)
        await session.send(f"\r\nNext: {nxt.objective}\r\n")
        return

    session.database.complete_quest(c.id, beat.quest_key(arc.race_key))
    session.database.grant_flag(c.id, beat.completion_flag(arc.race_key))
    new_level = session.database.add_experience(c.id, beat.xp_reward)
    refreshed = session.database.get_character_by_name(c.name)
    if refreshed is not None:
        session.character = refreshed
    await session.send(
        f"\r\n--- {beat.title} complete ---\r\n{beat.completion_text}\r\n"
        f"Reward: {beat.xp_reward} XP. You are level {new_level}.\r\n"
    )
    if beat.key == "capstone":
        line = CLASS_CAPSTONE_BEATS.get(session.character.character_class or "")
        if line:
            await session.send(line + "\r\n")
        await session.send(
            "Your level 1-10 origin arc is complete. JOURNEY now points fully into Veyra, class commissions, dungeons, factions, and the roads toward level 12+.\r\n"
        )


async def _handle_arc_command(session, command):
    if session.character is None:
        return False
    normalized = " ".join(command.strip().lower().split())
    if normalized in {"heritage", "origin arc", "first ten", "1-10"}:
        await _show_heritage(session)
        return True
    current = _current_beat(session)
    if current is None:
        return False
    arc, beat = current
    if session.character.level < beat.unlock_level:
        return False
    loop = STARTER_RACE_LOOPS_BY_RACE[arc.race_key]
    if session.character.current_room != loop.starting_room_key:
        return False
    state = _ensure_quest(session, arc.race_key, beat)
    if state is None or state.get("status") != "active":
        return False
    step = next((s for s in beat.steps if s.key == state.get("current_step")), None)
    if step is None or normalized != step.command:
        return False
    await _complete_step(session, arc, beat, step)
    return True


def _resolve_capstone(session, text):
    c = getattr(session, "character", None)
    if c is None or c.level < 10:
        return None
    ability = CLASS_CAPSTONE_ABILITIES.get(c.character_class or "")
    if ability is None:
        return None
    normalized = " ".join(text.strip().lower().replace("_", " ").split())
    return ability if normalized in {ability.key.replace("_", " "), ability.name.lower()} else None


async def _use_capstone(session, ability):
    combatant = getattr(session, "combatant", None)
    if combatant is None:
        await session.send("You need an active character state to use that ability.\r\n")
        return True

    if ability.key == "last_stand":
        if not await class_progression._activate(session, ability):
            return True
        restored = min(12, combatant.max_hp - combatant.current_hp)
        combatant.current_hp += restored
        session.ward_until = max(getattr(session, "ward_until", 0.0), asyncio.get_running_loop().time() + 10.0)
        await session.send(f"Last Stand restores {restored} HP and wards you for ten seconds.\r\n")
    elif ability.key == "starbreak":
        if session.active_enemy is None:
            await session.send("Starbreak needs an active enemy target.\r\n")
            return True
        if not await class_progression._activate(session, ability):
            return True
        await class_progression._deal_damage(session, ability, combatant.spell_damage(20))
    elif ability.key == "living_chorus":
        if not await class_progression._activate(session, ability):
            return True
        targets = class_progression._support_targets(session)
        if session not in targets and class_progression._living(session):
            targets.insert(0, session)
        until = asyncio.get_running_loop().time() + 8.0
        for member in targets:
            await class_progression._heal(session, member, 10, "Living Chorus")
            member.ward_until = max(getattr(member, "ward_until", 0.0), until)
        await session.send(f"Living Chorus reaches {len(targets)} living party member{'s' if len(targets) != 1 else ''}.\r\n")
    elif ability.key == "soul_harvest":
        enemy = session.active_enemy
        if enemy is None:
            await session.send("Soul Harvest needs an active enemy target.\r\n")
            return True
        if not await class_progression._activate(session, ability):
            return True
        before = enemy.current_hp
        await class_progression._deal_damage(session, ability, combatant.spell_damage(16))
        dealt = max(0, before - enemy.current_hp)
        restored = min(max(1, dealt // 2), combatant.max_hp - combatant.current_hp)
        combatant.current_hp += restored
        await session.send(f"Soul Harvest returns {restored} HP to you.\r\n")
    else:
        return False

    await class_progression._complete_use(session, ability)
    return True


def validate_first_ten_contract():
    problems = []
    if set(RACE_FIRST_TEN_ARCS) != set(STARTER_RACE_LOOPS_BY_RACE):
        problems.append("race arc roster does not match starter race roster")
    for race_key, arc in RACE_FIRST_TEN_ARCS.items():
        if tuple(b.unlock_level for b in arc.beats) != (4, 8, 10):
            problems.append(f"{race_key}: expected milestones at levels 4, 8, and 10")
        for beat in arc.beats:
            if len(beat.steps) < 3:
                problems.append(f"{race_key}/{beat.key}: needs three authored actions")
            if beat.quest_key(race_key) not in quests.QUESTS_BY_KEY:
                problems.append(f"{race_key}/{beat.key}: quest not registered")
    for class_key in ("brute", "wizard", "druid", "necromancer"):
        if not any(a.unlock_level == 10 for a in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())):
            problems.append(f"{class_key}: no level-10 ability")
    for path_key, abilities in mechanics.PRIEST_DEITY_ABILITIES.items():
        if not any(a.key == "divine_concord" and a.unlock_level == 10 for a in abilities):
            problems.append(f"priest/{path_key}: Divine Concord missing at 10")
    if problems:
        raise RuntimeError("Level 1-10 contract failed:\n- " + "\n- ".join(problems))


async def _delegate_prompt(self, previous, command):
    had = "prompt" in self.__dict__
    prior = self.__dict__.get("prompt")

    async def replay(_text):
        return command

    self.prompt = replay
    try:
        await previous(self)
    finally:
        if had:
            self.prompt = prior
        else:
            self.__dict__.pop("prompt", None)


def install_first_ten_runtime(player_session_class):
    install_first_ten_content()
    validate_first_ten_contract()
    if getattr(player_session_class, "_first_ten_runtime_installed", False):
        return

    previous_prompt = player_session_class.playing_prompt
    previous_use = player_session_class.use_ability

    async def use_ability(self, ability_text):
        ability = _resolve_capstone(self, ability_text)
        if ability is not None and await _use_capstone(self, ability):
            return
        await previous_use(self, ability_text)

    async def playing_prompt(self):
        if self.character is None:
            await previous_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        if await _handle_arc_command(self, command):
            return
        await _delegate_prompt(self, previous_prompt, command)

    player_session_class.use_ability = use_ability
    player_session_class.playing_prompt = playing_prompt
    player_session_class._first_ten_runtime_installed = True
