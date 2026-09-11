from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_city import MOON_ELF_REGION_KEY, MOON_ELF_WIND_TERRACE_KEY
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_ALPINE_GARDEN_KEY = "moon_elf_alpine_light_garden"
MOON_ELF_DRUID_QUEST_KEY = "moon_elf_druid_where_light_falls"
MOON_ELF_DRUID_COMPLETE_FLAG = "moon_elf_druid_where_light_falls_complete"
MOON_ELF_DRUID_BED_INSPECTED_FLAG = "moon_elf_druid_bed_inspected"
MOON_ELF_DRUID_SHADE_VIEW_FLAG = "moon_elf_druid_shade_view"
MOON_ELF_DRUID_PATH_VIEW_FLAG = "moon_elf_druid_path_view"
MOON_ELF_DRUID_LIGHT_FAULT_FLAG = "moon_elf_druid_light_fault_found"
MOON_ELF_DRUID_REFLECTOR_RESET_FLAG = "moon_elf_druid_reflector_reset"
MOON_ELF_DRUID_FIRST_NURTURE_FLAG = "moon_elf_druid_first_nurture"
MOON_ELF_DRUID_ROOTS_NURTURED_FLAG = "moon_elf_druid_roots_nurtured"
MOON_ELF_DRUID_BED_STABLE_FLAG = "moon_elf_druid_bed_stable"

NERA_VOSS_KEY = "moon_elf_druid_nera_voss"


MOON_ELF_DRUID_QUEST = QuestDefinition(
    key=MOON_ELF_DRUID_QUEST_KEY,
    name="Where the Light Falls",
    style="structured",
    description=(
        "After The Third Chair, a Moon Elf Druid is asked to look at a struggling alpine herb bed on the Wind Terrace. "
        "The leaves resemble disease damage at first, but two viewpoints reveal that a shifted daymirror has been doubling the harsh midday light over the same patch. "
        "The lesson is that care begins with accurate observation: establish what is hurting the plants, correct the ordinary cause first, use Nurture only after the environment is made safe, then wait long enough to see whether the living thing actually responds."
    ),
    objective_steps=(
        ("meet_nera", "From the Wind Terrace, go SOUTH to the Alpine Light Garden and TALK NERA."),
        ("inspect_bed", "EXAMINE STARBELL BED before deciding what kind of care it needs."),
        ("compare_views", "VIEW FROM SHADE BENCH and VIEW FROM WATER STEP. Both views are required."),
        ("check_light", "CHECK LIGHT after comparing the two viewpoints."),
        ("reset_reflector", "RESET DAYMIRROR so the bed is no longer receiving the doubled light."),
        ("nurture_roots", "Use your Druid training carefully with NURTURE ROOTS."),
        ("wait_watch", "WAIT AND WATCH rather than adding more magic immediately."),
        ("return_nera", "TALK NERA after the bed has had time to respond."),
        ("complete", "You learned that nurture without understanding can still become harm: see clearly, correct the cause, help only where help is useful, and then let recovery tell you what happened."),
    ),
)


NERA_VOSS = NpcDefinition(
    key=NERA_VOSS_KEY,
    name="Druid Nera Voss",
    short_description=(
        "a Moon Elf Druid in a sun-faded garden coat, carrying a soil knife, a folded shade cloth, and a slate crowded with watering notes"
    ),
    room_key=MOON_ELF_ALPINE_GARDEN_KEY,
    role="Moon Elf Druid mentor and keeper of the upper terrace gardens",
    dialogue=(
        "Nera rubs a leaf between two fingers. 'Good intentions are not a diagnosis.'",
        "'Care without clarity can still cause harm. A generous mistake is still a mistake.'",
        "'If the plant is telling you something, your first job is not to make it quiet. Your first job is to understand what it is saying.'",
    ),
)


