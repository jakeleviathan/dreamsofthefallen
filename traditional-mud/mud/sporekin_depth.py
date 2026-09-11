from __future__ import annotations

from dataclasses import replace

import mud.character_options as character_options
import mud.combat as combat
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition
from mud.quests import QuestDefinition
from mud.world import NpcDefinition, SPOREKIN_MEMORY_PATH_ROOM_KEY


SPOREKIN_DEPTH_QUEST_KEY = "sporekin_voice_of_your_own"
SPOREKIN_DEPTH_COMPLETE_FLAG = "sporekin_voice_of_your_own_complete"
SPOREKIN_INDIVIDUAL_VOICE_FLAG = "sporekin_spoke_as_individual"
SPOREKIN_PRACTICE_HUSK_FLAG = "sporekin_practice_husk_defeated"
SPOREKIN_GUIDE_KEY = "sporekin_guide_nemm_quiet_thread"
SPOREKIN_PRACTICE_HUSK_KEY = "sporekin_practice_husk"


SPOREKIN_DEPTH_QUEST = QuestDefinition(
    key=SPOREKIN_DEPTH_QUEST_KEY,
    name="A Voice of Your Own",
    style="structured",
    description=(
        "Beyond the restored memory path, Guide Nemm teaches a newly surface-bound Sporekin something the Chorus cannot teach by itself: "
        "shared memory does not replace individual judgment, and guidance is not the same thing as control."
    ),
    objective_steps=(
        ("talk_nemm", "Follow the revealed path north and TALK NEMM."),
        ("speak_alone", "Practice choosing a thought as your own by typing SPEAK ALONE."),
        ("practice_husk", "ATTACK PRACTICE HUSK and defeat the harmless training growth."),
        ("return_nemm", "TALK NEMM again after the practice bout."),
        ("complete", "You learned how a Sporekin can belong to the Chorus without surrendering a private point of view."),
    ),
)


GUIDE_NEMM = NpcDefinition(
    key=SPOREKIN_GUIDE_KEY,
    name="Guide Nemm of the Quiet Thread",
    short_description=(
        "a broad-capped Sporekin guide standing deliberately apart from the nearest mycelial cluster, "
        "speaking aloud even though the Chorus could carry part of the thought"
    ),
    room_key=SPOREKIN_MEMORY_PATH_ROOM_KEY,
    role="Sporekin mentor in individuality, surface guidance, and first safe combat practice",
    dialogue=(
        "Nemm touches two fingers to the pale threads underfoot. 'The Chorus remembers with us. It does not decide for us.'",
        "'You will hear many impressions below the words of the surface peoples. Do not mistake hearing more for knowing better.'",
        "'A guide walks beside. A master pulls from ahead. We try very hard not to confuse the two.'",
    ),
)


PRACTICE_HUSK = EnemyDefinition(
    key=SPOREKIN_PRACTICE_HUSK_KEY,
    name="Practice Husk",
    aliases=("husk", "practice husk", "training husk", "fungal husk"),
    description=(
        "a waist-high bundle of dead shelf-fungus, reed fiber, and soft rootwood grown around a weighted training frame"
    ),
    max_hp=14,
    armor_class=0,
    auto_attack_damage=0,
    auto_attack_interval=999.0,
    xp_reward=0,
    retaliates=False,
    tutorial=True,
)


SPOREKIN_CULTURE_LINES: tuple[str, ...] = (
    "The Chorus is a shared consciousness, but not a single mind wearing many bodies. Sporekin retain names, preferences, private attention, disagreement, and responsibility for their own choices.",
    "What travels most easily through the Chorus is impression: urgency, direction, remembered sensation, emotional weight, and patterns learned by many. Precise language and private reasoning still belong strongly to individual minds.",
    "A Sporekin can deliberately quiet their attention to the Chorus. Surface travelers practice this often, because listening to another people requires leaving room for thoughts that did not originate in the network.",
    "Experiences brought back to the underways enrich collective memory, but they do not become a compulsory opinion. Two Sporekin can share the same remembered event and still disagree about what it meant.",
    "Sporekin call themselves guides because their culture prizes accompaniment, translation, patience, and long memory. The title is an aspiration, not proof that they are wiser than everyone they meet.",
)

