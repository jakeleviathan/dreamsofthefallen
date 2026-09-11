from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_city import MOON_ELF_REGION_KEY, MOON_ELF_SKYCOURT_KEY
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_THIRD_CHAIR_ROOM_KEY = "moon_elf_third_chair_chamber"
MOON_ELF_FIRST_OVERLOOK_KEY = "moon_elf_first_overlook"
MOON_ELF_ORCHARD_OVERLOOK_KEY = "moon_elf_orchard_overlook"
MOON_ELF_THIRD_CHAIR_ROOM_KEYS = (
    MOON_ELF_THIRD_CHAIR_ROOM_KEY,
    MOON_ELF_FIRST_OVERLOOK_KEY,
    MOON_ELF_ORCHARD_OVERLOOK_KEY,
)

MOON_ELF_THIRD_CHAIR_QUEST_KEY = "moon_elf_third_chair"
MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG = "moon_elf_third_chair_complete"
MOON_ELF_HEARD_SERA_FLAG = "moon_elf_third_chair_heard_sera"
MOON_ELF_HEARD_TALIN_FLAG = "moon_elf_third_chair_heard_talin"
MOON_ELF_CHOICE_REDRAW_FLAG = "moon_elf_third_chair_redraw_path"
MOON_ELF_CHOICE_KEEP_FLAG = "moon_elf_third_chair_keep_old_path"
MOON_ELF_CHOICE_WIND_FLAG = "moon_elf_third_chair_study_wind"
MOON_ELF_CHOICE_NEIGHBORS_FLAG = "moon_elf_third_chair_ask_neighbors"

ILYRA_SEN_KEY = "moon_elf_witness_ilyra_sen"
SERA_VALEGLASS_KEY = "moon_elf_sera_valeglass"
TALIN_ORROW_KEY = "moon_elf_talin_orrow"


MOON_ELF_THIRD_CHAIR = QuestDefinition(
    key=MOON_ELF_THIRD_CHAIR_QUEST_KEY,
    name="The Third Chair",
    style="structured",
    description=(
        "Witness Ilyra Sen has asked you to sit in on an ordinary civic disagreement about a safer footpath and an old orchard. "
        "The lesson is not to discover which person is secretly wrong, but to learn what High Horizon means when it asks someone to change where they stand before deciding what they see."
    ),
    objective_steps=(
        ("meet_ilyra", "From the Skycourt, go UP to the Third Chair Chamber and TALK ILYRA."),
        ("sit_third_chair", "SIT THIRD CHAIR and take the place reserved for what neither side can yet see."),
        ("hear_counterviews", "TALK SERA and TALK TALIN. Each must explain the other person's position before the discussion continues."),
        ("inspect_first_view", "Go NORTH to the First Overlook and EXAMINE PATH."),
        ("inspect_second_view", "Go DOWN to the Orchard Overlook and EXAMINE ORCHARD."),
        ("choose_next_step", "Choose what should happen next: REDRAW THE PATH, KEEP THE OLD PATH, STUDY THE WIND, or ASK THE NEIGHBORS."),
        ("complete", "You learned that clarity can reveal another question instead of demanding a fast answer."),
    ),
)


ILYRA_SEN = NpcDefinition(
    key=ILYRA_SEN_KEY,
    name="Witness Ilyra Sen",
    short_description="a Moon Elf Witness seated beside three deliberately equal chairs and an untouched pot of tea",
    room_key=MOON_ELF_THIRD_CHAIR_ROOM_KEY,
    role="Witness mediator and Moon Elf starter mentor",
    dialogue=(
        "Ilyra rests one hand on the back of the empty chair. 'There are three chairs because a disagreement usually contains at least three things: what one person sees, what the other sees, and what neither can see while they are fighting.'",
        "'A Witness does not make disagreement disappear. We try to make sure everyone is finally disagreeing about the same thing.'",
    ),
)

SERA_VALEGLASS = NpcDefinition(
    key=SERA_VALEGLASS_KEY,
    name="Sera Valeglass",
    short_description="an older orchard keeper with weathered hands, a folded property map, and very little patience for being reduced to a line on it",
    room_key=MOON_ELF_THIRD_CHAIR_ROOM_KEY,
    role="orchard keeper in the Third Chair mediation",
    dialogue=(
        "Sera folds her arms. 'The orchard was here before that surveyor learned to hold a measuring chain.'",
        "After a long pause she adds, more carefully, 'He believes the old path is dangerous in winter. He thinks people will be hurt because I prefer my trees undisturbed.'",
    ),
)