MOON_ELF_ALPINE_GARDEN = RoomDefinition(
    key=MOON_ELF_ALPINE_GARDEN_KEY,
    name="Alpine Light Garden",
    region_key=MOON_ELF_REGION_KEY,
    description=(
        "A sheltered garden terrace steps down from the residential Wind Terrace behind low pale-stone walls. Hardy alpine herbs, dwarf berry shrubs, silver grasses, and blue starbell flowers grow in narrow beds fed by a small cistern and drip channels. "
        "Adjustable daymirrors mounted along the outer wall redirect limited morning light into shaded corners during the colder months, while sliding cloth screens soften the harsher midday sun. One starbell bed near the center looks noticeably worse than its neighbors: several leaves are pale, curled, and blotched along their upper surfaces. "
        "Nothing here is sacred or ceremonial. It is a neighborhood garden where medicine herbs, tea plants, food, and flowers share the same practical care."
    ),
    exits={"north": MOON_ELF_WIND_TERRACE_KEY},
    npc_keys=(NERA_VOSS_KEY,),
    tags=("safe", "moon_elf_start", "druid", "garden", "alpine", "civic_work", "perspective", "ordinary_care"),
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


def moon_elf_druid_augmentations() -> dict[str, RoomAugmentation]:
    both_views = ViewCondition(required_flags=(MOON_ELF_DRUID_SHADE_VIEW_FLAG, MOON_ELF_DRUID_PATH_VIEW_FLAG))
    fault_found = ViewCondition(required_flags=(MOON_ELF_DRUID_LIGHT_FAULT_FLAG,))
    reflector_reset = ViewCondition(required_flags=(MOON_ELF_DRUID_REFLECTOR_RESET_FLAG,))
    nurtured = ViewCondition(required_flags=(MOON_ELF_DRUID_ROOTS_NURTURED_FLAG,))
    stable = ViewCondition(required_flags=(MOON_ELF_DRUID_BED_STABLE_FLAG,))
    not_stable = ViewCondition(forbidden_flags=(MOON_ELF_DRUID_BED_STABLE_FLAG,))

    return {
        MOON_ELF_ALPINE_GARDEN_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    MOON_ELF_WIND_TERRACE_KEY,
                    "Wind Terrace",
                    travel_text="You climb north from the sheltered garden beds to the residential Wind Terrace.",
                ),
            ),
            features=(
                _feature(
                    "alpine_starbells",
                    "Struggling Starbell Bed",
                    "a bed of blue alpine starbells with pale, curling leaves concentrated on the upper sides",
                    "The plants are alive and their stems remain firm. The damage is uneven: the upper leaf faces are pale and dry while shaded lower growth is much healthier. A few blotches resemble fungal stress at first glance, but there is no obvious fuzz, rot, soft stem tissue, or spreading edge between neighboring plants.",
                    ("starbells", "starbell bed", "bed", "flowers", "plants", "herb bed"),
                    condition=not_stable,
                ),
                _feature(
                    "alpine_shade_bench",
                    "Shade Bench",
                    "a low stone bench beneath a fixed awning on the garden's inner side",
                    "From the bench, the damaged leaves are seen mostly against the damp soil and shaded wall. Their pale mottling looks plausibly like disease, especially if the observer focuses only on the leaves themselves.",
                    ("shade bench", "bench", "inner bench", "shade view"),
                ),
                _feature(
                    "alpine_water_step",
                    "Water Step",
                    "a narrow service step beside the cistern where the whole bed and outer wall can be seen together",
                    "From here, a hard stripe of reflected light crosses the struggling bed even though the sun itself is partly screened. The same stripe misses the healthier neighboring plants by several feet.",
                    ("water step", "step", "cistern step", "outer view", "water view"),
                ),
                _feature(
                    "alpine_double_light",
                    "Doubled Light Path",
                    "a bright reflected band crossing the starbells from a slightly shifted daymirror",
                    "With both viewpoints compared, the pattern is difficult to miss. The direct midday sun is already reaching the bed through the normal screen, while one daymirror is adding a second concentrated band across the same leaves. The upper surfaces are heat-stressed and the top layer of soil is drying faster than the roots below can replace the moisture.",
                    ("light", "light path", "reflected light", "double light", "sunlight", "reflection"),
                    condition=both_views,
                ),
                _feature(
                    "alpine_shifted_daymirror",
                    "Shifted Daymirror",
                    "a hand-sized polished reflector whose seasonal angle has slipped toward the starbell bed",
                    "The mirror itself is intact. Its simple locking tooth is sitting one notch outside the autumn mark, probably after repeated wind vibration. Resetting it to the engraved seasonal mark will send the borrowed light back toward the shaded herb shelf it was meant to serve.",
                    ("daymirror", "mirror", "reflector", "shifted mirror", "garden mirror"),
                    condition=fault_found,
                ),
                _feature(
                    "alpine_reset_daymirror",
                    "Reset Daymirror",
                    "the garden reflector resting on its correct seasonal mark and no longer doubling light over the starbells",
                    "The reflected band now falls across the intended shaded herb shelf. The starbell bed is receiving ordinary high-altitude daylight again, which is the condition it should have had before any magical care was considered.",
                    ("daymirror", "mirror", "reflector", "reset mirror"),
                    condition=reflector_reset,
                ),
                _feature(
                    "alpine_nurtured_roots",
                    "Nurtured Starbell Roots",
                    "the stressed bed cooling in even shade after a small pulse of Druidic support through the root zone",
                    "Nurture has not erased the pale leaves or made the flowers spring upright. It has eased the root stress and helped the plants hold moisture while the environment returns to normal. The visible damage remains useful evidence of what happened.",
                    ("roots", "starbell roots", "nurtured roots", "root zone", "bed"),
                    condition=nurtured,
                ),
                _feature(
                    "alpine_stable_bed",
                    "Stabilizing Starbell Bed",
                    "the starbells resting in cooler soil with their newest leaves no longer curling tighter",
                    "The old pale patches remain, but the newest leaf edges have relaxed and the soil surface is holding moisture evenly. Recovery is beginning slowly enough to be believable. Nothing has been magically restored to an untouched state.",
                    ("stable bed", "stabilizing bed", "starbells", "bed", "plants"),
                    condition=stable,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "alpine_garden_lived_in",
                    "Water ticks through a narrow stone channel. A basket of clipped herbs waits beside the cistern, and somebody has left two cups under the shade awning for the next person on watering duty.",
                    priority=40,
                ),
                DescriptionLayer(
                    "alpine_garden_views_compared",
                    "Seen from both sides, the apparent disease pattern lines up less with neighboring plants than with a stripe of misplaced reflected light.",
                    priority=60,
                    condition=both_views,
                ),
                DescriptionLayer(
                    "alpine_garden_reflector_fixed",
                    "The harsh reflected stripe is gone. The damaged bed is still damaged, but at least it is no longer being asked to recover inside the condition that hurt it.",
                    priority=70,
                    condition=reflector_reset,
                ),
                DescriptionLayer(
                    "alpine_garden_stable",
                    "The starbells are not suddenly perfect. They are simply cooler, better hydrated, and no longer worsening. In a garden, that can be enough evidence for one afternoon.",
                    priority=90,
                    condition=stable,
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


def _patch_wind_terrace() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_WIND_TERRACE_KEY]
    exits = dict(original.exits)
    exits["south"] = MOON_ELF_ALPINE_GARDEN_KEY
    description = original.description
    if "Alpine Light Garden" not in description:
        description += (
            " A short stair descends south into the Alpine Light Garden, where neighborhood beds use screens and adjustable daymirrors to manage the severe high-altitude sun."
        )
    return replace(original, exits=exits, description=description)


def install_moon_elf_druid_content(world_service=None) -> None:
    if MOON_ELF_DRUID_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_DRUID_QUEST,)
    quests.QUESTS_BY_KEY[MOON_ELF_DRUID_QUEST.key] = MOON_ELF_DRUID_QUEST

    _replace_room(MOON_ELF_ALPINE_GARDEN)
    _replace_npc(NERA_VOSS)
    wind_terrace = _patch_wind_terrace()
    _replace_room(wind_terrace)

    if world_service is None:
        return

    world_service.legacy_rooms[MOON_ELF_ALPINE_GARDEN_KEY] = MOON_ELF_ALPINE_GARDEN
    world_service.legacy_rooms[MOON_ELF_WIND_TERRACE_KEY] = wind_terrace
    world_service.augmentations.update(moon_elf_druid_augmentations())

    base = world_service.augmentations.get(MOON_ELF_WIND_TERRACE_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "south"]
    exits.append(
        ExitDefinition(
            "south",
            MOON_ELF_ALPINE_GARDEN_KEY,
            "Alpine Light Garden",
            travel_text="You descend the short south stair from the Wind Terrace into the sheltered alpine garden beds.",
        )
    )
    world_service.augmentations[MOON_ELF_WIND_TERRACE_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(MOON_ELF_ALPINE_GARDEN_KEY, None)
        cache.pop(MOON_ELF_WIND_TERRACE_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "moon_elf" and character.character_class == "druid")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, MOON_ELF_DRUID_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_druid_start(session) -> bool:
    if not _qualifies(session):
        return False
    if MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "meet_nera")
    return True


