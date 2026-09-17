from __future__ import annotations


PUMP_GALLERY_ROOM_KEY = "goblin_greenhouse_pump_gallery"

_VALVE_TARGETS: dict[str, str] = {
    "black": "black",
    "black valve": "black",
    "drain": "black",
    "drain valve": "black",
    "blue": "blue",
    "blue valve": "blue",
    "intake": "blue",
    "intake valve": "blue",
    "red": "red",
    "red valve": "red",
    "return": "red",
    "return valve": "red",
}


def normalize_local_interaction(room_key: str, command: str) -> str:
    """Translate intuitive room-local phrasings into the authored canonical command.

    USE normally belongs to class abilities, but obvious physical room features should
    win when the player is standing next to them. This keeps local world interaction
    phrasing from falling through to the ability parser.
    """
    if room_key != PUMP_GALLERY_ROOM_KEY:
        return command

    stripped = " ".join(command.strip().lower().split())
    parts = stripped.split(maxsplit=1)
    if not parts or parts[0] not in {"turn", "open", "use"}:
        return command

    target = parts[1] if len(parts) == 2 else ""
    if target in {"valve", "valves", "hand valve", "hand valves", "three valves"}:
        return "turn valves"

    color = _VALVE_TARGETS.get(target)
    if color is None:
        return command
    return f"turn {color} valve"


def contextual_action_hints(room_key: str) -> tuple[tuple[str, str], ...]:
    if room_key != PUMP_GALLERY_ROOM_KEY:
        return ()
    return (
        (
            "TURN <valve>",
            "operate one of the blue, red, or black hand valves; OPEN and USE work as aliases here",
        ),
    )


def hidden_feature_verbs(room_key: str) -> frozenset[str]:
    """Suppress text-derived hints that are misleading for a specific interaction."""
    if room_key == PUMP_GALLERY_ROOM_KEY:
        # The pipe-map prose says "opening" a circuit, which made the generic help
        # scanner advertise OPEN even though the authored puzzle's real verb is TURN.
        return frozenset({"OPEN"})
    return frozenset()
