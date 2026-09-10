from __future__ import annotations

import asyncio
from dataclasses import replace

import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.troll_start as troll_start
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, FeatureDefinition, ViewCondition
from mud.stats import EquipmentItem


TROLL_RAID_QUEST_KEY = "troll_night_is_not_over"
TROLL_RAID_COMPLETE_FLAG = "troll_raid_opening_complete"
TROLL_RAID_OPENING_SEEN_FLAG = "troll_raid_opening_seen"
TROLL_RAID_WEAPON_FLAG = "troll_raid_weapon_taken"
TROLL_RAID_COMBAT_FLAG = "troll_raid_scavenger_defeated"
TROLL_RAID_REGEN_SEEN_FLAG = "troll_raid_regeneration_seen"

TROLL_RAID_WEAPON_KEY = "frostroot_notched_spear"
TROLL_RAID_ENEMY_KEY = "troll_breach_scavenger"

TROLL_RAID_QUEST = QuestDefinition(
    key=TROLL_RAID_QUEST_KEY,
    name="The Night Is Not Over",
    style="structured",
    description=(
        "Frostroot has just survived a violent raid. A new Troll wakes wounded inside the "
        "half-burned palisade and has to survive the minutes after the fighting: listen to "
        "Raska, take a usable weapon, put down a scavenger at the breach, and notice what "
        "Troll regeneration can—and cannot—do for an injured body."
    ),
    objective_steps=(
        ("talk_raska", "TALK RASKA. He is wounded, but he is the one giving orders."),
        ("take_weapon", "GRAB SPEAR from the mud beside the broken palisade."),
        ("fight_scavenger", "ATTACK SCAVENGER at the breach. Normal weapon attacks repeat automatically."),
        ("recover", "Stay still and let Troll Regeneration work instead of chasing into the dark."),
        ("return_raska", "TALK RASKA after the immediate danger is down."),
        ("complete", "You survived the raid's aftermath and learned that regeneration is resilience, not invulnerability."),
    ),
)

NOTCHED_HUNTING_SPEAR = ItemDefinition(
    key=TROLL_RAID_WEAPON_KEY,
    name="Notched Hunting Spear",
    description=(
        "A long Troll hunting spear recovered from the mud at Frostroot's broken palisade. "
        "The shaft is smoke-blackened and the blade is nicked, but it is still serviceable."
    ),
    category="equipment",
    equipment=EquipmentItem(
        "Notched Hunting Spear",
        "weapon",
        allowed_races=frozenset({"troll"}),
    ),
    tier=0,
)

BREACH_SCAVENGER = EnemyDefinition(
    key=TROLL_RAID_ENEMY_KEY,
    name="Wounded Scavenger Wolf",
    aliases=("scavenger", "wolf", "wounded wolf", "scavenger wolf", "wounded scavenger"),
    description=(
        "a lean gray wolf with singed fur and a bleeding foreleg, drawn to Frostroot by "
        "smoke, blood, and the confusion after the raid"
    ),
    max_hp=14,
    armor_class=0,
    auto_attack_damage=1,
    auto_attack_interval=1.8,
    xp_reward=15,
    retaliates=True,
    tutorial=False,
)


_ORIGINAL_RECONCILE = troll_start._initialize_or_reconcile_troll
_RECONCILE_PATCHED = False


def _quest(session):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, TROLL_RAID_QUEST.key)


def _ensure_room_and_bind(session) -> None:
    if session.character is None:
        return
    character_id = session.character.id
    changed = False
    if not session.character.current_room:
        session.database.set_character_room(character_id, troll_start.TROLL_START_ROOM_KEY)
        changed = True
    if not session.character.bind_room:
        session.database.set_bind_room(character_id, troll_start.TROLL_START_ROOM_KEY)
        changed = True
    if changed:
        refreshed = session.database.get_character_by_name(session.character.name)
        if refreshed is not None:
            session.character = refreshed


