from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppearanceTrait:
    key: str
    label: str
    options: tuple[str, ...]
    default: str


STANDARD_TRAITS = (
    AppearanceTrait("hair_style", "Hair style", ("shaved", "cropped", "shoulder-length", "long", "braided", "wild"), "cropped"),
    AppearanceTrait("hair_color", "Hair color", ("black", "brown", "auburn", "blond", "silver", "white", "red"), "brown"),
    AppearanceTrait("eye_color", "Eye color", ("brown", "blue", "green", "gray", "amber", "violet", "black", "silver"), "brown"),
    AppearanceTrait("adornment", "Adornment", ("none", "kohl", "ritual paint", "earrings", "facial chain", "brow stud", "bone beads"), "none"),
)

UNDEAD_TRAITS = (
    AppearanceTrait("eye_glow", "Eye glow", ("none", "blue", "green", "violet", "amber", "white"), "none"),
    AppearanceTrait("bone_finish", "Bone finish", ("natural", "ash-dusted", "polished", "rune-marked", "smoke-darkened"), "natural"),
    AppearanceTrait("adornment", "Adornment", ("none", "iron rings", "funerary chain", "grave beads", "ritual paint"), "none"),
)

SPOREKIN_TRAITS = (
    AppearanceTrait("cap_pattern", "Cap pattern", ("plain", "ringed", "speckled", "marbled", "veined"), "plain"),
    AppearanceTrait("cap_color", "Cap color", ("earth", "amber", "violet", "ivory", "blue-green"), "earth"),
    AppearanceTrait("glow", "Bioluminescent glow", ("none", "soft blue", "green", "amber", "violet"), "soft blue"),
    AppearanceTrait("adornment", "Adornment", ("none", "root cord", "stone beads", "copper rings", "woven moss"), "none"),
)


def traits_for_race(race_key: str) -> tuple[AppearanceTrait, ...]:
    if race_key == "undead":
        return UNDEAD_TRAITS
    if race_key == "sporekin":
        return SPOREKIN_TRAITS
    return STANDARD_TRAITS


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


def reflection_text(character_name: str, race_key: str, stored: dict[str, str]) -> str:
    appearance = normalized_appearance(race_key, stored)
    trait_by_key = {trait.key: trait for trait in traits_for_race(race_key)}
    details = ", ".join(
        f"{trait_by_key[key].label.lower()}: {value}"
        for key, value in appearance.items()
        if key in trait_by_key
    )
    return (
        f"Rainwater steadies just enough to hold {character_name}'s reflection. "
        f"The image is imperfect, broken by tiny ripples, but clear enough to study: {details}."
    )


def appearance_menu_text(race_key: str, stored: dict[str, str]) -> str:
    appearance = normalized_appearance(race_key, stored)
    lines = ["--- Reflection Appearance ---"]
    for trait in traits_for_race(race_key):
        lines.append(f"{trait.key}: {appearance[trait.key]}  | choices: {', '.join(trait.options)}")
    lines.append("Use APPEARANCE <category> <choice> while looking into the puddle. Type DONE when finished.")
    return "\r\n".join(lines)
