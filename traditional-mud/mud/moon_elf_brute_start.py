from __future__ import annotations

from dataclasses import replace

import mud.quests as quests
import mud.world as legacy_world
from mud.moon_elf_city import MOON_ELF_HORIZON_DECK_KEY, MOON_ELF_REGION_KEY
from mud.moon_elf_third_chair import MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_HIGH_SPAN_WALK_KEY = "moon_elf_high_span_service_walk"
MOON_ELF_BRUTE_QUEST_KEY = "moon_elf_brute_before_you_lift"
MOON_ELF_BRUTE_COMPLETE_FLAG = "moon_elf_brute_before_you_lift_complete"
MOON_ELF_BRUTE_FRAME_INSPECTED_FLAG = "moon_elf_brute_frame_inspected"
MOON_ELF_BRUTE_INNER_VIEW_FLAG = "moon_elf_brute_inner_view"
MOON_ELF_BRUTE_OUTER_VIEW_FLAG = "moon_elf_brute_outer_view"
MOON_ELF_BRUTE_STRAIN_FOUND_FLAG = "moon_elf_brute_strain_found"
MOON_ELF_BRUTE_BRACE_SET_FLAG = "moon_elf_brute_brace_set"
MOON_ELF_BRUTE_WEIGHT_TAKEN_FLAG = "moon_elf_brute_weight_taken"
MOON_ELF_BRUTE_MECHANISM_RESET_FLAG = "moon_elf_brute_mechanism_reset"
MOON_ELF_BRUTE_FRAME_STABLE_FLAG = "moon_elf_brute_frame_stable"

KALEN_SORR_KEY = "moon_elf_brute_kalen_sorr"


MOON_ELF_BRUTE_QUEST = QuestDefinition(
    key=MOON_ELF_BRUTE_QUEST_KEY,
    name="Before You Lift",
    style="structured",
    description=(
        "After The Third Chair, a Moon Elf Brute is sent to a high service walk where a suspended supply frame has shifted out of square. "
        "The first view makes the job look like a simple shove. The second reveals that one loaded sling is carrying the strain diagonally through a guide bracket. The lesson is to understand the weight before using strength: compare views, brace the load, take only the weight the crew needs removed, hold steady while the mechanism is reset, then verify the result."
    ),
    objective_steps=(
        ("meet_kalen", "From the Horizon Deck, go SOUTH to the High Span Service Walk and TALK KALEN."),
        ("inspect_frame", "EXAMINE SUPPLY FRAME before trying to move it."),
        ("compare_views", "VIEW FROM INNER RAIL and VIEW FROM OUTER RAIL. Both views are required."),
        ("check_strain", "CHECK STRAIN after comparing both sides of the load."),
        ("set_brace", "SET SAFETY BRACE before putting your body under the load."),
        ("take_weight", "TAKE WEIGHT in the marked stance. Do not try to lift the whole frame free."),
        ("hold_steady", "HOLD STEADY while the rigging crew resets the sling drum and guide bracket."),
        ("verify_frame", "CHECK FRAME after the weight is back on the mechanism."),
        ("return_kalen", "TALK KALEN after the frame is stable."),
        ("complete", "You learned that strength is responsibility: know what you are carrying before you decide you can carry it."),
    ),
)


KALEN_SORR = NpcDefinition(
    key=KALEN_SORR_KEY,
    name="Brute Kalen Sorr",
    short_description=(
        "a broad-shouldered Moon Elf Brute in a clipped safety harness, checking sling tension with a chalked thumb while two riggers wait by a hand drum"
    ),
    room_key=MOON_ELF_HIGH_SPAN_WALK_KEY,
    role="Moon Elf Brute mentor and high-span load safety keeper",
    dialogue=(
        "Kalen rests one hand on the rail. 'Strength does not make your first judgment heavier than everyone else's. It only makes a bad judgment more expensive.'",
        "'Know what you are carrying before you decide you can carry it.'",
        "'A Brute is useful when force has somewhere responsible to go. If the safest answer is hold, then holding is the work.'",
    ),
)


