from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_city import MOON_ELF_HORIZON_DECK_KEY, MOON_ELF_REGION_KEY
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_CROWN_MIRROR_ARRAY_KEY = "moon_elf_crown_mirror_array"
MOON_ELF_WIZARD_QUEST_KEY = "moon_elf_wizard_first_explanation"
MOON_ELF_WIZARD_COMPLETE_FLAG = "moon_elf_wizard_first_explanation_complete"
MOON_ELF_WIZARD_ARRAY_INSPECTED_FLAG = "moon_elf_wizard_array_inspected"
MOON_ELF_WIZARD_NORTH_VIEW_FLAG = "moon_elf_wizard_north_view"
MOON_ELF_WIZARD_SOUTH_VIEW_FLAG = "moon_elf_wizard_south_view"
MOON_ELF_WIZARD_BRACKET_FOUND_FLAG = "moon_elf_wizard_bracket_found"
MOON_ELF_WIZARD_COLLAR_SET_FLAG = "moon_elf_wizard_collar_set"
MOON_ELF_WIZARD_FIRST_COLDFIRE_FLAG = "moon_elf_wizard_first_coldfire"
MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG = "moon_elf_wizard_beacon_aligned"

CORIN_VAEL_KEY = "moon_elf_wizard_corin_vael"


MOON_ELF_WIZARD_QUEST = QuestDefinition(
    key=MOON_ELF_WIZARD_QUEST_KEY,
    name="The First Explanation",
    style="structured",
    description=(
        "After The Third Chair, a Moon Elf Wizard is sent to the Crown Mirror Array, where one of High Horizon's ordinary navigation lights is falling slightly out of alignment. "
        "The lesson is not to fix the first thing that looks wrong. Observe the array, compare it from two sighting rails, identify the actual fault, use ordinary adjustment first, then apply a small controlled Coldfire Burst only where heat is truly needed."
    ),
    objective_steps=(
        ("meet_corin", "From the Horizon Deck, go EAST to the Crown Mirror Array and TALK CORIN."),
        ("inspect_array", "EXAMINE MIRROR ARRAY before touching any part of it."),
        ("compare_views", "SIGHT NORTH RAIL and SIGHT SOUTH RAIL. Both views are required."),
        ("check_bracket", "CHECK BRACKET after comparing both sight lines."),
        ("set_collar", "SET ALIGNMENT COLLAR using the ordinary adjustment before reaching for magic."),
        ("heat_pin", "Use a small controlled spell with COLDFIRE BURST PIN."),
        ("verify_beacon", "CHECK BEACON and confirm the navigation light is actually aligned."),
        ("return_corin", "TALK CORIN after the verification."),
        ("complete", "You learned that power tells you what you can change; understanding tells you what to change."),
    ),
)


CORIN_VAEL = NpcDefinition(
    key=CORIN_VAEL_KEY,
    name="Wizard Corin Vael",
    short_description=(
        "a Moon Elf Wizard in a wind-fastened work coat, holding a sighting slate and a tiny brass wrench instead of a staff"
    ),
    room_key=MOON_ELF_CROWN_MIRROR_ARRAY_KEY,
    role="Moon Elf Wizard mentor and civic optical-maintenance keeper",
    dialogue=(
        "Corin squints through one of the rail sights. 'The first explanation is useful. It gives you somewhere to begin. The mistake is promoting it to truth before you have earned that.'",
        "'Power tells you what you can change. Understanding tells you what to change.'",
        "'If the mirror looks wrong, that is evidence that something looks wrong. It is not yet evidence that the mirror is the problem.'",
    ),
)


