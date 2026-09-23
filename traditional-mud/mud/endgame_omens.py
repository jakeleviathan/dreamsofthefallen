"""Quiet early-game threads for the future Hinge and Unstruck Bell story.

The mural, chalk, child's refrain and clapperless bell are optional. They are
not quest prerequisites and deliberately do not name the later gateway. The
shared discovery journal and collective wiki remember real player interactions.
"""
from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.discovery_engine import (
    DiscoveryCondition,
    DiscoveryDefinition,
    DiscoveryRegistry,
    _delegate_prompt,
    _parse_command,
    attempt_discovery_command,
    discovered_keys,
)
from mud.goblin_start import GOBLIN_PATCHWORK_PLAZA_KEY
from mud.roadside_discoveries import QUIET_BELFRY_KEY, NOON_LENS_KEY
from mud.room_engine import DescriptionLayer, FeatureDefinition, RoomAugmentation
from mud.waymeet_frontier import (
    WAYMEET_COMMONHOUSE_KEY,
    WAYMEET_CROSSROADS_KEY,
    WAYMEET_LANTERN_MARKET_KEY,
)
from mud.world import NpcDefinition


CLAPPERLESS_BELL_KEY = "omen_clapperless_waybell"
BURIED_MURAL = "omen:buried_mural"
CHALK_CIPHER = "omen:chalk_cipher"
CHILD_REFRAIN = "omen:child_refrain"
BELL_RESONANCE = "omen:bell_resonance"
EMPTY_BELFRY = "omen:empty_belfry"
BELL_COMPARISON = "omen:bell_comparison"
NOON_ALIGNMENT = "omen:noon_alignment"
MISSING_NOTE = "omen:missing_note"

CLAPPERLESS_BELL = ItemDefinition(
    key=CLAPPERLESS_BELL_KEY,
    name="Clapperless Waybell",
    description=(
        "A palm-sized bronze travel bell with no clapper and no maker's mark. "
        "Four short notches surround one unusually smooth patch inside its rim. "
        "It was sold as a useless roadside curiosity."
    ),
    category="curio",
    tier=1,
)

PELLA = NpcDefinition(
    key="waymeet_child_pella_dawnskein",
    name="Pella Dawnskein",
    short_description=(
        "a curious child sorting painted road pebbles and humming an unfinished tune"
    ),
    room_key=WAYMEET_COMMONHOUSE_KEY,
    role="Commonhouse child and keeper of a half-remembered road song",
    dialogue=(
        "Pella lines up four colored pebbles. 'These are the four roads. "
        "This one's for the road that isn't there. My grandma says I made it up.'",
        "She hums four clear notes, pauses for a fifth, then shrugs. "
        "'Grandma always stopped there. She said the rest wasn't ours to sing.'",
        "'If you find a better ending, tell me when you're back. "
        "People always come back through Waymeet.'",
    ),
)


def _feature(
    key: str, name: str, summary: str, examine: str, *,
    aliases: tuple[str, ...] = (),
    listen: str = "",
    search: str = "",
    touch: str = "",
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        summary=summary,
        examine_text=examine,
        aliases=aliases,
        listen_text=listen,
        search_text=search,
        touch_text=touch,
    )


