from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_beliefs import MOON_ELF_WITNESS_PATH_KEY
from mud.moon_elf_city import MOON_ELF_MOONMIRROR_WALK_KEY, MOON_ELF_REGION_KEY
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_WITNESS_INFIRMARY_KEY = "moon_elf_open_sky_infirmary"
MOON_ELF_WITNESS_QUEST_KEY = "moon_elf_witness_wound_and_whole"
MOON_ELF_WITNESS_COMPLETE_FLAG = "moon_elf_witness_wound_and_whole_complete"
MOON_ELF_WITNESS_FIRST_MENDING_FLAG = "moon_elf_witness_first_mending"
MOON_ELF_WITNESS_RESULT_CHECKED_FLAG = "moon_elf_witness_result_checked"

MAERA_VENN_KEY = "moon_elf_witness_maera_venn"
RALEN_ORR_KEY = "moon_elf_runner_ralen_orr"


MOON_ELF_WITNESS_QUEST = QuestDefinition(
    key=MOON_ELF_WITNESS_QUEST_KEY,
    name="The Wound and the Whole",
    style="structured",
    description=(
        "After the Third Chair, a new Moon Elf Witness is sent to High Horizon's Open-Sky Infirmary. "
        "The lesson is deliberately practical: listen to an injured person, observe the injury without reducing the person to it, "
        "use Clearview Mending, and then check what actually changed instead of assuming that magic settled every question."
    ),
    objective_steps=(
        ("meet_maera", "From Moonmirror Walk, go EAST into the Open-Sky Infirmary and TALK MAERA."),
        ("hear_ralen", "TALK RALEN before deciding what his injury needs."),
        ("inspect_injury", "EXAMINE ANKLE and compare the injury with what Ralen says he can still feel and do."),
        ("mend_injury", "Use your first Witness healing in context with MEND RALEN."),
        ("check_result", "After the mending, EXAMINE GAIT instead of assuming the result."),
        ("return_maera", "TALK MAERA and report what changed and what did not."),
        ("complete", "You practiced Clearview Mending as care rather than proof, spectacle, or doctrine."),
    ),
)


MAERA_VENN = NpcDefinition(
    key=MAERA_VENN_KEY,
    name="Witness Maera Venn",
    short_description=(
        "an older Moon Elf Witness in rolled sleeves, sorting clean bandages beside an open window instead of presiding over an altar"
    ),
    room_key=MOON_ELF_WITNESS_INFIRMARY_KEY,
    role="Witness healer and Moon Elf Priest starter mentor",
    dialogue=(
        "Maera folds a strip of linen. 'A wound is true. It is not the whole person. See both, then act.'",
        "'Do not make healing carry a theological argument it never agreed to carry. Help the person in front of you first.'",
    ),
)

RALEN_ORR = NpcDefinition(
    key=RALEN_ORR_KEY,
    name="Ralen Orr",
    short_description=(
        "a young Moon Elf route runner sitting on the edge of a treatment bench with one boot unlaced and an annoyed, swollen ankle"
    ),
    room_key=MOON_ELF_WITNESS_INFIRMARY_KEY,
    role="injured High Horizon courier and first Witness healing patient",
    dialogue=(
        "Ralen gestures toward his ankle. 'I slipped on the lower mirror stair. I can move my toes. I can put a little weight on it. I cannot pretend the rest of the route sounds appealing.'",
        "'Please ask before you turn me into a lesson. I am already having a fairly educational afternoon.'",
    ),
)


MOON_ELF_WITNESS_INFIRMARY = RoomDefinition(
    key=MOON_ELF_WITNESS_INFIRMARY_KEY,
    name="Open-Sky Infirmary",
    region_key=MOON_ELF_REGION_KEY,
    description=(
        "A small public infirmary occupies a bright terrace beside Moonmirror Walk. One entire wall is open above a waist-high stone rail, letting mountain air and a long valley view into a room that otherwise looks reassuringly ordinary: treatment benches, washbasins, bandages, splints, kettles, and shelves of labeled supplies. "
        "A circular viewing frame hangs above one bench, but it is used to compare posture and movement from different angles rather than as an icon. Nothing here resembles a temple pretending not to be one."
    ),
    exits={"west": MOON_ELF_MOONMIRROR_WALK_KEY},
    npc_keys=(MAERA_VENN_KEY, RALEN_ORR_KEY),
    tags=("safe", "moon_elf_start", "witness", "infirmary", "healing", "public_service"),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...]) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
    )