def reconcile_troll_raid_opening(session) -> None:
    """Put brand-new Trolls through the raid before the existing survival arc.

    Existing Troll characters that already began the older Frostroot lesson are
    grandfathered forward so this content update never rolls their progression back.
    """
    if session.character is None or session.character.race != "troll":
        _ORIGINAL_RECONCILE(session)
        return

    _ensure_room_and_bind(session)
    character_id = session.character.id
    raid = _quest(session)
    cold = session.database.get_quest(character_id, troll_start.TROLL_COLD_QUEST.key)

    # Backward compatibility for Trolls created before the raid opening existed.
    if raid is None and cold is not None:
        session.database.start_quest(character_id, TROLL_RAID_QUEST.key, "complete")
        session.database.complete_quest(character_id, TROLL_RAID_QUEST.key)
        session.database.grant_flag(character_id, TROLL_RAID_COMPLETE_FLAG)
        _ORIGINAL_RECONCILE(session)
        return

    if raid is None:
        session.database.start_quest(character_id, TROLL_RAID_QUEST.key, "talk_raska")
        return

    if raid.get("status") == "active":
        return

    session.database.grant_flag(character_id, TROLL_RAID_COMPLETE_FLAG)
    _ORIGINAL_RECONCILE(session)


def _patch_reconcile() -> None:
    global _RECONCILE_PATCHED
    if _RECONCILE_PATCHED:
        return
    troll_start._initialize_or_reconcile_troll = reconcile_troll_raid_opening
    _RECONCILE_PATCHED = True


def _raid_start_room():
    original = legacy_world.ROOMS_BY_KEY[troll_start.TROLL_START_ROOM_KEY]
    return replace(
        original,
        description=(
            "Cold mud sucks at your feet just inside Frostroot's southern breach. Half the "
            "palisade is blackened to charcoal; the rest leans outward where something hit "
            "it hard enough to shear the lashings. Smoke crawls beneath collapsed hide roofs, "
            "and sleet hisses in embers that no one has had time to bury. Blood has gone dark "
            "in the ruts between overturned sledges. Trolls move without ceremony—hauling "
            "water, binding wounds, and counting who is missing. Beyond the broken stakes the "
            "spruce stand close and lightless. The shouting has stopped. That is not the same "
            "thing as being safe."
        ),
        tags=tuple(
            dict.fromkeys(
                original.tags
                + (
                    "raid_aftermath",
                    "burned_palisade",
                    "survival_crisis",
                    "broken_breach",
                )
            )
        ),
    )


def _raid_raska():
    original = legacy_world.NPCS_BY_KEY[troll_start.RASKA_GREYBARK.key]
    return replace(
        original,
        short_description=(
            "a wounded Troll hunter on one knee beside the broken palisade, one hand "
            "clamped over a blood-dark hide wrap"
        ),
        role="wounded Troll hunter, emergency survival mentor, and Frostroot instructor",
        dialogue=(
            "Raska keeps pressure on the bandage beneath his ribs. 'If you can stand, you can help. If you can think, you might live.'",
            "'Do not chase shapes into the trees. Put down what comes through the breach. The dark can wait until daylight.'",
            "'Troll flesh mends. That does not mean it cannot be torn faster than it heals.'",
        ),
    )


