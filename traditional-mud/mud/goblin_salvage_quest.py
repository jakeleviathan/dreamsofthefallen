from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_LEDGER_HALL_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_TINKER_ROW_KEY,
)
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, RoomAugmentation, ViewCondition
from mud.scavenging import RUMMAGE_NODES, RummageNode
from mud.world import NpcDefinition, RoomDefinition


GOBLIN_SALVAGE_ITEM_KEY = "cracked_copper_regulator"
GOBLIN_SALVAGE_COMPLETE_FLAG = "goblin_first_salvage_loop_completed"
GOBLIN_SALVAGE_CREDIT_FLAG = "goblin_salvage_credit_established"

# Keep the original internal key forever so characters from the earlier build
# retain their saved step even though the player-facing title has been refined.
GOBLIN_SALVAGE_QUEST = QuestDefinition(
    key="goblin_from_scrap_to_claim",
    name="A Piece Worth Keeping",
    style="structured",
    description=(
        "Ruskle Coil sends a new Goblin through Junk City's salvage economy: find a useful discarded part, "
        "have it weighed, put the claim into the ledger, carry it to Tinker Row for repair, and return it to the broker. "
        "The route teaches how Goblin ownership, repair, and trade fit together without requiring combat."
    ),
    objective_steps=(
        ("find_salvage", "Go to the Sorting Spine and RUMMAGE SORTING BINS for one unclaimed part worth carrying."),
        ("weigh_salvage", "Take the part to Skiv Weightwire at the Sorting Spine and TALK SKIV to have it weighed."),
        ("stamp_claim", "Carry the weighed part to Nalla Inkthumb in the Ledger Hall and TALK NALLA to record and stamp the claim."),
        ("repair_salvage", "Take the stamped part to Brin Copperhand on Tinker Row and TALK BRIN to have it identified and made useful."),
        ("return_broker", "Return the repaired part to Ruskle Coil in Brassgut Market and TALK RUSKLE."),
        ("complete", "You completed your first full Junk City salvage transaction and established a recorded salvage credit."),
    ),
)

GOBLIN_SALVAGE_ITEM = ItemDefinition(
    key=GOBLIN_SALVAGE_ITEM_KEY,
    name="Cracked Copper Regulator",
    description=(
        "A fist-sized copper pressure regulator recovered from Junk City's sorting stream. Its spring cage is bent, "
        "one mounting ear is cracked, and several old ownership marks have been deliberately scraped away."
    ),
    category="quest_item",
    tier=0,
)

# RUMMAGE is an authored room interaction, not a universal loot command. This
# node only says which phrases identify the one starter pile; quest eligibility
# and the result remain in this quest module.
GOBLIN_SORTING_RUMMAGE = RummageNode(
    key="goblin_starter_sorting_bins",
    room_key=GOBLIN_SORTING_SPINE_KEY,
    targets=(
        "sorting bins",
        "sorting bin",
        "bins",
        "bin",
        "sorting chutes",
        "sorting chute",
        "unknown but interesting",
        "salvage pile",
        "unclaimed salvage",
    ),
)

SKIV_WEIGHTWIRE = NpcDefinition(
    key="goblin_skiv_weightwire",
    name="Skiv Weightwire",
    short_description="a scale clerk keeping the starter weighing station open through the city's day-and-night shifts",
    room_key=GOBLIN_SORTING_SPINE_KEY,
    role="round-the-clock starter salvage weighmaster",
    dialogue=(
        "Skiv taps the nearest scale pan. 'Finding it is only the first half. Weight tells the lanes what moved, and the ledger tells everybody whose problem it becomes next.'",
        "'Starter claims get weighed at every hour. Junk City doesn't make a new Goblin wait for sunrise just to learn the rules.'",
    ),
)