def witness_start_augmentations() -> dict[str, RoomAugmentation]:
    return {
        MOON_ELF_WITNESS_INFIRMARY_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "west",
                    MOON_ELF_MOONMIRROR_WALK_KEY,
                    "Moonmirror Walk",
                    travel_text="You step west from the infirmary into the shifting reflections of Moonmirror Walk.",
                ),
            ),
            features=(
                _feature(
                    "witness_treatment_bench",
                    "Treatment Bench",
                    "a plain padded bench beside Ralen's unlaced boot",
                    "The bench is practical, scrubbed, and slightly scuffed. A folded towel supports Ralen's ankle while Maera keeps the rest of him in the conversation.",
                    ("bench", "treatment bench", "ralen"),
                ),
                _feature(
                    "witness_viewing_frame",
                    "Viewing Frame",
                    "a circular frame positioned to compare stance and gait from two angles",
                    "The frame is not an altar or holy symbol. Healers use it to notice asymmetry in posture and movement before and after treatment.",
                    ("frame", "viewing frame", "circle"),
                ),
                _feature(
                    "witness_supply_shelves",
                    "Supply Shelves",
                    "carefully labeled bandages, splints, salves, kettles, and ordinary medical tools",
                    "The shelves are a quiet reminder that Witness healing is not too proud to use linen, hot water, braces, rest, or someone else's expertise.",
                    ("shelves", "supplies", "medical supplies"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "witness_infirmary_lived_in",
                    "Someone has left half a cup of tea cooling beside a stack of intake slates. The room is a place where people work, ache, recover, argue, and go home.",
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


def _patch_moonmirror_walk() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_MOONMIRROR_WALK_KEY]
    exits = dict(original.exits)
    exits["east"] = MOON_ELF_WITNESS_INFIRMARY_KEY
    description = original.description
    if "Open-Sky Infirmary" not in description:
        description += (
            " A short eastward terrace leads to the Open-Sky Infirmary, a public clinic maintained by ordinary healers and several Witnesses."
        )
    return replace(original, exits=exits, description=description)


def install_moon_elf_witness_start_content(world_service=None) -> None:
    if MOON_ELF_WITNESS_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_WITNESS_QUEST,)
    quests.QUESTS_BY_KEY[MOON_ELF_WITNESS_QUEST.key] = MOON_ELF_WITNESS_QUEST

    _replace_room(MOON_ELF_WITNESS_INFIRMARY)
    _replace_npc(MAERA_VENN)
    _replace_npc(RALEN_ORR)
    moonmirror = _patch_moonmirror_walk()
    _replace_room(moonmirror)

    if world_service is None:
        return

    world_service.legacy_rooms[MOON_ELF_WITNESS_INFIRMARY_KEY] = MOON_ELF_WITNESS_INFIRMARY
    world_service.legacy_rooms[MOON_ELF_MOONMIRROR_WALK_KEY] = moonmirror
    world_service.augmentations.update(witness_start_augmentations())

    base = world_service.augmentations.get(MOON_ELF_MOONMIRROR_WALK_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "east"]
    exits.append(
        ExitDefinition(
            "east",
            MOON_ELF_WITNESS_INFIRMARY_KEY,
            "Open-Sky Infirmary",
            travel_text="You follow the short public terrace east into the Open-Sky Infirmary.",
        )
    )
    world_service.augmentations[MOON_ELF_MOONMIRROR_WALK_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(MOON_ELF_WITNESS_INFIRMARY_KEY, None)
        cache.pop(MOON_ELF_MOONMIRROR_WALK_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    return (
        character.race == "moon_elf"
        and character.character_class == "priest"
        and character.deity_key == MOON_ELF_WITNESS_PATH_KEY
    )


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, MOON_ELF_WITNESS_QUEST_KEY)


def _reconcile_witness_start(session) -> bool:
    if not _qualifies(session):
        return False
    character = session.character
    flags = session.database.list_flags(character.id)
    if MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG not in flags:
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(character.id, MOON_ELF_WITNESS_QUEST_KEY, "meet_maera")
    return True


def _in_infirmary(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == MOON_ELF_WITNESS_INFIRMARY_KEY)


async def _talk_maera(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_infirmary(session):
        return False
    step = quest.get("current_step")

    if step == "meet_maera":
        await session.send(
            "\r\nMaera looks from you to Ralen, then deliberately back to Ralen.\r\n"
            "'He is not here so that you can demonstrate that you are a Priest. He is here because his ankle hurts.'\r\n"
            "She nods toward him. 'Start with the person. TALK RALEN.'\r\n"
        )
        session.database.advance_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY, "hear_ralen")
        return True

    if step == "return_maera":
        session.database.complete_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY)
        session.database.grant_flag(session.character.id, MOON_ELF_WITNESS_COMPLETE_FLAG)
        await session.send(
            "\r\nMaera listens to your report without asking whether the moon approved.\r\n"
            "'Good. You did not heal a metaphor. You helped Ralen. You checked the result. You noticed what remained.'\r\n"
            "She folds the last bandage. 'Later, protection asks the same habit of you from another direction. Immediate danger is real, but it is rarely the only thing present. That is the beginning of the Second View Ward. Not today.'\r\n"
            "\r\nQuest complete: The Wound and the Whole.\r\n"
        )
        return True

    await session.send(
        "Maera gestures gently back toward the current work. 'Finish what is in front of you. Clarity is not an excuse to skip steps.'\r\n"
    )
    return True


async def _talk_ralen(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_infirmary(session) or quest.get("current_step") != "hear_ralen":
        return False
    await session.send(
        "\r\nRalen exhales through his nose. 'Lower mirror stair. Wet edge. Bad foot placement. I caught the rail, so I did not fall far.'\r\n"
        "He flexes his toes. 'I can feel all of those. I can put a little weight on it. The outside of the ankle hurts most.'\r\n"
        "Maera says nothing until you have listened. Then: 'Now EXAMINE ANKLE.'\r\n"
    )
    session.database.advance_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY, "inspect_injury")
    return True


async def _examine_ankle(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_infirmary(session) or quest.get("current_step") != "inspect_injury":
        return False
    await session.send(
        "\r\nThe ankle is swollen along the outer joint, but the line of the limb is intact. Ralen can move his toes, sensation is present, and cautious weight does not collapse the joint. The injury matters; so do all the things that are still working.\r\n"
        "Maera nods once. 'That is the view. Not wound instead of person. Not person instead of wound. Both. When you are ready: MEND RALEN.'\r\n"
    )
    session.database.advance_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY, "mend_injury")
    return True


async def _mend_ralen(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_infirmary(session) or quest.get("current_step") != "mend_injury":
        return False
    flags = session.database.list_flags(session.character.id)
    if MOON_ELF_WITNESS_FIRST_MENDING_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "restoring_light", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, MOON_ELF_WITNESS_FIRST_MENDING_FLAG)
    await session.send(
        "\r\nYou use Clearview Mending with Ralen's permission. You hold the painful swelling in awareness without letting it become the entire picture: intact bone line, responsive toes, warm skin, steady breath, the body's larger pattern still present around the injury.\r\n"
        "Restorative magic answers that disciplined view. The swelling eases. Ralen's jaw unclenches. Nothing speaks from the moon, and nothing about the moment needs to become a proof of where sacred magic ultimately comes from.\r\n"
        "Maera waits before praising anything. 'Now check. EXAMINE GAIT.'\r\n"
    )
    session.database.advance_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY, "check_result")
    return True


