from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.mechanics as mechanics
import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_nurture import (
    FOREST_ELF_HEARTSEED_BLOOMED_FLAG,
    FOREST_ELF_HEARTSEED_QUEST,
    FOREST_ELF_HEARTSEED_TENDED_FLAG,
    FOREST_ELF_NURTURE_COMPLETE_FLAG,
    SILVERMOSS_SPRIG,
)
from mud.mechanics import AbilityDefinition
from mud.quests import QuestDefinition
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import FOREST_ELF_START_ROOM_KEY, NpcDefinition, RoomDefinition


FOREST_ELF_GREENWAY_KEY = "forest_elf_greenway"
FOREST_ELF_KEEPER_NURSERY_KEY = "forest_elf_keeper_nursery"
FOREST_ELF_RAINPOOL_TERRACE_KEY = "forest_elf_rainpool_terrace"
FOREST_ELF_SEEPSTONE_RUN_KEY = "forest_elf_seepstone_run"
FOREST_ELF_OVERGROWTH_HOLLOW_KEY = "forest_elf_overgrowth_hollow"

FOREST_ELF_STEWARDSHIP_ROOM_KEYS = (
    FOREST_ELF_KEEPER_NURSERY_KEY,
    FOREST_ELF_RAINPOOL_TERRACE_KEY,
    FOREST_ELF_SEEPSTONE_RUN_KEY,
    FOREST_ELF_OVERGROWTH_HOLLOW_KEY,
)

FOREST_ELF_RAIN_QUEST_KEY = "forest_elf_rainpool_balance"
FOREST_ELF_RAIN_CHANNEL_ADJUSTED_FLAG = "forest_elf_rain_channel_adjusted"
FOREST_ELF_RAIN_BALANCED_FLAG = "forest_elf_rainpool_balance_restored"

DRUID_FIRST_QUEST_KEY = "druid_circle_living_answer"
DRUID_FALSE_BLIGHT_QUEST_KEY = "druid_circle_false_blight"
DRUID_NURTURE_FIRST_USE_FLAG = "druid_nurture_first_use"
DRUID_NURSERY_TENDED_FLAG = "druid_nursery_runner_tended"
DRUID_NURSERY_ANSWERED_FLAG = "druid_nursery_runner_answered"
DRUID_CIRCLE_FIRST_LESSON_FLAG = "druid_circle_first_lesson"
DRUID_FALSE_BLIGHT_DIAGNOSED_FLAG = "druid_false_blight_diagnosed"
DRUID_OVERGROWTH_STABILIZED_FLAG = "druid_overgrowth_stabilized"
DRUID_FALSE_BLIGHT_COMPLETE_FLAG = "druid_false_blight_complete"


NURTURE_ABILITY = AbilityDefinition(
    key="nurture",
    name="Nurture",
    unlock_level=1,
    mana_cost=0,
    cooldown_seconds=0.0,
    description=(
        "A contextual Druid utility that encourages an already-living system to recover, settle, or strengthen. "
        "Nurture does not create life, replace diagnosis, or force unhealthy growth."
    ),
    category="nature_utility",
    design_status="approved_initial_identity",
)


RAINPOOL_BALANCE_QUEST = QuestDefinition(
    key=FOREST_ELF_RAIN_QUEST_KEY,
    name="What the Rain Remembers",
    style="structured",
    description=(
        "Keeper Sela Rainbough asks a new Forest Elf to trace why the Circle's teaching rain pools are filling unevenly. "
        "The lesson is about following water, identifying the smallest useful intervention, and refusing to over-correct a living system."
    ),
    objective_steps=(
        ("inspect_pools", "Go north from the Greenway to Rainpool Terrace and EXAMINE RAIN POOLS."),
        ("trace_runoff", "Follow the terrace east to Seepstone Run and EXAMINE LEAF DAM."),
        ("adjust_flow", "CLEAR LEAF DAM carefully enough to reopen one channel without stripping the whole seep."),
        ("listen_flow", "LISTEN WATER at Seepstone Run and confirm that the restored channel is moving naturally."),
        ("return_sela", "Return to the Greenway and TALK SELA."),
        ("complete", "You restored the rain-pool flow with the smallest useful change."),
    ),
)


DRUID_LIVING_ANSWER_QUEST = QuestDefinition(
    key=DRUID_FIRST_QUEST_KEY,
    name="The Living Answer",
    style="structured",
    description=(
        "Druid Aven Rootwake uses a nursery runner to teach the class skill Nurture. "
        "The Druid must observe first, offer a measured living impulse, and then wait for the plant to answer in its own time."
    ),
    objective_steps=(
        ("inspect_runner", "In Keeper's Nursery, EXAMINE TEACHING RUNNER before using magic."),
        ("nurture_runner", "Use NURTURE RUNNER after you understand what the plant needs."),
        ("wait_runner", "WAIT and let the runner decide what to do with the help you gave it."),
        ("return_aven", "TALK AVEN after the runner responds."),
        ("complete", "You practiced Nurture as assistance rather than command."),
    ),
)


DRUID_FALSE_BLIGHT_QUEST = QuestDefinition(
    key=DRUID_FALSE_BLIGHT_QUEST_KEY,
    name="Green Without Illness",
    style="structured",
    description=(
        "A dark vine has engulfed a storm-damaged sapling in Overgrowth Hollow. It resembles an invasive blight at first glance. "
        "Aven asks the Druid to determine what is actually happening before choosing whether anything should be removed."
    ),
    objective_steps=(
        ("inspect_overgrowth", "Go north from Keeper's Nursery and EXAMINE OVERGROWTH."),
        ("inspect_host", "EXAMINE SAPLING and compare the host tree's condition with the vine."),
        ("diagnose", "DIAGNOSE OVERGROWTH before attempting to cut or heal anything."),
        ("nurture_host", "NURTURE SAPLING without removing the living bracevine."),
        ("wait_response", "WAIT and observe whether host and vine settle together."),
        ("return_aven", "Return south to Keeper's Nursery and TALK AVEN."),
        ("complete", "You recognized a protective relationship that only looked like disease."),
    ),
)


