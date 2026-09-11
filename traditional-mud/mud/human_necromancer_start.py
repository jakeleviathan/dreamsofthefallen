from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.human_blackwall_opening import HUMAN_CARAVAN_COURT_KEY, HUMAN_OPENING_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


HUMAN_SUBSIDENCE_CUT_KEY = "human_blackwall_subsidence_cut"
HUMAN_NECROMANCER_QUEST_KEY = "human_necromancer_work_beneath_wall"
HUMAN_NECROMANCER_COMPLETE_FLAG = "human_necromancer_work_beneath_wall_complete"
HUMAN_NECROMANCER_SITE_INSPECTED_FLAG = "human_necromancer_site_inspected"
HUMAN_NECROMANCER_LIFE_CLEAR_FLAG = "human_necromancer_life_clear"
HUMAN_NECROMANCER_SHORING_INSPECTED_FLAG = "human_necromancer_shoring_inspected"
HUMAN_NECROMANCER_GROWTH_IDENTIFIED_FLAG = "human_necromancer_mortarvine_identified"
HUMAN_NECROMANCER_FIRST_LIFETAP_FLAG = "human_necromancer_first_lifetap"
HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG = "human_necromancer_mortarvine_drained"
HUMAN_NECROMANCER_REMAINS_RECOVERED_FLAG = "human_necromancer_remains_recovered"
HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG = "human_necromancer_tunnel_stable"

TAMSIN_ROOK_KEY = "human_necromancer_tamsin_rook"


HUMAN_NECROMANCER_QUEST = QuestDefinition(
    key=HUMAN_NECROMANCER_QUEST_KEY,
    name="The Work Beneath the Wall",
    style="structured",
    description=(
        "After the Blackwall opening, a Human Necromancer joins a controlled civic salvage job beneath Caravan Court. "
        "A shallow collapse has exposed an older maintenance gallery. The lesson is practical rather than theatrical: confirm that no living person is trapped, understand what is carrying the load, use Minor Life Tap only on a living growth that is actively worsening the structure, recover old Human remains as a person rather than raw material, and leave the tunnel safer than it was found."
    ),
    objective_steps=(
        ("meet_tamsin", "From Caravan Court, go NORTH to the Blackwall Subsidence Cut and TALK TAMSIN."),
        ("inspect_collapse", "EXAMINE COLLAPSE before touching the rubble."),
        ("check_life", "CHECK FOR LIFE before treating anything in the collapse as salvage."),
        ("inspect_shoring", "EXAMINE SHORING and learn where the damaged gallery is still carrying weight."),
        ("inspect_growth", "EXAMINE MORTARVINE before deciding whether necromancy is useful."),
        ("tap_growth", "Use your level-one Necromancer spell precisely with LIFE TAP MORTARVINE."),
        ("recover_remains", "RECOVER REMAINS after the loosened growth exposes the old surveyor."),
        ("verify_tunnel", "CHECK TUNNEL after the crew resets the shore and clears the loose rubble."),
        ("return_tamsin", "TALK TAMSIN once the gallery is stable."),
        ("complete", "You learned that Human necromancy can be civic work: distinguish rescue from salvage, power from permission, and useful intervention from spectacle."),
    ),
)


TAMSIN_ROOK = NpcDefinition(
    key=TAMSIN_ROOK_KEY,
    name="Necromancer Tamsin Rook",
    short_description=(
        "a Human civic necromancer in a soot-grey work coat, kneeling beside a shoring diagram with chalk, gloves, and a coil of survey cord"
    ),
    room_key=HUMAN_SUBSIDENCE_CUT_KEY,
    role="Human Necromancer mentor and Blackwall civic salvage specialist",
    dialogue=(
        "Tamsin folds the shoring diagram once. 'A tunnel does not care what our robes mean. It cares whether we leave the load safer than we found it.'",
        "'Necromancy is very good at making people imagine the most dramatic possible use of necromancy. Most useful work is less impressed with itself.'",
        "'Stone, timber, brass: salvage. A person is recovery. Learn the difference before you learn stronger spells.'",
    ),
)