OMEN_FEATURES: dict[str, tuple[FeatureDefinition, ...]] = {
    GOBLIN_PATCHWORK_PLAZA_KEY: (
        _feature(
            "omen_buried_mural",
            "Buried Rivet Mural",
            "the curved edge of a very old mosaic beneath patched paving",
            "Most of the mosaic is beneath salvage-built shops. What remains is "
            "a circular border, four roads converging on an empty center, and "
            "a row of five sockets where the last stone has been removed.",
            aliases=("mural", "mosaic", "old mural", "rivet mural"),
            search="Newer Goblin claim marks cross much older stonework. Nobody "
                   "has bothered to claim the buried portion.",
        ),
    ),
    WAYMEET_CROSSROADS_KEY: (
        _feature(
            "omen_chalk_ciphers",
            "Weathered Chalk Marks",
            "small courier-like symbols half-hidden beneath a bridge repair notice",
            "At a glance these look like freight marks. But there are five "
            "repeated spaces for only four road signs, and the fifth is "
            "always filled with a short downward stroke.",
            aliases=("chalk marks", "graffiti", "chalk", "symbols"),
            search="Someone has renewed these marks over much older scratches.",
        ),
    ),
    WAYMEET_COMMONHOUSE_KEY: (
        _feature(
            "omen_commonhouse_refrain",
            "Children's Road Song",
            "children at the steps playing a four-road counting game",
            "The children trade rhymes and painted pebbles while the adults "
            "talk about broken wagons and tonight's meals. Pella keeps "
            "stopping her tune one note before the others expect it.",
            aliases=("children", "road song", "humming", "song"),
            listen="Four bright notes rise from the steps, followed by a "
                   "deliberate silence where a fifth ought to be.",
        ),
    ),
    WAYMEET_LANTERN_MARKET_KEY: (
        _feature(
            "omen_curio_rumor",
            "Curio Gossip",
            "a handful of road traders arguing about objects with no obvious use",
            "The copper-painted caravan sometimes brings bells without "
            "clappers, broken compasses, and other things merchants call "
            "worthless until someone starts asking questions.",
            aliases=("curios", "gossip", "road traders"),
        ),
    ),
    QUIET_BELFRY_KEY: (
        _feature(
            "omen_belfry_notches",
            "Belfry Bolt Notches",
            "a pattern of four close marks and one smooth gap behind the empty frame",
            "The marks were cut before the heavy oak frame was installed. "
            "Someone used the pattern as a fitting guide, then scraped "
            "away the symbol that should occupy its last position.",
            aliases=("bolt notches", "notches", "belfry marks"),
            listen="The unloaded frame settles without moving. Four thin "
                   "overtones rise and then stop.",
        ),
    ),
    NOON_LENS_KEY: (
        _feature(
            "omen_fifth_notch",
            "Fifth Notch",
            "an intentionally unmarked fifth position on the old sighting frame",
            "Four notches describe ordinary road bearings. The fifth is "
            "blank, polished by a thumb, and aligned with no visible road.",
            aliases=("fifth notch", "sighting notches", "notch"),
            touch="The blank fifth position has been handled far more than "
                  "the four marked bearings.",
        ),
    ),
}

OMEN_DEFINITIONS = (
    DiscoveryDefinition(
        key=BURIED_MURAL,
        kind="omen",
        trigger="command",
        verbs=("examine", "search"),
        targets=("mural", "buried mural", "rivet mural"),
        text=(
            "Beneath the newer Goblin work, the mural's oldest layer depicts "
            "four roads meeting inside a ring. A fifth road is not drawn, "
            "yet its empty place is carefully measured. Whoever made this "
            "could count an absence as precisely as a stone."
        ),
        condition=DiscoveryCondition(room_keys=(GOBLIN_PATCHWORK_PLAZA_KEY,)),
        internal_name="The buried map nobody recognizes",
    ),
    DiscoveryDefinition(
        key=CHALK_CIPHER,
        kind="omen",
        trigger="command",
        verbs=("read", "trace"),
        targets=("chalk marks", "graffiti", "chalk cipher", "symbols"),
        text=(
            "The supposed courier graffiti cannot be a route code. Its "
            "four marks are repeated around an empty fifth position, and "
            "every attempt to fill that space has been rubbed out. The "
            "chalk follows cuts older than Waymeet's repaired bridge."
        ),
        condition=DiscoveryCondition(room_keys=(WAYMEET_CROSSROADS_KEY,)),
        internal_name="The crossroads cipher",
    ),
    DiscoveryDefinition(
        key=CHILD_REFRAIN,
        kind="omen",
        trigger="command",
        verbs=("listen",),
        targets=("children", "humming", "road song", "pella"),
        text=(
            "Pella Dawnskein hums four notes and leaves a fifth hanging in "
            "silence. She says her grandmother sang it the same way and "
            "refused to supply an ending. Then she runs off to fetch "
            "another painted road pebble, as if it meant nothing."
        ),
        condition=DiscoveryCondition(room_keys=(WAYMEET_COMMONHOUSE_KEY,)),
        internal_name="Pella's unfinished refrain",
    ),
    DiscoveryDefinition(
        key=BELL_RESONANCE,
        kind="omen",
        trigger="command",
        verbs=("listen", "ring"),
        targets=("bell", "waybell", "clapperless bell"),
        text=(
            "The bell has no clapper. Still, when you hold it close, "
            "you hear four faint notes and a pause so clean it sounds "
            "intentional. The fifth notch beneath your thumb remains cold."
        ),
        condition=DiscoveryCondition(
            room_keys=(WAYMEET_CROSSROADS_KEY, WAYMEET_COMMONHOUSE_KEY),
            required_items=(CLAPPERLESS_BELL_KEY,),
        ),
        internal_name="A silent merchant trinket",
    ),
    DiscoveryDefinition(
        key=EMPTY_BELFRY,
        kind="omen",
        trigger="command",
        verbs=("listen", "examine"),
        targets=("frame", "empty frame", "belfry notches"),
        text=(
            "The empty frame makes four notes in succession, though the "
            "bronze that once hung here was carefully removed. The fifth "
            "note never comes. On the far beam, five fittings describe "
            "a much larger circle than this tower could have housed."
        ),
        condition=DiscoveryCondition(room_keys=(QUIET_BELFRY_KEY,)),
        internal_name="The unloaded watchtower",
    ),
    DiscoveryDefinition(
        key=BELL_COMPARISON,
        kind="omen",
        trigger="command",
        verbs=("compare", "hold"),
        targets=("bell", "waybell", "clapperless bell"),
        text=(
            "The four notches on your little waybell match those behind "
            "the empty frame exactly. It is not a model of this tower's "
            "missing bell. Both appear to be copies of something larger."
        ),
        condition=DiscoveryCondition(
            room_keys=(QUIET_BELFRY_KEY,),
            required_items=(CLAPPERLESS_BELL_KEY,),
        ),
        internal_name="Two copies of the same missing mechanism",
    ),
    DiscoveryDefinition(
        key=NOON_ALIGNMENT,
        kind="omen",
        trigger="command",
        verbs=("read", "examine"),
        targets=("lens scratches", "sighting notches", "fifth notch"),
        text=(
            "The lens scratched into the frame is not aimed at an enemy "
            "position. Four bearings converge on a region left blank "
            "in every surviving road survey. A fifth notch points "
            "below the horizon instead of across it."
        ),
        condition=DiscoveryCondition(room_keys=(NOON_LENS_KEY,)),
        internal_name="Noonwatch's missing bearing",
    ),
    DiscoveryDefinition(
        key=MISSING_NOTE,
        kind="omen",
        trigger="command",
        verbs=("trace",),
        targets=("fifth notch", "missing note"),
        text=(
            "Remembering Pella's unfinished song and the Waymeet chalk, "
            "you trace four marks on the frame. The fifth is not a direction "
            "or a note. It is an instruction to wait while something "
            "on the other side answers."
        ),
        condition=DiscoveryCondition(
            room_keys=(NOON_LENS_KEY,),
            required_discoveries=(CHILD_REFRAIN, CHALK_CIPHER),
        ),
        internal_name="The answer after the fourth note",
    ),
)

