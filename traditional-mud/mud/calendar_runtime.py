from __future__ import annotations

from mud.astralis_calendar import ASTRALIS_DAYS_PER_YEAR, MOON_CYCLE_DAYS, SEASONS, calendar_rules_text
from mud.astralis_time import ASTRALIS_CLOCK


def install_calendar_runtime(player_session_class, world_service) -> None:
    """Layer calendar commands over the existing room runtime.

    This intentionally wraps the already-installed room runtime rather than
    duplicating its exploration/business/reflection command logic.
    """

    if getattr(player_session_class, "_calendar_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

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
        moment = ASTRALIS_CLOCK.now()
        date = moment.calendar

        if normalized in {"date", "today", "astralis date"}:
            await self.send(
                f"Astralis date: {date.display}. Current time: {moment.hour:02d}:{moment.minute:02d} ({moment.phase}).\r\n"
            )
            return

        if normalized in {"calendar", "year", "seasons", "moon", "moon phase"}:
            await self.send("\r\n--- Astralis Calendar ---\r\n")
            await self.send(f"Current date: {date.display}.\r\n")
            await self.send(f"Current time: {moment.hour:02d}:{moment.minute:02d} ({moment.phase}).\r\n")
            await self.send(f"Year length: {ASTRALIS_DAYS_PER_YEAR} days.\r\n")
            await self.send("Seasons:\r\n")
            for season in SEASONS:
                await self.send(
                    f" - {season.name}: days {season.start_day}-{season.end_day} ({season.length_days} days)\r\n"
                )
            await self.send(
                f"Moon cycle: {MOON_CYCLE_DAYS} days — New Moon -> Waxing Moon -> Full Moon -> Waning Moon.\r\n"
            )
            await self.send(
                "Month names have intentionally not been authored yet; the calendar currently tracks year, day, season, and moon phase.\r\n"
            )
            return

        if normalized in {"time", "clock", "astralis time"}:
            await self.send(
                f"Astralis time: {moment.calendar_display}. One full Astralis day passes every four real hours; each Astralis hour lasts ten real minutes.\r\n"
            )
            return

        if normalized in {"weather", "conditions"}:
            scene = world_service.scene(self.character.current_room or "")
            if scene is None:
                await self.send("You cannot get a clear read on the weather here.\r\n")
                return
            weather = world_service.state.weather_for(scene.region_key)
            context = moment.regional_context(scene.region_key)
            await self.send(
                f"Regional weather: {weather}. Season: {context.season.title()}. Moon: {date.moon_phase_name}. "
                f"Astralis date: Year {date.year}, Day {date.day_of_year}/{ASTRALIS_DAYS_PER_YEAR}; "
                f"time {moment.hour:02d}:{moment.minute:02d} ({moment.phase}).\r\n"
            )
            return

        # Replay the command into the complete room/session command stack.
        had_instance_prompt = "prompt" in self.__dict__
        previous_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await previous_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = previous_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"help", "?"}:
            await self.send(
                "Calendar commands: DATE shows today's year/day/season/moon; CALENDAR shows the 90-day year and four-season structure; TIME and WEATHER include calendar context.\r\n"
            )

    player_session_class.playing_prompt = playing_prompt
    player_session_class._calendar_runtime_installed = True