SPOREKIN_SELFHOOD_LINES: tuple[str, ...] = (
    "Individual identity is not considered a defect in the Chorus. A name marks a continuing point of experience: the place from which one particular life has seen the world.",
    "Young Sporekin are raised communally from spore nurseries and tend to speak of grove-of-origin, teachers, and close growth-companions more often than parents in the humanoid sense.",
    "Privacy is possible. A thought can be held inward, and forcing another mind open is considered a profound violation rather than an impressive use of the shared consciousness.",
    "The cultural ideal is neither total independence nor total merger. A mature Sporekin should be able to say both 'we remember' and 'I choose' without treating either statement as a contradiction.",
)

SPOREKIN_GUIDANCE_LINES: tuple[str, ...] = (
    "Good guidance leaves the other person more capable of choosing after you are gone. Advice that creates dependence is treated with suspicion.",
    "Sporekin guides are taught to distinguish warning from command. 'There is danger east' may be shared urgently; 'therefore you must go west' belongs to the listener's judgment whenever circumstances allow.",
    "This is why surface guides often speak aloud even when other Sporekin are nearby. Separate words slow thought down enough for disagreement, consent, and misunderstanding to become visible.",
)


def _patch_sporekin_lore() -> None:
    current = character_options.RACES_BY_KEY.get("sporekin")
    if current is None:
        return
    extra = (
        "The shared consciousness carries impressions, memory, urgency, and emotional weight more readily than exact private thoughts; individual Sporekin retain real privacy and personal judgment.",
        "A mature Sporekin is expected to balance 'we remember' with 'I choose.' The Chorus informs a person without owning that person's decisions.",
        "Young Sporekin are raised communally from spore nurseries and commonly identify a grove-of-origin rather than a conventional humanoid family lineage.",
        "Their ideal of guidance is accompaniment rather than control: useful advice should leave another person more capable of choosing for themselves.",
    )
    lore = current.lore + tuple(line for line in extra if line not in current.lore)
    replacement = replace(current, lore=lore)
    character_options.RACES = tuple(
        replacement if race.key == "sporekin" else race for race in character_options.RACES
    )
    character_options.RACES_BY_KEY["sporekin"] = replacement


def _patch_memory_path() -> None:
    original = legacy_world.ROOMS_BY_KEY.get(SPOREKIN_MEMORY_PATH_ROOM_KEY)
    if original is None:
        return
    description = original.description
    addition = (
        " A sheltered training shelf has been cleared beside the path, where a weighted Practice Husk stands among old root marks. "
        "Guide Nemm of the Quiet Thread waits nearby, conspicuously speaking aloud rather than letting every thought disappear into the Chorus."
    )
    if "Practice Husk" not in description:
        description += addition
    npc_keys = tuple(dict.fromkeys((*original.npc_keys, SPOREKIN_GUIDE_KEY)))
    enemy_keys = tuple(dict.fromkeys((*original.enemy_keys, SPOREKIN_PRACTICE_HUSK_KEY)))
    tags = tuple(dict.fromkeys((*original.tags, "sporekin_mentor", "safe_training", "selfhood")))
    replacement = replace(
        original,
        description=description,
        npc_keys=npc_keys,
        enemy_keys=enemy_keys,
        tags=tags,
    )
    legacy_world.ROOMS = tuple(
        replacement if room.key == SPOREKIN_MEMORY_PATH_ROOM_KEY else room
        for room in legacy_world.ROOMS
    )
    legacy_world.ROOMS_BY_KEY[SPOREKIN_MEMORY_PATH_ROOM_KEY] = replacement