def _in_garden(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == MOON_ELF_ALPINE_GARDEN_KEY)


async def _talk_nera(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session):
        return False
    step = quest.get("current_step")

    if step == "meet_nera":
        session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "inspect_bed")
        await session.send(
            "\r\nNera kneels beside the pale leaves but does not touch them again.\r\n"
            "'Three people have already told me fungus. They may be right. Before I treat the answer, I would like you to look at the question.'\r\n"
            "She points to the blue flowers. 'EXAMINE STARBELL BED.'\r\n"
        )
        return True

    if step == "return_nera":
        session.database.complete_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY)
        session.database.grant_flag(session.character.id, MOON_ELF_DRUID_COMPLETE_FLAG)
        await session.send(
            "\r\nNera presses two fingers into the soil, then checks the newest leaf rather than the oldest scar.\r\n"
            "'Good. The old damage is still there. That means we still have evidence. The new growth is no longer tightening, which means the bed has stopped losing ground.'\r\n"
            "She folds the shade cloth over one arm. 'You corrected the light before you strengthened the roots. That order matters.'\r\n"
            "'Care without clarity can still cause harm. Druidry is not the art of helping as hard as possible. It is the discipline of learning what help actually means here.'\r\n"
            "She glances up at the reset daymirror. 'See clearly. Change the cause when you can. Offer support when it is useful. Then give the living thing enough time to answer for itself.'\r\n"
            "\r\nQuest complete: Where the Light Falls.\r\n"
        )
        return True

    objective = MOON_ELF_DRUID_QUEST.objective_for_step(step)
    await session.send("\r\nNera nods toward the bed. 'Stay with what you can actually observe.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_bed(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session) or quest.get("current_step") != "inspect_bed":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_DRUID_BED_INSPECTED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "compare_views")
    await session.send(
        "\r\nThe upper leaf faces are pale, curled, and blotched, but the stems are firm and the shaded lower growth is healthier. You find no soft rot, spreading fuzz, collapsed stem tissue, or clear boundary moving from plant to plant.\r\n"
        "Nera says, 'Disease is still possible. So is something else. Look at the bed from where the garden itself changes. VIEW FROM SHADE BENCH and VIEW FROM WATER STEP.'\r\n"
    )
    return True


async def _view_garden(session, which: str) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session) or quest.get("current_step") != "compare_views":
        return False

    flag = MOON_ELF_DRUID_SHADE_VIEW_FLAG if which == "shade" else MOON_ELF_DRUID_PATH_VIEW_FLAG
    session.database.grant_flag(session.character.id, flag)

    if which == "shade":
        await session.send(
            "\r\nFrom the shade bench, the damaged leaves dominate the view. Against damp soil and the cool inner wall, the pale mottling really could be mistaken for a disease pattern. Nothing from this angle disproves that first diagnosis.\r\n"
        )
    else:
        await session.send(
            "\r\nFrom the water step, the whole terrace lines up differently. A sharp stripe of reflected light crosses the sickest plants even though the normal sun screen is already filtering the midday glare. The healthier neighboring bed sits just outside that stripe.\r\n"
        )

    flags = _flags(session)
    if {MOON_ELF_DRUID_SHADE_VIEW_FLAG, MOON_ELF_DRUID_PATH_VIEW_FLAG}.issubset(flags):
        session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "check_light")
        await session.send(
            "Nera follows your eyes instead of supplying the answer. 'One view made disease plausible. The other gave us a competing explanation. CHECK LIGHT.'\r\n"
        )
    else:
        await session.send("Nera says, 'Useful. Now take the other view before you decide what it means.'\r\n")
    return True


