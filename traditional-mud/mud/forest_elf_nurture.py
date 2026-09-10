from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import FOREST_ELF_START_ROOM_KEY, NpcDefinition, RoomDefinition


FOREST_ELF_GREENWAY_KEY = "forest_elf_greenway"
FOREST_ELF_HEARTSEED_QUEST_KEY = "forest_elf_heartseed_patience"
FOREST_ELF_HEARTSEED_TENDED_FLAG = "forest_elf_heartseed_tended"
FOREST_ELF_HEARTSEED_BLOOMED_FLAG = "forest_elf_heartseed_bloomed"
FOREST_ELF_NURTURE_COMPLETE_FLAG = "forest_elf_first_nurture_complete"

SILVERMOSS_SPRIG = ItemDefinition(
    "forest_elf_silvermoss_sprig",
    "Silvermoss Sprig",
    "A cool, pale-green sprig gathered from the Circle's herb border. It holds moisture without smothering delicate roots.",
    "herb",
    tier=0,
)

FOREST_ELF_HEARTSEED_QUEST = QuestDefinition(
    key=FOREST_ELF_HEARTSEED_QUEST_KEY,
    name="The Heartseed's Patience",
    style="structured",
    description=(
        "Keeper Maelis asks a new Elf to restore a stressed heartseed cutting in Circle Clearing. "
        "The lesson teaches diagnosis, gentle Herbalism, tending, and patience rather than forcing growth with spectacular magic."
    ),
    objective_steps=(
        ("speak_keeper", "TALK MAELIS in Circle Clearing and accept the tending lesson."),
        ("inspect_heartseed", "EXAMINE HEARTSEED and determine whether the cutting is blighted or simply stressed."),
        ("gather_silvermoss", "GATHER SILVERMOSS from the Circle herb border."),
        ("tend_heartseed", "TEND HEARTSEED using the Silvermoss you gathered."),
        ("wait_for_growth", "WAIT beside the Heartseed instead of trying to force another change."),
        ("return_keeper", "TALK MAELIS after the Heartseed has responded."),
        ("complete", "You learned the Circle's first lesson in patient stewardship."),
    ),
)