SELA_RAINBOUGH = NpcDefinition(
    key="forest_elf_keeper_sela_rainbough",
    name="Keeper Sela Rainbough",
    short_description="a mud-kneed water keeper carrying reed markers, a hand level, and no spell focus at all",
    room_key=FOREST_ELF_GREENWAY_KEY,
    role="non-Druid Circle water steward and Forest Elf starter mentor",
    dialogue=(
        "Sela taps the mud from a reed marker. 'Water does not need a wizard. Most days it needs someone willing to find out where it stopped going.'",
        "'The Circle has Druids, growers, healers, path wardens, seed keepers, and people like me who spend embarrassing amounts of time staring at drainage.'",
    ),
)


AVEN_ROOTWAKE = NpcDefinition(
    key="forest_elf_druid_aven_rootwake",
    name="Druid Aven Rootwake",
    short_description="a quiet Druid instructor pruning dead tips from a nursery runner one careful cut at a time",
    room_key=FOREST_ELF_KEEPER_NURSERY_KEY,
    role="Druid class mentor and Circle adviser",
    dialogue=(
        "Aven turns a leaf over rather than looking at its top. 'Druidry is not the art of making green things obey you.'",
        "'Nurture is useful because it is small. If you cannot tell whether a living thing needs help, more power only gives you a larger mistake.'",
    ),
)


FOREST_ELF_STEWARDSHIP_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=FOREST_ELF_KEEPER_NURSERY_KEY,
        name="Keeper's Nursery",
        region_key="great_elf_forest",
        description=(
            "A low woven fence encloses a nursery beneath a carefully thinned canopy east of Circle Clearing. Seedlings, rooted cuttings, storm-damaged saplings, and medicinal groundcover share beds arranged by light and moisture rather than by species. "
            "Small wooden tags record who tended each plant and what was changed, including many entries that simply say LEFT ALONE. A narrow path runs north toward a shaded training hollow used by the Circle's Druids."
        ),
        exits={"west": FOREST_ELF_START_ROOM_KEY, "north": FOREST_ELF_OVERGROWTH_HOLLOW_KEY},
        npc_keys=(AVEN_ROOTWAKE.key,),
        tags=("safe", "forest_town", "nursery", "druid_training", "stewardship"),
    ),
    RoomDefinition(
        key=FOREST_ELF_RAINPOOL_TERRACE_KEY,
        name="Rainpool Terrace",
        region_key="great_elf_forest",
        description=(
            "Three shallow stone-and-root basins step down a ferny slope north of the Greenway. They catch roof runoff and hillside rain before releasing it slowly toward the river system. "
            "The pools are practical teaching infrastructure: frogs use them, birds drink from them, and young keepers learn that the shape of a watershed can matter more than the amount of water in it. A narrow seep path follows the overflow east."
        ),
        exits={"south": FOREST_ELF_GREENWAY_KEY, "east": FOREST_ELF_SEEPSTONE_RUN_KEY},
        tags=("safe", "water", "rainpool", "stewardship", "forest_town_edge"),
    ),
    RoomDefinition(
        key=FOREST_ELF_SEEPSTONE_RUN_KEY,
        name="Seepstone Run",
        region_key="great_elf_forest",
        description=(
            "A ribbon of shallow water threads between slate-colored stones under alder roots. Fallen leaves and small branches naturally collect in bends, forming temporary dams that spread moisture through the soil before the overflow continues downhill. "
            "Nothing here is engineered to stay fixed forever. The keepers intervene only when a temporary blockage begins starving one part of the slope while drowning another."
        ),
        exits={"west": FOREST_ELF_RAINPOOL_TERRACE_KEY},
        tags=("safe", "water", "runoff", "stewardship", "observation"),
    ),
    RoomDefinition(
        key=FOREST_ELF_OVERGROWTH_HOLLOW_KEY,
        name="Overgrowth Hollow",
        region_key="great_elf_forest",
        description=(
            "A shaded hollow lies just north of the nursery behind a screen of hazel. One young oak has been nearly hidden beneath a mass of dark green bracevine. At a glance the growth looks aggressive: overlapping leaves, thick stems, and tendrils wrapped around the trunk. "
            "Closer inspection is clearly expected here. Training slates hang from a post, all blank except for one repeated instruction: NAME THE RELATIONSHIP BEFORE YOU NAME THE REMEDY."
        ),
        exits={"south": FOREST_ELF_KEEPER_NURSERY_KEY},
        tags=("safe", "druid_training", "diagnosis", "overgrowth", "subtle_magic"),
    ),
)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    touch: str = "",
    listen: str = "",
    condition: ViewCondition | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
        condition=condition or ViewCondition(),
    )


def _exit(direction: str, destination: str, name: str, text: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, **kwargs)


