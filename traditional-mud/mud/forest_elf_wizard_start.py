from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.forest_elf_home_and_omens import FOREST_ELF_OPENING_COMPLETE_FLAG
from mud.forest_elf_stewardship import FOREST_ELF_KEEPER_NURSERY_KEY
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


FOREST_ELF_KILN_TERRACE_KEY = "forest_elf_tile_kiln_terrace"
FOREST_ELF_WIZARD_QUEST_KEY = "forest_elf_wizard_useful_heat"
FOREST_ELF_WIZARD_COMPLETE_FLAG = "forest_elf_wizard_useful_heat_complete"
FOREST_ELF_WIZARD_KILN_READ_FLAG = "forest_elf_wizard_kiln_read"
FOREST_ELF_WIZARD_VENTS_SET_FLAG = "forest_elf_wizard_vents_set"
FOREST_ELF_WIZARD_FIRST_COLDFIRE_FLAG = "forest_elf_wizard_first_coldfire"
FOREST_ELF_WIZARD_TILE_FIRED_FLAG = "forest_elf_wizard_tile_fired"
FOREST_ELF_WIZARD_TILE_RACKED_FLAG = "forest_elf_wizard_tile_racked"

LETHRA_CLAYBOUGH_KEY = "forest_elf_wizard_lethra_claybough"


FOREST_ELF_WIZARD_QUEST = QuestDefinition(
    key=FOREST_ELF_WIZARD_QUEST_KEY,
    name="The Useful Heat",
    style="structured",
    description=(
        "After the shared Forest Elf opening, a young Wizard helps fire a batch of drainage tiles needed by the town before the next heavy rain. "
        "The lesson treats Coldfire Burst as a practical tool: understand the clay and kiln first, set the ordinary controls, apply only enough magical heat to finish the firing, then inspect the result instead of mistaking power for success."
    ),
    objective_steps=(
        ("meet_lethra", "From Keeper's Nursery, go SOUTH to the Tile Kiln Terrace and TALK LETHRA."),
        ("inspect_tile", "EXAMINE GREEN TILE before applying any magic."),
        ("inspect_kiln", "EXAMINE KILN and learn what the firebox, vents, and heat marks are already doing."),
        ("set_vents", "SET VENTS to prepare the kiln for a short controlled magical firing."),
        ("fire_tile", "Use your Wizard spell in context with COLDFIRE BURST KILN."),
        ("inspect_fired_tile", "EXAMINE FIRED TILE and check whether the result is actually sound."),
        ("rack_tile", "MOVE TILE TO RACK and let useful work cool before anyone handles it."),
        ("return_lethra", "TALK LETHRA after the tile is safely cooling."),
        ("complete", "You learned that magic is a tool, not a performance: enough power to do the work, enough judgment to stop."),
    ),
)


LETHRA_CLAYBOUGH = NpcDefinition(
    key=LETHRA_CLAYBOUGH_KEY,
    name="Wizard Lethra Claybough",
    short_description=(
        "a Forest Elf Wizard in a clay-streaked work apron, checking kiln vents with one hand while marking firing times on a slate with the other"
    ),
    room_key=FOREST_ELF_KILN_TERRACE_KEY,
    role="Forest Elf Wizard mentor and practical kiln keeper",
    dialogue=(
        "Lethra taps ash from the end of a measuring rod. 'If all you can do with power is impress someone, it is not much of a tool.'",
        "'Too little heat and the tile crumbles after a wet freeze. Too much and it cracks before it ever reaches a roof or drain. Useful magic lives somewhere between.'",
        "'The spell is yours. The kiln, clay, weather, and people using the result are not. Learn what the work needs before you decide what your magic should do.'",
    ),
)