NALLA_INKTHUMB = NpcDefinition(
    key="goblin_nalla_inkthumb",
    name="Nalla Inkthumb",
    short_description="a ledger clerk maintaining the starter claim desk beneath a lamp that never quite goes dark",
    room_key=GOBLIN_LEDGER_HALL_KEY,
    role="round-the-clock starter salvage claim clerk",
    dialogue=(
        "Nalla holds up one ink-black thumb. 'A mark says you touched it. A ledger says the city remembers you touched it. Those are different things.'",
        "'One claim desk stays staffed all night. A proper record does not care what hour you found the thing.'",
    ),
)

BRIN_COPPERHAND = NpcDefinition(
    key="goblin_brin_copperhand",
    name="Brin Copperhand",
    short_description="a repairer keeping a blue-white task lamp burning over the starter bench at every shift",
    room_key=GOBLIN_TINKER_ROW_KEY,
    role="round-the-clock starter salvage repairer",
    dialogue=(
        "Brin does not look up from the bench. 'Broken is a condition. Useless is an opinion. Put the interesting bit down.'",
        "'The starter bench stays open after dark. Bad repairs happen because of bad hands, not because the moon is up.'",
    ),
)

GOBLIN_SALVAGE_NPCS: tuple[NpcDefinition, ...] = (
    SKIV_WEIGHTWIRE,
    NALLA_INKTHUMB,
    BRIN_COPPERHAND,
)

NIGHT_SHIFT_LAYERS: dict[str, DescriptionLayer] = {
    GOBLIN_BRASSGUT_MARKET_KEY: DescriptionLayer(
        "goblin_salvage_broker_night_shift",
        "One brass lamp remains lit at Ruskle Coil's broker counter. The starter salvage route can be begun or settled even after most outer stalls have folded shut.",
        priority=56,
        condition=ViewCondition(time_buckets=("night",)),
    ),
    GOBLIN_SORTING_SPINE_KEY: DescriptionLayer(
        "goblin_salvage_scale_night_shift",
        "A hard white lamp burns over Skiv Weightwire's scale station. The main salvage flow is slower, but the starter weighing lane remains staffed through the night.",
        priority=56,
        condition=ViewCondition(time_buckets=("night",)),
    ),
    GOBLIN_LEDGER_HALL_KEY: DescriptionLayer(
        "goblin_salvage_ledger_night_shift",
        "A green-shaded lamp marks Nalla Inkthumb's claim desk as the one public ledger station that remains open for starter transactions after dark.",
        priority=56,
        condition=ViewCondition(time_buckets=("night",)),
    ),
    GOBLIN_TINKER_ROW_KEY: DescriptionLayer(
        "goblin_salvage_repair_night_shift",
        "Brin Copperhand's blue-white task lamp is still burning. Small starter-lane repairs continue here even when most of Tinker Row has narrowed its shutters.",
        priority=56,
        condition=ViewCondition(time_buckets=("night",)),
    ),
}


def _room_with_npc(room: RoomDefinition, npc_key: str) -> RoomDefinition:
    if npc_key in room.npc_keys:
        return room
    return replace(room, npc_keys=room.npc_keys + (npc_key,))


def _install_night_shift_layers(world_service) -> None:
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return
    for room_key, layer in NIGHT_SHIFT_LAYERS.items():
        augmentation = augmentations.get(room_key, RoomAugmentation())
        if any(existing.key == layer.key for existing in augmentation.description_layers):
            continue
        augmentations[room_key] = replace(
            augmentation,
            description_layers=augmentation.description_layers + (layer,),
        )
        scene_cache = getattr(world_service, "_scene_cache", None)
        if scene_cache is not None:
            scene_cache.pop(room_key, None)


