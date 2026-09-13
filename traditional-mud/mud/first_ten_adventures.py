from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.first_ten_progression as first_ten
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE
from mud.waymeet_frontier import (
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_GREEN_APPROACH_KEY,
    WAYMEET_HIGH_ROAD_KEY,
    WAYMEET_MARSH_ROAD_KEY,
    WAYMEET_WEST_ROAD_KEY,
)
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class OriginAdventureContact:
    key: str
    name: str
    short_description: str
    role: str
    talk_alias: str
    outbound_room_key: str
    waymeet_approach_key: str
    reward_key: str


@dataclass(frozen=True, slots=True)
class AdventureStep:
    key: str
    room_key: str
    command: str
    objective: str
    narrative: str
    twist: bool = False
    shared_world: bool = False


@dataclass(frozen=True, slots=True)
class AdventureRoute:
    race_key: str
    beat_key: str
    steps: tuple[AdventureStep, ...]
    reward_key: str | None = None


ORIGIN_CONTACTS: dict[str, OriginAdventureContact] = {
    "human": OriginAdventureContact(
        key="first_ten_human_road_captain_elian_voss",
        name="Road-Captain Elian Voss",
        short_description="a road-captain with a slate full of repairs nobody else managed to own",
        role="Blackwall road captain and recurring first-ten contact",
        talk_alias="elian",
        outbound_room_key="human_outer_caravan_road",
        waymeet_approach_key=WAYMEET_WEST_ROAD_KEY,
        reward_key="heritage_blackwall_road_seal",
    ),
    "forest_elf": OriginAdventureContact(
        key="first_ten_forest_keeper_sael_fernhand",
        name="Keeper Sael Fernhand",
        short_description="a mud-kneed keeper who distrusts any answer reached without touching the ground first",
        role="Forest keeper and recurring first-ten contact",
        talk_alias="sael",
        outbound_room_key="forest_elf_briarshadow_thicket",
        waymeet_approach_key=WAYMEET_GREEN_APPROACH_KEY,
        reward_key="heritage_living_boundary_knot",
    ),
    "moon_elf": OriginAdventureContact(
        key="first_ten_moon_recorder_yra_venn",
        name="Recorder Yra Venn",
        short_description="a civic recorder carrying three notebooks and leaving a fourth page deliberately blank",
        role="High Horizon recorder and recurring first-ten contact",
        talk_alias="yra",
        outbound_room_key="moon_elf_wind_terrace",
        waymeet_approach_key=WAYMEET_HIGH_ROAD_KEY,
        reward_key="heritage_fourth_chair_token",
    ),
    "dwarf": OriginAdventureContact(
        key="first_ten_dwarf_shiftmaster_orla_flintmark",
        name="Shiftmaster Orla Flintmark",
        short_description="a soot-striped shiftmaster who reads accident ledgers more closely than production tallies",
        role="Foundry shiftmaster and recurring first-ten contact",
        talk_alias="orla",
        outbound_room_key="dwarf_upper_freight_deck",
        waymeet_approach_key=WAYMEET_WEST_ROAD_KEY,
        reward_key="heritage_one_bell_brass_stamp",
    ),
    "goblin": OriginAdventureContact(
        key="first_ten_goblin_claimwright_pella_six_wires",
        name="Claimwright Pella Six-Wires",
        short_description="a claimwright with six copper wires braided into her hair and three contradictory ledgers under one arm",
        role="Rattlefen claimwright and recurring first-ten contact",
        talk_alias="pella",
        outbound_room_key="goblin_floodgate_walk",
        waymeet_approach_key=WAYMEET_MARSH_ROAD_KEY,
        reward_key="heritage_heap_held_plate",
    ),
    "troll": OriginAdventureContact(
        key="first_ten_troll_hunter_varka_ashsnow",
        name="Hunter-Mother Varka Ashsnow",
        short_description="an old hunter who notices wind, hunger, and bad pride before she notices trophies",
        role="Frostroot hunter and recurring first-ten contact",
        talk_alias="varka",
        outbound_room_key="troll_stonejaw_pass",
        waymeet_approach_key=WAYMEET_HIGH_ROAD_KEY,
        reward_key="heritage_untaken_trophy_cord",
    ),
    "undead": OriginAdventureContact(
        key="first_ten_undead_scribe_esh_vell",
        name="Free-Name Scribe Esh Vell",
        short_description="a skeletal scribe whose ledgers leave more room for present choices than past ownership",
        role="Necropolis free-name scribe and recurring first-ten contact",
        talk_alias="esh",
        outbound_room_key="undead_sunscar_road",
        waymeet_approach_key=WAYMEET_MARSH_ROAD_KEY,
        reward_key="heritage_free_name_lamp",
    ),
    "sporekin": OriginAdventureContact(
        key="first_ten_sporekin_guide_seven_rings",
        name="Guide Seven-Rings",
        short_description="a broad-capped Sporekin whose seven pale growth rings each carry a different remembered journey",
        role="Lumen Hollow guide and recurring first-ten contact",
        talk_alias="seven-rings",
        outbound_room_key="sporekin_memory_path",
        waymeet_approach_key=WAYMEET_GREEN_APPROACH_KEY,
        reward_key="heritage_chosen_chorus_sporeglass",
    ),
}


