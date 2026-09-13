from __future__ import annotations

from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_REGION_KEY,
    GOBLIN_ROOMS,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_PATCHWORK_PLAZA_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
    GOBLIN_START_ROOM_KEY,
)
import mud.world as legacy_world


_OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
}

# The authored spine a new Goblin follows from arrival, through Three Bells, and
# eventually to the supervised edge of the wider swamp.
GOBLIN_STARTER_ROUTE = (
    GOBLIN_START_ROOM_KEY,
    GOBLIN_SORTING_SPINE_KEY,
    GOBLIN_PATCHWORK_PLAZA_KEY,
    GOBLIN_FLOODGATE_WALK_KEY,
)


def validate_goblin_starter_routes() -> None:
    """Fail fast if the safe Rattlefen core ever develops a dead exit.

    A player should never see an exit advertised by LOOK/EXITS and then discover
    that its destination is missing. Every starter-core exit is required to land
    in a real Goblin room and to have a matching way back.
    """

    authored = {room.key: room for room in GOBLIN_ROOMS}
    problems: list[str] = []

    for room in GOBLIN_ROOMS:
        for direction, destination_key in room.exits.items():
            destination = authored.get(destination_key)
            if destination is None:
                problems.append(f"{room.key} {direction} -> missing room {destination_key}")
                continue
            opposite = _OPPOSITE_DIRECTIONS.get(direction)
            if opposite and destination.exits.get(opposite) != room.key:
                problems.append(
                    f"{room.key} {direction} -> {destination_key} has no {opposite} return exit"
                )

    for room_key in GOBLIN_STARTER_ROUTE:
        if room_key not in authored:
            problems.append(f"starter route is missing {room_key}")

    start = authored.get(GOBLIN_START_ROOM_KEY)
    if start is not None and start.exits.get("north") != GOBLIN_SORTING_SPINE_KEY:
        problems.append("Clattergate north must lead directly to the Three Bells Sorting Spine")

    if problems:
        raise RuntimeError("Goblin starter-route contract failed:\n- " + "\n- ".join(problems))


def repair_goblin_location(session) -> bool:
    """Repair legacy/stale Goblin locations before the generic room engine runs.

    Some older characters can carry a region key, a deleted development room, or
    a blank room in current_room. The old runtime only repaired the blank case,
    which let LOOK advertise Goblin directions while movement fell through to
    'There are no authored exits from this area yet.' Any *invalid* room is now
    migrated to the real Clattergate start. Valid rooms outside Rattlefen remain
    untouched so travelled Goblins are never teleported home on login.
    """

    character = getattr(session, "character", None)
    if character is None or character.race != "goblin":
        return False

    changed = False
    if character.current_room not in legacy_world.ROOMS_BY_KEY:
        session.database.set_character_room(character.id, GOBLIN_START_ROOM_KEY)
        changed = True
    if character.bind_room not in legacy_world.ROOMS_BY_KEY:
        session.database.set_bind_room(character.id, GOBLIN_START_ROOM_KEY)
        changed = True

    if changed:
        refreshed = session.database.get_character_by_name(character.name)
        if refreshed is not None:
            session.character = refreshed
    return changed


def _goblin_npc_in_room(session, target: str):
    if session.character is None:
        return None
    room = legacy_world.ROOMS_BY_KEY.get(session.character.current_room or "")
    if room is None:
        return None
    normalized = target.strip().lower().removeprefix("to ").strip()
    for npc_key in room.npc_keys:
        npc = legacy_world.NPCS_BY_KEY.get(npc_key)
        if npc is None or not npc.key.startswith("goblin_"):
            continue
        aliases = {
            npc.name.lower(),
            npc.key.replace("_", " "),
            npc.name.lower().split()[0],
            npc.name.lower().split()[-1],
        }
        if not normalized or normalized in aliases:
            return npc
    return None


def install_goblin_runtime(player_session_class, world_service) -> None:
    """Add Goblin start placement and lightweight social interaction."""
    if getattr(player_session_class, "_goblin_start_runtime_installed", False):
        return

    validate_goblin_starter_routes()

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        repair_goblin_location(self)
        await previous_enter_character(self)
        if self.character is not None and self.character.race == "goblin":
            flags = self.database.list_flags(self.character.id)
            if "goblin_junk_city_welcomed" not in flags:
                self.database.grant_flag(self.character.id, "goblin_junk_city_welcomed")
                await self.send(
                    "\r\nJunk City does not stop to welcome you; it simply makes room. "
                    "Vikka Three-Nails works the intake counter here. TALK VIKKA if you want the quickest explanation of the city core.\r\n"
                )

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
            target = command.strip()[4:].strip() if len(command.strip()) > 4 else ""
            npc = _goblin_npc_in_room(self, target)
            if npc is not None:
                await self.send("\r\n")
                for line in npc.dialogue:
                    await self.send(line + "\r\n")
                return

        if normalized in {"city", "junk city", "district", "where am i"}:
            await self.send(
                "\r\n--- Junk City Core ---\r\n"
                "This is the busy, supervised heart of Goblin civilization: the Clattergate, Brassgut Market, the Sorting Spine, Patchwork Plaza, Tinker Row, the Ledger Hall, and Floodgate Walk. "
                "The core is intentionally safe. Floodgate Walk marks the point where future outer-swamp routes will become less controlled and more dangerous.\r\n"
            )
            return

        if normalized in {"shop", "wares", "market"} and self.character.current_room == GOBLIN_BRASSGUT_MARKET_KEY:
            await self.send(
                "\r\n--- Brassgut Market ---\r\n"
                "Dozens of independent stalls trade repaired tools, salvage, household goods, mechanisms, curios, clothing, and unidentified parts. "
                "The market is active, but permanent item prices and Astralis currency have not been finalized yet, so buying and selling are not enabled here yet. "
                "EXAMINE SALVAGE STALLS or TALK RUSKLE to learn more.\r\n"
            )
            return

        # Replay everything else into the complete seasonal/calendar/room stack.
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
                "Goblin start commands: CITY summarizes the safe Junk City core; TALK VIKKA and TALK RUSKLE speak with local contacts; Brassgut Market responds to SHOP/MARKET.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_start_runtime_installed = True
