from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class StarterRaceLoop:
    """The minimum playable promise for one race's opening.

    This is deliberately a contract over authored content rather than another
    tutorial system. Each race already has (or grows through) its own quest and
    room runtime. The contract makes sure those openings remain reachable and
    that their identity is expressed through things the player actually does.
    """

    race_key: str
    region_key: str
    starting_room_key: str
    first_quest_key: str
    hook_name: str
    hook_summary: str
    player_actions: tuple[str, ...]
    completion_flag: str


STARTER_RACE_LOOPS: tuple[StarterRaceLoop, ...] = (
    StarterRaceLoop(
        race_key="human",
        region_key="human_kingdom",
        starting_room_key="human_demon_gate",
        first_quest_key="human_blackwall_readiness",
        hook_name="Blackwall Civic Readiness",
        hook_summary=(
            "A routine civic drill becomes an evidence-led caravan investigation, a real fight, "
            "and a first look at how outsiders understand the people they call Demons."
        ),
        player_actions=(
            "EXAMINE SIGNAL BOARD",
            "DRILL SIGNALS",
            "READ DAMAGE",
            "ATTACK BURROWER",
            "SEARCH NEST",
        ),
        completion_flag="human_blackwall_opening_complete",
    ),
    StarterRaceLoop(
        race_key="forest_elf",
        region_key="great_elf_forest",
        starting_room_key="forest_elf_circle_clearing",
        first_quest_key="forest_elf_first_walk",
        hook_name="The Old River Path",
        hook_summary=(
            "A comfortable woodland home gives way gradually to signs, still water, an old waystone, "
            "and a boundary where beauty and danger occupy the same forest."
        ),
        player_actions=(
            "FOLLOW THE RIVER",
            "EXAMINE WAYSTONE",
            "LISTEN",
            "REACH THE BOUNDARY OAK",
        ),
        completion_flag="forest_elf_first_walk_completed",
    ),
    StarterRaceLoop(
        race_key="moon_elf",
        region_key="moon_peaks",
        starting_room_key="moon_elf_high_horizon_plaza",
        first_quest_key="moon_elf_third_chair",
        hook_name="The Third Chair",
        hook_summary=(
            "The player sits inside an ordinary civic disagreement, then physically changes viewpoint "
            "before deciding what the evidence justifies."
        ),
        player_actions=(
            "SIT THIRD CHAIR",
            "TALK SERA",
            "TALK TALIN",
            "EXAMINE PATH",
            "EXAMINE ORCHARD",
        ),
        completion_flag="moon_elf_third_chair_complete",
    ),
    StarterRaceLoop(
        race_key="dwarf",
        region_key="dwarven_mountain_industry",
        starting_room_key="dwarf_foundry_concourse",
        first_quest_key="dwarf_first_work_order",
        hook_name="By Stamp and Steam",
        hook_summary=(
            "The player completes a real civic work order through registry, union safety procedure, "
            "pressure inspection, and operation of a working training lift."
        ),
        player_actions=(
            "TALK HELGA",
            "TALK TORREN",
            "EXAMINE PRESSURE GAUGE",
            "TURN BLEED VALVE",
            "OPERATE LIFT",
        ),
        completion_flag="dwarf_first_obligation_completed",
    ),
    StarterRaceLoop(
        race_key="goblin",
        region_key="junk_city_and_swamps",
        starting_room_key="goblin_clattergate",
        first_quest_key="goblin_rattlefen_three_bells",
        hook_name="Three Bells",
        hook_summary=(
            "A single salvage claim forces the player to choose what is useful, bargain over value, "
            "settle ownership, repurpose the part, and finally put their own mark on the economy."
        ),
        player_actions=(
            "EXAMINE FRESH WRECK",
            "CLAIM ONE PIECE",
            "BARGAIN",
            "RESOLVE THE CLAIM",
            "REPURPOSE SALVAGE",
        ),
        completion_flag="goblin_rattlefen_opening_complete",
    ),
    StarterRaceLoop(
        race_key="troll",
        region_key="troll_strongholds",
        starting_room_key="troll_frostroot_camp",
        first_quest_key="troll_fire_before_pride",
        hook_name="A Fire Before Pride",
        hook_summary=(
            "The player survives cold by reading wind, building shelter, laying a proper fire, and "
            "recovering beside it: Troll toughness is demonstrated as preparation, not stupidity or bravado."
        ),
        player_actions=(
            "EXAMINE WIND",
            "GATHER DEADFALL",
            "BUILD WINDBREAK",
            "LAY FIRE",
            "REST BY FIRE",
        ),
        completion_flag="troll_first_cold_complete",
    ),
    StarterRaceLoop(
        race_key="undead",
        region_key="desert_necropolis",
        starting_room_key="undead_reclamation_vault",
        first_quest_key="undead_no_voice_above_you",
        hook_name="No Voice Above You",
        hook_summary=(
            "The first thing an Undead player does is listen for a master's command and discover silence; "
            "they then inspect and sever the last binding themselves."
        ),
        player_actions=(
            "LISTEN",
            "TALK RECLAIMER",
            "EXAMINE BINDING",
            "SEVER ORDERS",
        ),
        completion_flag="undead_opening_complete",
    ),
    StarterRaceLoop(
        race_key="sporekin",
        region_key="sporekin_underways",
        starting_room_key="sporekin_lumen_hollow",
        first_quest_key="sporekin_first_call",
        hook_name="The Chorus Beneath",
        hook_summary=(
            "The shared Chorus guides the player through living mycelial paths toward the surface, "
            "then recedes enough for the individual to act away from the collective."
        ),
        player_actions=(
            "FOLLOW LIVING THREADS",
            "FOLLOW COOL AIR",
            "CLIMB TOWARD LIGHT",
            "CROSS THE VEIL",
        ),
        completion_flag="sporekin_first_call_answered",
    ),
)

