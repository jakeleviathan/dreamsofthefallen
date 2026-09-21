from __future__ import annotations

from time import time

import mud.room_runtime as room_runtime
from mud.actor_inspection import install_actor_inspection_runtime
from mud.astralis_human_district import HUMAN_DISTRICT
from mud.astralis_time import ASTRALIS_CLOCK, puddle_available
from mud.combat import ENEMIES_BY_KEY
from mud.consider import install_consider_runtime
from mud.contextual_command_routing import install_contextual_command_routing_guard
from mud.corpse_decay import corpse_decay_label
from mud.corpse_loot import list_corpses
from mud.database import Database
from mud.enemy_lifecycle import iter_static_enemy_spawns, static_enemy_available
from mud.exploration_map import install_exploration_map_runtime
from mud.exploration_map_gmcp import install_exploration_map_gmcp_runtime
from mud.fantasy_drugs import install_perception_runtime
from mud.final_runtime_policy import install_final_runtime_policy
from mud.goblin_swamp import (
    GOBLIN_APOTHECARY_BLIND_KEY,
    GOBLIN_SWAMP_GATHERING,
    GOBLIN_SWAMP_ROOM_KEYS,
    _handle_swamp_gathering,
)
from mud.inventory_inspection import install_inventory_inspection_runtime
from mud.mana_regeneration import install_mana_regeneration_runtime
from mud.movement_system import install_movement_runtime
from mud.partial_target_matching import install_partial_target_matching_runtime
from mud.quest_experience import install_quest_experience_runtime
from mud.room_engine import PlayerRoomContext
from mud.style_collectibles import (
    PAVO_ATELIER_NAME,
    PAVO_NAME,
    PAVO_SHORT_DESCRIPTION,
    style_atelier_available,
)
from mud.world import NPCS_BY_KEY


RESET = "\x1b[0m"
TITLE = "\x1b[1;93m"
REGION = "\x1b[90m"
BODY = "\x1b[37m"
FEATURE = "\x1b[96m"
NPC = "\x1b[92m"
CREATURE = "\x1b[93m"
HOSTILE = "\x1b[1;91m"
# Compatibility alias for older imports. New room presentation uses CREATURE
# for attackable-but-passive beings and HOSTILE only for on-sight aggressors.
ENEMY = HOSTILE
CORPSE = "\x1b[33m"
EXIT = "\x1b[94m"
BUSINESS = "\x1b[95m"
DIVIDER = "\x1b[90m"


_SWAMP_GATHERING_COMMANDS = {
    "gather",
    "harvest",
    "herbalism",
    "herbs",
    "pick",
    "collect",
    "fill",
}


def _paint(style: str, text: str) -> str:
    return f"{style}{text}{RESET}"


def _region_label(region_key: str) -> str:
    return region_key.replace("_", " ").strip().title()


def _context_for(session) -> PlayerRoomContext:
    character = session.character
    moment = ASTRALIS_CLOCK.now()
    return PlayerRoomContext(
        character_id=character.id,
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=character.level,
        character_flags=frozenset(session.database.list_flags(character.id)),
        hour=moment.hour,
    )


def _section_header(label: str, color: str) -> str:
    return _paint(color, f"[ {label} ]")


