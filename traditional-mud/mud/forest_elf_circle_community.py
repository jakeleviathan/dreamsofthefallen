"""Forest Elf Circle community pilot: joint Heartseed care and storm recovery.

The existing Heartseed tutorial and its quest-giving keeper stay untouched.
Two new noncombatant residents use the ordinary scheduled mobile NPC manager.
Their gatherings, interruptions and shared stories use a durable, reusable
community-event journal instead of player-session flags or scripted teleports.
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass

import mud.npcs as mobile_registry
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment
from mud.community_events import CommunityEvent, CommunityEventJournal
from mud.forest_elf_nurture import FOREST_ELF_HEARTSEED_BLOOMED_FLAG
from mud.forest_elf_home_and_omens import FOREST_ELF_HEARTHWALK_KEY
from mud.forest_elf_stewardship import FOREST_ELF_KEEPER_NURSERY_KEY
from mud.npc_conversation import _delegate_prompt
from mud.npcs import BEHAVIOR_ROUTINE, MobileNpcDefinition, MobileNpcManager, RoutineStop
from mud.world import FOREST_ELF_START_ROOM_KEY as CIRCLE

GREENWAY = "forest_elf_greenway"
REGION = "great_elf_forest"
COMMUNITY = "forest_elf_circle"
RITUAL = "heartseed_ritual"
DISRUPTION = "herb_border_storm"
STORY = "restored_heartseed"
SEVERE = frozenset(("storm", "thunderstorm"))
WET = frozenset(("rain", "storm", "thunderstorm", "snow"))
# A daily gathering and one storm disruption are the entire initial content
# scope; extending community behavior means adding authored event definitions,
# not adding more independent server movement loops.
CIRCLE_ROOMS = (CIRCLE, GREENWAY, FOREST_ELF_KEEPER_NURSERY_KEY, FOREST_ELF_HEARTHWALK_KEY)

OTHIRA = MobileNpcDefinition(
    key="forest_elf_circle_druid_othira_mossweft",
    name="Druid Othira Mossweft",
    short_description="a patient Druid carrying damp root wraps and a slim notebook of Heartseed observations",
    spawn_room_key=FOREST_ELF_KEEPER_NURSERY_KEY,
    allowed_room_keys=CIRCLE_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("othira", "mossweft"),
    routine_schedule=(
        RoutineStop(0, FOREST_ELF_KEEPER_NURSERY_KEY),
        RoutineStop(5, CIRCLE),
        RoutineStop(9, FOREST_ELF_KEEPER_NURSERY_KEY),
        RoutineStop(13, GREENWAY),
        RoutineStop(17, CIRCLE),
        RoutineStop(19, FOREST_ELF_HEARTHWALK_KEY),
        RoutineStop(22, FOREST_ELF_KEEPER_NURSERY_KEY),
    ),
    weather_shelter_room_key=CIRCLE,
    shelter_weathers=tuple(sorted(SEVERE)),
)
ZELIK = MobileNpcDefinition(
    key="forest_elf_circle_keeper_zelik_fernstitch",
    name="Keeper Zelik Fernstitch",
    short_description="a practical herb keeper with a basket of reed braces and weather-worn planting tags",
    spawn_room_key=FOREST_ELF_HEARTHWALK_KEY,
    allowed_room_keys=CIRCLE_ROOMS,
    behavior=BEHAVIOR_ROUTINE,
    move_chance_per_tick=1.0,
    aliases=("zelik", "fernstitch"),
    routine_schedule=(
        RoutineStop(0, FOREST_ELF_HEARTHWALK_KEY),
        RoutineStop(5, CIRCLE),
        RoutineStop(9, GREENWAY),
        RoutineStop(13, FOREST_ELF_KEEPER_NURSERY_KEY),
        RoutineStop(17, CIRCLE),
        RoutineStop(19, FOREST_ELF_HEARTHWALK_KEY),
    ),
    weather_shelter_room_key=CIRCLE,
    shelter_weathers=tuple(sorted(SEVERE)),
)
CIRCLE_LIVING_NPCS = (OTHIRA, ZELIK)
CIRCLE_KEYS = frozenset(npc.key for npc in CIRCLE_LIVING_NPCS)


def register_circle_living_npcs() -> None:
    additions: list[MobileNpcDefinition] = []
    for npc in CIRCLE_LIVING_NPCS:
        existing = mobile_registry.MOBILE_NPCS_BY_KEY.get(npc.key)
        if existing is not None and existing != npc:
            raise ValueError("Conflicting Circle mobile NPC: " + npc.key)
        if existing is None:
            additions.append(npc)
        mobile_registry.MOBILE_NPCS_BY_KEY[npc.key] = npc
    if additions:
        mobile_registry.MOBILE_NPC_DEFINITIONS += tuple(additions)


register_circle_living_npcs()


def gathered(manager: MobileNpcManager, room: str = CIRCLE) -> bool:
    return all(
        (state := manager.states.get(actor.key)) is not None
        and state.active and state.current_room_key == room
        for actor in CIRCLE_LIVING_NPCS
    )


def _visible(manager: MobileNpcManager | None, room: str):
    if manager is None or room not in CIRCLE_ROOMS:
        return ()
    return tuple(
        state.definition for state in manager.npcs_in_room(room)
        if state.definition.key in CIRCLE_KEYS
    )


RITUAL_OPENING = (
    "Keeper Maelis moves a bowl of water into the shade of the seven Circle stones. "
    "'We are not here to command the Heartseed. We are here to see what it needs.'",
    "Druid Othira Mossweft checks the Heartseed's leaves while Keeper Zelik "
    "Fernstitch loosens the soil at the outer edge of the herb border.",
    "The three work together in a quiet dawn rite: observe, tend only what needs "
    "tending, and leave the rest of the morning to the roots.",
)
RITUAL_CLOSING = (
    "Maelis puts the bowl away. 'The Heartseed's growth is its own answer. "
    "Our part was to make the answer possible.'",
    "Othira and Zelik return the gathering tools to their places. "
    "The Circle resumes its ordinary morning work.",
)
STORM_DAMAGE = (
    "A hard gust tears across Circle Clearing. A low reed brace snaps and the "
    "herb border begins to wash out beneath the seven stones.",
    "Maelis calls for the nursery wraps and spare stakes. "
    "Othira and Zelik abandon their ordinary rounds and come to help.",
)
REPAIR_START = (
    "With the worst wind past, Othira holds the exposed roots steady while "
    "Zelik resets the reed braces. Maelis checks that the Heartseed's own bed "
    "has not been disturbed.",
    "They work in pairs rather than forcing the damaged herbs upright. "
    "You could HELP REPAIR BORDER if you want to lend a hand.",
)
REPAIR_FINISHED = (
    "Zelik sets the last brace. Othira checks the water path, and Maelis "
    "finds the newly settled soil firm enough to leave alone.",
    "The herb border is secure again. The little teaching patch of "
    "Silvermoss under the flat stones was kept safe throughout.",
)


@dataclass(slots=True)
class CircleCommunityDirector:
    journal: CommunityEventJournal

    @classmethod
    def for_database(cls, database) -> "CircleCommunityDirector":
        return cls(CommunityEventJournal(database))

    @staticmethod
    def _key(day: int) -> str:
        return str(day)

    def incident(self) -> CommunityEvent | None:
        event = self.journal.recent(COMMUNITY, DISRUPTION)
        return event if event is not None and event.stage in {"damaged", "tending"} else None

    def ritual(self, day: int) -> CommunityEvent | None:
        return self.journal.get(COMMUNITY, RITUAL, self._key(day))

    def _route_group(self, manager: MobileNpcManager, active: bool) -> None:
        # The core manager still owns every step of the route and the movement
        # broadcasts. The override only changes a resident's desired workplace.
        for npc in CIRCLE_LIVING_NPCS:
            if active and npc.key in manager.states:
                manager.routine_overrides[npc.key] = CIRCLE
            else:
                manager.routine_overrides.pop(npc.key, None)

    def pulse(
        self, manager: MobileNpcManager, moment: AstralisMoment, weather: str,
    ) -> tuple[str, ...]:
        """Advance only on world-time/weather changes; safe to call repeatedly."""
        day, minute = moment.day_number, moment.total_minutes
        weather = weather.casefold()
        messages: list[str] = []
        last_weather = self.journal.meta(COMMUNITY, "last_weather")
        pending = self.incident()

        # The first sample is a baseline. Restarting into an existing storm
        # must never fabricate another damaged garden.
        if last_weather is None:
            self.journal.set_meta(COMMUNITY, "last_weather", weather)
        elif last_weather != weather:
            self.journal.set_meta(COMMUNITY, "last_weather", weather)
            last_damage_day = self.journal.meta(COMMUNITY, "last_damage_day")
            if (weather in SEVERE and last_weather not in SEVERE
                    and pending is None and last_damage_day != str(day)):
                event, created = self.journal.start_once(
                    COMMUNITY, DISRUPTION, self._key(day), day, minute, stage="damaged",
                )
                self.journal.set_meta(COMMUNITY, "last_damage_day", str(day))
                if created:
                    pending = event
                    messages.extend(STORM_DAMAGE)

        ritual = self.ritual(day)
        ritual_due = (
            weather not in SEVERE and pending is None
            and (
                (5 <= moment.hour < 8 and ritual is None)
                or (ritual is not None and ritual.stage == "active")
            )
        )
        self._route_group(manager, bool(pending) or ritual_due)

        if pending is not None:
            if weather in SEVERE:
                if pending.stage == "tending":
                    self.journal.advance(pending, "tending", "damaged", minute)
                    messages.append(
                        "Another gust tears across the herb border. The keepers "
                        "pause their repairs until the wind calms."
                    )
            elif gathered(manager):
                if pending.stage == "damaged":
                    if self.journal.advance(pending, "damaged", "tending", minute):
                        messages.extend(REPAIR_START)
                elif pending.stage == "tending" and minute - pending.stage_minute >= 10:
                    if self.journal.advance(pending, "tending", "repaired", minute):
                        messages.extend(REPAIR_FINISHED)
                        self._route_group(manager, False)
            return tuple(messages)

        if ritual_due and gathered(manager):
            if ritual is None:
                ritual, created = self.journal.start_once(
                    COMMUNITY, RITUAL, self._key(day), day, minute,
                )
                if created:
                    messages.extend(RITUAL_OPENING)
                    story = self.journal.latest_story(COMMUNITY, STORY)
                    if story is not None:
                        messages.append(
                            "Maelis recalls how " + story[0]
                            + " helped a young Heartseed recover, and the keepers "
                            "compare what they learned from that care."
                        )
            elif ritual.stage == "active" and minute - ritual.stage_minute >= 8:
                if self.journal.advance(ritual, "active", "completed", minute):
                    participant = self.journal.latest_participant(ritual, "joined")
                    if participant:
                        messages.append(
                            "Maelis thanks " + participant
                            + " for sharing the quiet morning work."
                        )
                    messages.extend(RITUAL_CLOSING)
                    self._route_group(manager, False)

        return tuple(messages)

    def help_repair(
        self, manager: MobileNpcManager, character_id: int,
        moment: AstralisMoment, weather: str,
    ) -> tuple[str, ...]:
        event = self.incident()
        if event is None:
            return ("The herb border does not need emergency repairs right now.",)
        if weather.casefold() in SEVERE:
            return ("The wind is still tearing through the clearing. The Circle "
                    "will work on the roots when it is safe to do so.",)
        if not gathered(manager):
            return ("The Circle's keepers are gathering their tools. "
                    "Wait for Othira and Zelik to arrive.",)
        if event.stage == "damaged":
            self.journal.advance(event, "damaged", "tending", moment.total_minutes)
        if not self.journal.participate(event, character_id, "repair", moment.total_minutes):
            return ("Your help is already part of this repair. "
                    "The Circle has your work recorded.",)
        # All three local keepers are present; with a player's help they can
        # finish early without waiting for the automatic ten-minute work period.
        changed = self.journal.advance(event, "tending", "repaired", moment.total_minutes)
        self._route_group(manager, False)
        return (
            "You hold the loosened herb roots while Zelik resets the stakes. "
            "Othira shapes the runoff channel and Maelis checks every patch "
            "before the three of you stand back.",
            "The herb border is repaired. The Circle remembers your help."
        ) if changed else ("The Circle records your help with the garden.",)

    def join_ritual(
        self, manager: MobileNpcManager, character_id: int,
        moment: AstralisMoment,
    ) -> tuple[str, ...]:
        event = self.ritual(moment.day_number)
        if event is None or event.stage != "active" or not gathered(manager):
            return ("The Circle gathers at dawn when Maelis, Othira and Zelik "
                    "are together. Watch for their next Heartseed rite.",)
        if not self.journal.participate(event, character_id, "joined", moment.total_minutes):
            return ("You are already taking part in this morning's Heartseed rite.",)
        return (
            "You join the keepers beside the seven stones. Othira offers you "
            "the water bowl while Zelik makes room at the herb border.",
            "Maelis nods. 'The work is shared. That is how a Circle holds together.'",
        )

    def share_heartseed(
        self, character_id: int, moment: AstralisMoment,
    ) -> tuple[str, ...]:
        if not self.journal.share_story(COMMUNITY, STORY, character_id, moment.total_minutes):
            return ("The Circle already remembers the Heartseed story you shared.",)
        return (
            "You tell the Circle how the Heartseed recovered after careful "
            "observation, Silvermoss and time.",
            "Maelis adds the lesson to the shared care slates. "
            "Other keepers can now refer to what you discovered.",
        )

    def scene_line(self, moment: AstralisMoment) -> str:
        incident = self.journal.recent(COMMUNITY, DISRUPTION)
        if incident is not None and incident.stage == "damaged":
            return (
                "Community: The last storm has torn loose the herb border. "
                "The protected Silvermoss teaching patch remains usable; "
                "Othira and Zelik are being called to help."
            )
        if incident is not None and incident.stage == "tending":
            return (
                "Community: Othira and Zelik are repairing the storm-battered "
                "herb border with Maelis. HELP REPAIR BORDER to work beside them."
            )
        ritual = self.ritual(moment.day_number)
        if ritual is not None and ritual.stage == "active":
            return (
                "Community: The dawn Heartseed rite is underway. "
                "JOIN RITUAL to help the keepers."
            )
        if incident is not None and incident.stage == "repaired" and incident.day >= moment.day_number - 1:
            return (
                "Community: Fresh reed braces mark the herb border. "
                "The Circle repaired the storm damage together."
            )
        if ritual is not None and ritual.stage == "completed":
            return "Community: The Heartseed rite has ended. The seven stones are quiet again."
        story = self.journal.latest_story(COMMUNITY, STORY)
        if story is not None:
            return "Community: The care slates remember " + story[0] + "'s Heartseed discovery."
        return ""

    def status_lines(self, moment: AstralisMoment) -> tuple[str, ...]:
        lines = ["--- Circle Community ---"]
        ritual = self.ritual(moment.day_number)
        if ritual is None:
            lines.append("Heartseed: The keepers plan their next gathering at dawn.")
        elif ritual.stage == "active":
            lines.append("Heartseed: The shared dawn rite is underway. JOIN RITUAL here.")
        else:
            lines.append("Heartseed: Today's rite is complete.")
        incident = self.journal.recent(COMMUNITY, DISRUPTION)
        if incident is None:
            lines.append("Herb border: The teaching beds are well kept.")
        elif incident.stage == "damaged":
            lines.append("Herb border: Storm damaged. The keepers are gathering to repair it.")
        elif incident.stage == "tending":
            lines.append("Herb border: Repair underway. HELP REPAIR BORDER in Circle Clearing.")
        else:
            lines.append("Herb border: The last storm damage has been repaired.")
        story = self.journal.latest_story(COMMUNITY, STORY)
        if story:
            lines.append("Shared story: " + story[0] + " helped restore a Heartseed.")
        return tuple(lines)

    def ambient_lines(
        self, manager: MobileNpcManager, moment: AstralisMoment, weather: str,
        *, rng: random.Random | None = None,
    ) -> tuple[str, ...]:
        visible = _visible(manager, CIRCLE)
        if not visible:
            return ()
        rng = rng or random.Random()
        incident = self.incident()
        if incident is not None and gathered(manager):
            if incident.stage == "damaged":
                return (
                    "Zelik checks the herb stakes while Othira waits for the wind to ease.",
                    "Maelis warns them to leave the exposed roots alone until the gusts pass.",
                )
            return (
                "Othira and Zelik exchange quiet instructions over the damaged herb border.",
                "Maelis checks the teaching patch, keeping the novice Silvermoss safe.",
            )
        ritual = self.ritual(moment.day_number)
        if ritual is not None and ritual.stage == "active" and gathered(manager):
            return (
                "Othira examines the Heartseed without touching its new growth.",
                "Zelik passes Maelis the water bowl. 'No more moisture than the roots need.'",
            )
        story = self.journal.latest_story(COMMUNITY, STORY)
        if story is not None and rng.random() < 0.45:
            return (
                "Maelis mentions " + story[0] + "'s work with the Heartseed "
                "as an example of patient care, not stronger magic.",
            )
        actor = rng.choice(visible)
        if actor.key == OTHIRA.key:
            return (
                "Othira folds a damp root wrap and makes a note about tomorrow's nursery beds.",
            )
        return (
            "Zelik replaces a weather-faded herb marker and checks the soil beneath it.",
        )


async def run_circle_community(
    director: CircleCommunityDirector,
    manager: MobileNpcManager,
    player_rooms_provider: Callable[[], Iterable[str]],
    broadcast: Callable[[str, str], Awaitable[None]],
    weather_provider: Callable[[str], str],
    *,
    interval_seconds: float = 5.0,
    ambient_seconds: float = 115.0,
) -> None:
    """One shared pulse runs with no listeners; speech needs an occupied room."""
    loop = asyncio.get_running_loop()
    last_ambient = loop.time()
    rng = random.Random()
    while True:
        await asyncio.sleep(interval_seconds)
        moment = ASTRALIS_CLOCK.now()
        weather = weather_provider(REGION)
        messages = director.pulse(manager, moment, weather)
        occupied = CIRCLE in set(player_rooms_provider())
        if occupied and messages:
            await broadcast(CIRCLE, "\r\n".join(messages))
        if occupied and loop.time() - last_ambient >= ambient_seconds:
            last_ambient = loop.time()
            if rng.random() < 0.75:
                lines = director.ambient_lines(manager, moment, weather, rng=rng)
                if lines:
                    await broadcast(CIRCLE, "\r\n".join(lines))


def resolve_circle_talk(
    manager: MobileNpcManager | None, room: str, target: str,
) -> MobileNpcDefinition | None:
    if not target:
        return None
    query = " ".join(target.casefold().replace("-", " ").split())
    if query.startswith("to "):
        query = query[3:]
    matches = [
        actor for actor in _visible(manager, room)
        if query in {
            actor.name.casefold(),
            actor.name.split()[1].casefold(),
            actor.name.split()[-1].casefold(),
            *(alias.casefold() for alias in actor.aliases),
        }
    ]
    return matches[0] if len(matches) == 1 else None


def talk_lines(
    actor: MobileNpcDefinition, moment: AstralisMoment,
    weather: str, director: CircleCommunityDirector,
) -> tuple[str, ...]:
    incident = director.incident()
    if incident is not None:
        if actor.key == OTHIRA.key:
            return (actor.name + " says, 'When the wind stops, we repair the "
                    "water path first. Roots do not wait for speeches.'",)
        return (actor.name + " says, 'I have the replacement braces ready. "
                "The small teaching patch is safe beneath its stones.'",)
    ritual = director.ritual(moment.day_number)
    if ritual is not None and ritual.stage == "active":
        return (actor.name + " says, 'The Circle works together at dawn. "
                "You can JOIN RITUAL if you wish.'",)
    if weather.casefold() in WET:
        return (actor.name + " says, 'Wet weather is for checking drainage, "
                "not for demanding that every leaf grow faster.'",)
    if actor.key == OTHIRA.key:
        return (actor.name + " says, 'Morning care at the stones, nursery "
                "work in the daylight. A good routine leaves room for surprises.'",)
    return (actor.name + " says, 'The herb border teaches where to gather "
            "and where to leave things alone. We work with both lessons.'",)


def install_circle_community_runtime(player_session_class) -> None:
    """An outer, strictly scoped command layer; original starter quests win."""
    if getattr(player_session_class, "_circle_community_installed", False):
        return
    previous_prompt = player_session_class.playing_prompt
    previous_room = player_session_class.show_current_room

    def _director(session) -> CircleCommunityDirector | None:
        attached = getattr(session, "circle_community", None)
        if attached is not None:
            return attached
        database = getattr(session, "database", None)
        return CircleCommunityDirector.for_database(database) if database is not None else None

    async def show_current_room(self) -> None:
        await previous_room(self)
        character = getattr(self, "character", None)
        if character is None or character.current_room != CIRCLE:
            return
        director = _director(self)
        if director is not None:
            line = director.scene_line(ASTRALIS_CLOCK.now())
            if line:
                await self.send("\r\n" + line + "\r\n")

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.casefold().strip().split())
        room = character.current_room or ""
        if room != CIRCLE and room not in CIRCLE_ROOMS:
            await _delegate_prompt(self, previous_prompt, command)
            return

        director = _director(self)
        manager = getattr(self, "mobile_npcs", None)
        if director is None:
            await _delegate_prompt(self, previous_prompt, command)
            return
        moment = ASTRALIS_CLOCK.now()
        try:
            from mud.room_runtime import WORLD
            weather = WORLD.state.weather_for(REGION)
        except (AttributeError, KeyError):
            weather = "clear"

        if room == CIRCLE and normalized in {"circle", "circle status", "community", "circle community"}:
            await self.send("\r\n" + "\r\n".join(director.status_lines(moment)) + "\r\n")
            return
        if room == CIRCLE and normalized in {"join ritual", "join heartseed ritual"}:
            lines = director.join_ritual(manager, character.id, moment) if manager is not None else (
                "The keepers have not gathered yet.",
            )
            await self.send("\r\n" + "\r\n".join(lines) + "\r\n")
            return
        if room == CIRCLE and normalized in {"help repair border", "help repair herb border"}:
            lines = director.help_repair(manager, character.id, moment, weather) if manager is not None else (
                "The keepers are gathering first.",
            )
            await self.send("\r\n" + "\r\n".join(lines) + "\r\n")
            return
        if room == CIRCLE and normalized in {"share heartseed story", "tell circle about heartseed"}:
            flags = self.database.list_flags(character.id)
            if FOREST_ELF_HEARTSEED_BLOOMED_FLAG not in flags:
                await self.send(
                    "\r\nRestore the Heartseed during the Circle's tending lesson "
                    "before sharing a story about its recovery.\r\n"
                )
                return
            await self.send("\r\n" + "\r\n".join(
                director.share_heartseed(character.id, moment)
            ) + "\r\n")
            return
        if room == CIRCLE and normalized in {"examine herb border", "look herb border"}:
            incident = director.incident()
            if incident is not None:
                await self.send(
                    "\r\nThe storm has pulled loose the outside reed braces. "
                    "Othira and Zelik are organizing the repair with Maelis. "
                    "The protected Silvermoss teaching patch remains harvestable.\r\n"
                )
                return
        parts = command.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].casefold() == "talk":
            actor = resolve_circle_talk(manager, room, parts[1])
            if actor is not None:
                await self.send("\r\n" + "\r\n".join(
                    talk_lines(actor, moment, weather, director)
                ) + "\r\n")
                return

        # In particular, do not capture TALK MAELIS, GATHER SILVERMOSS,
        # TEND HEARTSEED, WAIT, existing quest actions, or generic HELP.
        await _delegate_prompt(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class.show_current_room = show_current_room
    player_session_class._circle_community_installed = True
