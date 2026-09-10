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
from mud.world import NpcDefinition, RoomDefinition


GOBLIN_SALVAGE_ITEM_KEY = "cracked_copper_regulator"
GOBLIN_SALVAGE_COMPLETE_FLAG = "goblin_first_salvage_loop_completed"
GOBLIN_SALVAGE_CREDIT_FLAG = "goblin_salvage_credit_established"

GOBLIN_SALVAGE_QUEST = QuestDefinition(
    key="goblin_from_scrap_to_claim",
    name="From Scrap to Claim",
    style="structured",
    description=(
        "Ruskle Coil sends a new Goblin through Junk City's salvage economy: find a useful discarded part, "
        "have it weighed, put the claim into the ledger, carry it to Tinker Row for repair, and return it to the broker. "
        "The route teaches how Goblin ownership, repair, and trade fit together without requiring combat."
    ),
    objective_steps=(
        ("find_salvage", "Go to the Sorting Spine and SEARCH SORTING BINS for one unclaimed part worth carrying."),
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

SKIV_WEIGHTWIRE = NpcDefinition(
    key="goblin_skiv_weightwire",
    name="Skiv Weightwire",
    short_description="a scale clerk balancing salvage baskets against scarred brass weights",
    room_key=GOBLIN_SORTING_SPINE_KEY,
    role="starter salvage weighmaster",
    dialogue=(
        "Skiv taps the nearest scale pan. 'Finding it is only the first half. Weight tells the lanes what moved, and the ledger tells everybody whose problem it becomes next.'",
    ),
)

NALLA_INKTHUMB = NpcDefinition(
    key="goblin_nalla_inkthumb",
    name="Nalla Inkthumb",
    short_description="a ledger clerk with black-stained fingers and a belt full of brass claim stamps",
    room_key=GOBLIN_LEDGER_HALL_KEY,
    role="starter salvage claim clerk",
    dialogue=(
        "Nalla holds up one ink-black thumb. 'A mark says you touched it. A ledger says the city remembers you touched it. Those are different things.'",
    ),
)

BRIN_COPPERHAND = NpcDefinition(
    key="goblin_brin_copperhand",
    name="Brin Copperhand",
    short_description="a repairer peering through a cracked lens while sorting springs by tension",
    room_key=GOBLIN_TINKER_ROW_KEY,
    role="starter salvage repairer",
    dialogue=(
        "Brin does not look up from the bench. 'Broken is a condition. Useless is an opinion. Put the interesting bit down.'",
    ),
)

GOBLIN_SALVAGE_NPCS: tuple[NpcDefinition, ...] = (
    SKIV_WEIGHTWIRE,
    NALLA_INKTHUMB,
    BRIN_COPPERHAND,
)


def _room_with_npc(room: RoomDefinition, npc_key: str) -> RoomDefinition:
    if npc_key in room.npc_keys:
        return room
    return replace(room, npc_keys=room.npc_keys + (npc_key,))


def install_goblin_salvage_quest_content(world_service=None) -> None:
    """Register the starter salvage quest, its item, and its three civic contacts.

    Registration is deliberately idempotent. The existing session module imports
    shared registry dictionaries by reference, so updating those dictionaries
    makes the new quest/item/NPCs visible without duplicating the entire session
    command layer.
    """
    if GOBLIN_SALVAGE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GOBLIN_SALVAGE_QUEST,)
        quests.QUESTS_BY_KEY[GOBLIN_SALVAGE_QUEST.key] = GOBLIN_SALVAGE_QUEST

    if GOBLIN_SALVAGE_ITEM.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (GOBLIN_SALVAGE_ITEM,)
        crafting.ITEMS_BY_KEY[GOBLIN_SALVAGE_ITEM.key] = GOBLIN_SALVAGE_ITEM

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
        for room_key in replacements:
            world_service._scene_cache.pop(room_key, None)


def _target_after_talk(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _matches_name(target: str, npc: NpcDefinition) -> bool:
    aliases = {
        npc.name.lower(),
        npc.key.replace("_", " "),
        npc.name.lower().split()[0],
        npc.name.lower().split()[-1],
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


async def _talk_ruskle(session) -> None:
    assert session.character is not None
    quest = _quest_state(session)
    if quest is None:
        session.database.start_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key, "find_salvage")
        await session.send(
            "\r\nRuskle Coil hooks one measuring tape back over his shoulder. 'Want a real lesson? Don't buy anything. Find me something the city nearly threw away.'\r\n"
            "He jerks a thumb toward the Sorting Spine. 'Rummage the sorting bins. One unclaimed mechanism, small enough to carry. Then get Skiv Weightwire to weigh it. After that, the Ledger Hall stamps the claim, Tinker Row tells us what it wants to become, and you bring it back to me.'\r\n"
            "Ruskle grins. 'Finding is luck. Getting a thing all the way through Junk City is work.'\r\n"
            "\r\nNew quest: From Scrap to Claim.\r\n"
            "Go to the Sorting Spine and SEARCH SORTING BINS.\r\n"
        )
        return

    if quest.get("status") == "completed":
        await session.send(
            "\r\nRuskle gives you a quick nod. 'Your name is already in the book. Next time you drag something useful out of a pile, nobody gets to call you completely new.'\r\n"
        )
        return

    step = str(quest.get("current_step") or "")
    if step == "return_broker":
        if not _has_salvage(session):
            await session.send(
                "\r\nRuskle looks at your empty hands. 'You did the paperwork and forgot the object? Go find the regulator before we make that a story people repeat.'\r\n"
            )
            return
        session.database.consume_item(session.character.id, GOBLIN_SALVAGE_ITEM_KEY, 1)
        session.database.complete_quest(session.character.id, GOBLIN_SALVAGE_QUEST.key)
        session.database.grant_flag(session.character.id, GOBLIN_SALVAGE_COMPLETE_FLAG)
        session.database.grant_flag(session.character.id, GOBLIN_SALVAGE_CREDIT_FLAG)
        await session.send(
            "\r\nRuskle turns the repaired regulator over twice, tests the moving spindle with one thumbnail, and finally sets it beneath his counter.\r\n"
            "'There. Found, weighed, claimed, repaired, returned. That's a Junk City object now—not because we made it from nothing, but because six people can tell you exactly what happened to it.'\r\n"
            "He scratches your name onto a narrow broker strip and adds his mark. 'Your first salvage credit is recorded. It isn't money. It means the next Goblin who asks whether you understand how this city works has one less reason to laugh.'\r\n"
            "\r\nQuest complete: From Scrap to Claim.\r\n"
        )
        return

    objective = GOBLIN_SALVAGE_QUEST.objective_for_step(step)
    await session.send("\r\nRuskle points you back toward the job already in motion.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")


async def _talk_skiv(session) -> None:
    assert session.character is not None
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
        "Quest updated: From Scrap to Claim.\r\n"
    )


async def _talk_nalla(session) -> None:
    assert session.character is not None
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
        "Quest updated: From Scrap to Claim.\r\n"
    )