def render_room_lines(session, world_service) -> tuple[str, ...]:
    """Return one consistently formatted, ANSI-colored room view."""

    character = getattr(session, "character", None)
    if character is None:
        return ()

    view = world_service.build_view(character.current_room or "", _context_for(session))
    if view is None:
        return ()

    scene = world_service.scene(view.key)
    if scene is None:
        return ()

    lines: list[str] = [
        "",
        _paint(TITLE, view.name),
        _paint(REGION, _region_label(scene.region_key)),
        _paint(DIVIDER, "-" * 64),
    ]

    for index, paragraph in enumerate(view.description.split("\n\n")):
        if index:
            lines.append("")
        lines.append(_paint(BODY, paragraph.replace("\n", " ")))

    has_puddle = puddle_available(view.key, scene.region_key, world_service.state)
    business = HUMAN_DISTRICT.business_in_room(view.key)
    has_style_atelier = style_atelier_available(world_service, view.key)

    notable: list[str] = []
    for feature in view.features:
        detail = f"  {_paint(FEATURE, feature.name)}"
        if feature.summary:
            detail += f" - {feature.summary}"
        notable.append(detail)
    if has_puddle:
        notable.append(
            f"  {_paint(FEATURE, 'Puddle')} - fresh rainwater deep enough to hold your reflection"
        )
    if business is not None:
        notable.append(
            f"  {_paint(BUSINESS, business.name)} - {business.storefront_description}"
        )
    if has_style_atelier:
        notable.append(
            f"  {_paint(BUSINESS, PAVO_ATELIER_NAME)} - mirrors, draped garment forms, "
            "and a brass placard offering permanent STYLE COPY service"
        )

    if notable:
        lines.extend(["", _section_header("Notable", FEATURE), *notable])

    people: list[str] = []
    creature_records: list[tuple[str, str]] = []
    hostile_records: list[tuple[str, str]] = []
    for npc_key in scene.npc_keys:
        npc = NPCS_BY_KEY.get(npc_key)
        if npc is not None:
            people.append(f"  {_paint(NPC, npc.name)} - {npc.short_description}")
    if has_style_atelier:
        people.append(f"  {_paint(NPC, PAVO_NAME)} - {PAVO_SHORT_DESCRIPTION}")

    mobile_npcs = getattr(session, "mobile_npcs", None)
    if mobile_npcs is not None:
        static_names = {NPCS_BY_KEY[key].name for key in scene.npc_keys if key in NPCS_BY_KEY}
        for state in mobile_npcs.npcs_in_room(view.key):
            definition = state.definition
            aggressive = bool(getattr(definition, "aggressive", False))
            attackable = bool(getattr(definition, "attackable", False))
            if aggressive:
                hostile_records.append((definition.name, definition.short_description))
            elif attackable:
                creature_records.append((definition.name, definition.short_description))
            elif definition.name not in static_names:
                people.append(
                    f"  {_paint(NPC, definition.name)} - {definition.short_description}"
                )

    if people:
        lines.extend(["", _section_header("People", NPC), *people])

    # Authored room enemies do not auto-aggro merely because they can fight.
    # They therefore belong under Creatures. Only mobile definitions explicitly
    # marked aggressive appear under Hostile.
    for enemy_key, spawn_key in iter_static_enemy_spawns(scene.enemy_keys):
        enemy = ENEMIES_BY_KEY.get(enemy_key)
        if enemy is not None and static_enemy_available(
            view.key,
            spawn_key,
            database=getattr(session, "database", None),
        ):
            creature_records.append((enemy.name, enemy.description))

    def append_actor_section(label: str, color: str, records: list[tuple[str, str]]) -> None:
        if not records:
            return
        # One rendered line represents one actual creature/NPC instance. Do not
        # collapse duplicates into x2/x3 shorthand because each can have its own
        # combat and lifecycle state.
        rendered = [
            f"  {_paint(color, name)} - {description}"
            for name, description in records
        ]
        lines.extend(["", _section_header(label, color), *rendered])

    append_actor_section("Creatures", CREATURE, creature_records)
    append_actor_section("Hostile", HOSTILE, hostile_records)

    database = getattr(session, "database", None)
    current = time()
    corpses = (
        list_corpses(database, view.key, now=current)
        if database is not None and callable(getattr(database, "connect", None))
        else []
    )
    if corpses:
        counts: dict[str, int] = {}
        for corpse in corpses:
            counts[corpse.enemy_name] = counts.get(corpse.enemy_name, 0) + 1
        seen: dict[str, int] = {}
        corpse_lines: list[str] = []
        for corpse in corpses:
            seen[corpse.enemy_name] = seen.get(corpse.enemy_name, 0) + 1
            suffix = f" #{seen[corpse.enemy_name]}" if counts[corpse.enemy_name] > 1 else ""
            decay = corpse_decay_label(corpse, now=current)
            corpse_lines.append(
                f"  {_paint(CORPSE, f'Corpse of {corpse.enemy_name}{suffix} ({decay})')}"
            )
        lines.extend(["", _section_header("Corpses", CORPSE), *corpse_lines])

    if business is not None:
        moment = ASTRALIS_CLOCK.now()
        status_lines = HUMAN_DISTRICT.storefront_lines(
            view.key,
            world_service.state,
            moment.hour,
            moment.day_number,
        )
        if status_lines:
            lines.extend(["", _section_header("Business", BUSINESS)])
            lines.extend(f"  {_paint(REGION, line)}" for line in status_lines)

    if view.exits:
        lines.extend(["", _section_header("Exits", EXIT)])
        for exit_view in view.exits:
            direction = _paint(EXIT, exit_view.direction.upper())
            destination = exit_view.name or exit_view.destination_key
            lines.append(f"  {direction:<16} -> {destination}")

    lines.append("")
    return tuple(lines)


async def _capture_send_calls(session, render) -> list[str]:
    """Capture one room-render pass without affecting other player sessions."""

    captured: list[str] = []
    had_instance_send = "send" in session.__dict__
    prior_instance_send = session.__dict__.get("send")

    async def capture(text: str) -> None:
        captured.append(text)

    session.send = capture
    try:
        await render()
    finally:
        if had_instance_send:
            session.send = prior_instance_send
        else:
            session.__dict__.pop("send", None)
    return captured


