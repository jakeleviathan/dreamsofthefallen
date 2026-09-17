from __future__ import annotations

from time import monotonic

import mud.ability_mastery as ability_mastery
import mud.mechanics as mechanics


# Levels 21-30 deepen each established class identity rather than replacing it.
# These are fixed progression abilities, consistent with the game's existing rule
# that class abilities are earned by level rather than selected from a talent tree.
BRUTE_UPPER_ABILITIES = (
    mechanics.AbilityDefinition(
        key="intercept",
        name="Intercept",
        unlock_level=22,
        mana_cost=10,
        cooldown_seconds=14.0,
        description="Step into the dangerous line, recover your footing, and harden yourself against the next exchange.",
        category="threat_survival",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="iron_challenge",
        name="Iron Challenge",
        unlock_level=25,
        mana_cost=12,
        cooldown_seconds=10.0,
        description="A punishing challenge that combines weapon damage with a brief defensive brace.",
        category="threat_attack",
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="last_one_standing",
        name="Last One Standing",
        unlock_level=28,
        mana_cost=14,
        cooldown_seconds=30.0,
        description="Turn missing health into stubborn recovery and a short survival window.",
        category="emergency_survival",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="breakers_call",
        name="Breaker's Call",
        unlock_level=30,
        mana_cost=18,
        cooldown_seconds=22.0,
        description="A level-30 linebreaker: heavy physical damage, immediate recovery, and enough presence to reclaim a collapsing fight.",
        category="capstone_threat_attack",
        design_status="approved_upper_midgame_live",
    ),
)

WIZARD_UPPER_ABILITIES = (
    mechanics.AbilityDefinition(
        key="arcane_primer",
        name="Arcane Primer",
        unlock_level=22,
        mana_cost=8,
        cooldown_seconds=8.0,
        description="Prime the next stage of a deliberate spell sequence. Primer rewards planning rather than repeated single-spell spam.",
        category="spell_setup",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="resonant_spear",
        name="Resonant Spear",
        unlock_level=25,
        mana_cost=14,
        cooldown_seconds=8.0,
        description="A focused single-target spell that hits substantially harder when cast after Arcane Primer.",
        category="sequence_damage",
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="mirror_step",
        name="Mirror Step",
        unlock_level=28,
        mana_cost=12,
        cooldown_seconds=18.0,
        description="Fold a reflection around yourself, creating a short defensive window without turning the Wizard into a party tank.",
        category="self_protection",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="convergence",
        name="Convergence",
        unlock_level=30,
        mana_cost=22,
        cooldown_seconds=24.0,
        description="Collapse a prepared spell sequence into one severe single-target strike; strongest after Primer and Resonant Spear.",
        category="capstone_sequence_damage",
        design_status="approved_upper_midgame_live",
    ),
)

DRUID_UPPER_ABILITIES = (
    mechanics.AbilityDefinition(
        key="rootward",
        name="Rootward",
        unlock_level=22,
        mana_cost=10,
        cooldown_seconds=14.0,
        description="Call a short-lived living ward around yourself, turning the immediate terrain into protection.",
        category="terrain_protection",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="lifebloom",
        name="Lifebloom",
        unlock_level=25,
        mana_cost=12,
        cooldown_seconds=10.0,
        description="A strong efficient burst of natural healing that keeps the Druid a reliable secondary healer.",
        category="healing",
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="briar_snare",
        name="Briar Snare",
        unlock_level=28,
        mana_cost=14,
        cooldown_seconds=12.0,
        description="Bind a dangerous foe in violent growth for nature damage while creating a moment of breathing room.",
        category="terrain_control",
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="green_tide",
        name="Green Tide",
        unlock_level=30,
        mana_cost=22,
        cooldown_seconds=24.0,
        description="A level-30 surge that hurts the current foe while returning life to the Druid, expressing restoration and danger at once.",
        category="capstone_nature_cycle",
        design_status="approved_upper_midgame_live",
    ),
)

