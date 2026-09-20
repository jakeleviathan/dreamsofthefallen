from __future__ import annotations

import re
from dataclasses import dataclass

from mud.npc_name_audit import likely_given_name


@dataclass(frozen=True, slots=True)
class TalkMatch:
    key: str
    name: str
    dialogue: tuple[str, ...]
    role: str = ""
    mobile: bool = False


def _normalize(value: str) -> str:
    return " ".join(
        re.findall(r"[a-z0-9]+", (value or "").casefold().replace("-", " "))
    )


def _talk_target(command: str) -> str:
    stripped = command.strip()
    if not stripped:
        return ""
    pieces = stripped.split(maxsplit=1)
    if not pieces or pieces[0].casefold() != "talk":
        return ""
    target = pieces[1] if len(pieces) > 1 else ""
    normalized = target.strip()
    if normalized.casefold().startswith("to "):
        normalized = normalized[3:].strip()
    return normalized


def _static_aliases(npc) -> set[str]:
    aliases: set[str] = set()
    full = _normalize(getattr(npc, "name", ""))
    if full:
        aliases.add(full)

    given = likely_given_name(
        getattr(npc, "name", ""),
        getattr(npc, "role", ""),
    )
    if given:
        aliases.add(_normalize(given))

    # A visible proper-name component should be usable as a MUD talk target.
    # This deliberately excludes one-letter fragments while allowing surnames
    # and hyphenated name components such as "Somn" from "Somn-of-Rain".
    for token in re.findall(r"[A-Za-z][A-Za-z'-]*", getattr(npc, "name", "")):
        for part in re.split(r"[-']", token):
            normalized = _normalize(part)
            if len(normalized) >= 2:
                aliases.add(normalized)

    words = full.split()
    for index in range(len(words)):
        suffix = " ".join(words[index:])
        if suffix:
            aliases.add(suffix)
    return aliases


def _mobile_aliases(definition) -> set[str]:
    aliases = {_normalize(getattr(definition, "name", ""))}
    aliases.update(
        _normalize(alias)
        for alias in getattr(definition, "aliases", ())
        if _normalize(alias)
    )
    words = _normalize(getattr(definition, "name", "")).split()
    aliases.update(word for word in words if len(word) >= 2)
    return {alias for alias in aliases if alias}


def visible_static_npcs(world_service, npcs_by_key, room_key: str):
    scene = world_service.scene(room_key) if world_service is not None else None
    if scene is None:
        return ()
    return tuple(
        npcs_by_key[key]
        for key in getattr(scene, "npc_keys", ())
        if key in npcs_by_key
    )


def resolve_static_talk_target(world_service, npcs_by_key, room_key: str, target: str):
    query = _normalize(target)
    if not query:
        return None, ()

    candidates = []
    for npc in visible_static_npcs(world_service, npcs_by_key, room_key):
        aliases = _static_aliases(npc)
        if query in aliases:
            candidates.append(npc)

    if len(candidates) == 1:
        return candidates[0], ()
    if len(candidates) > 1:
        return None, tuple(sorted(npc.name for npc in candidates))

    # If there is no exact alias, allow a unique prefix over authored names.
    # Exact first/full/surname matching above always wins.
    prefix_matches = []
    for npc in visible_static_npcs(world_service, npcs_by_key, room_key):
        full = _normalize(npc.name)
        if full.startswith(query) or any(
            word.startswith(query) for word in full.split()
        ):
            prefix_matches.append(npc)
    if len(prefix_matches) == 1:
        return prefix_matches[0], ()
    if len(prefix_matches) > 1:
        return None, tuple(sorted(npc.name for npc in prefix_matches))
    return None, ()


def resolve_mobile_talk_target(session, target: str):
    query = _normalize(target)
    character = getattr(session, "character", None)
    manager = getattr(session, "mobile_npcs", None)
    if not query or character is None or manager is None:
        return None, ()

    candidates = []
    for state in getattr(manager, "states", {}).values():
        if not getattr(state, "active", True):
            continue
        if state.current_room_key != character.current_room:
            continue
        aliases = _mobile_aliases(state.definition)
        if query in aliases:
            candidates.append(state.definition)

    if len(candidates) == 1:
        return candidates[0], ()
    if len(candidates) > 1:
        return None, tuple(sorted(definition.name for definition in candidates))
    return None, ()