HERITAGE_REWARDS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        key="heritage_blackwall_road_seal",
        name="Blackwall Road Seal",
        description="A palm-sized blackened-iron seal issued after the Demon Gate held through a real crisis. It marks its bearer as someone trusted to carry Blackwall procedure onto shared roads.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_living_boundary_knot",
        name="Living Boundary Knot",
        description="A small cord knot woven around a living green twig. It remembers a boundary protected without turning the forest into a wall.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_fourth_chair_token",
        name="Fourth Chair Token",
        description="A thin lavender-grey disk engraved with three sight lines and one deliberately unfinished edge: a High Horizon reminder that the missing perspective still matters.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_one_bell_brass_stamp",
        name="One-Bell Brass Stamp",
        description="A square brass shift stamp cut from a retired safety plate. Its face records one bell of production deliberately lost so a crew could live.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_heap_held_plate",
        name="Heap-Held Plate",
        description="A crooked plate cut from three previous repairs and stamped only after a loaded wagon crossed safely. It is ugly, public, and proven useful.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_untaken_trophy_cord",
        name="Untaken Trophy Cord",
        description="A plain braided hunting cord with no tooth, claw, or horn tied to it. Frostroot gives it only for a hunt whose success was measured by who survived.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_free_name_lamp",
        name="Free-Name Lamp",
        description="A tiny smoked-glass Necropolis lamp etched with a blank ownership line and a present-name line. It burns for memory without treating memory as command.",
        category="keepsake",
        tier=1,
    ),
    ItemDefinition(
        key="heritage_chosen_chorus_sporeglass",
        name="Chosen Chorus Sporeglass",
        description="A thumb-sized piece of translucent fungal glass containing several separate threads that meet without merging. The Chorus records it as connection entered by choice.",
        category="keepsake",
        tier=1,
    ),
)


CONTACT_DIALOGUE: dict[str, tuple[str, ...]] = {
    "human": (
        "'A wall is not stone,' Elian says. 'It is people noticing the same crack before it becomes everybody else's problem.'",
        "'If a road sign only makes sense to the person who painted it, it is decoration, not procedure.'",
        "'Bring me what actually happened, not the version that makes Blackwall look best.'",
    ),
    "forest_elf": (
        "'Beautiful things still rot,' Sael says. 'Kneel down before you decide the grove is healthy.'",
        "'A boundary that cannot teach a stranger how to cross safely is only half a boundary.'",
        "'Protection is not the same thing as keeping every unfamiliar foot away.'",
    ),
    "moon_elf": (
        "'Bring me the angle you dislike most,' Yra says. 'That is usually the one the record is missing.'",
        "'Do not repair contradiction by deleting one witness.'",
        "'Leave room in the record for the person who has not arrived yet.'",
    ),
    "dwarf": (
        "'A stamped form can still describe a dead worker,' Orla says. 'Read the machine, then read the people around it.'",
        "'Standards exist to make work safer, not to make exceptions impossible.'",
        "'If the quota and the crew disagree, the crew gets to come home.'",
    ),
    "goblin": (
        "'Useful by itself ain't the same as useful together,' Pella says, tapping three mismatched ledgers into alignment.",
        "'Explain the claim before you make the claim. Saves shouting. Usually.'",
        "'If it holds, write down why it held. Otherwise the next genius gets to rediscover your mistake.'",
    ),
    "troll": (
        "'Snow lies less than frightened people,' Varka says. 'Read it before you start naming enemies.'",
        "'A guest does not have to prove they can freeze before you give them fire.'",
        "'A hunt is finished when the danger is finished. The corpse is optional.'",
    ),
    "undead": (
        "'A record may remember who owned your body,' Esh says. 'It does not get to continue owning you.'",
        "'The living can be afraid and still be right about the road.'",
        "'Preserve evidence. Destroy authority that has no living consent behind it.'",
    ),
    "sporekin": (
        "'Many voices can repeat one mistake very beautifully,' Seven-Rings says. 'Listen for the seam.'",
        "'Bring the Chorus what you saw, not what it expected you to see.'",
        "'Returning to us means more when you were capable of remaining apart.'",
    ),
}