async def _check_light(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session) or quest.get("current_step") != "check_light":
        return False
    flags = _flags(session)
    if not {MOON_ELF_DRUID_SHADE_VIEW_FLAG, MOON_ELF_DRUID_PATH_VIEW_FLAG}.issubset(flags):
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_DRUID_LIGHT_FAULT_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "reset_reflector")
    await session.send(
        "\r\nYou trace the bright band backward to a daymirror on the outer wall. Its locking tooth has slipped one notch beyond the seasonal mark. The bed has been receiving ordinary midday sun and a second concentrated reflection at the same time.\r\n"
        "The leaf pattern now makes sense without inventing a disease: heat on the upper surfaces, fast evaporation at the soil line, healthier growth beneath.\r\n"
        "Nera says, 'Good. Do not heal a plant while leaving the thing hurting it in place. RESET DAYMIRROR.'\r\n"
    )
    return True


async def _reset_daymirror(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session) or quest.get("current_step") != "reset_reflector":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_DRUID_REFLECTOR_RESET_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "nurture_roots")
    await session.send(
        "\r\nYou release the simple locking catch, return the daymirror to its engraved seasonal mark, and seat the tooth firmly. The hard stripe slides away from the starbells and settles onto the shaded herb shelf it was designed to illuminate.\r\n"
        "The leaves are still pale. Fixing the cause does not pretend the damage never happened.\r\n"
        "Nera touches the cooler soil. 'Now support what is recovering, not what you imagined was wrong. NURTURE ROOTS.'\r\n"
    )
    return True