HUMAN_SUBSIDENCE_CUT = RoomDefinition(
    key=HUMAN_SUBSIDENCE_CUT_KEY,
    name="Blackwall Subsidence Cut",
    region_key="human_kingdom",
    description=(
        "A fenced public-works cut has been opened beneath the north edge of Caravan Court where a patch of freight paving settled after heavy rain. The surface collapse proved shallow, but it exposed an older maintenance gallery running beside Blackwall's foundations. "
        "Fresh timber shores, chalk load marks, rubble sleds, lanterns, and canvas dust screens make the place look more like a municipal repair job than an adventure. The watch has already completed a headcount and closed the lane above; nobody is waiting for a hero to dive into an active cave-in. "
        "At the back of the cut, pale mortarvine has pushed through an old drainage seam and wrapped itself around cracked brick and one tired support. Beneath it, a bronze badge and part of an old coat show through the rubble."
    ),
    exits={"south": HUMAN_CARAVAN_COURT_KEY},
    npc_keys=(TAMSIN_ROOK_KEY,),
    tags=("safe", "human_start", "necromancer", "blackwall", "civic_work", "salvage", "tunnel", "controlled_site"),
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


def human_necromancer_augmentations() -> dict[str, RoomAugmentation]:
    growth_present = ViewCondition(forbidden_flags=(HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG,))
    growth_drained = ViewCondition(required_flags=(HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG,))
    remains_recovered = ViewCondition(required_flags=(HUMAN_NECROMANCER_REMAINS_RECOVERED_FLAG,))
    tunnel_stable = ViewCondition(required_flags=(HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG,))
    tunnel_unstable = ViewCondition(forbidden_flags=(HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG,))

    return {
        HUMAN_SUBSIDENCE_CUT_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "south",
                    HUMAN_CARAVAN_COURT_KEY,
                    "Caravan Court",
                    travel_text="You climb south out of the public-works cut into the paved freight court.",
                ),
            ),
            features=(
                _feature(
                    "subsidence_collapse",
                    "Shallow Collapse",
                    "a controlled rubble slope beneath the settled freight paving, already fenced and lit for public-works inspection",
                    "The collapse is inconvenient rather than catastrophic. Broken paving, old brick, and wet fill have slumped into a forgotten side gallery. Fresh survey stakes show that the current crew has already mapped the surface movement instead of simply sending people underneath it.",
                    ("collapse", "rubble", "rubble slope", "cave-in", "site"),
                ),
                _feature(
                    "subsidence_shoring",
                    "Temporary Shoring",
                    "fresh timber shores carrying the gallery roof around one older cracked support",
                    "Most of the temporary shores are square and well seated. The concern is one older support where a living mortarvine has threaded through the brick around it. Pulling the growth out by force would tug directly on already-cracked masonry.",
                    ("shoring", "shore", "shores", "supports", "support", "timbers"),
                    condition=tunnel_unstable,
                ),
                _feature(
                    "subsidence_mortarvine",
                    "Mortarvine",
                    "a pale rope-thick living vine pressed through a drainage seam and wound around cracked masonry",
                    "The vine is alive and vigorous. Fine roots have entered old mortar joints and swollen there, slowly levering bricks apart. It is not malicious and it is not merely decoration; continuing growth will worsen the load path around the damaged support.",
                    ("mortarvine", "vine", "growth", "roots", "root growth"),
                    condition=growth_present,
                ),
                _feature(
                    "subsidence_drained_vine",
                    "Drained Mortarvine",
                    "the slackened vine lying grey and brittle where it has released the cracked brick",
                    "The growth has lost enough vitality to release its grip without tearing masonry loose with it. The crew has cut the deadened length into short sections for disposal rather than turning a precise intervention into a display.",
                    ("mortarvine", "vine", "drained vine", "growth", "roots"),
                    condition=growth_drained,
                ),
                _feature(
                    "subsidence_old_badge",
                    "Bronze Survey Badge",
                    "a tarnished Blackwall survey badge visible beside old coat cloth beneath the loosened rubble",
                    "The badge carries an obsolete civic mark and a stamped number. The nearby bones are Human. Whatever else can be reclaimed from this gallery, this is evidence of a person who died here long before the current repair crew was born.",
                    ("badge", "survey badge", "bronze badge", "remains", "bones", "surveyor"),
                    condition=growth_drained,
                ),
                _feature(
                    "subsidence_recovery_cloth",
                    "Recovery Cloth",
                    "a clean dark cloth holding the old surveyor's recovered bones, badge, and personal buckles together for the civic archive",
                    "Nothing has been pocketed and nothing has been turned into a catalyst. The remains are labeled with the location and badge number so the archive can identify the worker if the old maintenance rolls survived.",
                    ("recovery cloth", "recovered remains", "remains", "bones", "surveyor"),
                    condition=remains_recovered,
                ),
                _feature(
                    "subsidence_stable_gallery",
                    "Reset Gallery",
                    "the exposed maintenance gallery resting under a new square shore with loose rubble cleared from its drainage edge",
                    "The replacement support is plumb, the cracked bricks are no longer being pulled apart by living roots, and the chalk reference marks have stopped moving. The job looks less dramatic than it did an hour ago, which is a good result for a tunnel beneath a city wall.",
                    ("gallery", "stable gallery", "reset gallery", "tunnel", "new shore"),
                    condition=tunnel_stable,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "subsidence_worksite_detail",
                    "A kettle sits on a brick beside three dented cups. Someone has written DO NOT LEAN ON THIS on the safest-looking timber in the cut, then underlined it twice.",
                    priority=40,
                ),
                DescriptionLayer(
                    "subsidence_growth_released",
                    "With the mortarvine slack, the crew can work around the old support without making living roots part of the structure anymore.",
                    priority=65,
                    condition=growth_drained,
                ),
                DescriptionLayer(
                    "subsidence_recovery_done",
                    "The surveyor's remains lie together on a labeled recovery cloth, separate from the piles of reusable brick and metal.",
                    priority=75,
                    condition=remains_recovered,
                ),
                DescriptionLayer(
                    "subsidence_stable",
                    "The gallery has become boring again: square timber, still chalk marks, a clear drain edge, and no reason for anyone to hurry.",
                    priority=90,
                    condition=tunnel_stable,
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


def _patch_caravan_court() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[HUMAN_CARAVAN_COURT_KEY]
    exits = dict(original.exits)
    exits["north"] = HUMAN_SUBSIDENCE_CUT_KEY
    description = original.description
    if "Subsidence Cut" not in description:
        description += (
            " A fenced work stair descends north beneath the edge of the court into the Blackwall Subsidence Cut, where public-works crews are repairing an exposed old maintenance gallery."
        )
    return replace(original, exits=exits, description=description)


def install_human_necromancer_content(world_service=None) -> None:
    if HUMAN_NECROMANCER_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (HUMAN_NECROMANCER_QUEST,)
    quests.QUESTS_BY_KEY[HUMAN_NECROMANCER_QUEST.key] = HUMAN_NECROMANCER_QUEST

    _replace_room(HUMAN_SUBSIDENCE_CUT)
    _replace_npc(TAMSIN_ROOK)
    caravan_court = _patch_caravan_court()
    _replace_room(caravan_court)

    if world_service is None:
        return

    world_service.legacy_rooms[HUMAN_SUBSIDENCE_CUT_KEY] = HUMAN_SUBSIDENCE_CUT
    world_service.legacy_rooms[HUMAN_CARAVAN_COURT_KEY] = caravan_court
    world_service.augmentations.update(human_necromancer_augmentations())

    base = world_service.augmentations.get(HUMAN_CARAVAN_COURT_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "north"]
    exits.append(
        ExitDefinition(
            "north",
            HUMAN_SUBSIDENCE_CUT_KEY,
            "Blackwall Subsidence Cut",
            travel_text="You pass the work fence and descend north beneath Caravan Court into the lantern-lit repair cut.",
        )
    )
    world_service.augmentations[HUMAN_CARAVAN_COURT_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(HUMAN_SUBSIDENCE_CUT_KEY, None)
        cache.pop(HUMAN_CARAVAN_COURT_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "human" and character.character_class == "necromancer")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, HUMAN_NECROMANCER_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_human_necromancer_start(session) -> bool:
    if not _qualifies(session):
        return False
    if HUMAN_OPENING_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "meet_tamsin")
    return True


def _in_cut(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == HUMAN_SUBSIDENCE_CUT_KEY)


async def _talk_tamsin(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session):
        return False
    step = quest.get("current_step")

    if step == "meet_tamsin":
        session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "inspect_collapse")
        await session.send(
            "\r\nTamsin looks past you toward the shoring instead of checking whether you brought a dramatic enough robe.\r\n"
            "'This is a repair job. The lane is closed, the headcount is complete, and nobody is asking you to raise an army under Caravan Court.'\r\n"
            "She points to the rubble slope. 'Before we call anything salvage, EXAMINE COLLAPSE.'\r\n"
        )
        return True

    if step == "return_tamsin":
        session.database.complete_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY)
        session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_COMPLETE_FLAG)
        await session.send(
            "\r\nTamsin checks the new shore, the clear drain edge, and the labeled recovery cloth in that order.\r\n"
            "'Good. You confirmed there was nobody living under the rubble before you treated the site as material. You found the thing still taking from the structure, and you stopped exactly that.'\r\n"
            "She nods toward the surveyor's remains. 'Stone, timber, brass: salvage. A person is recovery. Death does not turn citizenship into inventory.'\r\n"
            "'When you learn Raise Skeleton, remember this room. Being able to animate bone will tell you what is possible. It will not tell you what is yours, what is useful, or what consequences somebody else has to live with afterward.'\r\n"
            "She folds the shoring diagram. 'Human necromancy is still Human work. Leave the wall safer than you found it.'\r\n"
            "\r\nQuest complete: The Work Beneath the Wall.\r\n"
        )
        return True

    objective = HUMAN_NECROMANCER_QUEST.objective_for_step(step)
    await session.send("\r\nTamsin glances toward the current piece of work instead of giving you a second speech.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _examine_collapse(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "inspect_collapse":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_SITE_INSPECTED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "check_life")
    await session.send(
        "\r\nThe settled paving opened only a shallow pocket, but the old gallery continues beneath the wall foundation. Fresh stakes and chalk lines show that the crew has already mapped the movement from above.\r\n"
        "Tamsin says, 'Good. Now do the check that comes before salvage, before remains, before cleverness. CHECK FOR LIFE.'\r\n"
    )
    return True


async def _check_for_life(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "check_life":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_LIFE_CLEAR_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "inspect_shoring")
    await session.send(
        "\r\nYou quiet your attention and read for the coarse signs a Necromancer learns not to confuse with death: breath, heartbeat, warm blood, active animal life caught beneath stone.\r\n"
        "There is life in the cut -- workers, insects, and a stubborn root growth -- but no living person or animal trapped inside the collapse. The old shape under the rubble is still.\r\n"
        "Tamsin nods. 'Now it is a salvage site with remains in it, not a rescue scene we have mislabeled. EXAMINE SHORING.'\r\n"
    )
    return True


async def _examine_shoring(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "inspect_shoring":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_SHORING_INSPECTED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "inspect_growth")
    await session.send(
        "\r\nThe fresh shores are carrying the roof correctly. The weak point is older: mortarvine has rooted through cracked joints around one tired support. If the crew yanks the vine free while it is swollen and gripping, it can bring loose brick with it.\r\n"
        "Tamsin taps the living growth with a chalk stick. 'There is something here our craft can change without pretending it can solve masonry. EXAMINE MORTARVINE.'\r\n"
    )
    return True


async def _examine_growth(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "inspect_growth":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_GROWTH_IDENTIFIED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "tap_growth")
    await session.send(
        "\r\nThe mortarvine is vigorous enough that its fine roots are widening old joints as they swell. Draining some vitality will make the growth slack and brittle, letting the crew cut it away without pulling against the wall.\r\n"
        "It is a living thing, and the choice is deliberate: leave it here and the structure worsens; remove it carefully and the gallery can be repaired.\r\n"
        "Tamsin says, 'Use the smallest tool that does the job. LIFE TAP MORTARVINE.'\r\n"
    )
    return True


async def _life_tap_growth(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "tap_growth":
        return False
    flags = _flags(session)
    if HUMAN_NECROMANCER_FIRST_LIFETAP_FLAG not in flags:
        session.database.record_ability_use(session.character.id, "minor_life_tap", skill_xp_gain=1)
        session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_FIRST_LIFETAP_FLAG)
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "recover_remains")
    await session.send(
        "\r\nYou draw only enough vitality from the mortarvine to break its swollen grip. The pale cords grey, slacken, and release the cracked joints one by one.\r\n"
        "The crew cuts the brittle lengths away and slides a replacement shore into the space without a shower of bricks, applause, or purple fire.\r\n"
        "As the last roots come free, an old bronze survey badge and Human bones are exposed beneath the rubble. Tamsin says, 'Now the vocabulary changes. RECOVER REMAINS.'\r\n"
    )
    return True