def _raid_room_augmentation():
    base = troll_start.troll_room_augmentations()[troll_start.TROLL_START_ROOM_KEY]
    breach = FeatureDefinition(
        key="frostroot_broken_breach",
        name="Broken Palisade",
        aliases=("palisade", "breach", "broken stakes", "south wall", "wall"),
        summary="a blackened gap where the southern palisade was smashed open during the raid",
        examine_text=(
            "Several stakes are burned through; others were snapped inward and then kicked "
            "back outward during the fighting. Mud beyond the gap holds too many overlapping "
            "tracks to read cleanly in the dark. A notched hunting spear lies where someone "
            "dropped it beside the lowest broken timber."
        ),
        search_text=(
            "You find blood, boot prints, wolf tracks, splintered lashings, and too much churned "
            "mud to say with confidence what finally broke the wall."
        ),
        listen_text=(
            "Behind the voices and crackle of wet embers, the spruce beyond the stakes go "
            "quiet for a few breaths at a time."
        ),
    )
    aftermath_layers = (
        DescriptionLayer(
            key="troll_raid_day",
            text=(
                "In daylight the damage is worse, not better: scorched roofs, split stakes, "
                "and hurried bandages show exactly how close Frostroot came to breaking."
            ),
            priority=80,
            condition=ViewCondition(time_buckets=("day",)),
        ),
        DescriptionLayer(
            key="troll_raid_night",
            text=(
                "Torchlight reaches only a few paces beyond the broken stakes. Every movement "
                "between the spruce trunks looks deliberate until it disappears."
            ),
            priority=85,
            condition=ViewCondition(time_buckets=("night",)),
        ),
        DescriptionLayer(
            key="troll_raid_snow",
            text=(
                "Fresh snow catches in the ash and turns gray where boots have ground it into "
                "the bloody mud."
            ),
            priority=90,
            condition=ViewCondition(weather=("snow",)),
        ),
        DescriptionLayer(
            key="troll_raid_storm",
            text=(
                "Wind drives smoke sideways through the breach, making every torch gutter and "
                "every shouted instruction shorter."
            ),
            priority=95,
            condition=ViewCondition(weather=("storm",)),
        ),
    )
    return replace(
        base,
        features=base.features + (breach,),
        description_layers=aftermath_layers,
    )


def _replace_room(room) -> None:
    legacy_world.ROOMS = tuple(
        room if existing.key == room.key else existing for existing in legacy_world.ROOMS
    )
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc) -> None:
    legacy_world.NPCS = tuple(
        npc if existing.key == npc.key else existing for existing in legacy_world.NPCS
    )
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def install_troll_raid_content(world_service=None) -> None:
    """Register the desperate Frostroot opening without replacing the later Troll arc."""
    if TROLL_RAID_QUEST.key not in quests.QUESTS_BY_KEY:
        quests.QUESTS = quests.QUESTS + (TROLL_RAID_QUEST,)
    quests.QUESTS_BY_KEY[TROLL_RAID_QUEST.key] = TROLL_RAID_QUEST

    if TROLL_RAID_WEAPON_KEY not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (NOTCHED_HUNTING_SPEAR,)
    crafting.ITEMS_BY_KEY[TROLL_RAID_WEAPON_KEY] = NOTCHED_HUNTING_SPEAR

    if TROLL_RAID_ENEMY_KEY not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (BREACH_SCAVENGER,)
    combat.ENEMIES_BY_KEY[TROLL_RAID_ENEMY_KEY] = BREACH_SCAVENGER

    room = _raid_start_room()
    raska = _raid_raska()
    _replace_room(room)
    _replace_npc(raska)
    _patch_reconcile()

    if world_service is not None:
        world_service.legacy_rooms[room.key] = room
        world_service.augmentations[room.key] = _raid_room_augmentation()
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(room.key, None)


def _raid_step(session) -> str | None:
    raid = _quest(session)
    if raid and raid.get("status") == "active":
        return raid.get("current_step")
    return None


def _raid_enemy_target(text: str) -> bool:
    return BREACH_SCAVENGER.matches(text)


async def _show_raid_status(session) -> None:
    raid = _quest(session)
    await session.send("\r\n--- Frostroot: Immediate Survival ---\r\n")
    if raid is None:
        await session.send("The raid opening has not been initialized.\r\n")
        return
    if raid.get("status") == "completed":
        await session.send("The immediate danger at the breach is over.\r\n")
        return
    objective = TROLL_RAID_QUEST.objective_for_step(raid.get("current_step"))
    await session.send(f"Lesson: {TROLL_RAID_QUEST.name}\r\n")
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    await session.send(
        "This is survival, not a rite of passage. Getting through the next minute matters more than looking brave.\r\n"
    )