MOON_ELF_CROWN_MIRROR_ARRAY = RoomDefinition(
    key=MOON_ELF_CROWN_MIRROR_ARRAY_KEY,
    name="Crown Mirror Array",
    region_key=MOON_ELF_REGION_KEY,
    description=(
        "A narrow maintenance platform projects east from the Horizon Deck near the crown of Skyglass Spire. Three polished mirror plates, two prismatic skyglass lenses, and a hooded civic lamp sit in a braced frame aimed toward the high switchback roads below. The array does not predict anything and is not sacred; it simply throws a clean navigation line across the mountain approaches after dark. "
        "Two sighting rails run along opposite sides of the platform. Their engraved marks let a keeper compare the same light path from different positions before loosening a single fitting. Wind hums around the tower ribs, but the work surface itself is solid and carefully fenced."
    ),
    exits={"west": MOON_ELF_HORIZON_DECK_KEY},
    npc_keys=(CORIN_VAEL_KEY,),
    tags=("safe", "moon_elf_start", "wizard", "optics", "navigation", "civic_work", "perspective"),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    aliases: tuple[str, ...],
    *,
    condition: ViewCondition | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        condition=condition or ViewCondition(),
    )


def moon_elf_wizard_augmentations() -> dict[str, RoomAugmentation]:
    both_views = ViewCondition(required_flags=(MOON_ELF_WIZARD_NORTH_VIEW_FLAG, MOON_ELF_WIZARD_SOUTH_VIEW_FLAG))
    bracket_found = ViewCondition(required_flags=(MOON_ELF_WIZARD_BRACKET_FOUND_FLAG,))
    collar_set = ViewCondition(required_flags=(MOON_ELF_WIZARD_COLLAR_SET_FLAG,))
    aligned = ViewCondition(required_flags=(MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG,))
    not_aligned = ViewCondition(forbidden_flags=(MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG,))

    return {
        MOON_ELF_CROWN_MIRROR_ARRAY_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "west",
                    MOON_ELF_HORIZON_DECK_KEY,
                    "Horizon Deck",
                    travel_text="You leave the mirror platform and step west onto the broad public Horizon Deck.",
                ),
            ),
            features=(
                _feature(
                    "crown_mirror_array",
                    "Crown Mirror Array",
                    "three polished mirror plates and two skyglass lenses set around a hooded navigation lamp",
                    "At first glance the middle mirror appears a fraction low. The lamp itself burns cleanly, none of the glass is cracked, and the frame has no obvious break. The visible error is real; its cause is not yet established.",
                    ("array", "mirror array", "crown mirror array", "mirrors", "lenses", "navigation light"),
                ),
                _feature(
                    "crown_north_sight",
                    "North Sighting Rail",
                    "an engraved rail used to compare the beacon line from the platform's north side",
                    "The rail has old correction marks, a fixed brass sight, and a reference notch aimed at a white stone marker on the distant switchback road.",
                    ("north rail", "north sight", "north sighting rail", "north reference"),
                ),
                _feature(
                    "crown_south_sight",
                    "South Sighting Rail",
                    "a matching sighting rail on the opposite side of the platform",
                    "The second rail exists precisely because one angle can make a nearly aligned optical system look more certain than it is. Its reference notch points to the same distant road marker from a different baseline.",
                    ("south rail", "south sight", "south sighting rail", "south reference"),
                ),
                _feature(
                    "crown_twisted_bracket",
                    "Twisted Lens Bracket",
                    "a secondary lens bracket turned by barely more than a fingernail's width",
                    "With both sight lines in mind, the fault becomes clear. The center mirror is still true to its mounting marks. The smaller lens bracket behind it has twisted slightly, changing the apparent path of the reflected light. A seized retaining pin is holding the bracket just off its proper seat.",
                    ("bracket", "lens bracket", "twisted bracket", "retaining pin", "pin"),
                    condition=both_views,
                ),
                _feature(
                    "crown_alignment_collar",
                    "Alignment Collar",
                    "a fine mechanical collar around the secondary lens mount",
                    "The collar is the ordinary adjustment for this problem. It can put the bracket back on its engraved reference line, but the old retaining pin must be warmed slightly before it will seat without forcing the glass frame.",
                    ("collar", "alignment collar", "adjustment collar", "lens collar"),
                    condition=bracket_found,
                ),
                _feature(
                    "crown_prepared_pin",
                    "Prepared Retaining Pin",
                    "the old retaining pin resting squarely against the realigned collar, ready for a brief controlled warming",
                    "Nothing needs a blast. The pin only needs enough carefully placed heat to relax the old locking compound and settle into the collar's notch. Heating the mirror or lens would be careless and unnecessary.",
                    ("prepared pin", "retaining pin", "pin", "locking pin"),
                    condition=collar_set,
                ),
                _feature(
                    "crown_aligned_beacon",
                    "Aligned Beacon Line",
                    "a clean line of lamplight passing through both lenses and striking the distant road marker",
                    "The navigation line now lands exactly on the white switchback marker from both sighting rails. The mirror that looked wrong at first was never adjusted at all.",
                    ("beacon", "beacon line", "aligned beacon", "navigation beacon", "light line"),
                    condition=aligned,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "crown_array_misaligned",
                    "The navigation line is visibly a little off its distant road marker, enough to matter to someone approaching the high switchbacks in darkness and not enough to justify panic.",
                    priority=45,
                    condition=not_aligned,
                ),
                DescriptionLayer(
                    "crown_array_compared",
                    "After comparing both rails, the apparent error no longer points cleanly at the center mirror. The two viewpoints disagree in a way that makes the secondary lens mount more suspicious than the mirror face.",
                    priority=60,
                    condition=both_views,
                ),
                DescriptionLayer(
                    "crown_array_aligned",
                    "The corrected beacon holds steady on its road marker while the mirror plates continue doing exactly what they were doing before anyone blamed them.",
                    priority=85,
                    condition=aligned,
                ),
            ),
        )
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _patch_horizon_deck() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_HORIZON_DECK_KEY]
    exits = dict(original.exits)
    exits["east"] = MOON_ELF_CROWN_MIRROR_ARRAY_KEY
    description = original.description
    if "Crown Mirror Array" not in description:
        description += (
            " A fenced maintenance bridge runs east to the Crown Mirror Array, where polished optics aim an ordinary civic navigation light toward the mountain approaches."
        )
    return replace(original, exits=exits, description=description)


