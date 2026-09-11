from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_home_and_omens import FOREST_ELF_HEARTHWALK_KEY, FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FOREST_ELF_RETURNING_GROVE_KEY = "forest_elf_returning_grove"
FOREST_ELF_NECROMANCER_QUEST_KEY = "forest_elf_necromancer_part_that_ends"
FOREST_ELF_NECROMANCER_COMPLETE_FLAG = "forest_elf_necromancer_part_that_ends_complete"
FOREST_ELF_NECROMANCER_TRACE_FLAG = "forest_elf_necromancer_ordinary_passing_traced"
FOREST_ELF_NECROMANCER_LIFETAP_FLAG = "forest_elf_necromancer_first_lifetap"
FOREST_ELF_ROOTLEECH_RELEASED_FLAG = "forest_elf_necromancer_rootleech_released"

VEYRA_REEDSHADE_KEY = "forest_elf_necromancer_veyra_reedshade"


FOREST_ELF_NECROMANCER_QUEST = QuestDefinition(
    key=FOREST_ELF_NECROMANCER_QUEST_KEY,
    name="The Part That Ends",
    style="structured",
    description=(
        "After the Forest Elf opening, a young Necromancer is sent to Keeper Veyra Reedshade in the Returning Grove. "
        "The lesson compares the strange delayed transition noticed at the Hushed Verge with an ordinary death, then asks the player to use Minor Life Tap deliberately rather than treating access to life and death as permission to take whatever is nearby."
    ),
    objective_steps=(
        ("meet_veyra", "From Hearthwalk, go NORTH to the Returning Grove and TALK VEYRA."),
        ("examine_doe", "EXAMINE DOE and notice what an ordinary death looks like here."),
        ("trace_passing", "TRACE PASSING to compare the doe's fading life residue with what you sensed at the Hushed Verge."),
        ("inspect_rootleech", "EXAMINE ROOTLEECH before deciding whether to use necromancy on it."),
        ("tap_rootleech", "Use Minor Life Tap in context with LIFE TAP ROOTLEECH."),
        ("check_sapling", "EXAMINE SAPLING and check what your intervention actually changed."),
        ("return_veyra", "TALK VEYRA and explain what you learned about death, taking, and restraint."),
        ("complete", "You learned that death belongs to the forest too, and that touching its boundary does not make everything at that boundary yours."),
    ),
)


VEYRA_REEDSHADE = NpcDefinition(
    key=VEYRA_REEDSHADE_KEY,
    name="Keeper Veyra Reedshade",
    short_description=(
        "a middle-aged Forest Elf Necromancer in a patched work coat, kneeling beside a ledger of fallen animals, compost beds, and marked bone collections"
    ),
    room_key=FOREST_ELF_RETURNING_GROVE_KEY,
    role="Forest Elf Necromancer mentor and keeper of ordinary death-work",
    dialogue=(
        "Veyra closes the ledger with one finger keeping her place. 'Death is not the opposite of the forest. Refusing to look at it would be.'",
        "'Our craft becomes ugly when we confuse being able to touch a boundary with owning whatever lies on it.'",
        "'A corpse is not automatically a problem to solve. Sometimes the correct necromantic decision is to notice that nothing is wrong.'",
    ),
)