MOON_ELF_HIGH_SPAN_WALK = RoomDefinition(
    key=MOON_ELF_HIGH_SPAN_WALK_KEY,
    name="High Span Service Walk",
    region_key=MOON_ELF_REGION_KEY,
    description=(
        "A fenced service walk runs just below the Horizon Deck along the outer ribs of Skyglass Spire. Counterweighted supply cages stop here so food, water, glass, tools, and household freight can be transferred to upper floors without carrying every crate through the public lookout. "
        "Today one suspended supply frame hangs a little crooked between two guide posts. A loaded sling disappears upward into a hand-drum mechanism while a second sling hangs visibly slacker. The walkway is broad, dry, and built for maintenance; nobody is dangling over open air, and the crew has already closed the transfer lane until the frame is made safe."
    ),
    exits={"north": MOON_ELF_HORIZON_DECK_KEY},
    npc_keys=(KALEN_SORR_KEY,),
    tags=("safe", "moon_elf_start", "brute", "service_walk", "rigging", "civic_work", "perspective"),
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


def moon_elf_brute_augmentations() -> dict[str, RoomAugmentation]:
    both_views = ViewCondition(required_flags=(MOON_ELF_BRUTE_INNER_VIEW_FLAG, MOON_ELF_BRUTE_OUTER_VIEW_FLAG))
    strain_found = ViewCondition(required_flags=(MOON_ELF_BRUTE_STRAIN_FOUND_FLAG,))
    brace_set = ViewCondition(required_flags=(MOON_ELF_BRUTE_BRACE_SET_FLAG,))
    weight_taken = ViewCondition(required_flags=(MOON_ELF_BRUTE_WEIGHT_TAKEN_FLAG,))
    reset = ViewCondition(required_flags=(MOON_ELF_BRUTE_MECHANISM_RESET_FLAG,))
    stable = ViewCondition(required_flags=(MOON_ELF_BRUTE_FRAME_STABLE_FLAG,))
    not_stable = ViewCondition(forbidden_flags=(MOON_ELF_BRUTE_FRAME_STABLE_FLAG,))

    return {
        MOON_ELF_HIGH_SPAN_WALK_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "north",
                    MOON_ELF_HORIZON_DECK_KEY,
                    "Horizon Deck",
                    travel_text="You leave the closed transfer lane and climb north onto the broad public Horizon Deck.",
                ),
            ),
            features=(
                _feature(
                    "high_span_supply_frame",
                    "Suspended Supply Frame",
                    "a rectangular freight frame hanging slightly low on its outer corner between two guide posts",
                    "The frame is carrying sealed water jars, sacks of meal, and a crate of lamp glass. From the center of the walkway it looks as though one hard shove upward would square it. The load is real and awkward, but the visible tilt alone does not explain where the strain is traveling.",
                    ("frame", "supply frame", "suspended frame", "freight frame", "load"),
                ),
                _feature(
                    "high_span_inner_rail",
                    "Inner Sighting Rail",
                    "a waist-high marked rail on the tower side of the transfer lane",
                    "The inner rail gives a clean view of the frame face and both lower guide shoes. From here the outer corner looks plainly low, making a direct upward shove seem almost embarrassingly obvious.",
                    ("inner rail", "inner sight", "tower rail", "inside rail"),
                ),
                _feature(
                    "high_span_outer_rail",
                    "Outer Sighting Rail",
                    "a matching marked rail on the valley side of the service walk",
                    "From the outer rail, the apparently simple tilt changes character. The far sling is drawn tight on a diagonal while the near sling is slack, and the upper guide bracket is being pulled sideways instead of merely downward.",
                    ("outer rail", "outer sight", "valley rail", "outside rail"),
                ),
                _feature(
                    "high_span_strain_path",
                    "Diagonal Strain Path",
                    "a taut far sling carrying load sideways through the upper guide bracket",
                    "With both views compared, the danger is clear. Shoving the low corner straight upward would load the already-twisted guide bracket even harder. If it sheared, the frame could swing across the work lane. The safe job is to remove just enough weight for the riggers to reseat the sling drum and bracket.",
                    ("strain", "strain path", "diagonal strain", "taut sling", "guide bracket", "bracket"),
                    condition=both_views,
                ),
                _feature(
                    "high_span_safety_brace",
                    "Safety Brace",
                    "a stout adjustable timber brace locked between the frame base and a floor socket",
                    "The brace is not meant to carry the whole load. It prevents a sudden lateral swing if the rigging shifts while someone is taking weight by hand. It turns strength from the only safety measure into one part of a safer system.",
                    ("brace", "safety brace", "timber brace", "floor brace"),
                    condition=brace_set,
                ),
                _feature(
                    "high_span_marked_stance",
                    "Marked Load Stance",
                    "two chalk foot marks beneath the frame where a lifter can take controlled weight without standing under the guide hardware",
                    "The stance keeps your shoulders under the frame rail while leaving your head and hands clear of the bracket above. It is designed for taking part of the load, not proving that one person can lift everything.",
                    ("stance", "marked stance", "foot marks", "load stance"),
                    condition=strain_found,
                ),
                _feature(
                    "high_span_reset_rigging",
                    "Reset Rigging",
                    "the sling drum and upper guide bracket sitting square again after the crew's adjustment",
                    "The far sling now runs vertically instead of pulling across the bracket. The drum teeth are seated, the guide bolts are true to their paint marks, and the frame is ready to take its own weight again.",
                    ("rigging", "reset rigging", "sling drum", "drum", "guide"),
                    condition=reset,
                ),
                _feature(
                    "high_span_stable_frame",
                    "Stable Supply Frame",
                    "the freight frame hanging square between its guides with both slings sharing the load",
                    "The jars, meal sacks, and lamp glass are exactly where they were before. The success is not that something impressive moved. It is that the frame is boring again and the transfer lane can reopen safely.",
                    ("stable frame", "square frame", "repaired frame", "frame"),
                    condition=stable,
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "high_span_shifted_load",
                    "The supply frame hangs visibly crooked, inviting the kind of quick physical answer that would be satisfying for about half a second.",
                    priority=45,
                    condition=not_stable,
                ),
                DescriptionLayer(
                    "high_span_views_compared",
                    "From two sides, the load tells a different story: the low corner is only the visible symptom, while the real problem runs diagonally through the far sling and upper guide.",
                    priority=60,
                    condition=both_views,
                ),
                DescriptionLayer(
                    "high_span_weight_held",
                    "With the brace locked and part of the frame's weight resting through your stance, the riggers can work the mechanism without asking your strength to do their job too.",
                    priority=70,
                    condition=weight_taken,
                ),
                DescriptionLayer(
                    "high_span_stable",
                    "The supply frame now hangs square and unremarkable. The crew has reopened the transfer lane, which is exactly what successful maintenance is supposed to look like.",
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


def _patch_horizon_deck() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[MOON_ELF_HORIZON_DECK_KEY]
    exits = dict(original.exits)
    exits["south"] = MOON_ELF_HIGH_SPAN_WALK_KEY
    description = original.description
    if "High Span Service Walk" not in description:
        description += (
            " A gated maintenance stair descends south to the High Span Service Walk, where upper-floor freight is transferred from counterweighted supply cages."
        )
    return replace(original, exits=exits, description=description)


def install_moon_elf_brute_content(world_service=None) -> None:
    if MOON_ELF_BRUTE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (MOON_ELF_BRUTE_QUEST,)
    quests.QUESTS_BY_KEY[MOON_ELF_BRUTE_QUEST.key] = MOON_ELF_BRUTE_QUEST

    _replace_room(MOON_ELF_HIGH_SPAN_WALK)
    _replace_npc(KALEN_SORR)
    horizon_deck = _patch_horizon_deck()
    _replace_room(horizon_deck)

    if world_service is None:
        return

    world_service.legacy_rooms[MOON_ELF_HIGH_SPAN_WALK_KEY] = MOON_ELF_HIGH_SPAN_WALK
    world_service.legacy_rooms[MOON_ELF_HORIZON_DECK_KEY] = horizon_deck
    world_service.augmentations.update(moon_elf_brute_augmentations())

    base = world_service.augmentations.get(MOON_ELF_HORIZON_DECK_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "south"]
    exits.append(
        ExitDefinition(
            "south",
            MOON_ELF_HIGH_SPAN_WALK_KEY,
            "High Span Service Walk",
            travel_text="You descend the gated maintenance stair south from the Horizon Deck to the closed freight transfer lane.",
        )
    )
    world_service.augmentations[MOON_ELF_HORIZON_DECK_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(MOON_ELF_HIGH_SPAN_WALK_KEY, None)
        cache.pop(MOON_ELF_HORIZON_DECK_KEY, None)


def _qualifies(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "moon_elf" and character.character_class == "brute")


def _quest(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return session.database.get_quest(character.id, MOON_ELF_BRUTE_QUEST_KEY)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _reconcile_brute_start(session) -> bool:
    if not _qualifies(session):
        return False
    if MOON_ELF_THIRD_CHAIR_COMPLETE_FLAG not in _flags(session):
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "meet_kalen")
    return True


def _in_walk(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.current_room == MOON_ELF_HIGH_SPAN_WALK_KEY)


async def _talk_kalen(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session):
        return False
    step = quest.get("current_step")

    if step == "meet_kalen":
        session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "inspect_frame")
        await session.send(
            "\r\nKalen does not ask you to lift anything when you arrive. He points at the crooked freight frame and then at the closed transfer gate.\r\n"
            "'From here it looks simple: low corner, strong arms, push up. That is an observation, not a plan.'\r\n"
            "He folds his arms. 'Strength does not make your first judgment heavier than everyone else's. EXAMINE SUPPLY FRAME.'\r\n"
        )
        return True

    if step == "return_kalen":
        session.database.complete_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY)
        session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_COMPLETE_FLAG)
        await session.send(
            "\r\nKalen checks the frame from the inner rail, crosses to the outer rail, and checks the sling marks before he opens the transfer gate.\r\n"
            "'Good. You could have moved more weight than we asked you to. That was never the point.'\r\n"
            "He taps the now-straight guide bracket. 'A Brute is not the person who proves they can overpower the problem. A Brute is the person who can put force exactly where the situation can safely afford it.'\r\n"
            "Kalen looks back at the load. 'Know what you are carrying before you decide you can carry it.'\r\n"
            "\r\nQuest complete: Before You Lift.\r\n"
        )
        return True

    objective = MOON_ELF_BRUTE_QUEST.objective_for_step(step)
    await session.send(
        "\r\nKalen nods toward the rigging. 'Do the part that makes the next part safe. Strength is not a reason to skip information.'\r\n"
    )
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _inspect_frame(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "inspect_frame":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_FRAME_INSPECTED_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "compare_views")
    await session.send(
        "\r\nThe frame is heavy but intact. Nothing is falling, the cargo lashings are sound, and both guide posts are still anchored. The outer corner hangs low enough that a direct shove feels obvious.\r\n"
        "Kalen says, 'Obvious is where we begin. Not where we stop. VIEW FROM INNER RAIL and VIEW FROM OUTER RAIL.'\r\n"
    )
    return True


