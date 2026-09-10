from __future__ import annotations

from mud.appearance import appearance_menu_text, reflection_text, validate_choice
from mud.appearance_storage import get_appearance, set_appearance
from mud.astralis_human_district import HUMAN_DISTRICT
from mud.astralis_time import ASTRALIS_CLOCK, puddle_available
from mud.combat import ENEMIES_BY_KEY
from mud.crafting import ITEMS_BY_KEY
from mud.human_district import HUMAN_REGION_KEY
from mud.room_content import complete_room_augmentations
from mud.room_engine import PlayerRoomContext, WorldService
from mud.world import (
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_WAYSTONE_BEND_KEY,
    HUMAN_BLACKGLASS_ARCH_KEY,
    NPCS_BY_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
)


# Every authored room now runs through the rich scene catalog rather than only
# the original showcase rooms.
WORLD = WorldService(augmentations=complete_room_augmentations())


def _moment():
    return ASTRALIS_CLOCK.now()


def _context_for(session) -> PlayerRoomContext:
    character = session.character
    if character is None:
        raise RuntimeError("A room view requires an active character")
    moment = _moment()
    return PlayerRoomContext(
        character_id=character.id,
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=character.level,
        character_flags=frozenset(session.database.list_flags(character.id)),
        hour=moment.hour,
    )


def _quest_sensitive_legacy_interaction(room_key: str, command: str) -> bool:
    """Keep existing quest side effects for commands upgraded into features."""
    normalized = command.strip().lower()
    if room_key == FOREST_ELF_WAYSTONE_BEND_KEY:
        return normalized in {
            "examine waystone", "look waystone", "examine stone marker", "look stone marker"
        }
    if room_key == FOREST_ELF_LISTENING_POOL_KEY:
        return normalized in {
            "listen", "listen pool", "listen to pool", "listen water"
        }
    if room_key == HUMAN_BLACKGLASS_ARCH_KEY:
        return normalized in {
            "examine mark", "look mark", "examine symbol", "look symbol",
            "examine occult mark", "look occult mark",
        }
    if room_key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY:
        if normalized in {
            "examine mushrooms", "examine mushroom ring", "examine ring", "look mushrooms",
            "look mushroom ring", "look ring", "examine stone", "look stone",
            "listen", "listen grove", "listen to grove",
        }:
            return True
        if normalized.startswith("touch "):
            return True
    return False


def _current_business(session, target: str = ""):
    if session.character is None:
        return None
    return HUMAN_DISTRICT.find_business(session.character.current_room or "", target)


def _current_scene(session):
    if session.character is None:
        return None
    return WORLD.scene(session.character.current_room or "")


def _puddle_here(session) -> bool:
    if session.character is None:
        return False
    scene = _current_scene(session)
    if scene is None:
        return False
    return puddle_available(session.character.current_room or "", scene.region_key, WORLD.state)


async def _render_business_status(session) -> None:
    if session.character is None:
        return
    moment = _moment()
    lines = HUMAN_DISTRICT.storefront_lines(
        session.character.current_room or "",
        WORLD.state,
        moment.hour,
        moment.day_number,
    )
    for line in lines:
        await session.send(f"\r\n{line}\r\n")