FOREST_ELF_KILN_TERRACE = RoomDefinition(
    key=FOREST_ELF_KILN_TERRACE_KEY,
    name="Tile Kiln Terrace",
    region_key="great_elf_forest",
    description=(
        "A low stone terrace sits just south of the Keeper's Nursery beneath a gap deliberately opened in the canopy. A squat clay kiln occupies the center beneath a rain hood, its chimney rising between branches without scorching them. Racks hold roof shingles, seed-pot inserts, drain collars, and flat water-channel tiles made for the town's paths and rain systems. "
        "Nothing here resembles a Wizard's tower. Buckets of slip, stacks of firewood, heat-darkened gloves, cracked practice pieces, and a chalkboard of firing times make the place look exactly like what it is: a workshop that happens to have magic available."
    ),
    exits={"north": FOREST_ELF_KEEPER_NURSERY_KEY},
    npc_keys=(LETHRA_CLAYBOUGH_KEY,),
    tags=("safe", "forest_elf_start", "wizard", "kiln", "craft", "community_work", "controlled_magic"),
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


def forest_elf_wizard_augmentations() -> dict[str, RoomAugmentation]:
    unfired = ViewCondition(forbidden_flags=(FOREST_ELF_WIZARD_TILE_FIRED_FLAG,))
    fired = ViewCondition(
        required_flags=(FOREST_ELF_WIZARD_TILE_FIRED_FLAG,),
        forbidden_flags=(FOREST_ELF_WIZARD_TILE_RACKED_FLAG,),
    )
    racked = ViewCondition(required_flags=(FOREST_ELF_WIZARD_TILE_RACKED_FLAG,))
    vents_set = ViewCondition(required_flags=(FOREST_ELF_WIZARD_VENTS_SET_FLAG,))

    return {
        FOREST_ELF_KILN_TERRACE_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    FOREST_ELF_KEEPER_NURSERY_KEY,
                    "Keeper's Nursery",
                    travel_text="You leave the warm stone of the kiln terrace and follow the short path north into the nursery beds.",
                ),
            ),
            features=(
                _feature(
                    "kiln_green_tile",
                    "Green Drainage Tile",
                    "a broad unfired drainage tile resting on a kiln shelf, still dark with a little moisture",
                    "The tile is evenly rolled and thick enough to survive footpath runoff. Its surface is leather-hard rather than wet, but the center still carries enough moisture that sudden excessive heat could split it. It needs a controlled final firing, not a blast for its own sake.",
                    ("green tile", "unfired tile", "tile", "drainage tile", "clay tile"),
                    condition=unfired,
                ),
                _feature(
                    "kiln_body",
                    "Working Kiln",
                    "a squat clay kiln with a wood-fed firebox, two sliding vents, and painted heat marks around the mouth",
                    "The wood fire has already brought the kiln most of the way to temperature. The lower vent feeds the coals; the upper vent controls the draw. A short, carefully placed increase in heat would finish the tile. A careless magical burst could overshoot the firing and crack it.",
                    ("kiln", "working kiln", "firebox", "oven", "clay kiln"),
                ),
                _feature(
                    "kiln_vents_ready",
                    "Set Kiln Vents",
                    "the kiln vents adjusted to a narrow, steady draw for the final firing",
                    "The vents are set so the fire will accept a brief magical increase without turning the kiln into a bellows. Ordinary controls are doing most of the safety work before magic ever enters the process.",
                    ("vents", "kiln vents", "upper vent", "lower vent"),
                    condition=vents_set,
                ),
                _feature(
                    "kiln_fired_tile",
                    "Fresh-Fired Drainage Tile",
                    "a newly fired tile resting inside the opened kiln, its surface hard and evenly colored",
                    "The tile has fired through without warping. A faint hairline of darker color at one edge is only a heat mark, not a crack. Tapping it produces a clear ceramic note instead of the dull sound of underfired clay.",
                    ("fired tile", "fresh-fired tile", "tile", "drainage tile"),
                    condition=fired,
                ),
                _feature(
                    "kiln_cooling_rack",
                    "Cooling Rack",
                    "a slatted stone-and-wood rack where finished tiles cool slowly before being moved into town",
                    "The rack keeps hot ceramic off damp ground and spaces pieces far enough apart that trapped heat does not crack neighboring work. Several older tiles are marked for rain channels near the Greenway and Rainpool Terrace.",
                    ("rack", "cooling rack", "tile rack", "finished rack"),
                ),
                _feature(
                    "kiln_racked_tile",
                    "Cooling Drainage Tile",
                    "your finished drainage tile cooling among the town's other practical ceramic work",
                    "The tile is not beautiful enough for a display shelf and not meant to be. Once cool, it will carry rainwater away from a path where people walk. That is the entire success condition.",
                    ("cooling tile", "finished tile", "tile", "drainage tile"),
                    condition=racked,
                ),
                _feature(
                    "kiln_cracked_practice",
                    "Cracked Practice Pieces",
                    "a basket of warped and split tiles kept beside the kiln instead of hidden",
                    "The failures are labeled with blunt notes: TOO FAST, TOO HOT, CENTER STILL WET, VENT CLOSED. The lesson is not that skilled Wizards never make mistakes. It is that useful craftspeople keep evidence of them.",
                    ("cracked pieces", "practice pieces", "failed tiles", "failures", "broken tiles"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "kiln_workshop_noise",
                    "The kiln gives a low settling tick under the softer sounds of nursery work to the north. Someone has left a covered pitcher of water beside the chalkboard for whoever draws the hot shift.",
                    priority=45,
                ),
                DescriptionLayer(
                    "kiln_controlled_draw",
                    "With the vents set, the chimney draws in a narrow, even breath. The workshop is ready for one precise increase in heat rather than a display of force.",
                    priority=60,
                    condition=vents_set,
                ),
                DescriptionLayer(
                    "kiln_finished_work",
                    "One newly fired tile now sits on the cooling rack among dozens of ordinary pieces destined for roofs, drains, and garden paths.",
                    priority=75,
                    condition=racked,
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
    exits["south"] = FOREST_ELF_KILN_TERRACE_KEY
    description = original.description
    if "Tile Kiln Terrace" not in description:
        description += (
            " A short stone path runs south to the Tile Kiln Terrace, where practical ceramic work for roofs, planters, drains, and rain channels is fired under a deliberately open patch of sky."
        )
    return replace(original, exits=exits, description=description)


def install_forest_elf_wizard_content(world_service=None) -> None:
    if FOREST_ELF_WIZARD_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_WIZARD_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_WIZARD_QUEST.key] = FOREST_ELF_WIZARD_QUEST

    _replace_room(FOREST_ELF_KILN_TERRACE)
    _replace_npc(LETHRA_CLAYBOUGH)
    nursery = _patch_nursery()
    _replace_room(nursery)

    if world_service is None:
        return

    world_service.legacy_rooms[FOREST_ELF_KILN_TERRACE_KEY] = FOREST_ELF_KILN_TERRACE
    world_service.legacy_rooms[FOREST_ELF_KEEPER_NURSERY_KEY] = nursery
    world_service.augmentations.update(forest_elf_wizard_augmentations())

    base = world_service.augmentations.get(FOREST_ELF_KEEPER_NURSERY_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "south"]
    exits.append(
        ExitDefinition(
            "south",
            FOREST_ELF_KILN_TERRACE_KEY,
            "Tile Kiln Terrace",
            travel_text="You follow the short stone path south from the nursery to the warm clay kiln terrace.",
        )
    )
    world_service.augmentations[FOREST_ELF_KEEPER_NURSERY_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(FOREST_ELF_KILN_TERRACE_KEY, None)
        cache.pop(FOREST_ELF_KEEPER_NURSERY_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(
        character
        and character.race == "forest_elf"
        and character.character_class == "wizard"
    )


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, FOREST_ELF_WIZARD_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_wizard_start(session) -> bool:
    if not _qualifies(session):
        return False
    if FOREST_ELF_OPENING_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "meet_lethra")
    return True


def _in_kiln(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == FOREST_ELF_KILN_TERRACE_KEY)


async def _talk_lethra(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session):
        return False
    step = quest.get("current_step")

    if step == "meet_lethra":
        session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "inspect_tile")
        await session.send(
            "\r\nLethra does not hand you a wand, point at a target dummy, or ask for a demonstration. She hands you a clay-smudged work slate instead.\r\n"
            "'Rainpool Terrace needs six replacement channel tiles before the next hard runoff. Five are already done. You are finishing the sixth.'\r\n"
            "She points to the dark clay piece on the kiln shelf. 'Power comes later. EXAMINE GREEN TILE first.'\r\n"
        )
        return True

    if step == "return_lethra":
        session.database.complete_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY)
        session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_COMPLETE_FLAG)
        await session.send(
            "\r\nLethra checks the cooling tile, then checks the slate where you recorded the firing. Only after both does she nod.\r\n"
            "'That is Wizardry I trust. You knew what the material needed, you let ordinary controls do their share, you added exactly enough power, and then you checked whether the work survived you.'\r\n"
            "She taps one of the cracked practice pieces with her boot. 'A spell is not successful because it was bright. It is successful because the thing you meant to accomplish is now true.'\r\n"
            "Her eyes flick toward the rack. 'Tomorrow somebody will set that tile in a drainage channel and probably never know which Wizard fired it. Good. Magic is a tool, not a performance.'\r\n"
            "\r\nQuest complete: The Useful Heat.\r\n"
        )
        return True

    objective = FOREST_ELF_WIZARD_QUEST.objective_for_step(step)
    await session.send("\r\nLethra gestures back toward the work. 'Finish the part in front of you before reaching for the impressive part.'\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_tile(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "inspect_tile":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "inspect_kiln")
    await session.send(
        "\r\nThe tile is leather-hard and evenly shaped, but the center still holds a little moisture. Too little heat and it will remain weak. Too much heat too quickly and trapped moisture could split it from within.\r\n"
        "Lethra says, 'Good. Now learn the tool around the spell. EXAMINE KILN.'\r\n"
    )
    return True


async def _inspect_kiln(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "inspect_kiln":
        return False
    if FOREST_ELF_WIZARD_KILN_READ_FLAG not in _flags(session):
        session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_KILN_READ_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "set_vents")
    await session.send(
        "\r\nThe wood fire has done nearly all the work already. The painted heat marks show the kiln is just below the final firing range, while the current wide draw would turn a magical burst into a fast temperature spike.\r\n"
        "Lethra points to the two vent sliders. 'A good Wizard is allowed to use a lever. SET VENTS.'\r\n"
    )
    return True


async def _set_vents(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "set_vents":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_VENTS_SET_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "fire_tile")
    await session.send(
        "\r\nYou narrow the lower intake and ease the upper vent until the chimney pulls a thin, steady draft. The coals settle instead of roaring. Ordinary airflow has made the kiln predictable enough for magic to be precise.\r\n"
        "Lethra steps back. 'Now the spell. Not at the tile itself. Through the firebox, where the kiln can spread the heat. COLDFIRE BURST KILN.'\r\n"
    )
    return True


async def _coldfire_kiln(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "fire_tile":
        return False
    flags = _flags(session)
    if FOREST_ELF_WIZARD_VENTS_SET_FLAG not in flags:
        await session.send("\r\nThe kiln is not prepared for a controlled magical firing yet. EXAMINE KILN and set its vents first.\r\n")
        return True
    if FOREST_ELF_WIZARD_FIRST_COLDFIRE_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "coldfire_burst", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_FIRST_COLDFIRE_FLAG)
    session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_TILE_FIRED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "inspect_fired_tile")
    await session.send(
        "\r\nYou shape Coldfire Burst into the kiln's firebox instead of throwing it across the terrace. Blue-white flame folds through the coals for a brief controlled pulse. The narrowed draw carries the heat evenly around the tile rather than slamming one face of it.\r\n"
        "You stop before the kiln begins to roar. The spell ends; the kiln keeps doing its ordinary work for several breaths more.\r\n"
        "Lethra does not applaud. She opens the inspection slot. 'Magic happened. That does not tell us whether the work succeeded. EXAMINE FIRED TILE.'\r\n"
    )
    return True