async def _recover_remains(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "recover_remains":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_REMAINS_RECOVERED_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "verify_tunnel")
    await session.send(
        "\r\nYou and Tamsin lift the bones onto a clean recovery cloth, keeping the badge, buckles, and location tag together. The stamped number can be checked against old Blackwall maintenance rolls.\r\n"
        "Tamsin separates a bent brass bracket into the salvage sled, then leaves the bones where they are. 'Same collapse. Different obligations.'\r\n"
        "Behind you, the crew seats the new shore and clears the drain edge. CHECK TUNNEL before anyone reopens the work lane.\r\n"
    )
    return True


async def _check_tunnel(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session) or quest.get("current_step") != "verify_tunnel":
        return False
    session.database.grant_flag(session.character.id, HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG)
    session.database.advance_quest(session.character.id, HUMAN_NECROMANCER_QUEST_KEY, "return_tamsin")
    await session.send(
        "\r\nThe replacement shore is square. The chalk reference marks have not moved. The drainage seam is clear, and no living root is carrying hidden force through the damaged brick anymore.\r\n"
        "Nothing about the result looks magical. The gallery is simply safer and easier to understand than it was when you arrived.\r\n"
        "Tamsin says, 'That is the part people forget to check. TALK TAMSIN.'\r\n"
    )
    return True


