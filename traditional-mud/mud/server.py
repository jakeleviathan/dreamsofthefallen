import asyncio

# Register race-specific world content before session and room-runtime modules
# take their references to the shared room/crafting/quest registries.
from mud.dwarf_start import install_dwarf_content, install_dwarf_runtime
from mud.dwarf_first_shift import install_dwarf_first_shift_content, install_dwarf_first_shift_runtime
from mud.forest_elf_nurture import install_forest_elf_nurture_content, install_forest_elf_nurture_runtime
from mud.forest_elf_stewardship import install_forest_elf_stewardship_content, install_forest_elf_stewardship_runtime
from mud.forest_elf_home_and_omens import install_forest_elf_home_content, install_forest_elf_home_runtime
from mud.forest_elf_homecoming import install_forest_elf_homecoming_runtime
from mud.forest_elf_necromancer_start import (
    install_forest_elf_necromancer_content,
    install_forest_elf_necromancer_runtime,
)
from mud.forest_elf_druid_start import (
    install_forest_elf_druid_content,
    install_forest_elf_druid_runtime,
)
from mud.forest_elf_wizard_start import (
    install_forest_elf_wizard_content,
    install_forest_elf_wizard_runtime,
)
from mud.forest_elf_brute_start import (
    install_forest_elf_brute_content,
    install_forest_elf_brute_runtime,
)
from mud.forest_elf_priest_start import (
    install_forest_elf_priest_content,
    install_forest_elf_priest_runtime,
)
from mud.goblin_start import goblin_room_augmentations, install_goblin_world
from mud.human_blackwall_opening import install_human_blackwall_content, install_human_blackwall_runtime
from mud.human_cathedral_faith import install_human_cathedral_content, install_human_cathedral_runtime
from mud.moon_elf_beliefs import install_moon_elf_belief_runtime
from mud.moon_elf_city import install_moon_elf_city_content, install_moon_elf_city_runtime
from mud.moon_elf_third_chair import install_third_chair_content, install_third_chair_runtime
from mud.moon_elf_witness_start import (
    install_moon_elf_witness_start_content,
    install_moon_elf_witness_start_runtime,
)
from mud.moon_elf_necromancer_start import (
    install_moon_elf_necromancer_content,
    install_moon_elf_necromancer_runtime,
)
from mud.racial_abilities import (
    install_fast_learner_database_hook,
    install_racial_ability_definitions,
    install_racial_ability_runtime,
)
from mud.sporekin_depth import install_sporekin_depth_content, install_sporekin_depth_runtime
from mud.starter_class_moments import install_starter_class_moment_runtime
from mud.command_help import install_command_help_runtime
from mud.undead_start import install_undead_content, install_undead_runtime
from mud.troll_start import install_troll_content, install_troll_runtime
from mud.troll_raid_opening import install_troll_raid_content, install_troll_raid_runtime
from mud.troll_survivor_choice import (
    install_troll_survivor_choice_content,
    install_troll_survivor_choice_runtime,
)
from mud.troll_choice_echoes import (
    install_troll_choice_echo_content,
    install_troll_choice_echo_runtime,
)
from mud.equipment_system import install_equipment_runtime
from mud.equipment_accessory import install_accessory_runtime
from mud.login_experience import install_login_experience

install_dwarf_content()
install_dwarf_first_shift_content()
install_forest_elf_nurture_content()
install_forest_elf_stewardship_content()
install_forest_elf_home_content()
# The first dedicated Forest Elf class extension adds a public death-work grove
# to Hearthwalk, then waits until the shared racial opening is complete.
install_forest_elf_necromancer_content()
# Forest Elf Druids receive a gentler post-opening capstone in the nursery's
# Warmhouse: one healing spell surrounded by ordinary care and patient release.
install_forest_elf_druid_content()
# Forest Elf Wizards learn practical restraint at a communal tile kiln: ordinary
# controls first, one precise Coldfire Burst, then inspect whether the work held.
install_forest_elf_wizard_content()
# Forest Elf Brutes join an ordinary path crew: brace a dangerous load, lift with
# other people, then use Taunt to protect someone without turning danger into a fight.
install_forest_elf_brute_content()
# Forest Elf Priests serve at a family remembrance: listening and ritual matter
# without requiring grief to become a spell problem or evidence for a doctrine.
install_forest_elf_priest_content()
install_goblin_world()
install_human_blackwall_content()
install_human_cathedral_content()
# High Horizon must exist before PlayerSession imports the shared room and race
# registries so new Moon Elves enter a real starter city rather than a fallback.
install_moon_elf_city_content()
# The Third Chair extends High Horizon with its first guided social quest and
# therefore registers after the city it patches but before PlayerSession imports.
install_third_chair_content()
# The first dedicated race/class opening extension belongs to Moon Elf Witness
# Priests and grows naturally out of The Third Chair into practical healing.
install_moon_elf_witness_start_content()
# Moon Elf Necromancers get their own post-Third-Chair lesson in evidence,
# perspective, death residue, and the discipline not to invent a ghost.
install_moon_elf_necromancer_content()
install_undead_content()
install_troll_content()
install_troll_raid_content()
install_troll_survivor_choice_content()
install_troll_choice_echo_content()
# Deepen the existing Sporekin opening before PlayerSession snapshots shared
# quest, room, NPC, enemy, and race registries.
install_sporekin_depth_content()
# Lock all eight racial passive/at-will identities before PlayerSession imports
# RACES for character creation, then make Human Fast Learner executable.
install_racial_ability_definitions()
install_fast_learner_database_hook()