async def _talk_raska_raid(session) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    raid = _quest(session)
    if not raid or raid.get("status") != "active":
        return False
    step = raid.get("current_step")

    if step == "talk_raska":
        session.database.advance_quest(session.character.id, TROLL_RAID_QUEST.key, "take_weapon")
        await session.send(
            "\r\nRaska is on one knee beside the shattered wall, one hand clamped over a cut "
            "beneath his ribs. He looks up only long enough to make sure you are standing.\r\n"
            "'Good. You're awake. Don't waste it.'\r\n"
            "A sound moves through the spruce beyond the broken stakes. Raska jerks his chin "
            "toward a spear lying half in the mud.\r\n"
            "'South wall. GRAB SPEAR. Something's still coming in after the dead.'\r\n"
            "Quest: The Night Is Not Over.\r\n"
        )
        return True

    if step == "return_raska":
        session.database.grant_flag(session.character.id, TROLL_RAID_COMPLETE_FLAG)
        session.database.complete_quest(session.character.id, TROLL_RAID_QUEST.key)
        _ORIGINAL_RECONCILE(session)
        await session.send(
            "\r\nRaska watches the last tremor leave your hands. He does not congratulate you.\r\n"
            "'You're breathing. That's enough for tonight.' He tightens the wrap at his ribs. "
            "'Feel your body closing what it can? Good. Remember the other part: it was not "
            "fast enough to make the teeth harmless.'\r\n"
            "He looks across the burned camp. 'When the ash cools, I'll teach you how to keep "
            "that body alive before something reaches it. Wind. Shelter. Fire. Preparation.'\r\n"
            "Quest complete: The Night Is Not Over.\r\n"
            "New quest: A Fire Before Pride. TALK RASKA when you are ready to begin the first "
            "Frostroot survival lesson.\r\n"
        )
        return True

    objective = TROLL_RAID_QUEST.objective_for_step(step)
    if step == "recover":
        await session.send(
            "\r\nRaska barks without looking over. 'Stay where you are. Let the shaking stop. "
            "Your flesh is working; don't make it chase you into the trees.'\r\n"
        )
    else:
        await session.send(
            "\r\nRaska keeps his attention on the broken stakes. 'Do the next useful thing. "
            "Nothing else matters yet.'\r\n"
        )
    if objective:
        await session.send(f"Current objective: {objective}\r\n")
    return True


async def _take_raid_weapon(session, normalized: str) -> bool:
    if session.character is None or session.character.race != "troll":
        return False
    if normalized not in {
        "grab spear",
        "take spear",
        "get spear",
        "pick up spear",
        "grab weapon",
        "take weapon",
        "get weapon",
        "pick up weapon",
    }:
        return False

    raid = _quest(session)
    if not raid or raid.get("status") != "active":
        return False
    step = raid.get("current_step")
    if step != "take_weapon":
        if TROLL_RAID_WEAPON_FLAG in session.database.list_flags(session.character.id):
            await session.send("\r\nThe notched hunting spear is already in your hands.\r\n")
            return True
        await session.send("\r\nRaska has not sent you for the spear yet. TALK RASKA.\r\n")
        return True

    if session.database.item_quantity(session.character.id, TROLL_RAID_WEAPON_KEY) <= 0:
        session.database.add_item(session.character.id, TROLL_RAID_WEAPON_KEY, 1)
    session.database.grant_flag(session.character.id, TROLL_RAID_WEAPON_FLAG)
    session.database.advance_quest(session.character.id, TROLL_RAID_QUEST.key, "fight_scavenger")
    await session.send(
        "\r\nYou wrench the spear out of the mud. The shaft is smoke-blackened and the blade "
        "has a fresh notch near the point, but it is straight enough.\r\n"
        "A lean gray wolf limps through the broken stakes, fur singed along one shoulder. "
        "It is wounded, hungry, and close enough that running would only give it your back.\r\n"
        "ATTACK SCAVENGER.\r\n"
        "Once combat begins, your normal weapon attacks repeat automatically until the fight "
        "ends or you flee.\r\n"
    )
    return True