async def _render_current_room(session, original_show_current_room) -> None:
    character = session.character
    if character is None:
        return
    context = _context_for(session)
    view = WORLD.build_view(character.current_room or "", context)
    if view is None:
        await original_show_current_room(session)
        return

    scene = WORLD.scene(view.key)
    await session.send(f"{view.name}\r\n")
    await session.send(view.description.replace("\n", "\r\n") + "\r\n")

    if _puddle_here(session):
        await session.send(
            "\r\nRainwater has collected in a shallow puddle. Its dark surface catches a wavering reflection whenever the rain eases between drops.\r\n"
        )

    if view.features:
        await session.send("\r\nNotable: " + ", ".join(feature.name for feature in view.features) + ".\r\n")
    if _puddle_here(session):
        await session.send("Notable: Puddle.\r\n")

    business = HUMAN_DISTRICT.business_in_room(view.key)
    if business is not None:
        await session.send(f"Notable business: {business.name}.\r\n")
        await _render_business_status(session)

    if scene is not None:
        for npc_key in scene.npc_keys:
            npc = NPCS_BY_KEY.get(npc_key)
            if npc:
                await session.send(f"\r\n{npc.name} is here, {npc.short_description}.\r\n")
        for enemy_key in scene.enemy_keys:
            enemy = ENEMIES_BY_KEY.get(enemy_key)
            if enemy:
                await session.send(f"\r\n{enemy.name} is here, {enemy.description}.\r\n")

    if session.mobile_npcs is not None:
        for state in session.mobile_npcs.npcs_in_room(view.key):
            await session.send(f"\r\n{state.definition.name} is here, {state.definition.short_description}.\r\n")

    if view.exits:
        await session.send("Exits: " + ", ".join(exit_view.direction for exit_view in view.exits) + "\r\n")
        named = [f"{exit_view.direction} -> {exit_view.name}" for exit_view in view.exits if exit_view.name]
        if named:
            await session.send("Routes: " + " | ".join(named) + "\r\n")


async def _show_exits(session) -> None:
    character = session.character
    if character is None:
        return
    view = WORLD.build_view(character.current_room or "", _context_for(session))
    if view is None or not view.exits:
        await session.send("No authored exits are available here yet.\r\n")
        return
    await session.send("Exits:\r\n")
    for exit_view in view.exits:
        label = f" - {exit_view.direction}"
        if exit_view.name:
            label += f" : {exit_view.name}"
        await session.send(label + "\r\n")


async def _show_features(session) -> None:
    character = session.character
    if character is None:
        return
    view = WORLD.build_view(character.current_room or "", _context_for(session))
    business = HUMAN_DISTRICT.business_in_room(character.current_room or "")
    has_puddle = _puddle_here(session)
    if (view is None or not view.features) and business is None and not has_puddle:
        await session.send("Nothing here is singled out as an interactive landmark.\r\n")
        return
    await session.send("Notable features:\r\n")
    if view is not None:
        for feature in view.features:
            detail = f" - {feature.name}"
            if feature.summary:
                detail += f": {feature.summary}"
            await session.send(detail + "\r\n")
    if has_puddle:
        await session.send(" - Puddle: fresh rainwater deep enough to hold your reflection. Try USE PUDDLE.\r\n")
    if business is not None:
        await session.send(f" - {business.name}: {business.storefront_description} Proprietor: {business.proprietor}.\r\n")
    await session.send(
        "Try EXAMINE, SEARCH, TOUCH, LISTEN, SMELL, or LOOK <feature>. Human businesses also support SHOP, HOURS, TALK, OPEN, and CLOSE.\r\n"
    )


async def _show_business_shop(session, business) -> None:
    moment = _moment()
    lines = HUMAN_DISTRICT.shop_lines(business, WORLD.state, moment.hour, moment.day_number)
    for index, line in enumerate(lines):
        if index >= 3 and line in ITEMS_BY_KEY:
            await session.send(ITEMS_BY_KEY[line].name + "\r\n")
        else:
            await session.send(line + "\r\n")
    if HUMAN_DISTRICT.is_open(business, WORLD.state, moment.hour, moment.day_number):
        await session.send("Prices are deliberately not attached yet; Astralis's permanent currency/economy has not been finalized.\r\n")


async def _show_weather(session) -> None:
    if session.character is None:
        return
    scene = WORLD.scene(session.character.current_room or "")
    if scene is None:
        await session.send("You cannot get a clear read on the weather here.\r\n")
        return
    weather = WORLD.state.weather_for(scene.region_key)
    moment = _moment()
    await session.send(f"Astralis time: {moment.display}. Regional weather: {weather}.\r\n")


