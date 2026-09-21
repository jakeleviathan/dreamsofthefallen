from __future__ import annotations

from dataclasses import dataclass

from mud.appearance import appearance_description


RAINY_WEATHER = frozenset({"rain", "storm", "thunderstorm"})


@dataclass(frozen=True, slots=True)
class ReflectionOpportunity:
    key: str
    name: str
    aliases: tuple[str, ...]
    room_text: str
    reflection_text: str
    source_kind: str = "fixture"

    def matches(self, target: str) -> bool:
        needle = " ".join(target.strip().lower().split())
        if not needle:
            return False
        names = {
            self.key.lower().replace("_", " "),
            self.name.lower(),
            *(alias.lower() for alias in self.aliases),
        }
        return needle in names


_STARTING_FIXTURES: dict[str, ReflectionOpportunity] = {
    "human_demon_gate": ReflectionOpportunity(
        "blackglass_looking_plate",
        "Blackglass Looking Plate",
        ("mirror", "looking plate", "blackglass", "reflection"),
        "A hand-wide blackglass looking plate is fixed beside the gate watch station, polished enough for guards and travelers to check their appearance.",
        "The blackglass returns a dark, unusually crisp reflection.",
    ),
    "forest_elf_circle_clearing": ReflectionOpportunity(
        "stillwater_bowl",
        "Stillwater Bowl",
        ("bowl", "water", "mirror", "reflection"),
        "A shallow stone bowl at the clearing's edge holds water deliberately kept still for washing, grooming, and quiet reflection.",
        "The still water gathers your face and form between faint rings of light.",
        "water",
    ),
    "moon_elf_high_horizon_plaza": ReflectionOpportunity(
        "silvered_skyglass",
        "Silvered Skyglass",
        ("mirror", "skyglass", "silvered glass", "reflection"),
        "A narrow sheet of silvered skyglass stands near the plaza's public wash niche, reflecting both the viewer and a sliver of open sky.",
        "The silvered skyglass renders your features with cool, exact clarity.",
    ),
    "dwarf_foundry_concourse": ReflectionOpportunity(
        "brass_inspection_mirror",
        "Brass Inspection Mirror",
        ("mirror", "brass mirror", "inspection mirror", "reflection"),
        "A burnished brass inspection mirror is bolted beside a workers' washstand, scarred at the rim but kept bright at its center.",
        "The burnished brass throws back a warm, slightly imperfect reflection.",
    ),
    "goblin_clattergate": ReflectionOpportunity(
        "salvaged_mirror",
        "Salvaged Mirror",
        ("mirror", "mirror shard", "salvaged glass", "reflection"),
        "A surprisingly good mirror shard has been wired flat to a post among the gate's useful scraps. Someone has even wiped the fingerprints off it.",
        "The salvaged glass catches your reflection in one sharp-edged piece.",
    ),
    "troll_frostroot_camp": ReflectionOpportunity(
        "polished_water_bowl",
        "Polished Water Bowl",
        ("bowl", "water bowl", "water", "mirror", "reflection"),
        "A broad stone water bowl sits near the camp's grooming tools. Its dark polished interior makes the water surface easy to use as a mirror.",
        "The dark water holds your reflection with only a slow tremor from the cold air.",
        "water",
    ),
    "undead_reclamation_vault": ReflectionOpportunity(
        "mourning_mirror",
        "Obsidian Mourning Mirror",
        ("mirror", "obsidian mirror", "mourning mirror", "reflection"),
        "A polished obsidian mourning mirror is set into one wall, a funerary object meant for the newly reawakened to study what death has left them.",
        "The obsidian gives back your preserved dead form without softening a single detail.",
    ),
    "sporekin_lumen_hollow": ReflectionOpportunity(
        "dew_basin",
        "Dew Basin",
        ("basin", "dew", "water", "mirror", "reflection"),
        "A cupped shelf of living fungus gathers clear condensation into a calm dew basin used by the Sporekin to inspect caps, growth, and adornments.",
        "The dew basin holds a soft reflection beneath its faint fungal light.",
        "water",
    ),
}