MAELIS_FERNWARD = NpcDefinition(
    key="forest_elf_keeper_maelis_fernward",
    name="Keeper Maelis Fernward",
    short_description="a silver-haired Circle keeper kneeling beside trays of seedlings and handwritten weather notes",
    room_key=FOREST_ELF_START_ROOM_KEY,
    role="Forest Elf starter mentor and tending instructor",
    dialogue=(
        "Maelis rests two fingers against a leaf before answering. 'A good keeper asks what changed before deciding what must be changed back.'",
        "'The forest is not impressed by speed. Roots do most of their work where nobody can applaud them.'",
        "'When this lesson is done, the old river path will teach you the other half of keeping: knowing where the tended forest ends.'",
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


def forest_elf_nurture_augmentations() -> dict[str, RoomAugmentation]:
    struggling = ViewCondition(forbidden_flags=(FOREST_ELF_HEARTSEED_TENDED_FLAG, FOREST_ELF_HEARTSEED_BLOOMED_FLAG))
    resting = ViewCondition(
        required_flags=(FOREST_ELF_HEARTSEED_TENDED_FLAG,),
        forbidden_flags=(FOREST_ELF_HEARTSEED_BLOOMED_FLAG,),
    )
    bloomed = ViewCondition(required_flags=(FOREST_ELF_HEARTSEED_BLOOMED_FLAG,))

    return {
        FOREST_ELF_START_ROOM_KEY: RoomAugmentation(
            features=(
                _feature(
                    "heartseed_struggling",
                    "Struggling Heartseed",
                    "a young heartseed cutting whose leaves have curled inward",
                    (
                        "The cutting is alive, but several leaves have folded against themselves and the soil around the root crown is too dry. "
                        "There is no blackening, webbing, sour smell, or vein-scarring associated with common forest blights. This looks like transplant stress, not disease."
                    ),
                    aliases=("heartseed", "cutting", "sapling", "plant", "heartseed cutting"),
                    search="A careful look beneath the leaves confirms the same thing: no pests and no blight, only a root bed that has lost moisture too quickly.",
                    touch="The stem has a little spring in it. The plant is stressed, not dying.",
                    condition=struggling,
                ),
                _feature(
                    "heartseed_resting",
                    "Tended Heartseed",
                    "the heartseed resting in a newly loosened bed of damp Silvermoss",
                    (
                        "Silvermoss now cups the exposed root crown without covering the stem. The leaves have not opened yet. "
                        "Nothing dramatic is happening—which, Maelis would probably say, is not the same as nothing happening."
                    ),
                    aliases=("heartseed", "cutting", "sapling", "plant", "heartseed cutting"),
                    touch="The soil is evenly cool now. The stem is best left alone.",
                    listen="There is no magical whisper or sudden crack of growth, only wind moving through the clearing.",
                    condition=resting,
                ),
                _feature(
                    "heartseed_awakened",
                    "Opened Heartseed",
                    "the restored heartseed holding a small fan of newly opened leaves toward the canopy",
                    (
                        "The curled leaves have relaxed into a healthy fan. One tiny new bud has pushed free at the center. "
                        "The change is modest enough to be believable and unmistakable enough to reward the patience that produced it."
                    ),
                    aliases=("heartseed", "cutting", "sapling", "plant", "heartseed cutting"),
                    touch="The new leaf is soft and resilient. There is no reason to disturb it further.",
                    condition=bloomed,
                ),
                _feature(
                    "circle_herb_border",
                    "Circle Herb Border",
                    "a carefully mixed border of useful low-growing herbs kept for teaching and ordinary remedies",
                    (
                        "Nothing is planted in ruler-straight rows. Species are grouped by shade, moisture, and what they do for neighboring roots. "
                        "Pale Silvermoss grows beneath the wetter stones where beginners can learn to gather without damaging a wild patch."
                    ),
                    aliases=("herb border", "herbs", "garden", "silvermoss", "silvermoss bed"),
                    search="Small wooden markers identify which patches may be gathered today and which are being rested.",
                ),
                _feature(
                    "circle_season_wheel",
                    "Season Wheel",
                    "a simple wooden wheel showing the Circle's recurring duties through the four seasons",
                    (
                        "Four carved quarters show budding shoots, a full leaf, a falling seed, and a sleeping root. "
                        "The wheel is less a festival calendar than a reminder that the same place asks different kinds of care at different times of year."
                    ),
                    aliases=("season wheel", "wheel", "seasonal wheel", "calendar"),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "forest_elf_heartseed_tended_layer",
                    "Near the Circle stones, a heartseed cutting rests quietly in a fresh collar of damp Silvermoss.",
                    priority=70,
                    condition=resting,
                ),
                DescriptionLayer(
                    "forest_elf_heartseed_bloomed_layer",
                    "Near the Circle stones, a restored heartseed has opened a small fan of green leaves toward the canopy.",
                    priority=80,
                    condition=bloomed,
                ),
            ),
        ),
        FOREST_ELF_GREENWAY_KEY: RoomAugmentation(
            features=(
                _feature(
                    "greenway_boundary_marks",
                    "Boundary Care Marks",
                    "small, practical signs recording recent pruning, blight checks, and path repairs",
                    (
                        "The marks are not territorial warnings. They are dated care records: bark inspected, fungus identified, dead limb removed, drainage cleared. "
                        "The farther the Greenway runs from town, the less frequent these marks become."
                    ),
                    aliases=("care marks", "boundary marks", "marks", "inspection marks"),
                    search="One recent mark notes that the birches here were checked for silver-vein blight and found clean.",
                ),
            ),
        ),
    }


def _patch_start_npc() -> None:
    room = legacy_world.ROOMS_BY_KEY.get(FOREST_ELF_START_ROOM_KEY)
    if room is None:
        return
    if MAELIS_FERNWARD.key in room.npc_keys:
        return
    replacement = replace(room, npc_keys=room.npc_keys + (MAELIS_FERNWARD.key,))
    legacy_world.ROOMS = tuple(replacement if value.key == FOREST_ELF_START_ROOM_KEY else value for value in legacy_world.ROOMS)
    legacy_world.ROOMS_BY_KEY[FOREST_ELF_START_ROOM_KEY] = replacement


def install_forest_elf_nurture_content(world_service=None) -> None:
    _patch_start_npc()

    if MAELIS_FERNWARD.key not in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = legacy_world.NPCS + (MAELIS_FERNWARD,)
    legacy_world.NPCS_BY_KEY[MAELIS_FERNWARD.key] = MAELIS_FERNWARD

    if SILVERMOSS_SPRIG.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (SILVERMOSS_SPRIG,)
    crafting.ITEMS_BY_KEY[SILVERMOSS_SPRIG.key] = SILVERMOSS_SPRIG

    if FOREST_ELF_HEARTSEED_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (FOREST_ELF_HEARTSEED_QUEST,)
    quests.QUESTS_BY_KEY[FOREST_ELF_HEARTSEED_QUEST.key] = FOREST_ELF_HEARTSEED_QUEST

    if world_service is not None:
        patched = legacy_world.ROOMS_BY_KEY.get(FOREST_ELF_START_ROOM_KEY)
        if patched is not None:
            world_service.legacy_rooms[FOREST_ELF_START_ROOM_KEY] = patched
        world_service.augmentations.update(forest_elf_nurture_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(FOREST_ELF_START_ROOM_KEY, None)
            cache.pop(FOREST_ELF_GREENWAY_KEY, None)


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)


def _consume_silvermoss(session) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, SILVERMOSS_SPRIG.key)
    if quantity > 0:
        session.database.consume_item(session.character.id, SILVERMOSS_SPRIG.key, quantity)


def _ensure_one_silvermoss(session) -> None:
    assert session.character is not None
    quantity = session.database.item_quantity(session.character.id, SILVERMOSS_SPRIG.key)
    if quantity == 0:
        session.database.add_item(session.character.id, SILVERMOSS_SPRIG.key, 1)
    elif quantity > 1:
        session.database.consume_item(session.character.id, SILVERMOSS_SPRIG.key, quantity - 1)


def _initialize_or_reconcile_forest_elf(session) -> None:
    if session.character is None or session.character.race != "forest_elf":
        return
    quest = _quest(session)
    if quest is None:
        session.database.start_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "speak_keeper")
        _consume_silvermoss(session)
        return

    if quest.get("status") == "completed":
        _consume_silvermoss(session)
        session.database.grant_flag(session.character.id, FOREST_ELF_HEARTSEED_BLOOMED_FLAG)
        session.database.grant_flag(session.character.id, FOREST_ELF_NURTURE_COMPLETE_FLAG)
        return

    step = quest.get("current_step")
    if step == "tend_heartseed":
        _ensure_one_silvermoss(session)
    else:
        _consume_silvermoss(session)


