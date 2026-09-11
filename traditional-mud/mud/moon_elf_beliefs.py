from __future__ import annotations

from dataclasses import dataclass, replace

import mud.character_options as character_options
from mud.astralis_time import ASTRALIS_CLOCK
from mud.mechanics import AbilityDefinition, PRIEST_DEITIES_BY_KEY, PRIEST_DEITY_ABILITIES


MOON_ELF_BELIEF_INTRO_FLAG = "moon_elf_lunar_philosophy_introduced"
MOON_ELF_WITNESS_INTRO_FLAG = "moon_elf_witness_introduced"
MOON_ELF_RELIGION_HAS_PERSONAL_DEITY = False
MOON_ELF_RELIGION_GRANTS_PRIEST_PATH = True

# The existing database column is called deity_key because the original Priest
# class was entirely patron-based. Witness is deliberately stored in that path
# field for compatibility, but it is not added to the game's deity roster.
MOON_ELF_WITNESS_PATH_KEY = "moon_elf_witness"


@dataclass(frozen=True, slots=True)
class MoonPhaseMeaning:
    key: str
    name: str
    emphasis: str
    practice: str


@dataclass(frozen=True, slots=True)
class WitnessPathDefinition:
    key: str
    name: str
    domain: str
    description: str
    starter_ability: AbilityDefinition
    progression_identity: str


# Witness magic uses the executable healing/protection effects already present
# in the Priest engine, but the authored names and explanations belong to this
# non-patron tradition. Exact balance remains shared with the underlying spells.
WITNESS_ABILITIES: tuple[AbilityDefinition, ...] = (
    AbilityDefinition(
        key="restoring_light",
        name="Clearview Mending",
        unlock_level=1,
        description=(
            "A Witness holds injury and the body's intact pattern in the same awareness, "
            "using that clearer view to guide restorative magic."
        ),
        category="healing",
        design_status="approved_witness_identity_initial_tuning",
    ),
    AbilityDefinition(
        key="guardian_ward",
        name="Second View Ward",
        unlock_level=2,
        description=(
            "A Witness shapes a protective ward by holding immediate danger and the wider field "
            "around it in awareness at the same time."
        ),
        category="protection",
        design_status="approved_witness_identity_initial_tuning",
    ),
)

MOON_ELF_WITNESS_PATH = WitnessPathDefinition(
    key=MOON_ELF_WITNESS_PATH_KEY,
    name="No patron (Witness tradition)",
    domain="clarity",
    description=(
        "The Moon Elf Priest tradition of Witnesses: specialists in perspective, mediation, "
        "healing, and protection who do not claim a lunar god grants their power."
    ),
    starter_ability=WITNESS_ABILITIES[0],
    progression_identity=(
        "Develops healing, protection, and clarity-oriented Priest magic through the Witness "
        "discipline rather than through service to a personal patron deity."
    ),
)


def _register_witness_path() -> None:
    """Register Witness as a Priest path without adding a fourth deity."""
    PRIEST_DEITY_ABILITIES[MOON_ELF_WITNESS_PATH_KEY] = WITNESS_ABILITIES
    # Session summaries historically look paths up in this mapping. Supplying a
    # display record here keeps them compatible while PRIEST_DEITIES itself stays
    # untouched, so Witness can never appear in the ordinary deity-selection list.
    PRIEST_DEITIES_BY_KEY[MOON_ELF_WITNESS_PATH_KEY] = MOON_ELF_WITNESS_PATH


def _patch_moon_elf_witness_lore() -> None:
    current = character_options.RACES_BY_KEY.get("moon_elf")
    if current is None:
        return
    extra = (
        "Priests formed within the central lunar tradition are called Witnesses rather than servants of the moon.",
        "Witnesses specialize in clarity: they mediate disputes, accompany the dying, preserve conflicting histories, and practice healing and protective magic through disciplined perspective.",
        "Patron-bound Priests often describe divine magic as power granted by a god; Witnesses usually describe their own magic as power accessed through clarity. Astralis does not provide a provable answer that makes either explanation unquestionably correct.",
    )
    lore = current.lore + tuple(line for line in extra if line not in current.lore)
    replacement = replace(current, lore=lore)
    character_options.RACES = tuple(
        replacement if race.key == "moon_elf" else race for race in character_options.RACES
    )
    character_options.RACES_BY_KEY["moon_elf"] = replacement