def forest_elf_stewardship_augmentations() -> dict[str, RoomAugmentation]:
    rain_unbalanced = ViewCondition(forbidden_flags=(FOREST_ELF_RAIN_BALANCED_FLAG,))
    rain_balanced = ViewCondition(required_flags=(FOREST_ELF_RAIN_BALANCED_FLAG,))
    channel_blocked = ViewCondition(forbidden_flags=(FOREST_ELF_RAIN_CHANNEL_ADJUSTED_FLAG,))
    channel_open = ViewCondition(required_flags=(FOREST_ELF_RAIN_CHANNEL_ADJUSTED_FLAG,))
    runner_untended = ViewCondition(forbidden_flags=(DRUID_NURSERY_TENDED_FLAG,))
    runner_tended = ViewCondition(
        required_flags=(DRUID_NURSERY_TENDED_FLAG,),
        forbidden_flags=(DRUID_NURSERY_ANSWERED_FLAG,),
    )
    runner_answered = ViewCondition(required_flags=(DRUID_NURSERY_ANSWERED_FLAG,))
    overgrowth_unsettled = ViewCondition(forbidden_flags=(DRUID_OVERGROWTH_STABILIZED_FLAG,))
    overgrowth_settled = ViewCondition(required_flags=(DRUID_OVERGROWTH_STABILIZED_FLAG,))

    return {
        FOREST_ELF_START_ROOM_KEY: RoomAugmentation(
            extra_exits=(
                _exit("east", FOREST_ELF_KEEPER_NURSERY_KEY, "Keeper's Nursery", "You follow a bark-chip path east into the Circle's nursery beds."),
            ),
            features=(
                _feature(
                    "keeper_roster",
                    "Circle Keeper Roster",
                    "a living-wood board listing the current keepers and the work each one is responsible for",
                    (
                        "The Circle is not a Druid order. Its seats include water keepers, growers, healers, path wardens, seed keepers, and several Druids whose magic makes them influential advisers on living systems. "
                        "Decisions are recorded beside the name of the keeper responsible for carrying them out."
                    ),
                    aliases=("roster", "keeper roster", "circle roster", "keepers", "circle of keepers"),
                ),
            ),
        ),
        FOREST_ELF_GREENWAY_KEY: RoomAugmentation(
            extra_exits=(
                _exit("north", FOREST_ELF_RAINPOOL_TERRACE_KEY, "Rainpool Terrace", "You leave the main Greenway along a damp keeper's path climbing toward the rain pools."),
            ),
            features=(
                _feature(
                    "water_keeper_markers",
                    "Water-Keeper Markers",
                    "reed stakes showing recent pool depths and drainage checks",
                    "The marks are mundane and precise: water depth, last overflow, silt height, frog spawn observed, channel checked. Nothing about the work requires spellcasting to matter.",
                    aliases=("reed markers", "water markers", "markers", "rain markers"),
                ),
            ),
        ),
        FOREST_ELF_KEEPER_NURSERY_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", FOREST_ELF_START_ROOM_KEY, "Circle Clearing", "You leave the nursery by the bark-chip path and return to the Circle stones."),
                ExitDefinition(
                    direction="north",
                    destination_key=FOREST_ELF_OVERGROWTH_HOLLOW_KEY,
                    name="Overgrowth Hollow",
                    travel_text="Aven's training path leads north through hazel into Overgrowth Hollow.",
                    failure_text="The shaded training hollow is reserved for Druids working under the Circle's instruction.",
                    condition=ViewCondition(classes=("druid",)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                _feature(
                    "teaching_runner_fresh",
                    "Teaching Runner",
                    "a healthy creeping runner with one bruised node held just above damp soil",
                    "The runner is alive and vigorous. One node was bent during transplanting and has not decided whether to root or abandon that segment. It needs support, not healing from disease.",
                    aliases=("runner", "teaching runner", "vine runner", "nursery runner"),
                    touch="The bruised node is flexible and cool. There is no rot or heat around it.",
                    condition=runner_untended,
                ),
                _feature(
                    "teaching_runner_tended",
                    "Listening Runner",
                    "the teaching runner resting with its bruised node against damp soil",
                    "The runner has been given a quiet Nurture impulse, but no new root has appeared yet. The useful thing to do now is wait.",
                    aliases=("runner", "teaching runner", "vine runner", "nursery runner"),
                    condition=runner_tended,
                ),
                _feature(
                    "teaching_runner_answered",
                    "Rooted Teaching Runner",
                    "the teaching runner holding a single new white root into the nursery soil",
                    "The plant answered modestly: one small root now anchors the bruised node. The rest of the runner looks exactly as it did before, which is precisely the point of the lesson.",
                    aliases=("runner", "teaching runner", "vine runner", "nursery runner"),
                    condition=runner_answered,
                ),
                _feature(
                    "druid_workbench",
                    "Druid Workbench",
                    "a plain outdoor bench holding lenses, bark samples, water dishes, and pruning knives",
                    "Most of the tools are diagnostic rather than magical. Hand lenses, pH stones, sample envelopes, and clean knives suggest that the Circle expects Druids to observe physical causes before reaching for power.",
                    aliases=("bench", "workbench", "druid bench", "tools"),
                    condition=ViewCondition(classes=("druid",)),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "nursery_druid_recognition",
                    "As a Druid, you recognize the nursery as a place for class practice as much as ordinary plant care; Aven watches for restraint more than spectacle.",
                    priority=60,
                    condition=ViewCondition(classes=("druid",)),
                ),
            ),
        ),
        FOREST_ELF_RAINPOOL_TERRACE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", FOREST_ELF_GREENWAY_KEY, "The Greenway", "You descend from the rain pools to the broad Greenway."),
                _exit("east", FOREST_ELF_SEEPSTONE_RUN_KEY, "Seepstone Run", "You follow the uneven overflow east between alder roots."),
            ),
            features=(
                _feature(
                    "uneven_rain_pools",
                    "Uneven Rain Pools",
                    "three teaching pools whose waterlines no longer match the keeper stakes",
                    "The upper pool is lower than its recent water marks while the middle basin is overfull. Wet moss above both lines proves water arrived here recently; the imbalance is downstream routing, not simple drought.",
                    aliases=("rain pools", "pools", "upper pool", "basins", "water"),
                    search="A thin trail of wet leaves leads toward the eastern overflow rather than toward the normal lower channel.",
                    condition=rain_unbalanced,
                ),
                _feature(
                    "balanced_rain_pools",
                    "Balanced Rain Pools",
                    "three shallow basins sharing runoff evenly again",
                    "Each pool now sits close to its keeper mark. Water enters, pauses, and leaves slowly enough that no basin is being starved or drowned.",
                    aliases=("rain pools", "pools", "upper pool", "basins", "water"),
                    condition=rain_balanced,
                ),
            ),
        ),
        FOREST_ELF_SEEPSTONE_RUN_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", FOREST_ELF_RAINPOOL_TERRACE_KEY, "Rainpool Terrace", "You follow Seepstone Run west back toward the teaching pools."),
            ),
            features=(
                _feature(
                    "leaf_dam_blocked",
                    "Leaf Dam",
                    "a natural leaf-and-branch dam that has packed too tightly across one fork of the seep",
                    "The dam itself is normal habitat, not a defect. The problem is one thumb-thick branch wedged across the lower fork, forcing almost all runoff into the middle pool's channel. Removing the whole dam would dry the surrounding soil; freeing that one branch should be enough.",
                    aliases=("leaf dam", "dam", "blockage", "branch", "runoff"),
                    touch="The wedged branch is firm but movable. The rest of the leaf mat is soft and full of small invertebrates.",
                    condition=channel_blocked,
                ),
                _feature(
                    "leaf_dam_opened",
                    "Opened Seep Fork",
                    "the same natural leaf dam with one lower channel gently reopened",
                    "Most of the leaf mat remains exactly where it formed. A narrow stream now slips beneath the loosened branch and divides the runoff between both forks.",
                    aliases=("leaf dam", "dam", "channel", "opened fork", "runoff"),
                    listen="Two quiet water notes overlap now instead of one louder rush through the upper fork.",
                    condition=channel_open,
                ),
            ),
        ),
        FOREST_ELF_OVERGROWTH_HOLLOW_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", FOREST_ELF_KEEPER_NURSERY_KEY, "Keeper's Nursery", "You leave the shaded training hollow and return to the nursery."),
            ),
            features=(
                _feature(
                    "bracevine_tangle",
                    "Bracevine Tangle",
                    "a dark mass of living vine wrapped densely around a young oak",
                    "The vine looks alarming from a distance, but its leaves are evenly colored rather than spotted, its stems are supple rather than brittle, and no sour fungal smell rises from the bark. Several tendrils cross the trunk exactly where the oak was split by an old storm.",
                    aliases=("overgrowth", "vine", "bracevine", "tangle", "dark vine"),
                    search="Beneath the outer leaves, the vine is not penetrating healthy bark. It is spanning the storm split and anchoring into the soil on both sides of the tree.",
                    condition=overgrowth_unsettled,
                ),
                _feature(
                    "storm_split_sapling",
                    "Storm-Split Sapling",
                    "a young oak whose old trunk split is being held surprisingly still by the surrounding vine",
                    "The sapling's leaves show normal color and new growth. Callus tissue is forming along the edges of the old split. The bracevine crosses the wound without feeding from it; the relationship looks structural, not parasitic.",
                    aliases=("sapling", "oak", "tree", "host", "young oak"),
                    touch="The trunk flexes less than you expect. The vine is carrying some of the strain across the split.",
                ),
                _feature(
                    "settled_bracevine",
                    "Settled Bracevine",
                    "bracevine and young oak holding a quiet, stable tension after careful Druidic support",
                    "Nothing has been cut away. The oak's living edge has tightened slightly around the old split while the bracevine remains in place as a flexible natural brace.",
                    aliases=("overgrowth", "vine", "bracevine", "tangle", "sapling", "oak"),
                    condition=overgrowth_settled,
                ),
                _feature(
                    "training_slate",
                    "Diagnosis Slate",
                    "a blank slate beneath the words NAME THE RELATIONSHIP BEFORE YOU NAME THE REMEDY",
                    "Previous chalk has been scrubbed away so each Druid must make the observation independently. The phrase is repeated deeply enough to have become a groove in the wood behind the slate.",
                    aliases=("slate", "training slate", "diagnosis slate", "sign"),
                    condition=ViewCondition(classes=("druid",)),
                ),
            ),
        ),
    }


