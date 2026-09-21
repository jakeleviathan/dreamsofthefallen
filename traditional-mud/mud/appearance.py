from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppearanceTrait:
    key: str
    label: str
    options: tuple[str, ...]
    default: str


HUMAN_TRAITS = (
    AppearanceTrait("build", "Build", ("lean", "wiry", "average", "broad", "heavyset"), "average"),
    AppearanceTrait("complexion", "Complexion", ("pale", "fair", "olive", "brown", "deep brown"), "fair"),
    AppearanceTrait("hair_style", "Hair style", ("shaved", "cropped", "shoulder-length", "long", "braided", "wild"), "cropped"),
    AppearanceTrait("hair_color", "Hair color", ("black", "brown", "auburn", "blond", "silver", "white", "red"), "brown"),
    AppearanceTrait("eye_color", "Eye color", ("brown", "blue", "green", "gray", "amber", "violet", "black", "silver"), "brown"),
    AppearanceTrait("adornment", "Adornment", ("none", "kohl", "black ritual paint", "earrings", "facial chain", "brow stud"), "none"),
)

FOREST_ELF_TRAITS = (
    AppearanceTrait("build", "Build", ("slight", "lean", "graceful", "athletic", "sturdy"), "graceful"),
    AppearanceTrait("complexion", "Complexion", ("pale", "fair", "sun-warmed", "olive", "brown"), "fair"),
    AppearanceTrait("hair_style", "Hair style", ("cropped", "loose", "shoulder-length", "long", "braided", "leaf-braided"), "long"),
    AppearanceTrait("hair_color", "Hair color", ("black", "brown", "auburn", "blond", "silver", "white"), "brown"),
    AppearanceTrait("eye_color", "Eye color", ("green", "hazel", "brown", "gray", "blue", "amber"), "green"),
    AppearanceTrait("ear_style", "Ear shape", ("fine-pointed", "long-pointed", "swept-back", "high-set"), "long-pointed"),
    AppearanceTrait("adornment", "Adornment", ("none", "leaf beads", "wooden earrings", "green paint", "vine cord"), "none"),
)

MOON_ELF_TRAITS = (
    AppearanceTrait("build", "Build", ("slight", "lean", "poised", "athletic", "statuesque"), "poised"),
    AppearanceTrait("skin_tone", "Skin tone", ("pale lavender", "lavender-gray", "cool gray", "dusk violet", "silver-gray"), "lavender-gray"),
    AppearanceTrait("hair_style", "Hair style", ("cropped", "shoulder-length", "long", "braided", "swept-back", "loose"), "long"),
    AppearanceTrait("hair_color", "Hair color", ("black", "silver", "white", "ash brown", "midnight", "pale blond"), "silver"),
    AppearanceTrait("eye_color", "Eye color", ("silver", "violet", "black", "amber", "pale blue", "sea-green"), "silver"),
    AppearanceTrait("ear_style", "Ear shape", ("fine-pointed", "long-pointed", "swept-back", "high-set"), "fine-pointed"),
    AppearanceTrait("lunar_marking", "Lunar marking", ("none", "crescent brow mark", "temple dots", "silver linework", "moon-disc tattoo"), "none"),
)

DWARF_TRAITS = (
    AppearanceTrait("build", "Build", ("compact", "broad", "stocky", "muscular", "heavyset"), "stocky"),
    AppearanceTrait("complexion", "Complexion", ("pale", "fair", "ruddy", "olive", "brown", "deep brown"), "ruddy"),
    AppearanceTrait("hair_color", "Hair color", ("black", "brown", "auburn", "blond", "gray", "white", "red"), "brown"),
    AppearanceTrait("beard_style", "Beard style", ("clean-shaven", "close-cropped", "full", "forked", "braided", "double-braided", "ring-bound"), "full"),
    AppearanceTrait("beard_adornment", "Beard adornment", ("none", "iron rings", "brass clasps", "trade beads", "union ribbons", "stone beads"), "none"),
    AppearanceTrait("eye_color", "Eye color", ("brown", "gray", "green", "blue", "amber", "hazel"), "brown"),
)

