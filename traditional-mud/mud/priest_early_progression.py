from __future__ import annotations

import asyncio

import mud.class_progression as class_progression
import mud.mechanics as mechanics
from mud.death_recovery import RESURRECTION_ABILITY


# Every Priest keeps the level-one spell granted by their deity. This common
# backbone makes the class playable regardless of path: heal from the start,
# contribute damage while solo, protect an ally, then grow into the prime-healer
# role through resurrection, group recovery, and protection.
PRIEST_FOUNDATION_ABILITIES = (
    mechanics.AbilityDefinition(
        key="mend_ally",
        name="Mend Ally",
        unlock_level=1,
        mana_cost=3,
        cooldown_seconds=3.0,
        description="A quick targeted prayer that restores health to you or another living character.",
        category="healing",
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="sacred_spark",
        name="Sacred Spark",
        unlock_level=1,
        mana_cost=4,
        cooldown_seconds=4.0,
        description="A small bolt of neutral divine force that gives every Priest a dependable solo attack.",
        category="divine_damage",
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="blessing_of_resolve",
        name="Blessing of Resolve",
        unlock_level=2,
        mana_cost=5,
        cooldown_seconds=12.0,
        description="Bless yourself or an ally with four temporary maximum HP for one minute.",
        category="ally_buff",
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="greater_mend",
        name="Greater Mend",
        unlock_level=4,
        mana_cost=7,
        cooldown_seconds=6.0,
        description="A slower, stronger targeted heal for damage that Mend Ally cannot efficiently cover.",
        category="healing",
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="purifying_light",
        name="Purifying Light",
        unlock_level=6,
        mana_cost=7,
        cooldown_seconds=6.0,
        description="A concentrated divine strike that deals stronger spell damage to the current enemy.",
        category="divine_damage",
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="aegis_of_faith",
        name="Aegis of Faith",
        unlock_level=8,
        mana_cost=8,
        cooldown_seconds=15.0,
        description="Wrap yourself or an ally in a twelve-second protective ward.",
        category="ally_protection",
        skill_improves_effectiveness=False,
        design_status="approved_early_game_live",
    ),
    mechanics.AbilityDefinition(
        key="divine_concord",
        name="Divine Concord",
        unlock_level=10,
        mana_cost=14,
        cooldown_seconds=24.0,
        description="A level-ten Priest capstone that heals the living party and briefly wards everyone reached by the prayer.",
        category="group_healing",
        skill_improves_effectiveness=False,
        design_status="approved_early_game_live",
    ),
)

PRIEST_FOUNDATION_KEYS = frozenset(ability.key for ability in PRIEST_FOUNDATION_ABILITIES)
PRIEST_NEW_RUNTIME_KEYS = PRIEST_FOUNDATION_KEYS - {"mend_ally"}


def _sort_abilities(abilities):
    return tuple(
        sorted(
            abilities,
            key=lambda ability: (
                10_000 if ability.unlock_level is None else ability.unlock_level,
                ability.name,
            ),
        )
    )


def install_priest_early_progression_content() -> None:
    """Install a complete, executable Priest foundation through level 10.

    Love and Mind already drive the shared stat model: Love increases healing,
    Mind increases spell damage, and both increase maximum mana. These abilities
    deliberately use those existing formulas instead of inventing Priest-only
    resource math.
    """

    # Make this installer safe to use by itself in tests/tools as well as after
    # the production class-progression assembly.
    class_progression.install_class_progression_content()

    for path_key, current in tuple(mechanics.PRIEST_DEITY_ABILITIES.items()):
        by_key = {ability.key: ability for ability in current}
        for definition in PRIEST_FOUNDATION_ABILITIES:
            by_key[definition.key] = definition

        # Level 5 is the shared Priest recovery milestone. Keep one canonical
        # Resurrection definition even if the death runtime registered it first.
        by_key[RESURRECTION_ABILITY.key] = RESURRECTION_ABILITY
        mechanics.PRIEST_DEITY_ABILITIES[path_key] = _sort_abilities(by_key.values())


def _resolve_priest_ability(session, ability_text: str):
    character = getattr(session, "character", None)
    if character is None or character.character_class != "priest":
        return None, ""

    normalized = " ".join(ability_text.strip().lower().replace("_", " ").split())
    matches = []
    for ability in mechanics.class_abilities_for_level(
        "priest", character.level, character.deity_key
    ):
        for alias in {ability.key.replace("_", " ").lower(), ability.name.lower()}:
            if normalized == alias:
                matches.append((len(alias), ability, ""))
            elif normalized.startswith(alias + " "):
                matches.append((len(alias), ability, normalized[len(alias):].strip()))
    if not matches:
        return None, ""
    _, ability, target = max(matches, key=lambda row: row[0])
    return ability, target