def _apply_raid_wound(session) -> None:
    if session.combatant is None:
        return
    step = _raid_step(session)
    if step not in {"talk_raska", "take_weapon", "fight_scavenger"}:
        return
    target = max(6, int(session.combatant.max_hp * 0.40))
    target = min(target, max(1, session.combatant.max_hp - 1))
    if session.combatant.current_hp > target:
        session.combatant.current_hp = target


async def _raid_regeneration_sequence(session) -> None:
    """Show Troll +1 regeneration as visible recovery after the real first fight."""
    if session.character is None or session.combatant is None:
        return
    for pulse in range(1, 4):
        await asyncio.sleep(1.25)
        if (
            session.character is None
            or session.character.race != "troll"
            or _raid_step(session) != "recover"
            or session.combatant is None
        ):
            return
        before = session.combatant.current_hp
        restored = session.combatant.apply_normal_regeneration(0)
        await session.send(
            f"\r\nYour breathing steadies. Troll Regeneration restores {restored} HP "
            f"({before} -> {session.combatant.current_hp})."
            + (" The wound is knitting, slowly." if pulse == 1 else "")
            + "\r\n"
        )
        await session.send_client_state()

    if session.character is None or _raid_step(session) != "recover":
        return
    session.database.grant_flag(session.character.id, TROLL_RAID_REGEN_SEEN_FLAG)
    session.database.advance_quest(session.character.id, TROLL_RAID_QUEST.key, "return_raska")
    await session.send(
        "\r\nThree slow pulses of recovery take the edge off the damage, but they do not erase "
        "what happened. Regeneration bought you breathing room; it did not make the fight free.\r\n"
        "TALK RASKA.\r\n"
    )