NECROMANCER_UPPER_ABILITIES = (
    mechanics.AbilityDefinition(
        key="bone_harvest",
        name="Bone Harvest",
        unlock_level=22,
        mana_cost=10,
        cooldown_seconds=8.0,
        description="Tear necromantic force through a foe; a killing use leaves behind Bone Chips for later summons.",
        category="resource_attack",
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="grave_pact",
        name="Grave Pact",
        unlock_level=25,
        mana_cost=0,
        cooldown_seconds=18.0,
        description="Trade your own health for mana, making the Necromancer actively manage life as a resource.",
        category="resource_conversion",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="marrow_host",
        name="Marrow Host",
        unlock_level=28,
        mana_cost=14,
        cooldown_seconds=20.0,
        description="Prepare a coordinated undead surge that empowers the Necromancer's next offensive working.",
        category="pet_setup",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="lichform",
        name="Lichform",
        unlock_level=30,
        mana_cost=20,
        cooldown_seconds=30.0,
        description="Assume a brief lich-like battle state: recover health, harden against damage, and empower necromantic attacks.",
        category="capstone_transformation",
        skill_improves_effectiveness=False,
        design_status="approved_upper_midgame_live",
    ),
)

PRIEST_COMMON_UPPER = (
    mechanics.AbilityDefinition(
        key="intercession",
        name="Intercession",
        unlock_level=22,
        mana_cost=10,
        cooldown_seconds=12.0,
        description="A dependable upper-midgame act of healing and protection shared by every Priest path.",
        category="healing_protection",
        design_status="approved_upper_midgame_live",
    ),
)