def install_goblin_salvage_quest_content(world_service=None) -> None:
    """Register the starter salvage quest, item, contacts, and rummage node.

    Every registration path is idempotent. Saved quest progress uses SQLite; the
    display-name change does not alter the internal quest key.
    """
    if GOBLIN_SALVAGE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GOBLIN_SALVAGE_QUEST,)
    quests.QUESTS_BY_KEY[GOBLIN_SALVAGE_QUEST.key] = GOBLIN_SALVAGE_QUEST

    if GOBLIN_SALVAGE_ITEM.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (GOBLIN_SALVAGE_ITEM,)
    crafting.ITEMS_BY_KEY[GOBLIN_SALVAGE_ITEM.key] = GOBLIN_SALVAGE_ITEM

    RUMMAGE_NODES.register(GOBLIN_SORTING_RUMMAGE)

    known_npcs = {npc.key for npc in legacy_world.NPCS}
    additions = tuple(npc for npc in GOBLIN_SALVAGE_NPCS if npc.key not in known_npcs)
    if additions:
        legacy_world.NPCS = legacy_world.NPCS + additions
    legacy_world.NPCS_BY_KEY.update({npc.key: npc for npc in GOBLIN_SALVAGE_NPCS})

    patch_plan = {
        GOBLIN_SORTING_SPINE_KEY: SKIV_WEIGHTWIRE.key,
        GOBLIN_LEDGER_HALL_KEY: NALLA_INKTHUMB.key,
        GOBLIN_TINKER_ROW_KEY: BRIN_COPPERHAND.key,
    }
    replacements: dict[str, RoomDefinition] = {}
    for room_key, npc_key in patch_plan.items():
        room = legacy_world.ROOMS_BY_KEY.get(room_key)
        if room is None:
            continue
        replacements[room_key] = _room_with_npc(room, npc_key)

    if replacements:
        legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
        legacy_world.ROOMS_BY_KEY.update(replacements)

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        scene_cache = getattr(world_service, "_scene_cache", None)
        if scene_cache is not None:
            for room_key in replacements:
                scene_cache.pop(room_key, None)
        _install_night_shift_layers(world_service)