def _merge_augmentation(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    override_by_direction = {exit_def.direction: exit_def for exit_def in existing.exit_overrides}
    for exit_def in extra.exit_overrides:
        override_by_direction[exit_def.direction] = exit_def
    extra_exit_keys = {(exit_def.direction, exit_def.destination_key): exit_def for exit_def in existing.extra_exits}
    for exit_def in extra.extra_exits:
        extra_exit_keys[(exit_def.direction, exit_def.destination_key)] = exit_def
    feature_by_key = {feature.key: feature for feature in existing.features}
    for feature in extra.features:
        feature_by_key[feature.key] = feature
    layer_by_key = {layer.key: layer for layer in existing.description_layers}
    for layer in extra.description_layers:
        layer_by_key[layer.key] = layer
    return RoomAugmentation(
        exit_overrides=tuple(override_by_direction.values()),
        extra_exits=tuple(extra_exit_keys.values()),
        features=tuple(feature_by_key.values()),
        description_layers=tuple(layer_by_key.values()),
    )


def _patch_existing_room(room_key: str, *, exits: dict[str, str] | None = None, npc_keys: tuple[str, ...] = ()) -> None:
    room = legacy_world.ROOMS_BY_KEY.get(room_key)
    if room is None:
        return
    merged_exits = dict(room.exits)
    if exits:
        merged_exits.update(exits)
    merged_npcs = room.npc_keys + tuple(key for key in npc_keys if key not in room.npc_keys)
    replacement = replace(room, exits=merged_exits, npc_keys=merged_npcs)
    legacy_world.ROOMS = tuple(replacement if value.key == room_key else value for value in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY[room_key] = replacement


def _register_nurture_ability() -> None:
    current = mechanics.FIXED_CLASS_ABILITIES.get("druid", ())
    if any(ability.key == NURTURE_ABILITY.key for ability in current):
        return
    rebuilt: list[AbilityDefinition] = []
    inserted = False
    for ability in current:
        rebuilt.append(ability)
        if ability.key == "forage":
            rebuilt.append(NURTURE_ABILITY)
            inserted = True
    if not inserted:
        rebuilt.insert(0, NURTURE_ABILITY)
    mechanics.FIXED_CLASS_ABILITIES["druid"] = tuple(rebuilt)


def install_forest_elf_stewardship_content(world_service=None) -> None:
    """Register the expanded Circle area, water-stewardship quest, and Druid class arc."""
    _register_nurture_ability()

    _patch_existing_room(
        FOREST_ELF_START_ROOM_KEY,
        exits={"east": FOREST_ELF_KEEPER_NURSERY_KEY},
    )
    _patch_existing_room(
        FOREST_ELF_GREENWAY_KEY,
        exits={"north": FOREST_ELF_RAINPOOL_TERRACE_KEY},
        npc_keys=(SELA_RAINBOUGH.key,),
    )

    known_rooms = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in FOREST_ELF_STEWARDSHIP_ROOMS if room.key not in known_rooms)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    legacy_world.ROOMS_BY_KEY.update({room.key: room for room in FOREST_ELF_STEWARDSHIP_ROOMS})

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    for npc in (SELA_RAINBOUGH, AVEN_ROOTWAKE):
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    for quest in (RAINPOOL_BALANCE_QUEST, DRUID_LIVING_ANSWER_QUEST, DRUID_FALSE_BLIGHT_QUEST):
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    if world_service is not None:
        for room_key in (FOREST_ELF_START_ROOM_KEY, FOREST_ELF_GREENWAY_KEY):
            room = legacy_world.ROOMS_BY_KEY.get(room_key)
            if room is not None:
                world_service.legacy_rooms[room_key] = room
        world_service.legacy_rooms.update({room.key: room for room in FOREST_ELF_STEWARDSHIP_ROOMS})
        for room_key, augmentation in forest_elf_stewardship_augmentations().items():
            world_service.augmentations[room_key] = _merge_augmentation(
                world_service.augmentations.get(room_key), augmentation
            )
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in (
                FOREST_ELF_START_ROOM_KEY,
                FOREST_ELF_GREENWAY_KEY,
                *FOREST_ELF_STEWARDSHIP_ROOM_KEYS,
            ):
                cache.pop(room_key, None)


def _quest(session, quest_key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, quest_key)


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _is_sela(target: str) -> bool:
    return target in {"sela", "keeper sela", "sela rainbough", "water keeper", "water-keeper", "keeper"}


def _is_aven(target: str) -> bool:
    return target in {"aven", "druid aven", "aven rootwake", "druid", "instructor", "druid instructor"}


def _record_nurture(session) -> None:
    assert session.character is not None
    session.database.record_ability_use(session.character.id, NURTURE_ABILITY.key)
    session.database.grant_flag(session.character.id, DRUID_NURTURE_FIRST_USE_FLAG)


def _nurture_target(normalized: str) -> str | None:
    text = normalized.strip()
    for prefix in ("use nurture on ", "cast nurture on ", "use nurture ", "cast nurture ", "nurture "):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    if text == "nurture":
        return ""
    return None


def _forest_elf_heartseed_quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)


