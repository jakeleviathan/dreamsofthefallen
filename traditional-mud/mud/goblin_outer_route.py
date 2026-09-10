from __future__ import annotations

from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.goblin_salvage_quest import GOBLIN_SALVAGE_CREDIT_FLAG
from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_REGION_KEY,
)
from mud.quests import QuestDefinition
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.scavenging import RUMMAGE_NODES, RummageNode
from mud.world import RoomDefinition


GOBLIN_FIRST_PILING_KEY = "goblin_first_piling"
GOBLIN_OUTER_ROUTE_ACCESS_FLAG = "goblin_first_outer_route_authorized"
GOBLIN_OUTER_ROUTE_COMPLETE_FLAG = "goblin_first_outer_route_completed"
GOBLIN_REEDJAW_DEFEATED_FLAG = "goblin_first_reedjaw_defeated"
GOBLIN_ROUTE_TALLY_ITEM_KEY = "goblin_broker_route_tally"
REEDJAW_SCAVENGER_KEY = "reedjaw_scavenger"


GOBLIN_OUTER_ROUTE_QUEST = QuestDefinition(
    key="goblin_beyond_painted_line",
    name="Beyond the Painted Line",
    style="structured",
    description=(
        "Ruskle Coil sends a newly credited Goblin one supervised route beyond Junk City's painted safe line. "
        "The job is simple on paper: reach the First Piling, clear a small scavenger away from the route cache, "
        "recover the broker tally inside, and bring it home."
    ),
    objective_steps=(
        (
            "cross_checkpoint",
            "Go to Floodgate Walk and travel NORTH beyond the painted safe-route checkpoint to the First Piling.",
        ),
        (
            "defeat_scavenger",
            "A Reedjaw Scavenger is blocking the route cache. ATTACK REEDJAW and drive it off.",
        ),
        (
            "recover_tally",
            "With the cache clear, SEARCH ROUTE CACHE and recover Ruskle's brass broker tally.",
        ),
        (
            "return_broker",
            "Return to Ruskle Coil in Brassgut Market with the Broker's Brass Route Tally and TALK RUSKLE.",
        ),
        (
            "complete",
            "You crossed Junk City's safe line, handled your first outer-route threat, recovered the tally, and returned alive.",
        ),
    ),
)


BROKER_ROUTE_TALLY = ItemDefinition(
    key=GOBLIN_ROUTE_TALLY_ITEM_KEY,
    name="Broker's Brass Route Tally",
    description=(
        "A thumb-length brass tally stamped with Ruskle Coil's broker mark and the number of the First Piling. "
        "A hole through one end lets it hang from a route cache hook or claim cord."
    ),
    category="quest_item",
    tier=0,
)


REEDJAW_SCAVENGER = EnemyDefinition(
    key=REEDJAW_SCAVENGER_KEY,
    name="Reedjaw Scavenger",
    aliases=("reedjaw", "scavenger", "reedjaw scavenger"),
    description=(
        "a dog-sized swamp lizard with reed-colored hide, flat bony jaw plates, and the bad habit of nesting beside anything that smells of oil or food"
    ),
    max_hp=16,
    armor_class=2,
    auto_attack_damage=1,
    auto_attack_interval=3.6,
    xp_reward=20,
    retaliates=True,
    tutorial=False,
)


FIRST_PILING_ROOM = RoomDefinition(
    key=GOBLIN_FIRST_PILING_KEY,
    name="The First Piling",
    region_key=GOBLIN_REGION_KEY,
    description=(
        "The raised route narrows almost immediately beyond Junk City's painted checkpoint and ends at a broad timber piling sunk deep into black swamp mud. "
        "A small work platform has been bolted around it from mismatched planks and old bridge grating. The city remains plainly visible to the south—close enough to hear distant hammering—but the reeds on every other side are taller than a Goblin. "
        "A brass-faced route cache is chained to the piling above the flood line. Fresh claw marks score the boards around it."
    ),
    exits={"south": GOBLIN_FLOODGATE_WALK_KEY},
    enemy_keys=(REEDJAW_SCAVENGER_KEY,),
    tags=("outer_route", "swamp", "tutorial_danger", "first_combat", "one_room_beyond"),
)