async def _inspect_fired_tile(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "inspect_fired_tile":
        return False
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "rack_tile")
    await session.send(
        "\r\nThe tile is hard, flat, and evenly fired. No steam fracture has opened through the center, and a light tap gives a clear ceramic note rather than the dull thud of underfired clay.\r\n"
        "It is not perfect because you cast a spell. It is sound because the clay, airflow, existing fire, timing, and spell all did the jobs they were supposed to do.\r\n"
        "Lethra hooks a padded lifting board under it. 'Last step. Do not ruin good work by handling it like a trophy. MOVE TILE TO RACK.'\r\n"
    )
    return True


async def _rack_tile(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_kiln(session) or quest.get("current_step") != "rack_tile":
        return False
    session.database.grant_flag(session.character.id, FOREST_ELF_WIZARD_TILE_RACKED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_WIZARD_QUEST_KEY, "return_lethra")
    await session.send(
        "\r\nUsing the padded board and both hands, you move the hot tile to the cooling rack. It settles beside roof shingles, garden collars, and five matching drainage pieces.\r\n"
        "By tomorrow it will be an unremarkable part of the town's rain system. For now it only needs to cool. TALK LETHRA.\r\n"
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


def install_forest_elf_wizard_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Forest Elf Wizard extension after the shared opening."""
    if getattr(player_session_class, "_forest_elf_wizard_runtime_installed", False):
        return

    install_forest_elf_wizard_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_wizard_start(self):
            await self.send(
                "\r\nAs the Circle settles back into its ordinary work, Neris catches you with a clay-marked note from the nursery.\r\n"
                "'Lethra Claybough needs a Wizard for the last drainage tile before the next rain. She was very specific that she needs a Wizard, not a fireworks display.'\r\n"
                "'Find her at the Tile Kiln Terrace, south from Keeper's Nursery.'\r\n"
                "\r\nNew quest: The Useful Heat.\r\n"
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
        if normalized in {"talk lethra", "talk wizard lethra", "talk lethra claybough", "talk wizard lethra claybough"}:
            handled = await _talk_lethra(self)
        elif normalized in {"examine green tile", "inspect green tile", "look green tile", "examine unfired tile", "inspect tile", "examine tile"}:
            quest = _quest(self)
            if quest and quest.get("current_step") == "inspect_fired_tile":
                handled = await _inspect_fired_tile(self)
            else:
                handled = await _inspect_tile(self)
        elif normalized in {"examine kiln", "inspect kiln", "look kiln", "examine firebox", "inspect firebox"}:
            handled = await _inspect_kiln(self)
        elif normalized in {"set vents", "adjust vents", "set kiln vents", "adjust kiln vents", "prepare vents"}:
            handled = await _set_vents(self)
        elif normalized in {
            "coldfire burst kiln", "coldfire kiln", "cast coldfire burst kiln", "cast coldfire burst on kiln",
            "use coldfire burst kiln", "use coldfire burst on kiln", "coldfire firebox", "coldfire burst firebox"
        }:
            handled = await _coldfire_kiln(self)
        elif normalized in {"examine fired tile", "inspect fired tile", "look fired tile", "check fired tile", "tap tile"}:
            handled = await _inspect_fired_tile(self)
        elif normalized in {"move tile to rack", "rack tile", "place tile on rack", "put tile on rack", "cool tile"}:
            handled = await _rack_tile(self)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_wizard_start(self):
            await self.send(
                "\r\nWhen the shared Forest Elf lesson is finally behind you, Neris hands you a clay-marked work note.\r\n"
                "'Lethra Claybough needs the sixth drainage tile fired before the next hard rain. Tile Kiln Terrace, south from Keeper's Nursery.'\r\n"
                "\r\nNew quest: The Useful Heat.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_wizard_runtime_installed = True