_register_witness_path()
_patch_moon_elf_witness_lore()


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
        "Its Priest-class practitioners are called Witnesses. A Witness does not serve a moon god or claim to speak for one; the vocation is built around clarity, care, mediation, and the disciplined search for a wider view.",
    )


def shrine_lines() -> tuple[str, ...]:
    return (
        "Moon Elf shrines are places for perspective rather than places to bargain for miracles. Many are open-air alcoves, roof terraces, quiet rooms, or framed overlooks positioned to show the moon, a horizon, or a reflected view.",
        "A typical shrine may contain a bench, a writing surface, a mirror or viewing frame, and somewhere to leave a private note for yourself. It does not need an idol, a throne, or an altar piled with offerings.",
        "People visit to sit quietly, compare what they thought before with what they think now, write, speak with someone they trust, or simply look outward until a problem feels less crowded by its own immediacy.",
        "Witnesses often tend such places or make themselves available there, but they do not own the shrine's meaning and are not required intermediaries between ordinary people and the sacred.",
        "Nothing at a shrine promises an answer. The point is to create enough distance that a person may notice an answer, a better question, or the fact that no answer is ready yet.",
    )


def prayer_lines() -> tuple[str, ...]:
    return (
        "There is no single required Moon Elf form of prayer. Some people address the moon poetically as though speaking to an old companion; others would insist they are speaking in front of the moon, not to it.",
        "Silence, journaling, conversation, and deliberate observation can all fill the same role. The practice is about becoming able to see differently, not persuading a supernatural listener to intervene.",
        "Witnesses may guide reflection when asked, but a Witness is not a gatekeeper who makes private thought valid. The tradition remains invitational rather than commanding.",
        "Reverent language and philosophical language comfortably coexist. The culture cares more about whether reflection changes understanding than about which vocabulary a person uses.",
    )


def witness_lines() -> tuple[str, ...]:
    return (
        "Moon Elf Priests of the central lunar tradition are called Witnesses. The title is deliberate: they are trained to notice, remember, compare, and remain present rather than to announce what a god wants.",
        "A Witness is not a servant or mouthpiece of the moon. The moon remains a sacred lens, not a person. Witnesses cultivate the ability to hold more than one angle of a problem in mind without rushing to collapse them into a single convenient story.",
        "In ordinary society, Witnesses often mediate disputes by helping each side state what the other side actually sees. They can advise the Horizon Council, but they hold no automatic government office and have no authority to overrule the civic process.",
        "They also sit with the dying and the bereaved. Their purpose is not to force a lesson onto death, but to be present, preserve what someone wishes remembered, and make room for uncertainty when certainty would be dishonest.",
        "Witnesses are frequently asked to preserve conflicting histories. When two sincere accounts disagree, the tradition prefers an honest record of both perspectives over a polished false certainty.",
    )