def install_moon_elf_wizard_content(world_service=None) -> None:
    if MOON_ELF_WIZARD_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_WIZARD_QUEST,)
    quests.QUESTS_BY_KEY[MOON_ELF_WIZARD_QUEST.key] = MOON_ELF_WIZARD_QUEST

    _replace_room(MOON_ELF_CROWN_MIRROR_ARRAY)
    _replace_npc(CORIN_VAEL)
    horizon_deck = _patch_horizon_deck()
    _replace_room(horizon_deck)

    if world_service is None:
        return

    world_service.legacy_rooms[MOON_ELF_CROWN_MIRROR_ARRAY_KEY] = MOON_ELF_CROWN_MIRROR_ARRAY
    world_service.legacy_rooms[MOON_ELF_HORIZON_DECK_KEY] = horizon_deck
    world_service.augmentations.update(moon_elf_wizard_augmentations())

    base = world_service.augmentations.get(MOON_ELF_HORIZON_DECK_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "east"]
    exits.append(
        ExitDefinition(
            "east",
            MOON_ELF_CROWN_MIRROR_ARRAY_KEY,
            "Crown Mirror Array",
            travel_text="You cross the fenced maintenance bridge east from the Horizon Deck to the mirror platform.",
        )
    )
    world_service.augmentations[MOON_ELF_HORIZON_DECK_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(MOON_ELF_CROWN_MIRROR_ARRAY_KEY, None)
        cache.pop(MOON_ELF_HORIZON_DECK_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "moon_elf" and character.character_class == "wizard")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, MOON_ELF_WIZARD_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_wizard_start(session) -> bool:
    if not _qualifies(session):
        return False
    if MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "meet_corin")
    return True


def _in_array(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == MOON_ELF_CROWN_MIRROR_ARRAY_KEY)