ROUTE_CACHE_RUMMAGE = RummageNode(
    key="goblin_first_piling_route_cache",
    room_key=GOBLIN_FIRST_PILING_KEY,
    targets=(
        "route cache",
        "cache",
        "brass cache",
        "broker cache",
        "piling cache",
        "route box",
    ),
)


def _first_piling_augmentation() -> RoomAugmentation:
    return RoomAugmentation(
        exit_overrides=(
            ExitDefinition(
                direction="south",
                destination_key=GOBLIN_FLOODGATE_WALK_KEY,
                name="Floodgate Walk",
                travel_text=(
                    "You retreat along the short raised route toward the painted line and Junk City's flood barrier."
                ),
            ),
        ),
        features=(
            FeatureDefinition(
                key="route_cache",
                name="Route Cache",
                aliases=("cache", "brass cache", "broker cache", "route box"),
                summary="a brass-faced supply and tally box chained above the flood line",
                examine_text=(
                    "The cache is little more than a reinforced box with a rain lip, two old locks, and hooks for route tallies. "
                    "Ruskle's broker scratch is visible beside the First Piling number. Claw marks around the hinges are too fresh to be old damage."
                ),
                search_text=(
                    "The cache can be searched properly once whatever made those fresh claw marks is no longer crowding the platform."
                ),
                touch_text="The brass face is warm where the sun reaches it and greasy around the working latch.",
            ),
            FeatureDefinition(
                key="first_piling",
                name="First Piling",
                aliases=("piling", "timber", "post", "route piling"),
                summary="the first numbered support beyond Junk City's supervised core",
                examine_text=(
                    "Old flood scars stripe the timber at several heights. Each repair band carries a different clan mark, proof that the route is public enough to matter and dangerous enough to need constant rebuilding."
                ),
                touch_text="The tarred timber is damp and rough beneath your hand.",
            ),
            FeatureDefinition(
                key="reed_water",
                name="Reed Water",
                aliases=("water", "reeds", "swamp", "channel"),
                summary="dark shallow water pressing close around the raised platform",
                examine_text=(
                    "The water is shallow near the piling but vanishes quickly beneath dense reeds. Small ripples move against the wind often enough to make the open city behind you feel reassuringly close."
                ),
                listen_text=(
                    "Insects buzz above the water. Something splashes farther into the reeds, followed by the distant clank of a Junk City salvage crew."
                ),
            ),
        ),
        description_layers=(
            DescriptionLayer(
                key="first_piling_day",
                text=(
                    "In daylight the route is exposed and easy to understand: one short span back to the city, one cache, one piling, and miles of bright reed water beyond."
                ),
                priority=40,
                condition=ViewCondition(time_buckets=("day",)),
            ),
            DescriptionLayer(
                key="first_piling_night",
                text=(
                    "At night, a hooded route lamp on the piling keeps the platform visible while everything beyond its small circle of light becomes black water and moving reeds."
                ),
                priority=50,
                condition=ViewCondition(time_buckets=("night",)),
            ),
            DescriptionLayer(
                key="first_piling_rain",
                text=(
                    "Rain ticks against the brass cache and turns the boards slick. The city's lamps to the south blur into yellow streaks through the wet air."
                ),
                priority=60,
                condition=ViewCondition(weather=("rain", "storm")),
            ),
            DescriptionLayer(
                key="first_piling_reedjaw_cleared",
                text=(
                    "You know this platform now: this is where you first learned that the painted line is not decoration."
                ),
                priority=70,
                condition=ViewCondition(required_flags=(GOBLIN_REEDJAW_DEFEATED_FLAG,)),
            ),
        ),
    )


def _floodgate_route_exit() -> ExitDefinition:
    return ExitDefinition(
        direction="north",
        destination_key=GOBLIN_FIRST_PILING_KEY,
        name="First Piling",
        travel_text=(
            "You step across the painted safe-route line and follow the first raised span into the reeds. Junk City remains close behind you, but the sound changes almost immediately."
        ),
        failure_text=(
            "The north checkpoint is not open to you yet. Ruskle Coil in Brassgut Market handles the first supervised outer-route job for newly credited Goblins."
        ),
        condition=ViewCondition(required_flags=(GOBLIN_OUTER_ROUTE_ACCESS_FLAG,)),
        hidden_when_unavailable=True,
    )


