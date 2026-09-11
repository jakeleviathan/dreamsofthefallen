from __future__ import annotations

from dataclasses import dataclass

from mud.astralis_time import ASTRALIS_CLOCK


MOON_ELF_BELIEF_INTRO_FLAG = "moon_elf_lunar_philosophy_introduced"
MOON_ELF_RELIGION_HAS_PERSONAL_DEITY = False
MOON_ELF_RELIGION_GRANTS_PRIEST_PATH = False


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
        "The moon is nevertheless sacred to many Moon Elves because it functions as a lens and reminder, not because it is believed to be a person who issues commands or grants favors.",
        "The high cities of the Moon Peaks were built for broad horizons and open night skies, not because height is believed to make their people holier or superior.",
        "It is respectable to change your mind when new distance, evidence, or experience changes the view. Certainty held past its usefulness is not admired.",
        "Many families keep journals across generations so descendants can see not only what their ancestors believed, but where they revised themselves.",
        "The moon's phases mark customary modes of thought rather than fate: New for privacy and beginnings, Waxing for inquiry and preparation, Full for clarity and honesty, and Waning for revision and release.",
    )


def religion_lines() -> tuple[str, ...]:
    return (
        "The central Moon Elf religious tradition has no personal lunar deity at its center. The moon is revered as a sacred lens: a visible reminder that distance, angle, and time can change what a person understands.",
        "Reverence does not require believing that the moon thinks, speaks, judges, chooses favorites, or answers requests. Calling it sacred describes the place it holds in Elven life, not a claim that it is a person in the sky.",
        "Some Moon Elves speak about the moon in deeply reverent language. Others describe the same tradition almost entirely as philosophy. Neither style is considered less authentically Elven.",
        "The tradition is meant to invite reflection rather than enforce obedience. A custom can be declined, a ritual can be skipped, and a conclusion can be revised without treating disagreement as spiritual failure.",
        "This cultural tradition does not itself create a Priest-class patron path. Priests still choose from the game's separately authored divine patrons; lunar reverence is part of Moon Elf culture rather than a fourth god mechanically added to the Priest roster.",
    )


def shrine_lines() -> tuple[str, ...]:
    return (
        "Moon Elf shrines are places for perspective rather than places to bargain for miracles. Many are open-air alcoves, roof terraces, quiet rooms, or framed overlooks positioned to show the moon, a horizon, or a reflected view.",
        "A typical shrine may contain a bench, a writing surface, a mirror or viewing frame, and somewhere to leave a private note for yourself. It does not need an idol, a throne, or an altar piled with offerings.",
        "People visit to sit quietly, compare what they thought before with what they think now, write, speak with someone they trust, or simply look outward until a problem feels less crowded by its own immediacy.",
        "Nothing at a shrine promises an answer. The point is to create enough distance that a person may notice an answer, a better question, or the fact that no answer is ready yet.",
    )


def prayer_lines() -> tuple[str, ...]:
    return (
        "There is no single required Moon Elf form of prayer. Some people address the moon poetically as though speaking to an old companion; others would insist they are speaking in front of the moon, not to it.",
        "Silence, journaling, conversation, and deliberate observation can all fill the same role. The practice is about becoming able to see differently, not persuading a supernatural listener to intervene.",
        "Because the tradition is invitational rather than commanding, reverent language and philosophical language comfortably coexist. The culture cares more about whether reflection changes understanding than about which vocabulary a person uses.",
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
    """Make the Moon Elf belief and religious tradition visible in play."""
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
            "\r\nAmong your people, the moon is not a god. It is revered as a sacred lens: an old reminder that distance can change understanding, and that a clearer view may require changing your mind.\r\n"
            "Some Elves speak of that tradition reverently and others philosophically. Both belong. Type BELIEFS for the larger tradition, RELIGION for its sacred meaning, or MOON to read the current phase through it.\r\n"
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
        if normalized in {
            "religion", "faith", "moon faith", "lunar faith", "lunar religion",
            "moon religion", "deity", "moon deity", "god", "moon god",
        }:
            await _show_lines(self, "Sacred Lunar Tradition", religion_lines())
            return
        if normalized in {"shrine", "shrines", "moon shrine", "lunar shrine", "reflection shrine"}:
            await _show_lines(self, "Shrines of Perspective", shrine_lines())
            return
        if normalized in {"prayer", "pray", "praying", "moon prayer", "lunar prayer"}:
            await _show_lines(self, "Prayer and Reflection", prayer_lines())
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
                "Moon Elf culture: BELIEFS explains the lunar philosophy; RELIGION explains why the moon is sacred without being a god; SHRINE describes places of reflection; PRAYER explains reverent and philosophical practice; MOON gives the current phase's cultural meaning; HORIZON explains the high cities; JOURNALS explains the generational record tradition; ELVES explains the Forest Elf rivalry.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_belief_runtime_installed = True