async def _speak_generic(session, npc) -> None:
    dialogue = tuple(getattr(npc, "dialogue", ()) or ())
    await session.send("\r\n")
    if dialogue:
        for line in dialogue:
            await session.send(line + "\r\n")
        return

    role = str(getattr(npc, "role", "") or "").strip()
    if role:
        await session.send(
            f"{npc.name} acknowledges you, but has nothing more to add right now. "
            f"({role})\r\n"
        )
    else:
        await session.send(f"{npc.name} acknowledges you, but has nothing more to say right now.\r\n")


def static_npc_talkability_problems(world_service, npcs_by_key) -> tuple[str, ...]:
    """Audit the final static NPC registry against the final visible room graph."""

    problems: list[str] = []
    for key, npc in sorted(npcs_by_key.items()):
        room_key = getattr(npc, "room_key", "") or ""
        scene = world_service.scene(room_key) if room_key else None
        if scene is None:
            problems.append(f"{key}: room {room_key!r} does not exist")
            continue
        if key not in getattr(scene, "npc_keys", ()):
            problems.append(
                f"{key}: {npc.name!r} claims room {room_key!r} but is not visible in that room's NPC list"
            )
            continue

        # Full display name must always target the NPC.
        resolved, ambiguous = resolve_static_talk_target(
            world_service, npcs_by_key, room_key, npc.name
        )
        if resolved is None or resolved.key != key:
            problems.append(
                f"{key}: full-name TALK target {npc.name!r} does not resolve uniquely"
                + (f" ({', '.join(ambiguous)})" if ambiguous else "")
            )

        # When a personal given name is identifiable, the global name uniqueness
        # invariant means it should also be a safe TALK target.
        given = likely_given_name(npc.name, getattr(npc, "role", ""))
        if given:
            resolved, ambiguous = resolve_static_talk_target(
                world_service, npcs_by_key, room_key, given
            )
            if resolved is None or resolved.key != key:
                problems.append(
                    f"{key}: given-name TALK target {given!r} does not resolve uniquely"
                    + (f" ({', '.join(ambiguous)})" if ambiguous else "")
                )
    return tuple(problems)


def validate_static_npc_talkability(world_service, npcs_by_key) -> int:
    problems = static_npc_talkability_problems(world_service, npcs_by_key)
    if problems:
        raise RuntimeError(
            "Static NPC talkability audit failed:\n- " + "\n- ".join(problems)
        )
    return len(npcs_by_key)


async def _delegate_prompt(session, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in session.__dict__
    previous_instance_prompt = session.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    session.prompt = replay_prompt
    try:
        await previous_prompt(session)
    finally:
        if had_prompt:
            session.prompt = previous_instance_prompt
        else:
            session.__dict__.pop("prompt", None)


def install_generic_npc_conversation_runtime(
    player_session_class,
    world_service,
    npcs_by_key,
) -> None:
    """Guarantee that every visible authored NPC can be spoken to.

    This layer is intentionally installed *inside* quest/content talk handlers.
    Specialized runtimes therefore get first chance to advance quests or show
    state-specific dialogue. If none handles the command, this fallback resolves
    the visible NPC and shows their ordinary authored dialogue instead of lying
    that nobody by that name is present.
    """

    if getattr(player_session_class, "_generic_npc_conversation_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return

        target = _talk_target(command)
        if not target and command.strip().casefold() == "talk":
            await self.send("Talk to whom?\r\n")
            return

        if target:
            room_key = self.character.current_room or ""
            npc, ambiguous = resolve_static_talk_target(
                world_service,
                npcs_by_key,
                room_key,
                target,
            )
            if ambiguous:
                await self.send(
                    "That name matches more than one person here: "
                    + ", ".join(ambiguous)
                    + ". Be more specific.\r\n"
                )
                return
            if npc is not None:
                await _speak_generic(self, npc)
                return

            mobile, mobile_ambiguous = resolve_mobile_talk_target(self, target)
            if mobile_ambiguous:
                await self.send(
                    "That name matches more than one nearby figure: "
                    + ", ".join(mobile_ambiguous)
                    + ". Be more specific.\r\n"
                )
                return
            if mobile is not None:
                await self.send(
                    f"{mobile.name} is here, but does not respond to conversation.\r\n"
                )
                return

        await _delegate_prompt(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._generic_npc_conversation_runtime_installed = True