async def _druid_nurture_heartseed(session) -> bool:
    assert session.character is not None
    if session.character.character_class != "druid" or session.character.race != "forest_elf":
        return False
    if session.character.current_room != FOREST_ELF_START_ROOM_KEY:
        return False
    quest = _forest_elf_heartseed_quest(session)
    if not quest or quest.get("status") != "active":
        return False
    if quest.get("current_step") != "tend_heartseed":
        await session.send(
            "\r\nYour Druidic sense finds no useful opening for Nurture yet. Maelis's lesson still expects observation before intervention.\r\n"
        )
        return True
    if session.database.item_quantity(session.character.id, SILVERMOSS_SPRIG.key) < 1:
        await session.send("\r\nThe root bed still needs the Silvermoss you were asked to gather before Nurture will help rather than dry it further.\r\n")
        return True

    session.database.consume_item(session.character.id, SILVERMOSS_SPRIG.key, 1)
    session.database.grant_flag(session.character.id, FOREST_ELF_HEARTSEED_TENDED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "wait_for_growth")
    _record_nurture(session)
    await session.send(
        "\r\nYou settle the Silvermoss around the exposed root crown, then use Nurture for the first time in the Circle's formal teaching.\r\n"
        "The ability does not force the cutting to grow. Instead you offer a small, steady living impulse into roots that are already trying to recover, then let the plant decide what to do with it.\r\n"
        "Nurture gains use-based ability progression. The leaves remain curled. Maelis gives you an approving look precisely because you stop there. WAIT beside the Heartseed.\r\n"
    )
    return True


