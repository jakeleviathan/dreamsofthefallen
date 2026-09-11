from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_home_and_omens import FOREST_ELF_HEARTHWALK_KEY, FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FOREST_ELF_REMEMBRANCE_ARBOR_KEY = "forest_elf_remembrance_arbor"
FOREST_ELF_PRIEST_QUEST_KEY = "forest_elf_priest_one_cup_unfilled"
FOREST_ELF_PRIEST_COMPLETE_FLAG = "forest_elf_priest_one_cup_unfilled_complete"
FOREST_ELF_PRIEST_STORY_HEARD_FLAG = "forest_elf_priest_story_heard"
FOREST_ELF_PRIEST_CUP_SET_FLAG = "forest_elf_priest_cup_set"
FOREST_ELF_PRIEST_SILENCE_HELD_FLAG = "forest_elf_priest_silence_held"
FOREST_ELF_PRIEST_NAME_SPOKEN_FLAG = "forest_elf_priest_name_spoken"

PRIEST_ALEN_WILLOWGREY_KEY = "forest_elf_priest_alen_willowgrey"
MIRA_ASHFERN_KEY = "forest_elf_mira_ashfern"


FOREST_ELF_PRIEST_QUEST = QuestDefinition(
    key=FOREST_ELF_PRIEST_QUEST_KEY,
    name="One Cup Unfilled",
    style="structured",
    description=(
        "After the shared Forest Elf opening, a young Priest helps prepare an ordinary remembrance for Elder Sera Ashfern, "
        "who died peacefully after a long life. The lesson is not to prove a deity, explain death, or magically remove grief. "
        "It is to listen, give ritual a useful shape, make room for silence, and help a community say one person's name together."
    ),
    objective_steps=(
        ("meet_alen", "From Hearthwalk, go SOUTH to the Remembrance Arbor and TALK ALEN."),
        ("listen_mira", "TALK MIRA and listen before deciding what the remembrance needs."),
        ("inspect_table", "EXAMINE MEMORY TABLE and learn why the ordinary objects were chosen."),
        ("set_cup", "SET EMPTY CUP at Sera's place without pretending she is still physically present."),
        ("hold_silence", "HOLD SILENCE with the family instead of rushing to fill the difficult moment."),
        ("speak_name", "SPEAK SERA'S NAME when Mira is ready for the remembrance to continue."),
        ("return_alen", "TALK ALEN after the family has had the moment it came here to have."),
        ("complete", "You learned that a Priest can hold a communal moment without turning grief into a problem to solve or a doctrine to prove."),
    ),
)


PRIEST_ALEN_WILLOWGREY = NpcDefinition(
    key=PRIEST_ALEN_WILLOWGREY_KEY,
    name="Priest Alen Willowgrey",
    short_description=(
        "an older Forest Elf Priest in a plain green-grey wrap, setting cups and benches with the concentration of someone who considers practical hospitality part of sacred work"
    ),
    room_key=FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
    role="Forest Elf Priest mentor and keeper of communal remembrances",
    dialogue=(
        "Alen straightens a bench. 'People sometimes come to Priests because they need an answer. Sometimes they come because they need someone not to run away from the question.'",
        "'Ritual is not evidence. It is a shape people can stand inside together when ordinary speech becomes difficult.'",
        "'Do not confuse comfort with explanation. A person can be comforted without being told why death happened.'",
    ),
)

MIRA_ASHFERN = NpcDefinition(
    key=MIRA_ASHFERN_KEY,
    name="Mira Ashfern",
    short_description=(
        "a tired middle-aged Forest Elf turning an old pruning knife over in both hands while deciding where it belongs on the memory table"
    ),
    room_key=FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
    role="daughter of Elder Sera Ashfern and participant in the remembrance",
    dialogue=(
        "Mira rubs her thumb across the worn handle. 'Mother died in her own bed after breakfast. She was eighty-one. Nothing went wrong. I still keep thinking there should be something to fix.'",
        "'She hated solemn speeches about how wise she was. She liked pears, complained about wet socks, and sharpened every knife in the house whether anyone asked her to or not.'",
    ),
)


