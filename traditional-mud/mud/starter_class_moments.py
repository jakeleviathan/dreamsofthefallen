from __future__ import annotations

from dataclasses import dataclass

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.mechanics import PRIEST_DEITIES_BY_KEY, class_abilities_for_level


@dataclass(frozen=True, slots=True)
class StarterClassMoment:
    race_key: str
    class_key: str
    title: str
    setting: str
    practice_text: str
    lesson: str

    @property
    def flag_key(self) -> str:
        return f"starter_class_moment_{self.race_key}_{self.class_key}"


RACE_SETTINGS: dict[str, tuple[str, str]] = {
    "human": (
        "Demon-Born Discipline",
        "The black walls, cathedral bells, and training yards of the Human kingdom make even ordinary instruction feel a little severe. Here, your class is treated as a practical craft rather than a destiny.",
    ),
    "forest_elf": (
        "A Skill Among Living Things",
        "The Forest Elf opening teaches that a useful skill should fit into the life already around it. The Circle does not ask your class to replace observation; it asks what your training notices that someone else might miss.",
    ),
    "moon_elf": (
        "One More Angle",
        "High Horizon treats class training as another way of seeing. Your discipline is not declared the correct lens; it is one more angle worth learning to use deliberately.",
    ),
    "dwarf": (
        "A Trade You Carry",
        "In the Dwarven mountain city, competence is expected to survive inspection. Your class is approached like any serious trade: know what the tool does, know what it costs, and know when not to use it.",
    ),
    "goblin": (
        "Useful Beats Pretty",
        "Rattlefen has little patience for impressive technique that does not solve a problem. Your class training gets judged the Goblin way: if it works, know why; if it breaks, learn what part is still worth keeping.",
    ),
    "troll": (
        "Practice Before Pride",
        "Troll instruction is blunt and supervised. Young Trolls are not thrown into danger to prove themselves; they practice one dependable habit at a time until the wilderness stops being a performance and becomes work.",
    ),
    "undead": (
        "What You Choose to Keep",
        "In the Necropolis, your class is not treated as an order left over from a former master or former life. It is a discipline you continue because you choose to continue it now.",
    ),
    "sporekin": (
        "One Voice in the Chorus",
        "The Chorus can share impressions, warnings, and memory, but it cannot practice your discipline for you. This is one of the first places a young Sporekin learns the difference between knowledge held by many and judgment exercised by one.",
    ),
}

CLASS_PRACTICE: dict[str, tuple[str, str]] = {
    "brute": (
        "You settle your weight, choose where an enemy would have to look to get past you, and let your voice carry from the chest instead of the throat. The exercise is small, but the principle behind Taunt is already there: threat control is placement, timing, and commitment, not merely shouting.",
        "Brutes protect a group by deliberately becoming the problem an enemy cannot ignore.",
    ),
    "wizard": (
        "You shape a bead of harmless coldfire no larger than a coin, hold it steady, then dismiss it without letting the spell spill into the surroundings. Coldfire Burst will be much louder in a fight; control begins with proving you can make it quiet.",
        "Wizards are not defined only by how much power they can release, but by whether they can place that power exactly where it belongs.",
    ),
    "druid": (
        "You find a small living rhythm nearby—your own pulse if nothing else is suitable—and match your breathing to it until a thread of restorative magic answers. Minor Heal begins with attention before it becomes healing.",
        "Druids support life by noticing what is strained, what is still healthy, and how little intervention may be enough.",
    ),
    "priest": (
        "You center yourself around the source of your Priest discipline and let the first shape of its magic become familiar without spending power. Whether you call that source a patron, a sacred relationship, or disciplined clarity, the lesson is the same: know what you are asking your magic to do before you ask it to do more.",
        "Priests begin as caretakers and protectors before their later path becomes powerful enough to define whole battles.",
    ),
    "necromancer": (
        "You feel for the boundary between vitality and absence, draw the faintest thread of that sensation toward yourself, then release it before any harm is done. Minor Life Tap is built from the same dangerous relationship: take, restore, stop before appetite becomes carelessness.",
        "Necromancers work close to death without being excused from control, consequence, or judgment.",
    ),
}