async def _talk_sela(session) -> bool:
    assert session.character is not None
    if session.character.race != "forest_elf":
        await session.send("\r\nSela is friendly, but the rain-pool check is part of the local Forest Elf keeper curriculum rather than a general contract.\r\n")
        return True

    flags = session.database.list_flags(session.character.id)
    if FOREST_ELF_NURTURE_COMPLETE_FLAG not in flags:
        await session.send(
            "\r\nSela glances toward Circle Clearing. 'Maelis has you first. Learn to make one careful change to one living thing before I ask you to follow water across a hillside.'\r\n"
        )
        return True

    quest = _quest(session, RAINPOOL_BALANCE_QUEST.key)
    if quest is None:
        session.database.start_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key, "inspect_pools")
        await session.send(
            "\r\nSela plants two reed markers in the Greenway mud. 'The teaching pools north of here filled unevenly after the last runoff. I could fix them in five minutes. You will learn more if I don't.'\r\n"
            "'Start by looking at the pools. Do not assume low water means drought and do not assume a blockage should be removed completely.'\r\n"
            "New quest: What the Rain Remembers. Go NORTH and EXAMINE RAIN POOLS.\r\n"
        )
        return True

    if quest.get("status") == "completed":
        await session.send("\r\nSela nods at the current water marks. 'Still dividing cleanly. Good. The best repair is often one the next rain can revise without asking us.'\r\n")
        return True

    if quest.get("current_step") == "return_sela":
        session.database.grant_flag(session.character.id, FOREST_ELF_RAIN_BALANCED_FLAG)
        session.database.complete_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key)
        await session.send(
            "\r\nSela listens to your description of the leaf dam, then checks that you left most of it intact. 'Exactly. The dam was habitat. The wedged branch was the problem. If you had cleaned the whole run, you would have traded one imbalance for another.'\r\n"
            "Quest complete: What the Rain Remembers.\r\n"
        )
        return True

    objective = RAINPOOL_BALANCE_QUEST.objective_for_step(quest.get("current_step"))
    await session.send("\r\nSela asks for the observation before the conclusion.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _handle_rainpool_quest(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session, RAINPOOL_BALANCE_QUEST.key)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    room = session.character.current_room

    if room == FOREST_ELF_RAINPOOL_TERRACE_KEY and normalized in {
        "examine rain pools", "look rain pools", "examine pools", "look pools", "inspect pools", "examine upper pool"
    }:
        if step == "inspect_pools":
            session.database.advance_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key, "trace_runoff")
        await session.send(
            "\r\nThe upper basin is low while the middle basin is too full, yet both have fresh wet lines above their current surfaces. Water arrived here recently. Something in the eastern overflow is routing it unevenly. Follow the seep EAST.\r\n"
        )
        return True

    if room == FOREST_ELF_SEEPSTONE_RUN_KEY and normalized in {
        "examine leaf dam", "look leaf dam", "examine dam", "look dam", "inspect dam", "examine blockage"
    }:
        if step == "trace_runoff":
            session.database.advance_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key, "adjust_flow")
        await session.send(
            "\r\nMost of the leaf dam is healthy, temporary wetland habitat. One wedged branch is the actual problem: it seals the lower fork and forces nearly all runoff into a single channel. The smallest useful intervention is to free that branch and leave the rest alone.\r\n"
        )
        return True

    if room == FOREST_ELF_SEEPSTONE_RUN_KEY and normalized in {
        "clear leaf dam", "adjust leaf dam", "clear dam", "free branch", "move branch", "open lower channel"
    }:
        if step != "adjust_flow":
            await session.send("\r\nBefore changing the seep, work out which part is actually causing the imbalance. EXAMINE LEAF DAM.\r\n")
            return True
        session.database.grant_flag(session.character.id, FOREST_ELF_RAIN_CHANNEL_ADJUSTED_FLAG)
        session.database.advance_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key, "listen_flow")
        await session.send(
            "\r\nYou brace the leaf mat with one hand and ease only the wedged branch upward. A thumb-wide channel opens beneath it. The rest of the dam stays intact, full of wet leaves and tiny moving things.\r\n"
            "Water begins dividing between both forks. Do not assume that means the job is finished. LISTEN WATER.\r\n"
        )
        return True

    if room == FOREST_ELF_SEEPSTONE_RUN_KEY and normalized in {
        "listen", "listen water", "listen to water", "listen seep", "listen to seep", "listen flow"
    }:
        if step != "listen_flow":
            return False
        session.database.grant_flag(session.character.id, FOREST_ELF_RAIN_BALANCED_FLAG)
        session.database.advance_quest(session.character.id, RAINPOOL_BALANCE_QUEST.key, "return_sela")
        await session.send(
            "\r\nYou stop moving. Two quiet notes of water now overlap beneath the alder roots: one through the original fork and one through the reopened lower channel. Neither is rushing hard enough to scour the soil.\r\n"
            "The hillside is sharing water again. Return WEST, then SOUTH to the Greenway and TALK SELA.\r\n"
        )
        return True

    return False


async def _talk_aven(session) -> bool:
    assert session.character is not None
    if session.character.character_class != "druid":
        await session.send(
            "\r\nAven is happy to discuss the nursery, but the exercises on his slate are Druid class instruction. The Circle does not require every keeper to be a Druid, and it does not pretend every keeper should train as one.\r\n"
        )
        return True

    if session.character.race == "forest_elf":
        heartseed = _forest_elf_heartseed_quest(session)
        if heartseed and heartseed.get("status") != "completed":
            await session.send(
                "\r\nAven nods toward Circle Clearing. 'Finish Maelis's Heartseed lesson first. If you are going to carry Druidic power, learn the local lesson in restraint before I add class technique to it.'\r\n"
            )
            return True

    first = _quest(session, DRUID_LIVING_ANSWER_QUEST.key)
    second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)

    if first is None:
        session.database.start_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key, "inspect_runner")
        prior = DRUID_NURTURE_FIRST_USE_FLAG in session.database.list_flags(session.character.id)
        await session.send(
            "\r\nAven lays a bruised nursery runner across damp soil. "
            + ("'You have already felt Nurture answer once. Good. Now show me that you can use it deliberately.'\r\n" if prior else "'This is where the Circle teaches a Druid's smallest useful intervention.'\r\n")
            + "'EXAMINE TEACHING RUNNER first. Nurture is not permission to skip diagnosis.'\r\n"
            "New Druid quest: The Living Answer.\r\n"
        )
        return True

    if first.get("status") == "active":
        if first.get("current_step") == "return_aven":
            session.database.grant_flag(session.character.id, DRUID_CIRCLE_FIRST_LESSON_FLAG)
            session.database.complete_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key)
            await session.send(
                "\r\nAven checks the new root and, more importantly, the rest of the runner you left unchanged. 'That is Nurture. Help the living thing complete work it was already trying to do.'\r\n"
                "Quest complete: The Living Answer. TALK AVEN again when you are ready for a diagnosis that is easier to get wrong.\r\n"
            )
            return True
        objective = DRUID_LIVING_ANSWER_QUEST.objective_for_step(first.get("current_step"))
        await session.send("\r\nAven waits for you to complete the nursery exercise.\r\n")
        if objective:
            await session.send(f"Current Druid objective: {objective}\r\n")
        return True

    if second is None:
        session.database.start_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "inspect_overgrowth")
        await session.send(
            "\r\nAven points north. 'Overgrowth Hollow has something that looks diseased from ten paces away. Most beginners decide what it is before they reach five.'\r\n"
            "'Go north. EXAMINE OVERGROWTH, then examine the tree it is growing on. Do not cut anything just because your first word for it is blight.'\r\n"
            "New Druid quest: Green Without Illness.\r\n"
        )
        return True

    if second.get("status") == "active":
        if second.get("current_step") == "return_aven":
            session.database.grant_flag(session.character.id, DRUID_FALSE_BLIGHT_COMPLETE_FLAG)
            session.database.complete_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key)
            await session.send(
                "\r\nAven smiles when you tell him you left the bracevine in place. 'Good. A Druid who knows ten cures but only one diagnosis is a hazard with excellent intentions.'\r\n"
                "Quest complete: Green Without Illness.\r\n"
            )
            return True
        objective = DRUID_FALSE_BLIGHT_QUEST.objective_for_step(second.get("current_step"))
        await session.send("\r\nAven says, 'Name the relationship before you name the remedy.'\r\n")
        if objective:
            await session.send(f"Current Druid objective: {objective}\r\n")
        return True

    await session.send(
        "\r\nAven gestures around the nursery. 'The Circle has more to teach, but those two lessons are enough foundation: Nurture what is already trying to live, and diagnose before you interfere.'\r\n"
    )
    return True