def _target_after_talk(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches_name(target: str, npc: NpcDefinition | None, extra_aliases: tuple[str, ...] = ()) -> bool:
    if npc is None:
        return False
    aliases = {
        npc.name.lower(),
        npc.key.replace("_", " "),
        npc.name.lower().split()[0],
        npc.name.lower().split()[-1],
        *(alias.lower() for alias in extra_aliases),
    }
    return target in aliases


def _quest_state(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key)


def _has_salvage(session) -> bool:
    return bool(
        session.character is not None
        and session.database.item_quantity(session.character.id, GOBLIN_SALVAGE_ITEM_KEY) > 0
    )


def _consume_all_salvage(session) -> None:
    if session.character is None:
        return
    quantity = session.database.item_quantity(session.character.id, GOBLIN_SALVAGE_ITEM_KEY)
    if quantity > 0:
        session.database.consume_item(session.character.id, GOBLIN_SALVAGE_ITEM_KEY, quantity)


def _completion_is_recorded(session) -> bool:
    if session.character is None:
        return False
    flags = session.database.list_flags(session.character.id)
    return bool({GOBLIN_SALVAGE_COMPLETE_FLAG, GOBLIN_SALVAGE_CREDIT_FLAG}.intersection(flags))


def _reconcile_persistent_state(session) -> str | None:
    """Repair interrupted quest state from persisted ledger/inventory facts.

    This makes logout/restart safe and also handles a process interruption
    between two SQLite calls. A completed ledger record is authoritative; an
    active post-rummage step is authoritative that the quest cargo should exist.
    """
    if session.character is None:
        return None

    character_id = session.character.id
    quest = _quest_state(session)
    quantity = session.database.item_quantity(character_id, GOBLIN_SALVAGE_ITEM_KEY)
    flags = session.database.list_flags(character_id)
    completion_recorded = bool(
        {GOBLIN_SALVAGE_COMPLETE_FLAG, GOBLIN_SALVAGE_CREDIT_FLAG}.intersection(flags)
    )

    if quest is not None and quest.get("status") == "completed":
        session.database.grant_flag(character_id, GOBLIN_SALVAGE_COMPLETE_FLAG)
        session.database.grant_flag(character_id, GOBLIN_SALVAGE_CREDIT_FLAG)
        _consume_all_salvage(session)
        return "complete"

    if completion_recorded:
        if quest is None:
            session.database.start_quest(character_id, GOBLIN_SALVAGE_QUEST.key, "complete")
        session.database.complete_quest(character_id, GOBLIN_SALVAGE_QUEST.key)
        session.database.grant_flag(character_id, GOBLIN_SALVAGE_COMPLETE_FLAG)
        session.database.grant_flag(character_id, GOBLIN_SALVAGE_CREDIT_FLAG)
        _consume_all_salvage(session)
        return "complete"

    if quest is None:
        # The quest item has no legitimate standalone acquisition path.
        if quantity > 0:
            _consume_all_salvage(session)
        return None

    if quest.get("status") != "active":
        return str(quest.get("current_step") or "")

    step = str(quest.get("current_step") or "find_salvage")
    post_find_steps = {"weigh_salvage", "stamp_claim", "repair_salvage", "return_broker"}

    if step == "find_salvage" and quantity > 0:
        # Crash-safe recovery if the item INSERT committed before the step update.
        if quantity > 1:
            session.database.consume_item(character_id, GOBLIN_SALVAGE_ITEM_KEY, quantity - 1)
        session.database.advance_quest(character_id, GOBLIN_SALVAGE_QUEST.key, "weigh_salvage")
        return "weigh_salvage"

    if step in post_find_steps:
        # If a development crash consumed/lost the unique quest cargo while the
        # ledger still says the transaction is active, restore exactly one.
        if quantity == 0:
            session.database.add_item(character_id, GOBLIN_SALVAGE_ITEM_KEY, 1)
        elif quantity > 1:
            session.database.consume_item(character_id, GOBLIN_SALVAGE_ITEM_KEY, quantity - 1)

    return step


async def _talk_ruskle(session) -> None:
    assert session.character is not None
    _reconcile_persistent_state(session)
    quest = _quest_state(session)

    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "find_salvage")
        await session.send(
            "\r\nRuskle Coil hooks one measuring tape back over his shoulder. 'Want a real lesson? Don't buy anything. Find me something the city nearly threw away.'\r\n"
            "He jerks a thumb toward the Sorting Spine. 'Rummage the sorting bins. One unclaimed mechanism, small enough to carry. Then get Skiv Weightwire to weigh it. After that, the Ledger Hall stamps the claim, Tinker Row tells us what it wants to become, and you bring it back to me.'\r\n"
            "Ruskle grins. 'Finding is luck. Getting a thing all the way through Junk City is work.'\r\n"
            "\r\nNew quest: A Piece Worth Keeping.\r\n"
            "Go to the Sorting Spine and RUMMAGE SORTING BINS.\r\n"
        )
        return

    if quest.get("status") == "completed" or _completion_is_recorded(session):
        _reconcile_persistent_state(session)
        await session.send(
            "\r\nRuskle gives you a quick nod. 'Your name is already in the book. Next time you drag something useful out of a pile, nobody gets to call you completely new.'\r\n"
        )
        return

    step = str(quest.get("current_step") or "")
    if step == "return_broker":
        if not _has_salvage(session):
            _reconcile_persistent_state(session)
        if not _has_salvage(session):
            await session.send(
                "\r\nRuskle frowns at the ledger strip and your empty hands. 'The claim says the regulator still exists. Go back through the route and find out who misplaced it.'\r\n"
            )
            return

        # The two flags are the one-time reward receipt. They are INSERT OR
        # IGNORE in SQLite, so reconnects/repeated TALK cannot duplicate credit.
        # Record completion before cleanup; reconciliation removes a leftover
        # item if the process dies between these calls.
        session.database.grant_flag(session.character.id, GOBLIN_SALVAGE_COMPLETE_FLAG)
        session.database.grant_flag(session.character.id, GOBLIN_SALVAGE_CREDIT_FLAG)
        session.database.complete_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key)
        _consume_all_salvage(session)
        await session.send(
            "\r\nRuskle turns the repaired regulator over twice, tests the moving spindle with one thumbnail, and finally sets it beneath his counter.\r\n"
            "'There. Found, weighed, claimed, repaired, returned. That's a Junk City object now—not because we made it from nothing, but because six people can tell you exactly what happened to it.'\r\n"
            "He scratches your name onto a narrow broker strip and adds his mark. 'Your first salvage credit is recorded. It isn't money. It means the next Goblin who asks whether you understand how this city works has one less reason to laugh.'\r\n"
            "\r\nQuest complete: A Piece Worth Keeping.\r\n"
        )
        return

    objective = GOBLIN_SALVAGE_QUEST.objective_for_step(step)
    await session.send("\r\nRuskle points you back toward the job already in motion.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")


