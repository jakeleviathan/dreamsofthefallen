from __future__ import annotations

from dataclasses import dataclass

from mud.discovery_engine import DiscoveryCondition, DiscoveryDefinition


TARGET_CATALOG_SIZE = 360


@dataclass(frozen=True, slots=True)
class _Theme:
    stone: str
    trace: str
    sound: str
    hidden: str
    history: str


def _theme(scene) -> _Theme:
    region = str(getattr(scene, "region_key", "") or "").casefold()
    tags = " ".join(getattr(scene, "tags", ()) or ()).casefold()
    combined = region + " " + tags

    if "human" in combined or "gothic" in combined:
        return _Theme("black stone", "soot", "distant bells", "a hooked sigil", "old civic masonry")
    if "forest" in combined or "elf" in combined and "moon" not in combined:
        return _Theme("mossed stone", "pollen", "water and leaves", "a leaf-shaped cut", "an older woodland path")
    if "moon" in combined:
        return _Theme("pale stone", "silver dust", "thin wind", "a crescent incision", "an observatory tradition")
    if "dwarf" in combined or "clockwork" in combined or "steam" in combined:
        return _Theme("riveted stone", "brass filings", "a buried hammer rhythm", "a maker's notch", "an abandoned shift record")
    if "goblin" in combined or "swamp" in combined or "junk" in combined:
        return _Theme("patched masonry", "green-black grime", "wire and water ticking", "a three-scratch tally", "a forgotten salvage claim")
    if "troll" in combined or "tundra" in combined:
        return _Theme("weathered rock", "old fur", "wind through bone charms", "a hunter's cut", "a trail remembered by elders")
    if "undead" in combined or "necropolis" in combined or "grave" in combined:
        return _Theme("funerary stone", "grey dust", "a sound like breath in a sealed room", "an erased name", "a burial custom nobody explains")
    if "spore" in combined or "fung" in combined or "mycel" in combined:
        return _Theme("root-bound stone", "luminous spores", "a pulse below hearing", "a branching mark", "a memory carried in the colony")
    if "veyra" in combined or "waymeet" in combined or "market" in combined or "road" in combined:
        return _Theme("road-worn stone", "wagon dust", "many footsteps", "a courier's sign", "an older route beneath the present one")
    if "desert" in combined or "salt" in combined:
        return _Theme("salt-bitten stone", "white grit", "wind over dry hollows", "a sun-scarred line", "a road swallowed by heat")
    return _Theme("weathered stone", "fine dust", "a faint change in the ambient noise", "a shallow old mark", "something older than the present use of the place")


def _targets(scene, index: int) -> tuple[str, ...]:
    tags = set(str(value).casefold() for value in (getattr(scene, "tags", ()) or ()))
    tag_text = " ".join(tags)
    options: list[tuple[str, ...]] = []

    if any(word in tag_text for word in ("river", "water", "pool", "swamp", "marsh", "harbor", "dock")):
        options.extend([
            ("water", "surface", "ripples"),
            ("bank", "mud", "reeds"),
            ("stones", "river stones", "wet stones"),
        ])
    if any(word in tag_text for word in ("forest", "grove", "wood", "garden", "root", "fung", "spore")):
        options.extend([
            ("roots", "root", "rootwork"),
            ("bark", "tree", "trunk"),
            ("moss", "growth", "leaves"),
        ])
    if any(word in tag_text for word in ("cathedral", "temple", "shrine", "cleric", "crypt", "grave")):
        options.extend([
            ("stonework", "stones", "masonry"),
            ("candles", "wax", "votives"),
            ("carvings", "inscriptions", "marks"),
        ])
    if any(word in tag_text for word in ("market", "guild", "city", "street", "alley", "court")):
        options.extend([
            ("paving", "cobbles", "street"),
            ("signs", "shop signs", "marks"),
            ("walls", "wall", "masonry"),
        ])
    if any(word in tag_text for word in ("mine", "cave", "underground", "tunnel", "works", "forge")):
        options.extend([
            ("floor", "stone floor", "dust"),
            ("walls", "rock", "masonry"),
            ("ceiling", "beams", "supports"),
        ])
    if any(word in tag_text for word in ("road", "path", "trail", "crossroads", "frontier")):
        options.extend([
            ("roadside", "road", "ruts"),
            ("tracks", "footprints", "wheel marks"),
            ("marker", "waymarker", "stones"),
        ])

    options.extend([
        ("ground", "floor", "earth"),
        ("walls", "wall", "stonework"),
        ("shadows", "shadow", "darkness"),
        ("details", "surroundings", "room"),
    ])
    return options[index % len(options)]