_CURATED_FIXTURES: dict[str, ReflectionOpportunity] = {
    **_STARTING_FIXTURES,
    "waymeet_crossroads": ReflectionOpportunity(
        "wayfarers_looking_glass",
        "Wayfarer's Looking Glass",
        ("mirror", "looking glass", "wayfarer mirror", "reflection"),
        "A weatherproof looking glass stands beside the crossroads notice board, maintained for travelers arriving dusty from every road.",
        "The public looking glass gives back a plain, honest reflection.",
    ),
    "waymeet_lantern_market": ReflectionOpportunity(
        "merchant_mirror",
        "Merchant Mirror",
        ("mirror", "market mirror", "looking glass", "reflection"),
        "A tall trade mirror hangs where cloth, armor, jewelry, and other wares can be judged before coin changes hands.",
        "The market mirror catches you from head to foot.",
    ),
    "waymeet_commonhouse_yard": ReflectionOpportunity(
        "commonhouse_wash_mirror",
        "Commonhouse Wash Mirror",
        ("mirror", "wash mirror", "looking glass", "reflection"),
        "A sturdy mirror hangs above the commonhouse wash basin, its frame repaired by more than one regional style.",
        "The commonhouse mirror reflects you in clear afternoon-bright glass.",
    ),
    "counterstar_mirrored_cut": ReflectionOpportunity(
        "cliff_mirror",
        "Cliff Mirror",
        ("mirror", "cliff mirror", "observation mirror", "reflection"),
        "One of the Moon Elf cliff mirrors can be turned low enough to catch a traveler's reflection as well as the sky beyond the blind turn.",
        "The angled cliff mirror shows you against an enormous wedge of mountain sky.",
    ),
    "echo_mirror_choir": ReflectionOpportunity(
        "black_mirror_panel",
        "Black Mirror Panel",
        ("mirror", "panel", "black panel", "mirror choir", "reflection"),
        "The black panels do not reflect ordinary light correctly, yet when you stand close they return enough of your outline and features to study yourself.",
        "Your reflection appears in the black panel with the light missing from everything around it.",
        "anomalous",
    ),
    "waymeet_flooded_culvert": ReflectionOpportunity(
        "culvert_water",
        "Flooded Culvert Water",
        ("water", "floodwater", "culvert water", "reflection"),
        "Between drips, the flooded culvert settles into dark stretches smooth enough to return a wavering face.",
        "The culvert water breaks your reflection into dark ripples and reforms it again.",
        "water",
    ),
}


_HUB_TAGS = frozenset({
    "social_hub",
    "market",
    "merchant",
    "rest",
    "meeting_place",
    "civic_work",
    "rail_hub",
    "bureaucracy",
    "trade",
    "wayhouse",
    "commonhouse",
})

_HUB_NAME_WORDS = (
    " plaza",
    " concourse",
    " market",
    " commonhouse",
    " wayhouse",
    " terminal",
    " registry",
    " exchange",
    " guildhall",
    " bath",
    " inn",
    " tavern",
)

_WATER_NAME_WORDS = (" pool", " basin", " flooded ", " flooded", " cistern")
_WATER_TAGS = frozenset({"water", "pool", "cistern"})


def _regional_fixture(region_key: str) -> ReflectionOpportunity:
    key = region_key.lower()
    if "human" in key or "blackglass" in key:
        return ReflectionOpportunity(
            "public_blackglass_mirror",
            "Public Blackglass Mirror",
            ("mirror", "blackglass mirror", "looking glass", "reflection"),
            "A polished blackglass mirror has been mounted here for public use, dark-framed and severe in the Human fashion.",
            "The blackglass holds a deep, crisp reflection.",
        )
    if "forest" in key or "alderwake" in key:
        return ReflectionOpportunity(
            "public_stillwater_basin",
            "Stillwater Wash Basin",
            ("basin", "water", "mirror", "reflection"),
            "A shallow communal wash basin has been shaped to keep its center still, useful for grooming as well as washing.",
            "The basin's quiet center gives back your reflection beneath the surrounding leaves.",
            "water",
        )
    if "moon" in key or "counterstar" in key:
        return ReflectionOpportunity(
            "public_skyglass_mirror",
            "Skyglass Mirror",
            ("mirror", "skyglass", "looking glass", "reflection"),
            "A slim skyglass mirror occupies one wall, positioned to borrow clean natural light whenever the sky is visible.",
            "The skyglass returns your reflection with cool precision.",
        )
    if "dwarf" in key or "deepwheel" in key:
        return ReflectionOpportunity(
            "public_brass_mirror",
            "Burnished Brass Mirror",
            ("mirror", "brass mirror", "inspection mirror", "reflection"),
            "A practical burnished brass mirror hangs beside the wash fixtures, its center polished by constant use.",
            "The brass surface returns your reflection in warm metal tones.",
        )
    if "goblin" in key or "rattle" in key:
        return ReflectionOpportunity(
            "public_salvage_mirror",
            "Salvaged Glass Mirror",
            ("mirror", "salvaged mirror", "glass", "reflection"),
            "A mismatched but perfectly usable piece of salvaged mirror glass has been fixed at face height with wire and old brackets.",
            "The scavenged glass gives you a surprisingly clear reflection.",
        )
    if "troll" in key or "thornwake" in key:
        return ReflectionOpportunity(
            "public_water_mirror",
            "Dark Water Bowl",
            ("bowl", "water", "water bowl", "mirror", "reflection"),
            "A broad dark-stone bowl of clean water sits among the shared grooming gear, its polished interior sheltering the surface from stray wind.",
            "The sheltered water holds your reflection steadily.",
            "water",
        )
    if "undead" in key or "pale" in key or "gravewatch" in key or "necropolis" in key:
        return ReflectionOpportunity(
            "public_obsidian_mirror",
            "Obsidian Mirror",
            ("mirror", "obsidian", "mourning mirror", "reflection"),
            "A black polished mirror stands among the public fixtures, severe enough to look funerary even where it serves an ordinary purpose.",
            "The obsidian returns every hard line of your reflection.",
        )
    if "spore" in key or "rainroot" in key:
        return ReflectionOpportunity(
            "public_dew_basin",
            "Dew Basin",
            ("basin", "dew", "water", "mirror", "reflection"),
            "A living cup of fungus gathers clear water into a still communal basin.",
            "Soft fungal light shimmers around your reflection in the dew.",
            "water",
        )
    return ReflectionOpportunity(
        "public_looking_glass",
        "Public Looking Glass",
        ("mirror", "looking glass", "reflection"),
        "A durable public looking glass hangs here for travelers who need to put themselves back in order.",
        "The glass gives back a straightforward reflection.",
    )


