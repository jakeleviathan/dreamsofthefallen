from __future__ import annotations

from datetime import datetime

from mud.combat import ENEMIES_BY_KEY
from mud.crafting import ITEMS_BY_KEY
from mud.human_district import HUMAN_DISTRICT, HUMAN_REGION_KEY
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


def _context_for(session) -> PlayerRoomContext:
    character = session.character
    if character is None:
        raise RuntimeError("A room view requires an active character")
    return PlayerRoomContext(
        character_id=character.id,
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=character.level,
        character_flags=frozenset(session.database.list_flags(character.id)),
        hour=datetime.now().hour,
    )


def _quest_sensitive_legacy_interaction(room_key: str, command: str) -> bool:
    """Keep existing quest side effects for commands upgraded into features.

    The new room catalog can describe these landmarks, but their original
    handlers currently own quest advancement. Until quest actions themselves
    become data-driven, these exact interactions deliberately delegate.
    """
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


async def _render_business_status(session) -> None:
    if session.character is None:
        return
    lines = HUMAN_DISTRICT.storefront_lines(
        session.character.current_room or "",
        WORLD.state,
        datetime.now().hour,
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

    if view.features:
        await session.send(
            "\r\nNotable: " + ", ".join(feature.name for feature in view.features) + ".\r\n"
        )

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
            await session.send(
                f"\r\n{state.definition.name} is here, {state.definition.short_description}.\r\n"
            )

    if view.exits:
        await session.send("Exits: " + ", ".join(exit_view.direction for exit_view in view.exits) + "\r\n")
        named = [
            f"{exit_view.direction} -> {exit_view.name}"
            for exit_view in view.exits
            if exit_view.name
        ]
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
    if (view is None or not view.features) and business is None:
        await session.send("Nothing here is singled out as an interactive landmark.\r\n")
        return
    await session.send("Notable features:\r\n")
    if view is not None:
        for feature in view.features:
            detail = f" - {feature.name}"
            if feature.summary:
                detail += f": {feature.summary}"
            await session.send(detail + "\r\n")
    if business is not None:
        await session.send(
            f" - {business.name}: {business.storefront_description} Proprietor: {business.proprietor}.\r\n"
        )
    await session.send(
        "Try EXAMINE, SEARCH, TOUCH, LISTEN, SMELL, or LOOK <feature>. Human businesses also support SHOP, HOURS, TALK, OPEN, and CLOSE.\r\n"
    )


async def _show_business_shop(session, business) -> None:
    lines = HUMAN_DISTRICT.shop_lines(business, WORLD.state, datetime.now().hour)
    for index, line in enumerate(lines):
        if index >= 3 and line in ITEMS_BY_KEY:
            await session.send(ITEMS_BY_KEY[line].name + "\r\n")
        else:
            await session.send(line + "\r\n")
    if HUMAN_DISTRICT.is_open(business, WORLD.state, datetime.now().hour):
        await session.send(
            "Prices are deliberately not attached yet; Astralis's permanent currency/economy has not been finalized.\r\n"
        )


async def _show_weather(session) -> None:
    if session.character is None:
        return
    scene = WORLD.scene(session.character.current_room or "")
    if scene is None:
        await session.send("You cannot get a clear read on the weather here.\r\n")
        return
    weather = WORLD.state.weather_for(scene.region_key)
    await session.send(f"Current regional weather: {weather}.\r\n")


def install_room_runtime(player_session_class) -> None:
    """Install the new room engine without discarding existing quest logic.

    The existing PlayerSession still owns combat, quests, character creation,
    and legacy special interactions. This compatibility layer replaces the
    room-facing surfaces while delegating unhandled commands and quest movement
    back to the existing session implementation.
    """

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
        # Preserve the existing combat/FLEE rule exactly.
        if self.active_enemy is not None:
            await original_move_character(self, direction)
            return

        resolution = WORLD.resolve_exit(
            self.character.current_room or "",
            direction,
            _context_for(self),
        )
        if not resolution.allowed:
            await self.send((resolution.message or "You cannot go that way.") + "\r\n")
            return
        if resolution.exit and resolution.exit.travel_text:
            await self.send("\r\n" + resolution.exit.travel_text + "\r\n")

        # The legacy movement method remains the owner of persistence, quests,
        # aggression checks, and all established side effects. Its destination
        # matches the first-class exit definition for existing rooms.
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

        # Human starting-district storefronts are real scheduled world objects.
        if normalized in {"shop", "list", "wares", "hours", "shop hours"}:
            business = _current_business(self)
            if business is not None:
                if normalized in {"hours", "shop hours"}:
                    await self.send(
                        f"{business.name} - proprietor {business.proprietor} - posted hours {business.hours_text}.\r\n"
                    )
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
                    await self.send(
                        f"{business.name} - proprietor {business.proprietor} - posted hours {business.hours_text}.\r\n"
                    )
                else:
                    await _show_business_shop(self, business)
                return

        if action in {"talk", "speak"}:
            business = _current_business(self, target) if target else _current_business(self)
            if business is not None:
                await self.send(HUMAN_DISTRICT.talk(business, WORLD.state, datetime.now().hour) + "\r\n")
                return

        if action in {"open", "close"} and target:
            business = _current_business(self, target)
            if business is not None:
                if action == "open":
                    text = HUMAN_DISTRICT.open_door(business, WORLD.state, datetime.now().hour)
                else:
                    text = HUMAN_DISTRICT.close_door(business, WORLD.state, datetime.now().hour)
                await self.send(text + "\r\n")
                return

        if action in {"smell", "sniff"}:
            business = _current_business(self, target) if target else _current_business(self)
            if business is not None:
                await self.send(HUMAN_DISTRICT.smell(business, WORLD.state, datetime.now().hour) + "\r\n")
                return
            await self.send("You take in the air, but nothing here has been authored with a distinct scent yet.\r\n")
            return

        if len(pieces) == 2 and action in {"look", "examine", "search", "listen"}:
            business = _current_business(self, target)
            if business is not None:
                if action == "listen":
                    text = HUMAN_DISTRICT.listen(business, WORLD.state, datetime.now().hour)
                else:
                    text = HUMAN_DISTRICT.examine(business, WORLD.state, datetime.now().hour)
                await self.send("\r\n" + text + "\r\n")
                return

        if (
            len(pieces) == 2
            and action in {"look", "examine", "search", "touch", "listen"}
            and not _quest_sensitive_legacy_interaction(room_key, normalized)
        ):
            result = WORLD.interact(
                room_key,
                action,
                target,
                _context_for(self),
            )
            if result.handled:
                await self.send("\r\n" + result.text + "\r\n")
                return

        # Replay the already-read command into the established command handler.
        # This lets every existing quest/combat/crafting command continue to
        # work unchanged while avoiding a second prompt/read.
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
                "Room exploration: FEATURES/LANDMARKS lists interactive details; SEARCH/LOOK/EXAMINE/TOUCH/LISTEN/SMELL can inspect the scene. "
                "Human district businesses also support SHOP, HOURS, TALK <proprietor>, OPEN <shop>, and CLOSE <shop>. WEATHER reports the current regional state.\r\n"
            )

    player_session_class.show_current_room = show_current_room
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._advanced_room_runtime_installed = True
