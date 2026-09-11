from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_home_and_omens import FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.forest_elf_stewardship import FOREST_ELF_KEEPER_NURSERY_KEY
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FOREST_ELF_WARMHOUSE_KEY = "forest_elf_warmhouse"
FOREST_ELF_DRUID_QUEST_KEY = "forest_elf_druid_light_left_on"
FOREST_ELF_DRUID_COMPLETE_FLAG = "forest_elf_druid_light_left_on_complete"
FOREST_ELF_DRUID_FIRST_HEAL_FLAG = "forest_elf_druid_first_minor_heal"
FOREST_ELF_DRUID_ROOST_PREPARED_FLAG = "forest_elf_druid_roost_prepared"
FOREST_ELF_DRUID_THRUSH_RESTED_FLAG = "forest_elf_druid_thrush_rested"
FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG = "forest_elf_druid_thrush_released"

SENNA_MOSSBELL_KEY = "forest_elf_druid_senna_mossbell"


FOREST_ELF_DRUID_QUEST = QuestDefinition(
    key=FOREST_ELF_DRUID_QUEST_KEY,
    name="The Light Left On",
    style="structured",
    description=(
        "After the shared Forest Elf opening, a young Druid takes one ordinary recovery shift in the Warmhouse beside the Keeper's Nursery. "
        "The lesson moves Druidry away from spectacle: diagnose a small injured animal, use Minor Heal only where it helps, provide ordinary shelter afterward, wait, and let the creature decide when it is ready to leave."
    ),
    objective_steps=(
        ("meet_senna", "From Keeper's Nursery, go EAST into the Warmhouse and TALK SENNA."),
        ("examine_thrush", "EXAMINE THRUSH before deciding whether magic is needed."),
        ("heal_thrush", "Use your basic Druid healing in context with MINOR HEAL THRUSH."),
        ("prepare_roost", "PREPARE ROOST so the bird has warmth, water, darkness, and somewhere safe to rest after the spell."),
        ("wait_rest", "WAIT and let recovery happen without adding more magic."),
        ("open_shutter", "OPEN SHUTTER and give the thrush the choice to stay or leave."),
        ("return_senna", "TALK SENNA after the bird makes its own choice."),
        ("complete", "You learned that Druidry is often one useful spell surrounded by ordinary care, patience, and respect for another living thing's agency."),
    ),
)


SENNA_MOSSBELL = NpcDefinition(
    key=SENNA_MOSSBELL_KEY,
    name="Druid Senna Mossbell",
    short_description=(
        "a broad-shouldered Forest Elf Druid in a wool cardigan, rinsing a tiny water dish beside a kettle and a stack of folded recovery cloths"
    ),
    room_key=FOREST_ELF_WARMHOUSE_KEY,
    role="Forest Elf Druid mentor and keeper of the nursery recovery room",
    dialogue=(
        "Senna checks the stove before she checks you. 'Druidry spends less time calling storms than stories suggest. Most days somebody needs clean water and a warm place to stop being frightened.'",
        "'Magic is one tool. If you reach for it before your eyes, your hands, and your patience, you will eventually make a very impressive mistake.'",
        "'Helping a living thing recover does not make it yours. That is true of birds, trees, patients, and people.'",
    ),
)


