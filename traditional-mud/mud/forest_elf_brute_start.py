from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_home_and_omens import FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.forest_elf_stewardship import FOREST_ELF_RAINPOOL_TERRACE_KEY
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FOREST_ELF_STORMFALL_CROSSING_KEY = "forest_elf_stormfall_crossing"
FOREST_ELF_BRUTE_QUEST_KEY = "forest_elf_brute_weight_you_take"
FOREST_ELF_BRUTE_COMPLETE_FLAG = "forest_elf_brute_weight_you_take_complete"
FOREST_ELF_BRUTE_LOAD_READ_FLAG = "forest_elf_brute_load_read"
FOREST_ELF_BRUTE_BRACE_SET_FLAG = "forest_elf_brute_brace_set"
FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG = "forest_elf_brute_beam_lifted"
FOREST_ELF_BRUTE_FIRST_TAUNT_FLAG = "forest_elf_brute_first_taunt"
FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG = "forest_elf_brute_boar_guided_away"
FOREST_ELF_BRUTE_CROSSING_CHECKED_FLAG = "forest_elf_brute_crossing_checked"

ERYN_STONELEAF_KEY = "forest_elf_brute_eryn_stoneleaf"


FOREST_ELF_BRUTE_QUEST = QuestDefinition(
    key=FOREST_ELF_BRUTE_QUEST_KEY,
    name="The Weight You Take",
    style="structured",
    description=(
        "After the shared Forest Elf opening, a young Brute joins a path crew repairing a storm-shifted footbridge near Rainpool Terrace. "
        "The lesson is not about proving strength. It is about reading a load, using braces and other people's hands before muscle, taking the dangerous position when something goes wrong, and using Taunt to draw a frightened animal away from someone more exposed without turning the moment into an unnecessary fight."
    ),
    objective_steps=(
        ("meet_eryn", "From Rainpool Terrace, go WEST to Stormfall Crossing and TALK ERYN."),
        ("inspect_load", "EXAMINE BEAM before touching the storm-shifted bridge support."),
        ("set_brace", "SET BRACE so the load has somewhere safe to go before anyone lifts."),
        ("lift_beam", "LIFT BEAM WITH CREW instead of trying to prove you can move it alone."),
        ("draw_boar", "When the startled brambleback rushes into the worksite, TAUNT BOAR so its attention leaves the exposed apprentice."),
        ("guide_boar", "BACK TOWARD BRUSH while holding its attention and give the animal a clear way out."),
        ("check_crossing", "EXAMINE CROSSING after the danger passes and verify that the repair is actually stable."),
        ("return_eryn", "TALK ERYN after the crossing is safe and the crew is clear."),
        ("complete", "You learned that a Brute's strength is not measured by how much force can be used, but by knowing what weight to take and what harm to prevent."),
    ),
)


ERYN_STONELEAF = NpcDefinition(
    key=ERYN_STONELEAF_KEY,
    name="Warden Eryn Stoneleaf",
    short_description=(
        "a thick-built Forest Elf path warden with a coil of rope over one shoulder, a pry bar in one hand, and the calm posture of someone who has spent years standing where falling things might land"
    ),
    room_key=FOREST_ELF_STORMFALL_CROSSING_KEY,
    role="Forest Elf Brute mentor and path-crew warden",
    dialogue=(
        "Eryn rests the pry bar against her shoulder. 'Strength is useful. So are wedges, rope, six other people, and knowing when not to be underneath the thing you are lifting.'",
        "'A Brute is not the person who uses the most force. A Brute is the person who can take the dangerous position without making everyone else share it.'",
        "'If the job ends with nobody impressed and everybody walking home, that is still a good job.'",
    ),
)


