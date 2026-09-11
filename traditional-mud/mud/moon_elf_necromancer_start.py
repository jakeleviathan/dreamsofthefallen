from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_city import MOON_ELF_JOURNAL_GALLERY_KEY, MOON_ELF_REGION_KEY
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_AFTERIMAGE_NICHE_KEY = "moon_elf_afterimage_niche"
MOON_ELF_NECROMANCER_QUEST_KEY = "moon_elf_necromancer_shape_left_behind"
MOON_ELF_NECROMANCER_COMPLETE_FLAG = "moon_elf_necromancer_shape_left_behind_complete"
MOON_ELF_NECROMANCER_TRACE_FLAG = "moon_elf_necromancer_residue_traced"
MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG = "moon_elf_necromancer_doorway_view"
MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG = "moon_elf_necromancer_window_view"
MOON_ELF_NECROMANCER_EDGES_FLAG = "moon_elf_necromancer_edges_mapped"
MOON_ELF_NECROMANCER_FADED_FLAG = "moon_elf_necromancer_residue_faded"

SAEL_ORUNE_KEY = "moon_elf_necromancer_sael_orune"


MOON_ELF_NECROMANCER_QUEST = QuestDefinition(
    key=MOON_ELF_NECROMANCER_QUEST_KEY,
    name="The Shape Left Behind",
    style="structured",
    description=(
        "After The Third Chair, a Moon Elf Necromancer is asked to help document a harmless death-residue in a quiet reading niche. "
        "The lesson is to distinguish evidence from personhood: observe the afterimage, compare it from more than one position, map where it actually ends, and then let it fade without calling, binding, siphoning, or pretending it is a ghost."
    ),
    objective_steps=(
        ("meet_sael", "From the Journal Gallery, go NORTH to the Afterimage Niche and TALK SAEL."),
        ("inspect_niche", "EXAMINE CUSHION and establish what is physically present before reading the magic around it."),
        ("trace_residue", "TRACE RESIDUE without addressing it as though it were a person."),
        ("compare_views", "VIEW FROM DOORWAY and VIEW FROM WINDOW. Compare both before deciding what the trace means."),
        ("map_edges", "MARK EDGES where the residue actually weakens and stops."),
        ("let_fade", "WAIT FOR FADE instead of binding or feeding on the trace."),
        ("return_sael", "TALK SAEL and explain what remained, what did not, and why the difference matters."),
        ("complete", "You learned that a trace can be real without being a person, a message, or an invitation to interfere."),
    ),
)


SAEL_ORUNE = NpcDefinition(
    key=SAEL_ORUNE_KEY,
    name="Necromancer Sael Orune",
    short_description=(
        "a Moon Elf Necromancer kneeling beside a chalk grid with mapping cord, a wax tablet, and none of the theatrical equipment people expect from the profession"
    ),
    room_key=MOON_ELF_AFTERIMAGE_NICHE_KEY,
    role="Moon Elf Necromancer mentor and civic death-residue specialist",
    dialogue=(
        "Sael checks a chalk mark against the open window. 'Not everything that lingers is a voice. If you forget that, you will spend your career inventing ghosts and then blaming the dead for them.'",
        "'A trace can be true without being a person. Necromancy becomes dangerous when certainty arrives before observation.'",
        "'We are here to discern what remains, not to make it dramatic enough to deserve us.'",
    ),
)