async def _handle_druid_class_arc(session, normalized: str) -> bool:
    if session.character is None or session.character.character_class != "druid":
        return False
    room = session.character.current_room

    target = _nurture_target(normalized)
    if target is not None:
        if not target:
            await session.send("\r\nNurture is contextual. Use NURTURE <living target>; the ability helps an existing living system rather than producing a generic spell effect.\r\n")
            return True
        if target in {"heartseed", "cutting", "heartseed cutting", "plant"} and room == FOREST_ELF_START_ROOM_KEY:
            return await _druid_nurture_heartseed(session)

        first = _quest(session, DRUID_LIVING_ANSWER_QUEST.key)
        if room == FOREST_ELF_KEEPER_NURSERY_KEY and target in {"runner", "teaching runner", "nursery runner", "vine runner"}:
            if not first or first.get("status") != "active" or first.get("current_step") != "nurture_runner":
                await session.send("\r\nThe runner does not need blind power. EXAMINE TEACHING RUNNER and follow Aven's exercise in order.\r\n")
                return True
            session.database.grant_flag(session.character.id, DRUID_NURSERY_TENDED_FLAG)
            session.database.advance_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key, "wait_runner")
            _record_nurture(session)
            await session.send(
                "\r\nYou rest two fingers near the bruised node and use Nurture. The impulse is subtle: warmth, moisture, and living tension briefly become easier to feel, and you offer the runner a small reserve of steadiness rather than an order to root.\r\n"
                "Nothing sprouts. Aven nods. WAIT and let the plant answer.\r\n"
            )
            return True

        second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)
        if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and target in {"sapling", "oak", "tree", "host", "young oak"}:
            if not second or second.get("status") != "active" or second.get("current_step") != "nurture_host":
                await session.send("\r\nNurture would be premature. The whole exercise is about determining what the vine and sapling are actually doing together first.\r\n")
                return True
            session.database.grant_flag(session.character.id, DRUID_OVERGROWTH_STABILIZED_FLAG)
            session.database.advance_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "wait_response")
            _record_nurture(session)
            await session.send(
                "\r\nYou place Nurture into the oak's own callus tissue rather than into the bracevine. The spell gives the damaged edge a little more living steadiness while leaving the vine untouched in its role as a flexible brace.\r\n"
                "No growth erupts and nothing falls away. WAIT and watch the tension between them settle.\r\n"
            )
            return True

        await session.send("\r\nThat living target has no authored Nurture interaction here. Nurture works through specific living relationships rather than as a free-form growth command.\r\n")
        return True

    if room == FOREST_ELF_KEEPER_NURSERY_KEY and normalized in {
        "examine teaching runner", "look teaching runner", "examine runner", "look runner", "inspect runner"
    }:
        first = _quest(session, DRUID_LIVING_ANSWER_QUEST.key)
        if not first or first.get("status") != "active":
            return False
        if first.get("current_step") == "inspect_runner":
            session.database.advance_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key, "nurture_runner")
        await session.send(
            "\r\nThe runner is healthy. One bruised node is still deciding whether to root where it touches damp soil. There is no infection to cure and no reason to force the whole plant into new growth. This is an appropriate target for a small NURTURE RUNNER.\r\n"
        )
        return True

    if room == FOREST_ELF_KEEPER_NURSERY_KEY and normalized in {"wait", "wait runner", "watch runner", "wait beside runner"}:
        first = _quest(session, DRUID_LIVING_ANSWER_QUEST.key)
        if not first or first.get("status") != "active" or first.get("current_step") != "wait_runner":
            return False
        await session.send("\r\nYou leave the runner alone after Nurture. For several breaths it looks exactly the same.\r\n")
        await asyncio.sleep(0.25)
        session.database.grant_flag(session.character.id, DRUID_NURSERY_ANSWERED_FLAG)
        session.database.advance_quest(session.character.id, DRUID_LIVING_ANSWER_QUEST.key, "return_aven")
        await session.send(
            "A single white root tip eases from the bruised node into the damp soil. The rest of the plant does not change. TALK AVEN.\r\n"
        )
        return True

    if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and normalized in {
        "examine overgrowth", "look overgrowth", "examine vine", "look vine", "examine bracevine", "inspect overgrowth"
    }:
        second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)
        if not second or second.get("status") != "active":
            return False
        if second.get("current_step") == "inspect_overgrowth":
            session.database.advance_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "inspect_host")
        await session.send(
            "\r\nThe bracevine is dense, but it lacks the mottling, brittle stems, sour smell, and bark penetration you would expect from the common blights it resembles. Its strongest tendrils cross the oak exactly where an old storm split the trunk. EXAMINE SAPLING before deciding what that means.\r\n"
        )
        return True

    if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and normalized in {
        "examine sapling", "look sapling", "examine oak", "look oak", "examine tree", "inspect sapling"
    }:
        second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)
        if not second or second.get("status") != "active":
            return False
        if second.get("current_step") == "inspect_host":
            session.database.advance_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "diagnose")
        await session.send(
            "\r\nThe oak is producing normal leaves and healthy callus tissue around its old split. The vine is not feeding through the wound; it crosses the damaged trunk under tension and anchors into soil on both sides. DIAGNOSE OVERGROWTH.\r\n"
        )
        return True

    if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and normalized in {
        "diagnose overgrowth", "diagnose vine", "diagnose bracevine", "assess overgrowth", "diagnose sapling"
    }:
        second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)
        if not second or second.get("status") != "active":
            return False
        if second.get("current_step") != "diagnose":
            await session.send("\r\nA diagnosis without both observations would only be a guess. Examine the overgrowth and its host first.\r\n")
            return True
        session.database.grant_flag(session.character.id, DRUID_FALSE_BLIGHT_DIAGNOSED_FLAG)
        session.database.advance_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "nurture_host")
        await session.send(
            "\r\nYou name the relationship: not blight, but living support. The bracevine colonized the disturbed soil after the storm and now spans the oak's split like a flexible splint. Removing it would increase the strain on healing wood.\r\n"
            "The useful intervention is to support the oak's own repair without destroying its helper. NURTURE SAPLING.\r\n"
        )
        return True

    if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and normalized in {
        "cut vine", "cut bracevine", "remove vine", "remove overgrowth", "chop vine", "clear overgrowth"
    }:
        await session.send(
            "\r\nYou stop before making the cut. The training slate's instruction is difficult to ignore: NAME THE RELATIONSHIP BEFORE YOU NAME THE REMEDY. Nothing is damaged, and the quest does not advance.\r\n"
        )
        return True

    if room == FOREST_ELF_OVERGROWTH_HOLLOW_KEY and normalized in {"wait", "wait sapling", "watch sapling", "wait overgrowth"}:
        second = _quest(session, DRUID_FALSE_BLIGHT_QUEST.key)
        if not second or second.get("status") != "active" or second.get("current_step") != "wait_response":
            return False
        await session.send("\r\nYou wait without touching vine or oak again. The hollow remains quiet.\r\n")
        await asyncio.sleep(0.25)
        session.database.advance_quest(session.character.id, DRUID_FALSE_BLIGHT_QUEST.key, "return_aven")
        await session.send(
            "The oak's split holds steady as the breeze moves through the crown. The bracevine flexes with it instead of against it. Nothing needed to be removed. Return SOUTH and TALK AVEN.\r\n"
        )
        return True

    return False