async def _expire_resolve_blessing(target, amount: int) -> None:
    try:
        await asyncio.sleep(60.0)
        combatant = getattr(target, "combatant", None)
        if combatant is None or getattr(target, "_priest_resolve_blessing", 0) != amount:
            return
        combatant.max_hp = max(1, combatant.max_hp - amount)
        combatant.current_hp = min(combatant.current_hp, combatant.max_hp)
        target._priest_resolve_blessing = 0
        await target.send("Blessing of Resolve fades; your maximum HP returns to normal.\r\n")
        await target.send_client_state()
    except asyncio.CancelledError:
        return


async def _use_priest_foundation_ability(session, ability, target_text: str) -> bool:
    key = ability.key

    if key in {"sacred_spark", "purifying_light"}:
        if session.active_enemy is None:
            await session.send(f"You need an active enemy target for {ability.name}.\r\n")
            return True
        if not await class_progression._activate(session, ability):
            return True
        base = 5 if key == "sacred_spark" else 10
        await class_progression._deal_damage(
            session,
            ability,
            session.combatant.spell_damage(base),
        )
        await class_progression._complete_use(session, ability)
        return True

    if key in {"blessing_of_resolve", "greater_mend", "aegis_of_faith"}:
        target = class_progression._ally_here(session, target_text)
        if target is None or not class_progression._living(target):
            await session.send("That living character is not here.\r\n")
            return True

        if key == "blessing_of_resolve" and getattr(target, "_priest_resolve_blessing", 0):
            await session.send(f"{target.character.name} is already under Blessing of Resolve.\r\n")
            return True

        if not await class_progression._activate(session, ability):
            return True

        if key == "blessing_of_resolve":
            amount = 4
            target._priest_resolve_blessing = amount
            target.combatant.max_hp += amount
            target.combatant.current_hp += amount
            await session.send(
                f"Blessing of Resolve strengthens {target.character.name}, granting {amount} maximum HP for one minute.\r\n"
            )
            if target is not session:
                await target.send(
                    f"{session.character.name}'s Blessing of Resolve grants you {amount} maximum HP for one minute.\r\n"
                )
            class_progression._track_task(
                target, _expire_resolve_blessing(target, amount)
            )
            await target.send_client_state()
        elif key == "greater_mend":
            await class_progression._heal(session, target, 14, ability.name)
        else:
            until = asyncio.get_running_loop().time() + 12.0
            target.ward_until = max(getattr(target, "ward_until", 0.0), until)
            await session.send(
                f"Aegis of Faith protects {target.character.name} for twelve seconds.\r\n"
            )
            if target is not session:
                await target.send(
                    f"{session.character.name}'s Aegis of Faith settles around you.\r\n"
                )

        await class_progression._complete_use(session, ability)
        return True

    if key == "divine_concord":
        if not await class_progression._activate(session, ability):
            return True
        targets = class_progression._support_targets(session)
        if session not in targets and class_progression._living(session):
            targets.insert(0, session)
        until = asyncio.get_running_loop().time() + 8.0
        await session.send(
            f"Divine Concord reaches {len(targets)} living party member{'s' if len(targets) != 1 else ''}.\r\n"
        )
        for member in targets:
            await class_progression._heal(session, member, 8, "Divine Concord")
            member.ward_until = max(getattr(member, "ward_until", 0.0), until)
            if member is not session:
                await member.send("Divine Concord wards you for eight seconds.\r\n")
        await class_progression._complete_use(session, ability)
        return True

    return False


def install_priest_early_progression_runtime(player_session_class) -> None:
    install_priest_early_progression_content()
    if getattr(player_session_class, "_priest_early_progression_runtime_installed", False):
        return

    previous_use_ability = player_session_class.use_ability

    async def use_ability(self, ability_text: str) -> None:
        ability, target_text = _resolve_priest_ability(self, ability_text)
        if ability is not None and ability.key in PRIEST_NEW_RUNTIME_KEYS:
            if await _use_priest_foundation_ability(self, ability, target_text):
                return
        await previous_use_ability(self, ability_text)

    player_session_class.use_ability = use_ability
    player_session_class._priest_early_progression_runtime_installed = True
