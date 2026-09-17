from __future__ import annotations

from dataclasses import dataclass
from time import time


@dataclass(frozen=True, slots=True)
class CorpseDecayState:
    """In-world presentation state for one persistent corpse."""

    family: str
    adjective: str
    description: str
    stage_index: int
    remaining_fraction: float


# Corpse decay is intentionally expressed as relative lifetime rather than raw
# seconds. A five-minute ordinary corpse and a fifteen-minute boss corpse pass
# through the same five narrative stages at the same proportional points.
_STAGE_THRESHOLDS: tuple[float, ...] = (0.75, 0.50, 0.25, 0.10)


_DECAY_PROFILES: dict[str, tuple[tuple[str, str], ...]] = {
    "living": (
        ("fresh", "The body is still fresh, with little sign of decay."),
        ("cooling", "The corpse is cooling and beginning to stiffen."),
        ("stinking", "The carcass has begun to stink badly."),
        ("rotting", "Rot has set in; the remains will not last much longer."),
        ("collapsing", "The remains are collapsing into an unrecognizable ruin and will soon be gone."),
    ),
    "undead": (
        ("still", "Whatever animating force held these remains has gone still."),
        ("deteriorating", "The death-touched remains are visibly deteriorating."),
        ("crumbling", "Bone, cloth, and dead tissue crumble at the edges."),
        ("disintegrating", "The remains are breaking down into dust and brittle fragments."),
        ("collapsing", "Only a collapsing heap of death-touched remains is left."),
    ),
    "construct": (
        ("sparking", "Residual sparks twitch through the wreckage."),
        ("cooling", "The ruined mechanism is cooling as its last motion dies away."),
        ("inert", "The construct is inert, its mechanisms locked and silent."),
        ("breaking down", "Joints loosen and damaged components begin to break down."),
        ("falling apart", "The wreck is falling apart into useless pieces and will soon be gone."),
    ),
    "arcane": (
        ("unstable", "The remains shiver with unstable magical residue."),
        ("flickering", "Its outline flickers as the force holding it together weakens."),
        ("fading", "The remains are fading, shedding traces of their former substance."),
        ("dissipating", "What remains is rapidly dissipating into the surrounding air."),
        ("nearly gone", "Only a faint trace remains, on the verge of vanishing completely."),
    ),
    "fungal": (
        ("fresh", "The fungal body is still fresh and heavy with living moisture."),
        ("wilting", "The fungal tissue is wilting and losing its firmness."),
        ("souring", "A sour smell rises as the fungal mass begins to spoil."),
        ("slumping", "The softened fungal body is slumping in on itself."),
        ("dissolving", "The remains are dissolving into wet pulp and will soon be gone."),
    ),
}


# These categories describe how remains physically leave the world, not combat
# or loot taxonomy. Anything recognizably biological defaults to "living".
_DECAY_FAMILY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "construct",
        (
            "construct",
            "clockwork",
            "automaton",
            "golem",
            "machine",
            "mechanical",
            "gearwork",
            "gear-work",
            "engine",
            "sentinel frame",
        ),
    ),
    (
        "fungal",
        (
            "fungus",
            "fungal",
            "mushroom",
            "mold",
            "mould",
            "spore",
            "mycel",
            "toadstool",
        ),
    ),
    (
        "undead",
        (
            "undead",
            "skeleton",
            "skeletal",
            "bonewalker",
            "ghoul",
            "wight",
            "revenant",
            "zombie",
            "mummy",
            "lich",
            "graveborn",
            "deathless",
        ),
    ),
    (
        "arcane",
        (
            "elemental",
            "wisp",
            "arcane",
            "astral",
            "spirit",
            "apparition",
            "specter",
            "spectre",
            "ghost",
            "shade",
            "anomaly",
            "moonfire",
            "ember",
            "cinder",
            "flame",
            "void",
            "planar",
            "imp",
            "demon",
            "devil",
            "fiend",
            "infernal",
        ),
    ),
)


def decay_family_for(enemy_key: str, enemy_name: str = "") -> str:
    """Return the physical decay family for a defeated creature."""

    text = f"{enemy_key} {enemy_name}".replace("_", " ").casefold()
    for family, tokens in _DECAY_FAMILY_TOKENS:
        if any(token in text for token in tokens):
            return family
    return "living"


def _decay_stage_index(remaining_fraction: float) -> int:
    remaining = max(0.0, min(1.0, float(remaining_fraction)))
    for index, threshold in enumerate(_STAGE_THRESHOLDS):
        if remaining > threshold:
            return index
    return len(_STAGE_THRESHOLDS)


def corpse_decay_state(corpse, *, now: float | None = None) -> CorpseDecayState:
    """Describe decay without exposing a literal despawn timer to the player."""

    current = time() if now is None else float(now)
    created = float(getattr(corpse, "created_at", current))
    expires = float(getattr(corpse, "expires_at", created + 1.0))
    lifetime = max(1.0, expires - created)
    remaining = max(0.0, min(1.0, (expires - current) / lifetime))
    stage_index = _decay_stage_index(remaining)
    family = decay_family_for(
        str(getattr(corpse, "enemy_key", "")),
        str(getattr(corpse, "enemy_name", "")),
    )
    adjective, description = _DECAY_PROFILES[family][stage_index]
    return CorpseDecayState(
        family=family,
        adjective=adjective,
        description=description,
        stage_index=stage_index,
        remaining_fraction=remaining,
    )


def corpse_decay_label(corpse, *, now: float | None = None) -> str:
    return corpse_decay_state(corpse, now=now).adjective


def corpse_decay_description(corpse, *, now: float | None = None) -> str:
    return corpse_decay_state(corpse, now=now).description
