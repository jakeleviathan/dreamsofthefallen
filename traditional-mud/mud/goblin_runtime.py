from __future__ import annotations

from mud.goblin_start import (
    GOBLIN_BRASSGUT_MARKET_KEY,
    GOBLIN_REGION_KEY,
    GOBLIN_START_ROOM_KEY,
)
import mud.world as legacy_world


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
    """Add Goblin start placement and lightweight social interaction.

    The district itself is intentionally safe. This layer does not introduce a
    tutorial combat encounter or invent an economy before those systems are
    designed; it gives the city real people to talk to and a useful market read.
    """
    if getattr(player_session_class, "_goblin_start_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "goblin":
            changed = False
            if not self.character.current_room:
                self.database.set_character_room(self.character.id, GOBLIN_START_ROOM_KEY)
                changed = True
            if not self.character.bind_room:
                self.database.set_bind_room(self.character.id, GOBLIN_START_ROOM_KEY)
                changed = True
            if changed:
                refreshed = self.database.get_character_by_name(self.character.name)
                if refreshed is not None:
                    self.character = refreshed
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