async def _talk_corin(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session):
        return False
    step = quest.get("current_step")

    if step == "meet_corin":
        session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "inspect_array")
        await session.send(
            "\r\nCorin hands you the sighting slate before he tells you what he thinks is wrong.\r\n"
            "'One navigation line is drifting. From the deck it looks like the center mirror is low. That is our first explanation, not our conclusion.'\r\n"
            "He rests the tiny wrench on the rail. 'Before you touch anything: EXAMINE MIRROR ARRAY.'\r\n"
        )
        return True

    if step == "return_corin":
        session.database.complete_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY)
        session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_COMPLETE_FLAG)
        await session.send(
            "\r\nCorin checks the north rail, walks to the south rail, and checks it again before he looks satisfied.\r\n"
            "'The mirror was the first explanation. The bracket was the better one. The difference was two viewpoints and enough patience not to cast at the first thing that looked guilty.'\r\n"
            "He pockets the brass wrench. 'Power tells you what you can change. Understanding tells you what to change.'\r\n"
            "The corrected navigation line holds steady over the switchback road below. Nobody applauds. Somewhere on the mountain, someone will simply see the light where it is supposed to be.\r\n"
            "\r\nQuest complete: The First Explanation.\r\n"
        )
        return True

    objective = MOON_ELF_WIZARD_QUEST.objective_for_step(step)
    await session.send(
        "\r\nCorin taps the sighting slate. 'Do not let having a spell shorten the thinking that should come before it.'\r\n"
    )
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_array(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "inspect_array":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_ARRAY_INSPECTED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "compare_views")
    await session.send(
        "\r\nThe center mirror appears slightly low, but its engraved mounting lines still match the frame. The lamp burns evenly. Both lenses are intact. The light misses its distant marker by only a little.\r\n"
        "Corin says, 'Good. You found the obvious answer and one fact that already makes it less comfortable. Now compare positions: SIGHT NORTH RAIL and SIGHT SOUTH RAIL.'\r\n"
    )
    return True


async def _sight_north(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_NORTH_VIEW_FLAG)
    await session.send(
        "\r\nThrough the north sight, the beacon lands left of the road marker. The center mirror still looks a little low, but the reflected line bends most sharply after the secondary lens.\r\n"
        "Corin says, 'Useful. Not final.'\r\n"
    )
    if MOON_ELF_WIZARD_SOUTH_VIEW_FLAG in _flags(session):
        session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "check_bracket")
        await session.send("You have both views now. CHECK BRACKET.\r\n")
    else:
        await session.send("Now SIGHT SOUTH RAIL.\r\n")
    return True


async def _sight_south(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_SOUTH_VIEW_FLAG)
    await session.send(
        "\r\nFrom the south sight, the center mirror's mounting marks line up almost perfectly. The error appears instead as a tiny rotation where the secondary lens joins its bracket. What looked like a low mirror from the deck now looks like a twisted support from here.\r\n"
        "Corin says, 'The first view was not useless. It was incomplete.'\r\n"
    )
    if MOON_ELF_WIZARD_NORTH_VIEW_FLAG in _flags(session):
        session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "check_bracket")
        await session.send("You have both views now. CHECK BRACKET.\r\n")
    else:
        await session.send("Now SIGHT NORTH RAIL.\r\n")
    return True


async def _check_bracket(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "check_bracket":
        return False
    flags = _flags(session)
    if not {MOON_ELF_WIZARD_NORTH_VIEW_FLAG, MOON_ELF_WIZARD_SOUTH_VIEW_FLAG}.issubset(flags):
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_BRACKET_FOUND_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "set_collar")
    await session.send(
        "\r\nUp close, the secondary lens bracket is twisted by barely more than a fingernail's width. The mirror face itself has never moved. A retaining pin has seized with the bracket just off its engraved seat.\r\n"
        "Corin gives you the tiny wrench. 'Now we know what is wrong. Use the ordinary adjustment first. SET ALIGNMENT COLLAR.'\r\n"
    )
    return True


async def _set_collar(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "set_collar":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_COLLAR_SET_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "heat_pin")
    await session.send(
        "\r\nYou ease the alignment collar back to its reference mark with the brass wrench. The bracket returns square, but the old retaining pin stops just short of seating. Forcing it would put stress through the lens frame.\r\n"
        "Corin points to the pin, not the mirror. 'There. That is the part that actually needs magic. A breath of heat, no more. COLDFIRE BURST PIN.'\r\n"
    )
    return True