def _maybe_finish_views(session) -> bool:
    flags = _flags(session)
    if {MOON_ELF_BRUTE_INNER_VIEW_FLAG, MOON_ELF_BRUTE_OUTER_VIEW_FLAG}.issubset(flags):
        session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "check_strain")
        return True
    return False


async def _view_inner(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_INNER_VIEW_FLAG)
    await session.send(
        "\r\nFrom the inner rail, the problem looks almost insultingly simple. The outer corner is low, the near guide shoe has room above it, and a strong upward push would appear to square the frame.\r\n"
        "Kalen says, 'That view is real. It is also only one view.'\r\n"
    )
    if _maybe_finish_views(session):
        await session.send("You have both views now. CHECK STRAIN before touching the load.\r\n")
    return True


async def _view_outer(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "compare_views":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_OUTER_VIEW_FLAG)
    await session.send(
        "\r\nFrom the outer rail, the low corner stops being the whole story. The far sling is pulled tight on a diagonal into the upper guide bracket while the near sling hangs slack. A hard shove upward would drive sideways strain into the very bracket already carrying too much of it.\r\n"
        "Kalen says, 'Strength does not make the first view false. It makes acting on an incomplete view more consequential.'\r\n"
    )
    if _maybe_finish_views(session):
        await session.send("You have both views now. CHECK STRAIN before touching the load.\r\n")
    return True


