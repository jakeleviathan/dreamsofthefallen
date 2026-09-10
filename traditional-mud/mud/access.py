from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CharacterAccessState:
    flags: frozenset[str] = frozenset()
    keys: frozenset[str] = frozenset()
    group_size: int = 1


@dataclass(frozen=True, slots=True)
class ContentGate:
    """Optional gate for the otherwise open world."""

    required_flags: frozenset[str] = frozenset()
    required_keys: frozenset[str] = frozenset()
    minimum_group_size: int = 1

    def missing_requirements(self, state: CharacterAccessState) -> tuple[str, ...]:
        missing: list[str] = []
        missing.extend(f"flag:{flag}" for flag in sorted(self.required_flags - state.flags))
        missing.extend(f"key:{key}" for key in sorted(self.required_keys - state.keys))
        if state.group_size < self.minimum_group_size:
            missing.append(f"group_size:{self.minimum_group_size}")
        return tuple(missing)

    def allows(self, state: CharacterAccessState) -> bool:
        return not self.missing_requirements(state)


@dataclass(frozen=True, slots=True)
class WorldAccessRules:
    mostly_open_world: bool = True
    keys_and_character_flags_can_gate_content: bool = True
    race_never_globally_locks_civilizations: bool = True
    every_class_can_solo_to_end_level: bool = True
    optional_group_content_can_require_parties: bool = True
    raids_can_require_groups: bool = True
    difficult_high_end_zones_can_require_groups: bool = True


WORLD_ACCESS_RULES = WorldAccessRules()