PRIEST_PATH_UPPER = {
    "zerjz": (
        mechanics.AbilityDefinition("wellspring", "Wellspring", 25, 13, 9.0, "A deep efficient heal for Priests of Zerjz.", "healing", design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("second_breath", "Second Breath", 28, 16, 20.0, "A rescue heal that becomes strongest when the Priest is already badly hurt.", "emergency_healing", design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("grace_unspent", "Grace Unspent", 30, 24, 28.0, "Zerjz's level-30 capstone: a major restorative surge without turning healing into damage.", "capstone_healing", design_status="approved_upper_midgame_live"),
    ),
    "tenebrous": (
        mechanics.AbilityDefinition("iron_psalm", "Iron Psalm", 25, 13, 14.0, "A dense personal ward that buys time for the party.", "protection", skill_improves_effectiveness=False, design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("aegis_rebound", "Aegis Rebound", 28, 16, 18.0, "A protective prayer that also answers the current foe with restrained retaliatory force.", "protection_retribution", design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("fortress_prayer", "Fortress Prayer", 30, 24, 28.0, "Tenebrous's level-30 capstone: recovery wrapped in the strongest short ward of the path so far.", "capstone_protection", skill_improves_effectiveness=False, design_status="approved_upper_midgame_live"),
    ),
    "leviathan": (
        mechanics.AbilityDefinition("rebuke", "Rebuke", 25, 13, 8.0, "A direct act of divine retaliation against the current foe.", "divine_damage", design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("vengeful_mark", "Vengeful Mark", 28, 14, 16.0, "Mark the next judgment to land with additional force.", "damage_setup", skill_improves_effectiveness=False, design_status="approved_upper_midgame_live"),
        mechanics.AbilityDefinition("final_judgment", "Final Judgment", 30, 24, 24.0, "Leviathan's level-30 capstone: a severe single-target judgment, strongest against a marked foe.", "capstone_divine_damage", design_status="approved_upper_midgame_live"),
    ),
}

UPPER_FIXED_BY_CLASS = {
    "brute": BRUTE_UPPER_ABILITIES,
    "wizard": WIZARD_UPPER_ABILITIES,
    "druid": DRUID_UPPER_ABILITIES,
    "necromancer": NECROMANCER_UPPER_ABILITIES,
}

ALL_UPPER_KEYS = {
    ability.key
    for abilities in (*UPPER_FIXED_BY_CLASS.values(), PRIEST_COMMON_UPPER, *PRIEST_PATH_UPPER.values())
    for ability in abilities
}


def _sort(abilities):
    return tuple(sorted(abilities, key=lambda item: (item.unlock_level or 0, item.name)))


def register_upper_class_abilities() -> None:
    for class_key, additions in UPPER_FIXED_BY_CLASS.items():
        by_key = {ability.key: ability for ability in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())}
        by_key.update({ability.key: ability for ability in additions})
        mechanics.FIXED_CLASS_ABILITIES[class_key] = _sort(by_key.values())

    for deity_key, path_additions in PRIEST_PATH_UPPER.items():
        by_key = {ability.key: ability for ability in mechanics.PRIEST_DEITY_ABILITIES.get(deity_key, ())}
        for ability in (*PRIEST_COMMON_UPPER, *path_additions):
            by_key[ability.key] = ability
        mechanics.PRIEST_DEITY_ABILITIES[deity_key] = _sort(by_key.values())


def _definition_for(session, key: str):
    if session.character is None:
        return None
    for ability in mechanics.class_abilities_for_level(
        session.character.character_class or "",
        session.character.level,
        session.character.deity_key,
    ):
        if ability.key == key:
            return ability
    return None


def _cooldowns(session) -> dict[str, float]:
    table = getattr(session, "_upper_class_cooldowns", None)
    if table is None:
        table = {}
        session._upper_class_cooldowns = table
    return table


async def _pay(session, key: str) -> bool:
    definition = _definition_for(session, key)
    if definition is None or session.combatant is None:
        await session.send("You have not learned that ability.\r\n")
        return False
    now = monotonic()
    ready_at = _cooldowns(session).get(key, 0.0)
    if ready_at > now:
        await session.send(f"{definition.name} is not ready for another {ready_at - now:.1f}s.\r\n")
        return False
    cost = ability_mastery.effective_mana_cost(session, definition)
    if not session.combatant.spend_mana(cost):
        await session.send(f"You need {cost} mana for {definition.name}.\r\n")
        return False
    _cooldowns(session)[key] = now + (definition.cooldown_seconds or 0.0)
    ability_mastery.begin_use(session, definition)
    return True


async def _damage(session, amount: int, text: str, *, bone_on_kill: bool = False) -> bool:
    enemy = getattr(session, "active_enemy", None)
    if enemy is None:
        await session.send("You need an active enemy for that ability.\r\n")
        return False
    ability = ability_mastery.pending_ability(session)
    amount = max(1, ability_mastery.scale_power(session, ability, amount))
    enemy.current_hp = max(0, enemy.current_hp - amount)
    ability_mastery.mark_damage_practice(session, amount, enemy)
    await session.send(f"{text} ({amount} damage)\r\n")
    if enemy.current_hp <= 0:
        if bone_on_kill and session.character is not None:
            session.database.add_item(session.character.id, "bone_chips", 1)
            await session.send("The ending leaves usable Bone Chips in your hands.\r\n")
        await session._finish_enemy_defeat(enemy)
    else:
        send_state = getattr(session, "send_client_state", None)
        if send_state is not None:
            await send_state()
    return True


def _heal(session, amount: int) -> int:
    if session.combatant is None:
        return 0
    ability = ability_mastery.pending_ability(session)
    amount = ability_mastery.scale_power(session, ability, amount)
    before = session.combatant.current_hp
    session.combatant.current_hp = min(session.combatant.max_hp, before + max(0, amount))
    restored = session.combatant.current_hp - before
    ability_mastery.mark_healing_practice(session, restored)
    return restored


async def _use_upper(session, key: str) -> bool:
    if session.character is None or key not in ALL_UPPER_KEYS:
        return False
    if _definition_for(session, key) is None:
        return False
    if session.combatant is None:
        return False

    stats = session.combatant.stats
    class_key = session.character.character_class or ""

    if key == "arcane_primer":
        if not await _pay(session, key):
            return True
        session._upper_arcane_sequence = "primed"
        await session.send("You set three arcane relationships in your mind and leave the final line deliberately unfinished. Arcane Primer is ready to be answered by RESONANT SPEAR.\r\n")
        return True

    if key == "marrow_host":
        if not await _pay(session, key):
            return True
        session._upper_marrow_host = True
        await session.send("Bone memory gathers around your current command. Your next damaging necromantic working will strike with the Marrow Host behind it.\r\n")
        return True

    if key == "vengeful_mark":
        if not await _pay(session, key):
            return True
        if session.active_enemy is None:
            await session.send("There is no foe to mark.\r\n")
            return True
        session._upper_vengeful_mark = id(session.active_enemy)
        await session.send("You name the present wrong without embellishment. The mark waits for FINAL JUDGMENT.\r\n")
        return True

    if key == "grave_pact":
        if not await _pay(session, key):
            return True
        if session.combatant.current_hp <= 18:
            await session.send("You are too close to death to make that pact safely.\r\n")
            return True
        session.combatant.current_hp -= 14
        restored = min(18, session.combatant.max_mana - session.combatant.current_mana)
        session.combatant.current_mana += restored
        await session.send(f"You trade 14 health for {restored} mana. The arithmetic is ugly and entirely yours.\r\n")
        return True

    if not await _pay(session, key):
        return True

    if key == "intercept":
        healed = _heal(session, 10 + max(0, stats.hp // 4))
        session.ward_until = max(session.ward_until, monotonic() + 8.0)
        await session.send(f"You plant yourself in the dangerous line, recover {healed} health, and brace for the next exchange.\r\n")
        return True
    if key == "iron_challenge":
        session.ward_until = max(session.ward_until, monotonic() + 4.0)
        return await _damage(session, 18 + stats.might * 2, "Your Iron Challenge lands like a door slammed on the fight")
    if key == "last_one_standing":
        missing = session.combatant.max_hp - session.combatant.current_hp
        healed = _heal(session, max(12, missing // 3))
        session.ward_until = max(session.ward_until, monotonic() + 8.0)
        await session.send(f"You refuse the arithmetic of collapse, recover {healed} health, and harden for eight seconds.\r\n")
        return True
    if key == "breakers_call":
        healed = _heal(session, 8 + stats.might)
        await session.send(f"The call drags {healed} health back into your stance.\r\n")
        return await _damage(session, 28 + stats.might * 3, "Breaker's Call crashes through the target's momentum")

    if key == "resonant_spear":
        primed = getattr(session, "_upper_arcane_sequence", "") == "primed"
        amount = 24 + stats.mind * 2
        if primed:
            amount = int(amount * 1.5)
            session._upper_arcane_sequence = "spear"
        else:
            session._upper_arcane_sequence = ""
        return await _damage(session, amount, "A Resonant Spear answers the pattern you prepared" if primed else "A Resonant Spear tears straight through the air")
    if key == "mirror_step":
        session.ward_until = max(session.ward_until, monotonic() + 9.0)
        await session.send("Your outline steps half a pace away from itself. For nine seconds, incoming force has to decide which version of you is real.\r\n")
        return True
    if key == "convergence":
        sequenced = getattr(session, "_upper_arcane_sequence", "") == "spear"
        amount = 38 + stats.mind * 3 + (20 if sequenced else 0)
        session._upper_arcane_sequence = ""
        return await _damage(session, amount, "The prepared sequence collapses into Convergence" if sequenced else "You force an unprepared Convergence into being")

    if key == "rootward":
        session.ward_until = max(session.ward_until, monotonic() + 9.0)
        await session.send("Roots, fibers, dust, and whatever living structure the room can offer answer you. Rootward holds for nine seconds.\r\n")
        return True
    if key == "lifebloom":
        healed = _heal(session, 20 + stats.love * 2)
        await session.send(f"Lifebloom restores {healed} health in one warm rush.\r\n")
        return True
    if key == "briar_snare":
        session.ward_until = max(session.ward_until, monotonic() + 3.0)
        return await _damage(session, 18 + stats.love + stats.mind, "Briars seize the foe and buy you a breath of space")
    if key == "green_tide":
        healed = _heal(session, 18 + stats.love * 2)
        await session.send(f"The Green Tide returns {healed} health to you as it surges outward.\r\n")
        return await _damage(session, 28 + stats.mind + stats.love * 2, "Living force breaks over the enemy")

    if key == "bone_harvest":
        bonus = 10 if getattr(session, "_upper_marrow_host", False) else 0
        session._upper_marrow_host = False
        return await _damage(session, 20 + stats.mind * 2 + bonus, "Bone Harvest rips a hard white line through the foe", bone_on_kill=True)
    if key == "lichform":
        healed = _heal(session, 20 + stats.mind)
        session.ward_until = max(session.ward_until, monotonic() + 12.0)
        session._upper_marrow_host = True
        await session.send(f"For twelve seconds you become colder, harder, and less negotiably alive. Lichform restores {healed} health and readies a Marrow Host surge.\r\n")
        return True

    if key == "intercession":
        healed = _heal(session, 18 + stats.love * 2)
        session.ward_until = max(session.ward_until, monotonic() + 5.0)
        await session.send(f"Intercession restores {healed} health and leaves a short protective hush around you.\r\n")
        return True
    if key == "wellspring":
        healed = _heal(session, 30 + stats.love * 3)
        await session.send(f"Wellspring restores {healed} health without spectacle.\r\n")
        return True
    if key == "second_breath":
        missing = session.combatant.max_hp - session.combatant.current_hp
        healed = _heal(session, 22 + stats.love * 2 + missing // 4)
        await session.send(f"Second Breath finds the part of you that had not quite given up and restores {healed} health.\r\n")
        return True
    if key == "grace_unspent":
        healed = _heal(session, 48 + stats.love * 4)
        await session.send(f"Grace Unspent restores {healed} health. Nothing is demanded in exchange.\r\n")
        return True
    if key == "iron_psalm":
        session.ward_until = max(session.ward_until, monotonic() + 12.0)
        await session.send("You speak the Iron Psalm once. The ward answers for twelve seconds.\r\n")
        return True
    if key == "aegis_rebound":
        session.ward_until = max(session.ward_until, monotonic() + 8.0)
        return await _damage(session, 14 + stats.mind + stats.love, "The Aegis answers pressure with pressure")
    if key == "fortress_prayer":
        healed = _heal(session, 20 + stats.love * 2)
        session.ward_until = max(session.ward_until, monotonic() + 16.0)
        await session.send(f"Fortress Prayer restores {healed} health and settles a sixteen-second ward around you.\r\n")
        return True
    if key == "rebuke":
        return await _damage(session, 24 + stats.mind * 2, "Rebuke lands with the weight of named consequence")
    if key == "final_judgment":
        marked = session.active_enemy is not None and getattr(session, "_upper_vengeful_mark", None) == id(session.active_enemy)
        amount = 42 + stats.mind * 3 + (22 if marked else 0)
        session._upper_vengeful_mark = None
        return await _damage(session, amount, "Final Judgment consumes the Vengeful Mark" if marked else "Final Judgment falls without a prepared mark")

    return False


ALIASES = {
    "intercept": "intercept",
    "iron challenge": "iron_challenge",
    "last one standing": "last_one_standing",
    "breakers call": "breakers_call",
    "breaker's call": "breakers_call",
    "arcane primer": "arcane_primer",
    "resonant spear": "resonant_spear",
    "mirror step": "mirror_step",
    "convergence": "convergence",
    "rootward": "rootward",
    "lifebloom": "lifebloom",
    "briar snare": "briar_snare",
    "green tide": "green_tide",
    "bone harvest": "bone_harvest",
    "grave pact": "grave_pact",
    "marrow host": "marrow_host",
    "lichform": "lichform",
    "intercession": "intercession",
    "wellspring": "wellspring",
    "second breath": "second_breath",
    "grace unspent": "grace_unspent",
    "iron psalm": "iron_psalm",
    "aegis rebound": "aegis_rebound",
    "fortress prayer": "fortress_prayer",
    "rebuke": "rebuke",
    "vengeful mark": "vengeful_mark",
    "final judgment": "final_judgment",
}


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had_instance = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_upper_class_progression_runtime(player_session_class) -> None:
    register_upper_class_abilities()
    if getattr(player_session_class, "_upper_class_progression_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())
        key = ALIASES.get(normalized)
        if key is not None and await _use_upper(self, key):
            await ability_mastery.commit_use(self)
            return
        if normalized in {"upper abilities", "abilities 21 30", "class 30"}:
            available = [
                ability
                for ability in mechanics.class_abilities_for_level(
                    self.character.character_class or "",
                    self.character.level,
                    self.character.deity_key,
                )
                if ability.key in ALL_UPPER_KEYS
            ]
            if not available:
                await self.send("You have not reached your level 21-30 class abilities yet.\r\n")
            else:
                await self.send("Upper class abilities:\r\n" + "\r\n".join(
                    f"  {ability.unlock_level:>2}  {ability.name:<20} {ability.description}"
                    for ability in available
                ) + "\r\n")
            return
        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._upper_class_progression_installed = True
