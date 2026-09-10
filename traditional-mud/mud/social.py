from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NpcSocialPolicy:
    """Selective authored social reactions while ordinary dialogue stays shared.

    NPCs can react to either race or class for important disposition beats such
    as hostility, fear, distrust, respect, or rare service refusal. Everything
    else can use the NPC's normal dialogue path.
    """

    respected_races: frozenset[str] = frozenset()
    respected_classes: frozenset[str] = frozenset()
    distrusted_races: frozenset[str] = frozenset()
    distrusted_classes: frozenset[str] = frozenset()
    feared_races: frozenset[str] = frozenset()
    feared_classes: frozenset[str] = frozenset()
    hostile_races: frozenset[str] = frozenset()
    hostile_classes: frozenset[str] = frozenset()
    refused_races: frozenset[str] = frozenset()
    refused_classes: frozenset[str] = frozenset()

    def reaction_to(self, race_key: str, class_key: str | None = None) -> str:
        class_key = class_key or ""
        if race_key in self.hostile_races or class_key in self.hostile_classes:
            return "hostile"
        if race_key in self.refused_races or class_key in self.refused_classes:
            return "refuse_service"
        if race_key in self.feared_races or class_key in self.feared_classes:
            return "fear"
        if race_key in self.distrusted_races or class_key in self.distrusted_classes:
            return "distrust"
        if race_key in self.respected_races or class_key in self.respected_classes:
            return "respect"
        return "normal"
