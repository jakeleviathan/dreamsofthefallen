from __future__ import annotations

from time import time

from mud.combat import ENEMIES_BY_KEY
from mud.world import ROOMS_BY_KEY


STATIC_ENEMY_RESPAWNS_SQL = """
CREATE TABLE IF NOT EXISTS room_enemy_respawns (
    room_key TEXT NOT NULL,
    enemy_key TEXT NOT NULL,
    defeated_at REAL NOT NULL,
    respawn_at REAL NOT NULL,
    PRIMARY KEY (room_key, enemy_key)
);
"""

# Static room enemies used to be reconstructed at full health on every ATTACK.
# These defaults make a defeat meaningful without making ordinary hunting areas
# feel permanently empty. Individual enemies can later opt into an explicit
# `respawn_seconds` attribute without changing the lifecycle code.
DEFAULT_RESPAWN_SECONDS = 120.0
TUTORIAL_RESPAWN_SECONDS = 60.0
TRAINING_DUMMY_RESPAWN_SECONDS = 15.0
ELITE_RESPAWN_SECONDS = 300.0
BOSS_RESPAWN_SECONDS = 600.0

_BOUND_DATABASE = None


def _usable_database(database) -> bool:
    return database is not None and callable(getattr(database, "connect", None))


def bind_enemy_lifecycle_database(database) -> None:
    """Bind the live shared database for presentation helpers without a session."""
    global _BOUND_DATABASE
    if not _usable_database(database):
        return
    _BOUND_DATABASE = database
    ensure_enemy_lifecycle_storage(database)


def ensure_enemy_lifecycle_storage(database) -> None:
    if not _usable_database(database):
        return
    with database.connect() as db:
        db.execute(STATIC_ENEMY_RESPAWNS_SQL)


def respawn_seconds_for(definition) -> float:
    """Return a conservative default respawn delay for a static room enemy."""
    explicit = getattr(definition, "respawn_seconds", None)
    if explicit is not None:
        return max(0.0, float(explicit))
    if getattr(definition, "key", "") == "training_dummy":
        return TRAINING_DUMMY_RESPAWN_SECONDS
    if bool(getattr(definition, "tutorial", False)):
        return TUTORIAL_RESPAWN_SECONDS

    xp = int(getattr(definition, "xp_reward", 0) or 0)
    if xp >= 250:
        return BOSS_RESPAWN_SECONDS
    if xp >= 100:
        return ELITE_RESPAWN_SECONDS
    return DEFAULT_RESPAWN_SECONDS


def static_enemy_available(
    room_key: str,
    enemy_key: str,
    *,
    database=None,
    now: float | None = None,
) -> bool:
    """Return whether a static room spawn is currently alive/available.

    Expired death rows are removed lazily. This keeps respawn state persistent
    across server restarts without requiring one asyncio task per enemy spawn.
    """
    database = database or _BOUND_DATABASE
    if not room_key or not enemy_key or not _usable_database(database):
        return True

    current = time() if now is None else float(now)
    try:
        ensure_enemy_lifecycle_storage(database)
        with database.connect() as db:
            row = db.execute(
                """
                SELECT respawn_at
                FROM room_enemy_respawns
                WHERE room_key = ? AND enemy_key = ?
                """,
                (room_key, enemy_key),
            ).fetchone()
            if row is None:
                return True
            if float(row["respawn_at"]) <= current:
                db.execute(
                    "DELETE FROM room_enemy_respawns WHERE room_key = ? AND enemy_key = ?",
                    (room_key, enemy_key),
                )
                return True
            return False
    except Exception:
        # Presentation must never take the game down because a temporary test DB
        # or an old development database disappeared underneath a helper call.
        return True


def static_enemy_respawn_remaining(
    room_key: str,
    enemy_key: str,
    *,
    database=None,
    now: float | None = None,
) -> float:
    database = database or _BOUND_DATABASE
    if not room_key or not enemy_key or not _usable_database(database):
        return 0.0
    current = time() if now is None else float(now)
    try:
        ensure_enemy_lifecycle_storage(database)
        with database.connect() as db:
            row = db.execute(
                "SELECT respawn_at FROM room_enemy_respawns WHERE room_key = ? AND enemy_key = ?",
                (room_key, enemy_key),
            ).fetchone()
        if row is None:
            return 0.0
        return max(0.0, float(row["respawn_at"]) - current)
    except Exception:
        return 0.0