def witness_magic_lines() -> tuple[str, ...]:
    return (
        "Witness magic is primarily healing, protection, and clarity-oriented Priest magic. Its practitioners train perspective as a magical discipline rather than treating insight as merely a metaphor.",
        "In healing, a Witness learns not to see only the wound: the injury is held alongside the larger living pattern that remains intact. Clearview Mending is the first practical expression of that discipline.",
        "In protection, the Witness learns to hold immediate danger and the wider field around it at once. Second View Ward grows from the same habit: danger is real, but it is rarely the only thing present.",
        "Priests of personal deities commonly say their magic is granted by their patron. Witnesses usually say power is accessed when disciplined clarity makes the right relationship visible. Neither explanation has been proven in a way that settles the argument for everyone on Astralis.",
        "That uncertainty is intentional. A Witness can respect a patron-bound Priest's experience without pretending that either tradition possesses a laboratory proof of where sacred magic ultimately comes from.",
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
    """Make the Moon Elf belief, religion, and Witness Priest path visible in play."""
    if getattr(player_session_class, "_moon_elf_belief_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_choose_creation_option = player_session_class.choose_creation_option
    previous_choose_priest_deity = player_session_class.choose_priest_deity

    async def choose_creation_option(self, label, options):
        selected = await previous_choose_creation_option(self, label, options)
        if label.strip().lower() == "race":
            self._moon_elf_creation_race_key = getattr(selected, "key", None)
        return selected

    async def choose_priest_deity(self):
        if getattr(self, "_moon_elf_creation_race_key", None) == "moon_elf":
            await self.send(
                "\r\n--- Moon Elf Priest Tradition: Witness ---\r\n"
                "Among the Elves of the Moon Peaks, a Priest formed in the central lunar tradition is a Witness, not the servant of a moon god. The moon is sacred, but it is not believed to be a person who grants commands or favors.\r\n"
                "Witnesses cultivate clarity as a magical discipline. They heal, protect, mediate disputes, accompany the dying, and preserve difficult or conflicting accounts without pretending uncertainty is failure.\r\n"
                f"Level 1: {WITNESS_ABILITIES[0].name} - {WITNESS_ABILITIES[0].description}\r\n"
                f"Level 2: {WITNESS_ABILITIES[1].name} - {WITNESS_ABILITIES[1].description}\r\n"
                "No patron deity is selected for this path.\r\n"
            )
            return MOON_ELF_WITNESS_PATH
        return await previous_choose_priest_deity(self)

    async def enter_character(self) -> None:
        # Older development Moon Elf Priests who never chose a path are safely
        # brought into the Witness tradition. Existing explicit deity choices are
        # respected rather than silently overwritten.
        if (
            self.character is not None
            and self.character.race == "moon_elf"
            and self.character.character_class == "priest"
            and not self.character.deity_key
        ):
            self.database.set_character_deity(self.character.id, MOON_ELF_WITNESS_PATH_KEY)
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed

        await previous_enter_character(self)
        if self.character is None or self.character.race != "moon_elf":
            return

        flags = self.database.list_flags(self.character.id)
        if MOON_ELF_BELIEF_INTRO_FLAG not in flags:
            self.database.grant_flag(self.character.id, MOON_ELF_BELIEF_INTRO_FLAG)
            await self.send(
                "\r\nAmong your people, the moon is not a god. It is revered as a sacred lens: an old reminder that distance can change understanding, and that a clearer view may require changing your mind.\r\n"
                "Some Elves speak of that tradition reverently and others philosophically. Both belong. Type BELIEFS for the larger tradition, RELIGION for its sacred meaning, or MOON to read the current phase through it.\r\n"
            )

        if (
            self.character.character_class == "priest"
            and self.character.deity_key == MOON_ELF_WITNESS_PATH_KEY
            and MOON_ELF_WITNESS_INTRO_FLAG not in flags
        ):
            self.database.grant_flag(self.character.id, MOON_ELF_WITNESS_INTRO_FLAG)
            await self.send(
                "\r\nYour Priest tradition names you a Witness. You do not claim to channel the will of a moon god. Your discipline is clarity: to see the wound without forgetting the whole, the danger without forgetting the wider field, and one sincere account without erasing another.\r\n"
                "Patron-bound Priests may call sacred power granted. Witnesses usually call it accessed. Neither explanation is treated as conclusively proven. Type WITNESS or WITNESS MAGIC to review the tradition.\r\n"
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
        if normalized in {
            "witness", "witnesses", "moon priest", "moon elf priest", "moon priests",
            "priest tradition", "witness tradition", "witness role",
        }:
            await _show_lines(self, "The Witnesses", witness_lines())
            if (
                self.character.character_class == "priest"
                and self.character.deity_key == MOON_ELF_WITNESS_PATH_KEY
            ):
                await self.send("You belong to this tradition.\r\n")
            return
        if normalized in {
            "witness magic", "clarity magic", "priest magic", "accessed magic",
            "granted magic", "clearview mending", "second view ward",
        }:
            await _show_lines(self, "Witness Magic", witness_magic_lines())
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
                "Moon Elf culture: BELIEFS explains the lunar philosophy; RELIGION explains why the moon is sacred without being a god; WITNESS explains the Moon Elf Priest vocation; WITNESS MAGIC explains its healing/protection tradition and the unresolved granted-vs-accessed question; SHRINE describes places of reflection; PRAYER explains reverent and philosophical practice; MOON gives the current phase's cultural meaning; HORIZON explains the high cities; JOURNALS explains the generational record tradition; ELVES explains the Forest Elf rivalry.\r\n"
            )

    player_session_class.choose_creation_option = choose_creation_option
    player_session_class.choose_priest_deity = choose_priest_deity
    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_belief_runtime_installed = True