def _talk_target(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _is_maelis(target: str) -> bool:
    return target in {
        "maelis",
        "keeper",
        "keeper maelis",
        "maelis fernward",
        "keeper maelis fernward",
        "druid",
        "mentor",
    }


async def _talk_maelis(session) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    quest = _quest(session)
    if quest is None:
        _initialize_or_reconcile_forest_elf(session)
        quest = _quest(session)
    if not quest:
        return False

    step = quest.get("current_step")
    if quest.get("status") == "completed":
        await session.send(
            "\r\nMaelis glances from you to the opened heartseed. 'You already know the first lesson. Care is not measured by how much of yourself you make visible.'\r\n"
            "She nods toward the northern path. 'The Old River Path is the next lesson: learn where the tended forest ends and the older forest begins.'\r\n"
        )
        return True

    if step == "speak_keeper":
        session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "inspect_heartseed")
        await session.send(
            "\r\nMaelis draws you beside a young heartseed cutting whose leaves are curled tight.\r\n"
            "'Do not heal it yet,' she says. 'First decide whether it is ill. EXAMINE HEARTSEED. A keeper who acts before looking can turn kindness into damage.'\r\n"
            "New quest: The Heartseed's Patience.\r\n"
        )
        return True

    if step == "return_keeper":
        session.database.grant_flag(session.character.id, FOREST_ELF_NURTURE_COMPLETE_FLAG)
        session.database.complete_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key)
        await session.send(
            "\r\nMaelis studies the newly opened leaves but seems more interested in what you did not do.\r\n"
            "'You diagnosed before treating. You took only what the herb border could spare. You changed the root bed once, then you gave the plant time to answer.'\r\n"
            "She touches the carved stones of the Circle. 'That is enough magic for a first morning.'\r\n"
            "Quest complete: The Heartseed's Patience.\r\n"
            "'Now take the Old River Path. Walk the boundary, read the waystone, listen at the pool, and notice where our careful marks begin to disappear.'\r\n"
        )
        return True

    objective = FOREST_ELF_HEARTSEED_QUEST.objective_for_step(step)
    await session.send("\r\nMaelis waits without hurrying you.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _examine_heartseed(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest or quest.get("status") != "active":
        return False
    step = quest.get("current_step")
    if step == "inspect_heartseed":
        session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "gather_silvermoss")
        await session.send(
            "\r\nYou inspect leaf veins, stem, root crown, soil, and the undersides of the curled leaves. There is no blight. The cutting is simply stressed and drying too quickly after transplanting.\r\n"
            "A thin collar of moisture-holding Silvermoss would protect the roots without drowning them. GATHER SILVERMOSS from the Circle herb border.\r\n"
        )
        return True
    return False