GOBLIN_TRAITS = (
    AppearanceTrait("build", "Build", ("wiry", "lean", "compact", "rangy", "sturdy"), "wiry"),
    AppearanceTrait("skin_tone", "Skin tone", ("moss green", "olive green", "swamp green", "yellow-green", "dark green", "gray-green"), "olive green"),
    AppearanceTrait("ear_style", "Ear shape", ("wide", "swept-back", "drooping", "notched", "uneven"), "wide"),
    AppearanceTrait("nose_shape", "Nose shape", ("long", "hooked", "blunt", "crooked", "sharp"), "long"),
    AppearanceTrait("teeth", "Teeth", ("small sharp", "jagged", "prominent canines", "chipped", "crowded"), "jagged"),
    AppearanceTrait("eye_color", "Eye color", ("amber", "yellow", "green", "brown", "black", "gray"), "amber"),
    AppearanceTrait("hair_style", "Hair style", ("shaved", "patchy", "cropped", "greasy", "tied-back", "wild"), "cropped"),
    AppearanceTrait("adornment", "Adornment", ("none", "salvage chain", "copper piercings", "scrap earrings", "painted clan mark", "wire braid"), "none"),
)

TROLL_TRAITS = (
    AppearanceTrait("build", "Build", ("lanky", "powerful", "broad", "heavy", "corded"), "powerful"),
    AppearanceTrait("skin_tone", "Skin tone", ("forest green", "moss green", "dark green", "blue-green", "gray-green", "tundra pale"), "forest green"),
    AppearanceTrait("hair_style", "Hair style", ("shaved", "cropped", "long", "braided", "wild", "topknot"), "wild"),
    AppearanceTrait("hair_color", "Hair color", ("black", "brown", "gray", "white", "rust"), "black"),
    AppearanceTrait("tusks", "Tusks", ("none", "short", "blunt", "curved", "chipped"), "short"),
    AppearanceTrait("eye_color", "Eye color", ("amber", "brown", "green", "gray", "yellow", "ice-blue"), "amber"),
    AppearanceTrait("scars", "Scars", ("none", "claw scars", "ritual cuts", "burn scars", "old battle scars", "frost-pale scars"), "none"),
)

UNDEAD_TRAITS = (
    AppearanceTrait("frame", "Skeletal frame", ("slender", "average", "broad", "heavy-boned", "elongated"), "average"),
    AppearanceTrait("skeletal_state", "Preservation", ("clean skeleton", "sinew-bound", "parchment-dry", "partly flesh-clad", "ceremonially wrapped"), "clean skeleton"),
    AppearanceTrait("eye_glow", "Eye glow", ("none", "blue", "green", "violet", "amber", "white"), "none"),
    AppearanceTrait("bone_finish", "Bone finish", ("natural", "ash-dusted", "polished", "rune-marked", "smoke-darkened"), "natural"),
    AppearanceTrait("damage_marks", "Old damage", ("none", "cracked brow", "missing tooth", "split rib", "sword notch", "fire scoring"), "none"),
    AppearanceTrait("adornment", "Adornment", ("none", "iron rings", "funerary chain", "grave beads", "ritual paint"), "none"),
)

SPOREKIN_TRAITS = (
    AppearanceTrait("stature", "Stature", ("squat", "short", "average", "tall", "towering"), "average"),
    AppearanceTrait("body_shape", "Body shape", ("slender", "rounded", "knotted", "broad", "columnar"), "rounded"),
    AppearanceTrait("cap_shape", "Cap shape", ("domed", "flat", "bell-shaped", "shelfed", "wide-brimmed", "clustered"), "domed"),
    AppearanceTrait("cap_pattern", "Cap pattern", ("plain", "ringed", "speckled", "marbled", "veined"), "plain"),
    AppearanceTrait("cap_color", "Cap color", ("earth", "amber", "violet", "ivory", "blue-green"), "earth"),
    AppearanceTrait("glow", "Bioluminescent glow", ("none", "soft blue", "green", "amber", "violet"), "soft blue"),
    AppearanceTrait("surface_texture", "Surface texture", ("smooth", "velvety", "bark-like", "ridged", "porous"), "velvety"),
    AppearanceTrait("adornment", "Adornment", ("none", "root cord", "stone beads", "copper rings", "woven moss"), "none"),
)