async def _show_time(session) -> None:
    moment = _moment()
    await session.send(
        f"Astralis time: {moment.display}. One full Astralis day passes every four real hours; each Astralis hour lasts ten real minutes.\r\n"
    )


async def _show_reflection(session, *, enter_editor: bool = False) -> None:
    if session.character is None:
        return
    if not _puddle_here(session):
        await session.send("There is no rain puddle here deep and still enough to hold a useful reflection.\r\n")
        return
    race_key = session.character.race or "human"
    stored = get_appearance(session.database, session.character.id)
    await session.send("\r\n" + reflection_text(session.character.name, race_key, stored) + "\r\n")
    if enter_editor:
        session._reflection_editor_room = session.character.current_room
        await session.send(appearance_menu_text(race_key, stored) + "\r\n")


async def _set_reflection_appearance(session, target: str) -> None:
    if session.character is None:
        return
    if getattr(session, "_reflection_editor_room", None) != session.character.current_room or not _puddle_here(session):
        session._reflection_editor_room = None
        await session.send("The reflection is no longer available. Find a fresh rain puddle and USE PUDDLE first.\r\n")
        return
    pieces = target.split(maxsplit=1)
    if len(pieces) != 2:
        stored = get_appearance(session.database, session.character.id)
        await session.send(appearance_menu_text(session.character.race or "human", stored) + "\r\n")
        return
    trait_key, choice = pieces
    valid, normalized = validate_choice(session.character.race or "human", trait_key, choice)
    if not valid:
        await session.send(normalized + "\r\n")
        return
    normalized_key = trait_key.strip().lower().replace(" ", "_")
    set_appearance(session.database, session.character.id, normalized_key, normalized)
    stored = get_appearance(session.database, session.character.id)
    await session.send(f"Your reflected {normalized_key.replace('_', ' ')} shifts to {normalized}.\r\n")
    await session.send(reflection_text(session.character.name, session.character.race or "human", stored) + "\r\n")