def install_troll_raid_runtime(player_session_class, world_service) -> None:
    """Layer the raid tutorial around the already-authored Frostroot starter."""
    install_troll_raid_content(world_service)
    if getattr(player_session_class, "_troll_raid_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "troll":
            reconcile_troll_raid_opening(self)
        await previous_enter_character(self)
        if self.character is None or self.character.race != "troll":
            return

        reconcile_troll_raid_opening(self)
        raid = _quest(self)
        if not raid or raid.get("status") != "active":
            return

        _apply_raid_wound(self)
        if TROLL_RAID_OPENING_SEEN_FLAG not in self.database.list_flags(self.character.id):
            self.database.grant_flag(self.character.id, TROLL_RAID_OPENING_SEEN_FLAG)
            await self.send(
                "\r\nCold mud is under your hands before you remember falling.\r\n"
                "Smoke scratches your throat. Half of Frostroot's palisade is burning or gone. "
                "Someone nearby is crying through clenched teeth while others carry water past "
                "without looking up. Beyond the breach, the spruce are black shapes against "
                "black sky.\r\n"
                "Your side hurts. Your body is already trying to close the damage, but far too "
                "slowly to pretend you are unhurt.\r\n"
                "Hunter Raska Greybark is alive, wounded, and still giving orders.\r\n"
                "TALK RASKA.\r\n"
            )
        else:
            objective = TROLL_RAID_QUEST.objective_for_step(raid.get("current_step"))
            await self.send(f"\r\nImmediate Troll opening: {TROLL_RAID_QUEST.name}.\r\n")
            if objective:
                await self.send(f"Current objective: {objective}\r\n")
        await self.send_client_state()

    def _enemy_in_current_room(self, target_text: str):
        if (
            self.character is not None
            and self.character.race == "troll"
            and self.character.current_room == troll_start.TROLL_START_ROOM_KEY
            and _raid_enemy_target(target_text)
        ):
            if (
                _raid_step(self) == "fight_scavenger"
                and TROLL_RAID_WEAPON_FLAG in self.database.list_flags(self.character.id)
            ):
                return EnemyState(BREACH_SCAVENGER)
            return None
        return previous_enemy_lookup(self, target_text)

    async def _finish_enemy_defeat(self, enemy) -> None:
        is_raid_enemy = (
            self.character is not None
            and self.character.race == "troll"
            and enemy.definition.key == TROLL_RAID_ENEMY_KEY
            and _raid_step(self) == "fight_scavenger"
        )
        await previous_finish_enemy(self, enemy)
        if not is_raid_enemy or self.character is None:
            return

        self.database.grant_flag(self.character.id, TROLL_RAID_COMBAT_FLAG)
        self.database.advance_quest(self.character.id, TROLL_RAID_QUEST.key, "recover")
        await self.send(
            "\r\nThe wolf folds into the mud beside the broken stakes. Your hands keep shaking "
            "after the danger stops moving.\r\n"
            "Raska's voice cuts across the breach: 'Don't chase anything else. Hold still.'\r\n"
        )
        old_task = getattr(self, "_troll_raid_regen_task", None)
        if old_task is None or old_task.done():
            self._troll_raid_regen_task = asyncio.create_task(_raid_regeneration_sequence(self))

    async def playing_prompt(self) -> None:
        if (
            self.character is None
            or self.character.race != "troll"
            or (_quest(self) or {}).get("status") != "active"
        ):
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"raid", "immediate", "survival", "survival record"}:
            await _show_raid_status(self)
            return

        if normalized == "talk" or normalized.startswith("talk "):
            target = troll_start._talk_target(command)
            if (
                self.character.current_room == troll_start.TROLL_START_ROOM_KEY
                and troll_start._matches(
                    target,
                    "raska",
                    "hunter",
                    "hunter raska",
                    "raska greybark",
                    "mentor",
                )
            ):
                if await _talk_raska_raid(self):
                    return

        if await _take_raid_weapon(self, normalized):
            return

        if normalized.startswith("attack ") or normalized.startswith("kill "):
            target = command.strip().split(maxsplit=1)[1]
            if _raid_enemy_target(target):
                if _raid_step(self) != "fight_scavenger":
                    await self.send(
                        "\r\nThere is no useful target to charge yet. Listen to Raska and deal "
                        "with the problem in front of you in order.\r\n"
                    )
                    return
                if TROLL_RAID_WEAPON_FLAG not in self.database.list_flags(self.character.id):
                    await self.send("\r\nYour hands are empty. GRAB SPEAR before the wolf closes.\r\n")
                    return

        if normalized in {
            "north", "south", "east", "west", "up", "down",
            "n", "s", "e", "w", "u", "d",
        }:
            await self.send(
                "\r\nYou make it only a step before Raska snaps, 'Not yet. Something is still "
                "at the breach. Survive this minute before you go looking for the next one.'\r\n"
            )
            return

        # Let the normal command stack execute LOOK, ATTACK, abilities, inventory, etc.
        had_instance_prompt = "prompt" in self.__dict__
        prior_instance_prompt = self.__dict__.get("prompt")

        async def replay_prompt(_text: str) -> str:
            return command

        self.prompt = replay_prompt
        try:
            await previous_playing_prompt(self)
        finally:
            if had_instance_prompt:
                self.prompt = prior_instance_prompt
            else:
                self.__dict__.pop("prompt", None)

        if normalized in {"look", "l"} and _raid_step(self) == "fight_scavenger":
            await self.send(
                "At the southern breach, a Wounded Scavenger Wolf prowls between the broken "
                "stakes, close enough to attack. ATTACK SCAVENGER.\r\n"
            )
        if normalized in {"help", "?"}:
            await self.send(
                "Immediate Troll opening: TALK RASKA, GRAB SPEAR, and ATTACK SCAVENGER. "
                "Use RAID to review the current emergency objective.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = _enemy_in_current_room
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._troll_raid_runtime_installed = True