TRAITS_BY_RACE = {
    "human": HUMAN_TRAITS,
    "forest_elf": FOREST_ELF_TRAITS,
    "moon_elf": MOON_ELF_TRAITS,
    "dwarf": DWARF_TRAITS,
    "goblin": GOBLIN_TRAITS,
    "troll": TROLL_TRAITS,
    "undead": UNDEAD_TRAITS,
    "sporekin": SPOREKIN_TRAITS,
}


RACE_NAMES = {
    "human": "Human",
    "forest_elf": "Forest Elf",
    "moon_elf": "Moon Elf",
    "dwarf": "Dwarf",
    "goblin": "Goblin",
    "troll": "Troll",
    "undead": "Undead",
    "sporekin": "Sporekin",
}


def traits_for_race(race_key: str) -> tuple[AppearanceTrait, ...]:
    return TRAITS_BY_RACE.get(race_key, HUMAN_TRAITS)


def defaults_for_race(race_key: str) -> dict[str, str]:
    return {trait.key: trait.default for trait in traits_for_race(race_key)}


def normalized_appearance(race_key: str, stored: dict[str, str]) -> dict[str, str]:
    result = defaults_for_race(race_key)
    valid = {trait.key: set(trait.options) for trait in traits_for_race(race_key)}
    for key, value in stored.items():
        if key in valid and value in valid[key]:
            result[key] = value
    return result


def validate_choice(race_key: str, trait_key: str, choice: str) -> tuple[bool, str]:
    normalized_key = trait_key.strip().lower().replace(" ", "_")
    normalized_choice = choice.strip().lower()
    trait = next((value for value in traits_for_race(race_key) if value.key == normalized_key), None)
    if trait is None:
        return False, "That is not an appearance category available to your race."
    if normalized_choice not in trait.options:
        return False, f"Choose one of: {', '.join(trait.options)}."
    return True, normalized_choice


def _detail_phrases(race_key: str, appearance: dict[str, str]) -> list[str]:
    phrases: list[str] = []
    handled: set[str] = set()

    if "build" in appearance:
        phrases.append(f"a {appearance['build']} build")
        handled.add("build")
    if "frame" in appearance:
        phrases.append(f"a {appearance['frame']} skeletal frame")
        handled.add("frame")
    if "stature" in appearance:
        phrases.append(f"{appearance['stature']} stature")
        handled.add("stature")
    if "body_shape" in appearance:
        phrases.append(f"a {appearance['body_shape']} body")
        handled.add("body_shape")
    if "complexion" in appearance:
        phrases.append(f"a {appearance['complexion']} complexion")
        handled.add("complexion")
    if "skin_tone" in appearance:
        phrases.append(f"{appearance['skin_tone']} skin")
        handled.add("skin_tone")

    hair_style = appearance.get("hair_style")
    hair_color = appearance.get("hair_color")
    if hair_style is not None:
        hair = f"{hair_style} {hair_color} hair" if hair_color is not None else f"{hair_style} hair"
        phrases.append(hair)
        handled.add("hair_style")
        if hair_color is not None:
            handled.add("hair_color")
    elif hair_color is not None and race_key != "dwarf":
        phrases.append(f"{hair_color} hair")
        handled.add("hair_color")

    beard_style = appearance.get("beard_style")
    if beard_style is not None:
        if beard_style == "clean-shaven":
            phrases.append("a clean-shaven face")
        else:
            color = appearance.get("hair_color")
            phrases.append(f"a {beard_style} {color} beard" if color else f"a {beard_style} beard")
        handled.add("beard_style")
        if "hair_color" in appearance:
            handled.add("hair_color")
    beard_adornment = appearance.get("beard_adornment")
    if beard_adornment and beard_adornment != "none" and beard_style != "clean-shaven":
        phrases.append(f"{beard_adornment} worked into the beard")
        handled.add("beard_adornment")

    if "eye_color" in appearance:
        phrases.append(f"{appearance['eye_color']} eyes")
        handled.add("eye_color")
    if "ear_style" in appearance:
        phrases.append(f"{appearance['ear_style']} ears")
        handled.add("ear_style")
    if "nose_shape" in appearance:
        phrases.append(f"a {appearance['nose_shape']} nose")
        handled.add("nose_shape")
    if "teeth" in appearance:
        phrases.append(f"{appearance['teeth']} teeth")
        handled.add("teeth")
    if "tusks" in appearance and appearance["tusks"] != "none":
        phrases.append(f"{appearance['tusks']} tusks")
        handled.add("tusks")
    if "scars" in appearance and appearance["scars"] != "none":
        phrases.append(appearance["scars"])
        handled.add("scars")

    if "skeletal_state" in appearance:
        phrases.append(appearance["skeletal_state"])
        handled.add("skeletal_state")
    if "eye_glow" in appearance and appearance["eye_glow"] != "none":
        phrases.append(f"{appearance['eye_glow']} light in the eye sockets")
        handled.add("eye_glow")
    if "bone_finish" in appearance:
        phrases.append(f"{appearance['bone_finish']} bones")
        handled.add("bone_finish")
    if "damage_marks" in appearance and appearance["damage_marks"] != "none":
        phrases.append(appearance["damage_marks"])
        handled.add("damage_marks")

    cap_shape = appearance.get("cap_shape")
    cap_pattern = appearance.get("cap_pattern")
    cap_color = appearance.get("cap_color")
    if cap_shape is not None:
        cap_bits = [value for value in (cap_color, cap_pattern, cap_shape) if value]
        phrases.append("a " + " ".join(cap_bits) + " cap")
        handled.update({"cap_shape", "cap_pattern", "cap_color"})
    if "glow" in appearance and appearance["glow"] != "none":
        phrases.append(f"a {appearance['glow']} bioluminescent glow")
        handled.add("glow")
    if "surface_texture" in appearance:
        phrases.append(f"a {appearance['surface_texture']} surface")
        handled.add("surface_texture")

    if "lunar_marking" in appearance and appearance["lunar_marking"] != "none":
        phrases.append(f"a {appearance['lunar_marking']}")
        handled.add("lunar_marking")
    if "adornment" in appearance and appearance["adornment"] != "none":
        phrases.append(f"{appearance['adornment']} as adornment")
        handled.add("adornment")

    traits = {trait.key: trait for trait in traits_for_race(race_key)}
    for key, value in appearance.items():
        if key in handled or value == "none":
            continue
        trait = traits.get(key)
        if trait is not None:
            phrases.append(f"{trait.label.lower()} {value}")
    return phrases