async def _gather_silvermoss(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest or quest.get("status") != "active":
        return False
    if quest.get("current_step") != "gather_silvermoss":
        await session.send("\r\nThe teaching bed is not something to harvest casually. Maelis expects you to know what the Heartseed needs first.\r\n")
        return True

    # Treat this as real Herbalism progression while keeping the tutorial node
    # single-use and authored rather than turning the starter garden into a farm.
    session.database.complete_crafting_transaction(
        session.character.id,
        trade_skill_key="herbalism",
        materials=(),
        output_item_key=SILVERMOSS_SPRIG.key,
        output_quantity=1,
        skill_xp_gain=1,
    )
    _ensure_one_silvermoss(session)
    session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "tend_heartseed")
    await session.send(
        "\r\nYou part the herb border with your fingers and take one healthy Silvermoss sprig from the marked teaching patch, leaving the pale runners beneath it intact.\r\n"
        "Herbalism improves through use. You receive a Silvermoss Sprig.\r\n"
        "Return your attention to the cutting and TEND HEARTSEED.\r\n"
    )
    return True


async def _tend_heartseed(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest or quest.get("status") != "active":
        return False
    if quest.get("current_step") != "tend_heartseed":
        await session.send("\r\nThere is no reason to keep fussing with the Heartseed. Look, diagnose, and make only the change the plant actually needs.\r\n")
        return True
    if session.database.item_quantity(session.character.id, SILVERMOSS_SPRIG.key) < 1:
        _ensure_one_silvermoss(session)

    session.database.consume_item(session.character.id, SILVERMOSS_SPRIG.key, 1)
    session.database.grant_flag(session.character.id, FOREST_ELF_HEARTSEED_TENDED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "wait_for_growth")
    await session.send(
        "\r\nYou loosen the dry crust around the root crown instead of digging into it, tuck the Silvermoss against the exposed soil, and press just enough damp earth around the runners to hold them in place.\r\n"
        "You let a little of the Circle's quiet nature magic follow the work—not a command to grow, only a gentle invitation for root and moss to settle together.\r\n"
        "The leaves do not spring open. Maelis says nothing. The lesson is clearly not finished. WAIT beside the Heartseed.\r\n"
    )
    return True


async def _wait_for_heartseed(session) -> bool:
    assert session.character is not None
    quest = _quest(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "wait_for_growth":
        return False

    await session.send("\r\nYou stay beside the Heartseed without touching it again. For a little while, nothing happens.\r\n")
    await asyncio.sleep(0.35)
    session.database.grant_flag(session.character.id, FOREST_ELF_HEARTSEED_BLOOMED_FLAG)
    session.database.advance_quest(session.character.id, FOREST_ELF_HEARTSEED_QUEST.key, "return_keeper")
    await session.send(
        "One curled leaf slowly relaxes. Then another. A tiny new bud clears the center of the cutting and holds there in the filtered light.\r\n"
        "The change is small, healthy, and enough. TALK MAELIS.\r\n"
    )
    return True


def _season_duty_text() -> str:
    moment = ASTRALIS_CLOCK.now()
    duties = {
        "spring": "Spring work favors transplanting, stream checks, new-growth blight inspections, and deciding which paths need repair after winter runoff.",
        "summer": "Summer work favors shade management, careful watering, pruning storm-damaged growth, and keeping herb beds productive without exhausting them.",
        "autumn": "Autumn work favors seed saving, root division, boundary inspection, and watching closely for blight before fallen leaves can hide it.",
        "winter": "Winter work favors root protection, dormant pruning, tool repair, and learning which plants are healthiest when left completely alone.",
    }
    duty = duties.get(moment.season, "The Circle adjusts its work to the season rather than forcing one schedule on the forest.")
    return f"Astralis is in {moment.season_name}. {duty}"


async def _show_season_wheel(session) -> None:
    await session.send(
        "\r\nThe Circle's season wheel is deliberately practical rather than ceremonial. " + _season_duty_text() + "\r\n"
    )


async def _handle_forest_elf_nurture(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "forest_elf":
        return False
    if session.character.current_room != FOREST_ELF_START_ROOM_KEY:
        return False

    if normalized in {
        "examine heartseed", "look heartseed", "examine cutting", "look cutting",
        "check heartseed", "check blight", "check heartseed for blight", "inspect heartseed",
    }:
        return await _examine_heartseed(session)

    if normalized in {
        "gather silvermoss", "harvest silvermoss", "gather moss", "harvest moss", "pick silvermoss",
    }:
        return await _gather_silvermoss(session)

    if normalized in {
        "tend heartseed", "coax heartseed", "nurture heartseed", "care for heartseed",
        "use silvermoss on heartseed", "apply silvermoss to heartseed",
    }:
        return await _tend_heartseed(session)

    if normalized in {"wait", "wait heartseed", "watch heartseed", "sit with heartseed", "wait beside heartseed"}:
        if await _wait_for_heartseed(session):
            return True

    if normalized in {
        "examine season wheel", "look season wheel", "read season wheel", "examine wheel", "read wheel", "season wheel",
    }:
        await _show_season_wheel(session)
        return True

    return False


def install_forest_elf_nurture_runtime(player_session_class, world_service) -> None:
    install_forest_elf_nurture_content(world_service)
    if getattr(player_session_class, "_forest_elf_nurture_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "forest_elf":
            _initialize_or_reconcile_forest_elf(self)
        await previous_enter_character(self)
        if self.character is not None and self.character.race == "forest_elf":
            _initialize_or_reconcile_forest_elf(self)
            quest = _quest(self)
            if quest and quest.get("status") == "active":
                objective = FOREST_ELF_HEARTSEED_QUEST.objective_for_step(quest.get("current_step"))
                await self.send("\r\nCircle lesson: The Heartseed's Patience.\r\n")
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "forest_elf":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if await _handle_forest_elf_nurture(self, normalized):
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = _talk_target(command)
            if self.character.current_room == FOREST_ELF_START_ROOM_KEY and _is_maelis(target):
                if await _talk_maelis(self):
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
                "Forest Elf starter: TALK MAELIS, EXAMINE HEARTSEED, GATHER SILVERMOSS, TEND HEARTSEED, WAIT, then TALK MAELIS. READ SEASON WHEEL explains the Circle's current seasonal work.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._forest_elf_nurture_runtime_installed = True