STARTER_RACE_LOOPS_BY_RACE: dict[str, StarterRaceLoop] = {
    loop.race_key: loop for loop in STARTER_RACE_LOOPS
}


def starting_room_for_race(race_key: str | None) -> str | None:
    if not race_key:
        return None
    loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
    return loop.starting_room_key if loop is not None else None


def validate_starter_loop_contract(
    *,
    rooms_by_key: Mapping[str, object],
    quests_by_key: Mapping[str, object],
    race_keys: set[str] | frozenset[str],
) -> None:
    """Fail fast if any launch race loses its playable authored opening."""

    problems: list[str] = []
    loop_keys = set(STARTER_RACE_LOOPS_BY_RACE)

    missing_races = set(race_keys) - loop_keys
    extra_races = loop_keys - set(race_keys)
    if missing_races:
        problems.append("missing starter contracts for: " + ", ".join(sorted(missing_races)))
    if extra_races:
        problems.append("starter contracts reference unknown races: " + ", ".join(sorted(extra_races)))

    seen_hooks: set[str] = set()
    for loop in STARTER_RACE_LOOPS:
        room = rooms_by_key.get(loop.starting_room_key)
        if room is None:
            problems.append(f"{loop.race_key}: missing start room {loop.starting_room_key}")
        else:
            room_region = getattr(room, "region_key", None)
            if room_region != loop.region_key:
                problems.append(
                    f"{loop.race_key}: start room region is {room_region!r}, expected {loop.region_key!r}"
                )
            exits = getattr(room, "exits", None)
            if not exits:
                problems.append(f"{loop.race_key}: start room has no authored exit")

        if loop.first_quest_key not in quests_by_key:
            problems.append(f"{loop.race_key}: missing first quest {loop.first_quest_key}")
        if not loop.player_actions:
            problems.append(f"{loop.race_key}: no playable show-don't-tell actions recorded")
        if not loop.completion_flag:
            problems.append(f"{loop.race_key}: no completion signal recorded")
        if loop.hook_name in seen_hooks:
            problems.append(f"duplicate starter hook name: {loop.hook_name}")
        seen_hooks.add(loop.hook_name)

    if problems:
        raise RuntimeError("Starter-race contract failed:\n- " + "\n- ".join(problems))


def install_starter_room_database_hook(database_class) -> None:
    """Give every launch race a real room/bind point immediately at creation.

    Older code only assigned creation rooms for Human, Forest Elf, and Sporekin.
    Race-specific enter-character runtimes already reconcile the other starts,
    but this hook closes the product gap: the roster and database now know where
    every new character belongs before their first ENTER command.

    Quest creation remains owned by each race's authored runtime so their first
    arrival narration and migration logic continue to work exactly as designed.
    """

    if getattr(database_class, "_eight_race_starter_room_hook_installed", False):
        return

    previous_create_character = database_class.create_character

    def create_character(
        self,
        account_id: int,
        name: str,
        race: str,
        character_class: str,
        deity_key: str | None = None,
        stats=None,
    ):
        character = previous_create_character(
            self,
            account_id,
            name,
            race,
            character_class,
            deity_key=deity_key,
            stats=stats,
        )
        desired_room = starting_room_for_race(race)
        if desired_room is None:
            return character

        if character.current_room != desired_room:
            self.set_character_room(character.id, desired_room)
        if character.bind_room != desired_room:
            self.set_bind_room(character.id, desired_room)

        if character.current_room != desired_room or character.bind_room != desired_room:
            refreshed = self.get_character_by_name(character.name)
            if refreshed is not None:
                return refreshed
        return character

    database_class.create_character = create_character
    database_class._eight_race_starter_room_hook_installed = True