from mud.goblin_deep_mire import install_goblin_deep_mire_runtime
from mud.goblin_clans import install_goblin_clan_content, install_goblin_clan_runtime
from mud.goblin_return_loop import install_goblin_return_loop_content, install_goblin_return_loop_runtime
from mud.goblin_clan_followups import install_goblin_clan_followup_content, install_goblin_clan_followup_runtime

# Clan/deep-mire content depends on (and idempotently registers) the earlier
# Goblin layers. Register the safe return loop and second-wave clan quests before
# importing PlayerSession so generic room, quest, recipe, and help views can see
# the complete Goblin progression tree.
install_goblin_clan_content()
install_goblin_return_loop_content()
install_goblin_clan_followup_content()

from mud.astralis_human_district import HUMAN_DISTRICT
from mud.astralis_time import ASTRALIS_CLOCK, ASTRALIS_WEATHER, WeatherEvent
from mud.calendar_runtime import install_calendar_runtime
from mud.database import Database
from mud.goblin_runtime import install_goblin_runtime
from mud.goblin_salvage_quest import install_goblin_salvage_quest_runtime
from mud.goblin_outer_route import install_goblin_outer_route_runtime
from mud.goblin_swamp import install_goblin_swamp_runtime
from mud.goblin_swamp_access import enforce_first_piling_swamp_access
from mud.goblin_rattlefen_opening import install_rattlefen_opening_runtime
from mud.human_district import DistrictEvent
from mud.seasonal_cultures import SEASONAL_CULTURES, SeasonalCultureEvent
from mud.seasonal_runtime import install_seasonal_runtime
from mud.session import PlayerSession, SessionState
from mud.npcs import MobileNpcManager, NpcMovement
from mud.room_runtime import WORLD, install_room_runtime
from mud.room_state_storage import load_world_room_state, save_world_room_state


# The room runtime was created from the registered legacy world. Add the rich
# Goblin starter scene layers before anyone can request/cache those room scenes.
WORLD.augmentations.update(goblin_room_augmentations())