OMEN_REGISTRY = DiscoveryRegistry(OMEN_DEFINITIONS)

# Only these rooms receive additional scene text. Never replace authored routes,
# story-specific description layers, NPCs or other feature definitions.
OMEN_LAYERS = {
    GOBLIN_PATCHWORK_PLAZA_KEY: DescriptionLayer(
        key="omen_plaza_paving",
        text="An arc of ancient stone peeks out where the plaza's newest paving has shifted.",
        priority=120,
    ),
    WAYMEET_CROSSROADS_KEY: DescriptionLayer(
        key="omen_crossroads_chalk",
        text="Rain has uncovered thin chalk marks beneath an old bridge-repair notice.",
        priority=120,
    ),
}


def _merge_features(existing: RoomAugmentation, features, layer=None) -> RoomAugmentation:
    all_features = {feature.key: feature for feature in existing.features}
    all_features.update({feature.key: feature for feature in features})
    layers = {entry.key: entry for entry in existing.description_layers}
    if layer is not None:
        layers[layer.key] = layer
    return RoomAugmentation(
        exit_overrides=existing.exit_overrides,
        extra_exits=existing.extra_exits,
        features=tuple(all_features.values()),
        description_layers=tuple(layers.values()),
    )


def install_endgame_omens_content(world_service) -> None:
    """Register optional artifacts and NPC/scene hooks after roadside content."""
    missing = set(OMEN_FEATURES).difference(world_service.legacy_rooms)
    if missing:
        raise ValueError("Foreshadowing rooms are not installed: " + ", ".join(sorted(missing)))
    if CLAPPERLESS_BELL_KEY not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (CLAPPERLESS_BELL,)
    crafting.ITEMS_BY_KEY[CLAPPERLESS_BELL_KEY] = CLAPPERLESS_BELL

    known = legacy_world.NPCS_BY_KEY.get(PELLA.key)
    if known is not None and known != PELLA:
        raise ValueError("Conflicting Commonhouse NPC: " + PELLA.key)
    if known is None:
        legacy_world.NPCS = legacy_world.NPCS + (PELLA,)
    legacy_world.NPCS_BY_KEY[PELLA.key] = PELLA

    # Registration alone cannot make a static NPC visible. Rich LOOK and the
    # generic TALK router both read the room's actual npc_keys.
    commonhouse = world_service.legacy_rooms[WAYMEET_COMMONHOUSE_KEY]
    if PELLA.key not in commonhouse.npc_keys:
        commonhouse = replace(
            commonhouse, npc_keys=(*commonhouse.npc_keys, PELLA.key),
        )
        world_service.legacy_rooms[WAYMEET_COMMONHOUSE_KEY] = commonhouse
        if WAYMEET_COMMONHOUSE_KEY in legacy_world.ROOMS_BY_KEY:
            legacy_world.ROOMS_BY_KEY[WAYMEET_COMMONHOUSE_KEY] = commonhouse
            legacy_world.ROOMS = tuple(
                commonhouse if old.key == WAYMEET_COMMONHOUSE_KEY else old
                for old in legacy_world.ROOMS
            )

    for room_key, features in OMEN_FEATURES.items():
        existing = world_service.augmentations.get(room_key, RoomAugmentation())
        world_service.augmentations[room_key] = _merge_features(
            existing, features, OMEN_LAYERS.get(room_key),
        )
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(room_key, None)


