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
        # Keep the original persistence key so characters who already completed
        # the older opt-in version are never made to repeat the lesson.
        return f"starter_class_moment_{self.race_key}_{self.class_key}"


@dataclass(frozen=True, slots=True)
class OpeningTrigger:
    quest_key: str
    trigger_step: str
    lead_in: str
    closing: str


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


# Each class lesson is attached to a real transition that already happens in the
# race's authored starter experience. There is no CLASS MOMENT command anymore.
# The beat appears only after the normal opening action genuinely advances its
# quest, so typing a phrase in the wrong room cannot summon a tutorial scene.
RACE_OPENING_TRIGGERS: dict[str, OpeningTrigger] = {
    "human": OpeningTrigger(
        "human_blackwall_readiness",
        "report_muster",
        "As Sergeant Mara finishes the muster check, she keeps you in the yard for one more minute. 'Blackwall does not care what you call your discipline. It cares whether you can use it without making the emergency worse.'",
        "Mara gives a short nod and turns you back toward the signal board. The readiness drill continues.",
    ),
    "forest_elf": OpeningTrigger(
        "forest_elf_morning_already_underway",
        "talk_neris",
        "Before Neris sends you off with the keeper parcel, the morning work pauses for one small piece of class practice. Nobody forms a ceremony around it; one useful correction is treated like any other part of learning the town.",
        "The practice ends without applause. Neris presses the parcel into your hands, and the ordinary morning resumes around you.",
    ),
    "moon_elf": OpeningTrigger(
        "moon_elf_third_chair",
        "meet_ilyra",
        "Before Ilyra asks you to take the Third Chair, she studies the way you carry your chosen discipline. 'Perspective is not only where you stand. It is also knowing what your own training makes easy for you to notice.'",
        "Ilyra leaves the lesson there and gestures toward the empty chair. The civic disagreement is waiting.",
    ),
    "dwarf": OpeningTrigger(
        "dwarf_first_work_order",
        "registry_stamp",
        "After Helga stamps the first work order, she points you toward a marked practice square beside the registry counter. 'Every serious trade carried through this city gets checked before somebody else has to trust it. Yours is no exception.'",
        "The check is brief, documented, and apparently sufficient. Helga sends you on toward the union counterseal.",
    ),
    "goblin": OpeningTrigger(
        "goblin_rattlefen_three_bells",
        "inspect_wreck",
        "While you sort the fresh wreck, an older salvage hand notices how your class training changes the way you approach the pile. 'Good. Show me one thing that works. Pretty can wait until useful survives.'",
        "The salvage hand loses interest the instant the lesson proves practical. You still have one claim tag and a wreck full of choices.",
    ),
    "troll": OpeningTrigger(
        "troll_night_is_not_over",
        "talk_raska",
        "Raska stops you before you reach for the spear. 'One clean habit first. Whatever your training is, show me the part you can still do tired, cold, and scared. No showing off.'",
        "Raska grunts once. 'Good enough. Now take the spear.' The broken palisade still needs you.",
    ),
    "undead": OpeningTrigger(
        "undead_no_voice_above_you",
        "talk_reclaimer",
        "Reclaimer Sevra studies you after explaining the severance ahead. 'A master may have chosen what your body once did. I will not. Before we cut away the last command thread, show me one discipline you choose to keep for yourself.'",
        "Sevra accepts the answer without asking who taught it to you in life. What matters here is that the choice belongs to you now.",
    ),
    "sporekin": OpeningTrigger(
        "sporekin_voice_of_your_own",
        "talk_nemm",
        "Nemm lets the Chorus settle quiet between you. 'A thousand remembered hands can show you how a technique looked. They still cannot decide how your hand should use it. Show me one thing that is yours to judge.'",
        "Nemm inclines their cap. The Chorus keeps the memory of the exercise, but the decision inside it remains unmistakably yours.",
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
    if character.deity_key == "moon_elf_witness":
        return "For you, that center is the Witness tradition: sacred clarity without a personal lunar patron."
    if path is None:
        return "Your Priest path has not been named yet."
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
    return f"Your training already gives you access to {first.name}. Type ABILITIES whenever you need to review what you can use."


def _quest_state(session, quest_key: str) -> dict | None:
    character = getattr(session, "character", None)
    database = getattr(session, "database", None)
    if character is None or database is None or not hasattr(database, "get_quest"):
        return None
    row = database.get_quest(character.id, quest_key)
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except (TypeError, ValueError):
        return None


def _trigger_ready(session) -> tuple[OpeningTrigger, StarterClassMoment] | None:
    character = getattr(session, "character", None)
    if character is None:
        return None
    moment = starter_class_moment(character.race or "", character.character_class or "")
    trigger = RACE_OPENING_TRIGGERS.get(character.race or "")
    if moment is None or trigger is None:
        return None
    if moment.flag_key in session.database.list_flags(character.id):
        return None
    quest = _quest_state(session, trigger.quest_key)
    if quest is None or quest.get("status") != "active":
        return None
    if quest.get("current_step") != trigger.trigger_step:
        return None
    return trigger, moment


async def _show_integrated_class_beat(session, trigger: OpeningTrigger, moment: StarterClassMoment) -> None:
    character = session.character
    if character is None:
        return
    if moment.flag_key in session.database.list_flags(character.id):
        return

    race = RACES_BY_KEY.get(moment.race_key)
    character_class = CLASSES_BY_KEY.get(moment.class_key)
    race_name = race.name if race else moment.race_key
    class_name = character_class.name if character_class else moment.class_key

    await session.send(f"\r\n--- {moment.title} ---\r\n")
    await session.send(trigger.lead_in + "\r\n\r\n")
    await session.send(moment.setting + "\r\n\r\n")
    await session.send(f"As a {race_name} {class_name}, you practice one small piece of the discipline:\r\n")
    await session.send(moment.practice_text + "\r\n")
    priest_line = _priest_path_line(session)
    if priest_line:
        await session.send(priest_line + "\r\n")
    ability_line = _starter_ability_line(session)
    if ability_line:
        await session.send(ability_line + "\r\n")
    await session.send("\r\n" + moment.lesson + "\r\n")
    await session.send(trigger.closing + "\r\n")
    session.database.grant_flag(character.id, moment.flag_key)


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


def install_starter_class_moment_runtime(player_session_class) -> None:
    """Weave all 8x5 class acknowledgements into existing racial openings.

    Nothing is launched by a meta tutorial command. A class beat is emitted once,
    immediately after a real authored starter-quest action advances the opening.
    """
    if getattr(player_session_class, "_starter_class_moment_runtime_installed", False):
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

        ready = _trigger_ready(self)
        before_step = None
        if ready is not None:
            trigger, _moment = ready
            before = _quest_state(self, trigger.quest_key)
            before_step = None if before is None else before.get("current_step")

        await _delegate_prompt(self, previous_playing_prompt, command)

        if ready is None:
            return
        trigger, moment = ready
        after = _quest_state(self, trigger.quest_key)
        if after is None:
            return
        # Only a real state transition inside the underlying racial opener earns
        # the beat. Wrong-room or invalid commands leave the step unchanged.
        if before_step == trigger.trigger_step and after.get("current_step") != before_step:
            await _show_integrated_class_beat(self, trigger, moment)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._starter_class_moment_runtime_installed = True