async def _talk_skiv(session) -> None:
    assert session.character is not None
    _reconcile_persistent_state(session)
    quest = _quest_state(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "weigh_salvage":
        await session.send("\r\nSkiv pats the scale pan. 'Bring me something with a claim worth measuring, then we'll have a conversation.'\r\n")
        return
    if not _has_salvage(session):
        await session.send("\r\nSkiv squints at your hands. 'Scale works better when you put the salvage on it.'\r\n")
        return
    session.database.advance_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "stamp_claim")
    await session.send(
        "\r\nSkiv wipes the largest clump of dirt from the copper regulator, places it on a hanging scale, and shifts three battered brass weights until the beam settles.\r\n"
        "'Two point six by old lane measure. Copper body, mixed spring steel, no live claim.' Skiv loops a yellow weight tag through the bent cage. 'Now it exists officially enough to argue about. Take it east through Patchwork Plaza to the Ledger Hall. TALK NALLA.'\r\n"
        "Quest updated: A Piece Worth Keeping.\r\n"
    )


async def _talk_nalla(session) -> None:
    assert session.character is not None
    _reconcile_persistent_state(session)
    quest = _quest_state(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "stamp_claim":
        await session.send("\r\nNalla keeps writing. 'Bring me a weighed claim or a dispute. Preferably the first one.'\r\n")
        return
    if not _has_salvage(session):
        await session.send("\r\nNalla holds out one ink-stained hand. 'The object is part of the paperwork.'\r\n")
        return
    session.database.advance_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "repair_salvage")
    await session.send(
        "\r\nNalla reads Skiv's weight tag, turns three ledger pages, and finds no active claim matching the regulator. She stamps a small brass-edged tag and crimps it around the copper cage.\r\n"
        "'Now if someone says it was theirs yesterday, they get to prove it.' She slides the regulator back. 'Tinker Row. Brin Copperhand. Let a repairer tell you whether you found treasure or a very official doorstop.'\r\n"
        "Quest updated: A Piece Worth Keeping.\r\n"
    )


async def _talk_brin(session) -> None:
    assert session.character is not None
    _reconcile_persistent_state(session)
    quest = _quest_state(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "repair_salvage":
        await session.send("\r\nBrin adjusts the cracked lens. 'If it isn't broken, interesting, or both, put it on somebody else's bench.'\r\n")
        return
    if not _has_salvage(session):
        await session.send("\r\nBrin looks at the empty bench space in front of you. 'Invisible repairs cost extra.'\r\n")
        return
    session.database.advance_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "return_broker")
    await session.send(
        "\r\nBrin turns the regulator under the cracked lens, straightens the spring cage in a vise, files the broken mounting ear square, and replaces a missing pin with one cut from a larger machine.\r\n"
        "'Old pressure regulator. Not rare. Not worthless. It'll regulate something again if Ruskle finds the right something.' Brin scratches a repair mark beside Nalla's claim stamp and hands it back. 'That's the whole trick. We don't need to know what it used to belong to.'\r\n"
        "Return to Ruskle Coil in Brassgut Market and TALK RUSKLE.\r\n"
        "Quest updated: A Piece Worth Keeping.\r\n"
    )