def _remove_contiguous_subsequence(full: list[str], core: list[str]) -> list[str]:
    """Remove the legacy room core while retaining pre/post authored overlays."""

    if not core:
        return full
    width = len(core)
    for index in range(0, len(full) - width + 1):
        if full[index : index + width] == core:
            return full[:index] + full[index + width :]
    return []


async def _legacy_room_overlays(session, original_show_current_room) -> list[str]:
    """Run the old presentation chain once and return only its overlay output."""

    async def no_fallback(_session) -> None:
        return None

    core = await _capture_send_calls(
        session,
        lambda: room_runtime._render_current_room(session, no_fallback),
    )
    full = await _capture_send_calls(session, lambda: original_show_current_room(session))
    return _remove_contiguous_subsequence(full, core)


async def _show_goblin_swamp_resources(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return

    room_key = character.current_room or ""
    nodes = GOBLIN_SWAMP_GATHERING.nodes_in_room(room_key)

    await session.send("\r\n--- Local Economy ---\r\n")
    if nodes:
        await session.send("Resources:\r\n")
        for state in nodes:
            definition = state.definition
            resource = definition.resource
            if resource is None:
                requirement = "Collect"
            else:
                label = resource.gathering_skill_key.replace("_", " ").title()
                requirement = f"{label} {resource.minimum_skill}"
            status = (
                "depleted"
                if state.remaining_uses <= 0
                else f"{state.remaining_uses} uses available"
            )
            await session.send(
                f"- {definition.name} [{requirement}] - {status}\r\n"
            )
    else:
        await session.send("Resources: none in this room.\r\n")

    if room_key == GOBLIN_APOTHECARY_BLIND_KEY:
        await session.send(
            "Stations: Field Alchemy Bench (Mortar and Pestle, Alchemy Table).\r\n"
        )
    else:
        await session.send("Stations: none in this room.\r\n")

    await session.send(
        "Use GATHER <resource>, HERBALISM, or COLLECT WATER as appropriate.\r\n"
    )


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_goblin_swamp_gathering_bridge(player_session_class) -> None:
    """Keep the authored Goblin swamp nodes authoritative over generic economy routing."""

    if getattr(player_session_class, "_goblin_swamp_gathering_bridge_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None or character.current_room not in GOBLIN_SWAMP_ROOM_KEYS:
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            disconnected = getattr(type(state), "DISCONNECTED", None) if state is not None else None
            if disconnected is not None:
                self.state = disconnected
            return

        normalized = " ".join(command.strip().lower().split())
        if normalized in {"resources", "resource", "nodes"}:
            await _show_goblin_swamp_resources(self)
            return

        first = normalized.split(maxsplit=1)[0] if normalized else ""
        if first in _SWAMP_GATHERING_COMMANDS:
            canonical = normalized
            if first == "herbs":
                canonical = "herbalism" + normalized[len(first):]
            if await _handle_swamp_gathering(self, canonical):
                return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._goblin_swamp_gathering_bridge_installed = True


def install_room_presentation_runtime(player_session_class, world_service) -> None:
    """Make final progression/travel systems and color room rendering player-facing."""

    install_movement_runtime(player_session_class, world_service)
    install_mana_regeneration_runtime(player_session_class, world_service)
    install_quest_experience_runtime(player_session_class, Database)
    install_contextual_command_routing_guard(player_session_class)

    if getattr(player_session_class, "_room_presentation_runtime_installed", False):
        return

    original_show_current_room = player_session_class.show_current_room

    async def show_current_room(self) -> None:
        lines = render_room_lines(self, world_service)
        if not lines:
            await original_show_current_room(self)
            return

        overlays = await _legacy_room_overlays(self, original_show_current_room)
        await self.send("\r\n".join(lines) + "\r\n")
        for text in overlays:
            await self.send(text)

    player_session_class.show_current_room = show_current_room
    player_session_class._room_presentation_runtime_installed = True

    install_inventory_inspection_runtime(player_session_class)
    install_perception_runtime(player_session_class, world_service)
    install_actor_inspection_runtime(player_session_class, world_service)
    install_consider_runtime(player_session_class, world_service)
    install_exploration_map_runtime(player_session_class, world_service)
    install_exploration_map_gmcp_runtime(player_session_class, world_service)
    install_partial_target_matching_runtime(player_session_class, world_service)
    install_goblin_swamp_gathering_bridge(player_session_class)

    # Final cross-cutting policies are deliberately installed after every room,
    # perception, mapper and command wrapper so saved accessibility/client choices
    # remain authoritative regardless of which subsystem produced the output.
    install_final_runtime_policy(player_session_class)