TALIN_ORROW = NpcDefinition(
    key=TALIN_ORROW_KEY,
    name="Talin Orrow",
    short_description="a young civic surveyor carrying rolled route plans annotated so heavily that almost no blank paper remains",
    room_key=MOON_ELF_THIRD_CHAIR_ROOM_KEY,
    role="surveyor in the Third Chair mediation",
    dialogue=(
        "Talin taps the route plan. 'The shelf path ices every winter. A straighter connection is not an insult to anyone's grandparents.'",
        "He looks toward Sera before trying again. 'She thinks I looked at the ridge and saw distances instead of a life.'",
    ),
)

THIRD_CHAIR_NPCS = (ILYRA_SEN, SERA_VALEGLASS, TALIN_ORROW)


THIRD_CHAIR_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=MOON_ELF_THIRD_CHAIR_ROOM_KEY,
        name="Third Chair Chamber",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A small mediation room is built directly into the ridge above the Skycourt. Three plain chairs surround a low stone table; none is larger, higher, or more ornate than the others. "
            "One wall opens completely onto the mountain night behind a waist-high rail, while the remaining walls hold route maps, blank writing boards, and hooks for coats. North, a narrow public stair climbs toward an overlook used when arguments about maps need to become arguments about actual ground."
        ),
        exits={"down": MOON_ELF_SKYCOURT_KEY, "north": MOON_ELF_FIRST_OVERLOOK_KEY},
        npc_keys=(ILYRA_SEN_KEY, SERA_VALEGLASS_KEY, TALIN_ORROW_KEY),
        tags=("safe", "moon_elf_start", "witness", "mediation", "civic_life"),
    ),
    RoomDefinition(
        key=MOON_ELF_FIRST_OVERLOOK_KEY,
        name="First Overlook",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A paved viewing shelf projects from the upper ridge. From here the proposed footpath seems almost embarrassingly sensible: a clean, gentle line between two neighborhoods that avoids the narrow icy shelf used now. "
            "Survey stakes mark the possible route through the edge of Sera's orchard below. A second stair drops toward a lower terrace where the same ground can be seen from beneath rather than above."
        ),
        exits={"south": MOON_ELF_THIRD_CHAIR_ROOM_KEY, "down": MOON_ELF_ORCHARD_OVERLOOK_KEY},
        tags=("safe", "moon_elf_start", "overlook", "perspective", "survey"),
    ),
    RoomDefinition(
        key=MOON_ELF_ORCHARD_OVERLOOK_KEY,
        name="Orchard Overlook",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "The lower terrace sits beside the old orchard instead of above it. Here the trees stop looking like dots on a plan. Their trunks and stone walls break the prevailing wind before it reaches several homes tucked farther down the slope. "
            "The old footpath is also visible from below, pinched along a shaded rock shelf where meltwater freezes hard in winter. Neither fact erases the other. The stair back to the first overlook climbs up behind you."
        ),
        exits={"up": MOON_ELF_FIRST_OVERLOOK_KEY},
        tags=("safe", "moon_elf_start", "overlook", "orchard", "perspective"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...]) -> FeatureDefinition:
    return FeatureDefinition(key=key, name=name, aliases=aliases, summary=summary, examine_text=examine)


