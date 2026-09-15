from __future__ import annotations

from mud.astralis_human_district import HUMAN_DISTRICT
from mud.astralis_time import ASTRALIS_CLOCK, puddle_available
from mud.combat import ENEMIES_BY_KEY
from mud.contextual_command_routing import install_contextual_command_routing_guard
from mud.database import Database
from mud.fantasy_drugs import install_perception_runtime
from mud.inventory_inspection import install_inventory_inspection_runtime
from mud.movement_system import install_movement_runtime
from mud.partial_target_matching import install_partial_target_matching_runtime
from mud.quest_experience import install_quest_experience_runtime
from mud.room_engine import PlayerRoomContext
from mud.world import NPCS_BY_KEY


RESET = "\x1b[0m"
TITLE = "\x1b[1;93m"
REGION = "\x1b[90m"
BODY = "\x1b[37m"
FEATURE = "\x1b[96m"
NPC = "\x1b[92m"
ENEMY = "\x1b[1;91m"
EXIT = "\x1b[94m"
BUSINESS = "\x1b[95m"
DIVIDER = "\x1b[90m"


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
    """Return one consistently formatted, ANSI-colored room view.

    The renderer deliberately colors labels and important nouns rather than whole
    paragraphs. This keeps the traditional MUD reading experience intact while
    making rooms much easier to scan in Mudlet and ordinary ANSI-capable Telnet
    clients.
    """

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

    # Preserve authored paragraph breaks, but give the prose its own visual block.
    for index, paragraph in enumerate(view.description.split("\n\n")):
        if index:
            lines.append("")
        lines.append(_paint(BODY, paragraph.replace("\n", " ")))

    has_puddle = puddle_available(view.key, scene.region_key, world_service.state)
    business = HUMAN_DISTRICT.business_in_room(view.key)

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

    if notable:
        lines.extend(["", _section_header("Notable", FEATURE), *notable])

    people: list[str] = []
    for npc_key in scene.npc_keys:
        npc = NPCS_BY_KEY.get(npc_key)
        if npc is not None:
            people.append(f"  {_paint(NPC, npc.name)} - {npc.short_description}")

    mobile_npcs = getattr(session, "mobile_npcs", None)
    if mobile_npcs is not None:
        static_names = {NPCS_BY_KEY[key].name for key in scene.npc_keys if key in NPCS_BY_KEY}
        for state in mobile_npcs.npcs_in_room(view.key):
            if state.definition.name not in static_names:
                people.append(
                    f"  {_paint(NPC, state.definition.name)} - {state.definition.short_description}"
                )

    if people:
        lines.extend(["", _section_header("People", NPC), *people])

    threats: list[str] = []
    for enemy_key in scene.enemy_keys:
        enemy = ENEMIES_BY_KEY.get(enemy_key)
        if enemy is not None:
            threats.append(f"  {_paint(ENEMY, enemy.name)} - {enemy.description}")
    if threats:
        lines.extend(["", _section_header("Danger", ENEMY), *threats])

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


def install_room_presentation_runtime(player_session_class, world_service) -> None:
    """Make final progression/travel systems and color room rendering player-facing."""

    # Room presentation is the final production assembly hook. Install travel and
    # quest-progression systems here so all authored quest/movement wrappers are
    # already assembled underneath them.
    install_movement_runtime(player_session_class, world_service)
    install_quest_experience_runtime(player_session_class, Database)

    # Scope older global verb fallbacks before the final prompt wrappers are
    # installed. This keeps SEARCH/LISTEN/CLIMB/PULL/TOUCH owned by the content
    # that actually authored the current room instead of allowing Waymeet's
    # helpful local fallback text to swallow commands elsewhere in Astralis.
    install_contextual_command_routing_guard(player_session_class)

    if getattr(player_session_class, "_room_presentation_runtime_installed", False):
        return

    original_show_current_room = player_session_class.show_current_room

    async def show_current_room(self) -> None:
        lines = render_room_lines(self, world_service)
        if not lines:
            await original_show_current_room(self)
            return
        await self.send("\r\n".join(lines) + "\r\n")

    player_session_class.show_current_room = show_current_room
    player_session_class._room_presentation_runtime_installed = True

    # ITEM/INSPECT ITEM becomes universal before perception wraps the prompt loop:
    # equipment still gets slot/stat details, while quest items, materials and
    # curios finally expose their authored description too.
    install_inventory_inspection_runtime(player_session_class)

    # Altered perception is intentionally outermost over ordinary item/room state:
    # the world remains authoritative, while this layer can add subjective prose
    # and richer recreational-drug inspection without falsifying real inventory.
    install_perception_runtime(player_session_class, world_service)

    # Input matching sits outside every authored TALK/ATTACK/item handler. A unique
    # visible abbreviation such as TALK RIVETER, TALK NIX, KILL STALK, ITEM TOKEN,
    # or EQUIP SCRAP can be expanded to the full displayed name before the existing
    # quest, combat, inventory, or equipment runtime sees it. Ambiguity is never
    # guessed.
    install_partial_target_matching_runtime(player_session_class, world_service)
