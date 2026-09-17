from __future__ import annotations

from time import monotonic

import mud.ability_mastery as ability_mastery
import mud.mechanics as mechanics


# Levels 31-40 continue the fixed class identities established by the earlier
# progression passes. These abilities are not a talent tree: every member of a
# class earns the same core tools, while Priests continue to diverge by deity.
BRUTE_LATE_ABILITIES = (
    mechanics.AbilityDefinition(
        key="guarded_advance",
        name="Guarded Advance",
        unlock_level=32,
        mana_cost=12,
        cooldown_seconds=10.0,
        description="Drive forward behind a short defensive brace and punish the current foe without giving up the line.",
        category="threat_attack",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="rallying_roar",
        name="Rallying Roar",
        unlock_level=35,
        mana_cost=14,
        cooldown_seconds=18.0,
        description="Turn a bad health position into stubborn recovery and a brief ward.",
        category="emergency_survival",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="blood_and_iron",
        name="Blood and Iron",
        unlock_level=38,
        mana_cost=16,
        cooldown_seconds=14.0,
        description="A brutal strike that becomes stronger the more health the Brute is missing.",
        category="missing_health_attack",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="holdfast",
        name="Holdfast",
        unlock_level=40,
        mana_cost=22,
        cooldown_seconds=26.0,
        description="The level-40 Brute culmination: recover, harden, and hit hard enough to re-center a collapsing fight.",
        category="capstone_threat_survival",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
)

WIZARD_LATE_ABILITIES = (
    mechanics.AbilityDefinition(
        key="returning_glyph",
        name="Returning Glyph",
        unlock_level=32,
        mana_cost=10,
        cooldown_seconds=8.0,
        description="Lay down the first relation in a new high-level spell sequence.",
        category="spell_setup",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="prismatic_lance",
        name="Prismatic Lance",
        unlock_level=35,
        mana_cost=16,
        cooldown_seconds=9.0,
        description="A precise single-target strike that becomes much stronger after Returning Glyph.",
        category="sequence_damage",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="phase_shelter",
        name="Phase Shelter",
        unlock_level=38,
        mana_cost=14,
        cooldown_seconds=18.0,
        description="Step partly outside the present exchange without losing a prepared spell sequence.",
        category="self_protection",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="starfall_equation",
        name="Starfall Equation",
        unlock_level=40,
        mana_cost=28,
        cooldown_seconds=26.0,
        description="Resolve a prepared glyph-and-lance sequence into the Wizard's strongest single-target working so far.",
        category="capstone_sequence_damage",
        design_status="approved_late_midgame_live",
    ),
)

DRUID_LATE_ABILITIES = (
    mechanics.AbilityDefinition(
        key="thornwall",
        name="Thornwall",
        unlock_level=32,
        mana_cost=12,
        cooldown_seconds=14.0,
        description="Raise a short-lived living barrier from whatever the local ground can give you.",
        category="terrain_protection",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="river_mend",
        name="River Mend",
        unlock_level=35,
        mana_cost=14,
        cooldown_seconds=10.0,
        description="A strong restorative flow that rewards the Druid for staying present in a long fight.",
        category="healing",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="stormseed",
        name="Stormseed",
        unlock_level=38,
        mana_cost=16,
        cooldown_seconds=12.0,
        description="Plant a burst of violent weather in the current foe, preparing Old Growth to answer it.",
        category="nature_setup_damage",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="old_growth",
        name="Old Growth",
        unlock_level=40,
        mana_cost=26,
        cooldown_seconds=26.0,
        description="Call on deep established life: heal, ward, and turn a prepared Stormseed back through the enemy.",
        category="capstone_nature_cycle",
        design_status="approved_late_midgame_live",
    ),
)

NECROMANCER_LATE_ABILITIES = (
    mechanics.AbilityDefinition(
        key="ossuary_tithe",
        name="Ossuary Tithe",
        unlock_level=32,
        mana_cost=0,
        cooldown_seconds=10.0,
        description="Consume one Bone Chip to recover mana and prepare the next necromantic strike.",
        category="resource_conversion",
        catalyst_item_key="bone_chips",
        catalyst_quantity=1,
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="soul_hook",
        name="Soul Hook",
        unlock_level=35,
        mana_cost=14,
        cooldown_seconds=9.0,
        description="Rip life from the current foe; an Ossuary Tithe makes the hook bite harder.",
        category="life_drain",
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="grave_dominion",
        name="Grave Dominion",
        unlock_level=38,
        mana_cost=18,
        cooldown_seconds=20.0,
        description="Establish a brief field of necromantic control that hardens the caster and prepares the capstone.",
        category="pet_field_setup",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
    mechanics.AbilityDefinition(
        key="deathless_hour",
        name="Deathless Hour",
        unlock_level=40,
        mana_cost=26,
        cooldown_seconds=30.0,
        description="For one decisive exchange, refuse ordinary mortality and cash Grave Dominion into recovery and damage.",
        category="capstone_necromancy",
        skill_improves_effectiveness=False,
        design_status="approved_late_midgame_live",
    ),
)

PRIEST_COMMON_LATE = (
    mechanics.AbilityDefinition(
        key="litany_of_presence",
        name="Litany of Presence",
        unlock_level=32,
        mana_cost=12,
        cooldown_seconds=12.0,
        description="A shared high-level Priest prayer: modest healing and a short protective ward.",
        category="healing_protection",
        design_status="approved_late_midgame_live",
    ),
)

PRIEST_PATH_LATE = {
    "zerjz": (
        mechanics.AbilityDefinition("mending_current", "Mending Current", 35, 15, 9.0, "A deep efficient heal that continues Zerjz's pure restorative identity.", "healing", design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("refuse_the_grave", "Refuse the Grave", 38, 19, 22.0, "A desperate recovery that scales with missing health.", "emergency_healing", design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("abundant_grace", "Abundant Grace", 40, 28, 30.0, "Zerjz's level-40 culmination: the largest direct restorative act on the path so far.", "capstone_healing", design_status="approved_late_midgame_live"),
    ),
    "tenebrous": (
        mechanics.AbilityDefinition("black_bastion", "Black Bastion", 35, 15, 15.0, "A dense ward that turns a dangerous moment into time the party can use.", "protection", skill_improves_effectiveness=False, design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("ward_of_names", "Ward of Names", 38, 18, 18.0, "A protective prayer that also answers the current foe with restrained force.", "protection_retribution", design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("citadel_prayer", "Citadel Prayer", 40, 28, 30.0, "Tenebrous's level-40 culmination: major recovery inside the strongest personal ward yet.", "capstone_protection", skill_improves_effectiveness=False, design_status="approved_late_midgame_live"),
    ),
    "leviathan": (
        mechanics.AbilityDefinition("accounting_flame", "Accounting Flame", 35, 15, 8.0, "Direct divine damage that treats vengeance as an accounting, not a tantrum.", "divine_damage", design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("sentence_mark", "Sentence Mark", 38, 16, 16.0, "Mark the current foe so Wrath Made Plain can land with full force.", "damage_setup", skill_improves_effectiveness=False, design_status="approved_late_midgame_live"),
        mechanics.AbilityDefinition("wrath_made_plain", "Wrath Made Plain", 40, 28, 26.0, "Leviathan's level-40 culmination: severe single-target judgment, strongest against a sentenced foe.", "capstone_divine_damage", design_status="approved_late_midgame_live"),
    ),
}

LATE_FIXED_BY_CLASS = {
    "brute": BRUTE_LATE_ABILITIES,
    "wizard": WIZARD_LATE_ABILITIES,
    "druid": DRUID_LATE_ABILITIES,
    "necromancer": NECROMANCER_LATE_ABILITIES,
}

ALL_LATE_KEYS = {
    ability.key
    for abilities in (*LATE_FIXED_BY_CLASS.values(), PRIEST_COMMON_LATE, *PRIEST_PATH_LATE.values())
    for ability in abilities
}


def _sort(abilities):
    return tuple(sorted(abilities, key=lambda item: (item.unlock_level or 0, item.name)))


def register_late_class_abilities() -> None:
    for class_key, additions in LATE_FIXED_BY_CLASS.items():
        by_key = {ability.key: ability for ability in mechanics.FIXED_CLASS_ABILITIES.get(class_key, ())}
        by_key.update({ability.key: ability for ability in additions})
        mechanics.FIXED_CLASS_ABILITIES[class_key] = _sort(by_key.values())

    for deity_key, path_additions in PRIEST_PATH_LATE.items():
        by_key = {ability.key: ability for ability in mechanics.PRIEST_DEITY_ABILITIES.get(deity_key, ())}
        for ability in (*PRIEST_COMMON_LATE, *path_additions):
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
    table = getattr(session, "_late_class_cooldowns", None)
    if table is None:
        table = {}
        session._late_class_cooldowns = table
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


def _heal(session, amount: int) -> int:
    ability = ability_mastery.pending_ability(session)
    amount = ability_mastery.scale_power(session, ability, amount)
    before = session.combatant.current_hp
    session.combatant.current_hp = min(session.combatant.max_hp, before + max(0, amount))
    restored = session.combatant.current_hp - before
    ability_mastery.mark_healing_practice(session, restored)
    return restored


def _ward(session, seconds: float) -> None:
    session.ward_until = max(getattr(session, "ward_until", 0.0), monotonic() + seconds)


async def _damage(session, amount: int, text: str) -> bool:
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
        await session._finish_enemy_defeat(enemy)
    else:
        send_state = getattr(session, "send_client_state", None)
        if send_state is not None:
            await send_state()
    return True


async def _use_late(session, key: str) -> bool:
    if session.character is None or key not in ALL_LATE_KEYS or session.combatant is None:
        return False
    if _definition_for(session, key) is None:
        return False

    stats = session.combatant.stats

    # Set-up abilities validate their special requirements before spending mana.
    if key == "ossuary_tithe":
        if session.database.item_quantity(session.character.id, "bone_chips") < 1:
            await session.send("Ossuary Tithe needs one Bone Chip.\r\n")
            return True
        if not await _pay(session, key):
            return True
        if not session.database.consume_item(session.character.id, "bone_chips", 1):
            await session.send("The bone slips out of the working before you can finish it.\r\n")
            return True
        restored = min(26, session.combatant.max_mana - session.combatant.current_mana)
        session.combatant.current_mana += restored
        session._late_ossuary_tithe = True
        await session.send(f"You pay the ossuary one Bone Chip and recover {restored} mana. The next Soul Hook is prepared.\r\n")
        return True

    if key == "returning_glyph":
        if not await _pay(session, key):
            return True
        session._late_wizard_sequence = "glyph"
        await session.send("You leave a Returning Glyph hanging unfinished in the air. PRISMATIC LANCE can complete its second relation.\r\n")
        return True

    if key == "sentence_mark":
        if getattr(session, "active_enemy", None) is None:
            await session.send("There is no foe to sentence.\r\n")
            return True
        if not await _pay(session, key):
            return True
        session._late_sentence_mark = id(session.active_enemy)
        await session.send("You pronounce the charge plainly. The Sentence Mark waits for WRATH MADE PLAIN.\r\n")
        return True

    if key == "stormseed":
        if getattr(session, "active_enemy", None) is None:
            await session.send("There is no foe in which to plant the Stormseed.\r\n")
            return True
        if not await _pay(session, key):
            return True
        session._late_stormseed = id(session.active_enemy)
        return await _damage(session, 26 + stats.mind + stats.love, "Stormseed flashes inside the target like weather remembering a tree")

    if key == "grave_dominion":
        if not await _pay(session, key):
            return True
        _ward(session, 12.0)
        session._late_grave_dominion = True
        await session.send("For twelve seconds the room feels arranged around your refusal to die. Grave Dominion is established.\r\n")
        return True

    if not await _pay(session, key):
        return True

    if key == "guarded_advance":
        _ward(session, 5.0)
        return await _damage(session, 24 + stats.might * 2, "You advance behind your own pressure and slam the line forward")
    if key == "rallying_roar":
        missing = session.combatant.max_hp - session.combatant.current_hp
        healed = _heal(session, 16 + missing // 4 + stats.hp // 3)
        _ward(session, 7.0)
        await session.send(f"Your Rallying Roar restores {healed} health and leaves you braced for seven seconds.\r\n")
        return True
    if key == "blood_and_iron":
        missing = session.combatant.max_hp - session.combatant.current_hp
        return await _damage(session, 26 + stats.might * 2 + missing // 5, "Blood and Iron turns damage already suffered into forward force")
    if key == "holdfast":
        healed = _heal(session, 18 + stats.might + stats.hp // 2)
        _ward(session, 12.0)
        await session.send(f"Holdfast restores {healed} health and locks your stance down for twelve seconds.\r\n")
        return await _damage(session, 36 + stats.might * 3, "You answer the whole fight at once with Holdfast")

    if key == "prismatic_lance":
        primed = getattr(session, "_late_wizard_sequence", "") == "glyph"
        amount = 30 + stats.mind * 2
        if primed:
            amount = int(amount * 1.5)
            session._late_wizard_sequence = "lance"
        else:
            session._late_wizard_sequence = ""
        return await _damage(session, amount, "Prismatic Lance catches the Returning Glyph and splits cleanly through the target" if primed else "Prismatic Lance cuts a hard line through the target")
    if key == "phase_shelter":
        _ward(session, 10.0)
        await session.send("You step just far enough out of phase to make the next ten seconds expensive for anyone trying to reach you.\r\n")
        return True
    if key == "starfall_equation":
        prepared = getattr(session, "_late_wizard_sequence", "") == "lance"
        session._late_wizard_sequence = ""
        amount = 48 + stats.mind * 3 + (34 if prepared else 0)
        return await _damage(session, amount, "The completed Starfall Equation arrives exactly where the sequence said it would" if prepared else "You force an unprepared Starfall Equation into the present")

    if key == "thornwall":
        _ward(session, 11.0)
        await session.send("Thorn, root, reed, fungus, and stubborn roadside weed knit into an eleven-second Thornwall.\r\n")
        return True
    if key == "river_mend":
        healed = _heal(session, 30 + stats.love * 3)
        await session.send(f"River Mend restores {healed} health in a steady current.\r\n")
        return True
    if key == "old_growth":
        enemy = getattr(session, "active_enemy", None)
        prepared = enemy is not None and getattr(session, "_late_stormseed", None) == id(enemy)
        session._late_stormseed = None
        healed = _heal(session, 28 + stats.love * 3)
        _ward(session, 10.0)
        await session.send(f"Old Growth restores {healed} health and roots a ten-second ward around you.\r\n")
        if enemy is None:
            return True
        return await _damage(session, 34 + stats.mind + stats.love * 2 + (26 if prepared else 0), "Old Growth answers the Stormseed from below" if prepared else "Old Growth breaks through the foe in a wave of living force")

    if key == "soul_hook":
        tithed = getattr(session, "_late_ossuary_tithe", False)
        session._late_ossuary_tithe = False
        amount = 28 + stats.mind * 2 + (18 if tithed else 0)
        healed = _heal(session, 10 + stats.mind + (6 if tithed else 0))
        await session.send(f"Soul Hook drags {healed} health back into you.\r\n")
        return await _damage(session, amount, "The Ossuary Tithe pulls the Soul Hook deeper" if tithed else "Soul Hook tears life loose and reels it home")
    if key == "deathless_hour":
        prepared = getattr(session, "_late_grave_dominion", False)
        session._late_grave_dominion = False
        healed = _heal(session, 30 + stats.mind * 2 + (12 if prepared else 0))
        _ward(session, 14.0)
        await session.send(f"Deathless Hour restores {healed} health and makes the next fourteen seconds difficult to call mortal.\r\n")
        if getattr(session, "active_enemy", None) is None:
            return True
        return await _damage(session, 38 + stats.mind * 3 + (24 if prepared else 0), "Grave Dominion collapses into the Deathless Hour" if prepared else "Deathless Hour reaches through the current foe")

    if key == "litany_of_presence":
        healed = _heal(session, 22 + stats.love * 2)
        _ward(session, 6.0)
        await session.send(f"Litany of Presence restores {healed} health and leaves a six-second ward.\r\n")
        return True
    if key == "mending_current":
        healed = _heal(session, 38 + stats.love * 3)
        await session.send(f"Mending Current restores {healed} health.\r\n")
        return True
    if key == "refuse_the_grave":
        missing = session.combatant.max_hp - session.combatant.current_hp
        healed = _heal(session, 28 + stats.love * 2 + missing // 3)
        await session.send(f"Refuse the Grave restores {healed} health where the need is greatest.\r\n")
        return True
    if key == "abundant_grace":
        healed = _heal(session, 62 + stats.love * 4)
        await session.send(f"Abundant Grace restores {healed} health. The prayer asks nothing back.\r\n")
        return True
    if key == "black_bastion":
        _ward(session, 14.0)
        await session.send("Black Bastion settles around you for fourteen seconds.\r\n")
        return True
    if key == "ward_of_names":
        _ward(session, 10.0)
        return await _damage(session, 18 + stats.mind + stats.love, "The Ward of Names answers force with remembered consequence")
    if key == "citadel_prayer":
        healed = _heal(session, 28 + stats.love * 2)
        _ward(session, 20.0)
        await session.send(f"Citadel Prayer restores {healed} health and raises a twenty-second ward.\r\n")
        return True
    if key == "accounting_flame":
        return await _damage(session, 30 + stats.mind * 2, "Accounting Flame writes the cost directly across the target")
    if key == "wrath_made_plain":
        enemy = getattr(session, "active_enemy", None)
        marked = enemy is not None and getattr(session, "_late_sentence_mark", None) == id(enemy)
        session._late_sentence_mark = None
        return await _damage(session, 52 + stats.mind * 3 + (30 if marked else 0), "Wrath Made Plain consumes the Sentence Mark" if marked else "Wrath Made Plain falls without a prepared sentence")

    return False


ALIASES = {
    "guarded advance": "guarded_advance",
    "rallying roar": "rallying_roar",
    "blood and iron": "blood_and_iron",
    "holdfast": "holdfast",
    "returning glyph": "returning_glyph",
    "prismatic lance": "prismatic_lance",
    "phase shelter": "phase_shelter",
    "starfall equation": "starfall_equation",
    "thornwall": "thornwall",
    "river mend": "river_mend",
    "stormseed": "stormseed",
    "old growth": "old_growth",
    "ossuary tithe": "ossuary_tithe",
    "soul hook": "soul_hook",
    "grave dominion": "grave_dominion",
    "deathless hour": "deathless_hour",
    "litany of presence": "litany_of_presence",
    "mending current": "mending_current",
    "refuse the grave": "refuse_the_grave",
    "abundant grace": "abundant_grace",
    "black bastion": "black_bastion",
    "ward of names": "ward_of_names",
    "citadel prayer": "citadel_prayer",
    "accounting flame": "accounting_flame",
    "sentence mark": "sentence_mark",
    "wrath made plain": "wrath_made_plain",
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


def install_late_class_progression_runtime(player_session_class) -> None:
    register_late_class_abilities()
    if getattr(player_session_class, "_late_class_progression_installed", False):
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
        if key is not None and await _use_late(self, key):
            await ability_mastery.commit_use(self)
            return
        if normalized in {"late abilities", "abilities 31 40", "class 40"}:
            available = [
                ability
                for ability in mechanics.class_abilities_for_level(
                    self.character.character_class or "",
                    self.character.level,
                    self.character.deity_key,
                )
                if ability.key in ALL_LATE_KEYS
            ]
            if not available:
                await self.send("You have not reached your level 31-40 class abilities yet.\r\n")
            else:
                await self.send("Level 31-40 class abilities:\r\n" + "\r\n".join(
                    f"  {ability.unlock_level:>2}  {ability.name:<22} {ability.description}"
                    for ability in available
                ) + "\r\n")
            return
        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._late_class_progression_installed = True