async def _examine_gait(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_infirmary(session) or quest.get("current_step") != "check_result":
        return False
    flags = session.database.list_flags(session.character.id)
    if MOON_ELF_WITNESS_RESULT_CHECKED_FLAG not in flags:
        session.database.grant_flag(session.character.id, MOON_ELF_WITNESS_RESULT_CHECKED_FLAG)
    await session.send(
        "\r\nRalen stands, tests the ankle, and takes several careful steps through the viewing frame. His gait is much steadier and the sharp pain has eased, but he still favors the injured side. Healing changed the situation; it did not erase the fact that rest and ordinary care still matter.\r\n"
        "Ralen gives you a relieved half-smile. 'Better. Not magically never-happened. Better.'\r\n"
        "Maera says, 'Exactly. TALK MAERA.'\r\n"
    )
    session.database.advance_quest(session.character.id, MOON_ELF_WITNESS_QUEST_KEY, "return_maera")
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


def install_moon_elf_witness_start_runtime(player_session_class, world_service=None) -> None:
    """Add the first dedicated race/class opening extension: Moon Elf Witness Priest.

    It begins only after The Third Chair, so every Moon Elf still shares the same
    cultural opening before a Witness receives a class-specific act of service.
    """
    if getattr(player_session_class, "_moon_elf_witness_start_runtime_installed", False):
        return

    install_moon_elf_witness_start_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_witness_start(self):
            await self.send(
                "\r\nWitness Ilyra catches you before the Third Chair lesson can become something abstract in memory.\r\n"
                "'You have practiced changing where you stand. Now practice care where someone else actually hurts. Maera Venn is expecting you at the Open-Sky Infirmary, east from Moonmirror Walk.'\r\n"
                "\r\nNew quest: The Wound and the Whole.\r\n"
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
        if normalized in {"talk maera", "talk witness maera", "talk maera venn"}:
            handled = await _talk_maera(self)
        elif normalized in {"talk ralen", "talk ralen orr", "ask ralen"}:
            handled = await _talk_ralen(self)
        elif normalized in {"examine ankle", "inspect ankle", "look ankle", "examine injury", "inspect injury"}:
            handled = await _examine_ankle(self)
        elif normalized in {"mend ralen", "heal ralen", "clearview mending ralen"}:
            handled = await _mend_ralen(self)
        elif normalized in {"examine gait", "inspect gait", "watch ralen", "check ralen"}:
            handled = await _examine_gait(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_witness_start(self):
            await self.send(
                "\r\nIlyra lets the finished civic lesson settle for only a moment.\r\n"
                "'Perspective is cheap if it never becomes care. Maera Venn is expecting you at the Open-Sky Infirmary, east from Moonmirror Walk.'\r\n"
                "\r\nNew quest: The Wound and the Whole.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_witness_start_runtime_installed = True