async def _handle_quest_talk(session, target: str) -> bool:
    if session.character is None:
        return False
    room_key = session.character.current_room or ""

    ruskle = legacy_world.NPCS_BY_KEY.get("goblin_ruskle_coil")
    if room_key == GOBLIN_BRASSGUT_MARKET_KEY and _matches_name(
        target, ruskle, ("broker", "salvage broker")
    ):
        await _talk_ruskle(session)
        return True
    if room_key == GOBLIN_SORTING_SPINE_KEY and _matches_name(
        target, SKIV_WEIGHTWIRE, ("scale clerk", "weighmaster", "weighing clerk")
    ):
        await _talk_skiv(session)
        return True
    if room_key == GOBLIN_LEDGER_HALL_KEY and _matches_name(
        target, NALLA_INKTHUMB, ("ledger clerk", "claim clerk")
    ):
        await _talk_nalla(session)
        return True
    if room_key == GOBLIN_TINKER_ROW_KEY and _matches_name(
        target, BRIN_COPPERHAND, ("repairer", "repair clerk", "tinker")
    ):
        await _talk_brin(session)
        return True
    return False


async def _handle_scavenge(session, normalized: str) -> bool:
    if session.character is None:
        return False
    node = RUMMAGE_NODES.resolve(normalized, session.character.current_room or "")
    if node is None or node.key != GOBLIN_SORTING_RUMMAGE.key:
        return False

    _reconcile_persistent_state(session)
    quest = _quest_state(session)
    if not quest or quest.get("status") != "active" or quest.get("current_step") != "find_salvage":
        return False

    if not _has_salvage(session):
        session.database.add_item(session.character.id, GOBLIN_SALVAGE_ITEM_KEY, 1)
    session.database.advance_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "weigh_salvage")
    await session.send(
        "\r\nYou work through a knee-high bin marked UNKNOWN BUT INTERESTING: broken handles, cracked housings, loose springs, a valve wheel with no valve, and something that might once have been a clock.\r\n"
        "Near the bottom, your fingers close around a heavy copper regulator with a bent spring cage. The old ownership marks have been scraped away, and no fresh claim tag is attached. Ugly, damaged, portable, and potentially useful—exactly what Ruskle asked for.\r\n"
        "You take the Cracked Copper Regulator. Skiv Weightwire is working the scales nearby. TALK SKIV.\r\n"
        "Quest updated: A Piece Worth Keeping.\r\n"
    )
    return True


def install_goblin_salvage_quest_runtime(player_session_class, world_service) -> None:
    install_goblin_salvage_quest_content(world_service)
    if getattr(player_session_class, "_goblin_salvage_quest_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "goblin":
            return
        step = _reconcile_persistent_state(self)
        quest = _quest_state(self)
        if quest and quest.get("status") == "active" and step:
            objective = GOBLIN_SALVAGE_QUEST.objective_for_step(step)
            await self.send("\r\nYour Junk City salvage transaction is still recorded in the ledger.\r\n")
            if objective:
                await self.send(f"Current objective: {objective}\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "goblin":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized == "talk" or normalized.startswith("talk "):
            target = _target_after_talk(command)
            if target and await _handle_quest_talk(self, target):
                return

        if await _handle_scavenge(self, normalized):
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
                "Goblin quest tip: TALK RUSKLE in Brassgut Market can start the safe salvage-economy introduction, A Piece Worth Keeping. RUMMAGE only has special results at explicitly authored rummage nodes.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_salvage_quest_runtime_installed = True