def starter_class_moment(race_key: str, class_key: str) -> StarterClassMoment | None:
    race_setting = RACE_SETTINGS.get(race_key)
    class_practice = CLASS_PRACTICE.get(class_key)
    if race_setting is None or class_practice is None:
        return None
    title, setting = race_setting
    practice_text, lesson = class_practice
    return StarterClassMoment(
        race_key=race_key,
        class_key=class_key,
        title=title,
        setting=setting,
        practice_text=practice_text,
        lesson=lesson,
    )


def all_starter_class_moments() -> tuple[StarterClassMoment, ...]:
    moments: list[StarterClassMoment] = []
    for race_key in RACE_SETTINGS:
        for class_key in CLASS_PRACTICE:
            moment = starter_class_moment(race_key, class_key)
            if moment is not None:
                moments.append(moment)
    return tuple(moments)


def _priest_path_line(session) -> str:
    character = session.character
    if character is None or character.character_class != "priest":
        return ""
    path = PRIEST_DEITIES_BY_KEY.get(character.deity_key or "")
    if path is None:
        return "Your Priest path has not been named yet."
    if character.deity_key == "moon_elf_witness":
        return "For you, that center is the Witness tradition: sacred clarity without a personal lunar patron."
    return f"For you, that center is {path.name}, whose path is associated with {path.domain}."


def _starter_ability_line(session) -> str:
    character = session.character
    if character is None:
        return ""
    abilities = class_abilities_for_level(
        character.character_class or "", character.level, character.deity_key
    )
    if not abilities:
        return ""
    first = abilities[0]
    return f"Your first executable class ability is {first.name}. Type ABILITIES for the full unlocked list."


async def _show_moment(session, *, complete: bool) -> None:
    character = session.character
    if character is None:
        return
    moment = starter_class_moment(character.race or "", character.character_class or "")
    if moment is None:
        await session.send("No starter class moment is authored for this character.\r\n")
        return

    race = RACES_BY_KEY.get(moment.race_key)
    character_class = CLASSES_BY_KEY.get(moment.class_key)
    race_name = race.name if race else moment.race_key
    class_name = character_class.name if character_class else moment.class_key
    already_done = moment.flag_key in session.database.list_flags(character.id)

    await session.send(f"\r\n--- {moment.title}: {race_name} {class_name} ---\r\n")
    await session.send(moment.setting + "\r\n\r\n")
    await session.send(moment.practice_text + "\r\n")
    priest_line = _priest_path_line(session)
    if priest_line:
        await session.send(priest_line + "\r\n")
    ability_line = _starter_ability_line(session)
    if ability_line:
        await session.send(ability_line + "\r\n")
    await session.send("\r\n" + moment.lesson + "\r\n")

    if complete and not already_done:
        session.database.grant_flag(character.id, moment.flag_key)
        await session.send("Class moment complete. This does not block or replace your racial opening quest.\r\n")
    elif already_done:
        await session.send("You have already completed this small class-specific opening moment.\r\n")


def install_starter_class_moment_runtime(player_session_class) -> None:
    """Give every one of the 8x5 race/class combinations a small opening beat.

    The moment is deliberately self-contained: no race needs forty duplicate
    rooms, enemies, or quest branches merely to acknowledge class identity.
    """
    if getattr(player_session_class, "_starter_class_moment_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        character = self.character
        if character is None:
            return
        moment = starter_class_moment(character.race or "", character.character_class or "")
        if moment is None:
            return
        if moment.flag_key not in self.database.list_flags(character.id):
            await self.send(
                "\r\nYour racial opening includes one brief class-specific practice beat. "
                "Type CLASS MOMENT when you want to play it; it is optional and never blocks your quest progress.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized in {"class moment", "class practice", "practice class", "starter class"}:
            await _show_moment(self, complete=True)
            return

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

        if normalized in {"help", "?"}:
            await self.send(
                "Starter identity: CLASS MOMENT plays the optional class-specific beat woven into your race's opening.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._starter_class_moment_runtime_installed = True
