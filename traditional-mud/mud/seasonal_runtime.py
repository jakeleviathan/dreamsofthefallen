from __future__ import annotations

from mud.astralis_time import ASTRALIS_CLOCK
from mud.seasonal_cultures import anchor_for_region, active_anchor_for_region, find_active_anchor


async def _replay_command(session, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in session.__dict__
    previous_instance_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    session.prompt = replay_prompt
    try:
        await previous_playing_prompt(session)
    finally:
        if had_instance_prompt:
            session.prompt = previous_instance_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_seasonal_runtime(player_session_class, world_service) -> None:
    """Layer culture-specific seasonal room behavior over calendar + room runtimes."""

    if getattr(player_session_class, "_seasonal_runtime_installed", False):
        return

    previous_show_current_room = player_session_class.show_current_room
    previous_playing_prompt = player_session_class.playing_prompt

    def current_region(session) -> str | None:
        if session.character is None:
            return None
        scene = world_service.scene(session.character.current_room or "")
        return None if scene is None else scene.region_key

    async def show_current_room(self) -> None:
        await previous_show_current_room(self)
        region_key = current_region(self)
        if region_key is None:
            return
        moment = ASTRALIS_CLOCK.now()
        anchor = active_anchor_for_region(region_key, moment.calendar)
        if anchor is None:
            return
        await self.send(f"\r\nSeasonal — {anchor.title}: {anchor.ambient_text}\r\n")
        await self.send(f"Seasonal feature: {anchor.feature_name}. Try EXAMINE {anchor.feature_name.upper()} or USE {anchor.feature_name.upper()}.\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        normalized = command.strip().lower()
        region_key = current_region(self)
        moment = ASTRALIS_CLOCK.now()
        date = moment.calendar
        regional_anchor = anchor_for_region(region_key or "")
        active_anchor = active_anchor_for_region(region_key or "", date)

        if normalized in {"season", "seasonal", "seasonal culture", "seasonal custom"}:
            await self.send(f"\r\nCurrent season: {date.season_name}, day {date.season_day} of {date.season_length}.\r\n")
            if regional_anchor is None:
                await self.send("This region does not yet have a race-specific seasonal anchor authored.\r\n")
                return
            if active_anchor is None:
                await self.send(
                    f"Regional seasonal anchor: {regional_anchor.title}, active during {regional_anchor.season_key.title()}. It is not active right now.\r\n"
                )
                return
            flag = active_anchor.observation_flag(date.year)
            observed = flag in self.database.list_flags(self.character.id)
            await self.send(f"Active regional anchor: {active_anchor.title} ({active_anchor.feature_name}).\r\n")
            await self.send(active_anchor.ambient_text + "\r\n")
            await self.send(f"Observed by this character in Year {date.year}: {'yes' if observed else 'no'}.\r\n")
            return

        if normalized in {"features", "feature", "details", "landmarks", "landmark"}:
            await _replay_command(self, previous_playing_prompt, command)
            if active_anchor is not None:
                await self.send(
                    f" - {active_anchor.feature_name} (seasonal): {active_anchor.title} is active during {date.season_name}.\r\n"
                )
            return

        pieces = normalized.split(maxsplit=1)
        action = pieces[0] if pieces else ""
        target = pieces[1] if len(pieces) == 2 else ""
        if target and action in {"look", "examine", "touch", "listen", "smell", "sniff", "use"}:
            anchor = find_active_anchor(region_key or "", date, target)
            if anchor is not None:
                if action in {"look", "examine"}:
                    text = anchor.examine_text
                elif action == "touch":
                    text = anchor.touch_text
                elif action == "listen":
                    text = anchor.listen_text
                elif action in {"smell", "sniff"}:
                    text = anchor.smell_text
                else:
                    text = anchor.use_text
                    flag = anchor.observation_flag(date.year)
                    flags = self.database.list_flags(self.character.id)
                    if flag not in flags:
                        self.database.grant_flag(self.character.id, flag)
                        text += f" You remember the custom as part of Year {date.year}; this seasonal observation is now recorded on your character."
                    else:
                        text += f" You have already recorded this seasonal custom during Year {date.year}."
                await self.send("\r\n" + text + "\r\n")
                return

        await _replay_command(self, previous_playing_prompt, command)

        if normalized in {"help", "?"}:
            await self.send(
                "Seasonal commands: SEASON shows the local culture's current seasonal anchor. Active anchors appear in room descriptions and FEATURES and can be LOOKed at, EXAMINEd, TOUCHED, LISTENed to, SMELLED, and USED. Using one records that yearly observation on the character.\r\n"
            )

    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class._seasonal_runtime_installed = True