def install_room_runtime(player_session_class) -> None:
    """Install the advanced room/time/weather runtime without discarding established systems."""

    if getattr(player_session_class, "_advanced_room_runtime_installed", False):
        return

    original_show_current_room = player_session_class.show_current_room
    original_move_character = player_session_class.move_character
    original_playing_prompt = player_session_class.playing_prompt

    async def show_current_room(self) -> None:
        await _render_current_room(self, original_show_current_room)

    async def move_character(self, direction: str) -> None:
        if self.character is None:
            return
        if self.active_enemy is not None:
            await original_move_character(self, direction)
            return
        self._reflection_editor_room = None
        resolution = WORLD.resolve_exit(self.character.current_room or "", direction, _context_for(self))
        if not resolution.allowed:
            await self.send((resolution.message or "You cannot go that way.") + "\r\n")
            return
        if resolution.exit and resolution.exit.travel_text:
            await self.send("\r\n" + resolution.exit.travel_text + "\r\n")
        await original_move_character(self, direction)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await original_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = command.strip().lower()
        room_key = self.character.current_room or ""

        if normalized in {"exits", "exit"}:
            await _show_exits(self)
            return
        if normalized in {"features", "feature", "details", "landmarks", "landmark"}:
            await _show_features(self)
            return
        if normalized in {"weather", "conditions"}:
            await _show_weather(self)
            return
        if normalized in {"time", "clock", "astralis time"}:
            await _show_time(self)
            return
        if normalized in {"look puddle", "examine puddle", "look reflection", "examine reflection"}:
            await _show_reflection(self)
            return
        if normalized in {"use puddle", "use reflection"}:
            await _show_reflection(self, enter_editor=True)
            return
        if normalized == "appearance":
            await _set_reflection_appearance(self, "")
            return
        if normalized.startswith("appearance "):
            await _set_reflection_appearance(self, command.strip().split(maxsplit=1)[1])
            return
        if normalized in {"done", "finish reflection", "leave reflection"} and getattr(self, "_reflection_editor_room", None):
            self._reflection_editor_room = None
            await self.send("You let the puddle settle back into ordinary rainwater.\r\n")
            return

        moment = _moment()

        # Human starting-district storefronts are real scheduled world objects.
        if normalized in {"shop", "list", "wares", "hours", "shop hours"}:
            business = _current_business(self)
            if business is not None:
                if normalized in {"hours", "shop hours"}:
                    hours = HUMAN_DISTRICT.effective_hours_text(
                        business, moment.day_number, WORLD.state.weather_for(HUMAN_REGION_KEY)
                    )
                    await self.send(f"{business.name} - proprietor {business.proprietor} - today's hours {hours}.\r\n")
                else:
                    await _show_business_shop(self, business)
                return

        pieces = normalized.split(maxsplit=1)
        action = pieces[0] if pieces else ""
        target = pieces[1] if len(pieces) == 2 else ""

        if action in {"shop", "hours"} and target:
            business = _current_business(self, target)
            if business is not None:
                if action == "hours":
                    hours = HUMAN_DISTRICT.effective_hours_text(
                        business, moment.day_number, WORLD.state.weather_for(HUMAN_REGION_KEY)
                    )
                    await self.send(f"{business.name} - proprietor {business.proprietor} - today's hours {hours}.\r\n")
                else:
                    await _show_business_shop(self, business)
                return

        if action in {"talk", "speak"}:
            business = _current_business(self, target) if target else _current_business(self)
            if business is not None:
                await self.send(HUMAN_DISTRICT.talk(business, WORLD.state, moment.hour, moment.day_number) + "\r\n")
                return

        if action in {"open", "close"} and target:
            business = _current_business(self, target)
            if business is not None:
                if action == "open":
                    text = HUMAN_DISTRICT.open_door(business, WORLD.state, moment.hour, moment.day_number)
                else:
                    text = HUMAN_DISTRICT.close_door(business, WORLD.state, moment.hour, moment.day_number)
                await self.send(text + "\r\n")
                return

        if action in {"smell", "sniff"}:
            business = _current_business(self, target) if target else _current_business(self)
            if business is not None:
                await self.send(HUMAN_DISTRICT.smell(business, WORLD.state, moment.hour, moment.day_number) + "\r\n")
                return
            await self.send("You take in the air, but nothing here has been authored with a distinct scent yet.\r\n")
            return

        if len(pieces) == 2 and action in {"look", "examine", "search", "listen"}:
            business = _current_business(self, target)
            if business is not None:
                if action == "listen":
                    text = HUMAN_DISTRICT.listen(business, WORLD.state, moment.hour, moment.day_number)
                else:
                    text = HUMAN_DISTRICT.examine(business, WORLD.state, moment.hour, moment.day_number)
                await self.send("\r\n" + text + "\r\n")
                return

        if (
            len(pieces) == 2
            and action in {"look", "examine", "search", "touch", "listen"}
            and not _quest_sensitive_legacy_interaction(room_key, normalized)
        ):
            result = WORLD.interact(room_key, action, target, _context_for(self))
            if result.handled:
                await self.send("\r\n" + result.text + "\r\n")
                return

        had_instance_prompt = "prompt" in self.__dict__
        previous_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await original_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = previous_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"}:
            await self.send(
                "World commands: TIME shows accelerated Astralis time; WEATHER reports regional conditions. Rain can create PUDDLES in outdoor rooms; USE PUDDLE opens the reflection appearance editor. "
                "Room exploration: FEATURES/LANDMARKS lists interactive details; SEARCH/LOOK/EXAMINE/TOUCH/LISTEN/SMELL inspect the scene. Human district businesses also support SHOP, HOURS, TALK <proprietor>, OPEN <shop>, and CLOSE <shop>.\r\n"
            )

    player_session_class.show_current_room = show_current_room
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._advanced_room_runtime_installed = True
