from __future__ import annotations

import re
from dataclasses import dataclass

from mud.combat import ENEMIES_BY_KEY
from mud.world import NPCS_BY_KEY


_NON_WORD = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class TargetCandidate:
    key: str
    name: str
    kind: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TargetResolution:
    command: str
    matched_name: str | None = None
    ambiguous_names: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.matched_name is not None and not self.ambiguous_names

    @property
    def ambiguous(self) -> bool:
        return bool(self.ambiguous_names)


def normalize_target(text: str) -> str:
    """Normalize player-facing names without exposing internal object keys."""

    return " ".join(_NON_WORD.sub(" ", text.lower()).split())


def _search_terms(candidate: TargetCandidate) -> tuple[str, ...]:
    terms: list[str] = []
    for raw in (candidate.name, *candidate.aliases):
        normalized = normalize_target(raw)
        if normalized and normalized not in terms:
            terms.append(normalized)
    return tuple(terms)


def _match_score(query: str, candidate: TargetCandidate) -> int:
    """Return a deterministic score for a traditional-MUD-style abbreviation.

    Exact authored names/aliases win first. Otherwise a player may type a
    distinctive whole word (NIX, RIVETER, RAT), a trailing phrase (NIX HOOK), or
    a unique prefix (RIV, HOOKS, SEW). One-character prefixes are deliberately
    not expanded because they are too easy to trigger accidentally.
    """

    if not query:
        return 0

    terms = _search_terms(candidate)
    if query in terms:
        return 100

    best = 0
    for term in terms:
        words = term.split()
        if query in words:
            best = max(best, 90)

        for index in range(len(words)):
            suffix = " ".join(words[index:])
            if suffix == query:
                best = max(best, 90)
            elif len(query) >= 2 and suffix.startswith(query):
                best = max(best, 75)

        if len(query) >= 2 and term.startswith(query):
            best = max(best, 80)
        if len(query) >= 2 and any(word.startswith(query) for word in words):
            best = max(best, 60)

    return best


def _dedupe_candidates(candidates: list[TargetCandidate]) -> tuple[TargetCandidate, ...]:
    # Multiple systems can surface the same named actor (for example a static
    # room listing plus a mobile state). The player only sees one name, so do not
    # create a fake ambiguity merely because two registries describe it.
    deduped: dict[tuple[str, str], TargetCandidate] = {}
    for candidate in candidates:
        identity = (candidate.kind, normalize_target(candidate.name))
        current = deduped.get(identity)
        if current is None:
            deduped[identity] = candidate
            continue
        aliases = tuple(dict.fromkeys((*current.aliases, *candidate.aliases)))
        deduped[identity] = TargetCandidate(
            key=current.key,
            name=current.name,
            kind=current.kind,
            aliases=aliases,
        )
    return tuple(deduped.values())


def visible_target_candidates(session, world_service, *, kind: str) -> tuple[TargetCandidate, ...]:
    """Return only actors that the current command is allowed to address."""

    character = getattr(session, "character", None)
    if character is None:
        return ()
    room_key = character.current_room or ""
    scene = world_service.scene(room_key)
    candidates: list[TargetCandidate] = []

    if scene is not None:
        if kind == "npc":
            for npc_key in scene.npc_keys:
                npc = NPCS_BY_KEY.get(npc_key)
                if npc is not None:
                    candidates.append(TargetCandidate(npc.key, npc.name, "npc"))
        elif kind == "enemy":
            for enemy_key in scene.enemy_keys:
                enemy = ENEMIES_BY_KEY.get(enemy_key)
                if enemy is not None:
                    candidates.append(
                        TargetCandidate(enemy.key, enemy.name, "enemy", tuple(enemy.aliases))
                    )

    mobile_npcs = getattr(session, "mobile_npcs", None)
    if mobile_npcs is not None:
        for state in mobile_npcs.npcs_in_room(room_key):
            definition = state.definition
            if kind == "npc":
                candidates.append(
                    TargetCandidate(
                        definition.key,
                        definition.name,
                        "npc",
                        tuple(getattr(definition, "aliases", ())),
                    )
                )
            elif kind == "enemy" and bool(getattr(definition, "aggressive", False)):
                candidates.append(
                    TargetCandidate(
                        definition.key,
                        definition.name,
                        "enemy",
                        tuple(getattr(definition, "aliases", ())),
                    )
                )

    return _dedupe_candidates(candidates)