FOREST_ELF_REMEMBRANCE_ARBOR = RoomDefinition(
    key=FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
    name="Remembrance Arbor",
    region_key="great_elf_forest",
    description=(
        "A modest open-sided arbor stands just south of Hearthwalk beneath two old pear trees. It is used for small remembrances, difficult conversations, naming ceremonies, reconciliations, and the occasional meal that simply needs somewhere quieter than home. "
        "Tonight a low table holds a worn pruning knife, a recipe slate stained with berry juice, a patched gardening glove, three pears, and several plain wooden cups. One chair remains deliberately empty. There is no altar at the head of the room and no place reserved above the family for a Priest."
    ),
    exits={"north": FOREST_ELF_HEARTHWALK_KEY},
    npc_keys=(PRIEST_ALEN_WILLOWGREY_KEY, MIRA_ASHFERN_KEY),
    tags=("safe", "forest_elf_start", "priest", "remembrance", "community", "grief", "ritual"),
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


def forest_elf_priest_augmentations() -> dict[str, RoomAugmentation]:
    cup_unset = ViewCondition(forbidden_flags=(FOREST_ELF_PRIEST_CUP_SET_FLAG,))
    cup_set = ViewCondition(required_flags=(FOREST_ELF_PRIEST_CUP_SET_FLAG,))
    silence_held = ViewCondition(required_flags=(FOREST_ELF_PRIEST_SILENCE_HELD_FLAG,))
    name_spoken = ViewCondition(required_flags=(FOREST_ELF_PRIEST_NAME_SPOKEN_FLAG,))
    return {
        FOREST_ELF_REMEMBRANCE_ARBOR_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    FOREST_ELF_HEARTHWALK_KEY,
                    "Hearthwalk",
                    travel_text="You leave the quiet pear arbor and follow the short plank path north into Hearthwalk's ovens, errands, and household noise.",
                ),
            ),
            features=(
                _feature(
                    "remembrance_memory_table",
                    "Memory Table",
                    "a low table of ordinary things that belonged to Sera Ashfern",
                    "Nothing on the table is valuable in the market sense. The pruning knife was sharpened almost to a different shape. The berry-stained recipe slate records a jam everyone says she routinely overcooked. The patched glove has two different kinds of thread. These objects were chosen because they make a specific person easier to remember, not because they prove anything about what happens after death.",
                    ("memory table", "table", "objects", "memories", "remembrance table"),
                ),
                _feature(
                    "remembrance_empty_chair",
                    "Empty Chair",
                    "Sera's usual arbor chair left empty beside the family benches",
                    "The chair is empty on purpose. No one claims Sera is secretly sitting in it. Its absence gives the eye somewhere to put the fact that a familiar person is no longer physically present.",
                    ("empty chair", "chair", "sera's chair", "sera chair"),
                ),
                _feature(
                    "remembrance_unset_cup",
                    "Unfilled Cup",
                    "one plain wooden cup waiting beside Sera's empty chair",
                    "The cup has not been filled. Alen explains that the custom marks a place in the shared meal without pretending the dead still need food or drink.",
                    ("empty cup", "unfilled cup", "cup", "sera's cup"),
                    condition=cup_unset,
                ),
                _feature(
                    "remembrance_set_cup",
                    "Sera's Unfilled Cup",
                    "a plain wooden cup now set at the empty place, deliberately left unfilled",
                    "The cup is present and empty. It says that Sera had a place among these people and that the place feels different now. It says nothing certain about gods, souls, or destinations.",
                    ("empty cup", "unfilled cup", "cup", "sera's cup"),
                    condition=cup_set,
                ),
                _feature(
                    "remembrance_pear_trees",
                    "Old Pear Trees",
                    "two broad pear trees shading the open arbor",
                    "Sera helped graft one of these trees decades ago, although three other gardeners did just as much work and apparently argued with her throughout. New growth has long since crossed every visible graft line.",
                    ("pear trees", "trees", "pear tree", "pears"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "remembrance_preparation",
                    "People arrive quietly with covered dishes and practical questions about benches. Grief has not stopped anyone from needing to know where the spoons went.",
                    priority=45,
                ),
                DescriptionLayer(
                    "remembrance_shared_silence",
                    "For a while, nobody speaks. Wind moves through the pear leaves, someone sniffles once, and no one hurries to rescue the silence from itself.",
                    priority=65,
                    condition=silence_held,
                ),
                DescriptionLayer(
                    "remembrance_name_carried",
                    "Sera's name has been spoken aloud here. Conversation has begun again in small pieces: a wet-socks story, an argument about pear jam, a laugh that surprises the person laughing.",
                    priority=80,
                    condition=name_spoken,
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


def _patch_hearthwalk() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[FOREST_ELF_HEARTHWALK_KEY]
    exits = dict(original.exits)
    exits["south"] = FOREST_ELF_REMEMBRANCE_ARBOR_KEY
    description = original.description
    if "Remembrance Arbor" not in description:
        description += (
            " A quieter plank path runs south beneath two pear trees to the Remembrance Arbor, a communal place for small ceremonies, grief, reconciliation, and meals that need gentler company."
        )
    return replace(original, exits=exits, description=description)


def install_forest_elf_priest_content(world_service=None) -> None:
    if FOREST_ELF_PRIEST_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_PRIEST_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_PRIEST_QUEST.key] = FOREST_ELF_PRIEST_QUEST

    _replace_room(FOREST_ELF_REMEMBRANCE_ARBOR)
    _replace_npc(PRIEST_ALEN_WILLOWGREY)
    _replace_npc(MIRA_ASHFERN)
    hearthwalk = _patch_hearthwalk()
    _replace_room(hearthwalk)

    if world_service is None:
        return

    world_service.legacy_rooms[FOREST_ELF_REMEMBRANCE_ARBOR_KEY] = FOREST_ELF_REMEMBRANCE_ARBOR
    world_service.legacy_rooms[FOREST_ELF_HEARTHWALK_KEY] = hearthwalk
    world_service.augmentations.update(forest_elf_priest_augmentations())

    base = world_service.augmentations.get(FOREST_ELF_HEARTHWALK_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "south"]
    exits.append(
        ExitDefinition(
            "south",
            FOREST_ELF_REMEMBRANCE_ARBOR_KEY,
            "Remembrance Arbor",
            travel_text="You take the quiet plank path south from Hearthwalk beneath the pear trees to the Remembrance Arbor.",
        )
    )
    world_service.augmentations[FOREST_ELF_HEARTHWALK_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(FOREST_ELF_REMEMBRANCE_ARBOR_KEY, None)
        cache.pop(FOREST_ELF_HEARTHWALK_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "forest_elf" and character.character_class == "priest")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, FOREST_ELF_PRIEST_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_priest_start(session) -> bool:
    if not _qualifies(session):
        return False
    if FOREST_ELF_OPENING_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "meet_alen")
    return True


def _in_arbor(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == FOREST_ELF_REMEMBRANCE_ARBOR_KEY)


def _deity_lens(deity_key: str | None) -> str:
    if deity_key == "zerjz":
        return (
            "Alen glances at the symbol of Zerjz you carry. 'Restoration has its place. But grief is not a wound you should try to close simply because it hurts.'"
        )
    if deity_key == "tenebrous":
        return (
            "Alen glances at the symbol of Tenebrous you carry. 'Protection has its place. But do not promise people that loving someone can be made safe from loss.'"
        )
    if deity_key == "leviathan":
        return (
            "Alen glances at the symbol of Leviathan you carry. 'Judgment has its place. But Sera died at eighty-one after breakfast. There is no culprit here for grief to prosecute.'"
        )
    return (
        "Alen studies you for a moment. 'Whatever language you use for the sacred, do not make this family carry your certainty for you. They came here to remember Sera.'"
    )


async def _talk_alen(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session):
        return False
    step = quest.get("current_step")

    if step == "meet_alen":
        session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "listen_mira")
        await session.send(
            "\r\nAlen is moving benches when you arrive. He gives you one end of a bench before he gives you a lesson.\r\n"
            "'Sera Ashfern died three mornings ago. Peacefully. Her family asked for a remembrance tonight.'\r\n"
            "Alen sets down his end of the bench. 'Ritual is not evidence. It is a shape people can stand inside together when ordinary speech becomes difficult.'\r\n"
            + _deity_lens(getattr(session.character, "deity_key", None))
            + "\r\n'Priests are useful here when we remember that presence is also a form of service. Start with her daughter. TALK MIRA.'\r\n"
        )
        return True

    if step == "return_alen":
        session.database.complete_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY)
        session.database.grant_flag(session.character.id, FOREST_ELF_PRIEST_COMPLETE_FLAG)
        await session.send(
            "\r\nAlen waits until Mira has joined the others before speaking to you.\r\n"
            "'You did not explain death. You did not turn grief into a test of faith. You did not use magic merely because you had it.'\r\n"
            "He gathers two unused cups. 'You listened. You gave the room a shape. You stayed when it became quiet. Then you helped them say her name.'\r\n"
            "'Remember that. Sometimes people need a Priest to heal, ward, or judge. Sometimes they need someone who knows how to hold a moment without stealing it.'\r\n"
            "\r\nQuest complete: One Cup Unfilled.\r\n"
        )
        return True

    objective = FOREST_ELF_PRIEST_QUEST.objective_for_step(step)
    await session.send("\r\nAlen lowers his voice. 'Do not rush the order of this. The family is not a ritual component.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _talk_mira(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session) or quest.get("current_step") != "listen_mira":
        return False
    if FOREST_ELF_PRIEST_STORY_HEARD_FLAG not in _flags(session):
        session.database.grant_flag(session.character.id, FOREST_ELF_PRIEST_STORY_HEARD_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "inspect_table")
    await session.send(
        "\r\nMira keeps turning the pruning knife over while she talks.\r\n"
        "'Mother died in her own bed after breakfast. She was eighty-one. Nothing went wrong. That almost makes it harder to know what I am supposed to be angry at.'\r\n"
        "You let the sentence remain unfinished until she chooses another one.\r\n"
        "'Please do not tell everyone she was serene and wise. She was funny and impatient and impossible about wet socks. I want them to remember her, not a polished version of her.'\r\n"
        "Alen says quietly, 'Good. Now EXAMINE MEMORY TABLE.'\r\n"
    )
    return True


async def _inspect_table(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session) or quest.get("current_step") != "inspect_table":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "set_cup")
    await session.send(
        "\r\nThe table holds things that make Sera specific rather than exemplary: the knife she over-sharpened, the glove she repaired badly, the recipe slate for jam everyone says she burned, and pears from a tree she helped graft while arguing with three neighbors.\r\n"
        "Alen touches the plain cup beside the empty chair. 'Ritual does not need to improve the dead person. It can simply help the living remember accurately. SET EMPTY CUP.'\r\n"
    )
    return True