async def _check_strain(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "check_strain":
        return False
    flags = _flags(session)
    if not {MOON_ELF_BRUTE_INNER_VIEW_FLAG, MOON_ELF_BRUTE_OUTER_VIEW_FLAG}.issubset(flags):
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_STRAIN_FOUND_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "set_brace")
    await session.send(
        "\r\nYou follow the load path instead of the frame's visible tilt. The far sling is carrying too much weight through a guide bracket that has twisted against its paint marks. If the low corner were simply forced upward, the bracket could shear and let the frame swing across the lane.\r\n"
        "Kalen points to a floor socket and an adjustable timber. 'Now you know what the weight is doing. SET SAFETY BRACE.'\r\n"
    )
    return True


async def _set_brace(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "set_brace":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_BRACE_SET_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "take_weight")
    await session.send(
        "\r\nYou seat the timber brace between the frame base and the marked floor socket, then tighten it until it will stop lateral swing without trying to lift the cargo itself.\r\n"
        "Kalen checks the lock pin. 'Good. Safety is allowed to have more than one layer. Put your feet on the chalk marks. TAKE WEIGHT.'\r\n"
    )
    return True


async def _take_weight(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "take_weight":
        return False
    if MOON_ELF_BRUTE_BRACE_SET_FLAG not in _flags(session):
        await session.send("\r\nKalen stops you. 'Not under an unbraced frame. Set the safety brace first.'\r\n")
        return True
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_WEIGHT_TAKEN_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "hold_steady")
    await session.send(
        "\r\nYou settle into the marked stance and lift only until the far sling loses its dangerous diagonal pull. The frame does not rise dramatically. It becomes lighter in exactly one place.\r\n"
        "The two riggers immediately begin backing the drum one tooth and reseating the guide bracket. Kalen watches the sling, not your muscles. 'That is enough. HOLD STEADY.'\r\n"
    )
    return True


