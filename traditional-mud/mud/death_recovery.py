from __future__ import annotations

from dataclasses import dataclass

import mud.party_system as party_system
from mud.mechanics import (
    AbilityDefinition,
    DEATH_RULES,
    PRIEST_DEITIES,
    PRIEST_DEITY_ABILITIES,
    PROGRESSION_RULES,
)
from mud.world import HUMAN_START_ROOM_KEY, ROOMS_BY_KEY


RESURRECTION_LEVEL = 5
RESURRECTION_MANA_COST = 15
RESURRECTION_COOLDOWN_SECONDS = 30.0
RESURRECTION_HEALTH_FRACTION = 0.25
RESURRECTION_MANA_FRACTION = 0.25

RESURRECTION_ABILITY = AbilityDefinition(
    key="resurrection",
    name="Resurrection",
    unlock_level=RESURRECTION_LEVEL,
    mana_cost=RESURRECTION_MANA_COST,
    cooldown_seconds=RESURRECTION_COOLDOWN_SECONDS,
    description=(
        "Returns a fallen character to life at the place they died before they RELEASE. "
        "A successful resurrection prevents the normal death experience loss."
    ),
    category="resurrection",
    skill_improves_effectiveness=False,
    design_status="approved_initial_tuning",
)


@dataclass(frozen=True, slots=True)
class DeathRecord:
    character_id: int
    room_key: str
    enemy_name: str


def ensure_death_storage(database) -> None:
    """Create the small persistent death table without changing the core migration."""
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_deaths (
                character_id INTEGER PRIMARY KEY,
                room_key TEXT NOT NULL,
                enemy_name TEXT NOT NULL,
                died_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )


