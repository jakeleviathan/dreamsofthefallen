from __future__ import annotations

"""Live, truthful player descriptions shared by both room renderers."""

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.social_experience import _ACTIVE_SESSIONS
from mud.waymeet_frontier import WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_LOFT_KEY


def _role_description(character) -> str:
    race_key = str(getattr(character, "race", "") or "")
    class_key = str(getattr(character, "character_class", "") or "")
    race = RACES_BY_KEY.get(race_key)
    klass = CLASSES_BY_KEY.get(class_key)
    race_name = race.name if race else race_key.replace("_", " ").title()
    class_name = klass.name if klass else class_key.replace("_", " ").title()
    return " ".join(part for part in (race_name, class_name) if part)


def _role_article(role: str) -> str:
    return "an" if role[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"


def _live_session(character, viewer):
    """The room callback supplies visible characters; this resolves live activity.

    Do not infer another player's activity from their saved character record.
    Only currently connected sessions have a meaningful REST/combat state.
    """
    if int(character.id) == int(viewer.character.id):
        return viewer
    for other in tuple(_ACTIVE_SESSIONS):
        active = getattr(other, "character", None)
        state = getattr(other, "state", None)
        if (
            active is not None
            and int(active.id) == int(character.id)
            and active.current_room == character.current_room
            and (state is None or getattr(state, "name", "PLAYING") == "PLAYING")
        ):
            return other
    return None


def _activity(session, room_key: str) -> str:
    if session is None:
        return "standing nearby"
    casting = getattr(session, "_active_cast", None)
    if isinstance(casting, dict):
        ability = casting.get("ability")
        spell_name = " ".join(str(getattr(ability, "name", "") or "").split())[:64]
        if spell_name:
            return f"casting {spell_name}"
    enemy = getattr(session, "active_enemy", None)
    if enemy is not None and bool(getattr(enemy, "alive", True)):
        name = str(getattr(getattr(enemy, "definition", None), "name", "") or "")
        # Names are authored, but never let control characters leak into room UI.
        name = " ".join(name.split())[:64]
        return f"fighting {name}" if name else "fighting"
    if bool(getattr(session, "_movement_resting", False)):
        if room_key == WAYMEET_TAVERN_KEY:
            return "resting beside the gearwheel hearth"
        if room_key == WAYMEET_TAVERN_LOFT_KEY:
            return "resting in the guest loft"
        return "resting"
    return "standing nearby"


def room_player_entries(session) -> list[tuple[str, str]]:
    """Render the viewer and other *online* characters in the same room.

    The server's room_players_callback remains the source of truth for who is
    visible. The live session registry is used only to describe their activity.
    An unavailable callback still permits showing the viewer's own posture.
    """
    viewer = getattr(session, "character", None)
    if viewer is None or not getattr(viewer, "current_room", None):
        return []
    others = []
    callback = getattr(session, "room_players_callback", None)
    if callable(callback):
        try:
            others = list(callback(viewer.current_room, viewer.id) or ())
        except Exception:
            others = []

    entries: list[tuple[str, str]] = []
    seen: set[int] = set()
    for character in (viewer, *sorted(others, key=lambda c: str(getattr(c, "name", "")).casefold())):
        name = str(getattr(character, "name", "") or "").strip()
        if not name:
            continue
        try:
            character_id = int(character.id)
        except (TypeError, ValueError, AttributeError):
            continue
        if character_id in seen or character.current_room != viewer.current_room:
            continue
        seen.add(character_id)
        is_self = character_id == int(viewer.id)
        role = _role_description(character)
        activity = _activity(_live_session(character, session), viewer.current_room)
        label = name + (" (you)" if is_self else "")
        description = f"{_role_article(role)} {role} {activity}" if role else f"an adventurer {activity}"
        entries.append((label, description))
    return entries
