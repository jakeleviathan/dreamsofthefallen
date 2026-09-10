import asyncio

from mud.astralis_human_district import HUMAN_DISTRICT
from mud.astralis_time import ASTRALIS_CLOCK, ASTRALIS_WEATHER, WeatherEvent
from mud.calendar_runtime import install_calendar_runtime
from mud.database import Database
from mud.human_district import DistrictEvent
from mud.session import PlayerSession, SessionState
from mud.npcs import MobileNpcManager, NpcMovement
from mud.room_runtime import WORLD, install_room_runtime
from mud.room_state_storage import load_world_room_state, save_world_room_state


# Install room behavior first, then layer calendar/date commands over that
# complete command stack so existing exploration and quest handling stay intact.
install_room_runtime(PlayerSession)
install_calendar_runtime(PlayerSession, WORLD)


class MudServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 4000) -> None:
        self.host = host
        self.port = port
        self.sessions: set[PlayerSession] = set()
        self.database = Database()
        self.mobile_npcs = MobileNpcManager()
        load_world_room_state(WORLD.state)

        moment = ASTRALIS_CLOCK.now()
        # Regional weather is persistent shared state. Missing regions receive
        # biome-appropriate defaults before businesses inspect weather.
        ASTRALIS_WEATHER.initialize(moment, WORLD.state)
        # Scheduled business state wins over stale saved door state. Temporary
        # rain shutters are rebuilt from the current weather on startup.
        HUMAN_DISTRICT.initialize(moment, WORLD.state)

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        session = PlayerSession(
            reader=reader,
            writer=writer,
            database=self.database,
            mobile_npcs=self.mobile_npcs,
            mobile_npc_movement_callback=self.broadcast_npc_movement,
        )
        self.sessions.add(session)
        try:
            await session.run()
        finally:
            self.sessions.discard(session)

    def player_room_keys(self) -> tuple[str, ...]:
        return tuple(
            session.character.current_room
            for session in self.sessions
            if session.state is SessionState.PLAYING
            and session.character is not None
            and session.character.current_room
        )

    async def broadcast_npc_movement(self, movement: NpcMovement) -> None:
        destination_sessions: list[PlayerSession] = []
        for session in tuple(self.sessions):
            if session.state is not SessionState.PLAYING or session.character is None:
                continue
            room_key = session.character.current_room
            if room_key == movement.origin_room_key:
                await session.send(
                    f"\r\n{movement.npc_name} {movement.movement_verb} {movement.direction}.\r\n> "
                )
            elif room_key == movement.destination_room_key:
                destination_sessions.append(session)
                await session.send(
                    f"\r\n{movement.npc_name} {movement.movement_verb} in from the {movement.arrival_from}.\r\n> "
                )
                if movement.behavior == "hunter" and movement.reason == "pursuit":
                    await session.send(
                        f"{movement.npc_name} fixes its attention on you and continues to stalk your trail.\r\n> "
                    )

        for session in destination_sessions:
            await session.check_mobile_npc_aggression(movement.npc_key)

    async def broadcast_district_event(self, event: DistrictEvent) -> None:
        room_keys = set(event.room_keys)
        for session in tuple(self.sessions):
            if session.state is not SessionState.PLAYING or session.character is None:
                continue
            if session.character.current_room not in room_keys:
                continue
            await session.send(f"\r\n{event.text}\r\n> ")

    async def broadcast_weather_event(self, event: WeatherEvent) -> None:
        for session in tuple(self.sessions):
            if session.state is not SessionState.PLAYING or session.character is None:
                continue
            scene = WORLD.scene(session.character.current_room or "")
            if scene is None or scene.region_key != event.region_key:
                continue
            await session.send(f"\r\n{event.text}\r\n> ")

    async def run(self) -> None:
        server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port,
        )

        addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
        moment = ASTRALIS_CLOCK.now()
        print(f"Dreams of the Fallen listening on {addresses}")
        print(f"Astralis clock: {moment.calendar_display} (4 real hours per world day)")
        print(f"Connect with a Telnet client on port {self.port}.")

        npc_task = asyncio.create_task(
            self.mobile_npcs.run(
                self.broadcast_npc_movement,
                player_rooms_provider=self.player_room_keys,
                hour_provider=lambda: ASTRALIS_CLOCK.now().hour,
            )
        )
        weather_task = asyncio.create_task(
            ASTRALIS_WEATHER.run(
                WORLD.state,
                self.broadcast_weather_event,
                clock=ASTRALIS_CLOCK,
                interval_seconds=5.0,
            )
        )
        district_task = asyncio.create_task(
            HUMAN_DISTRICT.run(
                WORLD.state,
                self.broadcast_district_event,
                now_provider=ASTRALIS_CLOCK.now,
                interval_seconds=5.0,
            )
        )
        try:
            async with server:
                await server.serve_forever()
        finally:
            npc_task.cancel()
            weather_task.cancel()
            district_task.cancel()
            await asyncio.gather(npc_task, weather_task, district_task, return_exceptions=True)
            save_world_room_state(WORLD.state)
