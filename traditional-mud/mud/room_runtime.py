from __future__ import annotations

from datetime import datetime

from mud.combat import ENEMIES_BY_KEY
from mud.room_engine import PlayerRoomContext, WorldService
from mud.world import NPCS_BY_KEY


WORLD = WorldService()


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
    if view is None or not view.features:
        await session.send("Nothing here is singled out as an interactive landmark.\r\n")
        return
    await session.send("Notable features:\r\n")
    for feature in view.features:
        detail = f" - {feature.name}"
        if feature.summary:
            detail += f": {feature.summary}"
        await session.send(detail + "\r\n")
    await session.send("Try EXAMINE, SEARCH, TOUCH, LISTEN, or LOOK <feature>.\r\n")


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
        if normalized in {"exits", "exit"}:
            await _show_exits(self)
            return
        if normalized in {"features", "feature", "details", "landmarks", "landmark"}:
            await _show_features(self)
            return

        pieces = normalized.split(maxsplit=1)
        if len(pieces) == 2 and pieces[0] in {"look", "examine", "search", "touch", "listen"}:
            action, target = pieces
            result = WORLD.interact(
                self.character.current_room or "",
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
                "Room exploration: FEATURES/LANDMARKS lists interactive details; SEARCH <feature> and LOOK/EXAMINE/TOUCH/LISTEN <feature> use the scene system.\r\n"
            )

    player_session_class.show_current_room = show_current_room
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._advanced_room_runtime_installed = True