FOREST_ELF_STORMFALL_CROSSING = RoomDefinition(
    key=FOREST_ELF_STORMFALL_CROSSING_KEY,
    name="Stormfall Crossing",
    region_key="great_elf_forest",
    description=(
        "A narrow footbridge spans a shallow rain-cut west of Rainpool Terrace beneath alder and willow. Last night's wind dropped a heavy limb across one side of the bridge and twisted a supporting beam out of its seat. A small path crew has already trimmed away the brush and laid out ropes, wedges, a timber brace, and two long pry bars. "
        "The worksite is orderly rather than heroic: tools are placed where hands can find them, the safe side of the load is marked with white cord, and a temporary brush gate keeps walkers away until the crossing is checked."
    ),
    exits={"east": FOREST_ELF_RAINPOOL_TERRACE_KEY},
    npc_keys=(ERYN_STONELEAF_KEY,),
    tags=("safe", "forest_elf_start", "brute", "path_warden", "community_work", "protection", "controlled_strength"),
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


def forest_elf_brute_augmentations() -> dict[str, RoomAugmentation]:
    beam_unmoved = ViewCondition(forbidden_flags=(FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG,))
    brace_set = ViewCondition(required_flags=(FOREST_ELF_BRUTE_BRACE_SET_FLAG,))
    beam_moved = ViewCondition(required_flags=(FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG,))
    boar_present = ViewCondition(
        required_flags=(FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG,),
        forbidden_flags=(FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG,),
    )
    boar_gone = ViewCondition(required_flags=(FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG,))

    return {
        FOREST_ELF_STORMFALL_CROSSING_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "east",
                    FOREST_ELF_RAINPOOL_TERRACE_KEY,
                    "Rainpool Terrace",
                    travel_text="You leave the path crew behind and follow the damp footpath east to Rainpool Terrace.",
                ),
            ),
            features=(
                _feature(
                    "stormfall_shifted_beam",
                    "Storm-Shifted Beam",
                    "a heavy bridge beam twisted partly out of its stone seat beneath the trimmed storm limb",
                    "The beam is carrying more than its own weight. One end is pinned by the fallen limb while the other has rolled against the bridge edge. Lifting from the obvious side would free it suddenly and throw the load toward whoever is standing downhill. The crew has enough strength. What they need first is a controlled place for the weight to settle.",
                    ("beam", "bridge beam", "shifted beam", "storm-shifted beam", "load", "bridge support"),
                    condition=beam_unmoved,
                ),
                _feature(
                    "stormfall_timber_brace",
                    "Timber Brace",
                    "a thick forked timber, wedges, rope, and a pry bar laid beside the safe side of the bridge",
                    "The brace is not a substitute for strength. It is what makes strength predictable. Set beneath the lifted end, it can catch the beam if hands slip and keep the load from rolling downhill into the crew.",
                    ("brace", "timber brace", "wedges", "rope", "pry bar", "tools"),
                ),
                _feature(
                    "stormfall_set_brace",
                    "Set Timber Brace",
                    "the forked timber wedged firmly beneath the beam with a safety rope taking the first slack",
                    "The brace now gives the shifted beam a controlled resting point. If the crew loses the lift, the load will drop only a handspan instead of rolling through the worksite.",
                    ("brace", "set brace", "timber brace", "safety brace", "wedges"),
                    condition=brace_set,
                ),
                _feature(
                    "stormfall_reseated_beam",
                    "Reseated Bridge Beam",
                    "the heavy support sitting squarely back in its stone seat after the crew's measured lift",
                    "The support is back where it belongs. The brace remains in place while the crew checks the bridge, because finishing the dramatic part of a lift is not the same thing as proving the structure is safe.",
                    ("beam", "reseated beam", "bridge beam", "support", "bridge support"),
                    condition=beam_moved,
                ),
                _feature(
                    "stormfall_brambleback",
                    "Startled Brambleback Boar",
                    "a mud-dark brambleback boar stamping at the edge of the worksite, frightened by the moving timber and blocked from its usual brush route",
                    "The boar is frightened, not hunting. Its ears are pinned and its attention keeps snapping between the crew, the temporary gate, and a young apprentice caught on the wrong side of the tool line. Hitting it would create a fight the worksite does not need. Drawing its attention toward the open brush lane would protect the apprentice and give the animal somewhere else to go.",
                    ("boar", "brambleback", "brambleback boar", "animal", "startled boar"),
                    condition=boar_present,
                ),
                _feature(
                    "stormfall_brush_lane",
                    "Open Brush Lane",
                    "a cleared lane beside the bridge leading away from the crew into alder cover",
                    "The lane is deliberately open and wide enough for the boar to leave without squeezing past anyone. Protection sometimes means giving danger a direction that is not through another person.",
                    ("brush", "brush lane", "lane", "escape route", "alder cover"),
                ),
                _feature(
                    "stormfall_quiet_crossing",
                    "Quiet Crossing",
                    "the repaired footbridge and empty brush lane after the animal has withdrawn into the trees",
                    "The beam is seated, the deck no longer twists under weight, and the safety brace still carries no unexpected pressure. A few churned hoofprints angle away into the brush. The crossing looks ordinary again, which is the point of the work.",
                    ("crossing", "bridge", "footbridge", "repaired bridge", "quiet crossing"),
                    condition=boar_gone,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "stormfall_worksite_rhythm",
                    "The crew speaks in short practical phrases: hand here, rope clear, wait, again. Nobody is trying to make hard work look effortless.",
                    priority=45,
                ),
                DescriptionLayer(
                    "stormfall_load_controlled",
                    "With the brace set, the worksite feels less tense. The weight has not changed; the consequences of a mistake have.",
                    priority=60,
                    condition=brace_set,
                ),
                DescriptionLayer(
                    "stormfall_boar_departed",
                    "The brush has gone still again. The apprentice is back behind the cord line, and the crew has returned to checking the bridge instead of congratulating anyone for not starting a fight.",
                    priority=75,
                    condition=boar_gone,
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


def _patch_rainpool() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[FOREST_ELF_RAINPOOL_TERRACE_KEY]
    exits = dict(original.exits)
    exits["west"] = FOREST_ELF_STORMFALL_CROSSING_KEY
    description = original.description
    if "Stormfall Crossing" not in description:
        description += (
            " A cord-marked path runs west to Stormfall Crossing, where path wardens are repairing a footbridge shifted by recent wind."
        )
    return replace(original, exits=exits, description=description)


def install_forest_elf_brute_content(world_service=None) -> None:
    if FOREST_ELF_BRUTE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_BRUTE_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_BRUTE_QUEST.key] = FOREST_ELF_BRUTE_QUEST

    _replace_room(FOREST_ELF_STORMFALL_CROSSING)
    _replace_npc(ERYN_STONELEAF)
    rainpool = _patch_rainpool()
    _replace_room(rainpool)

    if world_service is None:
        return

    world_service.legacy_rooms[FOREST_ELF_STORMFALL_CROSSING_KEY] = FOREST_ELF_STORMFALL_CROSSING
    world_service.legacy_rooms[FOREST_ELF_RAINPOOL_TERRACE_KEY] = rainpool
    world_service.augmentations.update(forest_elf_brute_augmentations())

    base = world_service.augmentations.get(FOREST_ELF_RAINPOOL_TERRACE_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "west"]
    exits.append(
        ExitDefinition(
            "west",
            FOREST_ELF_STORMFALL_CROSSING_KEY,
            "Stormfall Crossing",
            travel_text="You follow the cord-marked path west from the rain pools to the bridge repair at Stormfall Crossing.",
        )
    )
    world_service.augmentations[FOREST_ELF_RAINPOOL_TERRACE_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(FOREST_ELF_STORMFALL_CROSSING_KEY, None)
        cache.pop(FOREST_ELF_RAINPOOL_TERRACE_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "forest_elf" and character.character_class == "brute")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, FOREST_ELF_BRUTE_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_brute_start(session) -> bool:
    if not _qualifies(session):
        return False
    if FOREST_ELF_OPENING_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "meet_eryn")
    return True


def _at_crossing(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == FOREST_ELF_STORMFALL_CROSSING_KEY)


async def _talk_eryn(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session):
        return False
    step = quest.get("current_step")

    if step == "meet_eryn":
        session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "inspect_load")
        await session.send(
            "\r\nEryn passes you a pair of work gloves instead of a weapon.\r\n"
            "'Wind rolled that bridge support out of its seat. We have enough backs here to move it. What we do not have is permission to drop it on anybody.'\r\n"
            "She points to the twisted support. 'Before you touch it, EXAMINE BEAM.'\r\n"
        )
        return True

    if step == "return_eryn":
        session.database.complete_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY)
        session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_COMPLETE_FLAG)
        await session.send(
            "\r\nEryn walks the bridge once, then again with two other wardens, before she finally pulls the white cord aside.\r\n"
            "'You read the load before lifting it. You used a brace before your back. You took the animal's attention when somebody else was exposed, and then you gave it a way to leave.'\r\n"
            "She coils the safety rope. 'That is the part of being a Brute I care about. Anybody can make force look dramatic. Your job is to make danger choose you when it has to choose someone, then keep the danger from becoming bigger than it already is.'\r\n"
            "Her mouth quirks. 'If nobody writes a song about this bridge staying upright, I think we can survive the disappointment.'\r\n"
            "\r\nQuest complete: The Weight You Take.\r\n"
        )
        return True

    objective = FOREST_ELF_BRUTE_QUEST.objective_for_step(step)
    await session.send("\r\nEryn nods toward the unfinished work. 'Strength is not an excuse to skip the safe part.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_beam(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "inspect_load":
        return False
    if FOREST_ELF_BRUTE_LOAD_READ_FLAG not in _flags(session):
        session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_LOAD_READ_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "set_brace")
    await session.send(
        "\r\nThe beam is heavy, but weight is not the real problem. The fallen limb has pinned one end while the other is rolled toward the downhill edge. If everyone simply heaves upward, the freed end could swing through the crew.\r\n"
        "Eryn taps the forked timber beside you. 'Good. Strong enough to lift is not the same thing as ready to lift. SET BRACE.'\r\n"
    )
    return True