def third_chair_augmentations() -> dict[str, RoomAugmentation]:
    return {
        MOON_ELF_THIRD_CHAIR_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition("down", MOON_ELF_SKYCOURT_KEY, "The Skycourt", travel_text="You descend from the mediation chamber into the open civic court."),
                ExitDefinition("north", MOON_ELF_FIRST_OVERLOOK_KEY, "First Overlook", travel_text="You follow Ilyra's narrow stair north toward the upper view of the disputed route."),
            ),
            features=(
                _feature("third_chair", "Third Chair", "the deliberately ordinary empty chair reserved for the unseen part of a disagreement", "The chair carries no rank or mystical symbol. Its purpose is procedural: someone sits here to remember that two sincere viewpoints can still leave part of the situation unseen.", ("chair", "third chair", "empty chair")),
                _feature("mediation_table", "Low Stone Table", "a low table shared equally by all three chairs", "The table holds tea, the orchard map, Talin's survey notes, and a blank slate. No object is positioned to make one speaker look like the authority in the room.", ("table", "stone table", "map")),
            ),
            description_layers=(DescriptionLayer("third_chair_evening", "The open wall keeps the distant lights of High Horizon in view, making the room feel private without pretending the city outside has disappeared."),),
        ),
        MOON_ELF_FIRST_OVERLOOK_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition("south", MOON_ELF_THIRD_CHAIR_ROOM_KEY, "Third Chair Chamber", travel_text="You return south to the chamber where the argument began."),
                ExitDefinition("down", MOON_ELF_ORCHARD_OVERLOOK_KEY, "Orchard Overlook", travel_text="You descend the switchback stair until the orchard and lower homes rise into the same field of view."),
            ),
            features=(
                _feature("proposed_path", "Proposed Path", "the survey line that looks clean and safe from the upper ridge", "From this angle Talin's case is strong. The new route is shorter, broader, and avoids a shaded shelf where the existing path becomes dangerously icy in winter.", ("path", "proposed path", "route", "survey route")),
                _feature("survey_stakes", "Survey Stakes", "small pale stakes tracing the proposed route through the orchard edge", "The stakes are careful rather than destructive. They show exactly which trees might be affected, but from this height the orchard still reads mostly as geometry.", ("stakes", "survey stakes", "markers")),
            ),
            description_layers=(DescriptionLayer("first_overlook_lesson", "From above, efficiency has the visual force of obviousness. The straighter line almost seems to argue for itself."),),
        ),
        MOON_ELF_ORCHARD_OVERLOOK_KEY: RoomAugmentation(
            exit_overrides=(ExitDefinition("up", MOON_ELF_FIRST_OVERLOOK_KEY, "First Overlook", travel_text="You climb back toward the upper survey shelf."),),
            features=(
                _feature("old_orchard", "Old Orchard", "rows of old fruit trees and low stone walls sheltering the slope", "Seen from beside it, the orchard is also infrastructure. The trees and walls break the prevailing winter wind before it reaches the lower houses; removing too broad a strip could expose them.", ("orchard", "old orchard", "trees", "windbreak")),
                _feature("old_footpath", "Old Footpath", "the existing route squeezed against a cold shaded rock shelf", "Sera's objection does not make Talin's safety concern imaginary. From below, the old path's winter problem is obvious too: shade, meltwater, and a narrow shelf combine into a bad crossing.", ("old path", "footpath", "old footpath", "icy shelf")),
            ),
            description_layers=(DescriptionLayer("orchard_overlook_lesson", "The lower view does not reverse the first one. It adds something the first view made easy to ignore."),),
        ),
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


def _patch_skycourt() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_SKYCOURT_KEY]
    exits = dict(original.exits)
    exits["up"] = MOON_ELF_THIRD_CHAIR_ROOM_KEY
    description = original.description
    if "Third Chair" not in description:
        description += " A modest stair marked THIRD CHAIR CHAMBER climbs to a civic mediation room above the court."
    return replace(original, exits=exits, description=description)


def install_third_chair_content(world_service=None) -> None:
    if MOON_ELF_THIRD_CHAIR.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_THIRD_CHAIR,)
    quests.QUESTS_BY_KEY[MOON_ELF_THIRD_CHAIR.key] = MOON_ELF_THIRD_CHAIR

    for room in THIRD_CHAIR_ROOMS:
        _replace_room(room)
    for npc in THIRD_CHAIR_NPCS:
        _replace_npc(npc)
    skycourt = _patch_skycourt()
    _replace_room(skycourt)

    if world_service is None:
        return
    for room in THIRD_CHAIR_ROOMS:
        world_service.legacy_rooms[room.key] = room
    world_service.legacy_rooms[MOON_ELF_SKYCOURT_KEY] = skycourt
    world_service.augmentations.update(third_chair_augmentations())

    base = world_service.augmentations.get(MOON_ELF_SKYCOURT_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "up"]
    exits.append(ExitDefinition("up", MOON_ELF_THIRD_CHAIR_ROOM_KEY, "Third Chair Chamber", travel_text="You climb the modest civic stair to the mediation chamber above the Skycourt."))
    world_service.augmentations[MOON_ELF_SKYCOURT_KEY] = replace(base, exit_overrides=tuple(exits))
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room_key in (*MOON_ELF_THIRD_CHAIR_ROOM_KEYS, MOON_ELF_SKYCOURT_KEY):
            cache.pop(room_key, None)