async def _hold_steady(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "hold_steady":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_MECHANISM_RESET_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "verify_frame")
    await session.send(
        "\r\nYou hold the same amount of weight instead of chasing the satisfying feeling of lifting higher. The riggers reseat the drum, square the guide bracket to its paint marks, and take up the slack in the near sling.\r\n"
        "Kalen gives you a small downward gesture. You let the frame's weight return to the mechanism gradually. Nothing jerks. Nothing swings.\r\n"
        "'Now find out whether we actually fixed it. CHECK FRAME.'\r\n"
    )
    return True


async def _check_frame(session) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("current_step") != "verify_frame":
        return False
    session.database.grant_flag(session.character.id, MOON_ELF_BRUTE_FRAME_STABLE_FLAG)
    session.database.advance_quest(session.character.id, MOON_ELF_BRUTE_QUEST_KEY, "return_kalen")
    await session.send(
        "\r\nThe frame now hangs square between its guides. Both slings share the load, the bracket sits true to its marks, and a cautious push at either corner produces no lateral knock or binding. The cargo never had to leave the frame.\r\n"
        "Kalen nods toward the reopened lane. 'Good. The point of strength was to let everyone else do their part safely. TALK KALEN.'\r\n"
    )
    return True


async def _refuse_force_first(session, normalized: str) -> bool:
    quest = _quest(session)
    if quest is None or not _in_walk(session) or quest.get("status") == "completed":
        return False
    if normalized not in {
        "push frame",
        "shove frame",
        "lift frame",
        "raise frame",
        "muscle frame",
        "push supply frame",
        "lift supply frame",
    }:
        return False
    await session.send(
        "\r\nKalen puts one hand up before you commit force to the frame. 'No. Being strong enough to move something does not tell you what moving it will do. Read the load first.'\r\n"
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


def install_moon_elf_brute_runtime(player_session_class, world_service=None) -> None:
    """Add the dedicated Moon Elf Brute extension after the shared Third Chair opening."""
    if getattr(player_session_class, "_moon_elf_brute_runtime_installed", False):
        return

    install_moon_elf_brute_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _reconcile_brute_start(self):
            await self.send(
                "\r\nA high-span rigger catches you with a chalk-marked work chit from Kalen Sorr.\r\n"
                "'Supply frame shifted on the upper transfer lane. Nobody is hurt, nothing is falling, and Kalen says that is why you have time to learn it properly.'\r\n"
                "'High Span Service Walk, south from the Horizon Deck.'\r\n"
                "\r\nNew quest: Before You Lift.\r\n"
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
        if normalized in {"talk kalen", "talk brute kalen", "talk kalen sorr", "talk brute kalen sorr"}:
            handled = await _talk_kalen(self)
        elif normalized in {"examine supply frame", "inspect supply frame", "look supply frame", "examine frame", "inspect frame"}:
            handled = await _inspect_frame(self)
        elif normalized in {"view from inner rail", "view inner rail", "inner rail view", "study inner rail"}:
            handled = await _view_inner(self)
        elif normalized in {"view from outer rail", "view outer rail", "outer rail view", "study outer rail"}:
            handled = await _view_outer(self)
        elif normalized in {"check strain", "trace strain", "inspect strain", "examine strain", "check guide bracket"}:
            handled = await _check_strain(self)
        elif normalized in {"set safety brace", "set brace", "brace frame", "place safety brace", "install brace"}:
            handled = await _set_brace(self)
        elif normalized in {"take weight", "take the weight", "take frame weight", "support frame"}:
            handled = await _take_weight(self)
        elif normalized in {"hold steady", "hold weight", "keep steady", "steady frame"}:
            handled = await _hold_steady(self)
        elif normalized in {"check frame", "inspect stable frame", "verify frame", "test frame", "check rigging"}:
            handled = await _check_frame(self)
        if not handled:
            handled = await _refuse_force_first(self, normalized)

        if handled:
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if _reconcile_brute_start(self):
            await self.send(
                "\r\nAs the Third Chair lesson settles, a high-span rigger finds you with a work chit.\r\n"
                "'Kalen Sorr wants a Brute on the High Span Service Walk, south from the Horizon Deck. The load is stable enough to learn from before anybody moves it.'\r\n"
                "\r\nNew quest: Before You Lift.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_brute_runtime_installed = True