# The middle reveal of every adventure deliberately changes what the player
# thought the problem was. These are story turns, not merely extra checklist text.
TWIST_LINES: dict[tuple[str, str], str] = {
    ("human", "home_crisis"): "The embarrassing part is not the cracked mortar: an outsider hauler reported the seam days ago, but Blackwall filed the warning under the wrong shift mark. The wall failed at the handoff between competent people.",
    ("human", "wider_world"): "Marshal Aven lays the outsider report beside three other road complaints. None accuse Humans of malice. They all describe the same problem: Blackwall's excellent symbols become dangerous the moment a non-Human has to read them at speed.",
    ("human", "capstone"): "The blocked wagon belongs to no single people. A Goblin axle hand spots the safest cut while a Dwarf braces the load and Human guards hold the crowd. The gate can only hold if Blackwall accepts competence it did not issue a uniform to.",
    ("forest_elf", "home_crisis"): "The rot is not an invading curse. A well-meant water diversion built to protect young roots has kept one old root wet for too long. The grove is being hurt by yesterday's correct answer.",
    ("forest_elf", "wider_world"): "Aven produces statements from travelers who genuinely tried to obey the forest markers. The problem is not disrespect: the signs assume knowledge outsiders were never given.",
    ("forest_elf", "capstone"): "The prowler is following the strong resin used on the new safe markers. The boundary fix itself created the hunting line, so protecting the crossing means changing your own work rather than blaming the animal.",
    ("moon_elf", "home_crisis"): "The witnesses are not contradicting one another. A moving tower shadow changes the reference mark between observations. The impossible record becomes ordinary once time is treated as another angle.",
    ("moon_elf", "wider_world"): "Aven's lowland map is crude about elevation and uncannily accurate about travel time. High Horizon's elegant chart and the ugly road ledger are each wrong exactly where the other is useful.",
    ("moon_elf", "capstone"): "Both disputed witnesses are right: a fast storm crossed one route between their observations. The conflict survives only if the record insists there must be one privileged vantage point.",
    ("dwarf", "home_crisis"): "Every department followed its own procedure. The pressure fault survived precisely because three correct ledgers used three different names for the same symptom.",
    ("dwarf", "wider_world"): "Aven's road crew has been using an off-spec Goblin fitting because it flexes where mountain-standard iron cracks. Rejecting it would satisfy the drawing and make the bridge worse.",
    ("dwarf", "capstone"): "The emergency replacement that gets the line moving again is partly foreign work. The lesson is not that standards were wrong; it is that a standard that cannot describe a safe exception is unfinished.",
    ("goblin", "home_crisis"): "Every ugly repair you test is individually clever. The sinking happens because each fix shifted load onto the next clever fix. Nobody made a bad patch; nobody owned the whole heap.",
    ("goblin", "wider_world"): "At Waymeet, Aven asks the wreck's owner what actually matters. It is not the polished latch everyone is arguing over but a battered map case with family notes inside. Value and shine turn out to be different things.",
    ("goblin", "capstone"): "The supposed scavengers are mostly neighbors trying to save their own material before floodwater takes it. The crisis is not thieves versus rescuers; it is ten reasonable claims colliding at once.",
    ("troll", "home_crisis"): "The great tracks point away from Frostroot, not toward it. Whatever made them smelled the camp and chose retreat. Fear turned a tired animal into an invading monster before anyone read the wind.",
    ("troll", "wider_world"): "One traveler at Aven's road post admits refusing Troll help on an earlier journey. The storm now puts that same person at Frostroot's fire. Hospitality becomes harder, and therefore more meaningful.",
    ("troll", "capstone"): "The white beast is not stalking sleepers. Its loops protect a hidden feeding trail and two half-grown young. Hunger made the road dangerous; killing for pride would create the next problem.",
    ("undead", "home_crisis"): "The old ledger is historically accurate. That is what makes it dangerous: nobody forged the ownership line, so nobody thought to ask when truth stopped being authority.",
    ("undead", "wider_world"): "Aven's living travelers carry a route memory copied from an old Necropolis death record. The memory is useful and obsolete at the same time; moving dunes have changed the safe line.",
    ("undead", "capstone"): "The relic does not control minds by overwhelming them. It sounds familiar. Newly reanimated people begin obeying because the command feels like remembered routine, which makes destroying it more urgent than any dramatic possession would.",
    ("sporekin", "home_crisis"): "The repeated warning is not consensus at all. One damaged node is echoing its final panic with perfect fidelity, and the Chorus has mistaken repetition for agreement.",
    ("sporekin", "wider_world"): "Aven compares the Chorus's inherited picture of Waymeet with your firsthand account. The shared memory is not false; it is simply missing mud, impatience, jokes, smells, and all the things nobody thought important enough to transmit.",
    ("sporekin", "capstone"): "The overwhelming signal comes from a healthy survival reflex amplified through damaged routing. No hostile mind is attacking the Chorus. The danger is connection without enough room for refusal.",
}