async def _nurture_roots(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session):
        return False
    step = quest.get("current_step")

    if step != "nurture_roots":
        if step in {"inspect_bed", "compare_views", "check_light", "reset_reflector"}:
            await session.send(
                "\r\nNera lifts one hand. 'Not yet. Care is not more accurate because it is generous. Establish the cause before you strengthen a system that may still be under the same stress.'\r\n"
            )
            return True
        if step in {"wait_watch", "return_nera"}:
            await session.send(
                "\r\nNera shakes her head gently. 'You already gave the roots support. More magic would make it harder to learn whether the corrected environment was enough. Watch now.'\r\n"
            )
            return True
        return False

    flags = _flags(session)
    if MOON_ELF_DRUID_REFLECTOR_RESET_FLAG not in flags:
        await session.send("\r\nThe light problem is still active. Correct the environment before using Nurture.\r\n")
        return True
    if MOON_ELF_DRUID_FIRST_NURTURE_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "nurture", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, MOON_ELF_DRUID_FIRST_NURTURE_FLAG)
    session.database.grant_flag(session.character.id, MOON_ELF_DRUID_ROOTS_NURTURED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "wait_watch")
    await session.send(
        "\r\nYou place your hands near the root zone and let Nurture move through the bed as a small steady encouragement rather than a command. Moisture holds more evenly through the fine roots; the plants' strained tissues ease without erasing the pale leaves that record the damage.\r\n"
        "Nothing blooms on cue. Nothing becomes perfect.\r\n"
        "Nera sits back on her heels. 'Good. Now the difficult part for anyone with a useful spell: stop. WAIT AND WATCH.'\r\n"
    )
    return True


