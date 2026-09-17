from __future__ import annotations

from dataclasses import dataclass

from mud.combat import ENEMIES_BY_KEY
from mud.partial_target_matching import normalize_target
from mud.world import NPCS_BY_KEY


@dataclass(frozen=True, slots=True)
class VisibleActor:
    key: str
    name: str
    description: str
    kind: str
    aliases: tuple[str, ...] = ()
    aggressive: bool = False


def _sentence(text: str) -> str:
    value = text.strip()
    if not value:
        return value
    value = value[0].upper() + value[1:]
    if value[-1] not in ".!?":
        value += "."
    return value


def visible_actors(session, world_service) -> tuple[VisibleActor, ...]:
    """Return the people and creatures the player can actually see here.

    This deliberately uses the assembled room scene plus live mobile-NPC state,
    matching the same sources used by LOOK and partial target matching. Internal
    keys are never exposed as player-facing aliases.
    """

    character = getattr(session, "character", None)
    if character is None:
        return ()

    room_key = character.current_room or ""
    scene = world_service.scene(room_key)
    actors: list[VisibleActor] = []

    if scene is not None:
        for npc_key in scene.npc_keys:
            npc = NPCS_BY_KEY.get(npc_key)
            if npc is not None:
                actors.append(
                    VisibleActor(
                        key=npc.key,
                        name=npc.name,
                        description=npc.short_description,
                        kind="npc",
                    )
                )
        for enemy_key in scene.enemy_keys:
            enemy = ENEMIES_BY_KEY.get(enemy_key)
            if enemy is not None:
                actors.append(
                    VisibleActor(
                        key=enemy.key,
                        name=enemy.name,
                        description=enemy.description,
                        kind="enemy",
                        aliases=tuple(enemy.aliases),
                        aggressive=bool(getattr(enemy, "retaliates", False)),
                    )
                )

    mobile_npcs = getattr(session, "mobile_npcs", None)
    if mobile_npcs is not None:
        for state in mobile_npcs.npcs_in_room(room_key):
            definition = state.definition
            actors.append(
                VisibleActor(
                    key=definition.key,
                    name=definition.name,
                    description=definition.short_description,
                    kind="enemy" if bool(getattr(definition, "aggressive", False)) else "npc",
                    aliases=tuple(getattr(definition, "aliases", ())),
                    aggressive=bool(getattr(definition, "aggressive", False)),
                )
            )

    # A static listing and a mobile state can occasionally describe the same
    # visible actor. Collapse exact visible-name duplicates rather than making
    # LOOK report the same person twice.
    deduped: dict[tuple[str, str], VisibleActor] = {}
    for actor in actors:
        deduped[(actor.kind, normalize_target(actor.name))] = actor
    return tuple(deduped.values())


def _matches_exact(actor: VisibleActor, target: str) -> bool:
    query = normalize_target(target)
    if not query:
        return False
    names = (actor.name, *actor.aliases)
    return any(normalize_target(name) == query for name in names if name)


def find_visible_actor(session, world_service, target: str) -> VisibleActor | None:
    """Resolve an already-expanded visible actor name without guessing."""

    matches = [actor for actor in visible_actors(session, world_service) if _matches_exact(actor, target)]
    if len(matches) != 1:
        return None
    return matches[0]


def render_actor_detail(actor: VisibleActor) -> str:
    """Render only authored, trustworthy information about a visible actor."""

    lines = [actor.name, _sentence(actor.description)]
    if actor.kind == "enemy":
        lines.append(f"You can ATTACK {actor.name} if you choose to engage it.")
    else:
        lines.append(f"You can TALK {actor.name} to interact with them.")
    return "\r\n".join(lines)


def _inspection_target(command: str) -> str | None:
    stripped = command.strip()
    normalized = " ".join(stripped.lower().split())
    for prefix in ("look at ", "look ", "examine ", "inspect "):
        if normalized.startswith(prefix):
            return stripped[len(prefix):].strip()
    return None


def normalize_inspection_synonym(command: str) -> str:
    """Normalize common MUD inspection phrasing without changing bare LOOK.

    LOOK AT <thing> should behave exactly like LOOK <thing> everywhere, including
    room features. INSPECT <thing> is likewise a natural EXAMINE synonym. The
    established INSPECT ITEM <name> command is preserved for inventory details.
    """

    stripped = command.strip()
    normalized = " ".join(stripped.lower().split())
    if normalized.startswith("look at "):
        return "look " + stripped[len("look at "):].strip()
    if normalized.startswith("inspect ") and not normalized.startswith("inspect item "):
        return "examine " + stripped[len("inspect "):].strip()
    return command


async def handle_actor_inspection(session, command: str, world_service) -> bool:
    """Handle LOOK/LOOK AT/EXAMINE/INSPECT only when the target is an actor.

    Returning False for non-actors is essential: LOOK SIGN, EXAMINE WRECK, and
    every other authored feature command continue down the existing runtime
    stack untouched.
    """

    target = _inspection_target(command)
    if not target:
        return False
    actor = find_visible_actor(session, world_service, target)
    if actor is None:
        return False
    await session.send("\r\n" + render_actor_detail(actor) + "\r\n")
    return True


def install_actor_inspection_runtime(player_session_class, world_service) -> None:
    """Give every visible NPC/enemy conventional MUD inspection commands."""

    if getattr(player_session_class, "_actor_inspection_runtime_installed", False):
        # CONSIDER is part of the same visible-actor UX. Keep it installed even
        # when another production layer calls this idempotent installer again.
        from mud.consider import install_consider_runtime

        install_consider_runtime(player_session_class, world_service)
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

        if await handle_actor_inspection(self, command, world_service):
            return

        delegated_command = normalize_inspection_synonym(command)
        had_prompt = "prompt" in self.__dict__
        old_prompt = self.__dict__.get("prompt")

        async def replay(_text: str):
            return delegated_command

        self.prompt = replay
        try:
            await previous_playing_prompt(self)
        finally:
            if had_prompt:
                self.prompt = old_prompt
            else:
                self.__dict__.pop("prompt", None)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._actor_inspection_runtime_installed = True

    # Import lazily to avoid an actor_inspection <-> consider import cycle at
    # module load time. CONSIDER wraps inspection and remains entirely non-aggro.
    from mud.consider import install_consider_runtime

    install_consider_runtime(player_session_class, world_service)