async def _coldfire_pin(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session):
        return False
    if quest.get("current_step") != "heat_pin":
        await session.send(
            "\r\nCorin raises one hand. 'Not yet. We do not cast at the first object that looks wrong. Establish the fault first.'\r\n"
        )
        return True
    flags = _flags(session)
    if MOON_ELF_WIZARD_COLLAR_SET_FLAG not in flags:
        await session.send("\r\nThe collar has not been mechanically aligned yet. SET ALIGNMENT COLLAR first.\r\n")
        return True
    if MOON_ELF_WIZARD_FIRST_COLDFIRE_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "coldfire_burst", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_FIRST_COLDFIRE_FLAG)
    session.database.grant_flag(session.character.id, MOON_ELF_WIZARD_BEACON_ALIGNED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "verify_beacon")
    await session.send(
        "\r\nYou compress Coldfire Burst down to a brief blue-white tongue around the retaining pin. You do not heat the mirror. You do not heat the lens. The old locking compound softens, the pin settles into its notch, and you end the spell immediately.\r\n"
        "The light line shifts across the distant road marker. Corin does not call that success yet. 'Magic moved something. CHECK BEACON.'\r\n"
    )
    return True


async def _verify_beacon(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_array(session) or quest.get("current_step") != "verify_beacon":
        return False
    await session.send(
        "\r\nYou check the navigation line against both rail references. North and south now agree: the beam passes cleanly through both lenses and lands on the white switchback marker. The center mirror that looked wrong at first has not been adjusted at all.\r\n"
        "Corin smiles slightly. 'There is the difference between changing something and fixing it. TALK CORIN.'\r\n"
    )
    session.database.advance_quest(session.character.id, MOON_ELF_WIZARD_QUEST_KEY, "return_corin")
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_moon_elf_wizard_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Moon Elf Wizard extension after The Third Chair."""
    if getattr(player_session_class, "_moon_elf_wizard_runtime_installed", False):
        return

    install_moon_elf_wizard_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_wizard_start(self):
            await self.send(
                "\r\nA Skyglass maintenance runner catches you with a sighting slate tucked under one arm.\r\n"
                "'Wizard Corin Vael needs another pair of trained eyes at the Crown Mirror Array, east from the Horizon Deck. One navigation light is slightly out. He says not to fix anything before he tells you why that sentence is dangerous.'\r\n"
                "\r\nNew quest: The First Explanation.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().replace("’", "'").split())

        handled = False
        if normalized in {"talk corin", "talk wizard corin", "talk corin vael", "talk wizard corin vael"}:
            handled = await _talk_corin(self)
        elif normalized in {"examine mirror array", "inspect mirror array", "look mirror array", "examine array", "inspect array", "examine mirrors"}:
            handled = await _inspect_array(self)
        elif normalized in {"sight north rail", "use north rail", "view north rail", "north sight", "sight north"}:
            handled = await _sight_north(self)
        elif normalized in {"sight south rail", "use south rail", "view south rail", "south sight", "sight south"}:
            handled = await _sight_south(self)
        elif normalized in {"check bracket", "examine bracket", "inspect bracket", "check lens bracket", "examine lens bracket"}:
            handled = await _check_bracket(self)
        elif normalized in {"set alignment collar", "adjust alignment collar", "set collar", "adjust collar", "align collar"}:
            handled = await _set_collar(self)
        elif normalized in {
            "coldfire burst pin", "coldfire pin", "cast coldfire burst pin", "cast coldfire burst on pin",
            "use coldfire burst pin", "use coldfire burst on pin", "coldfire retaining pin", "coldfire burst retaining pin",
            "coldfire burst mirror", "coldfire mirror", "coldfire burst array", "coldfire array"
        }:
            handled = await _coldfire_pin(self)
        elif normalized in {"check beacon", "verify beacon", "inspect beacon", "check navigation light", "verify navigation light", "check light"}:
            handled = await _verify_beacon(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_wizard_start(self):
            await self.send(
                "\r\nAs The Third Chair lesson settles, a Skyglass maintenance runner catches up with you.\r\n"
                "'Corin Vael needs a Wizard at the Crown Mirror Array, east from the Horizon Deck. One navigation line is slightly out. He says the first explanation is probably the dangerous part.'\r\n"
                "\r\nNew quest: The First Explanation.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_wizard_runtime_installed = True