def appearance_description(character_name: str, race_key: str, stored: dict[str, str]) -> str:
    appearance = normalized_appearance(race_key, stored)
    race_name = RACE_NAMES.get(race_key, race_key.replace("_", " ").title())
    details = _detail_phrases(race_key, appearance)
    if not details:
        return f"{character_name} is a {race_name} with an unadorned appearance."
    if len(details) == 1:
        joined = details[0]
    else:
        joined = ", ".join(details[:-1]) + f", and {details[-1]}"
    return f"{character_name} is a {race_name} with {joined}."


def creation_preview_text(race_key: str, stored: dict[str, str]) -> str:
    appearance = normalized_appearance(race_key, stored)
    race_name = RACE_NAMES.get(race_key, race_key.replace("_", " ").title())
    details = _detail_phrases(race_key, appearance)
    if not details:
        return f"Your {race_name} will have an unadorned appearance."
    if len(details) == 1:
        joined = details[0]
    else:
        joined = ", ".join(details[:-1]) + f", and {details[-1]}"
    return f"Your {race_name} will have {joined}."


def reflection_text(character_name: str, race_key: str, stored: dict[str, str]) -> str:
    return (
        f"Rainwater steadies just enough to hold {character_name}'s reflection. "
        f"The image is imperfect, broken by tiny ripples, but clear enough to study. "
        f"{appearance_description(character_name, race_key, stored)}"
    )


def appearance_menu_text(race_key: str, stored: dict[str, str]) -> str:
    appearance = normalized_appearance(race_key, stored)
    lines = ["--- Reflection Appearance ---"]
    for trait in traits_for_race(race_key):
        lines.append(f"{trait.key}: {appearance[trait.key]}  | choices: {', '.join(trait.options)}")
    lines.append("Use APPEARANCE <category> <choice> while using this reflective surface. Type DONE when finished.")
    return "\r\n".join(lines)