def _event_weather_for(scene, index: int) -> str:
    region = str(getattr(scene, "region_key", "") or "").casefold()
    tags = " ".join(getattr(scene, "tags", ()) or ()).casefold()
    combined = region + " " + tags
    if "desert" in combined or "salt" in combined:
        values = ("clear", "windy", "duststorm", "rain")
    elif "swamp" in combined or "marsh" in combined:
        values = ("humid", "mist", "rain", "storm")
    elif any(word in combined for word in ("mountain", "tundra", "snow")):
        values = ("clear", "cloudy", "mist", "snow", "storm")
    elif any(word in combined for word in ("cavern", "underground", "underway")):
        values = ("damp", "mist", "clear", "rain")
    else:
        values = ("clear", "cloudy", "mist", "rain", "storm")
    return values[index % len(values)]


def _room_scenes(world_service) -> list[object]:
    scenes = []
    for room_key in sorted(getattr(world_service, "legacy_rooms", {})):
        scene = world_service.scene(room_key)
        if scene is not None:
            scenes.append(scene)
    if not scenes:
        raise RuntimeError("Cannot build discovery catalog without authored rooms.")
    return scenes


def _environmental_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"A closer search of {scene.name} turns up a line in the {t.stone} where {t.trace} has settled differently. "
        f"It is not a door or a cache, only evidence that someone once cared enough to conceal {t.hidden}.",
        f"For a moment the ordinary shape of {scene.name} resolves into something stranger: {t.hidden} repeats at three different heights. "
        f"The pattern is too consistent to be accidental, but whatever language it belonged to is gone.",
        f"Beneath the obvious traffic of the place, you find a quieter layer: {t.trace}, one old scrape, and the suggestion of {t.history}. "
        f"Nothing here asks to be solved. It simply rewards noticing.",
        f"You hold still long enough to separate {t.sound} from the rest of {scene.name}. "
        f"The rhythm repeats, pauses, and repeats again in a way that feels almost intentional.",
        f"An unremarkable patch of {t.stone} carries a repair older than everything around it. "
        f"The workmanship points to {t.history}, though no sign or plaque acknowledges it.",
        f"What looked like random wear proves to be directional. Tiny abrasions lead toward {t.hidden}, then stop exactly where newer work begins.",
        f"You notice that generations of hands avoided one small section of {t.stone}. The untouched patch is faintly marked by {t.hidden}.",
        f"The place has a second history written only in damage: a burn, a careful patch, {t.trace}, and one shallow cut that survived later repairs.",
    )
    return templates[index % len(templates)]


def _interaction_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"Under your hand, the surface gives a fraction more than expected. A concealed seam follows {t.hidden}, then vanishes into solid work. "
        f"Whatever once opened here has not moved in a very long time.",
        f"The mark is not decorative. Read from left to right it resembles a route notation; read from right to left it resembles a warning. "
        f"Both interpretations point back toward {t.history}.",
        f"Your knock returns one ordinary echo and then a softer answer from somewhere it should not. The second sound does not repeat.",
        f"Touching the worn place releases a smell of {t.trace} and old air. Someone sealed this surface after the rest of {scene.name} was already in use.",
        f"Up close, {t.hidden} has been cut with a tool too fine for the surrounding workmanship. It feels like a private signature rather than public ornament.",
        f"You trace the edge and find a tiny interruption: three deliberate taps, a pause, then two more. It is the kind of signal meant for someone already expecting it.",
    )
    return templates[index % len(templates)]