MOON_ELF_AFTERIMAGE_NICHE = RoomDefinition(
    key=MOON_ELF_AFTERIMAGE_NICHE_KEY,
    name="Afterimage Niche",
    region_key=MOON_ELF_REGION_KEY,
    description=(
        "A small reading chamber opens from the north end of the Journal Gallery into the mountain air. One side is enclosed by warm stone and book cabinets; the other ends in a broad open window above the valley. A low reading cushion sits beside a tea shelf and a narrow table where retired journal restorer Teren Veyl spent most afternoons for decades. "
        "Teren died here peacefully several days ago. His body, books, and personal things have already gone to his family. The room is clean, ordinary, and empty of any corpse. Only a faint necromantic afterimage remains: a soft uneven pressure in the magic near the place he used to sit."
    ),
    exits={"south": MOON_ELF_JOURNAL_GALLERY_KEY},
    npc_keys=(SAEL_ORUNE_KEY,),
    tags=("safe", "moon_elf_start", "necromancer", "death_residue", "observation", "quiet"),
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


def moon_elf_necromancer_augmentations() -> dict[str, RoomAugmentation]:
    traced = ViewCondition(required_flags=(MOON_ELF_NECROMANCER_TRACE_FLAG,))
    mapped = ViewCondition(required_flags=(MOON_ELF_NECROMANCER_EDGES_FLAG,))
    faded = ViewCondition(required_flags=(MOON_ELF_NECROMANCER_FADED_FLAG,))
    not_faded = ViewCondition(forbidden_flags=(MOON_ELF_NECROMANCER_FADED_FLAG,))
    return {
        MOON_ELF_AFTERIMAGE_NICHE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "south",
                    MOON_ELF_JOURNAL_GALLERY_KEY,
                    "Journal Gallery",
                    travel_text="You leave the quiet niche and step south into the warm rows and reading alcoves of the Journal Gallery.",
                ),
            ),
            features=(
                _feature(
                    "afterimage_reading_cushion",
                    "Reading Cushion",
                    "a flattened blue-grey cushion beside a low table and an empty tea shelf",
                    "The cushion shows decades of use, but nothing supernatural to ordinary sight. Teren Veyl died here after an ordinary afternoon of reading. His family has already taken his belongings. A place someone occupied for years can be meaningful without the place becoming that person.",
                    ("cushion", "reading cushion", "seat", "teren's seat", "teren seat"),
                ),
                _feature(
                    "afterimage_open_window",
                    "Open Sky Window",
                    "a broad unglazed opening framing the valley and the distant lower ridges",
                    "From the window side of the niche, the reading cushion is seen almost edge-on. Sael has left the floor clear so the same magical trace can be compared from this position and from the doorway.",
                    ("window", "open window", "sky window", "valley"),
                ),
                _feature(
                    "afterimage_chalk_grid",
                    "Chalk Grid",
                    "a simple floor grid for marking where the necromantic pressure strengthens and weakens",
                    "The grid contains no summoning circle. It is measurement: numbered chalk marks, mapping cord, and space for corrections when the first reading proves incomplete.",
                    ("grid", "chalk grid", "marks", "mapping grid"),
                ),
                _feature(
                    "afterimage_residue",
                    "Faint Afterimage",
                    "a quiet necromantic pressure clustered near the old reading place",
                    "Once traced, the residue has shape but no voice, language, intention, face, memory, or answer. It is strongest near the cushion and thins unevenly into the room. Something remains; nothing about that fact makes the remainder Teren Veyl.",
                    ("residue", "afterimage", "trace", "death residue", "faint afterimage"),
                    condition=traced,
                ),
                _feature(
                    "afterimage_mapped_edges",
                    "Mapped Edges",
                    "small chalk ticks showing exactly where the afterimage falls below perception",
                    "The marks make the lesson difficult to romanticize. The trace occupies a limited, irregular area. It does not reach toward Teren's books, his family, the city, or the moon. Its boundary is evidence against the story imagination first wants to tell.",
                    ("edges", "mapped edges", "chalk ticks", "boundary", "boundaries"),
                    condition=mapped,
                ),
                _feature(
                    "afterimage_empty_air",
                    "Quiet Air",
                    "ordinary cool mountain air where the last detectable residue has finally faded",
                    "Nothing dramatic replaces the afterimage. There is no departing apparition, last message, or sudden certainty about the afterlife. The room is simply a room again.",
                    ("air", "quiet air", "empty air", "faded residue"),
                    condition=faded,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "afterimage_present",
                    "The lingering pressure is subtle enough that anyone hoping for a haunting would probably be disappointed.",
                    priority=45,
                    condition=not_faded,
                ),
                DescriptionLayer(
                    "afterimage_traced",
                    "With your necromantic attention engaged, the residue resolves into an uneven afterimage rather than a figure: denser near the cushion, thinner toward the walls, silent everywhere.",
                    priority=60,
                    condition=traced,
                ),
                DescriptionLayer(
                    "afterimage_faded",
                    "The afterimage has dispersed on its own. Sael leaves the chalk marks in place because the absence is part of the record too.",
                    priority=90,
                    condition=faded,
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


def _patch_journal_gallery() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_JOURNAL_GALLERY_KEY]
    exits = dict(original.exits)
    exits["north"] = MOON_ELF_AFTERIMAGE_NICHE_KEY
    description = original.description
    if "Afterimage Niche" not in description:
        description += (
            " A narrow north passage leads to the Afterimage Niche, a small reading chamber temporarily being documented by one of the city's Necromancers before it returns to ordinary use."
        )
    return replace(original, exits=exits, description=description)


def install_moon_elf_necromancer_content(world_service=None) -> None:
    if MOON_ELF_NECROMANCER_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_NECROMANCER_QUEST,)
    quests.QUESTS_BY_KEY[MOON_ELF_NECROMANCER_QUEST.key] = MOON_ELF_NECROMANCER_QUEST

    _replace_room(MOON_ELF_AFTERIMAGE_NICHE)
    _replace_npc(SAEL_ORUNE)
    journal_gallery = _patch_journal_gallery()
    _replace_room(journal_gallery)

    if world_service is None:
        return

    world_service.legacy_rooms[MOON_ELF_AFTERIMAGE_NICHE_KEY] = MOON_ELF_AFTERIMAGE_NICHE
    world_service.legacy_rooms[MOON_ELF_JOURNAL_GALLERY_KEY] = journal_gallery
    world_service.augmentations.update(moon_elf_necromancer_augmentations())

    base = world_service.augmentations.get(MOON_ELF_JOURNAL_GALLERY_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "north"]
    exits.append(
        ExitDefinition(
            "north",
            MOON_ELF_AFTERIMAGE_NICHE_KEY,
            "Afterimage Niche",
            travel_text="You follow the narrow north passage from the Journal Gallery into the quiet reading niche.",
        )
    )
    world_service.augmentations[MOON_ELF_JOURNAL_GALLERY_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(MOON_ELF_AFTERIMAGE_NICHE_KEY, None)
        cache.pop(MOON_ELF_JOURNAL_GALLERY_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "moon_elf" and character.character_class == "necromancer")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, MOON_ELF_NECROMANCER_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_necromancer_start(session) -> bool:
    if not _qualifies(session):
        return False
    if MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "meet_sael")
    return True