FOREST_ELF_WARMHOUSE = RoomDefinition(
    key=FOREST_ELF_WARMHOUSE_KEY,
    name="The Warmhouse",
    region_key="great_elf_forest",
    description=(
        "A small clay-and-willow room leans against the east side of the Keeper's Nursery, warmed by a squat tile stove and the soft heat of covered seed trays. Shelves hold folded cloths, shallow water dishes, splints, salves, and recovery baskets for small animals found near the town. "
        "A kettle murmurs beside mismatched cups. Near a half-open shutter, a young wood thrush rests in a padded basket with one wing held carefully away from its body. The room feels less like a sanctuary than a place someone remembered to keep warm."
    ),
    exits={"west": FOREST_ELF_KEEPER_NURSERY_KEY},
    npc_keys=(SENNA_MOSSBELL_KEY,),
    tags=("safe", "forest_elf_start", "druid", "recovery", "cozy", "ordinary_care"),
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


def forest_elf_druid_augmentations() -> dict[str, RoomAugmentation]:
    thrush_present = ViewCondition(forbidden_flags=(FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG,))
    thrush_unhealed = ViewCondition(
        forbidden_flags=(FOREST_ELF_DRUID_FIRST_HEAL_FLAG, FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG)
    )
    thrush_healed = ViewCondition(
        required_flags=(FOREST_ELF_DRUID_FIRST_HEAL_FLAG,),
        forbidden_flags=(FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG,),
    )
    roost_ready = ViewCondition(required_flags=(FOREST_ELF_DRUID_ROOST_PREPARED_FLAG,))
    released = ViewCondition(required_flags=(FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG,))

    return {
        FOREST_ELF_WARMHOUSE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "west",
                    FOREST_ELF_KEEPER_NURSERY_KEY,
                    "Keeper's Nursery",
                    travel_text="You step west from the Warmhouse into the nursery beds and filtered forest light.",
                ),
            ),
            features=(
                _feature(
                    "warmhouse_injured_thrush",
                    "Injured Wood Thrush",
                    "a young wood thrush sitting low in a padded recovery basket with one wing guarded close to its body",
                    "The bird is alert and breathing evenly. One wing has a shallow torn patch through the small feathers and dark bruising beneath it, but the joint is aligned and the long flight feathers are intact. It is hurt, not dying, and the difference matters.",
                    ("thrush", "wood thrush", "bird", "injured bird", "young thrush"),
                    condition=thrush_unhealed,
                ),
                _feature(
                    "warmhouse_mended_thrush",
                    "Resting Wood Thrush",
                    "the young thrush resting more evenly after the torn skin has been mended",
                    "The scrape has closed and the angry swelling is already softer, but the bird is still tired and protective of the wing. Minor Heal changed the injury; it did not remove the need for warmth, quiet, water, and time.",
                    ("thrush", "wood thrush", "bird", "resting bird", "young thrush"),
                    condition=thrush_healed,
                ),
                _feature(
                    "warmhouse_recovery_roost",
                    "Recovery Roost",
                    "a low woven basket, folded cloth, shallow water cap, and dim cover arranged for a small recovering animal",
                    "Nothing about the roost is magical. Its design is practical: warmth without overheating, darkness without confinement, water shallow enough to be safe, and enough space for an animal to shift position without struggling.",
                    ("roost", "recovery roost", "basket", "recovery basket", "bed"),
                ),
                _feature(
                    "warmhouse_stove",
                    "Tile Stove",
                    "a squat tile stove keeping the room gently warm rather than hot",
                    "A small slate beside the stove records temperature checks in several hands. The Warmhouse is comfortable because people keep returning to ordinary maintenance, not because a Druid enchanted the weather indoors.",
                    ("stove", "tile stove", "heater", "warm stove"),
                ),
                _feature(
                    "warmhouse_kettle",
                    "Kettle and Cups",
                    "a blackened kettle and a shelf of mismatched cups beside dried mint and berry leaf",
                    "The cups have names scratched into some handles and repaired chips in others. One is labeled SELA and has a note tied to it: RETURN THIS TIME.",
                    ("kettle", "cups", "tea", "mugs", "tea shelf"),
                ),
                _feature(
                    "warmhouse_open_roost",
                    "Empty Recovery Roost",
                    "the rumpled basket the thrush left behind after choosing the open shutter",
                    "A few small feathers remain in the cloth. Senna has not cleaned them away yet. Recovery rooms are supposed to become empty again.",
                    ("roost", "recovery roost", "basket", "empty basket"),
                    condition=released,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "warmhouse_everyday_comfort",
                    "The stove ticks quietly as it cools and warms. Somewhere outside, nursery leaves brush against the wall. A folded blanket has been left over the back of a chair for whoever ends up staying longer than planned.",
                    priority=45,
                ),
                DescriptionLayer(
                    "warmhouse_roost_prepared",
                    "The recovery roost has been set with fresh cloth, shallow water, and a loose dim cover. Nothing about it is dramatic, which is part of why it works.",
                    priority=60,
                    condition=roost_ready,
                ),
                DescriptionLayer(
                    "warmhouse_after_release",
                    "The shutter stands open to the nursery branches outside. The room feels successful precisely because one of its baskets is empty.",
                    priority=75,
                    condition=released,
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


def _patch_nursery() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[FOREST_ELF_KEEPER_NURSERY_KEY]
    exits = dict(original.exits)
    exits["east"] = FOREST_ELF_WARMHOUSE_KEY
    description = original.description
    if "Warmhouse" not in description:
        description += (
            " A low clay-and-willow annex stands to the east: the Warmhouse, where seedlings, injured small animals, and occasionally exhausted keepers are given somewhere warm to recover."
        )
    return replace(original, exits=exits, description=description)


def install_forest_elf_druid_content(world_service=None) -> None:
    if FOREST_ELF_DRUID_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_DRUID_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_DRUID_QUEST.key] = FOREST_ELF_DRUID_QUEST

    _replace_room(FOREST_ELF_WARMHOUSE)
    _replace_npc(SENNA_MOSSBELL)
    nursery = _patch_nursery()
    _replace_room(nursery)

    if world_service is None:
        return

    world_service.legacy_rooms[FOREST_ELF_WARMHOUSE_KEY] = FOREST_ELF_WARMHOUSE
    world_service.legacy_rooms[FOREST_ELF_KEEPER_NURSERY_KEY] = nursery
    world_service.augmentations.update(forest_elf_druid_augmentations())

    base = world_service.augmentations.get(FOREST_ELF_KEEPER_NURSERY_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "east"]
    exits.append(
        ExitDefinition(
            "east",
            FOREST_ELF_WARMHOUSE_KEY,
            "The Warmhouse",
            travel_text="You follow the nursery wall east and step into the gentle heat of the Warmhouse.",
        )
    )
    world_service.augmentations[FOREST_ELF_KEEPER_NURSERY_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(FOREST_ELF_WARMHOUSE_KEY, None)
        cache.pop(FOREST_ELF_KEEPER_NURSERY_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(
        character
        and character.race == "forest_elf"
        and character.character_class == "druid"
    )


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, FOREST_ELF_DRUID_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_druid_start(session) -> bool:
    if not _qualifies(session):
        return False
    flags = _flags(session)
    if FOREST_ELF_OPENING_COMPLETE_FLAG not in flags:
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "meet_senna")
    return True


def _in_warmhouse(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == FOREST_ELF_WARMHOUSE_KEY)


async def _talk_senna(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session):
        return False
    step = quest.get("current_step")

    if step == "meet_senna":
        session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "examine_thrush")
        await session.send(
            "\r\nSenna pours a little hot water into a cup, thinks better of handing it to you yet, and points toward the recovery basket.\r\n"
            "'A child found that thrush tangled in thorn after a hard flight. Before you become impressed with being the Druid in the room, find out what is actually wrong.'\r\n"
            "She nudges a stool toward the basket. 'EXAMINE THRUSH.'\r\n"
        )
        return True

    if step == "return_senna":
        session.database.complete_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY)
        session.database.grant_flag(session.character.id, FOREST_ELF_DRUID_COMPLETE_FLAG)
        await session.send(
            "\r\nSenna finally hands you the cup she poured earlier. It is only warm now.\r\n"
            "'Good. You used magic once, cloth twice, and patience the longest.'\r\n"
            "She glances toward the open shutter. 'Druidry does not make you the owner of living things, and it does not make your care more important than Sela's drainage work, Neris's lunch parcel, or the person who remembered to clean this water dish.'\r\n"
            "'It means you have a few unusual tools. Be useful with them. Be ordinary when ordinary is enough.'\r\n"
            "She smiles into her own cup. 'Later, when you learn to lend more strength to another body, remember the thrush. Help is not the same thing as deciding what happens next.'\r\n"
            "\r\nQuest complete: The Light Left On.\r\n"
        )
        return True

    objective = FOREST_ELF_DRUID_QUEST.objective_for_step(step)
    await session.send("\r\nSenna keeps one eye on the recovery basket and lets the current lesson stay small.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _examine_thrush(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session) or quest.get("current_step") != "examine_thrush":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "heal_thrush")
    await session.send(
        "\r\nYou watch before touching. The thrush is alert, breathing steadily, and tracking movement with both eyes. The wing joint sits correctly and the flight feathers are intact. A shallow tear and deep bruise along the smaller feathers are painful enough to keep the wing guarded, but nothing suggests a break or internal collapse.\r\n"
        "Senna nods. 'Good. Minor Heal can help the damaged tissue. It cannot make rest unnecessary. Use MINOR HEAL THRUSH.'\r\n"
    )
    return True


async def _minor_heal_thrush(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session) or quest.get("current_step") != "heal_thrush":
        return False
    flags = _flags(session)
    if FOREST_ELF_DRUID_FIRST_HEAL_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "minor_heal", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, FOREST_ELF_DRUID_FIRST_HEAL_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "prepare_roost")
    await session.send(
        "\r\nYou let Minor Heal settle through the torn skin and bruised muscle without pushing farther than the injury asks. The shallow tear closes. The swelling eases. The thrush loosens its grip on the basket edge, but it does not suddenly become a healthy bird performing gratitude for you.\r\n"
        "Senna reaches past your magic for a clean cloth. 'Now do the part a spell cannot do for you. PREPARE ROOST.'\r\n"
    )
    return True