def _calendar_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"The light catches {t.hidden} at an angle that does not exist at other hours. For only a few minutes, the mark points somewhere instead of merely decorating the surface.",
        f"Under this moon the shadows in {scene.name} fail to line up with their objects. One narrow shadow instead outlines a forgotten path associated with {t.history}.",
        f"The season changes the acoustics here. {t.sound.capitalize()} carries from a direction that should be blocked, then disappears when you move your head.",
        f"At this hour, a hair-thin line of brightness crosses the {t.stone} and joins marks that look unrelated in ordinary light.",
        f"For a brief celestial alignment, {t.hidden} becomes legible as a sequence rather than a shape. You memorize it before the angle passes.",
    )
    return templates[index % len(templates)]


def _provenance_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"The old object you carry changes how you read this place. Its wear matches a patch of {t.stone} here closely enough to suggest the two once shared a workshop.",
        f"A maker's habit on one of your heritage pieces appears again in {scene.name}: the same unnecessary finishing stroke, hidden where only another craftsperson would notice.",
        f"Your carried relic bears a tiny abrasion that fits {t.hidden} almost perfectly. Whether it was a key, a measuring guide, or coincidence is impossible to prove.",
        f"Something about the provenance of what you carry makes the local repair work suddenly recognizable. This was done by the same tradition, perhaps generations apart.",
        f"You compare an old maker's mark in your possession with the nearby surface. The symbols are not identical, but their spacing follows the same hand.",
    )
    return templates[index % len(templates)]


def _ecology_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"The living world has exposed what construction hid. New growth follows a buried line beneath {scene.name}, tracing an older foundation one root at a time.",
        f"Tracks and disturbed growth form a pattern no map records. Animals are repeatedly avoiding one narrow strip, as if the ground there still carries an old boundary.",
        f"The current balance of moisture and vegetation has uncovered {t.hidden}. In a drier or more damaged season it would disappear completely.",
        f"A concentration of insects and fresh growth marks a pocket of unusually rich ground. Beneath it, the soil contains fragments from {t.history}.",
        f"Ecological pressure has made the secret visible: surviving plants cluster exactly where old stone lies shallow beneath the surface.",
    )
    return templates[index % len(templates)]


def _event_text(scene, index: int) -> str:
    t = _theme(scene)
    templates = (
        f"Something is different in {scene.name} today. Travelers are moving faster, and even the usual background noise bends around a rumor nobody says plainly.",
        f"A brief local disturbance passes through the area: {t.sound}, several startled animals, then silence. People nearby pretend not to have noticed.",
        f"The weather exposes an older version of this place. Water, dust, or frost outlines foundations that vanish again as conditions change.",
        f"For less than a minute, everyone in sight seems to be watching the same empty direction. Then ordinary activity resumes without explanation.",
        f"A rare pattern of light and weather makes {t.hidden} visible from across the room. By the time you approach, it has faded back into the surroundings.",
    )
    return templates[index % len(templates)]


CHAIN_MOTIFS = (
    ("bell_without_tower", "The Bell Without a Tower"),
    ("thread_under_road", "The Thread Under the Road"),
    ("ash_ledger", "The Ash Ledger"),
    ("empty_name", "The Empty Name"),
    ("fourth_footprint", "The Fourth Footprint"),
    ("borrowed_star", "The Borrowed Star"),
    ("glass_root", "The Glass Root"),
    ("remembering_door", "The Door That Remembers"),
    ("white_moth", "The White Moth"),
    ("ninth_toll", "The Ninth Toll"),
)

MYSTERY_MOTIFS = (
    ("unwritten_map", "The Unwritten Map"),
    ("grave_of_tomorrow", "The Grave of Tomorrow"),
    ("house_beneath_weather", "The House Beneath Weather"),
    ("breath_between_worlds", "The Breath Between Worlds"),
)