# Build the live command/runtime stack from broad room behavior outward into
# calendar/seasonal layers, then race-specific starter and progression systems.
install_room_runtime(PlayerSession)
install_calendar_runtime(PlayerSession, WORLD)
# Moon Elf culture interprets the existing astronomical moon cycle as a set of
# reflective customs rather than prophecy, fate, or worship.
install_moon_elf_belief_runtime(PlayerSession)
# High Horizon turns that philosophy into civic procedure and a lived-in city:
# rotating government, public Counterview, night markets, and Skyglass Spire.
install_moon_elf_city_runtime(PlayerSession, WORLD)
# The Third Chair lets new Moon Elves learn that philosophy through an ordinary
# civic disagreement, two physical viewpoints, and a non-punitive choice.
install_third_chair_runtime(PlayerSession, WORLD)
# Witness Priests receive a class-specific extension only after the shared Moon
# Elf opening: practical care, first Clearview Mending, and checking the result.
install_moon_elf_witness_start_runtime(PlayerSession, WORLD)
# Moon Elf Necromancers apply the same culture of perspective to death residue:
# two views, mapped boundaries, no invented ghost, and deliberate non-interference.
install_moon_elf_necromancer_runtime(PlayerSession, WORLD)
install_seasonal_runtime(PlayerSession, WORLD)
install_forest_elf_nurture_runtime(PlayerSession, WORLD)
install_forest_elf_stewardship_runtime(PlayerSession, WORLD)
# This outer Forest Elf layer turns the older Heartseed and Old River Path
# tutorials into the middle of a fuller home -> observation -> class-lens arc.
install_forest_elf_home_runtime(PlayerSession, WORLD)
# Finish that arc with a prepared wayroot return and a quiet homecoming beat.
install_forest_elf_homecoming_runtime(PlayerSession)
# Forest Elf Necromancers continue from the Hushed Verge observation into a
# grounded lesson about ordinary death, restraint, and their first Life Tap.
install_forest_elf_necromancer_runtime(PlayerSession, WORLD)
# Forest Elf Druids finish the shared opening with a quiet recovery shift that
# teaches Minor Heal, ordinary aftercare, patience, and non-ownership.
install_forest_elf_druid_runtime(PlayerSession, WORLD)
# Forest Elf Wizards finish with practical kiln work: inspect material and kiln,
# set ordinary controls, apply precise Coldfire, then verify the useful result.
install_forest_elf_wizard_runtime(PlayerSession, WORLD)
# Forest Elf Brutes learn protection through path work: control the load, use the
# crew, take hostile attention, and end the danger without needing to defeat it.
install_forest_elf_brute_runtime(PlayerSession, WORLD)
# Forest Elf Priests learn that communal ritual can serve grief without erasing it,
# proving a theology, or using magic simply because the class possesses magic.
install_forest_elf_priest_runtime(PlayerSession, WORLD)
install_dwarf_runtime(PlayerSession, WORLD)
install_dwarf_first_shift_runtime(PlayerSession, WORLD)
install_human_blackwall_runtime(PlayerSession, WORLD)
install_human_cathedral_runtime(PlayerSession, WORLD)
install_undead_runtime(PlayerSession, WORLD)
install_troll_runtime(PlayerSession, WORLD)
install_troll_raid_runtime(PlayerSession, WORLD)
install_troll_survivor_choice_runtime(PlayerSession, WORLD)
install_troll_choice_echo_runtime(PlayerSession, WORLD)
install_goblin_runtime(PlayerSession, WORLD)
install_goblin_salvage_quest_runtime(PlayerSession, WORLD)
install_goblin_outer_route_runtime(PlayerSession, WORLD)
install_goblin_swamp_runtime(PlayerSession, WORLD)
install_goblin_deep_mire_runtime(PlayerSession, WORLD)
install_goblin_return_loop_runtime(PlayerSession, WORLD)
install_goblin_clan_runtime(PlayerSession, WORLD)
install_goblin_clan_followup_runtime(PlayerSession, WORLD)
# The Rattlefen opening sits outside the older Goblin progression layers. New
# Goblins complete this richer six-part introduction first; legacy Goblins with
# existing salvage progress are grandfathered and never rewound.
install_rattlefen_opening_runtime(PlayerSession, WORLD)
# Racial kits sit outside race-specific quest layers so every class/race
# combination receives the same passive and at-will without room duplication.
install_racial_ability_runtime(PlayerSession)
# Sporekin now continue beyond the Forgotten Pulse into a mentor-led lesson on
# individual judgment, culture, and a safe first combat practice.
install_sporekin_depth_runtime(PlayerSession, WORLD)
# Every 8x5 race/class combination gets one compact class lesson automatically
# when a real authored milestone in that race's starter experience advances.
# There is no separate tutorial command and no duplicate room graph.
install_starter_class_moment_runtime(PlayerSession)
# Apply the authoritative First Piling branch gate last so no later content
# registration can accidentally expose the beginner swamp before Ruskle's lesson.
enforce_first_piling_swamp_access(WORLD)
# Equipment is deliberately the outermost game-command layer. It normalizes the
# final item catalog once, then notices quest rewards granted by existing runtimes.
install_equipment_runtime(PlayerSession)
# One universal accessory slot extends the base seven-slot equipment pass.
install_accessory_runtime(PlayerSession)
# The pre-character experience owns only opening/login/account/roster screens.
install_login_experience(PlayerSession)
# Command help is intentionally absolute outermost: one HELP stays concise, while
# COMMANDS/HELP ALL can summarize the fully assembled runtime without every inner
# feature layer appending its own help paragraph.
install_command_help_runtime(PlayerSession)


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
        # Seasonal culture transitions begin from the current calendar season;
        # startup itself does not replay a fake season-change announcement.
        SEASONAL_CULTURES.initialize(moment)

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

    async def broadcast_seasonal_culture_event(self, event: SeasonalCultureEvent) -> None:
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
        seasonal_task = asyncio.create_task(
            SEASONAL_CULTURES.run(
                self.broadcast_seasonal_culture_event,
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
            seasonal_task.cancel()
            await asyncio.gather(
                npc_task,
                weather_task,
                district_task,
                seasonal_task,
                return_exceptions=True,
            )
            save_world_room_state(WORLD.state)