FOREST_ELF_RETURNING_GROVE = RoomDefinition(
    key=FOREST_ELF_RETURNING_GROVE_KEY,
    name="The Returning Grove",
    region_key="great_elf_forest",
    description=(
        "A quiet working grove sits just north of Hearthwalk beneath beech and cedar. Fallen branches are stacked by age, compost beds steam gently under woven covers, and several small markers record where animals found dead near the town were moved clear of paths and left to return naturally to soil. "
        "Nothing here is dressed as a graveyard and nothing is hidden because it is unpleasant. A broad old doe lies beneath a beech where flies, beetles, moss, and fungi have already begun ordinary work. Nearby, a young sapling bends under a swollen rootleech clamped to its lower stem."
    ),
    exits={"south": FOREST_ELF_HEARTHWALK_KEY},
    npc_keys=(VEYRA_REEDSHADE_KEY,),
    tags=("safe", "forest_elf_start", "necromancer", "death_work", "ecology", "ordinary_life"),
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


def forest_elf_necromancer_augmentations() -> dict[str, RoomAugmentation]:
    leech_attached = ViewCondition(forbidden_flags=(FOREST_ELF_ROOTLEECH_RELEASED_FLAG,))
    leech_released = ViewCondition(required_flags=(FOREST_ELF_ROOTLEECH_RELEASED_FLAG,))
    return {
        FOREST_ELF_RETURNING_GROVE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "south",
                    FOREST_ELF_HEARTHWALK_KEY,
                    "Hearthwalk",
                    travel_text="You leave the working grove and follow the short cedar path south toward ovens, homes, and ordinary town noise.",
                ),
            ),
            features=(
                _feature(
                    "returning_grove_doe",
                    "Old Doe",
                    "the body of an old doe resting beneath a beech where decay has begun without disturbance",
                    "There is no wound that suggests violence and no sign of binding, animation, or magical interference. The body is cooling into the larger work of beetles, fungi, roots, and soil. To ordinary sight, death here is quiet and complete.",
                    ("doe", "old doe", "dead doe", "remains", "body"),
                ),
                _feature(
                    "returning_grove_ledger",
                    "Returning Ledger",
                    "a plain work ledger tracking found remains, compost beds, and bones deliberately set aside for later use",
                    "The entries are practical: where remains were found, whether a family or owner needed notifying, whether disease was suspected, whether bones were left to return or prepared for teaching and craft. Death does not make relationships disappear from the paperwork.",
                    ("ledger", "returning ledger", "records", "book"),
                ),
                _feature(
                    "returning_grove_rootleech",
                    "Swollen Rootleech",
                    "a thumb-thick forest parasite clamped to a young sapling's lower stem",
                    "The rootleech is alive, feeding, and clearly weakening the sapling. It is not a monster and it is not innocent scenery either. Left alone, it will keep taking until the young tree cannot afford the loss.",
                    ("rootleech", "leech", "parasite"),
                    condition=leech_attached,
                ),
                _feature(
                    "returning_grove_released_leech",
                    "Released Rootleech",
                    "the drained parasite curled in the leaf litter after losing its grip on the sapling",
                    "The rootleech has released the bark and lies sluggish in the leaf litter. The intervention was enough to stop the immediate harm; there was no need to turn the lesson into spectacle.",
                    ("rootleech", "leech", "released leech", "parasite"),
                    condition=leech_released,
                ),
                _feature(
                    "returning_grove_sapling_strained",
                    "Strained Sapling",
                    "a young tree bent slightly around the place where the rootleech is feeding",
                    "The sapling is alive but under obvious strain. Leaves nearest the damaged stem are dull and the bark around the parasite is soft from prolonged feeding.",
                    ("sapling", "young tree", "tree"),
                    condition=leech_attached,
                ),
                _feature(
                    "returning_grove_sapling_recovering",
                    "Recovering Sapling",
                    "the young tree standing free of the rootleech's grip",
                    "The bark is still damaged and recovery will take time, but the drain has stopped. The tree does not spring upright or glow with gratitude. It simply has a better chance than it had a moment ago.",
                    ("sapling", "young tree", "tree"),
                    condition=leech_released,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "returning_grove_working_place",
                    "A shovel leans against a compost frame beside a basket of gloves. Whatever philosophy lives here has to share space with smell, mud, record-keeping, and chores.",
                    priority=50,
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
    exits["north"] = FOREST_ELF_RETURNING_GROVE_KEY
    description = original.description
    if "Returning Grove" not in description:
        description += (
            " A narrow cedar path runs north toward the Returning Grove, where deadfall, compost, found animal remains, and other unglamorous pieces of forest stewardship are handled in the open."
        )
    return replace(original, exits=exits, description=description)


def install_forest_elf_necromancer_content(world_service=None) -> None:
    if FOREST_ELF_NECROMANCER_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_NECROMANCER_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_NECROMANCER_QUEST.key] = FOREST_ELF_NECROMANCER_QUEST

    _replace_room(FOREST_ELF_RETURNING_GROVE)
    _replace_npc(VEYRA_REEDSHADE)
    hearthwalk = _patch_hearthwalk()
    _replace_room(hearthwalk)

    if world_service is None:
        return

    world_service.legacy_rooms[FOREST_ELF_RETURNING_GROVE_KEY] = FOREST_ELF_RETURNING_GROVE
    world_service.legacy_rooms[FOREST_ELF_HEARTHWALK_KEY] = hearthwalk
    world_service.augmentations.update(forest_elf_necromancer_augmentations())

    base = world_service.augmentations.get(FOREST_ELF_HEARTHWALK_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "north"]
    exits.append(
        ExitDefinition(
            "north",
            FOREST_ELF_RETURNING_GROVE_KEY,
            "Returning Grove",
            travel_text="You follow the short cedar path north from Hearthwalk into the Returning Grove.",
        )
    )
    world_service.augmentations[FOREST_ELF_HEARTHWALK_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(FOREST_ELF_RETURNING_GROVE_KEY, None)
        cache.pop(FOREST_ELF_HEARTHWALK_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(
        character
        and character.race == "forest_elf"
        and character.character_class == "necromancer"
    )


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, FOREST_ELF_NECROMANCER_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_necromancer_start(session) -> bool:
    if not _qualifies(session):
        return False
    flags = _flags(session)
    if FOREST_ELF_OPENING_COMPLETE_FLAG not in flags:
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "meet_veyra")
    return True


def _in_returning_grove(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == FOREST_ELF_RETURNING_GROVE_KEY)


async def _talk_veyra(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session):
        return False
    step = quest.get("current_step")

    if step == "meet_veyra":
        session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "examine_doe")
        await session.send(
            "\r\nVeyra does not ask you to prove that you can raise anything. She points instead toward the old doe beneath the beech.\r\n"
            "'At the Hushed Verge, you found a transition that lingered too long. Before you decide what that means, learn the shape of one that is not wrong.'\r\n"
            "She wipes soil from her hands. 'EXAMINE DOE.'\r\n"
        )
        return True

    if step == "return_veyra":
        session.database.complete_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY)
        session.database.grant_flag(session.character.id, FOREST_ELF_NECROMANCER_COMPLETE_FLAG)
        await session.send(
            "\r\nVeyra listens, then nods toward the doe, the sapling, and the sluggish rootleech in turn.\r\n"
            "'Good. The doe did not need rescuing from death. The sapling did need relief from something taking too much. Same craft, different answer.'\r\n"
            "She taps the returning ledger. 'Remember this when you learn to Raise Skeleton. Bone can be material. Death can still have relationships around it. Silent does not mean ownerless, and possible does not mean permitted.'\r\n"
            "'Death belongs to the forest too. Your work is not to defeat that truth. It is to know when the boundary has been disturbed, when it has not, and what you are willing to do about it.'\r\n"
            "\r\nQuest complete: The Part That Ends.\r\n"
        )
        return True

    objective = FOREST_ELF_NECROMANCER_QUEST.objective_for_step(step)
    await session.send("\r\nVeyra waits for you to finish the observation in front of you instead of replacing it with a theory.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _examine_doe(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session) or quest.get("current_step") != "examine_doe":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "trace_passing")
    await session.send(
        "\r\nThe doe died without violence. The body is cooling, insects have begun to gather, and the first pale threads of fungus are already finding what they can use. Nothing is animated. Nothing appears trapped. Nothing here asks to be corrected.\r\n"
        "Veyra says, 'Now use the part of your training ordinary sight cannot. TRACE PASSING.'\r\n"
    )
    return True


async def _trace_passing(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session) or quest.get("current_step") != "trace_passing":
        return False
    if FOREST_ELF_NECROMANCER_TRACE_FLAG not in _flags(session):
        session.database.grant_flag(session.character.id, FOREST_ELF_NECROMANCER_TRACE_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "inspect_rootleech")
    await session.send(
        "\r\nYou let your Necromancer training settle around the place where life recently ended. The remaining vitality is not clinging or circling. It thins, breaks apart, and passes beyond the body in the ordinary way your training expects.\r\n"
        "The contrast with the Hushed Verge is immediate: there, the residue lingered at the threshold. Here, the transition is already completing.\r\n"
        "Veyra points to the young tree nearby. 'Good. One ordinary death can keep you from calling every dead thing a mystery. Now EXAMINE ROOTLEECH.'\r\n"
    )
    return True


async def _examine_rootleech(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session) or quest.get("current_step") != "inspect_rootleech":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "tap_rootleech")
    await session.send(
        "\r\nThe rootleech is healthy in exactly the way the sapling is not. Its body is swollen with stolen sap and blood-dark plant fluid; the young bark around its mouth is soft and failing. This is not a question of whether the parasite is alive. It is. The question is whether you have a reason to take from it.\r\n"
        "Veyra says, 'Now you do. Use enough force to end the drain, not enough to make yourself feel powerful. LIFE TAP ROOTLEECH.'\r\n"
    )
    return True