def install_sporekin_depth_content(world_service=None) -> None:
    """Add the mentor/culture/combat layer after the existing Forgotten Pulse."""
    if SPOREKIN_DEPTH_QUEST_KEY not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (SPOREKIN_DEPTH_QUEST,)
    quests.QUESTS_BY_KEY[SPOREKIN_DEPTH_QUEST_KEY] = SPOREKIN_DEPTH_QUEST

    if SPOREKIN_GUIDE_KEY not in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = legacy_world.NPCS + (GUIDE_NEMM,)
    legacy_world.NPCS_BY_KEY[SPOREKIN_GUIDE_KEY] = GUIDE_NEMM

    if SPOREKIN_PRACTICE_HUSK_KEY not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (PRACTICE_HUSK,)
    combat.ENEMIES_BY_KEY[SPOREKIN_PRACTICE_HUSK_KEY] = PRACTICE_HUSK

    _patch_sporekin_lore()
    _patch_memory_path()

    if world_service is not None:
        room = legacy_world.ROOMS_BY_KEY.get(SPOREKIN_MEMORY_PATH_ROOM_KEY)
        if room is not None:
            world_service.legacy_rooms[SPOREKIN_MEMORY_PATH_ROOM_KEY] = room
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(SPOREKIN_MEMORY_PATH_ROOM_KEY, None)


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, SPOREKIN_DEPTH_QUEST_KEY)


def _ready_for_depth(session) -> bool:
    character = session.character
    if character is None or character.race != "sporekin":
        return False
    flags = session.database.list_flags(character.id)
    if "sporekin_forgotten_pulse_solved" in flags:
        return True
    forgotten = session.database.get_quest(character.id, "sporekin_forgotten_pulse")
    return bool(forgotten and forgotten.get("status") == "completed")


def _ensure_depth_quest(session) -> bool:
    if not _ready_for_depth(session) or session.character is None:
        return False
    if _quest(session) is not None:
        return False
    session.database.start_quest(session.character.id, SPOREKIN_DEPTH_QUEST_KEY, "talk_nemm")
    return True


def _in_memory_path(session) -> bool:
    return bool(
        session.character is not None
        and session.character.current_room == SPOREKIN_MEMORY_PATH_ROOM_KEY
    )


async def _show_lines(session, title: str, lines: tuple[str, ...]) -> None:
    await session.send(f"\r\n--- {title} ---\r\n")
    for line in lines:
        await session.send(line + "\r\n")


async def _talk_nemm(session) -> bool:
    if not _in_memory_path(session):
        return False
    quest = _quest(session)
    if quest is None:
        await session.send("Guide Nemm is not part of your current path yet.\r\n")
        return True
    step = quest.get("current_step")
    if quest.get("status") == "completed":
        await session.send(
            "Nemm inclines their cap. 'The Chorus is still here. So are you. Neither fact has to make the other smaller.'\r\n"
        )
        return True
    if step == "talk_nemm":
        await session.send(
            "Nemm speaks aloud, slowly enough that each word feels separate from the background pressure of the Chorus.\r\n\r\n"
            "'You have followed a memory shared by many. Now practice something the Chorus cannot do for you: choose one thought because it is yours.'\r\n"
            "'Shared memory is not shared permission. Shared fear is not a command. Shared certainty can still be wrong.'\r\n\r\n"
            "Type SPEAK ALONE.\r\n"
        )
        session.database.advance_quest(session.character.id, SPOREKIN_DEPTH_QUEST_KEY, "speak_alone")
        return True
    if step == "return_nemm":
        session.database.complete_quest(session.character.id, SPOREKIN_DEPTH_QUEST_KEY)
        session.database.grant_flag(session.character.id, SPOREKIN_DEPTH_COMPLETE_FLAG)
        await session.send(
            "Nemm looks at the collapsed Practice Husk, then at you.\r\n\r\n"
            "'Good. The Chorus could tell you how a thousand hands once held a weapon. It could not decide when this hand should strike.'\r\n"
            "'Remember that on the surface. Listen widely. Warn clearly. Advise when useful. But leave people enough room to become themselves.'\r\n\r\n"
            "Quest complete: A Voice of Your Own.\r\n"
        )
        return True
    if step == "practice_husk":
        await session.send(
            "Nemm points toward the weighted fungal frame. 'The next thought belongs to your hands. ATTACK PRACTICE HUSK.'\r\n"
        )
        return True
    await session.send(
        "Nemm waits without filling the silence for you. 'Do the part only you can do.'\r\n"
    )
    return True