def _active_quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY)


def _start_if_needed(session) -> bool:
    if session.character is None or session.character.race != "moon_elf":
        return False
    quest = _active_quest(session)
    if quest is not None:
        return False
    session.database.start_quest(session.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "meet_ilyra")
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


def _in_room(session, room_key: str) -> bool:
    return session.character is not None and session.character.current_room == room_key


def _choice_flag(normalized: str) -> str | None:
    return {
        "redraw the path": MOON_ELF_CHOICE_REDRAW_FLAG,
        "redraw path": MOON_ELF_CHOICE_REDRAW_FLAG,
        "keep the old path": MOON_ELF_CHOICE_KEEP_FLAG,
        "keep old path": MOON_ELF_CHOICE_KEEP_FLAG,
        "study the wind": MOON_ELF_CHOICE_WIND_FLAG,
        "study wind": MOON_ELF_CHOICE_WIND_FLAG,
        "ask the neighbors": MOON_ELF_CHOICE_NEIGHBORS_FLAG,
        "ask neighbors": MOON_ELF_CHOICE_NEIGHBORS_FLAG,
    }.get(normalized)


async def _complete_choice(session, normalized: str) -> None:
    flag = _choice_flag(normalized)
    if flag is None:
        return
    session.database.grant_flag(session.character.id, flag)
    session.database.grant_flag(session.character.id, MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG)
    session.database.complete_quest(session.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY)

    if flag in {MOON_ELF_CHOICE_WIND_FLAG, MOON_ELF_CHOICE_NEIGHBORS_FLAG}:
        await session.send("\r\nIlyra nods. 'Good. Clarity is not the same thing as reaching a conclusion quickly.'\r\n")
    elif flag == MOON_ELF_CHOICE_REDRAW_FLAG:
        await session.send("\r\nIlyra considers the slope. 'Then redraw it with both facts on the page. A better conclusion is allowed to look less elegant than the first.'\r\n")
    else:
        await session.send("\r\nIlyra studies the old shelf. 'Then keeping it must include the danger you now understand. A clear choice does not become costless merely because it is clear.'\r\n")

    await session.send(
        "Talin lets out a short laugh. 'So we spent an hour discovering that we need another meeting.'\r\n"
        "Sera glances at him. 'That is still an improvement over the meeting we were having.'\r\n"
        "Ilyra pours the tea at last. 'Most miracles are considerably less impressive than advertised.'\r\n"
        "\r\nQuest complete: The Third Chair.\r\n"
    )