async def _set_brace(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "set_brace":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_BRACE_SET_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "lift_beam")
    await session.send(
        "\r\nYou and a warden wedge the forked timber beneath the beam and take the first slack out of the safety rope. If the lift fails, the support now has somewhere safe to settle instead of somewhere dangerous to fall.\r\n"
        "Eryn sets one pry bar under the pinned end. 'Now use the crew. LIFT BEAM WITH CREW.'\r\n"
    )
    return True


async def _lift_beam(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "lift_beam":
        return False
    if FOREST_ELF_BRUTE_BRACE_SET_FLAG not in _flags(session):
        await session.send("\r\nThe load still has no safe catch point. Set the brace before anybody lifts.\r\n")
        return True
    session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_BEAM_LIFTED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "draw_boar")
    await session.send(
        "\r\nYou take the lower pry bar while two wardens take the upper. On Eryn's count, the crew lifts together. Your strength matters, but so do their hands, the lever, the rope, and the brace waiting beneath the load.\r\n"
        "The beam rolls back into its stone seat with a deep wooden knock. Nobody's fingers are under it. Nobody has to jump clear.\r\n"
        "Then the cut brush behind the apprentice explodes outward. A brambleback boar, startled from cover by the shifting timber, stamps into the worksite with the young warden between it and the open lane.\r\n"
        "Eryn's voice goes hard and immediate. 'Do not hit it. Take its attention. TAUNT BOAR.'\r\n"
    )
    return True