async def _talk_brin(session) -> None:
    assert session.character is not None
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
        "Quest updated: From Scrap to Claim.\r\n"
    )


async def _handle_quest_talk(session, target: str) -> bool:
    if session.character is None:
        return False
    room_key = session.character.current_room or ""

    if room_key == GOBLIN_BRASSGUT_MARKET_KEY and target and _matches_name(target, legacy_world.NPCS_BY_KEY.get("goblin_ruskle_coil")):
        await _talk_ruskle(session)
        return True
    if room_key == GOBLIN_SORTING_SPINE_KEY and _matches_name(target, SKIV_WEIGHTWIRE):
        await _talk_skiv(session)
        return True
    if room_key == GOBLIN_LEDGER_HALL_KEY and _matches_name(target, NALLA_INKTHUMB):
        await _talk_nalla(session)
        return True
    if room_key == GOBLIN_TINKER_ROW_KEY and _matches_name(target, BRIN_COPPERHAND):
        await _talk_brin(session)
        return True
    return False


async def _handle_scavenge(session, normalized: str) -> bool:
    if session.character is None or session.character.current_room != GOBLIN_SORTING_SPINE_KEY:
        return False
    if not (normalized.startswith("search ") or normalized.startswith("rummage ")):
        return False
    target = normalized.split(maxsplit=1)[1] if " " in normalized else ""
    useful_words = ("bin", "bins", "chute", "chutes", "salvage", "sorting", "pile", "mechanism", "unknown")
    if not any(word in target for word in useful_words):
        return False

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
        "Quest updated: From Scrap to Claim.\r\n"
    )
    return True


def install_goblin_salvage_quest_runtime(player_session_class, world_service) -> None:
    install_goblin_salvage_quest_content(world_service)
    if getattr(player_session_class, "_goblin_salvage_quest_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

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
                "Goblin quest tip: TALK RUSKLE in Brassgut Market can start the safe salvage-economy introduction, From Scrap to Claim.\r\n"
            )

    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_salvage_quest_runtime_installed = True