def _patch_floodgate(room: RoomDefinition) -> RoomDefinition:
    exits = dict(room.exits)
    exits["north"] = GOBLIN_FIRST_PILING_KEY
    return replace(room, exits=exits)


def _merge_world_augmentations(world_service) -> None:
    augmentations = getattr(world_service, "augmentations", None)
    if augmentations is None:
        return

    floodgate = augmentations.get(GOBLIN_FLOODGATE_WALK_KEY, RoomAugmentation())
    route_exit = _floodgate_route_exit()
    floodgate_overrides = tuple(
        exit_def for exit_def in floodgate.exit_overrides if exit_def.direction != "north"
    ) + (route_exit,)
    route_layer = DescriptionLayer(
        key="goblin_outer_route_authorized",
        text=(
            "Your new route authorization is enough for the checkpoint watch: the first raised span north to the First Piling is open to you."
        ),
        priority=55,
        condition=ViewCondition(required_flags=(GOBLIN_OUTER_ROUTE_ACCESS_FLAG,)),
    )
    layers = floodgate.description_layers
    if not any(layer.key == route_layer.key for layer in layers):
        layers = layers + (route_layer,)
    augmentations[GOBLIN_FLOODGATE_WALK_KEY] = replace(
        floodgate,
        exit_overrides=floodgate_overrides,
        description_layers=layers,
    )
    augmentations[GOBLIN_FIRST_PILING_KEY] = _first_piling_augmentation()

    scene_cache = getattr(world_service, "_scene_cache", None)
    if scene_cache is not None:
        scene_cache.pop(GOBLIN_FLOODGATE_WALK_KEY, None)
        scene_cache.pop(GOBLIN_FIRST_PILING_KEY, None)


def install_goblin_outer_route_content(world_service=None) -> None:
    """Register the first one-room Goblin route beyond Junk City's safe core."""
    floodgate = legacy_world.ROOMS_BY_KEY.get(GOBLIN_FLOODGATE_WALK_KEY)
    replacements: dict[str, RoomDefinition] = {}
    if floodgate is not None:
        replacements[GOBLIN_FLOODGATE_WALK_KEY] = _patch_floodgate(floodgate)

    if GOBLIN_FIRST_PILING_KEY not in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = legacy_world.ROOMS + (FIRST_PILING_ROOM,)
    replacements[GOBLIN_FIRST_PILING_KEY] = FIRST_PILING_ROOM

    if replacements:
        legacy_world.ROOMS = tuple(replacements.get(room.key, room) for room in legacy_world.ROOMS)
        legacy_world.ROOMS_BY_KEY.update(replacements)

    if REEDJAW_SCAVENGER.key not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (REEDJAW_SCAVENGER,)
    combat.ENEMIES_BY_KEY[REEDJAW_SCAVENGER.key] = REEDJAW_SCAVENGER

    if BROKER_ROUTE_TALLY.key not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (BROKER_ROUTE_TALLY,)
    crafting.ITEMS_BY_KEY[BROKER_ROUTE_TALLY.key] = BROKER_ROUTE_TALLY

    if GOBLIN_OUTER_ROUTE_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (GOBLIN_OUTER_ROUTE_QUEST,)
    quests.QUESTS_BY_KEY[GOBLIN_OUTER_ROUTE_QUEST.key] = GOBLIN_OUTER_ROUTE_QUEST

    RUMMAGE_NODES.register(ROUTE_CACHE_RUMMAGE)

    if world_service is not None:
        world_service.legacy_rooms.update(replacements)
        _merge_world_augmentations(world_service)


def _quest_state(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, GOBLIN_OUTER_ROUTE_QUEST.key)


def _target_after_talk(command: str) -> str:
    text = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
    return text.lower().removeprefix("to ").strip()


def _is_ruskle(target: str) -> bool:
    return target in {
        "ruskle",
        "ruskle coil",
        "goblin ruskle coil",
        "broker",
        "salvage broker",
    }


