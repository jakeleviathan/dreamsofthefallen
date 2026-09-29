"""Brewing process metadata shared by authored catalogs and the live runtime.

Brewing deliberately uses the ordinary crafting recipe catalog for ingredients,
skill/trivial values, discovery flags and presentation, while this module keeps
the parts that make a brew different from an instant craft: fermentation,
optional cellaring, yeast choice and water profile.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrewProcess:
    recipe_key: str
    family: str
    ferment_seconds: int
    age_seconds: int = 0
    aged_output_item_key: str | None = None
    default_yeast_key: str | None = None
    default_water_key: str | None = None
    can_swap_yeast: bool = False
    can_swap_water: bool = False
    social_cups: int = 4

    def __post_init__(self) -> None:
        if self.ferment_seconds < 1:
            raise ValueError("Brew fermentation time must be positive.")
        if self.age_seconds < 0:
            raise ValueError("Brew aging time cannot be negative.")
        if self.social_cups < 1:
            raise ValueError("A brewed drink must pour at least one cup.")


BREW_PROCESSES: dict[str, BrewProcess] = {}

YEAST_OPTIONS: dict[str, tuple[str, float]] = {
    "brewers_yeast": ("Clean Brewer's Yeast", 0.90),
    "wild_yeast_culture": ("Wild Yeast Culture", 1.15),
}

WATER_OPTIONS: dict[str, tuple[str, float]] = {
    "spring_water": ("Spring Water", 1.00),
    "filtered_brewing_water": ("Filtered Brewing Water", 0.85),
}


def register_process(process: BrewProcess) -> None:
    """Register one process idempotently.

    Content installers can run more than once in isolated tests. Re-registering
    identical metadata is harmless, while conflicting metadata is a real authoring
    error and should fail loudly.
    """

    existing = BREW_PROCESSES.get(process.recipe_key)
    if existing is not None and existing != process:
        raise RuntimeError(f"Conflicting brewing process metadata for {process.recipe_key}")
    BREW_PROCESSES[process.recipe_key] = process


def process_for(recipe_key: str) -> BrewProcess | None:
    return BREW_PROCESSES.get(recipe_key)


def adjusted_seconds(
    process: BrewProcess,
    *,
    yeast_key: str | None,
    water_key: str | None,
) -> int:
    """Resolve the player-selected fermentation profile.

    Clean yeast and filtered water are quicker and predictable. Wild culture is
    slower. These choices affect real production timing without creating hidden
    combat-power advantages or a combinatorial set of item variants.
    """

    multiplier = 1.0
    if yeast_key in YEAST_OPTIONS:
        multiplier *= YEAST_OPTIONS[yeast_key][1]
    if water_key in WATER_OPTIONS:
        multiplier *= WATER_OPTIONS[water_key][1]
    return max(1, int(round(process.ferment_seconds * multiplier)))