async def _life_tap_rootleech(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session) or quest.get("current_step") != "tap_rootleech":
        return False
    flags = _flags(session)
    if FOREST_ELF_NECROMANCER_LIFETAP_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "minor_life_tap", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, FOREST_ELF_NECROMANCER_LIFETAP_FLAG)
    session.database.grant_flag(session.character.id, FOREST_ELF_ROOTLEECH_RELEASED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "check_sapling")
    await session.send(
        "\r\nYou catch the rootleech's vitality with Minor Life Tap and draw only until its grip fails. A brief thread of borrowed warmth returns through you as the parasite shrivels, loosens, and drops into the leaves. You stop when the purpose is achieved.\r\n"
        "Veyra does not congratulate the spell. 'Check the thing you meant to help. EXAMINE SAPLING.'\r\n"
    )
    return True


async def _examine_sapling(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_returning_grove(session) or quest.get("current_step") != "check_sapling":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_NECROMANCER_QUEST_KEY, "return_veyra")
    await session.send(
        "\r\nThe sapling is still damaged. Its bark will need time to close and several dull leaves may still be lost, but the active drain has stopped. The tree is not magically restored; it simply has a chance to recover under ordinary care.\r\n"
        "The result is modest, specific, and enough. Veyra waits beside the ledger. TALK VEYRA.\r\n"
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


def install_forest_elf_necromancer_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Forest Elf Necromancer extension after the shared opening."""
    if getattr(player_session_class, "_forest_elf_necromancer_runtime_installed", False):
        return

    install_forest_elf_necromancer_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_necromancer_start(self):
            await self.send(
                "\r\nBefore the Circle fully disperses, Maelis catches you by the sleeve.\r\n"
                "'What you noticed at the Hushed Verge belongs partly to your discipline. Veyra Reedshade can show you what an ordinary passing feels like before you decide the strange one means more than it does.'\r\n"
                "'Find her in the Returning Grove, north from Hearthwalk.'\r\n"
                "\r\nNew quest: The Part That Ends.\r\n"
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
        if normalized in {"talk veyra", "talk keeper veyra", "talk veyra reedshade", "talk keeper veyra reedshade"}:
            handled = await _talk_veyra(self)
        elif normalized in {"examine doe", "inspect doe", "look doe", "examine old doe", "inspect remains", "examine remains"}:
            handled = await _examine_doe(self)
        elif normalized in {"trace passing", "trace residue", "sense passing", "sense residue", "read passing", "read residue"}:
            handled = await _trace_passing(self)
        elif normalized in {"examine rootleech", "inspect rootleech", "look rootleech", "examine leech", "inspect leech"}:
            handled = await _examine_rootleech(self)
        elif normalized in {"life tap rootleech", "minor life tap rootleech", "tap rootleech", "life tap leech", "tap leech"}:
            handled = await _life_tap_rootleech(self)
        elif normalized in {"examine sapling", "inspect sapling", "look sapling", "check sapling", "examine tree"}:
            handled = await _examine_sapling(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_necromancer_start(self):
            await self.send(
                "\r\nAs the Circle breaks back into ordinary work, Maelis stops you for one last thing.\r\n"
                "'Your report from the Hushed Verge noticed a delayed passing. Before you build a theory around it, compare it with one that is ordinary. Veyra Reedshade is in the Returning Grove, north from Hearthwalk.'\r\n"
                "\r\nNew quest: The Part That Ends.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_necromancer_runtime_installed = True