REVISIT_LINES = {
    BURIED_MURAL: "The old mural still leads four roads toward an unmarked fifth place.",
    CHALK_CIPHER: "The same fifth chalk mark has been rubbed away again.",
    CHILD_REFRAIN: "Pella hums those four familiar notes, then goes quiet before the fifth.",
    BELL_RESONANCE: "Your waybell gives four faint notes, followed by that impossible pause.",
    EMPTY_BELFRY: "The empty frame still waits under the weight of something that is not here.",
    BELL_COMPARISON: "Your waybell's notches still fit the marks of the vanished larger bell.",
    NOON_ALIGNMENT: "The old lens still points to a blank place below the mapped roads.",
    MISSING_NOTE: "You remember now: the fifth space asks you to wait for an answer.",
}


def threshold_echoes(database, character_id: int) -> tuple[str, ...]:
    """Optional level-50 entrance callbacks; no history is required for access.

    This is a narrative contract for the future Hinge raid, not an unlock gate.
    The raid entrance can append these lines once its universal introduction
    has played. No endgame encounters or rewards are claimed to exist here.
    """
    known = discovered_keys(database, character_id)
    echoes: list[str] = []
    if BELL_RESONANCE in known and database.item_quantity(character_id, CLAPPERLESS_BELL_KEY):
        echoes.append(
            "The little clapperless waybell trembles in your pack. "
            "Four notes answer the great mechanism, then the fifth stays silent."
        )
    if BURIED_MURAL in known:
        echoes.append(
            "The gateway's ground plan is the buried mural from Junk City, "
            "only now you can see where its missing fifth road was meant to lead."
        )
    if CHALK_CIPHER in known:
        echoes.append(
            "The ward-script across the threshold is the chalk code from Waymeet. "
            "The absent mark was not a mistake."
        )
    if CHILD_REFRAIN in known:
        echoes.append(
            "You recognize Pella Dawnskein's unfinished tune in the ward's opening notes. "
            "Somewhere back at the Commonhouse she will still be humming it."
        )
    if EMPTY_BELFRY in known:
        echoes.append(
            "The missing weight above you is what kept the old Quiet Belfry's "
            "empty frame bowed for all those years."
        )
    if NOON_ALIGNMENT in known:
        echoes.append(
            "Noonwatch's fifth bearing does not point down a road. "
            "It points through the gap now opening before you."
        )
    return tuple(echoes[:3])


def install_endgame_omens_runtime(player_session_class, world_service) -> None:
    """Resolve optional omen interactions outside the ordinary discovery layer."""
    if getattr(player_session_class, "_endgame_omens_installed", False):
        return
    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        character = getattr(self, "character", None)
        if character is None:
            await previous_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        room_key = str(getattr(character, "current_room", "") or "")
        if room_key in OMEN_FEATURES:
            verb, target = _parse_command(command)
            for definition in OMEN_REGISTRY.candidates(room_key):
                if not definition.matches_command(verb, target):
                    continue
                if definition.key in discovered_keys(self.database, character.id):
                    await self.send("\r\n" + REVISIT_LINES[definition.key] + "\r\n")
                    return
            result = await attempt_discovery_command(
                self, world_service, command, registry=OMEN_REGISTRY,
            )
            if result.handled:
                return
        await _delegate_prompt(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._endgame_omens_installed = True