def _natural_water_source(scene) -> ReflectionOpportunity | None:
    key = str(getattr(scene, "key", "")).lower()
    name = str(getattr(scene, "name", "")).lower()
    tags = {str(tag).lower() for tag in getattr(scene, "tags", ())}
    haystack = f" {key.replace('_', ' ')} {name} "
    if not any(word in haystack for word in _WATER_NAME_WORDS) and not (tags & _WATER_TAGS):
        return None
    if "well" in name or "well" in key:
        return None
    return ReflectionOpportunity(
        "natural_water_reflection",
        "Still Water",
        ("water", "surface", "pool", "reflection"),
        "A calmer patch of water here is smooth enough to catch a usable reflection when you lean over it.",
        "The water's surface carries your reflection under a faint movement of ripples.",
        "water",
    )


def _named_reflective_source(scene) -> ReflectionOpportunity | None:
    key = str(getattr(scene, "key", "")).lower()
    name = str(getattr(scene, "name", "")).lower()
    haystack = f"{key.replace('_', ' ')} {name}"
    if "mirror" not in haystack and "mirrored" not in haystack and "skyglass" not in haystack:
        return None
    return ReflectionOpportunity(
        "reflective_architecture",
        "Reflective Surface",
        ("mirror", "glass", "surface", "reflection"),
        "Part of the room's reflective architecture catches your image clearly enough for a close look.",
        "The reflective surface gathers your features against the room behind you.",
    )


def _hub_fixture(scene) -> ReflectionOpportunity | None:
    tags = {str(tag).lower() for tag in getattr(scene, "tags", ())}
    name = " " + str(getattr(scene, "name", "")).lower()
    if not (tags & _HUB_TAGS) and not any(word in name for word in _HUB_NAME_WORDS):
        return None
    return _regional_fixture(str(getattr(scene, "region_key", "")))


def reflection_opportunities(scene, weather: str, *, exposed: bool) -> tuple[ReflectionOpportunity, ...]:
    """Return clear, usable reflective surfaces currently available in a room."""

    if scene is None:
        return ()

    result: list[ReflectionOpportunity] = []
    curated = _CURATED_FIXTURES.get(str(getattr(scene, "key", "")))
    if curated is not None:
        result.append(curated)

    for candidate in (
        _named_reflective_source(scene),
        _natural_water_source(scene),
        _hub_fixture(scene),
    ):
        if candidate is None:
            continue
        if any(existing.key == candidate.key or existing.name == candidate.name for existing in result):
            continue
        result.append(candidate)

    if exposed and weather in RAINY_WEATHER:
        result.append(
            ReflectionOpportunity(
                "rain_puddle",
                "Rain Puddle",
                ("puddle", "rainwater", "water", "reflection"),
                "Rainwater has collected in a shallow puddle. Its dark surface catches a wavering reflection whenever the fall eases between drops.",
                "The rainwater steadies just enough to hold your reflection, broken now and then by small ripples.",
                "weather",
            )
        )

    return tuple(result)


def find_reflection_opportunity(
    scene,
    weather: str,
    target: str,
    *,
    exposed: bool,
) -> ReflectionOpportunity | None:
    sources = reflection_opportunities(scene, weather, exposed=exposed)
    needle = " ".join(target.strip().lower().split())
    if not needle or needle in {"reflection", "my reflection", "self"}:
        return sources[0] if sources else None
    for source in sources:
        if source.matches(needle):
            return source
    return None


def render_reflection(
    character_name: str,
    race_key: str,
    stored: dict[str, str],
    source: ReflectionOpportunity,
) -> str:
    return f"{source.reflection_text} {appearance_description(character_name, race_key, stored)}"