def _consume_all_tallies(session) -> None:
    if session.character is None:
        return
    quantity = session.database.item_quantity(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY)
    if quantity > 0:
        session.database.consume_item(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY, quantity)


def _reconcile_outer_route(session) -> str | None:
    """Make the one-room route crash-safe across logout/server restarts."""
    if session.character is None:
        return None
    character_id = session.character.id
    quest = _quest_state(session)
    flags = session.database.list_flags(character_id)
    quantity = session.database.item_quantity(character_id, GOBLIN_ROUTE_TALLY_ITEM_KEY)

    if quest is not None and quest.get("status") == "completed":
        session.database.grant_flag(character_id, GOBLIN_OUTER_ROUTE_ACCESS_FLAG)
        session.database.grant_flag(character_id, GOBLIN_OUTER_ROUTE_COMPLETE_FLAG)
        _consume_all_tallies(session)
        return "complete"

    if GOBLIN_OUTER_ROUTE_COMPLETE_FLAG in flags:
        if quest is None:
            session.database.start_quest(character_id, GOBLIN_OUTER_ROUTE_QUEST.key, "complete")
        session.database.complete_quest(character_id, GOBLIN_OUTER_ROUTE_QUEST.key)
        session.database.grant_flag(character_id, GOBLIN_OUTER_ROUTE_ACCESS_FLAG)
        _consume_all_tallies(session)
        return "complete"

    if quest is None:
        if quantity > 0:
            _consume_all_tallies(session)
        return None

    if quest.get("status") != "active":
        return str(quest.get("current_step") or "")

    session.database.grant_flag(character_id, GOBLIN_OUTER_ROUTE_ACCESS_FLAG)
    step = str(quest.get("current_step") or "cross_checkpoint")

    if step == "recover_tally" and quantity > 0:
        if quantity > 1:
            session.database.consume_item(character_id, GOBLIN_ROUTE_TALLY_ITEM_KEY, quantity - 1)
        session.database.advance_quest(character_id, GOBLIN_OUTER_ROUTE_QUEST.key, "return_broker")
        return "return_broker"

    if step == "return_broker":
        if quantity == 0:
            session.database.add_item(character_id, GOBLIN_ROUTE_TALLY_ITEM_KEY, 1)
        elif quantity > 1:
            session.database.consume_item(character_id, GOBLIN_ROUTE_TALLY_ITEM_KEY, quantity - 1)
        return step

    if step in {"cross_checkpoint", "defeat_scavenger"} and quantity > 0:
        _consume_all_tallies(session)

    return step