async def _show_circle(session) -> None:
    await session.send(
        "\r\n--- Circle of Keepers ---\r\n"
        "The local Forest Elf Circle is civic stewardship, not a Druid-only order. Its keepers include growers, water stewards, healers, seed keepers, and path wardens. Druids hold influence because their class training gives them unusual insight into living systems, but ordinary Circle standing does not require the Druid class.\r\n"
        "Druids visiting the Circle can seek class instruction from Aven Rootwake in Keeper's Nursery. Forest Elves can seek water-stewardship work from Sela Rainbough on the Greenway after Maelis's Heartseed lesson.\r\n"
    )


def install_forest_elf_stewardship_runtime(player_session_class, world_service) -> None:
    install_forest_elf_stewardship_content(world_service)
    if getattr(player_session_class, "_forest_elf_stewardship_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_use_ability = player_session_class.use_ability

    async def use_ability(self, ability_text: str) -> None:
        normalized = ability_text.strip().lower().replace("_", " ")
        if normalized == "nurture" and self.character is not None and self.character.character_class == "druid":
            await self.send(
                "Nurture needs an authored living target. Use NURTURE <target> where the environment presents a living system you can actually help.\r\n"
            )
            return
        await previous_use_ability(self, ability_text)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"circle", "keepers", "circle of keepers", "keeper circle"}:
            await _show_circle(self)
            return

        if self.character.character_class == "druid":
            if normalized in {
                "tend heartseed", "coax heartseed", "care for heartseed", "use silvermoss on heartseed", "apply silvermoss to heartseed"
            } and self.character.race == "forest_elf" and self.character.current_room == FOREST_ELF_START_ROOM_KEY:
                heartseed = _forest_elf_heartseed_quest(self)
                if heartseed and heartseed.get("status") == "active" and heartseed.get("current_step") == "tend_heartseed":
                    await self.send(
                        "\r\nAs a Druid, Maelis turns this step into class practice. Set the Silvermoss as planned, then use your actual class skill: NURTURE HEARTSEED.\r\n"
                    )
                    return
            if await _handle_druid_class_arc(self, normalized):
                return

        if await _handle_rainpool_quest(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == FOREST_ELF_GREENWAY_KEY and _is_sela(target):
                if await _talk_sela(self):
                    return
            if self.character.current_room == FOREST_ELF_KEEPER_NURSERY_KEY and _is_aven(target):
                if await _talk_aven(self):
                    return

        had_instance_prompt = "prompt" in self.__dict__
        prior_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await previous_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = prior_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"}:
            await self.send(
                "Circle expansion: CIRCLE explains the Circle of Keepers. Forest Elves can TALK SELA for water-stewardship work after the Heartseed lesson. Druids can TALK AVEN in Keeper's Nursery and use contextual NURTURE <target>.\r\n"
            )

    player_session_class.use_ability = use_ability
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_stewardship_runtime_installed = True