async def _prepare_roost(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session) or quest.get("current_step") != "prepare_roost":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_DRUID_ROOST_PREPARED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "wait_rest")
    await session.send(
        "\r\nYou replace the rumpled cloth with a dry fold, set a shallow cap of water within reach, lower the loose cover enough to dim the basket, and move it one handspan farther from the stove. Warm, not hot. Quiet, not trapped.\r\n"
        "Senna settles into the chair by the kettle. 'That is care too. Now WAIT.'\r\n"
    )
    return True


async def _wait_rest(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session) or quest.get("current_step") != "wait_rest":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_DRUID_THRUSH_RESTED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "open_shutter")
    await session.send(
        "\r\nYou wait. The kettle ticks. Leaves brush the outer wall. Senna does not fill the silence with instruction.\r\n"
        "Eventually the thrush drinks, settles its weight evenly, then climbs from the basket to the low sill under its own power. It flexes the mended wing once, then again.\r\n"
        "Senna says quietly, 'You can make a choice available. You cannot make the choice for it. OPEN SHUTTER.'\r\n"
    )
    return True


async def _open_shutter(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_warmhouse(session) or quest.get("current_step") != "open_shutter":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_DRUID_THRUSH_RELEASED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_DRUID_QUEST_KEY, "return_senna")
    await session.send(
        "\r\nYou lift the wooden latch and open the shutter wide enough for the thrush to leave. For several breaths it does not. Then it hops to the outer ledge, tests the wing once more, and flies only as far as a nearby nursery branch.\r\n"
        "It stays there, small and self-contained, before disappearing deeper among the leaves. You do not call it back.\r\n"
        "Senna picks up the empty water cap. TALK SENNA.\r\n"
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


def install_forest_elf_druid_runtime(player_session_class, world_service=None) -> None:
    """Add the cozy Forest Elf Druid extension after the shared racial opening."""
    if getattr(player_session_class, "_forest_elf_druid_runtime_installed", False):
        return

    install_forest_elf_druid_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_druid_start(self):
            await self.send(
                "\r\nAs the Circle returns to its ordinary work, Maelis catches you before you leave.\r\n"
                "'You have spent the morning learning how much a Druid can notice. Senna Mossbell wants to teach you something less impressive: what care looks like after the spell is finished.'\r\n"
                "'Find her in the Warmhouse, east from Keeper's Nursery.'\r\n"
                "\r\nNew quest: The Light Left On.\r\n"
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
        if normalized in {"talk senna", "talk druid senna", "talk senna mossbell", "talk druid senna mossbell"}:
            handled = await _talk_senna(self)
        elif normalized in {"examine thrush", "inspect thrush", "look thrush", "examine bird", "inspect bird", "look bird"}:
            handled = await _examine_thrush(self)
        elif normalized in {"minor heal thrush", "heal thrush", "cast minor heal thrush", "minor heal bird", "heal bird"}:
            handled = await _minor_heal_thrush(self)
        elif normalized in {"prepare roost", "prepare recovery roost", "settle thrush", "make roost", "ready roost"}:
            handled = await _prepare_roost(self)
        elif normalized in {"wait", "wait quietly", "wait with thrush", "rest", "sit and wait"}:
            handled = await _wait_rest(self)
        elif normalized in {"open shutter", "open the shutter", "unlatch shutter", "lift shutter", "release thrush", "let thrush go"}:
            handled = await _open_shutter(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_druid_start(self):
            await self.send(
                "\r\nWhen the Circle meeting finally dissolves into chores, Maelis stops you with a small smile.\r\n"
                "'You know how to notice a living system now. Senna Mossbell wants to show you the part that comes after noticing: staying long enough for care to become ordinary.'\r\n"
                "'The Warmhouse is east from Keeper's Nursery.'\r\n"
                "\r\nNew quest: The Light Left On.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_druid_runtime_installed = True