CAPSTONE_REACTIONS: dict[str, str] = {
    "human": "Elian presses the Blackwall seal into your palm. 'Now take the habit with you. The iron is just proof somebody trusted you with it.'",
    "forest_elf": "Sael ties the living knot loosely enough that the twig can still grow. 'A boundary should survive the person who drew it.'",
    "moon_elf": "Yra gives you the unfinished token without filling its missing edge. 'Do not complete it. That is the point.'",
    "dwarf": "Orla stamps the brass once. 'One bell lost. Crew intact. Best production figure I saw all season.'",
    "goblin": "Pella bites the edge of the crooked plate, nods, and hands it over. 'Held a wagon. That's a better signature than pretty.'",
    "troll": "Varka ties the empty cord around your wrist. 'Nothing hanging from it. Remember why.'",
    "undead": "Esh lights the little smoked-glass lamp. 'It remembers. It does not command. Keep the difference.'",
    "sporekin": "Seven-Rings turns the sporeglass until its separate threads catch the light. 'Together. Not erased.'",
}


LEGACY_STEP_INDEX = {"step_1": 0, "step_2": 2, "step_3": 3}


def _room_name(room_key: str) -> str:
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    return room.name if room is not None else room_key.replace("_", " ").title()


def _normalized(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _route_rooms(race_key: str, beat_key: str) -> tuple[str, str, str, str, str]:
    contact = ORIGIN_CONTACTS[race_key]
    start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
    if beat_key == "home_crisis":
        return (start, contact.outbound_room_key, contact.outbound_room_key, start, start)
    if beat_key == "wider_world":
        return (start, contact.outbound_room_key, WAYMEET_CROSSROADS_KEY, contact.waymeet_approach_key, start)
    return (start, contact.outbound_room_key, contact.waymeet_approach_key, contact.outbound_room_key, start)


def _briefing_text(race_key: str, beat) -> str:
    contact = ORIGIN_CONTACTS[race_key]
    voice = CONTACT_DIALOGUE[race_key][{"home_crisis": 0, "wider_world": 1, "capstone": 2}[beat.key]]
    return f"{contact.name} gives you the problem without pretending to have the answer. {beat.summary}\r\n{voice}"


def _report_text(race_key: str, beat) -> str:
    contact = ORIGIN_CONTACTS[race_key]
    if beat.key == "capstone":
        return CAPSTONE_REACTIONS[race_key]
    return (
        f"You give {contact.name} the whole account, including the part that made the first explanation wrong. "
        f"{contact.name.split()[0]} does not reduce it to a slogan; the new finding is entered into the work of the homeland."
    )


def _build_route(race_key: str, beat) -> AdventureRoute:
    contact = ORIGIN_CONTACTS[race_key]
    rooms = _route_rooms(race_key, beat.key)
    base = beat.steps
    intro_command = f"talk {contact.talk_alias} about {beat.key.replace('_', ' ')}"
    report_command = f"report to {contact.talk_alias}"
    steps = (
        AdventureStep(
            key="adventure_1",
            room_key=rooms[0],
            command=intro_command,
            objective=f"At {_room_name(rooms[0])}, TALK {contact.talk_alias.upper()} ABOUT {beat.key.replace('_', ' ').upper()}.",
            narrative=_briefing_text(race_key, beat),
        ),
        AdventureStep(
            key="adventure_2",
            room_key=rooms[1],
            command=base[0].command,
            objective=f"At {_room_name(rooms[1])}, {base[0].objective}",
            narrative=base[0].response,
        ),
        AdventureStep(
            key="adventure_3",
            room_key=rooms[2],
            command=base[1].command,
            objective=f"At {_room_name(rooms[2])}, {base[1].objective}",
            narrative=base[1].response + "\r\n\r\n" + TWIST_LINES[(race_key, beat.key)],
            twist=True,
            shared_world=rooms[2].startswith("waymeet_"),
        ),
        AdventureStep(
            key="adventure_4",
            room_key=rooms[3],
            command=base[2].command,
            objective=f"At {_room_name(rooms[3])}, {base[2].objective}",
            narrative=base[2].response,
            shared_world=rooms[3].startswith("waymeet_"),
        ),
        AdventureStep(
            key="adventure_5",
            room_key=rooms[4],
            command=report_command,
            objective=f"Return to {_room_name(rooms[4])} and REPORT TO {contact.talk_alias.upper()}.",
            narrative=_report_text(race_key, beat),
        ),
    )
    return AdventureRoute(
        race_key=race_key,
        beat_key=beat.key,
        steps=steps,
        reward_key=contact.reward_key if beat.key == "capstone" else None,
    )


def build_adventure_routes() -> dict[tuple[str, str], AdventureRoute]:
    return {
        (race_key, beat.key): _build_route(race_key, beat)
        for race_key, arc in first_ten.RACE_FIRST_TEN_ARCS.items()
        for beat in arc.beats
    }


ADVENTURE_ROUTES = build_adventure_routes()


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _replace_quest(definition: QuestDefinition) -> None:
    if definition.key in quests.QUESTS_BY_KEY:
        quests.QUESTS = tuple(definition if old.key == definition.key else old for old in quests.QUESTS)
    else:
        quests.QUESTS = quests.QUESTS + (definition,)
    quests.QUESTS_BY_KEY[definition.key] = definition


def _install_contacts(world_service=None) -> None:
    for race_key, contact in ORIGIN_CONTACTS.items():
        start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
        npc = NpcDefinition(
            key=contact.key,
            name=contact.name,
            short_description=contact.short_description,
            room_key=start,
            role=contact.role,
            dialogue=CONTACT_DIALOGUE[race_key],
        )
        _replace_npc(npc)
        room = legacy_world.ROOMS_BY_KEY.get(start)
        if room is None:
            continue
        if contact.key not in room.npc_keys:
            room = replace(room, npc_keys=room.npc_keys + (contact.key,))
            legacy_world.ROOMS = tuple(room if old.key == start else old for old in legacy_world.ROOMS)
            legacy_world.ROOMS_BY_KEY[start] = room
        if world_service is not None:
            world_service.legacy_rooms[start] = room
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(start, None)


def install_first_ten_adventure_content(world_service=None) -> None:
    # Keep the original first-ten contract as the source of level gates, XP, and
    # class capstones; this layer turns each compact milestone into a real route.
    first_ten.install_first_ten_content()

    known_items = set(crafting.ITEMS_BY_KEY)
    additions = tuple(item for item in HERITAGE_REWARDS if item.key not in known_items)
    if additions:
        crafting.ITEMS = crafting.ITEMS + additions
    crafting.ITEMS_BY_KEY.update({item.key: item for item in HERITAGE_REWARDS})

    _install_contacts(world_service)

    for race_key, arc in first_ten.RACE_FIRST_TEN_ARCS.items():
        for beat in arc.beats:
            route = ADVENTURE_ROUTES[(race_key, beat.key)]
            definition = QuestDefinition(
                key=beat.quest_key(race_key),
                name=beat.title,
                style="structured",
                minimum_level=beat.unlock_level,
                description=(
                    beat.summary
                    + " This is a routed heritage adventure: it moves through real homeland rooms"
                    + (" and the shared Waymeet roads." if beat.key != "home_crisis" else ".")
                ),
                objective_steps=tuple((step.key, step.objective) for step in route.steps)
                + (("complete", beat.completion_text),),
            )
            _replace_quest(definition)


def _route_step_for_state(route: AdventureRoute, state) -> AdventureStep:
    current = state.get("current_step") if state else None
    for step in route.steps:
        if step.key == current:
            return step
    if current in LEGACY_STEP_INDEX:
        return route.steps[LEGACY_STEP_INDEX[current]]
    return route.steps[0]


def _normalize_legacy_state(session, beat, route: AdventureRoute, state):
    current = state.get("current_step") if state else None
    if current not in LEGACY_STEP_INDEX:
        return state
    step = route.steps[LEGACY_STEP_INDEX[current]]
    session.database.advance_quest(session.character.id, beat.quest_key(route.race_key), step.key)
    state = dict(state)
    state["current_step"] = step.key
    return state


async def _show_adventure_heritage(session) -> None:
    c = session.character
    arc = first_ten.RACE_FIRST_TEN_ARCS.get(c.race or "")
    if arc is None:
        await session.send("Your origin does not have a first-ten racial arc yet.\r\n")
        return
    loop = STARTER_RACE_LOOPS_BY_RACE[arc.race_key]
    contact = ORIGIN_CONTACTS[arc.race_key]
    flags = session.database.list_flags(c.id)
    opening_done = loop.completion_flag in flags

    await session.send("\r\n--- Level 1-10 Heritage Story ---\r\n")
    await session.send(f"Recurring contact: {contact.name} at {_room_name(loop.starting_room_key)}.\r\n")
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

        state = first_ten._ensure_quest(session, arc.race_key, beat)
        route = ADVENTURE_ROUTES[(arc.race_key, beat.key)]
        if state is not None:
            state = _normalize_legacy_state(session, beat, route, state)
        step = _route_step_for_state(route, state)
        await session.send(
            f"{label} - {beat.title}: active.\r\n"
            f"Next destination: {_room_name(step.room_key)}.\r\n"
            f"Next action: {step.objective}\r\n"
        )
        if beat.key == "wider_world":
            await session.send("This act deliberately crosses into Waymeet so your homeland story collides with people who do not share its assumptions.\r\n")
        break

    await session.send("Your heritage story is woven through the same Waymeet, dungeon, faction, crafting, and Veyra world used by everyone else.\r\n")


def _refresh_character(session) -> int:
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed
    return session.character.level


async def _finish_adventure(session, arc, beat, route: AdventureRoute, step: AdventureStep) -> None:
    c = session.character
    await session.send("\r\n" + step.narrative + "\r\n")
    session.database.complete_quest(c.id, beat.quest_key(arc.race_key))
    session.database.grant_flag(c.id, beat.completion_flag(arc.race_key))
    new_level = session.database.add_experience(c.id, beat.xp_reward)
    _refresh_character(session)

    reward_text = ""
    if route.reward_key is not None:
        reward = crafting.ITEMS_BY_KEY[route.reward_key]
        if session.database.item_quantity(c.id, route.reward_key) <= 0:
            session.database.add_item(c.id, route.reward_key, 1)
        reward_text = f" and {reward.name}"

    await session.send(
        f"\r\n--- {beat.title} complete ---\r\n{beat.completion_text}\r\n"
        f"Reward: {beat.xp_reward} XP{reward_text}. You are level {new_level}.\r\n"
    )
    if beat.key == "capstone":
        line = first_ten.CLASS_CAPSTONE_BEATS.get(session.character.character_class or "")
        if line:
            await session.send(line + "\r\n")
        await session.send(
            "Your homeland now has a reason to remember you, and people on the shared roads have seen what your culture looks like under pressure. "
            "Your level 1-10 origin story is complete. JOURNEY now points into Veyra, class commissions, dungeons, factions, and the roads toward level 12+.\r\n"
        )


async def _complete_adventure_step(session, arc, beat, route: AdventureRoute, step: AdventureStep) -> None:
    index = route.steps.index(step)
    if index == len(route.steps) - 1:
        await _finish_adventure(session, arc, beat, route, step)
        return

    await session.send("\r\n" + step.narrative + "\r\n")
    nxt = route.steps[index + 1]
    session.database.advance_quest(session.character.id, beat.quest_key(arc.race_key), nxt.key)
    await session.send(
        f"\r\nNext destination: {_room_name(nxt.room_key)}.\r\n"
        f"Next: {nxt.objective}\r\n"
    )


async def _handle_adventure_command(session, command) -> bool:
    if session.character is None:
        return False
    normalized = _normalized(command)
    if normalized in {"heritage", "origin arc", "first ten", "1-10"}:
        await _show_adventure_heritage(session)
        return True

    current = first_ten._current_beat(session)
    if current is None:
        return False
    arc, beat = current
    if session.character.level < beat.unlock_level:
        return False

    state = first_ten._ensure_quest(session, arc.race_key, beat)
    if state is None or state.get("status") != "active":
        return False
    route = ADVENTURE_ROUTES[(arc.race_key, beat.key)]
    state = _normalize_legacy_state(session, beat, route, state)
    step = _route_step_for_state(route, state)

    if normalized != _normalized(step.command):
        return False
    if session.character.current_room != step.room_key:
        await session.send(
            f"That is part of {beat.title}, but not here. Go to {_room_name(step.room_key)} first.\r\n"
            f"HERITAGE will remind you of the current destination.\r\n"
        )
        return True

    await _complete_adventure_step(session, arc, beat, route, step)
    return True


def validate_first_ten_adventure_contract(world_service=None) -> None:
    problems: list[str] = []
    if set(ORIGIN_CONTACTS) != set(first_ten.RACE_FIRST_TEN_ARCS):
        problems.append("origin contact roster does not match racial first-ten roster")

    live_rooms = legacy_world.ROOMS_BY_KEY if world_service is None else world_service.legacy_rooms
    reward_keys = {item.key for item in HERITAGE_REWARDS}
    if len(reward_keys) != 8:
        problems.append("expected eight unique heritage keepsakes")

    for race_key, arc in first_ten.RACE_FIRST_TEN_ARCS.items():
        contact = ORIGIN_CONTACTS[race_key]
        start = STARTER_RACE_LOOPS_BY_RACE[race_key].starting_room_key
        if contact.key not in legacy_world.NPCS_BY_KEY:
            problems.append(f"{race_key}: recurring contact is not registered")
        room = live_rooms.get(start)
        if room is None or contact.key not in room.npc_keys:
            problems.append(f"{race_key}: recurring contact is not physically present at the start")
        if contact.reward_key not in crafting.ITEMS_BY_KEY:
            problems.append(f"{race_key}: capstone keepsake is not registered")

        for beat in arc.beats:
            route = ADVENTURE_ROUTES[(race_key, beat.key)]
            if len(route.steps) != 5:
                problems.append(f"{race_key}/{beat.key}: expected five routed story steps")
            if not any(step.twist for step in route.steps):
                problems.append(f"{race_key}/{beat.key}: no authored story turn")
            if len({step.room_key for step in route.steps}) < 2:
                problems.append(f"{race_key}/{beat.key}: never leaves one room")
            for step in route.steps:
                if step.room_key not in live_rooms:
                    problems.append(f"{race_key}/{beat.key}: missing room {step.room_key}")
            if beat.key == "wider_world":
                if WAYMEET_CROSSROADS_KEY not in {step.room_key for step in route.steps}:
                    problems.append(f"{race_key}: wider-world act never reaches Waymeet Crossroads")
                if not any(step.shared_world for step in route.steps):
                    problems.append(f"{race_key}: wider-world act has no shared-world step")
            if beat.key == "capstone" and route.reward_key != contact.reward_key:
                problems.append(f"{race_key}: capstone does not award its heritage keepsake")

    if problems:
        raise RuntimeError("First-ten adventure contract failed:\n- " + "\n- ".join(problems))


def install_first_ten_adventures_runtime(player_session_class, world_service=None) -> None:
    install_first_ten_adventure_content(world_service)
    validate_first_ten_adventure_contract(world_service)
    # first_ten's prompt wrapper resolves this module-global handler dynamically,
    # so replacing it upgrades already-installed first-ten behavior without adding
    # another prompt wrapper to the production stack.
    first_ten._handle_arc_command = _handle_adventure_command
    first_ten._show_heritage = _show_adventure_heritage
    player_session_class._first_ten_adventures_installed = True