async def _wait_and_watch(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_garden(session) or quest.get("current_step") != "wait_watch":
        return False
    if MOON_ELF_DRUID_ROOTS_NURTURED_FLAG not in _flags(session):
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_DRUID_BED_STABLE_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_DRUID_QUEST_KEY, "return_nera")
    await session.send(
        "\r\nYou wait through an ordinary stretch of garden work. Nera trims another bed. Someone comes down for mint. Water moves through the drip channel one slow measure at a time.\r\n"
        "When you check the starbells again, the old pale patches remain, but the newest leaves are no longer curling tighter. The topsoil is cooler and holding moisture at the same rate as the neighboring bed. Recovery has begun by becoming less dramatic.\r\n"
        "Nera nods. 'That is enough evidence for today. TALK NERA.'\r\n"
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


def install_moon_elf_druid_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Moon Elf Druid extension after The Third Chair."""
    if getattr(player_session_class, "_moon_elf_druid_runtime_installed", False):
        return

    install_moon_elf_druid_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_druid_start(self):
            await self.send(
                "\r\nA garden runner catches you on the Wind Terrace with a soil-marked note from Druid Nera Voss.\r\n"
                "'One of the starbell beds is failing. Nera says several people already have an answer, so she would like one more person to look before anybody treats it.'\r\n"
                "'Alpine Light Garden, south from the Wind Terrace.'\r\n"
                "\r\nNew quest: Where the Light Falls.\r\n"
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
        if normalized in {"talk nera", "talk druid nera", "talk nera voss", "talk druid nera voss"}:
            handled = await _talk_nera(self)
        elif normalized in {
            "examine starbell bed", "inspect starbell bed", "look starbell bed", "examine starbells",
            "inspect starbells", "examine bed", "inspect bed", "look at starbells"
        }:
            handled = await _inspect_bed(self)
        elif normalized in {"view from shade bench", "view shade bench", "view from bench", "check shade bench", "sight shade bench"}:
            handled = await _view_garden(self, "shade")
        elif normalized in {"view from water step", "view water step", "view from step", "check water step", "sight water step"}:
            handled = await _view_garden(self, "path")
        elif normalized in {"check light", "examine light", "trace light", "inspect light", "check reflected light", "trace reflection"}:
            handled = await _check_light(self)
        elif normalized in {"reset daymirror", "adjust daymirror", "reset mirror", "adjust mirror", "reset reflector", "adjust reflector"}:
            handled = await _reset_daymirror(self)
        elif normalized in {
            "nurture roots", "nurture starbells", "nurture bed", "cast nurture roots",
            "use nurture roots", "use nurture on roots", "nurture root zone"
        }:
            handled = await _nurture_roots(self)
        elif normalized in {"wait and watch", "wait watch", "watch bed", "wait for bed", "observe recovery"}:
            handled = await _wait_and_watch(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_druid_start(self):
            await self.send(
                "\r\nWith The Third Chair behind you, a garden runner finds you with a soil-marked note.\r\n"
                "'Druid Nera Voss wants another pair of eyes on a failing starbell bed before anyone treats it. Alpine Light Garden, south from the Wind Terrace.'\r\n"
                "\r\nNew quest: Where the Light Falls.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_druid_runtime_installed = True