def install_third_chair_runtime(player_session_class, world_service) -> None:
    install_third_chair_content(world_service)
    if getattr(player_session_class, "_moon_elf_third_chair_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _start_if_needed(self):
            await self.send(
                "\r\nNew quest: The Third Chair.\r\n"
                "An ordinary disagreement has reached Witness Ilyra Sen: a safer public path may cut through Sera Valeglass's old orchard. "
                "From High Horizon Plaza, go NORTH to the Skycourt, then UP to the Third Chair Chamber and TALK ILYRA.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "moon_elf":
            await previous_playing_prompt(self)
            return

        _start_if_needed(self)
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()
        quest = _active_quest(self)
        step = quest.get("current_step") if quest and quest.get("status") == "active" else None

        if normalized in {"talk ilyra", "talk to ilyra", "talk witness", "talk to witness"}:
            if not _in_room(self, MOON_ELF_THIRD_CHAIR_ROOM_KEY):
                await self.send("Witness Ilyra Sen is not here.\r\n")
                return
            await self.send(
                "\r\nIlyra gestures to the empty seat. 'There are three chairs because a disagreement usually contains at least three things: what one person sees, what the other sees, and what neither of them can see while they are fighting.'\r\n"
                "'Sit. Not because you are the judge. Because for the next few minutes your job is to notice what the argument has left out.'\r\n"
            )
            if step == "meet_ilyra":
                self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "sit_third_chair")
                await self.send("Quest updated: The Third Chair. SIT THIRD CHAIR.\r\n")
            return

        if normalized in {"sit third chair", "sit in third chair", "sit chair", "sit in chair"}:
            if not _in_room(self, MOON_ELF_THIRD_CHAIR_ROOM_KEY):
                await self.send("The Third Chair is not here.\r\n")
                return
            if step != "sit_third_chair":
                await self.send("You sit in the plain third chair. It is deliberately no more important than the other two.\r\n")
                return
            self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "hear_counterviews")
            await self.send(
                "You take the third chair. Ilyra asks Sera to explain Talin's position, and Talin to explain Sera's. Neither looks pleased about it.\r\n"
                "Quest updated: TALK SERA and TALK TALIN.\r\n"
            )
            return

        if normalized in {"talk sera", "talk to sera", "talk valeglass", "talk to valeglass"}:
            if not _in_room(self, MOON_ELF_THIRD_CHAIR_ROOM_KEY):
                await self.send("Sera Valeglass is not here.\r\n")
                return
            await self.send("\r\nSera takes a long breath. 'He believes the old path is dangerous in winter. He thinks people will be hurt because I prefer my trees undisturbed.'\r\n")
            if step == "hear_counterviews":
                self.database.grant_flag(self.character.id, MOON_ELF_HEARD_SERA_FLAG)
                flags = self.database.list_flags(self.character.id)
                if MOON_ELF_HEARD_TALIN_FLAG in flags:
                    self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "inspect_first_view")
                    await self.send("Ilyra nods. 'Good. Now we are finally discussing the same problem.' Go NORTH and EXAMINE PATH.\r\n")
                else:
                    await self.send("Ilyra turns to Talin. 'Now you.' TALK TALIN.\r\n")
            return

        if normalized in {"talk talin", "talk to talin", "talk orrow", "talk to orrow"}:
            if not _in_room(self, MOON_ELF_THIRD_CHAIR_ROOM_KEY):
                await self.send("Talin Orrow is not here.\r\n")
                return
            await self.send("\r\nTalin looks at the orchard keeper rather than his map. 'She thinks I looked at the ridge and saw distances instead of a life.'\r\n")
            if step == "hear_counterviews":
                self.database.grant_flag(self.character.id, MOON_ELF_HEARD_TALIN_FLAG)
                flags = self.database.list_flags(self.character.id)
                if MOON_ELF_HEARD_SERA_FLAG in flags:
                    self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "inspect_first_view")
                    await self.send("Ilyra nods. 'Good. Now we are finally discussing the same problem.' Go NORTH and EXAMINE PATH.\r\n")
                else:
                    await self.send("Ilyra turns to Sera. 'Your turn.' TALK SERA.\r\n")
            return

        if normalized in {"examine path", "look path", "examine proposed path", "look proposed path", "examine route"} and _in_room(self, MOON_ELF_FIRST_OVERLOOK_KEY):
            await self.send("\r\nFrom the upper ridge, Talin's route looks plainly better: shorter, broader, and safely away from the old shaded shelf where winter ice gathers. From here, the orchard edge looks like a small price for a sensible public path.\r\n")
            if step == "inspect_first_view":
                self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "inspect_second_view")
                await self.send("Ilyra says only, 'Now change where you are standing.' Go DOWN and EXAMINE ORCHARD.\r\n")
            return

        if normalized in {"examine orchard", "look orchard", "examine trees", "look trees", "examine view", "look view"} and _in_room(self, MOON_ELF_ORCHARD_OVERLOOK_KEY):
            await self.send(
                "\r\nFrom the lower terrace, the orchard becomes more than property. Its old trees and stone walls break the prevailing winter wind before it reaches several homes below. "
                "But the old path is visible too, pinched against a shaded shelf where meltwater freezes. Both Sera and Talin were right about something, and neither had the whole picture.\r\n"
            )
            if step == "inspect_second_view":
                self.database.advance_quest(self.character.id, MOON_ELF_THIRD_CHAIR_QUEST_KEY, "choose_next_step")
                await self.send("What should happen next? REDRAW THE PATH, KEEP THE OLD PATH, STUDY THE WIND, or ASK THE NEIGHBORS.\r\n")
            return

        if _choice_flag(normalized) is not None:
            if not _in_room(self, MOON_ELF_ORCHARD_OVERLOOK_KEY) or step != "choose_next_step":
                await self.send("You are not at the point in the Third Chair discussion where that decision can be made.\r\n")
                return
            await _complete_choice(self, normalized)
            return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if normalized in {"help", "?"}:
            await self.send("Moon Elf starter: THE THIRD CHAIR uses TALK, SIT THIRD CHAIR, EXAMINE PATH, EXAMINE ORCHARD, and a final four-way decision.\r\n")

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_third_chair_installed = True