def get_death_record(database, character_id: int) -> DeathRecord | None:
    ensure_death_storage(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT character_id, room_key, enemy_name FROM character_deaths WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    if row is None:
        return None
    return DeathRecord(
        character_id=int(row["character_id"]),
        room_key=str(row["room_key"]),
        enemy_name=str(row["enemy_name"]),
    )


def _persist_death(database, character_id: int, room_key: str, enemy_name: str) -> None:
    ensure_death_storage(database)
    with database.connect() as db:
        db.execute(
            """
            INSERT INTO character_deaths (character_id, room_key, enemy_name)
            VALUES (?, ?, ?)
            ON CONFLICT(character_id) DO UPDATE SET
                room_key = excluded.room_key,
                enemy_name = excluded.enemy_name,
                died_at = CURRENT_TIMESTAMP
            """,
            (character_id, room_key, enemy_name),
        )


def _clear_death(database, character_id: int) -> None:
    ensure_death_storage(database)
    with database.connect() as db:
        db.execute("DELETE FROM character_deaths WHERE character_id = ?", (character_id,))


def _register_resurrection_ability() -> None:
    """Give every Priest deity path the shared level-5 resurrection utility."""
    for deity in PRIEST_DEITIES:
        current = PRIEST_DEITY_ABILITIES.get(deity.key, ())
        if any(ability.key == RESURRECTION_ABILITY.key for ability in current):
            continue
        PRIEST_DEITY_ABILITIES[deity.key] = current + (RESURRECTION_ABILITY,)


def _is_dead(session) -> bool:
    character = getattr(session, "character", None)
    if character is None:
        return False
    if getattr(session, "_death_pending", False):
        return True
    record = get_death_record(session.database, int(character.id))
    if record is None:
        return False
    session._death_pending = True
    session._death_room_key = record.room_key
    session._death_enemy_name = record.enemy_name
    combatant = getattr(session, "combatant", None)
    if combatant is not None:
        combatant.current_hp = 0
    return True


def _valid_bind_room(session) -> str:
    character = session.character
    bind_room = character.bind_room if character is not None else None
    if bind_room and bind_room in ROOMS_BY_KEY:
        return bind_room
    current_room = character.current_room if character is not None else None
    if current_room and current_room in ROOMS_BY_KEY:
        bind_room = current_room
    else:
        bind_room = HUMAN_START_ROOM_KEY
    if character is not None:
        session.database.set_bind_room(character.id, bind_room)
    return bind_room


async def _announce_party_death(session, enemy_name: str) -> None:
    party = party_system._party_for_session(session)
    character = getattr(session, "character", None)
    if party is None or character is None:
        return
    await party_system._send_party(
        party,
        (
            f"[Party] {character.name} falls to {enemy_name}. They remain at the death site until "
            "they RELEASE or a Priest RESURRECTS them.\r\n"
        ),
        exclude=session,
    )


async def _clean_empty_party_encounter(session, enemy) -> None:
    if enemy is None:
        return
    encounter = party_system._encounter_for(enemy)
    if encounter is None or encounter.participant_ids:
        return
    encounter.resolved = True
    party_system._PARTY_ENCOUNTERS.pop(id(enemy), None)
    await party_system._send_party(
        encounter.party,
        "[Party] No conscious participant remains in the encounter. The enemy breaks off.\r\n",
    )


async def mark_character_dead(session, enemy_name: str) -> None:
    """Leave the character dead in place; XP is not charged until RELEASE."""
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if character is None or combatant is None:
        return
    if _is_dead(session):
        return

    death_room = character.current_room or _valid_bind_room(session)
    enemy = getattr(session, "active_enemy", None)
    _persist_death(session.database, int(character.id), death_room, enemy_name)
    session._death_pending = True
    session._death_room_key = death_room
    session._death_enemy_name = enemy_name
    combatant.current_hp = 0

    await session._stop_combat()
    await _clean_empty_party_encounter(session, enemy)

    await session.send(f"\r\n*** You have been slain by {enemy_name}. ***\r\n")
    await session.send(
        "You remain where you fell. Type RELEASE to return to your bind point and accept the death XP loss, "
        "or wait here for a Priest to RESURRECT you. No item is lost and there is no death debuff.\r\n"
    )
    await _announce_party_death(session, enemy_name)
    await session.send_client_state()


async def release_character(session) -> bool:
    """Return a dead character to bind and apply the 10% current-level XP penalty."""
    character = getattr(session, "character", None)
    combatant = getattr(session, "combatant", None)
    if character is None or combatant is None:
        return False
    if not _is_dead(session):
        await session.send("You are alive; there is nothing to release from.\r\n")
        return False

    # Refresh before calculating the penalty so XP gained/lost elsewhere cannot
    # make a stale session snapshot produce the wrong death cost.
    refreshed = session.database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed
        character = refreshed

    requested_loss, level_floor = DEATH_RULES.experience_loss(character.level, character.experience)
    actual_loss, new_xp, new_level = session.database.apply_experience_loss(
        character.id,
        requested_loss,
        floor_experience=level_floor if not DEATH_RULES.allow_level_loss else 0,
    )

    bind_room = _valid_bind_room(session)
    session.database.set_character_room(character.id, bind_room)
    _clear_death(session.database, character.id)
    session._death_pending = False
    session._death_room_key = None
    session._death_enemy_name = None

    combatant.current_hp = combatant.max_hp
    combatant.current_mana = combatant.max_mana
    combatant.current_movement = combatant.max_movement

    refreshed = session.database.get_character_by_name(character.name)
    if refreshed is not None:
        session.character = refreshed

    await session.send("\r\nYou release your hold on the place where you fell.\r\n")
    if actual_loss:
        await session.send(
            f"Death costs {actual_loss} experience. You now have {new_xp} XP and remain level {new_level}.\r\n"
        )
    else:
        await session.send("You had no experience progress above your current level floor to lose.\r\n")

    room = ROOMS_BY_KEY.get(bind_room)
    room_name = room.name if room is not None else bind_room
    await session.send(f"You return to your bind point: {room_name}.\r\n\r\n")
    if room is not None:
        await session.show_current_room()
    await session.send_client_state()
    return True


def _resurrection_target(priest, target_name: str):
    target = party_system._session_for_name(target_name)
    target_character = getattr(target, "character", None) if target is not None else None
    priest_character = getattr(priest, "character", None)
    if target_character is None or priest_character is None:
        return None
    if int(target_character.id) == int(priest_character.id):
        return None
    if target_character.current_room != priest_character.current_room:
        return None
    if not _is_dead(target):
        return None
    return target


async def resurrect_character(priest, target_name: str) -> bool:
    """Priest level-5 group utility: revive in place with no death XP loss."""
    character = getattr(priest, "character", None)
    combatant = getattr(priest, "combatant", None)
    if character is None or combatant is None:
        return False
    if _is_dead(priest):
        await priest.send("The dead cannot cast Resurrection.\r\n")
        return False
    if character.character_class != "priest" or character.level < RESURRECTION_LEVEL:
        await priest.send(f"Resurrection is a Priest ability unlocked at level {RESURRECTION_LEVEL}.\r\n")
        return False
    if not combatant.ability_ready(RESURRECTION_ABILITY.key):
        await priest.send("Resurrection is still on cooldown.\r\n")
        return False

    target = _resurrection_target(priest, target_name)
    if target is None:
        await priest.send("No dead character by that name is here awaiting release.\r\n")
        return False
    target_character = target.character
    target_combatant = getattr(target, "combatant", None)
    if target_character is None or target_combatant is None:
        await priest.send("That fallen character cannot be restored right now.\r\n")
        return False
    if not combatant.spend_mana(RESURRECTION_MANA_COST):
        await priest.send(f"You need {RESURRECTION_MANA_COST} mana to cast Resurrection.\r\n")
        return False

    _clear_death(target.database, target_character.id)
    target._death_pending = False
    target._death_room_key = None
    target._death_enemy_name = None
    target_combatant.current_hp = max(1, round(target_combatant.max_hp * RESURRECTION_HEALTH_FRACTION))
    target_combatant.current_mana = max(0, round(target_combatant.max_mana * RESURRECTION_MANA_FRACTION))

    priest.database.record_ability_use(character.id, RESURRECTION_ABILITY.key)
    combatant.start_cooldown(RESURRECTION_ABILITY.key, RESURRECTION_COOLDOWN_SECONDS)

    await priest.send(
        f"You call {target_character.name} back from death. They rise where they fell, and no death XP is lost.\r\n"
    )
    await target.send(
        f"\r\n{character.name} calls you back. You rise where you fell with "
        f"{target_combatant.current_hp}/{target_combatant.max_hp} HP. No death XP is lost.\r\n"
    )
    party = party_system._party_for_session(priest)
    if party is not None and party is party_system._party_for_session(target):
        await party_system._send_party(
            party,
            f"[Party] {character.name} resurrects {target_character.name}; the death XP penalty is avoided.\r\n",
            exclude=priest,
        )
    await priest.send_client_state()
    await target.send_client_state()
    return True


async def _show_death_help(session) -> None:
    await session.send(
        "\r\n--- Death & Recovery ---\r\n"
        f"RELEASE: return to your bind point and lose {int(DEATH_RULES.experience_loss_fraction * 100)}% of XP earned in your current level. "
        "Death never removes a completed level.\r\n"
        f"RESURRECT <name>: Priests unlock Resurrection at level {RESURRECTION_LEVEL}; it raises a dead character in place before RELEASE and avoids the XP loss.\r\n"
        "There is no item loss and no post-death debuff.\r\n"
    )


async def _delegate_command(self, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    self.prompt = replay_prompt
    try:
        await previous_prompt(self)
    finally:
        if had_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


_ORIGINAL_PARTY_SEND = None


def _install_party_death_wording() -> None:
    """Correct the older immediate-bind party message now that death is a state."""
    global _ORIGINAL_PARTY_SEND
    if _ORIGINAL_PARTY_SEND is not None:
        return
    _ORIGINAL_PARTY_SEND = party_system._send_party

    async def send_party(party, text: str, *, exclude=None) -> None:
        if "falls and returns to their bind point" in text:
            # mark_character_dead already sends the richer death announcement.
            return
        await _ORIGINAL_PARTY_SEND(party, text, exclude=exclude)

    party_system._send_party = send_party


def install_death_recovery_runtime(player_session_class) -> None:
    """Install persistent death/release and Priest resurrection as the outermost player layer."""
    if getattr(player_session_class, "_death_recovery_runtime_installed", False):
        return

    _register_resurrection_ability()
    _install_party_death_wording()

    previous_death = player_session_class._handle_character_death
    previous_enter = player_session_class.enter_character
    previous_prompt = player_session_class.playing_prompt

    async def handle_character_death(self, enemy_name: str) -> None:
        # Keep the original method available beneath this layer for compatibility,
        # but the live rule is now death-in-place followed by RELEASE or Resurrection.
        await mark_character_dead(self, enemy_name)

    async def enter_character(self) -> None:
        await previous_enter(self)
        character = getattr(self, "character", None)
        combatant = getattr(self, "combatant", None)
        if character is None or combatant is None:
            return
        record = get_death_record(self.database, int(character.id))
        if record is None:
            self._death_pending = False
            return
        self._death_pending = True
        self._death_room_key = record.room_key
        self._death_enemy_name = record.enemy_name
        # Death records keep the death room authoritative across reconnects.
        if character.current_room != record.room_key:
            self.database.set_character_room(character.id, record.room_key)
            refreshed = self.database.get_character_by_name(character.name)
            if refreshed is not None:
                self.character = refreshed
        combatant.current_hp = 0
        await self.send(
            "\r\nYou reconnect still dead at the place you fell. RELEASE returns you to your bind point with the XP penalty; "
            "a Priest standing here can RESURRECT you first.\r\n"
        )
        await self.send_client_state()

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_prompt(self)
            return

        dead = _is_dead(self)
        command = await self.prompt("\r\n[DEAD] > " if dead else "\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())

        if normalized in {"death", "death help", "help death", "recovery", "help recovery"}:
            await _show_death_help(self)
            return

        if dead:
            if normalized in {"release", "release spirit", "return to bind"}:
                await release_character(self)
                return
            if normalized in {"look", "l"}:
                await self.show_current_room()
                await self.send("You are dead here. RELEASE, or wait for a Priest to RESURRECT you.\r\n")
                return
            if normalized in {"party", "group", "party status", "group status"}:
                await party_system._show_party(self)
                return
            if normalized.startswith("party say ") or normalized.startswith("group say "):
                await party_system._party_chat(self, stripped.split(maxsplit=2)[2])
                return
            await self.send(
                "You are dead and cannot act. Type RELEASE to return to your bind point, or wait for a Priest to RESURRECT you.\r\n"
            )
            return

        if normalized == "resurrect":
            await self.send("Usage: RESURRECT <dead character name>.\r\n")
            return
        if normalized.startswith("resurrect "):
            await resurrect_character(self, stripped.split(maxsplit=1)[1])
            return

        await _delegate_command(self, previous_prompt, command)

    player_session_class._handle_character_death = handle_character_death
    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._death_recovery_runtime_installed = True