def _in_niche(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == MOON_ELF_AFTERIMAGE_NICHE_KEY)


async def _talk_sael(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session):
        return False
    step = quest.get("current_step")

    if step == "meet_sael":
        session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "inspect_niche")
        await session.send(
            "\r\nSael is tying one end of a measuring cord to a floor weight when you arrive.\r\n"
            "'Teren Veyl died here several days ago. Peacefully. His family has his body and his things. What remains in this room is much smaller than a person.'\r\n"
            "Sael looks toward the empty cushion. 'Not everything that lingers is a voice. If you treat every trace as a ghost, you stop observing and start writing dialogue for the dead.'\r\n"
            "'Start before the magic. EXAMINE CUSHION.'\r\n"
        )
        return True

    if step == "return_sael":
        session.database.complete_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY)
        session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_COMPLETE_FLAG)
        await session.send(
            "\r\nSael reads your chalk map, then looks at the now-ordinary air where the trace used to be.\r\n"
            "'Good. The residue was real. It had shape. It had a boundary. It changed over time. None of those facts made it Teren.'\r\n"
            "Sael rolls up the mapping cord. 'A Necromancer has access to things other people cannot always perceive. That makes restraint more important, not less.'\r\n"
            "'Discern first. Do not dramatize what you have not established. What stays behind can matter without becoming the person who left it.'\r\n"
            "\r\nQuest complete: The Shape Left Behind.\r\n"
        )
        return True

    objective = MOON_ELF_NECROMANCER_QUEST.objective_for_step(step)
    await session.send(
        "\r\nSael taps the chalk once. 'Stay with the evidence. A trace does not become a person because the story would be more interesting.'\r\n"
    )
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_cushion(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "inspect_niche":
        return False
    session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "trace_residue")
    await session.send(
        "\r\nThe cushion is worn flat on one side. There is a tea ring on the low table and a repaired nick in the stone where a chair leg once struck it. Nothing moves. Nothing whispers. Nothing in the ordinary room claims to be Teren Veyl.\r\n"
        "Sael nods. 'Good. Now use the sense your training gives you. TRACE RESIDUE. Do not speak to it.'\r\n"
    )
    return True


async def _trace_residue(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "trace_residue":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_TRACE_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "compare_views")
    await session.send(
        "\r\nYou extend necromantic attention through the room without pulling on anything. A faint afterimage resolves near the cushion: pressure, thinning gradients, a few denser knots where life and long habit seem to have left temporary magical disturbance.\r\n"
        "There is no face in it. No memory opens. No voice answers. No intention turns toward you.\r\n"
        "Sael says, 'There. Something is present. Now earn the right to describe it. VIEW FROM DOORWAY and VIEW FROM WINDOW.'\r\n"
    )
    return True


async def _view_from_doorway(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG)
    await session.send(
        "\r\nFrom the doorway, the residue seems almost centered on the cushion. Its strongest point lies where Teren's torso would have rested, and the first impression is uncomfortably easy to turn into the outline of a seated person.\r\n"
        "Sael does not let the impression settle into certainty. 'One view is where stories become facts by accident. Take the window view too.'\r\n"
    )
    if MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG in _flags(session):
        session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "map_edges")
        await session.send("You now have both views. MARK EDGES.\r\n")
    return True