async def _set_cup(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session) or quest.get("current_step") != "set_cup":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_PRIEST_CUP_SET_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "hold_silence")
    await session.send(
        "\r\nYou set the plain cup beside Sera's empty chair and leave it unfilled. No one says she needs it. No one pretends absence is presence. The cup simply marks that this meal has a shape changed by someone missing from it.\r\n"
        "The family settles onto the benches. Mira looks as if she expects someone to begin speaking immediately. Alen does not.\r\n"
        "He murmurs to you, 'Do not rescue them from every silence. HOLD SILENCE.'\r\n"
    )
    return True


async def _hold_silence(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session) or quest.get("current_step") != "hold_silence":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_PRIEST_SILENCE_HELD_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "speak_name")
    await session.send(
        "\r\nYou remain where you are and let the quiet stay quiet. Wind moves through pear leaves. Someone breathes unevenly. A child leans against an aunt. Nobody is required to turn the silence into a lesson.\r\n"
        "After a while, Mira puts the pruning knife on the table and nods to you. She is ready for the room to move again.\r\n"
        "Alen says only, 'Now you can give them the smallest beginning. SPEAK SERA'S NAME.'\r\n"
    )
    return True


async def _speak_name(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_arbor(session) or quest.get("current_step") != "speak_name":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_PRIEST_NAME_SPOKEN_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_PRIEST_QUEST_KEY, "return_alen")
    await session.send(
        "\r\n'Sera Ashfern.'\r\n"
        "You do not attach a sermon to the name.\r\n"
        "Mira answers first: 'Sera Ashfern, who sharpened knives that were already sharp.'\r\n"
        "Someone else adds the wet-socks story. A cousin disputes the jam recipe. A laugh arrives unexpectedly and is allowed to be a laugh rather than evidence that grief is finished.\r\n"
        "Alen begins passing bread. The remembrance has become a meal without ceasing to be a remembrance. TALK ALEN when you are ready.\r\n"
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


def install_forest_elf_priest_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Forest Elf Priest remembrance extension after the shared opening."""
    if getattr(player_session_class, "_forest_elf_priest_runtime_installed", False):
        return

    install_forest_elf_priest_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_priest_start(self):
            await self.send(
                "\r\nNeris catches you on Hearthwalk with a folded note and a covered dish for the evening remembrance.\r\n"
                "'Alen Willowgrey asked for another Priest. Sera Ashfern died peacefully this week, and her family is gathering at the Remembrance Arbor south of here.'\r\n"
                "'He said to tell you they need a person, not a sermon.'\r\n"
                "\r\nNew quest: One Cup Unfilled.\r\n"
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
        if normalized in {"talk alen", "talk priest alen", "talk alen willowgrey", "talk priest alen willowgrey"}:
            handled = await _talk_alen(self)
        elif normalized in {"talk mira", "talk mira ashfern", "listen mira", "listen to mira"}:
            handled = await _talk_mira(self)
        elif normalized in {"examine memory table", "inspect memory table", "look memory table", "examine table", "inspect table"}:
            handled = await _inspect_table(self)
        elif normalized in {"set empty cup", "place empty cup", "set cup", "place cup", "set sera's cup", "set sera cup"}:
            handled = await _set_cup(self)
        elif normalized in {"hold silence", "keep silence", "sit in silence", "be silent", "wait in silence"}:
            handled = await _hold_silence(self)
        elif normalized in {"speak sera's name", "speak sera name", "say sera's name", "say sera name", "speak name", "say sera ashfern", "speak sera ashfern"}:
            handled = await _speak_name(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_priest_start(self):
            await self.send(
                "\r\nWhen the shared Forest Elf opening settles back into ordinary life, Neris gives you a covered dish and a short note.\r\n"
                "'Alen Willowgrey needs another Priest for Sera Ashfern's remembrance. Remembrance Arbor, south from Hearthwalk. He says they need a person, not a sermon.'\r\n"
                "\r\nNew quest: One Cup Unfilled.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_priest_runtime_installed = True