async def _taunt_boar(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "draw_boar":
        return False
    flags = _flags(session)
    if FOREST_ELF_BRUTE_FIRST_TAUNT_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "taunt", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_FIRST_TAUNT_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "guide_boar")
    await session.send(
        "\r\nYou step into the boar's line, strike the ground with your heel, and turn your whole posture into a challenge it cannot ignore. Taunt is not clever insult here. It is the practiced art of making yourself the obvious source of threat.\r\n"
        "The brambleback's head snaps toward you. The apprentice slips behind the white cord while the animal fixes on the larger problem you offered it.\r\n"
        "Eryn points toward the open alder lane. 'Good. Now do not win a fight we never needed. BACK TOWARD BRUSH.'\r\n"
    )
    return True


async def _guide_boar(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "guide_boar":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_BOAR_GUIDED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "check_crossing")
    await session.send(
        "\r\nYou give ground one measured step at a time, keeping the boar's attention without cornering it. When you reach the open brush lane, you turn your shoulders just enough to stop blocking the way.\r\n"
        "The brambleback hesitates, decides escape is better than conflict, and crashes into the alder cover. You let it go.\r\n"
        "Eryn waits until the brush is still. 'Protection is not the same thing as winning. Now finish the actual job. EXAMINE CROSSING.'\r\n"
    )
    return True