def mark_static_enemy_defeated(
    database,
    room_key: str,
    enemy_key: str,
    respawn_seconds: float,
    *,
    now: float | None = None,
) -> bool:
    """Atomically claim a static spawn's defeat.

    False means another combat already defeated the same shared room spawn and
    its respawn timer is still active. This prevents two concurrent sessions
    from both receiving a kill/reward for the same static creature.
    """
    if not _usable_database(database) or not room_key or not enemy_key:
        return True

    current = time() if now is None else float(now)
    respawn_at = current + max(0.0, float(respawn_seconds))
    ensure_enemy_lifecycle_storage(database)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT respawn_at
            FROM room_enemy_respawns
            WHERE room_key = ? AND enemy_key = ?
            """,
            (room_key, enemy_key),
        ).fetchone()
        if row is not None and float(row["respawn_at"]) > current:
            return False
        db.execute(
            """
            INSERT INTO room_enemy_respawns (room_key, enemy_key, defeated_at, respawn_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(room_key, enemy_key) DO UPDATE SET
                defeated_at = excluded.defeated_at,
                respawn_at = excluded.respawn_at
            """,
            (room_key, enemy_key, current, respawn_at),
        )
    return True


def clear_static_enemy_respawn(database, room_key: str, enemy_key: str) -> None:
    if not _usable_database(database):
        return
    ensure_enemy_lifecycle_storage(database)
    with database.connect() as db:
        db.execute(
            "DELETE FROM room_enemy_respawns WHERE room_key = ? AND enemy_key = ?",
            (room_key, enemy_key),
        )


def static_enemy_spawn_key(enemy_key: str, occurrence: int) -> str:
    """Return the persistent key for one authored static spawn.

    The first occurrence keeps the historical raw enemy key so existing death
    rows remain valid. Additional copies get stable #2, #3, ... suffixes.
    """
    return enemy_key if occurrence <= 1 else f"{enemy_key}#{occurrence}"


def iter_static_enemy_spawns(enemy_keys) -> tuple[tuple[str, str], ...]:
    """Pair authored enemy definition keys with concrete persistent spawn keys."""
    counts: dict[str, int] = {}
    result: list[tuple[str, str]] = []
    for enemy_key in enemy_keys:
        counts[enemy_key] = counts.get(enemy_key, 0) + 1
        result.append((enemy_key, static_enemy_spawn_key(enemy_key, counts[enemy_key])))
    return tuple(result)


def _static_enemy_keys_in_room(room_key: str) -> tuple[str, ...]:
    room = ROOMS_BY_KEY.get(room_key)
    return tuple(getattr(room, "enemy_keys", ())) if room is not None else ()


def _static_enemy_spawns_in_room(room_key: str) -> tuple[tuple[str, str], ...]:
    return iter_static_enemy_spawns(_static_enemy_keys_in_room(room_key))


def _enemy_definition_has_available_spawn(room_key: str, enemy_key: str, database=None) -> bool:
    matches = [
        spawn_key
        for definition_key, spawn_key in _static_enemy_spawns_in_room(room_key)
        if definition_key == enemy_key
    ]
    if not matches:
        return False
    return any(
        static_enemy_available(room_key, spawn_key, database=database)
        for spawn_key in matches
    )


def _install_presentation_filters() -> None:
    """Keep LOOK, inspection, abbreviation, and Mudlet actions in sync with death state."""
    try:
        import mud.room_prompt_experience as room_prompt

        if not getattr(room_prompt, "_enemy_lifecycle_filter_installed", False):
            original_enemy_lines = room_prompt._enemy_lines

            def enemy_lines(scene):
                if scene is None:
                    return []
                room_key = str(getattr(scene, "key", "") or "")
                if not room_key:
                    return original_enemy_lines(scene)
                lines: list[str] = []
                for enemy_key, spawn_key in iter_static_enemy_spawns(
                    getattr(scene, "enemy_keys", ())
                ):
                    enemy = ENEMIES_BY_KEY.get(enemy_key)
                    if enemy is not None and static_enemy_available(room_key, spawn_key):
                        lines.append(enemy.name)
                return lines

            room_prompt._enemy_lines = enemy_lines
            room_prompt._enemy_lifecycle_filter_installed = True
    except Exception:
        pass

    try:
        import mud.actor_inspection as actor_inspection

        if not getattr(actor_inspection, "_enemy_lifecycle_filter_installed", False):
            original_visible_actors = actor_inspection.visible_actors

            def visible_actors(session, world_service):
                actors = original_visible_actors(session, world_service)
                character = getattr(session, "character", None)
                if character is None:
                    return actors
                room_key = character.current_room or ""
                database = getattr(session, "database", None)
                static_keys = set(_static_enemy_keys_in_room(room_key))
                occurrence: dict[str, int] = {}
                filtered = []
                for actor in actors:
                    key = getattr(actor, "key", "")
                    if getattr(actor, "kind", "") == "enemy" and key in static_keys:
                        occurrence[key] = occurrence.get(key, 0) + 1
                        spawn_key = static_enemy_spawn_key(key, occurrence[key])
                        if not static_enemy_available(room_key, spawn_key, database=database):
                            continue
                    filtered.append(actor)
                return tuple(filtered)

            actor_inspection.visible_actors = visible_actors
            actor_inspection._enemy_lifecycle_filter_installed = True
    except Exception:
        pass

    try:
        import mud.partial_target_matching as partial_target_matching

        if not getattr(partial_target_matching, "_enemy_lifecycle_filter_installed", False):
            original_visible_targets = partial_target_matching.visible_target_candidates

            def visible_target_candidates(session, world_service, *, kind: str):
                candidates = original_visible_targets(session, world_service, kind=kind)
                if kind not in {"enemy", "actor"}:
                    return candidates
                character = getattr(session, "character", None)
                if character is None:
                    return candidates
                room_key = character.current_room or ""
                database = getattr(session, "database", None)
                static_keys = set(_static_enemy_keys_in_room(room_key))
                occurrence: dict[str, int] = {}
                filtered = []
                for candidate in candidates:
                    key = getattr(candidate, "key", "")
                    if getattr(candidate, "kind", "") == "enemy" and key in static_keys:
                        occurrence[key] = occurrence.get(key, 0) + 1
                        spawn_key = static_enemy_spawn_key(key, occurrence[key])
                        if not static_enemy_available(room_key, spawn_key, database=database):
                            continue
                    filtered.append(candidate)
                return tuple(filtered)

            partial_target_matching.visible_target_candidates = visible_target_candidates
            partial_target_matching._enemy_lifecycle_filter_installed = True
    except Exception:
        pass

    try:
        import mud.modern_client_experience as modern_client

        if not getattr(modern_client, "_enemy_lifecycle_filter_installed", False):
            original_context_actions = modern_client._context_actions

            def context_actions(session, world, room):
                payload = original_context_actions(session, world, room)
                character = getattr(session, "character", None)
                if character is None:
                    return payload
                room_key = character.current_room or ""
                database = getattr(session, "database", None)
                dead_names = {
                    ENEMIES_BY_KEY[key].name.lower()
                    for key in set(_static_enemy_keys_in_room(room_key))
                    if key in ENEMIES_BY_KEY
                    and not _enemy_definition_has_available_spawn(
                        room_key, key, database=database
                    )
                }
                if not dead_names:
                    return payload
                actions = payload.get("actions") if isinstance(payload, dict) else None
                if isinstance(actions, list):
                    payload["actions"] = [
                        action for action in actions
                        if not (
                            action.get("kind") == "combat"
                            and str(action.get("command", "")).lower().removeprefix("attack ") in dead_names
                        )
                    ]
                return payload

            modern_client._context_actions = context_actions
            modern_client._enemy_lifecycle_filter_installed = True
    except Exception:
        pass


def install_enemy_lifecycle_runtime(player_session_class) -> None:
    """Add shared death/respawn state to legacy static room enemies.

    Mobile NPCs already own their own inactive/respawn lifecycle. This installer
    only handles enemies authored directly into a room's `enemy_keys` list.
    """
    if getattr(player_session_class, "_enemy_lifecycle_runtime_installed", False):
        return

    original_init = getattr(player_session_class, "__init__", None)
    if callable(original_init):
        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            bind_enemy_lifecycle_database(getattr(self, "database", None))

        player_session_class.__init__ = __init__

    previous_enemy_in_room = getattr(player_session_class, "_enemy_in_current_room", None)
    if callable(previous_enemy_in_room):
        def _enemy_in_current_room(self, target_text: str):
            character = getattr(self, "character", None)
            if character is None:
                return previous_enemy_in_room(self, target_text)
            room_key = character.current_room or ""
            database = getattr(self, "database", None)
            matching_static = False
            for enemy_key, spawn_key in _static_enemy_spawns_in_room(room_key):
                definition = ENEMIES_BY_KEY.get(enemy_key)
                if definition is None or not definition.matches(target_text):
                    continue
                matching_static = True
                if static_enemy_available(room_key, spawn_key, database=database):
                    from mud.combat import EnemyState
                    return EnemyState(definition, spawn_key=spawn_key)
            if matching_static:
                return None
            return previous_enemy_in_room(self, target_text)

        player_session_class._enemy_in_current_room = _enemy_in_current_room

    previous_start_combat = getattr(player_session_class, "start_combat", None)
    if callable(previous_start_combat):
        async def start_combat(self, target_text: str) -> None:
            if getattr(self, "active_enemy", None) is None:
                character = getattr(self, "character", None)
                if character is not None:
                    room_key = character.current_room or ""
                    matching = [
                        (enemy_key, spawn_key)
                        for enemy_key, spawn_key in _static_enemy_spawns_in_room(room_key)
                        if (
                            ENEMIES_BY_KEY.get(enemy_key) is not None
                            and ENEMIES_BY_KEY[enemy_key].matches(target_text)
                        )
                    ]
                    if matching and not any(
                        static_enemy_available(
                            room_key,
                            spawn_key,
                            database=getattr(self, "database", None),
                        )
                        for _enemy_key, spawn_key in matching
                    ):
                        definition = ENEMIES_BY_KEY[matching[0][0]]
                        await self.send(
                            f"{definition.name} has already been defeated here and has not respawned yet.\r\n"
                        )
                        return
            await previous_start_combat(self, target_text)

        player_session_class.start_combat = start_combat

    previous_finish_enemy_defeat = getattr(player_session_class, "_finish_enemy_defeat", None)
    if callable(previous_finish_enemy_defeat):
        async def _finish_enemy_defeat(self, enemy) -> None:
            # MobileNpcManager already removes defeated mobile NPCs for several
            # ticks and respawns them at home. Do not create a second lifecycle.
            if getattr(self, "active_mobile_npc_key", None):
                await previous_finish_enemy_defeat(self, enemy)
                return

            character = getattr(self, "character", None)
            database = getattr(self, "database", None)
            room_key = character.current_room if character is not None else ""
            enemy_key = enemy.definition.key
            spawn_key = getattr(enemy, "spawn_key", None) or enemy_key
            claimed = mark_static_enemy_defeated(
                database,
                room_key or "",
                spawn_key,
                respawn_seconds_for(enemy.definition),
            )
            if not claimed:
                await self.send(
                    f"\r\n{enemy.definition.name} is already down; there is no second kill to claim.\r\n"
                )
                stop = getattr(self, "_stop_combat", None)
                if callable(stop):
                    await stop()
                send_state = getattr(self, "send_client_state", None)
                if callable(send_state):
                    await send_state()
                return

            await previous_finish_enemy_defeat(self, enemy)

        player_session_class._finish_enemy_defeat = _finish_enemy_defeat

    # Preserve the legacy/fallback room renderer too. The polished production
    # renderer is filtered separately above, but this keeps tests and Telnet-safe
    # fallback output from describing a defeated enemy as still standing there.
    previous_show_current_room = getattr(player_session_class, "show_current_room", None)
    if callable(previous_show_current_room):
        async def show_current_room(self) -> None:
            character = getattr(self, "character", None)
            if character is None:
                await previous_show_current_room(self)
                return
            room_key = character.current_room or ""
            database = getattr(self, "database", None)
            visibility_by_name: dict[str, list[bool]] = {}
            for enemy_key, spawn_key in _static_enemy_spawns_in_room(room_key):
                definition = ENEMIES_BY_KEY.get(enemy_key)
                if definition is None:
                    continue
                visibility_by_name.setdefault(definition.name, []).append(
                    static_enemy_available(room_key, spawn_key, database=database)
                )
            original_send = self.send
            seen_by_name: dict[str, int] = {}

            async def filtered_send(text: str):
                stripped = text.strip()
                for name, visibility in visibility_by_name.items():
                    if stripped.startswith(f"{name} is here,"):
                        index = seen_by_name.get(name, 0)
                        seen_by_name[name] = index + 1
                        if index < len(visibility) and not visibility[index]:
                            return None
                        break
                return await original_send(text)

            self.send = filtered_send
            try:
                await previous_show_current_room(self)
            finally:
                self.send = original_send

        player_session_class.show_current_room = show_current_room

    _install_presentation_filters()
    player_session_class._enemy_lifecycle_runtime_installed = True