async def _view_from_window(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG)
    await session.send(
        "\r\nFrom the open window, the apparent 'seated figure' falls apart. One dense knot sits well beyond the cushion near the tea shelf, while a broad thin wash follows the stone wall instead of any anatomy. The trace has structure, but the structure is not shaped like a person.\r\n"
        "Sael says, 'Perspective did not make the first reading false. It made it incomplete.'\r\n"
    )
    if MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG in _flags(session):
        session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "map_edges")
        await session.send("You now have both views. MARK EDGES.\r\n")
    return True


async def _mark_edges(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "map_edges":
        return False
    flags = _flags(session)
    if not {
        MOON_ELF_NECROMANCER_DOORWAY_VIEW_FLAG,
        MOON_ELF_NECROMANCER_WINDOW_VIEW_FLAG,
    }.issubset(flags):
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_EDGES_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "let_fade")
    await session.send(
        "\r\nYou mark the points where the necromantic pressure falls below perception, then connect them only after checking each one twice. The result is irregular and limited. It reaches neither toward Teren's family nor toward his old journals. It does not point anywhere.\r\n"
        "Sael studies the boundary. 'That is useful knowledge. Now comes the harder lesson for people who enjoy having power: do nothing to it. WAIT FOR FADE.'\r\n"
    )
    return True


async def _wait_for_fade(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session) or quest.get("current_step") != "let_fade":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_NECROMANCER_FADED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_NECROMANCER_QUEST_KEY, "return_sael")
    await session.send(
        "\r\nYou leave the afterimage alone. You do not bind it, call into it, feed on it, preserve it, or force it to perform significance for you.\r\n"
        "Minute by minute the faint pressure thins. The densest knot near the tea shelf goes last, and then there is only cool mountain air crossing an ordinary empty room. No apparition departs. No final message arrives.\r\n"
        "Sael erases none of the chalk. 'Good. Absence is part of the observation too. TALK SAEL.'\r\n"
    )
    return True


async def _refuse_dramatization(session, normalized: str) -> bool:
    quest = _quest(session)
    if quest is None or not _in_niche(session):
        return False
    if quest.get("status") == "completed":
        return False
    if normalized not in {
        "talk teren",
        "talk to teren",
        "call teren",
        "call to teren",
        "speak to dead",
        "speak to teren",
        "bind residue",
        "bind afterimage",
        "siphon residue",
        "life tap residue",
        "raise teren",
        "raise corpse",
    }:
        return False
    await session.send(
        "\r\nSael stops you before the impulse becomes a method. 'No. You have not established a person, a voice, a corpse, or a threat that needs binding. Do not manufacture permission from atmosphere. Observe what is actually here.'\r\n"
    )
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


def install_moon_elf_necromancer_runtime(player_session_class, world_service=None) -> None:
    """Add a Moon Elf Necromancer extension after the shared Third Chair opening."""
    if getattr(player_session_class, "_moon_elf_necromancer_runtime_installed", False):
        return

    install_moon_elf_necromancer_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_necromancer_start(self):
            await self.send(
                "\r\nA Journal Gallery runner finds you with a note written in a precise hand.\r\n"
                "'Sael Orune asks for a Necromancer at the Afterimage Niche, north from the Journal Gallery. Nothing is wrong. That is apparently part of the lesson.'\r\n"
                "\r\nNew quest: The Shape Left Behind.\r\n"
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
        if normalized in {"talk sael", "talk necromancer sael", "talk sael orune", "talk necromancer sael orune"}:
            handled = await _talk_sael(self)
        elif normalized in {"examine cushion", "inspect cushion", "look cushion", "examine reading cushion", "inspect reading cushion", "examine niche"}:
            handled = await _inspect_cushion(self)
        elif normalized in {"trace residue", "trace afterimage", "sense residue", "read residue"}:
            handled = await _trace_residue(self)
        elif normalized in {"view from doorway", "study from doorway", "doorway view", "view doorway"}:
            handled = await _view_from_doorway(self)
        elif normalized in {"view from window", "study from window", "window view", "view window"}:
            handled = await _view_from_window(self)
        elif normalized in {"mark edges", "map edges", "mark boundary", "map boundary", "mark boundaries"}:
            handled = await _mark_edges(self)
        elif normalized in {"wait for fade", "watch fade", "let it fade", "let residue fade", "wait"}:
            handled = await _wait_for_fade(self)
        if not handled:
            handled = await _refuse_dramatization(self, normalized)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_necromancer_start(self):
            await self.send(
                "\r\nAs the Third Chair lesson settles, a Journal Gallery runner catches up with you.\r\n"
                "'Sael Orune asks for a Necromancer at the Afterimage Niche, north from the Journal Gallery. Nothing is wrong. That is apparently part of the lesson.'\r\n"
                "\r\nNew quest: The Shape Left Behind.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_necromancer_runtime_installed = True