def build_discovery_catalog(world_service) -> tuple[DiscoveryDefinition, ...]:
    """Build the private production catalog from the fully assembled world.

    The count is intentional, not a UI contract. Players never receive this
    number. Room assignment is deterministic so future restarts do not move
    secrets, while the text and conditions remain authored by discovery family.
    """

    scenes = _room_scenes(world_service)
    definitions: list[DiscoveryDefinition] = []

    def scene_at(index: int, stride: int = 1, offset: int = 0):
        return scenes[(offset + index * stride) % len(scenes)]

    # 82 quiet environmental discoveries, starting with one anchor per region.
    verbs = ("search", "examine", "listen", "look")
    first_by_region: dict[str, object] = {}
    for scene in scenes:
        first_by_region.setdefault(str(scene.region_key), scene)
    region_anchors = [first_by_region[key] for key in sorted(first_by_region)]
    for index in range(82):
        scene = (
            region_anchors[index]
            if index < len(region_anchors)
            else scene_at(index - len(region_anchors), stride=7, offset=3)
        )
        target = _targets(scene, index)
        verb = verbs[index % len(verbs)]
        targets = ("",) if verb == "listen" and index % 3 == 0 else target
        definitions.append(
            DiscoveryDefinition(
                key=f"env:{scene.key}:{index:03d}",
                kind="environmental",
                trigger="command",
                verbs=(verb,),
                targets=targets,
                text=_environmental_text(scene, index),
                condition=DiscoveryCondition(room_keys=(scene.key,)),
                internal_name=f"Environmental trace {index + 1}",
            )
        )

    # Eight race-specific perceptions. These are not stat bonuses; they are
    # pieces of cultural/world knowledge that another ancestry can walk past.
    racial_clues = (
        ("human", "civic emblem", "You read the severe ornament as civic shorthand rather than menace. One tiny variation marks a municipal repair crew whose records supposedly vanished generations ago."),
        ("forest_elf", "living edge", "The growth pattern is legible to you as maintenance, not wilderness. Someone has been tending this edge according to an old Druidic convention without admitting it."),
        ("moon_elf", "moon angle", "The geometry is wrong for decoration and right for lunar sighting. A line that means nothing from ground level points cleanly toward the moon's seasonal path."),
        ("dwarf", "tool chatter", "The tool marks tell a work story: two crews, two shifts, and one deliberate interruption where the official job should have continued."),
        ("goblin", "repair logic", "You recognize the ugly little repair as excellent work. More importantly, it was designed to be reopened quickly by someone who knew which scrap piece was load-bearing."),
        ("troll", "old trail", "The scuffs are not random wear. They preserve the age and direction of a trail in the same practical grammar used by hunters who expect snow or leaf-fall to erase tracks."),
        ("undead", "burial layer", "You recognize a funerary sequence under the later decoration. The living reused this place without realizing which part was meant to face the dead."),
        ("sporekin", "quiet pulse", "A faint biological rhythm sits beneath the obvious sounds. It resembles a colony memory that has been cut off from whatever network once answered it."),
    )
    for index, (race, target, text_value) in enumerate(racial_clues):
        scene = scene_at(index, stride=41, offset=11)
        definitions.append(
            DiscoveryDefinition(
                key=f"racial_perception:{race}:{scene.key}",
                kind="racial",
                trigger="command",
                verbs=("examine", "listen"),
                targets=(target, "details", "surroundings"),
                text=text_value,
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    races=(race,),
                ),
                internal_name=f"{race} cultural perception",
            )
        )

    # Five class-specific readings of the same physical world.
    class_clues = (
        ("necromancer", "death trace", "What others might call age reads to you as a sequence of death practices. One part of the sequence was interrupted intentionally."),
        ("brute", "impact marks", "Weight, angle, and repeated impact tell you more than the inscription does. Someone trained here for a fight with a very specific reach."),
        ("wizard", "residue", "A weak magical residue survives in the material, not the air. It was built into the work rather than cast over it later."),
        ("druid", "growth pattern", "The plants are responding to something below the visible surface. Their spacing sketches the hidden shape better than any survey line."),
        ("priest", "votive wear", "The wear pattern is devotional but unofficial. Generations of private gestures have polished a place the public rite never mentions."),
    )
    for index, (class_key, target, text_value) in enumerate(class_clues):
        scene = scene_at(index, stride=53, offset=19)
        definitions.append(
            DiscoveryDefinition(
                key=f"class_perception:{class_key}:{scene.key}",
                kind="class",
                trigger="command",
                verbs=("examine",),
                targets=(target, "marks", "details"),
                text=text_value,
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    classes=(class_key,),
                ),
                internal_name=f"{class_key} professional perception",
            )
        )

    # 10 reputation-gated confidences. A faction must actually control the
    # region; otherwise the room is not selected for this family.
    try:
        from mud.faction_reputation import faction_for_region
        faction_scenes = [
            scene for scene in scenes
            if faction_for_region(getattr(scene, "region_key", None))
        ]
    except Exception:
        faction_scenes = []
    for index in range(10):
        scene = (faction_scenes or scenes)[(index * 7 + 2) % len(faction_scenes or scenes)]
        condition = DiscoveryCondition(room_keys=(scene.key,))
        if faction_scenes:
            condition = DiscoveryCondition(
                room_keys=(scene.key,),
                min_region_standing=120 + (index % 3) * 115,
                min_region_renown=80 if index % 2 else None,
            )
        definitions.append(
            DiscoveryDefinition(
                key=f"reputation_confidence:{scene.key}:{index:02d}",
                kind="reputation",
                trigger="command",
                verbs=("listen", "talk"),
                targets=("locals", "quiet talk", "trusted rumor", "old business"),
                text=(
                    f"Because people here know how the local faction regards you, a conversation does not stop when you approach. "
                    f"You hear a detail about {scene.name} that strangers are normally allowed to misunderstand: an old route, obligation, or warning still shapes how locals use the place."
                ),
                condition=condition,
                internal_name=f"Faction confidence {index + 1}",
            )
        )

    # Five inventory-keyed clues. These make physical possessions part of the
    # secret grammar instead of treating inventory as a separate minigame.
    item_clues = (
        ("starter_weapon", "old nicks", "The wear on your plain weapon matches practice cuts here that everyone else reads as random damage."),
        ("wildflower", "pressed hollow", "The flower you carry fits a tiny pressed hollow exactly; someone once used the same bloom as a temporary sign."),
        ("blank_waymap", "survey mark", "Your blank waymap makes the spacing obvious: these shallow marks are survey intervals for a route no current map records."),
        ("sealed_cathedral_note", "hooked sign", "Beside the sealed note, the hooked sign stops looking ornamental. The same hand taught both systems of marks."),
        ("bone_chips", "bone tally", "The bone chips you carry make the little tally suddenly legible as anatomy rather than arithmetic."),
    )
    for index, (item_key, target, text_value) in enumerate(item_clues):
        scene = scene_at(index, stride=47, offset=61)
        definitions.append(
            DiscoveryDefinition(
                key=f"inventory_clue:{scene.key}:{item_key}",
                kind="inventory",
                trigger="command",
                verbs=("examine", "compare"),
                targets=(target, "marks", "clue"),
                text=text_value,
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    required_items=(item_key,),
                ),
                internal_name=f"Inventory-bound clue {index + 1}",
            )
        )

    # 60 direct object/room interactions. Some are deliberately odd verbs; they
    # only become meaningful where the hidden content exists.
    interaction_verbs = ("touch", "read", "knock", "examine", "pray")
    for index in range(60):
        scene = scene_at(index, stride=11, offset=17)
        target = _targets(scene, index + 2)
        condition = DiscoveryCondition(room_keys=(scene.key,))
        if index % 14 == 5:
            condition = DiscoveryCondition(
                room_keys=(scene.key,),
                classes=("priest", "druid", "wizard"),
            )
        elif index % 14 == 9:
            condition = DiscoveryCondition(
                room_keys=(scene.key,),
                min_level=4,
            )
        definitions.append(
            DiscoveryDefinition(
                key=f"interaction:{scene.key}:{index:03d}",
                kind="interaction",
                trigger="command",
                verbs=(interaction_verbs[index % len(interaction_verbs)],),
                targets=target,
                text=_interaction_text(scene, index),
                condition=condition,
                internal_name=f"Hidden interaction {index + 1}",
            )
        )

    # 10 rumor discoveries. These are deliberately not all reliable. Some point
    # toward real chains, some preserve local prejudice, and some are simply the
    # kind of story travelers repeat because it is memorable.
    rumor_texts = (
        "Two travelers lower their voices over the same claim: a bell can sometimes be heard where no tower stands. One swears it marks a road; the other says following it killed a friend.",
        "Someone insists that certain old road repairs hide messages between couriers. A second voice laughs and says the marks are only lazy masonry.",
        "A market story claims a burned ledger survived because the ash itself remembers the names. Nobody telling the story agrees on what that means.",
        "You catch a warning about an erased name that appears only after rain. The speaker refuses to say whether the name belongs to a saint, criminal, or city.",
        "A hunter describes finding four sets of prints where only three people walked. The listeners call it drink-talk, but nobody jokes very loudly.",
        "A quiet argument concerns a star that appears in reflections before it appears in the sky. One person calls it an omen; another calls it bad glass.",
        "A gardener tells someone that glass sometimes grows roots underground. The answer is immediate: 'That is not what the story means.'",
        "You hear of a door that never opens but somehow remembers everyone who touches it. The storyteller cannot say where it is.",
        "A child repeats a rhyme about a white moth that only lands on places people have forgotten on purpose. An adult sharply tells them to stop.",
        "A road-worker mutters that some bells have a ninth toll, too quiet to hear unless you already know the first eight were wrong.",
    )
    for index in range(10):
        scene = scene_at(index, stride=43, offset=73)
        definitions.append(
            DiscoveryDefinition(
                key=f"rumor:{scene.key}:{index:02d}",
                kind="rumor",
                trigger="command",
                verbs=(("listen", "talk")[index % 2],),
                targets=(("rumors", "gossip", "crowd") if index % 2 == 0 else ("rumor", "traveler", "locals")),
                text=rumor_texts[index],
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    time_buckets=("dusk", "night") if index in {3, 7} else (),
                ),
                internal_name=f"Unverified rumor {index + 1}",
            )
        )

    # 35 calendar/celestial discoveries.
    phases = ("new", "waxing", "full", "waning")
    buckets = ("dawn", "dusk", "night")
    seasons = ("spring", "summer", "autumn", "winter")
    for index in range(35):
        scene = scene_at(index, stride=13, offset=29)
        target = _targets(scene, index + 5)
        condition = DiscoveryCondition(
            room_keys=(scene.key,),
            time_buckets=(buckets[index % len(buckets)],),
            moon_phases=(phases[index % len(phases)],) if index % 2 == 0 else (),
            seasons=(seasons[index % len(seasons)],) if index % 5 == 0 else (),
        )
        definitions.append(
            DiscoveryDefinition(
                key=f"calendar:{scene.key}:{index:03d}",
                kind="calendar",
                trigger="command",
                verbs=(("look", "examine", "listen")[index % 3],),
                targets=target if index % 3 != 2 else ("", "air", "silence"),
                text=_calendar_text(scene, index),
                condition=condition,
                internal_name=f"Calendar alignment {index + 1}",
            )
        )

    # 25 item-provenance resonances. Any individually tracked heritage item can
    # become context for reading a location differently.
    for index in range(25):
        scene = scene_at(index, stride=17, offset=41)
        definitions.append(
            DiscoveryDefinition(
                key=f"heritage_resonance:{scene.key}:{index:03d}",
                kind="provenance",
                trigger="command",
                verbs=("examine",),
                targets=("maker mark", "makers mark", "old mark", "wear", "tool marks"),
                text=_provenance_text(scene, index),
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    requires_heritage_item=True,
                ),
                internal_name=f"Heritage resonance {index + 1}",
            )
        )

    # 25 ecology-dependent discoveries. They exist only while the simulation
    # itself creates the right local conditions.
    ecology_fields = (
        ("vegetation", 0.66),
        ("moisture", 0.70),
        ("resource_stock", 0.64),
        ("insects", 0.62),
        ("prey", 0.58),
    )
    for index in range(25):
        scene = scene_at(index, stride=19, offset=53)
        field_name, threshold = ecology_fields[index % len(ecology_fields)]
        definitions.append(
            DiscoveryDefinition(
                key=f"ecology:{scene.key}:{index:03d}",
                kind="ecology",
                trigger="command",
                verbs=(("search", "examine", "listen")[index % 3],),
                targets=_targets(scene, index + 7) if index % 3 != 2 else ("", "wildlife", "air"),
                text=_ecology_text(scene, index),
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    ecology_min=((field_name, threshold),),
                ),
                internal_name=f"Ecology revelation {index + 1}",
            )
        )

    # 20 transient world-event discoveries. These are passive and diegetic:
    # entering at the right time is enough. Nothing announces that an event is
    # active elsewhere.
    for index in range(20):
        scene = scene_at(index, stride=23, offset=67)
        condition = DiscoveryCondition(
            room_keys=(scene.key,),
            weather=(_event_weather_for(scene, index),) if index % 2 == 0 else (),
            day_modulus=(17 + (index % 5) * 4) if index % 2 else 0,
            day_remainder=(index * 3 + 2),
            time_buckets=(("night",) if index % 4 == 1 else ()),
        )
        definitions.append(
            DiscoveryDefinition(
                key=f"world_event:{scene.key}:{index:03d}",
                kind="world_event",
                trigger="enter",
                text=_event_text(scene, index),
                condition=condition,
                internal_name=f"Unannounced regional event {index + 1}",
                consume_command=False,
            )
        )

    # 10 invisible quest chains, five clues each. They never enter the quest
    # journal. A player only knows what they personally noticed.
    hidden_chain_finals: list[str] = []
    for chain_index, (motif_key, motif_name) in enumerate(CHAIN_MOTIFS):
        previous_key = ""
        for step in range(5):
            scene = scene_at(chain_index * 5 + step, stride=29, offset=83)
            key = f"hidden_quest:{motif_key}:{step + 1}"
            required = (previous_key,) if previous_key else ()
            extra = {}
            if step == 1:
                extra["time_buckets"] = ("dusk", "night")
            elif step == 2:
                extra["moon_phases"] = (("full", "new")[chain_index % 2],)
            elif step == 3:
                extra["min_level"] = 3 + chain_index % 5
            condition = DiscoveryCondition(
                room_keys=(scene.key,),
                required_discoveries=required,
                **extra,
            )
            stage_texts = (
                f"You find the first sign of {motif_name}, though nothing calls it by that name: a repeated mark where no public mark should be.",
                f"A second clue answers the first. Someone expected the same person to notice both, and assumed everyone else would walk past.",
                f"The trail stops being coincidence. The third sign contains a direction encoded as spacing rather than words.",
                f"You reach a place the earlier clues described without naming it. Something here has been maintained in secret long after its original purpose was forgotten.",
                f"The final piece settles into place. There is no proclamation, no reward chest, and no one to congratulate you. You simply understand what {motif_name} was trying to preserve.",
            )
            verb = ("search", "listen", "read", "touch", "examine")[step]
            targets = (
                ("mark", "old mark", "scratches"),
                ("", "echo", "silence"),
                ("sign", "inscription", "spacing"),
                ("seam", "hidden seam", "stone"),
                ("pattern", "final mark", "clue"),
            )[step]
            definitions.append(
                DiscoveryDefinition(
                    key=key,
                    kind="hidden_quest",
                    trigger="command",
                    verbs=(verb,),
                    targets=targets,
                    text=stage_texts[step],
                    condition=condition,
                    internal_name=f"{motif_name}, clue {step + 1}",
                    experience_reward=20 if step == 4 else 0,
                    chronicle_first=step == 4,
                )
            )
            previous_key = key
        hidden_chain_finals.append(previous_key)

    # Four larger mysteries cross-reference the invisible quests. Each one asks
    # players to combine knowledge from otherwise unrelated regions.
    mystery_finals: list[str] = []
    for mystery_index, (motif_key, motif_name) in enumerate(MYSTERY_MOTIFS):
        previous_key = ""
        prerequisites = (
            hidden_chain_finals[(mystery_index * 2) % len(hidden_chain_finals)],
            hidden_chain_finals[(mystery_index * 2 + 3) % len(hidden_chain_finals)],
        )
        for step in range(5):
            scene = scene_at(mystery_index * 5 + step, stride=31, offset=107)
            key = f"mystery:{motif_key}:{step + 1}"
            required = prerequisites if step == 0 else (previous_key,)
            condition = DiscoveryCondition(
                room_keys=(scene.key,),
                required_discoveries=required,
                time_buckets=("night",) if step in {1, 4} else (),
                moon_phases=("waning",) if step == 2 else (),
                day_modulus=29 if step == 3 else 0,
                day_remainder=7 + mystery_index,
                requires_heritage_item=step == 4,
            )
            text = (
                f"Two unrelated secrets suddenly share the same grammar. The first piece of {motif_name} was hidden across traditions that should never have agreed.",
                f"At night the second piece appears as absence: a gap deliberately preserved while everything around it changed.",
                f"Under the waning moon, the third piece becomes readable. It describes a place by what cannot be seen from it.",
                f"On this rare day the fourth piece is present. Tomorrow the same evidence will look ordinary again.",
                f"Your carried history supplies the final comparison. {motif_name} is not a legend but a method: a way people in different ages left knowledge for strangers they would never meet.",
            )[step]
            definitions.append(
                DiscoveryDefinition(
                    key=key,
                    kind="mystery",
                    trigger="command",
                    verbs=(("compare", "look", "examine", "wait", "remember")[step],),
                    targets=(
                        ("signs", "clues", "marks"),
                        ("gap", "absence", "darkness"),
                        ("sky", "moon", "shadow"),
                        ("place", "surroundings", "room"),
                        ("history", "relic", "maker mark"),
                    )[step],
                    text=text,
                    condition=condition,
                    internal_name=f"{motif_name}, stage {step + 1}",
                    experience_reward=40 if step == 4 else 0,
                    chronicle_first=step == 4,
                )
            )
            previous_key = key
        mystery_finals.append(previous_key)

    # Five community-scale secrets. These deliberately combine a solved mystery,
    # identity, a rare day, a moon phase, and a precise interaction. They are
    # meant to survive ordinary completionist play for a very long time.
    ultra_specs = (
        ("the_silent_coronation", "human", "priest", "full", 137, 61),
        ("the_root_that_dreams_back", "forest_elf", "druid", "new", 149, 38),
        ("the_moon_below_the_moon", "moon_elf", "wizard", "waning", 163, 91),
        ("the_market_of_things_never_sold", "goblin", "brute", "waxing", 173, 44),
        ("the_spore_before_memory", "sporekin", "necromancer", "new", 181, 117),
    )
    for index, (key_suffix, race, class_key, phase, modulus, remainder) in enumerate(ultra_specs):
        scene = scene_at(index, stride=37, offset=139)
        definitions.append(
            DiscoveryDefinition(
                key=f"ultra:{key_suffix}",
                kind="ultra_secret",
                trigger="command",
                verbs=(("kneel", "touch", "look", "offer", "listen")[index],),
                targets=(
                    ("empty place", "vacant stone", "nothing"),
                    ("root", "old root", "roots"),
                    ("reflection", "dark reflection", "sky"),
                    ("empty stall", "closed stall", "counter"),
                    ("silence", "", "pulse"),
                )[index],
                text=(
                    "The world does not announce what happened. For one impossible instant, several old stories agree with one another, and you are standing exactly where their contradiction becomes true. "
                    "Then the moment closes. Nothing visible remains except the certainty that Astralis is stranger than its maps."
                ),
                condition=DiscoveryCondition(
                    room_keys=(scene.key,),
                    races=(race,),
                    classes=(class_key,),
                    time_buckets=("night",),
                    moon_phases=(phase,),
                    day_modulus=modulus,
                    day_remainder=remainder,
                    required_discoveries=(mystery_finals[index % len(mystery_finals)],),
                    requires_heritage_item=True,
                    min_level=8,
                ),
                internal_name=f"Community-scale secret {index + 1}",
                experience_reward=100,
                chronicle_first=False,
            )
        )

    if len(definitions) != TARGET_CATALOG_SIZE:
        raise RuntimeError(
            f"Discovery catalog construction drifted to {len(definitions)} entries; "
            f"expected {TARGET_CATALOG_SIZE}."
        )
    return tuple(definitions)


def catalog_kind_counts(definitions: tuple[DiscoveryDefinition, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for definition in definitions:
        counts[definition.kind] = counts.get(definition.kind, 0) + 1
    return counts