def _parse_target_command(command: str) -> tuple[str, str, str] | None:
    stripped = command.strip()
    normalized = " ".join(stripped.lower().split())

    # SPEAK is accepted as a convenience synonym and canonicalized to TALK so it
    # reaches older authored quest handlers that only registered TALK.
    for prefix in ("talk to ", "talk ", "speak to ", "speak "):
        if normalized.startswith(prefix):
            target = stripped[len(prefix):].strip()
            return "talk", target, "npc"

    for prefix in ("attack ", "kill "):
        if normalized.startswith(prefix):
            target = stripped[len(prefix):].strip()
            return prefix.strip(), target, "enemy"

    return None


def resolve_target_command(session, command: str, world_service) -> TargetResolution:
    """Expand a unique room-local NPC/enemy abbreviation to its visible name."""

    parsed = _parse_target_command(command)
    if parsed is None:
        return TargetResolution(command)

    verb, raw_target, kind = parsed
    query = normalize_target(raw_target)
    if not query:
        return TargetResolution(command)

    candidates = visible_target_candidates(session, world_service, kind=kind)
    scored = [(_match_score(query, candidate), candidate) for candidate in candidates]
    scored = [(score, candidate) for score, candidate in scored if score > 0]
    if not scored:
        return TargetResolution(command)

    best_score = max(score for score, _candidate in scored)
    best = [candidate for score, candidate in scored if score == best_score]
    best_names = tuple(sorted({candidate.name for candidate in best}, key=str.lower))
    if len(best_names) > 1:
        return TargetResolution(command, ambiguous_names=best_names)

    candidate = best[0]
    canonical = f"{verb} {candidate.name}"
    # Leave an already-canonical command alone. This matters for telemetry and
    # prevents cosmetic rewrites from making ordinary full-name input look new.
    if normalize_target(raw_target) == normalize_target(candidate.name) and verb == command.strip().split(maxsplit=1)[0].lower():
        return TargetResolution(command)
    return TargetResolution(canonical, matched_name=candidate.name)


def install_partial_target_matching_runtime(player_session_class, world_service) -> None:
    """Expand unique NPC/enemy abbreviations before any authored command layer.

    Wrapping prompt rather than one particular TALK implementation is deliberate:
    Dreams of the Fallen has many quest runtimes, each with its own authored NPC
    dialogue. The rewritten full visible name therefore flows through the same
    handler the player would have reached by typing the complete name manually.
    """

    if getattr(player_session_class, "_partial_target_matching_runtime_installed", False):
        return

    original_prompt = player_session_class.prompt

    async def prompt(self, text: str):
        next_prompt = text
        while True:
            command = await original_prompt(self, next_prompt)
            if command is None:
                return None

            character = getattr(self, "character", None)
            state = getattr(self, "state", None)
            # Avoid touching account, character-creation, roster, confirmation,
            # or other non-gameplay prompts. SessionState is intentionally not
            # imported here so this module stays free of a session import cycle.
            if character is None or getattr(state, "name", "") != "PLAYING":
                return command

            resolution = resolve_target_command(self, command, world_service)
            if not resolution.ambiguous:
                return resolution.command

            choices = ", ".join(resolution.ambiguous_names)
            await self.send(
                f"That abbreviation matches more than one target: {choices}. Be more specific.\r\n"
            )
            next_prompt = "\r\n> "

    player_session_class.prompt = prompt
    player_session_class._partial_target_matching_runtime_installed = True