async def _refuse_bad_necromancy(session, normalized: str) -> bool:
    quest = _quest(session)
    if quest is None or not _in_cut(session):
        return False
    if normalized in {
        "raise skeleton",
        "raise remains",
        "animate remains",
        "animate bones",
        "life tap remains",
        "life tap bones",
        "life tap surveyor",
    }:
        await session.send(
            "\r\nTamsin's answer is immediate. 'No. We have not established a useful reason, permission, or even the right problem for that. Necromancy is not permission to turn the first dead thing you notice into equipment.'\r\n"
        )
        return True
    if normalized == "life tap mortarvine" and quest.get("current_step") != "tap_growth":
        await session.send(
            "\r\nTamsin puts the chalk stick between you and the vine. 'Not yet. A spell is not a substitute for knowing what is carrying the load. Inspect first.'\r\n"
        )
        return True
    return False


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


def install_human_necromancer_runtime(player_session_class, world_service=None) -> None:
    """Add a dedicated Human Necromancer extension after the Blackwall opening."""
    if getattr(player_session_class, "_human_necromancer_runtime_installed", False):
        return

    install_human_necromancer_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_human_necromancer_start(self):
            await self.send(
                "\r\nA Blackwall public-works runner finds you with a chalk-stained work slip from Necromancer Tamsin Rook.\r\n"
                "'Subsidence repair under Caravan Court. Controlled site, no emergency. Tamsin asked for a Necromancer who can tell the difference.'\r\n"
                "\r\nNew quest: The Work Beneath the Wall.\r\n"
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
        if normalized in {"talk tamsin", "talk to tamsin"}:
            handled = await _talk_tamsin(self)
        elif normalized in {"examine collapse", "look collapse", "inspect collapse"}:
            handled = await _examine_collapse(self)
        elif normalized in {"check for life", "check life", "sense life"}:
            handled = await _check_for_life(self)
        elif normalized in {"examine shoring", "inspect shoring", "look shoring"}:
            handled = await _examine_shoring(self)
        elif normalized in {"examine mortarvine", "inspect mortarvine", "look mortarvine", "examine vine"}:
            handled = await _examine_growth(self)
        elif normalized == "life tap mortarvine":
            handled = await _life_tap_growth(self)
            if not handled:
                handled = await _refuse_bad_necromancy(self, normalized)
        elif normalized in {"recover remains", "recover surveyor", "collect remains"}:
            handled = await _recover_remains(self)
        elif normalized in {"check tunnel", "check gallery", "verify tunnel", "inspect tunnel"}:
            handled = await _check_tunnel(self)
        else:
            handled = await _refuse_bad_necromancy(self, normalized)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_human_necromancer_start(self):
            await self.send(
                "\r\nWith your first Blackwall circuit complete, a public-works runner catches up with you near Caravan Court.\r\n"
                "'Necromancer Tamsin Rook has a controlled subsidence job under the freight paving. She said it is salvage work, not theater. North side of the court.'\r\n"
                "\r\nNew quest: The Work Beneath the Wall.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._human_necromancer_runtime_installed = True