async def _check_crossing(session) -> bool:
    quest = _quest(session)
    if quest is None or not _at_crossing(session) or quest.get("current_step") != "check_crossing":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_BRUTE_CROSSING_CHECKED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_BRUTE_QUEST_KEY, "return_eryn")
    await session.send(
        "\r\nYou check the seated beam, the deck above it, the safety rope, and the brace underneath. The bridge takes weight without twisting. No fastener has pulled loose, and the support is carrying the load where it should.\r\n"
        "The dramatic part was over when the boar left. The useful part ends when you know the crossing is safe. TALK ERYN.\r\n"
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


def install_forest_elf_brute_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Forest Elf Brute extension after the shared opening."""
    if getattr(player_session_class, "_forest_elf_brute_runtime_installed", False):
        return

    install_forest_elf_brute_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_brute_start(self):
            await self.send(
                "\r\nWhen the Circle returns to ordinary work, Sela catches you near the rain pools and hooks a coil of safety rope over your shoulder.\r\n"
                "'Stormfall Crossing shifted last night. Eryn has enough people to move the beam, but she asked for someone trained to stand where the dangerous part goes.'\r\n"
                "'Path west from Rainpool Terrace. Bring the rope. She already has plenty of heroics.'\r\n"
                "\r\nNew quest: The Weight You Take.\r\n"
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
        normalized = " ".join(command.strip().lower().split())

        handled = False
        if normalized in {"talk eryn", "talk warden eryn", "talk eryn stoneleaf", "talk warden eryn stoneleaf"}:
            handled = await _talk_eryn(self)
        elif normalized in {"examine beam", "inspect beam", "look beam", "examine load", "inspect load", "examine bridge beam"}:
            handled = await _inspect_beam(self)
        elif normalized in {"set brace", "place brace", "set timber brace", "brace beam", "set safety brace"}:
            handled = await _set_brace(self)
        elif normalized in {"lift beam with crew", "lift beam", "lift with crew", "raise beam with crew", "move beam with crew"}:
            handled = await _lift_beam(self)
        elif normalized in {"taunt boar", "taunt brambleback", "use taunt on boar", "use taunt boar", "challenge boar", "draw boar"}:
            handled = await _taunt_boar(self)
        elif normalized in {"back toward brush", "back to brush", "give ground", "guide boar", "draw boar to brush", "lead boar to brush"}:
            handled = await _guide_boar(self)
        elif normalized in {"examine crossing", "inspect crossing", "check crossing", "examine bridge", "inspect bridge", "check bridge"}:
            handled = await _check_crossing(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_brute_start(self):
            await self.send(
                "\r\nWith the shared Forest Elf opening behind you, Sela passes you a coil of safety rope from the rain crew.\r\n"
                "'Eryn Stoneleaf needs another Brute at Stormfall Crossing. West from Rainpool Terrace. It is bridge work, not a wrestling contest.'\r\n"
                "\r\nNew quest: The Weight You Take.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_brute_runtime_installed = True