async def _talk_ruskle(session) -> bool:
    assert session.character is not None
    flags = session.database.list_flags(session.character.id)
    if GOBLIN_SALVAGE_CREDIT_FLAG not in flags:
        return False

    _reconcile_outer_route(session)
    quest = _quest_state(session)

    if quest is None:
        session.database.start_quest(
            session.character.id,
            GOBLIN_OUTER_ROUTE_QUEST.key,
            "cross_checkpoint",
        )
        session.database.grant_flag(session.character.id, GOBLIN_OUTER_ROUTE_ACCESS_FLAG)
        await session.send(
            "\r\nRuskle glances at the broker strip bearing your first salvage credit, then finally stops looking at you like a complete beginner.\r\n"
            "'Good. You can move an object through the city. Now learn why the paint at Floodgate Walk matters.'\r\n"
            "He taps a small route map with one gloved finger. 'First Piling. One span north of the checkpoint. I left a brass broker tally in the route cache before the water came up. Bring it back.'\r\n"
            "Ruskle's grin thins. 'There was a Reedjaw nosing around the platform this morning. Small one. Mean enough to teach the lesson. If it is still there, don't reach past its teeth. Deal with it first.'\r\n"
            "'The watch knows your name. If you get flattened, they'll drag you back across the line. Embarrassing is cheaper than dead.'\r\n"
            "\r\nNew quest: Beyond the Painted Line.\r\n"
            "Go to Floodgate Walk, then travel NORTH to the First Piling.\r\n"
        )
        return True

    if quest.get("status") == "completed":
        await session.send(
            "\r\nRuskle taps the returned route tally hanging beneath his counter. 'You've been one room past the paint and came back knowing why it exists. That's enough for a first trip.'\r\n"
        )
        return True

    step = str(quest.get("current_step") or "cross_checkpoint")
    if step == "return_broker":
        quantity = session.database.item_quantity(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY)
        if quantity <= 0:
            _reconcile_outer_route(session)
            quantity = session.database.item_quantity(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY)
        if quantity <= 0:
            await session.send(
                "\r\nRuskle holds out a hand. 'You were supposed to bring back the tally, not a dramatic story about where you left it.'\r\n"
            )
            return True

        # Completion flag is the permanent receipt. No repeatable item/currency
        # reward is attached to this starter lesson.
        session.database.grant_flag(session.character.id, GOBLIN_OUTER_ROUTE_COMPLETE_FLAG)
        session.database.complete_quest(session.character.id, GOBLIN_OUTER_ROUTE_QUEST.key)
        _consume_all_tallies(session)
        await session.send(
            "\r\nRuskle takes the brass tally, wipes a smear of swamp mud from its stamped number, and hangs it beneath his counter.\r\n"
            "'There. One span out, one problem handled, one thing brought home. The city is loud enough that people forget how quickly it stops being safe.'\r\n"
            "He points north with the tally before letting it swing on its hook. 'Next time you cross the paint, nobody gets to pretend you weren't warned.'\r\n"
            "\r\nQuest complete: Beyond the Painted Line.\r\n"
        )
        return True

    objective = GOBLIN_OUTER_ROUTE_QUEST.objective_for_step(step)
    await session.send("\r\nRuskle taps the First Piling on his little route map.\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _handle_route_cache(session, normalized: str) -> bool:
    if session.character is None:
        return False
    node = RUMMAGE_NODES.resolve(normalized, session.character.current_room or "")
    if node is None or node.key != ROUTE_CACHE_RUMMAGE.key:
        return False

    _reconcile_outer_route(session)
    quest = _quest_state(session)
    if not quest or quest.get("status") != "active":
        await session.send(
            "\r\nThe route cache is secured for working crews. You have no current broker job that gives you a reason to open it.\r\n"
        )
        return True

    step = str(quest.get("current_step") or "")
    if step == "defeat_scavenger":
        await session.send(
            "\r\nThe fresh claw marks make more sense when the Reedjaw lifts its plated head beside the cache. Reaching past it would be a terrible first outer-route habit. ATTACK REEDJAW first.\r\n"
        )
        return True
    if step == "cross_checkpoint":
        await session.send("\r\nYou need to cross the checkpoint and reach the First Piling before you can search its route cache.\r\n")
        return True
    if step == "recover_tally":
        if session.database.item_quantity(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY) == 0:
            session.database.add_item(session.character.id, GOBLIN_ROUTE_TALLY_ITEM_KEY, 1)
        session.database.advance_quest(session.character.id, GOBLIN_OUTER_ROUTE_QUEST.key, "return_broker")
        await session.send(
            "\r\nYou work the cache latch free and sort past a coil of dry cord, two waxed route notes, and a stoppered jar of something medicinal-smelling. Ruskle's brass tally hangs from the back hook exactly where he said it would.\r\n"
            "You take the Broker's Brass Route Tally.\r\n"
            "Return south to Junk City and TALK RUSKLE in Brassgut Market.\r\n"
            "Quest updated: Beyond the Painted Line.\r\n"
        )
        return True
    if step == "return_broker":
        await session.send("\r\nThe cache has already given you what Ruskle sent you to recover. The brass tally is with you.\r\n")
        return True
    return False


async def _rescue_from_reedjaw(session) -> None:
    """Nonlethal safety net for the player's first unsupervised-looking fight."""
    assert session.character is not None and session.combatant is not None
    await session.send(
        "\r\n*** The Reedjaw knocks you down hard enough to end the lesson. ***\r\n"
        "A hook pole snaps around the back of your harness before the creature can press the attack. Two Goblins from the flood-route watch haul you across the painted line while loudly debating which part of that was funniest.\r\n"
        "You recover at Floodgate Walk. No experience is lost on this first supervised outer-route attempt.\r\n"
    )
    session.database.set_character_room(session.character.id, GOBLIN_FLOODGATE_WALK_KEY)
    session.combatant.current_hp = session.combatant.max_hp
    session.combatant.current_mana = session.combatant.max_mana
    await session._stop_combat()

    getter = getattr(session.database, "get_character_by_name", None)
    if getter is not None:
        refreshed = getter(session.character.name)
        if refreshed is not None:
            session.character = refreshed

    await session.show_current_room()
    await session.send_client_state()


def install_goblin_outer_route_runtime(player_session_class, world_service) -> None:
    install_goblin_outer_route_content(world_service)
    if getattr(player_session_class, "_goblin_outer_route_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = player_session_class.move_character
    previous_finish_enemy_defeat = player_session_class._finish_enemy_defeat
    previous_handle_character_death = player_session_class._handle_character_death

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "goblin":
            return
        step = _reconcile_outer_route(self)
        quest = _quest_state(self)
        if quest and quest.get("status") == "active" and step:
            objective = GOBLIN_OUTER_ROUTE_QUEST.objective_for_step(step)
            await self.send("\r\nYour first outer-route job is still active.\r\n")
            if objective:
                await self.send(f"Current objective: {objective}\r\n")

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        if self.character is None or self.character.race != "goblin":
            return
        after = self.character.current_room
        if before != after and after == GOBLIN_FIRST_PILING_KEY:
            quest = _quest_state(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "cross_checkpoint":
                self.database.advance_quest(self.character.id, GOBLIN_OUTER_ROUTE_QUEST.key, "defeat_scavenger")
                await self.send(
                    "\r\nThe moment you step onto the First Piling, a Reedjaw Scavenger lifts its flat plated head beside the route cache and gives a wet, rasping hiss.\r\n"
                    "This is the lesson Ruskle meant. The city is only one span behind you, but nothing here is obligated to be polite.\r\n"
                    "ATTACK REEDJAW when you are ready.\r\n"
                    "Quest updated: Beyond the Painted Line.\r\n"
                )

    async def _finish_enemy_defeat(self, enemy: EnemyState) -> None:
        defeated_key = enemy.definition.key
        await previous_finish_enemy_defeat(self, enemy)
        if (
            self.character is not None
            and self.character.race == "goblin"
            and defeated_key == REEDJAW_SCAVENGER_KEY
        ):
            quest = _quest_state(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "defeat_scavenger":
                self.database.grant_flag(self.character.id, GOBLIN_REEDJAW_DEFEATED_FLAG)
                self.database.advance_quest(self.character.id, GOBLIN_OUTER_ROUTE_QUEST.key, "recover_tally")
                await self.send(
                    "The Reedjaw scrambles off the platform and disappears into the reeds. The route cache is clear.\r\n"
                    "SEARCH ROUTE CACHE to recover Ruskle's tally.\r\n"
                    "Quest updated: Beyond the Painted Line.\r\n"
                )

    async def _handle_character_death(self, enemy_name: str) -> None:
        if (
            self.character is not None
            and self.character.race == "goblin"
            and self.character.current_room == GOBLIN_FIRST_PILING_KEY
            and self.active_enemy is not None
            and self.active_enemy.definition.key == REEDJAW_SCAVENGER_KEY
        ):
            await _rescue_from_reedjaw(self)
            return
        await previous_handle_character_death(self, enemy_name)

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
            if target and _is_ruskle(target) and self.character.current_room == GOBLIN_BRASSGUT_MARKET_KEY:
                if await _talk_ruskle(self):
                    return

        if await _handle_route_cache(self, normalized):
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

        if normalized in {"help", "?"} and GOBLIN_SALVAGE_CREDIT_FLAG in self.database.list_flags(self.character.id):
            quest = _quest_state(self)
            if quest is None:
                await self.send(
                    "Goblin route tip: after A Piece Worth Keeping, TALK RUSKLE again for your first supervised trip beyond Floodgate Walk.\r\n"
                )

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._handle_character_death = _handle_character_death
    player_session_class._goblin_outer_route_runtime_installed = True