async def _speak_alone(session) -> bool:
    if not _in_memory_path(session):
        return False
    quest = _quest(session)
    if quest is None or quest.get("status") != "active":
        await session.send("You can speak aloud, but no guided exercise is asking for it now.\r\n")
        return True
    if quest.get("current_step") != "speak_alone":
        await session.send("You have already made that distinction for this lesson.\r\n")
        return True
    session.database.grant_flag(session.character.id, SPOREKIN_INDIVIDUAL_VOICE_FLAG)
    session.database.advance_quest(session.character.id, SPOREKIN_DEPTH_QUEST_KEY, "practice_husk")
    await session.send(
        "You let the Chorus remain present without reaching into it for an answer. Then you speak one sentence aloud simply because you chose it:\r\n\r\n"
        "  'I am here. I can listen, and I can decide.'\r\n\r\n"
        "The shared consciousness does not withdraw. It makes room. Nemm gives a small approving nod toward the Practice Husk.\r\n"
        "Quest updated: A Voice of Your Own. ATTACK PRACTICE HUSK.\r\n"
    )
    return True


def install_sporekin_depth_runtime(player_session_class, world_service=None) -> None:
    if getattr(player_session_class, "_sporekin_depth_runtime_installed", False):
        return

    install_sporekin_depth_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_finish_enemy_defeat = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if _ensure_depth_quest(self):
            await self.send(
                "\r\nA restored memory path now leads to a different kind of Sporekin lesson. "
                "New quest: A Voice of Your Own. Follow the old path north and TALK NEMM.\r\n"
            )

    async def _finish_enemy_defeat(self, enemy) -> None:
        defeated_key = enemy.definition.key
        await previous_finish_enemy_defeat(self, enemy)
        if (
            self.character is not None
            and self.character.race == "sporekin"
            and defeated_key == SPOREKIN_PRACTICE_HUSK_KEY
        ):
            quest = _quest(self)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "practice_husk":
                self.database.grant_flag(self.character.id, SPOREKIN_PRACTICE_HUSK_FLAG)
                self.database.advance_quest(self.character.id, SPOREKIN_DEPTH_QUEST_KEY, "return_nemm")
                await self.send(
                    "Quest updated: A Voice of Your Own. The Practice Husk slumps harmlessly apart. TALK NEMM.\r\n"
                )

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return

        _ensure_depth_quest(self)
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if self.character.race == "sporekin":
            if normalized in {"sporekin", "chorus", "the chorus"}:
                await _show_lines(self, "The Sporekin Chorus", SPOREKIN_CULTURE_LINES)
                return
            if normalized in {"selfhood", "sporekin selfhood", "individual", "individuality"}:
                await _show_lines(self, "Sporekin Selfhood", SPOREKIN_SELFHOOD_LINES)
                return
            if normalized in {"guidance", "sporekin guidance", "guide"}:
                await _show_lines(self, "The Discipline of Guidance", SPOREKIN_GUIDANCE_LINES)
                return
            if normalized in {"speak alone", "speak for myself", "speak as myself"}:
                if await _speak_alone(self):
                    return
            if normalized in {"talk nemm", "speak nemm", "talk guide", "talk guide nemm"}:
                if await _talk_nemm(self):
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

        _ensure_depth_quest(self)
        if normalized in {"help", "?"} and self.character.race == "sporekin":
            await self.send(
                "Sporekin culture: CHORUS, SELFHOOD, GUIDANCE. Later in the opening, Guide Nemm teaches A Voice of Your Own.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._sporekin_depth_runtime_installed = True
