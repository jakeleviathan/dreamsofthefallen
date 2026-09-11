from __future__ import annotations

from dataclasses import dataclass

from mud.astralis_time import ASTRALIS_CLOCK


MOON_ELF_BELIEF_INTRO_FLAG = "moon_elf_lunar_philosophy_introduced"


@dataclass(frozen=True, slots=True)
class MoonPhaseMeaning:
    key: str
    name: str
    emphasis: str
    practice: str


# Moon phases are cultural prompts for reflection, not omens, horoscopes, or
# commands. A Moon Elf can ignore a custom without being treated as impious.
MOON_PHASE_MEANINGS: tuple[MoonPhaseMeaning, ...] = (
    MoonPhaseMeaning(
        key="new",
        name="New Moon",
        emphasis="privacy and beginnings",
        practice=(
            "New work is allowed to remain unfinished and private. A person is not expected "
            "to explain a decision before it has had time to become one."
        ),
    ),
    MoonPhaseMeaning(
        key="waxing",
        name="Waxing Moon",
        emphasis="inquiry and preparation",
        practice=(
            "Questions are favored over declarations. Plans, measurements, and competing accounts "
            "are gathered before anyone insists that the whole shape is already visible."
        ),
    ),
    MoonPhaseMeaning(
        key="full",
        name="Full Moon",
        emphasis="clarity and honesty",
        practice=(
            "This is the traditional phase for speaking plainly, comparing accounts, recording a "
            "decision, or saying aloud what has become clear enough to share."
        ),
    ),
    MoonPhaseMeaning(
        key="waning",
        name="Waning Moon",
        emphasis="revision and release",
        practice=(
            "Old conclusions are reviewed without embarrassment. Changing one's mind when the view "
            "changes is treated as maturity, not weakness."
        ),
    ),
)
MOON_PHASE_MEANINGS_BY_KEY = {meaning.key: meaning for meaning in MOON_PHASE_MEANINGS}


def phase_meaning(phase_key: str) -> MoonPhaseMeaning:
    """Return the cultural reading for one of Astralis's four moon phases."""
    try:
        return MOON_PHASE_MEANINGS_BY_KEY[phase_key]
    except KeyError as exc:
        raise ValueError(f"Unknown moon phase: {phase_key}") from exc


def belief_summary_lines() -> tuple[str, ...]:
    return (
        "The moon is not a god in the central Elven lunar tradition. It is a symbol of perspective: distance can reveal a shape that closeness hides.",
        "The high cities of the Moon Peaks were built for broad horizons and open night skies, not because height is believed to make their people holier or superior.",
        "It is respectable to change your mind when new distance, evidence, or experience changes the view. Certainty held past its usefulness is not admired.",
        "Many families keep journals across generations so descendants can see not only what their ancestors believed, but where they revised themselves.",
        "The moon's phases mark customary modes of thought rather than fate: New for privacy and beginnings, Waxing for inquiry and preparation, Full for clarity and honesty, and Waning for revision and release.",
    )


def horizon_lines() -> tuple[str, ...]:
    return (
        "A clear horizon is both practical and philosophical in the Moon Peaks. Weather, roads, distant fires, stars, and the moon can all be read earlier from high ground.",
        "The cultural lesson is not 'we stand above others.' It is 'sometimes you must step far enough back to see what you are standing inside.'",
    )


def journal_lines() -> tuple[str, ...]:
    return (
        "Family journals commonly pass through several generations. They hold observations, decisions, disagreements, letters, corrections, and the reasons a conclusion changed.",
        "A perfectly consistent journal is often less respected than an honest one. The point is to preserve perspective, not to make ancestors look infallible.",
    )


def forest_elf_rivalry_lines() -> tuple[str, ...]:
    return (
        "Forest Elves and the Elves of the Moon Peaks both insist that they are simply Elves. 'Forest Elf' and 'Moon Elf' are useful outsider labels, not identities either culture considers necessary among its own people.",
        "Forest Elves often accuse their highland cousins of watching life so carefully that they forget to live it. Moon Elves answer that rootedness can become narrowness when nobody steps back far enough to see the larger shape.",
        "The disagreement can be sharp and personal, especially over who has the better claim to the word Elf, but it is a cultural rivalry rather than automatic hatred or war.",
    )


async def _show_beliefs(session) -> None:
    await session.send("\r\n--- Elven Lunar Tradition ---\r\n")
    for line in belief_summary_lines():
        await session.send(line + "\r\n")


async def _show_current_phase(session) -> None:
    moment = ASTRALIS_CLOCK.now()
    date = moment.calendar
    meaning = phase_meaning(date.moon_phase)
    await session.send("\r\n--- The Moon as Perspective ---\r\n")
    await session.send(
        f"Astralis is under the {date.moon_phase_name}, day {date.moon_phase_day} of this phase.\r\n"
    )
    await session.send(
        "Among your people this does not predict fate, luck, personality, or divine favor. The phase is a customary prompt for how to approach thought and conversation.\r\n"
    )
    await session.send(f"{meaning.name}: {meaning.emphasis}. {meaning.practice}\r\n")
    await session.send("Use CALENDAR for the astronomical cycle itself.\r\n")


async def _show_lines(session, title: str, lines: tuple[str, ...]) -> None:
    await session.send(f"\r\n--- {title} ---\r\n")
    for line in lines:
        await session.send(line + "\r\n")


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_moon_elf_belief_runtime(player_session_class) -> None:
    """Make the Moon Elf belief system visible in play without inventing a starter arc yet."""
    if getattr(player_session_class, "_moon_elf_belief_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if self.character is None or self.character.race != "moon_elf":
            return
        flags = self.database.list_flags(self.character.id)
        if MOON_ELF_BELIEF_INTRO_FLAG in flags:
            return
        self.database.grant_flag(self.character.id, MOON_ELF_BELIEF_INTRO_FLAG)
        await self.send(
            "\r\nAmong your people, the moon is not a god. It is an old reminder that distance can change understanding, and that a clearer view may require changing your mind.\r\n"
            "The cities of the Moon Peaks prize open horizons for the same reason. Type BELIEFS to review the lunar tradition or MOON to read the current phase through that tradition.\r\n"
        )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "moon_elf":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {
            "beliefs", "belief", "lunar tradition", "moon tradition", "lunar belief",
            "lunar beliefs", "perspective", "moon philosophy", "philosophy",
        }:
            await _show_beliefs(self)
            return
        if normalized in {"moon", "moon meaning", "moon phase meaning", "lunar phase"}:
            await _show_current_phase(self)
            return
        if normalized in {"horizon", "horizons", "high places", "moon peaks", "peaks"}:
            await _show_lines(self, "The High Horizon", horizon_lines())
            return
        if normalized in {"journal", "journals", "family journal", "family journals"}:
            await _show_lines(self, "Generational Journals", journal_lines())
            return
        if normalized in {"elves", "forest elves", "forest elf", "elf rivalry", "elven rivalry"}:
            await _show_lines(self, "The Elven Argument", forest_elf_rivalry_lines())
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {"help", "?"}:
            await self.send(
                "Moon Elf culture: BELIEFS explains the lunar philosophy; MOON gives the current phase's cultural meaning; HORIZON explains the high cities; JOURNALS explains the generational record tradition; ELVES explains the Forest Elf rivalry.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_belief_runtime_installed = True
